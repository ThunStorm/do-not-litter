# API Design

> API 风格：REST + WebSocket  
> 第一版单用户，本地使用，但仍保持明确资源边界。

---

# 1. Capture API

## POST /api/inbox

输入：

```json
{
  "input_type": "url",
  "value": "https://..."
}
```

返回：
`202 Accepted`

```json
{
  "item_id": "...",
  "job_id": "...",
  "status": "QUEUED"
}
```

## GET /api/inbox/{id}

返回：
- input
- resolved type
- processor
- processing status
- result link

---

# 2. Recruitment API

## GET /api/recruitment/dashboard

返回 `RecruitmentDashboardVM`：

```json
{
  "nearest_deadline": {},
  "action_items": [],
  "eligibility_summary": {},
  "recommended_positions": [],
  "profile_questions": [],
  "recent_notices": []
}
```

## GET /api/recruitment/notices

支持分页与状态。

## GET /api/recruitment/positions

Filters：
- eligibility
- region
- deadline
- organization
- education
- major
- user_state

## GET /api/recruitment/positions/{id}

返回：
- position
- requirement results
- Evidence
- source graph
- deadlines
- actions

## POST /api/recruitment/positions/{id}/state

```json
{"state":"PREPARING"}
```

## GET /api/recruitment/questions

返回按 Information Gain 排序的待补充 Profile。

## POST /api/recruitment/questions/{id}/answer

更新 profile 后触发增量匹配。

---

# 3. Travel API

## GET /api/travel/dashboard

```json
{
  "days_since_last_trip": 63,
  "map_places": [],
  "recent_discoveries": [],
  "recommended_places": [],
  "pending_reviews": 0
}
```

## GET /api/travel/places

Filters：
- city
- place_type
- status
- source
- preference
- user_state

## GET /api/travel/places/{id}

返回：
- place
- mentions
- observations
- evidence
- preference explanation

## GET /api/travel/map

只返回 Confirmed Place ViewModel。

## POST /api/travel/places/{id}/save
## POST /api/travel/places/{id}/dismiss
## POST /api/travel/places/{id}/visited

写 PreferenceEvent / VisitEvent。

## POST /api/travel/export

格式：
- csv
- json
- geojson

---

# 4. Control Center API

## GET /api/admin/dashboard
## GET /api/admin/jobs
## GET /api/admin/jobs/{id}

## POST /api/admin/jobs/{id}/retry
## POST /api/admin/jobs/{id}/cancel

## POST /api/admin/jobs/{id}/rerun

```json
{
  "from_step": "EXTRACT_PLACES",
  "provider_override": null
}
```

## POST /api/admin/jobs/{id}/rerun-external

显式使用外部模型。

## GET /api/admin/sources/{id}
## GET /api/admin/sources/{id}/graph

## GET /api/admin/poi/review
## POST /api/admin/poi/{id}/confirm
## POST /api/admin/poi/{id}/reject

## GET /api/admin/settings
## PUT /api/admin/settings

---

# 5. WebSocket

## WS /api/ws/jobs

消息：

```json
{
  "job_id":"...",
  "status":"RUNNING",
  "step":"ASR",
  "progress":62,
  "message":"..."
}
```

前端断线后重新连接，再通过 REST 重新取状态，不能只依赖 WS。

---

# 6. ViewModel 原则

API 返回给产品前端的是 ViewModel，而不是 ORM Row。

原因：
- 防止 UI 绑定数据库；
- 支持未来小程序/移动 App；
- 数据库可演进；
- 保持业务语义。

---

# 7. 错误响应

统一错误：

```json
{
  "code":"POI_NEEDS_REVIEW",
  "message":"...",
  "details": {}
}
```

错误 code 必须稳定，不直接依赖异常类名。

---

# 8. 单用户认证

第一版本地模式可简化。

若允许局域网手机访问：
- 至少增加本地访问 token；
- 不允许匿名开放管理 API。

未来远程访问再引入完整认证。
