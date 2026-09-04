# AI Personal Inbox / Personal Scout
## Complete Project Specification

> GENERATED FILE. Edit the source documents in this directory, then run `.venv/bin/python scripts/build_complete_project_spec.py`.


---

# FILE: README.md

# 文档目录与维护规则

> 按需目录，不是必读清单。外部读者先看 [项目概览](../README.md)，开发 Agent 先看 [CODEX_CONTEXT.md](CODEX_CONTEXT.md)。2026-09-03 完成入口去重、主题分篇和历史隔离；本次不重新评定业务验收。

## 1. 谁读什么，读到哪里停止

| 读者 / 问题 | 最短路径 | 停止条件 |
| --- | --- | --- |
| 外部了解项目 | 根 README → 有需要再选 PRODUCT_REQUIREMENTS 或 SYSTEM_ARCHITECTURE 的相关章 | 能说明用途、架构、支持范围与限制 |
| Codex 继续开发 | AGENTS → CODEX_CONTEXT → 当前状态 → 相关冻结行 → 一个专项分篇 | 能说明目标、现状、代码位置、约束与验收 |
| 运维 / 部署 | CURRENT_HANDOFF → DEPLOYMENT_OPTIONS 或 deploy/macos/README | 已区分历史快照与本次现场证据 |
| 审计 / 追溯 | 当前状态 → 指定 history 章节 / ADR | 得到所需历史证据，不扫描全部历史 |
| 对外完整导出 | 构建 COMPLETE_PROJECT_SPEC | 只生成，不把合订本加载进 Agent 上下文 |

## 2. 唯一事实来源

| 内容 | 唯一维护位置 | 不要重复放到 |
| --- | --- | --- |
| 产品简介 / 使用入口 | [根 README](../README.md) | 本目录索引、每个专项开头 |
| Agent 规则 / 路由 | [AGENTS](../AGENTS.md) / [CODEX_CONTEXT](CODEX_CONTEXT.md) | 历史计划中的强制阅读清单 |
| 当前源码能力 / 自动验证 / 缺口 | [IMPLEMENTATION_STATUS](IMPLEMENTATION_STATUS.md) | 概览、接手页、回归清单 |
| 任务续接 / 生产现场（分段） | [CURRENT_HANDOFF](CURRENT_HANDOFF.md) | 源码状态与静态版本介绍 |
| 不可回退约束 | [REGRESSION_AND_CHANGE_GUARD](REGRESSION_AND_CHANGE_GUARD.md) | 大段复制到各交接页 |
| 设计契约 | 下表专项正文 | 实施状态的长篇叙述 |
| 逐版本过程 / 旧计划 | history/，仅按需追溯 | 默认接手正文 |
| 未来候选范围 | [待办池](planning/POST_FREEZE_TODO_BACKLOG.md)、[路线图](planning/FUTURE_ROADMAP.md) | 当前完成度或自动授权 |

源码/测试证明实际行为，冻结契约表达必须保持的要求，两者冲突应报告差异，不能用一方静默覆盖另一方。新草案也不因日期更新就自动生效。

## 3. 专项目录（按问题选读）

根目录只保留总索引、Agent 接手与模板、当前状态、交接、冻结清单，以及文档清单 manifest.json 和生成合订本。正文按主题归位；下列目录就是实际存放位置，不另建重复索引。Markdown 链接相对当前文件解析；正文中的裸文档路径以 `dev docs/` 为基准，明确带 `../` 或仓库前缀的路径除外。

| 子目录 | 存放内容 |
| --- | --- |
| product/ | 产品需求、招聘与旅行领域、控制台信息结构 |
| architecture/ | 系统架构、ADR、数据模型、API、安全 |
| jobs/ | Job、Replay、会话、任务状态与时间 |
| video/ | 视频分篇、代码地图、阅读/列表/删除规格 |
| ai-gateway/ | Gateway 分篇、模型与 Prompt、运行配置、AI 验收 |
| operations/ | 部署、日志、运维交互、运行监控 |
| testing/、benchmark/ | 测试策略与样本说明；机器可读验收样本 |
| planning/ | 待办池、未来路线、未冻结地图 V2 草案；不自动授权实施 |
| history/ | 历史实施记录和旧计划；仅追溯时读取 |

| 领域 | 文档与职责 |
| --- | --- |
| 产品 / 架构 | [PRODUCT_REQUIREMENTS](product/PRODUCT_REQUIREMENTS.md) 用户场景与边界；[SYSTEM_ARCHITECTURE](architecture/SYSTEM_ARCHITECTURE.md) 模块关系；[ARCHITECTURE_DECISIONS](architecture/ARCHITECTURE_DECISIONS.md) 按 ADR 编号追溯原因 |
| 数据 / API / 安全 | [DATA_MODEL](architecture/DATA_MODEL.md) 按表定位；[API_DESIGN](architecture/API_DESIGN.md) 按路由定位；[SECURITY_PRIVACY](architecture/SECURITY_PRIVACY.md) 按安全边界定位 |
| 招聘 / 旅行 | [RECRUITMENT_PIPELINE](product/RECRUITMENT_PIPELINE.md) 提取/规则/资格；[TRAVEL_FOOD_PIPELINE](product/TRAVEL_FOOD_PIPELINE.md) 地点/POI/偏好 |
| 视频 Pipeline | [VIDEO_AI_NOTE_PIPELINE](video/VIDEO_AI_NOTE_PIPELINE.md) 五篇索引：范围、输入转写、生成物化、Job/API、视图与安全 |
| 视频代码定位 | [VIDEO_AI_NOTE_IMPLEMENTATION_GUIDE](video/VIDEO_AI_NOTE_IMPLEMENTATION_GUIDE.md) 短代码地图；旧 WP 已归档，不再要求完整读取八份文档 |
| 阅读 / 列表 / 删除 | [阅读体验](video/VIDEO_NOTE_READING_EXPERIENCE_V042_SPEC.md)、[列表封面](video/VIDEO_NOTE_LIST_V043_SPEC.md)、[笔记删除](video/VIDEO_NOTE_DELETE_V044_SPEC.md)，保持独立验收边界 |
| 渲染 / 任务模型摘要 | [VIDEO_NOTE_RENDERING_AND_TASK_MODEL_CONTEXT_SPEC](video/VIDEO_NOTE_RENDERING_AND_TASK_MODEL_CONTEXT_SPEC.md) |
| Job / Replay / 会话 | [步骤续跑](jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md)、[手机会话与任务控制](jobs/MOBILE_SESSION_DIAGNOSTICS_AND_JOB_CONTROL_SPEC.md) |
| 任务表达 / 时间 | [摘要与部分成功](jobs/TASK_SUMMARY_AND_PARTIAL_SUCCESS_SPEC.md)、[状态与北京时间](jobs/TASK_STATUS_AND_BEIJING_TIME_SPEC.md) |
| AI Gateway | [AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2](ai-gateway/AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md) 六篇索引：模型边界、公共能力、Pipeline/Provider、阶段参数、单任务策略、历史工作包/验收 |
| AI 运行 / 生产验收 | [AI_RUNTIME_AND_PROVIDERS](ai-gateway/AI_RUNTIME_AND_PROVIDERS.md) 运行配置；[AI_GATEWAY_PRODUCTION_ACCEPTANCE](ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md) 真实验收门禁 |
| 模型 / Prompt / 来源保留 | [模型与历史删除](ai-gateway/MODEL_AND_RETENTION_UI_SPEC.md)、[补充 Prompt](ai-gateway/PROMPT_SUPPLEMENTS_V045_SPEC.md)、[转写路由与来源保留](ai-gateway/AI_ROUTING_SOURCE_RETENTION_V046_SPEC.md) |
| 控制台 / 运维 | [CONTROL_CENTER](product/CONTROL_CENTER.md) 信息结构；[OPERATIONS_UI_SPEC](operations/OPERATIONS_UI_SPEC.md) 工作台交互；[LOGGING](operations/LOGGING.md) 日志契约与维护 |
| 运行监控 / Provider | [监控与预设](operations/RUNTIME_MONITOR_AND_MODEL_PRESETS_SPEC.md)、[内存口径与预设切换](operations/RUNTIME_MONITOR_AND_PROVIDER_SWITCH_V06_SPEC.md) |
| 部署 | [DEPLOYMENT_OPTIONS](operations/DEPLOYMENT_OPTIONS.md) 支持边界；[Mac mini 操作说明](../deploy/macos/README.md) 安装与维护 |
| 验证 / 样本 | [TESTING_AND_ACCEPTANCE](testing/TESTING_AND_ACCEPTANCE.md) 验证策略；[GOLDEN_SAMPLES](testing/GOLDEN_SAMPLES.md) 样本/Fixture；benchmark/ 仅验收任务按需查看 |
| 设计 / 授权 | [design/ui](../design/ui/README.md) → 目标版本/页面；[THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES.md) 授权记录 |
| 提示词 / 写交接 | [CODEX_TASK_TEMPLATES](CODEX_TASK_TEMPLATES.md) 三条短指令；交接固定更新 CURRENT_HANDOFF.md 的任务续接段，不另建文件 |
| 历史 / 未来 | [历史实施记录](history/IMPLEMENTATION_HISTORY.md)、[早期工程计划](history/PROJECT_PLAN.md)、[FUTURE_ROADMAP](planning/FUTURE_ROADMAP.md)；均非默认阅读 |

已删除 LOGGING_ARCHITECTURE.md、LOGGING_IMPLEMENTATION.md 与根层 PROJECT_PLAN.md 三个纯跳转页；正文分别在 operations/LOGGING.md 和 history/PROJECT_PLAN.md。仓库内使用处已直达正文，旧路径不再保留。

## 4. 拆分与合并结论

| 原文 / 组合（整理前行数） | 处理 | 理由与边界 |
| --- | --- | --- |
| IMPLEMENTATION_STATUS（234 行，约 34 KB） | 已拆：短当前状态 + history/IMPLEMENTATION_HISTORY | 长段落混杂多轮“当前”；历史测试数量不再干扰当前结论 |
| Gateway v2（2,754 行） | 已拆为六个主题分篇，索引与正文均在 ai-gateway/ | 模型/路由/上下文/阶段设置/任务覆盖/验收按任务独立检索，保留原章节编号 |
| VIDEO_AI_NOTE_PIPELINE（896 行） | 已拆为五篇，索引与正文均在 video/ | 输入、生成、状态/API 与视图的读取需求不同 |
| 视频实施指南（961 行） / PROJECT_PLAN（926 行） | 正文已归档；仅保留有代码地图的视频短指南 | 是历史执行序列，不能继续充当“先读全部”或当前待办 |
| LOGGING_ARCHITECTURE + LOGGING_IMPLEMENTATION（82 + 92 行） | 已合并 operations/LOGGING.md | 同一维护任务反复跳转，且“已实施/待实施”互相冲突；删除重复与过期标签，保留契约与维护入口 |
| 根 README / dev docs README / CODEX_CONTEXT | 已合并重复背景，职责分开 | 产品简介只在根入口；目录只导航；接手页只放代码地图与任务路由 |
| CURRENT_HANDOFF / 状态 / 回归清单中的运行事实 | 已去重 | 当前源码、现场快照、冻结约束各有唯一来源 |
| 地图 V2 计划（3,761 行） | 完整移入 planning/，暂不拆正文 | 作为实施与验收追溯；核心实现状态以 IMPLEMENTATION_STATUS 为准，仍不把后续推荐/路线规划自动升级为当前需求 |
| DATA_MODEL（903 行） / API_DESIGN（427 行） | 本次保留，按表/路由检索 | 数据模型大量为字段/空行；单一数据字典不为行数机械拆碎。未来某领域持续独立改动时再抽出该域 |
| 多份短 UI 规格 | 暂不合并成大 UI 文档 | 阅读/删除/Replay/时间具有独立风险与验收边界；目录统一导航即可 |
| CONTROL_CENTER / OPERATIONS_UI / RUNTIME_MONITOR 系列 | 保持分层 | 页面信息结构、工作台交互、指标语义不同；不要把架构、交互、运行时混成新合订本 |

### 地图 V2 草案的按需路由

原文：[地图 V2 计划](planning/PLACE_INTELLIGENCE_MAP_V2_IMPLEMENTATION_PLAN.md)。已归入 planning/；下表保留按需阅读边界。核心地图实现已获用户授权并进入源码，当前实现/验收以 IMPLEMENTATION_STATUS 为准；任何后续扩展仍须同时核对 §98–99 的 Review 修正、§106 原则和冻结约束。

| 拟拆领域 / 任务 | 原章节 |
| --- | --- |
| 模型、Insight、来源证据、人工覆盖 | §1–20 |
| POI Resolver 与 Review | §21–30、§88–89 |
| 地图 Runtime / 筛选 / Place Sheet | §31–44、§77–78、§82–86 |
| 编辑、手工 Pin、删除与 API | §45–68、§87 |
| Pipeline / 合并 / Migration | §69–76、§79–81 |
| 测试 / 执行计划 / Review 修正 / DoD | §90–106 |

## 5. 后续维护规则

- 根 AGENTS 自动加载，所以只放行为规则；不把本目录或长规格放进自动注入配置。新任务按 CODEX_CONTEXT 导航；已读内容不重复。
- 接手页以约 6 KB 为目标、当前状态约 5 KB；首轮总读取约 12 KB 是软预算，不是真实 token 上限。安全/数据/验收证据不足可说明原因后增读。
- 专项跨多个独立任务域且超过约 500 行或 20 KB 时评估拆分，不机械按行切割；同一任务必读的重复短文优先合并。分篇必须带返回入口、来源与状态性质。
- 新增/移动文档时更新本目录与必要的 CODEX_CONTEXT 路由；有独立导航价值的主题索引保留，纯跳转页更新引用后删除。契约只保留一个正文源；不复制到状态页、临时交接或新版本文件。
- history/ 默认不读，不因未来工作包在文档中出现而执行。实施历史只在追溯时定位相关日期/标题。
- 合订本由 scripts/build_complete_project_spec.py 的显式清单生成；不含交接快照、history/ 正文、旧 PROJECT_PLAN、未来路线或未冻结草案。Gateway 分篇中的原验收设计仍作为契约保留，不代表新的执行授权。清单或清单内源文件变化时重建；不要为同步生成物读取它。
- 文档交付检查链接、分篇正文完整性、生成可重复性和 git diff --check；可运行 .venv/bin/python scripts/test_build_complete_project_spec.py 检查生成物、来源清单与分篇链接重定位。不重启、不迁移、不调用真实 Provider、不跑业务全量。

## 6. Codex 设置说明

本次设置落在仓库 AGENTS.md，未更改用户全局配置、模型或推理档，也未设置会截断安全指令的硬 token 限制。按 [OpenAI 官方 AGENTS.md 文档](https://learn.chatgpt.com/docs/agent-configuration/agents-md)，仓库指令在运行开始时加载；建议在该仓库新建任务使用新规则。本轮未额外启动付费模型任务来测试加载。


---

# FILE: CODEX_CONTEXT.md

# Codex 精简接手页

> 项目任务默认入口；本页只放稳定背景与阅读路由，不重复当前提交、测试数量、生产快照。规则见仓库根 AGENTS.md。

## 项目与代码边界

至简是 Mac mini 单用户、本地优先的信息处理系统。PC/手机经可信局域网访问 React Web；FastAPI + SQLite/WAL，独立 Worker 处理招聘与 Bilibili 旅行视频长任务。当前唯一支持的后端部署是 Mac mini。

流程：Capture → Source/Job → Resolver → Segment/Evidence → Processor → Content。视频包括字幕/ASR、校对、笔记、地点/POI、截图与物化。计划中的功能不等于已实现。

| 位置（仓库根相对路径） | 职责 |
| --- | --- |
| backend/src/zhijian/api/ | API 与认证入口，长任务不在请求内执行 |
| backend/src/zhijian/services/ | Video Pipeline、登录恢复、Replay、审计 |
| backend/src/zhijian/ai/ | Gateway、策略、预算、本地资源串行 |
| backend/src/zhijian/db/、backend/alembic/versions/ | 持久模型与追加式迁移 |
| frontend/src/features/ | tasks / video / map / settings 等产品页面 |
| deploy/macos/ | LaunchAgent 管理；服务变更须另行满足安全门禁 |

## 最短接手路径

1. 开发/诊断读 [当前实施状态](IMPLEMENTATION_STATUS.md)，再按关键词定位 [冻结清单](REGRESSION_AND_CHANGE_GUARD.md) 的相关行。
2. 下表选一个直接相关分篇/章节；先查标题，再读命中段。别把所有可选文档作为启动清单。
3. 已能说明目标、现状、影响文件、不可破坏项和验收方法，就停止读文档，转到目标代码/测试。首轮目标约 12 KB；这是软预算，证据不足可说明原因后增读。
4. 继续上次任务时读 [当前交接](CURRENT_HANDOFF.md) 的任务续接段；部署/服务问题才读生产快照。快照有原采样日期，不保证当前仍然成立。

## 按任务选一个入口

| 任务关键词 | 首选文档 / 章节 |
| --- | --- |
| Capture、文件、OCR、招聘 | [产品需求](product/PRODUCT_REQUIREMENTS.md) 命中段；招聘专项选 [招聘 Pipeline](product/RECRUITMENT_PIPELINE.md) |
| Bilibili、登录、字幕、ASR、转写 | [视频输入与转写](video/02-input-transcript.md) |
| 视频笔记、地点抽取、截图 | [视频生成与物化](video/03-generation-materialization.md)；Gateway 优化才读下行 |
| Gateway、Map/Reduce、Provider、Usage | [Pipeline 与 Provider](ai-gateway/03-pipeline-providers.md) |
| Profile、模型能力、硬件限制 | [架构与模型边界](ai-gateway/01-architecture-models.md)；运行命令才读 ai-gateway/AI_RUNTIME_AND_PROVIDERS.md |
| 路由、AUTO、阶段参数、设置 | [Stage Policy](ai-gateway/04-stage-policy.md)；实际语义须核对 ai/policies.py 与 backend/tests/test_ai_stage_policies.py |
| 单任务覆盖、Policy API、Cache Key | [任务策略覆盖](ai-gateway/05-job-policy.md) |
| Domain Context、Cache、Budget、资源锁 | [Gateway 公共能力](ai-gateway/02-gateway-context.md) |
| Job、取消、重试、Replay | [步骤续跑](jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md)；会话/取消问题选 jobs/MOBILE_SESSION_DIAGNOSTICS_AND_JOB_CONTROL_SPEC.md |
| 视频阅读、列表、删除 | 分别选 [阅读](video/VIDEO_NOTE_READING_EXPERIENCE_V042_SPEC.md)、[列表](video/VIDEO_NOTE_LIST_V043_SPEC.md)、[删除](video/VIDEO_NOTE_DELETE_V044_SPEC.md) |
| Prompt、来源保留、模型设置 | 分别选 ai-gateway/PROMPT_SUPPLEMENTS_V045_SPEC.md、ai-gateway/AI_ROUTING_SOURCE_RETENTION_V046_SPEC.md、ai-gateway/MODEL_AND_RETENTION_UI_SPEC.md |
| 地图、地点、POI | [旅行领域](product/TRAVEL_FOOD_PIPELINE.md) 命中段；Marker 导航见 [视频视图](video/05-views-safety-acceptance.md) |
| 地图 V2 草案（仅用户指定时） | [文档目录](README.md#地图-v2-草案的按需路由) 选章节，不能推断已冻结或已实现 |
| 运维日志、监控、北京时间 | [日志](operations/LOGGING.md)；监控选 operations/OPERATIONS_UI_SPEC.md，时间选 jobs/TASK_STATUS_AND_BEIJING_TIME_SPEC.md |
| 数据迁移、API、安全 | 分别在 architecture/DATA_MODEL.md、architecture/API_DESIGN.md、architecture/SECURITY_PRIVACY.md 中按表/路由/威胁定位 |
| 真实 AI 验收 | [生产验收门禁](ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md)；不因自动测试通过而跳过 |

表中裸文件名以本目录为基准。其他专项和历史入口只在 [文档目录](README.md) 按需查找。

## 必须保留的边界

- 长任务进 Worker；Source/Snapshot/Segment/Claim/Evidence、Job/Step/Artifact 各自身份不混用。
- note_* 是公开 Note ID，ntv_* 是版本 ID；raw/corrected Transcript 保持 Segment ID、顺序、时间码。
- PARTIAL_SUCCESS 是终态；Replay Options 由后端计算；Marker 隐藏不级联删除 Place/Source/Evidence。
- Secret 不进 SQLite 明文、日志、URL、导出或 localStorage；登录用站内 QR/恢复状态，不要求用户复制 Cookie。
- 不擅自调用真实 Provider、重跑视频、迁移生产库或重启服务；修改历史迁移被禁止。
- 只读概览、文档整理、诊断不等于修复/上线授权。未来计划不自动变为任务。

## 定位与验证

用 rg -n "关键词" 指定文件，再用 sed -n '起始,结束p' 读取；不要扫描全部源码/文档。代码工作先目标测试，工作包末一次全量验证；前端行为改变才做目标页面 Browser。命令见 [测试策略](testing/TESTING_AND_ACCEPTANCE.md)，Node 基线见当前实施状态。纯文档只做链接、迁移正文、生成一致性和 diff 检查。提示词见 [任务模板](CODEX_TASK_TEMPLATES.md)。


---

# FILE: CODEX_TASK_TEMPLATES.md

# 三条短指令

在本仓库使用；具体读取、安全与交接规则已写入根 AGENTS.md，不必每次粘贴。

## 开始新工作

```text
按 AGENTS.md 接手项目，完成：<具体目标>。按需读文档，先明确验收条件再实施。
```

## 结束前写交接

```text
按 AGENTS.md 更新 CURRENT_HANDOFF.md，简要写清完成、验证、阻塞、下一步和注意事项，不另建交接文件。
```

完整路径为 dev docs/CURRENT_HANDOFF.md。任务续接段目标不超过 600 字；当前能力/自动验证仍只维护在 IMPLEMENTATION_STATUS.md，生产快照保留真实采样日期，未复核就注明。写交接不授权上线、提交或推送；要求验收后再写时应等待。

## 新任务继续上次工作

```text
按 AGENTS.md 和 CURRENT_HANDOFF.md 接手，继续其中明确授权的下一步；没有明确目标时先问我。
```

先读任务续接段，不默认读取生产快照或历史。诊断任务另加“只诊断，不修改”即可。


---

# FILE: REGRESSION_AND_CHANGE_GUARD.md

# 回归基线与变更防覆盖清单

更新日期：2026-09-03。本文只维护已确认需求的保护清单。改动前按能力关键词读取相关条目与契约，不默认通读所有链接；不能以原型截图、静态数据或“构建成功”替代真实实现。

## 1. 变更规则

1. 先定位所属能力，再改代码；不以重写页面的方式覆盖已有可操作功能。
2. 改动数据模型时必须添加 Alembic 迁移并验证 `alembic current`；不得改动历史 Source、Claim、Evidence 或 Note 来实现地图隐藏。
3. 改动 Job、模型、视频或地图链路时，必须同时更新任务步骤、可读日志、API、UI 与验收用例。
4. 代码工作包先目标验证、结束时一次全量后端/前端验证。部署是独立授权：需要部署时先确认无活跃 Job/lease，不能中断用户任务。纯文档只做文档一致性检查，不跑业务全量、不重启服务。
5. `COMPLETE_PROJECT_SPEC.md` 仅由构建脚本的 source set 生成；这些源文档或清单变化后运行 `.venv/bin/python scripts/build_complete_project_spec.py`。不需要读取合订本，也不因只更新历史/交接而重建。

## 2. 已冻结的功能基线

| 能力 | 不可回退要求 | 契约 / 主要实现 |
| --- | --- | --- |
| 部署与局域网 | 唯一后端为 Mac mini；4 位配对码显眼展示；Cookie 会话刷新不应重新要求配对；服务状态来自真实 API/Worker/SQLite | `operations/DEPLOYMENT_OPTIONS.md`、`jobs/MOBILE_SESSION_DIAGNOSTICS_AND_JOB_CONTROL_SPEC.md`、`services/auth.py` |
| 捕获与本地处理 | URL、正文、DOCX、PDF、XLSX、图像 OCR、音视频均可进入 Job；Whisper.cpp、FFmpeg 与 OCR 状态必须是探测结果 | `product/PRODUCT_REQUIREMENTS.md`、`ai-gateway/AI_RUNTIME_AND_PROVIDERS.md` |
| 模型设置 | 用户可维护任意 Provider/模型库；预设仅帮助填写；主/备用从已存模型选择；草稿可真实测试；默认超时 300 秒 | `ai-gateway/MODEL_AND_RETENTION_UI_SPEC.md`、`operations/RUNTIME_MONITOR_AND_MODEL_PRESETS_SPEC.md` |
| AI Gateway 契约 | Model Profile 显式保存 location/modalities/capabilities；Stage 参数仅白名单；没有新策略的历史任务保持旧路由，`AUTO/LOCAL_ONLY/LOCAL_FIRST/REMOTE_FIRST/REMOTE_ONLY` 语义不得回退 | `ai-gateway/AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md`、`ai/policies.py` |
| AI Gateway 质量与上下文 | 干净平台字幕不得无条件全文送模；长转写只传候选或 Facts，不能多阶段重复全文；Domain Context 仅低优先级增强，不能覆盖 Evidence、Schema 或安全契约；text-only Profile 不得绑定视觉 Stage | `ai-gateway/AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md`、`services/video_support.py` |
| AI Gateway 稳定性 | 精确 Cache hit 不重复调用 Provider；`force_regenerate` 绕过命中并保留结果链；本机 ASR/文本/视觉/模型测试必须跨 API/Worker 进程串行；LOCAL/REMOTE Token 分账只依据审计路由位置；Cache hit 不计模型调用或预算；Ollama `keep_alive: 0` 与本地重任务低并发不得回退；未经真实 E2E 与 Benchmark Gate 不得宣称生产验证 | `ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md`、`ai/resource_manager.py`、`ai/budget.py`、`ai-gateway/AI_RUNTIME_AND_PROVIDERS.md` |
| 任务控制 | 当前标记只属于运行中的当前 JobStep；终态不固定高亮最后一步；时间线按 Pipeline 排序、阶段中文化并显示步骤用时；普通步骤 90 秒、LLM 步骤 500 秒预警，900 秒才终止；取消协作释放 lease，确认前不允许重试 | `jobs/MOBILE_SESSION_DIAGNOSTICS_AND_JOB_CONTROL_SPEC.md`、`jobs/TASK_SUMMARY_AND_PARTIAL_SUCCESS_SPEC.md`、`jobs/TASK_STATUS_AND_BEIJING_TIME_SPEC.md` |
| Worker 存活与完整重跑 | 全局 Worker 心跳独立于同步 Pipeline；Job 活动只反映真实阶段/batch；长模型取消在请求边界停止后续批次，429/5xx 不放大请求；取消 lease 释放后 `CANCELLED` 也可完整重跑 | `operations/RUNTIME_MONITOR_AND_PROVIDER_SWITCH_V06_SPEC.md`、`jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md`、ADR-030 |
| 终态与时间 | 终态不显示预估；展示层强制北京时间，持久化 ISO 时间仍保持 UTC | `jobs/TASK_STATUS_AND_BEIJING_TIME_SPEC.md` |
| 运维 | CPU/内存/磁盘与 Worker 心跳为 SQLite 持久化快照；内存百分比使用可回收页口径；日志支持筛选、关联 Job、分页与脱敏 | `operations/OPERATIONS_UI_SPEC.md`、`operations/LOGGING.md` |
| 步骤续跑 | ERROR/CRITICAL 事件先查询 Replay Options；Artifact 有效时从失败步骤继续，上游 REUSED、当前/下游顺次执行；过期后只允许完整重跑；日志页不直接改步骤 | `jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md`、`operations/LOGGING.md`、ADR-026 |
| 内容保留 | 终态任务和内容可删除；删除不破坏共享来源、地点、路线或证据；密钥只进 Keychain/Secret Store | `ai-gateway/MODEL_AND_RETENTION_UI_SPEC.md`、`architecture/SECURITY_PRIVACY.md` |
| 视频 v0.3 | Bilibili 元数据/字幕优先/受控音频/Whisper 转写；AI 笔记、章节、时间码、地点候选、POI、Place Note 和失败/部分成功均为真实数据 | `video/VIDEO_AI_NOTE_PIPELINE.md` 1–4.11 |
| Bilibili 登录与字幕 | 登录只走站内二维码与 Keychain；登录失效必须进入 `NEEDS_USER` 并提供可用的续跑/非核心跳过选择；字幕 CDN 使用用途级 HTTPS Host Policy，安全支持官方子域；人工中文、AI 中文、其他语言依次尝试，单轨失败不得击穿整个 Job | `video/VIDEO_AI_NOTE_PIPELINE.md` 4.4–4.5、`core/url_policy.py`、`services/bilibili_auth.py` |
| 视频 v0.4 截图 | 笔记先综合元数据与 Transcript；`PLAN_SCREENSHOTS → DOWNLOAD_VIDEO_FOR_FRAMES → EXTRACT_SCREENSHOTS → MATERIALIZE` 为显式步骤；3–12 张全文截图、主要地点优先，绑定章节/地点候选/Segment/时间码；过滤黑帧、曝光异常、低清晰度和重复帧 | `video/VIDEO_AI_NOTE_PIPELINE.md` 4.12–4.15、`services/video_screenshots.py` |
| 视频 v0.4.2 阅读返工 | Hero 有真实封面、缺省为空；摘要/主体目录/正文优先，地点候选与完整转写放底部；默认使用 AI corrected Transcript；截图以侧排缩略图嵌入并支持 contain Lightbox；TXT 按钮使用统一视觉 | `video/VIDEO_NOTE_READING_EXPERIENCE_V042_SPEC.md` |
| 视频 v0.4.3 列表封面 | 主按钮为“添加视频链接”并使用统一 40px/14px Token；Card 展示本地持久真实封面、16:9 cover 和时长徽标；封面失败只显示占位，不阻塞 Note | `video/VIDEO_NOTE_LIST_V043_SPEC.md` |
| 视频笔记删除 | 列表/详情共用删除；删除 Note/Version/Section/TOC/Content 投影，保留共享 Source/Asset/Cover/Transcript/Place/Evidence；活跃 Job 阻止删除 | `video/VIDEO_NOTE_DELETE_V044_SPEC.md` |
| 地点与 POI | 保留 `raw_name`，人工改名仅更新 `suggested_name`；高德确认写 `canonical_name`；歧义进入 Review，拒绝项不再显示且可撤销，不能生成 Confirmed Marker | `product/TRAVEL_FOOD_PIPELINE.md`、`services/video_support.py` |
| 全国地图 | 首次中国大陆全境、之后恢复 viewport；按 bbox + zoom 查询且低 zoom 聚合、放大后直出独立 Marker；不得恢复厦门/思明区默认参数、标题、静态伪地图或路线默认城市 | `video/VIDEO_AI_NOTE_PIPELINE.md` 4.16、`MapOverviewPage.tsx` |
| Marker 生命周期 | 自动 Marker 删除仅隐藏投影；用户 Marker 软删除可恢复；绝不删除 Place、Source、Claim、Evidence、Place Note；浮层展示图片、地址、特色、来源数、状态和详情入口 | `architecture/API_DESIGN.md`、`map_marker_states`、`MapOverviewPage.tsx` |
| 高德设置 | JS API Key、Security Code、Web 服务 Key 分别保存/测试/诊断；前端已认证后用 bootstrap 读取，不在代码或构建变量硬编码 Key | `product/CONTROL_CENTER.md`、`SettingsPage.tsx` |
| UI 体系 | PC 是 CMS/运维优先，手机是日常入口；底部导航只放共性功能；外部来源图标单色；设计稿只作代码原生 UI 依据 | `design/ui/README.md`、`design/ui/v0.4/README.md` |

## 3. 回归矩阵

| 层 | 必跑检查 | 通过条件 |
| --- | --- | --- |
| 数据库（仓库） | `python -m alembic -c backend/alembic.ini heads` | 与当前迁移文件和 IMPLEMENTATION_STATUS.md 的仓库记录一致；历史迁移不可修改 |
| 数据库（生产） | `python -m alembic -c backend/alembic.ini current` | 仅记录实际读取的 production revision；迁移前确认无活跃 Job/lease、备份和完整性检查，不能由仓库 head 推断 |
| 后端 | `./.venv/bin/python -m pytest backend/tests -q` | 全量通过；至少覆盖局域网、超时、取消/重试、运行状态、地图聚合与 Marker 生命周期 |
| 前端 | 在 `frontend/` 运行 `pnpm run lint`、`pnpm test -- --run`、`pnpm run build` | 无 lint/类型/构建错误；地图画布和设置核心单测通过 |
| 服务 | `/api/status`、`/api/travel/map?zoom=4`、`/api/travel/map/bootstrap` | API/Worker/SQLite 为 RUNNING；返回中国全境 viewport 和聚合/配置字段 |
| GUI | PC 与手机宽度分别走概览、投递、内容、任务/详情、视频笔记/截图、地图/Marker、路线、全部设置、日志 | 无控制台错误、无横向溢出、状态与 API 一致；外部 Key 未配置时显示可行动诊断，绝不伪造底图或成功 |

## 4. 验证记录的唯一来源

自动验证与未闭环项见 [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)，生产采样见 [CURRENT_HANDOFF.md](CURRENT_HANDOFF.md)，逐版本证据见 history/IMPLEMENTATION_HISTORY.md。本文不再复制测试数量、生产版本和活跃任务数，避免多处漂移。Gateway 生产验收继续受 ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md 约束。


---

# FILE: jobs/TASK_STATUS_AND_BEIJING_TIME_SPEC.md

# 任务终态与北京时间显示规格

版本：v0.1，更新日期：2026-08-22，状态：`IMPLEMENTED`。

## 1. 终态不能显示预估

概览、任务列表和详情中的预估仅属于 `QUEUED` 或 `RUNNING`。任务达到终态后必须立即以真实状态替换预估：

| Job 状态 | 展示文案 |
| --- | --- |
| `COMPLETED` | 已完成 |
| `PARTIAL_SUCCESS` | 处理流程已完成，并显示补充原因 |
| `FAILED` | 失败 |
| `NEEDS_USER` | 需确认 |
| `CANCELLED` | 已取消 |

`progress=100` 不是成功的独立判定；以 Job 状态为准。禁止在 `CLEAN_CACHE` 已完成、`PARTIAL_SUCCESS` 或失败任务上继续显示“预计 N 分钟”。

时间线的“当前”标记只在 `Job.status=RUNNING`、对应 `JobStep.status=RUNNING` 且名称等于 `current_step` 时显示。终态 Job 只显示“结束步骤”，不得把 `CLEAN_CACHE` 永久高亮。每个 Step 统一展示中文名称、技术枚举、状态、进度和 `finished_at-started_at` 用时；运行中步骤使用当前时间计算已用时。

## 2. 北京时间

- 数据库、API ISO 时间和审计事件继续使用 UTC 带时区保存，保证排序、跨端比较和导出不含歧义；
- SQLite 读取历史 `datetime` 时若丢失 offset，API 必须按 UTC 恢复为带 `+00:00` 的 ISO 值后再输出；禁止把无时区 UTC 数值直接交给浏览器；
- 所有面向用户的时间（日志表、日志抽屉、任务详情、概览更新时间、侧栏采样时间）必须强制使用 `Asia/Shanghai` 格式化，不依赖浏览器或设备时区；
- 日志界面标题明确显示“北京时间”。原始 UTC ISO 值仅作为导出/诊断数据保留；
- 相对时间仍按当前时刻与 UTC 时间差计算，避免本地时区导致停滞阈值误判。

## 3. 验收

1. 输入 `2026-08-22T07:00:20Z`，日志 UI 显示 `08/22 15:00:20`；
2. 在 UTC、美国和中国时区的浏览器均显示相同的北京时刻；
3. 终态 Job 不显示预估文本；`PARTIAL_SUCCESS` 显示“处理流程已完成”及原因；
4. API 排序与原始时间不因显示层时区转换改变。


---

# FILE: IMPLEMENTATION_STATUS.md

# 当前实施状态

> 状态记录日期：2026-09-04。本文唯一记录当前源码能力与自动验证；生产状态只见 [CURRENT_HANDOFF.md](CURRENT_HANDOFF.md)。

## Current repository freeze

- 当前工作分支为 `codex/mac-mini-implementation`；提交前仍须用 git 状态核对，保护同批文档拆分与地图改动。
- 仓库 migration head 为 Alembic 0013；生产版本见 CURRENT_HANDOFF 的实际采样，不由仓库推断。
- 唯一支持的后端为 Mac mini；FastAPI、SQLite/WAL、独立 Worker；其他平台不在当前支持范围。
- 真实验收与自动回归分开记录；规格中的“待实施”、历史 Work Package、未来规划均不得单独认定为当前缺口。

## 当前能力

| 领域 | 已进入源码的能力 | 契约入口 |
| --- | --- | --- |
| Capture / 基础 | URL、正文、DOCX、PDF、XLSX、图像 OCR、音视频；局域网配对与 Session；Source/Evidence | product/PRODUCT_REQUIREMENTS.md、architecture/SECURITY_PRIVACY.md |
| 招聘 / 旅行 | 首批招聘结构化与证据；Place Insight、POI Review、全国交互地图、Marker 生命周期、地图点选 POI 与人工路线 | product/RECRUITMENT_PIPELINE.md、product/TRAVEL_FOOD_PIPELINE.md |
| 视频 | 字幕优先、ASR、校对、笔记/章节、地点、截图、列表封面、保留式删除 | video/VIDEO_AI_NOTE_PIPELINE.md（分篇索引） |
| Bilibili 登录恢复 | 站内扫码、nav 账号验证、Keychain 保存；登录失败进入 NEEDS_USER；核心恢复与非核心截图显式跳过；字幕多轨与官方 CDN Host Policy | video/02-input-transcript.md |
| Job / Replay | 独立 Worker 心跳、协作取消、租约门禁、终态表达、步骤续跑和完整重跑；后端决定 Replay Options | jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md |
| Gateway | 显式 Profile/Stage Policy、路由、Usage、转写质量门禁、Map/Reduce Facts、Cache、Budget、Domain Context、Vision Profile 边界 | ai-gateway/AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md（分篇索引） |
| 稳定性 | API/Worker 通过 OS flock 串行本机 AI；预算按 LOCAL/REMOTE 分账，Cache hit 不计真实模型尝试或预算 | ai-gateway/02-gateway-context.md、ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md |
| 产品 / 运维 | PC/手机 Web、真实状态快照、自定义模型/补充 Prompt、JSONL + SQLite 审计、运维工作台 | product/CONTROL_CENTER.md、operations/LOGGING.md |
| 部署 | Mac mini LaunchAgent 双服务、外置生产 venv Python 3.14、健康内容与 Worker 心跳门禁 | operations/DEPLOYMENT_OPTIONS.md、CURRENT_HANDOFF.md |

## 自动验证记录

2026-09-04：后端 pytest 93 项、Ruff；Node 22.21.0 下前端 ESLint、Vitest 11 项、TypeScript 与 Vite build 通过；0013 在隔离 SQLite 可升级。生产真实视频 Job 已完成字幕、笔记、地点提取与截图，因全部 POI 需要人工确认而为 `PARTIAL_SUCCESS`。真实 Provider/视频结论仅覆盖该样本，不能外推为全部 Provider 验收。

## 未闭环与外部条件

- Gateway 真实 Local/Remote Provider、真实视频、fallback、cache/force-regenerate、预算、取消/Replay 与 Benchmark 仍需按 [生产验收门禁](ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md) 取证；本次未执行。
- Bilibili 扫码、nav 验证和 Keychain 保存已有真实验收记录；曾暴露 VIDEO_HOST_BLOCKED 的现场 Job 未自动重跑，不把修复等同于该 Job 成功。
- 高德、远程 Provider 等需要用户合法提供外部配置；不在文档保存 Secret，不通过编造状态代替配置/验收。
- Vision Profile 绑定边界已实现，不代表已自动运行视觉理解。地图 V2 草案已获用户授权并落实核心 Insight、Review、地图 Runtime、点选 POI 和编辑历史；推荐评分、自动行程与其他规划项仍不自动实施。

## 历史与维护

[实施历史](history/IMPLEMENTATION_HISTORY.md) 保留本轮整理前的逐版本记录（含后来被覆盖的旧状态），默认不读。当前页只保留最新结论和未闭环项；完成项不持续追加长叙事。生产现场只更新 CURRENT_HANDOFF.md；冻结约束只更新 REGRESSION_AND_CHANGE_GUARD.md。新增证据必须写明日期、对象与验证层级。


---

# FILE: operations/DEPLOYMENT_OPTIONS.md

# Mac mini 部署基线

版本：v0.4.6，更新日期：2026-08-28。第一版唯一受支持的后端节点是 Mac mini；项目不再维护其他操作系统的部署脚本、运行时矩阵、硬件假设或回退方案。

## 1. 当前设备与职责

- 节点：Mac mini `Mac16,10`，Apple M4，16 GB 统一内存，arm64；
- 服务：FastAPI、React 生产资源、SQLite/WAL、永久文件、独立 Worker、Playwright、文档解析、OCR、whisper.cpp、Ollama 和可选外部 Provider；
- 客户端：PC 浏览器与手机浏览器，均通过可信局域网访问同一节点；
- 密钥：macOS Keychain；开发环境允许权限受限的本地文件存储。

## 2. 运行形态

```text
PC Browser / Mobile Browser
          │ trusted LAN + session
          ▼
Mac mini
├─ launchd: cn.zhijian.api
├─ launchd: cn.zhijian.worker
├─ FastAPI + WebSocket + React static assets
├─ SQLite + APFS permanent files
├─ Ollama / Metal
├─ whisper.cpp / Metal
└─ macOS Keychain
```

生产服务由 `deploy/macos/manage.py install` 渲染并重启两个用户级 LaunchAgent。生产解释器固定为 Python `3.14.6`，venv 位于 `/Volumes/D/Library/Application Support/Zhijian/venv`，`PYTHONPATH` 直接指向当前仓库 `backend/src`。仓库或数据位于外置卷时，必须为实际 Python 责任进程配置 `SystemPolicyRemovableVolumes`/完全磁盘访问权限；安装后用 `manage.py status` 验证首页正文实际可读和 Worker 心跳，并用 `launchctl print` 核对实际 `program`，而不是只看 PID。关闭自动睡眠、启用断电恢复，并为局域网地址设置 DHCP 保留或固定地址。

## 3. 容量与并发约束

- 16 GB 为 CPU、GPU 与本地模型共享的统一内存；不把它当成独立显存。
- GPU 重任务初始并发固定为 1；ASR、LLM、Vision 不并行抢占统一内存。
- Ollama 用 Metal，whisper.cpp 用 Metal；Core ML encoder 仅在可复现安装且结果一致时启用。
- 较长视频、较大模型或本地运行时不可用时，可按用户策略调用 DeepSeek、MiMo 等兼容 Provider；敏感字段外发规则不变。

## 4. 安全与恢复

- 默认只在本机访问；启用手机访问时才绑定明确 LAN 地址，并采用 4 位配对码换取 HttpOnly Session。
- 不做端口映射、UPnP 或公网暴露；公共/访客网络不得启用可信 LAN 模式。
- API Key、LAN 配对码和平台 Cookie 不进入 SQLite、日志、导出或前端通用接口。
- LaunchAgent 崩溃或重启后自动恢复；Worker 启动先冷导入视频 Pipeline，外置卷不可读时不得领取 Job。未捕获异常立即将当前 Job 标为 `FAILED/WORKER_UNHANDLED_EXCEPTION` 并释放 lease。

## 5. 真实状态原则

PC 控制台硬件、运行时、CPU、内存、磁盘与 Worker 心跳均从 Mac mini 当前状态接口读取。不可使用文档样例、固定 M4 参数或虚构百分比作为页面数据；单项采集失败应明确显示不可用原因。


---

# FILE: product/PRODUCT_REQUIREMENTS.md

# Product Requirements
## AI Personal Inbox / Personal Scout

> 状态：Baseline v0.2
> 当前产品策略：Narrow Product, Extensible Core

---

# 1. 背景与问题

用户希望把日常“随手看到、随手保存”的非结构化信息，转化为后续真正能支持工作和生活决策的结构化结果。

当前典型问题：

- 收藏链接后长期不再打开；
- 微信公众号、视频、网页、附件信息散乱；
- 招聘公告中真正重要的是报名时间、岗位条件、附件，而不是全文摘要；
- 探店/旅行视频真正重要的是地点、地图、推荐理由和后续是否想去，而不是一段视频总结；
- 同一主题的信息散布在不同来源，缺少统一组织；
- 用户不希望频繁手动分类；
- 用户要求 AI 的事实结论必须可追溯，不能随意发挥。

---

# 2. 产品核心目标

用户只需完成一个高频动作：

> **把链接分享或粘贴给系统。**

系统后台自动完成：

```text
Capture
→ Resolve
→ Understand
→ Verify
→ Personalize
→ Materialize
→ Action
```

最终结果不是“AI 摘要”，而是：

- 倒计时；
- 待办；
- 岗位资格列表；
- 需要补充的个人信息；
- 地图；
- 地点清单；
- 想去/去过；
- 证据；
- 来源；
- 可导出数据。

---

# 3. 第一阶段目标用户

## P0
产品作者本人。

## P1
未来具有类似需求的普通个人用户。

第一阶段不做团队、企业、组织协作。

---

# 4. 第一阶段核心场景

## 4.1 Recruitment

用户输入：

- 微信公众号事业编汇总文章；
- 政府招聘公告；
- 招聘 PDF；
- 扫描 PDF、PNG/JPEG 公告；
- DOCX 公告/附件；
- 岗位 Excel；
- 报名说明页面。

系统输出：

- 招聘批次；
- 岗位列表；
- 报名开始/截止；
- 资格审查；
- 缴费；
- 笔试/面试时间；
- 每个岗位的要求；
- 用户是否符合；
- `PASS / FAIL / UNKNOWN / REVIEW`；
- 缺失个人资料；
- 倒计时；
- 待办；
- 咨询建议；
- 所有条件的原文证据。

## 4.2 Travel / Food

用户输入：

- Bilibili 视频；
- 未来扩展抖音、YouTube、快手；
- 普通旅行图文网页。

系统输出：

- 视频/内容来源；
- 字幕；
- 餐馆候选；
- 景点候选；
- 菜品；
- 价格/评价等 Observation；
- 地图 POI；
- 地点列表；
- 作者观点；
- AI 个性化推荐；
- 用户想去/去过/不感兴趣；
- 来源时间码；
- CSV/JSON/GeoJSON 导出。

## 4.3 第一阶段地域与来源基线

- Recruitment 首域：北京市公务员、事业单位招聘及相关考试公告；
- Travel/Food：第一版按中国范围设计；
- POI 与底图首选高德地图；
- 首批真实样本与 Fixture 规则见 `testing/GOLDEN_SAMPLES.md`。

---

# 5. 核心体验原则

## 5.1 默认零操作

成功路径：

```text
分享链接
→ 系统回复“已收下”
→ 后台处理
→ 完成后出现在对应页面
```

用户不应在每次分享后被要求选择分类。

## 5.2 只有异常时才介入

例如：

- 分类不明确；
- 微信需要登录；
- POI 无法唯一确认；
- 招聘专业存在语义歧义；
- 个人档案缺少关键字段；
- 外部页面需要验证码。

这时进入：

`NEEDS_USER`

---

# 6. Intake Policy

第一版允许进入主业务体系：

### Recruitment
- 事业单位招聘
- 公务员/考试
- 招聘岗位
- 招聘附件
- 报名公告

### Travel/Food
- 旅行攻略
- 景点推荐
- 探店
- 餐厅推荐
- 美食视频

### 其他
默认：

`UNSUPPORTED`

UI 可提供：

- 仅保存链接；
- 删除。

第一版不自动创建新的业务分类。

第一版 Capture 支持：

- URL 粘贴；
- PDF / DOCX / XLS / XLSX 文件上传；
- PNG / JPEG 图片上传；
- 直接文本作为补充输入。

上传文件与 URL 入口使用相同的 Job、Evidence 与 Processor Router，不建立第二套处理链。

## 6.1 粘贴内容中的链接识别

粘贴入口必须接受完整分享文案，不能要求用户先手工删除标题、“复制打开”等文字。后端对原始粘贴值先执行输入规范化并分类：

- `URL_ONLY`：去除首尾空白/包裹符号后只有一个 URL；
- `SHARE_TEXT_WITH_URL`：标题、分享话术或说明文字中包含一个可唯一确定的 URL；
- `TEXT_ONLY`：没有 URL，继续作为直接文本处理；
- `MULTIPLE_URLS`：包含多个不能自动唯一确定的内容 URL，需要用户选择。

`SHARE_TEXT_WITH_URL` 成功时，只把提取出的 URL 写入 Source locator 和后续 Resolver payload；标题、分享说明、App 推广文字不得进入分类、网页/视频解析、LLM、Claim 或 Evidence，也不得覆盖来源页面返回的正式标题。

多个重复或仅参数差异但 canonical 后相同的 URL 先去重。若多个候选中只有一个能被专用 Resolver 处理，可自动选择该 URL；若仍有多个不同内容链接，返回稳定的 `CAPTURE_MULTIPLE_URLS` 和候选列表，不静默使用第一个。

URL 提取必须支持换行分享文案、Markdown 链接、尖括号包裹、中文标点结尾和 Bilibili 短链，并保留 URL 内合法的 query/fragment。没有 URL 的普通文段不得被误判成链接任务。

---

# 7. 个人档案策略

不要求用户第一次填写完整档案。

采用渐进式补充：

```text
系统发现：
76 个岗位因为“基层工作经历”未知无法判断

→ 提问：
是否具有 2 年以上基层工作经历？

回答一次
→ 自动重算 76 个岗位
```

个人信息分层：

- 普通偏好；
- 敏感 Profile；
- 高敏感 Local Only。

---

# 8. AI 角色边界

AI 可以：

- 理解自然语言；
- 分类；
- 提取字段；
- 转换 Requirement DSL；
- 识别作者观点；
- 提取地点特征；
- 提出推荐；
- 生成咨询话术；
- 生成建议性 Todo。

AI 不应：

- 自己计算年龄并直接作为事实；
- 自己编造报名日期；
- 自己编造地图坐标；
- 把“相关专业”语义相似直接判定 PASS；
- 把推荐结论伪装成来源事实；
- 自动提交第三方系统。

---

# 9. 事实模型

任何结论归类为：

1. `EXTRACTED`
   - 原文明确存在。

2. `NORMALIZED`
   - 对原文进行标准化，如“8月26日下午5点” → 时间戳。

3. `COMPUTED`
   - 程序计算，如“剩余 7 天”。

4. `INFERRED`
   - AI 推断，如“这家店可能符合你的偏好”。

UI 必须能区分。

---

# 10. 来源冲突

来源优先级参考：

```text
官方原始文件
>
官方网页
>
招聘单位官网
>
官方公众号
>
第三方转载/视频
>
AI 推断
```

发生冲突：

- 不静默覆盖；
- 保留多个 Claim；
- 显示 Source Conflict；
- 当前采用高权威来源；
- 用户可查看全部证据。

---

# 11. Recruitment 用户体验目标

首页优先回答：

1. 最近什么要截止？
2. 哪些岗位我能报？
3. 哪些岗位更值得我关注？
4. 现在我需要做什么？

岗位结果不采用单一虚假百分比，而拆成：

- Eligibility
- Preference
- Urgency
- UserState

Eligibility：
- PASS
- FAIL
- UNKNOWN
- REVIEW

用户状态：
- DISCOVERED
- INTERESTED
- PREPARING
- APPLIED
- DROPPED

---

# 12. Travel 用户体验目标

首页优先回答：

1. 我多久没有旅行？
2. 最近发现了什么值得去的地点？
3. 哪些地点最符合我的偏好？
4. 地图上都在哪里？

地点用户状态：

- DISCOVERED
- SAVED
- PLANNED
- VISITED
- DISMISSED

## 12.1 视频 AI 笔记是一级产物

旅行视频不能只作为地点抽取的临时输入。用户粘贴 Bilibili 链接后，系统必须先形成可独立阅读、版本化、带时间码与来源引用的 AI 视频笔记，再从 Transcript 中提取地点并形成 Place 数据。

处理完成后必须同时提供：

- 同时包含独立摘要与按真实时间线详述的完整视频 AI 笔记；
- 视频页元数据、封面和来源链接；
- 视频完整 Transcript、全部时间码和 TXT 导出；
- 与章节和地点时间码对应的代表性截图；
- 本视频提到的地点列表；
- 已确认地点的地图 Marker；
- 每个地点跨来源聚合的地点归纳笔记。

摘要用于快速判断内容，不得替代时间线正文。时间线章节必须覆盖完整 Transcript，按时间递增并由服务端绑定 Segment；模型返回无效引用时不得静默生成只有百余字摘要的“完成”笔记。完整 Transcript 在服务端固定保留 180 天并自动清理，清理后 Note、时间线详述和截图仍可阅读，页面显示文稿已过期且不再提供导出。

视频详情页面的阅读顺序固定为：Hero → AI 摘要 → 主旨目录 → 按时间线详述 → 地点候选/完整转写。地点候选与完整转写是文章底部的回查工具；页面“正文/全文”指 AI 校对后的提纲和时间线详述，不是连续铺开的 ASR 原文。Hero 使用真实 CoverAsset，缺省时为空/收起，不显示场记板占位。

所有 Transcript Segment 在总结前执行 AI 校对，修正口音、同音字、断句和专有名词，同时保留 raw_text、时间码和 Segment ID。校对模型不得新增事实；无法确定的地名进入 Review。默认预览、总结和 TXT 导出使用 corrected_text，原始转写只用于证据审计。

目录必须归纳每段具体主旨，每项包含时间码、明确标题和一句 thesis；禁止无信息套话。地点候选、Transcript、目录和截图时间码均可跳到对应时间线 Section。

截图必须以 220–280px 缩略图放在对应时间线文字侧面并说明关键内容，支持点击放大、上一张/下一张、Escape 和遮罩关闭。独立宫格和默认全宽 talking head 不再作为主阅读形式。目录使用暖白纸面、朱砂时间码、衬线标题和细分隔线，不使用硬边框表格。完整规范见 `video/VIDEO_NOTE_READING_EXPERIENCE_V042_SPEC.md`。

## 12.1.1 视频笔记列表

列表顶部主操作文案使用“添加视频链接”，不使用“投递视频链接”等系统术语；按钮复用全局 Primary Button 的 40px 高度和 14px 字号。

每条 Video Note Card 必须展示从平台元数据下载并本地缓存的真实视频封面，保持 16:9、object-fit cover 和右下角时长徽标。只有封面下载/校验失败时才显示场记板占位。封面失败不阻塞笔记生成。完整契约见 `video/VIDEO_NOTE_LIST_V043_SPEC.md`。

## 12.1.2 视频笔记删除

视频笔记列表和详情均通过 `…` 菜单提供“删除笔记”，共用同一删除语义。删除 Note 正文、版本、Section、目录和内容投影，但保留共享 Source、VideoAsset、CoverAsset、Transcript、Place 和 Evidence；活跃生成任务阻止删除。第一版不可恢复，必须确认标题和保留边界。完整契约见 `video/VIDEO_NOTE_DELETE_V044_SPEC.md`。

地点归纳笔记的入口至少包括视频笔记、地点列表和地图 Marker，所有入口必须进入同一个 Place Detail，不建立多套地点详情。完整流程、BiliNote 复用边界、DeepSeek 调用、异常回退、数据模型和 UI 决策门见 `video/VIDEO_AI_NOTE_PIPELINE.md`。

## 12.2 地点粒度与名称校正

旅行地点不能只提取城市或泛化区域。第一版必须识别餐馆、景区、街区、步行街、商圈、市场、公园、博物馆、寺庙、村镇、地标、住宿和交通点，并生成景区/街区特色、菜品特色、价格、排队、适合人群、注意事项和作者态度简介。

字幕/ASR 中的地点名称可能存在同音字、错别字、简称或口语表达。系统必须保留原始 `raw_name`，再用高德搜索结合城市、行政区、附近地标和类别校正为 `canonical_name`。无法唯一确认时进入 Review，不加载成正式地图 Marker。

## 12.3 中国大陆全境地图

地图以中国大陆全境为初始视野，不设置默认城市。用户可以平移、缩放、搜索、聚合和按当前视野加载地点；之后恢复上次 viewport。不得在请求、页面标题、fallback 地图或路线创建中硬编码厦门或其他城市。

点击 Marker 在地图内直接展开简略浮窗，显示代表图、名称、类型、地址、特色、关键菜品/体验、来源数和用户状态；点击“查看详情”进入统一 Place Detail。

用户可以自定义添加、隐藏、删除和恢复 Marker。用户创建 Marker 使用软删除；自动抽取 Marker 的“删除”只隐藏地图投影，不删除 Source、Claim、Evidence 或 Place。

设置页必须提供高德 JS API Key、Security Code 和 Web 服务 Key 的录入、保存、状态与真实测试入口。

---

# 13. Control Center 是 MVP 核心

不是开发附属后台。

必须让用户看到：

- 正在处理什么；
- 等待什么；
- 是否等待 PC；
- 哪一步失败；
- ASR 进度；
- POI 解析；
- 招聘解析；
- 当前模型；
- 是否使用外部 API；
- 单步骤重跑；
- 整条任务重试；
- 查看 Evidence；
- 修改模型/ASR/数据目录等配置。

步骤级重跑的含义固定为：中间产物有效期内，从 ERROR 步骤重新执行当前及下游，上游已完成步骤 REUSED；中间产物过期后才退回完整重跑。用户不逐步点击下游，也不能任意选择 from_step。完整契约见 `jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md`。

---

# 14. MVP 非功能目标

## 稳定性
- PC 重启后任务不丢；
- 失败任务可重试；
- Pipeline 可从中间步骤重跑。

## 可审计性
- 所有核心事实可回溯证据；
- 记录模型、Prompt/Parser 版本；
- 记录 Processor 版本。

## 本地优先
- 默认数据保存在 PC；
- 手机通过可信局域网访问 PC，不在手机保存完整业务数据库；
- LAN API、WebSocket 与 Admin API 必须验证访问 Token；
- 外部模型只是可选 Provider；
- API Key 安全存储；
- 浏览器登录态不导出。

## 扩展性
- 新 Resolver 不修改业务 Processor；
- 新 Processor 不修改 Capture；
- 新模型不修改业务代码；
- 新 POI Provider 不修改 Travel Processor。

---

# 15. 第一版不做

详见 README，重点包括：

- GenericProcessor 实际处理；
- 动态 Space；
- Source Watch 自动监控；
- 云端多用户；
- 自动报名；
- 全平台移动端；
- 复杂推荐机器学习；
- 通用 Agent 系统。

这些能力记录于 planning/FUTURE_ROADMAP.md。


---

# FILE: architecture/SYSTEM_ARCHITECTURE.md

# System Architecture

## 1. 架构目标

第一版采用：

> **Mac mini 单节点 + LAN Browser Client + Local First + Local AI First + 可选外部 LLM**

但内部保持清晰模块边界，以便未来平滑演化为：

- 移动端薄客户端；
- 云 Control Plane；
- 多 Worker；
- GenericProcessor；
- SaaS。

---

# 2. 逻辑架构

```text
Clients
  │
  ├─ PC Browser
  └─ Mobile Browser（trusted LAN + access token）
       │
       ▼
React + TypeScript + Vite
       │
       ├─ REST
       └─ WebSocket
       ▼
FastAPI
       │
       ├─ Capture API
       ├─ Product Query API
       ├─ Admin API
       └─ Job WS
       │
       ▼
SQLite + Local Files
       ▲
       │
Independent Worker
       │
       ├─ Resolver Registry
       ├─ Video Resolver Registry
       │    ├─ Bilibili Resolver
       │    ├─ Subtitle Fetcher
       │    └─ yt-dlp Media Adapter
       ├─ Cover Fetcher / Derivative Generator
       ├─ Processor Router
       ├─ Recruitment Processor
       ├─ TravelFood Processor
       ├─ Evidence Validator
       ├─ Rule Engine
       ├─ POI Resolver
       ├─ ASR Provider
       ├─ Transcript Corrector
       ├─ AI Note Generator
       ├─ Screenshot Planner / Frame Extractor
       ├─ Place Note Builder
       └─ LLM Router
             │
             ├─ Ollama
             ├─ OpenAI Provider
             └─ OpenAI-Compatible Provider（DeepSeek / Xiaomi MiMo / custom）
```

---

# 3. 物理运行架构

第一版不做微服务。

开发阶段至少三个进程：

```text
1. FastAPI / Uvicorn
2. Worker Process
3. React Vite Dev Server
```

手机和 PC 浏览器通过同一可信局域网访问 Mac mini。开发与生产都必须支持可配置监听地址；默认不做公网暴露。所有非 localhost 的 REST/WebSocket 请求必须带有效访问 Token，Admin API 不允许匿名访问。

生产/桌面封装后：

```text
launchd
 ├─ cn.zhijian.api
 ├─ cn.zhijian.worker
 └─ FastAPI 同源提供 UI
```

后续可使用 Tauri 封装，但桌面壳不属于 MVP 前置条件。

---

# 4. FastAPI 职责

允许：

- API；
- WebSocket；
- 请求校验；
- 配置读写；
- 查询；
- Job 创建；
- 结果读取。

禁止：

- 在 HTTP 请求中直接跑 Whisper；
- 长时间执行 LLM；
- 下载大视频；
- 做长时 Playwright 抓取；
- 执行完整 Recruitment/Travel Pipeline。

长任务必须写入 `jobs`。

---

# 5. Worker 职责

Worker 循环：

```text
lease job
→ 执行
→ heartbeat
→ 更新进度
→ 写结果
→ 完成 / 失败 / NEEDS_USER
```

Worker 初期只有一个。

未来扩展多 Worker 时，不改变 Processor 接口。

---

# 6. Job Lease

Job 最少包含：

- id
- type
- status
- priority
- current_step
- progress
- lease_owner
- lease_expire_at
- heartbeat_at
- retry_count
- error
- created_at
- started_at
- finished_at

若 PC 异常关闭：

```text
RUNNING
+ heartbeat stale
→ lease expired
→ QUEUED
```

---

# 7. 核心模块

## capture/
统一接受 URL/Text/File。

Capture 在创建 Source/Job 前执行 `InputNormalizer`：区分纯 URL、带标题/分享话术的单链接文本、无链接正文和多链接文本。唯一 URL 被选中后，周围文字不得进入 Resolver、Classifier、LLM 或 Evidence；多链接歧义在 Intake 层返回候选，不启动下游网络请求。

## resolvers/
解决“如何读取内容”。

## processors/
解决“内容对应什么业务”。

## evidence/
解决“为什么这个结论可信”。

## ai/
解决“用哪个模型、如何结构化调用”。

## asr/
解决“如何转录音视频”。

## transcript_correction/
在 Note 生成前将 raw Transcript 分块送入 LLM 校对，保持 Segment ID/顺序/时间码不变，输出 corrected_text、置信度与变更原因；服务端负责覆盖率和无新增事实校验。

## poi/
解决“现实地点解析”。

## screenshots/
根据 Note Section、PlaceMention 与 Transcript 时间码规划并提取代表帧，执行清晰度、黑帧和重复检测；不等同于默认全视频多模态理解。

## covers/
从 VideoAsset 平台元数据下载真实封面，校验 HTTPS host、MIME、文件头、尺寸和字节数，按内容哈希保存原图并生成 16:9 列表衍生图。封面失败不阻塞 Note，列表使用明确占位。

## documents/
解决 PDF、DOCX、XLS/XLSX 与图片型文档的归一化。

## ocr/
解决扫描 PDF、PNG/JPEG 的中文 OCR、页码/边界框定位与低置信 Review。

## jobs/
解决“后台长任务”。

## repositories/
隔离业务层与数据库。

---

# 8. Resolver Registry

统一：

```python
class Resolver:
    def can_handle(self, source) -> bool: ...
    async def resolve(self, source) -> ResolvedContent: ...
```

ResolvedContent：

```text
title
author
published_at
metadata
segments[]
links[]
attachments[]
media[]
```

原则：

- Resolver 不做招聘判断；
- Resolver 不做推荐；
- Resolver 不修改 Profile。

视频 Resolver 的首个生产实现为 Bilibili，参考并适配 BiliNote 的 URL 解析、字幕优先、yt-dlp 下载和平台兼容逻辑。第三方代码必须封装在适配层；至简 Job、数据库、Evidence、POI 与 UI 不依赖 BiliNote 内部类型。完整边界见 `video/VIDEO_AI_NOTE_PIPELINE.md`。

---

# 9. Processor Router

当前路由：

```text
Recruitment
TravelFood
Unsupported
```

长期：

```text
Recruitment
TravelFood
Generic
Shopping
Learning
...
```

Processor 接口概念：

```python
class Processor:
    def can_handle(self, content) -> bool: ...
    async def process(self, content, context): ...
```

---

# 10. Provider 抽象

## LLMProvider
- OllamaProvider
- OpenAIProvider
- OpenAICompatibleProvider（DeepSeek、Xiaomi MiMo、自定义兼容端点）

## ASRProvider
- WhisperCppProvider
- FasterWhisperProvider（预留）
- CloudASRProvider（预留）

## POIProvider
- 第一版实现 AMapPOIProvider；
- 业务代码不得依赖具体厂商。

地图前端第一版使用高德地图 JS API 2.0。中国大陆 POI 的 `coordinate_system` 显式记录为 `GCJ02`，严禁把 GCJ-02 静默标成 WGS84；GeoJSON 导出必须附坐标系元数据与来源 Provider。

地图运行时以中国大陆全境为初始 viewport，通过 `bbox + zoom` 查询 Marker/cluster，不绑定默认城市。Marker 是 Place 的投影，用户的新增/隐藏/软删除状态由独立 Marker State 保存；地图浮窗读取轻量 Preview，详情页读取完整 Place Note。

---

# 11. Mac mini 本地 AI

Apple Silicon 使用 Metal；统一内存下 GPU 重任务初始并发为 1，ASR、LLM 和 Vision 不默认并行。完整运行时、内存约束与常驻规则见 `operations/DEPLOYMENT_OPTIONS.md`。

---

# 12. GPU Scheduler

第一版可以非常轻：

```text
GPU semaphore = 1
```

重量级任务：

- Whisper
- 主力 LLM
- Vision

串行。

轻量任务可并行：

- HTTP；
- Playwright；
- Excel；
- SQLite；
- ffmpeg 部分 CPU 工作；
- 文件下载。

后续根据实际显存与稳定性将并发调至 2。

---

# 13. 文件存储

```text
data/
├─ app.db
├─ permanent/
│  ├─ sources/
│  ├─ snapshots/
│  ├─ transcripts/
│  ├─ evidence/
│  └─ exports/
├─ browser/
│  └─ profile/
├─ models/
├─ cache/
│  ├─ video/
│  ├─ audio/
│  ├─ frames/
│  └─ temp/
└─ logs/
```

视频策略：

```text
下载视频（临时）
→ 抽音频
→ ASR
→ 提取必要 Evidence Frames
→ 删除原视频/音频
→ 永久保留 Transcript + Evidence
```

---

# 14. SQLite 策略

第一版 SQLite 足够。

开启：
- WAL；
- foreign_keys。

设计要求：
- 所有访问经过 Repository；
- migrations 使用 Alembic；
- JSON 仅用于适合嵌套的 AST/metadata，不把全部业务塞 JSON。

未来若迁 PostgreSQL，尽量限制在 Repository/Database 层。

---

# 15. Pipeline Replay

每一步必须有：
- input artifact；
- output artifact；
- status；
- version；
- error。

用户可：

```text
重新解析岗位条件
```

不必：
- 重新抓微信；
- 重新下载视频。

运行日志中的错误事件可作为 Replay 入口，但不成为执行器：`SystemEvent(entity_type=job, entity_id=job.id)` → Job 服务校验当前状态与来源事件 → 同一 Job 新 attempt 入队 → Worker 按 Pipeline 顺序执行。日志页只提交 `source_event_id`，不能修改步骤状态、选择 Provider 或跳过依赖。

错误恢复使用 Job 服务的步骤级 Replay：Step Artifact 在默认 24 小时窗口内有效时，上游完成步骤 REUSED，从失败步骤开始顺次执行当前及下游；到期或输入/版本失效后只允许完整重跑。日志和任务详情只展示 Replay Options，不允许任意 from_step，也不让用户逐个点击后续步骤。完整契约见 `jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md`。

Worker 进程存活与任务进度是不同信号。进程心跳由独立于同步 Job 执行循环的轻量通道定期持久化，不能依赖被外部模型、FFmpeg 或网络调用阻塞的主领取循环；Job 心跳只由真实阶段与 batch 活动推进。取消请求写入持久状态后，长模型批次在请求边界检查该状态并停止新请求，随后释放 lease；完整重跑必须等待这一确认。

---

# 16. Partial Materialization

不要求一个大任务全部完成后才出结果。

例如：
- 贵州 43 地点：36 个确认就先显示 36；
- 招聘 500 岗位：可分批 materialize。

这是长任务 UX 的核心。

---

# 17. 未来云化演进

第一版：
```text
手机 ↔ PC
```

未来：
```text
Clients
  ↓
Cloud Control Plane
  ↓
Execution Router
  ├─ Home PC
  ├─ Cloud CPU
  └─ Cloud GPU
```

因为当前 Processor/Provider/Job 已抽象，迁移时无需重构业务算法。


---

# FILE: architecture/DATA_MODEL.md

# Data Model

## 1. 数据建模原则

1. 原始来源与业务结果分离。
2. Claim 与 Evidence 分离。
3. “视频中提到某地点”与“现实 POI”分离。
4. 招聘资格与用户偏好分离。
5. 个人 Profile 与 Preference 分离。
6. 原始行为事件与推导出的 Preference 分离。
7. AST/复杂嵌套规则可用 JSON；核心实体用关系表。
8. 所有结果保留 processor/model/version。

---

# 2. 核心领域对象

## ContentItem
用户一次输入。

## Source
外部信息源。

## Snapshot
某 Source 某次抓取内容。

## Segment
可定位的最小文本/字幕/表格单位。

## Claim
事实、标准化结果、计算或推断。

## Evidence
支持某 Claim 的来源定位。

## RecruitmentNotice
一场招聘。

## Position
具体岗位。

## Requirement
岗位/公告资格规则 AST。

## PlaceMention
内容中提到的地点。

## Place
解析后的现实 POI。

## UserProfile
客观个人条件。

## Preference
主观偏好。

## Job / JobStep
后台处理工作。

---

# 3. Content / Source

## content_items

建议字段：

```text
id
input_type
original_url
raw_text
capture_input_kind
selected_url
capture_candidate_count
discarded_text_length
raw_input_hash
status
processor_hint
created_at
updated_at
```

`capture_input_kind`：`URL_ONLY / SHARE_TEXT_WITH_URL / TEXT_ONLY / MULTIPLE_URLS`。URL 任务的 `raw_text` 必须为空；分享文案只参与瞬时 URL 提取，默认不持久化全文。`raw_input_hash` 用于排错和幂等，`discarded_text_length` 只记录被忽略文本长度。

## sources

```text
id
content_item_id
source_type
platform
url
external_id
title
publisher
author
published_at
authority_level
metadata_json
created_at
```

URL Source 的 `url/locator` 只能写 Input Normalizer 选中的 URL。页面或视频解析得到的正式 title 才写 `sources.title`；粘贴文案中的标题不得覆盖正式元数据。

文件型 Source 的 `metadata_json` 至少保存：原始文件名、MIME、字节数、内容哈希、解析器与 OCR 版本；文件正文仍通过 Snapshot/Segment 建模。

## source_snapshots

```text
id
source_id
fetched_at
content_hash
raw_path
normalized_path
metadata_json
```

## source_relations

```text
id
from_source_id
to_source_id
relation_type
evidence_segment_id
```

relation_type：
- references
- attachment
- original_source
- registration
- supplement
- supersedes
- related
- derived_from

---

# 4. Segment

## segments

```text
id
snapshot_id
segment_type
sequence_no
text
raw_text
corrected_text
locator_json
metadata_json
```

视频 Segment 的 `raw_text` 保存平台字幕/ASR 原文，`corrected_text` 保存 AI 校对稿；`text` 作为兼容投影默认返回 corrected_text，未校对时不得静默冒充已校对。校对不得改变 Segment ID、sequence_no 或时间码。

locator 示例：

网页：
```json
{"css_path":"...", "start_offset":10, "end_offset":50}
```

视频：
```json
{"start_ms":197200, "end_ms":211500}
```

Excel：
```json
{"sheet":"岗位计划表","row":27,"cell":"H27"}
```

PDF：
```json
{"page":7,"block":13}
```

DOCX：
```json
{"part":"document","paragraph":18,"run_start":2,"run_end":5}
```

OCR：
```json
{"page":3,"bbox":[120,240,920,318],"ocr_confidence":0.91}
```

---

# 5. Claim / Evidence

## claims

```text
id
subject_type
subject_id

claim_type
field
value_json

confidence

processor
processor_version
model_provider
model_name
parser_version

created_at
```

claim_type：
- EXTRACTED
- NORMALIZED
- COMPUTED
- INFERRED

## claim_evidences

```text
claim_id
segment_id
evidence_role
```

一个 Claim 可以多证据。
一个 Segment 可以支持多个 Claim。

## claim_relations

```text
from_claim_id
to_claim_id
relation_type
created_at
```

relation_type：
- derived_from
- normalizes
- computes_from
- conflicts_with
- supersedes

`NORMALIZED`、`COMPUTED` Claim 必须通过关系指向其输入 Claim；来源冲突不得只靠覆盖最终字段表达。

---

# 6. Recruitment

## recruitment_notices

```text
id
primary_source_id
title
organization
region
registration_start
registration_deadline
exam_date
interview_date
registration_url
status
created_at
```

## positions

```text
id
notice_id
position_code
name
organization
headcount
raw_row_json
created_at
```

## requirements

```text
id
notice_id nullable
position_id nullable

raw_text
dsl_version
ast_json

parser_model
parser_version
evidence_status

created_at
```

## requirement_matches

```text
id
requirement_id
position_id
profile_subject

status
reason_code
details_json
matched_evidence_json
created_at
```

status:
- PASS
- FAIL
- UNKNOWN
- REVIEW

## position_matches

```text
id
position_id
eligibility_status
preference_level
urgency_level
user_state
summary_json
updated_at
```

user_state:
- DISCOVERED
- INTERESTED
- PREPARING
- APPLIED
- DROPPED

---

# 7. User Profile

## profile_fields

```text
id
field_key
value_json
sensitivity
source
verified
updated_at
```

sensitivity:
- NORMAL
- SENSITIVE
- LOCAL_ONLY

## education_experiences

```text
id
level
school
raw_major_name
mapped_catalog_id
mapped_major_code
degree
graduation_date
verified
```

必须保留 `raw_major_name`，不允许映射结果覆盖原始专业名称。

## work_experiences（可在 Phase 2 引入）

```text
id
organization
role
start_date
end_date
description
tags_json
```

## certificates（可独立表或 profile JSON）

---

# 8. Major Catalog

## major_catalogs

```text
id
authority
name
version
education_level
effective_date
source_url
snapshot_id
```

## major_entries

```text
id
catalog_id
code
name
parent_code
level
aliases_json
```

## major_equivalences

```text
id
from_catalog_id
from_code
to_catalog_id
to_code
relation_type
evidence_source_id
```

---

# 9. Deadline / Todo

## deadlines

```text
id
subject_type
subject_id
deadline_type
at
claim_id
status
```

## todos

```text
id
subject_type
subject_id
title
todo_type
source_type
due_at
status
metadata_json
```

source_type：
- FACT_BASED
- SYSTEM_SUGGESTED

---

# 10. Travel / Food

## video_assets

```text
id
source_id
platform
canonical_url
external_video_id
part_number
external_part_id
title
author
cover_url
duration_ms
published_at
metadata_json
metadata_hash
resolver_version
created_at
updated_at
```

`platform + external_video_id + part_number` 用于识别同一个视频分 P；原始 URL 仍保存在 Source，不能被 canonical URL 覆盖。

## video_cover_assets

```text
id
video_asset_id
source_url
local_path
derivative_path
content_hash
content_type
width
height
byte_size
status
error_code
fetched_at
created_at
```

`status`：`PENDING / READY / UNAVAILABLE / INVALID`。VideoAsset.cover_url 保存平台元数据；CoverAsset 表示已下载并可由本地 API 服务的封面。原图按 SHA-256 去重，列表 672×378 WebP 衍生图可重建；不同 Note Version 复用同一 VideoAsset/CoverAsset。

## transcripts

```text
id
video_asset_id
snapshot_id
source_kind
language
full_text_hash
provider
model
adapter_version
correction_status
correction_provider
correction_model
correction_prompt_version
correction_coverage
status
created_at
```

`source_kind`：

- CLIENT_PREFETCHED_SUBTITLE
- PLATFORM_SUBTITLE
- YT_DLP_SUBTITLE
- ASR

Transcript 的正文通过通用 `segments` 表保存，视频 Segment 的 `locator_json` 至少包含 `start_ms/end_ms`。

`correction_status`：`PENDING / CORRECTING / CORRECTED / REVIEW / FAILED / PURGED`。每次重新校对生成新 Transcript Version 或版本化 Correction，不覆盖 raw。默认 Note、目录、页面预览和 TXT 导出使用 corrected_text；raw 只用于 Evidence/差异审计。

视频 Transcript 还必须保存 `retention_until` 与 `purged_at`。`metadata_json` 只能保存 `fingerprint_sha256`，不得保存由“时间码 + 正文”拼成的全文 fingerprint。完整转写固定保留 180 天；到期后 Transcript/Segment 行作为时间轴 tombstone 保留，但 `Transcript.text`、`Segment.text/raw_text/corrected_text` 与关联 `Evidence.quote` 被清空，`segment_count` 可保留原始数量供审计，API 依据 `purged_at` 返回 410。Note Section 的服务端时间范围和截图实际时间码不随文稿清理删除。

Whisper.cpp JSON 的 `offsets.from/to` 单位为毫秒。写入新 Transcript Version 前必须校验时间单调性及末段与 `VideoAsset.duration_ms` 的合理关系；约 10 倍的历史错误时间轴通过新版本修复，不原地覆盖旧版本。

## ai_notes / ai_note_versions

```text
ai_notes:
id
content_item_id
video_asset_id
current_version_id
created_at
updated_at

ai_note_versions:
id
ai_note_id
version_no
markdown
structured_json
input_hash
provider
model
prompt_version
template_version
status
created_at
```

重跑生成新版本，不静默覆盖旧 Markdown。`structured_json` 保存章节与 Segment 引用，但不能替代 Transcript、Claim 或 Evidence。

## ai_note_sections

```text
id
note_version_id
heading
thesis
summary
bullets_json
anchor_id
sequence_no
start_ms
end_ms
markdown
segment_ids_json
```

## video_screenshots

```text
id
video_asset_id
note_version_id
note_section_id nullable
place_mention_id nullable
segment_id nullable
planned_timestamp_ms
actual_timestamp_ms
image_path
content_hash
perceptual_hash
width
height
quality_score
selection_reason
caption
content_role
status
created_at
```

截图必须能回到视频时间码。`perceptual_hash` 用于去重；`caption/content_role` 必须说明地点、菜品、景区特色、路线、价格或关键结论，不能统一写“章节起始时间码代表帧”。截图是来源派生资产，不代替 Transcript Evidence。被 Note/Place 页面引用的截图进入永久派生存储，任务视频仍按缓存 TTL 清理。

## place_notes / place_note_versions

```text
place_notes:
id
place_id
current_version_id
created_at
updated_at

place_note_versions:
id
place_note_id
version_no
markdown
structured_json
input_hash
provider
model
prompt_version
status
created_at
```

Place Note 聚合多个 Mention/Observation/Source。事实必须通过 Claim/Evidence 回到 Transcript Segment；用户状态变化不直接改写事实版本。

## map_marker_states

```text
id
place_id
origin
visibility
custom_label nullable
created_by
created_at
updated_at
deleted_at nullable
```

`origin`：`AI_EXTRACTED / USER`。`visibility`：`VISIBLE / HIDDEN / DELETED`。用户 Marker 删除为软删除；自动 Marker 删除只改为 `HIDDEN`。Marker 是 Place 的投影，不能保存第二份完整地点详情。

## places

```text
id
name
canonical_name
place_type
origin
country
province
city
district
address
latitude
longitude
coordinate_system

external_provider
external_poi_id

resolution_status
metadata_json
created_at
```

`origin` 至少区分 `AI_EXTRACTED / USER / IMPORTED`。用户直接点选地图坐标时，`resolution_status=CONFIRMED` 只能表示 `USER_CONFIRMED`，不得伪装成高德 POI 命中；具体确认来源保存于 metadata。

resolution_status:
- CANDIDATE
- CONFIRMED
- REVIEW
- UNRESOLVED
- REJECTED

中国大陆高德 POI 的 `coordinate_system` 为 `GCJ02`。任何导出都必须携带该字段，不得默认标记为 WGS84。

## place_mentions

```text
id
source_id
segment_id
raw_name
suggested_name
place_type
city_hint
district_hint
resolved_place_id
resolution_confidence
status
metadata_json
```

`raw_name` 永远保留字幕/ASR 原文；高德确认名称写入关联 Place 的 `canonical_name`，不得覆盖原始 Mention。

## place_observations

```text
id
place_id
source_id
segment_id
observation_type
value_json
claim_id
observed_at
```

例如：
- price
- dish
- author_opinion
- warning
- ranking
- recommended_season

---

# 11. Preference

## preference_events

```text
id
target_type
target_id
event_type
created_at
metadata_json
```

event_type：
- SAVE
- DISMISS
- VISITED
- PLANNED
- LIKE
- DISLIKE

## preferences

```text
id
preference_key
weight
source_type
confidence
version
updated_at
```

source_type：
- EXPLICIT
- BEHAVIOR
- INFERRED

优先级：
EXPLICIT > BEHAVIOR > INFERRED

## visit_events

```text
id
place_id
trip_id nullable
visited_at
rating nullable
notes nullable
```

地点当前用户状态由 `preference_events` / `visit_events` 投影得到；若为查询性能物化缓存，缓存必须可从事件重建，不能成为唯一事实源。

---

# 12. Jobs

## jobs

```text
id
job_type
status
priority

content_item_id
subject_type
subject_id

current_step
progress

lease_owner
lease_expire_at
heartbeat_at

retry_count
max_retries
idempotency_key
error_code
error_message

created_at
started_at
finished_at
```

`idempotency_key` 对同一 Capture/Step 的重复提交建立唯一约束。Job Lease 必须通过单条条件更新原子抢占；Step 输出与领域写入按版本幂等 upsert，防止 Worker 崩溃恢复后重复物化。

status：
- QUEUED
- RUNNING
- DONE
- FAILED
- RETRYABLE
- NEEDS_USER
- CANCELLED

## job_steps

```text
id
job_id
attempt_id
step_name
status
progress
input_ref_json
output_ref_json
version
error_message
started_at
finished_at
```

上游步骤在新 Attempt 中被复用时，新增 Step 记录或 Attempt-Step 投影状态为 `REUSED`，不得改写旧步骤时间与输出。

## job_step_artifacts

```text
id
job_id
attempt_id
step_name
artifact_type
artifact_ref_json
input_hash
content_hash
schema_version
producer_version
status
created_at
replayable_until
invalidated_at nullable
```

`status`：`AVAILABLE / EXPIRED / INVALIDATED / MISSING`。默认 Replay Cache TTL 使用 `video_cache_ttl_hours=24`。步骤级续跑只有在所有依赖 Artifact 可用且输入/版本一致时成立；TTL 到期后由 Worker 清理文件并把状态改为 EXPIRED，持久 Source/Transcript/Note/Evidence 不属于本表的临时缓存。

## settings / secret references

非敏感设置可存 SQLite；API Key、LAN Token 与其他 Secret 只保存 macOS Keychain 引用。数据库字段包含 `setting_key/value_json/updated_at` 与 `secret_key/secret_ref/updated_at`，不得存 Secret 明文。

---

# 13. 不建议第一版建的表

- dynamic_spaces
- skill_marketplace
- agent_memory
- vector_embeddings
- cloud_workers
- tenants
- payments

它们均属于未来能力，不提前实现。


---

# FILE: product/RECRUITMENT_PIPELINE.md

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

第一阶段优先覆盖北京市公务员、事业单位招聘及相关考试公告；真实样本见 `testing/GOLDEN_SAMPLES.md`。

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
OCR（扫描 PDF / 图片时）
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

MVP 文档矩阵：

- HTML；
- 文本型 PDF；
- 扫描 PDF；
- DOCX；
- XLS/XLSX；
- PNG/JPEG。

OCR 必须保留页码、边界框、OCR 置信度与原始图片引用。低置信 OCR 不可直接支撑关键日期或 HARD Requirement 的自动确定结论，必须进入 `REVIEW`。

---

# 7. Excel Normalizer

处理：

- 多 Sheet；
- 标题行不固定；
- 合并单元格；
- 隐藏列；
- 备注列；
- 列名差异。

`.xlsx` 先用 openpyxl 读取；旧 `.xls` 通过独立 SpreadsheetReader 适配器处理，Phase 0A 按 macOS arm64 安装、格式覆盖和维护状态选择，不允许把 `.xls` 伪装成 openpyxl 支持。

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


---

# FILE: product/TRAVEL_FOOD_PIPELINE.md

# Travel / Food Pipeline

> 视频链接到 AI 笔记、BiliNote 复用边界、DeepSeek 分块总结、地点归纳笔记与多入口导航的冻结契约见 `video/VIDEO_AI_NOTE_PIPELINE.md`。本文件继续定义 Travel/Food 的领域抽取、POI、偏好和地图规则；发生冲突时，专项文档中的视频链路规则优先。

## 1. 目标

将视频/图文中的旅行与探店信息转换成：

- 带时间码 Transcript；
- 地点候选；
- 现实 POI；
- 餐厅/景点；
- 菜品/价格/作者评价；
- 用户偏好匹配；
- 地图；
- 收藏/想去/去过；
- 可导出数据；
- 全程可追溯 Evidence。

第一版地域为中国范围，POI 与地图首选高德；真实样本见 `testing/GOLDEN_SAMPLES.md`。

---

# 2. Pipeline

```text
CAPTURE
↓
RESOLVE_SOURCE
↓
FETCH_METADATA
↓
FETCH_SUBTITLE
↓
DOWNLOAD_MEDIA（必要时）
↓
ASR
↓
SEGMENT
↓
EXTRACT_PLACES
↓
RESOLVE_POI
↓
DEDUPLICATE
↓
MATCH_PREFERENCES
↓
MATERIALIZE
↓
CLEAN_CACHE
```

`FETCH_SUBTITLE / DOWNLOAD_MEDIA / ASR` 之前必须完成平台 URL 规范化和视频元数据抓取；`SEGMENT` 后先生成版本化 AI 视频笔记，再执行地点结构化抽取。AI 笔记是用户可阅读的一级产物，但地点事实仍必须引用 Transcript Segment，不得只引用 AI Markdown。

完整顺序为：

```text
VALIDATE_LINK
→ FETCH_METADATA
→ FETCH_SUBTITLE
→ DOWNLOAD_AUDIO / ASR（仅字幕不可用时）
→ NORMALIZE_TRANSCRIPT
→ GENERATE_AI_NOTE
→ EXTRACT_PLACES
→ RESOLVE_POI
→ BUILD_PLACE_NOTES
→ PLAN_SCREENSHOTS
→ DOWNLOAD_VIDEO_FOR_FRAMES
→ EXTRACT_SCREENSHOTS
→ MATERIALIZE
→ CLEAN_CACHE
```

---

# 3. Transcript First

优先：
1. 平台已有字幕；
2. 浏览器/登录态字幕；
3. 音频下载；
4. whisper.cpp。

第一版不默认做全视频视觉分析。

---

# 4. Transcript Segment

每段保存：

```text
start_ms
end_ms
text
segment_id
```

例如：

```text
03:12.480 - 03:27.120
“今天第一家来到的是……”
```

后续餐厅/景点 Claim 直接挂该 segment。

每个 Segment 同时保留 raw_text 与 AI corrected_text。地点/菜品/特色提取默认使用 corrected_text，Evidence 详情允许对照 raw；校对不得改变 Segment ID 和时间码。无法确定的同音地名先标 Review，再交给高德候选校正，不能由校对模型直接生成 canonical Place。

---

# 5. Extraction 不等于 Summary

第一阶段 AI 任务：

- PlaceCandidate[]
- RestaurantCandidate[]
- DishCandidate[]
- PriceClaim[]
- OpinionClaim[]
- WarningClaim[]
- RankingClaim[]
- RegionMention[]

摘要是辅助，不是核心产物。

---

# 6. PlaceMention vs Place

必须分开。

PlaceMention：
> 内容中“说到了什么”。

Place：
> 现实地图中“到底是哪一个地点”。

流程：

```text
PlaceMention
→ POI Resolution
→ Place
```

多个视频可指向同一个 Place。

---

# 7. POI Resolver

匹配依据：

- 名称相似；
- 城市；
- 区域；
- 附近地标；
- 地址上下文；
- 类别。

状态：

- CONFIRMED
- REVIEW
- UNRESOLVED
- REJECTED

只有 CONFIRMED 默认进入地图。

MVP 实现 `AMapPOIProvider`：使用高德 Web 服务进行候选搜索，优先传城市/adcode 与 `citylimit` 收敛歧义；保存 Provider、POI ID、原始候选响应哈希与 `GCJ02` 坐标系。前端使用高德地图 JS API 2.0。

POI 解析同时承担名称校正：保留转写原文 `raw_name`，高德候选命中后保存 `canonical_name` 与 aliases。必须结合地点类型、城市/区县、附近地标、地址上下文和视频其他地点进行确定性打分；无法唯一确认时进入 Review。城市/省份只作为上下文，不因为被提及就默认创建 Marker。

## 7.1 地点类型与简介

第一版地点粒度至少包括餐馆、景区、街区、步行街、商圈、市场、公园、博物馆、寺庙、村镇、地标、住宿和交通点。每个 PlaceMention 生成结构化 `PlaceBrief`：

- 景区/街区/店铺特色；
- 推荐菜品或核心体验；
- 价格、排队、环境与营业提示；
- 适合人群、季节与注意事项；
- 作者态度和引用时间码；
- AI 归纳，明确与来源观点区分。

## 7.2 中国大陆全境地图

地图首次进入显示中国大陆全境，不设置默认城市；之后恢复用户上次 viewport。请求以 `bbox + zoom` 为主，city/district 只作为可选筛选。全国尺度使用聚合，放大后展开 Marker。点击 Marker 在地图内打开浮窗/侧浮层，显示代表图、地址、特色、关键菜品/体验、来源数和用户状态，再通过“查看详情”进入统一 Place Detail。

用户可创建 Marker：搜索/逆地理编码优先取得规范 POI，直接点选坐标时标为 `USER_CONFIRMED`。用户 Marker 删除为软删除；自动 Marker 删除只改变地图可见性，不删除 Place/Evidence。所有 Marker 返回 `marker_id + place_id + origin + visibility`。

---

# 8. 禁止 LLM 生成地图坐标

坐标只能来自：

- POI Provider；
- 用户确认；
- 可信地理数据。

LLM 仅能提取地点候选和上下文。

---

# 9. PlaceObservation

内容来源对地点的描述不能直接覆盖 Place。

例如：
视频 A：人均 80
视频 B：人均 120

保存两条 Observation。

类型：
- price
- dish
- author_opinion
- warning
- ranking
- recommended_season
- queue
- environment

---

# 10. 作者观点 vs AI 推荐

作者观点：
`SOURCE_OPINION`

AI 个性化：
`PERSONAL_INFERENCE`

UI 必须明确区分。

---

# 11. 偏好三层

## Explicit
用户明确设置。

## Behavior
收藏/忽略/去过等行为推导。

## Inferred
AI 推断。

优先级：
Explicit > Behavior > Inferred

---

# 12. PreferenceEvent

所有行为先存事件：

- SAVE
- DISMISS
- VISITED
- PLANNED
- LIKE
- DISLIKE

不要直接在点击时永久修改一个神秘分数。

PreferenceLearner 可随时重算。

---

# 13. Trait-based Preference v1

第一版不用复杂向量推荐。

地点可提取 Traits：

- nature
- urban
- historic
- food
- hiking
- island
- commercial
- crowded
- local
- luxury
- budget
- family
- nightlife

Preference 有权重。

推荐理由来自贡献最大的 Trait。

---

# 14. 避免虚假匹配度

不显示：
“匹配度 87%”

展示：
- 优先关注
- 值得考虑
- 一般
- 不符合偏好

并提供解释：

```text
✓ 海岛
✓ 适合步行探索
✓ 本地饮食
△ 游客较多
```

---

# 15. 地点状态

- DISCOVERED
- SAVED
- PLANNED
- VISITED
- DISMISSED

未来 Trip Planner 可直接复用。

---

# 16. Visit / Trip

第一版至少有 VisitEvent。

用于：
- 记录去过；
- 计算“距离上次旅行多少天”。

完整 Trip 可后续加入。

---

# 17. Partial Materialization

贵州 43 地点：

```text
36 Confirmed
5 Review
2 Unresolved
```

主地图立即展示 36。
任务仍可继续。

---

# 18. 视频截图与视觉边界

代表性截图属于第一版视频笔记必备产物，不再只做未来预留。系统根据 Note Section、PlaceMention 和 Transcript 时间码生成计划，下载受限画质视频流并用 FFmpeg 抽帧；每个主要地点 1–3 张，整篇默认 3–12 张。

截图必须过滤黑帧、模糊帧、过曝/欠曝和感知重复帧，并保存实际时间码、文件哈希、尺寸、选择原因以及 Section/PlaceMention/Segment 关系。当前版本使用时间码附近的候选帧与确定性画质规则避开转场；广告语义识别不使用视觉模型，属于后续独立能力。平台禁止下载或资源超限时，笔记可 `PARTIAL_SUCCESS`，但必须明确截图缺失原因。

第一版不默认把所有帧发送给 VisionProvider。店招、菜单、路牌和屏幕价格的多模态识别仍作为后续独立能力；启用时生成新的 Visual Claim/Model Version，不能覆盖 Transcript Evidence。

---

# 19. 视频缓存

临时：
- video
- audio
- full frames

永久：
- transcript
- evidence frames
- note screenshots
- thumbnail
- metadata
- claims

---

# 20. 导出

第一版：
- CSV
- JSON
- GeoJSON

GeoJSON 必须显式附带坐标来源和 `coordinate_system`。中国大陆高德坐标不得静默声明为 WGS84；若未来需要跨坐标系输出，必须由独立、可测试的转换策略完成并标注转换来源。

导出字段尽可能带：
- name
- coordinates
- source_title
- source_url
- source_timestamp
- recommendation_reason
- user_status

---

# 21. Travel Dashboard

TravelDashboardVM：

- days_since_last_trip
- map_places
- recent_discoveries
- recommended_places
- pending_reviews

---

# 22. CMS

视频任务显示：

- Metadata
- Subtitle/ASR
- 当前进度
- 发现 PlaceCandidate 数
- Confirmed/Review/Unresolved
- 模型
- 是否调用外部 API
- 查看字幕
- 查看时间码 Evidence
- 重跑地点提取
- 重跑 POI


---

# FILE: video/VIDEO_AI_NOTE_PIPELINE.md

# 视频 Pipeline 契约索引

> 2026-09-03 按主题拆分；原章节编号保留。只选与本任务有关的一篇，再按标题定位，不要求连读。正文中的规划/旧状态不证明当前实现；先看 [当前状态](IMPLEMENTATION_STATUS.md) 与相关 [冻结约束](REGRESSION_AND_CHANGE_GUARD.md)。

| 任务主题 | 分篇 | 原章节 |
| --- | --- | --- |
| 业务范围与上游复用 | [01-scope-upstream.md](video/01-scope-upstream.md) | 1–3 |
| 输入、登录、字幕与转写 | [02-input-transcript.md](video/02-input-transcript.md) | 4–4.7 |
| 笔记、地点、截图与物化 | [03-generation-materialization.md](video/03-generation-materialization.md) | 4.8–4.16 |
| Job、数据身份与 API | [04-jobs-data-api.md](video/04-jobs-data-api.md) | 5–7 |
| 视图、地图、安全与验收 | [05-views-safety-acceptance.md](video/05-views-safety-acceptance.md) | 8–12 |

## 使用边界

- 最新的阅读/列表/删除/Replay 约束分别见 video/VIDEO_NOTE_READING_EXPERIENCE_V042_SPEC.md、video/VIDEO_NOTE_LIST_V043_SPEC.md、video/VIDEO_NOTE_DELETE_V044_SPEC.md、jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md；按任务选读，不重复加载全部。
- 登录/字幕修复已更新在输入分篇，所有状态结论统一读 IMPLEMENTATION_STATUS.md；旧版范围章的“待实施”只作历史说明。
- 代码定位见 [短实施指南](video/VIDEO_AI_NOTE_IMPLEMENTATION_GUIDE.md)，旧工作包不再是必读项。
- 上游参考：[BiliNote](https://github.com/JefferyHcool/BiliNote)，原审阅基线 f58e6182c41889873f9df98e4988e479fe9bf14f（2026-08-11）；授权见仓库 THIRD_PARTY_NOTICES.md。


---

# FILE: video/01-scope-upstream.md

# 业务范围与上游复用

> 来源：video/VIDEO_AI_NOTE_PIPELINE.md，原章节 1–3（正文保留，2026-09-03 分篇）。返回 [主题索引](video/VIDEO_AI_NOTE_PIPELINE.md)。本篇是契约/规划，不是已实施清单；当前结论见 [实施状态](IMPLEMENTATION_STATUS.md)，安全与回归见 [冻结清单](REGRESSION_AND_CHANGE_GUARD.md)。裸文档路径均以 dev docs/ 为基准。只读取命中章节及其必要约束。

# 1. 业务目标

用户只需要粘贴一个视频链接，系统在后台完成视频页信息解析、字幕获取或语音转写、语义理解、AI 笔记生成、代表性截图提取、旅行地点提取、现实 POI 校名和地点归纳笔记生成。本文中的“转义理解”统一指“字幕/转写文本的语义理解”，不是字符转义。处理完成后，用户可以：

- 阅读完整 AI 视频笔记；
- 查看视频标题、作者、封面、时长、简介、标签和来源链接；
- 在笔记章节、餐馆、景区和街区简介中查看与时间码对应的代表性截图；
- 从视频笔记中的地点引用进入地点归纳笔记；
- 从旅行地点列表进入同一地点归纳笔记；
- 点击地图 Marker 预览地点并进入同一地点归纳笔记；
- 从地点归纳笔记返回来源视频笔记及对应时间码；
- 查看每个事实、作者观点和 AI 推断的来源与类型。

产品成功路径固定为：

```text
粘贴视频链接
→ 系统回复“已收下”
→ 后台解析视频页、字幕/ASR 和语义
→ 生成带截图的 AI 笔记
→ 自动提取餐馆、景区、街区等细粒度地点并用高德校名
→ 视频笔记、地点列表和中国大陆全境地图同时可用
```

用户在成功路径中不需要选择平台、下载器、字幕来源、ASR 引擎或 LLM。只有登录态缺失、平台风控、POI 歧义、模型不可用等异常才进入 `NEEDS_USER`。

---

# 2. MVP 范围与非目标

## 2.0 历史状态说明（2026-08-24，不作为当前结论）

v0.4/v0.4.1 基础 Pipeline、内容完整性和全国地图已实现；v0.4.2 第一阶段阅读能力与 v0.4.3 列表封面/CTA 已实施。v0.4.4 最新批注返工（底部证据区、目录视觉、侧排缩略图/Lightbox）、真正步骤级续跑和视频笔记删除仅完成文档/设计，不得描述成已实现。

## 2.1 MVP 必须完成

- 接收 Bilibili 普通链接、BV 链接、`b23.tv` 短链和带 `p=N` 的分 P 链接；
- 解析 canonical URL、BV ID、分 P 序号、CID、标题、作者、封面、时长、发布时间和标签；
- 优先获取平台字幕，无字幕时下载音频并调用 ASR；
- 将字幕/ASR 统一为带时间码的 Transcript Segment；
- 使用已配置的 DeepSeek OpenAI-compatible Provider 生成结构化 Markdown AI 笔记；
- AI 笔记综合视频页元数据与 Transcript，而不是只总结单一文本；
- 对长字幕进行安全分块、分块总结和层级合并；
- 为主要章节和地点选取清晰、非重复、可回溯时间码的代表性截图；
- 从 Transcript 中提取餐馆、景区、街区、步行街、商圈、市场、公园、博物馆等地点及菜品、价格、特色、作者观点、提醒和推荐语；
- 通过高德 POI 服务校正转写名称并把 PlaceMention 解析成现实 Place；
- 为同一 Place 聚合多个来源，生成版本化地点归纳笔记；
- 保留 Source、Transcript、Claim、Evidence、模型和 Prompt 版本；
- 支持 Job 恢复、单步骤重跑、缓存复用和幂等写入；
- 支持从视频笔记、地点列表和地图 Marker 进入同一个 Place Detail。
- 地图覆盖中国大陆全境，无默认城市；支持平移、缩放、聚合、搜索、视野恢复和按当前 bbox 加载；
- 用户可以自定义添加、隐藏、恢复和删除 Marker；地图浮窗直接展示简略信息并可进入详情页。

## 2.2 本阶段不做

- 默认把视频帧发送给多模态模型做全视频视觉理解；
- 下载无上限或原始最高画质视频；截图只下载满足清晰度和大小限制的最低必要视频流；
- 评论区、弹幕和直播内容总结；
- 自动生成或猜测 POI 经纬度；
- 自动规划交通路线或最优行程；
- BiliNote 的 RAG 问答、浏览器插件和桌面 UI；
- 抖音、快手、YouTube 的生产级保证；这些平台保留 Resolver 接口，待 Bilibili 验收后逐个平台启用；
- 批量处理收藏夹、合集或播放列表；
- 绕过付费、权限、验证码、地区限制或平台访问控制。

---

# 3. BiliNote 复用策略

## 3.1 复用原则

BiliNote 作为经过真实使用验证的视频笔记参考实现。至简优先移植、适配或封装其成熟轮子，不重复从零实现平台细节；但业务数据、任务运行时、Evidence、POI 与 UI 仍使用至简自己的架构。

允许复用或适配：

- 视频 URL 校验、短链解析、BV ID 与分 P 参数提取；
- `BilibiliSubtitleFetcher` 的 player API 字幕优先策略；
- Bilibili Cookie 注入、字幕轨优先级与字幕 JSON 解析；
- `yt-dlp` 的元数据、字幕、音频和必要视频下载配置；
- Bilibili WBI/playurl 风控参数兼容经验；
- `TranscriptResult / TranscriptSegment` 的数据语义；
- FFmpeg 音频提取与转码策略；
- Whisper 转写 Provider 的实现经验；
- 长文本 Request Chunker、分块总结、层级合并、重试和 checkpoint 思路；
- Markdown 时间跳转标记和截图后处理逻辑；BiliNote 中的可选开关不改变至简 v0.4 的截图必备要求；
- 模型就绪门禁、代理配置和下载失败诊断经验。

不直接照搬：

- FastAPI `BackgroundTasks` 作为长任务运行时；
- JSON 状态文件作为任务真相源；
- `NoteGenerator` 单体服务和 BiliNote 独立 SQLite 表；
- BiliNote 前端页面、路由和 UI 信息架构；
- BiliNote 的 Provider 配置文件和明文 Secret 处理方式；
- RAG、向量库、问答和多模态能力；
- 与至简 Claim/Evidence/Place 模型冲突的数据结构。

## 3.2 许可证要求

BiliNote 使用 MIT License。若复制或实质性移植其源码，必须：

- 在仓库第三方声明中保留 BiliNote 的版权与 MIT License；
- 在移植文件头或 `THIRD_PARTY_NOTICES` 中标明来源仓库、参考 commit 和修改说明；
- 不删除上游版权声明；
- 对“参考思路”和“直接移植代码”分别记录，便于后续升级与安全审计。

## 3.3 上游隔离

所有移植代码进入受控适配层，例如：

```text
resolvers/video/
  bilibili.py
  url_parser.py
  subtitle.py
providers/media/
  yt_dlp.py
```

Processor、数据库模型和前端不得 import BiliNote 包。上游升级通过适配层吸收，不能让第三方内部类型泄漏到业务层。

---


---

# FILE: video/02-input-transcript.md

# 输入、登录、字幕与转写

> 来源：video/VIDEO_AI_NOTE_PIPELINE.md，原章节 4–4.7（正文保留，2026-09-03 分篇）。返回 [主题索引](video/VIDEO_AI_NOTE_PIPELINE.md)。本篇是契约/规划，不是已实施清单；当前结论见 [实施状态](IMPLEMENTATION_STATUS.md)，安全与回归见 [冻结清单](REGRESSION_AND_CHANGE_GUARD.md)。裸文档路径均以 dev docs/ 为基准。只读取命中章节及其必要约束。

# 4. 端到端处理流程

```text
CAPTURE
↓
NORMALIZE_CAPTURE_INPUT
↓
VALIDATE_AND_CANONICALIZE_URL
↓
FETCH_VIDEO_METADATA
↓
FETCH_COVER
↓
FETCH_PLATFORM_SUBTITLE
├─ 成功 → NORMALIZE_TRANSCRIPT
└─ 失败 → DOWNLOAD_AUDIO → ASR → NORMALIZE_TRANSCRIPT
↓
CORRECT_TRANSCRIPT
↓
GENERATE_AI_NOTE
↓
EXTRACT_TRAVEL_FACTS
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
MATERIALIZE_VIEWS
↓
CLEAN_CACHE
```

每个箭头都是可持久化 `JobStep`，不得只在内存中推进。每一步保存输入哈希、输出引用、实现版本、开始/完成时间和错误码。

## 4.1 CAPTURE

输入可以是纯视频 URL，也可以是包含标题、来源说明、“复制打开”等文字的完整分享文案。Capture API：

- 先提取并选择唯一内容 URL；
- 创建 `ContentItem`、`Source` 和持久 `Job`；
- 提取出的原始 URL 原样保留；
- 分享文案中的标题和其他文字不进入 Resolver/Classifier/LLM；
- 返回 `202 Accepted`、`content_id` 和 `job_id`；
- 不在 HTTP 请求中访问 Bilibili、下载音频、运行 ASR 或调用 LLM。

相同 canonical 视频重复提交时允许生成新的 Note Version，但复用有效的 Source Snapshot、Transcript 和媒体缓存。幂等键至少包含：

```text
platform + external_video_id + part_number + source_revision
```

## 4.1.1 NORMALIZE_CAPTURE_INPUT

输入分类：

```text
URL_ONLY
SHARE_TEXT_WITH_URL
TEXT_ONLY
MULTIPLE_URLS
```

处理规则：

1. 在不修改 URL 内部字符的前提下处理 Unicode 空白、零宽字符和换行；
2. 提取 `http/https` URL、Markdown `[标题](URL)`、`<URL>` 和已知平台无 scheme 链接；
3. 去除 URL 外侧引号、括号及末尾中文/英文标点，保留合法 query、fragment 和百分号编码；
4. canonicalize 后去重；
5. 一个候选直接选择；多个候选但只有一个命中专用 Resolver 时选择该候选；多个不同内容链接仍然存在时返回 `CAPTURE_MULTIPLE_URLS`；
6. 选中 URL 后，后续 payload 的 `text` 必须为空，不能把分享标题当正文；
7. 无 URL 时才按 `TEXT_ONLY` 进入直接文本路径。

示例：

```text
“厦门这家店太绝了！ https://b23.tv/abc123 复制打开哔哩哔哩”
→ SHARE_TEXT_WITH_URL
→ selected_url = https://b23.tv/abc123
→ 其余文字不进入视频处理
```

为最小化无关内容保留，数据库默认只记录 `input_kind / selected_url / candidate_count / discarded_text_length / raw_input_hash`，不保存被丢弃分享文案全文。日志不得记录完整原始粘贴内容。

## 4.2 VALIDATE_AND_CANONICALIZE_URL

MVP 接受：

- `https://www.bilibili.com/video/BV...`
- 带 query 的 BV 链接；
- `https://b23.tv/...`
- `?p=N` 分 P 链接。

输出：

```text
platform = bilibili
canonical_url
external_video_id = BV...
part_number
```

短链只允许跟随有限次数的 HTTPS 重定向。最终 host 必须仍在平台 allowlist；拒绝本地地址、内网地址和非 HTTP(S) Scheme，避免 SSRF。

无法识别的链接返回稳定错误 `VIDEO_URL_UNSUPPORTED`；短链失效为 `VIDEO_SHORT_URL_EXPIRED`。

## 4.3 FETCH_VIDEO_METADATA

优先通过平台接口或 `yt-dlp` 的 metadata-only 模式获取：

- title；
- author / uploader；
- description；
- cover URL；
- duration；
- published_at；
- tags；
- BV ID、CID、分 P 标题和分 P 序号；
- 可用字幕轨；
- 原始 metadata 哈希。

元数据保存为 Source Snapshot。元数据与 Transcript 共同作为 AI Note 输入。音频下载和截图视频下载分开规划：字幕命中时仍可为了截图下载受限画质的视频流，但不得因此重复下载音频或启用全视频多模态理解。

## 4.3.1 FETCH_COVER

VideoAsset 的平台 `cover_url` 在元数据完成后进入独立封面步骤：HTTPS 规范化、Bilibili 图片 CDN allowlist、状态/MIME/文件头/尺寸/字节限制校验、SHA-256 去重、本地原图存储和 672×378 WebP 列表衍生图。列表只使用本地 Cover API，不长期热链远程 CDN。

实现方法参考 `lanyeeee/bilibili-video-downloader` 的 CoverTask：从 `pic/cover` 获取 URL，GET 原图，根据 Content-Type 识别扩展名并写入本地；至简继续使用自己的 httpx、SSRF、缓存和 Job 体系。封面失败记录 `COVER_UNAVAILABLE`，显示占位但不阻塞 Note。完整契约见 `video/VIDEO_NOTE_LIST_V043_SPEC.md`。

## 4.4 FETCH_PLATFORM_SUBTITLE

字幕优先级固定为：

1. 客户端在用户登录态下合法取得并传入的字幕；
2. Bilibili player API 人工中文字幕；
3. Bilibili player API AI 中文字幕；
4. 其他中文轨；
5. `yt-dlp` 可获得的非弹幕字幕；
6. 没有可用字幕时进入音频下载与 ASR。

Bilibili 路径：

```text
BV ID + p
→ /x/web-interface/view 获取对应 CID
→ /x/player/wbi/v2 获取字幕轨
→ 选择字幕轨
→ 获取 subtitle_url JSON
→ Transcript Segment
```

AI 字幕可能要求有效 `SESSDATA`。用户在设置页或任务恢复卡内使用 Bilibili App 扫描站内二维码；后端通过 Passport API 轮询登录结果，以 `/x/web-interface/nav` 验证账号后只将 Cookie 写入 Secret Store/Keychain，不提供开发者工具复制粘贴入口，也不在 API、SQLite 或日志中回显凭据。

平台返回的 `subtitle_url` 必须经过用途级 HTTPS Host Policy：平台 API 使用精确域名，字幕和封面 CDN 使用各自受控的官方子域后缀；后缀匹配必须以完整 DNS 标签为边界，拒绝 HTTP、userinfo、非标准端口、`evilhdslb.com` 和 `hdslb.com.evil.example` 等绕过。新增平台资源类型时扩展对应策略，不在下载函数中散落一次性 hostname 判断。

字幕选择按人工中文、AI 中文（包括 `ai-zh` 等平台变体）、其他语言排序。单条字幕发生 CDN、网络、空内容或格式错误时尝试下一轨；全部不可用时进入音频下载与 ASR fallback。只有明确的登录失效继续进入 `NEEDS_USER`，不得把普通单轨失败升级成整个任务失败。

## 4.5 DOWNLOAD_AUDIO

仅在没有可用字幕时下载音频。使用 `yt-dlp` 取得 best available audio，并由 FFmpeg 转为 ASR 所需格式。约束：

- `noplaylist = true`；
- 本音频步骤不下载完整视频；截图所需的受限画质视频由后续独立步骤处理；
- 限制单任务时长、文件大小、重定向和下载速率；
- 下载到 `data/cache/video/<job_id>/`，不得写永久 Source 目录；
- 校验实际 MIME、容器和 FFprobe 元数据；
- 保存内容哈希、字节数和缓存过期时间；
- 需要 Cookie、验证码、会员或其他权限时进入 `NEEDS_USER`，不绕过限制。

`VIDEO_LOGIN_REQUIRED` 必须停止当前及后续步骤、释放 Worker lease，并在任务页展示站内扫码登录。登录成功后，音频下载可从 `DOWNLOAD_AUDIO` 继续；截图下载可从原步骤继续，或由用户明确选择跳过非核心截图。核心音频/Transcript 步骤不可伪跳过。

错误码至少包括：

- `VIDEO_LOGIN_REQUIRED`
- `VIDEO_ACCESS_DENIED`
- `VIDEO_DOWNLOAD_FAILED`
- `VIDEO_TOO_LARGE`
- `VIDEO_TOO_LONG`
- `VIDEO_PLATFORM_RATE_LIMITED`

## 4.6 ASR

字幕不存在时：

```text
下载音频
→ FFmpeg 16 kHz / mono / PCM
→ ASRProvider
→ timestamp segments
```

默认继续使用至简的 `WhisperCppProvider`；未来可增加 Faster Whisper 或云 ASR。ASR 输出必须包含语言、完整文本、分段开始/结束时间、置信度（若 Provider 提供）、Provider 和模型版本。

ASR 与本地 LLM 不默认并行争用 GPU。模型未安装、损坏或不就绪时，任务在排队前或 ASR Step 前进入 `NEEDS_USER`，前端展示明确修复动作。

## 4.7 NORMALIZE_TRANSCRIPT

字幕和 ASR 都归一为同一模型：

```json
{
  "language": "zh-CN",
  "source_kind": "PLATFORM_SUBTITLE",
  "segments": [
    {"start_ms": 192480, "end_ms": 207120, "text": "……"}
  ]
}
```

规则：

- 时间按毫秒存储；
- Segment 顺序稳定；
- 空段删除，相邻重复段去重；
- 不为了“好看”改写原字幕；
- 原始字幕/ASR 响应以哈希和可选 raw snapshot 保留；
- 后续事实 Evidence 必须指向 Transcript Segment，而不是只指向 AI 笔记。

## 4.7.1 CORRECT_TRANSCRIPT

归一化后、生成笔记前必须执行 AI 校对。每个 Segment 保留 `raw_text`，并生成时间码与 ID 不变的 `corrected_text`。校对修正口音/同音字、断句、重复词、标题/作者/地名/菜名和单位，但不得新增事实或改变作者立场。

校对输出必须覆盖全部 Segment，顺序和时间范围与输入一致；缺段、乱序、新增 ID 或空文本均拒绝。无法确认的地名保留待确认标记，再由高德 POI 流程校正。默认 Note、目录、页面预览和 TXT 导出使用 corrected_text；raw_text 只在证据审计中查看。完整阅读与校对规范见 `video/VIDEO_NOTE_READING_EXPERIENCE_V042_SPEC.md`。

Whisper.cpp `-oj` JSON 的 `offsets.from/to` 已经是毫秒，适配器必须直接使用，不得再乘以 10。归一化后必须校验 `max(segment.end_ms)` 与 `VideoAsset.duration_ms`：允许片尾静音和平台元数据的小幅误差，但超过视频时长 2 倍必须中止后续 Note/截图物化并记录 `TRANSCRIPT_TIMELINE_INVALID`。已受影响的历史 Transcript 不原地篡改；当末段时间与视频时长比值约为 10 时，从现有 Segment 生成修正后的新 Transcript Version，再基于新版本重建 Note Version 与截图。


---

# FILE: video/03-generation-materialization.md

# 笔记、地点、截图与物化

> 来源：video/VIDEO_AI_NOTE_PIPELINE.md，原章节 4.8–4.16（正文保留，2026-09-03 分篇）。返回 [主题索引](video/VIDEO_AI_NOTE_PIPELINE.md)。本篇是契约/规划，不是已实施清单；当前结论见 [实施状态](IMPLEMENTATION_STATUS.md)，安全与回归见 [冻结清单](REGRESSION_AND_CHANGE_GUARD.md)。裸文档路径均以 dev docs/ 为基准。只读取命中章节及其必要约束。

## 4.8 GENERATE_AI_NOTE

AI 视频笔记是一级业务产物，不再只是地点抽取的中间文本。

默认使用 Settings 中 `VIDEO_NOTE_SUMMARY` 能力绑定的 Provider。当前产品默认绑定已录入的 DeepSeek OpenAI-compatible 配置；API Key 从 Secret Store 读取，模型名由设置提供，不写死在业务代码。

输入：

- 视频标题、作者、简介、标签；
- 视频封面、时长、发布时间和来源页 URL；
- 带时间码 Transcript Segment；
- 笔记模板和 Prompt Version；
- 用户选择的语言/详细程度（未来 UI 可配置，MVP 使用系统默认）。

默认输出 Markdown，并同时保存可解析结构：

```text
标题
来源信息
内容概览
关键结论
按主题组织的章节
旅行/探店地点索引（若有）
注意事项
AI 总结
```

同时生成结构化目录 `toc[]`：`section_id/start_ms/heading/thesis`。heading 必须是本段明确主题，thesis 用一句话概括主旨；禁止“继续介绍”“本段讲了一些内容”等泛化句。页面正文使用校对稿生成的摘要、要点和时间线详述，不直接拼接 Transcript 原文。

### 摘要与时间线完整性契约

视频 AI 笔记必须同时包含两个独立层次：

1. **摘要**：用较短篇幅说明视频主题、核心结论、适用对象和重要提醒，不能代替正文；
2. **按时间线详述**：按真实视频顺序覆盖从首个有效 Segment 到末个有效 Segment 的全部内容，每节展示标题、`start_ms/end_ms` 和足够具体的正文。不能只取前 8 段、只写一个地点或把 overview 重复充当章节。

时间线边界由服务端对完整 Transcript 做连续分块，综合最大 120 秒与字符预算切分；`segment_ids/start_ms/end_ms` 由服务端赋值，模型只为给定分块生成标题和详述，不再要求模型抄写数据库 ID。单块模型失败时，以该块完整转写整理成“转写整理（未总结）”章节并记录 warning，保证有效 Transcript 永远不会物化为 0 个章节。最终摘要从全部时间线章节合并生成，不允许继续使用只截取前 `video_note_chunk_chars` 的单次请求代表完整视频。

理解顺序固定为两阶段：第一阶段先把视频页元数据与完整 Transcript 组织成 Video Understanding，包括总体摘要、主题章节、作者观点和初步地点线索；第二阶段再由独立结构化调用从 Transcript 中生成餐馆/景区/街区等 PlaceMention 与 PlaceBrief。第二阶段可以引用第一阶段的章节结构帮助定位，但最终事实仍必须直接绑定 Transcript Segment。

每个主要章节必须保留一个或多个 `segment_id` 和起始时间码，渲染层可生成原片跳转。AI 笔记中要明确区分作者观点、来源事实和 AI 归纳。

### 长字幕分块

不得把完整长字幕无条件塞入一次请求。流程固定为：

```text
按 Provider 上下文与请求字节预算切块
→ 每块生成局部笔记
→ 保存 checkpoint
→ 层级合并和去重
→ Schema/Markdown 校验
→ 保存最终 Note Version
```

切块边界优先选择自然停顿和主题边界，同时保留时间范围。合并 Prompt 只允许整理、合并和去重，不得补造原文没有的地点或事实。

每个分块 checkpoint 保存服务端确定的 Segment 范围、输入哈希和局部结果；重试只重跑失败分块。最终校验至少确认：章节数大于 0、章节按时间递增、相邻章节不倒序、末节覆盖末个有效 Segment、所有引用 ID 属于当前 Transcript Version。

### 重试与版本

- 429、超时、5xx 使用有限指数退避；
- 配额不足、Key 无效、模型不存在不盲目重试；
- 每次生成保存 provider、model、prompt_version、template_version、input_hash；
- 同一输入和同一配置可以命中缓存；
- 用户重跑产生新 Note Version，旧版本可查看，不静默覆盖。

## 4.9 EXTRACT_TRAVEL_FACTS

地点提取使用 `TRAVEL_PLACE_EXTRACTION` 能力，当前默认也可绑定 DeepSeek，但它是与 AI 笔记生成分开的结构化调用。

事实抽取的权威输入是 Transcript Segment；AI 笔记只能帮助组织上下文，不能成为唯一 Evidence。模型必须返回符合 Schema 的结构化 JSON：

```text
PlaceMention
RestaurantCandidate
DishObservation
PriceObservation
AuthorOpinion
Warning
Ranking
RecommendedSeason
RegionHint
```

地点粒度不得只停留在城市或行政区。MVP 必须区分并尽可能解析：

- `RESTAURANT`：餐馆、咖啡店、小吃店、摊位；
- `SCENIC_AREA`：景区、景点、自然景观；
- `NEIGHBORHOOD`：街区、历史文化街区、社区；
- `PEDESTRIAN_STREET`：步行街、商业街；
- `BUSINESS_DISTRICT`：商圈、综合体；
- `MARKET`：菜市场、夜市、集市；
- `PARK / MUSEUM / TEMPLE / VILLAGE / TOWN`；
- `LANDMARK / ACCOMMODATION / TRANSIT / OTHER`。

每个地点还必须生成 `PlaceBrief`：地点/景区特色、推荐菜品或体验、适合人群、价格与排队信息、注意事项、作者态度和对应 Segment。城市、省份、国家只作为上下文，不因视频提及就默认创建地图 Marker。

每个对象至少包含：

- `raw_name`；
- `suggested_name`；
- `place_type`；
- `city_hint / district_hint / nearby_landmark`；
- `segment_ids[]`；
- `source_quote`；
- `claim_type`；
- `confidence`。
- `brief` 与结构化特色字段。

无有效 `segment_ids` 的事实拒绝入库或进入 Review。地点别名、商场内分店、同名店和跨城市歧义不能由 LLM 擅自合并。

## 4.10 RESOLVE_POI

```text
PlaceMention
→ AMapPOIProvider 候选搜索
→ 名称/别名/拼音或同音候选校正
→ 结合城市、区县、附近地标、类别与地址上下文确定性打分
→ CONFIRMED / REVIEW / UNRESOLVED / REJECTED
→ Place
```

转写名称必须原样保存在 `raw_name`；高德校正后的名称保存为 `canonical_name`，不得覆盖原始 Evidence。高德返回的 POI ID、名称、别名、地址、行政区和 GCJ-02 坐标是地图事实来源。LLM 可以提供搜索词和上下文，不能自行确认经纬度。只有 `CONFIRMED` Place 默认进入主地图；歧义、同名跨城或搜索无结果进入待确认队列。

多个视频提到同一高德 POI 时复用同一 Place，并新增 Mention/Observation，而不是创建重复 Marker。

## 4.11 BUILD_PLACE_NOTES

地点归纳笔记是 Place 的版本化聚合视图，与单个视频 AI 笔记分开。

输入：

- Place 基础信息和 POI 元数据；
- 所有有效 PlaceMention；
- Dish/Price/Opinion/Warning 等 PlaceObservation；
- 来源视频和时间码；
- 用户状态与已验证偏好（可选）。

输出至少包括：

- 地点名称、类型、地址和地图定位；
- “为什么值得看/去”的归纳；
- 视频作者分别怎么评价；
- 推荐菜品、价格、排队、环境、季节和避坑信息；
- 不同来源之间的冲突；
- 来源视频列表与时间码；
- AI 个性化建议，明确标为 `PERSONAL_INFERENCE`；
- 最近生成时间、模型和版本。

地点归纳笔记中的事实必须能展开到 Observation → Claim → Transcript Segment。来源冲突并列展示，不能由后一次生成静默覆盖。

当 Place 新增 Mention、Observation 被修正、POI 被重新确认或 Prompt/Model 改变时，创建新的 Place Note Version。只修改用户的 SAVE/VISITED 状态时不强制重生成事实归纳。

## 4.12 PLAN_SCREENSHOTS

截图是视频笔记必备产物，不再是纯可选格式。截图计划同时使用：

- 视频封面和元数据；
- AI Note 章节的时间范围；
- PlaceMention 与 PlaceBrief 的 Evidence 时间码；
- Transcript 中的主题切换点。

默认目标：每个主要地点 1–3 张，整篇笔记 3–12 张；短视频可低于 3 张，但至少保留封面和一个可用代表帧。计划结果必须保存 `timestamp_ms / segment_id / section_id / place_mention_id / selection_reason / caption`。关键帧必须对应地点外观、菜品、景区特色、路线提示、价格/菜单、关键操作或结论证据；不得仅因为“章节起始”就选取普通 talking head、片头、广告、转场、纯黑帧或重复画面。

默认页面不再使用割裂的独立截图宫格。每张 READY 截图嵌入其对应时间线 Section，支持 contain 灯箱、上一张/下一张、时间码与说明、Escape/遮罩/按钮关闭和焦点恢复。

截图计划不得只依赖模型章节。若章节为空或没有可用 Segment 引用，必须从已校验的 Transcript 时间范围按开场、主题转换和均匀覆盖生成 3–6 个确定性候选；非空视频得到 0 个计划属于 `SCREENSHOT_PLAN_EMPTY`，不能继续下载视频并把 `EXTRACT_SCREENSHOTS` 记为成功。只有 `plans > 0` 才进入下载步骤。

## 4.13 DOWNLOAD_VIDEO_FOR_FRAMES

截图需要本地可读取的视频流。下载策略：

- 优先选择能满足截图清晰度的受限画质 MP4，不默认最高码率；
- 配置最大字节数、最大时长、分辨率上限和超时；
- 只保存到任务缓存目录，不进入永久原始文件目录；
- 已有同一视频/分 P 且内容哈希匹配的缓存可以复用；
- 平台不允许下载、Cookie 缺失或资源超限时，AI Note 继续交付并标记 `PARTIAL_SUCCESS`，UI 明确显示“截图不可用”的原因。

### Bilibili 格式选择契约

截图链路只需要可解码的视频流，不要求下载音频。Bilibili 常见 DASH 结果是 video-only MP4 与 audio-only M4A；不得使用只匹配音视频合一资源的 `best[height<=720][ext=mp4]/best[height<=720]`。该表达式还会把 `720x1280` 竖屏视频按 `height=1280` 排除，已在 `BV1JH826zEKC`、`BV1SNb966Ebs` 和 `BV1qF3t6TENn` 上造成 `Requested format is not available`。

实现时参照 BiliNote 的 `bv*` 视频流优先、Referer、Cookie 与 MP4 输出处理，但保留至简自己的资源边界：优先 `bv*[ext=mp4]`，再回退任意 `bv*`/可用视频；使用 yt-dlp 的 `res:720` 排序表达“优先不超过 720p、无匹配时取最小可用格式”，不要用单一 `height<=720` 代表横竖屏分辨率。请求必须携带 `Referer: https://www.bilibili.com`，需要登录态时复用短生命周期 Netscape Cookie 文件；最终仍执行超时、最大字节数、实际文件存在性和 FFmpeg 可解码检查。若未来需要合并音视频，才启用 `bestvideo+bestaudio` 与 `merge_output_format=mp4`，截图本身不得为无用音轨付出下载和合并成本。

## 4.14 EXTRACT_SCREENSHOTS

FFmpeg 按计划时间码抽帧，并进行确定性质量过滤：

- 清晰度/模糊度阈值；
- 黑帧和过曝/欠曝检测；
- 感知哈希去重；
- 在目标时间码前后小范围搜索最佳帧；
- 输出 WebP/JPEG、尺寸、文件哈希与实际时间码；
- 截图绑定 Note Section、PlaceMention 和 Transcript Segment。

本阶段不要求用视觉模型识别截图内容。截图是来源视频的可追溯辅助证据；若未来启用多模态理解，必须新增独立版本和审计，不能覆盖 Transcript Evidence。

## 4.15 MATERIALIZE_VIEWS

成功物化后至少可查询：

- 视频 AI 笔记；
- 视频页元数据、封面和章节截图；
- 具体主旨目录与稳定 Section 锚点；
- AI 校对稿、校对状态和 raw/corrected 审计关系；
- Transcript；
- 视频中提及的地点列表；
- Place 列表；
- 地图 Marker；
- Place 归纳笔记；
- 任务步骤、错误和外部调用审计。

视频 AI 笔记生成成功但 POI 仍需确认时，任务允许 `PARTIAL_SUCCESS`：笔记立即可读，已确认地点进入地图，歧义地点显示“待确认”。

`ContentItem.structured_json.note_id` 的公开身份必须是 `AINote.id`（`note_*`），不得写入 `AINoteVersion.id`（`ntv_*`）。所有 `/api/video-notes/{note_id}` 子资源均以 `AINote.id` 为规范参数。为保证已生成内容和旧书签可恢复，共享查询入口应在未命中 `AINote.id` 时识别历史 `AINoteVersion.id` 并解析到其父 Note；新写入数据仍必须使用规范 ID，兼容读取不得继续扩散错误身份。

## 4.16 CLEAN_CACHE

- AI Note、时间线章节和截图属于持久结果，不随缓存清理删除；完整 Transcript 文稿固定保留 180 天，按下述保留契约清理；
- 临时 Cookie、Secret 和未登记 scratch 立即清理；可供步骤续跑的音频、视频、分块结果、POI 候选和截图计划登记为 Replay Cache，默认保留 24 小时，到期后由 Worker 清理；
- 任务运行中、失败待重试或被 Note/截图引用的文件不得提前删除；
- 清理失败记录日志但不回滚已完成业务结果；
- 用户删除 Source 时按删除策略处理 Note、Mention、Observation 和 Evidence 引用。

### 完整转写导出与 180 天保留契约

视频 AI 笔记页提供“导出完整转写（TXT）”。导出由服务端按当前 Transcript Version 即时生成 UTF-8 附件，包含标题、来源 URL、转写来源、生成时间，以及所有 Segment 的 `[HH:MM:SS–HH:MM:SS] 正文`；不得只导出页面预览的前 8 段，也不在服务端保存第二份导出文件。

完整 Transcript 文本从创建时起保留 180 天，独立于通用日志保留天数。`Transcript` 保存 `retention_until/purged_at`；Worker 启动时及最多每 24 小时执行一次幂等清理。到期后清空 `Transcript.text`、全部关联 `Segment.text/raw_text/corrected_text` 和 `Evidence.quote`，移除 `metadata_json` 中当前错误保存的全文 fingerprint，仅保留 SHA-256、时间码、版本和审计所需元数据。AI Note、时间线正文、章节时间范围、截图和来源链接继续保留，但页面明确显示“完整转写已按 180 天策略删除”；转写读取与导出接口返回 `410 Gone`。清理事件只记录 Transcript ID、清理时间和数量，不记录原文。

---


---

# FILE: video/04-jobs-data-api.md

# Job、数据身份与 API

> 来源：video/VIDEO_AI_NOTE_PIPELINE.md，原章节 5–7（正文保留，2026-09-03 分篇）。返回 [主题索引](video/VIDEO_AI_NOTE_PIPELINE.md)。本篇是契约/规划，不是已实施清单；当前结论见 [实施状态](IMPLEMENTATION_STATUS.md)，安全与回归见 [冻结清单](REGRESSION_AND_CHANGE_GUARD.md)。裸文档路径均以 dev docs/ 为基准。只读取命中章节及其必要约束。

# 5. Job 状态与恢复

建议步骤和进度：

| Step | 建议进度 | 可复用缓存 | 可单步重跑 |
|---|---:|---|---|
| NORMALIZE_CAPTURE_INPUT | 2 | selected URL | 是 |
| VALIDATE_LINK | 5 | canonical URL | 是 |
| FETCH_METADATA | 12 | Source Snapshot | 是 |
| FETCH_COVER | 18 | CoverAsset / local derivative | 是 |
| FETCH_SUBTITLE | 22 | raw/normalized subtitle | 是 |
| DOWNLOAD_AUDIO | 32 | media cache | 是 |
| ASR | 48 | Transcript | 是 |
| NORMALIZE_TRANSCRIPT | 60 | normalized Transcript Version | 是 |
| CORRECT_TRANSCRIPT | 62 | corrected Transcript Version | 是 |
| GENERATE_AI_NOTE | 65 | Note chunk/checkpoint | 是 |
| EXTRACT_TRAVEL_FACTS | 76 | typed extraction | 是 |
| RESOLVE_POI | 86 | provider candidates | 是 |
| BUILD_PLACE_NOTES | 90 | Place Note Version | 是 |
| PLAN_SCREENSHOTS | 92 | Screenshot Plan | 是 |
| DOWNLOAD_VIDEO_FOR_FRAMES | 94 | bounded video cache | 是 |
| EXTRACT_SCREENSHOTS | 97 | Screenshot Assets | 是 |
| MATERIALIZE | 99 | View projection | 是 |
| CLEAN_CACHE | 100 | 不适用 | 是 |

有平台字幕时跳过 `DOWNLOAD_AUDIO/ASR`，进度直接推进，但保留 `SKIPPED` Step 记录。Worker 重启后从最后一个已完成且输入哈希一致的 Step 恢复。

失败后的人工续跑不从首步骤开始。Artifact Manifest 有效时，上游 COMPLETED 步骤在新 Attempt 中标记 `REUSED`，从失败步骤开始，后续步骤顺次执行；TTL 到期或输入/版本变化时步骤级续跑不可用，只能完整重跑。完整契约见 `jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md`。

最终状态：

- `COMPLETED`：AI 笔记完成，地点处理已完成或视频无地点；
- `PARTIAL_SUCCESS`：AI 笔记可读，但部分地点需确认或部分增强失败；
- `NEEDS_USER`：需要 Cookie、登录、模型配置或 POI 选择；
- `FAILED`：当前无法自动恢复；
- `CANCELLED`：用户取消。

---

# 6. 数据边界

需要新增或补全的核心实体：

```text
VideoAsset
Transcript
TranscriptSegment（复用通用 Segment）
AINote
AINoteVersion
AINoteSection
VideoScreenshot
PlaceMention
PlaceObservation
PlaceNote
PlaceNoteVersion
MapMarkerState
ExternalCallAudit
```

关键关系：

```text
Source 1 ── * Snapshot
Snapshot 1 ── 1 VideoAsset
VideoAsset 1 ── * Transcript
Transcript 1 ── * Segment
ContentItem 1 ── * AINoteVersion
AINoteVersion 1 ── * AINoteSection
AINoteSection 1 ── * VideoScreenshot
Segment 1 ── * Claim/Evidence
Segment 1 ── * PlaceMention
Place 1 ── * PlaceMention
Place 1 ── * PlaceObservation
Place 1 ── * PlaceNoteVersion
Place 1 ── 0..1 MapMarkerState
```

AI Note Markdown 不能代替 Transcript、Typed Claim 或 Evidence；Place Note Markdown 不能代替 PlaceObservation。

---

# 7. API 契约概要

Capture 继续使用统一入口：

```text
POST /api/inbox
GET  /api/inbox/{content_id}
```

视频笔记资源：

```text
GET  /api/video-notes
GET  /api/video-notes/{note_id}
GET  /api/video-notes/{note_id}/transcript
GET  /api/video-notes/{note_id}/places
GET  /api/video-notes/{note_id}/screenshots
POST /api/video-notes/{note_id}/regenerate
```

地点资源：

```text
GET  /api/travel/places
GET  /api/travel/places/{place_id}
GET  /api/travel/places/{place_id}/note
GET  /api/travel/places/{place_id}/sources
GET  /api/travel/map?bbox=&zoom=&place_type=&user_state=&query=
GET  /api/travel/map/bootstrap
POST /api/travel/map/markers
DELETE /api/travel/map/markers/{marker_id}
POST /api/travel/map/markers/{marker_id}/restore
```

所有入口最终使用同一个 `place_id` 和 Place Detail ViewModel。列表和 Marker 不维护第二份地点详情数据。

---


---

# FILE: video/05-views-safety-acceptance.md

# 视图、地图、安全与验收

> 来源：video/VIDEO_AI_NOTE_PIPELINE.md，原章节 8–12（正文保留，2026-09-03 分篇）。返回 [主题索引](video/VIDEO_AI_NOTE_PIPELINE.md)。本篇是契约/规划，不是已实施清单；当前结论见 [实施状态](IMPLEMENTATION_STATUS.md)，安全与回归见 [冻结清单](REGRESSION_AND_CHANGE_GUARD.md)。裸文档路径均以 dev docs/ 为基准。只读取命中章节及其必要约束。

# 8. 多入口导航规则

地点详情的 canonical route 建议固定为：

```text
/places/:placeId
```

入口包括：

- 视频 AI 笔记中的地点链接；
- 视频笔记的“本片地点”列表；
- 全局旅行地点列表；
- 地图 Marker 预览卡；
- 最近发现、收藏、想去和去过列表。

所有入口进入同一 Place Detail，不允许为“地图地点详情”和“列表地点详情”创建两套页面。入口上下文通过路由 state 或 query 保存：

```text
from = video-note | place-list | map | dashboard
source_note_id
source_segment_id
return_state
```

从地图返回时需要恢复 viewport、筛选和选中 Marker；从视频笔记返回时恢复阅读位置。Place Detail 中点击来源时间码可打开原视频或返回视频笔记对应章节。

## 8.1 中国大陆全境地图

地图不是默认城市页面。首次打开且没有用户历史视野时，以中国大陆全境为初始 viewport；之后恢复用户上次的中心点、zoom、bbox 和筛选。禁止在前端请求或界面文案中硬编码厦门或其他城市。

地图必须支持：

- 连续平移和缩放；
- 根据当前 `bbox + zoom` 请求 Marker；
- 全国尺度聚合，放大后逐步展开；
- 地点名称、别名、行政区和类型搜索；
- 当前视野结果计数和“适配全部结果”；
- 用户定位只作为主动操作，不改变默认全国策略；
- 地图 Provider 不可用时显示配置/诊断入口，不用静态厦门示意图伪装真实地图。

## 8.2 Marker 浮窗与详情

点击 Marker 必须在地图上直接打开浮窗/侧浮层，地图不离场。简略信息至少包含：名称、类型、地址/行政区、1 张代表图、特色摘要、关键菜品/体验、来源数量、用户状态和“查看详情”。点击“查看详情”进入 canonical `/places/:placeId`；返回时恢复原地图视野和浮窗。

PC 使用锚定 Marker 的浮窗或右侧浮层；Mobile 使用不遮挡主要地图操作的底部 Sheet。浮窗不是完整 Place Note，完整来源、冲突和 Evidence 仍在详情页。

## 8.3 用户自定义 Marker

用户可以通过地图长按/点击“添加地点”或搜索结果创建 Marker。创建时：

- 优先用高德搜索/逆地理编码取得规范名称、地址和 GCJ-02 坐标；
- 用户可以填写自定义名称、类型、简介和备注；
- 来源标为 `USER`，与视频自动提取的 `AI_EXTRACTED` 区分；
- 用户直接点选的坐标可以保存，但必须标记 `USER_CONFIRMED`，不能伪装成高德 POI 命中。

删除语义固定为：

- 用户创建的 Marker：软删除，可恢复；关联 Place/审计在保留期内不物理删除；
- 视频/POI 自动生成的 Marker：默认执行“从地图隐藏”，不能删除 Source、Claim、Evidence 或 Place；
- 恢复操作重新显示；
- 只有专门的数据删除流程才能物理删除无引用对象。

Marker 是 Place 的地图投影，不维护第二套地点详情数据。`marker_id` 与 `place_id` 同时返回，浮窗和详情始终以 `place_id` 查询。

---

# 9. 后续 UI 决策门

本文件先冻结产品与后端契约，不在本阶段直接决定页面数量或开始实现。下一阶段必须基于现有页面截图和路由完成 UI 信息架构审查，并回答：

1. 现有 Content Detail 能否承载完整视频 AI 笔记，还是需要独立 Video Note Detail；
2. 现有 Content 列表是否需要“视频笔记”筛选或独立入口；
3. 地点列表采用独立页还是地图内可切换列表视图；两者都必须共享同一 Place 数据；
4. 现有 Place Detail 是否能容纳地点归纳、来源视频、冲突与 Evidence；
5. 手机端长笔记、字幕时间轴、地图预览和返回状态如何组织；
6. 任务详情是否需要显示字幕来源、下载/ASR跳过、DeepSeek 分块和 POI 部分成功。

候选 UI 变化只包括：

- 扩展现有投递页；
- 扩展任务详情步骤；
- 扩展或新增视频 AI 笔记详情；
- 扩展地点列表/地图联动；
- 扩展 Place Detail 为地点归纳笔记；
- 扩展设置中的视频下载/Cookie、ASR 和 DeepSeek 角色配置。
- 地图改为中国大陆全境交互底图，新增 Marker 浮窗、自定义新增/隐藏/删除/恢复；
- 设置新增高德 JS Key、Security Code、Web 服务 Key 和真实连通测试。

必须先生成 PC 与 Mobile UI 图并确认，再进入前端实现；UI 图不得反向改变本文件已经冻结的业务数据和 Evidence 规则。

---

# 10. 安全、隐私与外部服务

- Bilibili Cookie 属于 Secret，不得进入 SQLite 明文字段、日志、导出或前端普通 API；
- DeepSeek API Key 只从 Secret Store 读取；
- 发送给 DeepSeek 的默认内容是视频元数据、字幕 Segment 和普通旅行信息，不发送招聘 Profile；
- 外部调用审计记录 Provider、Model、输入 Segment ID、字节/Token估计、时间、状态和错误码，不记录 API Key；
- 所有远程 URL 必须经过 SSRF 防护和平台 allowlist；
- URL allowlist 使用可复用、用途级的 HTTPS Host Policy；仅允许明确平台域名或完整 DNS 标签边界的官方 CDN 后缀，不使用任意 URL、字符串包含或无边界后缀匹配；
- 下载遵守平台条款与用户合法访问权限；
- 临时媒体不进入普通备份和导出；
- AI 输出必须在 UI 标明模型生成及可能存在错误。
- 高德 Web 服务 Key 保存在 Secret Store；JS Key 可作为普通设置，Security Code 按敏感设置保存并只通过受认证的地图 bootstrap 接口提供。浏览器加载地图后无法把 JS 端凭据视为绝对机密，设置页必须如实提示其客户端可见性与域名白名单要求。
- 视频截图属于来源派生资产，默认本地保存，不在普通导出中自动包含；删除/隐藏 Marker 不删除截图 Evidence。

---

# 11. 验收标准

## 11.1 核心成功路径

给定一个公开、可访问的 Bilibili 旅行视频：

1. 用户只粘贴链接即可获得 `202` 和 Job；
2. 系统正确识别 BV ID 与分 P；
3. 有字幕时不下载音频、不运行 ASR；
4. 无字幕时自动下载音频并生成带时间码 Transcript；
5. DeepSeek 生成可读、结构化、带来源时间码的 AI 笔记；
6. 主要章节和地点拥有清晰、非重复、带时间码的代表性截图；
7. 餐馆、景区、街区等细粒度地点被提取并绑定 Transcript Evidence；
8. 高德完成名称与 POI 校正后，Confirmed 地点显示在列表和地图；
9. 中国大陆全境地图无默认城市，支持平移、缩放、聚合和 bbox 加载；
10. 点击 Marker 在地图浮窗查看简略信息，视频笔记地点链接、列表项和浮窗详情按钮均进入同一个 Place Detail；
11. 用户可以新增、隐藏、删除和恢复自定义 Marker，自动生成 Marker 被删除时只隐藏地图投影；
12. Place Detail 显示地点归纳笔记、来源视频、截图和时间码；
13. 任务重跑可复用 Transcript 和有效截图，不重复下载/ASR；
14. Worker 重启后任务可恢复；
15. 全流程保存 Provider、Model、Prompt、Parser 和上游适配器版本。

## 11.2 异常路径

必须覆盖：

- 短链失效；
- 不支持平台；
- Bilibili 无字幕；
- Cookie 缺失或过期；
- 平台 412/429/访问拒绝；
- 音频超大、下载中断、FFmpeg 失败；
- Whisper 模型未就绪；
- DeepSeek Key 无效、余额不足、超时、429、5xx；
- 长字幕分块中途失败后 checkpoint 恢复；
- POI 无匹配、多匹配和同名跨城市；
- 转写错别字/同音地点通过高德候选校名，无法唯一确认时进入 Review；
- 截图视频不可下载、抽帧失败、黑帧、模糊帧和重复帧；
- 高德 JS Key、Security Code 或 Web 服务 Key 缺失/无效；
- AI 笔记成功但 POI 失败的 `PARTIAL_SUCCESS`；
- 取消任务后的缓存和数据库一致性。

## 11.3 质量门槛

- 不存在无 Segment Evidence 的来源事实；
- 不存在 LLM 生成的地图坐标；
- 同一 POI 不因多视频来源产生重复 Marker；
- 不存在城市级泛化 Mention 挤占细粒度餐馆/景区/街区结果；
- 每张展示截图有实际视频时间码、文件哈希和 Segment/Section/Place 关联；
- 分 P 字幕、元数据和原片跳转指向同一集；
- 旧 Note Version 不被重跑覆盖；
- 列表和地图进入的 Place Detail 数据一致；
- 地图初始状态不包含硬编码城市，Marker 添加/删除/恢复语义符合来源类型；
- CI 使用冻结 Fixture，真实 Bilibili URL 只作为手工验收；
- BiliNote 移植代码保留 MIT 声明与参考 revision。

---

# 12. 实施顺序

v0.4/v0.4.1 基础链路、v0.4.2 第一阶段与 v0.4.3 列表封面已完成。v0.4.4 后续按以下顺序实施：

1. 模型级全 Segment `CORRECT_TRANSCRIPT`、覆盖验证和 fallback；
2. Hero 缺封面空状态、正文优先、底部地点候选/完整转写；
3. 主体设计语言目录、稳定锚点和页面内时间码跳转；
4. 220–280px 侧排关键缩略图、语义重选与 contain Lightbox；
5. Step Artifact Manifest、24h Replay Cache 与 Replay Options；
6. 从错误步骤执行当前/下游，上游 REUSED，过期后完整重跑；
7. 视频笔记列表/详情统一删除和共享数据保留；
8. PC/Mobile 标注设计、键盘、安全和真实样本回归。


---

# FILE: video/VIDEO_NOTE_RENDERING_AND_TASK_MODEL_CONTEXT_SPEC.md

# 至简 视频笔记渲染与任务模型上下文规格

版本：v0.9，更新日期：2026-08-22，状态：`IMPLEMENTED / BROWSER_VERIFIED`。

本文件中的封面、错误态、Markdown 安全渲染和任务模型摘要仍是已实施基线。视频笔记页面的信息顺序、Transcript AI 校对、主旨目录、时间码跳转、随文截图、Lightbox 与 TXT 按钮返工以 `video/VIDEO_NOTE_READING_EXPERIENCE_V042_SPEC.md` 为最新待实施契约；不得据本文件保留独立截图宫格或原始 Transcript 正文堆叠。

## 1. 任务模型上下文

任务摘要的 Provider/模型表示当前或最近一次 LLM 调用，不表示当前所有步骤都在调用模型。任务接口从最近 LLM 步骤或保存的主模型路由中补齐 Provider、模型与 `model_step`；ASR、下载、解析和缓存清理不得把本地二进制或模型文件路径填入此字段。

界面标签为“最近模型调用”，下方显示对应步骤名称；没有任何 LLM 调用时显示“本任务尚未调用模型”。值列必须可换行/截断，完整值通过 title 可查看，不能越过摘要面板。

## 2. 部分完成

`PARTIAL_SUCCESS` 的全部流水线步骤已结束，进度满格是正确的执行状态。页面文案必须为“处理流程已完成”，紧随解释说明：`AI 笔记已生成；5 个地点待确认`、`未配置高德 POI，地图补充未执行`等。它不得称为“核心结果”或让用户误以为某个隐形步骤仍在运行。

## 3. 视频封面

当前已实施基线是 API 将远程封面规范化为 HTTPS，加载失败显示 Clapperboard 占位。v0.4.3 将列表封面升级为服务端下载、校验、按哈希本地保存并生成 672×378 WebP，列表只使用本地 Cover API；详情页仍可复用同一 CoverAsset。封面失败不影响笔记阅读。最新契约见 `video/VIDEO_NOTE_LIST_V043_SPEC.md`。

## 4. 安全 Markdown 渲染

视频笔记章节正文按受限 Markdown 渲染：段落、二三级标题、无序/有序列表、粗体、斜体、行内代码与引用。Markdown 不允许 HTML 注入、脚本、图片、任意链接协议或原始 HTML。模型生成的未识别语法以纯文本降级显示。

## 5. 已实施基线与 v0.4.2 替代规则

当前实现已经具备摘要、时间线、独立截图区、完整转写预览和 TXT 导出，并能区分 `PLANNING / READY / PARTIAL / UNAVAILABLE`。最新批注返工将页面顺序替换为：Hero → 摘要 → 主旨目录 → 按时间线详述 → 地点候选/完整转写；截图从独立宫格/全宽图迁移为对应 Section 文字侧面的缩略图。

完整转写区继续显示 Segment 总数、来源、180 天保留截止和导出，但默认展示/导出 AI corrected_text；raw_text 只在证据审计入口使用。导出按钮和 Lightbox 视觉、时间码锚点及 responsive 规则以 `video/VIDEO_NOTE_READING_EXPERIENCE_V042_SPEC.md` 为准。

## 6. 验收

1. `EXTRACT_TRAVEL_FACTS` 等 LLM 步骤在任务摘要中显示实际路由的 Provider/模型和步骤名。
2. `PARTIAL_SUCCESS` 显示“处理流程已完成”及明确的待确认/未配置原因，不显示“部分完成 · 100%”。
3. Bilibili `http://` 封面在浏览器请求 HTTPS，失败时显示占位。
4. AI 笔记中的 `**粗体**`、列表和标题被渲染为对应 HTML，原始标记不再直接显示。
5. 同一页面同时可见摘要和按时间线详述；时间线章节按时间递增并覆盖视频末段。
6. 0 张截图时显示 `SCREENSHOT_PLAN_EMPTY` 或实际失败原因，不显示无解释的“0 张可用”。
7. 完整转写区显示总段数、保留截止时间；TXT 导出包含全部段落，过期后显示 180 天清理状态。


---

# FILE: video/VIDEO_NOTE_READING_EXPERIENCE_V042_SPEC.md

# Video Note Reading Experience v0.4.2

> 状态：第一阶段已实施；2026-08-24 批注返工已冻结、待实施
> 更新日期：2026-08-24
> 适用页面：`/video-notes/:noteId`
> 现场样本：`note_221cd61e9600493cb3f32e062e1ad013`
> 标注设计：`design/ui/v0.4.4/video-note-detail-pc-annotated.png`、`video-note-detail-mobile-annotated.png`

---

# 1. 返工目标

当前页面已经具备视频元数据、摘要、时间线章节、截图、地点候选、完整转写预览与 TXT 导出，但信息顺序和内容语义仍不符合“先定位、再阅读、随文看图、需要时核对原文”的阅读目标。

本次返工固定解决：

- 地点候选和完整转写入口移到文章最底部，作为集中回查区；
- 所有时间码可以跳到对应时间线段落；
- 目录展示各段主旨，不输出泛化套话；
- 页面正文使用 AI 校对后的提纲与详述，不直接铺转录原文；
- 转写内容在进入总结前执行 AI 校对，保留原始版本供审计；
- 截图嵌入对应章节，不再作为割裂的独立图库；
- 截图可点击放大、切换并关闭；
- TXT 导出使用项目统一按钮视觉。

本文件不授权直接实施。实现前仍需遵守 `REGRESSION_AND_CHANGE_GUARD.md`。

---

# 2. 页面信息顺序

除返回栏和视频 Hero 外，页面顺序固定为：

```text
Video Hero：封面、标题、作者、时长、来源
↓
AI 摘要
↓
主旨目录
↓
按时间线详述（随文嵌入截图）
↓
Bottom Evidence Zone
  ├─ 地点候选
  └─ 完整转写入口/预览
↓
来源、冲突、生成版本与审计信息
```

## 2.1 Video Hero 封面

Hero 有 READY CoverAsset 时展示真实封面；封面缺失、失败或未下载时不显示场记板/图标占位，封面区域为空并收起，标题/来源内容自然占据可用宽度。不得用视频截图冒充平台封面。

## 2.2 Bottom Evidence Zone

地点候选和完整转写必须位于文章正文最底部，在所有时间线详述之后、来源/版本审计之前。它们是回查工具，不抢占首屏阅读顺序。

PC：双列布局，地点候选在左，完整转写在右；两卡顶部对齐。Mobile：按“地点候选 → 完整转写”纵向排列，不横向挤压。

地点候选显示：

- canonical/raw 名称；
- 类型；
- POI 状态；
- 一句特色简介；
- 来源时间码；
- 点击时间码跳转到对应正文；
- Confirmed 地点可进入 Place Detail。

完整转写卡显示：

- 总段数；
- AI 校对状态与模型；
- 保留截止日期；
- 前 8 段校对稿预览；
- “展开更多”和“导出完整转写”；
- 原始转写只在证据/校对差异入口中查看，不作为默认阅读正文。

---

# 3. Transcript 双版本与 AI 校对

## 3.1 数据原则

每个时间码 Segment 同时保留：

```text
raw_text
corrected_text
start_ms / end_ms
correction_status
correction_confidence
correction_reason
correction_provider / model / prompt_version
```

`raw_text` 是 ASR/平台字幕原文，永久只读直到保留期清理；`corrected_text` 是默认展示、总结和导出的校对稿。AI 校对不得覆盖 raw，也不得改变时间范围和 Segment ID。

## 3.2 校对目标

AI 校对处理：

- 口齿不清、口音造成的同音字；
- ASR 断句与重复词；
- 视频标题、作者、地名、菜名和专有名词；
- 明显语法残缺和无意义填充词；
- 数字、计量单位和常见旅行表达。

校对不得：

- 增加原文没有的事实；
- 改写作者立场；
- 猜测无法确认的地名；
- 把城市、景区、寺庙等候选擅自合并；
- 删除影响 Evidence 的否定、价格和提醒。

不确定内容使用 `［待确认：…］` 或低置信标记；地名在高德确认后再写 canonical name。

## 3.3 Pipeline

```text
NORMALIZE_TRANSCRIPT
→ CORRECT_TRANSCRIPT
→ VALIDATE_CORRECTION
→ GENERATE_AI_NOTE
```

校对按固定 Segment 块执行，每个输出必须引用原 Segment ID。服务端校验 Segment 覆盖率、顺序、时间范围和文本非空；不得接受缺段、乱序或新增 ID。

优先使用配置的主模型，失败时使用备用模型。全部模型不可用时，Transcript 保留 `UNCORRECTED`，最终 AI Note 不得伪装为完整完成；任务进入 `NEEDS_USER` 或明确的 `PARTIAL_SUCCESS`，页面显示“转写尚未校对”。

---

# 4. 摘要、目录与正文语义

## 4.1 摘要

摘要只回答：视频讲什么、核心结论、主要地点/体验、最值得注意什么。建议 120–300 中文字，不直接拼接 Transcript。

## 4.2 主旨目录

目录由服务端基于校对稿和时间线章节生成。每项包含：

```text
start_ms
heading
thesis
target_section_id
```

规则：

- `heading` 是明确主题，例如“避开国庆人流的筛选方法”；
- `thesis` 用 20–50 字概括本段主旨；
- 禁止“本段介绍了一些内容”“作者继续讲解”等无信息句；
- 目录按时间递增；
- 最多两级；
- 点击整行或时间码跳转对应正文。

目录视觉必须使用产品主体设计语言，而不是表格：暖白纸面、不使用硬边框网格；标题使用现有衬线标题体系，时间码使用朱砂红小号等宽数字，heading 为主要文字，thesis 使用较浅正文色；行间用细分隔线和留白组织。hover/focus 使用轻暖底色，当前 Section 使用左侧短朱砂标记和文字状态，不能只靠颜色。

## 4.3 按时间线详述

页面“全文/正文”统一改称“按时间线详述”。它不是 Transcript 原文，而是基于完整 AI 校对稿生成的提纲挈领内容。

每个 Section 固定包含：

- 时间范围和可点击起始时间码；
- 主旨标题；
- 1 段结论性概述；
- 2–6 条关键要点；
- 相关地点/菜品/注意事项；
- 嵌入的关键截图；
- “查看对应校对稿”和“打开原片”两个不同动作。

Section 必须覆盖完整 Transcript，不因摘要长度限制只处理前 12000 字符。禁止在正文中直接连续铺满原始转录句子。

---

# 5. 时间码跳转规则

页面内所有时间码默认执行本地段落跳转：

- 地点候选时间码 → 包含该 PlaceMention 的时间线 Section；
- 完整转写 Segment 时间码 → 最近的 Section，并定位/展开对应校对稿；
- 目录时间码 → 对应 Section；
- 截图时间码 → 截图所在 Section；
- Section 时间码 → 当前 Section 顶部。

跳转后：

- 使用稳定锚点 `#section-<id>` 或 `#t=<milliseconds>`；
- 将目标滚动到固定 Header 下方；
- 目标短暂高亮 2 秒；
- 将标题容器设为可聚焦并移动键盘焦点；
- 浏览器前进/后退恢复锚点；
- “打开原片”必须是独立按钮，不与页面内跳转混用。

---

# 6. 截图随文排版

独立“代表截图”宫格不再作为默认主阅读区。截图必须嵌入相关时间线 Section：

- PC 单张图默认作为 220–280px 缩略图放在文字侧面，正文占 60–68%，图片占 32–40%；
- 图片可在章节间左右交替，但同一页面保持可预测节奏，不做机械锯齿；
- 两张图可在侧栏上下堆叠；只有全景或强视觉章节才允许全宽主图；
- Mobile 缩略图放在该段文字之后并占满内容宽度，不产生横向滚动；
- 图片使用 `object-fit: contain`，不得裁掉菜单、店招、景区主体或文字。

截图选择必须对应关键内容：地点外观、菜品、景区特色、路线提示、价格/菜单、关键操作或结论证据。仅因为“章节起始时间”而选取普通 talking head、片头、转场或无信息帧不合格。

每张截图保存并展示：

- 实际时间码；
- 简短内容说明，而不是统一“章节起始时间码代表帧”；
- selection_reason；
- Section/PlaceMention/Segment 关系。

## 6.1 Lightbox

点击截图打开灯箱：

- 完整 `contain` 显示；
- 支持上一张/下一张；
- 显示时间码与说明；
- 点击遮罩、关闭按钮或 Escape 关闭；
- 打开后锁定背景滚动；
- 关闭后焦点回到原截图；
- Mobile 支持触控但不要求复杂手势缩放；
- 图片加载失败显示占位与来源时间码。

---

# 7. 导出按钮规范

“导出完整转写（TXT）”使用项目统一次级按钮：

- 与现有 `.button / .button--outline` 体系一致；
- 统一 36–40px 高度、圆角、边框、图标尺寸和 hover/focus 状态；
- 文案简化为“导出 TXT”，旁边以辅助文字说明“完整 AI 校对稿”；
- 不使用浏览器原生灰色按钮样式；
- 导出进行中、成功、失败均有状态；
- 默认导出 `corrected_text`，文件头记录校对模型和生成时间；原始稿只通过审计型独立导出提供。

---

# 8. API 与 ViewModel

Video Note Detail 增加：

```text
toc[]: section_id / start_ms / heading / thesis
transcript.correction_status
transcript.correction_provider/model
transcript.preview[].raw_text/corrected_text
sections[].summary/bullets/place_refs/screenshots
screenshots[].caption/selection_reason/section_id
```

时间码 API 必须使用稳定 Section ID；历史 Note Version 的锚点不能因重新排序随机变化。

Transcript 导出：

```text
GET /api/video-notes/{note_id}/transcript/export?version=corrected
GET /api/video-notes/{note_id}/transcript/export?version=raw
```

默认页面只调用 corrected；raw 入口放在证据/审计区域。

---

# 9. 响应式与视觉层级

PC 首屏优先看到 Hero、摘要和主旨目录；地点候选与完整转写位于文章底部。Mobile 同样先阅读正文，底部 Transcript 默认只显示 4–8 段并可展开。

视觉层级：

- 地点候选和完整转写是文章底部的工具/证据卡；
- 摘要和目录是阅读导航；
- 时间线详述是主正文；
- 截图是随文内容，不是独立附件区；
- 原始转写和模型审计是次级信息。

所有时间码、截图和按钮需要键盘可达、可见焦点、中文 aria-label；不能只靠朱砂色表达选中或错误。

---

# 10. 验收标准

1. Hero 后依次进入摘要、目录和正文；地点候选与完整转写位于文章最底部；
2. Hero 有封面时使用真实 CoverAsset，缺省时封面区域为空/收起，不显示场记板占位；
3. 地点、Transcript、目录、截图时间码均跳转到正确 Section；
4. 跳转后 Section 高亮、聚焦，前进/后退可恢复；
5. 目录使用暖白、朱砂时间码、衬线标题、细分隔线和明确 focus，不呈现硬边框表格；
6. 目录每项包含具体 heading 和 thesis，无泛化套话；
7. 正文是 AI 校对后的时间线提纲/详述，不连续铺转录原文；
8. 232 段 Transcript 全部拥有 corrected_text 或明确待确认状态；
9. AI 校对不改变 Segment ID、顺序和时间范围；
10. 地名不确定时进入待确认，不由校对模型编造；
11. 关键截图以 220–280px 缩略图放在对应文字侧面，不再只显示独立宫格或默认全宽大图；
12. 截图说明具体，普通 talking head/片头/转场不作为关键帧；
13. 点击截图打开灯箱，Escape/遮罩/关闭按钮均可关闭；
14. Lightbox 使用 contain，PC/Mobile 无裁切和横向溢出；
15. TXT 按钮符合统一视觉，默认导出完整 AI 校对稿；
16. raw Transcript、corrected Transcript、Note 和 Evidence 版本关系可审计；
17. 校对模型不可用时页面不伪装为完整完成。

---

# 11. 实施边界

本轮只完成文档。后续实现应拆为：

1. Transcript Correction 数据/API/Pipeline；
2. TOC thesis 与稳定锚点；
3. Hero CoverAsset/缺省空状态和 Bottom Evidence Zone 重排；
4. 时间码页面内跳转；
5. Section 结构化正文；
6. 侧排缩略图、关键帧重新选取和 Lightbox；
7. 导出按钮与 corrected/raw 导出；
8. PC/Mobile、键盘和真实样本验收。


---

# FILE: video/VIDEO_NOTE_LIST_V043_SPEC.md

# Video Note List v0.4.3

> 状态：已实施；后续回归受 `REGRESSION_AND_CHANGE_GUARD.md` 保护
> 更新日期：2026-08-24
> 适用页面：`/video-notes`
> 参考实现：[lanyeeee/bilibili-video-downloader](https://github.com/lanyeeee/bilibili-video-downloader)，审阅基线 `1254c6bf2a09a590163091e67651bfc9942171e2`

---

# 1. 目标

本次只返工视频笔记列表页的两个问题：

1. 顶部操作按钮文案、字号和尺寸符合现有设计系统；
2. 每条视频笔记下载并展示真实视频封面，不再长期显示通用场记板占位。

本文件不授权直接实施。

---

# 2. 顶部操作按钮

## 2.1 文案

“投递视频链接”改为：

> **添加视频链接**

原因：

- “投递”偏系统术语，不符合普通用户表达；
- 页面已经说明系统会把视频整理成笔记，按钮只需说明下一动作；
- 文案更短，PC/Mobile 都不容易换行。

## 2.2 视觉规格

按钮复用项目统一 `.button.button--primary`，不得单独创建超大红色按钮：

```text
height: 40px
padding-inline: 16–18px
font-size: 14px
font-weight: 600
icon-size: 16px（可选 Link/Plus 图标）
border-radius: 使用全局按钮 token
white-space: nowrap
```

PC：位于介绍卡右侧，宽度由内容决定，与介绍卡垂直居中。Mobile：介绍文字与按钮分行，按钮可占满内容宽度，但高度和字号不放大。

状态：hover、focus-visible、active、disabled 使用统一 Button Token；不能使用浏览器原生样式、内联字号或局部特殊圆角。

---

# 3. 封面来源

## 3.1 元数据优先

Bilibili Resolver 从视频元数据保存：

```text
VideoAsset.cover_url
```

普通视频通常来自 Bilibili `view` 数据的 `pic` 字段；分 P 默认使用所属视频主封面，未来若平台提供独立分 P 封面再覆盖。封面 URL 不由 LLM 推断。

## 3.2 参考实现

参考仓库的做法：

- `normal_info.pic / episode.cover` 作为 CoverTask URL；
- `ensureHttps` 把 `http://` 转成 `https://`；
- `BiliClient.get_cover_data_and_ext` 发起 GET；
- 检查 HTTP 200；
- 根据 `Content-Type` 识别 PNG/WebP/AVIF，其他图像回退 JPEG；
- 读取原始 bytes 并写入本地文件；
- 列表展示使用 `@672w_378h_1c.webp` 等 16:9 CDN 变体。

至简只借鉴封面 URL、HTTPS、响应校验、Content-Type 和本地写入方法，不复制其 Tauri/Rust 任务系统。若未来直接移植实质源码，必须在 `THIRD_PARTY_NOTICES.md` 加入其 MIT 声明和参考 commit。

---

# 4. 至简封面处理流程

```text
FETCH_METADATA
→ FETCH_COVER
→ VALIDATE_COVER
→ STORE_COVER_ORIGINAL
→ GENERATE_LIST_DERIVATIVE
→ MATERIALIZE_VIDEO_NOTE_LIST
```

## 4.1 FETCH_COVER

- 将协议相对或 HTTP URL 规范为 HTTPS；
- 只允许 Bilibili 已知图片 CDN host，例如受配置 allowlist 管理的 `*.hdslb.com / *.biliimg.com`；
- 请求携带合理 User-Agent 和 Bilibili Referer；
- 限制重定向、超时和最大字节数；
- 不因为元数据含 URL 就绕过 SSRF 检查；
- 下载失败不阻塞 AI Note，记录 `COVER_UNAVAILABLE` 并使用占位图。

## 4.2 VALIDATE_COVER

- HTTP 状态必须为 200；
- `Content-Type` 必须为允许的 `image/jpeg / image/png / image/webp / image/avif`；
- 文件头必须与 MIME 一致；
- 图片可解码且宽高合理；
- 拒绝 HTML、SVG、超大文件和 0 字节响应；
- 原始内容使用 SHA-256 去重。

## 4.3 本地存储

```text
data/permanent/video-covers/<sha256>.<ext>
data/permanent/video-covers/derivatives/<sha256>-672x378.webp
```

原始封面按内容哈希永久保存，列表衍生图可重建。不同 Note/Version 引用同一 VideoAsset 时复用封面，不重复下载。

列表 API 返回本地受控图片 URL，不直接长期热链 Bilibili CDN。图片响应使用内容哈希 ETag 和 immutable Cache-Control。

---

# 5. 列表卡封面布局

```text
aspect-ratio: 16 / 9
object-fit: cover
desktop width: 184–200px
border-radius: 使用 Card token
background: 当前 paper placeholder token
```

- 封面填满当前左侧缩略图区；
- 时长徽标保留在右下角，不遮挡重要主体；
- 图片 alt 使用视频标题；
- 图片 lazy-load；首屏第一张允许 eager；
- 加载时使用低对比 skeleton；
- 下载失败才显示现有场记板占位，并提供不打断阅读的“封面不可用”语义；
- 封面点击行为仍属于整张 Card 导航，不新增独立下载动作；
- PC/Mobile 保持 16:9，不拉伸、不使用 contain 留大面积空白。

---

# 6. 数据模型

推荐新增 `video_cover_assets`：

```text
id
video_asset_id
source_url
local_path
derivative_path
content_hash
content_type
width
height
byte_size
status
error_code
fetched_at
created_at
```

`status`：`PENDING / READY / UNAVAILABLE / INVALID`。

VideoAsset 保留平台 `cover_url`；CoverAsset 表示已下载、本地可服务的派生资产。不得用远程 URL 是否存在代表本地封面已经可用。

---

# 7. API

Video Note List Item 增加：

```text
cover_status
cover_image_url
cover_width
cover_height
cover_error
```

图片资源：

```text
GET /api/video-covers/{cover_id}/image
```

或使用等价的 VideoAsset cover endpoint，但必须：

- 只服务数据库已登记路径；
- 防止任意文件路径读取；
- 返回正确 Content-Type、ETag、Cache-Control；
- READY 以外返回稳定占位/404，不代理任意用户 URL。

---

# 8. Job 与重试

`FETCH_COVER` 位于 `FETCH_METADATA` 之后，可独立重试和缓存复用。封面失败属于非核心增强：

- 不把整个视频笔记标为 FAILED；
- Job/Note 可以 COMPLETED 或 PARTIAL_SUCCESS；
- 列表使用占位；
- 后续重新生成或封面专项重试可补齐；
- 错误日志只保存 host、状态、MIME、字节数和错误码，不记录 Cookie。

---

# 9. 验收标准

1. 顶部按钮文案为“添加视频链接”；
2. PC 按钮高度 40px、14px 字号，与全局 Primary Button 一致；
3. Mobile 按钮可全宽但不放大字号/高度；
4. Bilibili 元数据 cover URL 能规范为 HTTPS；
5. 参考样本下载原始封面并生成 672×378 WebP 列表图；
6. 封面使用本地 API URL，不长期热链远程 CDN；
7. 同一 VideoAsset 多 Note Version 只下载一次；
8. JPEG/PNG/WebP/AVIF MIME 和文件头校验通过；
9. HTML、SVG、超大和损坏响应被拒绝；
10. 列表缩略图保持 16:9、object-fit cover、时长徽标可读；
11. 加载 skeleton 和失败占位不导致布局跳动；
12. 封面失败不阻塞视频笔记阅读；
13. PC/Mobile 无裁切异常、拉伸和横向溢出；
14. 键盘焦点、alt 和 Card 导航保持可用；
15. 若直接复用参考项目代码，MIT Notice 完整。

---

# 10. 实施边界

本轮只完成文档。后续实现拆为：

1. CoverAsset 数据与迁移；
2. `FETCH_COVER` Provider/Service；
3. 本地原图与 16:9 衍生图；
4. 封面图片 API；
5. Video Note List ViewModel；
6. 列表真实封面与按钮视觉；
7. Fixture、网络失败、安全、PC/Mobile 回归；
8. 必要时补充第三方 MIT Notice。


---

# FILE: jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md

# Pipeline Step Replay v0.4.4

> 实施状态：源码、自动测试、在线库 `0007`、服务重启与真实步骤续跑均已完成。

> 状态：已实施并验收
> 更新日期：2026-08-24
> 适用入口：任务详情、运行日志 ERROR/CRITICAL 详情
> 标注设计：`design/ui/v0.4.4/pipeline-step-replay-and-delete-pc-annotated.png`

---

# 1. 正确语义

“从错误恢复”不是把所属任务从第一步重新执行。Pipeline 在运行期间暂存每个已完成步骤的可复用中间产物；某一步产生 ERROR 时，只要所需中间产物仍在有效期内，用户可以从该失败步骤重新执行，并让所有后续步骤顺次运行。失败步骤之前已经完成的步骤不再执行。

```text
STEP A COMPLETED ─┐
STEP B COMPLETED ─┼─ 复用，不重跑
STEP C FAILED    ─┘
        ↓ 用户确认“从此步骤继续”
STEP C RETRYING
→ STEP D
→ STEP E
→ ...
```

中间产物到期清理后，步骤级续跑不可用；用户只能选择“完整重跑”。

---

# 2. 中间产物生命周期

默认复用窗口使用现有 `video_cache_ttl_hours=24`，允许未来配置但第一版不在 UI 暴露任意值。

## 2.1 立即清理

- 临时 Cookie 文件；
- API Key/Authorization 临时值；
- 未登记的 scratch 文件；
- 被取消的未完成写入。

## 2.2 24 小时 Replay Cache

- canonical URL 与 metadata Snapshot；
- 平台字幕/ASR Transcript Version；
- corrected Transcript Version；
- Note 分块 checkpoint；
- Place extraction JSON；
- POI candidates；
- Screenshot Plan；
- 已下载且校验通过的音频/截图视频；
- 已生成但尚未成为最终投影的截图/派生文件。

## 2.3 持久结果

- Source/Snapshot/Transcript/Segment；
- AINote/Version/Section；
- Claim/Evidence；
- PlaceMention/Place/PlaceNote；
- READY Screenshot/CoverAsset；
- 审计事件。

`CLEAN_CACHE` 不能在任务结束时立即删除 Replay Cache；它只清理 secrets/scratch，并登记 replayable_until。Worker 定时清理在 TTL 到期后删除 Replay Cache。

---

# 3. Step Artifact Manifest

每个可重放步骤保存：

```text
job_id
attempt_id
step_name
artifact_type
artifact_ref/path
input_hash
content_hash
schema_version
producer_version
created_at
replayable_until
status
```

Artifact 状态：`AVAILABLE / EXPIRED / INVALIDATED / MISSING`。

只有输入哈希、Schema、Producer Version 与依赖 Artifact 均有效时才能复用。模型、Prompt 或用户输入变化导致依赖失效时，服务端自动把真正受影响的最早步骤作为 replay_from_step；前端不能绕过。

---

# 4. 可续跑判定

步骤级续跑必须同时满足：

1. Job 当前为 `FAILED / NEEDS_USER / PARTIAL_SUCCESS`，且没有活跃 lease；
2. ERROR/CRITICAL 事件规范关联该 Job 和失败 Step；
3. 请求 step_name 等于服务端判定的最早失败/失效步骤；
4. 该步骤所有上游 Artifact 均 AVAILABLE 且未过期；
5. Source、模型路由、Prompt、Parser 和配置没有使上游输入哈希失效；
6. 没有另一个 replay 正在排队或执行。

不满足时返回不可续跑原因：

- `REPLAY_ARTIFACT_EXPIRED`
- `REPLAY_ARTIFACT_MISSING`
- `REPLAY_INPUT_CHANGED`
- `REPLAY_STEP_MISMATCH`
- `REPLAY_ALREADY_RUNNING`
- `REPLAY_LEASE_ACTIVE`

---

# 5. 执行行为

提交步骤级续跑后：

- 创建同一 Job 的新 Attempt；
- 上游已完成步骤记录为 `REUSED`，保留原始 started/finished 和 Artifact 引用；
- 失败步骤及其所有下游步骤重置为 `PENDING`；
- 下游旧中间输出标记 `INVALIDATED`，最终版本不原地覆盖；
- `current_step` 设置为 replay_from_step；
- Worker 从该步骤开始顺序执行；
- 写入 `job.step_replay.queued/started/completed/failed` 审计链；
- 新 Attempt 再失败时保留旧 ERROR 和旧 Attempt。

完整重跑是不同动作：从 Pipeline 首个步骤开始，可按缓存策略复用，但不保证跳过任何步骤。

取消不是失败步骤。步骤续跑仍只在有明确失败步骤与有效 Artifact 时可用。完整重跑是独立动作：任何状态下均可从右上角提交；若原 Job 正在排队或运行，服务端先将其标记为协作式取消，再创建新的 `QUEUED` Job。单 Worker 会在旧流程到达安全边界并释放 lease 后领取新任务，避免两个流程并发写同一结果。

---

# 6. API

```text
GET /api/jobs/{job_id}/replay-options
POST /api/jobs/{job_id}/retry-from-step
POST /api/jobs/{job_id}/retry-full
```

`GET /api/jobs/{job_id}/replay-options` 还返回：

```json
{
  "full_replay_available": true,
  "full_replay_reason": "将停止当前流程并创建新的完整任务"
}
```

右上角始终展示“从头重新运行”。失败恢复卡仅在 `step_replay_available=true` 时展示步骤续跑按钮；不可续跑时只展示原因并引导用户使用右上角完整重跑，不重复放置完整重跑按钮。

Replay Options：

```json
{
  "step_replay_available": true,
  "replay_from_step": "GENERATE_AI_NOTE",
  "replayable_until": "...",
  "remaining_seconds": 53210,
  "reused_steps": ["VALIDATE_LINK", "FETCH_METADATA", "FETCH_SUBTITLE"],
  "rerun_steps": ["GENERATE_AI_NOTE", "EXTRACT_TRAVEL_FACTS", "..."],
  "reason": null
}
```

步骤续跑请求：

```json
{
  "step_name": "GENERATE_AI_NOTE",
  "source_event_id": "evt_..."
}
```

服务端不接受任意 from_step。`step_name` 只是用户确认值，最终必须与 Replay Options 一致。

---

# 7. 任务详情与日志 UI

失败 Step 行显示：

- “从此步骤继续”；
- “将复用前 N 个步骤”；
- “中间产物保留至 … / 剩余 …”；
- 将重新执行的下游步骤列表；
- 完整重跑作为次级动作。

日志 ERROR/CRITICAL 抽屉不再使用“重跑所属任务”作为唯一动作。规则：

- Artifact 可用：主按钮“从错误步骤继续”；
- Artifact 已过期：不显示步骤续跑按钮，说明“中间产物已清理”，引导使用右上角完整重跑；
- Job 已运行/完成：不显示过期 ERROR 的续跑按钮；
- 点击后确认框明确列出复用步骤和重跑步骤。

页面不得让用户逐个手动点击后续步骤；Worker 自动顺次执行。

---

# 8. 验收

1. C 步骤失败且 A/B Artifact 有效时，续跑只执行 C 及下游；
2. 上游步骤显示 REUSED，不产生新的外部请求；
3. 下游旧输出被 INVALIDATED，新版本不覆盖历史；
4. 24 小时内 Replay Options 返回可用和剩余时间；
5. TTL 到期后返回 `REPLAY_ARTIFACT_EXPIRED`，只能完整重跑；
6. Cookie/scratch 立即清理，Replay Cache 保留到 TTL；
7. 输入/模型/Prompt 变化时从服务端计算的最早失效步骤开始；
8. 日志按钮语义为“从错误步骤继续”，不再误导为整任务重跑；
9. 重复点击、活跃 lease、错误事件不匹配均被拒绝；
10. 审计可追踪旧 Attempt、来源 ERROR、复用 Artifact 和新 Attempt。
11. 运行中点击右上角完整重跑会取消旧 Job、创建新 Job，并导航到新任务；旧 Worker 在安全边界停止后再领取新 Job。
12. 复用 canonical VideoAsset 时，步骤续跑以 `FETCH_METADATA` Artifact 的 `video_asset_id` 定位资产，不假设当前 Capture Source 与资产原 Source 相同。


---

# FILE: video/VIDEO_NOTE_DELETE_V044_SPEC.md

# Video Note Delete v0.4.4

> 实施状态：列表/详情菜单、后端删除边界与保留式删除测试已完成。

> 状态：规格已冻结，待实施
> 更新日期：2026-08-24
> 标注设计：`design/ui/v0.4.4/pipeline-step-replay-and-delete-pc-annotated.png`

---

# 1. 入口

删除能力同时提供两个合理入口，但共用同一个后端动作：

- 视频笔记列表：每行右侧 `…` 菜单 → “删除笔记”；
- 视频笔记详情：顶栏 `…` 菜单 → “删除笔记”。

不在页面正文或首屏放常驻红色删除按钮。删除属于低频破坏性操作，放入溢出菜单；PC/Mobile 均保持至少 44px 点击区域和键盘操作。

---

# 2. 删除边界

删除 Video Note：

- 删除 AINote、Note Version、Section、TOC 和 ContentItem 投影；
- 删除只属于该 Note 的截图关联与本地派生文件；共享 Screenshot/CoverAsset 保留；
- 删除 Note 专属的模型生成结果和索引；
- 写审计事件。

不得连带删除：

- Source 与原始 URL；
- VideoAsset 与共享 CoverAsset；
- Place、Route、Marker 和地点笔记；
- 仍被其他内容或 Note 引用的共享 Source/资产；
- Route、Marker 和地点笔记。

v0.4.6 起，最后一个内容/Note 引用消失且无活跃 Job 时，同一事务删除孤立 Source，并由外键级联清理其 Snapshot、Segment、VideoAsset、Transcript、Cover 与截图；Place 和路线不随 Source 删除。

---

# 3. 状态与门禁

- 有活跃生成/重生成 Job 时返回 409，提示先取消或等待结束；
- Note 不存在返回 404；
- 重复删除返回幂等 404/410，不产生重复审计；
- 删除后详情页返回列表，列表、内容、概览、地点来源和搜索缓存全部刷新；
- 旧书签访问已删除 Note 显示“笔记已删除”，不永久 loading；
- 删除确认文案必须显示笔记标题和保留边界。

第一版沿用现有内容删除策略，不新增回收站；这是不可恢复操作，确认框必须明确说明。若未来增加回收站，再单独迁移为 soft delete。

---

# 4. API

```text
DELETE /api/video-notes/{note_id}
```

响应：

```json
{
  "status": "DELETED",
  "note_id": "note_...",
  "preserved": ["places"],
  "source_deleted": true
}
```

实现必须复用统一 Content/Note 删除 Service，列表页和详情页不能各自维护删除语义。

---

# 5. 确认框

标题：`删除视频笔记？`

正文示例：

> 将删除《中秋国庆人少景美又便宜的地方》及其内容投影。若来源已无其他内容或活跃任务，来源视频、完整转写和审计记录会一并清理；地点与路线保留。此操作目前无法撤销。

按钮：`取消` / `确认删除`。确认按钮使用 destructive variant；默认焦点在取消。

---

# 6. 验收

1. 列表和详情 `…` 菜单都有删除入口；
2. 删除前显示标题、保留边界和不可恢复提示；
3. 活跃 Job 阻止删除；
4. 删除 Note 后列表立即移除，旧 URL 显示已删除；
5. Source、VideoAsset、Transcript、Place、Evidence 仍存在；
6. Note 专属版本、Section、TOC 和无共享引用截图被清理；
7. 共享 Cover/Screenshot 不被删除；
8. 审计事件不包含 Transcript 正文或 Secret；
9. PC/Mobile 菜单与确认框可键盘操作；
10. 列表和详情调用同一 API/Service。


---

# FILE: ai-gateway/PROMPT_SUPPLEMENTS_V045_SPEC.md

# Prompt Supplements v0.4.5

> 状态：已实施并验收。
> 设计图：`design/ui/v0.4.5/prompt-supplements-settings-annotated.png`

## 目标

用户可为三个 AI 阶段增加表达偏好，而不能修改会影响解析和持久化的核心契约。

| 阶段 | 可编辑补充 | 不可编辑核心契约 |
| --- | --- | --- |
| `transcript_correction` | 语气、口语保留程度、简洁度、专有名词关注点 | JSON、Segment ID 唯一性/顺序、字段、Schema、时间码边界 |
| `video_note_summary` | 摘要篇幅、目标读者、行程/风险侧重点、措辞 | JSON、章节字段、有效 Segment 证据、章节结构 |
| `travel_place_extraction` | 优先地点类型、体验/价格/人群关注点 | JSON、地点字段、有效 Segment 证据、不得生成坐标 |

每项最多 1000 字符。补充文本只作为低优先级 System Message 插入固定核心 Prompt 与用户输入之间；核心 Prompt 不会通过 API 返回或编辑。

## 保护与审计

1. 设置页按每个阶段完整展示 6 条只读核心规则摘要与可编辑补充输入框；摘要可压缩措辞，但不得省略 JSON/Schema、字段、Segment ID、顺序/身份、Evidence/事实边界和坐标/锚点等契约类别，也不展示可编辑的 JSON 模板。
2. `PromptSupplementsConfig` 在 API 写入时拒绝覆盖/忽略系统规则、修改 JSON/Schema/字段/键名/ID/顺序等越权表述。
3. 即使补充文本绕过语义过滤，现有 JSON 解析、字段白名单、Segment ID 有效性与顺序校验仍在模型输出之后执行。
4. 设置写入 `prompt:supplements`，审计事件只记录启用阶段和哈希，不记录用户文本。
5. 保存仅影响之后发起的 AI 请求；已经完成的 Note/Transcript/Place 版本不原地修改。

## API

```text
GET /api/settings/prompt-supplements
PUT /api/settings/prompt-supplements
```

GET 返回三个补充文本、只读核心规则摘要、最大长度和每个阶段的哈希。PUT 只接收：

```json
{
  "transcript_correction": "保留自然口语风格。",
  "video_note_summary": "面向首次到访者，突出风险。",
  "travel_place_extraction": "优先提取餐馆和街区。"
}
```

## Pipeline 与续跑

每个 AI Step Input 写入对应 `prompt_supplement_hash`。失败 Job 读取 Replay Options 时，系统比较历史 Input Hash 与当前设置；若哈希变化，从三个 AI 步骤中最早受影响步骤开始续跑，前端不能指定更晚步骤绕过变更。

```text
补充转写校对 Prompt 变更 → CORRECT_TRANSCRIPT 起续跑
补充视频笔记 Prompt 变更 → GENERATE_AI_NOTE 起续跑
补充地点提取 Prompt 变更 → EXTRACT_TRAVEL_FACTS 起续跑
```

## UI

入口位于“设置 → AI 模型”，固定插入“推理路由”与“已保存模型”之间，不新增导航项或独立页面。每一行包含：阶段名、锁定核心契约说明、补充文本框、字符计数与“清空补充”。页面顶部提供统一“保存补充提示词”操作。


---

# FILE: ai-gateway/MODEL_AND_RETENTION_UI_SPEC.md

# 至简 模型配置与历史清理规格

版本：v0.4，更新日期：2026-08-21，状态：`IMPLEMENTED / BROWSER_VERIFIED`。适用部署：Mac mini 单节点。

## 1. 自定义模型库与路由

模型设置不再固定展示 DeepSeek、MiMo、Ollama 等预置槽位。用户可新增、编辑、真实测试并保存任意 OpenAI 兼容或 Ollama 模型配置；每条配置至少包括显示名称、Provider 标识、Base URL、模型名、超时和 API Key。API Key 只进入 macOS Keychain，接口和 SQLite 仅返回“已保存/未保存”状态。

“推理路由”独立于模型编辑：主模型与备用模型均从已保存的模型库中选择。转写校对另有可选的主/备用模型，两项均优先于推理路由，对应项留空时分别继承推理主/备用模型。主模型是唯一默认调用目标；仅在网络、HTTP、超时或 Provider 不可用等可恢复调用错误发生时才尝试备用模型。备用模型可留空；所有有效路由都未选择主模型时，依赖模型的任务必须进入 `NEEDS_USER`，不得回退到硬编码模型。

已被主/备用路由引用的模型不能删除；先切换路由才能删除。每次保存、路由切换、真实测试、自动备用切换和删除均写入审计日志，不含 Key。

## 2. 历史删除

任务列表与内容列表提供独立的“删除历史”入口。删除不是归档：操作需要确认，成功后列表立即移除并写审计事件。

- 仅 `COMPLETED`、`PARTIAL_SUCCESS`、`FAILED`、`CANCELLED`、`NEEDS_USER` 状态的任务可以删除；排队或运行中任务必须先取消，防止 Worker 写入已删除记录。
- 删除任务会级联删除其步骤和执行事件；已生成内容不会被连带删除，用户可在内容页单独判断是否删除。
- 删除内容会删除该内容及其专属 Claim/Evidence；若同一 Source 已无其他内容、视频笔记或活跃 Job，则同步删除其来源审计记录、Snapshot/Segment 与专属视频资产。Place、路线和已独立持久化的地点信息保留。
- 来源审计页支持手动删除孤立 Source；存在内容、视频笔记、排队/运行任务或取消清理 lease 时返回 409，并显示各类阻塞数量。
- 前端确认文案必须说明上述边界；操作成功后刷新任务/内容/待办/概览缓存。

### 2.1 视频完整转写 180 天自动清理（已实施）

视频完整转写采用固定 180 天保留期，不复用当前通用 `data_retention_days`/日志保留配置，也不增加可变的用户设置。保留截止时间从 Transcript 创建时计算，并显示在视频 AI 笔记页；有效期内可导出完整时间码 TXT。

Worker 启动时及最多每 24 小时执行幂等清理：正文、Segment 文本、Evidence quote 和 metadata 全文 fingerprint 被物理清空，保留 Transcript ID、版本、哈希、时间码元数据、`retention_until/purged_at`、AI Note 与截图。过期后页面显示“完整转写已按 180 天策略删除”，导出和完整转写接口返回 410。浏览器已下载到用户设备的文件不受服务端清理控制。

### 2.2 视频笔记删除（已实施，v0.4.6 更新）

视频笔记列表和详情均在 `…` 菜单提供“删除笔记”，共用 `DELETE /api/video-notes/{note_id}`。删除 AINote、版本、Section、TOC 和 Content 投影；若 Source 已无其他内容或活跃 Job，再清理 Source、VideoAsset、CoverAsset、Transcript、截图与 Segment Evidence。Place、路线及独立地点信息保留。活跃生成 Job 阻止删除，第一版不提供回收站。

## 3. 页面与响应式

模型页先显示“推理路由”两条选择框与状态摘要，随后是可展开的“已保存模型”列表和“新增自定义模型”入口。窄桌面下路由选择框垂直排布，编辑卡仍使用既有暖白、朱砂红与细线体系，不引入第三方品牌图标。

任务与内容行的删除入口默认隐藏于行尾操作区；窄桌面保留最小 40×40px 触控区域，删除前使用原生确认对话框并附带对象名称。删除控件不得覆盖行的详情跳转区域。

## 4. API 契约与验收

模型库接口：`GET/POST /api/settings/model-profiles`、`PUT/DELETE /api/settings/model-profiles/{id}`、`POST /api/settings/model-profiles/{id}/test`；通用/转写路由：`GET/PUT /api/settings/model-routing`；转写参数：`GET/PUT /api/settings/transcript-processing`。任务删除：`DELETE /api/jobs/{id}`；内容删除：`DELETE /api/content/{id}`；孤立来源删除：`DELETE /api/sources/{id}`。

验收：新增两个自定义模型后，可分别选为主/备用；已被引用模型无法删除；主模型连接失败时视频笔记记录实际备用模型并写入审计；没有主模型时任务明确需配置。终态任务和内容均可删除，运行中任务返回可理解的冲突提示，删除后刷新不再出现且相关审计日志可查询。


---

# FILE: jobs/MOBILE_SESSION_DIAGNOSTICS_AND_JOB_CONTROL_SPEC.md

# 至简 移动会话、视频诊断与任务控制规格

版本：v0.8，更新日期：2026-08-25，状态：`IMPLEMENTED / BROWSER_VERIFIED`。适用：Mac mini 局域网服务与手机浏览器。

## 1. 可信会话刷新

局域网配对成功后，服务以 HttpOnly 会话 Cookie 保存授权，不保存原始 4 位配对码。SQLite 读取到的 `AccessSession.expires_at` 必须统一按 UTC 解释后比较；无时区数据库值不得抛出 500。Cookie 使用根路径、7 天 Max-Age、显式 Expires 与 `SameSite=Lax`，HTTP 局域网环境仅在非 HTTPS 时不设置 Secure。

手机刷新时，前端只在 `/api/status` 返回 401/403 时进入配对页。500、网络不可达或其他服务错误必须进入“暂时无法连接 Mac mini”状态并提供重试，不得要求用户再次输入配对码。配对成功后刷新页面仍必须保留已授权状态，直至 Cookie 过期、配对码轮换撤销会话或用户清除浏览器数据。

## 2. 手机投递与视频资产复用

手机投递链接的 HTTP 请求仅创建 Source/Job 并立即返回持久 Job；认证错误、参数错误和后台视频处理错误必须分层显示。重复投递同一 Bilibili canonical URL 时，VideoAsset 按 canonical URL 复用，不得再次插入并触发唯一约束。数据库写入异常必须回滚当前事务，再用干净 Session 写入稳定错误码和审计事件，Worker 不得因 `PendingRollback` 退出。

## 3. 阶段诊断日志

视频任务每个阶段最少记录“开始、外部请求、关键检查点、完成/失败”四类审计事件。`FETCH_METADATA` 必须可区分：Bilibili 元数据请求、BV/CID 解析、视频资产查询、资产复用/创建、元数据写入。日志 detail 必须包含 `job_id`、`step`、`phase`、非敏感耗时与可人工判断的对象标识（BV、CID、字幕轨数量、缓存命中），不得包含 Cookie、Key、完整请求正文。

任务详情错误卡显示稳定错误码、可读原因与“查看关联日志”入口。阶段日志中的每个错误需要给出可操作提示，例如 `VIDEO_METADATA_FAILED` 提示检查链接/网络，`VIDEO_LOGIN_REQUIRED` 提示补充 Cookie，`ATTEMPT_TIMEOUT` 提示查看该步骤日志后重试。

## 4. 取消与重试门禁

取消是协作式停止：API 先将 Job 和当前 Step 标为 `CANCELLED`，保留 lease owner 直到 Worker 在当前可中断边界确认取消。视频与通用 Pipeline 在每个步骤开始、外部调用返回后、物化写入前检查 Job 状态；若已取消，停止后续步骤、清理临时音频/Cookie、写入 `job.cancel.observed`，再释放 lease。取消后不得生成内容、覆盖结果或重新入队。

“重试”只允许终态 Job，且取消中的 Job 必须等待 Worker 确认并释放 lease 后才能重试；否则返回 409 和“正在停止当前阶段”。重试重置 Job 的运行字段与所有未完成 Step 的运行状态/错误，增加 `retry_count`，再入队。Worker 启动时会释放已过期的取消 lease，避免崩溃后永久占锁。

### 4.1 长模型步骤的取消观察与完整重跑（已实施）

`CORRECT_TRANSCRIPT`、长字幕总结、地点提取等会连续发出多批模型请求。每一批请求开始前、请求返回后、递归拆分前和数据库物化前都读取持久 Job 状态；发现 `CANCELLED` 即抛出统一取消信号，停止尚未开始的批次、释放 lease 并写入 `job.cancel.observed`。已经发出的单次 HTTP 请求不能被 SQLite 状态反向中断，因此转写校对单批超时上限为 90 秒，不沿用模型配置的 300 秒上限。

429、5xx、网络错误和超时不再通过递归二分放大外部调用；只有响应结构校验失败才缩小批次。校对按最多 2400 字符、16 段组织批次，每一批开始和结束写入 `batch_index / batch_total / provider / duration_ms` 的脱敏活动事件。

取消中的页面状态必须是“正在停止当前步骤；确认停止后可从头重新运行”，而不是把禁用的“从头重新运行”伪装成可点击操作。`CANCELLED` 且 lease 已释放时允许完整重跑；仍持有 lease 时后端返回不可用原因。前端不得硬编码终态名单，而应读取服务端返回的操作能力。

## 5. 验收

1. 使用非 localhost 会话访问 `/api/status`、`/api/capture`、`/api/content` 不再产生无时区比较 500；刷新手机页面保持会话。
2. 已授权手机在服务临时 500 时看到连接诊断与重试，不回到配对页。
3. 重复 Bilibili 链接创建新 Job 时复用现有 VideoAsset，不发生 canonical URL 唯一约束失败。
4. `FETCH_METADATA` 日志可定位到外部请求、CID、资产复用/创建和元数据写入；日志不泄露 Secret。
5. 取消运行任务后，当前流程在下一个可中断边界停止，临时文件清理，lease 释放；取消确认前重试返回 409，确认后可入队重试。
6. 取消处于多批模型校对的任务后，至多等待当前受控 HTTP 请求结束，不再发起下一批；`job.cancel.observed` 在 lease 释放前出现。
7. 已取消且 lease 已释放的任务可从详情页完整重跑；取消进行中显示服务端原因并持续刷新，不存在永久禁用按钮。


---

# FILE: operations/RUNTIME_MONITOR_AND_MODEL_PRESETS_SPEC.md

# 至简 运行监控与模型预设规格

版本：v0.5，更新日期：2026-08-21，状态：`IMPLEMENTED / BROWSER_VERIFIED`。适用部署：Mac mini 单节点，局域网可信会话访问。

## 1. 目的

本规格落实设置页审阅的七项意见：局域网访问时资源指标必须稳定显示；监控采样由后端持久化而非浏览器实时探测；模型路由与控件保持“至简”视觉语言；新增模型在保存前可做真实测试；用户既可选择主流 Provider，也可保留手工填写；选择 Provider 后自动带出模型与 Base URL；本地模型不要求远端连接字段；内存统一以百分比展示。

## 2. 持久化运行监控

Mac mini API 进程是唯一采样者。它在启动时立即采样一次，此后每 30 秒采样一次，将最新记录写入 SQLite `settings` 的 `runtime:metrics-sample`。采样包含 `sampled_at`、CPU 百分比、内存百分比、数据盘百分比、每项不可用原因及 Worker 心跳快照；不得写入用户内容、密钥或访问 Token。

`GET /api/status` 只读取该持久化快照并返回其原始采样时间，不因请求来源是 `127.0.0.1`、局域网 IP 或已经可信配对的移动端而改用浏览器或即时伪造的指标。API 启动到第一条样本落库前返回“等待首个采样”；样本超过 75 秒时标为“指标延迟”，前端保留数值并同时显示延迟状态。侧栏和弹层每 30 秒刷新一次，与采样频率一致。

侧栏完整状态卡显示 CPU、内存、数据盘三个百分比与 Worker 心跳；内存不再显示“已用 / 总量”。可访问名称仍保留具体采样时间，展开弹层显示“采样于 …”。采集失败的单项显示 `—` 与“暂未采集”，不得显示 `0%`。

## 3. 模型路由视觉与交互

推理路由说明必须位于卡片正文的 20px 内边距中，紧邻路由选择而不贴在卡片左边线。主模型和备用模型使用统一的“选择框外壳”：40px 高、暖灰底、细线圆角、右侧定制 Chevron，不使用浏览器默认的黑色原生 select 外观。窄桌面时两项纵向排列。

主模型是必选的已保存模型，备用模型可空且不得与主模型相同。只有网络、超时、HTTP 服务错误或 Provider 不可用才触发备用模型；模型输出格式错误、结构化校验失败和用户取消不触发回退。该规则保留在路由卡的内嵌说明中。

## 4. Provider 预设与自定义模型

新增和编辑模型的 Provider 控件同时支持预设选择与手工填写：预设清单为 DeepSeek、MiMo、Moonshot / Kimi、智谱 GLM、通义千问、OpenAI 兼容、Ollama（本地），末项为“自定义”。选择预设会填入 Provider 标识、推荐 Base URL 和可选模型清单；模型名可从同一 Provider 的常用模型下拉选择，也始终允许自行输入。切换 Provider 只自动填充仍为空或仍等于前一预设默认值的字段，不覆盖用户明确修改过的值。

| Provider | 默认 Base URL | 模型建议 | 凭据 |
| --- | --- | --- | --- |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat`、`deepseek-reasoner` | 必填 |
| MiMo | `https://api.xiaomimimo.com/v1` | `mimo-v2-flash`、`mimo-v2-pro` | 必填 |
| Moonshot / Kimi | `https://api.moonshot.cn/v1` | `kimi-k2.6`、`kimi-k2.5` | 必填 |
| 智谱 GLM | `https://open.bigmodel.cn/api/paas/v4` | `glm-5-turbo`、`glm-5`、`glm-4.7` | 必填 |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus`、`qwen-max` | 必填 |
| OpenAI 兼容 | 留空，由用户填写 | 自行输入或常见模型建议 | 依服务而定 |
| Ollama（本地） | `http://127.0.0.1:11434` | 读取/填写本机模型名 | 不要求 |
| 自定义 | 留空，由用户填写 | 自行输入 | 依服务而定 |

Ollama 本地模型模式隐藏 API Key 与 Base URL 的必填提示，Base URL 可使用默认本机地址；显示“本机运行，不需要 API Key”。默认超时为 **300 秒**，允许 5–900 秒。所有 API Key 仅存 macOS Keychain。

新增模型即使尚未保存，也必须提供“真实测试”：前端把当前表单作为临时配置提交到 `POST /api/settings/model-profiles/test-draft`，后端只用请求内容发起一次最小真实请求，不写入 SQLite、Keychain 或模型库。测试结果只展示连通性、Provider 和模型，不回显 Key。保存后的模型继续使用持久化测试接口。

## 5. API 与数据契约

- `GET /api/status`：返回持久化 `metrics`、`metrics.sampled_at` 与 `metrics.freshness`（`FRESH` / `STALE` / `PENDING`）。
- `POST /api/settings/model-profiles/test-draft`：接收完整临时模型配置，执行真实连接测试，不产生配置、密钥或审计持久化副作用。
- 原有模型库 CRUD、已保存模型测试、主/备路由接口保持兼容。

## 6. 验收

1. 使用局域网 IP 访问并完成可信配对后，侧栏在首次 30 秒采样完成后持续显示与数据库快照一致的 CPU、内存、磁盘百分比和采样时间。
2. 断开实时采样超过 75 秒，侧栏明确显示“指标延迟”，不以 `0%` 代替。
3. 路由说明与两项选择控件有统一 20px 内边距，选择框不出现浏览器默认黑色边框/箭头。
4. 新建未保存配置可点击“真实测试”；测试后模型库数量、SQLite `settings` 与 Keychain 不新增该草稿。
5. 选择 DeepSeek、MiMo、通义、Ollama 后，推荐 Base URL 和模型建议正确出现；切换为本地 Ollama 时不要求 Key。
6. 新增模型默认超时为 300 秒，内存显示为百分比。


---

# FILE: operations/RUNTIME_MONITOR_AND_PROVIDER_SWITCH_V06_SPEC.md

# 至简 运行监控口径与 Provider 联动规格

版本：v0.7，更新日期：2026-08-25，状态：`IMPLEMENTED / BROWSER_VERIFIED`。适用部署：Mac mini 单节点。

## 1. 问题与目标

本规格处理本轮设置页与任务详情审阅意见：侧栏内存百分比不能把 macOS 可回收文件缓存算作业务已用内存；运行状态浮窗需要提供足够的单机运维信息；切换模型 Provider 时，上一 Provider 自动带入的 Base URL 与模型名不得残留；重试后的任务不得把旧尝试时间误显示为本次运行时长。

## 2. macOS 内存口径

macOS 指标使用 `vm_stat` 物理页统计。`active`、`wired down`、`occupied by compressor` 构成工作集参考；`free`、`inactive` 与 `speculative` 视为可立即或可回收内存，不能计入“已用”。

接口返回字段：

| 字段 | 定义 |
| --- | --- |
| `memory.used_bytes` | `total - (free + inactive + speculative)`，用于侧栏百分比与浮窗主数值 |
| `memory.available_bytes` | `free + inactive + speculative` |
| `memory.cached_bytes` | `inactive + speculative`，仅作诊断 |
| `memory.compressed_bytes` | `occupied by compressor`，仅作诊断 |
| `memory.method` | `macos-reclaimable-pages`；非 macOS 返回实际采集方法或不可用原因 |

页面不得以 `active + inactive + wired + compressor` 求和，因为这些页集合存在缓存与压缩页重叠，会把内存占用虚高。单项无法读取时返回 `null` 和原因，不显示伪造数值。

## 3. 侧栏与运行浮窗

侧栏继续保持紧凑：CPU、内存、数据盘均展示百分比，内存值使用上述工作集口径。浮窗展开后显示：

- CPU：百分比与采样来源；
- 内存：`已用 GB / 总 GB`、百分比、可回收 GB、压缩 GB；
- 数据盘：`已用 GB / 总 GB` 与可用 GB；
- 服务：API、Worker、SQLite、Ollama 的真实状态；
- 采样时间、指标新鲜度、Worker 最近心跳。

API 每 30 秒写入 SQLite 的同一快照仍是局域网与本机的唯一数据源。超过 75 秒未更新时浮窗明确显示“指标延迟”。

## 4. Provider 预设切换

每个模型编辑器单独维护 `model` 和 `base_url` 的“用户手填”状态：

1. 新增模型和与预设匹配的已保存模型，两个字段初始均为自动值。
2. 每次选择 DeepSeek、MiMo、Moonshot / Kimi、智谱 GLM、通义千问、OpenAI 兼容或 Ollama，所有仍为自动值的字段必须立即替换为该 Provider 当前预设；不得保留上一个 Provider 的默认值。
3. 用户在模型名或 Base URL 输入框亲自修改后，该字段标为手填；之后切换 Provider 时保留该字段，另一个未手填字段仍会更新。
4. 选择“自定义”后不再写入任何默认值；用户可自行填写。Ollama 仍隐藏 Key 与 Base URL 必填提示。

## 5. 任务尝试时间与停滞语义

每次 Job 被重新领取或某个已存在步骤被再次开始时，该步骤的 `started_at` 必须重置为本次尝试时间，`finished_at` 清空；历史开始时间只保留在审计事件中。任务接口额外返回 `runtime_state`、`last_activity_age_seconds` 与 `last_activity_source`：普通运行步骤 90 秒没有活动时为 `STALLED`；`GENERATE_AI_NOTE / EXTRACT_TRAVEL_FACTS / BUILD_PLACE_NOTES` 等 LLM 步骤使用 500 秒预警阈值，避免正常长模型调用被误报；真正终止尝试仍使用 900 秒。

任务停滞只能由该 Job 自身的 `heartbeat_at`、当前步骤活动时间或该 Job 的审计事件判断；绝不能使用 `runtime:worker-heartbeat` 等全局 Worker 心跳。全局 Worker 正常只说明执行器进程仍在运行，不能证明当前任务正在推进。任务页字段统一写作“该任务最后活动”，必要时显示来源字段。

全局 `runtime:worker-heartbeat` 由独立于 Job 执行循环的守护线程每 `worker_heartbeat_seconds` 写入进程存活信号。同步 Pipeline 被外部模型、FFmpeg 或网络调用阻塞时，心跳仍持续；它只表达“Worker 进程存活”，不更新任何 Job 的 `heartbeat_at`，也不掩盖任务停滞。

### 5.1 尝试超时错误规则

`job_attempt_timeout_seconds` 默认 900 秒。运行中的任务从其自身最后活动起超过此阈值后，Worker 将该次尝试终止为 `FAILED`，而不是无限自动重新领取。错误码固定为 `ATTEMPT_TIMEOUT`；错误原因必须包含当前步骤、人类可读开始时间、该任务最后活动时间与无进度分钟数，示例：`本次“获取元信息”自 2026-08-21 17:22 开始，已 15 分钟未收到该任务进度更新，已停止本次尝试。`

超时事件写入 `SystemEvent`：`job.attempt.timeout`，关联该 Job 与当前步骤。当前 `JobStep` 同时标为 `FAILED` 并保存相同原因。用户可以通过“重试”显式开始下一次尝试，系统增加 `retry_count` 并重新设置 Job 与步骤的开始时间；不得静默循环重试。

任务详情不再以 `489:03` 形式展示分钟与秒。时长小于一小时显示“xx 分 xx 秒”，大于等于一小时显示“x 小时 xx 分”。停滞任务不得使用“当前尝试 / 本次尝试”等术语；卡片必须用完整句表达：`开始于 昨天 17:22`、`8 小时未收到进度更新`、`任务可能停滞，建议查看日志或重试`。这表示 Worker 自该开始时间后未报告进度，不表示模型或视频内容正常处理了 8 小时。时间线使用同一语义并附最后活动时间，不把旧事件伪装为实时进度。

## 6. 步骤独立进度

任务 `progress` 是全流程总进度，只允许出现在任务标题或列表的总进度条。`JobStep.progress` 改为步骤自身 0–100 的进度：步骤开始为 0，完成为 100；有真实子任务数据（例如字幕段落、下载字节、地点条目）时才更新中间值。时间线不得复用全局 12%、15% 等里程碑数字。

步骤无法产生可量化中间值时显示“进行中，等待下一项活动”，不显示伪造的 0% 或总任务百分比。事件会同时记录 `job_progress` 与 `step_progress`，以便日志与页面均可明确区分两个维度。

## 7. 验收

1. 以包含 `inactive` 和 `occupied by compressor` 的 macOS 页统计输入，内存占比按可回收口径计算，不再接近 95% 的缓存误计结果。
2. 浮窗显示 `已用 GB / 总 GB`、可回收、压缩、磁盘容量、四项服务状态、采样与 Worker 心跳。
3. 新增模型依次选择 Moonshot 与智谱，模型名/Base URL 依次变为各自预设；不保存草稿即可观察到变化。
4. 手工改写模型名或 Base URL 后切换 Provider，该单项保留，未手填项仍更新。
5. 对重试过的步骤，API 返回的 `current_step_started_at` 为当前尝试而非初始旧时间。
6. 普通步骤运行中 90 秒无活动、LLM 步骤 500 秒无活动时显示“任务可能停滞”，并显示开始时间和“x 分钟未收到进度更新”；正常任务保留实时连接或轮询信息。
7. 超过 900 秒没有该任务自身活动的任务返回 `ATTEMPT_TIMEOUT` 与可读原因；全局 Worker 仍正常时也必须正确触发，不得把全局心跳当作任务进度。
8. 标题总进度与时间线步骤进度不会混用；已完成步骤为 100%，运行步骤显示自身进度或“进行中”。
9. API 状态、浏览器控制台、Ruff、后端测试、前端 lint/test/build 均通过。
10. 长模型调用持续超过全局心跳阈值时，服务状态仍为 Worker 运行中；若同一 Job 超过其 LLM 活动阈值未产生 batch/阶段事件，只有任务详情显示“任务可能停滞”。


---

# FILE: jobs/TASK_SUMMARY_AND_PARTIAL_SUCCESS_SPEC.md

# 至简 任务摘要与部分完成语义规格

版本：v0.8，更新日期：2026-08-22，状态：`IMPLEMENTED / BROWSER_VERIFIED`。

## 1. 运行摘要字段

任务摘要中的 `Provider` 与 `模型` 仅在当前步骤实际调用 LLM 时展示。ASR、下载、解析、清理等非 LLM 步骤不得把本地二进制路径、Whisper 模型文件路径或缓存路径填入“模型”字段；应显示“当前步骤不调用模型”。

摘要采用可收缩双列：值列最小宽度为 0，长 Provider、模型 ID、路径、错误码等必须在容器内换行或截断，不得越过右侧面板。截断字段保留完整 `title` 属性供查看。

## 2. PARTIAL_SUCCESS

`PARTIAL_SUCCESS` 表示所有后台处理步骤已结束，已交付结果中仍有待人工确认或待配置的补充项；它不是“总流程只处理了一部分”。视频笔记场景中，AI 笔记、时间码与已确认地点均已交付，但可能有地点待确认或未配置高德 POI。

任务标题卡使用“处理流程已完成”作为状态文案，不与 `100%` 并列。其下展示简短原因，如“所有处理步骤已完成；AI 笔记已生成，3 个地点待确认”或“所有处理步骤已完成；未配置高德 POI”。进度条仍可满格，语义是后台处理已结束；页面必须同时展示补充原因和进入内容/地图/日志的后续入口。

## 3. 验收

1. ASR 取消或运行中的任务摘要不显示 Whisper 文件路径为 LLM 模型。
2. 摘要长值不越界，窄侧栏与完整桌面均可读。
3. `PARTIAL_SUCCESS` 不再显示“部分完成 · 100%”或“核心结果已完成”；显示“处理流程已完成”与具体补充原因。


---

# FILE: ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md

# AI Gateway 生产验收与发布门禁

更新日期：2026-09-02。本文件取代已删除的阶段执行计划，保留尚未完成的生产验收边界，不把源码实现误写为生产已验证。

## 已在源码验证

- `LocalAIResourceManager` 使用共享 `data/runtime/local-ai.lock` 的 `flock` 串行化 API 与 Worker 的本地 ASR、文本、视觉及模型测试；进程退出由操作系统释放锁。
- AI Budget 按审计中的 `location` 分别累计 LOCAL/REMOTE Token；缓存命中不计模型调用或 Token 预算，且保留位置与缓存节省用量。
- `scripts/run_ai_benchmark.py` 评估受控真实 E2E 采集的结果；Golden 样本定义在 `benchmark/golden-ai-gateway-samples.json`。它不调用 Provider、不下载视频。

执行已采集数据的发布门禁：

```bash
.venv/bin/python scripts/run_ai_benchmark.py \
  'dev docs/benchmark/golden-ai-gateway-samples.json' real-e2e-runs.json --output benchmark-result.json
```

结果必须同时有 `BASELINE` 与 `CANDIDATE`，并满足：Schema 通过率 >= 0.95、Evidence coverage >= 0.90、严重幻觉为 0、Candidate 的地点/实体召回不低于 Baseline、远程 Token 降幅 >= 50%。平台字幕目标为 >= 70%，ASR 目标为 >= 30%，应在结果记录中分组复核。

## 生产门禁（尚未由本文件宣称完成）

生产迁移前确认无 `QUEUED/RUNNING` Job 或 lease，备份 SQLite，并执行 `PRAGMA integrity_check`。当前数据库须为 `0010 (head)`；迁移或重启只通过 `deploy/macos/manage.py`，不得以临时开发服务替代 LaunchAgent。

真实 E2E 必须分别留存：本地 Ollama text/JSON/structured output、一个已配置远程 Provider、LOCAL_ONLY/REMOTE_ONLY/LOCAL_FIRST/REMOTE_FIRST/AUTO 路由、跨进程 ASR 与模型测试等待、缓存与 force-regenerate、低预算拦截、AI 阶段取消与 Replay、一个平台字幕视频及一个 ASR 视频。未配置的 Key、Cookie、模型或可访问样本是明确的外部条件，不能以 Mock 或空记录替代。

通过所有门禁前，禁止声明 “AI Workload Gateway Production Proven”，也不启动 GenericProcessor、Source Watch、RAG、Multi Worker、Cloud Worker 或高风险自动操作。


---

# FILE: ai-gateway/AI_RUNTIME_AND_PROVIDERS.md

# AI Runtime and Providers

## 1. 原则

业务层永远不依赖具体模型厂商。

统一能力：

```text
LLMProvider
ASRProvider
POIProvider
```

---

# 2. LLMProvider

接口概念：

```python
class LLMProvider:
    async def generate(...)
    async def structured_output(...)
    async def vision(...)
```

实现：

- OllamaProvider
- OpenAIProvider
- OpenAICompatibleProvider
- MockProvider（测试）

第一版外部兼容端点至少验证：

- DeepSeek API；
- Xiaomi MiMo API；
- 用户自定义 OpenAI-compatible `base_url`。

模型 ID、上下文长度与能力随服务更新，不写死在 Processor；通过 Settings 的能力映射配置。

---

# 3. LLM 策略

支持：

- LOCAL_ONLY
- LOCAL_FIRST
- CLOUD_FIRST
- MANUAL

默认：
`LOCAL_FIRST`

视频 AI 笔记是明确例外：MVP 的 `VIDEO_NOTE_SUMMARY` 与 `TRAVEL_PLACE_EXTRACTION` 默认绑定用户已配置的 DeepSeek OpenAI-compatible Provider，以满足长字幕总结质量要求；用户仍可在 Settings 中改为其他兼容模型。业务代码只声明能力，不写死模型 ID 或直接读取 API Key。

---

# 4. Local First

示意：

```text
本地模型
→ Schema 验证
→ 成功：完成
→ 失败/低置信：根据策略调用外部模型
```

外部模型是增强，不是核心依赖。

## 4.1 Ollama 模型释放契约（已实施）

Mac mini 只有 16 GB 统一内存，本地模型调用不得依赖 Ollama 默认的 5 分钟驻留。`OllamaProvider` 对 `/api/chat` 的每次非流式请求都必须发送 `keep_alive: 0`，让模型在响应完成后立即卸载；任务推理、备用模型调用和设置页“真实测试”遵守同一规则。该参数是 Ollama 官方 API 对 `ollama stop <model>` 的等价能力，优先于为每次 HTTP 请求另起 CLI 子进程。

若兼容旧 Ollama 而保留 CLI 兜底，必须记录本次实际使用的本地模型，并在调用边界的 `finally` 中限时执行 `ollama stop <model>`；推理失败、JSON 解析失败、备用模型切换和用户取消也必须进入清理。停止失败只记录脱敏告警，不能把已成功的业务结果改成失败，也不能停止未由本次调用触发的其他模型。验收以响应返回后 `ollama ps` 在短时间内不再列出该模型为准。

---

# 5. 外部 API Key

Settings 支持：

- provider
- base_url
- api_key
- model
- timeout
- max_retry

正式版本不把 Key 明文放 SQLite。

生产环境：
- macOS Keychain

SQLite 只存 key reference。

开发环境允许 `.env`，但不得提交 Git。

外部请求的数据策略：

- `NORMAL` 来源 Segment 可按所选策略外发；
- `SENSITIVE` Profile 默认不外发，仅在用户对单次任务明确授权后发送最小必要字段；
- `LOCAL_ONLY` 永不发送到外部 Provider；
- 审计仅记录字段类别、Segment ID、Provider/Model 与结果状态，不记录完整敏感正文。

---

# 6. Capability-based Routing

业务不要指定具体模型。

任务声明：

- CLASSIFICATION
- STRUCTURED_EXTRACTION
- LONG_CONTEXT
- VISION
- SEMANTIC_MATCH
- VERIFY
- SCREENSHOT_PLANNING
- TRANSCRIPT_CORRECTION
- NOTE_TOC_AND_SECTION_SUMMARY

Router 决定 Provider + Model。

---

# 7. 本地硬件策略

Mac mini：
- Apple M4
- 16 GB 统一内存
- Metal

可以本地承担：
- 分类；
- 结构化提取；
- Recruitment DSL；
- Travel Trait；
- ASR；
- 未来视觉理解。

---

# 8. 模型角色

具体型号允许随时间更新，不应硬编码到业务。

建议角色：

### Fast Local Model
- 分类
- 简单摘要
- 链接判断
- 轻量实体提取

### Main Local Model
- 招聘公告结构化
- Requirement DSL
- 地点抽取
- 偏好解释

### Vision Model
视觉 Stage 已完成 image-capable Profile 绑定校验；当前视频抽帧仍是确定性筛选，不会因为注册视觉阶段而自动上传帧或调用视觉模型。

### External Strong Model
- 本地解析失败
- 低置信
- 用户手动高质量重跑
- 高价值歧义验证

---

# 9. Structured Output

必须 Schema First。

流程：

```text
Prompt
+ JSON Schema
+ Evidence Segments
→ LLM
→ JSON
→ Pydantic Validation
→ PASS / RETRY / FAIL
```

不允许依赖自由文本再正则抠 JSON。

---

# 10. Evidence Validation

模型输出事实时必须引用 segment/evidence id。

若 Claim 没有对应 Evidence：
- Reject；
- Retry；
- 标记不可信。

---

# 11. Cross-model Verification

未来/可选：

重要字段可由本地与外部模型交叉验证。

若冲突：
- 不自动选择；
- 回到 Evidence；
- 显示冲突。

---

# 12. ASRProvider

默认：
WhisperCppProvider

预留：
- FasterWhisperProvider
- CloudASRProvider

原因：
macOS arm64 / Metal 环境。

---

# 13. ASR 策略

模式：

- FAST
- AUTO
- ACCURATE

AUTO：
- 默认快速模型；
- 低置信/关键内容再高精度重跑。

---

# 14. GPU 并发

初始：
`gpu_heavy_concurrency = 1`

CMS 可配置。

避免 ASR + 大模型同时抢占显存导致稳定性问题。

---

# 15. Prompt / Parser Version

每个结构化任务保存：

- provider
- model
- prompt_version
- parser_version
- schema_version

支持以后 Replay 与对比。

视频笔记还必须保存：

- note_template_version；
- chunker_version；
- merge_prompt_version；
- transcript_id / input_hash；
- checkpoint 状态；
- 外部调用审计引用。

长 Transcript 使用 Provider 能力预算进行分块、局部总结和层级合并。所有 Pipeline AI 请求统一读取 `app:general` 调用策略：默认请求前等待 3 秒；429、408、409、425、超时、连接失败、可恢复 5xx 与空响应默认重试 1 次，每次至少等待 5 秒；429 优先采用 `Retry-After`。主模型耗尽重试后才切换不同故障域的备用模型。401/403、余额不足和模型不存在不做无效重试。

`SCREENSHOT_PLANNING` 只根据视频元数据、Note Section、PlaceMention 和 Transcript 时间范围提出候选时间码；最终抽帧、清晰度、黑帧与感知重复检测由确定性代码完成。MVP 不要求把所有视频帧发送给多模态模型。

`TRANSCRIPT_CORRECTION` 在 Note 生成前按字符预算与 Segment 数双门槛分块。默认每批 12,000 字符、最多 128 Segment、单次超时 180 秒；设置页基础校验范围分别为 2,000–24,000、16–256、30–300 秒。转写专属主/备用模型优先于推理路由，任一选项留空时继承对应推理模型。模型只能返回原 Segment ID 对应的 corrected_text、置信度和原因；服务端验证覆盖率、顺序与时间码，不接受新增/缺失 ID。

`NOTE_TOC_AND_SECTION_SUMMARY` 输出具体 heading、20–50 字 thesis、summary 和 bullets。禁止无信息套话；Section ID 和时间范围由服务端提供，模型不得自行编造锚点。

## Prompt Supplements v0.4.5

固定核心 Prompt 继续负责 JSON、Schema、字段、Segment ID、顺序和证据契约。设置页只允许用户给 `transcript_correction / video_note_summary / travel_place_extraction` 添加低优先级表达偏好，例如语气、篇幅、目标读者和关注重点。保存时服务端拒绝试图覆盖系统规则、JSON、字段、ID 或顺序的内容；模型返回仍经过原有解析和证据校验。默认入口及完整契约见 `ai-gateway/PROMPT_SUPPLEMENTS_V045_SPEC.md`。

---

# 16. 禁止

- Processor 内 import openai/ollama SDK；
- LLM 直接决定确定性日期/年龄；
- LLM 生成 POI 经纬度；
- LLM 输出没有 Evidence 的事实；
- 只保存最终自然语言摘要而丢失 Typed Result。


---

# FILE: ai-gateway/AI_ROUTING_SOURCE_RETENTION_V046_SPEC.md

# 转写路由、分段参数与来源清理 v0.4.6

> 状态：已实施并完成自动化与 Browser 验收。

## 验收契约

1. 设置 → AI 模型同时展示通用推理主/备用与转写校对主/备用；转写项非空时优先，空时逐项继承通用路由。
2. 被任一路由引用的模型不能删除；转写主/备用不能选择同一条配置。
3. 转写参数为字符预算、最多 Segment、单次超时，默认 `12000 / 128 / 180`，范围 `2000–24000 / 16–256 / 30–300`。
4. 三个 Prompt 阶段各完整显示 6 条只读核心契约；补充文本仍只有语气、篇幅、受众和关注重点权限。
5. 来源详情返回删除可用性及内容、视频笔记、活跃任务三个阻塞计数；有任一阻塞时手动删除返回 409。
6. 删除最后一个内容或视频笔记后自动删除孤立 Source、Snapshot、Segment 和 Source 专属 VideoAsset/Transcript；Place、路线与独立地点信息保留。
7. 所有保存、删除与自动清理均刷新关联页面缓存并写入脱敏审计；不触发真实模型或任务重跑。

## 验收记录

- 后端 pytest 55 项及 Ruff 通过；前端 ESLint、Vitest 10 项、TypeScript、Vite build 通过。
- Browser 桌面验证 4 个路由选择、3 个参数输入、18 条核心契约、参数保存成功状态；来源删除禁用态与孤立来源启用态均符合契约。
- 390×844 移动端设置页无横向溢出，桌面与移动端控制台均无 ERROR/WARN。

## 页面设计

AI 模型页沿用暖白纸面卡片：状态摘要下是一张四选项模型路由卡，随后是三列转写参数卡、Prompt 契约与模型库。来源审计详情标题栏提供“删除记录”，不可删除时禁用并在证据统计下显示阻塞数量。桌面保持双栏来源审计，移动端改为单列且操作按钮保持可触达。


---

# FILE: ai-gateway/AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md

# AI Workload Gateway v2 契约索引

> 2026-09-03 按主题拆分；原章节编号保留。只选与本任务有关的一篇，再按标题定位，不要求连读。正文中的规划/旧状态不证明当前实现；先看 [当前状态](IMPLEMENTATION_STATUS.md) 与相关 [冻结约束](REGRESSION_AND_CHANGE_GUARD.md)。

| 任务主题 | 分篇 | 原章节 |
| --- | --- | --- |
| 架构与模型边界 | [01-architecture-models.md](ai-gateway/01-architecture-models.md) | 1–11 |
| Gateway、路由与公共上下文 | [02-gateway-context.md](ai-gateway/02-gateway-context.md) | 12–27 |
| Pipeline 优化、Provider 与 Usage | [03-pipeline-providers.md](ai-gateway/03-pipeline-providers.md) | 28–41 |
| Stage Policy 与参数设置 | [04-stage-policy.md](ai-gateway/04-stage-policy.md) | 41A–41I |
| 单次任务策略、API 与 Cache Key | [05-job-policy.md](ai-gateway/05-job-policy.md) | 41J–41S |
| 历史工作包与验收设计 | [06-rollout-acceptance.md](ai-gateway/06-rollout-acceptance.md) | 42–50 |

## 使用边界

- 本方案形成于 2026-08-28。模型体积、型号建议与 Work Package 状态属于当时规划；不能据此宣称当前模型能力、路由已升级或生产验收完成。
- AUTO 等“实际运行语义”必须核对当前策略解析代码与测试，不能只照设计目标推断。未授权的质量升级、视觉理解、RAG 不自动实施。
- 真实 Provider/视频与 Benchmark 只按 [生产验收门禁](ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md) 执行；第 6 分篇默认只在追溯或明确验收任务时读取。
- 现有 Provider 运行说明见 [ai-gateway/AI_RUNTIME_AND_PROVIDERS.md](ai-gateway/AI_RUNTIME_AND_PROVIDERS.md)；不要求每次与所有分篇一起读取。


---

# FILE: ai-gateway/01-architecture-models.md

# 架构与模型边界

> 来源：ai-gateway/AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md，原章节 1–11（正文保留，2026-09-03 分篇）。返回 [主题索引](ai-gateway/AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md)。本篇是契约/规划，不是已实施清单；当前结论见 [实施状态](IMPLEMENTATION_STATUS.md)，安全与回归见 [冻结清单](REGRESSION_AND_CHANGE_GUARD.md)。裸文档路径均以 dev docs/ 为基准。只读取命中章节及其必要约束。

# 1. 架构决策

后续 AI 架构统一采用：

```text
AI Workload Gateway
+ Capability-based Routing
+ Local-first / Remote-selectable Execution
+ Context Reduction
+ Schema & Evidence Validation
+ Domain Context
+ Cache / Budget / Audit
```

原则：

```text
确定性代码做能确定的事
本地模型做高频、便宜、可验证的“量”
远程强模型做困难、专业、高价值的“难”
用户始终可以对任意 AI 语义阶段选择远程模型
```

“默认本地优先”**不等于**“远程模型只能是 fallback”。

每个 AI 语义阶段必须支持：

```text
AUTO
LOCAL_ONLY
LOCAL_FIRST
REMOTE_FIRST
REMOTE_ONLY
```

并支持单次任务覆盖具体 Provider / Model。

非 AI 的确定性步骤，例如下载、hash、时间换算、坐标计算、黑帧检测，不要为了“每阶段可远程”而模型化。

---

# 2. 当前 Provider 层保留

当前项目已有：

```text
LLMProvider
OllamaProvider
OpenAICompatibleProvider
FallbackLLMProvider
ExternalCallAudit
```

当前 `OllamaProvider` 已使用：

```text
/api/chat
stream = false
keep_alive = 0
format = json
```

现有 Provider 层解决的是：

> 怎么调用某个模型。

本次新增的 `AI Workload Gateway` 解决：

> 是否需要模型、给多少上下文、选哪个模型、结果是否合格、是否升级远程、是否可复用、预算是否允许。

目标：

```text
Business Pipeline
      ↓
AI Workload Gateway
      ↓
Router / Reducer / Cache / Validator / Escalation
      ↓
Existing Provider Layer
      ↓
Ollama / OpenAI-compatible / Future Providers
```

不要把 HTTP Provider 逻辑重复搬入 Gateway。

---

# 3. 不再硬编码 Qwen3.5:9B

本项目业务代码不得硬编码：

```text
qwen3.5:9b
qwen3:8b
qwen2.5:7b
```

业务只声明 Capability。

模型由 Profile 配置：

```text
FAST_LOCAL_TEXT
MAIN_LOCAL_TEXT
LOCAL_VISION
REMOTE_FAST
REMOTE_STRONG
REMOTE_VISION
REMOTE_SPECIALIST
```

允许多个 Profile 指向同一个模型。例如在 16 GB Mac mini 上：

```text
FAST_LOCAL_TEXT = qwen2.5:7b
MAIN_LOCAL_TEXT = qwen2.5:7b
```

完全合法。

---

# 4. Qwen2.5:7B / Qwen3:8B 结论

## 4.1 标准型号都是文本模型

Ollama 标准：

```text
qwen2.5:7b
qwen3:8b
```

均为 **Text-only**。

它们不能直接处理图片。

视觉必须使用独立型号，例如：

```text
qwen2.5vl:7b
qwen3-vl:4b
qwen3-vl:8b
```

因此 ModelProfile 必须显式声明：

```python
modalities={"text"}
```

或：

```python
modalities={"text", "image"}
```

不能根据模型名称猜视觉能力。

## 4.2 当前 Ollama 参考体积

| 模型 | 当前 Ollama 参考体积 | 模态 | 推荐角色 |
|---|---:|---|---|
| `qwen2.5:7b` | ~4.7 GB | Text | Fast/Main Local |
| `qwen3:8b` | ~5.2 GB | Text | Main Local |
| `qwen2.5vl:7b` | ~6.0 GB | Text+Image | Local Vision |
| `qwen3-vl:4b` | ~3.3 GB | Text+Image | Lightweight Vision |
| `qwen3-vl:8b` | ~6.1 GB | Text+Image | Main Vision |

模型文件体积不等于运行峰值内存。还要考虑 KV cache、Metal buffer、上下文、Whisper、Backend 和 macOS 本身。

---

# 5. Qwen2.5:7B 的定位

优点：

- 比 Qwen3:8B 略轻；
- 成熟稳定；
- 中文能力好；
- Qwen2.5 官方强调 structured data / JSON 能力；
- 不存在默认 thinking 带来的额外推理时间；
- 很适合大量固定 Schema 的任务。

推荐 Capability：

```text
CLASSIFICATION
STRUCTURED_EXTRACTION
ENTITY_EXTRACTION
TRANSCRIPT_CORRECTION
LINK_CLASSIFICATION
LIGHT_SUMMARIZATION
DOMAIN_TERM_EXTRACTION
```

建议作为：

```text
FAST_LOCAL_TEXT
```

如果真实 benchmark 已满足质量，也可以直接作为 `MAIN_LOCAL_TEXT`，减少模型切换和内存波动。

---

# 6. Qwen3:8B 的定位

Qwen3 官方相较 Qwen2.5 强调：

- reasoning；
- instruction following；
- agent capability；
- multilingual；
- thinking / non-thinking 双模式。

更适合：

```text
较复杂结构化抽取
章节摘要
语义冲突判断
复杂实体关系
本地 Verify
Ambiguity Analysis
```

建议作为：

```text
MAIN_LOCAL_TEXT
```

但必须通过真实项目 benchmark，而不是只看排行榜。

---

# 7. Qwen3 Thinking 默认关闭

对于以下高频阶段默认使用 non-thinking：

```text
CLASSIFICATION
STRUCTURED_EXTRACTION
ENTITY_EXTRACTION
TRANSCRIPT_CORRECTION
CHUNK_SUMMARIZATION
JSON_REPAIR
```

原因：

- 更低延迟；
- 更少本地计算；
- 更容易控制输出；
- Pipeline 吞吐更重要。

只有：

```text
COMPLEX_VERIFY
CONFLICT_RESOLUTION
COMPLEX_REASONING
AMBIGUITY_ANALYSIS
```

才允许 Router 根据策略开启 thinking。

thinking 必须：

```text
显式启用
有输出预算
有 Audit
```

不能全局默认开启。

---

# 8. Mac mini 16 GB 推荐部署

## 稳定优先方案

```text
FAST_LOCAL_TEXT = qwen2.5:7b
MAIN_LOCAL_TEXT = qwen2.5:7b 或 qwen3:8b
LOCAL_VISION = 按需加载，不常驻
REMOTE_STRONG = 用户配置的 OpenAI-compatible 模型
```

如果频繁切换两个文本模型造成加载时间或内存压力，则只保留一个 7B/8B 文本模型。

不要为了理论上多一个“Main Model”牺牲稳定性。

---

# 9. 本地模型最低要求

任何本地模型进入 Router 前必须通过 Capability Probe。

最低要求：

### 9.1 API

支持：

```text
Ollama /api/chat
```

未来也允许 localhost OpenAI-compatible endpoint。

### 9.2 中文

必须测试：

- 中文指令跟随；
- 中文实体；
- 中英混合；
- 地名/人名；
- 数字日期；
- 专有名词保持。

### 9.3 Structured Output

最低：

```text
JSON object
```

推荐：

```text
JSON Schema constrained output
```

Profile 记录：

```python
supports_json_mode
supports_json_schema
```

### 9.4 Context

项目自己控制工作窗口，不追求塞满模型标称上下文。

建议：

```text
最低：16K
推荐：32K+
```

即使模型标称 128K / 256K，16 GB Mac mini 也不应默认使用超长上下文。

### 9.5 Output Limit

Provider 必须支持或模拟：

```text
max_output_tokens
```

### 9.6 可重复性

Benchmark 至少记录：

```text
schema_pass_rate
field_consistency
evidence_consistency
```

### 9.7 模态

明确：

```text
text
image
```

视觉任务不能调度到 text-only 模型。

---

# 10. 本地模型的限制

本地模型不能被当成知识库。

以下内容尤其容易超出本地 7B/8B 的知识和辨识能力：

- 医学；
- 法律；
- 航空；
- 小众设备；
- 地方历史；
- 方言；
- 新政策；
- 行业黑话；
- 游戏/动漫小众设定；
- 罕见地名与专有名词。

正确做法：

```text
Domain Context
+ Relevant Evidence
+ Local/Remote Model
```

而不是简单：

```text
换更大模型
```

模型不知道时允许输出：

```text
UNKNOWN
```

禁止无证据补全事实。

---

# 11. 多模态策略

视觉 Capability 独立：

```text
VISION
DOCUMENT_VISION
SCREENSHOT_UNDERSTANDING
GUI_UNDERSTANDING
VISUAL_ENTITY_EXTRACTION
```

Mac mini 16 GB 建议：

```text
轻量图片初筛
→ qwen3-vl:4b 等较轻视觉模型

复杂文档 / 专业图 / 高质量视觉
→ REMOTE_VISION

用户要求最高质量
→ REMOTE_ONLY
```

视频不要把大量帧直接送视觉模型。

继续：

```text
Metadata + Note + Transcript time range
→ 确定候选时间码
→ 确定性抽帧
→ 少量候选帧
→ Vision Model
```

---


---

# FILE: ai-gateway/02-gateway-context.md

# Gateway、路由与公共上下文

> 来源：ai-gateway/AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md，原章节 12–27（正文保留，2026-09-03 分篇）。返回 [主题索引](ai-gateway/AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md)。本篇是契约/规划，不是已实施清单；当前结论见 [实施状态](IMPLEMENTATION_STATUS.md)，安全与回归见 [冻结清单](REGRESSION_AND_CHANGE_GUARD.md)。裸文档路径均以 dev docs/ 为基准。只读取命中章节及其必要约束。

# 12. 所有 AI 阶段都可选远程

新增：

```python
class AIExecutionMode(str, Enum):
    AUTO = "AUTO"
    LOCAL_ONLY = "LOCAL_ONLY"
    LOCAL_FIRST = "LOCAL_FIRST"
    REMOTE_FIRST = "REMOTE_FIRST"
    REMOTE_ONLY = "REMOTE_ONLY"
```

“手动指定模型”不要再作为 `MANUAL` mode，而是：

```text
provider_override
model_override
```

## AUTO

综合：

```text
capability
quality
domain
privacy
local load
benchmark
model availability
validation
```

自动选择。

## LOCAL_ONLY

绝不外发。失败则 FAIL/PARTIAL，不允许偷偷升级远程。

## LOCAL_FIRST

```text
Local
→ Validate
→ PASS
或
→ Remote Escalation
```

## REMOTE_FIRST

优先质量，可配置远程不可用时是否 Local fallback。

## REMOTE_ONLY

强制远程。用于专业、高价值、用户主动高质量重跑等。

---

# 13. Quality Preset

普通用户不需要逐 Stage 调参数。

提供：

```text
ECONOMY
BALANCED
QUALITY
LOCAL_PRIVATE
CUSTOM
```

建议：

```text
ECONOMY
→ LOCAL_FIRST
→ 仅 validation fail 升级

BALANCED
→ AUTO

QUALITY
→ 重要语义阶段 REMOTE_FIRST

LOCAL_PRIVATE
→ 所有 AI Stage LOCAL_ONLY

CUSTOM
→ 逐 Stage 配置
```

创建任务时允许单次覆盖。

优先级：

```text
Single-run Stage Override
> Single-run Preset
> Saved Stage Policy
> Global Preset
> System Default
```

---

# 14. AI Workload Gateway

建议新增：

```text
backend/src/zhijian/ai/
├── gateway.py
├── schemas.py
├── capabilities.py
├── model_registry.py
├── router.py
├── context_reducer.py
├── domain_context.py
├── validator.py
├── escalation.py
├── cache.py
├── budget.py
├── resource_manager.py
└── audit.py
```

Provider HTTP 实现继续留在现有 `providers/`。

---

# 15. Capability Enum

第一版统一：

```text
CLASSIFICATION
STRUCTURED_EXTRACTION
ENTITY_EXTRACTION
TRANSCRIPT_CORRECTION
CHUNK_SUMMARIZATION
GLOBAL_SYNTHESIS
VERIFY
CONFLICT_RESOLUTION
DOMAIN_TERM_EXTRACTION
DOMAIN_REASONING
VISION
DOCUMENT_VISION
SCREENSHOT_UNDERSTANDING
```

兼容并整理现有文档中的：

```text
LONG_CONTEXT
SEMANTIC_MATCH
SCREENSHOT_PLANNING
NOTE_TOC_AND_SECTION_SUMMARY
```

不要同时保留多套 role string。

---

# 16. AIRequest

建议：

```python
class AIRequest(BaseModel):
    capability: AICapability
    stage: str

    input_text: str | None = None
    evidence_segments: list[EvidenceSegment] = []

    output_schema: dict | None = None

    quality_target: AIQualityTarget = AIQualityTarget.BALANCED
    execution_mode: AIExecutionMode | None = None

    provider_override: str | None = None
    model_override: str | None = None

    domain: str | None = None
    domain_pack_ids: list[str] = []

    privacy: AIPrivacyPolicy = AIPrivacyPolicy.NORMAL

    max_input_tokens: int | None = None
    max_output_tokens: int | None = None

    cache_policy: AICachePolicy = AICachePolicy.USE
    force_regenerate: bool = False

    allow_escalation: bool = True
```

---

# 17. AIResult

```python
class AIResult(BaseModel):
    data: Any

    provider: str
    model: str
    capability: AICapability

    execution_route: str
    local_attempted: bool
    remote_attempted: bool
    escalated: bool

    validation_status: str
    confidence: float | None
    evidence_ids: list[str]

    cache_hit: bool

    input_tokens: int | None
    output_tokens: int | None
    cached_tokens: int | None

    duration_ms: int

    prompt_version: str
    schema_version: str
    parser_version: str

    escalation_reasons: list[str]
```

---

# 18. ModelProfile

```python
class ModelProfile(BaseModel):
    id: str
    provider: str
    model: str

    location: Literal["LOCAL", "REMOTE"]
    modalities: set[str]
    capabilities: set[AICapability]

    supports_json_mode: bool
    supports_json_schema: bool
    supports_thinking: bool
    supports_tools: bool

    context_window: int
    recommended_working_context: int
    max_output_tokens: int

    quality_tier: Literal["FAST", "MAIN", "STRONG", "SPECIALIST"]
    specialties: set[str] = set()

    enabled: bool = True
```

---

# 19. Capability Probe

新增模型首次保存/测试时至少测试：

```text
plain text
Chinese instruction
JSON output
JSON Schema（如声明支持）
Evidence ID echo
long-ish context
vision（如声明支持）
thinking switch（如声明支持）
```

Capability 分别记录 PASS/FAIL。

例如：

```text
qwenX:
CLASSIFICATION = PASS
STRUCTURED_EXTRACTION = PASS
VISION = FAIL
```

仍可作为文本模型。

---

# 20. Router 从 Fallback 升级为 Escalation

现有 Provider fallback 继续处理：

```text
HTTP error
timeout
429
empty response
```

业务 Gateway 增加 Semantic Escalation。

触发原因：

```text
SCHEMA_FAILED
EVIDENCE_MISSING
LOW_CONFIDENCE
DOMAIN_UNKNOWN
DOMAIN_AMBIGUOUS
ENTITY_CONFLICT
OUTPUT_INCOMPLETE
USER_FORCED_REMOTE
QUALITY_PRESET
LOCAL_MODEL_UNAVAILABLE
```

远程不是只在 HTTP 失败后才出现。

---

# 21. 两种远程升级

## VERIFY_DRAFT

远程收到：

```text
relevant evidence
+ local draft
+ validation issue
```

适合字段/实体验证。

## REPROCESS_EVIDENCE

远程重新看：

```text
relevant raw evidence
+ Domain Context
+ schema
```

不给本地答案强锚定。

适合：

```text
专业材料
高价值判断
QUALITY
REMOTE_ONLY
事实冲突
```

---

# 22. Domain Context 公共模块

新增：

```text
DomainContextProvider
```

定义 Domain Pack：

```python
class DomainPack(BaseModel):
    id: str
    name: str
    version: str

    glossary: dict[str, str]
    aliases: dict[str, list[str]]
    rules: list[str]
    examples: list[DomainExample]

    retrieval_sources: list[str]
    prompt_supplement: str | None

    allowed_capabilities: set[AICapability]
```

示例：

```text
travel-cn
aviation
recruitment
medical
legal
photography
local-history
```

航空包可包含：

```text
ICAO / IATA
机场别名
航司简称
机型代码
共享航班
经停 / 联程
专业缩写
```

本地和远程使用同一 Domain Context。

---

# 23. RAG 以后统一接 Domain Context

未来接知识库时，不要每个业务重写 RAG。

统一：

```text
AIRequest
→ DomainContextProvider
→ Retrieve Relevant References
→ Context Reducer
→ Model
```

只发送当前任务相关资料，不发送整个知识库。

第一版 Domain Pack 可以只做：

```text
glossary
aliases
rules
examples
```

不要立即引入复杂向量数据库。

---

# 24. Context Reducer

公共职责：

```text
去重
规范化
Segment 选择
Evidence 选择
邻近上下文
Token 预算
Chunk
历史结果压缩
```

关键原则：

> 模型调用前先决定“哪些内容值得送模型”。

例如 Transcript：

```text
500 Segments
→ Deterministic Quality Gate
→ 35 suspicious segments
→ 35 个目标 + 少量邻近 context
→ Model
```

---

# 25. Cache

所有 AI Stage 支持统一 exact cache。

Cache Key 至少：

```text
capability
input_hash
evidence_hash
prompt_version
schema_version
parser_version
domain_pack_version
provider
model
relevant generation options
```

用户：

```text
force_regenerate=true
```

则跳过 cache，并保留 previous result reference。

---

# 26. Budget

统一叫 `AI Budget`，因为本地也有资源成本。

建议：

```text
max_model_attempts_per_job
max_remote_prompt_tokens_per_job
max_remote_completion_tokens_per_job
max_local_prompt_tokens_per_job
max_local_completion_tokens_per_job
max_ai_wall_time_seconds_per_job
```

不得无限 retry。

---

# 27. LocalAIResourceManager

Mac mini 16 GB 必须有：

```text
gpu_heavy_concurrency = 1
```

Resource Manager 统一处理：

```text
ASR / Text LLM / Vision LLM 排他
模型切换
取消
内存压力
任务结束释放
```

当前 `keep_alive: 0` 第一阶段继续保持。

不要把改长 keep_alive 混入 Token 优化。

未来若优化模型重复加载，单独 benchmark：

```text
peak memory
ASR coexistence
cancel
unload
latency
```

再决定是否做 job-scoped residency。

---


---

# FILE: ai-gateway/03-pipeline-providers.md

# Pipeline 优化、Provider 与 Usage

> 来源：ai-gateway/AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md，原章节 28–41（正文保留，2026-09-03 分篇）。返回 [主题索引](ai-gateway/AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md)。本篇是契约/规划，不是已实施清单；当前结论见 [实施状态](IMPLEMENTATION_STATUS.md)，安全与回归见 [冻结清单](REGRESSION_AND_CHANGE_GUARD.md)。裸文档路径均以 dev docs/ 为基准。只读取命中章节及其必要约束。

# 28. Transcript Correction 改造

## 28.1 Quality Gate

新增 deterministic：

```text
TranscriptQualityGate
```

检测：

```text
低 ASR confidence
明显重复
异常字符
断句异常
专有名词可疑
常见 ASR 错误模式
用户指定重点
```

## 28.2 平台字幕

平台已有字幕默认：

```text
PASS_THROUGH
```

只处理 Quality Gate candidate。

用户仍可：

```text
TRANSCRIPT_CORRECTION = REMOTE_ONLY
force_full_correction = true
```

进行高质量重跑。

## 28.3 Delta Output

模型只返回变化：

```json
{
  "changes": [
    {
      "segment_id": "xxx",
      "corrected_text": "...",
      "confidence": 0.92,
      "reason": "..."
    }
  ]
}
```

未出现的 Segment：

```text
UNCHANGED
```

不再让模型把全文复述一遍。

## 28.4 模型

通用：

```text
qwen2.5:7b
或
qwen3:8b non-thinking
```

专业字幕：

```text
Domain Pack
+ REMOTE_FIRST / REMOTE_ONLY
```

---

# 29. Correction JSON 失败

禁止默认：

```text
大 Batch JSON 错
→ 全文再次请求
→ 递归二分
→ 两半继续付费
```

新顺序：

```text
parse
→ local tolerant repair
→ schema validation
→ 小型 JSON-only repair
→ REVIEW / Escalation
```

只有明确：

```text
context length exceeded
request too large
```

才允许拆 chunk。

---

# 30. 视频 Note 改 Map → Reduce

```text
Transcript Chunks
→ Local Map
→ SectionFacts[]
→ Global Reduce
→ Final Note
```

Local Map 一次输出：

```json
{
  "summary": "...",
  "key_points": [],
  "places": [],
  "people": [],
  "warnings": [],
  "opinions": [],
  "prices": [],
  "domain_terms": [],
  "segment_ids": []
}
```

一次调用同时承担：

```text
chunk summary
place candidate extraction
entity extraction
evidence anchoring
```

---

# 31. Global Reduce

BALANCED：

```text
SectionFacts[]
→ Local
→ Validate
→ PASS
```

QUALITY：

```text
SectionFacts[]
+ Necessary Evidence
→ REMOTE_STRONG
→ Final Note
```

默认不要把完整 Transcript 再发远程。

只有用户显式：

```text
force_full_remote_context
```

才允许全量远程重读。

---

# 32. Place Extraction

默认不再单独读取 Transcript 前 12K。

改为：

```text
Local Map
→ place_candidates per chunk
→ deterministic aggregate
→ resolve mentions
```

保留 `EXTRACT_TRAVEL_FACTS` Pipeline Step 名称兼容 UI / replay。

默认内部不调用 LLM。

但用户如果指定：

```text
EXTRACT_TRAVEL_FACTS = REMOTE_ONLY
```

则允许远程重新提取。

这可以用于罕见地点、地方历史、专业 POI 等场景。

---

# 33. Stage Replay

统一支持：

```python
replay_stage(
    job_id,
    stage,
    execution_override=...,
)
```

例如：

```text
只用远程重跑字幕纠错
只用远程重跑地点抽取
只用远程重跑最终笔记
```

不要重复下载、ASR、抽帧等无关阶段。

---

# 34. 远程 Provider Registry

不要只存在一个“云模型”。

支持角色：

```text
REMOTE_FAST
REMOTE_STRONG
REMOTE_VISION
REMOTE_SPECIALIST
```

兼容：

```text
OpenAI-compatible
DeepSeek
MiMo
其他未来 Provider
```

业务禁止：

```python
if provider == "deepseek":
```

---

# 35. Validation

统一：

```text
Schema
+ Evidence
+ Semantic checks
```

事实型输出无 Evidence：

```text
UNKNOWN / reject / escalation
```

Confidence 不只相信模型自报，应综合：

```text
schema completeness
evidence coverage
domain match
cross-field consistency
deterministic checks
```

Cross-model verification 仅用于：

```text
高价值字段
冲突字段
低置信
QUALITY
```

不要默认所有内容双跑，否则会抵消 Token 优化。

---

# 36. Structured Output Provider 改造

当前 Ollama 只有：

```text
format = "json"
```

新增 Provider 方法：

```python
generate_structured(
    messages,
    model,
    schema,
    options,
)
```

支持 JSON Schema 的 Provider：

```text
直接使用 Schema constraint
```

只支持 JSON object：

```text
JSON mode
+ schema prompt
+ Pydantic validate
```

不具备可靠 Structured Output 的模型不得用于核心抽取 Capability。

---

# 37. Provider Options

新增：

```python
AIProviderRequestOptions(
    max_output_tokens,
    temperature,
    thinking,
    json_schema,
)
```

Thinking Policy：

```text
CLASSIFICATION          OFF
STRUCTURED_EXTRACTION   OFF
ENTITY_EXTRACTION       OFF
TRANSCRIPT_CORRECTION   OFF
CHUNK_SUMMARIZATION     OFF
GLOBAL_SYNTHESIS        OPTIONAL
VERIFY                  OPTIONAL
CONFLICT_RESOLUTION     AUTO/ON
```

---

# 38. Audit / Usage API

扩展现有 `ExternalCallAudit` 或增加统一 execution view。

每次记录：

```text
job
stage
capability
mode
provider
model
local/remote
input chars
input tokens
output tokens
cached tokens
cache hit
attempt
retry
escalated
escalation reason
domain
domain pack version
schema pass
evidence pass
duration
```

新增：

```text
GET /api/jobs/{job_id}/ai-usage
```

返回：

```text
total
local
remote
by_stage
by_model
cache
escalations
```

---

# 39. UI

Settings：

```text
AI Quality
├─ Economy
├─ Balanced
├─ Quality
├─ Local Private
└─ Custom
```

Custom：

| Stage | Mode | Local Model | Remote Model | Domain |
|---|---|---|---|---|
| Transcript Correction | Local First | qwen2.5:7b | Strong #1 | Auto |
| Note Chunk | Local First | qwen3:8b | Strong #1 | Auto |
| Final Note | Remote First | qwen3:8b | Strong #1 | Auto |
| Place Extraction | Local First | qwen2.5:7b | Strong #1 | Travel |

Dropdown 必须按 Capability 过滤。

Vision 阶段不能列 text-only 模型。

创建 Job 时允许覆盖 Preset / Stage。

---

# 40. Benchmark

新增：

```text
scripts/benchmark_ai_profiles.py
```

不要只看公开榜单决定默认模型。

真实 Dataset 至少：

### Transcript
- 正常平台字幕；
- ASR 错字；
- 中英混合；
- 地名；
- 人名；
- 数字；
- 专业术语。

### Structured Extraction
- 招聘；
- 旅行；
- 通用网页；
- 专业材料。

### Note
- 10 / 30 / 60 分钟内容。

### Domain
- 通识；
- 小众专业；
- supplied glossary；
- remote rerun。

指标：

```text
schema_pass_rate
evidence_coverage
field_accuracy
correction_precision
correction_recall
unchanged_preservation
entity_precision
entity_recall
summary_coverage
hallucination_rate
latency
peak_memory
local tokens
remote tokens
escalation_rate
```

模型选择同时看：

```text
quality / second
quality / GB
remote tokens saved
failure rate
```

---

# 41. 初始模型决策

Benchmark 前暂定：

```text
qwen2.5:7b → FAST_LOCAL_TEXT
qwen3:8b   → MAIN_LOCAL_TEXT
```

但不是最终硬要求。

如果真实数据表明：

```text
qwen2.5:7b 已满足 MAIN 质量目标
```

则优先：

```text
FAST_LOCAL_TEXT = MAIN_LOCAL_TEXT = qwen2.5:7b
```

以稳定、低内存和少切换为优先。

---


---

# FILE: ai-gateway/04-stage-policy.md

# Stage Policy 与参数设置

> 来源：ai-gateway/AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md，原章节 41A–41I（正文保留，2026-09-03 分篇）。返回 [主题索引](ai-gateway/AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md)。本篇是契约/规划，不是已实施清单；当前结论见 [实施状态](IMPLEMENTATION_STATUS.md)，安全与回归见 [冻结清单](REGRESSION_AND_CHANGE_GUARD.md)。裸文档路径均以 dev docs/ 为基准。只读取命中章节及其必要约束。

# 41A. Stage-level Model & Parameter Policy

本项目必须把“每个 AI 流程环节独立选择模型及参数”作为一等能力实现，而不是只允许覆盖 Provider / Model。

目标：

```text
Global Defaults
    ↓
Capability Defaults
    ↓
Saved Stage Policy
    ↓
Single Job Override
    ↓
Single Stage Runtime Override
```

越靠下优先级越高。

最终每个 AI Stage 都可以单独控制：

```text
Execution Mode
Local Provider / Model
Remote Provider / Model

Temperature
Max Input Tokens
Max Output Tokens
Thinking
Timeout
Retry Count

Confidence Threshold
Escalation Threshold

Context Strategy
Chunk Size
Neighbor Context

Domain Pack
Cache Policy
Force Regenerate
```

注意：

> 不是所有参数都对所有 Stage 可用。必须通过 Stage/Capability 参数白名单与 Provider Capability 校验，避免 UI 暴露无效参数。

---

# 41B. AIStagePolicy

新增统一配置模型：

```python
class AIStagePolicy(BaseModel):
    stage: str
    capability: AICapability

    # Routing
    execution_mode: AIExecutionMode | None = None

    local_provider: str | None = None
    local_model: str | None = None

    remote_provider: str | None = None
    remote_model: str | None = None

    # Generation
    temperature: float | None = None
    max_input_tokens: int | None = None
    max_output_tokens: int | None = None
    thinking: bool | None = None

    # Runtime
    timeout_seconds: int | None = None
    retry_count: int | None = None

    # Quality / Escalation
    confidence_threshold: float | None = None
    escalation_threshold: float | None = None

    # Context
    context_strategy: str | None = None
    chunk_size: int | None = None
    neighbor_segments: int | None = None

    # Domain
    domain: str | None = None
    domain_pack_ids: list[str] = []

    # Cache
    cache_enabled: bool | None = None
    force_regenerate: bool = False
```

允许项目根据现有 Settings / Pydantic 结构调整字段名，但必须保留上述能力边界。

---

# 41C. 参数继承优先级

运行时必须通过统一 Resolver 合并参数。

推荐：

```text
System Defaults
    ↓
Global AI Preset
    ↓
Capability Defaults
    ↓
Saved Stage Policy
    ↓
Job-level Override
    ↓
Stage Runtime Override
```

最终产出：

```python
ResolvedAIStagePolicy
```

业务 Pipeline 不直接自己拼配置。

示例：

```text
Global:
    BALANCED

Capability STRUCTURED_EXTRACTION:
    temperature = 0.1
    max_output_tokens = 1200

Stage TRAVEL_PLACE_EXTRACTION:
    execution_mode = LOCAL_FIRST
    local_model = qwen2.5:7b
    remote_model = remote-strong
    confidence_threshold = 0.75

Single Job:
    quality = QUALITY

Single Stage Runtime Override:
    TRAVEL_PLACE_EXTRACTION = REMOTE_ONLY
```

最终该 Stage 应按：

```text
REMOTE_ONLY
remote-strong
temperature = 0.1
max_output_tokens = 1200
confidence_threshold = 0.75
```

执行。

---

# 41D. Stage 参数必须区分“模型参数”和“业务参数”

不要把所有参数都塞进 Provider Options。

分两层：

## Model Runtime Parameters

```text
temperature
max_input_tokens
max_output_tokens
thinking
timeout
retry_count
```

## Stage Semantic Parameters

例如 Transcript Correction：

```text
candidate_threshold
neighbor_segments
force_full_correction
chunk_size
```

例如 Note Chunk：

```text
chunk_size
section_target_length
max_key_points
```

例如 Place Extraction：

```text
max_places
minimum_evidence_count
domain_pack_ids
```

Stage Semantic Parameters 应归属于 Stage Policy 或 Stage-specific config，而不是 Provider 层。

---

# 41E. Stage 参数白名单

新增：

```text
StageParameterSpec
```

示例：

```python
StageParameterSpec(
    stage="TRANSCRIPT_CORRECTION",
    allowed={
        "execution_mode",
        "local_model",
        "remote_model",
        "temperature",
        "max_input_tokens",
        "max_output_tokens",
        "thinking",
        "timeout_seconds",
        "retry_count",
        "confidence_threshold",
        "escalation_threshold",
        "chunk_size",
        "neighbor_segments",
        "domain_pack_ids",
        "cache_enabled",
    }
)
```

UI 与 API 均通过该 Spec 判断哪些参数可配置。

禁止：

```text
前端写死一套参数
后端接受任意 JSON
```

---

# 41F. Provider Capability Validation

当用户给某个 Stage 配置参数时，需要验证目标 Provider / Model 是否支持。

例如：

```text
qwen2.5:7b
thinking = true
```

如果 Profile 声明：

```text
supports_thinking = false
```

保存时应拒绝或明确忽略，不允许静默假装生效。

同理：

```text
Vision Stage
+ qwen3:8b
```

应直接阻止保存。

JSON Schema、工具调用、上下文窗口、输出长度等同样需要校验。

---

# 41G. Stage 默认参数建议

第一版可提供以下默认值作为起点，最终以 benchmark 调整。

## TRANSCRIPT_CORRECTION

```text
execution_mode = LOCAL_FIRST
temperature = 0.1
thinking = false
retry_count = 0
confidence_threshold = 0.75
escalation_threshold = 0.60
neighbor_segments = 2
chunk_size = 6000~12000 chars（由 benchmark 决定）
cache_enabled = true
```

## NOTE_CHUNK_SUMMARY

```text
execution_mode = LOCAL_FIRST
temperature = 0.2
thinking = false
retry_count = 0
max_output_tokens = 1200~2000
cache_enabled = true
```

## FINAL_NOTE

```text
execution_mode = AUTO 或 REMOTE_FIRST（由 Quality Preset 决定）
temperature = 0.3~0.5
thinking = optional
retry_count = 1
cache_enabled = true
```

## TRAVEL_PLACE_EXTRACTION

默认由 Map 阶段聚合。

当单独启用模型重跑时：

```text
execution_mode = LOCAL_FIRST
temperature = 0.1
thinking = false
retry_count = 0
confidence_threshold = 0.75
domain = travel
cache_enabled = true
```

这些数字不是不可变常量。

必须：

```text
Benchmark
→ 调整 Capability Default
→ 用户仍可覆盖
```

---

# 41H. UI：每 Stage 独立设置

`Custom` 模式必须支持展开每个 AI Stage。

示例：

```text
Transcript Correction
├─ Mode: Local First
├─ Local Provider: Ollama
├─ Local Model: qwen2.5:7b
├─ Remote Provider: DeepSeek-compatible
├─ Remote Model: xxx
├─ Temperature: 0.1
├─ Max Input Tokens: Auto / 8000
├─ Max Output Tokens: 1000
├─ Thinking: Off
├─ Timeout: 180s
├─ Retry: 0
├─ Confidence Threshold: 0.75
├─ Escalation Threshold: 0.60
├─ Neighbor Segments: 2
├─ Domain Pack: Auto
└─ Cache: On
```

另一个：

```text
Final Note
├─ Mode: Remote First
├─ Remote Model: strong-model
├─ Temperature: 0.4
├─ Max Output Tokens: 5000
├─ Thinking: Auto
├─ Retry: 1
├─ Domain Pack: Auto
└─ Cache: On
```

---

# 41I. UI 参数展示层级

为了避免设置页过度复杂，分：

```text
Basic
Advanced
```

Basic：

```text
Mode
Local Model
Remote Model
Quality
```

Advanced：

```text
temperature
tokens
thinking
timeout
retry
confidence
escalation
context/chunk
domain
cache
```

默认折叠 Advanced。

---


---

# FILE: ai-gateway/05-job-policy.md

# 单次任务策略、API 与 Cache Key

> 来源：ai-gateway/AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md，原章节 41J–41S（正文保留，2026-09-03 分篇）。返回 [主题索引](ai-gateway/AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md)。本篇是契约/规划，不是已实施清单；当前结论见 [实施状态](IMPLEMENTATION_STATUS.md)，安全与回归见 [冻结清单](REGRESSION_AND_CHANGE_GUARD.md)。裸文档路径均以 dev docs/ 为基准。只读取命中章节及其必要约束。

# 41J. 单次任务覆盖

创建 Job 时允许：

```text
Use Saved Settings
Economy
Balanced
Quality
Local Only
Custom
```

Custom 下允许只覆盖某几个 Stage。

没有覆盖的 Stage 继续继承 Saved Stage Policy。

例如：

```text
本次视频：
Transcript Correction → Local
Note Chunk → Local
Final Note → Remote Strong
Place Extraction → Remote Specialist
```

无需复制整套全局配置。

---

# 41K. Stage Policy API

建议新增：

```text
GET    /api/ai/stage-policies
GET    /api/ai/stage-policies/{stage}
PUT    /api/ai/stage-policies/{stage}
DELETE /api/ai/stage-policies/{stage}
```

获取可配置参数：

```text
GET /api/ai/stages
```

返回：

```json
{
  "stage": "TRANSCRIPT_CORRECTION",
  "capability": "TRANSCRIPT_CORRECTION",
  "parameter_spec": {},
  "resolved_default": {}
}
```

Job 创建接口支持：

```json
{
  "ai_overrides": {
    "FINAL_NOTE": {
      "execution_mode": "REMOTE_ONLY",
      "remote_model": "xxx",
      "temperature": 0.4
    }
  }
}
```

---

# 41L. Resolved Policy 必须进入 Audit

每次调用 Audit 不只记录最终 model。

还应记录本次生效配置摘要：

```text
policy_source
execution_mode
provider
model
temperature
thinking
max_input_tokens
max_output_tokens
timeout
retry_count
confidence_threshold
escalation_threshold
domain_pack_version
```

不要记录 API Key。

这样以后才能判断：

```text
为什么这个 Stage Token 很高
为什么本次用了远程
为什么同一个 Stage 两次质量不同
```

---

# 41M. Stage 参数与 Cache Key

影响输出语义的参数必须进入 Cache Key。

至少：

```text
model
temperature
thinking
max_output_tokens
prompt_version
schema_version
domain_pack_version
stage semantic parameters
```

纯运行参数，例如：

```text
timeout
retry_count
```

通常不需要进入内容 Cache Key。

Codex 实现时应明确区分：

```text
semantic cache inputs
runtime-only settings
```

---

# 41N. Stage 参数版本化

保存：

```text
stage_policy_version
```

AIResult / Audit 记录：

```text
stage_policy_version
```

这样以后修改默认参数时可以追踪旧结果。

---

# 41O. Stage 参数导入导出

建议为未来维护预留：

```text
Export AI Stage Policies
Import AI Stage Policies
Reset Stage to Default
Reset All AI Settings
```

第一版至少实现：

```text
Reset Stage to Default
```

方便 benchmark 后统一调整。

---

# 41P. 新增 Work Package — Stage Policy & Parameter Control

在原实施顺序中新增独立 Work Package。

建议放在 Routing 之后、Observability 之前：

```text
WP1 Gateway Skeleton
WP2 Model Registry
WP3 Routing / Remote Override
WP4 Stage Policy & Parameter Control
WP5 Observability
WP6 Transcript Delta
WP7 Map/Reduce
WP8 Place Aggregation
WP9 Cache/Budget
WP10 Domain Context
WP11 Vision
```

## WP4 任务

1. `AIStagePolicy`
2. `ResolvedAIStagePolicy`
3. Config Resolver
4. StageParameterSpec
5. Provider Capability Validation
6. Settings persistence
7. Stage Policy API
8. Job-level Stage Override
9. Basic / Advanced UI
10. Audit policy snapshot
11. Cache semantic parameter integration
12. tests

## WP4 验收

必须通过：

```text
不同 Stage 可配置不同模型
不同 Stage 可配置不同 temperature
不同 Stage 可配置不同 max_output_tokens
Qwen3 thinking 可按 Stage 控制
不支持 thinking 的模型不能保存 thinking=true
Vision Stage 不能选择 text-only model
Job override 高于 saved stage policy
Stage runtime override 高于 Job preset
未覆盖参数正确继承
Reset Stage 恢复默认
Audit 能看到最终 resolved policy
```

---

# 41Q. 参数配置的边界

即使用户可以调高级参数，也必须设置安全范围。

例如：

```text
temperature: 0.0 ~ 2.0
retry_count: 0 ~ 3
timeout_seconds: 10 ~ 600
neighbor_segments: 0 ~ 10
```

`max_input_tokens` 不能超过：

```text
min(
  model.context_window - reserved_output,
  system_global_limit,
  local_resource_limit
)
```

本地 Mac mini 还要经过 Resource Manager 的可用预算裁剪。

因此用户填写：

```text
max_input_tokens = 100000
```

不代表实际会直接使用 100000。

最终：

```text
requested policy
↓
capability validation
↓
resource clamp
↓
ResolvedAIStagePolicy
```

并在 UI / Audit 显示实际生效值。

---

# 41R. 参数模板

允许提供 Stage Template：

```text
Economy
Balanced
Quality
Custom
```

但 Template 只是预填 Stage Policy。

不是隐藏不可覆盖的黑箱。

例如：

```text
QUALITY / FINAL_NOTE
```

可以预填：

```text
REMOTE_FIRST
temperature = 0.4
max_output_tokens = 5000
```

用户仍可继续修改。

---

# 41S. 核心验收语句

实现完成后，系统必须满足：

> 同一条 Pipeline 中，用户可以让字幕纠错由 `qwen2.5:7b` 以低 temperature、本地 non-thinking 执行；让 Note Chunk 由 `qwen3:8b` 本地执行；让 Final Note 使用指定远程强模型并单独设置更高输出预算；让专业 Place Extraction 使用另一个远程 Specialist + Domain Pack。所有 Stage 的配置互不污染，并可被单次 Job 覆盖。


---

# FILE: ai-gateway/06-rollout-acceptance.md

# 历史工作包与验收设计

> 来源：ai-gateway/AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md，原章节 42–50（正文保留，2026-09-03 分篇）。返回 [主题索引](ai-gateway/AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md)。本篇是契约/规划，不是已实施清单；当前结论见 [实施状态](IMPLEMENTATION_STATUS.md)，安全与回归见 [冻结清单](REGRESSION_AND_CHANGE_GUARD.md)。裸文档路径均以 dev docs/ 为基准。只读取命中章节及其必要约束。

# 42. Work Packages

> 注意：因新增 Stage-level Model & Parameter Policy，Work Package 总数由 10 个调整为 11 个。

## WP1 — Gateway Skeleton

- 新建 `ai/` 模块；
- 定义 Capability / Mode / Request / Result / ModelProfile；
- 包装现有 Provider；
- 第一版行为先等价当前逻辑；
- 不改变业务结果。

## WP2 — Model Registry + Probe

- Profile Registry；
- Ollama / Remote Profile；
- Capability Probe；
- text / vision 区分；
- thinking；
- schema；
- Settings API。

预置候选：

```text
qwen2.5:7b
qwen3:8b
```

不得要求已经安装。

## WP3 — Routing + Per-stage Remote Override

实现：

```text
AUTO
LOCAL_ONLY
LOCAL_FIRST
REMOTE_FIRST
REMOTE_ONLY
```

先迁移：

```text
TRANSCRIPT_CORRECTION
VIDEO_NOTE_SUMMARY
TRAVEL_PLACE_EXTRACTION
```

## WP4 — Stage Policy & Parameter Control

- 实现 `AIStagePolicy` / `ResolvedAIStagePolicy`；
- 实现配置继承 Resolver；
- 实现 `StageParameterSpec` 参数白名单；
- 实现 Provider / Model Capability Validation；
- 支持每 Stage 独立 Local / Remote Model；
- 支持每 Stage 独立 generation/runtime/quality/context 参数；
- Settings 持久化；
- Stage Policy API；
- Job-level 与 Stage-level override；
- Basic / Advanced UI；
- Audit 记录 resolved policy；
- Cache Key 纳入语义参数；
- 完整继承与边界测试。

## WP5 — Observability

- `/api/jobs/{job_id}/ai-usage`
- stage / model / local / remote；
- retry；
- escalation；
- cache；
- UI。

## WP6 — Transcript Delta

- Quality Gate；
- 平台字幕 pass-through；
- suspicious segment selection；
- neighbor context；
- changed-only schema；
- 去除默认递归二分；
- remote override。

## WP7 — Note Map/Reduce

- SectionFacts；
- chunk local map；
- final local/remote reduce。

## WP8 — Place Aggregation

- Map 阶段产出 places；
- `EXTRACT_TRAVEL_FACTS` 默认 deterministic aggregate；
- REMOTE_ONLY 可重新处理。

## WP9 — Cache + Budget

- exact AI cache；
- force regenerate；
- job/stage budget。

## WP10 — Domain Context

第一版：

```text
glossary
aliases
rules
examples
```

预留 Retrieval，不立即引入复杂向量库。

## WP11 — Vision

有实际视觉需求再做，不阻塞文本 Token 优化。

---

# 43. 测试要求

Routing：

```text
LOCAL_ONLY 永不外发
REMOTE_ONLY 不调本地
LOCAL_FIRST 本地成功不远程
LOCAL_FIRST validation fail 可升级
REMOTE_FIRST 优先远程
Provider override 生效
Model override 生效
```

Privacy：

```text
LOCAL_ONLY
```

必须高于 Router 任何自动策略。

Capability：

```text
text-only model
```

不得进入 Vision。

Qwen3：

```text
CLASSIFICATION
```

默认 thinking off。

Correction：

```text
非 candidate Segment 不变
Segment ID 不丢
时间码不改
```

Cache：

```text
相同输入/版本 → no second provider call
force regenerate → provider called
```

Domain：

加入 glossary 后应提高专业实体识别质量。

---

# 44. Regression Guard

必须保持：

```text
Job 状态机
replay
cancel
ExternalCallAudit
NoteVersion
Evidence
Settings
Provider credential handling
Sensitive / LOCAL_ONLY
Mac mini Ollama unload contract
```

---

# 45. 禁止的实现方式

不要：

1. 在业务代码散落 `qwen2.5:7b` / `qwen3:8b`。
2. 把所有任务强制本地。
3. 只有 HTTP 失败才允许远程。
4. 专业内容只通过换更大模型解决。
5. 所有阶段默认双模型验证。
6. 用超长 Context 代替分块。
7. 默认启用 Qwen3 thinking。
8. 用标准 `qwen3:8b` / `qwen2.5:7b` 处理图片。
9. 为“每阶段可远程”把下载、hash、坐标等确定性步骤模型化。
10. 为了省 API Token 而降低用户主动选择高质量远程处理的能力。

---

# 46. 最终架构

```text
                         User / Job Policy
                                │
                                ▼
┌──────────────────────────────────────────────────────────────┐
│                     AI Workload Gateway                      │
│                                                              │
│ Capability                                                   │
│     ↓                                                        │
│ Domain Detection → Domain Context / Retrieval                │
│     ↓                                                        │
│ Context Reducer / Candidate Selection                        │
│     ↓                                                        │
│ Exact Cache                                                  │
│     ↓                                                        │
│ Policy Resolver                                              │
│ AUTO / LOCAL_ONLY / LOCAL_FIRST / REMOTE_FIRST / REMOTE_ONLY │
│     ↓                                                        │
│ Capability Router                                            │
└──────────────┬──────────────────────────────┬────────────────┘
               │                              │
               ▼                              ▼
       LOCAL MODEL                     REMOTE MODEL
 qwen2.5:7b / qwen3:8b              Strong / Specialist
               │                              │
               └──────────────┬───────────────┘
                              ▼
                   Schema + Evidence
                       Validation
                              │
                    PASS ─────┴──── FAIL
                      │               │
                      │          Escalation
                      └───────┬───────┘
                              ▼
                           AIResult
                              │
                         Cache / Audit
```

视频：

```text
Subtitle / ASR
→ Transcript Quality Gate
→ suspicious segments only
→ Local Correction
→ optional Remote Correction
→ Corrected Transcript
→ Local Map
→ SectionFacts
→ Local/Remote Global Reduce
→ Final Note
→ deterministic Place Aggregate
→ POI Resolution
```

---

# 47. 验收目标

平台字幕视频：

```text
远程 token 降低 >= 50%
目标 >= 70%
```

前提：

```text
Note coverage 不明显下降
Place recall 不明显下降
Evidence binding 不下降
```

ASR 视频：

```text
远程 token 降低目标 >= 30%
```

通用内容：

```text
LOCAL_FIRST 多数任务无需远程即可 PASS
```

专业内容：

```text
REMOTE_ONLY + Domain Pack
```

必须允许只重跑目标 AI Stage，而不是整个 Pipeline。

---

# 48. Codex 最终实施顺序

严格按：

```text
WP1 Gateway Skeleton
→ WP2 Model Registry
→ WP3 Routing / Remote Override
→ WP4 Stage Policy & Parameter Control
→ WP5 Observability
→ WP6 Transcript Delta
→ WP7 Map/Reduce
→ WP8 Place Aggregation
→ WP9 Cache/Budget
→ WP10 Domain Context
→ WP11 Vision
```

每包：

```text
搜索当前源码
→ 只读必要上下文
→ 小范围实现
→ targeted tests
→ 更新状态文档
→ 下一包
```

如果当前分支代码与本文描述有变化，以当前源码为准，但不得改变以下核心决策：

```text
Capability-based
Provider-independent
Per-stage remote selectable
Per-stage model and parameter configurable
Hierarchical policy inheritance and runtime override
Local-first optional
Schema/Evidence validation
Domain Context
Shared context reduction/cache/budget/audit
```

---

# 49. 外部模型信息核对说明

制定本文时核对的当前公开信息：

- Ollama `qwen2.5`: `qwen2.5:7b` 为 Text，当前约 4.7 GB。
- Ollama `qwen3`: `qwen3:8b` 为 Text，当前约 5.2 GB。
- Qwen 官方 Qwen3-8B Model Card：支持 thinking / non-thinking，并强调 reasoning、instruction-following、agent、multilingual 提升。
- Ollama `qwen2.5vl`: `qwen2.5vl:7b` 为 Text+Image，当前约 6.0 GB。
- Ollama `qwen3-vl`: `qwen3-vl:4b` 当前约 3.3 GB；`qwen3-vl:8b` 当前约 6.1 GB，均为 Text+Image。
- Qwen2.5-7B-Instruct 官方 Model Card 强调 structured data、JSON、multilingual 与长上下文能力。

模型库会变化，因此具体体积、Context 和 Capability 必须由 `Model Registry + Capability Probe` 管理，不在业务 Processor 写死。

---

# 50. 一句话最终决策

> **业务层只声明 Capability、Evidence、Quality、Privacy 与 Domain；AI Workload Gateway 负责用确定性预处理、本地模型、领域上下文、缓存和选择性远程升级，以最少资源获得满足质量要求的结果，同时用户可对任意 AI 语义阶段强制使用远程强模型。**


---

# FILE: product/CONTROL_CENTER.md

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

运行日志中的 `ERROR/CRITICAL` Job 事件查询 Replay Options。中间产物有效时提供“从错误步骤继续”，复用上游完成步骤并顺次执行当前/下游；过期时只提供“完整重跑”。日志页不能直接更改步骤或 Provider，完整契约见 `jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md`。

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

2026-08-21 页面审阅提出的缩放对齐、实时步骤诊断、日志工作台和侧栏硬件指标已按 `operations/OPERATIONS_UI_SPEC.md` 实施。设计稿位于 `design/ui/operations-v0.3/`，实际回归与防覆盖规则见 `REGRESSION_AND_CHANGE_GUARD.md`；尚未实现的仅限该规格明确标注的后续增强项。


---

# FILE: operations/OPERATIONS_UI_SPEC.md

# 至简 PC 运维与任务可观测性 UI 规格

版本：v0.4，更新日期：2026-08-25，状态：`IMPLEMENTED / BROWSER_VERIFIED`，适用部署：Mac mini 单节点后端。

## 1. 目的与范围

本规格把 2026-08-21 页面审阅中的四条批注固化为可实施、可测试的产品契约：浏览器缩放或窗口变窄时任务列表仍然对齐；运行中的任务必须实时说明“当前具体在做什么、已持续多久、最后一次活动是什么”；日志页必须达到单机运维工作台的可用程度；PC 左侧栏底部必须持续展示 Mac mini 的真实资源与 Worker 活性。

本轮已交付响应式任务列表、任务详情 WebSocket 实时快照（断线回退 3 秒轮询）、步骤状态事件、游标日志查询/详情抽屉和侧栏实时指标。对应实装审阅图位于 `design/ui/operations-v0.3/`；未实现的增强能力必须保留为待办，不能以效果图替代。

## 2. 共通设计原则

- 延用既有“至简”视觉体系：暖白底、墨黑正文、朱砂红主强调色、苔绿正常状态、灰色结构线，不增加品牌色或彩色应用图标。
- 状态不可只依赖颜色；必须同时显示文字、数值或图标语义。
- 页面展示真实采集值；无数据时显示“暂未采集/等待心跳”，不得用演示硬件、虚构进度或随机曲线填充。
- 时间统一以本机时区展示，诊断详情同时保留 ISO 8601 原始时间；所有实时区域显示“更新于/心跳于”。
- Job ID、Request ID、Provider、Model、Worker 和事件类型是可检索、可复制、可串联日志的运维字段，不只放在人类可读消息中。

## 3. 浏览器缩放与窄桌面适配

### 3.1 适配模型

不检测浏览器缩放倍率，统一按 CSS 有效视口宽度重排。这样浏览器 125%/150%/200% 缩放与窗口变窄得到同一套确定行为。

| 有效视口 | 页面结构 | 任务列表布局 |
| --- | --- | --- |
| `>= 1180px` | 196px 完整侧栏 | 标题、元信息、进度、状态/操作四列 |
| `820–1179px` | 72px 图标侧栏；悬停/聚焦显示名称 | 两层栅格：首行标题+状态，次行元信息+整行进度 |
| `720–819px` | 72px 图标侧栏 | 单列任务卡；进度与操作位于卡片底部 |
| `< 720px` | 手机导航规则 | 使用手机端任务列表，不压缩 PC 表格 |

### 3.2 任务行约束

- 标题列 `min-width: 0`，URL 或长文件名只能在自身区域省略，不得把进度和状态挤出容器。
- 进度条最小可用宽度 160px；空间不足时独占次行，不得与状态文本重叠。
- 百分比使用等宽数字并紧邻进度条；状态列最小宽度 72px，操作按钮最小触控区域 40×40px。
- 页面在 200% 缩放下不得产生整页横向滚动；日志数据表是唯一允许在自身容器内横向滚动的区域。
- 键盘焦点、下拉菜单和侧栏提示不得被 `overflow: hidden` 截断。

## 4. 任务列表与实时运行详情

### 4.1 列表页

任务列表已显示标题/来源、业务类型、当前人类可读阶段、总体进度、运行状态和最后活动时间。运行中任务显示“当前步骤 · 已持续 02:18”，而不是只显示技术枚举或百分比；普通步骤超过 90 秒、LLM 步骤超过 500 秒无任务活动时状态显示“需关注”。

详情页已采用 WebSocket 快照推送，断线后回退为 3 秒轮询；列表页目前按 4 秒刷新，更新不改变排序或整页布局。列表级事件推送是后续增强项。

### 4.2 任务详情顶部“当前处理”卡

运行中任务在概要卡下方固定显示当前处理卡，字段如下：

| 字段 | 示例 | 说明 |
| --- | --- | --- |
| 人类可读步骤 | 生成 AI 笔记 | 首要信息 |
| 技术步骤 | `GENERATE_AI_NOTE` | 支持复制和日志检索 |
| 子状态 | 等待模型首个响应 | 由执行器上报，不由前端推测 |
| 已运行 | `02:18` | 使用单调计时显示，重连后由 `started_at` 恢复 |
| 最后活动 | `2 秒前` | 同时保留 `last_activity_at` |
| Worker | `mac-mini-worker-1` | 显示实例与活性 |
| Provider / Model | `DeepSeek / deepseek-chat` | 仅在该步骤确实调用模型时显示 |
| 最近事件 | 已提交第 3/8 个分块 | 非敏感、可理解的执行事件 |

卡片提供“查看关联日志”入口，跳转后自动以 `job_id` 筛选；“取消任务”和“重试当前步骤”只有在后端返回允许操作时可用。禁止用前端计时自行判断任务失败。

### 4.3 执行时间线

- 时间线必须按 Pipeline 定义的执行顺序排序，不得按数据库返回顺序或更新时间倒排。
- 步骤状态为 `PENDING / RUNNING / COMPLETED / SKIPPED / RETRYING / FAILED / CANCELLED`；当前步骤自动展开，完成步骤可折叠。
- 当前步骤展开区已显示开始时间、已运行时间、最近一条步骤事件和脱敏错误摘要；最近 3 条步骤事件、下次重试时间和步骤级操作权限仍待执行器提供字段后实现。
- 时间线严格按 Pipeline 定义排序；所有技术阶段必须有人类可读中文名称，每行同时显示状态、进度与本步骤用时。只有 Job 和 JobStep 都处于 `RUNNING` 时才显示当前标记；终态任务不把 `CLEAN_CACHE` 或其他最后步骤永久标成当前步骤。
- Worker 心跳超过 30 秒标记“心跳延迟”，超过 90 秒标记“疑似停滞”；阈值由后端配置返回，前端只负责展示。

### 4.4 实时事件契约

当前 WebSocket 每秒推送真实 Job 快照，包含任务/步骤状态、进度、心跳和最后活动；断线后客户端重新请求快照。带 `event_id` 的增量补发、`attempt` 与分块进度字段属于后续增强，不能由前端虚构。

### 4.5 取消停止期与“从头重新运行”（已实施）

任务详情的完整重跑按钮由 `replay-options.full_replay_available` 决定，不由前端硬编码 `FAILED / NEEDS_USER / PARTIAL_SUCCESS`。当 Job 为 `CANCELLED` 但 lease 尚未释放时，按钮显示“正在停止当前步骤”，不可提交，并保持轮询或连接直到操作能力改变；Worker 确认停止后显示“从头重新运行”。

用户点击完整重跑前，确认框说明会从 Pipeline 首步骤创建新 attempt、可能再次访问来源或调用模型；确认后调用 `retry-full`。成功显示“已重新入队”，任务状态为排队中；409 显示最新的 lease/状态原因。不得出现视觉上标为“从头重新运行”却永久禁用且没有原因的按钮。

长模型步骤在时间线中展示最近 batch 活动，例如“AI 校对 12/29 · 上次响应 18 秒前”。侧栏 Worker 进程状态与任务活动分开呈现：前者表示进程是否存活，后者表示该任务是否在推进。

## 5. 运维级日志工作台

### 5.1 页面结构

日志页由健康摘要、筛选工具条、事件表格和详情抽屉组成。健康摘要显示 API、Worker、最近 ERROR、近 1 小时 WARNING 数量和日志写入状态；它只用于快速定位，不替代首页系统状态。

### 5.2 筛选与控制

- 时间范围：已实现最近 15 分钟、1 小时、24 小时和全部时间；7 天与自定义起止时间待补。
- 级别：多选 `DEBUG / INFO / WARNING / ERROR / CRITICAL`。
- 组件与事件类型：可搜索多选。
- 关联标识：Job ID、Request ID、实体 ID 精确筛选。
- 全文检索：搜索消息与允许索引的结构化详情，不搜索密钥或正文。
- 实时模式：默认每 5 秒增量刷新；“实时跟随”开启时置顶新事件，用户滚动查看历史后自动暂停并给出“有 N 条新日志”。
- 已支持重置筛选、关联 Job 链接和单条脱敏 JSON 导出；筛选链接复制、JSONL/CSV 批量导出待补。

### 5.3 表格与详情

表格最少包含时间、级别、组件/事件、关联对象、耗时/状态码、消息。长消息在单元格内最多两行，点击行打开详情抽屉；窄桌面下表格可在自身容器横向滚动，固定时间和级别列。

详情抽屉显示完整时间、事件类型、Job/Request/实体标识、结构化 detail、异常摘要和经过脱敏的堆栈。标识均可复制，并提供“仅看同一任务”“仅看同一请求”“打开任务”快捷动作。API Key、Cookie、配对码、Authorization、正文、上传内容和完整个人档案永不展示或导出。

### 5.3.1 从错误步骤继续（现有整任务按钮待返工）

当选中事件为 `ERROR/CRITICAL` 且规范关联现存 Job/Step 时，详情抽屉加载 Replay Options。中间产物有效时，在“打开任务”旁显示主操作“从错误步骤继续”；过期时显示“中间产物已清理”，只提供次级“完整重跑”。

确认框展示任务名称、失败步骤、事件时间、复用步骤、重新执行步骤、中间产物保留截止和当前重试次数。确认前不发送请求；不能允许用户任意选择 from_step。

提交中按钮禁用并显示“正在从该步骤恢复”；成功后展示 REUSED/RETRYING 状态和“查看续跑进度”。失败显示稳定 `REPLAY_*` 原因。完整契约见 `jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md`。

### 5.4 查询契约

日志查询需要支持游标分页和组合筛选：`from/to`、重复 `level`、重复 `component`、`event_type`、`job_id`、`request_id`、`entity_id`、`query`、`cursor`、`limit`、`sort`。返回 `items`、`next_cursor`、`server_time` 与 `applied_filters`。页面初始限制 100 条，滚动加载，不一次性读取全部日志。

## 6. 侧栏 Mac mini 实时指标

### 6.1 完整侧栏

左下角系统卡固定显示：节点在线状态、CPU 使用率、内存已用/总量、数据盘使用率、Worker 最后心跳。CPU/内存/磁盘使用细进度条和数字，默认每 5 秒刷新；超过 15 秒未更新时显示“指标延迟”，不保留看似实时的旧值。

### 6.2 收窄侧栏

72px 图标侧栏只保留节点状态按钮和异常徽标；点击或键盘聚焦后弹出同一组完整指标。弹层不得遮挡当前任务的主要操作，Escape 可关闭。

### 6.3 指标数据契约

状态接口至少返回：`sampled_at`、`hostname`、`cpu.percent`、`memory.used_bytes/total_bytes/percent`、`disk.used_bytes/total_bytes/percent`、`services.api.status`、`services.worker.status/heartbeat_at`。所有值来自当前 Mac mini；采集失败时单项返回 `null` 与 `unavailable_reason`，其他指标继续显示。

## 7. 状态与告警语义

| 语义 | 颜色 | 文案要求 |
| --- | --- | --- |
| 正常 | 苔绿 | 在线、运行中、刚刚更新 |
| 处理中 | 朱砂红 | 当前步骤、实时进度、主动操作 |
| 延迟/需关注 | 琥珀棕 | 必须给出延迟秒数或原因 |
| 故障 | 深红 | 必须给出可执行入口，如关联日志/重试 |
| 未采集 | 中性灰 | 明确写“暂未采集”，不得显示 0% 冒充真实值 |

## 8. 验收标准

1. Chrome/Safari 在 935×886 CSS 视口下，任务列表标题、进度、状态和操作不重叠；125%、150%、200% 缩放均无整页横向滚动。
2. 运行任务的当前步骤、子状态、已运行时间和最后活动在 3 秒内更新；断开 WebSocket 后自动进入轮询并显示连接状态。
3. 人工停止 Worker 后，普通步骤 90 秒、LLM 步骤 500 秒出现任务疑似停滞提示，并可一键进入该 Job 的过滤日志；Worker 全局心跳仍使用独立阈值。
4. 时间线按 Pipeline 定义排序，当前步骤自动展开，失败/重试/跳过均有独立语义。
5. 日志可按时间、级别、组件、事件、Job ID、Request ID 和关键词组合筛选；详情抽屉可复制标识、关联任务，分页加载稳定。
6. 日志页面、单条导出文件和浏览器网络响应中均不存在 API Key、Cookie、配对码、Authorization、正文和完整个人档案。
7. 侧栏指标与状态 API 的真实值一致；采集失败显示不可用原因，超过 15 秒不再把旧值显示为实时。
8. 键盘可完成侧栏系统卡、任务详情、日志筛选与详情抽屉全部操作，焦点可见，状态不只依赖颜色。

## 9. 设计稿映射

| 文件 | 规格重点 |
| --- | --- |
| `design/ui/operations-v0.3/01-tasks-responsive-pc.png` | 935px 缩放/窄桌面任务列表重排 |
| `design/ui/operations-v0.3/02-task-detail-live-pc.png` | 当前处理诊断卡、实时事件与有序时间线 |
| `design/ui/operations-v0.3/03-logs-operations-pc.png` | 健康摘要、组合筛选、运维表格与详情入口 |
| `design/ui/operations-v0.3/04-sidebar-runtime-pc.png` | 完整侧栏的真实 CPU/内存/磁盘/心跳指标 |


---

# FILE: architecture/API_DESIGN.md

# API Design

> API 风格：REST + WebSocket
> 第一版单用户，本地使用，但仍保持明确资源边界。

---

# 1. Capture API

## POST /api/inbox

输入：

```json
{
  "value": "视频标题\nhttps://b23.tv/...\n复制打开 App"
}
```

`value` 是原始粘贴值。服务端是输入判定的权威方，不依赖前端 `startsWith("http")`。现有 `{url}` / `{text}` 字段可保持向后兼容，但都应进入同一 Input Normalizer。

唯一链接识别成功时返回：

```json
{
  "item_id": "...",
  "job_id": "...",
  "status": "QUEUED",
  "input_kind": "SHARE_TEXT_WITH_URL",
  "selected_url": "https://b23.tv/..."
}
```

存在多个无法唯一选择的内容链接时不创建处理 Job，返回 `422`：

```json
{
  "code": "CAPTURE_MULTIPLE_URLS",
  "message": "检测到多个链接，请选择要处理的内容",
  "details": {"candidates": ["https://...", "https://..."]}
}
```

选择规则：canonical 去重后仅一个候选直接使用；多个候选中仅一个命中专用 Resolver 时自动选择；仍有多个内容候选时不得静默选择第一个。选中 URL 后，周围标题/分享文案不发送给 Resolver、Classifier 或 LLM。

返回：
`202 Accepted`

```json
{
  "item_id": "...",
  "job_id": "...",
  "status": "QUEUED"
}
```

URL/Text 使用 JSON。文件使用：

`POST /api/inbox/upload`（`multipart/form-data`）

MVP 允许：

- `.pdf`
- `.docx`
- `.xls` / `.xlsx`
- `.png` / `.jpg` / `.jpeg`

上传时校验扩展名、MIME、文件头、大小上限与内容哈希；原文件写入本地永久 Source 存储，再创建统一 Job。扫描 PDF 与图片自动进入 OCR Step。

## GET /api/inbox/{id}

返回：
- input
- resolved type
- processor
- processing status
- result link

---

# 2. Recruitment API

## GET /api/recruitment/dashboard

返回 `RecruitmentDashboardVM`：

```json
{
  "nearest_deadline": {},
  "action_items": [],
  "eligibility_summary": {},
  "recommended_positions": [],
  "profile_questions": [],
  "recent_notices": []
}
```

## GET /api/recruitment/notices

支持分页与状态。

## GET /api/recruitment/positions

Filters：
- eligibility
- region
- deadline
- organization
- education
- major
- user_state

## GET /api/recruitment/positions/{id}

返回：
- position
- requirement results
- Evidence
- source graph
- deadlines
- actions

## POST /api/recruitment/positions/{id}/state

```json
{"state":"PREPARING"}
```

## GET /api/recruitment/questions

返回按 Information Gain 排序的待补充 Profile。

## POST /api/recruitment/questions/{id}/answer

更新 profile 后触发增量匹配。

---

# 3. Travel API

## Video Note API

```text
GET  /api/video-notes
GET  /api/video-notes/{note_id}
GET  /api/video-notes/{note_id}/transcript
GET  /api/video-notes/{note_id}/transcript/export
GET  /api/video-notes/{note_id}/places
GET  /api/video-notes/{note_id}/screenshots
POST /api/video-notes/{note_id}/regenerate
DELETE /api/video-notes/{note_id}
GET  /api/video-covers/{cover_id}/image
```

`GET /api/video-notes` 的每项增加 `cover_status/cover_image_url/cover_width/cover_height/cover_error`。READY 时必须返回本地受控图片 API URL；非 READY 使用统一占位，不能把远程 CDN URL 当成已下载封面。

`GET /api/video-covers/{cover_id}/image` 只读取数据库已登记的 CoverAsset 路径，返回正确 Content-Type、内容哈希 ETag 和 immutable Cache-Control；禁止接受任意文件路径或代理任意 URL。

`DELETE /api/video-notes/{note_id}` 由列表和详情共用。删除 Note/Version/Section/TOC/Content 投影，保留 Source、VideoAsset、CoverAsset、Transcript、Place 和 Evidence；活跃生成 Job 返回 409。完整契约见 `video/VIDEO_NOTE_DELETE_V044_SPEC.md`。

`GET /api/video-notes/{note_id}` 返回当前 Note Version、视频页元数据、封面、摘要、主旨目录 `toc[]`、按时间线详述章节、地点引用和文稿校对状态；代表性截图仍由独立的 `GET /api/video-notes/{note_id}/screenshots` 返回，前端按 `section_id` 随文嵌入，避免详情首屏传输图片数据。`regenerate` 创建新版本，不覆盖旧版本。

Video Note Detail ViewModel 的默认页面顺序为 Hero → 摘要 → 目录 → 时间线详述 → 地点候选/完整转写。Hero 返回 cover_status/local cover URL；非 READY 时前端收起封面区域，不返回场记板占位。`toc[]` 至少返回 `section_id/start_ms/heading/thesis`；Section 返回 `summary/bullets/place_refs/anchor_id`，Screenshot 返回 `section_id/caption/selection_reason/target_section_id`。

详情响应同时返回 `transcript_status`（`AVAILABLE / EXPIRED / NOT_READY`）、`transcript_correction_status`、`transcript_correction_provider/model`、`transcript_segment_count`、`transcript_retention_until`、`screenshot_status`（`PLANNING / READY / PARTIAL / UNAVAILABLE`）和脱敏 `screenshot_error`。空截图列表必须可区分“尚在规划”“计划为空”和“下载/抽帧失败”。

`GET .../transcript` 在可用期返回全部 Segment 的 `raw_text/corrected_text/start_ms/end_ms/target_section_id`；默认页面使用 corrected_text，raw 只在证据审计入口展示。导出支持：

```text
GET /api/video-notes/{note_id}/transcript/export?version=corrected
GET /api/video-notes/{note_id}/transcript/export?version=raw
```

默认 corrected，返回 `text/plain; charset=utf-8` 与安全的附件文件名，逐行输出完整 AI 校对稿、时间码、校对模型和生成时间；raw 仅由证据/审计入口调用。导出即时生成且不在服务端落第二份文件。文稿满 180 天清理后两个 Transcript 接口返回 `410 Gone`，Note 详情、时间线章节和截图仍可读取。

## Prompt Supplements API v0.4.5

```text
GET /api/settings/prompt-supplements
PUT /api/settings/prompt-supplements
```

API 只允许读写三个低优先级补充文本：`transcript_correction`、`video_note_summary`、`travel_place_extraction`。响应附带不可编辑的 `core_contracts` 摘要、`max_length=1000` 与哈希；固定核心 Prompt 正文不通过 API 返回。PUT 在服务端拒绝修改/覆盖 JSON、Schema、字段、键名、ID 或顺序的越权语言，并将变更写入审计事件。完整边界见 `ai-gateway/PROMPT_SUPPLEMENTS_V045_SPEC.md`。

## 转写路由、参数与来源清理 API v0.4.6

`GET/PUT /api/settings/model-routing` 在通用 `primary_id/fallback_id` 之外返回可空的 `transcript_primary_id/transcript_fallback_id`；转写专属值优先，空值继承通用对应项。`GET/PUT /api/settings/transcript-processing` 管理 `chunk_chars/batch_size/timeout_seconds`，缺省为 `12000/128/180` 并执行数值范围校验。

`GET /api/sources/{id}` 返回 `deletion.allowed/content_count/video_note_count/active_job_count`。`DELETE /api/sources/{id}` 只删除孤立来源；仍有关联业务内容或活跃 Job 时返回 409。删除最后一个内容或视频笔记后，服务端自动执行同一孤立判断并按需清理来源。

地点候选、Transcript Segment、目录和截图 ViewModel 都返回 `target_section_id`。页面内时间码使用稳定 `anchor_id` 跳转对应 Section；“打开原片”使用独立外链字段，不能与页面内跳转混用。

`note_id` 的规范值为 `AINote.id`（`note_*`），`AINoteVersion.id`（`ntv_*`）只表示一次版本快照，不能写入内容页入口。为兼容已生成内容和旧书签，共享 Note 查询器可把历史 `ntv_*` 解析到所属 `AINote`，但响应和后续写入必须返回规范 `note_*`。未知 ID 返回 404；前端必须展示错误与重试/返回入口，不能把 error 状态继续渲染为 loading。

当前实现使用统一 `POST /api/capture`（文件为 `/api/capture/file`）投递；长期 `/api/inbox` 命名保留为兼容演进方向。响应只确认入队；字幕获取、媒体下载、ASR、总结和 POI 解析全部由 Worker 完成。

## GET /api/travel/dashboard

```json
{
  "days_since_last_trip": 63,
  "map_places": [],
  "recent_discoveries": [],
  "recommended_places": [],
  "pending_reviews": 0
}
```

## GET /api/travel/places

Filters：
- city
- place_type
- user_state
- origin
- query

`source`、偏好打分和复杂状态组合属于后续查询增强；当前通过 `/sources`、地点详情和用户状态分别下钻，避免在单机 SQLite 上预先构建不可用的大型筛选索引。

## GET /api/travel/places/{id}

返回：
- 地点预览、坐标系、坐标、POI Provider 与元数据；
- 观察摘要；
- 详细来源/时间码由 `/api/travel/places/{id}/sources` 返回；
- 地点归纳笔记与其 Evidence 数由 `/api/travel/places/{id}/note` 返回。

## GET /api/travel/places/{id}/note

返回地点归纳笔记、当前版本、来源冲突、Observation 摘要和 Evidence 引用。

## GET /api/travel/places/{id}/sources

返回提到该地点的视频/图文来源、Note、Mention、时间码和原片跳转信息。

## GET /api/travel/map

参数：

- `bbox=min_lng,min_lat,max_lng,max_lat`；
- `zoom`；
- `place_type`；
- `user_state`；
- `origin`；
- `query`；
- `selected_place_id`。

首次进入由前端使用中国大陆全境 viewport；API 不提供默认城市。全国尺度返回 clusters，放大后返回 Marker。响应保存当前 viewport、总数、可见数、聚合和 selected preview。

地点列表、视频笔记中的地点链接和地图 Marker 必须使用同一 `place_id`。Marker 返回：

```text
marker_id
place_id
origin
visibility
canonical_name
place_type
latitude / longitude
address
preview_image
brief
key_observations
source_count
user_state
```

完整归纳笔记统一从 Place Detail/Note API 获取。

## GET /api/travel/map/bootstrap

返回受认证用户加载高德 JS 所需的 JS Key、Security Code、配置状态、默认中国大陆 viewport 和 Provider 诊断。不得返回高德 Web 服务 Key。

## POST /api/travel/map/markers

当前实现支持用户点选坐标与 `longitude/latitude + custom_name`，生成 `USER_CONFIRMED` Place 并返回 `marker_id + place_id`。高德搜索候选直接创建属于后续增强；已由视频链路确认的 POI 仍通过 `RESOLVE_POI` 生成 Provider-confirmed Place。

## DELETE /api/travel/map/markers/{marker_id}

用户 Marker 软删除；自动 Marker 只隐藏地图投影。不得级联删除 Source、Claim、Evidence、PlaceMention 或 Place Note。

## POST /api/travel/map/markers/{marker_id}/restore

恢复软删除/隐藏 Marker。

## POST /api/travel/places/{id}/save
## POST /api/travel/places/{id}/dismiss
## POST /api/travel/places/{id}/visited

写入用户地点状态与可审计事件；独立 PreferenceEvent / VisitEvent 领域模型属于后续增强。

## POST /api/travel/export

格式：
- csv
- json
- geojson

当前以 `POST /api/travel/export?format=csv|json|geojson` 提供。GeoJSON 顶层及每个 Feature 的属性均明确标注 `GCJ02`；只导出当前可见 Marker 投影，不导出已隐藏/软删除的投影。

---

# 4. Control Center API

当前任务控制接口为：

```text
GET  /api/jobs/{job_id}
GET  /api/jobs/{job_id}/replay-options
POST /api/jobs/{job_id}/retry-from-step
POST /api/jobs/{job_id}/retry-full
POST /api/jobs/{job_id}/cancel
```

`GET replay-options` 由服务端根据失败步骤、Artifact Manifest、输入哈希和 TTL 返回：可否步骤续跑、replay_from_step、复用步骤、需重跑步骤、replayable_until 和不可用原因。

`POST retry-from-step`：

```json
{
  "step_name": "GENERATE_AI_NOTE",
  "source_event_id": "evt_..."
}
```

服务端只接受与 Replay Options 一致的失败步骤，不允许前端任意指定 from_step。新 Attempt 复用之前 COMPLETED 且 Artifact 有效的步骤，将它们标记为 REUSED；失败步骤和所有下游步骤重新执行。下游旧输出 INVALIDATED，新版本不覆盖旧版本。

Artifact 已过期/缺失、输入变化、活跃 lease、事件归属不匹配或已有 replay 时返回 409 和稳定 `REPLAY_*` code。`retry-full` 是独立动作，从首步骤创建新的完整 Job；原 Job 正在运行时先请求取消旧流程。响应返回 `job_id / replaced_job_id / stopped_active_job`，客户端导航到新 Job。完整契约见 `jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md`。

`replay-options` 还返回 `full_replay_available / full_replay_reason`。完整重跑在所有状态可提交；运行态 reason 明确提示“将停止当前流程并创建新的完整任务”。步骤恢复卡不重复放置完整重跑按钮。

## GET /api/admin/dashboard
## GET /api/admin/jobs
## GET /api/admin/jobs/{id}

## GET /api/admin/jobs/{id}/replay-options
## POST /api/admin/jobs/{id}/retry-from-step
## POST /api/admin/jobs/{id}/retry-full
## POST /api/admin/jobs/{id}/cancel

## POST /api/admin/jobs/{id}/rerun-external

显式使用外部模型。

## GET /api/admin/sources/{id}
## GET /api/admin/sources/{id}/graph

## GET /api/admin/poi/review
## POST /api/admin/poi/{id}/confirm
## POST /api/admin/poi/{id}/reject

## GET /api/admin/settings
## PUT /api/admin/settings

地图设置至少包括：

```text
amap_js_key
amap_security_code
amap_web_service_key
```

提供独立真实测试，分别报告 JS 配置、Web 服务搜索和域名白名单提示。Web 服务 Key 不回传明文；Security Code 只通过地图 bootstrap 提供给已认证客户端。

---

# 5. WebSocket

## WS /api/ws/jobs

消息：

```json
{
  "job_id":"...",
  "status":"RUNNING",
  "step":"ASR",
  "progress":62,
  "message":"..."
}
```

前端断线后重新连接，再通过 REST 重新取状态，不能只依赖 WS。

---

# 6. ViewModel 原则

API 返回给产品前端的是 ViewModel，而不是 ORM Row。

原因：
- 防止 UI 绑定数据库；
- 支持未来小程序/移动 App；
- 数据库可演进；
- 保持业务语义。

---

# 7. 错误响应

统一错误：

```json
{
  "code":"POI_NEEDS_REVIEW",
  "message":"...",
  "details": {}
}
```

错误 code 必须稳定，不直接依赖异常类名。

---

# 8. 单用户认证

第一版必须支持手机局域网访问，因此认证不是可选项：

- localhost 与 LAN UI 使用同一 API；
- 手机首次配对通过 `POST /api/auth/session` 在请求体提交访问 Token，服务端换发短期 HttpOnly、SameSite Session Cookie；
- 后续 REST 与 WebSocket 握手统一验证 Session Cookie；脚本型客户端可使用 `Authorization: Bearer <access-token>`；
- Token 由 Mac mini 生成、存入 macOS Keychain，并支持轮换；
- CORS 使用明确 Origin allowlist；
- 长期 Token 不放在查询字符串、localStorage 或普通日志中；
- 未授权请求统一返回稳定错误码 `AUTH_REQUIRED` / `AUTH_INVALID`。

未来远程访问再引入完整认证。


---

# FILE: architecture/SECURITY_PRIVACY.md

# Security & Privacy

## 1. 核心原则

Local First。

第一版业务数据默认只在用户的 Mac mini。

---

# 2. 数据分级

## Normal
- 链接
- 地点收藏
- 普通偏好

## Sensitive
- 学历
- 工作经历
- 政治面貌
- 户籍
- 证书

## Local Only
未来高敏感：
- 身份证
- 报名材料
- 自动操作凭据

---

# 3. API Key

正式版本：
- macOS Keychain；
- 数据库只保存引用。

开发 `.env`：
- 只能本机；
- 必须 .gitignore。

---

# 4. Browser Profile

`data/browser/profile/`

可能包含：
- Cookie
- 登录态
- Token
- local storage

禁止：
- Git；
- 普通导出；
- 默认云备份。

Bilibili 字幕或下载可能使用用户 Cookie。Cookie 与 `SESSDATA` 适用同一安全等级：只存平台 Secret Store 或受保护 Browser Profile；不得写入 SQLite 明文、普通日志、错误详情、导出文件或前端通用 Settings API。短链解析和媒体下载必须执行平台 host allowlist、DNS/IP 检查、重定向上限和私网地址拒绝，避免 SSRF。

视频截图属于来源派生资产，默认只保存在本机，不自动进入普通数据导出或云备份。任务缓存视频按 TTL 清理；已被 Note/Place 页面引用的截图保留哈希、时间码和来源关系。隐藏/删除 Marker 不得级联删除截图或 Evidence。

视频封面下载只允许经 Bilibili Resolver 取得且命中图片 CDN allowlist 的 HTTPS URL；执行 DNS/IP、重定向、Content-Type、文件头、尺寸和最大字节校验。封面图片 API 只服务数据库登记路径，禁止任意路径读取和通用 URL 代理。封面原图属于本地派生资产，默认不进入普通导出。

Transcript AI 校对会把视频字幕/ASR 文本发送给所选 LLM Provider，适用 `NORMAL` 来源外发策略并写 ExternalCallAudit。raw_text 与 corrected_text 都受 180 天文稿保留策略约束；默认 UI/导出使用 corrected_text，raw 仅用于本地 Evidence/差异审计。审计日志只能记录 Segment ID、模型、覆盖率和变更计数，不记录原始或校对全文。

完整视频转写属于可导出的来源正文，只在已认证的视频笔记详情提供 TXT 下载。导出由服务端即时生成，不写入缓存目录，不包含 Cookie、模型 Prompt、API Key、内部绝对路径或审计 detail。文件名只使用清洗后的标题与 Transcript Version。

## 用户补充 Prompt

用户在设置页保存的补充 Prompt 属于本地设置数据，写入 SQLite `prompt:supplements`，不写入 Keychain，也不进入 Transcript TXT 导出。审计事件只保留启用阶段与内容哈希，不写入原文，避免运行日志泄露用户表达偏好。核心 Prompt 文件和 JSON/Schema/ID 契约不经 API 提供编辑能力。

完整转写正文固定保留 180 天。清理必须覆盖 `Transcript.text`、`Segment.text/raw_text/corrected_text`、`Evidence.quote` 以及 `metadata_json` 中可能重复保存的全文 fingerprint；只保留哈希、时间范围、数量、版本和 `purged_at`。派生 AI Note 与截图可继续保留，但 UI 必须说明完整转写已过期，不能假装 Evidence 仍可展开。

---

# 5. 外部大模型数据边界

Local First 默认尽可能本地处理。

调用外部模型前：
- 明确 provider；
- 允许用户选择 Local Only；
- 日志记录是否调用外部；
- `NORMAL` 内容按策略发送；
- `SENSITIVE` Profile 默认不外发，仅允许单次明确授权和最小字段发送；
- `LOCAL_ONLY` 永不外发；
- 发送审计记录只保存字段类别与 Evidence/Segment 引用，不复制敏感正文。

高德 Web 服务 Key 与 Security Code 使用 SecretStore；JS API Key 可保存为普通配置。由于 JS Key/Security Code 最终需要提供给已认证浏览器运行时，系统不得宣称其对客户端不可见，必须依赖高德控制台的域名白名单、配额与服务端 Web Key 隔离。Web 服务 Key 永不返回前端。

---

# 6. 本地 Web 安全

MVP 明确支持手机局域网访问：

- 首次安装默认生成高熵访问 Token；
- Mac mini Control Center 显示 LAN 地址并允许复制/轮换 Token；
- 手机首次访问输入 Token，通过 `POST /api/auth/session` 换取短期 HttpOnly、SameSite Session Cookie；
- 浏览器不把长期 Token 保存到 localStorage，REST 与 WebSocket 统一验证 Session；
- localhost 之外的请求缺少/无效 Token 一律拒绝；
- CORS 只允许配置的 LAN Origin，不使用通配符；
- 管理 API 与业务 API 均受保护；
- 监听地址与 LAN 访问可关闭；
- 不做 UPnP、端口映射或公网暴露；
- Token 不写入 URL、普通日志或导出文件。

LAN 传输只允许用户明确配置的可信家庭/办公网络。Phase 0A 必须比较本地 HTTPS 与可信 LAN HTTP 的安装/配对体验；若 MVP 不能可靠部署 HTTPS，UI 必须明确提示不得在公共 Wi-Fi、访客网络或不可信热点中启用 LAN，并将 HTTPS 列为发布前风险项。

---

# 7. 超出可信局域网的远程访问

MVP 不强制实现。

未来可选择：
- VPN
- 安全隧道
- 轻 Control Plane

不建议直接端口映射暴露 FastAPI 到公网。

---

# 8. 日志

日志不得记录：
- API Key
- Cookie
- 登录 Token
- 完整身份证等未来高敏感字段

对敏感 Profile 做字段级掩码。

粘贴分享文案的 Input Normalizer 不在普通日志记录原始全文。URL 任务默认仅持久化选中 URL、输入类型、候选数量、丢弃文本长度和原始输入哈希；周围标题、聊天内容或分享话术不发送给外部 LLM。提取出的每个候选在网络访问前仍需执行 scheme/host allowlist、DNS/IP 与重定向检查，不能因为它出现在文本中就自动抓取。

---

# 9. 数据导出

普通导出不包含：
- browser profile
- API Key
- secret refs
- 原始 Cookie

用户可独立导出：
- Recruitment 数据
- Travel Places
- Evidence
- Settings（无 secret）
- 在 180 天有效期内导出单条视频的完整时间码转写 TXT

---

# 10. 删除

视频笔记删除仅删除 Note 阅读产物，保留共享 Source、VideoAsset、CoverAsset、Transcript、Place 和 Evidence；活跃生成 Job 阻止删除。确认框必须说明不可恢复和保留边界，审计不记录 Transcript 正文。完整契约见 `video/VIDEO_NOTE_DELETE_V044_SPEC.md`。

其他未来删除能力：
- 删除 Source；
- 删除 Snapshot；
- 删除 Profile；
- 删除 Place；
- 清理 Cache。

删除业务对象时注意 Evidence 引用与审计完整性。

步骤级 Replay Cache 默认保留 24 小时，但临时 Cookie、Secret 和未登记 scratch 必须立即清理；Artifact 日志只记录哈希、路径引用、类型、版本和到期时间，不记录正文或凭据。


---

# FILE: testing/TESTING_AND_ACCEPTANCE.md

# Testing & Acceptance

> 实施回归的不可回退功能清单见 `REGRESSION_AND_CHANGE_GUARD.md`。每次跨模块改动均应先过该清单，再执行本文件的专项验收。

## 1. 测试原则

本项目最危险的问题不是页面 Bug，而是：

- AI 误提取；
- 资格误判；
- Evidence 丢失；
- Job 重启丢失；
- POI 错认；
- 模型版本变化导致行为漂移。

因此测试必须覆盖 Pipeline 与业务规则。

---

# 2. Test Layers

## Unit
- Rule Engine
- Requirement DSL
- MajorMatcher
- Information Gain
- Preference scoring
- Job state transition
- Capture Input Normalizer

## Fixture
- HTML Resolver
- WeChat Snapshot
- Excel
- PDF
- DOCX
- scanned PDF / image OCR
- Transcript
- POI candidates
- share text with embedded URL

## Integration
- Capture → Job
- raw paste → selected URL → Source locator
- Recruitment End-to-End
- Travel End-to-End
- External LLM fallback
- Worker recovery

## UI
- Dashboard
- Control Center
- Evidence drill-down

## Capture Input Normalizer

至少覆盖：

1. 前后空白的纯 URL → `URL_ONLY`；
2. 标题 + 换行 + Bilibili URL + “复制打开” → `SHARE_TEXT_WITH_URL`，后续 payload 只有 URL；
3. Markdown `[标题](URL)` 与 `<URL>`；
4. URL 后的 `。`、`，`、`)`、`】`、引号被正确剥离，query/fragment 保留；
5. 相同 URL 或 canonical 后相同的短链去重；
6. 多个候选但只有一个命中专用 Resolver时自动选择；
7. 多个不同内容 URL → `CAPTURE_MULTIPLE_URLS`，不创建 Job、不访问网络；
8. 无 URL 普通文段 → `TEXT_ONLY`；
9. 分享标题不覆盖平台正式标题，不进入 LLM/Claim/Evidence；
10. 日志和数据库不保存被丢弃分享文案全文。

---

# 3. Requirement DSL Tests

至少覆盖：

- ALL
- ANY
- NOT
- nested ALL/ANY
- HARD
- SEMANTIC
- PREFERENCE
- UNKNOWN propagation
- REVIEW propagation

---

# 4. Rule Engine Acceptance

案例：

```text
ALL(PASS, PASS) → PASS
ALL(PASS, FAIL) → FAIL
ALL(PASS, UNKNOWN) → UNKNOWN
ALL(PASS, REVIEW) → REVIEW

ANY(FAIL, PASS) → PASS
ANY(FAIL, FAIL) → FAIL
ANY(FAIL, UNKNOWN) → UNKNOWN
ANY(FAIL, REVIEW) → REVIEW
```

---

# 5. MajorMatcher Tests

- exact code
- exact name
- category
- official mapping
- old/new mapping
- semantic similar → REVIEW
- unknown catalog → NEED_FETCH / REVIEW

禁止语义匹配自动 PASS。

---

# 6. Evidence Integrity

每个 `EXTRACTED` Claim：
- 至少 1 Evidence；
- Evidence Segment 存在；
- Segment 对应 Snapshot；
- Snapshot 对应 Source。

发现孤儿 Claim：
测试失败。

`NORMALIZED` / `COMPUTED` Claim 必须具有有效 Claim 血缘；冲突 Claim 必须同时保留，不能靠最后写入覆盖。

---

# 7. Recruitment E2E

Fixture 包含：
- 公众号快照
- 政府公告
- Excel 岗位表

验收：
- 自动下钻；
- 解析时间；
- 解析岗位；
- 生成 DSL；
- Profile 匹配；
- Deadline；
- Evidence 可回溯。

---

# 8. Travel E2E

Fixture：
- 本地 Transcript
- Bilibili metadata/subtitle/无字幕响应
- DeepSeek 分块与合并响应
- 视频帧、黑帧、模糊帧和重复帧 Fixture
- 地点候选
- Mock POI Provider
- 中国大陆 bbox/zoom/cluster 和 Marker 生命周期

验收：
- PlaceMention；
- POI；
- Dedup；
- Preference；
- Map ViewModel；
- Evidence timestamp。
- AI Note Version；
- Place Note Version；
- 视频笔记、列表和 Marker 进入同一 Place Detail。

视频专项验收：

1. BV、`b23.tv` 与 `?p=N` 均能 canonicalize；
2. 平台字幕命中时 `DOWNLOAD_AUDIO/ASR` 为 `SKIPPED`；
3. 无字幕时 yt-dlp + FFmpeg + ASR fallback；
4. 长 Transcript 分块失败后可从 checkpoint 恢复；
5. DeepSeek 429/5xx 有限重试，Key/余额错误不盲重试；
6. AI Note 成功、POI 歧义时为 `PARTIAL_SUCCESS`；
7. 每个地点事实引用 Transcript Segment，不只引用 AI Markdown；
8. 同一高德 POI 来自多个视频时只有一个 Marker；
9. 重跑复用 Transcript 并新增 Note Version；
10. BiliNote 移植文件保留 MIT 声明和参考 revision。
11. 每个主要地点 1–3 张、全文默认 3–12 张截图，均有时间码与来源绑定；
12. 黑帧、模糊帧和感知重复帧不会进入 Note；
13. 餐馆、景区、街区、步行街、商圈和市场可区分；
14. 转写同音/错别字名称经高德校正，raw/canonical 同时保留；
15. 首次地图加载无默认城市参数、标题或厦门 fallback；
16. 全国 bbox/zoom/cluster 和 viewport 恢复；
17. Marker 点击在地图浮窗查看简介并进入统一详情；
18. 用户 Marker 新增、软删除、恢复；
19. 自动 Marker 隐藏不删除 Source/Evidence；
20. 高德 JS Key、Security Code、Web 服务 Key 可配置并分别诊断。
21. 内容页写入并跳转 `AINote.id`；历史 `AINoteVersion.id` 链接仍能由共享 API 兼容解析，未知 ID 返回可见 404，不永久显示“正在读取视频笔记”。
22. `/api/status` 不响应时 SessionGate 在有界时间内进入可重试状态；服务恢复后无需重新配对即可进入目标页面。
23. Ollama 请求体包含 `keep_alive: 0`；成功、HTTP 失败、JSON 解析失败、备用模型与设置页真实测试后均释放本次模型，清理失败不覆盖原结果。
24. Bilibili 横屏与竖屏 Fixture 都能选择 video-only DASH 流；真实样本 `BV1JH826zEKC` 不再出现 `Requested format is not available`，并生成至少一张 `READY` 截图。
25. Whisper.cpp JSON offset `2800` 写入后仍为 `2800 ms`，不得变成 `28000 ms`；末段时间显著超过视频时长时，Note 与截图步骤不得继续物化。
26. 样本 `note_221cd61e9600493cb3f32e062e1ad013` 的 10 倍历史时间轴生成修正版 Transcript Version，页面时长、章节时间码、导出时间码和截图定位一致。
27. 任意非空 Transcript 均同时得到摘要和至少一个“按时间线详述”章节；章节按时间递增并覆盖末个 Segment。模型返回全部无效 `segment_ids` 时使用服务端分块引用和转写整理兜底，不得得到 0 章节。
28. 无 Note Section 时截图计划仍从有效 Transcript 生成 3–6 个候选；`plans == 0` 不下载视频、不把截图步骤记为成功，并显示稳定错误原因。
29. “导出完整转写（TXT）”包含所有 Segment、完整时间范围和来源元数据，不只包含页面前 8 段；响应为附件且服务端不产生持久导出文件。
30. Transcript 创建后第 179 天仍可读取/导出，第 180 天清理任务幂等清空正文、Segment 文本、Evidence quote 和全文 fingerprint；Note/时间线/截图仍可读，Transcript/导出返回 410，审计日志不包含原文。
31. 全部 Segment 生成 corrected_text，Segment ID、顺序和时间范围不变；缺段/新增 ID/乱序的模型输出被拒绝。
32. 口音、同音字、断句、重复词和专有名词校对符合人工答案；不确定地名进入 Review，不编造事实。
33. 默认 Transcript 预览、Note 和 TXT 导出使用 corrected_text；raw_text 只从审计入口读取。
34. Hero 后进入摘要/目录/正文；地点候选与完整转写在文章最底部，PC 双列、Mobile 纵向，无横向溢出。
35. 地点、Transcript Segment、目录和截图时间码均跳转正确 Section，更新锚点、聚焦并短暂高亮；前进/后退恢复。
36. 目录每项具有具体 heading 与 20–50 字 thesis，不出现“本段继续介绍”等泛化套话。
37. “按时间线详述”由 summary/bullets/place refs 组成，不连续铺原始转录句子，并覆盖完整校对稿。
38. READY 截图以 220–280px 缩略图放在对应 Section 文字侧面；仅章节起始 talking head、片头、转场不作为关键帧。
39. 截图 caption 说明实际关键内容，不统一显示“章节起始时间码代表帧”。
40. 点击截图打开 contain 灯箱，上一张/下一张、Escape、遮罩和关闭按钮均可用，关闭后焦点恢复。
41. “导出 TXT”使用统一次级按钮视觉，默认导出 corrected 版本；raw 导出只在审计区域。
42. VideoAsset.cover_url 的 HTTP/协议相对 URL 规范为 HTTPS，只有允许的 Bilibili 图片 CDN host 可下载。
43. JPEG/PNG/WebP/AVIF 封面按状态、MIME、文件头、尺寸和最大字节验证，HTML/SVG/损坏响应被拒绝。
44. 原始封面按 SHA-256 去重并生成 672×378 WebP；同一 VideoAsset 多 Note Version 不重复下载。
45. Video Note List 使用本地 cover_image_url、16:9 object-fit cover 和时长徽标；失败时布局稳定显示占位。
46. 列表顶部主按钮文案为“添加视频链接”，PC 40px/14px，Mobile 不放大且符合全局 Primary Button 状态。
47. C 步骤 ERROR 且 A/B Artifact 有效时，续跑只执行 C 及下游；A/B 记录 REUSED 且不产生新外部调用。
48. Replay Cache 24 小时内可用并显示剩余时间；到期后返回 `REPLAY_ARTIFACT_EXPIRED`，只能完整重跑。
49. 输入/模型/Prompt 改变时，服务端从最早失效步骤续跑；前端不能任意指定 from_step。
50. 任务详情和日志显示“从错误步骤继续”、复用/重跑步骤；旧“重跑所属任务”不再代表整 Job 重跑。
51. 视频笔记列表/详情删除共用同一 API；删除 Note 后 Source、VideoAsset、CoverAsset、Transcript、Place 和 Evidence 仍存在。
52. 活跃生成 Job 阻止删除；确认框展示标题、保留边界和不可恢复。
53. Hero 缺封面时区域为空/收起，不显示场记板占位；地点候选和完整转写位于文章最底部。
54. 目录符合主体暖白/朱砂/衬线/细分隔线语言；截图以 220–280px 缩略图侧排并可打开 contain Lightbox。

55. 单 Worker 运行超过 `worker_heartbeat_seconds * 3` 的模型批次时，`/api/status.services.worker` 仍为 `RUNNING` 且进程心跳持续推进；该 Job 的停滞只依据自身活动时间。
56. `CORRECT_TRANSCRIPT` 进入多批模型请求后取消：当前受控 HTTP 请求结束后不再发起下一批，写入 `job.cancel.observed` 并释放 lease。
57. 429/5xx/超时不会通过递归二分放大同一批外部请求；仅 payload/结构问题允许缩小批次，batch 开始/结束均写入非敏感进度事件。
58. 运行或排队中的 Job 点击右上角“从头重新运行”：旧 Job 进入协作式取消，新 Job 立即创建为 `QUEUED`，响应返回新旧 Job ID，前端导航到新 Job。
59. LaunchAgent 部署在外置卷时，`manage.py status` 必须验证 `/health`、首页正文非空和 75 秒内 Worker 心跳；`launchctl running` 不能单独判定健康。
60. Worker 启动时无法冷导入视频 Pipeline 则不领取 Job；处理中的未捕获异常立即返回 `FAILED/WORKER_UNHANDLED_EXCEPTION`、释放 lease 并写审计。
61. 步骤恢复卡仅在 Replay Options 可用时显示续跑按钮；不可续跑时仅提示原因，不重复显示完整重跑按钮。
62. 通用设置默认返回 `ai_retry_count=2 / ai_retry_wait_seconds=5 / ai_request_interval_seconds=1`，保存后下一次 Pipeline AI 调用生效。
63. 429/408/409/425、超时、连接失败、可恢复 5xx 与空响应按设置有限重试；每次调用前执行配置间隔，重试事件记录 attempt、limit、wait 和脱敏原因。
64. LLM 步骤在 600 秒内不显示“可能停滞”；900 秒真实 Attempt 终止阈值保持独立。
65. `GET /api/settings/prompt-supplements` 默认返回三项空补充、只读核心规则摘要与 1000 字符上限；保存语气/篇幅偏好后可读回。
66. PUT 包含“忽略系统规则”“修改 JSON/字段/ID/顺序”等越权语言返回 422，且原设置不变。
67. 补充文本会作为低优先级 System Message 插入三个对应 LLM 阶段；固定 Prompt、JSON 解析和 Segment ID 校验仍保持生效。
68. 失败 Job 在某个补充 Prompt 哈希改变后，Replay Options 返回最早受影响的 AI 步骤，不允许从更晚步骤绕过重算。
69. 生产 LaunchAgent 的 `program` 均指向 `/Volumes/D/Library/Application Support/Zhijian/venv/bin/python`，解释器为 Python `3.14.6`；切换后 `/health`、首页正文、Worker 心跳、Keychain 可用性和外置卷 deny 日志均符合部署手册要求。

---

# 9. Job Recovery

场景：
1. 创建 RUNNING Job；
2. 模拟 Worker 异常停止；
3. heartbeat 超时；
4. Job 回 QUEUED；
5. 新 Worker 接管。

验收：不丢任务、不重复写最终结果。

运行日志手动重跑专项验收：

1. 点击普通 INFO/WARNING 或无 Job 关联事件，只打开详情，不显示重跑按钮；
2. 点击 `ERROR/CRITICAL + entity_type=job` 事件，抽屉显示所属任务当前状态、步骤和重试次数；
3. `FAILED / PARTIAL_SUCCESS / NEEDS_USER` 与 lease 已释放的 `CANCELLED` 可确认重跑；`QUEUED / RUNNING / COMPLETED`、取消未释放、已删除 Job 均不可误触发；
4. 确认前没有请求；连续双击只产生一次重入队，第二次由 pending 禁用或服务端 409 拒绝；
5. 请求携带 `source_event_id`，服务端拒绝非 ERROR/CRITICAL、归属不匹配或不存在的事件；
6. 成功后 Job 为 `QUEUED`、`retry_count + 1`，产生包含来源事件 ID 的 `job.retry.queued`，日志页保持同一 Job 筛选并可进入重跑进度；
7. Worker 按 Pipeline 定义顺序执行，前端不需要逐步点击；输入哈希一致的缓存是否复用由 Pipeline 决定；
8. 新 attempt 再次失败时生成新 ERROR 事件，旧事件仍保留；敏感正文、Cookie、Key 不进入确认框或审计 detail。

---

# 10. Replay

Recruitment：
从 `BUILD_REQUIREMENTS` 重跑，不重新抓 Source。

Travel：
从 `EXTRACT_PLACES` 重跑，不重新 ASR。

---

# 11. External LLM

Mock：
- Local validation fail twice；
- Local First 策略；
- External Provider 被调用；
- 记录 provider/model；
- 仍执行 Evidence Validator。

---

# 12. PC Hardware Acceptance

安装诊断：

- Python
- SQLite
- ffmpeg
- Playwright browser
- Ollama
- Apple Silicon / Metal runtime detected
- whisper.cpp
- model availability
- disk writable
- Node.js 20.19+ 或 22.12+
- LAN mobile access / token auth
- AMap API / map render
- DeepSeek / Xiaomi MiMo connection

CMS 显示诊断结果。

---

# 13. MVP Acceptance Definition

系统达到 MVP，需要至少满足：

1. 用户可以粘贴招聘链接；
2. 后台可见 Job；
3. 能解析至少一种真实招聘公告 + Excel；
4. 能形成岗位资格结果；
5. Evidence 可点击回溯；
6. 用户补 Profile 后自动重算；
7. 用户可粘贴 Bilibili 链接；
8. 能得到字幕或 ASR；
9. 能提取并确认地点；
10. 地点可出现在地图 ViewModel；
11. 可 SAVE / DISMISS / VISITED；
12. PC 重启任务可恢复；
13. 外部模型 API Key 可配置且可测试；
14. 所有核心长任务可从 CMS 重试。
15. 手机可在同一局域网安全访问，未授权请求无法读取业务或管理数据；
16. DOCX、扫描 PDF 与图片公告可归一化并保留 Evidence 定位；
17. 高德 POI/地图可用，GCJ-02 在存储与导出中明确标注；
18. DeepSeek、Xiaomi MiMo 可通过兼容 Provider 配置和测试；
19. `testing/GOLDEN_SAMPLES.md` 的安全与正确性门槛全部通过。
20. Bilibili 视频可生成完整、带时间码和版本记录的 AI 笔记；
21. 地点可生成跨来源归纳笔记，视频笔记、列表和地图 Marker 均进入同一地点详情；
22. 已配置 DeepSeek Provider 可完成长字幕分块总结，外部调用可审计且 API Key 不进入日志。
23. 视频笔记包含与章节/地点时间码绑定的代表性截图；
24. 餐馆、景区、街区等细粒度地点具有特色简介并通过高德校名；
25. 地图以中国大陆全境为首次视野，不使用默认城市，支持 bbox、zoom、cluster 和视野恢复；
26. Marker 浮窗、用户新增、隐藏、软删除和恢复均可用，且不破坏 Place/Evidence；
27. 设置页可填写并测试高德 JS Key、Security Code 和 Web 服务 Key。
28. 粘贴标题/分享话术与唯一链接时只处理该 URL；多个不同内容链接返回候选且不静默选择。
29. 视频笔记阅读体验符合 `video/VIDEO_NOTE_READING_EXPERIENCE_V042_SPEC.md`：顶部证据区、AI 校对稿、主旨目录、段落跳转、随文截图与灯箱全部通过。
30. 视频笔记列表符合 `video/VIDEO_NOTE_LIST_V043_SPEC.md`：按钮文案/尺寸和真实本地封面全部通过。
31. 步骤级续跑符合 `jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md`；中间产物有效时不重跑上游，过期后只允许完整重跑。
32. 视频笔记删除符合 `video/VIDEO_NOTE_DELETE_V044_SPEC.md`，共享数据和证据不受影响。

---

# 14. PC 运维 UI v0.3 验收

下一实施阶段必须执行 `operations/OPERATIONS_UI_SPEC.md` 第 8 节的全部验收，至少覆盖：935×886 有效视口和 125%/150%/200% 缩放下无重叠；当前步骤、子状态、计时与最后活动 3 秒内更新；Worker 心跳延迟/疑似停滞阈值；时间线按 Pipeline 顺序；日志组合筛选、游标分页、详情深链和脱敏导出；侧栏 CPU/内存/数据盘/Worker 心跳与真实状态接口一致；键盘全流程与不依赖颜色的状态表达。

该验收组的代码实现已完成：任务详情采用 WebSocket/轮询回退，日志页支持组合筛选、游标分页、详情抽屉与脱敏导出，侧栏读取持久化运行指标。自动回归见 `REGRESSION_AND_CHANGE_GUARD.md`；原生 PC/手机浏览器缩放点击回归需在具备 Computer Use 或 Browser 控制器的会话补录，不能以设计稿代替。


---

# FILE: operations/LOGGING.md

# 日志：契约与维护

> 2026-09-03 合并 LOGGING_ARCHITECTURE.md 与 LOGGING_IMPLEMENTATION.md，消除重复说明与过期“待实施”标签。当前完成度只见 [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)，本次未重新运行日志或服务验收。

## 1. 边界与存储

日志回答服务健康、任务结果与用户操作审计三个问题。Mac mini 单节点不引入 Elasticsearch、Loki 或云遥测。JSONL 用于排障，SQLite system_events 用于长期可读审计，不能互相替代。

| 层 | 存储 / 查询 | 约束 |
| --- | --- | --- |
| API / Worker 运行日志 | data/logs/api.jsonl、worker.jsonl | 每行 JSON；单文件 10 MiB，5 个轮换；页面不直接暴露原文件 |
| 审计事件 | SQLite system_events；GET /api/logs | 局域网 Session 保护；本机豁免取决于部署设置 |
| 兜底日志 | data/logs/ 下 API/Worker 的 stdout.log、stderr.log | 日志子系统失效时排查，不作为业务状态证明 |

JSONL 包含 timestamp、level、component、message，可选 request_id、event_type、duration_ms、status_code、path、job_id、脱敏异常。审计事件包含 ID、时间、级别、组件、类型、消息、Actor、实体类型/ID、Request ID 与非敏感 detail。data/ 不进入 Git。

## 2. 事件与事务

API 生成或接受 X-Request-ID 并在响应头返回；业务动作关联 system_events，Job 事件同时带 Job ID。自动化根据 event_type 判断，不解析人类消息文本。

| 级别 | 含义 |
| --- | --- |
| INFO | 正常状态变更，如配对、设置、任务完成 |
| WARNING | 可恢复但需关注，如来源待确认、运行时降级 |
| ERROR / CRITICAL | 处理或运行失败，关联 Job/Step 便于恢复 |

事件类型采用领域.对象.动作，如 auth.session.created、job.failed、profile.updated。业务使用 services/audit.py 的 record_event；同一事务尚有其他写入时使用 commit=False，防止提前提交部分状态。运行日志失败不阻塞主业务；审计失败应回滚相应业务事务并在 stderr 留痕。

## 3. 安全、保留与备份

- 不记录配对码、Session Cookie、API Key、正文、文件内容、完整个人档案；Secret 仅进 Keychain/Secret Store。URL 保留在 Source 域，HTTP 日志只记路径，不记查询串/请求体。
- Provider 日志只含 Provider、模型及脱敏摘要；页面与导出共用脱敏层。
- JSONL 按大小轮换；审计保留期产品默认设计为 90 天，不能据此假定定时清理已上线，核对 app:general.data_retention_days 与实现。
- 备份 SQLite 要有 WAL/SHM 的一致性快照及永久文件；可再生 JSONL 无强制备份要求。不得为日志升级直接执行删除审计表的历史 downgrade。

## 4. 查询与工作台

既有实施记录包含健康摘要、组合筛选、Job/Request 深链、游标分页、实时跟随暂停、结构化详情与单条脱敏导出。时间范围支持快捷项和自定义，服务端支持 from/to、cursor、asc/desc。UI 契约按需读 [operations/OPERATIONS_UI_SPEC.md](operations/OPERATIONS_UI_SPEC.md) 第 5 节，精确参数以 API schema 为准。

只读示例：GET /api/logs?level=ERROR&component=worker&query=Whisper&limit=20。先限定 Job、时间和数量，不导出全部日志。批量 CSV/JSONL、筛选链接复制、低水位告警和完整性哈希不因本次合并而列为已实现。

## 5. 错误事件与 Replay

日志页是操作入口，不拥有 Job 状态机。ERROR/CRITICAL 事件关联仍存在的 Job 与失败 Step 时，先查 GET /api/jobs/{job_id}/replay-options；服务端检查 lease、source_event_id、失败步骤与上游 Artifact 的输入/版本和有效期。

1. Artifact 有效：显示“从错误步骤继续”，确认框展示复用上游、重跑步骤、剩余保留时间；调用 POST /api/jobs/{job_id}/retry-from-step，提交受后端约束的 step_name/source_event_id。
2. 上游标为 REUSED，下游旧输出 INVALIDATED；新尝试失败保留旧事件与 Attempt；跟随 job.step_replay.* 事件。
3. 过期显示“中间产物已清理”，禁用步骤续跑；“完整重跑”是独立按钮/API。409 展示 REPLAY_ARTIFACT_EXPIRED、INPUT_CHANGED、LEASE_ACTIVE 等原因。
4. 页面不能直接改 JobStep、调用 Processor 或选择任意 from_step；新事件保存非敏感 step/error_code/attempt。

完整约束只维护在 [jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md](jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md)，本节仅说明日志如何接入。

## 6. 代码定位与验证

| 位置（仓库根相对路径） | 职责 |
| --- | --- |
| backend/src/zhijian/core/logging.py | Formatter 与轮换 |
| backend/src/zhijian/main.py | 请求关联、状态码与耗时 |
| backend/src/zhijian/services/audit.py | 审计记录与事务边界 |
| backend/src/zhijian/db/models.py、backend/alembic/versions/0002_system_events.py | 审计模型与历史迁移，不改已发布迁移 |

验证 Request ID、事件/JSONL、Job 关联、筛选/分页、脱敏和 Replay 门禁。生产升级只按 [部署说明](../deploy/macos/README.md) 执行；迁移前备份并确认无活跃 Job/lease，不以测试为由停止 Worker 或触发真实任务。原 v0.2/v0.3 文本可从 Git 历史追溯，旧验收结论不代表当前现场。


---

# FILE: architecture/ARCHITECTURE_DECISIONS.md

# Architecture Decisions

## ADR-001：第一版取消云端
**Decision**
全部核心数据与计算运行在用户 PC。

**Reason**
- 单用户；
- 可接受 PC 关机时暂不处理；
- 用户明确希望先走通链路；
- 降低云部署与成本复杂度。

**Future**
可演化为 Cloud Control Plane + Home Worker。

---

## ADR-002：后端使用 FastAPI，不使用 Flask
**Decision**
FastAPI。

**Reason**
- Pydantic/Schema；
- WebSocket；
- ASGI；
- OpenAPI；
- 更适合当前 Typed Pipeline。

---

## ADR-003：FastAPI 不承担长任务
**Decision**
独立 Worker + SQLite Job Queue。

**Reason**
- ASR/视频/LLM 长任务；
- PC 重启恢复；
- CMS 可视化状态；
- 不引入 Redis/Celery。

---

## ADR-004：SQLite
**Decision**
MVP 使用 SQLite + WAL。

**Reason**
- 单机；
- 数据规模小；
- 部署简单；
- 可满足关系模型与全文检索基础需求。

---

## ADR-005：产品只做两个场景
**Decision**
Recruitment + TravelFood。

**Reason**
- 真实高频需求；
- 避免应用成为杂乱收藏箱。

**Future**
Processor Router 保留扩展。

---

## ADR-006：Unknown 不自动归类
**Decision**
第一版 Unknown → Unsupported。

**Reason**
- 保持产品干净；
- 不让 AI 擅自创建分类；
- 后续 GenericProcessor 再接入。

---

## ADR-007：Evidence First
**Decision**
事实 Claim 必须证据化。

**Reason**
- 招聘是高风险判断；
- 用户明确禁止 AI 随意发挥；
- 未来 GenericProcessor 同样需要可信度。

---

## ADR-008：Requirement DSL
**Decision**
招聘条件必须转 AST，不让 LLM 每次重新理解。

**Reason**
- 可测试；
- 可重放；
- 可审计；
- 逻辑嵌套。

---

## ADR-009：专业语义只 REVIEW
**Decision**
Semantic Major Match 不自动 PASS。

**Reason**
招聘单位认定可能与 AI 语义不同。

---

## ADR-010：Eligibility 与 Preference 分离
**Decision**
资格、偏好、紧急程度分别建模。

**Reason**
避免“匹配度 92%”混合多重含义。

---

## ADR-011：PlaceMention 与 Place 分离
**Decision**
视频提及与现实 POI 两层。

**Reason**
- 多来源去重；
- POI 解析可审核；
- 坐标可信。

---

## ADR-012：本地优先 + 外部 LLM 口子
**Decision**
LLMProvider 抽象，默认 LOCAL_FIRST。

**Reason**
- 利用 Mac mini 的本地 Metal 运行时；
- 可离线；
- 外部强模型用于增强；
- 不锁厂商。

---

## ADR-013：ASR 抽象
**Decision**
ASRProvider，Mac mini 首选 whisper.cpp Metal 路线。

**Reason**
避免锁 CUDA/faster-whisper。

---

## ADR-014：Control Center 是 MVP
**Decision**
后台控制台不是后置。

**Reason**
用户明确需要看见系统处理过程并管理配置。

---

## ADR-015：Pipeline Replay
**Decision**
步骤结果持久化，可单步重跑。

**Reason**
模型升级、解析纠错、节省视频/网页重复抓取。

---

## ADR-016：Partial Materialization
**Decision**
长任务允许部分结果提前展示。

**Reason**
提升 43 地点/数百岗位等任务 UX。

---

## ADR-017：Narrow Product, Extensible Core
**Decision**
UI 窄，接口宽。

**Reason**
兼顾第一版速度与长期 GenericProcessor 演进。

---

## ADR-018：MVP 支持可信局域网手机访问
**Decision**
PC 仍是唯一数据与计算节点；手机通过同一可信局域网访问响应式 Web。REST/WebSocket/Admin API 必须验证本机生成的访问 Token，不自动暴露公网。

**Reason**
- 手机是“随手分享/查看结果”的必要入口；
- 不为此提前引入云端与多用户体系；
- LAN 已扩大攻击面，认证不能后置。

---

## ADR-019：招聘文档矩阵包含 DOCX 与 OCR
**Decision**
MVP 支持 PDF、扫描 PDF、DOCX、XLS/XLSX、PNG/JPEG；OCR 结果保存页码、边界框和置信度，低置信关键事实进入 Review。

**Reason**
北京市公务员/事业单位公告附件并不只使用文本型 PDF/Excel，缺少 DOCX/OCR 会造成真实链路断裂。

---

## ADR-020：中国 POI 首选高德并显式使用 GCJ-02
**Decision**
MVP 实现 AMapPOIProvider 和高德地图 JS API 2.0。中国大陆高德坐标存储为 `GCJ02`，导出必须标注坐标系。

**Reason**
- 第一版旅行范围为中国；
- 高德同时提供 POI 搜索与 PC/移动 Web 地图；
- 显式坐标系避免地图显示与 GeoJSON 语义错误。

---

## ADR-021：外部模型通过兼容 Provider 接入且敏感档案默认不外发
**Decision**
DeepSeek、Xiaomi MiMo 等通过 OpenAICompatibleProvider 配置；模型名不写死。`SENSITIVE` Profile 默认不外发，`LOCAL_ONLY` 永不外发。

**Reason**
- Provider 与模型会持续变化；
- 招聘 Profile 涉及学历、工作经历、政治面貌和户籍；
- 最小化外发符合 Local First。

---

## ADR-022：真实 URL 手工验收，冻结 Fixture 用于 CI
**Decision**
微信/Bilibili 真实链接用于手工验收；CI 使用脱敏冻结 Fixture，不依赖实时平台网络。

**Reason**
- 平台存在登录态、验证码、风控、412 与内容变化；
- 实时网络依赖无法提供可复现测试；
- 不绕过平台访问限制。

---

## ADR-023：视频 AI 笔记参考 BiliNote，但由至简领域模型承接
**Decision**
Bilibili 视频链路优先适配 BiliNote 已验证的 URL/分 P 解析、平台字幕优先、yt-dlp 音频 fallback、Transcript、长文本分块与 Markdown 后处理轮子。BiliNote 代码只进入第三方适配层；任务运行使用至简持久 Worker，结果使用至简 Source/Snapshot/Segment/Claim/Evidence/Place/Note Version。MVP 默认以已配置 DeepSeek Provider 生成视频 AI 笔记和旅行结构化结果。

**Reason**
- 平台字幕、Cookie、风控和媒体下载存在大量已知边界，重复实现风险高；
- BiliNote 的单体 NoteGenerator、BackgroundTasks 和 JSON 状态文件不满足至简的恢复、审计与 Evidence 要求；
- AI 视频笔记和地点归纳笔记是产品一级产物，不能只把视频当地点抽取中间件；
- 适配层隔离便于跟踪上游修复并履行 MIT License。

完整契约见 `video/VIDEO_AI_NOTE_PIPELINE.md`。

---

## ADR-024：代表性截图、细粒度地点与中国全境地图
**Decision**
视频 AI 笔记必须生成与章节/地点时间码绑定的代表性截图；默认通过受限画质视频下载和 FFmpeg 确定性抽帧，不启用全视频多模态理解。旅行地点粒度扩展到餐馆、景区、街区、步行街、商圈、市场等，并由高德校正名称与 POI。地图以中国大陆全境为初始 viewport，按 bbox/zoom 加载和聚合，无默认城市；Marker 支持用户新增、隐藏、软删除和恢复，点击后先显示地图浮窗，再进入统一 Place Detail。

**Reason**
- 纯文字笔记难以快速建立视频场景记忆，代表帧能显著提升地点和菜品辨识；
- ASR 容易产生同音错字，真实地图 Provider 校名比 LLM 猜测可靠；
- 旅行内容跨中国多个城市，硬编码厦门会错误限制产品范围；
- Marker 是 Place 的地图投影，用户管理可见性不能破坏来源、Evidence 与跨来源聚合；
- JS 地图和 Web POI 使用不同 Key/安全边界，需要在设置中分别配置与诊断。

---

## ADR-025：粘贴分享文案先规范化为唯一链接
**Decision**
Capture 接受完整原始粘贴值，并在创建 Source/Job 前区分纯 URL、带标题/分享话术的唯一 URL、无链接正文和多 URL。唯一 URL 被选中后，只有 URL 进入 Resolver、Classifier 与 LLM；周围标题和分享文字被丢弃。多个不同内容 URL 无法唯一确定时返回 `CAPTURE_MULTIPLE_URLS`，不静默选第一个。

**Reason**
- 手机和内容平台复制出的通常是“标题 + 链接 + 复制打开”整段文案；
- 以 `startsWith("http")` 判断会把合法分享链接误当正文；
- 分享标题可能不准确或包含推广文字，不能覆盖来源正式元数据；
- 多链接静默取第一个可能处理错误内容并触发非预期网络访问；
- 只持久化选中 URL 和最小审计字段可以减少无关聊天/分享文字留存。

---

## ADR-026：运行日志通过 Job 服务触发步骤级续跑

**Decision**
`ERROR/CRITICAL` 审计事件规范关联 Job/Step 后，日志页查询 Replay Options。中间产物有效时，调用 Job 服务从失败步骤继续；上游完成步骤标记 REUSED，当前及下游顺次执行。中间产物过期后禁用步骤续跑，只允许完整重跑。日志模块不得写 JobStep、调用 Processor 或允许任意 from_step。

**Reason**
- 当前错误事件已经通过 `entity_type=job / entity_id` 建立可靠关联，现场 ERROR 事件均可定位所属 Job；
- 步骤中间产物默认保留 24 小时，可以可靠避免重复下载、ASR 和上游模型调用；
- 点击历史错误时任务可能已重新运行或完成，必须读取 Job 当前状态，不能按旧消息直接执行；
- 把来源事件 ID 写入 `job.step_replay.queued` 可形成“错误 → 用户确认 → 新 attempt → 当前/下游步骤”的审计链；
- Artifact、输入哈希、版本与 TTL 由 Job 服务统一判断，日志 UI 只展示可用动作；
- 完整重跑仍保留，但不能冒充步骤级恢复。

---

## ADR-027：视频笔记以 AI 校对稿和时间线主旨组织阅读

**Decision**
视频笔记详情在 Hero 后优先显示摘要、主旨目录和时间线正文，地点候选与完整转写放文章底部；Hero 使用真实 CoverAsset，缺省时为空/收起。Transcript 保留 raw/corrected 双版本，Note、目录、默认预览和 TXT 导出使用 AI corrected_text。目录由具体 heading/thesis 组成，所有时间码跳转稳定 Section 锚点。正文是按时间线组织的摘要、要点和地点引用；关键截图以侧排缩略图嵌入 Section 并提供 contain Lightbox。

**Reason**
- 地点和 Transcript 是回查工具，应在正文底部集中呈现而不打断阅读；
- 口音和 ASR 错字会污染摘要、地名和目录，必须先校对再总结；
- 原始转录堆叠不等于可读笔记，目录套话也无法帮助定位；
- 时间码若不能跳到段落，就失去阅读导航价值；
- 独立截图宫格割裂上下文，章节起始帧也未必是关键内容；
- raw Transcript 仍需保留以满足 Evidence 和校对审计。

---

## ADR-028：视频笔记列表使用本地持久封面资产

**Decision**
VideoAsset 元数据中的 Bilibili `pic/cover` URL 进入独立 `FETCH_COVER`：HTTPS/host/SSRF、状态、MIME、文件头、尺寸和字节校验后，按 SHA-256 保存原图并生成 672×378 WebP。列表只使用本地 Cover API，封面失败显示稳定占位但不阻塞 Note。顶部主操作文案统一为“添加视频链接”，复用全局 Primary Button。

**Reason**
- 长期远程热链受协议、Referer、CDN 变化和网络状态影响；
- 视频元数据已经提供原始封面，无需 LLM 或从视频帧猜测；
- 本地派生图便于缓存、离线浏览和统一 16:9 布局；
- 封面属于非核心增强，不应导致完整视频笔记失败；
- “投递”是系统术语，“添加视频链接”更符合用户动作；
- 参考项目已验证 `pic/cover → GET → Content-Type → 本地文件` 的可行性。

---

## ADR-029：删除视频笔记不删除共享来源与证据

**Decision**
列表和详情通过统一 Delete Service 删除 AINote、版本、Section、TOC 和 Content 投影；保留 Source、VideoAsset、CoverAsset、Transcript、Place、Claim/Evidence 和其他对象引用的 Screenshot。活跃生成 Job 阻止删除，第一版确认后不可恢复。

**Reason**
- 同一视频资产、转写和地点可被多个 Note/Place 复用；
- 删除阅读产物不应破坏来源审计和地图；
- 同步级联删除大文件风险高，孤立资产应由引用计数和保留策略清理；
- 列表与详情需要一致语义，不能各自维护删除边界。

---

## ADR-030：Worker 存活心跳、任务活动与取消确认分离

**Decision**
Worker 进程使用独立于同步 Job 执行循环的周期性心跳报告存活；Job 只在真实阶段、批次开始/结束或可观测外部调用边界更新自身活动时间。长模型步骤在每次批量请求前后检查取消状态，停止未开始批次，并在释放 lease 后才允许完整重跑。任务详情的完整重跑能力由服务端返回，不由前端按状态字符串硬编码。

**Reason**
- 单 Worker 被长模型请求占用时，外层领取循环不能刷新全局心跳，造成“Worker 延迟”的误报；
- 将全局心跳写入 Job 会掩盖真实任务无进度，因此两者不能复用；
- 转写校对会把 232 段拆为约 29 个模型批次，取消只在整步结束观察会继续消耗模型与占用 Worker；
- 已取消但 lease 未释放时必须防止并发完整重跑，释放后又不能因为 UI 漏掉 `CANCELLED` 而永久不可操作；
- 操作能力由服务端统一生成可消除任务详情、日志抽屉与未来客户端之间的状态分歧。


---

# FILE: testing/GOLDEN_SAMPLES.md

# Golden Samples & Feasibility Baseline

> 状态：Baseline v0.2
> 冻结日期：2026-08-13
> 用途：登记 MVP 首批真实样本、Fixture 获取规则、技术 Spike 与质量门槛。

---

# 1. 样本使用原则

1. 真实 URL 用于手工验收与定期兼容性检查，不作为 CI 的实时网络依赖。
2. 首次成功解析后，保存脱敏且许可范围内的 HTML、附件、字幕、POI 候选响应为 Fixture。
3. Fixture 必须记录获取时间、原始 URL、内容哈希、Resolver/Parser 版本；不得保存 Cookie、Token 或浏览器 Profile。
4. 微信、Bilibili 等来源若受登录态、验证码、风控或 412 限制，按 `HTTP → Playwright 持久 Profile → NEEDS_USER` 处理，不绕过平台限制。
5. 公众号正文中的官方公告和附件允许按 Source Graph 规则下钻；默认 `max_depth = 2`、单来源最多跟随 30 个链接。
6. 黄金样本内容可能随来源页面更新或失效；验收以冻结 Fixture 为可复现基准，以真实 URL 为补充手工验证。

---

# 2. Recruitment 黄金样本

首域：北京市公务员、事业单位招聘及相关考试公告。

## R-001

- 类型：微信公众号招聘汇总/入口文章
- URL：`https://mp.weixin.qq.com/s/_A_u11jr_FDA58sQ5QkBhg`
- 目标：验证微信 Resolver、正文解析、官方来源下钻、附件发现、Notice/Position/Requirement/Evidence 全链路。
- 当前网络特征：普通无状态 HTTP 无法稳定读取，必须验证 Playwright 持久登录态与 `NEEDS_USER` 路径。

## R-002

- 类型：微信公众号招聘汇总/入口文章
- URL：`https://mp.weixin.qq.com/s/HTw6_R4YICpLCFFl6PO4Yg`
- 目标：作为第二种页面结构与下钻关系样本，避免 Resolver 只适配单页。
- 当前网络特征：普通无状态 HTTP 无法稳定读取，测试策略同 R-001。

## 招聘 Fixture 最小集合

每个样本应尽量冻结：

- 微信正文 HTML；
- 下钻后的官方公告 HTML/PDF/DOCX；
- 岗位 XLS/XLSX；
- 扫描 PDF 或图片型公告（若来源存在）；
- Source Graph 期望结果；
- 关键日期、岗位数、字段映射、Requirement DSL 与 Evidence 的人工校验答案。

---

# 3. Travel/Food 黄金样本

## T-001

- 标题：厦门街头米其林小馆，连吃两家爽了…
- URL：`https://www.bilibili.com/video/BV189ui6LEhK`
- 类型：探店视频
- 目标：字幕优先、餐厅/菜品/价格/作者观点抽取、厦门 POI 解析、重复地点合并、时间码 Evidence。

## T-002

- 标题：不只是凉快，一口气逛遍贵州全省43个景区，TOP10你去过几个？｜全景推荐03
- URL：`https://www.bilibili.com/video/BV1qF3t6TENn`
- 类型：多地点旅行视频
- 目标：长视频字幕/ASR、43 地点批量抽取、Partial Materialization、高德 POI 候选、地图与 Review 队列。
- 当前网络特征：无状态抓取可能返回 412，必须覆盖浏览器/媒体解析 fallback 与 `NEEDS_USER`。

## 旅行 Fixture 最小集合

- 元数据与封面引用；
- 平台字幕（若有）或经授权生成的本地 Transcript；
- 时间码 Segment；
- 人工校验的 PlaceMention/Observation；
- 脱敏后的 Mock 高德 POI 候选响应；
- Confirmed/Review/Unresolved 期望状态。
- 餐馆、景区、街区等细粒度类型与 PlaceBrief 人工答案；
- raw_name、同音/错字候选与高德 canonical_name 期望结果；
- 合法的短小抽帧 Fixture，包含正常、黑帧、模糊和重复画面；
- 代表性截图期望时间码和淘汰原因；
- 至少覆盖中国东部、西部、南部和北部的 Mock Marker，用于全国 bbox/zoom/cluster；
- USER/AI Marker 新增、隐藏、软删除和恢复期望状态。
- 纯 URL、标题+URL+分享话术、Markdown 链接、末尾中文标点、多 URL 歧义的 Capture 输入 Fixture；
- 期望的 `input_kind / selected_url / discarded_text_length`，并验证丢弃文案不进入 Resolver/LLM。
- raw/corrected Transcript 对照，覆盖口音、同音地名、菜名、断句、重复词和不确定内容；
- 人工标注的主旨目录 `heading/thesis/start_ms/section_id`；
- 时间码 → Section 锚点期望映射；
- 每个 Section 的 summary、bullets、Place refs 与关键截图期望；
- talking head/片头/转场等不合格截图 Fixture；
- Lightbox、顶部地点/转写区和 corrected/raw TXT 导出的 UI 验收截图。
- Bilibili `pic/cover` URL、HTTP→HTTPS、JPEG/PNG/WebP/AVIF、HTML/损坏/超大响应 Fixture；
- 原图 SHA-256、672×378 WebP 衍生图和本地 Cover API 期望；
- 列表 16:9 封面、时长徽标、加载 skeleton、失败占位和“添加视频链接”按钮 PC/Mobile 验收截图。
- A/B 完成、C ERROR、Artifact 有效/过期/输入变化的 Replay Fixture，标注 REUSED/RETRYING/INVALIDATED 期望；
- 视频笔记删除前后对象引用 Fixture，验证共享 Source/Transcript/Place/Evidence 保留；
- Hero 有封面/缺省为空、底部地点与转写、主体语言目录、侧排缩略图与 Lightbox 的 PC/Mobile 标注图。

不把完整受版权保护的视频提交到 Git。测试仓库仅保存短小、必要、合法的派生 Fixture；本地媒体放入被忽略的数据目录。

---

# 4. Phase 0A 技术 Spike

正式业务实施前必须在目标 Mac mini 完成：

1. `LAN_ACCESS`：手机通过同一局域网访问前后端，验证 Token-to-Session、CORS、WebSocket 重连、Admin API 保护，并比较本地 HTTPS 与可信 LAN HTTP 的可部署性。
2. `WECHAT_RESOLVER`：R-001/R-002 至少一个可通过持久浏览器 Profile 获取正文并发现下钻链接；失败时能进入 `NEEDS_USER`。
3. `DOCUMENT_MATRIX`：验证 HTML、PDF、扫描 PDF、DOCX、XLS/XLSX、PNG/JPEG 的文本与定位信息。
4. `OCR`：中文 OCR 输出页码/边界框/置信度，低置信内容进入 Review，不直接生成高风险事实。
5. `LOCAL_LLM`：RX 7900 XT 上 Ollama 结构化输出、显存占用、吞吐与 JSON Schema 成功率。
6. `ASR`：whisper.cpp Vulkan 在 RX 7900 XT 上输出中文时间码 Transcript。
7. `EXTERNAL_LLM`：DeepSeek 与 Xiaomi MiMo 至少各完成一次 OpenAI-compatible 连接测试、结构化输出测试与审计记录测试。
8. `AMAP`：高德 Web 服务 POI 搜索、JS API 2.0 地图渲染、GCJ-02 坐标与配额错误路径。
9. `SQLITE_MULTI_PROCESS`：FastAPI + Worker 下 WAL、原子 Job Lease、崩溃恢复与幂等写入。

每项记录：环境版本、命令、输入、结果、耗时、资源占用、失败原因、是否阻塞后续 Phase。

---

# 5. 初始质量门槛

在黄金 Fixture 上：

- 关键报名/考试日期：人工标注项 100% 有正确值或明确进入 `UNKNOWN/REVIEW`，不得静默给出错误确定值；
- Eligibility：不得把人工标注的明确 `FAIL/REVIEW` 自动判为 `PASS`；
- Evidence：所有 `EXTRACTED` Claim 100% 可回到有效 Segment/Cell/Page/时间码；
- Excel 岗位行：不得静默丢行，无法可靠识别的行必须进入 Review 并报告计数；
- OCR：低于配置阈值的文字不得作为无需复核的关键日期或硬性资格依据；
- POI：只有高置信且候选唯一时自动 `CONFIRMED`；黄金样本中的误确认数必须为 0，其余进入 `REVIEW/UNRESOLVED`；
- Screenshot：黑帧、模糊帧和感知重复帧不得进入 Note；展示帧 100% 有实际时间码和来源关联；
- Map：首次加载无默认城市，全国 bbox/zoom/cluster 正确；Marker 生命周期不破坏 Place/Evidence；
- Job：崩溃恢复不丢任务，业务结果幂等，不重复生成最终实体；
- LAN：未携带有效 Token 的 API、WebSocket 和 Admin 请求全部拒绝。

吞吐、ASR 速度、LLM Schema 首次成功率等性能指标由 Phase 0A 在目标主机实测后补入，不凭空设定。

---

# 6. 尚待补充的样本

- 至少一份北京市官方 DOCX 招聘附件；
- 至少一份扫描 PDF 或图片公告；
- 至少一份结构复杂的 XLS/XLSX 岗位表；
- R-001/R-002 的人工期望答案与脱敏 Fixture；
- T-001/T-002 的人工地点清单与时间码答案。
