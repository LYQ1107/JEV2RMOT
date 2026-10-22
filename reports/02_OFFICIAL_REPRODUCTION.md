# 官方复现结果

## 状态

FlexHook Refer-KITTI-V2 已完成官方 checkpoint 的完整 4-GPU 前向、raw logits 封存和 862 表达式 TrackEval。YesTrack V2 的官方归档、LoRA、候选、MOTC GT 和 Qwen3-VL-2B 基座均已取得；862 个表达式的推理和官方 YesTrack evaluator + bundled TrackEval 已完成。

复现边界：本机可用的是 9 张 V100-DGXS，不是用户提到的 A800；V100 不支持原生 bf16，因此 YesTrack 使用 fp16 运行。模型、LoRA、提示词、裁剪、视频精炼、TCP 和 TRP 语义保持官方实现；为使全量运行可完成，独立脚本只把彼此独立的 primary/refine 样本批量送入同一官方 forward helper。原始官方逐帧脚本已对一个完整表达式做 smoke 对照。

## YesTrack V2

代码版本：ed42b8315b28c94dc595d83b0d49bf57002bb281。

官方归档：

- Baidu archive 大小 178,142,422 bytes，SHA-256 为 f303e4f2578ea011cc7861afc359be535e132bbb59308e22726621e37e0ca97b，unzip test 通过；
- V2 adapter 为 34,922,600 bytes，SHA-256 为 749d7c48bc8507105fb068adb539f5ebd58a587402d6e30542675c6e5a050b55；
- V2 候选为 862 个表达式、1,850,576 行；V2 MOTC GT 与 seqmap 同为官方归档内容；
- 基座为 Qwen/Qwen3-VL-2B-Instruct，HF revision 89644892e4d85e24eaac8bacfd4f463576704203。HF 直连超时后才使用 proxy snapshot fallback。

全量 receipt：[analysis/yestrack_official_run_receipt.json](../analysis/yestrack_official_run_receipt.json)。

| 阈值 | HOTA | DetA | AssA | IDF1 | IDSW | DetRe | DetPr | Dets |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.30 | 39.819 | 30.148 | 53.019 | 46.064 | 3652 | 48.137% | 43.025% | 549654 |
| 0.35 | 40.202 | 30.694 | 53.083 | 46.729 | 3581 | 47.736% | 44.491% | 527124 |
| 0.40 | 40.610 | 31.259 | 53.181 | 47.444 | 3481 | 47.324% | 46.079% | 504561 |
| 0.45 | 40.864 | 31.622 | 53.228 | 47.889 | 3388 | 47.025% | 47.177% | 489706 |
| 0.50 | 41.028 | 31.894 | 53.198 | 48.228 | 3316 | 46.690% | 48.144% | 476454 |
| 0.55 | 41.133 | 32.089 | 53.143 | 48.474 | 3250 | 46.363% | 48.959% | 465233 |
| 0.60 | 41.155 | 32.191 | 53.032 | 48.612 | 3169 | 46.004% | 49.618% | 455499 |
| 0.65 | 41.179 | 32.261 | 52.973 | 48.716 | 3085 | 45.619% | 50.255% | 445964 |
| 0.70 | 41.163 | 32.306 | 52.857 | 48.785 | 3018 | 45.208% | 50.888% | 436454 |

GT_Dets 为 491,286。官方文档给出的 V2 起始阈值约为 0.6，因此主指标表和 metrics.csv 采用 0.60；本次 sweep 的 HOTA 最大值是 0.65 的 41.179，而不是事后把最大值冒充预先固定的官方阈值。

全量完整性校验为：source tasks 862、output tasks 862、缺失 0、多余 0；source rows 1,850,576、output rows 1,850,576、frame/id/box row mismatch 0。对 0005/automobiles-are-located-to-the-left 的 1,029 行，原始官方逐帧脚本与批量脚本的结构行和二值决策完全一致；fp16 的最大概率差 0.003907，均值绝对差 0.0001300292，因此不宣称逐浮点数 byte-identical。

## FlexHook 官方 O0

代码版本：bd1acc38634b28525d54dc6e0fcb38335f0029f9。使用官方 configs/infer/kitti2.yaml、--eval、rope-swin-tiny+roberta、A800 找到的 refer-kitti-v2-best.pth 和 Temp-NeuralSORT-kitti2 候选。为避免 SSHFS 图像逐帧 I/O，图像只缓存到本地；候选、runtime expression/labels 和 checkpoint 仍指向官方资源。

运行 receipt：[analysis/flexhook_official_run_receipt.json](../analysis/flexhook_official_run_receipt.json)。raw result 为 227,060,055 bytes，SHA-256 为 4af904f8ea839c9cf00c6fa6e6ee5d85d799c116e89019b29da6a183b18c5c3d；checkpoint SHA-256 为 71dbd691e7633a3d20facb1ebc405908863aff786e5af30899d4cb666250d613。前向使用 4 个空闲 V100，297,706 validation samples，世界大小 4；模型加载日志为 All keys matched successfully。

| 指标 | 数值 |
|---|---:|
| HOTA | 42.526 |
| DetA | 30.629 |
| AssA | 59.185 |
| IDF1 | 46.496 |
| DetRe / DetPr | 63.965% / 41.854% |
| IDSW | 2,908 |
| GT boxes / output detections | 491,286 / 750,832 |
| expression sequences | 862 |

TrackEval 使用官方仓库 evaluator、seqmaps/kitti-2.txt 和 V2 图像/GT 路径。官方 main.py 的 TrackEval 命令对 V2 硬编码 refer-kitti；isolated run 增加 refer-kitti -> refer-kitti-v2 兼容链接后，用相同 evaluator 独立重跑。该修正只解决路径，不改变模型输入、raw logits 或决策。

官方 generate_final_results 在 SSHFS 上会在每个候选帧 × 每个表达式内层重复打开表达式 JSON，前向完成后长时间停在结果落盘。本轮在 raw result.json 已封存后使用预加载表达式映射的等价落盘脚本，保持 argmax(raw_two_class_score)>0、原候选 bbox 和合并 ID 不变；生成结果完整覆盖 862 个 predict.txt。

另发现 FlexHook 测试 DataLoader 的 sample_end=obj_last-sample_frame_num 会使 314 个候选 frame-object 条目没有 raw score，对应 7,750 个 GT-frame，记为 MODEL_WINDOW_MISSING，不归因给语言选择。

## 复现边界

- 没有训练新 JEV，也没有修改官方权重或官方 upstream checkout。
- GT 没有进入模型 forward；GT 只用于 raw output 之后的 TrackEval、错误归因和 Oracle 反事实。
- YesTrack 的原生候选是官方发布的 TempRMOT*，FlexHook 的原生候选是 Temp-NeuralSORT-kitti2；两套原生 HOTA 不能直接解释成二阶段语言模块差异。
- FlexHook 候选已转换成 YesTrack 可读的逐表达式布局；共享候选推理已完成，并用 A800 FlexHook `gt_template` 与同一 bundled TrackEval 对两套结果重评。共享结果不是新的训练权重，只用于隔离二阶段评分/筛选差异。

## 共享候选结果

共用 `Temp-NeuralSORT-kitti2` 后，YesTrack @0.60 为 HOTA 47.607、DetA 37.944、AssA 59.818、IDF1 55.302；同一候选、同一 GT、同一评估器下的 FlexHook O0 为 HOTA 42.526、DetA 30.629、AssA 59.185、IDF1 46.496。对应差值为 +5.081/+7.315/+0.633/+8.806。完整 receipt 在 [`analysis/yestrack_official_run_receipt.json`](../analysis/yestrack_official_run_receipt.json)。
