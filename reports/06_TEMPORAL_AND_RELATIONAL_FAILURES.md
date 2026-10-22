# 时间与关系型失败

## 已完成的实测

FlexHook raw result 已封存。每个候选帧包含 negative/positive logit，最终决策为 argmax(score)>0；O0 的 TrackEval 为 HOTA 42.526、IDSW 2,908。离线对齐得到 40,412 个合格候选上的选择假阴性和 436,690 个选择假阳性，连续事件链见 `analysis/temporal_error_chains.csv`。

YesTrack V2 的 862 个表达式已使用官方 prompts/crops、视频精炼、TCP 和 TRP 语义完成。原生 threshold 0.60 的 O0 为 HOTA 41.155、IDSW 3,169；官方候选 IoU 0.5 覆盖只有 57.870%。

## 同一候选下的错误分解

共享 FlexHook 候选在 A800 GT 上覆盖 362,304/491,286 = 73.746%，缺失 128,982 个 GT boxes。YesTrack @0.60 对 2,425,382 行全部产生 score，之后得到：

| 类别 | 数量 | 解释 |
|---|---:|---|
| CANDIDATE_MISSING | 128,982 | GT boxes 的 26.254%，二阶段不可修复 |
| MATCHED_TRUE_POSITIVE | 327,801 | score >= 0.60 且匹配当前表达式 GT |
| REFER_FALSE_NEGATIVE | 34,503 | 有合格候选但 score < 0.60 |
| REFER_FALSE_POSITIVE | 276,224 | score >= 0.60 但未匹配当前表达式 GT |
| MODEL_WINDOW_MISSING | 0 | 共享候选的所有行均有 score |

按视频，共享候选 IoU 0.5 的 matched/missing 为：0005 `37,954/5,734`，0011 `76,675/27,449`，0013 `28,731/7,517`，0019 `218,944/88,282`。0019 贡献了 68.45% 的候选缺失，仍是第一阶段和长序列稳定性的优先对象。

原生 YesTrack 的对应数字是 candidate missing 206,978、selection FN 27,345、selection FP 198,536；它们不能与共享候选数字混为一谈，因为 candidate pool 不同。

## 身份和时间

| 口径 | matched-frame recall | mean ID purity | ID switches | 有切换轨迹 |
|---|---:|---:|---:|---:|
| FlexHook candidate-only proxy | 73.746% | 0.9351 | 4,725 | 2,363 |
| native YesTrack candidate proxy, score 0.50 | 53.130% | 0.9275 | 6,208 | 2,192 |
| native YesTrack candidate proxy, score 0.60 | 51.696% | 0.9320 | 5,614 | 2,081 |
| shared candidate + YesTrack, score 0.50 | 67.732% | 0.9443 | 3,800 | 1,963 |
| shared candidate + YesTrack, score 0.60 | 65.746% | 0.9503 | 3,381 | 1,813 |

这些 proxy 的分母和 selection 方式不同，主要用于定位身份/历史证据，不代替 official IDSW。共享 O1 保留原候选 ID 时 IDSW=4,601，O2 做 GT identity mapping 后 IDSW=0，HOTA 从 65.423 增到 69.125；这说明身份连续性有研究空间，但不证明实际 JEV 能达到 identity oracle。

## 时间传播边界

YesTrack 本轮保存了 video refinement、TCP 和 TRP 运行语义，但没有分别关闭它们做因果消融；FlexHook 也没有 YesTrack 的 TCP/TRP。下一步应固定候选和 checkpoint，依次比较：

1. 单帧直接推理；
2. 只开启 video refinement；
3. 再开启 TCP；
4. 最后开启 TRP 与 `infer_every_n_frames=4`。

只有这样才能把连续错误从描述性现象提升为传播机制证据。当前不把任何链条直接归因给 TCP/TRP。

## 研究含义

同帧竞争、表达式语义、轨迹历史和短时视觉状态都可能提供额外信息。选择假阳性规模大，支持先做无训练竞争抑制、阈值校准和 ID 稳定规则，再决定是否训练 JEV；但候选缺失、IoU 不足和 FlexHook 末帧窗口缺口必须由第一阶段或几何协议处理。
