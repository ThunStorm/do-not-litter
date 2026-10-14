# 至简：视频标题时间证据、Mention ID 边界与分片 Prompt 优化实施计划

> 2026-10-14 归档：已授权范围的源码与离线验证已实施；此处保留原计划作为追溯，不是当前执行指令。现状见 [实施状态](../../IMPLEMENTATION_STATUS.md)，未完成真实质量/缓存收益及会话实验须另行授权。

> 目标分支：`ThunStorm/do-not-litter@codex/mac-mini-implementation`。本计划基于 2026-10-14 静态源码检查；实施前确认当前 HEAD 与在途修改。**不需直接修改 LocalAiMux 代码**。

## 0. 边界与不可破坏约束

- 保持现有 `PlaceMention.id`、`PlaceVisitWindow.place_mention_id`、`PlaceInsightItem.place_mention_id`、`AINoteSection.place_mention_ids_json`、`VideoScreenshot.place_mention_id`、POI 人审流程、外键级联及现有 API 兼容；绝不直接删除 `mention_id`。
- 标题是 `VideoAsset.title` 的来源元数据，不是语音转写 `Segment`。不能造假的 Segment ID 或用标题冒充转写引文；事实出处必须区分，保留原始标题和精确可验证的文本片段。
- 不能因为 Token 节约而裁掉转写后段、弱化 Evidence 校验、抬高 POI 自动确认率或自动批准待确认地点。
- 先写回归与 Golden，再做改造；避免全仓盲扫。优先局部修改，不引入独立新服务或冗余数据库表。
- 上游订阅额度、缓存命中 Token 与 API 计费/配额并不等价；所有收益以真实 Provider 上报为准，否则记作 UNKNOWN。

## 1. P0：将视频标题纳入时间证据链

### 现状与缺口

- `services/grounded_map.py:get_or_create_grounded_map` 给 Ground Map 模型传标题，但 `prompts/grounded_map.md` 的 Claim 只允许逐字 Segment 证据。
- `services/video_support.py:_visit_windows_from_candidate` 只接受 `segment_texts` 可逐字匹配的 `source_text`，无法把纯标题时间转成 `PlaceVisitWindow`。
- `generate_note` 的 `NOTE_REDUCE` 主路径只发送 GroundedEvidencePack，而非显式标题证据；前面的标题上下文可能被丢掉。
- Ground Map 的 `semantic_hash` 依据 `transcript/version/content_hash/config` 等，不包含实际 `asset.title`；标题变化可能复用过时 Artifact。
- Semantic Map v3 输出 `claims.subject_entity_ids`，但当前 `_ground_map_facts` 更倾向依据重叠 Segment 绑定 mention，未完整建立 claim 对应特定地点的继承映射。

### 实施

1. 新增精简的、确定性的 `title_temporal_context` 解析层（可放 `services/` 邻近小模块），输入 `asset.title`，输出：`source_kind='TITLE_METADATA'`、`source_text`（原标题精确子串）、月份数组、季节、旬、时段、语义 `intent`（推荐/不推荐/限制/未知）、`scope`（视频主题/章节/特定地点/非推荐行程时间）、`confidence`、`parser_version`。优先复用 `_months_in_text`、`_calendar_fields_from_text`，但**不能**仅看到“月”就判推荐。
2. 建立保守传播规则：只向本视频明确推荐且处于该标题适用主题/ContentUnit 的地点继承；背景 `REFERENCE_ONLY/SKIP`、反例、否定推荐、明确冲突者不可继承。正文明确时间信息优先于标题推断；如某点正文称“十一月闭园”，不得变成十一月推荐。
3. 优先用 `PlaceMention.metadata_json` 中带版本的 `temporal_context` 保存标题继承源，再物化为现有 `PlaceVisitWindow`；新增可区分于 `SOURCE_FACT` 的来源值（例如 `TITLE_CONTEXT`，名称要全局一致），保留 `source_id`、`source_text`，不要伪造 `segment_ids`。若现有知识/证据完整性依赖 segment 非空，则明确适配 Title evidence 的验证逻辑与 DTO；标题推荐不能被错误计为两条独立正文来源的 CONSENSUS。
4. 增加稳定的唯一去重键：`place_id + source_id + mention_id + temporal_kind + time_window + source_text_hash`，保证重放或重物化不重复；不删除用户维护的时间窗口。
5. 将已验证的 Title context 以紧凑表示传递给 NOTE_REDUCE 的输入和 fallback 渲染，可在笔记摘要与地点详情显示“11 月适合前往 · 来自视频标题”，与“正文原句佐证”区分。
6. 将 `normalized_title` / `title_temporal_context_hash` 与 `parser_version` 加入 Ground Map 语义身份；变更时安全失效缓存，避免旧 Artifact 被复用。必要时提高 `MAP_PROMPT_VERSION` 并增加 Golden。
7. 修正 Semantic Claim（包括适宜时间类）到 Entity/PlaceMention 的映射，以 `subject_entity_ids` 为主、ContentUnit 为辅助；绝不把同一 Segment 的所有时间事实分配给所有地点。

### 建议 Golden 矩阵

| 标题 / 正文情境 | 期望 |
|---|---|
| 《十一月哪里人少景美》 + 推荐 A/B | A/B 拥有 11 月 Title context，来源为 TITLE_METADATA |
| 《十一月哪里人少景美》 + B 为比较用、非推荐 | 仅 A 继承 |
| 《十一月哪里人少景美》 + B 正文称“11 月闭园” | B 不得获得“11 月推荐”；冲突信息被明确记录 |
| 《十一月出发十二月回来》 | 行程时间不转最佳到访月份 |
| 《去年十一月旅行记录》 | 记录时间不转推荐月份 |
| 《十月中旬赏红叶》 | 10 月中旬 + FOLIAGE，非泛化全年推荐 |
| 同视频标题编辑、转写不变 | 缓存身份改变并产生新的标题投影，不误命中旧结果 |
| 重放两次、已有人工时间窗口 | 无重复、无误删人工编辑 |

## 2. P1：保留 Mention ID 作为内部业务锚点，减少无效重复

### 保留

- `PlaceMention.id` 是“本视频本次提及”的实例标识，不等价于全局 `Place.id` 或高德 POI ID。
- 不拆数据库外键、不修改已持久化主键，也不把多个视频/多个 ContentUnit 的同一地点 mention 强制合并。

### 优化

1. 前端普通用户页隐藏随机字符串 ID；只在调试面板、复制诊断或开发 API 中可见。前端 `id` 仍作 key、跳转及人工确认定位。
2. 模型输入：复用 `ai/request_compiler.py` 的请求边界短 ID（`p...`/`s...`），坚持响应时还原规范 ID；避免在原始 Prompt 与 JSON 包内一遍遍传完整 canonical ID。不能修改持久化 ID。
3. `_pack_place_evidence` 只传当前分包用到的 mention，并尝试去重重复证据引文；不存在的数据不能引用。
4. NOTE_REDUCE 若从事实到 mention 的确定性关系足够可靠，允许服务端在生成后补关联 ID，避免模型输出冗余 ID；必须先以 Golden 验证无混淆的多地点同段落场景，并保留 fallback 方案。
5. 自测：对同名不同视频、相同地点不同章节、同一 Segment 多地点、模型引用不存在的 ID、用户人工修改和重放版控做精确性回归。

## 3. P1：分片请求中重复 System Prompt 优化

### 不应该做

- 不能把“首片发送完整 System、后续仅发送正文”直接用在无状态 `/v1/chat/completions`：后续调用不继承上一片规则。
- 不能把现有 `ai/cache.py` 结果缓存当成跨不同分片的 Prompt 缓存。
- 不为了减少文本而削弱“只返回有证据的 JSON、不得幻觉、禁止错误 POI 确认”的系统级守卫。

### 第一阶段（无 LocalAiMux 变更）

1. 对 `GROUND_MAP`、`NOTE_REDUCE`、`CORRECT_TRANSCRIPT` 统计每次发送的 `system_chars`、`domain_chars`、实际 Prompt 指纹、静态/动态前缀长度、请求数、总调用耗时、reported/estimated/unknown tokens、上游报告缓存 tokens。
2. 把稳定任务指令放在前面，动态 `视频标题/分片编号/时间码/证据包` 放后面；不在固定前缀中混入 job_id、日期、动态哈希。相同任务的 prompt/template version 恒定且审计可追踪。
3. 只清除**可以证明语义冗余**的静态说明和重复示例。不同 Stage 使用适量说明，而非为了 cache 强行加长 Prompt。维护原证据与 JSON 契约。
4. 避免每一分片完整复制与当前分片无关的 Domain Pack/证据索引。按 ContentUnit、实际 mention / target segment 精确投影；保留多地点跨段落所需邻段。
5. 现有请求编译器/缓存已落地，不再重建；对缓存命中必须区分：`APP_RESULT_CACHE_HIT`、`PROVIDER_PREFIX_CACHE_HIT`、`UNKNOWN`。

### 第二阶段（有真实支持证据才启动）

- 上游接口如果公开支持可复用 Prompt 前缀/缓存控制，优先使用 Provider 原生能力；不能假设 Codex 桌面订阅 AppServer 与 OpenAI 直连 API 是相同合同。
- `/v1/responses` + `previous_response_id` 只在有原生 resume 能力、上下文边界明确、同一视频且同一任务指令版本时考虑实验性顺序模式。**默认每片无状态独立请求**，避免上下文增长、前片污染后片、错误跨片传播和恢复困难。
- 会话方案必须支持切片失败重试、断点重放、拒绝跨模型续接、控制上下文过长，并验证质量不低于无状态基线。

## 4. 统一测试、基线和验收

优先扩展：`backend/tests/test_video_semantic_poi.py`、`test_travel_recommendations.py`、`test_video_notes.py`、`test_ai_request_optimization.py`、`test_ai_cache.py`。

比较当前基线 vs 新代码时必须固定：测试样本、模型、温度/努力程度（若上游支持）、分片策略、提示词版本、是否使用客户端结果缓存、是否真实上游调用。至少报告：

- 时间事实准确召回率（包含标题）、错误传播率、标题/正文冲突处理率；证据完整率；正文中多地点、多个主题视频的归属正确率。
- POI precision/recall 和人工复核量不得恶化；旧笔记、地点、时间窗口、人工状态及导出格式不破坏。
- `raw_request_bytes`、估算输入 Token、可信上游 input/output/cached tokens（未知要标 UNKNOWN）、调用次数、处理时长；分别呈现 Stage 而不是只报总数。
- Cache 命中前缀收益不能以字节节省冒充，不能把已缓存 Token 假定等价于订阅额度减免。

### 执行顺序

A. 仅加测试与观测基线 → B. Title evidence 和作用域传递 → C. 物化、渲染与 Replay/cache 指纹 → D. Mention 网络边界/模型包紧缩 → E. Prompt 稳定前缀与实测配对 A/B → F. 封版文档。

实施后先运行局部后端测试、全后端回归/格式检查、前端类型/构建与对应 UI 测试；除非用户明确授权，不调用真实模型、不改生产数据库、不自动执行迁移/重跑生产视频、不部署、不提交推送。评估结果写入当前文档体系和独立 Benchmark 报告，避免新增重复的权威文档。
