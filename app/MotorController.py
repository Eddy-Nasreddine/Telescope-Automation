class StepperMotor:
    def __init__(self, step_angle, micro_stepping, motor_id: str = ""):
        self.step_angle = step_angle
        self.micro_stepping = micro_stepping
        self.motor_id = motor_id

    def build_command(self, direction: str, steps: int) -> str:
        # The firmware reads exactly one sign and four digits per axis, and acts
        # on the azimuth half before it checks the elevation half, so a malformed
        # command must never leave the Pi.
        if direction not in ("+", "-"):
            raise ValueError(f"{self.motor_id or 'motor'}: invalid direction {direction!r}")
        if not isinstance(steps, int) or not 0 <= steps <= 9999:
            raise ValueError(f"{self.motor_id or 'motor'}: steps must be 0-9999, got {steps!r}")
        return f"{direction}{steps:04d}"

    # Degrees per motor step after microstepping (before any gearing)
    @property
    def angle_per_step(self) -> float:
        return self.step_angle * self.micro_stepping

    def __repr__(self):
        return f"StepperMotor({self.motor_id!r}, {self.step_angle}°, x{self.micro_stepping})"
