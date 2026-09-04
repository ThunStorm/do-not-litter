# 视图、地图、安全与验收

> 来源：video/VIDEO_AI_NOTE_PIPELINE.md，原章节 8–12（正文保留，2026-09-03 分篇）。返回 [主题索引](VIDEO_AI_NOTE_PIPELINE.md)。本篇是契约/规划，不是已实施清单；当前结论见 [实施状态](../IMPLEMENTATION_STATUS.md)，安全与回归见 [冻结清单](../REGRESSION_AND_CHANGE_GUARD.md)。裸文档路径均以 dev docs/ 为基准。只读取命中章节及其必要约束。

# 8. 多入口导航规则

地点详情的 canonical route 建议固定为：

```text
/places/:placeId
```

入口包括：

- 视频 AI 笔记中的地点链接；
- 视频笔记的“本片地点”列表；
- 全局旅行地点列表；
- 地图 Marker 预览卡；
- 最近发现、收藏、想去和去过列表。

所有入口进入同一 Place Detail，不允许为“地图地点详情”和“列表地点详情”创建两套页面。入口上下文通过路由 state 或 query 保存：

```text
from = video-note | place-list | map | dashboard
source_note_id
source_segment_id
return_state
```

从地图返回时需要恢复 viewport、筛选和选中 Marker；从视频笔记返回时恢复阅读位置。Place Detail 中点击来源时间码可打开原视频或返回视频笔记对应章节。

## 8.1 中国大陆全境地图

地图不是默认城市页面。首次打开且没有用户历史视野时，以中国大陆全境为初始 viewport；之后恢复用户上次的中心点、zoom、bbox 和筛选。禁止在前端请求或界面文案中硬编码厦门或其他城市。

地图必须支持：

- 连续平移和缩放；
- 根据当前 `bbox + zoom` 请求 Marker；
- 全国尺度聚合，放大后逐步展开；
- 地点名称、别名、行政区和类型搜索；
- 当前视野结果计数和“适配全部结果”；
- 用户定位只作为主动操作，不改变默认全国策略；
- 地图 Provider 不可用时显示配置/诊断入口，不用静态厦门示意图伪装真实地图。

## 8.2 Marker 浮窗与详情

点击 Marker 必须在地图上直接打开浮窗/侧浮层，地图不离场。简略信息至少包含：名称、类型、地址/行政区、1 张代表图、特色摘要、关键菜品/体验、来源数量、用户状态和“查看详情”。点击“查看详情”进入 canonical `/places/:placeId`；返回时恢复原地图视野和浮窗。

PC 使用锚定 Marker 的浮窗或右侧浮层；Mobile 使用不遮挡主要地图操作的底部 Sheet。浮窗不是完整 Place Note，完整来源、冲突和 Evidence 仍在详情页。

## 8.3 用户自定义 Marker

用户可以通过地图长按/点击“添加地点”或搜索结果创建 Marker。创建时：

- 优先用高德搜索/逆地理编码取得规范名称、地址和 GCJ-02 坐标；
- 用户可以填写自定义名称、类型、简介和备注；
- 来源标为 `USER`，与视频自动提取的 `AI_EXTRACTED` 区分；
- 用户直接点选的坐标可以保存，但必须标记 `USER_CONFIRMED`，不能伪装成高德 POI 命中。

删除语义固定为：

- 用户创建的 Marker：软删除，可恢复；关联 Place/审计在保留期内不物理删除；
- 视频/POI 自动生成的 Marker：默认执行“从地图隐藏”，不能删除 Source、Claim、Evidence 或 Place；
- 恢复操作重新显示；
- 只有专门的数据删除流程才能物理删除无引用对象。

Marker 是 Place 的地图投影，不维护第二套地点详情数据。`marker_id` 与 `place_id` 同时返回，浮窗和详情始终以 `place_id` 查询。

---

# 9. 后续 UI 决策门

本文件先冻结产品与后端契约，不在本阶段直接决定页面数量或开始实现。下一阶段必须基于现有页面截图和路由完成 UI 信息架构审查，并回答：

1. 现有 Content Detail 能否承载完整视频 AI 笔记，还是需要独立 Video Note Detail；
2. 现有 Content 列表是否需要“视频笔记”筛选或独立入口；
3. 地点列表采用独立页还是地图内可切换列表视图；两者都必须共享同一 Place 数据；
4. 现有 Place Detail 是否能容纳地点归纳、来源视频、冲突与 Evidence；
5. 手机端长笔记、字幕时间轴、地图预览和返回状态如何组织；
6. 任务详情是否需要显示字幕来源、下载/ASR跳过、DeepSeek 分块和 POI 部分成功。

候选 UI 变化只包括：

- 扩展现有投递页；
- 扩展任务详情步骤；
- 扩展或新增视频 AI 笔记详情；
- 扩展地点列表/地图联动；
- 扩展 Place Detail 为地点归纳笔记；
- 扩展设置中的视频下载/Cookie、ASR 和 DeepSeek 角色配置。
- 地图改为中国大陆全境交互底图，新增 Marker 浮窗、自定义新增/隐藏/删除/恢复；
- 设置新增高德 JS Key、Security Code、Web 服务 Key 和真实连通测试。

必须先生成 PC 与 Mobile UI 图并确认，再进入前端实现；UI 图不得反向改变本文件已经冻结的业务数据和 Evidence 规则。

---

# 10. 安全、隐私与外部服务

- Bilibili Cookie 属于 Secret，不得进入 SQLite 明文字段、日志、导出或前端普通 API；
- DeepSeek API Key 只从 Secret Store 读取；
- 发送给 DeepSeek 的默认内容是视频元数据、字幕 Segment 和普通旅行信息，不发送招聘 Profile；
- 外部调用审计记录 Provider、Model、输入 Segment ID、字节/Token估计、时间、状态和错误码，不记录 API Key；
- 所有远程 URL 必须经过 SSRF 防护和平台 allowlist；
- URL allowlist 使用可复用、用途级的 HTTPS Host Policy；仅允许明确平台域名或完整 DNS 标签边界的官方 CDN 后缀，不使用任意 URL、字符串包含或无边界后缀匹配；
- 下载遵守平台条款与用户合法访问权限；
- 临时媒体不进入普通备份和导出；
- AI 输出必须在 UI 标明模型生成及可能存在错误。
- 高德 Web 服务 Key 保存在 Secret Store；JS Key 可作为普通设置，Security Code 按敏感设置保存并只通过受认证的地图 bootstrap 接口提供。浏览器加载地图后无法把 JS 端凭据视为绝对机密，设置页必须如实提示其客户端可见性与域名白名单要求。
- 视频截图属于来源派生资产，默认本地保存，不在普通导出中自动包含；删除/隐藏 Marker 不删除截图 Evidence。

---

# 11. 验收标准

## 11.1 核心成功路径

给定一个公开、可访问的 Bilibili 旅行视频：

1. 用户只粘贴链接即可获得 `202` 和 Job；
2. 系统正确识别 BV ID 与分 P；
3. 有字幕时不下载音频、不运行 ASR；
4. 无字幕时自动下载音频并生成带时间码 Transcript；
5. DeepSeek 生成可读、结构化、带来源时间码的 AI 笔记；
6. 主要章节和地点拥有清晰、非重复、带时间码的代表性截图；
7. 餐馆、景区、街区等细粒度地点被提取并绑定 Transcript Evidence；
8. 高德完成名称与 POI 校正后，Confirmed 地点显示在列表和地图；
9. 中国大陆全境地图无默认城市，支持平移、缩放、聚合和 bbox 加载；
10. 点击 Marker 在地图浮窗查看简略信息，视频笔记地点链接、列表项和浮窗详情按钮均进入同一个 Place Detail；
11. 用户可以新增、隐藏、删除和恢复自定义 Marker，自动生成 Marker 被删除时只隐藏地图投影；
12. Place Detail 显示地点归纳笔记、来源视频、截图和时间码；
13. 任务重跑可复用 Transcript 和有效截图，不重复下载/ASR；
14. Worker 重启后任务可恢复；
15. 全流程保存 Provider、Model、Prompt、Parser 和上游适配器版本。

## 11.2 异常路径

必须覆盖：

- 短链失效；
- 不支持平台；
- Bilibili 无字幕；
- Cookie 缺失或过期；
- 平台 412/429/访问拒绝；
- 音频超大、下载中断、FFmpeg 失败；
- Whisper 模型未就绪；
- DeepSeek Key 无效、余额不足、超时、429、5xx；
- 长字幕分块中途失败后 checkpoint 恢复；
- POI 无匹配、多匹配和同名跨城市；
- 转写错别字/同音地点通过高德候选校名，无法唯一确认时进入 Review；
- 截图视频不可下载、抽帧失败、黑帧、模糊帧和重复帧；
- 高德 JS Key、Security Code 或 Web 服务 Key 缺失/无效；
- AI 笔记成功但 POI 失败的 `PARTIAL_SUCCESS`；
- 取消任务后的缓存和数据库一致性。

## 11.3 质量门槛

- 不存在无 Segment Evidence 的来源事实；
- 不存在 LLM 生成的地图坐标；
- 同一 POI 不因多视频来源产生重复 Marker；
- 不存在城市级泛化 Mention 挤占细粒度餐馆/景区/街区结果；
- 每张展示截图有实际视频时间码、文件哈希和 Segment/Section/Place 关联；
- 分 P 字幕、元数据和原片跳转指向同一集；
- 旧 Note Version 不被重跑覆盖；
- 列表和地图进入的 Place Detail 数据一致；
- 地图初始状态不包含硬编码城市，Marker 添加/删除/恢复语义符合来源类型；
- CI 使用冻结 Fixture，真实 Bilibili URL 只作为手工验收；
- BiliNote 移植代码保留 MIT 声明与参考 revision。

---

# 12. 实施顺序

v0.4/v0.4.1 基础链路、v0.4.2 第一阶段与 v0.4.3 列表封面已完成。v0.4.4 后续按以下顺序实施：

1. 模型级全 Segment `CORRECT_TRANSCRIPT`、覆盖验证和 fallback；
2. Hero 缺封面空状态、正文优先、底部地点候选/完整转写；
3. 主体设计语言目录、稳定锚点和页面内时间码跳转；
4. 220–280px 侧排关键缩略图、语义重选与 contain Lightbox；
5. Step Artifact Manifest、24h Replay Cache 与 Replay Options；
6. 从错误步骤执行当前/下游，上游 REUSED，过期后完整重跑；
7. 视频笔记列表/详情统一删除和共享数据保留；
8. PC/Mobile 标注设计、键盘、安全和真实样本回归。
