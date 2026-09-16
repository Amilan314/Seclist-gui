# -*- coding: utf-8 -*-
"""配色、字体与 ttk 主题。"""

from __future__ import annotations

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

FONT_UI = ("Microsoft YaHei UI", 10)
FONT_UI_SM = ("Microsoft YaHei UI", 9)
FONT_UI_B = ("Microsoft YaHei UI", 10, "bold")
FONT_H1 = ("Microsoft YaHei UI", 15, "bold")
FONT_H2 = ("Microsoft YaHei UI", 12, "bold")
FONT_MONO = ("Consolas", 10)
FONT_MONO_SM = ("Consolas", 9)


def _pick_ui_font() -> tuple:
    """挑一个本机存在的中文字体。"""
    global FONT_UI, FONT_UI_SM, FONT_UI_B, FONT_H1, FONT_H2
    try:
        available = set(tkfont.families())
    except Exception:
        return FONT_UI
    for family in ("Microsoft YaHei UI", "Microsoft YaHei", "微软雅黑", "Segoe UI", "SimHei"):
        if family in available:
            FONT_UI = (family, 10)
            FONT_UI_SM = (family, 9)
            FONT_UI_B = (family, 10, "bold")
            FONT_H1 = (family, 15, "bold")
            FONT_H2 = (family, 12, "bold")
            return FONT_UI
    return FONT_UI


def enable_dpi_awareness() -> None:
    """让窗口在缩放显示器上不糊。"""
    try:
        import ctypes

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


FONT_NAMES = ("FONT_UI", "FONT_UI_SM", "FONT_UI_B", "FONT_H1", "FONT_H2",
              "FONT_MONO", "FONT_MONO_SM")


def sync_fonts(namespace: dict) -> None:
    """把 apply_theme() 检测到的字体写回调用方模块的全局变量。

    `from .theme import FONT_UI_SM` 拿到的是导入时的副本，apply_theme 之后并不会更新，
    于是显式写了 font=FONT_UI_SM 的控件仍然用着默认字体族（在字体不同的机器上会被 Tk
    回退替换）。在建控件之前调用本函数同步一次即可。
    """
    for name in FONT_NAMES:
        if name in globals():
            namespace[name] = globals()[name]


def human_size(num: int) -> str:
    num = float(num or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(num)} B"
            return f"{num:.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} TB"


def apply_theme(root: tk.Misc) -> ttk.Style:
    """配置整体深色主题，返回 style 对象。"""
    _pick_ui_font()
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
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
