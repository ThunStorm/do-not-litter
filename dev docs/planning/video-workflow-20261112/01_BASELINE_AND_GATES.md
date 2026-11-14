# G0｜共享基线、指标与离线检查

返回[总览](README.md)。承接原 01 WP0、07 WP1/WP3 与各包重复的验收脚手架；执行[共同契约](09_AGENT_EXECUTION.md)。这是测试与证据包，不调整 Prompt、POI 阈值或业务路由。

## 工作阶段

1. **G0.1 样本与裁定。** 优先复用云南、12 月错峰、标题/封面时节的现存 Snapshot/Transcript/响应；厦门餐饮、贵州、多地区快速口播仅在材料存在时补充。登记缺失材料为 BLOCKED_SOURCE，不联网补抓、不合成后冒称真实。每条绑定 Source、Snapshot、Transcript/Note 版本、Segment、原句、时间范围、内容哈希及人工裁定者/日期；身份缺失明确未知。Agent 可准备标注草案，未经人工裁定的项目保持 unjudged，不自称独立人工金标。无需等待所有视频齐备；每个下游包只使用其已裁定的类别。
2. **G0.2 最小可复现门禁。** 固定基线源码/工作树摘要、解析器与 Fixture 版本，建立单条运行命令与机器可读结果。冻结当前关键反例断言，保留云南 P0_CRITICAL，不按历史测试数量判断完整性。离线重放已保存响应只能验证解析/归并/投影，不能证明新 Prompt 的模型效果。模型生成样本与人工判定来源分列；保留开发样本与未用于调参的保留样本，避免边改答案边提分。
3. **G0.3 轻量 CI。** 先核对 lockfile、Python/Node/pnpm 和平台依赖，复用现有命令，不更换包管理器。补最小 workflow 与本地检查入口：后端 Ruff/可移植测试、前端 lint/test/隔离构建、离线质量回放；最小只读权限，不注入业务 Secret、不读取生产库。测试外网访问失败即暴露，不以“Mock 名字”代替零业务外部调用证明。macOS Keychain/Vision/LaunchAgent 单列本机门禁，保留未覆盖清单，不大量删测。托管运行需后续提交/推送授权；未实际运行记 HOSTED_NOT_RUN，不以 YAML 校验冒充 CI 成功。

## 指标定义与出口

地点、事实、POI 身份分别评价，不能共用一个 TP。标注金标正例集合和输出集合，以语义实体/事实一对一匹配计 TP/FP/FN；比较点、背景点按角色单列，不强算应推荐 POI。precision=TP/(TP+FP)，recall=TP/(TP+FN)，零分母为 N/A。NEEDS_REVIEW 是输出处置状态，unjudged 是裁定状态，两者不作为与 TP/FP/FN 互斥的第四类；分别报告数量及裁定覆盖率，不把未裁定计对或计错。

POI 错误自动确认数、自动确认总数、裁定覆盖率同时列出：自动确认 0 时准确率 N/A，不能声称 100%。关键否定/限制逐条断言；来源可达率与语义完整性分别计算。每个对照记录样本数、模型/参数、输入哈希、缓存模式、首次请求/恢复/备用/未派发次数、耗时和 Token 口径。

交付 `dev docs/benchmark/GOLDEN_QUALITY_BASELINE.md` 及该报告引用的脱敏 JSON/Fixture manifest（实施时创建，本次尚不存在），记录裁定缺口。门禁自检需证明漏一条关键否定、跨来源引用、错 POI 会失败；不要只测报告文件存在。G0.1/2 的目标类别可用即可放行 Q/R/P；人工未裁定阻塞调参结论，不阻塞已复现结构错误的离线修复。

## 定位入口

按需读 `dev docs/testing/GOLDEN_SAMPLES.md`、`backend/tests/test_yunnan_multiregion_travel_golden.py`、`backend/tests/test_note_quality.py` 与 fixtures/travel_pipeline 下相关样本；构建命令见根 README、backend/pyproject.toml、frontend/package.json。不要求读完整合订本或全部测试目录。
