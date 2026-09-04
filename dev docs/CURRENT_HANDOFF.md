# 当前交接

> 本文件只维护任务续接与带日期的生产快照；源码能力和自动验证的唯一来源为 [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)。

## 任务续接

- 更新：2026-09-04。范围为地图 V2 核心实现、生产迁移与文档拆分收敛。
- 已完成：0011–0013、Insight/POI Review、地图聚合展开、点选附近 POI、手工地点、审核改名/拒绝/撤销、Place Sheet 与编辑历史；LLM 停滞预警为 500 秒、终止仍为 900 秒。
- 验证：后端 pytest 93、Ruff；前端 lint/Vitest 11/build；生产 SQLite 0013、integrity ok、API/Worker 健康。真实视频完成字幕/笔记/截图并产生 Review 候选，终态 PARTIAL_SUCCESS，未自动确认 POI。
- 未闭环：生产已有 5 条 USER_REJECTED 测试 Mention，保留等待用户决定是否恢复；未提交/推送本批代码与文档拆分。
- 下一步：用户验收后仅处理审计队列数据或继续新增需求；禁止未经选择自动确认候选、清理审计或重跑真实视频。
- 相关文件：IMPLEMENTATION_STATUS.md、operations/RUNTIME_MONITOR_AND_PROVIDER_SWITCH_V06_SPEC.md、planning/PLACE_INTELLIGENCE_MAP_V2_IMPLEMENTATION_PLAN.md、frontend/src/features/map/。本次已部署，提交/推送由本轮用户授权。

## 生产快照（采样 2026-09-04）

- cn.zhijian.api、cn.zhijian.worker 为 RUNNING；health、首页正文和 Worker 心跳就绪；SQLite/WAL 为 Alembic 0013，采样时活跃 Job/lease 为 0。
- 运行时为 Python 3.14.6，/Volumes/D/Library/Application Support/Zhijian/venv/bin/python；LaunchAgent 的 PYTHONPATH 指向仓库 backend/src。
- 原验收记录包含 Bilibili 站内扫码、nav 账号验证与 Keychain 保存；登录失效仍须 NEEDS_USER，不回显 Cookie。
- 精确生产 Git SHA 未嵌入进程，不能由当前工作树/HEAD 推断加载版本。上述健康、迁移和任务数都是旧采样，需要操作生产时须重新读取。
- Gateway 真实 Local/Remote Provider、视频、fallback、cache/force-regenerate、预算、取消/Replay 与 Benchmark 不因健康检查而通过；按 [生产验收门禁](ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md) 单独留证。
- 不为写交接运行生产检查、迁移或重启。Secret、Cookie、API Key 和真实用户内容不写入交接；未来范围不自动授权。
