# 视频 Pipeline 契约索引

> 2026-09-03 按主题拆分；原章节编号保留。只选与本任务有关的一篇，再按标题定位，不要求连读。正文中的规划/旧状态不证明当前实现；先看 [当前状态](../IMPLEMENTATION_STATUS.md) 与相关 [冻结约束](../REGRESSION_AND_CHANGE_GUARD.md)。

| 任务主题 | 分篇 | 原章节 |
| --- | --- | --- |
| 业务范围与上游复用 | [01-scope-upstream.md](01-scope-upstream.md) | 1–3 |
| 输入、登录、字幕与转写 | [02-input-transcript.md](02-input-transcript.md) | 4–4.7 |
| 笔记、地点、截图与物化 | [03-generation-materialization.md](03-generation-materialization.md) | 4.8–4.16 |
| Job、数据身份与 API | [04-jobs-data-api.md](04-jobs-data-api.md) | 5–7 |
| 视图、地图、安全与验收 | [05-views-safety-acceptance.md](05-views-safety-acceptance.md) | 8–12 |

## 使用边界

- 最新的阅读/列表/删除/Replay 约束分别见 video/VIDEO_NOTE_READING_EXPERIENCE_V042_SPEC.md、video/VIDEO_NOTE_LIST_V043_SPEC.md、video/VIDEO_NOTE_DELETE_V044_SPEC.md、jobs/PIPELINE_STEP_REPLAY_V044_SPEC.md；按任务选读，不重复加载全部。
- 登录/字幕修复已更新在输入分篇，所有状态结论统一读 IMPLEMENTATION_STATUS.md；旧版范围章的“待实施”只作历史说明。
- 代码定位见 [短实施指南](VIDEO_AI_NOTE_IMPLEMENTATION_GUIDE.md)，旧工作包不再是必读项。
- 上游参考：[BiliNote](https://github.com/JefferyHcool/BiliNote)，原审阅基线 f58e6182c41889873f9df98e4988e479fe9bf14f（2026-08-11）；授权见仓库 THIRD_PARTY_NOTICES.md。
