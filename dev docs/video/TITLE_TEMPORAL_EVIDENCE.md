# 标题时间证据与模型请求边界

## 标题时间来源

平台正式 `VideoAsset.title` 可作为 `TITLE_METADATA` 时间上下文，分享文案不进入此链路。解析版本 `title-temporal-v1` 保留原标题精确文本、月份/季节/旬/时段、period_type、intent、scope、scope_terms 和 confidence；标题不是 Transcript，不创建 Segment 或转写引文。

只有明确推荐、PRIMARY/SECONDARY 且 RESOLVE/AREA_RESOLVE 的已有转写地点可继承。行程/记录、含混多时间子句、未知或否定推荐、限制标题、比较/背景、用户拒绝均不产生标题推荐窗口。特定地点标题须命中该地点名；主题标题的残余范围词须由地点证据或省市提示匹配，红叶/赏花等主题须有该地点的相应证据。正文月份、季节、时段或限制优先；冲突/正文优先原因保存在 `PlaceMention.metadata_json.temporal_context` 的 status 与 conflict_recorded，来源 ID 另存 temporal_source_id。保守拒绝可能降低召回率，不能凭常识扩展范围。

解析在新提取/重放时运行。Ground Map semantic_hash 包含 normalized_title、完整标题上下文哈希与 parser_version；标题变化不能复用旧 Artifact。当前 Map Prompt 为 `semantic-map-v3-title1`；旧 Artifact/Note 不回写。

## 物化与展示

通过校验的投影物化为 `PlaceVisitWindow.provenance=TITLE_CONTEXT`，source_id 指向视频来源、source_text 保留标题原文、segment_ids 为空；SOURCE_FACT 仍为正文证据。DTO 返回 source_id 与 source_kind，推荐理由和地点详情区分“来自视频标题”/“正文原句佐证”。标题不写入正文 Insight 聚合，不能被计为多正文来源 CONSENSUS。

派生窗口按 `place_id + source_id + mention_id + provenance + period_type/suitability + season/month/month_segment/day_time_slot + source_text_hash` 对账；重复调用保持窗口 ID，地点重新绑定时只迁移派生窗口，过期投影只删除对应 SOURCE_FACT/TITLE_CONTEXT。人工窗口及状态保留；两个来源类别均禁止用户删除。无 Schema 变更，不对生产历史批量补算。

NOTE_REDUCE 仅接收当前分包地点的已验证标题上下文；摘要/fallback 按地点名追加时间与标题来源。标题文本不得出现在 supporting_quotes 中冒充语音原句，原逐字 Segment 守卫继续生效。

## 地点归属与请求投影

Semantic Claim 先按 subject_entity_ids 对应 Mention，再以 ContentUnit 辅助；明确但无效的 subject 不回退到 Segment 广播。无 subject 时仅在相同单位/Segment 内唯一地点可补关联，多个地点保持无关联。共享 Segment 的正文时间仅由具名、无其他地点的子句或单一 subject Claim 分配，不能把每条时间分给全部地点。

canonical Mention/Segment/Note ID 及外键保持原值；普通页面不显示随机 ID，模型边界复用 request_compiler 的短 ID 并还原。Evidence Index 只包含当前包实际 mention/Segment 和相关引文，正文事实保留 ContentUnit。多地点场景保留模型显式 mention 输出与严格还原；不为节省几个 ID 冒险省略。

## Prompt 与观测

每次分片都发送完整无状态系统规则。顺序为任务守卫、稳定补充指令、当前分片领域上下文、动态正文。已有 Domain Pack 相关术语/示例投影继续使用；不删安全规则、不静默截掉转写后段、不新增会话或缓存服务。

request_metrics 增加 metrics_version、prompt_fingerprint、static_prompt_fingerprint、static_prefix_chars、dynamic_body_chars、raw_request_bytes 与 request_bytes_scope；保留 system_chars/domain_chars、估算 Token 和请求数。Provider 实际 payload 与合成 messages JSON 字节范围明确分开，耗时仍使用现有审计 duration_ms/provider_ms/queue_ms。日志只保存数字/哈希，不能保存 Prompt/证据全文。

应用命中记 `APP_RESULT_CACHE_HIT`，不生成当前上游 cached_tokens；可信非负整数 cached_tokens 或 prompt_tokens_details.cached_tokens 大于零才记 `PROVIDER_PREFIX_CACHE_HIT`，否则 UNKNOWN。UNKNOWN 入口不得借历史 usage 宣称节省订阅配额。真实缓存、计费与质量必须由授权的同模型配对 A/B 证明；原生会话/resume 实验尚未启动。

验证与度量入口：[离线 A/B 报告](../benchmark/TITLE_TEMPORAL_PROMPT_AB_REPORT.md)、`backend/tests/test_title_temporal_evidence.py`、`scripts/benchmark_title_temporal.py`。当前通过数只维护在 [实施状态](../IMPLEMENTATION_STATUS.md)，生产现场只维护在 [交接](../CURRENT_HANDOFF.md)。
