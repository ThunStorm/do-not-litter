# 回归基线与变更防覆盖清单

更新日期：2026-09-03。本文只维护已确认需求的保护清单。改动前按能力关键词读取相关条目与契约，不默认通读所有链接；不能以原型截图、静态数据或“构建成功”替代真实实现。

## 1. 变更规则

1. 先定位所属能力，再改代码；不以重写页面的方式覆盖已有可操作功能。
2. 改动数据模型时必须添加 Alembic 迁移并验证 `alembic current`；不得改动历史 Source、Claim、Evidence 或 Note 来实现地图隐藏。
3. 改动 Job、模型、视频或地图链路时，必须同时更新任务步骤、可读日志、API、UI 与验收用例。
4. 代码工作包先目标验证、结束时一次全量后端/前端验证。部署是独立授权：需要部署时先确认无活跃 Job/lease，不能中断用户任务。纯文档只做文档一致性检查，不跑业务全量、不重启服务。
5. `COMPLETE_PROJECT_SPEC.md` 仅由构建脚本的 source set 生成；这些源文档或清单变化后运行 `.venv/bin/python scripts/build_complete_project_spec.py`。不需要读取合订本，也不因只更新历史/交接而重建。

## 2. 已冻结的功能基线

| 能力 | 不可回退要求 | 契约 / 主要实现 |
| --- | --- | --- |
| 部署与局域网 | 唯一后端为 Mac mini；4 位配对码显眼展示；Cookie 会话刷新不应重新要求配对；服务状态来自真实 API/Worker/SQLite | `operations/DEPLOYMENT_OPTIONS.md`、`jobs/MOBILE_SESSION_DIAGNOSTICS_AND_JOB_CONTROL_SPEC.md`、`services/auth.py` |
| 捕获与本地处理 | URL、正文、DOCX、PDF、XLSX、图像 OCR、音视频均可进入 Job；Whisper.cpp、FFmpeg 与 OCR 状态必须是探测结果 | `product/PRODUCT_REQUIREMENTS.md`、`ai-gateway/AI_RUNTIME_AND_PROVIDERS.md` |
| 模型设置 | 用户可维护任意 Provider/模型库；预设仅帮助填写；主/备用从已存模型选择；草稿可真实测试；默认超时 300 秒 | `ai-gateway/MODEL_AND_RETENTION_UI_SPEC.md`、`operations/RUNTIME_MONITOR_AND_MODEL_PRESETS_SPEC.md` |
| AI Gateway 契约 | Model Profile 显式保存 location/modalities/capabilities；Stage 参数仅白名单；没有新策略的历史任务保持旧路由，`AUTO/LOCAL_ONLY/LOCAL_FIRST/REMOTE_FIRST/REMOTE_ONLY` 语义不得回退 | `ai-gateway/AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md`、`ai/policies.py` |
| AI Gateway 质量与上下文 | 干净平台字幕不得无条件全文送模；长转写只传候选或 Facts，不能多阶段重复全文；Domain Context 仅低优先级增强，不能覆盖 Evidence、Schema 或安全契约；text-only Profile 不得绑定视觉 Stage | `ai-gateway/AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md`、`services/video_support.py` |
| AI Gateway 稳定性 | 精确 Cache hit 不重复调用 Provider；`force_regenerate` 绕过命中并保留结果链；本机 ASR/文本/视觉/模型测试必须跨 API/Worker 进程串行；LOCAL/REMOTE Token 分账只依据审计路由位置；Cache hit 不计模型调用或预算；Ollama `keep_alive: 0` 与本地重任务低并发不得回退；未经真实 E2E 与 Benchmark Gate 不得宣称生产验证 | `ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md`、`ai/resource_manager.py`、`ai/budget.py`、`ai-gateway/AI_RUNTIME_AND_PROVIDERS.md` |
| 任务控制 | 当前标记只属于运行中的当前 JobStep；终态不固定高亮最后一步；时间线按 Pipeline 排序、阶段中文化并显示步骤用时；普通步骤 90 秒、LLM 步骤 500 秒预警，900 秒才终止；取消协作释放 lease，确认前不允许重试 | `jobs/MOBILE_SESSION_DIAGNOSTICS_AND_JOB_CONTROL_SPEC.md`、`jobs/TASK_SUMMARY_AND_PARTIAL_SUCCESS_SPEC.md`、`jobs/TASK_STATUS_AND_BEIJING_TIME_SPEC.md` |
| Worker 存活与完整重跑 | 全局 Worker 心跳独立于同步 Pipeline；Job 活动只反映真实阶段/batch；长模型取消在请求边界停止后续批次，429/5xx 不放大请求；取消 lease 释放后 `CANCELLED` 也可完整重跑 | `operations/RUNTIME_MONITOR_AND_PROVIDER_SWITCH_V06_SPEC.md`、`jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md`、ADR-030 |
| 终态与时间 | 终态不显示预估；展示层强制北京时间，持久化 ISO 时间仍保持 UTC | `jobs/TASK_STATUS_AND_BEIJING_TIME_SPEC.md` |
| 运维 | CPU/内存/磁盘与 Worker 心跳为 SQLite 持久化快照；内存百分比使用可回收页口径；日志支持筛选、关联 Job、分页与脱敏 | `operations/OPERATIONS_UI_SPEC.md`、`operations/LOGGING.md` |
| 步骤续跑 | ERROR/CRITICAL 事件先查询 Replay Options；Artifact 有效时从失败步骤继续，上游 REUSED、当前/下游顺次执行；过期后只允许完整重跑；日志页不直接改步骤 | `jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md`、`operations/LOGGING.md`、ADR-026 |
| 内容保留 | 终态任务和内容可删除；删除不破坏共享来源、地点、路线或证据；密钥只进 Keychain/Secret Store | `ai-gateway/MODEL_AND_RETENTION_UI_SPEC.md`、`architecture/SECURITY_PRIVACY.md` |
| 视频 v0.3 | Bilibili 元数据/字幕优先/受控音频/Whisper 转写；AI 笔记、章节、时间码、地点候选、POI、Place Note 和失败/部分成功均为真实数据 | `video/VIDEO_AI_NOTE_PIPELINE.md` 1–4.11 |
| Bilibili 登录与字幕 | 登录只走站内二维码与 Keychain；登录失效必须进入 `NEEDS_USER` 并提供可用的续跑/非核心跳过选择；字幕 CDN 使用用途级 HTTPS Host Policy，安全支持官方子域；人工中文、AI 中文、其他语言依次尝试，单轨失败不得击穿整个 Job | `video/VIDEO_AI_NOTE_PIPELINE.md` 4.4–4.5、`core/url_policy.py`、`services/bilibili_auth.py` |
| 视频 v0.4 截图 | 笔记先综合元数据与 Transcript；`PLAN_SCREENSHOTS → DOWNLOAD_VIDEO_FOR_FRAMES → EXTRACT_SCREENSHOTS → MATERIALIZE` 为显式步骤；3–12 张全文截图、主要地点优先，绑定章节/地点候选/Segment/时间码；过滤黑帧、曝光异常、低清晰度和重复帧 | `video/VIDEO_AI_NOTE_PIPELINE.md` 4.12–4.15、`services/video_screenshots.py` |
| 视频 v0.4.2 阅读返工 | Hero 有真实封面、缺省为空；摘要/主体目录/正文优先，地点候选与完整转写放底部；默认使用 AI corrected Transcript；截图以侧排缩略图嵌入并支持 contain Lightbox；TXT 按钮使用统一视觉 | `video/VIDEO_NOTE_READING_EXPERIENCE_V042_SPEC.md` |
| 视频 v0.4.3 列表封面 | 主按钮为“添加视频链接”并使用统一 40px/14px Token；Card 展示本地持久真实封面、16:9 cover 和时长徽标；封面失败只显示占位，不阻塞 Note | `video/VIDEO_NOTE_LIST_V043_SPEC.md` |
| 视频笔记删除 | 列表/详情共用删除；删除 Note/Version/Section/TOC/Content 投影，保留共享 Source/Asset/Cover/Transcript/Place/Evidence；活跃 Job 阻止删除 | `video/VIDEO_NOTE_DELETE_V044_SPEC.md` |
| 地点与 POI | 保留 `raw_name`，人工改名仅更新 `suggested_name`；高德确认写 `canonical_name`；歧义进入 Review，拒绝项不再显示且可撤销，不能生成 Confirmed Marker | `product/TRAVEL_FOOD_PIPELINE.md`、`services/video_support.py` |
| 全国地图 | 首次中国大陆全境、之后恢复 viewport；按 bbox + zoom 查询且低 zoom 聚合、放大后直出独立 Marker；不得恢复厦门/思明区默认参数、标题、静态伪地图或路线默认城市 | `video/VIDEO_AI_NOTE_PIPELINE.md` 4.16、`MapOverviewPage.tsx` |
| Marker 生命周期 | 自动 Marker 删除仅隐藏投影；用户 Marker 软删除可恢复；绝不删除 Place、Source、Claim、Evidence、Place Note；浮层展示图片、地址、特色、来源数、状态和详情入口 | `architecture/API_DESIGN.md`、`map_marker_states`、`MapOverviewPage.tsx` |
| 高德设置 | JS API Key、Security Code、Web 服务 Key 分别保存/测试/诊断；前端已认证后用 bootstrap 读取，不在代码或构建变量硬编码 Key | `product/CONTROL_CENTER.md`、`SettingsPage.tsx` |
| UI 体系 | PC 是 CMS/运维优先，手机是日常入口；底部导航只放共性功能；外部来源图标单色；设计稿只作代码原生 UI 依据 | `design/ui/README.md`、`design/ui/v0.4/README.md` |

## 3. 回归矩阵

| 层 | 必跑检查 | 通过条件 |
| --- | --- | --- |
| 数据库（仓库） | `python -m alembic -c backend/alembic.ini heads` | 与当前迁移文件和 IMPLEMENTATION_STATUS.md 的仓库记录一致；历史迁移不可修改 |
| 数据库（生产） | `python -m alembic -c backend/alembic.ini current` | 仅记录实际读取的 production revision；迁移前确认无活跃 Job/lease、备份和完整性检查，不能由仓库 head 推断 |
| 后端 | `./.venv/bin/python -m pytest backend/tests -q` | 全量通过；至少覆盖局域网、超时、取消/重试、运行状态、地图聚合与 Marker 生命周期 |
| 前端 | 在 `frontend/` 运行 `pnpm run lint`、`pnpm test -- --run`、`pnpm run build` | 无 lint/类型/构建错误；地图画布和设置核心单测通过 |
| 服务 | `/api/status`、`/api/travel/map?zoom=4`、`/api/travel/map/bootstrap` | API/Worker/SQLite 为 RUNNING；返回中国全境 viewport 和聚合/配置字段 |
| GUI | PC 与手机宽度分别走概览、投递、内容、任务/详情、视频笔记/截图、地图/Marker、路线、全部设置、日志 | 无控制台错误、无横向溢出、状态与 API 一致；外部 Key 未配置时显示可行动诊断，绝不伪造底图或成功 |

## 4. 验证记录的唯一来源

自动验证与未闭环项见 [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)，生产采样见 [CURRENT_HANDOFF.md](CURRENT_HANDOFF.md)，逐版本证据见 history/IMPLEMENTATION_HISTORY.md。本文不再复制测试数量、生产版本和活跃任务数，避免多处漂移。Gateway 生产验收继续受 ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md 约束。
