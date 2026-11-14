# 视频工作流增量计划：执行总览

2026-11-12 修订。状态：待实施计划，不是实施/上线记录。本次仅编制文档；不授权业务代码、真实调用、历史数据或提交推送。原始依据为用户提供的七份 Plan、总览与派发模板；逐项去向见[审校映射](10_REVIEW_MAPPING.md)，文件哈希见 `source_manifest.json`。原文件保留在用户 Downloads，不复制成第二套有效计划。

## 现状与范围

本次本地分支 `codex/mac-mini-implementation`，HEAD `e9c509913208480604295f3db6acf4053f73a221`；存在既有未提交的资源保留、封面、地图及 API 修改和测试。计划依据为此工作树的定点源码核查与[实施状态](../../IMPLEMENTATION_STATUS.md)，不能把工作树能力当成该提交的能力，也未复核生产。902/944 等历史测试数量不作为本次验证结果。

已核对：`note_quality.py` 的 `summarized_fact_count` 仍为空；`place_knowledge.py` 已按独立 Source 计数、保留 observations，并把同类多簇判为 CONFLICT；时间缺失会回退 created_at。`video_support.py` 已有地域冲突、候选完整性及人工确认保护；JSON 有界恢复、短 ID、预算和冷却续跑已有实现；本地未见 `.github` 目录。源码观察只是改进线索，未复现的假设不直接变为修复任务。

明确排除独立旅行决策台、作者路线转个人行程、重建地图/路线系统、招聘、RAG/知识图谱、多 Worker 和跨仓修改。既有路线复制功能保留；不因本次排除而删除它。

## 拆并后的执行包

六个业务领域保留；共享基线与 CI 独立前置，来源领域拆成现有链路与可选新平台，共八个可分别派发的包。每次派一个包中的一个阶段，阶段完成即按出口停止，不自动把整套计划变成授权。

| 包 | 目的与交付 | 优先级 | 硬依赖/出口 |
| --- | --- | --- | --- |
| [G0 基线与离线门禁](01_BASELINE_AND_GATES.md) | 小规模已裁定金标、对照指标、可复现检查入口及 CI | P0 支撑 | 无；G0.1/2 可用即可放行下游，托管 CI 不阻塞 |
| [Q 内容质量](02_CONTENT_QUALITY.md) | 已复现漏项、错归属、时节/否定/阅读投影修复 | P0 | G0 对应类别裁定样本；不等全库标注完成 |
| [R 模型可靠性与成本](03_RELIABILITY_AND_COST.md) | 失败分类、预算内恢复、同条件收益 | P0 | 诊断可先做；语义/Prompt 变更依赖 G0 |
| [P POI 匹配与复核契约](04_POI_CORRECTNESS.md) | 原因、候选完整性、保守匹配与可读 DTO | P0 | G0 POI 裁定样本；Q 改身份时先冻结接口 |
| [U 待处理入口与复核交互](05_REVIEW_EXPERIENCE.md) | 合并原 02 复核 UI 与原 04 跨入口体验 | P1 | 受影响的 Q/R/P 原因和版本契约稳定 |
| [K 多来源事实对照](06_PLACE_KNOWLEDGE.md) | 修正聚合、条件差异和时效表达 | P2 | 对应身份契约稳定；不必等待 U 完成 |
| [S 现有来源可靠性](07_EXISTING_SOURCES.md) | Bilibili/YouTube/local 输入和字幕防污染 | P1；错源复现升 P0 | 来源 Fixture；不依赖全部模型优化 |
| [X 单平台试点](08_OPTIONAL_SOURCE_PILOT.md) | 明确选定平台的一档能力与诚实降级 | P2 可选 | S 契约、平台选择、合法样本及外部操作授权 |

默认顺序：G0.1/2 → Q → R → P → U → S → K；若已有错字幕/错源反例，S 提前到 Q 前并停止受污染样本的质量调参。X 最后按需启动；G0.3 托管 CI 和真实业务验收各自独立，不阻塞无需它们的离线工作。Q/R/P 不默认并行改 `video_support.py`，也不并发调用同一 Provider Key。没有复现缺陷时可交付 NO_CHANGE，不强行写代码。

## 共同验收与授权

执行、指标口径、发布与派发模板统一在 [Agent 执行契约](09_AGENT_EXECUTION.md)。状态分为 PLANNED、OFFLINE_PASS、LIVE_NOT_RUN、LIVE_PASS、NO_CHANGE、BLOCKED_SOURCE/DECISION；离线通过与真实验收分别记录，不能用一个“完成”抹掉未验证项。需求选择与冻结契约冲突时停止该分支，继续独立工作。

当前能力只更新 IMPLEMENTATION_STATUS；本计划保留范围与依赖，不滚动复制测试数量。只有用户要求写交接或实际前端发布需记录生产现场时才更新 CURRENT_HANDOFF，相应现场保留采样日期。既有专项是契约正文，本计划只做增量派发，不复制或覆盖旧正文。
