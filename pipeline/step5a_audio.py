# -*- coding: utf-8 -*-
"""step5a_audio.py · 第 ⑤ 步 · 音频先行（voice-first）

这是整个工作流最省钱的机制：先出配音，量出真实时长，吸附到 1.875 网格，
回写块卡的 dur_bar / dur_sec，然后画面才按这个时长生成。

如果先做画面再配音，只有三个烂选择：拉慢视频（变糊）/ 配音变速（毁音色）/ 裁画面（废构图）。

本模块做三件事：
1. 生成本地 mock 配音（ffmpeg 合成不同音色的正弦调制音，时长按台词字数估算）
2. 实测时长 → 吸附网格 → 回写块卡
3. 生成 BGM（整集 48 小节，4 层）+ SFX + SRT
"""
from __future__ import annotations

import math
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import (BAR_SEC, BLOCK_SEC, ROOT, Gate, Project, bar_time, bars_to_sec,
                    log, read_csv, read_json, save_gate, sec_to_bars, write_csv,
                    write_json)

SLUG = "demo_雨夜的订单"
FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"


# ============================================================
# 工具
# ============================================================
def ff_dur(path: Path) -> float:
    out = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def ff_run(args: list[str]):
    r = subprocess.run(args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        err = (r.stderr or "")[-800:]
        raise RuntimeError(f"ffmpeg failed: {' '.join(args[:6])}...\n{err}")
    return r


# ============================================================
# 音色参数（对应音色表 VOICE_V1）
# ============================================================
VOICE_PARAMS = {
    "VOICE_LEAD_01":    dict(f0=115, timbre=0.35, rate=0.95),   # 男 偏低 微哑
    "VOICE_VILLAIN_01": dict(f0=220, timbre=0.62, rate=1.05),   # 女 中高 尖
    "VOICE_ALLY_01":    dict(f0=185, timbre=0.45, rate=1.00),   # 女 中 清亮
}
# 情绪 → 语速系数 / 停顿
EMOTION_RATE = {
    "EXP_ANGER_L": (0.95, 0.20), "EXP_ANGER_M": (0.95, 0.20), "EXP_ANGER_H": (1.10, 0.0),
    "EXP_GRIEF_L": (0.90, 0.28), "EXP_GRIEF_M": (0.88, 0.35), "EXP_GRIEF_H": (0.92, 0.25),
    "EXP_SHOCK_L": (1.00, 0.20), "EXP_SHOCK_M": (1.00, 0.30), "EXP_SHOCK_H": (1.05, 0.15),
    "EXP_CONTEMPT_L": (1.05, 0.35), "EXP_CONTEMPT_M": (1.05, 0.40), "EXP_CONTEMPT_H": (1.08, 0.35),
    "EXP_RESOLVE_L": (0.95, 0.15), "EXP_RESOLVE_M": (0.92, 0.15), "EXP_RESOLVE_H": (0.90, 0.12),
    "EXP_TENDER_L": (0.95, 0.25), "EXP_TENDER_M": (0.92, 0.25), "EXP_TENDER_H": (0.95, 0.22),
}


def estimate_speech_sec(text: str, rate: float) -> float:
    """按中文字数估算真人语速：约 4.2 字/秒，乘情绪语速系数"""
    n = len(re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", text))
    if n == 0:
        return 0.0
    return n / (4.2 * rate)


def synth_voice(path: Path, sec: float, f0: float, timbre: float, expr_code: str):
    """造一段"类语音"音频：基频+谐波+颤动，代表该音色在该情绪下的时长与质感"""
    path.parent.mkdir(parents=True, exist_ok=True)
    if sec <= 0.05:
        ff_run([FFMPEG, "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono",
                "-t", "0.1", str(path)])
        return
    d = f"{sec:.3f}"
    tremor = 5.5 if ("GRIEF" in expr_code or "SHOCK" in expr_code) else 6.5
    # 基频 1.0 / 二次谐波 timbre*0.5 / 三次谐波 timbre*0.25 + 颤动
    graph = (
        f"sine=frequency={f0}:duration={d}[f1];"
        f"sine=frequency={f0*2:.2f}:duration={d}[f2];"
        f"sine=frequency={f0*3:.2f}:duration={d}[f3];"
        f"[f1][f2][f3]amix=inputs=3:"
        f"weights={1.0-timbre:.2f} {timbre*0.5:.2f} {timbre*0.25:.2f}:normalize=0[m];"
        f"[m]tremolo=f={tremor}:d=0.35,volume=0.55,"
        f"afade=t=in:d=0.02,afade=t=out:st={max(0,sec-0.05):.3f}:d=0.05,"
        f"aformat=channel_layouts=mono[out]"
    )
    ff_run([FFMPEG, "-y", "-filter_complex", graph, "-map", "[out]",
            "-t", d, "-ar", "48000", "-ac", "1", str(path)])


# ============================================================
# BGM 四层（整集 48 小节，块只是切片）
# ============================================================
def build_bgm_layer(out: Path, total_sec: float, kind: str):
    """PAD 氛围 / LOOP 节奏 / STRINGS 情绪 —— 用 synth + 滤镜实现，避免超长表达式"""
    out.parent.mkdir(parents=True, exist_ok=True)
    d = f"{total_sec:.3f}"
    if kind == "PAD":
        # 三个低频正弦叠加 + 慢速起伏（0.25Hz），代表弦乐长音铺底
        graph = (
            f"sine=frequency=110:duration={d}[a];"
            f"sine=frequency=164.81:duration={d}[b];"
            f"sine=frequency=220:duration={d}[c];"
            f"[a][b][c]amix=inputs=3:weights=0.5 0.35 0.25:normalize=0[m];"
            f"[m]tremolo=f=0.25:d=0.4,volume=0.16,"
            f"afade=t=in:d=1.5,afade=t=out:st={max(0,total_sec-1.5):.3f}:d=1.5,"
            f"aformat=channel_layouts=stereo[out]"
        )
    elif kind == "LOOP":
        # 节奏层：70Hz 低频脉冲，tremolo 频率 = 128BPM/60 = 2.1333Hz
        graph = (
            f"sine=frequency=70:duration={d}[k];"
            f"[k]tremolo=f=2.13333:d=0.95,volume=0.11,"
            f"aformat=channel_layouts=stereo[out]"
        )
    elif kind == "STRINGS":
        # 情绪层：中频双音缓慢起伏
        graph = (
            f"sine=frequency=329.63:duration={d}[x];"
            f"sine=frequency=392:duration={d}[y];"
            f"[x][y]amix=inputs=2:normalize=0[m];"
            f"[m]tremolo=f=0.4:d=0.5,volume=0.10,"
            f"afade=t=in:d=1.0,afade=t=out:st={max(0,total_sec-1.0):.3f}:d=1.0,"
            f"aformat=channel_layouts=stereo[out]"
        )
    else:
        graph = f"anullsrc=r=48000:cl=stereo:d={d}[out]"

    ff_run([FFMPEG, "-y", "-filter_complex", graph, "-map", "[out]",
            "-t", d, "-ar", "48000", "-ac", "2", str(out)])


def build_hits(out: Path, hit_times: list[float], total_sec: float):
    """冲击层：低频砸击，落在指定秒点（用 adelay + amix，避免超长表达式）"""
    out.parent.mkdir(parents=True, exist_ok=True)
    d = f"{total_sec:.3f}"
    if not hit_times:
        ff_run([FFMPEG, "-y", "-f", "lavfi", "-i",
                f"anullsrc=r=48000:cl=stereo:d={d}",
                "-t", d, "-ac", "2", str(out)])
        return

    inputs, filters, labels = [], [], []
    for i, t in enumerate(hit_times):
        ms = int(round(t * 1000))
        inputs += ["-f", "lavfi", "-i",
                   "sine=frequency=55:duration=0.30"]
        filters.append(f"[{i}:a]volume=0.55,afade=t=out:st=0.04:d=0.26,"
                       f"adelay={ms}|{ms},aformat=channel_layouts=stereo[h{i}]")
        labels.append(f"[h{i}]")
    filters.append("".join(labels) +
                   f"amix=inputs={len(labels)}:normalize=0,"
                   f"apad=whole_dur={d},atrim=0:{d}[out]")
    ff_run([FFMPEG, "-y", *inputs,
            "-filter_complex", ";".join(filters), "-map", "[out]",
            "-t", d, "-ar", "48000", "-ac", "2", str(out)])


def build_sfx(out: Path, kind: str, total_sec: float):
    """音效：雨声/门铃/心跳/whoosh/雷/翻页"""
    out.parent.mkdir(parents=True, exist_ok=True)
    d = f"{total_sec:.3f}"
    m = {
        "雨声": "anoisesrc=c=white:r=48000:a=0.10,highpass=f=1200,volume=0.45",
        "雨声底噪": "anoisesrc=c=white:r=48000:a=0.08,highpass=f=1000,volume=0.40",
        "门铃": "sine=frequency=880:r=48000,tremolo=f=8:d=0.7,volume=0.30",
        "门开声": "anoisesrc=c=brown:r=48000:a=0.20,lowpass=f=400,volume=0.50",
        "心跳": "sine=frequency=58:r=48000,tremolo=f=2.2:d=0.9,volume=0.45",
        "雷声": "anoisesrc=c=brown:r=48000:a=0.28,lowpass=f=180,volume=0.65",
        "低频砸击": "sine=frequency=48:r=48000,volume=0.60",
        "whoosh": "anoisesrc=c=pink:r=48000:a=0.15,bandpass=f=2000:width=1500,volume=0.45",
        "纸质翻页": "anoisesrc=c=pink:r=48000:a=0.12,highpass=f=2500,volume=0.40",
    }
    src = m.get(kind, "anoisesrc=c=pink:r=48000:a=0.05,volume=0.35")
    ff_run([FFMPEG, "-y", "-f", "lavfi", "-i", src,
            "-t", d, "-ar", "48000", "-ac", "1", str(out)])


# ============================================================
# 主流程
# ============================================================
def run(slug: str = SLUG) -> Gate:
    proj = Project(ROOT, slug)
    script = read_json(proj.d_script / "script.json")
    g = Gate("第⑤步·A · 音频先行门禁")

    voice_tbl = _parse_voice_table(proj.d_char / "音色表.md")
    char_by_id = {c["id"]: c for c in script["characters"]}

    for ep in script["episodes"]:
        epn = ep["ep"]
        blocks = ep["blocks"]
        # 读回第③步生成的块卡
        blk_csv = proj.d_scene / f"BLOCK_EP{epn:02d}.csv"
        rows = read_csv(blk_csv)
        rows_by_key = {(int(r["block"]), int(r["shot"])): r for r in rows}

        ep_total = sum(float(r["dur_sec"]) for r in rows)
        print(f"\n  EP{epn:02d} · {len(blocks)} 块 / {len(rows)} 镜 / {ep_total:.2f}s")

        srt_entries = []
        hit_times = []
        abs_time = 0.0

        for b in blocks:
            bn = b["block"]
            bdir = proj.d_blocks / f"EP{epn:02d}" / f"B{bn:02d}"
            voice_dir = bdir / "voice"
            sfx_dir = bdir / "sfx"
            voice_dir.mkdir(parents=True, exist_ok=True)
            sfx_dir.mkdir(parents=True, exist_ok=True)

            block_voice_files = []

            for s in b["shots"]:
                sn = s["shot"]
                key = (bn, sn)
                r = rows_by_key[key]
                primary = s["chars"][0]
                vid = char_by_id[primary].get("voice_id", "VOICE_LEAD_01")
                vp = VOICE_PARAMS.get(vid, VOICE_PARAMS["VOICE_LEAD_01"])
                base_rate, pause = EMOTION_RATE.get(s["expr"], (1.0, 0.2))

                has_line = s["line"] not in ("—", "-", "")
                wav = voice_dir / f"B{bn:02d}_SH{sn:02d}.wav"

                if has_line:
                    est = estimate_speech_sec(s["line"], vp["rate"] * base_rate)
                    # 生成 2 版候选（模拟抽卡），选更接近目标的那条
                    cand = []
                    for att in (1, 2):
                        p = voice_dir / f"B{bn:02d}_SH{sn:02d}_a{att}.wav"
                        synth_voice(p, est * (1 + 0.02 * (att - 1)), vp["f0"],
                                    vp["timbre"], s["expr"])
                        cand.append((p, ff_dur(p)))
                    # 选与估算最接近的
                    best = min(cand, key=lambda x: abs(x[1] - est))
                    best[0].replace(wav)
                    measured = ff_dur(wav)
                else:
                    synth_voice(wav, 0.1, vp["f0"], vp["timbre"], s["expr"])
                    measured = 0.0

                # ---------- 吸附网格 ----------
                if has_line:
                    bars = sec_to_bars(measured + pause)
                    new_dur_sec = bars_to_sec(bars)
                    # 若吸附后超过原片长，允许（块内会重算），但记录
                else:
                    bars = int(r["dur_bar"])
                    new_dur_sec = bars_to_sec(bars)
                    measured = 0.0

                r["_measured_voice_sec"] = f"{measured:.3f}"
                r["_bars_from_voice"] = bars
                r["_new_dur_sec"] = f"{new_dur_sec:.3f}"
                block_voice_files.append((sn, wav, new_dur_sec, has_line))

            # ---------- 块内重排（保证 8 小节 = 15.000s）----------
            fixed = _rebalance_block(block_voice_files, bn, rows_by_key, g, epn)

            for sn, wav, dur_sec, has_line in block_voice_files:
                r = rows_by_key[(bn, sn)]
                r["dur_bar"] = str(int(round(dur_sec / BAR_SEC)))
                r["dur_sec"] = f"{dur_sec:.3f}"

            # 重算 bar_start / time_in_block
            t = 0.0
            for sn, wav, dur_sec, has_line in block_voice_files:
                r = rows_by_key[(bn, sn)]
                r["bar_start"] = str(int(round(t / BAR_SEC)) + 1)
                r["time_in_block"] = f"{t:.3f}"
                if has_line:
                    srt_entries.append({
                        "idx": len(srt_entries) + 1,
                        "start": abs_time + t + 0.15,
                        "end": abs_time + t + 0.15 + float(r["_measured_voice_sec"]),
                        "text": r["sub_text"],
                    })
                t += dur_sec

            g.check(abs(t - BLOCK_SEC) < 0.05,
                    f"EP{epn:02d}B{bn:02d} 重排后块内时长 15.000s", f"{t:.3f}s")

            # ---------- SFX ----------
            for s in b["shots"]:
                if s["sfx"] in ("—", "-", ""):
                    continue
                sn = s["shot"]
                r = rows_by_key[(bn, sn)]
                dur = float(r["dur_sec"])
                sp = sfx_dir / f"B{bn:02d}_SH{sn:02d}_{_slug(s['sfx'])}.wav"
                if not sp.exists():
                    build_sfx(sp, s["sfx"], dur)

            # ---------- HIT 点 ----------
            for sn, wav, dur_sec, has_line in block_voice_files:
                r = rows_by_key[(bn, sn)]
                if r["bgm_cue"].startswith("BEAT_DROP") or r["bgm_cue"] == "HIT":
                    hit_times.append(abs_time + float(r["time_in_block"]))

            abs_time += BLOCK_SEC

        # ---------- 写回块卡 ----------
        write_csv(blk_csv, rows)

        # ---------- BGM 整集 ----------
        bgm_dir = proj.d_blocks / f"EP{epn:02d}" / "bgm"
        bgm_dir.mkdir(parents=True, exist_ok=True)
        ep_sec = abs_time
        for kind in ("PAD", "LOOP", "STRINGS"):
            p = bgm_dir / f"EP{epn:02d}_{kind}.wav"
            build_bgm_layer(p, ep_sec, kind)
            g.check(ff_dur(p) > 0, f"EP{epn:02d} BGM {kind} 已生成", f"{ff_dur(p):.2f}s")
        build_hits(bgm_dir / f"EP{epn:02d}_HIT.wav", hit_times, ep_sec)

        # ---------- 卡点表 ----------
        cue_rows = []
        for r in rows:
            bar_abs = (int(r["block"]) - 1) * 8 + int(r["bar_start"])
            cue_rows.append({
                "ep": epn, "block": r["block"], "shot": r["shot"],
                "bar_abs": bar_abs,
                "time_sec": f"{bar_time(bar_abs):.4f}",
                "layer": r["bgm_layer"],
                "cue": r["bgm_cue"],
                "sfx": r["sfx"],
            })
        write_csv(proj.d_scene / f"配乐卡点表_EP{epn:02d}.csv", cue_rows)

        # ---------- SRT ----------
        srt_path = proj.d_out / f"EP{epn:02d}.srt"
        srt_path.parent.mkdir(parents=True, exist_ok=True)
        srt_path.write_text(_srt(srt_entries), encoding="utf-8")

        # ---------- 门禁：语音时长 vs 镜时长 ----------
        for r in rows:
            mv = float(r["_measured_voice_sec"])
            ds = float(r["dur_sec"])
            if mv > 0:
                g.check(mv <= ds + 0.05,
                        f"EP{epn:02d}B{int(r['block']):02d}SH{int(r['shot']):02d} 配音不超镜长",
                        f"voice {mv:.2f}s / shot {ds:.2f}s")

        n_line = sum(1 for r in rows if float(r["_measured_voice_sec"]) > 0)
        print(f"  配音 {n_line} 句 | BGM 3 层 + HIT {len(hit_times)} 点 | 集长 {ep_sec:.2f}s")
        print(f"  → {blk_csv.name} / 配乐卡点表_EP{epn:02d}.csv / EP{epn:02d}.srt")

    # 清理临时列不写盘（保留在内存即可，这里已写过一次带临时列的，重写干净版）
    for ep in script["episodes"]:
        blk_csv = proj.d_scene / f"BLOCK_EP{ep['ep']:02d}.csv"
        rows = read_csv(blk_csv)
        for r in rows:
            for k in list(r.keys()):
                if k.startswith("_"):
                    del r[k]
        write_csv(blk_csv, rows)

    save_gate(g, proj.d_report / "gate_05a_audio.txt")
    return g


def _rebalance_block(items, bn, rows_by_key, g, epn):
    """块内时长必须收口到 8 小节 = 15.000s。

    正确的分配逻辑（这次测试发现的关键点）：
      不是"把余量塞给无台词镜"，而是按**表演权重**分配——
      ECU/CU 特写 1–2 小节（特写挂太久观众出戏），MS 2–3，MFS 3 上限。
      有台词镜的下限由配音长度决定（语音吸附后的 bars）。

    分三步：
      A. 有台词镜先定下限（= 语音吸附 bars）
      B. 剩余小节按镜的表演容量上限做加权轮分配
      C. 收口失败 → 报错回第①步（剧本层缺陷）
    """
    FACE_CAP = {"ECU": 2, "CU": 2, "MS": 3, "MFS": 3, "FS": 3, "ELS": 3}

    def cap_of(i):
        r = rows_by_key[(bn, items[i][0])]
        return FACE_CAP.get(r["shot_size"], 3)

    # A. 有台词镜已按语音定好（items 里的 d 就是吸附结果）
    total = sum(d for _, _, d, _ in items)
    diff = round((BLOCK_SEC - total) / BAR_SEC)

    # B. 分轮分配
    while diff != 0:
        progressed = False
        # 变长：所有镜按容量上限加，无台词镜优先（它们当前偏短）
        if diff > 0:
            cand = [i for i in range(len(items))
                    if int(round(items[i][2] / BAR_SEC)) < cap_of(i)]
            # 排优先级：先补无台词，再补有台词
            cand.sort(key=lambda i: (items[i][3], int(round(items[i][2] / BAR_SEC))))
            for i in cand:
                if diff <= 0:
                    break
                sn, w, d, hl = items[i]
                cur = int(round(d / BAR_SEC))
                items[i] = (sn, w, bars_to_sec(cur + 1), hl)
                diff -= 1
                progressed = True
        # 变短：只压无台词镜，且不低于 1 小节
        else:
            cand = [i for i in range(len(items))
                    if not items[i][3] and int(round(items[i][2] / BAR_SEC)) > 1]
            for i in cand:
                if diff >= 0:
                    break
                sn, w, d, hl = items[i]
                cur = int(round(d / BAR_SEC))
                items[i] = (sn, w, bars_to_sec(cur - 1), hl)
                diff += 1
                progressed = True
        if not progressed:
            break

    if diff != 0:
        g.check(False, f"EP{epn:02d}B{bn:02d} 块时长收口失败",
                f"残差 {diff} 小节 —— 台词总量超出 8 小节容量或镜数不足，"
                f"请回第①步减少该块台词 / 拆块 / 增加镜数")
    else:
        # 附带检查：特写镜不应超过容量上限（表演合理性）
        for i, (sn, w, d, hl) in enumerate(items):
            bars = int(round(d / BAR_SEC))
            g.check(bars <= cap_of(i),
                    f"EP{epn:02d}B{bn:02d}SH{sn:02d} 镜长不超过景别容量上限",
                    f"{bars} 小节 > 上限 {cap_of(i)}")

    return diff

    if diff_bars != 0:
        # 收口失败 → 这是剧本层缺陷（台词塞不进 8 小节），必须回第 ① 步
        longest = max((len(t) for _, _, _, t in items if False), default=0)
        g.check(False, f"EP{epn:02d}B{bn:02d} 块时长收口失败",
                f"残差 {diff_bars} 小节 —— 台词总量超出 8 小节容量，"
                f"请回第①步把该块台词减少或拆块")

    return diff_bars


def _parse_voice_table(path: Path) -> dict:
    out = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("|") and "VOICE_" in line:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 5:
                out[cells[0]] = cells[4]
    return out


def _slug(s: str) -> str:
    import hashlib
    return hashlib.md5(s.encode()).hexdigest()[:6]


def _srt(entries) -> str:
    def ts(t: float) -> str:
        h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
        return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")
    lines = []
    for e in entries:
        lines.append(f"{e['idx']}\n{ts(e['start'])} --> {ts(e['end'])}\n{e['text']}\n")
    return "\n".join(lines)


if __name__ == "__main__":
    gate = run()
    print(gate.report())
    sys.exit(0 if gate.passed else 1)
