# 跨项目 E2E 记录

日期：2026-10-10。至简基线 SHA `b365616fc3309ad48d1c5b24470a2ee8989bd1d4`，编译器 `stage-evidence-v1`，原业务 Map schema v3，Prompt `semantic-map-v3-compiler1`，合成 Golden `request-synthetic-v1`；数据库 schema 保持 0025。唯一修改范围为至简仓库，未修改或重启 LocalAiMux。

授权：本轮用户明确要求开发验证、重新部署与提交。计划第 0.3、12 节仍要求真实模型/视频 E2E 单独授权；本轮真实推理请求为 0，未续跑生产 Job、修改模型配置、确认 POI 或改写历史。

| 矩阵 | 结果 | 证据与限制 |
| --- | --- | --- |
| A 标准 OpenAI Mock | PASS（离线） | 本地路由参数/消息归一化、JSON、usage 缺省与契约回归；不启用未支持的流式能力 |
| B 现有 Mux | BLOCKED_EXTERNAL（实机） | 已保存型号 codebuddy/glm-5.3；Keychain 凭据存在，健康 GET ConnectError，目录读取 AI_PROVIDER_INTERFACE_UNAVAILABLE；未调用推理或扩大权限。已安装 Build SHA/目录 schema/执行限制 NOT_VERIFIED；Mock 兼容回归通过 |
| C 单模型 Text/JSON | NOT_RUN | 等待精确型号与低额度真实调用授权 |
| D 字幕视频 | NOT_RUN | 未提交新视频/重跑历史 Job |
| E ASR/校对视频 | NOT_RUN | 原业务证据保留；合成错音/数字/否定覆盖不是实机视频验收 |
| F 长视频/多地点 | PASS（合成传输）/NOT_RUN（实机） | 分块、末段、短 ID 与引用往返；真实 15–30 分钟 Ground Truth 未采集 |
| G 异常与恢复 | PASS（离线） | 429/503/timeout/截断/JSON 修复/取消、预算、Fence、Replay 目标和全量回归 |
| H Cache/强制生成 | PASS（离线） | 同快照缓存、跨视频/内容/接口身份隔离、fallback 与强制生成历史链；缓存不计新消耗 |
| I 并发/排队 | PASS（离线） | 资源锁、限流等待、取消与排队后 deadline 复核；未模拟实机多任务生成 |
| J Ollama 取消 | PASS（Mock 清理）/NOT_RUN（实机） | 一次限时空 Prompt 卸载及 /api/ps 核对；进程退出 NOT_VERIFIED，失败/仍加载为 UNKNOWN，不把客户端终止当成上游停止 |
| K A/B Token/质量 | PASS（合成表示）/NOT_RUN（模型） | 见 A/B 记录，reported Token 与 POI P/R 为 null，20%–30% 实测目标未证明 |

自动验证：后端全量 320 项通过，末次调用诊断变更的 74 项目标回归通过；完整源码/测试 Ruff 通过。前端 19 项、ESLint、TypeScript、隔离 Vite 构建通过。隔离 FastAPI/SQLite 与已安装 Edge 的 Playwright 验收 1440×1000、390×844 的 7 类调用结果、用量未知、部分接受、展开/收起，无溢出或相关控制台错误；Browser 插件未提供，内置 Computer Use 初始化超时，使用已有 Edge，未安装浏览器依赖。

真实模型、原生 Mux 目录、真实媒体质量、模型上游进程退出及 A/B 计费用量均不宣称通过。整体 production_proven=false。部署与回滚证据见 CURRENT_HANDOFF.md 的本次生产采样；本报告不覆盖其他日期的生产快照。

部署证据（2026-10-10 11:04 北京时间）：API/Worker/首页/新心跳 READY，Worker PID=12182；0025、integrity=ok、FK=0、active/lease=0，Job 与 549 条 LLM Audit hash 不变；104 路径及新调用明细 DTO、JS/CSS HTTP 内容一致。生产 1440×1000/390×844 只读明细展开/收起通过。备份与静态切换入口均记录在 [交接生产快照](../CURRENT_HANDOFF.md)。

Ollama 生命周期依据：[generate keep_alive](https://docs.ollama.com/api/generate)、[运行模型列表](https://docs.ollama.com/api/ps)。只核对公开卸载/加载状态；不据此推断系统进程实际退出。
