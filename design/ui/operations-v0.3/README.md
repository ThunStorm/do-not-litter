# operations-v0.3 设计审阅包

状态：已实施并经浏览器审阅。基线日期：2026-08-21。

本目录针对页面批注只升级四个范围：缩放/窄桌面任务列表、任务实时步骤诊断、运维日志工作台、侧栏 Mac mini 实时指标。视觉语言、导航结构和内容层级继续沿用 `implementation-v0.2`，不借本轮改动重做整套产品。

| 设计稿 | 审阅重点 |
| --- | --- |
| `01-tasks-responsive-pc.png` | 935px 有效视口，72px 收窄侧栏；标题/状态和元信息/进度分为两层，长 URL 不再挤压状态 |
| `02-task-detail-live-pc.png` | 顶部“当前处理”卡展示子状态、持续时间、心跳、模型和最近事件；时间线按执行顺序排列 |
| `03-logs-operations-pc.png` | 健康摘要、时间/级别/组件/关联 ID 组合筛选、结构化事件表格和实时跟随控制 |
| `04-sidebar-runtime-pc.png` | 完整侧栏左下角增加 CPU、内存、数据盘与 Worker 心跳，数值均定义为真实接口数据 |
| `05-model-routing-pc.png` | 自定义模型库与主/备用路由；模型名称、Provider、Base URL、模型名和 Keychain 状态都由用户填写 |
| `06-content-history-delete-pc.png` | 内容行尾的独立删除入口与详情跳转隔离 |
| `07-task-history-delete-pc.png` | 终态任务行尾的删除入口；运行中任务不显示该操作 |
| `08-settings-runtime-models-v0.5.svg` | 持久化局域网指标、百分比内存、路由卡内嵌说明与 Provider 预设联动 |
| `09-settings-runtime-models-implemented-pc.png` | 1193px 实装验收：草稿 Ollama 真实测试成功、300 秒默认超时、百分比侧栏指标 |
| `11-runtime-provider-v0.6.svg` | 修正后内存工作集口径、扩展运行浮窗与 Provider 默认值/手填值切换规则 |
| `12-task-attempt-time-v0.6.svg` | 任务重试时间重置与停滞状态的诊断卡、时间线、摘要语义 |
| `13-step-progress-v0.6.svg` | 总任务进度与每一步独立进度的分离规则，避免复用里程碑百分比 |
| `14-task-timeout-implemented-pc.png` | 真实旧任务被任务专属超时终止后，错误码、原因、100% 完成步骤与本地时间显示 |
| `15-runtime-popover-implemented-pc.png` | 修正口径后的 Mac mini 运行浮窗：GB 内存、可回收/压缩、磁盘和服务状态 |
| `16-mobile-session-job-control-v0.7.svg` | 手机刷新会话、阶段诊断日志与取消/重试门禁状态 |
| `17-video-stage-diagnostics-implemented-pc.png` | 真实重复 Bilibili 投递的阶段日志、取消请求与 Worker 确认释放 lease |
| `18-task-summary-partial-success-v0.8.svg` | 长字段收缩、非 LLM 模型字段与“核心结果已完成”部分完成语义 |
| `19-task-summary-partial-success-implemented-pc.png` | 实际部分完成任务：核心结果说明、地点待确认原因与不显示 ASR 文件路径的摘要 |
| `20-video-note-rendering-v0.9.svg` | 最近模型调用、处理流程完成说明、封面占位与安全 Markdown 笔记排版 |
| `21-task-model-context-implemented-pc.png` | 实际部分完成任务的最近模型调用与补充原因摘要 |
| `22-video-note-markdown-implemented-pc.png` | HTTPS 封面失败占位与 Markdown 标题、列表、粗体渲染 |

图片来自已运行的生产构建，供审阅与回退比对；交互、数据字段、延迟阈值和验收条款以 `dev docs/OPERATIONS_UI_SPEC.md` 为唯一实现契约。`prototype.html` 只用于设计探索，不属于生产前端，不应打包部署。
