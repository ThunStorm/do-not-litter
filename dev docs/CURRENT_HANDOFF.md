# 当前交接

> 本文件只维护任务续接与带日期的生产快照；源码能力和自动验证的唯一来源为 [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)。

## 任务续接

- 更新：2026-09-14。LLM Token 与自动化优化 WP0–WP14 已入源码：Grounded Map 复用、Delta Whisper 校对、Retry Guard、v2 AUTO 路由、Soft Budget、严格 AUTO_STRONG POI、Token Anomaly 与离线回归 Gate 均完成；WP15 仅完成证据 Gate。全量后端、Ruff、Node 24 前端 verify、`diff --check` 通过；未调用真实 Provider/视频。
- 现场：迁移验证命令意外作用于 `data/app.db`，已到 `0023`；这是未授权的生产迁移，事前未做本轮备份/Job 门禁。事后只读复核 `integrity_check=ok`、active Job/lease=0，API/Worker/心跳 READY；未重启服务，不能据此宣称新源码已加载或真实 E2E 已通过。
- 未完成/边界：WP15 尚无真实毕业证据；无 Vision Profile、ASR corpus、真实主备 fallback 或 390px Browser 验收。下一步仅在用户明确授权后，以固定 10/30/60 分钟视频按 Gate 采集 Local/Remote/fallback/timeout/invalid-JSON、Replay 与质量/Token 对比；真实调用/重启前先按部署门禁备份和复核，不得重跑既有媒体、ASR、校对，或改历史 Source/Transcript/Note/Evidence。

## 生产快照（采样 2026-09-13）

- 2026-09-13 已重启 cn.zhijian.api、cn.zhijian.worker；health、首页正文和 Worker 心跳 READY。迁移前 active Job/lease=0，SQLite/WAL `integrity_check=ok`。
- SQLite/WAL 实读 Alembic 0022（head），`video_note_search` 已存在；本次升级前逻辑备份为 `data/backups/app-pre-ui-video-poi-v2-20260913-125600.db`，完整性为 ok。
- 运行时为 Python 3.14.6，/Volumes/D/Library/Application Support/Zhijian/venv/bin/python；LaunchAgent 的 PYTHONPATH 指向仓库 backend/src。精确 Git SHA 未嵌入进程。
- 2026-09-13 修复后再次重启；API/Worker/首页/心跳 READY，生产 `integrity_check=ok`、active Job/lease=0。真实样本已证明下载、ASR、校对、抽取、Note、POI Review、截图和 FTS 交付；仍不外推为 Vision、Profile 切换、fallback、cache/force-regenerate、预算或 Browser/390px 验收。
- 2026-09-14：Evidence Index 改为稳定 Mention ID 顺序，部署后真实验证 COMPACT Profile、Cache Hit 与 force-regenerate；API/Worker/心跳 READY。Local Video 只验证至 ASR，后续本地校对超时；本轮不再重试。
- 2026-09-14（本次复核）：`data/app.db` revision 为 `0023`，`integrity_check=ok`，未见 active Job/lease；API/Worker 与心跳 READY。本次没有重启，以上只证明迁移后的存储和现有运行状态，不证明新源码已加载。
