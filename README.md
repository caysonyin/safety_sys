

# Safety System 展品防盗监控系统

本项目是一套面向展品防盗场景的本机开发版安全监控系统。当前阶段先不做
ESP32-S3、ESP32-CAM、红外传感器和 MPU6050 的开发板固件，而是在电脑本机
完成可运行、可演示、可连接华为云 IoTDA 的版本。

系统把 **展品检测/跟踪、人体姿态估计、危险物识别、三级报警状态管理、华为云
MQTT 属性上报、Qt 可视化界面** 放在同一条视频处理流程里。

> 当前默认把 `cup` 当作受保护展品类别，把 `knife`、`scissors`、`baseball bat`
> 当作危险物类别。这些类别可以在代码中调整。

## 功能

- 使用 YOLOv7-tiny 做目标检测，并用轻量跟踪逻辑保持展品 ID 稳定。
- 使用 MediaPipe Pose 输出 33 个人体关键点。
- 支持选中展品并生成安全围栏，检测人体关键点是否侵入围栏。
- 支持危险物与人员关联，识别“人携带危险物”的视觉风险。
- 支持三级报警：
  - `0`：安全。
  - `1`：一级报警，本机按钮模拟红外传感器触发。
  - `2`：二级报警，由视觉风险自动触发。
  - `3`：三级报警，本机按钮模拟 MPU6050 检测到展品移动。
- 支持将报警状态按华为云 IoTDA 属性上报格式发布到 MQTT Topic。
- 提供 PySide6 桌面界面，包含视频画面、状态面板、报警列表、云端连接状态和模拟按钮。
- 新增 GY-521/MPU6050 与 TCRT5000 的纯代码逻辑模块，当前不访问真实硬件，后续可接入 I2C/GPIO 适配器。
- 提供 ESP32-S3 Arduino C/C++ 示例代码，后续可作为开发板端传感器节点的起点。

## 环境要求

- Python 3.10 或 3.11。项目依赖中包含 MediaPipe，暂不建议使用 Python 3.12 及以上版本。
- `uv`，用于创建虚拟环境、解析依赖和运行命令。
- Linux、macOS 或 Windows，运行摄像头时需要授予摄像头权限。
- 首次下载模型文件时需要联网。
- 若要连接华为云，需要已注册 IoTDA 设备并拿到设备连接参数。

## 安装

```bash
# 1. 安装 uv（如果本机还没有）
# 2. 创建/同步项目虚拟环境
uv sync

# 3. 克隆 YOLOv7 源码到项目根目录
# 当前检测模块会动态导入这个本地目录里的推理工具。
git clone --depth 1 https://github.com/WongKinYiu/yolov7.git
```


## 快速运行

```bash
# 推荐：启动 PySide6 本机客户端
uv run python run.py --source 0
```

常用参数：

- `--source`：摄像头编号或视频文件路径，例如 `0`。
- `--conf`：YOLO 置信度阈值，默认 `0.25`。
- `--pose-model`：姿态模型路径，默认 `models/pose_landmarker_full.task`。
- `--yolo-model`：YOLO 权重路径，默认 `models/yolov7-tiny.pt`。
- `--alert-sound`：自定义报警声音文件路径。
- `--mqtt-enabled`：启用华为云 IoTDA MQTT 属性上报。
- `--mqtt-key-file`：华为云控制台下载的设备连接参数文件。

## 本机开发模式

当前阶段的目标是先把业务链路跑通：本机摄像头负责视觉二级报警，Qt 按钮模拟
红外和 MPU6050 触发，报警状态可以上报到华为云。

界面中的模拟按钮含义：

- `Trigger IR L1`：模拟红外传感器检测到有人靠近展品，上报一级报警。
- `Trigger MPU6050 L3`：模拟 MPU6050 检测到展品被移动，上报三级报警。
- `Restore Safe`：清除本机模拟传感器状态和视觉报警状态，上报安全状态。
- `Resend State`：强制重发当前报警状态，便于检查云端数据刷新。

视觉模块检测到安全围栏侵入或危险物关联时，会自动触发二级报警。报警优先级为：
三级 MPU6050 > 二级视觉 > 一级红外 > 安全。

## 连接华为云 IoTDA

如果已经从华为云控制台下载了设备连接参数文件，可以直接运行：

```bash
uv run python run.py --source 0 --mqtt-enabled --mqtt-key-file /path/to/DEVICES-CONNECT-KEY-xxx.txt
```

也可以用环境变量手动配置：

```bash
export HUAWEI_IOTDA_HOST="your-iotda-mqtt-host"
export HUAWEI_DEVICE_ID="your-device-id"
export HUAWEI_DEVICE_SECRET="your-device-secret"
export HUAWEI_SERVICE_ID="Security"
uv run python run.py --source 0 --mqtt-enabled
```

可选环境变量：

- `HUAWEI_IOTDA_PORT`：MQTT 端口。普通 MQTT 默认 `1883`，MQTTS 通常为 `8883`。
- `HUAWEI_IOTDA_TLS`：设为 `1` 时使用 MQTTS。
- `HUAWEI_MQTT_CLIENT_ID`：手动指定 MQTT clientId。
- `HUAWEI_MQTT_PASSWORD`：使用华为云连接参数文件里的预计算 password。

## 其他入口

```bash
# OpenCV 窗口版本的融合监控逻辑
uv run python -m cv_safety_sys.monitoring.integrated_monitor --source 0

# 直接启动 Qt 模块
uv run python -m cv_safety_sys.ui.qt_monitor --source 0

# 只调试检测和跟踪
uv run python -m cv_safety_sys.detection.yolov7_tracker --source 0
```

## 测试

```bash
uv run python -m unittest discover -s tests
```

如果已经同步过环境，只想跳过依赖同步直接运行测试：

```bash
uv run --no-sync python -m unittest discover -s tests
```

## 目录结构

```text
cv_safety_sys/
├── run.py
├── pyproject.toml
├── uv.lock
├── firmware/
│   └── esp32_s3_security_node/ # ESP32-S3 传感器节点 Arduino 示例
├── src/cv_safety_sys/
│   ├── alarm/               # 三级报警状态机与华为云 MQTT 上报
│   ├── devices/             # MPU6050/GY-521 与 TCRT5000 的设备逻辑
│   ├── detection/           # YOLOv7 检测和跟踪
│   ├── monitoring/          # 展品、姿态、危险物融合逻辑
│   ├── pose/                # MediaPipe 姿态模型下载辅助
│   ├── ui/                  # PySide6 本机客户端
│   └── utils/               # 文本渲染等工具
└── docs/                    # 中文说明文档
```

## 文档

- 系统架构：[docs/system_architecture.md](docs/system_architecture.md)
- 展品保护与视觉融合：[docs/object_protection.md](docs/object_protection.md)
- 姿态检测模块：[docs/webcam_pose_detection.md](docs/webcam_pose_detection.md)
- 华为云云端配置建议：[docs/huawei_iotda_setup.md](docs/huawei_iotda_setup.md)
- 本机模拟说明：[docs/local_simulation.md](docs/local_simulation.md)
- 设备逻辑模块说明：[docs/device_logic.md](docs/device_logic.md)
- ESP32-S3 传感器节点示例：[firmware/esp32_s3_security_node/README.md](firmware/esp32_s3_security_node/README.md)

## 当前未做的开发板内容

当前版本将部分开发板开发修改为本地开发来实现完整逻辑实现。已经包含
MPU6050/GY-521 与 TCRT5000 的阈值判断、防抖和报警转换逻辑，并提供未实测的
ESP32-S3 Arduino 示例代码。但当前仍不包含：

- ESP32-S3 通过真实 GPIO/I2C 读取红外传感器和 MPU6050。
- ESP32-CAM 低功耗唤醒、拍照、SD 卡存图。
- ESP32-S3 与 ESP32-CAM 之间的唤醒或通信协议。
- 真实传感器阈值标定和硬件抗干扰设计。

这些内容应在本机业务链路稳定后作为硬件阶段继续实现。

## 许可证

本项目使用 GNU General Public License v3.0（GPL-3.0）。你可以按照 GPL-3.0
条款复制、修改和再分发本项目。完整条款见 [LICENSE](./LICENSE)。
