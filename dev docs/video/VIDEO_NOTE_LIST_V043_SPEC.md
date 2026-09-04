# Video Note List v0.4.3

> 状态：已实施；后续回归受 `REGRESSION_AND_CHANGE_GUARD.md` 保护
> 更新日期：2026-08-24
> 适用页面：`/video-notes`
> 参考实现：[lanyeeee/bilibili-video-downloader](https://github.com/lanyeeee/bilibili-video-downloader)，审阅基线 `1254c6bf2a09a590163091e67651bfc9942171e2`

---

# 1. 目标

本次只返工视频笔记列表页的两个问题：

1. 顶部操作按钮文案、字号和尺寸符合现有设计系统；
2. 每条视频笔记下载并展示真实视频封面，不再长期显示通用场记板占位。

本文件不授权直接实施。

---

# 2. 顶部操作按钮

## 2.1 文案

“投递视频链接”改为：

> **添加视频链接**

原因：

- “投递”偏系统术语，不符合普通用户表达；
- 页面已经说明系统会把视频整理成笔记，按钮只需说明下一动作；
- 文案更短，PC/Mobile 都不容易换行。

## 2.2 视觉规格

按钮复用项目统一 `.button.button--primary`，不得单独创建超大红色按钮：

```text
height: 40px
padding-inline: 16–18px
font-size: 14px
font-weight: 600
icon-size: 16px（可选 Link/Plus 图标）
border-radius: 使用全局按钮 token
white-space: nowrap
```

PC：位于介绍卡右侧，宽度由内容决定，与介绍卡垂直居中。Mobile：介绍文字与按钮分行，按钮可占满内容宽度，但高度和字号不放大。

状态：hover、focus-visible、active、disabled 使用统一 Button Token；不能使用浏览器原生样式、内联字号或局部特殊圆角。

---

# 3. 封面来源

## 3.1 元数据优先

Bilibili Resolver 从视频元数据保存：

```text
VideoAsset.cover_url
```

普通视频通常来自 Bilibili `view` 数据的 `pic` 字段；分 P 默认使用所属视频主封面，未来若平台提供独立分 P 封面再覆盖。封面 URL 不由 LLM 推断。

## 3.2 参考实现

参考仓库的做法：

- `normal_info.pic / episode.cover` 作为 CoverTask URL；
- `ensureHttps` 把 `http://` 转成 `https://`；
- `BiliClient.get_cover_data_and_ext` 发起 GET；
- 检查 HTTP 200；
- 根据 `Content-Type` 识别 PNG/WebP/AVIF，其他图像回退 JPEG；
- 读取原始 bytes 并写入本地文件；
- 列表展示使用 `@672w_378h_1c.webp` 等 16:9 CDN 变体。

至简只借鉴封面 URL、HTTPS、响应校验、Content-Type 和本地写入方法，不复制其 Tauri/Rust 任务系统。若未来直接移植实质源码，必须在 `THIRD_PARTY_NOTICES.md` 加入其 MIT 声明和参考 commit。

---

# 4. 至简封面处理流程

```text
FETCH_METADATA
→ FETCH_COVER
→ VALIDATE_COVER
→ STORE_COVER_ORIGINAL
→ GENERATE_LIST_DERIVATIVE
→ MATERIALIZE_VIDEO_NOTE_LIST
```

## 4.1 FETCH_COVER

- 将协议相对或 HTTP URL 规范为 HTTPS；
- 只允许 Bilibili 已知图片 CDN host，例如受配置 allowlist 管理的 `*.hdslb.com / *.biliimg.com`；
- 请求携带合理 User-Agent 和 Bilibili Referer；
- 限制重定向、超时和最大字节数；
- 不因为元数据含 URL 就绕过 SSRF 检查；
- 下载失败不阻塞 AI Note，记录 `COVER_UNAVAILABLE` 并使用占位图。

## 4.2 VALIDATE_COVER

- HTTP 状态必须为 200；
- `Content-Type` 必须为允许的 `image/jpeg / image/png / image/webp / image/avif`；
- 文件头必须与 MIME 一致；
- 图片可解码且宽高合理；
- 拒绝 HTML、SVG、超大文件和 0 字节响应；
- 原始内容使用 SHA-256 去重。

## 4.3 本地存储

```text
data/permanent/video-covers/<sha256>.<ext>
data/permanent/video-covers/derivatives/<sha256>-672x378.webp
```

原始封面按内容哈希永久保存，列表衍生图可重建。不同 Note/Version 引用同一 VideoAsset 时复用封面，不重复下载。

列表 API 返回本地受控图片 URL，不直接长期热链 Bilibili CDN。图片响应使用内容哈希 ETag 和 immutable Cache-Control。

---

# 5. 列表卡封面布局

```text
aspect-ratio: 16 / 9
object-fit: cover
desktop width: 184–200px
border-radius: 使用 Card token
background: 当前 paper placeholder token
```

- 封面填满当前左侧缩略图区；
- 时长徽标保留在右下角，不遮挡重要主体；
- 图片 alt 使用视频标题；
- 图片 lazy-load；首屏第一张允许 eager；
- 加载时使用低对比 skeleton；
- 下载失败才显示现有场记板占位，并提供不打断阅读的“封面不可用”语义；
- 封面点击行为仍属于整张 Card 导航，不新增独立下载动作；
- PC/Mobile 保持 16:9，不拉伸、不使用 contain 留大面积空白。

---

# 6. 数据模型

推荐新增 `video_cover_assets`：

```text
id
video_asset_id
source_url
local_path
derivative_path
content_hash
content_type
width
height
byte_size
status
error_code
fetched_at
created_at
```

`status`：`PENDING / READY / UNAVAILABLE / INVALID`。

VideoAsset 保留平台 `cover_url`；CoverAsset 表示已下载、本地可服务的派生资产。不得用远程 URL 是否存在代表本地封面已经可用。

---

# 7. API

Video Note List Item 增加：

```text
cover_status
cover_image_url
cover_width
cover_height
cover_error
```

图片资源：

```text
GET /api/video-covers/{cover_id}/image
```

或使用等价的 VideoAsset cover endpoint，但必须：

- 只服务数据库已登记路径；
- 防止任意文件路径读取；
- 返回正确 Content-Type、ETag、Cache-Control；
- READY 以外返回稳定占位/404，不代理任意用户 URL。

---

# 8. Job 与重试

`FETCH_COVER` 位于 `FETCH_METADATA` 之后，可独立重试和缓存复用。封面失败属于非核心增强：

- 不把整个视频笔记标为 FAILED；
- Job/Note 可以 COMPLETED 或 PARTIAL_SUCCESS；
- 列表使用占位；
- 后续重新生成或封面专项重试可补齐；
- 错误日志只保存 host、状态、MIME、字节数和错误码，不记录 Cookie。

---

# 9. 验收标准

1. 顶部按钮文案为“添加视频链接”；
2. PC 按钮高度 40px、14px 字号，与全局 Primary Button 一致；
3. Mobile 按钮可全宽但不放大字号/高度；
4. Bilibili 元数据 cover URL 能规范为 HTTPS；
5. 参考样本下载原始封面并生成 672×378 WebP 列表图；
6. 封面使用本地 API URL，不长期热链远程 CDN；
7. 同一 VideoAsset 多 Note Version 只下载一次；
8. JPEG/PNG/WebP/AVIF MIME 和文件头校验通过；
9. HTML、SVG、超大和损坏响应被拒绝；
10. 列表缩略图保持 16:9、object-fit cover、时长徽标可读；
11. 加载 skeleton 和失败占位不导致布局跳动；
12. 封面失败不阻塞视频笔记阅读；
13. PC/Mobile 无裁切异常、拉伸和横向溢出；
14. 键盘焦点、alt 和 Card 导航保持可用；
15. 若直接复用参考项目代码，MIT Notice 完整。

---

# 10. 实施边界

本轮只完成文档。后续实现拆为：

1. CoverAsset 数据与迁移；
2. `FETCH_COVER` Provider/Service；
3. 本地原图与 16:9 衍生图；
4. 封面图片 API；
5. Video Note List ViewModel；
6. 列表真实封面与按钮视觉；
7. Fixture、网络失败、安全、PC/Mobile 回归；
8. 必要时补充第三方 MIT Notice。
