<!-- Copyright (C) 2026 Linsheng Yin, Heng Quan, Bojin Li, Yunpeng Din, Penghan Chen -->
<!-- File purpose: GY-521/MPU6050 与 TCRT5000 设备逻辑说明。 -->

# 设备逻辑模块说明

本文说明当前已实现的 GY-521/MPU6050 和 TCRT5000 代码逻辑。当前没有实物设备，
所以代码只负责“读数判断”和“报警状态转换”，不负责真实 I2C、GPIO、供电或烧录调试。

## 模块位置

```text
src/cv_safety_sys/devices/
├── mpu6050.py      # GY-521/MPU6050 六轴读数和移动判断
├── tcrt5000.py     # TCRT5000 红外反射传感器靠近判断
└── controller.py   # 把设备状态接入 AlarmManager

firmware/esp32_s3_security_node/
├── esp32_s3_security_node.ino # ESP32-S3 Arduino C/C++ 示例
└── README.md                  # 接线、依赖和配置说明
```

## TCRT5000 逻辑

`TCRT5000Detector` 支持两种输入：

- `digital_value`：对应模块 DO 引脚。常见 TCRT5000 模块靠近时输出低电平，所以默认
  `active_low=True`。
- `analog_value`：对应模块 AO 引脚。当前只做阈值判断，后续接 ADC 时可以使用。

默认逻辑：

- 连续 2 个样本检测到靠近后，才认为红外触发，避免单帧抖动误报。
- 连续 3 个样本未触发后，才认为红外恢复。
- 触发后通过 `SensorAlarmController` 转成一级报警。

## GY-521/MPU6050 逻辑

`MPU6050Detector` 接收归一化后的读数：

- 加速度单位：`g`
- 角速度单位：`degree/s`

默认逻辑：

- 首个样本或手动 `calibrate()` 的样本作为静止基准。
- 如果当前加速度模长相对基准变化超过 `0.35g`，认为可能移动。
- 如果陀螺仪角速度模长超过 `80 degree/s`，认为可能移动。
- 连续 2 个样本满足移动条件后，才触发三级报警。
- 连续 5 个稳定样本后，设备逻辑可认为移动状态清除。

注意：报警状态机中三级报警优先级最高。实际 UI 中仍建议由用户点击 `Restore Safe`
进行人工复位，避免展品被移动后自动降级。

## 报警接入

`SensorAlarmController` 把两个设备检测器接到现有 `AlarmManager`：

- TCRT5000 触发：调用 `AlarmManager.trigger_ir()`，形成一级报警。
- MPU6050 触发：调用 `AlarmManager.trigger_imu()`，形成三级报警。
- 如果同一轮同时出现红外和 IMU 触发，优先发出 IMU 三级报警。

## ESP32-S3 Arduino 示例

`firmware/esp32_s3_security_node/esp32_s3_security_node.ino` 提供一个开发板端
C/C++ 版本参考，实现内容包括：

- `Wire` 直接读取 MPU6050 原始寄存器，不额外依赖 MPU6050 第三方库。
- `digitalRead` 读取 TCRT5000 DO 引脚。
- 使用与 Python 版本一致的阈值、防抖和三级报警优先级。
- 使用 `PubSubClient` 和 `ArduinoJson` 上报华为云 IoTDA 属性 JSON。
- 支持直接填写华为云连接参数文件中的 `clientId` 和 `password`。
- 如果不使用预计算 password，可通过 NTP 时间和设备密钥动态生成 HMAC-SHA256 password。

这个示例尚未在真实开发板上编译、烧录和调试。

## 后续接真实硬件时要补的内容

当前还没有实现：

- Python 端直接读 GPIO/I2C 的硬件适配器。
- MPU6050 零偏校准、滤波、安装方向补偿。
- TCRT5000 现场灵敏度标定和环境光干扰处理。

这些内容应该在拿到实物后再根据实际接线和采样数据调整。
