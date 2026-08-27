# 至简当前交接

> 快照日期：2026-08-28。本文只负责“当前现场、剩余条件、下一步入口”，不复制产品规格。实施事实仍以 `IMPLEMENTATION_STATUS.md` 为准。
> 本文故意不加入 `manifest.json` 和 `COMPLETE_PROJECT_SPEC.md`，避免把短期现场快照重复塞进 1 万多行合订本。

## 1. 当前可接手状态

- 分支：`codex/mac-mini-implementation`；Python 3.14/LaunchAgent 定版实现基线为提交 `d4c7ab2`，最新提交以 `git log -1 --oneline` 为准。
- API、Worker、SQLite 均为 `RUNNING`；`/health=ok`，首页正文非空，Worker 心跳持续更新。
- 生产解释器：Python `3.14.6`，路径 `/Volumes/D/Library/Application Support/Zhijian/venv/bin/python`。
- 数据库：SQLite/WAL，Alembic `0008 (head)`；当前活跃 Job 为 0。
- 自动回归：Python 3.14 后端 pytest 57 项、Ruff、`pip check`；Node 22 前端 ESLint、Vitest 10 项、TypeScript、Vite build。
- `install/restart` 已增加 launchd 标签卸载等待门禁，避免 `bootout` 后立即 `bootstrap` 的退出码 5 竞态；已有目标测试。
- Keychain 服务可访问；未在日志、数据库或文档中输出 Secret。

快速确认现场只需要：

```bash
git status --short
.venv/bin/python deploy/macos/manage.py status
.venv/bin/python -m alembic -c backend/alembic.ini current
```

## 2. 真正尚未闭环的事项

冻结的 v0.4.6 范围内没有已知阻塞实现。以下均为条件项或观察项，不应自动扩张成新工作包：

1. **下一次自然维护窗口验证重载**：launchd 卸载等待修复已通过单测，但修复后没有为了验收而再次中断健康服务。下次正常安装、登录重启或计划维护时，核对两个服务能连续重载且 `program` 仍指向 Python 3.14 生产 venv。
2. **长期 TCC 观察**：切换后的短期日志没有新的 `SystemPolicyRemovableVolumes deny`；仍需跨一次自然登录/重启继续观察。不要仅为取证主动打断服务。
3. **GUI 与真实外部链路**：本次运行时迁移没有重跑全站 PC/Mobile GUI、真实 Provider、真实 Bilibili 视频或 Job。只有相关行为变化或专项验收明确授权时才执行。
4. **Ollama 模型状态**：当前 Ollama 服务在线，但 `/api/status` 显示 0 个模型。若要使用本地推理，再执行模型拉取与真实推理验收；若当前使用远程模型路由，这不是阻塞项。
5. **外部配置**：高德 Key、外部模型 Key、部分视频 Cookie 只能由部署者提供。未配置时系统应显示可行动诊断或 `NEEDS_USER/PARTIAL_SUCCESS`，不能伪造成功。
6. **Git 交付**：当前分支没有配置 upstream，定版提交尚未推送远端；是否推送由用户另行授权。`.DS_Store` 属于本机噪声，不要提交。

`FUTURE_ROADMAP.md` 中的 GenericProcessor、云化、多 Worker、自动操作等不是未完成工作，也不授权实施。

## 3. 上次文档合并核对

- 已删除旧的 445 行 `PROJECT_HANDOVER.md`、临时 Python 迁移交接和用户指定删除的问题记录；索引、生成清单和正式文档链接中没有残留引用。
- 旧交接中的稳定事实已分别收敛到 `CODEX_CONTEXT.md`、`IMPLEMENTATION_STATUS.md`、`REGRESSION_AND_CHANGE_GUARD.md` 和 `deploy/macos/README.md`。
- `manifest.json` 与 `scripts/build_complete_project_spec.py` 当前均包含 37 份正式源文档，集合完全一致。
- `COMPLETE_PROJECT_SPEC.md` 已由正式源文档重新生成；它是派生产物，不是编辑源。
- 各版本专项规格仍保留，因为它们承担精确回归契约，不属于可随意删除的重复文档。

## 4. 最省 token 的接手顺序

默认只读以下内容，读到足够解决当前工作包就停止：

1. `CODEX_CONTEXT.md`：完整读取，确认项目边界、危险文件和文档路由。
2. `IMPLEMENTATION_STATUS.md`：先用 `rg` 定位当前能力，只读命中段和最新部署段，不要从头重放全部历史。
3. `REGRESSION_AND_CHANGE_GUARD.md`：只读与当前改动相关的基线和回归矩阵。
4. 本文：只有接手当前服务、部署或交付状态时读取。
5. 再选 **一份** 直接相关专项规格；只有它明确引用且确有必要时才读下一份。

### 默认不要读

| 内容 | 为什么费 token 且默认收益低 | 什么时候才读 |
| --- | --- | --- |
| `COMPLETE_PROJECT_SPEC.md`（约 1.04 万行） | 只是分文档合订本，重复度最高 | 用户明确要求全局审计、重建合订本或检查跨域冲突 |
| `PROJECT_PLAN.md`（约 926 行） | 大量历史计划已被实施状态取代 | 重新规划阶段、核对未进入实现的原始工作包 |
| `VIDEO_AI_NOTE_IMPLEMENTATION_GUIDE.md`（约 961 行） | 只服务视频实施，且含历史阶段说明 | 视频 Pipeline 实施或专项回归 |
| `VIDEO_AI_NOTE_PIPELINE.md`（约 889 行） | 视频领域完整规格，局部任务通常用不到 | 视频步骤、Transcript、截图、地点或地图链路变化 |
| `FUTURE_ROADMAP.md`（约 315 行） | 未来设想，不是当前授权和验收条件 | 用户明确做路线规划或提升某项优先级 |
| 不相关的 v0.4.2–v0.4.6 专项规格 | 精确但彼此独立，批量读取会重复状态说明 | 当前改动直接触及对应功能 |
| `design/ui/**`、历史截图 | 视觉证据体积大，后端/文档任务无收益 | 前端视觉实现或 Browser 验收 |
| `node_modules/`、`frontend/dist/`、缓存、模型文件 | 生成物或第三方内容，不是项目决策源 | 依赖损坏、构建产物或运行时文件专项诊断 |
| 全量日志、完整数据库记录、完整 DOM/AX Tree | 噪声大且可能含敏感上下文 | 先聚合/筛选仍无法定位问题时 |

### 不要重复验证

- 文档-only 变更不重启服务、不跑 Browser、不跑真实 Provider/视频 Job。
- 先跑目标测试；完成代码工作包后再跑一次全量后端与前端验证。
- 已确认的文件和输出后续只查变化或失败证据，不重新整段读取。
- 不因“顺手”读取或实施 `FUTURE_ROADMAP.md`。

## 5. 接手边界

- 当前实施状态：`IMPLEMENTATION_STATUS.md`。
- 稳定上下文和文档路由：`CODEX_CONTEXT.md`。
- 防回退契约：`REGRESSION_AND_CHANGE_GUARD.md`。
- 部署与恢复命令：`../deploy/macos/README.md`。
- 本文只做短期交接；现场事实变化时更新本文，不把历史过程继续堆进来。
