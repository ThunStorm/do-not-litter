# 测试结果
生产同版本Python3.14.6、只读复用venv；测试在隔离工作树/临时SQLite/file Secret Store，Python网络connect由sitecustomize阻断。发布探测另外仅访问本机API，不使用离线阻网runner。

|检查|exit|结果与日志（offline-evidence内）|
|---|---:|---|
|初期基线 video_notes+yunnan|0|100通过；baseline.log|
|V01–V08最小反例，修前|1（预期）|各wp*-before、v07-authorized-before.log；V07已移除xfail|
|V07生产Python目标回归|0|98项通过；v07-targets.xml/v07-after.log|
|旧夹具修正后最终目标：poi_note_structure+video_minimal_fixes+grounded_map|0|v07-final-target.log|
|生产Python后端全量（初次）|1|仅poi_note_structure的2个无身份SimpleNamespace夹具失败；v07-full.log|
|生产Python后端全量（最终）|0|745项通过，失败0，跳过0，156.115秒；v07-final-full.xml/log|
|Ruff backend/src+tests+0027|0|v07-ruff.log|
|pnpm --dir frontend run verify|0|ESLint、59 Vitest、TS和隔离构建；v07-frontend.log|
|云南 --output v07-yunnan.json|0|46测试/29断言；v07-yunnan.json/log|
|生产DB副本升级0027→降级0026→再升级0027|0|44张业务表原字段内容与数量逐表哈希不变，integrity=ok/FK0；migration-copy/report.json|
|0027单测|0|旧笔记字段保真/新增NULL、非法外键拒绝、降级还原，再升级通过|
|文档链接/合订本生成一致性/git diff --check|0|交付前核对|

此前3.12阶段的预期失败、740通过+V07 xfail等证据原样保留，仅用于追溯，不计为本次3.14全量。前端既有>500KB chunk警告和TestClient弃用警告保留。初期pnpm离线缓存不完整曾自动补51依赖包；本轮verify使用隔离依赖，未改生产venv/node_modules。

## 生产核验
开发/隔离验证完成，待发布门禁；尚未迁移生产、提交或推送。
保存点：/Volumes/D/Projects/Codework/Git/do-not-litter/data/backups/video-minimal-release-20261028-180824；离线日志最终位置：/Volumes/D/Projects/Codework/Git/do-not-litter/data/backups/video-minimal-release-20261028-180824/offline-evidence。初次错误地用阻网runner执行本机manage.status导致探测被拒绝，已改为直接生产Python只读核验；不是服务故障。
生产发布守卫：入口关闭前/后两次空闲检查；无任务/lease/在途调用；已验逻辑备份；0026→0027后全部44表原字段哈希不变；新API/Worker首页与心跳READY、旧新HTTP静态哈希相同；允许的启动事件及正常Artifact过期另记保存点。
真实模型、视频语义E2E和真实POI质量仍NOT_RUN_REAL_E2E。无前端源码/布局变更，本轮未重复Browser测试；生产HTTP与相关API只读核验不冒充Browser或模型质量验收。
