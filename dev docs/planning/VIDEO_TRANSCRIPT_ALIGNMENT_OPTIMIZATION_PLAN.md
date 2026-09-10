# 视频字幕与音画一致性优化方案

> 状态：P0 已于 2026-09-10 实施、部署并取得两条真实视频证据；P1 暂缓。第二条历史修复的核心 Transcript/Note 已完成，非核心截图与列表物化因协作取消停在下载视频阶段，不能据此宣称全链路完全完成。

## 1. 问题与结论

已确认以下两条视频的 BV、CID、标题、下载视频与 Source/VideoAsset 绑定正确，但 Bilibili `ai-zh` 字幕内容与实际音画无关：

| Note | 正确视频主题 | 错误字幕主题 | 可见异常 |
| --- | --- | --- | --- |
| `note_d0a5923a0cee4a2d88df37fa9ee282f4` | 九月旅行目的地推荐 | 露丝出狱寻妹的电影解说 | 530 秒视频对应字幕末段为 838.5 秒；84.9 秒画面为“黑龙江抚远”，Segment 却为“露丝独自照顾妹妹长大” |
| `note_dcd0049a8d5a47c391c9b614ba35962c` | 九月限定景观推荐 | 兴趣、才华与个人成长自述 | 33.8 秒画面讲景区窗口期，Segment 却为“但是高中开课之后” |

当前 Pipeline 对任意非空平台字幕直接执行 `materialize_transcript()`，随后跳过音频下载和 ASR。现有质量门禁只识别空文本、乱码、相邻重复和低置信度，不验证字幕与 BV/CID、视频时长、音频或画面是否一致；总结模型即使发现标题与转写冲突，也只写 warning，仍继续物化 Note、Section、PlaceMention 和截图说明。

高置信根因是任务执行时获得了错误或失效的 Bilibili AI 字幕轨，应用缺少不可信平台字幕的完整性门禁。历史任务未保存字幕轨 ID、请求端点、`subtitle_url` 哈希或响应正文哈希，因此不能完成平台响应级的绝对归因。另有契约漂移：规格要求 `/x/player/wbi/v2`，当前代码使用 `/x/player/v2`；需要修正并审计，但现有证据不足以认定它单独导致本次错配。

## 2. 目标与边界

### 2.1 目标

1. 平台生成式字幕不能再未经音频验证成为权威 Transcript。
2. 检出异常时自动回退既有音频下载和 Whisper ASR，不让错误 Transcript 进入 `GENERATE_AI_NOTE`。
3. 保存足以追溯字幕来源和验证结论的非敏感元数据。
4. 对受污染历史 Note 生成新的 Transcript Version 和 Note Version，保留旧版本供审计。
5. 自动测试不访问 Bilibili、下载真实视频或调用真实 LLM/ASR Provider；真实验收单独授权并串行执行。

### 2.2 非目标

- 不用标题关键词匹配替代音频一致性验证；标题可能口语化或具有悬念，只能作为弱信号。
- 不在本工作包引入视觉模型、OCR 服务、向量数据库或新的外部依赖。
- 不原地修改历史 Transcript、Segment、Evidence 或 Note Version。
- 不自动迁移生产库、重启服务、重跑真实视频或调用真实模型。

## 3. 推荐设计

### 3.1 字幕信任分级

`SubtitleTrack` 增加可确定的来源属性：`track_id`、`language`、`language_doc`、`is_generated` 和 `endpoint`。按以下规则处理：

| 字幕类型 | 默认信任级别 | Pipeline 行为 |
| --- | --- | --- |
| 人工中文字幕 | `TRUSTED_PLATFORM` | 通过结构与时间轴门禁后可直接物化；异常则回退 ASR |
| `ai-zh`、自动/机器字幕 | `UNVERIFIED_GENERATED` | P0 阶段不直接物化，保留哈希后进入现有音频/ASR路径 |
| 其他语言字幕 | `UNVERIFIED_OTHER` | 依现有语言策略选择；作为权威输入前必须通过一致性验证 |
| 本机 ASR | `LOCAL_ASR` | 作为平台 AI 字幕不可信时的权威回退结果 |

不能继续使用“`source_kind` 不含 `ASR` 就是高质量平台字幕”的隐式判断。`Transcript.source_kind` 至少区分 `BILIBILI_HUMAN_SUBTITLE`、`BILIBILI_AI_SUBTITLE` 与 `WHISPER_CPP_ASR`；字段仍为字符串，无需新增数据库列。

### 3.2 P0：立即止损

对生成式字幕采用最小可靠改动：

```text
解析 BV/CID 与字幕轨
→ 人工字幕：校验后沿用现有直通路径
→ AI 字幕：只记录来源与内容哈希，不物化为权威 Transcript
→ 进入现有 DOWNLOAD_AUDIO → ASR → NORMALIZE_TRANSCRIPT
→ 仅从 ASR Transcript 生成 Note
```

P0 不实现新算法，只改变 AI 字幕分支条件并复用已有 ASR 路径。即使增加本地处理时间，也优先保证不会产出主题完全错误的笔记。

### 3.3 P1：抽样验证后恢复性能

P0 稳定后增加有界验证，避免所有 AI 字幕都执行完整 ASR：

1. 下载音频后，从前段、中段、后段各取一个 15–25 秒样本；优先落在已有字幕非空区间。
2. 使用当前 Whisper.cpp 对三个样本串行转写，不新增模型或依赖。
3. 对样本文本做统一空白、标点、大小写和常见口头词归一化，使用 Python 标准库 `difflib.SequenceMatcher` 计算字幕与 ASR 的相似度。
4. 三段中至少两段达到阈值且没有严重时间轴异常，标记 `VERIFIED_GENERATED` 并允许平台字幕直通；否则标记 `PLATFORM_SUBTITLE_MISMATCH`，继续完整 ASR。
5. 阈值先由 Fixture Golden 固定，真实样本验收后再调整；不得只凭标题相似度放行。

建议初始门禁：单段相似度 `>= 0.55` 为通过，三段中至少两段通过；`last_end_ms > duration_ms + max(30_000, duration_ms * 0.20)` 直接判为时间轴异常并回退 ASR。阈值属于待验证参数，不写死在多个调用点，只保留一处配置和一组回归样本。

### 3.4 生成前硬门禁

在 `GENERATE_AI_NOTE` 前统一检查：

- Transcript 必须有 `validation_status`，且状态属于 `TRUSTED_PLATFORM`、`VERIFIED_GENERATED` 或 `LOCAL_ASR`；
- Transcript 的 `video_asset_id`、Snapshot `source_id`、请求 BV/CID 必须与当前 Job 一致；
- Segment 非空、顺序稳定、时间轴没有硬异常；
- 检出 `PLATFORM_SUBTITLE_MISMATCH` 且 ASR 未成功时，任务进入 `NEEDS_USER`，错误码为 `TRANSCRIPT_SOURCE_MISMATCH`，不得继续总结或物化；
- 总结阶段仍可报告标题与内容存在弱冲突，但不能承担字幕真实性判定。

## 4. 审计与数据记录

优先复用现有 JSON 字段，不新增 Schema/Migration：

### 4.1 `Transcript.metadata_json`

```json
{
  "requested_bvid": "...",
  "requested_cid": "...",
  "subtitle_endpoint": "/x/player/wbi/v2",
  "subtitle_track_id": "...",
  "subtitle_language": "ai-zh",
  "subtitle_generated": true,
  "subtitle_url_sha256": "...",
  "subtitle_body_sha256": "...",
  "timeline_ratio": 1.0,
  "validation_status": "LOCAL_ASR",
  "validation_reasons": ["PLATFORM_SUBTITLE_MISMATCH"],
  "validation_version": "subtitle-alignment-v1"
}
```

只保存 URL 哈希，不保存带临时参数的完整字幕 URL；不保存 Cookie、SESSDATA 或其他 Secret。若 AI 字幕未成为权威 Transcript，则将同类字段写入 `FETCH_SUBTITLE` Step/Artifact，而不是伪装成 Transcript 来源。

### 4.2 `ExternalCallAudit` 与 Job Step

- `VIDEO_RESOLVE`：记录 `bvid`、`cid`、`page_number`、实际 endpoint 和轨道数量。
- `VIDEO_SUBTITLE`：记录轨道 ID、语言、是否 AI、URL 哈希、正文哈希、Segment 数、首末时间，不记录正文。
- `FETCH_SUBTITLE.output_json`：记录 `accepted`、`validation_status`、`validation_reasons`、`fallback_to_asr`。
- `NORMALIZE_TRANSCRIPT.output_json`：记录最终权威来源和时间轴比例。

这些字段使后续能够区分“平台返回错误轨”“应用绑定错误轨”“历史 Transcript 被错误复用”，且不会泄露凭据或大段原文。

## 5. 代码工作包

### WP1：来源与审计

涉及：

- `backend/src/zhijian/resolvers/video/bilibili.py`
- `backend/src/zhijian/services/video_pipeline.py`
- `backend/src/zhijian/services/external_audit.py`（仅在现有接口无法表达时调整）

内容：改用规格约定的 `/x/player/wbi/v2`；保留实际 endpoint；解析轨道 ID/生成类型；补齐非敏感哈希与 BV/CID 审计。若为兼容性保留 `/x/player/v2` fallback，必须在审计中明确记录，且 fallback 返回的 AI 字幕仍走不可信分支。

### WP2：P0 信任门禁与 ASR 回退

涉及：

- `backend/src/zhijian/services/video_pipeline.py`
- `backend/src/zhijian/services/video_support.py`
- `backend/src/zhijian/ai/transcript_quality.py`

内容：区分人工/AI 字幕；AI 字幕不再触发 `subtitle_available → skip ASR`；在生成前增加统一验证状态断言；时间轴硬异常进入 ASR fallback，而不是直接物化。

### WP3：P1 抽样一致性验证

涉及既有 FFmpeg、Whisper.cpp 与音频缓存封装，不引入新 Provider。实现单一 `validate_generated_subtitle()`，返回结构化状态、分段分数和原因；调用方只消费结果，不复制阈值逻辑。

### WP4：历史数据修复

修复对象：

- `note_d0a5923a0cee4a2d88df37fa9ee282f4`
- `note_dcd0049a8d5a47c391c9b614ba35962c`

在代码部署和真实视频授权后，从可信音频重新生成：

```text
新 Transcript Version
→ 新 Snapshot / Segment（保留 raw/corrected 身份）
→ 新 Note Version / Section / Map Facts
→ 重新生成 PlaceMention、截图计划与说明
→ 切换 AINote.current_version_id
```

旧 Transcript、Note Version、Evidence 保留且标记被新版本替代；不得修改旧 Segment 文本。开始前检查活跃 Job/lease，避免与 Worker 并发；真实 Provider 调用串行并遵守预算/QPS。

## 6. 验证方案

### 6.1 自动测试

在 `backend/tests/test_video_notes.py` 增加最小 Fixture：

1. 人工中文字幕、时间轴正常：直接物化，不运行 ASR。
2. AI 中文字幕：P0 必须走 ASR，最终 Transcript 来源为 `WHISPER_CPP_ASR`。
3. 旅行标题 + 电影字幕 + 旅行 ASR：Note 输入只包含旅行 ASR，不包含“露丝”。
4. 旅行标题 + 兴趣字幕 + 旅行 ASR：Note 输入只包含旅行 ASR，不包含“兴趣广泛”。
5. 530 秒视频 + 838.5 秒字幕：判定时间轴异常并回退 ASR。
6. AI 字幕异常且 ASR 不可用：Job 为 `NEEDS_USER/TRANSCRIPT_SOURCE_MISMATCH`，不存在新 Note Version。
7. 同时运行两个 Job：字幕 Track、Snapshot、Transcript 不交叉复用。
8. 审计只包含哈希和 ID，不包含 Cookie、完整字幕 URL或字幕正文。

P1 追加相似、部分相似、完全不相关、短视频和片尾静音样本，验证阈值只影响 AI 字幕直通，不改变人工字幕或现有 ASR 行为。

### 6.2 代码验证

开发中先运行目标测试与目标 Ruff；工作包完成后按仓库规则运行一次完整后端测试。没有前端行为变化时不做 Browser 验收；若增加异常状态/恢复卡，再补 PC 与 390×844 移动验收。

### 6.3 真实验收（需单独授权）

1. 串行重放上述两个视频，不并发调用模型。
2. 核对 BV/CID、视频文件哈希、最终 Transcript 来源与验证状态。
3. 在至少前、中、后三个时间点对照视频硬字幕/语音和 Segment。
4. 确认两条新 Note 均为九月旅行内容，且不含“露丝”“兴趣广泛”等污染主题。
5. 确认旧版本仍可审计，新版本成为 `current_version_id`。
6. 检查 PlaceMention、截图 caption 和 Section 均来自新 Transcript；不得仅以 Job 命令成功作为通过。

## 7. 验收条件

- [ ] 任意 `ai-zh` 字幕未经验证不得成为唯一权威 Transcript。
- [ ] 字幕验证失败时自动回退 ASR；ASR 失败则阻止 `GENERATE_AI_NOTE`。
- [ ] 两个污染样本的离线 Fixture 能稳定复现并阻止错误主题进入 Note。
- [ ] 字幕请求与校验具备 BV/CID、轨道、端点和内容哈希审计，且无 Secret/正文泄露。
- [ ] 人工字幕和原无字幕 ASR 路径保持兼容。
- [ ] 历史修复生成新版本，不原地覆盖 Source/Snapshot/Segment/Transcript/Note/Evidence。
- [ ] 真实重放、部署、服务重启和生产数据处理均保持独立授权边界。

## 8. 推荐执行顺序与停止点

顺序：`WP1 → WP2 → 自动回归 → 部署授权 → 两条真实修复验收 → 评估是否需要 WP3`。

P0 已能可靠阻断同类污染；只有实际数据证明全量 ASR 的延迟或资源成本不可接受时才实施 P1。不要在 P0 中同时引入视觉理解或复杂语义分类器。

### 8.1 本次执行结果

- WP1、WP2 已完成：WBI 字幕轨记录来源/哈希，`ai-zh` 被标记为不可信并强制转入 Whisper ASR；生成前验证 VideoAsset、Source、BV/CID、Snapshot 与时间轴。
- 本机 Ollama 对长 ASR 校对固定为每批最多 32 段，避免原 128 段请求在 180 秒内超时；不改变远程默认路由或新增依赖。
- 自动验证通过：目标 Ruff、视频相关 36 项测试、后端全量 117 项；前端 `pnpm verify` 在可用 Node 24 运行时通过。当前 shell 的 Node 16 不兼容 ESLint 9，未找到 Node 22。
- `note_d0a5923a0cee4a2d88df37fa9ee282f4`：新 Transcript/Note v2 已完成，终态 `PARTIAL_SUCCESS` 仅有 2 个 POI 待确认。
- `note_dcd0049a8d5a47c391c9b614ba35962c`：新 Transcript/Note v2 已完成并成为当前版本；Job 在 `DOWNLOAD_VIDEO_FOR_FRAMES` 被协作取消，未重新触发模型，因此截图、列表 ContentItem 物化及终态仍待后续受支持的非核心续跑。
- P1 不进入本轮：两个完整 ASR 分别约 34 秒与 31 秒，未显示不可接受的资源成本；先以 P0 作为可靠基线。

## 9. 相关契约

- [输入、登录、字幕与转写](../../video/02-input-transcript.md)
- [笔记、地点、截图与物化](../../video/03-generation-materialization.md)
- [回归与变更冻结清单](../../REGRESSION_AND_CHANGE_GUARD.md)
- [Bilibili Resolver](../../../backend/src/zhijian/resolvers/video/bilibili.py)
- [Video Pipeline](../../../backend/src/zhijian/services/video_pipeline.py)
- [Transcript Quality](../../../backend/src/zhijian/ai/transcript_quality.py)
