# Oracle headroom

## FlexHook V2 已完成

固定候选池为 A800 的官方 `Temp-NeuralSORT-kitti2`，共 862 个表达式、491,286 个 GT boxes。O1/O2 使用 IoU 0.5 的逐帧一对一匹配；GT 只在模型 forward 之后进入离线反事实。

| Oracle | HOTA | DetA | AssA | IDF1 | 相对 O0 HOTA |
|---|---:|---:|---:|---:|---:|
| O0 官方 raw-score 输出 | 42.526 | 30.629 | 59.185 | 46.496 | 0 |
| O1 固定候选 + GT 完美 selection | 65.423 | 64.270 | 66.878 | 77.244 | +22.897 |
| O2 O1 + GT identity mapping | 69.125 | 64.414 | 74.397 | 84.889 | +26.599 |
| O3 GT box + GT ID sanity | 100.000 | 100.000 | 100.000 | 100.000 | 不计收益 |

O1 保留原候选 bbox 和原合并 Track ID，只保留与当前表达式 GT 在 IoU 0.5 下合法匹配的候选；O2 进一步将已选候选的 ID 映射为匹配 GT ID，不新增框、不修改坐标。O3 只是验证 GT、帧号、seqmap 与 TrackEval 的转换正确，不能当作 JEV 提升。

## 解释

- O1–O0 为 `22.897` HOTA points，是“选择/过滤 + 官方测试窗口缺口”的离线理想差距，不是 JEV 实际收益。
- O2–O1 为 `3.702` HOTA points，是在已有候选框上的理想身份纠错空间；它不能证明实际 JEV 能修复所有 IDSW。
- O1 的 DetRe 约 73.739%，O2 的 DetRe 约 73.746%，与候选覆盖 362,304/491,286=73.746% 一致；这确认第一阶段覆盖是硬上限。
- O1 的 IDSW 仍为 4,601，O2 为 0；因此候选 ID/轨迹连续性是独立于语言 selection 的第二个瓶颈。

候选统计与 Oracle 必须区分：IoU 0.3/0.5/0.7 的候选覆盖为 75.32%/73.75%/69.84%，但这些覆盖率不是 HOTA。完整数字见 [`analysis/flexhook_candidate_ceiling.csv`](../analysis/flexhook_candidate_ceiling.csv)、[`analysis/oracle_results.csv`](../analysis/oracle_results.csv) 和 run 目录中的 `trackeval_o*.log`。

YesTrack 的 O0/O1/O2/O3 仍为 `BLOCKED`，因为官方 archive/权重/候选字节未取得；没有把 FlexHook Oracle 数字移植给 YesTrack。
