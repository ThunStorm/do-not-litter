# Travel / Food Pipeline

> 视频链接到 AI 笔记、BiliNote 复用边界、DeepSeek 分块总结、地点归纳笔记与多入口导航的冻结契约见 `VIDEO_AI_NOTE_PIPELINE.md`。本文件继续定义 Travel/Food 的领域抽取、POI、偏好和地图规则；发生冲突时，专项文档中的视频链路规则优先。

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

第一版地域为中国范围，POI 与地图首选高德；真实样本见 `GOLDEN_SAMPLES.md`。

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
