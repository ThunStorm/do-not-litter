# 日志系统设计架构

版本：v0.1，更新日期：2026-08-19，适用部署：Mac mini 单节点。

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
