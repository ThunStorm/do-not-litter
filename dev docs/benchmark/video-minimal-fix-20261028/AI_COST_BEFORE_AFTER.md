# AI用量对比
新增业务LLM/ASR/高德真实调用=0，真实视频重跑=0；无新增阶段、逐地点校验、Prompt/缓存键失效。V07仅持久固定ID，读取不调用模型。

|同fixture代理测量|旧版|新版|
|---|---:|---:|
|第2轨合格：字幕fetch|1|2|
|第2轨合格：ASR入口|1|0|
|前3轨失败、第4轨合格：字幕fetch|1|3（不访问第4轨）|
|前3轨失败：ASR入口|1|1|
|上述路径到校对边界：LLM|0|0|
|截图Replay：额外LLM|0|0|
|已有GroundMap/两种笔记生成Mock：Provider总调用|5|5（固定引用断言通过）|

证据：cost-before.log、cost-after.log、test_grounded_map原5次断言及最终全量。字幕fetch为HTTP代理，适配器每轨一次HTTP；metadata/封面不计字幕请求。真实reported input/output Tokens=null、usage_source=unknown、NOT_MEASURED_REAL_COST；不声称节省百分比、完整视频耗时或真实缓存率改善。生产审计前后保持由保存点逐表哈希核验，不以服务健康推导模型质量。
