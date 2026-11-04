# -*- coding: utf-8 -*-
"""probe2.py · 定位 mediautil.dur 在中文路径下的行为"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mediautil import dur, _run_bytes

p = Path(sys.argv[1])
print("exists:", p.exists())
rc, out, err = _run_bytes(["ffprobe", "-nostdin", "-v", "error",
                           "-show_entries", "format=duration",
                           "-of", "default=nw=1:nk=1", str(p)])
print("rc:", rc)
print("stdout repr:", repr(out[:80]))
print("ascii:", out.decode("ascii", "ignore").strip())
print("stderr repr:", repr(err[:200]))
print("dur():", dur(p))
