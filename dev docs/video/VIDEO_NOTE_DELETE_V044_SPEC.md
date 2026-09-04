# Video Note Delete v0.4.4

> 实施状态：列表/详情菜单、后端删除边界与保留式删除测试已完成。

> 状态：规格已冻结，待实施
> 更新日期：2026-08-24
> 标注设计：`design/ui/v0.4.4/pipeline-step-replay-and-delete-pc-annotated.png`

---

# 1. 入口

删除能力同时提供两个合理入口，但共用同一个后端动作：

- 视频笔记列表：每行右侧 `…` 菜单 → “删除笔记”；
- 视频笔记详情：顶栏 `…` 菜单 → “删除笔记”。

不在页面正文或首屏放常驻红色删除按钮。删除属于低频破坏性操作，放入溢出菜单；PC/Mobile 均保持至少 44px 点击区域和键盘操作。

---

# 2. 删除边界

删除 Video Note：

- 删除 AINote、Note Version、Section、TOC 和 ContentItem 投影；
- 删除只属于该 Note 的截图关联与本地派生文件；共享 Screenshot/CoverAsset 保留；
- 删除 Note 专属的模型生成结果和索引；
- 写审计事件。

不得连带删除：

- Source 与原始 URL；
- VideoAsset 与共享 CoverAsset；
- Place、Route、Marker 和地点笔记；
- 仍被其他内容或 Note 引用的共享 Source/资产；
- Route、Marker 和地点笔记。

v0.4.6 起，最后一个内容/Note 引用消失且无活跃 Job 时，同一事务删除孤立 Source，并由外键级联清理其 Snapshot、Segment、VideoAsset、Transcript、Cover 与截图；Place 和路线不随 Source 删除。

---

# 3. 状态与门禁

- 有活跃生成/重生成 Job 时返回 409，提示先取消或等待结束；
- Note 不存在返回 404；
- 重复删除返回幂等 404/410，不产生重复审计；
- 删除后详情页返回列表，列表、内容、概览、地点来源和搜索缓存全部刷新；
- 旧书签访问已删除 Note 显示“笔记已删除”，不永久 loading；
- 删除确认文案必须显示笔记标题和保留边界。

第一版沿用现有内容删除策略，不新增回收站；这是不可恢复操作，确认框必须明确说明。若未来增加回收站，再单独迁移为 soft delete。

---

# 4. API

```text
DELETE /api/video-notes/{note_id}
```

响应：

```json
{
  "status": "DELETED",
  "note_id": "note_...",
  "preserved": ["places"],
  "source_deleted": true
}
```

实现必须复用统一 Content/Note 删除 Service，列表页和详情页不能各自维护删除语义。

---

# 5. 确认框

标题：`删除视频笔记？`

正文示例：

> 将删除《中秋国庆人少景美又便宜的地方》及其内容投影。若来源已无其他内容或活跃任务，来源视频、完整转写和审计记录会一并清理；地点与路线保留。此操作目前无法撤销。

按钮：`取消` / `确认删除`。确认按钮使用 destructive variant；默认焦点在取消。

---

# 6. 验收

1. 列表和详情 `…` 菜单都有删除入口；
2. 删除前显示标题、保留边界和不可恢复提示；
3. 活跃 Job 阻止删除；
4. 删除 Note 后列表立即移除，旧 URL 显示已删除；
5. Source、VideoAsset、Transcript、Place、Evidence 仍存在；
6. Note 专属版本、Section、TOC 和无共享引用截图被清理；
7. 共享 Cover/Screenshot 不被删除；
8. 审计事件不包含 Transcript 正文或 Secret；
9. PC/Mobile 菜单与确认框可键盘操作；
10. 列表和详情调用同一 API/Service。
