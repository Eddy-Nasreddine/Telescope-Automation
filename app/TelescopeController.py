from GpsUartReceiver import GpsUartReceiver
from CelestialObject import CelestialObject
import threading
from time import sleep
import serial

class TelescopeController():    
    def __init__(
        self, 
        elevation_controller, 
        azimuth_controller,     
        el_driver_teeth: int,
        el_driven_teeth: int,
        az_driver_teeth: int,
        az_driven_teeth: int,
    ):
        self.elevation_controller = elevation_controller
        self.azimuth_controller = azimuth_controller
        self.el_driver_teeth = el_driver_teeth
        self.el_driven_teeth = el_driven_teeth
        self.az_driver_teeth = az_driver_teeth
        self.az_driven_teeth = az_driven_teeth
        self.current_el = 0
        self.current_az = 0
        self.error_el = 0
        self.error_az = 0
        self.pulse_delay = 0
        self.moving = False
        self.sys_ready = False
        self.calibrating = False
        self.calibration_obj = CelestialObject("polaris")
        self.ser = serial.Serial('/dev/ttyAMA0', 115200, timeout=1)
        self.listener_thread = threading.Thread(target=self._listen, daemon=True)
        self.listener_thread.start()
        self.handshake()
        self.GpsUartReceiver = GpsUartReceiver()
        # self.GpsUartReceiver.start() uncomment when ready 

    # Altitude angle per motor step (after microstepping + gear ratio)
    @property
    def get_alt_angle(self) -> float:    
        gear_ratio = self.el_driver_teeth / self.el_driven_teeth
        return self.elevation_controller.get_angle_per_step * gear_ratio
        
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
            try:
                if (line):
                    print("Received:", line)
                    if line.startswith("A"):
                        self.current_az = float(line[1:])
                        self.moving = True
                    elif line.startswith("E") and len(line) > 1 and not line.startswith("ERR"):
                        self.current_el = float(line[1:])
                        self.moving = True
                    elif line.startswith("S"):
                        self.moving = False
                    elif line.startswith("D"):
                        self.moving = False
                        print("<TelescopeController>:: System reached target position.")
                    elif line.startswith("O"):
                        print("<TelescopeController>:: System origin has been reset.")
                        self.current_az = 90
                        self.current_el = 90
                    elif line.startswith("R"):
                        self.sys_ready = True
                        print("<TelescopeController>:: Handshake Established")
                    elif line.startswith("T"):
                        self.pulse_delay = int(line[1:])
            except Exception as e:
                print(f"<TelescopeController>:: Sys Error, {e}")


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
        if diff > 180:
            diff -= 360
        elif diff < -180:
            diff += 360
        steps = round(abs(diff) / step_angle)
        direction = "+" if diff > 0 else "-"
        return direction, steps

    def _calc_el(self, target_alt: float) -> tuple[str, int]:
        step_angle = self.get_alt_angle
        diff = target_alt - self.current_el
        steps = round(abs(diff) / step_angle)
        direction = "+" if diff > 0 else "-"
        return direction, steps
    
    def reset_origin(self):
        self._send("O")
        print("<TelescopeController>:: Command Sent: O")

    def move_to(self, target:tuple):      
        el_dir, el_steps = self._calc_el(target[0])
        az_dir, az_steps = self._calc_az(target[1])
        az_cmd = self.azimuth_controller.build_command(az_dir, az_steps)
        el_cmd = self.elevation_controller.build_command(el_dir, el_steps)
        full_cmd = az_cmd + el_cmd
        print(f"<TelescopeController>:: Command Sent: Azimuth[{az_steps}{az_dir}]:Elevation[{el_steps}{el_dir}]")
        self._send(full_cmd)
        
    def calibrate(self):
        print(f"<TelescopeController>:: Calibration process has started...")
        self.calibrating = True
        my_coords = self.GpsUartReceiver.get_coords()
        self.move_to_object(self.calibration_obj)
        # self.move_to((85,85))
                
    def finish_calibration(self):
        my_coords = self.GpsUartReceiver.get_coords()
        cal_obj_location = self.calibration_obj.get_astrometric_coords(my_coords)
        el = cal_obj_location[0].degrees
        az = cal_obj_location[1].degrees
        print(f"EL: {el}, AZ: {az}")
        self.error_az = self.current_az - az
        self.error_el = self.current_el - el
        self.calibrating = False
        
    def move_to_object(self, CelestialObject):
        coords = self.GpsUartReceiver.get_coords()
        object_location = CelestialObject.get_astrometric_coords(coords)
        angle = (object_location[0].degrees, object_location[1].degrees)
        print(f"<TelescopeController>:: Moving to celestial object {CelestialObject.name} at Elevation: {angle[0]:.3f}° | Azimuth:  {angle[1]:.3f}°")
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
        #TODO
        object_location = CelestialObject.get_astrometric_coords()
        angle = Angle(object_location[0].degrees, 360-object_location[1].degrees)
        print(f"<TelescopeController>:: Tracking has begin, moving to {CelestialObject.name} at, Elevation: {angle.alt:.3f}° | Azimuth:  {angle.az:.3f}°")
        self.move_to(angle)
        print(f"<TelescopeController>:: Reached {CelestialObject.name} now will begin live tracking")
        while True:            
            object_location = CelestialObject.get_astrometric_coords()
            angle = Angle(object_location[0].degrees, 360-object_location[1].degrees)
            self.move_to(angle)
            sleep(0.5)
        
        print("<TelescopeController>:: tracking stopped")
        
