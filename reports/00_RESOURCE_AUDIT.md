# 资源审计

审计时间：2026-10-22 UTC。项目状态：`FLEXHOOK_COMPLETE / YESTRACK_COMPLETE_FP16 / SHARED_CANDIDATE_COMPLETE`。本报告只记录实际可读的资源，不把目录名或论文数字当作资源证据。

## 结论

A800 上已经找到 FlexHook 的“完整 Refer-KITTI-V2 数据 + Temp-NeuralSORT-kitti2 候选 + 官方 checkpoint”三元组，并完成 4-GPU 官方前向、raw result 封存和 862 表达式 TrackEval。继续清点还找到一份按路径/文件名对应的官方 TempRMOT Refer-KITTI-V2 baseline checkpoint（以及其 R50 Deformable-DETR 预训练），可用于独立 RMOT baseline，但不能冒充 YesTrack 或 FlexHook 权重。随后通过本地 BaiduPCS-Go 在不走代理的路径下载了 YesTrack 官方 `yestrack.zip`，解压得到 V1/V2 LoRA、V2 候选和 V1/V2 MOTC GT；Qwen3-VL 基座的直连下载超时，使用固定 revision 的 Hugging Face 代理回退完成。YesTrack V2 已完成 862 表达式推理和官方 TrackEval；运行硬件是本地 V100，不冒充 A800 硬件复现，也不把 A800 上用户自训的 OneJev/GroundJEV 权重当作官方 YesTrack。

## 主机与 GPU

| 项目 | 实际值 | 结论 |
|---|---|---|
| hostname | `cieelab` | 已记录 |
| user / cwd | `liuyeqiang` / `/data1/liuyeqiang` | 已记录 |
| GPU | 10 × Tesla V100-DGXS 32508 MiB，driver 470.141.03，CUDA 11.4 | 与官方 FlexHook 推荐的 CUDA 12.4 不同 |
| 审计时空闲 GPU | 0、2、3、4、5、6、7、8、9 | YesTrack 使用 0、2–9；A800 GPU3 另有全量 FlexHook 任务，未中断 |
| 忙碌/不确定 GPU | 1 | 发现其他进程/显存占用，未触碰；本地 GPU1 始终保持原任务状态 |
| 本地 `/data1` | 约 143G 可用 | 不复制大数据集 |
| NAS `/data1/liuyeqiang/nas/A100` | SSHFS，约 3.7T 可用 | 可读取若干历史资产，远端遍历较慢 |
| `/home/liuyeqiang/remote/A800` | SSHFS，约 437G 可用 | 挂载可读；host key 已按 `a800-datasets` 配置核验；直接 SSH 仅被服务端限制为强制 SFTP/挂载用途 |

没有停止、重启或修改其他 GPU 任务。审计期间被终止的进程均为本任务自己启动的远端遍历/审计进程。

## 仓库与代码版本

| 仓库 | 路径 | commit | 状态 |
|---|---|---|---|
| YesTrack | [官方仓库](https://github.com/ggbondrighthere24/YesTrack) | `ed42b8315b28c94dc595d83b0d49bf57002bb281` | clean，已核对为当前 `main`；V2 官方包已落地 |
| FlexHook | [官方仓库](https://github.com/buptLwz/FlexHook) | `bd1acc38634b28525d54dc6e0fcb38335f0029f9` | clean，已核对为当前 `main` |
| LLM2Jev | [官方仓库](https://github.com/Yinsongxu/LLM2Jev) | `93d4fcdcc81e0732026a65195eca3b45333af451` | clean，仅作设计参考，本轮未训练 |

官方仓库链接：[YesTrack](https://github.com/ggbondrighthere24/YesTrack)、[FlexHook](https://github.com/buptLwz/FlexHook)、[LLM2Jev](https://github.com/Yinsongxu/LLM2Jev)。目标仓库代码本身不含大权重或完整数据；FlexHook 资产在 A800 的用户资源区，YesTrack 发布包和基座下载到项目 ignored run/download 目录，轻量 hash/manifest 提交到报告仓库。

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
| A800 YesTrack native runs | `.../LocateMOT-runs/YesTrack/training/yestrack_native_gpu7_v1/` 有 merged/adapter | `FOUND_NON_OFFICIAL`，未替代官方 Qwen3-VL |

## Baidu 官方分享

YesTrack 分享（提取码 `z5kt`）先在不使用代理的普通 HTTPS 请求下完成提取码验证；页面公开 `api/sharedownload` 曾返回 `errno=113`（验证码/签名错误）。随后本机已有的 `/home/liuyeqiang/.local/bin/BaiduPCS-Go` 使用 direct/no-proxy transfer 成功下载 `/Yestrack/yestrack.zip`：`178,142,422` bytes，SHA-256 `f303e4f2578ea011cc7861afc359be535e132bbb59308e22726621e37e0ca97b`，`unzip -t` 通过，7168 个归档条目。Baidu 远端文件保留在用户自己的网盘中，没有删除或绕过验证码。

FlexHook 分享（提取码 `d3qj`）不再是当前阻塞项，因为官方 checkpoint、预训练 backbone、V2 数据和候选已经在 A800 找到。A800 资源明细见 [`analysis/a800_resource_manifest.csv`](../analysis/a800_resource_manifest.csv)。

归档内含 `v1bestweight`、`v2bestweight`、`v1best_track_result`、`v2best_track_result`、`refer_kitti_motc_gt` 和 `refer_kitti_motc_gt_v2`。V2 adapter SHA-256 为 `749d7c48bc8507105fb068adb539f5ebd58a587402d6e30542675c6e5a050b55`；V2 候选共 1,850,576 行、862 个表达式。基座 `Qwen/Qwen3-VL-2B-Instruct` 固定 HF revision `89644892e4d85e24eaac8bacfd4f463576704203`，直连超时后通过 proxy snapshot 下载。A800 SSH key 仍是强制 SFTP，未尝试远程执行客户端。FlexHook 与 YesTrack 原生结果、Oracle 和错误归因 receipt 均留在项目 run 目录，仓库只提交轻量 manifest/CSV/报告。

## 环境

| 环境 | 关键版本/缺项 |
|---|---|
| base | Python 3.9.12，PyTorch 2.0.1；无 `transformers` / `peft`；无 Qwen3-VL |
| RMOT2 | PyTorch 1.13.1+cu117，Transformers 4.30.2；无 `peft`；不足以直接运行当前 Qwen3-VL 代码 |
| GMT | PyTorch 2.0.0+cu118；缺少目标 Transformers 等 |
| Hugging Face cache | 约 9.9G；未发现 Qwen3-VL-2B 或 YesTrack LoRA |
| YesTrack isolated deps | `runs/yestrack_pydeps`：Transformers 4.57.6、PEFT 0.18.0、Tokenizers 0.22.1、Accelerate 1.15.0；复用 worldmot311 的 Torch 2.6.0+cu118 |
| YesTrack inference hardware | 9 张本地 V100-DGXS，`CUDA_VISIBLE_DEVICES=0,2,3,4,5,6,7,8,9`；GPU1 的其他任务未触碰；使用 fp16，不能宣称 A800 硬件等价 |
| git-lfs | 未安装；目标仓库没有 LFS 对象可供恢复 |

## 可用的历史辅助资产

`/data1/liuyeqiang/nas/A100/codex_archive_20261014/TempRMOT/exps/default_rk_v2/results_epoch2` 存在 4 个视频（0005、0011、0013、0019）的历史 TempRMOT `gt.txt`/`predict.txt` 结果目录。日志和配置明确表明这是 TempRMOT 的最终结果树，不是 YesTrack 的 `v2best_track_result`，也不是 FlexHook 的 `Temp-NeuralSORT-kitti2` 原始候选。因此只做格式/覆盖审计，输出见 [`legacy_temprmot_v2_inventory.csv`](../analysis/legacy_temprmot_v2_inventory.csv)，状态统一为 `AUXILIARY_NOT_COMPARABLE`。

## 共享候选已完成

- YesTrack 官方 V2 原生复现已完成；V1 资源已找到但本轮未运行 V1 全量。
- FlexHook 的 `Temp-NeuralSORT-kitti2` 已转换为 862 条 YesTrack 表达式输入；frame、bbox 保持不变，行人 ID 使用 FlexHook 官方 `max_car_id` offset。
- 共用候选推理完成 862/862 个表达式、2,425,382 行 score、0 个任务错误；候选源仍位于 A800，推理使用本地 9 张 V100 的 fp16，不能称为 A800 硬件复现。
- 用同一 A800 `gt_template` 和同一 bundled TrackEval 重评：FlexHook O0 HOTA 42.526，YesTrack shared O0@0.60 HOTA 47.607；这才是受控的二阶段对照。YesTrack 原生行仍使用官方归档 GT，坐标精度略有不同，报告中不混用两种 GT。

## 当前剩余边界

- 共享实验证明了候选内二阶段差异，但没有训练新的 JEV 参数；O1/O2 仍是离线反事实，不能直接当作实际收益。
- 候选缺失、IoU 不足和 FlexHook 的末帧窗口缺口仍属于第一阶段/几何协议边界，不能由普通二阶段凭空恢复。
- 原始大权重、图像和 run 输出保持在 ignored 目录或挂载路径；仓库提交 `analysis/yestrack_official_run_receipt.json`、CSV 和 Markdown 证据。

