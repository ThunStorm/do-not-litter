# 模型级可靠调用机制实施计划

> 项目：`ThunStorm/do-not-litter`
> 分支：`codex/mac-mini-implementation`
> 基线：当前分支已存在 AI Gateway、FallbackLLMProvider、模型 Profile、Stage Policy、AI Cache 与 ExternalCallAudit。
> 目标：为 OpenRouter Free、SenseNova 等免费/易限流模型增加可选的可靠调用机制，同时确保稳定付费模型可以保持低延迟直连，不因统一重试、排队或限速策略降低效率。

---

## 1. 背景与当前问题

当前项目已经具备以下基础能力：

- `AIWorkloadGateway` 统一执行 AI 调用并接入缓存、预算与审计。
- `FallbackLLMProvider` 已有基础主备模型、简单重试、请求间隔与 429 cooldown。
- `ModelProfileConfig` 已保存 provider、model、timeout、request interval、JSON 能力、context window 等模型能力。
- Stage Policy 已支持按阶段指定模型、timeout、retry_count 等。
- `parse_model_json()` 已能处理 Markdown JSON fence、截取 `{...}`、删除尾逗号等简单 JSON 修复。
- AI Cache 已能避免相同请求重复调用远端模型。

但当前在 OpenRouter Free / SenseNova 等模型上存在明显不稳定现象：

1. 经常出现 HTTP `429`。
2. 可能出现 HTTP `200`，但业务仍失败。
3. 出现 `模型没有返回 JSON 对象`。
4. 免费模型经常返回解释文字、Markdown、截断 JSON、错误 Schema。
5. 当前大量 AI Stage 默认 `retry_count=0`。
6. `FallbackLLMProvider` 对长 Prompt 存在 `>= 8000 chars` 时禁用 retry 的行为，与视频工作流的 8000/12000 字符 chunk 冲突。
7. 当前 429 的可重试判断较依赖 `Retry-After`，没有该 Header 时可能直接失败。
8. Primary/Fallback 如果使用相同 endpoint，当前逻辑会阻止 fallback，不利于 OpenRouter 同 endpoint 多模型切换。
9. 现有重试逻辑主要围绕 HTTP/网络错误，没有把“HTTP 200 但输出非法”视为独立的可恢复错误。
10. 如果对所有模型统一加入排队、等待、指数退避，将影响稳定付费模型的正常响应速度。

---

# 2. 核心设计原则

## 2.1 可靠性策略必须绑定 Model Profile，而不是 Provider

不要实现：

```text
OpenRouter = 全部进入强限速模式
SenseNova = 全部进入强限速模式
```

应实现：

```text
OpenRouter / xxx:free        -> FREE_TIER
OpenRouter / paid-model      -> DIRECT / STANDARD
SenseNova / free model       -> GUARDED
DeepSeek paid                -> DIRECT / STANDARD
Ollama local                 -> DIRECT
```

即：

> **每个模型 Profile 单独决定是否启用可靠调用机制。**

---

## 2.2 稳定付费模型正常路径不得引入人为等待

`DIRECT` 模式必须满足：

```text
业务请求
  ↓
Provider
  ↓
HTTP/内容校验
  ↓
返回
```

正常请求不得进入：

- 固定 sleep
- 排队等待
- RPM 限速
- 指数退避
- 自动重复调用

允许保留本地校验，因为 JSON parse / schema validation 基本没有可感知延迟。

---

## 2.3 免费模型以“避免无意义请求”为第一目标

对于 OpenRouter Free、SenseNova 免费额度：

- 429 后禁止立即连续轰炸。
- quota exhausted 不允许重复 retry。
- JSON 错误最多进行有限恢复。
- 应尽量命中现有 AI Cache。
- 同一个 in-flight 请求后续可考虑去重。
- 每次 retry 都应计入 Attempt Audit。
- 防止一次视频任务因重试消耗过多免费额度。

---

# 3. Reliability Mode 设计

新增：

```python
ReliabilityMode = Literal[
    "DIRECT",
    "STANDARD",
    "GUARDED",
    "FREE_TIER",
]
```

建议四种模式。

| 模式 | 使用场景 | 请求间隔 | 并发 | HTTP retry | JSON retry | 熔断 |
|---|---|---:|---:|---:|---:|---|
| DIRECT | 稳定收费 API / 本地模型 | 0 | 不额外限制 | 0 | 0 | 否 |
| STANDARD | 普通收费 API | 0 | 不额外限制 | 1 | 1 | 否 |
| GUARDED | SenseNova 免费/较易限流模型 | 2~3s | 1~2 | 2 | 1 | 是 |
| FREE_TIER | OpenRouter Free 等 | 4~5s | 1 | 2~3 | 1 | 是 |

注意：

- 表中的值是默认 Preset。
- Profile 可以覆盖默认参数。
- 不要硬编码“OpenRouter 必定 FREE_TIER”，只在新增 Profile 或选择免费模型 preset 时推荐。
- `DIRECT` 仍必须执行结果合法性检查，但检查失败后直接交给现有 fallback，而不是等待后 retry。

---

# 4. Model Profile 数据结构调整

## 4.1 后端

修改：

```text
backend/src/zhijian/domain/schemas.py
```

在 `ModelProfileConfig` 中新增：

```python
reliability_mode: Literal[
    "DIRECT",
    "STANDARD",
    "GUARDED",
    "FREE_TIER",
] = "STANDARD"

max_concurrency: int | None = Field(default=None, ge=1, le=16)

retry_count: int | None = Field(default=None, ge=0, le=5)

json_retry_count: int | None = Field(default=None, ge=0, le=3)

rate_limit_rpm: int | None = Field(default=None, ge=1, le=10000)

circuit_breaker_enabled: bool | None = None

circuit_breaker_threshold: int | None = Field(default=None, ge=1, le=20)

circuit_breaker_cooldown_seconds: float | None = Field(
    default=None,
    ge=1,
    le=3600,
)
```

已有字段继续复用：

```python
request_interval_seconds
timeout_seconds
supports_json_mode
supports_json_schema
max_output_tokens
```

不要重复增加同义字段。

---

## 4.2 AI ModelProfile

修改：

```text
backend/src/zhijian/ai/schemas.py
backend/src/zhijian/ai/model_registry.py
```

确保保存的 Reliability 配置进入运行时 `ModelProfile`。

增加一个解析函数，例如：

```python
resolve_reliability_policy(profile) -> ModelReliabilityPolicy
```

负责把 preset + 用户覆盖字段组合成最终参数。

示例：

```python
@dataclass(frozen=True)
class ModelReliabilityPolicy:
    mode: str
    request_interval_seconds: float
    max_concurrency: int | None
    retry_count: int
    json_retry_count: int
    rate_limit_rpm: int | None
    circuit_breaker_enabled: bool
    circuit_breaker_threshold: int
    circuit_breaker_cooldown_seconds: float
```

不要把 preset 默认值散落在 Gateway / Provider / UI 多处。

建议由后端维护单一默认值来源，前端仅用于展示。

---

# 5. 新增 Reliable LLM Execution Layer

建议新增：

```text
backend/src/zhijian/ai/reliability.py
```

职责：

```text
AIWorkloadGateway
        ↓
Reliability Policy
        ↓
Rate Limit / Concurrency Guard（仅需要时）
        ↓
Provider 调用
        ↓
Response Classification
        ↓
Retry / Backoff / JSON Recovery
        ↓
Circuit Breaker
        ↓
Fallback
```

不要把全部代码继续堆到 `providers/llm.py`。

`providers/llm.py` 应重点负责：

- HTTP 请求。
- Provider response 转换。
- Provider-specific header / usage / finish_reason 信息。

`reliability.py` 负责：

- 是否等待。
- 是否重试。
- 等多久。
- 是否熔断。
- 错误分类。
- JSON retry。
- 并发控制。

---

# 6. 错误模型重构

目前不能继续把不同错误都压成普通 `ValueError`。

新增结构化异常基类，例如：

```python
class AIProviderError(Exception):
    code: str
    retryable: bool
    switch_model: bool
    switch_provider: bool
```

最少实现：

```text
AI_PROVIDER_RATE_LIMITED
AI_PROVIDER_QUOTA_EXHAUSTED
AI_PROVIDER_TIMEOUT
AI_PROVIDER_NETWORK_ERROR
AI_PROVIDER_HTTP_5XX
AI_PROVIDER_BAD_REQUEST
AI_PROVIDER_AUTH_ERROR
AI_PROVIDER_EMPTY_RESPONSE
AI_PROVIDER_INVALID_JSON
AI_PROVIDER_SCHEMA_INVALID
AI_PROVIDER_OUTPUT_TRUNCATED
AI_PROVIDER_MODEL_UNAVAILABLE
```

---

# 7. Retry 分类规则

实现统一规则：

| 错误 | 同模型 retry | 切模型 | 熔断 |
|---|---|---|---|
| 429 rate limit | 是 | 多次失败后 | 达阈值后 |
| quota exhausted | 否 | 是 | 立即 |
| 5xx | 是 | 多次失败后 | 可选 |
| timeout | 是 | 多次失败后 | 可选 |
| network | 是 | 多次失败后 | 可选 |
| empty response | 是 | 多次失败后 | 否 |
| invalid JSON | JSON retry | 是 | 否 |
| schema invalid | JSON retry | 是 | 否 |
| output truncated | 缩小输入或增加输出上限后 | 是 | 否 |
| 400 参数错误 | 否 | 视错误原因 | 否 |
| 401/403 | 否 | 是 | 是 |
| model unavailable | 否 | 是 | 是 |

---

# 8. 429 改造

修改当前 `_retryable()` 行为。

当前逻辑不应继续要求：

```text
429 必须存在 Retry-After 才 retry
```

改成：

```text
所有 429 都进入 rate-limit 分类
```

等待时间：

```python
if Retry-After:
    wait = Retry-After
else:
    wait = exponential_backoff(attempt)
```

推荐：

```text
attempt 1 -> 5s
attempt 2 -> 10s
attempt 3 -> 20s
```

并增加：

```text
jitter = 0~30%
```

最终：

```python
wait = base_wait * random.uniform(1.0, 1.3)
```

注意：

- `DIRECT` 不执行等待型 retry。
- `STANDARD` 最多轻量 retry。
- `GUARDED/FREE_TIER` 才执行完整 backoff。

---

# 9. 删除“长 Prompt 不重试”的硬切断

当前存在：

```text
_LONG_PROMPT_RETRY_CHARS = 8_000
```

并在长 Prompt 时把 retry_count 强制设为 0。

应删除该硬编码行为。

改成：

```text
是否 retry 由 Reliability Policy 决定
```

对于长 Prompt：

- 不建议无限 retry。
- FREE_TIER 建议最多 1~2 次。
- 如果检测到 `OUTPUT_TRUNCATED`，优先降低 chunk 或 max input，而不是原样 retry。
- 不能因为输入超过 8000 chars 就完全取消网络/429 retry。

---

# 10. Rate Limiter

## 10.1 粒度

建议 key：

```text
provider + credential identity
```

不要直接把 API Key 明文作为 key。

例如：

```python
rate_key = sha256(
    f"{provider}:{api_key}".encode()
).hexdigest()
```

只保存在内存，不写日志。

---

## 10.2 FREE_TIER

建议初始默认：

```text
max_concurrency = 1
request_interval_seconds = 4
```

不要把 3 秒作为 OpenRouter Free 的默认稳定配置。

用户仍可在高级设置手动修改。

---

## 10.3 实现方式

第一阶段不需要 Redis。

当前 Mac mini 单机部署可以使用进程内：

```python
threading.Lock / Semaphore
monotonic timestamp
```

如果 worker 后续改为多进程/多实例，再升级 Redis / SQLite distributed limiter。

本阶段不要提前引入 Redis。

---

# 11. Circuit Breaker

维护：

```text
credential/provider/model
```

健康状态：

```text
CLOSED
OPEN
HALF_OPEN
```

行为：

```text
CLOSED
  ↓ 连续失败达到阈值
OPEN
  ↓ cooldown 到期
HALF_OPEN
  ↓ 一次探测成功
CLOSED
```

默认：

### GUARDED

```text
threshold = 3
cooldown = 60s
```

### FREE_TIER

```text
threshold = 3
cooldown = 120s
```

如果明确检测：

```text
quota exhausted
401
403
```

可直接 OPEN。

---

# 12. OpenRouter 同 endpoint 多模型 fallback

当前逻辑不要继续通过：

```text
primary.base_url == fallback.base_url
```

判断“fallback 无意义”。

改成判断：

```text
provider identity + model identity
```

以下情况允许 fallback：

```text
OpenRouter / model-a:free
    ↓
OpenRouter / model-b:free
```

即使：

```text
base_url 完全相同
```

也必须允许。

只有：

```text
same provider
same model
same endpoint
```

才视为重复配置。

---

# 13. HTTP 200 的 Response Validation

HTTP 2xx 不能等于业务成功。

`OpenAICompatibleProvider` 返回结果时补充 metadata：

```python
finish_reason
response_id
content_length
```

如果 Provider 支持，也保存：

```text
model returned by provider
usage
request-id
```

成功定义：

```text
HTTP 2xx
AND choices 存在
AND message/content 合法
AND 非空
AND finish_reason 可接受
```

对于 JSON Stage：

```text
AND JSON parse 成功
AND 顶层对象符合预期
AND Schema/contract validation 成功
```

---

# 14. JSON Structured Output Recovery

当前：

```text
services/video_support.py -> parse_model_json()
```

保留现有能力：

- strip
- 去 Markdown fence
- 截取 `{...}`
- 删除尾逗号

但重构为清晰的阶段：

```text
normalize
  ↓
extract candidate
  ↓
strict json.loads
  ↓
safe syntax repair
  ↓
json.loads
  ↓
object type validation
```

---

## 14.1 只允许安全修复

允许：

```text
Markdown fence
前后解释文字
尾逗号
BOM
部分控制字符
```

禁止自动“猜内容”。

例如下面这种：

```json
{"places": [
```

禁止自动补成：

```json
{"places": []}
```

因为这会造成静默数据损失。

应识别为：

```text
AI_PROVIDER_OUTPUT_TRUNCATED
```

---

# 15. JSON Retry

如果 Reliability Mode：

```text
STANDARD / GUARDED / FREE_TIER
```

允许：

```text
json_retry_count >= 1
```

第一次返回非法 JSON 后：

```text
同模型进行一次重新生成
```

附加非常短的系统约束：

```text
上一次响应无法被解析。
只返回合法 JSON 对象。
不要 Markdown。
不要解释。
不要代码块。
必须遵守原字段契约。
```

不要把整个错误回答重新塞入 Prompt。

只记录：

```text
error_type
parser_error
required_contract
```

防止浪费 Token。

---

# 16. Schema Validation

不要只验证“是不是 dict”。

不同 Stage 增加最小 contract validator。

### TRANSCRIPT_CORRECTION

至少：

```text
segments: list
```

### EXTRACT_TRAVEL_FACTS

至少：

```text
places: list
```

### GENERATE_AI_NOTE

至少：

```text
overview
warnings
sections
section_facts
```

业务完整性仍由现有下游逻辑验证。

Reliability Layer 只负责：

> 输出是否具备基本可消费结构。

---

# 17. supports_json_mode 的正确使用

当前模型 Profile 已存在：

```text
supports_json_mode
supports_json_schema
```

调整 `OpenAICompatibleProvider`：

### supports_json_mode = true

发送：

```json
{
  "response_format": {
    "type": "json_object"
  }
}
```

### supports_json_mode = false

不要发送 `response_format`。

使用：

```text
Prompt contract
+
本地 JSON parser
+
Schema validator
```

避免某些 OpenRouter Free 模型因为不支持 response_format 导致：

```text
400
200 但行为异常
provider fallback 异常
```

---

# 18. Profile Preset

修改：

```text
frontend/src/features/settings/providerPresets.ts
```

增加 Reliability 推荐值。

例如：

```typescript
DIRECT
STANDARD
GUARDED
FREE_TIER
```

不要完全依赖 provider 名称自动覆盖。

可以推荐：

```text
model name endsWith ":free"
→ 推荐 FREE_TIER
```

但用户最终选择优先。

---

# 19. 设置页面 UI

修改：

```text
frontend/src/features/settings/SettingsPage.tsx
frontend/src/lib/types.ts
frontend/src/lib/api.ts
```

模型编辑区域增加：

## 调用稳定性

```text
调用模式

[ 直连 ]
[ 标准 ]
[ 受保护 ]
[ 免费模型 ]
```

描述：

### 直连

```text
适合稳定付费模型。
不主动排队或延迟请求。
失败后快速进入备用模型。
```

### 标准

```text
适合普通付费 API。
对临时网络错误和非法结构化输出进行一次轻量恢复。
```

### 受保护

```text
适合有明显限流或免费额度的 API。
启用请求间隔、退避和熔断保护。
```

### 免费模型

```text
适合 OpenRouter Free 等严格限流模型。
单并发、主动限速，并对 429 进行退避。
```

---

# 20. 高级设置

默认折叠：

```text
高级调用参数
```

展开显示：

```text
请求最小间隔
最大并发
HTTP 重试次数
JSON 重试次数
RPM 上限
熔断开关
连续失败阈值
熔断冷却时间
```

Preset 改变时填充建议值。

用户手动修改后保存 Profile 自定义值。

---

# 21. 主备模型策略必须独立

Primary 和 Fallback 分别读取自己的 Reliability Policy。

示例 A：

```text
Primary:
DeepSeek Paid
DIRECT

Fallback:
OpenRouter Free
FREE_TIER
```

正常：

```text
DeepSeek -> 立即完成
```

只有失败时：

```text
OpenRouter -> 进入 FREE_TIER limiter
```

不能因为 fallback 是 FREE_TIER，导致 Primary 也进入 4 秒等待。

---

示例 B：

```text
Primary:
SenseNova Free
GUARDED

Fallback:
DeepSeek Paid
DIRECT
```

执行：

```text
SenseNova
  ↓
成功 -> 免费完成
  ↓
429 / quota / 多次失败
DeepSeek
  ↓
DIRECT
```

---

# 22. Stage Policy 与 Reliability Policy 的职责边界

不要混淆：

## Stage Policy

解决：

```text
这个工作阶段该用哪个模型？
temperature?
thinking?
max input/output?
```

## Model Reliability Policy

解决：

```text
这个具体模型应该如何被调用？
是否限速？
失败是否 retry？
JSON 错误是否恢复？
是否熔断？
```

优先级：

```text
Stage 决定选哪个 Model Profile
        ↓
Model Profile 决定 Reliability Policy
        ↓
Execution Layer 执行
```

Stage Policy 中已有的 `retry_count` 暂时保留兼容。

建议最终规则：

```text
Stage retry_count 有显式 override
    ↓
覆盖 Reliability 默认 HTTP retry_count

否则
    ↓
使用 Profile Reliability retry_count
```

避免一次性破坏现有配置。

---

# 23. Audit 与日志

继续复用：

```text
ExternalCallAudit
record_event
```

每次 Attempt 至少记录：

```json
{
  "provider": "openrouter",
  "model": "...",
  "reliability_mode": "FREE_TIER",
  "attempt": 2,
  "route": "primary",
  "error_code": "AI_PROVIDER_RATE_LIMITED",
  "http_status": 429,
  "retry_after": 10,
  "wait_seconds": 10.8,
  "circuit_state": "CLOSED"
}
```

JSON 错误：

```json
{
  "error_code": "AI_PROVIDER_INVALID_JSON",
  "http_status": 200,
  "finish_reason": "stop",
  "content_chars": 1843,
  "json_detected": true,
  "recovery": "retry_same_model",
  "json_attempt": 1
}
```

禁止记录：

```text
API Key
Authorization Header
完整 provider response
完整用户 prompt
```

现有 provider redaction 行为继续保留。

---

# 24. UI 运行状态提示

不是第一阶段硬要求，但如果改动量较小，可在任务详情日志中展示：

```text
OpenRouter / xxx:free
429 限流 · 10 秒后重试

OpenRouter / xxx:free
返回 JSON 无法解析 · 正在重新生成

OpenRouter
连续限流 · 暂停调用 120 秒

SenseNova
额度不足 · 已切换备用模型 DeepSeek
```

比现在只出现：

```text
模型没有返回 JSON 对象
```

更便于判断问题。

---

# 25. 新增文件建议

建议新增：

```text
backend/src/zhijian/ai/reliability.py
backend/tests/test_ai_reliability.py
```

可选：

```text
backend/src/zhijian/ai/structured_output.py
backend/tests/test_structured_output.py
```

如果 `reliability.py` 超过约 500~700 行，则拆出：

```text
structured_output.py
```

不要继续扩大已经很大的：

```text
services/video_support.py
```

---

# 26. 需要修改的现有文件

## Backend

```text
backend/src/zhijian/domain/schemas.py
backend/src/zhijian/ai/schemas.py
backend/src/zhijian/ai/model_registry.py
backend/src/zhijian/ai/gateway.py
backend/src/zhijian/providers/llm.py
backend/src/zhijian/services/video_support.py
backend/src/zhijian/ai/stages.py（仅兼容规则，避免大改）
```

根据设置 API 的实际实现，可能还需调整：

```text
backend/src/zhijian/api/router.py
```

---

## Frontend

```text
frontend/src/features/settings/SettingsPage.tsx
frontend/src/features/settings/providerPresets.ts
frontend/src/lib/types.ts
frontend/src/lib/api.ts
frontend/src/features/settings/SettingsPage.test.ts
```

---

## Tests

优先复用：

```text
backend/tests/test_ai_gateway.py
backend/tests/test_ai_stage_policies.py
backend/tests/test_video_notes.py
```

新增：

```text
backend/tests/test_ai_reliability.py
backend/tests/test_structured_output.py
```

---

# 27. 实施阶段

## Phase 1：配置模型

### 任务

- [x] 新增 ReliabilityMode。
- [x] 扩展 ModelProfileConfig。
- [x] 扩展运行时 ModelProfile。
- [x] 增加 Reliability preset resolver。
- [x] API 可完整读写新字段。
- [x] 老 Profile 缺失新字段时兼容，默认 `STANDARD`。
- [x] 不要求 Alembic migration，除非当前 Profile 实际存储结构不是 JSON Setting。

### 验收

老用户配置加载无异常。

---

# 28. Phase 2：错误分类与 Response Validation

### 任务

- [x] 引入 AIProviderError 类型体系。
- [x] HTTP 错误转换成稳定 error code。
- [x] 200 空内容识别。
- [x] finish_reason 记录。
- [x] output truncated 识别。
- [x] invalid JSON 识别。
- [x] schema invalid 识别。
- [x] quota exhausted 与普通 rate-limit 尽可能区分。

### 验收

日志不再只显示：

```text
模型没有返回 JSON 对象
```

而能显示明确错误代码。

---

# 29. Phase 3：Reliable Execution

### 任务

- [x] 新增 `ai/reliability.py`。
- [x] DIRECT 不产生额外等待。
- [x] STANDARD 支持轻量 retry。
- [x] GUARDED 支持 limiter/backoff。
- [x] FREE_TIER 支持单并发/强限速。
- [x] 所有 429 可进入 retry 分类。
- [x] Retry-After 优先。
- [x] 无 Retry-After 时指数退避。
- [x] 增加 jitter。
- [x] 删除 8000 字符硬禁 retry。
- [x] Circuit Breaker。
- [x] Primary/Fallback 分别使用自己的策略。

### 验收

稳定收费模型正常成功请求额外延迟接近 0。

---

# 30. Phase 4：Structured Output Recovery

### 任务

- [x] 抽离 JSON normalize。
- [x] 保留安全 repair。
- [x] 禁止业务内容猜测。
- [x] invalid JSON 支持有限重新生成。
- [x] schema validator。
- [x] output truncated 不走 JSON repair。
- [x] structured output recovery 记录 Audit。

### 验收

模拟：

```text
```json
{"places":[]}
```
```

可成功解析。

模拟：

```text
以下是结果：
{"places":[]}
```

可成功解析。

模拟：

```text
{"places":[
```

必须标记 OUTPUT_TRUNCATED，而不是静默产生空 places。

---

# 31. Phase 5：同 Provider 多模型 Fallback

### 任务

- [x] 修改 endpoint 相同即拒绝 fallback 的逻辑。
- [x] 以 provider/model identity 判断是否重复。
- [x] OpenRouter 不同模型允许 fallback。
- [x] Primary disabled 的作用域不得永久污染后续 Job。
- [x] Circuit 状态由可靠层统一维护。

### 验收

```text
OpenRouter model-a
→ rate limited
→ OpenRouter model-b
```

能正常工作。

---

# 32. Phase 6：Settings UI

### 任务

- [x] 模型 Profile 新增“调用稳定性”。
- [x] 四个模式显示简短说明。
- [x] 高级设置折叠。
- [x] Provider preset 可提供推荐模式。
- [x] `:free` 模型可提示推荐 FREE_TIER。
- [x] 用户可以覆盖。
- [x] 保存/刷新后配置保持一致。
- [x] Primary/Fallback Profile 各自独立。

---

# 33. Phase 7：测试

## Backend Unit Tests

必须覆盖：

### DIRECT

- [x] 正常 200 不 sleep。
- [x] 正常 JSON 不 retry。
- [x] 429 不进行等待型 retry。
- [x] fallback 可立即接管。

### STANDARD

- [x] 5xx retry 1 次。
- [x] timeout retry 1 次。
- [x] invalid JSON retry 1 次。
- [x] 不启用强制 limiter。

### GUARDED

- [x] request interval 生效。
- [x] concurrency 生效。
- [x] 429 Retry-After 生效。
- [x] 429 无 Retry-After 仍 retry。
- [x] exponential backoff。
- [x] circuit breaker。

### FREE_TIER

- [x] max concurrency = 1。
- [x] 请求间隔。
- [x] 多次 429 后 OPEN。
- [x] cooldown 后 HALF_OPEN。
- [x] probe 成功后 CLOSED。

---

# 34. Structured Output Tests

覆盖：

```text
纯 JSON
Markdown JSON
JSON 前后有解释
尾逗号
空字符串
纯文本
JSON array
截断 JSON
合法 JSON 但缺关键字段
finish_reason=length
```

顶层 array：

```json
[]
```

如果 Stage 要求 object，应返回：

```text
AI_PROVIDER_SCHEMA_INVALID
```

而不是当成功。

---

# 35. Fallback Tests

覆盖：

```text
paid DIRECT -> free FREE_TIER
free GUARDED -> paid DIRECT
same provider different model
same provider same model
different provider
primary quota exhausted
primary invalid JSON
primary 429
```

验证：

> Fallback 自己的可靠模式不能反向影响 Primary。

---

# 36. Frontend Tests

至少覆盖：

- [x] Reliability Mode 正常渲染。
- [x] 切换 Preset 后默认参数变化。
- [x] 展开高级设置。
- [x] 用户自定义参数可保存。
- [x] 刷新后参数恢复。
- [x] 旧 Profile 正常显示。
- [x] `:free` 模型显示推荐信息但不强制。

---

# 37. 性能验收

最重要指标：

## DIRECT

同一个 Mock Provider：

```text
修改前调用耗时
VS
修改后 DIRECT 调用耗时
```

除本地检查外：

```text
不得人为 sleep
不得进入 queue wait
不得 retry
```

正常路径额外逻辑耗时目标：

```text
< 10 ms（不计算网络）
```

---

# 38. 稳定性验收场景

使用 Fake Provider 模拟：

### 场景 A

```text
429
429
200 valid JSON
```

FREE_TIER：

```text
最终成功
Attempt = 3
```

---

### 场景 B

```text
200 invalid JSON
200 valid JSON
```

STANDARD / GUARDED：

```text
JSON retry 后成功
```

---

### 场景 C

```text
200 truncated JSON
```

结果：

```text
OUTPUT_TRUNCATED
```

不得错误缓存。

---

### 场景 D

```text
429 quota exhausted
```

结果：

```text
不原模型连续 retry
直接进入 circuit/fallback
```

---

### 场景 E

```text
OpenRouter model-a
OpenRouter model-b
```

同 base_url。

model-a 失败后：

```text
model-b 必须可以接管
```

---

# 39. Cache 要求

现有 AI Cache 保留。

严格要求：

```text
只有最终通过 Response Validation + JSON/Schema Validation 的结果
才能写入 Cache。
```

不得缓存：

```text
invalid JSON
truncated output
empty response
schema invalid
```

Retry 过程中也不得提前缓存。

---

# 40. Token 控制

免费模型 retry 会增加 Token 消耗，因此：

```text
HTTP retry_count
+
json_retry_count
```

必须共同受：

```text
ai_max_model_attempts_per_job
```

约束。

同一次逻辑调用建议：

```text
FREE_TIER 最大实际调用次数 <= 3~4
```

不能形成：

```text
HTTP retry 3
×
JSON retry 2
×
Fallback retry 3
```

导致指数级 Attempt。

实现时应建立：

```text
AttemptBudget
```

所有 retry 共用一个实际调用预算。

---

# 41. 不在本计划范围内

本阶段不要顺便：

- 重做完整 AI Router。
- 引入 Redis。
- 增加新的云服务依赖。
- 重写视频总结 Prompt。
- 修改 POI 算法。
- 重做 AI Cache。
- 改变 Stage 的业务职责。
- 自动购买/充值 API。
- 实现 OpenRouter 全模型动态价格路由。
- 做大规模 provider benchmark。

保持本次改造聚焦：

> **模型调用稳定性。**

---

# 42. 推荐默认配置

## OpenRouter Free

```yaml
reliability_mode: FREE_TIER
request_interval_seconds: 4
max_concurrency: 1
retry_count: 2
json_retry_count: 1
circuit_breaker_enabled: true
circuit_breaker_threshold: 3
circuit_breaker_cooldown_seconds: 120
```

---

## SenseNova 免费/低额度

```yaml
reliability_mode: GUARDED
request_interval_seconds: 2
max_concurrency: 1
retry_count: 2
json_retry_count: 1
circuit_breaker_enabled: true
circuit_breaker_threshold: 3
circuit_breaker_cooldown_seconds: 60
```

---

## 稳定付费模型

建议：

```yaml
reliability_mode: DIRECT
request_interval_seconds: 0
retry_count: 0
json_retry_count: 0
circuit_breaker_enabled: false
```

如果希望付费模型也对偶发网络问题有一点保护：

```yaml
reliability_mode: STANDARD
retry_count: 1
json_retry_count: 1
```

---

# 43. 最终期望架构

```text
Stage
  ↓
Model Routing
  ↓
Selected Model Profile
  ↓
Reliability Policy
  ↓
AIWorkloadGateway
  ↓
Cache
  ↓ miss
Reliable Execution
  ├── DIRECT -------------------------┐
  ├── STANDARD -> light retry         │
  ├── GUARDED  -> limiter/backoff     │
  └── FREE_TIER -> queue/circuit      │
                                      ↓
                                 LLM Provider
                                      ↓
                              HTTP Response
                                      ↓
                              Response Validator
                                      ↓
                         Structured Output Validator
                                      ↓
                    valid ---------------- invalid
                      ↓                      ↓
                    Cache             recovery policy
                      ↓                      ↓
                    Return        retry/model/provider
```

---

# 44. Definition of Done

必须全部满足：

- [x] 每个 Model Profile 可以独立选择 DIRECT / STANDARD / GUARDED / FREE_TIER。
- [x] 稳定付费模型可使用 DIRECT，正常调用无额外 sleep。
- [x] OpenRouter Free 可使用 FREE_TIER。
- [x] SenseNova 可使用 GUARDED。
- [x] 429 无 Retry-After 时仍能按策略退避。
- [x] quota exhausted 不重复浪费请求。
- [x] “模型没有返回 JSON 对象”被结构化错误替代。
- [x] HTTP 200 + invalid JSON 可以按 Profile 策略恢复。
- [x] HTTP 200 + truncated output 不被误判为合法 JSON。
- [x] 同一 OpenRouter endpoint 不同模型可以 fallback。
- [x] Primary/Fallback 分别应用自己的 Reliability Policy。
- [x] 长 Prompt 不再因为 8000 字符硬阈值完全失去 retry。
- [x] Invalid output 不进入 AI Cache。
- [x] Audit 能看出 provider/model/attempt/error/recovery。
- [x] 后端测试通过。
- [x] 前端测试通过。
- [x] 现有视频笔记、地点抽取、转写校对链路无回归。

## 44.1 实施记录（2026-09-16）

- Profile JSON Setting 已兼容扩展 `reliability_mode`、限速、并发、HTTP/JSON 重试与熔断字段；旧 Profile 默认为 `STANDARD`，无需 Alembic migration。
- `reliability.py` 集中提供预设解析、脱敏 credential identity、单进程限速/并发、指数退避（含 jitter）与熔断；DIRECT 不等待，主备按各自 Policy 执行，共享尝试上限。
- Provider 现在分类 429/quota/网络/超时/5xx/空响应，记录安全 metadata；同 endpoint 不同 model 可以 fallback。结构化输出在写 Cache 前校验，安全解析 Markdown、前后说明、尾逗号，截断不猜测且不缓存。
- 设置页可选择四种模式、显示 `:free` 建议，并折叠编辑高级调用参数；本地预览已在桌面与 390×844 验收，控制台无 warning/error。
- 离线验证：`pytest backend/tests -q`、`ruff check backend/src backend/tests`、Node 24 `pnpm verify` 与 `git diff --check` 通过。未调用真实 Provider、未重跑视频、未迁移或重启服务；真实配额、实际 fallback 与性能仍须按生产验收门禁取证。
- 2026-09-16 现场跟进：`job_ea308f2be1424feeb7446462d527694e` 两次 Replay 均命中同一条截断的 v1 Ground Map Cache，解析失败但无新 Provider Attempt。Cache Hit 现会先执行 JSON/Stage 契约校验；非法项以 `SKIPPED / AI_CACHE_INVALID` 记录 `cache_entry_id` 后绕过，合法 v1 项继续复用，新结果使用 v2 Cache Key 并通过 `previous_entry_id` 保留替代链。完整后端回归、Ruff 与 `diff --check` 通过；修复后续已部署，未删除历史 Cache，未自动 Replay。
- 2026-09-16 增量恢复与隔离已补齐：结构化输出失败只消耗 JSON retry，不再叠加 HTTP retry；转写拆分子批成功后立即提交，模型未返回的 Segment 记为 `UNCHANGED`，Replay 跳过 `CORRECTED/UNCHANGED`；截断后学习到的安全批量按 model 写入 Job runtime hint，后续批次和 Replay 直接复用。TPM/RPM 临时上限单独分类为 `AI_PROVIDER_THROTTLED`，只熔断对应 provider/credential/model；DIRECT 付费 Profile 不继承免费模型的锁、等待、重试或 circuit。Provider 阻塞的 Replay 进入 `NEEDS_USER` 而不是反复 FAILED。完整后端 180 项与 Ruff 通过，已受控重启；未自动 Replay、未调用真实 Provider。

---

# 45. Agent 执行约束

执行本计划时：

1. 先阅读：
   - `AGENTS.md`
   - `backend/src/zhijian/providers/llm.py`
   - `backend/src/zhijian/ai/gateway.py`
   - `backend/src/zhijian/domain/schemas.py`
   - `backend/src/zhijian/ai/model_registry.py`
   - `backend/src/zhijian/services/video_support.py` 中 `parse_model_json` 与 AI provider 构建相关部分
   - `frontend/src/features/settings/SettingsPage.tsx`
   - `frontend/src/features/settings/providerPresets.ts`
   - `frontend/src/lib/types.ts`

2. 不要扫描整个仓库后才开始开发；按上述文件定向读取。

3. 优先复用现有：
   - `AIWorkloadGateway`
   - `FallbackLLMProvider`
   - `AI Cache`
   - `ExternalCallAudit`
   - `record_event`
   - Stage Policy
   - Model Profile

4. 不得将 API Key 写入日志、数据库普通字段或错误详情。

5. 每个 Phase 完成后先运行相关小范围测试，再运行完整 Backend/Frontend Test。

6. 不要因为本计划顺便重构与 AI Reliability 无关的大文件。

7. 如现有数据存储是 JSON Setting，则优先兼容式扩展，不创建无必要 Alembic migration。

8. 最终提交前更新与模型设置/AI 调用机制直接相关的开发文档；不要大面积重写项目文档。

---

# 46. 建议执行顺序

```text
Phase 1  Profile Schema
   ↓
Phase 2  Error Classification
   ↓
Phase 3  Response Validation
   ↓
Phase 4  Reliable Execution
   ↓
Phase 5  Structured Output Recovery
   ↓
Phase 6  Fallback 修正
   ↓
Phase 7  Settings UI
   ↓
Phase 8  Tests + Regression
   ↓
Docs / Commit
```

不要先做 UI 再补运行机制。

后端行为与测试稳定后再接前端配置。
