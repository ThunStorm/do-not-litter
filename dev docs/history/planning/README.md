# 已归档实施计划

> 这里保存已由后续提交覆盖的执行计划，供追溯设计决策、验收条目与当时范围。它们不是当前待办，也不构成新的实现授权；现状以 [实施状态](../../IMPLEMENTATION_STATUS.md) 为准。

| 归档计划 | 覆盖证据 | 未进入本轮的后续方向 |
| --- | --- | --- |
| [Place Intelligence + Interactive Map V2](PLACE_INTELLIGENCE_MAP_V2_IMPLEMENTATION_PLAN.md) | `8a6484b`、`77e37eb`、`161d320` | 推荐评分、自动行程；已转入 [Future Roadmap](../../planning/FUTURE_ROADMAP.md)。 |
| [地图稳定化、地点管理与旅行决策](PLACE_MAP_STABILIZATION_AND_TRAVEL_DECISION_PLAN.md) | `77e37eb`、`161d320` | 地点比较托盘、推荐与自动路线；已转入 Future Roadmap。 |
| [地图 / 地点管理 / 路线稳定化 v2](MAP_PLACE_MANAGEMENT_AND_UI_REFINEMENT_PLAN.md) | `161d320` | 本轮明确排除的推荐评分与自动行程；已转入 Future Roadmap。 |
| [AI Benchmark 与本地模型路由](PLAN_A_AI_BENCHMARK_AND_LOCAL_ROUTING.md) | Benchmark、Capability Probe、离线 Golden 与 E2E Harness 已进入源码 | 真实 Provider/视频矩阵仍以 AI Gateway 生产验收为准。 |
| [POI 自动确认与地点知识聚合](PLAN_B_PLACE_POI_KNOWLEDGE_QUALITY.md) | Resolver Golden、Review、知识聚合、共识/冲突已进入源码 | 真实 AMap/视频与移动端验收仍未外推。 |
| [季节地图、推荐与 Visual Fact](PLAN_C_TRAVEL_RECOMMENDATION_AND_VISION.md) | Visit Window、偏好事件、确定性推荐与 Visual Fact 离线 Gate 已进入源码 | Vision、AMap、视频与移动端验收仍未外推。 |
| [UI、视频与 POI V2](AGENT_IMPLEMENTATION_PLAN_UI_VIDEO_POI_V2.md) | WP0–WP15、0022、Source/Asset 复用与缓存稳定性已交付 | 外部 Adapter、Vision、备用 ASR 与移动端验收保留为生产门禁。 |
| [视频质量与 Evidence](VIDEO_WORKFLOW_QUALITY_MASTER_PLAN.md) | WP0–WP22、0020、Grounded Evidence 与统一 Review 已进入源码 | WP23 仅在性能证据触发时评估；历史修复须指定对象后执行。 |
| [LLM Token 与自动化优化](LLM_TOKEN_AND_AUTOMATION_OPTIMIZATION_PLAN.md) | Grounded Map、路由/预算/重试守卫、复用、异常与离线 Gate 已进入源码 | Production Graduation 仍须按真实证据完成。 |
| [视频工作流 Benchmark 与验收](VIDEO_WORKFLOW_BENCHMARK_AND_ACCEPTANCE_PLAN.md) | Fixture Golden、只读采集与离线 runner 已进入源码 | 有标注真实样本与 Provider 结果仍是未来验收。 |

计划中描述的旧 migration head、旧 UI 现状和“下一 WP”均只对原写作时点有效。若需要追溯，先读当前状态与冻结清单，再按章节查阅本目录文件。
