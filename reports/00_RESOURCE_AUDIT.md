# 资源审计

审计时间：2026-10-21 UTC。项目状态：`PARTIAL/BLOCKED`。本报告只记录当前主机实际可读的资源，不把目录名或论文数字当作资源证据。

## 结论

目标机器上有可用 GPU，但没有同时满足“完整 Refer-KITTI 图像/标签 + 官方候选轨迹 + 官方权重”的可运行三元组。因此本轮没有合法的 YesTrack/FlexHook 官方推理，也没有伪造 HOTA、Oracle 或 JEV headroom 数字。

## 主机与 GPU

| 项目 | 实际值 | 结论 |
|---|---|---|
| hostname | `cieelab` | 已记录 |
| user / cwd | `liuyeqiang` / `/data1/liuyeqiang` | 已记录 |
| GPU | 10 × Tesla V100-DGXS 32508 MiB，driver 470.141.03，CUDA 11.4 | 与官方 FlexHook 推荐的 CUDA 12.4 不同 |
| 审计时空闲 GPU | 0、3、4、5、6、7、8、9 | 可用于后续小规模单卡推理，但不解决权重/数据缺失 |
| 忙碌/不确定 GPU | 1、2 | 发现其他进程/显存占用，未触碰 |
| 本地 `/data1` | 约 143G 可用 | 不复制大数据集 |
| NAS `/data1/liuyeqiang/nas/A100` | SSHFS，约 3.7T 可用 | 可读取若干历史资产，远端遍历较慢 |
| `/home/liuyeqiang/remote/A800` | SSHFS，约 438G 可用 | 挂载可读；直接 SSH 因 host key 未确认而未使用 |

没有停止、重启或修改其他 GPU 任务。审计期间被终止的进程均为本任务自己启动的远端遍历/审计进程。

## 仓库与代码版本

| 仓库 | 路径 | commit | 状态 |
|---|---|---|---|
| YesTrack | [`upstream/YesTrack`](/data1/liuyeqiang/RMOT_JEV_DIAG_20261021/upstream/YesTrack) | `ed42b8315b28c94dc595d83b0d49bf57002bb281` | clean，已核对为当前 `main` |
| FlexHook | [`upstream/FlexHook`](/data1/liuyeqiang/RMOT_JEV_DIAG_20261021/upstream/FlexHook) | `bd1acc38634b28525d54dc6e0fcb38335f0029f9` | clean，已核对为当前 `main` |
| LLM2Jev | [`upstream/LLM2Jev`](/data1/liuyeqiang/RMOT_JEV_DIAG_20261021/upstream/LLM2Jev) | `93d4fcdcc81e0732026a65195eca3b45333af451` | clean，仅作设计参考，本轮未训练 |

官方仓库链接：[YesTrack](https://github.com/ggbondrighthere24/YesTrack)、[FlexHook](https://github.com/buptLwz/FlexHook)、[LLM2Jev](https://github.com/Yinsongxu/LLM2Jev)。两个目标仓库的 GitHub Releases 均未提供可直接下载的 checkpoint；仓库本身也不含目标权重或完整数据。

对官方 FlexHook checkout 的所有 Python 文件做 AST 级语法检查，还发现两个源码级阻塞：`SwinTransformer/utils.py:22` 和 `deit/main.py:44` 的 `return checkpoint` 位于未闭合的 `try` 块之后。官方工作树保持未修改；该问题与资源缺失并列记录。

## 资源路径核对

| 资源 | 实际路径/现象 | 状态 |
|---|---|---|
| 用户指定 `/data2/user/LocateMOT` | 不存在 | `MISSING` |
| 用户指定 `/home/Valadmin/A100` | 不存在 | `MISSING` |
| 用户指定 `/data1/liuyeqiang/TempMam` | 不存在；NAS 中有同名历史归档 | 不能把归档当作当前工作区 |
| 用户指定 `/data1/liuyeqiang/TempMam_frez` | 不存在 | `MISSING` |
| NAS 中的 V2 表达式 | `/data1/liuyeqiang/nas/A100/codex_archive_20261014/TempMam/data/Dataset/refer-kitti-v2`，约 58M | 仅表达式与 zip，非完整数据集 |
| V2 expression 目录 | `0000`–`0020` 共 21 个目录 | 可读取 |
| V2 expression archive | `kittiv2_expression.zip`，约 7,116,114 bytes | 可读取 |
| V2 `KITTI` | 符号链接指向 `/data1/liuyeqiang/RMOT/data/Dataset/refer-kitti/KITTI`，目标不存在 | 图像/标签 `BLOCKED` |
| V1 | NAS 归档中的 `refer-kitti-v1` / `TempRMOT` 链接指向缺失的本地 RMOT 数据 | `BLOCKED` |
| 远端 A800 | `/home/liuyeqiang/remote/A800` 可列目录；目标资源名搜索未发现 | 数据/权重未确认 |

## Baidu 官方分享

尝试读取用户给出的 YesTrack 分享（提取码 `z5kt`）和 FlexHook 分享（提取码 `d3qj`）。页面能返回 share id，但授权验证/列表接口随后返回提取码验证失败或 `errno=2` 链接错误；没有得到可下载的文件清单，因此没有绕过认证或猜测直链。

这不是 GPU 失败，而是外部资源读取失败。待用户提供可读的 NAS 路径、有效分享或直接文件后，才能继续官方复现。

## 环境

| 环境 | 关键版本/缺项 |
|---|---|
| base | Python 3.9.12，PyTorch 2.0.1；无 `transformers` / `peft`；无 Qwen3-VL |
| RMOT2 | PyTorch 1.13.1+cu117，Transformers 4.30.2；无 `peft`；不足以直接运行当前 Qwen3-VL 代码 |
| GMT | PyTorch 2.0.0+cu118；缺少目标 Transformers 等 |
| Hugging Face cache | 约 9.9G；未发现 Qwen3-VL-2B 或 YesTrack LoRA |
| git-lfs | 未安装；目标仓库没有 LFS 对象可供恢复 |

## 可用的历史辅助资产

`/data1/liuyeqiang/nas/A100/codex_archive_20261014/TempRMOT/exps/default_rk_v2/results_epoch2` 存在 4 个视频（0005、0011、0013、0019）的历史 TempRMOT `gt.txt`/`predict.txt` 结果目录。日志和配置明确表明这是 TempRMOT 的最终结果树，不是 YesTrack 的 `v2best_track_result`，也不是 FlexHook 的 `Temp-NeuralSORT-kitti2` 原始候选。因此只做格式/覆盖审计，输出见 [`legacy_temprmot_v2_inventory.csv`](/data1/liuyeqiang/RMOT_JEV_DIAG_20261021/analysis/legacy_temprmot_v2_inventory.csv)，状态统一为 `AUXILIARY_NOT_COMPARABLE`。

## 下一步解阻塞条件

需要同时提供：

- YesTrack `v2bestweight`、`v2best_track_result`、`refer_kitti_motc_gt_v2` 和完整 V2 图像/标签；
- FlexHook `SOTA_ckpts/refer-kitti-v2-best`、`Temp-NeuralSORT-kitti2` 和完整 V2 图像/标签；
- 可写的输出空间或允许使用当前项目目录。

