# 日志系统实施文档

版本：v0.1，更新日期：2026-08-19。

## 1. 已实施组件

| 组件 | 文件/接口 | 职责 |
|---|---|---|
| JSON Formatter | `backend/src/zhijian/core/logging.py` | 统一 API/Worker JSONL 格式与 10 MiB×5 轮换 |
| 请求中间件 | `backend/src/zhijian/main.py` | Request ID、状态码、耗时和异常记录 |
| 审计模型 | `backend/src/zhijian/db/models.py` | `system_events` 持久表 |
| 数据迁移 | `backend/alembic/versions/0002_system_events.py` | 新建表与时间/组件索引 |
| 审计服务 | `backend/src/zhijian/services/audit.py` | 业务事件统一写入 |
| 查询 API | `GET /api/logs` | 按级别、组件、关键词和数量查询 |
| PC 页面 | `/logs` | 五秒刷新、级别筛选、关键词检索 |

## 2. 运行目录

```text
data/logs/
  api.jsonl
  api.jsonl.1 ... api.jsonl.5
  worker.jsonl
  worker.jsonl.1 ... worker.jsonl.5
  api.stdout.log / api.stderr.log
  worker.stdout.log / worker.stderr.log
```

`data/` 不进入 Git。生产服务由 `deploy/macos/manage.py` 生成的两个 LaunchAgent 写入同一目录。

## 3. 接口使用

```http
GET /api/logs?level=ERROR&component=worker&query=Whisper&limit=200
```

返回时间倒序事件列表。`limit` 范围为 1–1000；全部接口复用局域网 Session 保护。本机 `127.0.0.1` 按部署设置可豁免会话。

新增审计事件时调用：

```python
record_event(
    db,
    "job.failed",
    "任务处理失败",
    component="worker",
    level="ERROR",
    entity_type="job",
    entity_id=job.id,
    detail={"reason": "runtime unavailable"},
)
```

`detail` 只能放非敏感字段。若业务随后还有同一事务提交，使用 `commit=False`，避免把部分状态提前提交。

## 4. 部署与升级

1. 运行 `.venv/bin/alembic -c backend/alembic.ini upgrade head`；当前启动仍使用 `create_all` 兼容初装，但正式升级以 Alembic 为准。
2. 构建前端并重新安装 LaunchAgent：`pnpm --dir frontend verify`，随后 `.venv/bin/python deploy/macos/manage.py install`。
3. 检查 `data/logs/api.jsonl`、`data/logs/worker.jsonl` 是否持续追加，并在 `/logs` 验证结构化事件。
4. 回退到 v0.1.0 时先停止服务并备份数据库；`0002` 降级会删除审计事件表，因此默认不执行 downgrade，只回退应用代码。

## 5. 测试清单

- 后端测试覆盖日志 API、档案更新产生审计事件、4 位配对码轮换和真实状态 Schema。
- 手工触发一次设置保存、一次失败登录、一次任务完成，验证页面筛选和时间排序。
- 对日志目录运行敏感词检查，确认不存在 Keychain 值、Cookie 和正文。
- 停止 Worker，等待超过三倍心跳间隔，`/api/status.services.worker` 应显示 `STALE`；重启后恢复 `RUNNING`。

本轮实际验收已确认 API/Worker 启动事件与 Whisper 音频任务完成事件进入 `/api/logs`，`api.jsonl`、`worker.jsonl` 均持续写入合法 JSONL；PC `/logs` 页已完成搜索、级别筛选、立即刷新和五秒自动刷新界面验收。

## 6. 后续增强

第二阶段可增加审计事件导出、按 Request ID/Job ID 深链、90 天定时清理、磁盘低水位告警和日志完整性哈希。未达到单机查询瓶颈前不引入外部日志栈。
