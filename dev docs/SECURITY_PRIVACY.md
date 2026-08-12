# Security & Privacy

## 1. 核心原则

Local First。

第一版业务数据默认只在用户 PC。

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
- Windows Credential Manager / DPAPI；
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

---

# 5. 外部大模型数据边界

Local First 默认尽可能本地处理。

调用外部模型前：
- 明确 provider；
- 允许用户选择 Local Only；
- 日志记录是否调用外部；
- 可后续增加敏感字段脱敏策略。

---

# 6. 本地 Web 安全

如果只 localhost：
风险较低。

如果允许局域网：
- bind 到局域网需显式开启；
- API token；
- Admin API 保护；
- 不默认暴露互联网。

---

# 7. PC-only 远程访问

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

---

# 10. 删除

未来应支持：
- 删除 Source；
- 删除 Snapshot；
- 删除 Profile；
- 删除 Place；
- 清理 Cache。

删除业务对象时注意 Evidence 引用与审计完整性。
