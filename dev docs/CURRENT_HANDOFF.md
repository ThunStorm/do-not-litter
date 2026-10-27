# 当前交接

> 本文件只维护任务续接与带日期的生产快照；源码能力和自动验证的唯一来源为 [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)。

## 任务续接

- 目标：发布并交付Ground Map局部ID恢复，不扩大真实模型/视频验收。
- 完成：无歧义Claim ID本地修复；实体/单元冲突拒绝，精确诊断、原预算纠错及审计/缓存血缘闭环。新增20项，工作树后端589/前端43及Lint/类型/隔离构建及提交副本目标72项通过；真实响应40条Claim离线保留，修复1处，调用0。
- 发布：无迁移重载API/Worker，0025、内容/新PID心跳READY，业务/静态哈希不变；保存点data/backups/claim-id-recovery-20261026。提交含JSON纠错依赖，隔离验证及提交/推送结果见保存点release-result.json；其他在途改动保留。
- 未闭环：真实恢复率、歧义纠错质量及既有取消/地图F未验。原任务部署前19:24已PARTIAL_SUCCESS，本次未重跑。
- 下一步：明确视频、模型与调用范围后验实际恢复质量。
- 文件：ai/structured_ids.py、request_compiler.py、json_recovery.py、services/video_support.py；契约ai-gateway/04-stage-policy.md。
- 禁止：不自动调用模型、重跑视频、确认POI、迁移或改历史/凭据；旧快照、显式0重试与REMOTE_ONLY保持。

## 生产快照（最新采样2026-10-27 15:48，北京时间）

- 2026-10-27 15:48 POI匹配/代表点：经用户明确授权执行0025→0026，迁移中所有业务表行内容/数量一致；最终重载前后42张业务表摘要不变。API/Worker RUNNING，内容及新Worker PID51609心跳READY，active/lease/在途调用0，integrity=ok、FK0。迁移保存点 `data/backups/poi-resolution-release-20261027-153554`；最终无迁移重载保存点 `data/backups/poi-resolution-final-20261027-154725`，含源码、旧新静态、哈希、已验逻辑DB与安全回退脚本；最终备份SHA256 `d2de50144ac96dafca1b9ead25846d27465bb16b8371a738f18564ac9416070e`。线上index SHA256 `ef053deddaafbfc16de8329e9b7848ad17dcc35b5004bd315f19f012625b5f63`，JS/CSS HTTP哈希与构建一致。目标笔记真实只读接口77条、地图真实只读接口18点；962/390px生产Browser验证搜索展开、代表点和类型筛选，搜索POST与代表点由夹具拦截，零生产业务写入、溢出与相关错误。未调用真实高德/模型、重跑视频或确认历史POI；代表点真实质量和实体级操作仍有独立验收边界。本任务本地提交、不推送。

- 2026-10-27 15:35 POI工作包发布准备：当前生产0025，API/Worker RUNNING、内容及Worker心跳READY；active Job/lease/在途调用0，integrity=ok、FK0。保存点 `data/backups/poi-resolution-release-20261027-153554` 含逻辑DB备份、旧新静态、源码快照、哈希清单及带漂移/空闲/重名门禁的rollback.py；备份SHA256 `13804244fc1bf37e3b191b41f56ac053dba56b9484c589503db4dc9a47062d8d`，旧线上静态HTTP与备份哈希一致。0026已在临时逻辑副本验证业务行内容/数量不变、integrity=ok/FK0；本次尚未迁移、部署、重启或真实Provider调用。该采样随时间失效，实际执行前必须重新核对并更新备份。

- 2026-10-27 11:47 地点标签/候选紧凑化：默认推荐不额外显示态度标签，只有名称旁“不推荐/有来源不推荐”；视频候选仅显示状态、真实详情/时间入口，无确认按钮与重复玩法chips，320px列表内部滚动。保存点`data/backups/place-display-20261027-113420`含源码前/发布tar/patch/哈希、已验逻辑DB、旧新静态/HTTP哈希与带漂移保护的rollback.py。仅静态更新，API/Worker未重启且RUNNING，内容/心跳READY，Worker PID61468不变；active/lease/在途调用0、integrity=ok/FK0/0025，业务表摘要一致，调用审计仍1746。最终3个静态资源HTTP哈希匹配，index SHA256 `df1cf3ebc3375164f47f5f45151f30e4dd561e49ca6358f6e8b155a3a1f88617`。后端632/前端49、目标10、ESLint/类型/隔离构建、文档5项通过；预览与生产962/390px验证两个指定Note的77/34条候选、栏目390px/内滚/状态/时间链接、地图单点/聚合/详情无默认标签，无溢出、相关错误或写请求。负向名称标记及聚合颜色用客户端fixture核对，不写生产。无历史改写、模型调用、视频重跑或POI确认；提交推送结果见同保存点release-result.json。


- 2026-10-27 02:56 存储/日志与地点态度：保存点`data/backups/storage-intent-20261026`含接手/发布源码tar、HEAD/patch/498文件哈希、41变更+9新增运行文件清单、已验SQLite逻辑备份、旧静态/旧新HTTP哈希、原LaunchAgent及无业务库回退的rollback.py。接手源码对上次发布零漂移。已登记现有根，根路径未变、配置与API/Worker加载代次均1；0025未迁移，未搬生产数据。API/Worker RUNNING，内容与新PID61468心跳READY；active/lease/在途调用0，integrity=ok/FK0。业务旧行无删除/改写，仅4条服务启动事件；调用审计仍1746。历史图片HTTP哈希、62段转写及可续跑Options只读核对通过，结构化日志在新active位置写入。最终6个静态资源HTTP哈希全匹配，index SHA256 `dabc76a105d454b8aaa5b9c998247151f2c8819d0ceaf0cca4143833aa6c66b6`。后端全量631、后续来源相关93/存储18（含二次切根别名）及暂存副本110通过；前端44+聚合1、Ruff/ESLint/类型/隔离构建、文档5项通过。隔离1192/390px预检不切根、策略保存刷新、人工确认后态度/偏好独立、视频/地图/详情与来源链接通过；生产相同断点存储状态/已有地点/地图只读通过，无溢出、相关错误或写请求。最终重载后等待READY再复验；中间一次Browser启动早于端口就绪，不作应用失败。生产无新态度证据/已确认负向样本，真实模型质量、视频、物理拔盘与实际搬迁未验。两计划归档、稳定契约及旧现场整理完成；提交推送结果见同保存点release-result.json。

> 下列保留上次原采样现场，本次未按当时PID重新复核。


- 2026-10-26 19:59 局部ID恢复：保存点data/backups/claim-id-recovery-20261026含485文件源码tar/patch/HEAD/哈希、已验逻辑DB、旧静态及HTTP哈希、6文件runtime-changes与带漂移/空闲门禁的rollback.py。对最近发布108文件清单核对，运行源码仅本包5文件变化及新增structured_ids.py；无迁移重载API/Worker。前后active Job/lease/在途调用0、integrity=ok/FK0/0025，业务表（含非runtime设置、历史任务、缓存及调用审计）摘要一致，ExternalCallAudit=1746。API PID63636/Worker PID63681 RUNNING，内容与新PID心跳READY；原index SHA256 c676fb6adbb82ac397b30b4a86e968400644b2389b23e242edcdb3b3a3f75999及JS/CSS HTTP哈希不变。发布工作树后端589/前端43及Lint/类型/隔离构建通过，无前端交互变化，未扩大Browser验收。指定任务在发布前已续跑一次并于19:24 PARTIAL_SUCCESS，本次API/DB与备份一致；未触发真实Provider/视频/POI操作。准确提交范围含必要已上线JSON纠错依赖，隔离副本目标72项及Ruff通过，提交/推送结果见保存点release-result.json；其他在途改动不纳入。

旧生产快照已归档至 [生产快照历史](history/PRODUCTION_SNAPSHOTS.md)，保留原采样日期。
