# 日志：契约与维护

> 2026-09-03 合并 LOGGING_ARCHITECTURE.md 与 LOGGING_IMPLEMENTATION.md，消除重复说明与过期“待实施”标签。当前完成度只见 [IMPLEMENTATION_STATUS.md](../IMPLEMENTATION_STATUS.md)，本次未重新运行日志或服务验收。

## 1. 边界与存储

日志回答服务健康、任务结果与用户操作审计三个问题。Mac mini 单节点不引入 Elasticsearch、Loki 或云遥测。JSONL 用于排障，SQLite system_events 用于长期可读审计，不能互相替代。

| 层 | 存储 / 查询 | 约束 |
| --- | --- | --- |
| API / Worker 运行日志 | data/logs/api.jsonl、worker.jsonl | 每行 JSON；单文件 10 MiB，5 个轮换；页面不直接暴露原文件 |
| 审计事件 | SQLite system_events；GET /api/logs | 局域网 Session 保护；本机豁免取决于部署设置 |
| 兜底日志 | data/logs/ 下 API/Worker 的 stdout.log、stderr.log | 日志子系统失效时排查，不作为业务状态证明 |

JSONL 包含 timestamp、level、component、message，可选 request_id、event_type、duration_ms、status_code、path、job_id、脱敏异常。审计事件包含 ID、时间、级别、组件、类型、消息、Actor、实体类型/ID、Request ID 与非敏感 detail。data/ 不进入 Git。

## 2. 事件与事务

API 生成或接受 X-Request-ID 并在响应头返回；业务动作关联 system_events，Job 事件同时带 Job ID。自动化根据 event_type 判断，不解析人类消息文本。

| 级别 | 含义 |
| --- | --- |
| INFO | 正常状态变更，如配对、设置、任务完成 |
| WARNING | 可恢复但需关注，如来源待确认、运行时降级 |
| ERROR / CRITICAL | 处理或运行失败，关联 Job/Step 便于恢复 |

事件类型采用领域.对象.动作，如 auth.session.created、job.failed、profile.updated。业务使用 services/audit.py 的 record_event；同一事务尚有其他写入时使用 commit=False，防止提前提交部分状态。运行日志失败不阻塞主业务；审计失败应回滚相应业务事务并在 stderr 留痕。

## 3. 安全、保留与备份

- 不记录配对码、Session Cookie、API Key、正文、文件内容、完整个人档案；Secret 仅进 Keychain/Secret Store。URL 保留在 Source 域，HTTP 日志只记路径，不记查询串/请求体。
- Provider 日志只含 Provider、模型及脱敏摘要；页面与导出共用脱敏层。
- JSONL 按大小轮换；审计保留期产品默认设计为 90 天，不能据此假定定时清理已上线，核对 app:general.data_retention_days 与实现。
- 备份 SQLite 要有 WAL/SHM 的一致性快照及永久文件；可再生 JSONL 无强制备份要求。不得为日志升级直接执行删除审计表的历史 downgrade。

## 4. 查询与工作台

既有实施记录包含健康摘要、组合筛选、Job/Request 深链、游标分页、实时跟随暂停、结构化详情与单条脱敏导出。时间范围支持快捷项和自定义，服务端支持 from/to、cursor、asc/desc。UI 契约按需读 [operations/OPERATIONS_UI_SPEC.md](OPERATIONS_UI_SPEC.md) 第 5 节，精确参数以 API schema 为准。

只读示例：GET /api/logs?level=ERROR&component=worker&query=Whisper&limit=20。先限定 Job、时间和数量，不导出全部日志。批量 CSV/JSONL、筛选链接复制、低水位告警和完整性哈希不因本次合并而列为已实现。

## 5. 错误事件与 Replay

日志页是操作入口，不拥有 Job 状态机。ERROR/CRITICAL 事件关联仍存在的 Job 与失败 Step 时，先查 GET /api/jobs/{job_id}/replay-options；服务端检查 lease、source_event_id、失败步骤与上游 Artifact 的输入/版本和有效期。

1. Artifact 有效：显示“从错误步骤继续”，确认框展示复用上游、重跑步骤、剩余保留时间；调用 POST /api/jobs/{job_id}/retry-from-step，提交受后端约束的 step_name/source_event_id。
2. 上游标为 REUSED，下游旧输出 INVALIDATED；新尝试失败保留旧事件与 Attempt；跟随 job.step_replay.* 事件。
3. 过期显示“中间产物已清理”，禁用步骤续跑；“完整重跑”是独立按钮/API。409 展示 REPLAY_ARTIFACT_EXPIRED、INPUT_CHANGED、LEASE_ACTIVE 等原因。
4. 页面不能直接改 JobStep、调用 Processor 或选择任意 from_step；新事件保存非敏感 step/error_code/attempt。

完整约束只维护在 [jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md](../jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md)，本节仅说明日志如何接入。

## 6. 代码定位与验证

| 位置（仓库根相对路径） | 职责 |
| --- | --- |
| backend/src/zhijian/core/logging.py | Formatter 与轮换 |
| backend/src/zhijian/main.py | 请求关联、状态码与耗时 |
| backend/src/zhijian/services/audit.py | 审计记录与事务边界 |
| backend/src/zhijian/db/models.py、backend/alembic/versions/0002_system_events.py | 审计模型与历史迁移，不改已发布迁移 |

验证 Request ID、事件/JSONL、Job 关联、筛选/分页、脱敏和 Replay 门禁。生产升级只按 [部署说明](../../deploy/macos/README.md) 执行；迁移前备份并确认无活跃 Job/lease，不以测试为由停止 Worker 或触发真实任务。原 v0.2/v0.3 文本可从 Git 历史追溯，旧验收结论不代表当前现场。
