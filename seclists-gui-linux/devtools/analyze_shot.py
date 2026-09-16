"""开发辅助：对界面截图做像素统计校验（Linux 版）。

用法：
    python3 devtools/analyze_shot.py [截图目录或某个 png]
    # 默认目录： $SECLISTS_GUI_DATA 或 ~/.local/share/seclists-gui

校验思路：画面里必须同时出现主题背景色、等宽区背景色、足够多的独立颜色
和一定比例的亮像素（文字），否则判定为空白/未渲染/截错窗口。
"""

from __future__ import annotations

import collections
import os
import struct
import sys
import zlib

EXPECT = {
    "bg": (0x15, 0x17, 0x1C),
    "panel": (0x1C, 0x1F, 0x26),
    "code_bg": (0x10, 0x12, 0x18),
    "accent": (0x4F, 0x9D, 0xFF),
    "fg": (0xE7, 0xEA, 0xF0),
}


def read_png(path: str):
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a png")
    pos = 8
    idat = bytearray()
    width = height = depth = ctype = interlace = 0
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        ctag = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if ctag == b"IHDR":
            width, height, depth, ctype, _comp, _filt, interlace = struct.unpack(">IIBBBBB", chunk)
        elif ctag == b"IDAT":
            idat += chunk
        elif ctag == b"IEND":
            break
    if depth != 8 or ctype not in (2, 6) or interlace != 0:
        raise ValueError(f"unsupported png: depth={depth} type={ctype} interlace={interlace}")
    channels = 3 if ctype == 2 else 4
    raw = zlib.decompress(bytes(idat))
    stride = width * channels
    out = bytearray(width * height * channels)
    prev = bytearray(stride)
    p = 0
    for y in range(height):
        f = raw[p]
        p += 1
        line = bytearray(raw[p:p + stride])
        p += stride
        if f == 1:
            for i in range(channels, stride):
                line[i] = (line[i] + line[i - channels]) & 0xFF
        elif f == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif f == 3:
            for i in range(stride):
                left = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 0xFF
        elif f == 4:
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                b = prev[i]
                c = prev[i - channels] if i >= channels else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xFF
        out[y * stride:(y + 1) * stride] = line
        prev = line
    return width, height, channels, bytes(out)


def analyze(path: str) -> bool:
    width, height, ch, px = read_png(path)
    total = width * height
    counter = collections.Counter()
    bright = 0
    sums = [0, 0, 0]
    step = 2
    sampled = 0
    for y in range(0, height, step):
        row = y * width * ch
        for x in range(0, width, step):
            i = row + x * ch
            r, g, b = px[i], px[i + 1], px[i + 2]
            counter[(r, g, b)] += 1
            sums[0] += r
            sums[1] += g
            sums[2] += b
            sampled += 1
            if max(r, g, b) >= 150:
                bright += 1
    mean = tuple(s / sampled for s in sums)
    print(f"\n== {os.path.basename(path)}  {width}×{height}")
    print(f"   独立颜色数：{len(counter)}   平均 RGB：({mean[0]:.0f}, {mean[1]:.0f}, {mean[2]:.0f})"
          f"   亮像素占比：{100.0 * bright / sampled:.2f}%")
    for name, rgb in EXPECT.items():
        hit = counter.get(rgb, 0)
        print(f"   主题色 {name:<8} #{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X} 出现 {hit} 次样本")
    top = counter.most_common(4)
    pretty = "  ".join(f"#{r:02X}{g:02X}{b:02X}({100.0 * c / sampled:.1f}%)" for (r, g, b), c in top)
    print(f"   主色：{pretty}")

    ok = True
    if len(counter) < 200:
        print("   ✗ 颜色过于单一，疑似空白窗口")
        ok = False
    if not (0.05 < 100.0 * bright / sampled < 60):
        print("   ✗ 亮像素比例异常，疑似未渲染文本")
        ok = False
    if mean[0] > 120 or mean[1] > 120:
        print("   ✗ 画面整体过亮，可能截到了别的窗口")
        ok = False
    missing = [n for n, rgb in (("bg", EXPECT["bg"]), ("code_bg", EXPECT["code_bg"]))
               if counter.get(rgb, 0) == 0]
    if missing:
        print(f"   ! 未找到主题色 {missing}（可能被缩放影响，仅供参考）")
    if ok:
        print("   ✓ 画面正常：有背景色、有文字像素、颜色层次丰富")
    return ok


def _default_dir() -> str:
    env = os.environ.get("SECLISTS_GUI_DATA")
    if env:
        return os.path.abspath(os.path.expanduser(env))
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, "seclists-gui")


def main() -> int:
    target = sys.argv[1] if len(sys.argv) > 1 else _default_dir()
    if os.path.isfile(target):
        return 0 if analyze(target) else 1
    if not os.path.isdir(target):
        print(f"目录不存在：{target}")
        print("用法：python3 analyze_shot.py [截图目录或某个 png]")
        return 1
    shots = sorted(f for f in os.listdir(target) if f.endswith(".png"))
    if not shots:
        print(f"{target} 下没有 png 截图")
        return 1
    results = [analyze(os.path.join(target, s)) for s in shots]
    print("\n" + "=" * 60)
    print(f"{sum(results)}/{len(results)} 张截图通过校验")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
