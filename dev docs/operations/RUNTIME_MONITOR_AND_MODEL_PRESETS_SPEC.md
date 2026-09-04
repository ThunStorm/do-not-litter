# 至简 运行监控与模型预设规格

版本：v0.5，更新日期：2026-08-21，状态：`IMPLEMENTED / BROWSER_VERIFIED`。适用部署：Mac mini 单节点，局域网可信会话访问。

## 1. 目的

本规格落实设置页审阅的七项意见：局域网访问时资源指标必须稳定显示；监控采样由后端持久化而非浏览器实时探测；模型路由与控件保持“至简”视觉语言；新增模型在保存前可做真实测试；用户既可选择主流 Provider，也可保留手工填写；选择 Provider 后自动带出模型与 Base URL；本地模型不要求远端连接字段；内存统一以百分比展示。

## 2. 持久化运行监控

Mac mini API 进程是唯一采样者。它在启动时立即采样一次，此后每 30 秒采样一次，将最新记录写入 SQLite `settings` 的 `runtime:metrics-sample`。采样包含 `sampled_at`、CPU 百分比、内存百分比、数据盘百分比、每项不可用原因及 Worker 心跳快照；不得写入用户内容、密钥或访问 Token。

`GET /api/status` 只读取该持久化快照并返回其原始采样时间，不因请求来源是 `127.0.0.1`、局域网 IP 或已经可信配对的移动端而改用浏览器或即时伪造的指标。API 启动到第一条样本落库前返回“等待首个采样”；样本超过 75 秒时标为“指标延迟”，前端保留数值并同时显示延迟状态。侧栏和弹层每 30 秒刷新一次，与采样频率一致。

侧栏完整状态卡显示 CPU、内存、数据盘三个百分比与 Worker 心跳；内存不再显示“已用 / 总量”。可访问名称仍保留具体采样时间，展开弹层显示“采样于 …”。采集失败的单项显示 `—` 与“暂未采集”，不得显示 `0%`。

## 3. 模型路由视觉与交互

推理路由说明必须位于卡片正文的 20px 内边距中，紧邻路由选择而不贴在卡片左边线。主模型和备用模型使用统一的“选择框外壳”：40px 高、暖灰底、细线圆角、右侧定制 Chevron，不使用浏览器默认的黑色原生 select 外观。窄桌面时两项纵向排列。

主模型是必选的已保存模型，备用模型可空且不得与主模型相同。只有网络、超时、HTTP 服务错误或 Provider 不可用才触发备用模型；模型输出格式错误、结构化校验失败和用户取消不触发回退。该规则保留在路由卡的内嵌说明中。

## 4. Provider 预设与自定义模型

新增和编辑模型的 Provider 控件同时支持预设选择与手工填写：预设清单为 DeepSeek、MiMo、Moonshot / Kimi、智谱 GLM、通义千问、OpenAI 兼容、Ollama（本地），末项为“自定义”。选择预设会填入 Provider 标识、推荐 Base URL 和可选模型清单；模型名可从同一 Provider 的常用模型下拉选择，也始终允许自行输入。切换 Provider 只自动填充仍为空或仍等于前一预设默认值的字段，不覆盖用户明确修改过的值。

| Provider | 默认 Base URL | 模型建议 | 凭据 |
| --- | --- | --- | --- |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat`、`deepseek-reasoner` | 必填 |
| MiMo | `https://api.xiaomimimo.com/v1` | `mimo-v2-flash`、`mimo-v2-pro` | 必填 |
| Moonshot / Kimi | `https://api.moonshot.cn/v1` | `kimi-k2.6`、`kimi-k2.5` | 必填 |
| 智谱 GLM | `https://open.bigmodel.cn/api/paas/v4` | `glm-5-turbo`、`glm-5`、`glm-4.7` | 必填 |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus`、`qwen-max` | 必填 |
| OpenAI 兼容 | 留空，由用户填写 | 自行输入或常见模型建议 | 依服务而定 |
| Ollama（本地） | `http://127.0.0.1:11434` | 读取/填写本机模型名 | 不要求 |
| 自定义 | 留空，由用户填写 | 自行输入 | 依服务而定 |

Ollama 本地模型模式隐藏 API Key 与 Base URL 的必填提示，Base URL 可使用默认本机地址；显示“本机运行，不需要 API Key”。默认超时为 **300 秒**，允许 5–900 秒。所有 API Key 仅存 macOS Keychain。

新增模型即使尚未保存，也必须提供“真实测试”：前端把当前表单作为临时配置提交到 `POST /api/settings/model-profiles/test-draft`，后端只用请求内容发起一次最小真实请求，不写入 SQLite、Keychain 或模型库。测试结果只展示连通性、Provider 和模型，不回显 Key。保存后的模型继续使用持久化测试接口。

## 5. API 与数据契约

- `GET /api/status`：返回持久化 `metrics`、`metrics.sampled_at` 与 `metrics.freshness`（`FRESH` / `STALE` / `PENDING`）。
- `POST /api/settings/model-profiles/test-draft`：接收完整临时模型配置，执行真实连接测试，不产生配置、密钥或审计持久化副作用。
- 原有模型库 CRUD、已保存模型测试、主/备路由接口保持兼容。

## 6. 验收

1. 使用局域网 IP 访问并完成可信配对后，侧栏在首次 30 秒采样完成后持续显示与数据库快照一致的 CPU、内存、磁盘百分比和采样时间。
2. 断开实时采样超过 75 秒，侧栏明确显示“指标延迟”，不以 `0%` 代替。
3. 路由说明与两项选择控件有统一 20px 内边距，选择框不出现浏览器默认黑色边框/箭头。
4. 新建未保存配置可点击“真实测试”；测试后模型库数量、SQLite `settings` 与 Keychain 不新增该草稿。
5. 选择 DeepSeek、MiMo、通义、Ollama 后，推荐 Base URL 和模型建议正确出现；切换为本地 Ollama 时不要求 Key。
6. 新增模型默认超时为 300 秒，内存显示为百分比。
