# -*- coding: utf-8 -*-
"""dump_prompts.py · 导出指定镜 × 指定风格的完整提示词到 UTF-8 文件

用法：python pipeline/dump_prompts.py --shot 2 --styles A,B,C --out _p.txt
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, NEGATIVE_DEFAULT, dedupe_csv, read_csv
from stylelib import (STYLES, build_style_prompt, build_negative,
                      quality_suffix, tier_of, overlays_for,
                      needs_marker_echo, enforce_shot_size)
from step3_blocks import (build_first_frame, parse_md_blocks, parse_table,
                          SECONDARY_BY_SCENE)

SLUG = "demo_雨夜的订单"
MARKERS = {
    "C_LEAD": "左手腕旧钢带手表，右眉尾一道浅疤",
    "C_VILLAIN": "右耳金色圆环耳饰",
    "C_ALLY": "颈间细银链",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shot", type=int, default=2)
    ap.add_argument("--styles", required=True)
    ap.add_argument("--out", default="_prompts.txt")
    a = ap.parse_args()

    rows = read_csv(ROOT / "04_场景分镜" / SLUG / "BLOCK_EP01.csv")
    row = next(r for r in rows if int(r["shot"]) == a.shot)

    locks = parse_md_blocks((ROOT / "02_角色" / SLUG / "外观锁定词.md").read_text(encoding="utf-8"))
    exprs = parse_table((ROOT / "02_角色" / SLUG / "表情片段库.md").read_text(encoding="utf-8"))
    outfits = parse_table((ROOT / "02_角色" / SLUG / "服装表.md").read_text(encoding="utf-8"))
    scenes = parse_md_blocks((ROOT / "04_场景分镜" / SLUG / "场景设定.md").read_text(encoding="utf-8"))
    script = json.loads((ROOT / "01_剧本" / SLUG / "script.json").read_text(encoding="utf-8-sig"))
    ep_blocks = {(e["ep"], b["block"]): b for e in script["episodes"] for b in e["blocks"]}
    blk = ep_blocks[(int(row["ep"]), int(row["block"]))]

    char = row["char_ids"].split("|")[0]
    lock = locks[char]
    expr_desc = exprs[row["expr_code"]]
    outfit_desc = outfits[row["outfit"]]
    scene_env = scenes[blk["scene"]]
    marker = MARKERS.get(char, "")

    out_lines = [f"# 镜 EP{row['ep']} SH{a.shot} | {row['shot_size']} {row['camera']} "
                 f"| {row['expr_code']} i{row['expr_int']} | {char} | 台词：{row['line']}", ""]

    for sid in [s.strip() for s in a.styles.split(",") if s.strip()]:
        if sid not in STYLES:
            out_lines.append(f"## [跳过] 未知风格 {sid}")
            continue
        ols = overlays_for(sid)
        sp = build_style_prompt(sid, ols)
        suffix = quality_suffix(sid, ols)
        echo = needs_marker_echo(sid, ols)
        enf = enforce_shot_size(row["shot_size"])
        p = build_first_frame(
            lock=lock, size=row["shot_size"], camera=row["camera"],
            expr_desc=expr_desc, chars=[], outfit_desc=outfit_desc,
            scene_env=scene_env, product_desc=None, product_moment="",
            style_prompt=sp, suffix=suffix, marker=marker, echo_marker=echo)
        neg = dedupe_csv(NEGATIVE_DEFAULT + ", " + build_negative(sid, ols)
                         + ", " + enf["neg"]
                         + ", 文字水印, 字幕, logo, 招牌文字乱码")
        out_lines += [
            f"## {sid} · {STYLES[sid]['name']} [{tier_of(sid)}档] + {ols}"
            f"（风格 {len([x for x in sp.split('，') if x])} 短语"
            f"{'，标志物回声' if echo else ''}）",
            "",
            "### PROMPT",
            p,
            "",
            "### NEGATIVE",
            neg,
            "",
            "-" * 60,
            "",
        ]

    Path(a.out).write_text("\n".join(out_lines), encoding="utf-8")
    print(f"已写出 {a.out}（{len(out_lines)} 行）")


if __name__ == "__main__":
    main()
