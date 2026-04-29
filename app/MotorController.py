import RPi.GPIO as GPIO
from time import sleep


class StepperMotor:
    def __init__(self, step_angle, micro_stepping, motor_id:str=""):
        self.step_angle = step_angle
        self.micro_stepping = micro_stepping
        self.motor_id = motor_id
        
    def build_command(self, direction:str, steps:int) -> str:
        return f"{direction}{steps:04d}"

    @property
    def get_angle_per_step(self) -> float:
        return self.step_angle*self.micro_stepping
