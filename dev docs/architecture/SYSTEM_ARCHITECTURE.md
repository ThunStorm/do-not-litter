# System Architecture

## 1. 架构目标

第一版采用：

> **Mac mini 单节点 + LAN Browser Client + Local First + Local AI First + 可选外部 LLM**

但内部保持清晰模块边界，以便未来平滑演化为：

- 移动端薄客户端；
- 云 Control Plane；
- 多 Worker；
- GenericProcessor；
- SaaS。

---

# 2. 逻辑架构

```text
Clients
  │
  ├─ PC Browser
  └─ Mobile Browser（trusted LAN + access token）
       │
       ▼
React + TypeScript + Vite
       │
       ├─ REST
       └─ WebSocket
       ▼
FastAPI
       │
       ├─ Capture API
       ├─ Product Query API
       ├─ Admin API
       └─ Job WS
       │
       ▼
SQLite + Local Files
       ▲
       │
Independent Worker
       │
       ├─ Resolver Registry
       ├─ Video Resolver Registry
       │    ├─ Bilibili Resolver
       │    ├─ Subtitle Fetcher
       │    └─ yt-dlp Media Adapter
       ├─ Cover Fetcher / Derivative Generator
       ├─ Processor Router
       ├─ Recruitment Processor
       ├─ TravelFood Processor
       ├─ Evidence Validator
       ├─ Rule Engine
       ├─ POI Resolver
       ├─ ASR Provider
       ├─ Transcript Corrector
       ├─ AI Note Generator
       ├─ Screenshot Planner / Frame Extractor
       ├─ Place Note Builder
       └─ LLM Router
             │
             ├─ Ollama
             ├─ OpenAI Provider
             └─ OpenAI-Compatible Provider（DeepSeek / Xiaomi MiMo / custom）
```

---

# 3. 物理运行架构

第一版不做微服务。

开发阶段至少三个进程：

```text
1. FastAPI / Uvicorn
2. Worker Process
3. React Vite Dev Server
```

手机和 PC 浏览器通过同一可信局域网访问 Mac mini。开发与生产都必须支持可配置监听地址；默认不做公网暴露。所有非 localhost 的 REST/WebSocket 请求必须带有效访问 Token，Admin API 不允许匿名访问。

生产/桌面封装后：

```text
launchd
 ├─ cn.zhijian.api
 ├─ cn.zhijian.worker
 └─ FastAPI 同源提供 UI
```

后续可使用 Tauri 封装，但桌面壳不属于 MVP 前置条件。

---

# 4. FastAPI 职责

允许：

- API；
- WebSocket；
- 请求校验；
- 配置读写；
- 查询；
- Job 创建；
- 结果读取。

禁止：

- 在 HTTP 请求中直接跑 Whisper；
- 长时间执行 LLM；
- 下载大视频；
- 做长时 Playwright 抓取；
- 执行完整 Recruitment/Travel Pipeline。

长任务必须写入 `jobs`。

---

# 5. Worker 职责

Worker 循环：

```text
lease job
→ 执行
→ heartbeat
→ 更新进度
→ 写结果
→ 完成 / 失败 / NEEDS_USER
```

Worker 初期只有一个。

未来扩展多 Worker 时，不改变 Processor 接口。

---

# 6. Job Lease

Job 最少包含：

- id
- type
- status
- priority
- current_step
- progress
- lease_owner
- lease_expire_at
- heartbeat_at
- retry_count
- error
- created_at
- started_at
- finished_at

若 PC 异常关闭：

```text
RUNNING
+ heartbeat stale
→ lease expired
→ QUEUED
```

---

# 7. 核心模块

## capture/
统一接受 URL/Text/File。

Capture 在创建 Source/Job 前执行 `InputNormalizer`：区分纯 URL、带标题/分享话术的单链接文本、无链接正文和多链接文本。唯一 URL 被选中后，周围文字不得进入 Resolver、Classifier、LLM 或 Evidence；多链接歧义在 Intake 层返回候选，不启动下游网络请求。

## resolvers/
解决“如何读取内容”。

## processors/
解决“内容对应什么业务”。

## evidence/
解决“为什么这个结论可信”。

## ai/
解决“用哪个模型、如何结构化调用”。

## asr/
解决“如何转录音视频”。

## transcript_correction/
在 Note 生成前将 raw Transcript 分块送入 LLM 校对，保持 Segment ID/顺序/时间码不变，输出 corrected_text、置信度与变更原因；服务端负责覆盖率和无新增事实校验。

## poi/
解决“现实地点解析”。

## screenshots/
根据 Note Section、PlaceMention 与 Transcript 时间码规划并提取代表帧，执行清晰度、黑帧和重复检测；不等同于默认全视频多模态理解。

## covers/
从 VideoAsset 平台元数据下载真实封面，校验 HTTPS host、MIME、文件头、尺寸和字节数，按内容哈希保存原图并生成 16:9 列表衍生图。封面失败不阻塞 Note，列表使用明确占位。

## documents/
解决 PDF、DOCX、XLS/XLSX 与图片型文档的归一化。

## ocr/
解决扫描 PDF、PNG/JPEG 的中文 OCR、页码/边界框定位与低置信 Review。

## jobs/
解决“后台长任务”。

## repositories/
隔离业务层与数据库。

---

# 8. Resolver Registry

统一：

```python
class Resolver:
    def can_handle(self, source) -> bool: ...
    async def resolve(self, source) -> ResolvedContent: ...
```

ResolvedContent：

```text
title
author
published_at
metadata
segments[]
links[]
attachments[]
media[]
```

原则：

- Resolver 不做招聘判断；
- Resolver 不做推荐；
- Resolver 不修改 Profile。

视频 Resolver 的首个生产实现为 Bilibili，参考并适配 BiliNote 的 URL 解析、字幕优先、yt-dlp 下载和平台兼容逻辑。第三方代码必须封装在适配层；至简 Job、数据库、Evidence、POI 与 UI 不依赖 BiliNote 内部类型。完整边界见 `video/VIDEO_AI_NOTE_PIPELINE.md`。

---

# 9. Processor Router

当前路由：

```text
Recruitment
TravelFood
Unsupported
```

长期：

```text
Recruitment
TravelFood
Generic
Shopping
Learning
...
```

Processor 接口概念：

```python
class Processor:
    def can_handle(self, content) -> bool: ...
    async def process(self, content, context): ...
```

---

# 10. Provider 抽象

## LLMProvider
- OllamaProvider
- OpenAIProvider
- OpenAICompatibleProvider（DeepSeek、Xiaomi MiMo、自定义兼容端点）

## ASRProvider
- WhisperCppProvider
- FasterWhisperProvider（预留）
- CloudASRProvider（预留）

## POIProvider
- 第一版实现 AMapPOIProvider；
- 业务代码不得依赖具体厂商。

地图前端第一版使用高德地图 JS API 2.0。中国大陆 POI 的 `coordinate_system` 显式记录为 `GCJ02`，严禁把 GCJ-02 静默标成 WGS84；GeoJSON 导出必须附坐标系元数据与来源 Provider。

地图运行时以中国大陆全境为初始 viewport，通过 `bbox + zoom` 查询 Marker/cluster，不绑定默认城市。Marker 是 Place 的投影，用户的新增/隐藏/软删除状态由独立 Marker State 保存；地图浮窗读取轻量 Preview，详情页读取完整 Place Note。

---

# 11. Mac mini 本地 AI

Apple Silicon 使用 Metal；统一内存下 GPU 重任务初始并发为 1，ASR、LLM 和 Vision 不默认并行。完整运行时、内存约束与常驻规则见 `operations/DEPLOYMENT_OPTIONS.md`。

---

# 12. GPU Scheduler

第一版可以非常轻：

```text
GPU semaphore = 1
```

重量级任务：

- Whisper
- 主力 LLM
- Vision

串行。

轻量任务可并行：

- HTTP；
- Playwright；
- Excel；
- SQLite；
- ffmpeg 部分 CPU 工作；
- 文件下载。

后续根据实际显存与稳定性将并发调至 2。

---

# 13. 文件存储

```text
data/
├─ app.db
├─ permanent/
│  ├─ sources/
│  ├─ snapshots/
│  ├─ transcripts/
│  ├─ evidence/
│  └─ exports/
├─ browser/
│  └─ profile/
├─ models/
├─ cache/
│  ├─ video/
│  ├─ audio/
│  ├─ frames/
│  └─ temp/
└─ logs/
```

视频策略：

```text
下载视频（临时）
→ 抽音频
→ ASR
→ 提取必要 Evidence Frames
→ 删除原视频/音频
→ 永久保留 Transcript + Evidence
```

---

# 14. SQLite 策略

第一版 SQLite 足够。

开启：
- WAL；
- foreign_keys。

设计要求：
- 所有访问经过 Repository；
- migrations 使用 Alembic；
- JSON 仅用于适合嵌套的 AST/metadata，不把全部业务塞 JSON。

未来若迁 PostgreSQL，尽量限制在 Repository/Database 层。

---

# 15. Pipeline Replay

每一步必须有：
- input artifact；
- output artifact；
- status；
- version；
- error。

用户可：

```text
重新解析岗位条件
```

不必：
- 重新抓微信；
- 重新下载视频。

运行日志中的错误事件可作为 Replay 入口，但不成为执行器：`SystemEvent(entity_type=job, entity_id=job.id)` → Job 服务校验当前状态与来源事件 → 同一 Job 新 attempt 入队 → Worker 按 Pipeline 顺序执行。日志页只提交 `source_event_id`，不能修改步骤状态、选择 Provider 或跳过依赖。

错误恢复使用 Job 服务的步骤级 Replay：Step Artifact 在默认 24 小时窗口内有效时，上游完成步骤 REUSED，从失败步骤开始顺次执行当前及下游；到期或输入/版本失效后只允许完整重跑。日志和任务详情只展示 Replay Options，不允许任意 from_step，也不让用户逐个点击后续步骤。完整契约见 `jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md`。

Worker 进程存活与任务进度是不同信号。进程心跳由独立于同步 Job 执行循环的轻量通道定期持久化，不能依赖被外部模型、FFmpeg 或网络调用阻塞的主领取循环；Job 心跳只由真实阶段与 batch 活动推进。取消请求写入持久状态后，长模型批次在请求边界检查该状态并停止新请求，随后释放 lease；完整重跑必须等待这一确认。

---

# 16. Partial Materialization

不要求一个大任务全部完成后才出结果。

例如：
- 贵州 43 地点：36 个确认就先显示 36；
- 招聘 500 岗位：可分批 materialize。

这是长任务 UX 的核心。

---

# 17. 未来云化演进

第一版：
```text
手机 ↔ PC
```

未来：
```text
Clients
  ↓
Cloud Control Plane
  ↓
Execution Router
  ├─ Home PC
  ├─ Cloud CPU
  └─ Cloud GPU
```

因为当前 Processor/Provider/Job 已抽象，迁移时无需重构业务算法。
