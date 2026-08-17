# AI Personal Inbox / Personal Scout
## 项目文档索引

> 文档版本：v0.3
> 更新日期：2026-08-18
> 当前阶段：需求与架构基线已完成，可进入 Phase 0A 技术验证与工程实施
> 第一阶段部署形态：保留 Windows 11 PC 与 Mac mini 两套本地优先单节点方案，实施前由用户选择其一作为后端与 AI Worker；手机通过可信局域网访问
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
| [DEPLOYMENT_OPTIONS.md](./DEPLOYMENT_OPTIONS.md) | Windows PC / Mac mini 双部署方案、选择矩阵与决策门 |
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

## 4. 当前硬件基线与待选部署

### 方案 A：Windows PC 后端

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

### 方案 B：Mac mini 后端

- 设备：Mac mini（`Mac16,10`）
- OS：macOS 26.6.1（实施时允许升级）
- 芯片：Apple M4，10 核 CPU
- RAM：16 GB 统一内存
- 架构：arm64

这台机器可独立承担同一套 FastAPI、SQLite、Playwright、文档/OCR、Worker、Web Control Center 与本地文件存储；本地 AI 改用 Ollama Metal 与 whisper.cpp Metal，Secret 改存 macOS Keychain，服务由 `launchd` 常驻托管。完整差异与选择条件见 `DEPLOYMENT_OPTIONS.md`。

两套方案互斥选择，不在 MVP 中让 Windows PC 与 Mac mini 共享同一个 SQLite 文件，也不同时维护两套生产安装包。

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
9. **长任务必须持久化，所选后端节点重启后可恢复。**
10. **原始证据优先，AI 解释次之。**
