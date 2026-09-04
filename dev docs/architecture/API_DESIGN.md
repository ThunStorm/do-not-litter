# API Design

> API 风格：REST + WebSocket
> 第一版单用户，本地使用，但仍保持明确资源边界。

---

# 1. Capture API

## POST /api/inbox

输入：

```json
{
  "value": "视频标题\nhttps://b23.tv/...\n复制打开 App"
}
```

`value` 是原始粘贴值。服务端是输入判定的权威方，不依赖前端 `startsWith("http")`。现有 `{url}` / `{text}` 字段可保持向后兼容，但都应进入同一 Input Normalizer。

唯一链接识别成功时返回：

```json
{
  "item_id": "...",
  "job_id": "...",
  "status": "QUEUED",
  "input_kind": "SHARE_TEXT_WITH_URL",
  "selected_url": "https://b23.tv/..."
}
```

存在多个无法唯一选择的内容链接时不创建处理 Job，返回 `422`：

```json
{
  "code": "CAPTURE_MULTIPLE_URLS",
  "message": "检测到多个链接，请选择要处理的内容",
  "details": {"candidates": ["https://...", "https://..."]}
}
```

选择规则：canonical 去重后仅一个候选直接使用；多个候选中仅一个命中专用 Resolver 时自动选择；仍有多个内容候选时不得静默选择第一个。选中 URL 后，周围标题/分享文案不发送给 Resolver、Classifier 或 LLM。

返回：
`202 Accepted`

```json
{
  "item_id": "...",
  "job_id": "...",
  "status": "QUEUED"
}
```

URL/Text 使用 JSON。文件使用：

`POST /api/inbox/upload`（`multipart/form-data`）

MVP 允许：

- `.pdf`
- `.docx`
- `.xls` / `.xlsx`
- `.png` / `.jpg` / `.jpeg`

上传时校验扩展名、MIME、文件头、大小上限与内容哈希；原文件写入本地永久 Source 存储，再创建统一 Job。扫描 PDF 与图片自动进入 OCR Step。

## GET /api/inbox/{id}

返回：
- input
- resolved type
- processor
- processing status
- result link

---

# 2. Recruitment API

## GET /api/recruitment/dashboard

返回 `RecruitmentDashboardVM`：

```json
{
  "nearest_deadline": {},
  "action_items": [],
  "eligibility_summary": {},
  "recommended_positions": [],
  "profile_questions": [],
  "recent_notices": []
}
```

## GET /api/recruitment/notices

支持分页与状态。

## GET /api/recruitment/positions

Filters：
- eligibility
- region
- deadline
- organization
- education
- major
- user_state

## GET /api/recruitment/positions/{id}

返回：
- position
- requirement results
- Evidence
- source graph
- deadlines
- actions

## POST /api/recruitment/positions/{id}/state

```json
{"state":"PREPARING"}
```

## GET /api/recruitment/questions

返回按 Information Gain 排序的待补充 Profile。

## POST /api/recruitment/questions/{id}/answer

更新 profile 后触发增量匹配。

---

# 3. Travel API

## Video Note API

```text
GET  /api/video-notes
GET  /api/video-notes/{note_id}
GET  /api/video-notes/{note_id}/transcript
GET  /api/video-notes/{note_id}/transcript/export
GET  /api/video-notes/{note_id}/places
GET  /api/video-notes/{note_id}/screenshots
POST /api/video-notes/{note_id}/regenerate
DELETE /api/video-notes/{note_id}
GET  /api/video-covers/{cover_id}/image
```

`GET /api/video-notes` 的每项增加 `cover_status/cover_image_url/cover_width/cover_height/cover_error`。READY 时必须返回本地受控图片 API URL；非 READY 使用统一占位，不能把远程 CDN URL 当成已下载封面。

`GET /api/video-covers/{cover_id}/image` 只读取数据库已登记的 CoverAsset 路径，返回正确 Content-Type、内容哈希 ETag 和 immutable Cache-Control；禁止接受任意文件路径或代理任意 URL。

`DELETE /api/video-notes/{note_id}` 由列表和详情共用。删除 Note/Version/Section/TOC/Content 投影，保留 Source、VideoAsset、CoverAsset、Transcript、Place 和 Evidence；活跃生成 Job 返回 409。完整契约见 `video/VIDEO_NOTE_DELETE_V044_SPEC.md`。

`GET /api/video-notes/{note_id}` 返回当前 Note Version、视频页元数据、封面、摘要、主旨目录 `toc[]`、按时间线详述章节、地点引用和文稿校对状态；代表性截图仍由独立的 `GET /api/video-notes/{note_id}/screenshots` 返回，前端按 `section_id` 随文嵌入，避免详情首屏传输图片数据。`regenerate` 创建新版本，不覆盖旧版本。

Video Note Detail ViewModel 的默认页面顺序为 Hero → 摘要 → 目录 → 时间线详述 → 地点候选/完整转写。Hero 返回 cover_status/local cover URL；非 READY 时前端收起封面区域，不返回场记板占位。`toc[]` 至少返回 `section_id/start_ms/heading/thesis`；Section 返回 `summary/bullets/place_refs/anchor_id`，Screenshot 返回 `section_id/caption/selection_reason/target_section_id`。

详情响应同时返回 `transcript_status`（`AVAILABLE / EXPIRED / NOT_READY`）、`transcript_correction_status`、`transcript_correction_provider/model`、`transcript_segment_count`、`transcript_retention_until`、`screenshot_status`（`PLANNING / READY / PARTIAL / UNAVAILABLE`）和脱敏 `screenshot_error`。空截图列表必须可区分“尚在规划”“计划为空”和“下载/抽帧失败”。

`GET .../transcript` 在可用期返回全部 Segment 的 `raw_text/corrected_text/start_ms/end_ms/target_section_id`；默认页面使用 corrected_text，raw 只在证据审计入口展示。导出支持：

```text
GET /api/video-notes/{note_id}/transcript/export?version=corrected
GET /api/video-notes/{note_id}/transcript/export?version=raw
```

默认 corrected，返回 `text/plain; charset=utf-8` 与安全的附件文件名，逐行输出完整 AI 校对稿、时间码、校对模型和生成时间；raw 仅由证据/审计入口调用。导出即时生成且不在服务端落第二份文件。文稿满 180 天清理后两个 Transcript 接口返回 `410 Gone`，Note 详情、时间线章节和截图仍可读取。

## Prompt Supplements API v0.4.5

```text
GET /api/settings/prompt-supplements
PUT /api/settings/prompt-supplements
```

API 只允许读写三个低优先级补充文本：`transcript_correction`、`video_note_summary`、`travel_place_extraction`。响应附带不可编辑的 `core_contracts` 摘要、`max_length=1000` 与哈希；固定核心 Prompt 正文不通过 API 返回。PUT 在服务端拒绝修改/覆盖 JSON、Schema、字段、键名、ID 或顺序的越权语言，并将变更写入审计事件。完整边界见 `ai-gateway/PROMPT_SUPPLEMENTS_V045_SPEC.md`。

## 转写路由、参数与来源清理 API v0.4.6

`GET/PUT /api/settings/model-routing` 在通用 `primary_id/fallback_id` 之外返回可空的 `transcript_primary_id/transcript_fallback_id`；转写专属值优先，空值继承通用对应项。`GET/PUT /api/settings/transcript-processing` 管理 `chunk_chars/batch_size/timeout_seconds`，缺省为 `12000/128/180` 并执行数值范围校验。

`GET /api/sources/{id}` 返回 `deletion.allowed/content_count/video_note_count/active_job_count`。`DELETE /api/sources/{id}` 只删除孤立来源；仍有关联业务内容或活跃 Job 时返回 409。删除最后一个内容或视频笔记后，服务端自动执行同一孤立判断并按需清理来源。

地点候选、Transcript Segment、目录和截图 ViewModel 都返回 `target_section_id`。页面内时间码使用稳定 `anchor_id` 跳转对应 Section；“打开原片”使用独立外链字段，不能与页面内跳转混用。

`note_id` 的规范值为 `AINote.id`（`note_*`），`AINoteVersion.id`（`ntv_*`）只表示一次版本快照，不能写入内容页入口。为兼容已生成内容和旧书签，共享 Note 查询器可把历史 `ntv_*` 解析到所属 `AINote`，但响应和后续写入必须返回规范 `note_*`。未知 ID 返回 404；前端必须展示错误与重试/返回入口，不能把 error 状态继续渲染为 loading。

当前实现使用统一 `POST /api/capture`（文件为 `/api/capture/file`）投递；长期 `/api/inbox` 命名保留为兼容演进方向。响应只确认入队；字幕获取、媒体下载、ASR、总结和 POI 解析全部由 Worker 完成。

## GET /api/travel/dashboard

```json
{
  "days_since_last_trip": 63,
  "map_places": [],
  "recent_discoveries": [],
  "recommended_places": [],
  "pending_reviews": 0
}
```

## GET /api/travel/places

Filters：
- city
- place_type
- user_state
- origin
- query

`source`、偏好打分和复杂状态组合属于后续查询增强；当前通过 `/sources`、地点详情和用户状态分别下钻，避免在单机 SQLite 上预先构建不可用的大型筛选索引。

## GET /api/travel/places/{id}

返回：
- 地点预览、坐标系、坐标、POI Provider 与元数据；
- 观察摘要；
- 详细来源/时间码由 `/api/travel/places/{id}/sources` 返回；
- 地点归纳笔记与其 Evidence 数由 `/api/travel/places/{id}/note` 返回。

## GET /api/travel/places/{id}/note

返回地点归纳笔记、当前版本、来源冲突、Observation 摘要和 Evidence 引用。

## GET /api/travel/places/{id}/sources

返回提到该地点的视频/图文来源、Note、Mention、时间码和原片跳转信息。

## GET /api/travel/map

参数：

- `bbox=min_lng,min_lat,max_lng,max_lat`；
- `zoom`；
- `place_type`；
- `user_state`；
- `origin`；
- `query`；
- `selected_place_id`。

首次进入由前端使用中国大陆全境 viewport；API 不提供默认城市。全国尺度返回 clusters，放大后返回 Marker。响应保存当前 viewport、总数、可见数、聚合和 selected preview。

地点列表、视频笔记中的地点链接和地图 Marker 必须使用同一 `place_id`。Marker 返回：

```text
marker_id
place_id
origin
visibility
canonical_name
place_type
latitude / longitude
address
preview_image
brief
key_observations
source_count
user_state
```

完整归纳笔记统一从 Place Detail/Note API 获取。

## GET /api/travel/map/bootstrap

返回受认证用户加载高德 JS 所需的 JS Key、Security Code、配置状态、默认中国大陆 viewport 和 Provider 诊断。不得返回高德 Web 服务 Key。

## POST /api/travel/map/markers

当前实现支持用户点选坐标与 `longitude/latitude + custom_name`，生成 `USER_CONFIRMED` Place 并返回 `marker_id + place_id`。高德搜索候选直接创建属于后续增强；已由视频链路确认的 POI 仍通过 `RESOLVE_POI` 生成 Provider-confirmed Place。

## DELETE /api/travel/map/markers/{marker_id}

用户 Marker 软删除；自动 Marker 只隐藏地图投影。不得级联删除 Source、Claim、Evidence、PlaceMention 或 Place Note。

## POST /api/travel/map/markers/{marker_id}/restore

恢复软删除/隐藏 Marker。

## POST /api/travel/places/{id}/save
## POST /api/travel/places/{id}/dismiss
## POST /api/travel/places/{id}/visited

写入用户地点状态与可审计事件；独立 PreferenceEvent / VisitEvent 领域模型属于后续增强。

## POST /api/travel/export

格式：
- csv
- json
- geojson

当前以 `POST /api/travel/export?format=csv|json|geojson` 提供。GeoJSON 顶层及每个 Feature 的属性均明确标注 `GCJ02`；只导出当前可见 Marker 投影，不导出已隐藏/软删除的投影。

---

# 4. Control Center API

当前任务控制接口为：

```text
GET  /api/jobs/{job_id}
GET  /api/jobs/{job_id}/replay-options
POST /api/jobs/{job_id}/retry-from-step
POST /api/jobs/{job_id}/retry-full
POST /api/jobs/{job_id}/cancel
```

`GET replay-options` 由服务端根据失败步骤、Artifact Manifest、输入哈希和 TTL 返回：可否步骤续跑、replay_from_step、复用步骤、需重跑步骤、replayable_until 和不可用原因。

`POST retry-from-step`：

```json
{
  "step_name": "GENERATE_AI_NOTE",
  "source_event_id": "evt_..."
}
```

服务端只接受与 Replay Options 一致的失败步骤，不允许前端任意指定 from_step。新 Attempt 复用之前 COMPLETED 且 Artifact 有效的步骤，将它们标记为 REUSED；失败步骤和所有下游步骤重新执行。下游旧输出 INVALIDATED，新版本不覆盖旧版本。

Artifact 已过期/缺失、输入变化、活跃 lease、事件归属不匹配或已有 replay 时返回 409 和稳定 `REPLAY_*` code。`retry-full` 是独立动作，从首步骤创建新的完整 Job；原 Job 正在运行时先请求取消旧流程。响应返回 `job_id / replaced_job_id / stopped_active_job`，客户端导航到新 Job。完整契约见 `jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md`。

`replay-options` 还返回 `full_replay_available / full_replay_reason`。完整重跑在所有状态可提交；运行态 reason 明确提示“将停止当前流程并创建新的完整任务”。步骤恢复卡不重复放置完整重跑按钮。

## GET /api/admin/dashboard
## GET /api/admin/jobs
## GET /api/admin/jobs/{id}

## GET /api/admin/jobs/{id}/replay-options
## POST /api/admin/jobs/{id}/retry-from-step
## POST /api/admin/jobs/{id}/retry-full
## POST /api/admin/jobs/{id}/cancel

## POST /api/admin/jobs/{id}/rerun-external

显式使用外部模型。

## GET /api/admin/sources/{id}
## GET /api/admin/sources/{id}/graph

## GET /api/admin/poi/review
## POST /api/admin/poi/{id}/confirm
## POST /api/admin/poi/{id}/reject

## GET /api/admin/settings
## PUT /api/admin/settings

地图设置至少包括：

```text
amap_js_key
amap_security_code
amap_web_service_key
```

提供独立真实测试，分别报告 JS 配置、Web 服务搜索和域名白名单提示。Web 服务 Key 不回传明文；Security Code 只通过地图 bootstrap 提供给已认证客户端。

---

# 5. WebSocket

## WS /api/ws/jobs

消息：

```json
{
  "job_id":"...",
  "status":"RUNNING",
  "step":"ASR",
  "progress":62,
  "message":"..."
}
```

前端断线后重新连接，再通过 REST 重新取状态，不能只依赖 WS。

---

# 6. ViewModel 原则

API 返回给产品前端的是 ViewModel，而不是 ORM Row。

原因：
- 防止 UI 绑定数据库；
- 支持未来小程序/移动 App；
- 数据库可演进；
- 保持业务语义。

---

# 7. 错误响应

统一错误：

```json
{
  "code":"POI_NEEDS_REVIEW",
  "message":"...",
  "details": {}
}
```

错误 code 必须稳定，不直接依赖异常类名。

---

# 8. 单用户认证

第一版必须支持手机局域网访问，因此认证不是可选项：

- localhost 与 LAN UI 使用同一 API；
- 手机首次配对通过 `POST /api/auth/session` 在请求体提交访问 Token，服务端换发短期 HttpOnly、SameSite Session Cookie；
- 后续 REST 与 WebSocket 握手统一验证 Session Cookie；脚本型客户端可使用 `Authorization: Bearer <access-token>`；
- Token 由 Mac mini 生成、存入 macOS Keychain，并支持轮换；
- CORS 使用明确 Origin allowlist；
- 长期 Token 不放在查询字符串、localStorage 或普通日志中；
- 未授权请求统一返回稳定错误码 `AUTH_REQUIRED` / `AUTH_INVALID`。

未来远程访问再引入完整认证。
