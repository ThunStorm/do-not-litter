# PROJECT_PLAN.md
## Codex / Agent 可执行实施计划

> 项目：AI Personal Inbox / Personal Scout  
> 目标平台：二选一——Windows 11 PC 或 Mac mini（实施前设置 `DEPLOYMENT_TARGET`）
> 候选硬件 A：Ryzen 7 5800X / 32GB / RX 7900 XT 20GB
> 候选硬件 B：Apple M4 10-core / 16GB unified memory / arm64
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

# Phase 0A — Target Node Feasibility Spikes（在 Phase 0 最小 Bootstrap 后执行）

## Goal

在搭建完整业务代码前，先从 `windows_pc` 与 `mac_mini` 中选择一个 `DEPLOYMENT_TARGET`，并在该目标节点消除高风险外部依赖的不确定性。若用户需要比较两套方案，则分别运行同一套 Fixture 与记录模板，但不同时开发两套生产安装包。

## Spikes

- 手机 LAN 访问、Token-to-Session、CORS、WebSocket 与 HTTPS 可部署性；
- 微信持久 Playwright Profile 与 `NEEDS_USER`；
- HTML/PDF/扫描 PDF/DOCX/XLS/XLSX/PNG/JPEG 文档矩阵；
- 中文 OCR 定位与置信度；
- Windows：Ollama AMD 结构化输出、whisper.cpp Vulkan 时间码 ASR、Credential Manager/DPAPI、服务恢复；
- Mac mini：Ollama Metal 结构化输出、whisper.cpp Metal 时间码 ASR、Keychain、arm64 依赖和 `launchd` 服务恢复；
- DeepSeek / Xiaomi MiMo OpenAI-compatible 连接；
- 高德 POI Web 服务 / JS API 2.0 / GCJ-02；
- SQLite WAL 多进程、原子 Lease 与幂等恢复。

## Acceptance

- 每项有可复现记录与 `PASS / DEGRADED / BLOCKED` 结论；
- `BLOCKED` 项在进入依赖它的 Phase 前必须选定替代方案或调整范围；
- 性能门槛使用目标 PC 实测值回填 `GOLDEN_SAMPLES.md`。

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
- 所选平台 README 安装与启动命令可用。

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
后端节点/Worker 异常停止后任务可恢复。

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
实现所选后端节点的本地视频转录。

## Tasks
- ffmpeg detection
- whisper.cpp provider
- model management
- timestamp transcript
- 加速器诊断：Windows Vulkan / Mac Metal
- ASR mode
- cache cleanup

## Acceptance
本地视频/音频 → timestamp segments。

---

# Phase 15 — Bilibili Resolver

## Goal
B站视频进入 Travel Pipeline。

## Tasks
- metadata
- subtitle-first
- media fallback
- ASR fallback
- snapshot / transcript storage

## Acceptance
测试视频 Fixture 或真实样本可得到 Transcript。

---

# Phase 16 — Travel Extraction

## Goal
Transcript → PlaceMention / Observations。

## Tasks
- TravelFood classifier
- Place extractor
- Restaurant extractor
- dish/price/opinion/warning
- Evidence timestamp binding

## Acceptance
每个事实可回到字幕 segment。

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
- name/location matching
- confidence
- Confirmed/Review/Unresolved
- CMS POI Review
- deduplicate
- AMap JS API 2.0 map view

## Acceptance
LLM 不参与经纬度生成。
两个来源提同一家店最终可归并为一个 Place。
GeoJSON 明确携带坐标系，不把 GCJ-02 静默声明为 WGS84。

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
- MapOverviewVM：viewport、markers、clusters、filters、selected preview
- 独立地图总览页；Marker 点击切换底部预览，详情为下一级页面
- 地图路由状态恢复：viewport / zoom / filters / selected_place_id
- route_drafts / route_draft_items
- 路线清单选点与手动排序
- list view

## Acceptance
SAVE/DISMISS/VISITED 会影响后续推荐解释。
同一区域多个 Confirmed Place 可在地图总览中同时显示；依次点击 Marker 只切换地点预览，不离开地图；进入详情再返回后保留原地图状态。路线清单不伪造最优顺序、距离或交通时间。

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
- rerun from step
- versioned step output
- partial publish
- stale result invalidation
- CMS controls

## Acceptance
Travel 可在 43 个地点未全部完成时展示已确认地点。
Recruitment 可单独重跑 DSL/Major Matching。

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
- selected local node only（Windows PC 或 Mac mini）；
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
