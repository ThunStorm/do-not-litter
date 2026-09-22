# 当前交接

> 本文件只维护任务续接与带日期的生产快照；源码能力和自动验证的唯一来源为 [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)。

## 任务续接

- 完成：Pipeline runtime resilience 已部署；Attempt 预登记/heartbeat、lease 续期、独立 watchdog、run fence、Stage-first 截断恢复、Note Reduce 有界分包/降级、能力准入及任务/日志实时 UI 已加载。后端 209 项、完整 Ruff、前端 verify、文档与 `diff --check` 通过；桌面/390px Browser 无溢出或控制台错误。
- 部署：2026-09-22 无 migration 重启；门禁 active Job/lease=0、revision=`0023`、`integrity_check=ok`，备份 `app-pre-runtime-resilience-20260922-165753.db` 完整性 ok、SHA-256=`ba23d9a…f41`。API/Worker/首页/heartbeat READY，PID=`97038`，executor=`IDLE`；OpenAPI 已含 active Attempt 与 Stage budget 字段。
- 保留：Qwen 仍为显式备用，默认 Whisper；真实 Frozen Benchmark、Context A/B、长视频、真实 fallback/迟到响应 E2E 仍待用户授权执行。禁止用 Fake/Smoke 代替真实毕业，不自动重跑历史视频、切默认或确认 POI。

## 生产快照（采样 2026-09-13）

- 2026-09-13 已重启 cn.zhijian.api、cn.zhijian.worker；health、首页正文和 Worker 心跳 READY。迁移前 active Job/lease=0，SQLite/WAL `integrity_check=ok`。
- SQLite/WAL 实读 Alembic 0022（head），`video_note_search` 已存在；本次升级前逻辑备份为 `data/backups/app-pre-ui-video-poi-v2-20260913-125600.db`，完整性为 ok。
- 运行时为 Python 3.14.6，/Volumes/D/Library/Application Support/Zhijian/venv/bin/python；LaunchAgent 的 PYTHONPATH 指向仓库 backend/src。精确 Git SHA 未嵌入进程。
- 2026-09-13 修复后再次重启；API/Worker/首页/心跳 READY，生产 `integrity_check=ok`、active Job/lease=0。真实样本已证明下载、ASR、校对、抽取、Note、POI Review、截图和 FTS 交付；仍不外推为 Vision、Profile 切换、fallback、cache/force-regenerate、预算或 Browser/390px 验收。
- 2026-09-14：Evidence Index 改为稳定 Mention ID 顺序，部署后真实验证 COMPACT Profile、Cache Hit 与 force-regenerate；API/Worker/心跳 READY。Local Video 只验证至 ASR，后续本地校对超时；本轮不再重试。
- 2026-09-14（本次复核）：`data/app.db` revision 为 `0023`，`integrity_check=ok`，未见 active Job/lease；API/Worker 与心跳 READY。本次没有重启，以上只证明迁移后的存储和现有运行状态，不证明新源码已加载。
- 2026-09-14（本次部署）：先备份 `app-pre-llm-token-automation-20260914-143324.db` 并验证 ok，revision `0023` 无需重复迁移；重装后 API/Worker/首页/心跳 READY，LaunchAgent 环境为 `ENV=production`，`grounded_map_artifacts` 表存在。主远程 Profile 返回 429，未重试；本地 JSON 测试通过。
- 2026-09-16（本次部署）：本轮仅重启加载当前 checkout，未迁移；重启前 active Job/lease=0、`integrity_check=ok`、revision=`0023`。备份 `app-pre-cache-validation-20260916-095211.db` 已验证完整性/revision。重启后 API/Worker `RUNNING`、API content 与 Worker heartbeat `READY`；LaunchAgent 生产 Python/PYTHONPATH 已实读核对。未触发真实 Provider、视频续跑或 Cache 删除。
- 2026-09-16（部署修正）：首次重启后 Worker 因新可靠层触发的包循环导入退出，故上述首次 Worker READY 已撤回；修复 `zhijian.ai` Gateway 惰性导出、完整回归和第二份备份后重新重启。API/Worker 均 RUNNING，heartbeat PID=`38268` 已与 Worker 进程核对一致；未迁移或触发真实视频/Provider。
- 2026-09-16（GLM-only 实验）：备份与闲置/完整性门禁通过后写入 REMOTE_ONLY/GLM GUARDED/32 Segment 配置并受控重启；真实 Replay 未进入内容生成，首个校对批次即被 SenseNova 以 `insufficient_quota` 429 拒绝。可靠层未重试 quota、未切本地模型；API/Worker/心跳继续 READY，active Job/lease=0。
- 2026-09-16（截断修复部署）：后续 Replay 已越过 429，但 GLM 首批输出达到长度上限；未继续自动请求。部署批次二分恢复与 4000/16 配置前备份 `app-pre-transcript-split-20260916-142848.db` 并验证 ok；无 migration。部署后 API/Worker RUNNING、内容/心跳 READY、active Job/lease=0。
- 2026-09-16（增量恢复与隔离部署）：部署前 active Job/lease=0、`integrity_check=ok`、revision=`0023`，备份 `app-pre-reliability-isolation-20260916-continue.db` 验证 ok；无 migration。重启后 API/Worker RUNNING、内容/心跳 READY，heartbeat PID=`60964` 与 LaunchAgent 一致，active Job/lease=0。未触发真实 Provider 或 Replay。
