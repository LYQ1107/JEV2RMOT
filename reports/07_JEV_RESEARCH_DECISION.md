# JEV 研究决策

## 结论：有空间，且共享候选已完成

统计已经闭环：

- YesTrack native O0：HOTA 41.155（V2 推荐 threshold 0.60），官方候选 recall@IoU0.5 为 57.870%；
- FlexHook native O0：HOTA 42.526，A800 候选 recall@IoU0.5 为 73.746%；
- 同一 FlexHook 候选、同一 A800 GT、同一 TrackEval：YesTrack shared O0@0.60 HOTA 47.607，FlexHook O0 HOTA 42.526；
- 受控 shared 差值为 HOTA +5.081、DetA +7.315、AssA +0.633、IDF1 +8.806；
- 同一候选的 O1/O2 为 HOTA 65.423/69.125，且与 FlexHook O1/O2 完全一致；
- shared 候选仍缺失 26.254% GT boxes，native YesTrack 候选缺失 42.130%。

所以答案是：有可提升空间，而且证据足以支持开发一个窄的候选内 JEV；但普通二阶段不能凭空恢复候选缺失，O1/O2 也不能直接包装成实际收益。

## 七个决策问题

| 问题 | 结论 | 证据 |
|---|---|---|
| 是否存在候选出现却被二阶段误判？ | YES | shared YesTrack @0.60 有 34,503 个 selection FN 和 276,224 个 selection FP；native YesTrack 为 27,345/198,536 |
| 是否存在可利用的身份断裂和 IDSW？ | YES | shared O1 IDSW 4,601、O2 为 0；candidate proxy 仍有 3,381 次切换 |
| 联合多个候选能否提供独立信息？ | PLAUSIBLE | 共享候选中 FP 规模大，同帧竞争和表达式语义有可利用信息；需先做规则 baseline |
| 历史语言/视觉证据是否能纠错？ | PLAUSIBLE, 未完成因果证明 | TRP/TCP 语义已运行，但尚未做开关/窗口消融 |
| 简单阈值和时序规则能否解决大部分？ | 尚未证明 | native threshold sweep 最高 HOTA 仅 41.179；共享候选还需按表达式/竞争结构做校准 |
| 相同候选下谁更强？ | YesTrack shared O0 更强 | 同一 A800 GT：47.607 vs 42.526；阈值 0.50 时 shared YesTrack 为 47.284，结论不变 |
| 是否值得继续训练 JEV？ | YES，限定为候选内联合决策 | selection/identity headroom 已被同候选统计隔离，下一步先做 frozen-candidate baseline |

## 推荐研究顺序

1. 先跑不训练 baseline：全局/按表达式阈值、同帧竞争抑制、分数校准和简单轨迹 ID 稳定规则。
2. 固定 shared candidate，分别关闭 video refinement、TCP、TRP，区分模型判断、传播和候选 ID 的作用。
3. 只有规则不能解释主要 FN/FP 后，才训练 JEV；输入包括表达式语义、候选框、同帧竞争候选、Track ID 历史和短时视觉状态。
4. 以 O0 -> rule -> JEV 的 HOTA/DetA/AssA/IDF1、candidate recall、IDSW 和 0019/关系类别分层结果作为验收。

不要把候选缺失、IoU 不足、FlexHook 末帧窗口缺口或 O3 GT sanity 包装成 JEV 能力。完整数字见 `analysis/yestrack_official_run_receipt.json`、`analysis/metrics.csv`、`analysis/candidate_coverage.csv` 和 `analysis/oracle_results.csv`。
