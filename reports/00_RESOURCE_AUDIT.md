# 资源审计

审计时间：2026-10-21 UTC。项目状态：`PARTIAL / FLEXHOOK_RUNNING / YESTRACK_BLOCKED`。本报告只记录实际可读的资源，不把目录名或论文数字当作资源证据。

## 结论

A800 上已经找到 FlexHook 的“完整 Refer-KITTI-V2 数据 + Temp-NeuralSORT-kitti2 候选 + 官方 checkpoint”三元组，并启动了官方单卡全量推理；本次复核最后记录为 `500/7443`，之后暂未看到新日志或结果文件，因此只记为未完成，不声称任务仍在正常推进。继续清点还找到一份按路径/文件名对应的官方 TempRMOT Refer-KITTI-V2 baseline checkpoint（以及其 R50 Deformable-DETR 预训练），可用于独立 RMOT baseline，但不能冒充 YesTrack 或 FlexHook 权重。YesTrack 的官方 `yestrack.zip` 已能通过公开分享正常列目录，但下载接口仍返回签名错误，官方 `v1/v2` 权重和官方候选字节尚未落地。因此不能给出 YesTrack 官方指标，也不把 A800 上用户自训的 OneJev/GroundJEV 权重当作官方 YesTrack 替代品。

## 主机与 GPU

| 项目 | 实际值 | 结论 |
|---|---|---|
| hostname | `cieelab` | 已记录 |
| user / cwd | `liuyeqiang` / `/data1/liuyeqiang` | 已记录 |
| GPU | 10 × Tesla V100-DGXS 32508 MiB，driver 470.141.03，CUDA 11.4 | 与官方 FlexHook 推荐的 CUDA 12.4 不同 |
| 审计时空闲 GPU | 0、3、4、5、6、7、8、9 | 本机可用于小规模验证；A800 GPU3 另有全量 FlexHook 任务，未中断 |
| 忙碌/不确定 GPU | 1、2 | 发现其他进程/显存占用，未触碰 |
| 本地 `/data1` | 约 143G 可用 | 不复制大数据集 |
| NAS `/data1/liuyeqiang/nas/A100` | SSHFS，约 3.7T 可用 | 可读取若干历史资产，远端遍历较慢 |
| `/home/liuyeqiang/remote/A800` | SSHFS，约 437G 可用 | 挂载可读；host key 已按 `a800-datasets` 配置核验；直接 SSH 仅被服务端限制为强制 SFTP/挂载用途 |

没有停止、重启或修改其他 GPU 任务。审计期间被终止的进程均为本任务自己启动的远端遍历/审计进程。

## 仓库与代码版本

| 仓库 | 路径 | commit | 状态 |
|---|---|---|---|
| YesTrack | [官方仓库](https://github.com/ggbondrighthere24/YesTrack) | `ed42b8315b28c94dc595d83b0d49bf57002bb281` | clean，已核对为当前 `main` |
| FlexHook | [官方仓库](https://github.com/buptLwz/FlexHook) | `bd1acc38634b28525d54dc6e0fcb38335f0029f9` | clean，已核对为当前 `main` |
| LLM2Jev | [官方仓库](https://github.com/Yinsongxu/LLM2Jev) | `93d4fcdcc81e0732026a65195eca3b45333af451` | clean，仅作设计参考，本轮未训练 |

官方仓库链接：[YesTrack](https://github.com/ggbondrighthere24/YesTrack)、[FlexHook](https://github.com/buptLwz/FlexHook)、[LLM2Jev](https://github.com/Yinsongxu/LLM2Jev)。目标仓库代码本身不含目标权重或完整数据；FlexHook 资产已在 A800 的用户资源区找到，YesTrack 发布包目前只有公开目录元数据。

对官方 FlexHook checkout 的所有 Python 文件做 AST 级语法检查，还发现两个源码级阻塞：`SwinTransformer/utils.py:22` 和 `deit/main.py:44` 的 `return checkpoint` 位于未闭合的 `try` 块之后。官方工作树保持未修改；该问题与资源缺失并列记录。

## 资源路径核对

| 资源 | 实际路径/现象 | 状态 |
|---|---|---|
| 用户指定 `/data2/user/LocateMOT` | 当前主机不存在；A800 挂载下对应为 `/home/liuyeqiang/remote/A800/data2/user/LocateMOT` | 主机本地 `MISSING`，A800 `FOUND` |
| 用户指定 `/home/Valadmin/A100` | 不存在 | `MISSING` |
| 用户指定 `/data1/liuyeqiang/TempMam` | 不存在；NAS 中有同名历史归档 | 不能把归档当作当前工作区 |
| 用户指定 `/data1/liuyeqiang/TempMam_frez` | 不存在 | `MISSING` |
| NAS 中的 V2 表达式 | `/data1/liuyeqiang/nas/A100/codex_archive_20261014/TempMam/data/Dataset/refer-kitti-v2`，约 58M | 仅表达式与 zip，非完整数据集 |
| V2 expression 目录 | `0000`–`0020` 共 21 个目录 | 可读取 |
| V2 expression archive | `kittiv2_expression.zip`，约 7,116,114 bytes | 可读取 |
| V2 `KITTI`（NAS 旧链接） | 符号链接指向 `/data1/liuyeqiang/RMOT/data/Dataset/refer-kitti/KITTI`，目标不存在 | 旧 NAS 副本 `BLOCKED` |
| A800 V2 expression | `/home/liuyeqiang/remote/A800/data2/user/LocateMOT/data/refer_kitti_v2/expression`，9758 files，21 videos | `FOUND_COMPLETE` |
| A800 V2 labels | `/home/liuyeqiang/remote/A800/data2/user/LocateMOT/data/refer_kitti_v2/labels_with_ids`，7162 files，21 videos | `FOUND_COMPLETE` |
| A800 KITTI image_02 | `/home/liuyeqiang/remote/A800/data2/user/LocateMOT/data/kitti_tracking/training/image_02`，8008 images，21 videos | `FOUND_COMPLETE` |
| A800 FlexHook GT/evaluation copy | `.../TTA-RMOT-assets/flexhook/refer-kitti-v2/labels.json`、`gt_template/`；metadata 记录 862 templates | `FOUND_EVALUATION_ONLY` |
| V1 | NAS 归档中的 `refer-kitti-v1` / `TempRMOT` 链接指向缺失的本地 RMOT 数据 | `BLOCKED` |
| A800 FlexHook checkpoint | `.../TTA-RMOT-assets/flexhook/SOTA_ckpts/refer-kitti-v2-best.pth`，995,768,450 bytes，SHA256 `71db...d613` | `FOUND_OFFICIAL` |
| A800 FlexHook candidates | `.../flexhook/tracker_outputs/Temp-NeuralSORT-kitti2`，4 test videos × car/pedestrian | `FOUND_CANDIDATE_INPUT` |
| A800 TempRMOT baseline checkpoint | `.../TTA-RMOT-assets/checkpoints/temprmot_refer_kitti_v2_official_checkpoint_rk2.pth`，1,096,316,824 bytes，Zip-format PyTorch archive | `FOUND_OFFICIAL_BASELINE`，不属于 YesTrack/FlexHook |
| A800 TempRMOT R50 pretrain | `.../TTA-RMOT-assets/checkpoints/r50_deformable_detr_plus_iterative_bbox_refinement-checkpoint.pth`，489,084,000 bytes | `FOUND_OFFICIAL_PRETRAIN`，不属于 YesTrack/FlexHook |
| A800 YesTrack native runs | `.../LocateMOT-runs/YesTrack/training/yestrack_native_gpu7_v1/` 有 merged/adapter | `FOUND_NON_OFFICIAL`，不可替代官方 Qwen3-VL |

## Baidu 官方分享

YesTrack 分享（提取码 `z5kt`）已在不使用代理的普通 HTTPS 请求下完成提取码验证，`/share/list` 正常返回唯一文件 `/Yestrack/yestrack.zip`：`178,142,422` bytes，`fs_id=981448710771451`，分享 `shareid=57327686470`、`share_uk=3538711738`。随后按页面公开下载接口提交普通 `api/sharedownload` 请求，返回 `errno=113`（验证码/签名错误）；没有继续绕过签名、验证码或登录边界，也没有把 178 MB 的目录元数据误报成已下载权重。

FlexHook 分享（提取码 `d3qj`）不再是当前阻塞项，因为官方 checkpoint、预训练 backbone、V2 数据和候选已经在 A800 找到。A800 资源明细见 [`analysis/a800_resource_manifest.csv`](../analysis/a800_resource_manifest.csv)。

YesTrack 仍是外部发布包下载阻塞；本次还确认 A800 有 `BaiduPCS-Go` 客户端，但该二进制在本地主机因需要 glibc `>=2.32` 无法执行，而 A800 SSH key 是强制 SFTP、不能远程执行客户端。没有改用代理、绕过验证码或复制私有 cookie。FlexHook 已进入远端推理阶段。待 A800 全量结果封存或用户提供 YesTrack 官方文件后，才能继续完整官方比较。

## 环境

| 环境 | 关键版本/缺项 |
|---|---|
| base | Python 3.9.12，PyTorch 2.0.1；无 `transformers` / `peft`；无 Qwen3-VL |
| RMOT2 | PyTorch 1.13.1+cu117，Transformers 4.30.2；无 `peft`；不足以直接运行当前 Qwen3-VL 代码 |
| GMT | PyTorch 2.0.0+cu118；缺少目标 Transformers 等 |
| Hugging Face cache | 约 9.9G；未发现 Qwen3-VL-2B 或 YesTrack LoRA |
| git-lfs | 未安装；目标仓库没有 LFS 对象可供恢复 |

## 可用的历史辅助资产

`/data1/liuyeqiang/nas/A100/codex_archive_20261014/TempRMOT/exps/default_rk_v2/results_epoch2` 存在 4 个视频（0005、0011、0013、0019）的历史 TempRMOT `gt.txt`/`predict.txt` 结果目录。日志和配置明确表明这是 TempRMOT 的最终结果树，不是 YesTrack 的 `v2best_track_result`，也不是 FlexHook 的 `Temp-NeuralSORT-kitti2` 原始候选。因此只做格式/覆盖审计，输出见 [`legacy_temprmot_v2_inventory.csv`](../analysis/legacy_temprmot_v2_inventory.csv)，状态统一为 `AUXILIARY_NOT_COMPARABLE`。

## 下一步解阻塞条件

当前剩余条件：

- YesTrack `v2bestweight`、`v2best_track_result`、`refer_kitti_motc_gt_v2` 和完整 V2 图像/标签；
- FlexHook 全量日志完成并取得 raw result/receipt，随后计算 TrackEval、Oracle 和错误案例；
- 如需独立复核 TempRMOT baseline，可直接使用 A800 上已找到的 rk2 checkpoint 与 R50 pretrain；它们不解除 YesTrack 官方权重阻塞；
- 可写的输出空间或允许使用当前项目目录。

