#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2026 Linsheng Yin, Heng Quan, Bojin Li, Yunpeng Din, Penghan Chen
# File purpose: Pure TCRT5000 infrared proximity detection logic without GPIO I/O.
"""TCRT5000 infrared reflection sensor proximity detector."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TCRT5000Reading:
    """One TCRT5000 sample.

    Use ``digital_value`` for module DO output. Use ``analog_value`` only when a
    future adapter reads the AO pin through an ADC.
    """

    digital_value: bool | None = None
    analog_value: float | None = None


@dataclass(frozen=True)
class TCRT5000Config:
    """Thresholds and debounce settings for proximity detection."""

    active_low: bool = True
    analog_threshold: float = 0.5
    analog_trigger_below_threshold: bool = True
    consecutive_trigger_samples: int = 2
    consecutive_clear_samples: int = 3


@dataclass(frozen=True)
class TCRT5000Status:
    """Result of one TCRT5000 detector update."""

    detected: bool
    triggered_now: bool
    cleared_now: bool
    raw_active: bool
    reason: str


class TCRT5000Detector:
    """Debounced infrared proximity detector."""

    def __init__(self, config: TCRT5000Config | None = None) -> None:
        self.config = config or TCRT5000Config()
        self._detected = False
        self._trigger_count = 0
        self._clear_count = 0

    def update(self, reading: TCRT5000Reading) -> TCRT5000Status:
        """Update detector state from one digital or analog sample."""

        raw_active, reason = self._is_raw_active(reading)
        triggered_now = False
        cleared_now = False

        if raw_active:
            self._trigger_count += 1
            self._clear_count = 0
            if not self._detected and self._trigger_count >= self.config.consecutive_trigger_samples:
                self._detected = True
                triggered_now = True
        else:
            self._trigger_count = 0
            if self._detected:
                self._clear_count += 1
                if self._clear_count >= self.config.consecutive_clear_samples:
                    self._detected = False
                    cleared_now = True

        return TCRT5000Status(
            detected=self._detected,
            triggered_now=triggered_now,
            cleared_now=cleared_now,
            raw_active=raw_active,
            reason=reason,
        )

    def _is_raw_active(self, reading: TCRT5000Reading) -> tuple[bool, str]:
        if reading.digital_value is not None:
            active = not reading.digital_value if self.config.active_low else reading.digital_value
            return active, "digital"

        if reading.analog_value is None:
            raise ValueError("TCRT5000Reading requires digital_value or analog_value")

        if self.config.analog_trigger_below_threshold:
            return reading.analog_value <= self.config.analog_threshold, "analog_below_threshold"
        return reading.analog_value >= self.config.analog_threshold, "analog_above_threshold"
