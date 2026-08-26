# 至简 运行监控口径与 Provider 联动规格

版本：v0.7，更新日期：2026-08-25，状态：`IMPLEMENTED / BROWSER_VERIFIED`。适用部署：Mac mini 单节点。

## 1. 问题与目标

本规格处理本轮设置页与任务详情审阅意见：侧栏内存百分比不能把 macOS 可回收文件缓存算作业务已用内存；运行状态浮窗需要提供足够的单机运维信息；切换模型 Provider 时，上一 Provider 自动带入的 Base URL 与模型名不得残留；重试后的任务不得把旧尝试时间误显示为本次运行时长。

## 2. macOS 内存口径

macOS 指标使用 `vm_stat` 物理页统计。`active`、`wired down`、`occupied by compressor` 构成工作集参考；`free`、`inactive` 与 `speculative` 视为可立即或可回收内存，不能计入“已用”。

接口返回字段：

| 字段 | 定义 |
| --- | --- |
| `memory.used_bytes` | `total - (free + inactive + speculative)`，用于侧栏百分比与浮窗主数值 |
| `memory.available_bytes` | `free + inactive + speculative` |
| `memory.cached_bytes` | `inactive + speculative`，仅作诊断 |
| `memory.compressed_bytes` | `occupied by compressor`，仅作诊断 |
| `memory.method` | `macos-reclaimable-pages`；非 macOS 返回实际采集方法或不可用原因 |

页面不得以 `active + inactive + wired + compressor` 求和，因为这些页集合存在缓存与压缩页重叠，会把内存占用虚高。单项无法读取时返回 `null` 和原因，不显示伪造数值。

## 3. 侧栏与运行浮窗

侧栏继续保持紧凑：CPU、内存、数据盘均展示百分比，内存值使用上述工作集口径。浮窗展开后显示：

- CPU：百分比与采样来源；
- 内存：`已用 GB / 总 GB`、百分比、可回收 GB、压缩 GB；
- 数据盘：`已用 GB / 总 GB` 与可用 GB；
- 服务：API、Worker、SQLite、Ollama 的真实状态；
- 采样时间、指标新鲜度、Worker 最近心跳。

API 每 30 秒写入 SQLite 的同一快照仍是局域网与本机的唯一数据源。超过 75 秒未更新时浮窗明确显示“指标延迟”。

## 4. Provider 预设切换

每个模型编辑器单独维护 `model` 和 `base_url` 的“用户手填”状态：

1. 新增模型和与预设匹配的已保存模型，两个字段初始均为自动值。
2. 每次选择 DeepSeek、MiMo、Moonshot / Kimi、智谱 GLM、通义千问、OpenAI 兼容或 Ollama，所有仍为自动值的字段必须立即替换为该 Provider 当前预设；不得保留上一个 Provider 的默认值。
3. 用户在模型名或 Base URL 输入框亲自修改后，该字段标为手填；之后切换 Provider 时保留该字段，另一个未手填字段仍会更新。
4. 选择“自定义”后不再写入任何默认值；用户可自行填写。Ollama 仍隐藏 Key 与 Base URL 必填提示。

## 5. 任务尝试时间与停滞语义

每次 Job 被重新领取或某个已存在步骤被再次开始时，该步骤的 `started_at` 必须重置为本次尝试时间，`finished_at` 清空；历史开始时间只保留在审计事件中。任务接口额外返回 `runtime_state`、`last_activity_age_seconds` 与 `last_activity_source`：普通运行步骤 90 秒没有活动时为 `STALLED`；`GENERATE_AI_NOTE / EXTRACT_TRAVEL_FACTS / BUILD_PLACE_NOTES` 等 LLM 步骤使用 300 秒预警阈值，避免正常 2–3 分钟模型调用被误报；真正终止尝试仍使用 900 秒。

任务停滞只能由该 Job 自身的 `heartbeat_at`、当前步骤活动时间或该 Job 的审计事件判断；绝不能使用 `runtime:worker-heartbeat` 等全局 Worker 心跳。全局 Worker 正常只说明执行器进程仍在运行，不能证明当前任务正在推进。任务页字段统一写作“该任务最后活动”，必要时显示来源字段。

全局 `runtime:worker-heartbeat` 由独立于 Job 执行循环的守护线程每 `worker_heartbeat_seconds` 写入进程存活信号。同步 Pipeline 被外部模型、FFmpeg 或网络调用阻塞时，心跳仍持续；它只表达“Worker 进程存活”，不更新任何 Job 的 `heartbeat_at`，也不掩盖任务停滞。

### 5.1 尝试超时错误规则

`job_attempt_timeout_seconds` 默认 900 秒。运行中的任务从其自身最后活动起超过此阈值后，Worker 将该次尝试终止为 `FAILED`，而不是无限自动重新领取。错误码固定为 `ATTEMPT_TIMEOUT`；错误原因必须包含当前步骤、人类可读开始时间、该任务最后活动时间与无进度分钟数，示例：`本次“获取元信息”自 2026-08-21 17:22 开始，已 15 分钟未收到该任务进度更新，已停止本次尝试。`

超时事件写入 `SystemEvent`：`job.attempt.timeout`，关联该 Job 与当前步骤。当前 `JobStep` 同时标为 `FAILED` 并保存相同原因。用户可以通过“重试”显式开始下一次尝试，系统增加 `retry_count` 并重新设置 Job 与步骤的开始时间；不得静默循环重试。

任务详情不再以 `489:03` 形式展示分钟与秒。时长小于一小时显示“xx 分 xx 秒”，大于等于一小时显示“x 小时 xx 分”。停滞任务不得使用“当前尝试 / 本次尝试”等术语；卡片必须用完整句表达：`开始于 昨天 17:22`、`8 小时未收到进度更新`、`任务可能停滞，建议查看日志或重试`。这表示 Worker 自该开始时间后未报告进度，不表示模型或视频内容正常处理了 8 小时。时间线使用同一语义并附最后活动时间，不把旧事件伪装为实时进度。

## 6. 步骤独立进度

任务 `progress` 是全流程总进度，只允许出现在任务标题或列表的总进度条。`JobStep.progress` 改为步骤自身 0–100 的进度：步骤开始为 0，完成为 100；有真实子任务数据（例如字幕段落、下载字节、地点条目）时才更新中间值。时间线不得复用全局 12%、15% 等里程碑数字。

步骤无法产生可量化中间值时显示“进行中，等待下一项活动”，不显示伪造的 0% 或总任务百分比。事件会同时记录 `job_progress` 与 `step_progress`，以便日志与页面均可明确区分两个维度。

## 7. 验收

1. 以包含 `inactive` 和 `occupied by compressor` 的 macOS 页统计输入，内存占比按可回收口径计算，不再接近 95% 的缓存误计结果。
2. 浮窗显示 `已用 GB / 总 GB`、可回收、压缩、磁盘容量、四项服务状态、采样与 Worker 心跳。
3. 新增模型依次选择 Moonshot 与智谱，模型名/Base URL 依次变为各自预设；不保存草稿即可观察到变化。
4. 手工改写模型名或 Base URL 后切换 Provider，该单项保留，未手填项仍更新。
5. 对重试过的步骤，API 返回的 `current_step_started_at` 为当前尝试而非初始旧时间。
6. 普通步骤运行中 90 秒无活动、LLM 步骤 300 秒无活动时显示“任务可能停滞”，并显示开始时间和“x 分钟未收到进度更新”；正常任务保留实时连接或轮询信息。
7. 超过 900 秒没有该任务自身活动的任务返回 `ATTEMPT_TIMEOUT` 与可读原因；全局 Worker 仍正常时也必须正确触发，不得把全局心跳当作任务进度。
8. 标题总进度与时间线步骤进度不会混用；已完成步骤为 100%，运行步骤显示自身进度或“进行中”。
9. API 状态、浏览器控制台、Ruff、后端测试、前端 lint/test/build 均通过。
10. 长模型调用持续超过全局心跳阈值时，服务状态仍为 Worker 运行中；若同一 Job 超过其 LLM 活动阈值未产生 batch/阶段事件，只有任务详情显示“任务可能停滞”。
