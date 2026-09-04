# Security & Privacy

## 1. 核心原则

Local First。

第一版业务数据默认只在用户的 Mac mini。

---

# 2. 数据分级

## Normal
- 链接
- 地点收藏
- 普通偏好

## Sensitive
- 学历
- 工作经历
- 政治面貌
- 户籍
- 证书

## Local Only
未来高敏感：
- 身份证
- 报名材料
- 自动操作凭据

---

# 3. API Key

正式版本：
- macOS Keychain；
- 数据库只保存引用。

开发 `.env`：
- 只能本机；
- 必须 .gitignore。

---

# 4. Browser Profile

`data/browser/profile/`

可能包含：
- Cookie
- 登录态
- Token
- local storage

禁止：
- Git；
- 普通导出；
- 默认云备份。

Bilibili 字幕或下载可能使用用户 Cookie。Cookie 与 `SESSDATA` 适用同一安全等级：只存平台 Secret Store 或受保护 Browser Profile；不得写入 SQLite 明文、普通日志、错误详情、导出文件或前端通用 Settings API。短链解析和媒体下载必须执行平台 host allowlist、DNS/IP 检查、重定向上限和私网地址拒绝，避免 SSRF。

视频截图属于来源派生资产，默认只保存在本机，不自动进入普通数据导出或云备份。任务缓存视频按 TTL 清理；已被 Note/Place 页面引用的截图保留哈希、时间码和来源关系。隐藏/删除 Marker 不得级联删除截图或 Evidence。

视频封面下载只允许经 Bilibili Resolver 取得且命中图片 CDN allowlist 的 HTTPS URL；执行 DNS/IP、重定向、Content-Type、文件头、尺寸和最大字节校验。封面图片 API 只服务数据库登记路径，禁止任意路径读取和通用 URL 代理。封面原图属于本地派生资产，默认不进入普通导出。

Transcript AI 校对会把视频字幕/ASR 文本发送给所选 LLM Provider，适用 `NORMAL` 来源外发策略并写 ExternalCallAudit。raw_text 与 corrected_text 都受 180 天文稿保留策略约束；默认 UI/导出使用 corrected_text，raw 仅用于本地 Evidence/差异审计。审计日志只能记录 Segment ID、模型、覆盖率和变更计数，不记录原始或校对全文。

完整视频转写属于可导出的来源正文，只在已认证的视频笔记详情提供 TXT 下载。导出由服务端即时生成，不写入缓存目录，不包含 Cookie、模型 Prompt、API Key、内部绝对路径或审计 detail。文件名只使用清洗后的标题与 Transcript Version。

## 用户补充 Prompt

用户在设置页保存的补充 Prompt 属于本地设置数据，写入 SQLite `prompt:supplements`，不写入 Keychain，也不进入 Transcript TXT 导出。审计事件只保留启用阶段与内容哈希，不写入原文，避免运行日志泄露用户表达偏好。核心 Prompt 文件和 JSON/Schema/ID 契约不经 API 提供编辑能力。

完整转写正文固定保留 180 天。清理必须覆盖 `Transcript.text`、`Segment.text/raw_text/corrected_text`、`Evidence.quote` 以及 `metadata_json` 中可能重复保存的全文 fingerprint；只保留哈希、时间范围、数量、版本和 `purged_at`。派生 AI Note 与截图可继续保留，但 UI 必须说明完整转写已过期，不能假装 Evidence 仍可展开。

---

# 5. 外部大模型数据边界

Local First 默认尽可能本地处理。

调用外部模型前：
- 明确 provider；
- 允许用户选择 Local Only；
- 日志记录是否调用外部；
- `NORMAL` 内容按策略发送；
- `SENSITIVE` Profile 默认不外发，仅允许单次明确授权和最小字段发送；
- `LOCAL_ONLY` 永不外发；
- 发送审计记录只保存字段类别与 Evidence/Segment 引用，不复制敏感正文。

高德 Web 服务 Key 与 Security Code 使用 SecretStore；JS API Key 可保存为普通配置。由于 JS Key/Security Code 最终需要提供给已认证浏览器运行时，系统不得宣称其对客户端不可见，必须依赖高德控制台的域名白名单、配额与服务端 Web Key 隔离。Web 服务 Key 永不返回前端。

---

# 6. 本地 Web 安全

MVP 明确支持手机局域网访问：

- 首次安装默认生成高熵访问 Token；
- Mac mini Control Center 显示 LAN 地址并允许复制/轮换 Token；
- 手机首次访问输入 Token，通过 `POST /api/auth/session` 换取短期 HttpOnly、SameSite Session Cookie；
- 浏览器不把长期 Token 保存到 localStorage，REST 与 WebSocket 统一验证 Session；
- localhost 之外的请求缺少/无效 Token 一律拒绝；
- CORS 只允许配置的 LAN Origin，不使用通配符；
- 管理 API 与业务 API 均受保护；
- 监听地址与 LAN 访问可关闭；
- 不做 UPnP、端口映射或公网暴露；
- Token 不写入 URL、普通日志或导出文件。

LAN 传输只允许用户明确配置的可信家庭/办公网络。Phase 0A 必须比较本地 HTTPS 与可信 LAN HTTP 的安装/配对体验；若 MVP 不能可靠部署 HTTPS，UI 必须明确提示不得在公共 Wi-Fi、访客网络或不可信热点中启用 LAN，并将 HTTPS 列为发布前风险项。

---

# 7. 超出可信局域网的远程访问

MVP 不强制实现。

未来可选择：
- VPN
- 安全隧道
- 轻 Control Plane

不建议直接端口映射暴露 FastAPI 到公网。

---

# 8. 日志

日志不得记录：
- API Key
- Cookie
- 登录 Token
- 完整身份证等未来高敏感字段

对敏感 Profile 做字段级掩码。

粘贴分享文案的 Input Normalizer 不在普通日志记录原始全文。URL 任务默认仅持久化选中 URL、输入类型、候选数量、丢弃文本长度和原始输入哈希；周围标题、聊天内容或分享话术不发送给外部 LLM。提取出的每个候选在网络访问前仍需执行 scheme/host allowlist、DNS/IP 与重定向检查，不能因为它出现在文本中就自动抓取。

---

# 9. 数据导出

普通导出不包含：
- browser profile
- API Key
- secret refs
- 原始 Cookie

用户可独立导出：
- Recruitment 数据
- Travel Places
- Evidence
- Settings（无 secret）
- 在 180 天有效期内导出单条视频的完整时间码转写 TXT

---

# 10. 删除

视频笔记删除仅删除 Note 阅读产物，保留共享 Source、VideoAsset、CoverAsset、Transcript、Place 和 Evidence；活跃生成 Job 阻止删除。确认框必须说明不可恢复和保留边界，审计不记录 Transcript 正文。完整契约见 `video/VIDEO_NOTE_DELETE_V044_SPEC.md`。

其他未来删除能力：
- 删除 Source；
- 删除 Snapshot；
- 删除 Profile；
- 删除 Place；
- 清理 Cache。

删除业务对象时注意 Evidence 引用与审计完整性。

步骤级 Replay Cache 默认保留 24 小时，但临时 Cookie、Secret 和未登记 scratch 必须立即清理；Artifact 日志只记录哈希、路径引用、类型、版本和到期时间，不记录正文或凭据。
