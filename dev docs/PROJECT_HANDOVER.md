# 至简项目交接说明书

> 交接基线：2026-08-26 代码、文档、在线服务与本地数据只读核验结果
> 项目目录：`/Volumes/D/Projects/Codework/Git/do-not-litter`
> 当前分支：`codex/mac-mini-implementation`
> 当前 HEAD：`f882201b05661f868b61f66c2bcb81ec0be418a8`（2026-08-20）
> 重要说明：HEAD 之后存在大量未提交实现与文档；交接基线是当前工作区，不是该 Git commit。

## 1. 项目定位与整体现状

### 1.1 产品定位

“至简”是单用户、本地优先的个人信息处理系统。用户从 PC 或手机浏览器投递链接、正文和文件，Mac mini 后端执行解析、OCR/ASR、AI 结构化、证据绑定和结果物化，当前聚焦：

- 北京市公务员、事业单位等招聘信息；
- 中国大陆旅行、探店和视频 AI 笔记；
- 结构化内容、任务、来源、证据、地点、地图、路线和本机运维管理。

产品不属于通用 Agent 平台、SaaS、多租户系统或公网服务。未来 GenericProcessor、云控制面、多 Worker、自动报名等只在路线图中预留，未纳入当前交付。

### 1.2 运行形态

- Mac mini 是唯一支持的后端节点；PC/手机是同一 React Web 客户端；
- API 与 Worker 由用户级 launchd 服务 `cn.zhijian.api`、`cn.zhijian.worker` 常驻；
- FastAPI 同源提供生产前端、REST、WebSocket 和受控本地图片资源；
- SQLite/WAL 与永久文件均位于 `data/`；不使用 Redis、Celery、PostgreSQL、消息队列或云业务数据库；
- 手机通过可信局域网访问，4 位配对码换取 HttpOnly Session；默认不支持公网直接暴露。

### 1.3 当前成熟度与版本状态

当前是“功能较完整、真实单机运行、仍处于快速迭代和工程治理前”的本地 MVP/内部可用版本，不是稳定发布基线：

- 文档版本：v0.4.5；后端/前端包版本仍为 0.2.0/0.1.0，尚未统一版本语义；
- 数据库迁移：`0007` head；SQLite `integrity_check=ok`，journal mode 为 WAL；
- 在线服务：API、Worker、SQLite 均为 RUNNING；运行主机为 Apple M4/16 GB/arm64；
- 自动验证：后端 pytest 51 项、Ruff 通过；前端 Vitest 10 项、ESLint、TypeScript、Vite build 通过；
- 当前数据快照：28 张业务表、36 个 Source、7 个 VideoAsset、1 个 Video Note、8 个 Place、464 条审计事件、16 个 AVAILABLE Step Artifact；
- 当前磁盘量级：数据库约 4.1 MB、永久文件约 14 MB、可再生缓存约 103 MB、日志约 40 MB、模型约 141 MB；
- 当前工作树约有百余个修改/未跟踪文件，绝大多数 v0.4–v0.4.5 实现尚未形成可回退 commit/tag，这是首要交付风险。

### 1.4 已实施范围

- 输入：URL、分享文案唯一 URL、正文、DOCX、PDF、XLSX/XLSM、图片、音频、视频；
- 文档：PDF/DOCX/XLSX 解析、macOS Vision OCR、FFmpeg 归一化；
- 招聘：基础分类、公告字段、岗位/条件、档案、Evidence、截止时间与待办基础视图；
- 视频：Bilibili BV/短链/分 P、元数据、字幕优先、yt-dlp 音频/视频、Whisper.cpp、raw/corrected Transcript、AI Note、章节/目录、地点、POI、截图、封面；
- 任务：持久 Job、Lease、独立 Worker 心跳、取消、超时、完整重跑、步骤级 Replay、24 小时 Artifact；
- AI：自定义 OpenAI-compatible/Ollama 模型库、主/备用路由、有限重试、Ollama `keep_alive: 0`、Prompt 补充；
- 地图：全国视野、bbox/zoom/cluster、GCJ-02、Marker 生命周期、地点详情、路线清单和 GeoJSON/CSV/JSON 导出；
- 运维：真实 Mac mini 指标、JSONL 日志、SQLite 审计、组合筛选、事件详情、关联任务、脱敏导出；
- 数据治理：Transcript 180 天清理、视频笔记保留式删除、任务/内容历史删除、Secret Store。

### 1.5 尚未充分验证或不属于当前范围

- CI 不依赖实时 Bilibili、微信、高德或外部 LLM；平台改版、Cookie 风控、额度和网络仍需定期真实样本回归；
- 高德三项 Key、外部模型 Key、Bilibili Cookie 由部署者提供，代码无法替代外部配置；
- 局域网 HTTP 只适用于可信网络，HTTPS/VPN 尚未成为默认部署；
- 单 Worker、单 GPU 重任务并发为 1；未验证多 Worker 和高并发；
- 浏览器截图主要来自历史版本，当前 v0.4.5 虽有 Browser 验收记录，但没有独立自动化端到端套件覆盖所有 PC/Mobile 路径；
- 备份文件存在且数据库完整性已验证，但文档未提供近期完整“备份恢复演练”证据；
- `FUTURE_ROADMAP.md` 中云化、多用户、GenericProcessor、C 级自动操作等均未实施。

### 1.6 文档覆盖结论

文档对产品、架构、领域、API、安全、运维、测试和历次 UI/可靠性决策覆盖较完整，但存在以下客观缺口：

- `IMPLEMENTATION_STATUS.md` 是当前唯一实施状态来源，源码和在线服务基本支持其 v0.4.5 声明；
- 若干专项文档标题仍写“待实施”，但源码、迁移和测试已存在，例如阅读返工、视频笔记删除、日志续跑；
- `REGRESSION_AND_CHANGE_GUARD.md` 的测试数字、迁移版本和部分待实施标签停留在早期版本；
- 原 `manifest.json` 漏列多份现有专项文档；原合订本生成清单漏入 Prompt 补充、模型/保留、移动会话等专项契约；
- 根 README、后端包、前端包、FastAPI 与业务文档版本号不一致；
- `SYSTEM_ARCHITECTURE.md` 中 Repository/Processor 接口部分是目标边界，当前实现仍大量由 Router/Service 直接访问 SQLAlchemy，不应误认为已经完全分层。

因此：文档已覆盖主要已实施能力，但在交接前仍需完成“状态标签统一、聚合清单统一、版本统一”。本交接书记录的是核验后的实际基线。

## 2. 完整技术栈与架构

### 2.1 前端

- React 19、React DOM 19；
- TypeScript 5.8、Vite 7；
- React Router 7；
- TanStack React Query 5；
- Lucide React；
- Vitest、Testing Library、jsdom、ESLint 9；
- 响应式单页应用，PC 使用 CMS/运维侧栏，手机使用“首页/内容/投递/待办/我的”底栏。

### 2.2 后端

- Python 3.12；
- FastAPI、Uvicorn、Pydantic Settings；
- SQLAlchemy 2、Alembic；
- httpx、python-multipart；
- Pillow、pypdf、python-docx、openpyxl；
- yt-dlp；
- 自研同步 Worker、Lease、Artifact Replay 和审计服务。

### 2.3 数据与文件

- SQLite，启用 WAL、foreign_keys、busy_timeout=5000；
- 迁移序列 `0001`–`0007`；启动时仍调用 `Base.metadata.create_all` 兼容初装，正式升级以 Alembic 为准；
- 永久文件：Source、Snapshot、Evidence、截图、视频封面衍生图、导出；
- Replay/cache：视频、音频、帧、临时文件，默认 24 小时；
- JSONL 日志：10 MB × 5 轮换，API/Worker 分文件；
- Secret：生产 macOS Keychain，开发可用 0700 目录/0600 文件。

### 2.4 本地与外部运行时

- macOS Vision OCR；
- FFmpeg 9.x；
- whisper.cpp + `ggml-base.bin`，Metal 失败时 CPU 回退；
- Ollama + Metal，本地 `/api/chat` 使用 `keep_alive: 0`；
- DeepSeek、MiMo、Moonshot/Kimi、智谱、通义及任意 OpenAI-compatible Provider；
- 高德 JS API/Security Code/Web Service Key，坐标系 GCJ-02；
- Bilibili API/CDN、yt-dlp 和可选平台 Cookie。

### 2.5 物理与逻辑架构

```text
PC/Mobile Browser
  → React SPA
  → FastAPI REST/WebSocket
  → SQLite + Local Files + Keychain
  → Independent Worker
      → Resolver / Document / OCR / ASR
      → LLM Router / Transcript Correction / Note
      → Place / AMap / Screenshot / Cover
      → Artifact Manifest / Replay / Materialize
```

API 只负责接入、校验、查询、配置和创建 Job。下载、OCR/ASR、模型调用、截图等长任务必须进入 Worker。

## 3. 系统核心能力清单

### 3.1 Capture 与来源

- 统一接收 URL/Text/File；
- InputNormalizer 区分 URL_ONLY、SHARE_TEXT_WITH_URL、TEXT_ONLY、MULTIPLE_URLS；
- 单一分享链接只保留 URL、候选数、丢弃长度和原始输入哈希，不保存周边分享全文；
- 多链接歧义返回候选，不创建 Job；
- Source → Snapshot → Segment → Claim → Evidence 可回读。

### 3.2 招聘链路

- 招聘/旅行/不支持分类；
- 公告正文、附件和表格解析；
- 招聘时间、数量、条件、岗位等首批字段；
- 用户档案、条件状态、Evidence 和 Review/Unknown 表达；
- 内容、详情、待办和来源审计 UI。

当前招聘能力属于首批业务闭环，文档中的完整 DSL、MajorMatcher 和大规模真实岗位质量门槛仍需持续样本验证。

### 3.3 视频 AI 笔记链路

主要步骤：

```text
VALIDATE_LINK → FETCH_METADATA → FETCH_SUBTITLE
→ DOWNLOAD_AUDIO → ASR → NORMALIZE_TRANSCRIPT
→ CORRECT_TRANSCRIPT → GENERATE_AI_NOTE
→ EXTRACT_TRAVEL_FACTS → RESOLVE_POI → BUILD_PLACE_NOTES
→ PLAN_SCREENSHOTS → DOWNLOAD_VIDEO_FOR_FRAMES
→ EXTRACT_SCREENSHOTS → MATERIALIZE → CLEAN_CACHE
```

已实现：

- Bilibili URL 规范化、元数据、字幕优先与 ASR fallback；
- raw/corrected Transcript 双版本、Segment ID/顺序/时间码校验、批次校对；
- 版本化 AINote、结构化 Section、thesis/summary/bullets/anchor；
- 主旨目录、时间线详述、地点/转写证据区、时间码跳转；
- 代表截图规划、质量过滤、哈希去重、Section 绑定、Lightbox；
- 本地封面下载、CDN allowlist、MIME/解码/大小校验、672×378 WebP；
- 完整转写 TXT 导出和 180 天清理；
- Note/Version ID 历史兼容；
- 视频笔记保留式删除。

### 3.4 地点、地图与路线

- PlaceMention 与 Place 分离；raw_name/canonical_name 并存；
- 高德 POI 提供坐标，不接受 LLM 自造经纬度；
- 歧义进入 REVIEW，不生成正式 Marker；
- 中国大陆默认 viewport，bbox/zoom 查询和低缩放聚合；
- Marker 新增、隐藏、用户软删除/恢复；
- 地图浮层、统一 Place Detail、想去/去过/计划/忽略；
- 路线清单只保存选点和人工顺序，不伪造最优路线；
- CSV/JSON/GeoJSON 导出明确 GCJ-02。

### 3.5 Job、恢复与调度

- Job 状态：QUEUED/RUNNING/NEEDS_USER/COMPLETED/PARTIAL_SUCCESS/FAILED/CANCELLED；
- JobStep 独立状态/进度/输入哈希/输出引用；
- SQLite 原子领取、lease、任务心跳、900 秒尝试超时；
- Worker 进程心跳使用独立守护线程，不被同步长 Pipeline 阻塞；
- 取消在批次和 Provider 边界检查，取消完成前阻止重试；
- 完整重跑创建新 Job；步骤续跑使用 JobStepArtifact、24 小时 TTL、REUSED/INVALIDATED 状态；
- Replay Options 由服务端计算，Prompt/输入变化可推进最早失效步骤；
- Artifact 到期或缺失时只允许完整重跑；
- Worker 每日清理过期 Replay Artifact 和 Transcript 正文。

### 3.6 模型与 Prompt

- 任意 OpenAI-compatible/Ollama 模型配置；
- 主模型/备用模型路由；
- Keychain Secret、草稿真实测试；
- 调用前等待、有限重试、重试间隔、备用切换；
- Ollama 调用后立即释放；
- 三类低优先级 Prompt 补充：转写校对、视频笔记、地点提取；
- 固定 JSON/Schema/ID/证据契约不可通过 UI 修改；
- 补充 Prompt Hash 参与 Replay 失效判断。

### 3.7 运维与审计

- 真实 CPU、内存、压缩内存、磁盘、API/Worker/SQLite/Ollama 状态；
- 指标写入 SQLite，局域网客户端读取同一快照；
- Request ID、JSONL 日志、SystemEvent 审计；
- 时间/级别/组件/事件/Job/Request/实体/关键词组合筛选；
- 游标分页、实时跟随、事件详情、关联任务、脱敏单条导出；
- 任务详情 WebSocket，断线后轮询回退；
- 所有用户时间强制 Asia/Shanghai，持久化为 UTC。

## 4. 系统真实复杂度来源

### 4.1 多层状态机

- Job 总状态、JobStep 状态、Artifact 状态、Note 状态、Transcript 校对状态、POI Resolution、Marker Visibility、用户地点状态彼此独立；
- `progress=100` 不等于 COMPLETED，PARTIAL_SUCCESS 表示流程结束但仍有补充项；
- 旧 ERROR 事件不代表当前 Job 仍失败，UI 必须查询实时状态和 Replay Options。

### 4.2 并发与 SQLite

- API、Worker、Worker heartbeat thread 和浏览器查询共享 SQLite/WAL；
- Lease 领取依赖条件 UPDATE；事务边界、rollback 和 busy timeout 直接影响稳定性；
- 同一数据库同时保存业务状态、运行时指标、审计和配置，长事务会放大锁竞争。

### 4.3 同步重任务与取消

- yt-dlp、FFmpeg、Whisper、Pillow、httpx/LLM 多为同步调用；
- 单 Worker 内的长调用必须靠任务心跳、独立进程心跳和请求边界取消共同维持可观测性；
- 取消不能等同于简单改状态，必须停止后续批次并释放 lease/临时资源。

### 4.4 版本与引用关系

- Source/Snapshot/Segment/Claim/Evidence 是证据骨架；
- VideoAsset、Transcript Version、AINote、AINoteVersion、Section、Screenshot、CoverAsset 有不同生命周期；
- `note_*` 是公开 Note ID，`ntv_*` 是版本 ID；历史兼容不能散落在各接口；
- raw/corrected Transcript 必须保持 Segment ID、顺序和时间范围不变。

### 4.5 Replay 依赖

- 步骤续跑不仅看 JobStep 状态，还依赖 Artifact 文件、TTL、Input Hash、Prompt Hash、Producer/Schema Version；
- 上游 REUSED、下游 INVALIDATED、新版本产物之间存在审计链；
- 清理 Cache、删除 Note、删除内容不能破坏 Replay 或 Evidence。

### 4.6 外部平台不确定性

- Bilibili 格式、Cookie、字幕和 CDN；
- 微信风控/登录；
- LLM 限流、超时、非标准 JSON；
- 高德 Key、白名单、配额和 POI 歧义；
- Mac 统一内存下 ASR/LLM/图像处理资源争用。

### 4.7 前后端契约耦合

- Task Detail、Logs、Video Note 和 Map 依赖大量状态字段与稳定 ID；
- 任务步骤中文化、排序、停滞阈值、Replay 按钮必须与后端顺序/门禁一致；
- 删除、重跑、Token 轮换等操作需要同时刷新多个 React Query cache。

## 5. 核心高危文件职责与风险

| 文件 | 职责 | 风险与约束 |
| --- | --- | --- |
| `backend/src/zhijian/api/router.py` | 绝大多数业务/管理 API、状态 ViewModel、日志、模型设置、地图和 Job 操作 | 约 1949 行，直接查询多张表；**禁止随意修改**路由返回字段、认证依赖、Job 门禁和删除边界。应先加契约测试再拆分 Router。 |
| `backend/src/zhijian/services/video_pipeline.py` | 视频端到端状态机、步骤/Artifact、取消、部分成功、Replay 分支 | 约 1096 行；**禁止随意修改**步骤顺序、进度、Artifact、finally 清理和状态收口。任何步骤变化必须同步 Replay、前端时间线、文档和测试。 |
| `backend/src/zhijian/services/video_support.py` | Transcript、AI 校对、Note/Section、Prompt Hash、地点提取/POI/历史修复 | 约 917 行；**禁止随意修改**Segment ID、raw/corrected、证据校验、Prompt 核心契约和版本生成。 |
| `backend/src/zhijian/services/job_replay.py` | Replay Options、Artifact/Prompt 失效、步骤续跑入队 | **禁止绕过**服务端计算的 replay_from_step；前端不得指定任意后续步骤。 |
| `backend/src/zhijian/services/jobs.py`、`worker.py` | Lease、超时、Artifact 清理、独立心跳、Worker 主循环 | **禁止随意修改**原子领取、lease 释放、取消、心跳线程和每日清理。 |
| `backend/src/zhijian/db/models.py`、`backend/alembic/versions/` | 28 张业务表和历史迁移 | **禁止直接改历史迁移**；新 Schema 必须新建迁移、备份生产库、验证 head/integrity。当前 0002/0003 已在工作树被修改，合并前必须重点审计。 |
| `backend/src/zhijian/db/session.py` | Engine、WAL、FK、busy timeout、Session 工厂 | **禁止取消** WAL/FK/busy timeout；不在无评估下改连接/事务模型。 |
| `backend/src/zhijian/services/auth.py`、`core/secret_store.py` | LAN 配对、Session、Keychain/File Secret | **禁止记录或回传**配对码、Cookie、API Key；不得把 Secret 写 SQLite/localStorage。 |
| `backend/src/zhijian/main.py` | Lifespan、指标采样、CORS、日志中间件、SPA 静态资源 | **禁止在请求线程加入长任务**；保持 index no-cache、hash asset immutable。 |
| `frontend/src/features/tasks/TaskDetailPage.tsx`、`taskTimeline.ts` | 实时任务、停滞、重跑/续跑、步骤时间线 | **禁止前端推测失败或绕过 Replay Options**；状态/阈值必须来自统一契约。 |
| `frontend/src/features/video/VideoNotesPage.tsx` | Note 列表/详情、目录、证据、删除、截图/Lightbox | **禁止回退**到远程封面、原始 Transcript 正文堆叠或错误 Note ID。 |
| `frontend/src/lib/api.ts`、`lib/types.ts` | 前后端契约 | 字段改动影响全站；先更新后端 Schema/测试，再同步类型和调用。 |
| `frontend/src/styles/global.css` | 全局 701 行视觉与响应式规则 | **禁止无范围的全局选择器/重置**；缩放、窄桌面、手机可能被一次改动同时破坏。 |
| `deploy/macos/manage.py` | LaunchAgent 安装、状态、回退 | 涉及运行服务和 Keychain 主体；安装前必须备份 plist/数据库并确认无活跃 Job。 |

## 6. 现有技术债务与维护风险

### 6.1 交付与版本治理

- 当前工作树远离 HEAD，存在大量未提交文件；没有可证明包含 v0.4.5 的单一 commit/tag；
- 根 package 0.1.0、前端/后端 0.2.0、API 0.2.0、文档 v0.4.5 不一致；
- 当前在线服务实际运行的是工作树构建，重装或误切分支可能丢失大量功能。

### 6.2 文档漂移

- `IMPLEMENTATION_STATUS.md` 与源码最接近，但更新日期仍为 2026-08-24；
- 若干专项文档和 `REGRESSION_AND_CHANGE_GUARD.md` 仍把已实现能力写为待实施；
- 回归基线仍记 25 项测试/0004，真实为 51 项/0007；
- 合订本/manifest 过去未覆盖所有专项文档；
- 设计截图分散在多个版本目录，概念稿与实际运行截图容易混用。

### 6.3 代码集中度

- Router、视频 Pipeline、视频 Support 三个文件合计约 4000 行，是主要耦合中心；
- SQLAlchemy 查询、ViewModel、权限、状态机和审计在 Router 中混合；
- 视频模块同时处理网络、模型、文件、数据库、状态和 UI 契约，局部改动回归面大。

### 6.4 数据库与迁移

- 启动时 `create_all` 与 Alembic 并存，可能掩盖迁移遗漏；
- SQLite 适合当前单节点，但审计/指标/业务共库会增加锁与容量压力；
- JSON 字段承载较多跨层结构，Schema 演进依赖应用校验；
- 历史迁移文件 0002/0003 在当前工作树被修改，禁止在未审计的情况下发布。

### 6.5 测试不均衡

- 后端测试数量和状态机覆盖较强；前端只有 10 项，主要覆盖任务/设置/地图/Markdown/时间；
- 缺少持续执行的全浏览器 E2E、网络故障注入、数据库恢复演练、长视频压力测试；
- 真实平台验收依赖外部环境，结果不可完全复现。

### 6.6 外部与资源风险

- 16 GB 统一内存限制 ASR/LLM 并行；单 Worker 是稳定性选择也是吞吐瓶颈；
- LLM 返回不合法 JSON、限流和长响应仍是主要失败来源；
- 平台 Cookie/接口改版可能使字幕、音频、截图、封面失效；
- 当前 40 MB 日志已接近多轮换文件规模，长期清理与磁盘水位告警仍需治理。

### 6.7 安全与部署风险

- 4 位配对码依赖可信 LAN、失败锁定和 Session；不适合公网；
- LAN HTTP 无传输加密；公共 Wi-Fi/访客网络禁用；
- 开发默认 Secret Store 为文件，生产必须确认实际使用 Keychain；
- `.env.example` 仍含早期 Vite 高德变量，当前高德配置主要由设置/Bootstrap 管理，易误导接手者。

## 7. 后续优先治理与迭代方向

### P0：先建立可回退交付基线

1. 备份 `data/app.db`、Keychain 项目清单、LaunchAgent plist 和永久文件；执行一次恢复演练。
2. 审阅当前 dirty diff，特别是历史迁移 0002/0003；移除 `.DS_Store` 等无关变更。
3. 将当前已验证工作树形成单一 commit/tag，记录数据库 `0007`、前端 asset hash 和部署时间。
4. 统一 root/backend/frontend/API/docs 版本号与发布说明。
5. 重新安装/重启服务前确认无 QUEUED/RUNNING/CANCELLING Job。

### P1：同步文档事实

1. 以 `IMPLEMENTATION_STATUS.md` 为状态源，清理各专项文档过期的“待实施”标签。
2. 更新 `REGRESSION_AND_CHANGE_GUARD.md` 的迁移、测试数和 GUI 记录。
3. 保证 manifest、README 索引、合订本生成清单包含全部源文档。
4. 区分“设计稿”“运行截图”“历史稿”，避免把效果图当实现证据。

### P1：降低高危文件耦合

1. 先通过契约测试冻结 API，再按领域拆分 `api/router.py`。
2. 将视频 Pipeline 的步骤执行、Artifact、状态收口和 Provider 调用分层；不改变步骤顺序。
3. 将 Query/ViewModel 从写操作 Service 中分离，减少 Router 直接操作多表。
4. 保持所有拆分为机械迁移；不与新功能同时进行。

### P1：补关键回归

1. 建立 PC 1440、935 窄桌面和 390 手机的 Browser E2E smoke；
2. 覆盖 Session 刷新、Capture、多链接、取消、完整重跑、步骤续跑、Note 删除、Map Marker 生命周期；
3. 增加 SQLite busy/断电恢复、备份恢复和 Artifact TTL 测试；
4. 定期跑 Bilibili 有字幕/无字幕、竖屏/横屏和外部模型故障样本。

### P2：稳定性和容量

1. 增加磁盘低水位、数据库备份年龄、日志/缓存容量告警；
2. 对视频时长、ASR、校对批次、截图下载和模型调用建立性能基线；
3. 对 LLM 结构化输出建立更严格的 Schema/重试/降级统计；
4. 评估审计/指标与业务数据的清理节奏，不急于迁移数据库。

### P3：谨慎迭代

- 招聘 DSL/MajorMatcher、旅行偏好、更多平台 Resolver 只在黄金样本和 Evidence 门槛明确后扩展；
- 多 Worker、云化、GenericProcessor、自动操作属于未来路线，不与当前单机治理混做；
- 高德路线计算、远程访问和 HTTPS 需要独立安全/部署决策。

## 8. 开发硬性约束规范

### 8.1 改动禁区

- **禁止随意修改** Source/Snapshot/Segment/Claim/Evidence 引用链；
- **禁止随意修改** Job/JobStep/Artifact 状态、步骤顺序、Lease、取消和 Replay 门禁；
- **禁止随意修改** `note_*`/`ntv_*`、raw/corrected Transcript、PlaceMention/Place 的身份边界；
- **禁止随意修改** 历史 Alembic 迁移；新增 Schema 必须新迁移；
- **禁止随意修改** Auth、Secret Store、日志脱敏和局域网安全边界；
- **禁止随意修改** 全局 CSS、PC/Mobile 导航和地图父页面语义；
- **禁止随意修改** 固定 Prompt 中的 JSON/Schema/ID/证据契约。

### 8.2 必须遵守的范式

1. 长任务只创建 Job，由 Worker 执行；FastAPI 请求不跑 ASR、LLM、视频下载或长 Playwright。
2. 事实性 Claim 必须有 Evidence；LLM 不生成 POI 坐标，不把推理伪装成事实。
3. Secret 只进 Keychain/受限 FileSecretStore；禁止进入 SQLite 明文、日志、URL、导出和 localStorage。
4. 数据库变更：备份 → 新 Alembic migration → upgrade → current → integrity_check → 回归。
5. Job 改动必须同步：后端状态机、审计事件、API Schema、Task/Logs UI、测试和文档。
6. 视频步骤变化必须同步 `VIDEO_STEP_ORDER`、Artifact、Replay、时间线中文映射和进度。
7. 前端不能自行判断可重跑/可续跑步骤；只消费服务端 Replay Options。
8. 取消必须协作式生效，释放 lease 前禁止新尝试覆盖旧执行。
9. 用户时间显示为 Asia/Shanghai，持久化和 API 时间保持带时区 UTC。
10. 地图首次全国视野；禁止恢复厦门/思明等历史默认参数和静态伪地图。
11. Marker 删除不级联删除 Place/Source/Claim/Evidence/Note。
12. Note 删除保留共享 Source、VideoAsset、CoverAsset、Transcript、Place 和 Evidence。
13. Transcript 到期清理 raw/corrected/quote，但保留时间轴、Note、截图和审计 tombstone。
14. 新功能不得通过重写页面覆盖现有入口；设计资产只作为实现依据，不作为页面背景。

### 8.3 每次交付必跑

```bash
.venv/bin/python -m alembic -c backend/alembic.ini current
.venv/bin/python -m pytest backend/tests -q
.venv/bin/python -m ruff check backend/src backend/tests
pnpm --dir frontend lint
pnpm --dir frontend test -- --run
pnpm --dir frontend build
python scripts/build_complete_project_spec.py
git diff --check
```

然后：

- 查询 `/api/jobs`，确认没有活跃任务再重启 API/Worker；
- 检查 `/api/status`、Worker heartbeat、数据库 integrity；
- 用 Browser 回归目标页面、控制台和至少一个真实交互；
- 更新 `IMPLEMENTATION_STATUS.md`，不得把 Fixture、设计稿或构建成功描述为真实端到端验收。

### 8.4 兼容与回退要求

- API/DB 字段优先向后兼容；历史 `ntv_*` 链接仍需解析；
- 新版本结果追加版本，不原地覆盖 Note/Transcript/Evidence 历史；
- Provider/Prompt/Parser 变化必须进入 Input/Prompt Hash 和 Replay 失效计算；
- 发布前记录 Git commit/tag、迁移 head、备份路径、前端 hash 和服务状态；
- 回退代码前先停止服务并备份数据库；默认不 downgrade 破坏性迁移。

## 交接入口

- 当前实施状态：`IMPLEMENTATION_STATUS.md`
- 防覆盖基线：`REGRESSION_AND_CHANGE_GUARD.md`
- 完整规格索引：`README.md`
- 生成合订本：`COMPLETE_PROJECT_SPEC.md`
- 部署操作：`../deploy/macos/README.md`
- 设计资产：`../design/ui/README.md`
