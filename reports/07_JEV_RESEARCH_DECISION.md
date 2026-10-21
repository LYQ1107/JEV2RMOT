# JEV 研究决策

## 当前决策：暂缓正向结论，保留窄切入点

候选覆盖统计已经给出第一个数字边界，但官方 O0/O1/O2 仍没有运行。A800 FlexHook 候选在 IoU 0.5 下只覆盖 `362,304/491,286 = 73.75%` 的目标框，因此至少 `26.25%` 的目标框不能由 JEV 的二阶段选择或身份决策修复。可计算结果见 [`analysis/flexhook_candidate_ceiling.csv`](../analysis/flexhook_candidate_ceiling.csv)。

进一步的可修复空间分解见 [`analysis/flexhook_candidate_gap_breakdown.csv`](../analysis/flexhook_candidate_gap_breakdown.csv)：IoU 0.3/0.5/0.7 的不可覆盖比例分别为 24.68%/26.25%/30.16%；0019 占 IoU 0.5 全部缺失框的 68.45%。候选层还有身份时序风险：2,363/8,043 条目标轨迹出现候选 ID 切换，但这只是候选 proxy，不能代替官方 IDF1。

所以 JEV 不应直接从 bbox 修复或重新训练第一阶段开始；若继续，应切入已有候选上的联合决策——把语言选择分数、候选身份连续性和短时轨迹状态一起用于 selection/identity decision。但优先级应是“候选/检测覆盖问题 > 选择问题 > 身份时序问题”，而不是先宣称 JEV 有很大的总体收益。

## 为什么是这个环节

- YesTrack 明确把二阶段输出写回候选轨迹，TCP/TRP 也以 track ID 历史为状态。
- FlexHook 保存 raw 二分类 logits，并以 argmax 生成最终结果；这提供了可观测的决策边界。
- 候选缺失、frame 错位和 bbox 几何错误在完美 Yes/No 下仍不可修复，应先从 JEV 的可修复空间中排除。
- A800 候选统计显示，IoU 0.5 下候选框覆盖率为 73.75%；候选 ID 的平均 purity 为 93.51%，但 8,043 条目标轨迹中有 2,363 条出现至少一次候选 ID 切换。这是候选级诊断，不是官方 IDF1。

## 需要的证据门槛

在宣布 JEV 的最终收益之前，仍必须拿到同一候选池上的 O0、O1、O2 和至少 30 个可视化案例；候选统计已证明总体上限受第一阶段覆盖约束，但还不能把 `73.75%` 直接换算成 HOTA，也不能由候选 ID proxy 代替 O2。若 O1–O0 很小，JEV 不能把主要问题说成选择；若 O2–O1 很小，身份模块也不应作为主线。

