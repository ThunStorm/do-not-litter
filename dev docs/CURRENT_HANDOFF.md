# 至简当前交接

> Repository snapshot：2026-09-03，HEAD `5ffaa1c057656b85845a2cdce3e3604471ee198f`。
> Production snapshot：2026-09-03 实际读取；生产提交未嵌入运行进程，不从工作树推断。
> 本文只说明交接与现场，不替代 `IMPLEMENTATION_STATUS.md` 的实现记录。

## 1. Repository state

- 分支：`codex/mac-mini-implementation`；当前工作树含未提交的源码和文档改动，接手前先读 `git status --short`，不得覆盖。
- Repository migration head：Alembic `0010`。
- 当前自动验证：后端 pytest 88 项、Ruff；Node `22.21.0` 下前端 ESLint、Vitest 12 项、TypeScript、Vite build 全部通过。
- 已实现：AI Workload Gateway 的显式 Profile/Stage Policy、兼容路由、质量门禁、Map/Reduce Facts、Cache、Budget、Domain Context、Vision Profile 边界，以及跨 API/Worker 的本地 AI `flock` 串行。具体契约见 `AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md`。
- `AI_ROUTING_SOURCE_RETENTION_V046_SPEC.md`、Gateway 规划契约和生产验收门禁已加入正式 source set；`COMPLETE_PROJECT_SPEC.md` 必须由构建脚本生成。

## 2. Production state

- 本次实际读取：`cn.zhijian.api`、`cn.zhijian.worker` 均为 `RUNNING`；`/health=ok`、首页正文可读、Worker 心跳就绪。
- Production database：SQLite/WAL，Alembic `0010 (head)`；当前 `QUEUED/RUNNING` Job 或 lease 为 0。
- 生产运行时：Python `3.14.6`，`/Volumes/D/Library/Application Support/Zhijian/venv/bin/python`；LaunchAgent 以当前仓库 `backend/src` 为 `PYTHONPATH`。
- 已有 Bilibili 站内二维码登录、`/nav` 账号验证与 Keychain 保存的真实验收；登录失效必须进入 `NEEDS_USER`，不回显 Cookie。
- Gateway 后半程尚无本次真实 Local/Remote Provider、真实视频或 Benchmark 的成套证据；不得称为 Gateway 生产验证通过。

## 3. Repository vs production gap

- 生产迁移当前已实际确认到 `0010`；以后仓库新增迁移时，仍必须重新读取 production revision，不能沿用本次结论。
- 当前生产服务对应的精确 Git SHA 不可得；任何未提交源码或当前 HEAD 是否已加载均不能由本文件断言。
- 自动回归证明源码行为；真实 Provider、真实视频、fallback、cache/force-regenerate、预算、取消与 Replay 的 Gateway 验收仍按 `AI_GATEWAY_PRODUCTION_ACCEPTANCE.md` 留存证据。

## 4. Current freeze conclusion

- 当前仓库能力与自动验证已封板；本轮没有为文档更新重启服务、调用真实 Provider 或重跑视频 Job。
- Production 服务健康和 `0010` 数据库已实际读取，但 Gateway 的真实端到端验收不随健康检查升级结论。
- Secret、API Key、Cookie 和真实用户内容不写入 SQLite 明文、日志、URL、localStorage 或交接材料。

## 5. Next task entry

1. 完整读取 `CODEX_CONTEXT.md`。
2. 在 `IMPLEMENTATION_STATUS.md` 中用 `rg` 定位当前能力段。
3. 读取 `REGRESSION_AND_CHANGE_GUARD.md` 的相关冻结项。
4. 仅再读一份直接相关专项规格；AI 路由优先读 `AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md`，真实验收优先读 `AI_GATEWAY_PRODUCTION_ACCEPTANCE.md`。

快速现场检查：

```bash
git status --short
.venv/bin/python deploy/macos/manage.py status
.venv/bin/python -m alembic -c backend/alembic.ini current
```

## 6. Explicit non-scope

封板后的候选工作全部在 `To Do/POST_FREEZE_TODO_BACKLOG.md`，且只有用户明确选择后才可实施：Production Acceptance、per-attempt Budget、fallback cache 语义、Gateway Consolidation、GenericProcessor、Source Watch、Contextual Vision、Multi Worker、Cloud、RAG 和高风险 Action Layer。

不得因“顺手”实施 `FUTURE_ROADMAP.md`，不得把测试、fixture、Browser 或本地临时迁移写成生产真实验收，也不得为取证中断健康服务。
