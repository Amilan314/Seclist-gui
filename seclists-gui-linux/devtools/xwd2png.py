#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 Xvfb 下用 xwd 抓到的 XWD 截图转成 PNG（纯标准库，不需要 PIL/ImageMagick）。

用法： python3 xwd2png.py 目录或文件 [...]
"""

from __future__ import annotations

import os
import struct
import sys
import zlib


def _chunk(tag: bytes, data: bytes) -> bytes:
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def write_png(path: str, width: int, height: int, rows: list[bytes]) -> None:
    raw = b"".join(b"\x00" + row for row in rows)  # 每行 filter=0
    png = (b"\x89PNG\r\n\x1a\n"
           + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
           + _chunk(b"IDAT", zlib.compress(raw, 6))
           + _chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(png)


def convert(xwd_path: str) -> str:
    with open(xwd_path, "rb") as fh:
        blob = fh.read()
    header = struct.unpack(">25I", blob[:100])
    (header_size, _version, pixmap_format, depth, width, height, _xoff, byte_order,
     _bmp_unit, _bmp_bit_order, _bmp_pad, bits_per_pixel, bytes_per_line, _visual_class,
     red_mask, green_mask, blue_mask, _bits_per_rgb, _cmap_entries, ncolors,
     _win_w, _win_h, _win_x, _win_y, _bdr) = header
    if pixmap_format != 2:
        raise ValueError(f"只支持 ZPixmap（当前 {pixmap_format}）")
    ncolors = ncolors if ncolors != 0 else (1 << depth)
    data_off = header_size + ncolors * 12
    nbytes = bytes_per_line * height
    pixels = blob[data_off:data_off + nbytes]
    if len(pixels) < nbytes:
        raise ValueError("XWD 数据不完整")

    bpp_bytes = bits_per_pixel // 8
    msb = byte_order == 1

    def shift_of(mask: int) -> tuple[int, int]:
        if mask == 0:
            return 0, 8
        shift = (mask & -mask).bit_length() - 1
        bits = bin(mask >> shift).count("1")
        return shift, bits

    rs, rb = shift_of(red_mask)
    gs, gb = shift_of(green_mask)
    bs, bb = shift_of(blue_mask)

    def scale(value: int, bits: int) -> int:
        if bits >= 8:
            return value & 0xFF
        return int(value * 255 / max((1 << bits) - 1, 1))

    rows: list[bytes] = []
    for y in range(height):
        base = y * bytes_per_line
        row = bytearray()
        for x in range(width):
            off = base + x * bpp_bytes
            chunk = pixels[off:off + bpp_bytes]
            value = int.from_bytes(chunk, "big" if msb else "little")
            r = scale((value & red_mask) >> rs, rb) if red_mask else 0
            g = scale((value & green_mask) >> gs, gb) if green_mask else 0
            b = scale((value & blue_mask) >> bs, bb) if blue_mask else 0
            row += bytes((r, g, b))
        rows.append(bytes(row))
    out = os.path.splitext(xwd_path)[0] + ".png"
    write_png(out, width, height, rows)
    return out


def main() -> int:
    targets: list[str] = []
    for arg in sys.argv[1:] or ["."]:
        if os.path.isdir(arg):
            targets += [os.path.join(arg, f) for f in sorted(os.listdir(arg))
                        if f.endswith(".xwd")]
        else:
            targets.append(arg)
    if not targets:
        print("没有找到 .xwd 文件")
        return 1
    failed = 0
    for path in targets:
        try:
            out = convert(path)
            print(f"  {os.path.basename(path)} -> {out}  ({os.path.getsize(out) / 1024:.0f} KB)")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"  ✗ {os.path.basename(path)}: {exc}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
