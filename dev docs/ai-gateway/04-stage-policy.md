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
