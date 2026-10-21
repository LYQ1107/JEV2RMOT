# 时间与关系型失败

## 已验证的机制

YesTrack 的 TCP 保存每个 track ID 的历史最终 confidence，在窗口满足条件时提升当前分数；TRP 每隔若干帧完整推理，中间帧复用已有 ID 的 confidence。代码和官方文档都说明这些操作发生在候选轨迹之上，不能修复缺失 bbox 或重新建立身份。

FlexHook 的模型输出保存为 `video/object/frame/expression -> [negative_logit, positive_logit]`，随后 `test_utils.py` 依据 argmax 选择并从候选轨迹中取 bbox。该结构允许后续拆解“视觉/语言选择错误”和“候选身份/时序错误”，但本轮没有 raw result.json。

## 候选层时间统计

A800 的 FlexHook 官方全量模型运行仍没有完整 raw result，因此不能报告模型的传播错误或官方 IDF1。但候选层已经可以独立统计：IoU 0.5 下，0005/0011/0013/0019 的最长连续候选缺失分别为 34/92/30/77 帧；候选 ID 切换分别为 326/189/381/3829。对应的覆盖、缺失和轨迹切换汇总见 [`analysis/flexhook_candidate_error_summary.csv`](../analysis/flexhook_candidate_error_summary.csv)。这些帧在候选池中不存在，即使完美 selection 也无法恢复。

## 对 JEV 的预判

若资源恢复，优先检查“已有候选下的联合选择 + 身份状态更新”这一决策环节：它有 raw score、候选 ID 和时间邻接，且能与 bbox 覆盖错误严格隔离。不要从当前证据推出 JEV 能修复第一阶段漏检或坐标偏差。

