# Execution status log

## Completed

- Host/GPU/disk/NAS/remote-mount audit.
- Official repository clone and commit verification.
- YesTrack/FlexHook entry-point, frame mapping, GT, candidate and cache audit.
- Authorized direct/no-proxy Baidu share read attempt; public verification and `/share/list` succeeded for `/Yestrack/yestrack.zip`, but ordinary `api/sharedownload` returned errno=113 signature error.
- A800 resource discovery: complete Refer-KITTI-V2 data, official FlexHook checkpoint/backbone, Temp-NeuralSORT-kitti2 candidate tree, and TempRMOT rk2/R50 baseline assets found; see `analysis/a800_resource_manifest.csv`.
- A800 contains `BaiduPCS-Go`, but the local host cannot execute that binary because it requires glibc >=2.32; the A800 key is forced SFTP-only, so no remote client execution or archive download was attempted through it.
- A800 FlexHook official full inference started and loaded all checkpoint keys; last observed progress was batch 500/7443.
- Historical TempRMOT V2 auxiliary file-schema sample: 40 expression pairs, four videos.
- Candidate ceiling computation completed on A800 FlexHook test tuple: 862 expressions, 491286 GT target boxes; at IoU 0.5, 362304 boxes matched (73.746%), with 26.254% outside any candidate. This is not HOTA/IDF1 or completed O0/O1/O2.
- Candidate identity proxy completed: at IoU 0.5, mean ID purity 93.513%, 4725 ID switches over 362304 matched target frames; see `analysis/flexhook_identity_proxy.csv`.
- Candidate error breakdown completed at IoU 0.5: video 0019 has the lowest coverage (71.265%), 88282 missing target boxes, 3829 candidate-ID switches, and a 77-frame longest missing run; see `analysis/flexhook_candidate_error_summary.csv`.
- Candidate-gap summary completed: IoU 0.3/0.5/0.7 leave 24.68%/26.25%/30.16% of GT boxes uncovered; 0019 contributes 68.45% of the IoU 0.5 missing boxes; 501/8043 target tracks have no candidate match and 2363/8043 have a candidate-ID switch. Reproducible table: `analysis/flexhook_candidate_gap_breakdown.csv`.
- Delivery tests: 7 passed after allowing explicit `RUNNING`/`PENDING` states with blank metrics.
- Read-only entrypoint preflight: YesTrack base/RMOT2 and FlexHook base failed at dependency import; exact errors are in `analysis/entrypoint_preflight.csv`.

## Remaining blocks / active run

- YesTrack: official V2 weight/candidate/MOTC release bytes unavailable; public archive is listed but not downloaded; Qwen3-VL cache absent. A800 OneJev/GroundJEV assets are non-official and not substituted.
- FlexHook: A800 official full inference is active or stalled after the last visible batch 500/7443; final raw result/receipt is not yet available. Two syntax errors remain in the untouched local original checkout and are tracked separately from the remote runtime.
- Shared-candidate comparison, official TrackEval, Oracle and visual cases: no legal input tuple.

No large official weight/dataset, private log, or authentication cookie is copied into this project; only paths, sizes, hashes and public-share metadata are recorded.
