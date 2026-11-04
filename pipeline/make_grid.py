# -*- coding: utf-8 -*-
"""make_grid.py · 把多张风格对照图拼成一张横向对比图

用法：python pipeline/make_grid.py [对照目录]
"""
import subprocess
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "风格对照"
FFMPEG = "ffmpeg"

ORDER = ["CINEMA_REAL", "DOUYIN_HIGH", "RETRO_HK", "CYBERPUNK"]


def main(d: Path):
    files = [d / f"{s}.png" for s in ORDER if (d / f"{s}.png").exists()]
    if not files:
        print("没有找到对照图")
        return
    # 统一缩放到 512x768，横向拼接，中间留白
    inputs = []
    for f in files:
        inputs += ["-i", str(f)]
    n = len(files)
    # 每个缩放后 pad 到 512x768
    filters = []
    for i in range(n):
        filters.append(f"[{i}:v]scale=512:768:force_original_aspect_ratio=decrease,"
                       f"pad=512:768:(ow-iw)/2:(oh-ih)/2:color=0x1a1a1a,"
                       f"drawbox=x=0:y=0:w=512:h=768:color=0x444444:t=3[v{i}]")
    # 横向堆叠
    if n > 1:
        stack_in = "".join(f"[v{i}]" for i in range(n))
        filters.append(f"{stack_in}hstack=inputs={n}[out]")
    else:
        filters.append("[v0]copy[out]")

    out = d / "对照_grid.jpg"
    cmd = ["ffmpeg", "-hide_banner", "-y", *inputs,
           "-filter_complex", ";".join(filters), "-map", "[out]",
           "-q:v", "2", str(out)]
    r = subprocess.run(cmd, capture_output=True, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        print("拼接失败：", (r.stderr or b"")[-500:].decode("utf-8", "replace"))
        return
    print(f"横向对比图：{out}  ({out.stat().st_size:,} bytes)")
    print(f"顺序：{' | '.join(ORDER[:n])}")


if __name__ == "__main__":
    d = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT / "EP01_SH02"
    main(d)
