<!-- Copyright (C) 2026 Linsheng Yin, Heng Quan, Bojin Li, Yunpeng Din, Penghan Chen -->
<!-- File purpose: 华为云 IoTDA 云端配置建议。 -->

# 华为云 IoTDA 云端配置建议

本文说明为了让本机程序顺利上报三级报警，华为云 IoTDA 控制台建议如何配置。
不同区域和控制台版本的页面名称可能略有差异，但核心配置保持一致。

## 目标

本机程序会通过 MQTT/MQTTS 向华为云 IoTDA 上报设备属性，Topic 为：

```text
$oc/devices/{device_id}/sys/properties/report
```

默认服务 ID 为 `Security`，上报 JSON 形态如下：

```json
{
  "services": [
    {
      "service_id": "Security",
      "properties": {
        "alarm_level": 2,
        "ir_status": 0,
        "vision_status": 1,
        "imu_status": 0,
        "message": "vision danger detected"
      },
      "event_time": "2026-05-23T07:30:00.000Z"
    }
  ]
}
```

## 产品建议

在 IoTDA 控制台创建产品时，建议使用：

| 配置项 | 建议值 |
| --- | --- |
| 协议类型 | MQTT |
| 数据格式 | JSON |
| 产品类型 | 自定义产品或普通直连设备 |
| 认证方式 | 密钥认证 |
| 服务 ID | `Security` |

## 物模型属性建议

在产品的模型定义中创建服务 `Security`，并添加以下属性：

| 属性名 | 类型建议 | 说明 |
| --- | --- | --- |
| `alarm_level` | 整型 | 0=安全，1=红外一级报警，2=视觉二级报警，3=MPU6050 三级报警。 |
| `ir_status` | 整型 | 0=未触发，1=红外触发。 |
| `vision_status` | 整型 | 0=无视觉风险，1=检测到围栏侵入或危险物关联。 |
| `imu_status` | 整型 | 0=未触发，1=检测到展品移动。 |
| `message` | 字符串 | 本机程序生成的报警说明，便于调试。 |

如果控制台要求设置取值范围，建议：

- `alarm_level`：0 到 3。
- `ir_status`、`vision_status`、`imu_status`：0 到 1。
- `message`：长度按控制台限制设置，建议至少 128 字符。

## 设备注册建议

1. 在产品下注册一个设备。
2. 保存设备 ID 和设备密钥。
3. 在设备详情页下载 MQTT/MQTTS 连接参数文件。
4. 优先使用连接参数文件运行本机程序：

```bash
uv run python run.py --source 0 --mqtt-enabled --mqtt-key-file /path/to/DEVICES-CONNECT-KEY-xxx.txt
```

这种方式会直接使用文件中的 `hostname`、`port`、`clientId`、`username` 和
预计算 `password`，比手动配置环境变量更不容易出错。

## 手动环境变量方式

如果不用连接参数文件，可以配置：

```bash
export HUAWEI_IOTDA_HOST="your-hostname"
export HUAWEI_DEVICE_ID="your-device-id"
export HUAWEI_DEVICE_SECRET="your-device-secret"
export HUAWEI_SERVICE_ID="Security"
export HUAWEI_IOTDA_TLS="1"
export HUAWEI_IOTDA_PORT="8883"
uv run python run.py --source 0 --mqtt-enabled
```

程序会按华为云密钥认证规则生成：

- `clientId`: `{device_id}_0_0_{YYYYMMDDHH}`
- `username`: `{device_id}`
- `password`: 使用时间戳对设备密钥做 HMAC-SHA256 后得到的 64 位十六进制字符串。

## 云端验证方法

运行程序后，可以在华为云控制台检查：

1. 设备是否在线。
2. 设备详情页的属性值是否更新。
3. 消息跟踪中是否能看到属性上报消息。
4. 点击 Qt 界面按钮后，`alarm_level` 是否按预期变化：
   - `Trigger IR L1` 后应为 `1`。
   - 视觉检测到风险后应为 `2`。
   - `Trigger MPU6050 L3` 后应为 `3`。
   - `Restore Safe` 后应为 `0`。

## 常见问题

- **设备一直不在线**：检查 hostname、端口、协议、clientId、username、password 是否来自同一个设备。
- **MQTTS 连接失败**：确认端口为 `8883`，并确保本机网络允许访问外部 TLS MQTT。
- **能连接但属性不显示**：确认产品模型中服务 ID 是 `Security`，属性名和程序上报字段一致。
- **报警等级没有降低**：三级报警优先级最高，必须点击 `Restore Safe` 才会清除本机模拟的 MPU6050 状态。
