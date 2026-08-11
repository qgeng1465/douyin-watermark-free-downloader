# 🎬 Douyin Watermark-free Video / Photo Downloader

> A lightweight Python tool: paste a Douyin (TikTok China) share link and download the **watermark-free video** or **original photo slides** in one click.
> Only depends on `requests` — no login, no signature, no browser. Comes with both a **GUI** and a **CLI**.

```bash
python douyin_dl.py "7.43 复制打开抖音，看看视频 https://v.douyin.com/xxxx/ 复制此链接"
```

## ✨ Features

- ✅ **Watermark-free download**: automatically swaps `playwm` → `play` for the clean version
- ✅ **GUI + CLI**: double-click `douyin_gui.bat` (Windows) or run `python douyin_dl.py --gui`
- ✅ **Video / photo posts**: auto-detects the type; slides are downloaded as full original images
- ✅ **Cover & music**: `--cover` saves the cover image, `--music` saves the background music
- ✅ **Clipboard**: `--clipboard` reads the link straight from your system clipboard (GUI has a paste button too)
- ✅ **Smart link detection**: paste an entire share message — the link is extracted automatically
- ✅ **Many link formats**: `v.douyin.com` short links / `iesdouyin.com` / `douyin.com/video`
- ✅ **Batch download**: a txt file with one link per line, built-in throttling to avoid WAF
- ✅ **Progress + speed + ETA**, automatic retries
- ✅ **Remembers your output folder** via a local config file
- ✅ **Bilingual**: `--lang en` for an English interface

## 📦 Install

```bash
pip install requests
```

## 🚀 Usage

### 🖥️ GUI (recommended for beginners)
```bash
python douyin_dl.py --gui
# On Windows you can also double-click douyin_gui.bat
```

### Single download
```bash
python douyin_dl.py "https://v.douyin.com/xxxx/"
# Or paste the whole share message
python douyin_dl.py "7.43 复制打开抖音 https://v.douyin.com/xxxx/ 复制此链接"
# Or just grab the clipboard
python douyin_dl.py --clipboard
```

### Batch download
```bash
# links.txt with one link per line
python douyin_dl.py links.txt -b
```

### Other options
```bash
python douyin_dl.py <link> -o ./downloads   # output folder
python douyin_dl.py <link> --cover          # also save the cover
python douyin_dl.py <link> --music          # also save the music
python douyin_dl.py <link> --json           # machine-readable JSON output
python douyin_dl.py <link> --lang en        # English UI
python douyin_dl.py --version               # version
```

## 🔧 How it works

1. Resolve the share short link → follow redirects to get the `aweme_id`
2. Request `https://www.iesdouyin.com/share/video/<id>` with a mobile UA
3. Extract `play_addr.url_list[0]` from the embedded `_ROUTER_DATA` / `RENDER_DATA` JSON
4. Replace `playwm` → `play` to get the watermark-free URL, then download

## 🙏 Credits

The parsing approach references these open-source projects (public community techniques):

- [boredbar9527/douyin-download-skill](https://github.com/boredbar9527/douyin-download-skill) — `_ROUTER_DATA` parsing
- [belingud/douyin-downloader-skill](https://github.com/belingud/douyin-downloader-skill) (MIT) — photo-post handling
- [aehyok/douyin-video-download](https://github.com/aehyok/douyin-video-download) (MIT) — link parsing

This is an independent implementation, enhanced with: robust JSON extraction (both `_ROUTER_DATA` and `RENDER_DATA`), auto video/photo detection, original-image slides, optional cover/music, a GUI, clipboard reading, download speed & ETA, batch throttling, retries, friendly dead-link handling, and bilingual output.

## ⚠️ Disclaimer

This tool is for **learning, research, and personal fair use only** (e.g. archiving publicly accessible content you are allowed to keep).
Please comply with the laws of your country/region and Douyin's terms of service, and respect creators' and copyright holders' rights.

- Do not use this tool for **commercial or infringing purposes**, or to bulk-download / redistribute copyrighted content.
- Any risk and legal responsibility from using this tool lies with the user.
- If content infringes your rights, contact us and we will remove related links and content promptly.

## 🧪 Tests

```bash
python test_douyin.py   # offline unit tests (no network needed)
```

## 📚 More Tools

> All my free tools & agents: [qgeng1465](https://github.com/qgeng1465) · open source, local-first, ready to use.

## 📄 License

[MIT](./LICENSE) © 2026 qgeng1465
