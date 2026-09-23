# 视频语义结构、地点体系化、POI 自动确认与笔记质量优化实施计划

> 适用项目：`ThunStorm/do-not-litter`
> 目标分支：`codex/mac-mini-implementation`
> 文档用途：供 Codex / Agent 直接实施
> 设计原则：在不牺牲通用视频适配能力的前提下，提高地点抽取准确率、减少 POI 人工确认、提升视频笔记质量，并降低远程模型 Token 消耗。

---

# 1. 背景与当前问题

当前视频链路已经具备：

- 字幕 / ASR；
- Transcript Correction；
- Grounded Map；
- Travel Place Extraction；
- AI Note；
- 高德 POI Resolver；
- PlaceMention / Place / PlaceInsight；
- Place Detail；
- POI Review；
- Golden Sample 与 POI benchmark；
- 本地 / 远程模型路由；
- Token / 调用审计与缓存。

但当前设计存在几个结构性问题。

## 1.1 所有被提及地点过早进入 POI 流程

现有 `travel_place_extraction.md` 的核心目标偏向：

> 高召回提取所有明确提到、可落地图的地点。

这会把以下不同语义的地点放在同一层：

- 真正推荐游览的地点；
- 当前段落核心地点；
- 周边推荐地点；
- 路线停靠点；
- 比较对象；
- 反例；
- 背景地点；
- 仅用于解释地理位置的地点。

结果是：

```text
视频提到地点
→ PlaceMention
→ POI Resolver
→ CONFIRMED / REVIEW / UNRESOLVED
```

导致用户需要人工判断大量本不应该进入 POI 流程的地点。

典型错误：

```text
“北京故宫比沈阳故宫规模更大”
```

如果视频本身讲的是北京攻略：

```text
北京故宫      → 应参与 POI
沈阳故宫      → 仅是比较参考，不应进入 POI Review
```

当前结构无法可靠表达这种差异。

---

## 1.2 当前结构容易隐含“一视频一个核心地点”

实际视频可能存在：

```text
视频
├ 北京
│ ├ 故宫
│ ├ 天坛
│ └ 颐和园
├ 承德
│ ├ 避暑山庄
│ └ 外八庙
└ 天津
  ├ 五大道
  └ 天津之眼
```

一个视频中可以存在多个核心地点、多个地区、多个主题段落。

同时也可能完全不是“地区 → 景点”模式，例如：

- 单一景区深度攻略；
- 多景点榜单；
- 旅行路线；
- 跨地域同类景观比较；
- 美食探店；
- Vlog；
- 主题型内容；
- 纯交通 / 住宿 / 避坑类视频。

因此不能把“地区 → 景点”作为系统前提。

---

## 1.3 视频笔记存在“摘要再摘要”的信息损失

当前正常路径中：

```text
Transcript
→ GroundedMap section_facts
→ AI Note
```

GroundedMap 已经做过一次压缩，并对：

- 每 chunk facts 数量；
- summary 长度；
- key_points 数量；
- quotes 数量；

进行了较强限制。

之后 AI Note 又对压缩后的内容做二次总结。

容易造成：

- 细节丢失；
- 地点要点不足；
- 推荐理由不具体；
- 价格、预约、季节、游览时长等实用信息遗漏；
- 最终笔记出现大量低信息密度表达。

---

## 1.4 POI Resolver 已经具备基础，但自动确认还不够智能

当前 `_poi_score()` 已经支持：

- 名称完全匹配；
- 名称包含；
- 城市；
- 省份；
- 区县；
- 地点类型；
- Nearby Landmark；
- 视频内地域上下文；
- 候选差距；
- 连锁店风险；
- 坐标合法性；
- `AUTO_STRONG` shadow decision。

现有 Golden Sample 已包含：

```text
国博 → 中国国家博物馆
东方明珠 → 东方明珠广播电视塔
水路案 → 水陆庵
```

因此无需重新设计一套 POI 系统。

需要做的是：

> 在现有 Resolver V2 基础上升级为 Resolver V3，增加语义上下文、规范名匹配、行政区 Anchor、Topic/ContentUnit 地域上下文和更加严格的自动确认规则。

---

# 2. 总体目标

本次改造完成后，系统应实现：

1. 支持一个视频包含多个核心地点 / 地区 / 主题。
2. 不假设视频一定是“地区 → 景点”结构。
3. 将“内容提及”和“应该进入 POI”彻底解耦。
4. 比较对象、背景地点、反例不进入 POI 人工确认。
5. 真正推荐 / 游览 / 路线地点保持高召回。
6. 支持地点简称、官方全称、景区后缀等近似 POI 自动确认。
7. 行政区域与 POI 分开建模。
8. 视频笔记围绕实际内容结构生成，而非强行地点树。
9. 删除低信息量废话，提高笔记信息密度。
10. 大部分高吞吐处理由本地模型完成。
11. 远程模型只用于：
    - 专名高风险校对；
    - 歧义语义判断；
    - 最终高质量视频笔记生成。
12. 保持 POI 最终确认由确定性 Resolver 控制。
13. 所有关键质量都具有 Golden Fixture 与量化验收指标。

---

# 3. 核心架构原则

## 3.1 不以“地点树”为第一层抽象

统一采用：

```text
Video
↓
ContentUnit[]
├ unit_type
├ topic
├ anchor_entities[]
├ mentioned_entities[]
├ relations[]
├ atomic_claims[]
└ evidence_segments[]
```

`ContentUnit` 才是视频内容结构的第一层。

地区、景点、路线、榜单只是不同内容组织方式。

---

# 4. ContentUnit 设计

## 4.1 ContentUnit 类型

建议支持：

```text
AREA_GUIDE
PLACE_GUIDE
MULTI_PLACE_LIST
ROUTE
THEME
CATEGORY_COMPARE
EXPERIENCE
FOOD
MIXED
SUPPLEMENTAL
```

### AREA_GUIDE

示例：

```text
北京怎么玩
```

结构：

```text
北京
├ 故宫
├ 天坛
├ 颐和园
└ 圆明园
```

---

### PLACE_GUIDE

示例：

```text
故宫完整攻略
```

结构：

```text
故宫
├ 午门
├ 太和殿
├ 珍宝馆
└ 景山
```

---

### MULTI_PLACE_LIST

示例：

```text
北京最值得去的 10 个博物馆
```

不需要强制存在一个父级 POI。

---

### ROUTE

示例：

```text
川西五日自驾
```

结构应保留路线顺序，而不是地点树。

---

### THEME

示例：

```text
国内最适合秋天看的湿地
```

各地点之间是：

```text
SAME_THEME
```

而非父子关系。

---

### CATEGORY_COMPARE

示例：

```text
北京故宫 vs 沈阳故宫
```

此时两个地点均可能是主角。

不能因为出现比较关系就自动过滤其中一个。

---

### EXPERIENCE

示例：

```text
一天逛完故宫是什么体验
```

---

### FOOD

示例：

```text
天津早餐吃什么
```

---

### MIXED

旅行 Vlog 等混合型视频。

---

### SUPPLEMENTAL

交通、住宿、预约、避坑等补充章节。

---

# 5. ContentUnit 边界识别

ContentUnit 不应完全由 LLM 自由生成。

采用：

```text
本地模型提出 ContentUnit
↓
deterministic validator 校验
```

## 5.1 识别信号

综合：

```text
语义主题变化
+
连续 Segment
+
地域 Anchor 变化
+
显式转场语言
```

显式转场例子：

```text
“下面去第二个地方”
“接下来我们到天津”
“第三站”
“再来说另一个城市”
```

---

## 5.2 不应触发 ContentUnit 切换的情况

例如：

```text
“北京故宫比沈阳故宫规模更大”
```

不能因为出现“沈阳”就切到沈阳 ContentUnit。

因为：

```text
沈阳故宫 = comparison reference
```

而不是内容主题迁移。

---

## 5.3 ContentUnit Anchor 允许 0..N

禁止设计：

```python
if not core_place:
    invalid
```

正确设计：

```text
anchor_entities = 0..N
```

因为以下视频可能没有明确单一核心地点：

```text
“去新疆旅行最需要注意的 6 件事”
```

甚至某些主题内容可以：

```text
anchor_entities = []
```

---

# 6. Entity Mention 语义模型

不要再使用单一 role 枚举同时承担：

- 是否核心；
- 是否推荐；
- 是否 POI；
- 是否比较。

拆成三个维度。

## 6.1 subject_role

```text
PRIMARY
SECONDARY
REFERENCE
CONTEXT
```

表示实体在当前 ContentUnit 中的内容作用。

---

## 6.2 visit_intent

```text
RECOMMENDED
OPTIONAL
NEUTRAL
NOT_RECOMMENDED
NOT_APPLICABLE
```

表示作者对实际游览的态度。

---

## 6.3 poi_policy

```text
RESOLVE
AREA_RESOLVE
REFERENCE_ONLY
SKIP
```

---

# 7. 典型语义示例

## 7.1 北京攻略中的比较

原文：

```text
北京故宫比沈阳故宫规模大很多。
```

结果：

```text
北京故宫
subject_role = PRIMARY
visit_intent = RECOMMENDED
poi_policy = RESOLVE

沈阳故宫
subject_role = REFERENCE
visit_intent = NOT_APPLICABLE
poi_policy = REFERENCE_ONLY
```

沈阳故宫：

- 可以保留为 Evidence；
- 可以用于说明北京故宫；
- 不进入 POI Review；
- 不出现在“附近值得去”；
- 不成为视频推荐 Place。

---

## 7.2 故宫比较视频

标题：

```text
北京故宫和沈阳故宫有什么区别
```

结果：

```text
北京故宫
subject_role = PRIMARY
visit_intent = NEUTRAL
poi_policy = RESOLVE

沈阳故宫
subject_role = PRIMARY
visit_intent = NEUTRAL
poi_policy = RESOLVE
```

两者均进入 POI。

因此：

> `COMPARISON_REFERENCE` 不能作为全局过滤规则。

角色必须相对于 ContentUnit 判断。

---

# 8. Semantic Travel Map v3

现有 Grounded Map 建议升级为：

```text
Semantic Travel Map
```

但不增加额外远程模型调用。

Ground Map 同一次模型调用直接输出：

```json
{
  "content_units": [],
  "entities": [],
  "relations": [],
  "claims": [],
  "warnings": []
}
```

---

# 9. Semantic Map Entity Schema

建议字段：

```json
{
  "entity_id": "ent_xxx",
  "raw_name": "妙峰山",
  "canonical_hint": "妙峰山",
  "aliases": [],
  "entity_type": "PLACE",
  "place_type": "SCENIC_AREA",

  "content_unit_id": "unit_01",

  "subject_role": "PRIMARY",
  "visit_intent": "RECOMMENDED",
  "poi_policy": "RESOLVE",

  "city_hint": "北京市",
  "province_hint": "北京市",
  "district_hint": "门头沟区",

  "segment_ids": [],
  "quote": "",
  "confidence": 0.0
}
```

---

# 10. Relations

支持：

```text
CONTAINS
NEARBY
RECOMMENDED_WITH
ROUTE_NEXT
SAME_THEME
COMPARED_WITH
ALTERNATIVE_TO
PART_OF
LOCATED_IN
```

注意：

```text
COMPARED_WITH
```

只是语义关系。

不能自动产生 POI Materialization。

---

# 11. Atomic Claims

替代目前过度压缩的 `section_facts`。

建议：

```json
{
  "claim_id": "claim_xxx",
  "content_unit_id": "unit_01",
  "subject_entity_ids": ["ent_xxx"],
  "claim_type": "HIGHLIGHT",
  "text": "作者认为中轴线是第一次游览故宫最值得优先看的部分。",
  "importance": "HIGH",
  "segment_ids": ["seg_xxx"],
  "supporting_quote": "..."
}
```

支持：

```text
HIGHLIGHT
RECOMMENDED_ITEM
BEST_TIME
BEST_SEASON
DURATION
PRICE
RESERVATION
QUEUE
TRANSPORT
WARNING
ROUTE
AUTHOR_OPINION
COMPARISON
OTHER
```

---

# 12. 不再使用固定“每 chunk 最多 4 个事实”

当前 Grounded Map 对 facts 压缩过强。

改成：

> Evidence-bound atomic claims，以事实完整性优先。

可以限制：

- 重复 Claim；
- 无信息 Claim；
- 没有 Evidence 的 Claim；

但不要用过低的固定数量硬截断。

---

# 13. 地点抽取两阶段策略

为了减少漏报，同时降低远程 Token：

## Pass A：Local High Recall Entity Spotting

目标：

```text
哪里可能是地点？
```

原则：

```text
宁可稍微多，不要漏
```

由本地模型执行。

---

## Pass B：Local Semantic Classification

针对 Pass A 的候选，判断：

```text
所属 ContentUnit
subject_role
visit_intent
poi_policy
place_type
aliases
region context
```

仍由本地模型执行。

---

## Remote Escalation

只有存在冲突 / 不确定的实体才发送远程。

---

# 14. Remote Escalation 触发规则

任何满足以下条件之一：

1. 本地修正了疑似地名 / 专名；
2. ASR 地名 Segment 置信度低；
3. Mention 同时具有推荐和比较信号；
4. ContentUnit 出现地域变化但没有明确转场；
5. 同一实体被分配到多个不兼容 ContentUnit；
6. CORE / PRIMARY 无法判断是 AREA 还是 PLACE；
7. 地域上下文与候选 POI 明显冲突；
8. Pass A 找到实体，但 Pass B 无法给出可靠角色；
9. ContentUnit validator 发现主题边界冲突；
10. Local 输出 JSON / Evidence Contract 不稳定。

---

# 15. Remote Escalation 输入范围

远程模型默认不得接收完整 Transcript。

只发送：

```text
Video title
ContentUnit summary
Target Segment
± 2~3 neighbor segments
Related entities
Region context
Current local hypothesis
```

目标：

```text
small context → high-value remote reasoning
```

---

# 16. Transcript Correction 模型策略

现有：

```text
correction_candidates()
```

已经可以筛选：

- 低置信 Segment；
- 损坏文本；
- 重复文本；
- Whisper 中可能包含地点、日期、价格、季节等内容；
- 邻近 Segment。

保留。

---

## 16.1 默认路由

```text
TRANSCRIPT_CORRECTION = LOCAL_FIRST
```

不是全量远程。

---

## 16.2 专名升级

在 `correct_transcript()` 内增加：

```text
GEO_TERM / PROPER_NOUN RISK
```

如果本地对疑似地名做了修改，例如：

```text
水路案 → 水陆庵
妙风山 → 妙峰山
额尔古那 → 额尔古纳
```

则将对应小范围 Segment 升级远程校验。

可以第一阶段先以内部分支实现，不必立即新增独立 Job Step。

---

# 17. 默认模型路由

最终建议：

```text
TRANSCRIPT_CORRECTION
= LOCAL_FIRST
  地名 / 专名高风险 → REMOTE escalation

GROUND_MAP / SEMANTIC_MAP
= LOCAL_FIRST
  歧义 → REMOTE escalation

ENTITY SPOTTING
= LOCAL_FIRST

SEMANTIC CLASSIFICATION
= LOCAL_FIRST
  低置信 / 冲突 → REMOTE escalation

EXTRACT_TRAVEL_FACTS
= 尽量 deterministic materialization
  不再重复模型提取

POI_QUERY_EXPANSION
= LOCAL_FIRST
  只有首次搜索失败时使用

POI_RESOLUTION
= deterministic

GENERATE_AI_NOTE
= REMOTE_FIRST

NOTE_REDUCE
= 尽量合并 / 删除

PLACE_KNOWLEDGE
= deterministic / LOCAL
```

---

# 18. 设置页要求

继续使用当前已有：

```text
AUTO
LOCAL_ONLY
LOCAL_FIRST
REMOTE_FIRST
REMOTE_ONLY
```

用户可以逐阶段覆盖。

系统默认采用本计划中的策略。

---

## 18.1 建议增加高层预设

```text
高质量
平衡
本地优先
自定义
```

### 高质量

地点高风险语义更积极升级远程。

### 平衡（建议默认）

本地扫描 + 远程歧义处理 + 远程最终笔记。

### 本地优先

只有必要情况远程。

### 自定义

完全使用现有 Stage Policy。

---

# 19. POI Resolver V3

禁止直接用 LLM 最终确认 POI。

完整链路：

```text
Semantic Entity
↓
POI Query Builder
↓
高德
↓
Candidate Ranking
↓
Deterministic Resolver
↓
AUTO_EXACT
AUTO_NORMALIZED
ADMIN_ANCHOR
REVIEW
UNRESOLVED
```

---

# 20. Resolver V3 Feature Vector

在现有基础增加：

```text
name_exact
name_contains
normalized_token_overlap
alias_match

explicit_city_match
unit_city_match
province_match
district_match

category_match

nearby_anchor_match
distance_to_unit_cluster

query_consensus_count
candidate_gap

prior_confirmation_match

cross_city_conflict
chain_risk
category_conflict
reference_only
coordinate_valid
```

---

# 21. AUTO_EXACT

适用：

```text
故宫博物院
→ 故宫博物院
```

要求：

```text
名称强匹配
+ 地域一致
+ 类型一致
+ 候选唯一或明显领先
+ 无 hard risk
```

---

# 22. AUTO_NORMALIZED

处理：

```text
妙峰山
→ 妙峰山森林公园

额尔古纳湿地
→ 额尔古纳湿地景区

东方明珠
→ 东方明珠广播电视塔

国博
→ 中国国家博物馆
```

允许：

```text
简称 → 官方全称
俗称 → 官方名
核心名称 → 景区 / 森林公园 / 博物馆等完整名
```

要求：

```text
核心名称覆盖高
+ ContentUnit 地域一致
+ 类型兼容
+ Top1 明显领先 Top2
+ 无跨城市冲突
+ 非连锁风险
```

---

# 23. 行政区域不能当普通 Place

用户说：

```text
天津
```

不应该在知识库里被建成：

```text
天津市人民政府
```

作为旅游地点。

正确结构：

```text
Destination / AREA
canonical_name = 天津市
```

地图需要落点时：

```text
ADMIN_ANCHOR
```

优先使用：

- 行政区中心；
- 行政区 centroid；
- provider 行政区域结果。

如果现阶段 provider 不支持，再允许：

```text
天津市人民政府
```

作为：

```text
representative_anchor
```

但不能把政府 POI 当成用户视频推荐 Place。

---

# 24. Destination / Area 数据结构

新增独立区域模型。

建议：

```text
Destination
```

字段：

```text
id
name
canonical_name
scope_type

country
province
city
district
adcode

center_latitude
center_longitude

external_provider
external_area_id

metadata_json
created_at
updated_at
```

`scope_type`：

```text
COUNTRY
PROVINCE
CITY
PREFECTURE
COUNTY
DISTRICT
SCENIC_REGION
TOWN
OTHER
```

---

# 25. DestinationPlaceLink

用于：

```text
北京
├ 故宫
├ 天坛
└ 颐和园
```

建议：

```text
destination_id
place_id
relation_type
source_id
video_asset_id
content_unit_id
segment_ids_json
confidence
metadata_json
```

relation：

```text
RECOMMENDED_IN
NEARBY
PART_OF
ROUTE_STOP
```

比较地点不能生成 `RECOMMENDED_IN`。

---

# 26. 不强制把所有关系持久化为 Place Relation

例如：

```text
北京故宫 COMPARED_WITH 沈阳故宫
```

如果沈阳故宫只是参考：

- 保存在 Semantic Artifact；
- 保存在 Claim Evidence；
- 不必创建 Place；
- 不必创建永久 PlaceRelation。

只有目标地点已经因其他来源独立成为 Place，且产品未来需要展示比较关系时，再考虑持久化。

---

# 27. PlaceMention 调整

如果继续使用 `PlaceMention`：

新增或放入结构化 metadata：

```text
content_unit_id
subject_role
visit_intent
poi_policy
semantic_confidence
```

推荐最终变成正式字段，而不是长期依赖 `metadata_json`。

---

# 28. Materialization Gate

核心规则：

```python
if poi_policy not in {"RESOLVE", "AREA_RESOLVE"}:
    do_not_materialize_to_poi_queue()
```

这样从根源上阻止：

```text
REFERENCE
CONTEXT
NEGATIVE
```

进入 POI Resolver。

---

# 29. POI Review API

当前：

```text
REVIEW / UNRESOLVED
```

会进入 `/api/travel/place-reviews`。

修改后增加硬过滤：

```text
poi_policy == RESOLVE
```

或 Area 的专门处理。

Reference Entity 永远不能出现在 POI Review。

---

# 30. 连锁店继续采用严格策略

以下：

```text
喜茶
海底捞
四季民福
酒店
咖啡连锁
```

即使名称包含很强，也不能使用普通 `AUTO_NORMALIZED`。

需要：

```text
branch address
district
mall
street
nearby landmark
```

等证据。

否则：

```text
REVIEW
```

现有：

```text
CHAIN_BRANCH_AMBIGUITY
```

保留并加强。

---

# 31. 视频笔记新结构

AI Note 不再强制：

```text
PLACE / AREA / ROUTE
```

三类章节覆盖所有视频。

改为基于 ContentUnit。

输出：

```json
{
  "overview": "...",
  "units": [
    {
      "content_unit_id": "...",
      "unit_type": "AREA_GUIDE",
      "heading": "...",
      "thesis": "...",
      "summary": "...",
      "bullets": [],
      "entity_ids": [],
      "claim_ids": [],
      "segment_ids": []
    }
  ]
}
```

---

# 32. 根据 unit_type 自适应渲染

## AREA_GUIDE

```text
北京
故宫
天坛
颐和园
```

---

## PLACE_GUIDE

```text
妙峰山
核心看点
路线
最佳时间
周边地点
```

---

## ROUTE

```text
Day 1
Day 2
Day 3
```

---

## CATEGORY_COMPARE

```text
故宫 vs 沈阳故宫
规模
建筑
游览方式
差异
```

---

## THEME

```text
秋季湿地推荐
1.
2.
3.
```

---

# 33. 信息价值排序

Prompt 明确要求优先：

```text
具体特色
作者明确推荐理由
核心体验
路线
适合月份 / 季节 / 时间
游览时长
价格
预约
排队
交通
注意事项
推荐菜
比较结论
```

低优先：

```text
一般性情绪
重复评价
无具体信息的赞美
```

---

# 34. LOW_INFORMATION_CONTENT

以下单独出现时视为低信息：

```text
景色优美
非常值得一去
体验很好
很有特色
非常推荐
环境不错
值得打卡
```

如果 bullet 只有这类内容且没有：

- 地点；
- 原因；
- 特征；
- 数字；
- 时间；
- 行为建议；

则不允许进入最终 bullets。

---

# 35. Note Quality Gate

生成后增加确定性 lint：

检查：

```text
重复 bullet
heading / thesis 重复
泛化 bullet
无 Evidence Claim
无实际信息的 section
同一事实重复出现
Reference 地点错误变成推荐地点
```

不建议新增第二次远程“审稿”。

质量检查优先 deterministic。

---

# 36. 保留模型生成 heading

当前 `_ground_section()` 会用 Place 名覆盖模型生成 heading。

需要调整。

分离：

```text
anchor_entity
```

和：

```text
heading
```

例如：

```text
anchor_entity = 故宫
heading = 第一次去故宫最值得看的中轴线
```

不要再强制：

```text
heading = 故宫
```

---

# 37. NOTE_REDUCE

改造后优先尝试删除 / 合并。

目标：

```text
Transcript
↓
Local Semantic Map
↓
Atomic Claims
↓
Remote Final Synthesis × 1
```

避免：

```text
总结
→ 再总结
→ 再压缩
```

---

# 38. Place Detail 页面扩展

当前已有：

```text
地点知识
推荐原因
截图事实
Visit Windows
个人笔记
历史
```

增加：

```text
所属目的地
同目的地下值得去
周边可顺路
相关来源视频
相关主题内容
```

---

# 39. Place Detail 不显示无关 Comparison Reference

北京故宫详情页可以使用：

```text
“视频中曾与沈阳故宫进行规模比较”
```

作为一个 Claim（如果有信息价值）。

但沈阳故宫不能因为这句话出现在：

```text
北京周边推荐
```

里面。

---

# 40. Destination 页面 / 区域知识

后续可增加：

```text
北京市
├ 推荐地点
├ 来源视频
├ 主题
├ 季节
└ 地图
```

这正是用户希望的：

```text
北京市
→ 故宫
→ 颐和园
→ 圆明园
→ 长城
→ 天坛
```

---

# 41. 通用性保护规则

必须明确写入 Prompt / Test：

> 不允许假设视频存在城市核心地点。
> 不允许假设一个视频只有一个 ContentUnit。
> 不允许假设每个 ContentUnit 只有一个 Anchor。
> 不允许假设所有被提到的地点都是推荐地点。
> 不允许假设比较对象都应该过滤。
> 不允许为了建立地点树而改变原视频内容结构。

---

# 42. Token 优化总策略

最终模型链路：

```text
Transcript
↓
确定性质量筛选
↓
Local Entity Spotting
↓
Local Semantic Classification
↓
Deterministic Validation
↓
仅歧义片段 Remote Escalation
↓
Semantic Map
↓
Deterministic POI
↓
Remote Final Note × 1
```

---

# 43. 避免的高 Token 设计

禁止：

```text
完整 Transcript → Remote Correction
完整 Transcript → Remote Ground Map
完整 Transcript → Remote Place Extraction
完整 Transcript → Remote Note
Note → Remote Reduce
```

---

# 44. Cache / Version

修改 Semantic Map schema 后：

```text
MAP_PROMPT_VERSION
```

从当前：

```text
grounded-map-v2
```

升级：

```text
semantic-map-v3
```

确保旧缓存不会与新 schema 混用。

---

# 45. Prompt Contract 更新

修改：

```text
backend/src/zhijian/services/video_support.py
PROMPT_CORE_CONTRACTS
```

增加：

```text
ContentUnit
subject_role
visit_intent
poi_policy
Atomic Claim
Evidence
```

并同步：

```text
grounded_map
travel_place_extraction
video_note_summary
```

---

# 46. 关键代码修改清单

## Backend

### Prompt

```text
backend/src/zhijian/prompts/grounded_map.md
backend/src/zhijian/prompts/travel_place_extraction.md
backend/src/zhijian/prompts/video_note.md
backend/src/zhijian/prompts/transcript_correction.md
```

---

### AI

```text
backend/src/zhijian/ai/stages.py
backend/src/zhijian/ai/cost_router.py
backend/src/zhijian/ai/stage_decision.py
backend/src/zhijian/ai/transcript_quality.py
```

---

### Service

```text
backend/src/zhijian/services/grounded_map.py
backend/src/zhijian/services/video_support.py
backend/src/zhijian/services/video_pipeline.py
backend/src/zhijian/services/place_knowledge.py
```

---

### DB

```text
backend/src/zhijian/db/models.py
```

以及 Alembic migration。

---

### API

```text
backend/src/zhijian/api/router.py
backend/src/zhijian/api/video_notes.py
```

---

## Frontend

```text
frontend/src/features/video/VideoNotesPage.tsx
frontend/src/features/map/PlaceDetailPage.tsx
frontend/src/features/map/PlaceReviewsPage.tsx
frontend/src/features/places/PlaceReviewCard.tsx
frontend/src/features/settings/SettingsPage.tsx
frontend/src/lib/types.ts
```

---

# 47. 实施阶段

---

# Phase 0：冻结基线

在任何改动前记录：

```text
现有 Golden Sample 结果
POI candidate recall@1
POI candidate recall@3
auto confirm precision
auto confirm rate
review rate
wrong confirm count
视频处理总 Token
远程输入 Token
远程输出 Token
本地输入/输出 Token
各 AI stage 调用次数
```

不得先修改测试预期再实施。

---

# Phase 1：Semantic Schema

实现：

```text
ContentUnit
Entity semantic fields
AtomicClaim
Relation
```

优先先存在：

```text
GroundedMapArtifact / Semantic Artifact JSON
```

中。

第一阶段不需要立即全部落数据库。

---

## Phase 1 验收

Fixture 必须覆盖：

```text
一个城市多个景点
一个视频多个城市
单景区
榜单
路线
比较
主题
Vlog
探店
地点只是背景
```

ContentUnit 结构必须和人工标注一致。

---

# Phase 2：POI Materialization Gate

实现：

```text
poi_policy
```

只有：

```text
RESOLVE
AREA_RESOLVE
```

才能进入 POI。

`REFERENCE_ONLY` / `SKIP` 永远不能进入 Place Review。

---

## Phase 2 验收

Golden Fixture：

```text
“北京故宫比沈阳故宫大”
```

北京故宫：

```text
RESOLVE
```

沈阳故宫：

```text
REFERENCE_ONLY
```

人工 POI Review 中：

```text
沈阳故宫 = 0
```

---

# Phase 3：ContentUnit / Multi-Core

加入：

```text
content_unit_id
```

让：

```text
北京
天津
承德
```

在同一个视频中形成独立 Unit。

---

## Phase 3 验收

一个三城市视频：

```text
3 个核心 Unit
```

不得：

```text
串城市
串子地点
串 Region Context
```

---

# Phase 4：Resolver V3

在现有 `_poi_score()` 基础上增强。

增加：

```text
normalized_token_overlap
unit_city_match
distance_to_unit_cluster
query_consensus
admin_anchor
```

并定义：

```text
AUTO_EXACT
AUTO_NORMALIZED
ADMIN_ANCHOR
REVIEW
UNRESOLVED
```

---

# Phase 5：行政区域模型

新增：

```text
Destination
DestinationPlaceLink
```

实现：

```text
天津
→ Destination 天津市
```

而不是：

```text
Place 天津市人民政府
```

政府 POI 仅允许作为代表 Anchor fallback。

---

# Phase 6：本地 / 远程升级路由

默认：

```text
Local Full Scan
Remote Escalation
Remote Final Synthesis
```

实现 Remote Escalation 小上下文输入。

---

# Phase 7：视频笔记改造

改成：

```text
Semantic Map
+
Atomic Claims
→ 一次 Remote Final Note
```

弱化 / 删除 `NOTE_REDUCE`。

---

# Phase 8：Destination / Place Detail

增加：

```text
所属目的地
相关地点
同主题内容
来源视频
```

---

# Phase 9：回归 / Token Benchmark

比较改造前后：

```text
地点 Recall
POI Precision
Review Rate
Wrong Confirm
Remote Token
总延迟
Note Quality
```

---

# 48. Golden Fixture 新增

必须新增以下测试。

## G-001 地区攻略

```text
北京
故宫
天坛
颐和园
```

---

## G-002 多核心地区

```text
北京
天津
承德
```

---

## G-003 单景区

```text
黄山攻略
```

---

## G-004 跨地域榜单

```text
国内 10 个湿地
```

---

## G-005 比较作为参考

```text
北京故宫比沈阳故宫大
```

预期：

```text
北京故宫 RESOLVE
沈阳故宫 REFERENCE_ONLY
```

---

## G-006 比较视频

```text
北京故宫 vs 沈阳故宫
```

预期：

```text
两者均 RESOLVE
```

---

## G-007 近似 POI

```text
妙峰山
→ 妙峰山森林公园
```

预期：

```text
AUTO_NORMALIZED
```

---

## G-008 近似 POI

```text
额尔古纳湿地
→ 额尔古纳湿地景区
```

预期：

```text
AUTO_NORMALIZED
```

---

## G-009 行政区

```text
天津
```

预期：

```text
Destination 天津市
```

不得：

```text
旅游 Place = 天津市人民政府
```

---

## G-010 跨城市重名

```text
凤凰山
```

无地域上下文：

```text
REVIEW
```

---

## G-011 连锁店

```text
喜茶
```

无分店上下文：

```text
REVIEW
```

---

## G-012 Vlog

大量经过地点中只有少部分被作者推荐。

只有 Actionable 地点进入 POI。

---

# 49. 核心质量指标

---

## 49.1 Actionable Place Recall

定义：

```text
人工标注应该进入 POI 的地点
```

要求：

```text
Recall = 100%
```

针对冻结 Golden Fixture。

---

## 49.2 Reference Leakage

定义：

```text
REFERENCE / CONTEXT / NOT_APPLICABLE
错误进入 POI Queue
```

要求：

```text
0
```

---

## 49.3 Candidate Recall@3

沿用现有：

```text
candidate_recall_at_3 = 100%
```

---

## 49.4 Wrong Auto Confirm

要求：

```text
wrong_confirm_count = 0
```

---

## 49.5 Auto Confirm Precision

要求：

```text
auto_confirm_precision = 100%
```

---

# 50. Auto Eligible Coverage

为了避免“全部 Review 就算安全”。

新增：

```text
AUTO_ELIGIBLE fixture
```

例如：

```text
妙峰山
额尔古纳湿地
国博
东方明珠
行政区域
```

目标：

```text
auto_confirm_rate >= 90%
wrong_confirm_count = 0
```

该指标仅针对专门的 `AUTO_ELIGIBLE` 集合，不应用于所有 POI。

---

# 51. MUST_REVIEW Fixture

例如：

```text
喜茶
凤凰山（无地域）
老街（无地域）
同城多个同名分店
```

要求：

```text
auto_confirm_count = 0
```

---

# 52. ContentUnit 验收

新增：

```text
unit_count_accuracy
entity_unit_assignment_accuracy
unit_boundary_error_count
cross_unit_location_leak_count
```

冻结 Golden Fixture：

```text
unit_boundary_error_count = 0
cross_unit_location_leak_count = 0
```

---

# 53. Note Quality 验收

人工 + deterministic lint。

要求：

1. 所有关键结论具有 Evidence；
2. 不新增原文没有的事实；
3. 不把 Reference 地点写成推荐地点；
4. 不出现纯泛化 bullet；
5. 同一事实不得重复；
6. 地点推荐必须包含至少一个具体理由或实用信息；
7. 地区 / 榜单 / 路线 / 比较视频使用合适结构；
8. heading 不再全部退化成 POI 名。

---

# 54. Token 验收

记录：

```text
remote_prompt_tokens
remote_completion_tokens
local_prompt_tokens
local_completion_tokens
remote_call_count
```

以 Golden Video Fixture 对比改造前后。

目标不是凭空设绝对值，而是要求：

```text
Remote Prompt Token 总量显著下降
```

并保证：

```text
质量指标不下降
```

建议首个工程目标：

```text
远程输入 Token 相对基线减少 >= 40%
```

但此指标必须在真实 Fixture 基线建立后冻结。

---

# 55. 性能原则

不得为了减少 Token 造成：

```text
模型调用次数暴增
```

因此优先：

```text
一次 Local Semantic Map
```

而不是：

```text
Local 地点抽取
Local 主题判断
Local Facts
Local Role
Local Relation
```

全部做成五次独立大调用。

可以逻辑上分 Pass，但应尽可能：

- 同一个本地上下文批处理；
- 使用缓存；
- 复用 Semantic Map Artifact。

---

# 56. 错误处理

Remote Escalation 失败：

```text
明确实体
→ 使用 Local 结果继续

歧义实体
→ REVIEW / PARTIAL
```

禁止：

```text
远程失败
→ 自动把低置信本地结果 CONFIRMED
```

---

# 57. 可观测性

新增指标：

```text
semantic.entities.total
semantic.entities.actionable
semantic.entities.reference
semantic.units.count

poi.skipped.reference
poi.resolve.requested
poi.auto_exact
poi.auto_normalized
poi.review
poi.unresolved

ai.remote_escalation.count
ai.remote_escalation.reason

note.low_information_removed
```

方便后续判断：

> Review 变少究竟是 Resolver 变强，还是系统漏抽地点。

---

# 58. 向后兼容

旧数据：

```text
PlaceMention 无 semantic role
```

处理：

```text
legacy records
→ poi_policy = LEGACY
```

不要批量自动重新判定。

新任务使用新 Schema。

旧视频需要重新处理时，通过 Replay / Force Regenerate 生成新 Semantic Artifact。

---

# 59. Migration 原则

DB migration：

1. 可为空字段先上线；
2. 后端兼容旧数据；
3. 新 pipeline 写新字段；
4. UI 对字段缺失做 legacy fallback；
5. Golden Test 通过后再逐步收紧 NOT NULL。

---

# 60. 不应做的事情

本次改造禁止：

1. 把所有地点阶段都改成远程模型；
2. 新增一个远程模型专门做 POI 最终确认；
3. 把所有出现的城市都建成 Destination；
4. 把所有比较地点都过滤；
5. 强制所有视频生成“地区 → 景点”树；
6. 为了 Review 少而牺牲 Recall；
7. 为了 Recall 高而把 Reference 全送 POI；
8. 使用 LLM 再做一次全量 Note Quality Review；
9. 用政府 POI 替代行政区域实体；
10. 取消现有 Evidence / Segment grounding。

---

# 61. 推荐开发顺序

严格按：

```text
1. Golden Fixture
2. Semantic Schema
3. Role / POI Gate
4. Multi ContentUnit
5. Resolver V3
6. Destination
7. Local / Remote Escalation
8. Note Quality
9. Place Detail
10. Token Benchmark
```

原因：

> 先解决“哪些地点根本不该进入 POI”，再解决“如何更智能地自动确认 POI”。

否则会出现：

```text
Resolver 更强
↓
错误的 Comparison Reference
反而被更快自动确认
```

---

# 62. Phase Definition of Done

## Phase 1

- Semantic Map v3 Schema 完成；
- Fixture 可稳定输出；
- Evidence Contract 不下降。

## Phase 2

- Reference 不再进入 POI；
- Review API 正确过滤。

## Phase 3

- 一个视频支持多个 ContentUnit；
- 不串 Region Context。

## Phase 4

- AUTO_NORMALIZED 完成；
- Wrong Confirm = 0。

## Phase 5

- Area / Destination 与 Place 解耦。

## Phase 6

- Local Full Scan + Remote Escalation 生效；
- UI 可覆盖 Stage Policy。

## Phase 7

- 新视频笔记没有明显摘要再摘要问题；
- 低信息 bullet 显著减少。

## Phase 8

- Place / Destination 页面支持体系化阅读。

## Phase 9

- 完成质量 + Token + 延迟基准对比。

---

# 63. 最终目标架构

```text
                  ┌─────────────────────┐
                  │ Transcript / ASR    │
                  └──────────┬──────────┘
                             ↓
              Deterministic Quality Gate
                             ↓
                Local Transcript Cleanup
                             ↓
                 Proper-Noun Risk Gate
                    │                 │
                    │ clear           │ risky
                    ↓                 ↓
                  keep        Remote small-context
                    └────────┬────────┘
                             ↓
                    Local Semantic Map
         ┌───────────────────┼────────────────────┐
         │                   │                    │
     ContentUnit          Entities             Claims
         │                   │                    │
         └───────────────────┼────────────────────┘
                             ↓
                  Deterministic Validator
                             ↓
               Ambiguity / Conflict Gate
                    │                 │
                    │ clear           │ ambiguous
                    ↓                 ↓
                  keep         Remote Escalation
                    └────────┬────────┘
                             ↓
                    Semantic Artifact
                             ↓
              ┌──────────────┴───────────────┐
              │                              │
      poi_policy=RESOLVE             REFERENCE / CONTEXT
              │                              │
              ↓                              ↓
        AMap POI Search                Evidence only
              ↓
        Resolver V3
              ↓
 AUTO_EXACT / AUTO_NORMALIZED / REVIEW
              ↓
     Place / Destination Knowledge
              ↓
      Remote Final Note Synthesis
              ↓
      Video Note / Place Detail / Map
```

---

# 64. 最终产品行为示例

输入视频：

```text
“这次讲北京和天津。
北京我最推荐故宫和颐和园。
故宫比沈阳故宫规模大很多。
颐和园如果秋天去体验更好。
第二站天津，推荐五大道。
如果时间多可以去天津之眼。”
```

预期 Semantic Map：

```text
ContentUnit 1
type = AREA_GUIDE
anchor = 北京市

故宫
PRIMARY
RECOMMENDED
RESOLVE

颐和园
SECONDARY
RECOMMENDED
RESOLVE

沈阳故宫
REFERENCE
NOT_APPLICABLE
REFERENCE_ONLY

ContentUnit 2
type = AREA_GUIDE
anchor = 天津市

五大道
PRIMARY
RECOMMENDED
RESOLVE

天津之眼
SECONDARY
OPTIONAL
RESOLVE
```

最终：

```text
POI Queue：
故宫
颐和园
五大道
天津之眼

不进入 POI Queue：
沈阳故宫
```

Destination：

```text
北京
├ 故宫
└ 颐和园

天津
├ 五大道
└ 天津之眼
```

视频笔记：

```text
北京
- 故宫：作者重点推荐；……
- 颐和园：秋季体验更好；……

天津
- 五大道：作者主要推荐地点。
- 天津之眼：时间充裕时可作为可选地点。
```

没有：

```text
“沈阳也是值得探索的城市”
```

之类模型自行扩展内容。

---

# 65. Agent 执行要求

Codex / Agent 开始实施前：

1. 读取本文件；
2. 只补充阅读涉及阶段的代码；
3. 不对整个仓库无差别扫描；
4. 先运行现有相关测试；
5. 建立 / 冻结 baseline；
6. 按 Phase 逐步实施；
7. 每个 Phase 独立通过测试后再继续；
8. 不得一次性重写整个 video pipeline；
9. 不得删除现有兼容逻辑后再补；
10. 每阶段更新对应 dev docs。

---

# 66. 最终交付物

完成本计划后至少应包含：

```text
Semantic Map v3
ContentUnit
Semantic Entity Role
Atomic Claim
POI Materialization Gate
Resolver V3
AUTO_NORMALIZED
Destination / Area
Local → Remote Escalation
Adaptive Video Note
Note Quality Gate
Expanded Golden Fixture
POI Benchmark v2
Token Benchmark
Migration
API / UI Updates
Updated Dev Docs
```

---

# 67. 最终验收总表

| 项目 | 必须达到 |
|---|---:|
| Actionable Place Recall | 100%（冻结 Fixture） |
| Reference → POI Leakage | 0 |
| Candidate Recall@3 | 100% |
| Wrong Auto Confirm | 0 |
| Auto Confirm Precision | 100% |
| AUTO_ELIGIBLE Auto Confirm Rate | ≥ 90% |
| MUST_REVIEW 自动确认 | 0 |
| ContentUnit 跨单元串地点 | 0 |
| Evidence 可回溯 | 100% |
| 最终 Note 无 unsupported claim | 100% |
| 纯泛化 Bullet | 0 |
| 远程 Token | 相比基线显著下降 |
| 用户自定义模型路由 | 必须保留 |
| 通用视频类型支持 | 不得退化 |

---

# 68. 实施结论

本次改造的核心不是单独“优化 Prompt”，也不是简单“提高 POI 模糊匹配”。

真正需要完成的是：

```text
从：
地点提到
→ 全部 POI
→ 人工清理

升级为：

视频内容结构
→ ContentUnit
→ 地点语义角色
→ Actionable Gate
→ 智能 Resolver
→ 体系化知识
```

同时模型策略从：

```text
所有复杂内容依赖远程
```

变为：

```text
本地模型处理完整、高吞吐内容
+
确定性代码负责验证与最终 POI 判定
+
远程模型只处理歧义和最终高质量写作
```

这样才能同时满足：

- 通用性；
- 地点高召回；
- POI 低误报；
- 少人工确认；
- 更智能自动匹配；
- 多核心地点；
- 体系化内容组织；
- 视频笔记质量；
- Token 成本控制；
- 后续可扩展性。
