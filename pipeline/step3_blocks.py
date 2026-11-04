# -*- coding: utf-8 -*-
"""step3_blocks.py · 第 ③④ 步：块卡生成 + 首尾帧清单 + 提示词拼装

这是整个工作台的核心模块：
  输入 = script.json + 三份锁定词
  输出 = BLOCK_EP{N}_B{N}.csv（22+ 列，提示词已拼好可直接贴）
       + 首尾帧清单 frame_manifest.csv

拼装公式（严格照此，不做自由发挥）：
  first_frame_prompt = LOCK_V1 + 景别机位 + EXP肌肉级 + 视线姿势 + SCN_LOCK环境 + SCN_LOCK光线 + 画质后缀
  last_frame_prompt  = 同上，只改表演层
  video_prompt       = 主体微动 + 次要运动 + 运镜 + 时长感
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import (BAR_SEC, BLOCK_SEC, CAMERAS, EXPR_CODES, FORBIDDEN_IN_VIDEO,
                    FORBIDDEN_MOVE_WORDS, MODEL_TAG_TRIES, MODEL_TAGS, MOVES_BANNED,
                    MOVES_OK, NEGATIVE_DEFAULT, QUALITY_SUFFIX_CN, ROOT, SHOT_SIZES,
                    Gate, Project, bar_time, bars_to_sec, dedupe_csv, log,
                    read_json, save_gate, write_csv, write_json)

SLUG = "demo_雨夜的订单"

# 运镜 → 中文提示词写法
MOVE_CN = {
    "STATIC": "镜头固定不动",
    "PUSH_S": "镜头极缓慢推近",
    "PULL_S": "镜头极缓慢拉远",
    "PAN_S": "镜头缓慢左右摇，幅度不超过15度",
    "TILT_S": "镜头缓慢上仰或下俯，幅度不超过15度",
    "TRACK_S": "镜头跟随人物缓慢横移",
    "HANDHELD_L": "轻微手持晃动",
    "RACK": "焦点从前景移到人物脸",
}
CAMERA_CN = {
    "EYE": "平视机位", "LOW": "低机位仰拍", "HIGH": "高机位俯拍",
    "OTS": "过肩镜头，前景肩部虚化，焦点在对方脸上",
    "PROFILE": "四分之三侧脸", "BCK": "背对镜头",
    "POV": "第一人称视角", "DUTCH": "镜头倾斜十五度",
}
SIZE_CN = {
    "ECU": "大特写镜头", "CU": "特写镜头", "MS": "中景镜头",
    "MFS": "中全景镜头", "FS": "全景镜头", "ELS": "大全景镜头",
}


# ============================================================
# 锁定词解析
# ============================================================
def parse_md_blocks(text: str) -> dict[str, str]:
    """从 '## KEY\n\n**中文**\n\n内容\n' 结构里抽出 {KEY: 中文内容}"""
    out = {}
    parts = re.split(r"^##\s+", text, flags=re.M)
    for p in parts[1:]:
        head, _, rest = p.partition("\n")
        key = head.strip()
        body = rest.split("**EN**")[0]
        body = body.replace("**中文**", "").strip()
        body = re.sub(r"\s+", " ", body)
        out[key] = body
    return out


def parse_table(text: str, col: int = 1) -> dict[str, str]:
    """从 markdown 表格里抽 {第一列: 第col列}"""
    out = {}
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) <= col or set(cells[0]) <= {"-", " "}:
            continue
        out[cells[0]] = cells[col]
    return out


# ============================================================
# 提示词拼装
# ============================================================
def build_first_frame(lock: str, size: str, camera: str, expr_desc: str,
                      chars: list[str], outfit_desc: str, scene_env: str,
                      product_desc: str | None, product_moment: str,
                      style_prompt: str = "", suffix: str = QUALITY_SUFFIX_CN,
                      marker: str = "", echo_marker: bool = False,
                      identity_echo: str = "") -> str:
    """提示词拼装（顺序不可改）：

    [景别强制lead] + LOCK_V1 + 景别机位 + EXP表情 + 服装
    + 场景环境光线 + ★STYLE★ + [构图限制tail] + [标志物回声] + 画质后缀

    实测教训（风格对照 EP01_SH02）：
      ① 风格词权重会压过景别词 → 景别必须前置强调 + 尾部构图限制 + 负向词三锁
      ② 风格词过长会稀释标志物 → 超 15 短语时标志物在结尾单独回声一次
      ③ 标志物已在锁定词里，不许在开头再写一遍（会变成重复稀释）
    """
    from stylelib import enforce_shot_size
    enf = enforce_shot_size(size)

    parts = [
        enf["lead"],                                    # ① 景别前置强约束
        lock,                                           # ② 外观锁定词（已含标志物）
        f"{SIZE_CN.get(size, size)}，{CAMERA_CN.get(camera, camera)}",
        expr_desc,
        f"身穿{outfit_desc}" if outfit_desc else "",
        scene_env,
    ]
    if product_desc:
        parts.append(f"画面中的{product_desc}，{product_moment}")
    if style_prompt:
        parts.append(style_prompt)                      # ③ 风格层
    parts.append(enf["tail"])                           # ④ 构图限制（尾部再锁一次）
    if identity_echo:
        parts.append(identity_echo)                     # ⑤ 人物身份回声（强风格必加）
    if echo_marker and marker:
        parts.append(f"重要特征必须清晰可见：{marker}")   # ⑥ 标志物回声（仅尾部一次）
    parts.append(suffix)
    return "，\n".join(p for p in parts if p)


# 场景 → 次要运动（避免室内戏写"雨水滴落"这种穿帮）
SECONDARY_BY_SCENE = {
    "SCN_ALLEY_NIGHT": "雨水从发梢滴落，衣角被风带动，地面积水有细微涟漪",
    "SCN_ROOM_DUSK": "窗帘被气流带动轻晃，细微浮尘在光柱里飘动",
}
SECONDARY_DEFAULT = "衣角被气流带动，轻微起伏"


def build_video_prompt(size: str, move: str, expr_int: int, chars: list[str],
                       dur_sec: float, has_line: bool, scene_id: str = "") -> str:
    """只写微动，不写表情变化"""
    if expr_int >= 3:
        micro = "他保持这个表情不动，眼睑快速眨了一下，喉结微微吞咽"
    elif expr_int == 2:
        micro = "他保持这个表情，幅度极小，呼吸让肩膀微微起伏"
    else:
        micro = "他保持这个表情，几乎没有动作，只有眼睫轻颤"
    if has_line:
        micro += "，嘴唇随之开合说话"
    secondary = SECONDARY_BY_SCENE.get(scene_id, SECONDARY_DEFAULT)
    camera_move = MOVE_CN.get(move, "镜头固定不动")
    return f"{micro}，{secondary}，{camera_move}，{dur_sec}秒。"


def build_last_frame_note(first: str, expr_desc_end: str) -> str:
    """尾帧 = 首帧提示词，替换表情段为结束状态"""
    return f"（尾帧：在首帧基础上，表情改为「{expr_desc_end}」，其余锁定词与环境光线一字不改）"


# ============================================================
# 主流程
# ============================================================
def run(slug: str = SLUG) -> Gate:
    proj = Project(ROOT, slug)
    script = read_json(proj.d_script / "script.json")
    g = Gate("第③④步 · 块卡与提示词门禁")

    # ---- 载入锁定词 ----
    locks = parse_md_blocks((proj.d_char / "外观锁定词.md").read_text(encoding="utf-8"))
    exprs = parse_table((proj.d_char / "表情片段库.md").read_text(encoding="utf-8"))
    outfits = parse_table((proj.d_char / "服装表.md").read_text(encoding="utf-8"))
    scn_raw = (proj.d_scene / "场景设定.md").read_text(encoding="utf-8")
    scenes_lock = parse_md_blocks(scn_raw)

    # ---- 载入风格（第①步锁定）----
    from stylelib import (STYLES, build_negative as style_neg,
                          build_style_prompt, quality_suffix, tier_of,
                          needs_marker_echo, enforce_shot_size, style_phrase_count,
                          identity_echo as get_identity_echo, era_compatible)
    style_spec = script["spec"].get("style") or {}
    style_id = style_spec.get("style_id", "")
    overlays = style_spec.get("overlays") or []
    style_prompt = build_style_prompt(style_id, overlays) if style_id else ""
    style_prompt_en = (build_style_prompt(style_id, overlays, "en")
                       if style_id else "")
    style_negative = style_neg(style_id, overlays) if style_id else ""
    # 画质后缀：与风格层去重，避免同一形容词重复稀释权重
    quality_suffix_final = quality_suffix(style_id, overlays) if style_id else QUALITY_SUFFIX_CN
    echo_marker = needs_marker_echo(style_id, overlays) if style_id else False
    # 人物身份回声（强风格会磨掉年龄/疤痕）
    id_echo = get_identity_echo(style_id) if style_id else ""
    g_style_tier = tier_of(style_id) if style_id else "?"
    print(f"  风格：{style_id} [{g_style_tier}档] + {overlays}"
          f"（{style_phrase_count(style_id, overlays)} 短语"
          f"{'，标志物回声' if echo_marker else ''}"
          f"{'，身份回声' if id_echo else ''}）")
    print(f"  后缀（去重后）：{quality_suffix_final}")

    # 风格 ↔ 场景年代 匹配（实测教训：古装风格配现代场景会完全失效）
    all_scene_ids = {s["id"] for s in script["scenes"]}
    era_results = {sid: era_compatible(style_id, sid)
                   for sid in all_scene_ids} if style_id else {}

    # 角色标志物（用于标志物前置 + 回声）
    MARKERS = {
        "C_LEAD": "左手腕旧钢带手表，右眉尾一道浅疤",
        "C_VILLAIN": "右耳金色圆环耳饰",
        "C_ALLY": "颈间细银链",
    }

    # ---- 索引 ----
    item_by_id = {i["id"]: i for i in script["items"]}
    char_by_id = {c["id"]: c for c in script["characters"]}

    # ---- 允许的（不参与冲突检测的）片段 ----
    frames_rows = []          # 首尾帧清单
    all_rows_by_ep = {}       # {ep: [rows]}
    shot_index = {}           # (ep,block,shot) -> row

    for ep in script["episodes"]:
        epn = ep["ep"]
        rows = []
        for b in ep["blocks"]:
            bn = b["block"]
            scene_env = scenes_lock.get(b["scene"], "")

            # 块级首尾帧
            frames_rows.append({
                "ep": epn, "block": bn, "shot": "BLOCK", "level": "block",
                "kind": "IN", "file": f"EP{epn:02d}/B{bn:02d}_IN.png",
                "char_ids": "|".join(sorted({c for s in b["shots"] for c in s["chars"]})),
                "scene": b["scene"], "tries": 3,
                "note": "块的视觉起点 = 块首镜 IN",
            })
            frames_rows.append({
                "ep": epn, "block": bn, "shot": "BLOCK", "level": "block",
                "kind": "OUT", "file": f"EP{epn:02d}/B{bn:02d}_OUT.png",
                "char_ids": "|".join(sorted({c for s in b["shots"] for c in s["chars"]})),
                "scene": b["scene"], "tries": 3,
                "note": "块的视觉终点 = 块末镜 OUT；与下块 IN 必须可接",
            })

            for s in b["shots"]:
                sn = s["shot"]
                sid = f"EP{epn:02d}B{bn:02d}SH{sn:02d}"
                ch = s["chars"]
                primary = ch[0]
                lock = locks.get(primary, "")
                expr_desc = exprs.get(s["expr"], "")
                outfit_desc = outfits.get(s["outfit"], "")
                dur_sec = s["dur_sec"]
                has_line = s["line"] not in ("—", "-", "")

                # 产品/物品
                prod_desc = None
                prod_moment = ""
                if s["product"] not in ("无", "-", ""):
                    it = item_by_id.get(s["product"], {})
                    prod_desc = it.get("desc", "")
                    prod_moment = ("瓶身侧对镜头半露，标签文字清晰可读"
                                   if it.get("type") == "产品"
                                   else "作为视觉焦点，材质与磨损细节清晰")

                ff = build_first_frame(lock, s["size"], s["camera"], expr_desc,
                                      ch, outfit_desc, scene_env, prod_desc,
                                      prod_moment, style_prompt,
                                      quality_suffix_final,
                                      marker=MARKERS.get(primary, ""),
                                      echo_marker=echo_marker,
                                      identity_echo=id_echo)
                vp = build_video_prompt(s["size"], s["move"], s["expr_int"],
                                        ch, dur_sec, has_line, b["scene"])
                lf = build_last_frame_note(ff, expr_desc)
                # 负向词：默认 + 风格 + 景别强约束 + 台词镜特化，最后整体去重
                neg = NEGATIVE_DEFAULT
                if style_negative:
                    neg += ", " + style_negative
                neg += ", " + enforce_shot_size(s["size"])["neg"]
                if has_line:
                    neg += ", 哭, 笑, 表情剧变"
                neg = dedupe_csv(neg)

                img_tries, vid_tries = MODEL_TAG_TRIES[s["model_tag"]]

                row = {
                    "ep": epn, "block": bn, "shot": sn,
                    "bar_start": s["bar_start"], "bar_len": s["dur_bar"],
                    "dur_bar": s["dur_bar"], "dur_sec": f"{dur_sec:.3f}",
                    "time_in_block": f"{bar_time(s['bar_start']):.3f}",
                    "frame_in": f"EP{epn:02d}/B{bn:02d}_SH{sn:02d}_IN.png",
                    "frame_out": f"EP{epn:02d}/B{bn:02d}_SH{sn:02d}_OUT.png",
                    "shot_size": s["size"], "camera": s["camera"], "move": s["move"],
                    "expr_code": s["expr"], "expr_int": s["expr_int"],
                    "char_ids": "|".join(ch), "outfit": s["outfit"],
                    "product": s["product"], "level": s["level"],
                    "model_tag": s["model_tag"],
                    "img_tries": img_tries, "vid_tries": vid_tries,
                    "chain_break": str(s["chain_break"]).lower(),
                    # 音频列
                    "line": s["line"], "sub_text": s["sub"],
                    "voice_emotion": s["expr"], "sfx": s["sfx"],
                    "bgm_layer": s["bgm_layer"], "bgm_cue": s["bgm_cue"],
                    "ambience": s["ambience"],
                    # 提示词列
                    "first_frame_prompt": ff,
                    "last_frame_prompt": lf,
                    "video_prompt": vp,
                    "negative": neg,
                    "lock_id_used": primary,
                    # 风格列（第①步锁定，全剧逐字复用）
                    "style_id": style_id,
                    "style_overlays": "|".join(overlays),
                    "style_prompt": style_prompt,
                    "style_prompt_en": style_prompt_en,
                }
                rows.append(row)
                shot_index[(epn, bn, sn)] = row

                # 镜级首尾帧清单
                frames_rows.append({
                    "ep": epn, "block": bn, "shot": sn, "level": "shot",
                    "kind": "IN", "file": row["frame_in"],
                    "char_ids": row["char_ids"], "scene": b["scene"], "tries": img_tries,
                    "note": "断链重开" if s["chain_break"] else "继承上一镜 OUT",
                })
                frames_rows.append({
                    "ep": epn, "block": bn, "shot": sn, "level": "shot",
                    "kind": "OUT", "file": row["frame_out"],
                    "char_ids": row["char_ids"], "scene": b["scene"], "tries": img_tries,
                    "note": "同镜 IN 为参考，只改表演层",
                })

        all_rows_by_ep[epn] = rows
        out_csv = proj.d_scene / f"BLOCK_EP{epn:02d}.csv"
        write_csv(out_csv, rows)

    write_csv(proj.d_char / "frame_manifest.csv", frames_rows)

    # ============================================================
    # 门禁检查
    # ============================================================
    all_rows = [r for rs in all_rows_by_ep.values() for r in rs]

    # --- 1. 每镜提示词含锁定词（逐字）---
    for r in all_rows:
        lock = locks.get(r["lock_id_used"], "")
        g.check(lock and lock in r["first_frame_prompt"],
                f"{r['ep']}B{r['block']:02d}SH{r['shot']:02d} 首帧含锁定词逐字")

    # --- 2. 每镜提示词含场景环境 ---
    ep_blocks = {(e["ep"], b["block"]): b for e in script["episodes"] for b in e["blocks"]}
    for r in all_rows:
        b = ep_blocks[(r["ep"], r["block"])]
        env = scenes_lock.get(b["scene"], "")
        g.check(env and env in r["first_frame_prompt"],
                f"{r['ep']}B{r['block']:02d}SH{r['shot']:02d} 首帧含场景锁定词")

    # --- 2b. 每镜提示词含风格层（逐字，且位置在环境之后、画质之前）---
    g.check(bool(style_prompt), "全剧有 STYLE_PROMPT")
    for r in all_rows:
        sid = f"{r['ep']}B{r['block']:02d}SH{r['shot']:02d}"
        g.check(bool(r["style_prompt"]) and r["style_prompt"] in r["first_frame_prompt"],
                f"{sid} 首帧含 STYLE_PROMPT 逐字")
        # 位置检查：风格必须在最后一个环境词之后、画质后缀之前
        fp = r["first_frame_prompt"]
        b = ep_blocks[(r["ep"], r["block"])]
        env = scenes_lock.get(b["scene"], "")
        if env and style_prompt and style_prompt in fp:
            g.check(fp.index(style_prompt) > fp.index(env),
                    f"{sid} STYLE 在环境之后（位置正确）")
            g.check(fp.index(style_prompt) < fp.index(quality_suffix_final),
                    f"{sid} STYLE 在画质后缀之前（位置正确）")
    # 全剧风格唯一
    g.eq(len({r["style_id"] for r in all_rows}), 1, "全剧 style_id 唯一")
    # 修饰层 ≤2
    g.check(len(overlays) <= 2, "修饰层 ≤2 个", f"{overlays}")

    # --- 2c. 风格 ↔ 场景年代 匹配（实测：古装风格配现代场景会完全失效）---
    for sid, (ok, msg) in era_results.items():
        g.check(ok, f"风格与场景 {sid} 年代匹配", msg)

    # --- 3. 视频提示词禁止表情变化动词 ---
    for r in all_rows:
        bad = [w for w in FORBIDDEN_IN_VIDEO if w in r["video_prompt"]]
        g.check(not bad, f"{r['ep']}B{r['block']:02d}SH{r['shot']:02d} 视频提示词无表情变化动词",
                f"命中 {bad}")

    # --- 4. 运镜白名单 + 黑名单 ---
    for r in all_rows:
        g.in_(r["move"], MOVES_OK,
              f"{r['ep']}B{r['block']:02d}SH{r['shot']:02d} 运镜在白名单", )
        bad = [w for w in FORBIDDEN_MOVE_WORDS if w in r["video_prompt"]]
        g.check(not bad, f"{r['ep']}B{r['block']:02d}SH{r['shot']:02d} 视频提示词无黑名单运镜词",
                f"命中 {bad}")

    # --- 4b. 场景-次要运动一致性（室内不许出现雨水）---
    RAIN_SCENES = {"SCN_ALLEY_NIGHT"}
    for r in all_rows:
        b = ep_blocks[(r["ep"], r["block"])]
        if b["scene"] not in RAIN_SCENES:
            g.check("雨水" not in r["video_prompt"],
                    f"{r['ep']}B{r['block']:02d}SH{r['shot']:02d} 室内场景无雨水描述",
                    b["scene"])

    # --- 5. 运镜不写进首帧提示词 ---
    for r in all_rows:
        bad = [w for w in FORBIDDEN_MOVE_WORDS if w in r["first_frame_prompt"]]
        g.check(not bad, f"{r['ep']}B{r['block']:02d}SH{r['shot']:02d} 首帧提示词不含运镜词",
                f"命中 {bad}")

    # --- 6. 景别/机位/表情/标签 合法性 ---
    for r in all_rows:
        sid = f"{r['ep']}B{r['block']:02d}SH{r['shot']:02d}"
        g.in_(r["shot_size"], SHOT_SIZES, f"{sid} 景别合法")
        g.in_(r["camera"], CAMERAS, f"{sid} 机位合法")
        g.in_(r["expr_code"], EXPR_CODES, f"{sid} 表情码合法")
        g.in_(r["model_tag"], MODEL_TAGS, f"{sid} 模型标签合法")
        g.in_(r["bgm_layer"], ("PAD", "LOOP", "STRINGS", "HIT"),
              f"{sid} BGM层合法")

    # --- 7. 时长：dur_sec = dur_bar × 1.875，块内和 = 15.000 ---
    for (epn, bn), b in ep_blocks.items():
        shots = [r for r in all_rows if r["ep"] == epn and r["block"] == bn]
        total = sum(float(r["dur_sec"]) for r in shots)
        g.check(abs(total - BLOCK_SEC) < 0.05,
                f"EP{epn}B{bn:02d} 块内时长 15.000s", f"实际 {total:.3f}")
        for r in shots:
            expect = bars_to_sec(int(r["dur_bar"]))
            g.check(abs(float(r["dur_sec"]) - expect) < 0.001,
                    f"EP{epn}B{bn:02d}SH{r['shot']:02d} dur_sec 由 dur_bar 算出",
                    f"{r['dur_sec']} vs {expect}")

    # --- 8. 镜头语言配比（CU+ECU≥50%，STATIC≥60%）---
    n = len(all_rows)
    cu_ecu = sum(1 for r in all_rows if r["shot_size"] in ("CU", "ECU"))
    static = sum(1 for r in all_rows if r["move"] == "STATIC")
    g.check(cu_ecu / n >= 0.5, "CU+ECU 占比 ≥50%", f"{cu_ecu}/{n} = {cu_ecu/n:.1%}")
    g.check(static / n >= 0.6, "STATIC 占比 ≥60%", f"{static}/{n} = {static/n:.1%}")

    # --- 9. 每块内**同角色**表情跨级 ≤1（不同角色各有各的弧线，不能混判）---
    for (epn, bn), b in ep_blocks.items():
        shots = sorted([r for r in all_rows if r["ep"] == epn and r["block"] == bn],
                       key=lambda x: x["shot"])
        per_char: dict[str, list[int]] = {}
        for r in shots:
            for c in r["char_ids"].split("|"):
                if c:
                    per_char.setdefault(c, []).append(int(r["expr_int"]))
        for c, ints in per_char.items():
            g.check(max(ints) - min(ints) <= 1,
                    f"EP{epn}B{bn:02d} {c} 块内表情跨级 ≤1",
                    f"强度序列 {ints}")

    # --- 10. 每镜人数 ≤2 ---
    for r in all_rows:
        nch = len([x for x in r["char_ids"].split("|") if x])
        g.check(1 <= nch <= 2,
                f"{r['ep']}B{r['block']:02d}SH{r['shot']:02d} 人数 ≤2", f"{nch}")

    # --- 11. 首尾帧清单齐全 ---
    n_block_frames = sum(1 for f in frames_rows if f["level"] == "block")
    n_shot_frames = sum(1 for f in frames_rows if f["level"] == "shot")
    g.eq(n_block_frames, len(ep_blocks) * 2, "块级首尾帧数 = 块数×2")
    g.eq(n_shot_frames, len(all_rows) * 2, "镜级首尾帧数 = 镜数×2")

    # --- 12. 继承链长 ≤4 ---
    for (epn, bn), b in ep_blocks.items():
        shots = sorted([r for r in all_rows if r["ep"] == epn and r["block"] == bn],
                       key=lambda x: x["shot"])
        chain = 0
        max_chain = 0
        for r in shots:
            if r["chain_break"] == "true":
                chain = 1
            else:
                chain += 1
            max_chain = max(max_chain, chain)
        g.check(max_chain <= 4, f"EP{epn}B{bn:02d} 继承链长 ≤4", f"实际 {max_chain}")

    # --- 统计输出 ---
    print(f"  块卡：{len(all_rows)} 镜 → {len(ep_blocks)} 个 BLOCK_EP*.csv")
    print(f"  首尾帧清单：块级 {n_block_frames} 张 + 镜级 {n_shot_frames} 张 = {len(frames_rows)} 张")
    print(f"  镜头配比：CU+ECU {cu_ecu/n:.0%} | STATIC {static/n:.0%}")
    print(f"  模型分布：{_tag_dist(all_rows)}")
    n_img = sum(int(r["img_tries"]) for r in all_rows)
    n_vid = sum(int(r["vid_tries"]) for r in all_rows)
    print(f"  抽卡预算：首帧 {n_img} 张 + 视频 {n_vid} 条")
    print(f"  → {proj.d_scene / 'BLOCK_EP01.csv'}")

    save_gate(g, proj.d_report / "gate_03_blocks.txt")
    return g


def _tag_dist(rows):
    from collections import Counter
    c = Counter(r["model_tag"] for r in rows)
    return " ".join(f"{k}×{v}" for k, v in c.most_common())


if __name__ == "__main__":
    gate = run()
    print(gate.report())
    sys.exit(0 if gate.passed else 1)
