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
