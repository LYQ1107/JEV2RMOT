# 详细错误分类

## FlexHook V2 实测分解

按 `(video, expression, frame, candidate_id)` 对齐官方 raw logits、固定候选和 GT；IoU 阈值为 0.5。事件允许重叠，假阳性是保留的非匹配候选，不与 GT-frame 分母混加。

| 类别 | 数量 | 分母/解释 |
|---|---:|---|
| `CANDIDATE_MISSING` | 128,982 | 491,286 GT-frame 的 26.254%，二阶段不可修复 |
| `MODEL_WINDOW_MISSING` | 7,750 | 1.577%，官方 DataLoader 末帧窗口缺 raw score，不归因语言选择 |
| 合格候选 + raw score 的 matched TP | 314,142 | 选择正确的 GT-frame |
| `REFER_FALSE_NEGATIVE` | 40,412 | 有合格候选且有 raw score 的 11.398% |
| `REFER_FALSE_POSITIVE` | 436,690 | 750,832 个正决策中的 58.161%；候选被保留但未匹配当前表达式目标 |

在有合格候选且有 raw score 的 354,554 个 GT-frame 中，选择正确率为 88.602%，假阴性率为 11.398%。假阴性平均 `p_yes=0.101` 左右，而假阳性平均 `p_yes` 约 0.93，说明错误不是单纯集中在 0.5 附近的阈值噪声；关系/竞争候选和身份历史值得检查。逐视频汇总见 [`analysis/flexhook_model_error_summary.csv`](../analysis/flexhook_model_error_summary.csv)，紧凑事件表见 [`analysis/error_events.csv`](../analysis/error_events.csv)。

### 按视频

| 视频 | 候选缺失 | 窗口缺口 | 选择假阴性 | 选择假阳性 |
|---:|---:|---:|---:|---:|
| 0005 | 5,734 | 1,259 | 5,771 | 16,388 |
| 0011 | 27,449 | 1,286 | 13,085 | 33,191 |
| 0013 | 7,517 | 1,233 | 2,949 | 48,810 |
| 0019 | 88,282 | 3,972 | 18,607 | 338,301 |

0019 同时贡献 68.45% 的候选缺失和约 77.5% 的假阳性，仍是优先排查视频。假阳性不一定全部是视觉语言理解错误，也可能是表达式对应多个竞争候选、GT 对象未覆盖、或官方候选/表达式协议带来的非目标框保留。

## 身份和时间

官方 O0 CLEAR 指标为 IDSW=2,908；O1 仍有 4,601 次 IDSW，O2 通过离线 GT identity mapping 降为 0。候选层独立统计显示 4,725 次候选 ID 切换、2,363/8,043 条目标轨迹发生切换；这类问题不能全部归咎于 FlexHook selection。

`analysis/temporal_error_chains.csv` 包含 15,486 条连续候选缺失/选择假阴性链。它们是描述性连续事件，不证明 TCP/TRP 因果；FlexHook 没有 YesTrack 的 TCP/TRP，但其 4-frame window 和候选 ID 历史仍可能造成错误延续。`MODEL_WINDOW_MISSING` 单独标注为协议/采样边界，不能计入 JEV 的语言错误。

## 已验证的机制边界

- FlexHook `test_utils.py` 的最终决策是 `argmax(score)>0`，输出沿用候选 bbox 和 ID。
- 候选缺失、IoU 不足、末帧窗口缺失不能靠普通 Yes/No 修复。
- 选择假阴性、假阳性由冻结 raw logits 直接归因；没有用最终 MOT 结果反推分数。
- O1/O2 是离线 Oracle，不参与 O0 推理，也没有训练新参数。
