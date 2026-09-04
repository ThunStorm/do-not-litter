# Pipeline 优化、Provider 与 Usage

> 来源：ai-gateway/AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md，原章节 28–41（正文保留，2026-09-03 分篇）。返回 [主题索引](AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md)。本篇是契约/规划，不是已实施清单；当前结论见 [实施状态](../IMPLEMENTATION_STATUS.md)，安全与回归见 [冻结清单](../REGRESSION_AND_CHANGE_GUARD.md)。裸文档路径均以 dev docs/ 为基准。只读取命中章节及其必要约束。

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
