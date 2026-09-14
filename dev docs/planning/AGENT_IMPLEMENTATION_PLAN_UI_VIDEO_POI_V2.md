# 至简下一阶段完整 Agent 实施计划
## UI 视觉语言收口 + 视频工作流扩展 + POI Resolution 2.0 + 视频笔记全文检索

> Repository: `ThunStorm/do-not-litter`
> Target branch: `codex/mac-mini-implementation`
> Plan date: `2026-09-12`
> Inspected branch tree SHA: `631e729739986545e73e26e50cd6be45cd559a8a`
> Current migration baseline: `0020_video_note_grounded_sections`
> Nature: **现有稳定架构上的增量升级，不是重构重写**
> Agent rule: **一次只执行一个 Work Package，完成验收即停止，不得顺手进入下一包。**
> Current status: **2026-09-14 已完成 WP0–WP15 源码实施、生产迁移 `0020→0022`、Source/VideoAsset 复用和 Cache Key 稳定性修复，以及真实 Bilibili E2E。** POI Golden 17 例：Top-1/Top-3 1.0、自动确认精度 1.0、错误确认 0、Review 率 0.2353；Video Golden 保持 18 个离线 Fixture。用户样本完成下载、Whisper、时间轴、校对、抽取、Note、POI Review、截图、FTS、COMPACT Profile、Cache Hit 与 force-regenerate；45 个 POI 均未自动确认。Local Video 验证至 ASR；Vision、备用 ASR corpus、fallback、POI 人审晋级和 Browser/390px 未执行。

---

# 0. 计划的来源、优先级与适用方式

本计划综合以下三部分已经明确的需求：

1. 当前会话：
   - UI 大方向可接受，但文字字号、按钮尺寸、输入控件等尚未形成统一视觉语言；
   - POI 人工确认负担仍然偏高；
   - 希望利用省市主题、前后文地点、相邻已确认 POI 等上下文，提高高置信 POI 的自动确认覆盖率；
   - 仍然坚持错误自动确认比进入人工 Review 更不可接受。

2. 《项目对比总结》中的产品方向：
   - 借鉴 BiliNote 的“广输入”能力，但不牺牲现有通用 Capture / AI Workflow；
   - 借鉴灵活的视频笔记输出能力；
   - 借鉴更丰富、可替换的 ASR 能力；
   - 增加对**视频笔记正文全部内容**的全文搜索，而不是只搜标题；
   - **不做视频问答 / RAG**；
   - 当前**不做 Docker、桌面 App、云部署、多用户产品化**；
   - 保持本地 Mac mini + Web 访问作为当前主部署模式。

3. 当前仓库已进入源码的能力：
   - Bilibili 字幕优先、ASR fallback、Transcript 校对与时间轴门禁；
   - Grounded Video Note、地点抽取、Place/POI、截图与 Visual Fact；
   - AI Gateway / Model Profile / Capability / Stage Policy / Budget / Cache / Resource Lock；
   - Job / Step / Artifact / Replay / Partial Success；
   - Map、Place、Place Review、Place Knowledge；
   - 现有 Video Workflow Golden、POI Golden、Vision Golden；
   - 已完成的视频质量 WP0–22 不得重新实现。

## 0.1 文档冲突时的优先级

Agent 遇到冲突时按以下顺序判断：

```text
用户本轮明确要求
    >
AGENTS.md / REGRESSION_AND_CHANGE_GUARD.md 中的安全与冻结约束
    >
当前源码 + 当前自动测试所证明的真实行为
    >
IMPLEMENTATION_STATUS.md
    >
现行专项规格
    >
本计划
    >
历史 planning / history 文档
```

本计划**不能授权 Agent 破坏仓库硬约束**。

若本计划与当前源码实际情况不一致：

1. 不猜；
2. 先用目标源码与目标测试确认；
3. 记录差异；
4. 只在不改变产品语义的情况下做兼容调整；
5. 若需要重新做产品选择，则停止当前 Work Package 并报告。

---

# 1. 总体目标

这一阶段不是继续堆功能，而是让目前已经具备的能力形成更稳定、更易扩展、更少人工介入的产品闭环：

```text
任意受支持的视频输入
        ↓
统一 Source / Snapshot / VideoAsset
        ↓
字幕优先 / 可替换 ASR
        ↓
可信 Transcript / Evidence
        ↓
Grounded 地点与事实抽取
        ↓
Context-aware POI Resolution 2.0
        ↓
Canonical Place / Place Knowledge
        ↓
Grounded Video Note
        ↓
可选择的 Note Render Profile
        ↓
全文搜索 / 地图 / Review / Evidence 回跳
```

最终希望达到四个结果：

### A. UI
用户在设置、视频笔记、地点审核、地图等页面看到的是同一套视觉语言，而不是每个页面自己决定字号、按钮大小和圆角。

### B. POI
人工 Review 从“常规步骤”变成“真正存在歧义时的异常步骤”。

### C. 视频工作流
视频来源与 ASR Provider 可扩展，但所有来源最终继续走**一条**现有 Pipeline。

### D. 笔记
同一套 Grounded Evidence 可以形成不同阅读风格，同时支持中文视频笔记正文全文检索，不引入 RAG 或 Vector DB。

---

# 2. 明确不做的内容

本计划范围内明确禁止 Agent 实施：

```text
视频 RAG / 视频问答
向量数据库
知识图谱重构
Docker 产品化
桌面 App / Tauri 产品化
SaaS / 多用户
云 Worker
多 Worker 调度重构
完整自动行程规划
推荐指数评分体系重做
自动修改或删除用户已人工确认的 POI
LLM 直接生成真实地图坐标
LLM 直接决定真实高德 POI ID
用视觉识别覆盖 Transcript 来源事实
为了支持多视频来源建立第二套 Source / Job / VideoNote 数据模型
为了灵活笔记输出建立第二套 Note 数据库
为了 ASR 多 Provider 绕过现有 Worker / Resource Lock
```

对 BiliNote 的借鉴只采用**能力思想**，不复制其产品部署形态，也不把当前项目改造成 BiliNote 的结构。

---

# 3. 当前系统必须保留的架构边界

Agent 在所有 Work Package 中必须持续满足以下不变量。

## 3.1 数据身份不变量

以下身份必须继续分离：

```text
Source
Snapshot
Segment
Claim
Evidence

Job
Step
Artifact

公开 Note ID: note_*
版本 ID: ntv_*

Raw Transcript
Corrected Transcript

PlaceMention
Canonical Place
MapMarkerState
```

禁止为了“简化”将它们合并成一张大表或 JSON Blob。

## 3.2 长任务不变量

以下工作不得运行在 API 请求主链路：

- 视频下载；
- 音频提取；
- ASR；
- LLM；
- Vision；
- 大规模 Note re-render；
- 批量 POI re-resolution。

必须进入 Worker / Job。

## 3.3 Evidence 不变量

所有来源事实必须能回到：

```text
Source
→ Snapshot / VideoAsset
→ Transcript Segment / Screenshot
→ timestamp / source link
```

AI 推断不得伪装成来源事实。

## 3.4 Migration 不变量

- 当前历史 migration 到 `0020` 均视为已发布；
- **禁止修改任何旧 migration**；
- 新 Schema 必须新建 migration；
- 当前仓库已有“空库升级在旧 0019 历史迁移上存在既有问题”的记录，本计划不得通过篡改旧 migration 偷偷修复；
- 新 migration 至少必须验证从可信 `0020` 基线升级成功。

## 3.5 Secrets 不变量

任何新增 Provider：

- API Key 不进入 SQLite 明文；
- 不进 URL；
- 不进日志；
- 不进前端 localStorage；
- 复用现有 Secret Store / Keychain 机制。

---

# 4. 本轮核心架构决策

## 4.1 不建立第二套视频流水线

新的来源必须采用：

```text
Capture
→ existing Source/Snapshot
→ VideoSourceAdapter
→ Normalized Video Descriptor / VideoAsset
→ existing Transcript / Evidence / Note / Place Pipeline
```

而不是：

```text
YouTubePipeline
DouyinPipeline
LocalVideoPipeline
BilibiliPipeline
```

四套彼此独立的系统。

平台差异只允许存在于：

- URL / 文件解析；
- Metadata；
- Subtitle 获取；
- 登录态；
- Media 获取；
- Timestamp URL；
- 平台特有错误码。

下游 Transcript / Note / Place / POI 不感知平台实现细节。

---

## 4.2 ASR 扩展使用 Provider 契约，不在 Video Pipeline 硬编码引擎

目标结构：

```text
TranscriptAcquisitionStrategy
    ├─ Platform Subtitle
    └─ ASRProviderRegistry
          ├─ Existing Whisper
          ├─ MLX Whisper（若当前 Mac 环境验证通过）
          ├─ Faster Whisper（若资源与依赖验证通过）
          └─ Remote ASR（未来/可选）
```

Video Pipeline 只声明：

```text
需要可带时间码的中文 Transcript
```

不应写：

```python
if engine == "mlx":
    ...
elif engine == "faster_whisper":
    ...
```

散落在业务流程中。

---

## 4.3 灵活笔记输出不改变 Evidence 基座

不能为了“精简笔记 / 详细笔记 / 旅行攻略”重新创造互不兼容的语义模型。

目标：

```text
Grounded Evidence Bundle
        ↓
Grounded Note Generation
        ↓
Note Render Profile
        ↓
Markdown Presentation
```

Note Profile 改变的是：

- 信息密度；
- Section 展示；
- bullet / paragraph 风格；
- screenshot 是否展示；
- timestamp link 的展示方式；
- 概览长度。

不能改变：

- 事实来源；
- Evidence 绑定；
- Place identity；
- 原始 Transcript；
- 历史 Note Version。

---

## 4.4 视频全文搜索使用确定性全文索引，不引入 RAG

用户本轮需要的是：

> 搜索所有视频笔记正文内容。

不是：

> 与全部视频知识进行语义问答。

因此首选：

```text
SQLite FTS5
```

并针对中文明确做 tokenizer 能力检测。

不得因为 FTS5 中文分词麻烦直接上：

- Chroma；
- Milvus；
- Elasticsearch；
- pgvector；
- Embedding RAG。

---

## 4.5 POI Precision 始终优先于 Coverage

优化目标：

```text
先保证 false auto-confirm 接近 0
再提升 auto-confirm coverage
```

绝对禁止：

```text
为了减少 Review
→ 简单把 85 阈值降到 70
```

正确方式：

```text
给正确候选更多可信上下文
+
给错误候选更多负证据
+
提高候选生成质量
+
保留风险门禁
```

---

# 5. POI Resolution 2.0 目标模型

## 5.1 现有 Resolver 已有能力

当前 Resolver 已经存在自动确认，不需要从零实现。

当前大致逻辑：

```text
候选搜索
→ 名称 / 城市 / 省 / 区 / 类型 / nearby / 同视频上下文评分
→ Top1 / Top2
→ 风险门禁
→ AMap detail 二次确认
→ CONFIRMED 或 REVIEW
```

当前自动确认门禁应继续作为初始安全基线：

- 总分不足；
- name_match 不够；
- 无 geo support；
- category 不兼容；
- Top1/Top2 gap 不足；
- 坐标异常；

均不得自动确认。

---

## 5.2 第一优先修复：Place Type → AMap Category 映射缺口

地点抽取允许的类型包含：

```text
RESTAURANT
SCENIC_AREA
NEIGHBORHOOD
PEDESTRIAN_STREET
BUSINESS_DISTRICT
MARKET
PARK
MUSEUM
TEMPLE
VILLAGE
TOWN
LANDMARK
ACCOMMODATION
TRANSIT
OTHER
```

当前 Resolver 类型匹配覆盖并不完整。

由于 `category_match` 缺失会直接导致 Review，所以以下类型必须首先核对：

```text
NEIGHBORHOOD
PEDESTRIAN_STREET
VILLAGE
TOWN
LANDMARK
OTHER
```

### 硬规则

Agent **不得凭记忆填写高德 typecode**。

必须：

1. 查当前高德 POI 类型规范；
2. 为每一类决定：
   - 可安全映射；
   - 只能宽类型映射；
   - 不应作为强类型门禁；
3. 写 fixture；
4. 再修改 Resolver。

`OTHER` 不允许因为“没有具体类别”永久阻断所有自动确认；但它也不能变成“任何高德类别都算匹配”。应单独定义弱类型策略。

---

## 5.3 Geo Context 层级

统一使用以下优先级：

```text
1. mention 自身明确的 province/city/district
2. 当前 Section / 相邻 Transcript Window 的明确地理信息
3. 当前 Geo Session 内已经确认的 POI
4. 当前 Geo Session 的 dominant region / coordinate cluster
5. 整个视频的弱 region hint
6. 无限制全局搜索
```

高层级冲突时，低层级不得覆盖高层级。

例如：

```text
mention 明确说“丽江”
但视频多数内容在昆明
→ 丽江优先
```

---

## 5.4 Geo Session

多城市视频不得继续使用“整条视频所有地点共用一个上下文集合”。

建议新增运行时模型：

```python
GeoSession:
    id
    start_ms
    end_ms
    explicit_region
    inferred_region
    anchor_place_ids
    anchor_coordinates
    confidence
    transition_reason
```

Geo Session 可以由以下信号建立/切换：

- 明确城市/省份变化；
- “第二天去了……”
- “从昆明到大理……”
- “下一站……”
- 已确认锚点出现明显地理跳变；
- Section 地理主题明确变化。

### 注意

Geo Session 首版可以是**运行时结构 + resolver metadata**。

除非确实需要跨 Job 查询，不要一开始就为它新建复杂关系表。

---

## 5.5 两阶段 Resolver

### Pass 1：Seed Resolution

先找极强地点：

- 名称高度唯一；
- mention 明确 city/district；
- 类型吻合；
- Top1/Top2 gap 足够；
- 坐标有效；
- AMap detail 有效。

这些地点成为：

```text
Confirmed Geo Anchors
```

### Pass 2：Contextual Resolution

再处理：

- 缺 city_hint；
- ASR 轻微错字；
- 别名；
- 只说街道/商圈；
- “附近那家店”；
- 地点名短且可能重名。

使用 Pass 1 的锚点建立 Local Geo Cluster。

---

## 5.6 Candidate Generation 应先使用上下文，而不是只在评分阶段补分

候选生成顺序：

```text
Query A:
raw/canonical name + explicit city

Query B:
normalized name / alias + explicit city

Query C:
name + inferred Geo Session city

Query D:
around(anchor coordinates) + keyword
仅在语义明确含附近/旁边/对面/步行等关系时优先

Query E:
global text search
只用于兜底
```

所有结果按 `provider_id` 去重。

每个候选保存 provenance：

```text
raw_name_query
alias_query
explicit_city_query
context_city_query
around_query
global_query
```

---

## 5.7 多查询一致性投票

同一个 Provider POI 若在多种独立查询中反复位于 Top1，是强证据。

示例：

```text
原始名 Top1 = A
别名 Top1 = A
city_limit Top1 = A
around Top1 = A
```

可增加：

```text
query_consensus_count
query_consensus_ratio
```

反之：

```text
原始名 → A
city_limit → B
around → C
```

属于强风险，不应通过简单总分自动确认。

---

## 5.8 负证据

Resolver 不能只有“符合就加分”。

至少建立以下负证据：

```text
cross_city_conflict
type_conflict
district_conflict
far_from_geo_cluster
chain_branch_ambiguity
candidate_disagreement
name_semantic_conflict
coordinate_outlier
```

示例：

```text
原文：某古镇
候选：某古镇大酒店
→ type/name semantic conflict
```

---

## 5.9 连锁品牌单独策略

以下情况不得使用普通非连锁地点的门禁：

```text
瑞幸
星巴克
喜茶
全季
汉庭
麦当劳
肯德基
大型连锁商场/品牌
```

只有当至少存在以下强分店信息之一时才允许自动确认：

- 分店名；
- 商场名；
- 街道；
- district；
- nearby landmark；
- 极强 Geo Cluster；
- 唯一 provider branch identity。

否则进入 Review。

---

## 5.10 历史人工确认复用

已有人工确认是最高价值的未来 Resolver 证据之一。

后续 mention 如果满足：

```text
normalized name / alias 高匹配
+
geographic scope 兼容
+
历史 Place 有 external_provider + external_poi_id
```

可优先复用已有 Canonical Place。

禁止：

```text
仅因为名字相同
→ 跨城市自动复用
```

---

## 5.11 Confirmation Origin

为以后重新评估算法，确认结果必须区分来源：

```text
AUTO_STRONG
AUTO_CONTEXTUAL
MANUAL_CONFIRMED
```

UI 可都显示为“已确认”，但后台必须知道确认来源。

原则：

- `MANUAL_CONFIRMED` 不允许普通 Replay 静默覆盖；
- `AUTO_CONTEXTUAL` 可在明确执行 re-audit/re-resolution 时重新评估；
- `AUTO_STRONG` 若 Provider identity 仍有效，一般稳定保留；
- 所有变化有 audit reason。

若当前 PlaceMention metadata 已能可靠承载且可查询需求很低，可先不加列；若后续 Review/统计必须 SQL 查询，则再通过新 migration 正规化。

---

## 5.12 用户纠错进入 Golden

当发生：

```text
系统推荐 A
用户确认 B
```

应生成可离线复现的 regression fixture 内容：

- mention raw/canonical name；
- source context；
- city/province/district hint；
- candidate A/B 必要字段；
- feature vector；
- old decision；
- manual decision；
- resolver version。

注意：

- 不保存 Secret；
- 不复制不必要的完整 Transcript；
- Golden 可由显式脚本导出；
- 首版不需要“在线机器学习”。

---

# 6. UI 一致性目标

现有 `FRONTEND_VISUAL_DESIGN_SYSTEM.md` 继续作为规范，不重新设计视觉风格。

## 6.1 统一 Typography

继续使用现有语义层级：

```text
Display      40/40
H1 Desktop   31/38
H1 Mobile    20/28
H2           22/30
H3 / Panel   18/25
Body         14/22
Dense        13/20
Meta         12/18
Caption      11/16
Micro        10/14
```

Agent 不能因为某页面“看起来差一点”继续新增：

```text
17px
19px
15.5px
```

等私有字号。

---

## 6.2 Controls

建议统一：

```text
Dense Button / Input: 36px
Default Button / Input: 40px
High-emphasis special control: 46px（极少使用）
IconButton: 36 / 40
```

移动端主要触控目标不得低于设计规范。

---

## 6.3 Shared Components

逐步建立或补齐：

```text
frontend/src/components/ui/
    Button.tsx
    IconButton.tsx
    TextField.tsx
    SearchField.tsx
    SelectMenu.tsx
    Badge.tsx / Chip.tsx（按实际重复程度决定）
```

现有：

```text
ConfirmDialog.tsx
FilterMenu.tsx
```

优先复用和扩展，不重复创建相似组件。

---

## 6.4 不进行大爆炸式 CSS 重写

`global.css` 当前较大，禁止一次 Work Package：

```text
把所有样式重写成新体系
```

正确方式：

1. 先补 token；
2. 建 shared primitive；
3. 按页面簇迁移；
4. 每一簇做 Browser 验收；
5. 最后清理确认无引用的 legacy selector。

---

# 7. 多视频来源架构

## 7.1 VideoSourceAdapter 契约

建议建立统一抽象，具体命名以当前代码习惯为准：

```python
class VideoSourceAdapter(Protocol):
    def can_handle(self, input) -> bool: ...
    def resolve(self, source, snapshot) -> NormalizedVideoDescriptor: ...
    def fetch_metadata(self, descriptor) -> VideoMetadata: ...
    def fetch_subtitle_tracks(self, descriptor) -> list[SubtitleTrack]: ...
    def obtain_media(self, descriptor, requirement) -> MediaArtifact: ...
    def build_timestamp_url(self, descriptor, seconds) -> str | None: ...
```

Adapter 只做平台接入。

明确禁止 Adapter：

- 调 LLM；
- 创建 Note；
- 创建 Place；
- 做 POI Resolution；
- 绕过 Source/Snapshot；
- 自己管理独立 Job 状态。

---

## 7.2 Normalized Descriptor

至少应统一：

```text
platform
platform_video_id
canonical_url
title
author
duration_ms
cover
published_at
subtitle_tracks
media_capabilities
timestamp_link_capability
auth_requirement
provider_metadata
```

Provider-specific metadata 必须放 namespaced metadata，不把每个平台所有字段塞入核心 Schema。

---

## 7.3 错误码统一

来源 Adapter 至少规范到：

```text
SOURCE_UNSUPPORTED
AUTH_REQUIRED
MEDIA_UNAVAILABLE
SUBTITLE_UNAVAILABLE
RATE_LIMITED
HOST_BLOCKED
PROVIDER_TEMPORARY_FAILURE
INVALID_SOURCE
```

Replay 是否可用仍由后端决定。

---

## 7.4 推进顺序

### 第一阶段
现有 Bilibili 逻辑迁入 Adapter 契约，行为不得变化。

### 第二阶段
Local Video。

原因：

- 不依赖第三方登录；
- 不依赖网络；
- 最适合证明 Adapter 真正与平台解耦。

### 第三阶段
YouTube。

### 后续 gated
Douyin / Kuaishou 等平台只在以下条件全部满足后加入：

- 有稳定 fixture；
- URL Policy 明确；
- 登录/访问方案合法且可维护；
- 下载策略不会绕过安全限制；
- 错误能稳定归一化；
- 不需要复制一套业务 Pipeline。

---

# 8. ASR Provider 架构

## 8.1 Provider 输出必须统一

```python
TranscriptArtifact:
    segments
    language
    timestamps
    provider
    model
    provider_version
    source_media_hash
    confidence_metadata
```

无论 Provider 是：

- 当前 Whisper；
- MLX Whisper；
- Faster Whisper；
- 未来 Remote ASR；

下游都只读取统一 TranscriptArtifact。

---

## 8.2 Transcript Acquisition Policy

推荐：

```text
可信平台字幕
→ 直接 normalize

可疑/生成字幕
→ 按当前安全门禁决定是否强制 ASR

无字幕
→ Preferred ASR Provider

Provider failure
→ 仅在 Policy 允许时 fallback
```

禁止无提示地从 Local-only 自动升级远程 Provider。

---

## 8.3 Provider 扩展顺序

本阶段不追求一次性支持 BiliNote 全部引擎。

建议：

```text
1. 抽象 Registry
2. 把当前 Whisper 包进统一接口
3. 引入一个适合 Mac mini 的本地候选
4. Benchmark
5. 再决定是否加入第二个本地候选
6. Remote ASR 只作为可配置扩展
```

任何默认 Provider 切换必须由项目 Benchmark 证明。

---

## 8.4 ASR Benchmark 不只看 WER

旅行视频更应该关注：

```text
place_entity_recall
proper_noun_accuracy
timestamp_alignment
segment_continuity
hallucination_rate
runtime
peak_memory
failure_recovery
```

尤其是：

> 是否漏掉快速说出的地点。

这应成为 ASR 比较的重要指标。

---

# 9. 灵活 Note Output

## 9.1 推荐首批 Profile

```text
CURRENT_DEFAULT
COMPACT
DETAILED
TRAVEL_GUIDE
```

但这些只是输出 Profile，不是四套 Pipeline。

---

## 9.2 Profile 可以控制

- 总览长度；
- Section 详细度；
- bullet 密度；
- Place Insight 展示；
- timestamp 链接显示；
- screenshot 显示策略；
- 是否展示注意事项等辅助块。

---

## 9.3 Profile 不可以控制

- 是否允许编造事实；
- 是否跳过 Evidence；
- 是否改变 Place identity；
- 是否覆盖旧 Note Version；
- 是否绕过 Grounded Evidence；
- 是否改变 Transcript。

---

## 9.4 版本策略

用户重新选择 Profile 并生成时：

```text
same note_*
→ new ntv_*
```

不得覆盖历史版本。

如当前 NoteVersion 已有可复用的 style/profile 字段，应扩展而不是重复建表。

只有确认当前 Schema 无法表达时才新增 migration。

---

# 10. 视频笔记全文搜索

## 10.1 搜索范围

本轮索引：

- Note title；
- 当前可见 Note Version 的 Markdown/body；
- Section title；
- Place names；
- 必要的结构化 Note text。

默认不索引：

- 历史隐藏版本；
- Raw Transcript；
- Deleted Note；
- Secret / internal logs。

---

## 10.2 SQLite FTS5 中文策略

Agent 必须首先在**生产等价 Python SQLite**验证：

```sql
SELECT sqlite_version();
```

并验证：

```text
FTS5
trigram tokenizer
```

是否可用。

### Preferred

若 `trigram` 可用：

```text
FTS5 + trigram
```

适合中文子串搜索。

### Fallback

若 production SQLite 不支持 trigram：

1. 不引入外部向量数据库；
2. 使用应用层 deterministic CJK n-gram normalization；
3. 将 bigram/trigram token 写入 FTS shadow field；
4. 短关键词可 fallback 到受控 LIKE 查询。

禁止直接把未经 escape 的用户输入拼进 `MATCH`。

---

## 10.3 Index 生命周期

```text
Note materialized
→ index

新 ntv 成为 current
→ 原 current index 原子替换

Note soft delete
→ remove from visible index

restore
→ reindex

hard retention cleanup
→ 与 Note 生命周期一致
```

---

## 10.4 Search API

建议：

```text
GET /api/video-notes/search?q=&page=&page_size=
```

或按现有 API 设计风格落位。

返回至少：

```text
note_id
current_version_id
title
matched_section
snippet
matched_place_name
source_title
```

前端点击应进入当前 Note，并尽可能定位对应 Section。

---

# 11. 实施 Work Packages 总览

严格按以下顺序执行：

```text
WP0  冻结基线、指标与冲突保护
WP1  POI 类型映射与 Review 原因可观测性
WP2  POI Resolver Feature Model / Shadow Mode
WP3  Geo Session + Seed / Context Propagation
WP4  Context-aware Candidate Generation + Consensus + Negative Evidence
WP5  Canonical Reuse + Confirmation Origin + Re-resolution Safety
WP6  Place Review 批量快速确认 UX + Correction Golden Loop
WP7  UI Token / Shared Control Foundation
WP8  UI Page-cluster Migration + Visual Acceptance
WP9  VideoSourceAdapter 抽象并无行为迁移 Bilibili
WP10 Local Video Adapter
WP11 YouTube Adapter
WP12 ASR Provider Registry + Alternate Local ASR Benchmark
WP13 Note Render Profiles
WP14 Video Note Full-text Search
WP15 Cross-cutting Regression / Real Acceptance Preparation / Documentation Closure
```

任何 Agent 会话只能执行其中一个 WP。

---

# 12. WP0 — 冻结基线、指标与冲突保护

## 目标

在改变任何行为之前，建立本阶段统一可验证基线。

## Preflight

Agent 只读：

```text
AGENTS.md
dev docs/CODEX_CONTEXT.md
dev docs/IMPLEMENTATION_STATUS.md
REGRESSION_AND_CHANGE_GUARD.md 中：
    video
    transcript
    evidence
    place
    POI
    map
    frontend
    migration
相关条目
```

然后定位：

```text
video_support.py
video_pipeline.py
providers/amap.py
PlaceReviewCard.tsx
global.css
FRONTEND_VISUAL_DESIGN_SYSTEM.md
poi-resolution-golden-v1.json
video-workflow-golden-v1.json
```

不要扫描整个仓库。

## 实施

### 1. 记录当前 POI baseline

至少输出：

```text
candidate_recall_at_1
candidate_recall_at_3
auto_confirm_precision
auto_confirm_rate
review_rate
wrong_confirm_count
```

### 2. 记录 UI inventory

只统计重复出现的：

- font-size；
- control height；
- button padding；
- border-radius；
- icon-button dimensions。

不要在本 WP 修改 UI。

### 3. 记录 Video baseline

确认当前：

```text
Bilibili → subtitle/ASR → corrected transcript
→ place extraction → POI
→ grounded note → screenshots
```

目标测试通过。

### 4. 增加本阶段验收文档区

将本计划加入 repository 后，必要时在文档目录登记。

## 验收

- 不改变任何业务行为；
- 当前 POI Golden 与 Video Golden 结果被记录；
- 所有后续 WP 有可对比 baseline。

## 禁止

- 调 Prompt；
- 调 POI threshold；
- 改数据库；
- 重跑真实视频；
- 调真实 AMap/LLM。

## Stop condition

Baseline 完成后立即停止。

---

# 13. WP1 — POI 类型映射与 Review 原因可观测性

## 目标

解决“因为类型映射缺失导致天然无法自动确认”的低风险高收益问题。

## 主要文件

预期涉及：

```text
backend/src/zhijian/services/video_support.py
backend/src/zhijian/providers/amap.py
backend/tests/test_poi_resolution_benchmark.py
dev docs/benchmark/poi-resolution-golden-v1.json
```

实际以代码定位为准。

## 实施步骤

1. 将 Place Type → Provider category/typecode mapping 从 scoring 函数内部散落常量中抽离；
2. 建立单一映射来源；
3. 核对当前高德 typecode；
4. 补齐可明确映射类型；
5. 对宽泛类型定义：
   - strong category match；
   - weak compatible；
   - incompatible；
6. `OTHER` 不能自动成为强 match；
7. candidate explanation 中展示 category 判定；
8. Review reason 明确显示：
   - `CATEGORY_UNMAPPED`
   - `CATEGORY_CONFLICT`
   - `CATEGORY_WEAK_ONLY`
   等稳定 reason code。

## Golden 新增

至少覆盖：

- neighborhood；
- pedestrian street；
- village；
- town；
- landmark；
- OTHER；
- 同名 hotel vs scenic landmark；
- 类型缺失但名字+城市极强。

## Gate

```text
wrong_confirm_count == 0
auto_confirm_precision 不下降
candidate_recall_at_3 不下降
```

允许 Review rate 改善，但不能以 precision 换 coverage。

## Rollback

类型 mapping 与门禁应集中，若某一类导致 false confirm，可单独降级为 weak/review，不回滚整个 Resolver。

---

# 14. WP2 — Resolver Feature Model + Shadow Mode

## 目标

先重构“可解释 feature”，暂时不改变生产 decision。

## 建议结构

```python
ResolutionFeatureVector:
    name_match
    city_match
    province_match
    district_match
    category_match
    nearby_landmark_match
    query_consensus_count
    candidate_gap
    coordinate_valid
    cross_city_conflict
    chain_risk
    distance_to_cluster_m
    prior_confirmation_match
```

## 原则

Score 可以保留，但 Auto Confirm 不再只理解一个总分。

应当：

```text
features
→ score
→ hard risk gates
→ decision
```

## Shadow Mode

新增 Resolver v2 计算路径：

```text
旧 resolver decision = authoritative
新 resolver decision = shadow only
```

记录：

- 是否一致；
- v2 想自动确认但 v1 Review；
- v1 想自动确认但 v2 Review；
- candidate Top1 是否变化。

Shadow 数据只用于测试/benchmark，不要求永久存生产库。

## 验收

同一 Golden：

- v1 行为完全不变；
- v2 feature 输出 deterministic；
- repeated run 得到完全相同结果。

---

# 15. WP3 — Geo Session + Seed / Context Propagation

## 目标

把“整条视频一个城市上下文”升级成“局部地理上下文”。

## Runtime 设计

构建：

```text
Transcript / Sections
→ Geo Signals
→ Geo Sessions
→ Seed Anchors
→ unresolved mentions inherit local context
```

## 地理信号来源优先级

1. mention explicit hints；
2. grounded section geo；
3. transcript transition phrase；
4. manual/auto confirmed place；
5. video dominant region。

## LLM 使用边界

允许 LLM 识别：

```text
“第二天来到大理” = region transition
“就在翠湖旁边” = nearby relation
```

但输出只能是：

```text
semantic relation / region hint
```

不得输出 AMap POI ID 或坐标事实。

尽量优先复用已有 place extraction 的 resolver_context；如果规则即可识别，则不要新增 LLM 调用。

## Seed

只使用：

```text
AUTO_STRONG
或
MANUAL_CONFIRMED
```

作为高权重 anchor。

`AUTO_CONTEXTUAL` 不应在同一轮无限递归放大自身推断。

建议最大 propagation depth = 1。

## 关键风险

防止：

```text
错误 contextual auto confirm
→ 成为 anchor
→ 污染后续 10 个地点
```

因此第一版必须限制 anchor 信任级别。

## Golden

至少：

- 昆明 → 大理转场；
- 同一个 city 多 section；
- mention 无 city 但邻近 anchor 明确；
- 开头北京、后半上海；
- 视频标题写云南但 section 明确在贵州；
- 两个城市交界/跨区域路线。

---

# 16. WP4 — Context-aware Candidate Generation + Consensus + Negative Evidence

## 目标

让上下文直接改善“搜什么”，而不仅是“搜完之后加几分”。

## Candidate pipeline

```text
explicit city query
→ alias query
→ session inferred city query
→ around query（满足 nearby relation）
→ global fallback
→ dedupe provider_id
→ feature extraction
```

## around

现有 fixed radius 不应长期硬编码。

建议按 relation 配置有限离散档：

```text
VERY_NEAR / 对面 / 隔壁
NEAR / 附近
WALKABLE / 步行可达
REGIONAL / 同片区
```

首版实际半径必须由 fixture/Provider 行为验证，不要随意设巨大范围。

## Consensus

聚合同一 provider_id 的 query provenance。

增加：

```text
consensus_count
top1_count
query_diversity
```

## Negative evidence

至少实现：

- cross-city conflict；
- type conflict；
- chain branch ambiguity；
- far-from-cluster；
- contradictory district；
- query disagreement。

## 决策等级

Shadow 阶段输出：

```text
AUTO_STRONG
AUTO_CONTEXTUAL
REVIEW
UNRESOLVED
```

## Promotion gate

只有当扩充 Golden 后满足：

```text
wrong_confirm_count == 0
auto_confirm_precision == 1.0（当前 Golden）
且新增真实纠错样本无 regression
```

才能考虑把 v2 decision 从 shadow 切为 authoritative。

切换应为一个清晰 commit，不要和 feature 开发混在一起。

---

# 17. WP5 — Canonical Reuse + Confirmation Origin + Re-resolution Safety

## 目标

减少重复确认，并确保自动化升级不会覆盖人工确认。

## Existing Place reuse

查询已有 Place：

```text
external_provider
external_poi_id
aliases
normalized names
geographic scope
```

优先级：

```text
exact provider_id
>
historically confirmed alias + compatible geo
>
normal AMap resolution
```

## Manual Confirmation

人工确认后必须保留：

```text
decision origin
decision time
resolver version
candidate
reason/features
```

具体存储方式先审查当前 metadata/audit 是否足够。

### Schema 决策原则

只有出现以下查询需求才正规化成列/表：

- 按确认来源批量筛选；
- 后续 re-audit；
- 统计 auto/manual coverage；
- 纠错 Golden 导出。

否则避免过早扩张 Schema。

## Re-resolution

普通 replay：

- 不覆盖 `MANUAL_CONFIRMED`；
- 不自动解绑 canonical Place；
- 不因为新版 Resolver 分数变化修改人工选择。

单独的 explicit re-audit 才允许重新评估 AUTO 类型。

---

# 18. WP6 — Review 快速确认 UX + Correction Golden Loop

## 目标

即使必须人工确认，也把成本从“研究一张复杂卡片”降到“快速判定真正歧义项”。

## 复用现有 PlaceReviewCard

不要新建另一套 Review UI。

扩展：

### 顶部只突出

```text
地点名
系统首选候选
为什么没有自动确认
来源一句话
地区 / 与 anchor 距离
```

### Candidate 展开后才显示

- provider id；
- 完整地址；
- match feature；
- score detail；
- transcript context；
- screenshot。

## Review reason

用户看到的是可理解文本，例如：

```text
同名地点存在 2 个，候选差距不足
这是连锁品牌，缺少分店信息
视频当前在昆明，但候选位于曲靖
地点类型与候选 POI 不一致
```

不要只显示数字 `82.5`。

## Batch Flow

支持：

```text
确认首选 → 自动进入下一条
选择其他候选 → 下一条
不是地点 → 下一条
暂时跳过
```

按：

- Geo Session；
- city；
- source video；

聚合显示。

## Human-as-new-anchor

人工确认后：

- 只允许触发同 Geo Session 中剩余 `REVIEW/UNRESOLVED` 的 resolver-only refresh；
- 不重新 ASR；
- 不重新 Note Generation；
- 不修改其他已 confirmed mention。

此操作若较重，进入 Worker / Replay step。

## Golden Loop

提供显式 developer script：

```text
export_poi_correction_fixture
```

把人工纠错转成脱敏 fixture 草稿。

不要自动无审查提交 Golden。

---

# 19. WP7 — UI Token / Shared Control Foundation

## 目标

建立统一视觉语言底座，但暂不大范围迁移所有页面。

## 实施

### CSS Token

补齐现有设计系统定义到实际 CSS token。

例如：

```text
--text-h1-desktop
--text-h1-mobile
--text-h2
--text-panel
--text-body
--text-dense
--text-meta

--control-height-dense
--control-height-default
--control-height-emphasis

--radius-control
--radius-panel
```

实际命名以项目现有 token 命名习惯为准。

### Shared Components

实现最小可用：

```text
Button
IconButton
TextField
SearchField
SelectMenu
```

避免一次引入大型 UI framework。

## 测试

- variants；
- disabled；
- loading；
- aria；
- keyboard；
- mobile touch target。

## 禁止

- 改品牌色；
- 改整体布局；
- 改地图交互模型；
- 全局搜索替换 CSS。

---

# 20. WP8 — UI Page-cluster Migration + Visual Acceptance

## 目标

用 shared primitives 收口实际页面。

## 迁移顺序

建议按风险：

```text
1. Settings
2. Place Review / Places
3. Video Notes
4. Capture / Tasks
5. Map toolbar / route controls
```

每个 cluster 可以独立 commit；若 Agent 会话较小，可将 WP8 再拆成 WP8A–E。

## 验收

Desktop + Mobile：

- 字号层级一致；
- 主要按钮同高度；
- icon button 同尺寸；
- 搜索框一致；
- Dropdown 一致；
- focus ring 可见；
- 文本不溢出；
- 不因 compact 改造导致触控目标过小。

## CSS cleanup

只有确认 selector 无引用后再删除 legacy style。

不得为追求“代码漂亮”删除仍被旧页面使用的 alias。

---

# 21. WP9 — VideoSourceAdapter 抽象 + Bilibili 无行为迁移

## 目标

先证明平台抽象可用，不新增平台。

## 实施

1. 从现有 Bilibili resolver 中识别平台专属职责；
2. 建 VideoSourceAdapter contract；
3. Bilibili 实现该 contract；
4. Pipeline 改为从 registry 获取 adapter；
5. 现有 Bilibili login/subtitle/media/host policy 保持；
6. Job Step 名称尽量不变，避免 Replay 历史兼容破坏。

## Compatibility Gate

同一 Bilibili Fixture：

```text
metadata
subtitle selection
transcript
place extraction
note
screenshots
job terminal status
```

必须与改造前兼容。

## 禁止

本 WP 不加 YouTube。

先证明“抽象没有改变 Bilibili”。

---

# 22. WP10 — Local Video Adapter

## 目标

支持用户上传本地视频进入同一视频 Pipeline。

## Intake

复用现有 file Capture。

禁止创建：

```text
/local-video-upload
```

另一套入口，除非现有 Capture 无法表达 MIME/large-file requirements。

## 处理

```text
uploaded file
→ Source/Snapshot
→ LocalVideoAdapter
→ metadata
→ no platform subtitle
→ ASR
→ existing transcript/evidence pipeline
```

## Source link

本地视频没有公网 timestamp URL 时：

- 不伪造链接；
- 若项目已有可安全本地播放入口，可生成 in-app timestamp；
- 否则显示时间码但无外链。

## Retention

继续服从现有 temporary media retention。

不要永久保存整段视频只是为了以后截图。

---

# 23. WP11 — YouTube Adapter

## 目标

在不复制 Pipeline 的情况下增加第二个网络视频平台。

## 安全

URL Policy 只允许明确 YouTube host。

不得把任意 URL 直接交给 yt-dlp 形成 SSRF/下载器。

## 获取策略

优先：

```text
官方/可用字幕
→ transcript
```

无字幕：

```text
media/audio
→ ASR
```

## Auth

首版优先支持无需登录的公开视频。

需要 cookie/login 的能力若复杂，留为独立后续 WP，不能拖累公共视频主链路。

## Timestamp

统一由 Adapter build timestamp link。

## 验收

至少：

- 有字幕公开长视频；
- 无字幕视频；
- unavailable/private；
- rate limit；
- malformed URL；
- source deletion/unavailable；
- title/cover；
- timestamp jump。

---

# 24. WP12 — ASR Provider Registry + Alternate Local ASR Benchmark

## 目标

建立真正可替换 ASR，同时保持默认不盲目变化。

## Step 1

把当前 ASR 包成 Provider。

业务结果应完全兼容。

## Step 2

增加 Provider Registry / Selection Policy。

## Step 3

选择**一个**符合当前 Mac mini 环境的备用本地 ASR 候选实施。

不要一口气加入 4–5 个引擎。

## Resource

必须复用现有 resource lock。

重型任务：

```text
Whisper / Local LLM / Vision
```

仍不能无控制并发。

## Benchmark

至少加入：

- 普通普通话旅行介绍；
- 快速连续地点名；
- 专有名词；
- 背景音乐；
- 多人对话；
- 10 分钟以上连续视频片段。

输出：

```text
place_entity_recall
proper_noun_accuracy
timestamp_alignment
runtime
peak_memory（可取近似测量）
failure count
```

## 默认切换

只有新 Provider Benchmark 明显不低于当前默认，并通过稳定性门禁，才能改默认。

否则标记：

```text
VALID_ALTERNATIVE
```

---

# 25. WP13 — Note Render Profiles

## 目标

增加用户可选择的输出风格，同时不破坏 grounded note。

## Preflight

先检查当前：

- note style 字段；
- prompt supplement；
- NoteVersion metadata；
- renderer；
- MarkdownContent。

不要重复设计已有能力。

## Profile

首批：

```text
CURRENT_DEFAULT
COMPACT
DETAILED
TRAVEL_GUIDE
```

## Implementation

尽量采用：

```text
Profile config
+
grounded generation constraints
+
deterministic post-render
```

不要为每种 Profile 各复制一份巨大 Prompt。

## Regenerate

切 Profile：

```text
new Note Version
```

不得覆盖旧 ntv。

## Cache

AI Cache key 必须包含：

```text
profile_id
profile_version
```

避免不同 Profile 错误命中同一 cache。

---

# 26. WP14 — Video Note Full-text Search

## 目标

搜索不仅匹配标题，还匹配正文、Section 与地点名。

## Step 1 — Runtime Probe

验证 production-equivalent SQLite：

- FTS5；
- trigram tokenizer。

## Step 2 — Schema

如采用 FTS5，新建 migration。

不要修改 0020。

## Step 3 — Backfill

对现有可见 current note 生成 index。

Backfill 必须：

- 可重复；
- 幂等；
- 失败可继续；
- 不调用 LLM；
- 不重新生成 Note。

## Step 4 — Sync

在 Note materialization / current-version switch / delete / restore 时保持同步。

## Step 5 — API

分页、query escaping、snippet。

## Step 6 — UI

视频笔记列表搜索框变为：

```text
标题 + 正文 + Section + 地点
```

搜索结果提示：

```text
“正文命中”
“地点命中”
“标题命中”
```

## 中文测试

至少：

- “昆明”
- “文林街”
- “菌子”
- 正文出现但标题不出现的短语；
- section 标题；
- place alias；
- 2 个汉字短词；
- 特殊字符；
- 空 query；
- 超长 query。

## 禁止

- 加 embedding；
- 加 Chat；
- 加 RAG endpoint。

---

# 27. WP15 — Cross-cutting Regression / Acceptance / Documentation Closure

## 自动验证

按仓库规则：

### Backend

先目标测试，再一次：

```text
pytest backend/tests -q
Ruff
```

### Frontend

一次：

```text
ESLint
Vitest
TypeScript
Vite build
```

### Benchmarks

至少：

```text
POI Resolution Golden
Video Workflow Golden
AI Gateway related target tests
Vision Golden（若本轮未改 vision，只做防回归）
```

## 关键回归场景

### POI

1. 唯一景区；
2. 同名景区；
3. 同城同名店；
4. 连锁门店；
5. mention 缺城市；
6. 快速 ASR 错字；
7. alias；
8. 附近地标；
9. 昆明→大理多城市视频；
10. 以前人工确认过的 Place 再出现；
11. 用户从系统推荐 A 改成 B；
12. AMap 无结果。

### Video

1. 旧 Bilibili 成功样本；
2. Bilibili 登录需求；
3. 平台字幕；
4. ASR；
5. Local Video；
6. YouTube subtitle；
7. YouTube ASR fallback；
8. Provider failure；
9. Replay；
10. PARTIAL_SUCCESS。

### Note

1. 旧 Note 不变；
2. Profile regenerate 产生新 ntv；
3. timestamp Evidence 正常；
4. screenshot 正常；
5. 全文搜索正文命中；
6. delete 后搜索不可见；
7. restore 后可重新检索。

### UI

Desktop + Mobile：

- Settings；
- Video Note；
- Place Review；
- Map；
- Capture/Search。

---

# 28. 生产真实验收门禁

自动测试通过**不等于真实验收通过**。

以下动作需要用户明确授权：

- 真实高德 API；
- 真实 Bilibili 新视频重跑；
- 真实 YouTube 视频；
- Remote LLM；
- Remote ASR；
- 生产 DB migration；
- 服务重启；
- 历史 Note/POI 批量 re-resolution。

Agent 不得以：

```text
fixture 通过
```

描述为：

```text
生产已验证
```

---

# 29. POI 上线策略

POI Resolution 2.0 建议按四阶段 rollout：

## Phase A — Shadow

```text
v1 决策 authoritative
v2 只算结果
```

## Phase B — Benchmark Promotion

当：

```text
false auto-confirm = 0
precision 不下降
真实 correction fixtures 无 regression
```

再晋级。

## Phase C — AUTO_STRONG

只让最强 v2 case 自动确认。

`AUTO_CONTEXTUAL` 仍进入 Review。

## Phase D — AUTO_CONTEXTUAL

只有积累足够真实样本后才开放。

因此不允许一个 commit 直接：

```text
全面启用全部 context auto-confirm
```

---

# 30. 数据库与 Migration 策略

每个新 Schema 需求必须先回答：

1. 是否当前 metadata 已足够？
2. 是否需要 SQL 查询/排序/统计？
3. 是否具有长期稳定业务语义？
4. 是否跨 Job / Replay 需要？

只有 2–4 中有明确需求才优先正规化。

## 可能新增但不是强制全部新增

```text
confirmation_origin
resolver_version
render_profile_id / version
FTS table
```

Geo Session / feature vector 第一版尽量是 runtime / audit metadata，避免过度建模。

---

# 31. Backward Compatibility Checklist

每个 WP 提交前逐项判断：

- [ ] 旧 Bilibili URL 仍可处理；
- [ ] 已存在 Note 仍可读取；
- [ ] `note_*` / `ntv_*` 语义未变；
- [ ] 旧 Replay 不因为 Step rename 失效；
- [ ] `MANUAL_CONFIRMED` 不被自动覆盖；
- [ ] Map hidden 不删除 Place；
- [ ] Evidence timestamp 不丢；
- [ ] current Place/provider identity 不重复；
- [ ] Source retention 不因新 Adapter 改变；
- [ ] 本地模型名称没有被业务代码硬编码；
- [ ] LOCAL_ONLY 不会偷偷远程 fallback；
- [ ] Secret 未进入日志/数据库明文；
- [ ] 新 migration 没有修改历史 migration；
- [ ] 未经授权没有真实 Provider call。

---

# 32. 性能与资源约束

Mac mini 当前是唯一支持后端。

因此：

## ASR / LLM / Vision

重任务继续遵守资源锁。

## POI

Context-aware resolver 应避免：

```text
每个 mention × 10 query × 20 candidates
```

无限放大请求。

建议：

- Query 去重；
- Candidate provider_id 去重；
- Geo Session 复用；
- 已有 Place 先本地命中；
- around 只在语义需要时使用；
- 失败使用 backoff；
- 不为了多投票机械重复相同 query。

## Search

FTS query 分页；
不把整个 Markdown 全量返回给列表页。

---

# 33. Logging / Observability

新增能力必须使用已有审计/日志体系。

## POI

记录：

```text
resolver_version
decision
reason_codes
candidate_count
query_count
selected_provider_id（允许）
feature summary
duration
```

不要记录完整敏感 Prompt。

## Adapter

记录：

```text
platform
step
normalized error code
duration
```

## ASR

记录：

```text
provider
model
duration
media hash
segment count
fallback chain
```

## Search

只记录：

- latency；
- result count；

默认不记录用户完整搜索词到长期日志，除非现有隐私规范允许且有必要。

---

# 34. Agent Git / 工作区安全规则

每个 Work Package 开始：

```bash
git status --short
git branch --show-current
git rev-parse HEAD
```

如果工作区已有与当前 WP 无关的修改：

- 不 revert；
- 不 stash 用户工作；
- 不格式化整个仓库；
- 只改当前 WP 必要文件。

## Commit

建议：

```text
1 WP = 1 logical commit
```

大 WP 可拆：

```text
contract/test
implementation
frontend
```

但不要把多个 WP 混进同一 commit。

禁止：

- force push；
- 重写历史；
- 自动 merge；
- 未授权 push；
- 自动 production deploy。

---

# 35. 每个 Work Package 的统一执行模板

Agent 开始任何 WP 时使用：

```text
你正在开发：
ThunStorm/do-not-litter
branch: codex/mac-mini-implementation

严格遵守仓库根 AGENTS.md。

本次只执行本计划中的：WP<X> — <名称>

开始前：
1. git status --short / branch / HEAD；
2. 读 dev docs/CODEX_CONTEXT.md；
3. 读 dev docs/IMPLEMENTATION_STATUS.md；
4. rg 定位 REGRESSION_AND_CHANGE_GUARD.md 中与本 WP 直接相关的条目；
5. 只读当前 WP 所需专项文档和目标源码，不扫描无关目录；
6. 对照本计划中的 Backward Compatibility Checklist。

实施原则：
- 先冻结验收条件；
- 优先补目标测试/fixture；
- 一次只改一个明确能力；
- 不顺手重构无关代码；
- 不建立平行 Pipeline；
- 不改历史 migration；
- 不覆盖人工确认或历史 Note Version；
- 不调用未经授权的真实 Provider；
- 如果源码与计划不一致，先验证真实行为再做兼容调整。

验证：
1. 目标单测 / lint；
2. 当前 WP Benchmark；
3. 完成后按 AGENTS.md 规定进行一次必要的全量验证；
4. 前端行为变化才做 Browser PC + Mobile 验收；
5. 不把 fixture 结果描述成生产 E2E。

完成时只报告：
- 改了什么；
- 为什么这样改；
- 测试 / Benchmark；
- backward compatibility；
- migration 状态；
- 未验证项；
- 下一 WP 是什么。

完成本 WP 后立即停止，不得自行进入下一 WP。
```

---

# 36. 推荐执行批次

虽然 WP 有严格顺序，但为了降低一次会话上下文压力，可按下面批次交给 Codex/Agent。

## Batch 1 — POI P0

```text
WP0
WP1
```

目的：

最快降低“本来可以确认但类型门禁导致 Review”的人工量。

---

## Batch 2 — POI Resolution 2.0 Core

```text
WP2
WP3
WP4
WP5
WP6
```

每个 WP 单独执行，不一次提交。

---

## Batch 3 — UI Consistency

```text
WP7
WP8
```

---

## Batch 4 — Video Input Expansion

```text
WP9
WP10
WP11
WP12
```

顺序不可反：

> 先抽象，再加平台；先 Registry，再加新 ASR。

---

## Batch 5 — Note Experience

```text
WP13
WP14
```

---

## Batch 6 — Closure

```text
WP15
```

---

# 37. 本阶段最终验收指标

## POI

硬门禁：

```text
wrong auto-confirm = 0 on Golden
```

推荐目标：

```text
Auto Confirm Precision >= 99% on representative real-reviewed corpus
```

Coverage 是第二指标。

最终人工队列应主要剩：

- 连锁分店真实歧义；
- 同名地点；
- 跨城市冲突；
- 高德数据缺失；
- 上下文不足。

---

## Video

- Bilibili 现有链路零功能回退；
- Local Video 与 YouTube 进入同一下游 Pipeline；
- ASR Provider 可替换；
- 不硬编码 Provider/model；
- Replay / Partial Success 语义保持。

---

## Note

- 多 Profile 不改变 Evidence；
- 历史 ntv 不覆盖；
- 中文正文全文搜索可用；
- 无 RAG / Vector DB。

---

## UI

- 常用页面不再拥有各自独立字号/按钮体系；
- Shared control 成为新增代码默认入口；
- Desktop/Mobile 保持可用。

---

# 38. 结束条件

本计划全部完成后，系统应从：

```text
“已经有很多独立能力”
```

进入：

```text
“同一套架构可以稳定吸收更多视频来源，
并把大多数明确 POI 自动落到 Place，
只有真正歧义需要用户，
同时 UI 与笔记阅读体验已经形成统一产品语言。”
```

最重要的成功标准不是功能数量，而是：

```text
新增一个视频平台
不需要重写 Note / Place / POI；

新增一个 ASR
不需要修改业务 Pipeline；

新增一种笔记风格
不需要复制 Evidence；

提高 POI 自动化
不会降低错误确认门禁；

新增 UI 页面
不再产生第五套按钮和字号；
```

如果达不到这些条件，即使功能表面完成，也不能视为本阶段成功。

---

# 39. Agent 封版要求

最终 WP15 完成并且用户明确要求封版时，Agent 才执行：

1. 更新 `IMPLEMENTATION_STATUS.md`：
   - 只记录真正进入源码并通过自动验证的能力；
2. 更新相关专项规格；
3. 若用户要求写交接，再更新 `CURRENT_HANDOFF.md`；
4. 如 source set 发生变化，按仓库规则重建 `COMPLETE_PROJECT_SPEC.md`；
5. `git diff --check`；
6. 最终状态中明确：
   - 自动测试；
   - Benchmark；
   - Browser 验收；
   - 真实 Provider 验收；
   - 生产迁移；
   - 生产重启；
   分别是否执行。

不得把“代码已完成”写成“生产已上线”。
