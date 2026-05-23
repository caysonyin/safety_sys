<!-- Copyright (C) 2026 Linsheng Yin, Heng Quan, Bojin Li, Yunpeng Din, Penghan Chen -->
<!-- File purpose: Project overview, setup, usage, and licensing notes. -->

# CV Safety System

A computer-vision safety monitoring system for exhibition environments, combining **relic detection/tracking, human pose estimation, dangerous-object detection, and real-time alert visualization** in a single video pipeline.

> The current default configuration treats `cup` as the protected relic class and `knife`, `scissors`, and `baseball bat` as dangerous classes (configurable in code).

## Features

- YOLOv7-tiny detection with lightweight multi-object tracking and relic selection logic
- MediaPipe Pose 33-keypoint estimation
- Relic fence intrusion detection plus dangerous-object/person association alerts
- PySide6 desktop UI with alert list, status panel, and video overlays
- Automatic first-run download for pose model and YOLO weights

## Requirements

- Python 3.10+
- Linux / macOS / Windows (with camera access permissions)
- Internet access for first-time model download


## Installation

```bash
# 1) Install dependencies
pip install -r requirements.txt

# 2) Clone YOLOv7 repository
# The current implementation dynamically imports inference utilities from this local folder.
git clone --depth 1 https://github.com/WongKinYiu/yolov7.git
```

## Quick Start

```bash
# Recommended: launch the integrated PySide6 client
python run.py --source 0
```

Optional arguments:

- `--source`: camera index (for example, `0`) or video file path
- `--conf`: YOLO confidence threshold (default: `0.25`)
- `--pose-model`: pose model path (default: `models/pose_landmarker_full.task`)
- `--yolo-model`: YOLO weights path (default: `models/yolov7-tiny.pt`)
- `--alert-sound`: custom alert sound file path
- `--mqtt-enabled`: publish local alarm states to Huawei Cloud IoTDA

## Local Development Mode

The current implementation focuses on PC-based development before ESP32-S3,
ESP32-CAM, infrared, and MPU6050 firmware work. The Qt client includes local
buttons that simulate the hardware stages:

- `Trigger IR L1`: simulate the infrared proximity sensor and report level 1.
- `Trigger MPU6050 L3`: simulate relic movement and report level 3.
- `Restore Safe`: clear simulated sensor and vision alarm states.
- `Resend State`: force one more report of the current alarm state.

Vision risks detected by the existing camera pipeline are reported as level 2.
Alarm priority is level 3 (MPU6050) > level 2 (vision) > level 1 (infrared) >
level 0 (safe).

Use Python 3.10 or 3.11 for the local environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
git clone --depth 1 https://github.com/WongKinYiu/yolov7.git
python run.py --source 0
```

To connect the local client directly to Huawei Cloud IoTDA, create an MQTT
product model with service ID `Security` and properties `alarm_level`,
`ir_status`, `vision_status`, `imu_status`, and `message`. Then set these
environment variables before launching:

```bash
export HUAWEI_IOTDA_HOST="your-iotda-mqtt-host"
export HUAWEI_DEVICE_ID="your-device-id"
export HUAWEI_DEVICE_SECRET="your-device-secret"
export HUAWEI_SERVICE_ID="Security"
python run.py --source 0 --mqtt-enabled
```

If you downloaded a Huawei device connection key file from the console, you can
use it directly instead of exporting the connection fields manually:

```bash
python run.py --source 0 --mqtt-enabled --mqtt-key-file /path/to/DEVICES-CONNECT-KEY-xxx.txt
```

Optional MQTT settings:

- `HUAWEI_IOTDA_PORT`: defaults to `1883`, or `8883` when TLS is enabled.
- `HUAWEI_IOTDA_TLS`: set to `1` to use MQTT over TLS.
- `HUAWEI_MQTT_CLIENT_ID`: override the MQTT client ID if your IoTDA device
  authentication mode requires a specific client ID format.
- `HUAWEI_MQTT_PASSWORD`: use a precomputed MQTT password from Huawei's
  connection-parameter file instead of deriving one from the device secret.

Development-board work is intentionally deferred. ESP32-S3 sensor firmware,
ESP32-CAM low-power capture, board-to-board wakeup, and SD-card photo storage
will be added in a later hardware phase.

## Alternative Entry Points

```bash
# Integrated monitoring logic with OpenCV window
PYTHONPATH=src python -m cv_safety_sys.monitoring.integrated_monitor --source 0

# Directly launch the Qt module
PYTHONPATH=src python -m cv_safety_sys.ui.qt_monitor --source 0

# Detector/tracker only (debug)
PYTHONPATH=src python -m cv_safety_sys.detection.yolov7_tracker --source 0
```

## Repository Structure

```text
cv_safety_sys/
├── run.py
├── requirements.txt
├── src/cv_safety_sys/
│   ├── detection/           # YOLOv7 detection and tracking
│   ├── monitoring/          # Relic + pose + dangerous-object safety logic
│   ├── pose/                # MediaPipe pose model download helper
│   ├── ui/                  # PySide6 client
│   └── utils/               # Utilities (for example, text rendering)
└── docs/                    # Architecture and module documentation
```

## Documentation

- System architecture: `docs/system_architecture.md`
- Relic protection workflow: `docs/object_protection.md`
- Pose module guide: `docs/webcam_pose_detection.md`

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0).
You may copy, modify, and redistribute this project under the terms of GPL-3.0.
See the [LICENSE](./LICENSE) file for details.

## Open Source Notice

This project is released under GPL-3.0.
You may use, modify, and redistribute it under GPL-3.0 conditions.
If you distribute modified versions, you are generally required to provide corresponding source code under GPL-compatible terms.
See [LICENSE](./LICENSE) for full terms.

## Copyright

Copyright (C) 2025 Linsheng Yin, Heng Quan, Bojin Li, Yunpeng Din, Penghan Chen
