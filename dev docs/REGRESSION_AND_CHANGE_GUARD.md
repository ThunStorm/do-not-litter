# 回归基线与变更防覆盖清单

更新日期：2026-09-03。本文只维护已确认需求的保护清单。改动前按能力关键词读取相关条目与契约，不默认通读所有链接；不能以原型截图、静态数据或“构建成功”替代真实实现。

## 1. 变更规则

1. 先定位所属能力，再改代码；不以重写页面的方式覆盖已有可操作功能。
2. 改动数据模型时必须添加 Alembic 迁移并验证 `alembic current`；不得改动历史 Source、Claim、Evidence 或 Note 来实现地图隐藏。
3. 改动 Job、模型、视频或地图链路时，必须同时更新任务步骤、可读日志、API、UI 与验收用例。
4. 代码工作包先目标验证、结束时一次全量后端/前端验证。明确请求的前端改动按根 `AGENTS.md` 的持续授权在备份、保存点及回退准备后直接部署并做生产 Browser 验收；需要重载服务时先确认无活跃 Job/lease，不能中断用户任务。其他部署仍按任务授权边界处理。纯文档只做文档一致性检查，不跑业务全量、不重启服务。
5. `COMPLETE_PROJECT_SPEC.md` 仅由构建脚本的 source set 生成；这些源文档或清单变化后运行 `.venv/bin/python scripts/build_complete_project_spec.py`。不需要读取合订本，也不因只更新历史/交接而重建。

## 2. 已冻结的功能基线

| 能力 | 不可回退要求 | 契约 / 主要实现 |
| --- | --- | --- |
| 部署与局域网 | 唯一后端为 Mac mini；4 位配对码显眼展示；Cookie 会话刷新不应重新要求配对；服务状态来自真实 API/Worker/SQLite | `operations/DEPLOYMENT_OPTIONS.md`、`jobs/MOBILE_SESSION_DIAGNOSTICS_AND_JOB_CONTROL_SPEC.md`、`services/auth.py` |
| 捕获与本地处理 | URL、正文、DOCX、PDF、XLSX、图像 OCR、音视频均可进入 Job；Whisper.cpp、FFmpeg 与 OCR 状态必须是探测结果 | `product/PRODUCT_REQUIREMENTS.md`、`ai-gateway/AI_RUNTIME_AND_PROVIDERS.md` |
| 模型设置 | 用户可维护任意 Provider/模型库；预设仅帮助填写；主/备用从已存模型选择；草稿可真实测试；已保存模型一键与单项共用Worker队列，同供应商/入口FIFO、独立最多三组并行，跨进程节流/429冷却/去重/取消及晚结果fence保留；默认超时 300 秒 | `ai-gateway/MODEL_AND_RETENTION_UI_SPEC.md`、`operations/RUNTIME_MONITOR_AND_MODEL_PRESETS_SPEC.md` |
| AI Gateway 契约 | Model Profile 显式保存 location/modalities/capabilities；Stage 参数仅白名单；新 Job 按提交时快照固定路由、Profile、Stage Policy、Prompt/领域上下文与 AI 参数，普通/完整/步骤重跑入队时自动刷新原模型最新可调参数，其余沿用原快照；身份变更/删除/禁用重跑安全拒绝，模型/入口身份和提交路由保留，不借用其他模型参数；执行参数入队后不追随全局变化，各阶段能力门禁重新核对同身份模型最新已保存评估并审计，历史执行快照可追溯，累计预算不重置，Secret 不进 Job；笔记失败后的显式恢复操作仅覆盖本 Job 的笔记模型并审计，完整重跑清除该覆盖；没有快照的历史任务保持兼容路由，`AUTO/LOCAL_ONLY/LOCAL_FIRST/REMOTE_FIRST/REMOTE_ONLY` 语义不得回退 | `ai-gateway/05-job-policy.md`、`ai/policies.py` |
| 阶段分批/请求时限 | v2显式Stage超时覆盖模型默认，阶段与Job剩余时间仍硬限制；旧快照无标记保留取小及旧分批规则，明确重跑生成新版执行快照，历史不回填；预算预览只读不调用模型，校对批次统一Stage入口且旧值逐项回退 | `ai-gateway/04-stage-policy.md`、`ai/stage_limits.py`、`tests/test_stage_limits.py` |
| AI Gateway 质量与上下文 | 干净平台字幕不得无条件全文送模；长转写只传候选或 Facts，不能多阶段重复全文；Domain Context 仅低优先级增强，不能覆盖 Evidence、Schema 或安全契约；text-only Profile 不得绑定视觉 Stage | `ai-gateway/AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md`、`services/video_support.py` |
| Qwen 逐字对齐与校对预算 | 高比例逐字对齐须在新 Transcript 物化前合并为语句 Segment，保留原始时间码；不得原地修改历史 Segment。批次经验按入口/账户/有效参数隔离，旧模型名经验不借用；单批尝试上限不误作整个阶段批次数，校对/地图/笔记按正常及拆分批次分配额度；校对预算按实际批次预估，实测剩余工作超墙钟上限时提前收口，请求 timeout 受剩余时长约束 | `scripts/qwen_asr_runner.py`、`services/video_support.py`、`ai/budget.py` |
| 证据地图截断恢复 | `LOCAL_FIRST` 首次本地输出截断后先拆分；存在已配置备用模型时，子块或预计超出剩余阶段预算的后续块走备用路由，保持原 Segment Evidence、Schema 校验、调用审计与缓存，不重复扩大本地慢请求；正文字符 Hint 不得漏算分块结构开销 | `services/grounded_map.py`、`ai/gateway.py` |
| 笔记归纳恢复 | `GLOBAL_SYNTHESIS` 是内部阶段契约；版本有效的 `FAIL` 仍拦截，旧版笔记小样/过期结果为未验证而非通过。显式阶段选定或非AUTO首选槽位留空继承通用主模型可尝试 `NOT_TESTED`，不扩大自动候选/备用声明；保存/执行/恢复统一判定，同模型续跑刷新最新评估；每个阶段重新核对同身份模型最新已保存能力结果，执行参数与历史快照保留。小样允许合并/拆分章节，严格验证来源和事实证据，歧义不误判失败。DeepSeek 笔记默认关闭思考，保留原 JSON/Evidence/预算；续跑仍须 lease 释放、上游有效且无待执行完整重跑 | `ai-gateway/01-architecture-models.md`、`services/video_support.py`、`services/job_replay.py`、`jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md` |
| 请求优化与能力诊断 | 短 ID 仅在模型边界，Snapshot/内容/编译器/投影/映射绑定缓存；原文/quote 不变，未知或越界引用拒绝，校对只返回 target_ids；不静默截尾；格式 smoke 不授业务 PASS，模型修复默认关闭；解析质量与回退/重试/缓存分开，等待后复核 Deadline；POI 空证据/跨来源不得自动确认，合成字节收益不冒称真实 Token/质量 | `ai/request_compiler.py`、`benchmark/RELEASE_ACCEPTANCE.md` |
| AI Gateway 稳定性 | 精确 Cache hit 不重复调用 Provider；`force_regenerate` 绕过命中并保留结果链；本机 ASR/文本/视觉/模型测试必须跨 API/Worker 进程串行；本地模型测试不论直连/入口，每子调用结束后至少5秒，配置/RPM更长取更长，共享完成时间并统一分组锁→硬件锁顺序；LOCAL/REMOTE Token 分账只依据审计路由位置；Cache hit 不计模型调用或预算；Ollama `keep_alive: 0` 与本地重任务低并发不得回退；未经真实 E2E 与 Benchmark Gate 不得宣称生产验证 | `ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md`、`ai/resource_manager.py`、`ai/budget.py`、`ai-gateway/AI_RUNTIME_AND_PROVIDERS.md` |
| Ground Map 局部 ID 恢复 | 仅无反向引用的缺省/重复 Claim ID 可确定性重编号，保留全部事实与原句/归属；实体/单元冲突、非法条目、越界引用仍拒绝，缓存命中重新校验且修复血缘幂等。结构错误只记安全路径/编号哈希，纠错不改变显式0、备用语义或预算；不回写旧任务、不冒称语义质量通过 | `ai/structured_ids.py`、`ai/request_compiler.py`、`ai/json_recovery.py`、`tests/test_ground_map_id_recovery.py` |
| 可取消本地路由 HTTP | LOCAL_ROUTER 的 `trust_env=False` 在异步路径必须配置到 AsyncClient 构造函数；成功请求和 DIRECT/LOCAL_ROUTER 取消均须通过离线回归。客户端取消不等于上游停止，Ollama 显式清理缺口不得被健康或 Mock 测试抹掉 | `providers/llm.py`、`tests/test_local_router_contract.py`、`tests/test_job_runtime_optimization.py`、`ai-gateway/AI_RUNTIME_AND_PROVIDERS.md` |
| 任务控制 | 当前标记只属于运行中的当前 JobStep；终态不固定高亮最后一步；时间线按 Pipeline 排序、阶段中文化并显示步骤用时；普通步骤 90 秒、LLM 步骤 500 秒预警，900 秒才终止；模型/重试/资源锁等待与 ASR 每 250ms 观察取消，ASR 每 30 秒报告等待，确认停止前不开始重跑 | `jobs/MOBILE_SESSION_DIAGNOSTICS_AND_JOB_CONTROL_SPEC.md`、`jobs/TASK_SUMMARY_AND_PARTIAL_SUCCESS_SPEC.md`、`jobs/TASK_STATUS_AND_BEIJING_TIME_SPEC.md` |
| Token 用量 | 实测字段与本地字符估算/未知独立；缺省不冒充 0，失败输出不编造、Cache 不重复计消耗；估算参与预算，历史 Audit 只读推导不回填；超时不重复相同模型请求，备用受路由/能力/预算门禁约束 | `ai/token_usage.py`、`operations/LOGGING.md#41-token-口径2026-10-08` |
| Worker 存活与完整重跑 | 全局 Worker 心跳独立于同步 Pipeline；Job 活动只反映真实阶段/batch；长模型取消在请求边界停止后续批次，429/5xx 不放大请求；取消 lease 释放后 `CANCELLED` 也可完整重跑 | `operations/RUNTIME_MONITOR_AND_PROVIDER_SWITCH_V06_SPEC.md`、`jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md`、ADR-030 |
| 终态与时间 | 终态不显示预估；展示层强制北京时间，持久化 ISO 时间仍保持 UTC | `jobs/TASK_STATUS_AND_BEIJING_TIME_SPEC.md` |
| 运维 | CPU/内存/磁盘与 Worker 心跳为 SQLite 持久化快照；内存百分比使用可回收页口径；日志支持筛选、关联 Job、分页与脱敏 | `operations/OPERATIONS_UI_SPEC.md`、`operations/LOGGING.md` |
| 步骤续跑 | ERROR/CRITICAL 事件先查询 Replay Options；Artifact 有效时从失败步骤继续，上游 REUSED、当前/下游顺次执行；过期后只允许完整重跑；日志页不直接改步骤 | `jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md`、`operations/LOGGING.md`、ADR-026 |
| 存储与日志生命周期 | 启动根/锁统一；缺卷/实例不符拒绝建空库；搬迁保持旧副本，放行后不回旧库；日志只删已登记封卷，gzip核验后删原件；转录180天与永久资料独立 | `operations/STORAGE_AND_LOG_LIFECYCLE.md`、`test_storage_lifecycle.py`、`test_storage_api.py` |
| 地点时节与作者路线 | 背景零推荐加权，活动/路段限制不关闭区域，跨年/用途/精度有据；新作者路线仅绑定当前版本、逐字证据/站序校验、原词待核、非导航；个人清单独立、旧导出兼容、历史仅dry_run；云南P0_CRITICAL必跑 | `product/TRAVEL_FOOD_PIPELINE.md` 10.26、`test_yunnan_multiregion_travel_golden.py` |
| 作者地点态度 | 整体态度需逐字证据/主体/版本，局部限制不建地点；合并顺序无关，负向/存疑自动POI零调用，确认位置/个人偏好不改作者；负向来源不被体验筛选吞掉，旧证据不回写；默认无态度标签，仅负向名称标记 | `product/TRAVEL_FOOD_PIPELINE.md` 10.25、`services/recommendation_intent.py`、`test_recommendation_intent.py` |
| 内容保留 | 终态任务和内容可删除；删除清理专属关联和无来源/人工记录的自动地点，不破坏共享来源、地点、路线或证据；密钥只进 Keychain/Secret Store | `ai-gateway/MODEL_AND_RETENTION_UI_SPEC.md`、`architecture/SECURITY_PRIVACY.md` |
| 视频 v0.3 | Bilibili 元数据/字幕优先/受控音频/Whisper 转写；同一视频的每次提交产生独立 Note/Content/Transcript Version，重跑只给所属 Note 增新版本；Place 按 Provider POI ID 复用，地点与笔记证据不跨任务串联；章节、时间码、POI、Place Note 和失败/部分成功均为真实数据 | `video/04-jobs-data-api.md`、`services/video_pipeline.py` |
| Bilibili 登录与字幕 | 登录只走站内二维码与 Keychain；登录失效必须进入 `NEEDS_USER` 并提供可用的续跑/非核心跳过选择；字幕 CDN 使用用途级 HTTPS Host Policy，安全支持官方子域；人工中文、AI 中文、其他语言依次尝试，单轨失败不得击穿整个 Job。AI/自动字幕不可单独成为权威 Transcript，必须保留 BV/CID、轨道与非敏感哈希审计并回退 ASR；生成 Note 前校验来源身份、验证状态与时间轴 | `video/VIDEO_AI_NOTE_PIPELINE.md` 4.4–4.7、`core/url_policy.py`、`services/video_pipeline.py` |
| 视频 v0.4 截图 | 笔记先综合元数据与 Transcript；`PLAN_SCREENSHOTS → DOWNLOAD_VIDEO_FOR_FRAMES → EXTRACT_SCREENSHOTS → MATERIALIZE` 为显式步骤；3–12 张全文截图、主要地点优先，绑定章节/地点候选/Segment/时间码；过滤黑帧、曝光异常、低清晰度和重复帧 | `video/VIDEO_AI_NOTE_PIPELINE.md` 4.12–4.15、`services/video_screenshots.py` |
| 地点笔记与确认同步 | 多地点笔记按已验证地点/主题组织，跨包合并但比较不广播；模型引用必须局限当前包，逐字引文与要点覆盖校验，缺项明确HYBRID；历史阅读投影不改版本/证据，旧anchor与截图可达；确认后跨页面通知/焦点刷新/前台15秒兜底，定位入口清旧筛选且选中Marker从聚合拆出且原生层级更高、PC/Mobile预览避让并能实点，隐藏/删除边界保留 | `services/note_structure.py`、`services/video_support.py`、`features/places/PlaceReviewCard.tsx`、`lib/travelChanges.ts` |
| 视频 v0.4.2 阅读返工 | Hero 有真实封面、缺省为空；摘要/主体目录/正文优先，地点候选与完整转写放底部；默认使用 AI corrected Transcript；截图以侧排缩略图嵌入并支持 contain Lightbox；TXT 按钮使用统一视觉 | `video/VIDEO_NOTE_READING_EXPERIENCE_V042_SPEC.md` |
| 视频 v0.4.3 列表封面 | 主按钮为“添加视频链接”并使用统一 40px/14px Token；Card 展示本地持久真实封面、16:9 cover 和时长徽标；封面失败只显示占位，不阻塞 Note | `video/VIDEO_NOTE_LIST_V043_SPEC.md` |
| 视频笔记删除 | 列表/详情共用删除；删除 Note/Version/Section/TOC/Content 投影，保留共享 Source/Asset/Cover/Transcript/Evidence及共享/人工地点，清理本Note所有版本生成关联和孤立自动地点；活跃Job/lease阻止删除 | `video/VIDEO_NOTE_DELETE_V044_SPEC.md` |
| 地点与 POI | 保留 `raw_name`，人工改名仅更新 `suggested_name`；高德确认写 `canonical_name`；`REFERENCE_ONLY`/`SKIP` 不进入POI；推荐区域或景区可在严格门禁后以 Destination 代表点上图，政府/游客中心不是 Place 本体；同名区域按行政链隔离，歧义不自动确认，拒绝项不再显示且可撤销 | `product/TRAVEL_FOOD_PIPELINE.md`、`services/video_support.py` |
| POI并发与代表点 | 人工确认先于意见门禁保护；搜索/确认/拒绝原子revision且所属运行Job拒绝编辑；地域不跨提交/版本，引用和无效证据不传播；满页候选为不完整；代表点绑定来源/目标/证据，冲突先于bbox判定，Provider身份大小写归一且保留删除墓碑 | `benchmark/POI_RESOLUTION_CODE_REVIEW_REPORT.md`、`test_poi_audit_regressions.py` |
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

本轮新增回归：笔记归纳首包Provider失败且无任何有效AI章节时暂停，不把确定性提纲当作模型成功；历史DETERMINISTIC_FALLBACK或HYBRID部分降级任务可从GENERATE_AI_NOTE显式恢复，普通部分成功仍不复跑清理步骤。分包按有效模型输出容量估算，保留真正截断后的二分及同入口经验。厂商HTTP配额/限流、本地断路保护、思考/正文预算原因分开记录，不用应用OPEN状态推断厂商熔断。

保护请求预约与实际发出分别核对间隔；取消检查耗时计入墙钟等待，不能额外放大配置间隔；等待后复核取消/截止时间。手动探测统一关闭思考，由实际入口映射协议，LOCAL_ROUTER继续按接口契约省略。归纳保留时间/限制在笔记中的事实表达，使用已验证地点窗口，不重复提取地点窗口结构；地点提取与窗口校验契约不变。

标题时间必须区分 TITLE_METADATA/TITLE_CONTEXT 与转写 SOURCE_FACT，不伪造 Segment；正文时间/限制优先，比较/否定/记录/范围不明不继承。Semantic Claim 先按 subject_entity_ids 绑定地点，无效或多地点歧义不能 Segment 广播；派生窗口重放保持唯一并保护人工窗口。标题/解析版本必须进入 Map 缓存身份，Prompt 分片保持完整系统守卫；应用结果缓存不冒充上游前缀缓存。契约见 [标题时间证据](video/TITLE_TEMPORAL_EVIDENCE.md)。

2026-10-29 经用户确认新增THEME_CONTEXT推荐关系：只对作者明确主题、当前块内有逐字成员证据且通过主体/ContentUnit/连续同Snapshot/主题边界门禁的PRIMARY/SECONDARY推荐对象投影；OPTIONAL不升级推荐，比较/中转/背景/整体否定不继承。来源注册表随请求实际提供并还原短ID，新Note固定Artifact身份；旧NULL不猜绑，GET不回写。暑假/寒假保持假期语义，不命中精确月份；历史客流气候和既有SEMANTIC_CONTEXT仍零推荐加权。局部活动、日期与道路限制独立保留，Place/Destination展示、筛选与v2导出共用有效时间投影。

2026-10-21 JSON恢复：定点错误行列/限长用户数据+原始完整Evidence，同模型有界重答，重验Schema/ID/引文/覆盖；不猜修双引号、不以失败输出作事实、不向无历史接口添加assistant轮次。修复上下文超输入预算不得发出，备用仍用原始请求；取消、时限及总尝试硬门禁保持。审计只记错误位置/哈希和恢复血缘，不落响应全文；新逻辑调用不继承旧修复状态。

地图定位点阅读（2026-10-23）：浮窗先显示地点、适合时节和有据简短理由，路线收起，管理/编辑在详情保存。主地点允许同版本PLACE_GUIDE完整单元投影；跨单元共同季节须按旅行领域10.24的同Note版本/重复地点/共同景观/无冲突门禁，具体日期时刻不广播，历史日期不升级年度最佳，地图筛选和详情使用相同有效窗口。保留旧记录与修订号冲突保护，PC/Mobile验证编辑草稿和保存刷新。

2026-10-24 地图直读：浮窗外层展示有据自然语言时节、限制和看点；不以内部适宜度/偏好分代替业务说明。地点级NOT_RECOMMENDED进入人工复核且自动POI调用0；天气级否定只显示条件限制。数字聚合点击放大并列成员，仅同一Note版本可展示有据共同看点；成员散开或聚合失效立即关闭，不保留过期列表。

2026-10-25 地点阅读：展示层去除视频叙述外壳必须保留否定、日期、程度和不确定限定；来源/继承关系/原句与超链接收进查看更多，不能删除依据。详情业务信息优先，空资料不占大区块，元数据/历史/管理次级收起；按需读取历史，编辑保存与聚合散开关闭继续回归。

2026-10-26 详情阅读不可整体折叠：关联笔记/时间依据/来源默认可读，时间锚点仍能定位；资料/历史维持紧凑辅助层级，历史独立按需加载，管理按钮直接可达。PC要点卡片同行等高等分，Mobile边缘对齐且长内容不裁切；高德入口沿用共享按钮水平留白，业务主操作不得被导航遮挡。

2026-10-26 底部操作/历史：五个状态偏好按钮须在同一底栏且不在正文重复；移动端不得换行/溢出/被导航遮挡。历史默认展开自动加载，保存后刷新，资料与历史都固定160px并内部滚动；长历史样例不得撑高辅助区或写入生产。


2026-10-29 封面来源与验收重放：COVER_TEXT独立Stage/Worker产物，默认仅本地OCR、视觉显式启用且绑定图片能力/有效参数；现行LOCAL_ROUTER不接受图片，接口能力未验不能冒称通过。日期与否定/多候选/区域质量检查失败保留待核，不阻塞正文；封面不造Segment、不由画面猜月份。成功证据按图片及内容身份不可变保存，失败15分钟缓存；GET只读，按哈希追溯原图。真实阶段与确定性重放分别计量，旧NULL不猜绑，Note/Section/Mention新版本不得覆盖旧身份。局部未归属限制保留原句待核，不做全城否定；清单关系恢复必须有明确原句/唯一主体与derivation，不按地理关系广播。

2026-10-29 审查回归：小字否定不得被大字推荐覆盖；冬季限制不能降级8月，明确日期与跨年窗口按交集判断；视觉关闭时探测等Profile运维变化不能打穿OCR/Map缓存，未触发视觉且内容相同时下游身份保持。新解析版本与显式强制重算仍允许必要失效，不能用压缩方案删除成员/否定/局部条件证据。
