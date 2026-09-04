# 至简

至简是本地优先的个人信息处理系统：在 Mac mini 上接收链接、正文和文件，形成可追溯的结构化招聘/旅行内容，并通过 PC 管理界面与手机 Web 入口使用。

## 当前实现

- FastAPI + SQLite（WAL）+ 独立持久 Job Worker；
- URL、正文、DOCX、PDF、XLSX、图片和音视频投递入口；图片使用 macOS Vision OCR，音视频使用 FFmpeg + Whisper.cpp；
- 北京公务员/事业单位招聘的首批结构化规则及 Claim/Evidence；
- 旅行地点、高德 GCJ-02 坐标、独立地图总览、POI 审核/改名、点选附近 POI 与手动路线清单；
- Ollama、DeepSeek、MiMo/OpenAI-compatible Provider，macOS Keychain 保存密钥；
- PC CMS 与移动端共性导航、4 位局域网配对码→Session、失败限流与会话撤销；
- 真实 Mac mini 硬件/服务/模型检测、JSONL 运行日志与 SQLite 审计事件；
- Mac mini `launchd` API/Worker 双服务部署。

## 范围与可信度

当前面向单用户，唯一支持的后端为 Mac mini，PC/手机通过可信局域网访问。长任务进入独立 Worker，事实结论保留 Evidence；密钥进入 Keychain，不是云端多用户平台。设计草案与未来路线不代表已实现，自动测试也不等于真实模型/视频验收。当前能力和未闭环项只维护在 [实施状态](dev%20docs/IMPLEMENTATION_STATUS.md)，生产现场只见带日期的 [交接快照](dev%20docs/CURRENT_HANDOFF.md)。

## 按需了解

- 只了解项目：读到这里即可；架构主线是 Web → FastAPI → SQLite/Worker → 解析与模型 → 带证据的内容/地图。
- Codex 继续开发：从 [精简接手页](dev%20docs/CODEX_CONTEXT.md) 开始，遵循仓库 [AGENTS.md](AGENTS.md)；可复制 [接手提示词](dev%20docs/CODEX_TASK_TEMPLATES.md)。
- 深入某个领域：在 [文档目录](dev%20docs/README.md) 选一个专项章节，不需要通读全部文档或合订本。

## 本地启动

```bash
.venv/bin/zhijian-api
.venv/bin/zhijian-worker
```

打开 `http://127.0.0.1:8787`。开发前端可用 `pnpm --dir frontend dev`；完整验证使用 `pnpm --dir frontend verify` 与 `.venv/bin/pytest backend/tests`。部署说明见 [deploy/macos/README.md](deploy/macos/README.md)，完整设计与决策见 [dev docs/README.md](dev%20docs/README.md)，真实运行 UI 截图见 [design/ui/implementation-v0.2](design/ui/implementation-v0.2)。
