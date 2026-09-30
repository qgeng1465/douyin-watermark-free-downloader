# 🎬 抖音无水印视频 / 图文下载器

> 轻量 Python 工具：复制抖音分享链接，一键下载**无水印视频**或**图文原图**。
> 仅依赖 `requests`，无需登录、无需签名、无需浏览器。自带**图形界面**与命令行双模式。

```bash
python douyin_dl.py "7.43 复制打开抖音，看看视频 https://v.douyin.com/xxxx/ 复制此链接"
```

<!-- README-I18N:START -->
**汉语** | [English](./README.en.md)
<!-- README-I18N:END -->

## ✨ 功能特性

- ✅ **无水印下载**：自动把 `playwm` 替换为 `play`，获取无水印版本
- ✅ **图形界面 / 命令行双模式**：双击 `douyin_gui.bat` 即可用图形界面，或 `--gui` 启动
- ✅ **视频 / 图文双支持**：自动识别作品类型，图集下载全部原图
- ✅ **封面 / 背景音乐**：`--cover` 存封面图、`--music` 存背景音乐
- ✅ **剪贴板一键粘贴**：`--clipboard` 直接读取系统剪贴板链接（GUI 内也有粘贴按钮）
- ✅ **智能识别链接**：粘贴整段分享文案也能自动提取链接
- ✅ **多种链接格式**：`v.douyin.com` 短链 / `iesdouyin.com` / `douyin.com/video`
- ✅ **批量下载**：txt 每行一个链接，内置限速避免被 WAF
- ✅ **断点续传**：`.part` 文件 + HTTP Range，下载中断后重跑自动从断点接上（不再从头下）；失败自动重试 3 次
- ✅ **跳过已下载**：重复下载同一链接时自动跳过已存在的文件（视频/封面/音乐/图集逐文件判断，`--redownload` 强制重下）
- ✅ **进度 + 速度 + 剩余时间**、失败自动重试
- ✅ **记住上次目录**：自动保存输出目录配置
- ✅ **中英双语**：`--lang en` 切换英文界面

## 📦 安装

```bash
pip install requests
```

## 🚀 使用

### 🖥️ 图形界面（推荐新手）
```bash
python douyin_dl.py --gui
# Windows 上也可直接双击 douyin_gui.bat
```

### 单条下载
```bash
python douyin_dl.py "https://v.douyin.com/xxxx/"
# 或直接粘贴整段分享文案
python douyin_dl.py "7.43 复制打开抖音 https://v.douyin.com/xxxx/ 复制此链接"
# 或直接读剪贴板
python douyin_dl.py --clipboard
```

### 批量下载
```bash
# links.txt 每行一条链接
python douyin_dl.py links.txt -b
```

### 其他参数
```bash
python douyin_dl.py <链接> -o ./downloads   # 指定保存目录
python douyin_dl.py <链接> --cover          # 同时下载封面
python douyin_dl.py <链接> --music          # 同时下载背景音乐
python douyin_dl.py <链接> --json           # 输出机器可读 JSON
python douyin_dl.py <链接> --lang en        # 英文界面
python douyin_dl.py <链接> --redownload    # 忽略已下载文件，强制重新下载
python douyin_dl.py --version               # 查看版本
```

## 🔧 原理简述

1. 解析分享短链 → 跟随重定向拿到 `aweme_id`
2. 用移动端 UA 请求 `https://www.iesdouyin.com/share/video/<id>`
3. 从页面内嵌 `_ROUTER_DATA` / `RENDER_DATA` 提取 `play_addr.url_list[0]`
4. 地址中 `playwm` → `play`，获得无水印地址并下载

## 🙏 致谢

技术方案参考以下开源项目（均为社区公开的解析思路）：

- [boredbar9527/douyin-download-skill](https://github.com/boredbar9527/douyin-download-skill) —— `_ROUTER_DATA` 解析思路
- [belingud/douyin-downloader-skill](https://github.com/belingud/douyin-downloader-skill)（MIT）—— 图文处理思路
- [aehyok/douyin-video-download](https://github.com/aehyok/douyin-video-download)（MIT）—— 链接解析思路

本项目为独立实现，并在以下方面做了增强：更健壮的 JSON 提取（兼容 `_ROUTER_DATA` / `RENDER_DATA` 两种形态）、自动识别视频/图文、图文原图下载、封面/音乐可选下载、图形界面、剪贴板读取、下载速度与剩余时间显示、断点续传、跳过已下载、批量限速、重试与错误处理、失效链接友好提示、中英双语。

## ⚠️ 免责声明

本工具**仅用于学习研究及个人合理使用**（如个人归档公开可访问的内容）。
请遵守您所在国家/地区的法律法规以及抖音服务条款，尊重创作者与版权所有者权益。

- 请勿将本工具用于任何**商业用途**、**侵权用途**，或批量下载、再分发受版权保护的内容。
- 使用本工具产生的任何风险与法律责任由使用者自行承担。
- 如内容侵犯了您的合法权益，请联系我们，我们将第一时间移除相关链接与内容。

## 🧪 测试

```bash
python test_douyin.py   # 单元测试（无需网络）
```

## ☕ 支持作者

如果这个工具帮到了你，欢迎扫码赞赏支持，让我有动力持续更新下去～

<img src="assets/donate.png" alt="赞赏码" width="200">

## 📚 更多工具 More Tools

> 我做的所有免费工具与智能体都在这：[qgeng1465](https://github.com/qgeng1465) · 全部开源、本地优先、即装即用。

| 类别 | 项目 |
|---|---|
| ✈️ 可视化 | [飞行足迹 3D](https://github.com/qgeng1465/flight-trajectory-visualizer) · [TS→MP4](https://github.com/qgeng1465/ts-to-mp4-converter) · [MP4转换](https://github.com/qgeng1465/mp4-converter) · [音频工具箱](https://github.com/qgeng1465/audio-toolbox) |
| 🎬 下载 | [抖音](https://github.com/qgeng1465/douyin-watermark-free-downloader) · [B站](https://github.com/qgeng1465/bilibili-video-downloader) · [YouTube](https://github.com/qgeng1465/youtube-downloader) · [小红书](https://github.com/qgeng1465/xiaohongshu-downloader) · [公众号](https://github.com/qgeng1465/wechat-article-exporter) · [直播录制](https://github.com/qgeng1465/LiveRecorder) |
| 🧬 AI 智能体 | [AI4Bio](https://github.com/qgeng1465/ai4bio-agents) · [AI4Chem](https://github.com/qgeng1465/ai4chem-agents) · [AI4科研](https://github.com/qgeng1465/ai4research-agents) · [日常生活](https://github.com/qgeng1465/daily-agents) |

## 📄 License

[MIT](./LICENSE) © 2026 qgeng1465
