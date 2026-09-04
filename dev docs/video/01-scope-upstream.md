# 业务范围与上游复用

> 来源：video/VIDEO_AI_NOTE_PIPELINE.md，原章节 1–3（正文保留，2026-09-03 分篇）。返回 [主题索引](VIDEO_AI_NOTE_PIPELINE.md)。本篇是契约/规划，不是已实施清单；当前结论见 [实施状态](../IMPLEMENTATION_STATUS.md)，安全与回归见 [冻结清单](../REGRESSION_AND_CHANGE_GUARD.md)。裸文档路径均以 dev docs/ 为基准。只读取命中章节及其必要约束。

# 1. 业务目标

用户只需要粘贴一个视频链接，系统在后台完成视频页信息解析、字幕获取或语音转写、语义理解、AI 笔记生成、代表性截图提取、旅行地点提取、现实 POI 校名和地点归纳笔记生成。本文中的“转义理解”统一指“字幕/转写文本的语义理解”，不是字符转义。处理完成后，用户可以：

- 阅读完整 AI 视频笔记；
- 查看视频标题、作者、封面、时长、简介、标签和来源链接；
- 在笔记章节、餐馆、景区和街区简介中查看与时间码对应的代表性截图；
- 从视频笔记中的地点引用进入地点归纳笔记；
- 从旅行地点列表进入同一地点归纳笔记；
- 点击地图 Marker 预览地点并进入同一地点归纳笔记；
- 从地点归纳笔记返回来源视频笔记及对应时间码；
- 查看每个事实、作者观点和 AI 推断的来源与类型。

产品成功路径固定为：

```text
粘贴视频链接
→ 系统回复“已收下”
→ 后台解析视频页、字幕/ASR 和语义
→ 生成带截图的 AI 笔记
→ 自动提取餐馆、景区、街区等细粒度地点并用高德校名
→ 视频笔记、地点列表和中国大陆全境地图同时可用
```

用户在成功路径中不需要选择平台、下载器、字幕来源、ASR 引擎或 LLM。只有登录态缺失、平台风控、POI 歧义、模型不可用等异常才进入 `NEEDS_USER`。

---

# 2. MVP 范围与非目标

## 2.0 历史状态说明（2026-08-24，不作为当前结论）

v0.4/v0.4.1 基础 Pipeline、内容完整性和全国地图已实现；v0.4.2 第一阶段阅读能力与 v0.4.3 列表封面/CTA 已实施。v0.4.4 最新批注返工（底部证据区、目录视觉、侧排缩略图/Lightbox）、真正步骤级续跑和视频笔记删除仅完成文档/设计，不得描述成已实现。

## 2.1 MVP 必须完成

- 接收 Bilibili 普通链接、BV 链接、`b23.tv` 短链和带 `p=N` 的分 P 链接；
- 解析 canonical URL、BV ID、分 P 序号、CID、标题、作者、封面、时长、发布时间和标签；
- 优先获取平台字幕，无字幕时下载音频并调用 ASR；
- 将字幕/ASR 统一为带时间码的 Transcript Segment；
- 使用已配置的 DeepSeek OpenAI-compatible Provider 生成结构化 Markdown AI 笔记；
- AI 笔记综合视频页元数据与 Transcript，而不是只总结单一文本；
- 对长字幕进行安全分块、分块总结和层级合并；
- 为主要章节和地点选取清晰、非重复、可回溯时间码的代表性截图；
- 从 Transcript 中提取餐馆、景区、街区、步行街、商圈、市场、公园、博物馆等地点及菜品、价格、特色、作者观点、提醒和推荐语；
- 通过高德 POI 服务校正转写名称并把 PlaceMention 解析成现实 Place；
- 为同一 Place 聚合多个来源，生成版本化地点归纳笔记；
- 保留 Source、Transcript、Claim、Evidence、模型和 Prompt 版本；
- 支持 Job 恢复、单步骤重跑、缓存复用和幂等写入；
- 支持从视频笔记、地点列表和地图 Marker 进入同一个 Place Detail。
- 地图覆盖中国大陆全境，无默认城市；支持平移、缩放、聚合、搜索、视野恢复和按当前 bbox 加载；
- 用户可以自定义添加、隐藏、恢复和删除 Marker；地图浮窗直接展示简略信息并可进入详情页。

## 2.2 本阶段不做

- 默认把视频帧发送给多模态模型做全视频视觉理解；
- 下载无上限或原始最高画质视频；截图只下载满足清晰度和大小限制的最低必要视频流；
- 评论区、弹幕和直播内容总结；
- 自动生成或猜测 POI 经纬度；
- 自动规划交通路线或最优行程；
- BiliNote 的 RAG 问答、浏览器插件和桌面 UI；
- 抖音、快手、YouTube 的生产级保证；这些平台保留 Resolver 接口，待 Bilibili 验收后逐个平台启用；
- 批量处理收藏夹、合集或播放列表；
- 绕过付费、权限、验证码、地区限制或平台访问控制。

---

# 3. BiliNote 复用策略

## 3.1 复用原则

BiliNote 作为经过真实使用验证的视频笔记参考实现。至简优先移植、适配或封装其成熟轮子，不重复从零实现平台细节；但业务数据、任务运行时、Evidence、POI 与 UI 仍使用至简自己的架构。

允许复用或适配：

- 视频 URL 校验、短链解析、BV ID 与分 P 参数提取；
- `BilibiliSubtitleFetcher` 的 player API 字幕优先策略；
- Bilibili Cookie 注入、字幕轨优先级与字幕 JSON 解析；
- `yt-dlp` 的元数据、字幕、音频和必要视频下载配置；
- Bilibili WBI/playurl 风控参数兼容经验；
- `TranscriptResult / TranscriptSegment` 的数据语义；
- FFmpeg 音频提取与转码策略；
- Whisper 转写 Provider 的实现经验；
- 长文本 Request Chunker、分块总结、层级合并、重试和 checkpoint 思路；
- Markdown 时间跳转标记和截图后处理逻辑；BiliNote 中的可选开关不改变至简 v0.4 的截图必备要求；
- 模型就绪门禁、代理配置和下载失败诊断经验。

不直接照搬：

- FastAPI `BackgroundTasks` 作为长任务运行时；
- JSON 状态文件作为任务真相源；
- `NoteGenerator` 单体服务和 BiliNote 独立 SQLite 表；
- BiliNote 前端页面、路由和 UI 信息架构；
- BiliNote 的 Provider 配置文件和明文 Secret 处理方式；
- RAG、向量库、问答和多模态能力；
- 与至简 Claim/Evidence/Place 模型冲突的数据结构。

## 3.2 许可证要求

BiliNote 使用 MIT License。若复制或实质性移植其源码，必须：

- 在仓库第三方声明中保留 BiliNote 的版权与 MIT License；
- 在移植文件头或 `THIRD_PARTY_NOTICES` 中标明来源仓库、参考 commit 和修改说明；
- 不删除上游版权声明；
- 对“参考思路”和“直接移植代码”分别记录，便于后续升级与安全审计。

## 3.3 上游隔离

所有移植代码进入受控适配层，例如：

```text
resolvers/video/
  bilibili.py
  url_parser.py
  subtitle.py
providers/media/
  yt_dlp.py
```

Processor、数据库模型和前端不得 import BiliNote 包。上游升级通过适配层吸收，不能让第三方内部类型泄漏到业务层。

---
