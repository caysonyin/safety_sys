# ESP32-S3 传感器节点示例

这个目录提供一个兼容 ESP32-S3 开发板的 Arduino C/C++ 示例，用于后续接入：

- GY-521 / MPU6050 六轴加速度计和陀螺仪
- TCRT5000 红外反射传感器
- 华为云 IoTDA MQTT/MQTTS 属性上报

当前没有实物设备，因此代码只作为开发板端逻辑实现参考，尚未做烧录和现场调试。

## 接线建议

| 模块 | 模块引脚 | ESP32-S3 引脚 |
| --- | --- | --- |
| TCRT5000 | VCC | 3.3V |
| TCRT5000 | GND | GND |
| TCRT5000 | DO | GPIO 18 |
| GY-521/MPU6050 | VCC | 3.3V |
| GY-521/MPU6050 | GND | GND |
| GY-521/MPU6050 | SDA | GPIO 21 |
| GY-521/MPU6050 | SCL | GPIO 22 |

如果你的 ESP32-S3 开发板默认 I2C 引脚不同，只需要修改 `.ino` 顶部的
`MPU_SDA_PIN` 和 `MPU_SCL_PIN`。

## Arduino IDE 依赖

在 Arduino IDE 中安装：

- ESP32 by Espressif Systems
- PubSubClient by Nick O'Leary
- ArduinoJson by Benoit Blanchon

代码没有依赖额外 MPU6050 库，而是直接用 `Wire` 读取 MPU6050 寄存器。

## 需要填写的配置

打开 `esp32_s3_security_node.ino`，修改：

- `WIFI_SSID`
- `WIFI_PASSWORD`
- `MQTT_HOST`
- `MQTT_PORT`
- `DEVICE_ID`
- `DEVICE_SECRET` 或连接参数文件里的 `MQTT_CLIENT_ID` / `MQTT_PASSWORD`

如果使用华为云控制台下载的连接参数文件，可以直接填写文件中的：

- `hostname` -> `MQTT_HOST`
- `port` -> `MQTT_PORT`
- `username` -> `DEVICE_ID`
- `clientId` -> `MQTT_CLIENT_ID`
- `password` -> `MQTT_PASSWORD`

如果不填 `MQTT_CLIENT_ID` 和 `MQTT_PASSWORD`，代码会尝试通过 NTP 获取 UTC 时间，
再用设备密钥动态生成华为云需要的 clientId 和 HMAC-SHA256 password。

## 行为说明

- TCRT5000 连续检测到靠近后，上报一级报警。
- MPU6050 连续检测到加速度突变或角速度过大后，上报三级报警。
- 三级报警默认锁存，避免展品被移动后自动恢复为安全状态。
- 串口输入 `r` 或 `R` 可以清除锁存报警并上报安全状态。

## 未验证事项

- 未在真实 ESP32-S3 上编译和烧录。
- 未做 MPU6050 零偏、安装方向和现场噪声标定。
- 未做 TCRT5000 电位器灵敏度现场调试。
- MQTTS 证书校验示例为了开发方便使用 `setInsecure()`，正式部署应替换为华为云根证书。
