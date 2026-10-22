# 数据集与协议审计

## 审计结果

V1/V2 未混用。A800 上已找到完整的 Refer-KITTI-V2 表达式、labels_with_ids 和 image_02 文件树；FlexHook 的 evaluation copy 还包含 `labels.json`、`gt_template` 与数据元数据。YesTrack 官方归档已下载并解压出 V2 adapter、TempRMOT* 候选和 862-expression MOTC GT；Qwen3-VL-2B 基座通过固定 revision 下载。YesTrack V2 已完成全量推理和官方 TrackEval；FlexHook 已完成 4-GPU 官方 checkpoint forward、快速结果物化和 862 expression 的 TrackEval O0。

## YesTrack 约束

[YesTrack 的 `docs/USAGE.md`](https://github.com/ggbondrighthere24/YesTrack/blob/ed42b8315b28c94dc595d83b0d49bf57002bb281/docs/USAGE.md) 明确要求数据根目录同时包含 `KITTI/`、`expression/`、`KITTI/labels_with_ids/`；官方发布资源应分别是 `v1bestweight`、`v2bestweight`、`v1best_track_result`、`v2best_track_result` 和匹配的 MOTC GT。归档已提供这些 V1/V2 资源；本轮 V2 使用官方 adapter、官方候选和官方 GT，基座为 Qwen3-VL-2B-Instruct。A800 上的 OneJev/GroundJEV checkpoint 未被替代使用。

V1 评测必须保留官方完整 158-entry seqmap；不能用 TempRMOT/TransRMOT 的缩减 seqmap 代替。V2 表达式文件名含逗号，seqmap 必须 CSV-safe，目录名和 GT 表达式名必须逐一匹配。当前 V2 expression 目录确实存在含逗号的文件名，说明不能用简单逗号分割或手工重命名。

## FlexHook 约束

`configs/infer/kitti2.yaml` 将数据根设为 `./datasets/refer-kitti-v2`、候选根设为 `./tracker_outputs/Temp-NeuralSORT-kitti2`。`infer.sh` 的 V2 配置使用 `SOTA_ckpts/refer-kitti-v2-best`。A800 已提供这三类资源的可读副本；运行时映射为 `/data3/user/TTA-RMOT-assets/flexhook/refer-kitti-v2-runtime`、`.../Temp-NeuralSORT-kitti2-runtime` 和官方 checkpoint，后者由日志记录 SHA256 `71db...d613`。

FlexHook 测试 DataLoader 对 KITTI 读取 `<video>/car/predict.txt` 与 `<video>/pedestrian/predict.txt`，并在 `data/mydataloader.py` 中对非 MIX 轨迹执行 `frame_id = int(frame[0]) - 1`。这是一个必须在真实候选上验证的帧偏移，不可凭目录名猜测。

## GT 读取与潜在误归因

`test_utils.py:75–94` 的 `generate_final_results` 先尝试读取 `track_dir/<video>/all/gt.txt`，失败后才回退到 car/pedestrian `predict.txt` 合并。已对 A800 上 FlexHook `Temp-NeuralSORT-kitti2` 做内容和生成链审计：运行时使用的是 car/pedestrian `predict.txt`，没有把 GT 文件送入模型输入或决策；全量结果已封存。

`test_utils.py:110–122` 以 `argmax(score)>0` 做最终二分类选择，`thr_score` 参数没有改变这一判断。该实现意味着 FlexHook 原生输出的决策边界是 logits 的 argmax，而不是可直接与 YesTrack 的概率阈值 `.6` 对齐的固定阈值。

## 帧映射表

| 环节 | 预期映射 | 本轮状态 |
|---|---|---|
| YesTrack `results_root` | MOT 1-based、图像通常 `000000.png`：`image = raw_mot - 1 + offset` | 已在 V2 全量推理使用；862/862 表达式、首个单表达式与官方脚本 smoke 通过 |
| YesTrack GT converter | MOTC GT 固定写为 1-based；V2 目录/seqmap 与 862 个输出表达式逐一匹配 | 已使用归档 GT 和 `seqmaps/val.txt` 完成官方 TrackEval |
| FlexHook KITTI candidate loader | 读候选帧后减 1，供模型使用 | 已核对代码；A800 候选已到位，首帧和全量输出已完成 |
| FlexHook final writer | 非 MIX 分支将内部帧再加 1 | 已核对代码；862 expression 的结果已物化并通过官方 TrackEval O0 |

已在 smoke 和全量 run 中保存首帧/末帧的 MOT 行、图像映射和输出结构；后续共享候选复核仍应保留同样的 frame、bbox、ID checksum，并用 GT/pred 叠加图抽查首帧、末帧和长轨迹。

## 可读资产的范围

A800 的 `refer_kitti_v2/expression` 有 21 个视频目录、9758 个表达式文件，`image_02` 有 8008 张图；测试视频为 0005/0011/0013/0019，候选目录含 8 个 `gt/predict.txt` 对。历史 TempRMOT 结果仍然只是辅助资产，不是共享候选池；详情见 [`legacy_temprmot_v2_video_summary.csv`](../analysis/legacy_temprmot_v2_video_summary.csv)。

## 共享候选复核

FlexHook 的 `Temp-NeuralSORT-kitti2` 已按官方 `generate_final_results` 的合并规则转换到 YesTrack 的逐表达式目录。转换只做目录适配和行人 ID offset，不改变 frame、bbox 或候选轨迹；862 个表达式目录与 YesTrack V2 seqmap 完全对应。候选池为 4 个视频共 10,822 行，逐表达式 score 输入为 2,425,382 行。

公平对照使用 A800 FlexHook `gt_template` 和同一 `refer_eval_seqmap` 重评两套结果。原因是 FlexHook GT 保留高精度坐标，而 YesTrack 发布归档的 GT 约保留三位小数；原生 YesTrack 的官方归档评测仍单独保留，不能把两种 GT 的数值直接混成一个 native 表。

