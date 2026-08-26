# Architecture Decisions

## ADR-001：第一版取消云端
**Decision**
全部核心数据与计算运行在用户 PC。

**Reason**
- 单用户；
- 可接受 PC 关机时暂不处理；
- 用户明确希望先走通链路；
- 降低云部署与成本复杂度。

**Future**
可演化为 Cloud Control Plane + Home Worker。

---

## ADR-002：后端使用 FastAPI，不使用 Flask
**Decision**
FastAPI。

**Reason**
- Pydantic/Schema；
- WebSocket；
- ASGI；
- OpenAPI；
- 更适合当前 Typed Pipeline。

---

## ADR-003：FastAPI 不承担长任务
**Decision**
独立 Worker + SQLite Job Queue。

**Reason**
- ASR/视频/LLM 长任务；
- PC 重启恢复；
- CMS 可视化状态；
- 不引入 Redis/Celery。

---

## ADR-004：SQLite
**Decision**
MVP 使用 SQLite + WAL。

**Reason**
- 单机；
- 数据规模小；
- 部署简单；
- 可满足关系模型与全文检索基础需求。

---

## ADR-005：产品只做两个场景
**Decision**
Recruitment + TravelFood。

**Reason**
- 真实高频需求；
- 避免应用成为杂乱收藏箱。

**Future**
Processor Router 保留扩展。

---

## ADR-006：Unknown 不自动归类
**Decision**
第一版 Unknown → Unsupported。

**Reason**
- 保持产品干净；
- 不让 AI 擅自创建分类；
- 后续 GenericProcessor 再接入。

---

## ADR-007：Evidence First
**Decision**
事实 Claim 必须证据化。

**Reason**
- 招聘是高风险判断；
- 用户明确禁止 AI 随意发挥；
- 未来 GenericProcessor 同样需要可信度。

---

## ADR-008：Requirement DSL
**Decision**
招聘条件必须转 AST，不让 LLM 每次重新理解。

**Reason**
- 可测试；
- 可重放；
- 可审计；
- 逻辑嵌套。

---

## ADR-009：专业语义只 REVIEW
**Decision**
Semantic Major Match 不自动 PASS。

**Reason**
招聘单位认定可能与 AI 语义不同。

---

## ADR-010：Eligibility 与 Preference 分离
**Decision**
资格、偏好、紧急程度分别建模。

**Reason**
避免“匹配度 92%”混合多重含义。

---

## ADR-011：PlaceMention 与 Place 分离
**Decision**
视频提及与现实 POI 两层。

**Reason**
- 多来源去重；
- POI 解析可审核；
- 坐标可信。

---

## ADR-012：本地优先 + 外部 LLM 口子
**Decision**
LLMProvider 抽象，默认 LOCAL_FIRST。

**Reason**
- 利用 Mac mini 的本地 Metal 运行时；
- 可离线；
- 外部强模型用于增强；
- 不锁厂商。

---

## ADR-013：ASR 抽象
**Decision**
ASRProvider，Mac mini 首选 whisper.cpp Metal 路线。

**Reason**
避免锁 CUDA/faster-whisper。

---

## ADR-014：Control Center 是 MVP
**Decision**
后台控制台不是后置。

**Reason**
用户明确需要看见系统处理过程并管理配置。

---

## ADR-015：Pipeline Replay
**Decision**
步骤结果持久化，可单步重跑。

**Reason**
模型升级、解析纠错、节省视频/网页重复抓取。

---

## ADR-016：Partial Materialization
**Decision**
长任务允许部分结果提前展示。

**Reason**
提升 43 地点/数百岗位等任务 UX。

---

## ADR-017：Narrow Product, Extensible Core
**Decision**
UI 窄，接口宽。

**Reason**
兼顾第一版速度与长期 GenericProcessor 演进。

---

## ADR-018：MVP 支持可信局域网手机访问
**Decision**
PC 仍是唯一数据与计算节点；手机通过同一可信局域网访问响应式 Web。REST/WebSocket/Admin API 必须验证本机生成的访问 Token，不自动暴露公网。

**Reason**
- 手机是“随手分享/查看结果”的必要入口；
- 不为此提前引入云端与多用户体系；
- LAN 已扩大攻击面，认证不能后置。

---

## ADR-019：招聘文档矩阵包含 DOCX 与 OCR
**Decision**
MVP 支持 PDF、扫描 PDF、DOCX、XLS/XLSX、PNG/JPEG；OCR 结果保存页码、边界框和置信度，低置信关键事实进入 Review。

**Reason**
北京市公务员/事业单位公告附件并不只使用文本型 PDF/Excel，缺少 DOCX/OCR 会造成真实链路断裂。

---

## ADR-020：中国 POI 首选高德并显式使用 GCJ-02
**Decision**
MVP 实现 AMapPOIProvider 和高德地图 JS API 2.0。中国大陆高德坐标存储为 `GCJ02`，导出必须标注坐标系。

**Reason**
- 第一版旅行范围为中国；
- 高德同时提供 POI 搜索与 PC/移动 Web 地图；
- 显式坐标系避免地图显示与 GeoJSON 语义错误。

---

## ADR-021：外部模型通过兼容 Provider 接入且敏感档案默认不外发
**Decision**
DeepSeek、Xiaomi MiMo 等通过 OpenAICompatibleProvider 配置；模型名不写死。`SENSITIVE` Profile 默认不外发，`LOCAL_ONLY` 永不外发。

**Reason**
- Provider 与模型会持续变化；
- 招聘 Profile 涉及学历、工作经历、政治面貌和户籍；
- 最小化外发符合 Local First。

---

## ADR-022：真实 URL 手工验收，冻结 Fixture 用于 CI
**Decision**
微信/Bilibili 真实链接用于手工验收；CI 使用脱敏冻结 Fixture，不依赖实时平台网络。

**Reason**
- 平台存在登录态、验证码、风控、412 与内容变化；
- 实时网络依赖无法提供可复现测试；
- 不绕过平台访问限制。

---

## ADR-023：视频 AI 笔记参考 BiliNote，但由至简领域模型承接
**Decision**
Bilibili 视频链路优先适配 BiliNote 已验证的 URL/分 P 解析、平台字幕优先、yt-dlp 音频 fallback、Transcript、长文本分块与 Markdown 后处理轮子。BiliNote 代码只进入第三方适配层；任务运行使用至简持久 Worker，结果使用至简 Source/Snapshot/Segment/Claim/Evidence/Place/Note Version。MVP 默认以已配置 DeepSeek Provider 生成视频 AI 笔记和旅行结构化结果。

**Reason**
- 平台字幕、Cookie、风控和媒体下载存在大量已知边界，重复实现风险高；
- BiliNote 的单体 NoteGenerator、BackgroundTasks 和 JSON 状态文件不满足至简的恢复、审计与 Evidence 要求；
- AI 视频笔记和地点归纳笔记是产品一级产物，不能只把视频当地点抽取中间件；
- 适配层隔离便于跟踪上游修复并履行 MIT License。

完整契约见 `VIDEO_AI_NOTE_PIPELINE.md`。

---

## ADR-024：代表性截图、细粒度地点与中国全境地图
**Decision**
视频 AI 笔记必须生成与章节/地点时间码绑定的代表性截图；默认通过受限画质视频下载和 FFmpeg 确定性抽帧，不启用全视频多模态理解。旅行地点粒度扩展到餐馆、景区、街区、步行街、商圈、市场等，并由高德校正名称与 POI。地图以中国大陆全境为初始 viewport，按 bbox/zoom 加载和聚合，无默认城市；Marker 支持用户新增、隐藏、软删除和恢复，点击后先显示地图浮窗，再进入统一 Place Detail。

**Reason**
- 纯文字笔记难以快速建立视频场景记忆，代表帧能显著提升地点和菜品辨识；
- ASR 容易产生同音错字，真实地图 Provider 校名比 LLM 猜测可靠；
- 旅行内容跨中国多个城市，硬编码厦门会错误限制产品范围；
- Marker 是 Place 的地图投影，用户管理可见性不能破坏来源、Evidence 与跨来源聚合；
- JS 地图和 Web POI 使用不同 Key/安全边界，需要在设置中分别配置与诊断。

---

## ADR-025：粘贴分享文案先规范化为唯一链接
**Decision**
Capture 接受完整原始粘贴值，并在创建 Source/Job 前区分纯 URL、带标题/分享话术的唯一 URL、无链接正文和多 URL。唯一 URL 被选中后，只有 URL 进入 Resolver、Classifier 与 LLM；周围标题和分享文字被丢弃。多个不同内容 URL 无法唯一确定时返回 `CAPTURE_MULTIPLE_URLS`，不静默选第一个。

**Reason**
- 手机和内容平台复制出的通常是“标题 + 链接 + 复制打开”整段文案；
- 以 `startsWith("http")` 判断会把合法分享链接误当正文；
- 分享标题可能不准确或包含推广文字，不能覆盖来源正式元数据；
- 多链接静默取第一个可能处理错误内容并触发非预期网络访问；
- 只持久化选中 URL 和最小审计字段可以减少无关聊天/分享文字留存。

---

## ADR-026：运行日志通过 Job 服务触发步骤级续跑

**Decision**
`ERROR/CRITICAL` 审计事件规范关联 Job/Step 后，日志页查询 Replay Options。中间产物有效时，调用 Job 服务从失败步骤继续；上游完成步骤标记 REUSED，当前及下游顺次执行。中间产物过期后禁用步骤续跑，只允许完整重跑。日志模块不得写 JobStep、调用 Processor 或允许任意 from_step。

**Reason**
- 当前错误事件已经通过 `entity_type=job / entity_id` 建立可靠关联，现场 ERROR 事件均可定位所属 Job；
- 步骤中间产物默认保留 24 小时，可以可靠避免重复下载、ASR 和上游模型调用；
- 点击历史错误时任务可能已重新运行或完成，必须读取 Job 当前状态，不能按旧消息直接执行；
- 把来源事件 ID 写入 `job.step_replay.queued` 可形成“错误 → 用户确认 → 新 attempt → 当前/下游步骤”的审计链；
- Artifact、输入哈希、版本与 TTL 由 Job 服务统一判断，日志 UI 只展示可用动作；
- 完整重跑仍保留，但不能冒充步骤级恢复。

---

## ADR-027：视频笔记以 AI 校对稿和时间线主旨组织阅读

**Decision**
视频笔记详情在 Hero 后优先显示摘要、主旨目录和时间线正文，地点候选与完整转写放文章底部；Hero 使用真实 CoverAsset，缺省时为空/收起。Transcript 保留 raw/corrected 双版本，Note、目录、默认预览和 TXT 导出使用 AI corrected_text。目录由具体 heading/thesis 组成，所有时间码跳转稳定 Section 锚点。正文是按时间线组织的摘要、要点和地点引用；关键截图以侧排缩略图嵌入 Section 并提供 contain Lightbox。

**Reason**
- 地点和 Transcript 是回查工具，应在正文底部集中呈现而不打断阅读；
- 口音和 ASR 错字会污染摘要、地名和目录，必须先校对再总结；
- 原始转录堆叠不等于可读笔记，目录套话也无法帮助定位；
- 时间码若不能跳到段落，就失去阅读导航价值；
- 独立截图宫格割裂上下文，章节起始帧也未必是关键内容；
- raw Transcript 仍需保留以满足 Evidence 和校对审计。

---

## ADR-028：视频笔记列表使用本地持久封面资产

**Decision**
VideoAsset 元数据中的 Bilibili `pic/cover` URL 进入独立 `FETCH_COVER`：HTTPS/host/SSRF、状态、MIME、文件头、尺寸和字节校验后，按 SHA-256 保存原图并生成 672×378 WebP。列表只使用本地 Cover API，封面失败显示稳定占位但不阻塞 Note。顶部主操作文案统一为“添加视频链接”，复用全局 Primary Button。

**Reason**
- 长期远程热链受协议、Referer、CDN 变化和网络状态影响；
- 视频元数据已经提供原始封面，无需 LLM 或从视频帧猜测；
- 本地派生图便于缓存、离线浏览和统一 16:9 布局；
- 封面属于非核心增强，不应导致完整视频笔记失败；
- “投递”是系统术语，“添加视频链接”更符合用户动作；
- 参考项目已验证 `pic/cover → GET → Content-Type → 本地文件` 的可行性。

---

## ADR-029：删除视频笔记不删除共享来源与证据

**Decision**
列表和详情通过统一 Delete Service 删除 AINote、版本、Section、TOC 和 Content 投影；保留 Source、VideoAsset、CoverAsset、Transcript、Place、Claim/Evidence 和其他对象引用的 Screenshot。活跃生成 Job 阻止删除，第一版确认后不可恢复。

**Reason**
- 同一视频资产、转写和地点可被多个 Note/Place 复用；
- 删除阅读产物不应破坏来源审计和地图；
- 同步级联删除大文件风险高，孤立资产应由引用计数和保留策略清理；
- 列表与详情需要一致语义，不能各自维护删除边界。

---

## ADR-030：Worker 存活心跳、任务活动与取消确认分离

**Decision**
Worker 进程使用独立于同步 Job 执行循环的周期性心跳报告存活；Job 只在真实阶段、批次开始/结束或可观测外部调用边界更新自身活动时间。长模型步骤在每次批量请求前后检查取消状态，停止未开始批次，并在释放 lease 后才允许完整重跑。任务详情的完整重跑能力由服务端返回，不由前端按状态字符串硬编码。

**Reason**
- 单 Worker 被长模型请求占用时，外层领取循环不能刷新全局心跳，造成“Worker 延迟”的误报；
- 将全局心跳写入 Job 会掩盖真实任务无进度，因此两者不能复用；
- 转写校对会把 232 段拆为约 29 个模型批次，取消只在整步结束观察会继续消耗模型与占用 Worker；
- 已取消但 lease 未释放时必须防止并发完整重跑，释放后又不能因为 UI 漏掉 `CANCELLED` 而永久不可操作；
- 操作能力由服务端统一生成可消除任务详情、日志抽屉与未来客户端之间的状态分歧。
