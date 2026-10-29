# 视频时间P0/P1实施与验收（2026-10-29）

范围：用户确认P0/P1及新增THEME_CONTEXT；P2封面与P3真实模型/历史更新后置。没有数据库迁移、真实模型调用、视频重跑、POI确认、提交或推送。

## 变更与证据

- P0：统一时间词、假期HOLIDAY精度与原词、标题装饰词、完整单主体Claim连续证据、跨段历史修饰词及时间状态归一化。标题parser v2、map-timing-v4、travel-semantics-v2。
- P1：同次GROUND_MAP提供当前激活主题与块内切换的来源注册表，既有短ID编译器还原，未提供的主题引用拒绝；ContentUnit成员须有逐字连续证据，比较/背景/中转/整体否定不继承，OPTIONAL不升级。Prompt semantic-map-v7-temporal-context与temporal-context-v2进入缓存身份。
- Artifact JSON保存主题/关联；Note固定产物、Mention记录语义哈希，读取复验视频/转写/原句/版本。旧NULL不猜绑，GET不补写历史。
- Place/Destination共用有效时间投影；地图主题/月季筛选、浮窗/时间详情、聚合成员、v2导出及Note输入保留来源。局部活动/日期条件、人工窗口及不同来源不覆盖。

## 验证

| 验证 | 结果与边界 |
| --- | --- |
| 后端全量 | 生产Python3.14，774项通过；之后收尾目标100项通过，含新增分块/非法月份/真实片头反例 |
| 前端 | 60项、ESLint、TypeScript、隔离Vite构建通过；既有bundle体积提示不影响通过 |
| 真实来源夹具 | BV1bgKm6YE4m原Segment/Snapshot及时间码；古龙山连续证据和暑假片头可离线复查；地点适用关系不是人工金标 |
| 背景隔离 | 真实片头仅生成暑假主题原词，7月15日—8月15日不成为推荐日期；13月/十三月/0月不猜合法月份 |
| 关联拒绝 | 错误主体/单位、未见来源、跨Snapshot/跳段/倒序/改引文、比较/整体否定、主题切换均有反例 |
| 用途与历史 | 活动观赏限制不取消整体推荐；同用途限制降为条件性参考；人工窗口保留，固定产物NULL不继承 |
| Browser | Browser插件未提供，使用Edge/Playwright。1440×900、390×844：主题选择、8月组合、来源展开、清除、无横向溢出与相关控制台错误 |
| Browser真实性 | 新主题展示使用明确模拟的map响应且禁止写请求；生产真实GET旧数据无主题、空结果及清除另验；不冒充真实模型提取 |

## 发布与回退

首次保存点：`data/backups/temporal-context-20261029-104841`；最终保存点：`data/backups/temporal-context-20261029-105228`。目录含可恢复工作树、原HEAD源码、静态资源、已验证SQLite备份、哈希、发布/回退脚本及Browser截图/JSON。SQL iterdump包含FTS恢复限制，已明确标为unverified；恢复使用已验`.db`备份，无生产库恢复或迁移。

发布最终时间：2026-10-29T10:52:50.718794+08:00；API/Worker READY，新Worker PID55272。index SHA256：`eafdab39468469b98b3b03df1c5ce30c247b2965ebcfd7049cecb03960b0ea6e`；新JS SHA256：`d0a843cdbdd1a9ee11f6d27e508f3ca64b654bbba59d94ba1c1cf47f7b27e13f`。HTTP资源逐一与隔离构建匹配，区域时间路由与temporal_theme参数已核对，业务表摘要在发布及最终GET后无变化；仅允许运行事件与指定runtime设置变化。未使用回退。

## 未验证与后置

没有证明真实模型必定输出正确主题成员、跨块指代召回率或完整端到端质量；规则候选采取保守识别，不以置信度替代原句校验。P2封面OCR/视觉和P3真实小样、人工金标、指定历史新版本仍未实施。目标旧版本`ntv_39e83862aecc41e4bf0a5ba9ddba5fa3`产物引用仍NULL，不能宣称旧笔记已自动改善；要更新它必须按P3建立获授权的新版本，而非猜绑旧Artifact。
