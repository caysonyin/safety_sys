#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from cv_safety_sys.alarm import AlarmLevel, AlarmManager


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


class AlarmManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 5, 23, 7, 30, tzinfo=timezone.utc)
        self.publisher = FakePublisher()
        self.manager = AlarmManager(self.publisher, clock=lambda: self.now)

    def test_alarm_priority_prefers_imu_over_vision_and_ir(self) -> None:
        ir_event = self.manager.trigger_ir()
        self.assertIsNotNone(ir_event)
        self.assertEqual(ir_event.alarm_level, AlarmLevel.IR)

        vision_event = self.manager.update_vision(True, "vision danger detected")
        self.assertIsNotNone(vision_event)
        self.assertEqual(vision_event.alarm_level, AlarmLevel.VISION)

        imu_event = self.manager.trigger_imu()
        self.assertIsNotNone(imu_event)
        self.assertEqual(imu_event.alarm_level, AlarmLevel.IMU)
        self.assertEqual(self.manager.current_level, AlarmLevel.IMU)

    def test_same_alarm_state_is_not_published_twice(self) -> None:
        self.assertIsNotNone(self.manager.trigger_ir())
        self.assertIsNone(self.manager.trigger_ir())
        self.assertEqual(len(self.publisher.events), 1)

    def test_initial_safe_vision_clear_is_not_published(self) -> None:
        self.assertIsNone(self.manager.update_vision(False))
        self.assertEqual(len(self.publisher.events), 0)

    def test_same_state_with_different_message_is_not_published(self) -> None:
        self.assertIsNotNone(self.manager.update_vision(True, "first risk"))
        self.assertIsNone(self.manager.update_vision(True, "second risk"))
        self.assertEqual(len(self.publisher.events), 1)

    def test_restore_safe_clears_all_signal_flags(self) -> None:
        self.manager.trigger_ir()
        self.manager.update_vision(True, "vision danger detected")
        self.manager.trigger_imu()

        event = self.manager.restore_safe()

        self.assertIsNotNone(event)
        self.assertEqual(event.alarm_level, AlarmLevel.SAFE)
        self.assertFalse(event.ir_status)
        self.assertFalse(event.vision_status)
        self.assertFalse(event.imu_status)


if __name__ == "__main__":
    unittest.main()
