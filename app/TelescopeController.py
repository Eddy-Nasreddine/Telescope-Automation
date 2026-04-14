from Angle import Angle 
import threading
from time import sleep

class TelescopeController():    
    def __init__(
        self, 
        altitude_controller, 
        azimuth_controller,     
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
        self.current_az = 100
        self.stop_event = threading.Event()

        
    # Altitude angle per motor step (after microstepping + gear ratio)
    def get_alt_angle(self) -> float:    
        gear_ratio = self.alt_driver_teeth / self.alt_driven_teeth
        return self.altitude_controller.get_angle_per_step() * gear_ratio
        
    # Azimuth angle per motor step (after microstepping + gear ratio)
    def get_az_angle(self) -> float:
        gear_ratio = self.az_driver_teeth / self.az_driven_teeth
        return self.azimuth_controller.get_angle_per_step() * gear_ratio
    
    def stop(self):
        self.stop_event.set()

    def clear_stop(self):
        self.stop_event.clear()
    
    def move_az_to(self, target_az: float):
        step_angle = self.get_az_angle()
        diff = target_az - self.current_az
        steps = round(abs(diff) / step_angle)

        if diff < 0:
            for _ in range(steps):
                if self.stop_event.is_set():
                    return
                self.azimuth_controller.step_clockwise()
                self.current_az -= step_angle

        elif diff > 0:
            for _ in range(steps):
                if self.stop_event.is_set():
                    return
                self.azimuth_controller.step_counterclockwise()
                self.current_az += step_angle

    def move_alt_to(self, target_alt: float):
        step_angle = self.get_alt_angle()
        diff = target_alt - self.current_alt
        steps = round(abs(diff) / step_angle)

        if diff < 0:
            for _ in range(steps):
                if self.stop_event.is_set():
                    return
                self.altitude_controller.step_clockwise()
                self.current_alt -= step_angle

        elif diff > 0:
            for _ in range(steps):
                if self.stop_event.is_set():
                    return
                self.altitude_controller.step_counterclockwise()
                self.current_alt += step_angle
    
    def move_to(self, target:Angle):
        self.clear_stop()

        alt_thread = threading.Thread(
            target=self.move_alt_to,
            args=(target.alt,)
        )
        
        az_thread = threading.Thread(
            target=self.move_az_to,
            args=(target.az,)
        )
        
        print("both threads have started")
        alt_thread.start()
        az_thread.start()

        alt_thread.join()
        az_thread.join()
        print("both threads have ended")
        
    def track_object(self, CelestialObject):
        object_location = CelestialObject.get_astrometric_coords()
        angle = Angle(object_location[0].degrees, 360-object_location[1].degrees)
        print(f"Tracking has begin, moving to {CelestialObject.name} at, Altitude: {angle.alt:.3f}° | Azimuth:  {angle.az:.3f}°")
        self.move_to(angle)
        print(f"Reached {CelestialObject.name} now will begin live tracking")
        while not self.stop_event.is_set():            
            object_location = CelestialObject.get_astrometric_coords()
            angle = Angle(object_location[0].degrees, 360-object_location[1].degrees)
            self.move_to(angle)
            sleep(0.5)
        
        print("tracking stopped")

    def start_tracking(self, celestial_object):
        self.clear_stop()

        self.tracking_thread = threading.Thread(
            target=self.track_object,
            args=(celestial_object,),
            daemon=True  
        )
        self.tracking_thread.start()
        
        
