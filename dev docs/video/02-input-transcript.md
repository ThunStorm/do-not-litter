# 输入、登录、字幕与转写

> 来源：video/VIDEO_AI_NOTE_PIPELINE.md，原章节 4–4.7（正文保留，2026-09-03 分篇）。返回 [主题索引](VIDEO_AI_NOTE_PIPELINE.md)。本篇是契约/规划，不是已实施清单；当前结论见 [实施状态](../IMPLEMENTATION_STATUS.md)，安全与回归见 [冻结清单](../REGRESSION_AND_CHANGE_GUARD.md)。裸文档路径均以 dev docs/ 为基准。只读取命中章节及其必要约束。

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

实现方法参考 `lanyeeee/bilibili-video-downloader` 的 CoverTask：从 `pic/cover` 获取 URL，GET 原图，根据 Content-Type 识别扩展名并写入本地；至简继续使用自己的 httpx、SSRF、缓存和 Job 体系。封面失败记录 `COVER_UNAVAILABLE`，显示占位但不阻塞 Note。完整契约见 `video/VIDEO_NOTE_LIST_V043_SPEC.md`。

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

校对输出必须覆盖全部 Segment，顺序和时间范围与输入一致；缺段、乱序、新增 ID 或空文本均拒绝。无法确认的地名保留待确认标记，再由高德 POI 流程校正。默认 Note、目录、页面预览和 TXT 导出使用 corrected_text；raw_text 只在证据审计中查看。完整阅读与校对规范见 `video/VIDEO_NOTE_READING_EXPERIENCE_V042_SPEC.md`。

Whisper.cpp `-oj` JSON 的 `offsets.from/to` 已经是毫秒，适配器必须直接使用，不得再乘以 10。归一化后必须校验 `max(segment.end_ms)` 与 `VideoAsset.duration_ms`：允许片尾静音和平台元数据的小幅误差，但超过视频时长 2 倍必须中止后续 Note/截图物化并记录 `TRANSCRIPT_TIMELINE_INVALID`。已受影响的历史 Transcript 不原地篡改；当末段时间与视频时长比值约为 10 时，从现有 Segment 生成修正后的新 Transcript Version，再基于新版本重建 Note Version 与截图。
