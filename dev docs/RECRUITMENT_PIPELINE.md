# Recruitment Pipeline

## 1. 目标

将招聘公告、微信公众号、官网、PDF、Excel 岗位表，转换为：

- 招聘批次；
- 岗位；
- 报名/考试时间；
- 可执行 Requirement DSL；
- 证据；
- 用户资格判断；
- 缺失 Profile；
- 待办；
- 推荐；
- 冲突提示。

---

# 2. 总流程

```text
URL / File
↓
CAPTURE
↓
RESOLVE_SOURCE
↓
DISCOVER_LINKS
↓
FOLLOW_SOURCES
↓
NORMALIZE_DOCUMENTS
↓
EXTRACT_NOTICE
↓
EXTRACT_POSITIONS
↓
BUILD_REQUIREMENTS
↓
VALIDATE_EVIDENCE
↓
MATCH_PROFILE
↓
GENERATE_DEADLINES
↓
GENERATE_TODOS
↓
RANK / MATERIALIZE
```

---

# 3. 微信 Resolver

优先：

1. 直接 HTTP；
2. Playwright 专用浏览器 Profile；
3. NEEDS_USER。

专用 Browser Profile：

```text
data/browser/profile/
```

不得复用/提交到 Git。
首次用户扫码/登录后持久保存状态。

---

# 4. Link Discovery

招聘公众号常只是入口。

必须提取：
- `<a href>`
- PDF
- XLS/XLSX
- DOC/DOCX
- 官方网站
- 报名入口

规则 + AI 分类：

- FOLLOW
- RECORD_ONLY
- IGNORE
- UNKNOWN

默认：
- max_depth = 2
- max_followed_links_per_source = 30

避免无限爬取。

---

# 5. Source Graph

例如：

```text
公众号汇总
  ├─ references → 政府招聘公告
  │                ├─ attachment → 岗位表.xlsx
  │                └─ registration → 报名入口
  └─ references → 另一官方公告
```

官方附件优先级高于公众号转载。

---

# 6. Document Normalization

统一为：

```text
NormalizedDocument
├─ Metadata
├─ Sections[]
├─ Tables[]
├─ Segments[]
├─ Attachments[]
└─ SourceLocators[]
```

---

# 7. Excel Normalizer

处理：

- 多 Sheet；
- 标题行不固定；
- 合并单元格；
- 隐藏列；
- 备注列；
- 列名差异。

先 openpyxl 读取。

AI 只做 Column Mapping：

```text
岗位名称 → position_name
专业要求 → major_requirement
其他资格条件 → other_requirements
```

不得直接把整本 Excel 当纯文本让模型自由理解。

---

# 8. RecruitmentNotice

字段：

- title
- organization
- region
- registration_start
- registration_deadline
- exam_date
- interview_date
- registration_url
- general_requirements
- sources

---

# 9. Position

字段：

- position_code
- name
- organization
- headcount
- requirements
- source_row

一个 Notice 可包含数百 Position。

---

# 10. Requirement DSL v1.0

节点：

- ALL
- ANY
- NOT
- CONDITION

Condition：

```json
{
  "type": "CONDITION",
  "field": "education_level",
  "operator": "gte",
  "value": "bachelor",
  "rule_type": "HARD",
  "evidence_ids": ["segment_xxx"]
}
```

rule_type：
- HARD
- SEMANTIC
- PREFERENCE

---

# 11. DSL 示例

原文：

> 本科及以上，年龄 35 周岁以下，计算机科学与技术或软件工程专业，具有 PMP 优先。

AST：

```text
ALL
├─ education >= bachelor          HARD
├─ age <= 35                      HARD
├─ ANY
│  ├─ major = 计算机科学与技术     HARD
│  └─ major = 软件工程             HARD
└─ PMP                            PREFERENCE
```

PMP 不参与 Eligibility Fail。

---

# 12. Rule Engine

原子状态：

- PASS
- FAIL
- UNKNOWN
- REVIEW

ALL：

```text
有 FAIL        → FAIL
无 FAIL 有 UNKNOWN → UNKNOWN
无 FAIL/UNKNOWN 有 REVIEW → REVIEW
否则 → PASS
```

ANY：

```text
有 PASS → PASS
全部 FAIL → FAIL
否则有 REVIEW → REVIEW
否则 → UNKNOWN
```

---

# 13. MajorMatcher

优先级：

1. 专业代码精确匹配
2. 指定目录名称精确匹配
3. 专业类包含
4. 官方新旧专业映射
5. 公告明确允许的其他官方映射
6. 语义相似

第 6 级：
**只能 REVIEW，不自动 PASS。**

---

# 14. Catalog Registry

公告若明确指定专业目录：

> 必须优先使用公告指定目录。

本地没有时：
`FETCH_CATALOG`

逐步缓存用户实际遇到的目录，而不是第一版抓全中国所有目录。

---

# 15. EducationExperience

用户可有多个学历阶段。

每条：

- level
- school
- raw_major_name
- mapped_catalog
- mapped_code
- degree
- graduation_date

Requirement scope 支持：

- undergraduate
- graduate
- any_education
- highest_degree

---

# 16. 年龄处理

禁止让 LLM 直接做最终计算。

流程：

```text
原文年龄条件
→ DSL
→ reference_date
→ Python date calculation
→ PASS/FAIL
```

如公告给出“年龄计算截止日期”，必须使用公告日期。

---

# 17. 工作经历

例：

> 具有 2 年以上项目管理相关工作经验

拆：

- duration ≥ 24 months：程序计算；
- domain = project_management：语义判断。

语义不确定：
`REVIEW`

---

# 18. Missing Profile Analyzer

统计所有 UNKNOWN 的原因。

例如：

```text
基层经历未知 → 影响 76 个岗位
政治面貌未知 → 影响 8 个
证书未知 → 影响 3 个
```

优先提问信息收益最大的字段。

---

# 19. Information Gain

基础：

```text
QuestionPriority
≈ affected_positions
× deadline_weight
× position_importance
```

让用户每次补最少信息，解决最多岗位。

---

# 20. Eligibility / Preference / Urgency

三个维度彻底分离。

### Eligibility
- PASS
- FAIL
- UNKNOWN
- REVIEW

### Preference
- HIGH
- MEDIUM
- LOW

### Urgency
- HIGH
- MEDIUM
- LOW

禁止展示混合意义的“92% 匹配度”。

---

# 21. UserState

- DISCOVERED
- INTERESTED
- PREPARING
- APPLIED
- DROPPED

`DROPPED` 后不再持续提醒。

---

# 22. Deadline / Todo

Deadline 来自 Claim。

Todo 分：

- FACT_BASED
- SYSTEM_SUGGESTED

例如：
“8 月 19 日前缴费”是 FACT_BASED。
“建议提前 3 天准备材料”是 SYSTEM_SUGGESTED。

---

# 23. 时间冲突

第一版应检测：

- 报名冲突无需处理；
- 笔试/面试同时间；
- 用户关注岗位之间的显式日期冲突。

未来可加入跨城市交通可达性。

---

# 24. 排序

先分层：

1. PASS
2. REVIEW
3. UNKNOWN
4. FAIL

PASS 内再按：
- Preference
- Urgency

不要统一 1~N 黑盒排名。

---

# 25. Evidence

每条 Requirement 必须绑定原文。

Excel：
- Sheet
- Cell

PDF：
- Page
- Block

网页：
- Segment

用户可从岗位详情点击“查看依据”。

---

# 26. LLM 职责

Qwen 小模型/快速模型：
- 分类；
- 链接分类；
- 列名判断。

主力模型：
- 公告结构化；
- Requirement AST；
- 复杂条件；
- 语义专业条件。

外部模型：
- 本地 Schema 连续失败；
- 低置信；
- 用户手动重跑；
- 高价值歧义。

无论外部模型多强，都不得跳过 Evidence Validator。

---

# 27. 推荐输出 UI ViewModel

RecruitmentDashboardVM：

- nearest_deadline
- action_items
- eligibility_summary
- recommended_positions
- profile_questions
- recent_notices

PositionDetailVM：

- position
- eligibility
- preference
- urgency
- requirement_results
- evidence
- actions
- source_graph

---

# 28. CMS 调试

任务页显示：

- Source Graph
- Pipeline Steps
- 当前模型
- External API 是否调用
- 每步耗时
- 重跑当前步骤
- 使用外部模型重跑
- 查看 Evidence
