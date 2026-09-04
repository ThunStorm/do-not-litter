# AI Gateway 生产验收与发布门禁

更新日期：2026-09-02。本文件取代已删除的阶段执行计划，保留尚未完成的生产验收边界，不把源码实现误写为生产已验证。

## 已在源码验证

- `LocalAIResourceManager` 使用共享 `data/runtime/local-ai.lock` 的 `flock` 串行化 API 与 Worker 的本地 ASR、文本、视觉及模型测试；进程退出由操作系统释放锁。
- AI Budget 按审计中的 `location` 分别累计 LOCAL/REMOTE Token；缓存命中不计模型调用或 Token 预算，且保留位置与缓存节省用量。
- `scripts/run_ai_benchmark.py` 评估受控真实 E2E 采集的结果；Golden 样本定义在 `benchmark/golden-ai-gateway-samples.json`。它不调用 Provider、不下载视频。

执行已采集数据的发布门禁：

```bash
.venv/bin/python scripts/run_ai_benchmark.py \
  'dev docs/benchmark/golden-ai-gateway-samples.json' real-e2e-runs.json --output benchmark-result.json
```

结果必须同时有 `BASELINE` 与 `CANDIDATE`，并满足：Schema 通过率 >= 0.95、Evidence coverage >= 0.90、严重幻觉为 0、Candidate 的地点/实体召回不低于 Baseline、远程 Token 降幅 >= 50%。平台字幕目标为 >= 70%，ASR 目标为 >= 30%，应在结果记录中分组复核。

## 生产门禁（尚未由本文件宣称完成）

生产迁移前确认无 `QUEUED/RUNNING` Job 或 lease，备份 SQLite，并执行 `PRAGMA integrity_check`。当前数据库须为 `0010 (head)`；迁移或重启只通过 `deploy/macos/manage.py`，不得以临时开发服务替代 LaunchAgent。

真实 E2E 必须分别留存：本地 Ollama text/JSON/structured output、一个已配置远程 Provider、LOCAL_ONLY/REMOTE_ONLY/LOCAL_FIRST/REMOTE_FIRST/AUTO 路由、跨进程 ASR 与模型测试等待、缓存与 force-regenerate、低预算拦截、AI 阶段取消与 Replay、一个平台字幕视频及一个 ASR 视频。未配置的 Key、Cookie、模型或可访问样本是明确的外部条件，不能以 Mock 或空记录替代。

通过所有门禁前，禁止声明 “AI Workload Gateway Production Proven”，也不启动 GenericProcessor、Source Watch、RAG、Multi Worker、Cloud Worker 或高风险自动操作。
