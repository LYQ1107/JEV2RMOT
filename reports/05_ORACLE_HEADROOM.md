# Oracle headroom

## 状态

YesTrack 的 Selection/Identity Oracle 仍为 `BLOCKED`；FlexHook 的 O0 已随 A800 全量推理 `RUNNING`，O1/O2/O3 等待 raw output 封存与 GT/帧协议 sanity。独立于模型前向的候选覆盖统计已经完成，但它不是 O0/O1/O2，也不产生 HOTA。`analysis/oracle_results.csv` 保留可追溯状态，没有填入 0 或推算的 HOTA。

## 已完成的候选覆盖统计

对 A800 FlexHook 的 4 个测试视频、862 个 `gt_template` 表达式逐帧做一对一 IoU 匹配，候选使用官方 `Temp-NeuralSORT-kitti2` 的 car/pedestrian `predict.txt` 并按官方代码拼接 ID。结果见 [`analysis/flexhook_candidate_ceiling.csv`](../analysis/flexhook_candidate_ceiling.csv)：

| IoU | 匹配目标框 | 目标框总数 | 候选覆盖上限 | 严格全表达式覆盖 |
|---:|---:|---:|---:|---:|
| 0.30 | 370,039 | 491,286 | 75.32% | 10.32%（89/862） |
| 0.50 | 362,304 | 491,286 | 73.75% | 9.74%（84/862） |
| 0.70 | 343,094 | 491,286 | 69.84% | 9.74%（84/862） |

因此在 IoU 0.5 下，至少 `26.25%` 的目标框没有任何候选覆盖，JEV 的 selection/identity 决策无法修复这部分。严格全表达式覆盖很低是因为一个表达式只要任一目标帧缺候选就算失败，不应当直接当作 HOTA。

缺口进一步拆分见 [`analysis/flexhook_candidate_gap_breakdown.csv`](../analysis/flexhook_candidate_gap_breakdown.csv)：IoU 0.3 时不可覆盖框为 `121,247/491,286 = 24.68%`，收紧到 0.5 后为 `128,982 = 26.25%`，收紧到 0.7 后为 `148,192 = 30.16%`。因此从 0.3 到 0.5 的额外几何损失为 7,735 框，从 0.5 到 0.7 的额外损失为 19,210 框；这些数字是候选质量诊断，不是模型选择错误事件。0019 贡献了 IoU 0.5 全局缺失框的 `68.45%`，应优先排查其候选生成与帧/类别协议。

候选 ID 诊断见 [`analysis/flexhook_identity_proxy.csv`](../analysis/flexhook_identity_proxy.csv)：IoU 0.5 下平均 ID purity 为 `93.51%`，但有 `2,363/8,043` 个 GT 轨迹出现至少一次候选 ID 切换；这说明身份/时序仍有空间，但第一瓶颈更像候选覆盖而不是纯身份选择。

## 预定定义

| Oracle | 允许的理想化操作 | 本轮阻塞原因 |
|---|---|---|
| O0 | 官方二阶段原生输出 | YesTrack 资源缺失；FlexHook 全量推理仍在运行 |
| O1 | 在同一候选池上使用 GT 完美选择 | FlexHook 候选已找到，但预测/raw receipt 尚未封存 |
| O2 | O1 加身份连续性/身份选择 | 等待候选 ID、输出和完整 GT 对齐 |
| O3 | GT/帧/seqmap sanity | A800 数据已找到，尚未完成独立 sanity receipt |

历史 TempRMOT 目录中的 `predict.txt` 不是候选池，而是历史最终结果；把它用于 O1 会把选择结果当候选输入，产生循环定义，因此没有计算。

## 解阻塞后的计算要求

对每帧候选和 GT 做合法一对一匹配，至少报告 IoU 0.3/0.5/0.7 的 candidate recall ceiling，再用官方 TrackEval 计算 O0/O1/O2。O1–O0 只代表选择 headroom；O2–O1 才能讨论身份/关联 headroom；二者均不能代替第一阶段检测覆盖率。

