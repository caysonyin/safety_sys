#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from cv_safety_sys.alarm import AlarmLevel, AlarmManager
from cv_safety_sys.devices import (
    MPU6050Config,
    MPU6050Detector,
    MPU6050Reading,
    SensorAlarmController,
    TCRT5000Config,
    TCRT5000Detector,
    TCRT5000Reading,
)


class FakePublisher:
    enabled = True
    connected = True
    status = "test"
    last_error = None

    def __init__(self) -> None:
        self.events = []

    def publish(self, event):
        self.events.append(event)
        return True


class TCRT5000DetectorTests(unittest.TestCase):
    def test_active_low_digital_signal_triggers_after_debounce(self) -> None:
        detector = TCRT5000Detector(
            TCRT5000Config(active_low=True, consecutive_trigger_samples=2)
        )

        first = detector.update(TCRT5000Reading(digital_value=False))
        second = detector.update(TCRT5000Reading(digital_value=False))

        self.assertFalse(first.detected)
        self.assertTrue(second.detected)
        self.assertTrue(second.triggered_now)
        self.assertEqual(second.reason, "digital")

    def test_analog_threshold_can_trigger_above_threshold(self) -> None:
        detector = TCRT5000Detector(
            TCRT5000Config(
                analog_threshold=0.7,
                analog_trigger_below_threshold=False,
                consecutive_trigger_samples=1,
            )
        )

        status = detector.update(TCRT5000Reading(analog_value=0.8))

        self.assertTrue(status.detected)
        self.assertTrue(status.triggered_now)
        self.assertEqual(status.reason, "analog_above_threshold")

    def test_missing_reading_value_is_rejected(self) -> None:
        detector = TCRT5000Detector()

        with self.assertRaises(ValueError):
            detector.update(TCRT5000Reading())


class MPU6050DetectorTests(unittest.TestCase):
    def test_acceleration_delta_triggers_movement_after_debounce(self) -> None:
        detector = MPU6050Detector(
            MPU6050Config(
                acceleration_delta_threshold_g=0.25,
                gyro_threshold_dps=100.0,
                consecutive_trigger_samples=2,
            )
        )
        detector.calibrate(MPU6050Reading(0.0, 0.0, 1.0))

        first = detector.update(MPU6050Reading(0.0, 0.0, 1.35))
        second = detector.update(MPU6050Reading(0.0, 0.0, 1.35))

        self.assertFalse(first.moved)
        self.assertTrue(second.moved)
        self.assertTrue(second.triggered_now)
        self.assertEqual(second.reason, "acceleration_delta")

    def test_gyro_speed_triggers_movement(self) -> None:
        detector = MPU6050Detector(
            MPU6050Config(
                acceleration_delta_threshold_g=0.8,
                gyro_threshold_dps=50.0,
                consecutive_trigger_samples=1,
            )
        )
        detector.calibrate(MPU6050Reading(0.0, 0.0, 1.0))

        status = detector.update(MPU6050Reading(0.0, 0.0, 1.0, gyro_z_dps=60.0))

        self.assertTrue(status.moved)
        self.assertTrue(status.triggered_now)
        self.assertEqual(status.reason, "gyro_speed")

    def test_stable_samples_can_clear_movement_state(self) -> None:
        detector = MPU6050Detector(
            MPU6050Config(
                acceleration_delta_threshold_g=0.25,
                consecutive_trigger_samples=1,
                consecutive_clear_samples=2,
            )
        )
        detector.calibrate(MPU6050Reading(0.0, 0.0, 1.0))
        detector.update(MPU6050Reading(0.0, 0.0, 1.4))

        first_clear = detector.update(MPU6050Reading(0.0, 0.0, 1.0))
        second_clear = detector.update(MPU6050Reading(0.0, 0.0, 1.0))

        self.assertTrue(first_clear.moved)
        self.assertFalse(second_clear.moved)
        self.assertTrue(second_clear.cleared_now)


class SensorAlarmControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.publisher = FakePublisher()
        self.alarm_manager = AlarmManager(
            self.publisher,
            clock=lambda: datetime(2026, 5, 23, 8, 0, tzinfo=timezone.utc),
        )

    def test_ir_detection_emits_level_one_alarm(self) -> None:
        controller = SensorAlarmController(
            self.alarm_manager,
            ir_detector=TCRT5000Detector(
                TCRT5000Config(active_low=True, consecutive_trigger_samples=1)
            ),
        )

        state = controller.update(ir_reading=TCRT5000Reading(digital_value=False))

        self.assertIsNotNone(state.alarm_event)
        self.assertEqual(state.alarm_event.alarm_level, AlarmLevel.IR)
        self.assertTrue(state.alarm_event.ir_status)
        self.assertIn("TCRT5000", state.alarm_event.message)

    def test_imu_detection_overrides_existing_ir_alarm(self) -> None:
        controller = SensorAlarmController(
            self.alarm_manager,
            ir_detector=TCRT5000Detector(
                TCRT5000Config(active_low=True, consecutive_trigger_samples=1)
            ),
            imu_detector=MPU6050Detector(
                MPU6050Config(
                    acceleration_delta_threshold_g=0.25,
                    consecutive_trigger_samples=1,
                )
            ),
        )
        controller.calibrate_imu(MPU6050Reading(0.0, 0.0, 1.0))
        controller.update(ir_reading=TCRT5000Reading(digital_value=False))

        state = controller.update(imu_reading=MPU6050Reading(0.0, 0.0, 1.4))

        self.assertIsNotNone(state.alarm_event)
        self.assertEqual(state.alarm_event.alarm_level, AlarmLevel.IMU)
        self.assertTrue(state.alarm_event.ir_status)
        self.assertTrue(state.alarm_event.imu_status)


if __name__ == "__main__":
    unittest.main()
