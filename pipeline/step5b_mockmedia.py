# -*- coding: utf-8 -*-
"""step5b_mockmedia.py · 第 ⑤ 步 · 生成 mock 素材（模拟抽卡结果）

用途：在没有真实模型额度的情况下，跑通"抽卡 → 验证 → 合成"全链路。
做法：用 ffmpeg 生成占位首尾帧 PNG + 按块卡时长生成占位视频。
      用**色相 + 几何条数**编码身份信息，验证器据此做"计划 vs 实际"比对。

★ 这不是替代真实生成 —— 它验证的是**工程链路**（时长/命名/引继/验证/合成）。
  真实生成时把 draw_frame / draw_video 换成平台调用即可，其余一行不改。
"""
from __future__ import annotations

import colorsys
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import ROOT, Project, read_csv, read_json

SLUG = "demo_雨夜的订单"
FFMPEG = "ffmpeg"

HUE_BY_CHAR = {"C_LEAD": 200, "C_VILLAIN": 330, "C_ALLY": 45}
HUE_BY_SCENE = {"SCN_ALLEY_NIGHT": 15, "SCN_ROOM_DUSK": -20}
SIZE_BARS = {"ECU": 1, "CU": 2, "MS": 3, "MFS": 4, "FS": 5, "ELS": 6}


def ff(args: list[str]):
    r = subprocess.run(args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "")[-500:])
    return r


def hexc(h: int, s: float, v: float) -> str:
    r, g, b = colorsys.hsv_to_rgb((h % 360) / 360.0, min(1, s), min(1, v))
    return f"0x{int(r*255):02X}{int(g*255):02X}{int(b*255):02X}"


def frame_color(row: dict, char: str, scene: str) -> str:
    """稳定代表色：同角色 + 同场景 + 同表情强度 → 同色"""
    h = HUE_BY_CHAR.get(char, 120) + HUE_BY_SCENE.get(scene, 0)
    s = 0.50 + int(row["expr_int"]) * 0.08
    v = 0.40 + int(row["expr_int"]) * 0.05
    return hexc(h, s, v)


def bars_of(row: dict) -> str:
    """身份条：景别→条数，表情强度→条高"""
    return f"{SIZE_BARS.get(row['shot_size'], 2)}x{int(row['expr_int'])}"


def draw_frame(path: Path, row: dict, char: str, scene: str,
               w: int = 540, h: int = 960, tag: str = "IN"):
    """占位帧：角色底色 + 景别横条 + 表情强度竖条 + 顶部定色块"""
    path.parent.mkdir(parents=True, exist_ok=True)
    bg = frame_color(row, char, scene)
    nbar = SIZE_BARS.get(row["shot_size"], 2)
    eint = int(row["expr_int"])

    filters = []
    # 顶部定色块（角色识别用）
    filters.append(f"drawbox=x=0:y=0:w={w}:h={int(h*0.10)}:"
                   f"color={hexc(HUE_BY_CHAR.get(char,120),0.85,0.9)}:t=fill")
    # 景别横条
    for i in range(nbar):
        y = int(h * 0.20) + i * 46
        filters.append(f"drawbox=x={int(w*0.08)}:y={y}:w={int(w*0.84)}:h=28:"
                       f"color=white@0.85:t=fill")
    # 表情强度竖条
    for i in range(eint):
        x = int(w * 0.08) + i * 60
        filters.append(f"drawbox=x={x}:y={int(h*0.52)}:w=40:h={int(h*0.20)}:"
                       f"color=white@0.55:t=fill")
    # 底部尾帧标记（OUT 为双横线）
    if tag == "OUT":
        filters.append(f"drawbox=x={int(w*0.08)}:y={int(h*0.84)}:"
                       f"w={int(w*0.84)}:h=16:color=white@0.9:t=fill")
        filters.append(f"drawbox=x={int(w*0.08)}:y={int(h*0.89)}:"
                       f"w={int(w*0.84)}:h=16:color=white@0.9:t=fill")
    else:
        filters.append(f"drawbox=x={int(w*0.08)}:y={int(h*0.86)}:"
                       f"w={int(w*0.84)}:h=16:color=white@0.9:t=fill")
    # 场景边框色
    filters.append(f"drawbox=x=6:y=6:w={w-12}:h={h-12}:"
                   f"color={hexc(HUE_BY_SCENE.get(scene,0),0.8,0.9)}:t=8")

    ff([FFMPEG, "-y", "-f", "lavfi", "-i", f"color=c={bg}:s={w}x{h}:d=1",
        "-vf", ",".join(filters), "-frames:v", "1", str(path)])


def draw_video(path: Path, row: dict, char: str, scene: str, dur: float,
               w: int = 1080, h: int = 1920):
    """按块卡时长生成占位视频：底色 + 轻微亮度脉动（代表微动）"""
    path.parent.mkdir(parents=True, exist_ok=True)
    bg = frame_color(row, char, scene)
    nbar = SIZE_BARS.get(row["shot_size"], 2)
    filters = [f"drawbox=x=0:y=0:w={w}:h={int(h*0.10)}:"
               f"color={hexc(HUE_BY_CHAR.get(char,120),0.85,0.9)}:t=fill"]
    for i in range(nbar):
        y = int(h * 0.20) + i * 90
        filters.append(f"drawbox=x={int(w*0.08)}:y={y}:w={int(w*0.84)}:h=54:"
                       f"color=white@0.85:t=fill")
    for i in range(int(row["expr_int"])):
        x = int(w * 0.08) + i * 120
        filters.append(f"drawbox=x={x}:y={int(h*0.52)}:w=80:h={int(h*0.20)}:"
                       f"color=white@0.55:t=fill")
    filters.append("eq=brightness='0.03*sin(2*PI*t*0.8)'")

    ff([FFMPEG, "-y", "-f", "lavfi",
        "-i", f"color=c={bg}:s={w}x{h}:r=30:d={dur:.4f}",
        "-vf", ",".join(filters),
        "-c:v", "libx264", "-crf", "32", "-preset", "ultrafast",
        "-pix_fmt", "yuv420p", "-r", "30", str(path)])


def run(slug: str = SLUG, inject_flaw: bool = True, force: bool = False):
    proj = Project(ROOT, slug)
    script = read_json(proj.d_script / "script.json")
    ep_blocks = {(e["ep"], b["block"]): b for e in script["episodes"] for b in e["blocks"]}

    total_f = total_v = 0
    for ep in script["episodes"]:
        epn = ep["ep"]
        rows = read_csv(proj.d_scene / f"BLOCK_EP{epn:02d}.csv")
        for r in rows:
            bn, sn = int(r["block"]), int(r["shot"])
            b = ep_blocks[(epn, bn)]
            char = r["char_ids"].split("|")[0]
            scene = b["scene"]
            bdir = proj.d_blocks / f"EP{epn:02d}" / f"B{bn:02d}"
            fdir, cdir = bdir / "frames", bdir / "clips"
            dur = float(r["dur_sec"])

            fin = fdir / f"B{bn:02d}_SH{sn:02d}_IN.png"
            fout = fdir / f"B{bn:02d}_SH{sn:02d}_OUT.png"
            if force or not fin.exists():
                draw_frame(fin, r, char, scene, tag="IN")
                total_f += 1
            if force or not fout.exists():
                draw_frame(fout, r, char, scene, tag="OUT")
                total_f += 1

            clip = cdir / f"B{bn:02d}_SH{sn:02d}.mp4"
            if force or not clip.exists():
                draw_video(clip, r, char, scene, dur)
                total_v += 1

            act_in = cdir / f"B{bn:02d}_SH{sn:02d}_actual_IN.png"
            act_out = cdir / f"B{bn:02d}_SH{sn:02d}_actual_OUT.png"
            if force or not act_in.exists():
                ff([FFMPEG, "-y", "-i", str(clip), "-frames:v", "1", str(act_in)])
            if force or not act_out.exists():
                ff([FFMPEG, "-y", "-sseof", "-0.1", "-i", str(clip),
                    "-frames:v", "1", str(act_out)])

    injected = None
    if inject_flaw:
        rows = read_csv(proj.d_scene / "BLOCK_EP01.csv")
        target = next(r for r in rows if r["block"] == "3" and r["shot"] == "3")
        bad = proj.d_blocks / "EP01" / "B03" / "clips" / "B03_SH03_actual_OUT.png"
        b = ep_blocks[(1, 3)]
        fake = dict(target)
        fake["expr_int"] = "1"
        fake["shot_size"] = "FS"          # 景别也换了 → A 道和 C 道都该抓到
        draw_frame(bad, fake, "C_ALLY", b["scene"], tag="IN")
        injected = "B03_SH03 实际尾帧换成错误角色 + 错景别（模拟抽卡抽崩）"
        print(f"  [注入缺陷] {injected}")

    print(f"  mock 素材：首尾帧 {total_f} 张 / 视频 {total_v} 条（已存在的跳过）")
    return injected


if __name__ == "__main__":
    print("=== 生成 mock 素材（模拟抽卡结果）===")
    run(force="--force" in sys.argv)
