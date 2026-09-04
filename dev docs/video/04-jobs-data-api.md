# Job、数据身份与 API

> 来源：video/VIDEO_AI_NOTE_PIPELINE.md，原章节 5–7（正文保留，2026-09-03 分篇）。返回 [主题索引](VIDEO_AI_NOTE_PIPELINE.md)。本篇是契约/规划，不是已实施清单；当前结论见 [实施状态](../IMPLEMENTATION_STATUS.md)，安全与回归见 [冻结清单](../REGRESSION_AND_CHANGE_GUARD.md)。裸文档路径均以 dev docs/ 为基准。只读取命中章节及其必要约束。

# 5. Job 状态与恢复

建议步骤和进度：

| Step | 建议进度 | 可复用缓存 | 可单步重跑 |
|---|---:|---|---|
| NORMALIZE_CAPTURE_INPUT | 2 | selected URL | 是 |
| VALIDATE_LINK | 5 | canonical URL | 是 |
| FETCH_METADATA | 12 | Source Snapshot | 是 |
| FETCH_COVER | 18 | CoverAsset / local derivative | 是 |
| FETCH_SUBTITLE | 22 | raw/normalized subtitle | 是 |
| DOWNLOAD_AUDIO | 32 | media cache | 是 |
| ASR | 48 | Transcript | 是 |
| NORMALIZE_TRANSCRIPT | 60 | normalized Transcript Version | 是 |
| CORRECT_TRANSCRIPT | 62 | corrected Transcript Version | 是 |
| GENERATE_AI_NOTE | 65 | Note chunk/checkpoint | 是 |
| EXTRACT_TRAVEL_FACTS | 76 | typed extraction | 是 |
| RESOLVE_POI | 86 | provider candidates | 是 |
| BUILD_PLACE_NOTES | 90 | Place Note Version | 是 |
| PLAN_SCREENSHOTS | 92 | Screenshot Plan | 是 |
| DOWNLOAD_VIDEO_FOR_FRAMES | 94 | bounded video cache | 是 |
| EXTRACT_SCREENSHOTS | 97 | Screenshot Assets | 是 |
| MATERIALIZE | 99 | View projection | 是 |
| CLEAN_CACHE | 100 | 不适用 | 是 |

有平台字幕时跳过 `DOWNLOAD_AUDIO/ASR`，进度直接推进，但保留 `SKIPPED` Step 记录。Worker 重启后从最后一个已完成且输入哈希一致的 Step 恢复。

失败后的人工续跑不从首步骤开始。Artifact Manifest 有效时，上游 COMPLETED 步骤在新 Attempt 中标记 `REUSED`，从失败步骤开始，后续步骤顺次执行；TTL 到期或输入/版本变化时步骤级续跑不可用，只能完整重跑。完整契约见 `jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md`。

最终状态：

- `COMPLETED`：AI 笔记完成，地点处理已完成或视频无地点；
- `PARTIAL_SUCCESS`：AI 笔记可读，但部分地点需确认或部分增强失败；
- `NEEDS_USER`：需要 Cookie、登录、模型配置或 POI 选择；
- `FAILED`：当前无法自动恢复；
- `CANCELLED`：用户取消。

---

# 6. 数据边界

需要新增或补全的核心实体：

```text
VideoAsset
Transcript
TranscriptSegment（复用通用 Segment）
AINote
AINoteVersion
AINoteSection
VideoScreenshot
PlaceMention
PlaceObservation
PlaceNote
PlaceNoteVersion
MapMarkerState
ExternalCallAudit
```

关键关系：

```text
Source 1 ── * Snapshot
Snapshot 1 ── 1 VideoAsset
VideoAsset 1 ── * Transcript
Transcript 1 ── * Segment
ContentItem 1 ── * AINoteVersion
AINoteVersion 1 ── * AINoteSection
AINoteSection 1 ── * VideoScreenshot
Segment 1 ── * Claim/Evidence
Segment 1 ── * PlaceMention
Place 1 ── * PlaceMention
Place 1 ── * PlaceObservation
Place 1 ── * PlaceNoteVersion
Place 1 ── 0..1 MapMarkerState
```

AI Note Markdown 不能代替 Transcript、Typed Claim 或 Evidence；Place Note Markdown 不能代替 PlaceObservation。

---

# 7. API 契约概要

Capture 继续使用统一入口：

```text
POST /api/inbox
GET  /api/inbox/{content_id}
```

视频笔记资源：

```text
GET  /api/video-notes
GET  /api/video-notes/{note_id}
GET  /api/video-notes/{note_id}/transcript
GET  /api/video-notes/{note_id}/places
GET  /api/video-notes/{note_id}/screenshots
POST /api/video-notes/{note_id}/regenerate
```

地点资源：

```text
GET  /api/travel/places
GET  /api/travel/places/{place_id}
GET  /api/travel/places/{place_id}/note
GET  /api/travel/places/{place_id}/sources
GET  /api/travel/map?bbox=&zoom=&place_type=&user_state=&query=
GET  /api/travel/map/bootstrap
POST /api/travel/map/markers
DELETE /api/travel/map/markers/{marker_id}
POST /api/travel/map/markers/{marker_id}/restore
```

所有入口最终使用同一个 `place_id` 和 Place Detail ViewModel。列表和 Marker 不维护第二份地点详情数据。

---
