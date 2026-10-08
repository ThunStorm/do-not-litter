# 当前交接

> 本文件只维护任务续接与带日期的生产快照；源码能力和自动验证的唯一来源为 [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)。

## 任务续接

- 目标与范围：全局文档同步与当前分支远程交付，包含已验证的本地路由/CLI、Token/取消响应及 trust_env 修复；不扩展未来路线。
- 完成与验证：源码后端 279/前端 19、Ruff/类型/构建通过；2026-10-08 23:47 已无迁移加载，服务原快照见下。本轮仅文档链接、历史迁移、清单及合订一致性检查；代码和文档随本轮提交交付，准确提交以分支 Git 记录为准。
- 当前只读复核：job_d3fc3507…于 2026-10-09 00:16 从校对续跑至 PARTIAL_SUCCESS，复用 ASR，产出笔记/截图；地点 3 REVIEW、12 UNRESOLVED。此前两条旧阻塞 Job 已不在库中。本轮没有发起真实调用或续跑。
- 未完成：Ollama 客户端取消后上游继续推理；全型号/长视频/厂商额度、远端取消计费和质量 Benchmark 未闭环。当前仅有有界真实样本，不能外推全矩阵。
- 下一步一项：经用户授权处理 Ollama 取消后的限时清理及真实退出验收。相关文件：providers/llm.py、ai/resource_manager.py、ai-gateway/AI_RUNTIME_AND_PROVIDERS.md。禁止自动重跑、改历史审计/提交快照、自动确认 POI；本轮不重启/迁移，旧服务健康采样未复核。

## 生产快照（最新数据库采样 2026-10-09；服务健康采样仍为 2026-10-08，下列旧条目保留原日期）

- 2026-10-09（文档任务的数据库只读复核）：`job_d3fc3507d995425eb6d1fe01a76b0311` 在 2026-10-08 23:50:36 至 2026-10-09 00:16:08 从 CORRECT_TRANSCRIPT 续跑，终态 PARTIAL_SUCCESS/CLEAN_CACHE，生成 `cnt_c48ba4c1f95d4013bbe82269041e58d0` 与 `note_0e1dbcfa3148455db77e5146f8ffa12c`；上游含 ASR 的 6 步 REUSED，校对、Ground Map、Note、地点/截图/物化均 COMPLETED。地点 confirmed=0、REVIEW=3、UNRESOLVED=12，保留人审；调用审计仍保留原 trust_env 失败及后续 Ground Map 失败，不能因步骤完成改写历史。此前 job_d8e17638…/job_f4495f14…均已不在当前库中。本轮仅采集上述证据，没有发起推理/重跑/迁移/重启，也未重新采样 API/Worker 健康；23:47 的服务状态继续保留原日期，不当作本次健康结果。

- 2026-10-08 23:47（trust_env 修复加载）：用户授权无迁移重载 API/Worker；重载前 active Job/lease=0、integrity=ok、FK=0、revision=0025，逻辑备份 `data/backups/app-pre-trust-env-fix-20261008-234654.db` 的完整性/FK/revision 均通过。生产解释器 manage.py restart/status 确认 API/Worker RUNNING、首页/health READY，Worker 新心跳 PID=65568 与进程一致；OpenAPI HTTP 200（104 条路径），重载后 integrity=ok、revision=0025、active/lease=0。后端 279 项、前端 19 项及 Lint/类型/构建通过；原 `job_d3fc3507d995425eb6d1fe01a76b0311` 保持 NEEDS_USER/CORRECT_TRANSCRIPT，ASR 已完成，未自动续跑、改历史审计或调用真实模型。取消后 Ollama 侧停止推理仍为独立未闭环项；本轮未提交/推送，以下旧现场保留原采样日期。

- 2026-10-08 22:22（Mux 安装版 CLI 保护值核对）：本轮通过只读 `/api/health` 确认 API=ok、active_tasks=0、总期 600/流空闲 180/Agent 并发 1/间隔 5/锁等待 30 秒；以至简 LaunchAgent 的既有 Keychain 凭据 GET `/v1/models` 返回 200，codebuddy/hy3 可见，无生成。安装版/release SHA 均为 `58575bf15a7ec24154d439bb76f172066dcdcadb35515884aec9dcf53981e39e`；Mux Key ID/哈希/scopes/限制/角色/RPM 的聚合摘要与 18:08 备份一致，DB integrity=ok、FK=0。Mux schema=11 由并行调用记录包部署，本包无 Schema 改动；本次已在最终 CSS 安装后重新核对二进制与运行保护值；原生 API 页显示运行中，本轮没有点击模型测试、复制 Key 或修改权限。至简 API/Worker/首页/心跳复核 READY（PID=93666），新参数 6/6 匹配，原失败 Job 9 条历史 Audit 与备份逐字段一致；未调用真实模型、重跑视频或确认 POI。

- 2026-10-08 18:08–18:10（订阅 CLI 参数与至简加载）：两库逻辑备份 `data/backups/zhijian-pre-cli-reliability-20261008-180852.db`、`~/Library/Application Support/LocalMux/backups/localmux-pre-cli-reliability-20261008-180852.db` 均 integrity/FK 通过；版本分别为 0025、10。生产 6 项非密钥 Settings 校验后单事务保存，Job payload 哈希未变，配置审计为 settings.cli_reliability.updated；只影响新提交。生产解释器 manage.py 无迁移重载后 API/Worker RUNNING、首页/heartbeat READY（PID=93666），OpenAPI 与 6/6 参数匹配；integrity=ok、FK=0、revision=0025、active/lease=0。原 job_d8e17638fff7485fa6483accbf734865 仍 FAILED/AI_PROVIDER_HTTP_5XX，未重跑。Mux 安装版仍为旧期限，本轮此时未重启它，待并行调用记录改造的最终验证与部署；真实推理、视频和 POI 未操作。此前带日期采样保留原现场，不视为本次状态。

- 2026-10-08 18:11（收尾复核）：API/Worker/页面/心跳仍 READY，当前 Worker PID=93666；active Job/lease=0，用量 HTTP 仍返回估算 88864/659 和 9 次输出未知。18:09 现场另有 API/Worker 正常重新启动记录，本轮仅在 18:02 发起一次重载；不把较早 PID 作为当前运行进程。

- 2026-10-08 18:02–18:08（Token 与任务响应部署）：active Job/lease=0、integrity=ok、FK=0、revision=0025；逻辑备份 `data/backups/app-pre-token-responsive-20261008-180203.db` 完整性/FK/revision 已验证。生产解释器 manage.py restart 无迁移重载；API/Worker RUNNING、页面/心跳 READY，Worker PID=91660。实际 `/api/jobs/job_f4495f14062f4ed097e32692298b9f64/ai-usage` 返回实测 0/0、累计请求输入估算 88864、可见输出估算 659、9 次输出未知；PC/390px 显示“约 88864 / 约 659（部分未知）”，无横向溢出/控制台错误。该 Job 的 22 条历史 Audit 与部署前备份逐字段一致；未执行真实 Provider 测试、视频重跑、配置改写、历史结果改写、提交或推送。以下旧现场保留原采样日期，本次未逐项复核。

- 2026-10-08 16:07–16:10（手动测试队列与 Mux 修复加载）：用户明确授权无迁移重载。重载前 integrity=ok、FK=0、active/leased Job=0、revision=0025；逻辑备份 `data/backups/app-pre-manual-test-reload-20261008-160711.db` 已验证完整性/FK/revision。通过生产解释器执行 manage.py restart，API/Worker RUNNING、页面与心跳 READY（Worker PID=48539）；OpenAPI 已有接口能力读取路由，旧 Local Ai Mux 配置正确解析 LOCAL_ROUTER。对同一已保存 `model_9840af90390a42ac8e4f9b19a37a3d37 / codebuddy/hy3` 连续提交真实 test 与 probe：test PASS 15.64 秒先完成，probe 排队后完成（提交起 27.63 秒），既有四项小样 PASS、其余 NOT_TESTED，无 FAIL；两条审计先后为 tested/probed。Probe 已保存本机路由类型、接口快照与原生 JSON=false。复核 integrity=ok、active/leased Job=0；没有视频重跑、迁移、POI 确认或 Mux 重启。此为该模型连通/小样能力和混合队列验收，不是完整业务 Benchmark；未提交/推送。旧任务续接的 POI 人审边界仍有效。

- 2026-09-24 09:07（笔记恢复加载与验收）：重启前 revision=`0025`、`integrity_check=ok`、FK 错误 0、active Job/lease=0；逻辑备份 `data/backups/app-pre-note-nonthinking-20260924-090716.db` 完整性 ok、FK=0、revision=`0025`。无 migration 重启后 API/Worker RUNNING、内容/心跳 READY，Worker PID=`23602`。任务详情页选择 DeepSeek Flash，排队审计记录 `NOTE_REDUCE` 任务级覆盖和 `thinking=false`，原提交快照未改；真实笔记归纳 23 次调用均 COMPLETED，无输出截断。Job `PARTIAL_SUCCESS`、error_code/error 均空，完成摘要为“AI 笔记已生成，52 个地点待确认”；Note `ntv_38fdf4bb64ba48ea8d65064c932cd7f1`（Version 2）含 48 章节、75 条引文且无失效 Segment ID/不归属引文，9 张截图 READY，3 张 REJECTED。桌面与 390×844 恢复卡无溢出，浏览器控制台无错误；POI 未自动确认。

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
