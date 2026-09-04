# Gateway、路由与公共上下文

> 来源：ai-gateway/AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md，原章节 12–27（正文保留，2026-09-03 分篇）。返回 [主题索引](AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md)。本篇是契约/规划，不是已实施清单；当前结论见 [实施状态](../IMPLEMENTATION_STATUS.md)，安全与回归见 [冻结清单](../REGRESSION_AND_CHANGE_GUARD.md)。裸文档路径均以 dev docs/ 为基准。只读取命中章节及其必要约束。

# 12. 所有 AI 阶段都可选远程

新增：

```python
class AIExecutionMode(str, Enum):
    AUTO = "AUTO"
    LOCAL_ONLY = "LOCAL_ONLY"
    LOCAL_FIRST = "LOCAL_FIRST"
    REMOTE_FIRST = "REMOTE_FIRST"
    REMOTE_ONLY = "REMOTE_ONLY"
```

“手动指定模型”不要再作为 `MANUAL` mode，而是：

```text
provider_override
model_override
```

## AUTO

综合：

```text
capability
quality
domain
privacy
local load
benchmark
model availability
validation
```

自动选择。

## LOCAL_ONLY

绝不外发。失败则 FAIL/PARTIAL，不允许偷偷升级远程。

## LOCAL_FIRST

```text
Local
→ Validate
→ PASS
或
→ Remote Escalation
```

## REMOTE_FIRST

优先质量，可配置远程不可用时是否 Local fallback。

## REMOTE_ONLY

强制远程。用于专业、高价值、用户主动高质量重跑等。

---

# 13. Quality Preset

普通用户不需要逐 Stage 调参数。

提供：

```text
ECONOMY
BALANCED
QUALITY
LOCAL_PRIVATE
CUSTOM
```

建议：

```text
ECONOMY
→ LOCAL_FIRST
→ 仅 validation fail 升级

BALANCED
→ AUTO

QUALITY
→ 重要语义阶段 REMOTE_FIRST

LOCAL_PRIVATE
→ 所有 AI Stage LOCAL_ONLY

CUSTOM
→ 逐 Stage 配置
```

创建任务时允许单次覆盖。

优先级：

```text
Single-run Stage Override
> Single-run Preset
> Saved Stage Policy
> Global Preset
> System Default
```

---

# 14. AI Workload Gateway

建议新增：

```text
backend/src/zhijian/ai/
├── gateway.py
├── schemas.py
├── capabilities.py
├── model_registry.py
├── router.py
├── context_reducer.py
├── domain_context.py
├── validator.py
├── escalation.py
├── cache.py
├── budget.py
├── resource_manager.py
└── audit.py
```

Provider HTTP 实现继续留在现有 `providers/`。

---

# 15. Capability Enum

第一版统一：

```text
CLASSIFICATION
STRUCTURED_EXTRACTION
ENTITY_EXTRACTION
TRANSCRIPT_CORRECTION
CHUNK_SUMMARIZATION
GLOBAL_SYNTHESIS
VERIFY
CONFLICT_RESOLUTION
DOMAIN_TERM_EXTRACTION
DOMAIN_REASONING
VISION
DOCUMENT_VISION
SCREENSHOT_UNDERSTANDING
```

兼容并整理现有文档中的：

```text
LONG_CONTEXT
SEMANTIC_MATCH
SCREENSHOT_PLANNING
NOTE_TOC_AND_SECTION_SUMMARY
```

不要同时保留多套 role string。

---

# 16. AIRequest

建议：

```python
class AIRequest(BaseModel):
    capability: AICapability
    stage: str

    input_text: str | None = None
    evidence_segments: list[EvidenceSegment] = []

    output_schema: dict | None = None

    quality_target: AIQualityTarget = AIQualityTarget.BALANCED
    execution_mode: AIExecutionMode | None = None

    provider_override: str | None = None
    model_override: str | None = None

    domain: str | None = None
    domain_pack_ids: list[str] = []

    privacy: AIPrivacyPolicy = AIPrivacyPolicy.NORMAL

    max_input_tokens: int | None = None
    max_output_tokens: int | None = None

    cache_policy: AICachePolicy = AICachePolicy.USE
    force_regenerate: bool = False

    allow_escalation: bool = True
```

---

# 17. AIResult

```python
class AIResult(BaseModel):
    data: Any

    provider: str
    model: str
    capability: AICapability

    execution_route: str
    local_attempted: bool
    remote_attempted: bool
    escalated: bool

    validation_status: str
    confidence: float | None
    evidence_ids: list[str]

    cache_hit: bool

    input_tokens: int | None
    output_tokens: int | None
    cached_tokens: int | None

    duration_ms: int

    prompt_version: str
    schema_version: str
    parser_version: str

    escalation_reasons: list[str]
```

---

# 18. ModelProfile

```python
class ModelProfile(BaseModel):
    id: str
    provider: str
    model: str

    location: Literal["LOCAL", "REMOTE"]
    modalities: set[str]
    capabilities: set[AICapability]

    supports_json_mode: bool
    supports_json_schema: bool
    supports_thinking: bool
    supports_tools: bool

    context_window: int
    recommended_working_context: int
    max_output_tokens: int

    quality_tier: Literal["FAST", "MAIN", "STRONG", "SPECIALIST"]
    specialties: set[str] = set()

    enabled: bool = True
```

---

# 19. Capability Probe

新增模型首次保存/测试时至少测试：

```text
plain text
Chinese instruction
JSON output
JSON Schema（如声明支持）
Evidence ID echo
long-ish context
vision（如声明支持）
thinking switch（如声明支持）
```

Capability 分别记录 PASS/FAIL。

例如：

```text
qwenX:
CLASSIFICATION = PASS
STRUCTURED_EXTRACTION = PASS
VISION = FAIL
```

仍可作为文本模型。

---

# 20. Router 从 Fallback 升级为 Escalation

现有 Provider fallback 继续处理：

```text
HTTP error
timeout
429
empty response
```

业务 Gateway 增加 Semantic Escalation。

触发原因：

```text
SCHEMA_FAILED
EVIDENCE_MISSING
LOW_CONFIDENCE
DOMAIN_UNKNOWN
DOMAIN_AMBIGUOUS
ENTITY_CONFLICT
OUTPUT_INCOMPLETE
USER_FORCED_REMOTE
QUALITY_PRESET
LOCAL_MODEL_UNAVAILABLE
```

远程不是只在 HTTP 失败后才出现。

---

# 21. 两种远程升级

## VERIFY_DRAFT

远程收到：

```text
relevant evidence
+ local draft
+ validation issue
```

适合字段/实体验证。

## REPROCESS_EVIDENCE

远程重新看：

```text
relevant raw evidence
+ Domain Context
+ schema
```

不给本地答案强锚定。

适合：

```text
专业材料
高价值判断
QUALITY
REMOTE_ONLY
事实冲突
```

---

# 22. Domain Context 公共模块

新增：

```text
DomainContextProvider
```

定义 Domain Pack：

```python
class DomainPack(BaseModel):
    id: str
    name: str
    version: str

    glossary: dict[str, str]
    aliases: dict[str, list[str]]
    rules: list[str]
    examples: list[DomainExample]

    retrieval_sources: list[str]
    prompt_supplement: str | None

    allowed_capabilities: set[AICapability]
```

示例：

```text
travel-cn
aviation
recruitment
medical
legal
photography
local-history
```

航空包可包含：

```text
ICAO / IATA
机场别名
航司简称
机型代码
共享航班
经停 / 联程
专业缩写
```

本地和远程使用同一 Domain Context。

---

# 23. RAG 以后统一接 Domain Context

未来接知识库时，不要每个业务重写 RAG。

统一：

```text
AIRequest
→ DomainContextProvider
→ Retrieve Relevant References
→ Context Reducer
→ Model
```

只发送当前任务相关资料，不发送整个知识库。

第一版 Domain Pack 可以只做：

```text
glossary
aliases
rules
examples
```

不要立即引入复杂向量数据库。

---

# 24. Context Reducer

公共职责：

```text
去重
规范化
Segment 选择
Evidence 选择
邻近上下文
Token 预算
Chunk
历史结果压缩
```

关键原则：

> 模型调用前先决定“哪些内容值得送模型”。

例如 Transcript：

```text
500 Segments
→ Deterministic Quality Gate
→ 35 suspicious segments
→ 35 个目标 + 少量邻近 context
→ Model
```

---

# 25. Cache

所有 AI Stage 支持统一 exact cache。

Cache Key 至少：

```text
capability
input_hash
evidence_hash
prompt_version
schema_version
parser_version
domain_pack_version
provider
model
relevant generation options
```

用户：

```text
force_regenerate=true
```

则跳过 cache，并保留 previous result reference。

---

# 26. Budget

统一叫 `AI Budget`，因为本地也有资源成本。

建议：

```text
max_model_attempts_per_job
max_remote_prompt_tokens_per_job
max_remote_completion_tokens_per_job
max_local_prompt_tokens_per_job
max_local_completion_tokens_per_job
max_ai_wall_time_seconds_per_job
```

不得无限 retry。

---

# 27. LocalAIResourceManager

Mac mini 16 GB 必须有：

```text
gpu_heavy_concurrency = 1
```

Resource Manager 统一处理：

```text
ASR / Text LLM / Vision LLM 排他
模型切换
取消
内存压力
任务结束释放
```

当前 `keep_alive: 0` 第一阶段继续保持。

不要把改长 keep_alive 混入 Token 优化。

未来若优化模型重复加载，单独 benchmark：

```text
peak memory
ASR coexistence
cancel
unload
latency
```

再决定是否做 job-scoped residency。

---
