# -*- coding: utf-8 -*-
"""配色、字体与 ttk 主题（Linux 版）。

与 Windows 版的区别：
  * 字体按 Linux 发行版常见字体族挑选（含中文字体与等宽字体）
  * 不支持 ctypes 设置 DPI 感知，改为按需调整 Tk 缩放（环境变量 SECLISTS_GUI_SCALING）
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

COLORS = {
    "bg": "#15171c",
    "panel": "#1c1f26",
    "panel2": "#23272f",
    "panel3": "#2b303a",
    "border": "#333a45",
    "fg": "#e7eaf0",
    "fg_dim": "#aab3c0",
    "muted": "#7f8a99",
    "accent": "#4f9dff",
    "accent_dark": "#2b6fd0",
    "ok": "#3ddc97",
    "warn": "#ffb454",
    "danger": "#ff6b6b",
    "code_bg": "#101218",
    "code_fg": "#d7dce5",
    "sel": "#2f4f7a",
    "stripe": "#1f232b",
}

# 默认值会在 apply_theme() 里按本机实际字体替换
FONT_UI = ("Noto Sans CJK SC", 10)
FONT_UI_SM = ("Noto Sans CJK SC", 9)
FONT_UI_B = ("Noto Sans CJK SC", 10, "bold")
FONT_H1 = ("Noto Sans CJK SC", 15, "bold")
FONT_H2 = ("Noto Sans CJK SC", 12, "bold")
FONT_MONO = ("DejaVu Sans Mono", 10)
FONT_MONO_SM = ("DejaVu Sans Mono", 9)

# 界面字体：优先能显示中文的（否则中文会变成方框）
UI_FONT_CANDIDATES = (
    "Noto Sans CJK SC", "Source Han Sans SC", "Source Han Sans CN", "Noto Sans SC",
    "WenQuanYi Micro Hei", "WenQuanYi Zen Hei", "Droid Sans Fallback", "AR PL UMing CN",
    "Sarasa Gothic SC", "Ubuntu", "Cantarell", "Noto Sans", "DejaVu Sans",
    "Liberation Sans", "FreeSans",
)
CJK_FONT_CANDIDATES = (
    "Noto Sans CJK SC", "Source Han Sans SC", "Source Han Sans CN", "Noto Sans SC",
    "WenQuanYi Micro Hei", "WenQuanYi Zen Hei", "Droid Sans Fallback", "AR PL UMing CN",
    "Sarasa Gothic SC", "Noto Serif CJK SC",
)
MONO_FONT_CANDIDATES = (
    "DejaVu Sans Mono", "Noto Sans Mono CJK SC", "Noto Sans Mono", "Source Code Pro",
    "Ubuntu Mono", "Liberation Mono", "FreeMono", "Courier New", "monospace",
)


def _pick_fonts() -> None:
    """挑本机存在的界面字体与等宽字体（各发行版字体差异很大）。"""
    global FONT_UI, FONT_UI_SM, FONT_UI_B, FONT_H1, FONT_H2, FONT_MONO, FONT_MONO_SM
    try:
        available = set(tkfont.families())
    except Exception:
        return
    for family in UI_FONT_CANDIDATES:
        if family in available:
            FONT_UI = (family, 10)
            FONT_UI_SM = (family, 9)
            FONT_UI_B = (family, 10, "bold")
            FONT_H1 = (family, 15, "bold")
            FONT_H2 = (family, 12, "bold")
            break
    for family in MONO_FONT_CANDIDATES:
        if family in available:
            FONT_MONO = (family, 10)
            FONT_MONO_SM = (family, 9)
            break


def has_cjk_font(root: tk.Misc | None = None) -> bool:
    """本机是否有中文字体（没有的话界面中文会显示成方框）。"""
    try:
        available = set(tkfont.families(root))
    except Exception:
        return False
    return any(f in available for f in CJK_FONT_CANDIDATES)


def enable_dpi_awareness() -> None:
    """Linux 下无需设置进程 DPI 感知；缩放由桌面环境负责。

    如果显示器是 HiDPI 而字太小，可以设置环境变量：
        export SECLISTS_GUI_SCALING=1.5
    """
    return None


FONT_NAMES = ("FONT_UI", "FONT_UI_SM", "FONT_UI_B", "FONT_H1", "FONT_H2",
              "FONT_MONO", "FONT_MONO_SM")


def sync_fonts(namespace: dict) -> None:
    """把 apply_theme() 检测到的字体写回调用方模块的全局变量。

    `from .theme import FONT_UI_SM` 拿到的是导入时的副本，apply_theme 之后并不会更新，
    于是显式写了 font=FONT_UI_SM 的控件仍然用着默认字体族。在字体与默认值不一致的
    Linux 发行版上，那会退回 Tk 默认字体（可能连汉字都没有）。建控件前同步一次即可。
    """
    for name in FONT_NAMES:
        if name in globals():
            namespace[name] = globals()[name]


def human_size(num: int) -> str:
    num = float(num or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num < 1024 or unit == "TB":
            return f"{int(num)} B" if unit == "B" else f"{num:.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} TB"


def apply_theme(root: tk.Misc) -> ttk.Style:
    """配置整体深色主题，返回 style 对象。"""
    _pick_fonts()
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    scaling = os.environ.get("SECLISTS_GUI_SCALING", "").strip()
    if scaling:
        try:
            root.tk.call("tk", "scaling", float(scaling))
        except Exception:
            pass

    root.configure(background=COLORS["bg"])
    root.option_add("*Font", FONT_UI)
    root.option_add("*TearOff", False)

    style.configure(".", background=COLORS["bg"], foreground=COLORS["fg"],
                    fieldbackground=COLORS["panel2"], bordercolor=COLORS["border"],
                    lightcolor=COLORS["panel3"], darkcolor=COLORS["bg"],
                    focuscolor=COLORS["accent"], font=FONT_UI)

    style.configure("TFrame", background=COLORS["bg"])
    style.configure("Panel.TFrame", background=COLORS["panel"])
    style.configure("Card.TFrame", background=COLORS["panel2"], relief="flat")
    style.configure("Header.TFrame", background=COLORS["panel"])

    style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["fg"])
    style.configure("Panel.TLabel", background=COLORS["panel"], foreground=COLORS["fg"])
    style.configure("Card.TLabel", background=COLORS["panel2"], foreground=COLORS["fg"])
    style.configure("Dim.TLabel", background=COLORS["bg"], foreground=COLORS["fg_dim"])
    style.configure("CardDim.TLabel", background=COLORS["panel2"], foreground=COLORS["muted"])
    style.configure("Muted.TLabel", background=COLORS["bg"], foreground=COLORS["muted"])
    style.configure("H1.TLabel", background=COLORS["panel"], foreground=COLORS["fg"], font=FONT_H1)
    style.configure("H2.TLabel", background=COLORS["bg"], foreground=COLORS["fg"], font=FONT_H2)
    style.configure("CardH2.TLabel", background=COLORS["panel2"], foreground=COLORS["fg"], font=FONT_H2)
    style.configure("Accent.TLabel", background=COLORS["bg"], foreground=COLORS["accent"], font=FONT_UI_B)
    style.configure("Ok.TLabel", background=COLORS["bg"], foreground=COLORS["ok"])
    style.configure("Warn.TLabel", background=COLORS["bg"], foreground=COLORS["warn"])
    style.configure("Danger.TLabel", background=COLORS["bg"], foreground=COLORS["danger"])
    style.configure("Code.TLabel", background=COLORS["code_bg"], foreground=COLORS["code_fg"], font=FONT_MONO)

    style.configure("TButton", background=COLORS["panel3"], foreground=COLORS["fg"],
                    bordercolor=COLORS["border"], padding=(10, 4), relief="flat")
    style.map("TButton",
              background=[("active", COLORS["accent_dark"]), ("pressed", COLORS["accent"]),
                          ("disabled", COLORS["panel2"])],
              foreground=[("disabled", COLORS["muted"])])
    style.configure("Accent.TButton", background=COLORS["accent_dark"], foreground="#ffffff",
                    padding=(12, 5))
    style.map("Accent.TButton",
              background=[("active", COLORS["accent"]), ("pressed", COLORS["accent_dark"])])
    style.configure("Tiny.TButton", padding=(6, 2), font=FONT_UI_SM)
    style.configure("Link.TButton", padding=(2, 0), font=FONT_UI_SM,
                    background=COLORS["panel2"], foreground=COLORS["accent"])

    style.configure("TEntry", fieldbackground=COLORS["panel2"], foreground=COLORS["fg"],
                    insertcolor=COLORS["fg"], bordercolor=COLORS["border"], padding=4)
    style.map("TEntry", fieldbackground=[("disabled", COLORS["panel"])])
    style.configure("TCombobox", fieldbackground=COLORS["panel2"], background=COLORS["panel3"],
                    foreground=COLORS["fg"], arrowcolor=COLORS["fg"], padding=3)
    style.map("TCombobox", fieldbackground=[("readonly", COLORS["panel2"])],
              foreground=[("readonly", COLORS["fg"])])
    root.option_add("*TCombobox*Listbox.background", COLORS["panel2"])
    root.option_add("*TCombobox*Listbox.foreground", COLORS["fg"])
    root.option_add("*TCombobox*Listbox.selectBackground", COLORS["sel"])

    style.configure("TCheckbutton", background=COLORS["bg"], foreground=COLORS["fg"])
    style.map("TCheckbutton", background=[("active", COLORS["bg"])])
    style.configure("Card.TCheckbutton", background=COLORS["panel2"], foreground=COLORS["fg"])
    style.map("Card.TCheckbutton", background=[("active", COLORS["panel2"])])
    style.configure("TRadiobutton", background=COLORS["bg"], foreground=COLORS["fg"])
    style.map("TRadiobutton", background=[("active", COLORS["bg"])])

    style.configure("Treeview", background=COLORS["panel"], fieldbackground=COLORS["panel"],
                    foreground=COLORS["fg"], bordercolor=COLORS["border"], rowheight=22)
    style.map("Treeview", background=[("selected", COLORS["sel"])],
              foreground=[("selected", "#ffffff")])
    style.configure("Treeview.Heading", background=COLORS["panel3"], foreground=COLORS["fg_dim"],
                    relief="flat", padding=(6, 4))
    style.map("Treeview.Heading", background=[("active", COLORS["panel3"])])

    style.configure("TNotebook", background=COLORS["bg"], bordercolor=COLORS["border"], tabmargins=(6, 4, 6, 0))
    style.configure("TNotebook.Tab", background=COLORS["panel"], foreground=COLORS["fg_dim"],
                    padding=(16, 7), bordercolor=COLORS["border"])
    style.map("TNotebook.Tab",
              background=[("selected", COLORS["panel3"]), ("active", COLORS["panel2"])],
              foreground=[("selected", COLORS["fg"])],
              expand=[("selected", (0, 0, 0, 0))])

    style.configure("TLabelframe", background=COLORS["bg"], bordercolor=COLORS["border"],
                    foreground=COLORS["fg_dim"], relief="solid", borderwidth=1)
    style.configure("TLabelframe.Label", background=COLORS["bg"], foreground=COLORS["accent"], font=FONT_UI_B)

    style.configure("Horizontal.TProgressbar", background=COLORS["accent"],
                    troughcolor=COLORS["panel2"], bordercolor=COLORS["panel2"],
                    lightcolor=COLORS["accent"], darkcolor=COLORS["accent"])
    style.configure("Vertical.TScrollbar", background=COLORS["panel3"], troughcolor=COLORS["bg"],
                    bordercolor=COLORS["bg"], arrowcolor=COLORS["fg_dim"])
    style.configure("Horizontal.TScrollbar", background=COLORS["panel3"], troughcolor=COLORS["bg"],
                    bordercolor=COLORS["bg"], arrowcolor=COLORS["fg_dim"])
    style.configure("TSeparator", background=COLORS["border"])
    style.configure("TPanedwindow", background=COLORS["bg"])

    return style
