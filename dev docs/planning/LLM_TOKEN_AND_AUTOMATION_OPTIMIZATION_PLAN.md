# LLM_TOKEN_AND_AUTOMATION_OPTIMIZATION_PLAN.md

# 至简：运行时 LLM Token 与自动化优化实施计划

> 适用仓库：`ThunStorm/do-not-litter`
> 适用分支：`codex/mac-mini-implementation`
> 范围：仅优化项目运行时 LLM 消耗、自动化处理链路与相关 POI 自动化；不讨论 Codex 开发额度。
> 执行方式：按 Work Package 逐步实施，每个 WP 独立验证，禁止无边界扩张。

---

# 1. 总体目标

当前项目已具备：

- 视频字幕 / ASR；
- Transcript Correction；
- 地点抽取；
- Note Map / Reduce；
- POI Resolver；
- Replay；
- AI Gateway；
- Cache；
- Budget；
- Provider fallback；
- Stage Policy；
- Evidence；
- Usage Audit。

下一阶段不再以“增加更多 LLM 调用换功能”为主要方向，而应转为：

```text
更少读取
+
更多复用
+
更多 deterministic
+
自动决定是否需要模型
+
只在真正困难的地方升级模型
```

目标系统：

```text
Input
  ↓
Deterministic Gate
  ↓
必要时 Correction
  ↓
Canonical Grounded Map
  ↓
┌───────────────┬────────────────┬─────────────────┐
│               │                │                 │
PlaceMention    Insights       Note Facts        Search/FTS
│                                │
↓                                ↓
Automatic POI               Final Reduce
Resolution                  Local / Remote
│                                │
↓                                ↓
High Confidence            Final Note
Auto Confirm
Low Confidence
Human Review
```

---

# 2. 核心优化指标

以下为目标值，不作为未经 Benchmark 的完成声明。

| 指标 | 目标 |
|---|---:|
| 首次视频 Prompt Token | ↓ 30%～45% |
| Remote Prompt Token | ↓ 50% 以上 |
| 同视频重新生成 Note | ↓ 70%～90% |
| Note Profile 切换 | ↓ 80% 左右 |
| 无变化 Replay | 接近 0 新 Token |
| 无效 Retry/Fallback Token | ↓ 70% 以上 |
| 自动跳过无必要 LLM Stage | ≥ 80% 可判定场景 |
| 高置信 POI 人工审核量 | 持续下降 |
| Token / 视频分钟 | 可量化、可追踪、可回归 |

---

# 3. 当前主要问题

现有链路近似：

```text
字幕 / ASR
    ↓
TRANSCRIPT_CORRECTION
    ↓
EXTRACT_TRAVEL_FACTS
    ↓
GENERATE_AI_NOTE Map
    ↓
GLOBAL_SYNTHESIS Reduce
```

主要浪费来源：

1. 同一 Transcript 被多个 LLM Stage 重复读取；
2. 地点抽取与 Note Map 做了大量重复语义理解；
3. Note Chunk 重复携带完整 Place Evidence；
4. Render Profile 进入 Map Prompt，导致 Map Cache 无法跨 Profile 复用；
5. Retry / Fallback 在大 Prompt 下可能把成本放大 2～3 倍；
6. Transcript Correction 对 ASR 的校对范围仍可缩小；
7. Token Budget 目前更像硬熔断器，不是主动优化器；
8. Stage Policy 仍主要依赖静态配置，缺少运行时自动决策；
9. POI V2 已有 Shadow 能力，但真实业务仍需要大量人工 Review；
10. 当前已有 Usage 数据，但缺少完整的成本闭环和自动化调参依据。

---

# 4. 最终目标架构

```text
                     Transcript
                         │
                 Transcript Analyzer
                         │
             ┌───────────┴───────────┐
             │                       │
          PASS                     NEED_FIX
             │                       │
             │                Delta Correction
             │                       │
             └───────────┬───────────┘
                         ↓
               Corrected Transcript
                         │
                         ↓
             Canonical Grounded Map
                   一次主语义扫描
                         │
          ┌──────────────┼───────────────┐
          │              │               │
       Places          Facts          Note Facts
          │                              │
          ↓                              ↓
 Automatic POI                    Profile-independent
 Resolution                       Map Artifact Cache
          │                              │
          │                              ↓
          │                        Final Reduce
          │                         │          │
          │                       Local      Remote
          │                         │          │
          └──────────────→ Quality / Cost Router
```

核心规则：

> 同一 Transcript 原则上只允许一次主要语义扫描。

---

# 5. Work Package 总览

| WP | 内容 | 优先级 |
|---|---|---:|
| WP0 | Token Baseline / Usage Breakdown | P0 |
| WP1 | Canonical Grounded Map 契约 | P0 |
| WP2 | 合并 Place Extraction 与 Note Map | P0 |
| WP3 | GroundedMapArtifact 持久化与 Cache | P0 |
| WP4 | Render Profile 与 Map 解耦 | P0 |
| WP5 | Chunk-local Evidence | P1 |
| WP6 | Delta Transcript Correction | P1 |
| WP7 | Retry / Fallback Token Guard | P1 |
| WP8 | 自动 Stage Skip | P0 |
| WP9 | 自动 Local / Remote Router | P0 |
| WP10 | Token-aware Soft Budget | P1 |
| WP11 | 自动 Cache / Artifact Reuse | P0 |
| WP12 | 自动 POI Resolution / Human Review Gate | P0 |
| WP13 | 自动 Benchmark / Regression | P0 |
| WP14 | Token Anomaly Detection | P1 |
| WP15 | Production Graduation | P0 |

---

# 6. WP0：建立 Token Baseline

## 目标

改 Pipeline 前先知道真实 Token 去向。

## 新增接口

```text
GET /api/jobs/{job_id}/ai-usage
```

建议返回：

```json
{
  "total": {},
  "local": {},
  "remote": {},
  "by_stage": {},
  "by_model": {},
  "cache": {},
  "retry": {},
  "fallback": {},
  "waste": {}
}
```

每 Stage：

```text
prompt_tokens
completion_tokens
cached_tokens
input_chars
attempt_count
retry_count
fallback_count
cache_hit_count
duration_ms
provider
model
location
```

新增指标：

```text
prompt_tokens_per_video_minute
remote_tokens_per_video_minute
cache_hit_ratio
retry_token_ratio
fallback_token_ratio
repeated_input_ratio
```

## 验收

能够得到：

```text
Total Prompt              42,350
Transcript Correction      6,200
Ground Map                21,300
Note Reduce                8,100
Retry / Fallback            6,750
```

---

# 7. WP1：Canonical Grounded Map

## 目标

一次 Map 输出同时供：

```text
地点
核心 bullet point
推荐菜 / 核心体验
月份 / 季节
价格
注意事项
作者观点
Note
POI Context
```

使用。

## 推荐结构

```json
{
  "chunk_index": 1,
  "segment_ids": [],
  "summary": "",
  "key_points": [],
  "places": [
    {
      "name": "",
      "raw_name": "",
      "place_type": "",
      "city_hint": "",
      "province_hint": "",
      "district_hint": "",
      "aliases": [],
      "nearby_landmarks": [],
      "highlights": [],
      "recommended_items": [],
      "best_months": [],
      "best_seasons": [],
      "best_time_slots": [],
      "visit_windows": [],
      "warnings": [],
      "price": "",
      "queue": "",
      "audience": "",
      "author_opinion": "",
      "quote": "",
      "segment_ids": [],
      "confidence": 0.0
    }
  ],
  "warnings": [],
  "prices": [],
  "opinions": []
}
```

## 规则

所有事实：

```text
必须有 Segment ID
+
必须能回到逐字 Evidence
```

模型禁止生成：

```text
经纬度
POI ID
确认状态
Transcript 中没有的事实
```

---

# 8. WP2：合并 Place Extraction 与 Map

## 目标

彻底取消默认：

```text
Transcript
→ Place LLM
```

独立扫描。

## 新流程

```text
Transcript
  ↓
Ground Map
  ↓
GroundedMapFacts
  ↓
deterministic
  ↓
PlaceMention
```

Pipeline 继续保留：

```text
EXTRACT_TRAVEL_FACTS
```

但默认逻辑改为：

```text
读取 GroundedMapArtifact
→ 合并地点
→ Evidence Validation
→ Materialize PlaceMention
```

不调用 LLM。

仅允许：

```text
用户主动 Force Re-extract
REMOTE_ONLY
特殊疑难地点
```

触发重新抽取。

## 验收

```text
EXTRACT_TRAVEL_FACTS
prompt_tokens == 0
```

默认链路必须成立。

---

# 9. WP3：GroundedMapArtifact 持久化

## 目标

让主语义扫描变成稳定中间产物。

建议新增：

```text
GroundedMapArtifact
```

或等价 Artifact 类型。

Key 建议：

```text
transcript_id
transcript_version
content_hash
map_prompt_version
supplement_hash
domain
domain_pack_version
provider
model
semantic_options
```

禁止包含：

```text
COMPACT
DETAILED
TRAVEL_GUIDE
overview_limit
max_bullets
UI mode
```

## 验收

同一 Transcript：

```text
COMPACT
→ DETAILED
```

不得重新调用 Ground Map。

---

# 10. WP4：Render Profile 与 Map 解耦

## Map 只负责事实

```text
summary
key_points
places
warnings
prices
opinions
Evidence
```

禁止 Map Prompt 包含：

```text
COMPACT
DETAILED
TRAVEL_GUIDE
```

最终：

```text
GroundedMapFacts
      ↓
Render Profile
      ↓
Note Reduce
```

## 验收

Profile 切换时，只产生：

```text
NOTE_REDUCE
```

---

# 11. WP5：Chunk-local Evidence

## 目标

禁止每个 Chunk 重复发送全部 Mention。

实现：

```python
place_evidence_index_for_chunk(
    mentions,
    chunk_segment_ids
)
```

筛选条件：

```text
mention.segment_ids
∩
chunk.segment_ids
!= empty
```

允许少量相邻上下文，但必须有硬上限。

## 验收

构造：

```text
50 mentions
10 chunks
```

每 Chunk 只输入真实相关 Mention。

---

# 12. WP6：Delta Transcript Correction

## 原则

Transcript Correction 不再追求：

```text
全文润色
```

而只解决：

```text
会影响后续事实理解的错误
```

优先关注：

```text
地名
人名
菜名
机构名
数字
价格
日期
月份
专有名词
严重断句
明显 ASR 错字
```

## 自动分类

### 人工字幕

```text
默认 PASS
0 LLM
```

### 高质量平台字幕

```text
Quality Gate
→ 仅异常 Segment
```

### Whisper

```text
Deterministic Candidate Detector
→ 可疑 Segment
→ ± N 个邻接 Segment
→ Correction LLM
```

输出仍采用 Delta：

```json
{
  "changes": []
}
```

未返回的 Segment：

```text
UNCHANGED
```

---

# 13. WP7：Retry / Fallback Token Guard

## 问题

大 Prompt：

```text
20K
→ retry
→ 20K
→ fallback
→ 20K
```

会瞬间三倍成本。

## 改造

长上下文 Stage 默认：

```text
retry_count = 0
```

仅以下错误允许自动 Retry：

```text
connection reset
HTTP 429 with retry-after
短暂网络错误
明确 Provider transient error
```

以下错误不得重新发送完整 Prompt：

```text
JSON parse error
schema mismatch
minor malformed output
missing optional field
```

先执行：

```text
local tolerant parser
→ JSON repair
→ schema validation
```

只有仍失败才考虑模型修复。

---

# 14. WP8：自动 Stage Skip

## 目标

Pipeline 自动判断：

> 这个 Stage 真的需要 LLM 吗？

新增：

```text
StageDecisionEngine
```

输出：

```json
{
  "stage": "TRANSCRIPT_CORRECTION",
  "decision": "RUN | SKIP | REUSE | ESCALATE",
  "reason": "",
  "estimated_input_tokens": 0
}
```

### 示例

平台人工中文字幕：

```text
CORRECTION
→ SKIP
```

已有匹配 GroundMapArtifact：

```text
GROUND_MAP
→ REUSE
```

Note Profile 改变：

```text
GROUND_MAP
→ REUSE
NOTE_REDUCE
→ RUN
```

POI 已人工确认：

```text
POI Resolver
→ REUSE
```

## 原则

优先级：

```text
REUSE
>
SKIP
>
LOCAL
>
REMOTE
```

---

# 15. WP9：自动 Local / Remote Router

## 目标

不再主要依赖用户手动选模型。

新增运行时：

```text
CostQualityRouter
```

输入：

```text
stage
estimated tokens
content size
model capabilities
historical success rate
historical schema pass rate
latency
local availability
remote price
job budget remaining
```

输出：

```text
LOCAL
REMOTE_FAST
REMOTE_STRONG
SKIP
REUSE
```

## 默认策略

### Local 优先

```text
Transcript Correction
Ground Map
Entity Extraction
Classification
```

### Remote Strong 仅用于

```text
复杂 Reduce
冲突解决
低置信结果
高价值字段
本地多次失败
用户显式 Quality 模式
```

---

# 16. WP10：Token-aware Soft Budget

现有 Hard Budget 保留。

增加 Soft Budget：

```text
expected_prompt_tokens
expected_completion_tokens
expected_total_calls
```

在 Job 开始时估算：

```text
视频分钟
Transcript chars
Chunk 数量
Stage 数
```

产生：

```text
EXPECTED
WARNING
HARD_LIMIT
```

### 自动行为

达到 Warning：

```text
优先 Local
禁止重复 Retry
禁止无必要 Remote Escalation
提高 Cache / Reuse 优先级
```

接近 Hard Limit：

```text
只允许必要 Stage
```

---

# 17. WP11：自动 Artifact Reuse

## 目标

不需要用户知道“该 Replay 哪一步”。

新增：

```text
ArtifactDependencyResolver
```

自动检查：

```text
Source
Transcript
Correction
GroundMap
PlaceMention
Note
POI
Screenshot
```

每个 Artifact：

```text
input_hash
producer_version
semantic_hash
dependency_hash
```

## 自动规则

如果上游没有语义变化：

```text
直接 REUSE
```

例如：

```text
修改 Note Profile
```

自动：

```text
Transcript REUSE
Correction REUSE
GroundMap REUSE
PlaceMention REUSE
POI REUSE
Note Reduce RUN
```

这应成为默认行为，而不是要求用户手动选择 Replay 起点。

---

# 18. WP12：POI 自动确认自动化

## 背景

当前真正影响人工成本的是：

```text
大量 REVIEW / UNRESOLVED
```

已有 POI V2 Shadow 不应浪费。

## 自动化架构

```text
PlaceMention
    ↓
Candidate Search
    ↓
Feature Scoring
    ↓
Confidence Gate
 ┌───────┼───────────┐
 ↓       ↓           ↓
AUTO   CONTEXTUAL   REVIEW
 ↓       ↓           ↓
Confirm  Verify      Human
```

## AUTO_STRONG 条件

必须同时满足高标准：

```text
name_match >= threshold
city / province / district context
category compatible
candidate gap 足够大
坐标有效
无 chain risk
无 cross-city conflict
无 negative evidence
```

### 自动确认

只允许：

```text
AUTO_STRONG
```

直接晋级。

### AUTO_CONTEXTUAL

需要：

```text
附近地点
Geo Session
已确认 Anchor
视频上下文
```

支持时自动进入二次验证，而不是直接人工。

### REVIEW

只将：

```text
真正歧义
跨城市冲突
连锁门店
候选分差小
分类冲突
无可靠上下文
```

交给用户。

## 学习闭环

人工确认后记录：

```text
MANUAL_CONFIRMED
MANUAL_REJECTED
```

用于：

```text
离线 Golden
Threshold Benchmark
规则调优
```

禁止未经验证的在线自学习直接改变生产阈值。

---

# 19. WP13：自动 Benchmark / Regression

## 目标

以后任何模型 / Prompt / Router 改动都能自动知道：

```text
质量有没有下降
Token 有没有增加
```

建立：

```text
scripts/benchmark_llm_pipeline.py
```

数据集至少包括：

```text
10 分钟视频
30 分钟视频
60 分钟视频

高质量字幕
Whisper ASR
快速多地点
长尾地点
餐馆
景区
跨城市
月份/季节
价格
错误字幕
无地点视频
```

指标：

```text
place_precision
place_recall
evidence_coverage
hallucination_rate
note_coverage
schema_pass_rate
poi_top1
poi_top3
auto_confirm_precision
review_rate

prompt_tokens
completion_tokens
remote_tokens
local_tokens
cache_hit_ratio
latency
```

## 自动回归 Gate

例如：

```text
Token +15%
且
质量无明显提升
→ FAIL
```

```text
Hallucination 增加
→ FAIL
```

```text
Evidence Coverage 下降
→ FAIL
```

```text
POI 自动确认错误 > 0
→ FAIL
```

---

# 20. WP14：Token Anomaly Detection

新增运行时异常检测：

```text
TokenCostMonitor
```

自动发现：

```text
同一 Stage 重复调用
Chunk 数异常增加
Fallback 连续触发
Cache Hit 突然归零
Prompt Token / 分钟异常
Remote 占比突增
```

例如：

```text
某 20 分钟视频正常 40K Token
本次突然 130K
```

记录：

```text
AI_TOKEN_ANOMALY
```

并给出：

```text
stage
provider
model
suspected_reason
```

默认不自动重新执行 Job。

---

# 21. WP15：Production Graduation

所有结构改造完成后再进行真实验收。

## Benchmark 顺序

### A. Fixture

```text
全部离线 Golden
```

### B. 固定真实视频

至少：

```text
10 min
30 min
60 min
```

分别跑：

```text
旧 Pipeline
新 Pipeline
```

比较：

```text
Token
质量
耗时
地点召回
POI 审核量
Note Evidence
```

### C. Replay

验证：

```text
同 Profile
不同 Profile
force regenerate
Stage Replay
```

### D. Provider

验证：

```text
Local
Remote
Fallback
Timeout
Invalid JSON
```

---

# 22. 自动化决策优先级

系统运行时统一遵循：

```text
1. Can REUSE?
      ↓ no
2. Can SKIP?
      ↓ no
3. Can deterministic solve?
      ↓ no
4. Can LOCAL solve?
      ↓ no
5. Can REMOTE_FAST solve?
      ↓ no
6. REMOTE_STRONG
```

而不是：

```text
直接调用最强模型
```

---

# 23. 自动化状态记录

每个 Stage 增加决策记录：

```json
{
  "decision": "REUSE",
  "decision_source": "AUTO",
  "reason_code": "UNCHANGED_SEMANTIC_INPUT",
  "estimated_tokens_saved": 12400
}
```

Reason Code 建议：

```text
CACHE_HIT
ARTIFACT_REUSED
QUALITY_GATE_PASS
NO_RELEVANT_SEGMENTS
LOCAL_SUFFICIENT
REMOTE_ESCALATION_REQUIRED
BUDGET_PRESSURE
PROVIDER_UNAVAILABLE
LOW_CONFIDENCE
```

---

# 24. 推荐代码边界

优先复用现有：

```text
backend/src/zhijian/ai/
backend/src/zhijian/services/video_pipeline.py
backend/src/zhijian/services/video_support.py
backend/src/zhijian/services/job_replay.py
backend/src/zhijian/services/external_audit.py
```

建议新增：

```text
backend/src/zhijian/ai/stage_decision.py
backend/src/zhijian/ai/cost_router.py
backend/src/zhijian/ai/token_monitor.py
backend/src/zhijian/services/artifact_dependencies.py
backend/src/zhijian/services/grounded_map.py
```

不要继续把所有逻辑堆入：

```text
video_support.py
```

这次优化同时应适当拆分大文件，但禁止为了重构而重写整个视频 Pipeline。

---

# 25. 实施顺序

必须按以下顺序：

```text
WP0
↓
WP1
↓
WP2
↓
WP3
↓
WP4
↓
WP5
↓
WP8
↓
WP11
↓
WP6
↓
WP7
↓
WP9
↓
WP10
↓
WP12
↓
WP13
↓
WP14
↓
WP15
```

核心原因：

先建立：

```text
Ground Map + Artifact Reuse
```

再做：

```text
Router / Budget / Automation
```

否则会在旧架构上自动化错误行为。

---

# 26. 第一阶段建议冻结范围

第一阶段先只实施：

```text
WP0～WP5
WP8
WP11
```

这批完成后应已经实现：

```text
地点抽取不再独立扫 Transcript
Map 可持久复用
Profile 切换不重跑 Map
Evidence 不再全量重复
Stage 自动 Skip / Reuse
```

这是最直接的 Token 降耗核心。

---

# 27. 第二阶段建议

实施：

```text
WP6
WP7
WP9
WP10
```

解决：

```text
Correction Token
Retry 爆量
Local / Remote 自动路由
Token Budget 自动管理
```

---

# 28. 第三阶段建议

实施：

```text
WP12
WP13
WP14
WP15
```

解决：

```text
POI 人工成本
自动 Benchmark
Token 异常检测
生产晋级
```

---

# 29. 非目标

本 Plan 不实施：

```text
新的旅行推荐功能
自动行程规划
新的地图大功能
视觉设计重构
Codex Token 优化
无必要的新 Provider
无依据的 Prompt 大改
无真实数据支撑的阈值降低
```

---

# 30. 最终验收标准

完成后应满足：

### 架构

```text
Transcript 只有一次主要语义扫描
```

### Cache

```text
Profile 切换不重跑 Map
```

### Replay

```text
无变化 Stage 自动 Reuse
```

### Place

```text
EXTRACT_TRAVEL_FACTS 默认 0 LLM Token
```

### Correction

```text
只校对必要 Segment
```

### Router

```text
Local 优先
Remote 按质量 / 风险自动升级
```

### Retry

```text
非法 JSON 不触发完整 Prompt 重发
```

### POI

```text
高置信候选自动确认
真正歧义才人工 Review
```

### Observability

每个 Job 可以明确回答：

```text
用了多少 Token
哪个 Stage 用的
为什么调用
为什么升级 Remote
Cache 节省多少
自动化节省多少
Retry 浪费多少
```

### Benchmark

能够证明：

```text
质量不下降
+
Token 明显下降
+
人工 POI Review 明显下降
```

---

# 31. Agent 执行提示词

可直接交给 Codex：

```text
按 AGENTS.md 接手项目，并实施 dev docs/planning/LLM_TOKEN_AND_AUTOMATION_OPTIMIZATION_PLAN.md。

严格按 Work Package 顺序执行，不一次性实施全部 WP。

本任务核心目标是降低项目运行时 LLM Token，并提高自动化处理比例，不关注 Codex 自身额度。

优先消除 Transcript 被不同 Stage 重复送入 LLM 的问题。

必须保留现有 Source / Transcript / Segment / Evidence / Job / Replay 身份边界，不修改已发布 migration。

任何模型调用、生产迁移、生产重启、真实视频重跑均需遵循现有项目授权边界。

每个 WP：
1. 先确认现状；
2. 明确验收条件；
3. 只改目标代码；
4. 先跑目标测试；
5. 完成该工作包后更新必要文档；
6. 不顺手扩展范围。

第一阶段只实施 WP0～WP5、WP8、WP11。
完成第一阶段后停止，汇报：
- 变更；
- 测试；
- Token 理论减少点；
- 尚未进行的真实 Benchmark；
- 下一阶段建议。
```
