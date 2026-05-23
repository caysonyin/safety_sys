#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2026 Linsheng Yin, Heng Quan, Bojin Li, Yunpeng Din, Penghan Chen
# File purpose: Publish alarm property reports to Huawei Cloud IoTDA over MQTT.
"""Huawei Cloud IoTDA MQTT property publisher."""

from __future__ import annotations

import json
import os
import ssl
import hmac
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from cv_safety_sys.alarm.alarm_manager import AlarmEvent

try:  # Optional dependency so local UI can run without MQTT enabled.
    import paho.mqtt.client as mqtt
except ImportError:  # pragma: no cover - exercised when dependency is absent
    mqtt = None  # type: ignore[assignment]


@dataclass(frozen=True)
class HuaweiIoTDAConfig:
    """Connection settings read from the local environment."""

    host: str
    device_id: str
    device_secret: str
    service_id: str = "Security"
    port: int = 1883
    client_id: str | None = None
    password: str | None = None
    use_tls: bool = False
    keepalive: int = 60

    @property
    def topic(self) -> str:
        return f"$oc/devices/{self.device_id}/sys/properties/report"

    def auth_timestamp(self, value: datetime | None = None) -> str:
        timestamp = value or datetime.now(timezone.utc)
        return timestamp.astimezone(timezone.utc).strftime("%Y%m%d%H")

    def resolved_client_id(self, value: datetime | None = None) -> str:
        if self.client_id:
            return self.client_id
        return f"{self.device_id}_0_0_{self.auth_timestamp(value)}"

    def resolved_password(self, value: datetime | None = None) -> str:
        if self.password:
            return self.password
        timestamp = self.auth_timestamp(value)
        return hmac.new(
            timestamp.encode("utf-8"),
            self.device_secret.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    @classmethod
    def from_env(cls) -> "HuaweiIoTDAConfig":
        host = os.getenv("HUAWEI_IOTDA_HOST", "").strip()
        device_id = os.getenv("HUAWEI_DEVICE_ID", "").strip()
        device_secret = os.getenv("HUAWEI_DEVICE_SECRET", "").strip()
        missing = [
            name
            for name, value in (
                ("HUAWEI_IOTDA_HOST", host),
                ("HUAWEI_DEVICE_ID", device_id),
                ("HUAWEI_DEVICE_SECRET", device_secret),
            )
            if not value
        ]
        if missing:
            raise ValueError(f"Missing Huawei IoTDA environment variables: {', '.join(missing)}")

        use_tls = os.getenv("HUAWEI_IOTDA_TLS", "0").strip().lower() in {"1", "true", "yes"}
        default_port = 8883 if use_tls else 1883
        return cls(
            host=host,
            device_id=device_id,
            device_secret=device_secret,
            service_id=os.getenv("HUAWEI_SERVICE_ID", "Security").strip() or "Security",
            port=int(os.getenv("HUAWEI_IOTDA_PORT", str(default_port))),
            client_id=os.getenv("HUAWEI_MQTT_CLIENT_ID", "").strip() or None,
            password=os.getenv("HUAWEI_MQTT_PASSWORD", "").strip() or None,
            use_tls=use_tls,
        )

    @classmethod
    def from_connection_key_file(cls, path: Path) -> "HuaweiIoTDAConfig":
        data = json.loads(path.read_text(encoding="utf-8"))
        protocol = str(data.get("protocol", "")).strip().upper()
        port = int(data.get("port", 8883 if protocol == "MQTTS" else 1883))
        return cls(
            host=str(data["hostname"]).strip(),
            device_id=str(data["username"]).strip(),
            device_secret="",
            port=port,
            client_id=str(data["clientId"]).strip(),
            password=str(data["password"]).strip(),
            use_tls=protocol == "MQTTS" or port == 8883,
        )


def format_huawei_event_time(value: datetime) -> str:
    """Format UTC event time as Huawei IoTDA-compatible ISO text."""

    utc_value = value.astimezone(timezone.utc)
    return utc_value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def build_property_payload(event: AlarmEvent, service_id: str = "Security") -> dict[str, Any]:
    """Build Huawei IoTDA device property report payload."""

    return {
        "services": [
            {
                "service_id": service_id,
                "properties": {
                    "alarm_level": int(event.alarm_level),
                    "ir_status": int(event.ir_status),
                    "vision_status": int(event.vision_status),
                    "imu_status": int(event.imu_status),
                    "message": event.message,
                },
                "event_time": format_huawei_event_time(event.event_time),
            }
        ]
    }


class HuaweiIoTDAPublisher:
    """Small MQTT publisher with lazy connection and UI-friendly status."""

    def __init__(
        self,
        config: HuaweiIoTDAConfig | None,
        *,
        enabled: bool = False,
        client_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.config = config
        self.enabled = enabled
        self.connected = False
        self.status = "disabled" if not enabled else "not connected"
        self.last_error: str | None = None
        self.last_payload: str | None = None
        self.last_topic: str | None = None
        self._client_factory = client_factory
        self._client: Any | None = None

        if self.enabled and self.config is None:
            self.status = "missing config"
            self.last_error = "Huawei IoTDA MQTT is enabled but config is missing."

    def publish(self, event: AlarmEvent) -> bool:
        if not self.enabled:
            self.status = "disabled"
            return False
        if self.config is None:
            self.status = "missing config"
            self.last_error = "Huawei IoTDA MQTT config is missing."
            return False

        payload = json.dumps(
            build_property_payload(event, self.config.service_id),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        self.last_payload = payload
        self.last_topic = self.config.topic

        try:
            client = self._ensure_client()
            result = client.publish(self.config.topic, payload, qos=1)
            rc = getattr(result, "rc", 0)
            if rc != 0:
                self.connected = False
                self.status = f"publish failed ({rc})"
                self.last_error = self.status
                return False
            self.connected = True
            self.status = "published"
            self.last_error = None
            return True
        except Exception as exc:  # pragma: no cover - depends on network stack
            self.connected = False
            self.status = "error"
            self.last_error = str(exc)
            return False

    def _ensure_client(self) -> Any:
        if self._client is not None and self.connected:
            return self._client
        if self.config is None:
            raise RuntimeError("Huawei IoTDA config is missing")

        if self._client_factory is not None:
            client = self._client_factory(client_id=self.config.resolved_client_id())
        else:
            if mqtt is None:
                raise RuntimeError("paho-mqtt is required when --mqtt-enabled is used")
            client = mqtt.Client(client_id=self.config.resolved_client_id())

        client.username_pw_set(self.config.device_id, self.config.resolved_password())
        if self.config.use_tls:
            client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
        client.connect(self.config.host, self.config.port, self.config.keepalive)
        client.loop_start()

        self._client = client
        self.connected = True
        self.status = "connected"
        self.last_error = None
        return client

    def close(self) -> None:
        if self._client is None:
            return
        try:
            self._client.loop_stop()
            self._client.disconnect()
        finally:
            self.connected = False
            self.status = "closed" if self.enabled else "disabled"
