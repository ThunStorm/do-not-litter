# P｜POI 后端正确性与复核契约（2026-11-13）

范围：执行 P1→P2→P3，仅后端匹配和 U 的原因/动作 DTO；不实施 U。接手 HEAD `e9c509913208480604295f3db6acf4053f73a221`，工作树已有 G0/Q/R、资源保留、router/video_notes、video_support 时间解析等在途修改，全部保留。接手差异保存在 `/tmp/poi-p-20261113/preexisting.patch`；本次结果属于含这些修改的工作树，不代表单独 HEAD。未提交、推送、部署、重启；无 Schema、依赖或历史数据变更。

## P1：材料、原因与保守行为

G0 清单 127 条全部 unjudged，已人工裁定 POI 样本 0；没有可用于阈值调整的人工金标或独立保留集。13+8 当时待核快照未在冻结材料取得，不以当前数据库查询重构；未读取生产库。使用已有 `poi-resolution-golden-v2.json` 的 17 个合成规则期望及现有 Mock 反例核对，不冒称人工裁定。逐例 raw_name、行政提示、类别、分差、规则拒绝与版本见[机器分析](POI_CORRECTNESS_P_20261113.json)；没有实际查询/详情响应的字段明确 NOT_RUN。

| 原因/阶段 | 结论与处置 |
| --- | --- |
| 名称/别名 | 保留原词和 suggested_name 区分；没有新证据证明应改别名/名称规则，NO_CHANGE |
| 多义/地域不足 | 既有同名、连锁、无地域及跨地点上下文反例保持 REVIEW；不能因为待核数量多视为缺陷，NO_CHANGE |
| 对象类别/区域 | 未映射 OTHER、景区子项/入口/政府代表点继续独立门禁；已有 R1–R13 和区域身份测试覆盖，NO_CHANGE |
| 候选完整性 | 满页、重复页、部分搜索失败阻止自动确认；没有“有效候选被满页遗漏”的冻结真实反例，分页 NO_CHANGE |
| 详情一致性 | 名称/地域/类型/坐标必须一致；隔离库详情城市冲突为 REVIEW、完全一致可确认，NO_CHANGE |
| 全失败后的旧候选 | **真实代码缺陷**：失败仅写原因，旧候选仍可被人工确认接口接受。两类失败先红后绿；清除本轮失效候选并强制 REVIEW/POI_SEARCH_FAILED，原词、证据、人工决定不改 |

17 例规则回放：基线/本次均自动确认 11、错误自动确认 0、REVIEW 6，规则期望未裁定 0；这个 0 仅表示夹具自带期望完整，不代表存在独立人工裁定。Top-1/Top-3 均 1.0，均仅为旧候选的规则回放，无详情/真实来源门禁执行，不称真实准确率。G0：自动确认 0（未运行解析）、误确认未知、未裁定 127；真实质量 N/A。新增隔离 resolver 配对例自动确认 1、误确认 0（合成期望）、详情冲突拒绝 1；不与 Golden/G0 混加。

## P2：最小差异及保护

仅在 `video_support.resolve_mentions_with_amap` 的搜索异常与 FAILED 分支清空失效候选并记录原因/来源/决定；不改分数、阈值、名称、地域或缓存/QPS。保留人工确认优先保护、USER_REJECTED、revision、运行 Job/lease、Provider 大小写、墓碑、隐藏 Marker 与版本身份；API 写入仍原子校验，不以 DTO 替代服务端门禁。原有 `poi_error` 行为不扩展。

维护性评估：可选切口为评分链、Provider 查询链、复核 DTO；只新增只读 `services/poi_review.py` 隔离 DTO 组装，评分/事务/异常公共入口不搬迁，不重造系统。

## P3：U 接入契约

正式领域契约在[旅行领域 7 节](../product/TRAVEL_FOOD_PIPELINE.md#7-poi-resolver)。`GET /api/travel/place-reviews` 每行和 `POST /api/travel/place-mentions/{mention_id}/poi-search` 成功响应增量提供 `review_contract`，旧字段兼容。11 组[合成 Mock](../../backend/tests/fixtures/poi_review_v1.json)由当前构造器生成，仅供 U，不是真实历史记录。

| 字段 | U 的解释与动作 |
| --- | --- |
| version | 固定 `poi-review-v1`；未知版本保守处理 |
| authority | mention_id/revision 是写入权威；保留 asset、submission Job、NoteVersion、Place、Destination 身份，不用 note/ntv 互换 |
| classification | 当前分类：NAME_UNCERTAIN/AMBIGUOUS/OBJECT_CATEGORY/INCOMPLETE_CANDIDATES/DETAIL_MISMATCH/SEARCH_ERROR/NO_RESULTS/INSUFFICIENT_EVIDENCE；人工搜索成功为 MANUAL_RESULTS，拒绝为 MANUAL_REJECTED，区域为 AREA_ONLY，确认态为 UNIQUE_CONFIRMED |
| automatic_classification / reason_codes | 保存自动判定原因；人工搜索后仍可能保留旧自动失败码，不能把旧原因当成本次人工搜索失败。未知原因保留原码并回退 INSUFFICIENT_EVIDENCE；文案由 U 维护，不解析 reason 字符串 |
| candidate_source / search | AUTO/MANUAL/HISTORICAL 与对应查询 trace；仅对实际可得的 query hash/count、duration、requests/cache_hits、候选 ID 等原样返回，缺失不能补零推断。FAILED/PARTIAL 或截断为 PARTIAL，其余 UNKNOWN；短页不是全集证明；不输出无依据的 COMPLETE |
| effective_context / evidence | 保存的行政提示及 content_unit；不是新推断。evidence 自实际 Segment/Snapshot/Source 校验，含原 quote/segment_ids/版本/valid；失效证据仍保留引用，禁止捏造出处 |
| detail_verification | FAILED/AUTO_VERIFIED/MANUAL_SELECTED/CONTEXTUAL_FETCHED/NOT_RECORDED；上下文详情抓取不是一致性验证通过，人工选择也不冒称自动详情验真 |
| allowed_actions / blocked_by | SEARCH、REJECT 或 RESTORE；运行 Job 或遗留 lease、SUPERSEDED、删除保护禁用动作。空数组是禁用，不是等待 UI 猜原因 |
| candidate_actions | 按 provider_id 提供 CONFIRM 及 blocked_by；校验候选坐标/名称、Provider ID 重复、删除墓碑；隐藏 Marker 不被读取或改写。CONFIRM 是人工选择能力，不表示自动门禁已通过 |
| manual_decision | 原人工确认/反馈；只读保留，不修改作者意见 |

U 应把 authority.revision 传入搜索及确认的 expected_revision，409 后重新读取；拒绝/恢复沿用既有接口（当前不接收 expected_revision，但后端以读取到的 revision 原子更新）。动作是读取时提示，写接口仍须重新检查；搜索成功用返回的新 revision/DTO，确认/拒绝/恢复后重新获取队列。每个候选数据继续在外层 candidates 中，名称/地址/类型/score/match_explanation 沿用既有结构；Mock 字段缺失表示未知。错误码 PLACE_JOB_ACTIVE、REVISION_CONFLICT、PLACE_DELETED 等依既有写接口返回，不新增绕过接口。

未实施分页，因此没有新增分页预算：沿用最多 5 次搜索（含附近搜索，重复候选按 ID 去重），每次单页 20 条，未增逐候选模型或请求。网络重试/缓存/QPS 沿用 Provider；现有 20 秒超时和进程间锁等待不构成严格 Mention 墙钟上限，本次不虚构该保证。未来若有明确遗漏反例，先另行冻结页数/候选数/请求数/墙钟上限，再改分页。429、网络异常均不自动确认；取消链保持原有语义，无新增重试。

## 验证、限制与停止

目标：失败旧候选不得确认、已确认人工数据不变、详情冲突零自动确认、搜索最多 5 次、满页/重复页保守、同名跨城/景区父子/区域、负向/引用、revision 并发、运行任务与终态 lease、隐藏和墓碑、DTO/Mock。新增13项；目标49项、后端全量970项、前端64项、Ruff/ESLint/TypeScript/隔离构建与质量回放均通过，业务联网尝试0。完整检查步骤与源码哈希保存在本报告配套JSON的validation/provenance；原始日志在 `/tmp/poi-p-20261113/full`。

收尾入口：`scripts/check_g0.py --output-dir /tmp/poi-p-20261113/full`，固定本机 Python 3.12.14、Node 22.21.0、pnpm 11.19.0；虚拟环境 pytest shebang 指向旧路径，因此通过 `.venv/bin/python -m pytest`，未更换依赖。使用离线网络守卫和隔离 SQLite、隔离前端构建；不写正在提供服务的静态目录。真实高德串行对照、生产实际确认、历史回写均 **NOT_RUN，分别等待授权**。UI 由 U 负责；无前端行为变化，不做 Browser、不发布。到 P 停止；下一步仅 U 按契约接入。
