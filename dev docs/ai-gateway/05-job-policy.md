# 单次任务策略、API 与 Cache Key

> 来源：ai-gateway/AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md，原章节 41J–41S（正文保留，2026-09-03 分篇）。返回 [主题索引](AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md)。本篇是契约/规划，不是已实施清单；当前结论见 [实施状态](../IMPLEMENTATION_STATUS.md)，安全与回归见 [冻结清单](../REGRESSION_AND_CHANGE_GUARD.md)。裸文档路径均以 dev docs/ 为基准。只读取命中章节及其必要约束。

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
