from motor_controller import MotorController
from Angle import Angle 
from time import sleep

class TelescopeController():    
    def __init__(
        self, 
        altitude_controller:MotorController, 
        azimuth_controller:MotorController,     
        alt_driver_teeth: int,
        alt_driven_teeth: int,
        az_driver_teeth: int,
        az_driven_teeth: int
    ):
        self.altitude_controller = altitude_controller
        self.azimuth_controller = azimuth_controller
        self.alt_driver_teeth = alt_driver_teeth
        self.alt_driven_teeth = alt_driven_teeth
        self.az_driver_teeth = az_driver_teeth
        self.az_driven_teeth = az_driven_teeth
        self.current_alt = 90
        self.current_az = 90
        
    # Altitude angle per motor step (after microstepping + gear ratio)
    def get_alt_angle(self) -> float:    
        gear_ratio = self.alt_driver_teeth / self.alt_driven_teeth
        return self.altitude_controller.get_angle_per_step() * gear_ratio
        
    # Azimuth angle per motor step (after microstepping + gear ratio)
    def get_az_angle(self) -> float:
        gear_ratio = self.az_driver_teeth / self.az_driven_teeth
        return self.azimuth_controller.get_angle_per_step() * gear_ratio
    
    def move_az_to(self, target_az: float):
        step_angle = self.get_az_angle()
        diff = target_az - self.current_az
        steps = round(abs(diff) / step_angle)

        if diff < 0:
            for _ in range(steps):
                self.azimuth_controller.step_clockwise()
        elif diff > 0:
            for _ in range(steps):
                self.azimuth_controller.step_counterclockwise()

        self.current_az = target_az
    def move_alt_to(self, target_alt: float):
        step_angle = self.get_alt_angle()
        diff = target_alt - self.current_alt
        steps = round(abs(diff) / step_angle)

        if diff < 0:
            for _ in range(steps):
                self.altitude_controller.step_clockwise()
        elif diff > 0:
            for _ in range(steps):
                self.altitude_controller.step_counterclockwise()

        self.current_alt = target_alt
    
    def move_to(self, target:Angle):
        self.move_alt_to(target.alt)
        self.move_az_to(target.az)
    
    def testy():
        time.sleep(10)
        
        
    
# NEMA17_Motor = MotorController(17, 27, 0.01, 1.8, 1/2)
# NEMA23_Motor = MotorController(23, 24, 0.01, 1.8, 1/2)
# a = TelescopeController(NEMA17_Motor, NEMA23_Motor, 12, 120, 30, 200)

# print(a.get_alt_angle())
# print(a.get_az_angle())
