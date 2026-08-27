# Mac mini 部署基线

版本：v0.4.6，更新日期：2026-08-28。第一版唯一受支持的后端节点是 Mac mini；项目不再维护其他操作系统的部署脚本、运行时矩阵、硬件假设或回退方案。

## 1. 当前设备与职责

- 节点：Mac mini `Mac16,10`，Apple M4，16 GB 统一内存，arm64；
- 服务：FastAPI、React 生产资源、SQLite/WAL、永久文件、独立 Worker、Playwright、文档解析、OCR、whisper.cpp、Ollama 和可选外部 Provider；
- 客户端：PC 浏览器与手机浏览器，均通过可信局域网访问同一节点；
- 密钥：macOS Keychain；开发环境允许权限受限的本地文件存储。

## 2. 运行形态

```text
PC Browser / Mobile Browser
          │ trusted LAN + session
          ▼
Mac mini
├─ launchd: cn.zhijian.api
├─ launchd: cn.zhijian.worker
├─ FastAPI + WebSocket + React static assets
├─ SQLite + APFS permanent files
├─ Ollama / Metal
├─ whisper.cpp / Metal
└─ macOS Keychain
```

生产服务由 `deploy/macos/manage.py install` 渲染并重启两个用户级 LaunchAgent。生产解释器固定为 Python `3.14.6`，venv 位于 `/Volumes/D/Library/Application Support/Zhijian/venv`，`PYTHONPATH` 直接指向当前仓库 `backend/src`。仓库或数据位于外置卷时，必须为实际 Python 责任进程配置 `SystemPolicyRemovableVolumes`/完全磁盘访问权限；安装后用 `manage.py status` 验证首页正文实际可读和 Worker 心跳，并用 `launchctl print` 核对实际 `program`，而不是只看 PID。关闭自动睡眠、启用断电恢复，并为局域网地址设置 DHCP 保留或固定地址。

## 3. 容量与并发约束

- 16 GB 为 CPU、GPU 与本地模型共享的统一内存；不把它当成独立显存。
- GPU 重任务初始并发固定为 1；ASR、LLM、Vision 不并行抢占统一内存。
- Ollama 用 Metal，whisper.cpp 用 Metal；Core ML encoder 仅在可复现安装且结果一致时启用。
- 较长视频、较大模型或本地运行时不可用时，可按用户策略调用 DeepSeek、MiMo 等兼容 Provider；敏感字段外发规则不变。

## 4. 安全与恢复

- 默认只在本机访问；启用手机访问时才绑定明确 LAN 地址，并采用 4 位配对码换取 HttpOnly Session。
- 不做端口映射、UPnP 或公网暴露；公共/访客网络不得启用可信 LAN 模式。
- API Key、LAN 配对码和平台 Cookie 不进入 SQLite、日志、导出或前端通用接口。
- LaunchAgent 崩溃或重启后自动恢复；Worker 启动先冷导入视频 Pipeline，外置卷不可读时不得领取 Job。未捕获异常立即将当前 Job 标为 `FAILED/WORKER_UNHANDLED_EXCEPTION` 并释放 lease。

## 5. 真实状态原则

PC 控制台硬件、运行时、CPU、内存、磁盘与 Worker 心跳均从 Mac mini 当前状态接口读取。不可使用文档样例、固定 M4 参数或虚构百分比作为页面数据；单项采集失败应明确显示不可用原因。
