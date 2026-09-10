# 视频工作流质量总优化计划

> 仓库：`ThunStorm/do-not-litter`  
> 分支：`codex/mac-mini-implementation`  
> 日期：2026-09-10  
> 用途：Codex / Agent 可直接执行  
> 合并来源：视频字幕与音画一致性优化方案 + 视频笔记地点化/地点召回/Evidence/审核优化方案

---

## 0. 总目标

本轮集中解决四类已确认问题：

1. 视频笔记产生大量非地点主题的一级段落，例如“100 出头就能住到带院子的民宿”；
2. 围绕城市快速介绍多个周边景点时，地点识别不完整；
3. Bilibili 平台 AI 字幕错配后污染 Transcript，并进一步污染 Note、PlaceMention 和截图说明；
4. 地点只能在 `/place-reviews` 下确认，且缺少原视频笔记、时间码、转写上下文，判断成本高。

统一目标链路：

```text
Video
↓
Subtitle Source Validation
↓
Authoritative Transcript
↓
Independent High-Recall Place Extraction
↓
Evidence Validation / Merge
↓
Place-Anchored Video Note
↓
POI Resolution
↓
Inline Review + Global Review
↓
Map / Place Knowledge
```

核心原则：

> 先保证输入是真的，再保证地点找全，再保证每个结论有原文 Evidence，最后降低人工审核成本。

---

# 1. 已确认根因

## 1.1 非地点内容被提升为一级章节

当前 `video_note.md` 对 `heading` 的主要要求是“具体主题”，没有要求一级 Section 必须以地点、区域或路线为锚点。

因此类似：

```text
100 出头就能住到带院子的民宿
交通非常方便
这里真的太出片了
建议早点来
```

在当前 Prompt 下都有机会成为一级标题。

当前服务端也主要检查 Section 是否引用合法 `segment_ids`，没有充分验证：

```text
heading 是否地点化
summary / bullets 是否被这些 Segment 真实支撑
```

结论：

```text
Prompt 目标不够明确
+
Section 缺少语义类型
+
Evidence Gate 不足
```

共同导致问题。

---

## 1.2 地点召回被视频摘要质量绑架

当前 `EXTRACT_TRAVEL_FACTS` 在默认非 `REMOTE_ONLY` 路径下可复用：

```text
AINoteVersion.map_facts_json
```

等价于：

```text
完整 Transcript
→ 视频摘要
→ 摘要阶段保留下来的地点
→ PlaceMention
```

而正确关系应是：

```text
完整 Transcript
→ 独立高召回地点抽取
→ PlaceMention
```

因此：

> 总结阶段一旦忽略快速提到的地点，后续地点抽取没有第二次机会补回来。

同时，当前 `_transcript_context()` 达到字符限制后会 `break`。长视频若一次性执行地点抽取，后半段可能完全没有进入模型。

---

## 1.3 Bilibili AI 字幕错配污染已得到实测支持

已确认至少两个真实样本中：

```text
BV / CID / Source / VideoAsset 绑定正确
但 Bilibili ai-zh 字幕内容与实际音画无关
```

典型表现：

```text
九月旅行目的地推荐
→ “露丝结束 20 年牢狱后获释……”
```

另一个旅行景观视频则出现兴趣、才华、个人成长自述。

其中一个样本还存在：

```text
视频约 530 秒
字幕末段约 838.5 秒
```

说明不仅语义错配，时间轴也明显异常。

高置信根因：

```text
错误 / 失效的 Bilibili AI 字幕轨
+
应用缺少“不可信平台字幕”的完整性门禁
```

另有 `/x/player/v2` 与规格中的 `/x/player/wbi/v2` 契约漂移，需要修正和审计，但不能在现有证据下认定它是唯一事故根因。

---

## 1.4 当前字幕质量门禁不足

现有字幕质量检查主要关注：

```text
空文本
乱码
相邻重复
低 confidence
```

但“内容完全错误、文字却很流畅”的平台字幕通常不会触发这些条件。

因此平台字幕可能：

```text
接口成功
+
正文非空
→ materialize_transcript()
→ 跳过 DOWNLOAD_AUDIO / ASR
```

然后一路污染下游。

---

## 1.5 Note Map/Reduce 会放大错误

当前 Map 阶段产出的 `section_facts`，主要依赖合法 Segment ID 进入后续流程。

Reduce 又会把这些模型产物作为“按时间块验证的 SectionFacts”继续总结，而不是始终携带原始 Evidence。

错误可能变成：

```text
错误字幕
↓
错误 Map Fact
↓
被当作已验证事实
↓
Reduce 再组织
↓
更完整、更像真的错误笔记
```

---

## 1.6 地点审核所需数据其实已经大部分存在

`PlaceMention` 已有：

```text
quote
segment_ids_json
reason
confidence
city_hint
province_hint
video_asset_id
```

视频笔记 API 也已经可以得到：

```text
Section
时间码
Transcript
地点与章节映射
截图
```

因此审核优化不需要重做底层数据采集，重点是：

```text
Review Context API
+
统一 PlaceReviewCard
+
视频笔记页内直接确认
```

---

# 2. 冻结产品规则

## 2.1 一级视频笔记必须地点化

一级目录仅允许：

```text
PLACE
AREA
ROUTE
```

示例：

```text
鸡足山
沙溪古镇
大理周边｜沙溪・诺邓・巍山
古城 → 苍山 → 洱海
```

以下信息不得成为一级 Heading：

```text
100 出头就能住到带院子的民宿
交通非常方便
这里真的太出片了
建议早点来
性价比很高
```

只能：

```text
挂到相关地点 Section
或
进入 supplemental_facts
```

---

## 2.2 地点抽取以召回为优先

目标不是“只找最重要地点”，而是：

```text
所有明确提到、可落地图的地点候选
```

即使：

```text
只出现一次
说得很快
只有一句
没有推荐理由
同一句里出现多个地点
```

也应先进入候选，再由 Evidence、AMap 和用户审核完成精确化。

---

## 2.3 没有原文 Evidence，不生成正式事实

以下信息必须可追溯到：

```text
segment_id
+
exact quote
+
timecode
```

包括：

```text
地点
价格
推荐菜
核心看点
月份 / 季节
排队
适合人群
作者态度
注意事项
```

---

## 2.4 平台 AI 字幕默认不可信

字幕信任分级：

| 字幕类型 | 状态 | P0 行为 |
|---|---|---|
| 人工中文字幕 | `TRUSTED_PLATFORM` | 通过结构/时间轴 Gate 后可直通 |
| Bilibili AI / 机器字幕 | `UNVERIFIED_GENERATED` | P0 不直接作为权威 Transcript |
| 其他语言字幕 | `UNVERIFIED_OTHER` | 作为权威输入前必须验证 |
| 本地 Whisper ASR | `LOCAL_ASR` | AI 字幕异常时的权威回退 |

不得继续使用：

```text
source_kind 不含 ASR
≈
高质量平台字幕
```

这种隐式判断。

---

# 3. 目标 Pipeline

调整为：

```text
VALIDATE_LINK
↓
FETCH_METADATA
↓
FETCH_SUBTITLE
↓
VALIDATE_SUBTITLE_SOURCE          # new
↓
必要时 DOWNLOAD_AUDIO
↓
ASR
↓
NORMALIZE_TRANSCRIPT
↓
VALIDATE_TRANSCRIPT              # new hard gate
↓
CORRECT_TRANSCRIPT
↓
EXTRACT_TRAVEL_FACTS             # 独立完整扫描
↓
VALIDATE / MERGE PLACE CANDIDATES
↓
GENERATE_AI_NOTE                 # 地点驱动 + Evidence
↓
RESOLVE_POI
↓
BUILD_PLACE_NOTES
↓
PLAN_SCREENSHOTS
↓
DOWNLOAD_VIDEO_FOR_FRAMES
↓
EXTRACT_SCREENSHOTS
↓
MATERIALIZE
```

关键语义：

```text
EXTRACT_TRAVEL_FACTS.execution_mode
```

以后只表示：

```text
本地 / 远程 Provider 路由
```

不得再决定：

```text
是否真正执行地点抽取
```

---

# 4. WP0 — 先冻结失败 Fixture

优先更新：

```text
dev docs/benchmark/video-workflow-golden-v1.json
backend/tests/test_video_notes.py
```

增加以下失败样本。

### Case A：旅行标题 + “露丝出狱”错误字幕

Expected：

```text
平台 AI 字幕不得进入正式 Note
必须 fallback ASR
```

### Case B：旅行景观标题 + 兴趣/成长类错误字幕

Expected 同上。

### Case C：时间轴异常

```text
duration = 530s
last subtitle end ≈ 838.5s
```

Expected：

```text
TIMELINE_INVALID
→ fallback ASR
```

### Case D：快速多地点

例如：

```text
来到 X 城以后，
周边可以去 A、B、C，
D 有时间也值得看，
最后去 E 吃饭。
```

Expected：

```text
A/B/C/D/E 全部进入候选
```

### Case E：长上下文后半段地点

构造：

```text
前 12000+ chars 无目标地点
后半段出现 5 个明确地点
```

Expected：

```text
5 个全部召回
```

### Case F：非地点事实

```text
这边一百出头就能住到带院子的民宿，性价比挺高。
```

Expected：

```text
不能产生 Primary Section
可进入 supplemental fact
```

---

# 5. WP1 — 字幕来源、轨道与 Endpoint 审计

涉及：

```text
backend/src/zhijian/resolvers/video/bilibili.py
backend/src/zhijian/services/video_pipeline.py
backend/src/zhijian/services/external_audit.py   # 必要时
```

`SubtitleTrack` 增加：

```text
track_id
language
language_doc
is_generated
endpoint
```

规范 `Transcript.source_kind`：

```text
BILIBILI_HUMAN_SUBTITLE
BILIBILI_AI_SUBTITLE
WHISPER_CPP_ASR
```

修正并审计：

```text
/x/player/wbi/v2
```

如需兼容保留：

```text
/x/player/v2
```

则必须记录实际 Endpoint，并且其返回的 AI 字幕仍走 `UNVERIFIED_GENERATED` 分支。

---

# 6. WP2 — P0 止损：AI 字幕默认走 ASR

P0 不引入复杂相似度算法。

处理：

```text
人工中文字幕
→ structure / timeline gate
→ 通过后可直接 materialize

AI 字幕
→ 记录 Track / Endpoint / Hash
→ 不物化为唯一权威 Transcript
→ DOWNLOAD_AUDIO
→ Whisper.cpp ASR
→ LOCAL_ASR Transcript
```

原则：

```text
正确性 > 本地处理时间
```

---

# 7. WP3 — Transcript Validation Hard Gate

新增：

```text
backend/src/zhijian/services/transcript_validation.py
```

建议函数：

```python
assess_transcript_quality(...)
```

返回：

```json
{
  "status": "PASS|WARN|SUSPECT",
  "validation_status": "TRUSTED_PLATFORM|VERIFIED_GENERATED|LOCAL_ASR|PLATFORM_SUBTITLE_MISMATCH",
  "reasons": [],
  "metrics": {
    "timeline_coverage": 0.0,
    "timeline_ratio": 0.0,
    "monotonic_ratio": 0.0,
    "duplicate_ratio": 0.0,
    "text_density": 0.0
  }
}
```

确定性检查至少包括：

```text
Segment 顺序
时间单调
时间轴是否严重超过 duration
字幕覆盖
空白率
重复率
异常字符
极端文本密度
```

建议初始硬规则：

```text
last_end_ms >
duration_ms + max(30_000, duration_ms * 0.20)
→ timeline invalid
```

在 `GENERATE_AI_NOTE` 前统一断言：

```text
validation_status ∈
TRUSTED_PLATFORM
VERIFIED_GENERATED
LOCAL_ASR
```

同时检查：

```text
Transcript.video_asset_id
Snapshot.source_id
Job 请求 BV/CID
```

一致。

若：

```text
PLATFORM_SUBTITLE_MISMATCH
+
ASR 失败 / 不可用
```

则：

```text
Job = NEEDS_USER
error_code = TRANSCRIPT_SOURCE_MISMATCH
```

禁止继续：

```text
GENERATE_AI_NOTE
EXTRACT_TRAVEL_FACTS
MATERIALIZE
```

---

# 8. WP4 — 保存非敏感审计信息

优先复用 JSON 字段。

`Transcript.metadata_json` 或对应 Job Artifact 保存：

```json
{
  "requested_bvid": "...",
  "requested_cid": "...",
  "subtitle_endpoint": "...",
  "subtitle_track_id": "...",
  "subtitle_language": "ai-zh",
  "subtitle_generated": true,
  "subtitle_url_sha256": "...",
  "subtitle_body_sha256": "...",
  "timeline_ratio": 1.0,
  "validation_status": "LOCAL_ASR",
  "validation_reasons": [],
  "validation_version": "subtitle-alignment-v1"
}
```

安全要求：

```text
不保存 Cookie
不保存 SESSDATA
不保存完整带临时参数 subtitle_url
不保存整段字幕正文
```

若 AI 字幕没有成为权威 Transcript：

```text
轨道信息 / Hash / Validation
→ 写入 FETCH_SUBTITLE Step / Artifact
```

不要伪装成 Transcript 来源。

---

# 9. WP5 — 地点抽取与视频总结彻底解耦

修改：

```text
backend/src/zhijian/services/video_support.py
backend/src/zhijian/ai/stages.py
backend/src/zhijian/prompts/travel_place_extraction.md
```

删除当前语义：

```text
非 REMOTE_ONLY
→ 直接使用 note.map_facts_json
```

改为：

```text
所有 execution_mode
→ 都执行真正的 EXTRACT_TRAVEL_FACTS
```

`execution_mode` 只决定 Provider。

`note.map_facts_json`：

```text
只用于旧数据兼容 / 辅助
不得成为新地点数据的主来源
```

---

# 10. WP6 — 完整 Transcript 分块高召回地点抽取

禁止：

```python
_transcript_context(all_segments, max_chars)
```

一次性处理完整长视频。

必须：

```text
_transcript_chunks
↓
chunk1
chunk2
chunk3
...
↓
每块 Travel Place Extraction
↓
merge / dedupe
```

建议默认：

```text
chunk_chars ≈ 8000
neighbor_segments = 3
```

实际参数通过：

```text
EXTRACT_TRAVEL_FACTS Stage Policy
```

管理。

Chunk 需要有限 overlap，避免：

```text
上一块：
“接下来我们去”

下一块：
“鸡足山”
```

被切断。

---

# 11. WP7 — Place Extraction Prompt 改为召回优先

修改：

```text
backend/src/zhijian/prompts/travel_place_extraction.md
```

明确：

```text
目标是召回所有明确提到、可落地图的地点，
而不是总结最重要地点。

地点即使：
- 只出现一次
- 句子很短
- 语速很快
- 没有推荐理由
也必须输出。

同一个 Segment 可以输出多个地点。
```

城市/区域：

```text
仅作上下文 → city_hint
本身是游览对象 → AREA candidate
```

每个 Candidate 必须：

```text
raw_name
quote
segment_ids
```

---

# 12. WP8 — Place Candidate Evidence Gate

写入 `PlaceMention` 之前验证：

```text
segment_ids 是否真实存在
quote 是否能在对应校对文本找到
raw_name 是否能由 Evidence 或已记录 ASR Correction 支撑
start_ms / end_ms 是否可计算
```

不通过：

```text
DROP
+
record_event(place.extraction.evidence_rejected)
```

不能再认为：

```text
有合法 Segment ID
=
事实成立
```

---

# 13. WP9 — Cross-chunk Merge / Dedupe

合并考虑：

```text
normalized raw_name
suggested_name
city_hint
province_hint
place_type
时间邻近关系
```

规则：

```text
同一地点 + 相邻 Chunk
→ 合并 Segment / Quote Evidence

同名不同城市
→ 不自动合并

同名且语境不清
→ 保持 REVIEW

任何 dedupe
→ 不得丢失 Evidence
```

---

# 14. WP10 — 调整 Pipeline：先抽地点，再生成 Note

由：

```text
GENERATE_AI_NOTE
↓
EXTRACT_TRAVEL_FACTS
```

调整为：

```text
EXTRACT_TRAVEL_FACTS
↓
GENERATE_AI_NOTE
```

这样 Note 生成前已经拥有：

```text
Validated Place Evidence Index
```

由于 `PlaceMention.ai_note_version_id` 当前可为空，地点可以在 Note Version 前生成，随后再关联。

同步更新：

```text
Replay
retry-from-step
JobStepArtifact
Pipeline ordering tests
```

---

# 15. WP11 — 视频笔记一级章节地点化

建议新增 Migration：

```text
backend/src/zhijian/db/migrations/0019_video_note_grounded_sections.py
```

`AINoteSection` 至少新增：

```text
section_kind
```

类型：

```text
PLACE
AREA
ROUTE
SUPPLEMENTAL
```

长期推荐同时增加：

```text
place_mention_ids_json
evidence_quotes_json
```

如需控制本轮 Schema 范围，至少先落 `section_kind`。

---

# 16. WP12 — 给 Note 模型输入 Validated Place Evidence Index

示例：

```json
[
  {
    "mention_id": "pm_xxx",
    "name": "鸡足山",
    "place_type": "SCENIC_AREA",
    "segment_ids": ["seg_1"],
    "quotes": ["……鸡足山……"]
  }
]
```

修改：

```text
backend/src/zhijian/prompts/video_note.md
```

冻结规则：

```text
1. 一级 Section 只能 PLACE / AREA / ROUTE
2. Heading 必须以地点为锚点
3. 非地点事实挂到对应地点
4. 无法归属的事实进入 supplemental
5. 不得遗漏 Validated Place Evidence 中明确地点
6. 每个主要事实必须带 supporting_quotes
7. supporting_quotes 必须来自 Transcript
```

---

# 17. WP13 — Heading 尽量由服务端生成

建议：

### 单地点

```text
鸡足山
```

### 区域

```text
大理周边｜沙溪・诺邓・巍山
```

### 路线

```text
古城 → 苍山 → 洱海
```

禁止模型自由产生一级标题：

```text
一定要来的宝藏地方
100出头就能住小院
这里太出片了
```

---

# 18. WP14 — 修复伪 Grounding 的 Map/Reduce

Map 输出应包含：

```text
facts
segment_ids
supporting_quotes
place_mention_ids
```

服务端执行：

```text
Exact Quote Match
↓
Segment Validation
↓
删除 unsupported facts
↓
GroundedEvidencePack
```

只有 `GroundedEvidencePack` 可以进入 Reduce。

Reduce 输入：

```text
Validated Fact
+
Exact Transcript Quote
+
Segment ID
+
PlaceMention ID
```

不再只输入“模型总结出的 SectionFacts”。

---

# 19. WP15 — Note 输出后二次 Evidence 校验

至少检查：

```text
segment_ids valid
supporting_quotes exact match
section_kind valid
PLACE section 至少绑定一个 PlaceMention
数字 / 金额 / 月份存在于 Evidence
```

不满足：

```text
局部 Section fallback
或
删除 unsupported fact
```

禁止保留“语言流畅但无证据”的事实。

---

# 20. WP16 — 扩展 Review Context API

继续复用已有：

```text
POST /api/travel/place-mentions/{mention_id}/confirm
POST /api/travel/place-mentions/{mention_id}/poi-search
POST /api/travel/place-mentions/{mention_id}/reject
POST /api/travel/place-mentions/{mention_id}/restore
```

扩展：

```text
GET /api/travel/place-reviews
GET /api/travel/place-reviews?video_note_id=...
```

返回每条 Review：

```json
{
  "mention_id": "...",
  "name": "...",
  "raw_name": "...",
  "suggested_name": "...",
  "place_type": "...",
  "reason": "...",
  "confidence": 0.0,
  "revision": 0,
  "candidates": [],
  "source_context": {
    "video_note_id": "...",
    "video_title": "...",
    "canonical_url": "...",
    "quote": "...",
    "segment_ids": [],
    "start_ms": 0,
    "end_ms": 0,
    "section": {
      "id": "...",
      "heading": "...",
      "summary": "..."
    },
    "transcript_context": [],
    "screenshot": null
  }
}
```

---

# 21. WP17 — Review Transcript Context

默认返回：

```text
Evidence Segment
+
前 2 Segment
+
后 2 Segment
```

每段可标：

```text
is_evidence
```

如果 Transcript 已按现有 retention 删除：

```text
继续展示 PlaceMention.quote
+
“完整转写已过期”
```

不要为了 Review 绕过现有保留策略。

---

# 22. WP18 — 统一 PlaceReviewCard

新增：

```text
frontend/src/features/places/PlaceReviewCard.tsx
```

统一展示：

```text
地点候选
地点类型
置信度
提取原因

视频标题
章节
时间码
Evidence 原文
前后 Transcript Context
相关截图

AMap Candidates
重新搜索
选择 POI
不是地点
撤销
```

两个审核入口必须复用同一个组件和同一套 API。

---

# 23. WP19 — 升级 `/place-reviews`

修改：

```text
frontend/src/features/map/PlaceReviewsPage.tsx
```

审核体验顺序：

```text
先让用户知道：
“原视频到底说了什么？”

再让用户判断：
“高德里应该选哪个 POI？”
```

避免用户只看到一个孤立地名凭空判断。

---

# 24. WP20 — 视频笔记页内直接确认地点

修改：

```text
frontend/src/features/video/VideoNotesPage.tsx
```

状态：

### CONFIRMED

保持普通地点展示。

### REVIEW

显示轻量：

```text
待确认
```

点击后：

```text
Inline / Drawer PlaceReviewCard
```

允许原页面完成：

```text
选择 POI
重新搜索
不是地点
撤销
```

不要求跳转到 `/place-reviews`。

---

# 25. WP21 — 前端缓存同步

确认 / Reject / Restore 后 invalidate：

```text
video-places
video-note
place-reviews
place-review-count
map
```

不要依赖整页刷新。

---

# 26. WP22 — Evidence 双向跳转

支持：

```text
Review 时间码
→ 跳到对应 Note Section
```

以及：

```text
Note Section 有待确认地点
→ 显示轻量 Review Indicator
→ 点击打开对应 PlaceReviewCard
```

---

# 27. WP23 — P1 性能优化：AI 字幕抽样验证

只有 P0 稳定后，并且真实运行证明“AI 字幕全部走完整 ASR”的延迟或资源成本不可接受时才实施。

不要与 P0 同时增加复杂度。

流程：

```text
下载音频
↓
前 / 中 / 后各采样 15–25 秒
↓
Whisper.cpp 局部 ASR
↓
归一化平台字幕与 ASR
↓
difflib.SequenceMatcher
```

初始建议：

```text
单段 similarity >= 0.55
3 段至少 2 段通过
且无时间轴硬异常
```

则：

```text
VERIFIED_GENERATED
```

否则：

```text
PLATFORM_SUBTITLE_MISMATCH
→ Full ASR
```

阈值：

```text
只能在一个配置位置定义
必须经过 Fixture + 真实样本后再调整
```

标题相似度只能作为弱信号，不能用于放行。

---

# 28. WP24 — 历史污染数据修复

至少已知两个污染 Note。

原则：

```text
不原地修改旧 Transcript
不原地修改旧 Segment
不原地修改旧 Note Version
不覆盖旧 Evidence
```

修复流程：

```text
可信音频
↓
新 Transcript Version
↓
新 Snapshot / Segment
↓
重新抽 PlaceMention
↓
新 Note Version / Section
↓
新截图计划 / Caption
↓
切换 AINote.current_version_id
```

旧版本：

```text
保留审计
标记 superseded
```

真实修复前检查：

```text
active Job
lease
Worker concurrency
```

真实 Provider 调用：

```text
串行
遵守预算 / QPS
```

---

# 29. 自动测试清单

Backend 至少增加：

```text
test_human_subtitle_passes_timeline_gate_without_asr
test_ai_subtitle_requires_asr_in_p0
test_platform_subtitle_severe_mismatch_requires_fallback
test_platform_subtitle_mismatch_blocks_note_when_asr_unavailable
test_subtitle_timeline_exceeds_video_duration_falls_back_to_asr
test_video_jobs_do_not_cross_reuse_subtitle_tracks
test_subtitle_audit_does_not_store_secret_or_full_body

test_place_extraction_scans_all_chunks
test_place_extraction_keeps_fast_multi_poi_mentions
test_place_extraction_dedupes_overlap_without_losing_evidence
test_place_candidate_without_exact_evidence_is_rejected

test_note_primary_sections_are_place_anchored
test_generic_price_fact_is_not_primary_heading
test_reduce_rejects_unbacked_fact
test_numeric_fact_requires_transcript_evidence

test_place_review_api_contains_video_context
test_place_review_api_contains_neighbor_transcript
test_video_review_filter_by_note_id
```

Frontend 至少覆盖：

```text
待确认地点展示 Evidence
选择 POI 后立即变为 confirmed
Reject 后立即移出当前 Review
视频笔记页可以直接审核
全局 review count 同步
```

---

# 30. Benchmark 指标

扩展：

```text
dev docs/benchmark/video-workflow-golden-v1.json
scripts/run_video_benchmark.py
```

新增：

```text
explicit_place_recall
place_precision
unsupported_place_count
primary_section_place_anchor_rate
unsupported_numeric_fact_count
evidence_quote_pass_rate
transcript_mismatch_detection_rate
review_context_coverage
```

最低 Gate：

```text
Explicit Place Recall >= 95%
primary_section_place_anchor_rate = 100%
evidence_quote_pass_rate = 100%
unsupported_numeric_fact_count = 0
unsupported_place_count = 0
```

污染字幕 Fixture：

```text
错误平台字幕不得进入正式 Note
```

---

# 31. 修改文件清单

## Backend

```text
backend/src/zhijian/resolvers/video/bilibili.py
backend/src/zhijian/services/video_pipeline.py
backend/src/zhijian/services/video_support.py
backend/src/zhijian/services/transcript_validation.py        # new
backend/src/zhijian/ai/transcript_quality.py
backend/src/zhijian/ai/stages.py
backend/src/zhijian/prompts/video_note.md
backend/src/zhijian/prompts/travel_place_extraction.md
backend/src/zhijian/api/router.py
backend/src/zhijian/api/video_notes.py
backend/src/zhijian/db/models.py
backend/src/zhijian/db/migrations/0019_video_note_grounded_sections.py
```

必要时：

```text
backend/src/zhijian/services/external_audit.py
```

## Tests

```text
backend/tests/test_video_notes.py
backend/tests/test_api.py
backend/tests/test_transcript_validation.py
backend/tests/test_place_extraction_recall.py
```

## Frontend

```text
frontend/src/features/map/PlaceReviewsPage.tsx
frontend/src/features/video/VideoNotesPage.tsx
frontend/src/features/places/PlaceReviewCard.tsx
frontend/src/lib/api.ts
frontend/src/lib/types.ts
frontend/src/styles.css
```

## Benchmark / Docs

```text
dev docs/benchmark/video-workflow-golden-v1.json
scripts/run_video_benchmark.py
dev docs/planning/video/VIDEO_WORKFLOW_BENCHMARK_AND_ACCEPTANCE_PLAN.md
dev docs/IMPLEMENTATION_STATUS.md
```

---

# 32. Agent 推荐执行顺序

严格按依赖执行：

```text
WP0 失败 Fixture / 回归基线
↓
WP1 Subtitle Source / Track / Endpoint Audit
↓
WP2 P0 AI 字幕信任门禁 + ASR
↓
WP3 Transcript Validation Hard Gate
↓
WP4 审计记录
↓
WP5 地点独立 Extraction
↓
WP6 完整 Chunk + Overlap
↓
WP7 High-Recall Prompt
↓
WP8 Place Evidence Gate
↓
WP9 Cross-chunk Merge
↓
WP10 Pipeline 改为先 Place 后 Note
↓
WP11–15 地点化 Note + Grounded Map/Reduce
↓
WP16–22 Review Context + 双入口审核
↓
完整 Backend / Frontend / Benchmark 回归
↓
授权后真实重放两个污染视频
↓
历史污染数据新版本修复
↓
根据性能结果决定是否实施 WP23 抽样验证
```

不要优先做：

```text
视觉模型
OCR
推荐指数
模型大换血
地图整体 UI 重构
```

---

# 33. Real E2E 验收

真实 Provider / 视频重跑需要单独授权后执行。

至少串行重放两个污染样本。

核对：

```text
BV
CID
VideoAsset
最终 Transcript source
validation_status
```

人工检查：

```text
前 / 中 / 后至少三个时间点
视频语音 / 硬字幕
vs
Segment
```

必须确认：

```text
新 Note 为真实旅行主题
不包含“露丝”
不包含错误兴趣/成长内容
```

同时检查：

```text
PlaceMention
Section
Screenshot Caption
```

均来自新的权威 Transcript。

不能只以：

```text
Job 命令成功
```

作为通过。

---

# 34. Definition of Done

- [ ] 人工字幕只有通过结构/时间轴 Gate 后才可直通。
- [ ] 任意 `ai-zh` 未验证前不得成为唯一权威 Transcript。
- [ ] P0 下 AI 字幕默认进入 ASR。
- [ ] 字幕验证失败且 ASR 失败时进入 `NEEDS_USER/TRANSCRIPT_SOURCE_MISMATCH`。
- [ ] BV/CID、Subtitle Track、Endpoint、Hash 可审计且无 Secret 泄露。
- [ ] 默认 `LOCAL_FIRST` 也会独立扫描完整 Transcript 抽取地点。
- [ ] 超过 12000 字符的长视频不会漏掉后半段地点。
- [ ] 快速多地点 Explicit Place Recall 达到 ≥95%。
- [ ] Place candidate 必须具有真实 Evidence。
- [ ] 一级目录 100% 为 PLACE / AREA / ROUTE。
- [ ] 价格、住宿体验、交通建议等不再成为一级 Heading。
- [ ] Map/Reduce 不再把模型摘要直接视为已验证事实。
- [ ] 地点、数字、金额、月份等必须回溯到 exact quote。
- [ ] `/place-reviews` 展示视频标题、章节、时间码、原文及前后文。
- [ ] 视频笔记页可以直接完成确认、重新搜索、Reject、Restore。
- [ ] 两个审核入口复用同一 API 和 `PlaceReviewCard`。
- [ ] 两个污染 Fixture 可稳定阻断错误内容。
- [ ] Backend Test / Frontend Test / Fixture Benchmark 全部通过。
- [ ] 历史污染数据通过新 Transcript / Note Version 修复，不覆盖旧版本。
- [ ] 更新 `dev docs/IMPLEMENTATION_STATUS.md`。
- [ ] 提交并推送 `codex/mac-mini-implementation`。

---

# 35. 本轮明确不做

```text
推荐指数 / 作者评分体系
跨视频自动评分
地图整体视觉重构
路线规划算法扩展
视觉 OCR 作为主地点抽取源
新增向量数据库
更换默认模型
删除现有 Model Profile
绕过 Transcript retention 长期保存完整转写
```

---

# 36. Agent 执行约束

1. 不做大面积 Repo 扫描。
2. 先读本计划，再只读目标文件及其直接依赖。
3. 每个工作包先补 Fixture / Failing Test，再改实现。
4. 保留现有 AI Gateway / Model Profile / Stage Policy 架构。
5. 不硬编码替换模型。
6. 不用 Prompt 掩盖确定性代码 Bug。
7. 不因为优化地点功能扩大到地图、路线或评分体系。
8. 任何“已验证 Evidence”必须由服务端校验，而不能只因为模型声称已验证。
9. 历史污染修复必须版本化，不原地改旧数据。
10. 完成后更新状态文档，再 Commit / Push 当前分支。

---

# 37. 最终架构判断

本轮真正需要修复的是四个架构问题：

```text
1. 不可信 AI 字幕被直接当成权威 Transcript
2. 视频总结结果被当成地点抽取数据源
3. 带 Segment ID 的模型摘要被当成已验证 Evidence
4. 人工地点确认与原始 Evidence 被拆成两个割裂体验
```

正确顺序必须是：

```text
可信输入
→ 高召回实体
→ 强 Evidence
→ 地点化笔记
→ 低成本人工确认
```

不要继续在被污染或不完整的数据上增加更复杂的 Prompt。
