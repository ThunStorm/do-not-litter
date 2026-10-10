# 至简（Zhijian）实施计划：AI 请求瘦身、证据可信度、阶段治理与全链路验收

> **交付类型**：可直接交给本项目 Codex/Agent 分阶段执行的实施计划\
> **目标仓库**：`ThunStorm/do-not-litter`\
> **目标分支**：`codex/mac-mini-implementation`\
> **基线复核日期**：2026-10-10（基于该分支源码及 2026-10-09 状态文档；不等于现网运行时验收）\
> **唯一修改范围**：本仓库。**不得修改 `ThunStorm/local-ai-mux`。**\
> **外部依赖原则**：只依赖当前已公开的 OpenAI 兼容接口；Mux 后续增强全部作为可选增益，不作为本计划前置条件。

---

## 0. Agent 执行指令（从这里开始）

你是至简项目的实现 Agent。请按本计划 **Z0 → Z1 → … → Z8 → E2E** 顺序实施，每一阶段具备独立测试、回滚与文档记录。执行前只阅读本计划指定的入口和相关测试，不要全仓盲扫。不得重写现有 Gateway、Cache、POI Resolver、Job/Replay 或数据库 ID 体系。

1. 核对当前分支、工作区状态、现有 `AGENTS.md`/仓库开发规范、`dev docs/IMPLEMENTATION_STATUS.md`、`dev docs/CURRENT_HANDOFF.md`、`dev docs/ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md`。若已有同等机制，**复用并补缺口**，不得因名称不同而复制第二套逻辑。
2. 不覆盖任何未提交更改。开始前记录基线 commit SHA、测试结果、兼容契约快照；若源码与本文不一致，以当前源码为准，先形成一页差异说明再继续。
3. 默认只做**代码、离线测试、文档**；不得自行调用付费/订阅真实模型、消费额度、修改真实密钥、自动续跑生产 Job、确认真实 POI、重启生产 API/Worker、迁移生产库或清理用户历史。真实 E2E 由用户授权后在隔离/可回滚条件下运行。
4. 保留 SQLite/WAL、Mac mini 单 Worker、现有 Web 前端、既有配置/日志习惯；不引入 Redis、LangChain、云 Worker、向量数据库或复杂 Agent 框架。
5. 每个工作包交付：代码 diff、测试、性能/质量证据、契约变更、剩余风险、文档更新。任何未实测项必须标为 `NOT_VERIFIED`，不得描述为已通过。
6. 所有外发请求的 Prompt 和证据不得写入普通审计日志；本机隔离测试允许脱敏采样，原始材料、Cookie、API Key、凭据及视频私人内容不得提交仓库。
7. 严格遵守“**业务证据不损失，模型输入表示可以压缩**”；不得为了 Token 目标截掉视频后段、弱化逐字 Evidence 校验或提高 POI 自动确认风险。

## 0.1 本轮源码差异与执行范围（2026-10-10）

基线 `b365616fc3309ad48d1c5b24470a2ee8989bd1d4`；分支 `codex/mac-mini-implementation`。接手时同模型保存/Replay 与设置样式已有未提交改动，已保留并一并验证，不覆盖原提交快照。起始目标回归 41 项通过，未调用模型。

| 与计划的差异 | 本轮取舍 |
| --- | --- |
| 已有 InterfaceCapabilities、Token 三态、Cache、预算、本地锁、GroundedEvidencePack、严格 POI Resolver 和 run fence | 复用旧机制，只在请求边界及审计 JSON/DTO 补能力，不建第二套目录/Job/表 |
| 旧 parser 允许外插说明；旧格式 smoke 曾授予多个业务 PASS | 保留 parser 兼容，将外插说明和尾逗号记录为规则修复；业务小样单独评级，旧 smoke PASS 不当作高置信业务依据 |
| JobStep 的持久状态已冻结 | 状态保持不变，Attempt 仅附加派生详情；Replay 新执行与历史审计保留 |
| 生产验收文档的预算/Schema 描述过期 | 按当前源码更正累计预算和 0025；旧独立真实毕业门槛没有降低 |
| 原文/业务 Schema 不应为 Token 指标牺牲 | 只缩短引用、去重结构；拒绝无效链与静默截尾，合成 P/R 不冒充模型质量 |

Z0–Z7 核心代码与离线开发验证完成，实机未验证项保持开放；Z8 只保留第 11 节的独立 backlog，不实施新产品功能。独立报告为 [合成 A/B](../benchmark/AI_REQUEST_OPTIMIZATION_AB_REPORT.md)、[跨项目 E2E](../benchmark/CROSS_PROJECT_E2E_REPORT.md)、[发布门禁](../benchmark/RELEASE_ACCEPTANCE.md)。15:56 已沿用保存型号完成 3 次真实 Text/JSON 小样与单样本请求配对；实际型号/Token、真实视频 GT 与 Ollama 推理退出仍无证据。Mux API 未启动的连接阻塞已解除，有限范围见真实小样报告。不得将本次部署等同于完整 E2E 完成。

---

## 1. 目标、范围与既有实现

### 1.1 业务目标

- 降低高重复度的 API 请求文本/JSON 字节、实际输入与输出 Token、请求次数和长视频总时长。
- 继续支持“一视频多核心地点、多 ContentUnit、多个实体/Claim、多地关系、季节月份/时间窗口、特色与推荐菜、反向评价与背景地名”；不损失速读短地名召回。
- 让模型接入能力真实可靠：连通性、格式能力和各业务阶段能力必须独立评级，不得把一个 `{"ok":true}` 当成结构化地点抽取通过。
- 让错误、重试、模型 fallback、局部修复、阶段状态和 Evidence 源头可被用户和开发者解释。
- 实现不依赖 LocalAiMux 新版本的离线回归，并在两个项目独立开发完成后执行受控真实全链路验收。
- 为通用非结构化处理、来源变化监控、视觉证据等后续产品功能留下复用的基础，但不借本包重构全产品。

### 1.2 经源码核对的现有基线（不要重复开发）

| 已有能力 | 既有入口 | 本计划只补什么 |
| --- | --- | --- |
| 模型 Stage Policy/参数和执行路由 | `backend/src/zhijian/ai/stages.py`、`ai/cost_router.py` | 业务级验证、策略拒绝理由与证据化选型 |
| 接口能力目录及参数过滤 | `ai/interface_contract.py` | 可追溯版本/过期策略、业务能力独立模型 |
| AI Gateway、缓存、重试、预算、本地锁 | `ai/gateway.py`、`ai/cache.py`、`ai/reliability.py` | 统一 deadline 传递、实际尝试观测、缓存安全 |
| Token 实测/估算/未知区分 | `ai/token_usage.py`、`ai/token_monitor.py` | 请求内容分类、真实与估算可比性、阶段仪表 |
| 视频校对/分块、Grounded Map、Note Reduce | `services/video_support.py`、`services/grounded_map.py` | 去重、短 ID、按 Stage 的最小证据投影 |
| Evidence 校验、POI Resolver、人工审核 | `services/grounded_map.py`、`services/video_support.py` | 统一事实链、冲突/漏报审计、回归指标 |
| JobStep/Replay、作业心跳与取消 | `services/video_pipeline.py` | 阶段状态及尝试结果规范；不建第二个 Job 系统 |
| Golden 骨架和生产验收清单 | `dev docs/benchmark/`、`dev docs/ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md` | 标注、对照、指标和真实验收补全 |

注意：`_probe_model_profile` 当前用非常简单的 JSON `{"id":"evidence_probe_01","ok":true}` 同时标记 `STRUCTURED_EXTRACTION`、`ENTITY_EXTRACTION`、`TRANSCRIPT_CORRECTION` 为 PASS；这是**本计划必须修正的误判**。`parse_json_object()` 已容忍围栏及尾随逗号，却未充分区分原生成功、确定性修复和重试成功。

### 1.3 明确不做

- 不修改主数据库的 `seg_`、`job_`、`plc_` 等 UUID 生成规则，不做全表 ID 迁移。
- 不要求 Mux 理解 Segment/Claim/POI ID、访问至简数据库、接收特殊业务字段，或代替至简判断旅游 POI。
- 不暗中改 OpenAI `/v1/chat/completions` 的请求 schema；继续使用标准 `model`、`messages`、受支持的可选参数。
- 不把 HTTP gzip、缩短日志内容等同于模型 Token 降低。
- 不默认开启远程模型再次修复；不将本地取消视为远端停止计费。
- 不为求降低人工复核率放宽当前自动确认门槛。
- 不在当前实施包内全面重做 UI 风格、地图、泛化处理器或移动端。

---

## 2. 两项目边界和七个重点议题的责任清单

| 核心议题 | 至简责任（本文件） | Mux 责任（另一个文件；非前置） |
| --- | --- | --- |
| 统一 deadline | Job/Stage/Attempt 剩余时间预算，决定能否发送/重试/回退，协作取消 | Gateway/排队/Adapter 生命周期的本机单请求硬期限 |
| 统一 capability schema | **消费**已公布的 `schema_version=2` 目录，形成业务 Stage eligibility；未知即未知 | **生产**版本化通用能力目录、来源/生效层与可验证约束 |
| runtime telemetry | 记录视频阶段、调用尝试、模型路由、质量、Token 及业务耗时 | 记录连接级排队、Adapter、首输出、超时、实际型号、usage |
| POI 证据链 | Transcript→Claim→Entity→Mention→POI/Review→Note/Map 全程验证 | 不理解、不储存业务 POI 证据 |
| repaired vs direct success | 解析/确定性修复/模型重试/回退分别记录，拒绝伪成功 | 保留上游终态，不伪造 `stop`、`usage=0`，通用生成不做旅游语义修复 |
| Stage 状态机 | 统一业务状态和 Attempt 生命周期、Replay/取消/重用语义 | 通用 Gateway 运行态与清晰的完成/失败终态 |
| 小规模回归基准 | 至简业务 Golden、A/B Token 与 POI 质量及 E2E 门禁 | 通用 SDK/Adapter mock、能力与超时/错误矩阵 |

**独立交付条件**：至简全部离线测试必须可接 `MockLLMProvider` 或标准 OpenAI mock；不得要求 Mux 提供新增 header、endpoint、错误 code 才能通过。Mux 发布后，只能作为额外实机验收组合加入。

---

## 3. Z0 — 基线冻结与最小观测（P0，先于优化）

**目的**：证明节省来自哪里，避免一开始就靠主观删除字段。

### 执行

1. 固定一组已获授权的脱敏/合成样本，覆盖现有 `video-semantic-poi-golden-v1.json` 的 G-001～G-012，另补至少：两个核心城市、速读单次地名、否定/比较地名、价格和单位、季节与月份、无地点视频、字幕与 ASR 差异、长视频分块边界。
2. 在实际发出 `messages` **之前**无侵入地统计：`system_chars`、`domain_chars`、`user_body_chars`、`unique_transcript_chars`、`duplicate_context_chars`、`evidence_quote_chars`、`id_chars`、`json_key_chars`、`json_bytes`、`model_input_chars`、`estimated_input_tokens`、`reported_input_tokens`、`reported_output_tokens`、`usage_source`、`request_count`。
3. 按 `Job / Stage / Attempt / profile / request shape` 聚合；追加 `cache_hit`、`fallback_used`、`retry_count`、`error_code`、`elapsed_ms`，并维持 reported/estimated/UNKNOWN 三态。
4. 历史记录不反向伪填；新字段默认可缺省。优先在现有 Audit/AI Usage DTO 扩展，只有无法保留兼容时才新增迁移。
5. 明确上报的 Token 数不能用 `ceil(chars/2)` 冒充真实模型用量；每条报表显示来源。

**建议入口**：`ai/token_usage.py`、`ai/token_monitor.py`、`ai/gateway.py`、`ai/cache.py`、`services/video_support.py`；新增 `ai/request_metrics.py`（命名可依规范调整）。

**验收**：相同请求的统计结果确定性一致；日志/数据库不落完整 Prompt、凭据；失败及 cache hit 有明确计数，缓存命中不再记成实际模型调用；支持优化前后的离线对比 JSON/Markdown 报告。

---

## 4. Z1 — Request Compiler 与 Short ID Codec（P0/P1）

### 4.1 架构

实现一个小而清晰的 Stage 请求编译器，而不是让每个 Stage 自己不断手写大段 JSON。

建议内部数据流：

`Persisted canonical artifacts → StageEvidenceProjection → ShortIdCodec → Prompt/JSON renderer → capability/payload guard → Gateway → response decode → canonical validation → persisted artifacts`

参考文件（具体是否新建由现有目录决定）：

- `ai/request_compiler.py`：分离 `StageInput`、`CompiledRequest`、`CompilerVersion` 与 `InputIdentity`；
- `ai/short_id_codec.py`：只针对特定 schema 的 ID 字段进行编码/解码，显式作用域和反查；
- `ai/request_metrics.py`：优化前后请求形状统计；
- `services/video_support.py`、`services/grounded_map.py`：逐 Stage 替换消息拼装，不一次性重写 3,000 行模块。

### 4.2 ID 压缩规则

| ID | 模型可见形式 | 服务端/存储 | 特别约束 |
| --- | --- | --- | --- |
| `Segment.id`，如 `seg_<uuid32>` | `s1`, `s2`… | 继续原样 UUID | 优先级最高；按转写快照 ordinal 确定映射，跨分块/重试稳定 |
| `PlaceMention.id` | `p1`, `p2`… | 保留既有 `plc_...` 或现有具体类型 | 仅在确实需要引用的 Note 阶段映射 |
| `ContentUnit` 局部 ID | `u1`, `u2`… | 落库合并后以命名空间生成唯一稳定标识 | 模型局部 ID 不能直接跨分块合并 |
| `Entity` 局部 ID | `e1`, `e2`… | 保留规范化后的跨分块引用 | 关系 source/target 必须同时转换 |
| `Claim` 局部 ID | `c1`, `c2`… | 保留规范化后的跨分块引用 | Claim 的主体实体与 Unit 引用必须一起恢复 |
| Job/Step/Transcript/Place 真正数据库主键 | **正常请求不发送**；确有业务关联时临时引用 | 不变 | 不做替换数据库主键的表结构迁移 |
| 高德 POI ID、模型 ID | 不压缩，对相关上游使用原值 | 不变 | 外部契约禁止改写 |

**作用域规则**：映射身份至少绑定 `transcript/snapshot`、`compiler_version`、输入内容指纹；局部实体映射还绑定 chunk 的**稳定来源区间**，不能只凭易变的 `chunk_index` 或 `split_path` 合并。支持同块内部重复引用与合并后的全局唯一性。

**校验顺序**：

1. 编译前检查所有 canonical ID 属于当前 Snapshot/Job 范围。
2. 序列化时只更改明确定义的 `segment_ids`、`entity_id`、`source_entity_id`、`place_mention_ids` 等结构字段和 Segments 外围标签。
3. 解码返回时遇到未知 ID、越界 ID、重复但不允许重复的局部 ID、关系指向不存在实体，一律拒绝对应结果或保守进入 REVIEW；**不能猜测、静默丢弃、用相似 ID 自动匹配**。
4. quote / supporting_quote / 原始 Segment 文本必须逐字不改，Evidence 校验继续使用原始 UUID 与原文。
5. 缓存命中、Chunk 自适应二分、Replay、fallback 时复用/重建相同映射；旧产物版本仍可正常读。

### 4.3 请求和输出紧凑表示

- 转写行可从 `[segment:seg_UUID 125000-131000ms] 文本` 投影为 `s12|125-131|文本` 或 `s12|文本`（取决于 Stage 是否用到时间）；原始毫秒和完整 ID 保留在本地。
- 校对 `items=[{target, context_before, context_after}]` 改为单次去重的 `segments=[...]` + `target_ids=[...]`，模型仅返回目标 ID 的修改；前后文保留语义窗口，不重复全文。
- 优先使用紧凑 JSON（`separators=(',',':')`）及按 Stage 所需字段投影；不急于把 `segment_ids`、`supporting_quote` 等全部改成单字母。
- 不能将“只提取高置信度地点”当作精简方案。全部明确提及的候选仍应保留，后续再分 RESOLVE/REFERENCE/REVIEW。

### 4.4 缓存与版本

**重大风险**：所有视频都可以有 `s1`，且当前缓存 Key 依赖 messages。**不能只用压缩后的 messages 判断业务身份。**

对 AI Cache key/semantic options 添加可验证的 `compiler_version`、`source_content_hash`、`snapshot_identity`、`stage_projection_version`、`short_id_map_fingerprint`；实现稳定计算规则，并测试“不同视频相同 `s1` 不互串”“同快照 Replay 命中”“内容改变不命中”。旧缓存保留现有读取机制，只有原语义等价且可验证时可复用，否则安全失效；不得删除用户历史缓存来方便开发。

**验收**：ID 完整往返、文本/quote 字节一致；同视频分块分裂/回退/重播及两个视频重叠局部 ID 均无错链；数据库主键、前端 API 不变；校对结果仍只能修改 `target_ids`。

---

## 5. Z2 — 按阶段精简 Prompt、Evidence 与模型调用（P1）

按以下顺序小步提交，每一步做 Z0 基线对照。

| Stage | 需要执行的工作 | 不允许的捷径 |
| --- | --- | --- |
| `TRANSCRIPT_CORRECTION` | 统一邻接上下文索引，目标只发一次；上下文重叠去重；必要时做局部候选选择 | 不删除容易错听的地点、数字、否定信息 |
| `GROUND_MAP` | 应用短 Segment ID，精简时间码/模板；分块只带当前相关领域知识；统一 Schema，不重复同义规则 | 不默认“一视频一城市”、不靠截断 Claim 条数制造节省 |
| `EXTRACT_TRAVEL_FACTS` | 仅对当前仍执行的 legacy/force re-extract 路径优化；先检查是否已由 Ground Map 复用，避免重复抽取 | 不并行运行第二个全转写地点识别流程 |
| `NOTE_REDUCE` | 精简 `summary/key_points/quote` 重述；已核验 Claim 采用精简投影与 ID 引用，按需恢复 quote | 不让摘要失去否定/价格/时间/来源限定条件 |
| `GENERATE_AI_NOTE` | 复用既有 Ground Map、facts、notes 与 profile 机制；减少冗余系统规则 | 不退回每轮重新发送完整转写 |
| `DOMAIN_CONTEXT` | 同一 Stage 仅送允许的精简 glossary/aliases；限制无关 examples 和超长 supplement | 不把领域规则转换为无证据的地点事实 |

### Prompt 改版规则

- 新编译器和 Prompt/schema 版本必须联动；Prompt 输出形状变更同步 validator、cache 版本、Golden。
- 优先压缩**重复结构**，再压缩固定措辞，不先压缩原始证据。
- 跨 Stage 共用规范在服务器代码中保持单一来源，传给模型的固定规则按任务必要性投影；不允许偷删 system 证据/安全条款。
- 不把 prompt caching 当成已存在的订阅优势；如无法从真实元数据判断 cache 命中，则收益为 `UNKNOWN`。
- 在分块边缘至少保障关联地点、否定与时间窗口必要邻段；按 Token/字节及模型已证实能力动态估计，不以单纯字符上限截尾。
- 任一分块超预算应改小块或给出可见的 `NEEDS_USER/FAILED`，绝不悄悄丢掉未处理段。

**验收**：所有被发送的原文 Segment 均可覆盖回溯；无静默跳段；地点/Claim 召回与基线不下降，直接统计请求重复字符比例。

---

## 6. Z3 — Capability、业务 Probe、统一 Deadline 与质量路由（P0）

### 6.1 消费通用 capability，而非再造目录

当前 `ai/interface_contract.py` 读取 Mux `/api/chat/models` 的 `schema_version=2` 和 `/v1/models`，具备最基本的参数/消息能力核对。保留此机制：

- 定义 `TransportCapabilitySnapshot`：`SUPPORTED / UNSUPPORTED / UNKNOWN`、`limiting_layer`、版本、采样时间、能力哈希和精确模型 ID。
- 定义独立的 `BusinessCapabilityAssessment(stage, model, prompt_version, benchmark_version, probe_status, evidence_ref, tested_at)`，表示真正完成校对/地点识别/复杂结构化笔记的程度。
- **连接 smoke ≠ JSON 解析通过 ≠ 业务 Stage PASS**。将 `_probe_model_profile` 的简单小 JSON 仅归为 `FORMAT_SMOKE`，不能同时授予 `TRANSCRIPT_CORRECTION/ENTITY_EXTRACTION/STRUCTURED_EXTRACTION` PASS。
- 支持低成本逐业务场景的小样，含地点多实体、逐字证据、否定比较和错音；不同 stage 独立评级。未测为 `NOT_TESTED/UNKNOWN`，不能冒称 PASS。
- 当前 Stage 路由在已配置允许未验证模型时可保留显式用户选择和**提示风险**，但 AUTO 不得默许 UNKNOWN 获得高置信业务能力；不要因未测就从模型目录消失。
- Snapshot 能力陈旧、精确型号/Adapter 版本改变时重新标记待核验，不越权自动调用真实模型。

### 6.2 统一 deadline（明确分层）

用**单一预算决策点**为 `Job → Stage → Attempt` 计算截止时间，而不是分别叠加多个无解释的 timeout。

推荐规则：

`usable_remaining = min(Job hard deadline - reserve, Stage hard deadline, policy allowance) - elapsed`

- 真实 Attempt 开始前先扣掉至简内本地锁、速率限制、前置等待消耗；每个请求检查余量。
- 对 Mux，当前 `/api/health.execution_limits` 可读到服务器公开的期限信息（如目前记载 600 秒、排队 30 秒）。这些是**辅助约束**，不能要求 Mux 新增字段；目录不可用时采用当前配置和保守策略，不进入无限等待。
- 当客户端 HTTP 超时小于可能的 Mux Gateway 执行期限时，应有明确策略：在 Job 预算允许时留足安全余量获取 Mux 错误；预算不允许则本地提前终止，但将远端是否仍运行标为 `UNKNOWN`。不能简单把所有超时设成 660 秒。
- 排队与请求本体时间分开记录；只有在剩余预算足够且错误可证明未执行时才安全重试。对未知远端完成/可能已计费的 timeout，禁止自动重发同请求。
- Job 协作取消必须穿过 HTTP 等待、fallback、retry wait；现存 Ollama 取消后 llama-server 仍生成属于**独立必须封闭的缺口**，通过公开可用且安全的生命周期手段限时停止/清理，并用真实进程退出证据证明，不能只断开客户端。
- `429` 区分 `rate_limit`、`quota_exhausted`、`busy_queue`、`cooldown`，分别决定延迟/切换/NEEDS_USER，不盲重试。
- Deadline 来源、剩余预算、已尝试次数、fallback 决策入审计，但不带全文。

**验收**：可控虚拟时钟单元测试覆盖 queue 消耗、慢首字、JSON 截断、并发锁、Stage 跨界、超时取消后未知状态、重试预算耗尽；全链路无超过总预算的后台重复模型提交。

---

## 7. Z4 — “direct success / repaired / fallback” 结果分型（P0）

现有 `ai/structured_output.py` 会进行 Markdown 围栏和尾随逗号修复，结果最终“解析成功”不足以衡量模型可靠性。

统一为**两个独立维度**，避免把 repaired/fallback/cache 错误归到同一类：

**解析质量维度**：

- `DIRECT_VALID`：首次输出无需实质修复，原生可解析，业务 Schema + Evidence 通过。
- `NORMALIZED_VALID`：仅清理外部围栏、BOM、空白，不修改结构。
- `DETERMINISTIC_REPAIRED`：受控确定性修复（例如 JSON 尾逗号）后通过；必须记录规则名。
- `MODEL_REPAIRED`：确有单独的模型二次修复尝试且通过（默认不开启）。
- `INVALID/INCOMPLETE`：Schema/证据/引用不合法，或输出截断。

**执行路径维度**：

- `PRIMARY_DIRECT` / `PRIMARY_RETRY` / `FALLBACK` / `CACHE_HIT`；
- `finish_reason` 与 `usage` 单独保留 nullable 语义；
- 成功但有部分事实因证据无效丢弃，另标 `PARTIAL_ACCEPTED`，并统计 rejected item 数，不能作无损成功。

不得把 JSON 被修复后成功统计为 first-pass 成功，不把 fallback 成功冒充首选模型表现。保留请求身份与原结果 hash；日志只记录规则、次数和哈希，不持久化隐私正文。

**验收**：用合法 JSON、代码围栏、尾随逗号、缺右括号、截断、外插说明、无效 Segment、错误引用、fallback/cache 全矩阵测试；修复后仍走完整 Schema/Evidence 检验。

---

## 8. Z5 — Stage 状态机、Telemetry 与 UI 诊断（P0/P1）

### 8.1 与现有 JobStep 协调

`video_pipeline.py` 已拥有 `JobStep`（如 `RUNNING/COMPLETED`）、Job、StepArtifact、Replay Fence；**不得另立一套独立而可能冲突的 Job 状态真源**。

建议：

- JobStep 保持现有持久化状态与 API 兼容；必要时新增一个 `stage_outcome`/`attempt_state` 的**派生视图或附加详情**。
- Attempt 子状态：`QUEUED → DISPATCHED → (STREAMING) → VALIDATING → [REPAIRING / RETRY_WAIT / FALLBACK_WAIT] → TERMINAL`；缓存命中直接走 `CACHE_HIT → TERMINAL`。
- Stage 语义结果：`SUCCESS / PARTIAL_SUCCESS / REUSED / SKIPPED / NEEDS_USER / FAILED / CANCELLED`。`REUSED` 是执行来源，与业务质量结果需区别，不能覆盖现有 Step 状态。
- 明确转移表，拒绝非法反向跳转；终态幂等且不可被旧 Attempt 回写；Replay 只能建立新 run/attempt 语义，保留旧审计，不改历史事实。
- 取消后迟到结果必须被 run fence 挡住；UI 不把 `PARTIAL_SUCCESS`、`REVIEW_REQUIRED`、`FAILED` 统一写成“完成”。

### 8.2 Runtime Telemetry

聚合 `job_id/stage/attempt_id`、请求编译器版本、供应商/请求模型/实际模型（如可知）、request_id、bytes、reported/estimated/unknown usage、cache/fallback、`queue_ms`、`provider_ms`、`end_to_end_ms`、结束原因和错误码。

- Mux 响应的可选 `localmux` 运行元数据要在 `providers/llm.py` **安全地采集并透传**到 `LLMResult.metadata` 和审计；字段缺失时允许 UNKNOWN。
- 至简先可独立记录自己知道的阶段耗时；若 Mux 将来附加 `queue_ms/adapter_ms`，只在结构校验后显示。不要求新字段。
- 不能把 LocalAiMux 实际用量未知映射成“0 Token”；不能把估算值写成可信余额。
- UI 优先在现有任务详情/AI 用量视图增加小型“调用明细：直接/修复/重试/回退、阶段、耗时、使用量可信度”信息；不新建重型管理后台。
- 改善设置页面过密的阶段路由展示只限与此功能相关的字段/一致性；全站字体按钮统一设计另列后续视觉维护任务，避免本轮大拆样式表。

**验收**：前端可识别直接/修复/回退/缓存/UNKNOWN，用户看得到卡住在队列还是业务阶段；现有旧审计与新 DTO 兼容；无敏感数据被记录。

---

## 9. Z6 — POI Evidence 链与保守自动确认（P0/P1）

### 9.1 数据链

明确既有 Grounded Map v3 中的：

`Source → VideoAsset → Transcript(version)/Snapshot → Segment → ContentUnit → Entity → Claim → PlaceMention → POI Candidate → Confirmed/Review/Unresolved → Note/Map/Route`

每个用户可见的推荐景点、餐馆推荐菜、最佳季节、价格、路线提醒都能够回溯到具体 Segment，最好包含**可跳转时间码、逐字 quote、解析版本、候选依据、决定记录**。

### 9.2 实现要求

1. 构建一个现有模型可投影的 `EvidenceTrace` 或查询组装函数（无需立即新增复杂表），统一检查 id/quote/source/version。
2. POI 解析保留 v3 已有 `AUTO_EXACT`/`AUTO_NORMALIZED` 等严格门禁，不重建 resolver；加强区域/上下文候选排序时不能凭“天津”将行政区强行匹配市政府。
3. 同一视频多核心地区、多 ContentUnit、一个 Segment 多地点、Reference 比较项与真正可行动地点分开计数；`REFERENCE_ONLY/SKIP` 不落可行动 POI。
4. 内容与候选矛盾时保留冲突和候选证据，进入 REVIEW；无来源或空 quote 不得自动确认。
5. 前端在现有视频笔记页面及 POI Review 上复用证据组件：原文、时间码、当前地点名、候选名称与位置、为何待确认。已有功能先完善一致性和缺口，不另造第二套确认页。
6. `source_coverage`、`claim_evidence_validity`、`actionable_poi_precision`、`actionable_poi_recall`、`manual_review_rate` 与 `review_reasons` 加入 Golden 报告。

**验收**：全部已接受的 Claim/Mention 有有效来源；不会遗漏单句中两个地点；对仅作为比较的地名不自动落点；没有坐标/地址凭空生成；拒绝/人工 tombstone 在 Replay 后仍生效。此前一条真实续跑有 3 REVIEW、12 UNRESOLVED、0 confirmed，这一条不应被直接视为 12 次错误：需要看每个地名是主体、背景还是语义不清。

---

## 10. Z7 — 小规模 Golden、质量回归与 Token 基准（P0）

### 10.1 数据集与标签

以 `dev docs/benchmark/video-semantic-poi-golden-v1.json` 的 12 个冻结语义案例为起点，加最小但有代表性的真实获授权样本：

- 至少 1 个结构清晰的地区→多景点视频；
- 至少 1 个非“地区→景点”的主题视频；
- 至少 1 个城市/景点对比视频（可行动 vs 参考）；
- 至少 1 个快语速/ASR 容易丢小地名的视频；
- 至少 1 个季节/月份/丰枯水/排队/价格信息的视频；
- 至少 1 个非地点视频；
- 至少 1 个长视频（建议 15–30 分钟），跨多个 chunk；
- 另保留 source subtitle、ASR、人工校对差异的输入变体。

每个样本标 `video_id`（使用脱敏固定 ID）、预期 `content_units`、`entities`、`actionable/reference`、`claims`、`segment evidence`、`visit_windows`、真实地点匹配（若允许）及不应出现的幻觉。

### 10.2 对照运行

- A 组：当前请求/Prompt/ID 基线；B 组：Request Compiler 优化后；两组使用相同输入、Stage 路由、已核实模型、温度、预算与人工标注，记录 hash。
- 在 Mock 模式做确定性结构/缓存/状态回归；在用户授权时再做少量真实模型成对实测。
- 指标至少：`input_json_bytes`、`input_chars`、`reported_input_tokens`（可靠时）、`estimated_tokens`（单独）、模型调用次数、输出 Token、时长、cache ratio、JSON direct_valid_rate、repaired_rate、fallback_rate、evidence_validity、POI precision/recall、manual review rate、Claim/Visit Window 覆盖率。
- 避免将多次随机生成波动当成优化收益；对少量真实样本标明 `N`、模型实际身份及统计置信度，不输出伪精确百分比。

### 10.3 发布门禁

**强制硬门禁**：

- 不允许引入错配 Segment、串视频缓存、丢失后续分块、Reference 错落 POI、无证据 Claim、未经确认的自动 POI。
- Golden 基线的地点 Recall/Precision、Quote 有效率、有效 Visit Window/推荐菜提取不退化；允许的偏差必须有逐样本人工批准与原因。
- Job/Step/Cache/Replay/Deadline/取消/错误分类回归通过；同一请求优化前后输出可无损恢复为既有 API DTO。
- AI Token 报告不混淆 `reported / estimated / unknown`。

**优化目标而非硬承诺**：在相同业务质量下，争取真实输入 Token 减少 **20%–30%**；若实际模型缺乏可信 token usage，不能宣称达标，只能显示字节和估算结果。低于目标但业务正确仍可按用户确认发布性能工作包，不得为了指标伤害召回。

**脚本建议**：扩展既有 `scripts/run_ai_benchmark.py`，不要平行创建一套重型基准框架。

---

## 11. Z8 — 延续产品能力的后续里程碑（P2/P3；**独立于前述核心改造**）

这些是最初系统评估中建议的新增能力，纳入路线图以避免遗漏，**不是 Z0–Z7 发布的阻塞条件**。每项需独立 Feature Flag、Golden 与 PR：

| 工作包 | 完成要求 | 准入条件 |
| --- | --- | --- |
| 通用 `GenericProcessor` MVP | 网页、PDF、聊天、通知等产生 Evidence-backed summary、entities、date/location/action_items | Z5/Z6 的 Stage/Evidence 契约稳定后；复用现有 Source/Snapshot |
| `Source Watch` MVP | HTTP ETag/Last-Modified/content-hash 检测变化，保存新 Snapshot/diff，只对差异生成摘要 | 单 Worker 稳定；默认不登录、不高频抓取 |
| Contextual Vision | 只抽取有文本锚点的关键帧（路牌、菜单、价牌等），分别保留 Visual/Transcript Evidence | 真实 Vision Provider 能力 + P0 E2E 通过，不能仅依靠模型目录声称支持 |
| 地点聚合与轻行程建议 | 汇总多视频地点证据、冲突、月份/时段，生成带来源的候选路线；优先人工确认 | 不直接预订、购买或自动生成不存在的 POI |
| 产品 UI 稳定性维护 | 统一按钮/字体/间距/待确认状态，在既有组件规范做局部收敛 | 不借 AI Gateway 改造全站视觉 |

**执行边界**：除非用户明确批准 Z8 某个独立工作包，本计划实施时只更新其 backlog/技术契约，不应自动引入 Z8 代码或改变当前项目主线。

---

## 12. E2E — 两项目独立完成后的全链路验收（验收由至简负责；Mux 只提供标准服务）

> **重要**：E2E 是本计划最终验收章节，**不是对 Mux Agent 的修改指令**。Mux 保持独立仓库、独立版本、独立发布。两项目单独的离线测试应在 Mux 新版未部署时就能通过。跨系统真实生成必须由用户明确授权。

### 12.1 测试前固定证据

- 至简 Git SHA / compiler、prompt、schema、Golden 版本 / 配置快照 / DB 备份和迁移版本 / 服务健康及活跃任务数；
- Mux 已安装 App 的 Build SHA、schema_version、`/v1/models`、`/api/chat/models`、`/api/health.execution_limits` 的**脱敏快照**；
- 精确测试模型 ID、连接状态、Key scope（只验证权限，不导出 Key）、实际型号声明/未知状态；记录操作系统版本。
- 只用已授权的模型、合法媒体来源、高德接口；不自动扩大权限，不暴露密钥。无真实访问条件时 `BLOCKED_EXTERNAL`，不以 Mock 取代真实通过。

### 12.2 分层 E2E 矩阵

| 场景 | 运行方式 | 必须检查 |
| --- | --- | --- |
| A. 原生兼容 Mock | 至简 → 标准 OpenAI Mock | system+user、不支持参数跳过、JSON/SSE可选能力、请求上限、错误契约 |
| B. 现有 Mux 版本兼容 | 至简 → 当前已安装 Mux Mock/合成接入 | 未新增字段时依旧可运行；`schema_version=2` 对齐；UNKNOWN 安全 |
| C. 当前单模型 Text/JSON | 用户授权后，选 1 个已配置型号低额度调用 | 模型真实回答、非流式结果、JSON direct/repair 分类、实际 route/usage |
| D. 字幕输入视频 | 一条完整视频 → Note/POI/Map/Review | 所有 Stage 状态、Segment 还原、Evidence/时间码、没有漏段 |
| E. ASR/校对视频 | 一条 ASR 视频 → Note/POI | 速读地点、错音、价格/否定、校对 targets、背景地名 |
| F. 多地点/长视频 | 15–30 分钟/多区域/跨分块 | 多 Unit、多地实体、无重复 ID、chunk replay、最末段处理 |
| G. 异常与恢复 | Mock 注入 429/503/timeout/truncated/invalid JSON/取消 | Deadline、无盲重试、正确 `NEEDS_USER`、fallback、resume、run-fence |
| H. Cache 与强制重生成 | 同一输入、不同输入、force-regenerate、fallback 后 cache hit | 不跨视频串缓存、不把 cache 当新 Token 花费、实际型号可追溯 |
| I. 并发与排队 | 模拟多个至简 Job + 有限 Agent Lane | 不突破网关限额、等待可见、不把拥塞误判模型无效 |
| J. Ollama 取消 | 隔离机器上的实际受控取消 | 客户端终止与实际推理停止分别证明；不可证明的标 UNKNOWN |
| K. A/B Token 与质量 | 同一样本同模型新旧编译器 | 输入 Token（如实测）、总耗时、调用次数、POI/Claim/Evidence 指标对照 |

### 12.3 联调故障归因

当联调失败时，仅用标准 HTTP/目录/本地调用记录判定：

- **至简负责**：Payload 编译、ID decode、业务 Schema、Evidence、POI、Stage 策略、Replay、质量门槛。
- **Mux 负责**：Key/scope、公开能力目录、Gateway 限流、Agent 队列/启动、标准响应/错误/usage、CLI 连接与实际 Adapter。
- **上游未知**：供应商额度、订阅规则、远端是否继续计费/执行、未公开模型限制；保持 UNKNOWN，不能随意归责。
- 双方使用 `request_id`（如 Mux 已提供）和时间范围关联；新增客户端追踪 header 为可选，**不得硬依赖**。

### 12.4 验收产物与最终发布门禁

形成以下文件，建议置于 `dev docs/benchmark/` 或其已存在的归档结构：

1. `AI_REQUEST_OPTIMIZATION_BASELINE.json`：新旧请求构成及已知/未知来源；
2. `AI_REQUEST_OPTIMIZATION_AB_REPORT.md`：逐场景、总表、异常样本和差异；
3. `CROSS_PROJECT_E2E_REPORT.md`：Z/Mux build SHA、能力快照、结果矩阵、耗时/用量归因、真实测试批准记录；
4. `RELEASE_ACCEPTANCE.md` 或更新原 `AI_GATEWAY_PRODUCTION_ACCEPTANCE.md`：逐门禁 `PASS / FAIL / BLOCKED_EXTERNAL / NOT_RUN`，不删除已有历史；
5. 发布、回滚操作和风险说明（含旧 Job/Cache/业务文档兼容性）。

**不得发布/宣布 E2E 完成的情况**：有未解释的跨视频 ID 错链、POI 无证据自动确认、已知 429/timeout 下重复无保护发起可能计费的请求、`UNKNOWN` 用量被记为 0、Stage 终态被旧请求覆盖、任一合成契约的兼容测试失败。

---

## 13. 分批提交与可独立关闭的实施顺序

| 阶段 | 交付内容 | 单独关闭条件 |
| --- | --- | --- |
| Z0 | 最小数据/请求构成与测试基线 | 测量不改变运行逻辑；可用 Mock 再现 |
| Z1 | 编译器与短 ID（先校对、再 Ground Map、Note） | 稳定往返、缓存/Replay/分块回归通过 |
| Z2 | Stage 精简与重复 Evidence 治理 | A/B 质量无退化 |
| Z3 | 业务 Probe、deadline、可靠路由 | UNKNOWN 不伪 PASS、超时矩阵全绿 |
| Z4 | 解析质量结果分型 | repaired/direct/fallback/cache 可分别统计 |
| Z5 | Stage 状态与轻量 Telemetry/UI | 终态幂等，旧 Job 可读 |
| Z6 | 完整 POI Evidence 关联 | 多地/比较/否定/回溯 Golden 通过 |
| Z7 | Golden 发布门禁 | 报告可复现并具备质量、Token 两组指标 |
| Z8 | 选定的增量产品功能 | 用户另行批准后独立验收 |
| E2E | 联调与真实门禁 | A–K 逐项有真实证据或明确 BLOCKED |

每个工作包完成后运行目标相关测试，再运行全量：

```bash
# 在项目当前 Python 虚拟环境中；依现有 README/CI 设置工作目录
pytest backend/tests -q
# 依项目已有 ruff 配置运行 check/format 校验
# 在 frontend 目录
pnpm verify
```

不得凭文档中的历史通过数量代替本次实际输出。需要 Alembic 迁移时先证明现有 schema 无法表达，并同时提供升级/回滚/旧记录兼容测试。

## 14. 交付总结模板（Agent 每一阶段填写）

```markdown
### 阶段：Z?
- 当前分支 / 基线 SHA / 结束 SHA：
- 修改文件与设计边界：
- 复用旧能力与新增差异：
- 原始 ID 与短 ID 往返测试：
- 请求字节 / 实测 Token / 估算 Token / UNKNOWN：
- 业务 Golden P/R、Evidence 有效率、月份与 Claim 覆盖：
- 直接成功 / normalized / repaired / fallback / cache：
- Deadline / 取消 / Replay / Queue：
- 单测、全量测试与 UI 结果：
- 真实 Provider 调用：有/无，用户授权记录：
- 未解决问题及回滚：
- 文档/版本/配置更新：
- 是否达到本阶段发布门禁：
```

### 核心决策

**至简完整保存证据；只在模型请求边界短 ID 化和按需精简；外部 Mux 仍是通用 OpenAI 兼容服务。以 POI 召回、Evidence 可信和任务稳定性优先于单纯 Token 数字。**

## 本轮指定视频补充（2026-10-10）

BV11Ao7BYE1V真实ASR视频流程已完成，PARTIAL_SUCCESS、6个地点待人审。真实异常暴露Stage0未约束Profile JSON重试，已补修/测试/部署43f42ff，保留旧失败与取消记录后仅从笔记继续；未把离线重解析旧输出作为新生成结果，实际10次尝试。详见 [视频验收及未验证项](../benchmark/VIDEO_E2E_BV11Ao7BYE1V_REPORT.md)，整体验收仍受完整矩阵/人工GT/实际Token/上游退出门禁限制。
