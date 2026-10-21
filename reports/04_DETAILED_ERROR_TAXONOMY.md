# 详细错误分类

A800 的完整图像/标签和 FlexHook 候选已经可读，但全量模型预测尚未完成，因此 `analysis/error_events.csv` 和 `analysis/temporal_error_chains.csv` 暂为空；这表示没有可合法标注的模型事件，不表示错误率为零。独立候选覆盖统计已完成：IoU 0.5 下 `362,304/491,286 = 73.75%` 的 GT 目标框有候选覆盖，剩余 `26.25%` 属于 JEV 无法通过二阶段选择修复的候选缺失/几何类上限问题。

## 预定标签

| 标签 | 定义 | 可归因的决策环节 |
|---|---|---|
| `geometry/detection` | 候选没有覆盖 GT 或 bbox/帧错位 | 第一阶段/输入协议，JEV 通常不能修复 |
| `selection/false_negative` | 候选存在但被判 No | 语言选择/分数边界 |
| `selection/false_positive` | 非目标候选被判 Yes | 语言选择/分数边界 |
| `identity/fragmentation` | 目标候选存在但 ID 断裂或切换 | 关联/身份状态 |
| `temporal_propagation` | TCP/TRP 或缓存把错误延续到后续帧 | 时序决策 |
| `alignment/protocol` | frame、seqmap、逗号表达式或 GT 映射错误 | 评测协议，不能归因模型 |
| `unresolvable_by_selection` | 候选缺失/几何错误，即使完美 Yes/No 也无法修复 | 第一阶段 |

## 代码层面的已验证风险

- YesTrack 的最终输出沿用候选 bbox 和 ID；二阶段主要修改 confidence/选择，不能凭空生成缺失候选。
- FlexHook `test_utils.py` 的最终决策是 `argmax(score)>0`，没有基于 bbox 的二阶段修正；其 raw logits 在 `main.py:653–667` 可保存，后续应使用 logits 直接判定错误边界。
- FlexHook 对候选帧做前后偏移，任何未核对首帧的结果都可能被错误标记为几何或选择失败。
- `all/gt.txt` 特殊分支现在可以在 A800 evaluation copy 上做独立审计；全量结果尚未封存，不能把该潜在误归因写成已发生事件。

## 候选层错误拆分（IoU 0.5）

这部分统计不使用 FlexHook 未完成的模型输出，只回答“候选本身能不能覆盖目标”：

| 视频 | 候选覆盖 | 缺失目标框 | 最长连续缺失 | 候选 ID 切换 | 发生切换的目标轨迹 |
|---:|---:|---:|---:|---:|---:|
| 0005 | 86.88% | 5,734 / 43,688 | 34 帧 | 326 | 272 / 1,333（20.41%） |
| 0011 | 73.64% | 27,449 / 104,124 | 92 帧 | 189 | 177 / 1,479（11.97%） |
| 0013 | 79.26% | 7,517 / 36,248 | 30 帧 | 381 | 336 / 1,455（23.09%） |
| 0019 | 71.26% | 88,282 / 307,226 | 77 帧 | 3,829 | 1,578 / 3,776（41.79%） |

因此 0019 是候选层的主要失败视频，不能把它的 28.74% 缺失归因给 JEV。最差表达式簇也集中在 0019；例如 `humans` 有 `1,817/6,047` 个目标框没有候选，覆盖率 69.95%，最长缺失段 77 帧。逐表达式结果见 [`analysis/flexhook_top_expression_misses.csv`](../analysis/flexhook_top_expression_misses.csv)，按视频汇总见 [`analysis/flexhook_candidate_error_summary.csv`](../analysis/flexhook_candidate_error_summary.csv)。

用户要求“每类至少一个无法由简单二阶段修复的反例”。在 FlexHook 全量结果封存前，本轮仍无法诚实构造或可视化这些反例，故保持 `PENDING`；A800 资源到位后优先从四个测试视频生成反例，而不是用历史 TempRMOT 结果替代。

