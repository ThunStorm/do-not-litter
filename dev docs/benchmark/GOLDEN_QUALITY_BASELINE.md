# G0 共享离线质量基线（2026-11-12）

完成复核日期：2026-11-13（材料与包冻结日 2026-11-12）。执行包：[G0.1–G0.3](../planning/video-workflow-20261112/01_BASELINE_AND_GATES.md)。本包是证据、测试和 CI 脚手架，不修改 Prompt、POI 阈值或业务路由。基线 HEAD：`e9c509913208480604295f3db6acf4053f73a221`；不是干净提交。接手时已有 router/video_notes、cover_text/grounded_map、place/source retention、video_support 与资源保留新增文件及规划文档等未提交改动，全部保留。本次全量结果描述这一工作树，不能外推到单独 HEAD。机器报告逐文件记录源码、测试、Fixture、依赖和配置 SHA256 及工作树状态；重新运行应核对摘要，不能只比较测试数量。

## G0.1 可用材料与裁定

脱敏清单：[manifest.json](../../backend/tests/fixtures/quality_baseline_v1/manifest.json)。冻结已有文件哈希；逐记录保存 Segment、原句/哈希、时间范围和已知身份，缺失 Source/Snapshot/Transcript/Note 版本使用 `null`，不从其他对象推断。云南的 `sN` 是现有回放解析器的归一化下标，原数据库 Segment 身份未知；转写参考版本文本不等于数据库版本。

| 类别 | 可供下游使用 | 裁定状态/限制 |
| --- | --- | --- |
| 云南多区域/路线，P0_CRITICAL | 101 个转写 Segment；simulation-v1 的 71 个类型候选；12 个作用域路线夹具；保存的真实 gpt-6-luna 响应 | unjudged；模拟参考与真实响应分文件，均非独立人工金标；可复现解析/归并/投影与否定限制 |
| 12 月错峰 | 24 条原文标注草案、保存的 43 条 Claim、20 个 Mention、22 个章节 | unjudged；保留既有 Note 版本，未补造 Source/Snapshot；历史“人工核对”描述缺裁定者及逐条裁定日期，不能据此晋级 |
| 标题/封面时节 | 2 条古龙山连续原句，已知 Snapshot/Note 版本；原有标题、正文与合成封面测试 | unjudged；真实封面图不在本清单，合成封面仅作来源/否定/日期守卫测试；不冒充真实视觉识别验收 |
| 厦门餐饮 | BLOCKED_SOURCE | 只有样本定位文档，缺完整冻结材料 |
| 贵州完整视频 | BLOCKED_SOURCE | 12 月样本中的从江原句不能代替贵州 43 景区完整视频 |
| 独立快速多区域/保留集 | BLOCKED_SOURCE | 现有材料均曾用于开发，不将任何一个重新命名为未调参保留集 |

清单共 127 个证据/标注记录，全部 `unjudged`，人工裁定覆盖率 0%。它们不是 127 个地点或 127 个事实金标。下游可用于结构错误重放和修复；当前没有已人工裁定的类别可支持模型调参收益或独立质量提升结论。人工待办是逐条指定实体/事实语义匹配键、正负例、推荐/比较/背景角色，并登记裁定者和日期；不在本包由 Agent 代替裁定。

## G0.2 门禁与指标

单条质量回放命令（仓库根目录）：

```bash
.venv/bin/python scripts/check_quality_baseline.py --output /tmp/g0-quality.json
```

引用的本次机器报告：[GOLDEN_QUALITY_BASELINE.json](GOLDEN_QUALITY_BASELINE.json)。运行会生成 JSON、JUnit XML 和网络审计文件。Python/解析器/Fixture 版本以源码与清单哈希冻结；保存响应只验证当前解析、归并、证据投影和物化规则，不派发新 Prompt，不测量模型效果。

地点、事实、POI 身份按维度和推荐/比较/背景角色分别报告。裁定语义键用多重集合一对一匹配，重复输出产生 FP；precision=TP/(TP+FP)，recall=TP/(TP+FN)，零分母为 JSON `null`（N/A）。未裁定不计正确或错误；当前各维度 TP/FP/FN/precision/recall 均 N/A。`NEEDS_REVIEW` 是处置状态，另列保存输出中的分布，不替代 `unjudged`。本次未执行 POI resolver，自动确认总数 0、错误确认数未知、准确率 N/A、裁定覆盖率 N/A，不能写成 100%。来源可达率按冻结文件中的逐字引用计算，语义完整性仍 N/A。

关键门禁复用云南 P0_CRITICAL、笔记原句/跨包身份、标题/正文时节与封面来源等现有断言；新增自检分别删除真实草案中的否定词、替换来源身份、注入错误确认 POI，必须被结构契约检测器拒绝。这些复制/变异用例只校验检测器，不是新模型样本或人工金标。原有生产规则测试仍单独执行，不以检测器自测代替业务规则。

每份对照记录样本数、保存响应来源/模型、未知参数、输入哈希、OFFLINE_FILES 缓存模式、首次/恢复/备用/未派发次数（本次全部 0）、离线墙钟耗时、Token 口径（未测量，不能填成实际消耗 0 或缓存收益）。既有云南检查脚本保持不变；本报告不复用其类型投影 1.0 指标冒称模型召回。

## G0.3 本地与 CI

完整本地入口（Node 22.21.0、pnpm 11.19.0、Python 3.12；使用已经安装的环境）：

```bash
PATH="$HOME/.nvm/versions/node/v22.21.0/bin:$PATH" .venv/bin/python scripts/check_g0.py --output-dir /tmp/do-not-litter-g0
```

脚本不安装依赖，依次执行原有 Ruff、后端全量、前端 ESLint/Vitest/TypeScript、临时目录 Vite 构建和质量回放，并输出逐步退出码、日志、JUnit、版本与审计。生产静态目录不覆盖。3 个状态 API 测试使用显式离线 runtime fixture，返回 UNAVAILABLE，不进行真实硬件或 Ollama 就绪探测；保留测试本身与状态契约断言。

新增 [workflow](../../.github/workflows/offline-g0.yml) 使用 Ubuntu/Python 3.12、Node 22.21.0、pnpm 11.19.0，复用根 pnpm v9 格式 lockfile，以 frozen-lockfile 安装；[requirements-ci.txt](../../backend/requirements-ci.txt) 固定本机既有 Python 依赖快照，editable 后端以 no-deps 安装。本机没有更新依赖。安装阶段允许包下载；检查阶段不注入业务 Secret、不读取生产库。workflow 仅 contents:read，checkout 不保留凭据，失败也保存检查产物。

检查阶段对 Python socket/DNS/UDP 和 Node socket/DNS/UDP API 施加守卫；Python 子进程即使覆盖 PYTHONPATH 也继承守卫。Python 非解释器子进程默认拒绝，仅放行只读 `uname -p`、`/sbin/mount`；ffmpeg、媒体下载和业务 CLI 不放行。审计按检查步骤隔离；捕获异常仍使步骤失败。守卫自身另用独立审计验证 Python 捕获异常、Python 子进程、Node 捕获异常三种绕过，故意阻断不计入业务尝试。它是测试运行时检测，不是操作系统级网络沙箱；未证明任意原生扩展、Node 原生子进程等所有通道。新增原生调用时须扩展检测，不能因 Mock 名称宣称零外部调用。

托管状态 **HOSTED_NOT_RUN**：仅本地解析 YAML 和执行相同检查入口；未提交、推送或触发 GitHub。Linux 包安装、Runner 路径/平台分支、Actions 权限/产物上传均未托管验证。真实 macOS Keychain、Vision/OCR、LaunchAgent、真实 ASR/模型/高德/媒体另列本机/授权门禁；没有删测或声称它们通过。

## 本次检查结果与停止条件

后端 949 项、质量回放 151 项（含 5 项新增门禁自检）、前端 64 项均通过；Ruff/ESLint/TypeScript/隔离构建通过，无跳过。127/127 冻结原句可达率 1.0 仅表示文件引用可达；保存的 20 个 Mention 中 15 个 NEEDS_REVIEW、5 个 UNKNOWN，与裁定状态分列。三种守卫绕过自检均通过；最终业务检查阻断尝试 0。质量 JSON 附源码文件哈希和冻结清单哈希，全量检查 JSON 中的测试数量是对本次 JUnit 的导出聚合；原始日志/JUnit 位于 `/tmp/do-not-litter-g0-20261112-verified`。

最终检查数据见 [G0_LOCAL_CHECKS.json](G0_LOCAL_CHECKS.json)，源码和自动验证状态仅同步至 IMPLEMENTATION_STATUS。早期守卫过严拦截只读系统命令及状态探测、全局数据目录覆盖冲突导致失败，保留在 `/tmp/do-not-litter-g0-20261112*` 日志；随后最小修正检查脚手架和 3 项离线状态测试，未改业务实现。

本包不改变 Schema、历史数据、依赖安装或生产服务；无真实外部业务调用，无部署、重启、提交或推送。到 G0 停止。下一步仅由人工完成所需类别裁定并提供缺失材料；不得自动执行下一个包。
