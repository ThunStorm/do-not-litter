# 至简（do-not-litter）前端视觉设计规范 v1.0

> 建议仓库落点：`dev docs/design/FRONTEND_VISUAL_DESIGN_SYSTEM.md`
> 适用范围：`frontend/` 全部 PC / Mobile Web 页面、地图工作区、设置、内容、任务、地点管理、路线管理。
> 状态：本轮建议冻结为 **前端视觉唯一规范（normative）**。`design/ui/` 下截图继续作为视觉参考（reference），但不再承担 Design Token 和组件契约职责。
> 基线分支：`codex/mac-mini-implementation`，审阅基线提交：`77e37ebf15eaab59bd23dbd384b8040702f2aa60`。

## 1. 设计目标

“至简”是长期使用、信息密度较高的个人信息处理工作台。视觉保持：暖纸张感；编辑感而非营销感；宋体感标题 + 现代中文无衬线正文；朱砂红克制使用；苔绿只表达正向/完成/健康；地图低干扰；组件优先于页面临时 CSS；PC 与 Mobile 使用同一设计语言。

## 2. 规范优先级

发生冲突时：已冻结产品/安全契约 > 本文视觉规范 > 共享组件 > `design/ui/README.md` 当前有效参考稿 > 页面历史 CSS。旧截图不能成为继续复制不一致控件的理由。

## 3. Design Tokens

### 3.1 颜色

```css
:root {
  --color-canvas: #F4F1EB;
  --color-surface: #FBFAF7;
  --color-surface-muted: #F7F5F0;
  --color-surface-active: #F1ECE5;

  --color-text: #1D1B18;
  --color-text-secondary: #504B44;
  --color-text-muted: #77726A;
  --color-text-disabled: #AAA49B;

  --color-border: #D8D3CA;
  --color-border-soft: #E8E3DB;
  --color-border-strong: #B9B3A9;

  --color-accent: #B52B1D;
  --color-accent-hover: #8F2016;
  --color-accent-soft: #FBF3EF;

  --color-success: #59863F;
  --color-success-soft: #F2F6ED;
  --color-warning: #A66C15;
  --color-warning-soft: #FCF8EF;
  --color-danger: #A63326;
  --color-danger-soft: #FBF0ED;

  --color-scrim: rgb(29 27 24 / 42%);
  --shadow-floating: 0 12px 34px rgb(55 45 35 / 12%);
  --shadow-panel: 0 8px 24px rgb(55 45 35 / 8%);
}
```

规则：页面背景用 canvas；卡片/浮层用 surface；正文用 text；说明用 muted。Accent 仅用于当前导航/筛选、主动作、待处理 Badge、选中 Marker、少量重点链接。删除用 danger；成功/在线/完成用 success；警告用 warning。外部品牌默认单色图标，不引入品牌色。

### 3.2 字体

```css
--font-sans: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", system-ui, sans-serif;
--font-serif: "Songti SC", STSong, SimSun, serif;
--font-mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
```

页面标题、区块标题、品牌用 serif；正文、控件、表格、筛选用 sans；ID、时间戳、技术指标用 mono。页面不得自行引入新的字体族。

### 3.3 字号

| Token | 字号 / 行高 | 用途 |
| --- | --- | --- |
| Display | 40 / 40 | 品牌字 |
| H1 Desktop | 31 / 38 | PC 页面主标题 |
| H1 Mobile | 20 / 28 | Mobile 页面主标题 |
| H2 | 22 / 30 | 大区块标题 |
| H3 / Panel | 18 / 25 | 卡片/面板标题 |
| Body | 14 / 22 | 默认正文 |
| Body Dense | 13 / 20 | 表格、地图预览、设置 |
| Meta | 12 / 18 | 次要信息 |
| Caption | 11 / 16 | 时间、来源、辅助提示 |
| Micro | 10 / 14 | 仅紧凑运维元信息 |

字重：正文 400；强调/按钮 500–600；标题 600。禁止大量 700+ 制造层级。

## 4. 间距、圆角、边框、阴影

统一 4px 基础网格：`4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 48`。新页面禁止随意新增 7/13/17/19px 等随机间距。

圆角：输入/小按钮 6px；Icon Button / Dropdown Trigger 8px；Panel 8px；Popover/Dialog 10px；Mobile Bottom Sheet 顶部 16px；Badge/Chip 999px。

边框默认 1px `--color-border`；分割线 `--color-border-soft`。常规 Panel 不使用重阴影，只有 Dropdown、Popover、Dialog、地图浮层使用 floating shadow。

## 5. 页面骨架

### PC

- Sidebar 基线 232px。
- 常规内容最大宽 1180px；管理工作区可 1280–1440px，但必须通过统一 workspace frame。
- 页面主操作集中 Header 右侧，不散落首屏角落。

### Mobile

- `<720px` 进入 Mobile 布局。
- 页面安全边距 15–16px。
- 表格改为紧凑卡片列表，不做横向缩小版 PC 表格。
- Dropdown/Filter 优先 Bottom Sheet，不用窄浮层强塞。

## 6. 共享组件

新前端工作优先落到 `frontend/src/components/ui/`（或同级共享目录）：

- `Button`
- `IconButton`
- `TextField`
- `SearchField`
- `SelectMenu`
- `MultiSelectMenu`
- `FilterChip`
- `FilterPopover`
- `Dialog`
- `ConfirmDialog`
- `BottomSheet`
- `Toast`
- `DataTable`
- `EmptyState`
- `OverflowMenu`

禁止地图、路线、地点详情各复制一套 dropdown/menu CSS。

## 7. Dropdown / SelectMenu 强制规范

### 禁止项

- 产品主界面禁止裸用浏览器原生 `<select>` 作为最终视觉实现。
- 内部 Enum（如 `SCENIC_AREA`、`AUTUMN`、`MID`）不得直接展示给用户。
- 禁止每页自己画箭头/边框/阴影。
- 菜单打开不得挤压页面布局。

原生 `<select>` 仅允许无障碍降级、测试夹具、内部调试页。

### Trigger

- 高度 40px；min-width 112px；水平 padding 12px；radius 8px。
- surface 背景、1px border、13px secondary text、16px muted Chevron。
- Hover 用 strong border。
- Open/focus-visible 用 accent border + `0 0 0 3px rgb(181 43 29 / 8%)`。
- Disabled 40–50% opacity。

### Menu

- min-width = trigger；max-width 320px；max-height 320px；padding 6px；radius 10px。
- surface + border + floating shadow。
- Option min-height 36px。
- Selected 用 accent-soft + check，不用整块实心红。
- Section label 11px muted。
- 支持 ArrowUp / ArrowDown / Enter / Escape / Home / End。
- Trigger 使用 `aria-haspopup`、`aria-expanded`；Option 使用可访问 listbox/menu 语义。

当前前端没有 Radix/Headless UI 依赖，本轮默认不为了 Dropdown 引入大型 UI 框架；实现轻量共享组件并配交互测试。

## 8. Filter 规范

筛选不是表单，不表现为连续多个 `<select>`。

第一层使用 `FilterChip`，点击后打开 `FilterPopover`。Active Chip 显示摘要，如 `类型 · 景点`、`适宜时间 · 秋季 / 10月中旬`、`路线 · 云南秋季`；多筛选时有统一“清除筛选”。

### Map Workspace

PC：搜索、筛选、待确认、地点管理进入同一条 Map Toolbar / Filter Rail；地图右下只留定位/缩放/全国视野；选中地点用右侧 Preview；新增地点进入搜索态，不出现手工落点 Marker。

Mobile：顶部搜索，下面横向 Filter Chips；复杂筛选进 Bottom Sheet；Place Preview 用底部 Sheet；禁止堆叠多个独立 absolute 浮层。

## 9. 地图 Marker 规范

### 单一 Marker

禁止同时保留 `.amap-marker`、`.map-marker`、AMap 默认 Marker、临时 Draft Marker 多套视觉。

统一 `PlaceMarker` SVG/DOM：默认 26×34，锚点底部中心，默认填充 `#302E2A`，选中 accent + scale 1.12，Hover 只提高 z-index/轻微 scale。Hidden 用空心/低透明度。Cluster 用圆形数字 Badge。

**不得再使用旋转方块 + `::after` 内圆的两层 CSS 拼接 Marker。**

### 空间重叠

- 低 Zoom：Cluster。
- 高 Zoom：同坐标/近像素点先聚成 Stack Marker，显示数量；点击展开地点选择列表或局部 spiderfy。
- Selected Marker 永远在普通 Marker 上层。

## 10. 地图新增地点交互

正确流程：

1. 用户点“添加地点”；
2. 地图进入“选择搜索区域”；
3. 用户单击地图；
4. **只记录搜索锚点，不生成 Marker**；
5. 自动打开地点搜索面板，默认加载附近 POI；
6. 用户关键词搜索；
7. 确认高德 POI；
8. 后端创建/复用 canonical Place；
9. 刷新地图；
10. 使用 Provider POI 坐标自动出现正式 Marker；
11. 自动选中并打开 Preview/详情入口。

取消：Esc、关闭、“取消”均清空 anchor/result，关闭面板，不创建 Place/Marker。换区域使用“重新选择区域”。地图普通新增流程不得把用户点击坐标作为最终 POI 坐标。

## 11. Table / 批量管理

地点管理使用 DataTable：Row 48–56px；sticky header；checkbox 点击热区 >=32px；列标题 12px；数据 13px；Hover surface-active；Selected 左侧 accent 2px + accent-soft；批量选中后才出现 Batch Action Bar；批量永久删除必须二次确认。

Mobile 使用地点卡片：名称、类型、城市/地址、适宜时间摘要、状态、OverflowMenu。

## 12. Dialog / 删除规范

路线删除使用 `ConfirmDialog`，禁止 `window.confirm`，明确“删除路线不会删除地点”。

地点永久删除必须使用 Danger Confirm Dialog：展示 Marker、备注/Overlay、洞察、路线引用、视频地点关联等影响；明确 Source/视频/Evidence 不被删除。来源地点建议输入地点名称确认；按钮写“永久删除地点”，不能只写“确定”。

## 13. 状态与反馈

Mutation pending 禁止重复触发并显示 loading。成功用绿色 Toast；错误在控件/Dialog 附近显示。删除后按影响失效 Place list、Map、Routes、Place detail 等 Query。

## 14. 中文 Enum 映射

业务 Enum 保留在 API，UI 统一中文。

| Enum | 中文 |
| --- | --- |
| SCENIC_AREA | 景点 |
| RESTAURANT | 餐饮 |
| NEIGHBORHOOD | 街区 |
| PEDESTRIAN_STREET | 步行街 |
| BUSINESS_DISTRICT | 商圈 |
| MARKET | 市集 |
| PARK | 公园 |
| MUSEUM | 博物馆 |
| TEMPLE | 寺庙 |
| VILLAGE | 村落 |
| TOWN | 古镇/城镇 |
| LANDMARK | 地标 |
| ACCOMMODATION / HOTEL | 住宿 |
| TRANSIT / TRANSPORT | 交通 |
| OTHER / UNKNOWN | 其他 |

时间：春季/夏季/秋季/冬季；1月…12月；上旬/中旬/下旬；清晨/上午/中午/下午/日落/晚间/夜间/早餐/午餐/晚餐/深夜。

## 15. 响应式与无障碍

- 点击热区 >=36px，Mobile 主要控件 >=40px。
- `:focus-visible` 可见。
- Icon-only button 必须 `aria-label`。
- Dropdown/Popover/Dialog 全键盘可用。
- Dialog 管理焦点，关闭后返回 Trigger。
- `prefers-reduced-motion` 禁用非必要动画。
- 不依赖颜色单独表达状态。

## 16. CSS / 组件治理

现有变量允许一阶段 alias：`--paper → --color-surface`、`--paper-deep → --color-canvas`、`--ink → --color-text`、`--muted → --color-text-muted`、`--line → --color-border`、`--accent → --color-accent`、`--green → --color-success`。新代码只使用新 Token。

必须清理地图 `.map-marker` / `.amap-marker` 重复体系。页面局部 CSS 只做布局，不重新定义共享控件视觉。

禁止：新硬编码颜色、新 font-family、`window.confirm` 最终交互、地图/地点/路线主交互裸 `<select>`、复制旧页面控件 CSS。

## 17. Agent 强制接手规则

### `AGENTS.md`

新增等价规则：

> ## 前端视觉规范
> 任何涉及 `frontend/` 的页面布局、组件、样式、表单、地图覆盖物或交互视觉变更，在读目标源码前必须按需读取 `dev docs/design/FRONTEND_VISUAL_DESIGN_SYSTEM.md`。新 UI 必须优先复用其中 Design Tokens 和共享组件；不得新增裸原生下拉、页面私有按钮体系或未登记颜色/字号。前端行为变更完成后必须在受影响的 PC/Mobile 断点进行 Browser 视觉验收。若产品需求与视觉规范冲突，先遵循冻结产品/安全契约，再更新视觉规范，不允许页面自行偏离。

### `dev docs/CODEX_CONTEXT.md`

路由表新增：

| 任务关键词 | 首选文档 |
| --- | --- |
| 前端、UI、视觉、样式、布局、组件、Dropdown、Filter | `design/FRONTEND_VISUAL_DESIGN_SYSTEM.md` |

“地图、地点、POI”行补充：若变更地图前端布局/控件/Marker，同时读取视觉规范 Map Workspace、Filter、Marker 章节。

### `design/ui/README.md`

开头增加：本目录截图是参考图，不是 Token/组件规范。前端视觉规范性来源为 `../../dev docs/design/FRONTEND_VISUAL_DESIGN_SYSTEM.md`。

## 18. 前端验收清单

- [ ] 未出现新的裸 `<select>` 主界面控件。
- [ ] Enum 未直接显示给用户。
- [ ] 新样式无未登记硬编码颜色。
- [ ] 字号/字体符合层级。
- [ ] PC 与 Mobile 无溢出、遮挡、不可点击。
- [ ] Dropdown 可键盘操作、Esc 关闭。
- [ ] Dialog 有焦点管理。
- [ ] 地图 Marker 只有一套正式视觉实现。
- [ ] 同坐标地点不会完全互相遮挡。
- [ ] 地图新增地点取消后无残留 Marker。
- [ ] 批量危险操作有二次确认。
- [ ] 使用真实浏览器验收，而非 build 通过代替视觉验收。

## 19. Definition of Done

本规范落地完成不是“文档写完”，而是：规范成为 Agent 路由的一部分；`AGENTS.md` 和 `CODEX_CONTEXT.md` 明确要求遵循；建立共享 UI primitives；地图页第一批迁移；地点管理直接使用规范；地图/地点管理/路线的 PC 与 Mobile 页面完成浏览器视觉验收；之后新增前端页面默认从本规范起步。
