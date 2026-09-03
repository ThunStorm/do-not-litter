# 至简当前封板物料与交接文档更新指南

> 适用仓库：`ThunStorm/do-not-litter`
> 适用分支：`codex/mac-mini-implementation`
> 本轮目标：**只完成当前代码状态的封板、物料同步、交接文档收敛与一致性校验。**
> 本轮不授权实现新的产品能力，不授权顺手处理未来 Roadmap，不授权把尚未发生的生产迁移写成已完成。
> 本文是一份给 Codex / Agent 的执行指南，不是未来开发计划。

---

## 0. 本轮封板的核心定义

本轮“封板”指：

1. 以当前分支最新代码为实现事实源，整理已经进入仓库的能力；
2. 将落后的交接、回归、上下文和物料索引更新到与当前仓库一致；
3. 明确区分：
   - **仓库代码事实**
   - **自动测试事实**
   - **生产 Mac mini 现场事实**
   - **尚未执行的真实验收**
4. 将下一阶段开发事项全部隔离到单独的待办文档；
5. 让后续新 Agent 只读少量文件即可知道：
   - 现在代码做到哪里；
   - 哪些已经自动验证；
   - 哪些尚未在生产执行；
   - 从哪里继续；
   - 哪些内容不属于当前授权。

本轮封板不是：

- 自动把 v0.4.6 改成一个未经确认的新版本号；
- 自动升级生产数据库；
- 自动重启 API / Worker；
- 自动跑真实 Provider；
- 自动跑视频 Job；
- 自动实施 GenericProcessor / Source Watch / Vision；
- 自动重构 AI Gateway；
- 自动处理所有未来技术债。

---

# 1. 当前必须采用的事实基线

## 1.1 Git 仓库事实

当前工作分支：

```text
codex/mac-mini-implementation
```

当前已知 HEAD：

```text
20ad3521685cc8c66d51d75a9b31c91de418bc84
feat: add AI workload gateway routing
2026-08-29
```

Agent 开始工作时必须重新执行：

```bash
git status --short
git log -1 --oneline
git rev-parse HEAD
```

如果 HEAD 已经变化：

- 以实际 HEAD 为准；
- 不机械复制本文 SHA；
- 先查看从 `20ad352` 到当前 HEAD 的差异，再决定哪些文档需要继续更新。

## 1.2 当前代码数据库头

当前仓库已经包含：

```text
0008_llm_quota_defaults
0009_ai_workload_facts
0010_ai_cache_entries
```

因此：

```text
repository migration head = 0010
```

但这一事实**不能自动推出生产数据库已经升级到 0010**。

## 1.3 当前已知生产快照

现有 `CURRENT_HANDOFF.md` 的 2026-08-28 快照记录过：

```text
production database = Alembic 0008
API / Worker / SQLite = RUNNING
Python = 3.14.6
```

这只是历史生产快照。

本轮更新文档前，若 Agent 能访问实际 Mac mini，必须重新检查：

```bash
.venv/bin/python deploy/macos/manage.py status
.venv/bin/python -m alembic -c backend/alembic.ini current
```

若无法访问生产现场：

- 只能写“最后已确认生产状态为 0008（2026-08-28 快照）”；
- 不允许写“生产已升级至 0010”；
- 不允许把临时 SQLite 迁移测试当成生产迁移完成。

## 1.4 当前自动验证事实

`IMPLEMENTATION_STATUS.md` 已记录 AI Workload Gateway 后续工作包已经推进到：

- WP1 Gateway Skeleton
- WP2–WP4 Model Registry / Policy / Routing
- WP5–WP8 Usage / Quality Gate / Map-Reduce / Facts
- WP9 Cache + Budget
- WP10 Domain Context
- WP11 Vision Boundary
- Runtime Hardening

最新记录的自动验证基线为：

```text
Backend pytest: 74
Ruff: PASS

Frontend:
ESLint: PASS
Vitest: 10
TypeScript: PASS
Vite build: PASS
```

本轮封板时，应重新运行或至少核实当前代码对应的真实测试数量；不得继续把旧的 57/59/69/71/73 当成“当前最终基线”。

## 1.5 当前真实验收边界

现有实现记录明确说明，AI Workload Gateway 后半程实施时：

```text
未触发真实 Provider
未触发真实视觉模型
未触发真实视频 Job
未迁移生产数据库到 0009 / 0010
未因此轮实现重启生产服务
```

因此封板文档必须保留这个边界。

不能使用：

```text
“Gateway 已生产验证”
“Cache 已生产验证”
“Budget 已生产验证”
“Local/Remote 路由已完整生产验证”
```

除非本轮实际完成并留下证据。

---

# 2. 本轮要解决的文档不一致

当前不是“缺文档”，而是**不同文档停留在不同时间点**。

至少存在以下漂移：

| 文件 | 当前问题 | 本轮处理 |
| --- | --- | --- |
| `IMPLEMENTATION_STATUS.md` | 已包含 Gateway 最新实施记录，但顶部日期、总体摘要和生产边界仍需收敛 | 更新 |
| `CODEX_CONTEXT.md` | 仍写数据库 0008、旧验证基线，没有把最新 AI Gateway 作为当前上下文入口 | 必须更新 |
| `CURRENT_HANDOFF.md` | 仍以 2026-08-28 / 0008 / 57 tests 为现场主描述 | 必须更新 |
| `REGRESSION_AND_CHANGE_GUARD.md` | 回归矩阵仍把数据库 head 写成 0008，AI Gateway 新契约未进入冻结保护 | 必须更新 |
| `manifest.json` | 仍为 `0.4.6 / 2026-08-28`，正式文档集合未显式纳入最新 Gateway 规划文档 | 评估后更新 |
| `COMPLETE_PROJECT_SPEC.md` | 是派生产物，只能在源文档更新完成后重新生成 | 重新生成 |
| `CODEX_TASK_TEMPLATES.md` | 如仍未覆盖“封板/生产验收/AI 路由”最省 Token 接手模式，可小幅更新 | 可选 |
| `README.md` | 若顶层状态与部署事实明显落后，可只做最小更新 | 可选 |
| `AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md` | 是本轮已实施架构的重要专项计划/契约，应确认是否升级为正式源文档 | 必须评估 |
| `AI_ROUTING_SOURCE_RETENTION_V046_SPEC.md` | 已实施专项契约，但未出现在当前 manifest 正式集合 | 必须评估 |

原则：

> 不因“封板”而把所有文档都重写一遍。
> 只更新已经被当前实现事实影响的文件。

---

# 3. 本轮文档层级重新定义

封板后必须让每份文档职责清晰。

## 3.1 `IMPLEMENTATION_STATUS.md`

唯一职责：

> **记录仓库已经实现了什么，以及每一批实现有什么验证证据。**

必须包含：

- 当前分支与 HEAD；
- 当前代码迁移 head；
- 当前自动验证基线；
- 最新 AI Workload Gateway 已实施能力摘要；
- “生产是否已经应用”的独立说明；
- 不把 Future Roadmap 写成未完成缺陷。

不应包含：

- 大量下一阶段设计；
- 未授权的技术债处理方案；
- GenericProcessor 计划；
- Source Watch 规划。

## 3.2 `CURRENT_HANDOFF.md`

唯一职责：

> **告诉下一位 Agent 当前现场是什么、从哪里接手、哪些事情没有闭环。**

必须采用双层状态：

### A. Repository State

例如：

```text
branch
HEAD
migration head
latest test baseline
latest implemented architecture
```

### B. Production State

例如：

```text
last verified production commit
production alembic revision
API / Worker / SQLite status
runtime
active jobs
last real provider/video acceptance
```

禁止再把：

```text
代码 head = 0010
```

和：

```text
生产 database = 0010
```

混成一个事实。

若生产无法实时读取，就写：

```text
Last verified production snapshot: 2026-08-28
```

并明确标记为历史快照。

## 3.3 `CODEX_CONTEXT.md`

唯一职责：

> **成为后续新任务的第一读物。**

封板后应控制在精简范围。

必须新增/更新：

- 当前分支 / HEAD；
- Repository migration head 与 Production migration state 分开；
- 当前测试基线；
- AI Workload Gateway 入口；
- 与模型 / AI 路由任务相关时应该优先读哪一份专项文档；
- 不默认读取整个 `COMPLETE_PROJECT_SPEC.md`；
- 不默认执行真实 Provider / 视频 Job / 生产迁移。

## 3.4 `REGRESSION_AND_CHANGE_GUARD.md`

唯一职责：

> **冻结已经确认的行为，防止后续 Agent 重构时破坏。**

本轮应新增 AI Gateway 冻结项，至少覆盖：

- Model Profile 显式记录 location / modalities / capabilities；
- Stage Policy 不靠模型名推断能力；
- 历史任务无新策略时保持旧路由兼容；
- Transcript Quality Gate 不允许重新扩大成无条件全文校对；
- Map/Reduce 不允许退回“每阶段重复发送整份 Transcript”；
- Cache Hit 不重复调用 Provider；
- `force_regenerate` 必须绕过命中并保留结果链；
- Domain Context 只能低优先级增强，不能覆盖 Evidence / Schema / 安全契约；
- Vision Profile 必须 image-capable；
- Ollama `keep_alive: 0` 契约不可回退；
- 本地 AI 重任务不能默认提高并发。

数据库回归矩阵必须改成双层：

```text
repository migration head
production current revision
```

不要再写单一：

```text
current head = 0008
```

## 3.5 `manifest.json`

它的职责是：

> **定义正式文档源集合与当前冻结元数据。**

本轮不要自动把：

```json
"version": "0.4.6"
```

改成任意新版本。

只有以下情况才能改版本：

1. 项目已有明确版本规则；
2. 用户明确授权新版本号；
3. 或代码中存在统一版本源且可以确定本轮正式版本。

否则：

- 保留 `0.4.6`；
- 可以更新 `frozen_date` 前必须确认其语义是“产品版本冻结日期”还是“文档集合最后同步日期”；
- 若语义不明确，优先增加新的元数据字段，而不是篡改历史版本含义，例如：

```json
"repository_snapshot_date": "2026-09-03",
"repository_snapshot_commit": "<HEAD>"
```

如果不希望修改 manifest schema，则保持原字段，避免为了形式制造新版本。

## 3.6 `COMPLETE_PROJECT_SPEC.md`

严格规则：

```text
GENERATED FILE
```

禁止手改。

必须在全部源文档完成之后再执行：

```bash
.venv/bin/python scripts/build_complete_project_spec.py
```

生成后必须检查：

```bash
git diff -- "dev docs/COMPLETE_PROJECT_SPEC.md"
```

确认它只反映源文档变化，没有异常丢失章节。

---

# 4. 正式物料集合处理规则

## 4.1 本轮必须保留的核心交接物料

至少：

```text
dev docs/CODEX_CONTEXT.md
dev docs/CURRENT_HANDOFF.md
dev docs/IMPLEMENTATION_STATUS.md
dev docs/REGRESSION_AND_CHANGE_GUARD.md
dev docs/AI_RUNTIME_AND_PROVIDERS.md
dev docs/AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md
dev docs/manifest.json
dev docs/COMPLETE_PROJECT_SPEC.md
deploy/macos/README.md
AGENTS.md
```

## 4.2 Gateway 文档是否加入 manifest

必须检查：

```text
AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md
AI_ROUTING_SOURCE_RETENTION_V046_SPEC.md
```

判断原则：

### 应加入正式 source set

若文档承担以下任意职责：

- 当前实现契约；
- 当前回归基线；
- 后续 Agent 必须读取；
- 包含仍然有效的架构边界。

### 不应加入

若只是：

- 临时计划；
- 已完全被 `IMPLEMENTATION_STATUS.md` / ADR 取代；
- 与正式规格重复且不再具有约束力。

如果加入：

必须同时同步：

```text
manifest.json documents[]
scripts/build_complete_project_spec.py ORDER[]
```

并确保两个集合一致。

如果不加入：

必须在交接文档明确说明为什么保留在仓库但不是正式合订本源。

---

# 5. 推荐执行顺序

Agent 必须按照下面顺序执行，禁止先大改文档再回头查事实。

## Phase 1 — 锁定现场

```bash
git status --short
git log -1 --oneline
git rev-parse HEAD
```

如果能访问生产 Mac mini：

```bash
.venv/bin/python deploy/macos/manage.py status
.venv/bin/python -m alembic -c backend/alembic.ini current
```

记录：

```text
repository HEAD
repository migration head
production revision
service status
active jobs
```

不做任何修改。

## Phase 2 — 只读必要源

完整读取：

```text
AGENTS.md
dev docs/CODEX_CONTEXT.md
dev docs/CURRENT_HANDOFF.md
dev docs/REGRESSION_AND_CHANGE_GUARD.md
```

定向读取：

```text
IMPLEMENTATION_STATUS.md 中 2026-08-28 以后 AI Workload Gateway 段
AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md 的状态/验收/工作包段
AI_RUNTIME_AND_PROVIDERS.md 的 Local First / GPU / Provider 契约
```

默认不要读取：

```text
COMPLETE_PROJECT_SPEC.md 全文
PROJECT_PLAN.md 全文
FUTURE_ROADMAP.md 全文
design/ui/**
完整历史日志
完整数据库
```

## Phase 3 — 建立事实表

在动文档前先形成临时事实表：

| 类型 | 值 | 是否已生产验证 | 来源 |
| --- | --- | --- | --- |
| HEAD | 当前 SHA | N/A | Git |
| repo migration head | 0010 或实际值 | N/A | Alembic files |
| prod migration | 实际读取或 last verified | YES/UNKNOWN | production |
| pytest | 当前实际结果 | N/A | test |
| frontend build | 当前实际结果 | N/A | test |
| Local routing | implemented | 未生产/已生产 | status |
| Remote fallback | implemented | 未生产/已生产 | status |
| cache | implemented | 未生产/已生产 | status |
| budget | implemented | 未生产/已生产 | status |
| domain context | implemented | 未生产/已生产 | status |
| vision boundary | implemented | 未生产/已生产 | status |

所有文档都从这个事实表写，不允许各自猜测。

## Phase 4 — 更新源文档

推荐顺序：

```text
1. IMPLEMENTATION_STATUS.md
2. REGRESSION_AND_CHANGE_GUARD.md
3. CODEX_CONTEXT.md
4. CURRENT_HANDOFF.md
5. AI_RUNTIME_AND_PROVIDERS.md（仅必要修正）
6. manifest.json
7. scripts/build_complete_project_spec.py（仅 source set 改变时）
8. README / CODEX_TASK_TEMPLATES（仅必要时）
```

## Phase 5 — 生成派生物

只有源文档稳定后：

```bash
.venv/bin/python scripts/build_complete_project_spec.py
```

## Phase 6 — 一致性检查

至少检查：

```bash
git diff --check
git diff --stat
git diff -- "dev docs"
```

并人工确认：

- 没有把生产 0008 写成已升级 0010；
- 没有把自动测试写成真实 Provider 验收；
- 没有把 Future Roadmap 写成当前缺陷；
- 没有重复大段历史；
- 没有把 Secret / Key / Cookie 写入文档；
- `manifest.json` 与构建脚本正式文档集合一致；
- `COMPLETE_PROJECT_SPEC.md` 与源文档一致。

---

# 6. 本轮测试策略

## 6.1 文档-only 更新

如果本轮最终只改：

```text
*.md
manifest.json
build_complete_project_spec.py 中的文档 ORDER
```

则默认不需要：

- 重启 API；
- 重启 Worker；
- 跑真实 Provider；
- 跑真实视频；
- 跑 Browser 全站验收。

至少执行：

```bash
git diff --check
.venv/bin/python scripts/build_complete_project_spec.py
```

如修改构建脚本：

```bash
.venv/bin/python -m py_compile scripts/build_complete_project_spec.py
```

## 6.2 如果为了确认基线执行自动测试

可运行：

```bash
.venv/bin/python -m pytest backend/tests -q
.venv/bin/python -m ruff check backend/src backend/tests
pnpm --dir frontend lint
pnpm --dir frontend test -- --run
pnpm --dir frontend build
```

目的只是：

> 更新当前封板验证基线。

不能因为测试通过就声称：

```text
生产真实模型链路已验收
```

---

# 7. `CURRENT_HANDOFF.md` 推荐最终结构

建议重写为下面的短结构，不再继续堆历史。

```markdown
# 至简当前交接

> Repository snapshot:
> Production snapshot:
> Last updated:

## 1. Repository state
- branch
- HEAD
- migration head
- test baseline
- latest implemented work packages

## 2. Production state
- last verified commit/deployment
- production alembic
- API / Worker / SQLite
- runtime
- active jobs
- last real provider/video acceptance

## 3. Repository vs production gap
- code changes not yet deployed
- migrations not yet applied
- features only automatically tested

## 4. Current freeze conclusion
- what is considered implemented
- what is not considered production-accepted

## 5. Next task entry
- read CODEX_CONTEXT
- locate only relevant status section
- read regression guard
- read one specialist spec

## 6. Explicit non-scope
- refer to POST_FREEZE_TODO_BACKLOG.md
```

目标：

```text
CURRENT_HANDOFF <= 约 200 行
```

不要再把大量版本历史复制进去。

---

# 8. `CODEX_CONTEXT.md` 推荐更新点

至少修正：

### 当前事实

从旧的：

```text
数据库：Alembic 0008
```

改为明确分层：

```text
仓库 schema head：0010
生产 schema：以 CURRENT_HANDOFF 的现场快照为准，不从仓库 head 推断
```

### AI 任务路由

增加：

| 任务 | 必读 |
| --- | --- |
| AI Gateway / 模型路由 / Cache / Budget / Domain | `AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md` + `AI_RUNTIME_AND_PROVIDERS.md` |
| AI 生产验收 | `CURRENT_HANDOFF.md` + `REGRESSION_AND_CHANGE_GUARD.md` |

### 禁止项

新增：

```text
- 不把 repository migration head 当作 production migration state；
- 不把 pytest / Browser fixture 当作真实 Provider 验收；
- 不因发现 Future TODO 顺手实施；
- 不重复设计已经落地的 Token 优化架构。
```

---

# 9. `IMPLEMENTATION_STATUS.md` 推荐更新点

不要删除已有 Gateway 工作包历史。

在顶部增加一个最新摘要，例如：

```markdown
## Current repository freeze

- Branch:
- HEAD:
- Repository schema head:
- Automated regression:
- AI Workload Gateway:
  - stage policy/routing: implemented
  - usage: implemented
  - transcript quality gate: implemented
  - map/reduce facts: implemented
  - cache: implemented
  - budget: implemented
  - domain context: implemented
  - vision boundary: implemented
  - local single-process resource guard: implemented
- Production acceptance:
  - production migration: NOT CLAIMED unless verified
  - real provider/video E2E after Gateway: NOT CLAIMED unless verified
```

这样后续 Agent 无需扫历史 1,000 行才能知道现在在哪。

---

# 10. `REGRESSION_AND_CHANGE_GUARD.md` 推荐新增 AI 冻结矩阵

建议增加：

| 能力 | 不可回退要求 |
| --- | --- |
| AI Stage Policy | Stage 参数按白名单，不能任意透传未知模型参数 |
| Model Profile | Location / modalities / capabilities 显式保存，不能仅靠模型名猜 |
| Routing | LOCAL_ONLY / LOCAL_FIRST / REMOTE_FIRST / REMOTE_ONLY / AUTO 保持兼容 |
| Transcript Gate | 干净平台字幕不应默认整份送模 |
| Map/Reduce | 长 Transcript 不应在多个阶段重复全文送模 |
| AI Cache | 精确命中不重复调用 Provider；refresh 保留版本链 |
| AI Budget | Cache Hit 不计真实模型调用预算 |
| Domain Pack | 低优先级上下文，不得覆盖 Evidence / Schema / Safety |
| Vision Boundary | text-only Profile 不得绑定视觉 Stage |
| Ollama Memory | `keep_alive: 0` 不得回退 |
| Production Truth | 自动测试与真实生产验收必须分开记录 |

本轮只冻结已实现契约。

尚未修复的技术债不要写成“不可回退的已完成能力”。

---

# 11. 待办隔离规则

本轮发现的以下内容：

- Production Acceptance；
- 跨进程 Local AI Resource Lease；
- Local / Remote Budget 分账；
- Per-attempt Budget；
- Fallback Cache 语义；
- Gateway Consolidation；
- GenericProcessor；
- Source Watch；
- Vision；
- Multi Worker；
- Cloud；
- RAG；

全部写入：

```text
POST_FREEZE_TODO_BACKLOG.md
```

在当前交接文件里只能写：

```text
“后续非封板事项见 POST_FREEZE_TODO_BACKLOG.md”
```

不要复制正文。

---

# 12. 封板完成标准

只有全部满足才算本轮完成。

## 文档完整性

- [ ] `IMPLEMENTATION_STATUS.md` 有当前 Repository Freeze 摘要
- [ ] `CODEX_CONTEXT.md` 不再把 0008 当作仓库当前唯一 schema
- [ ] `CURRENT_HANDOFF.md` 区分 Repository / Production
- [ ] `REGRESSION_AND_CHANGE_GUARD.md` 已加入 AI Gateway 已实现契约
- [ ] 未来事项已移出交接正文
- [ ] `manifest.json` 正式文档集合经过核对
- [ ] `COMPLETE_PROJECT_SPEC.md` 已重新生成

## 事实一致性

- [ ] HEAD 一致
- [ ] repository migration head 一致
- [ ] production migration state 没有被猜测
- [ ] pytest 数量与当前运行结果一致
- [ ] frontend test/build 状态一致
- [ ] 没有把自动验证升级为生产验收
- [ ] 没有把未实现 TODO 写成已完成

## 安全与边界

- [ ] 没有 Secret
- [ ] 没有 Cookie
- [ ] 没有 API Key
- [ ] 没有真实用户内容
- [ ] 没有自动启动未来开发
- [ ] 没有不必要重启服务

---

# 13. 建议提交方式

本轮建议只形成一个“文档封板提交”。

建议 commit message：

```text
docs: refresh current freeze and handoff materials
```

如果同时修复 manifest / 生成脚本文档集合：

```text
docs: align freeze manifest and handoff sources
```

不要在这个提交里混入：

```text
AI runtime bug fixes
new GenericProcessor
resource locking
budget logic
UI feature
```

这些属于下一工作包。

---

# 14. 给执行 Agent 的最终指令

```text
你的任务不是继续开发“至简”。

你的任务是把 codex/mac-mini-implementation 当前已经进入仓库的实现，
准确、精简、无夸大地封板成最新交接物料。

必须严格区分：
1. Repository implementation
2. Automated verification
3. Production deployment
4. Real-provider / real-video acceptance

先查事实，再更新源文档，最后生成 COMPLETE_PROJECT_SPEC。

不要实现 POST_FREEZE_TODO_BACKLOG.md 中任何事项。
不要把未来计划写进当前封板。
不要把 0010 仓库迁移头自动写成生产已升级。
不要把 pytest 通过写成真实模型生产验收。
不要为文档封板主动中断健康服务。

完成后只报告：
- 更新了哪些源文档；
- 当前仓库 HEAD；
- repository migration head；
- production state 是否实际读取；
- 当前自动测试基线；
- manifest/source set 是否变化；
- COMPLETE_PROJECT_SPEC 是否重新生成；
- 是否存在仍无法确认的生产事实。
```
