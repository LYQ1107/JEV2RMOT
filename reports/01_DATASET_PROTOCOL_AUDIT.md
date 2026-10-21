# 数据集与协议审计

## 审计结果

V1/V2 未混用。A800 上已找到完整的 Refer-KITTI-V2 表达式、labels_with_ids 和 image_02 文件树；FlexHook 的 evaluation copy 还包含 `labels.json`、`gt_template` 与数据元数据。YesTrack 官方权重/候选仍未从公开 Baidu 包落地，因此 YesTrack 官方推理仍阻塞；FlexHook 已完成 4-GPU 官方 checkpoint forward、快速结果物化和 862 expression 的 TrackEval O0。

## YesTrack 约束

[YesTrack 的 `docs/USAGE.md`](https://github.com/ggbondrighthere24/YesTrack/blob/ed42b8315b28c94dc595d83b0d49bf57002bb281/docs/USAGE.md) 明确要求数据根目录同时包含 `KITTI/`、`expression/`、`KITTI/labels_with_ids/`；官方发布资源应分别是 `v1bestweight`、`v2bestweight`、`v1best_track_result`、`v2best_track_result` 和匹配的 MOTC GT。A800 已满足数据树一侧，但官方 YesTrack 发布包尚未下载，故不能用用户自训 OneJev/GroundJEV checkpoint 充当这些文件。

V1 评测必须保留官方完整 158-entry seqmap；不能用 TempRMOT/TransRMOT 的缩减 seqmap 代替。V2 表达式文件名含逗号，seqmap 必须 CSV-safe，目录名和 GT 表达式名必须逐一匹配。当前 V2 expression 目录确实存在含逗号的文件名，说明不能用简单逗号分割或手工重命名。

## FlexHook 约束

`configs/infer/kitti2.yaml` 将数据根设为 `./datasets/refer-kitti-v2`、候选根设为 `./tracker_outputs/Temp-NeuralSORT-kitti2`。`infer.sh` 的 V2 配置使用 `SOTA_ckpts/refer-kitti-v2-best`。A800 已提供这三类资源的可读副本；运行时映射为 `/data3/user/TTA-RMOT-assets/flexhook/refer-kitti-v2-runtime`、`.../Temp-NeuralSORT-kitti2-runtime` 和官方 checkpoint，后者由日志记录 SHA256 `71db...d613`。

FlexHook 测试 DataLoader 对 KITTI 读取 `<video>/car/predict.txt` 与 `<video>/pedestrian/predict.txt`，并在 `data/mydataloader.py` 中对非 MIX 轨迹执行 `frame_id = int(frame[0]) - 1`。这是一个必须在真实候选上验证的帧偏移，不可凭目录名猜测。

## GT 读取与潜在误归因

`test_utils.py:75–94` 的 `generate_final_results` 先尝试读取 `track_dir/<video>/all/gt.txt`，失败后才回退到 car/pedestrian `predict.txt` 合并。该 `all/gt.txt` 的语义不能仅由文件名判断；必须对 A800 上的官方 FlexHook `tracker_outputs` 做内容/生成链审计，确认没有把 GT 送入模型输入或决策。全量结果尚未封存，本轮仍没有把该分支行为当作最终基线。

`test_utils.py:110–122` 以 `argmax(score)>0` 做最终二分类选择，`thr_score` 参数没有改变这一判断。该实现意味着 FlexHook 原生输出的决策边界是 logits 的 argmax，而不是可直接与 YesTrack 的概率阈值 `.6` 对齐的固定阈值。

## 帧映射表

| 环节 | 预期映射 | 本轮状态 |
|---|---|---|
| YesTrack `results_root` | MOT 1-based、图像通常 `000000.png`：`image = raw_mot - 1 + offset` | 已从代码/文档核对，未在真实图像上可视化 |
| YesTrack GT converter | MOTC GT 固定写为 1-based；V2 需核对 JSON key convention | 已核对代码/文档，缺数据无法执行 |
| FlexHook KITTI candidate loader | 读候选帧后减 1，供模型使用 | 已核对代码；A800 候选已到位，首帧对照待全量输出 |
| FlexHook final writer | 非 MIX 分支将内部帧再加 1 | 已核对代码；862 expression 的结果已物化并通过官方 TrackEval O0 |

后续真实运行必须保存首帧五行 raw MOT、图像文件名、JSON key、模型输入 frame id 和最终输出 frame id；并用 GT/pred 叠加图检查首帧、末帧和一条长轨迹。

## 可读资产的范围

A800 的 `refer_kitti_v2/expression` 有 21 个视频目录、9758 个表达式文件，`image_02` 有 8008 张图；测试视频为 0005/0011/0013/0019，候选目录含 8 个 `gt/predict.txt` 对。历史 TempRMOT 结果仍然只是辅助资产，不是共享候选池；详情见 [`legacy_temprmot_v2_video_summary.csv`](../analysis/legacy_temprmot_v2_video_summary.csv)。

