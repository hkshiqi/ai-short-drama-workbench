#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""style_compare.py · 同一镜跑多种风格，出对照图

用法：
  python pipeline/style_compare.py                 # 默认 3 风格 × 1 镜
  python pipeline/style_compare.py --shot 3        # 指定镜号
  python pipeline/style_compare.py --styles CINEMA_REAL,DOUYIN_HIGH,RETRO_HK,CYBERPUNK
  python pipeline/style_compare.py --dry           # 只打印提示词不生成（省额度）

产出：
  风格对照/EP01_SH{N}/{STYLE_ID}.png
  风格对照/EP01_SH{N}/对照表.md
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import ROOT, dedupe_csv, read_csv, NEGATIVE_DEFAULT
from stylelib import STYLES, build_style_prompt, build_negative, quality_suffix, tier_of

SLUG = "demo_雨夜的订单"
OUT_DIR = ROOT / "风格对照"

MARKERS = {
    "C_LEAD": "左手腕旧钢带手表，右眉尾一道浅疤",
    "C_VILLAIN": "右耳金色圆环耳饰",
    "C_ALLY": "颈间细银链",
}


def build_prompt_for_style(row: dict, lock: str, scene_env: str,
                           expr_desc: str, outfit_desc: str,
                           style_id: str, overlays: list[str],
                           marker: str = "") -> tuple[str, str]:
    """★ 必须走正式拼装函数 build_first_frame，不许手工拼（实测教训）"""
    from step3_blocks import build_first_frame
    from stylelib import (build_negative as style_neg, build_style_prompt,
                          enforce_shot_size, needs_marker_echo, quality_suffix)
    sp = build_style_prompt(style_id, overlays)
    suffix = quality_suffix(style_id, overlays)
    echo = needs_marker_echo(style_id, overlays)
    p = build_first_frame(
        lock=lock, size=row["shot_size"], camera=row["camera"],
        expr_desc=expr_desc, chars=[], outfit_desc=outfit_desc,
        scene_env=scene_env, product_desc=None, product_moment="",
        style_prompt=sp, suffix=suffix, marker=marker, echo_marker=echo,
    )
    neg = dedupe_csv(
        NEGATIVE_DEFAULT + ", " + style_neg(style_id, overlays)
        + ", " + enforce_shot_size(row["shot_size"])["neg"]
        + ", 文字水印, 字幕, logo, 招牌文字乱码")
    return p, neg


def run(shot_no: int = 2, style_ids: list[str] | None = None,
        dry: bool = False) -> Path:
    rows = read_csv(ROOT / "04_场景分镜" / SLUG / "BLOCK_EP01.csv")
    row = next(r for r in rows if int(r["shot"]) == shot_no)

    # 载入锁定词与场景
    from step3_blocks import parse_md_blocks, parse_table, SECONDARY_BY_SCENE
    locks = parse_md_blocks((ROOT / "02_角色" / SLUG / "外观锁定词.md").read_text(encoding="utf-8"))
    exprs = parse_table((ROOT / "02_角色" / SLUG / "表情片段库.md").read_text(encoding="utf-8"))
    outfits = parse_table((ROOT / "02_角色" / SLUG / "服装表.md").read_text(encoding="utf-8"))
    scenes = parse_md_blocks((ROOT / "04_场景分镜" / SLUG / "场景设定.md").read_text(encoding="utf-8"))

    char = row["char_ids"].split("|")[0]
    lock = locks[char]
    expr_desc = exprs[row["expr_code"]]
    outfit_desc = outfits[row["outfit"]]

    # 场景：用块卡所在块的场景
    import json
    script = json.loads((ROOT / "01_剧本" / SLUG / "script.json").read_text(encoding="utf-8-sig"))
    ep_blocks = {(e["ep"], b["block"]): b for e in script["episodes"] for b in e["blocks"]}
    blk = ep_blocks[(int(row["ep"]), int(row["block"]))]
    scene_env = scenes[blk["scene"]]

    style_ids = style_ids or ["CINEMA_REAL", "DOUYIN_HIGH", "RETRO_HK"]
    out = OUT_DIR / f"EP{int(row['ep']):02d}_SH{shot_no:02d}"
    out.mkdir(parents=True, exist_ok=True)

    md = [f"# 风格对照 · EP{int(row['ep']):02d} SH{shot_no:02d}", "",
          f"**原始镜**：{row['shot_size']} {row['camera']} {row['move']} "
          f"{row['dur_sec']}s ｜ {row['expr_code']} i{row['expr_int']} ｜ {char}",
          f"**台词**：{row['line']}", "",
          "| 风格 | 名称 | 档 | 适用 | 生成文件 |", "|---|---|---|---|---|"]

    prompts = {}
    for sid in style_ids:
        if sid not in STYLES:
            print(f"  [跳过] 未知风格 {sid}")
            continue
        # 每个风格配它的推荐修饰层
        from stylelib import overlays_for
        rec_overlays = overlays_for(sid)
        p, n = build_prompt_for_style(row, lock, scene_env, expr_desc,
                                      outfit_desc, sid, rec_overlays,
                                      marker=MARKERS.get(char, ""))
        prompts[sid] = (p, n, rec_overlays)
        st = STYLES[sid]
        md.append(f"| `{sid}` | {st['name']} | {tier_of(sid)} | {st['use_for']} | "
                  f"{sid}.png |")
        print(f"\n{'='*66}\n{sid} · {st['name']} [{tier_of(sid)}档] + {rec_overlays}")
        print(f"{'-'*66}\n{p}\n{'-'*66}\n负向：{n}")

        if dry:
            continue

        # ---- 真实生成：调本环境生图能力 ----
        try:
            _gen_image(p, n, out / f"{sid}.png")
            print(f"  → {out / f'{sid}.png'}")
        except Exception as e:
            print(f"  [生成失败] {type(e).__name__}: {e}")

    # 写提示词明细
    detail = ["", "## 提示词明细", ""]
    for sid, (p, n, ols) in prompts.items():
        detail += [f"### {sid} + {ols}", "", "```", p, "```", "",
                   f"**负向**：`{n}`", ""]
    md += detail

    (out / "对照表.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\n对照表：{out / '对照表.md'}")
    return out


def _gen_image(prompt: str, negative: str, dst: Path):
    """调环境生图。若不可用则抛异常，由上层记录。"""
    # 本环境通过 MCP 工具生图，无法在 Python 内直接调；
    # 这里只负责把提示词落盘，实际生成由会话侧执行。
    raise NotImplementedError(
        "Python 内无法直调生图，提示词已落盘，由会话侧调用 workbuddy_draw_image")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--shot", type=int, default=2)
    ap.add_argument("--styles", default="")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    sids = [s.strip() for s in a.styles.split(",") if s.strip()] or None
    run(shot_no=a.shot, style_ids=sids, dry=a.dry)
