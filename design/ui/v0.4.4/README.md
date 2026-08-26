# v0.4.4 视频阅读、步骤续跑与删除标注稿

> 状态：设计稿与源码已对齐；在线服务、真实 Pipeline、PC/Mobile 和 Lightbox 已验收
> 更新日期：2026-08-24

本目录延续“至简”暖白纸面、墨黑正文、朱砂红强调、衬线标题和细分隔线。图片仅作为信息架构和视觉实施依据，不得直接作为页面背景。

| 文件 | 端/场景 | 关键标注 |
| --- | --- | --- |
| `video-note-detail-pc-annotated.png` | PC 视频笔记详情 | CoverAsset/缺省收起、主体目录、侧排关键缩略图、底部地点/转写、更多菜单删除 |
| `video-note-detail-mobile-annotated.png` | Mobile 视频笔记详情 | 单列正文优先、目录列表、随文缩略图、底部证据区、删除菜单 |
| `pipeline-step-replay-and-delete-pc-annotated.png` | PC ERROR 恢复与删除 | 上游 REUSED、从错误步骤继续、24h TTL/过期完整重跑、删除菜单与保留边界 |

## 最新覆盖关系

- 地点候选与完整转写放文章底部，覆盖 v0.4.2 早期“Hero 后顶部证据区”方案；
- Hero 有 READY CoverAsset 时显示真实封面；缺省时收起封面列，不显示场记板占位；
- 目录使用暖白纸面、朱砂时间码、衬线标题、thesis 和细分隔线，不使用硬网格表格；
- Section 图片使用 220–280px 侧排缩略图，Mobile 放文字下方；点击进入 contain Lightbox；
- ERROR 恢复不是整任务重跑：Artifact 有效时从失败步骤继续，上游 REUSED，当前/下游自动执行；过期后才提供完整重跑；
- 删除视频笔记位于列表/详情更多菜单，保留共享 Source、VideoAsset、CoverAsset、Transcript、Place 和 Evidence。

## 文档映射

- `../../../dev docs/VIDEO_NOTE_READING_EXPERIENCE_V042_SPEC.md`
- `../../../dev docs/PIPELINE_STEP_REPLAY_V044_SPEC.md`
- `../../../dev docs/VIDEO_NOTE_DELETE_V044_SPEC.md`
- `../../../dev docs/VIDEO_AI_NOTE_IMPLEMENTATION_GUIDE.md`

## 图稿注意

图稿中的图片和文本为设计示例。实施必须使用真实 CoverAsset、ScreenshotAsset、Note Section、Replay Options 与 API 状态；不得把图稿内容硬编码为业务数据。
