# 当前交接

> 本文件只维护任务续接与带日期的生产快照；源码能力和自动验证的唯一来源为 [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)。

## 任务续接

- 更新：2026-09-13。UI/视频/POI V2 的 `0021`（Note Profile）与 `0022`（FTS5）已生产迁移、重启；备份 `data/backups/app-pre-ui-video-poi-v2-20260913-125600.db` 完整性 ok。
- 已完成：API/Worker/首页/心跳 READY，生产 revision `0022`、FTS 表存在，active Job/lease 在迁移前为 0；现有 1 条 Note 的全文索引回填及 2 字中文标题搜索通过。
- 已修复：重复 Capture 命中既有 canonical VideoAsset 时，Job 改绑资产原 Source 并清理无引用的新 Source；异常审计按 UTC 归一化时间后再筛选。目标与全量后端、Ruff、Node 24 前端 verify、`diff --check` 通过，生产重启后 Source/Asset 实读一致且空 Source 已删除。
- 用户样本 `BV19sbV6eExE`：切换 Key 后从 `EXTRACT_TRAVEL_FACTS` Replay 成功，最终 `PARTIAL_SUCCESS`；已生成 Note version 2、9 张 READY 截图，FTS 命中新 Note，所有步骤完成且无失败/跳过。45 个 POI 为 REVIEW/UNRESOLVED，confirmed=0，未自动确认。
- 已完成：COMPACT Profile Replay 产生 current Note version 7（6 章节均带 Evidence、7 张 READY 截图）；同 Profile 二次 Replay 的三个分块 Cache Hit 均为 0ms；force-regenerate 真实绕过命中，新增 Cache result chain。Local Video 上传入口/Adapter/ASR 已由同一视频轨+音频轨合成 MP4 验证，后续本地校对超时。
- 未验证/条件缺口：无 image-capable Profile，Vision 不可跑；无授权的六类 ASR corpus，CPU fallback Benchmark 未跑；无有效 Browser/Playwright runtime（Computer Use 初始化超时），390px 未验；POI AUTO_STRONG 需要用户审核真实候选后才能晋级；fallback 需可用主备 Profile 和一次受控失败。本轮不再发起模型/视频 Job。
- 下一步：用户在视频笔记或 `/place-reviews` 审核 45 个 POI；补齐 Vision Profile、ASR corpus 或 Browser runtime 后再单独验收。不得重跑已完成媒体/ASR/校对，不改历史 Source/Transcript/Note/Evidence。

## 生产快照（采样 2026-09-13）

- 2026-09-13 已重启 cn.zhijian.api、cn.zhijian.worker；health、首页正文和 Worker 心跳 READY。迁移前 active Job/lease=0，SQLite/WAL `integrity_check=ok`。
- SQLite/WAL 实读 Alembic 0022（head），`video_note_search` 已存在；本次升级前逻辑备份为 `data/backups/app-pre-ui-video-poi-v2-20260913-125600.db`，完整性为 ok。
- 运行时为 Python 3.14.6，/Volumes/D/Library/Application Support/Zhijian/venv/bin/python；LaunchAgent 的 PYTHONPATH 指向仓库 backend/src。精确 Git SHA 未嵌入进程。
- 2026-09-13 修复后再次重启；API/Worker/首页/心跳 READY，生产 `integrity_check=ok`、active Job/lease=0。真实样本已证明下载、ASR、校对、抽取、Note、POI Review、截图和 FTS 交付；仍不外推为 Vision、Profile 切换、fallback、cache/force-regenerate、预算或 Browser/390px 验收。
- 2026-09-14：Evidence Index 改为稳定 Mention ID 顺序，部署后真实验证 COMPACT Profile、Cache Hit 与 force-regenerate；API/Worker/心跳 READY。Local Video 只验证至 ASR，后续本地校对超时；本轮不再重试。
