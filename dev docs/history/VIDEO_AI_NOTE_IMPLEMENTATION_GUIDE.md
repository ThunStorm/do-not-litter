> 历史实施计划，2026-09-03 归档；本文“待实施/当前/生产已验收”是旧记录，不覆盖 [当前实施状态](../IMPLEMENTATION_STATUS.md)。裸文档路径以 dev docs/ 为基准。

# Video AI Note Implementation Guide

> 用途：供后续 Codex/Agent 直接读取和实施
> 更新日期：2026-08-24
> 当前状态：v0.4/v0.4.1、v0.4.3 与 v0.4.4 已实施；在线库已应用 0007，API/Worker、真实视频 Pipeline 及 PC/Mobile 页面均已验收
> UI 前置已满足：v0.4 设计稿位于 `design/ui/v0.4/`，用户已确认既有视觉方向；后续修改必须遵循防覆盖基线

---

# 1. Agent 必读顺序

【旧读取要求已撤销】下列列表仅保留历史参考；当前按仓库 AGENTS.md 选择一个相关分篇，不要求完整读取：

1. `video/VIDEO_AI_NOTE_PIPELINE.md`：业务目标、端到端处理契约和异常边界，最高优先级；
2. `product/TRAVEL_FOOD_PIPELINE.md`：地点、Observation、POI、偏好和地图领域规则；
3. `architecture/DATA_MODEL.md`：持久化对象和 Evidence 关系；
4. `architecture/API_DESIGN.md`：资源边界和 ViewModel；
5. `ai-gateway/AI_RUNTIME_AND_PROVIDERS.md`：DeepSeek、ASR、模型路由和版本；
6. `architecture/SECURITY_PRIVACY.md`：Cookie、Secret、外发和 SSRF；
7. `testing/TESTING_AND_ACCEPTANCE.md`：验收用例；
8. 本文件：把上述设计映射到当前代码和实施工作包。

历史冲突优先级（不再作为当前指令；现行规则见仓库 AGENTS.md）：

```text
用户最新明确指令
> video/VIDEO_AI_NOTE_PIPELINE.md
> 本实施指南
> 专项领域文档
> COMPLETE_PROJECT_SPEC.md（生成文件）
> 旧实现行为
```

`COMPLETE_PROJECT_SPEC.md` 不能手工编辑。修改源文档后运行：

```bash
python3 scripts/build_complete_project_spec.py
```

---

# 2. 已冻结的产品决策

以下决策不再留给实现 Agent 自行选择：

- MVP 首个平台是 Bilibili；支持 BV、`b23.tv` 和 `?p=N` 分 P；
- 参考并复用 BiliNote 成熟轮子，不照搬其整套应用；
- 平台字幕优先，无字幕才下载音频和运行 ASR；
- AI 笔记必须包含代表性截图；为抽帧允许下载受限画质视频，但不做默认全视频多模态理解；
- 视频 AI 笔记是一级、版本化业务产物；
- 视频笔记默认使用已配置的 DeepSeek OpenAI-compatible Provider；
- 地点结构化提取是与笔记生成分开的 Schema-first LLM 调用；
- 地点事实的 Evidence 必须指向 Transcript Segment，AI Markdown 不能充当唯一证据；
- PlaceMention 与现实 Place 分离；坐标只能来自高德等 POI Provider；
- 地点粒度覆盖餐馆、景区、街区、步行街、商圈、市场、公园、博物馆等，不只停留在城市；
- 转写地点名必须经过高德候选校正，保留 `raw_name` 与 `canonical_name`；
- 同一 Place 聚合多个来源并生成版本化地点归纳笔记；
- 视频笔记、地点列表和地图 Marker 全部进入同一个 `/places/:placeId`；
- 地图使用中国大陆全境，无默认城市，按 bbox/zoom 加载和聚合；
- Marker 支持用户新增、隐藏、删除和恢复，点击后先在地图浮窗显示简介，再进入详情；
- 高德 JS Key、Security Code 和 Web 服务 Key 必须可在设置中填写与测试；
- 粘贴内容先区分纯 URL、带分享文字的唯一 URL、普通文本和多 URL；唯一 URL 场景只把 URL 送入 Pipeline，周围标题不得进入 Resolver/LLM；
- 多个不同内容 URL 不静默取第一个，返回 `CAPTURE_MULTIPLE_URLS` 候选；
- 长任务必须走持久 Worker，不能使用 FastAPI `BackgroundTasks`；
- 任务支持重启恢复、步骤重跑、缓存复用、部分成功和明确的 `NEEDS_USER`；
- PC/Mobile UI 已按确认方向实施；新增页面或重构现有页面前，必须先更新 `REGRESSION_AND_CHANGE_GUARD.md`，避免覆盖已可操作能力。

---

# 3. 当前代码事实与差距

## 3.1 当前已有

- FastAPI、SQLite WAL、SQLAlchemy、Alembic、持久 Job lease 与恢复；
- `VideoAsset / Transcript / AINote / AINoteVersion / AINoteSection / PlaceMention / PlaceNoteVersion / ExternalCallAudit`；
- Bilibili BV/短链/分 P、metadata、平台字幕优先与 yt-dlp 音频回退；
- FFmpeg + Whisper.cpp 时间码转写；
- `generate_text / generate_json`、能力角色和可配置主/备用模型；
- 版本化 AI Note、地点候选、Transcript Evidence、高德 POI 与 `PARTIAL_SUCCESS`；
- Video Note 列表、详情、Transcript、地点、重新生成 API 和响应式页面；
- 高德地图、Marker 选择、地点简略卡和 Place Detail；
- SecretStore、日志、SystemEvent、Request ID 和真实 Bilibili 无字幕样本验收。

## 3.2 v0.4 已实施映射

- `0004_video_screenshots_and_map_markers` 已持久化 `VideoScreenshot`、`MapMarkerState`、`raw_name`、`canonical_name` 和 `PlaceBrief`；
- Pipeline 使用 `PLAN_SCREENSHOTS → DOWNLOAD_VIDEO_FOR_FRAMES → EXTRACT_SCREENSHOTS` 显式步骤，下载受限视频，抽帧时进行时间窗搜索、黑帧/曝光/清晰度/感知去重过滤；
- POI 候选歧义会保留候选理由并进入 `REVIEW`，不会生成正式 Marker；
- `/api/travel/map` 使用中国大陆默认 bbox、zoom 聚合、视野恢复与 `origin` 过滤；旧地点惰性补齐独立投影状态；
- 地图浮层已显示代表图、地址、特色、来源数、类型、状态和详情入口；用户 Marker 可新增、软删除、恢复，AI Marker 仅隐藏投影；
- 高德 JS Key、Security Code 和 Web 服务 Key 通过设置/Keychain/Bootstrap 管理，并提供 Web 服务真实测试；
- 厦门、思明区、城市级 `setFitView` 和路线默认城市已从产品代码移除；“偏好城市”只保留为可选个人设置，不影响地图首屏。

## 3.3 历史临时行为

本节原列出的厦门硬编码、环境变量地图 Key、无 Marker 生命周期和无截图行为均已移除。保留这一实施指南是为了说明 v0.4 的迁移原因；当前防覆盖检查以 `REGRESSION_AND_CHANGE_GUARD.md` 为准。

## 3.4 2026-08-24 可靠性修复（已实施）

本轮按以下最小闭环完成了代码、数据库兼容、运行页面与上游实现修复：

1. **视频笔记身份修复**：新写入将父 `AINote.id` 写入 `ContentItem.structured_json.note_id`，并保存版本 ID 作为辅助字段；共享 `_asset_for_note` 对既有 `ntv_*` 链接提供只读兼容解析，所有详情/转写/地点/截图接口共用该根节点。
2. **详情错误态**：`VideoNoteDetailPage` 区分 pending、错误和 success；错误态显示后端原因、返回列表与重试入口。内容详情仅在 `structured.note_id` 非空时展示链接。`SessionGate` 的 `/api/status` 检查使用 8 秒有界超时，失败进入已有“重新连接”状态。
3. **Ollama 及时释放**：`OllamaProvider` 的每次 `/api/chat` 请求均发送 `keep_alive: 0`，覆盖任务推理、备用模型与设置页真实测试的共用调用路径。
4. **截图格式修复**：媒体适配器使用 `bv*[ext=mp4]/bv*/best + res:720`，注入 Bilibili Referer/Cookie，保留实际大小检查和缓存策略；不再要求音视频合一或错误排除竖屏流。
5. **状态恢复**：同一 Note Version 已有 `PLANNED` 截图计划会复用并继续物化；每次内容物化覆盖旧 `screenshot_error`，按本次 POI/截图结果决定 `COMPLETED/PARTIAL_SUCCESS`。

建议只修改共享根节点及其最小测试：`providers/llm.py`、`providers/media.py`、`services/video_pipeline.py`、`api/video_notes.py`、`VideoNotesPage.tsx`、`SessionGate.tsx`，以及对应后端/前端测试。无需引入新下载器、Ollama SDK 或独立状态机。

## 3.5 2026-08-24 内容完整性、截图与文稿保留修复（已实施）

样本 `note_221cd61e9600493cb3f32e062e1ad013` 的现场数据为：视频元数据时长 `369000 ms`，ASR 共 232 段但末段为 `3680800 ms`，Note Version 只有 102 字 overview、0 个 `AINoteSection`、0 个截图计划。截图视频已经成功下载 `21867505` 字节，因此本次“0 张可用”不是下载失败，而是没有计划可执行。

实施结果：

1. Whisper.cpp JSON offset 按毫秒写入；末段时间显著超过视频时长会拒绝物化。Worker 启动时对约 10 倍的历史时间轴创建修正版 Transcript Version，不原地覆盖旧数据。
2. 有效 Segment ID 为空时使用服务端固定分块的“转写整理”章节；模型调用失败也进入该兜底，任何有效 Transcript 至少物化一个时间线章节并覆盖末段。
3. 无章节时 `plan_screenshots` 从有效 Transcript 生成 3–6 张确定性计划；`plans == 0` 跳过视频下载并记录 `SCREENSHOT_PLAN_EMPTY`。Worker 为历史 Note 补齐计划，但不隐式下载历史媒体。
4. 视频笔记页分为“摘要”“按时间线详述”“代表截图”“完整转写”；完整转写显示段数、保留期、可折叠预览和即时 TXT 导出。
5. 新增 `retention_until/purged_at` 与 Worker 每日幂等清理。到期后清空正文、Segment 文本、Evidence quote 和旧全文 fingerprint；保留时间轴/Note/截图，转写读取和导出返回 410。

建议实施文件限定为 `providers/asr.py`、`services/video_support.py`、`services/video_screenshots.py`、`services/video_pipeline.py`、`services/transcript_retention.py`、`api/video_notes.py`、`worker.py`、`VideoNotesPage.tsx`、API types/tests 与一条 Alembic 迁移。导出使用标准库文本响应，不新增文档生成依赖或调度框架。

## 3.6 2026-08-24 粘贴输入规范化（已实施）

前端始终提交原始粘贴值，由后端统一 `InputNormalizer` 判定：

- `URL_ONLY`：纯链接；
- `SHARE_TEXT_WITH_URL`：周围有标题/分享文字但可唯一提取链接；
- `TEXT_ONLY`：无链接普通正文；
- `MULTIPLE_URLS`：多个不同内容链接。

唯一链接被选择后，只把 `selected_url` 送入 Capture/Pipeline，`text` 为空；分享标题不参与分类、Resolver、LLM、Claim 或 Evidence。多个候选 canonical 去重后仍不唯一时返回 `CAPTURE_MULTIPLE_URLS` 和候选，不创建 Job。数据库只保留输入类型、选中 URL、候选数、丢弃长度和原始输入哈希，不保存丢弃文案全文。

---

# 4. 目标目录与文件映射

建议新增目录：

```text
backend/src/zhijian/
  api/
    video_notes.py
    travel_notes.py
    map.py
  domain/
    video.py
    notes.py
  resolvers/
    __init__.py
    registry.py
    video/
      __init__.py
      url_parser.py
      bilibili.py
      subtitles.py
  providers/
    media.py
  services/
    input_normalizer.py
    video_pipeline.py
    transcript.py
    note_generator.py
    travel_extractor.py
    poi_resolver.py
    place_note_builder.py
    video_screenshots.py
  prompts/
    video_note_v1.md
    travel_place_extraction_v1.md
    place_note_v1.md
```

不要为了目录美观一次性搬迁现有招聘、认证或地图代码。新增子模块后由现有 `api/router.py` 和 `services/pipeline.py` 做最小路由接入。

前端目标文件只能在 UI 方案确认后创建或修改，候选范围：

```text
frontend/src/features/content/ContentDetailPage.tsx
frontend/src/features/video-notes/
frontend/src/features/map/PlaceDetailPage.tsx
frontend/src/features/map/MapOverviewPage.tsx
frontend/src/features/map/AmapLayer.tsx
frontend/src/features/map/MapCanvas.tsx
frontend/src/features/tasks/TaskDetailPage.tsx
frontend/src/features/settings/SettingsPage.tsx
frontend/src/lib/api.ts
frontend/src/lib/types.ts
frontend/src/App.tsx
frontend/src/styles/global.css
```

执行检查点：视频与地图 Work Package 0–11 的当前实施状态以各标题及 `IMPLEMENTATION_STATUS.md` 为准，不得重复从零实现或覆盖现有代码。本次新增且尚未实施的是 Work Package 6A“粘贴输入规范化”；后续 Agent 只做有测试保护的增量修改。

---

# 5. Work Package 0：上游与依赖基线

## 目标

建立可审计的 BiliNote 复用边界和运行依赖。

## 修改

- 在 `backend/pyproject.toml` 增加受版本范围约束的 `yt-dlp`；
- 新增 `THIRD_PARTY_NOTICES.md` 或等效文件，包含 BiliNote MIT 声明、来源 URL、审阅 commit 和移植文件清单；
- 在移植文件头写明来源与本项目修改；
- 不把 BiliNote 仓库作为 Git submodule，不在运行时依赖其 Python 包；
- 记录 FFmpeg、yt-dlp、Whisper 的运行诊断；
- 将代理和 Cookie 作为 Adapter 配置，不散落在 Downloader 内。

## 测试

- 上游 notice 存在；
- yt-dlp 可 import；
- runtime status 可区分 READY/MISSING/DEGRADED；
- 日志不包含 Cookie/API Key。

---

# 6. Work Package 1：Schema、枚举和迁移

## 新增模型

在 `db/models.py` 和新 Alembic `0003_video_ai_notes.py` 中新增：

- `VideoAsset`；
- `Transcript`；
- 视频 Transcript 继续复用 `Segment`，扩展 `kind/locator_json/confidence`；
- `AINote`；
- `AINoteVersion`；
- `AINoteSection`；
- `PlaceMention`；
- `PlaceNote`；
- `PlaceNoteVersion`；
- `ExternalCallAudit`。

## 约束

- `VideoAsset(platform, external_video_id, part_number)` 唯一；
- `AINoteVersion(ai_note_id, version_no)` 唯一；
- `PlaceNoteVersion(place_note_id, version_no)` 唯一；
- `Place(external_provider, external_poi_id)` 在值非空时应唯一；
- Transcript Segment 保存毫秒时间码；
- Note Current Version 由外键指向，版本记录不可覆盖；
- 迁移升级不得删除或重建现有业务表；
- downgrade 只删除本迁移新增对象。

## 枚举

- `JobStatus` 增加 `PARTIAL_SUCCESS`；
- 定义 Transcript SourceKind；
- 定义 Note Status；
- JobStep 名称保持字符串或单独枚举，但 API 输出必须稳定；
- 不把 Provider/Model 名称写进枚举。

## 测试

- 空数据库 upgrade 到 head；
- 已有 `0002` 数据库 upgrade 到 `0003`；
- upgrade/downgrade/upgrade；
- 唯一约束和外键；
- Note Version 不被覆盖。

---

# 7. Work Package 2：Bilibili Resolver

## 输入输出

输入：原始 URL。

输出 typed `ResolvedVideo`：

```text
platform
original_url
canonical_url
external_video_id
part_number
external_part_id/cid
title/author/description/tags
cover_url/duration_ms/published_at
subtitle_tracks
raw_metadata_hash
adapter_version
```

## 实现顺序

1. URL allowlist 和 SSRF 防护；
2. `b23.tv` 有限重定向解析；
3. BV ID 与 `p=N` 提取；
4. metadata-only 获取；
5. 根据分 P 获取正确 CID；
6. player API 字幕轨获取和优先级；
7. yt-dlp 字幕 fallback；
8. Typed Transcript 输出；
9. 稳定错误映射。

## BiliNote 对应轮子

- `app/validators/video_url_validator.py`；
- `app/utils/url_parser.py`；
- `app/downloaders/bilibili_subtitle.py`；
- `app/downloaders/bilibili_downloader.py`；
- `app/downloaders/bilibili_dm_patch.py`。

移植时替换 `requests` 为项目现有 `httpx` 约定；网络超时、代理、重定向和 headers 从配置传入，不使用模块级全局状态。

## 错误码

- `VIDEO_URL_UNSUPPORTED`
- `VIDEO_SHORT_URL_EXPIRED`
- `VIDEO_METADATA_FAILED`
- `VIDEO_LOGIN_REQUIRED`
- `VIDEO_ACCESS_DENIED`
- `VIDEO_PLATFORM_RATE_LIMITED`
- `VIDEO_SUBTITLE_UNAVAILABLE`

字幕不可用是 fallback 条件，不直接把任务标为 FAILED。

## 测试 Fixture

- 普通 BV；
- `b23.tv`；
- `?p=2`；
- 人工中文字幕；
- AI 中文字幕；
- 无字幕；
- 过期 Cookie；
- 412、429、超时；
- 恶意重定向到 localhost/私网。

---

# 8. Work Package 3：媒体下载与 ASR

## Media Adapter

`providers/media.py` 封装 yt-dlp：

- metadata-only；
- subtitle-only；
- audio-only；
- future video download，不在 MVP 默认调用；
- Cookie 临时 Netscape 文件必须 owner-only，并在任务后删除；
- 只允许明确输出目录；
- `noplaylist=true`；
- 使用配置的代理和超时；
- 下载后使用 FFprobe 验证时长、容器和大小。

## ASR 改造

`WhisperCppProvider` 改为返回 typed Transcript，而不是单个全文 Segment：

- 优先使用 whisper.cpp JSON/SRT/VTT 等带时间输出；
- 归一为 `start_ms/end_ms/text/confidence`；
- 保留全文；
- 保存 provider、model 和运行模式；
- Metal/Vulkan/CPU fallback 只影响运行信息，不改变 Transcript Schema。

## 配置

在 `core/config.py` 增加：

- media cache root/TTL；
- max video duration；
- max media bytes；
- yt-dlp binary/module strategy；
- network timeout；
- redirect limit；
- optional proxy；
- Bilibili Cookie secret key reference。

## 测试

- 有字幕时确认没有音频下载调用；
- 无字幕时 audio-only + ASR；
- 超长、超大、损坏媒体；
- FFmpeg/Whisper 缺失；
- Worker 失败后缓存保留，完成后按 TTL 清理；
- 取消任务不留下临时 Cookie 文件。

---

# 9. Work Package 4：DeepSeek AI Note

## Provider 改造

当前 `OpenAICompatibleProvider.generate()` 固定 `response_format=json_object`。改造成明确的两个能力：

```python
generate_text(...)
generate_json(..., schema=...)
```

- Markdown 笔记调用 `generate_text`；
- 地点抽取调用 `generate_json`；
- Provider 统一返回 usage、request id（若有）和模型；
- 429、408、连接错误和 5xx 有限指数退避；
- 401/403、余额不足、模型不存在不重试；
- 外部调用写 `ExternalCallAudit`；
- 不记录 Key 和完整敏感正文。

## Provider Role

Settings 新增能力角色：

- `video_note_summary`；
- `transcript_correction`；
- `note_toc_and_section_summary`；
- `travel_place_extraction`；
- `place_note_summary`。

首次迁移/读取时均回退到现有 `default` DeepSeek 配置，避免要求用户重复录入 API Key。Secret 引用复用现有 `provider:default:api-key`，只有用户单独配置角色时才创建角色 Secret。

## Chunk/Merge

实现 `note_generator.py`：

1. 根据 Provider context/request byte budget 切块；
2. 以 Transcript 自然边界切分；
3. 每块保存 index、time range、input hash 和 partial Markdown；
4. 每个 partial 完成后保存 checkpoint；
5. 层级合并，避免一次 merge 再次超限；
6. 校验 Markdown 非空、标题结构和 Segment 引用；
7. 保存新 Note Version；
8. 成功后清理 checkpoint，失败时保留。

Prompt 文件必须独立版本化，不把大段 Prompt 写进 service 代码。

### v0.4.5 用户补充 Prompt

设置页“AI 模型”在推理路由和模型库之间提供三个补充提示词输入。固定文件 Prompt 继续锁定 JSON、Schema、字段、Segment ID、顺序和证据契约；用户只可补充语气、篇幅、受众与关注重点。保存内容加入后续调用的低优先级 System Message，并写入相应 Job Step Input Hash，Prompt 变化时步骤续跑从最早受影响的 AI 阶段开始。

## 测试

- 短字幕单请求；
- 长字幕多 chunk 和多层 merge；
- 中途失败后恢复；
- 输入/模型/Prompt 不变时缓存命中；
- Prompt 或模型变化时生成新版本；
- DeepSeek Markdown 请求不发送 JSON response format；
- 地点 JSON 请求执行 Pydantic 校验；
- Key 无效、余额不足、429、5xx 行为正确。

---

# 10. Work Package 5：旅行提取、POI 与地点归纳

## Typed Extraction

新增 Pydantic 输出 Schema，每个 PlaceMention/Observation 必须包含 `segment_ids`。禁止继续使用 `_extract_travel()` 正则作为生产主路径；正则只能用于低成本分类或测试 fallback，不能生成 CONFIRMED 事实。

## Evidence

- 每个 Claim 绑定模型返回的实际 Segment；
- quote 从 Segment 原文截取并验证；
- 无 Segment、Segment 不存在或 quote 不匹配时 Reject/Retry/Review；
- AI 推断使用 `INFERRED`，作者原话使用 `EXTRACTED/SOURCE_OPINION`；
- 不再把所有 Claim 绑定第一个 Segment。

## POI Resolver

- 用名称、城市、区县、附近地标和类别调用高德；
- 确定性打分，不让 LLM 选经纬度；
- `CONFIRMED/REVIEW/UNRESOLVED/REJECTED`；
- 未解析 PlaceMention 不创建 `(0,0)` Marker；
- 只有 Confirmed Place 有坐标并进入地图；
- 以高德 POI ID 去重；
- 保存候选响应哈希和 GCJ-02。

## Place Note

Place Note Builder 聚合 Place、Mention、Observation、来源 Note 和 Transcript Evidence。新增来源或事实变化时生成新版本；SAVE/VISITED 等用户状态变化不强制重写事实笔记。

## 测试

- 单视频单地点；
- 单视频多地点；
- 多视频同一 POI；
- 同名跨城市；
- 无 POI 和多候选；
- 来源价格/观点冲突；
- 无证据事实被拒绝；
- Place Note 新版本与旧版本共存。

---

# 11. Work Package 6：持久 Pipeline 与 API

## Pipeline Steps

精确使用：

```text
NORMALIZE_CAPTURE_INPUT
VALIDATE_LINK
FETCH_METADATA
FETCH_SUBTITLE
DOWNLOAD_AUDIO
ASR
NORMALIZE_TRANSCRIPT
CORRECT_TRANSCRIPT
GENERATE_AI_NOTE
EXTRACT_TRAVEL_FACTS
RESOLVE_POI
BUILD_PLACE_NOTES
PLAN_SCREENSHOTS
DOWNLOAD_VIDEO_FOR_FRAMES
EXTRACT_SCREENSHOTS
MATERIALIZE
CLEAN_CACHE
```

跳过步骤写 `SKIPPED`，不能直接消失。每个 Step 保存 input hash/output reference。只有输入哈希和实现版本一致才可复用缓存。

## 状态

- `COMPLETED`：笔记和地点阶段完整完成，或合法判断没有地点；
- `PARTIAL_SUCCESS`：AI Note 可读，但部分地点 Review/Unresolved 或非核心增强失败；
- `NEEDS_USER`：Cookie、模型、Key 或 POI 人工选择；
- `FAILED`：不可自动恢复；
- `CANCELLED`：用户取消。

## API 子 Router

实现 `api/video_notes.py`：

```text
GET  /api/video-notes
GET  /api/video-notes/{note_id}
GET  /api/video-notes/{note_id}/transcript
GET  /api/video-notes/{note_id}/places
GET  /api/video-notes/{note_id}/screenshots
POST /api/video-notes/{note_id}/regenerate
```

实现或补充 `api/travel_notes.py`：

```text
GET /api/travel/places/{place_id}/note
GET /api/travel/places/{place_id}/sources
GET /api/travel/map?bbox=&zoom=&place_type=&user_state=&query=
GET /api/travel/map/bootstrap
POST /api/travel/map/markers
DELETE /api/travel/map/markers/{marker_id}
POST /api/travel/map/markers/{marker_id}/restore
```

Capture 可以暂时保留现有 `/api/capture`，但 ViewModel 和文档统一语义需兼容 `/api/inbox` 的长期设计。不要在本功能中无理由全量重命名已有 API。

## 测试

- 端到端公开 Fixture；
- API 鉴权；
- Job 恢复与并发幂等；
- retry/rerun-from-step；
- partial success；
- ViewModel 不泄漏 ORM/Secret；
- Source → Note → Place → Evidence 关系完整。

---

# 11A. Work Package 6A：粘贴输入规范化（已实施）

## 目标文件（实施时）

```text
backend/src/zhijian/domain/schemas.py
backend/src/zhijian/services/input_normalizer.py
backend/src/zhijian/services/capture.py
backend/src/zhijian/api/router.py
frontend/src/features/tasks/CapturePage.tsx
frontend/src/lib/api.ts
backend/tests/test_input_normalizer.py
backend/tests/test_api.py
```

## 契约

- 前端提交完整原始粘贴值，不再以 `startsWith("http")` 作为权威 URL 判定；
- 后端输出 `URL_ONLY / SHARE_TEXT_WITH_URL / TEXT_ONLY / MULTIPLE_URLS`；
- 支持换行、Markdown、尖括号、中文标点、零宽字符和已知平台无 scheme 链接；
- canonical 后去重；多个候选中仅一个命中专用 Resolver 时自动选择；
- 唯一 URL 进入 Source locator，周围文字不进入 payload text；
- 多个内容 URL 返回 `422 CAPTURE_MULTIPLE_URLS` 和候选，不创建 Job、不发起网络请求；
- 默认只持久化 `input_kind/selected_url/candidate_count/discarded_text_length/raw_input_hash`；
- 分享标题不得覆盖平台正式标题。

## 测试

- 纯 URL；
- 标题 + URL + “复制打开”；
- Markdown 与尖括号链接；
- URL 末尾中文/英文标点；
- query/fragment 保留；
- canonical 重复链接；
- 多链接歧义；
- 无链接普通正文；
- 丢弃文案不进入 Resolver、LLM、日志和数据库全文字段。

---

# 12. Work Package 7：代表性截图（已实施）

## 目标文件

```text
backend/src/zhijian/db/models.py
backend/alembic/versions/0004_video_screenshots_and_map_markers.py
backend/src/zhijian/services/video_screenshots.py
backend/src/zhijian/services/video_pipeline.py
backend/src/zhijian/domain/schemas.py
backend/src/zhijian/api/router.py
```

## 实现

- 新增 `VideoScreenshot`，保存 video/note section/place mention/segment、计划与实际时间码、路径、哈希、尺寸、质量分与选择原因；
- Note 和地点抽取完成后生成 Screenshot Plan；
- 用 yt-dlp 下载受限画质视频，禁止默认最高码率；
- FFmpeg 抽帧，检测黑帧、模糊、过曝/欠曝并用感知哈希去重；
- 目标时间码不可用时只在前后小窗口寻找替代帧；
- 每个主要地点 1–3 张，全文默认 3–12 张；
- 无法取得视频流时保留 AI Note，状态为 `PARTIAL_SUCCESS` 并记录稳定错误码；
- 缓存视频按 TTL 清理，已物化截图持久保存。

## 测试

- 截图数量范围、时间码绑定与文件哈希；
- 黑帧/模糊/重复帧淘汰；
- 字幕命中但仍只为截图下载受限视频，不重复 ASR；
- 下载失败时 Note 仍可读；
- 重跑复用有效截图，Prompt/章节变化时重建截图计划。

---

# 13. Work Package 8：细粒度地点与高德校名（已实施）

## 实现

- 扩展 Place 类型：餐馆、景区、街区、步行街、商圈、市场、公园、博物馆、寺庙、村镇、地标、住宿和交通点；
- 提取 `PlaceBrief`：景区/街区特色、菜品特色、价格、排队、适合人群、注意事项、作者态度；
- PlaceMention 同时保存 `raw_name`、`suggested_name`、Segment 与上下文；
- 高德候选确认后保存 `canonical_name`、别名、POI ID、地址、行政区和校正理由；
- 城市/省份只作上下文，不默认创建 Marker；
- 同音、错别字、简称和同名跨城市必须覆盖 Fixture；
- 无唯一候选进入 Review，不由 LLM 自行选择坐标。

## 测试

- 餐馆/景区/街区同一视频混合提取；
- 口语同音名称校正；
- 同名跨城和商场多分店；
- raw/canonical 名称与 Evidence 均保留；
- Brief 中每个来源事实可回到 Segment。

---

# 14. Work Package 9：中国全境地图与 Marker 管理（已实施）

## 后端

- `GET /api/travel/map` 使用 `bbox + zoom`，城市仅是可选筛选；
- 全国缩放级别返回聚合，城市/街区级逐步返回 Marker；
- 新增 `MapMarkerState` 或等效实体，保存 `place_id/origin/visibility/deleted_at`；
- `origin` 至少为 `AI_EXTRACTED / USER`；
- 用户 Marker 创建时调用高德搜索或逆地理编码；直接点选坐标标记 `USER_CONFIRMED`；
- 删除用户 Marker 为软删除；删除自动 Marker 只隐藏投影；支持恢复；
- Map ViewModel 返回 `marker_id + place_id + origin + visibility + preview_image + source_count`。

## 前端

- 删除 `city=厦门市`、厦门标题、思明区快捷筛选和厦门 fallback SVG；
- 首次加载使用中国大陆全境 viewport，之后恢复上次 viewport；
- 高德 Map 实例上报 `moveend/zoomend` 后按 bbox 查询；
- Marker 聚合、点击浮窗/侧浮层、Mobile Bottom Sheet；
- 浮窗显示代表图、名称、类型、地址、特色、关键菜品/体验、来源数、用户状态和详情按钮；
- 提供搜索、长按/添加地点、隐藏/删除/恢复入口；
- “查看详情”进入 `/places/:placeId`，返回恢复地图视野和当前浮窗。

## 测试

- 首屏无任何默认城市参数或文案；
- 全国 pan/zoom/bbox/cluster；
- PC 浮窗与 Mobile Sheet；
- 用户 Marker 新增、软删除、恢复；
- 自动 Marker 隐藏不删除 Source/Evidence；
- 同一 `place_id` 的列表、浮窗和详情数据一致。

---

# 15. Work Package 10：地图资源设置（已实施）

设置页新增：

- 高德 JS API Key；
- 高德 Security Code；
- 高德 Web 服务 Key；
- 域名白名单提示；
- 三项配置状态与真实测试；
- 地图 bootstrap 诊断。

Web 服务 Key 与 Security Code 经 SecretStore 保存；JS Key 可作为普通设置。地图通过受认证的 bootstrap API 获取客户端必需配置，不继续只依赖 Vite 构建变量。UI 必须提示 JS 端配置在浏览器运行时可见，安全边界依赖高德域名白名单，而不是宣称完全保密。

---

# 16. Work Package 11：UI（已实施）

UI 图确认已完成，以下页面决策已落地：

- 复用 Content Detail 还是新增 Video Note Detail；
- 地点列表是独立页面还是 Map 的列表模式；
- Place Detail 如何呈现归纳笔记、来源冲突和时间 Evidence；
- PC 和 Mobile 长笔记如何导航；
- Map 返回状态和 Video Note 阅读位置如何恢复。
- 地图浮窗、Marker 编辑和设置表单在 PC/Mobile 的布局；详细设计稿见 `design/ui/v0.4/`。

无论选择哪种页面结构，以下不变：

- `/places/:placeId` 是 canonical Place Detail；
- 视频笔记地点、列表和 Marker 使用同一 `place_id`；
- Marker 只加载 preview，不携带完整 Place Note；
- 地图无默认城市，使用全国 viewport；
- 用户 Marker 与 AI Marker 有可识别但不过度抢眼的状态差异；
- 时间码可以返回视频笔记章节或原片；
- AI 归纳、作者观点和来源事实视觉区分；
- `PARTIAL_SUCCESS/NEEDS_USER` 有明确修复入口；
- 前端不接触 Cookie/API Key 明文。

---

# 16A. Work Package 12：视频笔记阅读体验 v0.4.2（待实施）

## 后端

- `CORRECT_TRANSCRIPT / VALIDATE_CORRECTION`；
- Segment raw_text/corrected_text、校对状态、模型、置信度和原因；
- 全覆盖、顺序、ID 与时间码校验；
- 主旨目录 `heading/thesis/section_id/start_ms`；
- Section summary/bullets/place refs/稳定 anchor；
- corrected/raw Transcript API 与 TXT 导出；
- Screenshot caption/content_role/section_id。

## 前端

- Hero 使用真实 CoverAsset，缺省时为空/收起；
- 摘要、主旨目录、按时间线详述依次排列，地点候选与完整转写放文章底部；
- 地点/Transcript/目录/截图时间码页面内跳转、聚焦与高亮；
- 截图以 220–280px 缩略图放在对应 Section 文字侧面，移除默认独立宫格/全宽 talking head；
- contain Lightbox、前后切换、Escape/遮罩关闭和焦点恢复；
- “导出 TXT”改用统一次级按钮并默认导出校对稿；
- PC/Mobile/键盘与历史锚点回归。

## 约束

- 页面正文不是原始转录堆叠；
- AI 校对不改变 Segment ID、顺序和时间码，不新增事实；
- 目录不得输出泛化套话；
- 普通 talking head 或“章节起始帧”不自动视为关键截图；
- 具体契约以 `video/VIDEO_NOTE_READING_EXPERIENCE_V042_SPEC.md` 为准。

---

# 16B. Work Package 13：视频笔记列表封面与 CTA v0.4.3（待实施）

## 后端

- VideoCoverAsset 数据与迁移；
- `FETCH_COVER` 步骤；
- Bilibili cover URL HTTPS/host/SSRF/MIME/文件头/尺寸/字节校验；
- 原图 SHA-256 存储与 672×378 WebP；
- 本地封面图片 API、ETag 和 immutable cache；
- Video Note List cover ViewModel；
- 封面失败占位但不阻塞 Note。

## 前端

- CTA 改为“添加视频链接”；
- 复用 40px/14px 全局 Primary Button；
- 列表真实封面 16:9、object-fit cover、lazy loading；
- 时长徽标、skeleton、失败占位和 alt；
- PC/Mobile/键盘回归。

## 参考

借鉴 `lanyeeee/bilibili-video-downloader` commit `1254c6bf...` 的 `pic/cover → HTTPS GET → status/Content-Type → ext → bytes → local file` 方法，不引入其 Rust/Tauri 任务系统。直接移植实质代码时补充 MIT Notice。完整契约见 `video/VIDEO_NOTE_LIST_V043_SPEC.md`。

---

# 16C. Work Package 14：步骤级续跑 v0.4.4（源码已实施）

- Step Artifact Manifest 和 24h Replay Cache；
- `replay-options / retry-from-step / retry-full`；
- 上游 REUSED、失败/下游 RETRYING、旧输出 INVALIDATED；
- TTL 到期、输入/版本变化和 lease 门禁；
- 任务详情/日志“从错误步骤继续”、剩余时间和完整重跑；
- `job.step_replay.*` 审计和多 Attempt；
- 不允许前端任意 from_step。

完整契约见 `jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md`。

---

# 16D. Work Package 15：视频笔记删除 v0.4.4（已实施并通过 API 测试）

- 列表/详情 `…` 菜单；
- 共用 Note Delete Service/API；
- 删除 Note/Version/Section/TOC/Content 投影；
- 保留 Source/Asset/Cover/Transcript/Place/Evidence；
- 活跃 Job 门禁和不可恢复确认；
- 清理专属派生文件、缓存刷新、旧 URL 已删除状态和审计。

完整契约见 `video/VIDEO_NOTE_DELETE_V044_SPEC.md`。

---

# 17. 建议提交与执行顺序

不要一次提交全部功能。建议：

1. `feat(video): add domain schema and migration`；
2. `feat(video): add bilibili url metadata and subtitle resolver`；
3. `feat(video): add yt-dlp audio and timestamp asr fallback`；
4. `feat(notes): add deepseek chunked video note generation`；
5. `feat(travel): add typed place extraction and evidence`；
6. `feat(travel): add poi resolution and place note versions`；
7. `feat(api): expose video and place note resources`；
8. `feat(ui): implement approved video note and place flows`；
9. `feat(video): add evidence-bound representative screenshots`；
10. `feat(travel): add granular place briefs and amap name correction`；
11. `feat(map): add china viewport clustering and marker lifecycle`；
12. `feat(settings): add amap runtime configuration and diagnostics`；
13. `feat(ui): implement approved map popup and marker management`；
14. `test(video): add screenshot map recovery security and real-url acceptance`；
15. `docs(video): record final implementation and third-party notices`。

每个提交都必须保持已有招聘、文件上传、地图和认证测试通过。

---

# 18. Agent 每阶段输出格式

Agent 完成一个 Work Package 后必须输出：

```text
Work Package
完成内容
未完成内容
修改文件
新增迁移
新增/变更 API
第三方代码来源
新增测试
运行命令
测试结果
真实链接验收结果
安全检查
已知风险
下一 Work Package
```

不得只写“已经实现”。若真实 Bilibili 或 DeepSeek 因外部条件没有验收，必须明确写“仅 Fixture 通过”，不得宣称端到端完成。

---

# 19. 验证命令

后端：

```bash
.venv/bin/ruff check backend/src backend/tests
.venv/bin/pytest backend/tests
```

迁移：

```bash
cd backend
../.venv/bin/alembic upgrade head
../.venv/bin/alembic downgrade -1
../.venv/bin/alembic upgrade head
```

前端（UI 阶段）：

```bash
pnpm --dir frontend verify
```

文档：

```bash
python3 scripts/build_complete_project_spec.py
python3 -m json.tool "dev docs/manifest.json"
git diff --check
```

运行命令前确认 Node.js 满足 Vite 要求并使用项目 `.venv`。测试不得依赖实时 Bilibili/DeepSeek；CI 使用冻结 Fixture，真实 URL/API 只做显式手工验收。

---

# 20. 禁止事项

- 不覆盖或清理当前未提交的无关改动；
- 不为视频功能重写整个现有架构；
- 不使用 FastAPI BackgroundTasks 执行长任务；
- 不把 BiliNote 整仓复制进项目；
- 不遗漏 MIT notice；
- 不把 Cookie/API Key 写入 SQLite 明文或日志；
- 不绕过平台权限或验证码；
- 不下载无上限或原始最高画质视频；为截图只能下载受配置限制的最低必要视频流；
- 不把 AI Note 当事实 Evidence；
- 不让 LLM 生成 POI 坐标；
- 不使用 `(0,0)` 代表未解析 Place；
- 不静默覆盖 Note Version；
- 不在 UI 图确认前实现新页面；
- 不在没有真实验收时宣称完整支持 Bilibili。
- 不在地图请求、标题、fallback 或路线创建中硬编码厦门或其他默认城市；
- 不把 Marker 删除等同于删除 Place、Source 或 Evidence；
- 不把转写名称校正后覆盖 `raw_name`；
- 不把高德客户端配置宣称为浏览器不可见的绝对 Secret。

---

# 21. 最终 Definition of Done

只有同时满足以下条件才算视频 AI 笔记功能完成：

1. 用户粘贴 Bilibili/BV/短链/分 P 后立即得到持久 Job；
2. 字幕优先路径与无字幕 ASR fallback 均通过；
3. DeepSeek 生成带时间码、版本化的完整 AI Note；
4. 长字幕分块和 checkpoint 恢复通过；
5. 主要章节及地点拥有清晰、去重、带时间码的代表性截图；
6. 餐馆、景区、街区等细粒度地点结果全部有 Transcript Evidence；
7. 高德保留 raw/canonical 名称校正链，Confirmed 地点进入列表和地图，同一 POI 不重复；
8. 中国大陆全境地图无默认城市，bbox、zoom、聚合和 viewport 恢复通过；
9. Marker 浮窗可看简介并进入详情；用户 Marker 新增、隐藏、删除和恢复通过；
10. Place Note 聚合多个来源并保留冲突；
11. 视频笔记、列表和 Marker 进入同一 Place Detail；
12. 高德三项配置可在设置中填写、测试和诊断；
13. Worker 重启、重试、取消和部分成功行为通过；
14. Cookie、API Key、SSRF、临时文件、截图资产和外部调用审计通过；
15. BiliNote MIT notice 和移植记录完整；
16. 后端、前端、迁移、文档验证全部通过；
17. PC/Mobile 实际 UI 与已确认设计图一致；
18. 至少一个有字幕和一个无字幕的真实 Bilibili 样本完成手工验收。
19. 纯 URL、标题/分享文案中的唯一 URL、普通文本和多 URL 歧义均按 Input Normalizer 契约处理，丢弃文字不进入下游。
20. 全部可用 Transcript Segment 拥有 corrected_text 或明确 Review 状态，raw_text 仍可审计。
21. 地点候选与完整转写位于文章最底部；Hero 缺少 CoverAsset 时为空/收起。
22. 主旨目录具体且可跳转；正文是 AI 校对后的时间线提纲/详述，不是原始转写堆叠。
23. 截图嵌入对应 Section，关键内容选择、caption 和 Lightbox 交互通过。
24. 时间码页面内跳转、聚焦、高亮和历史恢复通过。
25. TXT 按钮符合统一视觉，默认导出完整 corrected Transcript。
26. Video Note List 使用本地真实封面、16:9 Card 和时长徽标，失败占位不抖动。
27. 顶部主按钮为“添加视频链接”，PC/Mobile 尺寸符合统一 Button Token。
28. ERROR 步骤在中间产物有效期内只执行当前及下游，上游显示 REUSED；过期后只能完整重跑。
29. 视频笔记列表和详情提供同一删除能力，并保留共享 Source/Transcript/Place/Evidence。
