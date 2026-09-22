# Pipeline 运行韧性与实时进度升级方案

> 日期：2026-09-22
>
> 状态：已实施并部署；真实 Provider/fallback/deadline E2E 仍待外部验收
>
> 前置基线：`PIPELINE_PERFORMANCE_TOKEN_QWEN_ASR_MASTER_IMPLEMENTATION_PLAN.md` 的 WP0–WP8 已完成并部署
>
> 范围：模型 Attempt 实时活动、Job lease / watchdog、恢复顺序、`NOTE_REDUCE` 有界归纳、模型能力准入、任务运行态 UI 与统一验收
>
> 不包含：重做 ASR、Correction、Grounded Map、Replay、Retry/Circuit、Cache、Stage Policy、POI Resolver、截图批处理或 Core-first

## 0. 目标与 Definition of Done

本方案解决“Worker 存活、任务仍显示运行中，但长时间没有可解释进度”的剩余缺口。完成后必须同时满足：

1. 每次 Provider Attempt 在请求发出前即可查询，运行中有新鲜 heartbeat，结束后在同一审计记录上收口。
2. 活跃 Job 的 lease 周期续期；超时判断不依赖被同步调用阻塞的 Worker 主循环。
3. watchdog 裁决后的迟到结果不能更新 Job、Step、Artifact、Cache 或公开内容。
4. `OUTPUT_TRUNCATED / CONTEXT_TOO_LARGE` 先由当前 Stage 缩小输入，不把同一完整输入立即发送给 fallback。
5. `NOTE_REDUCE` 的输入、输出、分包、checkpoint 和总墙钟预算有硬边界；失败时仍可交付有 Evidence 的确定性 Note。
6. 自动路由不会优先选择已知不支持目标能力的 Profile；人工覆盖保留，但必须显式告警并留审计。
7. 任务详情能显示当前 Stage、主备路由、模型、分块、已用时、deadline 和最后活动，不再只有静态百分比。
8. 假挂起、截断、取消、Worker 重启、fallback 和迟到响应均有自动回归；桌面与 390px 页面通过 Browser 验收。

本方案不以“最终任务成功”替代以上门禁，也不以 Worker 全局心跳代替 Job 自身活动。

## 1. 当前事实与问题边界

### 1.1 已完成能力，不重复建设

继续复用：

- `ExternalCallAudit`、`SystemEvent`、`Job`、`JobStep`、`JobStepArtifact`；
- `AIWorkloadGateway`、`FallbackLLMProvider`、现有 Reliability Policy 和错误分类；
- Stage Policy、Budget、Request Cache、Canonical Grounded Map、runtime hint；
- Correction / Ground Map 的自适应分块与成功结果缓存；
- Replay、同一 Job ID 完整重跑、协作式取消；
- Core-first 内容物化、截图 enrichment、统一 Graduation Gate；
- Worker 全局 heartbeat 与任务详情现有 `ACTIVE / STALLED` 表达。

禁止新增第二套 Retry Engine、Circuit Breaker、Replay、Stage Decision、任务表或日志系统。

### 1.2 触发本方案的现场证据

`job_cd982dac77164ee283f68c5a4d290460` 在一次生产运行中表现为：

| Stage | 路由与结果 | 累计耗时 |
| --- | --- | ---: |
| `GROUND_MAP` | 本地 `qwen3.5:9b` 5 次失败，包含输出截断与无效 JSON | 1230.2 秒 |
| `GROUND_MAP` fallback | `deepseek-flash` 5 次完成 | 23.7 秒 |
| `NOTE_REDUCE` | 本地 `qwen3.5:9b` 输出截断 | 327.5 秒 |
| `NOTE_REDUCE` fallback | `deepseek-v4-flash` 输出截断 | 18.3 秒 |

任务最终通过确定性兜底完成，但长 Provider 请求期间没有新的 Step 进度；审计只在请求返回后出现。该案例证明：

- 最终可完成，不代表运行过程可观察；
- 全局 Worker heartbeat 正常，不代表当前 Job 正在推进；
- Input 已经来自 Grounded Evidence，不代表 `NOTE_REDUCE` 输入规模已经有界；
- 已有 Stage splitter，不代表 fallback 一定发生在 splitter 之后；
- 同步 Worker 主循环中的 stale recovery 不能实时裁决当前阻塞调用。

### 1.3 当前外部验收边界

Qwen 权重、Frozen Corpus、Context A/B、长视频、RAM / RTF、真实 fallback 和 WP8 毕业仍需按既有 Master Plan 由用户提供或明确授权。新方案的单元/集成测试使用可控 Fake Provider；不得因本方案自动重跑历史视频、调用真实付费 Provider、切换默认 ASR 或自动确认 POI。

## 2. 冻结语义

### 2.1 三种 heartbeat 必须分离

| 信号 | 含义 | 不得表示 |
| --- | --- | --- |
| Worker heartbeat | Worker 进程存活 | 当前 Job 有进展 |
| Job lease heartbeat | 当前 run fence 仍由该 Worker 持有 | Provider 已返回有效内容 |
| Attempt heartbeat | 某个已登记 Attempt 尚在 deadline 内 | Stage 已完成或结果可信 |

三者不得互相覆盖。任务停滞只读取 Job / Attempt 活动，服务健康只读取 Worker heartbeat。

### 2.2 进度必须来自真实工作量

- Chunk Stage 使用原始输入权重计算单调进度，例如已完成 Evidence 字符数 / 总 Evidence 字符数。
- 递归拆分不能让百分比倒退；左右子块共享原父块权重。
- 单次不可细分请求只显示“进行中 + 已用时 + deadline”，不得伪造百分比。
- Job 总进度与 `JobStep.progress` 继续分离。

### 2.3 run fence

每次领取 Job 时冻结：

```text
job_id
lease_owner
retry_count
started_at
```

以上组成当前 run fence。所有长调用返回后的写入必须再次确认：

```text
Job.status == RUNNING
lease_owner 未变化
retry_count 未变化
started_at 未变化
```

任何一项不匹配即视为迟到结果：不得写 Cache、Artifact、Step、Content 或将 Job 改回成功，只记录脱敏的 `job.run.late_result_discarded`。

默认复用现有字段，不新增 migration。只有实现时证明现有组合无法形成可靠 fence，才允许新建追加式 Alembic migration；不得修改历史 migration。

## 3. WP0 — 冻结实时活动契约

### 3.1 Attempt 生命周期

每次实际 Provider 请求采用同一条 `ExternalCallAudit`：

```text
RUNNING
→ COMPLETED | FAILED | CANCELLED | TIMED_OUT | DISCARDED
```

请求发出前创建并提交 `RUNNING`；返回后更新原记录，不新增一条“结果记录”。已有查询与历史 `COMPLETED / FAILED` 记录保持兼容。

`request_meta_json` 至少写入：

```json
{
  "stage": "NOTE_REDUCE",
  "step": "GENERATE_AI_NOTE",
  "provider": "ollama",
  "model": "qwen3.5:9b",
  "route": "primary",
  "attempt": 1,
  "chunk_index": 1,
  "chunk_count": 3,
  "split_path": "root.L",
  "input_chars": 0,
  "estimated_input_tokens": 0,
  "timeout_seconds": 300,
  "deadline_at": "UTC timestamp",
  "run_fence": {
    "lease_owner": "...",
    "retry_count": 0,
    "started_at": "UTC timestamp"
  }
}
```

Secret、Prompt 正文、Cookie、URL Token 和 API Key 不进入审计。

### 3.2 Attempt heartbeat

- heartbeat 使用独立 `SessionLocal`，不得跨线程复用 Pipeline Session；
- 默认间隔取 `min(worker_heartbeat_seconds, worker_lease_seconds / 3)`；
- 只更新同一 Attempt 的 `updated_at`、对应 Job 的 `heartbeat_at` 和 lease deadline；
- heartbeat 不追加重复 `SystemEvent`，避免日志膨胀；
- `model.attempt.started`、终态和 deadline exceeded 才写事件；
- heartbeat 到达 deadline 后停止续期，由 watchdog 裁决。

### 3.3 API 契约

`GET /api/jobs/{id}` 增加可空的 `active_attempt`：

```json
{
  "id": "xca_...",
  "stage": "NOTE_REDUCE",
  "provider": "ollama",
  "model": "qwen3.5:9b",
  "route": "primary",
  "chunk_index": 1,
  "chunk_count": 3,
  "split_path": "root",
  "started_at": "...",
  "heartbeat_at": "...",
  "deadline_at": "...",
  "elapsed_seconds": 42,
  "timeout_seconds": 300
}
```

API 只返回脱敏字段。WebSocket 沿用现有 Job stream；Attempt 开始、终态和 Step 进度变化触发刷新。

### 3.4 WP0 验收

- Provider Fake 阻塞时，1 秒内可从 Job API 和日志 API 看到 `RUNNING` Attempt；
- heartbeat 间隔不超过配置值的 1.5 倍；
- 同一请求从开始到结束只有一个 audit ID；
- 历史审计和现有 AI Usage 聚合不回归；
- Prompt/Secret 脱敏测试通过。

## 4. WP1 — Lease 续期、watchdog 与迟到写入隔离

### 4.1 Lease 续期

活跃 run 在每次 Attempt heartbeat、Chunk 完成和长外部子进程活动时续期：

```text
lease_expire_at = now + worker_lease_seconds
```

续期必须带 run fence 条件；旧 run 不能续期新 run 的 lease。不存在活跃 Job 时不写数据库。

### 4.2 独立 watchdog

watchdog 独立于同步 `process_job()` 主循环，使用独立线程和数据库 Session，周期检查：

1. `RUNNING` Attempt 是否超过 `deadline_at + grace_seconds`；
2. `RUNNING` Job 是否无 active Attempt 且自身活动超过 `job_attempt_timeout_seconds`；
3. lease 是否过期且 owner 对应的 Worker heartbeat 已失效；
4. 当前 run fence 是否仍匹配。

watchdog 只对匹配 fence 的 run 原子写入终态。错误语义：

| 场景 | Job / Attempt 结果 | 错误码 |
| --- | --- | --- |
| Provider deadline 超过 | Job 当前 Step 失败；Attempt `TIMED_OUT` | `AI_PROVIDER_TIMEOUT` |
| Job 无任何活动超过总阈值 | Job / Step `FAILED` | `ATTEMPT_TIMEOUT` |
| Worker 消失且 lease 过期 | Job / Step `FAILED` | `WORKER_LEASE_EXPIRED` |
| 用户已取消 | Attempt `CANCELLED`；Job 保持 `CANCELLED` | 不改写为失败 |

不得静默重新领取或自动重跑。

### 4.3 对底层调用的处理

- HTTP Provider 继续以实际 `httpx` timeout 为硬边界；watchdog 不创建第二个并发请求。
- 可控子进程（Qwen Runner、FFmpeg、yt-dlp）超过 deadline 时终止子进程并清理临时资源。
- 对无法强制中断的在途调用，先终止 Job 所有权；调用迟到返回后由 run fence 丢弃。
- watchdog 不自动重启 LaunchAgent；若执行线程未恢复，运行监控显示 `EXECUTOR_DEADLINE_EXCEEDED`，由用户决定受控重启。

### 4.4 恢复与启动清理

Worker 启动时：

- 将已过 deadline 且没有有效 owner 的 `RUNNING` Attempt 收口为 `TIMED_OUT` 或 `DISCARDED`；
- 不改写已有 `COMPLETED / FAILED` 审计；
- 不自动 Replay；
- 继续遵守历史 Artifact、Source、Transcript 和 Content 身份边界。

### 4.5 WP1 验收

- 活跃任务不存在过期 lease；
- Fake Provider 永久挂起时，watchdog 可在 deadline + grace 内结束该 run；
- watchdog 结束后 Provider 再返回，Job/Step/Cache/Artifact/Content 均不变化；
- 用户取消与 watchdog 同时发生时，`CANCELLED` 优先且只产生一个终态；
- Worker 崩溃重启后不存在永久 `RUNNING` Attempt；
- 全局 Worker heartbeat 正常时，Job 超时仍可被正确裁决。

## 5. WP2 — Stage 恢复优先级与 fallback 裁决

### 5.1 单一恢复矩阵

在现有 `FallbackLLMProvider` 增加小型 `fallback_decider` 或等价回调；它只决定“错误交回 Stage 还是切模型”，不建立新 Retry Engine。

| 错误 | 当前模型动作 | fallback 条件 |
| --- | --- | --- |
| `OUTPUT_TRUNCATED` | 交回 Stage splitter，缩小当前输入 | 已缩到最小合法单元仍失败 |
| `CONTEXT_TOO_LARGE` | 交回 Stage splitter，缩小当前输入 | 已缩到最小合法单元仍失败 |
| `INVALID_JSON / SCHEMA_INVALID` | 安全本地修复；按 Profile 最多一次 JSON retry | 修复/重试耗尽且 fallback 合格 |
| `EMPTY_RESPONSE / TIMEOUT / NETWORK / 5XX` | 按现有 Reliability Policy | 同模型重试耗尽且 fallback 合格 |
| `RATE_LIMIT / QUOTA / POLICY / AUTH` | 不放大同模型请求 | 有合格 fallback 时切换，否则 `NEEDS_USER` |
| `AI_BUDGET_EXCEEDED` | 立即停止 | 不 fallback |

### 5.2 Stage 所有权

Correction、Ground Map、`NOTE_REDUCE` 声明自己可处理的 shrink 错误。Provider 层遇到这些错误时必须先返回 Stage；不得在 Stage splitter 看见错误前把原输入发给 fallback。

记录 `recovery`：

```text
split_same_model
json_repair
retry_same_model
fallback_model
deterministic_fallback
```

### 5.3 墙钟与 Attempt 预算

在 Stage Policy JSON 中追加可选参数，不需要 migration：

```text
wall_time_seconds
max_attempts
```

- `timeout_seconds` 仍是单次请求边界；
- `wall_time_seconds` 是整个 Stage 边界；
- `max_attempts` 同时计入 primary、retry、split 与 fallback；
- 达到 Stage 边界后不再开始新请求，转入该 Stage 的安全终态或确定性 fallback；
- Budget 与 Quality Gate 仍优先，不能为了“成功”突破硬预算。

### 5.4 WP2 验收

- 截断调用序列必须是 `primary full → primary split`，不得是 `primary full → fallback full`；
- `full_input_fallback_after_truncation = 0`；
- JSON 错误不会触发递归二分；
- Stage Attempt 总数和墙钟不超过 Policy；
- primary/fallback 的 Profile 参数、Token 和错误审计保持独立。

## 6. WP3 — `NOTE_REDUCE` 有界 Evidence Pack 与渐进交付

### 6.1 输入不等于“已经足够紧凑”

`NOTE_REDUCE` 继续只消费 Canonical Grounded Evidence，不重新读取整篇 Transcript；但必须在请求前执行确定性压缩与分包：

1. 按 Segment ordinal、Mention ID 稳定排序；
2. 合并重复事实、重复地点和重复 supporting quote；
3. 每个事实只保留必要 Evidence 指针与有界逐字引文；
4. 根据 Stage `max_input_tokens`、Profile working context 和输出保留量计算包大小；
5. 绝不通过截断 JSON 字符串满足上限。

Evidence 不得丢失：所有 Note 事实仍能回到原 Segment、Quote 和 Mention。

### 6.2 两级归纳

当一个包超过边界：

```text
Canonical Evidence
→ deterministic packs by place / time range
→ per-pack Note sections
→ bounded final merge of section summaries
```

最终 merge 不再携带全部原始 quote，只携带已验证 Section、Evidence ID 和必要标题信息；服务端在 merge 后重新验证所有引用均属于输入 Artifact。

### 6.3 NOTE_REDUCE runtime hint

在现有 runtime hint JSON 中按模型追加：

```json
{
  "safe_max_input_tokens": 6000,
  "safe_max_facts": 40,
  "safe_max_quotes": 80,
  "safe_max_sections": 12
}
```

示例数字只是结构说明，真实默认值由 Frozen Benchmark 决定。Hint 只能收紧，不能跨模型共享；Profile context 或 Prompt/Schema 版本变化时重新评估。

### 6.4 checkpoint

- 每个 pack 使用稳定 semantic hash 进入现有 Request Cache；
- Pack 成功立即可复用；后续失败只处理剩余 pack；
- Replay 不重复已完成 pack；
- 最终 merge 失败时，确定性拼接已完成 Section，不丢弃成功结果；
- 不新增 Note Reduce 专用数据库表。

### 6.5 渐进和降级交付

当 Grounded Evidence 已完成但 `NOTE_REDUCE` 达到 Stage 软边界：

- 不开始新的可选模型 Attempt；
- 使用现有确定性 Section/提纲生成 Evidence-backed Note；
- Core-first 立即物化并标记 `note_generation_mode=DETERMINISTIC_FALLBACK`；
- 后续人工触发的 Note Profile 重生成可以复用 Grounded Artifact 和成功 pack；
- 不自动后台补跑 Provider。

### 6.6 WP3 验收

- 每个请求估算输入不超过 Stage/Profile 硬上限；
- `NOTE_REDUCE` 截断时先拆 pack，不发送完整 pack 给 fallback；
- 任一 pack 失败不丢失其他成功 pack；
- merge 失败仍可交付 Note，且 unsupported fact 为 0；
- Evidence coverage 不低于 Master Plan baseline；
- Profile 重生成复用 Grounded Artifact，不重扫 Transcript。

## 7. WP4 — Stage 模型能力准入

### 7.1 自动路由

AUTO 和未显式指定 Profile 的 `LOCAL_FIRST / REMOTE_FIRST`：

- 排除 `enabled=false`；
- 排除目标 capability 明确为 `FAIL` 的 Profile；
- 优先 `probe_results[capability] == PASS`；
- `NOT_TESTED` 只能在没有 PASS 候选时作为保守候选，并写入 `ai.route.unverified_profile`；
- primary 与 fallback 分别校验，不能因为 primary 合格就跳过 fallback 准入。

### 7.2 人工显式覆盖

用户显式选择已知 `FAIL` 或未测试 Profile 时，不静默替换：

- Settings 显示中文告警；
- 保存时要求显式确认“允许未验证模型”；
- Job payload 记录本次 override，不修改历史 Job；
- 写入 `ai.route.capability_override`；
- 仍受 Budget、timeout、Attempt 和 Evidence 门禁约束。

不得为了验证能力在生产 Job 中自动 Probe 或调用真实 Provider。

### 7.3 WP4 验收

- `GLOBAL_SYNTHESIS` 已知失败的 Profile 不进入自动 `NOTE_REDUCE` 路由；
- `STRUCTURED_EXTRACTION` 已知失败的 Profile 不进入自动 Ground Map 路由；
- 显式覆盖可追溯且不会修改全局默认；
- 无合格模型时进入确定性 fallback 或 `NEEDS_USER`，不循环换模型。

## 8. WP5 — 任务详情与运行监控

### 8.1 任务详情

运行卡片显示：

```text
当前步骤：生成 AI 笔记
当前调用：主模型 · Ollama · qwen3.5:9b
分块：2 / 5（拆分 root.L）
已运行：2 分 18 秒
单次上限：5 分钟
最后活动：18 秒前
```

没有真实分块时隐藏分块字段。不得展示 Secret、完整 Provider URL 或内部 Prompt。

### 8.2 状态语义

| 状态 | UI 文案 |
| --- | --- |
| Attempt heartbeat 新鲜 | 模型正在处理 |
| Job 活动超过 LLM 预警阈值但未到 deadline | 本次调用耗时较长 |
| Attempt heartbeat 过期或超过 deadline | 当前调用可能停滞 |
| Worker heartbeat 正常但 executor deadline exceeded | Worker 进程在线，但执行任务已超时 |
| fallback 已发生 | 主模型失败，正在使用备用模型 |
| 确定性交付 | 模型归纳不可用，已交付基于证据的基础笔记 |

页面不提供运行中“重试”捷径；取消仍走协作式停止，完整重跑仍复用服务端操作能力。

### 8.3 日志页

- `RUNNING` Attempt 置顶显示 elapsed/deadline；
- 同一 Attempt 更新状态，不重复成多行；
- 清楚区分 retry、split、fallback 和 deterministic fallback；
- deadline exceeded、fence reject 和 discarded late result 可复制脱敏 JSON；
- 旧审计缺字段时显示“历史记录未采集”，不得推断为 0。

### 8.4 WP5 验收

- 桌面与 390×844 均无横向溢出；
- WebSocket 可用时实时更新，断开后 3 秒轮询仍能更新；
- 控制台无相关 warning/error；
- 长模型调用至少每个 heartbeat 周期刷新“最后活动”；
- 终态不再显示活跃 Attempt。

## 9. WP6 — 统一回归与 Graduation Gate

### 9.1 自动化场景

至少覆盖：

1. primary 成功；
2. primary 截断后同模型拆分成功；
3. primary 最小包仍截断后合格 fallback 成功；
4. primary/fallback 均截断后确定性 Note 交付；
5. JSON 修复成功；
6. JSON retry 后 fallback；
7. Provider 永久挂起；
8. deadline 前用户取消；
9. watchdog 与取消竞争；
10. watchdog 后迟到成功响应；
11. Worker 崩溃与重启清理；
12. 未验证 Profile 自动路由与人工覆盖；
13. Note 多 pack 中间失败与 Replay；
14. WebSocket 断开后的轮询显示。

### 9.2 硬门禁

| 指标 | 门禁 |
| --- | --- |
| Attempt 可见延迟 | 请求发出后不超过 1 秒 |
| Attempt heartbeat gap | 不超过配置间隔的 1.5 倍 |
| 活跃 Job 过期 lease | 0 |
| 截断后完整输入直接 fallback | 0 |
| Stage Attempt / Wall Time 超预算 | 0 |
| watchdog 后迟到写入 | 0 |
| Replay 重做成功 pack | 0 |
| Note unsupported fact | 0 |
| Evidence coverage | 不低于 Frozen baseline |
| Critical hallucination | 0 |
| 错误自动确认 POI | 0 |

性能改善继续输出 P50/P95、fallback amplification、Time To First Useful Note，不以单个样本替代 Frozen Benchmark。

### 9.3 验证命令层级

1. 目标单测：Audit 生命周期、fence、watchdog、fallback 顺序、Note pack、路由准入；
2. 目标后端集成测试：Fake Provider + SQLite；
3. 前端 Vitest / TypeScript / build；
4. 工作包完成后一次全量后端、Ruff、前端 verify、`git diff --check`；
5. UI 行为改变后执行桌面与 390px Browser 验收；
6. 真实 Provider / 视频只在用户明确授权后按 Frozen Benchmark 执行。

## 10. 实施顺序与提交边界

严格按以下顺序：

```text
WP0 Attempt 生命周期
→ WP1 Lease / watchdog / run fence
→ WP2 Stage 恢复顺序
→ WP3 NOTE_REDUCE 有界归纳
→ WP4 能力准入
→ WP5 UI / 运行监控
→ WP6 统一毕业
```

建议提交边界：

1. `jobs: persist live model attempts and renew leases`
2. `jobs: add fenced watchdog recovery`
3. `ai: enforce stage recovery before fallback`
4. `video: bound and checkpoint note reduction`
5. `ai: gate automatic routes by capability evidence`
6. `ui: show live attempt state and deadlines`
7. `test: graduate pipeline runtime resilience`

每个提交保持目标测试可独立通过；不得把部署、真实 Provider 验收或生产配置修改混入源码提交。

## 11. 主要修改面

| 文件/模块 | 预期修改 |
| --- | --- |
| `providers/llm.py` | Attempt begin/end hook；Stage-aware fallback decider |
| `ai/gateway.py` | Attempt context、run fence、Stage recovery ownership |
| `ai/reliability.py` | 复用错误分类；不新建 Retry 系统 |
| `services/jobs.py` | 条件 lease 续期、fence 校验、stale 收口 |
| `worker.py` | 独立 watchdog；不复用 Worker heartbeat 充当 Job 活动 |
| `services/grounded_map.py` | 明确 splitter 优先与加权 Step 进度 |
| `services/video_support.py` | `NOTE_REDUCE` pack、checkpoint、确定性降级 |
| `ai/cost_router.py` / Model Registry | capability eligibility 与 override 审计 |
| `api/router.py` | `active_attempt`、executor 状态、脱敏日志 |
| `frontend/src/features/tasks/` | Attempt 运行卡片与步骤进度 |
| `frontend/src/components/UtilityPages.tsx` | RUNNING Attempt、deadline、recovery 链 |
| `scripts/capture_video_benchmark.py` | 新增静默间隔、lease、deadline、late write 指标 |
| `backend/tests/`、前端测试 | 每个 WP 的回归与竞争条件测试 |

默认不新增数据库表。若实现时确需新字段，必须新建 migration，并保持旧记录可读。

## 12. 不实施内容

- 不自动重跑历史 Job；
- 不自动调用真实 Provider、视频或 Qwen 权重；
- 不切换默认 ASR 或默认模型；
- 不把 heartbeat 当作模型输出进度；
- 不为运行进度引入消息队列或第二 Worker 系统；
- 不用无限 heartbeat 掩盖超过 deadline 的挂起调用；
- 不在 watchdog 中自动重启 LaunchAgent；
- 不删除或覆盖历史 Audit、Artifact、Note Version；
- 不为节省 Token 降低 Evidence coverage、地点召回或自动确认安全门禁。

## 13. 最终交付状态

完成本方案后，运行链路应为：

```text
Job leased with run fence
→ Attempt persisted as RUNNING
→ lease + Attempt heartbeat
→ Stage progress / split / checkpoint visible
→ same-provider recovery before fallback
→ bounded NOTE_REDUCE or deterministic Note
→ Core-first materialization
→ Attempt and Job terminalized once
→ late results rejected by fence
```

用户看到的不再是“进度长时间不动但不知道是否还活着”，而是可验证的当前调用、分块、耗时、deadline、恢复动作与安全终态。
