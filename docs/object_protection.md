<!-- Copyright (C) 2026 Linsheng Yin, Heng Quan, Bojin Li, Yunpeng Din, Penghan Chen -->
<!-- File purpose: 中文展品保护流程和视觉报警融合说明。 -->

# 展品保护与视觉融合

本文说明系统如何把展品检测、人体姿态、危险物检测和安全围栏组合起来，形成
二级视觉报警。核心调度类是 `IntegratedSafetyMonitor`。

```text
src/cv_safety_sys/
├── detection/yolov7_tracker.py      # 检测、跟踪、展品选择
├── monitoring/integrated_monitor.py # 视觉融合和报警判断
└── ui/qt_monitor.py                 # Qt 界面和交互
```

## 完整流程

1. **检测阶段**：YOLOv7-tiny 检测展品、人员和危险物。
2. **跟踪阶段**：系统为检测目标分配相对稳定的 `track_id`。
3. **展品围栏阶段**：用户在画面中选中展品后，系统为该展品生成安全围栏。
4. **姿态关联阶段**：MediaPipe 的 33 个姿态关键点会关联到对应人员。
5. **围栏侵入判断**：如果人员关键点进入展品安全围栏，系统认为存在视觉风险。
6. **危险物关联判断**：如果危险物框与人员框重叠，或人体关键点落入危险物框，
   系统认为该人员可能携带危险物。
7. **二级报警输出**：围栏侵入或危险物关联会触发二级视觉报警，并进入三级报警状态机。

## 默认类别

- 受保护展品类别：`cup`
- 危险物类别：`knife`、`scissors`、`baseball bat`

如需扩展危险物类别，修改 `integrated_monitor.py` 中的 `DANGEROUS_CLASSES`。

## 报警关系

视觉模块只负责二级报警，即“看到了危险行为或危险物”。一级和三级报警在当前阶段
由本机按钮模拟：

- 一级报警：红外检测到有人靠近。
- 二级报警：视觉检测到围栏侵入或危险物关联。
- 三级报警：MPU6050 检测到展品被移动。

如果一级、二级、三级同时存在，最终上报级别以最高优先级为准：三级 > 二级 > 一级。

## 常用命令

```bash
# 推荐的集成运行方式
uv run python run.py --source 0

# 启用华为云上报
uv run python run.py --source 0 --mqtt-enabled --mqtt-key-file /path/to/DEVICES-CONNECT-KEY-xxx.txt

# 调试融合监控逻辑，使用 OpenCV 窗口
uv run python -m cv_safety_sys.monitoring.integrated_monitor --source 0 --conf 0.25

# 只调试检测和跟踪
uv run python -m cv_safety_sys.detection.yolov7_tracker --source 0 --conf 0.1
```

## Qt 交互说明

- 在选择阶段点击视频中的目标，可以选中或取消选中受保护展品。
- 选中展品后可以拖动安全围栏边界，调整保护区域。
- 点击 `Start Monitoring` 后进入监控阶段，视觉风险会触发二级报警。
- 报警列表展示最近报警；点击报警项可确认并清除对应人员报警。
- 可通过 `--alert-sound` 指定本地报警声音文件。
