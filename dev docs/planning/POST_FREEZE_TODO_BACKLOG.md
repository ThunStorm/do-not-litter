# 至简封板后待办池

> 本文只记录**当前封板完成之后**的候选工作。
> 本文不是当前授权，不应被 Agent 自动实施。
> 当前接手以 [CODEX_CONTEXT.md](../CODEX_CONTEXT.md) 与 [CURRENT_HANDOFF.md](../CURRENT_HANDOFF.md) 为准；不再依赖已移除的临时交接指南。

---

# 1. 使用规则

每个后续工作包只有在用户明确选择后才进入实施。

优先级含义：

```text
P0 = 影响当前架构正确性、生产可信度或稳定性
P1 = 封板后应尽快处理的架构收口
P2 = 下一阶段主要产品能力
P3 = 中长期增强
HOLD = 当前不值得承担复杂度
```

总体推荐顺序：

```text
封板物料更新
↓
P0 Production Acceptance
↓
P0 Runtime / Budget correctness
↓
P1 Gateway Consolidation
↓
P2 GenericProcessor
↓
P2 Source Watch
↓
P3 Contextual Vision
```

---

# 2. P0 — Production Acceptance & Production Truth

## 目标

证明当前仓库中的 AI Workload Gateway 不只在自动测试中成立，而是在真实 Mac mini 生产链路中成立。

## 当前原因

当前代码已到：

```text
Alembic 0010
AI stage policy
Local/Remote routing
usage aggregation
transcript quality gate
Map/Reduce
AI cache
AI budget
Domain Context
Vision boundary
runtime hardening
```

但已有实施记录仍没有证明本轮 Gateway 后半程已经执行：

```text
未来迁移的备份与恢复演练
真实 Local model E2E
真实 Remote provider E2E
真实 video job
真实 fallback
真实 cache hit
真实 budget exhaustion
```

## 建议工作

### A. Production migration

```text
backup SQLite
verify no active job
确认当前 `0010` 数据完整，再为未来新 migration 验证备份、升级与恢复
restart via existing managed path
verify API / Worker / SQLite
```

### B. Real E2E matrix

至少准备：

1. 有平台字幕的视频；
2. 需要 Whisper ASR 的视频；
3. Local-only；
4. Remote-only；
5. Local-first；
6. 故意制造 Local failure → Remote fallback；
7. cache hit；
8. force regenerate；
9. cancel；
10. replay。

### C. Metrics

对每个 Job 记录：

```text
input tokens
output tokens
cached tokens
local calls
remote calls
latency
fallback count
quality outcome
user-visible result
```

## Exit Gate

至少连续通过 3–5 个不同真实视频 Job，且：

- 数据库迁移无数据损失；
- API / Worker 正常；
- Local / Remote 路由与审计一致；
- Cache 命中真实生效；
- Cancel / Replay 无异常；
- Token 消耗没有明显反向放大；
- 笔记质量无明显退化。

---

# 3. P0 — Per-attempt Budget

## 当前问题

Budget 检查目前更接近 Pipeline 调用边界。

在：

```text
LOCAL_FIRST
Local fails
→ Remote fallback
```

场景中，应分别在实际 Provider attempt 前检查相应预算。

## 目标

变成：

```text
每一个真实 Provider attempt
↓
resolve actual location
↓
check corresponding budget
↓
execute
↓
audit actual usage
```

## Acceptance

必须证明：

- Local 预算耗尽不会错误阻止仍有额度的 Remote fallback（除非策略禁止）；
- Remote 预算耗尽时不会继续发 Remote 请求；
- Cache hit 不触发真实 attempt budget；
- Failed attempt 的计数语义明确。

---

# 4. P0 — Fallback Cache 语义明确化

## 当前问题

Cache key 目前绑定准备调用的：

```text
provider
model
```

但 Fallback 最终结果可能来自另一个 Provider / Model。

可能出现：

```text
key = local model
actual result = remote fallback
```

之后 Local 恢复时仍命中上次 Remote 结果。

## 需要先决定语义

### Option A — Actual Provider Cache

Cache 对实际产生结果的 Provider / Model 生效。

优点：

- 可解释；
- Provider/Model 一致。

### Option B — Route Result Cache

Cache 绑定：

```text
resolved route
evidence
semantic options
```

结果允许来自 fallback。

优点：

- 用户更关心“同一任务已有结果”。

## 推荐

优先 Option A，除非产品明确希望“请求级最终结果缓存”。

## Acceptance

必须覆盖：

```text
primary success
primary fail + fallback success
primary recovered
force regenerate
provider changed
model changed
```

---

# 5. P1 — AIWorkloadGateway Consolidation

## 当前问题

`AIWorkloadGateway` 当前仍接近 pass-through seam。

真正的：

```text
policy
routing
fallback
cache
budget
domain context
resource manager
audit
```

大量逻辑仍在 `video_support.py`。

如果直接开始 GenericProcessor，容易形成第二套 AI 执行逻辑。

## 目标

最终统一为：

```text
Processor
↓
AIRequest
↓
AIWorkloadGateway
├─ resolve stage policy
├─ resolve profile
├─ resolve route
├─ cache lookup
├─ budget check
├─ local lease
├─ provider attempt
├─ fallback / escalation
├─ audit
└─ AIResult
```

业务只负责：

```text
Evidence
Capability
Schema
business validation
result materialization
```

## 不做

- 不顺便引入 LangChain；
- 不引入复杂 Agent Framework；
- 不引入分布式调度；
- 不提前上 Redis。

## Exit Gate

Video Pipeline 仍通过原回归，同时一个最小非 Video 调用可以完整通过 Gateway。

---

# 6. P2 — GenericProcessor MVP

## 产品价值

这是封板后最推荐的下一项新产品能力。

目标是让：

```text
任何未知非结构化信息
```

不再直接 Unsupported，而进入通用整理。

## MVP 输出

```text
title
summary
key_points[]
entities[]
dates[]
locations[]
action_items[]
claims[]
evidence[]
```

## 原则

仍然：

```text
Evidence First
Schema First
User Correctable
```

不能变成纯自然语言总结器。

## 推荐演进

```text
Generic
↓ 高频场景
Configurable Processor
↓ 规则成熟
Dedicated Processor
```

## 第一版不做

- Vector DB；
- Knowledge Graph；
- 自动执行外部动作；
- 自动创建无限类别；
- 高风险自动化。

## Acceptance

至少用：

```text
网页正文
聊天/随手记
通用 PDF
未知主题文章
商品介绍
通知/公告
```

验证通用输出和 Evidence。

---

# 7. P2 — Source Watch

## 产品价值

让产品从一次性：

```text
Capture → Process
```

升级到：

```text
Capture
→ Process
→ Watch
→ New Snapshot
→ Diff
→ User notification
```

## 首批适合场景

- 招聘公告更新；
- 截止日期变化；
- 页面内容更新；
- 商品价格变化；
- 旅行地点状态变化。

## 数据原则

任何更新必须：

```text
create new Snapshot
```

不能静默覆盖历史事实。

## 第一版建议

只做：

```text
HTTP source watch
ETag / Last-Modified / content hash
deterministic diff
optional AI summary of diff
```

不要先做浏览器自动登录。

---

# 8. P3 — Contextual Vision

## 当前基础

代码已有：

```text
SCREENSHOT_UNDERSTANDING
image-capable Profile validation
```

但当前视频截图仍主要用于确定性抽帧和阅读回看。

## 推荐进入条件

必须先完成：

- 真实本地模型 Benchmark；
- Production Acceptance。

## 首批能力

不要做“整视频多模态理解”。

只对候选帧执行：

```text
店招
菜单
价格
路牌
景点名称
地图截图
```

## 原则

VisualEvidence 与 TranscriptEvidence 并存。

视觉模型结果不能覆盖更强的确定性来源。

---

# 9. P3 — Golden Benchmark / Release Gate

## 目标

避免以后每次换模型只能靠主观感觉。

建立固定样本：

```text
clean subtitle
bad ASR
long travel video
many POI
few POI
ambiguous names
local-only
remote-only
fallback
```

记录：

```text
schema pass
evidence coverage
quality score
local tokens
remote tokens
latency
fallback rate
cache rate
```

以后：

```text
change model
change prompt
change chunk size
change routing
```

都跑同一组。

---

# 10. HOLD — Multi Worker

暂缓。

当前：

```text
Mac mini
16 GB unified memory
single-user
single-node
```

收益暂不足以承担：

```text
distributed lease
queue scheduling
worker capability routing
cross-worker cache
failure recovery
```

触发条件：

- 单 Worker 成为真实吞吐瓶颈；
- 有多个物理节点；
- 需要 Cloud Worker。

---

# 11. HOLD — Cloud / SaaS

暂缓：

```text
multi-user
tenant isolation
cloud DB
cloud GPU
subscription
quota billing
```

当前架构不要为了未来 SaaS 预先复杂化。

---

# 12. HOLD — Vector DB / RAG

当前 Source / Segment / Claim / Evidence 关系数据仍足够。

触发条件：

- GenericProcessor 内容量明显增长；
- 用户开始频繁做跨来源语义问答；
- 传统查询已经无法满足检索。

在此之前不要引入 Vector DB。

---

# 13. HOLD — Knowledge Graph

当前关系表足够。

只有：

```text
跨领域 Entity
复杂 Relation
大量多跳查询
```

成为真实需求后再评估。

---

# 14. HOLD — 高风险 Action Layer

包括：

```text
自动提交报名
自动发邮件
自动购买
自动预订
自动填表并提交
```

必须以后单独设计：

```text
permission
preview
confirmation
audit
rollback
risk tier
```

不要和 GenericProcessor 混做。

---

# 15. 推荐后续工作包拆分

## WP-A — Production Acceptance

只做：

```text
production migration
real E2E
real routing
cache
fallback
budget
cancel/replay
benchmark
```

## WP-B — AI Runtime Correctness

只做：

```text
per-attempt budget
cache semantics
```

## WP-C — Gateway Consolidation

只做：

```text
central execution boundary
remove duplicate Video-specific orchestration
```

## WP-D — GenericProcessor

第一次重新进入产品功能扩展。

## WP-E — Source Watch

GenericProcessor 稳定后。

---

# 16. 推荐优先级结论

当前不建议：

```text
继续追加更多 AI 架构功能
```

推荐：

```text
先证明当前架构
→ 修正正确性边界
→ 收口 Gateway
→ 把基础设施兑换成 GenericProcessor
```

资源投入建议：

### 封板后第一阶段

```text
60% Production Acceptance
30% Runtime Correctness
10% Benchmark / next-phase design
```

### P0/P1 通过后

```text
80% GenericProcessor
20% regression / runtime maintenance
```

---

# 17. 明确非授权声明

任何 Agent 只要看到本文，都必须遵守：

```text
本文是 backlog，不是 execution plan。
```

除非用户明确指定某一项：

- 不创建代码；
- 不修改数据库；
- 不新增 API；
- 不改 UI；
- 不跑生产迁移；
- 不安装新依赖；
- 不自动实现下一优先级。

当前工作授权仍以用户最新指令为准。
