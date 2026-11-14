# Q 内容质量包核对（2026-11-13）

执行范围：[Q1→Q2→Q3](../planning/video-workflow-20261112/02_CONTENT_QUALITY.md)，遵循[执行契约](../planning/video-workflow-20261112/09_AGENT_EXECUTION.md)。本次结论为 **OFFLINE_PASS / BUSINESS_NO_CHANGE**：完成可用材料核对与现有规则回归；Q 的人工裁定反例关闭及真实模型质量验收尚未完成。

## 基线与工作树

HEAD `e9c509913208480604295f3db6acf4053f73a221`。接手已有 router/video_notes、cover_text/grounded_map、place/source retention、video_support、conftest/test_api 修改，以及资源依赖/截图保留、G0 fixture/检查脚本/CI和规划文档等未提交内容。本轮不覆盖这些在途修改，不将其记为本轮修复。尤其 grounded_map 的日期解析版本和 video_support 的 DAY/MONTH 区间处理已经在途。

[G0](GOLDEN_QUALITY_BASELINE.md) 冻结材料哈希复核通过：云南101条、12月错峰24条、标题/封面时节2条，合计127条，全部 unjudged（100%）；这不是127个事实/地点金标。厦门餐饮、贵州完整视频、独立快速多区域保留集为 BLOCKED_SOURCE。结构回放材料可用，已裁定漏项/错归属清单为空。缺失数据库 Source/Snapshot/Transcript 身份保持未知，真实封面图不在冻结清单。

## Q1 定位与最小复现

最小复现入口：`backend/tests/fixtures/travel_pipeline/december_reverse_bv1hrxe6yebq/baseline.json` 的 segments、semantic_map.claims、sections；以下是已有开发反例及待裁定线索，不能计为人工裁定 FN。

| 原句/对象 | 期望与保存状态 | 首个可观察差异/当前处理 | 复现入口 |
| --- | --- | --- | --- |
| “十二月份开始是梯田的灌水期” | 原句可回溯；转写有“灌水”，保存 Claim/章节未见对应原词 | Transcript→保存 semantic_map 间存在疑点；缺原请求分包及模型原响应，不能区分模型、验证或解析首偏差。现有 source_gaps 标 POSSIBLE_SOURCE_OMISSION，不创建确定 Claim | test_note_quality.py::test_source_scan_reports_omitted_risks_without_creating_claims |
| “开渔节期间人多价格高可能会遇到没有房的情况” | 保留日期、否定与可能性；保存 Claim/章节未见“没有房” | 同上；现有原文待核诊断通过，不把玉溪风险广播到全部地点 | 同上 |
| “开渔节是二十五号前后” | “前后”不得升级精确日期；保存 Claim/章节未见“二十五” | 只定位到转写与保存产物之间；原词未命中不等于语义漏项，待逐条裁定 | baseline.json，seg_169d1eb1d36f4d05b36c36c10e225ab9 |
| “丙察察主线十二月份容易积雪结冰如果你是普通的家用轿车那就不建议走这条路” | Claim已保留完整引文，章节为局部路况 SUPPLEMENTAL | 保存产物未复现此句丢失；局部限制不变成全目的地关闭 | test_yunnan_multiregion_travel_golden.py 的局部限制/道路用例；test_recommendation_intent.py |
| 拉萨跨包身份及河池/三门海分章 | 同源具名转场归并；区域主章可保留，原身份/锚点不改 | 现有 semantic_identity 与 note_structure 已覆盖；不重复实施 | test_note_quality.py 的 boundary_lhasa、explicit_unit_hierarchy 用例 |
| 模型归纳只返回“门票20元” | 其余事实不静默消失；缺项警告并保留待归纳证据 | 现有 NOTE_REDUCE→Note 覆盖兜底及跨包归组通过（Mock响应） | test_poi_note_structure.py::test_new_generation_merges_across_packs_and_audits_omitted_facts |

核对段ID：灌水为 `seg_3a3616f61a284a87af6d5c693b77ea94`，缺房为 `seg_9bfa63059f2b49ebb041077144767504`。上述词面检查只提供定位线索，不用词频计算事实召回。历史[11月5日报告](NOTE_QUALITY_ACCEPTANCE_20261105.md)的24/24可追溯不能替代本轮独立语义裁定，G0未将其晋级。

输入错源：本轮未拿到可复现的 Source/Snapshot→Transcript 错源反例，未核实媒体与转写同源。缺版本身份与上游原请求链作为 **S 接手证据缺口**登记；不据此宣称已证实错源，也不调整 Prompt 掩盖。未执行 S。

## Q2 / Q3 决定与停止条件

Q2 **NO_CHANGE**：检查 grounded_map、semantic_identity、note_structure、note_quality、video_support 及相关测试；本轮没有复现新的确定性丢失。既有规则保留主体、原词、否定、条件、逐字引文及版本，比较/路线/未归属主题章独立；历史阅读投影保留原sections、Markdown与旧锚点映射。`evidence_represented_count`只计证据覆盖，`summarized_fact_count`仍为 null，质量状态不升级为语义通过。

Q3 **NO_CHANGE**：缺少已裁定反例和完整原始响应，不能证实模型首答漏项。本轮不准备无对应反例的 Prompt 改动，不加阶段、逐地点复核或额外调用。真实配对验证需另行专项授权；本轮未读取生产服务、历史缓存或数据库补证，不重解析历史。

## 验证与指标

2026-11-13 对接手工作树执行，不能外推为单独 HEAD 或生产验收：

- G0质量入口151项通过；冻结引用可达127/127，哈希错误0，网络守卫阻断尝试0。覆盖云南 P0_CRITICAL、跨段否定/月份、局部道路、标题正文/封面来源、漏否定/跨来源/错POI检测器自检。
- 补充49项通过：test_poi_note_structure、test_video_semantic_poi、test_grounded_map、test_recommendation_intent；覆盖比较章独立、无地点的未归属材料、跨包引用拒绝、历史版本/旧锚点、证据包边界、背景提及及误确认门禁。target.network.log未产生记录；没有执行真实 resolver。
- 长列表原句不截尾由现有12条合并引文及云南80条以上候选回归覆盖。餐饮、贵州完整视频及独立快速口播保留集未验；合成非目标规则用例不能替代这些真实样本。截图仅沿用既有投影断言，本轮未做真实图片/Browser验收。

| 指标 | 基线 | 本轮（无候选业务改动） |
| --- | --- | --- |
| 已裁定事实/地点召回，误报 TP/FP/FN | N/A | N/A |
| 已裁定事实归属、关键限制语义完整性 | N/A | N/A；规则断言通过 |
| 未裁定比例 | 127/127（100%） | 127/127（100%） |
| 来源文件引用可达 | 127/127 | 127/127；不代表语义完整 |
| POI自动确认总数/错误数/准确率 | 0 / 未知 / N/A | 0 / 未知 / N/A；无resolver执行 |

原始日志、JUnit与带源码/Fixture哈希的质量JSON在 `/tmp/do-not-litter-q-20261113/`（quality.json、quality.junit.xml、quality.network.log、target.log、target.junit.xml）；临时目录非永久证据归档。复现命令为 `.venv/bin/python scripts/check_quality_baseline.py --output /tmp/do-not-litter-q-20261113/quality.json`，补充测试在同一离线网络守卫下执行。

本轮只有报告、状态、导航/清单及对应生成物变更，故不重复业务全量；检查文档生成一致性、链接及diff。模型首次/恢复/备用调用均0，无Token/费用实测（不填为缓存节省）；无Schema/依赖/历史数据改变，无服务重启、发布、提交或推送，不自动写交接。维护性抽取 NO_CHANGE。下一步一项：对上述12月线索完成逐条人工裁定并补同输入分包/原始响应链，再定位可修首偏差；真实质量结论保持未验。
