# 当前交接

> 本文件只维护任务续接与带日期的生产快照；源码能力和自动验证的唯一来源为 [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)。

## 任务续接

- 更新：2026-09-11。视频质量总计划 WP0–22 已部署；`0020` 增加地点化章节 Evidence，地点抽取改为完整转写分块后先于 Note，审核页/笔记页共用 Review Context。
- 已完成：生产库从 `0019` 升级至 `0020`，备份 `data/backups/app-pre-video-quality-0020-20260910-234552.db` 完整性为 ok；API/Worker 重启后 health、首页、Worker 心跳、`/place-reviews` source_context 与 revision 均正常，无活跃 Job/lease。
- 已完成：确认后的地点候选直接显示当前绑定 `Place` 的名称/地址并链接地点详情，不再显示视频时间码或 Insight 行注释；`REVIEW` 与 `UNRESOLVED` 均可在笔记页打开搜索/确认 POI。
- 已完成：未确认候选及审核 Evidence 上下文的全部时间戳会以新窗口链接打开原 Bilibili 视频并传递 `t` 秒级定位参数；保留原链接查询参数。
- 验证：目标 Ruff、后端完整测试、Node 24 前端 verify、`diff --check` 均通过；已在已部署笔记页确认确认态不带转写行、待确认卡可点击“搜索 POI”；未调用 Provider、未重跑真实视频、未自动确认 POI。
- 未完成：WP23 仍按性能证据延期；现有 `PARTIAL_SUCCESS` Job 没有失败步骤可续跑，剩余 POI 需用户审核。
- 下一步：用户在视频笔记或 `/place-reviews` 审核 POI；如需真实 Benchmark/视频重跑，单任务串行并遵守 QPS。
- 注意：不删历史 Transcript/Note/Evidence，不自动确认不确定 POI；零库升级仍受已发布的 `0019` 重复建表问题影响，禁止回改历史 migration。

## 生产快照（采样 2026-09-10）

- 2026-09-10 已重启 cn.zhijian.api、cn.zhijian.worker；health、首页正文和 Worker 心跳 READY，活跃 Job/lease 为 0。
- SQLite/WAL 实读 Alembic 0020（head），`integrity_check=ok`；本次升级前逻辑备份为 `data/backups/app-pre-video-quality-0020-20260910-234552.db`，其完整性与 revision 均已复核。
- 运行时为 Python 3.14.6，/Volumes/D/Library/Application Support/Zhijian/venv/bin/python；LaunchAgent 的 PYTHONPATH 指向仓库 backend/src。精确 Git SHA 未嵌入进程。
- Gateway 的真实 Local/Remote、ASR、视觉、fallback、cache/force-regenerate、预算、取消/Replay 仍须按 [生产验收门禁](ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md) 单独留证；不得以本次健康和单个字幕样本外推。
