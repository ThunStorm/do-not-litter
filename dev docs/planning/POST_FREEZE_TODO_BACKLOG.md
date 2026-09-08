# 至简封板后待办池

> 仅记录尚未进入源码的候选工作；不是执行授权。当前能力与自动验证见 [实施状态](../IMPLEMENTATION_STATUS.md)，真实环境的验收缺口见 [AI Gateway 生产验收](../ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md)。

## 使用规则

每个工作包必须由用户明确选择后才实施。这里的优先级表示重新评估时的建议，而非队列或承诺。

## P0 — 生产验收与生产事实

已完成的自动化基础包括逐次预算检查、缓存命中审计、跨进程本地资源锁和离线 Benchmark runner；不把这些等同于真实 Provider 验收。缓存使用请求路由作为 key，同时保存实际返回的 Provider/Model；fallback 下的缓存语义仍须在真实矩阵中取证。仍需在合法配置和用户授权下完成生产门禁中的 Local/Remote 路由、fallback、cache/force-regenerate、预算、取消/Replay 与迁移演练。验收矩阵唯一维护在 [AI Gateway 生产验收](../ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md)。

## P1 — AIWorkloadGateway 收口

已完成第一段收口：缓存后的每次实际 Provider 尝试（含 retry/fallback）由 Gateway 按真实 LOCAL/REMOTE 执行预算与本地锁。下一段才是把 Profile/Stage route 解析和现有 Video audit adapter 脱离 `video_support.py`；在不改变现有路由审计或视频回归前，不进入 GenericProcessor。不得为此引入 LangChain、Redis 或分布式调度。

## P2 — GenericProcessor MVP

让未知非结构化内容产出带 Evidence 的 `title`、`summary`、`key_points`、`entities`、`dates`、`locations`、`action_items` 与 `claims`。首批验收样本为网页正文、聊天记录、通用 PDF、未知主题文章、商品介绍和通知公告；不同时引入 Vector DB、知识图谱或外部动作。

## P2 — Source Watch

以 HTTP 的 ETag、Last-Modified 或 content hash 识别变化，为每次变化创建新 Snapshot 与确定性 diff；可选 AI 只总结 diff。首批场景为招聘公告、网页内容、商品价格和旅行地点状态，不先做浏览器登录。

## P3 — Contextual Vision

只对由 Transcript、Section 或 PlaceMention 定位的候选帧做店招、菜单、价格、路牌或景点理解。VisualEvidence 与 TranscriptEvidence 并存，视觉结果不得覆盖确定性来源；进入条件是 P0 生产验收完成。视频样本与质量门见 [视频 Benchmark 与验收计划](video/VIDEO_WORKFLOW_BENCHMARK_AND_ACCEPTANCE_PLAN.md)。

## P3 — Golden Benchmark / Release Gate

建立有标注的视频 Golden Dataset，覆盖干净字幕、ASR、长视频、歧义 POI、Local/Remote、fallback 与 cache；模型、Prompt、chunk 与路由变更使用同一组样本。已有 Gateway Golden 骨架和离线 runner，尚缺业务标注与真实运行结果；详见 [视频 Benchmark 与验收计划](video/VIDEO_WORKFLOW_BENCHMARK_AND_ACCEPTANCE_PLAN.md)。

## HOLD

- Multi Worker：仅在单 Worker 成为真实瓶颈、出现多个物理节点或需要 Cloud Worker 时评估。
- Cloud / SaaS：多用户、租户隔离、云数据库、云 GPU、订阅与配额暂缓。
- Vector DB / RAG：等 GenericProcessor 规模与跨来源语义问答成为真实需求。
- Knowledge Graph：等跨域实体、多跳关系成为真实需求。
- 高风险 Action Layer：报名、发信、购买、预订和提交表单须另行设计权限、预览、确认、审计、回滚与风险分级。

## 建议重新启动顺序

1. P0 Production Acceptance；
2. P1 Gateway 收口；
3. P2 GenericProcessor；
4. P2 Source Watch；
5. P3 Vision 与视频业务 Benchmark。

任何 Agent 看到本文都不得创建代码、迁移、API、UI、生产操作或新依赖，除非用户明确选定一个工作包。
