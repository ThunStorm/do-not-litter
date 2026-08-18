# Implementation Status

更新日期：2026-08-19。当前实施目标为 **Mac mini 后端**；Windows PC 方案仍保留在 `DEPLOYMENT_OPTIONS.md` 和独立可回退分支，不在本分支运行。

## 已完成

- FastAPI、SQLite WAL、独立 Worker、Source/Snapshot/Segment/Claim/Evidence/Content/Job/Place/Route/Setting/Session/SystemEvent 数据模型和 Alembic 迁移；
- PC 首页显眼显示 4 位局域网配对码，可复制、轮换并撤销已有会话；5 次失败触发 10 分钟锁定，Session 使用 HttpOnly Cookie；
- `/api/status` 读取本机 `system_profiler`、磁盘、局域网地址、Worker 心跳、FFmpeg/Whisper/Ollama 实际路径与服务响应，前端不再使用硬编码硬件文案；
- URL、正文、DOCX、PDF、XLSX、图片、音频与视频投递；图片使用 macOS Vision OCR，音视频由 FFmpeg 转为 16 kHz 单声道后交给 Whisper.cpp；
- 招聘与旅行确定性分类、招聘首批字段、旅行地点、Evidence 约束、GCJ-02 地图总览、标记逐点切换、地点详情和人工路线排序；
- DeepSeek、MiMo、Ollama Provider 配置、Keychain Secret 隔离和真实推理测试；
- PC 概览、内容、任务、来源审计、设置六分区、运行日志；手机首页、内容、投递、待办、我的、地图和路线全部为可操作 React 页面；
- JSONL 运行日志、Request ID、SQLite 审计事件、日志查询页面，设计见 `LOGGING_ARCHITECTURE.md`，操作见 `LOGGING_IMPLEMENTATION.md`；
- Mac mini LaunchAgent API/Worker 双服务管理脚本和 Ollama Homebrew 后台服务。

## 自动验证

- 后端 Ruff 与 pytest：13 项通过，覆盖 4 位配对码轮换、真实状态 Schema、来源/档案/待办/日志、WebSocket、Provider Secret 隔离、DOCX 与 SPA 深链；
- 前端 ESLint、Vitest、TypeScript 和 Vite 生产构建通过；
- Homebrew 已安装 FFmpeg、Whisper.cpp、Ollama；运行页以实时探测结果为准；
- LaunchAgent API 与 Worker 均为 `RUNNING`，局域网地址为设备实时探测结果；实际页面读取到 Apple M4 10 核 CPU、10 核 GPU、16 GB 内存、macOS 26.6.2 与磁盘余量；
- Ollama 已完成 `qwen2.5:7b` 真实推理，Whisper.cpp 已通过 WAV 上传、Worker 处理、转写文本写入 Segment/Evidence 的端到端验收；
- Browser 验收覆盖 PC 14 个页面/选项卡与手机 7 个核心页面，控制台无应用错误，运行实图位于 `design/ui/implementation-v0.2/`。

## 外部条件

高德 Web 服务/JS API Key、DeepSeek Key 与 MiMo Key 无法由代码自动生成，未提供时必须显示未配置并保留回退能力。Whisper 模型和 Ollama 模型属于可自动下载的本机资源，启用前必须进行完整性校验和真实推理/转写测试。
