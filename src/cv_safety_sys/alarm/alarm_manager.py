#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2026 Linsheng Yin, Heng Quan, Bojin Li, Yunpeng Din, Penghan Chen
# File purpose: Manage local three-level alarm state and cloud publish deduplication.
"""Three-level alarm state machine for local-first theft monitoring."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import IntEnum
from typing import Callable, Protocol


class AlarmLevel(IntEnum):
    """Alarm priority used by the local demo and Huawei Cloud payload."""

    SAFE = 0
    IR = 1
    VISION = 2
    IMU = 3


@dataclass(frozen=True)
class AlarmEvent:
    """One alarm state report."""

    alarm_level: AlarmLevel
    ir_status: bool
    vision_status: bool
    imu_status: bool
    source: str
    message: str
    event_time: datetime


@dataclass(frozen=True)
class AlarmSnapshot:
    """User-facing alarm and publisher status."""

    alarm_level: AlarmLevel
    ir_status: bool
    vision_status: bool
    imu_status: bool
    source: str
    message: str
    event_time: datetime | None
    last_publish_time: datetime | None
    mqtt_enabled: bool
    mqtt_connected: bool
    mqtt_status: str
    mqtt_last_error: str | None


class AlarmPublisher(Protocol):
    """Minimal publisher interface used by AlarmManager."""

    enabled: bool
    connected: bool
    status: str
    last_error: str | None

    def publish(self, event: AlarmEvent) -> bool:
        """Publish one alarm event."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AlarmManager:
    """Track IR, vision, and IMU signals and publish state changes."""

    def __init__(
        self,
        publisher: AlarmPublisher | None = None,
        *,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self.publisher = publisher
        self._clock = clock
        self._ir_status = False
        self._vision_status = False
        self._imu_status = False
        self._source = "startup"
        self._message = "system safe"
        self._event_time: datetime | None = None
        self._last_signature: tuple[int, bool, bool, bool] | None = (
            int(AlarmLevel.SAFE),
            False,
            False,
            False,
        )
        self._last_publish_time: datetime | None = None

    def trigger_ir(self, message: str = "infrared proximity detected") -> AlarmEvent | None:
        self._ir_status = True
        return self._emit_if_changed("ir", message)

    def trigger_imu(self, message: str = "imu movement detected") -> AlarmEvent | None:
        self._imu_status = True
        return self._emit_if_changed("imu", message)

    def restore_safe(self, message: str = "system restored to safe state") -> AlarmEvent | None:
        self._ir_status = False
        self._vision_status = False
        self._imu_status = False
        return self._emit_if_changed("manual", message, force=True)

    def update_vision(self, active: bool, message: str = "vision danger detected") -> AlarmEvent | None:
        self._vision_status = active
        source = "vision" if active else "vision_clear"
        safe_message = "vision danger cleared"
        return self._emit_if_changed(source, message if active else safe_message)

    def resend_current(self, message: str = "manual resend current alarm state") -> AlarmEvent:
        return self._emit("manual", message, force=True)

    def close(self) -> None:
        if self.publisher and hasattr(self.publisher, "close"):
            self.publisher.close()

    def snapshot(self) -> AlarmSnapshot:
        publisher = self.publisher
        return AlarmSnapshot(
            alarm_level=self.current_level,
            ir_status=self._ir_status,
            vision_status=self._vision_status,
            imu_status=self._imu_status,
            source=self._source,
            message=self._message,
            event_time=self._event_time,
            last_publish_time=self._last_publish_time,
            mqtt_enabled=bool(publisher and publisher.enabled),
            mqtt_connected=bool(publisher and publisher.connected),
            mqtt_status=publisher.status if publisher else "disabled",
            mqtt_last_error=publisher.last_error if publisher else None,
        )

    @property
    def current_level(self) -> AlarmLevel:
        if self._imu_status:
            return AlarmLevel.IMU
        if self._vision_status:
            return AlarmLevel.VISION
        if self._ir_status:
            return AlarmLevel.IR
        return AlarmLevel.SAFE

    def _emit_if_changed(self, source: str, message: str, *, force: bool = False) -> AlarmEvent | None:
        level = self.current_level
        signature = (int(level), self._ir_status, self._vision_status, self._imu_status)
        if not force and signature == self._last_signature:
            return None
        return self._emit(source, message, force=force)

    def _emit(self, source: str, message: str, *, force: bool = False) -> AlarmEvent:
        event = AlarmEvent(
            alarm_level=self.current_level,
            ir_status=self._ir_status,
            vision_status=self._vision_status,
            imu_status=self._imu_status,
            source=source,
            message=message,
            event_time=self._clock(),
        )
        self._source = source
        self._message = message
        self._event_time = event.event_time
        self._last_signature = (
            int(event.alarm_level),
            event.ir_status,
            event.vision_status,
            event.imu_status,
        )
        if self._publish(event):
            self._last_publish_time = event.event_time
        return event

    def _publish(self, event: AlarmEvent) -> bool:
        if not self.publisher or not self.publisher.enabled:
            return False
        return self.publisher.publish(event)
