# Video AI Note Pipeline

> 状态：v0.4.4 需求与架构冻结候选稿
> 更新日期：2026-08-24
> MVP 平台：Bilibili 视频链接（含 `b23.tv`、BV 链接与分 P）
> 参考实现：[JefferyHcool/BiliNote](https://github.com/JefferyHcool/BiliNote)，审阅基线 `f58e6182c41889873f9df98e4988e479fe9bf14f`（2026-08-11）

后续实现 Agent 必须同时阅读 `VIDEO_AI_NOTE_IMPLEMENTATION_GUIDE.md`；该文件将本设计映射到当前代码、迁移、目标文件、Work Package 和验证命令。

---

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

## 2.0 当前状态说明

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

# 4. 端到端处理流程

```text
CAPTURE
↓
NORMALIZE_CAPTURE_INPUT
↓
VALIDATE_AND_CANONICALIZE_URL
↓
FETCH_VIDEO_METADATA
↓
FETCH_COVER
↓
FETCH_PLATFORM_SUBTITLE
├─ 成功 → NORMALIZE_TRANSCRIPT
└─ 失败 → DOWNLOAD_AUDIO → ASR → NORMALIZE_TRANSCRIPT
↓
CORRECT_TRANSCRIPT
↓
GENERATE_AI_NOTE
↓
EXTRACT_TRAVEL_FACTS
↓
RESOLVE_POI
↓
BUILD_PLACE_NOTES
↓
PLAN_SCREENSHOTS
↓
DOWNLOAD_VIDEO_FOR_FRAMES
↓
EXTRACT_SCREENSHOTS
↓
MATERIALIZE_VIEWS
↓
CLEAN_CACHE
```

每个箭头都是可持久化 `JobStep`，不得只在内存中推进。每一步保存输入哈希、输出引用、实现版本、开始/完成时间和错误码。

## 4.1 CAPTURE

输入可以是纯视频 URL，也可以是包含标题、来源说明、“复制打开”等文字的完整分享文案。Capture API：

- 先提取并选择唯一内容 URL；
- 创建 `ContentItem`、`Source` 和持久 `Job`；
- 提取出的原始 URL 原样保留；
- 分享文案中的标题和其他文字不进入 Resolver/Classifier/LLM；
- 返回 `202 Accepted`、`content_id` 和 `job_id`；
- 不在 HTTP 请求中访问 Bilibili、下载音频、运行 ASR 或调用 LLM。

相同 canonical 视频重复提交时允许生成新的 Note Version，但复用有效的 Source Snapshot、Transcript 和媒体缓存。幂等键至少包含：

```text
platform + external_video_id + part_number + source_revision
```

## 4.1.1 NORMALIZE_CAPTURE_INPUT

输入分类：

```text
URL_ONLY
SHARE_TEXT_WITH_URL
TEXT_ONLY
MULTIPLE_URLS
```

处理规则：

1. 在不修改 URL 内部字符的前提下处理 Unicode 空白、零宽字符和换行；
2. 提取 `http/https` URL、Markdown `[标题](URL)`、`<URL>` 和已知平台无 scheme 链接；
3. 去除 URL 外侧引号、括号及末尾中文/英文标点，保留合法 query、fragment 和百分号编码；
4. canonicalize 后去重；
5. 一个候选直接选择；多个候选但只有一个命中专用 Resolver 时选择该候选；多个不同内容链接仍然存在时返回 `CAPTURE_MULTIPLE_URLS`；
6. 选中 URL 后，后续 payload 的 `text` 必须为空，不能把分享标题当正文；
7. 无 URL 时才按 `TEXT_ONLY` 进入直接文本路径。

示例：

```text
“厦门这家店太绝了！ https://b23.tv/abc123 复制打开哔哩哔哩”
→ SHARE_TEXT_WITH_URL
→ selected_url = https://b23.tv/abc123
→ 其余文字不进入视频处理
```

为最小化无关内容保留，数据库默认只记录 `input_kind / selected_url / candidate_count / discarded_text_length / raw_input_hash`，不保存被丢弃分享文案全文。日志不得记录完整原始粘贴内容。

## 4.2 VALIDATE_AND_CANONICALIZE_URL

MVP 接受：

- `https://www.bilibili.com/video/BV...`
- 带 query 的 BV 链接；
- `https://b23.tv/...`
- `?p=N` 分 P 链接。

输出：

```text
platform = bilibili
canonical_url
external_video_id = BV...
part_number
```

短链只允许跟随有限次数的 HTTPS 重定向。最终 host 必须仍在平台 allowlist；拒绝本地地址、内网地址和非 HTTP(S) Scheme，避免 SSRF。

无法识别的链接返回稳定错误 `VIDEO_URL_UNSUPPORTED`；短链失效为 `VIDEO_SHORT_URL_EXPIRED`。

## 4.3 FETCH_VIDEO_METADATA

优先通过平台接口或 `yt-dlp` 的 metadata-only 模式获取：

- title；
- author / uploader；
- description；
- cover URL；
- duration；
- published_at；
- tags；
- BV ID、CID、分 P 标题和分 P 序号；
- 可用字幕轨；
- 原始 metadata 哈希。

元数据保存为 Source Snapshot。元数据与 Transcript 共同作为 AI Note 输入。音频下载和截图视频下载分开规划：字幕命中时仍可为了截图下载受限画质的视频流，但不得因此重复下载音频或启用全视频多模态理解。

## 4.3.1 FETCH_COVER

VideoAsset 的平台 `cover_url` 在元数据完成后进入独立封面步骤：HTTPS 规范化、Bilibili 图片 CDN allowlist、状态/MIME/文件头/尺寸/字节限制校验、SHA-256 去重、本地原图存储和 672×378 WebP 列表衍生图。列表只使用本地 Cover API，不长期热链远程 CDN。

实现方法参考 `lanyeeee/bilibili-video-downloader` 的 CoverTask：从 `pic/cover` 获取 URL，GET 原图，根据 Content-Type 识别扩展名并写入本地；至简继续使用自己的 httpx、SSRF、缓存和 Job 体系。封面失败记录 `COVER_UNAVAILABLE`，显示占位但不阻塞 Note。完整契约见 `VIDEO_NOTE_LIST_V043_SPEC.md`。

## 4.4 FETCH_PLATFORM_SUBTITLE

字幕优先级固定为：

1. 客户端在用户登录态下合法取得并传入的字幕；
2. Bilibili player API 人工中文字幕；
3. Bilibili player API AI 中文字幕；
4. 其他中文轨；
5. `yt-dlp` 可获得的非弹幕字幕；
6. 没有可用字幕时进入音频下载与 ASR。

Bilibili 路径：

```text
BV ID + p
→ /x/web-interface/view 获取对应 CID
→ /x/player/wbi/v2 获取字幕轨
→ 选择字幕轨
→ 获取 subtitle_url JSON
→ Transcript Segment
```

AI 字幕可能要求有效 `SESSDATA`。用户在设置页或任务恢复卡内使用 Bilibili App 扫描站内二维码；后端通过 Passport API 轮询登录结果，以 `/x/web-interface/nav` 验证账号后只将 Cookie 写入 Secret Store/Keychain，不提供开发者工具复制粘贴入口，也不在 API、SQLite 或日志中回显凭据。

平台返回的 `subtitle_url` 必须经过用途级 HTTPS Host Policy：平台 API 使用精确域名，字幕和封面 CDN 使用各自受控的官方子域后缀；后缀匹配必须以完整 DNS 标签为边界，拒绝 HTTP、userinfo、非标准端口、`evilhdslb.com` 和 `hdslb.com.evil.example` 等绕过。新增平台资源类型时扩展对应策略，不在下载函数中散落一次性 hostname 判断。

字幕选择按人工中文、AI 中文（包括 `ai-zh` 等平台变体）、其他语言排序。单条字幕发生 CDN、网络、空内容或格式错误时尝试下一轨；全部不可用时进入音频下载与 ASR fallback。只有明确的登录失效继续进入 `NEEDS_USER`，不得把普通单轨失败升级成整个任务失败。

## 4.5 DOWNLOAD_AUDIO

仅在没有可用字幕时下载音频。使用 `yt-dlp` 取得 best available audio，并由 FFmpeg 转为 ASR 所需格式。约束：

- `noplaylist = true`；
- 本音频步骤不下载完整视频；截图所需的受限画质视频由后续独立步骤处理；
- 限制单任务时长、文件大小、重定向和下载速率；
- 下载到 `data/cache/video/<job_id>/`，不得写永久 Source 目录；
- 校验实际 MIME、容器和 FFprobe 元数据；
- 保存内容哈希、字节数和缓存过期时间；
- 需要 Cookie、验证码、会员或其他权限时进入 `NEEDS_USER`，不绕过限制。

`VIDEO_LOGIN_REQUIRED` 必须停止当前及后续步骤、释放 Worker lease，并在任务页展示站内扫码登录。登录成功后，音频下载可从 `DOWNLOAD_AUDIO` 继续；截图下载可从原步骤继续，或由用户明确选择跳过非核心截图。核心音频/Transcript 步骤不可伪跳过。

错误码至少包括：

- `VIDEO_LOGIN_REQUIRED`
- `VIDEO_ACCESS_DENIED`
- `VIDEO_DOWNLOAD_FAILED`
- `VIDEO_TOO_LARGE`
- `VIDEO_TOO_LONG`
- `VIDEO_PLATFORM_RATE_LIMITED`

## 4.6 ASR

字幕不存在时：

```text
下载音频
→ FFmpeg 16 kHz / mono / PCM
→ ASRProvider
→ timestamp segments
```

默认继续使用至简的 `WhisperCppProvider`；未来可增加 Faster Whisper 或云 ASR。ASR 输出必须包含语言、完整文本、分段开始/结束时间、置信度（若 Provider 提供）、Provider 和模型版本。

ASR 与本地 LLM 不默认并行争用 GPU。模型未安装、损坏或不就绪时，任务在排队前或 ASR Step 前进入 `NEEDS_USER`，前端展示明确修复动作。

## 4.7 NORMALIZE_TRANSCRIPT

字幕和 ASR 都归一为同一模型：

```json
{
  "language": "zh-CN",
  "source_kind": "PLATFORM_SUBTITLE",
  "segments": [
    {"start_ms": 192480, "end_ms": 207120, "text": "……"}
  ]
}
```

规则：

- 时间按毫秒存储；
- Segment 顺序稳定；
- 空段删除，相邻重复段去重；
- 不为了“好看”改写原字幕；
- 原始字幕/ASR 响应以哈希和可选 raw snapshot 保留；
- 后续事实 Evidence 必须指向 Transcript Segment，而不是只指向 AI 笔记。

## 4.7.1 CORRECT_TRANSCRIPT

归一化后、生成笔记前必须执行 AI 校对。每个 Segment 保留 `raw_text`，并生成时间码与 ID 不变的 `corrected_text`。校对修正口音/同音字、断句、重复词、标题/作者/地名/菜名和单位，但不得新增事实或改变作者立场。

校对输出必须覆盖全部 Segment，顺序和时间范围与输入一致；缺段、乱序、新增 ID 或空文本均拒绝。无法确认的地名保留待确认标记，再由高德 POI 流程校正。默认 Note、目录、页面预览和 TXT 导出使用 corrected_text；raw_text 只在证据审计中查看。完整阅读与校对规范见 `VIDEO_NOTE_READING_EXPERIENCE_V042_SPEC.md`。

Whisper.cpp `-oj` JSON 的 `offsets.from/to` 已经是毫秒，适配器必须直接使用，不得再乘以 10。归一化后必须校验 `max(segment.end_ms)` 与 `VideoAsset.duration_ms`：允许片尾静音和平台元数据的小幅误差，但超过视频时长 2 倍必须中止后续 Note/截图物化并记录 `TRANSCRIPT_TIMELINE_INVALID`。已受影响的历史 Transcript 不原地篡改；当末段时间与视频时长比值约为 10 时，从现有 Segment 生成修正后的新 Transcript Version，再基于新版本重建 Note Version 与截图。

## 4.8 GENERATE_AI_NOTE

AI 视频笔记是一级业务产物，不再只是地点抽取的中间文本。

默认使用 Settings 中 `VIDEO_NOTE_SUMMARY` 能力绑定的 Provider。当前产品默认绑定已录入的 DeepSeek OpenAI-compatible 配置；API Key 从 Secret Store 读取，模型名由设置提供，不写死在业务代码。

输入：

- 视频标题、作者、简介、标签；
- 视频封面、时长、发布时间和来源页 URL；
- 带时间码 Transcript Segment；
- 笔记模板和 Prompt Version；
- 用户选择的语言/详细程度（未来 UI 可配置，MVP 使用系统默认）。

默认输出 Markdown，并同时保存可解析结构：

```text
标题
来源信息
内容概览
关键结论
按主题组织的章节
旅行/探店地点索引（若有）
注意事项
AI 总结
```

同时生成结构化目录 `toc[]`：`section_id/start_ms/heading/thesis`。heading 必须是本段明确主题，thesis 用一句话概括主旨；禁止“继续介绍”“本段讲了一些内容”等泛化句。页面正文使用校对稿生成的摘要、要点和时间线详述，不直接拼接 Transcript 原文。

### 摘要与时间线完整性契约

视频 AI 笔记必须同时包含两个独立层次：

1. **摘要**：用较短篇幅说明视频主题、核心结论、适用对象和重要提醒，不能代替正文；
2. **按时间线详述**：按真实视频顺序覆盖从首个有效 Segment 到末个有效 Segment 的全部内容，每节展示标题、`start_ms/end_ms` 和足够具体的正文。不能只取前 8 段、只写一个地点或把 overview 重复充当章节。

时间线边界由服务端对完整 Transcript 做连续分块，综合最大 120 秒与字符预算切分；`segment_ids/start_ms/end_ms` 由服务端赋值，模型只为给定分块生成标题和详述，不再要求模型抄写数据库 ID。单块模型失败时，以该块完整转写整理成“转写整理（未总结）”章节并记录 warning，保证有效 Transcript 永远不会物化为 0 个章节。最终摘要从全部时间线章节合并生成，不允许继续使用只截取前 `video_note_chunk_chars` 的单次请求代表完整视频。

理解顺序固定为两阶段：第一阶段先把视频页元数据与完整 Transcript 组织成 Video Understanding，包括总体摘要、主题章节、作者观点和初步地点线索；第二阶段再由独立结构化调用从 Transcript 中生成餐馆/景区/街区等 PlaceMention 与 PlaceBrief。第二阶段可以引用第一阶段的章节结构帮助定位，但最终事实仍必须直接绑定 Transcript Segment。

每个主要章节必须保留一个或多个 `segment_id` 和起始时间码，渲染层可生成原片跳转。AI 笔记中要明确区分作者观点、来源事实和 AI 归纳。

### 长字幕分块

不得把完整长字幕无条件塞入一次请求。流程固定为：

```text
按 Provider 上下文与请求字节预算切块
→ 每块生成局部笔记
→ 保存 checkpoint
→ 层级合并和去重
→ Schema/Markdown 校验
→ 保存最终 Note Version
```

切块边界优先选择自然停顿和主题边界，同时保留时间范围。合并 Prompt 只允许整理、合并和去重，不得补造原文没有的地点或事实。

每个分块 checkpoint 保存服务端确定的 Segment 范围、输入哈希和局部结果；重试只重跑失败分块。最终校验至少确认：章节数大于 0、章节按时间递增、相邻章节不倒序、末节覆盖末个有效 Segment、所有引用 ID 属于当前 Transcript Version。

### 重试与版本

- 429、超时、5xx 使用有限指数退避；
- 配额不足、Key 无效、模型不存在不盲目重试；
- 每次生成保存 provider、model、prompt_version、template_version、input_hash；
- 同一输入和同一配置可以命中缓存；
- 用户重跑产生新 Note Version，旧版本可查看，不静默覆盖。

## 4.9 EXTRACT_TRAVEL_FACTS

地点提取使用 `TRAVEL_PLACE_EXTRACTION` 能力，当前默认也可绑定 DeepSeek，但它是与 AI 笔记生成分开的结构化调用。

事实抽取的权威输入是 Transcript Segment；AI 笔记只能帮助组织上下文，不能成为唯一 Evidence。模型必须返回符合 Schema 的结构化 JSON：

```text
PlaceMention
RestaurantCandidate
DishObservation
PriceObservation
AuthorOpinion
Warning
Ranking
RecommendedSeason
RegionHint
```

地点粒度不得只停留在城市或行政区。MVP 必须区分并尽可能解析：

- `RESTAURANT`：餐馆、咖啡店、小吃店、摊位；
- `SCENIC_AREA`：景区、景点、自然景观；
- `NEIGHBORHOOD`：街区、历史文化街区、社区；
- `PEDESTRIAN_STREET`：步行街、商业街；
- `BUSINESS_DISTRICT`：商圈、综合体；
- `MARKET`：菜市场、夜市、集市；
- `PARK / MUSEUM / TEMPLE / VILLAGE / TOWN`；
- `LANDMARK / ACCOMMODATION / TRANSIT / OTHER`。

每个地点还必须生成 `PlaceBrief`：地点/景区特色、推荐菜品或体验、适合人群、价格与排队信息、注意事项、作者态度和对应 Segment。城市、省份、国家只作为上下文，不因视频提及就默认创建地图 Marker。

每个对象至少包含：

- `raw_name`；
- `suggested_name`；
- `place_type`；
- `city_hint / district_hint / nearby_landmark`；
- `segment_ids[]`；
- `source_quote`；
- `claim_type`；
- `confidence`。
- `brief` 与结构化特色字段。

无有效 `segment_ids` 的事实拒绝入库或进入 Review。地点别名、商场内分店、同名店和跨城市歧义不能由 LLM 擅自合并。

## 4.10 RESOLVE_POI

```text
PlaceMention
→ AMapPOIProvider 候选搜索
→ 名称/别名/拼音或同音候选校正
→ 结合城市、区县、附近地标、类别与地址上下文确定性打分
→ CONFIRMED / REVIEW / UNRESOLVED / REJECTED
→ Place
```

转写名称必须原样保存在 `raw_name`；高德校正后的名称保存为 `canonical_name`，不得覆盖原始 Evidence。高德返回的 POI ID、名称、别名、地址、行政区和 GCJ-02 坐标是地图事实来源。LLM 可以提供搜索词和上下文，不能自行确认经纬度。只有 `CONFIRMED` Place 默认进入主地图；歧义、同名跨城或搜索无结果进入待确认队列。

多个视频提到同一高德 POI 时复用同一 Place，并新增 Mention/Observation，而不是创建重复 Marker。

## 4.11 BUILD_PLACE_NOTES

地点归纳笔记是 Place 的版本化聚合视图，与单个视频 AI 笔记分开。

输入：

- Place 基础信息和 POI 元数据；
- 所有有效 PlaceMention；
- Dish/Price/Opinion/Warning 等 PlaceObservation；
- 来源视频和时间码；
- 用户状态与已验证偏好（可选）。

输出至少包括：

- 地点名称、类型、地址和地图定位；
- “为什么值得看/去”的归纳；
- 视频作者分别怎么评价；
- 推荐菜品、价格、排队、环境、季节和避坑信息；
- 不同来源之间的冲突；
- 来源视频列表与时间码；
- AI 个性化建议，明确标为 `PERSONAL_INFERENCE`；
- 最近生成时间、模型和版本。

地点归纳笔记中的事实必须能展开到 Observation → Claim → Transcript Segment。来源冲突并列展示，不能由后一次生成静默覆盖。

当 Place 新增 Mention、Observation 被修正、POI 被重新确认或 Prompt/Model 改变时，创建新的 Place Note Version。只修改用户的 SAVE/VISITED 状态时不强制重生成事实归纳。

## 4.12 PLAN_SCREENSHOTS

截图是视频笔记必备产物，不再是纯可选格式。截图计划同时使用：

- 视频封面和元数据；
- AI Note 章节的时间范围；
- PlaceMention 与 PlaceBrief 的 Evidence 时间码；
- Transcript 中的主题切换点。

默认目标：每个主要地点 1–3 张，整篇笔记 3–12 张；短视频可低于 3 张，但至少保留封面和一个可用代表帧。计划结果必须保存 `timestamp_ms / segment_id / section_id / place_mention_id / selection_reason / caption`。关键帧必须对应地点外观、菜品、景区特色、路线提示、价格/菜单、关键操作或结论证据；不得仅因为“章节起始”就选取普通 talking head、片头、广告、转场、纯黑帧或重复画面。

默认页面不再使用割裂的独立截图宫格。每张 READY 截图嵌入其对应时间线 Section，支持 contain 灯箱、上一张/下一张、时间码与说明、Escape/遮罩/按钮关闭和焦点恢复。

截图计划不得只依赖模型章节。若章节为空或没有可用 Segment 引用，必须从已校验的 Transcript 时间范围按开场、主题转换和均匀覆盖生成 3–6 个确定性候选；非空视频得到 0 个计划属于 `SCREENSHOT_PLAN_EMPTY`，不能继续下载视频并把 `EXTRACT_SCREENSHOTS` 记为成功。只有 `plans > 0` 才进入下载步骤。

## 4.13 DOWNLOAD_VIDEO_FOR_FRAMES

截图需要本地可读取的视频流。下载策略：

- 优先选择能满足截图清晰度的受限画质 MP4，不默认最高码率；
- 配置最大字节数、最大时长、分辨率上限和超时；
- 只保存到任务缓存目录，不进入永久原始文件目录；
- 已有同一视频/分 P 且内容哈希匹配的缓存可以复用；
- 平台不允许下载、Cookie 缺失或资源超限时，AI Note 继续交付并标记 `PARTIAL_SUCCESS`，UI 明确显示“截图不可用”的原因。

### Bilibili 格式选择契约

截图链路只需要可解码的视频流，不要求下载音频。Bilibili 常见 DASH 结果是 video-only MP4 与 audio-only M4A；不得使用只匹配音视频合一资源的 `best[height<=720][ext=mp4]/best[height<=720]`。该表达式还会把 `720x1280` 竖屏视频按 `height=1280` 排除，已在 `BV1JH826zEKC`、`BV1SNb966Ebs` 和 `BV1qF3t6TENn` 上造成 `Requested format is not available`。

实现时参照 BiliNote 的 `bv*` 视频流优先、Referer、Cookie 与 MP4 输出处理，但保留至简自己的资源边界：优先 `bv*[ext=mp4]`，再回退任意 `bv*`/可用视频；使用 yt-dlp 的 `res:720` 排序表达“优先不超过 720p、无匹配时取最小可用格式”，不要用单一 `height<=720` 代表横竖屏分辨率。请求必须携带 `Referer: https://www.bilibili.com`，需要登录态时复用短生命周期 Netscape Cookie 文件；最终仍执行超时、最大字节数、实际文件存在性和 FFmpeg 可解码检查。若未来需要合并音视频，才启用 `bestvideo+bestaudio` 与 `merge_output_format=mp4`，截图本身不得为无用音轨付出下载和合并成本。

## 4.14 EXTRACT_SCREENSHOTS

FFmpeg 按计划时间码抽帧，并进行确定性质量过滤：

- 清晰度/模糊度阈值；
- 黑帧和过曝/欠曝检测；
- 感知哈希去重；
- 在目标时间码前后小范围搜索最佳帧；
- 输出 WebP/JPEG、尺寸、文件哈希与实际时间码；
- 截图绑定 Note Section、PlaceMention 和 Transcript Segment。

本阶段不要求用视觉模型识别截图内容。截图是来源视频的可追溯辅助证据；若未来启用多模态理解，必须新增独立版本和审计，不能覆盖 Transcript Evidence。

## 4.15 MATERIALIZE_VIEWS

成功物化后至少可查询：

- 视频 AI 笔记；
- 视频页元数据、封面和章节截图；
- 具体主旨目录与稳定 Section 锚点；
- AI 校对稿、校对状态和 raw/corrected 审计关系；
- Transcript；
- 视频中提及的地点列表；
- Place 列表；
- 地图 Marker；
- Place 归纳笔记；
- 任务步骤、错误和外部调用审计。

视频 AI 笔记生成成功但 POI 仍需确认时，任务允许 `PARTIAL_SUCCESS`：笔记立即可读，已确认地点进入地图，歧义地点显示“待确认”。

`ContentItem.structured_json.note_id` 的公开身份必须是 `AINote.id`（`note_*`），不得写入 `AINoteVersion.id`（`ntv_*`）。所有 `/api/video-notes/{note_id}` 子资源均以 `AINote.id` 为规范参数。为保证已生成内容和旧书签可恢复，共享查询入口应在未命中 `AINote.id` 时识别历史 `AINoteVersion.id` 并解析到其父 Note；新写入数据仍必须使用规范 ID，兼容读取不得继续扩散错误身份。

## 4.16 CLEAN_CACHE

- AI Note、时间线章节和截图属于持久结果，不随缓存清理删除；完整 Transcript 文稿固定保留 180 天，按下述保留契约清理；
- 临时 Cookie、Secret 和未登记 scratch 立即清理；可供步骤续跑的音频、视频、分块结果、POI 候选和截图计划登记为 Replay Cache，默认保留 24 小时，到期后由 Worker 清理；
- 任务运行中、失败待重试或被 Note/截图引用的文件不得提前删除；
- 清理失败记录日志但不回滚已完成业务结果；
- 用户删除 Source 时按删除策略处理 Note、Mention、Observation 和 Evidence 引用。

### 完整转写导出与 180 天保留契约

视频 AI 笔记页提供“导出完整转写（TXT）”。导出由服务端按当前 Transcript Version 即时生成 UTF-8 附件，包含标题、来源 URL、转写来源、生成时间，以及所有 Segment 的 `[HH:MM:SS–HH:MM:SS] 正文`；不得只导出页面预览的前 8 段，也不在服务端保存第二份导出文件。

完整 Transcript 文本从创建时起保留 180 天，独立于通用日志保留天数。`Transcript` 保存 `retention_until/purged_at`；Worker 启动时及最多每 24 小时执行一次幂等清理。到期后清空 `Transcript.text`、全部关联 `Segment.text/raw_text/corrected_text` 和 `Evidence.quote`，移除 `metadata_json` 中当前错误保存的全文 fingerprint，仅保留 SHA-256、时间码、版本和审计所需元数据。AI Note、时间线正文、章节时间范围、截图和来源链接继续保留，但页面明确显示“完整转写已按 180 天策略删除”；转写读取与导出接口返回 `410 Gone`。清理事件只记录 Transcript ID、清理时间和数量，不记录原文。

---

# 5. Job 状态与恢复

建议步骤和进度：

| Step | 建议进度 | 可复用缓存 | 可单步重跑 |
|---|---:|---|---|
| NORMALIZE_CAPTURE_INPUT | 2 | selected URL | 是 |
| VALIDATE_LINK | 5 | canonical URL | 是 |
| FETCH_METADATA | 12 | Source Snapshot | 是 |
| FETCH_COVER | 18 | CoverAsset / local derivative | 是 |
| FETCH_SUBTITLE | 22 | raw/normalized subtitle | 是 |
| DOWNLOAD_AUDIO | 32 | media cache | 是 |
| ASR | 48 | Transcript | 是 |
| NORMALIZE_TRANSCRIPT | 60 | normalized Transcript Version | 是 |
| CORRECT_TRANSCRIPT | 62 | corrected Transcript Version | 是 |
| GENERATE_AI_NOTE | 65 | Note chunk/checkpoint | 是 |
| EXTRACT_TRAVEL_FACTS | 76 | typed extraction | 是 |
| RESOLVE_POI | 86 | provider candidates | 是 |
| BUILD_PLACE_NOTES | 90 | Place Note Version | 是 |
| PLAN_SCREENSHOTS | 92 | Screenshot Plan | 是 |
| DOWNLOAD_VIDEO_FOR_FRAMES | 94 | bounded video cache | 是 |
| EXTRACT_SCREENSHOTS | 97 | Screenshot Assets | 是 |
| MATERIALIZE | 99 | View projection | 是 |
| CLEAN_CACHE | 100 | 不适用 | 是 |

有平台字幕时跳过 `DOWNLOAD_AUDIO/ASR`，进度直接推进，但保留 `SKIPPED` Step 记录。Worker 重启后从最后一个已完成且输入哈希一致的 Step 恢复。

失败后的人工续跑不从首步骤开始。Artifact Manifest 有效时，上游 COMPLETED 步骤在新 Attempt 中标记 `REUSED`，从失败步骤开始，后续步骤顺次执行；TTL 到期或输入/版本变化时步骤级续跑不可用，只能完整重跑。完整契约见 `PIPELINE_STEP_REPLAY_V044_SPEC.md`。

最终状态：

- `COMPLETED`：AI 笔记完成，地点处理已完成或视频无地点；
- `PARTIAL_SUCCESS`：AI 笔记可读，但部分地点需确认或部分增强失败；
- `NEEDS_USER`：需要 Cookie、登录、模型配置或 POI 选择；
- `FAILED`：当前无法自动恢复；
- `CANCELLED`：用户取消。

---

# 6. 数据边界

需要新增或补全的核心实体：

```text
VideoAsset
Transcript
TranscriptSegment（复用通用 Segment）
AINote
AINoteVersion
AINoteSection
VideoScreenshot
PlaceMention
PlaceObservation
PlaceNote
PlaceNoteVersion
MapMarkerState
ExternalCallAudit
```

关键关系：

```text
Source 1 ── * Snapshot
Snapshot 1 ── 1 VideoAsset
VideoAsset 1 ── * Transcript
Transcript 1 ── * Segment
ContentItem 1 ── * AINoteVersion
AINoteVersion 1 ── * AINoteSection
AINoteSection 1 ── * VideoScreenshot
Segment 1 ── * Claim/Evidence
Segment 1 ── * PlaceMention
Place 1 ── * PlaceMention
Place 1 ── * PlaceObservation
Place 1 ── * PlaceNoteVersion
Place 1 ── 0..1 MapMarkerState
```

AI Note Markdown 不能代替 Transcript、Typed Claim 或 Evidence；Place Note Markdown 不能代替 PlaceObservation。

---

# 7. API 契约概要

Capture 继续使用统一入口：

```text
POST /api/inbox
GET  /api/inbox/{content_id}
```

视频笔记资源：

```text
GET  /api/video-notes
GET  /api/video-notes/{note_id}
GET  /api/video-notes/{note_id}/transcript
GET  /api/video-notes/{note_id}/places
GET  /api/video-notes/{note_id}/screenshots
POST /api/video-notes/{note_id}/regenerate
```

地点资源：

```text
GET  /api/travel/places
GET  /api/travel/places/{place_id}
GET  /api/travel/places/{place_id}/note
GET  /api/travel/places/{place_id}/sources
GET  /api/travel/map?bbox=&zoom=&place_type=&user_state=&query=
GET  /api/travel/map/bootstrap
POST /api/travel/map/markers
DELETE /api/travel/map/markers/{marker_id}
POST /api/travel/map/markers/{marker_id}/restore
```

所有入口最终使用同一个 `place_id` 和 Place Detail ViewModel。列表和 Marker 不维护第二份地点详情数据。

---

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
