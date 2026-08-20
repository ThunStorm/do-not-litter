# 第三方组件与归属说明

## BiliNote

视频链接解析与字幕优先级的适配思路参考 [JefferyHcool/BiliNote](https://github.com/JefferyHcool/BiliNote)，基线提交 `f58e6182c41889873f9df98e4988e479fe9bf14f`（2026-08-11），许可证为 MIT。至简仅实现独立的适配层，不包含或分发该项目的完整应用；如后续引入其任何代码，将在对应文件保留完整 MIT 许可证及修改说明。

## yt-dlp

受 [yt-dlp](https://github.com/yt-dlp/yt-dlp) Unlicense 许可。仅在平台字幕不可用时调用，用于临时提取音频；不保留完整视频文件。
