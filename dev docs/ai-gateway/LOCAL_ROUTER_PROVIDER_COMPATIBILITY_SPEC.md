# 本地路由 Provider 接入规格（LocalAiMux）

状态核对：2026-10-09。至简 Z1–Z4、手动队列、订阅 CLI 错误分流与可取消本地路由调用已进入源码并加载；验证数量只在 [实施状态](../IMPLEMENTATION_STATUS.md)，生产和已观测的视频续跑只在 [交接](../CURRENT_HANDOFF.md) 按采样日期判定，不外推全型号质量。LocalAiMux 上游改造是独立仓库工作包。请求参数、厂商对照及 55 个模型的历史目录见[参数与模型调查](../history/LOCALMUX_PARAMETER_SURVEY_20261006.md)。

同日修订：此前的“不支持”只适用于 Mux 当时的有效接口，不能归因为 CLI 或底层模型不支持。只读调查发现部分公开能力未被 Mux 映射；完整归因和公共边界见 [LocalAiMux 通用设计](../../../local-ai-mux/docs/architecture/CAPABILITY_NEGOTIATION_DESIGN.md)及[逐型号盘点](../../../local-ai-mux/docs/architecture/CAPABILITY_AUDIT_2026-10-06.md)。至简实施结果见第 10 节，不代表 Mux 也已实施或既有总预算已调整。

## 1. 范围与目标

至简通过本机 HTTP Gateway 调用远程或本地推理模型时，必须按“该连接下、该实际模型、该协议”的能力构造请求。LocalAiMux、厂商原生 API 与 OpenAI-compatible 服务不能仅凭相同的模型名字共用全部参数。目标是让测试、正式 Stage、主备切换、JSON 修复和 Replay 使用同一份能力规则，避免只修测试而正式任务仍报 400。

本规格覆盖文本分类、转写校对、地点/实体抽取、证据地图和笔记 Map/Reduce；视觉作为独立门禁。ASR、OCR、媒体下载以及交互聊天产品不在本次范围。现有 Source/Snapshot/Segment/Claim/Evidence、Job/Step/Artifact、raw/corrected Transcript、note/ntv 身份边界与 POI 人工审核保持现有冻结契约。

## 2. 至简是否需要多轮对话与历史消息

**当前核心流程不以用户聊天或跨请求会话历史为前提，但需要同一次请求保留多条消息的语义。**调查范围内的生产 services/ai 调用没有构建 assistant 历史消息，也没有使用 `conversation_id`、`previous_response_id` 或 Chat history。以下概念必须分别处理：

| 概念 | 至简当前需要 | 规格要求 |
| --- | --- | --- |
| 同一次请求中的 system + user | 是 | 保留核心规则与业务材料的角色、顺序及优先级；不能只取最后一条 user |
| 同一次请求中的多个 system / 领域上下文 | 是 | 核心 JSON/Schema/Evidence 契约优先，表达偏好和领域包低优先级；保留全部必要材料 |
| JSON 修复后的再次请求 | 是 | 重发完整消息，将修复指令与前置 system 合并，业务 user 材料保持；不是接续上次 assistant 答案 |
| Map → Reduce 的阶段关系 | 是 | 下一阶段显式传入已验证 Facts/Evidence，不依赖模型记住上一阶段 |
| Job 完整/步骤续跑 | 是 | 复用冻结配置和有效 Artifact；不能依赖 Mux 内存会话才能恢复 |
| 用户连续提问的 user/assistant 历史 | 当前核心流程无此要求 | 不为接入 Mux 新建聊天会话系统；不把历史支持设为所有 Stage 的必要条件 |
| 上游状态会话 / Responses 续接 | 当前无此依赖 | 当前方案保持请求自包含，不发送 previous_response_id；若将来引入，另行冻结会话与持久化契约 |

因此 `history=UNSUPPORTED` 本身不应阻止无状态 Stage；当前 Mux 的 `system=UNSUPPORTED` 和“只能一条 user”才是直接兼容障碍。`system`、`multiple_messages`、`history`、`stateful_resume` 四项不能合并为一个“支持对话”。依据：[消息组装](../../backend/src/zhijian/services/video_support.py)、[JSON 重试](../../backend/src/zhijian/providers/llm.py)、[任务快照与恢复](05-job-policy.md)。

未来如果增加真正的多轮交互，须独立定义：历史归属和隔离、消息版本及顺序、Token 窗口/压缩、保留和删除、权限、模型切换行为、tool/reasoning 历史的原样回写以及会话失效后的恢复；不能从本规格推导出该功能已获实施授权。

## 3. 连接、模型及能力描述

1. 分开记录接入类型、协议、HTTP 地址、实际推理位置与实际模型身份。本机 `127.0.0.1` 只证明 Gateway 在本机，不证明推理本地、免费或不外传。Mux 当前云端桥接应继续遵守远程调用及预算边界，不把它改成 LOCAL 以绕过保护。
2. 不用空 provider 名称或端口号推断产品能力。实现时应为本地路由 Gateway 设置明确的接入类型，沿用现有 Profile/Stage Policy 选择边界；不为此重写 Pipeline。若确需 Schema 改动，追加 Alembic migration，不改历史 migration。
3. 目录读取为无推理操作：标准 `GET /v1/models` 获取模型 ID；Mux 扩展 `GET /api/chat/models` 获取接口能力。按当前 Key 的可见范围检查两个目录一致性，不把不可见模型判成已断开。记录采样时间；参数能力不由模型名称或厂商官网覆盖。
4. 能力按模型与连接保存，状态至少为 `SUPPORTED / UNSUPPORTED / UNKNOWN`，同时保存来源、采样时间和 Adapter/Gateway 版本。可选参数还需范围、默认值、线缆字段名、预算口径及“接收但忽略”的说明；声明支持与真实业务 Probe 状态分别存储。
5. 完整描述至少包含：system、多条消息、历史消息、会话续接、纯文本/图片等输入、非流式/SSE、JSON object/JSON Schema、tools、temperature/top_p、输出上限字段及范围、thinking 开关/强度、上下文/输入上限、usage 与结束原因可信度、取消能力。目录没有的字段记 UNKNOWN，不补造型号能力。
6. 请求选择显式型号；`Auto/Ultimate/Performance/Efficient` 及 free/cheap/balanced/best 等动态路由应标注动态性。要满足可复核任务，需返回实际上游型号/连接；若无法确定，不得声明已固定某个底层模型。

## 4. 参数协商与消息适配

| 参数/语义 | 支持时 | 不支持或未知时 |
| --- | --- | --- |
| model、业务输入 | 使用目录中的精确 ID，保留大小写、材料与证据身份 | 阻止请求并说明；不能换为同名厂商型号 |
| 输出上限（可选） | 将内部 max_output_tokens 映射为该接口支持的 max_tokens / max_completion_tokens / num_predict 等；注明是否含思考 | 默认采用模型默认值，不发送被拒字段；标明上游 Token 上限不可控，继续已有总预算/分包/尝试/耗时保护；不设为所有 Stage 的共同必需参数 |
| temperature / top_p | 只发经过该型号范围校验的参数 | 默认值偏好可显式选择“采用模型默认值”并审计省略；业务必需参数不静默丢弃 |
| thinking（可选） | 按型号映射其字段、开关和合法值 | 默认采用模型默认模式，不把所有 Stage 设置为必须关闭；不能把 low 档声称为关闭。个别严格预算任务仍按其实际门禁选型号 |
| JSON object / Schema（原生参数可选） | 使用原生约束并继续做服务端校验 | 使用明确业务 Prompt + 原有 JSON/Evidence 校验；原生 JSON mode/Schema 不是全型号准入前提，但业务落库质量门禁保持 |
| system / 多条消息 | 原样传角色与顺序 | 默认拦截正式 Stage；仅在显式启用且验收后的单轮文本适配模式下编译消息 |
| 历史 / stateful resume | 仅在业务确实使用时启用 | 当前无状态流程无需历史；不得为了适配丢失其他必需角色 |
| image / tools | 仅在声明支持且 Stage 获授权时发送 | 明确阻止；不能把图片改成文本描述来冒充视觉验收 |

输出上限不是唯一的预算机制。省略 max_tokens 后，本地响应字节上限、超时、最多尝试次数和停止接收只能保护本机；不能保证上游已停止生成或消费。硬 Token 上限、已知输出能力或关闭思考是某个 Stage 的必需条件时，当前不支持的 Mux 桥接模型必须保持不适用，不能只删除参数放行。

消息适配存在两个可评审方案，默认选择 A：

- A：完整消息模式，要求 Gateway/Adapter 真正支持至简需要的 system 与多条消息；缺能力时提前提示不兼容。
- B：显式单轮文本模式，把核心指令、低优先级上下文、业务材料和修复指令按有版本的模板编译为一条 user。不能删段、重排证据、改 Segment ID 或引用归属；不能视为保留原生 system 层级。须把转换方式、有效参数和转换后输入哈希写入审计/缓存，并单独验证指令冲突和资料注入。该模式是否用于核心抽取与笔记，需要用户评审后冻结；本次没有默认启用它。

至简内部的预算、拆包、Schema/Evidence 验证保持独立，不能把兼容选择塞进业务 Prompt 或让模型决定是否校验。主备模型各自协商参数；切换后不能直接沿用主模型的已序列化请求。新增能力版本与适配方式必须进入 Job 非密钥快照和 Cache Key；排队、Replay 不受后续全局配置变更影响。

## 5. 响应、审计与稳定性

1. 至简当前读取非流式 `choices[0].message.content`。Gateway 对外需提供相同的非流式形状；内部 SSE 聚合不得把思考文本、CLI 状态或工具事件混入业务答案。若未来至简主动消费 SSE，按完整结束标志判断成功。
2. 结束状态区分正常结束、输出/上下文截断、超时、取消、错误、空答案。不能固定填 stop 抹掉异常；JSON 合法且 Evidence 有效才可落业务产物。
3. usage 必须区分“上游实测”“估算”“未知”。占位 0 不能当作免费或零 Token；未知值不计为实测，不绕过预算。若现有字段无法表达未知，需另加可信度元数据，不破坏旧账本。
4. 审计保存至简请求 ID、Stage、主备链、Profile/实际模型、Adapter、能力版本、有效参数及省略原因、结束状态、耗时、usage 来源；不保存完整请求、Key 或模型原始错误正文。Mux 自己的路由切换也需可见，不能暗中换收费模型。
5. 保留安全的 Mux 错误码与中文可行动提示。参数/消息不兼容属于配置错误，不自动重复原请求，也不作为供应商暂时故障累计触发冷却；鉴权、配额、429、5xx、网络与超时分别处理。Probe 无法完成时保留原结果；“请求不兼容”与“模型业务能力 FAIL”分开。
6. 测试、Probe 和正式 Worker 使用同一凭据/连接的节流规则。Mux 可能把多个型号映射到同一上游账号，要按真实连接串行并遵守 Retry-After；本地资源锁与远程限流分别处理，不因为本地 HTTP 就占用 Ollama 的重任务身份。
7. 取消或客户端断开只在已证实能终止上游时声明停止消费；否则标注“停止接收，上游是否停止未知”。不得叠加无界自动重试或跨账户回退。
8. CLI/App Server 桥接必须提供纯模型执行边界：禁止读取至简项目文件、执行 shell、修改文件和启动不在任务授权范围内的工具；不使用开发助手的隐含系统提示代替至简规则。隔离工作目录、关闭 tools/MCP 或可证明的同等控制要纳入 Adapter 验收。

## 6. 能力 Probe 与阶段准入

| 层级 | 验收内容 | 能证明什么 |
| --- | --- | --- |
| 目录/配置检查 | 模型存在、权限、能力来源/版本、参数范围与冲突 | 接入前提；不调用推理、不写业务能力 PASS |
| 单轮连通测试 | 对不支持输出上限的桥省略该字段；已知支持关闭思考时才关闭；单 user 小样 | 可返回文本；不证明正式 Stage 可用 |
| 消息契约 Probe | 实际 Stage 所需 system、多消息、补充优先级及 JSON 修复路径；或经过授权的编译模式 | 消息传递符合选定适配方案 |
| 结构化与 Evidence Probe | JSON/Pydantic、字段和 ID、逐字引用归属、截断/空响应/非法输出 | 该专项能力的可用证据；未覆盖项保留 NOT_TESTED |
| Stage 准入 | 必需消息语义、业务 JSON/Evidence 校验和已有总预算满足；输出限额、采样、思考、原生格式、精确 usage 分别标可选/未知 | 允许该 Profile 用于该 Stage，不以非必要参数全支持作为共同门禁；不扩推为其他能力 |
| 真实业务验收 | 授权小样→代表性长文本/分包→完整视频及 Replay；保留主备、Cache、预算证据 | 才能声明对应生产场景成立 |

目录中 55 个型号不是 55 次真实模型测试。先按能力模板及 Adapter 完成离线覆盖，真实请求必须用户明确授权、串行、受小样预算限制；禁止借规格调查批量调用模型。Probe 只修改真实覆盖的能力，不用“回复了 PONG”自动授予转写校对、实体抽取或完整笔记能力。

## 7. 开发验收条件

1. 参数矩阵覆盖 2 种现有 Provider 实现、已保存的 12 个模型 Profile、7 类前端预设以及旧 Provider 测试入口；配置字段与线缆参数分开。
2. 对当前 4 个 Mux Adapter / 55 个精确模型 ID，分别保留完整目录和一致性校验；共同能力可以共享模板，但不能漏掉型号、替换大小写或推导未声明参数。
3. 离线证明：可选不支持参数按明示策略省略；严格必需参数提前拒绝；JSON/Schema/多消息/图像等冲突都有独立错误；主备、修复重试和快照采用正确能力版本。
4. 离线证明：400 配置错误不反复发起/触发临时故障冷却；UNKNOWN usage 不变成真实 0；截断、空回复、取消和未知实际上游身份不误报成功。
5. 现有 DeepSeek、Ollama 与其他 OpenAI-compatible 路径保留各自映射及质量门禁。不得全局删除 max_tokens，或仅因 Profile supports_json_mode=true 就忽略不支持的接口契约。
6. 若设置页面增加能力/默认值/不兼容提示，沿用[前端视觉体系](../design/FRONTEND_VISUAL_DESIGN_SYSTEM.md)，中文业务标签，PC/Mobile Browser 验收；长能力测试应受 Worker 或现有获批准的有界交互测试契约管理，不能扩成 API 请求内长任务。
7. 开发按仓库验证策略跑目标与完整验证；新增修复/失败证据才重复相关验证。真实 Provider、视频、迁移/重启分别授权，不能用 Fixture/构建替代生产验收。

## 8. 当前建议与待评审项

至简保留 model、业务指令和材料、答案文本、JSON/Evidence/身份校验及已有总预算。取消“每次强制输出限额、Probe 固定 64、所有型号关闭思考、固定温度、所有型号原生 JSON Schema”的普遍要求；context_window/num_ctx 只保留其本地语义，远程不强迫透传。top_p、history/previous_response_id、SSE、tools 和全型号视觉不进入本次接入要求。用量未知不能当 0，输出上限未知不能冒充硬限制；可选参数省略不等于取消业务/总预算门禁。

优先让 Mux 通过通用公开接口支持 system + 单 user；至简把当前完整指令明确组织为前置 system，JSON 重试不再在 user 后隐式追加另一层消息。若通用桥仍无法保持语义，提前诊断；B 单 user 编译只能是至简显式版本化选择，不能要求 Mux 增加至简特判。真正多轮聊天和上游会话不进入当前范围。

## 9. 至简实施工作包（源码已完成，外部验收保留）

| 包 | 方法与文件 | 验收 |
| --- | --- | --- |
| Z1 参数和测试 | providers/llm.py、ai/model_registry.py：生成选项可空；按接口能力选择输出字段/省略偏好，取消 Probe 无条件 64；旧 provider test 同样不强制 response_format | 保留 DeepSeek/Ollama 的正确映射，单轮连通成功不自动授予业务能力 |
| Z2 无状态消息 | services/video_support.py、JSON 修复：保持规则/资料/证据优先级，组织为前置 system + user；必要编译由至简显式管理 | 依赖 Mux 最小通用角色映射；不丢材料、不增加聊天历史/会话服务 |
| Z3 错误/预算/快照 | ai/reliability.py、ai/gateway.py 与审计/Cache/Job 非密钥配置：400 不兼容不计暂时熔断；未知 usage 估算/标未知；能力/规范化版本入快照与缓存，主备分别协商 | 原有总预算、Replay/Artifact/身份门禁保持，不改历史结果 |
| Z4 产品与授权验收 | 设置页中文显示限制所在层、默认参数/未知用量；PC/Mobile Browser 后，授权串行小样及代表性视频 | 不重启、不批量调用 55 型号、不自动 POI 确认；源码实施、部署、真实验收分开报告 |

Mux 的 M1–M5 和两项目边界由[通用设计说明书](../../../local-ai-mux/docs/architecture/CAPABILITY_NEGOTIATION_DESIGN.md)定义：Mux 负责标准协议/公开映射，至简负责业务 Prompt、预算、Schema/Evidence、Job 与缓存，不为一个客户端新增特殊服务端接口。需要改变既有冻结总预算的部分仍须评审，不由本文件自动放行。

## 10. 已实现的使用方式与验证入口

- 模型设置提供 LocalAiMux 预设和 `DIRECT / LOCAL_ROUTER` 接入方式；未登记接入类型的旧 Profile，仅在明确命名为 Local Ai Mux/LocalMux 且使用回环地址时识别本机路由，不凭端口猜测，也不覆盖显式 DIRECT。读取能力并保存后使用绑定模型/地址的快照；地址、模型、凭据或接入方式变化后，界面清除旧能力。快照沿用 Setting JSON，无数据库结构变更。
- 已保存配置通过 `POST /api/settings/model-profiles/{id}/interface-capabilities` 使用当前输入和既存 Key 读取；草稿使用 `/api/settings/model-profiles/interface-capabilities-draft`。这两条路由只读取 `/v1/models` 与 `/api/chat/models` 并核对目录，响应有大小/数量、读取超时和总时长限制，不跟随重定向、不经环境代理、不写配置、不调用模型。用户保存后快照才用于新任务。
- 测试不再强制 64 Token，连通测试使用文本调用；输出长度可空。正式调用和主备分别按冻结快照省略不可用的输出/温度/原生 JSON 参数，范围已声明时校验；路由模式采用默认思考行为。缺 system/历史/文本能力、快照未读取或绑定过期时在推理前拒绝，不启动单 user 业务编译。
- 前置 system 合并保持内容和顺序；JSON 修复指令组织到业务 user 前。能力指纹、客户端规范化版本及上游报告的 schema_version（若有）进入缓存语义与审计，现有 Job 提交/恢复快照自动保存新增非密钥字段；不改历史任务或已有业务 Probe 结果。
- 配置类 400 / 接口不兼容不再计入临时故障熔断，也不自动换模型。未知用量保留为未知，输入/可见输出估算参与原有预算；上游占位 stop 不能当可靠结束原因，保留 reported_finish_reason，明确 length 仍拦截。没有证据保证上游思考 Token 已计入估算或断开已停止消费。
- 自动验收入口：`backend/tests/test_local_router_contract.py`、`backend/tests/test_job_runtime_optimization.py`，以及既有 Provider/缓存/Job/预算/API 回归和前端 `pnpm verify`。浏览器使用 Edge 在隔离响应下验证 PC 1440×1000、Mobile 390×844 的选预设、读能力、默认参数、保存、修改模型后的能力失效及无溢出/控制台错误；这些 Fixture 不代表真实 Mux 推理。

2026-10-06 初次验证：后端全量 256 项通过（含本工作包 19 项），前端 18 项、ESLint、TypeScript、Vite build、后端 Ruff/格式检查通过；合订构建脚本 5 项、文档链接/生成一致性和 git diff --check 通过。Browser 插件不可用，按测试技能采用已安装 Edge 的 Playwright；隔离 PC/Mobile 控件流程无框架覆盖、控制台错误或水平溢出，保存 payload 和修改模型后的旧能力失效已核对。截图/测试脚本放在仓库外，不作为真实业务验收。

2026-10-06 初次只读访问 Mux 目录两次遇到 ReadTimeout 后停止；当时尚未部署或提交。后续目录时限、单模型真实准出和受控加载见第 11–12 节及带日期交接，不把这次旧阻塞当成当前状态。正式 Stage 仍按已保存快照验证 system 等必需能力，不通过放弃 Evidence/规则绕过。

## 11. 手动测试队列与冷却（2026-10-08 修订）

已保存/草稿连通测试、已保存/草稿能力探测及旧 Provider 测试共用 API 进程内 FIFO 队列。整个手动操作（含能力探测的多个调用）串行；失败也释放队列，重复点击和跨模型请求顺序执行。界面允许再次提交并显示等待/执行状态，保存/删除等配置动作在当前测试完成前保持保护。

手动调用不检查、不创建冷却失败，也不通过成功清除生产熔断；生产任务的熔断策略保持。按同一凭据保留请求间隔/RPM 节流；供应商实际 429/额度/鉴权错误仍如实返回，不自动重试或换模型。API 重启后内存队列不保留；这不是新增持久后台 Job 或聊天历史。

旧 Local Ai Mux 的 400 已定位到缺少接入类型导致参数协商未启用；修复从当前目录读取有效能力，省略不支持的输出限额及原生 JSON 字段。schema_version=2 的 details 仅使用 effective_support，不把 native/public_interface 声明当有效能力。验收以该已保存模型的真实连通测试及能力探测均通过为准；源码回归/隔离 UI 通过不替代真实准出。

目录元数据先读能力接口、再核对标准模型目录；已观测到 Mux 冷目录刷新约 7.3 秒，因此读取超时从 5 秒调为 20 秒，增加 30 秒总耗时检查，仍限制响应大小/数量、禁止重定向和环境代理。

2026-10-08 真实准出（隔离进程、直接读取现有配置与 Keychain，未写生产设置）：`model_9840af90390a42ac8e4f9b19a37a3d37 / codebuddy/hy3` 连通 PASS（5.02 秒，非空响应，实际省略 max_tokens）；既有能力 Probe PASS（12.11 秒，CLASSIFICATION/STRUCTURED_EXTRACTION/ENTITY_EXTRACTION/TRANSCRIPT_CORRECTION 为 PASS，其他 NOT_TESTED，无 FAIL）。共 4 次小样推理，无自动重试/备用模型/视频/POI 操作，不外推为整篇笔记或业务质量 Benchmark。隔离 PC/Mobile 验证重复提交可用、保存保护与排队提示。后端完整 259 项、前端 18 项/完整 verify、Ruff、合订脚本与 diff 检查通过。

2026-10-08 用户随后授权生产重载，已无迁移加载当前修复并核对新 OpenAPI。通过运行中的保存模型 HTTP 端点混合提交 test/probe，两项真实准出均 PASS，按提交顺序完成，无 400 或本地熔断拦截；Probe 保存接口快照、LOCAL_ROUTER 和原生 JSON=false。服务/备份/门禁与带日期现场唯一记录见 [CURRENT_HANDOFF](../CURRENT_HANDOFF.md)。隔离样例与生产端点小样均不外推为整篇视频或未知能力验收。


## 12. 订阅 CLI 稳定性实施与验收（2026-10-08）

目标：修复 `job_d8e17638fff7485fa6483accbf734865` 揭示的非流式 120 秒截断和偏好路由备用丢失；调整新任务参数，完成两仓离线验证、至简无迁移部署及文档收敛。用户明确选择仅离线回归与部署验证，不进行真实小样、视频重跑、POI 自动确认、登录或权限扩展。原 Job 的配置快照、业务数据与失败证据保留。厂商套餐额度仍 UNKNOWN；以下参数是本项目保护值，不是厂商承诺的额度或许可。

### 12.1 参数与理由

| 层/阶段 | 参数 | 依据与边界 |
| --- | --- | --- |
| Mux Gateway | 非流式/流式总执行期限 600 秒；流空闲 180 秒；Adapter 启动 30 秒 | 原校对成功用时 106/109 秒；总期限与空闲期分开，连续输出也不能无限运行。队列、目录核对不计执行期限 |
| Mux Agent 连接 | 并发 1、启动间隔 5 秒、锁等待最多 30 秒 | Chat/Responses/显式模型验证共用连接锁；排队超时返回 429 与 Retry-After=5，不启动新 CLI。同一 Adapter 下模型与客户端 Key 共用；不能限制 Mux 外独立 CLI/官方应用 |
| CLI 接收 | 无 stdout 事件 180 秒；工具禁用、单轮 1、隔离目录 | 无输出超时与进程错误分开；错误 result 只在内存分类，不保存供应商正文或凭据；取消/期限释放句柄，不证明远端立即停止计费 |
| 至简 Mux Profile | timeout=660；GUARDED；interval=5；concurrency=1；RPM=12；HTTP retry=0；JSON retry=1；熔断阈值 2、冷却 300 秒 | 660 覆盖 Mux 600、锁等待 30、节流与冷目录余量；额度/鉴权/限流/Mux 超时不重复消耗。RPM=12 为主动保护值，厂商真实限额未知 |
| 转写校对 | timeout=300；chunk_chars=3000；batch_size=16；邻段=1；Stage retry=0；max_attempts=4 | 降低每包 target/context 与重复 Prompt 输入；只读邻段和原 Segment ID/时间码不改变；更小分包可能增加调用次数 |
| GROUND_MAP | timeout=660；chunk_size=5000；max_input_tokens=6000；max_output_tokens=4096；retry=0；wall=1200；max_attempts=12 | 在保留 Evidence/实体关系的前提下降低单包工作量；截断走已有拆分，非截断故障才走已配置且适配的备用 |
| NOTE_REDUCE / GENERATE_AI_NOTE | timeout=660；chunk_size=5000；max_input_tokens=4000；max_output_tokens=4096；retry=0；wall=1200；max_attempts=20；thinking=false | 收紧输入/分包；max_output/thinking 仅在接口有效支持时发送，CLI 不支持时不伪装生效。未声明/探测失败的备用不被自动升级为可用 |
| 全 Job | 保持现有 48 次实际尝试、1800 秒以及 Local/Remote Token 总预算 | 不为容忍慢 CLI 放大整任务消费；达到预算会暂停/失败或按已有笔记降级规则收口，不承诺任何长度视频都能完成 |

阶段 wall 参数在包间检查，单次调用仍受请求/Job 总预算限制；它不是供应商端的硬消费上限。以上校对大小使用既有 transcript-processing 设置；它会影响后续所有校对任务。Stage 参数和 Profile 通过已有 Settings 保存，仅新提交捕获新值。旧 Job/排队任务/完整重跑继续使用提交快照；用户如要应用新参数须新投递或走明确授权的任务级恢复。

### 12.2 工作包与验收

1. **Mux 超时/并发**：Chat 非流式改用总期限；Responses 非流式/续接补同样期限；两类 SSE 同时限制总期与空闲期。Agent 按当前 Adapter 连接串行并覆盖显式验证入口，失败/断流/取消均释放锁。离线虚拟时钟验收 130 秒响应成功、601 秒失败、持续增量到总期失败、跨模型/Key/协议阻塞与断流释放；不真实等待十分钟或发起推理。
2. **至简错误/备用**：根据安全 LMX 码分别识别超时、额度、鉴权、限流、冷却，禁用这些错误的同模型自动 HTTP 重试；允许既有预算内的适配备用。LOCAL_FIRST/REMOTE_FIRST 没有相反位置候选时保留已保存的全局备用，必须不同于主模型、启用、满足能力且未探测 FAIL；*_ONLY 与语义 escalation 保持不回退。验证超时一次后备用接管以及禁用/ONLY 边界。
3. **参数落地**：生产空闲后做逻辑备份，校验 Profile/Stage/Transcript 配置，单事务更新上述 Settings 并记录无密钥审计；旧 Job payload 不写入。新配置与旧快照的离线路由均核对。全局主备、模型能力、Key/接口快照、默认 ASR 和历史业务数据不改。
4. **完整验证/部署**：至简完整后端、Ruff/格式、Node 24 前端 verify；Mux fmt、workspace tests、Clippy、前端类型/测试/构建。无需 UI 改动，本轮不新增 UI/Browser 验收。部署前两库 integrity/FK/版本与活跃 Job/lease、Mux active_tasks=0；备份并保留安装包回滚。Mux 按原生脚本构建安装重启，至简按 manage.py 无迁移重载；核对二进制 SHA、Key 身份、API/Worker/首页/heartbeat、只读模型目录和新配置。
5. **文档收敛**：本节维护参数/契约/计划，IMPLEMENTATION_STATUS 维护完成度与自动验证，CURRENT_HANDOFF 维护任务续接与带日期生产采样；Mux 更新 API/Streaming/Adapter 契约、CHANGELOG 与 HANDOFF。源文档变化后重建合订本、核对链接及 diff。未执行真实推理与完整视频验收，不把 fixture、构建或健康状态解释为业务质量完成。

### 12.3 当前验证与部署结果

至简：目标回归（含提交快照）57 项通过；在合并后的当前源码上使用生产 Python 3.14 完整验证 277 项通过，Node 24 前端 19 项/ESLint/TypeScript/Vite 通过，完整源码 Ruff 与本轮文件格式检查通过。6 项 Settings 在私有数据库副本上验证，再于 2026-10-08 18:08–18:09 单事务保存并记录无密钥审计；Job payload 全量哈希保持一致。无迁移重载后 API/Worker RUNNING、首页/heartbeat READY，OpenAPI 控件已加载，生产 6/6 参数匹配、integrity=ok、FK=0、revision=0025、active/leased=0。备份与现场唯一记录见 CURRENT_HANDOFF；原失败 Job 未重跑。

Mux：本轮独立基线完整验证 Rust 87 passed / 2 ignored、前端 7 passed、类型/构建与 Clippy 通过；随后叠加并行调用记录扩展，整合后的 Rust 95 passed / 2 ignored、前端 7 passed、Clippy、官方 Python/TypeScript SDK smoke 通过。记录表的虚拟时钟调度失败由该包以关闭虚拟时钟 fixture 保存、独立真实时钟 fixture 验证落库收口。安装版 API 只读 health 已报告 600/180 秒、并发 1、间隔 5 秒、排队 30 秒；安装/release SHA 一致，Key ID/哈希/权限/路由限制全量摘要未变。以至简生产 Keychain 既有凭据只读 `/v1/models` 返回 200 且包含 codebuddy/hy3，没有发起生成。Mux 当前 schema=11，新增表属于并行调用记录包，本工作包未新增 Schema；该包保留独立 UI 收尾与生产采样。最终安装后的 Mux 超时/队列专项 5 项再次通过；两库 integrity/FK 通过，active Job/lease 与 Mux active_tasks=0。

上述 2026-10-08 CLI 工作包当时只做离线回归与部署验证，未运行真实小样、重跑视频、确认 POI 或提交/推送；后续视频只读证据和本轮远程交付见带日期交接，不能外推厂商排队、账户限额、业务质量或远端取消/计费。

## 13. 可取消 HTTP 请求参数（2026-10-08 修复）

LOCAL_ROUTER 请求设置 `trust_env=False`，避免回环 Gateway 被环境代理接管。同步顶层 `httpx.post` 可接收该参数；Job 的可取消路径使用 `httpx.AsyncClient` 时必须把它传入客户端构造函数，不能传给 `.post()`。普通 DIRECT/Ollama 请求保持 httpx 的默认环境策略。取消检查和客户端等待回收不等于上游已停止生成；Ollama 清理缺口见 [模型释放边界](AI_RUNTIME_AND_PROVIDERS.md#41-ollama-响应后的释放契约与取消边界)。

离线回归同时覆盖本地路由成功请求、环境代理禁用和 DIRECT/LOCAL_ROUTER 等待取消；真实 Job 的原 TypeError 修复后步骤续跑结果见交接，不在本规格复制生产状态。
