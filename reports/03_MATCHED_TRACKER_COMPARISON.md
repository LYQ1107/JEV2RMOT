# 共享候选比较

## 结论

原生结果不能直接解释二阶段差异，因为候选源不同；完成共享候选控制后，结论变得清楚：在同一 FlexHook 候选、同一 A800 GT 和同一 bundled TrackEval 下，YesTrack V2 的二阶段结果高于 FlexHook O0。

## 原生结果

| 方法 | 原生候选 | 评测点 | HOTA | DetA | AssA | IDF1 | IDSW |
|---|---|---:|---:|---:|---:|---:|---:|
| YesTrack V2 | 官方归档 TempRMOT* | V2 threshold 0.60 | 41.155 | 32.191 | 53.032 | 48.612 | 3,169 |
| FlexHook V2 | A800 Temp-NeuralSORT-kitti2 | official argmax | 42.526 | 30.629 | 59.185 | 46.496 | 2,908 |

YesTrack 原生候选的 IoU 0.5 覆盖率为 284,308/491,286 = 57.870%；FlexHook 候选为 362,304/491,286 = 73.746%。因此 41.155 与 42.526 的 native 差值不能归因于语言/二阶段模块。

## 受控共享候选结果

共享输入是 A800 上的 FlexHook `Temp-NeuralSORT-kitti2`：4 个视频共 10,822 行候选，复制到 862 个 YesTrack 表达式目录后产生 2,425,382 行 score。转换保持 frame、bbox 和 car ID，并按 FlexHook 官方规则给 pedestrian ID 加 `max_car_id` offset；表达式目录校验 862/862 通过。

两套结果都用 A800 FlexHook `gt_template` 和同一 `refer_eval_seqmap` 重评，避免把 YesTrack 发布 GT 的三位小数坐标与 FlexHook 高精度 GT 混在一起：

| 方法 | 候选 | 阈值/决策 | HOTA | DetA | AssA | IDF1 | IDSW | Dets |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| FlexHook O0 | 同一 Temp-NeuralSORT-kitti2 | official argmax | 42.526 | 30.629 | 59.185 | 46.496 | 2,908 | 750,832 |
| YesTrack shared | 同一 Temp-NeuralSORT-kitti2 | score threshold 0.60 | 47.607 | 37.944 | 59.818 | 55.302 | 2,585 | 604,025 |

YesTrack 相对 FlexHook 的受控差值为 HOTA +5.081、DetA +7.315、AssA +0.633、IDF1 +8.806。用同一候选、同一 GT 的 score threshold 0.50 重评，YesTrack HOTA 为 47.284，结论不变。

这说明当前 native 中 FlexHook 的优势主要来自候选覆盖和输出协议，不是二阶段必然更强；在同一候选上，YesTrack 的选择结果更好。但这是已发布权重的控制实验，不等价于训练了新的 JEV。

## 候选上限

共享候选在 A800 GT 上的 IoU 覆盖为：0.3/0.5/0.7 分别为 75.320%/73.746%/69.836%，IoU 0.5 仍有 128,982/491,286 = 26.254% GT boxes 缺失。O1/O2 会复用同一候选上限，不能修复这些缺失框。

## 口径和边界

- native YesTrack 指官方归档 GT；共享表指 A800 FlexHook `gt_template`，两者数值不混写。
- YesTrack 共享推理在本地 V100 fp16 完成，不冒充 A800 硬件复现；A800 用于候选、GT 和 checkpoint 资产。
- 历史 NAS TempRMOT `predict.txt` 已经过表达式选择，不能替代原始第一阶段候选池。
- 完整 source checksum、任务/行数和共享指标见 `analysis/yestrack_official_run_receipt.json`、`analysis/metrics.csv` 和 `analysis/oracle_results.csv`。
