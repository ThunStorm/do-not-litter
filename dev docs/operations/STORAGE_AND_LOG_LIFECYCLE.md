# 数据目录与日志生命周期

本页维护启动、受管路径、搬迁与文件日志契约。源码能力/自动验证见[当前状态](../IMPLEMENTATION_STATUS.md)，实际部署见带日期的[生产快照](../CURRENT_HANDOFF.md)。历史设计分别归入[存储计划](../history/planning/DATA_STORAGE_AND_LOG_LIFECYCLE_PLAN.md)与[地点态度计划](../history/planning/PLACE_RECOMMENDATION_INTENT_PLAN.md)。

## 启动与目录

独立启动配置默认位于 `~/Library/Application Support/Zhijian/storage.json`，可通过 `ZHIJIAN_STORAGE_CONFIG` 指定隔离控制目录。它保存实例 ID、配置代次、卷/目录身份、当前根及已登记旧根；权限600、原子替换并保留切换前配置。根目录的 `.zhijian-instance.json` 与卷/目录身份必须匹配，既有实例的 app.db 必须存在。生产环境与保存配置冲突、卷失联或数据库缺失时拒绝启动；数据库连接使用 SQLite `mode=rw`，不隐式建立空库。未登记的旧安装保持原目录，开发/测试允许显式根覆盖；新实例必须经 `python -m zhijian.storage_cli init --root <新目录>` 明确初始化。

API、Worker、CLI、Alembic、部署管理、本地 AI/模型队列/高德锁使用同一配置解析。生产状态接口同时展示配置与实际加载代次；Worker 心跳携带加载根和代次。`permanent/` 管永久资料、截图/封面与导出，`cache/` 管有续跑契约的媒体和中间产物，`models/` 无自动过期。`runtime/` 仅恢复新进程运行状态，不复制旧PID/锁；混放其中的 Qwen venv 保留安装路径，外部模型库、Keychain、旧备份、系统启动日志单独披露，不当普通文件静默搬迁。

新增截图、封面和媒体Artifact使用 `storage:` 根相对引用；统一解析器拒绝 `..`、受管符号链接及根外逃逸。历史绝对路径仅按已登记旧根映射；读、Replay和删除共用解析器。用户外部原始媒体保持只读引用，不能被缓存清理。Source原始locator、正文和Evidence不做字符串替换；无法覆盖的技术引用使搬迁失败并留报告。

## 预检、应用和恢复

设置“存储与日志”输入的是服务器 Mac 路径。HTTP只做轻量预检、启动独立后台清点和保存待应用方案，不在请求内复制/哈希全量资料、不停服务、不切库。后台进程持稳定控制目录维护锁；设置保存成功只表示待应用。支持经过写探针、锁和原子替换检查的本机APFS/HFS卷；拒绝网络/云同步、相互嵌套、其他实例或非空目标及空间不足。预检展示分类容量、空间余量、例外和状态。

本机命令（仓库根，使用生产解释器或有完整项目依赖的解释器）：

```sh
.venv/bin/python deploy/macos/manage.py storage-adopt
.venv/bin/python deploy/macos/manage.py storage-plan --target /Volumes/资料盘/至简资料
.venv/bin/python deploy/macos/manage.py storage-apply
.venv/bin/python deploy/macos/manage.py storage-recover
PYTHONPATH=backend/src .venv/bin/python -m zhijian.storage_cli status
```

`storage-adopt`只登记已有库，不搬迁。实际搬迁须另外明确目标目录与授权；`storage-apply`先挡新业务写入，最多等待300秒让现有Job/模型测试/租约/调用自然结束，不为搬迁取消任务。未到安全窗口恢复待应用状态；停机后再复核空闲、完整性/FK与空间，建立已验SQLite逻辑备份，复制受管清单并逐文件核对大小/哈希，验证技术引用、提交新实例标记与原子配置。启动API/Worker时业务写入仍被挡住，核对健康与实际加载根/代次后才放行。旧根保留恢复副本，程序不删除它。

控制状态为 `DRAINING → COPYING → SWITCHED → VERIFYING → RELEASED`。中断/失败留下状态和清单；放行前用 `storage-recover` 停服务并恢复旧配置，核对旧服务健康后解除门禁，目标残留保留供追溯。放行写入后拒绝直接退回旧库，必须重新排空并保护最新数据。重复应用、配置代次漂移和并发维护均被拒绝。实际生产搬迁、物理拔盘和目标介质的故障验收须单独记录；临时目录模拟不能冒充它们。

## 文件日志与审计

| 类别 | 默认策略 |
| --- | --- |
| API/Worker结构化运行日志 | `logs/active/{service}.log` 中每行JSON；10MiB或跨UTC日封卷；关闭48小时后gzip；总保留30天；归档池1GiB |
| stdout/stderr与正常启动日志 | 输出包装器拥有句柄并轮换；启动日志在稳定用户Library日志目录，stdout/stderr在数据根；关闭48小时后gzip、总7天、独立池128MiB |
| 最小bootstrap故障兜底 | 稳定用户日志目录；标准库大小轮换，每服务128KiB/2备份；不依赖数据卷；Python自身无法启动的错误需查launchd系统诊断 |
| SQLite系统事件/外部调用审计 | 沿用原 `app:general.data_retention_days` 默认90天/7–3650天，按批最多500行；活跃/可续跑依赖与在途调用保留 |

文件策略在稳定控制目录 `log-policy.json`，不覆盖原数据库审计配置。设置包含压缩开关、延迟、保留天数、单卷大小、分类容量及低空间阈值；压缩延迟必须短于两类总保留期。写入器发出日志时至多5秒刷新策略代次；页面显示已加载版本，不能将保存等同于所有空闲进程已刷新。保留/容量缩短须先预览数量/字节，再凭相同封卷清单的token显式应用，清单变化必须重试。空间上限优先于天数；活跃文件不计作删除候选，无安全候选时只告警，不能牺牲业务资料。

封卷名称不可变且不重编号，关闭UTC时刻、原始字节/哈希和策略版本登记于旁索引，日龄不用mtime。gzip写同目录临时文件，解压核对原哈希后原子提交索引，再删原卷；失败保留原卷，封卷改名/索引提交的中断窗口可恢复，操作幂等。Worker在空闲时每分钟处理至多16卷/5秒，并和搬迁共享锁；状态摘要在控制目录 `log-maintenance.json`，按日志根保留最近结果。旧JSONL和launchd长期持有的stdout/stderr只在两服务停止后复制核验归档，不做copytruncate。新launchd通过包装器转发信号/退出码，应用句柄由包装器关闭重开。

缓存清理只处理当前实例缓存，保护活跃Job、有效续跑和共享文件；未知归属/根外原件不删。转录仍为180天，清理text/raw_text/corrected_text及既有Evidence.quote副本，保留永久笔记、截图和结构化业务证据契约；历史备份和永久原句不因在线正文清理被宣称物理消除。SQLite删行不等于缩小文件，不自动VACUUM或gzip业务库。归档内容遵守既有脱敏约束，不导出Keychain或凭据。

## 接口和验证入口

受Session保护的 `GET /api/settings/storage` 展示目录/代次/方案/维护/策略；`POST /plan` 后台清点，`POST /logs/preview` 预览，`POST /logs/apply` 校验token后保存策略。未提供远程执行任意shell或一键切库接口。故障与兼容验证见 `test_storage_lifecycle.py`、`test_storage_api.py`、`test_log_retention.py`；输出包装器覆盖中文分卷完整性、退出码与信号回收，独立Browser验证设置保存/刷新。生产资料搬迁、真实模型/ASR和视频不是这些离线测试的组成部分。
