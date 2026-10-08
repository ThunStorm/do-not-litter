# 实施历史（只按需追溯）

> 2026-09-03 从 IMPLEMENTATION_STATUS.md 分离；下文保留原逐版本正文。旧“当前/待实施/已验收”只适用于对应记录时点，不能覆盖 [当前状态](../IMPLEMENTATION_STATUS.md) 或 [现场快照](../CURRENT_HANDOFF.md)。裸文档路径以 dev docs/ 为基准。

## 已完成

- FastAPI、SQLite WAL、独立 Worker、Source/Snapshot/Segment/Claim/Evidence/Content/Job/Place/Route/Setting/Session/SystemEvent 数据模型和 Alembic 迁移；
- PC 首页显眼显示 4 位局域网配对码，可复制、轮换并撤销已有会话；5 次失败触发 10 分钟锁定，Session 使用 HttpOnly Cookie；
- `/api/status` 返回 Mac mini 的硬件、局域网地址、Worker 心跳与真实运行时检查；CPU、内存、数据盘由 API 每 30 秒采样并持久化到 SQLite，局域网访问与本机访问读取同一份快照；
- URL、正文、DOCX、PDF、XLSX、图片、音频与视频投递；图片使用 macOS Vision OCR，音视频由 FFmpeg 转为 16 kHz 单声道后交给 Whisper.cpp；
- 招聘与旅行确定性分类、招聘首批字段、旅行地点、Evidence 约束、GCJ-02 地图总览、标记逐点切换、地点详情和人工路线排序；
- DeepSeek、MiMo、Ollama Provider 配置、Keychain Secret 隔离和真实推理测试；
- PC 概览、内容、任务、来源审计、设置六分区、运行日志；手机首页、内容、投递、待办、我的、地图和路线全部为可操作 React 页面；
- JSONL 运行日志、Request ID、SQLite 审计事件、游标分页组合日志查询、详情抽屉和单条脱敏导出，设计与操作现统一见 `operations/LOGGING.md`；
- 任务页在 935px 窄桌面采用图标侧栏和两层任务行；任务详情显示当前步骤、持续时间、最后活动、Worker、实时连接状态与关联日志。Worker 长时间无活动的历史任务会明确标记为“需关注”；
- 侧栏运行状态每 30 秒读取持久化的 Mac mini CPU、内存、数据盘百分比和 Worker 心跳；超过 75 秒未采样明确显示指标延迟，无执行器上报时 Provider/模型显示“暂未上报”，不使用演示配置。
- AI 设置改为用户维护的自定义模型库：任意 OpenAI 兼容或 Ollama 配置可保存、真实测试，并从已保存条目选择主模型与可选备用模型；视频笔记的主模型网络/超时/服务失败会记录实际备用模型，不再回退到固定厂商配置。
- 模型编辑支持 DeepSeek、MiMo、Moonshot / Kimi、智谱 GLM、通义、OpenAI 兼容、Ollama 本地与自定义 Provider 预设；推荐 Base URL/模型会联动填写，本地模型不要求 API Key，未保存草稿也可真实测试且不会写入 SQLite 或 Keychain。
- macOS 内存监控改为可回收页口径：不再把 inactive/speculative 文件缓存和压缩页重叠计为业务已用；浮窗展示已用/总量 GB、可回收、压缩内存、数据盘容量、API/Worker/SQLite/Ollama 状态。
- Provider 切换区分预设默认值与用户手填值：自动字段随 Provider 替换，已手填模型名/Base URL 保留；任务步骤进度与总任务进度分离，完成步骤为 100%。
- 任务停滞只依据该 Job 自身的心跳、步骤与审计事件；超过 900 秒无任务活动返回 `ATTEMPT_TIMEOUT` 与可读原因，当前步骤同步失败，用户可显式重试。
- 任务接口统一以 UTC 带时区格式输出时间，客户端按本地时区显示；当前任务总进度与每个步骤独立进度分离，历史里程碑不再伪装为步骤百分比。
- 手机局域网会话统一按 UTC 比较 SQLite 中的过期时间；刷新仅在 401/403 时回到配对页，服务异常显示重试连接。视频资产按 canonical URL 复用，阶段日志覆盖 Bilibili 元数据、CID、资产查询/复用、字幕、音频、ASR、笔记与 POI 检查点。
- 取消改为协作式停止：取消请求保留 lease 至 Worker 观察并清理临时资源；取消确认前重试返回 409，确认或过期释放后才能创建新尝试。
- 任务摘要只在 LLM 步骤展示 Provider/模型，ASR 与下载路径不再误填模型字段；`PARTIAL_SUCCESS` 明确表达“处理流程已完成”及 POI/补充处理原因。
- 视频笔记 API 规范化封面为 HTTPS，封面加载失败展示本地占位；章节正文以受限 Markdown 渲染标题、列表、粗体、斜体、代码与引用，不执行模型输出的 HTML。
- 任务摘要显示最近模型调用的步骤、Provider 与模型；部分完成明确为“处理流程已完成”，并列出地点待确认/未配置地图等补充原因。
- 任务和内容历史都有独立删除入口：仅终态任务可删除；删除内容不会破坏共享来源、地点或路线，具体边界见 `ai-gateway/MODEL_AND_RETENTION_UI_SPEC.md`。
- Mac mini LaunchAgent API/Worker 双服务管理脚本和 Ollama.app；安装器将 `~/.ollama/models` 持久链接到 `/Volumes/D/Projects/ollama-models`，避免重启、App 更新或重复安装后回退到空的默认模型目录。

## 自动验证

- 后端 Ruff 与 pytest：59 项通过，覆盖 4 位配对码轮换、局域网会话刷新、取消/重试门禁、真实状态 Schema、macOS 内存口径、任务专属超时错误、持久化监控快照、来源/档案/待办/日志、WebSocket、Provider Secret 隔离、DOCX、SPA 深链、自定义模型路由、Ollama.app 模型目录持久链接、AI 限流间隔与有限重试、用户补充 Prompt 的契约保护与哈希续跑、运行中完整重跑、历史删除、截图规划/质量过滤、全国地图 Marker 生命周期与 GeoJSON 导出、分享链接规范化、完整转写导出与保留清理、AI 转写校对、步骤级续跑、终态 Replay 门禁、独立 Worker 心跳、备用模型切换取消门禁与视频笔记保留式删除；
- 前端 ESLint、Vitest、TypeScript 和 Vite 生产构建通过；
- Homebrew 已安装 FFmpeg、Whisper.cpp；Ollama 使用官方 macOS App，运行页以实时探测结果为准；
- 实际页面读取到 Apple M4 10 核 CPU、10 核 GPU、16 GB 内存、macOS 26.6.2 与磁盘余量；服务运行状态、局域网地址与资源数值均由状态接口实时返回；
- Ollama 已完成 `qwen2.5:7b` 真实推理，Whisper.cpp 已通过 WAV 上传、Worker 处理、转写文本写入 Segment/Evidence 的端到端验收；
- Browser 验收覆盖 PC 14 个页面/选项卡与手机 7 个核心页面，控制台无应用错误，运行实图位于 `design/ui/implementation-v0.2/`。

## 外部条件

高德 Web 服务/JS API Key、DeepSeek Key 与 MiMo Key 无法由代码自动生成，未提供时必须显示未配置并保留回退能力。Whisper 模型和 Ollama 模型属于可自动下载的本机资源，启用前必须进行完整性校验和真实推理/转写测试。

## 视频 AI 笔记：v0.3 已实施

- 新增 `0003_video_ai_notes`：视频资产、版本化时间码转写、AI 笔记/章节、地点候选、地点笔记版本和外部调用审计均为持久数据；`JobStatus.PARTIAL_SUCCESS` 用于笔记完成但 POI 未补齐的可用结果。
- Bilibili 适配器仅允许 Bilibili/API HTTPS 域名，限制短链重定向、按 `BV` 与 `p` 选择 CID、优先平台字幕；无字幕时通过 yt-dlp 临时音频 + FFmpeg + Whisper.cpp 生成带时间码 Segment。Cookie 仅来自 Secret Store，转换为 `0600` 临时 cookie 文件并在 finally 清理。
- 模型 Provider 已拆分 `generate_text` 与 `generate_json`，新增 `video_note_summary`、`travel_place_extraction`、`place_note_summary` 三个可配置角色，兼容 DeepSeek、MiMo、Ollama 等 OpenAI 兼容服务。没有密钥、Cookie 或硬件依赖时任务明确进入 `NEEDS_USER`，不伪造完成。
- 地点抽取强制保留有效 `segment_ids`；高德只确认 POI，不使用 LLM 坐标；无 Key 或未命中不写入 `0,0` 伪坐标，视频笔记仍可作为部分成功结果交付。
- 新增 `/api/video-notes` 列表、详情、转写、地点、重新生成，以及地点笔记/来源接口；PC 导航和响应式移动端均提供视频笔记列表、详情、时间码、地点和重生成功能。
- `THIRD_PARTY_NOTICES.md` 记录 BiliNote 适配参考与 yt-dlp 许可。Fixture 测试不依赖线上 Bilibili；给定真实链接 `BV1Tvbe6EEw2` 已验证元数据、无字幕判定、10.1 MiB 临时音频回退、Whisper 时间码转写和本地模型笔记生成。

### 仍需由部署者完成的外部配置

高德 Web 服务 Key、DeepSeek/MiMo Key、需要登录的视频 Cookie 不能由代码生成；控制台已提供对应 Provider 状态与 `NEEDS_USER` 原因。地点 POI 未配置时，笔记任务按设计返回 `PARTIAL_SUCCESS`，不会阻塞阅读或时间码回看。

## 视频理解与地图：v0.4 已实施

- 新增 `0004_video_screenshots_and_map_markers`：持久化 `video_screenshots`、`map_marker_states`，并为 `Place` 增加 `canonical_name`、`origin`，为 `PlaceMention` 增加 `raw_name`、建议名称与 `PlaceBrief`；迁移已应用到 Mac mini 的 SQLite 数据库。
- 视频笔记先利用元数据和带时间码 Transcript 生成完整笔记/章节，再以细粒度地点（餐馆、景区、街区、步行街、商圈、市场、公园、博物馆、寺庙、村镇、地标等）建立候选；地点笔记包含特色、菜品/体验、价格、排队、适合人群、注意事项、作者态度、转写名和校正名。
- 截图计划以主要地点优先并绑定章节、地点候选和时间码；章节不足时补齐全文代表帧，计划总量 3–12。受限清晰度下载后由 FFmpeg 抽帧，过滤黑帧、异常曝光、模糊/低方差和重复帧，持久化为受保护图片 API。下载/抽帧不可用时保留可读笔记与明确的部分成功原因。
- 高德 POI 命中写入 `canonical_name`；候选名称与转写/建议名称存在歧义时进入 `REVIEW`，不投影为 Confirmed Marker。
- 地图 API 以中国大陆 bbox 与 zoom 为默认，支持 `bbox + zoom` 查询、低 zoom 聚合、会话视野恢复，不再含厦门、思明区或路线默认城市。历史地点首次读取时补齐独立 Marker 状态，保证隐藏/恢复只影响地图投影。
- Marker 浮层展示代表图、地址、特色、来源数、来源类型和状态；可加入路线、隐藏并进入 `/places/:placeId`。用户新增的 Marker 为可恢复软删除；自动生成 Marker 的删除为隐藏，不删除 Place、Source、Claim、Evidence 或地点笔记。
- 设置页新增高德 JS API Key、Security Code、Web 服务 Key 的 Keychain 存储、独立保存、真实 POI 测试和诊断；前端地图在已认证客户端通过 bootstrap 获取 JS 配置。
- v0.4 设计稿见 `../design/ui/v0.4/`；后端 pytest 26 项、前端 ESLint/Vitest/TypeScript/Vite 已通过。本版本仍受真实高德 Key 和部分视频访问所需 Cookie 的外部条件限制。
- 地图补齐 `origin` 过滤、地点列表与旅行摘要 API，并可导出 CSV、JSON、带 GCJ-02 坐标标识的 GeoJSON；日志工作台补齐 DEBUG/CRITICAL、7 天/自定义时间、Request ID/实体 ID 和服务端升降序游标查询。
- 全量文档已按实现回查；历史“待实施”表述已迁移为已实施状态或明确后续增强。防覆盖和回归入口见 `REGRESSION_AND_CHANGE_GUARD.md`。
- 概览任务卡只对排队/运行任务显示预计耗时；终态改为真实状态。SQLite 历史日志在 API 输出前恢复 UTC offset，日志、任务详情、概览与侧栏统一以 `Asia/Shanghai` 显示北京时间。

## 2026-08-24 可靠性修复已实施

- 视频内容新写入使用规范 `note_*` ID；历史 `ntv_*` 链接由共享查询器兼容解析到父 Note。详情页区分加载、错误与成功，内容页不会生成空链接；SessionGate 的状态检查有 8 秒超时和可见重连入口。
- 所有 Ollama `/api/chat` 调用统一带 `keep_alive: 0`，避免 Mac mini 依赖默认 5 分钟模型驻留。
- 截图下载改为 Bilibili DASH video-only 优先（`bv*[ext=mp4]/bv*/best`）和 `res:720` 排序，携带 Referer/Cookie；现有 `PLANNED` 截图计划可在重试时继续物化。地点置信度兼容 `high/medium/low` 文本，避免模型返回标签时中断地点提取。
- 后端专项测试覆盖 Note/Version ID 兼容、Ollama 释放、DASH 格式选择、置信度归一化和截图计划复用；真实 Bilibili 抽帧仍受视频访问与 Cookie 条件影响，须在有权限样本上继续验收。

## 2026-08-24 第二轮现场排查已实施

- 修正 Whisper.cpp 毫秒 offset，新增末段时长门禁；Worker 为历史 10 倍时间轴创建修正版 Version。样本 `note_221cd61e9600493cb3f32e062e1ad013` 现有 232 段、2 个时间线章节，页面时间范围已恢复到 6:09 媒体范围。
- 模型章节引用无效或生成失败时，服务端按固定转写块生成“时间线详述”兜底；任何有效 Transcript 不再得到 0 个章节。
- 无章节截图计划改为 Transcript 兜底；历史 Note 已补齐 `PLANNING` 计划，实际下载/抽帧仅在显式重生成任务执行。
- 视频笔记新增完整转写段数、保留截止、TXT 导出和 180 天清理；数据库迁移 `0005_transcript_retention` 已应用。

## 2026-08-24 粘贴分享链接规范化已实施

- 后端 `InputNormalizer` 识别 `URL_ONLY / SHARE_TEXT_WITH_URL / TEXT_ONLY / MULTIPLE_URLS`，前端不再自行用 `startsWith` 决定类型；
- 唯一 URL 仅进入 Source/Resolver/Classifier，周围分享文案不进入 Job text；
- 多个不同链接返回 `CAPTURE_MULTIPLE_URLS` 和候选，不创建 Job；
- Source metadata 只保存输入类型、选中 URL、候选数、丢弃长度和输入哈希；自动测试覆盖分享文案、歧义与纯正文。

## 2026-08-24 运行日志错误恢复语义 v0.4.4（源码已实施）

- 当前 `/logs` 已能点击事件打开详情、定位 `entity_type=job / entity_id` 并进入任务页；现有 `POST /api/jobs/{job_id}/retry` 已具备重新入队、状态重置、取消 lease 门禁和 `job.retry.queued` 审计。
- 现场数据库中的 ERROR/CRITICAL 审计事件均规范关联 Job，但部分是旧 attempt 的历史错误，所属 Job 当前可能已经 `PARTIAL_SUCCESS` 或完成；因此按钮必须读取当前 Job 状态，不能仅凭错误消息执行。
- 已新增 Step Artifact Manifest 与 Replay Options：中间产物默认保留 24 小时，ERROR/NEEDS_USER 时从失败步骤继续，上游完成步骤标记 REUSED，当前及下游顺次执行；过期或产物缺失后只允许完整重跑。
- 任务详情根据 Replay Options 显示“从失败步骤继续”或“从头重新运行”，不会再把整 Job 重入队描述为步骤续跑；完整契约见 `jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md`。

## 2026-08-24 任务时间线显示修复

- 时间线排序补齐 `PLAN_SCREENSHOTS / DOWNLOAD_VIDEO_FOR_FRAMES / EXTRACT_SCREENSHOTS`，不再排到清理缓存之后；
- 只有正在运行的 JobStep 显示当前标记，终态任务不再固定高亮 `CLEAN_CACHE`；
- 截图相关技术枚举补齐中文名称，每个阶段同时展示状态、进度和本步骤用时；
- 普通步骤停滞预警保持 90 秒，LLM 步骤提高到 300 秒，真实尝试终止阈值保持 900 秒。

## 2026-08-24 视频笔记阅读体验 v0.4.2（第一阶段已实施）

- Transcript 增加 raw/corrected 双版本，所有转写在 Note 生成前执行 AI 校对，默认预览和 TXT 导出 corrected_text；
- 目录改为具体 heading + thesis，并与地点、Transcript、截图时间码统一跳转到稳定 Section 锚点；
- 页面“全文”改为“按时间线详述”，显示 AI 校对后的摘要、要点和地点引用，不连续铺原始转录；
- TXT 导出改用统一视觉按钮，raw 导出只保留在审计入口；
- 第一阶段已增加主旨目录、稳定 Section 锚点、按时间线详述和 Section 内截图链接；默认转写读取 `corrected_text` 字段并保留 raw 字段。
- 已完成返工：Hero 使用本地 CoverAsset，缺封面时收起；地点候选和完整转写位于文章底部；目录采用主体设计语言；截图为侧排关键缩略图并支持 contain Lightbox；模型逐段校对在 Note 生成前执行，旧版未校对正文会被隐藏并提示重新生成。

## 2026-08-24 视频笔记列表 v0.4.3（已实施）

- 顶部主操作从“投递视频链接”调整为“添加视频链接”，复用 40px 高、14px 字号的全局 Primary Button；
- 列表 Card 使用 Bilibili 元数据的真实封面，本地下载、校验、缓存并生成 672×378 WebP，不长期热链远程 CDN；
- 封面下载执行 HTTPS、图片 CDN allowlist、SSRF、MIME、文件头、尺寸和最大字节校验；
- 封面失败继续显示稳定场记板占位，不阻塞视频笔记；
- 参考 `lanyeeee/bilibili-video-downloader` 的 CoverTask/Content-Type 本地写入方法，直接移植代码时补 MIT Notice；
- 新增 `0006_video_reading_and_covers`、本地 CoverAsset、HTTPS/CDN allowlist/MIME/大小/解码校验、672×378 WebP 衍生图和受控图片 API；Worker 为历史视频补齐封面。列表 CTA 已改为“添加视频链接”，列表使用本地封面 URL，失败仍显示占位。

## 2026-08-24 Pipeline 续跑与视频笔记删除 v0.4.4（源码已实施）

- 步骤级续跑使用 24 小时 Replay Cache；失败步骤 ERROR 时仅重跑当前及下游，上游完成步骤 REUSED；中间产物清理后只允许完整重跑；
- 任务详情已接入 Replay Options 和“从错误步骤继续”；
- 视频笔记列表和详情 `…` 菜单增加统一删除入口；删除 Note/Version/Section/TOC/Content 投影，保留共享 Source、VideoAsset、CoverAsset、Transcript、Place 和 Evidence；
- 列表与详情已使用 `…` 菜单删除并显示保留边界；自动测试验证删除 Note/Version/Section/Content 后仍保留 Source、VideoAsset 与 Transcript。
- `0007_step_replay_and_reading_v044` 已应用到 Mac mini 在线库，迁移前备份为 `data/backups/pre-v044-20260825.db`，迁移后 `integrity_check=ok`；API/Worker 已重启并通过健康检查。
- 真实样本 `job_27bd13014cfc4d6fa16e62966f4208aa` 验证：前六步 REUSED，AI 校对 255/256 段、1 段 REVIEW，生成 7 个结构化章节与 7 张 READY 关键截图，因 3 个 POI 待确认交付 PARTIAL_SUCCESS；所有实际执行步骤均为 100%。
- Browser 已完成 1440×1000 与 390×844 验收：无横向溢出，桌面截图侧排、移动端单列、证据区位于正文底部、Lightbox 使用 contain、终态无当前步骤高亮、浏览器控制台无 ERROR/WARN。

## 2026-08-25 Worker 延迟与“从头重新运行”修复已实施

- 现场任务 `job_86445a9c341c44aaaac5e8c62db909f1` 在 `CORRECT_TRANSCRIPT` 处理 232 段转写时于 14:13 请求取消，页面随后显示 `CANCELLED`、仍持有 lease，且“从头重新运行”按钮禁用；浏览器证据表明该按钮没有发出请求。后端完整重跑在 lease 释放后本可接受 `CANCELLED`，但任务详情将可重跑状态硬编码为 `FAILED / NEEDS_USER / PARTIAL_SUCCESS`，因此停止完成后仍会永久不可用。
- 同一任务的全局 Worker 心跳停在 14:01，而任务自身活动在 14:28 仍更新；运行浮窗因单线程 Worker 在同步 Pipeline 内无法回到外层循环而误报“Worker 延迟”。当前 `CORRECT_TRANSCRIPT` 在批次间不检查取消，232 段约拆为 29 个模型请求；取消后仍可能继续发起剩余批次和占用模型/Worker。
- Worker 使用独立守护线程每 20 秒刷新进程存活心跳；模型校对单批使用 90 秒上限，在请求前后检查取消，HTTP 失败不再递归拆分，结构错误才缩小批次，并记录批次进度。
- 完整重跑现为右上角唯一入口，运行/排队/终态均可点击；运行态会取消旧 Job、创建新的 QUEUED Job 并导航。恢复卡仅在步骤续跑可用时显示续跑按钮，不可用时只提示原因。
- 复用旧 canonical VideoAsset 时，续跑从 `FETCH_METADATA` Artifact 读取 `video_asset_id`，不再用新 Capture Source ID 错误查询资产；续跑启动前失败也会把 PENDING 当前步骤恢复为 FAILED，确保可以再次续跑。
- 通用设置新增 AI 接口策略：默认调用前等待 1 秒；Warn/Error 默认重试 2 次、间隔 5 秒；主模型耗尽重试后再调用备用模型。
- LLM 页面停滞预警为 600 秒，覆盖单模型 300 秒超时及重试切换窗口；Worker 的真实尝试终止阈值仍为 900 秒。
- 全量后端 pytest 49 项、Ruff、前端 lint/Vitest 10 项/TypeScript/Vite 构建通过。
- 现场任务 `job_64b48537770e40efa1029f6ceaef8f87` 修复后从 `CORRECT_TRANSCRIPT` 成功续跑：前六步 REUSED，225/225 段校对完成；真实触发 transcript correction 5 次重试（最大 attempt=2）和 video note summary 1 次重试，最终所有执行步骤 100%，因 19 个 POI 待确认合理交付 PARTIAL_SUCCESS。
- Browser 验证失败态仅保留步骤续跑按钮、终态不显示恢复卡、右上角完整重跑始终可用、无当前步骤误高亮；设置页显示并保存 2 次/5 秒/1 秒默认策略，控制台无 ERROR/WARN。

## 2026-08-26 可编辑补充 Prompt v0.4.5

- 设置 → AI 模型在现有“推理路由”和“已保存模型”之间新增提示词补充区，按转写校对、视频笔记、地点提取分别保存低优先级表达偏好；界面保留当前导航、卡片、按钮和暖白纸面语言。
- 固定 Prompt、JSON、Schema、字段、Segment ID、顺序和证据契约不可编辑；服务端在写入时拒绝越权覆盖语言，模型返回仍走原有解析和证据校验。
- 三个 AI Step Input 记录 `prompt_supplement_hash`；补充 Prompt 改变时，失败 Job 的 Replay Options 自动从最早受影响的 AI 步骤开始，不会错误复用旧模型产物。
- 设计见 `design/ui/v0.4.5/prompt-supplements-settings-annotated.png`，完整实现契约见 `ai-gateway/PROMPT_SUPPLEMENTS_V045_SPEC.md`。

## 2026-08-27 转写路由、参数与来源清理 v0.4.6

- 转写校对支持独立主/备用模型；专属项优先于通用推理路由，留空时逐项继承。
- 转写每批字符、Segment 数和超时可配置，默认 `12000 / 128 / 180秒`，服务端和原生数字输入均限制安全范围。
- Prompt 补充区按阶段完整展示 6 条锁定核心契约，不再只显示一条笼统摘要。
- 来源审计页支持删除孤立来源；关联内容/视频笔记/活跃任务阻止删除。删除最后一个内容或视频笔记时自动清理孤立 Source、快照、分段及专属视频资产，Place 与路线保留。
- 完整契约与页面设计见 `ai-gateway/AI_ROUTING_SOURCE_RETENTION_V046_SPEC.md` 和 `design/ui/v0.4.6/README.md`。
- 自动验证为后端 pytest 55 项、Ruff，前端 ESLint、Vitest 10 项、TypeScript 与 Vite build；Browser 覆盖 1440×1000 桌面和 390×844 移动设置页、来源删除门禁与孤立来源启用态，控制台无 ERROR/WARN。

## 2026-08-28 LaunchAgent 外置卷健康门禁与 Python 3.14 迁移

- `manage.py status` 同时验证服务进程、API 健康、首页实际字节和 Worker 心跳；新增拒绝中断活跃 Job 的 `restart`。
- `install/restart` 在 `bootout` 后等待旧 launchd 标签确认消失再重新加载，避免立即 `bootstrap` 的退出码 5 竞态。
- Worker 启动先冷导入视频 Pipeline；未捕获异常立即失败并释放 Job lease，不再等待 15 分钟超时。
- D 卷由 macOS 识别为 External USB APFS；生产运行时已迁移到本机签名 Python `3.14.6`，venv 固定为 `/Volumes/D/Library/Application Support/Zhijian/venv`，LaunchAgent `PYTHONPATH` 直接指向当前项目 `backend/src`。
- API 与 Worker 已用该生产 venv 重新加载；`launchctl print` 的实际 `program` 均指向生产 venv，`manage.py status` 验证 `/health=ok`、首页正文 `555 bytes` 和持续更新的 Worker 心跳。
- 切换后未发现新 PID、服务名或项目路径对应的 `SystemPolicyRemovableVolumes deny`；Keychain 服务仍可访问，但未读取或输出凭据，也未触发真实 Provider、视频重生成或 Job 重跑。
- Python 3.14 回归为后端 pytest 57 项、Ruff、`pip check`；前端在 Node `22.21.0` 下通过 ESLint、Vitest 10 项、TypeScript 与 Vite build。长期冷启动与重启后的 TCC 稳定性仍需随日常运行观察。

## 2026-08-28 AI Workload Gateway v2 — WP1 Gateway Skeleton

- 新增无状态 `zhijian.ai` 边界：统一定义 Capability、执行模式、质量与隐私策略、请求/结果、Evidence 和 Model Profile 契约；不依赖模型名称推断能力或模态。
- `AIWorkloadGateway` 仅包装既有 `LLMProvider`，按是否要求结构化输出调用原有 JSON/文本方法，并透传模型覆盖、Provider 返回的用量和 Evidence ID；现有业务 Pipeline、重试、回退与审计均未改变。
- 目标验证：新增 Gateway 单测 2 项和针对新增模块的 Ruff 均通过。Model Registry、Probe、持久化设置和按阶段路由仍属于后续 WP2/WP3，尚未实施。

## 2026-08-28 AI Workload Gateway v2 — WP2–WP4

- 已扩展现有 Settings 模型库而未新增数据库表：Profile 显式记录本地/远程位置、text/image 模态、JSON/Thinking 能力、上下文/输出上限和质量档；能力探测只在用户主动触发时调用 Provider，并只持久化 PASS/FAIL 与 Capability，不写入 Keychain Secret。
- 已为 `TRANSCRIPT_CORRECTION`、`GENERATE_AI_NOTE`、`EXTRACT_TRAVEL_FACTS` 实施 `AUTO / LOCAL_ONLY / LOCAL_FIRST / REMOTE_FIRST / REMOTE_ONLY` 路由；没有保存新策略的历史任务严格保留旧主/备用路由。Capture API 支持受白名单和 Profile 能力校验的 Job 级阶段覆盖。
- 已实施 Settings 持久化的阶段策略、统一继承 Resolver、参数白名单、模型位置/Thinking/输出上限校验、重置默认、Basic/Advanced UI 和无 Secret 的 resolved policy 审计快照。实际 Provider 已接收 Temperature、最大输出和 Ollama Thinking 选项。
- 验证新增阶段策略/能力探测/API/实际 Provider 路由测试；桌面及 390px Browser 检查均完成，无控制台错误或横向溢出。语义升级、用量汇总、Delta/Map-Reduce、Cache/Budget、Domain Context、Vision 仍按 v2 后续 WP5–WP11 排期，未实施。

## 2026-08-28 AI Workload Gateway v2 — WP5–WP8

- 新增 `GET /api/jobs/{job_id}/ai-usage`，从现有 `ExternalCallAudit` 聚合调用、本地/远程、阶段、模型、输入/输出/缓存 Token 和耗时；任务详情新增只读 AI 用量摘要，不新增审计表或暴露 Secret。
- 转写校对加入确定性质量门禁：干净平台字幕标记 `PASS_THROUGH`，不发模型；其余仅发送候选 Segment，模型只返回 `changes`，未返回候选进入 REVIEW。JSON 不合格不再默认递归二分放大调用；仅保留现有请求级失败语义。
- 视频笔记按时间块生成并保存紧凑 `SectionFacts`，多块时只将 Facts 送入全局 Reduce；新增 Alembic `0009_ai_workload_facts` 保存 `map_facts_json`。默认地点提取从 Facts 作确定性聚合，保留 `EXTRACT_TRAVEL_FACTS` 步骤与 `REMOTE_ONLY` 显式模型重处理。
- 全量自动验证为后端 pytest 69 项、Ruff；前端 ESLint、Vitest 10 项、TypeScript 与 Vite build。迁移在全新临时 SQLite 库升级到 `0009 (head)`；Browser 验收任务详情用量卡（桌面）无控制台错误。未触发真实 Provider、视频 Job 或生产迁移/重启。Cache/Budget、Domain Context、Vision 和统一资源管理仍是后续范围。

## 2026-08-28 AI Workload Gateway v2 — WP9 Cache + Budget

- 新增 Alembic `0010_ai_cache_entries` 与精确 AI 输出缓存。缓存键绑定阶段、Capability、Provider/Model、完整消息、Prompt 补充哈希和会影响语义的 generation/domain 参数；命中返回原始模型输出并写入 `cache_hit` 审计，不重复调用 Provider。
- `force_regenerate` 会绕过命中并保留新缓存项对前一结果的引用；转写、笔记 Map/Reduce 和 `REMOTE_ONLY` 地点重处理均已接入同一缓存边界。
- 新增每 Job 模型尝试、远程/本地输入/输出 Token、AI 墙钟时长预算；每次真实模型调用前检查，缓存命中不计入次数或 Token。通用设置页支持安全范围内调整全部预算参数。
- 全量验证为后端 pytest 71 项、Ruff；前端 ESLint、Vitest 10 项、TypeScript 与 Vite build。全新临时 SQLite 已升级到 `0010 (head)`；Browser 验收预算字段可编辑且控制台无错误。未调用真实模型、未迁移或重启生产服务。WP10 Domain Context 与 WP11 Vision 尚未实施。

## 2026-08-28 AI Workload Gateway v2 — WP10 Domain Context + WP11 Vision Boundary

- 新增可版本化 Domain Pack：glossary、aliases、rules、examples、补充说明与允许 Capability 均由 Settings 持久化，并提供受保护 CRUD API。阶段策略和 Job 覆盖只能引用存在的领域包；包版本形成上下文哈希并参与 AI 缓存键。
- Domain Context 以低优先级 system 消息注入本地和远程同一调用路径，不能覆盖证据、Schema 或安全契约；不引入向量库或全量 RAG。
- 注册 `SCREENSHOT_UNDERSTANDING` 视觉阶段；策略校验强制 image-capable Profile，text-only Profile 会被 API 拒绝。当前视频抽帧仍是确定性质量筛选，未在没有具体视觉需求时自动上传帧或触发视觉模型。
- 全量验证为后端 pytest 73 项、Ruff；前端 ESLint、Vitest 10 项、TypeScript 与 Vite build。Browser 验收领域上下文面板可编辑且无控制台错误；未触发真实 Provider、视觉/视频 Job、生产迁移或服务重启。

## 2026-08-28 AI Workload Gateway v2 — Runtime Hardening

- `LocalAIResourceManager` 在单进程内串行化本机 ASR、文本和未来视觉模型重任务，避免 API 模型测试与 Worker 争用统一内存；当前 Worker 单租约设计仍是跨 Job 的第一层门禁，Ollama 保持 `keep_alive: 0`。
- 新增 `scripts/benchmark_ai_profiles.py`：只汇总既有 JSON Benchmark 样本的 schema、Evidence、延迟、local/remote Token 与升级率，不下载模型、不调用 Provider。
- 全量验证为后端 pytest 74 项、Ruff；前端 ESLint、Vitest 10 项、TypeScript 与 Vite build；Benchmark 示例仅使用临时本地 JSON，未触发真实模型、视频任务、生产迁移或重启。

## 2026-09-02 AI Workload Gateway — Stabilization Source Fixes

- `LocalAIResourceManager` 已由进程内 `threading.Lock` 改为共享 `data/runtime/local-ai.lock` 的 OS `flock`：API 模型测试/探测与 Worker ASR、文本、未来视觉任务在不同 LaunchAgent 进程间串行，异常进程退出后由内核释放锁；远程调用不再占用本地 AI 锁。
- Budget 从整个 Job 的混合 Token 聚合改为按审计 `location` 分账 LOCAL/REMOTE；Cache hit 明确不计 model attempts 或预算，并写入路由位置供 Usage Summary 聚合。新增跨进程锁释放、Local/Remote 互不消耗及缓存预算测试。
- 新增 `scripts/run_ai_benchmark.py` 和 `dev docs/benchmark/golden-ai-gateway-samples.json`，用于评估真实 E2E 已采集指标并输出 Schema、Evidence、质量、Token 降幅发布门禁；脚本不会调用 Provider 或视频下载。
- 该记录只代表源码与定向自动测试完成，不代表生产服务已加载此版本，也不代表真实 Provider/视频/Benchmark 已验收。真实生产门禁收敛到 `ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md`。

## 2026-09-02 Bilibili 扫码登录与字幕恢复

- 设置 → 网页解析与任务登录恢复卡共用站内二维码登录；后端通过 Bilibili Passport 生成/轮询二维码，成功后调用 `/x/web-interface/nav` 验证账号并只将 Cookie 写入 Secret Store/Keychain，API、SQLite 与日志不回显凭据。真实扫码、账号验证和 Keychain 保存已通过。
- Bilibili `401/403/412`、登录相关平台码和 yt-dlp 登录提示统一映射为 `VIDEO_LOGIN_REQUIRED → NEEDS_USER`，立即停止后续步骤并释放 Worker；登录后可从 `DOWNLOAD_AUDIO` 或截图下载步骤继续，非核心截图也可由用户明确选择跳过。
- 新增可复用的 HTTPS Host Policy，按用途组合精确域名与安全子域后缀；字幕允许官方 `*.hdslb.com` CDN，同时拒绝 HTTP、非标准端口、userinfo、相似后缀和后缀拼接绕过。封面与字幕不再各自维护易漂移的域名判断。
- 字幕轨按人工中文、AI 中文（含 `ai-zh`）、其他语言排序；单轨 CDN/网络/格式失败会继续尝试下一轨，全部不可用才回退音频 ASR，只有登录失效继续阻塞用户。现场 Job `job_7e390b26346a4bb085965aa5149d2ec2` 暴露的 `VIDEO_HOST_BLOCKED` 根因已修复，但未自动重跑。
- 自动验证为后端 pytest 88 项、Ruff、Alembic `0010 (head)`，前端 Vitest 12 项、ESLint、TypeScript 与 Vite build；API/Worker 已在无活跃 Job 时重启，`/health`、首页正文与 Worker 心跳通过。

## 2026-10-09 当前状态页历史归档

以下按原采样日期保留验证和实施过程，不代表当前部署或新的实施授权；当前结论见 [实施状态](../IMPLEMENTATION_STATUS.md)。

2026-10-08：修复协作取消路径的本地路由 HTTP 参数错误：`trust_env` 改为传给 `AsyncClient` 构造函数，不再进入 `.post()`；保留本地路由绕过环境代理与普通连接默认行为。新增离线请求成功和本地路由取消回归，修复前均复现原 TypeError；目标 34 项、生产 Python 3.14 后端全量 279 项、完整 Ruff、Node 24 前端 19 项/Lint/类型/构建通过。用户授权后已备份并无迁移生产重载，带日期现场见 CURRENT_HANDOFF；未调用真实模型或重跑视频，真实校对恢复尚未验收。

2026-10-08：Token 缺省按本地字符估算补齐读取展示与预算，实测/估算/未知独立计数，历史审计不回填、Cache 不重复计消耗；任务页保留“以原配置重跑”。Job 模型请求、请求间隔、重试及本地资源锁等待可协作取消，ASR 回收进程组并每 30 秒报告等待，超时不重复相同模型请求，旧执行身份仍拦截迟到写入。生产 Python 3.14 后端全量 277 项、完整 Ruff、Node 24 前端 19 项/Lint/类型/构建通过；备份后无迁移重载，实际用量 HTTP 与 PC/390px Browser 核验估算及部分未知。未触发真实 Provider 测试或视频重跑；带日期现场见 CURRENT_HANDOFF。

2026-09-09：后端完整 `pytest backend/tests -q`、POI Resolver Golden、Plan C 目标测试、目标 Ruff 与 `git diff --check` 通过；Node 22.21.0 下前端 ESLint、Vitest 15 项、TypeScript 与 Vite build 通过。Plan C 在空 SQLite 成功升级至 0019：12 个月/日期状态、Preference Event、确定性推荐与 Visual Fact Golden 均为离线验证；无 Vision Profile 时截图 Job 以 `SKIPPED_UNSUPPORTED` 进入 `PARTIAL_SUCCESS`，不调用 Provider。桌面浏览器已检查地图 Toolbar 的月份、适宜度与推荐筛选；当前工具无法设为 390px，移动视觉验收未执行。以上不替代真实高德、Vision 或视频验收；实际生产采样见 CURRENT_HANDOFF。

- 2026-09-10：视频字幕 P0 一致性门禁已进入源码。`ai-zh` 等生成字幕只保留非敏感来源哈希并强制走 Whisper ASR；人工中文字幕仍可通过来源/时间轴门禁直通。生成 Note 前验证 Transcript 的 VideoAsset、Source、BV/CID、Snapshot 与状态，长 ASR 校对在 Ollama 下每批最多 32 段。目标 Ruff、视频相关 36 项与后端全量 117 项通过；前端 verify 在可用 Node 24 通过。真实结果和未完成非核心截图不在本页判定，见当前任务证据。
- 2026-09-10：已保存模型可选保存 `request_interval_seconds`（0–300 秒，留空继承全局设置），并分别作用于主/备用 Profile 的每次调用。该字段不保存 Key、不新增 Schema migration；后端全量与前端 verify 通过，未调用真实 Provider。
- 2026-09-10：视频质量总计划 WP0–22 的源码实现已完成：统一转写结构/时间轴门禁；所有模式独立分块扫描完整校对稿后再写入逐字 Evidence 地点候选；Pipeline/Replay 改为先地点后 Note；`0020` 保存地点化章节类型、关联 Mention 与引文；Note Map/Reduce 和最终章节只接收服务端 Grounded Evidence；全局和笔记页审核共用 `PlaceReviewCard` 与上下文 API，审核后同步刷新地点、笔记和地图缓存。后端完整 122 项、前端 verify、`git diff --check` 通过；`0020` 已在隔离的 0019 状态成功升级。WP23 仍按性能证据条件性延期；真实 Provider/视频重放、生产迁移/重启和历史截图补全本轮未执行。零库升级仍在既有 0019 历史 migration 重复创建 `preference_events` 处失败，未修改该已发布 migration。
- 2026-09-11：视频笔记的确认态地点候选以当前绑定 `Place` 为唯一展示来源，显示最新名称/地址并跳转地点详情；不再携带该视频的时间码或 Insight 行注释。未确认的 `REVIEW` 与 `UNRESOLVED` 保留 Evidence，并可进入手动 POI 搜索/确认。前端 verify 与已部署页面验收通过，未自动确认真实 POI。
- 2026-09-11：未确认地点候选及 Review Evidence 上下文的时间戳均为新窗口 Bilibili 链接，保留原 URL 参数并追加秒级 `t` 定位；纯函数单测覆盖分 P 参数保留，已部署页面核验 `2:32 → t=152`。
- 2026-09-12：Provider/Job 日志补齐脱敏 HTTP 错误、可行动错误码、实际耗时、输入哈希、分块与主备调用链；Profile 默认 `max_output_tokens` 实际生效；`/api/logs?job_id=` 与日志页展示 LLM 尝试；Worker 每日按 `data_retention_days` 清理系统事件和外部调用审计。后端全量测试、Ruff、前端 verify 通过；未重启生产服务、未调用真实 Provider。
- 2026-09-12：下一阶段计划 WP1 已完成：Place Type→高德 typecode 的单一映射覆盖街区、步行街、村落、城镇、地标等类型，并区分强匹配、弱兼容、不兼容与未映射；Review API 返回稳定 reason code 与可读原因。POI Golden 从 10 例扩至 17 例，Top-1/Top-3、自动确认精度均为 1.0，错误确认 0，Review 率由 0.30 降至 0.2353；后端全量 126 项、Ruff、Node 24 前端 verify 与 `git diff --check` 通过。未调用真实高德/Provider，WP2–WP15 未实施。
- 2026-09-13：UI/视频/POI V2 的 WP2–WP15 源码实施完成：POI V2 为 Shadow Mode、Geo Session、上下文候选/负证据、确认来源保护与纠错草稿导出；共享 UI primitives 已迁移设置、审核、视频、投递/任务与地图搜索入口；Bilibili 经 Adapter Registry 保持兼容，本地文件和 YouTube 复用同一 Pipeline；ASR Registry 保持 Whisper.cpp 默认并提供 CPU fallback 与离线 Benchmark；Note Render Profile 生成新 ntv，0021 记录 Profile，0022 建立 SQLite FTS5 正文搜索和幂等回填。后端全量、Ruff、Node 24 前端 verify、`git diff --check` 均通过；隔离 SQLite 已从可信 0020 升至 0022。未调用真实高德/YouTube/Provider/视频，未迁移或重启生产；Browser/390px 视觉验收因现有运行实例不可中断且 Browser/Playwright 不可用而未执行。
- 2026-09-13：已授权生产迁移 `0020→0022`、受控重启和真实验证；迁移前 active Job/lease=0、`integrity_check=ok`，备份 `app-pre-ui-video-poi-v2-20260913-125600.db` 完整性 ok，API/Worker/心跳 READY。真实 YouTube Job 在元数据/字幕后因媒体不可用进入 `NEEDS_USER`；Bilibili Job 完成下载/Whisper/归一化后远程校对模型空响应，任务级 Local 重试被 Source/VideoAsset 复用导致的 `TRANSCRIPT_SOURCE_MISMATCH` 安全拒绝。不得把本轮描述为成功真实 E2E；修复复用缺陷后才可重试。
- 2026-09-13：重复 Capture 的 Source/VideoAsset 身份复用已修复，异常审计的 SQLite naive/UTC aware 时间比较已统一；全量回归通过并生产重启。用户样本 `BV19sbV6eExE` 的真实下载、Whisper、归一化与本地校对成功，Source/Asset 绑定一致且空 Source 已清理；地点抽取在多个已存 Profile 上分别遇到 OpenRouter 400、缺 `content`、非法 JSON 和超时，故未生成 Note/POI/截图，仍不能宣称成功 E2E。
- 2026-09-13：用户切换 Key 后，`BV19sbV6eExE` 从地点抽取步骤 Replay 成功并以 `PARTIAL_SUCCESS` 交付：Note version 2、9 张 READY 截图、FTS 新 Note 命中、45 个 POI 全部 REVIEW/UNRESOLVED、confirmed=0；步骤无失败/跳过。此为真实 Bilibili+ASR+校对+抽取+Note+POI Review+截图验收，不代表 Vision、Profile 切换、fallback、缓存/强制再生或移动浏览器验收。
- 2026-09-14：Note Evidence Index 按 Mention ID 稳定排序，避免同语义 Replay 因数据库读取顺序漂移 Cache Key。真实 COMPACT Profile 生成 current version 7，所有章节保留 Evidence；同 Profile 二次 Replay 的分块 Cache Hit 为 0ms，force-regenerate 真实调用并建立 Cache result chain。Local Video 文件上传、Adapter 与 ASR 通过，后续本地校对超时。Vision 无 image-capable Profile，备用 ASR 六类 corpus、可控 fallback、POI 人审晋级和 Browser/390px 仍未验证。
- 2026-09-14：LLM Token 与自动化计划第一阶段（WP0–WP5、WP8、WP11）已进入源码：`0023` 持久化 Profile 无关的 Grounded Map，默认链路只进行一次主语义扫描；`EXTRACT_TRAVEL_FACTS` 只从该 Artifact 确定性物化并记录 0 LLM Prompt Token；Profile 重生成从 `NOTE_REDUCE` 开始，复用 Transcript、Grounded Map 和 PlaceMention。`/api/jobs/{id}/ai-usage` 现按 Stage/模型/位置提供 Token、缓存、重试/fallback/重复输入浪费及自动化决策；每次 Map 记录 RUN/REUSE/SKIP 原因。完整后端回归、完整 Ruff、Node 24 前端 verify、`diff --check` 通过；均为离线验证，未调用真实 Provider/视频或做 Browser/390px 验收。第二、三阶段未实施。
- 2026-09-14：LLM Token 与自动化计划第二阶段（WP6、WP7、WP9、WP10）已进入源码。Whisper 只发送确定性语义候选及有界邻段；人工字幕直接 PASS，来源不明的旧 ASR 保持保守全量校对。长 Prompt 与 Map/Reduce 默认不 Retry；仅带 `Retry-After` 的 429、超时/连接或临时 4xx/5xx 重试，JSON 包裹/尾逗号先本地修复。标记为 `ai_automation_version=v2` 的新任务在 AUTO 下按 Stage capability、Profile location/tier、Quality preset 与软预算压力决定 LOCAL/REMOTE；软预算会在 Job payload 和 AI Usage API 记录 EXPECTED/WARNING/HARD_LIMIT，WARNING 时优先 Local、取消 fallback 与 Retry。完整后端回归、完整 Ruff、Node 24 前端 verify、`diff --check` 通过；未调用真实 Provider/视频。历史性能、价格和 Benchmark 数据未编造，仍待第三阶段取证。
- 2026-09-14：第三阶段离线能力已进入源码：POI V2 只允许满足全部 Evidence、类型、地域、候选差距、坐标、负证据与 chain-risk 门禁的 `AUTO_STRONG` 创建 Confirmed Place；`AUTO_CONTEXTUAL` 自动完成详情二次核验后仍进 Review，人工确认/拒绝写入可供离线 Golden 使用的 feedback，未在线调阈值。`AI_TOKEN_ANOMALY` 检测重复输入、连续 fallback、异常 Chunk 尝试和超预算 Prompt，默认只记录不重跑。Benchmark 现包含 Token 增长超过 15% 且无质量收益的回归 Gate；毕业检查脚本要求 Fixture、10/30/60 分钟真实视频、Replay 及 Provider 全部证据才会 PASS。离线 Golden 将有 chain risk 的“角楼咖啡”从 Confirmed 收紧为 Review；完整后端回归、Ruff、Node 24 前端 verify、`diff --check` 通过。未调用真实高德/Provider/视频，故未达到生产毕业。
- 2026-09-14：已受控部署 `09e4c6a` 与启动环境修复 `4226541`。部署前 revision `0023`、`integrity_check=ok`、active Job/lease=0；已备份 `data/backups/app-pre-llm-token-automation-20260914-143324.db`（完整性 ok），不重复迁移。API/Worker/首页/心跳 READY，`grounded_map_artifacts` 表和新 API 路由可读。LaunchAgent 改传配置别名 `ENV=production`，清理了此前错误 development 启动生成的 2 条无来源演示 Job；修复后未再生成。真实本地 `qwen3.5:9b` 最小 JSON 连通测试通过；当前主远程 Profile 返回 HTTP 429，未重试。没有合规 10/30/60 分钟样本，未重跑既有媒体/ASR/校对，故仍不宣称真实 Pipeline/Provider/fallback/毕业通过。
- 2026-09-14：内容、视频笔记、任务和来源列表均加入统一的当前列表全选、逐项选择、数量确认与批量删除工具条。后端批删先验证全部目标：任务仅终态可删；内容删除专属 Claim/Evidence 后才孤立来源清理；视频笔记批删保留地点/路线。来源批删只删除孤立来源并逐项返回关联内容/笔记/活跃任务跳过原因，不触碰关联内容；来源证据链删除必须 `confirm=true`，确认后同步删除关联内容、视频笔记、快照和分段，保留地点/路线。选择工具已移入各列表标题栏；复选框与类型图标分离，长标题/路径单行省略。内容批删路由的回归覆盖成功删除与孤立来源清理，响应中的来源 ID 顺序稳定。后端 162 项、Ruff、Node 24 前端 verify、`diff --check` 通过；Browser 在 1047×886 验收来源与任务标题栏、逐项选择和删除确认弹窗，在 390×844 验收来源列表，控制台无 warning/error，未执行真实删除。
- 2026-09-15：设置页 `SelectField` 将 option 的多段 React 子节点按空字符串合并，不再使用数组默认的逗号连接；模型选择器正确显示“名称 · 模型名”。Node 24 前端 lint、17 项 Vitest、TypeScript、Vite build 与 `diff --check` 通过。
- 2026-09-15：设置页 AI 阶段标题仅显示中文业务名，`GROUND_MAP` 显示“证据地图”，不再展示英文名称或技术 capability 枚举。Node 24 前端 lint、17 项 Vitest、TypeScript、Vite build 与 `diff --check` 通过。
- 2026-09-16：模型可靠调用计划已进入源码。Profile JSON Setting 以兼容字段保存 DIRECT/STANDARD/GUARDED/FREE_TIER 及限速、并发、重试、熔断参数，无新 migration；可靠层按 provider/credential/model 维护单进程 limiter 与 circuit，429 无 `Retry-After` 也按指数退避，quota 不重试，主备各自执行 Policy，OpenRouter 同 endpoint 不同 model 可切换。结构化输出仅在安全恢复及 Stage 最小契约通过后写 Cache，Audit 保留 attempt/error/recovery 的脱敏 metadata。后端完整 `pytest backend/tests -q`、完整 Ruff、Node 24 `pnpm verify`、`diff --check` 通过；设置页在本地桌面与 390×844 预览通过且控制台无 warning/error。未调用真实 Provider/视频，未迁移或重启服务。
- 2026-09-16：历史坏 Cache 循环失败已修复。现场 Job 的 `GROUND_MAP` 两次均以 0ms 命中同一条截断 v1 Cache，故 Replay 没有新 LLM Attempt 并重复报“模型没有返回 JSON 对象”。Gateway 现在对新结果和 Cache Hit 使用同一 JSON/Stage 契约；非法旧项记录 `SKIPPED / AI_CACHE_INVALID` 与 `cache_entry_id` 后绕过，合法 v1 Cache 继续复用，新写入使用 v2 Key 并保留替代链。完整后端回归、Ruff、`diff --check` 通过；未删除历史记录、未调用 Provider、未部署或 Replay。
- 2026-09-16：部署复核发现 Worker 启动时 `providers.llm` 导入 `ai.reliability` 会触发 `ai.__init__` 预加载 Gateway/Cache，反向导入部分初始化的 Provider。`AIWorkloadGateway` 改为惰性包导出，新增 Worker import 回归；生产解释器 import、完整后端回归与 Ruff 通过。第二次受控重启后 API/Worker 均 RUNNING、内容/心跳 READY；无 migration、Provider 调用或视频 Replay。
- 2026-09-16：转写校对对 `AI_PROVIDER_OUTPUT_TRUNCATED` 增加批次二分恢复：不原样重试被截断的大批次，而是递归拆分后串行校对，并记录 `transcript.correction.batch.split`。目标视频表明 32 Segment/4047 字符仍可能令 GLM 达到输出长度上限，生产默认已收紧至 4000 字符/16 Segment；目标与完整后端回归、Ruff、`diff --check` 通过。修复已受控部署，未自动 Replay。
- 2026-09-16：模型不稳定流程与付费 API 已进一步隔离。结构化错误只占 JSON retry；转写拆分子批完成即持久化，未变更段记为 `UNCHANGED`，后续 Replay 跳过完成段；截断学习到的 model 级安全批量保存在 Job runtime hint。TPM/RPM 临时上限使用 `AI_PROVIDER_THROTTLED`，仅打开对应 provider/credential/model circuit，DIRECT 付费 Profile 不等待、不加锁、不重试且不受该 circuit 影响；Replay 遇到 Provider 阻塞进入 `NEEDS_USER`。完整后端 180 项与 Ruff 通过；已无 migration 受控重启，未调用真实 Provider 或自动 Replay。
- 2026-09-16：OpenRouter `openrouter/free` 在账户/Guardrail ZDR 策略排除全部端点时现分类为 `AI_PROVIDER_POLICY_BLOCKED`，不再把首个 404 当网络错误重试成泛化 400；转写 Job 保留具体 Provider 错误码，取消仍保持取消语义。日志事件抽屉新增“复制日志”，复制当前脱敏事件 JSON 并显示成功反馈。后端 181 项、Ruff、前端 18 项测试/TypeScript/Vite build、`diff --check` 通过；桌面及 390×844 Browser 交互与控制台通过。已无 migration 受控重启，未重跑 Job 或调用真实 Provider；账户级 ZDR 仍需用户在 OpenRouter Privacy/Guardrail 调整，或改用支持 ZDR 的模型。
- 2026-09-16：完整重跑改为复用原 Job ID，终态任务直接重置并从首步入队；运行中任务先协作式取消，再由 Worker 在释放 lease 后以同一 Job 入队，保留 Job ID 与审计记录、重置 Step 执行态/中间 Artifact，且不会创建替代任务。任务列表运行态右侧显示“正在〈实际阶段〉”，不再以泛化“处理中”掩盖当前 Step。失败卡长 Provider URL 在 390px 下改为可换行单列，无横向溢出。后端 182 项、Ruff、前端 verify 与 `diff --check` 通过；已无 migration 受控重启，桌面/390×844 Browser 与控制台通过；未自动重跑或调用 Provider。
- 2026-09-16：任务列表改为真实的固定选择列，不再以条件 class 和行 margin 模拟占位；可删除任务显示复选框，运行中任务保留同宽空槽，标题、阶段、进度与状态列在桌面和 390×844 下对齐。列表改为复用任务详情的统一阶段词典，`CORRECT_TRANSCRIPT` 显示“AI 校对转写”，状态小字增加越界省略保护。Node 24 前端 verify（10 个文件、18 项）、`diff --check` 通过；本机生产页面 970×886/390×844 Browser 无横向溢出、控制台无 warning/error，勾选后工具条正确显示 `已选 1/1`。仅更新同源前端静态产物，无 migration、无服务重启、未触发真实任务或 Provider。
- 2026-09-17：AI 预算与模型探测边界已修正。远程调用次数/Token 按本轮及 Provider Profile 分账，本地不受固定调用次数限制；非 LLM 审计与 Cache Hit 不计次数，Replay 清理旧预算状态，预算前置拒绝不再形成 Provider 失败审计或触发 fallback。设置页测试/探测按凭据共享节流，远程请求至少间隔 4 秒、单并发、输出最多 64 Token；429/配额进入冷却并返回明确错误，不覆盖已有能力，未覆盖项记录 `NOT_TESTED`。完整后端 186 项、完整 Ruff、Node 24 前端 verify、文档生成一致性和 `diff --check` 通过；应用内浏览器状态读取连续两次超时，故本轮新增设置标签未完成 Browser 视觉验收。未调用真实 Provider、未 Replay、未重启服务。
- 2026-09-17：模型截断链路已修复并部署。生产审计确认截断只发生在转写校对与 Grounded Map：Ollama Profile 的上下文窗口现传入 `num_ctx`；DeepSeek 官方接口按 Stage Policy 发送 thinking 开关；空正文且 `finish_reason=length/max_tokens` 统一分类为 `AI_PROVIDER_OUTPUT_TRUNCATED`，使转写既有二分恢复生效；Grounded Map 也会按 Segment 递归二分，不再因单个长块阻塞整条视频任务。Note Chunk/Reduce 保持已有确定性兜底，默认地点物化不调用模型。后端 189 项、完整 Ruff、Node 24 前端 verify 与 `diff --check` 通过；部署前 active Job/lease=0、`integrity_check=ok`、revision=`0023`，备份 `data/backups/app-pre-truncation-chain-fix-20260917-235300.db` 完整性 ok。无 migration 重启后 API/Worker/内容/心跳 READY。现场 `job_8711f9326c474cae87a3d3c083401c55` 的 24 小时步骤续跑 Artifact 已过期，因此未绕过门禁调用真实 Provider；仍需新任务或用户明确授权完整重跑做生产 E2E。
- 2026-09-18：现场 `job_f3f791474c464126b78e6d98306eb934` 证明 Ground Map 的递归截断恢复仍可能被本地模型耗时拖垮：Qwen 3.5 9B 与 DeepSeek Flash 均多次达到 4096 输出上限，任务在第二个大块继续拆分前耗尽 1800 秒墙钟预算。Ground Map v2 针对默认 Ollama 路由预先收紧为每块最多 6000 字符/64 Segment，并要求模型省略地点空字段、合并同地点、限制事实与证据冗余；显式 Stage `chunk_size` 仍优先，截断递归兜底和全部地点候选契约不变。目标任务的 314 个 Segment 会直接分为 64/64/64/64/58，而非先发送 132 Segment 大块。全链路 16 个阶段审查后未删除阶段：条件性字幕/ASR/校对/POI/截图已有跳过或零调用路径，Normalize、Materialize、Clean Cache 保留 Transcript/Content/Replay 身份与生命周期门禁。后端 190 项、源码/测试 Ruff、Node 24 前端 18 项与生产构建、`diff --check` 通过；部署前 active Job/lease=0、`integrity_check=ok`、revision=`0023`，备份 `data/backups/app-pre-local-ground-map-v2-20260919-105010.db` 完整性 ok。无 migration 重启后 API/Worker/内容/心跳 READY；未自动调用 Provider，目标任务的步骤续跑材料随后过期。
- 2026-09-16：ASR Benchmark 第一阶段的可执行框架已进入源码：`run_asr_benchmark.py` 强制人工核对 manifest、六类场景、两条完整视频回放证据，并隔离运行 Whisper Base/Turbo 与显式本地 SenseVoice/Qwen Adapter；Qwen 自动生成无/有 Context 对照，统一评分输出 CER、coverage、时间码、RTF、内存、alignment 与候选建议。`benchmark_asr_providers.py` 仅做离线评分，始终 `production_eligible=false`，未改 `WHISPER_CPP` 默认值、Video Pipeline 或 Settings。当前没有合规语料、人工 Ground Truth、SenseVoice/Qwen Runtime 或真实回放证据，故未实际运行四引擎、未生成真实报告，不能宣称 Benchmark/生产接入完成。
- 2026-09-22：Pipeline 性能 / Token / Qwen-ASR 主计划的 WP0+WP1 开发支撑已完成：现有 Video Benchmark 导出新增 Pipeline wall time、First Useful Note、Correction coverage/input、Ground Map chunk/input/retry、AMap 请求、截图子进程及分 Stage Token/attempt/retry/fallback 指标；新增 Benchmark/后续 Production 共用的隔离 `qwen_asr_runner.py`，固定 `mlx-qwen3-asr==0.4.4`，stdout 仅输出统一 Transcript JSON，并强制真实 Forced Aligner 时间码单调与时长边界。ASR manifest 现要求至少 20 个已人工核对 clip、六类场景、至少一个 15 分钟 LONG_FORM 和两条完整视频回放证据；隔离 Runtime 已安装并通过模块 smoke，但权重、合规语料和真实 Benchmark 仍缺失，因此未进入 WP2、未注册生产 Qwen Provider、未修改 Whisper 默认值、未调用真实模型或视频。
- 2026-09-22：主计划 WP3 已完成源码实现。Transcript Quality 现统一归类人工字幕、平台生成字幕、有/无置信度本地 ASR，不再以 Whisper 名称决定策略；Whisper/Qwen/未知本地 ASR 都只把确定性异常或语义关键段作为 target，邻段只进入只读 context。校对输出强制为 Delta `changes`，未返回 target 视为 UNCHANGED，旧 `segments` 契约、重复/未知/context Segment ID 在缓存前拒绝；Segment ID、时间码和分段边界不由模型修改。Step/Baseline 同步记录 source class、target/context chars、coverage 与 input ratio。完整后端 195 项、完整源码 Ruff 与 `diff --check` 通过；未调用真实 Provider、未 Replay、未部署，WP2 仍等待真实 Qwen Benchmark Gate。
- 2026-09-22：经用户明确允许在 Benchmark 前以非默认备用方式部署，主计划 WP2、WP4–WP8 的源码实现已完成：`QWEN3_ASR` 通过隔离 Runner/本地模型路径进入 Registry，Capture 可显式选择，可信 Context 仅来自标题、平台标签和人工核对词，运行/对齐失败独立审计后回退 Whisper，默认仍为 `WHISPER_CPP`；Correction/Ground Map 的安全 chars/segments hint 按模型跨 Job 持久化，成功子块继续由 Request Cache checkpoint；Canonical Grounded Map key 不再绑定 provider/model；AMap 增加 TTL cache、同查询合并和 2 路有界并发；每个截图计划由 3 次降为 1 次 ffmpeg，核心 Note/POI/Evidence 在截图前先物化；统一 Graduation Gate 现同时检查 ASR、质量、Token 和性能。完整后端 201 项、完整源码 Ruff 与 `diff --check` 通过；Qwen 权重与真实 Frozen Benchmark 仍由用户后续执行，因此未切默认、未宣称真实毕业。
- 2026-09-22：Qwen3-ASR 运行资产已安装并启用：官方 0.6B ASR 与 Forced Aligner 权重固定在 `/Volumes/D/Projects/ollama-models/ASR/`，SHA-256 分别为 `79d6cbd4c98c7bbffe9db2edac07f56cd6637d0d5944b27f6c2b8353840323ea`、`47831d0e82f96b20e9034dba01a075ee06436654719f6a68289e49f1b65ce0e7`，生产配置已指向该目录。离线普通话 TTS smoke 真实加载 `mlx-qwen3-asr 0.4.4` 并正确识别“大理古城”，Forced Aligner 返回 7 个单调时间码；模型加载约 1.9 秒、转写/对齐约 4.8 秒、峰值内存约 1.19 GiB，生产 Provider 封装复测同样通过。完整后端 201 项、Ruff 与 `diff --check` 通过；默认仍为 Whisper，Frozen Benchmark 和默认晋级仍待用户执行。
- 2026-09-22：Pipeline 运行韧性与实时进度升级已完成并部署。真实模型请求在发出前写入同一条 `RUNNING` Audit，独立 heartbeat 续期 Job lease，Worker watchdog 可按 deadline / stale Job 收口，run fence 拒绝超时或重跑后的迟到写入；任务/API/日志页显示 active attempt、主备路由、分块、elapsed 与 deadline。Correction、Ground Map、Note Reduce 对截断先同模型拆分，最小单元才允许 fallback；Note Reduce 使用有界 Evidence Pack、跨包 checkpoint、Stage wall/attempt budget 与 Evidence-backed 确定性降级。AUTO 路由排除 capability Probe 明确失败的 Profile，人工覆盖需显式允许并审计。后端 209 项、完整 Ruff、前端 18 项/TypeScript/Vite、文档与 `diff --check` 通过；桌面及 390×844 Browser 无溢出/控制台错误。无 migration 重启后 API/Worker/首页/heartbeat READY，OpenAPI 已加载新字段；未调用真实 Provider、未重跑视频，Frozen Benchmark/真实 fallback 仍是外部验收门禁。
- 2026-09-22：VIDEO_SEMANTIC_POI_NOTE 优化已进入源码。Grounded Map 同次 Local-first 调用保存 Semantic Map v3 的 ContentUnit、Entity 角色/意图/POI Policy、Relation 与 Evidence-bound Atomic Claim；歧义只以目标段及邻段做 Remote Escalation，失败保留本地结果并走保守 Review。`REFERENCE_ONLY`/`SKIP` 不进入 AMap、Review 或手动确认；AREA 物化为 Destination，已确认 Place 才创建同 Unit 的 Destination Link。Resolver v3 在既有精度门禁上区分 `AUTO_EXACT`/`AUTO_NORMALIZED`；Note 保留模型 heading、以 Claim 驱动并去除低信息/重复 bullet。新增 12 个语义 Golden、API Gate 和迁移 0024；目标后端 108 项、Ruff 与 Node 24 前端 verify 通过。未调用真实 Provider/高德/视频，Browser 插件与项目 Playwright 均不可用，故未做渲染验收。
- 2026-09-23：视频 Job 在 `FETCH_METADATA` 完成时立即将解析标题写回 payload，运行详情刷新后显示视频标题；Job API 另返回仅限 HTTP(S) 的来源地址，任务详情页提供仅本页可见的复制按钮。API 回归、完整后端测试、Ruff、Node 24 前端 18 项/Vite/TypeScript verify 与 `diff --check` 通过。当前运行服务未重启加载这项 UI/API 变更，真实浏览器渲染未验收。
- 2026-09-23：新 Job 提交时保存无密钥 AI 配置快照，路由、Profile、Stage Policy、Prompt/Domain、转写参数、预算/重试、默认 ASR 与笔记分块在排队和重跑期间保持提交值；后续新任务使用后来设置。Alembic 0025 允许同一 VideoAsset 对应多个 Note，每次提交独立 Note/Content/Transcript，完整重跑只给所属 Note 增版本；POI 依高德 ID 复用 Place，笔记页和搜索按 Note 读 Evidence，单篇删除保留另一篇。A→B→C 离线时序、双 Note/单 Place/重跑与删除回归、隔离 0024→0025 迁移（旧 Note/Version 保留、FK/integrity ok）、完整后端、Ruff、Node 24 前端 verify 和 `diff --check` 通过；已受控加载到本机服务，未调用真实 Provider/视频。现场采样见 CURRENT_HANDOFF。

- 2026-09-23：Settings「语音与 OCR」新增可保存的默认 ASR 选择和 Qwen3-ASR 运行资产状态；仅允许在当前节点资产就绪时选择对应引擎。视频链接、本地视频及音频文件在提交时把选定 Provider 写入 Job 与无密钥配置快照，排队与完整重跑保持原值；任务详情显示提交时选择。视频 Qwen 转写失败时回退 Whisper，可信字幕仍跳过 ASR；普通音频文件失败则保留任务错误。OCR 仍由 macOS Vision 处理，尚无可切换的第二个 OCR Provider。修复 LaunchAgent 从用户主目录启动时 Qwen Runtime/Runner 相对路径失效，默认路径改为仓库绝对路径。隔离 API/Job 测试验证先 Qwen 后 Whisper 的两次提交与重跑不串设置；完整后端、Ruff、Node 24 前端验证通过。隔离浏览器桌面端验证选择、保存与刷新持久化；生产服务已加载并在桌面浏览器显示新控件，Qwen 资产探测 READY，默认仍为 Whisper。移动端浏览器与真实媒体/Provider 尚未验收，生产现场见 CURRENT_HANDOFF。

- 2026-09-23：针对 `job_ad0ba062003a492bb9ff62270bcce385` 的逐字 Qwen 对齐与校对超时，Runner 对高比例逐字输出在入库前合并语句 Segment，并在 `alignment_ms` 保留原时间码；校对按真实批次数/请求体预估预算，至少两批后用实测最快耗时判断是否应提前暂停，模型 timeout 受 Job 剩余时长约束。对该 Job 的已存片段做纯离线重放：3377 个原片段 → 71 个语句 Segment、48 个校对候选、2 批，文本及 3377 条对齐时间全部保留。目标回归、完整后端、完整源码 Ruff、Node 24 前端 18 项/TypeScript/Vite 和 `diff --check` 通过。仅完成源码与离线验证；本机服务未加载新代码，原 Job 未真实重跑，旧逐字 Transcript 需完整重跑才会得到新分段。

- 2026-09-23：该 Job 后续实际完整重跑生成 71 个 Qwen Segment，校对约 5 分钟完成，但 `EXTRACT_TRAVEL_FACTS` 的 Ground Map 第二块在本地 4096 输出上限连续截断，递归拆分使 Job 耗尽时长预算；当时 Worker 仍是 11:40 启动的旧进程，上一提交的预算/timeout 改动尚未加载。源码现让已配置备用的 `LOCAL_FIRST` 在首次截断并拆分后对子块使用备用模型；至少两个本地块证明剩余工作无法保留下游 600 秒时，后续块也切备用，保持缓存、审计和原 Evidence 契约。生产加载与真实续跑结果见 CURRENT_HANDOFF。

- 2026-09-23：已修复 Ground Map Runtime Hint 的正文字符/分块开销单位不一致；该 Job 的既有 `safe_max_chars=240`、`safe_max_segments=5` 在旧 Worker 下形成 70 块，按校对后真实 Segment 离线重算现为 17 块、每块不超过 5 段。步骤续跑中协作取消的 `JobCancelled` 现保持 `CANCELLED` 并释放 lease；对旧 Worker 已写成 `FAILED` Job + `CANCELLED` Step + 指定 run-fence 错误的状态，仅在 Replay Artifact 门禁通过时恢复原步骤续跑选项。目标与完整后端、Ruff、Node 24 前端 18 项/构建、文档生成检查和 `diff --check` 通过；生产续跑与再次加载新代码的状态见 CURRENT_HANDOFF。

- 2026-09-23：真实步骤续跑证实 Ground Map 新分块和自适应备用路由有效，地图 Artifact 已交付；后续 Note Reduce 因 Job 提交快照内主模型无 `GLOBAL_SYNTHESIS` 声明、备用模型该能力 Probe 为 `FAIL`，在模型调用前停止。现有模型能力 Probe 不测试 `GLOBAL_SYNTHESIS`，不能把结构化输出通过外推为笔记综合能力；原 Job 仍需用户明确选择合规模型/路由并保留可审计恢复证据。现场采样见 CURRENT_HANDOFF。

- 2026-09-24：笔记模型恢复链路已在源码修复：任务详情可显式选择“使用当前笔记模型继续”，服务端仅在本 Job 保存当前 Note 阶段策略和所选 Profile 的无密钥恢复配置、保留原提交快照与上游 Artifact，并在排队事件记录模型/Probe 状态；完整重跑会清除恢复配置。显式选定、Probe 为 `NOT_TESTED` 的模型可受 JSON/Evidence/预算门禁约束尝试，`FAIL` 仍被拒绝；步骤续跑的模型不可用错误会进入 `NEEDS_USER/PROVIDER_NOT_CONFIGURED`，页面显示中文业务提示。一条不改变 Job 的 DeepSeek V4 Flash 小样探测用 3 条真实 Evidence 生成 3 个有效 Segment ID 章节，JSON 合格、1055 输出 Token、未截断；这只证明小分包可行，不是整篇笔记验收。生产真实结果见下一条与 CURRENT_HANDOFF。

- 2026-09-24：加载上述恢复链路后，原 Job 明确使用 DeepSeek V4 Pro 的真实笔记归纳在首包连续截断：3 次调用的 4096 输出 Token 全部为 reasoning、正文 0；拆至单条事实后 3349 输出 Token 中仍有 2649 为 reasoning。已协作取消，保留原 Ground Map 与历史审计。源码再补 DeepSeek 笔记请求默认 `thinking=false`、每包输出预算收紧至最多约 3 条事实、只发送分包相关地点 Evidence；恢复卡可在当前 Pro 和已保存的 Flash 备用模型间做任务级选择，不改全局设置。已运行步骤取消后的续跑受 lease、Artifact 和完整重跑门禁约束。目标与完整后端、Ruff、Node 24 前端 18 项/构建、文档一致性和 `diff --check` 通过；生产真实验收见 CURRENT_HANDOFF。

- 2026-09-24：提交 `37b771a` 已无迁移加载。原 Job 在任务详情页明确选用 DeepSeek V4 Flash 后从 `GENERATE_AI_NOTE` 续跑，23/23 个笔记归纳分包全部完成，无截断或失败；笔记 Version 2 含 48 个章节、75 条逐字引文，Segment ID 与引文归属离线核对均有效，9 张截图 READY。所有 JobStep 完成，Job 为 `PARTIAL_SUCCESS`，剩余 20 个 `REVIEW`、32 个 `UNRESOLVED` 地点需人工确认；该结果证明本条视频的笔记交付，不外推为所有 Profile/视频或 POI 自动确认的质量验收。桌面与 390×844 浏览器恢复交互无溢出、无控制台错误，现场细节见 CURRENT_HANDOFF。

- 2026-10-06：至简本机路由 Provider 适配 Z1–Z4 源码完成：设置可显式选择 LocalAiMux、只读核对接口目录并保存绑定模型/地址的非密钥能力快照；测试不再固定 64 Token，主备/正式 Stage 按快照协商可选参数，保留 system/JSON/Evidence 和原有总预算门禁；修复指令前置，接口指纹/规范化版本入缓存与审计；配置类 400 不再触发临时熔断，未知 usage 以估算参与预算、不当真实 0，Mux 占位 stop 不当可靠结束证据。无数据库结构变更或单 user 业务编译。完整后端 256 项、前端 18 项/ESLint/TypeScript/Vite、Ruff/格式、合订脚本 5 项与 diff 检查通过；隔离 Edge 的 PC 1440×1000 / Mobile 390×844 交互无溢出/控制台错误。Mux 目录只读访问超时，生产/真实模型边界见 [接入规格](../ai-gateway/LOCAL_ROUTER_PROVIDER_COMPATIBILITY_SPEC.md#10-已实现的使用方式与验证入口)；没有调用真实模型/视频、改历史数据、重启服务或修改 LocalAiMux 代码。

- 2026-10-08：手动连通/能力测试取消生产熔断冷却，已保存/草稿/旧 Provider 入口共用 FIFO 整操作队列；重复点击可提交、失败释放队列，保留凭据节流和实际供应商错误，不修改生产熔断状态。旧的明确命名回环 Mux 配置在缺少接入类型时正确识别，省略不可用参数；适配 schema_version=2 目录 details，冷目录读取时限修正。完整后端 259 项、前端 18 项/verify、Ruff、PC/Mobile 隔离重复点击交互通过。已保存 codebuddy/hy3 的隔离真实连通/能力准出均 PASS；用户随后明确授权无迁移生产重载，运行 HTTP 接口混合 test/probe 也按顺序通过，既有四项小样 PASS、其余 NOT_TESTED，Probe 保存接入类型/接口能力。真实小样不代表完整视频或质量 Benchmark；范围见[接入规格](../ai-gateway/LOCAL_ROUTER_PROVIDER_COMPATIBILITY_SPEC.md#11-手动测试队列与冷却2026-10-08-修订)，带日期部署现场见 CURRENT_HANDOFF。未重跑视频、改历史业务数据或自动确认 POI。

[实施历史](../history/IMPLEMENTATION_HISTORY.md) 和 [归档实施计划](../history/planning/README.md) 保留旧状态与计划追溯，默认不读。当前页只保留最新结论和未闭环项；完成项不持续追加长叙事。生产现场只更新 CURRENT_HANDOFF.md；冻结约束只更新 REGRESSION_AND_CHANGE_GUARD.md。新增证据必须写明日期、对象与验证层级。

- 2026-10-08：订阅 CLI 调用稳定性源码完成：Mux 的安全错误码区分超时/额度/限流/鉴权/冷却，不重复同模型 HTTP 调用；偏好模式在缺少相反位置候选时保留合格全局备用，ONLY 与语义 escalation 仍不回退。已校验并保存 Profile/校对/Ground Map/Note 的 6 项新任务参数，旧 Job 配置快照未写入；参数及两仓工作包见[接入规格第 12 节](../ai-gateway/LOCAL_ROUTER_PROVIDER_COMPATIBILITY_SPEC.md#12-订阅-cli-稳定性实施与验收2026-10-08)。生产 Python 完整后端 277 项、Node 24 前端 19 项/verify、完整源码 Ruff 与本轮格式检查通过；至简已无迁移重载。Mux 本轮独立 87 项/2 ignored 与前端 7 项/Clippy 通过；叠加调用记录包后整合 95 项/2 ignored、前端 7 项及两个官方 SDK smoke 通过。安装版只读 health 已报告 600/180 秒、连接并发 1、间隔 5 秒、排队 30 秒；安装/release SHA、原 Key/权限和至简既有凭据目录访问 200 已核对。Mux schema=11 来自独立调用记录包，至简仍为 0025。未真实调用模型或重跑视频。

- 2026-10-08：设置页模型、高德与补充提示词的反馈从按钮区移至独立状态区，长提示自动换行；共享面板标题/操作栏允许整组换行，手机按钮保持 40px 热区。模型等待提示优先展示，保存加载图标只用于保存动作，保留手动测试重复排队与配置保护。前端 19 项/ESLint/TypeScript/Vite、后端 277 项、diff 检查通过；Browser 插件未提供，使用现有 Playwright 在 1440×1000/390×844 验证等待/成功/长错误/读取能力/保存、重复排队与按钮几何稳定，高德/提示词同类布局无溢出或非预期控制台错误。使用隔离 API 数据（错误用模拟 400），未真实调用模型/高德或写生产配置；8787 静态构建资源与同一界面流程已核对加载新代码，无后端重启。
