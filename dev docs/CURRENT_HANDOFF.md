# 当前交接

> 本文件只维护任务续接与带日期的生产快照；源码能力和自动验证的唯一来源为 [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)。

## 任务续接

- 更新：2026-09-08。范围为地图地点管理与证据化时间窗口。
- 已完成：地点全选/删除确认、Marker 预览、路线/POI 管理；0016–0017 迁移；视频地点从转写提取观赏期、丰枯水、渔业限制、花/红叶/雪/迁徙等窗口，保留原文与 Segment 证据；POI Review 不再覆盖这些元数据。提交并推送 `161d320`。
- 验证：后端 pytest 96、Ruff；前端 lint/Vitest 15/build；隔离新库完整升级与模拟旧 0016 升级均到 0017，重复列问题已消除。
- 未完成：生产库仍为 2026-09-04 采样的 0013，本次未复核、未迁移或重启；没有新的真实视频验收。
- 下一步：用户授权后，先确认无活跃 Job，再备份并迁移生产库至 0017，使用含明确时间表述的真实视频验收。
- 注意：不得自动确认候选、清理审计或重跑真实视频；上述生产快照未复核。

## 生产快照（采样 2026-09-04）

- cn.zhijian.api、cn.zhijian.worker 为 RUNNING；health、首页正文和 Worker 心跳就绪；SQLite/WAL 为 Alembic 0013，采样时活跃 Job/lease 为 0。
- 运行时为 Python 3.14.6，/Volumes/D/Library/Application Support/Zhijian/venv/bin/python；LaunchAgent 的 PYTHONPATH 指向仓库 backend/src。
- 原验收记录包含 Bilibili 站内扫码、nav 账号验证与 Keychain 保存；登录失效仍须 NEEDS_USER，不回显 Cookie。
- 精确生产 Git SHA 未嵌入进程，不能由当前工作树/HEAD 推断加载版本。上述健康、迁移和任务数都是旧采样，需要操作生产时须重新读取。
- Gateway 真实 Local/Remote Provider、视频、fallback、cache/force-regenerate、预算、取消/Replay 与 Benchmark 不因健康检查而通过；按 [生产验收门禁](ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md) 单独留证。
- 不为写交接运行生产检查、迁移或重启。Secret、Cookie、API Key 和真实用户内容不写入交接；未来范围不自动授权。
