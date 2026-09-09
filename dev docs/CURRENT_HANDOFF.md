# 当前交接

> 本文件只维护任务续接与带日期的生产快照；源码能力和自动验证的唯一来源为 [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)。

## 任务续接

- 更新：2026-09-09。Plan A/B 已提交 `6d88d84`；Plan C C1–C5 已提交 `10b84b6`，尚未部署或重启。
- 已完成：月份/日期 Visit Window 状态、Preference Event、确定性可解释推荐、地图/详情 UI、Visual Fact 独立模型、`VISION_FACT` Stage 与离线 Golden；无图像 Profile 时正确 `SKIPPED_UNSUPPORTED`。
- 验证：全量后端 pytest、空 SQLite 升级至 0019、Ruff、diff 检查及 Node 22.21.0 前端 verify 通过；桌面地图浏览器确认新筛选可见。未调用真实 Provider、高德或视频。
- 阻塞：生产仍采样为 0018；真实 Vision/视频/高德及 390px 视觉验收未执行。
- 下一步：用户确认后部署 0019 与源码，再以真实合法样本分别验收。
- 注意：不自动调用真实高德/视频、改默认路由、确认 POI 或删除模型；真实 Key/Cookie/用户内容不写入交接。

## 生产快照（采样 2026-09-09）

- 已重启 cn.zhijian.api、cn.zhijian.worker；health、首页正文和 Worker 心跳就绪，活跃 Job/lease 为 0。
- SQLite/WAL 为 Alembic 0018（head），`integrity_check=ok`；本轮迁移前逻辑备份为 `data/backups/app-pre-plan-b-20260909.db`。
- 运行时为 Python 3.14.6，/Volumes/D/Library/Application Support/Zhijian/venv/bin/python；LaunchAgent 的 PYTHONPATH 指向仓库 backend/src。精确 Git SHA 未嵌入进程。
- Gateway 的真实 Local/Remote、ASR、视觉、fallback、cache/force-regenerate、预算、取消/Replay 仍须按 [生产验收门禁](ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md) 单独留证；不得以本次健康和单个字幕样本外推。
