YesTrack 和 FlexHook 到底还有多少可修复空间，错误主要在哪里，JEV 该不该做、应该切入哪一个决策环节？

# FINAL_REPORT

当前仍不能诚实给出最终官方 HOTA/IDF1：交付状态是 `PARTIAL`，其中 FlexHook 为 `RUNNING/未完成`、YesTrack 为 `BLOCKED`。但候选级可修复空间已经统计：A800 FlexHook 的 862 个测试表达式、491,286 个目标框中，IoU 0.5 下有 362,304 个被候选覆盖，即 73.75%；至少 26.25% 不可能由 JEV 二阶段选择/身份决策修复。A800 已找到完整 Refer-KITTI-V2 数据、官方 FlexHook checkpoint 和 `Temp-NeuralSORT-kitti2` 候选，并启动了官方全量推理；最后可见日志为 `500/7443`，暂未出现最终结果。YesTrack 官方 Baidu 包已能列出 `/Yestrack/yestrack.zip`，但普通直连下载接口返回签名错误，官方 Yes/No 权重和候选字节尚未取得。没有把论文表格、历史 TempRMOT 结果或 A800 上的自训 OneJev 权重当成本地官方指标。

已完成：

- 固定并核验 YesTrack、FlexHook、LLM2Jev 官方仓库 commit；
- 完成 GPU、磁盘、NAS、远端挂载、Python 环境与模型缓存审计；
- 核对 V1 158-entry seqmap、V2 逗号表达式、YesTrack frame mapping、FlexHook 候选帧偏移、`all/gt.txt` 分支、argmax 决策和 result 缓存；
- 发现并记录 FlexHook 原始 checkout 中 `SwinTransformer/utils.py:22` 与 `deit/main.py:44` 的语法错误；未修改官方代码；
- 对历史 TempRMOT V2 输出抽样 40 个表达式对，仅做格式/结构审计，明确标记为 `AUXILIARY_NOT_COMPARABLE`；
- 生成了所需 CSV、Oracle 状态表和空的错误事件表，未填假数字。
- 对 A800 FlexHook 候选完成 IoU 0.3/0.5/0.7 覆盖统计和候选 ID proxy 统计；结果写入 [`analysis/flexhook_candidate_ceiling.csv`](../analysis/flexhook_candidate_ceiling.csv) 与 [`analysis/flexhook_identity_proxy.csv`](../analysis/flexhook_identity_proxy.csv)。
- 进一步按视频和表达式拆分候选缺失、最长连续缺失段与候选 ID 切换；0019 的候选覆盖最低（71.26%），缺失 88,282 个目标框、3,829 次 ID 切换，结果见 [`analysis/flexhook_candidate_error_summary.csv`](../analysis/flexhook_candidate_error_summary.csv)。
- 将候选层的“不可修复缺口”单独统计：IoU 0.3/0.5/0.7 下分别有 24.68%/26.25%/30.16% GT 框没有候选；从 0.3 收紧到 0.5 额外损失 7,735 框，从 0.5 收紧到 0.7 额外损失 19,210 框。0019 一条视频贡献了 IoU 0.5 全部缺失框的 68.45%；8,043 条目标轨迹中 501 条完全没有候选匹配，2,363 条出现候选 ID 切换。可复算明细见 [`analysis/flexhook_candidate_gap_breakdown.csv`](../analysis/flexhook_candidate_gap_breakdown.csv)，生成脚本见 [`scripts/write_flexhook_candidate_gap_breakdown.py`](../scripts/write_flexhook_candidate_gap_breakdown.py)。
- 重新清点 A800，生成 [`analysis/a800_resource_manifest.csv`](../analysis/a800_resource_manifest.csv)，记录完整数据、FlexHook 官方 checkpoint、TempRMOT baseline checkpoint/R50 pretrain、文件大小和非官方 YesTrack 实验资产边界；未复制大权重进 Git 仓库。

## 直接回答：有没有可提升空间

有，但当前证据把空间分成两段：

| 环节 | 当前统计 | 对 JEV 的含义 |
|---|---:|---|
| 候选覆盖/检测 | IoU 0.5 仅覆盖 73.75%，26.25% 无候选 | 这部分不是二阶段 JEV 的可修复空间；应先修候选生成、检测或帧对齐，尤其是 0019 |
| 候选框质量 | IoU 0.3→0.5 少 7,735 框，0.5→0.7 少 19,210 框 | 主要是几何/定位质量，不能直接归因给语言选择 |
| 候选身份/时序 | 2,363/8,043 条目标轨迹有候选 ID 切换，4,725 次切换 | 这是 JEV 可以优先尝试的联合 selection + identity/短时状态决策入口，但仍是候选 proxy，不是官方 IDF1 |

因此，若问题是“JEV 能不能让端到端 RMOT 明显提升”，目前不能只凭候选统计承诺；第一阶段覆盖已经给出硬上限。若问题是“JEV 是否值得做”，答案是有条件地值得：应把研究切口放在已有候选上的语言选择、身份连续性和短时轨迹状态联合决策，并用同一候选池的 O0→O1、O1→O2 差值验证，而不是从第一阶段漏检开始归因。当前 O0/O1/O2 尚未封存，故这些差值仍不能填写。

因此目前能说的科学结论只有机制级结论：JEV 若继续，优先切入已有候选上的 selection + identity/short-term state decision；不能宣称它能修复候选缺失、bbox 几何错误或协议错位。是否值得做、可修复空间的大小，必须等 O0/O1/O2 和共享候选跑通后由数字决定。

主结果表见 [`analysis/metrics.csv`](../analysis/metrics.csv)，其中 FlexHook 记录为 `RUNNING`、YesTrack 仍为 `BLOCKED`；Oracle 见 [`analysis/oracle_results.csv`](../analysis/oracle_results.csv)。资源和阻塞证据见 [`00_RESOURCE_AUDIT.md`](00_RESOURCE_AUDIT.md)。

## 解阻塞后的最短闭环

下一步仍需等待/监控 A800 FlexHook 全量运行，封存 raw score/logit、代码/权重 receipt 和预测目录，再计算官方 O0/O1/O2、模型错误事件、模型时间链和 30 个可视化案例；候选 recall ceiling 已完成。并行地，YesTrack 需要官方 `yestrack.zip` 的真实下载字节；拿到后再运行同一候选池比较。只有完成这条闭环后，才能把 JEV 结论从“候选上限已知”升级为“模型 O0→Oracle 的实际收益已知”。

