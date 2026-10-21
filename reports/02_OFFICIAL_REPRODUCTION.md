# 官方复现状态

## 状态

YesTrack 与 FlexHook 都完成了仓库、入口、参数、输入协议和资源路径审计。YesTrack 仍在官方权重/候选下载处阻塞；FlexHook 已在 A800 找到资源并启动官方单卡全量推理。没有使用论文表格数字冒充本地测量。

## YesTrack

代码版本：`ed42b8315b28c94dc595d83b0d49bf57002bb281`。

目标 V2 运行合同为：

```bash
cd /data1/liuyeqiang/RMOT_JEV_DIAG_20261021/upstream/YesTrack
python refer_llm/llm_eval_from_mot.py \
  --data_root <refer-kitti-v2> \
  --lora_path <v2bestweight> \
  --mot_input_type results_root \
  --results_root <v2best_track_result> \
  --mot_filename predict.txt \
  --output_root /data1/liuyeqiang/RMOT_JEV_DIAG_20261021/runs/yestrack/v2 \
  --stability_enable --stability_window 6 \
  --stability_thresh 0.6 --stability_boost 0.3 \
  --infer_every_n_frames 4
```

这是按官方文档保留候选、TCP/TRP 和 V2 起始阈值的命令模板；本轮仍没有执行模型前向，因为官方 `v2bestweight`、`v2best_track_result` 和 `yestrack.zip` 内的资源字节尚未可读。A800 上的 `yestrack_native_gpu7_v1` 是 OneJev/GroundJEV 自有实验，不具备官方 Qwen3-VL-2B/LoRA 兼容性，未替代官方资源。

## FlexHook

代码版本：`bd1acc38634b28525d54dc6e0fcb38335f0029f9`。官方 `infer.sh` 的 V2 组合为：

```text
DATASET_NAME=kitti-2
CKPT_PATH=SOTA_ckpts/refer-kitti-v2-best
TRACKER_ROOT=Temp-NeuralSORT-kitti2
TEST_CFG_NAME=kitti2.yaml
```

目标运行必须使用独立 `OUTPUT`，因为 `main.py` 会复用已有 `result.json`/`results`。A800 已启动独立运行：checkpoint 为 `.../flexhook/SOTA_ckpts/refer-kitti-v2-best.pth`，数据根为 GT-free runtime，候选根为 `Temp-NeuralSORT-kitti2-runtime`，日志记录 `runtime_dataset_samples=297706`、`batches=7443`、`gt_used_during_inference=false`。最后已读进度为 `500/7443`，之后暂未看到新日志或结果文件；没有中断或重启远端 GPU3，也没有在结果完成前填入 HOTA。历史 TempRMOT 输出没有替代 `Temp-NeuralSORT-kitti2`。

本地主机的 base/RMOT2 预检仍分别缺 `ftfy`/Qwen3-VL 类；A800 运行环境已通过模型加载并报告 `All keys matched successfully`。本地官方 checkout 的语法问题仍保留为独立审计项，未在上游目录打补丁；远端全量运行完成后还需核对其代码工作树、commit 和输出 receipt，避免把“已启动”误写成“已完成可比复现”。

## A800 上新增的 TempRMOT baseline 资源

继续清点 A800 后发现：

- `/home/liuyeqiang/remote/A800/data3/user/TTA-RMOT-assets/checkpoints/temprmot_refer_kitti_v2_official_checkpoint_rk2.pth`，`1,096,316,824` bytes，Zip-format PyTorch archive；
- `/home/liuyeqiang/remote/A800/data3/user/TTA-RMOT-assets/checkpoints/r50_deformable_detr_plus_iterative_bbox_refinement-checkpoint.pth`，`489,084,000` bytes。

它们与 A800 上的 TempRMOT 训练脚本和 Refer-KITTI-V2 baseline 命名一致，可作为独立 RMOT baseline 的权重/预训练输入；没有把它们接入 YesTrack 或 FlexHook，也没有把它们当作 YesTrack 官方 `v1/v2bestweight` 的替代品。两份大文件仍留在 A800 挂载上，未复制进报告仓库。

## 已完成的非推理验证

- 两个官方仓库均已固定 commit 并保持 clean。
- 已核对 YesTrack 的 `results_root` 输入格式、帧映射、V1 158-entry seqmap、V2 逗号表达式和阈值说明。
- 已核对 FlexHook 测试 DataLoader、`all/gt.txt` 特殊分支、`argmax(score)>0` 决策、原始 logits 保存结构和结果缓存逻辑。
- 已对本地历史 TempRMOT V2 结果做 40 个表达式对的文件格式抽样，输出不纳入官方 metrics。
- 只读入口预检也已执行：YesTrack base 环境缺 `transformers`，RMOT2 的 Transformers 不含 Qwen3-VL 类，FlexHook base 环境缺 `ftfy`；A800 远端运行另有 `RUNNING` 记录，错误见 [`entrypoint_preflight.csv`](../analysis/entrypoint_preflight.csv)。

## 没有执行的项目

官方 HOTA/DetA/AssA/IDF1、共享候选二阶段比较、Selection/Identity Oracle、30 个可视化案例、时间链和错误事件表仍没有完成的合法输出，因此对应 CSV 使用 `BLOCKED`、`RUNNING` 或 `PENDING`，而不是填 0。

