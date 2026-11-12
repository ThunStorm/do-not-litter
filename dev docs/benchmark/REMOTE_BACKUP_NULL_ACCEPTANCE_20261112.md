# 远程备用与嵌套列表恢复验收（2026-11-12）

## 范围与验收

用户要求查明两个失败任务，修复并真实验证；确认REMOTE_ONLY只限制位置，已配置备用也是远程时应生效。验收：不再以裸TypeError结束列表错误；结构错误有安全字段定位并进入原有有界恢复；允许合格远程备用但不跨入本地；保留原任务身份、Evidence、既有执行时限和累计调用/Token预算，串行续跑两项失败任务。无迁移或手动POI确认；发布及真实验收完成后，用户另授权本包文档更新和远程提交。

## 已确认的原因

两任务11月12日11:33、11:48在EXTRACT_TRAVEL_FACTS第2/6、2/7块失败。响应审计均DIRECT_VALID，已完成ID解码，但后续遍历列表遇None，转成AI_PROVIDER_RESPONSE_INVALID。失败响应未保留正文和异常栈，无法确定原始null字段；用部署代码对recommendation_evidence.statements[].supersedes=null离线复现同异常。旧REMOTE_ONLY分支强制清空fallback_id，因而通用配置中的codebuddy/hy3远程备用未参与；不是超时或配额错误。

## 实现与离线证据

structured_output先检查Ground Map语义及兼容投影内实际消费的列表与嵌套statements/supersedes；错误容器不静默归零，返回AI_PROVIDER_SCHEMA_INVALID及固定字段路径。structured_ids注册安全诊断字段，json_recovery明确要求空数组而非null。REMOTE_ONLY仅保留同位置合格的通用备用，其余模式及歧义升级不变。非结构异常不新增自动重试。

初轮含既有未提交修复的工作树后端全量944项通过；排除无关修复及其测试的确切提交候选后端全量902项通过，候选源码与线上逐文件一致。前端64项和生产Python3.14目标45项通过；Ruff、格式、diff、类型和隔离构建通过。零真实模型的合成测试覆盖JSON纠错0/1后切备用、备用原始证据完整、无备用/尝试预算阻止额外调用、错误响应不缓存、成功缓存复用，以及远程模式不选本地或禁用备用。

## 发布

基于11月9日线上运行副本隔离，仅4个后端文件与设置说明增量，保留其他未发布工作树修改。保存点见CURRENT_HANDOFF生产快照，含工作树tar/patch/哈希、验证过的SQLite逻辑备份、原plist、旧静态及新旧HTTP哈希。发布前无活跃Job/lease/在途调用；发布后0027未迁移、integrity=ok/FK0、业务摘要不变，仅新增两条服务启动事件，API/Worker READY。1280/390px生产浏览器核对说明、无横向溢出/错误覆盖层/相关控制台错误；Browser插件不可用，使用本机Edge Playwright，只允许GET及两项只读POST（预算预览/凭据状态）。

## 真实验收结果

按顺序续跑job_795ddb6ed717418c831423d1f2d94953、job_5feeb5abef9b40d4bf89567217df6ba1；通过正式retry-from-step接口从EXTRACT_TRAVEL_FACTS开始，复用已完成上游。使用原快照中的qoder/Qwen3.8-Flash和codebuddy/hy3身份；参数按既有续跑规则刷新同身份模型可调参数。生产续跑仅在自然主模型失败或既有剩余时限选路条件满足时进入备用分支；补充故障注入严格在隔离数据库中执行。


### 两项生产任务

| Job | 终态 | 章节 / 截图 | 事实 / 有证据表示 | 地点待确认 | 内容质量待核 |
| --- | --- | --- | --- | --- | --- |
| job_795ddb6ed717418c831423d1f2d94953 | PARTIAL_SUCCESS | 20 / 12 | 56 / 56 | 8 | 7 |
| job_5feeb5abef9b40d4bf89567217df6ba1 | PARTIAL_SUCCESS | 9 / 9 | 84 / 84 | 13 | 11 |

两项全部步骤COMPLETED/REUSED，确认地点均0；Note/Version/Grounded Map身份与真实产物入口记录在保存点real-final-summary.json。PARTIAL_SUCCESS保留地点待确认；质量摘要还保留作者态度/证据待核，generation_mode=UNKNOWN、summarized_fact_count未提供，不把有证据表示冒称完整模型摘要覆盖或内容金标验收。

第一个任务真实触发了 `$.entities[0].recommendation_evidence.statements[0].supersedes` 非列表错误，现返回AI_PROVIDER_SCHEMA_INVALID并在一次纠错后成功，未再出现NoneType崩溃。新响应具体类型未记录，不能据此确定原始两次故障的字段/原值。

第二个任务首轮多次JSON纠错后用尽1320秒阶段时限，在最后一块的远程备用分支停为NEEDS_USER。该备用记录remote_execution_state=UNKNOWN，不能断言未派发或未消耗；不是一次已验证成功的备用响应。正式续跑核对前6块成功响应均有缓存，实际新请求直接进入第7块，随后9包笔记归纳全部成功。未调大任何生产预算；沿用正式Replay的执行时间窗规则及累计调用/Token门禁，未重做ASR或校对。

生产新增LLM尝试记录38条：28成功、8次JSON语法错误、1次列表Schema错误、1次阶段时限失败。其中37条primary，1条fallback；失败时限记录的实际上游执行未知。审计时长合计约3026秒，包含失败/等待，不是计费时长。上游未提供可信Token用量，不能将步骤中的0当作免费，也不估算账单金额。保留original_result_hash、恢复血缘和历史错误事件，详见real-attempt-summary.json。主模型的JSON稳定性与耗时仍有局限，本包不改变用户模型选择。

### 隔离的故障注入与真实备用验证

采用数据库副本和原Job快照，用生产选路代码选择qoder/Qwen3.8-Flash与codebuddy/hy3。仅在隔离进程注入主模型supersedes=null输出，将该测试的主模型纠错次数设为0，再向真实远程备用发送一个无业务资料的最小JSON协议请求。最终主路由AI_PROVIDER_SCHEMA_INVALID → fallback COMPLETED，真实备用约6448ms返回，Request ID `req_2e9a7460f68147bebf1f21b396d5c771`；响应SHA256及终态审计在backup-smoke-result.json和backup-smoke-isolated.db。这证明选路、结构错误分类及真实备用连通性，不代表自然主模型失败后的完整旅行事实质量金标通过。

测试准备阶段一次因system-only消息在本地被接口契约拒绝（未发请求）；随后真实备用约21607ms成功，但后台进度会话误用默认测试库，出现缺表异常。修正隔离SessionLocal绑定并启用副本WAL后再进行上述6448ms干净复核。合计补充2次已成功返回的真实备用调用，另有合成主失败及本地拒绝；全部副本审计与日志保留，不混入生产Job。前后生产两Job的38条LLM尝试记录数量不变，生产设置未保存变更。

### 最终现场与限制

最终采样 2026-11-12 21:17（北京时间）：API/Worker/SQLite正常、执行器IDLE，active Job/lease及在途调用0，SQLite仍0027、integrity=ok/FK0，Worker心跳新鲜。原有2754条Segment的身份/正文/校对/时间定位及32份转写身份/正文保持，无删除或改写。两项仅生成对应的新笔记版本与下游产物，不确认POI。保存点包含代码回退脚本（仅回退运行代码与静态，不恢复旧业务库）。部署及真实验收时尚未提交；后续交付范围和核对记录见下节。

## 提交前复核与交付

2026-11-12 21:42（北京时间）只读复核：API/Worker/SQLite正常、执行器IDLE、无活跃Job/lease，心跳新鲜，SQLite完整性ok/FK0、仍为0027；两任务仍为PARTIAL_SUCCESS，人工待核项保留。候选提交的全部backend/src和frontend/src与已部署副本逐文件一致；不含工作树既有的资源删除/保留、日期区间修复及其测试，也不纳入这些改动的状态段落或生成文档。仅提交本包14个文件，沿用同一分支 `codex/mac-mini-implementation`。最终提交哈希、远程对齐结果见该分支Git记录及保存点 `delivery-result.json`。本次不重启服务、不重跑视频或调用模型。

交付复核补充：候选后端全量902项退出0；Ruff及文档生成/链接相关5项检查通过。前端全部源码及package/lock/Vite/TypeScript/ESLint构建输入与已完成64项测试、类型、隔离构建及生产1280/390px验收的部署副本完全一致，未重复执行无变化的前端验证。原工作树944项结果作为更大混合工作树的补充证据，不作为本次提交的测试数量。
