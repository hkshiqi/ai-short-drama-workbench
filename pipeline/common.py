# -*- coding: utf-8 -*-
"""common.py · 工作台公共层：常量 / 时间网格 / CSV / 日志 / 断言

所有模块只依赖这里，保证"唯一真值"只有一个地方定义。
"""
from __future__ import annotations

import csv
import json
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

# ============================================================
# 一、全剧唯一的节拍真值（改这里 = 全剧时间轴重建）
# ============================================================
BPM = 128
BEAT_SEC = 60.0 / BPM            # 0.46875
BAR_SEC = 4 * BEAT_SEC           # 1.875   (4/4)
BARS_PER_BLOCK = 8
BLOCK_SEC = BARS_PER_BLOCK * BAR_SEC   # 15.000

# 合法单镜时长（必须落在节拍网格上）
LEGAL_SHOT_SEC = (1 * BAR_SEC, 2 * BAR_SEC, 3 * BAR_SEC)   # 1.875 / 3.750 / 5.625

# 一块内的镜数范围
MIN_SHOTS_PER_BLOCK = 4
MAX_SHOTS_PER_BLOCK = 6

# 容差
TOL_SHOT = 0.08
TOL_BLOCK = 0.05
TOL_CUE = 0.05
TOL_LIPSYNC = 0.15

# 编码表
SHOT_SIZES = ("ECU", "CU", "MS", "MFS", "FS", "ELS")
CAMERAS = ("EYE", "LOW", "HIGH", "OTS", "PROFILE", "BCK", "POV", "DUTCH")
MOVES_OK = ("STATIC", "PUSH_S", "PULL_S", "PAN_S", "TILT_S", "TRACK_S", "HANDHELD_L", "RACK")
MOVES_BANNED = ("CRASH_ZOOM", "WHIP_PAN", "ORBIT", "CRANE", "ZOOM", "ONER", "PASS_THRU")
EXPR_BASES = ("ANGER", "GRIEF", "SHOCK", "CONTEMPT", "RESOLVE", "TENDER")
EXPR_CODES = tuple(f"EXP_{b}_{i}" for b in EXPR_BASES for i in ("L", "M", "H"))
MODEL_TAGS = ("HERO", "FACE", "REACT", "HAND", "PROD", "ENV", "CROWD")
MODEL_TAG_TRIES = {
    "HERO": (6, 6), "FACE": (4, 3), "REACT": (3, 2), "HAND": (3, 2),
    "PROD": (4, 3), "ENV": (2, 2), "CROWD": (3, 2),
}
BGM_LAYERS = ("PAD", "LOOP", "STRINGS", "HIT")

# 画质后缀（全剧统一，一行不改）
QUALITY_SUFFIX_CN = "电影感, 35mm胶片质感, 浅景深, 高细节皮肤纹理, 自然光, 8k, 竖构图9:16"
NEGATIVE_DEFAULT = (
    "变形, 多余手指, 脸部扭曲, 五官漂移, 双人融合, 文字水印, 字幕, logo, "
    "塑料感皮肤, 过曝, 模糊, 低分辨率, 动漫风, 3D渲染, 卡通"
)


def dedupe_csv(csv_text: str) -> str:
    """去重逗号/中文逗号分隔的词条，保持首次出现顺序"""
    import re as _re
    parts = [p.strip() for p in _re.split(r"[,，]", csv_text) if p.strip()]
    seen, out = set(), []
    for p in parts:
        key = p.lower().replace(" ", "")
        if key not in seen:
            seen.add(key)
            out.append(p)
    return ", ".join(out)
# 视频提示词禁止情绪变化动词
FORBIDDEN_IN_VIDEO = ("变成", "转为", "逐渐", "慢慢变", "笑了", "哭了", "越来越", "流下泪", "流泪")
# 黑名单运镜的中文表现（写进提示词就算违规）
FORBIDDEN_MOVE_WORDS = ("环绕", "摇臂", "甩镜", "急推", "变焦", "一镜到底", "升镜", "降镜", "360")

ROOT = Path(__file__).resolve().parent.parent


# ============================================================
# 二、路径
# ============================================================
@dataclass
class Project:
    root: Path
    slug: str

    def p(self, *parts: str) -> Path:
        return self.root.joinpath(*parts)

    @property
    def d_input(self):  return self.p("00_输入包", self.slug)
    @property
    def d_script(self): return self.p("01_剧本", self.slug)
    @property
    def d_char(self):   return self.p("02_角色", self.slug)
    @property
    def d_scene(self):  return self.p("04_场景分镜", self.slug)
    @property
    def d_frames(self): return self.p("10_首尾帧", self.slug)
    @property
    def d_blocks(self): return self.p("06_资产", "blocks", self.slug)
    @property
    def d_out(self):    return self.p("05_成片", self.slug)
    @property
    def d_report(self): return self.p("08_测试报告", self.slug)

    def ensure_dirs(self):
        for d in (self.d_input, self.d_script, self.d_char, self.d_scene,
                  self.d_frames, self.d_blocks, self.d_out, self.d_report):
            d.mkdir(parents=True, exist_ok=True)


# ============================================================
# 三、时间网格工具
# ============================================================
def bars_to_sec(bars: float) -> float:
    return round(bars * BAR_SEC, 4)


def sec_to_bars(sec: float) -> int:
    """向上取整到整小节数（音频吸网格的唯一函数）"""
    import math
    return max(1, math.ceil(sec / BAR_SEC - 1e-6))


def snap_sec(sec: float) -> tuple[int, float]:
    bars = sec_to_bars(sec)
    return bars, bars_to_sec(bars)


def bar_time(bar_index_1based: int) -> float:
    """第 n 小节（1-based）的绝对起始秒"""
    return round((bar_index_1based - 1) * BAR_SEC, 4)


def is_on_grid(sec: float, tol: float = TOL_SHOT) -> bool:
    return any(abs(sec - g) < tol for g in LEGAL_SHOT_SEC)


# ============================================================
# 四、CSV / JSON 读写（统一 UTF-8-BOM，Excel 直开不乱码）
# ============================================================
def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None):
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    fieldnames = fieldnames or list(rows[0].keys())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


# ============================================================
# 五、校验框架（门禁的唯一表达方式）
# ============================================================
class Gate:
    """一个门禁 = 一组检查。全绿才允许进下一步。"""

    def __init__(self, name: str):
        self.name = name
        self.items: list[dict] = []

    def check(self, ok: bool, item: str, detail: str = "", fatal: bool = True):
        self.items.append({"ok": bool(ok), "item": item, "detail": detail, "fatal": fatal})
        return ok

    def eq(self, a, b, item: str, fatal: bool = True):
        return self.check(a == b, item, f"期望 {b!r} 实际 {a!r}", fatal)

    def in_(self, v, allowed, item: str, fatal: bool = True):
        return self.check(v in allowed, item, f"{v!r} 不在 {allowed}", fatal)

    def num(self, v, lo, hi, item: str, fatal: bool = True):
        return self.check(lo <= v <= hi, item, f"{v} 不在 [{lo},{hi}]", fatal)

    @property
    def passed(self) -> bool:
        return all(i["ok"] for i in self.items if i["fatal"])

    @property
    def fails(self) -> list[dict]:
        return [i for i in self.items if not i["ok"]]

    def report(self, verbose: bool = False) -> str:
        n = len(self.items)
        nfail = len(self.fails)
        head = f"{'PASS' if self.passed else 'FAIL'} · {self.name}  ({n} 项 / 失败 {nfail})"
        lines = [head]
        # 失败项永远列出
        for i in self.fails:
            lines.append(f"  [X] {i['item']}" + (f" — {i['detail']}" if i["detail"] else ""))
        # 通过项只在 verbose 时列出，且压缩为一行摘要
        if verbose and self.passed:
            lines.append(f"  all ok: {', '.join(i['item'] for i in self.items[:3])} …")
        return "\n".join(lines)


def save_gate(gate: Gate, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(gate.report(verbose=False), encoding="utf-8")


# ============================================================
# 六、拼音/中文拼音化留给文件名用
# ============================================================
def safe_name(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    keep = []
    for ch in s:
        if ch.isalnum() or ch in "-_":
            keep.append(ch)
    return "".join(keep) or "x"


def hr(title: str = ""):
    print("\n" + "=" * 68)
    if title:
        print(title)
        print("=" * 68)


def log(step: str, msg: str):
    print(f"[{step}] {msg}")
