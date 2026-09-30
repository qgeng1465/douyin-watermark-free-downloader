# -*- coding: utf-8 -*-
"""douyin_dl 核心逻辑单元测试（无需真实网络）"""
import sys, os, json, tempfile
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import douyin_dl as D

fails = 0
def check(name, cond, detail=""):
    global fails
    print(("PASS " if cond else "FAIL ") + name + (f"  | {detail}" if detail and not cond else ""))
    if not cond: fails += 1

# 1. extract_url：各种分享文本
for txt, expect in [
    ("7.43 复制打开抖音，看看视频 https://v.douyin.com/abc123/ 哈", "https://v.douyin.com/abc123"),
    ("https://www.iesdouyin.com/share/video/7412345678901234567/", "https://www.iesdouyin.com/share/video/7412345678901234567"),
    ("https://www.douyin.com/video/7412345678901234567 复制此链接", "https://www.douyin.com/video/7412345678901234567"),
    ("随便一段没有链接的文字", None),
]:
    got = D.extract_url(txt)
    check(f"extract_url: {txt[:40]}", got == expect, f"got={got}")

# 2. resolve_aweme_id：长链直接提取
check("resolve long video url", D.resolve_aweme_id("https://www.douyin.com/video/7412345678901234567", None) == "7412345678901234567")
check("resolve iesdouyin url", D.resolve_aweme_id("https://www.iesdouyin.com/share/video/9998887776665554443/", None) == "9998887776665554443")

# 3. _extract_json：_ROUTER_DATA 形态
html1 = '<html><script>window._ROUTER_DATA = {"loaderData": {"x": 1}};</script></html>'
d1 = D._extract_json(html1)
check("extract _ROUTER_DATA", isinstance(d1, dict) and d1.get("loaderData",{}).get("x")==1, f"got={d1}")

# 4. _extract_json：RENDER_DATA URL编码形态
import urllib.parse
payload = json.dumps({"a": {"b": 2}})
html2 = f'<script id="RENDER_DATA" type="application/json">{urllib.parse.quote(payload)}</script>'
d2 = D._extract_json(html2)
check("extract RENDER_DATA", isinstance(d2, dict) and d2.get("a",{}).get("b")==2, f"got={d2}")

# 5. parse_aweme：视频（含封面/音乐提取）
video_data = {"loaderData": {"video_(id)": {"videoInfoRes": {"item_list": [{
    "desc": "测试视频标题",
    "author": {"nickname": "测试作者"},
    "video": {"play_addr": {"url_list": ["https://aweme.snssdk.com/aweme/v1/playwm/?video_id=ABC", "https://x2"]},
              "cover": {"url_list": ["https://p3.douyinpic.com/cover.jpeg"]}},
    "music": {"play_url": {"url_list": ["https://m"]}}
}]}}}}
v = D.parse_aweme(video_data)
check("parse video type", v["type"]=="video", f"got={v['type']}")
check("parse video title", v["title"]=="测试视频标题")
check("parse video author", v["author"]=="测试作者")
check("parse video url", v["video_url"] and v["video_url"].startswith("https://aweme.snssdk.com/aweme/v1/playwm"), f"got={v['video_url']}")
check("parse cover url", v["cover_url"]=="https://p3.douyinpic.com/cover.jpeg", f"got={v['cover_url']}")
check("parse music url", v["music_url"]=="https://m", f"got={v['music_url']}")
check("no_watermark replace", D.no_watermark("https://aweme.snssdk.com/aweme/v1/playwm/?a=1") == "https://aweme.snssdk.com/aweme/v1/play/?a=1")

# 6. parse_aweme：图文
img_data = {"loaderData": {"x": {"item_list": [{
    "desc": "测试图文", "author": {"nickname": "图作者"},
    "images": [{"url_list": ["https://p1.douyinpic.com/aa.jpeg?high", "https://p1.douyinpic.com/aa.jpeg"]},
               {"url_list": ["https://p2.douyinpic.com/bb.jpeg"]}]
}]}}}
im = D.parse_aweme(img_data)
check("parse images type", im["type"]=="images", f"got={im['type']}")
check("parse images count", len(im["images"])==2, f"got={len(im['images'])}")

# 7. sanitize_name（8 个非法字符全部替换为 _）
_bad = 'a/b:c*d?"<>|'
check("sanitize illegal chars", D.sanitize_name(_bad) == "a_b_c_d_____", f"got={D.sanitize_name(_bad)}")

# 8. i18n：中英双语文案
check("i18n zh", D.t("zh", "video_saved", path="x") == "已保存: x")
check("i18n en", D.t("en", "video_saved", path="x") == "Saved: x")
check("i18n fallback", D.t("en", "no_such_key") == "no_such_key")

# 9. 死链识别：video_layout 为 null 时应判定 dead
dead_data = {"loaderData": {"video_(id)/page": {"videoInfoRes": None}, "video_layout": None}}
check("dead video detect", D._explain_failure(dead_data) == "dead", f"got={D._explain_failure(dead_data)}")
live_data = {"loaderData": {"video_(id)/page": {"videoInfoRes": {"item_list": [{"desc": "x"}]}}}}
check("live video detect", D._explain_failure(live_data) == "unknown")

# 10. 配置持久化读写
orig = D.CONFIG_PATH
D.CONFIG_PATH = D.CONFIG_PATH.with_suffix(".test.json")
try:
    D.save_config({"output": "D:/videos", "lang": "en"})
    cfg = D.load_config()
    check("config roundtrip", cfg.get("output")=="D:/videos" and cfg.get("lang")=="en", f"got={cfg}")
finally:
    if D.CONFIG_PATH.exists(): D.CONFIG_PATH.unlink()
    D.CONFIG_PATH = orig

# 11. 语言检测
os.environ["LANG"] = "en_US.UTF-8"
check("detect_lang default zh", D.detect_lang(None) == "zh")  # 抖音默认中文
check("detect_lang explicit", D.detect_lang("en") == "en")
check("detect_lang explicit zh", D.detect_lang("zh") == "zh")

# 12. CLI --help / --version / --lang en --help
import subprocess
r = subprocess.run([sys.executable, "douyin_dl.py", "--help"], capture_output=True, text=True)
check("cli --help exit0", r.returncode == 0, r.stderr[:200])
r2 = subprocess.run([sys.executable, "douyin_dl.py", "--version"], capture_output=True, text=True)
check("cli --version", r2.returncode == 0 and D.__version__ in r2.stdout, r2.stdout[:80])

# 13. 集成：download_one 全流程（stub session，无外网）
VIDEO_BYTES = b"FAKE-MP4-BYTES-" * 1000  # ~14KB 假视频
class _FakeResp:
    def __init__(self, url, text="", content=b"", status=200):
        self.url, self.text, self._content, self.status_code = url, text, content, status
        self.headers = {"Content-Length": str(len(content))}
    def raise_for_status(self):
        if self.status_code >= 400: raise Exception(f"HTTP {self.status_code}")
    def iter_content(self, chunk_size=1 << 16):
        for i in range(0, len(self._content), chunk_size):
            yield self._content[i:i + chunk_size]
    def __enter__(self): return self
    def __exit__(self, *a): return False

class _FakeSession:
    def __init__(self):
        self.headers = {}
    def get(self, url, **kw):
        if "iesdouyin.com/share/video/" in url:
            page_payload = {"loaderData": {"video_(id)/page": {"videoInfoRes": {"item_list": [{
                "desc": "集成测试", "author": {"nickname": "作者A"},
                "video": {"play_addr": {"url_list": ["https://aweme.snssdk.com/aweme/v1/playwm/?video_id=ITEST"]}}}]}}}}
            html = f'<html><script>window._ROUTER_DATA = {json.dumps(page_payload, ensure_ascii=False)};</script></html>'
            return _FakeResp(url, text=html)
        if "v.douyin.com" in url:
            return _FakeResp("https://www.douyin.com/video/7412345678901234567")
        return _FakeResp(url, content=VIDEO_BYTES)

# 13.1 断点续传：.part + Range + 原子改名
class _ResumeSession:
    def __init__(self):
        self.ranges = []
    def get(self, url, headers=None, **kw):
        self.ranges.append((headers or {}).get("Range"))
        has = bool(headers and headers.get("Range"))
        return _FakeResp(url, content=b"WORLD", status=(206 if has else 200))

with tempfile.TemporaryDirectory() as td2:
    td2 = Path(td2)
    dest = td2 / "v.mp4"
    (td2 / "v.mp4.part").write_bytes(b"HELLO")  # 已有 5 字节
    rs = _ResumeSession()
    ok = D.download("https://aweme.snssdk.com/aweme/v1/play/?x=1", dest, rs,
                    {"User-Agent": "ua"}, label="v", quiet=True)
    check("resume appends part", ok and dest.read_bytes() == b"HELLOWORLD", f"ok={ok}")
    check("resume sends Range", rs.ranges == ["bytes=5-"], f"ranges={rs.ranges}")
    check("resume renames part", not (td2 / "v.mp4.part").exists())

with tempfile.TemporaryDirectory() as td3:
    td3 = Path(td3)
    dest3 = td3 / "v.mp4"
    rs3 = _ResumeSession()
    ok3 = D.download("https://aweme.snssdk.com/aweme/v1/play/?x=2", dest3, rs3,
                     {"User-Agent": "ua"}, label="v", quiet=True)
    check("download no part no range", ok3 and rs3.ranges == [None] and dest3.read_bytes() == b"WORLD", f"ok={ok3}")

# 13.2 跳过已下载：视频文件已存在时不重复下载（文件保持原样）
with tempfile.TemporaryDirectory() as td4:
    td4 = Path(td4)
    existing = td4 / "作者A_集成测试.mp4"
    existing.write_bytes(b"OLD")
    info2 = D.download_one("https://v.douyin.com/abc123/", td4, _FakeSession(), lang="zh")
    check("skip existing video", info2 and existing.read_bytes() == b"OLD",
          f"file={existing.read_bytes()[:10]}")

with tempfile.TemporaryDirectory() as td:
    info = D.download_one("https://v.douyin.com/abc123/", Path(td), _FakeSession(), lang="zh")
    fp = Path(info["file"]) if info else None
    check("integration download_one video", info and info["type"] == "video" and fp and fp.exists() and fp.stat().st_size > 0, f"got={info}")

print(f"\n{'ALL PASS' if fails==0 else str(fails)+' FAILED'}")
sys.exit(1 if fails else 0)
