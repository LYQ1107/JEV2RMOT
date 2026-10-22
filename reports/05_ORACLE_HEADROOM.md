# Oracle headroom

Oracle 只用于离线分析，GT 在模型 forward 之后才进入匹配和结果生成。O1/O2 不应被称作模型收益。

## FlexHook V2

固定候选池为 A800 的官方 Temp-NeuralSORT-kitti2，共 862 个表达式、491,286 个 GT boxes；O1/O2 使用 IoU 0.5 的逐帧一对一匹配。

| Oracle | HOTA | DetA | AssA | IDF1 | 相对 O0 HOTA |
|---|---:|---:|---:|---:|---:|
| O0 官方 raw-score 输出 | 42.526 | 30.629 | 59.185 | 46.496 | 0 |
| O1 固定候选 + GT 完美 selection | 65.423 | 64.270 | 66.878 | 77.244 | +22.897 |
| O2 O1 + GT identity mapping | 69.125 | 64.414 | 74.397 | 84.889 | +26.599 |
| O3 GT box + GT ID sanity | 99.997 | 99.997 | 99.997 | 99.999 | 不计收益 |

O1 保留候选 bbox 和原合并 Track ID，只保留与当前表达式 GT 在 IoU 0.5 下合法匹配的候选；O2 进一步将已选候选的 ID 映射为匹配 GT ID。

## YesTrack 原生 V2

原生候选为官方归档 TempRMOT*，候选覆盖 IoU 0.5 为 284,308/491,286 = 57.870%。为保持原生 O0/O1/O2 同一阈值，以下均为官方归档 GT、TrackEval score threshold 0.50；主运行点另行报告为 threshold 0.60。

| Oracle | HOTA | DetA | AssA | IDF1 | IDSW | 相对 O0@0.50 HOTA |
|---|---:|---:|---:|---:|---:|---:|
| O0 官方输出 | 41.028 | 31.894 | 53.198 | 48.228 | 3,316 | 0 |
| O1 固定候选 + GT 完美 selection | 53.910 | 50.050 | 58.608 | 63.813 | 7,378 | +12.882 |
| O2 O1 + GT identity mapping | 57.779 | 50.285 | 66.805 | 73.314 | 0 | +16.751 |
| O3 GT box + GT ID sanity | 99.997 | 99.997 | 99.997 | 99.999 | 0 | 不计收益 |

## 共享 FlexHook 候选 + YesTrack V2

这是同候选、同 A800 GT、同评估器的控制实验。O0@0.50 是 YesTrack score threshold 0.50，O1/O2/O3 是离线反事实；O0@0.60 的主点为 HOTA 47.607。

| Oracle | HOTA | DetA | AssA | IDF1 | IDSW | 相对 shared O0@0.50 HOTA |
|---|---:|---:|---:|---:|---:|---:|
| O0 YesTrack score @0.50 | 47.284 | 37.359 | 59.930 | 54.633 | 2,766 | 0 |
| O1 固定候选 + GT 完美 selection | 65.423 | 64.270 | 66.878 | 77.244 | 4,601 | +18.139 |
| O2 O1 + GT identity mapping | 69.125 | 64.414 | 74.397 | 84.889 | 0 | +21.841 |
| O3 GT box + GT ID sanity | 99.997 | 99.997 | 99.997 | 99.999 | 0 | 不计收益 |

共享 O1/O2 与 FlexHook O1/O2 完全一致，证明两者使用的是同一个候选几何/身份上限；shared O0 与 FlexHook O0 的差异来自二阶段评分/筛选。O1-O0 仍是理想 selection 上限，O2-O1 的 3.702 HOTA 是身份关联上限，不能直接承诺为实际 JEV 增益。

## 研究含义

- 候选已有时，YesTrack 的 shared O0 到 O1 仍有 +18.139 HOTA 的离线 selection headroom；这支持候选内 JEV 或规则 baseline。
- 同一候选的 O1 到 O2 有 +3.702 HOTA，说明身份连续性有独立空间，但 O2 使用 GT ID，不是可部署方法。
- 候选缺失 26.254% 的 GT boxes 不会被 O1/O2 恢复；第一阶段、候选召回和几何协议仍是硬边界。
- O3 只代表评测 sanity，不计入方法收益。

完整统计见 `analysis/candidate_coverage.csv`、`analysis/yestrack_official_run_receipt.json` 和 `analysis/oracle_results.csv`。
