# Data Model

## 1. 数据建模原则

1. 原始来源与业务结果分离。
2. Claim 与 Evidence 分离。
3. “视频中提到某地点”与“现实 POI”分离。
4. 招聘资格与用户偏好分离。
5. 个人 Profile 与 Preference 分离。
6. 原始行为事件与推导出的 Preference 分离。
7. AST/复杂嵌套规则可用 JSON；核心实体用关系表。
8. 所有结果保留 processor/model/version。

---

# 2. 核心领域对象

## ContentItem
用户一次输入。

## Source
外部信息源。

## Snapshot
某 Source 某次抓取内容。

## Segment
可定位的最小文本/字幕/表格单位。

## Claim
事实、标准化结果、计算或推断。

## Evidence
支持某 Claim 的来源定位。

## RecruitmentNotice
一场招聘。

## Position
具体岗位。

## Requirement
岗位/公告资格规则 AST。

## PlaceMention
内容中提到的地点。

## Place
解析后的现实 POI。

## UserProfile
客观个人条件。

## Preference
主观偏好。

## Job / JobStep
后台处理工作。

---

# 3. Content / Source

## content_items

建议字段：

```text
id
input_type
original_url
raw_text
capture_input_kind
selected_url
capture_candidate_count
discarded_text_length
raw_input_hash
status
processor_hint
created_at
updated_at
```

`capture_input_kind`：`URL_ONLY / SHARE_TEXT_WITH_URL / TEXT_ONLY / MULTIPLE_URLS`。URL 任务的 `raw_text` 必须为空；分享文案只参与瞬时 URL 提取，默认不持久化全文。`raw_input_hash` 用于排错和幂等，`discarded_text_length` 只记录被忽略文本长度。

## sources

```text
id
content_item_id
source_type
platform
url
external_id
title
publisher
author
published_at
authority_level
metadata_json
created_at
```

URL Source 的 `url/locator` 只能写 Input Normalizer 选中的 URL。页面或视频解析得到的正式 title 才写 `sources.title`；粘贴文案中的标题不得覆盖正式元数据。

文件型 Source 的 `metadata_json` 至少保存：原始文件名、MIME、字节数、内容哈希、解析器与 OCR 版本；文件正文仍通过 Snapshot/Segment 建模。

## source_snapshots

```text
id
source_id
fetched_at
content_hash
raw_path
normalized_path
metadata_json
```

## source_relations

```text
id
from_source_id
to_source_id
relation_type
evidence_segment_id
```

relation_type：
- references
- attachment
- original_source
- registration
- supplement
- supersedes
- related
- derived_from

---

# 4. Segment

## segments

```text
id
snapshot_id
segment_type
sequence_no
text
raw_text
corrected_text
locator_json
metadata_json
```

视频 Segment 的 `raw_text` 保存平台字幕/ASR 原文，`corrected_text` 保存 AI 校对稿；`text` 作为兼容投影默认返回 corrected_text，未校对时不得静默冒充已校对。校对不得改变 Segment ID、sequence_no 或时间码。

locator 示例：

网页：
```json
{"css_path":"...", "start_offset":10, "end_offset":50}
```

视频：
```json
{"start_ms":197200, "end_ms":211500}
```

Excel：
```json
{"sheet":"岗位计划表","row":27,"cell":"H27"}
```

PDF：
```json
{"page":7,"block":13}
```

DOCX：
```json
{"part":"document","paragraph":18,"run_start":2,"run_end":5}
```

OCR：
```json
{"page":3,"bbox":[120,240,920,318],"ocr_confidence":0.91}
```

---

# 5. Claim / Evidence

## claims

```text
id
subject_type
subject_id

claim_type
field
value_json

confidence

processor
processor_version
model_provider
model_name
parser_version

created_at
```

claim_type：
- EXTRACTED
- NORMALIZED
- COMPUTED
- INFERRED

## claim_evidences

```text
claim_id
segment_id
evidence_role
```

一个 Claim 可以多证据。
一个 Segment 可以支持多个 Claim。

## claim_relations

```text
from_claim_id
to_claim_id
relation_type
created_at
```

relation_type：
- derived_from
- normalizes
- computes_from
- conflicts_with
- supersedes

`NORMALIZED`、`COMPUTED` Claim 必须通过关系指向其输入 Claim；来源冲突不得只靠覆盖最终字段表达。

---

# 6. Recruitment

## recruitment_notices

```text
id
primary_source_id
title
organization
region
registration_start
registration_deadline
exam_date
interview_date
registration_url
status
created_at
```

## positions

```text
id
notice_id
position_code
name
organization
headcount
raw_row_json
created_at
```

## requirements

```text
id
notice_id nullable
position_id nullable

raw_text
dsl_version
ast_json

parser_model
parser_version
evidence_status

created_at
```

## requirement_matches

```text
id
requirement_id
position_id
profile_subject

status
reason_code
details_json
matched_evidence_json
created_at
```

status:
- PASS
- FAIL
- UNKNOWN
- REVIEW

## position_matches

```text
id
position_id
eligibility_status
preference_level
urgency_level
user_state
summary_json
updated_at
```

user_state:
- DISCOVERED
- INTERESTED
- PREPARING
- APPLIED
- DROPPED

---

# 7. User Profile

## profile_fields

```text
id
field_key
value_json
sensitivity
source
verified
updated_at
```

sensitivity:
- NORMAL
- SENSITIVE
- LOCAL_ONLY

## education_experiences

```text
id
level
school
raw_major_name
mapped_catalog_id
mapped_major_code
degree
graduation_date
verified
```

必须保留 `raw_major_name`，不允许映射结果覆盖原始专业名称。

## work_experiences（可在 Phase 2 引入）

```text
id
organization
role
start_date
end_date
description
tags_json
```

## certificates（可独立表或 profile JSON）

---

# 8. Major Catalog

## major_catalogs

```text
id
authority
name
version
education_level
effective_date
source_url
snapshot_id
```

## major_entries

```text
id
catalog_id
code
name
parent_code
level
aliases_json
```

## major_equivalences

```text
id
from_catalog_id
from_code
to_catalog_id
to_code
relation_type
evidence_source_id
```

---

# 9. Deadline / Todo

## deadlines

```text
id
subject_type
subject_id
deadline_type
at
claim_id
status
```

## todos

```text
id
subject_type
subject_id
title
todo_type
source_type
due_at
status
metadata_json
```

source_type：
- FACT_BASED
- SYSTEM_SUGGESTED

---

# 10. Travel / Food

## video_assets

```text
id
source_id
platform
canonical_url
external_video_id
part_number
external_part_id
title
author
cover_url
duration_ms
published_at
metadata_json
metadata_hash
resolver_version
created_at
updated_at
```

`platform + external_video_id + part_number` 用于识别同一个视频分 P；原始 URL 仍保存在 Source，不能被 canonical URL 覆盖。

## video_cover_assets

```text
id
video_asset_id
source_url
local_path
derivative_path
content_hash
content_type
width
height
byte_size
status
error_code
fetched_at
created_at
```

`status`：`PENDING / READY / UNAVAILABLE / INVALID`。VideoAsset.cover_url 保存平台元数据；CoverAsset 表示已下载并可由本地 API 服务的封面。原图按 SHA-256 去重，列表 672×378 WebP 衍生图可重建；不同 Note Version 复用同一 VideoAsset/CoverAsset。

## transcripts

```text
id
video_asset_id
snapshot_id
source_kind
language
full_text_hash
provider
model
adapter_version
correction_status
correction_provider
correction_model
correction_prompt_version
correction_coverage
status
created_at
```

`source_kind`：

- CLIENT_PREFETCHED_SUBTITLE
- PLATFORM_SUBTITLE
- YT_DLP_SUBTITLE
- ASR

Transcript 的正文通过通用 `segments` 表保存，视频 Segment 的 `locator_json` 至少包含 `start_ms/end_ms`。

`correction_status`：`PENDING / CORRECTING / CORRECTED / REVIEW / FAILED / PURGED`。每次重新校对生成新 Transcript Version 或版本化 Correction，不覆盖 raw。默认 Note、目录、页面预览和 TXT 导出使用 corrected_text；raw 只用于 Evidence/差异审计。

视频 Transcript 还必须保存 `retention_until` 与 `purged_at`。`metadata_json` 只能保存 `fingerprint_sha256`，不得保存由“时间码 + 正文”拼成的全文 fingerprint。完整转写固定保留 180 天；到期后 Transcript/Segment 行作为时间轴 tombstone 保留，但 `Transcript.text`、`Segment.text/raw_text/corrected_text` 与关联 `Evidence.quote` 被清空，`segment_count` 可保留原始数量供审计，API 依据 `purged_at` 返回 410。Note Section 的服务端时间范围和截图实际时间码不随文稿清理删除。

Whisper.cpp JSON 的 `offsets.from/to` 单位为毫秒。写入新 Transcript Version 前必须校验时间单调性及末段与 `VideoAsset.duration_ms` 的合理关系；约 10 倍的历史错误时间轴通过新版本修复，不原地覆盖旧版本。

## ai_notes / ai_note_versions

```text
ai_notes:
id
content_item_id
video_asset_id
current_version_id
created_at
updated_at

ai_note_versions:
id
ai_note_id
version_no
markdown
structured_json
input_hash
provider
model
prompt_version
template_version
status
created_at
```

重跑生成新版本，不静默覆盖旧 Markdown。`structured_json` 保存章节与 Segment 引用，但不能替代 Transcript、Claim 或 Evidence。

## ai_note_sections

```text
id
note_version_id
heading
thesis
summary
bullets_json
anchor_id
sequence_no
start_ms
end_ms
markdown
segment_ids_json
```

## video_screenshots

```text
id
video_asset_id
note_version_id
note_section_id nullable
place_mention_id nullable
segment_id nullable
planned_timestamp_ms
actual_timestamp_ms
image_path
content_hash
perceptual_hash
width
height
quality_score
selection_reason
caption
content_role
status
created_at
```

截图必须能回到视频时间码。`perceptual_hash` 用于去重；`caption/content_role` 必须说明地点、菜品、景区特色、路线、价格或关键结论，不能统一写“章节起始时间码代表帧”。截图是来源派生资产，不代替 Transcript Evidence。被 Note/Place 页面引用的截图进入永久派生存储，任务视频仍按缓存 TTL 清理。

## place_notes / place_note_versions

```text
place_notes:
id
place_id
current_version_id
created_at
updated_at

place_note_versions:
id
place_note_id
version_no
markdown
structured_json
input_hash
provider
model
prompt_version
status
created_at
```

Place Note 聚合多个 Mention/Observation/Source。事实必须通过 Claim/Evidence 回到 Transcript Segment；用户状态变化不直接改写事实版本。

## map_marker_states

```text
id
place_id
origin
visibility
custom_label nullable
created_by
created_at
updated_at
deleted_at nullable
```

`origin`：`AI_EXTRACTED / USER`。`visibility`：`VISIBLE / HIDDEN / DELETED`。用户 Marker 删除为软删除；自动 Marker 删除只改为 `HIDDEN`。Marker 是 Place 的投影，不能保存第二份完整地点详情。

## places

```text
id
name
canonical_name
place_type
origin
country
province
city
district
address
latitude
longitude
coordinate_system

external_provider
external_poi_id

resolution_status
metadata_json
created_at
```

`origin` 至少区分 `AI_EXTRACTED / USER / IMPORTED`。用户直接点选地图坐标时，`resolution_status=CONFIRMED` 只能表示 `USER_CONFIRMED`，不得伪装成高德 POI 命中；具体确认来源保存于 metadata。

resolution_status:
- CANDIDATE
- CONFIRMED
- REVIEW
- UNRESOLVED
- REJECTED

中国大陆高德 POI 的 `coordinate_system` 为 `GCJ02`。任何导出都必须携带该字段，不得默认标记为 WGS84。

## place_mentions

```text
id
source_id
segment_id
raw_name
suggested_name
place_type
city_hint
district_hint
resolved_place_id
resolution_confidence
status
metadata_json
```

`raw_name` 永远保留字幕/ASR 原文；高德确认名称写入关联 Place 的 `canonical_name`，不得覆盖原始 Mention。

## place_observations

```text
id
place_id
source_id
segment_id
observation_type
value_json
claim_id
observed_at
```

例如：
- price
- dish
- author_opinion
- warning
- ranking
- recommended_season

---

# 11. Preference

## preference_events

```text
id
target_type
target_id
event_type
created_at
metadata_json
```

event_type：
- SAVE
- DISMISS
- VISITED
- PLANNED
- LIKE
- DISLIKE

## preferences

```text
id
preference_key
weight
source_type
confidence
version
updated_at
```

source_type：
- EXPLICIT
- BEHAVIOR
- INFERRED

优先级：
EXPLICIT > BEHAVIOR > INFERRED

## visit_events

```text
id
place_id
trip_id nullable
visited_at
rating nullable
notes nullable
```

地点当前用户状态由 `preference_events` / `visit_events` 投影得到；若为查询性能物化缓存，缓存必须可从事件重建，不能成为唯一事实源。

---

# 12. Jobs

## jobs

```text
id
job_type
status
priority

content_item_id
subject_type
subject_id

current_step
progress

lease_owner
lease_expire_at
heartbeat_at

retry_count
max_retries
idempotency_key
error_code
error_message

created_at
started_at
finished_at
```

`idempotency_key` 对同一 Capture/Step 的重复提交建立唯一约束。Job Lease 必须通过单条条件更新原子抢占；Step 输出与领域写入按版本幂等 upsert，防止 Worker 崩溃恢复后重复物化。

status：
- QUEUED
- RUNNING
- DONE
- FAILED
- RETRYABLE
- NEEDS_USER
- CANCELLED

## job_steps

```text
id
job_id
attempt_id
step_name
status
progress
input_ref_json
output_ref_json
version
error_message
started_at
finished_at
```

上游步骤在新 Attempt 中被复用时，新增 Step 记录或 Attempt-Step 投影状态为 `REUSED`，不得改写旧步骤时间与输出。

## job_step_artifacts

```text
id
job_id
attempt_id
step_name
artifact_type
artifact_ref_json
input_hash
content_hash
schema_version
producer_version
status
created_at
replayable_until
invalidated_at nullable
```

`status`：`AVAILABLE / EXPIRED / INVALIDATED / MISSING`。默认 Replay Cache TTL 使用 `video_cache_ttl_hours=24`。步骤级续跑只有在所有依赖 Artifact 可用且输入/版本一致时成立；TTL 到期后由 Worker 清理文件并把状态改为 EXPIRED，持久 Source/Transcript/Note/Evidence 不属于本表的临时缓存。

## settings / secret references

非敏感设置可存 SQLite；API Key、LAN Token 与其他 Secret 只保存 macOS Keychain 引用。数据库字段包含 `setting_key/value_json/updated_at` 与 `secret_key/secret_ref/updated_at`，不得存 Secret 明文。

---

# 13. 不建议第一版建的表

- dynamic_spaces
- skill_marketplace
- agent_memory
- vector_embeddings
- cloud_workers
- tenants
- payments

它们均属于未来能力，不提前实现。
