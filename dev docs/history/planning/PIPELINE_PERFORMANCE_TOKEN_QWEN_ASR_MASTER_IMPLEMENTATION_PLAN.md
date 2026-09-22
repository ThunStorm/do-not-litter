# PIPELINE_PERFORMANCE_TOKEN_QWEN_ASR_MASTER_IMPLEMENTATION_PLAN.md

> 归档状态：WP0–WP8 已实施并部署；真实 Frozen Benchmark 与默认晋级仍按外部验收门禁执行。

> 项目：`ThunStorm/do-not-litter`
> 分支：`codex/mac-mini-implementation`
> 类型：运行时性能 / LLM Token / Qwen3-ASR 合并实施主计划
> 适用对象：Codex / Agent
> 目标机器：Mac mini M4 / 16 GB 统一内存
> 核心原则：**不重复建设、不破坏现有 Evidence/Replay/Stage Policy、先 Benchmark 后切默认、优先减少调用而不是单纯更换模型。**

---

# 0. 本计划的作用

本文件取代“单独执行 Qwen-ASR 计划”和“单独执行 Pipeline 性能 / Token 优化计划”的做法。

从本文件开始，后续实施只遵循这一条主线：

```text
真实性 / Evidence
        ↓
ASR 输入质量
        ↓
Transcript Quality Gate
        ↓
最小化 Correction
        ↓
Canonical Grounded Artifact
        ↓
最大化 Artifact Reuse
        ↓
最小化 LLM 输入 / 重试 / fallback
        ↓
POI 与 Screenshot 确定性性能优化
        ↓
更快交付 First Useful Note
```

禁止让两个 Agent 分别按照旧计划修改同一模块。

---

# 1. 合并后的核心结论

当前最合理的目标不是：

```text
Whisper.cpp
→
Qwen3-ASR
```

也不是：

```text
继续优化 Prompt
→
希望 Token 自动下降
```

而是：

```text
可信平台字幕
    │
    └───────────────┐
                    │
无字幕 / 不可信字幕 │
    ↓               │
Qwen3-ASR / Whisper │
    ↓               │
统一 Transcript ────┘
    ↓
Provider-independent Transcript Quality Gate
    ↓
┌────────────────────────┐
│                        │
Clean                  Suspect
│                        │
│              target + minimal neighbors
│                        ↓
│                Delta Correction
│                        │
└────────────┬───────────┘
             ↓
Canonical Corrected Transcript
             ↓
Canonical Grounded Map / Evidence
             ↓
┌────────────┼────────────────┐
│            │                │
Place      Note Reduce      Search / UI
│
AMap Resolver
             ↓
Core Materialize
             ↓
Non-core Screenshot / enrichment
```

Qwen-ASR 的价值不是单纯提高 CER，而是：

```text
更准确的地点 / 店名 / 菜名 / 方言
→
更少可疑 Segment
→
更少 CORRECT_TRANSCRIPT 输入
→
更稳定地点抽取
→
更高 POI 命中
→
更少人工确认
→
更低 Token + 更低总延迟
```

---

# 2. 已验证的当前仓库状态

以下能力已经存在，**不得重复实现**。

## 2.1 ASR

现有：

```text
backend/src/zhijian/providers/asr.py

WHISPER_CPP
WHISPER_CPP_CPU
ASRProviderRegistry
```

现有接口：

```python
transcribe(media: Path) -> tuple[str, list[dict]]
```

Segment 至少包含：

```json
{
  "text": "...",
  "start_ms": 0,
  "end_ms": 1000,
  "locator": {}
}
```

当前默认：

```text
whisper.cpp
ggml-base.bin
```

---

## 2.2 ASR Benchmark 框架

仓库已经存在：

```text
scripts/run_asr_benchmark.py
scripts/benchmark_asr_providers.py
```

并已经预留：

```text
WHISPER_CPP_BASE
WHISPER_CPP_LARGE_V3_TURBO_Q5
SENSEVOICE_SHERPA_ONNX_INT8
QWEN3_ASR_MLX_0_6B
```

Qwen Benchmark 已支持：

```text
DEFAULT
WITH_CONTEXT
```

以及：

```text
place_entity_recall
proper_noun_accuracy
CER
segment_coverage
timestamp_alignment
RTF
peak_memory
context_gain
```

因此本计划 **不新增第二套 ASR Benchmark Runner**。

---

## 2.3 Transcript Quality

已有：

```text
backend/src/zhijian/ai/transcript_quality.py
backend/src/zhijian/services/transcript_validation.py
```

当前已有：

```text
correction_candidates(...)
assess_transcript_quality(...)
```

但当前逻辑仍带有 Whisper-specific 判断：

```text
"WHISPER" in source_kind
```

非 Whisper ASR 可能被保守地整段送入 Correction。

本计划修改现有门禁，不新增：

```text
asr/quality.py
SecondTranscriptQualityEngine
```

---

## 2.4 Correction 的可靠性能力

当前已经具备：

- 分块；
- 输出截断识别；
- 截断后二分；
- 子批成功立即提交；
- Replay 跳过已处理 Segment；
- model-specific runtime hint；
- Provider 错误分类；
- 429 / quota / policy block 区分；
- Stage Policy；
- Provider fallback；
- Budget；
- Cache；
- ExternalCallAudit。

因此禁止重新实现：

```text
新的 Retry Engine
新的 Circuit Breaker
新的 Scheduler
新的 Token Audit 表
新的 Replay 系统
```

若需优化，只扩展现有：

```text
zhijian.ai.reliability
zhijian.ai.gateway
zhijian.ai.stage_decision
zhijian.ai.cache
ExternalCallAudit
```

---

## 2.5 Replay

完整重跑已经复用原 Job ID。

本计划不新增：

```text
Replay V2
NewJobOnReplay
ASR-specific Replay
```

---

## 2.6 Grounded Evidence

当前视频质量体系已经演进为：

```text
Transcript
→ independent place / fact scan
→ Grounded Evidence
→ Note Map / Reduce
→ POI
```

本计划**不恢复旧方案**：

```text
先生成 Note
→ 再从 Note 猜地点
```

也不再采用旧 Token 审计里“简单把地点抽取并入 Note Generation”的方案。

原因：

> 地点召回必须独立覆盖完整校对 Transcript，不能为了省一次调用牺牲 Recall。

正确优化方向是：

```text
独立语义扫描保留
+
Grounded Artifact 复用
+
Compact Evidence
+
Reduce 不重新读取整篇 Transcript
```

---

# 3. 冲突消解结果

本计划已经做以下统一决定。

| 冲突项 | 最终决定 |
|---|---|
| 是否新增 `ASRResult` 数据类 | **不新增**。继续使用现有 `(text, segments)` Contract，避免重构 Pipeline |
| 是否新增独立 ASR Quality 模块 | **不新增**。扩展 `transcript_quality.py` / `transcript_validation.py` |
| 是否新增 ASR Resource Manager | **不新增**。继续使用 `local_ai_resource_manager` / 现有本地 AI 锁 |
| 是否新增 Benchmark Runner | **不新增**。复用 `run_asr_benchmark.py` 与 `run_video_benchmark.py` |
| 是否让 Qwen 失败后自动再跑 Whisper 做质量比较 | **不允许**。Fallback 只处理运行失败，不做双 ASR |
| 是否删除 Whisper | **不删除**。继续作为稳定 fallback |
| 是否把 Place Extraction 合并进 Note 生成 | **不合并**。保留独立地点 / Fact 扫描 |
| 是否新增 StageDecisionEngine | **不新增**。扩展现有 `decide_stage()` |
| 是否重新实现截断二分 | **不重新实现**。只优化避免不必要的 fallback / 全文重发 |
| 是否单独建立 LLM Usage 表 | **不新增**。继续聚合 `ExternalCallAudit` |
| 是否让 LLM 生成 ASR Hotword | **禁止** |
| 是否默认 Qwen 1.7B | **否**。首期只测试 0.6B |
| 是否立刻把 Qwen 设为默认 | **否**。必须通过 Benchmark / E2E Gate |
| 是否把 Qwen 依赖装进主 Backend venv | **否**。使用隔离 Runtime |
| 是否让 Qwen / Ollama 同时抢统一内存 | **否**。继续 `gpu_heavy_concurrency = 1` |

---

# 4. 最终性能目标

本轮同时优化：

```text
ASR Quality
LLM Prompt Token
LLM Completion Token
Retry Amplification
Fallback Amplification
Pipeline Wall Time
Time To First Useful Note
AMap Requests
Screenshot Subprocesses
Replay Cost
```

最终追踪：

```text
tokens/job
tokens/video-minute
prompt_tokens
completion_tokens
remote_prompt_tokens
local_prompt_tokens

correction_candidate_segments
total_segments
correction_coverage_ratio
correction_input_chars
transcript_chars
unchanged_correction_ratio

ground_map_input_chars
ground_map_chunk_count
ground_map_retry_count

model_attempts
retry_amplification
fallback_amplification
cache_hits
artifact_reuse_count

asr_runtime_ms
asr_rtf
asr_peak_memory
asr_place_recall
asr_proper_noun_accuracy
asr_timestamp_alignment

amap_request_count
amap_cache_hit_count

screenshot_process_count
screenshot_stage_ms

pipeline_wall_time
time_to_first_useful_note
```

---

# 5. 实施优先级

只保留三层。

## P0 — 必须先完成

```text
WP0  Baseline + Observability Freeze
WP1  Qwen3-ASR Runtime + Real Benchmark
WP2  Production Qwen Provider（非默认）
WP3  Provider-independent Quality Gate + Correction v2
WP4  Retry / Truncation / Chunk Token Amplification 优化
```

## P1 — 在 P0 稳定后

```text
WP5  Grounded Artifact Reuse + Compact Evidence
WP6  AMap Cache + Bounded Concurrency
WP7  Screenshot Batch + Core-first Materialization
WP8  Unified E2E Graduation
```

## P2 — 条件性

```text
Qwen3-ASR 1.7B
Cloud ASR
更复杂 ASR Auto Router
更激进的 Local/Remote 自动模型策略
Vision 与 ASR 并行调度
```

P2 不进入当前默认实施范围。

---

# 6. WP0 — Baseline + Observability Freeze

## 目标

在修改 ASR 和 Correction 前得到冻结基线。

禁止先改代码后“凭感觉”判断变快。

---

## 6.1 复用现有工具

优先复用：

```text
scripts/run_asr_benchmark.py
scripts/benchmark_asr_providers.py
scripts/run_video_benchmark.py
scripts/run_ai_e2e_harness.py
scripts/benchmark_ai_profiles.py
ExternalCallAudit
```

不要再增加：

```text
run_pipeline_benchmark_v2.py
run_qwen_pipeline_benchmark.py
token_benchmark_new.py
```

---

## 6.2 Baseline 数据集

至少准备：

```text
短视频：5～10 分钟
中视频：20～30 分钟
长视频：45～60 分钟
```

优先旅行 / 探店。

至少覆盖：

```text
高质量平台字幕
Whisper ASR
快速连续地点
复杂地名
餐馆 / 菜品
BGM
方言 / 口音
多地点
无地点
```

不要用生产历史污染结果直接作为 Ground Truth。

---

## 6.3 Baseline 输出

每个 Job 输出：

```json
{
  "video_minutes": 0,
  "transcript_chars": 0,

  "prompt_tokens": 0,
  "completion_tokens": 0,

  "correction_candidate_segments": 0,
  "total_segments": 0,
  "correction_input_chars": 0,

  "ground_map_input_chars": 0,
  "ground_map_chunks": 0,

  "model_attempts": 0,
  "retries": 0,
  "fallbacks": 0,

  "amap_requests": 0,
  "screenshot_processes": 0,

  "pipeline_wall_ms": 0,
  "time_to_first_useful_note_ms": 0
}
```

---

## 6.4 只扩展现有 Audit

如果字段已有：

```text
ExternalCallAudit.request_meta_json
ExternalCallAudit.response_meta_json
SystemEvent
JobStep.output_json
```

则直接使用。

不要为了方便统计立即新增数据库表。

---

## 6.5 Definition of Done

- [ ] 至少一个短 / 中 / 长视频基线。
- [ ] 能看到每 Stage Token。
- [ ] 能区分 retry 与 fallback。
- [ ] 能统计 Correction Coverage。
- [ ] 能统计 Ground Map chunk。
- [ ] 能统计 AMap request。
- [ ] 能统计 Screenshot subprocess。
- [ ] 能得到 Pipeline Wall Time。
- [ ] 能得到 Time To First Useful Note。
- [ ] 基线 JSON 可重复运行。

---

# 7. WP1 — Qwen3-ASR Runtime + Real Benchmark

## 目标

完成仓库已经预留但尚未真正落地的：

```text
QWEN3_ASR_MLX_0_6B
```

真实 Runtime。

---

## 7.1 不重写 Benchmark

已有 `CommandBenchmarkAdapter` 支持：

```text
--adapter-command PROVIDER=COMMAND
```

因此只新增一个统一 Runtime Runner：

```text
scripts/qwen_asr_runner.py
```

Benchmark 与 Production 都调用这一份 Runner。

禁止分别写：

```text
benchmark_qwen_runner.py
production_qwen_runner.py
```

---

## 7.2 Runtime 隔离

建议：

```text
data/runtime/qwen-asr/
├─ venv/
└─ runtime.json
```

模型：

```text
data/models/qwen-asr/
```

主 Backend：

```text
backend/pyproject.toml
```

不要添加：

```text
torch
transformers
mlx
qwen-asr
```

除非以后明确决定 Runtime 内嵌。

---

## 7.3 Apple Silicon Backend

第一轮以：

```text
Qwen3-ASR 0.6B
+
Apple Silicon MLX Runtime
```

作为 Benchmark Candidate。

注意：

> MLX Runtime 属于 Qwen 权重的 Apple Silicon 实现层，不等同于 Qwen 官方 PyTorch / vLLM inference framework。

因此 Runtime 必须：

```text
固定 package version
记录 backend_id
记录 model_id
记录 runtime version
```

Benchmark 通过后才能进入 Production Provider。

---

## 7.4 Runner Contract

输入：

```text
audio path
context
timestamps=true
```

输出 stdout 必须只有 JSON：

```json
{
  "text": "...",
  "language": "Chinese",
  "model": "Qwen/Qwen3-ASR-0.6B",
  "backend": "mlx-qwen3-asr",
  "segments": [
    {
      "text": "...",
      "start_ms": 1000,
      "end_ms": 4200,
      "confidence": null,
      "locator": {
        "method": "qwen3-asr",
        "model": "Qwen/Qwen3-ASR-0.6B"
      }
    }
  ],
  "metrics": {
    "model_load_ms": 0,
    "asr_runtime_ms": 0,
    "alignment_runtime_ms": 0,
    "peak_memory_bytes": 0
  }
}
```

stderr 可写诊断日志。

禁止日志混入 stdout。

---

## 7.5 时间码是硬门槛

下游依赖：

```text
Evidence
Bilibili timestamp link
Screenshot
PlaceMention
Section range
```

因此 Qwen 不允许只返回整篇文字。

必须保证：

```text
segments[i].start_ms
segments[i].end_ms
```

满足：

```text
start >= 0
end >= start
单调不逆序
最后时间不异常超出视频时长
```

时间对齐失败视为：

```text
QWEN_ASR_ALIGNMENT_FAILED
```

生产阶段可 fallback Whisper。

禁止平均分配时间。

---

## 7.6 Context 来源

允许：

```text
VideoAsset.title
平台 tags
平台 description 中确定存在的专名
用户人工确认过的 Canonical Place aliases
静态 Domain Dictionary
```

禁止：

```text
LLM 猜出来的地点
未确认 POI 候选
后续 Note 自动总结结果
模型根据常识扩展的地名
```

否则形成 Evidence feedback loop：

```text
LLM 猜地点
→
ASR 被诱导
→
Transcript 看起来“证明”该地点
```

这是明确禁止的。

---

## 7.7 Benchmark Context 只使用 Manifest

WP1 仍属于 Benchmark 阶段，因此禁止提前修改生产视频 Pipeline 来构建 Context。

直接复用现有 `run_asr_benchmark.py` 已支持的：

```text
manifest.samples[].context_hints
```

完成：

```text
QWEN3_ASR_MLX_0_6B DEFAULT
vs
QWEN3_ASR_MLX_0_6B WITH_CONTEXT
```

此阶段不得新增生产 `asr_context.py`，也不得从生产数据库自动读取地点词表。

生产可信 Context Builder 延后到 WP2，与 Production Provider 一起接入。

---

## 7.8 复用现有 Benchmark

运行：

```text
WHISPER_CPP_BASE
vs
QWEN3_ASR_MLX_0_6B DEFAULT
vs
QWEN3_ASR_MLX_0_6B WITH_CONTEXT
```

本轮以用户明确的 Qwen 集成为目标，不要求再次扩张到大量其它 ASR。

Whisper Turbo / SenseVoice 只有在：

```text
Qwen 没有明显收益
或
Qwen 资源不可接受
```

时作为 Challenge Candidate。

不要把 ASR 选型演变成长期模型大赛。

---

## 7.9 Benchmark Gate

Qwen 要进入 Production Registry，至少满足：

```text
failure_count <= Whisper Base
place_entity_recall >= Whisper Base
proper_noun_accuracy >= Whisper Base
timestamp_alignment 无显著回退
无明显长视频 drift
无 OOM
无不可接受 swap
```

Context 模式额外要求：

```text
context_gain > 0
false_hotword_insertions 不增加关键错误
```

---

## 7.10 Definition of Done

- [ ] `qwen_asr_runner.py` 可独立执行。
- [ ] Benchmark Adapter 可直接调用同一 Runner。
- [ ] 0.6B 完整跑通。
- [ ] Context / no Context 对照完成。
- [ ] 时间码验证完成。
- [ ] Peak RAM / RTF 有数据。
- [ ] 20～30 个 clip 至少覆盖真实业务类别。
- [ ] 至少 2 个长视频 / 完整视频。
- [ ] 输出既有 `ASR_BENCHMARK_REPORT.md`。
- [ ] 不修改生产默认 ASR。

---

# 8. WP2 — Production Qwen Provider

## 目标

在 Benchmark 通过后，将 Qwen 注册为可选 Production ASR。

---

## 8.1 修改文件

主要：

```text
backend/src/zhijian/providers/asr.py
backend/src/zhijian/core/config.py
backend/src/zhijian/services/video_pipeline.py
backend/tests/
```

Runner：

```text
scripts/qwen_asr_runner.py
```

---

## 8.2 Provider

新增：

```python
class Qwen3ASRProvider:
    provider_id = "QWEN3_ASR"
```

内部：

```text
Backend
↓
subprocess
↓
isolated qwen runtime
↓
JSON
↓
validate
↓
existing transcript tuple contract
```

返回仍然：

```python
(text, segments)
```

不新增 `ASRResult`。

---

## 8.3 Protocol 小幅扩展

为支持 Context，可把接口扩展为：

```python
def transcribe(
    self,
    media: Path,
    *,
    context: str | None = None,
) -> tuple[str, list[dict]]:
    ...
```

Whisper：

```text
忽略 context
```

Qwen：

```text
使用 context
```

这是允许的最小接口变化。

---

## 8.4 生产可信 Context Builder

在 Production Provider 接入时新增：

```text
backend/src/zhijian/services/asr_context.py
```

职责仅限：

```text
trusted metadata
→ normalize / dedupe / limit
→ ASR context text
→ context hash
```

允许来源：

```text
VideoAsset.title
平台 tags
平台 description 中确定存在的专名
用户人工确认过的 Canonical Place aliases
静态 Domain Dictionary
```

禁止来源：

```text
LLM 猜出来的地点
未确认 POI 候选
Note 自动总结
常识补全
```

该模块不负责质量判断、POI Resolve 或任何 LLM 调用。

---

## 8.5 Transcript Metadata

Pipeline 保存：

```text
provider_id
model_id
backend_id
runtime_version
context_hash
context_source_types
language
alignment_method
```

优先放现有：

```text
Transcript.metadata_json
JobStep.output_json
ExternalCallAudit
```

首期不新增 Schema。

---

## 8.6 Fallback

允许：

```text
QWEN3_ASR
↓ runtime failure
WHISPER_CPP
```

仅以下情况触发：

```text
runtime unavailable
model missing
runner crash
OOM
empty transcript
alignment failure
invalid timestamp contract
```

禁止：

```text
Qwen 结果看起来“不够好”
→ 再完整跑一次 Whisper
→ 两份全文比较
```

否则长视频耗时翻倍。

---

## 8.7 本地资源锁

继续：

```text
local_ai_resource_manager.run("ASR", ...)
```

不要新建：

```text
QwenResourceManager
MLXLock
```

Qwen结束后 Runner 必须退出。

之后才允许 Ollama 进入 GPU-heavy 阶段。

---

## 8.8 Settings

Benchmark Gate 通过后，Settings 增加：

```text
本地 ASR

Whisper.cpp
Qwen3-ASR 0.6B
```

如果 Qwen 性能较重：

```text
Qwen3-ASR 0.6B
高质量 · 较高资源
```

默认值仍由 Benchmark 决定，不在代码实现时擅自切换。

---

## 8.9 Tests

至少：

```text
qwen_provider_parses_runner_json
qwen_provider_rejects_empty_text
qwen_provider_rejects_invalid_timestamps
qwen_provider_passes_context
qwen_failure_falls_back_to_whisper
qwen_quality_does_not_trigger_second_asr
whisper_path_unchanged
asr_resource_lock_is_shared
```

---

# 9. WP3 — Provider-independent Quality Gate + Correction v2

这是整个合并计划中最重要的 Token 工作包。

---

## 9.1 当前问题

现有：

```text
WHISPER source
→ semantic candidate + neighbor correction

其它未知 ASR
→ conservative full correction
```

Qwen 加入后，如果不修改，会出现：

```text
更强 ASR
↓
反而整篇送 LLM
```

这是明确的反目标。

---

## 9.2 修改现有 `correction_candidates`

文件：

```text
backend/src/zhijian/ai/transcript_quality.py
```

禁止：

```python
if "WHISPER" in kind:
```

作为核心质量语义。

改为：

```text
source_class
provider_id
confidence availability
text anomaly
semantic criticality
neighbor relation
```

Provider-specific 只能作为输入特征，不应决定整个策略。

---

## 9.3 统一 Source Classes

内部可归一：

```text
TRUSTED_HUMAN_SUBTITLE
GENERATED_PLATFORM_SUBTITLE
LOCAL_ASR_WITH_CONFIDENCE
LOCAL_ASR_WITHOUT_CONFIDENCE
```

对应：

```text
TRUSTED_HUMAN_SUBTITLE
→ 默认 0 candidate

GENERATED_PLATFORM_SUBTITLE
→ 按门禁或回退 ASR

LOCAL_ASR_WITH_CONFIDENCE
→ low confidence + semantic suspicious

LOCAL_ASR_WITHOUT_CONFIDENCE
→ deterministic anomaly + semantic critical candidate
```

不要通过字符串猜：

```text
WHISPER
QWEN
SENSEVOICE
```

---

## 9.4 Candidate Features

首期只用确定性特征：

```text
空文本
乱码
重复
过短异常
过长异常
confidence 低
数字异常
月份 / 价格 / 时间语义
地点后缀
餐馆 / 酒店 / 景区语义
重复同音候选
邻近 Segment 语言模式突变
```

不要在 Quality Gate 再调用 LLM。

---

## 9.5 target 与 context 分离

当前 neighbor Segment 可能一起成为需要模型返回的 target。

改为：

```text
Target Segment
+
before neighbors（只读）
+
after neighbors（只读）
```

Payload：

```json
{
  "video_title": "...",
  "items": [
    {
      "target": {
        "id": "seg-2",
        "text": "..."
      },
      "context_before": [
        {"id": "seg-1", "text": "..."}
      ],
      "context_after": [
        {"id": "seg-3", "text": "..."}
      ]
    }
  ]
}
```

模型不需要返回 context。

---

## 9.6 Delta Correction Output

旧：

```json
{
  "segments": [
    {
      "id": "...",
      "corrected_text": "即使完全不变也重新输出",
      "confidence": 0.9,
      "reason": "..."
    }
  ]
}
```

新：

```json
{
  "changes": [
    {
      "id": "seg-2",
      "corrected_text": "需要修改的文本",
      "reason": "专名"
    }
  ]
}
```

规则：

```text
未出现在 changes 的 target
=
UNCHANGED
```

这样降低 Completion Token。

---

## 9.7 必须保留的安全约束

Correction 不得：

```text
增加新事实
修改时间码
修改 Segment ID
删除 Segment
合并 Segment
拆 Segment
根据常识补地点
```

地名无法确定：

```text
保留原文
+
REVIEW / low confidence
```

而不是强行纠正。

---

## 9.8 Correction Metrics

必须记录：

```text
total_segments
candidate_segments
candidate_ratio

target_chars
context_chars
transcript_chars

changes_count
unchanged_target_count

input_tokens
output_tokens
```

重点：

```text
correction_coverage_ratio
=
candidate_segments / total_segments
```

以及：

```text
correction_input_ratio
=
target_chars + context_chars
/
transcript_chars
```

---

## 9.9 StageDecision

继续使用：

```text
decide_stage("TRANSCRIPT_CORRECTION", ...)
```

结果：

```text
REUSE
SKIP
RUN
```

候选为 0：

```text
SKIP
```

已有相同 corrected artifact：

```text
REUSE
```

不要新增新的 Decision Engine。

---

## 9.10 Tests

必须覆盖：

```text
trusted_subtitle_skips_correction
qwen_clean_segments_skip_correction
whisper_clean_segments_skip_correction
semantic_candidate_becomes_target
neighbors_are_context_not_targets
unchanged_targets_are_not_returned
unknown_segment_id_rejected
timestamp_identity_preserved
delta_output_reduces_completion_payload
replay_skips_completed_targets
```

---

# 10. WP4 — Retry / Truncation / Chunk Amplification

## 目标

保留已经部署的可靠性能力，同时减少重复全文请求。

---

## 10.1 已有能力不得重做

当前已有：

```text
AI_PROVIDER_OUTPUT_TRUNCATED
batch split
sub-batch commit
adaptive runtime hint
provider-specific retry classification
circuit isolation
```

本 WP 只处理剩余放大问题。

---

## 10.2 Truncation 优先级

当：

```text
OUTPUT_TRUNCATED
```

优先：

```text
当前 Provider
→ smaller chunk
→ checkpoint success
→ remaining chunk
```

只有当前 Provider 真正不可用才 fallback。

禁止：

```text
local 8k chunk truncated
→ 立刻把原 8k 再发给 remote fallback
```

这会同时增加时间和 Token。

---

## 10.3 Structured Error

区分：

```text
OUTPUT_TRUNCATED
INVALID_JSON
SCHEMA_INVALID
EMPTY_RESPONSE
CONTEXT_TOO_LARGE
RATE_LIMIT
QUOTA
POLICY_BLOCK
```

只有：

```text
OUTPUT_TRUNCATED
CONTEXT_TOO_LARGE
```

可直接驱动 chunk shrink。

普通 JSON 问题不要默认整块二分。

---

## 10.4 Correction Chunk Hint

保留现有：

```text
ai_runtime_hints.transcript_correction[model].max_batch_size
```

扩展为同时可保存：

```text
safe_max_chars
safe_max_segments
```

不得跨模型错误共享。

---

## 10.5 Ground Map Adaptive Hint

为 Ground Map 使用同一思想，不新造调度器。

建议：

```text
ai_runtime_hints.ground_map[model]
```

保存：

```json
{
  "safe_max_chars": 6000,
  "safe_max_segments": 80
}
```

当 Provider 成功：

```text
可稳定保持
```

截断：

```text
收紧
```

不要每个新 Job 从已知会截断的最大块重新试错。

---

## 10.6 Checkpoint

Chunk 成功后：

```text
立即保存 partial artifact
```

后续失败：

```text
Replay
→ 只处理 remaining chunks
```

优先复用现有：

```text
JobStepArtifact
Job runtime hints
Grounded Map artifact
```

不要新增另一套 checkpoint 数据库。

---

## 10.7 Acceptance

目标：

```text
retry amplification 明显下降
fallback amplification 明显下降
同一失败 chunk 不重复发送完整输入
```

---

# 11. WP5 — Grounded Artifact Reuse + Compact Evidence

## 目标

不牺牲地点召回，减少同一 Transcript 被 LLM 多次全文读取。

---

## 11.1 保留独立 Grounded Scan

保持：

```text
Corrected Transcript
↓
EXTRACT_TRAVEL_FACTS / Ground Map
↓
Grounded Evidence
↓
Note
```

不要改回：

```text
Note
↓
Place Extraction
```

---

## 11.2 Canonical Grounded Artifact

Artifact key 应围绕：

```text
transcript fingerprint
correction version
ground map prompt version
schema version
domain context hash
semantic Stage settings
```

Render Profile 不应进入 Grounded Artifact key。

也就是说：

```text
TRAVEL_GUIDE
→
COMPACT
```

只改变 Note Render：

```text
Grounded Artifact REUSE
Note Reduce RUN
```

---

## 11.3 Provider-independent Artifact Reuse

区分：

### Request Cache

可以包含：

```text
provider
model
```

### Domain Artifact

例如：

```text
Canonical Grounded Map
Corrected Transcript
Validated Evidence Pack
```

只要语义输入 / contract 未变化，普通 Replay 可以复用。

不要因为：

```text
当前默认模型从 A 改成 B
```

自动让所有既有有效 Artifact 失效。

用户明确：

```text
Force Regenerate
Quality Re-run
```

时才绕过。

---

## 11.4 Compact Evidence Pack

Note Reduce 不再收到整篇 Transcript。

输入应收敛为：

```text
validated facts
exact supporting quotes
segment ids
place mention ids
time range
```

例如：

```json
{
  "section_id": "...",
  "places": ["mention-1"],
  "facts": [
    {
      "type": "DISH",
      "value": "...",
      "segment_ids": ["seg-12"],
      "quote": "..."
    }
  ]
}
```

禁止：

```text
为了写 Note
再次附上 30～60 分钟完整 corrected transcript
```

---

## 11.5 Evidence 安全

Compact 不代表丢 Evidence。

必须保留：

```text
exact quote
segment id
source range
```

Note 输出中的事实仍必须可回到 Transcript。

---

## 11.6 StageDecision

在每个 expensive Stage 前：

```text
REUSE
>
SKIP
>
RUN
```

这是唯一 Stage Decision 机制。

---

## 11.7 Replay 示例

### 修改 Note Profile

```text
Transcript             REUSE
Correction             REUSE
Grounded Map           REUSE
PlaceMention           REUSE
POI                    REUSE
Note Reduce            RUN
Screenshot             REUSE / optional
```

### 修改 ASR Provider 并显式 Full Re-run

```text
DOWNLOAD_AUDIO         REUSE
ASR                    RUN
Transcript             RUN
Correction             RUN / SKIP by gate
Grounded Map           RUN
Note                    RUN
POI                     RUN
```

---

# 12. WP6 — AMap Cache + Bounded Concurrency

## 目标

减少 POI 阶段非 AI 延迟和重复请求。

---

## 12.1 Cache Key

基于：

```text
normalized query
city / region hint
typecode set
around center
radius bucket
provider
resolver version
```

不要只用：

```text
query string
```

否则地理上下文会串缓存。

---

## 12.2 Cache 内容

保存：

```text
candidate provider ids
name
address
type
coordinates
query provenance
fetched_at
```

不保存 API Key。

---

## 12.3 Concurrency

使用 bounded concurrency。

不要：

```text
几十个 PlaceMention 全串行
```

也不要：

```text
几十个同时打高德
```

配置：

```text
amap_max_concurrency
```

默认值通过真实 Provider 行为验证。

不要在代码中散落硬编码线程数。

---

## 12.4 Duplicate Query Coalescing

同一 Job 内：

```text
相同 normalized query + geo context
```

只请求一次。

多个 Mention 可共享 Candidate Set。

---

## 12.5 不改变 Resolver 决策安全

Cache / concurrency 只能改变：

```text
性能
```

不能改变：

```text
AUTO_STRONG
AUTO_CONTEXTUAL
REVIEW
UNRESOLVED
MANUAL_CONFIRMED
```

决策逻辑。

人工确认永远不能被 Cache 更新覆盖。

---

# 13. WP7 — Screenshot Batch + Core-first Materialization

## 目标

缩短用户看到可用 Note 的时间。

---

## 13.1 定义 First Useful Note

当以下内容完成即可认为核心结果可用：

```text
可信 Transcript
Grounded places/facts
Note
POI 状态
Evidence links
```

不要求：

```text
所有 Screenshot 完成
```

---

## 13.2 Core-first

Pipeline 调整为：

```text
Core semantic stages
↓
MATERIALIZE_CORE
↓
UI 可读取 Note
↓
Screenshot stages
↓
MATERIALIZE_ENRICHMENT
```

如果不希望新增 JobStep 名称，也可：

```text
在现有 MATERIALIZE 中增加 core materialize checkpoint
```

优先最小结构改动。

---

## 13.3 Screenshot Batch

先 Benchmark 当前：

```text
screenshot_process_count
ffmpeg_total_ms
decode_redundancy
```

然后将同一个视频的多个时间点尽量减少重复启动 / 重复解码。

实现方式必须以现有 `video_screenshots.py` 为基础。

不要另建 Screenshot Service V2。

---

## 13.4 非核心失败

Screenshot 失败：

```text
不应让已经可信的 Note 丢失
```

保持：

```text
PARTIAL_SUCCESS
```

语义。

---

# 14. WP8 — Unified Graduation

## 目标

用同一份 frozen dataset 验证：

```text
Qwen ASR
+
Correction v2
+
Ground Artifact reuse
+
Adaptive chunks
+
AMap cache
+
Screenshot optimization
```

不是分别验证“单项看起来有效”。

---

## 14.1 复用现有 Runner

只扩展：

```text
run_asr_benchmark.py
run_video_benchmark.py
run_ai_e2e_harness.py
```

不要新增 master benchmark 程序，除非现有三个无法组合。

---

## 14.2 ASR Gate

至少：

```text
Qwen failure <= Whisper baseline
Qwen place recall >= baseline
Qwen proper noun >= baseline
timestamp no regression
no OOM
context false insertion 不产生关键错误
```

---

## 14.3 Transcript Gate

冻结样本：

```text
critical hallucination = 0
timestamp mutation = 0
segment identity mutation = 0
```

Correction：

```text
candidate recall 可接受
changed segment precision 高
```

---

## 14.4 Place / Evidence Gate

至少：

```text
place recall 不低于当前 baseline
critical false POI confirm = 0
evidence coverage >= current baseline
unsupported facts = 0
```

---

## 14.5 Token Gate

建议主目标：

```text
首次新视频 Prompt Token
相对 baseline 下降 30%～45%
```

其中 Correction：

```text
correction_input_chars
相对旧全量校对显著下降
```

Note Profile 重生成：

```text
Prompt Token 下降 70%～90%
```

因为 Grounded Artifact 应复用。

无变化 Replay：

```text
新增 LLM Token 接近 0
```

这些属于目标区间；最终 release gate 以 Frozen Benchmark 的质量不回退为前提。

---

## 14.6 Performance Gate

目标：

```text
Time To First Useful Note
明显低于 baseline
```

以及：

```text
AMap request/job ↓
Screenshot subprocess/job ↓
retry amplification ↓
fallback amplification ↓
```

不要只看总 wall time。

---

# 15. 推荐实施顺序

严格执行：

```text
WP0
冻结真实 Baseline
        ↓
WP1
跑通 Qwen Runtime + Benchmark
        ↓
Benchmark Gate
        ↓
WP2
Qwen Production Provider（保持非默认）
        ↓
WP3
Provider-independent Quality Gate + Delta Correction
        ↓
WP4
Adaptive chunk / retry amplification
        ↓
P0 E2E
        ↓
WP5
Grounded Artifact + Compact Evidence
        ↓
WP6
AMap Cache / concurrency
        ↓
WP7
Screenshot / core-first
        ↓
WP8
Unified Graduation
        ↓
决定是否切 Qwen 默认
```

禁止：

```text
先把 Qwen 设默认
然后再补 Benchmark
```

---

# 16. 建议 Commit 边界

每个 WP 独立 commit。

建议：

```text
perf: freeze video pipeline baseline metrics

asr: add isolated qwen3 asr runtime adapter

asr: register qwen3 provider behind explicit selection

ai: generalize transcript quality gate across asr providers

ai: switch transcript correction to delta targets

ai: reduce truncation and fallback amplification

ai: reuse canonical grounded artifacts across note profiles

perf: cache and bound amap resolution calls

perf: reduce screenshot subprocess overhead

perf: add unified qwen/token pipeline graduation report
```

禁止一个 commit 同时修改：

```text
ASR Runtime
+
Correction Prompt
+
POI Resolver
+
Screenshot
```

---

# 17. 主要代码修改矩阵

| 文件 | 修改 |
|---|---|
| `backend/src/zhijian/providers/asr.py` | 增加 Qwen Provider；Protocol 支持 optional context；保留 tuple Contract |
| `backend/src/zhijian/core/config.py` | Qwen Runtime 路径 / enable / model 配置 |
| `backend/src/zhijian/services/video_pipeline.py` | 构建 ASR Context；选择 Qwen；保存 metadata；fallback |
| `backend/src/zhijian/services/asr_context.py` | 新增可信 ASR Context 构建 |
| `backend/src/zhijian/ai/transcript_quality.py` | 去 Whisper-specific；统一 Provider-independent candidate gate |
| `backend/src/zhijian/services/transcript_validation.py` | 验证 Qwen timestamp / source metadata |
| `backend/src/zhijian/services/video_support.py` | target/context 分离；Delta Correction；Ground Map adaptive chunk / compact evidence |
| `backend/src/zhijian/ai/stage_decision.py` | 仅补充 REUSE/SKIP 所需输入，不建新引擎 |
| `backend/src/zhijian/ai/reliability.py` | 如有必要，仅调整 truncation → split → fallback 顺序 |
| `backend/src/zhijian/ai/cache.py` | 保持 request cache；配合高层 Artifact reuse |
| `backend/src/zhijian/services/grounded_map.py` | Canonical artifact key / partial checkpoint / compact evidence |
| `backend/src/zhijian/providers/amap.py` | Cache / bounded concurrency 支持 |
| `backend/src/zhijian/services/video_screenshots.py` | batching / subprocess reduction |
| `scripts/qwen_asr_runner.py` | Benchmark 与 Production 共享 Runner |
| `scripts/run_asr_benchmark.py` | 原则上复用；只做必要兼容 |
| `scripts/benchmark_asr_providers.py` | 原则上复用；只补实际指标缺口 |
| `scripts/run_video_benchmark.py` | 增加 performance/token 指标 |
| `backend/tests/` | 每 WP 对应回归测试 |
| `dev docs/IMPLEMENTATION_STATUS.md` | 每 WP 完成后更新真实状态 |
| `dev docs/CURRENT_HANDOFF.md` | 仅记录当前部署 / 验收事实 |

---

# 18. Schema / Migration 原则

本计划默认：

```text
不新增 Migration
```

优先使用：

```text
metadata_json
output_json
artifact_ref_json
ExternalCallAudit
runtime hints
```

只有出现以下需求才 migration：

```text
需要高频按字段查询
需要数据库约束
需要索引
JSON 已无法安全表达
```

禁止为了：

```text
provider
model
context hash
benchmark metric
```

单独立刻增加数据库列。

---

# 19. Qwen Runtime 安全要求

Runner 必须：

```text
无 shell=True
输入路径明确
timeout
stdout JSON only
stderr diagnostics
退出清理
模型路径受控
不读取任意网络 URL
```

Production Provider 不允许把用户可控字符串直接拼 Shell。

Context：

```text
长度限制
term 数量限制
单 term 长度限制
去重
Unicode normalize
```

---

# 20. Qwen Context 防幻觉门禁

必须增加测试：

```text
context term 未出现在音频
→ 不应被强插入 Transcript
```

Benchmark 记录：

```text
false_hotword_insertions
```

如果 Context：

```text
Place Recall ↑
但 false insertions 明显 ↑
```

则 Production 默认：

```text
Context OFF
```

或只允许更小可信词表。

不能因为 context_gain 为正就自动启用。

---

# 21. Runtime / Memory 策略

Mac mini 16 GB：

```text
ASR
与
Ollama
与
Vision
```

默认串行。

继续：

```text
gpu_heavy_concurrency = 1
```

Qwen Runner 完成：

```text
process exit
↓
memory release
↓
Correction / Ground Map
```

不让 Qwen 常驻服务作为首期默认。

只有 Benchmark 证明：

```text
常驻带来的加载收益
>
统一内存竞争成本
```

才另开 P2。

---

# 22. 默认 ASR Promotion Gate

Qwen 接入 Registry 与“成为默认”是两个不同事件。

## 可进入 Registry

满足：

```text
contract
timestamp
stability
memory
fallback
tests
```

即可。

## 可成为默认

额外要求：

```text
真实业务 Place Recall 有可重复收益
Proper Noun 有收益
Pipeline Total Cost 不恶化
Correction Token 有下降
没有重大 Context hallucination
长视频稳定
```

如果：

```text
Qwen 更准
但总 wall time / RAM 明显更高
```

则定位：

```text
QUALITY ASR
```

Whisper 保持：

```text
FAST / fallback
```

---

# 23. 不实施内容

本主计划明确不做：

```text
Qwen3-ASR 1.7B 默认化
云 ASR 默认化
多 ASR 同视频 ensemble
每个视频同时跑 Whisper + Qwen 取最优
LLM 生成 Hotword
ASR 自动生成 POI
ASR 改写 Evidence
新的 Replay 架构
新的 AI Gateway
新的 Retry Scheduler
新的 Token 数据库
新的 Resource Lock
重做 POI V2 决策
地图 UI 大改
Vision 全视频理解
```

---

# 24. Agent 执行规则

Agent 每次只能执行一个 WP。

开始前：

```text
1. 阅读本文件当前 WP
2. rg 目标代码
3. 只读取必要现有实现
4. 确认该能力是否已经存在
5. 已存在则扩展，不复制
```

结束前：

```text
targeted tests
backend full tests
ruff
frontend verify（涉及 frontend 时）
git diff --check
```

涉及真实 Provider：

```text
不得自动运行
```

除非该 WP 明确属于 Benchmark / E2E 且已有授权素材与配置。

---

# 25. 每个 WP 的交付模板

Agent 完成后必须记录：

```text
WP:
Status:

Changed files:

Reused existing components:

Deleted / avoided duplicate implementation:

Metrics before:
Metrics after:

Tests:

Known limits:

Production behavior changed?
YES / NO

Default ASR changed?
YES / NO

Migration?
YES / NO
```

---

# 26. 最终验收表

## Architecture

- [ ] 没有第二套 ASR Quality Engine。
- [ ] 没有第二套 StageDecision。
- [ ] 没有第二套 Retry / Circuit 系统。
- [ ] 没有第二套 Resource Lock。
- [ ] 没有第二套 ASR Benchmark Runner。
- [ ] Qwen 与 Whisper 输出同一 Transcript Contract。
- [ ] Grounded Evidence 仍是 Note / POI 的可信上游。

## Qwen

- [ ] Qwen 0.6B 实际 Benchmark。
- [ ] Context A/B 实际 Benchmark。
- [ ] Timestamp 实际 Benchmark。
- [ ] Long-form 实际 Benchmark。
- [ ] Runtime 隔离。
- [ ] Production failure 可 fallback。
- [ ] 不进行质量型双 ASR。

## Token

- [ ] Correction 不再因为“非 Whisper”全量发送。
- [ ] target 与 neighbor context 分离。
- [ ] Correction 只返回变化。
- [ ] Grounded Artifact 可复用。
- [ ] Note Reduce 不重新读取整篇 Transcript。
- [ ] Replay 优先 REUSE。
- [ ] Truncation 不优先触发完整 fallback。

## Performance

- [ ] AMap duplicate query 合并。
- [ ] AMap bounded concurrency。
- [ ] Screenshot subprocess 降低或证明无需修改。
- [ ] Core Note 可早于非核心截图交付。

## Quality

- [ ] Place Recall 不回退。
- [ ] Evidence coverage 不回退。
- [ ] Critical hallucination = 0。
- [ ] Wrong auto-confirm = 0。
- [ ] Timestamp identity 无破坏。

---

# 27. 最终目标状态

完成本主计划后，系统应达到：

```text
平台可靠字幕
→ 几乎零 Correction Token

Qwen 高质量 ASR
→ 仅可疑 Segment Correction

Whisper fallback
→ 稳定保底

Grounded semantic scan
→ 一次主扫描，多处复用

Note Profile change
→ 不重扫 Transcript

Replay no semantic change
→ 近零新增 Token

AMap
→ 缓存 + 去重 + 有界并发

Screenshot
→ 不阻塞 First Useful Note
```

最终希望从：

```text
同一 Transcript
被多个模型反复完整读取
```

演进到：

```text
Transcript
只在必要 Stage 被读取一次
其余流程消费已验证、可复用、紧凑的 Artifact
```

---

# 28. 建议 Agent 首次执行任务

第一个执行任务只做：

```text
WP0 + WP1
```

但提交必须分开：

```text
Commit 1
Baseline / metrics

Commit 2
Qwen isolated runtime adapter + benchmark execution support
```

禁止首个 Agent 同时：

```text
改 Production ASR
改 Correction
改 Ground Map
改 POI
```

首先得到真实数据：

```text
Qwen 是否更准？
Context 是否有效？
时间码是否可靠？
RAM 是否可接受？
它实际减少多少后续 Correction Candidate？
```

拿到这些数据，再进入 WP2 / WP3。

---

# 29. 参考实现边界

Qwen3-ASR 模型：

```text
Qwen/Qwen3-ASR-0.6B
```

Forced Alignment：

```text
Qwen/Qwen3-ForcedAligner-0.6B
```

Apple Silicon Benchmark 可使用 MLX implementation，但生产接入前必须固定版本并记录 backend provenance。

相关参考：

```text
https://github.com/QwenLM/Qwen3-ASR
https://huggingface.co/Qwen/Qwen3-ASR-0.6B
https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B
```

MLX implementation 属独立实现层，不能在文档中描述为 Qwen 官方 Runtime。

---

# 30. 计划完成条件

只有以下全部满足，才算本计划完成：

```text
Qwen Production Provider 可用
+
默认是否切换有 Benchmark 证据
+
Correction 已 provider-independent
+
Correction Token 显著降低
+
Ground Artifact 有稳定复用
+
Retry/Fallback 放大降低
+
AMap / Screenshot 性能优化有真实指标
+
Frozen E2E 质量无回退
```

如果 Qwen Benchmark 最终不优于现有 Whisper：

```text
本计划仍然有效
```

只需：

```text
不切 Qwen 默认
保留 WP3～WP8 的 Pipeline / Token 优化
```

因为真正的核心目标始终是：

> **用更少的计算、调用和 Token，得到更可信、更快可用的视频笔记。**
