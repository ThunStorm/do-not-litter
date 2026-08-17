# Golden Samples & Feasibility Baseline

> 状态：Baseline v0.2
> 冻结日期：2026-08-13
> 用途：登记 MVP 首批真实样本、Fixture 获取规则、技术 Spike 与质量门槛。

---

# 1. 样本使用原则

1. 真实 URL 用于手工验收与定期兼容性检查，不作为 CI 的实时网络依赖。
2. 首次成功解析后，保存脱敏且许可范围内的 HTML、附件、字幕、POI 候选响应为 Fixture。
3. Fixture 必须记录获取时间、原始 URL、内容哈希、Resolver/Parser 版本；不得保存 Cookie、Token 或浏览器 Profile。
4. 微信、Bilibili 等来源若受登录态、验证码、风控或 412 限制，按 `HTTP → Playwright 持久 Profile → NEEDS_USER` 处理，不绕过平台限制。
5. 公众号正文中的官方公告和附件允许按 Source Graph 规则下钻；默认 `max_depth = 2`、单来源最多跟随 30 个链接。
6. 黄金样本内容可能随来源页面更新或失效；验收以冻结 Fixture 为可复现基准，以真实 URL 为补充手工验证。

---

# 2. Recruitment 黄金样本

首域：北京市公务员、事业单位招聘及相关考试公告。

## R-001

- 类型：微信公众号招聘汇总/入口文章
- URL：`https://mp.weixin.qq.com/s/_A_u11jr_FDA58sQ5QkBhg`
- 目标：验证微信 Resolver、正文解析、官方来源下钻、附件发现、Notice/Position/Requirement/Evidence 全链路。
- 当前网络特征：普通无状态 HTTP 无法稳定读取，必须验证 Playwright 持久登录态与 `NEEDS_USER` 路径。

## R-002

- 类型：微信公众号招聘汇总/入口文章
- URL：`https://mp.weixin.qq.com/s/HTw6_R4YICpLCFFl6PO4Yg`
- 目标：作为第二种页面结构与下钻关系样本，避免 Resolver 只适配单页。
- 当前网络特征：普通无状态 HTTP 无法稳定读取，测试策略同 R-001。

## 招聘 Fixture 最小集合

每个样本应尽量冻结：

- 微信正文 HTML；
- 下钻后的官方公告 HTML/PDF/DOCX；
- 岗位 XLS/XLSX；
- 扫描 PDF 或图片型公告（若来源存在）；
- Source Graph 期望结果；
- 关键日期、岗位数、字段映射、Requirement DSL 与 Evidence 的人工校验答案。

---

# 3. Travel/Food 黄金样本

## T-001

- 标题：厦门街头米其林小馆，连吃两家爽了…
- URL：`https://www.bilibili.com/video/BV189ui6LEhK`
- 类型：探店视频
- 目标：字幕优先、餐厅/菜品/价格/作者观点抽取、厦门 POI 解析、重复地点合并、时间码 Evidence。

## T-002

- 标题：不只是凉快，一口气逛遍贵州全省43个景区，TOP10你去过几个？｜全景推荐03
- URL：`https://www.bilibili.com/video/BV1qF3t6TENn`
- 类型：多地点旅行视频
- 目标：长视频字幕/ASR、43 地点批量抽取、Partial Materialization、高德 POI 候选、地图与 Review 队列。
- 当前网络特征：无状态抓取可能返回 412，必须覆盖浏览器/媒体解析 fallback 与 `NEEDS_USER`。

## 旅行 Fixture 最小集合

- 元数据与封面引用；
- 平台字幕（若有）或经授权生成的本地 Transcript；
- 时间码 Segment；
- 人工校验的 PlaceMention/Observation；
- 脱敏后的 Mock 高德 POI 候选响应；
- Confirmed/Review/Unresolved 期望状态。

不把完整受版权保护的视频提交到 Git。测试仓库仅保存短小、必要、合法的派生 Fixture；本地媒体放入被忽略的数据目录。

---

# 4. Phase 0A 技术 Spike

正式业务实施前必须在用户选中的目标节点完成；若要比较两套方案，则在 Windows PC 与 Mac mini 上分别执行并保存结果：

1. `LAN_ACCESS`：手机通过同一局域网访问前后端，验证 Token-to-Session、CORS、WebSocket 重连、Admin API 保护，并比较本地 HTTPS 与可信 LAN HTTP 的可部署性。
2. `WECHAT_RESOLVER`：R-001/R-002 至少一个可通过持久浏览器 Profile 获取正文并发现下钻链接；失败时能进入 `NEEDS_USER`。
3. `DOCUMENT_MATRIX`：验证 HTML、PDF、扫描 PDF、DOCX、XLS/XLSX、PNG/JPEG 的文本与定位信息。
4. `OCR`：中文 OCR 输出页码/边界框/置信度，低置信内容进入 Review，不直接生成高风险事实。
5. `LOCAL_LLM`：Windows 记录 RX 7900 XT/Ollama 的显存占用与吞吐；Mac mini 记录 M4/Ollama Metal 的统一内存峰值与吞吐；两者都记录 JSON Schema 成功率。
6. `ASR`：Windows 验证 whisper.cpp Vulkan；Mac mini 验证 whisper.cpp Metal，并在启用时单独验证 Core ML encoder；两者都输出中文时间码 Transcript。
7. `EXTERNAL_LLM`：DeepSeek 与 Xiaomi MiMo 至少各完成一次 OpenAI-compatible 连接测试、结构化输出测试与审计记录测试。
8. `AMAP`：高德 Web 服务 POI 搜索、JS API 2.0 地图渲染、GCJ-02 坐标与配额错误路径。
9. `SQLITE_MULTI_PROCESS`：FastAPI + Worker 下 WAL、原子 Job Lease、崩溃恢复与幂等写入。
10. `SERVICE_SUPERVISION`：Windows 验证 launcher/服务或计划任务，Mac mini 验证 `launchd`；崩溃和重启后 API、Worker 与未完成 Job 均可恢复。
11. `PLATFORM_SECRET_STORE`：Windows 验证 Credential Manager/DPAPI，Mac mini 验证 Keychain；SQLite、日志和导出均不得出现 Secret 明文。

每项记录：环境版本、命令、输入、结果、耗时、资源占用、失败原因、是否阻塞后续 Phase。

---

# 5. 初始质量门槛

在黄金 Fixture 上：

- 关键报名/考试日期：人工标注项 100% 有正确值或明确进入 `UNKNOWN/REVIEW`，不得静默给出错误确定值；
- Eligibility：不得把人工标注的明确 `FAIL/REVIEW` 自动判为 `PASS`；
- Evidence：所有 `EXTRACTED` Claim 100% 可回到有效 Segment/Cell/Page/时间码；
- Excel 岗位行：不得静默丢行，无法可靠识别的行必须进入 Review 并报告计数；
- OCR：低于配置阈值的文字不得作为无需复核的关键日期或硬性资格依据；
- POI：只有高置信且候选唯一时自动 `CONFIRMED`；黄金样本中的误确认数必须为 0，其余进入 `REVIEW/UNRESOLVED`；
- Job：崩溃恢复不丢任务，业务结果幂等，不重复生成最终实体；
- LAN：未携带有效 Token 的 API、WebSocket 和 Admin 请求全部拒绝。

吞吐、ASR 速度、LLM Schema 首次成功率等性能指标由 Phase 0A 在目标主机实测后补入，不凭空设定。

---

# 6. 尚待补充的样本

- 至少一份北京市官方 DOCX 招聘附件；
- 至少一份扫描 PDF 或图片公告；
- 至少一份结构复杂的 XLS/XLSX 岗位表；
- R-001/R-002 的人工期望答案与脱敏 Fixture；
- T-001/T-002 的人工地点清单与时间码答案。
