# 请求超时与共享片段归属修复验收（2026-11-13）

样本：[BV1Wx4w67Ef4](https://www.bilibili.com/video/BV1Wx4w67Ef4/)。**两项修复验收通过；视频流程为 PARTIAL_SUCCESS，内容质量仍为 NEEDS_REVIEW，不是整套计划或独立金标质量通过。** 本次复用已有可信 LOCAL_ASR/校对转写，重新读取真实 Bilibili 元数据核对 BV/CID；真实抽取、归纳、只读高德查询与截图均在隔离库执行，不冒称从新 ASR 开始的完整 E2E。

## 原因与最小差异

1. Gateway 曾将单请求 timeout 并入阶段 deadline，660 秒请求超时时抛 `AI_STAGE_WALL_TIME_EXCEEDED / switch_model=False`，阻止既有备用。现在分别保留 attempt deadline 与阶段/任务 hard deadline：前者返回 `AI_PROVIDER_TIMEOUT`，不重试同一超时模型，允许已配置备用；后者、取消、总次数及 Token 预算继续阻止后续调用。不改路由身份、Prompt、默认重试次数或生产设置。
2. 真实抽取暴露共享 Segment 的错归属：原句“除了高反人群，其他人都非常适合”在“第四个，辽宁千山”之前，却被归为“高反人群不适合千山”。新增确定性分句位置保护：仅对唯一可定位、位于目标地点明确转场介绍之前且未直接点名该地点的引文，撤销错误主体绑定，移入独立 SUPPLEMENTAL 待核原文，并移除对应错误作者态度证据。有效推荐保留；不猜改为前一地点，不改 Segment/Transcript。明确前指、重复引文等不确定情形不套用该拒绝规则。`source_scope_version=shared-segment-transition-v1` 隔离新产物身份，不重写历史产物。

反例先红后绿：请求超时/真正阶段截止/取消/尝试上限与缓存、共享片段前后归属/明确前指/重复引文/无其他态度证据时禁止自动 POI。新增修复文件为 `ai/gateway.py`、`services/{semantic_identity,grounded_map}.py` 及对应 Gateway/语义回归。

## 真实调用与重放

| 阶段 | 实际外发 LLM 尝试 | 结果与解释 |
|---|---:|---|
| 原 660 秒失败 | 1 | hy4free 等待 660 秒后终止，暴露分类问题 |
| 修复验收准备 | 1 | 续跑配置刷新覆盖验收 timeout，主动取消；保留原记录 |
| 90 秒主备边界验证 | 2 | Qwen3.8-Flash 超时后真实切 hy3，两者均在验收截止取消；只证明备用已进入，不证明业务质量 |
| 恢复原时限的真实链路 | 8 | 抽取 5 次（4 包、1 次 JSON 语法失败后原有纠错成功）；初轮归纳 3 次（2 成功、1 因发现错归属主动取消） |
| 归属保护后的重放与归纳 | 6 | 抽取零新增调用，复用 4 包已保存成功响应；归纳 6 次均返回成功，随后物化与截图 |
| **合计** | **18** | 包含失败及取消；本机拒绝/缓存回放不计真实外发 |

90 秒是隔离验收参数，不是生产默认。日志补证显示 Qoder 已获得上游 HTTP 200 响应头，hy3 曾在约 943ms 开始接收原始流且持续接收至第 71 秒；非流式客户端在完整结果前被 90 秒截止取消，不能据此声称上游无任何输出。恢复原有单请求 660 秒、抽取阶段 1320 秒、任务 1800 秒后，前四次抽取响应分别约 197/127/115/87 秒返回；第 4 包 JSON 缺逗号，按既有一次纠错约 201 秒后恢复。因此本次没有增加 SSE 改造。

归属修复独立验收窗口仍使用原有时限；同一隔离 Job 的累计模型尝试及 Token 账本保留，未通过重建 Job 清空预算。模型按执行时已保存路由冻结为 `qoder/Qwen3.8-Flash → codebuddy/hy3`，没有改生产配置。Provider 可信 usage、实际模型计费和费用仍 UNKNOWN，不能把审计中的零当免费，也不把墙钟时间当计费时长。

## 本次产物与限定验收

- Note `note_119c385b3ffd44f28c170a48901483c1`，版本 `ntv_573bf0f82ca34ac69804f37e6c7ecf3b`，绑定产物 `gma_bbac8d62c811473a8816238bc4877ffb`。五个主目的地均可读；50 条 Claim 的 Segment/逐字引文可达，**不等于语义召回 100%**。
- 观鲸风力与预约限制、景迈山局部自驾提醒、海螺沟 3600 米/高反限制、万峰林花期预测与历史客流限定保留。错误千山高反事实及其态度证据已移除，原句作为未归属材料保留；未增加模型阶段或逐地点二次复核。
- 21 个候选：12 REVIEW、6 SKIPPED、3 AREA_UNRESOLVED，自动确认 0；真实 POI 准确率 N/A。高德只读外发 2 次，没有生产确认。截图 9 READY、1 REJECTED；拒绝帧不包装为可用截图。
- 质量 API 仍为 NEEDS_REVIEW：14 项问题，9 条证据未被模型章节完整覆盖而保留原文；`generation_mode=UNKNOWN`、`summarized_fact_count=null`。景迈山/海螺沟仍有重复章节，措辞与完整语义尚需逐条裁定。没有将本样本晋级独立人工金标或宣称全计划完成。

## 自动检查、页面与生产边界

精确隔离交付候选：后端 **951** 项、前端 **66** 项、质量回放 **151** 项与 Ruff/ESLint/TypeScript/隔离构建均通过，后端及质量 JUnit 失败/跳过均 0；离线网络守卫自检通过，业务联网尝试 0。超时目标 71 项、归属目标 36 项通过。质量基线仍有 127 条 unjudged，托管 CI 尚未运行。

Browser 插件不可用，使用已有 Playwright/Edge；隔离真实产物在 1440/970/390×900 验证非空、五主目的地、目录滚动与焦点、截图放大/关闭、Tab、无横向溢出/错误覆盖层/相关 console 错误，业务写请求 0。初轮脚本定位到嵌套 article 的 strict-mode 错误后收窄；随后 404 源于隔离副本漏复制封面 WebP 派生图，补齐真实资源并匹配 SHA256 后三断点通过。这些验收准备失败日志保留，不算业务源码修复。

生产业务表摘要前后一致，原生产 Job/Note/Transcript 未改；无迁移、重启、新部署、历史回填或人工 POI 确认。生产仍运行原 U/K 隔离运行包，不能将源码修复或隔离通过描述为生产已加载。范围内源码与自动验证只同步 IMPLEMENTATION_STATUS；本报告保留内容质量未签收及发布边界。

本机原始证据在 `data/backups/video-{live,timeout-fix,production-timeout,scope-guard}-*20261113*/`；最终 `video-scope-guard-bv1wx4w67ef4-20261113-final/` 包含 acceptance.json、原始响应/配置/哈希、replayed-map、Note、截图与 Browser JSON/PNG。全量检查在 `/tmp/video-scope-final-checks-20261113/`。原始模型正文、数据库、Cookie/Key、截图不提交到远程；本报告仅保留必要摘要。机器摘要见 [验收摘要](VIDEO_TIMEOUT_AND_SCOPE_ACCEPTANCE_20261113.json)。
