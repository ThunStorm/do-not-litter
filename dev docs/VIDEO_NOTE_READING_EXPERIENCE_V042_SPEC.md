# Video Note Reading Experience v0.4.2

> 状态：第一阶段已实施；2026-08-24 批注返工已冻结、待实施
> 更新日期：2026-08-24
> 适用页面：`/video-notes/:noteId`
> 现场样本：`note_221cd61e9600493cb3f32e062e1ad013`
> 标注设计：`design/ui/v0.4.4/video-note-detail-pc-annotated.png`、`video-note-detail-mobile-annotated.png`

---

# 1. 返工目标

当前页面已经具备视频元数据、摘要、时间线章节、截图、地点候选、完整转写预览与 TXT 导出，但信息顺序和内容语义仍不符合“先定位、再阅读、随文看图、需要时核对原文”的阅读目标。

本次返工固定解决：

- 地点候选和完整转写入口移到文章最底部，作为集中回查区；
- 所有时间码可以跳到对应时间线段落；
- 目录展示各段主旨，不输出泛化套话；
- 页面正文使用 AI 校对后的提纲与详述，不直接铺转录原文；
- 转写内容在进入总结前执行 AI 校对，保留原始版本供审计；
- 截图嵌入对应章节，不再作为割裂的独立图库；
- 截图可点击放大、切换并关闭；
- TXT 导出使用项目统一按钮视觉。

本文件不授权直接实施。实现前仍需遵守 `REGRESSION_AND_CHANGE_GUARD.md`。

---

# 2. 页面信息顺序

除返回栏和视频 Hero 外，页面顺序固定为：

```text
Video Hero：封面、标题、作者、时长、来源
↓
AI 摘要
↓
主旨目录
↓
按时间线详述（随文嵌入截图）
↓
Bottom Evidence Zone
  ├─ 地点候选
  └─ 完整转写入口/预览
↓
来源、冲突、生成版本与审计信息
```

## 2.1 Video Hero 封面

Hero 有 READY CoverAsset 时展示真实封面；封面缺失、失败或未下载时不显示场记板/图标占位，封面区域为空并收起，标题/来源内容自然占据可用宽度。不得用视频截图冒充平台封面。

## 2.2 Bottom Evidence Zone

地点候选和完整转写必须位于文章正文最底部，在所有时间线详述之后、来源/版本审计之前。它们是回查工具，不抢占首屏阅读顺序。

PC：双列布局，地点候选在左，完整转写在右；两卡顶部对齐。Mobile：按“地点候选 → 完整转写”纵向排列，不横向挤压。

地点候选显示：

- canonical/raw 名称；
- 类型；
- POI 状态；
- 一句特色简介；
- 来源时间码；
- 点击时间码跳转到对应正文；
- Confirmed 地点可进入 Place Detail。

完整转写卡显示：

- 总段数；
- AI 校对状态与模型；
- 保留截止日期；
- 前 8 段校对稿预览；
- “展开更多”和“导出完整转写”；
- 原始转写只在证据/校对差异入口中查看，不作为默认阅读正文。

---

# 3. Transcript 双版本与 AI 校对

## 3.1 数据原则

每个时间码 Segment 同时保留：

```text
raw_text
corrected_text
start_ms / end_ms
correction_status
correction_confidence
correction_reason
correction_provider / model / prompt_version
```

`raw_text` 是 ASR/平台字幕原文，永久只读直到保留期清理；`corrected_text` 是默认展示、总结和导出的校对稿。AI 校对不得覆盖 raw，也不得改变时间范围和 Segment ID。

## 3.2 校对目标

AI 校对处理：

- 口齿不清、口音造成的同音字；
- ASR 断句与重复词；
- 视频标题、作者、地名、菜名和专有名词；
- 明显语法残缺和无意义填充词；
- 数字、计量单位和常见旅行表达。

校对不得：

- 增加原文没有的事实；
- 改写作者立场；
- 猜测无法确认的地名；
- 把城市、景区、寺庙等候选擅自合并；
- 删除影响 Evidence 的否定、价格和提醒。

不确定内容使用 `［待确认：…］` 或低置信标记；地名在高德确认后再写 canonical name。

## 3.3 Pipeline

```text
NORMALIZE_TRANSCRIPT
→ CORRECT_TRANSCRIPT
→ VALIDATE_CORRECTION
→ GENERATE_AI_NOTE
```

校对按固定 Segment 块执行，每个输出必须引用原 Segment ID。服务端校验 Segment 覆盖率、顺序、时间范围和文本非空；不得接受缺段、乱序或新增 ID。

优先使用配置的主模型，失败时使用备用模型。全部模型不可用时，Transcript 保留 `UNCORRECTED`，最终 AI Note 不得伪装为完整完成；任务进入 `NEEDS_USER` 或明确的 `PARTIAL_SUCCESS`，页面显示“转写尚未校对”。

---

# 4. 摘要、目录与正文语义

## 4.1 摘要

摘要只回答：视频讲什么、核心结论、主要地点/体验、最值得注意什么。建议 120–300 中文字，不直接拼接 Transcript。

## 4.2 主旨目录

目录由服务端基于校对稿和时间线章节生成。每项包含：

```text
start_ms
heading
thesis
target_section_id
```

规则：

- `heading` 是明确主题，例如“避开国庆人流的筛选方法”；
- `thesis` 用 20–50 字概括本段主旨；
- 禁止“本段介绍了一些内容”“作者继续讲解”等无信息句；
- 目录按时间递增；
- 最多两级；
- 点击整行或时间码跳转对应正文。

目录视觉必须使用产品主体设计语言，而不是表格：暖白纸面、不使用硬边框网格；标题使用现有衬线标题体系，时间码使用朱砂红小号等宽数字，heading 为主要文字，thesis 使用较浅正文色；行间用细分隔线和留白组织。hover/focus 使用轻暖底色，当前 Section 使用左侧短朱砂标记和文字状态，不能只靠颜色。

## 4.3 按时间线详述

页面“全文/正文”统一改称“按时间线详述”。它不是 Transcript 原文，而是基于完整 AI 校对稿生成的提纲挈领内容。

每个 Section 固定包含：

- 时间范围和可点击起始时间码；
- 主旨标题；
- 1 段结论性概述；
- 2–6 条关键要点；
- 相关地点/菜品/注意事项；
- 嵌入的关键截图；
- “查看对应校对稿”和“打开原片”两个不同动作。

Section 必须覆盖完整 Transcript，不因摘要长度限制只处理前 12000 字符。禁止在正文中直接连续铺满原始转录句子。

---

# 5. 时间码跳转规则

页面内所有时间码默认执行本地段落跳转：

- 地点候选时间码 → 包含该 PlaceMention 的时间线 Section；
- 完整转写 Segment 时间码 → 最近的 Section，并定位/展开对应校对稿；
- 目录时间码 → 对应 Section；
- 截图时间码 → 截图所在 Section；
- Section 时间码 → 当前 Section 顶部。

跳转后：

- 使用稳定锚点 `#section-<id>` 或 `#t=<milliseconds>`；
- 将目标滚动到固定 Header 下方；
- 目标短暂高亮 2 秒；
- 将标题容器设为可聚焦并移动键盘焦点；
- 浏览器前进/后退恢复锚点；
- “打开原片”必须是独立按钮，不与页面内跳转混用。

---

# 6. 截图随文排版

独立“代表截图”宫格不再作为默认主阅读区。截图必须嵌入相关时间线 Section：

- PC 单张图默认作为 220–280px 缩略图放在文字侧面，正文占 60–68%，图片占 32–40%；
- 图片可在章节间左右交替，但同一页面保持可预测节奏，不做机械锯齿；
- 两张图可在侧栏上下堆叠；只有全景或强视觉章节才允许全宽主图；
- Mobile 缩略图放在该段文字之后并占满内容宽度，不产生横向滚动；
- 图片使用 `object-fit: contain`，不得裁掉菜单、店招、景区主体或文字。

截图选择必须对应关键内容：地点外观、菜品、景区特色、路线提示、价格/菜单、关键操作或结论证据。仅因为“章节起始时间”而选取普通 talking head、片头、转场或无信息帧不合格。

每张截图保存并展示：

- 实际时间码；
- 简短内容说明，而不是统一“章节起始时间码代表帧”；
- selection_reason；
- Section/PlaceMention/Segment 关系。

## 6.1 Lightbox

点击截图打开灯箱：

- 完整 `contain` 显示；
- 支持上一张/下一张；
- 显示时间码与说明；
- 点击遮罩、关闭按钮或 Escape 关闭；
- 打开后锁定背景滚动；
- 关闭后焦点回到原截图；
- Mobile 支持触控但不要求复杂手势缩放；
- 图片加载失败显示占位与来源时间码。

---

# 7. 导出按钮规范

“导出完整转写（TXT）”使用项目统一次级按钮：

- 与现有 `.button / .button--outline` 体系一致；
- 统一 36–40px 高度、圆角、边框、图标尺寸和 hover/focus 状态；
- 文案简化为“导出 TXT”，旁边以辅助文字说明“完整 AI 校对稿”；
- 不使用浏览器原生灰色按钮样式；
- 导出进行中、成功、失败均有状态；
- 默认导出 `corrected_text`，文件头记录校对模型和生成时间；原始稿只通过审计型独立导出提供。

---

# 8. API 与 ViewModel

Video Note Detail 增加：

```text
toc[]: section_id / start_ms / heading / thesis
transcript.correction_status
transcript.correction_provider/model
transcript.preview[].raw_text/corrected_text
sections[].summary/bullets/place_refs/screenshots
screenshots[].caption/selection_reason/section_id
```

时间码 API 必须使用稳定 Section ID；历史 Note Version 的锚点不能因重新排序随机变化。

Transcript 导出：

```text
GET /api/video-notes/{note_id}/transcript/export?version=corrected
GET /api/video-notes/{note_id}/transcript/export?version=raw
```

默认页面只调用 corrected；raw 入口放在证据/审计区域。

---

# 9. 响应式与视觉层级

PC 首屏优先看到 Hero、摘要和主旨目录；地点候选与完整转写位于文章底部。Mobile 同样先阅读正文，底部 Transcript 默认只显示 4–8 段并可展开。

视觉层级：

- 地点候选和完整转写是文章底部的工具/证据卡；
- 摘要和目录是阅读导航；
- 时间线详述是主正文；
- 截图是随文内容，不是独立附件区；
- 原始转写和模型审计是次级信息。

所有时间码、截图和按钮需要键盘可达、可见焦点、中文 aria-label；不能只靠朱砂色表达选中或错误。

---

# 10. 验收标准

1. Hero 后依次进入摘要、目录和正文；地点候选与完整转写位于文章最底部；
2. Hero 有封面时使用真实 CoverAsset，缺省时封面区域为空/收起，不显示场记板占位；
3. 地点、Transcript、目录、截图时间码均跳转到正确 Section；
4. 跳转后 Section 高亮、聚焦，前进/后退可恢复；
5. 目录使用暖白、朱砂时间码、衬线标题、细分隔线和明确 focus，不呈现硬边框表格；
6. 目录每项包含具体 heading 和 thesis，无泛化套话；
7. 正文是 AI 校对后的时间线提纲/详述，不连续铺转录原文；
8. 232 段 Transcript 全部拥有 corrected_text 或明确待确认状态；
9. AI 校对不改变 Segment ID、顺序和时间范围；
10. 地名不确定时进入待确认，不由校对模型编造；
11. 关键截图以 220–280px 缩略图放在对应文字侧面，不再只显示独立宫格或默认全宽大图；
12. 截图说明具体，普通 talking head/片头/转场不作为关键帧；
13. 点击截图打开灯箱，Escape/遮罩/关闭按钮均可关闭；
14. Lightbox 使用 contain，PC/Mobile 无裁切和横向溢出；
15. TXT 按钮符合统一视觉，默认导出完整 AI 校对稿；
16. raw Transcript、corrected Transcript、Note 和 Evidence 版本关系可审计；
17. 校对模型不可用时页面不伪装为完整完成。

---

# 11. 实施边界

本轮只完成文档。后续实现应拆为：

1. Transcript Correction 数据/API/Pipeline；
2. TOC thesis 与稳定锚点；
3. Hero CoverAsset/缺省空状态和 Bottom Evidence Zone 重排；
4. 时间码页面内跳转；
5. Section 结构化正文；
6. 侧排缩略图、关键帧重新选取和 Lightbox；
7. 导出按钮与 corrected/raw 导出；
8. PC/Mobile、键盘和真实样本验收。
