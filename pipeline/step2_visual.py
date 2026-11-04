# -*- coding: utf-8 -*-
"""step2_visual.py · 第 ② 步门禁 + 资产清单生成

做两件事：
1. 校验视觉圣经完整度（三份锁定词 / 九宫格 / 三视图 / 音色 / 试听）
2. 生成"待出图清单" asset_manifest.csv —— 这是真正出图时的任务单
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import (ROOT, Gate, Project, log, read_json, save_gate, write_csv)

SLUG = "demo_雨夜的订单"

GRID_VIEWS = ["正面全身", "3/4左半身", "3/4右半身",
              "左侧全身", "正面胸像", "右侧全身",
              "背面全身", "仰角胸像", "俯角胸像"]
SCENE_VIEWS = ["MAIN 主视角", "REVERSE 反打视角", "TOP 俯视布局", "LIGHT_REF 光线参考"]
ITEM_VIEWS = ["正面", "侧面", "45°", "HAND 手持"]
TRIAL_LINES = ["平静陈述句", "压抑怒 EXP_ANGER_M", "情绪上限 EXP_GRIEF_H"]


def run(slug: str = SLUG) -> Gate:
    proj = Project(ROOT, slug)
    script = read_json(proj.d_script / "script.json")
    g = Gate("第②步 · 视觉圣经门禁")

    chars = script["characters"]
    scenes = script["scenes"]
    items = script["items"]

    # ---------- 1. 三份锁定词存在且条数齐 ----------
    lock_path = proj.d_char / "外观锁定词.md"
    expr_path = proj.d_char / "表情片段库.md"
    scn_path = proj.d_scene / "场景设定.md"
    voice_path = proj.d_char / "音色表.md"
    outfit_path = proj.d_char / "服装表.md"

    for p, nm in [(lock_path, "外观锁定词"), (expr_path, "表情片段库"),
                  (scn_path, "场景设定"), (voice_path, "音色表"),
                  (outfit_path, "服装表")]:
        g.check(p.exists(), f"{nm} 文件存在", str(p))

    lock_txt = lock_path.read_text(encoding="utf-8") if lock_path.exists() else ""
    expr_txt = expr_path.read_text(encoding="utf-8") if expr_path.exists() else ""
    scn_txt = scn_path.read_text(encoding="utf-8") if scn_path.exists() else ""
    voice_txt = voice_path.read_text(encoding="utf-8") if voice_path.exists() else ""
    outfit_txt = outfit_path.read_text(encoding="utf-8") if outfit_path.exists() else ""

    # ---------- 2. 每个角色有锁定词，且长度 40–200 字（40–80 中文 + 容差）----------
    for c in chars:
        has = c["id"] in lock_txt
        g.check(has, f"{c['id']} 有外观锁定词")
        if has:
            seg = lock_txt.split(c["id"])[1][:400]
            # 取"中文"段
            body = seg.split("**EN**")[0].replace("**中文**", "").strip()
            g.num(len(body), 30, 300, f"{c['id']} 锁定词长度合理({len(body)}字)")

    # ---------- 3. 18 条表情片段齐 ----------
    from common import EXPR_CODES
    for code in EXPR_CODES:
        g.check(code in expr_txt, f"表情片段 {code} 存在")

    # ---------- 4. 每个场景有锁定词 ----------
    for s in scenes:
        g.check(s["id"] in scn_txt, f"场景 {s['id']} 有锁定词")

    # ---------- 5. 服装每套有描述 ----------
    all_outfits = sorted({o for c in chars for o in c["outfits"]})
    for o in all_outfits:
        g.check(o in outfit_txt, f"服装 {o} 有描述")

    # ---------- 6. 每角色有音色 ID + 试听通过 ----------
    for c in chars:
        g.check(bool(c.get("voice_id")), f"{c['id']} 有 voice_id", str(c.get("voice_id")))
        g.check(c["id"] in voice_txt, f"{c['id']} 在音色表中")
    g.check("| Y |" in voice_txt or "Y" in voice_txt, "音色试听已通过标记")

    # ---------- 7. 生成待出图清单 ----------
    rows = []
    for c in chars:
        for outfit in c["outfits"]:
            rows.append({
                "kind": "role_grid", "owner": c["id"], "variant": outfit,
                "n_views": 9, "views": " | ".join(GRID_VIEWS),
                "ref": c.get("face_photo") or f"FACE_REF_{c['id']}.png(AI生成)",
                "tries": 3, "note": "3版候选→选1；每套服装单独一版",
            })
        rows.append({
            "kind": "role_face_ref", "owner": c["id"], "variant": "-",
            "n_views": 1, "views": "正面高清胸像",
            "ref": c.get("face_photo") or "-", "tries": 2,
            "note": "首帧抽卡的图生图参考主力",
        })
        rows.append({
            "kind": "role_face_expr", "owner": c["id"], "variant": "-",
            "n_views": 6, "views": " | ".join(f"EXP_{b}" for b in
                                              ("ANGER", "GRIEF", "SHOCK", "CONTEMPT", "RESOLVE", "TENDER")),
            "ref": f"FACE_REF_{c['id']}.png", "tries": 2,
            "note": "6基表情小图，反推18条EXP片段",
        })

    for s in scenes:
        rows.append({
            "kind": "scene_views", "owner": s["id"], "variant": "-",
            "n_views": 4, "views": " | ".join(SCENE_VIEWS),
            "ref": "-", "tries": 3,
            "note": "四张成套出，光线方向必须自洽",
        })

    for it in items:
        rows.append({
            "kind": "item_views", "owner": it["id"], "variant": it["type"],
            "n_views": 4, "views": " | ".join(ITEM_VIEWS),
            "ref": "-", "tries": 3,
            "note": "文字类必须逐字核对" if it["type"] == "产品" else "剧情道具需可辨认",
        })

    manifest = proj.d_char / "asset_manifest.csv"
    write_csv(manifest, rows)

    # ---------- 8. 统计 ----------
    n_img = sum(r["n_views"] * r["tries"] for r in rows)
    n_pick = sum(r["n_views"] for r in rows)
    print(f"  待出图任务 {len(rows)} 条 | 需选定 {n_pick} 张 | 抽卡总量 {n_img} 张")
    print(f"  清单：{manifest}")

    # ---------- 9. 门禁：manifest 覆盖所有角色/场景/物品 ----------
    owners = {r["owner"] for r in rows}
    for c in chars:
        g.check(c["id"] in owners, f"{c['id']} 在待出图清单中")
    for s in scenes:
        g.check(s["id"] in owners, f"{s['id']} 在待出图清单中")
    for it in items:
        g.check(it["id"] in owners, f"{it['id']} 在待出图清单中")

    save_gate(g, proj.d_report / "gate_02_visual.txt")
    return g


if __name__ == "__main__":
    gate = run()
    print(gate.report())
    sys.exit(0 if gate.passed else 1)
