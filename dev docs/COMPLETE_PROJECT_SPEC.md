# AI Personal Inbox / Personal Scout
## Complete Project Specification

> GENERATED FILE. Edit the source documents in this directory, then run `python scripts/build_complete_project_spec.py`.


---

# FILE: README.md

# AI Personal Inbox / Personal Scout
## 项目文档索引

> 文档版本：v0.2
> 冻结日期：2026-08-13
> 当前阶段：需求与架构基线已完成，可进入 Phase 0A 技术验证与工程实施
> 第一阶段部署形态：Windows 11 本地优先，PC 作为完整后端与 AI Worker，手机通过可信局域网访问
> 第一阶段业务范围：北京市公务员/事业单位招聘 + 中国范围 Travel/Food

---

## 1. 产品一句话定义

这是一个“**随手分享信息 → AI 自动解析 → 结合个人信息/偏好 → 形成可信、可执行结果**”的个人 AI 信息处理与决策系统。

第一版不追求接纳所有信息，而只聚焦两个当前高价值场景：

1. **招聘/事业编/考试信息**
   - 解析公众号、官网、PDF、Excel 岗位表；
   - 自动下钻官方来源；
   - 提取报名期限、考试时间、岗位条件；
   - 结合个人档案进行资格筛选；
   - 输出倒计时、待办、符合/不符合/待确认岗位；
   - 所有事实保留证据链。

2. **旅行/探店信息**
   - 接收 Bilibili 等视频/图文链接；
   - 获取字幕或执行 ASR；
   - 提取餐馆、景点、菜品、地点评价与注意事项；
   - 将地点解析为现实地图 POI；
   - 结合用户偏好筛选；
   - 输出地图、地点列表、想去/去过状态及来源证据。

长期目标是在不推翻第一版架构的前提下，扩展为：

> **可自动接纳未知非结构化信息，通过 GenericProcessor + 专用 Processor 体系进行理解、归类、总结、行动化和可视化的个人 AI 信息操作系统。**

---

## 2. 最重要的产品原则

### 2.1 默认零操作
用户核心动作是“分享/粘贴链接”，后台自动处理，完成后允许用户修正。

### 2.2 AI 先做到 B 级，不直接做到 C 级
当前能力：
- 判断；
- 筛选；
- 生成待办；
- 生成材料 Checklist；
- 生成咨询建议；
- 生成地图；
- 生成可导出结构化结果。

未来 C 级能力：
- 自动填写报名页面；
- 自动操作第三方系统；
- 自动发邮件/提交表单；
- 需额外权限、风控、审计与用户确认机制。

### 2.3 AI 可以推理，但不能伪装成事实
任何事实性结论必须可回溯到：
- 网页原文；
- PDF 页码；
- Excel 单元格；
- 视频时间码；
- 其他明确来源。

### 2.4 产品做窄，内核留宽
第一版 UI 只展示招聘与旅行/探店。
底层仍按：
`Capture → Resolver → Processor Router → Processor → Evidence → Result → View`
设计。

### 2.5 Unknown 第一版不污染产品
第一版不支持的内容：
- 默认标记 `UNSUPPORTED`；
- 可选择仅保存链接或删除；
- 不自动创建乱七八糟的新分类；
- 后续通过 GenericProcessor 扩展。

---

## 3. 文档目录

| 文档 | 用途 |
|---|---|
| [PRODUCT_REQUIREMENTS.md](./PRODUCT_REQUIREMENTS.md) | 产品需求、用户场景、功能边界、MVP |
| [SYSTEM_ARCHITECTURE.md](./SYSTEM_ARCHITECTURE.md) | 总体架构、模块边界、运行方式 |
| [DATA_MODEL.md](./DATA_MODEL.md) | 领域对象、数据库表、Claim/Evidence 数据模型 |
| [RECRUITMENT_PIPELINE.md](./RECRUITMENT_PIPELINE.md) | 招聘完整处理链、DSL、MajorMatcher、资格判断 |
| [TRAVEL_FOOD_PIPELINE.md](./TRAVEL_FOOD_PIPELINE.md) | 视频/图文处理、ASR、POI、偏好学习、地图 |
| [AI_RUNTIME_AND_PROVIDERS.md](./AI_RUNTIME_AND_PROVIDERS.md) | 本地/外部模型、ASR、模型路由、Provider 抽象 |
| [CONTROL_CENTER.md](./CONTROL_CENTER.md) | CMS/控制后台设计 |
| [API_DESIGN.md](./API_DESIGN.md) | REST / WebSocket API 边界 |
| [SECURITY_PRIVACY.md](./SECURITY_PRIVACY.md) | 本地优先、API Key、浏览器登录态、敏感数据 |
| [TESTING_AND_ACCEPTANCE.md](./TESTING_AND_ACCEPTANCE.md) | 测试策略、关键验收用例 |
| [GOLDEN_SAMPLES.md](./GOLDEN_SAMPLES.md) | 首批真实样本、Fixture 规则、技术 Spike 与质量门槛 |
| [PROJECT_PLAN.md](./PROJECT_PLAN.md) | Codex/Agent 可直接执行的工程实施计划 |
| [FUTURE_ROADMAP.md](./FUTURE_ROADMAP.md) | GenericProcessor、移动端、云、多 Worker、C 级自动化 |
| [ARCHITECTURE_DECISIONS.md](./ARCHITECTURE_DECISIONS.md) | 关键设计决策与原因 |

`COMPLETE_PROJECT_SPEC.md` 是由上述分文档自动生成的合订本，不作为独立编辑源。修改分文档后运行 `python scripts/build_complete_project_spec.py` 重新生成。

---

## 4. 当前硬件基线

开发/运行主机：

- 设备名：`WILLIAM-PC`
- OS：Windows 11 x64
- CPU：AMD Ryzen 7 5800X，8C/16T
- RAM：32 GB
- GPU：AMD Radeon RX 7900 XT，20 GB VRAM
- 存储：总 4.61 TB，当前已使用约 3.30 TB

这台机器承担：

- FastAPI 服务；
- SQLite 数据库；
- Playwright Browser Resolver；
- Bilibili/视频解析；
- ffmpeg；
- whisper.cpp ASR；
- Ollama 本地大模型；
- 独立 Worker；
- Web Control Center；
- 本地文件存储。

---

## 5. 第一阶段技术基线

### Frontend
- React
- TypeScript
- Vite
- Node.js 20.19+ 或 22.12+
- 响应式 Web
- 后期可封装 Tauri 桌面壳
- 手机第一版通过同一可信局域网访问响应式 Web

### Backend
- Python 3.12+
- FastAPI
- Uvicorn
- Pydantic
- SQLAlchemy 2.x
- Alembic
- SQLite + WAL
- 独立 Worker Process
- WebSocket 进度推送

### AI / Parsing
- Ollama
- 外部大模型 Provider（API Key 可配置）
- OpenAI-Compatible Provider
- whisper.cpp
- Playwright
- yt-dlp / 平台解析能力
- ffmpeg
- openpyxl
- `.xls` legacy adapter（Phase 0A 选择 xlrd 或 python-calamine）
- PDF Parser
- DOCX Parser
- 中文 OCR（扫描 PDF / PNG / JPEG）
- 高德 POI Web 服务 + 地图 JS API 2.0
- DeepSeek / Xiaomi MiMo 等 OpenAI-compatible 外部 Provider

---

## 6. 第一版明确不做

- 云端业务数据库
- Redis
- Celery
- RabbitMQ
- PostgreSQL
- Vector DB
- 微服务
- 多用户/多租户
- 社交
- 付费
- Agent Marketplace
- 动态 Skill 自动生成
- 自动创建任意 Space
- 长期 Source Watch（仅预留接口）
- 自动报名/自动提交第三方表单
- iOS / Android / 微信小程序同时开发
- 泛知识收集器

---

## 7. 从第一版到长期产品的演化主线

```text
V0.1
RecruitmentProcessor
TravelFoodProcessor
Unknown → Unsupported

        ↓

V0.2+
GenericProcessor
Unknown → 摘要 / 关键事实 / 日期 / 人物 / 地点 / 行动项

        ↓

V0.x
高频 Generic 场景
→ Configurable Processor

        ↓

V1.x
成熟高频场景
→ Dedicated Processor

        ↓

长期
个人 AI 信息处理与行动平台
```

---

## 8. 开发原则

1. **不得把业务逻辑写进 Resolver。**
2. **不得在业务代码中直接调用具体 LLM SDK。**
3. **不得让 LLM 负责确定性计算。**
4. **不得生成没有 Evidence 的事实性 Claim。**
5. **不得把现实 POI 坐标交给 LLM 编造。**
6. **不得因为未来可能需要而提前实现大平台。**
7. **允许定义扩展接口，但不提前实现不属于 MVP 的能力。**
8. **Pipeline 必须可重放、可重跑、可审计。**
9. **长任务必须持久化，PC 重启后可恢复。**
10. **原始证据优先，AI 解释次之。**


---

# FILE: PRODUCT_REQUIREMENTS.md

# Product Requirements
## AI Personal Inbox / Personal Scout

> 状态：Baseline v0.2
> 当前产品策略：Narrow Product, Extensible Core

---

# 1. 背景与问题

用户希望把日常“随手看到、随手保存”的非结构化信息，转化为后续真正能支持工作和生活决策的结构化结果。

当前典型问题：

- 收藏链接后长期不再打开；
- 微信公众号、视频、网页、附件信息散乱；
- 招聘公告中真正重要的是报名时间、岗位条件、附件，而不是全文摘要；
- 探店/旅行视频真正重要的是地点、地图、推荐理由和后续是否想去，而不是一段视频总结；
- 同一主题的信息散布在不同来源，缺少统一组织；
- 用户不希望频繁手动分类；
- 用户要求 AI 的事实结论必须可追溯，不能随意发挥。

---

# 2. 产品核心目标

用户只需完成一个高频动作：

> **把链接分享或粘贴给系统。**

系统后台自动完成：

```text
Capture
→ Resolve
→ Understand
→ Verify
→ Personalize
→ Materialize
→ Action
```

最终结果不是“AI 摘要”，而是：

- 倒计时；
- 待办；
- 岗位资格列表；
- 需要补充的个人信息；
- 地图；
- 地点清单；
- 想去/去过；
- 证据；
- 来源；
- 可导出数据。

---

# 3. 第一阶段目标用户

## P0
产品作者本人。

## P1
未来具有类似需求的普通个人用户。

第一阶段不做团队、企业、组织协作。

---

# 4. 第一阶段核心场景

## 4.1 Recruitment

用户输入：

- 微信公众号事业编汇总文章；
- 政府招聘公告；
- 招聘 PDF；
- 扫描 PDF、PNG/JPEG 公告；
- DOCX 公告/附件；
- 岗位 Excel；
- 报名说明页面。

系统输出：

- 招聘批次；
- 岗位列表；
- 报名开始/截止；
- 资格审查；
- 缴费；
- 笔试/面试时间；
- 每个岗位的要求；
- 用户是否符合；
- `PASS / FAIL / UNKNOWN / REVIEW`；
- 缺失个人资料；
- 倒计时；
- 待办；
- 咨询建议；
- 所有条件的原文证据。

## 4.2 Travel / Food

用户输入：

- Bilibili 视频；
- 未来扩展抖音、YouTube、快手；
- 普通旅行图文网页。

系统输出：

- 视频/内容来源；
- 字幕；
- 餐馆候选；
- 景点候选；
- 菜品；
- 价格/评价等 Observation；
- 地图 POI；
- 地点列表；
- 作者观点；
- AI 个性化推荐；
- 用户想去/去过/不感兴趣；
- 来源时间码；
- CSV/JSON/GeoJSON 导出。

## 4.3 第一阶段地域与来源基线

- Recruitment 首域：北京市公务员、事业单位招聘及相关考试公告；
- Travel/Food：第一版按中国范围设计；
- POI 与底图首选高德地图；
- 首批真实样本与 Fixture 规则见 `GOLDEN_SAMPLES.md`。

---

# 5. 核心体验原则

## 5.1 默认零操作

成功路径：

```text
分享链接
→ 系统回复“已收下”
→ 后台处理
→ 完成后出现在对应页面
```

用户不应在每次分享后被要求选择分类。

## 5.2 只有异常时才介入

例如：

- 分类不明确；
- 微信需要登录；
- POI 无法唯一确认；
- 招聘专业存在语义歧义；
- 个人档案缺少关键字段；
- 外部页面需要验证码。

这时进入：

`NEEDS_USER`

---

# 6. Intake Policy

第一版允许进入主业务体系：

### Recruitment
- 事业单位招聘
- 公务员/考试
- 招聘岗位
- 招聘附件
- 报名公告

### Travel/Food
- 旅行攻略
- 景点推荐
- 探店
- 餐厅推荐
- 美食视频

### 其他
默认：

`UNSUPPORTED`

UI 可提供：

- 仅保存链接；
- 删除。

第一版不自动创建新的业务分类。

第一版 Capture 支持：

- URL 粘贴；
- PDF / DOCX / XLS / XLSX 文件上传；
- PNG / JPEG 图片上传；
- 直接文本作为补充输入。

上传文件与 URL 入口使用相同的 Job、Evidence 与 Processor Router，不建立第二套处理链。

---

# 7. 个人档案策略

不要求用户第一次填写完整档案。

采用渐进式补充：

```text
系统发现：
76 个岗位因为“基层工作经历”未知无法判断

→ 提问：
是否具有 2 年以上基层工作经历？

回答一次
→ 自动重算 76 个岗位
```

个人信息分层：

- 普通偏好；
- 敏感 Profile；
- 高敏感 Local Only。

---

# 8. AI 角色边界

AI 可以：

- 理解自然语言；
- 分类；
- 提取字段；
- 转换 Requirement DSL；
- 识别作者观点；
- 提取地点特征；
- 提出推荐；
- 生成咨询话术；
- 生成建议性 Todo。

AI 不应：

- 自己计算年龄并直接作为事实；
- 自己编造报名日期；
- 自己编造地图坐标；
- 把“相关专业”语义相似直接判定 PASS；
- 把推荐结论伪装成来源事实；
- 自动提交第三方系统。

---

# 9. 事实模型

任何结论归类为：

1. `EXTRACTED`
   - 原文明确存在。

2. `NORMALIZED`
   - 对原文进行标准化，如“8月26日下午5点” → 时间戳。

3. `COMPUTED`
   - 程序计算，如“剩余 7 天”。

4. `INFERRED`
   - AI 推断，如“这家店可能符合你的偏好”。

UI 必须能区分。

---

# 10. 来源冲突

来源优先级参考：

```text
官方原始文件
>
官方网页
>
招聘单位官网
>
官方公众号
>
第三方转载/视频
>
AI 推断
```

发生冲突：

- 不静默覆盖；
- 保留多个 Claim；
- 显示 Source Conflict；
- 当前采用高权威来源；
- 用户可查看全部证据。

---

# 11. Recruitment 用户体验目标

首页优先回答：

1. 最近什么要截止？
2. 哪些岗位我能报？
3. 哪些岗位更值得我关注？
4. 现在我需要做什么？

岗位结果不采用单一虚假百分比，而拆成：

- Eligibility
- Preference
- Urgency
- UserState

Eligibility：
- PASS
- FAIL
- UNKNOWN
- REVIEW

用户状态：
- DISCOVERED
- INTERESTED
- PREPARING
- APPLIED
- DROPPED

---

# 12. Travel 用户体验目标

首页优先回答：

1. 我多久没有旅行？
2. 最近发现了什么值得去的地点？
3. 哪些地点最符合我的偏好？
4. 地图上都在哪里？

地点用户状态：

- DISCOVERED
- SAVED
- PLANNED
- VISITED
- DISMISSED

---

# 13. Control Center 是 MVP 核心

不是开发附属后台。

必须让用户看到：

- 正在处理什么；
- 等待什么；
- 是否等待 PC；
- 哪一步失败；
- ASR 进度；
- POI 解析；
- 招聘解析；
- 当前模型；
- 是否使用外部 API；
- 单步骤重跑；
- 整条任务重试；
- 查看 Evidence；
- 修改模型/ASR/数据目录等配置。

---

# 14. MVP 非功能目标

## 稳定性
- PC 重启后任务不丢；
- 失败任务可重试；
- Pipeline 可从中间步骤重跑。

## 可审计性
- 所有核心事实可回溯证据；
- 记录模型、Prompt/Parser 版本；
- 记录 Processor 版本。

## 本地优先
- 默认数据保存在 PC；
- 手机通过可信局域网访问 PC，不在手机保存完整业务数据库；
- LAN API、WebSocket 与 Admin API 必须验证访问 Token；
- 外部模型只是可选 Provider；
- API Key 安全存储；
- 浏览器登录态不导出。

## 扩展性
- 新 Resolver 不修改业务 Processor；
- 新 Processor 不修改 Capture；
- 新模型不修改业务代码；
- 新 POI Provider 不修改 Travel Processor。

---

# 15. 第一版不做

详见 README，重点包括：

- GenericProcessor 实际处理；
- 动态 Space；
- Source Watch 自动监控；
- 云端多用户；
- 自动报名；
- 全平台移动端；
- 复杂推荐机器学习；
- 通用 Agent 系统。

这些能力记录于 FUTURE_ROADMAP.md。


---

# FILE: SYSTEM_ARCHITECTURE.md

# System Architecture

## 1. 架构目标

第一版采用：

> **Windows PC 单节点 + LAN Mobile Client + Local First + Local AI First + 可选外部 LLM**

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
       ├─ Processor Router
       ├─ Recruitment Processor
       ├─ TravelFood Processor
       ├─ Evidence Validator
       ├─ Rule Engine
       ├─ POI Resolver
       ├─ ASR Provider
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

手机通过同一可信局域网访问 PC。开发与生产都必须支持可配置监听地址；默认不做公网暴露。所有非 localhost 的 REST/WebSocket 请求必须带有效访问 Token，Admin API 不允许匿名访问。

生产/桌面封装后：

```text
PersonalAI.exe / launcher
 ├─ backend process
 ├─ worker process
 └─ UI
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

## poi/
解决“现实地点解析”。

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

---

# 11. Windows + AMD 本地 AI

当前硬件：

- Ryzen 7 5800X
- 32 GB RAM
- RX 7900 XT 20 GB

建议策略：

- 本地模型做分类、结构化抽取、偏好推断；
- 外部模型只在失败/低置信/用户手动时增强；
- GPU 重任务初始并发为 1；
- ASR 与 LLM 不默认同时抢显存。

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


---

# FILE: DATA_MODEL.md

# Data Model

## 1. 数据建模原则

1. 原始来源与业务结果分离。
2. Claim 与 Evidence 分离。
3. “视频中提到某地点”与“现实 POI”分离。
4. 招聘资格与用户偏好分离。
5. 个人 Profile 与 Preference 分离。
6. 原始行为事件与推导出的 Preference 分离。
7. AST/复杂嵌套规则可用 JSON；核心实体用关系表。
8. 所有结果保留 processor/model/version。

---

# 2. 核心领域对象

## ContentItem
用户一次输入。

## Source
外部信息源。

## Snapshot
某 Source 某次抓取内容。

## Segment
可定位的最小文本/字幕/表格单位。

## Claim
事实、标准化结果、计算或推断。

## Evidence
支持某 Claim 的来源定位。

## RecruitmentNotice
一场招聘。

## Position
具体岗位。

## Requirement
岗位/公告资格规则 AST。

## PlaceMention
内容中提到的地点。

## Place
解析后的现实 POI。

## UserProfile
客观个人条件。

## Preference
主观偏好。

## Job / JobStep
后台处理工作。

---

# 3. Content / Source

## content_items

建议字段：

```text
id
input_type
original_url
raw_text
status
processor_hint
created_at
updated_at
```

## sources

```text
id
content_item_id
source_type
platform
url
external_id
title
publisher
author
published_at
authority_level
metadata_json
created_at
```

文件型 Source 的 `metadata_json` 至少保存：原始文件名、MIME、字节数、内容哈希、解析器与 OCR 版本；文件正文仍通过 Snapshot/Segment 建模。

## source_snapshots

```text
id
source_id
fetched_at
content_hash
raw_path
normalized_path
metadata_json
```

## source_relations

```text
id
from_source_id
to_source_id
relation_type
evidence_segment_id
```

relation_type：
- references
- attachment
- original_source
- registration
- supplement
- supersedes
- related
- derived_from

---

# 4. Segment

## segments

```text
id
snapshot_id
segment_type
sequence_no
text
locator_json
metadata_json
```

locator 示例：

网页：
```json
{"css_path":"...", "start_offset":10, "end_offset":50}
```

视频：
```json
{"start_ms":197200, "end_ms":211500}
```

Excel：
```json
{"sheet":"岗位计划表","row":27,"cell":"H27"}
```

PDF：
```json
{"page":7,"block":13}
```

DOCX：
```json
{"part":"document","paragraph":18,"run_start":2,"run_end":5}
```

OCR：
```json
{"page":3,"bbox":[120,240,920,318],"ocr_confidence":0.91}
```

---

# 5. Claim / Evidence

## claims

```text
id
subject_type
subject_id

claim_type
field
value_json

confidence

processor
processor_version
model_provider
model_name
parser_version

created_at
```

claim_type：
- EXTRACTED
- NORMALIZED
- COMPUTED
- INFERRED

## claim_evidences

```text
claim_id
segment_id
evidence_role
```

一个 Claim 可以多证据。
一个 Segment 可以支持多个 Claim。

## claim_relations

```text
from_claim_id
to_claim_id
relation_type
created_at
```

relation_type：
- derived_from
- normalizes
- computes_from
- conflicts_with
- supersedes

`NORMALIZED`、`COMPUTED` Claim 必须通过关系指向其输入 Claim；来源冲突不得只靠覆盖最终字段表达。

---

# 6. Recruitment

## recruitment_notices

```text
id
primary_source_id
title
organization
region
registration_start
registration_deadline
exam_date
interview_date
registration_url
status
created_at
```

## positions

```text
id
notice_id
position_code
name
organization
headcount
raw_row_json
created_at
```

## requirements

```text
id
notice_id nullable
position_id nullable

raw_text
dsl_version
ast_json

parser_model
parser_version
evidence_status

created_at
```

## requirement_matches

```text
id
requirement_id
position_id
profile_subject

status
reason_code
details_json
matched_evidence_json
created_at
```

status:
- PASS
- FAIL
- UNKNOWN
- REVIEW

## position_matches

```text
id
position_id
eligibility_status
preference_level
urgency_level
user_state
summary_json
updated_at
```

user_state:
- DISCOVERED
- INTERESTED
- PREPARING
- APPLIED
- DROPPED

---

# 7. User Profile

## profile_fields

```text
id
field_key
value_json
sensitivity
source
verified
updated_at
```

sensitivity:
- NORMAL
- SENSITIVE
- LOCAL_ONLY

## education_experiences

```text
id
level
school
raw_major_name
mapped_catalog_id
mapped_major_code
degree
graduation_date
verified
```

必须保留 `raw_major_name`，不允许映射结果覆盖原始专业名称。

## work_experiences（可在 Phase 2 引入）

```text
id
organization
role
start_date
end_date
description
tags_json
```

## certificates（可独立表或 profile JSON）

---

# 8. Major Catalog

## major_catalogs

```text
id
authority
name
version
education_level
effective_date
source_url
snapshot_id
```

## major_entries

```text
id
catalog_id
code
name
parent_code
level
aliases_json
```

## major_equivalences

```text
id
from_catalog_id
from_code
to_catalog_id
to_code
relation_type
evidence_source_id
```

---

# 9. Deadline / Todo

## deadlines

```text
id
subject_type
subject_id
deadline_type
at
claim_id
status
```

## todos

```text
id
subject_type
subject_id
title
todo_type
source_type
due_at
status
metadata_json
```

source_type：
- FACT_BASED
- SYSTEM_SUGGESTED

---

# 10. Travel / Food

## places

```text
id
name
place_type
country
province
city
district
address
latitude
longitude
coordinate_system

external_provider
external_poi_id

resolution_status
metadata_json
created_at
```

resolution_status:
- CANDIDATE
- CONFIRMED
- REVIEW
- UNRESOLVED
- REJECTED

中国大陆高德 POI 的 `coordinate_system` 为 `GCJ02`。任何导出都必须携带该字段，不得默认标记为 WGS84。

## place_mentions

```text
id
source_id
segment_id
raw_name
place_type
city_hint
district_hint
resolved_place_id
resolution_confidence
status
metadata_json
```

## place_observations

```text
id
place_id
source_id
segment_id
observation_type
value_json
claim_id
observed_at
```

例如：
- price
- dish
- author_opinion
- warning
- ranking
- recommended_season

---

# 11. Preference

## preference_events

```text
id
target_type
target_id
event_type
created_at
metadata_json
```

event_type：
- SAVE
- DISMISS
- VISITED
- PLANNED
- LIKE
- DISLIKE

## preferences

```text
id
preference_key
weight
source_type
confidence
version
updated_at
```

source_type：
- EXPLICIT
- BEHAVIOR
- INFERRED

优先级：
EXPLICIT > BEHAVIOR > INFERRED

## visit_events

```text
id
place_id
trip_id nullable
visited_at
rating nullable
notes nullable
```

地点当前用户状态由 `preference_events` / `visit_events` 投影得到；若为查询性能物化缓存，缓存必须可从事件重建，不能成为唯一事实源。

---

# 12. Jobs

## jobs

```text
id
job_type
status
priority

content_item_id
subject_type
subject_id

current_step
progress

lease_owner
lease_expire_at
heartbeat_at

retry_count
max_retries
idempotency_key
error_code
error_message

created_at
started_at
finished_at
```

`idempotency_key` 对同一 Capture/Step 的重复提交建立唯一约束。Job Lease 必须通过单条条件更新原子抢占；Step 输出与领域写入按版本幂等 upsert，防止 Worker 崩溃恢复后重复物化。

status：
- QUEUED
- RUNNING
- DONE
- FAILED
- RETRYABLE
- NEEDS_USER
- CANCELLED

## job_steps

```text
id
job_id
step_name
status
progress
input_ref_json
output_ref_json
version
error_message
started_at
finished_at
```

## settings / secret references

非敏感设置可存 SQLite；API Key、LAN Token 与其他 Secret 只保存 Windows Credential Manager/DPAPI 引用。数据库字段包含 `setting_key/value_json/updated_at` 与 `secret_key/secret_ref/updated_at`，不得存 Secret 明文。

---

# 13. 不建议第一版建的表

- dynamic_spaces
- skill_marketplace
- agent_memory
- vector_embeddings
- cloud_workers
- tenants
- payments

它们均属于未来能力，不提前实现。


---

# FILE: RECRUITMENT_PIPELINE.md

# Recruitment Pipeline

## 1. 目标

将招聘公告、微信公众号、官网、PDF、Excel 岗位表，转换为：

- 招聘批次；
- 岗位；
- 报名/考试时间；
- 可执行 Requirement DSL；
- 证据；
- 用户资格判断；
- 缺失 Profile；
- 待办；
- 推荐；
- 冲突提示。

第一阶段优先覆盖北京市公务员、事业单位招聘及相关考试公告；真实样本见 `GOLDEN_SAMPLES.md`。

---

# 2. 总流程

```text
URL / File
↓
CAPTURE
↓
RESOLVE_SOURCE
↓
DISCOVER_LINKS
↓
FOLLOW_SOURCES
↓
NORMALIZE_DOCUMENTS
↓
OCR（扫描 PDF / 图片时）
↓
EXTRACT_NOTICE
↓
EXTRACT_POSITIONS
↓
BUILD_REQUIREMENTS
↓
VALIDATE_EVIDENCE
↓
MATCH_PROFILE
↓
GENERATE_DEADLINES
↓
GENERATE_TODOS
↓
RANK / MATERIALIZE
```

---

# 3. 微信 Resolver

优先：

1. 直接 HTTP；
2. Playwright 专用浏览器 Profile；
3. NEEDS_USER。

专用 Browser Profile：

```text
data/browser/profile/
```

不得复用/提交到 Git。
首次用户扫码/登录后持久保存状态。

---

# 4. Link Discovery

招聘公众号常只是入口。

必须提取：
- `<a href>`
- PDF
- XLS/XLSX
- DOC/DOCX
- 官方网站
- 报名入口

规则 + AI 分类：

- FOLLOW
- RECORD_ONLY
- IGNORE
- UNKNOWN

默认：
- max_depth = 2
- max_followed_links_per_source = 30

避免无限爬取。

---

# 5. Source Graph

例如：

```text
公众号汇总
  ├─ references → 政府招聘公告
  │                ├─ attachment → 岗位表.xlsx
  │                └─ registration → 报名入口
  └─ references → 另一官方公告
```

官方附件优先级高于公众号转载。

---

# 6. Document Normalization

统一为：

```text
NormalizedDocument
├─ Metadata
├─ Sections[]
├─ Tables[]
├─ Segments[]
├─ Attachments[]
└─ SourceLocators[]
```

MVP 文档矩阵：

- HTML；
- 文本型 PDF；
- 扫描 PDF；
- DOCX；
- XLS/XLSX；
- PNG/JPEG。

OCR 必须保留页码、边界框、OCR 置信度与原始图片引用。低置信 OCR 不可直接支撑关键日期或 HARD Requirement 的自动确定结论，必须进入 `REVIEW`。

---

# 7. Excel Normalizer

处理：

- 多 Sheet；
- 标题行不固定；
- 合并单元格；
- 隐藏列；
- 备注列；
- 列名差异。

`.xlsx` 先用 openpyxl 读取；旧 `.xls` 通过独立 SpreadsheetReader 适配器处理，Phase 0A 在 xlrd/python-calamine 中按 Windows 安装、格式覆盖和维护状态选择，不允许把 `.xls` 伪装成 openpyxl 支持。

AI 只做 Column Mapping：

```text
岗位名称 → position_name
专业要求 → major_requirement
其他资格条件 → other_requirements
```

不得直接把整本 Excel 当纯文本让模型自由理解。

---

# 8. RecruitmentNotice

字段：

- title
- organization
- region
- registration_start
- registration_deadline
- exam_date
- interview_date
- registration_url
- general_requirements
- sources

---

# 9. Position

字段：

- position_code
- name
- organization
- headcount
- requirements
- source_row

一个 Notice 可包含数百 Position。

---

# 10. Requirement DSL v1.0

节点：

- ALL
- ANY
- NOT
- CONDITION

Condition：

```json
{
  "type": "CONDITION",
  "field": "education_level",
  "operator": "gte",
  "value": "bachelor",
  "rule_type": "HARD",
  "evidence_ids": ["segment_xxx"]
}
```

rule_type：
- HARD
- SEMANTIC
- PREFERENCE

---

# 11. DSL 示例

原文：

> 本科及以上，年龄 35 周岁以下，计算机科学与技术或软件工程专业，具有 PMP 优先。

AST：

```text
ALL
├─ education >= bachelor          HARD
├─ age <= 35                      HARD
├─ ANY
│  ├─ major = 计算机科学与技术     HARD
│  └─ major = 软件工程             HARD
└─ PMP                            PREFERENCE
```

PMP 不参与 Eligibility Fail。

---

# 12. Rule Engine

原子状态：

- PASS
- FAIL
- UNKNOWN
- REVIEW

ALL：

```text
有 FAIL        → FAIL
无 FAIL 有 UNKNOWN → UNKNOWN
无 FAIL/UNKNOWN 有 REVIEW → REVIEW
否则 → PASS
```

ANY：

```text
有 PASS → PASS
全部 FAIL → FAIL
否则有 REVIEW → REVIEW
否则 → UNKNOWN
```

---

# 13. MajorMatcher

优先级：

1. 专业代码精确匹配
2. 指定目录名称精确匹配
3. 专业类包含
4. 官方新旧专业映射
5. 公告明确允许的其他官方映射
6. 语义相似

第 6 级：
**只能 REVIEW，不自动 PASS。**

---

# 14. Catalog Registry

公告若明确指定专业目录：

> 必须优先使用公告指定目录。

本地没有时：
`FETCH_CATALOG`

逐步缓存用户实际遇到的目录，而不是第一版抓全中国所有目录。

---

# 15. EducationExperience

用户可有多个学历阶段。

每条：

- level
- school
- raw_major_name
- mapped_catalog
- mapped_code
- degree
- graduation_date

Requirement scope 支持：

- undergraduate
- graduate
- any_education
- highest_degree

---

# 16. 年龄处理

禁止让 LLM 直接做最终计算。

流程：

```text
原文年龄条件
→ DSL
→ reference_date
→ Python date calculation
→ PASS/FAIL
```

如公告给出“年龄计算截止日期”，必须使用公告日期。

---

# 17. 工作经历

例：

> 具有 2 年以上项目管理相关工作经验

拆：

- duration ≥ 24 months：程序计算；
- domain = project_management：语义判断。

语义不确定：
`REVIEW`

---

# 18. Missing Profile Analyzer

统计所有 UNKNOWN 的原因。

例如：

```text
基层经历未知 → 影响 76 个岗位
政治面貌未知 → 影响 8 个
证书未知 → 影响 3 个
```

优先提问信息收益最大的字段。

---

# 19. Information Gain

基础：

```text
QuestionPriority
≈ affected_positions
× deadline_weight
× position_importance
```

让用户每次补最少信息，解决最多岗位。

---

# 20. Eligibility / Preference / Urgency

三个维度彻底分离。

### Eligibility
- PASS
- FAIL
- UNKNOWN
- REVIEW

### Preference
- HIGH
- MEDIUM
- LOW

### Urgency
- HIGH
- MEDIUM
- LOW

禁止展示混合意义的“92% 匹配度”。

---

# 21. UserState

- DISCOVERED
- INTERESTED
- PREPARING
- APPLIED
- DROPPED

`DROPPED` 后不再持续提醒。

---

# 22. Deadline / Todo

Deadline 来自 Claim。

Todo 分：

- FACT_BASED
- SYSTEM_SUGGESTED

例如：
“8 月 19 日前缴费”是 FACT_BASED。
“建议提前 3 天准备材料”是 SYSTEM_SUGGESTED。

---

# 23. 时间冲突

第一版应检测：

- 报名冲突无需处理；
- 笔试/面试同时间；
- 用户关注岗位之间的显式日期冲突。

未来可加入跨城市交通可达性。

---

# 24. 排序

先分层：

1. PASS
2. REVIEW
3. UNKNOWN
4. FAIL

PASS 内再按：
- Preference
- Urgency

不要统一 1~N 黑盒排名。

---

# 25. Evidence

每条 Requirement 必须绑定原文。

Excel：
- Sheet
- Cell

PDF：
- Page
- Block

网页：
- Segment

用户可从岗位详情点击“查看依据”。

---

# 26. LLM 职责

Qwen 小模型/快速模型：
- 分类；
- 链接分类；
- 列名判断。

主力模型：
- 公告结构化；
- Requirement AST；
- 复杂条件；
- 语义专业条件。

外部模型：
- 本地 Schema 连续失败；
- 低置信；
- 用户手动重跑；
- 高价值歧义。

无论外部模型多强，都不得跳过 Evidence Validator。

---

# 27. 推荐输出 UI ViewModel

RecruitmentDashboardVM：

- nearest_deadline
- action_items
- eligibility_summary
- recommended_positions
- profile_questions
- recent_notices

PositionDetailVM：

- position
- eligibility
- preference
- urgency
- requirement_results
- evidence
- actions
- source_graph

---

# 28. CMS 调试

任务页显示：

- Source Graph
- Pipeline Steps
- 当前模型
- External API 是否调用
- 每步耗时
- 重跑当前步骤
- 使用外部模型重跑
- 查看 Evidence


---

# FILE: TRAVEL_FOOD_PIPELINE.md

# Travel / Food Pipeline

## 1. 目标

将视频/图文中的旅行与探店信息转换成：

- 带时间码 Transcript；
- 地点候选；
- 现实 POI；
- 餐厅/景点；
- 菜品/价格/作者评价；
- 用户偏好匹配；
- 地图；
- 收藏/想去/去过；
- 可导出数据；
- 全程可追溯 Evidence。

第一版地域为中国范围，POI 与地图首选高德；真实样本见 `GOLDEN_SAMPLES.md`。

---

# 2. Pipeline

```text
CAPTURE
↓
RESOLVE_SOURCE
↓
FETCH_METADATA
↓
FETCH_SUBTITLE
↓
DOWNLOAD_MEDIA（必要时）
↓
ASR
↓
SEGMENT
↓
EXTRACT_PLACES
↓
RESOLVE_POI
↓
DEDUPLICATE
↓
MATCH_PREFERENCES
↓
MATERIALIZE
↓
CLEAN_CACHE
```

---

# 3. Transcript First

优先：
1. 平台已有字幕；
2. 浏览器/登录态字幕；
3. 音频下载；
4. whisper.cpp。

第一版不默认做全视频视觉分析。

---

# 4. Transcript Segment

每段保存：

```text
start_ms
end_ms
text
segment_id
```

例如：

```text
03:12.480 - 03:27.120
“今天第一家来到的是……”
```

后续餐厅/景点 Claim 直接挂该 segment。

---

# 5. Extraction 不等于 Summary

第一阶段 AI 任务：

- PlaceCandidate[]
- RestaurantCandidate[]
- DishCandidate[]
- PriceClaim[]
- OpinionClaim[]
- WarningClaim[]
- RankingClaim[]
- RegionMention[]

摘要是辅助，不是核心产物。

---

# 6. PlaceMention vs Place

必须分开。

PlaceMention：
> 内容中“说到了什么”。

Place：
> 现实地图中“到底是哪一个地点”。

流程：

```text
PlaceMention
→ POI Resolution
→ Place
```

多个视频可指向同一个 Place。

---

# 7. POI Resolver

匹配依据：

- 名称相似；
- 城市；
- 区域；
- 附近地标；
- 地址上下文；
- 类别。

状态：

- CONFIRMED
- REVIEW
- UNRESOLVED
- REJECTED

只有 CONFIRMED 默认进入地图。

MVP 实现 `AMapPOIProvider`：使用高德 Web 服务进行候选搜索，优先传城市/adcode 与 `citylimit` 收敛歧义；保存 Provider、POI ID、原始候选响应哈希与 `GCJ02` 坐标系。前端使用高德地图 JS API 2.0。

---

# 8. 禁止 LLM 生成地图坐标

坐标只能来自：

- POI Provider；
- 用户确认；
- 可信地理数据。

LLM 仅能提取地点候选和上下文。

---

# 9. PlaceObservation

内容来源对地点的描述不能直接覆盖 Place。

例如：
视频 A：人均 80
视频 B：人均 120

保存两条 Observation。

类型：
- price
- dish
- author_opinion
- warning
- ranking
- recommended_season
- queue
- environment

---

# 10. 作者观点 vs AI 推荐

作者观点：
`SOURCE_OPINION`

AI 个性化：
`PERSONAL_INFERENCE`

UI 必须明确区分。

---

# 11. 偏好三层

## Explicit
用户明确设置。

## Behavior
收藏/忽略/去过等行为推导。

## Inferred
AI 推断。

优先级：
Explicit > Behavior > Inferred

---

# 12. PreferenceEvent

所有行为先存事件：

- SAVE
- DISMISS
- VISITED
- PLANNED
- LIKE
- DISLIKE

不要直接在点击时永久修改一个神秘分数。

PreferenceLearner 可随时重算。

---

# 13. Trait-based Preference v1

第一版不用复杂向量推荐。

地点可提取 Traits：

- nature
- urban
- historic
- food
- hiking
- island
- commercial
- crowded
- local
- luxury
- budget
- family
- nightlife

Preference 有权重。

推荐理由来自贡献最大的 Trait。

---

# 14. 避免虚假匹配度

不显示：
“匹配度 87%”

展示：
- 优先关注
- 值得考虑
- 一般
- 不符合偏好

并提供解释：

```text
✓ 海岛
✓ 适合步行探索
✓ 本地饮食
△ 游客较多
```

---

# 15. 地点状态

- DISCOVERED
- SAVED
- PLANNED
- VISITED
- DISMISSED

未来 Trip Planner 可直接复用。

---

# 16. Visit / Trip

第一版至少有 VisitEvent。

用于：
- 记录去过；
- 计算“距离上次旅行多少天”。

完整 Trip 可后续加入。

---

# 17. Partial Materialization

贵州 43 地点：

```text
36 Confirmed
5 Review
2 Unresolved
```

主地图立即展示 36。
任务仍可继续。

---

# 18. 视觉能力预留

数据模型保留：
`VisualEvidence`

后续：

```text
FrameExtractor
→ VisionProvider
```

用于：
- 店招；
- 菜单；
- 路牌；
- 屏幕价格；
- 地图画面。

任务完成只永久保存真正被 Claim 引用的 Evidence Frames。

---

# 19. 视频缓存

临时：
- video
- audio
- full frames

永久：
- transcript
- evidence frames
- thumbnail
- metadata
- claims

---

# 20. 导出

第一版：
- CSV
- JSON
- GeoJSON

GeoJSON 必须显式附带坐标来源和 `coordinate_system`。中国大陆高德坐标不得静默声明为 WGS84；若未来需要跨坐标系输出，必须由独立、可测试的转换策略完成并标注转换来源。

导出字段尽可能带：
- name
- coordinates
- source_title
- source_url
- source_timestamp
- recommendation_reason
- user_status

---

# 21. Travel Dashboard

TravelDashboardVM：

- days_since_last_trip
- map_places
- recent_discoveries
- recommended_places
- pending_reviews

---

# 22. CMS

视频任务显示：

- Metadata
- Subtitle/ASR
- 当前进度
- 发现 PlaceCandidate 数
- Confirmed/Review/Unresolved
- 模型
- 是否调用外部 API
- 查看字幕
- 查看时间码 Evidence
- 重跑地点提取
- 重跑 POI


---

# FILE: AI_RUNTIME_AND_PROVIDERS.md

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

Windows 优先：
- DPAPI
- Windows Credential Manager

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

Router 决定 Provider + Model。

---

# 7. 本地硬件策略

WILLIAM-PC：
- 5800X
- 32 GB
- RX 7900 XT 20 GB

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

原因：
Windows + AMD 环境。

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

---

# 16. 禁止

- Processor 内 import openai/ollama SDK；
- LLM 直接决定确定性日期/年龄；
- LLM 生成 POI 经纬度；
- LLM 输出没有 Evidence 的事实；
- 只保存最终自然语言摘要而丢失 Typed Result。


---

# FILE: CONTROL_CENTER.md

# Control Center

## 1. 定位

Control Center 不是普通 CMS，而是：

> **本地 AI 处理系统的控制台、任务观察台、证据审计台与配置后台。**

它属于 MVP 核心功能。

---

# 2. 第一版页面

1. Dashboard
2. Tasks
3. Sources
4. Settings

后续：
- Profile & Preference
- POI Review
- Evidence Audit
- Model Benchmarks
- Source Watch

---

# 3. Dashboard

展示：

- Processing
- Queued
- Failed
- Needs User
- Today Done
- Recruitment processing
- Travel processing
- GPU 当前任务
- 最近错误

例：

```text
Processing      2
Queued          5
Failed          1
Needs User      1

贵州43景区
POI 31/43

事业编公告
解析岗位表.xlsx
```

---

# 4. Tasks

每个 Job 展示：

- title
- type
- status
- step
- progress
- priority
- created
- runtime
- model
- external API used?
- errors

操作：

- retry
- cancel
- rerun
- rerun from step
- external model rerun
- view logs

---

# 5. Pipeline View

Recruitment：

```text
✓ RESOLVE_WECHAT
✓ DISCOVER_LINKS
✓ RESOLVE_OFFICIAL
✓ PARSE_EXCEL
✓ EXTRACT_NOTICE
✓ EXTRACT_POSITIONS
✓ BUILD_REQUIREMENTS
● MATCH_PROFILE
○ GENERATE_TODOS
```

Travel：

```text
✓ METADATA
✓ AUDIO
✓ ASR
✓ TRANSCRIPT
● POI 31/43
○ PREFERENCE
○ MATERIALIZE
```

---

# 6. Sources

显示：

- 原始链接；
- Snapshot；
- 正文；
- 附件；
- 下钻关系；
- Source authority；
- Claim/Evidence；
- 原始视频时间码；
- PDF 页码；
- Excel Cell。

---

# 7. Settings

## General
- data directory
- cache limit
- cleanup policy
- worker concurrency
- LAN enable / bind address / port
- LAN access token rotate
- allowed origins

## AI
- mode: local/cloud
- provider
- model mapping
- API Key
- Base URL
- connection test
- outbound data policy / per-run sensitive authorization

## ASR
- engine
- model
- mode
- GPU test

## Browser
- profile status
- login status
- clear/reset profile

## POI
- provider（MVP: AMap）
- API key
- country/region preference
- coordinate system（China: GCJ02）

## Recruitment
- source crawl depth
- max links
- catalog policy

## Travel
- auto POI threshold
- review threshold

---

# 8. Cache Management

显示：

- permanent data
- AI models
- temp video
- temp audio
- temp frames

支持：
- clean cache
- auto clean
- size limit

---

# 9. Evidence Audit

未来/Phase 2 可加强：

点 Claim：

```text
Claim
→ Evidence
→ Source
→ 原始 Snapshot
```

支持“报告错误”和单步重跑。

---

# 10. POI Review

待确认地点：

- raw name
- source
- context
- candidate POIs
- confidence
- map preview（前端实现）
- confirm
- reject
- search again

---

# 11. Profile Questions

展示：

> 补充这一项可继续判断 30 个岗位。

按 Information Gain 排序。

---

# 12. 控制台目标

用户必须能清晰感知：
- 系统现在在做什么；
- 为什么慢；
- 用了哪个模型；
- 是否用了外部 API；
- 失败在哪里；
- 为什么得出某个结论；
- 如何重跑。


---

# FILE: API_DESIGN.md

# API Design

> API 风格：REST + WebSocket  
> 第一版单用户，本地使用，但仍保持明确资源边界。

---

# 1. Capture API

## POST /api/inbox

输入：

```json
{
  "input_type": "url",
  "value": "https://..."
}
```

返回：
`202 Accepted`

```json
{
  "item_id": "...",
  "job_id": "...",
  "status": "QUEUED"
}
```

URL/Text 使用 JSON。文件使用：

`POST /api/inbox/upload`（`multipart/form-data`）

MVP 允许：

- `.pdf`
- `.docx`
- `.xls` / `.xlsx`
- `.png` / `.jpg` / `.jpeg`

上传时校验扩展名、MIME、文件头、大小上限与内容哈希；原文件写入本地永久 Source 存储，再创建统一 Job。扫描 PDF 与图片自动进入 OCR Step。

## GET /api/inbox/{id}

返回：
- input
- resolved type
- processor
- processing status
- result link

---

# 2. Recruitment API

## GET /api/recruitment/dashboard

返回 `RecruitmentDashboardVM`：

```json
{
  "nearest_deadline": {},
  "action_items": [],
  "eligibility_summary": {},
  "recommended_positions": [],
  "profile_questions": [],
  "recent_notices": []
}
```

## GET /api/recruitment/notices

支持分页与状态。

## GET /api/recruitment/positions

Filters：
- eligibility
- region
- deadline
- organization
- education
- major
- user_state

## GET /api/recruitment/positions/{id}

返回：
- position
- requirement results
- Evidence
- source graph
- deadlines
- actions

## POST /api/recruitment/positions/{id}/state

```json
{"state":"PREPARING"}
```

## GET /api/recruitment/questions

返回按 Information Gain 排序的待补充 Profile。

## POST /api/recruitment/questions/{id}/answer

更新 profile 后触发增量匹配。

---

# 3. Travel API

## GET /api/travel/dashboard

```json
{
  "days_since_last_trip": 63,
  "map_places": [],
  "recent_discoveries": [],
  "recommended_places": [],
  "pending_reviews": 0
}
```

## GET /api/travel/places

Filters：
- city
- place_type
- status
- source
- preference
- user_state

## GET /api/travel/places/{id}

返回：
- place
- mentions
- observations
- evidence
- preference explanation

## GET /api/travel/map

只返回 Confirmed Place ViewModel。

## POST /api/travel/places/{id}/save
## POST /api/travel/places/{id}/dismiss
## POST /api/travel/places/{id}/visited

写 PreferenceEvent / VisitEvent。

## POST /api/travel/export

格式：
- csv
- json
- geojson

---

# 4. Control Center API

## GET /api/admin/dashboard
## GET /api/admin/jobs
## GET /api/admin/jobs/{id}

## POST /api/admin/jobs/{id}/retry
## POST /api/admin/jobs/{id}/cancel

## POST /api/admin/jobs/{id}/rerun

```json
{
  "from_step": "EXTRACT_PLACES",
  "provider_override": null
}
```

## POST /api/admin/jobs/{id}/rerun-external

显式使用外部模型。

## GET /api/admin/sources/{id}
## GET /api/admin/sources/{id}/graph

## GET /api/admin/poi/review
## POST /api/admin/poi/{id}/confirm
## POST /api/admin/poi/{id}/reject

## GET /api/admin/settings
## PUT /api/admin/settings

---

# 5. WebSocket

## WS /api/ws/jobs

消息：

```json
{
  "job_id":"...",
  "status":"RUNNING",
  "step":"ASR",
  "progress":62,
  "message":"..."
}
```

前端断线后重新连接，再通过 REST 重新取状态，不能只依赖 WS。

---

# 6. ViewModel 原则

API 返回给产品前端的是 ViewModel，而不是 ORM Row。

原因：
- 防止 UI 绑定数据库；
- 支持未来小程序/移动 App；
- 数据库可演进；
- 保持业务语义。

---

# 7. 错误响应

统一错误：

```json
{
  "code":"POI_NEEDS_REVIEW",
  "message":"...",
  "details": {}
}
```

错误 code 必须稳定，不直接依赖异常类名。

---

# 8. 单用户认证

第一版必须支持手机局域网访问，因此认证不是可选项：

- localhost 与 LAN UI 使用同一 API；
- 手机首次配对通过 `POST /api/auth/session` 在请求体提交访问 Token，服务端换发短期 HttpOnly、SameSite Session Cookie；
- 后续 REST 与 WebSocket 握手统一验证 Session Cookie；脚本型客户端可使用 `Authorization: Bearer <access-token>`；
- Token 由本机生成、存入 Windows Credential Manager/DPAPI，并支持轮换；
- CORS 使用明确 Origin allowlist；
- 长期 Token 不放在查询字符串、localStorage 或普通日志中；
- 未授权请求统一返回稳定错误码 `AUTH_REQUIRED` / `AUTH_INVALID`。

未来远程访问再引入完整认证。


---

# FILE: SECURITY_PRIVACY.md

# Security & Privacy

## 1. 核心原则

Local First。

第一版业务数据默认只在用户 PC。

---

# 2. 数据分级

## Normal
- 链接
- 地点收藏
- 普通偏好

## Sensitive
- 学历
- 工作经历
- 政治面貌
- 户籍
- 证书

## Local Only
未来高敏感：
- 身份证
- 报名材料
- 自动操作凭据

---

# 3. API Key

正式版本：
- Windows Credential Manager / DPAPI；
- 数据库只保存引用。

开发 `.env`：
- 只能本机；
- 必须 .gitignore。

---

# 4. Browser Profile

`data/browser/profile/`

可能包含：
- Cookie
- 登录态
- Token
- local storage

禁止：
- Git；
- 普通导出；
- 默认云备份。

---

# 5. 外部大模型数据边界

Local First 默认尽可能本地处理。

调用外部模型前：
- 明确 provider；
- 允许用户选择 Local Only；
- 日志记录是否调用外部；
- `NORMAL` 内容按策略发送；
- `SENSITIVE` Profile 默认不外发，仅允许单次明确授权和最小字段发送；
- `LOCAL_ONLY` 永不外发；
- 发送审计记录只保存字段类别与 Evidence/Segment 引用，不复制敏感正文。

---

# 6. 本地 Web 安全

MVP 明确支持手机局域网访问：

- 首次安装默认生成高熵访问 Token；
- PC Control Center 显示 LAN 地址并允许复制/轮换 Token；
- 手机首次访问输入 Token，通过 `POST /api/auth/session` 换取短期 HttpOnly、SameSite Session Cookie；
- 浏览器不把长期 Token 保存到 localStorage，REST 与 WebSocket 统一验证 Session；
- localhost 之外的请求缺少/无效 Token 一律拒绝；
- CORS 只允许配置的 LAN Origin，不使用通配符；
- 管理 API 与业务 API 均受保护；
- 监听地址与 LAN 访问可关闭；
- 不做 UPnP、端口映射或公网暴露；
- Token 不写入 URL、普通日志或导出文件。

LAN 传输只允许用户明确配置的可信家庭/办公网络。Phase 0A 必须比较本地 HTTPS 与可信 LAN HTTP 的安装/配对体验；若 MVP 不能可靠部署 HTTPS，UI 必须明确提示不得在公共 Wi-Fi、访客网络或不可信热点中启用 LAN，并将 HTTPS 列为发布前风险项。

---

# 7. 超出可信局域网的远程访问

MVP 不强制实现。

未来可选择：
- VPN
- 安全隧道
- 轻 Control Plane

不建议直接端口映射暴露 FastAPI 到公网。

---

# 8. 日志

日志不得记录：
- API Key
- Cookie
- 登录 Token
- 完整身份证等未来高敏感字段

对敏感 Profile 做字段级掩码。

---

# 9. 数据导出

普通导出不包含：
- browser profile
- API Key
- secret refs
- 原始 Cookie

用户可独立导出：
- Recruitment 数据
- Travel Places
- Evidence
- Settings（无 secret）

---

# 10. 删除

未来应支持：
- 删除 Source；
- 删除 Snapshot；
- 删除 Profile；
- 删除 Place；
- 清理 Cache。

删除业务对象时注意 Evidence 引用与审计完整性。


---

# FILE: TESTING_AND_ACCEPTANCE.md

# Testing & Acceptance

## 1. 测试原则

本项目最危险的问题不是页面 Bug，而是：

- AI 误提取；
- 资格误判；
- Evidence 丢失；
- Job 重启丢失；
- POI 错认；
- 模型版本变化导致行为漂移。

因此测试必须覆盖 Pipeline 与业务规则。

---

# 2. Test Layers

## Unit
- Rule Engine
- Requirement DSL
- MajorMatcher
- Information Gain
- Preference scoring
- Job state transition

## Fixture
- HTML Resolver
- WeChat Snapshot
- Excel
- PDF
- DOCX
- scanned PDF / image OCR
- Transcript
- POI candidates

## Integration
- Capture → Job
- Recruitment End-to-End
- Travel End-to-End
- External LLM fallback
- Worker recovery

## UI
- Dashboard
- Control Center
- Evidence drill-down

---

# 3. Requirement DSL Tests

至少覆盖：

- ALL
- ANY
- NOT
- nested ALL/ANY
- HARD
- SEMANTIC
- PREFERENCE
- UNKNOWN propagation
- REVIEW propagation

---

# 4. Rule Engine Acceptance

案例：

```text
ALL(PASS, PASS) → PASS
ALL(PASS, FAIL) → FAIL
ALL(PASS, UNKNOWN) → UNKNOWN
ALL(PASS, REVIEW) → REVIEW

ANY(FAIL, PASS) → PASS
ANY(FAIL, FAIL) → FAIL
ANY(FAIL, UNKNOWN) → UNKNOWN
ANY(FAIL, REVIEW) → REVIEW
```

---

# 5. MajorMatcher Tests

- exact code
- exact name
- category
- official mapping
- old/new mapping
- semantic similar → REVIEW
- unknown catalog → NEED_FETCH / REVIEW

禁止语义匹配自动 PASS。

---

# 6. Evidence Integrity

每个 `EXTRACTED` Claim：
- 至少 1 Evidence；
- Evidence Segment 存在；
- Segment 对应 Snapshot；
- Snapshot 对应 Source。

发现孤儿 Claim：
测试失败。

`NORMALIZED` / `COMPUTED` Claim 必须具有有效 Claim 血缘；冲突 Claim 必须同时保留，不能靠最后写入覆盖。

---

# 7. Recruitment E2E

Fixture 包含：
- 公众号快照
- 政府公告
- Excel 岗位表

验收：
- 自动下钻；
- 解析时间；
- 解析岗位；
- 生成 DSL；
- Profile 匹配；
- Deadline；
- Evidence 可回溯。

---

# 8. Travel E2E

Fixture：
- 本地 Transcript
- 地点候选
- Mock POI Provider

验收：
- PlaceMention；
- POI；
- Dedup；
- Preference；
- Map ViewModel；
- Evidence timestamp。

---

# 9. Job Recovery

场景：
1. 创建 RUNNING Job；
2. 模拟 Worker 异常停止；
3. heartbeat 超时；
4. Job 回 QUEUED；
5. 新 Worker 接管。

验收：不丢任务、不重复写最终结果。

---

# 10. Replay

Recruitment：
从 `BUILD_REQUIREMENTS` 重跑，不重新抓 Source。

Travel：
从 `EXTRACT_PLACES` 重跑，不重新 ASR。

---

# 11. External LLM

Mock：
- Local validation fail twice；
- Local First 策略；
- External Provider 被调用；
- 记录 provider/model；
- 仍执行 Evidence Validator。

---

# 12. PC Hardware Acceptance

安装诊断：

- Python
- SQLite
- ffmpeg
- Playwright browser
- Ollama
- AMD GPU detected
- whisper.cpp
- model availability
- disk writable
- Node.js 20.19+ 或 22.12+
- LAN mobile access / token auth
- AMap API / map render
- DeepSeek / Xiaomi MiMo connection

CMS 显示诊断结果。

---

# 13. MVP Acceptance Definition

系统达到 MVP，需要至少满足：

1. 用户可以粘贴招聘链接；
2. 后台可见 Job；
3. 能解析至少一种真实招聘公告 + Excel；
4. 能形成岗位资格结果；
5. Evidence 可点击回溯；
6. 用户补 Profile 后自动重算；
7. 用户可粘贴 Bilibili 链接；
8. 能得到字幕或 ASR；
9. 能提取并确认地点；
10. 地点可出现在地图 ViewModel；
11. 可 SAVE / DISMISS / VISITED；
12. PC 重启任务可恢复；
13. 外部模型 API Key 可配置且可测试；
14. 所有核心长任务可从 CMS 重试。
15. 手机可在同一局域网安全访问，未授权请求无法读取业务或管理数据；
16. DOCX、扫描 PDF 与图片公告可归一化并保留 Evidence 定位；
17. 高德 POI/地图可用，GCJ-02 在存储与导出中明确标注；
18. DeepSeek、Xiaomi MiMo 可通过兼容 Provider 配置和测试；
19. `GOLDEN_SAMPLES.md` 的安全与正确性门槛全部通过。


---

# FILE: ARCHITECTURE_DECISIONS.md

# Architecture Decisions

## ADR-001：第一版取消云端
**Decision**
全部核心数据与计算运行在用户 PC。

**Reason**
- 单用户；
- 可接受 PC 关机时暂不处理；
- 用户明确希望先走通链路；
- 降低云部署与成本复杂度。

**Future**
可演化为 Cloud Control Plane + Home Worker。

---

## ADR-002：后端使用 FastAPI，不使用 Flask
**Decision**
FastAPI。

**Reason**
- Pydantic/Schema；
- WebSocket；
- ASGI；
- OpenAPI；
- 更适合当前 Typed Pipeline。

---

## ADR-003：FastAPI 不承担长任务
**Decision**
独立 Worker + SQLite Job Queue。

**Reason**
- ASR/视频/LLM 长任务；
- PC 重启恢复；
- CMS 可视化状态；
- 不引入 Redis/Celery。

---

## ADR-004：SQLite
**Decision**
MVP 使用 SQLite + WAL。

**Reason**
- 单机；
- 数据规模小；
- 部署简单；
- 可满足关系模型与全文检索基础需求。

---

## ADR-005：产品只做两个场景
**Decision**
Recruitment + TravelFood。

**Reason**
- 真实高频需求；
- 避免应用成为杂乱收藏箱。

**Future**
Processor Router 保留扩展。

---

## ADR-006：Unknown 不自动归类
**Decision**
第一版 Unknown → Unsupported。

**Reason**
- 保持产品干净；
- 不让 AI 擅自创建分类；
- 后续 GenericProcessor 再接入。

---

## ADR-007：Evidence First
**Decision**
事实 Claim 必须证据化。

**Reason**
- 招聘是高风险判断；
- 用户明确禁止 AI 随意发挥；
- 未来 GenericProcessor 同样需要可信度。

---

## ADR-008：Requirement DSL
**Decision**
招聘条件必须转 AST，不让 LLM 每次重新理解。

**Reason**
- 可测试；
- 可重放；
- 可审计；
- 逻辑嵌套。

---

## ADR-009：专业语义只 REVIEW
**Decision**
Semantic Major Match 不自动 PASS。

**Reason**
招聘单位认定可能与 AI 语义不同。

---

## ADR-010：Eligibility 与 Preference 分离
**Decision**
资格、偏好、紧急程度分别建模。

**Reason**
避免“匹配度 92%”混合多重含义。

---

## ADR-011：PlaceMention 与 Place 分离
**Decision**
视频提及与现实 POI 两层。

**Reason**
- 多来源去重；
- POI 解析可审核；
- 坐标可信。

---

## ADR-012：本地优先 + 外部 LLM 口子
**Decision**
LLMProvider 抽象，默认 LOCAL_FIRST。

**Reason**
- 利用 RX7900XT；
- 可离线；
- 外部强模型用于增强；
- 不锁厂商。

---

## ADR-013：ASR 抽象
**Decision**
ASRProvider，Windows AMD 首选 whisper.cpp 路线。

**Reason**
避免锁 CUDA/faster-whisper。

---

## ADR-014：Control Center 是 MVP
**Decision**
后台控制台不是后置。

**Reason**
用户明确需要看见系统处理过程并管理配置。

---

## ADR-015：Pipeline Replay
**Decision**
步骤结果持久化，可单步重跑。

**Reason**
模型升级、解析纠错、节省视频/网页重复抓取。

---

## ADR-016：Partial Materialization
**Decision**
长任务允许部分结果提前展示。

**Reason**
提升 43 地点/数百岗位等任务 UX。

---

## ADR-017：Narrow Product, Extensible Core
**Decision**
UI 窄，接口宽。

**Reason**
兼顾第一版速度与长期 GenericProcessor 演进。

---

## ADR-018：MVP 支持可信局域网手机访问
**Decision**
PC 仍是唯一数据与计算节点；手机通过同一可信局域网访问响应式 Web。REST/WebSocket/Admin API 必须验证本机生成的访问 Token，不自动暴露公网。

**Reason**
- 手机是“随手分享/查看结果”的必要入口；
- 不为此提前引入云端与多用户体系；
- LAN 已扩大攻击面，认证不能后置。

---

## ADR-019：招聘文档矩阵包含 DOCX 与 OCR
**Decision**
MVP 支持 PDF、扫描 PDF、DOCX、XLS/XLSX、PNG/JPEG；OCR 结果保存页码、边界框和置信度，低置信关键事实进入 Review。

**Reason**
北京市公务员/事业单位公告附件并不只使用文本型 PDF/Excel，缺少 DOCX/OCR 会造成真实链路断裂。

---

## ADR-020：中国 POI 首选高德并显式使用 GCJ-02
**Decision**
MVP 实现 AMapPOIProvider 和高德地图 JS API 2.0。中国大陆高德坐标存储为 `GCJ02`，导出必须标注坐标系。

**Reason**
- 第一版旅行范围为中国；
- 高德同时提供 POI 搜索与 PC/移动 Web 地图；
- 显式坐标系避免地图显示与 GeoJSON 语义错误。

---

## ADR-021：外部模型通过兼容 Provider 接入且敏感档案默认不外发
**Decision**
DeepSeek、Xiaomi MiMo 等通过 OpenAICompatibleProvider 配置；模型名不写死。`SENSITIVE` Profile 默认不外发，`LOCAL_ONLY` 永不外发。

**Reason**
- Provider 与模型会持续变化；
- 招聘 Profile 涉及学历、工作经历、政治面貌和户籍；
- 最小化外发符合 Local First。

---

## ADR-022：真实 URL 手工验收，冻结 Fixture 用于 CI
**Decision**
微信/Bilibili 真实链接用于手工验收；CI 使用脱敏冻结 Fixture，不依赖实时平台网络。

**Reason**
- 平台存在登录态、验证码、风控、412 与内容变化；
- 实时网络依赖无法提供可复现测试；
- 不绕过平台访问限制。


---

# FILE: GOLDEN_SAMPLES.md

# Golden Samples & Feasibility Baseline

> 状态：Baseline v0.2
> 冻结日期：2026-08-13
> 用途：登记 MVP 首批真实样本、Fixture 获取规则、技术 Spike 与质量门槛。

---

# 1. 样本使用原则

1. 真实 URL 用于手工验收与定期兼容性检查，不作为 CI 的实时网络依赖。
2. 首次成功解析后，保存脱敏且许可范围内的 HTML、附件、字幕、POI 候选响应为 Fixture。
3. Fixture 必须记录获取时间、原始 URL、内容哈希、Resolver/Parser 版本；不得保存 Cookie、Token 或浏览器 Profile。
4. 微信、Bilibili 等来源若受登录态、验证码、风控或 412 限制，按 `HTTP → Playwright 持久 Profile → NEEDS_USER` 处理，不绕过平台限制。
5. 公众号正文中的官方公告和附件允许按 Source Graph 规则下钻；默认 `max_depth = 2`、单来源最多跟随 30 个链接。
6. 黄金样本内容可能随来源页面更新或失效；验收以冻结 Fixture 为可复现基准，以真实 URL 为补充手工验证。

---

# 2. Recruitment 黄金样本

首域：北京市公务员、事业单位招聘及相关考试公告。

## R-001

- 类型：微信公众号招聘汇总/入口文章
- URL：`https://mp.weixin.qq.com/s/_A_u11jr_FDA58sQ5QkBhg`
- 目标：验证微信 Resolver、正文解析、官方来源下钻、附件发现、Notice/Position/Requirement/Evidence 全链路。
- 当前网络特征：普通无状态 HTTP 无法稳定读取，必须验证 Playwright 持久登录态与 `NEEDS_USER` 路径。

## R-002

- 类型：微信公众号招聘汇总/入口文章
- URL：`https://mp.weixin.qq.com/s/HTw6_R4YICpLCFFl6PO4Yg`
- 目标：作为第二种页面结构与下钻关系样本，避免 Resolver 只适配单页。
- 当前网络特征：普通无状态 HTTP 无法稳定读取，测试策略同 R-001。

## 招聘 Fixture 最小集合

每个样本应尽量冻结：

- 微信正文 HTML；
- 下钻后的官方公告 HTML/PDF/DOCX；
- 岗位 XLS/XLSX；
- 扫描 PDF 或图片型公告（若来源存在）；
- Source Graph 期望结果；
- 关键日期、岗位数、字段映射、Requirement DSL 与 Evidence 的人工校验答案。

---

# 3. Travel/Food 黄金样本

## T-001

- 标题：厦门街头米其林小馆，连吃两家爽了…
- URL：`https://www.bilibili.com/video/BV189ui6LEhK`
- 类型：探店视频
- 目标：字幕优先、餐厅/菜品/价格/作者观点抽取、厦门 POI 解析、重复地点合并、时间码 Evidence。

## T-002

- 标题：不只是凉快，一口气逛遍贵州全省43个景区，TOP10你去过几个？｜全景推荐03
- URL：`https://www.bilibili.com/video/BV1qF3t6TENn`
- 类型：多地点旅行视频
- 目标：长视频字幕/ASR、43 地点批量抽取、Partial Materialization、高德 POI 候选、地图与 Review 队列。
- 当前网络特征：无状态抓取可能返回 412，必须覆盖浏览器/媒体解析 fallback 与 `NEEDS_USER`。

## 旅行 Fixture 最小集合

- 元数据与封面引用；
- 平台字幕（若有）或经授权生成的本地 Transcript；
- 时间码 Segment；
- 人工校验的 PlaceMention/Observation；
- 脱敏后的 Mock 高德 POI 候选响应；
- Confirmed/Review/Unresolved 期望状态。

不把完整受版权保护的视频提交到 Git。测试仓库仅保存短小、必要、合法的派生 Fixture；本地媒体放入被忽略的数据目录。

---

# 4. Phase 0A 技术 Spike

正式业务实施前必须在目标 Windows 11 主机完成：

1. `LAN_ACCESS`：手机通过同一局域网访问前后端，验证 Token-to-Session、CORS、WebSocket 重连、Admin API 保护，并比较本地 HTTPS 与可信 LAN HTTP 的可部署性。
2. `WECHAT_RESOLVER`：R-001/R-002 至少一个可通过持久浏览器 Profile 获取正文并发现下钻链接；失败时能进入 `NEEDS_USER`。
3. `DOCUMENT_MATRIX`：验证 HTML、PDF、扫描 PDF、DOCX、XLS/XLSX、PNG/JPEG 的文本与定位信息。
4. `OCR`：中文 OCR 输出页码/边界框/置信度，低置信内容进入 Review，不直接生成高风险事实。
5. `LOCAL_LLM`：RX 7900 XT 上 Ollama 结构化输出、显存占用、吞吐与 JSON Schema 成功率。
6. `ASR`：whisper.cpp Vulkan 在 RX 7900 XT 上输出中文时间码 Transcript。
7. `EXTERNAL_LLM`：DeepSeek 与 Xiaomi MiMo 至少各完成一次 OpenAI-compatible 连接测试、结构化输出测试与审计记录测试。
8. `AMAP`：高德 Web 服务 POI 搜索、JS API 2.0 地图渲染、GCJ-02 坐标与配额错误路径。
9. `SQLITE_MULTI_PROCESS`：FastAPI + Worker 下 WAL、原子 Job Lease、崩溃恢复与幂等写入。

每项记录：环境版本、命令、输入、结果、耗时、资源占用、失败原因、是否阻塞后续 Phase。

---

# 5. 初始质量门槛

在黄金 Fixture 上：

- 关键报名/考试日期：人工标注项 100% 有正确值或明确进入 `UNKNOWN/REVIEW`，不得静默给出错误确定值；
- Eligibility：不得把人工标注的明确 `FAIL/REVIEW` 自动判为 `PASS`；
- Evidence：所有 `EXTRACTED` Claim 100% 可回到有效 Segment/Cell/Page/时间码；
- Excel 岗位行：不得静默丢行，无法可靠识别的行必须进入 Review 并报告计数；
- OCR：低于配置阈值的文字不得作为无需复核的关键日期或硬性资格依据；
- POI：只有高置信且候选唯一时自动 `CONFIRMED`；黄金样本中的误确认数必须为 0，其余进入 `REVIEW/UNRESOLVED`；
- Job：崩溃恢复不丢任务，业务结果幂等，不重复生成最终实体；
- LAN：未携带有效 Token 的 API、WebSocket 和 Admin 请求全部拒绝。

吞吐、ASR 速度、LLM Schema 首次成功率等性能指标由 Phase 0A 在目标主机实测后补入，不凭空设定。

---

# 6. 尚待补充的样本

- 至少一份北京市官方 DOCX 招聘附件；
- 至少一份扫描 PDF 或图片公告；
- 至少一份结构复杂的 XLS/XLSX 岗位表；
- R-001/R-002 的人工期望答案与脱敏 Fixture；
- T-001/T-002 的人工地点清单与时间码答案。


---

# FILE: FUTURE_ROADMAP.md

# Future Roadmap

> 本文只记录未来能力，防止在 MVP 实施中被遗忘。  
> 这些能力**不是第一版必须实现**，除非后续明确提升优先级。

---

# 1. GenericProcessor

目标：

未知非结构化内容不再 Unsupported，而进入通用处理。

GenericResult：

```text
title
summary
key_points[]
entities[]
dates[]
locations[]
action_items[]
claims[]
```

仍保留 Evidence。

---

# 2. Processor 演进体系

长期三层：

## Dedicated Processor
- Recruitment
- TravelFood
- Shopping
- ...

## Configurable Processor
通过：
- Schema
- Prompt
- View Template
- Rules
实现中等复杂场景。

## Generic Processor
未知内容兜底。

演化：

```text
Generic 高频场景
→ Configurable
→ 成熟后 Dedicated
```

---

# 3. 动态分类 / Space

第一版不做。

未来：
- AI 建议创建；
- 用户确认；
- 用户可改名；
- 用户可合并；
- 用户可删除；
- 一条 Source 可进入多个 Space。

Space 不等于 Folder。

---

# 4. Generic View Templates

未来可提供：

- Countdown + Todo
- Map + List
- Timeline
- Comparison
- Knowledge Summary
- Wishlist

AI 建议 View，但用户有最终控制。

---

# 5. Source Watch

第一版仅预留接口。

未来支持：
- 招聘补充公告；
- 截止日期变化；
- 页面更新；
- 商品价格变化；
- 旅行地点状态变化。

Source Watch 新版本应产生新 Snapshot，不静默覆盖旧事实。

---

# 6. 自动执行 C 级

当前 B：
- 生成报名 Checklist
- 咨询建议
- 待办

未来 C：
- 自动填写报名；
- 自动填写网页表单；
- 自动发邮件；
- 自动日历同步；
- 自动导出到第三方地图；
- 自动购买/预订等更高风险行为（需独立安全设计）。

要求：
- 权限模型；
- 用户确认；
- 操作 Preview；
- 审计日志；
- 可撤销；
- 风险分级。

---

# 7. 移动端

第一版：
Responsive Web。

未来：
- Android app
- iOS app
- 微信小程序
- Share Extension

移动端应为薄客户端。
重任务继续由 PC/Cloud Worker。

---

# 8. Browser Extension

价值：
- 当前页面；
- 用户登录态；
- 选中文字；
- 页面 DOM；
- 截图；
- “记住这个”。

可解决部分微信/平台访问限制。

---

# 9. Remote PC

PC 节点 + 可信局域网 MVP 的限制：
PC 离线时无法即时处理。

未来选择：

### VPN / direct secure access
仍不需要业务云。

### Light Control Plane
手机先写 Inbox；
PC 上线后取任务。

### Full Cloud
云 Worker 兜底。

---

# 10. Multi Worker

未来 Job 带 capability：

```text
requires_gpu
requires_browser_cookie
privacy
priority
```

Execution Router：

```text
Home PC
Office PC
Cloud CPU
Cloud GPU
```

---

# 11. Cloud SaaS

长期商业化：

- Multi-user；
- User Auth；
- Tenant isolation；
- Cloud DB；
- Cloud GPU；
- Subscription；
- Quota；
- Remote Worker optional。

MVP 代码不得提前承担这些复杂度。

---

# 12. 向量搜索 / RAG

第一版不需要 Vector DB。

未来当 GenericProcessor 和历史资料规模提升后，可加入：
- embedding；
- semantic retrieval；
- RAG；
- cross-source question answering。

必须保持 Evidence。

---

# 13. Knowledge Graph

当前 Source Graph / Claim-Evidence 用关系表足够。

未来若跨领域 Entity/Relation 复杂度显著增长，可评估图数据库。

不提前引入。

---

# 14. Travel Vision

当前 Transcript First。

未来：
- 关键帧抽取；
- 店招；
- 菜单；
- OCR；
- 路牌；
- 价格；
- 景点画面；
- 视频中的地图。

VisualEvidence 与 TranscriptEvidence 并存。

---

# 15. Travel Planning

未来：
- Trip
- itinerary
- route
- opening hours
- travel time
- city clustering
- multi-day plan

当前 Place 用户状态已为未来 PLANNED 留口子。

---

# 16. Recruitment C-level

未来：
- 自动准备报名材料；
- 自动生成字段填充值；
- 浏览器自动填表；
- 最终提交必须另行确认；
- 对验证码/身份认证不绕过。

---

# 17. Personal Memory / Preference

未来：
- 更长期的行为学习；
- Preference versioning；
- Explanation；
- User correction；
- explicit vs inferred conflict management。

---

# 18. Generic Automation

最终目标：

```text
Input
→ Understand
→ Decide
→ Prepare Action
→ Execute (when allowed)
```

应用从“信息整理工具”进化为个人 AI 行动层，但必须始终保留：
- 来源；
- Evidence；
- 权限；
- 用户控制。


---

# FILE: PROJECT_PLAN.md

# PROJECT_PLAN.md
## Codex / Agent 可执行实施计划

> 项目：AI Personal Inbox / Personal Scout  
> 目标平台：Windows 11  
> 当前硬件：Ryzen 7 5800X / 32GB / RX 7900 XT 20GB  
> 当前范围：Recruitment + Travel/Food  
> 架构：FastAPI + React/TS/Vite + SQLite + Worker + Playwright + Ollama/External LLM + whisper.cpp  
> 原则：产品做窄，内核留宽

---

# 0. Agent 总体执行规则

Agent 在实现过程中必须：

1. 先阅读本目录所有设计文档。
2. 不得自行把 MVP 扩成通用 Agent 平台。
3. 所有长任务必须走 Job。
4. 所有事实性 Claim 必须有 Evidence。
5. 不得在 Processor 内直接调用具体 LLM SDK。
6. 不得用 LLM 代替确定性 Rule Engine。
7. 不得让 LLM 生成 POI 经纬度。
8. 所有数据库变更必须 Alembic migration。
9. 所有核心模块必须有测试。
10. 每完成一个 Phase 更新实现状态文档或 checklist。

真实样本、Fixture 规则和初始质量门槛见 `GOLDEN_SAMPLES.md`。

---

# Phase 0A — Target PC Feasibility Spikes（在 Phase 0 最小 Bootstrap 后执行）

## Goal

在搭建完整业务代码前，用目标 Windows 11 / RX 7900 XT 主机消除高风险外部依赖的不确定性。

## Spikes

- 手机 LAN 访问、Token-to-Session、CORS、WebSocket 与 HTTPS 可部署性；
- 微信持久 Playwright Profile 与 `NEEDS_USER`；
- HTML/PDF/扫描 PDF/DOCX/XLS/XLSX/PNG/JPEG 文档矩阵；
- 中文 OCR 定位与置信度；
- Ollama AMD 结构化输出；
- whisper.cpp Vulkan 时间码 ASR；
- DeepSeek / Xiaomi MiMo OpenAI-compatible 连接；
- 高德 POI Web 服务 / JS API 2.0 / GCJ-02；
- SQLite WAL 多进程、原子 Lease 与幂等恢复。

## Acceptance

- 每项有可复现记录与 `PASS / DEGRADED / BLOCKED` 结论；
- `BLOCKED` 项在进入依赖它的 Phase 前必须选定替代方案或调整范围；
- 性能门槛使用目标 PC 实测值回填 `GOLDEN_SAMPLES.md`。

---

# Phase 0 — Repository Bootstrap

## Goal
建立可运行 Monorepo。

## Tasks

### P0.1
创建：

```text
/backend
/frontend
/docs
/scripts
/data.example
```

### P0.2
Backend：
- Python 3.12+
- pyproject.toml
- FastAPI
- Uvicorn
- SQLAlchemy
- Alembic
- Pydantic
- aiosqlite/httpx

### P0.3
Frontend：
- React
- TypeScript
- Vite
- Node.js 20.19+ 或 22.12+

### P0.4
.gitignore：
- data/
- .env
- browser profile
- model cache
- logs

### P0.5
基础健康接口：
`GET /api/health`

### P0.6
LAN 安全基线：
- 可配置 bind address / port；
- 首次生成访问 Token；
- REST / WebSocket 鉴权；
- Origin allowlist；
- 默认不做公网暴露。

## Acceptance
- backend 启动；
- frontend 启动；
- health 正常；
- 手机在同一局域网携带 Token 可访问，未授权请求被拒绝；
- Windows README 命令可用。

---

# Phase 1 — Database & Core Domain

## Goal
落地核心数据库与 Repository。

## Tasks

### P1.1
数据库配置：
- SQLite
- WAL
- foreign_keys

### P1.2
Alembic 初始化。

### P1.3
实现：
- content_items
- sources
- source_snapshots
- source_relations
- segments
- claims
- claim_evidences
- claim_relations
- jobs
- job_steps
- settings / secret references

### P1.4
Repository 层。

### P1.5
Pydantic Domain Models。

### P1.6
Evidence Integrity 校验。

## Tests
- CRUD
- FK
- orphan Claim validation
- migration up/down（合理范围）

## Acceptance
创建 Source → Snapshot → Segment → Claim → Evidence 可完整回读。

---

# Phase 2 — Job Runtime

## Goal
实现持久后台任务。

## Tasks

### P2.1
Job 状态机。

### P2.2
Worker Process。

### P2.3
Lease + heartbeat。

### P2.4
stale RUNNING recovery。

### P2.5
JobStep。

### P2.6
REST：
- list
- retry
- cancel
- rerun

### P2.7
WebSocket progress。

## Tests
- worker crash
- lease expire
- retry
- cancel
- recovery

## Acceptance
PC/Worker 异常停止后任务可恢复。

---

# Phase 3 — Control Center Skeleton

## Goal
用户可以看到系统运行。

## Pages
- Dashboard
- Tasks
- Sources
- Settings

## Tasks
- Job list
- Job detail
- step progress
- retry/cancel
- WS updates
- settings storage

## Acceptance
创建 mock 长任务可实时看 0→100%。

---

# Phase 4 — LLM Provider Layer

## Goal
建立厂商无关 AI 层。

## Tasks

### P4.1
LLMProvider base。

### P4.2
OllamaProvider。

### P4.3
OpenAIProvider。

### P4.4
OpenAICompatibleProvider。

### P4.5
MockProvider。

### P4.6
LLM Router。

策略：
- LOCAL_ONLY
- LOCAL_FIRST
- CLOUD_FIRST
- MANUAL

### P4.7
Structured Output + Pydantic Validation。

### P4.8
Prompt/model/parser version logging。

### P4.9
API Key secret storage abstraction。

## Tests
- provider switching
- local failure → cloud fallback
- invalid JSON retry
- Evidence reference validation

## Acceptance
同一个业务抽取接口可在不改 Processor 的情况下切换 Provider。

---

# Phase 5 — Resolver Core

## Goal
建立统一 ResolvedContent。

## Tasks

### P5.1
Resolver base + registry。

### P5.2
WebResolver。

### P5.3
Snapshot 存储。

### P5.4
HTML → normalized text/segments。

### P5.5
outgoing links。

### P5.6
Document Resolver base。

## Acceptance
普通网页 URL → Source/Snapshot/Segments。

---

# Phase 6 — Playwright / WeChat Resolver

## Goal
支持真实公众号入口与登录态。

## Tasks

### P6.1
Playwright setup。

### P6.2
独立 browser profile。

### P6.3
WechatResolver：
- HTTP
- browser fallback
- NEEDS_USER

### P6.4
Link Discovery。

### P6.5
depth / children limit。

### P6.6
Source Graph。

## Tests
使用保存的 HTML Fixture，不让 CI 依赖真实微信。

## Acceptance
给定微信 Fixture 可发现官方链接/附件并建立 SourceRelation。

---

# Phase 7 — PDF / Excel Normalizer

## Goal
支持招聘附件与扫描材料。

## Excel Tasks
- `.xlsx` openpyxl reader
- `.xls` legacy reader adapter（Phase 0A 选型）
- sheet detect
- header detect
- merged cell recovery
- normalized table
- AI column mapping

## PDF Tasks
- page segments
- text blocks
- locator

## DOCX Tasks
- paragraph / table normalization
- paragraph/run locator
- embedded attachment/image discovery

## OCR Tasks
- scanned PDF detection
- PNG/JPEG input
- Chinese OCR provider abstraction
- page/bbox/confidence locator
- low-confidence Review policy

## Acceptance
岗位表 Fixture 可转换为标准 rows，保留原 Cell 定位；DOCX/PDF/OCR 文本均可回到原页、段落或边界框，低置信关键事实不自动确定。

---

# Phase 8 — Recruitment Schema

## Goal
创建招聘领域模型。

## Tables
- recruitment_notices
- positions
- requirements
- requirement_matches
- position_matches
- profile_fields
- education_experiences
- deadlines
- todos
- major catalogs（最小实现）

## Acceptance
Notice + 100 Position 可存取。

---

# Phase 9 — Requirement DSL & Rule Engine

## Goal
实现可测试资格逻辑。

## Tasks
- AST Pydantic
- ALL
- ANY
- NOT
- CONDITION
- HARD
- SEMANTIC
- PREFERENCE
- PASS/FAIL/UNKNOWN/REVIEW propagation

## Tests
必须覆盖所有组合。

## Acceptance
Rule Engine 完全不依赖 LLM。

---

# Phase 10 — Recruitment Extraction

## Goal
公告/岗位 → DSL。

## Tasks
- Notice extractor
- Position extractor
- Requirement parser
- Evidence binding
- schema validation
- retry policy

## Acceptance
Fixture 招聘完整得到 Typed Result + Evidence。

---

# Phase 11 — MajorMatcher

## Goal
实现专业匹配。

## Tasks
- MajorCatalog schema
- ExactCodeMatcher
- ExactNameMatcher
- CategoryMatcher
- OfficialMappingMatcher
- SemanticMatcher
- REVIEW policy

## Acceptance
Semantic similarity 永远不会自动 PASS。

---

# Phase 12 — Profile Matching & Information Gain

## Goal
用户 Profile 参与岗位筛选。

## Tasks
- profile CRUD
- education experiences
- match recomputation
- Missing Profile Analyzer
- Information Gain
- incremental recalculation

## Acceptance
修改一个 Profile 字段不会重新 Resolve Source，只重跑 Match。

---

# Phase 13 — Recruitment Deadline / Todo / UI

## Goal
招聘产品可用。

## Tasks
- deadline generation
- todo FACT_BASED / SYSTEM_SUGGESTED
- urgency
- preference
- user state
- time conflict
- RecruitmentDashboardVM
- PositionDetailVM
- React pages

## Acceptance
用户可以从首页：
- 看到最近截止；
- 看到 PASS；
- 看到 UNKNOWN；
- 回答 profile question；
- 查看 Evidence；
- 标记 PREPARING/APPLIED/DROPPED。

---

# Phase 14 — ASR Runtime

## Goal
实现 Windows AMD 本地视频转录。

## Tasks
- ffmpeg detection
- whisper.cpp provider
- model management
- timestamp transcript
- GPU diagnostic
- ASR mode
- cache cleanup

## Acceptance
本地视频/音频 → timestamp segments。

---

# Phase 15 — Bilibili Resolver

## Goal
B站视频进入 Travel Pipeline。

## Tasks
- metadata
- subtitle-first
- media fallback
- ASR fallback
- snapshot / transcript storage

## Acceptance
测试视频 Fixture 或真实样本可得到 Transcript。

---

# Phase 16 — Travel Extraction

## Goal
Transcript → PlaceMention / Observations。

## Tasks
- TravelFood classifier
- Place extractor
- Restaurant extractor
- dish/price/opinion/warning
- Evidence timestamp binding

## Acceptance
每个事实可回到字幕 segment。

---

# Phase 17 — POI Provider & Resolution

## Goal
PlaceMention → Place。

## Tasks
- POIProvider base
- AMapPOIProvider
- AMap Web Service Key / quota error handling
- GCJ-02 coordinate metadata
- candidate search
- name/location matching
- confidence
- Confirmed/Review/Unresolved
- CMS POI Review
- deduplicate
- AMap JS API 2.0 map view

## Acceptance
LLM 不参与经纬度生成。
两个来源提同一家店最终可归并为一个 Place。
GeoJSON 明确携带坐标系，不把 GCJ-02 静默声明为 WGS84。

---

# Phase 18 — Preference & Travel UI

## Goal
实现个性化地图与列表。

## Tasks
- preference_events
- preferences
- trait extraction
- simple scoring
- explanation
- place state
- VisitEvent
- days_since_last_trip
- TravelDashboardVM
- map view
- list view

## Acceptance
SAVE/DISMISS/VISITED 会影响后续推荐解释。

---

# Phase 19 — Export

## Goal
批量导出。

## Formats
- CSV
- JSON
- GeoJSON

## Acceptance
导出包含 source URL / timestamp / user state。

---

# Phase 20 — Replay / Partial Materialization

## Goal
实现长任务体验。

## Tasks
- rerun from step
- versioned step output
- partial publish
- stale result invalidation
- CMS controls

## Acceptance
Travel 可在 43 个地点未全部完成时展示已确认地点。
Recruitment 可单独重跑 DSL/Major Matching。

---

# Phase 21 — Hardening

## Goal
可日常使用。

## Tasks
- error taxonomy
- logs
- secret masking
- cache manager
- browser profile safety
- backup/export
- diagnostics
- startup script
- production build
- install documentation

## Acceptance
新机器可按文档部署；重启不丢数据；错误可定位。

---

# Phase 22 — Desktop Packaging（可选，MVP 后）

Tauri 或其他薄壳：
- launcher
- backend sidecar
- worker sidecar
- UI

不是业务 MVP 前置条件。

---

# 23. Future-only Interfaces

当前只定义接口，不实现完整功能：

- GenericProcessor
- SourceWatch
- CloudWorker
- ExecutionRouter
- VisionProvider
- MobileShare
- AutoActionExecutor

禁止 Agent 在 MVP Phase 擅自实现。

---

# 24. 最终 MVP Definition of Done

### Recruitment
- 真实招聘来源可解析；
- 官方附件可下钻；
- Excel 岗位可读取；
- DSL；
- MajorMatcher；
- Profile；
- PASS/FAIL/UNKNOWN/REVIEW；
- Deadline/Todo；
- Evidence。

### Travel
- Bilibili；
- Subtitle/ASR；
- PlaceMention；
- POI；
- Map；
- Preference；
- Evidence；
- Export。

### Platform
- PC only；
- Job recovery；
- Control Center；
- Ollama；
- external API；
- replay；
- secure settings；
- local data。

---

# 25. 建议 Agent 实施顺序

按 Phase 0 → Phase 0A → Phase 1–13 完成 Recruitment，
再 14 → 19 完成 Travel，
之后 20 → 21 做系统化完善。

原因：
Recruitment 覆盖 Evidence/DSL/Profile/Rule Engine，
它跑通后 Travel 只新增 ASR/POI/Preference 特有能力。

---

# 26. Agent 每阶段输出

每个 Phase 应输出：

```text
完成内容
涉及文件
数据库迁移
新增 API
新增测试
运行命令
验收结果
未完成/风险
下一 Phase
```

不要只报告“代码已完成”。
