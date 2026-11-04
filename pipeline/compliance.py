# -*- coding: utf-8 -*-
"""compliance.py · 合规扫描（带上下文，避免子串误报）

真实教训：裸"最"字会把"最后""最初""最近"全部误伤。
禁用词必须**带上下文判定**：
  - 绝对化用语（最+形容词 / 第一 / 顶级 / 国家级 / 100% / 彻底 / 永久）
  - 疗效承诺（根治 / 祛 / 见效 / 无副作用 / 治疗）
都不允许；但"最后""最近""第一次见面"这类叙事用法完全合法。
"""
from __future__ import annotations

import re

# 绝对化用语：需要匹配"最 + 评价性形容词"这种组合，而不是裸"最"
ABS_SUPERLATIVE = [
    r"最好", r"最强", r"最美", r"最佳", r"最高级", r"最低价", r"最便宜",
    r"最先进", r"最优质", r"最安全", r"最有效", r"最专业", r"最领先",
    r"最流行", r"最受欢迎", r"销量第一", r"全国第一", r"世界第一", r"行业第一",
]
# 无条件禁用（任何上下文都不行）
ABS_ALWAYS = [
    "顶级", "国家级", "世界级", "100%", "百分百", "彻底", "永久",
    "绝无仅有", "独一无二", "史上", "唯一",
]
# 疗效/功效承诺
EFFICACY = [
    "根治", "治愈", "治好", "祛斑", "祛痘", "祛皱", "祛湿",
    "见效", "立竿见影", "一次见效", "七天见效", "无副作用", "零副作用",
    "医用级", "药效", "疗程",
]
# 白名单：出现这些词时，"最"字相关匹配应豁免（它们不是评价性用法）
NARRATIVE_WHITELIST = [
    "最后", "最初", "最近", "最终", "最大声", "最后一次", "最早的",
]


def scan(text: str) -> dict:
    """返回 {hits: [{word, kind, context}], clean: bool}"""
    hits = []

    # 1) 白名单先行遮蔽（把叙事用法的"最X"从文本里挖掉，避免误伤）
    masked = text
    for w in NARRATIVE_WHITELIST:
        masked = masked.replace(w, "＊" * len(w))

    # 2) 绝对化最高级（正则）
    for pat in ABS_SUPERLATIVE:
        for m in re.finditer(pat, masked):
            hits.append({"word": m.group(0), "kind": "绝对化用语",
                         "context": _ctx(masked, m.start(), m.end())})

    # 3) 无条件禁用
    for w in ABS_ALWAYS:
        for m in re.finditer(re.escape(w), masked):
            hits.append({"word": w, "kind": "绝对化用语",
                         "context": _ctx(masked, m.start(), m.end())})

    # 4) 疗效承诺
    for w in EFFICACY:
        for m in re.finditer(re.escape(w), masked):
            hits.append({"word": w, "kind": "疗效承诺",
                         "context": _ctx(masked, m.start(), m.end())})

    return {"hits": hits, "clean": not hits}


def _ctx(s: str, a: int, b: int, pad: int = 12) -> str:
    lo, hi = max(0, a - pad), min(len(s), b + pad)
    return s[lo:hi].replace("\n", " ")


def scan_file(path) -> dict:
    from pathlib import Path
    p = Path(path)
    if not p.exists():
        return {"hits": [], "clean": True}
    return scan(p.read_text(encoding="utf-8-sig"))
