#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from cv_safety_sys.alarm import (
    AlarmEvent,
    AlarmLevel,
    HuaweiIoTDAConfig,
    HuaweiIoTDAPublisher,
)
from cv_safety_sys.alarm.huawei_iotda import build_property_payload


class FakePublishResult:
    rc = 0


class FakeMQTTClient:
    def __init__(self, client_id: str) -> None:
        self.client_id = client_id
        self.username = None
        self.password = None
        self.host = None
        self.port = None
        self.published = []

    def username_pw_set(self, username, password) -> None:
        self.username = username
        self.password = password

    def connect(self, host, port, keepalive) -> None:
        self.host = host
        self.port = port
        self.keepalive = keepalive

    def loop_start(self) -> None:
        pass

    def publish(self, topic, payload, qos=0):
        self.published.append((topic, payload, qos))
        return FakePublishResult()


class HuaweiIoTDATests(unittest.TestCase):
    def make_event(self) -> AlarmEvent:
        return AlarmEvent(
            alarm_level=AlarmLevel.VISION,
            ir_status=False,
            vision_status=True,
            imu_status=False,
            source="vision",
            message="vision danger detected",
            event_time=datetime(2026, 5, 23, 7, 30, tzinfo=timezone.utc),
        )

    def test_property_payload_matches_huawei_shape(self) -> None:
        payload = build_property_payload(self.make_event(), "Security")

        self.assertEqual(payload["services"][0]["service_id"], "Security")
        self.assertEqual(payload["services"][0]["event_time"], "2026-05-23T07:30:00.000Z")
        properties = payload["services"][0]["properties"]
        self.assertEqual(properties["alarm_level"], 2)
        self.assertEqual(properties["ir_status"], 0)
        self.assertEqual(properties["vision_status"], 1)
        self.assertEqual(properties["imu_status"], 0)
        self.assertEqual(properties["message"], "vision danger detected")

    def test_publisher_sends_expected_topic_and_json(self) -> None:
        created_clients = []

        def client_factory(client_id: str):
            client = FakeMQTTClient(client_id)
            created_clients.append(client)
            return client

        config = HuaweiIoTDAConfig(
            host="iot.example.com",
            device_id="device-001",
            device_secret="secret",
            service_id="Security",
            port=1883,
        )
        publisher = HuaweiIoTDAPublisher(config, enabled=True, client_factory=client_factory)

        published = publisher.publish(self.make_event())

        self.assertTrue(published)
        self.assertEqual(created_clients[0].username, "device-001")
        self.assertRegex(created_clients[0].client_id, r"^device-001_0_0_\d{10}$")
        self.assertRegex(created_clients[0].password, r"^[0-9a-f]{64}$")
        topic, raw_payload, qos = created_clients[0].published[0]
        self.assertEqual(topic, "$oc/devices/device-001/sys/properties/report")
        self.assertEqual(qos, 1)
        self.assertEqual(
            json.loads(raw_payload),
            build_property_payload(self.make_event(), "Security"),
        )

    def test_secret_auth_matches_huawei_documented_example(self) -> None:
        config = HuaweiIoTDAConfig(
            host="iot.example.com",
            device_id="device-001",
            device_secret="12345678",
        )
        timestamp = datetime(2025, 4, 14, 1, tzinfo=timezone.utc)

        self.assertEqual(config.auth_timestamp(timestamp), "2025041401")
        self.assertEqual(config.resolved_client_id(timestamp), "device-001_0_0_2025041401")
        self.assertEqual(
            config.resolved_password(timestamp),
            "c75150e6cb841417396819e4d2ee4358a416344a03a083e3a8567074ddec820a",
        )

    def test_config_loads_huawei_connection_key_file(self) -> None:
        data = {
            "username": "device-001",
            "password": "precomputed-password",
            "clientId": "device-001_0_0_2026052307",
            "hostname": "iot.example.com",
            "port": 8883,
            "protocol": "MQTTS",
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "connect-key.json"
            path.write_text(json.dumps(data), encoding="utf-8")

            config = HuaweiIoTDAConfig.from_connection_key_file(path)

        self.assertEqual(config.host, "iot.example.com")
        self.assertEqual(config.device_id, "device-001")
        self.assertEqual(config.resolved_client_id(), "device-001_0_0_2026052307")
        self.assertEqual(config.resolved_password(), "precomputed-password")
        self.assertTrue(config.use_tls)


if __name__ == "__main__":
    unittest.main()
