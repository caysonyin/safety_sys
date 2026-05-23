# Copyright (C) 2026 Linsheng Yin, Heng Quan, Bojin Li, Yunpeng Din, Penghan Chen
# File purpose:   init   module.
"""CV Safety System Python package."""

__all__ = ["IntegratedSafetyMonitor"]


def __getattr__(name: str):
    if name == "IntegratedSafetyMonitor":
        from .monitoring.integrated_monitor import IntegratedSafetyMonitor

        return IntegratedSafetyMonitor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
