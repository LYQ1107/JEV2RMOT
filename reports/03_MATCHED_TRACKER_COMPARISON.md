# 共享候选比较

## 结论

状态：`NOT_COMPARABLE`。本轮没有执行 YesTrack 与 FlexHook 的公平第二阶段比较。

用户指定的公共候选是 FlexHook 的 `Temp-NeuralSORT-kitti2`，再分别接入 YesTrack 与 FlexHook 的第二阶段。当前主机没有该目录；YesTrack 官方 `v2best_track_result` 也没有。NAS 中存在 TempRMOT 的历史最终 `predict.txt`，但它已经经过目标表达式选择，不能反向恢复候选池，也不能证明与 `Temp-NeuralSORT-kitti2` 同源。

因此不能用“两个原生结果的 HOTA 差值”解释成语言模块收益。`analysis/candidate_coverage.csv` 只保留阻塞记录。

## 必须完成的公平协议

解阻塞后应先固定同一视频、同一表达式、同一候选行和同一帧索引；复制候选到两个独立输出目录；只替换二阶段；保存 raw score/logit、最终概率、最终选择、候选 ID 和最终 ID；最后使用同一 GT/seqmap 和官方 TrackEval。

任何一方无法接受同一候选格式时，应输出 `NOT_COMPARABLE`，并报告格式适配是否改变 bbox、frame 或 ID，而不是静默转换。

