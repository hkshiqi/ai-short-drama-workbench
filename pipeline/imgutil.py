# -*- coding: utf-8 -*-
"""imgutil.py · 图像指纹工具（一次读像素，Python 内计算）

性能关键：验证 24 镜 × 4 张图 × 多区域 → 若每区域起一次 ffmpeg 会跑 600+ 次进程。
这里改成**每张图只起一次 ffmpeg**，读 64x114 的 raw RGB，后续全部在内存算。
"""
from __future__ import annotations

import colorsys
import subprocess
from pathlib import Path

FFMPEG = "ffmpeg"
W, H = 72, 128      # 采样分辨率（竖屏 9:16 近似）


def read_small(path: Path) -> bytes | None:
    if not path.exists():
        return None
    r = subprocess.run(
        [FFMPEG, "-hide_banner", "-nostdin", "-v", "error", "-i", str(path), "-vf",
         f"scale={W}:{H},format=rgb24", "-f", "rawvideo", "-"],
        capture_output=True, encoding=None, stdin=subprocess.DEVNULL, timeout=60)
    out = r.stdout
    if not isinstance(out, (bytes, bytearray)) or len(out) < W * H * 3:
        return None
    return bytes(out[: W * H * 3])


def px(data: bytes, x: int, y: int) -> tuple[int, int, int]:
    i = (y * W + x) * 3
    return data[i], data[i + 1], data[i + 2]


def region_avg(data: bytes, x0f: float, y0f: float,
               x1f: float, y1f: float) -> tuple[int, int, int]:
    x0, x1 = int(W * x0f), max(int(W * x0f) + 1, int(W * x1f))
    y0, y1 = int(H * y0f), max(int(H * y0f) + 1, int(H * y1f))
    sr = sg = sb = n = 0
    for y in range(y0, min(y1, H)):
        for x in range(x0, min(x1, W)):
            r, g, b = px(data, x, y)
            sr += r; sg += g; sb += b; n += 1
    if n == 0:
        return (0, 0, 0)
    return (sr // n, sg // n, sb // n)


def hue_of(rgb) -> float:
    r, g, b = [x / 255.0 for x in rgb]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return h * 360


def hue_dist(a: float, b: float) -> float:
    d = abs(a - b) % 360
    return min(d, 360 - d)


def brightness(rgb) -> float:
    return sum(rgb) / 3.0


def signature(path: Path) -> dict | None:
    """返回一张图的关键指纹
    - rgb       全图平均色（场景基调）
    - top_rgb   顶部角色定色块（角色签名）
    - bars      景别横条数（在第 20%~45% 高度扫白条）
    - ebar      表情强度竖条数（在第 52%~72% 高度扫竖条）
    """
    data = read_small(path)
    if data is None:
        return None

    rgb = region_avg(data, 0, 0, 1, 1)
    top_rgb = region_avg(data, 0.25, 0.02, 0.75, 0.08)

    # 景别横条：在 x∈[0.10,0.90] 的中心行里数"亮→暗"跳变
    bars = 0
    prev_white = False
    for yf in [i / 100.0 for i in range(18, 46)]:
        y = int(H * yf)
        if y >= H:
            break
        c = region_avg(data, 0.10, yf, 0.90, yf + 1.0 / H)
        white = brightness(c) > 150
        if white and not prev_white:
            bars += 1
        prev_white = white

    # 表情竖条：在 y∈[0.55,0.70] 的横带里数亮块
    ebar = 0
    prev_white = False
    for xf in [i / 100.0 for i in range(6, 60)]:
        x = int(W * xf)
        if x >= W:
            break
        c = region_avg(data, xf, 0.55, xf + 1.0 / W, 0.70)
        white = brightness(c) > 120
        if white and not prev_white:
            ebar += 1
        prev_white = white

    return {"rgb": rgb, "top_rgb": top_rgb, "bars": bars, "ebar": ebar,
            "hue": hue_of(rgb), "top_hue": hue_of(top_rgb)}
