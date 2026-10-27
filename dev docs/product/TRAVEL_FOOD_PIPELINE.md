# Travel / Food Pipeline

> 视频链接到 AI 笔记、BiliNote 复用边界、DeepSeek 分块总结、地点归纳笔记与多入口导航的冻结契约见 `video/VIDEO_AI_NOTE_PIPELINE.md`。本文件继续定义 Travel/Food 的领域抽取、POI、偏好和地图规则；发生冲突时，专项文档中的视频链路规则优先。

## 1. 目标

将视频/图文中的旅行与探店信息转换成：

- 带时间码 Transcript；
- 地点候选；
- 现实 POI；
- 餐厅/景点；
- 菜品/价格/作者评价；
- 用户偏好匹配；
- 地图；
- 收藏/想去/去过；
- 可导出数据；
- 全程可追溯 Evidence。

第一版地域为中国范围，POI 与地图首选高德；真实样本见 `testing/GOLDEN_SAMPLES.md`。

---

# 2. Pipeline

```text
CAPTURE
↓
RESOLVE_SOURCE
↓
FETCH_METADATA
↓
FETCH_SUBTITLE
↓
DOWNLOAD_MEDIA（必要时）
↓
ASR
↓
SEGMENT
↓
EXTRACT_PLACES
↓
RESOLVE_POI
↓
DEDUPLICATE
↓
MATCH_PREFERENCES
↓
MATERIALIZE
↓
CLEAN_CACHE
```

`FETCH_SUBTITLE / DOWNLOAD_MEDIA / ASR` 之前必须完成平台 URL 规范化和视频元数据抓取；`SEGMENT` 后先生成版本化 AI 视频笔记，再执行地点结构化抽取。AI 笔记是用户可阅读的一级产物，但地点事实仍必须引用 Transcript Segment，不得只引用 AI Markdown。

完整顺序为：

```text
VALIDATE_LINK
→ FETCH_METADATA
→ FETCH_SUBTITLE
→ DOWNLOAD_AUDIO / ASR（仅字幕不可用时）
→ NORMALIZE_TRANSCRIPT
→ GENERATE_AI_NOTE
→ EXTRACT_PLACES
→ RESOLVE_POI
→ BUILD_PLACE_NOTES
→ PLAN_SCREENSHOTS
→ DOWNLOAD_VIDEO_FOR_FRAMES
→ EXTRACT_SCREENSHOTS
→ MATERIALIZE
→ CLEAN_CACHE
```

---

# 3. Transcript First

优先：
1. 平台已有字幕；
2. 浏览器/登录态字幕；
3. 音频下载；
4. whisper.cpp。

第一版不默认做全视频视觉分析。

---

# 4. Transcript Segment

每段保存：

```text
start_ms
end_ms
text
segment_id
```

例如：

```text
03:12.480 - 03:27.120
“今天第一家来到的是……”
```

后续餐厅/景点 Claim 直接挂该 segment。

每个 Segment 同时保留 raw_text 与 AI corrected_text。地点/菜品/特色提取默认使用 corrected_text，Evidence 详情允许对照 raw；校对不得改变 Segment ID 和时间码。无法确定的同音地名先标 Review，再交给高德候选校正，不能由校对模型直接生成 canonical Place。

---

# 5. Extraction 不等于 Summary

第一阶段 AI 任务：

- PlaceCandidate[]
- RestaurantCandidate[]
- DishCandidate[]
- PriceClaim[]
- OpinionClaim[]
- WarningClaim[]
- RankingClaim[]
- RegionMention[]

摘要是辅助，不是核心产物。

---

# 6. PlaceMention vs Place

必须分开。

PlaceMention：
> 内容中“说到了什么”。

Place：
> 现实地图中“到底是哪一个地点”。

流程：

```text
PlaceMention
→ POI Resolution
→ Place
```

多个视频可指向同一个 Place。

---

# 7. POI Resolver

匹配依据：

- 名称相似；
- 城市；
- 区域；
- 附近地标；
- 地址上下文；
- 类别。

状态：

- CONFIRMED
- REVIEW
- UNRESOLVED
- REJECTED

只有 CONFIRMED 默认进入地图。

MVP 实现 `AMapPOIProvider`：使用高德 Web 服务进行候选搜索，优先传城市/adcode 与 `citylimit` 收敛歧义；保存 Provider、POI ID、原始候选响应哈希与 `GCJ02` 坐标系。前端使用高德地图 JS API 2.0。

POI 解析同时承担名称校正：保留转写原文 `raw_name`，高德候选命中后保存 `canonical_name` 与 aliases。必须结合地点类型、城市/区县、附近地标、地址上下文和视频其他地点进行确定性打分；无法唯一确认时进入 Review。城市/省份只作为上下文，不因为被提及就默认创建 Marker。

高德请求使用本机 API/Worker 共用的文件锁，所有 Key 的 text/around/detail 查询统一至少间隔 1.1 秒；缓存和同查询合并按 Key 哈希隔离，命中不发新请求。HTTP 429 或 QPS 错误进入 5 秒冷却，不自动重试、不缓存失败，不将外部限流判为地点识别失败；HTTP 错误不保存带 Key 的 URL。此为保守本机限速，实际账号配额及其他应用流量仍需独立核对，不保证消除外部限流。原历史候选/错误与人工确认保持不变。

## 7.1 地点类型与简介

第一版地点粒度至少包括餐馆、景区、街区、步行街、商圈、市场、公园、博物馆、寺庙、村镇、地标、住宿和交通点。每个 PlaceMention 生成结构化 `PlaceBrief`：

- 景区/街区/店铺特色；
- 推荐菜品或核心体验；
- 价格、排队、环境与营业提示；
- 适合人群、季节与注意事项；
- 作者态度和引用时间码；
- AI 归纳，明确与来源观点区分。

## 7.2 中国大陆全境地图

地图首次进入显示中国大陆全境，不设置默认城市；之后恢复用户上次 viewport。请求以 `bbox + zoom` 为主，city/district 只作为可选筛选。全国尺度使用聚合，放大后展开 Marker。点击 Marker 在地图内打开浮窗/侧浮层，显示代表图、地址、特色、关键菜品/体验、来源数和用户状态，再通过“查看详情”进入统一 Place Detail。

用户可创建 Marker：搜索/逆地理编码优先取得规范 POI，直接点选坐标时标为 `USER_CONFIRMED`。用户 Marker 删除为软删除；自动 Marker 删除只改变地图可见性，不删除 Place/Evidence。所有 Marker 返回 `marker_id + place_id + origin + visibility`。

---

# 8. 禁止 LLM 生成地图坐标

坐标只能来自：

- POI Provider；
- 用户确认；
- 可信地理数据。

LLM 仅能提取地点候选和上下文。

---

# 9. PlaceObservation

内容来源对地点的描述不能直接覆盖 Place。

例如：
视频 A：人均 80
视频 B：人均 120

保存两条 Observation。

类型：
- price
- dish
- author_opinion
- warning
- ranking
- recommended_season
- queue
- environment

---

# 10. 作者观点 vs AI 推荐

作者观点：
`SOURCE_OPINION`

AI 个性化：
`PERSONAL_INFERENCE`

UI 必须明确区分。

---

# 11. 偏好三层

## Explicit
用户明确设置。

## Behavior
收藏/忽略/去过等行为推导。

## Inferred
AI 推断。

优先级：
Explicit > Behavior > Inferred

---

# 12. PreferenceEvent

所有行为先存事件：

- SAVE
- DISMISS
- VISITED
- PLANNED
- LIKE
- DISLIKE

不要直接在点击时永久修改一个神秘分数。

PreferenceLearner 可随时重算。

---

# 13. Trait-based Preference v1

第一版不用复杂向量推荐。

地点可提取 Traits：

- nature
- urban
- historic
- food
- hiking
- island
- commercial
- crowded
- local
- luxury
- budget
- family
- nightlife

Preference 有权重。

推荐理由来自贡献最大的 Trait。

---

# 14. 避免虚假匹配度

不显示：
“匹配度 87%”

展示：
- 优先关注
- 值得考虑
- 一般
- 不符合偏好

并提供解释：

```text
✓ 海岛
✓ 适合步行探索
✓ 本地饮食
△ 游客较多
```

---

# 15. 地点状态

- DISCOVERED
- SAVED
- PLANNED
- VISITED
- DISMISSED

未来 Trip Planner 可直接复用。

---

# 16. Visit / Trip

第一版至少有 VisitEvent。

用于：
- 记录去过；
- 计算“距离上次旅行多少天”。

完整 Trip 可后续加入。

---

# 17. Partial Materialization

贵州 43 地点：

```text
36 Confirmed
5 Review
2 Unresolved
```

主地图立即展示 36。
任务仍可继续。

---

# 18. 视频截图与视觉边界

代表性截图属于第一版视频笔记必备产物，不再只做未来预留。系统根据 Note Section、PlaceMention 和 Transcript 时间码生成计划，下载受限画质视频流并用 FFmpeg 抽帧；每个主要地点 1–3 张，整篇默认 3–12 张。

截图必须过滤黑帧、模糊帧、过曝/欠曝和感知重复帧，并保存实际时间码、文件哈希、尺寸、选择原因以及 Section/PlaceMention/Segment 关系。当前版本使用时间码附近的候选帧与确定性画质规则避开转场；广告语义识别不使用视觉模型，属于后续独立能力。平台禁止下载或资源超限时，笔记可 `PARTIAL_SUCCESS`，但必须明确截图缺失原因。

第一版不默认把所有帧发送给 VisionProvider。店招、菜单、路牌和屏幕价格的多模态识别仍作为后续独立能力；启用时生成新的 Visual Claim/Model Version，不能覆盖 Transcript Evidence。

---

# 19. 视频缓存

临时：
- video
- audio
- full frames

永久：
- transcript
- evidence frames
- note screenshots
- thumbnail
- metadata
- claims

---

# 20. 导出

第一版：
- CSV
- JSON
- GeoJSON

GeoJSON 必须显式附带坐标来源和 `coordinate_system`。中国大陆高德坐标不得静默声明为 WGS84；若未来需要跨坐标系输出，必须由独立、可测试的转换策略完成并标注转换来源。

导出字段尽可能带：
- name
- coordinates
- source_title
- source_url
- source_timestamp
- recommendation_reason
- user_status

---

# 21. Travel Dashboard

TravelDashboardVM：

- days_since_last_trip
- map_places
- recent_discoveries
- recommended_places
- pending_reviews

---

# 22. CMS

视频任务显示：

- Metadata
- Subtitle/ASR
- 当前进度
- 发现 PlaceCandidate 数
- Confirmed/Review/Unresolved
- 模型
- 是否调用外部 API
- 查看字幕
- 查看时间码 Evidence
- 重跑地点提取
- 重跑 POI


## 地图时间与预览契约（2026-10-20）

地图只读查询不补建Marker；旧地点无投影时按可见处理，隐藏/恢复在显式写请求中补建。时间提取与展示拒绝“最美森林”等无时间语义的派生窗口，原记录保留供审计。月份与季节、旬段、时段在同一窗口内匹配；关闭/限制优先，正文具体时间优于无日期或标题上下文。日期范围仅在原句明确时保真展示，不从月份推造日级精度。

只有新版完整分析记录NO_TIME_MENTIONED且无有效时间结论时展示“全年适合 · 默认”；无记录/失败/歧义为“时间待分析”。默认全年不计为最佳或增加推荐得分。正文或标题含时间但归属不明时不标默认全年。历史数据批量更新先只读预览，保留人工记录，不自动确认POI。

预览以查看详情为主入口，加入路线默认折叠；编辑/隐藏等管理操作集中在详情页。时间依据展开后保留完整source_text与来源类型；卡片不重复推荐中的时间理由，空简介/无匹配图不留占位，来源数按独立Source去重。仅有已绑定该Mention的真实截图才能作代表图。路线筛选与加入目标独立；返回地图恢复筛选与视野。详见[实施计划](../planning/MAP_EXPERIENCE_REPAIR_AND_EVOLUTION_PLAN.md)，扩展部分不自动进入当前范围。


### POI确认后的地图可见性（2026-10-20）

人工确认显式将Place置CONFIRMED，首次补建可见Marker投影；复用已隐藏地点保留隐藏状态，已删除地点拒绝静默恢复。前端刷新地图/地点/审核/笔记缓存并通过不含业务数据的BroadcastChannel通知其他同源页面；地图焦点恢复强制刷新，前台15秒兜底轮询，不轮询后台。确认页提供`/map?place=...`入口，以全国视野和清空筛选展示目标；选中地点从聚合中单独显示。全国视野其他地点仍允许聚合，不等于未上图。

## 10.23 地图定位点阅读与编辑需求（2026-10-23）

点击定位点，浮窗优先展示名称、适合时节/天气窗口与最多三条简短记录理由（例如赏雪、云海、雾凇及地点特色）；理由取自已保存且归属明确的正文/地点证据，不用个人偏好分数替代地点价值，不因正文较长而整条隐藏。名称片段之外的时间须回到同版本证据地图：主地点可读取同版本PLACE_GUIDE的完整单元；共享季节继承按10.24规则处理，禁止按整部视频广播月份。明确十二月/冬季/雪后/晴天/早晨等条件应可见且参与同一套筛选；历史初雪日期不直接升级为年度最佳建议，缺少日期不臆造月份。封面只有已核验并保存的视觉证据才能作为时间来源，不把标题或封面主题伪造为转写原句。

浮窗以“查看详情”为主入口，路线默认折叠；不再显示“更多操作”或重复的编辑入口，展开操作不得改变按钮形状。编辑、隐藏/恢复和删除统一在详情中；显示名称、类型、标签与备注进入编辑态后可保存，保留修订号冲突保护、失败反馈及保存成功提示，人工时间补充有明确保存入口。详情与地图共用时间证据；读取旧笔记允许只读补充投影，不回写历史记录、不调用模型、不自动确认POI。验收包含目标笔记note_788c3ea3ba664770818be29fd6cc3e28的真实只读证据、月份筛选、PC/Mobile浮窗及详情保存/刷新和失败反馈。


## 10.24 地图信息直读、语义季节与聚合浮窗（2026-10-24）

浮窗与详情不以“12月 · 可以考虑”“冬季 · 需注意”“为什么推荐给你：一般”等评分/枚举作为内容结论；用完整自然语句说明视频明确表达的时节、天气条件、景观看点和限制。注意事项直接在浮窗外层显示，优先于较长的看点；无来源的建议不补写。正文声明与转写不确定性不得被升级为系统判断，往年气温不冒充最佳到访日期。完整来源与原笔记保持可达，展开证据仅用于核对，不作为获取重要提醒的前置步骤。

同一Note版本跨分块的PLACE_GUIDE与MULTI_PLACE_LIST，如果有重复的已绑定地点、共同且有正文依据的景观主题，以及明确的主次/共同Claim关系，可传递无冲突的共同季节；松花湖与雾凇岛属于同篇吉林雾凇讲解时可继承冬季背景。传递结果明确标为语义背景，并保留原句、来源和Segment；具体月份、日级窗口、天气和八九点等时刻不随关系图广播。不同Note版本、主题不同、季节冲突、背景/比较/被否定地点不得借此继承。地图筛选、单点与详情共用有效窗口，只读投影不回写历史。

地点本身被作者明确不推荐时，保留实体原句并进入“作者不推荐·待人工检核”队列；不自动查询/确认POI或创建地图点，用户检核后可显式搜索和确认。“不推荐下雪时去某地”等天气/季节限制只构成该地点的提醒，不等于否定整个地点。不追溯改写或自动隐藏既有人工确认历史。

点击数字聚合点同时放大地图并显示该聚合的准确地点列表，可点列表项切换至单点。聚合仍完整存在时保留浮窗；一旦成员散为多个点/子聚合、成员离开当前筛选范围或聚合不再存在，即自动关闭聚合浮窗，不保留旧列表遮挡地图。聚合各地点仅属于同一篇、同一版本笔记且有明确看点时，可整理该篇已保存的共同看点并链接原笔记；多篇/来源不完整时缺省区域总结，保留地点列表，不用空间接近推断共同推荐理由。PC/Mobile均验收普通点击、放大、列表切换、散开自动关闭和无溢出。

## 10.25 地点阅读层级与来源收纳（2026-10-25）

地图单点、聚合和地点详情面向用户直接展示已提取要点，不重复使用“同篇视频”“视频指出/提到/强调”等叙述外壳。仅作展示层清理，不删改原始文字、来源关系、时间范围、否定条件、“可能/约/往年”等限定；转写不确定性仍需保留可读提醒。来源关联说明、原句、继承背景与原笔记超链接放在默认收起的“查看更多”中。聚合是否有共同来源的判断及散开自动关闭行为不变。

详情以名称、地址/导航、时节与天气条件、看点及注意事项为首屏。费用、排队/预约、体验、美食及其他已有记录按业务分组，有数据才展示；冲突或较早记录保留简短提示，不补造缺失信息。个人备注可直接阅读；已有图片观察保留待核对边界，不伪装成验证事实。类型、用户状态与标签为紧凑附属信息，坐标系、地图标识、完整引文和编辑历史降为小字号次级内容；历史只在展开后读取。不显示空“地点知识/截图事实”等大区块。

编辑从次级入口进入，名称、类型、标签、备注和人工时间补充保留保存与修订号保护；隐藏/偏好/删除收进“管理地点”，主业务操作保留想去/去过。PC与Mobile验收原始要点不损失、正文无重复来源措辞、查看更多可展开并有有效链接、元数据不抢占首屏、编辑保存刷新及聚合交互保持；生产不保存验收虚构数据。

## 10.26 地点详情阅读展开与对齐（2026-10-26）

详情中的关联笔记、时间依据、原句与来源采用正常阅读排版并默认展开，保留原笔记超链接和继承边界说明；不把整个详情塞进“查看更多”。地点资料采用小字号紧凑字段，与默认展开的编辑历史在PC并列、Mobile纵向排列，降低非业务资料占用。状态/偏好按钮回到底部操作栏，隐藏/恢复与删除在地图显示区直接显示，危险操作仍须确认。此条调整详情展示，地图单点和聚合的来源仍留在查看更多。

何时去/注意事项/看什么要点卡片在PC共享一行、等宽等高并统一内边距；少于三项时平分可用宽度。Mobile单列对齐，保留内容自适应和合理最小高度，不截断长提醒。高德入口采用共享按钮规范，13px文字、至少40px高度与左右14px留白；标题、地址、卡片、阅读资料及手机业务操作对齐同一安全边距。保留编辑保存、时间锚点跳转及手机底部主操作避让。

## 10.26 底部操作与编辑历史补充

“不感兴趣、不喜欢、喜欢、去过、想去”恢复到同一条底部固定操作栏，按此顺序排列；正文不重复这些按钮。地图隐藏/恢复和永久删除保留在资料末尾的地图显示区，删除仍需确认。Mobile操作栏保持一行、不遮挡底部导航，文字不换行或溢出。

编辑历史默认展开并在地点读取成功后自动加载，保存或操作成功后刷新历史。地点资料与编辑历史都使用160px高的辅助容器，标题固定、内容区域内部滚动；历史条数或消息长度不能撑高整行、拉伸相邻资料字段，Mobile单列也保持相同高度。采用长历史样例校验容器高度、滚动和页面无横向溢出，模拟记录不得写入生产。


### 10.25 地点整体态度与局部限制（2026-10-27）

作者整体意见复用PlaceMention.visit_intent，但明确推荐必须具备recommendation-v1逐字证据。recommendation_evidence保存在既有JSON：statement_id、原态度、PLACE_OVERALL/LOCAL_DETAIL/UNCERTAIN范围、subject_entity_id、AUTHOR/OTHER/UNKNOWN说话者、quote、Segment IDs、原句条件/时间及显式修正关系。引文/Segment必须属于本包，主体在编译时按实体命名空间恢复；没有整体证据不默认推荐，版本标志和程序VERIFIED不代表真实模型质量已验。

“A值得去，但别坐游船”：A的整体推荐与局部提醒分开，游船/菜品/天气/费用等不建立独立地点或复核项。普通有效地点没有态度仍沿用POI规则；不推荐、标签/证据疑点及整体正反冲突暂停自动POI处理，转人工复核。否定词只用于疑点报警，双重否定、转述、主体不清不能伪装语义理解。同键候选合并先去重证据再判定，顺序无关；同一作者明确改口保留原意见及修正，条件不同的意见不擅自泛化，无法解释的正反意见并列CONFLICT。

统一只读recommendation_summary供审核/视频地点/PlacePreview/Detail/地图成员使用，状态RECOMMENDED/OPTIONAL/NOT_RECOMMENDED/CONFLICT/UNKNOWN，保留各来源版本与原文。共享地点只聚合各Note当前有效版本，排除USER_REJECTED/SUPERSEDED，不按时间/票数覆盖。负向来源独立于推荐体验筛选，关联笔记与原句始终可达；缺新证据旧标签标为旧记录，正向旧值不升级已验证推荐。旧版本不回写、不自动重跑、不隐藏历史Marker。

人工“确认地点位置”只绑定POI身份，不改作者态度或用户喜欢/想去/去过。负向手动确认后可上图但标签保持；地图/详情与视频使用同一后端投影。个人偏好照常保存，但不把UNKNOWN/OPTIONAL/CONFLICT或负向来源放进明确推荐集合；已有地点不因此消失。混合负向/分歧成员的聚合不生成共同看点摘要，各成员仍列自身态度。

笔记各分包仅携本包证据；整体意见和局部限制保真传递，未能核对归纳覆盖时保留绑定原句并标HYBRID/告警，存疑或负向章节不输出未经核验的正向概括。Prompt/地图Artifact版本已独立更新，旧缓存不冒充新证据；真实召回率/误报仍需另行授权的标注视频矩阵。隔离确认/偏好写入用于验收，生产Browser只读；不新增Schema或默认模型调用。

2026-10-27 用户确认的展示修订：已自动识别或人工确认进入地图的地点默认按推荐阅读，常态不显示推荐/可选/态度未明确标签；仅识别到整体不推荐时在地点名称旁标“不推荐”，正反来源并存则标“有来源不推荐”。UNKNOWN等字段继续用于内部证据与审计，不在阅读界面额外挂标签，也不回写旧证据。视频候选栏目仅展示地点当前状态与时间入口，实际位置确认留在可执行的人工复核卡。此条覆盖原计划对未知态度的常态标签展示要求，不改变来源证据、个人偏好或POI身份记录。
