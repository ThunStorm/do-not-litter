# S 现有来源离线核对（2026-11-13）

基于HEAD e9c5099及含U/Q/R/P等在途修改的工作树，业务NO_CHANGE；本包不部署、重启、真实读取平台、下载媒体、ASR/LLM、改历史或提交推送。S1/S2完成现有材料定点核对，真实来源矩阵保持LIVE_NOT_RUN/BLOCKED_SOURCE；S3暂缓，未开启三点抽样研究。

|来源/输入|既有离线证据|结论和缺口|
|---|---|---|
|Bilibili标准/短链/分享/分P/播放器|test_bilibili_links：ID、页号、大小写、重定向上限、逐跳Host、网络错与敏感查询不泄漏|规则通过，不代表平台实时稳定|
|主页/非法Host/非标准端口|test_bilibili_links、test_url_policy|拒绝或不当视频处理；不联网|
|人工/自动/空字幕、非单调/超长轴|test_video_notes字幕质量/信任门禁|自动字幕保持非权威并走既有ASR，未执行真实ASR|
|Asset/Transcript/Snapshot不一致|_trusted_transcript_or_raise校验asset、source、snapshot与Segment归属；已有可信转写回归|规则核对，不以标题相似认同源|
|local|本地投递创建Worker任务、扩展名/文件存在性边界|无公开时间跳转，不假造平台字幕|
|YouTube|test_url_policy时间链接/VTT/Host、test_video_notes创建既有TRAVEL任务|仅离线接口能力；元数据/字幕/媒体/转录/笔记真实成功率均N/A|
|取消/重复提交|已有取消和canonical Asset/Source复用回归|无真实取消或后台进程退出实测|
|登录/删除/429、下载失败|现有异常码及Job/NeedsUser分流只读检查|本次未取得独立各平台五档配对样本，不能报完整矩阵毕业|

目标44项通过，JUnit位于`data/benchmarks/source-s-20261113/target.xml`，日志同目录；离线守卫下业务联网尝试0（network.log无记录），没有新增外部请求。五档成功率的分母为真实可访问且有相应权限的样本，本轮每档真实n=0，均N/A，不能拿44项混合规则测试填平台成功率。Q遗留厦门餐饮、贵州完整视频、独立快速口播保留集和原请求链仍未取得，不把线索认定为错源。

停止条件：无新增已复现来源缺陷，不改已冻结P0、不追加抓取或模型阶段。下一包按用户追加指令执行K；X用户明确暂不启动。
