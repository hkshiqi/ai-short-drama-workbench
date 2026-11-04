# -*- coding: utf-8 -*-
"""show_prompt.py · 打印某镜拼装结果，用于人工核对提示词质量"""
import csv
import sys
from pathlib import Path

p = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    "04_场景分镜/demo_雨夜的订单/BLOCK_EP01.csv")
rows = list(csv.DictReader(open(p, encoding="utf-8-sig")))

out = []
for i, r in enumerate(rows):
    out.append(f"{'='*70}")
    out.append(f"EP{r['ep']} B{r['block']} SH{r['shot']}  "
               f"{r['shot_size']} {r['camera']} {r['move']}  "
               f"{r['dur_sec']}s  {r['model_tag']}")
    out.append(f"风格：{r['style_id']} + {r['style_overlays']}")
    out.append("--- first_frame_prompt ---")
    out.append(r["first_frame_prompt"])
    out.append("--- video_prompt ---")
    out.append(r["video_prompt"])
    out.append("--- negative ---")
    out.append(r["negative"])
    out.append(f"--- line: {r['line']} ---")

Path("_prompt_preview.txt").write_text("\n".join(out), encoding="utf-8")
print(f"已写出 _prompt_preview.txt（{len(rows)} 镜）")
