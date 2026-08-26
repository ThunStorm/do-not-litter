# 至简 模型配置与历史清理规格

版本：v0.4，更新日期：2026-08-21，状态：`IMPLEMENTED / BROWSER_VERIFIED`。适用部署：Mac mini 单节点。

## 1. 自定义模型库与路由

模型设置不再固定展示 DeepSeek、MiMo、Ollama 等预置槽位。用户可新增、编辑、真实测试并保存任意 OpenAI 兼容或 Ollama 模型配置；每条配置至少包括显示名称、Provider 标识、Base URL、模型名、超时和 API Key。API Key 只进入 macOS Keychain，接口和 SQLite 仅返回“已保存/未保存”状态。

“推理路由”独立于模型编辑：主模型与备用模型均从已保存的模型库中选择。转写校对另有可选的主/备用模型，两项均优先于推理路由，对应项留空时分别继承推理主/备用模型。主模型是唯一默认调用目标；仅在网络、HTTP、超时或 Provider 不可用等可恢复调用错误发生时才尝试备用模型。备用模型可留空；所有有效路由都未选择主模型时，依赖模型的任务必须进入 `NEEDS_USER`，不得回退到硬编码模型。

已被主/备用路由引用的模型不能删除；先切换路由才能删除。每次保存、路由切换、真实测试、自动备用切换和删除均写入审计日志，不含 Key。

## 2. 历史删除

任务列表与内容列表提供独立的“删除历史”入口。删除不是归档：操作需要确认，成功后列表立即移除并写审计事件。

- 仅 `COMPLETED`、`PARTIAL_SUCCESS`、`FAILED`、`CANCELLED`、`NEEDS_USER` 状态的任务可以删除；排队或运行中任务必须先取消，防止 Worker 写入已删除记录。
- 删除任务会级联删除其步骤和执行事件；已生成内容不会被连带删除，用户可在内容页单独判断是否删除。
- 删除内容会删除该内容及其专属 Claim/Evidence；若同一 Source 已无其他内容、视频笔记或活跃 Job，则同步删除其来源审计记录、Snapshot/Segment 与专属视频资产。Place、路线和已独立持久化的地点信息保留。
- 来源审计页支持手动删除孤立 Source；存在内容、视频笔记、排队/运行任务或取消清理 lease 时返回 409，并显示各类阻塞数量。
- 前端确认文案必须说明上述边界；操作成功后刷新任务/内容/待办/概览缓存。

### 2.1 视频完整转写 180 天自动清理（已实施）

视频完整转写采用固定 180 天保留期，不复用当前通用 `data_retention_days`/日志保留配置，也不增加可变的用户设置。保留截止时间从 Transcript 创建时计算，并显示在视频 AI 笔记页；有效期内可导出完整时间码 TXT。

Worker 启动时及最多每 24 小时执行幂等清理：正文、Segment 文本、Evidence quote 和 metadata 全文 fingerprint 被物理清空，保留 Transcript ID、版本、哈希、时间码元数据、`retention_until/purged_at`、AI Note 与截图。过期后页面显示“完整转写已按 180 天策略删除”，导出和完整转写接口返回 410。浏览器已下载到用户设备的文件不受服务端清理控制。

### 2.2 视频笔记删除（已实施，v0.4.6 更新）

视频笔记列表和详情均在 `…` 菜单提供“删除笔记”，共用 `DELETE /api/video-notes/{note_id}`。删除 AINote、版本、Section、TOC 和 Content 投影；若 Source 已无其他内容或活跃 Job，再清理 Source、VideoAsset、CoverAsset、Transcript、截图与 Segment Evidence。Place、路线及独立地点信息保留。活跃生成 Job 阻止删除，第一版不提供回收站。

## 3. 页面与响应式

模型页先显示“推理路由”两条选择框与状态摘要，随后是可展开的“已保存模型”列表和“新增自定义模型”入口。窄桌面下路由选择框垂直排布，编辑卡仍使用既有暖白、朱砂红与细线体系，不引入第三方品牌图标。

任务与内容行的删除入口默认隐藏于行尾操作区；窄桌面保留最小 40×40px 触控区域，删除前使用原生确认对话框并附带对象名称。删除控件不得覆盖行的详情跳转区域。

## 4. API 契约与验收

模型库接口：`GET/POST /api/settings/model-profiles`、`PUT/DELETE /api/settings/model-profiles/{id}`、`POST /api/settings/model-profiles/{id}/test`；通用/转写路由：`GET/PUT /api/settings/model-routing`；转写参数：`GET/PUT /api/settings/transcript-processing`。任务删除：`DELETE /api/jobs/{id}`；内容删除：`DELETE /api/content/{id}`；孤立来源删除：`DELETE /api/sources/{id}`。

验收：新增两个自定义模型后，可分别选为主/备用；已被引用模型无法删除；主模型连接失败时视频笔记记录实际备用模型并写入审计；没有主模型时任务明确需配置。终态任务和内容均可删除，运行中任务返回可理解的冲突提示，删除后刷新不再出现且相关审计日志可查询。
