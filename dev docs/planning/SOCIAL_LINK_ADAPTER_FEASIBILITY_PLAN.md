# 多平台粘贴链接提取 Adapter 可行性与开发计划

调研日期：2026-10-23。状态：候选方案，未冻结、未实施。范围为抖音、小红书、YouTube、Instagram、X/Twitter 单条链接或分享文案导入；“等平台”以后通过同一契约扩展，不包含本轮新增平台承诺。本轮仅核对源码与公开资料，未登录平台、调用收费 API、下载样本媒体或运行真实 ASR/LLM。仓库已有其他在途修改，本计划不改变它们。

## 1. 结论与交付目标

可以建设统一入口，但不能承诺五个平台任意链接均可自动提取全文、字幕和视频。推荐“平台适配 + 能力分级 + 可行动降级”：官方接口有合适权限时优先使用；公开网页只提取实际可见且身份匹配的内容；需要登录、权限或素材时明确等待用户补充。第三方解析服务与浏览器会话接入独立评估，不作为默认依赖。

先冻结三档目标，分别验收，不能相互冒充：

| 档位 | 输出 | 完成条件 |
| --- | --- | --- |
| 预览 | 平台、标准链接、内容 ID，以及实际取得的标题/作者/封面/时间 | 每字段有来源；缺失保留空值；仅有预览不启动正文总结 |
| 正文 | 帖子文字、图文顺序、图片引用、来源定位 | 能区分完整、截断、仅摘要；页面导航、登录提示不作正文；图片 OCR 单独标记 |
| 视频证据 | 人工/自动字幕，或授权媒体经 ASR 得到的转写 | 通过现有字幕质量与时间码门禁，保留 raw/corrected 身份；有标题不代表拿到视频内容 |

第一版仅支持单篇内容，不扩展搜索、主页批量抓取、评论、私信、直播、付费/私密内容、整条讨论串。平台帖子的文字说明与视频实际内容分别标注，不能用说明替代转写。旅行以外内容可保存来源与正文，但不因此扩展当前招聘/旅行 Processor，也不自动生成 POI。

## 2. 平台判断与证据

以下“可行性”是基于文档和源码的工程判断，不是本机成功率实测。

| 平台 | 可行性与首选路径 | 边界与建议 |
| --- | --- | --- |
| YouTube | 高：复用现有 yt-dlp Adapter；官方 Data API 可作为元数据候选，字幕/媒体单独判断 | 官方字幕列表不含正文且需要 OAuth；下载字幕不能当成任意第三方视频的开放接口。yt-dlp 受站点变化及 PO Token 等条件影响。优先完善现有路径，保留用户上传字幕/媒体 |
| X/Twitter | 高（具备开发者凭据及预算）：按 Post ID 调官方 lookup，按字段请求文字、作者与媒体 | 解析 x.com/twitter.com 身份别名；长文、引用和编辑版本要保留边界。只获取当前帖子，默认不扩展线程。媒体引用可得不等于可下载或已转写 |
| 抖音 | 中（公开页面试验）；授权账号自身内容有官方接口路径 | video.data 等需要权限及用户授权，不能据此承诺解析任意分享链接。公开页、短链与媒体解析须样本验证；登录/验证挑战时停止并提示补充 |
| 小红书 | 中低（任意公开笔记自动提取）；人工导入可交付 | 本次查到开放平台、账号授权接口，未找到足以承诺“任意笔记 URL → 全文/图片”的通用官方契约；这不是断言平台不存在其他合作能力。图文顺序、展开全文、分享参数与登录态是主要验证项 |
| Instagram | 中（授权专业账号内容）；任意公共帖子全文承诺低 | 官方 Instagram Login 面向 Business/Creator；Facebook Login 路径不能访问普通消费者账号。oEmbed 作为预览候选，不等价于正文或媒体下载 API；本次官方 oEmbed 页面未能读取，其当前权限条件留待验证 |

主要一手资料（实施前复核权限、版本和配额）：

- [YouTube captions.list](https://developers.google.com/youtube/data/reference/rest/v3/captions/list)：返回轨道列表，正文需另行下载，要求授权。精确下载权限须在技术验证时再次核对。
- [yt-dlp 支持列表](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)：项目明确提示，列出 extractor 不保证当前可用；[PO Token 指南](https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide)说明部分 YouTube 客户端请求的额外条件。采用时固定版本，不自动安装未知插件。
- [X Post Lookup](https://docs.x.com/x-api/posts/lookup/introduction)：按 ID 获取帖子、关联对象和编辑历史；[X 官方计费](https://docs.x.com/x-api/getting-started/pricing)：查询日为按量预付费，帖子读取 $0.005/资源，用户读取 $0.010/资源。只读 1,000 个帖子约 $5，不含作者等关联资源及其他费用；以控制台当期计费为准，配置硬预算与缓存。
- [抖音视频数据](https://open.douyin.com/platform/resource/docs/openapi/video-management/douyin/search-video/video-data/)、[基础数据](https://open.douyin.com/platform/resource/docs/openapi/data-open-service/video-data/get-basic-data/)：前者声明申请权限和用户授权，后者明确仅查询 token 对应用户上传的视频。
- [小红书开放平台](https://open.xiaohongshu.com/)、[账号 API 参考](https://openaccount.xiaohongshu.com/docs/api-reference)：当前检索证据覆盖平台入口及账号授权，不证明通用笔记提取能力。
- [Meta 官方 Instagram API 工作区](https://www.postman.com/meta/instagram/overview)、[Instagram Login](https://www.postman.com/meta/instagram/folder/6raa77c/instagram-api-with-instagram-login)、[官方 API 集合](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api?entity=request-23987686-af579d08-121e-4897-8f45-5fd41ace49df)：区分专业账号权限与普通公开链接；[oEmbed 待复核入口](https://developers.facebook.com/docs/instagram/oembed/)。

## 3. 仓库现状与直接缺口

本节依据当前工作树源码，未核对生产版本。

- `services/input_normalizer.py` 已支持分享文案提取，但无协议域名和多候选专用优先规则主要针对 Bilibili；不能简单追加几个域名就认定完整接入。
- `services/capture.py`、`services/pipeline.py`、`resolvers/video/adapters.py` 分别存在平台判定/分派，当前视频集合为 BILIBILI、LOCAL、YOUTUBE；新增平台要集中路由，避免注册成功却未进入正确 Pipeline。
- `resolvers/video/youtube.py` 已用 yt-dlp 获取元数据、字幕轨道和时间链接，当前不使用 Cookie。代码允许选 `srv3`，但读取仅走 VTT 解析，应补格式分流或只选择已支持格式，并增加回归。域名匹配还需收紧为单视频路径，拒绝主页/列表。
- `services/resolver.py` 的通用 HTML 提取会遍历非 script/style 的文字，缺少社交正文完整性判定；已识别社交域名失败时不能继续把登录提示页当作成功正文。
- 现有 `Source/Snapshot/Segment/Evidence` 支持来源与段落定位，可复用；`ResolvedVideo` 仍有 bvid/aid/cid 等 Bilibili 命名，YouTube 已把 video_id 放入 bvid。新图文不能伪装为视频；平台无关身份映射须单独明确兼容策略。

## 4. 建议架构与契约

流程：粘贴 → 本地识别/脱敏 → Capture 入队 → Worker 短链解析与抓取 → 统一结果 → 正文或视频分支 → 既有 Evidence/Processor。API 内不联网解析短链、不下载媒体、不跑模型。

建议新增 `LinkSourceAdapter`，现有 `VideoSourceAdapter` 作为视频能力桥接，避免复制下游流水线。统一注册表提供 `match`（纯本地）、`resolve`（Worker）、能力声明、版本及错误映射。结果建议包含：

| 字段组 | 契约 |
| --- | --- |
| 身份 | platform、platform_content_id、canonical_url、content_kind、adapter_version；按平台+内容 ID 去重，跨平台不合并 |
| 内容 | 可空 metadata；有序 text/image/video blocks；每块 origin、snapshot_ref 和 locator；不把 API caption 字段误称为视频字幕 |
| 能力 | metadata/text/images/subtitles/media 分别标 AVAILABLE、UNAVAILABLE、REQUIRES_AUTH、UNKNOWN；不能一个 supported 布尔值包办 |
| 完整性 | 每能力记录 FULL、PARTIAL、PREVIEW_ONLY 或 EMPTY、原因和缺失项；与现有 JobStatus 分开，不新增虚假终态 |
| 证据 | paragraph/字符范围、image_index/OCR 区域或真实 time_range；生成内容不得成为原始证据 |
| 运行 | 脱敏诊断、可重试性、恢复动作、限流等待、请求数/字节/耗时；不得保存 token、Cookie 或带签名媒体地址 |

预览与正文提取应能在没有 LLM 配置时完成，不沿用当前“所有视频导入先校验模型接口”的硬绑定；用户选择生成笔记时才进入已有模型配置快照与能力门禁。只有正文充分时才允许总结；不完整时显式提示覆盖范围。没有时间码的图文只链接原帖，不生成假的 `t=` 时间锚点。

短链与安全约束：逐跳 HTTPS、许可 Host、标准端口、无 URL 凭据，禁止跨域转发认证；校验 DNS/IP 防止内网/回环/重绑定访问，对页面、图片、字幕、CDN 分别设策略。限制跳数、请求数、响应大小、媒体时长与总墙钟；取消可中断网络和子进程。yt-dlp 的内部请求也须纳入网络边界，不能仅校验初始 URL。

分享 URL 中可能带访问相关参数：标准身份与抓取定位分离；去掉追踪参数前验证不影响访问，敏感定位参数仅以 SecretStore 引用暂存，不原样进入 Source.locator、Job、日志或导出。原分享文案也先脱敏再落库。保留内容证据快照时移除脚本、凭据和敏感字段，不保存整个登录页；抓取文本视为不可信数据，不执行页面指令。

首期尽量用已有元数据字段与 Artifact 引用，先做字段映射评审。确需新增平台身份索引、图文 Asset 或认证引用表时新增 Alembic migration，禁止改旧迁移/历史证据；迁移和生产执行另行授权。

## 5. 分阶段开发计划

以下为一名熟悉仓库工程师的粗估人天，不含平台审核、等待凭据、外部服务变化和真实模型验收；每阶段独立交付，不表示本次已获实施授权。

| 阶段 | 工作包与出口 | 估算 |
| --- | --- | --- |
| P0 契约与技术验证 | 确定字段、官方账号条件、合法可访问样本；按平台验证元数据/正文/媒体分别可得；输出 go/no-go 及固定依赖版本 | 2–3 |
| P1 公共入口 | 统一识别注册表、短链安全、结果/错误契约、能力与完整性、Worker 路由、人工补充；Bilibili/Local 不回归 | 3–5 |
| P2 YouTube | 复用并收紧路径、字幕格式、语言/自动轨道门禁、超时取消与媒体失败降级；不保证免登录媒体全覆盖 | 2–3 |
| P3 X | 官方单帖 lookup、正文/媒体关系、长文与编辑身份、缓存/预算/限流；无凭据时仅保留来源与补充入口 | 2–4 |
| P4 抖音/小红书 | 分别限时验证公开页，再决定发布实验能力或仅提供手工素材路径；不把逆向签名维护作为默认路线 | 4–8 |
| P5 Instagram | 专业账号官方路径与公共预览分别评估；OAuth、权限回收和过期恢复；普通账号全文不纳入保证范围 | 3–5 |
| P6 产品与集成验收 | 共用导入结果/缺失项/恢复动作 UI，PC/Mobile，数据兼容、取消、缓存、证据链及发布回退验证 | 3–5 |

全部范围约 19–33 人天；建议首个交付包仅 P0–P2，加 P6 中相应验收，预算约 9–14 人天。X 可在凭据/预算明确后接续；若中文旅行资料优先，可将 P4 的样本验证提前，但不因此提前承诺稳定提取。浏览器辅助接入及付费第三方解析服务不计入上述预算，另立方案评估运维、凭据托管、数据保留和服务可替换性。

平台验证限定时间：单平台最多 2 人天探索；若仍依赖不可持续挑战处理或拿不到稳定正文，则交付“预览/待补充”，暂停该自动提取能力。遇到登录/验证码提示用户正常登录或提供素材，不无限重试。

## 6. 验收与发布门禁

1. 离线：每平台覆盖标准链接、短链/分享文案、追踪参数、多个候选、重复/编辑、私密/删除、登录页、429、超时、取消；加入恶意跳转、伪域名、敏感参数泄漏测试。Capture 网络调用必须为零。
2. 内容：全文与页面原文逐段核对；图文顺序、作者、发布时间和未知值正确；未抓取的图片文字不能声称已读取；OCR 保留来源及不确定性。平台正文与 ASR 分开，所有输出引文均能回到 Snapshot/Segment。
3. 视频：人工/自动字幕、无字幕、格式异常、媒体失败分别验收；覆盖单视频 watch/shorts/youtu.be 等形式，列表/主页不误入；无字幕且媒体不可得必须给出缺失状态，不生成空内容笔记。
4. 授权后真实读取：每平台至少 10 条可访问正样本（含相关内容类型、长短链接）及 5 条受限/错误样本；至少两个不同日期复验。建议自动能力发布门槛为正样本 ≥90% 达到其声明档位，受限样本无虚假成功、安全/身份/证据硬门禁 100% 通过；不足则缩小声明范围。该小样本门槛不代表全站成功率。
5. 真实读取报告分开列预览、正文、字幕、媒体成功率与完整度、P50/P95、费用和登录依赖；预览成功不能计为正文成功。真实 ASR/LLM/视频重跑仍需专项授权，不因 Adapter 测试自动触发。
6. 开发先跑目标测试，代码工作包末各跑一次全量后端/前端；UI 改动按设计系统并做 PC/Mobile Browser。发布按现有安全门禁、源码保存点/静态备份/哈希与生产 Browser 验收执行；迁移、真实模型调用、提交推送不包含在本计划授权内。

## 7. 开发前需冻结的选择

默认建议：单用户本地、单篇内容、公开可访问范围、先预览/正文后视频证据；接受“需要补充素材”作为诚实降级。实施前只需明确首包平台顺序、是否具备 X/Meta/抖音应用权限及费用上限、是否将浏览器授权会话纳入后续范围。没有这些条件仍可完成公共契约和离线实现，但不能宣称完成对应平台真实验收。
