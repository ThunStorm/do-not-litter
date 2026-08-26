# 至简 移动会话、视频诊断与任务控制规格

版本：v0.8，更新日期：2026-08-25，状态：`IMPLEMENTED / BROWSER_VERIFIED`。适用：Mac mini 局域网服务与手机浏览器。

## 1. 可信会话刷新

局域网配对成功后，服务以 HttpOnly 会话 Cookie 保存授权，不保存原始 4 位配对码。SQLite 读取到的 `AccessSession.expires_at` 必须统一按 UTC 解释后比较；无时区数据库值不得抛出 500。Cookie 使用根路径、7 天 Max-Age、显式 Expires 与 `SameSite=Lax`，HTTP 局域网环境仅在非 HTTPS 时不设置 Secure。

手机刷新时，前端只在 `/api/status` 返回 401/403 时进入配对页。500、网络不可达或其他服务错误必须进入“暂时无法连接 Mac mini”状态并提供重试，不得要求用户再次输入配对码。配对成功后刷新页面仍必须保留已授权状态，直至 Cookie 过期、配对码轮换撤销会话或用户清除浏览器数据。

## 2. 手机投递与视频资产复用

手机投递链接的 HTTP 请求仅创建 Source/Job 并立即返回持久 Job；认证错误、参数错误和后台视频处理错误必须分层显示。重复投递同一 Bilibili canonical URL 时，VideoAsset 按 canonical URL 复用，不得再次插入并触发唯一约束。数据库写入异常必须回滚当前事务，再用干净 Session 写入稳定错误码和审计事件，Worker 不得因 `PendingRollback` 退出。

## 3. 阶段诊断日志

视频任务每个阶段最少记录“开始、外部请求、关键检查点、完成/失败”四类审计事件。`FETCH_METADATA` 必须可区分：Bilibili 元数据请求、BV/CID 解析、视频资产查询、资产复用/创建、元数据写入。日志 detail 必须包含 `job_id`、`step`、`phase`、非敏感耗时与可人工判断的对象标识（BV、CID、字幕轨数量、缓存命中），不得包含 Cookie、Key、完整请求正文。

任务详情错误卡显示稳定错误码、可读原因与“查看关联日志”入口。阶段日志中的每个错误需要给出可操作提示，例如 `VIDEO_METADATA_FAILED` 提示检查链接/网络，`VIDEO_LOGIN_REQUIRED` 提示补充 Cookie，`ATTEMPT_TIMEOUT` 提示查看该步骤日志后重试。

## 4. 取消与重试门禁

取消是协作式停止：API 先将 Job 和当前 Step 标为 `CANCELLED`，保留 lease owner 直到 Worker 在当前可中断边界确认取消。视频与通用 Pipeline 在每个步骤开始、外部调用返回后、物化写入前检查 Job 状态；若已取消，停止后续步骤、清理临时音频/Cookie、写入 `job.cancel.observed`，再释放 lease。取消后不得生成内容、覆盖结果或重新入队。

“重试”只允许终态 Job，且取消中的 Job 必须等待 Worker 确认并释放 lease 后才能重试；否则返回 409 和“正在停止当前阶段”。重试重置 Job 的运行字段与所有未完成 Step 的运行状态/错误，增加 `retry_count`，再入队。Worker 启动时会释放已过期的取消 lease，避免崩溃后永久占锁。

### 4.1 长模型步骤的取消观察与完整重跑（已实施）

`CORRECT_TRANSCRIPT`、长字幕总结、地点提取等会连续发出多批模型请求。每一批请求开始前、请求返回后、递归拆分前和数据库物化前都读取持久 Job 状态；发现 `CANCELLED` 即抛出统一取消信号，停止尚未开始的批次、释放 lease 并写入 `job.cancel.observed`。已经发出的单次 HTTP 请求不能被 SQLite 状态反向中断，因此转写校对单批超时上限为 90 秒，不沿用模型配置的 300 秒上限。

429、5xx、网络错误和超时不再通过递归二分放大外部调用；只有响应结构校验失败才缩小批次。校对按最多 2400 字符、16 段组织批次，每一批开始和结束写入 `batch_index / batch_total / provider / duration_ms` 的脱敏活动事件。

取消中的页面状态必须是“正在停止当前步骤；确认停止后可从头重新运行”，而不是把禁用的“从头重新运行”伪装成可点击操作。`CANCELLED` 且 lease 已释放时允许完整重跑；仍持有 lease 时后端返回不可用原因。前端不得硬编码终态名单，而应读取服务端返回的操作能力。

## 5. 验收

1. 使用非 localhost 会话访问 `/api/status`、`/api/capture`、`/api/content` 不再产生无时区比较 500；刷新手机页面保持会话。
2. 已授权手机在服务临时 500 时看到连接诊断与重试，不回到配对页。
3. 重复 Bilibili 链接创建新 Job 时复用现有 VideoAsset，不发生 canonical URL 唯一约束失败。
4. `FETCH_METADATA` 日志可定位到外部请求、CID、资产复用/创建和元数据写入；日志不泄露 Secret。
5. 取消运行任务后，当前流程在下一个可中断边界停止，临时文件清理，lease 释放；取消确认前重试返回 409，确认后可入队重试。
6. 取消处于多批模型校对的任务后，至多等待当前受控 HTTP 请求结束，不再发起下一批；`job.cancel.observed` 在 lease 释放前出现。
7. 已取消且 lease 已释放的任务可从详情页完整重跑；取消进行中显示服务端原因并持续刷新，不存在永久禁用按钮。
