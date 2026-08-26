# PROJECT_PLAN.md
## Codex / Agent 可执行实施计划

> 项目：AI Personal Inbox / Personal Scout  
> 目标平台：Mac mini（macOS arm64）
> 当前硬件：Apple M4 / 16GB 统一内存 / Metal
> 当前范围：Recruitment + Travel/Food  
> 架构：FastAPI + React/TS/Vite + SQLite + Worker + Playwright + Ollama/External LLM + whisper.cpp  
> 原则：产品做窄，内核留宽

---

# 0. Agent 总体执行规则

Agent 在实现过程中必须：

1. 先阅读本目录所有设计文档。
2. 不得自行把 MVP 扩成通用 Agent 平台。
3. 所有长任务必须走 Job。
4. 所有事实性 Claim 必须有 Evidence。
5. 不得在 Processor 内直接调用具体 LLM SDK。
6. 不得用 LLM 代替确定性 Rule Engine。
7. 不得让 LLM 生成 POI 经纬度。
8. 所有数据库变更必须 Alembic migration。
9. 所有核心模块必须有测试。
10. 每完成一个 Phase 更新实现状态文档或 checklist。

真实样本、Fixture 规则和初始质量门槛见 `GOLDEN_SAMPLES.md`。

---

# Phase 0A — Mac mini Feasibility Spikes（在 Phase 0 最小 Bootstrap 后执行）

## Goal

在搭建完整业务代码前，用目标 Mac mini / Metal 主机消除高风险外部依赖的不确定性。

## Spikes

- 手机 LAN 访问、Token-to-Session、CORS、WebSocket 与 HTTPS 可部署性；
- 微信持久 Playwright Profile 与 `NEEDS_USER`；
- HTML/PDF/扫描 PDF/DOCX/XLS/XLSX/PNG/JPEG 文档矩阵；
- 中文 OCR 定位与置信度；
- Ollama Metal 结构化输出；
- whisper.cpp Metal 时间码 ASR；
- DeepSeek / Xiaomi MiMo OpenAI-compatible 连接；
- 高德 POI Web 服务 / JS API 2.0 / GCJ-02；
- SQLite WAL 多进程、原子 Lease 与幂等恢复。

## Acceptance

- 每项有可复现记录与 `PASS / DEGRADED / BLOCKED` 结论；
- `BLOCKED` 项在进入依赖它的 Phase 前必须选定替代方案或调整范围；
- 性能门槛使用 Mac mini 实测值回填 `GOLDEN_SAMPLES.md`。

---

# Phase 0 — Repository Bootstrap

## Goal
建立可运行 Monorepo。

## Tasks

### P0.1
创建：

```text
/backend
/frontend
/docs
/scripts
/data.example
```

### P0.2
Backend：
- Python 3.12+
- pyproject.toml
- FastAPI
- Uvicorn
- SQLAlchemy
- Alembic
- Pydantic
- aiosqlite/httpx

### P0.3
Frontend：
- React
- TypeScript
- Vite
- Node.js 20.19+ 或 22.12+

### P0.4
.gitignore：
- data/
- .env
- browser profile
- model cache
- logs

### P0.5
基础健康接口：
`GET /api/health`

### P0.6
LAN 安全基线：
- 可配置 bind address / port；
- 首次生成访问 Token；
- REST / WebSocket 鉴权；
- Origin allowlist；
- 默认不做公网暴露。

## Acceptance
- backend 启动；
- frontend 启动；
- health 正常；
- 手机在同一局域网携带 Token 可访问，未授权请求被拒绝；
- Mac mini launchd 安装、状态与重启命令可用。

---

# Phase 1 — Database & Core Domain

## Goal
落地核心数据库与 Repository。

## Tasks

### P1.1
数据库配置：
- SQLite
- WAL
- foreign_keys

### P1.2
Alembic 初始化。

### P1.3
实现：
- content_items
- sources
- source_snapshots
- source_relations
- segments
- claims
- claim_evidences
- claim_relations
- jobs
- job_steps
- settings / secret references

### P1.4
Repository 层。

### P1.5
Pydantic Domain Models。

### P1.6
Evidence Integrity 校验。

## Tests
- CRUD
- FK
- orphan Claim validation
- migration up/down（合理范围）

## Acceptance
创建 Source → Snapshot → Segment → Claim → Evidence 可完整回读。

---

# Phase 2 — Job Runtime

## Goal
实现持久后台任务。

## Tasks

### P2.1
Job 状态机。

### P2.2
Worker Process。

### P2.3
Lease + heartbeat。

### P2.4
stale RUNNING recovery。

### P2.5
JobStep。

### P2.6
REST：
- list
- retry
- cancel
- rerun

### P2.7
WebSocket progress。

## Tests
- worker crash
- lease expire
- retry
- cancel
- recovery

## Acceptance
PC/Worker 异常停止后任务可恢复。

---

# Phase 3 — Control Center Skeleton

## Goal
用户可以看到系统运行。

## Pages
- Dashboard
- Tasks
- Sources
- Settings

## Tasks
- Job list
- Job detail
- step progress
- retry/cancel
- WS updates
- settings storage

## Acceptance
创建 mock 长任务可实时看 0→100%。

---

# Phase 4 — LLM Provider Layer

## Goal
建立厂商无关 AI 层。

## Tasks

### P4.1
LLMProvider base。

### P4.2
OllamaProvider。

### P4.3
OpenAIProvider。

### P4.4
OpenAICompatibleProvider。

### P4.5
MockProvider。

### P4.6
LLM Router。

策略：
- LOCAL_ONLY
- LOCAL_FIRST
- CLOUD_FIRST
- MANUAL

### P4.7
Structured Output + Pydantic Validation。

### P4.8
Prompt/model/parser version logging。

### P4.9
API Key secret storage abstraction。

## Tests
- provider switching
- local failure → cloud fallback
- invalid JSON retry
- Evidence reference validation

## Acceptance
同一个业务抽取接口可在不改 Processor 的情况下切换 Provider。

---

# Phase 5 — Resolver Core

## Goal
建立统一 ResolvedContent。

## Tasks

### P5.1
Resolver base + registry。

### P5.2
WebResolver。

### P5.3
Snapshot 存储。

### P5.4
HTML → normalized text/segments。

### P5.5
outgoing links。

### P5.6
Document Resolver base。

## Acceptance
普通网页 URL → Source/Snapshot/Segments。

---

# Phase 6 — Playwright / WeChat Resolver

## Goal
支持真实公众号入口与登录态。

## Tasks

### P6.1
Playwright setup。

### P6.2
独立 browser profile。

### P6.3
WechatResolver：
- HTTP
- browser fallback
- NEEDS_USER

### P6.4
Link Discovery。

### P6.5
depth / children limit。

### P6.6
Source Graph。

## Tests
使用保存的 HTML Fixture，不让 CI 依赖真实微信。

## Acceptance
给定微信 Fixture 可发现官方链接/附件并建立 SourceRelation。

---

# Phase 7 — PDF / Excel Normalizer

## Goal
支持招聘附件与扫描材料。

## Excel Tasks
- `.xlsx` openpyxl reader
- `.xls` legacy reader adapter（Phase 0A 选型）
- sheet detect
- header detect
- merged cell recovery
- normalized table
- AI column mapping

## PDF Tasks
- page segments
- text blocks
- locator

## DOCX Tasks
- paragraph / table normalization
- paragraph/run locator
- embedded attachment/image discovery

## OCR Tasks
- scanned PDF detection
- PNG/JPEG input
- Chinese OCR provider abstraction
- page/bbox/confidence locator
- low-confidence Review policy

## Acceptance
岗位表 Fixture 可转换为标准 rows，保留原 Cell 定位；DOCX/PDF/OCR 文本均可回到原页、段落或边界框，低置信关键事实不自动确定。

---

# Phase 8 — Recruitment Schema

## Goal
创建招聘领域模型。

## Tables
- recruitment_notices
- positions
- requirements
- requirement_matches
- position_matches
- profile_fields
- education_experiences
- deadlines
- todos
- major catalogs（最小实现）

## Acceptance
Notice + 100 Position 可存取。

---

# Phase 9 — Requirement DSL & Rule Engine

## Goal
实现可测试资格逻辑。

## Tasks
- AST Pydantic
- ALL
- ANY
- NOT
- CONDITION
- HARD
- SEMANTIC
- PREFERENCE
- PASS/FAIL/UNKNOWN/REVIEW propagation

## Tests
必须覆盖所有组合。

## Acceptance
Rule Engine 完全不依赖 LLM。

---

# Phase 10 — Recruitment Extraction

## Goal
公告/岗位 → DSL。

## Tasks
- Notice extractor
- Position extractor
- Requirement parser
- Evidence binding
- schema validation
- retry policy

## Acceptance
Fixture 招聘完整得到 Typed Result + Evidence。

---

# Phase 11 — MajorMatcher

## Goal
实现专业匹配。

## Tasks
- MajorCatalog schema
- ExactCodeMatcher
- ExactNameMatcher
- CategoryMatcher
- OfficialMappingMatcher
- SemanticMatcher
- REVIEW policy

## Acceptance
Semantic similarity 永远不会自动 PASS。

---

# Phase 12 — Profile Matching & Information Gain

## Goal
用户 Profile 参与岗位筛选。

## Tasks
- profile CRUD
- education experiences
- match recomputation
- Missing Profile Analyzer
- Information Gain
- incremental recalculation

## Acceptance
修改一个 Profile 字段不会重新 Resolve Source，只重跑 Match。

---

# Phase 13 — Recruitment Deadline / Todo / UI

## Goal
招聘产品可用。

## Tasks
- deadline generation
- todo FACT_BASED / SYSTEM_SUGGESTED
- urgency
- preference
- user state
- time conflict
- RecruitmentDashboardVM
- PositionDetailVM
- React pages

## Acceptance
用户可以从首页：
- 看到最近截止；
- 看到 PASS；
- 看到 UNKNOWN；
- 回答 profile question；
- 查看 Evidence；
- 标记 PREPARING/APPLIED/DROPPED。

---

# Phase 14 — ASR Runtime

## Goal
实现 Mac mini Metal 本地视频转录。

## Tasks
- ffmpeg detection
- whisper.cpp provider
- model management
- timestamp transcript
- GPU diagnostic
- ASR mode
- cache cleanup

## Acceptance
本地视频/音频 → timestamp segments。

---

# Phase 14A — Capture Input Normalization

## Goal
完整分享文案 → 唯一 URL 或明确多链接歧义。

## Tasks
- `URL_ONLY / SHARE_TEXT_WITH_URL / TEXT_ONLY / MULTIPLE_URLS`；
- URL/Markdown/尖括号/中文标点/零宽字符提取；
- canonical 去重和专用 Resolver 唯一命中；
- 选中 URL 后丢弃周围标题/分享话术，不进入 Resolver/LLM；
- `CAPTURE_MULTIPLE_URLS` 候选响应；
- raw input hash 与最小审计字段；
- 前端提交原始粘贴值，后端权威判定。

## Acceptance
标题+链接分享文案与纯链接进入同一 URL Pipeline；普通正文保持 TEXT_ONLY；多内容链接不静默选第一个且不创建 Job。

---

# Phase 15 — Bilibili Resolver

> Phase 15–18 的实施必须同时遵循 `VIDEO_AI_NOTE_PIPELINE.md` 与 `VIDEO_AI_NOTE_IMPLEMENTATION_GUIDE.md`，按指南中的 Work Package 拆分提交，不得一次性重写 Pipeline 或提前实现未确认 UI。

## Goal
B站视频进入 Travel Pipeline。

## Tasks
- 建立 BiliNote MIT 第三方声明与上游 revision 记录；
- 移植/适配 URL 校验、短链、BV ID、分 P 和 CID 解析；
- metadata-only 解析；
- Bilibili player API 字幕优先与字幕轨选择；
- yt-dlp 字幕和音频 fallback；
- Cookie/代理/412/429/登录态错误映射；
- ASR fallback；
- timestamp Transcript、Snapshot 和缓存存储；
- 持久 JobStep、幂等、恢复和单步重跑。

## Acceptance
测试视频 Fixture 或真实样本可得到 Transcript；有字幕时不下载音频，无字幕时自动 ASR；分 P 的字幕、元数据和时间跳转属于同一集。详细标准见 `VIDEO_AI_NOTE_PIPELINE.md`。

---

# Phase 15A — DeepSeek Video AI Note

## Goal
Transcript → 版本化 AI 视频笔记。

## Tasks
- `VIDEO_NOTE_SUMMARY` Provider Role，默认使用已配置 DeepSeek；
- 长 Transcript 分块预算；
- 局部总结、checkpoint 和层级合并；
- Markdown + structured sections；
- Segment/timecode binding；
- Note Version、缓存、重跑和历史版本；
- Provider/Model/Prompt/Chunker 审计。

## Acceptance
长视频可生成完整中文 AI 笔记；失败后从 checkpoint 继续；重跑不覆盖旧版本；章节可回到 Transcript 时间码。

---

# Phase 15B — Representative Screenshots

## Goal
为 AI Note 章节与地点生成可追溯代表性截图。

## Tasks
- Screenshot Plan：Section/PlaceMention/Segment 时间码；
- 受限画质视频下载与缓存；
- FFmpeg 抽帧；
- 黑帧、模糊、曝光与感知重复检测；
- VideoScreenshot 数据模型与 API；
- 每地点 1–3 张、全文默认 3–12 张；
- 下载不可用时 `PARTIAL_SUCCESS`。

## Acceptance
截图具有实际时间码、文件哈希和来源关系；重复/无效帧不进入 Note；失败不阻塞已完成笔记。

---

# Phase 15C — Transcript Correction

## Goal
raw Transcript → 时间码不变、可审计的 AI 校对稿。

## Tasks
- `CORRECT_TRANSCRIPT / VALIDATE_CORRECTION`；
- raw_text / corrected_text / status / provider / model / prompt version；
- 固定 Segment 分块和全覆盖校验；
- 口音、同音字、断句、重复词、地名/菜名/专有名词校对；
- 不确定内容 Review，不新增事实；
- corrected/raw 预览与 TXT 导出。

## Acceptance
全部 Segment ID、顺序和时间码不变；默认 Note/预览/导出使用 corrected_text；模型不可用时不伪装完成。

---

# Phase 15D — Video Note Reading Experience

## Goal
重构视频详情的信息顺序、目录、段落跳转、随文截图和灯箱。

## Tasks
- Hero CoverAsset/缺省空状态；地点候选 + 完整转写放文章底部；
- 具体 heading/thesis 目录与稳定 Section 锚点；
- 时间码本地跳转、聚焦、高亮与历史恢复；
- summary/bullets/place refs 的时间线详述；
- 截图重新选取并以侧排缩略图嵌入 Section；
- contain Lightbox、切换、Escape/遮罩关闭；
- 统一“导出 TXT”按钮；
- PC/Mobile/键盘回归。

## Acceptance
完整执行 `VIDEO_NOTE_READING_EXPERIENCE_V042_SPEC.md` 第 10 节，不得以独立截图宫格或原始转录堆叠代替。

---

# Phase 15E — Video Note List Cover & CTA

## Goal
列表展示真实本地封面，并统一顶部添加按钮。

## Tasks
- 主按钮文案“添加视频链接”和 40px/14px Button Token；
- VideoAsset.cover_url HTTPS 规范化；
- Bilibili 图片 CDN allowlist、MIME/文件头/尺寸/字节校验；
- 原始封面 SHA-256 存储与 672×378 WebP；
- CoverAsset、`FETCH_COVER`、本地图片 API；
- Video Note List cover ViewModel；
- 16:9、object-fit cover、lazy loading、时长徽标、skeleton 和失败占位；
- PC/Mobile/安全/缓存回归。

## Acceptance
完整执行 `VIDEO_NOTE_LIST_V043_SPEC.md` 第 9 节；封面失败不得阻塞 Note，不得长期热链远程 CDN。

---

# Phase 15F — Video Note Delete

## Goal
在列表和详情安全删除视频笔记，不破坏共享数据。

## Tasks
- 列表/详情 `…` 菜单；
- 共用 `DELETE /api/video-notes/{note_id}`；
- 删除 AINote/Version/Section/TOC/Content 投影；
- 保留 Source/VideoAsset/Transcript/Place/Evidence/Cover；
- 清理无共享引用的 Note 专属截图；
- 活跃 Job 409 门禁；
- 标题/保留边界/不可恢复确认；
- 缓存刷新、旧链接已删除状态和审计。

## Acceptance
完整执行 `VIDEO_NOTE_DELETE_V044_SPEC.md`，列表和详情入口使用同一 Service。

---

# Phase 16 — Travel Extraction

## Goal
Transcript → PlaceMention / Observations。

## Tasks
- TravelFood classifier
- Place extractor
- Restaurant extractor
- scenic area / neighborhood / pedestrian street / business district / market extractor
- PlaceBrief：景区/街区特色、菜品、价格、排队、适合人群、warning
- Evidence timestamp binding
- Place Note Builder 与版本化地点归纳笔记

## Acceptance
每个事实可回到字幕 segment；餐馆、景区、街区等粒度可区分；同一 Place 可聚合多个视频来源并生成带冲突与来源时间码的归纳笔记。

---

# Phase 17 — POI Provider & Resolution

## Goal
PlaceMention → Place。

## Tasks
- POIProvider base
- AMapPOIProvider
- AMap Web Service Key / quota error handling
- GCJ-02 coordinate metadata
- candidate search
- raw_name / canonical_name / aliases
- 同音错字、简称、名称和 location matching
- confidence
- Confirmed/Review/Unresolved
- CMS POI Review
- deduplicate
- AMap JS API 2.0 map view
- 高德 JS Key / Security Code / Web 服务 Key 设置与测试

## Acceptance
LLM 不参与经纬度生成。
两个来源提同一家店最终可归并为一个 Place。
GeoJSON 明确携带坐标系，不把 GCJ-02 静默声明为 WGS84。
转写名称校正后仍保留 raw_name；歧义名称进入 Review。

---

# Phase 18 — Preference & Travel UI

## Goal
实现个性化地图与列表。

## Tasks
- preference_events
- preferences
- trait extraction
- simple scoring
- explanation
- place state
- VisitEvent
- days_since_last_trip
- TravelDashboardVM
- 中国大陆全境 map view，无默认城市
- bbox/zoom query、cluster 和 viewport restore
- Marker popup / mobile sheet
- user marker add/hide/soft-delete/restore
- list view

## Acceptance
SAVE/DISMISS/VISITED 会影响后续推荐解释。
首次地图请求不携带默认城市；Marker 浮窗可看简介并进入统一详情；用户 Marker 生命周期与自动 Marker 隐藏语义通过验收。

---

# Phase 19 — Export

## Goal
批量导出。

## Formats
- CSV
- JSON
- GeoJSON

## Acceptance
导出包含 source URL / timestamp / user state。

---

# Phase 20 — Replay / Partial Materialization

## Goal
实现长任务体验。

## Tasks
- Step Artifact Manifest 与默认 24h Replay Cache
- `GET replay-options`
- `POST retry-from-step`：失败步骤及下游顺次执行
- 上游步骤 REUSED、下游旧输出 INVALIDATED
- TTL 到期后禁用步骤续跑，只允许完整重跑
- 任务详情/日志“从错误步骤继续”与剩余时间
- 完整重跑独立 API/按钮
- versioned attempt/step output
- partial publish
- stale result invalidation
- CMS controls

## Acceptance
Travel 可在 43 个地点未全部完成时展示已确认地点。
Recruitment 可单独重跑 DSL/Major Matching。
ERROR 步骤在 Artifact 有效期内只重跑当前及下游；上游不产生新外部调用。完整执行 `PIPELINE_STEP_REPLAY_V044_SPEC.md`。

---

# Phase 21 — Hardening

## Goal
可日常使用。

## Tasks
- error taxonomy
- logs
- secret masking
- cache manager
- browser profile safety
- backup/export
- diagnostics
- startup script
- production build
- install documentation

## Acceptance
新机器可按文档部署；重启不丢数据；错误可定位。

---

# Phase 22 — Desktop Packaging（可选，MVP 后）

Tauri 或其他薄壳：
- launcher
- backend sidecar
- worker sidecar
- UI

不是业务 MVP 前置条件。

---

# 23. Future-only Interfaces

当前只定义接口，不实现完整功能：

- GenericProcessor
- SourceWatch
- CloudWorker
- ExecutionRouter
- VisionProvider
- MobileShare
- AutoActionExecutor

禁止 Agent 在 MVP Phase 擅自实现。

---

# 24. 最终 MVP Definition of Done

### Recruitment
- 真实招聘来源可解析；
- 官方附件可下钻；
- Excel 岗位可读取；
- DSL；
- MajorMatcher；
- Profile；
- PASS/FAIL/UNKNOWN/REVIEW；
- Deadline/Todo；
- Evidence。

### Travel
- Bilibili；
- Subtitle/ASR；
- PlaceMention；
- POI；
- Map；
- Preference；
- Evidence；
- Export。

### Platform
- PC only；
- Job recovery；
- Control Center；
- Ollama；
- external API；
- replay；
- secure settings；
- local data。

---

# 25. 建议 Agent 实施顺序

按 Phase 0 → Phase 0A → Phase 1–13 完成 Recruitment，
再 14 → 19 完成 Travel，
之后 20 → 21 做系统化完善。

原因：
Recruitment 覆盖 Evidence/DSL/Profile/Rule Engine，
它跑通后 Travel 只新增 ASR/POI/Preference 特有能力。

---

# 26. Agent 每阶段输出

每个 Phase 应输出：

```text
完成内容
涉及文件
数据库迁移
新增 API
新增测试
运行命令
验收结果
未完成/风险
下一 Phase
```

不要只报告“代码已完成”。
