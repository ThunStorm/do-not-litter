# PLAN B — POI 自动确认与地点知识聚合

> 前置：Plan A 已完成。  
> 对应方向：**1 POI 自动确认率、2 地点知识卡 2.0、10 来源可信度/共识强度**。

---

# 1. 核心目标

把当前：

```text
视频
→ PlaceMention
→ POI Review
→ Place
```

升级为：

```text
PlaceMention
→ Context-aware POI Resolution
→ Place
→ Cross-source Knowledge
→ Consensus / Conflict
→ Place Knowledge Card
```

目标不是“尽量自动确认”，而是：

> **在不明显增加误确认的情况下提高自动确认覆盖率。**

Precision 优先于 Recall。

---

# 2. 执行前最小读取

```text
AGENTS.md
dev docs/CODEX_CONTEXT.md
dev docs/IMPLEMENTATION_STATUS.md
dev docs/product/TRAVEL_FOOD_PIPELINE.md
```

然后定位：

```bash
rg -n "AMapPOIProvider|PlaceMention|PlaceInsight|provider_poi|CONFIRMED|REVIEW|UNRESOLVED" \
  backend/src backend/tests frontend/src/features/map
```

重点代码区域：

```text
backend/src/zhijian/db/models.py
backend/src/zhijian/domain/
backend/src/zhijian/services/
backend/src/zhijian/api/
backend/alembic/versions/
frontend/src/features/map/
```

不要预设新的服务文件名；以实际代码为准。

---

# 3. WP-B1：POI Resolver Benchmark

在改算法之前先增加数据集。

Fixture 至少覆盖：

```text
唯一店名
连锁店
同名景区
同城同名店
转写错字
简称
别名
城市明确
城市缺失
附近地标存在
视频中多个地点形成地域上下文
```

指标：

```text
candidate_recall@1
candidate_recall@3
auto_confirm_precision
auto_confirm_rate
review_rate
unresolved_rate
wrong_confirm_count
```

核心门禁：

```text
wrong_confirm_count = 0
```

Golden 数量逐步扩展，不要求一次覆盖全国。

---

# 4. WP-B2：Context-aware POI Scoring

改进候选评分，但保持确定性和可解释。

候选分数来源：

### Name

```text
canonical name
raw name
aliases
normalized name
```

### Geographic Context

```text
province
city
district
adcode
nearby landmark
other places from same video
```

### Category

例如：

```text
餐馆
景区
街区
商场
市场
住宿
交通
```

### Provider Identity

已有 Provider POI ID 时优先稳定复用，不重复创造 Place。

---

# 5. POI Score Explanation

每个候选内部生成解释：

```json
{
  "name_match": 0.92,
  "city_match": true,
  "district_match": true,
  "category_match": true,
  "nearby_context": ["xxx"],
  "cross_place_context": ["xxx"]
}
```

UI 不一定展示原始数字，但后端测试和 Review 页面必须能够诊断为什么进入：

```text
CONFIRMED
REVIEW
UNRESOLVED
```

---

# 6. WP-B3：自动确认策略

不要使用一个简单 `score > x`。

至少满足组合门禁，例如：

```text
strong name
AND geographic context
AND category compatible
AND top1 与 top2 有足够差距
```

风险场景强制 Review：

```text
连锁门店
同名 POI
跨城市冲突
候选差距过小
类型冲突
坐标异常
上下文不足
```

禁止：

```text
LLM 直接生成地图坐标
LLM 直接确认现实 POI
```

LLM 只提供语义上下文。

---

# 7. WP-B4：Place Knowledge Card 2.0

Place Detail 从“地点信息”升级成“地点知识”。

每个地点至少汇总：

```text
核心看点
推荐菜 / 核心体验
价格
排队
环境
最佳月份/季节
营业/开放限制
注意事项
作者态度
来源数量
```

必须区分：

```text
SOURCE_FACT
SOURCE_OPINION
SYSTEM_AGGREGATION
PERSONAL_INFERENCE
```

不要把 AI 聚合文字伪装为来源原话。

---

# 8. WP-B5：跨来源归一化

同一地点不同来源可能表达：

```text
“人均八十”
“约 80 元”
“七八十”
```

先做 normalize，再判断是否一致。

按事实类型采用不同策略：

### 数值

```text
价格
等待时间
票价
```

允许区间。

### 枚举

```text
推荐
不推荐
拥挤
清静
```

### 时间

```text
月份
花期
雪季
开放期
```

### 文本

```text
菜品
看点
体验
```

使用标准化实体/标签，而不是整句字符串比较。

---

# 9. WP-B6：共识与冲突模型

现有状态继续扩展：

```text
SINGLE_SOURCE
CONSENSUS
CONFLICT
```

规则必须可解释。

示例：

```text
3 个独立来源推荐同一道菜
→ CONSENSUS

两个来源分别说“几乎不用排队”和“排队 2 小时”
→ CONFLICT

只有一个来源
→ SINGLE_SOURCE
```

不要简单按照“出现次数”计算可信度。

同时考虑：

```text
source_id 去重
时间
事实类型
Evidence 是否完整
```

---

# 10. 时间新旧语义

对于容易变化的事实：

```text
价格
营业时间
排队
菜单
门票
```

保留历史 Observation。

默认展示：

```text
最新有效信息
+
历史变化提示
```

例如：

```text
当前来源：约 ¥120
较早来源：约 ¥80
```

不要覆盖旧 Evidence。

---

# 11. WP-B7：API

在现有 Place API 上扩展，避免复制新的平行数据模型。

Place Detail 应提供类似：

```json
{
  "place": {},
  "knowledge": {
    "highlights": [],
    "dishes": [],
    "visit_windows": [],
    "warnings": [],
    "prices": []
  },
  "consensus": {},
  "sources": []
}
```

具体字段名称必须遵循现有 API 风格。

---

# 12. WP-B8：前端

重点修改：

```text
frontend/src/features/map/PlaceDetailPage.tsx
frontend/src/features/map/PlaceReviewsPage.tsx
```

Knowledge Card 建议结构：

```text
地点名称
一句话简介

核心看点
推荐菜 / 体验
最佳时间
价格 / 排队
注意事项

来源共识
────
✓ 多来源一致
△ 单一来源
! 来源存在冲突

查看证据
```

Review 页面增加：

```text
候选差异
城市/区县
类型
上下文
为什么需要确认
```

---

# 13. 数据迁移原则

优先复用：

```text
Place
PlaceMention
PlaceInsightItem
Evidence
provider identity
visit windows
```

只有确实无法表达的新数据才增加字段/表。

如需迁移：

- 创建当前 Alembic head 之后的新 revision；
- 禁止修改历史 migration；
- 新字段必须有兼容默认值；
- 隔离 SQLite 从空库完整升级测试。

---

# 14. Benchmark Gate

Plan A 的 Benchmark 增加 POI Quality 维度。

上线候选必须满足：

```text
wrong auto-confirm = 0
auto_confirm_rate 不低于旧版本
candidate recall@3 不下降
Place knowledge evidence coverage >= 90%
```

如果提高 auto-confirm rate 导致错误确认：

> 立即回退阈值。

---

# 15. 完成标准

- [ ] POI Resolver 有 Golden
- [ ] 自动确认率可量化
- [ ] 错误自动确认受到强门禁
- [ ] POI Score 可解释
- [ ] Place Detail 可跨来源聚合
- [ ] SINGLE_SOURCE / CONSENSUS / CONFLICT 完整
- [ ] 易变化信息保留时间语义
- [ ] Evidence 可直接跳转
- [ ] Review 页面解释更清楚
- [ ] Benchmark 纳入 POI Quality
- [ ] 后端全量测试通过
- [ ] 前端 verify 通过
- [ ] 更新 IMPLEMENTATION_STATUS.md

---

# 16. 建议提交拆分

```text
test: add poi resolution golden cases
feat: improve contextual poi resolution
feat: add explainable poi review reasons
feat: aggregate cross-source place knowledge
feat: add place consensus and conflict semantics
feat: enhance place knowledge card
docs: record poi and place knowledge completion
```

完成后进入 `PLAN_C_TRAVEL_RECOMMENDATION_AND_VISION.md`。