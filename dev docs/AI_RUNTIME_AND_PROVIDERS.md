# AI Runtime and Providers

## 1. 原则

业务层永远不依赖具体模型厂商。

统一能力：

```text
LLMProvider
ASRProvider
POIProvider
```

---

# 2. LLMProvider

接口概念：

```python
class LLMProvider:
    async def generate(...)
    async def structured_output(...)
    async def vision(...)
```

实现：

- OllamaProvider
- OpenAIProvider
- OpenAICompatibleProvider
- MockProvider（测试）

第一版外部兼容端点至少验证：

- DeepSeek API；
- Xiaomi MiMo API；
- 用户自定义 OpenAI-compatible `base_url`。

模型 ID、上下文长度与能力随服务更新，不写死在 Processor；通过 Settings 的能力映射配置。

---

# 3. LLM 策略

支持：

- LOCAL_ONLY
- LOCAL_FIRST
- CLOUD_FIRST
- MANUAL

默认：
`LOCAL_FIRST`

---

# 4. Local First

示意：

```text
本地模型
→ Schema 验证
→ 成功：完成
→ 失败/低置信：根据策略调用外部模型
```

外部模型是增强，不是核心依赖。

---

# 5. 外部 API Key

Settings 支持：

- provider
- base_url
- api_key
- model
- timeout
- max_retry

正式版本不把 Key 明文放 SQLite。

平台 Secret Store：
- Windows PC：DPAPI / Windows Credential Manager；
- Mac mini：macOS Keychain。

SQLite 只存平台无关的 key reference，业务代码通过 `SecretStore` 接口访问，不判断操作系统。

开发环境允许 `.env`，但不得提交 Git。

外部请求的数据策略：

- `NORMAL` 来源 Segment 可按所选策略外发；
- `SENSITIVE` Profile 默认不外发，仅在用户对单次任务明确授权后发送最小必要字段；
- `LOCAL_ONLY` 永不发送到外部 Provider；
- 审计仅记录字段类别、Segment ID、Provider/Model 与结果状态，不记录完整敏感正文。

---

# 6. Capability-based Routing

业务不要指定具体模型。

任务声明：

- CLASSIFICATION
- STRUCTURED_EXTRACTION
- LONG_CONTEXT
- VISION
- SEMANTIC_MATCH
- VERIFY

Router 决定 Provider + Model。

---

# 7. 本地硬件策略

方案 A，WILLIAM-PC：
- 5800X
- 32 GB
- RX 7900 XT 20 GB

方案 B，Mac mini：
- Apple M4，10 核 CPU
- 16 GB 统一内存
- arm64 / Metal

两者都应验证本地承担：
- 分类；
- 结构化提取；
- Recruitment DSL；
- Travel Trait；
- ASR；
- 未来视觉理解。

Windows PC 可优先验证更大的本地模型与未来视觉模型。Mac mini 从 7B/8B 量化档起步，16 GB 统一内存下不承诺与 RX 7900 XT 相同的模型容量、吞吐或并发；复杂任务允许按数据策略转外部 Provider。两套结果分别记录，不互相推算。

---

# 8. 模型角色

具体型号允许随时间更新，不应硬编码到业务。

建议角色：

### Fast Local Model
- 分类
- 简单摘要
- 链接判断
- 轻量实体提取

### Main Local Model
- 招聘公告结构化
- Requirement DSL
- 地点抽取
- 偏好解释

### Vision Model
后续阶段。

### External Strong Model
- 本地解析失败
- 低置信
- 用户手动高质量重跑
- 高价值歧义验证

---

# 9. Structured Output

必须 Schema First。

流程：

```text
Prompt
+ JSON Schema
+ Evidence Segments
→ LLM
→ JSON
→ Pydantic Validation
→ PASS / RETRY / FAIL
```

不允许依赖自由文本再正则抠 JSON。

---

# 10. Evidence Validation

模型输出事实时必须引用 segment/evidence id。

若 Claim 没有对应 Evidence：
- Reject；
- Retry；
- 标记不可信。

---

# 11. Cross-model Verification

未来/可选：

重要字段可由本地与外部模型交叉验证。

若冲突：
- 不自动选择；
- 回到 Evidence；
- 显示冲突。

---

# 12. ASRProvider

默认：
WhisperCppProvider

预留：
- FasterWhisperProvider
- CloudASRProvider

运行时：
- Windows PC：whisper.cpp Vulkan；
- Mac mini：whisper.cpp Metal，可选验证 Core ML encoder；
- FasterWhisper/CloudASR 仍只作为可替换 Provider，不改变 Transcript 与 Evidence 模型。

---

# 13. ASR 策略

模式：

- FAST
- AUTO
- ACCURATE

AUTO：
- 默认快速模型；
- 低置信/关键内容再高精度重跑。

---

# 14. GPU 并发

初始：
`gpu_heavy_concurrency = 1`

CMS 可配置。

避免 ASR + 大模型同时争用显存或统一内存导致稳定性问题。Windows 与 Mac 分别通过 Phase 0A 确定可用模型和资源阈值。

---

# 15. Prompt / Parser Version

每个结构化任务保存：

- provider
- model
- prompt_version
- parser_version
- schema_version

支持以后 Replay 与对比。

---

# 16. 禁止

- Processor 内 import openai/ollama SDK；
- LLM 直接决定确定性日期/年龄；
- LLM 生成 POI 经纬度；
- LLM 输出没有 Evidence 的事实；
- 只保存最终自然语言摘要而丢失 Typed Result。
