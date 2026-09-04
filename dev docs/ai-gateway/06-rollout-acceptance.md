# 历史工作包与验收设计

> 来源：ai-gateway/AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md，原章节 42–50（正文保留，2026-09-03 分篇）。返回 [主题索引](AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md)。本篇是契约/规划，不是已实施清单；当前结论见 [实施状态](../IMPLEMENTATION_STATUS.md)，安全与回归见 [冻结清单](../REGRESSION_AND_CHANGE_GUARD.md)。裸文档路径均以 dev docs/ 为基准。只读取命中章节及其必要约束。

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
