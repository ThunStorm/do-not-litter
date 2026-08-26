# Control Center

## 1. 定位

Control Center 不是普通 CMS，而是：

> **本地 AI 处理系统的控制台、任务观察台、证据审计台与配置后台。**

它属于 MVP 核心功能。

---

# 2. 第一版页面

1. Dashboard
2. Tasks
3. Sources
4. Settings

后续：
- Profile & Preference
- POI Review
- Evidence Audit
- Model Benchmarks
- Source Watch

---

# 3. Dashboard

展示：

- Processing
- Queued
- Failed
- Needs User
- Today Done
- Recruitment processing
- Travel processing
- GPU 当前任务
- 最近错误

例：

```text
Processing      2
Queued          5
Failed          1
Needs User      1

贵州43景区
POI 31/43

事业编公告
解析岗位表.xlsx
```

---

# 4. Tasks

每个 Job 展示：

- title
- type
- status
- step
- progress
- priority
- created
- runtime
- model
- external API used?
- errors

操作：

- 从错误步骤继续（Artifact 有效时）
- 完整重跑（独立动作）
- cancel
- 查看 Replay Cache 保留截止/复用步骤/重跑步骤
- rerun from step
- external model rerun
- view logs

---

# 5. Pipeline View

Recruitment：

```text
✓ RESOLVE_WECHAT
✓ DISCOVER_LINKS
✓ RESOLVE_OFFICIAL
✓ PARSE_EXCEL
✓ EXTRACT_NOTICE
✓ EXTRACT_POSITIONS
✓ BUILD_REQUIREMENTS
● MATCH_PROFILE
○ GENERATE_TODOS
```

Travel：

```text
✓ METADATA
✓ AUDIO
✓ ASR
✓ TRANSCRIPT
● POI 31/43
○ PREFERENCE
○ MATERIALIZE
```

---

# 6. Sources

显示：

- 原始链接；
- Snapshot；
- 正文；
- 附件；
- 下钻关系；
- Source authority；
- Claim/Evidence；
- 原始视频时间码；
- PDF 页码；
- Excel Cell。

---

# 7. Settings

## General
- data directory
- cache limit
- cleanup policy
- worker concurrency
- LAN enable / bind address / port
- LAN access token rotate
- allowed origins

## AI
- mode: local/cloud
- provider
- model mapping
- API Key
- Base URL
- connection test
- outbound data policy / per-run sensitive authorization
- Transcript Correction 能力角色、主/备用模型、校对 Prompt 版本与真实测试

## ASR
- engine
- model
- mode
- GPU test

## Browser
- profile status
- login status
- clear/reset profile

## POI
- provider（MVP: AMap）
- 高德 JS API Key
- 高德 Security Code
- 高德 Web 服务 Key
- 三项配置状态与真实测试
- 域名白名单和浏览器端凭据可见性提示
- country/region preference
- coordinate system（China: GCJ02）

## Recruitment
- source crawl depth
- max links
- catalog policy

## Travel
- auto POI threshold
- review threshold
- screenshot count / quality / max video bytes
- China map initial viewport（不可设置硬编码默认城市）
- Marker hidden/deleted management

---

# 8. Cache Management

显示：

- permanent data
- AI models
- temp video
- temp audio
- temp frames

支持：
- clean cache
- auto clean
- size limit

---

# 9. Evidence Audit

未来/Phase 2 可加强：

点 Claim：

```text
Claim
→ Evidence
→ Source
→ 原始 Snapshot
```

支持“报告错误”和单步重跑。

运行日志中的 `ERROR/CRITICAL` Job 事件查询 Replay Options。中间产物有效时提供“从错误步骤继续”，复用上游完成步骤并顺次执行当前/下游；过期时只提供“完整重跑”。日志页不能直接更改步骤或 Provider，完整契约见 `PIPELINE_STEP_REPLAY_V044_SPEC.md`。

---

# 10. POI Review

待确认地点：

- raw name
- suggested/canonical name
- place type（餐馆/景区/街区/商圈等）
- name correction reason
- source
- context
- candidate POIs
- confidence
- map preview（前端实现）
- confirm
- reject
- search again

---

# 11. Profile Questions

展示：

> 补充这一项可继续判断 30 个岗位。

按 Information Gain 排序。

---

# 12. 控制台目标

用户必须能清晰感知：
- 系统现在在做什么；
- 为什么慢；
- 用了哪个模型；
- 是否用了外部 API；
- 失败在哪里；
- 为什么得出某个结论；
- 如何重跑。

---

# 13. 运维与任务可观测性增补

2026-08-21 页面审阅提出的缩放对齐、实时步骤诊断、日志工作台和侧栏硬件指标已按 `OPERATIONS_UI_SPEC.md` 实施。设计稿位于 `design/ui/operations-v0.3/`，实际回归与防覆盖规则见 `REGRESSION_AND_CHANGE_GUARD.md`；尚未实现的仅限该规格明确标注的后续增强项。
