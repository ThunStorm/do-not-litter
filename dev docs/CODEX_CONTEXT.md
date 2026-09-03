# 至简 Codex 精简接手页

> 用途：后续 Codex 新任务的默认第一读物。它替代“先读全部文档”和默认加载合订本。

## 一句话

至简是运行在 Mac mini 上的单用户、本地优先信息处理系统。PC/手机通过可信局域网访问 React Web；FastAPI 接入，SQLite/WAL 持久化，独立 Worker 处理招聘与 Bilibili 旅行视频长任务。

## 当前事实

- 文档版本：v0.4.6；唯一实施状态源：`IMPLEMENTATION_STATUS.md`。当前 Git HEAD 为 `5ffaa1c`；未提交工作树须先经 `git status` 确认，不能据此推断已部署提交。
- 部署：`cn.zhijian.api` + `cn.zhijian.worker`，FastAPI 同源提供前端。
- 生产运行时：Python `3.14.6`，固定路径 `/Volumes/D/Library/Application Support/Zhijian/venv`；LaunchAgent 通过 `PYTHONPATH` 读取当前仓库 `backend/src`。
- 仓库 schema head：Alembic `0010`，SQLite/WAL；生产 schema 与服务现场只以 `CURRENT_HANDOFF.md` 的实际快照为准，不能由仓库 head 推断。
- 当前自动验证基线：后端 pytest 88 项、Ruff；Node `22.21.0` 下前端 Vitest 12 项、ESLint、TypeScript、Vite build。
- AI Workload Gateway 已实现阶段策略/路由、质量门禁、Map/Reduce Facts、缓存、预算、Domain Context、Vision 绑定边界和本地资源串行；生产真实模型/视频验收仍单独受门禁约束。
- 主要高危文件：
  - `backend/src/zhijian/api/router.py`
  - `backend/src/zhijian/services/video_pipeline.py`
  - `backend/src/zhijian/services/video_support.py`
  - `backend/src/zhijian/services/job_replay.py`
  - `backend/src/zhijian/db/models.py`
  - `frontend/src/features/tasks/TaskDetailPage.tsx`
  - `frontend/src/features/video/VideoNotesPage.tsx`
  - `frontend/src/styles/global.css`
- 当前工作树可能包含大量未提交实现；改动前先看 `git status`，不得覆盖用户变更。

## 按任务选文档

| 任务 | 必读 | 可选补充 |
| --- | --- | --- |
| 当前状态/交接 | `CURRENT_HANDOFF.md`、`IMPLEMENTATION_STATUS.md` 命中段 | `README.md`、`deploy/macos/README.md` |
| Capture/文件/OCR | `PRODUCT_REQUIREMENTS.md` | `SYSTEM_ARCHITECTURE.md`、`SECURITY_PRIVACY.md` |
| 招聘 | `RECRUITMENT_PIPELINE.md` | `DATA_MODEL.md`、`TESTING_AND_ACCEPTANCE.md` |
| 视频 Pipeline | `VIDEO_AI_NOTE_IMPLEMENTATION_GUIDE.md` | `VIDEO_AI_NOTE_PIPELINE.md` |
| 视频阅读/UI | `VIDEO_NOTE_READING_EXPERIENCE_V042_SPEC.md` | 对应 `design/ui/` 标注稿 |
| Job/取消/重跑 | `PIPELINE_STEP_REPLAY_V044_SPEC.md` | `MOBILE_SESSION_DIAGNOSTICS_AND_JOB_CONTROL_SPEC.md` |
| 模型/Prompt | `AI_RUNTIME_AND_PROVIDERS.md` 或 `PROMPT_SUPPLEMENTS_V045_SPEC.md` | `SECURITY_PRIVACY.md` |
| AI Gateway/路由/Cache/Budget/Domain | `AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md`、`AI_RUNTIME_AND_PROVIDERS.md` | `AI_GATEWAY_PRODUCTION_ACCEPTANCE.md` |
| AI 生产验收 | `CURRENT_HANDOFF.md`、`AI_GATEWAY_PRODUCTION_ACCEPTANCE.md` | `REGRESSION_AND_CHANGE_GUARD.md` |
| 地点/地图 | `TRAVEL_FOOD_PIPELINE.md` | `API_DESIGN.md`、`DATA_MODEL.md` |
| 日志/运维 | `OPERATIONS_UI_SPEC.md` | `LOGGING_ARCHITECTURE.md` |
| 数据库迁移 | `DATA_MODEL.md` | `ARCHITECTURE_DECISIONS.md` |

不要为局部任务读取 `COMPLETE_PROJECT_SPEC.md`。

## 核心 Pipeline

```text
Capture → Source/Job → Resolver → Segment/Evidence → Processor → Content

Video:
VALIDATE_LINK → FETCH_METADATA → FETCH_SUBTITLE → DOWNLOAD_AUDIO → ASR
→ NORMALIZE_TRANSCRIPT → CORRECT_TRANSCRIPT → GENERATE_AI_NOTE
→ EXTRACT_TRAVEL_FACTS → RESOLVE_POI → BUILD_PLACE_NOTES
→ PLAN_SCREENSHOTS → DOWNLOAD_VIDEO_FOR_FRAMES → EXTRACT_SCREENSHOTS
→ MATERIALIZE → CLEAN_CACHE
```

## 状态边界

- Job：QUEUED/RUNNING/NEEDS_USER/COMPLETED/PARTIAL_SUCCESS/FAILED/CANCELLED。
- PARTIAL_SUCCESS 表示流程结束但有补充项，不是仍在运行。
- Replay Options 由后端计算；前端不得指定任意续跑步骤。
- `note_*` 是公开 Note ID，`ntv_*` 是版本 ID。
- raw/corrected Transcript 保持 Segment ID、顺序和时间码不变。
- Marker 隐藏/删除不级联删除 Place/Source/Evidence。

## 低额度命令

定位：

```bash
rg -n "关键词" backend/src frontend/src "dev docs/相关文件.md"
sed -n '起始,结束p' 目标文件
```

目标验证优先；交付前再运行：

```bash
.venv/bin/python -m pytest backend/tests -q
.venv/bin/python -m ruff check backend/src backend/tests
pnpm --dir frontend lint
pnpm --dir frontend test -- --run
pnpm --dir frontend build
git diff --check
```

文档源文件变化时才运行：

```bash
.venv/bin/python scripts/build_complete_project_spec.py
```

## 禁止默认执行

- 读取整个合订本或全部 DOM/AX Tree；
- 真实 Provider 测试、视频重新生成、Job 重跑；
- 为局部改动反复运行全量测试；
- 顺手实施 Future Roadmap；
- 重启有活跃 Job 的 Worker；
- 修改历史迁移、Secret、安全/证据边界。
- 不把 repository migration head 当作 production migration state，也不把 pytest、Browser fixture 或构建通过写成真实 Provider/视频验收。
- 封板后的候选事项只读 `To Do/POST_FREEZE_TODO_BACKLOG.md`，且不自动实施。
