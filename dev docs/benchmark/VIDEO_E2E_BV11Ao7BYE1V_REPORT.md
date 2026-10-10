# BV11Ao7BYE1V 真实视频验收

采样：2026-10-10 17:31 北京时间。[原视频](https://www.bilibili.com/video/BV11Ao7BYE1V/)《五一到底哪里人少景色好》，479 秒。用户明确提供该 URL 用于真实测试；本轮独立 Job `job_64e7b17ff08a4c838cd9a9292760ff84`，保存模型/ASR 默认及历史记录未改写，未确认 POI。

**结果：PARTIAL_SUCCESS，全部处理步骤完成，6 个地点待人工处理。** 当前笔记 `note_dd2d238c6ec74bddb73a0e7616711456`，版本 `ntv_b9b5d931625c41caad4fd01124d731e7`（v2）；前次取消流程保留 v1 和失败/修复审计，不伪装为首次无损成功。

| 验收项 | 结果 | 证据 |
| --- | --- | --- |
| 输入与转写 | PASS（流程） | BV/CID=BV11Ao7BYE1V/37783145219，479000ms；AI 自动字幕因 PLATFORM_SUBTITLE_UNVERIFIED 被拒绝，实际 Qwen3-ASR-0.6B/MLX0.4.4 识别50段，12段校对/38段保留；音频词准率未人工评分 |
| 时轴/身份 | PASS | 0–477871ms，Snapshot与规范Source/共享Asset一致；当前实体/Claim/Note/Mention引用均属于当前转写，未串视频 |
| Ground Map Evidence | PASS（已接受项） | 实体17/17、Claim33/33、章节quote16/16通过规范化空白后的逐字校验；这证明依据链接，不证明音频识别/现实事实正确 |
| Note/截图 | PASS（生成与显示） | v2为当前版本，14章节、12张READY截图；PC1440×1000/390×844无溢出/相关控制台错误，18条本视频来源链接，截图弹层打开/关闭通过；源站实际播放跳时未另行验收 |
| POI/Review | PARTIAL | CONFIRMED=0，REVIEW=1、UNRESOLVED=5、AREA_RESOLVED=5、SKIPPED=6；没有人工确认动作，不将6个待处理项直接算成6个错误 |
| 调用/预算 | PASS（数量边界） | 全任务10次实际核心尝试，低于12；无模型fallback、无缓存命中。计费/思考Token未知；字符估算输入15957、可见输出27533及1次输出未知，不能当账单或实测收益 |
| 异常/恢复 | PASS（保留证据） | 首次Ground Map完整对象后多出 ]}，旧状态保留INVALID；模型JSON重试曾被Profile1绕过Stage0。停止任务后lease/Mux请求归零；补修43f42ff并无迁移加载后，仅续跑GENERATE_AI_NOTE，上游8步骤REUSED，未再跑ASR/校对/Ground Map |
| 历史保护 | PASS | 与测试前逻辑备份逐字段比较，原有Jobs/AINote/AINoteVersion/Segment/Transcript均未变化；模型配置未改，0025、integrity=ok、FK=0 |

补修：Stage retry_count同时约束HTTP与JSON模型重试，0禁止两类重发；只在完整对象可解析且剩余仅1–2个闭合括号时记录extra_closing_delimiters并修复，Schema/ID/Evidence全部重验，quote不变，不丢弃第二个文档。离线回放旧失败输出可恢复结构，但2个实体/5条Claim证据仍不合格而被拒；未将该离线结果写入生产或回填历史。输出估算现在依据原始响应content_length，避免短ID解码后的canonical字节膨胀。

验证与部署：后端322/前端19、Ruff/ESLint/TypeScript/Vite通过；43f42ff前已确认active/lease/Mux active=0，备份 `data/backups/app-pre-retry-fix-20261010-165737.db` 验证完整性/FK后经manage.py重载，API/Worker/页面/新心跳READY（Worker94467）。仅源代码补修时重载，验收文档更新不再次重载。

详细脱敏统计：[机器记录](VIDEO_E2E_BV11Ao7BYE1V.json)。本机原始阶段数据仍在SQLite/受控data目录，未提交字幕、Prompt、Cookie、密钥或模型正文。人工字幕、真实长视频、真实Ollama退出、全路由/缓存/强制生成矩阵与实际Token A/B仍开放；不宣称完整Production Proven，不改变模型/ASR Benchmark毕业门禁。

2026-10-10 后续只读归因：5个UNRESOLVED全部保存`CUQPS_HAS_EXCEEDED_THE_LIMIT`，1个REVIEW为`SCORE_BELOW_THRESHOLD`/`GEO_CONTEXT_MISSING`；不应把前5项计算成POI识别错误。高德[官方错误码](https://developer.amap.com/api/web-service/tools/info)说明10021为账号接口QPS超限。Provider已补入API/Worker跨进程统一1.1秒间隔、QPS/HTTP429后5秒冷却且不重试、按Key哈希隔离缓存及不含请求URL的HTTP错误。两个独立进程/不同Key的Mock请求间隔与冷却回归通过；实际账号配额和外部应用流量未验证，未重跑真实查询或改旧候选。供人审的6项地点与12段原始/校对转写、时间码清单保存在本机忽略目录 `data/benchmarks/video-bv11ao7bye1v-20261010-162544/HUMAN_REVIEW.md`，不提交转写原文，不自动确认POI。

历史输出估算保留修复前口径（部分曾按解码后的canonical字符计算），不回填；上述合计估算不能用于新旧Token收益对照。当前规范Source/共享Asset被复用，Capture临时Source按既有去重规则归并；BV/CID及当前Snapshot已核对，原有任务/笔记/转写行保持不变。人工字幕路径、15–30分钟长视频、源站实际播放跳时和真实人审精度均未外推。

QPS补修部署（2026-10-10 22:29北京时间）：`9fdf3fe`无迁移重载，API35459/Worker35471及页面/新心跳READY；0025、integrity=ok、FK0、active/lease0。重载前备份 `data/backups/app-pre-amap-qps-20261010-222813.db` 与旧Provider源码 `data/backups/source-pre-amap-qps-20261010-222813.tar.gz`；Job/Note/版本/地点候选/Segment/Transcript及997条外部调用审计逐字段hash不变，模型设置不变。本次后端326、前端19、目标11及HTTP脱敏补测5通过；无新前端行为，不重复Browser，不重跑真实高德或新增模型调用。
