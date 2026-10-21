# 官方复现状态

## 状态

YesTrack 与 FlexHook 都完成了仓库、入口、参数、输入协议和资源路径审计；两者都在“模型加载/正式推理”之前因资源不完整阻塞。没有使用论文表格数字冒充本地测量。

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

这是按官方文档保留候选、TCP/TRP 和 V2 起始阈值的命令模板；本轮没有执行模型前向，因为 `<refer-kitti-v2>`、`<v2bestweight>`、`<v2best_track_result>` 均不可替换为真实路径。YesTrack 代码需要 Qwen3-VL-2B 及 LoRA；本机缓存没有对应权重。

## FlexHook

代码版本：`bd1acc38634b28525d54dc6e0fcb38335f0029f9`。官方 `infer.sh` 的 V2 组合为：

```text
DATASET_NAME=kitti-2
CKPT_PATH=SOTA_ckpts/refer-kitti-v2-best
TRACKER_ROOT=Temp-NeuralSORT-kitti2
TEST_CFG_NAME=kitti2.yaml
```

目标运行必须使用独立 `OUTPUT`，因为 `main.py` 会复用已有 `result.json`/`results`。本轮没有执行该命令：checkpoint、tracker_outputs 和完整数据均缺失；也没有用历史 TempRMOT 输出替代 `Temp-NeuralSORT-kitti2`。

在资源阻塞之外，官方 FlexHook checkout 还存在源码级语法阻塞：`SwinTransformer/utils.py:22` 与 `deit/main.py:44` 的 `return checkpoint` 不在合法的 `try/except` 结构内，`python -m py_compile` 直接失败。为保持官方复现原则，本轮没有在上游目录打补丁；若后续允许做最小修复分支，必须单独记录 patch 并验证其不改变网络计算。

## 已完成的非推理验证

- 两个官方仓库均已固定 commit 并保持 clean。
- 已核对 YesTrack 的 `results_root` 输入格式、帧映射、V1 158-entry seqmap、V2 逗号表达式和阈值说明。
- 已核对 FlexHook 测试 DataLoader、`all/gt.txt` 特殊分支、`argmax(score)>0` 决策、原始 logits 保存结构和结果缓存逻辑。
- 已对本地历史 TempRMOT V2 结果做 40 个表达式对的文件格式抽样，输出不纳入官方 metrics。
- 只读入口预检也已执行：YesTrack base 环境缺 `transformers`，RMOT2 的 Transformers 不含 Qwen3-VL 类，FlexHook base 环境缺 `ftfy`；错误见 [`entrypoint_preflight.csv`](/data1/liuyeqiang/RMOT_JEV_DIAG_20261021/analysis/entrypoint_preflight.csv)。

## 没有执行的项目

官方 HOTA/DetA/AssA/IDF1、共享候选二阶段比较、Selection/Identity Oracle、30 个可视化案例、时间链和错误事件表均没有合法数据输入，因此对应 CSV 使用 `BLOCKED` 或空事件表，而不是填 0。

