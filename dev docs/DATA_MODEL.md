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
status
processor_hint
created_at
updated_at
```

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
locator_json
metadata_json
```

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

## places

```text
id
name
place_type
country
province
city
district
address
latitude
longitude

external_provider
external_poi_id

resolution_status
metadata_json
created_at
```

resolution_status:
- CANDIDATE
- CONFIRMED
- REVIEW
- REJECTED

## place_mentions

```text
id
source_id
segment_id
raw_name
place_type
city_hint
district_hint
resolved_place_id
resolution_confidence
status
metadata_json
```

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
error_code
error_message

created_at
started_at
finished_at
```

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
