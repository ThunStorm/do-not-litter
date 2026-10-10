# 请求优化工作包发布门禁

记录日期：2026-10-10。本轮批准的是至简代码、离线验证、无迁移重部署和提交；Z8 的独立产品功能未授权。核心代码可加载，完整真实 E2E 未关闭。

| 门禁 | 状态 | 证据 |
| --- | --- | --- |
| Canonical ID、原文/quote 与 API 身份不变 | PASS（离线） | 短 ID 仅在请求边界，未知/越界/重复与非法关系拒绝；局部 ID 按稳定来源区间命名；缓存读取重新验证 |
| 无跨视频缓存与静默丢段 | PASS（离线） | 输入身份绑定 Snapshot、内容 hash、编译器/投影/映射版本；保留旧缓存，不删除历史；上下文不截尾 |
| 能力与结果可信度 | PASS（离线） | FORMAT_SMOKE 独立；四个业务小样；旧 smoke PASS/过期记录不证明业务质量；AUTO 未验证理由显式审计；direct/normalized/规则/模型修复与执行路径独立；模型 JSON 修复默认关闭、显式开启才运行 |
| Deadline/实际尝试/取消/Fence | PASS（离线） | Job/Stage 期限及请求估算在发送前核对，资源/限流等待与 HTTP 协作取消；timeout 不重发同请求；旧 Attempt 不能回写终态 |
| POI 保守门禁 | PASS（离线） | 无 quote、未知 Segment、跨 Snapshot/Source/VideoAsset 进入 REVIEW；不放宽 AUTO_STRONG，不确认真实 POI；既有语义/POI Golden 通过 |
| 审计安全与旧 DTO | PASS（离线） | 只存数值/版本/哈希；LocalMux 元数据白名单；调用明细兼容旧记录，reported/estimated/unknown 独立 |
| 全量回归与目标 UI | PASS | 后端 320、前端 19；末次诊断目标 74；Ruff、Lint/类型/构建与 PC/390px Browser |
| 当前 Mux 健康/目录 | BLOCKED_EXTERNAL | 本轮只读连接失败；未重启 Mux，至简离线机制不依赖其新增字段 |
| 真实视频/POI/质量/Token | NOT_RUN | 无授权生成样本与配对实测；不能把合成字节下降当成真实 Token/业务质量收益 |
| Ollama 实际推理退出 | NOT_RUN | Mock 卸载证明代码路径，真实退出证据未采集；UNKNOWN 保留 |

发布方式：确认 active Job/lease=0、integrity/FK 通过后 SQLite 逻辑备份、旧静态包备份；将已验收静态构建切换到 frontend/dist，保留旧哈希资源；生产 Python 执行 deploy/macos/manage.py restart/status；复核 Worker 新心跳、首页及资源 hash、OpenAPI、数据库版本与历史审计/Job 配置一致。无 Alembic 变更。

回滚：先确认无活跃 Job，再恢复备份静态包并使用 manage.py 重载。接手时已有未提交后端更改且没有独立源码快照，不能声称精确回滚到 2026-10-09 的未提交现场；已提交基线 b365616 可用，但回退到它会同时撤销此前同模型 Replay 功能，须按其影响单独判断。本轮另保存当前候选源码归档，避免丢失接手与新增更改。此包无 schema 变更，通常无需恢复数据库；只有数据损坏并获授权时才恢复 SQLite 逻辑备份，避免覆盖后来产生的数据。保留旧 Cache/Artifact/Audit 和原提交快照；旧 Job 在用户显式 Replay 后才使用新版请求边界。备份具体路径与部署结果见 CURRENT_HANDOFF.md。

部署证据（2026-10-10 11:04 北京时间）：API/Worker/首页/新心跳 READY，Worker PID=12182；0025、integrity=ok、FK=0、active/lease=0，Job 与 549 条 LLM Audit hash 不变；104 路径及新调用明细 DTO、JS/CSS HTTP 内容一致。生产 1440×1000/390×844 只读明细展开/收起通过。备份与静态切换入口均记录在 [交接生产快照](../CURRENT_HANDOFF.md)。
