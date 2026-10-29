# 当前交接

> 本文件只维护任务续接与带日期的生产快照；源码能力和自动验证的唯一来源为 [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)。

## 任务续接

- 目标：视频最小修复V01–V08（含V07），迁移、发布、目录清理和提交推送。
- 完成：字段证据门禁、≤3字幕轨/VTT、截图首次/Replay一致、路线局部绑定/条件保留；0027固定笔记版本与提取产物。生产Python3.14全量745、前端59、云南46/29与Lint/类型/构建通过；DB副本升级/降级/再升级44表原字段不变。
- 生产：2026-10-28 18:17完成0026→0027，API/Worker/首页/新心跳READY，静态哈希不变；22旧版本关联NULL、不回填。保存点`data/backups/video-minimal-release-20261028-180824`；首次心跳守卫触发源码回退，核对仅运行指标/心跳后重发通过。
- 提交：源码f4dc52b；最终文档提交和推送结果见保存点release-result.json。
- 未完：V09–V12延期，云南独立语义金标和真实视频E2E未验。
- 下一步：人工裁定云南字面差异，冻结语义金标。
- 文件：benchmark/video-minimal-fix-20261028四报告/跟踪表；alembic/versions/0027_note_grounded_map_binding.py。
- 边界：本轮允许0027；真实Provider/视频重跑、历史回填和POI确认仍需另行授权。

## 生产快照（最新采样2026-10-30 01:41，北京时间）

- 2026-10-30 01:41 投递/分类/关联删除发布与真实重跑：PC新增投递，旅行包含VIDEO_NOTE并可单独筛选；删除专属Mention/Insight/时节/区域/截图事实及无其他来源和人工资料的自动地点，共享/个人资料与路线保留，自动汇总刷新；手机分类与来源长链接列宽修复。生产1440/390px导航、真实20条分类、删除确认后取消、无溢出/应用错误通过；实际来源/笔记删除在隔离API与Browser验证。后端全量822、收尾124/11，前端62及Lint/TS/隔离构建通过。两次发布均无迁移（0027）、空闲Job/lease/在途门禁、已验证SQLite备份和完整性/FK、资源哈希通过，发布窗口业务数据不变；最新保存点`data/backups/capture-delete-20261030-013000`，首次`data/backups/capture-delete-20261030-010608`，未回退。当前API/Worker RUNNING、新心跳正常；HTTP index SHA256 `d8f3094346a4aa6b1415374939ca1bf8b8c0cc1df6a2f50db96c3c971c271a34`。

- 本次按用户授权重新投递BV1bgKm6YE4m，Job `job_7d51418f8d694e5aa27749dc0f539a71`，新Note `note_2e53e29519954de5a57d58794a3d5917`、版本`ntv_34b4f2dfe8e743ff847d62b739dcec99`，29章、11 READY截图/1质量拒绝；全部处理步骤完成，PARTIAL_SUCCESS为22 REVIEW地点，另4 AREA_UNRESOLVED/15 SKIPPED。原旧Note在本次开始时已不存在，未猜绑历史；新Note已固定同视频/转写Map。首轮当前Qoder模型返回非法JSON/实体引用，未放宽门禁；仅此Job恢复为已有GPT-6 Luna并复用ASR/校对/下载，再将本Job笔记输入4000→8192（模型工作上下文8192/总上下文32768），全局路由/模型/预算设置未变、累计用量保留。Qoder7次用量只估算输入20,234/输出25,223；GPT-6 Luna6次上报输入95,666/输出28,732；含失败与恢复，不代表常态单视频成本，费用未知。本机OCR READY识别8月份，无视觉兜底。实际封面主题仅山西宁武通过，3条证据未完整归纳按原文保留、名称/态度疑点继续提示；人工语义与POI验收待用户，未人工确认POI。最终生产新笔记1440/390px正文/封面原图/区域只读验收通过。提交推送结果以Git和保存点git-delivery.json为准。

- 2026-10-29 23:08 主题Token优化发布：共享语义注册表/地点引用、精简投影、旧格式兼容、来源误归因校验、输出去重与语义待核稳定缓存；仅Note编译投影身份升级，未打穿GMap/校对。无迁移，空闲/lease/在途调用门禁、备份API及停止后完整性/FK校验通过。保存点`data/backups/note-token-opt-20261029-225908`；回退源码基线为temporal-repair-20261029-174012/final-working-tree.tar.gz。API/Worker READY，新PID21206；HTTP index SHA256 `05c624b7100c422d99669f8322976522381b8a331113cbde0c5a1dbc3e6044e2`，资源逐一匹配，业务表摘要在发布/GET后无变化（仅运行事件/指定runtime设置除外），未回退。后端全量811/收尾97，前端全量/Lint/TS/隔离构建通过。真实模型5次仅在隔离库，本轮合计输入93,965/输出29,757 Token，含首轮来源问题与中间候选；最终同例基线25,734→候选23,732（-7.8%），输入-8.6%、输出-5.0%，候选更慢、费用/上游缓存UNKNOWN。生产旧Note未切换，未ASR/视频重跑/POI确认、提交或推送；[完整对照](benchmark/NOTE_THEME_TOKEN_OPTIMIZATION_20261029.md)。

- 2026-10-29 17:46 时节三项修复发布：小字否定待核、完整日历交集、OCR/视觉元信息缓存分离与内容身份稳定；无迁移。807后端、前端全量/Lint/TS/隔离构建及反例复验通过。保存点`data/backups/temporal-repair-20261029-174012`含工作树/旧静态/已验逻辑DB/停止后备份与发布回退脚本；源码回退基线为上轮cover-temporal-20261029-125122/final-working-tree.tar.gz。API/Worker RUNNING，新PID48296心跳READY，HTTP资源与隔离构建一致（index `05c624b7100c422d99669f8322976522381b8a331113cbde0c5a1dbc3e6044e2`，前端代码未改）；生产1440/390×844旧数据读取/排队模拟无溢出或相关错误。发布及最后GET后业务表摘要无变化，仅运行事件/指定runtime设置除外，未回退。本轮模型调用/历史切换/POI确认/提交/推送0。Token方案是同包离线候选测量，未实施共享表或精简Prompt；见[修复与Token分析](benchmark/VIDEO_TEMPORAL_REPAIR_AND_TOKEN_ANALYSIS_20261029.md)。

- 2026-10-29 15:43 封面P2/P3发布：无迁移，0027保持；写入口排空/无活跃Job与lease、备份API/完整性/FK、停止后复核通过。保存点`data/backups/cover-temporal-20261029-125122`含发布前工作树、旧静态、已验生产DB及隔离案例DB、哈希/脚本/Browser证据；源码回退基线为上轮已发布P1保存点`data/backups/temporal-context-20261029-105228/final-working-tree.tar.gz`。API/Worker RUNNING，新Worker PID21202心跳READY；新封面入队/读取/哈希原图路由已加载，HTTP index SHA256 `05c624b7100c422d99669f8322976522381b8a331113cbde0c5a1dbc3e6044e2`，JS/CSS逐一匹配隔离构建。发布及最终GET后业务表摘要无变化（仅运行事件/指定runtime设置除外），未回退。799后端/收尾主题21、前端61与Lint/TS/隔离构建通过；生产资源1440/390×844真实旧Note GET与隔离新版本GET/原图区域/显式视觉选择/排队模拟通过，无溢出或相关错误。真实模型与阶段验收只在隔离副本，REMOTE Token输入72,689/输出38,321，LOCAL输入9,778/输出2,949，含失败/修复，费用UNKNOWN。原Note仍指向ntv_39e83862aecc41e4bf0a5ba9ddba5fa3且产物NULL，生产无历史切换/视频重跑/POI确认，发布窗口无模型调用。未提交/推送；完整边界见[验收报告](benchmark/VIDEO_COVER_TEMPORAL_ACCEPTANCE_20261029.md)。

- 2026-10-29 10:56 视频时间P0/P1发布：用户确认THEME_CONTEXT与P2/P3后置，无迁移，0027保持；空闲/lease/在途调用门禁、SQLite备份API恢复完整性/FK校验通过。首次发布保存点`data/backups/temporal-context-20261029-104841`保留原源码HEAD/工作树与旧静态；收尾解析v2保存点`data/backups/temporal-context-20261029-105228`保留当前工作树、发布前/停止后已验DB及静态、脚本与Browser证据。API/Worker RUNNING，新Worker PID55272心跳READY，区域时间路由200；HTTP index SHA256 `eafdab39468469b98b3b03df1c5ce30c247b2965ebcfd7049cecb03960b0ea6e`，JS/CSS匹配隔离构建。两次发布和最终GET后业务表摘要均无变化（仅运行事件/指定runtime设置除外），未回退。后端全量774/收尾100、前端60与Lint/TS/隔离构建通过；1440/390×844生产主题筛选/来源/月组合/清除为明确拦截模拟，真实API旧数据空主题/清除另验，无溢出/相关错误。目标旧Note产物引用仍NULL，不猜绑；真实Provider/视频重跑/POI确认/历史更新0。未提交或推送；[完整证据与限制](benchmark/VIDEO_TEMPORAL_CONTEXT_IMPLEMENTATION_20261029.md)。旧快照保留原采样日期，不由本轮外推。

- 2026-10-28 18:17 视频最小修复与V07发布：生产0026→0027，新增笔记版本可空GroundedMap外键，22旧版本均NULL，无推断回填；原作者路线产物0。发布前/关闭入口后空闲复核，无活跃Job/lease/在途调用；逻辑备份已验、DB隔离副本0026→0027→0026→0027校验，迁移后44表原字段内容/数量一致、integrity=ok/FK0。保存点`data/backups/video-minimal-release-20261028-180824`含0026及重发前0027逻辑DB、源码/静态/LaunchAgent备份、原包、逐表哈希与发布脚本日志。首次守卫漏排运行心跳而恢复旧源码、保留兼容0027；逐键确认仅runtime:metrics-sample和runtime:worker-heartbeat后重发成功，未覆盖数据库。新Worker PID79127心跳/首页READY，API/Worker RUNNING；HTTP index/JS/CSS哈希不变（index 66c60131b672c3a76a05a165c0c975ade1dce44868f1006cd80995e90cb482bc），相关API视频笔记21条、来源路线0，除system_events启动事件和上述两项运行设置外无变化，调用审计不变。后端745/前端59、云南46/29及Lint/类型/隔离构建通过。本轮无前端代码/布局变更，不新增Browser验收；真实Provider/ASR/高德、视频重跑/POI确认0。源码提交f4dc52b，最终推送见保存点release-result.json。


- 2026-10-28 14:34 云南时节/作者路线：无迁移，0026保持；API/Worker RUNNING，内容及新PID49051心跳READY，active/lease/在途调用0，integrity=ok/FK0，最终42业务表摘要一致。保存点`data/backups/yunnan-regression-20261028-141659`含原包/前后源码、旧新静态/HTTP哈希、已验逻辑DB和漂移/空闲门禁回退脚本；DB SHA256 `97da4699e857e7a2058a7ef1209bb189dcdc61ba0a443e6a2d248354d90515e6`，线上index SHA256 `66c60131b672c3a76a05a165c0c975ade1dce44868f1006cd80995e90cb482bc`，JS/CSS匹配构建。首轮187已到期Artifact仅状态/updated_at变化触发源码/静态自动回退；逐字段/到期时间及其余41表核对后新备份重发，未恢复DB。新增API/真实只读v2导出22地点/506来源候选/3个人清单正常，旧作者路线0，无历史补算。962/390px生产Browser来源路线/原词待核/时间用途与适宜度交互通过、零溢出/相关错误；所有写响应拦截模拟。经授权真实模型3次/高德搜索3次在隔离库执行，生产ExternalCallAudit未增加；无生产视频重跑/POI确认。详细边界及回退证据见验收报告与保存点。

- 2026-10-27 17:29 POI代码复核升级：无新迁移，0026保持；API/Worker RUNNING，内容及新Worker PID85838心跳READY，active/lease/在途调用0，integrity=ok/FK0。最终保存点 `data/backups/poi-audit-final-20261027-172908` 含源码、旧新静态、逻辑DB、哈希与带漂移/空闲门禁的rollback.py；备份SHA256 `b5ca74db664a15dee817b78a2501f2479a4cee2833d13448055dedf28fe9a3e6`，线上index SHA256 `74af3b22a6145348148962dc4db8822e805c0138040abf4d95b464bf29c0a9bd`，JS/CSS HTTP匹配构建。后端全量656与末次目标86、前端57及Ruff/ESLint/类型/隔离构建、文档5项通过。962/390px生产Browser以挂起/释放模拟响应确认输入/确认互斥、表单保持、手动结果标签和中文类型，无溢出/相关错误；POST及新代表点均拦截，真实地图/笔记API只读正常。首轮172006保存点因62条已到期中间产物状态变化触发并完成源码/静态回退；逐字段确认仅AVAILABLE→EXPIRED及updated_at，原内容不变。172309重发核对11条、最终本次核对6条相同维护迁移，其余41张业务表摘要一致；未恢复业务库，原始差异证据保留。真实高德/模型/视频及历史POI重处理0，ExternalCallAudit仍1746；缺陷与界限见benchmark/POI_RESOLUTION_CODE_REVIEW_REPORT.md。本次本地提交、不推送。

- 2026-10-27 15:48 POI匹配/代表点：经用户明确授权执行0025→0026，迁移中所有业务表行内容/数量一致；最终重载前后42张业务表摘要不变。API/Worker RUNNING，内容及新Worker PID51609心跳READY，active/lease/在途调用0，integrity=ok、FK0。迁移保存点 `data/backups/poi-resolution-release-20261027-153554`；最终无迁移重载保存点 `data/backups/poi-resolution-final-20261027-154725`，含源码、旧新静态、哈希、已验逻辑DB与安全回退脚本；最终备份SHA256 `d2de50144ac96dafca1b9ead25846d27465bb16b8371a738f18564ac9416070e`。线上index SHA256 `ef053deddaafbfc16de8329e9b7848ad17dcc35b5004bd315f19f012625b5f63`，JS/CSS HTTP哈希与构建一致。目标笔记真实只读接口77条、地图真实只读接口18点；962/390px生产Browser验证搜索展开、代表点和类型筛选，搜索POST与代表点由夹具拦截，零生产业务写入、溢出与相关错误。未调用真实高德/模型、重跑视频或确认历史POI；代表点真实质量和实体级操作仍有独立验收边界。本任务本地提交、不推送。

- 2026-10-27 15:35 POI工作包发布准备：当前生产0025，API/Worker RUNNING、内容及Worker心跳READY；active Job/lease/在途调用0，integrity=ok、FK0。保存点 `data/backups/poi-resolution-release-20261027-153554` 含逻辑DB备份、旧新静态、源码快照、哈希清单及带漂移/空闲/重名门禁的rollback.py；备份SHA256 `13804244fc1bf37e3b191b41f56ac053dba56b9484c589503db4dc9a47062d8d`，旧线上静态HTTP与备份哈希一致。0026已在临时逻辑副本验证业务行内容/数量不变、integrity=ok/FK0；本次尚未迁移、部署、重启或真实Provider调用。该采样随时间失效，实际执行前必须重新核对并更新备份。

- 2026-10-27 11:47 地点标签/候选紧凑化：默认推荐不额外显示态度标签，只有名称旁“不推荐/有来源不推荐”；视频候选仅显示状态、真实详情/时间入口，无确认按钮与重复玩法chips，320px列表内部滚动。保存点`data/backups/place-display-20261027-113420`含源码前/发布tar/patch/哈希、已验逻辑DB、旧新静态/HTTP哈希与带漂移保护的rollback.py。仅静态更新，API/Worker未重启且RUNNING，内容/心跳READY，Worker PID61468不变；active/lease/在途调用0、integrity=ok/FK0/0025，业务表摘要一致，调用审计仍1746。最终3个静态资源HTTP哈希匹配，index SHA256 `df1cf3ebc3375164f47f5f45151f30e4dd561e49ca6358f6e8b155a3a1f88617`。后端632/前端49、目标10、ESLint/类型/隔离构建、文档5项通过；预览与生产962/390px验证两个指定Note的77/34条候选、栏目390px/内滚/状态/时间链接、地图单点/聚合/详情无默认标签，无溢出、相关错误或写请求。负向名称标记及聚合颜色用客户端fixture核对，不写生产。无历史改写、模型调用、视频重跑或POI确认；提交推送结果见同保存点release-result.json。


- 2026-10-27 02:56 存储/日志与地点态度：保存点`data/backups/storage-intent-20261026`含接手/发布源码tar、HEAD/patch/498文件哈希、41变更+9新增运行文件清单、已验SQLite逻辑备份、旧静态/旧新HTTP哈希、原LaunchAgent及无业务库回退的rollback.py。接手源码对上次发布零漂移。已登记现有根，根路径未变、配置与API/Worker加载代次均1；0025未迁移，未搬生产数据。API/Worker RUNNING，内容与新PID61468心跳READY；active/lease/在途调用0，integrity=ok/FK0。业务旧行无删除/改写，仅4条服务启动事件；调用审计仍1746。历史图片HTTP哈希、62段转写及可续跑Options只读核对通过，结构化日志在新active位置写入。最终6个静态资源HTTP哈希全匹配，index SHA256 `dabc76a105d454b8aaa5b9c998247151f2c8819d0ceaf0cca4143833aa6c66b6`。后端全量631、后续来源相关93/存储18（含二次切根别名）及暂存副本110通过；前端44+聚合1、Ruff/ESLint/类型/隔离构建、文档5项通过。隔离1192/390px预检不切根、策略保存刷新、人工确认后态度/偏好独立、视频/地图/详情与来源链接通过；生产相同断点存储状态/已有地点/地图只读通过，无溢出、相关错误或写请求。最终重载后等待READY再复验；中间一次Browser启动早于端口就绪，不作应用失败。生产无新态度证据/已确认负向样本，真实模型质量、视频、物理拔盘与实际搬迁未验。两计划归档、稳定契约及旧现场整理完成；提交推送结果见同保存点release-result.json。

> 下列保留上次原采样现场，本次未按当时PID重新复核。


- 2026-10-26 19:59 局部ID恢复：保存点data/backups/claim-id-recovery-20261026含485文件源码tar/patch/HEAD/哈希、已验逻辑DB、旧静态及HTTP哈希、6文件runtime-changes与带漂移/空闲门禁的rollback.py。对最近发布108文件清单核对，运行源码仅本包5文件变化及新增structured_ids.py；无迁移重载API/Worker。前后active Job/lease/在途调用0、integrity=ok/FK0/0025，业务表（含非runtime设置、历史任务、缓存及调用审计）摘要一致，ExternalCallAudit=1746。API PID63636/Worker PID63681 RUNNING，内容与新PID心跳READY；原index SHA256 c676fb6adbb82ac397b30b4a86e968400644b2389b23e242edcdb3b3a3f75999及JS/CSS HTTP哈希不变。发布工作树后端589/前端43及Lint/类型/隔离构建通过，无前端交互变化，未扩大Browser验收。指定任务在发布前已续跑一次并于19:24 PARTIAL_SUCCESS，本次API/DB与备份一致；未触发真实Provider/视频/POI操作。准确提交范围含必要已上线JSON纠错依赖，隔离副本目标72项及Ruff通过，提交/推送结果见保存点release-result.json；其他在途改动不纳入。

旧生产快照已归档至 [生产快照历史](history/PRODUCTION_SNAPSHOTS.md)，保留原采样日期。
