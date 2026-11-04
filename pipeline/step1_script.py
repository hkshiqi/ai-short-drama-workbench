# -*- coding: utf-8 -*-
"""step1_script.py · 第 ① 步门禁：故事 → 剧本

跑 8 项结构门禁。全绿才允许进第 ② 步。
这是"故事体检"的可执行版本——不合格当场报出来，不硬写。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import (BAR_SEC, BLOCK_SEC, MAX_SHOTS_PER_BLOCK, MIN_SHOTS_PER_BLOCK,
                    ROOT, Gate, Project, bars_to_sec, is_on_grid, log, read_json,
                    save_gate, TOL_BLOCK)

SLUG = "demo_雨夜的订单"


def run(slug: str = SLUG) -> Gate:
    proj = Project(ROOT, slug)
    script = read_json(proj.d_script / "script.json")
    g = Gate("第①步 · 剧本门禁")

    spec = script["spec"]
    eps = script["episodes"]
    chars = {c["id"] for c in script["characters"]}
    scenes = {s["id"] for s in script["scenes"]}

    # ---------- 1. 集数 ----------
    g.eq(len(eps), spec["eps"], "集数与 spec 一致")

    hook_types = []
    for ep in eps:
        epn = ep["ep"]
        blocks = ep["blocks"]

        # ---------- 2. 块数 ----------
        g.eq(len(blocks), spec["blocks_per_ep"], f"EP{epn} 块数 = {spec['blocks_per_ep']}")

        # ---------- 3. 每块时长 = 15.000s ----------
        for b in blocks:
            total = sum(s["dur_sec"] for s in b["shots"])
            g.check(abs(total - BLOCK_SEC) < TOL_BLOCK,
                    f"EP{epn}B{b['block']:02d} 块内时长 = 15.000s",
                    f"实际 {total:.3f}s")

            # ---------- 4. 每块镜数 ----------
            n = len(b["shots"])
            g.num(n, MIN_SHOTS_PER_BLOCK, MAX_SHOTS_PER_BLOCK,
                  f"EP{epn}B{b['block']:02d} 镜数 {n} 在 [4,6]")

            # ---------- 5. 每镜时长在节拍网格上 ----------
            for s in b["shots"]:
                g.check(is_on_grid(s["dur_sec"]),
                        f"EP{epn}B{b['block']:02d}SH{s['shot']:02d} 时长在网格",
                        f"{s['dur_sec']}s")
                g.eq(s["dur_bar"], round(s["dur_sec"] / BAR_SEC),
                     f"EP{epn}B{b['block']:02d}SH{s['shot']:02d} dur_bar 自洽")

                # ---------- 6. 单镜人数 ≤2 ----------
                g.num(len(s["chars"]), 1, 2,
                      f"EP{epn}B{b['block']:02d}SH{s['shot']:02d} 人数 ≤2",
                      )
                # 角色/场景存在
                for c in s["chars"]:
                    g.in_(c, chars, f"EP{epn}B{b['block']:02d}SH{s['shot']:02d} 角色 {c} 已注册")
                g.in_(b["scene"], scenes, f"EP{epn}B{b['block']:02d} 场景已注册")

                # 表情码合法
                g.check(s["expr"].startswith("EXP_"),
                        f"EP{epn}B{b['block']:02d}SH{s['shot']:02d} 表情码合法", s["expr"])
                g.num(s["expr_int"], 1, 3,
                      f"EP{epn}B{b['block']:02d}SH{s['shot']:02d} 表情强度 1-3")

                # BGM 层
                for layer in [s["bgm_layer"]]:
                    g.check(layer in ("PAD", "LOOP", "STRINGS", "HIT", "—"),
                            f"EP{epn}B{b['block']:02d}SH{s['shot']:02d} BGM层合法", layer)

            # ---------- 7. 每块必须有情绪相位 + 软钩 ----------
            g.check(bool(b.get("phase")), f"EP{epn}B{b['block']:02d} 有情绪相位", b.get("phase", ""))
            g.check(bool(b.get("soft_hook")), f"EP{epn}B{b['block']:02d} 有软钩", b.get("soft_hook", ""))
            g.check(bool(b.get("emotion_arc")), f"EP{epn}B{b['block']:02d} 有情绪曲线",
                    b.get("emotion_arc", ""))

            # ---------- 7b. 台词容量检查（关键：字数是块容量的硬约束）----------
            # 中文语速约 4.2 字/秒；8 小节 = 15s → 单块可容纳约 63 字纯台词，
            # 但要给呼吸/停顿留 30% 余量 → 硬上限 44 字。超过则配音吸不进网格。
            import re as _re
            total_chars = 0
            for s in b["shots"]:
                if s["line"] in ("—", "-", ""):
                    continue
                total_chars += len(_re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", s["line"]))
            g.num(total_chars, 0, 44,
                  f"EP{epn}B{b['block']:02d} 台词字数 {total_chars} ≤44（配音可吸进 8 小节）")

        # ---------- 8. 每集硬钩 + 类型不连续重复 ----------
        hh = ep.get("hard_hook") or {}
        g.check(bool(hh.get("line")), f"EP{epn} 有硬钩台词", str(hh))
        hook_types.append(hh.get("type"))

        # 集时长
        ep_total = sum(s["dur_sec"] for b in blocks for s in b["shots"])
        g.check(abs(ep_total - spec["ep_sec"]) <= spec["ep_sec"] * 0.10,
                f"EP{epn} 集时长在 ±10%", f"实际 {ep_total:.2f}s / 目标 {spec['ep_sec']}s")

    # 硬钩类型不连续重复
    for i in range(1, len(hook_types)):
        g.check(hook_types[i] != hook_types[i - 1],
                f"EP{eps[i]['ep']} 硬钩类型不与上集重复",
                f"{hook_types[i-1]} → {hook_types[i]}")

    # ---------- 9. 风格锁定（第①步必选项）----------
    from stylelib import STYLES, OVERLAYS, build_style_prompt, validate, tier_of
    style = spec.get("style") or {}
    sid = style.get("style_id")
    overlays = style.get("overlays") or []
    topic = style.get("topic")
    g.check(bool(sid), "风格已选定 style_id", str(sid))
    if sid:
        g.in_(sid, tuple(STYLES), "style_id 在风格库中")
        errs = validate(sid, overlays, topic)
        for e in errs:
            # 题材不匹配是提醒不致命；其余致命
            fatal = "推荐" not in e
            g.check(False, "风格校验", e, fatal=fatal)
        if not errs:
            g.check(True, "风格校验通过",
                    f"{sid} [{tier_of(sid)}档] + {overlays}")
        # 风格提示词可正常拼装
        try:
            sp = build_style_prompt(sid, overlays)
            g.check(len(sp) > 20, "STYLE_PROMPT 可拼装",
                    f"{len(sp)} 字")
        except Exception as e:
            g.check(False, "STYLE_PROMPT 可拼装", str(e))

    # ---------- 附：统计 ----------
    n_blocks = sum(len(e["blocks"]) for e in eps)
    n_shots = sum(len(b["shots"]) for e in eps for b in e["blocks"])
    print(f"  统计：{len(eps)} 集 / {n_blocks} 块 / {n_shots} 镜 / "
          f"总时长 {sum(s['dur_sec'] for e in eps for b in e['blocks'] for s in b['shots']):.2f}s")
    print(f"  时长分布：{sorted({s['dur_sec'] for e in eps for b in e['blocks'] for s in b['shots']})}")

    save_gate(g, proj.d_report / "gate_01_script.txt")
    return g


if __name__ == "__main__":
    gate = run()
    print(gate.report())
    sys.exit(0 if gate.passed else 1)
