# Pipeline Step Replay v0.4.4

> 实施状态：源码、自动测试、在线库 `0007`、服务重启与真实步骤续跑均已完成。

> 状态：已实施并验收
> 更新日期：2026-08-24
> 适用入口：任务详情、运行日志 ERROR/CRITICAL 详情
> 标注设计：`design/ui/v0.4.4/pipeline-step-replay-and-delete-pc-annotated.png`

---

# 1. 正确语义

“从错误恢复”不是把所属任务从第一步重新执行。Pipeline 在运行期间暂存每个已完成步骤的可复用中间产物；某一步产生 ERROR 时，只要所需中间产物仍在有效期内，用户可以从该失败步骤重新执行，并让所有后续步骤顺次运行。失败步骤之前已经完成的步骤不再执行。

```text
STEP A COMPLETED ─┐
STEP B COMPLETED ─┼─ 复用，不重跑
STEP C FAILED    ─┘
        ↓ 用户确认“从此步骤继续”
STEP C RETRYING
→ STEP D
→ STEP E
→ ...
```

中间产物到期清理后，步骤级续跑不可用；用户只能选择“完整重跑”。

---

# 2. 中间产物生命周期

默认复用窗口使用现有 `video_cache_ttl_hours=24`，允许未来配置但第一版不在 UI 暴露任意值。

## 2.1 立即清理

- 临时 Cookie 文件；
- API Key/Authorization 临时值；
- 未登记的 scratch 文件；
- 被取消的未完成写入。

## 2.2 24 小时 Replay Cache

- canonical URL 与 metadata Snapshot；
- 平台字幕/ASR Transcript Version；
- corrected Transcript Version；
- Note 分块 checkpoint；
- Place extraction JSON；
- POI candidates；
- Screenshot Plan；
- 已下载且校验通过的音频/截图视频；
- 已生成但尚未成为最终投影的截图/派生文件。

## 2.3 持久结果

- Source/Snapshot/Transcript/Segment；
- AINote/Version/Section；
- Claim/Evidence；
- PlaceMention/Place/PlaceNote；
- READY Screenshot/CoverAsset；
- 审计事件。

`CLEAN_CACHE` 不能在任务结束时立即删除 Replay Cache；它只清理 secrets/scratch，并登记 replayable_until。Worker 定时清理在 TTL 到期后删除 Replay Cache。

---

# 3. Step Artifact Manifest

每个可重放步骤保存：

```text
job_id
attempt_id
step_name
artifact_type
artifact_ref/path
input_hash
content_hash
schema_version
producer_version
created_at
replayable_until
status
```

Artifact 状态：`AVAILABLE / EXPIRED / INVALIDATED / MISSING`。

只有输入哈希、Schema、Producer Version 与依赖 Artifact 均有效时才能复用。模型、Prompt 或用户输入变化导致依赖失效时，服务端自动把真正受影响的最早步骤作为 replay_from_step；前端不能绕过。

---

# 4. 可续跑判定

步骤级续跑必须同时满足：

1. Job 当前为 `FAILED / NEEDS_USER / PARTIAL_SUCCESS`，且没有活跃 lease；
2. ERROR/CRITICAL 事件规范关联该 Job 和失败 Step；
3. 请求 step_name 等于服务端判定的最早失败/失效步骤；
4. 该步骤所有上游 Artifact 均 AVAILABLE 且未过期；
5. Source、模型路由、Prompt、Parser 和配置没有使上游输入哈希失效；
6. 没有另一个 replay 正在排队或执行。

不满足时返回不可续跑原因：

- `REPLAY_ARTIFACT_EXPIRED`
- `REPLAY_ARTIFACT_MISSING`
- `REPLAY_INPUT_CHANGED`
- `REPLAY_STEP_MISMATCH`
- `REPLAY_ALREADY_RUNNING`
- `REPLAY_LEASE_ACTIVE`

---

# 5. 执行行为

提交步骤级续跑后：

- 创建同一 Job 的新 Attempt；
- 上游已完成步骤记录为 `REUSED`，保留原始 started/finished 和 Artifact 引用；
- 失败步骤及其所有下游步骤重置为 `PENDING`；
- 下游旧中间输出标记 `INVALIDATED`，最终版本不原地覆盖；
- `current_step` 设置为 replay_from_step；
- Worker 从该步骤开始顺序执行；
- 写入 `job.step_replay.queued/started/completed/failed` 审计链；
- 新 Attempt 再失败时保留旧 ERROR 和旧 Attempt。

完整重跑是不同动作：从 Pipeline 首个步骤开始，可按缓存策略复用，但不保证跳过任何步骤。

取消不是失败步骤。步骤续跑仍只在有明确失败步骤与有效 Artifact 时可用。完整重跑是独立动作：任何状态下均可从右上角提交；若原 Job 正在排队或运行，服务端先将其标记为协作式取消，再创建新的 `QUEUED` Job。单 Worker 会在旧流程到达安全边界并释放 lease 后领取新任务，避免两个流程并发写同一结果。

---

# 6. API

```text
GET /api/jobs/{job_id}/replay-options
POST /api/jobs/{job_id}/retry-from-step
POST /api/jobs/{job_id}/retry-full
```

`GET /api/jobs/{job_id}/replay-options` 还返回：

```json
{
  "full_replay_available": true,
  "full_replay_reason": "将停止当前流程并创建新的完整任务"
}
```

右上角始终展示“从头重新运行”。失败恢复卡仅在 `step_replay_available=true` 时展示步骤续跑按钮；不可续跑时只展示原因并引导用户使用右上角完整重跑，不重复放置完整重跑按钮。

Replay Options：

```json
{
  "step_replay_available": true,
  "replay_from_step": "GENERATE_AI_NOTE",
  "replayable_until": "...",
  "remaining_seconds": 53210,
  "reused_steps": ["VALIDATE_LINK", "FETCH_METADATA", "FETCH_SUBTITLE"],
  "rerun_steps": ["GENERATE_AI_NOTE", "EXTRACT_TRAVEL_FACTS", "..."],
  "reason": null
}
```

步骤续跑请求：

```json
{
  "step_name": "GENERATE_AI_NOTE",
  "source_event_id": "evt_..."
}
```

服务端不接受任意 from_step。`step_name` 只是用户确认值，最终必须与 Replay Options 一致。

---

# 7. 任务详情与日志 UI

失败 Step 行显示：

- “从此步骤继续”；
- “将复用前 N 个步骤”；
- “中间产物保留至 … / 剩余 …”；
- 将重新执行的下游步骤列表；
- 完整重跑作为次级动作。

日志 ERROR/CRITICAL 抽屉不再使用“重跑所属任务”作为唯一动作。规则：

- Artifact 可用：主按钮“从错误步骤继续”；
- Artifact 已过期：不显示步骤续跑按钮，说明“中间产物已清理”，引导使用右上角完整重跑；
- Job 已运行/完成：不显示过期 ERROR 的续跑按钮；
- 点击后确认框明确列出复用步骤和重跑步骤。

页面不得让用户逐个手动点击后续步骤；Worker 自动顺次执行。

---

# 8. 验收

1. C 步骤失败且 A/B Artifact 有效时，续跑只执行 C 及下游；
2. 上游步骤显示 REUSED，不产生新的外部请求；
3. 下游旧输出被 INVALIDATED，新版本不覆盖历史；
4. 24 小时内 Replay Options 返回可用和剩余时间；
5. TTL 到期后返回 `REPLAY_ARTIFACT_EXPIRED`，只能完整重跑；
6. Cookie/scratch 立即清理，Replay Cache 保留到 TTL；
7. 输入/模型/Prompt 变化时从服务端计算的最早失效步骤开始；
8. 日志按钮语义为“从错误步骤继续”，不再误导为整任务重跑；
9. 重复点击、活跃 lease、错误事件不匹配均被拒绝；
10. 审计可追踪旧 Attempt、来源 ERROR、复用 Artifact 和新 Attempt。
11. 运行中点击右上角完整重跑会取消旧 Job、创建新 Job，并导航到新任务；旧 Worker 在安全边界停止后再领取新 Job。
12. 复用 canonical VideoAsset 时，步骤续跑以 `FETCH_METADATA` Artifact 的 `video_asset_id` 定位资产，不假设当前 Capture Source 与资产原 Source 相同。
