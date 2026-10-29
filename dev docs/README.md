# 文档目录与维护规则

> 目录核对日期：2026-10-27。外部读者先看 [项目概览](../README.md)，开发 Agent 先看 [CODEX_CONTEXT.md](CODEX_CONTEXT.md)。本次同步文档清单、源码契约与历史归档，不重新授予业务验收。

## 1. 谁读什么，读到哪里停止

| 读者 / 问题 | 最短路径 | 停止条件 |
| --- | --- | --- |
| 外部了解项目 | 根 README → 有需要再选 PRODUCT_REQUIREMENTS 或 SYSTEM_ARCHITECTURE 的相关章 | 能说明用途、架构、支持范围与限制 |
| Codex 继续开发 | AGENTS → CODEX_CONTEXT → 当前状态 → 相关冻结行 → 一个专项分篇 | 能说明目标、现状、代码位置、约束与验收 |
| 存储 / 文件日志 | [数据目录与日志生命周期](operations/STORAGE_AND_LOG_LIFECYCLE.md)；原计划归入history/planning | 能确认生效根、维护门禁与独立验收边界 |
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
| design/ | 前端视觉设计契约；设计资源仍在仓库 design/ui/ |
| planning/ | 待办池、未来路线、[字幕一致性优化方案](planning/VIDEO_TRANSCRIPT_ALIGNMENT_OPTIMIZATION_PLAN.md)、[多平台链接 Adapter 调研计划](planning/SOCIAL_LINK_ADAPTER_FEASIBILITY_PLAN.md)；不自动授权实施 |
| history/ | 历史实施记录和已覆盖的旧计划；仅追溯时读取 |

| 领域 | 文档与职责 |
| --- | --- |
| 产品 / 架构 | [PRODUCT_REQUIREMENTS](product/PRODUCT_REQUIREMENTS.md) 用户场景与边界；[SYSTEM_ARCHITECTURE](architecture/SYSTEM_ARCHITECTURE.md) 模块关系；[ARCHITECTURE_DECISIONS](architecture/ARCHITECTURE_DECISIONS.md) 按 ADR 编号追溯原因 |
| 数据 / API / 安全 | [DATA_MODEL](architecture/DATA_MODEL.md) 按表定位；[API_DESIGN](architecture/API_DESIGN.md) 按路由定位；[SECURITY_PRIVACY](architecture/SECURITY_PRIVACY.md) 按安全边界定位 |
| 招聘 / 旅行 | [RECRUITMENT_PIPELINE](product/RECRUITMENT_PIPELINE.md) 提取/规则/资格；[TRAVEL_FOOD_PIPELINE](product/TRAVEL_FOOD_PIPELINE.md) 地点/POI/偏好 |
| POI匹配与搜索排查 | [归档排查与方案](history/planning/POI_RESOLUTION_DIAGNOSTIC_AND_OPTIMIZATION_PLAN.md)：跨片段证据、搜索一致性、景区父子候选与代表点；[代码复核报告](benchmark/POI_RESOLUTION_CODE_REVIEW_REPORT.md)，现状见旅行领域及实施状态 |
| 视频 Pipeline | [VIDEO_AI_NOTE_PIPELINE](video/VIDEO_AI_NOTE_PIPELINE.md) 五篇索引：范围、输入转写、生成物化、Job/API、视图与安全 |
| 视频代码定位 | [VIDEO_AI_NOTE_IMPLEMENTATION_GUIDE](video/VIDEO_AI_NOTE_IMPLEMENTATION_GUIDE.md) 短代码地图；旧 WP 已归档，不再要求完整读取八份文档 |
| 阅读 / 列表 / 删除 | [阅读体验](video/VIDEO_NOTE_READING_EXPERIENCE_V042_SPEC.md)、[列表封面](video/VIDEO_NOTE_LIST_V043_SPEC.md)、[笔记删除](video/VIDEO_NOTE_DELETE_V044_SPEC.md)，保持独立验收边界 |
| 渲染 / 任务模型摘要 | [VIDEO_NOTE_RENDERING_AND_TASK_MODEL_CONTEXT_SPEC](video/VIDEO_NOTE_RENDERING_AND_TASK_MODEL_CONTEXT_SPEC.md) |
| Job / Replay / 会话 | [步骤续跑](jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md)、[手机会话与任务控制](jobs/MOBILE_SESSION_DIAGNOSTICS_AND_JOB_CONTROL_SPEC.md) |
| 任务表达 / 时间 | [摘要与部分成功](jobs/TASK_SUMMARY_AND_PARTIAL_SUCCESS_SPEC.md)、[状态与北京时间](jobs/TASK_STATUS_AND_BEIJING_TIME_SPEC.md) |
| AI Gateway | [AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2](ai-gateway/AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md) 六篇索引：模型边界、公共能力、Pipeline/Provider、阶段参数、单任务策略、历史工作包/验收 |
| 标题时间证据 | [契约](video/TITLE_TEMPORAL_EVIDENCE.md)、[离线 A/B](benchmark/TITLE_TEMPORAL_PROMPT_AB_REPORT.md)、[归档计划](history/planning/ZHIJIAN_TITLE_TEMPORAL_EVIDENCE_AND_PROMPT_OPTIMIZATION_PLAN.md)；真实模型质量与缓存收益未验证 |
| 推荐时节与封面提取 | [待评审方案](planning/VIDEO_TEMPORAL_CONTEXT_AND_COVER_PLAN.md)：暑期主题继承、正文时间与跨句证据、地图一致性、按需OCR/视觉；不自动授权实施或历史更新 |
| 请求优化工作包 | [Z0–Z8/E2E 计划](history/planning/ZHIJIAN_AI_OPTIMIZATION_AND_E2E_PLAN.md)、[合成 A/B](benchmark/AI_REQUEST_OPTIMIZATION_AB_REPORT.md)、[本包发布门禁](benchmark/RELEASE_ACCEPTANCE.md)；真实 E2E 独立开放 |
| AI 运行 / 生产验收 | [AI_RUNTIME_AND_PROVIDERS](ai-gateway/AI_RUNTIME_AND_PROVIDERS.md) 运行配置；[AI_GATEWAY_PRODUCTION_ACCEPTANCE](ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md) 真实验收门禁 |
| 本机路由 Provider | [LocalAiMux 客户端接入](ai-gateway/LOCAL_ROUTER_PROVIDER_COMPATIBILITY_SPEC.md) 至简已实现的参数/消息协商与上游边界；[2026-10-06 参数及 55 型号调查](history/LOCALMUX_PARAMETER_SURVEY_20261006.md) 为有日期的证据快照，不代表真实模型验收 |
| 模型 / Prompt / 来源保留 | [模型与历史删除](ai-gateway/MODEL_AND_RETENTION_UI_SPEC.md)、[补充 Prompt](ai-gateway/PROMPT_SUPPLEMENTS_V045_SPEC.md)、[转写路由与来源保留](ai-gateway/AI_ROUTING_SOURCE_RETENTION_V046_SPEC.md) |
| 控制台 / 运维 | [CONTROL_CENTER](product/CONTROL_CENTER.md) 信息结构；[OPERATIONS_UI_SPEC](operations/OPERATIONS_UI_SPEC.md) 工作台交互；[LOGGING](operations/LOGGING.md) 日志契约与维护 |
| 运行监控 / Provider | [监控与预设](operations/RUNTIME_MONITOR_AND_MODEL_PRESETS_SPEC.md)、[内存口径与预设切换](operations/RUNTIME_MONITOR_AND_PROVIDER_SWITCH_V06_SPEC.md) |
| 部署 | [DEPLOYMENT_OPTIONS](operations/DEPLOYMENT_OPTIONS.md) 支持边界；[Mac mini 操作说明](../deploy/macos/README.md) 安装与维护 |
| 验证 / 样本 | [TESTING_AND_ACCEPTANCE](testing/TESTING_AND_ACCEPTANCE.md) 验证策略；[GOLDEN_SAMPLES](testing/GOLDEN_SAMPLES.md) 样本/Fixture；[视频 Fixture Golden](benchmark/video-workflow-golden-v1.json) 、[云南时节与路线回归](benchmark/YUNNAN_REGRESSION_ACCEPTANCE_20261028.md) 与 benchmark/ 仅验收任务按需查看 |
| 设计 / 授权 | [design/ui](../design/ui/README.md) → 目标版本/页面；[THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES.md) 授权记录 |
| 提示词 / 写交接 | [CODEX_TASK_TEMPLATES](CODEX_TASK_TEMPLATES.md) 三条短指令；交接固定更新 CURRENT_HANDOFF.md 的任务续接段，不另建文件 |
| 历史 / 未来 | [历史实施记录](history/IMPLEMENTATION_HISTORY.md)、[归档实施计划](history/planning/README.md)、[早期工程计划](history/PROJECT_PLAN.md)、[FUTURE_ROADMAP](planning/FUTURE_ROADMAP.md)；均非默认阅读 |

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
| 地图 V2 与后续地图执行计划 | 移入 history/planning/ 并保留原文 | 已由后续地图提交覆盖；实施状态只在 IMPLEMENTATION_STATUS，推荐/自动路线仍留 Future Roadmap |
| DATA_MODEL（903 行） / API_DESIGN（427 行） | 本次保留，按表/路由检索 | 数据模型大量为字段/空行；单一数据字典不为行数机械拆碎。未来某领域持续独立改动时再抽出该域 |
| 多份短 UI 规格 | 暂不合并成大 UI 文档 | 阅读/删除/Replay/时间具有独立风险与验收边界；目录统一导航即可 |
| CONTROL_CENTER / OPERATIONS_UI / RUNTIME_MONITOR 系列 | 保持分层 | 页面信息结构、工作台交互、指标语义不同；不要把架构、交互、运行时混成新合订本 |

### 地图 V2 草案的按需路由

原文：[地图 V2 计划](history/planning/PLACE_INTELLIGENCE_MAP_V2_IMPLEMENTATION_PLAN.md)。已归档；下表只保留追溯时的按需阅读边界。核心地图实现已获用户授权并进入源码，当前实现/验收以 IMPLEMENTATION_STATUS 为准；任何后续扩展仍须同时核对 §98–99 的 Review 修正、§106 原则和冻结约束。

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
- manifest.json 的 documents 列举现有 Markdown/JSON 文档及验收样本，generated_documents 单独列生成物；历史 repository_snapshot_date/commit 只说明当时冻结，documentation_inventory_date 表示本次清单核对日期。LocalAiMux 专项的跨仓链接依赖相邻 local-ai-mux checkout，远程单独克隆本仓时需同时取得该仓库；不把这些外部文档当成本仓的冻结正文。
- 文档交付检查链接、分篇正文完整性、生成可重复性和 git diff --check；可运行 .venv/bin/python scripts/test_build_complete_project_spec.py 检查生成物、来源清单与分篇链接重定位。不重启、不迁移、不调用真实 Provider、不跑业务全量。

## 6. Codex 设置说明

本次设置落在仓库 AGENTS.md，未更改用户全局配置、模型或推理档，也未设置会截断安全指令的硬 token 限制。按 [OpenAI 官方 AGENTS.md 文档](https://learn.chatgpt.com/docs/agent-configuration/agents-md)，仓库指令在运行开始时加载；建议在该仓库新建任务使用新规则。本轮未额外启动付费模型任务来测试加载。

2026-10-14 清理：已实施的 Z0–Z7 与标题时间证据计划归入 history/planning，未闭环的真实验收保留在当前状态/验收门禁；保留 ASR 与字幕对齐未完成计划及原有分篇索引。manifest 补齐当前专项、Benchmark 与历史文件；移除误跟踪的 Python 字节码，生成脚本仍保留。

2026-10-20 整理：地图修复与演进计划落入[当前计划](planning/MAP_EXPERIENCE_REPAIR_AND_EVOLUTION_PLAN.md)；旧生产快照归入[历史快照](history/PRODUCTION_SNAPSHOTS.md)，较早实施过程移入既有实施历史。主题索引保留，历史证据不删除，不把未来计划作为本轮自动授权。

2026-10-27 整理：两份已实施计划归入history/planning，稳定存储契约归入operations，地点态度归入旅行领域；保留未完成的地图F/社交平台/字幕计划。旧生产现场继续按原日期归档，export-evaluation-doc仅本地。
