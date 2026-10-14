# 标题时间证据与 Prompt 离线 A/B

采样日期：2026-10-14（北京时间）。范围：确定性规则、Mock Provider、合成请求表示；未调用真实上游、未重跑生产视频。机器结果：[TITLE_TEMPORAL_PROMPT_AB.json](TITLE_TEMPORAL_PROMPT_AB.json)，复现：`PYTHONPATH=backend/src <生产Python> scripts/benchmark_title_temporal.py --output <结果JSON>`。

## 请求表示

固定 16 个 Segment、8 个 Mention、当前包 2 个事实；模型 NONE、参数 N/A、原始样本/分片/System 相同、客户端结果缓存关闭。测量范围是 messages JSON，非完整 HTTP payload；projection_ms 仅为编译耗时，非 Provider 延迟。

| Stage | canonical 基线字节 | 既有编译器基线 | 本轮投影后 | 本轮新增降低 |
| --- | ---: | ---: | ---: | ---: |
| GROUND_MAP | 4,907 | 4,370 | 4,370 | 0% |
| NOTE_REDUCE | 4,656 | 3,252 | 3,042 | 6.46% |
| TRANSCRIPT_CORRECTION | 9,844 | 2,570 | 2,570 | 0% |

既有短 ID/校对上下文去重收益不归因于本轮。NOTE_REDUCE 的增量来自清除该包未用的 Segment 引用，保留同一证据与地点。真实标题上下文会增加必要输入，不能用本合成表推算整视频净 Token 节省。input/output/provider cached tokens、上游调用耗时、缓存前缀收益均为 UNKNOWN；真实调用数为 0。

## 离线质量边界

Golden 覆盖推荐月份、行程/记录时间拒绝、否定/闭园、非法月份、旬/季节、比较/用户拒绝、正文优先、特定地点/主题/地域范围、同段多地点 Claim、标题编辑缓存失效、重放/地点重新绑定/人工窗口保留、DTO 出处与删除保护、fallback 笔记及缓存分类。确定性预期全部由目标测试验证；输入明确推荐、作用域明确的基线样本标题时间召回 1/1（旧实现 0/1），受检反例错误传播 0。此为规则回归，不能作为真实视频召回率或真实模型 POI precision/recall。

POI Resolver/自动确认策略未修改；相关既有语义、旅行推荐、缓存、请求编译器与视频回归继续验证。真实模型时间事实召回、错误传播率、冲突处理率、POI precision/recall、人工复核量及长视频时延均 NOT_VERIFIED，需要单独授权与 Ground Truth。原生 Provider 前缀/会话缓存第二阶段仍 DEFERRED，不将连接可用等同于原生支持。

## 发布与验证边界

源码验证：标题证据17项、相关目标110项、后端完整458项、前端24项及Ruff/Lint/TypeScript/隔离构建通过。生产 `http://127.0.0.1:8787` 的1440×1000/390×844目标流程在Edge/Playwright通过：页面身份/非空、无框架覆盖、无相关console/溢出，标题与正文来源分离，只有人工窗口允许移除，模拟移除后派生窗口保留，月份菜单切换生效。Browser插件未提供，因此按测试技能使用Playwright；仅GET读取生产，新增窗口/DELETE响应拦截模拟，不替代真实新视频产物验收。截图/报告保存在交接保存点的browser/，当前服务与数据核对只见交接生产快照。

最终诊断补修：实际Provider请求字节计量按已安装HTTPX的紧凑UTF-8 JSON序列化计算，六入口回归逐一对照HTTPX Request.content长度；目标108项与最终后端458项通过，仍未真实调用Provider。
