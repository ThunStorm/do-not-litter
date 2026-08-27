# AI Personal Inbox / Personal Scout
## 项目文档索引

> 文档版本：v0.4.6
> 更新日期：2026-08-28
> 当前阶段：v0.4.6 功能、Python 3.14 生产运行时与外置卷 LaunchAgent 健康门禁均已实施；以 `IMPLEMENTATION_STATUS.md` 为唯一实施状态来源
> 第一阶段部署形态：Mac mini 作为完整后端与 AI Worker，PC/手机通过可信局域网访问
> 第一阶段业务范围：北京市公务员/事业单位招聘 + 中国范围 Travel/Food

---

## 1. 产品一句话定义

这是一个“**随手分享信息 → AI 自动解析 → 结合个人信息/偏好 → 形成可信、可执行结果**”的个人 AI 信息处理与决策系统。

第一版不追求接纳所有信息，而只聚焦两个当前高价值场景：

1. **招聘/事业编/考试信息**
   - 解析公众号、官网、PDF、Excel 岗位表；
   - 自动下钻官方来源；
   - 提取报名期限、考试时间、岗位条件；
   - 结合个人档案进行资格筛选；
   - 输出倒计时、待办、符合/不符合/待确认岗位；
   - 所有事实保留证据链。

2. **旅行/探店信息**
   - 接收 Bilibili 等视频/图文链接；
   - 获取字幕或执行 ASR；
   - 提取餐馆、景点、菜品、地点评价与注意事项；
   - 将地点解析为现实地图 POI；
   - 结合用户偏好筛选；
   - 输出地图、地点列表、想去/去过状态及来源证据。

长期目标是在不推翻第一版架构的前提下，扩展为：

> **可自动接纳未知非结构化信息，通过 GenericProcessor + 专用 Processor 体系进行理解、归类、总结、行动化和可视化的个人 AI 信息操作系统。**

---

## 2. 最重要的产品原则

### 2.1 默认零操作
用户核心动作是“分享/粘贴链接”，后台自动处理，完成后允许用户修正。

### 2.2 AI 先做到 B 级，不直接做到 C 级
当前能力：
- 判断；
- 筛选；
- 生成待办；
- 生成材料 Checklist；
- 生成咨询建议；
- 生成地图；
- 生成可导出结构化结果。

未来 C 级能力：
- 自动填写报名页面；
- 自动操作第三方系统；
- 自动发邮件/提交表单；
- 需额外权限、风控、审计与用户确认机制。

### 2.3 AI 可以推理，但不能伪装成事实
任何事实性结论必须可回溯到：
- 网页原文；
- PDF 页码；
- Excel 单元格；
- 视频时间码；
- 其他明确来源。

### 2.4 产品做窄，内核留宽
第一版 UI 只展示招聘与旅行/探店。
底层仍按：
`Capture → Resolver → Processor Router → Processor → Evidence → Result → View`
设计。

### 2.5 Unknown 第一版不污染产品
第一版不支持的内容：
- 默认标记 `UNSUPPORTED`；
- 可选择仅保存链接或删除；
- 不自动创建乱七八糟的新分类；
- 后续通过 GenericProcessor 扩展。

---

## 3. 文档目录

| 文档 | 用途 |
|---|---|
| [PRODUCT_REQUIREMENTS.md](./PRODUCT_REQUIREMENTS.md) | 产品需求、用户场景、功能边界、MVP |
| [SYSTEM_ARCHITECTURE.md](./SYSTEM_ARCHITECTURE.md) | 总体架构、模块边界、运行方式 |
| [DATA_MODEL.md](./DATA_MODEL.md) | 领域对象、数据库表、Claim/Evidence 数据模型 |
| [RECRUITMENT_PIPELINE.md](./RECRUITMENT_PIPELINE.md) | 招聘完整处理链、DSL、MajorMatcher、资格判断 |
| [TRAVEL_FOOD_PIPELINE.md](./TRAVEL_FOOD_PIPELINE.md) | 视频/图文处理、ASR、POI、偏好学习、地图 |
| [VIDEO_AI_NOTE_PIPELINE.md](./VIDEO_AI_NOTE_PIPELINE.md) | 视频页/Transcript 理解、代表性截图、细粒度地点、高德校名、中国全境地图与 Marker 生命周期 |
| [VIDEO_AI_NOTE_IMPLEMENTATION_GUIDE.md](./VIDEO_AI_NOTE_IMPLEMENTATION_GUIDE.md) | Agent 实施入口：v0.4/v0.4.1 已有能力、v0.4.2 Work Package 12、测试与 DoD |
| [AI_RUNTIME_AND_PROVIDERS.md](./AI_RUNTIME_AND_PROVIDERS.md) | 本地/外部模型、ASR、模型路由、Provider 抽象 |
| [CONTROL_CENTER.md](./CONTROL_CENTER.md) | CMS/控制后台设计 |
| [OPERATIONS_UI_SPEC.md](./OPERATIONS_UI_SPEC.md) | PC 缩放适配、实时任务诊断、运维日志工作台与 Mac mini 指标 UI 契约 |
| [MODEL_AND_RETENTION_UI_SPEC.md](./MODEL_AND_RETENTION_UI_SPEC.md) | 自定义模型库、主/备用路由与任务/内容历史删除契约 |
| [RUNTIME_MONITOR_AND_MODEL_PRESETS_SPEC.md](./RUNTIME_MONITOR_AND_MODEL_PRESETS_SPEC.md) | 持久化 Mac mini 指标、Provider 预设与草稿真实测试契约 |
| [RUNTIME_MONITOR_AND_PROVIDER_SWITCH_V06_SPEC.md](./RUNTIME_MONITOR_AND_PROVIDER_SWITCH_V06_SPEC.md) | macOS 内存口径、运维浮窗与 Provider 默认值联动契约 |
| [MOBILE_SESSION_DIAGNOSTICS_AND_JOB_CONTROL_SPEC.md](./MOBILE_SESSION_DIAGNOSTICS_AND_JOB_CONTROL_SPEC.md) | 手机会话刷新、视频阶段诊断、取消与重试控制契约 |
| [TASK_SUMMARY_AND_PARTIAL_SUCCESS_SPEC.md](./TASK_SUMMARY_AND_PARTIAL_SUCCESS_SPEC.md) | 任务摘要字段语义、长文本收缩与部分完成表达契约 |
| [TASK_STATUS_AND_BEIJING_TIME_SPEC.md](./TASK_STATUS_AND_BEIJING_TIME_SPEC.md) | 终态任务文案与全站北京时间显示契约 |
| [VIDEO_NOTE_RENDERING_AND_TASK_MODEL_CONTEXT_SPEC.md](./VIDEO_NOTE_RENDERING_AND_TASK_MODEL_CONTEXT_SPEC.md) | 视频笔记封面、Markdown 渲染、部分完成与模型调用摘要契约 |
| [VIDEO_NOTE_READING_EXPERIENCE_V042_SPEC.md](./VIDEO_NOTE_READING_EXPERIENCE_V042_SPEC.md) | 地点/转写前置、AI 校对稿、主旨目录、段落跳转、随文截图与 Lightbox 返工契约 |
| [VIDEO_NOTE_LIST_V043_SPEC.md](./VIDEO_NOTE_LIST_V043_SPEC.md) | “添加视频链接”按钮、Bilibili 封面下载、本地缓存与 16:9 列表卡契约 |
| [PIPELINE_STEP_REPLAY_V044_SPEC.md](./PIPELINE_STEP_REPLAY_V044_SPEC.md) | 24h 中间产物、从错误步骤续跑、上游复用和过期后完整重跑契约 |
| [VIDEO_NOTE_DELETE_V044_SPEC.md](./VIDEO_NOTE_DELETE_V044_SPEC.md) | 视频笔记列表/详情删除入口、共享数据保留和确认门禁契约 |
| [PROMPT_SUPPLEMENTS_V045_SPEC.md](./PROMPT_SUPPLEMENTS_V045_SPEC.md) | 不可变核心 Prompt 契约、可编辑补充偏好、哈希续跑与设置 UI 契约 |
| [API_DESIGN.md](./API_DESIGN.md) | REST / WebSocket API 边界 |
| [SECURITY_PRIVACY.md](./SECURITY_PRIVACY.md) | 本地优先、API Key、浏览器登录态、敏感数据 |
| [TESTING_AND_ACCEPTANCE.md](./TESTING_AND_ACCEPTANCE.md) | 测试策略、关键验收用例 |
| [GOLDEN_SAMPLES.md](./GOLDEN_SAMPLES.md) | 首批真实样本、Fixture 规则、技术 Spike 与质量门槛 |
| [PROJECT_PLAN.md](./PROJECT_PLAN.md) | Codex/Agent 可直接执行的工程实施计划 |
| [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md) | 当前已实现能力、真实验收状态与下一实施项 |
| [CURRENT_HANDOFF.md](./CURRENT_HANDOFF.md) | 当前服务、未闭环条件与低 token 接手顺序；短期快照，不进入合订本 |
| [CODEX_CONTEXT.md](./CODEX_CONTEXT.md) | Codex 新任务默认读取的精简项目上下文与文档路由 |
| [CODEX_TASK_TEMPLATES.md](./CODEX_TASK_TEMPLATES.md) | 诊断、修复、迁移、UI 与文档任务的低额度提示模板 |
| [REGRESSION_AND_CHANGE_GUARD.md](./REGRESSION_AND_CHANGE_GUARD.md) | 已确认需求的防覆盖基线、变更规则与回归矩阵 |
| [FUTURE_ROADMAP.md](./FUTURE_ROADMAP.md) | GenericProcessor、移动端、云、多 Worker、C 级自动化 |
| [ARCHITECTURE_DECISIONS.md](./ARCHITECTURE_DECISIONS.md) | 关键设计决策与原因 |

`COMPLETE_PROJECT_SPEC.md` 是由上述分文档自动生成的合订本，不作为独立编辑源。修改分文档后运行 `.venv/bin/python scripts/build_complete_project_spec.py` 重新生成。

---

## 4. 当前硬件基线

开发/运行主机为 Mac mini（Apple M4、16 GB 统一内存、arm64）。CPU、内存、磁盘、运行时与 Worker 心跳均以 `/api/status` 的实时结果为准；安装与常驻规则见 `DEPLOYMENT_OPTIONS.md`。

这台机器承担：

- FastAPI 服务；
- SQLite 数据库；
- Playwright Browser Resolver；
- Bilibili/视频解析；
- ffmpeg；
- whisper.cpp ASR；
- Ollama 本地大模型；
- 独立 Worker；
- Web Control Center；
- 本地文件存储。

---

## 5. 第一阶段技术基线

### Frontend
- React
- TypeScript
- Vite
- Node.js 20.19+ 或 22.12+
- 响应式 Web
- 后期可封装 Tauri 桌面壳
- 手机第一版通过同一可信局域网访问响应式 Web

### Backend
- Python 3.12+；Mac mini 生产 LaunchAgent 固定使用 Python 3.14.6 外置生产 venv
- FastAPI
- Uvicorn
- Pydantic
- SQLAlchemy 2.x
- Alembic
- SQLite + WAL
- 独立 Worker Process
- WebSocket 进度推送

### AI / Parsing
- Ollama
- 外部大模型 Provider（API Key 可配置）
- OpenAI-Compatible Provider
- whisper.cpp
- Playwright
- yt-dlp / 平台解析能力
- ffmpeg
- openpyxl
- `.xls` legacy adapter（Phase 0A 选择 xlrd 或 python-calamine）
- PDF Parser
- DOCX Parser
- 中文 OCR（扫描 PDF / PNG / JPEG）
- 高德 POI Web 服务 + 地图 JS API 2.0
- DeepSeek / Xiaomi MiMo 等 OpenAI-compatible 外部 Provider

---

## 6. 第一版明确不做

- 云端业务数据库
- Redis
- Celery
- RabbitMQ
- PostgreSQL
- Vector DB
- 微服务
- 多用户/多租户
- 社交
- 付费
- Agent Marketplace
- 动态 Skill 自动生成
- 自动创建任意 Space
- 长期 Source Watch（仅预留接口）
- 自动报名/自动提交第三方表单
- iOS / Android / 微信小程序同时开发
- 泛知识收集器

---

## 7. 从第一版到长期产品的演化主线

```text
V0.1
RecruitmentProcessor
TravelFoodProcessor
Unknown → Unsupported

        ↓

V0.2+
GenericProcessor
Unknown → 摘要 / 关键事实 / 日期 / 人物 / 地点 / 行动项

        ↓

V0.x
高频 Generic 场景
→ Configurable Processor

        ↓

V1.x
成熟高频场景
→ Dedicated Processor

        ↓

长期
个人 AI 信息处理与行动平台
```

---

## 8. 开发原则

1. **不得把业务逻辑写进 Resolver。**
2. **不得在业务代码中直接调用具体 LLM SDK。**
3. **不得让 LLM 负责确定性计算。**
4. **不得生成没有 Evidence 的事实性 Claim。**
5. **不得把现实 POI 坐标交给 LLM 编造。**
6. **不得因为未来可能需要而提前实现大平台。**
7. **允许定义扩展接口，但不提前实现不属于 MVP 的能力。**
8. **Pipeline 必须可重放、可重跑、可审计。**
9. **长任务必须持久化，PC 重启后可恢复。**
10. **原始证据优先，AI 解释次之。**
