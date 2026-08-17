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
- MapOverviewVM；
- 同一区域多 Marker 分布与密集点聚合；
- 依次点击 Marker 只切换地点预览，地图 viewport 不重置；
- 从地点详情返回恢复 zoom、filters 与 selected Marker；
- 路线清单按手动顺序保存 Place，且不生成未经 Route Provider 验证的距离/耗时；
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

# 12. Target Node Hardware Acceptance

共同安装诊断：

- Python
- SQLite
- ffmpeg
- Playwright browser
- Ollama
- whisper.cpp
- model availability
- disk writable
- Node.js 20.19+ 或 22.12+
- LAN mobile access / token auth
- AMap API / map render
- DeepSeek / Xiaomi MiMo connection

方案 A 额外验收：

- Windows Credential Manager / DPAPI；
- AMD GPU detected；
- Ollama AMD 结构化输出；
- whisper.cpp Vulkan；
- Windows 重启、休眠/唤醒与服务恢复。

方案 B 额外验收：

- macOS Keychain；
- Apple Metal detected；
- Ollama Metal 结构化输出与统一内存峰值；
- whisper.cpp Metal，Core ML encoder 如启用则单独记录；
- arm64 OCR、Playwright、ffmpeg 与 legacy `.xls` 依赖；
- `launchd` 在崩溃、退出登录和 Mac mini 重启后的服务恢复；
- mDNS 不可用时通过固定 IP/DHCP 保留地址访问。

CMS 显示当前后端类型、硬件、运行时和诊断结果。两套平台的性能结果必须分别记录。

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
10. 多个地点可同时出现在独立地图总览，点击 Marker 可切换预览并进入详情；
11. 可 SAVE / DISMISS / VISITED；
12. 选中的后端节点重启后任务可恢复；
13. 外部模型 API Key 可配置且可测试；
14. 所有核心长任务可从 CMS 重试。
15. 手机可在同一局域网安全访问，未授权请求无法读取业务或管理数据；
16. DOCX、扫描 PDF 与图片公告可归一化并保留 Evidence 定位；
17. 高德 POI/地图可用，GCJ-02 在存储与导出中明确标注；
18. DeepSeek、Xiaomi MiMo 可通过兼容 Provider 配置和测试；
19. 地点可加入路线清单并手动排序，系统不伪造自动最优路线、距离或交通耗时；
20. `GOLDEN_SAMPLES.md` 的安全与正确性门槛全部通过。
