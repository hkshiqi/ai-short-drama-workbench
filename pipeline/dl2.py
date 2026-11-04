# -*- coding: utf-8 -*-
"""dl2.py · 从本地 urls.local.json 下载风格对照图

urls.local.json 格式：
{
  "A/CINEMA_REAL.png": "https://...",
  "B/ROMANCE_SOFT.png": "https://..."
}
"""
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(r"E:\dsh\AI短剧_对照图\round2")
URL_FILE = ROOT / "urls.local.json"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if not URL_FILE.exists():
        print(f"未找到 {URL_FILE}")
        return 1
    items = json.loads(URL_FILE.read_text(encoding="utf-8"))
    ok = fail = 0
    for name, url in items.items():
        dst = OUT / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() and dst.stat().st_size > 100_000:
            print(f"  {name}  已存在，跳过")
            continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=180) as r:
                data = r.read()
            dst.write_bytes(data)
            print(f"  {name}  {len(data):,} bytes  OK")
            ok += 1
        except Exception as e:
            print(f"  {name}  FAILED: {type(e).__name__}: {e}")
            fail += 1
    print(f"\n成功 {ok} / 失败 {fail}")
    print(f"目录：{OUT}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
