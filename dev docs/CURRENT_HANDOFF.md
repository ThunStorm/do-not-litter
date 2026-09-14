# 当前交接

> 本文件只维护任务续接与带日期的生产快照；源码能力和自动验证的唯一来源为 [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)。

## 任务续接

- 更新：2026-09-14。LLM Token 自动化源码已部署（`09e4c6a`、`4226541`）：`0023` 已为 head，Grounded Map/Delta/Retry Guard/Router/Soft Budget/POI Gate/Anomaly/Regression 均已加载。部署前 active Job/lease=0、`integrity_check=ok`，备份 `data/backups/app-pre-llm-token-automation-20260914-143324.db` 完整性 ok；API/Worker/首页/心跳 READY。
- 已修复：LaunchAgent 原传 `ZHIJIAN_ENV` 而配置读取 `ENV`，曾启动 development 并生成 2 条无来源演示 Job；已改为 `ENV=production`、删除该两条本次生成的空 Job 并重装，复核未再生成。真实本地 `qwen3.5:9b` JSON 连通通过；主远程 Profile 返回 429，未重试。
- 未完成/边界：没有合规 10/30/60 分钟视频，WP15 真实毕业、远程成功/fallback、Vision、ASR corpus 和 390px Browser 仍未验证。下一步需用户提供或指定可重放样本后，串行按 Gate 采集；不得重跑既有媒体/ASR/校对或自动确认 POI。

## 生产快照（采样 2026-09-13）

- 2026-09-13 已重启 cn.zhijian.api、cn.zhijian.worker；health、首页正文和 Worker 心跳 READY。迁移前 active Job/lease=0，SQLite/WAL `integrity_check=ok`。
- SQLite/WAL 实读 Alembic 0022（head），`video_note_search` 已存在；本次升级前逻辑备份为 `data/backups/app-pre-ui-video-poi-v2-20260913-125600.db`，完整性为 ok。
- 运行时为 Python 3.14.6，/Volumes/D/Library/Application Support/Zhijian/venv/bin/python；LaunchAgent 的 PYTHONPATH 指向仓库 backend/src。精确 Git SHA 未嵌入进程。
- 2026-09-13 修复后再次重启；API/Worker/首页/心跳 READY，生产 `integrity_check=ok`、active Job/lease=0。真实样本已证明下载、ASR、校对、抽取、Note、POI Review、截图和 FTS 交付；仍不外推为 Vision、Profile 切换、fallback、cache/force-regenerate、预算或 Browser/390px 验收。
- 2026-09-14：Evidence Index 改为稳定 Mention ID 顺序，部署后真实验证 COMPACT Profile、Cache Hit 与 force-regenerate；API/Worker/心跳 READY。Local Video 只验证至 ASR，后续本地校对超时；本轮不再重试。
- 2026-09-14（本次复核）：`data/app.db` revision 为 `0023`，`integrity_check=ok`，未见 active Job/lease；API/Worker 与心跳 READY。本次没有重启，以上只证明迁移后的存储和现有运行状态，不证明新源码已加载。
- 2026-09-14（本次部署）：先备份 `app-pre-llm-token-automation-20260914-143324.db` 并验证 ok，revision `0023` 无需重复迁移；重装后 API/Worker/首页/心跳 READY，LaunchAgent 环境为 `ENV=production`，`grounded_map_artifacts` 表存在。主远程 Profile 返回 429，未重试；本地 JSON 测试通过。
