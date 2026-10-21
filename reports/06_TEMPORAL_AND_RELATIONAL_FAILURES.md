# 时间与关系型失败

## 已完成的实测

FlexHook raw result 已封存。每个候选帧包含 `negative_logit/positive_logit`，最终决策为 `argmax(score)>0`；O0 的 TrackEval 为 HOTA 42.526、IDSW 2,908。离线对齐得到 40,412 个合格候选上的选择假阴性和 436,690 个选择假阳性，连续事件链见 [`analysis/temporal_error_chains.csv`](../analysis/temporal_error_chains.csv)。

连续链是描述性证据，不等同于已证明的 TCP/TRP 传播：FlexHook 没有 YesTrack 的 TCP/TRP 开关，且模型使用 4-frame window。要把链归因成“上一帧错误导致下一帧错误”，仍需同一候选上的窗口消融或逐帧重放；本轮没有把这种因果关系写成已证事实。

## 候选层与身份层

IoU 0.5 下，0019 的候选缺失 88,282/307,226 GT-frame，最长连续缺失 77 帧；全局候选 ID proxy 有 4,725 次切换、2,363/8,043 条目标轨迹发生切换。O1 保留候选原 ID 后 IDSW=4,601，O2 做 GT identity mapping 后 IDSW=0，HOTA 从 65.423 增到 69.125。这给出了“身份/短时关联”可研究但不能直接承诺可实现的空间。

另有 314 个候选 frame-object 条目因官方 DataLoader 的末帧采样边界没有 raw score，对应 7,750 GT-frame，单列为 `MODEL_WINDOW_MISSING`。它属于官方输入窗口实现/评估协议边界，不应被 JEV 归因。

## 关系型研究含义

假阳性平均 `p_yes` 约 0.93，且主要集中在 0019；假阴性平均 `p_yes` 约 0.10。仅调一个全局阈值很难同时消除两类高置信错误。更合理的 JEV 入口是：在同一候选池上联合表达式语义、候选之间的竞争关系、空间/运动历史和候选 ID 连续性，再对 selection/identity 做决策。

但第一优先级仍是候选覆盖和窗口协议：至少 26.254% GT-frame 没有 IoU 0.5 候选，另有 1.577% 被官方测试窗口漏掉。普通二阶段模型不能凭空恢复这两类目标。
