# 详细错误分类

本轮没有官方预测与完整图像，因此 `analysis/error_events.csv` 和 `analysis/temporal_error_chains.csv` 为空；这表示没有可合法标注的事件，不表示错误率为零。

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
- `all/gt.txt` 特殊分支在真实资源缺失时未被运行；不能把该潜在误归因写成已发生事件。

用户要求“每类至少一个无法由简单二阶段修复的反例”。由于没有完整图像、GT 与候选，本轮无法诚实构造或可视化这些反例，故保持 `BLOCKED`。

