<!-- Copyright (C) 2026 Linsheng Yin, Heng Quan, Bojin Li, Yunpeng Din, Penghan Chen -->
<!-- File purpose: High-level architecture, module boundaries, and data flow. -->

# System Architecture

This project performs real-time safety monitoring by combining **protected relics, human pose landmarks, and dangerous objects**.

The main runtime pipeline is:

**Video Input → Detection/Tracking → Pose Estimation → Safety Fusion Logic → UI/Alerts**

## Modules and Responsibilities

| Module | Key File | Responsibility |
| --- | --- | --- |
| Startup and resource checks | `run.py` | Validates local `yolov7/` repository, prepares model paths, and launches the Qt client. |
| Detection and tracking | `src/cv_safety_sys/detection/yolov7_tracker.py` | Runs YOLOv7-tiny detection, class filtering, `SimpleTracker`, and relic selection interaction. |
| Pose model management | `src/cv_safety_sys/pose/model_downloader.py` | Downloads and caches the MediaPipe Pose Landmarker model. |
| Safety fusion logic | `src/cv_safety_sys/monitoring/integrated_monitor.py` | Fuses person/relic/dangerous-object detections with pose points and produces fences, alerts, and stats. |
| Alarm state and cloud reporting | `src/cv_safety_sys/alarm/` | Applies three-level alarm priority and optionally publishes Huawei Cloud IoTDA property JSON over MQTT. |
| Visualization and interaction | `src/cv_safety_sys/ui/qt_monitor.py` | Implements PySide6 UI, video panel, alert list, local sensor simulation controls, status widgets, and mouse/keyboard interactions. |

## Data Flow

1. **Video capture**: OpenCV reads frames from a camera or a video file.
2. **Detection and class filtering**: YOLOv7 outputs bounding boxes and classes, including `cup`, `person`, and configured dangerous classes.
3. **Tracking**: `SimpleTracker` maintains stable `track_id`s across frames.
4. **Pose estimation**: MediaPipe Pose produces 33 keypoints and associates pose entries to person detections via IoU.
5. **Safety logic**:
   - Build protection fences around selected relics.
   - Detect whether human keypoints enter the fenced region.
   - Associate dangerous objects to nearby persons and escalate alert severity.
6. **Alarm state**: Convert local infrared simulation, vision risks, and MPU6050 simulation into levels 1, 2, and 3, with level 3 taking priority.
7. **Cloud reporting**: When `--mqtt-enabled` is set, publish Huawei Cloud IoTDA device properties to `$oc/devices/{device_id}/sys/properties/report`.
8. **Output rendering**: Push structured status/alerts to OpenCV/Qt views and update alert history and counters.

## Runtime Entry Points

- `python run.py --source 0`: recommended integrated desktop client.
- `python run.py --source 0 --mqtt-enabled`: desktop client with Huawei Cloud IoTDA MQTT property reporting enabled.
- `PYTHONPATH=src python -m cv_safety_sys.monitoring.integrated_monitor --source 0`: OpenCV monitoring view.
- `PYTHONPATH=src python -m cv_safety_sys.ui.qt_monitor --source 0`: direct Qt module entry.

## Local-First Alarm Scope

The current phase does not implement ESP32-S3 firmware, ESP32-CAM low-power capture,
or physical infrared/MPU6050 sensor reads. The Qt client provides local simulation
buttons for level 1 and level 3 alarms while the existing vision pipeline provides
level 2 alarms.

## Models and Dependencies

- Default YOLO weights path: `models/yolov7-tiny.pt`
- Default pose model path: `models/pose_landmarker_full.task`
- YOLO inference code folder: repository root `yolov7/` (must be cloned manually)
