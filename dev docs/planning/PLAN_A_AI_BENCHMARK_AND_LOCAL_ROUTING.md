# PLAN A — AI Benchmark 与本地模型路由闭环

> 目标：先建立可靠的 AI 能力度量体系，再决定哪些 Stage 可以稳定交给本地 Ollama 模型。  
> 对应方向：**11 本地模型接管流水线、12 视频 Benchmark 完成**。  
> 本 Plan 不负责修改地图、POI 产品逻辑或推荐系统。

---

## 1. 目标

完成一套可重复执行的模型 Benchmark，使系统能够回答：

1. 每个模型适合执行哪些 Stage；
2. 本地模型与远程模型质量差距；
3. 本地模型是否达到替代远程模型的最低门槛；
4. 模型切换后 Schema、Evidence、实体召回是否退化；
5. Token、延迟、本地资源消耗分别如何；
6. Vision 模型未来能否使用同一 Benchmark 框架评估。

最终形成：

```text
Model
↓
Capability Probe
↓
Stage Benchmark
↓
Quality Gate
↓
Stage Policy Recommendation
```

Benchmark 负责给出建议，不自动修改生产默认模型。

---

# 2. 执行前最小读取

首先阅读：

```text
AGENTS.md
dev docs/CODEX_CONTEXT.md
dev docs/IMPLEMENTATION_STATUS.md
dev docs/CURRENT_HANDOFF.md
dev docs/ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md
```

然后只按需要定位：

```text
dev docs/ai-gateway/01-architecture-models.md
dev docs/ai-gateway/03-pipeline-providers.md
dev docs/ai-gateway/04-stage-policy.md
dev docs/benchmark/
scripts/run_ai_benchmark.py
backend/src/zhijian/ai/
backend/tests/
```

禁止扫描 `COMPLETE_PROJECT_SPEC.md`。

---

# 3. WP-A1：统一 Benchmark Schema

## 目标

把目前基础 Capability Probe 和视频 Workflow Golden 统一成明确的测试契约。

定义 Stage：

```text
CLASSIFY
STRUCTURED_EXTRACT
ENTITY_EXTRACT
TRANSCRIPT_CORRECT
NOTE_GENERATE
PLACE_EXTRACT
PLACE_INSIGHT
PLACE_AGGREGATE
POI_CONTEXT_RANK
VISION_FACT
```

其中 `VISION_FACT` 本 Plan 只定义接口和 Schema，不要求真实运行。

每个 Benchmark Case 至少包含：

```text
case_id
stage
input_fixture
expected_schema
expected_entities
expected_evidence
forbidden_claims
baseline_model
tags
```

每次运行结果至少包含：

```text
provider
model
location
stage
schema_valid
entity_recall
evidence_coverage
hallucination_count
latency_ms
prompt_tokens
completion_tokens
total_tokens
error_type
```

### 要求

- JSON 输出必须有正式 Schema；
- Schema 校验独立于模型调用；
- Fixture 不依赖生产数据库；
- Golden 可版本化；
- Benchmark 不直接调用真实视频下载。

---

# 4. WP-A2：扩展 Capability Probe

当前 Probe 不再只判断“能否返回结果”，而要判断是否达到 Stage 使用条件。

至少测试现有本地模型：

```text
qwen2.5:7b
qwen3:8b
qwen3.5:9b
```

若运行环境存在其他 Ollama 模型，允许发现但不得自动纳入生产。

每个模型输出能力矩阵：

| Stage | PASS | DEGRADED | FAIL | NOT_TESTED |
|---|---|---|---|---|

重点覆盖：

- JSON Schema 遵循；
- 中文地点实体抽取；
- Transcript 校对；
- 长文本结构化；
- Evidence 引用；
- Place Insight；
- 多段内容聚合。

---

# 5. WP-A3：视频 Workflow Benchmark

复用现有：

```text
dev docs/benchmark/video-workflow-golden-v1.json
```

补齐评估维度：

### Extraction

- Place recall
- Place precision
- Dish/experience recall
- 时间窗口 recall

### Evidence

- Segment 是否存在；
- source quote 是否有效；
- Claim 是否可追溯；
- 禁止无来源事实。

### Knowledge

- 推荐菜；
- 核心看点；
- 最佳时间；
- 注意事项；
- 作者观点。

### POI

只评价：

```text
候选召回
正确候选排名
错误自动确认率
```

本阶段不改变 POI Resolver。

---

# 6. WP-A4：模型对比矩阵

实现统一结果输出：

```text
benchmark-results/
  run-YYYYMMDD-HHMM/
    metadata.json
    raw-results.jsonl
    summary.json
    summary.md
```

`summary.md` 自动生成：

| Model | Stage | Schema | Recall | Evidence | Hallucination | Latency |
|---|---|---:|---:|---:|---:|---:|

并输出：

```text
RECOMMENDED
ACCEPTABLE
REMOTE_PREFERRED
UNSUPPORTED
```

禁止显示没有指标依据的“综合评分 92 分”。

---

# 7. WP-A5：Stage Routing Recommendation

Benchmark 只生成建议：

```json
{
  "PLACE_EXTRACT": {
    "recommended": "qwen3.5:9b",
    "fallback": "remote",
    "reason": []
  }
}
```

不要自动修改：

```text
默认模型
Stage Policy
生产 Profile
Provider Key
```

只有用户明确授权后才能实际切换。

推荐逻辑：

```text
满足质量门槛
→ 比较本地/远程成本
→ 满足本地延迟与资源约束
→ 推荐 LOCAL_FIRST

质量不足
→ REMOTE_FIRST / REMOTE_ONLY
```

---

# 8. WP-A6：Benchmark 发布门禁

至少继续保留现有指标：

```text
Schema >= 95%
Evidence coverage >= 90%
严重幻觉 = 0
实体/地点召回不得低于 Baseline
```

新增：

```text
POI Top-N candidate recall
Place Insight coverage
Visit-window recall
JSON repair rate
平均/P95 latency
```

任何 Candidate 未达到质量门槛，不得因为 Token 更低而推荐替代 Baseline。

---

# 9. WP-A7：真实 E2E Harness

实现真实 E2E 的采集能力，但不要擅自运行生产任务。

支持：

```text
平台字幕样本
ASR 样本
Local Provider
Remote Provider
Cache
Force regenerate
Fallback
Replay
Cancel
```

如果缺少：

```text
合法测试视频
远程 Key
Vision Profile
```

则：

```text
代码与测试完成
真实验收标记 BLOCKED_EXTERNAL
```

不得以 Mock 宣称真实 E2E 已完成。

---

# 10. 测试

新增/更新：

```text
Benchmark Schema tests
Capability Probe tests
Golden evaluator tests
Stage recommendation tests
Regression tests
```

先执行目标测试。

Plan 完成后执行：

```bash
.venv/bin/pytest backend/tests
pnpm --dir frontend verify
```

若本 Plan 未修改前端，可不增加新的 UI 行为测试。

---

# 11. 完成标准

满足以下条件才关闭 Plan：

- [ ] Benchmark Case 有正式 Schema
- [ ] Stage 能力矩阵完整
- [ ] 3 个现有 Ollama 模型可生成可比较结果
- [ ] 视频 Golden 可重复评分
- [ ] Evidence/实体/地点均有指标
- [ ] Routing Recommendation 可生成
- [ ] 不自动修改生产默认模型
- [ ] 真实 E2E Harness 可运行
- [ ] 外部条件缺失时正确标记 BLOCKED_EXTERNAL
- [ ] 全量测试通过
- [ ] 更新 IMPLEMENTATION_STATUS.md

---

# 12. 建议提交拆分

```text
feat: formalize ai benchmark schemas
feat: extend local model capability probes
feat: add stage benchmark scoring
feat: add model routing recommendations
test: expand video workflow benchmark coverage
docs: record ai benchmark implementation status
```

完成本 Plan 后，再进入 `PLAN_B_PLACE_POI_KNOWLEDGE_QUALITY.md`。