# U 待处理入口与原位复核验收（2026-11-13）

HEAD `e9c509913208480604295f3db6acf4053f73a221`，接手已有Q/R/P、资源保留、封面等未提交修改，初态保存于`data/benchmarks/review-u-20261113/initial-{status.txt,source.tar.gz}`及initial.patch。本包未提交/推送，无Schema/依赖/历史回填、真实Provider/高德/ASR、视频重跑或生产确认。维护性抽取仅选只读投影及前端契约纯函数，不拆状态机。

## 契约与实现

U1：`review-projection-v1`从Job/失败Step、Mention及Note版本批量读取，不建表、不逐问题调用详情。稳定键分别为Job+retry、Step+retry+version、Mention+Note版本（缺失标UNKNOWN）；同Step不再额外算Job失败，同任务多个Mention分别计数。后端提供同筛选任务数/问题数、人工和后台等待及未知任务身份计数；现有列表无分页，计数覆盖完整查询，非当前可见行。PARTIAL_SUCCESS保留终态，不从旧Content计数推断实时待办。运行中Mention进入等待，未派发冷却明确标自动继续；普通超时不写额度暂停。Note质量疑点继续现有版本绑定的阅读提示，不强制升级为人工红色待办。

U2：Tasks用URL保留人工/等待筛选，直达指定Mention；Video Notes搜索参数保留；复核卡显示原词、原句、时间、类别地址、分类原因和阻断原因，沿用P的poi-review-v1及后端revision保护。搜索返回的新契约支配新候选；未知契约关闭动作。确认位置不改作者态度。深链接含Note+精确版本+章节；缺少身份不猜绑，旧阅读页不能精确打开的历史版本返回410并说明，不静默跳新版；缺失锚点提示。历史完整阅读暂不新增，卡片原文证据可读。转写上下文按该Note版本绑定的Transcript查取，显示原始文本。

U3：复用travelChanges跨页通知及焦点刷新，刷新Job、问题数、POI/笔记/地图缓存；未加轮询。409丢弃本地搜索候选并刷新，网络错误与加载不显示为空待办。返回带筛选/目标锚点，定位焦点；现有人工决定、墓碑、隐藏与后端允许动作保留。

## 操作步数与验证

|固定流程|实施前|候选隔离Browser|
|---|---|---|
|Tasks→指定POI原文|没有“需要处理→指定问题”入口，不能同路径计步|筛选1→问题链接2，原文直接可见|
|Tasks→指定版本章节|没有版本限定的复核链接，旧链接可能读新版|筛选1→问题2→章节3；不含展开长证据|
|旧版本→返回|旧链接没有版本保护|明确410→返回恢复mention筛选，未切最新版|
|确认后刷新|原跨页通知保留|模拟写1次后目标从权威列表消失；生产写0|

后端工作树全量973项通过（末次运行后仅追加运行中Mention等待分类，已目标复验），前端全量66项与末次目标6项通过；Ruff、ESLint、TS、隔离构建及diff检查通过。生产Python3.14候选16项目标通过。首次候选未带P搜索失败修复，2项失败；纳入必要P依赖后16项通过，原失败日志保留，未以删测试规避。目标涵盖同任务多问题/不重复Job失败/等待/刷新消失/未知身份、版本410、契约缺失与候选禁用，已有409/互斥/空搜索回归复用。

Browser插件未提供，依frontend-testing-debugging使用已有Playwright/Edge。隔离及生产1440/970/390×900，任务筛选、目标定位、带版本链接、失效返回、模拟确认刷新、Tab和页面非空/无overlay、零溢出/相关console错误通过；隔离每视口1次确认拦截、生产0写请求。JSON/截图在`data/benchmarks/review-u-20261113/`。这些为界面/Fixture证据，不是POI或模型质量验收。

## 发布与回退

2026-11-13完成发布。保存点`data/backups/review-u-20261113/`含工作树tar/patch、源码逐文件哈希、旧静态/旧plist、已验SQLite逻辑备份及release.py回退入口。生产基线组装仅5后端文件：API router/video_notes、review_projection、poi_review及P搜索失败清旧候选的必要resolver函数；未带其他在途修改，runtime-changes.json记录范围。前端来自本包隔离构建。0027未迁移，维护锁内确认无活跃Job/lease/在途调用，逻辑备份integrity/FK通过后无迁移重载API/Worker。发布后业务表摘要一致，仅API/Worker启动事件2条；HTTP index/JS/CSS三资源哈希全匹配，Worker心跳及API正常。生产聚合人工待办30任务/321问题，POI DTO314条，任务/问题分开。生产Browser三断点通过。没有实际回退；`release.py rollback`校验后续部署漂移及空闲门禁后恢复旧源码/静态，不恢复业务库。哈希与时间见http-health-hashes.json，门禁及摘要见release-verification.json。

未验：真实搜索/确认/拒绝、重跑和模型质量；历史版本全文阅读仅明确失效，不新增历史阅读器。下一步按用户追加指令依总览继续S，然后K；X须另定平台档位及权限。
