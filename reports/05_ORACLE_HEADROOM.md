# Oracle headroom

## 状态

YesTrack 的 Selection/Identity Oracle 仍为 `BLOCKED`；FlexHook 的 O0 已随 A800 全量推理 `RUNNING`，O1/O2/O3 等待 raw output 封存与 GT/帧协议 sanity。`analysis/oracle_results.csv` 保留可追溯状态，没有填入 0 或推算的 HOTA。

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

