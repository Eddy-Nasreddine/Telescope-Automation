"""
A stand-in for the STM32's UART link, for running without the Pi hardware.

It mimics main.c: the same commands and replies, one position report per step,
'S' only noticed between steps, the azimuth move running before the elevation
direction is checked, and no 'D' after an ERR.
"""
import queue
import threading
import time

# Mirrors the constants hard-coded in main.c
EL_ANGLE_PER_STEP = 0.09
AZ_ANGLE_PER_STEP = 0.135
HOME_AZ = 90.0
HOME_EL = 90.0
UART_POLL_MS = 10   # HAL_UART_Receive timeout checked before every step


def _atoi(text: str) -> int:
    # Like C atoi: leading digits only, 0 if none
    digits = ""
    for ch in text:
        if not ch.isdigit():
            break
        digits += ch
    return int(digits) if digits else 0


class SimulatedSerial:
    def __init__(self, timeout: float = 1.0, step_time: float = None):
        self.timeout = timeout
        # Seconds per step; None = like the firmware (2 x pulse delay + UART poll)
        self.step_time = step_time
        self.connected = True       # False = the MCU stops answering (cable pulled)
        self.is_open = True
        self.azimuth = HOME_AZ
        self.elevation = HOME_EL
        self.delay = 10
        self._rx = queue.Queue()    # bytes Pi -> MCU
        self._tx = queue.Queue()    # lines MCU -> Pi
        self._thread = threading.Thread(target=self._firmware_loop, daemon=True)
        self._thread.start()

    # ---------- pyserial-like interface ----------

    def write(self, data: bytes) -> int:
        if self.connected:
            for byte in data:
                self._rx.put(byte)
        return len(data)

    def readline(self) -> bytes:
        try:
            return self._tx.get(timeout=self.timeout)
        except queue.Empty:
            return b""

    def close(self):
        self.is_open = False

    def inject(self, raw: bytes):
        """Push raw bytes to the Pi as if the MCU sent them (tests: corrupt data)."""
        self._tx.put(raw)

    # ---------- firmware ----------

    def _reply(self, text: str):
        if self.connected:
            self._tx.put((text + "\r\n").encode())

    def _firmware_loop(self):
        buffer = ""
        while self.is_open:
            try:
                ch = chr(self._rx.get(timeout=0.1))
            except queue.Empty:
                continue
            if ch == "\r":
                continue
            if ch != "\n":
                if len(buffer) < 19:
                    buffer += ch
                else:
                    buffer = ""
                    self._reply("ERR:overflow")
                continue
            self._handle(buffer)
            buffer = ""

    def _handle(self, cmd: str):
        if cmd.startswith("R"):
            self._reply("R")
            self._reply(f"A{self.azimuth:.3f}")
            self._reply(f"E{self.elevation:.3f}")
            self._reply(f"T{self.delay}")
            self._reply("D")
        elif cmd.startswith("T"):
            self.delay = _atoi(cmd[1:])
            self._reply(f"T{self.delay}")
        elif cmd.startswith("O"):
            self.azimuth, self.elevation = HOME_AZ, HOME_EL
            self._reply("O")
        elif len(cmd) < 4:
            self._reply(f"ERR:short buf={cmd}")
        else:
            self._motion(cmd.ljust(10, "\0"))

    def _motion(self, cmd: str):
        az_dir, el_dir = cmd[0], cmd[5]
        steps_az, steps_el = _atoi(cmd[1:5]), _atoi(cmd[6:10])
        if az_dir not in "+-":
            self._reply("ERR:dir")
            return
        stopped = self._step_axis("A", az_dir, steps_az)
        if el_dir not in "+-":
            self._reply("ERR:dir")      # azimuth already moved; no D (like main.c)
            return
        if not stopped:
            stopped = self._step_axis("E", el_dir, steps_el)
        if not stopped:
            self._reply("D")

    def _step_axis(self, axis: str, direction: str, steps: int) -> bool:
        sign = 1 if direction == "+" else -1
        for _ in range(steps):
            if not self.is_open:
                return True
            if self._stop_requested():
                self._reply("S")
                return True
            time.sleep(self.step_time if self.step_time is not None
                       else (2 * self.delay + UART_POLL_MS) / 1000)
            if axis == "A":
                self.azimuth = (self.azimuth + sign * AZ_ANGLE_PER_STEP) % 360
                self._reply(f"A{self.azimuth:.3f}")
            else:
                self.elevation += sign * EL_ANGLE_PER_STEP
                self._reply(f"E{self.elevation:.3f}")
        return False

    def _stop_requested(self) -> bool:
        # The firmware reads at most one byte per step and discards anything but 'S'
        try:
            return chr(self._rx.get_nowait()) == "S"
        except queue.Empty:
            return False
