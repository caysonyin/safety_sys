<!-- Copyright (C) 2026 Linsheng Yin, Heng Quan, Bojin Li, Yunpeng Din, Penghan Chen -->
<!-- File purpose: 本机模拟和按钮替代传感器的说明。 -->

# 本机模拟说明

当前阶段先不开发 ESP32-S3、ESP32-CAM、红外传感器和 MPU6050 固件。为了先验证
业务流程，系统在电脑本机用 Qt 按钮和摄像头视觉算法模拟完整三级报警链路。

## 哪些硬件被本机替代

| 原计划硬件或动作 | 真实项目中的作用 | 当前本机实现 |
| --- | --- | --- |
| 红外传感器 | 检测有人靠近展品，触发一级报警。 | Qt 按钮 `Trigger IR L1` 直接触发一级报警状态。 |
| MPU6050 | 检测展品被移动、拿起或强烈震动，触发三级报警。 | Qt 按钮 `Trigger MPU6050 L3` 直接触发三级报警状态。 |
| ESP32-S3 | 读取红外和 MPU6050，并通过 Wi-Fi 上报云端。 | 电脑本机 Python 程序管理报警状态，并通过 MQTT/MQTTS 上报华为云。 |
| ESP32-CAM 低功耗拍照 | 红外触发后唤醒摄像头高频拍照或做视觉判断。 | 电脑摄像头持续输入视频帧，视觉模块直接判断二级报警。 |
| SD 卡保存照片 | 保存报警证据。 | 当前只支持 UI 中手动 `Save Snapshot` 保存本机截图。 |

## 按钮和报警等级的对应关系

| Qt 按钮 | 模拟对象 | 报警等级 | 上报字段变化 |
| --- | --- | --- | --- |
| `Trigger IR L1` | 红外传感器检测到有人靠近 | 1 | `alarm_level=1`, `ir_status=1` |
| 视觉自动触发 | 围栏侵入或危险物关联 | 2 | `alarm_level=2`, `vision_status=1` |
| `Trigger MPU6050 L3` | MPU6050 检测到展品移动 | 3 | `alarm_level=3`, `imu_status=1` |
| `Restore Safe` | 人工复位系统 | 0 | `alarm_level=0`，三个状态字段都变为 0 |
| `Resend State` | 手动重发当前状态 | 当前等级 | 状态不变，但强制再发布一次 MQTT 消息 |

## 为什么这样模拟

这样做的目的不是替代最终硬件，而是先确认以下内容：

- 三级报警优先级是否正确。
- 视觉二级报警能否与一级、三级报警共存。
- 华为云 IoTDA 产品模型和属性上报格式是否正确。
- Qt 界面是否能清楚展示报警等级、上报时间和 MQTT 状态。
- 后续接入 ESP32-S3 时，硬件只需要把“按钮触发”替换成“真实传感器触发”。

## 代码中对应的位置

- 按钮触发逻辑：`src/cv_safety_sys/ui/qt_monitor.py`
  - `on_trigger_ir_alarm`
  - `on_trigger_imu_alarm`
  - `on_restore_safe_alarm`
  - `on_resend_alarm_state`
- 报警状态机：`src/cv_safety_sys/alarm/alarm_manager.py`
  - `trigger_ir`
  - `trigger_imu`
  - `update_vision`
  - `restore_safe`
- 华为云上报：`src/cv_safety_sys/alarm/huawei_iotda.py`
  - `build_property_payload`
  - `HuaweiIoTDAPublisher.publish`
- 视觉二级报警接入点：`src/cv_safety_sys/monitoring/integrated_monitor.py`
  - `process_frame`
  - `_analyse_risks`

## 从本机模拟切换到真实硬件的思路

后续接开发板时，不需要推翻当前状态机。推荐做法是：

1. ESP32-S3 负责读取红外和 MPU6050。
2. ESP32-S3 把传感器事件通过 MQTT、HTTP 或串口发给电脑本机程序，或直接上报华为云。
3. 如果仍由电脑统一上报云端，只需要新增一个“硬件事件输入层”，调用现有
   `AlarmManager.trigger_ir()` 和 `AlarmManager.trigger_imu()`。
4. 如果由 ESP32-S3 直接上报云端，则要保证它生成的 JSON 字段和本机程序一致。

这样本机阶段验证过的云端产品模型、报警字段和优先级规则可以继续复用。
