# 当前实施状态

> 状态记录日期：2026-09-09。本文唯一记录当前源码能力与自动验证；生产状态只见 [CURRENT_HANDOFF.md](CURRENT_HANDOFF.md)。

## Current repository freeze

- 当前工作分支为 `codex/mac-mini-implementation`；提交前仍须用 git 状态核对，保护同批文档拆分与地图改动。
- 仓库 migration head 为 Alembic 0020；生产版本见 CURRENT_HANDOFF 的实际采样，不由仓库推断。
- 唯一支持的后端为 Mac mini；FastAPI、SQLite/WAL、独立 Worker；其他平台不在当前支持范围。
- 真实验收与自动回归分开记录；规格中的“待实施”、历史 Work Package、未来规划均不得单独认定为当前缺口。

## 当前能力

| 领域 | 已进入源码的能力 | 契约入口 |
| --- | --- | --- |
| Capture / 基础 | URL、正文、DOCX、PDF、XLSX、图像 OCR、音视频；局域网配对与 Session；Source/Evidence | product/PRODUCT_REQUIREMENTS.md、architecture/SECURITY_PRIVACY.md |
| 招聘 / 旅行 | 首批招聘结构化与证据；Place Insight、POI Review、全国交互地图、Marker 生命周期、地点管理/人工路线；POI Resolver Golden、事实归一化、跨来源共识/冲突、地点知识 API/证据跳转；月份/日期 Visit Window 状态、可重算 Preference Event 与确定性可解释推荐；Visual Fact 实验性截图任务、Vision Profile Skip 与离线 Golden | product/TRAVEL_FOOD_PIPELINE.md、planning/PLAN_B_PLACE_POI_KNOWLEDGE_QUALITY.md、planning/PLAN_C_TRAVEL_RECOMMENDATION_AND_VISION.md |
| 视频 | 字幕优先、ASR、校对、笔记/章节、地点、截图、列表封面、保留式删除 | video/VIDEO_AI_NOTE_PIPELINE.md（分篇索引） |
| Bilibili 登录恢复 | 站内扫码、nav 账号验证、Keychain 保存；登录失败进入 NEEDS_USER；核心恢复与非核心截图显式跳过；字幕多轨与官方 CDN Host Policy | video/02-input-transcript.md |
| Job / Replay | 独立 Worker 心跳、协作取消、租约门禁、终态表达、步骤续跑和完整重跑；后端决定 Replay Options | jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md |
| Gateway | 显式 Profile/Stage Policy、路由、Usage、转写质量门禁、Map/Reduce Facts、Cache、Budget、Domain Context、Vision Profile 边界 | ai-gateway/AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md（分篇索引） |
| 稳定性 | Gateway 按每次实际 Provider 尝试（含重试/fallback）执行预算与本地 OS flock；LOCAL/REMOTE 分账，Cache hit 不计真实模型尝试或预算 | ai-gateway/02-gateway-context.md、ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md |
| 产品 / 运维 | PC/手机 Web、真实状态快照、自定义模型/补充 Prompt、JSONL + SQLite 审计、运维工作台 | product/CONTROL_CENTER.md、operations/LOGGING.md |
| 部署 | Mac mini LaunchAgent 双服务、外置生产 venv Python 3.14、健康内容与 Worker 心跳门禁 | operations/DEPLOYMENT_OPTIONS.md、CURRENT_HANDOFF.md |

## 自动验证记录

2026-09-09：后端完整 `pytest backend/tests -q`、POI Resolver Golden、Plan C 目标测试、目标 Ruff 与 `git diff --check` 通过；Node 22.21.0 下前端 ESLint、Vitest 15 项、TypeScript 与 Vite build 通过。Plan C 在空 SQLite 成功升级至 0019：12 个月/日期状态、Preference Event、确定性推荐与 Visual Fact Golden 均为离线验证；无 Vision Profile 时截图 Job 以 `SKIPPED_UNSUPPORTED` 进入 `PARTIAL_SUCCESS`，不调用 Provider。桌面浏览器已检查地图 Toolbar 的月份、适宜度与推荐筛选；当前工具无法设为 390px，移动视觉验收未执行。以上不替代真实高德、Vision 或视频验收；实际生产采样见 CURRENT_HANDOFF。

## 未闭环与外部条件

- Plan C C1–C5 已进入源码：时间状态与推荐仅由可追溯事实/行为确定，Visual Fact 保持实验性并且不覆盖 Transcript；未进行真实高德、Vision 或视频验收，也未在本轮验证后重启加载新增源码。390px 视觉验收待具备可设定视口的 Browser/Playwright 时补做。
- Gateway 真实 Local/Remote Provider、真实视频、fallback、cache/force-regenerate、预算、取消/Replay 与 Benchmark 仍需按 [生产验收门禁](ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md) 取证；本次未执行。
- 2026-09-08 已对本机 `qwen2.5:7b`、`qwen3:8b`、`qwen3.5:9b` 运行 Capability Probe：分类、结构化抽取、实体抽取与转写校对通过。其他 Stage 的 `FAIL` 只是该基础 Probe 未覆盖，不能视为模型能力否定；未更改默认模型或删除模型。
- Bilibili 扫码、nav 验证和 Keychain 保存已有真实验收记录；曾暴露 VIDEO_HOST_BLOCKED 的现场 Job 未自动重跑，不把修复等同于该 Job 成功。
- 高德、远程 Provider 等需要用户合法提供外部配置；不在文档保存 Secret，不通过编造状态代替配置/验收。
- Vision Profile 绑定边界已实现，不代表已自动运行视觉理解。视频 Fixture Golden（18 个冻结文本/POI 场景）现覆盖访期、知识、POI 候选排名、错误 AI 字幕、时间轴异常、快速多地点、长转写尾部地点和非地点事实；Plan C Visual Fact Golden 覆盖菜单、店招、营业时间与路牌，并对严重幻觉设为 0 门禁。Harness 在缺少合法视频、远程 Key 或 Vision Profile 时标记 `BLOCKED_EXTERNAL`；真实模型比较与可选 Vision 尚未执行。已有 Job/Replay 的只读采集器保持可用。自动行程等其他规划项仍不自动实施。

## 历史与维护

- 2026-09-10：视频字幕 P0 一致性门禁已进入源码。`ai-zh` 等生成字幕只保留非敏感来源哈希并强制走 Whisper ASR；人工中文字幕仍可通过来源/时间轴门禁直通。生成 Note 前验证 Transcript 的 VideoAsset、Source、BV/CID、Snapshot 与状态，长 ASR 校对在 Ollama 下每批最多 32 段。目标 Ruff、视频相关 36 项与后端全量 117 项通过；前端 verify 在可用 Node 24 通过。真实结果和未完成非核心截图不在本页判定，见当前任务证据。
- 2026-09-10：已保存模型可选保存 `request_interval_seconds`（0–300 秒，留空继承全局设置），并分别作用于主/备用 Profile 的每次调用。该字段不保存 Key、不新增 Schema migration；后端全量与前端 verify 通过，未调用真实 Provider。
- 2026-09-10：视频质量总计划 WP0–22 的源码实现已完成：统一转写结构/时间轴门禁；所有模式独立分块扫描完整校对稿后再写入逐字 Evidence 地点候选；Pipeline/Replay 改为先地点后 Note；`0020` 保存地点化章节类型、关联 Mention 与引文；Note Map/Reduce 和最终章节只接收服务端 Grounded Evidence；全局和笔记页审核共用 `PlaceReviewCard` 与上下文 API，审核后同步刷新地点、笔记和地图缓存。后端完整 122 项、前端 verify、`git diff --check` 通过；`0020` 已在隔离的 0019 状态成功升级。WP23 仍按性能证据条件性延期；真实 Provider/视频重放、生产迁移/重启和历史截图补全本轮未执行。零库升级仍在既有 0019 历史 migration 重复创建 `preference_events` 处失败，未修改该已发布 migration。
- 2026-09-11：视频笔记的确认态地点候选以当前绑定 `Place` 为唯一展示来源，显示最新名称/地址并跳转地点详情；不再携带该视频的时间码或 Insight 行注释。未确认的 `REVIEW` 与 `UNRESOLVED` 保留 Evidence，并可进入手动 POI 搜索/确认。前端 verify 与已部署页面验收通过，未自动确认真实 POI。
- 2026-09-11：未确认地点候选及 Review Evidence 上下文的时间戳均为新窗口 Bilibili 链接，保留原 URL 参数并追加秒级 `t` 定位；纯函数单测覆盖分 P 参数保留，已部署页面核验 `2:32 → t=152`。

[实施历史](history/IMPLEMENTATION_HISTORY.md) 和 [归档实施计划](history/planning/README.md) 保留旧状态与计划追溯，默认不读。当前页只保留最新结论和未闭环项；完成项不持续追加长叙事。生产现场只更新 CURRENT_HANDOFF.md；冻结约束只更新 REGRESSION_AND_CHANGE_GUARD.md。新增证据必须写明日期、对象与验证层级。
