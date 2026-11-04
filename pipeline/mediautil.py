# -*- coding: utf-8 -*-
"""mediautil.py · 媒体工具（Windows + 中文路径的安全封装）

关键坑：Windows 上 subprocess 默认用 GBK 解码 stdout，
若 ffprobe 输出含非 ASCII 或路径含中文，float() 会静默失败返回 0。
解法：全程用 bytes，手工 decode('ascii', 'ignore')。
"""
from __future__ import annotations

import subprocess
from pathlib import Path

FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"


def _run_bytes(args: list[str], timeout: int = 60) -> tuple[int, bytes, bytes]:
    r = subprocess.run(args, capture_output=True, encoding=None,
                       stdin=subprocess.DEVNULL, timeout=timeout)
    return (r.returncode,
            r.stdout if isinstance(r.stdout, (bytes, bytearray)) else b"",
            r.stderr if isinstance(r.stderr, (bytes, bytearray)) else b"")


def dur(path: Path) -> float:
    """视频/音频时长（秒）。安全版：bytes → ascii → float
    注意：ffprobe 不支持 -nostdin（那是 ffmpeg 的选项），用 stdin=DEVNULL 代替。"""
    if not path.exists():
        return 0.0
    rc, out, err = _run_bytes(
        [FFPROBE, "-v", "error",
         "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)])
    txt = out.decode("ascii", "ignore").strip()
    try:
        return float(txt)
    except ValueError:
        rc2, out2, err2 = _run_bytes([FFMPEG, "-hide_banner", "-i", str(path)])
        for line in err2.decode("ascii", "ignore").splitlines():
            if "Duration:" in line:
                frag = line.split("Duration:")[1].split(",")[0].strip()
                try:
                    h, m, s = frag.split(":")
                    return int(h) * 3600 + int(m) * 60 + float(s)
                except ValueError:
                    continue
        return 0.0


def run(args: list[str], timeout: int = 300) -> None:
    rc, out, err = _run_bytes(args, timeout=timeout)
    if rc != 0:
        raise RuntimeError(f"ffmpeg rc={rc}: "
                           + err.decode("utf-8", "replace")[-600:])
