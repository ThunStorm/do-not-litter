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
| 当前 Mux 健康/目录 | PASS（15:56） | 11:04 阻塞定位为 API 未启动；启动现有仅本机 API 后健康/目录恢复，凭据与权限未改变 |
| 真实视频/POI/质量/Token | PARTIAL / NOT_RUN | 3次有限模型小样与1对合成输入真实生成通过；Token/精确型号未知，指定8分钟ASR视频流程已完成、6个地点待处理；全矩阵/人审GT未验收 |
| Ollama 实际推理退出 | NOT_RUN | Mock 卸载证明代码路径，真实退出证据未采集；UNKNOWN 保留 |

发布方式：确认 active Job/lease=0、integrity/FK 通过后 SQLite 逻辑备份、旧静态包备份；将已验收静态构建切换到 frontend/dist，保留旧哈希资源；生产 Python 执行 deploy/macos/manage.py restart/status；复核 Worker 新心跳、首页及资源 hash、OpenAPI、数据库版本与历史审计/Job 配置一致。无 Alembic 变更。

回滚：先确认无活跃 Job，再恢复备份静态包并使用 manage.py 重载。接手时已有未提交后端更改且没有独立源码快照，不能声称精确回滚到 2026-10-09 的未提交现场；已提交基线 b365616 可用，但回退到它会同时撤销此前同模型 Replay 功能，须按其影响单独判断。本轮另保存当前候选源码归档，避免丢失接手与新增更改。此包无 schema 变更，通常无需恢复数据库；只有数据损坏并获授权时才恢复 SQLite 逻辑备份，避免覆盖后来产生的数据。保留旧 Cache/Artifact/Audit 和原提交快照；旧 Job 在用户显式 Replay 后才使用新版请求边界。备份具体路径与部署结果见 CURRENT_HANDOFF.md。

部署证据（2026-10-10 11:04 北京时间）：API/Worker/首页/新心跳 READY，Worker PID=12182；0025、integrity=ok、FK=0、active/lease=0，Job 与 549 条 LLM Audit hash 不变；104 路径及新调用明细 DTO、JS/CSS HTTP 内容一致。生产 1440×1000/390×844 只读明细展开/收起通过。备份与静态切换入口均记录在 [交接生产快照](../CURRENT_HANDOFF.md)。

本轮真实调用证据见 [小样记录](AI_REQUEST_OPTIMIZATION_LIVE_SAMPLE.json)。仅完成 C 与 B 的有限范围，K 仍为部分验收；D/E/F/J 的实机视频与退出证据保持开放。没有在小样通过后保存业务能力 PASS、改变默认模型、提高自动 POI 确认权限或启动 Z8。

2026-10-10 指定视频已进入PARTIAL_SUCCESS，生成Note/截图并留存Review；[视频验收](VIDEO_E2E_BV11Ao7BYE1V_REPORT.md)记录一次真实JSON格式错误、零重试约束补修、Wire字符估算修正与步骤续跑。代码补修322/19通过，43f42ff已加载；未回填失败历史，10次尝试未超12次边界。
