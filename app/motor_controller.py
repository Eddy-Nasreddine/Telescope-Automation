import RPi.GPIO as GPIO
from time import sleep

class MotorController:
    def __init__(self, pul, dir, delay, step_angle, micro_stepping):
        self.PUL = pul
        self.DIR = dir
        self.CW = 1
        self.CCW = 0
        self.step_angle = step_angle
        self.micro_stepping = micro_stepping
        self.delay = delay

        # GPIO.setmode(GPIO.BCM)
        # GPIO.setup(self.PUL, GPIO.OUT)
        # GPIO.setup(self.DIR, GPIO.OUT)

        # self.direction = self.CW
        # GPIO.output(self.DIR, self.direction)

    def set_direction(self, direction):
        self.direction = direction
        GPIO.output(self.DIR, direction)

    def step(self):
        GPIO.output(self.PUL, GPIO.HIGH)
        sleep(self.delay)
        GPIO.output(self.PUL, GPIO.LOW)
        sleep(self.delay)

    def step_clockwise(self):
        self.set_direction(self.CW)
        self.step()

    def step_counterclockwise(self):
        self.set_direction(self.CCW)
        self.step()

    def get_angle_per_step(self) -> float:
        return self.step_angle*self.micro_stepping
