<!-- Copyright (C) 2026 Linsheng Yin, Heng Quan, Bojin Li, Yunpeng Din, Penghan Chen -->
<!-- File purpose: 中文系统架构、模块边界和数据流说明。 -->

# 系统架构

本项目当前是“本机优先”的展品防盗监控系统。它把受保护展品、人体姿态、
危险物识别、三级报警状态和华为云 IoTDA 上报整合到一条实时视频流程里。

主流程如下：

**视频输入 → 目标检测/跟踪 → 姿态估计 → 安全融合判断 → 三级报警状态 → 华为云上报 → UI 展示**

## 模块职责

| 模块 | 关键文件 | 职责 |
| --- | --- | --- |
| 启动与资源检查 | `run.py` | 检查本地 `yolov7/` 目录，准备模型路径，启动 Qt 客户端。 |
| 检测与跟踪 | `src/cv_safety_sys/detection/yolov7_tracker.py` | 运行 YOLOv7-tiny，过滤类别，跟踪展品 ID，支持展品选择。 |
| 姿态模型管理 | `src/cv_safety_sys/pose/model_downloader.py` | 下载并缓存 MediaPipe Pose Landmarker 模型。 |
| 安全融合逻辑 | `src/cv_safety_sys/monitoring/integrated_monitor.py` | 融合展品、人体、危险物和姿态关键点，生成视觉风险。 |
| 报警状态与云端上报 | `src/cv_safety_sys/alarm/` | 管理三级报警优先级，按华为云 IoTDA 属性格式发布 MQTT JSON。 |
| 可视化与交互 | `src/cv_safety_sys/ui/qt_monitor.py` | 展示视频、状态、报警列表、云端连接状态，并提供本机模拟按钮。 |

## 数据流

1. **视频采集**：OpenCV 从摄像头或视频文件读取画面。
2. **目标检测**：YOLOv7 输出展品、人员、危险物等检测框。
3. **目标跟踪**：`SimpleTracker` 给展品和人员维持稳定的 `track_id`。
4. **姿态估计**：MediaPipe Pose 输出 33 个关键点，并通过 IoU 关联到人员检测框。
5. **视觉安全判断**：
   - 对选中的展品生成安全围栏。
   - 判断人体关键点是否进入安全围栏。
   - 判断危险物是否与某个人有关联。
6. **报警状态合成**：
   - Qt 按钮模拟红外触发，形成一级报警。
   - 视觉安全判断产生风险，形成二级报警。
   - Qt 按钮模拟 MPU6050 触发，形成三级报警。
   - 优先级固定为三级 > 二级 > 一级 > 安全。
7. **云端上报**：启用 `--mqtt-enabled` 后，系统向华为云 IoTDA Topic
   `$oc/devices/{device_id}/sys/properties/report` 发布属性 JSON。
8. **界面展示**：Qt 界面显示视频叠加层、报警状态、MQTT 状态、最近报警和统计信息。

## 运行入口

- `uv run python run.py --source 0`：推荐的本机 Qt 客户端。
- `uv run python run.py --source 0 --mqtt-enabled --mqtt-key-file <连接参数文件>`：启用华为云 IoTDA 上报。
- `uv run python -m cv_safety_sys.monitoring.integrated_monitor --source 0`：OpenCV 窗口版监控。
- `uv run python -m cv_safety_sys.ui.qt_monitor --source 0`：直接启动 Qt 模块。

## 本阶段范围

当前阶段不读取真实红外传感器和 MPU6050，也不控制 ESP32-CAM 低功耗拍照。
这些硬件动作先由本机 UI 和视觉模块模拟或替代，目的是先验证业务流程、报警优先级、
JSON 上报格式和华为云连接。

## 模型与依赖

- 默认 YOLO 权重路径：`models/yolov7-tiny.pt`
- 默认姿态模型路径：`models/pose_landmarker_full.task`
- YOLO 推理源码目录：项目根目录下的 `yolov7/`，需要手动克隆或提前放好。
