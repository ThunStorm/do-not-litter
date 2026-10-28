# 视频最小修复交付报告
V01–V08共8项修复已完成，V09–V12延期。已部署并通过生产只读核验，迁移0026→0027；最终提交推送结果见保存点release-result.json。
- 基线SHA：57df74ab8761223f49acbc9a29a26d0aba2b0b08；源码提交：f4dc52b93e68965be04f4481f0da031e0b8ee5fc。
- 隔离工作树：/Users/williamli/.codex/worktrees/video-minimal-fix/do-not-litter；部署目标：/Volumes/D/Projects/Codework/Git/do-not-litter；保存点：/Volumes/D/Projects/Codework/Git/do-not-litter/data/backups/video-minimal-release-20261028-180824。
- 2026-10-28用户追加授权迁移、重部署、按需重启、目录清理、提交推送；不包含真实LLM/ASR/高德或视频重跑，本次这些调用均0。

|问题|结果|主要改动与证据|
|---|---|---|
|V01|FIXED_VERIFIED|候选/物化字段原句链、数值、否定、不确定性与同段地点归属校验；wp1-before/extra/uncertainty-before.log|
|V02|FIXED_VERIFIED|质量拒绝后继续字幕候选，最多3轨，保留一次ASR回退；wp2-before、cost-before/after.log|
|V03|FIXED_VERIFIED|YouTube仅选择VTT，srv3-only走既有回退；wp2-before.log|
|V04|FIXED_VERIFIED|首次与Replay截图错误共用分类，保留核心、登录NeedsUser、取消传播；wp3-before.log|
|V05|FIXED_VERIFIED|公开gate→入队→缓存消失，不再误报完成；wp3-v05-before.log|
|V06|FIXED_VERIFIED|同NoteVersion/名称/局部Segment证据与已知内容单元、省市一致；wp4-before.log|
|V08|FIXED_VERIFIED|不同站序/条件/来源保留，新路线ID包含条件与Segment；wp4-before/id-before.log|
|V07|FIXED_VERIFIED|每个新笔记版本固定GroundedMap外键，读取同时校验视频/转写；v07-authorized-before.log→v07-after.log；旧xfail移除|

## 最小改动清单
7个生产文件（含1个追加迁移）、5个测试文件，无新增生产模块、依赖、AI阶段、Prompt或缓存键变动。
- resolvers/video/bilibili.py、youtube.py：有界质量选择与VTT格式。
- services/video_support.py：确定性字段证据门禁、生成笔记前校验产物身份并保存固定引用。
- services/video_pipeline.py：字幕质量谓词、截图纯错误分类与缓存缺失的部分成功状态。
- services/route_guides.py：局部站点绑定、条件/来源保留，严格按笔记固定引用读取，不取最新Artifact。
- db/models.py、alembic/versions/0027_note_grounded_map_binding.py：AINoteVersion.grounded_map_artifact_id可空外键，ON DELETE SET NULL；SQLite原地追加列，不重建业务表、不回填历史。
- tests/test_video_minimal_fixes.py：正反例、Mock计数、V07旧版/跨来源/转写/缺绑定及迁移往返。
- tests/test_video_notes.py：为原正例补足菜品/月/时段原句，不放宽断言。
- tests/test_yunnan_multiregion_travel_golden.py：补路线局部证据与固定版本引用；保留全部不同来源路线，继续校验站序/复制/用户路线不变。
- tests/test_grounded_map.py：真实生成路径断言固定引用，原Provider调用总数仍5。
- tests/test_poi_note_structure.py：原无身份SimpleNamespace改为隔离库真实Artifact，保留原包归属/负例断言；全量发现2个旧夹具不满足新身份契约后修复，未放宽生产校验。

## 数据与兼容边界
历史22个笔记版本新增列保持NULL；原字段不变。未知关联不猜绑、不自动重算，今后旧笔记没有可靠绑定时不展示作者路线。发布前生产已有route_guides产物为0，故无既有路线被隐藏。公开API字段/Job状态枚举不变，用户RouteDraft/人工POI不回填或覆盖。截图Replay不重跑模型；新笔记使用的固定Artifact不因后续生成而漂移。旧缓存JSON不强制重解析。

## 目录与追溯
原ZIP按SHA256校验后归档到dev docs/history/planning/ZHIJIAN_VIDEO_MINIMAL_IMPLEMENTATION_AND_AGENT_PROMPT_20261028.zip（d2bc90da770ba73320826ea1f86c083676d11114a2206b846d5d6d9ff858ebc3），不再留在当前计划目录。旧阶段报告保存于发布保存点reports-pre-authorization；本次日志/隔离数据移入offline-evidence，不提交真实数据库或临时依赖。源码指纹见source-hashes.json，生产保存点/提交结果见release-result.json。

## 源码定位
- [backend/src/zhijian/db/models.py:355](/Users/williamli/.codex/worktrees/video-minimal-fix/do-not-litter/backend/src/zhijian/db/models.py:355)
- [backend/src/zhijian/services/video_support.py:2417](/Users/williamli/.codex/worktrees/video-minimal-fix/do-not-litter/backend/src/zhijian/services/video_support.py:2417)
- [backend/src/zhijian/services/route_guides.py:174](/Users/williamli/.codex/worktrees/video-minimal-fix/do-not-litter/backend/src/zhijian/services/route_guides.py:174)
- [backend/alembic/versions/0027_note_grounded_map_binding.py:18](/Users/williamli/.codex/worktrees/video-minimal-fix/do-not-litter/backend/alembic/versions/0027_note_grounded_map_binding.py:18)
