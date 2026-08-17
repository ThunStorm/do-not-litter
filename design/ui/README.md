# 至简 UI 设计稿索引

本目录保存“至简”第一版的高保真界面参考稿，视觉基线为暖白纸张底、墨黑正文、朱砂红主强调色、少量苔绿状态色、浅灰发丝线、宋体感标题与现代无衬线正文。设计稿用于确定信息架构、层级、密度和交互优先级；实施时文字、图标、表格与地图均应使用原生 UI/代码绘制，不把整张设计图作为页面背景。

## 页面清单

| 文件 | 端 | 页面职责 |
| --- | --- | --- |
| `00-home-pc.png` | PC | 首页基线：兼顾运维状态与少量结构化结果 |
| `01-home-mobile.png` | 手机 | 首页视觉基线；底部导航实施时以本索引约束为准 |
| `02-home-pc-mac-mini-backend.png` | PC | Mac mini 独立后端方案：首页显示远端节点、服务与 Metal Runtime |
| `10-task-detail-pc.png` | PC | Job/Pipeline 运行详情、步骤日志、输出物版本与重试 |
| `11-source-evidence-pc.png` | PC | Source Graph、Snapshot、Segment 与 Claim/Evidence 审计 |
| `12-content-library-pc.png` | PC | 结构化内容库、筛选、列表与详情预览 |
| `13-settings-models-pc.png` | PC | DeepSeek、MiMo、Ollama 等 Provider 与调用策略配置 |
| `20-content-mobile.png` | 手机 | 内容中心、搜索、当前分类与截止提醒 |
| `21-todo-confirm-mobile.png` | 手机 | 身份、POI 歧义和截止日期的确认型待办 |
| `22-recruitment-detail-mobile.png` | 手机 | 招聘详情、PASS/REVIEW/UNKNOWN 与原文证据 |
| `23-travel-detail-mobile.png` | 手机 | 旧版旅行详情，仅保留设计过程；其中内嵌地图结构已废弃 |
| `23-travel-detail-mobile-v2.png` | 手机 | 地点详情修正版：无内嵌地图，可返回地图继续浏览 Marker |
| `24-capture-progress-mobile.png` | 手机 | 链接/文件/扫描投递，以及处理进度和最近完成 |
| `25-map-overview-mobile.png` | 手机 | 独立地图总览、多 Marker 分布、地点预览与路线清单入口 |

## 实施约束

- PC 是 CMS 与运维主入口，但首页必须同时展示少量结构化结果；数据不足时使用叙事式列表、详情预览和自然留白，不用空统计窗格或虚构数量填满页面。
- 手机是日常主入口。全局底部导航固定抽象为“首页 / 内容 / 投递 / 待办 / 我的”，招聘、旅行属于内容分类，不能成为全局导航项。
- 第一版内容分类只实现“全部 / 招聘 / 旅行 / 筛选”。分类栏应支持未来横向扩展，但当前不显示学习、项目、生活或“管理分类”。
- 微信、Bilibili、高德、模型服务商等外部来源均使用统一的单色线性图标，不引入品牌色破坏主题一致性；地图本体可使用低饱和底图。
- 招聘条件核验只显示 `PASS / FAIL / UNKNOWN / REVIEW` 及其证据，不生成伪精确匹配百分比；关键结论可下钻到页码、段落或原始快照。
- 旅行内容必须把作者观点、可观察事实与 AI 推断分开；高德 POI 和地图明确标注 `GCJ-02`，视频结论可定位到时间码 Evidence。
- 地图是旅行内容的独立空间总览父页面，不是地点详情的附属模块。点击不同 Marker 只切换底部地点预览；点击“查看详情”才进入 `23-travel-detail-mobile-v2.png`，返回时恢复地图视野与选中点。旧版 `23-travel-detail-mobile.png` 不再作为实施依据。
- 路线清单第一版只负责选点和手动排序，不展示未经真实 Route Provider 计算的最优路线、距离或交通时间。
- 投递入口统一承接 URL、DOCX、PDF、图片和 OCR；手机离开进度页后，可信局域网内的 PC Worker 仍可继续处理。
- 密钥只显示掩码。外部 Provider 是可选能力，敏感内容优先本地处理，并保留脱敏与最小审计信息。
- 部署方案二选一：`00-home-pc.png` 对应原 Windows PC 本地节点语境；`02-home-pc-mac-mini-backend.png` 对应 PC 浏览器连接 Mac mini 后端。两者共用页面结构，实施时根据 `DEPLOYMENT_TARGET` 显示节点、硬件与 Runtime，不维护两套业务 UI。

## 文档映射

- 页面与 CMS 职责：`../../dev docs/CONTROL_CENTER.md`
- Windows PC / Mac mini 部署选择：`../../dev docs/DEPLOYMENT_OPTIONS.md`
- 产品范围与手机局域网访问：`../../dev docs/PRODUCT_REQUIREMENTS.md`
- Source、Snapshot、Segment、Claim、Evidence：`../../dev docs/DATA_MODEL.md`
- DeepSeek、MiMo、Ollama 与 Provider 路由：`../../dev docs/AI_RUNTIME_AND_PROVIDERS.md`
- 招聘状态与证据规则：`../../dev docs/RECRUITMENT_PIPELINE.md`
- 高德地图、GCJ-02 与视频时间证据：`../../dev docs/TRAVEL_FOOD_PIPELINE.md`

## 生成说明

设计稿由内置图像生成模式依据已确认的 PC 与手机首页稿延展生成，生成日期为 2026-08-18。图片是产品设计参考，不是最终可访问性、文案或像素级实现验收的替代品。
