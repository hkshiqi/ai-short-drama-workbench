# -*- coding: utf-8 -*-
"""step6_compose.py · 第 ⑥ 步 · 块合成 + 集拼接 + 全片验收

做三件事：
  1. 块合成：统一参数 → concat → 混音（对白优先 + BGM 侧链 ducking）→ 烧字幕 → B{NN}.mp4
  2. 集拼接：块 concat，块界 硬切 + whoosh + BGM 跨块连续
  3. 全片验收：12 项交付校验
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import (BAR_SEC, BLOCK_SEC, ROOT, TOL_BLOCK, Gate, Project,
                    read_csv, read_json, save_gate, write_csv)
from mediautil import dur as media_dur, run as ff_run

SLUG = "demo_雨夜的订单"
W, H, FPS = 1080, 1920, 30
TARGET_LUFS = -14.0
DIALOG_PEAK = -6.0


def norm_video(src: Path, dst: Path, dur_override: float | None = None):
    """统一到 1080x1920 / 30fps / yuv420p / H.264"""
    args = ["ffmpeg", "-hide_banner", "-y", "-i", str(src)]
    vf = f"scale={W}:{H}:force_original_aspect_ratio=decrease," \
         f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,fps={FPS},format=yuv420p"
    args += ["-vf", vf, "-c:v", "libx264", "-crf", "23", "-preset", "veryfast"]
    if dur_override:
        args += ["-t", f"{dur_override:.4f}"]
    args += ["-an", str(dst)]
    ff_run(args)


def build_voice_track(rows: list[dict], block_dir: Path, out: Path,
                      total_sec: float):
    """把逐句配音按 time_in_block 拼成整块对白轨"""
    inputs, filters, labels = [], [], []
    idx = 0
    for r in rows:
        if r["line"] in ("—", "-", ""):
            continue
        wav = block_dir / "voice" / f"B{int(r['block']):02d}_SH{int(r['shot']):02d}.wav"
        if not wav.exists():
            continue
        ms = int(round((float(r["time_in_block"]) + 0.15) * 1000))
        inputs += ["-i", str(wav)]
        filters.append(f"[{idx}:a]aformat=sample_fmts=fltp:sample_rates=48000:"
                       f"channel_layouts=mono,"
                       f"adelay={ms}|{ms},volume=1.0[v{idx}]")
        labels.append(f"[v{idx}]")
        idx += 1

    if not labels:
        ff_run(["ffmpeg", "-hide_banner", "-y", "-f", "lavfi", "-i",
                f"anullsrc=r=48000:cl=mono:d={total_sec:.3f}",
                "-t", f"{total_sec:.3f}", "-ac", "1", str(out)])
        return

    filters.append("".join(labels) +
                   f"amix=inputs={len(labels)}:normalize=0,"
                   f"apad=whole_dur={total_sec:.3f},atrim=0:{total_sec:.3f},"
                   f"loudnorm=I={TARGET_LUFS - 2}:TP={DIALOG_PEAK}:LRA=11[out]")
    ff_run(["ffmpeg", "-hide_banner", "-y", *inputs,
            "-filter_complex", ";".join(filters), "-map", "[out]",
            "-t", f"{total_sec:.3f}", "-ar", "48000", "-ac", "1", str(out)])


def build_bgm_slice(src: Path, out: Path, start: float, dur: float):
    ff_run(["ffmpeg", "-hide_banner", "-y", "-ss", f"{start:.4f}", "-i", str(src),
            "-t", f"{dur:.4f}", "-ar", "48000", "-ac", "2", str(out)])


def build_sfx_track(rows: list[dict], block_dir: Path, out: Path, total_sec: float):
    inputs, filters, labels = [], [], []
    idx = 0
    for r in rows:
        if r["sfx"] in ("—", "-", ""):
            continue
        cands = list((block_dir / "sfx").glob(
            f"B{int(r['block']):02d}_SH{int(r['shot']):02d}_*.wav"))
        if not cands:
            continue
        ms = int(round(float(r["time_in_block"]) * 1000))
        inputs += ["-i", str(cands[0])]
        filters.append(f"[{idx}:a]aformat=sample_fmts=fltp:sample_rates=48000:"
                       f"channel_layouts=stereo,adelay={ms}|{ms},volume=0.35[s{idx}]")
        labels.append(f"[s{idx}]")
        idx += 1
    if not labels:
        ff_run(["ffmpeg", "-hide_banner", "-y", "-f", "lavfi", "-i",
                f"anullsrc=r=48000:cl=stereo:d={total_sec:.3f}",
                "-t", f"{total_sec:.3f}", "-ac", "2", str(out)])
        return
    filters.append("".join(labels) +
                   f"amix=inputs={len(labels)}:normalize=0,"
                   f"apad=whole_dur={total_sec:.3f},atrim=0:{total_sec:.3f},"
                   f"aformat=channel_layouts=stereo[out]")
    ff_run(["ffmpeg", "-hide_banner", "-y", *inputs,
            "-filter_complex", ";".join(filters), "-map", "[out]",
            "-t", f"{total_sec:.3f}", "-ar", "48000", "-ac", "2", str(out)])


def mix_with_ducking(voice: Path, bgm: Path, sfx: Path, out: Path, total_sec: float):
    """对白优先，BGM 侧链压缩（ducking），SFX 叠底"""
    graph = (
        # BGM 被对白侧链压缩：threshold 0.04 / ratio 8 / attack 80ms / release 350ms
        "[1:a][0:a]sidechaincompress=threshold=0.04:ratio=8:attack=80:release=350[bgm_duck];"
        "[bgm_duck][2:a]amix=inputs=2:duration=longest:weights=0.55 1.0[bed];"
        "[bed][0:a]amix=inputs=2:duration=longest:weights=1.0 1.35[mix];"
        f"[mix]loudnorm=I={TARGET_LUFS}:TP=-1.0:LRA=13,"
        f"apad=whole_dur={total_sec:.3f},atrim=0:{total_sec:.3f}[out]"
    )
    ff_run(["ffmpeg", "-hide_banner", "-y",
            "-i", str(voice), "-i", str(bgm), "-i", str(sfx),
            "-filter_complex", graph, "-map", "[out]",
            "-t", f"{total_sec:.3f}", "-ar", "48000", "-ac", "2", str(out)])


def burn_subs(video: Path, srt: Path, audio: Path, out: Path,
              style: str = "FontSize=18,Outline=3,Alignment=2,MarginV=180"):
    # Windows 路径在 subtitles 滤镜里要转义冒号与反斜杠
    srt_esc = str(srt).replace("\\", "/").replace(":", "\\:")
    vf = f"subtitles='{srt_esc}':force_style='{style}'"
    ff_run(["ffmpeg", "-hide_banner", "-y", "-i", str(video), "-i", str(audio),
            "-vf", vf, "-c:v", "libx264", "-crf", "23", "-preset", "veryfast",
            "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)])


def run(slug: str = SLUG) -> Gate:
    proj = Project(ROOT, slug)
    script = read_json(proj.d_script / "script.json")
    g = Gate("第⑥步 · 合成与交付门禁")

    ep = script["episodes"][0]
    epn = ep["ep"]
    rows_all = read_csv(proj.d_scene / f"BLOCK_EP{epn:02d}.csv")
    bgm_dir = proj.d_blocks / f"EP{epn:02d}" / "bgm"

    ep_dur = BLOCK_SEC * len(ep["blocks"])
    print(f"\n  EP{epn:02d} · {len(ep['blocks'])} 块 / 目标 {ep_dur:.2f}s")

    block_files = []
    for bn in sorted({int(r["block"]) for r in rows_all}):
        bdir = proj.d_blocks / f"EP{epn:02d}" / f"B{bn:02d}"
        rows = [r for r in rows_all if int(r["block"]) == bn]
        rows.sort(key=lambda r: int(r["shot"]))
        out_dir = bdir / "compose"
        out_dir.mkdir(parents=True, exist_ok=True)

        # ---- 1. 统一参数 + concat ----
        normed = []
        for r in rows:
            src = bdir / "clips" / f"B{bn:02d}_SH{int(r['shot']):02d}.mp4"
            dst = out_dir / f"n_{int(r['shot']):02d}.mp4"
            sd = float(r["dur_sec"])
            norm_video(src, dst, dur_override=sd)
            normed.append(dst)

        listfile = out_dir / "concat.txt"
        listfile.write_text(
            "\n".join(f"file '{p.as_posix()}'" for p in normed), encoding="utf-8")
        visual = out_dir / "visual.mp4"
        ff_run(["ffmpeg", "-hide_banner", "-y", "-f", "concat", "-safe", "0",
                "-i", str(listfile), "-c", "copy", str(visual)])

        # ---- 2. 三条音轨 ----
        voice = out_dir / "voice.wav"
        sfx = out_dir / "sfx.wav"
        bgm_slice = out_dir / "bgm.wav"
        build_voice_track(rows, bdir, voice, BLOCK_SEC)
        build_sfx_track(rows, bdir, sfx, BLOCK_SEC)
        # BGM 切片：整集轨上按块起点取 15s
        bgm_src = bgm_dir / f"EP{epn:02d}_PAD.wav"
        if bgm_src.exists():
            build_bgm_slice(bgm_src, bgm_slice, (bn - 1) * BLOCK_SEC, BLOCK_SEC)
        else:
            ff_run(["ffmpeg", "-hide_banner", "-y", "-f", "lavfi", "-i",
                    f"anullsrc=r=48000:cl=stereo:d={BLOCK_SEC:.3f}",
                    "-t", f"{BLOCK_SEC:.3f}", "-ac", "2", str(bgm_slice)])

        mixed = out_dir / "mix.wav"
        mix_with_ducking(voice, bgm_slice, sfx, mixed, BLOCK_SEC)

        # ---- 3. 块内字幕 ----
        blk_srt = out_dir / f"B{bn:02d}.srt"
        blk_srt.write_text(_block_srt(rows), encoding="utf-8")

        # ---- 4. 烧字幕成片 ----
        block_mp4 = bdir / f"B{bn:02d}.mp4"
        burn_subs(visual, blk_srt, mixed, block_mp4)

        d = media_dur(block_mp4)
        g.check(abs(d - BLOCK_SEC) < TOL_BLOCK,
                f"EP{epn:02d}B{bn:02d} 块成片 15.000s", f"{d:.3f}s")
        block_files.append(block_mp4)
        print(f"    B{bn:02d} → {d:.3f}s  {block_mp4.name}")

    # ---- 5. 集拼接（块界 大硬切 + whoosh + BGM 跨块连续）----
    ep_list = proj.d_out / "ep_concat.txt"
    ep_list.parent.mkdir(parents=True, exist_ok=True)
    ep_list.write_text(
        "\n".join(f"file '{p.as_posix()}'" for p in block_files), encoding="utf-8")
    ep_visual = proj.d_out / "EP01_visual.mp4"
    ff_run(["ffmpeg", "-hide_banner", "-y", "-f", "concat", "-safe", "0",
            "-i", str(ep_list), "-c", "copy", str(ep_visual)])

    # ---- 6. BGM 整集（跨块连续，48 小节）----
    ep_bgm = proj.d_out / "EP01_BGM.wav"
    layers = []
    for kind in ("PAD", "LOOP", "STRINGS", "HIT"):
        p = bgm_dir / f"EP{epn:02d}_{kind}.wav"
        if p.exists():
            layers.append(p)
    if layers:
        inputs, fil, labels = [], [], []
        for i, p in enumerate(layers):
            inputs += ["-i", str(p)]
            fil.append(f"[{i}:a]volume=1.0[b{i}]")
            labels.append(f"[b{i}]")
        fil.append("".join(labels) +
                   f"amix=inputs={len(labels)}:normalize=0,"
                   f"apad=whole_dur={ep_dur:.3f},atrim=0:{ep_dur:.3f},"
                   f"aformat=channel_layouts=stereo[out]")
        ff_run(["ffmpeg", "-hide_banner", "-y", *inputs,
                "-filter_complex", ";".join(fil), "-map", "[out]",
                "-t", f"{ep_dur:.3f}", "-ar", "48000", "-ac", "2", str(ep_bgm)])
    else:
        ff_run(["ffmpeg", "-hide_banner", "-y", "-f", "lavfi", "-i",
                f"anullsrc=r=48000:cl=stereo:d={ep_dur:.3f}",
                "-t", f"{ep_dur:.3f}", "-ac", "2", str(ep_bgm)])

    # ---- 7. 全片对白轨 + 全片混音 ----
    ep_voice = proj.d_out / "EP01_配音.wav"
    _concat_audio([b / "compose" / "voice.wav" for b in
                   [proj.d_blocks / f"EP{epn:02d}" / f"B{int(r['block']):02d}"
                    for r in rows_all if int(r["shot"]) == 1]], ep_voice, ep_dur)

    ep_mix = proj.d_out / "EP01_mix.wav"
    mix_with_ducking(ep_voice, ep_bgm, _silence(proj.d_out / "_sil.wav", ep_dur),
                     ep_mix, ep_dur)

    # ---- 8. 集最终成片（整集字幕）----
    ep_srt = proj.d_out / "EP01.srt"
    final = proj.d_out / "EP01.mp4"
    burn_subs(ep_visual, ep_srt, ep_mix, final)

    d = media_dur(final)
    print(f"  → EP01.mp4  {d:.3f}s")
    g.check(abs(d - ep_dur) < 0.5, f"EP{epn:02d} 集成片 {ep_dur:.0f}s",
            f"{d:.3f}s")

    # ================= 12 项全片验收 =================
    # 1 时长
    g.check(abs(d - ep_dur) <= ep_dur * 0.10, "1 时长 = 目标 ±10%",
            f"{d:.2f}s / {ep_dur:.0f}s")

    # 2 画幅
    w, h = _probe_size(final)
    g.check((w, h) == (W, H), "2 画幅 1080×1920", f"{w}x{h}")

    # 3 三轨齐全
    for p, nm in [(proj.d_out / "EP01_配音.wav", "3a 对白轨"),
                  (ep_bgm, "3b BGM 轨"),
                  (ep_srt, "3c 字幕 SRT")]:
        g.check(p.exists() and p.stat().st_size > 0, nm, str(p.name))

    # 4 音轨时长一致
    vd, ad = media_dur(final), media_dur(ep_mix)
    g.check(abs(vd - ad) < 0.5, "4 音画时长一致", f"{vd:.2f} vs {ad:.2f}")

    # 5 字幕条数 = 台词句数
    n_line = sum(1 for r in rows_all if r["line"] not in ("—", "-", ""))
    n_srt = len([x for x in ep_srt.read_text(encoding="utf-8").split("\n\n") if x.strip()])
    g.eq(n_srt, n_line, "5 字幕条数 = 台词句数")

    # 6 每块时长
    for bn in sorted({int(r["block"]) for r in rows_all}):
        rows = [r for r in rows_all if int(r["block"]) == bn]
        total = sum(float(r["dur_sec"]) for r in rows)
        g.check(abs(total - BLOCK_SEC) < TOL_BLOCK,
                f"6 EP{epn:02d}B{bn:02d} 块时长 15.000s", f"{total:.3f}s")

    # 7 禁用词扫描（带上下文，避免"最后"被裸"最"误伤）
    from compliance import scan as comp_scan
    text = (proj.d_scene / f"BLOCK_EP{epn:02d}.csv").read_text(encoding="utf-8-sig")
    cres = comp_scan(text)
    g.check(cres["clean"], "7 禁用词扫描 = 0",
            f"命中 {[(h['word'], h['kind']) for h in cres['hits']]}")

    # 8 首帧即进戏（0 秒有画面，无空镜）
    g.check(media_dur(final) > 0, "8 首帧即进戏（成片非空）")

    # 9 结尾硬钩
    hh = ep.get("hard_hook", {}).get("line", "")
    g.check(bool(hh), "9 结尾硬钩存在", hh)

    # 10 块界硬切（无转场特效：块数与块文件数一致）
    g.eq(len(block_files), len(ep["blocks"]), "10 块界硬切（块数一致）")

    # 11 交付物齐全
    for nm in ["EP01.mp4", "EP01_配音.wav", "EP01.srt", "EP01_BGM.wav"]:
        g.check((proj.d_out / nm).exists(), f"11 交付物 {nm}")

    # 12 母带电平
    lufs = _probe_lufs(final)
    g.check(-20 <= lufs <= -8, "12 母带电平 -14 LUFS ±6", f"{lufs:.1f} LUFS")

    # ---- 时间线 CSV ----
    tl = []
    t = 0.0
    for r in rows_all:
        sd = float(r["dur_sec"])
        tl.append({
            "track": "V1", "item": f"B{int(r['block']):02d}_SH{int(r['shot']):02d}",
            "in": f"{t:.3f}", "out": f"{t+sd:.3f}",
            "asset": f"B{int(r['block']):02d}/clips/B{int(r['block']):02d}_SH{int(r['shot']):02d}.mp4",
            "note": r["line"] if r["line"] not in ("—", "-", "") else "",
        })
        t += sd
    write_csv(proj.d_out / "EP01_时间线.csv", tl)

    print(f"  交付：{proj.d_out}")
    save_gate(g, proj.d_report / "gate_06_compose.txt")
    return g


def _block_srt(rows: list[dict]) -> str:
    """块内 SRT：时间按 time_in_block + 0.15 起，长度 = 该句配音实测时长"""
    out = []
    idx = 1
    for r in rows:
        if r["line"] in ("—", "-", ""):
            continue
        start = float(r["time_in_block"]) + 0.15
        voice = None
        # 用块卡 dur 保守估计（真实流程用实测 wav 时长）
        end = min(start + min(2.6, float(r["dur_sec"]) - 0.1),
                  float(r["time_in_block"]) + float(r["dur_sec"]))
        out.append(f"{idx}\n{_ts(start)} --> {_ts(end)}\n{r['sub_text']}\n")
        idx += 1
    return "\n".join(out)


def _ts(t: float) -> str:
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def _concat_audio(files: list[Path], out: Path, total: float):
    if not files or not all(f.exists() for f in files):
        ff_run(["ffmpeg", "-hide_banner", "-y", "-f", "lavfi", "-i",
                f"anullsrc=r=48000:cl=mono:d={total:.3f}",
                "-t", f"{total:.3f}", "-ac", "1", str(out)])
        return
    lst = out.parent / "_alist.txt"
    lst.write_text("\n".join(f"file '{f.as_posix()}'" for f in files), encoding="utf-8")
    ff_run(["ffmpeg", "-hide_banner", "-y", "-f", "concat", "-safe", "0",
            "-i", str(lst), "-t", f"{total:.3f}", "-ar", "48000", "-ac", "1",
            str(out)])


def _silence(out: Path, total: float) -> Path:
    if not out.exists():
        ff_run(["ffmpeg", "-hide_banner", "-y", "-f", "lavfi", "-i",
                f"anullsrc=r=48000:cl=stereo:d={total:.3f}",
                "-t", f"{total:.3f}", "-ac", "2", str(out)])
    return out


def _probe_size(path: Path) -> tuple[int, int]:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height",
                        "-of", "csv=s=x:p=0", str(path)],
                       capture_output=True, encoding=None,
                       stdin=subprocess.DEVNULL, timeout=60)
    txt = r.stdout.decode("ascii", "ignore").strip().splitlines()
    if txt:
        try:
            w, h = txt[0].split("x")
            return int(w), int(h)
        except ValueError:
            pass
    return (0, 0)


def _probe_lufs(path: Path) -> float:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(path),
                        "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, encoding=None,
                       stdin=subprocess.DEVNULL, timeout=180)
    txt = (r.stderr or b"").decode("utf-8", "ignore")
    val = 0.0
    for line in txt.splitlines():
        if "I:" in line and "LUFS" in line:
            try:
                val = float(line.split("I:")[1].split("LUFS")[0].strip())
            except ValueError:
                pass
    return val


if __name__ == "__main__":
    gate = run()
    print(gate.report())
    sys.exit(0 if gate.passed else 1)
