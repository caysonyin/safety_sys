"""Device-side sensor logic for future hardware integration."""

from cv_safety_sys.devices.controller import SensorAlarmController, SensorAlarmState
from cv_safety_sys.devices.mpu6050 import (
    MPU6050Config,
    MPU6050Detector,
    MPU6050Reading,
    MPU6050Status,
)
from cv_safety_sys.devices.tcrt5000 import (
    TCRT5000Config,
    TCRT5000Detector,
    TCRT5000Reading,
    TCRT5000Status,
)

__all__ = [
    "MPU6050Config",
    "MPU6050Detector",
    "MPU6050Reading",
    "MPU6050Status",
    "SensorAlarmController",
    "SensorAlarmState",
    "TCRT5000Config",
    "TCRT5000Detector",
    "TCRT5000Reading",
    "TCRT5000Status",
]
