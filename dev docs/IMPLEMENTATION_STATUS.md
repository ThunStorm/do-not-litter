# 当前实施状态

> 状态记录日期：2026-10-09。本文唯一记录当前源码能力与自动验证；生产状态只见带原采样日期的 [CURRENT_HANDOFF.md](CURRENT_HANDOFF.md)。

## 当前冻结范围

- 当前分支为 `codex/mac-mini-implementation`；本轮远程交付包含已验证的本地路由、Token/取消响应及 `trust_env` 修复，不实施未来路线。
- 仓库 Alembic head 为 0025；生产版本由交接现场证明，不由仓库推断。本轮文档更新不迁移、不重启、不运行真实模型。
- 唯一支持的后端为 Mac mini，FastAPI、SQLite/WAL 与独立 Worker；单用户通过可信局域网访问。
- 源码实现、离线验证、生产加载与真实业务验收分别记录。规格中的待实施项、历史工作包和新草案不自动成为已授权任务。

## 当前能力

| 领域 | 已进入源码的能力 | 契约入口 |
| --- | --- | --- |
| Capture / 基础 | URL、正文、DOCX、PDF、XLSX、图像 OCR、音视频；局域网配对与 Session；Source/Evidence | product/PRODUCT_REQUIREMENTS.md、architecture/SECURITY_PRIVACY.md |
| 招聘 / 旅行 | 首批招聘结构化与证据；Place Insight、POI Review、全国交互地图、Marker 生命周期、地点管理/人工路线；POI Resolver Golden、事实归一化、跨来源共识/冲突、地点知识 API/证据跳转；月份/日期 Visit Window 状态、可重算 Preference Event 与确定性可解释推荐；Visual Fact 实验性截图任务、Vision Profile Skip 与离线 Golden | product/TRAVEL_FOOD_PIPELINE.md、ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md |
| 视频 | 字幕优先、ASR、校对、Semantic Map v3（ContentUnit、实体角色、关系、Atomic Claim）、同链接每次提交独立 Note/Content/Transcript Version、共享规范 Place、自适应笔记/章节、地点、Destination、截图、列表封面、保留式删除 | video/VIDEO_AI_NOTE_PIPELINE.md（分篇索引） |
| Bilibili 登录恢复 | 站内扫码、nav 账号验证、Keychain 保存；登录失败进入 NEEDS_USER；核心恢复与非核心截图显式跳过；字幕多轨与官方 CDN Host Policy | video/02-input-transcript.md |
| Job / Replay | 独立 Worker 心跳、协作取消、租约门禁、终态表达、步骤续跑和完整重跑；新任务冻结 AI 配置、重跑复用原配置；HTTP/间隔/资源锁等待协作取消，ASR 进程组回收与活动提示；Replay Options 由后端决定 | jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md |
| Gateway | 显式 Profile/Stage Policy、接口能力协商、LocalAiMux 接入与手动测试 FIFO；Map/Reduce、Cache、Budget、Domain Context、Vision 边界；凭据从 Secret Store 读取 | ai-gateway/AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md（分篇索引） |
| 稳定性 | 每次实际 Provider 尝试执行预算与本地 OS flock；LOCAL/REMOTE 分账，可信 Token、字符估算和未知分开，Cache hit 不重复计耗；超时不重复同模型请求 | ai-gateway/02-gateway-context.md、ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md |
| 产品 / 运维 | PC/手机 Web、真实状态快照、自定义模型/补充 Prompt、JSONL + SQLite 审计、运维工作台 | product/CONTROL_CENTER.md、operations/LOGGING.md |
| 部署 | Mac mini LaunchAgent 双服务、外置生产 venv Python 3.14、健康内容与 Worker 心跳门禁 | operations/DEPLOYMENT_OPTIONS.md、CURRENT_HANDOFF.md |

## 最新自动验证

2026-10-08 最终源码：生产 Python 3.14 `pytest backend/tests -q` 全量 279 项、完整源码与测试 Ruff、Node 24 前端 `pnpm verify` 的 19 项 Vitest/ESLint/TypeScript/Vite 均通过。`trust_env` 的本地路由成功与取消回归在修复前复现同一 TypeError，修复后与相关目标回归共 34 项通过；异步客户端构造参数与请求参数分离，保留绕过环境代理及普通连接默认行为。

本地路由已按实际接口能力处理消息/可选参数，手动测试 FIFO 不改变生产熔断，CLI 安全错误分流保持原预算；Token 读取区分可信实测、估算、未知，历史审计不回填。Job HTTP 等待、间隔与重试可协作取消；ASR 回收进程组，旧执行结果仍受 run fence 约束。上述功能在 2026-10-08 已分批受控加载，生产与 Browser 证据仅在交接和相关历史记录判定；此处的通过数量不替代真实模型验收。

2026-10-09 本轮为文档和远程交付：补齐文档清单、接口入口、当前状态及取消边界，迁移旧验证过程；仅检查链接、迁移完整性、合订生成与格式，不重复业务全量测试。

## 未闭环与外部条件

- **本地推理取消未闭环**：Ollama 请求含 `keep_alive: 0`，但客户端取消后没有显式模型停止/卸载；观察到 llama-server 继续生成。释放客户端等待和本地锁不证明推理停止；需独立修复及真实取消验收，不能由 `trust_env` 修复推导为已完成。
- 本地路由的单模型小样、目录能力及一次视频续跑不代表全型号/全阶段质量；厂商额度、思考 Token、远端取消/计费以及完整 Provider/fallback/cache/预算矩阵仍按 [生产验收门禁](ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md) 取证。
- 视频语义/POI 与 Visual Fact 已有离线 Golden，真实高德质量、Vision、代表性长视频、Token/延迟基线与性能毕业门禁仍未整体闭环。REVIEW/UNRESOLVED 保持人工处理，Fixture、构建和数据库版本不替代真实验收。
- 提交配置快照及同链接多 Note 身份已实现；真实双提交、模型切换和 Place 复用矩阵仍需独立验证。旧 Job 没有提交快照时，不补造当时设置或改写历史业务结果。
- Qwen3-ASR 运行资产及 Forced Aligner 已安装并有真实 smoke；默认仍为 Whisper。六类人工 Ground Truth、15–30 分钟 LONG_FORM、Replay 及 Benchmark Gate 未完成前不得晋级默认或改变生产 Registry。
- Bilibili 登录/nav/Keychain 与部分视频已有真实记录；受阻对象不自动重跑。高德和远程 Provider 必须使用合法配置；Secret 不进文档、SQLite 明文或日志。
- 已完成的 PC/390px 验收仅覆盖相应设置/任务控件，未验收的地图、Vision 或真实视频体验不自动外推；具体范围以带日期记录为准。

## 追溯与维护

旧验证数量、按日实施过程已原文迁入 [实施历史](history/IMPLEMENTATION_HISTORY.md#2026-10-09-当前状态页历史归档)。已覆盖计划在 [历史计划目录](history/planning/README.md)，未来候选仍在 planning/；专项只说明契约，不证明部署。生产现场更新既有交接，合订本由源文档生成，不直接编辑。
