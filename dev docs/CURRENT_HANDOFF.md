# 当前交接

> 本文件只维护任务续接与带日期的生产快照；源码能力和自动验证的唯一来源为 [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)。

## 任务续接

- 更新：2026-09-10。字幕一致性 P0 已提交并部署：AI 字幕只审计、不作权威转写，强制 Whisper ASR；生成前校验 Source、BV/CID、Snapshot、状态与时间轴，Ollama 校对每批至多 32 段。
- 已完成：真实串行重放两条污染视频；`note_d0a…`、`note_dcd…` 均切至 Transcript/Note v2，来源 `WHISPER_CPP_ASR/LOCAL_ASR`，摘要已去除电影解说/兴趣自述污染。前者 `PARTIAL_SUCCESS` 仅有 2 个 POI 待确认；后者的 Note、地点和章节完成。
- 验证：目标 Ruff、视频相关 36 项、后端全量 117 项、Node 24 前端 verify、`diff --check`；生产 revision 0019、完整性/服务/心跳 READY、无活跃 Job/lease。备份 `data/backups/app-pre-transcript-alignment-20260910-153500.db` 已校验。
- 未完成：第二条在非核心 `DOWNLOAD_VIDEO_FOR_FRAMES` 协作取消，新截图与列表 ContentItem 物化未完成；不得为此盲目完整重放或原地篡改历史版本。
- 下一步：仅在用户允许真实视频/模型调用后，走受支持恢复路径补第二条截图/列表物化；P1 抽样验证暂缓，当前完整 ASR 用时可接受。
- 注意：真实 Provider 串行并尊重 QPS；不写入 Key/Cookie，不删历史 Transcript/Note/Evidence，不迁移数据库或改默认路由。

## 生产快照（采样 2026-09-10）

- 2026-09-10 已重启 cn.zhijian.api、cn.zhijian.worker；health、首页正文和 Worker 心跳 READY，活跃 Job/lease 为 0。
- SQLite/WAL 实读 Alembic 0019（head），`integrity_check=ok`；本轮部署前逻辑备份为 `data/backups/app-pre-transcript-alignment-20260910-153500.db`，其完整性与 revision 均已复核。本次未跑 migration。
- 运行时为 Python 3.14.6，/Volumes/D/Library/Application Support/Zhijian/venv/bin/python；LaunchAgent 的 PYTHONPATH 指向仓库 backend/src。精确 Git SHA 未嵌入进程。
- Gateway 的真实 Local/Remote、ASR、视觉、fallback、cache/force-regenerate、预算、取消/Replay 仍须按 [生产验收门禁](ai-gateway/AI_GATEWAY_PRODUCTION_ACCEPTANCE.md) 单独留证；不得以本次健康和单个字幕样本外推。
