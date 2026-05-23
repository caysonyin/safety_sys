#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2026 Linsheng Yin, Heng Quan, Bojin Li, Yunpeng Din, Penghan Chen
# File purpose: Pure MPU6050/GY-521 movement detection logic without hardware I/O.
"""MPU6050/GY-521 six-axis movement detector."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class MPU6050Reading:
    """One normalized MPU6050 sample.

    Acceleration uses g units and angular speed uses degrees per second.
    Hardware adapters should convert raw register values before creating this
    structure.
    """

    accel_x_g: float
    accel_y_g: float
    accel_z_g: float
    gyro_x_dps: float = 0.0
    gyro_y_dps: float = 0.0
    gyro_z_dps: float = 0.0

    @property
    def acceleration_magnitude_g(self) -> float:
        return math.sqrt(
            self.accel_x_g**2 + self.accel_y_g**2 + self.accel_z_g**2
        )

    @property
    def gyro_magnitude_dps(self) -> float:
        return math.sqrt(
            self.gyro_x_dps**2 + self.gyro_y_dps**2 + self.gyro_z_dps**2
        )


@dataclass(frozen=True)
class MPU6050Config:
    """Thresholds for detecting relic movement."""

    acceleration_delta_threshold_g: float = 0.35
    gyro_threshold_dps: float = 80.0
    consecutive_trigger_samples: int = 2
    consecutive_clear_samples: int = 5


@dataclass(frozen=True)
class MPU6050Status:
    """Result of one MPU6050 detector update."""

    moved: bool
    triggered_now: bool
    cleared_now: bool
    acceleration_magnitude_g: float
    acceleration_delta_g: float
    gyro_magnitude_dps: float
    reason: str


class MPU6050Detector:
    """Detect whether the protected exhibit appears to have moved."""

    def __init__(self, config: MPU6050Config | None = None) -> None:
        self.config = config or MPU6050Config()
        self._baseline_accel_g: float | None = None
        self._moved = False
        self._trigger_count = 0
        self._clear_count = 0

    def calibrate(self, reading: MPU6050Reading) -> None:
        """Set the current acceleration magnitude as the resting baseline."""

        self._baseline_accel_g = reading.acceleration_magnitude_g
        self._moved = False
        self._trigger_count = 0
        self._clear_count = 0

    def update(self, reading: MPU6050Reading) -> MPU6050Status:
        """Update detector state from one normalized sample."""

        if self._baseline_accel_g is None:
            self.calibrate(reading)

        acceleration = reading.acceleration_magnitude_g
        baseline = self._baseline_accel_g if self._baseline_accel_g is not None else acceleration
        acceleration_delta = abs(acceleration - baseline)
        gyro = reading.gyro_magnitude_dps

        acceleration_hit = acceleration_delta >= self.config.acceleration_delta_threshold_g
        gyro_hit = gyro >= self.config.gyro_threshold_dps
        candidate = acceleration_hit or gyro_hit
        reason = "stable"
        if acceleration_hit and gyro_hit:
            reason = "acceleration_and_gyro"
        elif acceleration_hit:
            reason = "acceleration_delta"
        elif gyro_hit:
            reason = "gyro_speed"

        triggered_now = False
        cleared_now = False
        if candidate:
            self._trigger_count += 1
            self._clear_count = 0
            if not self._moved and self._trigger_count >= self.config.consecutive_trigger_samples:
                self._moved = True
                triggered_now = True
        else:
            self._trigger_count = 0
            if self._moved:
                self._clear_count += 1
                if self._clear_count >= self.config.consecutive_clear_samples:
                    self._moved = False
                    cleared_now = True

        return MPU6050Status(
            moved=self._moved,
            triggered_now=triggered_now,
            cleared_now=cleared_now,
            acceleration_magnitude_g=acceleration,
            acceleration_delta_g=acceleration_delta,
            gyro_magnitude_dps=gyro,
            reason=reason,
        )
