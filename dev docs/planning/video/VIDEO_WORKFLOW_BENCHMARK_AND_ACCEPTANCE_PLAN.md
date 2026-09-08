# 视频知识提取工作流：Benchmark 与验收计划

> 适用分支：`codex/mac-mini-implementation`
> 范围：仅视频工作流
> 目标：把旅行/探店视频稳定转换为可阅读、可追溯、可落地图、可跨视频积累的视频知识资产。
> 本计划不扩展招聘、通用 Capture、自动行程规划或推荐指数。
>
> 状态（2026-09-08）：Pipeline、Place Insight、POI Review、地图核心能力与截图物化已进入源码；当前自动验证与真实样本边界以 [实施状态](../../IMPLEMENTATION_STATUS.md) 为准。下文保留原 Work Package 作为设计背景，不能把它们逐条当作当前待办。

## 当前尚未执行的范围

1. 建立有人工标注的 Video Workflow Golden Dataset，并以真实采集结果运行模型/路由 Benchmark；现有 Gateway runner 只是骨架。
2. 将 `qwen3.5:9b` 作为待验证的候选，而非当前默认或唯一模型；先完成 Capability Probe 与同数据集比较，再由用户决定 Profile 默认值。
3. 评估并按需实现单条 Insight 的时间码呈现、跨视频来源聚合/冲突视图和 POI 质量指标；来源与 Evidence 不得合并丢失。
4. 在 P0 生产门禁之后，才评估候选帧的 Visual Evidence；不得扫描整段视频或让视觉结果覆盖 Transcript Fact。
5. 按 [AI Gateway 生产验收](../../ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md) 留存真实 Provider、缓存、fallback、取消与 Replay 证据。

---

# 0. 核心决策

## 0.1 产品目标

视频处理的目标不是：

```text
Video → AI Summary
```

而是：

```text
Video
↓
Transcript / Evidence
↓
Video Understanding
↓
──────────────────────────────────
Video Note
Place Knowledge
Visual Evidence
──────────────────────────────────
↓
可阅读、可检索、可校验、可聚合的个人旅行知识
```

一个视频至少应产生四类长期资产：

| 资产 | 作用 |
|---|---|
| Video Note | 不观看完整原片也能理解视频主要内容 |
| Transcript Evidence | 所有重要事实可回到原视频时间码 |
| Place Knowledge | 地点、菜品、看点、价格、季节、提醒等结构化信息 |
| Visual Evidence | 菜品、店招、菜单、景点、路线等关键画面 |

多个视频提及同一地点时，应逐渐形成同一个 Place 的多来源知识，而不是创建互不相关的笔记。

---

# 1. 模型策略冻结

## 1.1 不采用“唯一 Qwen3.5 9B”架构

本计划明确禁止：

```text
业务代码硬编码 qwen3.5:9b
删除 qwen2.5 / qwen3 / 其他已有模型
隐藏其他本地模型配置
把 FAST_LOCAL / MAIN_LOCAL / LOCAL_VISION 固定绑定到某一型号
因为公开 Benchmark 排名决定删除模型
```

继续保留：

```text
Model Profile
+
Capability
+
Stage Policy
+
Execution Mode
```

业务 Pipeline 只声明 Capability，不感知具体模型名。

当前仓库已经有 Profile、Stage Policy、Local/Remote 路由、Cache、Budget 和 Domain Context，这部分架构继续保留。

## 1.2 Qwen3.5 9B 的定位

本计划的候选配置：

```text
Preferred Local Default:
    qwen3.5:9b
```

它可以同时作为：

```text
FAST_LOCAL_TEXT
MAIN_LOCAL_TEXT

未来在 Vision Probe 通过后：
LOCAL_VISION
```

但这里只代表：

> 通过本计划 Benchmark 后，才可考虑作为新安装或未选择模型时的推荐默认值。

不代表：

> 已证明比现有所有模型更好。

## 1.3 其他模型保留规则

Agent 必须：

1. 读取当前已保存的 Model Profile；
2. 读取 Ollama 当前已安装模型；
3. 建立 Benchmark Candidate Matrix；
4. 对符合 Capability 的模型使用同一 Golden Dataset 测试；
5. 输出模型对比报告。

本计划结束时只允许产生以下结论：

```text
RECOMMENDED_DEFAULT
RECOMMENDED_FAST
RECOMMENDED_MAIN
RECOMMENDED_VISION
VALID_ALTERNATIVE
NOT_ENOUGH_EVIDENCE
FAILED_MINIMUM_GATE
```

禁止自动产生：

```text
REMOVE_MODEL
DELETE_MODEL
UNINSTALL_MODEL
```

即使某模型 Benchmark 明显较差，也只允许报告结果，由用户后续决定是否下架。

---

# 2. 当前基线

当前源码已经实现：

```text
Bilibili Resolve
→ Metadata / Cover
→ Platform Subtitle
→ Audio + Whisper fallback
→ Transcript Normalize
→ Transcript Correction
→ Video Note Map/Reduce
→ Place Extraction
→ AMap POI Resolution
→ Place Insight
→ Screenshot Planning
→ Video Download for Frames
→ Screenshot Extraction
→ Materialize
```

真实生产样本已经至少走通过字幕、笔记、地点提取和截图；POI 未自动确认时以 `PARTIAL_SUCCESS` 结束。

目前已有 Place Insight 类型包括：

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
```

当前主要问题已经从“有没有 Pipeline”转变为：

```text
抽取得准不准
↓
证据够不够细
↓
地点能否正确 Grounding
↓
用户能否真正看到有价值的信息
↓
多个视频能否积累到同一个 Place
↓
视觉信息能否补充字幕遗漏
```

---

# 3. 本轮工作范围

按优先级分为 7 个 Work Package：

```text
WP0 Benchmark 基础设施
WP1 Model / Structured Output 基础
WP2 Video Knowledge Extraction
WP3 Video Note Insight UX
WP4 Cross-video Place Aggregation
WP5 POI Resolution Quality
WP6 Optional Visual Evidence
```

另设：

```text
WP7 Final Benchmark & Production Acceptance
```

WP0～WP5 为本轮核心。

WP6 Vision 可以完成架构与实验，但只有 Benchmark 达标后才能默认开启。

---

# 4. WP0 — Benchmark 基础设施

> 进度（2026-09-08）：Fixture Golden、`scripts/run_video_benchmark.py` 和 `scripts/capture_video_benchmark.py` 已完成，覆盖 12 个冻结字幕/ASR/POI/Insight/长上下文场景，并可从已有 Job/Replay 的只读记录导出可评分输入。它们不调用 Provider 或下载视频，明确不是真实模型或视频验收。Real E2E Matrix 仍待用户提供合法配置并授权执行。

## 4.1 目标

先建立可重复验证体系，再继续调 Prompt 或模型。

当前仓库已有：

```text
dev docs/benchmark/golden-ai-gateway-samples.json
scripts/run_ai_benchmark.py
```

但现有 Golden Sample 中 `key_entities` / `key_places` 基本仍为空，因此目前更像 Benchmark 骨架，还不足以比较不同模型的视频业务质量。

现有 evaluator 也主要比较：

```text
schema
evidence
place recall
entity recall
remote token reduction
```

还不足以评估本视频工作流需要的 Insight、POI 和校对质量。

## 4.2 新增 Dataset

新增：

```text
dev docs/benchmark/video-workflow-golden-v1.json
```

至少建立 12～16 个业务样本。

必须覆盖：

### Transcript

```text
干净平台字幕
存在少量 ASR 错字
口音 / 同音地名
中英混合
数字 / 时间 / 金额
否定句
专有名词
```

### Travel / Food

```text
单餐馆
多餐馆
景区
餐馆 + 景区混合
同名跨城市地点
模糊店名
仅提城市但不应创建 Marker
多个明确 POI
```

### Insight

至少包含：

```text
推荐菜
核心看点
价格
排队
最佳月份
最佳季节
最佳时间段
建议停留时长
适合人群
注意事项
作者正面评价
作者负面评价
```

### Long Context

至少：

```text
10 分钟
30 分钟
45～60 分钟
```

## 4.3 Golden Annotation Schema

每个样本至少定义：

```json
{
  "sample_id": "...",
  "source_kind": "...",
  "expected": {
    "transcript_changes": [],
    "required_places": [],
    "forbidden_places": [],
    "place_types": {},
    "insights": [],
    "section_topics": [],
    "required_evidence": [],
    "poi_resolution": {}
  }
}
```

每条 Insight Annotation 必须包含：

```text
place
insight_type
expected_value
segment_id
source_span / quote
```

这样才能真正验证“推荐菜抽出来了没有”，而不是只检查“JSON 能不能解析”。

## 4.4 Benchmark 分两层

### Layer A — Fixture Benchmark

不访问真实 Bilibili。

输入使用冻结：

```text
Transcript
Metadata
Segment
POI Fixture
Frame Fixture
```

用于：

```text
CI
回归
Prompt 对比
模型输出评价
Parser 评价
```

### Layer B — Real E2E Benchmark

使用 deployment-owned / 用户授权视频。

执行：

```text
真实 Bilibili
真实字幕
真实 Whisper
真实 Ollama
真实 AMap
真实截图
```

不进入普通 CI。

---

# 5. Benchmark Runner 改造

新增：

```text
scripts/capture_video_benchmark.py
scripts/run_video_benchmark.py
```

不要让 Agent 手工复制结果。

## 5.1 Capture Runner

输入：

```text
sample_id
profile_id
stage_policy
job_id / replay artifact
```

自动记录：

```text
model_profile
provider
model
context
temperature
thinking
input tokens
output tokens
wall time
model attempts
fallback count
schema pass
cache hit
peak memory
stage outputs
```

必须保存：

```text
input artifact hash
prompt version
model profile version
stage policy version
```

## 5.2 Replay Benchmark

模型比较禁止每次重新：

```text
下载视频
ASR
抽帧
```

应该利用已有 Replay：

```text
冻结 Transcript
↓
从 CORRECT_TRANSCRIPT Replay
或
从 GENERATE_AI_NOTE Replay
或
从 EXTRACT_TRAVEL_FACTS Replay
```

这样才能保证：

```text
同一输入
同一 Evidence
同一 Prompt
同一参数
仅改变 Model
```

---

# 6. 模型 Benchmark Matrix

> 进度（2026-09-08）：已发现并 Probe 本机 `qwen2.5:7b`、`qwen3:8b`、`qwen3.5:9b`；三者均通过分类、结构化抽取、实体抽取与转写校对的基础检查。Probe 未覆盖的 Stage 标为 `FAIL`，只表示尚无验证，不能作为能力否定或模型下架依据。尚未运行质量矩阵或改变默认 Profile。

Agent 首先自动发现：

```text
Saved Model Profiles
+
ollama list
```

然后按 Capability 分组。

例如实际存在时：

| Profile | Text | Thinking | Vision | 是否参与 |
|---|---:|---:|---:|---|
| qwen3.5:9b | ✓ | ✓ | Probe | ✓ |
| qwen3:8b | ✓ | ✓ | × | ✓ |
| qwen2.5:7b | ✓ | × | × | ✓ |
| 其他本地模型 | Probe | Probe | Probe | 按能力 |

不能因为模型名称猜 Capability。

必须经过 Capability Probe。

---

# 7. 模型比较规则

每个核心 Profile：

```text
同一数据集
同一 Prompt
同一 Context Strategy
同一温度
同一输出限制
force_regenerate=true
```

至少运行：

```text
3 次
```

报告平均值，同时记录最大差异。

## 7.1 不采用一个“总分决定一切”

模型报告必须按 Stage 分开：

```text
Transcript Correction
Place Extraction
Note Map
Note Reduce
Conflict Resolution
Vision
```

一个模型可能校对更好但 Note 更慢，另一个可能结构化抽取很好但复杂归纳较弱。

这种情况下两个模型都应保留为有效候选。

---

# 8. WP1 — Structured Output 与模型能力层

## 8.1 Ollama Structured Output

当前 Ollama Provider 主要使用：

```text
format = json
```

需要扩展成：

```python
generate_structured(
    messages,
    model,
    schema,
    options
)
```

Provider 有能力时：

```text
JSON Schema constrained output
```

否则：

```text
JSON Mode
+ Prompt Contract
+ Pydantic Validation
```

## 8.2 所有核心输出建立正式 Schema

至少：

```text
TranscriptCorrectionOutput
VideoMapOutput
VideoReduceOutput
PlaceExtractionOutput
VisualEvidenceOutput
```

禁止核心 Pipeline 依赖：

```text
json.loads()
+
手工猜字段
```

作为唯一验证。

## 8.3 Capability Probe 扩展

Probe 实际验证：

```text
TEXT
JSON
JSON_SCHEMA
THINKING
IMAGE
TOOLS
CONTEXT
```

Vision 不能再：

```text
modalities=image → 直接 FAIL
```

必须真实 Probe。

## 8.4 验收

WP1 完成条件：

```text
所有现有模型仍可保存和选择
qwen3.5:9b 可作为默认推荐 Profile
业务代码无 qwen3.5:9b 硬编码
JSON Schema 支持有自动测试
无 Schema 能力模型可以明确 fallback
Stage Policy 仍可替换模型
```

---

# 9. WP2 — Video Knowledge Extraction

> 进度（2026-09-08）：SectionFacts/Place Insight 已在源码中；0018 为每条 `PlaceInsightItem` 增加独立 `source_quote`，并优先使用结构化输入指定的 Segment，缺失时确定性匹配回 Transcript。未重跑视频，跨视频聚合与前端呈现仍在后续 WP。

这是本轮最核心工作。

## 9.1 Map 阶段统一产生 SectionFacts

每个 Transcript Chunk 一次生成：

```text
summary
key_points
places
people
warnings
opinions
prices
domain_terms
segment_ids
```

Place 内同时允许产生：

```text
highlights
recommended_items
best_months
best_seasons
best_time_slots
suggested_duration
price
queue
audience
warnings
author_opinion
```

默认不再为这些信息重复调用第二遍模型。

## 9.2 Insight 必须拥有自己的 Evidence

目前 PlaceMention 可以有多个 Segment，但单个 Insight 的 Evidence 粒度仍应进一步细化。

目标结构：

```text
PlaceInsightItem
├─ insight_type
├─ value
├─ confidence
├─ provenance
├─ segment_ids[]
├─ source_quote
└─ source_id
```

不能让“推荐菜”和“最佳月份”都只共享整个 PlaceMention 的宽泛 Evidence。

如果需要新增持久字段：

```text
创建新的 Alembic migration
```

禁止修改已经发布的历史 migration。

## 9.3 Source Fact 和 AI Inference 必须分开

至少区分：

```text
SOURCE_FACT
VISUAL_FACT
PERSONAL_INFERENCE
```

本阶段默认主要生成：

```text
SOURCE_FACT
```

推荐指数与个性化评分暂不实现。

## 9.4 不确定事实

模型无法确定时：

```text
UNKNOWN
或
REVIEW
```

禁止为了填满字段产生事实。

---

# 10. WP2 Benchmark 指标

## Transcript Correction

```text
correction_precision
correction_recall
unchanged_preservation
proper_noun_accuracy
number_preservation
hallucinated_change_rate
```

Minimum Gate：

```text
unchanged_preservation >= 0.98
critical hallucinated change = 0
数字/价格/否定语义重大破坏 = 0
```

## Place Extraction

```text
place_precision
place_recall
place_type_accuracy
false_place_count
```

推荐门槛：

```text
precision >= 0.90
recall >= 0.85
critical_false_place = 0
```

## Insight Extraction

分别计算：

```text
HIGHLIGHT
RECOMMENDED_ITEM
BEST_MONTH
BEST_SEASON
BEST_TIME_SLOT
PRICE
QUEUE
WARNING
AUTHOR_OPINION
```

核心目标：

```text
insight_precision >= 0.90
insight_recall >= 0.80
evidence_coverage >= 0.90
critical_hallucinations = 0
```

这里只作为 V1 release gate，之后可根据真实样本调整。

---

# 11. WP3 — Video Note Insight UX

当前后端已经拥有大量 Insight，但 Video Note 页面没有充分展示它们。

这是当前最高优先级产品差距之一。

## 11.1 本片地点卡

Video Note Detail 的地点区改为真正的知识卡。

餐馆示例：

```text
陶德砂锅

推荐
• 蒜香排骨
• 耙鸡脚

核心特点
• 本地家常口味
• 重口偏香

价格
• 人均约 70～90

什么时候去
• 17:00 前

提醒
• 周末晚餐排队明显

作者评价
• 味道值得专程去

证据
12:43
13:21
14:05

[地图] [地点详情] [回原视频]
```

景区根据类型自动改变字段优先级。

## 11.2 Insight 时间码

每条 Insight 必须可以：

```text
点击
↓
跳到 Video Note 对应 Section
↓
展开对应 Transcript
```

而不是只有整个 Place 有一个时间码。

## 11.3 Timeline 内轻量展示

时间线 Section 内出现地点时，可显示：

```text
地点名
+ 2～4 条最高价值 Insight
```

不要把完整地点详情塞进正文。

完整信息仍在：

```text
本片地点
或
Place Detail
```

## 11.4 前端验收

必须验证：

```text
PC
Mobile
键盘
长文本
多地点
无地点
Review POI
Confirmed POI
```

---

# 12. WP4 — Cross-video Place Aggregation

> 冻结（2026-09-08）：核心确定性聚合已实现；UI 冲突视图与真实 Cross-video Golden 暂缓。

当前 `build_place_notes()` 更接近单 Mention 模板。

需要升级成：

```text
Place
↓
收集全部有效 PlaceInsightItem
↓
按来源分组
↓
归一化 / 去重
↓
检测冲突
↓
生成聚合视图
```

## 12.1 不允许覆盖来源

例如：

```text
视频 A：人均 80
视频 B：人均 120
```

保存：

```text
PRICE / A / ¥80
PRICE / B / ¥120
```

聚合层展示：

```text
不同来源价格存在差异：
¥80 ～ ¥120
```

不能：

```text
最后一个模型输出覆盖前一个。
```

## 12.2 Consensus 与 Conflict

允许确定性生成：

```text
CONSENSUS
CONFLICT
SINGLE_SOURCE
```

例如：

```text
3 个来源都推荐蒜香排骨
→ CONSENSUS

价格 70 / 100 / 120
→ CONFLICT
```

## 12.3 Place Note

最终 Place Detail 建议结构：

```text
核心看点
推荐菜 / 体验
最佳时间
价格
排队
提醒

多个作者共同观点

不同作者观点

来源视频
├─ Video A · 12:43
├─ Video B · 08:22
└─ Video C · 21:15
```

---

# 13. WP4 Benchmark

新增 Cross-video Golden：

```text
同一 Place
+
2～3 个来源
```

验证：

```text
place_dedup_accuracy
insight_dedup_accuracy
conflict_detection
source_preservation
evidence_traceability
```

必须：

```text
不同来源事实丢失 = 0
错误合并不同地点 = 0
```

---

# 14. WP5 — POI Resolution Quality

> 冻结（2026-09-08）：候选打分/Review 与离线指标已实现；真实 POI 质量矩阵暂缓。

目标不是提高自动确认率，而是：

> 优先降低错误确认率。

## 14.1 Ranking Context

扩展：

```text
name
alias
city
province
district
place_type
nearby_landmark
address context
other places in same video
```

同一视频已经确认的地点可以作为：

```text
geographical context
```

辅助判断。

## 14.2 Auto Confirm Gate

Benchmark 核心指标：

```text
auto_confirm_precision
review_rate
unresolved_rate
false_confirm_count
```

强制门槛：

```text
false_confirm_count = 0
```

宁可：

```text
REVIEW
```

也不能：

```text
错误 Pin 到地图。
```

---

# 15. WP6 — Visual Evidence

> 暂缓：没有已验证的 image-capable Profile；Feature Flag 保持关闭。

Vision 属于增强链路。

不得阻塞文字 Pipeline。

## 15.1 Provider 层保持模型无关

新增统一 multimodal message：

```text
text
image
```

业务调用：

```text
SCREENSHOT_UNDERSTANDING
VISUAL_ENTITY_EXTRACTION
DOCUMENT_VISION
```

Router 决定使用：

```text
qwen3.5:9b
qwen3-vl
其他本地视觉模型
Remote Vision
```

禁止：

```text
if model == qwen3.5
```

## 15.2 Vision 不扫描整段视频

禁止：

```text
每秒抽帧
→ 全部送 VLM
```

继续使用：

```text
Transcript
+
Section
+
PlaceMention
↓
定位候选时间段
↓
确定性抽 3～5 帧
↓
质量过滤
↓
Vision 排序 / 理解
```

## 15.3 Visual Claim

支持：

```text
DISH
MENU
PRICE
STOREFRONT
PLACE_SCENE
SIGN
ROUTE_HINT
TICKET
OTHER
```

保存：

```text
frame timestamp
image hash
model
prompt
confidence
claim
provenance=VISUAL_FACT
```

Visual Fact 不允许覆盖 Transcript Fact。

## 15.4 OCR 优先原则

菜单、价格、店招：

```text
Apple Vision OCR
↓
确定性文字
↓
必要时 VLM 做语义解释
```

不要让 VLM 做所有 OCR。

---

# 16. Vision Benchmark

单独建立：

```text
video-vision-golden-v1
```

至少覆盖：

```text
菜品
菜单
价格
店招
景点
路牌
主持人 talking head
转场
黑帧
重复帧
```

指标：

```text
frame_relevance
visual_claim_precision
ocr_accuracy
place_visual_match
duplicate_rejection
```

Vision 默认开启条件：

```text
visual_claim_precision >= 0.90
critical hallucination = 0
且不会明显破坏 16 GB Mac mini 稳定性
```

达不到时保持：

```text
Feature Flag OFF
```

---

# 17. Screenshot 质量升级

当前确定性：

```text
黑帧
过曝
欠曝
模糊
重复
```

保留。

Vision 只作为第二级评分：

```text
Quality Filter
↓
Semantic Relevance
```

目标是把：

```text
“时间点附近最清晰”
```

升级成：

```text
“时间点附近最能解释这一条知识的画面”
```

---

# 18. WP7 — 最终 Benchmark

> 暂缓：等待用户提供合法标注视频和明确的真实 E2E 授权。

至少跑三种配置：

```text
A. qwen3.5:9b Local Only
B. 至少一个已有其他 Local Model
C. 当前可靠配置 Baseline
```

如果还有其他符合 Capability 的本地模型：

```text
全部加入 Matrix
```

Remote 模型可以作为 Quality Reference，但不是本轮通过条件。

---

# 19. Benchmark 输出

生成：

```text
benchmark-results/
  manifest.json
  stage-results.json
  model-comparison.json
  report.md
```

Report 至少展示：

| Stage | Model | Quality | Failure | Latency | Peak RAM |
|---|---|---:|---:|---:|---:|
| Correction | ... | ... | ... | ... | ... |
| Note Map | ... | ... | ... | ... | ... |
| Note Reduce | ... | ... | ... | ... | ... |
| Place | ... | ... | ... | ... | ... |
| Vision | ... | ... | ... | ... | ... |

另展示：

```text
quality / second
quality / GB
```

但不能只按单一综合分排序。

---

# 20. Qwen3.5 9B 默认模型 Gate

Qwen3.5 9B 可以继续作为默认候选。

最终正式成为默认 Profile，需要满足：

```text
所有 Critical Gate 通过

Transcript / Place / Insight
均达到 Minimum Quality Gate

无 Critical Hallucination

Mac mini 不发生 OOM / Worker Kill

运行时间处于可接受区间
```

如果：

```text
qwen3.5 9b 在某 Stage 明显弱于另一模型
```

允许：

```text
FAST_LOCAL_TEXT = Model A
MAIN_LOCAL_TEXT = qwen3.5:9b
```

或者反过来。

这正是保留 Capability Routing 的原因。

---

# 21. 模型下架决策明确不属于本计划

本轮结束时即使得到：

```text
Qwen3.5 9B > Qwen3 8B
```

Agent 也不得：

```text
删除 qwen3:8b
删除 Profile
隐藏 UI
自动 ollama rm
```

只将 Benchmark 结果写入：

```text
model-comparison.json
report.md
```

等待用户决定。

---

# 22. 自动化测试

后端至少新增/加强：

```text
test_video_structured_output.py
test_video_map_reduce.py
test_video_place_insights.py
test_video_insight_evidence.py
test_video_place_aggregation.py
test_video_poi_resolution.py
test_video_model_capability_probe.py
test_video_stage_replay_profiles.py
```

Vision 开发后：

```text
test_video_visual_claims.py
test_video_vision_routing.py
```

---

# 23. 前端测试

至少覆盖：

```text
地点 Insight Card
Insight 时间码跳转
无 Insight
多个 Insight
Review POI
Confirmed POI
多个视频来源
Conflict
Mobile layout
```

---

# 24. 回归要求

工作包结束执行：

```text
backend pytest
Ruff

frontend ESLint
Vitest
TypeScript
Vite build

Alembic isolated upgrade
```

仅涉及已有 Schema 时不创建 migration。

新增持久字段时：

```text
创建新 migration
```

不得修改历史 migration。

---

# 25. Real E2E Acceptance Matrix

最终至少选：

| 样本 | 必验 |
|---|---|
| 平台字幕干净旅行视频 | Subtitle Path |
| 无字幕清晰语音 | Whisper Path |
| 口音 / 地名较多 | Correction |
| 多餐馆探店 | Place + Dish |
| 景区攻略 | Month / Season / Duration |
| 30～60 分钟长视频 | Map/Reduce |
| 同名 POI | Review |
| 同一地点多个视频 | Aggregation |
| 截图可下载 | Screenshot |
| 截图不可下载 | PARTIAL_SUCCESS |

Vision 开启时再加入：

```text
菜单
店招
菜品
景点主体
```

---

# 26. 最终业务验收门

必须全部满足：

## Transcript

```text
时间码合法
Segment 身份稳定
raw/corrected 不混
关键数字/否定语义无破坏
```

## Video Note

```text
完整 Transcript 得到覆盖
不存在只总结前半段
Section 时间递增
所有 Section Evidence 合法
```

## Place

```text
地点可以追溯 Transcript
城市/省份不会错误成为 POI Marker
LLM 不生成经纬度
```

## Insight

```text
推荐菜/看点/月份/时间/价格/提醒可展示
每条重要 Insight 有 Evidence
```

## POI

```text
false auto-confirm = 0
歧义进入 Review
```

## Cross-video

```text
同一 POI 可以聚合
不同来源事实不会静默覆盖
冲突明确保留
```

## Screenshot

```text
黑帧/严重模糊/重复帧过滤
截图存在实际 timestamp
与 Section / Place / Segment 有绑定
```

---

# 27. Agent 执行顺序

严格按以下顺序：

```text
Phase 1
WP0 Benchmark Dataset + Metrics

Phase 2
WP1 Structured Output + Capability Probe

Phase 3
WP2 Video Insight Evidence

Phase 4
第一次 Local Model Benchmark
→ qwen3.5:9b + 当前其他模型

Phase 5
WP3 Insight UX

Phase 6
WP4 Cross-video Aggregation

Phase 7
WP5 POI Quality

Phase 8
第二次完整 Benchmark

Phase 9
WP6 Vision 实验

Phase 10
Vision Benchmark

Phase 11
Real E2E Acceptance

Phase 12
更新文档 / IMPLEMENTATION_STATUS / CURRENT_HANDOFF
```

不得先做 Vision 再补 Benchmark 基础。

---

# 28. 每个 Phase 的 Agent 停止条件

Agent 在一个 Work Package 达到：

```text
目标代码完成
+
目标测试通过
+
相关 Benchmark 可运行
+
文档更新
```

之后停止。

禁止顺手进入下一 Work Package。

这样可以防止一次会话扩散成：

```text
Pipeline
+ UI
+ Vision
+ POI
+ 推荐
+ 地图
```

的大改。

---

# 29. Agent 开始任务提示词

可直接给 Codex：

```text
你正在开发 ThunStorm/do-not-litter 的 codex/mac-mini-implementation 分支。

严格遵守仓库根 AGENTS.md。

本任务只执行：
planning/video/VIDEO_WORKFLOW_BENCHMARK_AND_ACCEPTANCE_PLAN.md 中当前指定的一个 Work Package。

接手顺序：
1. 读 dev docs/CODEX_CONTEXT.md；
2. 读 dev docs/IMPLEMENTATION_STATUS.md；
3. 定位 REGRESSION_AND_CHANGE_GUARD.md 中 video / AI Gateway / Place / Evidence 相关约束；
4. 只读取当前 Work Package 直接涉及的专项文档和源码。

模型硬约束：
- qwen3.5:9b 是待 Benchmark 的本地候选，不是当前默认或唯一允许模型；
- 不得在业务代码硬编码模型名；
- 必须保留 Model Profile / Capability / Stage Policy 的可替换架构；
- 不删除、隐藏、卸载任何已有本地模型；
- 模型优劣必须由本项目 Golden Benchmark 证明；
- 本任务不得根据公开排行榜决定模型去留。

数据硬约束：
- 所有来源事实必须能够追溯到 Transcript Segment 或 Visual Evidence；
- LLM 不得生成地图坐标；
- POI 歧义宁可 REVIEW，不得错误自动确认；
- Source Fact、Visual Fact 和 Personal Inference 不得混淆；
- 不覆盖历史 Note / Transcript / Place Evidence Version。

实施流程：
1. 先列出当前 Work Package 验收条件；
2. 再定位最小影响代码；
3. 编写/更新测试；
4. 实现；
5. 跑目标测试；
6. 跑该 Work Package Benchmark；
7. 满足 Gate 后再跑工作包级全量回归；
8. 更新 IMPLEMENTATION_STATUS；
9. 如用户要求交接，再更新 CURRENT_HANDOFF。

禁止：
- 未授权真实 Provider 调用；
- 未授权真实视频重跑；
- 修改历史 Alembic migration；
- 自动确认 POI；
- 自动删除模型；
- 顺手实现下一 Work Package。

最终只报告：
变更、测试、Benchmark、验收结果、已知限制。
```

---

# 30. 本计划完成后的理想状态

一个视频进入系统后：

```text
视频
↓
可靠 Transcript
↓
完整 Video Note
↓
地点
↓
地点核心 Insight
↓
POI Grounding
↓
地图
↓
来源级 Evidence
↓
关键截图 / Visual Evidence
```

用户看到的不再只是：

```text
“发现陶陶居”
```

而是：

```text
陶陶居

推荐菜
• 虾饺
• 榴莲酥

核心看点
• ...

价格
• ...

推荐时间
• ...

注意事项
• ...

作者评价
• ...

来源
12:43
13:21

[回原视频]
[地图]
[地点详情]
```

当多个视频再次提到该地点时：

```text
同一 Place
↓
多个来源
↓
Consensus + Conflict
↓
逐渐形成长期旅行知识
```

这是本轮视频工作流开发和 Benchmark 的最终验收方向。
