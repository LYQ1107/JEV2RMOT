# Official V2 command templates

YesTrack remains a template because the official archive bytes are not downloaded. FlexHook has verified A800 replacements and a remote full run has started; keep the output isolated and do not infer final metrics from the last visible progress line.

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

The A800 run uses the equivalent of `DATASET_NAME=kitti-2`, checkpoint `/data3/user/TTA-RMOT-assets/flexhook/SOTA_ckpts/refer-kitti-v2-best.pth`, GT-free runtime data `/data3/user/TTA-RMOT-assets/flexhook/refer-kitti-v2-runtime`, and runtime tracker root `/data3/user/TTA-RMOT-assets/flexhook/tracker_outputs/Temp-NeuralSORT-kitti2-runtime`. Its protocol is `official_flexhook_inference_single_card`, with `runtime_dataset_samples=297706` and `batches=7443`; the last visible log line is batch 500. Do not reuse an existing `result.json` or `results` directory.

## Additional A800 baseline assets

The A800 asset root also contains the separate TempRMOT Refer-KITTI-V2 baseline checkpoint and its R50 Deformable-DETR pretrain:

```text
/data3/user/TTA-RMOT-assets/checkpoints/temprmot_refer_kitti_v2_official_checkpoint_rk2.pth
/data3/user/TTA-RMOT-assets/checkpoints/r50_deformable_detr_plus_iterative_bbox_refinement-checkpoint.pth
```

These are available for a standalone TempRMOT baseline replay only. They are not YesTrack weights and are not part of the FlexHook inference tuple above.

