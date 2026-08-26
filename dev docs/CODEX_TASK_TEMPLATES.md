# Codex 低额度任务模板

新任务优先使用下列最短模板，不粘贴完整历史会话或合订本。

## 诊断

```text
先读 dev docs/CODEX_CONTEXT.md 和与问题直接相关的专项规格。
只诊断，不改代码。给出根因、证据、影响范围和最小修复建议。
不要读取 COMPLETE_PROJECT_SPEC.md；工具输出只保留相关片段。
```

建议：高效模型，低/中推理。

## 局部修复

```text
先读 dev docs/CODEX_CONTEXT.md、IMPLEMENTATION_STATUS.md 和 <专项规格>。
修复 <一个明确问题>，不得扩展范围。
先跑目标测试，完成后只跑一次全量验证；前端改变才做目标页面 Browser 回归。
```

建议：成本/能力平衡模型，中推理。

## 高风险状态机/迁移

```text
先读 dev docs/CODEX_CONTEXT.md、REGRESSION_AND_CHANGE_GUARD.md、<专项规格>。
目标：<明确目标>。
硬约束：不破坏历史数据、Evidence、Job Lease、Replay 和兼容 ID。
先列出数据迁移与回退边界，再实施；必须有专项测试和数据库 integrity 验证。
```

建议：旗舰模型，高推理；避免 max/ultra，除非标准任务证明必要。

## UI 批注实施

```text
仅处理本轮全部批注，先抽象成同一份规格后一次实施。
读取目标页面组件、相关 CSS、标注设计和一个专项规格。
不要扫描所有 UI 文档；Browser 只返回目标容器 DOM、控制台错误和一张验收截图。
```

建议：成本/能力平衡模型，中推理。

## 文档同步

```text
只核对 <功能/版本> 的源码事实与状态文档。
不改业务代码，不读取全部合订本；更新源文档后重新生成 COMPLETE_PROJECT_SPEC.md。
输出差异和仍未验证项，不重复历史说明。
```

建议：高效模型，低推理。
