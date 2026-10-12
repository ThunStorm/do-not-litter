# Stage Policy 与参数设置

> 来源：ai-gateway/AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md，原章节 41A–41I（正文保留，2026-09-03 分篇）。返回 [主题索引](AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md)。本篇是契约/规划，不是已实施清单；当前结论见 [实施状态](../IMPLEMENTATION_STATUS.md)，安全与回归见 [冻结清单](../REGRESSION_AND_CHANGE_GUARD.md)。裸文档路径均以 dev docs/ 为基准。只读取命中章节及其必要约束。

# 41A. Stage-level Model & Parameter Policy

本项目必须把“每个 AI 流程环节独立选择模型及参数”作为一等能力实现，而不是只允许覆盖 Provider / Model。

目标：

```text
Global Defaults
    ↓
Capability Defaults
    ↓
Saved Stage Policy
    ↓
Single Job Override
    ↓
Single Stage Runtime Override
```

越靠下优先级越高。

最终每个 AI Stage 都可以单独控制：

```text
Execution Mode
Local Provider / Model
Remote Provider / Model

Temperature
Max Input Tokens
Max Output Tokens
Thinking
Timeout
Retry Count

Confidence Threshold
Escalation Threshold

Context Strategy
Chunk Size
Neighbor Context

Domain Pack
Cache Policy
Force Regenerate
```

注意：

> 不是所有参数都对所有 Stage 可用。必须通过 Stage/Capability 参数白名单与 Provider Capability 校验，避免 UI 暴露无效参数。

---

# 41B. AIStagePolicy

新增统一配置模型：

```python
class AIStagePolicy(BaseModel):
    stage: str
    capability: AICapability

    # Routing
    execution_mode: AIExecutionMode | None = None

    local_provider: str | None = None
    local_model: str | None = None

    remote_provider: str | None = None
    remote_model: str | None = None

    # Generation
    temperature: float | None = None
    max_input_tokens: int | None = None
    max_output_tokens: int | None = None
    thinking: bool | None = None

    # Runtime
    timeout_seconds: int | None = None
    retry_count: int | None = None

    # Quality / Escalation
    confidence_threshold: float | None = None
    escalation_threshold: float | None = None

    # Context
    context_strategy: str | None = None
    chunk_size: int | None = None
    neighbor_segments: int | None = None

    # Domain
    domain: str | None = None
    domain_pack_ids: list[str] = []

    # Cache
    cache_enabled: bool | None = None
    force_regenerate: bool = False
```

允许项目根据现有 Settings / Pydantic 结构调整字段名，但必须保留上述能力边界。

---

# 41C. 参数继承优先级

运行时必须通过统一 Resolver 合并参数。

推荐：

```text
System Defaults
    ↓
Global AI Preset
    ↓
Capability Defaults
    ↓
Saved Stage Policy
    ↓
Job-level Override
    ↓
Stage Runtime Override
```

最终产出：

```python
ResolvedAIStagePolicy
```

业务 Pipeline 不直接自己拼配置。

示例：

```text
Global:
    BALANCED

Capability STRUCTURED_EXTRACTION:
    temperature = 0.1
    max_output_tokens = 1200

Stage TRAVEL_PLACE_EXTRACTION:
    execution_mode = LOCAL_FIRST
    local_model = qwen2.5:7b
    remote_model = remote-strong
    confidence_threshold = 0.75

Single Job:
    quality = QUALITY

Single Stage Runtime Override:
    TRAVEL_PLACE_EXTRACTION = REMOTE_ONLY
```

最终该 Stage 应按：

```text
REMOTE_ONLY
remote-strong
temperature = 0.1
max_output_tokens = 1200
confidence_threshold = 0.75
```

执行。

---

# 41D. Stage 参数必须区分“模型参数”和“业务参数”

不要把所有参数都塞进 Provider Options。

分两层：

## Model Runtime Parameters

```text
temperature
max_input_tokens
max_output_tokens
thinking
timeout
retry_count
```

## Stage Semantic Parameters

例如 Transcript Correction：

```text
candidate_threshold
neighbor_segments
force_full_correction
chunk_size
```

例如 Note Chunk：

```text
chunk_size
section_target_length
max_key_points
```

例如 Place Extraction：

```text
max_places
minimum_evidence_count
domain_pack_ids
```

Stage Semantic Parameters 应归属于 Stage Policy 或 Stage-specific config，而不是 Provider 层。

---

# 41E. Stage 参数白名单

新增：

```text
StageParameterSpec
```

示例：

```python
StageParameterSpec(
    stage="TRANSCRIPT_CORRECTION",
    allowed={
        "execution_mode",
        "local_model",
        "remote_model",
        "temperature",
        "max_input_tokens",
        "max_output_tokens",
        "thinking",
        "timeout_seconds",
        "retry_count",
        "confidence_threshold",
        "escalation_threshold",
        "chunk_size",
        "neighbor_segments",
        "domain_pack_ids",
        "cache_enabled",
    }
)
```

UI 与 API 均通过该 Spec 判断哪些参数可配置。

禁止：

```text
前端写死一套参数
后端接受任意 JSON
```

---

# 41F. Provider Capability Validation

当用户给某个 Stage 配置参数时，需要验证目标 Provider / Model 是否支持。

例如：

```text
qwen2.5:7b
thinking = true
```

如果 Profile 声明：

```text
supports_thinking = false
```

保存时应拒绝或明确忽略，不允许静默假装生效。

同理：

```text
Vision Stage
+ qwen3:8b
```

应直接阻止保存。

JSON Schema、工具调用、上下文窗口、输出长度等同样需要校验。

---

# 41G. Stage 默认参数建议

第一版可提供以下默认值作为起点，最终以 benchmark 调整。

## TRANSCRIPT_CORRECTION

```text
execution_mode = LOCAL_FIRST
temperature = 0.1
thinking = false
retry_count = 0
confidence_threshold = 0.75
escalation_threshold = 0.60
neighbor_segments = 2
chunk_size = 6000~12000 chars（由 benchmark 决定）
cache_enabled = true
```

## NOTE_CHUNK_SUMMARY

```text
execution_mode = LOCAL_FIRST
temperature = 0.2
thinking = false
retry_count = 0
max_output_tokens = 1200~2000
cache_enabled = true
```

## FINAL_NOTE

```text
execution_mode = AUTO 或 REMOTE_FIRST（由 Quality Preset 决定）
temperature = 0.3~0.5
thinking = optional
retry_count = 1
cache_enabled = true
```

## TRAVEL_PLACE_EXTRACTION

默认由 Map 阶段聚合。

当单独启用模型重跑时：

```text
execution_mode = LOCAL_FIRST
temperature = 0.1
thinking = false
retry_count = 0
confidence_threshold = 0.75
domain = travel
cache_enabled = true
```

这些数字不是不可变常量。

必须：

```text
Benchmark
→ 调整 Capability Default
→ 用户仍可覆盖
```

---

# 41H. UI：每 Stage 独立设置

`Custom` 模式必须支持展开每个 AI Stage。

示例：

```text
Transcript Correction
├─ Mode: Local First
├─ Local Provider: Ollama
├─ Local Model: qwen2.5:7b
├─ Remote Provider: DeepSeek-compatible
├─ Remote Model: xxx
├─ Temperature: 0.1
├─ Max Input Tokens: Auto / 8000
├─ Max Output Tokens: 1000
├─ Thinking: Off
├─ Timeout: 180s
├─ Retry: 0
├─ Confidence Threshold: 0.75
├─ Escalation Threshold: 0.60
├─ Neighbor Segments: 2
├─ Domain Pack: Auto
└─ Cache: On
```

另一个：

```text
Final Note
├─ Mode: Remote First
├─ Remote Model: strong-model
├─ Temperature: 0.4
├─ Max Output Tokens: 5000
├─ Thinking: Auto
├─ Retry: 1
├─ Domain Pack: Auto
└─ Cache: On
```

---

# 41I. UI 参数展示层级

为了避免设置页过度复杂，分：

```text
Basic
Advanced
```

Basic：

```text
Mode
Local Model
Remote Model
Quality
```

Advanced：

```text
temperature
tokens
thinking
timeout
retry
confidence
escalation
context/chunk
domain
cache
```

默认折叠 Advanced。

---


## 偏好模式与已保存备用（2026-10-08）

LOCAL_FIRST/REMOTE_FIRST 优先使用相反位置候选作为备用；没有相反位置候选时，保留全局 model-routing 已保存且符合当前阶段能力的 fallback_id。候选须启用、不同于主模型且能力 Probe 不为 FAIL；不自动扩大未声明的能力。LOCAL_ONLY/REMOTE_ONLY 和 Ground Map semantic escalation 不采用此回退。Job 使用提交时快照中的全局备用，修改当前 Settings 不改旧 Job 的备用。参数与验收见[订阅 CLI 稳定性](LOCAL_ROUTER_PROVIDER_COMPATIBILITY_SPEC.md#12-订阅-cli-稳定性实施与验收2026-10-08)。

## 阶段重试上限补充（2026-10-10）

显式 Stage `retry_count` 优先于 Model Profile：同时限制 HTTP 重试及 JSON 修复重试，JSON 上限取 Profile 与 Stage 的较小值。因此 `retry_count=0` 禁止两类模型重发；没有阶段覆盖时沿用 Profile。确定性 JSON 规范化不算模型重试，最多两个多余尾部闭合括号只在完整对象已经可解析时移除；不丢弃第二个文档或额外字段，修复后继续完整 Schema/Evidence 校验并记录规则。历史失败/修复审计不回填。


## 正常批次与调用经验隔离（2026-10-12）

`max_attempts`表示单批逻辑请求的实际尝试上限，包含HTTP重试、JSON修复与备用调用，不能直接作为整个阶段的正常批次数上限。校对、证据地图、笔记分包按计划批次B分配B×上限的有界阶段额度，二分拆分增加实际计划叶子批次；同时保留单Job累计次数、Token及墙钟硬预算。系统默认Stage重试值不覆盖Model Profile，只有保存/任务/运行时显式值才优先。

批次经验使用v2不透明配置指纹，包含主/备用供应商、入口、Profile/模型、账户摘要、接口约束及有效生成/稳定性参数。不同免费/官方入口或参数不共享经验；v1仅模型名记录保留历史，生产不借用。校对Job内经验也使用该指纹，模型参数变化后不沿用旧条目。原始LLM缓存及证据地图语义Artifact同样包含调用配置指纹，地图还包含执行模式与升级阈值；限时请求只临时缩短客户端超时，调用结束恢复配置，不把剩余期限传播给下一批。有效的来源/Evidence复用仍遵守原身份及Replay规则。无密钥进入快照/日志/经验条目。

本地地图的输入块上限同时受输出容量约束，显式输入长度不能绕过输出容量；4096输出默认每块最多16段。Ollama JSON调用使用原生format Schema要求阶段必需字段，兼容入口仍使用已有协议。地图v2只允许缺省空辅助集合，实体与Claim仍必须存在且逐项验证；必需字段缺失、无效引文或越权ID不能补造。LOCAL_ONLY也约束歧义实体远程复核；保留本地结果待审核，不借用全局官方入口。远程复核成功次数如实计数，允许远程的模式按计划批次另计一次复核额度。

模型可保存可选默认温度，阶段留空时使用该模型值；模型未配置时采用原阶段默认值。显式阶段/任务温度仍优先，显式零重试仍保留；表单依据sources保留继承状态，不把系统展示默认值在无关保存中写成显式覆盖。生成请求的输出上限不超过实际模型Profile容量，降低模型上限后旧阶段较高值也不能越界。兼容入口的原始缓存/经验还含请求契约版本；商汤DeepSeek V4关闭思考使用入口专属reasoning_effort=none，官方入口仍用thinking.type=disabled。真实验证只记录实际返回用量，不根据同名模型推断参数协议。

输出达到上限且无正文、供应商报告正数reasoning_tokens时，返回AI_PROVIDER_REASONING_BUDGET并保留用量；不作为普通输入/正文截断进行二分，也不执行JSON修复或自动备用。正常正文被截断仍可自适应分块。该诊断表示本次配置的输出/思考预算不足，不把Model能力判成FAIL、不覆盖已有能力结果；总调用/Token/时间硬预算仍保留。

笔记分包保留256 Token基础余量，按每事实384 Token有界估算，结合输入容量形成初始包；真正正文截断再自适应拆分，阶段额度随叶子批次增长。首包Provider失败且无有效AI章节必须暂停，不能遍历大量熔断包并把事实提纲标成AI归纳成功；已有有效AI章节时保留混合结果和未归纳范围。历史确定性提纲可以显式续跑笔记阶段，沿用原模型身份并刷新该模型参数。

保护模式在等待资源/任务检查后、实际发起Provider调用前再次核对同入口间隔；预约槽位晚到不能压缩下一次实际发出的间隔。取消和阶段/任务墙钟在额外等待后仍复核，DIRECT不借用免费入口等待/熔断。手动测试/探测也关闭思考并按实际入口协议发送，使用独立的跨进程排队与本地完成后冷却。
