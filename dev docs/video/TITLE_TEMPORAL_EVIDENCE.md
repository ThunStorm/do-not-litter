# 标题时间证据与模型请求边界

## 标题时间来源

平台正式 `VideoAsset.title` 可作为 `TITLE_METADATA` 时间上下文，分享文案不进入此链路。解析版本 `title-temporal-v2` 保留原标题精确文本、月份/季节/旬/时段、period_type、intent、scope、scope_terms 和 confidence；标题不是 Transcript，不创建 Segment 或转写引文。v2识别暑假/寒假/暑期并保留假期原词，不猜月份；“月份”“宝藏”“到底”等修饰词不作范围，实际地域与观赏主题门禁仍保留。

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


## 地图展示补充（2026-10-20）

地图以统一时间判断过滤无时间语义的历史派生记录，仅改变读取投影，不改历史Evidence。明确日期范围从source_text保真展示；来源详情对不可用旧窗口显示待核实。新提取允许读取同一Mention已绑定且相邻的Segment拼接句子，保存全部原Segment ID与连续引文；不读取其他地点片段。NO_TIME_MENTIONED仅在完整转写与正式标题均无时间语义时记录，历史无窗口不自动补造此状态。无Schema迁移，未触发真实模型/视频重跑。


## 正文时间补证据（2026-10-29）

map-timing-v4统一候选识别与窗口验证的时间词；假期保持HOLIDAY精度与原词，不能自动命中月份筛选。新Mention用HAS_LOCAL_TIME/NO_LOCAL_TIME描述本地提取结果，NO_LOCAL_TIME不等于视频未提时间或全年适宜；旧状态和旧记录不回写。单主体Claim可读取独立于Mention地名片段的完整连续原句，须同Snapshot、输入转写顺序连续且逐字匹配；保存完整原Segment引用，不向Mention无差别扩展。相邻已归属片段拼句保留“去年”等历史修饰词，历史年份与客流高峰保持INFORMATIONAL。GROUND_MAP身份包含map-timing-v4和travel-semantics-v2；新增漂流活动语义。新增主题关系见下节。


## 作者推荐主题（2026-10-29用户确认）

GROUND_MAP semantic-map-v7-temporal-context在既有调用中读取连续正文主题候选；每包只携带当前激活的前置主题及本包主题切换，注册表中实际Segment使用既有短ID编译器，未提供的主题引用拒绝。实体temporal_applications必须有本ContentUnit的逐字成员依据，服务端复验主次角色、推荐意图、命名主体或唯一锚点、连续顺序、同Snapshot和主题切换边界。OPTIONAL保持可选，比较/背景/中转/整体否定不继承；不按共享Segment或地理包含广播。

Artifact.semantic_options_json保存版本化temporal_contexts/temporal_applications；新Mention保存经复验的关联和Artifact语义哈希。读取只使用Note版本的固定grounded_map_artifact_id并复核视频/转写/哈希与原句，旧NULL不猜绑。新增THEME_CONTEXT为只读投影，source_id/主题Segment及原句、成员原句、Note/version均可追溯；不物化为地点正文事实，不写入历史窗口。正文限制不会被主题覆盖；同用途、重叠时间的局部限制将主题降为条件性参考，观赏/活动限制不泛化为全地点关闭。

Place与Destination共用effective_windows；区域的本地时间也通过固定产物核验，区域浮窗/时间详情API、语义/月份季节筛选、聚合成员及v2导出复用结果。假期主题匹配暑期/寒假语义，避暑目的不生成月份；主题日历字段只取推荐时间原词，不从完整溯源背景中的日期提取。NOTE_REDUCE接收已验证关联并注明主题来源，不再次提取窗口结构。P2封面来源与P3真实模型/历史更新仍后置。


## 封面文字与真实案例重放（2026-10-29 P2/P3）

默认在Worker/CLI对受控本地原封面做macOS Vision OCR；API只入队或读已存证据。COVER_TEXT是独立视觉文字Stage，不复用截图身份，不从山水/衣着推断日期。`video:cover-text`支持enabled与visual_fallback_enabled，默认本地OCR开启、真实视觉兜底关闭；单次入队的allow_visual仍需用户选择。视觉必须显式配置支持图片的Profile，LOCAL_ROUTER现行契约拒绝图片，不能借目录声明绕过；可用Ollama图像Profile已有目标实测。

识别结果保留图片SHA256、原图ID、引擎/Swift脚本/预处理版本、逐行原文/置信度/区域、方法/用量/耗时与失败状态。视觉采用左上原点的命名四边坐标，程序严格转换为统一的左下原点bbox，不猜坐标制；低可信、多月份、超密文字、错误坐标或接口失败保留待核/回退，不阻塞正文。默认视觉关闭思考、单次尝试与输出/时限有界，OCR排队与子进程检查取消/截止时间，Worker不重置运行fence且终态释放lease。

提取身份包括封面字节、引擎/预处理/解析器、Profile与有效参数；成功/失败的语义内容也进入下游身份。成功证据保存不可变内容记录，失败缓存15分钟，JobStepArtifact独立保存；GET不重新OCR、调用模型或绑定旧结果。新封面、策略或可信内容变化生成不同结果身份，保留旧版记录。图片证据GET按所属视频与哈希核对，不能把旧文字指向已更换的新封面。

COVER_TEXT上下文仍须经过ContentUnit成员、主体与局部例外校验才成为THEME_CONTEXT投影；DTO同时标明来源COVER_TEXT并提供封面/区域追溯，不造Segment。模型遗漏的明确清单成员可按连续原句与唯一锚点恢复，保留derivation；原整体态度NEUTRAL不因此改成整体推荐。遗漏的局部时节否定以UNRESOLVED_LOCAL_SUBJECT保留原句待核，不升级为城市窗口。

`benchmark_cover_temporal.py`只在指定隔离库执行真实阶段验收或对显式指定的新Map做确定性重放；旧NULL不能猜绑。`temporal_replay.py`复核同视频/转写/内容哈希与封面归属，新建Artifact；投影更新可追加Note版本并复用相同事实源的已存模型正文，Section/Mention均换新身份，原版本保留，不能伪称新增模型输出。生产历史切换仍须明确授权并建立事务备份/回退材料。

接口：POST `/api/video-notes/{note_id}/cover-text?allow_visual=false`只排Worker任务并去重活跃任务；GET同路径分别返回当前Note已用证据和独立最新提取，不自动应用。GET `/api/video-covers/{cover_id}/evidence-image?content_hash=...`读取绑定哈希的原图。前端显示文字区域、当前/未应用新结果、适用地点和未归属的正文限制；模型来源与原句分开。


### 审查修复补充（2026-10-29）

小字号否定/限制不按字体过滤，无法明确归属保持NEEDS_REVIEW；冲突按实际日历交集而不是仅凭month空值判定，跨季节/日期范围不互相取消，假期不猜月份。OCR键排除未使用的视觉策略，视觉键只纳入推理相关字段，探测/显示名等运维信息不影响结果；下游内容身份不因未触发视觉的配置变化失效。force_regenerate保留显式重算，版本升级仍产生一次必要失效。Token共享表/精简投影尚属方案，见修复与Token分析。


### Note模型语义投影（2026-10-29）

每包Evidence Index可为{version,contexts,places}：同一context只定义一次，地点保留成员原句/Segment、relation与exclusions并引用context_id；机器追溯/图片区域保留在Artifact/UI。编译器接受旧列表与新注册表，未知/冲突引用拒绝。原始数据不因投影缩短而改写，当前主题和来源所需原句、用途、范围均保留。COVER_TEXT只称封面文字，不称正式标题/字幕；确定的月份误归因由校验拒绝。成功识别但语义待核按内容缓存，临时错误才走短期失败TTL。
