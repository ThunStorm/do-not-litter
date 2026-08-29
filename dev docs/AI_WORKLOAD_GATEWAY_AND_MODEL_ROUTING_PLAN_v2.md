# AI Workload Gateway、本地模型与远程模型统一路由实施方案

> 项目：`ThunStorm/do-not-litter`  
> 目标分支：`codex/mac-mini-implementation`  
> 用途：**Codex / Agent 可直接执行的架构与实施交接文档**  
> 日期：2026-08-28  
>
> 本文整合：视频 Pipeline Token 优化、本地 Ollama 模型选择、Qwen2.5:7B / Qwen3:8B 边界、多模态模型约束、每个 AI 阶段可选远程模型、专业领域 Domain Context，以及未来所有 AI 功能共用的减负基础设施。

---

## 0. Codex 执行原则

本文件作为此次改造的主实施依据。不要默认读取 `dev docs/COMPLETE_PROJECT_SPEC.md`。实施时优先读取：

1. 本文件；
2. `dev docs/CODEX_CONTEXT.md`；
3. 当前 Work Package 对应源码；
4. 必要时局部读取 `IMPLEMENTATION_STATUS.md` 与相关专项规范。

不要一次性完成全部 Work Package。每包完成 targeted tests 后再进入下一包。

---

# 1. 架构决策

后续 AI 架构统一采用：

```text
AI Workload Gateway
+ Capability-based Routing
+ Local-first / Remote-selectable Execution
+ Context Reduction
+ Schema & Evidence Validation
+ Domain Context
+ Cache / Budget / Audit
```

原则：

```text
确定性代码做能确定的事
本地模型做高频、便宜、可验证的“量”
远程强模型做困难、专业、高价值的“难”
用户始终可以对任意 AI 语义阶段选择远程模型
```

“默认本地优先”**不等于**“远程模型只能是 fallback”。

每个 AI 语义阶段必须支持：

```text
AUTO
LOCAL_ONLY
LOCAL_FIRST
REMOTE_FIRST
REMOTE_ONLY
```

并支持单次任务覆盖具体 Provider / Model。

非 AI 的确定性步骤，例如下载、hash、时间换算、坐标计算、黑帧检测，不要为了“每阶段可远程”而模型化。

---

# 2. 当前 Provider 层保留

当前项目已有：

```text
LLMProvider
OllamaProvider
OpenAICompatibleProvider
FallbackLLMProvider
ExternalCallAudit
```

当前 `OllamaProvider` 已使用：

```text
/api/chat
stream = false
keep_alive = 0
format = json
```

现有 Provider 层解决的是：

> 怎么调用某个模型。

本次新增的 `AI Workload Gateway` 解决：

> 是否需要模型、给多少上下文、选哪个模型、结果是否合格、是否升级远程、是否可复用、预算是否允许。

目标：

```text
Business Pipeline
      ↓
AI Workload Gateway
      ↓
Router / Reducer / Cache / Validator / Escalation
      ↓
Existing Provider Layer
      ↓
Ollama / OpenAI-compatible / Future Providers
```

不要把 HTTP Provider 逻辑重复搬入 Gateway。

---

# 3. 不再硬编码 Qwen3.5:9B

本项目业务代码不得硬编码：

```text
qwen3.5:9b
qwen3:8b
qwen2.5:7b
```

业务只声明 Capability。

模型由 Profile 配置：

```text
FAST_LOCAL_TEXT
MAIN_LOCAL_TEXT
LOCAL_VISION
REMOTE_FAST
REMOTE_STRONG
REMOTE_VISION
REMOTE_SPECIALIST
```

允许多个 Profile 指向同一个模型。例如在 16 GB Mac mini 上：

```text
FAST_LOCAL_TEXT = qwen2.5:7b
MAIN_LOCAL_TEXT = qwen2.5:7b
```

完全合法。

---

# 4. Qwen2.5:7B / Qwen3:8B 结论

## 4.1 标准型号都是文本模型

Ollama 标准：

```text
qwen2.5:7b
qwen3:8b
```

均为 **Text-only**。

它们不能直接处理图片。

视觉必须使用独立型号，例如：

```text
qwen2.5vl:7b
qwen3-vl:4b
qwen3-vl:8b
```

因此 ModelProfile 必须显式声明：

```python
modalities={"text"}
```

或：

```python
modalities={"text", "image"}
```

不能根据模型名称猜视觉能力。

## 4.2 当前 Ollama 参考体积

| 模型 | 当前 Ollama 参考体积 | 模态 | 推荐角色 |
|---|---:|---|---|
| `qwen2.5:7b` | ~4.7 GB | Text | Fast/Main Local |
| `qwen3:8b` | ~5.2 GB | Text | Main Local |
| `qwen2.5vl:7b` | ~6.0 GB | Text+Image | Local Vision |
| `qwen3-vl:4b` | ~3.3 GB | Text+Image | Lightweight Vision |
| `qwen3-vl:8b` | ~6.1 GB | Text+Image | Main Vision |

模型文件体积不等于运行峰值内存。还要考虑 KV cache、Metal buffer、上下文、Whisper、Backend 和 macOS 本身。

---

# 5. Qwen2.5:7B 的定位

优点：

- 比 Qwen3:8B 略轻；
- 成熟稳定；
- 中文能力好；
- Qwen2.5 官方强调 structured data / JSON 能力；
- 不存在默认 thinking 带来的额外推理时间；
- 很适合大量固定 Schema 的任务。

推荐 Capability：

```text
CLASSIFICATION
STRUCTURED_EXTRACTION
ENTITY_EXTRACTION
TRANSCRIPT_CORRECTION
LINK_CLASSIFICATION
LIGHT_SUMMARIZATION
DOMAIN_TERM_EXTRACTION
```

建议作为：

```text
FAST_LOCAL_TEXT
```

如果真实 benchmark 已满足质量，也可以直接作为 `MAIN_LOCAL_TEXT`，减少模型切换和内存波动。

---

# 6. Qwen3:8B 的定位

Qwen3 官方相较 Qwen2.5 强调：

- reasoning；
- instruction following；
- agent capability；
- multilingual；
- thinking / non-thinking 双模式。

更适合：

```text
较复杂结构化抽取
章节摘要
语义冲突判断
复杂实体关系
本地 Verify
Ambiguity Analysis
```

建议作为：

```text
MAIN_LOCAL_TEXT
```

但必须通过真实项目 benchmark，而不是只看排行榜。

---

# 7. Qwen3 Thinking 默认关闭

对于以下高频阶段默认使用 non-thinking：

```text
CLASSIFICATION
STRUCTURED_EXTRACTION
ENTITY_EXTRACTION
TRANSCRIPT_CORRECTION
CHUNK_SUMMARIZATION
JSON_REPAIR
```

原因：

- 更低延迟；
- 更少本地计算；
- 更容易控制输出；
- Pipeline 吞吐更重要。

只有：

```text
COMPLEX_VERIFY
CONFLICT_RESOLUTION
COMPLEX_REASONING
AMBIGUITY_ANALYSIS
```

才允许 Router 根据策略开启 thinking。

thinking 必须：

```text
显式启用
有输出预算
有 Audit
```

不能全局默认开启。

---

# 8. Mac mini 16 GB 推荐部署

## 稳定优先方案

```text
FAST_LOCAL_TEXT = qwen2.5:7b
MAIN_LOCAL_TEXT = qwen2.5:7b 或 qwen3:8b
LOCAL_VISION = 按需加载，不常驻
REMOTE_STRONG = 用户配置的 OpenAI-compatible 模型
```

如果频繁切换两个文本模型造成加载时间或内存压力，则只保留一个 7B/8B 文本模型。

不要为了理论上多一个“Main Model”牺牲稳定性。

---

# 9. 本地模型最低要求

任何本地模型进入 Router 前必须通过 Capability Probe。

最低要求：

### 9.1 API

支持：

```text
Ollama /api/chat
```

未来也允许 localhost OpenAI-compatible endpoint。

### 9.2 中文

必须测试：

- 中文指令跟随；
- 中文实体；
- 中英混合；
- 地名/人名；
- 数字日期；
- 专有名词保持。

### 9.3 Structured Output

最低：

```text
JSON object
```

推荐：

```text
JSON Schema constrained output
```

Profile 记录：

```python
supports_json_mode
supports_json_schema
```

### 9.4 Context

项目自己控制工作窗口，不追求塞满模型标称上下文。

建议：

```text
最低：16K
推荐：32K+
```

即使模型标称 128K / 256K，16 GB Mac mini 也不应默认使用超长上下文。

### 9.5 Output Limit

Provider 必须支持或模拟：

```text
max_output_tokens
```

### 9.6 可重复性

Benchmark 至少记录：

```text
schema_pass_rate
field_consistency
evidence_consistency
```

### 9.7 模态

明确：

```text
text
image
```

视觉任务不能调度到 text-only 模型。

---

# 10. 本地模型的限制

本地模型不能被当成知识库。

以下内容尤其容易超出本地 7B/8B 的知识和辨识能力：

- 医学；
- 法律；
- 航空；
- 小众设备；
- 地方历史；
- 方言；
- 新政策；
- 行业黑话；
- 游戏/动漫小众设定；
- 罕见地名与专有名词。

正确做法：

```text
Domain Context
+ Relevant Evidence
+ Local/Remote Model
```

而不是简单：

```text
换更大模型
```

模型不知道时允许输出：

```text
UNKNOWN
```

禁止无证据补全事实。

---

# 11. 多模态策略

视觉 Capability 独立：

```text
VISION
DOCUMENT_VISION
SCREENSHOT_UNDERSTANDING
GUI_UNDERSTANDING
VISUAL_ENTITY_EXTRACTION
```

Mac mini 16 GB 建议：

```text
轻量图片初筛
→ qwen3-vl:4b 等较轻视觉模型

复杂文档 / 专业图 / 高质量视觉
→ REMOTE_VISION

用户要求最高质量
→ REMOTE_ONLY
```

视频不要把大量帧直接送视觉模型。

继续：

```text
Metadata + Note + Transcript time range
→ 确定候选时间码
→ 确定性抽帧
→ 少量候选帧
→ Vision Model
```

---

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

# 28. Transcript Correction 改造

## 28.1 Quality Gate

新增 deterministic：

```text
TranscriptQualityGate
```

检测：

```text
低 ASR confidence
明显重复
异常字符
断句异常
专有名词可疑
常见 ASR 错误模式
用户指定重点
```

## 28.2 平台字幕

平台已有字幕默认：

```text
PASS_THROUGH
```

只处理 Quality Gate candidate。

用户仍可：

```text
TRANSCRIPT_CORRECTION = REMOTE_ONLY
force_full_correction = true
```

进行高质量重跑。

## 28.3 Delta Output

模型只返回变化：

```json
{
  "changes": [
    {
      "segment_id": "xxx",
      "corrected_text": "...",
      "confidence": 0.92,
      "reason": "..."
    }
  ]
}
```

未出现的 Segment：

```text
UNCHANGED
```

不再让模型把全文复述一遍。

## 28.4 模型

通用：

```text
qwen2.5:7b
或
qwen3:8b non-thinking
```

专业字幕：

```text
Domain Pack
+ REMOTE_FIRST / REMOTE_ONLY
```

---

# 29. Correction JSON 失败

禁止默认：

```text
大 Batch JSON 错
→ 全文再次请求
→ 递归二分
→ 两半继续付费
```

新顺序：

```text
parse
→ local tolerant repair
→ schema validation
→ 小型 JSON-only repair
→ REVIEW / Escalation
```

只有明确：

```text
context length exceeded
request too large
```

才允许拆 chunk。

---

# 30. 视频 Note 改 Map → Reduce

```text
Transcript Chunks
→ Local Map
→ SectionFacts[]
→ Global Reduce
→ Final Note
```

Local Map 一次输出：

```json
{
  "summary": "...",
  "key_points": [],
  "places": [],
  "people": [],
  "warnings": [],
  "opinions": [],
  "prices": [],
  "domain_terms": [],
  "segment_ids": []
}
```

一次调用同时承担：

```text
chunk summary
place candidate extraction
entity extraction
evidence anchoring
```

---

# 31. Global Reduce

BALANCED：

```text
SectionFacts[]
→ Local
→ Validate
→ PASS
```

QUALITY：

```text
SectionFacts[]
+ Necessary Evidence
→ REMOTE_STRONG
→ Final Note
```

默认不要把完整 Transcript 再发远程。

只有用户显式：

```text
force_full_remote_context
```

才允许全量远程重读。

---

# 32. Place Extraction

默认不再单独读取 Transcript 前 12K。

改为：

```text
Local Map
→ place_candidates per chunk
→ deterministic aggregate
→ resolve mentions
```

保留 `EXTRACT_TRAVEL_FACTS` Pipeline Step 名称兼容 UI / replay。

默认内部不调用 LLM。

但用户如果指定：

```text
EXTRACT_TRAVEL_FACTS = REMOTE_ONLY
```

则允许远程重新提取。

这可以用于罕见地点、地方历史、专业 POI 等场景。

---

# 33. Stage Replay

统一支持：

```python
replay_stage(
    job_id,
    stage,
    execution_override=...,
)
```

例如：

```text
只用远程重跑字幕纠错
只用远程重跑地点抽取
只用远程重跑最终笔记
```

不要重复下载、ASR、抽帧等无关阶段。

---

# 34. 远程 Provider Registry

不要只存在一个“云模型”。

支持角色：

```text
REMOTE_FAST
REMOTE_STRONG
REMOTE_VISION
REMOTE_SPECIALIST
```

兼容：

```text
OpenAI-compatible
DeepSeek
MiMo
其他未来 Provider
```

业务禁止：

```python
if provider == "deepseek":
```

---

# 35. Validation

统一：

```text
Schema
+ Evidence
+ Semantic checks
```

事实型输出无 Evidence：

```text
UNKNOWN / reject / escalation
```

Confidence 不只相信模型自报，应综合：

```text
schema completeness
evidence coverage
domain match
cross-field consistency
deterministic checks
```

Cross-model verification 仅用于：

```text
高价值字段
冲突字段
低置信
QUALITY
```

不要默认所有内容双跑，否则会抵消 Token 优化。

---

# 36. Structured Output Provider 改造

当前 Ollama 只有：

```text
format = "json"
```

新增 Provider 方法：

```python
generate_structured(
    messages,
    model,
    schema,
    options,
)
```

支持 JSON Schema 的 Provider：

```text
直接使用 Schema constraint
```

只支持 JSON object：

```text
JSON mode
+ schema prompt
+ Pydantic validate
```

不具备可靠 Structured Output 的模型不得用于核心抽取 Capability。

---

# 37. Provider Options

新增：

```python
AIProviderRequestOptions(
    max_output_tokens,
    temperature,
    thinking,
    json_schema,
)
```

Thinking Policy：

```text
CLASSIFICATION          OFF
STRUCTURED_EXTRACTION   OFF
ENTITY_EXTRACTION       OFF
TRANSCRIPT_CORRECTION   OFF
CHUNK_SUMMARIZATION     OFF
GLOBAL_SYNTHESIS        OPTIONAL
VERIFY                  OPTIONAL
CONFLICT_RESOLUTION     AUTO/ON
```

---

# 38. Audit / Usage API

扩展现有 `ExternalCallAudit` 或增加统一 execution view。

每次记录：

```text
job
stage
capability
mode
provider
model
local/remote
input chars
input tokens
output tokens
cached tokens
cache hit
attempt
retry
escalated
escalation reason
domain
domain pack version
schema pass
evidence pass
duration
```

新增：

```text
GET /api/jobs/{job_id}/ai-usage
```

返回：

```text
total
local
remote
by_stage
by_model
cache
escalations
```

---

# 39. UI

Settings：

```text
AI Quality
├─ Economy
├─ Balanced
├─ Quality
├─ Local Private
└─ Custom
```

Custom：

| Stage | Mode | Local Model | Remote Model | Domain |
|---|---|---|---|---|
| Transcript Correction | Local First | qwen2.5:7b | Strong #1 | Auto |
| Note Chunk | Local First | qwen3:8b | Strong #1 | Auto |
| Final Note | Remote First | qwen3:8b | Strong #1 | Auto |
| Place Extraction | Local First | qwen2.5:7b | Strong #1 | Travel |

Dropdown 必须按 Capability 过滤。

Vision 阶段不能列 text-only 模型。

创建 Job 时允许覆盖 Preset / Stage。

---

# 40. Benchmark

新增：

```text
scripts/benchmark_ai_profiles.py
```

不要只看公开榜单决定默认模型。

真实 Dataset 至少：

### Transcript
- 正常平台字幕；
- ASR 错字；
- 中英混合；
- 地名；
- 人名；
- 数字；
- 专业术语。

### Structured Extraction
- 招聘；
- 旅行；
- 通用网页；
- 专业材料。

### Note
- 10 / 30 / 60 分钟内容。

### Domain
- 通识；
- 小众专业；
- supplied glossary；
- remote rerun。

指标：

```text
schema_pass_rate
evidence_coverage
field_accuracy
correction_precision
correction_recall
unchanged_preservation
entity_precision
entity_recall
summary_coverage
hallucination_rate
latency
peak_memory
local tokens
remote tokens
escalation_rate
```

模型选择同时看：

```text
quality / second
quality / GB
remote tokens saved
failure rate
```

---

# 41. 初始模型决策

Benchmark 前暂定：

```text
qwen2.5:7b → FAST_LOCAL_TEXT
qwen3:8b   → MAIN_LOCAL_TEXT
```

但不是最终硬要求。

如果真实数据表明：

```text
qwen2.5:7b 已满足 MAIN 质量目标
```

则优先：

```text
FAST_LOCAL_TEXT = MAIN_LOCAL_TEXT = qwen2.5:7b
```

以稳定、低内存和少切换为优先。

---


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

# 41J. 单次任务覆盖

创建 Job 时允许：

```text
Use Saved Settings
Economy
Balanced
Quality
Local Only
Custom
```

Custom 下允许只覆盖某几个 Stage。

没有覆盖的 Stage 继续继承 Saved Stage Policy。

例如：

```text
本次视频：
Transcript Correction → Local
Note Chunk → Local
Final Note → Remote Strong
Place Extraction → Remote Specialist
```

无需复制整套全局配置。

---

# 41K. Stage Policy API

建议新增：

```text
GET    /api/ai/stage-policies
GET    /api/ai/stage-policies/{stage}
PUT    /api/ai/stage-policies/{stage}
DELETE /api/ai/stage-policies/{stage}
```

获取可配置参数：

```text
GET /api/ai/stages
```

返回：

```json
{
  "stage": "TRANSCRIPT_CORRECTION",
  "capability": "TRANSCRIPT_CORRECTION",
  "parameter_spec": {},
  "resolved_default": {}
}
```

Job 创建接口支持：

```json
{
  "ai_overrides": {
    "FINAL_NOTE": {
      "execution_mode": "REMOTE_ONLY",
      "remote_model": "xxx",
      "temperature": 0.4
    }
  }
}
```

---

# 41L. Resolved Policy 必须进入 Audit

每次调用 Audit 不只记录最终 model。

还应记录本次生效配置摘要：

```text
policy_source
execution_mode
provider
model
temperature
thinking
max_input_tokens
max_output_tokens
timeout
retry_count
confidence_threshold
escalation_threshold
domain_pack_version
```

不要记录 API Key。

这样以后才能判断：

```text
为什么这个 Stage Token 很高
为什么本次用了远程
为什么同一个 Stage 两次质量不同
```

---

# 41M. Stage 参数与 Cache Key

影响输出语义的参数必须进入 Cache Key。

至少：

```text
model
temperature
thinking
max_output_tokens
prompt_version
schema_version
domain_pack_version
stage semantic parameters
```

纯运行参数，例如：

```text
timeout
retry_count
```

通常不需要进入内容 Cache Key。

Codex 实现时应明确区分：

```text
semantic cache inputs
runtime-only settings
```

---

# 41N. Stage 参数版本化

保存：

```text
stage_policy_version
```

AIResult / Audit 记录：

```text
stage_policy_version
```

这样以后修改默认参数时可以追踪旧结果。

---

# 41O. Stage 参数导入导出

建议为未来维护预留：

```text
Export AI Stage Policies
Import AI Stage Policies
Reset Stage to Default
Reset All AI Settings
```

第一版至少实现：

```text
Reset Stage to Default
```

方便 benchmark 后统一调整。

---

# 41P. 新增 Work Package — Stage Policy & Parameter Control

在原实施顺序中新增独立 Work Package。

建议放在 Routing 之后、Observability 之前：

```text
WP1 Gateway Skeleton
WP2 Model Registry
WP3 Routing / Remote Override
WP4 Stage Policy & Parameter Control
WP5 Observability
WP6 Transcript Delta
WP7 Map/Reduce
WP8 Place Aggregation
WP9 Cache/Budget
WP10 Domain Context
WP11 Vision
```

## WP4 任务

1. `AIStagePolicy`
2. `ResolvedAIStagePolicy`
3. Config Resolver
4. StageParameterSpec
5. Provider Capability Validation
6. Settings persistence
7. Stage Policy API
8. Job-level Stage Override
9. Basic / Advanced UI
10. Audit policy snapshot
11. Cache semantic parameter integration
12. tests

## WP4 验收

必须通过：

```text
不同 Stage 可配置不同模型
不同 Stage 可配置不同 temperature
不同 Stage 可配置不同 max_output_tokens
Qwen3 thinking 可按 Stage 控制
不支持 thinking 的模型不能保存 thinking=true
Vision Stage 不能选择 text-only model
Job override 高于 saved stage policy
Stage runtime override 高于 Job preset
未覆盖参数正确继承
Reset Stage 恢复默认
Audit 能看到最终 resolved policy
```

---

# 41Q. 参数配置的边界

即使用户可以调高级参数，也必须设置安全范围。

例如：

```text
temperature: 0.0 ~ 2.0
retry_count: 0 ~ 3
timeout_seconds: 10 ~ 600
neighbor_segments: 0 ~ 10
```

`max_input_tokens` 不能超过：

```text
min(
  model.context_window - reserved_output,
  system_global_limit,
  local_resource_limit
)
```

本地 Mac mini 还要经过 Resource Manager 的可用预算裁剪。

因此用户填写：

```text
max_input_tokens = 100000
```

不代表实际会直接使用 100000。

最终：

```text
requested policy
↓
capability validation
↓
resource clamp
↓
ResolvedAIStagePolicy
```

并在 UI / Audit 显示实际生效值。

---

# 41R. 参数模板

允许提供 Stage Template：

```text
Economy
Balanced
Quality
Custom
```

但 Template 只是预填 Stage Policy。

不是隐藏不可覆盖的黑箱。

例如：

```text
QUALITY / FINAL_NOTE
```

可以预填：

```text
REMOTE_FIRST
temperature = 0.4
max_output_tokens = 5000
```

用户仍可继续修改。

---

# 41S. 核心验收语句

实现完成后，系统必须满足：

> 同一条 Pipeline 中，用户可以让字幕纠错由 `qwen2.5:7b` 以低 temperature、本地 non-thinking 执行；让 Note Chunk 由 `qwen3:8b` 本地执行；让 Final Note 使用指定远程强模型并单独设置更高输出预算；让专业 Place Extraction 使用另一个远程 Specialist + Domain Pack。所有 Stage 的配置互不污染，并可被单次 Job 覆盖。


# 42. Work Packages

> 注意：因新增 Stage-level Model & Parameter Policy，Work Package 总数由 10 个调整为 11 个。

## WP1 — Gateway Skeleton

- 新建 `ai/` 模块；
- 定义 Capability / Mode / Request / Result / ModelProfile；
- 包装现有 Provider；
- 第一版行为先等价当前逻辑；
- 不改变业务结果。

## WP2 — Model Registry + Probe

- Profile Registry；
- Ollama / Remote Profile；
- Capability Probe；
- text / vision 区分；
- thinking；
- schema；
- Settings API。

预置候选：

```text
qwen2.5:7b
qwen3:8b
```

不得要求已经安装。

## WP3 — Routing + Per-stage Remote Override

实现：

```text
AUTO
LOCAL_ONLY
LOCAL_FIRST
REMOTE_FIRST
REMOTE_ONLY
```

先迁移：

```text
TRANSCRIPT_CORRECTION
VIDEO_NOTE_SUMMARY
TRAVEL_PLACE_EXTRACTION
```

## WP4 — Stage Policy & Parameter Control

- 实现 `AIStagePolicy` / `ResolvedAIStagePolicy`；
- 实现配置继承 Resolver；
- 实现 `StageParameterSpec` 参数白名单；
- 实现 Provider / Model Capability Validation；
- 支持每 Stage 独立 Local / Remote Model；
- 支持每 Stage 独立 generation/runtime/quality/context 参数；
- Settings 持久化；
- Stage Policy API；
- Job-level 与 Stage-level override；
- Basic / Advanced UI；
- Audit 记录 resolved policy；
- Cache Key 纳入语义参数；
- 完整继承与边界测试。

## WP5 — Observability

- `/api/jobs/{job_id}/ai-usage`
- stage / model / local / remote；
- retry；
- escalation；
- cache；
- UI。

## WP6 — Transcript Delta

- Quality Gate；
- 平台字幕 pass-through；
- suspicious segment selection；
- neighbor context；
- changed-only schema；
- 去除默认递归二分；
- remote override。

## WP7 — Note Map/Reduce

- SectionFacts；
- chunk local map；
- final local/remote reduce。

## WP8 — Place Aggregation

- Map 阶段产出 places；
- `EXTRACT_TRAVEL_FACTS` 默认 deterministic aggregate；
- REMOTE_ONLY 可重新处理。

## WP9 — Cache + Budget

- exact AI cache；
- force regenerate；
- job/stage budget。

## WP10 — Domain Context

第一版：

```text
glossary
aliases
rules
examples
```

预留 Retrieval，不立即引入复杂向量库。

## WP11 — Vision

有实际视觉需求再做，不阻塞文本 Token 优化。

---

# 43. 测试要求

Routing：

```text
LOCAL_ONLY 永不外发
REMOTE_ONLY 不调本地
LOCAL_FIRST 本地成功不远程
LOCAL_FIRST validation fail 可升级
REMOTE_FIRST 优先远程
Provider override 生效
Model override 生效
```

Privacy：

```text
LOCAL_ONLY
```

必须高于 Router 任何自动策略。

Capability：

```text
text-only model
```

不得进入 Vision。

Qwen3：

```text
CLASSIFICATION
```

默认 thinking off。

Correction：

```text
非 candidate Segment 不变
Segment ID 不丢
时间码不改
```

Cache：

```text
相同输入/版本 → no second provider call
force regenerate → provider called
```

Domain：

加入 glossary 后应提高专业实体识别质量。

---

# 44. Regression Guard

必须保持：

```text
Job 状态机
replay
cancel
ExternalCallAudit
NoteVersion
Evidence
Settings
Provider credential handling
Sensitive / LOCAL_ONLY
Mac mini Ollama unload contract
```

---

# 45. 禁止的实现方式

不要：

1. 在业务代码散落 `qwen2.5:7b` / `qwen3:8b`。
2. 把所有任务强制本地。
3. 只有 HTTP 失败才允许远程。
4. 专业内容只通过换更大模型解决。
5. 所有阶段默认双模型验证。
6. 用超长 Context 代替分块。
7. 默认启用 Qwen3 thinking。
8. 用标准 `qwen3:8b` / `qwen2.5:7b` 处理图片。
9. 为“每阶段可远程”把下载、hash、坐标等确定性步骤模型化。
10. 为了省 API Token 而降低用户主动选择高质量远程处理的能力。

---

# 46. 最终架构

```text
                         User / Job Policy
                                │
                                ▼
┌──────────────────────────────────────────────────────────────┐
│                     AI Workload Gateway                      │
│                                                              │
│ Capability                                                   │
│     ↓                                                        │
│ Domain Detection → Domain Context / Retrieval                │
│     ↓                                                        │
│ Context Reducer / Candidate Selection                        │
│     ↓                                                        │
│ Exact Cache                                                  │
│     ↓                                                        │
│ Policy Resolver                                              │
│ AUTO / LOCAL_ONLY / LOCAL_FIRST / REMOTE_FIRST / REMOTE_ONLY │
│     ↓                                                        │
│ Capability Router                                            │
└──────────────┬──────────────────────────────┬────────────────┘
               │                              │
               ▼                              ▼
       LOCAL MODEL                     REMOTE MODEL
 qwen2.5:7b / qwen3:8b              Strong / Specialist
               │                              │
               └──────────────┬───────────────┘
                              ▼
                   Schema + Evidence
                       Validation
                              │
                    PASS ─────┴──── FAIL
                      │               │
                      │          Escalation
                      └───────┬───────┘
                              ▼
                           AIResult
                              │
                         Cache / Audit
```

视频：

```text
Subtitle / ASR
→ Transcript Quality Gate
→ suspicious segments only
→ Local Correction
→ optional Remote Correction
→ Corrected Transcript
→ Local Map
→ SectionFacts
→ Local/Remote Global Reduce
→ Final Note
→ deterministic Place Aggregate
→ POI Resolution
```

---

# 47. 验收目标

平台字幕视频：

```text
远程 token 降低 >= 50%
目标 >= 70%
```

前提：

```text
Note coverage 不明显下降
Place recall 不明显下降
Evidence binding 不下降
```

ASR 视频：

```text
远程 token 降低目标 >= 30%
```

通用内容：

```text
LOCAL_FIRST 多数任务无需远程即可 PASS
```

专业内容：

```text
REMOTE_ONLY + Domain Pack
```

必须允许只重跑目标 AI Stage，而不是整个 Pipeline。

---

# 48. Codex 最终实施顺序

严格按：

```text
WP1 Gateway Skeleton
→ WP2 Model Registry
→ WP3 Routing / Remote Override
→ WP4 Stage Policy & Parameter Control
→ WP5 Observability
→ WP6 Transcript Delta
→ WP7 Map/Reduce
→ WP8 Place Aggregation
→ WP9 Cache/Budget
→ WP10 Domain Context
→ WP11 Vision
```

每包：

```text
搜索当前源码
→ 只读必要上下文
→ 小范围实现
→ targeted tests
→ 更新状态文档
→ 下一包
```

如果当前分支代码与本文描述有变化，以当前源码为准，但不得改变以下核心决策：

```text
Capability-based
Provider-independent
Per-stage remote selectable
Per-stage model and parameter configurable
Hierarchical policy inheritance and runtime override
Local-first optional
Schema/Evidence validation
Domain Context
Shared context reduction/cache/budget/audit
```

---

# 49. 外部模型信息核对说明

制定本文时核对的当前公开信息：

- Ollama `qwen2.5`: `qwen2.5:7b` 为 Text，当前约 4.7 GB。
- Ollama `qwen3`: `qwen3:8b` 为 Text，当前约 5.2 GB。
- Qwen 官方 Qwen3-8B Model Card：支持 thinking / non-thinking，并强调 reasoning、instruction-following、agent、multilingual 提升。
- Ollama `qwen2.5vl`: `qwen2.5vl:7b` 为 Text+Image，当前约 6.0 GB。
- Ollama `qwen3-vl`: `qwen3-vl:4b` 当前约 3.3 GB；`qwen3-vl:8b` 当前约 6.1 GB，均为 Text+Image。
- Qwen2.5-7B-Instruct 官方 Model Card 强调 structured data、JSON、multilingual 与长上下文能力。

模型库会变化，因此具体体积、Context 和 Capability 必须由 `Model Registry + Capability Probe` 管理，不在业务 Processor 写死。

---

# 50. 一句话最终决策

> **业务层只声明 Capability、Evidence、Quality、Privacy 与 Domain；AI Workload Gateway 负责用确定性预处理、本地模型、领域上下文、缓存和选择性远程升级，以最少资源获得满足质量要求的结果，同时用户可对任意 AI 语义阶段强制使用远程强模型。**
