# 视频开发定位入口

> 本页只做代码定位。旧 961 行工作包与历史验收保存在 [历史指南](../history/VIDEO_AI_NOTE_IMPLEMENTATION_GUIDE.md)，默认不读；原“完整读取八份文档”要求已撤销。

先按 [CODEX_CONTEXT.md](../CODEX_CONTEXT.md) 获取当前状态与相关冻结项，再从 [视频契约索引](VIDEO_AI_NOTE_PIPELINE.md) 选一篇。不要依据旧 WP 的“待实施”重复开发已完成能力。

| 问题 | 目标代码（仓库根相对路径） | 先读契约 |
| --- | --- | --- |
| 登录/字幕/平台限制 | backend/src/zhijian/services/bilibili_auth.py、video_support.py | video/02-input-transcript.md |
| 阶段执行/生成/物化 | backend/src/zhijian/services/video_pipeline.py、video_support.py | video/03-generation-materialization.md |
| 截图 | backend/src/zhijian/services/video_screenshots.py | video/03-generation-materialization.md 的 4.12–4.15 |
| Replay | backend/src/zhijian/services/job_replay.py | jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md |
| 阅读 / 地图 | frontend/src/features/video/VideoNotesPage.tsx、frontend/src/features/map/MapOverviewPage.tsx | 相应 UI 专项；不把概念稿当运行证据 |

测试先按目标模块在 backend/tests、frontend/src 中定位。真实 Provider/视频重跑、生产迁移与重启需要相应授权；纯文档变更不触发。
