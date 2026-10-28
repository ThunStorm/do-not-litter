# 地点时节、作者路线与云南回归实施记录（已归档）

2026-10-28授权工作包。输入包及原始参考哈希见 backend/tests/fixtures/travel_pipeline/yunnan_bv16yem6reyx/provenance.json。人工模拟不是权威金标；保留71候选分类、11组路线线索与待核项，不据此制造POI。

|阶段|冻结范围/影响|兼容与验证|
|---|---|---|
|P0|travel_recommendations/video_support逐地点时间、TravelBrief及PlaceDetailPage人工窗口|背景零加权，禁渔/局部道路不关闭景区；目标测试及云南P0|
|P1|证据范围/活动/用途/精度与跨年解析，出行事实|复用mention metadata与Insight JSON；逐字证据、歧义待核；云南A/B/C及非云南负例|
|P2|作者RouteGuide/Stop/Evidence/Condition版本化JSON、只读API/路线页与显式复制|保存在新GroundedMapArtifact.semantic_options_json；绑定当前Note/Transcript，不回写旧Artifact，不覆盖RouteDraft；云南D及身份/墓碑测试|
|P3|只读dry_run审计、travel_export_v2地点/路线分文件、兼容及成本比较|无Schema迁移，无生产回填；离线SQL/耗时/零新增调用实测，旧导出兼容、人工资产保全|

先目标验证，各阶段复跑云南；完成后一次全量后端/前端及Lint/类型/隔离构建。源码与静态保存点、已验逻辑DB备份、空闲/完整性门禁后无迁移重载；PC/Mobile生产Browser验收。真实模型、高德、视频重跑与生产回填不在授权内。部署与提交/推送由本轮用户直接授权。最终契约归专项、验证归状态/benchmark、生产归CURRENT_HANDOFF；本计划完成后归档。

源码P0–P3已落地；真实模型省略route对象暴露后补证据语法恢复、单AREA锚点区域上下文与候选去静默截尾，真实响应冻结为额外回归。模型原响应的18个原词候选字面未匹配需复核，不冒充完整质量通过。最终测试、生产与提交结果分别见当前实施状态、交接与benchmark/YUNNAN_REGRESSION_ACCEPTANCE_20261028.md。输入zip已备份至本轮发布保存点，仓库只保留冻结原稿/参考与哈希，避免planning重复压缩包。
