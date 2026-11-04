# -*- coding: utf-8 -*-
"""make_grid2.py · 两行四列拼图（A 组 / B 组各一行）"""
import subprocess
from pathlib import Path

FFMPEG = "ffmpeg"
D = Path(r"E:\dsh\AI短剧_对照图\round2")
W, H = 512, 768

A = ["A_CINEMA_REAL", "A_DOUYIN_HIGH", "A_RETRO_HK", "A_CYBERPUNK"]
B = ["B_ROMANCE_SOFT", "B_RETRO_90S_CN", "B_SUSPENSE_DARK", "B_ANCIENT_CN"]


def build(names, out):
    files = [D / f"{n}.png" for n in names if (D / f"{n}.png").exists()]
    n = len(files)
    inputs = []
    for f in files:
        inputs += ["-i", str(f)]
    fil = []
    for i in range(n):
        fil.append(f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
                   f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x1a1a1a,"
                   f"drawbox=x=0:y=0:w={W}:h={H}:color=0x444444:t=3[v{i}]")
    fil.append("".join(f"[v{i}]" for i in range(n)) + f"hstack=inputs={n}[out]")
    r = subprocess.run(["ffmpeg", "-hide_banner", "-y", *inputs,
                        "-filter_complex", ";".join(fil), "-map", "[out]",
                        "-q:v", "2", str(out)],
                       capture_output=True, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        print("FAIL", (r.stderr or b"")[-400:].decode("utf-8", "replace"))
    else:
        print(f"OK {out.name}  {out.stat().st_size:,} bytes")


def vstack(p1, p2, out):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-y", "-i", str(p1), "-i", str(p2),
                        "-filter_complex", "[0:v][1:v]vstack=inputs=2[out]",
                        "-map", "[out]", "-q:v", "2", str(out)],
                       capture_output=True, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        print("VSTACK FAIL", (r.stderr or b"")[-400:].decode("utf-8", "replace"))
    else:
        print(f"OK {out.name}  {out.stat().st_size:,} bytes")


build(A, D / "gridA.jpg")
build(B, D / "gridB.jpg")
vstack(D / "gridA.jpg", D / "gridB.jpg", D / "对照_全8种.jpg")
