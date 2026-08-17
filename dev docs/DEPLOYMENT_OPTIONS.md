# Deployment Options

## 1. 决策状态

第一版保留两套互斥、均可实施的单节点部署方案，最终实施前由用户选择：

- **方案 A：Windows 11 PC 后端**；
- **方案 B：Mac mini 后端**。

两套方案共享同一套 React、FastAPI、SQLite、Job、Processor、Evidence 与 Provider 代码，不允许为了某台机器复制业务实现。`DEPLOYMENT_TARGET` 只决定安装脚本、进程托管、Secret Store、本地 AI 加速器和硬件诊断。进入 Phase 0A 前必须选择一个主目标完成验证；未选择前不得把平台特有实现写死进业务层。

---

## 2. 共同架构

```text
PC Browser ─┐
            ├─ trusted LAN + session ─→ Selected Backend Node
Mobile Web ─┘                              ├─ React production assets
                                          ├─ FastAPI / WebSocket
                                          ├─ SQLite + local files
                                          ├─ independent Worker
                                          ├─ Playwright / document / OCR
                                          └─ local AI + optional external Provider
```

共同约束：

- 选中的后端节点是第一版唯一业务数据库、永久文件和 Job Lease 所有者；
- PC 浏览器和手机都是客户端，不在客户端保存完整业务数据库；
- 默认只监听 localhost；启用手机访问时才监听明确的 LAN 地址，并执行 Token-to-Session、Origin 限制与 Admin API 认证；
- 不做 UPnP、端口映射或直接公网暴露；
- URL、DOCX、PDF、XLS/XLSX、PNG/JPEG、OCR、视频、Evidence 与 Processor 行为在两套方案中保持一致；
- DeepSeek、Xiaomi MiMo 与自定义 OpenAI-compatible Provider 均可配置；
- 两台机器之间不共享同一个 SQLite 文件，也不在第一版拆分 API 主机和 Worker。未来混合 Worker 属于 Multi Worker 路线，不属于本次二选一。

---

## 3. 方案 A：Windows 11 PC 后端

### 3.1 硬件基线

- 设备：`WILLIAM-PC`；
- CPU：AMD Ryzen 7 5800X，8C/16T；
- RAM：32 GB；
- GPU：AMD Radeon RX 7900 XT，20 GB VRAM；
- OS：Windows 11 x64。

### 3.2 运行方式

```text
Windows PC
├─ backend service / launcher
├─ worker process
├─ React static assets
├─ SQLite + permanent files
├─ Ollama on AMD GPU
├─ whisper.cpp Vulkan
└─ Windows Credential Manager / DPAPI
```

开发期可分别启动 Vite、FastAPI 与 Worker；生产期使用项目 launcher 或 Windows 服务/计划任务托管后端与 Worker。浏览器是管理界面，不要求桌面壳才能运行。

### 3.3 优势

- 20 GB 独立显存更适合较大的本地模型、长上下文与未来视觉任务；
- 32 GB 系统内存对 Playwright、OCR、文档解析与本地 AI 并行更宽裕；
- 已有 Windows + AMD、Ollama、whisper.cpp Vulkan 的原方案与验证清单。

### 3.4 代价与风险

- AMD 本地 AI 在 Windows 上的具体模型兼容性和稳定性必须实测；
- 若 PC 不是长期在线设备，手机随时投递和后台持续处理会受开关机影响；
- 功耗、噪声和作为常驻服务的维护成本通常高于 Mac mini；
- Windows 更新、休眠和显卡驱动可能中断长任务，必须验证自动恢复。

---

## 4. 方案 B：Mac mini 后端

### 4.1 当前设备基线

截至 2026-08-18 当前设备为：

- 设备：Mac mini；
- 型号标识：`Mac16,10`；
- 芯片：Apple M4，10 核 CPU（4 性能核 + 6 能效核）；
- 统一内存：16 GB；
- 架构：arm64；
- 当前系统：macOS 26.6.1。

系统版本允许升级，不作为代码硬依赖；Apple Silicon arm64 是必须验证的目标架构。

### 4.2 运行方式

```text
Mac mini
├─ launchd: backend service
├─ launchd: worker process
├─ React static assets
├─ SQLite + permanent files on APFS
├─ Ollama using Metal
├─ whisper.cpp using Metal（可选 Core ML encoder）
└─ macOS Keychain
```

生产期优先使用原生 arm64 Python/Node 与 `launchd` 托管，不把依赖 Metal 的本地 AI 主路径放进 Docker。Docker 只可用于不依赖本机 GPU/Metal 的辅助开发或 CI。关闭自动睡眠并启用断电恢复后，Mac mini 可作为无显示器常驻 LAN 节点；管理端通过浏览器访问。

### 4.3 本地 AI 策略

- Ollama 使用 Apple Metal；本地模型从 7B/8B 量化档起做结构化输出 Spike；
- 16 GB 是 CPU、GPU 与模型共享的统一内存，不能按 16 GB 独立显存理解；
- GPU 重任务并发初始为 1，ASR、LLM、Vision 不并行抢统一内存；
- whisper.cpp 使用 Metal，Core ML encoder 仅在可复现安装和结果一致时启用；
- OCR、Playwright 和文档解析必须验证 arm64 原生依赖；安装困难的 OCR 实现通过 `OCRProvider` 替换，不能渗入业务 Pipeline；
- 复杂长上下文、较大视觉模型或本地失败任务可按用户策略转 DeepSeek、MiMo 等外部 Provider；敏感字段外发规则不变。

### 4.4 存储与常驻运维

- SQLite、Source、Snapshot、Evidence 和浏览器 Profile 位于 Mac mini 本机 APFS 数据目录；
- API Key 与 LAN Token 存入 macOS Keychain，SQLite 只保存 Secret 引用；
- 可使用 Time Machine 或加密外置盘备份永久数据目录，但默认排除临时视频、模型缓存和浏览器 Profile；
- LAN 地址可显示主机名和 IP，客户端发现不能只依赖 mDNS；`zhijian.local` 不可用时必须提供固定 IP/路由器 DHCP 保留地址；
- `launchd` 必须在进程崩溃、用户退出登录或机器重启后恢复服务；Job 本身仍通过数据库 Lease 恢复。

### 4.5 优势

- 更适合低功耗、低噪声、长期开机的家庭/办公 LAN 服务节点；
- Apple Silicon 的 Metal 与统一内存路径相对集中，部署形态比桌面 PC 常驻更简单；
- PC 与手机都退化为浏览器客户端，后端状态不依赖 Windows PC 是否开机。

### 4.6 代价与风险

- 16 GB 统一内存限制可同时运行的模型大小与任务并发；
- 大模型、长视频 ASR、Vision 与 Playwright 并行时更容易出现内存压力；
- 部分 OCR、旧 `.xls` 或浏览器依赖需要单独验证 arm64 wheel/二进制；
- Mac mini 的本地 AI 吞吐不得从 Windows/AMD 结果推算，必须独立测量。

---

## 5. 选择矩阵

| 维度 | 方案 A：Windows PC | 方案 B：Mac mini |
| --- | --- | --- |
| 常驻服务 | 取决于 PC 开机、休眠与更新策略 | 更适合 7×24 低功耗常驻 |
| 本地模型容量 | 20 GB 独立显存，空间更大 | 16 GB 统一内存，需更保守 |
| 本地 AI 并发 | 初始仍为 1，实测后可调整 | 固定从 1 起步，优先串行 |
| ASR | whisper.cpp Vulkan | whisper.cpp Metal，可 Spike Core ML |
| Secret Store | Credential Manager / DPAPI | macOS Keychain |
| 服务托管 | launcher / Windows 服务 / 计划任务 | launchd |
| 本地 AI 兼容风险 | AMD Windows 运行时与驱动 | arm64 依赖与统一内存上限 |
| 手机可用性 | PC 在线时可用 | Mac mini 常驻时更稳定 |
| 功耗与噪声 | 通常更高 | 通常更低 |
| 适合优先级 | 更强本地 AI、未来视觉模型 | 稳定常驻、随时投递、外部模型可补强 |

选择建议不是最终决定：若“尽量本地跑更大模型”优先，先验证方案 A；若“手机随时可用、长期安静运行”优先，先验证方案 B。最终结论必须以两台目标机器各自的 Phase 0A 数据为依据。

---

## 6. 分别实施时的决策门

实施前设置且只设置一个目标：

```text
DEPLOYMENT_TARGET=windows_pc
```

或：

```text
DEPLOYMENT_TARGET=mac_mini
```

选择后：

1. 执行对应平台的 Phase 0A；
2. 把 LAN、OCR、本地 LLM、ASR、SQLite 恢复、常驻服务与功耗结果写入 `GOLDEN_SAMPLES.md`；
3. 所有关键项得到 `PASS / DEGRADED / BLOCKED`；
4. 若出现 `BLOCKED`，先选择 Provider 替代或调整范围，再进入依赖该能力的 Phase；
5. 未选择的方案保留文档与适配接口，但不要求同步交付安装包。

不允许在同一次 MVP 实施中同时维护两套生产安装包，以免部署工作吞噬业务验证时间。
