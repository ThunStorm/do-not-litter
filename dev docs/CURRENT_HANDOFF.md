# 当前交接

> 本文件只维护任务续接与带日期的生产快照；源码能力和自动验证的唯一来源为 [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)。

## 任务续接

- 更新：2026-09-08。视频 Benchmark/知识工作包已冻结，未部署。
- 已完成：Gateway 按真实 Provider attempt 执行预算/本地锁；12 个 Fixture Golden、离线评分与 Job/Replay 采集器；三种本地模型基础 Probe；0018 为 Insight 增加逐条 Segment/source quote；视频页展示 Insight 跳转；Place Note 跨来源汇总并标记 SINGLE_SOURCE/CONSENSUS/CONFLICT；POI 离线质量指标。
- 验证：最后一次全量后端 pytest 105；后续 Place 聚合目标测试 26、POI Benchmark 测试 1 与目标 Ruff 通过；前端 lint/Vitest 15/build；隔离 SQLite 升级到 0018 并确认新列；文档生成测试与 diff check 通过。
- 阻塞：WP1 正式 JSON Schema/完整 Probe、WP5 真实 POI 矩阵、WP6 Visual Fact/视觉模型、WP7 本地模型矩阵和真实视频 E2E；当前 qwen3.5:9b 仅验证文本能力，不可用于视觉。
- 下一步：后续重新授权并具备 image-capable Profile 与合法标注视频后，先确认无活跃 Job，再从 WP1 未闭环项继续并运行视觉/真实 Benchmark。
- 注意：不自动改默认模型、删除模型、确认 POI 或重跑真实视频；生产快照仍为 2026-09-04，本次未复核。

## 生产快照（采样 2026-09-04）

- cn.zhijian.api、cn.zhijian.worker 为 RUNNING；health、首页正文和 Worker 心跳就绪；SQLite/WAL 为 Alembic 0013，采样时活跃 Job/lease 为 0。
- 运行时为 Python 3.14.6，/Volumes/D/Library/Application Support/Zhijian/venv/bin/python；LaunchAgent 的 PYTHONPATH 指向仓库 backend/src。
- 原验收记录包含 Bilibili 站内扫码、nav 账号验证与 Keychain 保存；登录失效仍须 NEEDS_USER，不回显 Cookie。
- 精确生产 Git SHA 未嵌入进程，不能由当前工作树/HEAD 推断加载版本。上述健康、迁移和任务数都是旧采样，需要操作生产时须重新读取。
- Gateway 真实 Local/Remote Provider、视频、fallback、cache/force-regenerate、预算、取消/Replay 与 Benchmark 不因健康检查而通过；按 [生产验收门禁](ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md) 单独留证。
- 不为写交接运行生产检查、迁移或重启。Secret、Cookie、API Key 和真实用户内容不写入交接；未来范围不自动授权。
