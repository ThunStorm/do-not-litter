# 当前交接

> 本文件只维护任务续接与带日期的生产快照；源码能力和自动验证的唯一来源为 [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)。

## 任务续接

- 更新：2026-09-09。生产 SQLite 已按授权由 0016 升至 0018，API/Worker 已重启并健康；PLAN B B1–B8 已完成于工作树，未提交，新增源码尚未在验证后再次重启加载。
- 已完成：PLAN A 的 Benchmark/探测/SectionFacts 和真实 `PARTIAL_SUCCESS` 样本继续保留；Plan B 完成 10 类 POI Golden、可解释候选门禁、事实归一化、来源去重的共识/冲突与新旧观察、Place Knowledge API/证据跳转、详情知识卡及 Review 上下文。
- 验证：生产库 `integrity_check=ok`、0018 head 与 `source_quote` 已确认；API/首页/Worker 心跳就绪。完整后端 pytest、POI Golden（错误自动确认 0）、目标 Ruff、diff 检查及 Node 22.21.0 前端 verify 通过；桌面 Review 浏览器交互通过，390px 视觉验收未执行。
- 阻塞：ASR、视觉、cache/force-regenerate、fallback、取消/Replay 的真实 Benchmark 证据仍未齐；真实高德/视频及移动视觉验收尚未执行。
- 下一步：由用户决定是否部署 Plan B 源码，并在可用 Browser/Playwright 后补 390px 验收。
- 注意：不自动调用真实高德/视频、改默认路由、确认 POI 或删除模型；真实 Key/Cookie/用户内容不写入交接。

## 生产快照（采样 2026-09-09）

- 已重启 cn.zhijian.api、cn.zhijian.worker；health、首页正文和 Worker 心跳就绪，活跃 Job/lease 为 0。
- SQLite/WAL 为 Alembic 0018（head），`integrity_check=ok`；本轮迁移前逻辑备份为 `data/backups/app-pre-plan-b-20260909.db`。
- 运行时为 Python 3.14.6，/Volumes/D/Library/Application Support/Zhijian/venv/bin/python；LaunchAgent 的 PYTHONPATH 指向仓库 backend/src。精确 Git SHA 未嵌入进程。
- Gateway 的真实 Local/Remote、ASR、视觉、fallback、cache/force-regenerate、预算、取消/Replay 仍须按 [生产验收门禁](ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md) 单独留证；不得以本次健康和单个字幕样本外推。
