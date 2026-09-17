# PLAN C — 季节地图、可解释推荐与 Visual Fact

> 前置：Plan A、Plan B 完成。  
> 对应方向：**3 月份/季节地图、4 可解释推荐系统、8 Visual Fact**。

---

# 1. 总体目标

让地图从：

```text
“我收集了哪些地点”
```

升级成：

```text
“现在/某个月去哪”
+
“哪些更适合我”
+
“为什么”
```

同时利用已有视频截图增加视觉事实，但视觉信息永远作为补充 Evidence，不覆盖 Transcript Evidence。

---

# 2. 顺序

严格按照：

```text
WP-C1 时间筛选
↓
WP-C2 Preference / Recommendation
↓
WP-C3 Recommendation UI
↓
WP-C4 Visual Fact
↓
WP-C5 Vision Benchmark
```

不要先做 Vision。

原因：

> 文本知识链路必须先稳定，才能判断视觉信息究竟增加了多少价值。

---

# 3. WP-C1：月份 / 季节地图

复用现有 Visit Window 数据。

支持：

```text
月份
季节
具体日期
```

最小版本先实现月份：

```text
1 月 ... 12 月
```

地图筛选示例：

```text
10 月值得去
10 月不推荐
10 月关闭/受限制
全年适合
时间未知
```

---

# 4. 时间窗口语义

统一成可计算状态：

```text
BEST
GOOD
POSSIBLE
CAUTION
CLOSED
UNKNOWN
```

原始 Evidence 不修改。

示例：

```text
“10 月中下旬红叶最好”
→ BEST

“6-8 月丰水期”
→ GOOD

“冬季封山”
→ CLOSED
```

如果现有模型已有等价语义，优先复用，不建立第二套状态系统。

---

# 5. API

地图查询扩展：

```text
month
date
visit_window_state
```

示意：

```text
GET /.../map?...&month=10
```

具体 Route 遵循现有 API 命名。

返回 Marker 时增加：

```text
visit_window_summary
visit_window_state
visit_window_reason
```

---

# 6. 前端

地图增加轻量筛选：

```text
时间：全年 | 1月 ... 12月
```

Marker/详情显示：

```text
10 月：最佳
原因：红叶观赏期
```

不要让用户理解内部 Window Schema。

---

# 7. WP-C2：Preference Event

实现推荐前先检查现有数据结构。

复用或补齐：

```text
SAVE
DISMISS
VISITED
PLANNED
LIKE
DISLIKE
```

推荐计算使用：

```text
Explicit > Behavior > Inferred
```

第一版禁止使用复杂 Embedding 推荐系统。

---

# 8. Trait Model

Place Trait 第一版保持有限集合：

```text
nature
urban
historic
food
hiking
island
commercial
crowded
local
luxury
budget
family
nightlife
```

根据现有 Place Knowledge 推导 Trait。

每个 Trait 必须可以追溯到：

```text
明确地点属性
来源事实
用户行为
```

---

# 9. WP-C3：可解释推荐

推荐分数可在后端内部计算，但 UI 不显示：

```text
87%
92%
```

UI 只显示：

```text
优先关注
值得考虑
一般
不符合偏好
```

每个推荐必须返回理由。

例如：

```text
✓ 自然景观
✓ 10 月正值最佳观赏期
✓ 你经常收藏徒步地点
△ 游客较多
```

---

# 10. 推荐评分组成

建议使用确定性评分：

```text
Trait preference
+
Visit window
+
User state
+
Source consensus
+
Conflict penalty
```

例如：

```text
Preference match       +3
Current month BEST     +3
CONSENSUS              +2
PLANNED                 +1
CONFLICT                -1
CLOSED                  hard exclude
DISMISSED               hard exclude/default hide
```

具体权重需要通过 Fixture 固定，避免代码中散落 magic number。

---

# 11. 推荐系统边界

第一版不做：

```text
协同过滤
用户画像 Embedding
黑盒 LLM 排序
全自动旅行规划
```

LLM 可以生成解释文本，但：

> 排序结果必须由确定性数据决定。

---

# 12. 推荐地图体验

地图支持：

```text
全部地点
优先关注
值得考虑
本月适合
本月最佳
```

Place Detail 增加：

```text
为什么推荐给你
```

并明确区分：

```text
来源事实
系统判断
个人偏好推断
```

---

# 13. WP-C4：Visual Fact

Vision 不分析整个视频。

只处理已永久保留的：

```text
evidence frames
note screenshots
thumbnail（必要时）
```

优先目标：

```text
店招
菜单
菜名
价格
营业时间
路牌
景区告示
```

---

# 14. Visual Fact 数据结构

视觉模型输出独立事实：

```text
VisualFact
```

至少包含：

```text
fact_type
value
confidence
frame_id
timestamp
provider
model
model_version
source_id
```

并关联截图 Evidence。

禁止 Visual Fact：

```text
覆盖 Transcript Claim
覆盖作者观点
静默修改 Place canonical data
```

---

# 15. Transcript / Vision 冲突

示例：

```text
字幕：人均 80
菜单截图：套餐 128
```

不要判断谁“正确”。

保存：

```text
Transcript Observation
Visual Observation
```

Knowledge Aggregator 输出：

```text
CONFLICT / DIFFERENT_CONTEXT
```

根据事实类型决定是否属于真正冲突。

---

# 16. Vision Profile

继续复用 AI Gateway：

```text
VISION_FACT
```

Stage 必须：

```text
显式 Vision-capable Profile
```

若当前模型不支持 Vision：

```text
SKIPPED_UNSUPPORTED
```

不得把文本模型失败记录成普通 Pipeline Failure。

---

# 17. WP-C5：Vision Benchmark

复用 Plan A Benchmark 基础。

增加小型 Golden：

```text
菜单
店招
价格牌
营业时间
路牌
```

指标：

```text
fact precision
fact recall
OCR/entity accuracy
evidence linkage
hallucination count
```

门禁：

```text
严重幻觉 = 0
```

Vision Benchmark 未通过时：

> Visual Fact 保持实验性，不进入默认视频流水线。

---

# 18. 成本控制

Vision 必须限制调用量。

默认：

```text
每个主要 Place 少量候选截图
```

先做确定性筛选：

```text
清晰度
重复帧
黑帧
曝光
时间邻近
```

再调用 Vision。

不要逐帧分析视频。

---

# 19. UI

Place Knowledge Card 增加证据来源 Icon/标签：

```text
字幕
截图
多来源
系统归纳
```

Visual Fact 示例：

```text
菜单截图显示：招牌牛肉面 ¥28
[查看截图]
```

用户必须可以回到原始 Evidence。

---

# 20. Benchmark 联动

最终 Recommendation Benchmark 至少加入：

```text
月份筛选准确性
推荐排序稳定性
推荐解释完整率
Consensus 加权正确性
Conflict penalty
Visual Fact precision
```

本地模型是否承担：

```text
Trait extraction
Recommendation explanation
Visual Fact
```

由 Plan A 的 Stage Benchmark 决定。

---

# 21. 完成标准

### 季节地图

- [ ] 12 月份筛选可用
- [ ] BEST/GOOD/CAUTION/CLOSED 等语义稳定
- [ ] Marker 可解释“为什么这个月适合”
- [ ] Evidence 可追溯

### 推荐

- [ ] Preference Event 可重算
- [ ] Trait Model 可解释
- [ ] 推荐不是黑盒 LLM 排序
- [ ] UI 不展示虚假百分比
- [ ] CONSENSUS/CONFLICT 参与排序
- [ ] 推荐理由可追溯

### Vision

- [ ] Visual Fact 独立于 Transcript Claim
- [ ] Vision Profile 能力检查存在
- [ ] 不支持视觉时正确 Skip
- [ ] Vision Golden 与评分器存在
- [ ] 不逐帧分析视频
- [ ] Evidence 可查看
- [ ] 严重视觉幻觉门禁为 0

### 工程

- [ ] 后端全量 pytest 通过
- [ ] 前端 verify 通过
- [ ] 新 migration 从空 SQLite 可升级
- [ ] Benchmark 无质量回退
- [ ] IMPLEMENTATION_STATUS.md 更新
- [ ] 完成项归档，不继续扩大 CURRENT_HANDOFF

---

# 22. 建议提交拆分

```text
feat: add month-aware place filtering
feat: add travel visit-window map semantics
feat: add deterministic preference scoring
feat: add explainable place recommendations
feat: add visual fact evidence model
feat: integrate vision fact extraction
test: add recommendation and vision benchmark cases
docs: record travel intelligence implementation status
```

---

# 23. 三阶段最终产品链路

全部完成后：

```text
视频 / 图文
↓
Transcript / Evidence
↓
PlaceMention
↓
POI Resolution
↓
Place
↓
Cross-source Knowledge
↓
Consensus / Conflict
↓
Visit Window
↓
Preference Match
↓
Explainable Recommendation
↓
Map / Place Knowledge Card
        ↑
   Visual Fact 补充
```

最终原则：

> **先保证事实可信，再自动确认；先形成地点知识，再做推荐；Vision 永远补充证据，不替代证据。**