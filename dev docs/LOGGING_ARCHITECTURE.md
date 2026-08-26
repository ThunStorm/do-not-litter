# 日志系统设计架构

版本：v0.2，更新日期：2026-08-24，适用部署：Mac mini 单节点。

## 1. 目标与边界

日志系统解决三类问题：一是回答“服务是否真的在运行”；二是回答“某次投递为什么成功、失败或等待确认”；三是记录影响安全与结果的用户操作。第一版不引入 Elasticsearch、Loki、云日志或遥测 SaaS，所有日志保存在 Mac mini 本地。

日志不存储配对码、Session Cookie、API Key、请求正文、上传文件内容与个人档案完整值。URL 只在 Source 数据域保存，HTTP 运行日志仅记录路径，不记录查询串和请求体。

## 2. 双层日志模型

### 2.1 运行日志 JSONL

API 与 Worker 分别写入 `data/logs/api.jsonl` 和 `data/logs/worker.jsonl`。每行一个 JSON 对象，字段包括 `timestamp`、`level`、`component`、`message`，可选字段包括 `request_id`、`event_type`、`duration_ms`、`status_code`、`path`、`job_id` 和异常摘要。

运行日志用于开发排障和服务恢复。单文件 10 MiB，保留 5 个轮换文件；LaunchAgent 的 stdout/stderr 仍写入独立文件，作为 Python 日志子系统失效时的兜底。

### 2.2 审计事件 SQLite

`system_events` 表保存用户能理解且需要长期查询的事件：配对成功/失败、配对码轮换、设置更新、个人档案更新、任务完成/失败等。字段为事件 ID、时间、级别、组件、事件类型、消息、Actor、实体类型/ID、Request ID 和非敏感结构化详情。

审计事件通过 `/api/logs` 查询并在 PC“运行日志”页面展示。页面只展示结构化事件，不直接暴露原始日志文件。

## 3. 事件链路

```text
手机/PC 请求
  → Request ID
  → API JSONL（路径、状态码、耗时）
  → 业务动作
      → system_events（可读审计事件）
      → Job
          → Worker JSONL
          → system_events（完成/失败）
```

Request ID 由 API 生成或接受客户端 `X-Request-ID`，并通过响应头返回。涉及 Job 的事件同时记录 Job ID，便于从页面任务跳转到日志筛选。

## 4. 级别与事件规范

| 级别 | 使用条件 | 示例 |
|---|---|---|
| INFO | 正常状态变化 | 会话建立、设置保存、任务完成 |
| WARNING | 可恢复但需要关注 | 配对失败、运行时降级、来源需确认 |
| ERROR | 操作失败或数据处理失败 | Worker 异常、Provider 调用失败 |

事件类型采用 `领域.对象.动作`，例如 `auth.session.created`、`auth.token.rotated`、`job.completed`、`job.failed`、`profile.updated`。消息供人阅读，自动化判断使用事件类型而不是解析消息文字。

## 5. 安全、保留与恢复

- 4 位配对码只存在 macOS Keychain，页面通过受保护接口读取；日志永不记录其值。
- API Key 只存在 Keychain；Provider 日志只记录 Provider、模型与错误摘要。
- 运行日志按文件大小轮换；审计事件的默认产品保留期为 90 天，清理任务后续按 `app:general.data_retention_days` 执行。
- SQLite 使用 WAL；日志写入失败不能阻塞主业务，审计事件失败应回滚当前业务事务并在 stderr 留痕。
- 备份应同时包含 `app.db`、`-wal/-shm` 一致性快照和永久文件，不要求备份可再生的 JSONL。

## 6. 可观测性验收

验收必须满足：PC 日志页能看到设置/档案/配对/任务事件；API 响应带 Request ID；`api.jsonl` 与 `worker.jsonl` 为合法逐行 JSON；任务失败可从 Job ID 定位事件；日志中搜索不到配对码、Cookie、API Key 与请求正文。

## 7. 运维查询与界面契约（v0.3 设计基线）

当前 `/api/logs` 的基础检索不足以支撑日常排障。下一实施版必须增加时间范围、多个级别/组件、事件类型、Job ID、Request ID、实体 ID、全文检索、游标分页与排序，并允许任务详情携带 Job ID 深链到日志页。日志详情需要保留结构化 detail、耗时/状态码和脱敏异常摘要；导出与页面使用同一脱敏层。

页面交互、实时跟随、详情抽屉、固定列和验收规则以 `OPERATIONS_UI_SPEC.md` 第 5 节为准。该节目前是设计契约，不代表查询 API 或日志页已经实施。

## 8. 错误事件触发步骤级续跑（已实施入口需返工）

运行日志是诊断与操作入口，不拥有 Job 状态机。ERROR/CRITICAL 事件关联 Job/Step 后，日志页先查询 Job Replay Options：

- `level` 为 `ERROR` 或 `CRITICAL`；
- `entity_type == "job"` 且 `entity_id` 对应仍存在的 Job；
- `detail.step` 对应本次失败步骤；
- Job 没有活跃 lease；
- 上游 Step Artifact 未过期且输入/版本有效。

Artifact 可用时主按钮为“从错误步骤继续”，确认框列出复用的上游步骤、重新执行的当前/下游步骤和 replayable_until；调用统一 `POST /api/jobs/{job_id}/retry-from-step`。Artifact 已清理时禁用步骤续跑并显示“中间产物已清理”，只提供独立的“完整重跑”。

新任务错误事件必须保存非敏感 `step/error_code/attempt`。服务端验证 source_event_id、失败 Step 与 Replay Options 一致；日志页面不得写 JobStep 或指定任意 from_step。

新 Attempt 把上游有效步骤标为 REUSED，从失败步骤开始顺次执行；下游旧输出 INVALIDATED。新尝试再次失败时保留旧事件和旧 Attempt。完整契约见 `PIPELINE_STEP_REPLAY_V044_SPEC.md`。
