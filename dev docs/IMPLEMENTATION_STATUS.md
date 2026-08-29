# Implementation Status

更新日期：2026-08-28。当前实施目标与唯一支持的部署形态为 **Mac mini 后端**；项目不再维护其他操作系统的部署方案、测试或运行时说明。

## 已完成

- FastAPI、SQLite WAL、独立 Worker、Source/Snapshot/Segment/Claim/Evidence/Content/Job/Place/Route/Setting/Session/SystemEvent 数据模型和 Alembic 迁移；
- PC 首页显眼显示 4 位局域网配对码，可复制、轮换并撤销已有会话；5 次失败触发 10 分钟锁定，Session 使用 HttpOnly Cookie；
- `/api/status` 返回 Mac mini 的硬件、局域网地址、Worker 心跳与真实运行时检查；CPU、内存、数据盘由 API 每 30 秒采样并持久化到 SQLite，局域网访问与本机访问读取同一份快照；
- URL、正文、DOCX、PDF、XLSX、图片、音频与视频投递；图片使用 macOS Vision OCR，音视频由 FFmpeg 转为 16 kHz 单声道后交给 Whisper.cpp；
- 招聘与旅行确定性分类、招聘首批字段、旅行地点、Evidence 约束、GCJ-02 地图总览、标记逐点切换、地点详情和人工路线排序；
- DeepSeek、MiMo、Ollama Provider 配置、Keychain Secret 隔离和真实推理测试；
- PC 概览、内容、任务、来源审计、设置六分区、运行日志；手机首页、内容、投递、待办、我的、地图和路线全部为可操作 React 页面；
- JSONL 运行日志、Request ID、SQLite 审计事件、游标分页组合日志查询、详情抽屉和单条脱敏导出，设计见 `LOGGING_ARCHITECTURE.md`，操作见 `LOGGING_IMPLEMENTATION.md`；
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
- 任务和内容历史都有独立删除入口：仅终态任务可删除；删除内容不会破坏共享来源、地点或路线，具体边界见 `MODEL_AND_RETENTION_UI_SPEC.md`。
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
- 任务详情根据 Replay Options 显示“从失败步骤继续”或“从头重新运行”，不会再把整 Job 重入队描述为步骤续跑；完整契约见 `PIPELINE_STEP_REPLAY_V044_SPEC.md`。

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
- 设计见 `design/ui/v0.4.5/prompt-supplements-settings-annotated.png`，完整实现契约见 `PROMPT_SUPPLEMENTS_V045_SPEC.md`。

## 2026-08-27 转写路由、参数与来源清理 v0.4.6

- 转写校对支持独立主/备用模型；专属项优先于通用推理路由，留空时逐项继承。
- 转写每批字符、Segment 数和超时可配置，默认 `12000 / 128 / 180秒`，服务端和原生数字输入均限制安全范围。
- Prompt 补充区按阶段完整展示 6 条锁定核心契约，不再只显示一条笼统摘要。
- 来源审计页支持删除孤立来源；关联内容/视频笔记/活跃任务阻止删除。删除最后一个内容或视频笔记时自动清理孤立 Source、快照、分段及专属视频资产，Place 与路线保留。
- 完整契约与页面设计见 `AI_ROUTING_SOURCE_RETENTION_V046_SPEC.md` 和 `design/ui/v0.4.6/README.md`。
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
