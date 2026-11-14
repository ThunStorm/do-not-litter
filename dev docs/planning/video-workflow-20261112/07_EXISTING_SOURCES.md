# S｜现有来源与字幕可信度

返回[总览](README.md)，遵循[执行契约](09_AGENT_EXECUTION.md)。承接原 06 WP0/WP1 和对应 WP3；只维护已有 Bilibili、YouTube、local。新平台另见 X。

## 阶段

1. **S1 输入矩阵。** 用冻结材料记录标准/短链/分享文案、列表主页、人工/自动/无字幕、错时间轴、身份不匹配、登录/删除/429、媒体失败、取消与重复提交。按平台内容 ID（Bilibili BV/CID 等）追踪 Asset→Transcript→Snapshot/Note；哈希用于内容绑定，不能拿两份不同格式材料哈希相同作为身份要求，也不能只凭标题相似判断同源。
2. **S2 具体失败修复。** 沿现有 adapter/字幕信任门禁修复；自动字幕不得直接提升为权威 Transcript，保留 P0 的受控 ASR 路径与已有人工字幕验证。没有可用媒体/字幕时明确缺失及下一步，不生成空内容伪成功。仅有帖子正文可以按已支持类型保存，不能假装取得视频转写。重定向逐跳、URL/Host 与网络安全沿现有边界，API 内不下载媒体。
3. **S3 可选抽样研究。** 原字幕计划 P1 仍为暂缓研究，三点抽样不是全文一致性证明。只在用户选择该优化后，用已授权本地素材比较错配放行、误拒绝和总 ASR 成本；未授权不跑真实 ASR。记录偏移/局部错配/重复片头等对抗样本；小样本零误放行不构成更改冻结信任门禁的授权。收益不足或无法证明安全则维持 P0，研究可以不启动。

## 验证与交付

正文契约复用[字幕一致性计划](../VIDEO_TRANSCRIPT_ALIGNMENT_OPTIMIZATION_PLAN.md)，新增平台复用[Adapter 计划](../SOCIAL_LINK_ADAPTER_FEASIBILITY_PLAN.md)，不重复编写第三套抓取架构。入口 `resolvers/video/{adapters,bilibili,youtube,local,url_parser}.py`、`services/{video_pipeline,transcript_validation}.py`、`core/url_policy.py`；先定位 `test_bilibili_links.py`、`test_capture_video_benchmark.py` 和相关 pipeline 用例。

分别统计元数据、字幕、媒体、完整转录、笔记五档成功率，分母是具有相应能力/权限的测试输入，受限样本单列；预览成功不计全文成功。`PREVIEW_ONLY` 属完整性，`NEEDS_USER` 属 Job 状态，不新增同名 Job 终态；按现有状态机映射动作。正负样本各有入口身份、原文/哈希和期望降级，保证错误来源不进入已确认笔记；零未授权联网、媒体/模型/ASR 执行。真实平台稳定性必须后续在授权条件下测，不以离线 adapter 测试宣称可用。
