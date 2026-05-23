#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2026 Linsheng Yin, Heng Quan, Bojin Li, Yunpeng Din, Penghan Chen
# File purpose: Convert simulated/future hardware sensor states into alarm events.
"""Bridge GY-521 and TCRT5000 detector outputs into AlarmManager."""

from __future__ import annotations

from dataclasses import dataclass

from cv_safety_sys.alarm import AlarmEvent, AlarmManager
from cv_safety_sys.devices.mpu6050 import MPU6050Detector, MPU6050Reading, MPU6050Status
from cv_safety_sys.devices.tcrt5000 import TCRT5000Detector, TCRT5000Reading, TCRT5000Status


@dataclass(frozen=True)
class SensorAlarmState:
    """Combined state after processing one or both sensor samples."""

    ir_status: TCRT5000Status | None
    imu_status: MPU6050Status | None
    alarm_event: AlarmEvent | None


class SensorAlarmController:
    """Run sensor detectors and update the shared alarm state machine."""

    def __init__(
        self,
        alarm_manager: AlarmManager,
        *,
        ir_detector: TCRT5000Detector | None = None,
        imu_detector: MPU6050Detector | None = None,
    ) -> None:
        self.alarm_manager = alarm_manager
        self.ir_detector = ir_detector or TCRT5000Detector()
        self.imu_detector = imu_detector or MPU6050Detector()

    def calibrate_imu(self, reading: MPU6050Reading) -> None:
        self.imu_detector.calibrate(reading)

    def update(
        self,
        *,
        ir_reading: TCRT5000Reading | None = None,
        imu_reading: MPU6050Reading | None = None,
    ) -> SensorAlarmState:
        """Process available sensor samples and emit at most one alarm event."""

        ir_status = self.ir_detector.update(ir_reading) if ir_reading is not None else None
        imu_status = self.imu_detector.update(imu_reading) if imu_reading is not None else None

        alarm_event = None
        if imu_status and imu_status.triggered_now:
            alarm_event = self.alarm_manager.trigger_imu(
                f"MPU6050 movement detected ({imu_status.reason})"
            )
        elif ir_status and ir_status.triggered_now:
            alarm_event = self.alarm_manager.trigger_ir(
                f"TCRT5000 proximity detected ({ir_status.reason})"
            )

        return SensorAlarmState(
            ir_status=ir_status,
            imu_status=imu_status,
            alarm_event=alarm_event,
        )
