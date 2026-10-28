# WP0 隔离基线（首次阶段快照）

后续追加授权已完成V07开发，当前状态见同目录实现/测试报告；下文仅保留最初基线事实。日志最终归档至发布保存点offline-evidence。
- 开始/结束 HEAD：`57df74ab8761223f49acbc9a29a26d0aba2b0b08`；未提交，因此 after_sha 与 before_sha 相同，改动在工作树。
- 原仓库：`/Volumes/D/Projects/Codework/Git/do-not-litter`；开始状态仅用户提供 ZIP 未跟踪，与冻结审计 SHA 一致。没有 reset/stash/clean。
- 隔离工作树：`/Users/williamli/.codex/worktrees/video-minimal-fix/do-not-litter`（detached）；包解压：`/var/folders/k2/yx7m7z457ydcjnyk4dgj2fjr0000gn/T/zhijian-minimal-20261028-zyilzrfp`。06 全文及 01–05 工作包/门禁已读；没有重新做全仓库架构审计。
- 基线：`.video-fix-results/run -m pytest -p no:cacheprovider backend/tests/test_video_notes.py backend/tests/test_yunnan_multiregion_travel_golden.py -q --tb=short`，exit=0，100 项通过；日志 `/Users/williamli/.codex/worktrees/video-minimal-fix/do-not-litter/.video-fix-results/baseline.log`。
- 只读复用原仓库 Python 3.12 venv；PYTHONPATH 优先隔离源码。ENV=development，独立 ZHIJIAN_STORAGE_CONFIG、file Secret Store、临时 SQLite。Python sitecustomize 阻断 IPv4/IPv6 connect；本次未访问生产 API/SQLite/Keychain 或启动服务。
- 原始基线脚本已审阅，未直接运行：避免重复全量及当前 shell Node 包装器问题；采用同等隔离设置的定点基线。最终生产配置单测去掉 ZHIJIAN_DATA_DIR 环境覆盖，默认数据目录仍为本工作树/data；这些单测自行创建 tmp_path 存储配置和数据库。
- 已有修复条目：无；本次 V01–V06/V08 先复现后修复；V07 复现后阻塞，V09–V12 延期。生产与真实 E2E 未运行。
