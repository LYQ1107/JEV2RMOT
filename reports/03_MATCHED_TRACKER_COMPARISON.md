# 共享候选比较

## 结论

状态：`BLOCKED_SHARED_YESTRACK`。FlexHook 原生 V2 已完成，使用 A800 的公共 `Temp-NeuralSORT-kitti2` 候选得到 O0 HOTA 42.526；但 YesTrack 官方 `v2best_track_result`/权重仍未下载，因此公平第二阶段比较尚未执行。

用户指定的公共候选是 FlexHook 的 `Temp-NeuralSORT-kitti2`，再分别接入 YesTrack 与 FlexHook 的第二阶段。A800 已有 FlexHook 候选及其 GT-free runtime 映射；YesTrack 官方 `v2best_track_result` 仍只有 Baidu 目录元数据。NAS 中存在 TempRMOT 的历史最终 `predict.txt`，但它已经经过目标表达式选择，不能反向恢复候选池，也不能证明与 `Temp-NeuralSORT-kitti2` 同源。

因此不能用“两个原生结果的 HOTA 差值”解释成语言模块收益。FlexHook 的 O0/O1/O2 只能回答 FlexHook 自己的候选内 headroom，不能外推 YesTrack。`analysis/candidate_coverage.csv` 保留阻塞记录。

## 必须完成的公平协议

解阻塞后应先固定同一视频、同一表达式、同一候选行和同一帧索引；复制候选到两个独立输出目录；只替换二阶段；保存 raw score/logit、最终概率、最终选择、候选 ID 和最终 ID；最后使用同一 GT/seqmap 和官方 TrackEval。

任何一方无法接受同一候选格式时，应输出 `NOT_COMPARABLE`，并报告格式适配是否改变 bbox、frame 或 ID，而不是静默转换。

