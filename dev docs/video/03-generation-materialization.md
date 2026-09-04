# 笔记、地点、截图与物化

> 来源：video/VIDEO_AI_NOTE_PIPELINE.md，原章节 4.8–4.16（正文保留，2026-09-03 分篇）。返回 [主题索引](VIDEO_AI_NOTE_PIPELINE.md)。本篇是契约/规划，不是已实施清单；当前结论见 [实施状态](../IMPLEMENTATION_STATUS.md)，安全与回归见 [冻结清单](../REGRESSION_AND_CHANGE_GUARD.md)。裸文档路径均以 dev docs/ 为基准。只读取命中章节及其必要约束。

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
