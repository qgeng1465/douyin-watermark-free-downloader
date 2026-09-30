#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Douyin Watermark-free Downloader · 抖音无水印视频/图文下载器
=============================================================
仅依赖 requests 的轻量下载工具：解析分享链接 / 分享文本，下载无水印视频与原图。

原理（无需登录、无需签名）：
  1. 解析分享短链 v.douyin.com/xxxx  →  跟随重定向拿到真实链接与 aweme_id
  2. 用移动端 UA 请求 https://www.iesdouyin.com/share/video/<id>
  3. 从页面内嵌的 _ROUTER_DATA / RENDER_DATA JSON 中提取 play_addr.url_list[0]
  4. 把地址里的 playwm 替换为 play 得到无水印版本，再跟随重定向下载

⚠️ 本工具仅用于学习研究与个人合理使用，请遵守法律法规及平台条款，尊重创作者版权。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Callable, Optional

try:
    import requests
except ImportError:  # pragma: no cover
    sys.exit("缺少依赖 requests，请先执行:  pip install requests\nMissing dependency requests, run:  pip install requests")

# Windows 下 stdout 可能是 GBK，含 ✓ 等字符时管道重定向会崩溃；统一 UTF-8 + 容错
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

__version__ = "2.1.1"

UA_MOBILE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)
UA_DESKTOP = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

# 分享链接 / 各形态链接的正则
URL_RE = re.compile(
    r"https?://(?:v\.douyin\.com/\S+|(?:www\.)?iesdouyin\.com/share/(?:video|slides|note)/\d+"
    r"|(?:www\.|m\.)?douyin\.com/(?:video|note|slides)/\d+|www\.douyin\.com/\d+)"
)
ID_RE = re.compile(r"/(?:video|slides|note)/(\d+)")
SHARE_HTTP_RE = re.compile(r"https?://[^\s<>\"']+", re.I)

# ---------- i18n（中文 / English） ----------
_ZH = {
    "proj": "抖音无水印下载器",
    "parsing": "解析链接",
    "resolve_fail": "无法解析 aweme_id，链接可能已失效或被删",
    "no_link": "未在输入中找到抖音链接",
    "page_fail": "解析失败: {e}（可稍后重试）",
    "no_data": "页面未包含数据，可能被 WAF 拦截",
    "video_info": "视频: {title} by {author}",
    "video_saved": "已保存: {path}",
    "album_info": "图文作品: {n} 张 by {author}",
    "album_saved": "已保存 {ok}/{total} 张到: {dir}",
    "cover_saved": "封面已保存: {path}",
    "music_saved": "音乐已保存: {path}",
    "unknown_type": "未能识别作品类型（视频或图文）",
    "dead_video": "该视频不存在、已删除或为私密/地区限制内容",
    "download_fail": "第 {n} 次下载失败: {e}",
    "empty_file": "空文件（可能 UA 不对或被限流）",
    "batch_mode": "批量模式: {n} 条链接",
    "batch_item": "[{i}/{total}]",
    "batch_ratio": "成功 {ok}/{total}",
    "rate_limit": "已暂停 {s}s 避免触发风控",
    "proxy_hint": "提示：检测到代理环境变量 {k}，如解析失败请尝试清除后重试",
    "clipboard_hint": "已从剪贴板读取链接",
    "clipboard_empty": "剪贴板中没有可用的链接",
    "gui_no_tk": "当前 Python 环境缺少 tkinter，无法启动图形界面；请安装带 tk 的 Python 或改用命令行。",
    "gui_title": "抖音无水印下载器 v{ver}",
    "gui_link": "分享链接 / 文案",
    "gui_out": "保存目录",
    "gui_browse": "浏览…",
    "gui_paste": "粘贴剪贴板",
    "gui_download": "下载",
    "gui_paste2": "粘贴剪贴板链接",
    "gui_downloading": "下载中，请稍候…",
    "gui_open": "打开目录",
    "ok": "OK",
    "exists": "已存在，跳过",
}
_EN = {
    "proj": "Douyin Watermark-free Downloader",
    "parsing": "Resolving link",
    "resolve_fail": "Cannot resolve aweme_id; the link may be expired or removed",
    "no_link": "No Douyin link found in the input",
    "page_fail": "Parse failed: {e} (retry later)",
    "no_data": "Page contains no data; possibly blocked by WAF",
    "video_info": "Video: {title} by {author}",
    "video_saved": "Saved: {path}",
    "album_info": "Photo post: {n} image(s) by {author}",
    "album_saved": "Saved {ok}/{total} image(s) to: {dir}",
    "cover_saved": "Cover saved: {path}",
    "music_saved": "Music saved: {path}",
    "unknown_type": "Could not recognize post type (video or photo)",
    "dead_video": "This video does not exist, was removed, or is private / region-restricted",
    "download_fail": "Attempt {n} failed: {e}",
    "empty_file": "Empty file (wrong UA or rate limited)",
    "batch_mode": "Batch mode: {n} link(s)",
    "batch_item": "[{i}/{total}]",
    "batch_ratio": "Success {ok}/{total}",
    "rate_limit": "Pausing {s}s to avoid rate limiting",
    "proxy_hint": "Hint: proxy env {k} detected; clear it if requests fail",
    "clipboard_hint": "Read link from clipboard",
    "clipboard_empty": "No usable link in clipboard",
    "gui_no_tk": "tkinter is not available; install Python with tk support or use the CLI.",
    "gui_title": "Douyin Watermark-free Downloader v{ver}",
    "gui_link": "Share link / text",
    "gui_out": "Output folder",
    "gui_browse": "Browse…",
    "gui_paste": "Paste from clipboard",
    "gui_download": "Download",
    "gui_paste2": "Paste clipboard link",
    "gui_downloading": "Downloading, please wait…",
    "gui_open": "Open folder",
    "ok": "OK",
    "exists": "already downloaded, skipped",
}


def t(lang: str, key: str, **kw) -> str:
    """按语言取文案（lang 为 zh 时中文，其余英文）。"""
    table = _ZH if lang == "zh" else _EN
    s = table.get(key, key)
    return s.format(**kw) if kw else s


def detect_lang(arg_lang: Optional[str]) -> str:
    if arg_lang:
        return arg_lang
    env = (os.environ.get("LANG") or os.environ.get("LC_ALL") or "").lower()
    return "zh" if env.startswith("zh") else "zh"


# ---------- 配置持久化 ----------
CONFIG_PATH = Path.home() / ".douyin_dl_config.json"


def load_config() -> dict:
    try:
        if CONFIG_PATH.exists():
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def save_config(cfg: dict) -> None:
    try:
        CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


# ---------- 基础工具 ----------
def sanitize_name(name: str, max_len: int = 80) -> str:
    """去掉 Windows/各平台非法字符，控制长度。"""
    name = re.sub(r'[\\/:*?"<>|\r\n\t]', "_", name).strip().strip(".")
    name = re.sub(r"\s+", " ", name)
    if not name:
        name = "douyin"
    return name[:max_len]


def extract_url(text: str) -> Optional[str]:
    """从任意文本中提取抖音链接。"""
    m = URL_RE.search(text)
    if m:
        return m.group(0).rstrip("/")
    m = SHARE_HTTP_RE.search(text)
    return m.group(0).rstrip(")").rstrip("，。；）") if m else None


def resolve_aweme_id(url: str, session: requests.Session) -> Optional[str]:
    """解析链接 -> aweme_id。支持短链/长链/图文。"""
    url = url.rstrip("/")
    m = ID_RE.search(url)
    if m:
        return m.group(1)
    try:
        r = session.get(url, headers={"User-Agent": UA_MOBILE},
                        allow_redirects=True, timeout=15)
        m = ID_RE.search(r.url or url)
        if m:
            return m.group(1)
    except requests.RequestException:
        pass
    return None


def _extract_json(text: str):
    """从分享页 HTML 中提取内嵌 JSON 数据（_ROUTER_DATA / RENDER_DATA）。"""
    m = re.search(r"window\._ROUTER_DATA\s*=\s*(\{.*?\});?\s*</script>", text, re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    m = re.search(r'<script\s+id="RENDER_DATA"\s+type="application/json"[^>]*>(.*?)</script>', text, re.S)
    if m:
        import urllib.parse
        try:
            return json.loads(urllib.parse.unquote(m.group(1)))
        except json.JSONDecodeError:
            pass
    m = re.search(r"window\._ROUTER_DATA\s*=\s*(\{.*\})\s*;\s*$", text, re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    return None


def _walk_json(obj, target: str):
    """在嵌套 dict 中按 key 名搜索（返回第一个命中）。"""
    if isinstance(obj, dict):
        if target in obj:
            return obj[target]
        for v in obj.values():
            r = _walk_json(v, target)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _walk_json(v, target)
            if r is not None:
                return r
    return None


def _find_aweme(data):
    """定位真正的 aweme 数据对象（_ROUTER_DATA 深层嵌套）。"""
    if not isinstance(data, dict):
        return None
    r = _walk_json(data, "aweme")
    if isinstance(r, dict):
        return r
    r = _walk_json(data, "item_list")
    if isinstance(r, list) and r and isinstance(r[0], dict):
        return r[0]
    if any(k in data for k in ("desc", "video", "images", "aweme_id")):
        return data

    def rec(o):
        if isinstance(o, dict):
            if any(k in o for k in ("desc", "video", "images", "aweme_id")):
                return o
            for v in o.values():
                r = rec(v)
                if r is not None:
                    return r
        elif isinstance(o, list):
            for v in o:
                r = rec(v)
                if r is not None:
                    return r
        return None
    return rec(data)


def _first_url(node, *keys) -> Optional[str]:
    """从 url_list / urlList / url 等形态里取第一个可用地址。"""
    if not isinstance(node, dict):
        return None
    for k in keys:
        v = node.get(k)
        if isinstance(v, list) and v:
            return v[0]
        if isinstance(v, str) and v.startswith("http"):
            return v
    for k in ("url_list", "urlList"):
        v = node.get(k)
        if isinstance(v, list) and v:
            return v[0]
    return None


def parse_aweme(data: dict) -> dict:
    """从 _ROUTER_DATA 提取视频/图文信息。"""
    info = {"type": "unknown", "title": "", "author": "", "video_url": None,
            "cover_url": None, "images": [], "music_url": None}
    detail = _find_aweme(data)
    if not isinstance(detail, dict):
        return info
    info["title"] = (detail.get("desc") or (detail.get("share_info") or {}).get("share_title") or "").strip()
    author = detail.get("author") or {}
    if isinstance(author, dict):
        info["author"] = (author.get("nickname") or author.get("unique_id") or "").strip()

    video = detail.get("video") or {}
    if isinstance(video, dict):
        play = video.get("play_addr") or video.get("playAddr") or {}
        url = _first_url(play, "url_list", "urlList")
        if url:
            info["video_url"] = url
            info["type"] = "video"
        info["cover_url"] = _first_url(video.get("cover") or {}, "url_list", "urlList") \
            or (video.get("cover") if isinstance(video.get("cover"), str) and video["cover"].startswith("http") else None)

    images = detail.get("images")
    if isinstance(images, list):
        urls = []
        for im in images:
            if not isinstance(im, dict):
                continue
            u = _first_url(im, "url_list", "urlList")
            if u:
                urls.append(u)
        if urls:
            info["images"] = urls
            info["type"] = "images"

    music = detail.get("music") or {}
    if isinstance(music, dict):
        info["music_url"] = _first_url(music.get("play_url") or {}, "url_list", "urlList")
    return info


def no_watermark(url: str) -> str:
    """playwm -> play，得到无水印地址。"""
    return url.replace("/playwm/", "/play/").replace("playwm", "play")


def _fmt_size(n: int) -> str:
    if n >= 1024 * 1024:
        return f"{n / 1048576:.1f}MB"
    return f"{n / 1024:.0f}KB"


def _fmt_eta(secs: float) -> str:
    if secs >= 3600:
        return f"{secs / 3600:.1f}h"
    if secs >= 60:
        return f"{secs / 60:.0f}m{secs % 60:02.0f}s"
    return f"{secs:.0f}s"


def _exists_nonempty(p: Path) -> bool:
    """文件存在且非空（用于跳过已下载 / 空文件检查）。"""
    return p.exists() and p.stat().st_size > 0


def download(url: str, dest: Path, session: requests.Session, headers: dict,
             label: str = "", log: Callable[[str], None] = print, quiet: bool = False):
    """下载到 dest（先写 dest.part 断点续传，成功后原子改名），带进度与重试。

    quiet=False：控制台用 \r 原位刷新进度；quiet=True：每次进度通过 log 回调输出（供 GUI 用）。
    """
    part = dest.with_name(dest.name + ".part")
    for attempt in range(3):
        try:
            have = part.stat().st_size if part.exists() else 0
            hdrs = dict(headers or {})
            if have:
                hdrs["Range"] = f"bytes={have}-"
            with session.get(url, headers=hdrs, stream=True, timeout=(10, 90)) as r:
                if r.status_code == 416:  # Range 越界 = 文件其实已完整
                    os.replace(part, dest)
                    return True
                r.raise_for_status()
                partial = r.status_code == 206  # 服务器支持断点续传
                total = int(r.headers.get("Content-Length") or 0) + (have if partial else 0)
                done = have if partial else 0
                t0 = time.time()
                last_pct = -10
                with open(part, "ab" if partial else "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 16):
                        if not chunk:
                            continue
                        f.write(chunk)
                        done += len(chunk)
                        if total:
                            pct = done * 100 // total
                            if pct >= last_pct + 2 or done >= total:
                                last_pct = pct
                                elapsed = time.time() - t0
                                speed = done / elapsed if elapsed > 0 else 0
                                eta = _fmt_eta((total - done) / speed) if speed > 0 else "-"
                                line = (f"\r  {label} {pct:3d}% {_fmt_size(done)}/{_fmt_size(total)} "
                                        f"{speed / 1048576:.1f}MB/s ETA {eta}")
                                if quiet:
                                    log(line + "\n")
                                else:
                                    sys.stdout.write(line)
                                    sys.stdout.flush()
                if not _exists_nonempty(part):
                    raise ValueError("empty")
                os.replace(part, dest)
                if not quiet:
                    sys.stdout.write("\r" + " " * 70 + "\r")
                return True
        except (requests.RequestException, ValueError, OSError) as e:
            log(f"  [!] {t('zh', 'download_fail', n=attempt + 1, e=e)}")
            time.sleep(2 * (attempt + 1))
    return False


def _explain_failure(data) -> str:
    """对解析出的数据做常见失败原因判断，返回可读提示。"""
    if isinstance(data, dict):
        # 分享页视频不存在/私密/地区限制：loaderData 中 video 相关字段为 null
        ld = data.get("loaderData")
        if isinstance(ld, dict):
            for key, val in ld.items():
                if val is None and "video" in key:
                    return "dead"
                if isinstance(val, dict) and val.get("videoInfoRes") is None and "video" in key:
                    return "dead"
    return "unknown"


# ---------- 单个作品处理 ----------
def download_one(link_or_text: str, out_dir: Path, session: requests.Session,
                 lang: str = "zh", cover: bool = False, music: bool = False,
                 redownload: bool = False, log: Callable[[str], None] = print) -> Optional[dict]:
    """处理单个分享链接，返回解析信息。"""
    url = extract_url(link_or_text)
    if not url:
        log(f"  [!] {t(lang, 'no_link')}: {link_or_text[:60]}")
        return None
    log(f"  [*] {t(lang, 'parsing')}: {url}")
    aweme_id = resolve_aweme_id(url, session)
    if not aweme_id:
        log(f"  [!] {t(lang, 'resolve_fail')}")
        return None

    page = f"https://www.iesdouyin.com/share/video/{aweme_id}/"
    data = None
    for attempt in range(3):
        try:
            r = session.get(page, headers={"User-Agent": UA_MOBILE}, timeout=(8, 20))
            if r.status_code != 200:
                raise requests.RequestException(f"HTTP {r.status_code}")
            data = _extract_json(r.text)
            if not data:
                raise ValueError(t(lang, "no_data"))
            break
        except (requests.RequestException, ValueError, json.JSONDecodeError) as e:
            if attempt == 2:
                log(f"  [!] {t(lang, 'page_fail', e=e)}")
                return None
            time.sleep(2 * (attempt + 1))

    info = parse_aweme(data)
    if info["type"] == "unknown" and _explain_failure(data) == "dead":
        log(f"  [!] {t(lang, 'dead_video')}")
        return None

    quiet = log is not print  # GUI 等自定义 log 时进度走回调
    video_label = "视频" if lang == "zh" else "video"

    if info["type"] == "video" and info["video_url"]:
        log(f"  [*] {t(lang, 'video_info', title=info['title'][:40] or '(无标题)', author=info['author'] or '未知')}")
        video_url = no_watermark(info["video_url"])
        fname = sanitize_name(f"{info['author']}_{info['title']}") or aweme_id
        # aweme_id 后缀保证不同作品不互相顶掉（同作者空标题等同名场景），同一作品重跑仍可命中跳过
        dest = out_dir / f"{fname}_{aweme_id[:8]}.mp4"
        if _exists_nonempty(dest) and not redownload:
            log(f"  [·] {t(lang, 'exists')}: {dest.name}")
        elif download(video_url, dest, session, {"User-Agent": UA_MOBILE}, label=video_label, log=log, quiet=quiet):
            log(f"  [✓] {t(lang, 'video_saved', path=dest)}")
        info["file"] = str(dest)
        if cover and info["cover_url"]:
            cdest = dest.with_suffix(".jpg")
            if _exists_nonempty(cdest) and not redownload:
                log(f"  [·] {t(lang, 'exists')}: {cdest.name}")
            elif download(info["cover_url"], cdest, session, {"User-Agent": UA_MOBILE}, label="cover", log=log, quiet=quiet):
                log(f"  [✓] {t(lang, 'cover_saved', path=cdest)}")
            info["cover"] = str(cdest)
        if music and info["music_url"]:
            mdest = dest.with_suffix(".mp3")
            if _exists_nonempty(mdest) and not redownload:
                log(f"  [·] {t(lang, 'exists')}: {mdest.name}")
            elif download(info["music_url"], mdest, session, {"User-Agent": UA_MOBILE}, label="music", log=log, quiet=quiet):
                log(f"  [✓] {t(lang, 'music_saved', path=mdest)}")
            info["music"] = str(mdest)
    elif info["type"] == "images" and info["images"]:
        log(f"  [*] {t(lang, 'album_info', n=len(info['images']), author=info['author'] or '未知')}")
        base = sanitize_name(f"{info['author']}_{info['title']}") or aweme_id
        sub = out_dir / f"{base}_{aweme_id[:8]}"
        sub.mkdir(parents=True, exist_ok=True)
        ok = 0
        for i, img_url in enumerate(info["images"], 1):
            ext = Path(img_url.split("?")[0]).suffix or ".jpg"
            if len(ext) > 5:
                ext = ".jpg"
            dest = sub / f"{i:02d}{ext}"
            if _exists_nonempty(dest) and not redownload:
                ok += 1
            elif download(img_url, dest, session, {"User-Agent": UA_MOBILE}, label=f"img{i}", log=log, quiet=quiet):
                ok += 1
        log(f"  [✓] {t(lang, 'album_saved', ok=ok, total=len(info['images']), dir=sub)}")
        info["dir"] = str(sub)
    else:
        log(f"  [!] {t(lang, 'unknown_type')}")
        return None
    return info


def get_clipboard() -> Optional[str]:
    """读取系统剪贴板（优先 tkinter，纯标准库）。"""
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        try:
            return root.clipboard_get()
        finally:
            root.destroy()
    except Exception:
        return None


# ---------- 图形界面 ----------
def run_gui(lang: str) -> int:
    """tkinter 简易图形界面。"""
    try:
        import queue
        import tkinter as tk
        from tkinter import filedialog, scrolledtext
    except ImportError:
        print(t(lang, "gui_no_tk"))
        return 1

    session = requests.Session()
    session.headers.update({"Accept-Language": "zh-CN,zh;q=0.9"})
    cfg = load_config()

    root = tk.Tk()
    root.title(t(lang, "gui_title", ver=__version__))
    root.geometry("680x560")
    root.minsize(560, 420)

    q = queue.Queue()

    # 顶部：链接输入
    tk.Label(root, text=t(lang, "gui_link")).pack(anchor="w", padx=12, pady=(12, 2))
    link_entry = tk.Entry(root)
    link_entry.pack(fill="x", padx=12)
    link_entry.insert(0, get_clipboard() or "")

    # 中间：输出目录
    tk.Label(root, text=t(lang, "gui_out")).pack(anchor="w", padx=12, pady=(10, 2))
    out_row = tk.Frame(root)
    out_row.pack(fill="x", padx=12)
    out_entry = tk.Entry(out_row)
    out_entry.pack(side="left", fill="x", expand=True)
    out_entry.insert(0, cfg.get("output", "downloads"))

    def browse():
        d = filedialog.askdirectory()
        if d:
            out_entry.delete(0, tk.END)
            out_entry.insert(0, d)
    tk.Button(out_row, text=t(lang, "gui_browse"), command=browse).pack(side="left", padx=(6, 0))

    # 功能行
    opt_row = tk.Frame(root)
    opt_row.pack(fill="x", padx=12, pady=(10, 0))
    cb_cover = tk.BooleanVar(value=False)
    cb_music = tk.BooleanVar(value=False)
    cb_redownload = tk.BooleanVar(value=False)
    tk.Checkbutton(opt_row, text="封面 cover", variable=cb_cover).pack(side="left")
    tk.Checkbutton(opt_row, text="音乐 music", variable=cb_music).pack(side="left", padx=10)
    tk.Checkbutton(opt_row, text="重下 redownload", variable=cb_redownload).pack(side="left", padx=10)

    # 按钮
    btn = tk.Button(root, text=t(lang, "gui_download"), width=18)
    btn.pack(pady=10)
    log_box = scrolledtext.ScrolledText(root, height=14, state="disabled", wrap="word")
    log_box.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def append(msg):
        log_box.configure(state="normal")
        log_box.insert(tk.END, msg + "\n")
        log_box.see(tk.END)
        log_box.configure(state="disabled")

    def worker(url_text, out_str, with_cover, with_music, with_redownload):
        def log(msg):
            print(msg)
            q.put(msg)
        try:
            save_config({"output": out_str})
            info = download_one(url_text, Path(out_str), session, lang=lang,
                                cover=with_cover, music=with_music,
                                redownload=with_redownload, log=log)
            if info:
                q.put(f"[✓] {t(lang, 'ok')} {info.get('file') or info.get('dir', '')}")
        except Exception as e:
            q.put(f"[!] {e}")
        finally:
            q.put("__DONE__")

    def on_download():
        text = link_entry.get().strip()
        if not text:
            text = get_clipboard() or ""
        if not text:
            append(f"[!] {t(lang, 'clipboard_empty')}")
            return
        btn.configure(state="disabled", text=t(lang, "gui_downloading"))
        out_str = out_entry.get().strip() or "downloads"
        import threading
        threading.Thread(target=worker, args=(text, out_str, cb_cover.get(), cb_music.get(), cb_redownload.get()), daemon=True).start()

    def poll():
        try:
            while True:
                m = q.get_nowait()
                if m == "__DONE__":
                    btn.configure(state="normal", text=t(lang, "gui_download"))
                else:
                    append(m)
        except queue.Empty:
            pass
        root.after(100, poll)

    btn.configure(command=on_download)
    root.after(100, poll)
    root.mainloop()
    return 0


# ---------- 命令行入口 ----------
def main():
    ap = argparse.ArgumentParser(
        prog="douyin_dl",
        description="抖音无水印视频/图文下载器 v{} · {}（仅供学习研究使用）".format(__version__, "Douyin watermark-free downloader"),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("input", nargs="?", help="分享链接 / 分享文本 / 含链接的txt文件")
    ap.add_argument("-o", "--output", default=None, help="保存目录 (默认 downloads，记住上次选择)")
    ap.add_argument("-b", "--batch", action="store_true", help="输入是 txt 文件，每行一个链接")
    ap.add_argument("--json", action="store_true", help="输出机器可读 JSON 摘要")
    ap.add_argument("--cover", action="store_true", help="同时下载封面图")
    ap.add_argument("--music", action="store_true", help="同时下载背景音乐")
    ap.add_argument("--clipboard", "-c", action="store_true", help="从系统剪贴板读取链接")
    ap.add_argument("--lang", choices=["zh", "en"], default=None, help="界面语言 (默认自动)")
    ap.add_argument("--gui", action="store_true", help="启动图形界面")
    ap.add_argument("--no-config", action="store_true", help="不使用配置文件记住上次目录")
    ap.add_argument("--redownload", action="store_true", help="忽略已下载文件，强制重新下载")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = ap.parse_args()

    cfg = load_config()
    if args.lang:
        lang = args.lang
    elif not args.no_config and cfg.get("lang"):
        lang = cfg["lang"]
    else:
        lang = detect_lang(None)

    if args.gui:
        return run_gui(lang)

    if args.clipboard:
        args.input = get_clipboard() or args.input
        if args.input:
            print(f"  [i] {t(lang, 'clipboard_hint')}")
        else:
            print(f"  [!] {t(lang, 'clipboard_empty')}")

    if not args.input:
        ap.print_help()
        return 1

    out_str = args.output or ("" if args.no_config else cfg.get("output")) or "downloads"
    out_dir = Path(out_str)
    out_dir.mkdir(parents=True, exist_ok=True)
    if not args.no_config:
        save_config({"output": str(out_dir), "lang": lang})

    session = requests.Session()
    session.headers.update({"Accept-Language": "zh-CN,zh;q=0.9"})
    for k in ("ALL_PROXY", "all_proxy"):
        if os.environ.get(k):
            print(f"  [i] {t(lang, 'proxy_hint', k=k)}")

    if args.batch:
        links = [l.strip() for l in Path(args.input).read_text(encoding="utf-8").splitlines() if l.strip()]
        print(f"[*] {t(lang, 'batch_mode', n=len(links))}")
        results, ok = [], 0
        for i, link in enumerate(links, 1):
            print(t(lang, "batch_item", i=i, total=len(links)))
            r = download_one(link, out_dir, session, lang=lang,
                             cover=args.cover, music=args.music, redownload=args.redownload)
            if r:
                results.append(r)
                ok += 1
            if i < len(links):
                sleep = 1.5
                print(f"  [i] {t(lang, 'rate_limit', s=sleep)}")
                time.sleep(sleep)
        print(f"[*] {t(lang, 'batch_ratio', ok=ok, total=len(links))}")
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        r = download_one(args.input, out_dir, session, lang=lang,
                         cover=args.cover, music=args.music, redownload=args.redownload)
        if args.json and r:
            print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n已取消 / Canceled")
        sys.exit(130)
