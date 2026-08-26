# Prompt Supplements v0.4.5

> 状态：已实施并验收。
> 设计图：`design/ui/v0.4.5/prompt-supplements-settings-annotated.png`

## 目标

用户可为三个 AI 阶段增加表达偏好，而不能修改会影响解析和持久化的核心契约。

| 阶段 | 可编辑补充 | 不可编辑核心契约 |
| --- | --- | --- |
| `transcript_correction` | 语气、口语保留程度、简洁度、专有名词关注点 | JSON、Segment ID 唯一性/顺序、字段、Schema、时间码边界 |
| `video_note_summary` | 摘要篇幅、目标读者、行程/风险侧重点、措辞 | JSON、章节字段、有效 Segment 证据、章节结构 |
| `travel_place_extraction` | 优先地点类型、体验/价格/人群关注点 | JSON、地点字段、有效 Segment 证据、不得生成坐标 |

每项最多 1000 字符。补充文本只作为低优先级 System Message 插入固定核心 Prompt 与用户输入之间；核心 Prompt 不会通过 API 返回或编辑。

## 保护与审计

1. 设置页按每个阶段完整展示 6 条只读核心规则摘要与可编辑补充输入框；摘要可压缩措辞，但不得省略 JSON/Schema、字段、Segment ID、顺序/身份、Evidence/事实边界和坐标/锚点等契约类别，也不展示可编辑的 JSON 模板。
2. `PromptSupplementsConfig` 在 API 写入时拒绝覆盖/忽略系统规则、修改 JSON/Schema/字段/键名/ID/顺序等越权表述。
3. 即使补充文本绕过语义过滤，现有 JSON 解析、字段白名单、Segment ID 有效性与顺序校验仍在模型输出之后执行。
4. 设置写入 `prompt:supplements`，审计事件只记录启用阶段和哈希，不记录用户文本。
5. 保存仅影响之后发起的 AI 请求；已经完成的 Note/Transcript/Place 版本不原地修改。

## API

```text
GET /api/settings/prompt-supplements
PUT /api/settings/prompt-supplements
```

GET 返回三个补充文本、只读核心规则摘要、最大长度和每个阶段的哈希。PUT 只接收：

```json
{
  "transcript_correction": "保留自然口语风格。",
  "video_note_summary": "面向首次到访者，突出风险。",
  "travel_place_extraction": "优先提取餐馆和街区。"
}
```

## Pipeline 与续跑

每个 AI Step Input 写入对应 `prompt_supplement_hash`。失败 Job 读取 Replay Options 时，系统比较历史 Input Hash 与当前设置；若哈希变化，从三个 AI 步骤中最早受影响步骤开始续跑，前端不能指定更晚步骤绕过变更。

```text
补充转写校对 Prompt 变更 → CORRECT_TRANSCRIPT 起续跑
补充视频笔记 Prompt 变更 → GENERATE_AI_NOTE 起续跑
补充地点提取 Prompt 变更 → EXTRACT_TRAVEL_FACTS 起续跑
```

## UI

入口位于“设置 → AI 模型”，固定插入“推理路由”与“已保存模型”之间，不新增导航项或独立页面。每一行包含：阶段名、锁定核心契约说明、补充文本框、字符计数与“清空补充”。页面顶部提供统一“保存补充提示词”操作。
