# v0.4.4 Design QA

更新日期：2026-08-24。参照 `video-note-detail-pc-annotated.png`、`video-note-detail-mobile-annotated.png` 和 `pipeline-step-replay-and-delete-pc-annotated.png` 验收。

## 已通过

- 信息层级：CoverAsset Hero、AI 摘要、主旨目录、时间线正文、文章底部地点/转写顺序与标注一致；缺封面收起，不显示详情占位图。
- 阅读布局：桌面截图在正文侧面，移动端落到正文下方；关键图为缩略图，点击打开 contain Lightbox，支持遮罩、关闭按钮与 Escape。
- 文本质量：新增 `CORRECT_TRANSCRIPT` 工序和严格结构化总结提示词；未经校对的历史正文、目录、地点与导出不会继续冒充校对结果，页面提示重新生成。
- 交互：目录、地点和转写时间点统一跳转 Section；导出按钮使用统一描边样式；删除收进列表/详情 `…` 菜单。
- 恢复语义：Replay Options 区分步骤续跑与完整重跑，上游完成步骤 REUSED，中间产物过期时不再提供步骤续跑。
- 自动化：后端 42 项 pytest、前端 9 项 Vitest、Ruff、ESLint、TypeScript 与 Vite 生产构建通过；Alembic 空库与在线库均达到 0007 head。
- 真实 Pipeline：`job_27bd13014cfc4d6fa16e62966f4208aa` 从 AI 校对步骤续跑，前六步 REUSED；校对 255/256 段，生成 7 个章节与 7 张 READY 截图，3 个 POI 待确认，因此合理交付 PARTIAL_SUCCESS。
- PC：1440×1000 下 `scrollWidth=1440`；7 张图片全部载入，正文/侧排截图/底部证据顺序正确，Lightbox `object-fit: contain` 且可关闭。
- Mobile：390×844 下页面和 Body 均无横向溢出；章节与证据单列，截图宽 320px，目录保持双列可读。
- 任务时间线：6 个上游步骤显示 REUSED + 100% + 原步骤用时，执行步骤均显示中文名称、100% 和耗时；终态 `currentRows=0`，无固定清理缓存高亮；浏览器控制台无 ERROR/WARN。

## 在线发布记录

- 2026-08-25 迁移前备份：`data/backups/pre-v044-20260825.db`。
- 在线数据库已由 0006 升级为 0007，`PRAGMA integrity_check=ok`；API/Worker 新进程均为 RUNNING，`/health` 返回 ok。
