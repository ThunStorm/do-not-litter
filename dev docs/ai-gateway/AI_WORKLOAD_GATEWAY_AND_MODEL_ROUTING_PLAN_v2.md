# AI Workload Gateway v2 契约索引

> 2026-09-03 按主题拆分；原章节编号保留。只选与本任务有关的一篇，再按标题定位，不要求连读。正文中的规划/旧状态不证明当前实现；先看 [当前状态](../IMPLEMENTATION_STATUS.md) 与相关 [冻结约束](../REGRESSION_AND_CHANGE_GUARD.md)。

| 任务主题 | 分篇 | 原章节 |
| --- | --- | --- |
| 架构与模型边界 | [01-architecture-models.md](01-architecture-models.md) | 1–11 |
| Gateway、路由与公共上下文 | [02-gateway-context.md](02-gateway-context.md) | 12–27 |
| Pipeline 优化、Provider 与 Usage | [03-pipeline-providers.md](03-pipeline-providers.md) | 28–41 |
| Stage Policy 与参数设置 | [04-stage-policy.md](04-stage-policy.md) | 41A–41I |
| 单次任务策略、API 与 Cache Key | [05-job-policy.md](05-job-policy.md) | 41J–41S |
| 历史工作包与验收设计 | [06-rollout-acceptance.md](06-rollout-acceptance.md) | 42–50 |

## 使用边界

- 本方案形成于 2026-08-28。模型体积、型号建议与 Work Package 状态属于当时规划；不能据此宣称当前模型能力、路由已升级或生产验收完成。
- AUTO 等“实际运行语义”必须核对当前策略解析代码与测试，不能只照设计目标推断。未授权的质量升级、视觉理解、RAG 不自动实施。
- 真实 Provider/视频与 Benchmark 只按 [生产验收门禁](AI_GATEWAY_PRODUCTION_ACCEPTANCE.md) 执行；第 6 分篇默认只在追溯或明确验收任务时读取。
- 现有 Provider 运行说明见 [ai-gateway/AI_RUNTIME_AND_PROVIDERS.md](AI_RUNTIME_AND_PROVIDERS.md)；不要求每次与所有分篇一起读取。
