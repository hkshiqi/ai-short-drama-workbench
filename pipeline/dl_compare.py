# -*- coding: utf-8 -*-
"""dl_compare.py · 下载风格对照图

★ 安全约定：签名 URL 含 q-ak（访问密钥 ID），**绝不写进代码或提交到仓库**。
   正确做法：URL 写入本地 urls.local.json（已在 .gitignore 中排除），本脚本读取它。

用法：
    # 第一步：在本地建 urls.local.json（不进 git）
    # {"CINEMA_REAL.png": "https://...", "DOUYIN_HIGH.png": "https://..."}
    python pipeline/dl_compare.py [--dir 风格对照/EP01_SH02]

    # 若 urls.local.json 不存在：只提示，不报错
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
URL_FILE = ROOT / "urls.local.json"


def run(out_dir: Path) -> int:
    out_dir = Path(out_dir)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    if not URL_FILE.exists():
        print(f"[跳过] 未找到 {URL_FILE.name}。")
        print("  签名 URL 含访问密钥，不能进仓库。请在本地建该文件：")
        print('  {"CINEMA_REAL.png": "https://...", "...": "..."}')
        return 0

    try:
        items = json.loads(URL_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[错误] {URL_FILE.name} 解析失败：{e}")
        return 1

    ok = fail = skip = 0
    for name, url in items.items():
        dst = out_dir / name
        if dst.exists() and dst.stat().st_size > 100_000:
            print(f"  {name}  已存在 {dst.stat().st_size:,} bytes，跳过")
            skip += 1
            continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            dst.write_bytes(data)
            print(f"  {name}  {len(data):,} bytes  OK")
            ok += 1
        except Exception as e:
            print(f"  {name}  FAILED: {type(e).__name__}: {e}")
            fail += 1

    print(f"\n成功 {ok} / 跳过 {skip} / 失败 {fail}")
    print(f"目录：{out_dir}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="风格对照/EP01_SH02")
    a = ap.parse_args()
    sys.exit(run(a.dir))
