# 架构与模型边界

> 来源：ai-gateway/AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md，原章节 1–11（正文保留，2026-09-03 分篇）。返回 [主题索引](AI_WORKLOAD_GATEWAY_AND_MODEL_ROUTING_PLAN_v2.md)。本篇是契约/规划，不是已实施清单；当前结论见 [实施状态](../IMPLEMENTATION_STATUS.md)，安全与回归见 [冻结清单](../REGRESSION_AND_CHANGE_GUARD.md)。裸文档路径均以 dev docs/ 为基准。只读取命中章节及其必要约束。

# 1. 架构决策

后续 AI 架构统一采用：

```text
AI Workload Gateway
+ Capability-based Routing
+ Local-first / Remote-selectable Execution
+ Context Reduction
+ Schema & Evidence Validation
+ Domain Context
+ Cache / Budget / Audit
```

原则：

```text
确定性代码做能确定的事
本地模型做高频、便宜、可验证的“量”
远程强模型做困难、专业、高价值的“难”
用户始终可以对任意 AI 语义阶段选择远程模型
```

“默认本地优先”**不等于**“远程模型只能是 fallback”。

每个 AI 语义阶段必须支持：

```text
AUTO
LOCAL_ONLY
LOCAL_FIRST
REMOTE_FIRST
REMOTE_ONLY
```

并支持单次任务覆盖具体 Provider / Model。

非 AI 的确定性步骤，例如下载、hash、时间换算、坐标计算、黑帧检测，不要为了“每阶段可远程”而模型化。

---

# 2. 当前 Provider 层保留

当前项目已有：

```text
LLMProvider
OllamaProvider
OpenAICompatibleProvider
FallbackLLMProvider
ExternalCallAudit
```

当前 `OllamaProvider` 已使用：

```text
/api/chat
stream = false
keep_alive = 0
format = json
```

现有 Provider 层解决的是：

> 怎么调用某个模型。

本次新增的 `AI Workload Gateway` 解决：

> 是否需要模型、给多少上下文、选哪个模型、结果是否合格、是否升级远程、是否可复用、预算是否允许。

目标：

```text
Business Pipeline
      ↓
AI Workload Gateway
      ↓
Router / Reducer / Cache / Validator / Escalation
      ↓
Existing Provider Layer
      ↓
Ollama / OpenAI-compatible / Future Providers
```

不要把 HTTP Provider 逻辑重复搬入 Gateway。

---

# 3. 不再硬编码 Qwen3.5:9B

本项目业务代码不得硬编码：

```text
qwen3.5:9b
qwen3:8b
qwen2.5:7b
```

业务只声明 Capability。

模型由 Profile 配置：

```text
FAST_LOCAL_TEXT
MAIN_LOCAL_TEXT
LOCAL_VISION
REMOTE_FAST
REMOTE_STRONG
REMOTE_VISION
REMOTE_SPECIALIST
```

允许多个 Profile 指向同一个模型。例如在 16 GB Mac mini 上：

```text
FAST_LOCAL_TEXT = qwen2.5:7b
MAIN_LOCAL_TEXT = qwen2.5:7b
```

完全合法。

---

# 4. Qwen2.5:7B / Qwen3:8B 结论

## 4.1 标准型号都是文本模型

Ollama 标准：

```text
qwen2.5:7b
qwen3:8b
```

均为 **Text-only**。

它们不能直接处理图片。

视觉必须使用独立型号，例如：

```text
qwen2.5vl:7b
qwen3-vl:4b
qwen3-vl:8b
```

因此 ModelProfile 必须显式声明：

```python
modalities={"text"}
```

或：

```python
modalities={"text", "image"}
```

不能根据模型名称猜视觉能力。

## 4.2 当前 Ollama 参考体积

| 模型 | 当前 Ollama 参考体积 | 模态 | 推荐角色 |
|---|---:|---|---|
| `qwen2.5:7b` | ~4.7 GB | Text | Fast/Main Local |
| `qwen3:8b` | ~5.2 GB | Text | Main Local |
| `qwen2.5vl:7b` | ~6.0 GB | Text+Image | Local Vision |
| `qwen3-vl:4b` | ~3.3 GB | Text+Image | Lightweight Vision |
| `qwen3-vl:8b` | ~6.1 GB | Text+Image | Main Vision |

模型文件体积不等于运行峰值内存。还要考虑 KV cache、Metal buffer、上下文、Whisper、Backend 和 macOS 本身。

---

# 5. Qwen2.5:7B 的定位

优点：

- 比 Qwen3:8B 略轻；
- 成熟稳定；
- 中文能力好；
- Qwen2.5 官方强调 structured data / JSON 能力；
- 不存在默认 thinking 带来的额外推理时间；
- 很适合大量固定 Schema 的任务。

推荐 Capability：

```text
CLASSIFICATION
STRUCTURED_EXTRACTION
ENTITY_EXTRACTION
TRANSCRIPT_CORRECTION
LINK_CLASSIFICATION
LIGHT_SUMMARIZATION
DOMAIN_TERM_EXTRACTION
```

建议作为：

```text
FAST_LOCAL_TEXT
```

如果真实 benchmark 已满足质量，也可以直接作为 `MAIN_LOCAL_TEXT`，减少模型切换和内存波动。

---

# 6. Qwen3:8B 的定位

Qwen3 官方相较 Qwen2.5 强调：

- reasoning；
- instruction following；
- agent capability；
- multilingual；
- thinking / non-thinking 双模式。

更适合：

```text
较复杂结构化抽取
章节摘要
语义冲突判断
复杂实体关系
本地 Verify
Ambiguity Analysis
```

建议作为：

```text
MAIN_LOCAL_TEXT
```

但必须通过真实项目 benchmark，而不是只看排行榜。

---

# 7. Qwen3 Thinking 默认关闭

对于以下高频阶段默认使用 non-thinking：

```text
CLASSIFICATION
STRUCTURED_EXTRACTION
ENTITY_EXTRACTION
TRANSCRIPT_CORRECTION
CHUNK_SUMMARIZATION
JSON_REPAIR
```

原因：

- 更低延迟；
- 更少本地计算；
- 更容易控制输出；
- Pipeline 吞吐更重要。

只有：

```text
COMPLEX_VERIFY
CONFLICT_RESOLUTION
COMPLEX_REASONING
AMBIGUITY_ANALYSIS
```

才允许 Router 根据策略开启 thinking。

thinking 必须：

```text
显式启用
有输出预算
有 Audit
```

不能全局默认开启。

---

# 8. Mac mini 16 GB 推荐部署

## 稳定优先方案

```text
FAST_LOCAL_TEXT = qwen2.5:7b
MAIN_LOCAL_TEXT = qwen2.5:7b 或 qwen3:8b
LOCAL_VISION = 按需加载，不常驻
REMOTE_STRONG = 用户配置的 OpenAI-compatible 模型
```

如果频繁切换两个文本模型造成加载时间或内存压力，则只保留一个 7B/8B 文本模型。

不要为了理论上多一个“Main Model”牺牲稳定性。

---

# 9. 本地模型最低要求

任何本地模型进入 Router 前必须通过 Capability Probe。

最低要求：

### 9.1 API

支持：

```text
Ollama /api/chat
```

未来也允许 localhost OpenAI-compatible endpoint。

### 9.2 中文

必须测试：

- 中文指令跟随；
- 中文实体；
- 中英混合；
- 地名/人名；
- 数字日期；
- 专有名词保持。

### 9.3 Structured Output

最低：

```text
JSON object
```

推荐：

```text
JSON Schema constrained output
```

Profile 记录：

```python
supports_json_mode
supports_json_schema
```

### 9.4 Context

项目自己控制工作窗口，不追求塞满模型标称上下文。

建议：

```text
最低：16K
推荐：32K+
```

即使模型标称 128K / 256K，16 GB Mac mini 也不应默认使用超长上下文。

### 9.5 Output Limit

Provider 必须支持或模拟：

```text
max_output_tokens
```

### 9.6 可重复性

Benchmark 至少记录：

```text
schema_pass_rate
field_consistency
evidence_consistency
```

### 9.7 模态

明确：

```text
text
image
```

视觉任务不能调度到 text-only 模型。

---

# 10. 本地模型的限制

本地模型不能被当成知识库。

以下内容尤其容易超出本地 7B/8B 的知识和辨识能力：

- 医学；
- 法律；
- 航空；
- 小众设备；
- 地方历史；
- 方言；
- 新政策；
- 行业黑话；
- 游戏/动漫小众设定；
- 罕见地名与专有名词。

正确做法：

```text
Domain Context
+ Relevant Evidence
+ Local/Remote Model
```

而不是简单：

```text
换更大模型
```

模型不知道时允许输出：

```text
UNKNOWN
```

禁止无证据补全事实。

---

# 11. 多模态策略

视觉 Capability 独立：

```text
VISION
DOCUMENT_VISION
SCREENSHOT_UNDERSTANDING
GUI_UNDERSTANDING
VISUAL_ENTITY_EXTRACTION
```

Mac mini 16 GB 建议：

```text
轻量图片初筛
→ qwen3-vl:4b 等较轻视觉模型

复杂文档 / 专业图 / 高质量视觉
→ REMOTE_VISION

用户要求最高质量
→ REMOTE_ONLY
```

视频不要把大量帧直接送视觉模型。

继续：

```text
Metadata + Note + Transcript time range
→ 确定候选时间码
→ 确定性抽帧
→ 少量候选帧
→ Vision Model
```

---
