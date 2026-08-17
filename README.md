# 至简

至简是本地优先的个人信息处理系统：在 Mac mini 上接收链接、正文和文件，形成可追溯的结构化招聘/旅行内容，并通过 PC 管理界面与手机 Web 入口使用。

## 当前实现

- FastAPI + SQLite（WAL）+ 独立持久 Job Worker；
- URL、正文、DOCX、PDF、XLSX 与图片投递入口；图片进入显式 OCR 待处理状态，不伪造识别结果；
- 北京公务员/事业单位招聘的首批结构化规则及 Claim/Evidence；
- 旅行地点、高德 GCJ-02 坐标、独立地图总览、标记切换与手动路线清单；
- Ollama、DeepSeek、MiMo/OpenAI-compatible Provider，macOS Keychain 保存密钥；
- PC CMS 与移动端共性导航、可信局域网 Token→Session 配对；
- Mac mini `launchd` API/Worker 双服务部署。

## 本地启动

```bash
.venv/bin/zhijian-api
.venv/bin/zhijian-worker
```

打开 `http://127.0.0.1:8787`。开发前端可用 `pnpm --dir frontend dev`；完整验证使用 `pnpm verify` 与 `.venv/bin/pytest backend/tests`。部署说明见 [deploy/macos/README.md](deploy/macos/README.md)，完整设计与决策见 [dev docs/README.md](dev%20docs/README.md)。
