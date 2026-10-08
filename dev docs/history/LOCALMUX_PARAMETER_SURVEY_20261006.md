# 至简 / LocalAiMux 参数与模型调查（2026-10-06）

这是一份有日期的调查快照，不是当前实施状态或生产验收结论。规格建议见[本地路由 Provider 接入规格](../ai-gateway/LOCAL_ROUTER_PROVIDER_COMPATIBILITY_SPEC.md)。至简源码、SQLite 中非密钥 Profile 字段、Mux 的只读目录和官方参数文档是各自结论的依据；本次没有真实推理、任务重跑、配置写入或服务重启。

归因修订（同日 19:17 续查）：本报告 C0 表示 **Mux 当前有效接口**，不是 CodeBuddy/Qoder/Codex 或底层模型本体能力。公开 help/schema 证明部分 system、输出上限、结构化输出、思考和用量能力尚未被 Mux 映射；不能把 max_tokens 400 说成 hy3 拒绝了该参数。逐型号已知数据、来源层和 UNKNOWN 缺口见 [Mux 全量盘点](../../../local-ai-mux/docs/architecture/CAPABILITY_AUDIT_2026-10-06.md)；通用设计与精简客户端计划见 [Mux 设计](../../../local-ai-mux/docs/architecture/CAPABILITY_NEGOTIATION_DESIGN.md)。下面 18:25 参数/目录快照保留原采样事实。

## 1. 采样范围与完整性

北京时间 2026-10-06 18:25 读取现有 Key 可见的 `/v1/models` 和 `/api/chat/models`：各 55 个 ID，集合完全一致，无重复 ID；连接库有 codex、qoder、qoder-cn、codebuddy 四种 Adapter，与目录一致。数量为 Codex 7、Qoder 17、Qoder CN 14、CodeBuddy 17。当前可见目录没有 free/cheap/balanced/best 路由，也没有 MiMo/Claude/Gemini 独立 Adapter。Key 权限之外的隐藏型号不在本次“已接入”定义内，不作完整性断言。

Mux 正在本机 `127.0.0.1:8317` 监听；至简保存的 Mux Profile 是 `codebuddy/hy3`，地址 `http://127.0.0.1:8317/v1`，location=REMOTE，supports_json_mode=false，max_output_tokens=4096，provider 名称为空。读取目录鉴权成功。这些事实不能证明模型真实推理已成功。

## 2. 至简实际发送的全部大模型请求参数

生产大模型实现只有 `OllamaProvider` 与 `OpenAICompatibleProvider`；DeepSeek、MiMo、Moonshot、Zhipu、Qwen、OpenAI-compatible、SenseNova、OpenRouter 与 Mux 等标签不各自拥有独立序列化器。`FallbackLLMProvider` 调度主备及重试，不是新的上游协议。依据：[LLM Provider](../../backend/src/zhijian/providers/llm.py)、[请求选项](../../backend/src/zhijian/ai/schemas.py)、[Stage 选项映射](../../backend/src/zhijian/services/video_support.py)。

### 2.1 线缆字段清单

| 参数/位置 | OpenAICompatibleProvider 当前行为 | OllamaProvider 当前行为 | 用途或边界 |
| --- | --- | --- | --- |
| HTTP URL | base_url 去掉末尾 / 后加 `/chat/completions` | base_url 加 `/api/chat` | base_url 应填 API 基路径，不能再包含完整 chat/completions |
| Authorization | `Bearer <SecretStore 取出的 Key>` | 不设置此认证头 | Key 不进入请求正文/Job/日志 |
| Content-Type | httpx 的 json 请求生成 application/json | 同左 | HTTP 编码，不是生成参数 |
| model | 必传字符串 | 必传字符串 | 当前选定模型；Mux 带 Adapter 前缀且保留大小写 |
| messages | 原样传入消息列表 | 原样传入消息列表 | 常见为 system + user，可包含多个 system 及低优先级上下文 |
| messages[].role | 业务常用 system、user；当前未构建 assistant 历史 | 同左 | 消息层级，不是聊天产品的证据 |
| messages[].content | 文本；视觉路径可为 text/image_url 内容数组 | 文本；视觉使用额外 images | 文本里包含任务输入、JSON 字段契约、Segment/Evidence ID、来源材料；不是单独顶层 schema 字段 |
| messages[].images | 不使用 | 视觉路径传 base64 图片数组 | 仅视觉 Stage，文本阶段没有该字段 |
| temperature | options 非空且值非 None 时发送 | 映射到 options.temperature | Stage 温度；范围未做厂商型号级协商 |
| max_output_tokens（内部名） | 映射为顶层 **max_tokens** | 映射为 options.**num_predict** | 不是同名线缆字段；正式主/备用各用自己的 Profile，Stage 可覆盖 |
| context_window（内部名） | **不发送** | 映射为 options.**num_ctx** | 远程上下文限制主要是本地路由/拆包元数据，未改变厂商窗口 |
| thinking（内部布尔） | 只在 provider=deepseek 或 base_url 含 api.deepseek.com 时传 `thinking:{type:enabled/disabled}` | 支持时发顶层 `think` 布尔 | MiMo、GLM、Kimi、Qwen、Mux、SenseNova/OpenRouter 并不会因此自动收到对应的思考参数 |
| JSON 模式 | generate_json/generate 调用且 supports_json_mode=true 才发 `response_format:{type:json_object}` | generate_json/generate 发 `format:"json"` | generate_text 不发；JSON object 不等于 JSON Schema |
| stream | **不发送**，当前期待默认非流式 choices | 明确发送 false | 至简当前未消费大模型 SSE |
| keep_alive | 不发送 | 明确发送 0 | 本地请求后不常驻模型，不能为 Mux 照搬 |
| options 对象 | 不发送该对象 | 非空才发送，包含 temperature/num_predict/num_ctx | 不把内部 options 整体塞到远程正文 |
| timeout_seconds | httpx 客户端 timeout 参数 | 同左 | 不在 JSON 中；正式任务可由剩余墙钟预算收紧 |

当前 **不会发送**：top_p、top_k、seed、stop、n、logprobs、presence/frequency/repetition_penalty、max_completion_tokens、远程 max_output_tokens、reasoning_effort、Qwen enable_thinking/thinking_budget、json_schema/strict、tools/tool_choice/parallel_tool_calls、service_tier、store、user/metadata、previous_response_id/conversation_id、stream_options。这里的“不发送”是至简实现现状，不等于上游不支持。

Profile 的 supports_json_schema/supports_tools/modalities/capabilities、quality_tier、specialties、recommended_working_context、enabled 等是本地选择/声明字段，不是发给模型的参数。其中 supports_thinking 不构成所有厂商的参数映射，不能据此声称关闭思考。重试、并发、RPM、请求间隔、熔断阈值/冷却、wall_time、max_attempts、max_input_tokens、置信度门槛、Domain Pack、Job/Profile ID、Cache Key、Prompt hash/版本与 Audit metadata 均由至简控制；Prompt/领域包的正文会作为 messages 内容参与推理，名称/管理字段不自动进入线缆正文。

### 2.2 每条调用入口的差异

| 调用入口 | 当前传入选项 | 额外情况 |
| --- | --- | --- |
| Profile 已保存/草稿连通测试 | max_output_tokens=min(64, Profile 上限)，thinking=false；不传温度或 num_ctx | 只发一条 user；远程路径强制共享节流、并发 1、无自动重试、熔断开启且冷却至少 120 秒 |
| Profile 已保存/草稿能力 Probe | 同上述，每个小样都通过 invoke_profile_model | 两个纯文本小样，然后一个 JSON 小样；本次不执行推理 |
| 正式业务，经 Stage/主备包装器 | Stage temperature、Stage 或 Profile 输出上限、Stage thinking、Profile context_window | 主备分别构造；笔记角色的 DeepSeek 若未指定 thinking，默认 false |
| JSON 修复重试 | 保留上述选项，原 messages 后追加 system 修复要求 | 不追加上次 assistant 回复；对单 user 桥仍形成不支持的多消息 |
| 旧 `/api/settings/providers/{role}/test` | 不传 ProviderRequestOptions | OpenAICompatibleProvider 默认 supports_json_mode=true，generate 因而仍发送 response_format；不能因没有 max_tokens 就判定旧入口兼容 Mux |
| AIWorkloadGateway.execute / 未包装的直接调用 | 不显式传 ProviderRequestOptions | generate_json/text 决定 JSON 模式；是否有选项必须按实际入口判断，不能说每次都传温度/上限 |
| Visual Fact | system + 含图片的 user，原 Provider JSON 路径 | 上游媒体能力和业务视觉验收独立；当前 Mux 不允许这类请求 |

依据：[Profile 测试/Probe](../../backend/src/zhijian/ai/model_registry.py)、[API 测试入口](../../backend/src/zhijian/api/router.py)、[Gateway](../../backend/src/zhijian/ai/gateway.py)、[Visual Fact](../../backend/src/zhijian/services/visual_facts.py)。现有专项文档中计划的 generate_structured/json_schema 不应当被当成已经上线的参数。

### 2.3 当前所有已保存 Profile（12 个）

下面只保留名称、上游类型、模型及 JSON 开关，避免导出凭据；这是配置声明，未逐个重新验证。当前各 Profile max_output_tokens 均为 4096，正式 Stage 仍可能覆盖。旧 provider:default 与 provider:fallback 是独立兼容设置，不是额外 Profile。

| 名称 | 上游标签 | 模型 | JSON mode 配置声明 |
| --- | --- | --- | --- |
| DeepSeek Flash Main | DeepSeek | `deepseek-v4-flash` | true |
| DeepSeek Pro Main | DeepSeek | `deepseek-v4-pro` | true |
| Free SN Flash | OpenAI Compatible | `sensenova-6.8-flash-lite` | false |
| Free SN DSv4F | OpenAI Compatible | `deepseek-v4-flash` | true |
| Free SN GLM | OpenAI Compatible | `glm-5.2` | false |
| Local Ollama | Ollama | `qwen3:8b` | true |
| Local Ollama fast | Ollama | `qwen2.5:7b` | true |
| Local Ollama 3.5 | Ollama | `qwen3.5:9b` | true |
| Benchmark use | SenseNova | `sensenova-6.8-flash-lite` | true |
| OR Free | OpenAI Compatible | `openrouter/free` | true |
| 史哥赞助 | Zhipu | `glm-5-turbo` | false |
| Local Ai Mux | 空值（通用 OpenAI-compatible） | `codebuddy/hy3` | false |

前端预设为 7 类：DeepSeek、MiMo、Moonshot/Kimi、Zhipu GLM、Qwen、OpenAI-compatible、Ollama。没有单独的 Anthropic/Gemini 原生 Provider。预设型号与最新厂商目录可能漂移，本次不替换旧型号，也不认定别名已失效。

## 3. 主流 API 参数对照

下表覆盖至简的全部预设/已保存上游、当前 Mux 目录可识别的模型族，另列 Claude/Gemini 供协议比较；它不是全行业型号全集。每行是指定接口的官方契约，型号/模式差异继续按其说明处理。Mux 中同名或近似名字只可参考该模型族，不代表与原生 API 的某个版本一一对应。

### 3.1 输出长度、采样、JSON 和思考

| 接口/代表范围 | 输出上限字段 | temperature / top_p | JSON 约束 | 思考控制 | 至简当前差异 |
| --- | --- | --- | --- | --- | --- |
| DeepSeek 官方 Chat API（当前 Flash/Pro） | max_tokens，合法正值；默认/上限依模式 | 声明支持，思考模式的有效行为不同 | response_format.json_object | thinking.type；reasoning_effort 按型号 | 已映射 max_tokens/json_object/thinking；未发送 reasoning_effort，不能把通用温度视为所有模式有效。[官方 API](https://api-docs.deepseek.com/api/create-chat-completion/) |
| OpenAI Chat API（GPT 与推理型号） | max_completion_tokens；max_tokens 已弃用且不兼容 o-series | 按型号/推理模式决定，不是所有 GPT 无条件支持 | response_format.json_object / json_schema，按型号 | reasoning_effort，合法值按型号 | 至简统一发 max_tokens，未映射 max_completion_tokens/reasoning_effort；Mux 中 Codex 型号不等同于这些公开 API ID。[官方 API](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create) |
| 阿里百炼 OpenAI Chat（Qwen 系列） | 新接入推荐 max_completion_tokens；max_tokens 即将弃用，计数口径存在型号差异 | 支持，范围及模式以型号为准 | json_object / json_schema，各有型号清单 | enable_thinking / thinking_budget 等扩展，按型号 | 至简仍发 max_tokens，不发送 Qwen 思考扩展；不能把 Qoder 的 Qwen ID 当作百炼 ID。[官方参数](https://help.aliyun.com/zh/model-studio/qwen-api-via-openai-chat-completions) |
| 智谱官方 Chat（GLM 4.5+/5.x） | max_tokens；GLM 5.1/5.2/5.3 等参考页上限 131072 | temperature 0–1，top_p 0.01–1；do_sample=false 时忽略 | 文本型号支持 json_object | thinking；5.2+ reasoning_effort；5.3 合法档位 low/high/max | 至简不发送 GLM thinking/effort；通用 Stage 温度允许到 2，需要型号范围校验。[官方 API](https://docs.bigmodel.cn/api-reference/%E6%A8%A1%E5%9E%8B-api/%E5%AF%B9%E8%AF%9D%E8%A1%A5%E5%85%A8) |
| Kimi 官方 Chat（K3 / K2.x） | 新接口推荐 max_completion_tokens，max_tokens 已弃用 | 当前 Chat 参考页没有列出这两个字段；不据此推断所有 K2.x 不支持，保持型号级 UNKNOWN | 当前参考页列 json_object / json_schema | K3 始终推理，用 reasoning_effort；K2.6/K2.7 Code 使用其 thinking 契约 | 至简仍发 max_tokens，未实现 Kimi 模式映射；不得统一用 thinking=false 关闭所有 Kimi。[官方 API](https://platform.kimi.com/docs/api/chat) |
| MiMo 官方 Chat（当前 V2.5 / V2.6） | max_completion_tokens，1–131072，含可见输出和思考 | 非思考 temperature 0–1.5、top_p 0.01–1；思考时覆盖为默认值 | json_object | thinking.type enabled/disabled | 至简仅对 DeepSeek 映射 thinking，未映射 MiMo 长度新字段；旧预设 V2 Flash/Pro 不由这张新页自动重新定性。[官方 API](https://mimo.mi.com/docs/en-US/api/chat/openai-api)、[JSON 模式](https://mimo.mi.com/docs/zh-CN/quick-start/usage-guide/text-generation/structured-output) |
| MiniMax OpenAI Chat（M3 / M2.x） | max_completion_tokens 推荐；旧 max_tokens 包含思考，过小可导致空 content | temperature 0–2，top_p 0–1，默认依系列 | 本轮官方 SDK 页未明确列 response_format，保持 UNKNOWN，不声称支持 | M3 thinking disabled/adaptive；M2.x 无法关闭；另一些型号强制推理 | 至简没有 MiniMax 模式映射；64 Token 测试不能保证容纳思考答案。[官方 SDK](https://platform.minimax.cn/docs/api-reference/text-openai-api) |
| 腾讯 TokenHub（混元 hy3 等参考） | 公共协议列 max_tokens / max_completion_tokens；hy3 推理与回答共享额度 | 以型号/模式为准，本轮不冻结具体范围 | 混元指南列 response_format Schema 场景 | 依混元型号，不能从 CodeBuddy hy3-x/space-bunny 名字推导 | 这是 TokenHub API 资料，不是 CodeBuddy 桥或所有别名的支持证明；指南仅获得官方检索内容，完整页未成功读取。[混元指南](https://cloud.tencent.cn/document/product/1823/132252)、[协议参数](https://cloud.tencent.cn/document/product/1823/135872) |
| SenseNova token API | 官方 6.7 示例列 max_tokens | 示例列 temperature/top_p 及额外采样字段 | 本轮引用材料未确认当前 6.8 与所有代管型号的 JSON mode | 不从 DS/GLM 代管名推断官方 thinking | 已保存 6.8、DS、GLM 的布尔声明不能替代对应 token API 型号元数据；本次未验收。[官方仓库示例](https://github.com/OpenSenseNova/SenseNova6.7/blob/main/API.md) |
| OpenRouter / openrouter/free | 接口支持输出限制，具体 target 的 supported_parameters 与 top_provider 上限决定 | 依模型、上游 endpoint | 依模型/endpoint | reasoning 扩展按模型；不是 DeepSeek 原生 thinking 的无条件透传 | 动态路由不能保证每次同一型号/参数；至简没有目录协商。[官方模型属性](https://openrouter.ai/docs/api/api-reference/models/list-all-models-and-their-properties) |
| Ollama 原生（qwen2.5/qwen3/qwen3.5 等） | options.num_predict，窗口 options.num_ctx | options 中配置；具体模型生效性独立 | format=json 或 Schema；至简当前仅 json | think 布尔/档位依模型 | 现有原生映射与 Mux 接口不能混用；不将 keep_alive=0 复制到云端 Gateway。[官方 Chat](https://docs.ollama.com/api/chat) |
| Claude 原生 Messages（对比项） | max_tokens 是该原生接口字段 | 新于 Opus 4.6 的型号不支持自定义采样；兼容值有例外 | output_config.format 等原生契约，非 response_format | thinking / output_config.effort 按型号 | 至简没有原生 Messages、头部和 system 映射；只填 api.anthropic.com 不会自动兼容。[官方 Messages](https://platform.claude.com/docs/en/api/messages/create) |
| Gemini 原生 / OpenAI compatibility（对比项） | 原生 generationConfig.maxOutputTokens；兼容层须按其支持契约 | 原生 generationConfig.temperature/topP，默认按型号 | 原生 MIME/Schema；兼容 Chat 示例支持 Schema | 原生 thinkingConfig；兼容 reasoning_effort/Google 扩展 | 至简无 Gemini 原生序列化；本轮未据兼容页确认所有 max_tokens 行为。[原生 API](https://ai.google.dev/api/generate-content)、[兼容接口](https://ai.google.dev/gemini-api/docs/openai) |
| **当前 LocalAiMux 的全部 55 型号** | **max_tokens 明确 UNSUPPORTED；max_completion_tokens / max_output_tokens 不在请求类型中，拒绝** | **temperature/top_p 明确 UNSUPPORTED** | **response_format 字段被拒绝；提示词产出 JSON 的质量尚未验证** | **thinking/reasoning_effort 字段被拒绝，上游默认行为 UNKNOWN** | **不能按模型族的原生参数调用；见下面全部精确 ID 与 C0 能力模板** |

`SUPPORTED`、`UNSUPPORTED`、`UNKNOWN`、接受后忽略、字段弃用是不同状态。上面没有核实的精确型号范围/格式支持一律明确留空或 UNKNOWN，不能由公共族资料或同名代管推断。格式化上限的语义也不同：有的只限制回答，有的包含推理；至简须记录预算口径。所有来源为 2026-10-06 调查时检索的官方资料，日后可漂移。

### 3.2 消息与会话对照

| 接口 | 同请求多角色/多消息 | 真正历史与会话 | 当前至简适配 |
| --- | --- | --- | --- |
| DeepSeek/OpenAI/Qwen/GLM/Kimi/MiMo/MiniMax 官方文本 Chat | 支持各自协议的 messages；某些型号/字段有约束 | 多轮通常需客户端回传 messages；工具/推理历史有额外原样回写约束 | 当前主要使用 system/user 的无状态请求；不表示已做多轮工具对话 |
| Claude 原生 | system 是顶层字段，messages 为 user/assistant 等内容块 | 客户端提供历史，不能原样照搬 OpenAI 消息 | 当前没有原生 Adapter |
| Gemini 原生 | contents/parts + systemInstruction；兼容接口另有 OpenAI messages | 依协议回传上下文 | 当前没有原生 Adapter |
| Ollama | messages 可包含角色、历史及部分模型的 images | 常见为无状态重传 messages | 当前没有构建 assistant 聊天历史 |
| 当前 Mux 四种 CLI/App Server 桥 | **仅单条 user 文本；system 或多条消息拒绝** | Chat history 明确 UNSUPPORTED；Responses 的续接能力不能等同 Chat history | 需要完整消息桥或评审后的显式文本编译；Job 续跑继续以快照/Artifact 为准 |

至简不存在“因为步骤有先后，所以必须保存聊天历史”的要求。当前 JSON 重试追加 system 指令、Domain Context 插入消息，均属于本次完整请求的输入；Map/Reduce 各次明确传入 Facts/Evidence。真正聊天历史如将来引入，须另行制定持久化、隔离、窗口、删除与模型切换规格。

## 4. LocalAiMux 当前完整能力模板 C0

**以下 C0 适用于下面逐项列出的全部 55 个 ID，没有例外。**各型号的运行时 chat 元数据相同，stream=true。字段拒绝、非流式和 response usage/finish_reason 的补充事实依据当前 Gateway/Adapter 源码；没有重发任何 POST 推理来确认报错正文。

| 能力/参数 | C0 当前状态 | 证据层级与含义 |
| --- | --- | --- |
| model | 支持精确字符串 ID | 两个当前目录一致；只证明可发现，不证明账号有余额或真实成功 |
| messages | 仅一条 role=user、content 字符串 | Adapter 的 single_user_prompt 检查；不能只取最后 user 丢掉前面的 system |
| system | UNSUPPORTED | `/api/chat/models` 的 chat.system |
| history | UNSUPPORTED | chat.history；当前普通 Chat 不保证历史语义 |
| 多条消息 / assistant / tool | 单轮 Adapter 不支持；Gateway 本身也不接受 tool 角色 | 不是“支持 system/history 但至简没用”的状态 |
| temperature | UNSUPPORTED，min=0、max=null | min/max 只是占位，不能把 min=0 理解为允许温度 0 |
| top_p | UNSUPPORTED，min=0、max=null | 同上 |
| max_tokens | UNSUPPORTED，min=0、max=null | 任意正值仍会被参数能力门禁拒绝 |
| stream | true；Gateway 支持非流式与 SSE | 运行时目录及 Gateway；至简当前用非流式 |
| response_format / JSON Schema | 顶层字段不支持，被严格请求类型拒绝 | 单纯 Prompt 要求 JSON 可以传文本，但业务 JSON 可靠性 UNKNOWN |
| thinking / reasoning_effort | 顶层字段不支持，被拒绝 | 不能保证上游思考开关/预算；不能因某型号名称认为支持 |
| max_completion_tokens / max_output_tokens / num_ctx / keep_alive | 不是当前 ChatRequest 字段，拒绝 | ChatRequest 使用 deny_unknown_fields |
| stop / seed / n / penalties / logprobs / stream_options / metadata / user / tools / tool_choice / extra_body 等 | 不在当前 ChatRequest 顶层，拒绝 | 这是接口字段不支持，不是所有底层模型本身不支持 |
| 图片/音视频/文件内容块 | 当前 Chat 路径不支持 | role/content 检查要求字符串；名字含 GLM-5V、Qwen 或多模态型号也不开放视觉 |
| usage | 非流式源码固定 prompt/completion/total=0 | 不能作实测用量或免费证明；没有声明型号级真实 Token 计量 |
| finish_reason | 非流式成功封装固定 stop | 不足以判断上游是否因 Token/上下文上限结束；JSON/Evidence 校验仍必须 |
| context_window / 输入上限 / 上游输出上限 | 当前 chat 元数据没有提供 | UNKNOWN，不套用至简 Profile 的 32768/4096 声明冒充上游实值 |
| structured extraction / 校对 / Evidence 引用 / 笔记质量 | 本次未做真实能力测试 | NOT_TESTED，不把目录属性转换为业务 PASS/FAIL |
| actually selected upstream / cost / quota | 本轮只读取目录，没有逐型号核验这类值 | UNKNOWN；自动档位尤其不能证明固定底层型号或免费 |
| stateful_resume / Responses | 与 Chat 分开，当前至简未调用 | 不从 Chat history=UNSUPPORTED 推断上游所有协议都不能续接；也不从存在 Responses 推断完整历史已支持 |
| 当前能力来源 | 官方 CLI/App Server 单轮文本桥 | 全部 55 项 chat.source 的原文；这是 Mux 接口声明，不是厂商网页能力 |

源码依据（同级本地 checkout；在另一台机器需换成相应仓库）：[ChatRequest](../../../local-ai-mux/crates/api-types/src/lib.rs)、[Gateway](../../../local-ai-mux/crates/gateway/src/lib.rs)、[参数/单消息校验](../../../local-ai-mux/crates/adapter-sdk/src/lib.rs)、[能力类型](../../../local-ai-mux/crates/domain/src/lib.rs)、[公开接口契约](../../../local-ai-mux/docs/api/OPENAI_COMPAT.md)。运行时字段优先于本地源码对已运行版本的猜测，源码补充部分不替代真实调用验证。

### 4.1 当前全部精确模型 ID

表内“族”仅是目录名字的参考归类，不是已确认的原生 API ID 映射。不能用主流 API 表覆盖 C0。Auto/性能档位、Sonus/Cantus、space-bunny 等不猜测实际上游。每行均使用 C0，并保留接口未提供的能力为 UNKNOWN。

| 序号 | 精确模型 ID | 参考族 | 当前能力 |
| --- | --- | --- | --- |
| 1 | `codex/gpt-6.1-sol` | OpenAI/Codex 目录名 | C0 |
| 2 | `codex/gpt-6-astra` | OpenAI/Codex 目录名 | C0 |
| 3 | `codex/gpt-6-sol` | OpenAI/Codex 目录名 | C0 |
| 4 | `codex/gpt-6-luna` | OpenAI/Codex 目录名 | C0 |
| 5 | `codex/gpt-5.6-sol` | OpenAI/Codex 目录名 | C0 |
| 6 | `codex/gpt-5.6-terra` | OpenAI/Codex 目录名 | C0 |
| 7 | `codex/gpt-5.6-luna` | OpenAI/Codex 目录名 | C0 |
| 8 | `qoder/Auto` | 路由/别名，实际上游未确认 | C0 |
| 9 | `qoder/Ultimate` | 路由/别名，实际上游未确认 | C0 |
| 10 | `qoder/Performance` | 路由/别名，实际上游未确认 | C0 |
| 11 | `qoder/Efficient` | 路由/别名，实际上游未确认 | C0 |
| 12 | `qoder/Sonus` | 路由/别名，实际上游未确认 | C0 |
| 13 | `qoder/Cantus` | 路由/别名，实际上游未确认 | C0 |
| 14 | `qoder/Qwen3.8-Max` | Qwen 参考族 | C0 |
| 15 | `qoder/Qwen3.8-Flash` | Qwen 参考族 | C0 |
| 16 | `qoder/Qwen3.7-Max` | Qwen 参考族 | C0 |
| 17 | `qoder/Qwen3.7-Plus` | Qwen 参考族 | C0 |
| 18 | `qoder/Kimi-K3` | Kimi 参考族 | C0 |
| 19 | `qoder/Kimi-K2.8-Preview` | Kimi 参考族 | C0 |
| 20 | `qoder/GLM-5.3` | GLM 参考族 | C0 |
| 21 | `qoder/GLM-5.3-Flash` | GLM 参考族 | C0 |
| 22 | `qoder/DeepSeek-V4-Pro` | DeepSeek 参考族 | C0 |
| 23 | `qoder/DeepSeek-Flash` | DeepSeek 参考族 | C0 |
| 24 | `qoder/MiniMax-M3` | MiniMax 参考族 | C0 |
| 25 | `qoder-cn/Auto` | 路由/别名，实际上游未确认 | C0 |
| 26 | `qoder-cn/Qwen3.8-Max` | Qwen 参考族 | C0 |
| 27 | `qoder-cn/Qwen3.8-Flash` | Qwen 参考族 | C0 |
| 28 | `qoder-cn/Qwen3.7-Max` | Qwen 参考族 | C0 |
| 29 | `qoder-cn/Qwen3.7-Plus` | Qwen 参考族 | C0 |
| 30 | `qoder-cn/Qwen3.7-Flash` | Qwen 参考族 | C0 |
| 31 | `qoder-cn/DeepSeek-V4-Pro` | DeepSeek 参考族 | C0 |
| 32 | `qoder-cn/DeepSeek-Flash` | DeepSeek 参考族 | C0 |
| 33 | `qoder-cn/GLM-5.3` | GLM 参考族 | C0 |
| 34 | `qoder-cn/GLM-5.3-Flash` | GLM 参考族 | C0 |
| 35 | `qoder-cn/GLM-5.2` | GLM 参考族 | C0 |
| 36 | `qoder-cn/Kimi-K3` | Kimi 参考族 | C0 |
| 37 | `qoder-cn/Kimi-K2.8-Preview` | Kimi 参考族 | C0 |
| 38 | `qoder-cn/MiniMax-M2.7` | MiniMax 参考族 | C0 |
| 39 | `codebuddy/hy4-preview` | 混元参考族 | C0 |
| 40 | `codebuddy/hy3` | 混元参考族 | C0 |
| 41 | `codebuddy/hy3-x` | 混元参考族 | C0 |
| 42 | `codebuddy/space-bunny` | 路由/别名，实际上游未确认 | C0 |
| 43 | `codebuddy/deepseek-v4.1-flash` | DeepSeek 参考族 | C0 |
| 44 | `codebuddy/glm-5.3` | GLM 参考族 | C0 |
| 45 | `codebuddy/glm-5.3-flash` | GLM 参考族 | C0 |
| 46 | `codebuddy/glm-5.2` | GLM 参考族 | C0 |
| 47 | `codebuddy/glm-5.1` | GLM 参考族 | C0 |
| 48 | `codebuddy/glm-5v-turbo` | GLM 参考族 | C0 |
| 49 | `codebuddy/minimax-m3` | MiniMax 参考族 | C0 |
| 50 | `codebuddy/minimax-m2.7` | MiniMax 参考族 | C0 |
| 51 | `codebuddy/kimi-k3-1` | Kimi 参考族 | C0 |
| 52 | `codebuddy/kimi-k2.8-preview` | Kimi 参考族 | C0 |
| 53 | `codebuddy/kimi-k2.7` | Kimi 参考族 | C0 |
| 54 | `codebuddy/kimi-k2.6` | Kimi 参考族 | C0 |
| 55 | `codebuddy/deepseek-v4-pro` | DeepSeek 参考族 | C0 |

## 5. 当前兼容障碍与规格取舍

1. Profile 测试/Probe 必传 max_tokens≤64，当前 C0 全部拒绝；正式 Stage 的输出上限与温度也会冲突。只有单独省略测试参数不能解决生产任务。
2. 至简当前 Mux supports_json_mode=false 可以避免 response_format，但不会省略 max_tokens；改为 true 会新增严格字段拒绝，不能借此开启 Mux JSON mode。
3. 至简核心 Stage 的 system/user、补充 system、Domain Context、JSON 修复指令需要完整传递。当前 C0 单 user 不能原样完成；它与“不需要聊天历史”并不矛盾。
4. 参数/消息 400 属于协议不兼容，当前可靠层仍累计失败。2026-10-06 14:34 三次 Mux 400 之后，14:35 测试/Probe 被熔断拦住；因此冷却提示是后续症状。修规格应分类错误，不能靠关闭保护掩盖配置问题。
5. 当前 Mux 不提供可靠输出上限与实测 usage。省略 max_tokens 必须同时处理 Stage 的预算/思考/结束原因门禁，不能把 Token 0 当成没有消耗。
6. 多模态型号名、接口目录、测试构建、能返回文本、能生成一次 JSON、真实视频完整交付是不同证据层级。任何新适配都不得跳过 Grounded Evidence、JSON、引用、身份和人工 POI 门禁。

建议与待评审项已集中在[接入规格](../ai-gateway/LOCAL_ROUTER_PROVIDER_COMPATIBILITY_SPEC.md)。本调查不修改历史任务/Profile 能力结果、不写 CURRENT_HANDOFF 的生产快照，也不更新实现状态为“已接入”。
