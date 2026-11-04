# -*- coding: utf-8 -*-
"""probe_color.py · 调试取色（验证器为什么读不到角色色相）"""
import subprocess
import sys
from pathlib import Path

p = Path(sys.argv[1])
print("file:", p, "exists:", p.exists())

for f in ["null",
          "crop=iw*0.5:ih*0.06:iw*0.25:ih*0.02",
          "crop=iw:ih*0.08:0:0",
          "crop=iw*0.5:ih*0.5:iw*0.25:ih*0.25"]:
    r = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-i", str(p), "-vf",
         f"{f},scale=1:1,format=rgb24", "-f", "rawvideo", "-"],
        capture_output=True, encoding=None)
    out = r.stdout
    print(f"  {f:45s} bytes={len(out) if isinstance(out,(bytes,bytearray)) else 'N/A'} "
          f"rgb={tuple(out[:3]) if isinstance(out,(bytes,bytearray)) and len(out)>=3 else None} "
          f"err={(r.stderr or b'')[:100]}")
