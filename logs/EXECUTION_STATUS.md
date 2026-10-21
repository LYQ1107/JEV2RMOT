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
- Delivery tests: 7 passed after allowing explicit `RUNNING`/`PENDING` states with blank metrics.
- Read-only entrypoint preflight: YesTrack base/RMOT2 and FlexHook base failed at dependency import; exact errors are in `analysis/entrypoint_preflight.csv`.

## Remaining blocks / active run

- YesTrack: official V2 weight/candidate/MOTC release bytes unavailable; public archive is listed but not downloaded; Qwen3-VL cache absent. A800 OneJev/GroundJEV assets are non-official and not substituted.
- FlexHook: A800 official full inference is active or stalled after the last visible batch 500/7443; final raw result/receipt is not yet available. Two syntax errors remain in the untouched local original checkout and are tracked separately from the remote runtime.
- Shared-candidate comparison, official TrackEval, Oracle and visual cases: no legal input tuple.

No large official weight/dataset, private log, or authentication cookie is copied into this project; only paths, sizes, hashes and public-share metadata are recorded.
