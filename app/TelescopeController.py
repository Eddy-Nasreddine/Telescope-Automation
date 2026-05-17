from Angle import Angle 
import threading
from time import sleep
import serial

class TelescopeController():    
    def __init__(
        self, 
        altitude_controller, 
        azimuth_controller,     
        alt_driver_teeth: int,
        alt_driven_teeth: int,
        az_driver_teeth: int,
        az_driven_teeth: int,
    ):
        self.altitude_controller = altitude_controller
        self.azimuth_controller = azimuth_controller
        self.alt_driver_teeth = alt_driver_teeth
        self.alt_driven_teeth = alt_driven_teeth
        self.az_driver_teeth = az_driver_teeth
        self.az_driven_teeth = az_driven_teeth
        self.current_alt = 0
        self.current_az = 0
        self.pulse_delay = 0
        self.moving = False
        self.sys_ready = False
        self.ser = serial.Serial('/dev/ttyAMA0', 115200, timeout=1)
        self.listener_thread = threading.Thread(target=self._listen, daemon=True)
        self.listener_thread.start()
        self.handshake()

    # Altitude angle per motor step (after microstepping + gear ratio)
    @property
    def get_alt_angle(self) -> float:    
        gear_ratio = self.alt_driver_teeth / self.alt_driven_teeth
        return self.altitude_controller.get_angle_per_step * gear_ratio
        
    # Azimuth angle per motor step (after microstepping + gear ratio)
    @property
    def get_az_angle(self) -> float:
        gear_ratio = self.az_driver_teeth / self.az_driven_teeth
        return self.azimuth_controller.get_angle_per_step * gear_ratio

    def _send(self, cmd: str):
        if self.moving:
            print("<TelescopeController>:: Busy, ignoring command")
            return
        self.ser.write((cmd+"\n").encode())
        
        
    def _listen(self):
        print("<TelescopeController>:: UART Listener Has Begun...")
        while True:
            line = self.ser.readline().decode().strip()
            if (line):
                print("Received:", line)
                if line.startswith("A"):
                    self.current_az = float(line[1:])
                    self.moving = True
                elif line.startswith("E"):
                    self.current_alt = float(line[1:])
                    self.moving = True
                elif line.startswith("S"):
                    self.moving = False
                elif line.startswith("D"):
                    self.moving = False
                    print("<TelescopeController>:: System reached target position")
                elif line.startswith("R"):
                    self.sys_ready = True
                    print("<TelescopeController>:: Handshake Established")
                elif line.startswith("T"):
                    self.pulse_delay = int(line[1:])

    def handshake(self):
        print("<TelescopeController>:: Sending Handshake...")
        self._send("R")
               
    def stop(self):
        self.ser.write(("S" + "\n").encode())
        self.moving = False
        print("Command Sent: ", "S")
        
    def set_pulse(self, delay: int):
        MAX_DELAY = 100
        MIN_DELAY = 10
        if (delay < MIN_DELAY) or (delay > MAX_DELAY):
            print(f"<TelescopeController>:: Invalid Delay Amount: {delay}")
            return
        cmd = f"T{delay}"
        self._send(cmd)
        print("<TelescopeController>:: Command Sent: ",cmd)

    def _calc_az(self, target_az: float) -> tuple[str, int]:
        step_angle = self.get_az_angle
        diff = target_az - self.current_az
        steps = round(abs(diff) / step_angle)
        direction = "+" if diff < 0 else "-"
        return direction, steps

    def _calc_alt(self, target_alt: float) -> tuple[str, int]:
        step_angle = self.get_alt_angle
        diff = target_alt - self.current_alt
        steps = round(abs(diff) / step_angle)
        direction = "+" if diff < 0 else "-"
        return direction, steps

    def move_to(self, target:Angle):        
        az_dir, az_steps = self._calc_az(target.az)
        alt_dir, alt_steps = self._calc_alt(target.alt)
        az_cmd = self.azimuth_controller.build_command(az_dir, az_steps)
        alt_cmd = self.altitude_controller.build_command(alt_dir, alt_steps)
        full_cmd = az_cmd + alt_cmd
        print(f"<TelescopeController>:: Command Sent: Azimuth[{az_steps}{az_dir}]:Elevation[{alt_steps}{alt_dir}]")
        self._send(full_cmd)
        
    def move_to_object(self, CelestialObject):
        object_location = CelestialObject.get_astrometric_coords()
        angle = Angle(object_location[0].degrees, 360-object_location[1].degrees)
        print(f"<TelescopeController>:: Moving to celestial object: {CelestialObject.name}")
        self.move_to(angle)
          
    def jog(self, direction: str):
        commands = {
            "left":  ("+4000-0000\n"),
            "right": ("-4000-0000\n"),
            "up":    ("+0000+4000\n"),
            "down":  ("+0000-4000\n"),
        }
        cmd = commands.get(direction)
        if cmd:
            print(f"<TelescopeController>:: Command Sent: {cmd}")
            self._send(cmd)
        
    def track_object(self, CelestialObject):
        object_location = CelestialObject.get_astrometric_coords()
        angle = Angle(object_location[0].degrees, 360-object_location[1].degrees)
        print(f"<TelescopeController>:: Tracking has begin, moving to {CelestialObject.name} at, Altitude: {angle.alt:.3f}° | Azimuth:  {angle.az:.3f}°")
        self.move_to(angle)
        print(f"<TelescopeController>:: Reached {CelestialObject.name} now will begin live tracking")
        while True:            
            object_location = CelestialObject.get_astrometric_coords()
            angle = Angle(object_location[0].degrees, 360-object_location[1].degrees)
            self.move_to(angle)
            sleep(0.5)
        
        print("<TelescopeController>:: tracking stopped")
        
