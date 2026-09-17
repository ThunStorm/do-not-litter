# 本地 ASR 引擎 Benchmark 与接入实施计划

> 项目：`ThunStorm/do-not-litter`
> 分支：`codex/mac-mini-implementation`
> 目标：先在真实业务素材上完成本地 ASR Benchmark，再决定是否替换或新增生产 ASR Provider。
> 原则：Benchmark 与生产接入严格分离；测试阶段不修改当前默认 ASR。

---

## 1. 当前基线

当前生产 ASR：

```text
WHISPER_CPP
whisper.cpp
ggml-base.bin
```

当前 Provider 接口统一输出：

```python
(
    text,
    [
        {
            "text": "...",
            "start_ms": 0,
            "end_ms": 1000,
            "locator": {...}
        }
    ]
)
```

后续所有候选引擎必须适配这一 Contract，禁止下游 Video Pipeline 感知具体 ASR 实现。

---

# 2. 本轮 Benchmark 的核心问题

本轮不追求“哪个模型公开榜单最好”，而是回答：

> 在当前 Mac mini、本地视频工作流、中文旅行内容、地点识别需求下，哪个 ASR 最合适？

重点看：

```text
地点是否漏识别
专有名词是否准确
快语速是否丢句
BGM 是否造成幻觉
多人说话是否稳定
长视频时间码是否漂移
运行速度
峰值内存
是否影响 Ollama / Vision / LLM
```

---

# 3. 第一阶段必须测试的 4 组

本轮第一阶段固定测试以下四组，不再把 Qwen3-ASR 作为可选项。

## A. 当前基线

```text
WHISPER_CPP_BASE
```

用途：

- 获得当前真实基准。
- 所有新方案必须与其比较。

---

## B. Whisper.cpp 升级模型

```text
WHISPER_CPP_LARGE_V3_TURBO_Q5
```

建议模型：

```text
large-v3-turbo-q5_0
```

目的：

> 判断当前主要问题是 Whisper 架构本身，还是当前 `base` 模型过弱。

优点：

- 不增加新 Runtime。
- 不修改 Provider 架构。
- 时间码路径不变。
- Metal 路径不变。
- 接入成本最低。

---

## C. SenseVoiceSmall + sherpa-onnx

```text
SENSEVOICE_SHERPA_ONNX_INT8
```

目的：

> 验证一个轻量、中文优先、非 Whisper 架构的本地 ASR。

重点：

- 普通话。
- 快速地点连续出现。
- 中国地名、人名、景点名。
- BGM。
- 数字、价格、月份。
- 多人。
- 时间戳。

SenseVoice 是本轮主要的“轻量替代候选”。

---

## D. Qwen3-ASR 0.6B + MLX

```text
QWEN3_ASR_MLX_0_6B
```

Qwen3-ASR 从本计划开始正式进入第一阶段 Benchmark。

目的：

> 验证较强中文、方言、BGM、上下文提示能力，是否值得用更高资源占用换取更高识别质量。

只测试：

```text
Qwen3-ASR 0.6B
```

本轮暂不测试：

```text
Qwen3-ASR 1.7B
```

原因：当前机器还同时需要承载 ASR、Ollama、LLM、Vision。1.7B 更适合作为以后单独的高质量模式，不适合作为当前默认候选。

---

# 4. Qwen3-ASR 必须额外测试的能力

## 4.1 Context / Hotword

测试：

```text
视频主题：云南大理
已知可能出现：
大理古城
洱海
双廊
喜洲
苍山
```

比较：

```text
无上下文
vs
有上下文提示
```

观察：

```text
地点 Recall
专有名词准确率
是否错误强行匹配 Hotword
```

目标：判断未来能否将“当前视频主题 / 已确认城市 / POI 候选”反向用于 ASR 提升地名识别。

## 4.2 BGM / 复杂声音

重点收集：

```text
旅行 vlog BGM
街道环境音
风声
车内录音
音乐下旁白
```

检查幻觉率、漏句率、地点识别率。

## 4.3 方言与口音

至少包含普通话、轻口音普通话，以及真实业务视频中已有的粤语/方言样本。

## 4.4 Forced Alignment / 时间码

Qwen3-ASR 本体与时间对齐需要单独评估，必须记录：

```text
ASR 推理时间
Forced Aligner 时间
合计时间
额外内存
最终时间码偏差
```

不能只测文本准确率后忽略 alignment 成本。

---

# 5. 第二阶段条件性候选：Paraformer

Paraformer 不进入第一轮必测。

只有以下情况之一出现时再测试：

```text
1. SenseVoice 和 Qwen 都没有明显胜出
2. Qwen 准确但资源太重
3. 希望利用 CoreML / ANE 降低 GPU 竞争
4. 中文准确率仍有优化空间
```

候选：

```text
PARAFORMER_COREML_INT8
```

优先验证中文准确率、ANE 占用、Peak RAM、30 秒切片策略和时间码拼接。

---

# 6. 第一阶段执行顺序

```text
Step 1
WHISPER_CPP_BASE
        ↓
Step 2
WHISPER_CPP_LARGE_V3_TURBO_Q5
        ↓
Step 3
SENSEVOICE_SHERPA_ONNX_INT8
        ↓
Step 4
QWEN3_ASR_MLX_0_6B
        ↓
统一比较
        ↓
决定是否需要 Paraformer
```

Qwen 不再依赖前三个结果才执行。

---

# 7. 为什么仍按这个顺序测试

```text
Whisper Base
→ 已存在

Whisper Turbo
→ 只换模型

SenseVoice
→ 轻量新 Runtime

Qwen3-ASR
→ MLX + 更高内存 + Forced Alignment
```

这样可以控制环境复杂度，并方便逐层排查。

---

# 8. Benchmark 数据集

复用仓库已有六类：

```text
MANDARIN_TRAVEL
RAPID_PLACES
PROPER_NOUNS
BACKGROUND_MUSIC
MULTI_SPEAKER
LONG_FORM
```

现有：

```text
scripts/benchmark_asr_providers.py
```

继续作为评分器。

新增：

```text
scripts/run_asr_benchmark.py
```

负责真正运行 Provider 和采集结果。

---

# 9. 数据集规模

第一轮建议：

```text
每类 3~5 个样本
总计 20~30 个 clip
```

短片：30 秒 ~ 3 分钟。
Long Form：15~30 分钟。
额外至少挑 2 个完整真实视频做最终回放。

---

# 10. Ground Truth

每个样本：

```json
{
  "id": "rapid_places_001",
  "category": "RAPID_PLACES",
  "audio": "...",
  "reference_text": "...",
  "expected_entities": [
    "大理古城",
    "洱海",
    "双廊"
  ],
  "expected_numbers": [],
  "context_hints": [
    "云南",
    "大理"
  ],
  "notes": ""
}
```

Ground Truth 必须人工核对，不能把另一个 ASR 的输出直接作为标准答案。

---

# 11. 指标

继续保留现有：

```text
place_entity_recall
proper_noun_accuracy
timestamp_alignment
runtime_ms
peak_memory_bytes
failure_count
```

新增：

```text
CER
segment_coverage
hallucination_rate
number_accuracy
long_form_drift
RTF
```

Qwen 额外：

```text
context_gain
alignment_runtime_ms
alignment_peak_memory
```

---

# 12. context_gain

定义：

```text
context_gain =
有 Context 的 Place Recall
-
无 Context 的 Place Recall
```

同时必须检查：

```text
false_hotword_insertions
```

避免模型把未出现的候选词强行插入结果。

---

# 13. 推荐指标权重

```text
Place Entity Recall       30%
Proper Noun Accuracy      20%
Segment Coverage          15%
CER                       15%
Timestamp Alignment       10%
Hallucination Rate         5%
Runtime / Memory           5%
```

不要只看 CER。

---

# 14. 为什么地点 Recall 权重最高

当前链路：

```text
ASR
↓
LLM 校对
↓
地点抽取
↓
POI Grounding
```

如果“洱海”被识别成“耳海”，后续还有机会修复；如果整句被漏掉，后续模型无法恢复该地点。因此漏句 / 漏地点比单字错误更严重。

---

# 15. 硬门槛

任何候选成为默认 Provider 前必须满足：

```text
failure_count <= baseline
Place Entity Recall >= baseline
不存在明显长视频时间码漂移
不会造成系统 OOM / swap 严重抖动
```

---

# 16. Qwen 额外资源门槛

Qwen3-ASR 即使准确率最高，也不能仅凭准确率成为默认。

需要额外确认：

```text
ASR + ForcedAligner
```

在本机总 Peak RAM 可接受。

Benchmark 时同时记录：

```text
系统物理内存
swap
CPU
GPU / Metal
MLX peak
```

若 Qwen 明显挤压 Ollama / Vision，则定位为：

```text
ADVANCED_ASR
```

而不是：

```text
DEFAULT_ASR
```

---

# 17. Benchmark Runner

新增：

```text
scripts/run_asr_benchmark.py
```

流程：

```text
读取 manifest
↓
选择 Provider
↓
加载模型
↓
预热
↓
调用 transcribe
↓
记录 runtime
↓
记录内存
↓
保存 text / segments
↓
计算基础 metrics
↓
交给 benchmark_asr_providers.py
```

---

# 18. 预热与冷启动

所有模型都区分：

```text
model_load_ms
first_run_ms
warm_run_ms
```

不要把首次模型加载时间直接混进纯推理速度。

---

# 19. 输出目录

建议：

```text
data/benchmarks/asr/
```

结构：

```text
manifest.json

runs/
  whisper-base/
  whisper-turbo/
  sensevoice/
  qwen3-asr/
  paraformer/

reports/
  asr_benchmark_results.json
  ASR_BENCHMARK_REPORT.md
```

---

# 20. Benchmark Provider 与生产 Provider 分离

Benchmark 阶段不得修改：

```text
ASRProviderRegistry.default_provider_id
```

可以先实现实验 Adapter，只有通过 Benchmark 后才迁移到：

```text
backend/src/zhijian/providers/asr.py
```

正式生产实现。

---

# 21. 第一阶段报告

最终生成：

```text
ASR_BENCHMARK_REPORT.md
asr_benchmark_results.json
```

报告至少包含：

| Provider | Place Recall | Proper Noun | CER | Coverage | Timestamp | RTF | Peak RAM | Failures |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Whisper Base | | | | | | | | |
| Whisper Turbo | | | | | | | | |
| SenseVoice | | | | | | | | |
| Qwen3-ASR 0.6B | | | | | | | | |
| Paraformer（若执行） | | | | | | | | |

Qwen 额外增加 Context 对照：

| Mode | Place Recall | Proper Noun | Hallucination |
|---|---:|---:|---:|
| 无 Context | | | |
| 有 Context | | | |

---

# 22. 决策输出

报告必须给出以下结果之一：

```text
KEEP_CURRENT
UPGRADE_WHISPER_MODEL
ADD_NEW_DEFAULT_PROVIDER
ADD_NEW_FALLBACK_PROVIDER
ADD_ADVANCED_PROVIDER
RUN_PARAFORMER_CHALLENGE
```

---

# 23. 推荐决策逻辑

## 情况 A：Whisper Turbo 与其它模型准确率接近

```text
UPGRADE_WHISPER_MODEL
```

优先最低工程复杂度。

## 情况 B：SenseVoice 明显领先，且很轻

```text
ADD_NEW_DEFAULT_PROVIDER
```

Whisper 保留 fallback。

## 情况 C：Qwen3-ASR 准确率明显领先，而且资源可接受

```text
ADD_NEW_DEFAULT_PROVIDER
```

候选：

```text
QWEN3_ASR
```

但必须同时满足时间码和长视频稳定性要求。

## 情况 D：Qwen 明显更准，但资源较高

```text
ADD_ADVANCED_PROVIDER
```

例如：

```text
默认：
SenseVoice / Whisper Turbo

高质量模式：
Qwen3-ASR 0.6B
```

## 情况 E：Qwen Context 对地点提升明显

未来可考虑：

```text
视频主题
+
已确认城市
+
已有 POI / 地点词表
↓
ASR Context
```

本轮只验证，不直接实现自动 Context Routing。

---

# 24. 是否继续 Paraformer

完成四个必测 Provider 后：

```text
Whisper Base
Whisper Turbo
SenseVoice
Qwen3-ASR 0.6B
```

如果仍没有明确的“质量 + 资源”平衡方案，则：

```text
RUN_PARAFORMER_CHALLENGE
```

否则跳过 Paraformer，减少无意义依赖和开发。

---

# 25. 第二阶段：正式接入应用

Benchmark 完成并人工确认决策后，再开始生产接入。

修改：

```text
backend/src/zhijian/providers/asr.py
```

只增加最终保留的引擎，例如：

```python
class SenseVoiceProvider:
    provider_id = "SENSEVOICE"

class Qwen3ASRProvider:
    provider_id = "QWEN3_ASR"
```

不要把所有实验模型永久塞进 Production Registry。

---

# 26. ASR Registry

扩展：

```python
ASRProviderRegistry.get()
```

最终可能：

```text
WHISPER_CPP
WHISPER_CPP_CPU
SENSEVOICE
QWEN3_ASR
```

实际加入哪些，以 Benchmark 结论为准。

---

# 27. 设置页面

第二阶段增加：

```text
本地 ASR 引擎
```

例如：

```text
Whisper.cpp — Large V3 Turbo
SenseVoice Small
Qwen3-ASR 0.6B
```

如果 Qwen 资源明显较高：

```text
Qwen3-ASR 0.6B
高质量 · 较高资源占用
```

---

# 28. 默认 / 高质量模式

如果 Benchmark 表明：

```text
SenseVoice
速度快、资源低

Qwen
地点/专名更准
```

可以最终设计：

```text
标准 ASR：
SenseVoice

高质量 ASR：
Qwen3-ASR
```

但不要在 Benchmark 阶段提前实现。

---

# 29. Fallback

生产接入后允许：

```text
Primary ASR
↓
运行失败
↓
Fallback ASR
```

只针对：

```text
runtime crash
模型缺失
OOM
无 transcript
无法初始化
```

不要因为识别结果“可能不好”自动再跑第二个完整 ASR，否则长视频成本会翻倍。

---

# 30. 本地资源调度

所有新 ASR 必须纳入：

```text
local_ai_resource_manager
```

或统一的本地 AI Resource Lock。

尤其 Qwen MLX 不允许与 Ollama 大模型 / Vision Model 无约束同时抢 unified memory。

---

# 31. 正式接入后的回归测试

必须覆盖：

```text
短视频
长视频
Bilibili
本地视频
任务重放
Worker 重启
模型不存在
Runtime 不存在
OOM
ASR fallback
```

并保证原 `WHISPER_CPP` 路径仍能正常工作。

---

# 32. 第一阶段明确禁止

Benchmark 阶段不要：

- 修改生产默认 Provider。
- 重写 Video Pipeline。
- 实现复杂 ASR 自动路由。
- 测 Qwen3-ASR 1.7B。
- 添加云 ASR。
- 修改后面的 LLM Prompt。
- 因单个测试视频决定最终方案。
- 把实验依赖永久写入生产环境后再决定是否使用。

---

# 33. Agent 第一阶段执行范围

第一次执行只完成：

```text
1. Benchmark Runner
2. Benchmark Dataset / Manifest
3. Whisper Base
4. Whisper Large-v3-Turbo Q5
5. SenseVoiceSmall
6. Qwen3-ASR 0.6B
7. Qwen Context 对照测试
8. Qwen Alignment 成本测试
9. 统一评分
10. 报告
```

如果结果没有明确结论，再申请执行 Paraformer。

不要自动进入第二阶段生产接入。

---

# 34. 第一阶段 Definition of Done

- [ ] 六类现有 Benchmark 场景全部覆盖。
- [ ] Ground Truth 人工核对。
- [ ] Whisper Base 完成。
- [ ] Whisper Turbo 完成。
- [ ] SenseVoice 完成。
- [ ] Qwen3-ASR 0.6B 完成。
- [ ] Qwen Context / 无 Context 对照完成。
- [ ] Qwen Alignment 成本有独立记录。
- [ ] 每个 Provider 有 runtime / RTF / RAM 数据。
- [ ] 每个 Provider 有地点 Recall / 专名 / CER / coverage 数据。
- [ ] 至少两个完整真实视频完成回放。
- [ ] 输出 `asr_benchmark_results.json`。
- [ ] 输出 `ASR_BENCHMARK_REPORT.md`。
- [ ] 明确是否需要 Paraformer。
- [ ] 明确 production integration candidate。
- [ ] 默认生产 ASR 尚未改变。

---

# 35. 第二阶段 Definition of Done

- [ ] 只正式接入 Benchmark 通过的 Provider。
- [ ] 新 Provider 遵守统一 ASR contract。
- [ ] Registry 可选择新引擎。
- [ ] Settings 可选择新 ASR。
- [ ] 原 Whisper 路径保留。
- [ ] Fallback 只针对运行失败。
- [ ] 新 Provider 接入本地资源管理。
- [ ] Qwen 若资源较高，可配置为高质量模式而非默认。
- [ ] 视频完整链路无回归。
- [ ] 是否替换默认 Provider 有 Benchmark 数据支撑。

---

# 36. 推荐最终执行流程

```text
当前 Whisper Base
        ↓
Whisper Large-v3-Turbo Q5
        ↓
SenseVoiceSmall
        ↓
Qwen3-ASR 0.6B
        ↓
统一 Benchmark
        ↓
有明确结果？
   ├── 是 → 选 Integration Candidate
   └── 否 → 测 Paraformer
                 ↓
           最终 Benchmark Report
                 ↓
           人工确认接入方案
                 ↓
           正式新增 ASR Provider
                 ↓
           设置页配置
                 ↓
           回归测试 / 灰度
                 ↓
           决定默认 ASR
```

核心原则：

> **先测，后接。**

Qwen3-ASR 0.6B 本轮必须实际跑，不再只是备选；但是否成为默认、备用或高质量模式，完全由同一台机器、同一批真实视频的 Benchmark 决定。
