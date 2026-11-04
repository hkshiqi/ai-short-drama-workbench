# -*- coding: utf-8 -*-
"""test_era.py · 验证年代匹配门禁（负样本回归）

原则：门禁必须能真的抓到错配，否则等于没做。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stylelib import era_compatible, scene_era, STYLE_ERA

CASES = [
    # (style, scene, 期望兼容)
    ("ANCIENT_CN", "SCN_ALLEY_NIGHT", False),      # 古装配现代 → 必须拒
    ("ANCIENT_CN", "SCN_ANCIENT_PALACE", True),    # 古装配古装 → 通过
    ("INK_WASH", "SCN_ALLEY_NIGHT", False),
    ("CYBERPUNK", "SCN_ALLEY_NIGHT", False),       # 未来配现代 → 必须拒
    ("CYBERPUNK", "SCN_FUTURE_STREET", True),
    ("RETRO_90S_CN", "SCN_ANCIENT_TEMPLE", False),
    ("RETRO_90S_CN", "SCN_ALLEY_NIGHT", True),
    ("CINEMA_REAL", "SCN_ALLEY_NIGHT", True),      # 通用风格任何场景都行
    ("DOUYIN_HIGH", "SCN_FUTURE_LAB", True),
    ("FILM_16MM", "SCN_ALLEY_NIGHT", True),        # 任意年代
]

out = []
fail = 0
for sty, scn, want in CASES:
    got, msg = era_compatible(sty, scn)
    ok = (got == want)
    if not ok:
        fail += 1
    out.append(f"{'PASS' if ok else 'FAIL'}  期望{want!s:<5} 实际{got!s:<5}  "
               f"{sty:<14} × {scn:<22}  场景年代={scene_era(scn)}")
    out.append(f"        {msg}")

out.append("")
out.append(f"共 {len(CASES)} 例，失败 {fail}")
Path("_era_test.txt").write_text("\n".join(out), encoding="utf-8")
print(f"共 {len(CASES)} 例，失败 {fail}")
