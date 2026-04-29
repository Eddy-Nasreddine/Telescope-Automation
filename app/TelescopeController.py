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
        self.moving = False
        self.ser = serial.Serial('/dev/ttyAMA0', 115200, timeout=1)
        self.listener_thread = threading.Thread(target=self._listen, daemon=True)
        self.listener_thread.start()
        
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

    def _listen(self):
        print("UART Listener Has Begun...")
        while True:
            line = self.ser.readline().decode().strip()
            if (line):
                # print("Received:", line)
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

                
    def stop(self):
        self.ser.write(("S" + "\n").encode())
        print("Command Sent: ", "S")
        
    def _calc_az(self, target_az: float) -> tuple[str, int]:
        step_angle = self.get_az_angle
        diff = target_az - self.current_az
        steps = round(abs(diff) / step_angle)
        direction = "+" if diff < 0 else "-"
        print("AZIMUTH: ", steps)
        return direction, steps

    def _calc_alt(self, target_alt: float) -> tuple[str, int]:
        step_angle = self.get_alt_angle
        diff = target_alt - self.current_alt
        steps = round(abs(diff) / step_angle)
        direction = "+" if diff < 0 else "-"
        print("Altitude: ", steps)
        return direction, steps

    def move_to(self, target:Angle):        
        az_dir, az_steps = self._calc_az(target.az)
        alt_dir, alt_steps = self._calc_alt(target.alt)
        az_cmd = self.azimuth_controller.build_command(az_dir, az_steps)
        alt_cmd = self.altitude_controller.build_command(alt_dir, alt_steps)
        full_cmd = az_cmd + alt_cmd + "\n" 
        print(f"Command Sent: Azimuth[{az_steps}{az_dir}]:Elevation[{alt_steps}{alt_dir}]")
        self.ser.write(full_cmd.encode())
        
    def track_object(self, CelestialObject):
        object_location = CelestialObject.get_astrometric_coords()
        angle = Angle(object_location[0].degrees, 360-object_location[1].degrees)
        print(f"Tracking has begin, moving to {CelestialObject.name} at, Altitude: {angle.alt:.3f}° | Azimuth:  {angle.az:.3f}°")
        self.move_to(angle)
        print(f"Reached {CelestialObject.name} now will begin live tracking")
        while True:            
            object_location = CelestialObject.get_astrometric_coords()
            angle = Angle(object_location[0].degrees, 360-object_location[1].degrees)
            self.move_to(angle)
            sleep(0.5)
        
        print("tracking stopped")
        
