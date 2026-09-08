# Place Intelligence + Interactive Map V2 实施计划

> 已归档（2026-09-08）：核心计划已被 `8a6484b`、`77e37eb` 与 `161d320` 覆盖。当前实现与未闭环项见 [实施状态](../../IMPLEMENTATION_STATUS.md)；推荐评分与自动行程等未授权方向见 [Future Roadmap](../../planning/FUTURE_ROADMAP.md)。

> Repository: `ThunStorm/do-not-litter`
> Target branch: `codex/mac-mini-implementation`
> Suggested document path: `dev/PLACE_INTELLIGENCE_MAP_V2_IMPLEMENTATION_PLAN.md`
>
> 状态：Approved for implementation
> 原则：先搭建地点知识、POI 校验、地图交互和人工编辑基础，不实现推荐指数/综合评分。

---

# 1. 项目目标

当前视频处理已经能够从内容中尝试抽取地点，也存在 `Place`、`PlaceMention`、`MapMarkerState` 等基础模型，但整体仍然没有形成真正可使用的“地点知识系统”。

本阶段目标不是继续给视频摘要增加字段，而是建立一套稳定的：

**Video → Place Mention → Place Insight → POI Resolution → Canonical Place → Interactive Map → User Editing**

完整链路。

完成后系统应支持：

1. 从视频中抽取地点。
2. 为地点抽取结构化核心信息。
3. 使用高德 POI 对地点进行自动校验。
4. 无法确定时进入人工校验。
5. 地点可以稳定 Pin 到真实交互地图。
6. 地图支持平移、缩放、聚合、筛选、点击 Pin。
7. 点击 Pin 后直接查看地点信息，而不是强制跳页面。
8. 用户可以：
   - 编辑备注；
   - 修改显示名称；
   - 添加自己的标签；
   - 手动增加 Pin；
   - 手动隐藏 Pin；
   - 删除自己添加的地点；
   - 恢复误删/隐藏的 Pin；
   - 修正错误 POI；
   - 解绑 POI；
   - 重新绑定 POI。
9. AI 重跑不能覆盖人工编辑。
10. 视频重新解析不能 resurrect 用户明确删除/否定的地点。
11. 为未来推荐指数保留可靠数据基础，但本阶段不计算推荐分。

---

# 2. 本阶段明确不做

以下内容暂时不要实现：

- 综合推荐指数；
- 作者评分体系；
- 用户个性化推荐算法；
- 多作者信誉加权；
- 自动行程生成；
- 路线最优化；
- 自动计算旅游季节；
- 自动从天气/气候库补月份；
- 大模型自动修改用户备注；
- 社交分享；
- 多用户协作编辑。

允许保留数据接口和 provenance，但不得为了未来评分提前实现复杂算法。

---

# 3. 当前主要问题

## 3.1 地点提取存在两个事实来源

当前：

- `GENERATE_AI_NOTE`
- `EXTRACT_TRAVEL_FACTS`

均可能产生地点信息。

结果是：

- schema 不一致；
- rich place facts 并不总是使用；
- 后续无法确定哪个结果是真正 Source of Truth。

### 决策

以后：

```text
GENERATE_AI_NOTE
    ↓
仅负责生成适合阅读的视频笔记

EXTRACT_PLACE_INSIGHTS
    ↓
唯一负责结构化地点事实
```

`AINote.map_facts_json` 不再作为正式地点结构化来源。

---

# 4. 核心架构

推荐最终结构：

```text
Video
 ↓
Transcript / Segment
 ↓
PlaceMention
 ↓
PlaceInsightItem
 ↓
POI Resolver
 ↓
Place
 ↓
PlaceMarkerState
 ↓
Map Explorer
```

旁路：

```text
User
 ├── UserPlaceOverlay
 ├── PlaceUserNote
 ├── USER_ADDED Insight
 ├── Manual Place
 └── POI Resolution Override
```

重要原则：

> AI 数据层与人工数据层不要互相覆盖。

---

# 5. Place、Mention、Insight、Marker 的职责

这是本次重构最重要的边界。

## 5.1 Place

`Place` 表示现实世界中的“一个地点”。

例如：

```text
故宫博物院
```

Place 不应该表示：

- 某条视频里的一次提及；
- 某个作者观点；
- 某条推荐菜；
- 某个地图 Pin 的显示状态。

Place 是 canonical entity。

---

## 5.2 PlaceMention

`PlaceMention` 表示：

> 某条视频中提到了这个地点。

例如：

```text
视频 A
  └── 提到 "四季民福故宫店"
```

它属于 Source 层。

同一个 Place 可以拥有：

```text
Video A → Mention A
Video B → Mention B
Video C → Mention C
```

---

## 5.3 PlaceInsightItem

表示：

> 某个来源针对地点表达的一条结构化事实或观点。

例如：

```text
RECOMMENDED_ITEM
烤鸭
```

或者：

```text
BEST_TIME_SLOT
SUNSET
```

或者：

```text
WARNING
下午排队很长
```

不要把这一层继续堆进一个巨大 `brief_json`。

---

## 5.4 MapMarkerState

只负责：

> 这个 Place 在用户地图中如何展示。

例如：

```text
VISIBLE
HIDDEN
ARCHIVED
custom_label
```

MapMarkerState 不保存旅游知识。

---

# 6. Place Insight Schema V1

新增模型：

```python
class PlaceInsightItem:
    id
    place_id
    place_mention_id
    source_id

    insight_type
    value_key
    value_text
    value_json

    provenance
    confidence

    status
    supersedes_id

    segment_ids_json

    created_by
    created_at
    updated_at
```

---

# 7. insight_type

第一版支持：

```text
HIGHLIGHT
RECOMMENDED_ITEM

BEST_MONTH
BEST_SEASON
BEST_TIME_SLOT

SUGGESTED_DURATION

PRICE
QUEUE
AUDIENCE

WARNING
AUTHOR_OPINION

CUSTOM_TAG
```

---

# 8. 推荐菜/项目的数据结构

例如餐馆：

```json
{
  "insight_type": "RECOMMENDED_ITEM",
  "value_key": "dish",
  "value_text": "脆皮乳鸽",
  "value_json": {
    "category": "DISH",
    "reason": "作者称这是最值得点的一道菜"
  }
}
```

景区：

```json
{
  "insight_type": "RECOMMENDED_ITEM",
  "value_key": "attraction",
  "value_text": "日照金山",
  "value_json": {
    "category": "EXPERIENCE"
  }
}
```

博物馆：

```text
RECOMMENDED_ITEM
镇馆展品
```

咖啡馆：

```text
RECOMMENDED_ITEM
手冲咖啡
```

因此不要建立：

```text
recommended_dishes
recommended_attractions
recommended_exhibits
```

多个数据库字段。

统一使用：

```text
RECOMMENDED_ITEM
```

并通过 category 分类。

---

# 9. 时间相关结构

为了后续地图筛选，时间类字段不能只存自然语言。

## Month

每个月单独一条：

```text
insight_type = BEST_MONTH
value_key = 04
value_text = 四月
```

---

## Season

```text
SPRING
SUMMER
AUTUMN
WINTER
```

---

## Time Slot

统一枚举：

```text
EARLY_MORNING
MORNING
NOON
AFTERNOON
SUNSET
EVENING
NIGHT

BREAKFAST
LUNCH
DINNER
LATE_NIGHT
```

---

# 10. Provenance

所有 insight 必须有来源类型。

枚举：

```text
SOURCE_FACT
POI_VERIFIED
SYSTEM_ENRICHED
USER_ADDED
USER_CORRECTION
```

---

## SOURCE_FACT

视频作者明确说过。

必须存在：

```text
source_id
segment_ids
```

---

## POI_VERIFIED

来自高德 POI。

例如：

```text
标准名称
地址
行政区
POI 类型
```

---

## SYSTEM_ENRICHED

未来系统推导。

例如：

```text
气候数据库判断 10 月适合
```

本阶段尽量不生成。

---

## USER_ADDED

用户主动添加。

---

## USER_CORRECTION

用户明确覆盖/修正系统事实。

---

# 11. 禁止 AI 覆盖人工编辑

这是强制设计规则。

重新运行视频解析：

```text
只能更新：

SOURCE_FACT
```

不得修改：

```text
USER_ADDED
USER_CORRECTION
```

---

# 12. Insight 编辑方式

禁止：

```text
直接修改 AI Insight 原记录
```

应该：

```text
AI Insight
status = SUPERSEDED

↓ supersedes

USER_CORRECTION
status = ACTIVE
```

这样未来可以回答：

> 原视频说了什么？

以及：

> 用户后来修正成了什么？

两者不会丢失。

---

# 13. 用户备注必须独立

新增：

```python
PlaceUserNote
```

建议字段：

```text
id
place_id

markdown
revision

created_by
updated_by

created_at
updated_at
```

Constraint：

```text
UNIQUE(place_id)
```

V1 每个地点一条用户备注即可。

未来如果需要多人/多条 note 再扩展。

---

# 14. 为什么备注不能存在 Place.summary

`Place.summary` 未来可能继续承担：

- AI summary；
- generated description。

用户备注如果直接覆盖它：

```text
AI regenerate
↓
覆盖用户内容
```

因此：

```text
Place.summary
≠
PlaceUserNote.markdown
```

---

# 15. User Overlay

增加：

```python
PlaceUserOverlay
```

字段：

```text
place_id

display_name
override_place_type

custom_tags_json

revision

created_at
updated_at
```

说明：

canonical POI：

```text
Place.name
```

用户界面：

```text
display_name ?? Place.name
```

这样用户把：

```text
上海迪士尼度假区
```

显示为：

```text
迪士尼
```

不会破坏高德 POI identity。

---

# 16. Place 模型调整

建议增加：

```text
origin
coordinate_source

poi_binding_status

deleted_at
revision
```

---

# 17. origin

枚举：

```text
AI_EXTRACTED
USER_CREATED
IMPORTED
SYSTEM_CREATED
```

---

# 18. coordinate_source

枚举：

```text
AMAP_POI
USER_MAP_CLICK
USER_GEOLOCATION
IMPORTED
UNKNOWN
```

---

# 19. 不要混用“有坐标”和“POI 已验证”

这是 Review 中发现的一个重要潜在问题。

用户在地图上点一下：

```text
116.391, 39.907
```

只能说明：

> 这里有一个用户创建的位置。

不能说明：

> 这个位置已经通过高德 POI 验证。

因此新增：

```text
poi_binding_status
```

枚举：

```text
UNBOUND
AUTO_CONFIRMED
USER_CONFIRMED
REVIEW
FAILED
```

---

# 20. 高德 POI Identity

对于已经匹配的地点：

```text
external_provider = AMAP
external_poi_id = xxxx
```

数据库增加唯一约束：

```text
UNIQUE(external_provider, external_poi_id)
```

允许 provider/id 为空。

目的：

避免：

```text
故宫
故宫博物院
北京故宫
```

分别建立三个 Place。

---

# 21. POI Resolver V2

当前 resolver 不应继续简单采用：

```text
搜索
↓
取第一个
```

必须升级。

---

# 22. 高德接口

迁移到：

```text
/v5/place/text
```

并支持：

```text
/v5/place/around
/v5/place/detail
```

---

# 23. Resolver Query Expansion

对于：

```text
raw_name
suggested_name
city_hint
province_hint
district_hint
```

执行候选查询：

```text
suggested_name + city
normalized_name + city
raw_name + city
name + district
name + province
```

不要一次请求大量无意义 query。

去重后执行。

---

# 24. Candidate

内部统一结构：

```json
{
  "provider": "AMAP",
  "provider_id": "...",

  "name": "...",
  "address": "...",

  "province": "...",
  "city": "...",
  "district": "...",

  "typecode": "...",

  "longitude": 0,
  "latitude": 0,

  "score": 0,
  "match_reasons": []
}
```

---

# 25. Candidate Scoring

V1：

```text
name similarity       45
city/adcode            20
district               10
POI type               15
alias/brand token       5
address context         5

TOTAL                  100
```

禁止直接把高德排序当作最终可信度。

---

# 26. 自动确认阈值

建议：

```text
score >= 80
AND
top1 - top2 >= 15

=> AUTO_CONFIRMED
```

---

```text
score 55–79
OR
top1/top2 过于接近

=> REVIEW
```

---

```text
score < 55

=> FAILED / UNRESOLVED
```

阈值放配置，不硬编码散落。

---

# 27. POI Detail 二次确认

Auto confirm 前：

```text
Search Candidate
↓
AMap Place Detail
↓
verify
↓
save
```

detail 请求失败时：

不要直接降级成错误确认。

应该：

```text
REVIEW
```

---

# 28. POI Review UI

建立：

```text
待确认地点
```

入口。

用户看到：

```text
AI 提取：
四季民福故宫店

可能地点：

○ 四季民福烤鸭店（故宫店）
  北京市东城区...
  距...
  匹配度 92

○ 四季民福烤鸭店（王府井店）
  ...
  匹配度 74
```

---

# 29. 地图辅助 POI Review

Review 页面不要只放列表。

地图同时展示：

```text
AI candidate A
AI candidate B
AI candidate C
```

点击 marker：

```text
选择这个地点
```

---

# 30. 用户必须可以选择

```text
确认候选
所有候选都不对
重新搜索
地图手动指定
创建自定义地点
```

---

# 31. Interactive Map Runtime 重构

当前 `AmapLayer` 必须整体调整。

基本原则：

```text
AMap.Map 创建一次
```

生命周期：

```text
mount
 ↓
create map
 ↓
keep mapRef
 ↓
update markers
 ↓
update selection
 ↓
update viewport

unmount
 ↓
destroy map
```

禁止：

```text
viewport change
↓
destroy
↓
create
```

---

# 32. React Effect 拆分

建议：

### Effect A

```text
load AMap
create Map
```

dependency：

```text
config
```

---

### Effect B

```text
marker dataset update
```

---

### Effect C

```text
selected marker styling
```

---

### Effect D

```text
external flyTo / fitView
```

---

### Effect E

```text
map moveend/zoomend
→ update React viewport
```

---

# 33. 避免 Viewport Feedback Loop

增加：

```text
viewportChangeSource
```

逻辑：

```text
USER_MAP_INTERACTION
PROGRAMMATIC
```

只有确实需要时 React 才调用：

```text
map.setZoomAndCenter()
```

否则仅同步状态。

API bbox 请求：

```text
moveend
↓
debounce 200–300ms
↓
fetch
```

不要监听每一个 map movement frame。

---

# 34. 地图控制按钮必须操作真实 AMap

删除目前只操作 fallback SVG zoom 的逻辑。

按钮：

```text
定位
放大
缩小
适配全部
```

必须分别调用真实：

```text
AMap.Map
```

方法。

---

# 35. MarkerCluster

使用：

```text
AMap.MarkerCluster
```

不要继续依赖当前自定义 SVG cluster 作为主交互。

数据：

```text
Place[]
↓
MarkerCluster
```

cluster click：

```text
zoom / fit cluster bounds
```

---

# 36. 数据规模策略

V1 不需要提前构建复杂地图 Tile 服务。

API：

```text
GET /api/travel/map/places
```

支持：

```text
bbox
filters
limit
```

响应：

```json
{
  "items": [],
  "total": 123,
  "truncated": false
}
```

建议：

```text
limit default = 3000
```

超过：

```text
truncated = true
```

前端提示：

```text
地点较多，请放大地图查看
```

未来如规模扩大，可以换 H3/vector tile，不需要改变 Place 数据模型。

---

# 37. 地图 Filter V2

支持：

```text
place_types[]
months[]
seasons[]
time_slots[]
user_states[]
origins[]
source_ids[]
poi_binding_status[]
query
```

---

# 38. 多选而不是单选

例如：

```text
☑ 餐馆
☑ 景点
☐ 酒店
☑ 咖啡
```

月份：

```text
3
4
5
```

---

# 39. Month Filtering 语义

默认：

```text
匹配任意月份
```

即：

```text
April OR May
```

不要实现：

```text
April AND May
```

---

# 40. 没有月份数据的地点

默认筛选月份时：

```text
不展示
```

但提供：

```text
□ 同时显示未标注月份
```

否则用户会误以为“没有月份数据 = 不适合”。

---

# 41. Pin 样式

V1 类型视觉区分即可：

```text
RESTAURANT
SCENIC_AREA
HOTEL
CAFE
SHOPPING
MUSEUM
TRANSPORT
OTHER
```

同时：

```text
selected
unresolved
user-created
```

使用形状/图标辅助，不要只依赖颜色。

---

# 42. Pin Click UX

点击 Pin：

不要立即跳转页面。

桌面：

```text
右侧 Detail Sheet
```

移动端：

```text
Bottom Sheet
```

---

# 43. Place Sheet

顶部：

```text
地点名
类型
地址
POI 状态
用户状态
```

---

## Core Highlights

例如：

```text
• 可以看到日落和城市全景
• 建议下午 4 点后前往
• 周末排队明显
```

---

## Recommended

餐馆：

```text
推荐点
• 烤鸭
• 贝勒烤肉
```

---

## Best Time

```text
最佳月份
10 / 11 月

最佳时间
SUNSET
```

---

## Sources

```text
来自 3 条视频
```

点击展开来源。

---

# 44. Place Sheet 编辑模式

增加：

```text
编辑
```

编辑模式支持：

```text
显示名称
地点类型人工覆盖
个人备注
自定义标签
用户状态
```

不要一开始允许任意修改：

```text
AMap POI ID
provider address
provider coordinates
```

这些属于 identity。

如需修改：

进入：

```text
修正地点
```

独立流程。

---

# 45. Pin 备注

Sheet 中展示：

```text
我的备注
```

支持 Markdown/plain text。

编辑方式：

```text
点击编辑
↓
textarea
↓
保存
```

API：

```http
PUT /api/travel/places/{place_id}/note
```

request：

```json
{
  "markdown": "...",
  "expected_revision": 3
}
```

---

# 46. Optimistic Concurrency

所有可编辑对象增加：

```text
revision
```

更新：

```text
expected_revision
```

如果：

```text
server revision != expected_revision
```

返回：

```http
409 Conflict
```

响应：

```json
{
  "code": "REVISION_CONFLICT",
  "latest": {}
}
```

避免未来桌面端/手机端同时编辑覆盖。

---

# 47. 手动增加 Pin

地图增加：

```text
+ 添加地点
```

之后进入：

```text
ADD_PLACE_MODE
```

用户点击地图：

```text
temporary marker
```

---

# 48. 点击地图后的第一选择

先调用：

```text
AMap /v5/place/around
```

搜索附近 POI。

例如：

```text
附近地点

○ 三里屯太古里
○ Apple 三里屯
○ ...
```

用户选中：

```text
创建绑定 POI 的 Place
```

---

# 49. 自定义地点

附近结果都不对：

```text
创建自定义地点
```

输入：

```text
名称
类型
备注（optional）
```

此时：

```text
origin = USER_CREATED
coordinate_source = USER_MAP_CLICK
poi_binding_status = UNBOUND
```

非常重要：

不得设成：

```text
CONFIRMED
```

---

# 50. 手动增加地点的去重

创建 POI Place 前：

检查：

```text
external_provider + external_poi_id
```

如果已存在：

```text
复用 Place
```

而不是再次创建。

---

# 51. 删除 Pin 的三种语义

这是本方案经过 Review 后必须明确拆开的行为。

## A. Hide from map

用户：

```text
隐藏此标注
```

只更新：

```text
MapMarkerState.visibility = HIDDEN
```

Place、Mention、Insight 全部保留。

支持恢复。

---

## B. Remove user-created place

仅对于：

```text
origin = USER_CREATED
```

提供：

```text
删除地点
```

执行：

```text
Place.deleted_at = now
```

软删除。

---

## C. Reject AI mention

AI 提取错误：

例如：

```text
“小王府”
```

并非地点。

执行：

```text
PlaceMention.extraction_status = USER_REJECTED
```

而不是删除 Place。

---

# 52. 禁止一个 DELETE API 承担全部语义

不要做：

```http
DELETE /places/{id}
```

然后什么都删。

应该分别：

```http
POST /places/{id}/hide
POST /places/{id}/restore-marker
DELETE /places/{id}/user-created
POST /place-mentions/{id}/reject
```

动作必须明确。

---

# 53. 用户删除后 AI 重跑

如果 Mention：

```text
USER_REJECTED
```

新 pipeline 发现相同：

```text
video_asset_id
normalized mention identity
```

不得自动恢复。

保留：

```text
USER_REJECTED
```

除非用户手动：

```text
恢复 AI 标注
```

---

# 54. Soft Delete

人工地点：

```text
deleted_at
```

默认查询：

```text
WHERE deleted_at IS NULL
```

提供：

```text
最近删除
```

V1 可以只提供：

```text
恢复
永久删除
```

永久删除可以延期实现。

---

# 55. 为什么不立即物理删除

Place 可能已经有关联：

```text
PlaceMention
PlaceInsight
RouteDraft
Source
Observation
```

直接 CASCADE 极容易把历史证据删掉。

因此 V1：

```text
soft delete first
```

---

# 56. MapMarkerState 调整

当前结构保留，并增加：

```text
revision
updated_by
```

建议：

```text
visibility:
VISIBLE
HIDDEN
```

不要同时把：

```text
deleted_at
visibility
```

都作为多个互相矛盾状态。

建议统一：

```text
deleted_at
```

只表示 MarkerState 本身被归档。

正常隐藏：

```text
visibility = HIDDEN
```

---

# 57. 用户人工修改历史

现有 `SystemEvent` 已能做基础审计。

所有用户动作记录：

```text
place.note.updated
place.overlay.updated
place.marker.hidden
place.marker.restored
place.created.manual
place.deleted.manual
place.poi.bound
place.poi.unbound
place.poi.rebound
place_mention.rejected
place_mention.restored
place_insight.corrected
```

detail 保存：

```text
before
after
reason
```

不要记录 secret。

---

# 58. Place API V2

新增：

```http
GET /api/travel/places/{place_id}
```

返回：

```json
{
  "place": {},
  "display": {},
  "marker": {},
  "note": {},
  "insights": [],
  "sources": [],
  "poi": {},
  "permissions": {
    "can_delete_place": true,
    "can_hide": true
  }
}
```

---

# 59. 更新 Overlay

```http
PATCH /api/travel/places/{place_id}/overlay
```

request：

```json
{
  "display_name": "...",
  "override_place_type": "RESTAURANT",
  "custom_tags": [],
  "expected_revision": 2
}
```

---

# 60. Note API

```http
PUT /api/travel/places/{place_id}/note
```

---

# 61. Hide

```http
POST /api/travel/places/{place_id}/marker/hide
```

---

# 62. Restore

```http
POST /api/travel/places/{place_id}/marker/restore
```

---

# 63. Manual Create

```http
POST /api/travel/places
```

POI：

```json
{
  "mode": "AMAP_POI",
  "external_poi_id": "..."
}
```

Custom：

```json
{
  "mode": "CUSTOM",
  "name": "...",
  "place_type": "...",
  "longitude": 0,
  "latitude": 0
}
```

---

# 64. POI Rebind

```http
POST /api/travel/places/{place_id}/poi-binding
```

request：

```json
{
  "provider": "AMAP",
  "poi_id": "...",
  "expected_revision": 4
}
```

---

# 65. POI Unbind

```http
DELETE /api/travel/places/{place_id}/poi-binding
```

解绑不能删除：

```text
用户备注
Insights
Mentions
```

---

# 66. Reject Mention

```http
POST /api/video-notes/place-mentions/{mention_id}/reject
```

---

# 67. Restore Mention

```http
POST /api/video-notes/place-mentions/{mention_id}/restore
```

---

# 68. 视频 Places API

当前 places endpoint 应扩展。

每个 mention：

```json
{
  "mention": {},
  "place": {},
  "insights": [],
  "resolution": {}
}
```

不要再让 frontend 自己从多个 endpoint 拼凑基本地点卡片。

---

# 69. Place Extraction Prompt V2

输出：

```json
{
  "places": [
    {
      "raw_name": "",
      "suggested_name": "",

      "city_hint": "",
      "province_hint": "",
      "district_hint": "",

      "place_type": "",

      "highlights": [],

      "recommended_items": [],

      "best_months": [],
      "best_seasons": [],
      "best_time_slots": [],

      "suggested_duration": "",

      "price": "",
      "queue": "",
      "audience": [],
      "warnings": [],

      "author_opinion": "",

      "evidence": [],

      "confidence": 0
    }
  ]
}
```

---

# 70. 强制 Evidence Rule

对于：

```text
SOURCE_FACT
```

如果没有 segment evidence：

```text
不得生成对应 Insight
```

特别是：

```text
BEST_MONTH
RECOMMENDED_ITEM
WARNING
```

不能让 AI 根据常识补充。

---

# 71. “作者没说月份”怎么办

输出：

```json
"best_months": []
```

不要：

```text
系统觉得云南适合春秋
```

那属于未来：

```text
SYSTEM_ENRICHED
```

---

# 72. Pipeline V2

建议：

```text
INGEST
 ↓
TRANSCRIBE
 ↓
GENERATE_AI_NOTE
 ↓
EXTRACT_PLACE_INSIGHTS
 ↓
RESOLVE_POI
 ↓
UPSERT_PLACES
 ↓
BUILD_PLACE_NOTE
 ↓
DONE
```

---

# 73. Reprocess Rules

重新运行：

```text
EXTRACT_PLACE_INSIGHTS
```

只废弃旧：

```text
SOURCE_FACT
```

产生的新版本。

禁止：

```text
delete all insights
```

再重建。

---

# 74. 数据版本

Insight 建议：

```text
status:
ACTIVE
SUPERSEDED
REJECTED
```

pipeline 新版本：

旧：

```text
ACTIVE → SUPERSEDED
```

新：

```text
ACTIVE
```

人工：

```text
USER_CORRECTION
```

不参与 AI supersede。

---

# 75. Place Merge

POI resolver 可能发现：

```text
Mention A
Mention B
```

其实同一个 AMap POI。

必须：

```text
reuse Place
```

Mention：

```text
place_id → same Place
```

---

# 76. 不要自动合并用户自定义地点

两个：

```text
USER_CREATED
```

只因为距离近不能自动 merge。

未来可以：

```text
suggest duplicate
```

但本阶段不自动处理。

---

# 77. Map 搜索

地图搜索支持：

```text
display_name
canonical name
address
custom tags
```

不要把全文 source transcript 放入 map query。

---

# 78. 地图筛选性能

新增 indexes：

```text
places(place_type)
places(origin)
places(poi_binding_status)
places(latitude, longitude)

place_insight_items(place_id, insight_type, status)
place_insight_items(insight_type, value_key, status)

map_marker_states(place_id, visibility)
place_mentions(place_id, extraction_status)
```

SQLite 阶段保持简单。

不要提前引入 Elasticsearch/PostGIS。

---

# 79. 数据库 Migration

建议 migration：

```text
0005_place_intelligence_v2.py
```

包含：

```text
place_insight_items
place_user_notes
place_user_overlays

places:
    coordinate_source
    poi_binding_status
    deleted_at
    revision

map_marker_states:
    revision
    updated_by
```

以及：

```text
external_provider/external_poi_id UNIQUE
```

如果历史数据存在重复 POI：

migration 不要直接创建 UNIQUE 导致失败。

先：

```text
detect duplicates
```

输出 migration diagnostics。

必要时先做：

```text
partial/normal index
```

再在数据清洗后加 unique。

---

# 80. Migration Backfill

旧：

```text
PlaceMention.brief_json
```

转换：

```text
feature
→ HIGHLIGHT

experience
→ HIGHLIGHT or RECOMMENDED_ITEM

price
→ PRICE

queue
→ QUEUE

audience
→ AUDIENCE

warning
→ WARNING

author_opinion
→ AUTHOR_OPINION
```

provenance：

```text
SOURCE_FACT
```

但只有能找到有效 evidence 的项目才标 SOURCE_FACT。

否则：

```text
metadata:
legacy_unverified = true
```

不要伪造 evidence。

---

# 81. brief_json 迁移策略

短期：

```text
read legacy
write new model
```

一个 release 后：

停止写：

```text
brief_json
```

再后续 migration 才删除字段。

不要一次 migration 同时：

```text
迁数据
改 API
删字段
```

降低 rollback 难度。

---

# 82. Frontend State Architecture

建议拆：

```text
MapOverviewPage
 ├── MapToolbar
 ├── MapFilterPanel
 ├── AmapLayer
 ├── PlaceSheet
 ├── PlaceEditSheet
 ├── AddPlaceFlow
 └── POIResolutionSheet
```

不要继续把全部逻辑堆在：

```text
MapOverviewPage.tsx
```

---

# 83. AmapLayer 对外 imperative API

可使用：

```ts
export interface MapController {
  zoomIn(): void
  zoomOut(): void
  locate(): void
  fitPlaces(): void
  flyTo(placeId: string): void
  enterAddMode(): void
}
```

通过 ref/controller 暴露。

页面按钮不得复制地图逻辑。

---

# 84. Selection

地图选择状态：

```text
selectedPlaceId
```

只改变：

```text
marker selected style
PlaceSheet
```

不能重建地图。

---

# 85. URL State

推荐逐步支持：

```text
/map?place=plc_xxx
```

filter 可后续放：

```text
type=
month=
```

至少 selected place 应可 deep link。

---

# 86. 用户状态

已有：

```text
DISCOVERED
SAVED
VISITED
PLANNED
```

继续使用。

Place Sheet 可直接修改。

不要和：

```text
MapMarker.visibility
```

混在一起。

例如：

```text
SAVED
```

不等于：

```text
VISIBLE
```

---

# 87. API Error Contract

所有新 API 统一：

```json
{
  "code": "...",
  "message": "...",
  "detail": {}
}
```

主要：

```text
REVISION_CONFLICT
PLACE_NOT_FOUND
INVALID_POI
POI_PROVIDER_UNAVAILABLE
PLACE_HAS_REFERENCES
CANNOT_DELETE_NON_USER_PLACE
```

---

# 88. AMap 配置诊断

地图 bootstrap 返回：

```json
{
  "js_api": {
    "configured": true
  },
  "web_service": {
    "configured": true
  },
  "capabilities": {
    "map": true,
    "poi_search": true,
    "poi_detail": true
  }
}
```

UI 如果：

```text
Web Service Key 缺失
```

明确显示：

```text
地图可以浏览，但无法执行 POI 校验
```

不要静默失败。

---

# 89. Resolver 可观测性

使用现有：

```text
ExternalCallAudit
SystemEvent
```

记录：

```text
provider
operation
duration
result count
status
error code
```

不要记录 secret key。

---

# 90. 测试要求

## Backend Unit

### Insight parser

测试：

```text
restaurant recommended items
scenic highlights
best_months
empty months
evidence binding
```

---

## Resolver

Mock AMap：

```text
exact match
alias match
wrong city
multiple candidates
close score
no result
provider timeout
detail failure
```

---

## Editing

测试：

```text
edit note
revision conflict
hide marker
restore marker
manual create
manual delete
reject mention
reprocess rejected mention
```

---

# 91. Map Lifecycle Test

这是 P0。

Mock：

```text
AMap.Map
```

断言：

```text
initial render:
new Map = 1
```

然后：

```text
pan
zoom
select marker
filters changed
markers changed
```

仍然：

```text
new Map = 1
destroy = 0
```

unmount：

```text
destroy = 1
```

---

# 92. E2E Map Test

必须测试：

```text
打开地图
拖动
缩放
点击 Pin
打开 Place Sheet
关闭
继续拖动
筛选
打开另一个 Pin
```

全程地图实例不得重建。

---

# 93. Manual Pin E2E

流程：

```text
+ 添加地点
↓
点击地图
↓
显示 temporary marker
↓
附近 POI
↓
选择 POI
↓
Pin 出现
↓
刷新页面
↓
Pin 仍存在
```

---

# 94. Custom Pin E2E

```text
点击地图
↓
附近都不是
↓
自定义地点
↓
名称
↓
创建
```

确认：

```text
poi_binding_status = UNBOUND
```

---

# 95. Delete E2E

分别测试：

### AI Pin hide

```text
hide
reload
hidden
restore
visible
```

### User Place delete

```text
soft delete
reload
not visible
restore
visible
```

### Mention reject

```text
reject
rerun extraction
still rejected
```

---

# 96. Agent 实施顺序

禁止一次性大 PR。

---

# PR 1 — `fix/map-runtime-lifecycle`

优先级：

```text
P0
```

修改：

```text
frontend/src/features/map/AmapLayer.tsx
frontend/src/features/map/MapCanvas.tsx
frontend/src/features/map/MapOverviewPage.tsx
```

任务：

- Map 只初始化一次；
- mapRef；
- markers independent update；
- selected independent update；
- viewport independent update；
- move/zoom debounce；
- 真正地图 zoom controls；
- fitView；
- MarkerCluster；
- 移除 fake SVG zoom control 对真实地图的影响；
- lifecycle tests。

Acceptance：

```text
拖动、缩放、选 Pin 不创建新的 AMap.Map。
```

---

# PR 2 — `feat/place-insight-schema-v1`

优先级：

```text
P0
```

任务：

- `PlaceInsightItem`
- provenance
- normalized filter value
- evidence
- insight extraction schema
- legacy brief migration/backfill
- new response DTO

Acceptance：

餐馆：

```text
推荐菜
```

景点：

```text
核心看点
最佳时间
明确提到的月份
```

均可结构化返回。

---

# PR 3 — `feat/amap-resolver-v2`

优先级：

```text
P0
```

任务：

- AMap v5；
- search;
- around;
- detail;
- query expansion;
- name normalization;
- scoring;
- thresholds;
- candidate metadata;
- retry/error;
- diagnostics。

Acceptance：

不得使用：

```text
search result[0]
```

作为唯一判断。

---

# PR 4 — `feat/place-editing-foundation`

优先级：

```text
P0
```

增加：

```text
PlaceUserNote
PlaceUserOverlay
revision
soft delete
marker hide
audit
```

API：

```text
note
overlay
hide
restore
```

Acceptance：

AI 重跑后：

```text
用户备注仍存在
display_name 仍存在
hidden 状态仍存在
```

---

# PR 5 — `feat/manual-map-place`

优先级：

```text
P1
```

实现：

```text
map click
temporary marker
nearby POI
select POI
custom place
```

Acceptance：

用户无需视频即可手工维护地点。

---

# PR 6 — `feat/place-resolution-review`

优先级：

```text
P1
```

实现：

```text
REVIEW queue
candidate list
candidate pins
confirm
reject
custom
rebind
unbind
```

---

# PR 7 — `feat/map-place-explorer`

优先级：

```text
P1
```

实现：

```text
type filter
month filter
season filter
time filter
state filter
origin filter

PlaceSheet
insights
note
edit
source list
```

---

# PR 8 — `feat/place-edit-history`

优先级：

```text
P2
```

完善：

```text
revision conflict UX
edit history UI
recently deleted
restore
```

后端审计应在 PR4 已存在。

---

# 97. 推荐实施的文件结构

Backend：

```text
backend/src/zhijian/
├── api/
│   ├── places.py
│   ├── map.py
│   └── video_notes.py
│
├── services/
│   ├── place_insight.py
│   ├── place_editing.py
│   ├── poi_resolution.py
│   └── map_service.py
│
├── providers/
│   └── amap.py
│
├── schemas/
│   ├── places.py
│   ├── place_insights.py
│   └── map.py
```

如果当前项目尚未按此拆 router，可以渐进迁移。

不要为了本 PR 强行重构全部 API。

---

Frontend：

```text
frontend/src/features/map/
├── AmapLayer.tsx
├── MapOverviewPage.tsx
├── MapToolbar.tsx
├── MapFilterPanel.tsx
├── PlaceSheet.tsx
├── PlaceEditSheet.tsx
├── AddPlaceFlow.tsx
├── POIResolutionSheet.tsx
└── hooks/
    ├── useAmap.ts
    ├── useMapPlaces.ts
    └── usePlaceEditor.ts
```

---

# 98. Review：禁止采用的设计

以下方案虽然实现快，但不要采用。

## 禁止 1

```text
把所有新字段继续存 brief_json
```

原因：

月份/季节筛选最终会变成 JSON 遍历。

---

## 禁止 2

```text
用户直接修改 SOURCE_FACT
```

原因：

失去原始视频证据。

---

## 禁止 3

```text
AI 重新解析 delete + recreate 全部 Place
```

原因：

用户备注、route、状态、Pin 都会断关联。

---

## 禁止 4

```text
删除 Pin = DELETE Place
```

原因：

语义错误且可能 Cascade。

---

## 禁止 5

```text
用户地图点击 = POI CONFIRMED
```

原因：

坐标不是 POI identity。

---

## 禁止 6

```text
React viewport 作为地图唯一真实状态
```

原因：

地图交互会与 React 产生 feedback loop。

地图实例负责即时地图状态。

React 保存：

```text
last settled viewport
```

---

## 禁止 7

```text
前端直接请求高德 WebService Key
```

WebService Key 只在 backend。

JS API key 按高德要求配置。

---

## 禁止 8

```text
过滤只在 frontend 做
```

小数据可临时，但 API 必须拥有标准 filter contract。

---

## 禁止 9

```text
用推荐分反向决定原始事实是否展示
```

事实层和 ranking 层必须分离。

---

# 99. 设计 Review 后的最终架构修正

本计划形成后进行了第二轮 Review，发现并已经修正以下潜在问题。

---

## Review Finding 1

最初容易把：

```text
Place.resolution_status
```

同时拿来表示：

```text
是否有坐标
是否有 POI
POI 是否确认
```

这三个概念不同。

### 修正

增加：

```text
coordinate_source
poi_binding_status
```

---

## Review Finding 2

容易让 Marker 成为地点数据本身。

### 修正

Marker 仅为：

```text
UI state
```

Place 独立存在。

---

## Review Finding 3

单纯增加 editable 字段，会被 AI 重跑覆盖。

### 修正

增加：

```text
PlaceUserOverlay
PlaceUserNote
USER_CORRECTION
```

作为单独数据层。

---

## Review Finding 4

如果用户删除错误 AI 地点，仅隐藏 Marker：

再次重新解析可能重新出现。

### 修正

增加：

```text
PlaceMention.USER_REJECTED
```

作为 source-level suppression。

---

## Review Finding 5

所有 Insights 做成 JSON 对未来过滤不友好。

### 修正

使用：

```text
PlaceInsightItem
insight_type
value_key
```

一条一条存储。

---

## Review Finding 6

用户删除 Place 会破坏视频 Evidence。

### 修正

只有：

```text
USER_CREATED Place
```

才允许直接用户软删除。

AI/source Place：

主要使用：

```text
hide
reject mention
```

---

## Review Finding 7

手机和桌面未来可能同时编辑。

### 修正

增加：

```text
revision + expected_revision
```

实现 optimistic concurrency。

---

## Review Finding 8

POI 搜索第一个结果很容易误匹配。

### 修正

采用：

```text
candidate pool
+
scoring
+
detail verification
+
review
```

---

## Review Finding 9

只使用 client-side clustering，未来地点数增大可能一次拉太多。

### 修正

API 保留：

```text
bbox
limit
total
truncated
```

未来可以替换 backend implementation，不改变客户端协议。

---

## Review Finding 10

推荐指数未来如果直接读取最终编辑后的字段，将失去出处。

### 修正

未来 scoring 输入必须来自：

```text
Insight + provenance + source + confidence
```

而不是一个已经融合的不透明 `summary`。

---

# 100. 为未来 Recommendation Score 预留

本阶段不计算分数。

但是确保以后可以取得：

```text
作者观点
来源数量
事实出现次数
SOURCE_FACT confidence
POI verified status
warnings
best month
time slot
user corrections
```

未来可以实现：

```text
RecommendationEngine
```

而无需重新设计 Place 数据。

---

# 101. 最终用户体验

完成本阶段以后，理想流程应是：

```text
导入视频
↓
自动解析
↓
发现 7 个地点
↓
其中：
5 个自动确认
2 个待确认
↓
用户打开地图
↓
所有已确认地点真实 Pin 在地图
↓
类型/月份/时间筛选
↓
点击 Pin
↓
看到：

地点
地址
推荐菜 / 看点
最佳月份
最佳时间
注意事项
作者观点
视频来源
自己的备注
↓
可以编辑备注
↓
可以隐藏 Pin
↓
可以修正 POI
↓
可以人工补 Pin
```

这才是本阶段的完成状态。

---

# 102. Definition of Done

只有同时满足以下条件，本阶段才算完成。

## Extraction

- [ ] 地点只有一个正式结构化提取 pipeline。
- [ ] restaurant 可产生 recommended item。
- [ ] scenic spot 可产生 highlights。
- [ ] 支持 best_month。
- [ ] 支持 best_time_slot。
- [ ] SOURCE_FACT 有 evidence。
- [ ] AI 不凭常识补月份。

## POI

- [ ] 使用 AMap POI v5。
- [ ] 有 candidate scoring。
- [ ] 有 detail verification。
- [ ] ambiguous → REVIEW。
- [ ] 无 key 时 UI 明确诊断。
- [ ] 支持人工确认。

## Map

- [ ] AMap instance 初始化一次。
- [ ] pan 不重建 map。
- [ ] zoom 不重建 map。
- [ ] select marker 不重建 map。
- [ ] MarkerCluster。
- [ ] 真 zoom controls。
- [ ] fitView。
- [ ] filter。
- [ ] Pin Sheet。

## Editable

- [ ] 用户备注。
- [ ] display name。
- [ ] custom tags。
- [ ] marker hide。
- [ ] marker restore。
- [ ] manual add POI。
- [ ] manual custom Pin。
- [ ] soft delete user-created place。
- [ ] reject AI mention。
- [ ] POI rebind。
- [ ] POI unbind。
- [ ] revision conflict。
- [ ] audit events。

## Safety of Data

- [ ] AI reprocess 不覆盖用户 note。
- [ ] AI reprocess 不覆盖 overlay。
- [ ] AI reprocess 不恢复 rejected mention。
- [ ] hide Pin 不删除 evidence。
- [ ] remove Mention 不删除 canonical Place。
- [ ] user map coordinate 不伪装成 verified POI。
- [ ] legacy brief_json 可迁移。
- [ ] migration 可 rollback。

---

# 103. Agent 执行规则

Agent 在实施过程中必须遵守：

1. 先阅读本文件。
2. 只读取当前 PR 相关代码。
3. 不要每个 PR 扫描整个 repository。
4. 不要顺手进行无关重构。
5. 每个 PR 开始先列受影响文件。
6. 修改 schema 必须同时写 migration。
7. 修改 API 必须同时修改 frontend type。
8. 修改地图 runtime 必须添加 lifecycle regression test。
9. 用户数据修改必须考虑：
   - provenance；
   - revision；
   - soft delete；
   - audit。
10. AI pipeline 不得修改 USER_* 数据。
11. 所有 destructive operation 首先判断其语义究竟是：
   - hide；
   - reject；
   - detach；
   - soft delete；
   - hard delete。
12. 不确定时默认使用非破坏性操作。
13. 不实现 Recommendation Score。
14. 不引入 PostGIS、Elastic、Redis 等本阶段不需要的基础设施。
15. PR 完成后逐项验证本文件 Acceptance Criteria。

---

# 104. Agent 推荐起始 Prompt

执行时可以直接给 Agent：

```text
你正在开发仓库 ThunStorm/do-not-litter，
目标分支 codex/mac-mini-implementation。

首先阅读：

dev/PLACE_INTELLIGENCE_MAP_V2_IMPLEMENTATION_PLAN.md

不要扫描整个项目。

当前只执行该计划中的下一个未完成 PR。

开始前：
1. 确认当前 PR 名称与目标；
2. 根据计划中列出的路径，只读取相关文件；
3. 列出预计修改文件；
4. 检查现有测试；
5. 然后直接实施。

严格遵守以下原则：

- Place、PlaceMention、PlaceInsightItem、MapMarkerState 职责分离；
- AI 数据不得覆盖 USER_ADDED / USER_CORRECTION；
- hide marker、reject mention、delete place 必须是不同操作；
- USER_CREATED Place 使用 soft delete；
- 用户地图点击产生的坐标不能视为 POI verified；
- 用户可编辑对象采用 revision / optimistic concurrency；
- 地图 AMap.Map 实例只能初始化一次；
- pan / zoom / marker selection 不得重建地图；
- SOURCE_FACT 必须保留 evidence；
- 不实现 recommendation score；
- 不做当前 PR 以外的大规模重构。

实施完成后：
1. 运行相关 backend/frontend tests；
2. 新增必要 regression test；
3. 按计划 Acceptance Criteria 自查；
4. 报告：
   - 修改内容
   - 修改文件
   - 数据库 migration
   - API 变化
   - 测试结果
   - 尚存风险
   - 下一 PR 建议

如果现有代码与计划冲突：
不要绕过计划悄悄实现。
先判断是不是现有架构遗留问题。
优先选择保持数据可追溯、用户修改不丢失、未来可迁移的方案。
```

---

# 105. 最终实施优先级

如果只看接下来最值得做的工作：

```text
PR1 Map Runtime
        ↓
PR2 Place Insight Schema
        ↓
PR3 AMap Resolver V2
        ↓
PR4 Editing Foundation
        ↓
PR5 Manual Pin
        ↓
PR6 POI Review
        ↓
PR7 Map Explorer
```

其中：

```text
PR1 + PR2 + PR3 + PR4
```

属于基础架构。

不要在它们完成之前开始做 Recommendation Score。

---

# 106. 最终架构原则

整个地点系统最终坚持四条原则：

### 事实不覆盖

```text
原始来源永远可追溯
```

### 人工优先但不篡改历史

```text
用户可以修正显示和结果
但原始 AI/视频事实仍保留
```

### 地点与地图解耦

```text
Place 是地点
Marker 只是地图表现
```

### Identity 与 Opinion 解耦

```text
高德回答“这是哪里”
视频回答“作者觉得这里怎么样”
用户回答“我自己怎么记录这里”
```

只要这四条不被破坏，未来加入：

```text
多视频聚合
推荐指数
用户偏好
自动路线
更多地图 Provider
旅游季节 enrichment
```

都不需要再次推翻底层数据结构。
