<!-- Copyright (C) 2026 Linsheng Yin, Heng Quan, Bojin Li, Yunpeng Din, Penghan Chen -->
<!-- File purpose: 中文姿态模块使用、模型处理和运行建议。 -->

# 姿态检测模块说明

系统使用 **MediaPipe Tasks Pose Landmarker** 进行人体姿态估计。姿态模块为视觉
二级报警提供关键几何信息，例如“手是否伸进展品安全围栏”。

## 模块位置

- 模型下载辅助：`src/cv_safety_sys/pose/model_downloader.py`
- 姿态推理封装：`src/cv_safety_sys/monitoring/integrated_monitor.py` 中的
  `PoseLandmarkHelper`

## 模型文件

- 默认模型路径：`models/pose_landmarker_full.task`
- 如果模型文件不存在，系统首次运行时会尝试自动下载。

也可以手动预下载：

```bash
uv run python -m cv_safety_sys.pose.model_downloader
```

## 在安全系统中的作用

1. 对每一帧画面运行人体姿态推理，得到 33 个关键点。
2. 根据关键点生成姿态包围框。
3. 通过 IoU 将姿态结果匹配到 YOLO 检测到的人员框。
4. 判断人体关键点是否进入展品安全围栏。
5. 判断人体关键点是否与危险物检测框有关联。

## 运行建议

- 如果实时速度较慢，可以降低视频分辨率或改用性能更好的电脑。
- 如果模型下载失败，可以手动把 `.task` 文件放到 `models/` 目录。
- 如果需要使用自定义姿态模型，运行时传入 `--pose-model <path>`。

## 与传感器报警的关系

姿态检测只负责视觉二级报警。它不会替代红外传感器或 MPU6050 的真实硬件能力。
当前本机开发阶段中，一级红外报警和三级 MPU6050 报警由 Qt 按钮模拟，详见
[本机模拟说明](local_simulation.md)。
