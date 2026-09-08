# 当前实施状态

> 状态记录日期：2026-09-08。本文唯一记录当前源码能力与自动验证；生产状态只见 [CURRENT_HANDOFF.md](CURRENT_HANDOFF.md)。

## Current repository freeze

- 当前工作分支为 `codex/mac-mini-implementation`；提交前仍须用 git 状态核对，保护同批文档拆分与地图改动。
- 仓库 migration head 为 Alembic 0018；生产版本见 CURRENT_HANDOFF 的实际采样，不由仓库推断。
- 唯一支持的后端为 Mac mini；FastAPI、SQLite/WAL、独立 Worker；其他平台不在当前支持范围。
- 真实验收与自动回归分开记录；规格中的“待实施”、历史 Work Package、未来规划均不得单独认定为当前缺口。

## 当前能力

| 领域 | 已进入源码的能力 | 契约入口 |
| --- | --- | --- |
| Capture / 基础 | URL、正文、DOCX、PDF、XLSX、图像 OCR、音视频；局域网配对与 Session；Source/Evidence | product/PRODUCT_REQUIREMENTS.md、architecture/SECURITY_PRIVACY.md |
| 招聘 / 旅行 | 首批招聘结构化与证据；Place Insight（逐条 Segment 与 source quote）、POI Review、全国交互地图、Marker 生命周期、地点管理/人工路线；地点时间窗口提取并保留原文 Segment 证据，覆盖观赏期、丰枯水、渔业限制、花/红叶/雪/迁徙与季节性开放 | product/RECRUITMENT_PIPELINE.md、product/TRAVEL_FOOD_PIPELINE.md |
| 视频 | 字幕优先、ASR、校对、笔记/章节、地点、截图、列表封面、保留式删除 | video/VIDEO_AI_NOTE_PIPELINE.md（分篇索引） |
| Bilibili 登录恢复 | 站内扫码、nav 账号验证、Keychain 保存；登录失败进入 NEEDS_USER；核心恢复与非核心截图显式跳过；字幕多轨与官方 CDN Host Policy | video/02-input-transcript.md |
| Job / Replay | 独立 Worker 心跳、协作取消、租约门禁、终态表达、步骤续跑和完整重跑；后端决定 Replay Options | jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md |
| Gateway | 显式 Profile/Stage Policy、路由、Usage、转写质量门禁、Map/Reduce Facts、Cache、Budget、Domain Context、Vision Profile 边界 | ai-gateway/AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md（分篇索引） |
| 稳定性 | Gateway 按每次实际 Provider 尝试（含重试/fallback）执行预算与本地 OS flock；LOCAL/REMOTE 分账，Cache hit 不计真实模型尝试或预算 | ai-gateway/02-gateway-context.md、ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md |
| 产品 / 运维 | PC/手机 Web、真实状态快照、自定义模型/补充 Prompt、JSONL + SQLite 审计、运维工作台 | product/CONTROL_CENTER.md、operations/LOGGING.md |
| 部署 | Mac mini LaunchAgent 双服务、外置生产 venv Python 3.14、健康内容与 Worker 心跳门禁 | operations/DEPLOYMENT_OPTIONS.md、CURRENT_HANDOFF.md |

## 自动验证记录

2026-09-08：后端 pytest 105 项、目标 Ruff；Node 22.21.0 下前端 ESLint、Vitest 15 项、TypeScript 与 Vite build 通过。隔离 SQLite 已从空库升级至 0018，确认 `place_insight_items.source_quote` 存在；0017 的列存在性保护仍避免 0001 使用当前 ORM 元数据建表时的重复列错误。生产真实视频 Job 已完成字幕、笔记、地点提取与截图，因全部 POI 需要人工确认而为 `PARTIAL_SUCCESS`；真实 Provider/视频结论仅覆盖该样本，不能外推为全部 Provider 验收。

## 未闭环与外部条件

- 本轮视频工作包已按用户要求冻结：代码、Fixture 与离线验证保留，未部署、未迁移生产库、未重启服务；后续只在用户重新授权后继续。
- Gateway 真实 Local/Remote Provider、真实视频、fallback、cache/force-regenerate、预算、取消/Replay 与 Benchmark 仍需按 [生产验收门禁](ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md) 取证；本次未执行。
- 2026-09-08 已对本机 `qwen2.5:7b`、`qwen3:8b`、`qwen3.5:9b` 运行 Capability Probe：分类、结构化抽取、实体抽取与转写校对通过。其他 Stage 的 `FAIL` 只是该基础 Probe 未覆盖，不能视为模型能力否定；未更改默认模型或删除模型。
- Bilibili 扫码、nav 验证和 Keychain 保存已有真实验收记录；曾暴露 VIDEO_HOST_BLOCKED 的现场 Job 未自动重跑，不把修复等同于该 Job 成功。
- 高德、远程 Provider 等需要用户合法提供外部配置；不在文档保存 Secret，不通过编造状态代替配置/验收。
- Vision Profile 绑定边界已实现，不代表已自动运行视觉理解。视频 Fixture Golden（12 个冻结文本/POI 场景）、离线评分器与已有 Job/Replay 的只读采集器已就绪；真实模型比较与可选 Vision 尚未执行。视频 Insight 的更深层呈现/跨视频聚合增强仍须由用户从 planning/video 选择。地图 V2 的核心 Insight、Review、地图 Runtime、点选 POI 和编辑历史已落实；原实施计划已归档，推荐评分、自动行程与其他规划项仍不自动实施。

## 历史与维护

[实施历史](history/IMPLEMENTATION_HISTORY.md) 和 [归档实施计划](history/planning/README.md) 保留旧状态与计划追溯，默认不读。当前页只保留最新结论和未闭环项；完成项不持续追加长叙事。生产现场只更新 CURRENT_HANDOFF.md；冻结约束只更新 REGRESSION_AND_CHANGE_GUARD.md。新增证据必须写明日期、对象与验证层级。
