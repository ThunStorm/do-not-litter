# 地图 / 地点管理 / 路线稳定化执行计划 v2

> 建议仓库落点：`dev docs/planning/MAP_PLACE_MANAGEMENT_AND_UI_REFINEMENT_PLAN.md`
> 关联视觉规范：`dev docs/design/FRONTEND_VISUAL_DESIGN_SYSTEM.md`
> 基线分支：`codex/mac-mini-implementation`
> 审阅基线提交：`77e37ebf15eaab59bd23dbd384b8040702f2aa60` (`feat: stabilize travel map and route decisions`)
> 目标：修复现存交互回归，建立统一视觉系统，把地图从“展示 + 零散编辑”推进为“旅行地点决策工作区 + 全量地点管理”。

## 0. 本轮范围

只处理：

1. `/routes` 路线仍无法实际删除；
2. `/map` Marker 视觉/空间重叠；
3. 地图 Dropdown 与项目 UI 不一致；建立项目级视觉规范并加入 Agent 强制路由；
4. 重构筛选栏；类型中文化；适宜时间增加季节、月份、上/中/下旬、一天时段，并使用有关联的数据模型；
5. 重做地图新增地点：点击地图仅确定搜索区域，确认搜索结果后才自动标记，并可取消；
6. 增加地点永久删除入口；
7. 增加全量地点列表管理入口，支持批量筛选/编辑/删除，并进入单地点详情二级页。

本轮仍不做：推荐指数/评分、自动行程、路线优化、未经 Route Provider 验证的距离/交通时间、天气/常识推断最佳月份、非视频旅行输入扩展、Android/微信小程序迁移。

---

# 1. 当前源码核对结论

## 1.1 路线删除：已写接口，但实际链路仍失败

当前已经存在：

- `RoutesPage.tsx` 删除按钮；
- `api.deleteRoute(routeId)`；
- `DELETE /api/travel/route-drafts/{route_id}`；
- `RouteDraftItem.route_draft_id` 的 `ON DELETE CASCADE`。

因此禁止简单“再加一个删除按钮”后宣布完成。必须真实复现：空路线、含 1 个地点、含多个地点、当前正在 Map Route Filter 中使用的路线。记录 Network、HTTP status/body、后端异常、删除前后 `route_drafts`/`route_draft_items`、React Query 刷新结果。

修复后：路线立即消失；Place 不受影响；地图不保留已删除 routeId；若当前筛选该路线则回到“全部路线”。

## 1.2 Marker 重叠：同时处理视觉双层与真实坐标碰撞

当前 CSS 同时存在 `.amap-marker` 和旧 `.map-marker`；`.amap-marker` 又由旋转外形 + `::after` 内圆组成，容易呈现“两个标记叠在一起”。此外，高 Zoom 下不同 Place 坐标相同/极近时也会实际互相遮挡。

本轮必须同时处理：

- 视觉：统一单一 SVG/DOM `PlaceMarker`，删除旧 `.map-marker` 和 pseudo-element 拼接。
- 空间：低 Zoom cluster；高 Zoom 同坐标/近像素点变成 Stack Marker，显示数量，可展开地点列表/局部 spiderfy；selected z-index 最高。

---

# 2. 视觉规范先行

先将配套文档落到：

`dev docs/design/FRONTEND_VISUAL_DESIGN_SYSTEM.md`

并同步：

### `AGENTS.md`

增加硬规则：任何 `frontend/` 页面布局、组件、样式、表单、地图覆盖物变更必须按需读取视觉规范；不得新增裸原生 Dropdown、私有按钮体系、未登记颜色/字号；PC/Mobile 受影响断点必须 Browser 验收。

### `dev docs/CODEX_CONTEXT.md`

路由表新增：

`前端 / UI / 视觉 / 样式 / 布局 / 组件 / Dropdown / Filter` → `design/FRONTEND_VISUAL_DESIGN_SYSTEM.md`

地图行补充：变更地图前端布局/控件/Marker 时同时读取视觉规范对应章节。

### `design/ui/README.md`

明确截图是 reference；视觉规范才是 Token / Component normative source。

---

# 3. 地图 Workspace 重构

当前页面由 Header、Search、Filters、Route/action、Map tools、Add Marker、Place Preview、Add Flow 多个绝对定位层叠加，破坏一体感，Mobile 更明显。

## PC 新结构

```text
┌──────────────────────────────────────────────────────────────┐
│ Map Toolbar                                                  │
│ [搜索地点…] [状态] [类型] [适宜时间] [路线] [更多]  [地点管理] │
│                                         [待确认] [路线清单]   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│                         AMap                                 │
│                                             ┌──────────────┐ │
│                                             │ Place Preview │ │
│                                             └──────────────┘ │
│                                                              │
│ [添加地点]                         [定位][+][-][全国视野]      │
└──────────────────────────────────────────────────────────────┘
```

规则：Toolbar 是一个整体；待确认为中性色图标，有 pending 数量才显示红 Badge；地点管理固定进入 `/places`；地图本体不承载复杂编辑表单；Preview 只做快速决策，深度编辑进入详情页。

## Mobile

顶部搜索；下方横向 Filter Chips；复杂筛选进 Bottom Sheet；Place Preview 为底部 Sheet。禁止多个独立 absolute 浮层互相抢空间。

---

# 4. Filter 重构

地图第一层只保留：

- 状态
- 类型
- 适宜时间
- 路线
- 更多

不要横向铺开“月份/季节/旬段/一天时段/来源/可见性”等大量独立 Dropdown。

## 4.1 中文地点类型

新增统一 adapter（如 `frontend/src/features/map/placeLabels.ts`），内部 API 保持 Enum，UI 统一中文：

- SCENIC_AREA → 景点
- RESTAURANT → 餐饮
- NEIGHBORHOOD → 街区
- PEDESTRIAN_STREET → 步行街
- BUSINESS_DISTRICT → 商圈
- MARKET → 市集
- PARK → 公园
- MUSEUM → 博物馆
- TEMPLE → 寺庙
- VILLAGE → 村落
- TOWN → 古镇/城镇
- LANDMARK → 地标
- ACCOMMODATION/HOTEL → 住宿
- TRANSIT/TRANSPORT → 交通
- OTHER/UNKNOWN → 其他

禁止在 JSX 内散落 switch。

---

# 5. “适宜时间”升级为关联 Visit Window

## 5.1 旧模型问题

当前提取只有：`best_months[]`、`best_seasons[]`、`best_time_slots[]`。它可以表示“秋季”“10 月”“下午”，但无法知道这些值是否属于同一条来源事实，因此不能保证“秋季 + 10 月中旬”正确联合筛选。

## 5.2 新表 `place_visit_windows`

建议新增 migration 与 ORM：

```text
id
place_id                  FK places ON DELETE CASCADE
place_mention_id          nullable FK place_mentions
source_id                 nullable FK sources
season                    nullable
month                     nullable integer 1..12
month_segment             nullable EARLY | MID | LATE
day_time_slot             nullable
source_text               text
provenance                SOURCE_FACT | USER_ADDED | USER_CORRECTION
confidence                float
status                    ACTIVE | SUPERSEDED | REMOVED
created_at
updated_at
```

索引：`(place_id,status)`、`(season,month,month_segment,status)`、`(day_time_slot,status)`；Check Constraint 限制 month、season、segment、slot 合法值。

## 5.3 新提取结构

Prompt 改为输出有关联的：

```json
{
  "visit_windows": [
    {
      "season": "AUTUMN",
      "month": 10,
      "month_segment": "MID",
      "day_time_slot": "AFTERNOON",
      "source_text": "十月中旬秋色最好，下午光线更漂亮"
    }
  ]
}
```

同一 row 代表同一条相关事实：筛“秋季”、筛“10 月”、筛“10 月中旬”、筛“秋季 + 10 月中旬”都能命中。同一地点可有多条 Visit Window。

禁止通过常识把“秋季=9–11 月”自动写成来源事实。常规季节月份关系最多用于 UI 提示，不进入 source-backed data。

## 5.4 旬段

- EARLY → 上旬
- MID → 中旬
- LATE → 下旬

本轮视为定性旅行标签，不转换成精确日期区间。

## 5.5 一天时段

EARLY_MORNING 清晨；MORNING 上午；NOON 中午；AFTERNOON 下午；SUNSET 日落；EVENING 晚间；NIGHT 夜间；BREAKFAST 早餐；LUNCH 午餐；DINNER 晚餐；LATE_NIGHT 深夜。

“适宜时间” Popover 内分：季节 / 月份 / 旬段 / 一天时段。Active Chip 可显示：`适宜时间 · 秋季 / 10月中旬 / 日落`。

---

# 6. 旧时间数据兼容

不立即删除 `BEST_MONTH / BEST_SEASON / BEST_TIME_SLOT`。

迁移：

1. 新增 PlaceVisitWindow；
2. 历史 BEST_MONTH 生成 month-only window；
3. BEST_SEASON 生成 season-only window；
4. BEST_TIME_SLOT 生成 day-time-only window；
5. **禁止把三条互不相关旧 Insight 自动拼成一个相关窗口**；
6. 新视频开始输出 visit_windows；
7. 可暂时继续物化 legacy Insight，保证现有详情/导出不断；
8. 稳定后另开工作包决定是否废弃旧数组。

---

# 7. Map API 筛选契约

建议统一：

```http
GET /api/travel/map?
  state=SAVED
  &place_type=SCENIC_AREA
  &season=AUTUMN
  &month=10
  &month_segment=MID
  &day_time_slot=SUNSET
  &route_id=route_x
  &source_id=src_x
  &visibility=VISIBLE
  &bbox=...
  &zoom=...
```

语义：同一时间维度多选 OR，不同时间维度必须在**同一个 VisitWindow row** 上 AND；再与 Place 状态、类型、路线、来源、可见性 AND。避免多个独立 EXISTS 误把不同来源事实拼成一个组合。

---

# 8. 地图新增地点：Search-first，不做 Draft Marker

当前 map click 会立即 `new AMap.Marker(...)`，这条主流程应退出。

## 8.1 状态机

```text
IDLE
  ↓ 添加地点
CHOOSE_SEARCH_AREA
  ↓ 单击地图
SEARCHING_POI(anchor only)
  ↓ 选择搜索结果
CONFIRMING
  ↓ create/reuse canonical Place
DONE
  ↓ map refresh + auto select
IDLE
```

### CHOOSE_SEARCH_AREA

地图单击只保存 `{lng,lat}` 到内存，并作为附近 POI 搜索中心；**不创建临时 Marker**。

### SEARCHING_POI

自动加载附近 POI并打开 Search Panel，搜索框 focus。结果展示名称、中文类型、地址，以及 Provider 确实提供时的距离。

### CONFIRMING

确认结果后使用 POI 自身 provider ID/坐标调用 canonical create/reuse；invalidate map/places；刷新后正式 Marker 自动出现并自动 selected。

## 8.2 取消

新增 `cancelAddMode()`：Escape、关闭、“取消”、路由切换都会清 anchor/result、关闭 panel、恢复 IDLE，不写 DB、不创建 AMap Marker、不留视觉残留。

“重新选择区域”只清 anchor/result，回到 CHOOSE_SEARCH_AREA。

自定义地点若继续支持，应进入独立高级流程，通过名称/地址搜索或明确 geocode 完成，不混入普通 POI 搜索主路径。

---

# 9. 地点永久删除

用户已明确要求硬删除入口。本轮允许**显式永久删除 Place**，但必须保护 Source/Evidence。

## 9.1 三种动作严格区分

| 动作 | 可恢复 | 影响 |
| --- | --- | --- |
| 隐藏 Marker | 是 | 地图可见性 |
| 不感兴趣 | 是 | user_state |
| 永久删除地点 | 否 | 删除 canonical Place 及地点域从属数据 |

永久删除不得级联删除 Source、VideoAsset、Transcript、Segment、Snapshot、Evidence。

## 9.2 删除内容

删除 Place 及 PlaceObservation、PlaceInsightItem、PlaceVisitWindow、MapMarkerState、PlaceUserNote、PlaceUserOverlay、PlaceNoteVersion、RouteDraftItem 等地点域从属数据。

保留 PlaceMention 与来源证据。PlaceMention：`place_id=NULL`，resolution 改为明确用户删除语义；若不新增 enum，可先使用 `REJECTED` + metadata（`deleted_by_user=true`、`former_place_id`、provider/id 快照），不能留下 `CONFIRMED + place_id=NULL`。

## 9.3 防自动复活

强烈建议新增 `place_deletion_tombstones`：

```text
id
external_provider
external_poi_id
normalized_name
former_place_id
deleted_at
reason
```

Provider-bound Place hard delete 时写 tombstone；Resolver 遇到同 provider+poi_id 默认不自动重建。地点管理高级动作“允许重新导入”可清 suppression。

否则硬删除后下一次重解析又出现，用户语义不完整。

## 9.4 API

```http
GET /api/travel/places/{place_id}/deletion-impact
DELETE /api/travel/places/{place_id}/hard
```

请求需要明确确认字段，例如 `confirm_name`。事务顺序：检查 → audit/tombstone → 更新 PlaceMention → 删除 Place → commit；失败全 rollback。

Map Preview 不放高风险的一键删除主按钮；详情页 Danger Zone 和地点管理 Overflow/批量操作才提供永久删除。

---

# 10. 全量地点管理中心 `/places`

当前已有 `/places/:placeId`，新增 `/places`：

```tsx
<Route path="/places" element={<PlacesPage />} />
<Route path="/places/:placeId" element={<PlaceDetailPage />} />
```

## 10.1 入口

Map Toolbar 固定“地点管理”入口。先不扩大全局 Sidebar；后续若使用频率足够高再提升。

## 10.2 PC 列表字段

- checkbox
- 地点名称
- 类型
- 城市/地址
- 来源
- 适宜时间
- 状态
- 所属路线
- 地图可见性
- 更新时间
- 操作

默认分页/游标，例如 50 条，不一次全量加载。

## 10.3 筛选

复用 Map 相同筛选语义：搜索、类型、状态、季节、月份、旬段、一天时段、来源视频、路线、Marker 可见性、Origin；高级可显示 suppression/tombstone。

## 10.4 批量操作

第一版支持：加入/移出路线、隐藏/恢复 Marker、改状态、加/删用户标签、修改显示类型（写 Overlay）、永久删除。

不要前端循环 N 次危险请求。建议：

```http
PATCH /api/travel/places/bulk
POST /api/travel/places/bulk-delete-impact
POST /api/travel/places/bulk-hard-delete
```

批量操作必须有清晰事务语义，并返回 requested/succeeded/failed/failures 或明确 all-or-nothing。

---

# 11. 地点详情二级页

保留已有 `PlaceDetailPage`，不另造第二套详情，重构为：

```text
[返回地点管理 / 返回地图]

地点名
类型 · 地址 · POI 状态 · 来源

[概览]
[适宜时间]
[地点洞察]
[来源与证据]
[我的覆盖信息]
[备注]
[编辑历史]

Danger Zone
  [永久删除地点]
```

## 11.1 适宜时间编辑

不再以 `BEST_MONTH + 任意自由文本` 作为主要编辑方式。使用结构化 VisitWindow：季节 SelectMenu、月份 SelectMenu、旬段 SelectMenu/Segment、一天时段 MultiSelect、说明文本。人工添加为 USER_ADDED；来源事实不可覆盖，纠正写 USER_CORRECTION。

## 11.2 类型编辑

继续使用 `PlaceUserOverlay.override_place_type`，中文 SelectMenu 显示，内部发送 Enum，不直接改 canonical source fact。

---

# 12. 全量 Place 查询 API

新增：

```http
GET /api/travel/places
```

参数：`q`、`place_type[]`、`state[]`、`season[]`、`month[]`、`month_segment[]`、`day_time_slot[]`、`source_id[]`、`route_id[]`、`visibility`、`origin[]`、`sort`、`cursor`、`limit`。

响应：

```json
{
  "items": [],
  "next_cursor": null,
  "total": 123
}
```

地图仍使用 bbox/zoom 专用 endpoint；两个 endpoint 共用筛选 builder，不直接互相复用响应结构。

---

# 13. 共享后端过滤层

建议新增 `backend/src/zhijian/services/place_query.py`，统一构造 Place base query、VisitWindow correlated filter、Source/Route/Visibility/Origin/State/Type。`map_overview()` 和 `list_places()` 共用，保证地图筛选与列表筛选语义不分叉。

---

# 14. 路线删除修复细节

## Backend tests

新增：

- `test_delete_empty_route`
- `test_delete_route_with_items`
- `test_delete_route_preserves_places`
- `test_deleted_route_disappears_from_route_filter`

如果复现证明实际环境 cascade 不可靠，改为确定性先删 RouteDraftItem 再删 RouteDraft，即使仍保留 FK cascade 也不依赖隐式行为。

## Frontend

- `window.confirm` → `ConfirmDialog`；
- pending 禁重复点击；
- error 显示在 Dialog；
- success invalidate `routes` + map；
- 当前 routeId=deleted 时 reset；
- 成功 Toast。

---

# 15. Marker 修复细节

新增 `frontend/src/features/map/PlaceMarker.tsx`，使用单一 SVG。AMap content 只挂一个 root，统一 bottom-center anchor/offset，selected 仅改变同一个 marker 的状态。

清理：`.map-marker`、`.amap-marker::after`、所有 draft Marker CSS。

新增 Stack Marker：count badge + 小地点列表/局部展开。

---

# 16. 测试策略

## Backend

覆盖：route delete、place hard delete、deletion impact、tombstone prevents auto recreate、PlaceMention preserved、Source/Evidence preserved、bulk operations、VisitWindow validation、correlated filtering、map/list filter consistency、legacy backfill。

迁移必须在隔离 SQLite 从当前真实 migration head 升级，并检查 FK integrity。

## Frontend

覆盖：SelectMenu keyboard、FilterPopover reset、中文 Enum、Visit Time summary、add mode cancel、POI confirm 前无 marker、confirm 后 marker 出现、route delete success/error、PlacesPage bulk selection、Danger Confirm、stale routeId reset。

## Browser

PC：`/map`、`/routes`、`/places`、`/places/:id`。Mobile：`/map`、`/places`、`/places/:id`。

检查 Dropdown、Toolbar 一体感、Marker/Stack、add/cancel、route delete、hard delete、batch bar、返回上下文。Browser 验收不调用真实 LLM、不重跑真实视频。

---

# 17. Work Packages

每个 WP 独立提交/验收；完成一个后停止，不自动继续下一包。

## WP0 — 复现与契约冻结

- 复现 route delete；
- 复现 marker overlap；
- PC/Mobile map baseline；
- 确认实际 migration head；
- 加入本计划与视觉规范；
- 更新 AGENTS/CODEX_CONTEXT/design README。

验收：两个 bug 有复现证据；视觉规范能被 Agent 最短接手路径发现。

## WP1 — Design System primitives + Map Toolbar

- Token；
- SelectMenu；
- FilterChip/Popover；
- ConfirmDialog；
- Toast；
- Map Toolbar；
- 地图主页面移除 native selects；
- 中文 enum adapter。

暂不做时间新 schema。

验收：地图主下拉统一；PC/Mobile 不再浮层互压；键盘交互通过。

## WP2 — Route Delete 回归修复

找根因；backend deterministic delete（如需要）；ConfirmDialog；query invalidation；tests。

验收：空/非空路线可删；Place 不删；map route filter 同步。

## WP3 — Marker + Add Place 状态机

单一 PlaceMarker；高 Zoom stack；移除 draft Marker；search-anchor 模式；cancel/reselect；confirm POI 后自动 marker。

验收：无双层 Marker；同坐标可操作；确认前无新增 Marker；cancel 零残留。

## WP4 — VisitWindow 数据模型与筛选

migration、ORM、extraction schema/prompt、materialization、backfill、共享 query filter、UI 适宜时间 Popover。

验收：“秋季 + 10月中旬”由同一 VisitWindow 命中；不会把独立 Insight 误拼；旧数据仍可单维度筛选。

## WP5 — Hard Delete

Deletion impact、hard delete transaction、tombstone/suppression、resolver guard、detail Danger Zone、tests。

验收：Place 真删；Source/Evidence 保留；PlaceMention 不为悬空 CONFIRMED；provider POI 不自动复活；可显式解除 suppression 后重新导入。

## WP6 — Places Management Center

`/places`、list API、DataTable/Mobile cards、filters、batch actions、detail link、return context。

验收：全量地点可列表管理、批量筛选/编辑/隐藏/路线/永久删除；点击进入现有 `/places/:id`。

## WP7 — 详情页结构化编辑与全量回归

PlaceDetail 迁移到视觉规范；VisitWindow editor；中文 type SelectMenu；source/user provenance；全量测试 + Browser acceptance；只在有证据时更新 IMPLEMENTATION_STATUS / regression guard / handoff。

---

# 18. 删除安全边界

本轮用户已明确授权“地点硬删除入口”，但不意味着自动删除、Marker 隐藏时删除、Dismiss 时删除、删除 Source/Evidence、Resolver 任意清库。只有用户显式执行“永久删除地点”才进入 hard delete transaction。批量永久删除必须再次展示数量与影响。

---

# 19. 冻结的产品选择

1. Map 不是表格管理页；批量工作进 `/places`。
2. Map Filter 用统一 Toolbar/Chip/Popover，不用连续原生 Select。
3. 类型中文显示，内部仍是 Enum。
4. 适宜时间使用结构化 VisitWindow，不由三个独立数组拼接。
5. 点击地图不是落点，只是选搜索区域。
6. 正式坐标来自确认后的 Provider POI。
7. 取消新增零残留。
8. Hard Delete 是显式危险动作，Source/Evidence 不随 Place 删除。
9. Provider-bound Hard Delete 需要 suppression/tombstone 防自动复活。
10. Place Detail 继续 `/places/:id`，不造第二套详情。
11. 路线删除先修真实回归，不重复实现已有按钮/API。
12. 推荐评分与自动行程不进入本轮。

---

# 20. 最终 Definition of Done

用户应能完成：视频地点解析/确认 → 地图单一无重叠 Marker → 中文类型/状态/路线/适宜时间筛选 → “秋季 + 10月中旬”关系筛选正确 → 地图点击只选搜索区域 → 搜索确认 POI 后自动 Marker → 可取消且无残留 → 路线真实可删 → 地图进入地点管理 → 全量地点列表批量管理 → `/places/:id` 二级详情 → Overlay/标签/VisitWindow/备注编辑 → 永久删除有影响确认且不删 Source/Evidence → 所有前端遵循统一视觉规范 → PC/Mobile Browser 验收通过。

---

# 21. 给执行 Agent 的启动提示词

```text
你正在 ThunStorm/do-not-litter 的 codex/mac-mini-implementation 分支工作。

当前任务只执行 MAP_PLACE_MANAGEMENT_AND_UI_REFINEMENT_PLAN.md 中我明确指定的一个 Work Package，不得自动继续下一个 WP。

最短接手：
1. 读根 AGENTS.md。
2. 读 dev docs/CODEX_CONTEXT.md。
3. 读 dev docs/IMPLEMENTATION_STATUS.md 的当前状态。
4. 用 rg 只定位 REGRESSION_AND_CHANGE_GUARD.md 与本 WP 直接相关条目。
5. 如果本 WP 涉及 frontend/UI，必须读 dev docs/design/FRONTEND_VISUAL_DESIGN_SYSTEM.md 的相关章节。
6. 只读本 WP 涉及的目标源码/测试，不扫描 COMPLETE_PROJECT_SPEC、history 或全部 planning。

硬约束：
- 不调用真实 LLM/Provider。
- 不重跑真实视频。
- 不迁移生产库。
- 不重启生产服务。
- 不自动提交/推送，除非我明确要求。
- Source/Snapshot/Segment/Evidence 不因 Place 硬删除而删除。
- Marker 隐藏、Dismiss、Place Hard Delete 是三个不同动作。
- 前端不得新增裸原生 dropdown、私有按钮体系、未登记颜色/字号。
- UI Enum 必须中文展示。
- 地图点击只能选择搜索区域；POI 确认前不得生成正式或临时 Marker。
- 时间筛选必须基于同一 VisitWindow 的关联字段，不能把独立 Insight 错误拼接。
- 完成后只报告：改动、测试、Browser 验收、已知限制；不要扩展范围。
```
