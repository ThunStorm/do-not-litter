# 当前实施状态

> 状态记录日期：2026-10-23。本文唯一记录当前源码能力与自动验证；生产状态只见带原采样日期的 [CURRENT_HANDOFF.md](CURRENT_HANDOFF.md)。

## 当前冻结范围

- 当前分支为 `codex/mac-mini-implementation`；本轮交付包含标题时间证据/分包 Prompt、同模型重跑配置与 Z0–Z7 请求优化核心；Z8 保持独立 backlog，不修改 LocalAiMux。
- 仓库 Alembic head 为 0025；生产版本由交接现场证明，不由仓库推断。本轮无 Schema 变更；重新部署和已授权真实模型/视频矩阵另由交接及验收报告证明。
- 唯一支持的后端为 Mac mini，FastAPI、SQLite/WAL 与独立 Worker；单用户通过可信局域网访问。
- 源码实现、离线验证、生产加载与真实业务验收分别记录。规格中的待实施项、历史工作包和新草案不自动成为已授权任务。

## 当前能力

2026-10-23 概览长链接列宽修复：dashboard-grid两列改为minmax(0,1.55fr)/minmax(0,1fr)，直接子项、任务标题行及标题允许收缩；标题保留单行省略、状态与进度及详情入口不变。仅CSS。隔离Browser以1277字符URL模拟未识别标题，1208px两列543.4/350.6px保持原比例，970/390px单列无横向溢出，标题被截断；生产1208/390px真实数据布局通过。后端547/前端34、ESLint/类型/隔离构建及仅本包HEAD副本构建通过；只发布静态资源，未重启服务、保存业务配置或触发模型/视频。保存点与HTTP哈希见交接。

2026-10-23 LocalAiMux共享凭据与模型输入：同Provider/规范化完整服务地址共享Keychain凭据；自动复用一致的历史Key，无凭据或冲突提示填写，不再选择模型凭据。新Key保存后同地址模型与Worker统一优先使用；目录/能力/草稿测试/探测/保存均复用，凭据状态API只返回布尔值，页面显示掩码状态不回传明文。新增草稿选择Mux后自动只读目录，其他服务不自动读取；换地址不携带旧Key。模型框右侧两图标刷新/切换输入，原位手动输入保值，补充接入方式说明。后端全量547、前端34、Ruff/ESLint/类型/隔离构建通过；HEAD隔离提交副本目标回归与构建通过。生产970×876/390×844自动读取49模型、搜索选择Kimi、原位输入/切换保值、缺Key提示及无溢出通过；备份/哈希/服务现场见交接。无迁移、真实模型调用、配置保存或历史数据改写。

2026-10-22 阶段说明留白：阶段表单与说明共用PC 20px/Mobile 16px内边距，底部20px、段落8px，折叠入口40px；重置说明段落默认margin，复用Caption与muted Token，7个阶段同步对齐。当前工作树后端543/前端31、Ruff/ESLint/TypeScript/隔离构建通过；本次提交范围另在HEAD隔离副本通过类型与构建。隔离与生产970×876/390×844验证展开/收起、键盘及自然换行，无横向溢出/框架覆盖层/相关控制台错误；仅浏览读取和折叠，未保存模型设置或发起真实调用。无Schema/API改动；生产保存点与静态资源哈希见交接。其他在途工作包不随本次提交。

2026-10-14 标题时间证据：新增确定性 TITLE_METADATA 解析/范围投影，仅明确推荐且适用的地点继承；行程/记录、背景、否定、地域/主题不匹配及正文时间优先均保守拒绝。TITLE_CONTEXT 窗口保持真实 source_id/标题原文且无伪 Segment，按来源/提及/时间/文本哈希对账，重放保持 ID、地点重新绑定正确迁移且人工窗口不删除；API 区分 source_kind 并保护派生窗口。Ground Map 缓存身份包含标题上下文/解析版本；Claim 优先 subject_entity_ids，歧义不按同段广播，模型包保留 ContentUnit 并仅含当前包相关地点/Segment/引文。笔记摘要/fallback 按地点显示标题来源，前端地点详情区分标题/正文。稳定系统指令前置，请求增加前缀/Prompt 哈希、长度与字节范围观测，应用缓存不冒充 Provider 上报缓存；复用既有编译器、ID/外键/人工 POI 门禁，无 Schema/LocalAiMux 变更。[契约](video/TITLE_TEMPORAL_EVIDENCE.md)、[离线 A/B](benchmark/TITLE_TEMPORAL_PROMPT_AB_REPORT.md)记录合成增量及真实质量/Token UNKNOWN；真实模型/视频和会话缓存未执行。新增17项标题证据回归及1项前端出处/删除保护测试；目标110项、后端全量458项、前端24项与完整源码/测试Ruff、ESLint、TypeScript、隔离Vite构建通过。最终HTTPX请求体字节计量六入口对照、相关目标108项及末次全量458项通过；首次全量的旧分包测试缺失Segment范围，按新证据契约补全并扩展非法范围断言后复跑全量通过。生产1440/390px目标Browser通过，浏览器新增时间与删除响应均拦截模拟；实际服务/资源哈希/历史数据核对只见[交接快照](CURRENT_HANDOFF.md)。

2026-10-14 截图保存前压缩：选帧与去重后保持原分辨率，按 WebP 85/90/95 与无损后备尝试，RGB PSNR≥38 dB 且体积至少减少5%才采用；编码/写入失败或无收益保留JPEG，先完整写入并原子替换后登记最终路径与SHA-256。图片接口及Vision请求兼容JPEG/WebP MIME，无新增依赖/Schema；旧截图不自动重编码。11项新增回归覆盖细小彩字无损后备、普通抽样JPEG压缩、画质/体积拒绝、编码/磁盘失败回退、最终文件哈希及两种格式的读取/模拟Vision请求；相关目标15项、后端全量441项、前端23项及完整后端Ruff、ESLint、TypeScript、隔离Vite构建通过。441张现有JPEG的临时副本离线实测426张采用压缩、15张保留，63,817,940→45,527,644字节，减少28.66%，采用压缩的最低PSNR38.1802 dB、单张编码中位87.54ms；最低PSNR样本标题/字幕可辨认，不替代全面OCR/语义验收。忽略目录 `data/benchmarks/screenshot-compression-20261014/report.json` 保存逐文件哈希与指标，原截图逐张字节核对未改。源码验收阶段未提交/部署或触发真实Provider/视频重跑；后续已按用户授权无迁移重载API/Worker，新截图保存链路已加载压缩逻辑，生产核对及首张真实新图未采集的边界见[交接快照](CURRENT_HANDOFF.md)。契约见[截图与物化](video/03-generation-materialization.md#414-extract_screenshots)。

2026-10-14 系统指令传递纳入独立接口小样和普通能力探测；已保存模型读取目录后将小样加入Worker队列，配置未保存时提示先保存。折叠卡测试反馈处独立展示通过、未通过、未验证、未测试、探测中及目录声明/脱敏错误；保留采样时间与接口指纹，配置变更清除旧结果，执行中变更拒绝保存。角色冲突小样不提升目录声明、不授予业务能力、不解除正式Stage门禁。目标5项、后端全量430项、前端23项及源码Ruff、ESLint、TypeScript、隔离构建通过；PC1159/390px覆盖五状态与入队交互，无溢出或相关console错误（推理返回与入队均模拟，真实Provider未调用）。无Schema迁移；生产现场见交接快照。

2026-10-13 已保存模型显示通过能力中文标签，并提供整卡拖动排序及上移/下移；指针捕获让整张卡片跟随移动，相邻卡片动画让位、目标显示插入线，松开自动保存，失败恢复原顺序，取消清除效果。顺序独立保存，更新/探测不再按更新时间冒泡，新模型排末尾；完整ID排列校验不改变推理路由，无Schema迁移。整卡位移/让位/取消目标测试、后端全量、前端23项及ESLint、TypeScript、隔离Vite构建通过。已发布生产静态包，Browser 1081/390px实际拖动换位成功，刷新持久化后恢复原顺序，页面无横向溢出/相关console错误；此前拖拽未验收项已闭环。未触发真实模型调用；生产现场见交接快照。

2026-10-12 Mux模型目录修复：实机冷标准目录10.16秒、随后能力目录0.03秒，两者56个实际ID一致；确认新下拉刷新接口的5秒读取上限导致失败。读取等待改20秒、连接5秒、总期限30秒并按剩余预算收紧；列表与模型保存能力读取共用实际ID校验，仅排除owned_by=localmux的free/cheap/balanced/best虚拟路由，实际差异/重复仍拒绝，下拉返回实际模型。超时/HTTP状态/目录不一致/异常响应分别给脱敏提示。目标69项、后端全量424项、前端22项及源码/测试Ruff、前端Lint/TypeScript/隔离Vite构建通过；生产接口HTTP200返回56项，设置页刷新/搜索通过，原型号保留，无相关console错误；无迁移部署现场见交接。只读目录验证不代表真实推理或模型质量。

2026-10-12 模型设置收敛：有标题的“已保存模型”父section包含说明、批量反馈、内缩子卡片、新增表单及空态；各模型默认收起、编辑保留、新增默认展开，共享IconButton支持键盘/ARIA。模型名改为可搜索SelectMenu，支持手动填写及显式刷新目录；新增POST /api/settings/model-catalog读取标准/Ollama/Mux元数据，Mux双目录实际ID须一致，标准目录中的虚拟路由独立识别。连接变更不复用跨origin/服务来源的旧Key，响应限时限量/无重定向，精确ID/凭据反射校验，过期结果不覆盖新连接/模型；失败保留原值，不保存配置或创建推理任务。新增目录18项、后端全量418、前端22及源码/测试Ruff、ESLint/TypeScript/隔离Vite构建通过；内置Browser验证父子包含、独立折叠、编辑保留、新增、搜索/选择、模拟刷新/失败、手动输入、长名称与PC/390px，修复长名称撑宽和相邻控件拉伸。沿用部署更新要求完成无迁移发布；真实目录采样及生产页面/数据证据见[交接快照](CURRENT_HANDOFF.md)，完整契约见[模型设置](ai-gateway/MODEL_AND_RETENTION_UI_SPEC.md)。未触发模型推理、真实测试/能力探测、视频生成或POI确认。

2026-10-12 视频笔记风格入口撤下：移除详情页选择器、前端风格状态/类型和生成请求的风格参数，普通重新生成走后端默认；Render Profile 接口/历史版本字段继续预留，契约见 [生成与物化](video/03-generation-materialization.md#笔记风格接口预留与生成模型标注2026-10-12)。详情 API 从当前 Note Version 返回生成 Provider/模型，右上角用 Caption 显示 `By 模型名`，不加“AI 生成”字样；缺失/待生成明确提示，长名称截断并可通过 title 查看模型名。目标 2 项、后端全量 400 项、前端 21 项及源码/测试 Ruff、ESLint/TypeScript/隔离 Vite 构建通过；包含历史迁移的 backend 全目录 Ruff 仍有 28 条既有问题，未修改历史迁移。Edge/Playwright 在隔离 SQLite 快照与构建包上验证 PC 1440px/876px、手机 390px、真实样本的历史模型、模拟长名称/缺失/待生成、菜单展开与拦截重新生成请求，无溢出/相关控制台错误。随后最终 By 文案通过目标 ESLint 和隔离构建，已授权无迁移部署与生产 Browser 验收见 [交接生产快照](CURRENT_HANDOFF.md)；无 Schema 变更或真实模型/视频生成。

| 领域 | 已进入源码的能力 | 契约入口 |
| --- | --- | --- |
| Capture / 基础 | URL、正文、DOCX、PDF、XLSX、图像 OCR、音视频；局域网配对与 Session；Source/Evidence | product/PRODUCT_REQUIREMENTS.md、architecture/SECURITY_PRIVACY.md |
| 招聘 / 旅行 | 首批招聘结构化与证据；Place Insight、POI Review、全国交互地图、Marker 生命周期、地点管理/人工路线；POI Resolver Golden、事实归一化、跨来源共识/冲突、地点知识 API/证据跳转；月份/日期 Visit Window 状态、可重算 Preference Event 与确定性可解释推荐；Visual Fact 实验性截图任务、Vision Profile Skip 与离线 Golden | product/TRAVEL_FOOD_PIPELINE.md、ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md |
| 视频 | 字幕优先、ASR、校对、Semantic Map v3（ContentUnit、实体角色、关系、Atomic Claim）、同链接每次提交独立 Note/Content/Transcript Version、共享规范 Place、自适应笔记/章节、地点、Destination、截图、列表封面、保留式删除 | video/VIDEO_AI_NOTE_PIPELINE.md（分篇索引） |
| Bilibili 登录恢复 | 站内扫码、nav 账号验证、Keychain 保存；登录失败进入 NEEDS_USER；核心恢复与非核心截图显式跳过；字幕多轨与官方 CDN Host Policy | video/02-input-transcript.md |
| Job / Replay | 独立 Worker 心跳、协作取消、租约门禁、终态表达、步骤续跑和完整重跑；新任务冻结提交意图，重跑自动刷新同模型必要执行配置并保留执行历史；HTTP/间隔/资源锁等待协作取消，ASR 进程组回收与活动提示；Replay Options 由后端决定 | jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md |
| Gateway | 显式 Profile/Stage Policy、接口能力协商、LocalAiMux 接入与手动测试 FIFO；Map/Reduce、Cache、Budget、Domain Context、Vision 边界；凭据从 Secret Store 读取 | ai-gateway/AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md（分篇索引） |
| 稳定性 | 每次实际 Provider 尝试执行预算与本地 OS flock；LOCAL/REMOTE 分账，可信 Token、字符估算和未知分开，Cache hit 不重复计耗；超时不重复同模型请求 | ai-gateway/02-gateway-context.md、ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md |
| 产品 / 运维 | PC/手机 Web、真实状态快照、自定义模型/补充 Prompt、JSONL + SQLite 审计、运维工作台 | product/CONTROL_CENTER.md、operations/LOGGING.md |
| 部署 | Mac mini LaunchAgent 双服务、外置生产 venv Python 3.14、健康内容与 Worker 心跳门禁 | operations/DEPLOYMENT_OPTIONS.md、CURRENT_HANDOFF.md |

## 最新自动验证

2026-10-12 入口隔离、正常分批及同模型续跑补修：单批尝试与正常计划批次数分开，保留累计硬预算；v2调用经验、原始响应缓存与地图语义产物按实际入口/账户摘要/模型参数隔离，旧模型名经验不借用。新提交固定当前设置，续跑刷新原身份模型最新生成/上下文/稳定性参数，阶段参数刷新受原路由/模型池归属约束。Ollama使用原生阶段JSON Schema，本地地图4096输出默认最多16段，模型默认温度独立保存、继承表单保留来源状态，思考耗尽且无正文单独诊断停止拆分，商汤三类模型与OpenRouter按实际入口映射关闭思考，手动探测同步关闭思考；间隔按实际发出时间复核，等待使用墙钟避免取消检查放大时长；笔记减少重复地点窗口提取规则，LOCAL_ONLY禁止歧义复核借用全局远程入口；提示删除悬空关系示例，严格保留Evidence引用校验。后端全量400、补充目标及继承/预算测试及Ruff通过；前端21、ESLint/TypeScript/隔离构建通过，Browser1095×876/390×844只读核对中文“单批最多模型尝试”、模型默认温度及留空继承、无溢出/相关错误。无迁移；授权真实视频结果与模型质量边界见[指定视频矩阵](benchmark/AI_ENTRY_ISOLATION_BV1eAew6UEvG_REPORT.md)，生产现场见带日期交接。

2026-10-11 本地模型测试间隔补修：LOCAL或Ollama统一共用本地硬件分组，不因Provider/入口、直连模式或Base URL缺失绕过串行；每次测试/探测子调用结束（含失败）后至少5秒，前后配置间隔/RPM更长取更长，共享完成时间和期限跨API/Worker/模型保留。已保存/草稿探测统一先分组锁再硬件锁，避免与Worker反向取锁。队列目标21项（新增10项覆盖成功/失败、较长间隔、跨Provider/入口与锁顺序）、后端全量379及Ruff通过；前端19/ESLint/TypeScript/隔离Vite通过，生产Browser1095与390px只读核对明确说明、无溢出/相关console错误。未重新触发真实模型推理；加载和备份证据见[交接生产快照](CURRENT_HANDOFF.md)，契约见[模型测试队列](ai-gateway/MODEL_AND_RETENTION_UI_SPEC.md#11-已保存模型测试队列2026-10-11)。

2026-10-11 已保存模型测试队列：新增一键真实测试+能力探测，单模型按钮共用MODEL_TEST Worker通道，不进入业务任务列表/首页计数；同供应商/入口FIFO和跨进程文件锁，独立最多三组并行，本地硬件仍串行，尊重间隔/RPM且远程至少4秒，429等共享至少60秒/Retry-After冷却，不自动重试或备用。重复在途同项复用，每模型独立结果/续租/fence与取消，错误不影响其他入口，晚结果不覆盖新执行；模型身份变化拒绝旧测试，凭据不进Job。PC1095与390px在隔离SQLite/模拟模型上通过一键、持续单点/去重、分组并发、失败/取消隔离、未保存编辑保留、进度和无溢出/相关console错误验收；外部Edge稳定帧/截图阻塞，改用Codex内置Browser完成。新增队列11项（含真实凭据存储初始化及首页计数隔离），自动测试使用临时模型/硬件锁避免干扰生产；后端全量369、前端19及Ruff/ESLint/TypeScript/隔离Vite通过，无迁移。真实已保存模型测试与生产加载另见带日期交接快照；完整契约见[模型设置](ai-gateway/MODEL_AND_RETENTION_UI_SPEC.md#11-已保存模型测试队列2026-10-11)。

2026-10-11 能力门禁与探测400修复：针对3bebb50笔记小样的版式/固定措辞限制，使用独立note-synthesis-v2；允许合并/拆分/调整章节，以来源、逐字引文、事实证据和有限数字/推荐方向检查判定，歧义为未验证，旧版/过期笔记评估不冒充PASS，历史裸FAIL/新版有效FAIL保守拦截，显式允许仍审计。按用户确认，每次阶段选模独立读取同身份模型最新已保存探测/业务评估，绕过旧事务/ORM缓存并固定本阶段判定；新PASS替代快照旧FAIL，新FAIL影响下一阶段，原模型/路由/生成参数/声明/预算和历史快照保留。同模型重跑入队刷新最新评估，不借用不同身份结果，原重跑身份门禁保留。ai.capability.checked及调用审计记录状态/更新时间/来源/哈希；能力拒绝与未配置错误分离。结构化探测明确JSON指令，HTTP失败记录具体小样、状态/脱敏厂商原因；格式可解析不自动开启DIRECT原生JSON，失败/截断不覆盖旧结果，限长小样诊断保留。专项32、目标97、后端全量358、完整Ruff及改动文件格式通过；Node24前端19/ESLint/TypeScript/隔离Vite构建通过。全库原有29文件格式差异未扩张修正，前端未改代码或重复Browser。只读复核job_b232da84…：校对成功、地图两次截断拆分恢复，笔记无请求，被v1 FAIL拦截；加载前API返回v1 FAIL且13:29探测仍写v1，确认当时修复未加载。源码验收时未提交/部署/重启、真实探测/续跑或改生产数据；随后已按用户授权无迁移加载并完成只读现场验收，证据见[交接生产快照](CURRENT_HANDOFF.md)。小样不证明全面语义质量，契约/回归入口见[模型边界](ai-gateway/01-architecture-models.md#笔记归纳小样与有效结论2026-10-11)、[任务策略](ai-gateway/05-job-policy.md)。

2026-10-10 高德QPS补修：指定视频5项UNRESOLVED只读归因为账号接口QPS超限；Provider统一API/Worker跨进程请求间隔1.1秒、QPS/HTTP429后5秒冷却、不自动重试，缓存/同查询合并按Key哈希隔离，HTTP错误不带请求URL。新增跨进程/不同Key/失败冷却测试，后端全量326、目标11及HTTP错误补测5、Ruff通过，前端19/ESLint/TypeScript/隔离Vite构建通过。未改变前端行为或重复Browser，未增加真实Provider请求/改历史地点。6项地点及12个校对段的本机人审清单已生成；仍须人工核对与实机账号配额验收。

2026-10-10 指定视频真实验收：BV11Ao7BYE1V（479秒）达到PARTIAL_SUCCESS，Note v2有14章节和12截图，0确认/1REVIEW/5UNRESOLVED/5AREA_RESOLVED/6SKIPPED。AI字幕拒绝后使用当前用户已保存的Qwen3-ASR；50段/12校对，Source/BV/CID/时轴及当前实体17/Claim33/章节quote16的引用与逐字校验通过。阶段0重试补修43f42ff加载后只续跑笔记，上游8步REUSED；全任务实际尝试10（含旧失败/修复/取消），保留审计，未超12次。原有Job/Note/Segment/Transcript与模型配置不改；PC/390px阅读/截图弹层通过。人审词准率/地名/现实POI、上游精确型号、计费Token和完整矩阵未证明，见 [视频验收](benchmark/VIDEO_E2E_BV11Ao7BYE1V_REPORT.md)。

2026-10-10 视频实测补修：显式 Stage retry_count 同时限制 HTTP 与 JSON 修复重试，0 不再继承 Profile 的 JSON 重发；完整 JSON 对象后的最多两个多余闭合括号受控修复，规则、quote 与全量验证保留；输出字符估算取原始响应 content_length，避免短 ID 解码后的 canonical 字符膨胀。后端全量 322、前端19及静态/类型/隔离构建通过；首次视频执行的失败/修复/取消审计保留，部署与续跑结果另见交接。

2026-10-10 真实模型小样：在现有 Mux 标准接口上串行执行 1 次 Text 与 2 次 Ground Map JSON（代码3bebb50、请求型号codebuddy/glm-5.3），两次 JSON DIRECT_VALID、短 ID 还原与逐字 Evidence 通过；两处景点、参考政策和价格/月季/否定/推荐食物/排队事实检查通过。输入为六段自建合成文本，N=1、请求字节3534→3330，不代表真实视频人审质量；实际型号、Token、finish_reason仍UNKNOWN，原生JSON/温度/输出上限不支持。未保存模型能力标记或改配置/历史结果；当前真实验收范围与风险见 [真实小样](benchmark/AI_REQUEST_OPTIMIZATION_LIVE_SAMPLE.json)、[A/B 记录](benchmark/AI_REQUEST_OPTIMIZATION_AB_REPORT.md)。本轮只写验收文档，不重复业务测试或部署。

2026-10-10 请求优化核心：请求编译器仅在模型边界短 ID 化，按 Snapshot/内容/版本/映射绑定 Cache；校对去重上下文、限制 targets，Ground Map 局部事实 ID 按来源区间命名，笔记仅去除可由事实包恢复的重复 quote，完整上下文不静默截尾。格式 smoke 与四类业务小样分开，旧 smoke PASS/过期小样不证明质量，AUTO 未验证路由显式审计；统一等待/请求期限与实际尝试门禁，模型 JSON 修复默认关闭，结果解析质量与执行路径分型。复用 JobStep/Fence，附加 Attempt 状态与数值/哈希诊断；LocalMux 遥测白名单，任务调用明细中文化，旧审计可读。来源/空 quote/越界 Segment 阻止 POI 自动确认，复用现有 Review 与严格 resolver。后端全量 320 项通过，末次诊断目标 74 项与 Ruff 通过；前端 19 项及 ESLint/TypeScript/Vite 通过，隔离 PC/390px 调用明细验收无溢出/错误。18 场景合成请求字节减少 36.77%，只证明表示与往返门禁；真实 Token/POI 质量未验证。入口：[实施计划](history/planning/ZHIJIAN_AI_OPTIMIZATION_AND_E2E_PLAN.md)、[A/B 报告](benchmark/AI_REQUEST_OPTIMIZATION_AB_REPORT.md)、[E2E 矩阵](benchmark/CROSS_PROJECT_E2E_REPORT.md)、[发布门禁](benchmark/RELEASE_ACCEPTANCE.md)。

2026-10-09 同模型保存检查与重跑配置：LocalAiMux 保存前自动核对接口目录，失败保留旧配置/凭据；视频提交在创建任务前检查核心文本阶段接口。普通重试、步骤续跑及完整重跑自动刷新同模型必要配置，保持语义/路由/预算上限和原提交快照；执行版本/历史与延迟重跑配置可追溯，身份变更/删除/禁用安全拒绝，Token/远程调用按同 Job 的现存审计累计。最终生产 Python 全量 300 项、完整源码/测试 Ruff 通过；Node 24 前端全量 19 项与 ESLint/TypeScript/Vite 隔离构建通过，末次文字更新后目标 8 项通过。内置 Browser 在隔离 SQLite/模拟目录上验证 1440×1000 与 390×844 的自动保存、目录失败保留原配置、同模型步骤续跑/ASR 复用及无溢出/相关控制台错误，推理请求 0。详尽计划已归档至 [实施计划与验收记录](history/planning/SAME_MODEL_REPLAY_CONFIG_IMPLEMENTATION_PLAN.md)。源码验收阶段未提交/部署或重跑真实视频；后续 2026-10-09 统一重载的生产证据仅见 [交接生产快照](CURRENT_HANDOFF.md)。

2026-10-09 设置按钮错位补修：共享按钮图标统一 16×16 与 8px 间距，保存的普通/加载图标占位一致；模型检测与删除/保存分组，补充提示词网格取消固定最小列宽，覆盖中间桌面宽度溢出。前端 19 项/ESLint/TypeScript/Vite、生产 Python 后端 279 项与 diff 检查通过；静态包在 8787 加载后，1440/1024/760/390/320 五种宽度的等待、成功、长错误、保存与重复排队隔离交互通过，保存切换前后按钮几何一致，无横向溢出/非预期控制台错误。另在真实浏览器、真实已保存模型上核对图标尺寸/间距和新资源，无真实模型调用或配置写入；当时有活跃任务，仅更新静态前端，未重启后端。

2026-10-08 最终源码：生产 Python 3.14 `pytest backend/tests -q` 全量 279 项、完整源码与测试 Ruff、Node 24 前端 `pnpm verify` 的 19 项 Vitest/ESLint/TypeScript/Vite 均通过。`trust_env` 的本地路由成功与取消回归在修复前复现同一 TypeError，修复后与相关目标回归共 34 项通过；异步客户端构造参数与请求参数分离，保留绕过环境代理及普通连接默认行为。

本地路由已按实际接口能力处理消息/可选参数，手动测试 FIFO 不改变生产熔断，CLI 安全错误分流保持原预算；Token 读取区分可信实测、估算、未知，历史审计不回填。Job HTTP 等待、间隔与重试可协作取消；ASR 回收进程组，旧执行结果仍受 run fence 约束。上述功能在 2026-10-08 已分批受控加载，生产与 Browser 证据仅在交接和相关历史记录判定；此处的通过数量不替代真实模型验收。

2026-10-09 本轮为文档和远程交付：补齐文档清单、接口入口、当前状态及取消边界，迁移旧验证过程；仅检查链接、迁移完整性、合订生成与格式，不重复业务全量测试。

## 未闭环与外部条件

- **本地推理取消未闭环**：Ollama 已增加中断后有界空 Prompt 卸载与 `/api/ps` 核对，Mock 路径通过；真实 llama-server 停止/退出仍未采集，失败或仍加载为 UNKNOWN。释放客户端等待和本地锁不证明推理停止；需独立修复及真实取消验收，不能由 `trust_env` 修复推导为已完成。
- 本地路由的单模型小样、目录能力及一次视频续跑不代表全型号/全阶段质量；厂商额度、思考 Token、远端取消/计费以及完整 Provider/fallback/cache/预算矩阵仍按 [生产验收门禁](ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md) 取证。
- 视频语义/POI 与 Visual Fact 已有离线 Golden，真实高德质量、Vision、代表性长视频、Token/延迟基线与性能毕业门禁仍未整体闭环。REVIEW/UNRESOLVED 保持人工处理，Fixture、构建和数据库版本不替代真实验收。
- 提交配置快照及同链接多 Note 身份已实现；真实双提交、模型切换和 Place 复用矩阵仍需独立验证。旧 Job 没有提交快照时，不补造当时设置或改写历史业务结果。
- Qwen3-ASR 运行资产及 Forced Aligner 已安装并有真实 smoke；系统注册基线为 Whisper；本次沿用用户已保存的 QWEN3_ASR 选择，不将单条视频视为 Benchmark 毕业或默认推荐。六类人工 Ground Truth、15–30 分钟 LONG_FORM、Replay 及 Benchmark Gate 未完成前不得晋级默认或改变生产 Registry。
- Bilibili 登录/nav/Keychain 与部分视频已有真实记录；受阻对象不自动重跑。高德和远程 Provider 必须使用合法配置；Secret 不进文档、SQLite 明文或日志。
- 已完成的 PC/390px 验收仅覆盖相应设置/任务控件，未验收的地图、Vision 或真实视频体验不自动外推；具体范围以带日期记录为准。

## 追溯与维护

旧验证数量、按日实施过程已原文迁入 [实施历史](history/IMPLEMENTATION_HISTORY.md#2026-10-09-当前状态页历史归档)。已覆盖计划在 [历史计划目录](history/planning/README.md)，未来候选仍在 planning/；专项只说明契约，不证明部署。生产现场更新既有交接，合订本由源文档生成，不直接编辑。
