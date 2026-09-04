# 至简：地图稳定化、地点管理与旅行决策能力实施计划

> Repository: `ThunStorm/do-not-litter`  
> Target branch: `codex/mac-mini-implementation`  
> Baseline inspected: `8a6484b94bf1f59edfbeb55229b7ee255836f1b3` (`feat: ship place intelligence map v2`, 2026-09-04)  
> 建议落库路径：`dev docs/planning/PLACE_MAP_STABILIZATION_AND_TRAVEL_DECISION_PLAN.md`  
> 性质：Map V2 落地后的稳定化 + 地点管理闭环 + 第一阶段旅行决策能力；不做推荐指数和自动行程规划。

---

## 0. 本轮目标

本轮不要继续增加彼此孤立的地图按钮，而要把现有能力收敛成一条用户真正可用的链路：

```text
视频输入
→ Transcript / Evidence
→ 地点与核心信息抽取
→ 高德 POI 校验 / 人工确认
→ Canonical Place
→ 地图 Pin
→ 用户增删改 / 隐藏恢复
→ 按类型、状态、适宜月份/时段、路线筛选
→ 加入并维护路线清单
→ 辅助用户做旅行路线决策
```

核心判断：

1. **Place 是现实地点实体，不等于 Pin。**
2. **Marker 只是 Place 的地图投影与可见性状态。**
3. **AI 来源事实不能被用户编辑直接覆盖；用户修正使用 Overlay / User Note / USER_CORRECTION Insight。**
4. **所有创建来源最终统一进入同一套 Place 管理逻辑。**
5. **隐藏、删除、不感兴趣必须是三个不同动作。**
6. **路线清单必须成为一等对象，不能再默认操作 `routes[0]`。**
7. **筛选必须服务“去哪、什么时候去、放进哪条路线”，而不是仅做地图装饰。**

---

# 1. 当前实现诊断与产品决策

## 1.1 设置：删除“转写校对主模型 / 备用模型”专项路由

### 当前状态

目前同时存在两套配置入口：

- `model-routing`
  - `primary_id`
  - `fallback_id`
  - `transcript_primary_id`
  - `transcript_fallback_id`
- `AIStagePolicy`
  - `TRANSCRIPT_CORRECTION`
  - `local_profile_id`
  - `remote_profile_id`
  - `execution_mode`
  - retry / timeout / thinking / token 等阶段参数

`provider_for_role()` 仍会先读取 transcript 专属 legacy routing，再由 Stage Policy 覆盖/重排，导致同一件事在两个地方都能配置。

### 决策

**删除 `transcript_primary_id` 与 `transcript_fallback_id` 的 UI、API schema 和持久化语义。**

保留：

- “推理主模型”
- “推理备用模型”

它们作为未专项绑定模型时的默认 Profile 池；具体 `TRANSCRIPT_CORRECTION` 由 Stage Policy 唯一负责。

### 兼容迁移

升级时：

1. 若旧 `model-routing.transcript_primary_id` / `transcript_fallback_id` 存在；
2. 且 `ai-stage-policy:TRANSCRIPT_CORRECTION` 没有显式 `local_profile_id / remote_profile_id`；
3. 根据旧模型 Profile 的 `location` 折叠写入 Stage Policy；
4. 保持现有 execution mode；
5. 成功迁移后删除 legacy transcript 字段。

不要让用户升级后无声换模型。

### 受影响文件

- `frontend/src/features/settings/SettingsPage.tsx`
- `frontend/src/lib/types.ts`
- `frontend/src/lib/api.ts`
- `backend/src/zhijian/api/router.py`
- `backend/src/zhijian/services/video_support.py`
- `backend/src/zhijian/domain/schemas.py`（实际 ModelRoutingConfig 所在文件以 `rg` 为准）
- 对应 tests / migration

---

# 2. 地图修复项

## 2.1 “待确认”入口：从红色常驻 CTA 改成异常队列入口

### 问题

当前地图顶部常驻红色 `待确认` pill，会产生“这是一个需要操作的主按钮”的暗示；即使队列为空也继续吸引点击。

### 决策

顶部 actions 顺序建议：

```text
[待确认 icon] [导出] [全国视野] [搜索]
```

规则：

- 使用与 download / reset / search 同级的 `icon-button`，不再使用红底 pill。
- `pending_review_count == 0`：普通中性色 icon，无红色状态。
- `pending_review_count > 0`：icon 上显示小红点或数字 badge，例如 `3`；红色仅表示“确实存在待处理项”。
- `aria-label`：`待确认地点，3 项` / `暂无待确认地点`。
- 不要用整块红色按钮表达常驻导航。

建议新增轻量 count：

```http
GET /api/travel/place-reviews/count
→ { "count": 3 }
```

不要为了一个数字拉取全部候选 POI。

### place-reviews 空状态

当前 `.panel` 本身无正文 padding，空状态 `<h2>/<p>` 直接贴边。

改成专用：

```tsx
<section className="panel review-empty-state">
  <MapPinCheck />
  <h2>没有待确认地点</h2>
  <p>出现无法自动确认的地点时，会在这里等待你选择。</p>
</section>
```

要求：

- 内边距 desktop 24–32px；mobile 20px；
- icon / title / text 有清晰层级；
- 不使用错误态红色；
- 页面仍可从 URL 直接访问。

---

## 2.2 “适配全部”改为真正的“全国视野”

### 已确认根因

当前按钮调用：

```text
fitPlaces()
→ setFitView(mapMarkersRef.current)
```

但地图 API 在 `zoom < 6` 时只返回 `clusters`，`markers=[]`。因此全国尺度下 `mapMarkersRef.current` 本身为空，“适配全部”天然可能什么也不做。

同时默认全国视野只是：

```text
bbox = [73.5, 18, 135.1, 53.6]
zoom = 4
center = bbox 中点
```

不是依据容器宽高真正 fit bounds。

### 决策

将按钮文案改为 **“全国视野”**，语义与行为一致。

在 `AmapLayer` controller 新增：

```ts
fitChina(): void
fitVisibleResults?(): void   // 可后续加入，不与全国视野混用
```

`fitChina()` 必须使用中国范围 Bounds + padding，由高德计算实际 zoom，而不是固定 `zoom=4`。

要求：

- desktop / mobile / resize 后均能完整覆盖中国大陆目标范围；
- `ResizeObserver` 检测地图容器尺寸改变后调用地图 resize/重算；
- reset 后把地图真实返回的 bbox/zoom 写入 session viewport；
- 初次进入地图也走同一 `fitChina()` 逻辑；
- 不再有一套初始化算法、一套 reset 算法。

---

## 2.3 地图选点：统一为“搜索并创建地点”流程

### 当前已有

地图选点后已有 `nearbyPois(longitude, latitude)` 与自定义地点创建，但：

- 只展示附近 POI；
- 没有完整关键词搜索体验；
- 创建后没有进入统一编辑器；
- 用户创建与视频自动地点的后续操作不一致。

### 新流程

```text
点击“添加地点”
→ 地图进入选点模式
→ 用户点一个坐标
→ 打开 Add Place Sheet
   ├─ 搜索地点（关键词，可修改）
   ├─ 附近地点（默认）
   └─ 创建自定义地点
→ 选择高德 POI / 自定义创建
→ 返回 Place
→ 立即打开统一 Place Editor / Preview
```

Add Place Sheet 必须支持：

- 当前坐标；
- 附近 POI；
- 关键词全文搜索；
- 候选名称、地址、距离/行政区信息；
- “都不是，创建自定义地点”；
- 取消后清理 draft marker。

选择高德 POI 时继续以 `external_provider + external_poi_id` 作为 identity，不直接使用点击坐标覆盖高德坐标。

---

## 2.4 路线清单补全 CRUD

### 当前缺口

现有：

- 新建 route；
- PUT route items；
- 上移/下移。

缺少：

- 重命名 route；
- 删除 route；
- 从 route 中删除单个地点；
- 地图加入路线时选择目标 route；
- 没 route 时快速创建。

地图当前硬编码 `routes.data?.[0]`，这是“加入路线不可用/行为不明确”的根因之一。

### 后端新增

```http
PATCH /api/travel/route-drafts/{route_id}
{
  "name": "云南秋季",
  "city": ""
}

DELETE /api/travel/route-drafts/{route_id}
```

单地点移除不必增加独立 endpoint，继续复用 `PUT .../items`，发送移除该 ID 后的数组即可。

### 地图“加入路线”交互

点击：

```text
加入路线
→ route chooser popover/sheet
   ├─ 云南秋季      已有 7 个地点
   ├─ 贵州周末      已有 4 个地点
   └─ + 新建路线
```

规则：

- 已在目标 route 中显示“已加入”，不可重复加入；
- 不再默认第一条 route；
- route = 0 时直接展示“新建路线并加入”；
- mutation 后刷新 route badge 和 route list。

### RoutesPage

每个 route：

- 标题旁 pencil → inline rename；
- 更多菜单 → 删除路线；
- 每个地点 row 有 remove；
- 上移/下移保留；
- 删除路线需 confirm；删除地点无需危险级 confirm，可提供短暂 undo。

---

## 2.5 Marker “重影/双标”修复：视觉 + 数据双保险

### 当前判断

当前 `/api/travel/map` 在：

- `zoom < 6`：返回 clusters，markers 为空；
- `zoom >= 6`：返回 markers，clusters 为空。

因此正常 API 返回下，cluster 与 marker 不应同时覆盖同一地点。

但当前 Marker CSS 本身由：

```css
.amap-marker { ... pin 外形 ... }
.amap-marker::after { ... 白色内圆 ... }
```

构成，视觉上可能被理解为“两个标记重合”。同时当前 `Place` 模型没有实现原 V2 规格要求的：

```text
UNIQUE(external_provider, external_poi_id)
```

因此数据库层仍存在同一高德 POI 产生多个 Place 的风险。

### 修复要求 A：Marker 视觉

将 Marker 统一成单一视觉组件，不再用容易产生“双 Pin”错觉的重叠结构。

推荐：

- 一个 pin silhouette + 一个中心 dot，中心 dot 明确作为内部装饰；或
- 单个 SVG pin；
- selected 仅改变 fill/scale，不再叠加第二个 marker。

删除未使用的 legacy `.map-marker` 样式，避免后续误用两套 marker implementation。

### 修复要求 B：身份唯一性

新增数据审计：

```sql
GROUP BY lower(external_provider), external_poi_id
HAVING COUNT(*) > 1
```

若已有重复：

1. 先实现 Place merge helper；
2. 将 PlaceMention / PlaceInsightItem / PlaceObservation / RouteDraftItem / MapMarkerState / Overlay / Note 等外键归并到 canonical Place；
3. RouteDraftItem 同 route 的重复 place 要去重；
4. MarkerState 保留用户最新 visibility/custom label；
5. 不丢 Evidence；
6. 再增加 DB unique constraint/index。

目标约束：

```text
UNIQUE(external_provider, external_poi_id)
```

`NULL` provider/id 允许多个。

### 修复要求 C：API / 前端保险

- map serialization 以 `place.id` 再做一次稳定去重；
- React marker key 使用唯一 `place.id`；
- 测试 zoom 临界值 5.9 / 6.0，确保同一响应绝不同时出现同一 Place 的 cluster + marker；
- manual AMAP create 与 POI confirm 都必须复用 existing Place。

---

## 2.6 Pin 浮窗补全删除、隐藏恢复、加入路线、编辑

### 统一操作原则

浮窗不要把危险动作都堆成主按钮。建议：

主操作：

```text
[加入路线] [查看详情]
```

次操作 / 更多菜单：

```text
编辑地点
隐藏于地图
不感兴趣
删除地点（仅 USER_CREATED）
```

### 删除语义

| 操作 | USER_CREATED | AI_EXTRACTED / POI 来源 |
| --- | --- | --- |
| 编辑显示名/类型/标签/备注 | 可以 | 可以，写 Overlay/Note |
| 隐藏 Pin | 可以 | 可以 |
| 恢复 Pin | 可以 | 可以 |
| 不感兴趣 | 可以 | 可以，改 user_state |
| 删除 Place | **软删除** | **不允许删除 canonical Place/Evidence** |

自动地点如果用户不想看到，应使用：

- 隐藏；或
- 不感兴趣；

不能把来源事实/Evidence 删除掉。

### 解决“隐藏后找不到”

地图筛选新增：

```text
可见性
○ 仅显示正常地点
○ 包含隐藏地点
○ 仅隐藏地点
```

`包含隐藏/仅隐藏` 时：

- hidden Pin 以灰色/空心样式显示；
- 点击浮窗主操作为“恢复显示”；
- 后端 map API 增加 `visibility=VISIBLE|HIDDEN|ALL`；
- 默认仍为 VISIBLE。

这样恢复动作仍发生在地图语境，不另造“垃圾箱页面”。

---

# 3. 统一 Place 增删改管理逻辑

## 3.1 一个 Place Editor，覆盖所有来源

无论地点来自：

```text
视频自动确认
人工待确认后确认
地图点选高德 POI
地图自定义创建
```

最终全部进入同一个：

```text
PlaceEditorSheet / PlaceDetail editing model
```

禁止按来源维护四套 UI。

### 可编辑字段分层

#### Canonical 不直接改

```text
external_provider
external_poi_id
POI canonical_name
canonical coordinates
source evidence
```

如 POI 错误，应进入“重新绑定 POI”专门流程，而不是直接改经纬度。

#### User Overlay 可改

```text
display_name
override_place_type
custom_tags
```

#### User Note 可改

```text
markdown
```

#### User Insight 可增删改

用户修正适宜月份、推荐项目、注意事项时，不覆盖 AI Source Fact：

```text
SOURCE_FACT status = SUPERSEDED（需要修正时）
→ USER_CORRECTION status = ACTIVE
```

或新增：

```text
USER_ADDED
```

### 建议新增 API

```http
POST /api/travel/places/{place_id}/insights
PATCH /api/travel/places/{place_id}/insights/{insight_id}
DELETE /api/travel/places/{place_id}/insights/{insight_id}
```

注意：DELETE 对用户 Insight 是撤销/软状态变化；不得物理删除来源 Evidence。

---

# 4. 地图筛选：从“几个按钮”升级成旅行决策 Facets

## 4.1 第一层快速筛选

地图顶部只保留高频维度：

```text
[状态] [类型] [适宜时间] [路线] [更多筛选]
```

不要继续平铺“全部 / 想去 / 去过 / 计划 / 景区 / ...”直到挤满地图。

### 状态

- 想去
- 已计划
- 去过
- 不感兴趣（默认不显示，可在更多中打开）

### 类型

- 景区
- 餐馆
- 街区/商圈
- 博物馆
- 公园/自然
- 住宿
- 交通点
- 其他

类型列表应来自统一 place type mapping，不写死只有 `SCENIC_AREA`。

### 适宜时间

支持：

- 本月适合（快捷项，按当前月份映射）
- 月份 1–12
- 春 / 夏 / 秋 / 冬
- 清晨 / 上午 / 下午 / 日落 / 晚间 / 夜间
- 早餐 / 午餐 / 晚餐 / 宵夜（餐饮）

### 路线

- 未加入路线
- 选择某条 route
- 可多选或先做单选；V1 建议单选，降低 UI/查询复杂度。

## 4.2 更多筛选

后续/同一工作包低优先级：

- 来源视频；
- 用户创建 / 视频发现；
- 可见 / 隐藏；
- 有无推荐项目；
- 有无注意事项；
- 城市/省份。

### 高价值建议：增加“来源视频”筛选

用户的主要入口是“丢一个视频进来”。因此处理完成后，从任务页/视频页点击“在地图查看”时，应携带：

```text
source_id / video_asset_id
```

地图只突出该视频产生的地点，用户能立即检查“这条视频到底解析出了什么”。

这是比继续加更多静态 marker 类型更符合主流程的能力。

---

# 5. 适宜月份 / 时段：视频解析必须结构化输出

## 5.1 当前基础

现有 Place Insight 已支持：

```text
BEST_MONTH
BEST_SEASON
BEST_TIME_SLOT
```

materialization 也已经读取：

```text
best_months
best_seasons
best_time_slots
```

因此本轮不是重新发明数据结构，而是：

1. 强化抽取 Prompt/Schema；
2. 规范枚举；
3. 把结构化 Insight 接到地图筛选。

## 5.2 抽取原则

只在视频来源明确表达时写 `SOURCE_FACT`。

例如：

> “10 月底银杏最好看”

输出：

```json
{
  "best_months": [10, 11],
  "best_seasons": ["AUTUMN"],
  "best_time_slots": [],
  "segment_ids": ["seg_xxx"]
}
```

例如：

> “傍晚过来正好能看日落”

输出：

```json
{
  "best_time_slots": ["SUNSET"]
}
```

禁止模型因为“常识上秋天适合”就自动补月份。天气/气候系统推导仍是未来 `SYSTEM_ENRICHED`，不属于本轮。

## 5.3 规范枚举

### BEST_MONTH

`value_key = 01..12`

### BEST_SEASON

```text
SPRING
SUMMER
AUTUMN
WINTER
```

### BEST_TIME_SLOT

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

自然语言保留在 `value_text`，筛选使用 `value_key`。

## 5.4 Map API

新增 query：

```text
best_month=10
best_season=AUTUMN
best_time_slot=SUNSET
route_id=route_xxx
source_id=src_xxx
visibility=VISIBLE|HIDDEN|ALL
```

筛选应使用 `PlaceInsightItem ACTIVE` + `EXISTS`，不要把月份复制回 `Place` 表制造第二事实源。

---

# 6. 路线决策体验：本轮做到“可组织”，先不做“自动优化”

当前目标不是自动生成行程，而是让用户能完成：

```text
发现地点
→ 筛选候选
→ 放入路线清单
→ 调整顺序
→ 在地图只看该路线
→ 判断是否值得安排
```

## 6.1 路线模式

地图选中 route 后：

- 非该 route 地点可隐藏或降低透明度；V1 推荐“只显示路线地点”；
- route 内 marker 用 `1 / 2 / 3...` 编号；
- RoutesPage 改顺序后地图编号同步；
- 不显示未经真实路线 API 验证的里程/交通时间。

## 6.2 下一阶段可做但本轮不实现

等地点管理稳定后，再考虑：

- 高德路径规划 API；
- 驾车/公交/步行时间矩阵；
- 按天分组；
- 自动建议顺序；
- 时间窗冲突检查。

在没有真实路线服务验证前，不用直线距离伪装成“建议路线”。

---

# 7. 建议新增“候选比较托盘”（P2，可延期）

这是我建议补充的旅行决策功能，但优先级低于 CRUD / filter / route。

用户在地图筛选后可把 2–6 个地点加入临时“比较”：

```text
地点           类型    最佳月份   推荐看点     注意事项    来源
A              景区    10–11     银杏         周末拥挤    2
B              古镇    9–11      夜景         商业化      3
```

用途：

- 不计算虚假的综合推荐分；
- 只把已经抽取到的事实并排展示；
- 很适合“这个周末到底去哪几个”的决策；
- 后续推荐评分体系建立后可自然接入。

若要控制本轮范围，可将其保留在文档 P2，不实施。

---

# 8. 实施 Work Packages

建议 Agent **按工作包独立提交**，不要一个 commit 同时改设置、地图、Insight schema 和路线。

## WP0 — 冻结契约与回归测试基线

目标：先用测试把本轮关键语义锁住。

新增/补充测试：

- map zoom <6 只 clusters；>=6 只 markers；
- MapMarkerState one-per-place；
- manual AMAP POI 重用 existing Place；
- auto POI confirm 重用 existing Place；
- 自动地点不可 soft-delete Place；
- USER_CREATED 可 soft-delete/restore；
- hide 不删除 Place / Insight / Evidence；
- route item PUT 可移除单地点；
- current `BEST_MONTH/BEST_TIME_SLOT` materialization 测试。

输出：测试先红或确认已有覆盖。

---

## WP1 — 设置模型路由清理

### Backend

- 删除 ModelRoutingConfig transcript 两字段；
- `provider_for_role()` 不再读取 transcript legacy route；
- `TRANSCRIPT_CORRECTION` 统一走 Stage Policy；
- generic primary/fallback 仍作为默认 Profile candidate pool；
- legacy settings 做一次兼容迁移。

### Frontend

- 删除“转写校对主模型 / 转写校对备用模型”两个 Select；
- Provider summary 中“转写校对”改为展示 Stage Policy resolve 后实际选择，或干脆取消 summary，避免第三种语义；
- 文案明确：“各工作负载阶段在下方单独配置；通用主/备作为默认模型池。”

### 验收

- 用户只在一个地方配置 TRANSCRIPT_CORRECTION；
- 旧配置升级后行为不突变；
- 删除模型时引用检查只考虑仍有效的 generic routing + stage policies。

---

## WP2 — 地图交互稳定化

一次处理：

- 待确认 toolbar icon + count badge；
- place review empty-state padding；
- 全国视野 `fitBounds`；
- resize 适配；
- Marker 单一视觉；
- 清除 legacy marker CSS；
- `origin === 'USER_CREATED'` 的 UI label 修正（当前前端判断 `USER`）；
- 增加 hidden visibility filter 与 restore；
- marker preview 更多菜单；
- USER_CREATED 删除入口；
- 自动地点仅 hide/dismiss。

### 验收场景

1. 0 待确认：无红色警告状态。
2. 3 待确认：仅 icon badge 为红色 `3`。
3. 任意窗口比例点击“全国视野”：中国全境完整进入可视区。
4. 全国聚合态点击“全国视野”仍有效。
5. 隐藏一个地点后切换“包含隐藏”，能找到并恢复。
6. 用户自建地点可软删除并从默认地图消失。
7. 视频地点没有“删除来源地点”危险操作。

---

## WP3 — Place Identity / Duplicate hardening

### 先诊断

增加只读脚本/测试检查：

- duplicate `(provider, poi_id)`；
- duplicate MapMarkerState；
- 同一 route 重复 Place；
- 高度可疑的同名同坐标 Place（只报告，不自动合并无 provider 的 custom place）。

### 再修复

- 若有 provider duplicate，执行保守 merge；
- 新 migration 增加 `(external_provider, external_poi_id)` unique；
- 保留 MapMarkerState `UNIQUE(place_id)`；
- API serializer 再去重。

### 验收

同一高德 POI 无论来自：

- 两条视频；
- 视频 + 手工搜索；
- 两次人工确认；

最终只有一个 Place / 一个可见 Pin。

---

## WP4 — 地图添加地点 + 统一 Place Editor

### Frontend 新组件建议

```text
features/map/components/AddPlaceSheet.tsx
features/map/components/PlacePreviewSheet.tsx
features/map/components/PlaceEditorSheet.tsx
features/map/components/RouteChooser.tsx
features/map/components/MapFilterBar.tsx
```

不要继续把所有状态塞进 `MapOverviewPage.tsx`。

### 功能

- 点地图 → nearby + keyword search + custom；
- 创建后打开统一 editor；
- editor 支持 display name / type / tags / note；
- marker preview 可以进入 editor；
- POI canonical identity 只读显示；
- POI 重绑作为独立 action，不直接编辑 coordinates。

### 验收

手工创建的地点与视频自动地点，在用户看来使用同一套详情/编辑/路线操作。

---

## WP5 — Route CRUD + Map route chooser

### Backend

- PATCH route metadata；
- DELETE route；
- tests。

### Frontend

- rename route；
- delete route；
- remove route item；
- add-to-route chooser；
- quick create route；
- route badge 不再依赖 `routes[0]`；
- 选中 route 后 map 可只看该 route。

### 验收

至少创建两条路线，任意 marker 能明确选择加入哪一条；删除/重命名任一条不会影响另一条。

---

## WP6 — 时间 Insight 抽取规范化 + 地图 Facet

### Extraction

强化 `EXTRACT_TRAVEL_FACTS` schema/prompt：

- best_months；
- best_seasons；
- best_time_slots；
- 只允许来源明确表达；
- 枚举正规化；
- segment evidence 必须存在。

### Materialization

- month `value_key=01..12`；
- season/time slot 统一 enum key；
- legacy free text 可保留 `value_text`，但不作为 facet key。

### Map API / UI

加入：

- best_month；
- best_season；
- best_time_slot；
- source_id；
- route_id；
- visibility。

UI 第一阶段只暴露：状态 / 类型 / 适宜时间 / 路线。

### 验收

准备测试视频 Transcript：

- “10 月底最好看银杏” → 10/11 月 facet；
- “傍晚来看日落” → SUNSET；
- 未提季节的地点不能被模型擅自补月份；
- 筛选条件组合后 map count / markers / clusters 一致。

---

## WP7 — 最终回归与真实浏览器验收

自动验证：

- backend target tests；
- backend full pytest；
- Ruff；
- frontend Vitest；
- TypeScript；
- ESLint；
- Vite build。

浏览器真实验收：

1. 打开地图；
2. resize desktop → narrow mobile；
3. 全国视野；
4. zoom cluster → marker；
5. 搜索；
6. 地图点选创建地点；
7. 编辑地点；
8. 隐藏 → 显示隐藏 → 恢复；
9. 删除 USER_CREATED；
10. 待确认 badge / 空状态；
11. 创建 2 条路线；
12. marker 分别加入不同路线；
13. 路线重命名/移除地点/删除；
14. 月份/时段筛选；
15. route filter；
16. source/video filter（若本 WP 实现）。

真实外部 Provider/高德调用仅在用户已合法配置并明确允许的验收条件下执行；测试不要擅自消耗真实模型或重跑视频。

---

# 9. API 建议汇总

现有保留：

```text
GET    /api/travel/map
GET    /api/travel/place-reviews
POST   /api/travel/map/nearby-pois
POST   /api/travel/places
PATCH  /api/travel/places/{id}/overlay
PUT    /api/travel/places/{id}/note
POST   /api/travel/places/{id}/marker/{hide|restore}
DELETE /api/travel/places/{id}/user-created
POST   /api/travel/places/{id}/user-created/restore
GET    /api/travel/route-drafts
POST   /api/travel/route-drafts
PUT    /api/travel/route-drafts/{id}/items
```

建议新增/统一：

```text
GET    /api/travel/place-reviews/count
POST   /api/travel/map/place-search        # 坐标上下文 + keyword；或复用通用 POI search service
PATCH  /api/travel/route-drafts/{id}
DELETE /api/travel/route-drafts/{id}
POST   /api/travel/places/{id}/insights
PATCH  /api/travel/places/{id}/insights/{insight_id}
DELETE /api/travel/places/{id}/insights/{insight_id}
```

`GET /api/travel/map` 新 filters：

```text
place_type
user_state
origin
query
bbox
zoom
visibility
best_month
best_season
best_time_slot
route_id
source_id
```

---

# 10. 数据迁移注意事项

当前 migration head 为 0013，本轮如果增加 schema/constraint，必须新增迁移，不修改历史 migration。

可能需要：

```text
0014_remove_legacy_transcript_routing_or_data_migration
0015_place_provider_identity_unique
```

是否拆成两个 migration 由实现时实际 schema 决定，但必须满足：

- 可从 0013 正向升级；
- 隔离 SQLite migration test；
- provider duplicate 未处理前不得直接加 unique 导致生产升级失败；
- legacy transcript route 的迁移必须可审计；
- 不写 Secret 到 migration/log。

---

# 11. 本轮不做

明确防止 Agent 越界：

- 不做推荐指数；
- 不做作者可信度评分；
- 不做个性化推荐算法；
- 不做自动生成完整行程；
- 不做路线最优化；
- 不做天气/气候数据库自动补最佳月份；
- 不把 LLM 生成坐标；
- 不做微信小程序/Android 版本；
- 不扩展其他资料输入类型，本轮仍以视频链路为主；
- 不为了地图功能删除 Source / Segment / Evidence；
- 不重构无关 Dashboard / 招聘链路。

---

# 12. 推荐执行顺序

严格顺序：

```text
WP0 测试基线
→ WP1 模型路由清理
→ WP2 地图 UI/交互稳定化
→ WP3 Place 去重与唯一性
→ WP4 添加地点 + 统一 Editor
→ WP5 Route CRUD
→ WP6 时间/路线/来源筛选
→ WP7 回归与真实浏览器验收
```

理由：

- 先修用户每天会碰到的错误交互；
- 再修 Place identity，避免后面 CRUD/route 建在重复实体上；
- 再统一编辑和 route；
- 最后把结构化 Insight 接成筛选能力。

不要一开始就做自动路线规划。

---

# 13. Definition of Done

本计划完成的标准不是“按钮存在”，而是以下用户故事全部成立：

### Story A — 视频到地图

我投入一个旅行视频后，系统抽取地点、校验 POI、确认的地点自动 Pin 到地图；不确定的地点只有在确实存在时才通过待确认 badge 提醒我。

### Story B — 地图管理

我能在地图搜索、点选并新增地点；无论地点来自 AI 还是我自己创建，都能用同一个编辑器修改显示信息、标签和备注。

### Story C — 生命周期

我能隐藏一个地点，之后通过“包含隐藏地点”再次看到它并恢复；我自己创建的地点可以删除并恢复；来源地点不会因为我的地图操作丢失 Evidence。

### Story D — 路线

我能创建多条路线，明确选择把某地点加入哪条路线，重命名路线、调整顺序、删除路线中的地点或整条路线。

### Story E — 旅行决策

我能按地点类型、想去/计划状态、适宜月份/时段、路线进行筛选；视频如果明确说“10 月最好”“傍晚看日落”，这些信息可以直接成为地图筛选条件。

### Story F — 地图可靠性

同一个高德 POI 不会因为多条视频或手动再添加而出现多个 Place/多个 Pin；全国视野在不同窗口尺寸都正确。

---

# 14. 给执行 Agent 的启动提示词

```text
你现在继续开发 ThunStorm/do-not-litter 的 codex/mac-mini-implementation 分支。

本任务只实施 dev docs/planning/PLACE_MAP_STABILIZATION_AND_TRAVEL_DECISION_PLAN.md 中当前指定的 Work Package，不跨包顺手优化。

接手顺序：
1. 读 dev docs/CODEX_CONTEXT.md；
2. 读 dev docs/IMPLEMENTATION_STATUS.md；
3. 用 rg 只定位 REGRESSION_AND_CHANGE_GUARD.md 中 map/place/route/model-routing 相关条目；
4. 读本计划的“当前 Work Package”章节；
5. 只读该 WP 涉及的目标源码与测试，不扫描 COMPLETE_PROJECT_SPEC.md 和 history。

硬约束：
- Place / PlaceMention / PlaceInsight / MapMarkerState 职责不能混用；
- 隐藏 Marker 不删除 Place/Source/Evidence；
- USER_CREATED 地点删除必须软删除；
- AI/source 地点不得因 UI 删除动作物理删除；
- LLM 不生成坐标；
- AI Source Fact 不覆盖 USER_ADDED / USER_CORRECTION；
- 不实现推荐指数、自动路线优化、天气补月份；
- 不调用真实模型、不重跑真实视频、不修改生产库、不重启服务，除非当前任务明确授权。

每个 WP：
- 先列当前事实与验收条件；
- 先补/调整目标测试；
- 再实施最小代码；
- 跑目标测试；
- WP 完成后一次全量后端/前端验证；
- 前端交互变化必须做目标页面 Browser 验收；
- 汇报实际改动文件、测试结果、仍未完成项，不把下一 WP 自动视为已授权。
```

---

# 15. 产品方向结论

Map V2 下一步最值得投入的不是“再多一种 Pin”，而是完成三个闭环：

```text
地点身份闭环：同一个现实 POI = 一个 Place
地点管理闭环：创建 / 编辑 / 隐藏 / 恢复 / 删除语义统一
决策闭环：筛选 → 对比 → 放入路线 → 调整路线
```

只要这三条成立，“视频丢进来 → 地图形成个人旅行知识库 → 使用时辅助决策”的产品主线就真正成立。
