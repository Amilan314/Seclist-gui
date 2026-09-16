#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SecLists 使用助手（Linux 版）启动入口。

用法：
    ./seclists-gui                  # 启动图形界面（同目录的 shell 启动器）
    python3 SecListsAssistant.py    # 直接运行
    python3 SecListsAssistant.py --doctor     # 只做环境自检（不需要图形界面）
    python3 SecListsAssistant.py --selftest   # 无头自检：索引/场景/预览/搜索/工具箱全链路
    python3 SecListsAssistant.py --tab 3      # 启动后直接打开某个标签页（0~4）
    python3 SecListsAssistant.py --capture DIR  # 开发用：配合 Xvfb 逐标签页截图（需 xwd）

环境变量：
    SECLISTS_ROOT       指定 SecLists 仓库根目录
    SECLISTS_GUI_DATA   指定数据目录（缓存与工具箱输出），默认 ~/.local/share/seclists-gui
    SECLISTS_GUI_SCALING   HiDPI 缩放，例如 1.5
"""

from __future__ import annotations

import os
import shutil
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

APP_NAME = "seclists-gui"

# 常见的 SecLists 仓库位置（Linux / Kali / WSL）
REPO_CANDIDATES = (
    "/usr/share/seclists",
    "/usr/local/share/seclists",
    "~/SecLists",
    "~/seclists",
    "~/tools/SecLists",
    "~/wordlists/SecLists",
    "/opt/SecLists",
    "/opt/seclists",
)


def data_dir() -> str:
    """数据目录：缓存 + 工具箱输出。默认走 XDG。"""
    env = os.environ.get("SECLISTS_GUI_DATA")
    if env:
        return os.path.abspath(os.path.expanduser(env))
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, APP_NAME)


def _looks_like_seclists(path: str) -> bool:
    return bool(path) and os.path.isdir(os.path.join(path, "Discovery")) and \
        os.path.isdir(os.path.join(path, "Passwords"))


def find_repo_root() -> str:
    """定位 SecLists 仓库根目录。"""
    env = os.environ.get("SECLISTS_ROOT")
    if env:
        cand = os.path.abspath(os.path.expanduser(env))
        if _looks_like_seclists(cand):
            return cand
    for cand in REPO_CANDIDATES:
        path = os.path.expanduser(cand)
        if _looks_like_seclists(path):
            return os.path.abspath(path)
    # 本工具放在仓库里时，上一级就是仓库根
    parent = os.path.dirname(HERE)
    if _looks_like_seclists(parent):
        return parent
    # 逐级向上找
    cur = parent
    for _ in range(5):
        if _looks_like_seclists(cur):
            return cur
        nxt = os.path.dirname(cur)
        if nxt == cur:
            break
        cur = nxt
    return parent


# --------------------------------------------------------------------- doctor
def doctor(root_dir: str, data_path: str) -> int:
    """环境自检：不需要图形界面也能跑，方便在 WSL / 服务器上排查。"""
    ok = True
    warnings: list[str] = []

    def line(name: str, value: str) -> None:
        print(f"  {name:<14}: {value}")

    print("=" * 70)
    print("SecLists 助手（Linux 版）环境自检")
    print("=" * 70)

    print("[Python 与 Tk]")
    line("Python", f"{sys.version.split()[0]}  ({sys.executable})")
    try:
        import tkinter

        tk_version = str(tkinter.TkVersion)
        try:
            import _tkinter

            tk_version += f"  (_tkinter {_tkinter.TK_VERSION})"
        except Exception:
            pass
        line("Tkinter", tk_version)
    except Exception as exc:  # noqa: BLE001
        line("Tkinter", f"✗ 不可用：{exc}")
        warnings.append("缺少 Tkinter：Debian/Ubuntu/Kali 用 sudo apt install python3-tk")
        ok = False

    print("[图形显示]")
    display = os.environ.get("DISPLAY", "")
    wayland = os.environ.get("WAYLAND_DISPLAY", "")
    line("DISPLAY", display or "（未设置）")
    line("WAYLAND_DISPLAY", wayland or "（未设置）")
    try:
        import tkinter as tk

        probe = tk.Tk()
        probe.withdraw()
        w, h = probe.winfo_screenwidth(), probe.winfo_screenheight()
        probe.destroy()
        line("Tk 窗口测试", f"✓ 正常（屏幕 {w}×{h}）")
    except Exception as exc:  # noqa: BLE001
        line("Tk 窗口测试", f"✗ 失败：{exc}")
        if not display and not wayland:
            warnings.append("没有图形显示：WSL 需要 WSLg（Windows 11 或已更新的 Windows 10），"
                            "或自建 X server 后 export DISPLAY=:0；SSH 请用 ssh -X")
        else:
            warnings.append(f"DISPLAY/WAYLAND_DISPLAY 已设置但连接失败：{exc}")
        ok = False

    print("[字体]")
    try:
        import tkinter as tk
        from tkinter import font as tkfont

        from slgui.theme import MONO_FONT_CANDIDATES, UI_FONT_CANDIDATES, has_cjk_font

        probe = tk.Tk()
        probe.withdraw()
        families = set(tkfont.families())
        ui = next((f for f in UI_FONT_CANDIDATES if f in families), "（用 Tk 默认）")
        mono = next((f for f in MONO_FONT_CANDIDATES if f in families), "（用 Tk 默认）")
        cjk = has_cjk_font(probe)
        probe.destroy()
        line("界面字体", ui)
        line("等宽字体", mono)
        line("中文字体", "✓ 有" if cjk else "✗ 没有")
        if not cjk:
            warnings.append("缺少中文字体，界面中文会显示成方框："
                            "Debian 系装 fonts-noto-cjk 或 fonts-wqy-microhei")
    except Exception as exc:  # noqa: BLE001
        line("字体检测", f"跳过（{exc}）")

    print("[仓库与数据目录]")
    line("仓库根目录", root_dir)
    if _looks_like_seclists(root_dir):
        count = 0
        for _root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
            count += len(files)
            if count > 20000:
                break
        line("文件数量", f"✓ 约 {count} 个文件")
    else:
        line("文件数量", "✗ 看起来不是 SecLists 仓库（缺少 Discovery/Passwords）")
        warnings.append("用 SECLISTS_ROOT=/path/to/SecLists 指定仓库位置")
        ok = False
    try:
        os.makedirs(data_path, exist_ok=True)
        probe_file = os.path.join(data_path, ".write-test")
        with open(probe_file, "w", encoding="utf-8") as fh:
            fh.write("ok")
        os.remove(probe_file)
        line("数据目录", f"✓ 可写 {data_path}")
    except Exception as exc:  # noqa: BLE001
        line("数据目录", f"✗ 不可写：{exc}")
        warnings.append("用 SECLISTS_GUI_DATA=/some/writable/dir 指定可写目录")
        ok = False

    print("[外部工具]")
    for tool, why in (("xdg-open", "在文件管理器中打开"), ("dbus-send", "文件管理器选中文件"),
                      ("xclip", "外部剪贴板（可选）"), ("wl-copy", "Wayland 剪贴板（可选）"),
                      ("tar", "解压 rockyou 等")):
        line(tool, ("✓ " if shutil.which(tool) else "✗ ") + why)

    print("[终端模拟器]（命令卡片「▶ 在终端运行」需要其中之一）")
    found_term = False
    for term in ("x-terminal-emulator", "gnome-terminal", "konsole", "xfce4-terminal",
                 "mate-terminal", "tilix", "kitty", "alacritty", "wezterm", "xterm"):
        hit = shutil.which(term)
        if hit:
            found_term = True
            line(term, f"✓ {hit}")
    if not found_term:
        line("终端", "✗ 未找到任何终端模拟器")
        warnings.append("装一个终端模拟器（如 xterm / gnome-terminal）才能用「▶ 在终端运行」")

    print("[环境变量]")
    for var in ("SECLISTS_ROOT", "SECLISTS_GUI_DATA", "SECLISTS_GUI_SCALING", "WSL_DISTRO_NAME",
                "XDG_SESSION_TYPE"):
        line(var, os.environ.get(var, "（未设置）"))
    if os.path.exists("/proc/version"):
        try:
            with open("/proc/version", "r", encoding="utf-8", errors="replace") as fh:
                line("内核", fh.read().strip()[:90])
        except OSError:
            pass

    print("-" * 70)
    if warnings:
        print("需要注意：")
        for item in warnings:
            print(f"  • {item}")
    print("结论：" + ("环境就绪 ✅" if ok else "环境不完整 ❌（见上方提示）"))
    print("=" * 70)
    return 0 if ok else 1


# ---------------------------------------------------------------------- main
def report_crash(exc: BaseException, gui: bool = True) -> None:
    text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    try:
        path = data_dir()
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, "error.log"), "a", encoding="utf-8") as fh:
            fh.write(text + "\n" + "-" * 60 + "\n")
    except Exception:
        path = data_dir()
    if not gui:
        print(text, file=sys.stderr)
        return
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("SecLists 助手启动失败",
                             f"{exc}\n\n详细信息已写入：\n{path}/error.log")
        root.destroy()
    except Exception:
        print(text, file=sys.stderr)


def _arg_value(flag: str, default: str = "") -> str:
    if flag in sys.argv:
        idx = sys.argv.index(flag)
        if idx + 1 < len(sys.argv):
            return sys.argv[idx + 1]
    return default


def main() -> int:
    selftest = "--selftest" in sys.argv
    root_dir = find_repo_root()
    data_path = data_dir()

    if "--doctor" in sys.argv:
        return doctor(root_dir, data_path)

    capture_dir = _arg_value("--capture", "")
    if capture_dir:
        # 开发用：配合 Xvfb 逐标签页截图（需要 xwd）
        from slgui.app import launch_capture

        return launch_capture(root_dir, data_path, os.path.abspath(os.path.expanduser(capture_dir)))

    try:
        initial_tab = int(_arg_value("--tab", "0"))
    except ValueError:
        initial_tab = 0

    try:
        from slgui.theme import enable_dpi_awareness
        from slgui.app import launch

        enable_dpi_awareness()
        return launch(root_dir, data_path, selftest=selftest, initial_tab=initial_tab)
    except BaseException as exc:  # noqa: BLE001
        report_crash(exc, gui=not selftest)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
