# 详细错误分类

## FlexHook V2 实测分解

按 video、expression、frame、candidate_id 对齐官方 raw logits、固定候选和 GT；IoU 阈值为 0.5。事件允许重叠，假阳性是保留的非匹配候选，不与 GT-frame 分母混加。

| 类别 | 数量 | 分母/解释 |
|---|---:|---|
| CANDIDATE_MISSING | 128,982 | 491,286 GT-frame 的 26.254%，二阶段不可修复 |
| MODEL_WINDOW_MISSING | 7,750 | 1.577%，官方 DataLoader 末帧窗口缺 raw score，不归因语言选择 |
| 合格候选 + raw score 的 matched TP | 314,142 | 选择正确的 GT-frame |
| REFER_FALSE_NEGATIVE | 40,412 | 有合格候选且有 raw score 的 11.398% |
| REFER_FALSE_POSITIVE | 436,690 | 750,832 个正决策中的 58.161%；候选被保留但未匹配当前表达式目标 |

在有合格候选且有 raw score 的 354,554 个 GT-frame 中，选择正确率为 88.602%，假阴性率为 11.398%。假阴性平均 p_yes 约 0.10，假阳性平均 p_yes 约 0.93，说明错误不是单纯集中在 0.5 附近的阈值噪声。逐视频汇总见 analysis/flexhook_model_error_summary.csv、analysis/error_events.csv。

| 视频 | 候选缺失 | 窗口缺口 | 选择假阴性 | 选择假阳性 |
|---:|---:|---:|---:|---:|
| 0005 | 5,734 | 1,259 | 5,771 | 16,388 |
| 0011 | 27,449 | 1,286 | 13,085 | 33,191 |
| 0013 | 7,517 | 1,233 | 2,949 | 48,810 |
| 0019 | 88,282 | 3,972 | 18,607 | 338,301 |

0019 同时贡献 68.45% 的候选缺失和约 77.5% 的假阳性，仍是优先排查视频。假阳性不一定全部是视觉语言理解错误，也可能是表达式对应多个竞争候选、GT 对象未覆盖、或官方候选/表达式协议带来的非目标框保留。

## YesTrack V2 实测分解

YesTrack 使用官方 TempRMOT* 候选、官方 V2 GT 和输出 score，在 IoU 0.5 做逐帧一对一匹配；主决策点采用官方文档建议的 V2 threshold 0.60。该结果与 FlexHook 分开统计，不能混合分母。

| 类别 | 数量 | 占 GT-frame / output 的比例 | 解释 |
|---|---:|---:|---|
| CANDIDATE_MISSING | 206,978 | GT-frame 的 42.130% | 官方候选没有 IoU 0.5 合格框，冻结二阶段不能修复 |
| 候选可匹配 GT | 284,308 | GT-frame 的 57.870% | 候选层可达到的几何覆盖 |
| MATCHED_TRUE_POSITIVE | 256,963 | 合格候选的 90.382% | score >= 0.60 且匹配当前表达式 GT |
| REFER_FALSE_NEGATIVE | 27,345 | 合格候选的 9.618% | 有候选但 score < 0.60 |
| REFER_FALSE_POSITIVE | 198,536 | 输出的 43.586% | score >= 0.60 但未匹配当前表达式 GT |
| MODEL_WINDOW_MISSING | 0 | 不适用 | YesTrack 这次对释放的 1,850,576 个候选行均产生了 score |

YesTrack threshold 0.60 的官方输出为 455,499 rows；其中 256,963 是当前表达式 GT 可匹配的保留候选，198,536 是保留但不匹配的候选。IoU 0.3/0.5/0.7 的候选覆盖分别为 59.161%/57.870%/54.336%，说明候选层是 YesTrack 的首要硬瓶颈。按视频，IoU 0.5 的 matched/missing 为：

| 视频 | GT boxes | matched | missing |
|---:|---:|---:|---:|
| 0005 | 43,688 | 35,867 | 7,821 |
| 0011 | 104,124 | 71,180 | 32,944 |
| 0013 | 36,248 | 18,874 | 17,374 |
| 0019 | 307,226 | 158,387 | 148,839 |

这里的 YesTrack 错误数字来自官方候选和 score 的离线对齐，不是用论文数字或 Oracle 结果反推。完整计数、阈值敏感性和 identity proxy 在 run/analysis/yestrack_candidate_oracle/yestrack_candidate_oracle_summary.json。

## 身份和时间

FlexHook 官方 O0 CLEAR 的 IDSW 为 2,908；其 O1 保留候选原 ID 后 IDSW 为 4,601，O2 GT identity mapping 后为 0。候选层独立统计显示 4,725 次候选 ID 切换、2,363/8,043 条目标轨迹发生切换。

YesTrack 官方 O0 threshold 0.60 的 IDSW 为 3,169。YesTrack 候选 proxy 在 IoU 0.5、score threshold 0.5 下有 6,208 次切换，2,192/8,043 条目标轨迹发生切换；threshold 0.6 下为 5,614 次、2,081/8,043 条轨迹，匹配帧 recall 为 51.696%。这些是可供联合 JEV 使用的身份历史证据，不等于二阶段独立造成了全部 IDSW。

analysis/temporal_error_chains.csv 中的 FlexHook 连续链是描述性证据，不证明 TCP/TRP 因果；FlexHook 没有 YesTrack 的 TCP/TRP。YesTrack 本轮保存了 TRP/TCP 运行语义，但没有把“传播错误”单独宣称为因果，需要做开关/窗口消融后才能下结论。

## 已验证的机制边界

- FlexHook test_utils.py 的最终决策是 argmax(score)>0，输出沿用候选 bbox 和 ID。
- YesTrack 的官方 V2 结果对全部释放候选行产生 score；主评测阈值 0.60，threshold sweep 的 HOTA 只从 39.819 变化到最高 41.179。
- 候选缺失、IoU 不足和 FlexHook 末帧窗口缺失不能靠普通 Yes/No 修复。
- 选择假阴性、假阳性由冻结 score 与 GT 后验对齐；没有用最终 MOT 结果反推模型分数。
- O1/O2 是离线 Oracle，不参与 O0 推理，也没有训练新参数。
