# Implementation Status

更新日期：2026-08-18。当前实施目标已选择 **Mac mini 后端**；Windows PC 方案仍保留在 `DEPLOYMENT_OPTIONS.md`，但本分支不交付 Windows 安装包。

## 已完成

- 单仓结构、配置、SQLite WAL、初始迁移、Source/Snapshot/Segment/Claim/Evidence/Content/Job/Place/Route/Setting/Session 数据模型；
- 局域网 Token→HttpOnly Session、localhost 开发豁免、上传路径与大小/类型限制、Keychain Secret Store；
- URL/正文/文件投递，DOCX/PDF/XLSX/文本解析，macOS Vision 中英文图片 OCR（失败显式降级），任务 Lease/超时恢复/重试/取消/WebSocket 进度；
- 招聘与旅行确定性分类、首批招聘字段提取、旅行地点结构、Evidence 约束；
- 地图总览作为父视图、多个标记独立切换、地点详情不内嵌地图、GCJ-02、高德 POI/JS API Provider、无 Key 回退底图、手动路线清单；
- DeepSeek、MiMo、Ollama Provider 配置、Secret 隔离与真实连通测试接口；
- PC CMS、手机首页/内容/投递/待办/我的共性导航、招聘/旅行详情、地图总览、路线和设置页；
- Mac mini launchd API/Worker 双服务生成与管理脚本。

## 自动验证

- 后端 Ruff 与 pytest：通过（含 WebSocket、Provider Secret 隔离、SPA 深链）；
- 前端 ESLint、Vitest、TypeScript 与 Vite 生产构建：通过；
- 应用内浏览器完成 1280×720 PC 与 390×844 手机验收；无控制台错误、无横向溢出，地图 8 个标记切换通过；
- Mac mini 的 `cn.zhijian.api` 与 `cn.zhijian.worker` LaunchAgent 已加载，API 监听 `0.0.0.0:8787`，localhost 与当前 LAN 地址健康检查通过；
- 生产 API 实测上传 PNG 后由常驻 Worker 调用 Vision OCR，约 3 秒完成并在解析后重新判定为招聘任务；应用内浏览器可见文件/相机控件，但其自动化文件选择事件超时，仍需在真实 iPhone Safari 手动点选一次；
- 仍需在提供真实 API Key、AMap Key、Ollama 模型和 whisper/OCR 二进制后完成外部运行时验收。

## 外部条件

以下不是代码内可自动生成的凭据或模型资源：高德 Web 服务/JS API Key、DeepSeek Key、MiMo Key、Ollama 模型、ffmpeg 与 whisper.cpp。缺失时系统必须显示 `MISSING/UNAVAILABLE`，确定性解析、DOCX/PDF/XLSX、macOS Vision 图片 OCR、地图回退视图和 CMS 仍可运行。当前外部资源仍待配置，不影响已部署的本地核心链路。
