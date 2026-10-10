# AI 请求优化 A/B 记录

采样日期：2026-10-10。基线 SHA：`b365616fc3309ad48d1c5b24470a2ee8989bd1d4`。编译器 `stage-evidence-v1`，合成集 `request-synthetic-v1`。本记录比较同一合成输入的请求表示，不调用模型，不代表真实地点抽取质量或实际 Token 收益。

| 阶段 | 原请求字节 | 编译后字节 | 原输入估算 Token | 编译后估算 Token |
| --- | ---: | ---: | ---: | ---: |
| GROUND_MAP | 10568 | 7736 | 3288 | 1873 |
| TRANSCRIPT_CORRECTION | 26705 | 10493 | 9410 | 2806 |
| NOTE_REDUCE | 28297 | 23232 | 9494 | 7148 |

18 个合成场景（由 G-001～G-012 标签构造的输入，加价格/单位、月份/季节/排队/推荐菜、无地点、错音、速读、30 分钟跨块及末段）共 65570 → 41461 字节，减少 36.77%。校对去重、短 ID 与紧凑 JSON 为主要变化；Note Evidence Index 的重复 quote 仅在事实包已有逐字同值时省略。原文、否定、时间/数字单位、段落与尾段完整保留。

确定性门禁：18/18 ID 与原文往返一致；发送 Segment 覆盖与来源核验均为 1。两组没有真实模型响应，故 POI P/R、人工复核率、实际 Token、模型质量、时延、随机生成置信度全部为 `NOT_VERIFIED`，JSON 中保留 null。既有语义/POI Golden 单测另在全量后端回归中验证，不能与合成编译器往返混称模型质量通过。

复现：
```bash
"/Volumes/D/Library/Application Support/Zhijian/venv/bin/python" scripts/run_ai_benchmark.py \
  'dev docs/benchmark/video-semantic-poi-golden-v1.json' --request-optimization \
  --output 'dev docs/benchmark/AI_REQUEST_OPTIMIZATION_BASELINE.json'
```

真实配对 A/B：`NOT_RUN`。本工作包的 20%–30% 实测输入 Token 目标未验收；原 Gateway 毕业门禁的远程 Token 目标仍独立保留，没有用字节收益替代。

## 2026-10-10 15:56–15:57 真实模型调用小样（N=1）

代码 SHA `3bebb50`，请求型号 `codebuddy/glm-5.3`，实际上游型号 UNKNOWN。输入为本轮撰写的六段合成旅行说明，不是真实视频。保留当前 Prompt 与标准 OpenAI 路由；串行 1 次 Text、1 次原引用 JSON、1 次短 ID JSON，无重试或备用切换。

| 请求 | 耗时 | 请求 JSON 字节 | 输入 Token 估算 | 输出字符 | 解析 | 合法实体 / Claim / 单元 |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| Text smoke | 13.9s | 46 | 8 | 4 | PONG | 不适用 |
| 原引用基线 | 37.8s | 3534 | 1173 | 4371 | DIRECT_VALID | 5 / 8 / 3 |
| 编译短 ID | 30.4s | 3330 | 1071 | 3655 | DIRECT_VALID | 5 / 7 / 2 |

两次 JSON 的实体及 Claim 逐字 quote 有效率均为 1，全部六段发送。两个明确景点的语义召回、天津仅作参考的政策检查通过；实际 Claim 文本保留两处价格、月份、否定、春季、两道推荐食物和下午排队。基线另写一条天津参考说明 Claim/补充单元；候选保留该实体、逐字来源与参考政策，未单列该 Claim。分组与 claim_type 仍有生成差异，不能仅按条数宣称无损或真实视频质量通过。

本对 Ground Map 请求字节减少 5.77%，输入 Token 字符估算减少 8.70%；模型未上报可信 Token，20%–30% 实测目标仍 NOT_VERIFIED。temperature、max_tokens、response_format 被按目录省略，原生 JSON 模式/输出上限不支持；这次普通文本生成恰好直接返回了合格 JSON。N=1 且温度不受控，37.8→30.4 秒是观测，不是稳定性能结论。

脱敏结果与对应 Mux call_id/response_id 见 [真实小样记录](AI_REQUEST_OPTIMIZATION_LIVE_SAMPLE.json)。本机完整数值/哈希记录为 `data/benchmarks/request-live-20261010-155619/capture.json`，0600 权限，已被 Git 忽略；未提交 Prompt、密钥或原始模型正文。生产 Job、模型配置与 549 条 LLM Audit 的逐字段 hash 保持不变。该独立请求验收不替代 Worker/Replay/Note/POI 全流程。
