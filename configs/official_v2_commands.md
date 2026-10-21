# Official V2 command templates

These are templates only. They were not run because the placeholders have no verified local replacements.

## YesTrack

```bash
cd /data1/liuyeqiang/RMOT_JEV_DIAG_20261021/upstream/YesTrack
python refer_llm/llm_eval_from_mot.py \
  --data_root <REFER_KITTI_V2> \
  --lora_path <V2_BEST_WEIGHT> \
  --mot_input_type results_root \
  --results_root <V2_BEST_TRACK_RESULT> \
  --mot_filename predict.txt \
  --output_root /data1/liuyeqiang/RMOT_JEV_DIAG_20261021/runs/yestrack/v2 \
  --stability_enable --stability_window 6 \
  --stability_thresh 0.6 --stability_boost 0.3 \
  --infer_every_n_frames 4
```

## FlexHook

Start from `upstream/FlexHook/infer.sh`, set `DATASET_NAME=kitti-2`, `CKPT_PATH=SOTA_ckpts/refer-kitti-v2-best`, `TRACKER_ROOT=Temp-NeuralSORT-kitti2`, and use an isolated `OUTPUT`. Do not reuse an existing `result.json` or `results` directory.

