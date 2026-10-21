# Oracle headroom

## 状态

Selection Oracle、Selection + Identity Oracle 和 GT sanity 均为 `BLOCKED`。`analysis/oracle_results.csv` 已为 O0–O3 预留可追溯记录，但没有填入 0 或推算的 HOTA。

## 预定定义

| Oracle | 允许的理想化操作 | 本轮阻塞原因 |
|---|---|---|
| O0 | 官方二阶段原生输出 | 没有官方权重、候选、GT |
| O1 | 在同一候选池上使用 GT 完美选择 | 没有经过核验的候选池 |
| O2 | O1 加身份连续性/身份选择 | 没有候选 ID 与完整 GT 对齐 |
| O3 | GT/帧/seqmap sanity | KITTI 图像/标签链接断裂 |

历史 TempRMOT 目录中的 `predict.txt` 不是候选池，而是历史最终结果；把它用于 O1 会把选择结果当候选输入，产生循环定义，因此没有计算。

## 解阻塞后的计算要求

对每帧候选和 GT 做合法一对一匹配，至少报告 IoU 0.3/0.5/0.7 的 candidate recall ceiling，再用官方 TrackEval 计算 O0/O1/O2。O1–O0 只代表选择 headroom；O2–O1 才能讨论身份/关联 headroom；二者均不能代替第一阶段检测覆盖率。

