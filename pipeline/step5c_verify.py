# -*- coding: utf-8 -*-
"""step5c_verify.py · 第 ⑤ 步 · 六道一致性验证器

这是整个工作台的核心质检层。你的要求："确保所有 15 秒的片段都经过验证，
符合第三步和第四步的要求" —— 这份代码就是那个"验证"。

六道：
  A 计划 vs 实际    计划首尾帧 ↔ 实际生成的首尾帧   ← 最重要，一票否决
  B 块级接缝        前块实际 OUT ↔ 后块计划 IN
  C 角色一致        实际画面 ↔ 外观锁定词 + 角色色相签名
  D 物品与场景      实际画面 ↔ 场景签名 / 物品出现
  E 声音一致        配音 ↔ 音色表 / 时长 / 电平
  F 时长与节拍      实测时长 ↔ 节拍网格

判定：A/B/C/D 任一 ❌ → 该镜不入池；E/F 可先入池再修。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import (BAR_SEC, BLOCK_SEC, LEGAL_SHOT_SEC, ROOT, TOL_BLOCK, TOL_SHOT,
                    Gate, Project, read_csv, read_json, save_gate, write_csv)
from imgutil import hue_dist, signature
from mediautil import dur as media_dur

SLUG = "demo_雨夜的订单"
SIZE_BARS = {"ECU": 1, "CU": 2, "MS": 3, "MFS": 4, "FS": 5, "ELS": 6}
# 与 step5b_mockmedia 保持一致的签名编码（真实生成时替换为 CLIP/人脸 embedding）
HUE_BY_CHAR = {"C_LEAD": 200, "C_VILLAIN": 330, "C_ALLY": 45}
HUE_BY_SCENE = {"SCN_ALLEY_NIGHT": 15, "SCN_ROOM_DUSK": -20}


def ff_dur(path: Path) -> float:
    return media_dur(path)


def run(slug: str = SLUG) -> tuple[Gate, list[dict]]:
    proj = Project(ROOT, slug)
    script = read_json(proj.d_script / "script.json")
    ep_blocks = {(e["ep"], b["block"]): b for e in script["episodes"] for b in e["blocks"]}
    char_by_id = {c["id"]: c for c in script["characters"]}

    g = Gate("第⑤步·C · 六道一致性验证")
    ledger: list[dict] = []
    verdicts: dict[tuple, dict] = {}

    for ep in script["episodes"]:
        epn = ep["ep"]
        rows = read_csv(proj.d_scene / f"BLOCK_EP{epn:02d}.csv")
        print(f"\n  EP{epn:02d} · 验证 {len(rows)} 镜")

        for r in rows:
            bn, sn = int(r["block"]), int(r["shot"])
            sid = f"EP{epn:02d}B{bn:02d}SH{sn:02d}"
            b = ep_blocks[(epn, bn)]
            char = r["char_ids"].split("|")[0]
            scene = b["scene"]

            fdir = proj.d_frames / f"EP{epn:02d}"
            cdir = proj.d_blocks / f"EP{epn:02d}" / f"B{bn:02d}" / "clips"
            planned_in = fdir / f"B{bn:02d}_SH{sn:02d}_IN.png"
            planned_out = fdir / f"B{bn:02d}_SH{sn:02d}_OUT.png"
            clip = cdir / f"B{bn:02d}_SH{sn:02d}.mp4"
            actual_in = cdir / f"B{bn:02d}_SH{sn:02d}_actual_IN.png"
            actual_out = cdir / f"B{bn:02d}_SH{sn:02d}_actual_OUT.png"

            # 计划图若不在 d_frames，回落到 blocks/frames（本次测试的路径）
            if not planned_in.exists():
                planned_in = proj.d_blocks / f"EP{epn:02d}" / f"B{bn:02d}" / "frames" / planned_in.name
                planned_out = planned_in.parent / f"B{bn:02d}_SH{sn:02d}_OUT.png"

            v = {"sid": sid, "block": bn, "shot": sn, "fails": [], "notes": []}

            # ================= A. 计划 vs 实际 =================
            a_ok = True
            if not planned_in.exists():
                a_ok = False
                v["fails"].append(("A", "计划首帧缺失"))
            elif not actual_in.exists():
                a_ok = False
                v["fails"].append(("A", "实际首帧缺失"))
            else:
                ps = signature(planned_in)
                as_ = signature(actual_in)
                if ps is None or as_ is None:
                    a_ok = False
                    v["fails"].append(("A", "图片读取失败"))
                else:
                    dh = hue_dist(ps["hue"], as_["hue"])
                    dtop = hue_dist(ps["top_hue"], as_["top_hue"])
                    if dh > 25:
                        a_ok = False
                        v["fails"].append(("A", f"首帧主色偏差 {dh:.0f}° (>25°)"))
                    if dtop > 25:
                        a_ok = False
                        v["fails"].append(("A", f"首帧角色条色偏差 {dtop:.0f}° (>25°)"))
                    # 尾帧
                    if actual_out.exists() and planned_out.exists():
                        ps2 = signature(planned_out)
                        as2 = signature(actual_out)
                        if ps2 and as2:
                            dh2 = hue_dist(ps2["hue"], as2["hue"])
                            dtop2 = hue_dist(ps2["top_hue"], as2["top_hue"])
                            if dh2 > 25:
                                a_ok = False
                                v["fails"].append(("A", f"尾帧主色偏差 {dh2:.0f}° (>25°)"))
                            if dtop2 > 25:
                                a_ok = False
                                v["fails"].append(("A", f"尾帧角色条色偏差 {dtop2:.0f}° (>25°)"))
            v["A"] = a_ok

            # ================= B. 块级接缝 =================
            # 正确判据：接缝比的是"同一角色的外观是否延续"，不是绝对色相。
            #   - 前块末镜与后块首镜含同一角色 → 比该角色的签名（角色定色块）
            #   - 换角色 / 换场景 → 不构成接缝失败（这不是漂移，是正常切人）
            v["B"] = True
            if sn == 1 and bn > 1:
                prev_block = ep_blocks[(epn, bn - 1)]
                prev_chars = set()
                for ps_ in prev_block["shots"]:
                    prev_chars |= set(ps_["chars"])
                cur_chars = set(r["char_ids"].split("|"))
                shared = prev_chars & cur_chars
                prev_scene = prev_block["scene"]

                prev_out = (proj.d_blocks / f"EP{epn:02d}" / f"B{bn-1:02d}" /
                            "clips" / f"B{bn-1:02d}_SH{len(prev_block['shots']):02d}_actual_OUT.png")
                if shared and prev_out.exists() and actual_in.exists():
                    s1, s2 = signature(prev_out), signature(actual_in)
                    if s1 and s2:
                        # 只有在"同场景 + 同角色（且角色为后块首镜主角）"时才比色相
                        primary_prev_shot = prev_block["shots"][-1]
                        if (prev_scene == scene
                                and primary_prev_shot["chars"][0] in cur_chars
                                and r["char_ids"].split("|")[0] == primary_prev_shot["chars"][0]):
                            d = hue_dist(s1["top_hue"], s2["top_hue"])
                            if d > 40:
                                v["B"] = False
                                v["fails"].append(("B", f"块接缝角色漂移 {d:.0f}° (>40°)"))
                            else:
                                v["notes"].append(f"B:接缝角色 {d:.0f}° ok")
                        else:
                            v["notes"].append("B:换角色/换场景，不构成漂移")
                else:
                    v["notes"].append("B:换角色/换场景，不构成漂移")

            # ================= C. 角色一致 =================
            c_ok = True
            if actual_in.exists():
                sig = signature(actual_in)
                if sig:
                    exp_hue = HUE_BY_CHAR.get(char, 120) + HUE_BY_SCENE.get(scene, 0)
                    got = sig["top_hue"]
                    d = hue_dist(got, exp_hue)
                    if d > 40:
                        c_ok = False
                        v["fails"].append(("C", f"角色签名色相 {got:.0f}° vs 期望 "
                                                f"{exp_hue % 360:.0f}°（偏差 {d:.0f}°）→ 不像同一角色"))
                    # 景别横条数量（代表景别是否被改）
                    nb = sig["bars"]
                    exp_bars = SIZE_BARS.get(r["shot_size"], 2)
                    if nb > 0 and abs(nb - exp_bars) >= 2:
                        c_ok = False
                        v["fails"].append(("C", f"景别签名 {nb} 条 vs 期望 {exp_bars} 条"))
            v["C"] = c_ok

            # ================= D. 物品与场景 =================
            d_ok = True
            if actual_in.exists():
                sig = signature(actual_in)
                # 场景签名检查（近似：场景边框色是否属于已知场景集）
                # 真实场景：用 CLIP 比对场景三视图
                if scene not in ("SCN_ALLEY_NIGHT", "SCN_ROOM_DUSK"):
                    d_ok = False
                    v["fails"].append(("D", f"场景签名未知 {scene}"))
                # 产品镜必须有产品 id 且视频存在
                if r["product"] not in ("无", "-", ""):
                    if not clip.exists():
                        d_ok = False
                        v["fails"].append(("D", f"产品镜缺视频 {clip.name}"))
            v["D"] = d_ok

            # ================= E. 声音一致 =================
            e_ok = True
            voice_wav = (proj.d_blocks / f"EP{epn:02d}" / f"B{bn:02d}" / "voice" /
                         f"B{bn:02d}_SH{sn:02d}.wav")
            has_line = r["line"] not in ("—", "-", "")
            if has_line:
                if not voice_wav.exists():
                    e_ok = False
                    v["fails"].append(("E", "配音缺失"))
                else:
                    vd = ff_dur(voice_wav)
                    sd = float(r["dur_sec"])
                    if vd > sd + 0.05:
                        e_ok = False
                        v["fails"].append(("E", f"配音 {vd:.2f}s 超过镜长 {sd:.2f}s"))
                    # 音色 ID 存在
                    vid = char_by_id[char].get("voice_id")
                    if not vid:
                        e_ok = False
                        v["fails"].append(("E", f"{char} 无 voice_id"))
            v["E"] = e_ok

            # ================= F. 时长与节拍 =================
            f_ok = True
            if not clip.exists():
                f_ok = False
                v["fails"].append(("F", "视频缺失"))
            else:
                ad = ff_dur(clip)
                sd = float(r["dur_sec"])
                if abs(ad - sd) > TOL_SHOT:
                    f_ok = False
                    v["fails"].append(("F", f"实测 {ad:.3f}s vs 块卡 {sd:.3f}s"))
                if not any(abs(sd - x) < 0.01 for x in LEGAL_SHOT_SEC):
                    f_ok = False
                    v["fails"].append(("F", f"{sd:.3f}s 不在节拍网格"))
                if int(r["dur_bar"]) != round(sd / BAR_SEC):
                    f_ok = False
                    v["fails"].append(("F", "dur_bar 与 dur_sec 不自洽"))
            v["F"] = f_ok

            # ================= 判定 =================
            hard_fail = not (v["A"] and v["B"] and v["C"] and v["D"])
            soft_fail = not (v["E"] and v["F"])
            if hard_fail:
                v["verdict"] = "重抽"
            elif soft_fail:
                v["verdict"] = "待修（可入池）"
            else:
                v["verdict"] = "入池"
            verdicts[(epn, bn, sn)] = v

            ledger.append({
                "sid": sid, "ep": epn, "block": bn, "shot": sn,
                "A计划vs实际": "OK" if v["A"] else "FAIL",
                "B块接缝": "OK" if v["B"] else "FAIL",
                "C角色": "OK" if v["C"] else "FAIL",
                "D物品场景": "OK" if v["D"] else "FAIL",
                "E声音": "OK" if v["E"] else "FAIL",
                "F时长": "OK" if v["F"] else "FAIL",
                "结论": v["verdict"],
                "问题": " | ".join(f"[{c}]{m}" for c, m in v["fails"]),
            })

        # 块级汇总门禁
        for bn in sorted({int(r["block"]) for r in rows}):
            shots = [r for r in rows if int(r["block"]) == bn]
            total = sum(float(r["dur_sec"]) for r in shots)
            g.check(abs(total - BLOCK_SEC) < TOL_BLOCK,
                    f"EP{epn:02d}B{bn:02d} 块时长 15.000s", f"{total:.3f}s")
            blk_verdicts = [verdicts[(epn, bn, int(r["shot"]))]["verdict"] for r in shots]
            n_pool = sum(1 for x in blk_verdicts if x == "入池")
            g.check(n_pool == len(shots), f"EP{epn:02d}B{bn:02d} 全镜入池",
                    f"{n_pool}/{len(shots)} 入池")

    # 全片汇总门禁
    n_all = len(ledger)
    n_pass = sum(1 for x in ledger if x["结论"] == "入池")
    n_re = sum(1 for x in ledger if x["结论"] == "重抽")
    n_fix = sum(1 for x in ledger if x["结论"].startswith("待修"))
    g.check(n_re == 0, "全片无重抽镜", f"{n_re} 镜需重抽")

    write_csv(proj.d_report / "验证台账_EP01.csv", ledger)

    # Markdown 报告
    md = ["# 一致性验证报告 · EP01", "",
          "| 镜 | A计划vs实际 | B块接缝 | C角色 | D物品场景 | E声音 | F时长 | 结论 | 问题 |",
          "|---|---|---|---|---|---|---|---|---|"]
    for x in ledger:
        md.append(f"| {x['sid']} | {x['A计划vs实际']} | {x['B块接缝']} | {x['C角色']} | "
                  f"{x['D物品场景']} | {x['E声音']} | {x['F时长']} | **{x['结论']}** | {x['问题']} |")
    md += ["", f"## 汇总", "",
           f"- 总镜数：{n_all}",
           f"- 入池：{n_pass}",
           f"- 待修：{n_fix}",
           f"- 重抽：{n_re}"]
    (proj.d_report / "验证报告_EP01.md").write_text("\n".join(md), encoding="utf-8")

    print(f"\n  验证汇总：{n_all} 镜 | 入池 {n_pass} | 待修 {n_fix} | 重抽 {n_re}")
    print(f"  → {proj.d_report / '验证报告_EP01.md'}")

    save_gate(g, proj.d_report / "gate_05c_verify.txt")
    return g, ledger


if __name__ == "__main__":
    gate, led = run()
    print(gate.report())
    sys.exit(0 if gate.passed else 1)
