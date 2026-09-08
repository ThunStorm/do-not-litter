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
| 前端、UI、视觉、样式、布局、组件、Dropdown、Filter | [前端视觉设计系统](design/FRONTEND_VISUAL_DESIGN_SYSTEM.md) |
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
