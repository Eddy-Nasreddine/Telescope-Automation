import logging
import math
import threading
import time

import serial

import config
from CelestialObject import CelestialObject
from GpsUartReceiver import GpsUartReceiver

logger = logging.getLogger("TelescopeController")


class TelescopeError(Exception):
    """A command was refused; the message is safe to show in the UI."""


class TelescopeBusyError(TelescopeError):
    """The mount is moving (or the MCU link is down) and can't take this command."""


class LimitError(TelescopeError):
    """The requested move is outside the mount's safe range."""


class TelescopeController():
    def __init__(
        self,
        elevation_controller,
        azimuth_controller,
        el_driver_teeth: int,
        el_driven_teeth: int,
        az_driver_teeth: int,
        az_driven_teeth: int,
        ser=None,
        start_gps: bool = True,
    ):
        self.elevation_controller = elevation_controller
        self.azimuth_controller = azimuth_controller
        self.el_driver_teeth = el_driver_teeth
        self.el_driven_teeth = el_driven_teeth
        self.az_driver_teeth = az_driver_teeth
        self.az_driven_teeth = az_driven_teeth
        self.current_el = 0
        self.current_az = 0
        self.az_wrap = None     # net azimuth turn from home (cable wrap), set on first report
        self.error_el = 0
        self.error_az = 0
        self.pulse_delay = 0
        self.moving = False
        self.sys_ready = False
        self.calibrating = False
        self.tracking = None        # display name of the object being tracked
        self.calibration_obj = CelestialObject("polaris")

        # _command_lock serialises whole commands (check busy, claim, write, wait
        # for a reply). _write_lock only guards the raw write, so stop() never
        # has to wait behind another command.
        self._command_lock = threading.Lock()
        self._write_lock = threading.Lock()
        self._stop_ack = threading.Event()
        self._reply_done = threading.Event()
        self._shutdown = threading.Event()
        self._track_stop = threading.Event()
        self._jogging = False
        self._jog_deadline = 0.0
        self._last_mcu_activity = time.monotonic()
        self._last_heartbeat = time.monotonic()
        self._missed_heartbeats = 0

        # A serial-like object can be passed in (SimulatedSerial, tests); otherwise open the real port
        self.ser = ser if ser is not None else serial.Serial(config.MCU_PORT, config.MCU_BAUD, timeout=1)
        self.listener_thread = threading.Thread(target=self._listen, daemon=True)
        self.listener_thread.start()
        self.handshake()
        self.gps = GpsUartReceiver()
        if start_gps:
            self.gps.start()
        self.watchdog_thread = threading.Thread(target=self._watchdog, daemon=True)
        self.watchdog_thread.start()

    # Altitude angle per motor step (after microstepping + gear ratio)
    @property
    def alt_angle_per_step(self) -> float:
        gear_ratio = self.el_driver_teeth / self.el_driven_teeth
        return self.elevation_controller.angle_per_step * gear_ratio

    # Azimuth angle per motor step (after microstepping + gear ratio)
    @property
    def az_angle_per_step(self) -> float:
        gear_ratio = self.az_driver_teeth / self.az_driven_teeth
        return self.azimuth_controller.angle_per_step * gear_ratio

    def _write(self, cmd: str):
        with self._write_lock:
            self.ser.write((cmd + "\n").encode())

    def _send(self, cmd: str):
        # Non-motion commands. The firmware drops everything except a stop while
        # it's stepping, so refuse instead of silently losing the command.
        with self._command_lock:
            if self.moving:
                raise TelescopeBusyError("Telescope is already moving.")
            self._write(cmd)
        logger.info("Command sent: %s", cmd)

    def _send_motion(self, cmd: str, jogging: bool = False):
        # Check and claim the busy flag in one locked step, so two requests can
        # never both see "not moving" before the MCU's first position report.
        with self._command_lock:
            if not self.sys_ready:
                raise TelescopeBusyError("No link to the MCU. Check the UART connection.")
            if self.moving:
                raise TelescopeBusyError("Telescope is already moving.")
            self.moving = True
            self._jogging = jogging
            self._last_mcu_activity = time.monotonic()
            self._write(cmd)
        logger.info("Command sent: %s", cmd)

    def _listen(self):
        logger.info("UART listener has begun...")
        while not self._shutdown.is_set():
            try:
                raw = self.ser.readline()
            except serial.SerialException as e:
                logger.error("UART read failed: %s", e)
                self._set_link(False)
                self._shutdown.wait(1)
                continue
            # errors="replace": one corrupt byte must not kill this thread
            line = raw.decode("ascii", errors="replace").strip()
            if not line:
                continue
            try:
                self._handle_line(line)
            except ValueError:
                logger.warning("Ignoring malformed MCU line %r", line)
            except Exception:
                logger.exception("Could not handle MCU line %r", line)

    def _handle_line(self, line: str):
        logger.debug("Received: %s", line)
        self._last_mcu_activity = time.monotonic()
        if line.startswith("ERR"):
            # The firmware only reports errors from its idle loop, so any ERR
            # means it dropped that command and is idle. (After ERR:dir it never
            # sends D, which used to leave "moving" stuck.)
            if self.moving:
                logger.warning("MCU rejected the command: %s", line)
            else:
                logger.debug("MCU: %s", line)
            self.moving = False
            self._jogging = False
            self._stop_ack.set()
        elif line.startswith("A"):
            new_az = float(line[1:])
            if self.az_wrap is None:
                self.az_wrap = self._wrap180(new_az - config.HOME_AZ)
            else:
                self.az_wrap += self._wrap180(new_az - self.current_az)
            self.current_az = new_az
        elif line.startswith("E") and len(line) > 1:
            self.current_el = float(line[1:])
        elif line.startswith("S"):
            self.moving = False
            self._jogging = False
            self._stop_ack.set()
        elif line.startswith("D"):
            if self.moving:
                logger.info("System reached target position.")
            self.moving = False
            self._jogging = False
            self._reply_done.set()
        elif line.startswith("O"):
            logger.info("System origin has been reset.")
            self.current_az = config.HOME_AZ
            self.current_el = config.HOME_EL
            self.az_wrap = 0.0
        elif line.startswith("R"):
            self._set_link(True)
        elif line.startswith("T"):
            self.pulse_delay = int(line[1:])

    def handshake(self) -> bool:
        logger.info("Sending handshake...")
        with self._command_lock:
            return self._request_state()

    def _request_state(self) -> bool:
        # Caller holds _command_lock. The R reply ends with D; keeping the lock
        # until then stops another command colliding with the MCU's reply.
        if self.moving:
            return True     # position reports during a move already prove the link
        self._reply_done.clear()
        try:
            self._write("R")
        except serial.SerialException as e:
            logger.error("UART write failed: %s", e)
            return False
        return self._reply_done.wait(config.HEARTBEAT_TIMEOUT)

    def stop(self):
        # Stop never waits on the command lock. The MCU confirms with S (or ERR
        # when it was idle); resend if that doesn't arrive, because a byte can be
        # lost while the firmware is mid-step.
        self.stop_tracking()
        self._jogging = False
        for attempt in range(1, config.STOP_RETRIES + 1):
            self._stop_ack.clear()
            self._write("S")
            if self._stop_ack.wait(config.STOP_ACK_TIMEOUT):
                break
            logger.warning("Stop not confirmed by the MCU (attempt %d/%d)", attempt, config.STOP_RETRIES)
        else:
            logger.error("The MCU never confirmed the stop.")
        self.moving = False
        logger.info("Command sent: S")

    def set_pulse(self, delay: int):
        if isinstance(delay, bool) or not isinstance(delay, int) \
                or not config.PULSE_DELAY_MIN <= delay <= config.PULSE_DELAY_MAX:
            raise LimitError(f"Pulse delay must be {config.PULSE_DELAY_MIN}-{config.PULSE_DELAY_MAX} ms.")
        self._send(f"T{delay}")

    def _calc_az(self, target_az: float) -> tuple[str, int]:
        step_angle = self.az_angle_per_step
        diff = target_az - self.current_az
        if diff > 180:
            diff -= 360
        elif diff < -180:
            diff += 360
        # Shortest path, unless it would wind the motor cable past its limit
        if config.AZ_CABLE_LIMIT is not None:
            wrap = self._current_wrap()
            if abs(wrap + diff) > config.AZ_CABLE_LIMIT + 1e-6:
                diff -= math.copysign(360, diff)    # go the long way round instead
                if abs(wrap + diff) > config.AZ_CABLE_LIMIT + 1e-6:
                    raise LimitError(f"Azimuth {target_az:.2f}° can't be reached within the cable limit.")
        steps = round(abs(diff) / step_angle)
        direction = "+" if diff > 0 else "-"
        # Never let rounding carry the mount past a limit
        return direction, min(steps, self._az_steps_to_limit(direction))

    def _calc_el(self, target_alt: float) -> tuple[str, int]:
        step_angle = self.alt_angle_per_step
        diff = target_alt - self.current_el
        steps = round(abs(diff) / step_angle)
        direction = "+" if diff > 0 else "-"
        return direction, min(steps, self._el_steps_to_limit(direction))

    def reset_origin(self):
        self.stop_tracking()
        self._send("O")

    def move_to(self, target: tuple):
        # target = (elevation, azimuth) in sky coordinates
        el, az = float(target[0]), float(target[1])
        if not (math.isfinite(el) and math.isfinite(az)):
            raise LimitError("Target coordinates must be numbers.")
        if not config.EL_MIN <= el <= config.EL_MAX:
            raise LimitError(f"Elevation {el:.2f}° is outside the {config.EL_MIN:g}-{config.EL_MAX:g}° range.")
        if not 0 <= az <= 360:
            raise LimitError(f"Azimuth {az:.2f}° is outside 0-360°.")

        # The mount reads (true + error) after calibration, so aim at true + error,
        # then clamp to the physical range in case the offset pushes past it
        mount_el = min(max(el + self.error_el, config.EL_MIN), config.EL_MAX)
        mount_az = (az + self.error_az) % 360

        el_dir, el_steps = self._calc_el(mount_el)
        az_dir, az_steps = self._calc_az(mount_az)
        if el_steps == 0 and az_steps == 0:
            logger.info("Already at elevation %.3f° azimuth %.3f°; nothing to send.", el, az)
            return
        az_cmd = self.azimuth_controller.build_command(az_dir, az_steps)
        el_cmd = self.elevation_controller.build_command(el_dir, el_steps)
        full_cmd = az_cmd + el_cmd
        logger.info("Moving to elevation %.3f° azimuth %.3f°: Azimuth[%d%s] Elevation[%d%s]",
                    el, az, az_steps, az_dir, el_steps, el_dir)
        self._send_motion(full_cmd)

    def calibrate(self):
        logger.info("Calibration process has started...")
        self.stop_tracking()
        self.move_to_object(self.calibration_obj)
        self.calibrating = True     # only once the slew to Polaris was accepted

    def finish_calibration(self):
        if not self.calibrating:
            raise TelescopeError("Calibration isn't running.")
        my_coords = self.gps.get_coords()
        polaris = self.calibration_obj.get_astrometric_coords(my_coords)
        logger.info("Polaris is at elevation %.3f° azimuth %.3f°", polaris.altitude, polaris.azimuth)
        # wrap180 so an error across north (359.9 vs 0.1) is -0.2°, not 359.8°
        self.error_az = self._wrap180(self.current_az - polaris.azimuth)
        self.error_el = self.current_el - polaris.altitude
        self.calibrating = False
        logger.info("Calibration offsets: azimuth %+.3f° elevation %+.3f°", self.error_az, self.error_el)

    def move_to_object(self, celestial_object):
        coords = self.gps.get_coords()
        position = celestial_object.get_astrometric_coords(coords)
        if position.altitude < config.MIN_VISIBLE_ELEVATION:
            raise LimitError(f"{celestial_object.display_name} is at {position.altitude:.1f}°, "
                             f"below the {config.MIN_VISIBLE_ELEVATION:g}° minimum.")
        logger.info("Moving to celestial object %s at Elevation: %.3f° | Azimuth: %.3f°",
                    celestial_object.name, position.altitude, position.azimuth)
        self.move_to((position.altitude, position.azimuth))

    def jog(self, direction: str):
        # One long move toward the limit in that direction; releasing the button
        # calls stop(). The browser must call jog_heartbeat() while it's held,
        # or the watchdog stops the mount (dead-man).
        moves = {
            "left":  ("az", "+"),
            "right": ("az", "-"),
            "up":    ("el", "+"),
            "down":  ("el", "-"),
        }
        if direction not in moves:
            raise TelescopeError(f"Unknown jog direction: {direction!r}")
        self.stop_tracking()
        axis, sign = moves[direction]
        if axis == "az":
            steps = self._az_steps_to_limit(sign)
            cmd = self.azimuth_controller.build_command(sign, steps) + self.elevation_controller.build_command("+", 0)
        else:
            steps = self._el_steps_to_limit(sign)
            cmd = self.azimuth_controller.build_command("+", 0) + self.elevation_controller.build_command(sign, steps)
        if steps == 0:
            raise LimitError(f"Can't jog {direction}: already at the limit.")
        self._jog_deadline = time.monotonic() + config.JOG_HEARTBEAT_TIMEOUT
        self._send_motion(cmd, jogging=True)

    def jog_heartbeat(self):
        if self._jogging:
            self._jog_deadline = time.monotonic() + config.JOG_HEARTBEAT_TIMEOUT

    def track_object(self, celestial_object):
        # Slew now (errors reach the caller), then keep re-pointing every
        # TRACK_INTERVAL seconds until stop(), a jog, another move, or it sets.
        self.stop_tracking()
        self.move_to_object(celestial_object)
        stop_event = threading.Event()
        self._track_stop = stop_event
        self.tracking = celestial_object.display_name
        threading.Thread(target=self._track_loop, args=(celestial_object, stop_event), daemon=True).start()
        logger.info("Tracking has begun: %s", self.tracking)

    def _track_loop(self, celestial_object, stop_event):
        while not stop_event.wait(config.TRACK_INTERVAL):
            if self.moving:
                continue    # still finishing the previous correction
            try:
                self.move_to_object(celestial_object)
            except TelescopeBusyError:
                continue
            except Exception as e:
                logger.warning("Tracking stopped: %s", e)
                break
        if self._track_stop is stop_event:
            self.tracking = None

    def stop_tracking(self):
        if self.tracking:
            logger.info("Tracking stopped: %s", self.tracking)
        self._track_stop.set()
        self.tracking = None

    # ---------- Limits ----------

    @staticmethod
    def _wrap180(angle: float) -> float:
        return ((angle + 180) % 360) - 180

    def _current_wrap(self) -> float:
        if self.az_wrap is None:
            return self._wrap180(self.current_az - config.HOME_AZ)
        return self.az_wrap

    @staticmethod
    def _steps_within(degrees: float, step_angle: float) -> int:
        # floor, not round, so a move to the limit never steps past it
        steps = math.floor(max(0.0, degrees) / step_angle + 1e-9)
        return min(steps, config.MAX_STEPS_PER_COMMAND)

    def _el_steps_to_limit(self, sign: str) -> int:
        room = config.EL_MAX - self.current_el if sign == "+" else self.current_el - config.EL_MIN
        return self._steps_within(room, self.alt_angle_per_step)

    def _az_steps_to_limit(self, sign: str) -> int:
        if config.AZ_CABLE_LIMIT is None:
            room = 360.0    # a full turn is the most any single move needs
        else:
            wrap = self._current_wrap()
            room = config.AZ_CABLE_LIMIT - wrap if sign == "+" else config.AZ_CABLE_LIMIT + wrap
        return self._steps_within(room, self.az_angle_per_step)

    # ---------- Watchdog ----------

    def _set_link(self, ok: bool):
        if ok and not self.sys_ready:
            logger.info("Handshake established")
        elif not ok and self.sys_ready:
            logger.error("Lost the MCU link")
        self.sys_ready = ok
        if ok:
            self._missed_heartbeats = 0

    def _watchdog(self):
        while not self._shutdown.wait(0.05):
            try:
                self._watchdog_tick()
            except Exception:
                logger.exception("Watchdog error")

    def _watchdog_tick(self):
        now = time.monotonic()
        # Dead-man: the browser stopped confirming the jog button is held
        if self._jogging and now > self._jog_deadline:
            logger.warning("Jog heartbeat lost; stopping the mount.")
            self.stop()
        # The MCU went silent mid-move (it reports every step, so this is a fault)
        elif self.moving and now - self._last_mcu_activity > config.MOTION_TIMEOUT:
            logger.warning("No reply from the MCU for %.1f s during a move; clearing the busy flag.",
                           config.MOTION_TIMEOUT)
            self.moving = False
            self._jogging = False
        # Idle link check
        if not self.moving and now - self._last_heartbeat > config.HEARTBEAT_INTERVAL:
            self._last_heartbeat = now
            self._heartbeat()

    def _heartbeat(self):
        if not self._command_lock.acquire(blocking=False):
            return      # a command is in flight; check again next interval
        try:
            ok = self._request_state()
        finally:
            self._command_lock.release()
        if ok:
            self._missed_heartbeats = 0
        else:
            self._missed_heartbeats += 1
            if self._missed_heartbeats >= config.HEARTBEAT_MISSES:
                self._set_link(False)

    def close(self):
        # Stop background threads and release the ports (used by tests)
        self.stop_tracking()
        self._shutdown.set()
        self.gps.stop()
        self.listener_thread.join(timeout=2)
        self.watchdog_thread.join(timeout=2)
        self.ser.close()
