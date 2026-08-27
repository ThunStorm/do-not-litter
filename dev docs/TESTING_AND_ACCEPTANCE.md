# Testing & Acceptance

> 实施回归的不可回退功能清单见 `REGRESSION_AND_CHANGE_GUARD.md`。每次跨模块改动均应先过该清单，再执行本文件的专项验收。

## 1. 测试原则

本项目最危险的问题不是页面 Bug，而是：

- AI 误提取；
- 资格误判；
- Evidence 丢失；
- Job 重启丢失；
- POI 错认；
- 模型版本变化导致行为漂移。

因此测试必须覆盖 Pipeline 与业务规则。

---

# 2. Test Layers

## Unit
- Rule Engine
- Requirement DSL
- MajorMatcher
- Information Gain
- Preference scoring
- Job state transition
- Capture Input Normalizer

## Fixture
- HTML Resolver
- WeChat Snapshot
- Excel
- PDF
- DOCX
- scanned PDF / image OCR
- Transcript
- POI candidates
- share text with embedded URL

## Integration
- Capture → Job
- raw paste → selected URL → Source locator
- Recruitment End-to-End
- Travel End-to-End
- External LLM fallback
- Worker recovery

## UI
- Dashboard
- Control Center
- Evidence drill-down

## Capture Input Normalizer

至少覆盖：

1. 前后空白的纯 URL → `URL_ONLY`；
2. 标题 + 换行 + Bilibili URL + “复制打开” → `SHARE_TEXT_WITH_URL`，后续 payload 只有 URL；
3. Markdown `[标题](URL)` 与 `<URL>`；
4. URL 后的 `。`、`，`、`)`、`】`、引号被正确剥离，query/fragment 保留；
5. 相同 URL 或 canonical 后相同的短链去重；
6. 多个候选但只有一个命中专用 Resolver时自动选择；
7. 多个不同内容 URL → `CAPTURE_MULTIPLE_URLS`，不创建 Job、不访问网络；
8. 无 URL 普通文段 → `TEXT_ONLY`；
9. 分享标题不覆盖平台正式标题，不进入 LLM/Claim/Evidence；
10. 日志和数据库不保存被丢弃分享文案全文。

---

# 3. Requirement DSL Tests

至少覆盖：

- ALL
- ANY
- NOT
- nested ALL/ANY
- HARD
- SEMANTIC
- PREFERENCE
- UNKNOWN propagation
- REVIEW propagation

---

# 4. Rule Engine Acceptance

案例：

```text
ALL(PASS, PASS) → PASS
ALL(PASS, FAIL) → FAIL
ALL(PASS, UNKNOWN) → UNKNOWN
ALL(PASS, REVIEW) → REVIEW

ANY(FAIL, PASS) → PASS
ANY(FAIL, FAIL) → FAIL
ANY(FAIL, UNKNOWN) → UNKNOWN
ANY(FAIL, REVIEW) → REVIEW
```

---

# 5. MajorMatcher Tests

- exact code
- exact name
- category
- official mapping
- old/new mapping
- semantic similar → REVIEW
- unknown catalog → NEED_FETCH / REVIEW

禁止语义匹配自动 PASS。

---

# 6. Evidence Integrity

每个 `EXTRACTED` Claim：
- 至少 1 Evidence；
- Evidence Segment 存在；
- Segment 对应 Snapshot；
- Snapshot 对应 Source。

发现孤儿 Claim：
测试失败。

`NORMALIZED` / `COMPUTED` Claim 必须具有有效 Claim 血缘；冲突 Claim 必须同时保留，不能靠最后写入覆盖。

---

# 7. Recruitment E2E

Fixture 包含：
- 公众号快照
- 政府公告
- Excel 岗位表

验收：
- 自动下钻；
- 解析时间；
- 解析岗位；
- 生成 DSL；
- Profile 匹配；
- Deadline；
- Evidence 可回溯。

---

# 8. Travel E2E

Fixture：
- 本地 Transcript
- Bilibili metadata/subtitle/无字幕响应
- DeepSeek 分块与合并响应
- 视频帧、黑帧、模糊帧和重复帧 Fixture
- 地点候选
- Mock POI Provider
- 中国大陆 bbox/zoom/cluster 和 Marker 生命周期

验收：
- PlaceMention；
- POI；
- Dedup；
- Preference；
- Map ViewModel；
- Evidence timestamp。
- AI Note Version；
- Place Note Version；
- 视频笔记、列表和 Marker 进入同一 Place Detail。

视频专项验收：

1. BV、`b23.tv` 与 `?p=N` 均能 canonicalize；
2. 平台字幕命中时 `DOWNLOAD_AUDIO/ASR` 为 `SKIPPED`；
3. 无字幕时 yt-dlp + FFmpeg + ASR fallback；
4. 长 Transcript 分块失败后可从 checkpoint 恢复；
5. DeepSeek 429/5xx 有限重试，Key/余额错误不盲重试；
6. AI Note 成功、POI 歧义时为 `PARTIAL_SUCCESS`；
7. 每个地点事实引用 Transcript Segment，不只引用 AI Markdown；
8. 同一高德 POI 来自多个视频时只有一个 Marker；
9. 重跑复用 Transcript 并新增 Note Version；
10. BiliNote 移植文件保留 MIT 声明和参考 revision。
11. 每个主要地点 1–3 张、全文默认 3–12 张截图，均有时间码与来源绑定；
12. 黑帧、模糊帧和感知重复帧不会进入 Note；
13. 餐馆、景区、街区、步行街、商圈和市场可区分；
14. 转写同音/错别字名称经高德校正，raw/canonical 同时保留；
15. 首次地图加载无默认城市参数、标题或厦门 fallback；
16. 全国 bbox/zoom/cluster 和 viewport 恢复；
17. Marker 点击在地图浮窗查看简介并进入统一详情；
18. 用户 Marker 新增、软删除、恢复；
19. 自动 Marker 隐藏不删除 Source/Evidence；
20. 高德 JS Key、Security Code、Web 服务 Key 可配置并分别诊断。
21. 内容页写入并跳转 `AINote.id`；历史 `AINoteVersion.id` 链接仍能由共享 API 兼容解析，未知 ID 返回可见 404，不永久显示“正在读取视频笔记”。
22. `/api/status` 不响应时 SessionGate 在有界时间内进入可重试状态；服务恢复后无需重新配对即可进入目标页面。
23. Ollama 请求体包含 `keep_alive: 0`；成功、HTTP 失败、JSON 解析失败、备用模型与设置页真实测试后均释放本次模型，清理失败不覆盖原结果。
24. Bilibili 横屏与竖屏 Fixture 都能选择 video-only DASH 流；真实样本 `BV1JH826zEKC` 不再出现 `Requested format is not available`，并生成至少一张 `READY` 截图。
25. Whisper.cpp JSON offset `2800` 写入后仍为 `2800 ms`，不得变成 `28000 ms`；末段时间显著超过视频时长时，Note 与截图步骤不得继续物化。
26. 样本 `note_221cd61e9600493cb3f32e062e1ad013` 的 10 倍历史时间轴生成修正版 Transcript Version，页面时长、章节时间码、导出时间码和截图定位一致。
27. 任意非空 Transcript 均同时得到摘要和至少一个“按时间线详述”章节；章节按时间递增并覆盖末个 Segment。模型返回全部无效 `segment_ids` 时使用服务端分块引用和转写整理兜底，不得得到 0 章节。
28. 无 Note Section 时截图计划仍从有效 Transcript 生成 3–6 个候选；`plans == 0` 不下载视频、不把截图步骤记为成功，并显示稳定错误原因。
29. “导出完整转写（TXT）”包含所有 Segment、完整时间范围和来源元数据，不只包含页面前 8 段；响应为附件且服务端不产生持久导出文件。
30. Transcript 创建后第 179 天仍可读取/导出，第 180 天清理任务幂等清空正文、Segment 文本、Evidence quote 和全文 fingerprint；Note/时间线/截图仍可读，Transcript/导出返回 410，审计日志不包含原文。
31. 全部 Segment 生成 corrected_text，Segment ID、顺序和时间范围不变；缺段/新增 ID/乱序的模型输出被拒绝。
32. 口音、同音字、断句、重复词和专有名词校对符合人工答案；不确定地名进入 Review，不编造事实。
33. 默认 Transcript 预览、Note 和 TXT 导出使用 corrected_text；raw_text 只从审计入口读取。
34. Hero 后进入摘要/目录/正文；地点候选与完整转写在文章最底部，PC 双列、Mobile 纵向，无横向溢出。
35. 地点、Transcript Segment、目录和截图时间码均跳转正确 Section，更新锚点、聚焦并短暂高亮；前进/后退恢复。
36. 目录每项具有具体 heading 与 20–50 字 thesis，不出现“本段继续介绍”等泛化套话。
37. “按时间线详述”由 summary/bullets/place refs 组成，不连续铺原始转录句子，并覆盖完整校对稿。
38. READY 截图以 220–280px 缩略图放在对应 Section 文字侧面；仅章节起始 talking head、片头、转场不作为关键帧。
39. 截图 caption 说明实际关键内容，不统一显示“章节起始时间码代表帧”。
40. 点击截图打开 contain 灯箱，上一张/下一张、Escape、遮罩和关闭按钮均可用，关闭后焦点恢复。
41. “导出 TXT”使用统一次级按钮视觉，默认导出 corrected 版本；raw 导出只在审计区域。
42. VideoAsset.cover_url 的 HTTP/协议相对 URL 规范为 HTTPS，只有允许的 Bilibili 图片 CDN host 可下载。
43. JPEG/PNG/WebP/AVIF 封面按状态、MIME、文件头、尺寸和最大字节验证，HTML/SVG/损坏响应被拒绝。
44. 原始封面按 SHA-256 去重并生成 672×378 WebP；同一 VideoAsset 多 Note Version 不重复下载。
45. Video Note List 使用本地 cover_image_url、16:9 object-fit cover 和时长徽标；失败时布局稳定显示占位。
46. 列表顶部主按钮文案为“添加视频链接”，PC 40px/14px，Mobile 不放大且符合全局 Primary Button 状态。
47. C 步骤 ERROR 且 A/B Artifact 有效时，续跑只执行 C 及下游；A/B 记录 REUSED 且不产生新外部调用。
48. Replay Cache 24 小时内可用并显示剩余时间；到期后返回 `REPLAY_ARTIFACT_EXPIRED`，只能完整重跑。
49. 输入/模型/Prompt 改变时，服务端从最早失效步骤续跑；前端不能任意指定 from_step。
50. 任务详情和日志显示“从错误步骤继续”、复用/重跑步骤；旧“重跑所属任务”不再代表整 Job 重跑。
51. 视频笔记列表/详情删除共用同一 API；删除 Note 后 Source、VideoAsset、CoverAsset、Transcript、Place 和 Evidence 仍存在。
52. 活跃生成 Job 阻止删除；确认框展示标题、保留边界和不可恢复。
53. Hero 缺封面时区域为空/收起，不显示场记板占位；地点候选和完整转写位于文章最底部。
54. 目录符合主体暖白/朱砂/衬线/细分隔线语言；截图以 220–280px 缩略图侧排并可打开 contain Lightbox。

55. 单 Worker 运行超过 `worker_heartbeat_seconds * 3` 的模型批次时，`/api/status.services.worker` 仍为 `RUNNING` 且进程心跳持续推进；该 Job 的停滞只依据自身活动时间。
56. `CORRECT_TRANSCRIPT` 进入多批模型请求后取消：当前受控 HTTP 请求结束后不再发起下一批，写入 `job.cancel.observed` 并释放 lease。
57. 429/5xx/超时不会通过递归二分放大同一批外部请求；仅 payload/结构问题允许缩小批次，batch 开始/结束均写入非敏感进度事件。
58. 运行或排队中的 Job 点击右上角“从头重新运行”：旧 Job 进入协作式取消，新 Job 立即创建为 `QUEUED`，响应返回新旧 Job ID，前端导航到新 Job。
59. LaunchAgent 部署在外置卷时，`manage.py status` 必须验证 `/health`、首页正文非空和 75 秒内 Worker 心跳；`launchctl running` 不能单独判定健康。
60. Worker 启动时无法冷导入视频 Pipeline 则不领取 Job；处理中的未捕获异常立即返回 `FAILED/WORKER_UNHANDLED_EXCEPTION`、释放 lease 并写审计。
61. 步骤恢复卡仅在 Replay Options 可用时显示续跑按钮；不可续跑时仅提示原因，不重复显示完整重跑按钮。
62. 通用设置默认返回 `ai_retry_count=2 / ai_retry_wait_seconds=5 / ai_request_interval_seconds=1`，保存后下一次 Pipeline AI 调用生效。
63. 429/408/409/425、超时、连接失败、可恢复 5xx 与空响应按设置有限重试；每次调用前执行配置间隔，重试事件记录 attempt、limit、wait 和脱敏原因。
64. LLM 步骤在 600 秒内不显示“可能停滞”；900 秒真实 Attempt 终止阈值保持独立。
65. `GET /api/settings/prompt-supplements` 默认返回三项空补充、只读核心规则摘要与 1000 字符上限；保存语气/篇幅偏好后可读回。
66. PUT 包含“忽略系统规则”“修改 JSON/字段/ID/顺序”等越权语言返回 422，且原设置不变。
67. 补充文本会作为低优先级 System Message 插入三个对应 LLM 阶段；固定 Prompt、JSON 解析和 Segment ID 校验仍保持生效。
68. 失败 Job 在某个补充 Prompt 哈希改变后，Replay Options 返回最早受影响的 AI 步骤，不允许从更晚步骤绕过重算。
69. 生产 LaunchAgent 的 `program` 均指向 `/Volumes/D/Library/Application Support/Zhijian/venv/bin/python`，解释器为 Python `3.14.6`；切换后 `/health`、首页正文、Worker 心跳、Keychain 可用性和外置卷 deny 日志均符合部署手册要求。

---

# 9. Job Recovery

场景：
1. 创建 RUNNING Job；
2. 模拟 Worker 异常停止；
3. heartbeat 超时；
4. Job 回 QUEUED；
5. 新 Worker 接管。

验收：不丢任务、不重复写最终结果。

运行日志手动重跑专项验收：

1. 点击普通 INFO/WARNING 或无 Job 关联事件，只打开详情，不显示重跑按钮；
2. 点击 `ERROR/CRITICAL + entity_type=job` 事件，抽屉显示所属任务当前状态、步骤和重试次数；
3. `FAILED / PARTIAL_SUCCESS / NEEDS_USER` 与 lease 已释放的 `CANCELLED` 可确认重跑；`QUEUED / RUNNING / COMPLETED`、取消未释放、已删除 Job 均不可误触发；
4. 确认前没有请求；连续双击只产生一次重入队，第二次由 pending 禁用或服务端 409 拒绝；
5. 请求携带 `source_event_id`，服务端拒绝非 ERROR/CRITICAL、归属不匹配或不存在的事件；
6. 成功后 Job 为 `QUEUED`、`retry_count + 1`，产生包含来源事件 ID 的 `job.retry.queued`，日志页保持同一 Job 筛选并可进入重跑进度；
7. Worker 按 Pipeline 定义顺序执行，前端不需要逐步点击；输入哈希一致的缓存是否复用由 Pipeline 决定；
8. 新 attempt 再次失败时生成新 ERROR 事件，旧事件仍保留；敏感正文、Cookie、Key 不进入确认框或审计 detail。

---

# 10. Replay

Recruitment：
从 `BUILD_REQUIREMENTS` 重跑，不重新抓 Source。

Travel：
从 `EXTRACT_PLACES` 重跑，不重新 ASR。

---

# 11. External LLM

Mock：
- Local validation fail twice；
- Local First 策略；
- External Provider 被调用；
- 记录 provider/model；
- 仍执行 Evidence Validator。

---

# 12. PC Hardware Acceptance

安装诊断：

- Python
- SQLite
- ffmpeg
- Playwright browser
- Ollama
- Apple Silicon / Metal runtime detected
- whisper.cpp
- model availability
- disk writable
- Node.js 20.19+ 或 22.12+
- LAN mobile access / token auth
- AMap API / map render
- DeepSeek / Xiaomi MiMo connection

CMS 显示诊断结果。

---

# 13. MVP Acceptance Definition

系统达到 MVP，需要至少满足：

1. 用户可以粘贴招聘链接；
2. 后台可见 Job；
3. 能解析至少一种真实招聘公告 + Excel；
4. 能形成岗位资格结果；
5. Evidence 可点击回溯；
6. 用户补 Profile 后自动重算；
7. 用户可粘贴 Bilibili 链接；
8. 能得到字幕或 ASR；
9. 能提取并确认地点；
10. 地点可出现在地图 ViewModel；
11. 可 SAVE / DISMISS / VISITED；
12. PC 重启任务可恢复；
13. 外部模型 API Key 可配置且可测试；
14. 所有核心长任务可从 CMS 重试。
15. 手机可在同一局域网安全访问，未授权请求无法读取业务或管理数据；
16. DOCX、扫描 PDF 与图片公告可归一化并保留 Evidence 定位；
17. 高德 POI/地图可用，GCJ-02 在存储与导出中明确标注；
18. DeepSeek、Xiaomi MiMo 可通过兼容 Provider 配置和测试；
19. `GOLDEN_SAMPLES.md` 的安全与正确性门槛全部通过。
20. Bilibili 视频可生成完整、带时间码和版本记录的 AI 笔记；
21. 地点可生成跨来源归纳笔记，视频笔记、列表和地图 Marker 均进入同一地点详情；
22. 已配置 DeepSeek Provider 可完成长字幕分块总结，外部调用可审计且 API Key 不进入日志。
23. 视频笔记包含与章节/地点时间码绑定的代表性截图；
24. 餐馆、景区、街区等细粒度地点具有特色简介并通过高德校名；
25. 地图以中国大陆全境为首次视野，不使用默认城市，支持 bbox、zoom、cluster 和视野恢复；
26. Marker 浮窗、用户新增、隐藏、软删除和恢复均可用，且不破坏 Place/Evidence；
27. 设置页可填写并测试高德 JS Key、Security Code 和 Web 服务 Key。
28. 粘贴标题/分享话术与唯一链接时只处理该 URL；多个不同内容链接返回候选且不静默选择。
29. 视频笔记阅读体验符合 `VIDEO_NOTE_READING_EXPERIENCE_V042_SPEC.md`：顶部证据区、AI 校对稿、主旨目录、段落跳转、随文截图与灯箱全部通过。
30. 视频笔记列表符合 `VIDEO_NOTE_LIST_V043_SPEC.md`：按钮文案/尺寸和真实本地封面全部通过。
31. 步骤级续跑符合 `PIPELINE_STEP_REPLAY_V044_SPEC.md`；中间产物有效时不重跑上游，过期后只允许完整重跑。
32. 视频笔记删除符合 `VIDEO_NOTE_DELETE_V044_SPEC.md`，共享数据和证据不受影响。

---

# 14. PC 运维 UI v0.3 验收

下一实施阶段必须执行 `OPERATIONS_UI_SPEC.md` 第 8 节的全部验收，至少覆盖：935×886 有效视口和 125%/150%/200% 缩放下无重叠；当前步骤、子状态、计时与最后活动 3 秒内更新；Worker 心跳延迟/疑似停滞阈值；时间线按 Pipeline 顺序；日志组合筛选、游标分页、详情深链和脱敏导出；侧栏 CPU/内存/数据盘/Worker 心跳与真实状态接口一致；键盘全流程与不依赖颜色的状态表达。

该验收组的代码实现已完成：任务详情采用 WebSocket/轮询回退，日志页支持组合筛选、游标分页、详情抽屉与脱敏导出，侧栏读取持久化运行指标。自动回归见 `REGRESSION_AND_CHANGE_GUARD.md`；原生 PC/手机浏览器缩放点击回归需在具备 Computer Use 或 Browser 控制器的会话补录，不能以设计稿代替。
