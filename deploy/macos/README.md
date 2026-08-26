# Mac mini 部署

当前实现使用两个用户级 `launchd` 服务：`cn.zhijian.api` 提供同源前端与 API，`cn.zhijian.worker` 处理持久任务。前端生产资源由 FastAPI 同端口提供，PC 浏览器和手机都只是浏览器客户端。

## 安装

在仓库根目录执行：

```bash
pnpm --dir frontend verify
.venv/bin/pytest backend/tests
.venv/bin/zhijian-init
.venv/bin/python deploy/macos/manage.py install
```

安装器会先备份已有 plist，再加载新服务；不会删除 `data/`。默认监听 `0.0.0.0:8787`，Secret Store 使用 macOS Keychain，日志写入 `data/logs/`。手机通过 `http://<Mac-mini-局域网-IP>:8787` 访问，首次输入 PC 首页或“设置 → 局域网访问”显示的 4 位配对码，换取 HttpOnly Session。连续 5 次失败会触发 10 分钟锁定；轮换配对码会撤销已有设备会话。

## 本地 AI 运行时

```bash
brew install ffmpeg whisper-cpp ollama
brew services start ollama
ollama pull qwen2.5:7b
```

Whisper.cpp 还需要 `data/models/whisper/ggml-base.bin`。模型启用前必须核对 SHA-256 为 `60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe`。页面“设置 → 语音与 OCR”读取实际二进制路径、模型大小和 Ollama API，不以配置文字代替运行状态。

当前已验收组合为 FFmpeg 9.0.1、Whisper.cpp 1.9.2、`ggml-base.bin`（141 MB）和 Ollama 0.32.14 + `qwen2.5:7b`。Whisper 在 Metal 分配受 Ollama 统一内存占用影响时会自动以 `-ng` 回退 CPU，避免任务直接失败。

## 管理与回退

```bash
.venv/bin/python deploy/macos/manage.py status
.venv/bin/python deploy/macos/manage.py uninstall
```

`uninstall` 仅卸载进程，不删除数据库或永久文件。若需回退代码，先卸载服务，切换到已记录的 Git tag/commit，重新构建并安装。用户级 LaunchAgent 在登录后启动；若要求无人登录即可服务，应另行采用 LaunchDaemon，但这会改变 Keychain 的访问主体，不在第一版默认开启。

## 网络边界

- 不配置 UPnP、路由器端口转发或公网暴露；
- 推荐在路由器为 Mac mini 保留 DHCP 地址；
- 手机与 Mac mini 位于同一可信局域网；
- 若将来跨网络访问，先引入 HTTPS/VPN，不直接开放 8787 端口。
