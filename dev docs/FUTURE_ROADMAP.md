# Future Roadmap

> 本文只记录未来能力，防止在 MVP 实施中被遗忘。  
> 这些能力**不是第一版必须实现**，除非后续明确提升优先级。

---

# 1. GenericProcessor

目标：

未知非结构化内容不再 Unsupported，而进入通用处理。

GenericResult：

```text
title
summary
key_points[]
entities[]
dates[]
locations[]
action_items[]
claims[]
```

仍保留 Evidence。

---

# 2. Processor 演进体系

长期三层：

## Dedicated Processor
- Recruitment
- TravelFood
- Shopping
- ...

## Configurable Processor
通过：
- Schema
- Prompt
- View Template
- Rules
实现中等复杂场景。

## Generic Processor
未知内容兜底。

演化：

```text
Generic 高频场景
→ Configurable
→ 成熟后 Dedicated
```

---

# 3. 动态分类 / Space

第一版不做。

未来：
- AI 建议创建；
- 用户确认；
- 用户可改名；
- 用户可合并；
- 用户可删除；
- 一条 Source 可进入多个 Space。

Space 不等于 Folder。

---

# 4. Generic View Templates

未来可提供：

- Countdown + Todo
- Map + List
- Timeline
- Comparison
- Knowledge Summary
- Wishlist

AI 建议 View，但用户有最终控制。

---

# 5. Source Watch

第一版仅预留接口。

未来支持：
- 招聘补充公告；
- 截止日期变化；
- 页面更新；
- 商品价格变化；
- 旅行地点状态变化。

Source Watch 新版本应产生新 Snapshot，不静默覆盖旧事实。

---

# 6. 自动执行 C 级

当前 B：
- 生成报名 Checklist
- 咨询建议
- 待办

未来 C：
- 自动填写报名；
- 自动填写网页表单；
- 自动发邮件；
- 自动日历同步；
- 自动导出到第三方地图；
- 自动购买/预订等更高风险行为（需独立安全设计）。

要求：
- 权限模型；
- 用户确认；
- 操作 Preview；
- 审计日志；
- 可撤销；
- 风险分级。

---

# 7. 移动端

第一版：
Responsive Web。

未来：
- Android app
- iOS app
- 微信小程序
- Share Extension

移动端应为薄客户端。
重任务继续由 PC/Cloud Worker。

---

# 8. Browser Extension

价值：
- 当前页面；
- 用户登录态；
- 选中文字；
- 页面 DOM；
- 截图；
- “记住这个”。

可解决部分微信/平台访问限制。

---

# 9. Remote PC

PC 节点 + 可信局域网 MVP 的限制：
PC 离线时无法即时处理。

未来选择：

### VPN / direct secure access
仍不需要业务云。

### Light Control Plane
手机先写 Inbox；
PC 上线后取任务。

### Full Cloud
云 Worker 兜底。

---

# 10. Multi Worker

未来 Job 带 capability：

```text
requires_gpu
requires_browser_cookie
privacy
priority
```

Execution Router：

```text
Home PC
Office PC
Cloud CPU
Cloud GPU
```

---

# 11. Cloud SaaS

长期商业化：

- Multi-user；
- User Auth；
- Tenant isolation；
- Cloud DB；
- Cloud GPU；
- Subscription；
- Quota；
- Remote Worker optional。

MVP 代码不得提前承担这些复杂度。

---

# 12. 向量搜索 / RAG

第一版不需要 Vector DB。

未来当 GenericProcessor 和历史资料规模提升后，可加入：
- embedding；
- semantic retrieval；
- RAG；
- cross-source question answering。

必须保持 Evidence。

---

# 13. Knowledge Graph

当前 Source Graph / Claim-Evidence 用关系表足够。

未来若跨领域 Entity/Relation 复杂度显著增长，可评估图数据库。

不提前引入。

---

# 14. Travel Vision

当前 Transcript First。

未来：
- 关键帧抽取；
- 店招；
- 菜单；
- OCR；
- 路牌；
- 价格；
- 景点画面；
- 视频中的地图。

VisualEvidence 与 TranscriptEvidence 并存。

---

# 15. Travel Planning

未来：
- Trip
- itinerary
- route
- opening hours
- travel time
- city clustering
- multi-day plan

当前 Place 用户状态已为未来 PLANNED 留口子。

---

# 16. Recruitment C-level

未来：
- 自动准备报名材料；
- 自动生成字段填充值；
- 浏览器自动填表；
- 最终提交必须另行确认；
- 对验证码/身份认证不绕过。

---

# 17. Personal Memory / Preference

未来：
- 更长期的行为学习；
- Preference versioning；
- Explanation；
- User correction；
- explicit vs inferred conflict management。

---

# 18. Generic Automation

最终目标：

```text
Input
→ Understand
→ Decide
→ Prepare Action
→ Execute (when allowed)
```

应用从“信息整理工具”进化为个人 AI 行动层，但必须始终保留：
- 来源；
- Evidence；
- 权限；
- 用户控制。
