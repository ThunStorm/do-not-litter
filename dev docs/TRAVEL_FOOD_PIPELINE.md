# Travel / Food Pipeline

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

## 7.1 地图是空间总览，不是地点附件

旅行信息架构固定为：

```text
内容 > 旅行 > 地图总览
             ├─ Marker A → 地点预览 A → 地点详情 A
             ├─ Marker B → 地点预览 B → 地点详情 B
             └─ 路线清单 → 手动排序 → 后续路线规划
```

地图总览是独立主页面，默认展示当前区域内全部符合筛选条件的 `CONFIRMED Place` 分布。地点详情是从 Marker 预览进入的下一级页面；不得先进入某个地点详情，再把地图作为该地点的附属卡片。

地图总览必须支持：

- 按城市、行政区、地点类型与用户状态筛选；
- 根据当前 viewport/bbox 返回 Marker，并在密集区域聚合；
- 一键适配全部当前结果；
- 点击 Marker 只更新 `selected_place_id` 和底部地点预览，不重建或离开地图；
- 预览卡显示当前序号、名称、地址、关键观察、Evidence 摘要及“查看详情”；
- 从详情返回后恢复原 viewport、zoom、筛选与 selected Marker；
- 上一处/下一处按当前可见 Marker 的稳定顺序切换，不改变地图父级关系；
- 无选中 Marker 时仍完整展示区域分布，不能强制打开某个地点详情。

Marker 只表示现实 `Place`，不能直接用 `PlaceMention` 或 LLM 生成坐标。`REVIEW/UNRESOLVED` 不默认进入主地图，可通过“待确认地点”入口单独处理。

## 7.2 路线清单边界

第一版地图提供“加入路线清单”和手动排序，用于保存用户希望串联的地点。它不是自动路线优化：

- 清单存 `Place ID + 手动顺序`；
- 不在没有地图路线服务结果时生成距离、交通时长或最优顺序；
- 清单中的 Marker 可使用顺序编号，但普通总览 Marker 不强制编号；
- 真正的驾车/步行/公共交通路线计算、日期行程与导航跳转留给后续 Trip Planner；
- 后续接入路线 Provider 时复用清单，不改变 Place、Observation 与 Evidence。

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

# 18. 视觉能力预留

数据模型保留：
`VisualEvidence`

后续：

```text
FrameExtractor
→ VisionProvider
```

用于：
- 店招；
- 菜单；
- 路牌；
- 屏幕价格；
- 地图画面。

任务完成只永久保存真正被 Claim 引用的 Evidence Frames。

---

# 19. 视频缓存

临时：
- video
- audio
- full frames

永久：
- transcript
- evidence frames
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

MapOverviewVM：

- viewport / coordinate_system
- total_places / visible_places
- markers / clusters
- selected_place_id
- selected_preview
- filters
- route_draft_count

地图总览不依赖某个地点详情才能构造。`selected_preview` 只是当前 Marker 的轻量投影视图，完整 Observation、Evidence 与来源仍由 Place Detail ViewModel 提供。

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
