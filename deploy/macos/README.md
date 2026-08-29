# Mac mini 部署

当前实现使用两个用户级 `launchd` 服务：`cn.zhijian.api` 提供同源前端与 API，`cn.zhijian.worker` 处理持久任务。前端生产资源由 FastAPI 同端口提供，PC 浏览器和手机都只是浏览器客户端。

## 安装

生产 LaunchAgent 固定使用 Python `3.14.6`，虚拟环境位于 `/Volumes/D/Library/Application Support/Zhijian/venv`。仓库内 `.venv` 只负责运行部署管理器；前端验证使用 Node.js 22。首次安装或依赖变化时，在仓库根目录执行：

```bash
nvm use 22
pnpm --dir frontend verify
.venv/bin/python deploy/macos/manage.py runtime
'/Volumes/D/Library/Application Support/Zhijian/venv/bin/python' -m pytest backend/tests -q
'/Volumes/D/Library/Application Support/Zhijian/venv/bin/python' -m ruff check backend/src backend/tests deploy/macos/manage.py
'/Volumes/D/Library/Application Support/Zhijian/venv/bin/python' -m pip check
.venv/bin/zhijian-init
.venv/bin/python deploy/macos/manage.py install
.venv/bin/python deploy/macos/manage.py status
```

安装前必须确认没有 `QUEUED/RUNNING` Job 或未释放 lease。安装器会备份已有 plist，再加载新服务；不会删除 `data/`。默认监听 `0.0.0.0:8787`，Secret Store 使用 macOS Keychain，日志写入 `data/logs/`。手机通过 `http://<Mac-mini-局域网-IP>:8787` 访问，首次输入 PC 首页或“设置 → 局域网访问”显示的 4 位配对码，换取 HttpOnly Session。连续 5 次失败会触发 10 分钟锁定；轮换配对码会撤销已有设备会话。

## 本地 AI 运行时

```bash
brew install ffmpeg whisper-cpp
# Ollama 使用 /Applications/Ollama.app，不启动 Homebrew Ollama 服务
```

Ollama 模型固定存放在 `/Volumes/D/Projects/ollama-models`。`manage.py install` 会校验该目录包含 `blobs/` 与 `manifests/`，并把 Ollama.app 的默认路径 `~/.ollama/models` 持久链接到该目录；原默认目录会先备份。该链接不依赖临时环境变量，系统重启、Ollama.app 更新和重复执行 `manage.py install` 后仍然有效。Whisper.cpp 还需要 `data/models/whisper/ggml-base.bin`。模型启用前必须核对 SHA-256 为 `60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe`。页面“设置 → 语音与 OCR”读取实际二进制路径、模型大小和 Ollama API，不以配置文字代替运行状态。

当前已验收组合为 FFmpeg 9.0.1、Whisper.cpp 1.9.2、`ggml-base.bin`（141 MB）和 Ollama.app 0.32.15 + `qwen2.5:7b`。Whisper 在 Metal 分配受 Ollama 统一内存占用影响时会自动以 `-ng` 回退 CPU，避免任务直接失败。

## 管理与回退

```bash
.venv/bin/python deploy/macos/manage.py status
.venv/bin/python deploy/macos/manage.py restart
.venv/bin/python deploy/macos/manage.py uninstall
```

`status` 不再只看 PID：必须同时读取 `/health`、完整首页正文和 75 秒内 Worker 心跳；任一失败均返回非零退出码。`restart` 在存在排队/运行 Job 或未释放 lease 时拒绝执行。`uninstall` 仅卸载进程，不删除数据库或永久文件。

管理器会在 `bootout` 后等待旧标签从 launchd 消失，再执行 `bootstrap`。若仍报告 `launchctl bootstrap ... exit status 5`，不要连续重复整套安装。先用 `launchctl print gui/$(id -u)/cn.zhijian.api` 和 `cn.zhijian.worker` 确认旧标签已经消失，再只加载缺失服务：

```bash
launchctl bootstrap "gui/$(id -u)" ~/Library/LaunchAgents/cn.zhijian.worker.plist
launchctl kickstart -k "gui/$(id -u)/cn.zhijian.worker"
launchctl bootstrap "gui/$(id -u)" ~/Library/LaunchAgents/cn.zhijian.api.plist
launchctl kickstart -k "gui/$(id -u)/cn.zhijian.api"
.venv/bin/python deploy/macos/manage.py status
```

已加载的服务不要重复 `bootstrap`；只处理 `launchctl print` 明确不存在的标签。服务恢复后还要核对 `program` 指向生产 venv，而不是 Codex 缓存 Python。

仓库位于外置卷时，macOS 会按 `SystemPolicyRemovableVolumes` 单独授权。必须在“隐私与安全性 → 完全磁盘访问权限”中允许 LaunchAgent 实际使用的 Python；否则 API 可能只返回响应头而无法发送静态文件，Worker 也可能在延迟导入视频模块时失败。修改权限或 Python 路径后重新安装，再以 `status`、实际 plist `program` 和内核 deny 日志共同验证。软链接、chmod 和只看 `launchctl running` 均不能代替此检查。

若需回退代码，先卸载服务，切换到已记录的 Git tag/commit，重新构建并安装。用户级 LaunchAgent 在登录后启动；若要求无人登录即可服务，应另行采用 LaunchDaemon，但这会改变 Keychain 的访问主体，不在第一版默认开启。

## 网络边界

- 不配置 UPnP、路由器端口转发或公网暴露；
- 推荐在路由器为 Mac mini 保留 DHCP 地址；
- 手机与 Mac mini 位于同一可信局域网；
- 若将来跨网络访问，先引入 HTTPS/VPN，不直接开放 8787 端口。
