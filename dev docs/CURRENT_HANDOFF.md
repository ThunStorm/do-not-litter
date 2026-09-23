# 当前交接

> 本文件只维护任务续接与带日期的生产快照；源码能力和自动验证的唯一来源为 [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)。

## 任务续接

- 目标：修复 `job_ad0ba062003a492bb9ff62270bcce385` 的证据地图超时，并从 `EXTRACT_TRAVEL_FACTS` 验证步骤续跑；保持原 Transcript/Evidence 和 POI 人工审核边界。
- 已完成：`7a3488d`、`f85ccd9`、`34a801f` 已提交并经目标/完整后端、Ruff、前端和文档验证。2026-09-23 两次无迁移重载及备份通过；第二次真实步骤续跑按 17 块执行，2 次本地后切备用，Ground Map 已持久化，API/Worker/内容/心跳 READY。
- 未完成：Job 在 `GENERATE_AI_NOTE` 选路时停下，尚未调用笔记模型。提交快照的本地 Qwen 未声明 `GLOBAL_SYNTHESIS`，备用 DeepSeek Flash 的该能力 Probe 为 `FAIL`；无活跃 Job/lease。下一步按用户选择验证/指定笔记模型并做可审计的任务级恢复，再仅从笔记阶段续跑。保留快照、历史事件和 POI 人工审核；不把地图成功称为整条 Job 成功。

## 生产快照（最新采样 2026-09-23；下列历史条目保留原日期）

- 2026-09-23 22:08（Hint 与取消修复重载）：重启前 revision=`0025`、`integrity_check=ok`、FK 错误 0、active Job/lease=0；逻辑备份 `data/backups/app-pre-ground-map-hint-reload-20260923-220822.db` 完整性 ok、FK=0、revision=`0025`。无 migration 重启后 API/Worker RUNNING、内容/心跳 READY，Worker PID=`83871`；旧 `FAILED` Job + `CANCELLED` Step 已恢复步骤续跑选项。22:09 再次真实续跑中 Ground Map 17 块，2 次本地完成后因预计耗时切到 DeepSeek，15 次备用完成、1 次备用截断后拆分恢复，地图产物 `gma_22c844fa00aa459e9d255cb1973a6a3f` 已持久化。Job 随后在 `GENERATE_AI_NOTE` 未选到 `GLOBAL_SYNTHESIS` 模型而 `FAILED`，无笔记模型调用；此刻 active Job/lease=0，笔记步骤 Replay Options 可用，有效至 2026-09-24 17:53 北京时间。

- 2026-09-23 21:52（证据地图首次重载）：重启前 revision=`0025`、`integrity_check=ok`、FK 错误 0、active Job/lease=0；逻辑备份 `data/backups/app-pre-ground-map-fallback-20260923-215216.db` 完整性 ok、FK=0、revision=`0025`。无 migration 重启后 API/Worker RUNNING、内容/心跳 READY，Worker PID=`80152`。21:54 已授权的 `EXTRACT_TRAVEL_FACTS` 续跑因旧 Hint 形成 70 块，发现超出远程 48 次/轮上限后请求取消；仅 1 次本地 Attempt，记录 `CANCELLED/JOB_RUN_FENCED`，无远程调用。旧 Worker 错把 Job 终态写为 `FAILED`、Step 留在 `CANCELLED`，无 lease；本次真实端到端未通过。

- 2026-09-23（ASR 设置部署）：无 migration；复载后 `data/app.db` revision=`0025`、`integrity_check=ok`、`foreign_key_check=0`、active Job/lease=0。两份本轮逻辑备份 `app-pre-asr-settings-20260923-113702.db` 和 `app-pre-asr-path-fix-20260923-113952.db` 均验证完整性 ok、FK=0、revision=`0025`。API/Worker RUNNING、内容/心跳 READY（Worker PID=`21988`）；OpenAPI 含 `/api/settings/asr` GET/PUT，状态页 Qwen `READY`（运行包 0.4.4），桌面 Settings 新控件可见。默认 `WHISPER_CPP`；未提交媒体或调用真实 Provider。

- 2026-09-23：`data/app.db` revision=`0025`、`integrity_check=ok`、`foreign_key_check=0`；API/Worker RUNNING、内容/心跳 READY、active Job/lease=0。本轮未制作新备份；旧备份按最新两份保留策略清理，剩余两份 revision=`0023` 且完整性 ok。

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
