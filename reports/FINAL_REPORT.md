# FINAL_REPORT

## 结论先行

有可提升空间，但不是“JEV 可以把第一阶段漏检全部救回来”。FlexHook Refer-KITTI-V2 的真实官方 O0 为 **HOTA 42.526 / DetA 30.629 / AssA 59.185 / IDF1 46.496**。固定同一候选池做离线反事实后：

- 完美 selection：O1 HOTA **65.423**，相对 O0 **+22.897**；
- selection + identity：O2 HOTA **69.125**，相对 O1 再 **+3.702**；
- GT sanity：O3 四项指标均 **100**，仅证明评测协议正确，不是方法收益。

因此 JEV 值得做，但研究切口应是“已有候选上的 selection + 竞争关系 + identity/短时状态联合决策”。第一阶段候选覆盖 IoU 0.5 只有 **362,304/491,286=73.746%**，至少 **26.254%** GT-frame 无候选；这部分不能靠冻结二阶段 JEV 修复。

## 实测错误来源

| 类别 | 数量 | 解释 |
|---|---:|---|
| 候选缺失 `CANDIDATE_MISSING` | 128,982 | GT-frame 的 26.254%，第一阶段/几何/帧协议问题 |
| 官方窗口缺口 `MODEL_WINDOW_MISSING` | 7,750 | DataLoader 末帧采样边界导致没有 raw score，不能算语言错误 |
| 合格候选上的选择假阴性 | 40,412 | 有候选、有 raw score 但 argmax 判 No，11.398% |
| 选择假阳性 | 436,690 | 750,832 个正决策中未匹配当前表达式目标，58.161% |

假阴性平均 `p_yes≈0.10`，假阳性平均 `p_yes≈0.93`；错误不只是一个全局阈值附近的抖动。0019 是主失败视频：候选缺失 88,282、选择假阴性 18,607、选择假阳性 338,301。

## 官方复现状态

FlexHook 已完成 4-GPU 官方 forward，297,706 validation samples、862 expression sequences，raw result SHA-256 为 `4af904f8ea839c9cf00c6fa6e6ee5d85d799c116e89019b29da6a183b18c5c3d`；checkpoint SHA-256 为 `71dbd691e7633a3d20facb1ebc405908863aff786e5af30899d4cb666250d613`。详细 receipt 见 [`analysis/flexhook_official_run_receipt.json`](../analysis/flexhook_official_run_receipt.json)。

YesTrack 仍为 `BLOCKED`：官方 Baidu 分享页能列出 `/Yestrack/yestrack.zip`，但普通直连下载返回 `errno=113` 签名错误。没有把 A800 上的 OneJev/GroundJEV 资产或论文数字冒充 YesTrack 实测，因此 YesTrack HOTA/IDF1 和同候选比较仍留空。

## Oracle 解释

O1 保留原候选 bbox 和原 Track ID，只用 GT 选择 IoU≥0.5 的候选；O2 在 O1 框上将 ID 映射到 GT ID；O3 使用 GT 框/ID 做评测 sanity。三者都在模型 forward 之后生成，不参与 O0。

O1–O0 的 +22.897 HOTA 是选择/过滤和官方窗口覆盖的理想差距，不是 JEV 实际提升；O2–O1 的 +3.702 HOTA 是身份连续性的离线理想空间。候选覆盖率、Oracle 表和 raw-score 错误汇总分别见：

- [`analysis/oracle_results.csv`](../analysis/oracle_results.csv)
- [`analysis/flexhook_candidate_gap_breakdown.csv`](../analysis/flexhook_candidate_gap_breakdown.csv)
- [`analysis/flexhook_model_error_summary.csv`](../analysis/flexhook_model_error_summary.csv)

## 对 RMOT2JEV 的建议

先不要做“全模态端到端 JEV 替换”。推荐顺序：

1. 修复并固定官方 DataLoader 末帧窗口协议，确保候选 frame-object 都有 raw score。
2. 在冻结候选和官方分数上比较全局/表达式阈值、同帧竞争抑制、简单 ID 稳定规则。
3. 若简单规则不能解释主要 FN/FP，再训练 JEV；输入应包含表达式、候选框、同帧竞争候选、Track ID 历史和短时视觉状态。
4. 以 O0→规则→JEV 的 HOTA/DetA/AssA/IDF1，以及 0019 和关系类型分层结果作为验收。

当前证据足以支持“做一个窄的候选内 JEV”，不足以支持“JEV 能解决主要端到端瓶颈”或“立即做跨方法结论”。

## 交付状态

项目整体仍为 `PARTIAL`：FlexHook V2 已完成；YesTrack 官方资源和公平共享候选比较仍 `BLOCKED/NOT_COMPARABLE`。所有缺失项都保留明确状态，没有用 0、论文数字或 Oracle 数字冒充模型结果。
