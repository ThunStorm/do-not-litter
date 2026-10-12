# AI 入口隔离与指定视频验收（2026-10-12）

样本：[BV1eAew6UEvG](https://www.bilibili.com/video/BV1eAew6UEvG)。用户授权全部已保存模型真实调用、视频工作流、必要备份重载和本地提交；测试顺序为Local AI Mux、官方DeepSeek、本地Ollama、免费/赞助入口。没有自动确认POI、修改原提交快照、删失败历史或推送。

## 根因与修复

原任务`job_3faa644874cf49e98a9dbfbcdddd4f8e`的官方DeepSeek校对不是供应商拒绝：35批先成功4批，续跑31批再成功4批，均被整个阶段的4次上限暂停。`3bebb50`加入阶段实际调用总计后，正常分批被当作重复尝试；同时v1仅模型名经验被Free SN DSv4F的真实4096输出截断收紧到96字符/1段，传到同名官方模型，造成批次爆增。

修复在共享Gateway和阶段调用处执行：单批尝试仍有界，阶段额度按计划批次计算，二分拆分增加叶子批次；每Job累计调用、Token和时间硬预算保留。经验v2、原始响应缓存和地图语义产物按实际Profile、Provider、Base URL、账户摘要、接口/生成/稳定性参数隔离，不借用v1。限时调用的超时只在请求内缩短，结束恢复，不改变下一批配置指纹。

新提交冻结当时设置；续跑保留原模型/路由身份，刷新同身份模型生成、上下文、超时、重试和稳定性参数。阶段参数只在当前仍属于原路由/模型池时刷新，显式任务覆盖保留；原提交与执行历史保留。系统默认重试不覆盖Profile，显式Stage重试仍优先；每阶段使用同身份模型最新已保存能力判定。

实测发现并修复地图问题：辅助空集合可缺省，核心entities/claims必需且逐项验证；提示允许合法空数组；本地输入块同时受输出容量约束，4096输出每块最多16段。Ollama原生format使用阶段JSON Schema（[官方结构化输出接口](https://docs.ollama.com/capabilities/structured-outputs)），防止9b遗漏claims；不为通过而补造证据。LOCAL_ONLY也禁止歧义复核借用全局远程模型，升级成功次数如实记录。

## 验收口径

每个视频为独立Worker Job；只覆盖三核心阶段选模并显式记录`allow_unverified_model=true`，不修改全局路由/声明能力、不把未验证小样写成PASS。ASR和媒体按真实生产流程执行；步骤续跑仅复用相同任务上游产物。连接测试与业务视频分别记录。PARTIAL_SUCCESS表示核心笔记交付并保留地点审核/非核心限制，不等于POI已确认或人工语义质量满分。笔记引文允许跨绑定段边界，以转写顺序拼接绑定段后检查逐字归属；不是按每个单段孤立检查。

本地测试与探测保留跨进程统一硬件串行及完成后至少5秒间隔，较长配置间隔/RPM取更长。本轮视频入口逐一串行，不用并发规避供应商配额；免费入口无法恢复的配额/失效凭据保留具体结果。

## 视频矩阵与质量边界

以下均为真实Worker视频任务。PARTIAL_SUCCESS保留地点待审/非核心限制；MODEL表示笔记全由有效模型响应生成，HYBRID含降级提纲，不能视为完整模型通过。全部已生成笔记的Segment引用、引文归属检查错误0，自动确认地点0。7b只有1节/1引文，覆盖较薄；没有人工Ground Truth评分。

| 保存配置 | 视频结果 | 节/引文 | 证据及限制 |
| --- | --- | --- | --- |
| Local Ai Mux / codebuddy/hy3 | PARTIAL_SUCCESS，MODEL | 11/13 | job_edf80633461446b8b948d7954e8b683d；底层实际供应商/Token用量不透明 |
| DeepSeek Flash Main | PARTIAL_SUCCESS，MODEL | 26/48 | job_5c654588de5d4e1187c8f2ebf225e90a；请求deepseek-v4-flash，响应标识deepseek-flash，不能独立证明版本 |
| Local Ollama / qwen3:8b | PARTIAL_SUCCESS | 20/22 | job_3935e52727454e2890a39e996303f128；早期歧义复核有1次官方远程成功，用户授权不再复验8b/7b纯本地 |
| Local Ollama fast / qwen2.5:7b | PARTIAL_SUCCESS | 1/1 | job_f693ad17d1f14f6390fec3adb0d6b551；早期1次远程歧义复核失败，核心本地调用完成，覆盖薄 |
| Local Ollama 3.5 / qwen3.5:9b | PARTIAL_SUCCESS，MODEL | 6/12 | job_1ecf4d1ec2d94da3a2782f0f2fbf8e2e；最终轮9次纯Ollama调用、结束后已卸载，无远程借用 |
| Free SN Flash | PARTIAL_SUCCESS，MODEL | 32/56 | job_2b75dffb19024d64a59e62ef887fbc14；关闭思考/4096/温度1.0真实完成，旧失败Job保留 |
| Free SN GLM | PARTIAL_SUCCESS，MODEL | 25/79 | job_bf5eb3669f5347efb87330f3724d7e4b；关闭思考/4096/温度1.0真实完成 |
| Free SN DSv4F | PARTIAL_SUCCESS，HYBRID，未完整通过 | 6/8 | job_890f93c9bc9c4776828ab0623f29f055；校对/地图完成，归纳按90秒间隔前两包成功、第3包被上游429拒绝，旧混合笔记保留 |
| OR Free | PARTIAL_SUCCESS，HYBRID，未完整通过 | 10/16 | job_408dde11d99348d8b6cd134dfb0b31f4；动态免费路由仍出现强制思考400、真实截断与无效JSON，已保留有界重试结果 |
| 赞助 / glm-5-turbo | NEEDS_USER，认证阻断 | — | job_6bcfed5a325044b894abfe6f405503a1；连接与视频均401 expired token，需有效新凭据 |

原受阻官方任务job_3faa644874cf49e98a9dbfbcdddd4f8e已续跑至PARTIAL_SUCCESS，33节/67引文、引用错误0。原提交快照及原12条审计逐项保持不变；恢复只完成剩余校对等阶段，没有借用免费入口的单批参数。

## 免费入口的有界优化与证据

连接测试与视频分别记录：Flash、GLM、OR连接完成；DS为上游TPM/RPM限制，赞助为令牌失效。商汤Flash/GLM旧4096和16384试验出现零正文且全部输出为reasoning；单纯扩预算无效。实际入口专属reasoning_effort=none后，4096输出/温度1.0完成地图及归纳，最终响应reasoning_tokens=0。真正正文截断仍按当前入口自适应拆分，不把思考耗尽当成普通截断反复拆分。

DS的关闭思考已在真实校对、地图、归纳前3包证实有效；2048/90秒地图完成。旧归纳首包429后41包确定性提纲曾被当作模型成功，本轮修复无有效AI章节时必须暂停；已生成部分AI章节则如实HYBRID，允许从归纳恢复，新版本不覆盖旧笔记。优化初始分包容量（2048从41包降11包）后，首3包完成，第4包429。审计发现实际第2、3包发起时间只相隔46.8秒：取消检查带来的预约晚到会压缩后续间隔，已补实际调用前的间隔复核和取消/墙钟检查；保护模式按同入口共享，DIRECT不受免费保护参数影响。

修复后长时间空闲的第一个DS剩余包仍得到上游429、provider_code=insufficient_quota、provider_type=rate_limit_error、message=inference exceeds tpm/rpm limit、无Retry-After；1536输出有界复验首包仍遭同样拒绝。不能以本地Circuit OPEN当作厂商熔断，最小7 Token输入、64/1536输出上限均成功，因此不能判定不可恢复厂商熔断。缩减归纳中重复的地点窗口枚举规则后，以同视频3条事实作诊断：输入723/输出973、思考0、finish=stop成功。归纳减少重复提取窗口结构，并删除与摘要重复的要点和空字段，保留全部不同事实、原文引文、来源ID及已验证地点窗口。最终业务首两包按90秒间隔完成，第三包输入更短仍上游429；说明小请求可用，但当前免费配额窗口无法稳定承载连续视频归纳。旧HYBRID笔记保留、未伪称完整成功。没有换账户、并发、隐藏重试或借官方模型使免费验收表面通过。

OpenRouter按[官方统一reasoning协议](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens)映射thinking=false为reasoning.enabled=false；只有openrouter.ai真实入口应用，未知兼容入口不发送该字段。其动态free路由和mandatory推理模型仍可能拒绝/忽略关闭思考，真实结果按审计记录。手动真实测试与能力探测在支持该参数的实际入口发送关闭思考，LOCAL_ROUTER按接口契约省略，避免未声明supports_thinking时探测漏发入口专属控制；不根据此开关伪造能力PASS。

最终保存参数：Flash/GLM输出4096/默认温度1.0；OR FREE_TIER且仅一次HTTP/JSON恢复；DS最终复验输出1408/默认温度1.0并保持90秒间隔。三核心Stage温度/重试继承模型，地图/归纳输出继承模型；官方DIRECT零重试/4096不变。硬预算48次/100000远程输出Token/1800秒没有扩大。新提交快照、同模型最新参数和每次执行历史分别保留。证据目录data/benchmarks/ai-entry-isolation-bv1eaew6uevg-20261012/受Git忽略，含提交、终态、Benchmark、调用审计、引用检查和UI截图；没有提交凭据。

## 官方 DeepSeek 最终回归

已按用户追加要求独立提交完整视频Job `job_b218748b83704374a698223c614e90c3`，用保存的官方 `DeepSeek Flash Main` 完成16/16个Worker步骤，终态PARTIAL_SUCCESS/CLEAN_CACHE、`note_generation_mode=MODEL`；3次校对完成，地图1次真正正文截断后拆分恢复并成功3次，笔记4次成功。全部11条LLM审计只指向官方Profile `model_1e6a087280e648a8840112a96a464c9a` 的主路由，无免费入口/备用借用。最终12节、41条逐字引文；Segment ID和绑定来源错误0，自动确认地点0。原始模型请求为 `deepseek-v4-flash`，响应标识 `deepseek-flash`，无法仅凭别名独立证明上游精确版本。PARTIAL_SUCCESS来自仍需人工审核的地点/非核心交付边界；语义准确率仍需人审，自动引用检查只证明来源归属。新提交时AI设置独立冻结；本Job在最终补修加载后运行，能证明整条链路已使用新代码。

## 表单验收

内置Browser在1095×876和390×844只读进入设置→AI模型→展开转写校对高级参数，确认“单批最多模型尝试”、温度/重试留空继承；模型卡显示默认温度1.0。页面身份、内容、无框架错误遮罩、相关console错误0、横向溢出0均通过；仅展开/聚焦控件，不提交表单或触发新模型调用。截图见忽略证据目录的`ui/desktop.png`、`ui/mobile.png`和`ui/model-mobile.png`。恢复浏览器尺寸并关闭代理临时页，用户原页保留。前端21项（含继承/显式零保存测试）、ESLint、类型及隔离构建通过；后端400项和新增入口协议、温度继承/上限、思考预算测试及Ruff通过。未通过项仍按各Job实际终态记录，UI验收不替代供应商/视频/人工Ground Truth验收。
