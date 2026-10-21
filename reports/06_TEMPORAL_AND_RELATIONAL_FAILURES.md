# 时间与关系型失败

## 已验证的机制

YesTrack 的 TCP 保存每个 track ID 的历史最终 confidence，在窗口满足条件时提升当前分数；TRP 每隔若干帧完整推理，中间帧复用已有 ID 的 confidence。代码和官方文档都说明这些操作发生在候选轨迹之上，不能修复缺失 bbox 或重新建立身份。

FlexHook 的模型输出保存为 `video/object/frame/expression -> [negative_logit, positive_logit]`，随后 `test_utils.py` 依据 argmax 选择并从候选轨迹中取 bbox。该结构允许后续拆解“视觉/语言选择错误”和“候选身份/时序错误”，但本轮没有 raw result.json。

## 本轮没有数值结论

没有完整官方运行，因此没有报告传播持续帧数、错误累积比例、ID switch、断裂长度或关系型错误率。任何这类数字都会把代码机制误写成测量结果。

## 对 JEV 的预判

若资源恢复，优先检查“已有候选下的联合选择 + 身份状态更新”这一决策环节：它有 raw score、候选 ID 和时间邻接，且能与 bbox 覆盖错误严格隔离。不要从当前证据推出 JEV 能修复第一阶段漏检或坐标偏差。

