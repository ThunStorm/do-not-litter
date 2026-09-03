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

视频 AI 笔记是明确例外：MVP 的 `VIDEO_NOTE_SUMMARY` 与 `TRAVEL_PLACE_EXTRACTION` 默认绑定用户已配置的 DeepSeek OpenAI-compatible Provider，以满足长字幕总结质量要求；用户仍可在 Settings 中改为其他兼容模型。业务代码只声明能力，不写死模型 ID 或直接读取 API Key。

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

## 4.1 Ollama 模型释放契约（已实施）

Mac mini 只有 16 GB 统一内存，本地模型调用不得依赖 Ollama 默认的 5 分钟驻留。`OllamaProvider` 对 `/api/chat` 的每次非流式请求都必须发送 `keep_alive: 0`，让模型在响应完成后立即卸载；任务推理、备用模型调用和设置页“真实测试”遵守同一规则。该参数是 Ollama 官方 API 对 `ollama stop <model>` 的等价能力，优先于为每次 HTTP 请求另起 CLI 子进程。

若兼容旧 Ollama 而保留 CLI 兜底，必须记录本次实际使用的本地模型，并在调用边界的 `finally` 中限时执行 `ollama stop <model>`；推理失败、JSON 解析失败、备用模型切换和用户取消也必须进入清理。停止失败只记录脱敏告警，不能把已成功的业务结果改成失败，也不能停止未由本次调用触发的其他模型。验收以响应返回后 `ollama ps` 在短时间内不再列出该模型为准。

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

生产环境：
- macOS Keychain

SQLite 只存 key reference。

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
- SCREENSHOT_PLANNING
- TRANSCRIPT_CORRECTION
- NOTE_TOC_AND_SECTION_SUMMARY

Router 决定 Provider + Model。

---

# 7. 本地硬件策略

Mac mini：
- Apple M4
- 16 GB 统一内存
- Metal

可以本地承担：
- 分类；
- 结构化提取；
- Recruitment DSL；
- Travel Trait；
- ASR；
- 未来视觉理解。

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
视觉 Stage 已完成 image-capable Profile 绑定校验；当前视频抽帧仍是确定性筛选，不会因为注册视觉阶段而自动上传帧或调用视觉模型。

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

原因：
macOS arm64 / Metal 环境。

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

避免 ASR + 大模型同时抢占显存导致稳定性问题。

---

# 15. Prompt / Parser Version

每个结构化任务保存：

- provider
- model
- prompt_version
- parser_version
- schema_version

支持以后 Replay 与对比。

视频笔记还必须保存：

- note_template_version；
- chunker_version；
- merge_prompt_version；
- transcript_id / input_hash；
- checkpoint 状态；
- 外部调用审计引用。

长 Transcript 使用 Provider 能力预算进行分块、局部总结和层级合并。所有 Pipeline AI 请求统一读取 `app:general` 调用策略：默认请求前等待 3 秒；429、408、409、425、超时、连接失败、可恢复 5xx 与空响应默认重试 1 次，每次至少等待 5 秒；429 优先采用 `Retry-After`。主模型耗尽重试后才切换不同故障域的备用模型。401/403、余额不足和模型不存在不做无效重试。

`SCREENSHOT_PLANNING` 只根据视频元数据、Note Section、PlaceMention 和 Transcript 时间范围提出候选时间码；最终抽帧、清晰度、黑帧与感知重复检测由确定性代码完成。MVP 不要求把所有视频帧发送给多模态模型。

`TRANSCRIPT_CORRECTION` 在 Note 生成前按字符预算与 Segment 数双门槛分块。默认每批 12,000 字符、最多 128 Segment、单次超时 180 秒；设置页基础校验范围分别为 2,000–24,000、16–256、30–300 秒。转写专属主/备用模型优先于推理路由，任一选项留空时继承对应推理模型。模型只能返回原 Segment ID 对应的 corrected_text、置信度和原因；服务端验证覆盖率、顺序与时间码，不接受新增/缺失 ID。

`NOTE_TOC_AND_SECTION_SUMMARY` 输出具体 heading、20–50 字 thesis、summary 和 bullets。禁止无信息套话；Section ID 和时间范围由服务端提供，模型不得自行编造锚点。

## Prompt Supplements v0.4.5

固定核心 Prompt 继续负责 JSON、Schema、字段、Segment ID、顺序和证据契约。设置页只允许用户给 `transcript_correction / video_note_summary / travel_place_extraction` 添加低优先级表达偏好，例如语气、篇幅、目标读者和关注重点。保存时服务端拒绝试图覆盖系统规则、JSON、字段、ID 或顺序的内容；模型返回仍经过原有解析和证据校验。默认入口及完整契约见 `PROMPT_SUPPLEMENTS_V045_SPEC.md`。

---

# 16. 禁止

- Processor 内 import openai/ollama SDK；
- LLM 直接决定确定性日期/年龄；
- LLM 生成 POI 经纬度；
- LLM 输出没有 Evidence 的事实；
- 只保存最终自然语言摘要而丢失 Typed Result。
