# 云南地点时节与作者路线验收（2026-10-28）

结论：P0–P3源码、离线规则、无迁移发布完成；真实Ground Map/高德小样已执行，**完整语义召回不宣称通过**。原稿101段/5093字；simulation-v1仍是待审参考。输入包SHA见[fixture provenance](../../backend/tests/fixtures/travel_pipeline/yunnan_bv16yem6reyx/provenance.json)。

## 阶段与结果

|阶段|变更/存储兼容|结果|
|---|---|---|
|P0|逐mention时间状态、背景零分、活动/局部道路不关闭整个目的地、人工period_type/suitability、怎么去分栏|pass；负例、PC/Mobile交互通过|
|P1|用途/活动/范围/跨年/日级精度，单AREA锚点上下文，泛称/待核保留原词；取消80条物化静默截尾|pass；复用metadata/Insight JSON，无Schema迁移，区域11–3月不灌给子景点|
|P2|新Artifact JSON作者路线、站点/条件/Evidence验证，显式复制与版本门禁；模型缺route对象时证据语法恢复|pass；确定站序/列举/局部串线分开，未知位置保留待核，navigation=null；原RouteDraft独立|
|P3|只读dry_run、v2 ZIP地点/候选/路线/原句/人工备注，旧三格式不变|pass；不提供自动历史回填，未确认路线不能复制为只支持Place的个人清单|

后端全量703 pass（156.49秒），最终相关79 pass；云南专项46 pass/29条断言pass，fail=0/skip=0。前端全量59 pass、最终页面4 pass；Ruff/ESLint/TypeScript/隔离Vite构建pass。原有Starlette httpx弃用及Vite大chunk提示仍在，无本轮验证失败。专项一条命令及证据定义见[常驻样本](../testing/GOLDEN_SAMPLES.md)，逐条结果和71候选投影见[离线JSON](YUNNAN_REGRESSION_OFFLINE_REPORT_20261028.json)。所有离线name-retention指标只评价已标注输入保全，不是模型抽取质量。

## 真实验证与边界

用户本轮明确允许真实验证。当前已配`codex/gpt-6-luna`经LocalAiMux，隔离临时库运行3个串行GROUND_MAP分包，原始耗时265.967秒，Provider报告输入44,839/输出32,319 Token。只读现有设置和Keychain；无生产视频下载/ASR/整笔记重跑、历史回填或POI确认。临时GROUND_MAP限定max_attempts=4/retry_count=0/json_retry_count=1/单次360秒/阶段900秒；其他选型沿用现有配置，生产配置不改。

真实模型返回104实体/76 Claim，其中9条路线Claim均省略可选route对象，初版0条作者路线；还暴露80条截尾和区域原句缺名。保存真实响应后补通用证据语法恢复与单AREA锚点，禁网精确缓存重放仅0.088秒，新增模型请求0，最终13个全部待核路线对象及102条候选。13对象对应原11组参考、单独G214细节和额外局部边境描述；不能以对象数称导航正确率。冻结真实响应加入回归，恢复保留六库→贡山→丙中洛、G214细节/宏观、洱海骑驾分离、建水→石屏及美食清单；无里程/时长/几何或虚构闭环。

与参考71项按去括注原词进行字面集合比较TP53/extra39/FN18，precision0.5761/recall0.7465/F1 0.6503。extra可含有效背景、别名或粒度差异，**不是已裁定误报数**；真实语义TP/FP/FN、范围/活动错误数仍NEEDS_REVIEW，不以字面重合代替语义金标。模型遗漏部分实体和局部警示（含骑马负向）；C02“泸沽湖更推荐自驾”在该局部原文无明确支持，不从其他区域补造。71项matched/missing及13条实际路线见[真实JSON](YUNNAN_REGRESSION_REAL_REPORT_20261028.json)。

高德串行只读查询3次：元阳梯田20候选、罗平油菜花7候选、支子罗1近名游客中心；未自动改名、确认、选择坐标或批量请求。只证明这三次搜索响应，不证明官方名称、候选精度、现时道路安全或旅游季节事实。

## 同条件离线成本对比

|指标|原HEAD c2325ea|改造后|解释|
|---|---|---|---|
|固定时窗解析中位/200次|0.0228ms|0.0590ms|多范围解释增加约0.0363ms，不声称加速|
|同seed地图GET中位/10次|4.389ms|4.493ms|短样本，仅观测|
|每次地图SQL|31|31|无新增N+1或后台Provider调用|
|跨年月份|11、3|11、12、1、2、3|原词范围修复|
|背景状态|POSSIBLE|UNKNOWN|不再背景+1|

离线对比两侧模型请求均0，真实Token的改造前同模型对照not-run；缓存重放不是模型速度/Token节省证据。源脚本、日志和原始模型结果只存发布保存点，不将密钥/完整服务设置提交远端。

## 发布与Browser

2026-10-28 14:34（北京时间）无迁移重载，0026保持；API/Worker RUNNING、内容/新Worker PID49051心跳READY。active/lease/在途调用0，integrity=ok/FK0；最终42张业务表摘要一致。首轮187条到期Artifact只有AVAILABLE→EXPIRED与updated_at变化，严格门禁触发并完成源码/静态回退；核对41张其余业务表不变和到期时间后建立新逻辑备份重发，未恢复数据库。

保存点`data/backups/yunnan-regression-20261028-141659/`含原包/原源码、发布源码与patch、旧新静态、逻辑DB及哈希、门禁回退脚本。最终DB SHA256 `97da4699e857e7a2058a7ef1209bb189dcdc61ba0a443e6a2d248354d90515e6`，线上index SHA256 `66c60131b672c3a76a05a165c0c975ade1dce44868f1006cd80995e90cb482bc`；实际HTTP JS/CSS匹配构建。生产只读v2导出22地点/506当前来源候选/3个人清单，历史作者路线0，证明未自动回填。

Browser插件未提供，采用已安装Playwright+Edge。隔离与生产`http://127.0.0.1:8787`在962×876/390×876验证路线原词/待核、非导航声明、来源展开、用途与不宜保存/刷新；写请求全部拦截模拟，生产真实读接口另核验。均无横向溢出、框架覆盖层或相关控制台错误，真实业务写0；截图与browser JSON在保存点。

## 文档与未验收项

原zip保存到发布备份，planning重复压缩包已清理；唯一实施记录归档history/planning，冻结fixture和provenance保留；契约归旅行领域/API/测试专项，验证归当前状态与本报告，现场归既有CURRENT_HANDOFF，合订本按源集重建。未删无关文档和本地export-evaluation-doc，未修改历史迁移。

完整视频/ASR/Note端到端not-run；全71候选独立语义审核、实时路况、真实导航、全高德质量、生产历史回填not-run/NEEDS_REVIEW。下一步为人工审核字面差异及局部漏提并冻结独立语义金标，禁止把本包当作自动历史重算授权。
