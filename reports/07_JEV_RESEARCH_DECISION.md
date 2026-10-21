# JEV 研究决策

## 结论：有空间，但应做窄切入，不应先做端到端替换

FlexHook V2 的实测闭环已经给出明确证据：

- O0=42.526 HOTA；
- 同候选 GT selection oracle O1=65.423，理论选择差距 +22.897 HOTA；
- O1 加 identity oracle O2=69.125，再增加 +3.702 HOTA；
- 但 IoU 0.5 候选覆盖只有 73.746%，26.254% GT-frame 不可能由冻结二阶段修复；
- 在有合格候选和 raw score 的 GT-frame 上，假阴性 40,412、假阳性 436,690，且假阳性平均 `p_yes≈0.93`。

因此答案是：有可提升空间，而且主要存在于已有候选上的选择/竞争关系；但不能把 O1–O0 直接承诺为 JEV 收益，因为其中还包含官方窗口缺口和理想 GT 选择。身份关联的独立理想空间较小但真实存在：O2–O1 为 3.702 HOTA points。

## 六个决策问题

| 问题 | 结论 | 证据 |
|---|---|---|
| 是否有候选出现却被二阶段误判？ | YES | 40,412 个合格候选上的假阴性，436,690 个假阳性保留候选 |
| 是否有可利用的身份断裂/IDSW？ | YES | O1 IDSW 4,601，O2 identity oracle 为 0；候选 proxy 有 4,725 次切换 |
| 多候选能否提供独立信息？ | INSUFFICIENT_EVIDENCE | 假阳性规模很大，但本轮尚未做竞争候选消融 |
| 历史语言/视觉证据能否纠错？ | INSUFFICIENT_EVIDENCE | 连续链已统计，但尚未做窗口/历史消融证明因果 |
| 简单阈值/时序规则能否解决大部分？ | NO（全局阈值）/尚未证明（时序） | FN 平均 p_yes 约 0.10、FP 平均 p_yes 约 0.93，错误不是单一边界噪声 |
| 相同候选下 YesTrack 与 FlexHook 谁更强？ | INSUFFICIENT_EVIDENCE | YesTrack 官方 archive/权重/候选仍 BLOCKED |
| 是否值得继续训练 JEV？ | YES，限定为候选内联合决策 | 先做 frozen-candidate selection + identity/short-term state，对照 O0/O1/O2 |

## 推荐研究切口

1. 先修复/记录官方 DataLoader 末帧窗口问题，确保 raw score 覆盖完整候选池。
2. 在同一候选上做不训练的 baseline：全局阈值、按表达式阈值、候选竞争抑制、简单轨迹 ID 稳定规则。
3. 只有当这些规则不能解释 40,412 FN/436,690 FP 的主要部分时，才训练 JEV；输入应包括表达式、候选框/ID、候选历史和同帧竞争候选。
4. 以 O0→规则→JEV 的 HOTA/DetA/AssA/IDF1 和按视频/关系类型的错误变化为验收标准。

不要把 26.254% 候选缺失、1.577% 官方窗口缺口或 bbox 几何错误包装成 JEV 能力。YesTrack 仍未取得官方字节前，不做跨方法强结论。
