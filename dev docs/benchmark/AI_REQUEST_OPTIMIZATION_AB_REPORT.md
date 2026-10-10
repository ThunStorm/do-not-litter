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
