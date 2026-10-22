# FINAL_REPORT

## 直接结论

有提升空间，而且已经完成了同一候选源的统计。最可靠的结论是：候选已经存在时，YesTrack 二阶段仍能明显改善选择；候选不存在时，普通 JEV 无法修复，必须改第一阶段或候选生成。

## 原生 V2 结果

| 方法 | 候选 | 评测点 | HOTA | DetA | AssA | IDF1 | IDSW |
|---|---|---:|---:|---:|---:|---:|---:|
| YesTrack V2 | 官方 TempRMOT* | threshold 0.60 | 41.155 | 32.191 | 53.032 | 48.612 | 3,169 |
| FlexHook V2 | A800 Temp-NeuralSORT-kitti2 | official argmax | 42.526 | 30.629 | 59.185 | 46.496 | 2,908 |

这两行 native 不能直接比较：YesTrack 候选 IoU 0.5 recall 为 57.870%，FlexHook 为 73.746%。YesTrack threshold sweep 的最高 HOTA 是 0.65 的 41.179，主点仍按官方 V2 起始阈值 0.60。

## 同一候选的公平对照

FlexHook 的 A800 `Temp-NeuralSORT-kitti2` 已按官方合并规则转换到 YesTrack，frame、bbox 和合并 ID 保持一致，862/862 个表达式完成推理，2,425,382 行 score 无错误。两套结果用同一 A800 FlexHook `gt_template` 和同一 TrackEval 重评：

| 方法 | 候选 | 阈值/决策 | HOTA | DetA | AssA | IDF1 | IDSW |
|---|---|---:|---:|---:|---:|---:|---:|
| FlexHook O0 | 同一 Temp-NeuralSORT-kitti2 | official argmax | 42.526 | 30.629 | 59.185 | 46.496 | 2,908 |
| YesTrack shared | 同一 Temp-NeuralSORT-kitti2 | score 0.60 | 47.607 | 37.944 | 59.818 | 55.302 | 2,585 |

受控差值：HOTA +5.081、DetA +7.315、AssA +0.633、IDF1 +8.806。score 0.50 时 YesTrack shared HOTA 47.284，结论不变。因此在这个固定候选上，YesTrack 二阶段优于 FlexHook O0；native 表中的差异不能被解读为 FlexHook 语言模块更强。

## 错误来源和可修复空间

| 口径 | candidate missing @IoU0.5 | selection FN | selection FP | selection oracle HOTA | identity oracle HOTA |
|---|---:|---:|---:|---:|---:|
| YesTrack native | 206,978 / 42.130% | 27,345 | 198,536 | 53.910 | 57.779 |
| FlexHook/shared candidate | 128,982 / 26.254% | shared 34,503 @0.60 | shared 276,224 @0.60 | 65.423 | 69.125 |

共享候选的 IoU 0.3/0.5/0.7 recall 为 75.320%/73.746%/69.836%。因此 O1/O2 的上限主要由候选几何和身份决定；O1/O2 是离线反事实，不是已实现的 JEV 收益。共享 O1-O0@0.50 为 +18.139 HOTA，O2-O1 为 +3.702 HOTA，说明 selection 和身份连续性都值得研究。

## 最终建议

先做 frozen-candidate、候选内 JEV，而不是端到端替换：

1. 无训练 baseline：表达式/全局阈值校准、同帧竞争抑制、候选排序、ID 稳定规则；
2. 分别关闭 YesTrack 的 video refinement、TCP、TRP，做因果消融；
3. 再训练融合表达式、候选框、竞争候选、轨迹历史和短时视觉状态的 JEV；
4. 以 HOTA/DetA/AssA/IDF1、candidate recall、IDSW 和 0019 分层统计验收。

不能声称 JEV 能救回候选缺失，也不能把 O3 的约 100 分当作方法收益。资源、hash、权重下载、运行 receipt 和完整 CSV 见 [`analysis/yestrack_official_run_receipt.json`](../analysis/yestrack_official_run_receipt.json)、[`analysis/metrics.csv`](../analysis/metrics.csv)、[`analysis/oracle_results.csv`](../analysis/oracle_results.csv)。
