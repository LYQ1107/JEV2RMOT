# 官方复现结果

## 状态

FlexHook Refer-KITTI-V2 已完成官方 checkpoint 的完整 4-GPU 前向、raw logits 封存和 862 表达式 TrackEval。YesTrack 仍因官方发布包下载签名阻塞，不能给出官方实测指标。

## YesTrack

代码版本：`ed42b8315b28c94dc595d83b0d49bf57002bb281`。

官方 Baidu 分享页可以验证提取码并列出 `/Yestrack/yestrack.zip`，但普通直连下载接口返回 `errno=113`，因此 `v1/v2bestweight`、`v1/v2best_track_result` 和完整 YesTrack GT/候选字节尚未取得。本轮没有用 A800 上的 OneJev/GroundJEV 自训资产替代官方 Qwen3-VL/LoRA。

## FlexHook 官方 O0

代码版本：`bd1acc38634b28525d54dc6e0fcb38335f0029f9`。使用官方 `configs/infer/kitti2.yaml`、`--eval`、`rope-swin-tiny+roberta`、A800 找到的 `refer-kitti-v2-best.pth` 和 `Temp-NeuralSORT-kitti2` 候选。为避免 SSHFS 图像逐帧 I/O，图像只缓存到本地；候选、runtime expression/labels 和 checkpoint 仍指向 A800 官方资源。

运行 receipt：[`analysis/flexhook_official_run_receipt.json`](../analysis/flexhook_official_run_receipt.json)。raw result 为 227,060,055 bytes，SHA-256 为 `4af904f8ea839c9cf00c6fa6e6ee5d85d799c116e89019b29da6a183b18c5c3d`；checkpoint SHA-256 为 `71dbd691e7633a3d20facb1ebc405908863aff786e5af30899d4cb666250d613`。前向使用 4 个空闲 V100，297,706 validation samples，世界大小 4；模型加载日志为 `All keys matched successfully`。

### O0 官方实测指标

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

TrackEval 使用官方仓库 evaluator、`seqmaps/kitti-2.txt` 和 V2 图像/GT 路径，结果日志在 run 目录的 `trackeval_o0.log`。官方 `main.py` 的 TrackEval 命令对 V2 仍硬编码 `./datasets/refer-kitti`；本轮在 isolated run 中增加了 `refer-kitti -> refer-kitti-v2` 兼容链接后，用相同 evaluator 独立重跑。该修正只解决路径，不改变模型输入、raw logits 或决策。

官方 `generate_final_results` 在 SSHFS 上会在“每个候选帧 × 每个表达式”内层重复打开表达式 JSON，前向完成后长时间停在结果落盘。本轮在 raw `result.json` 已封存后使用预加载表达式映射的等价落盘脚本，保持 `argmax(raw_two_class_score)>0`、原候选 bbox 和合并 ID 不变；生成结果完整覆盖 862 个 `predict.txt`。

另发现 FlexHook 测试 DataLoader 的 `sample_end=obj_last-sample_frame_num` 会使 314 个候选 frame-object 条目没有 raw score，对应 7,750 个 GT-frame，记为 `MODEL_WINDOW_MISSING`，不归因给语言选择。该边界也写入错误汇总和后续 JEV 解释。

## 复现边界

- 没有训练新 JEV，也没有修改官方权重或官方 upstream checkout。
- GT 没有进入模型 forward；GT 只用于 raw output 之后的 TrackEval、错误归因和 Oracle 反事实。
- FlexHook 结果是官方 V2 tuple 的实测；YesTrack、共享候选 YesTrack/FlexHook 比较仍然是 `BLOCKED/NOT_COMPARABLE`，不能用两个原生方法的论文数字或不同候选结果做因果比较。
