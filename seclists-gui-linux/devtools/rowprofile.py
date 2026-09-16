# -*- coding: utf-8 -*-
"""开发辅助：输出一张截图自上而下的主色带，用来判断界面各部分落在哪一行。

用法： python3 devtools/rowprofile.py <png> [每带像素行数]
"""

from __future__ import annotations

import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_shot import EXPECT, read_png  # noqa: E402

NAMES = {v: k for k, v in EXPECT.items()}


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    path = sys.argv[1]
    band = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    width, height, ch, px = read_png(path)
    print(f"{os.path.basename(path)}  {width}x{height}  每 {band} 行一带")
    for y0 in range(0, height, band):
        counter = collections.Counter()
        for y in range(y0, min(y0 + band, height)):
            row = y * width * ch
            for x in range(0, width, 3):
                i = row + x * ch
                counter[(px[i], px[i + 1], px[i + 2])] += 1
        total = sum(counter.values()) or 1
        top = counter.most_common(3)
        desc = "  ".join(
            f"#{r:02X}{g:02X}{b:02X}{'(' + NAMES[(r, g, b)] + ')' if (r, g, b) in NAMES else ''}"
            f" {100.0 * c / total:.0f}%" for (r, g, b), c in top)
        print(f"  y={y0:>4}-{min(y0 + band, height):<4} {desc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
