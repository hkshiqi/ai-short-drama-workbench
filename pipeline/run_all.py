# -*- coding: utf-8 -*-
"""run_all.py · 一键跑通全流程 + 出总报告

用法：
  python pipeline/run_all.py            # 全流程（假定 fixture 已生成）
  python pipeline/run_all.py --fresh    # 从造 fixture 开始
"""
from __future__ import annotations

import io
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import ROOT, Project

SLUG = "demo_雨夜的订单"
LOG = ROOT / "pipeline" / "_run.log"


class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, s):
        for st in self.streams:
            try:
                st.write(s)
                st.flush()
            except Exception:
                pass

    def flush(self):
        for st in self.streams:
            try:
                st.flush()
            except Exception:
                pass


def main():
    fresh = "--fresh" in sys.argv
    only = [a for a in sys.argv[1:] if a.startswith("--only=")]
    LOG.parent.mkdir(parents=True, exist_ok=True)
    logf = LOG.open("w", encoding="utf-8")
    old = sys.stdout
    sys.stdout = Tee(old, logf)

    steps: list[tuple[str, str, bool, float, str]] = []
    t_all = time.time()

    try:
        if fresh:
            import make_fixture
            t = time.time()
            make_fixture.main()
            steps.append(("0", "造 fixture", True, time.time() - t, ""))

        import step1_script
        import step2_visual
        import step3_blocks
        import step5a_audio
        import step5b_mockmedia
        import step5c_verify
        import step6_compose

        seq = [
            ("①", "剧本门禁", step1_script.run),
            ("②", "视觉圣经门禁", step2_visual.run),
            ("③④", "块卡与提示词", step3_blocks.run),
            ("⑤A", "音频先行", step5a_audio.run),
            ("⑤B", "mock 素材", lambda: step5b_mockmedia.run(force=False)),
            ("⑤C", "六道验证", lambda: step5c_verify.run()[0]),
            ("⑥", "合成与交付", step6_compose.run),
        ]
        if only:
            key = only[0].split("=", 1)[1]
            seq = [x for x in seq if key in x[0]]

        for code, name, fn in seq:
            print(f"\n{'='*68}\n[{code}] {name}\n{'='*68}")
            t = time.time()
            try:
                r = fn()
                ok = getattr(r, "passed", True)
                steps.append((code, name, ok, time.time() - t, ""))
                if hasattr(r, "report"):
                    print(r.report())
            except Exception as e:
                steps.append((code, name, False, time.time() - t,
                              f"{type(e).__name__}: {e}"))
                print(f"  [EXCEPTION] {type(e).__name__}: {e}")
                traceback.print_exc()

    finally:
        total = time.time() - t_all
        print(f"\n{'='*68}\n总耗时 {total:.1f}s\n{'='*68}")
        print(f"{'步':<4} {'名称':<16} {'结果':<6} {'耗时':>8}  说明")
        print("-" * 68)
        for code, name, ok, dt, err in steps:
            print(f"{code:<4} {name:<16} {'PASS' if ok else 'FAIL':<6} "
                  f"{dt:>7.1f}s  {err}")
        n_ok = sum(1 for s in steps if s[2])
        print("-" * 68)
        print(f"通过 {n_ok}/{len(steps)} 步")

        # 写总报告
        proj = Project(ROOT, SLUG)
        proj.ensure_dirs()
        md = ["# 全流程测试报告", "",
              f"- 项目：{SLUG}",
              f"- 总耗时：{total:.1f}s",
              f"- 通过：{n_ok}/{len(steps)} 步", "",
              "| 步 | 名称 | 结果 | 耗时 | 说明 |", "|---|---|---|---|---|"]
        for code, name, ok, dt, err in steps:
            md.append(f"| {code} | {name} | {'PASS' if ok else 'FAIL'} | "
                      f"{dt:.1f}s | {err} |")
        md += ["", "## 门禁明细", ""]
        for f in sorted(proj.d_report.glob("gate_*.txt")):
            md.append(f"### {f.stem}\n```\n{f.read_text(encoding='utf-8')}\n```\n")
        (proj.d_report / "全流程测试报告.md").write_text("\n".join(md),
                                                         encoding="utf-8")
        print(f"\n报告：{proj.d_report / '全流程测试报告.md'}")
        print(f"日志：{LOG}")

        sys.stdout = old
        logf.close()


if __name__ == "__main__":
    main()
