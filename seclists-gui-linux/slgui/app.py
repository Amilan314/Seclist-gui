# -*- coding: utf-8 -*-
"""SecLists 助手（Linux 版）主窗口：本地 Tkinter 图形界面，不监听端口、不联网。"""

from __future__ import annotations

import os
import queue
import re
import shlex
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.parse
from tkinter import filedialog, messagebox, ttk

from .catalog import (CATEGORY_INFO, CATEGORY_STARTERS, CHEATSHEET, ETHICS_NOTICE, GROUPS,
                      QUICK_START_STEPS, SCENARIOS, derive_targets, render_command, render_path)
from .indexer import FileEntry, Index, human_int, human_size, is_probably_text, save_text
from .theme import (COLORS, FONT_H1, FONT_H2, FONT_MONO, FONT_MONO_SM, FONT_UI, FONT_UI_B,
                    FONT_UI_SM, apply_theme, sync_fonts)

STYLE_LABELS = [("本机路径（Linux 绝对路径）", "local"),
                ("Kali 路径（/usr/share/seclists/…）", "kali"),
                ("相对路径（仓库内相对）", "rel")]
PREVIEW_LIMITS = ["100 行", "500 行", "2000 行", "10000 行", "200000 行（可能较慢）"]


def _limit_value(label: str) -> int:
    try:
        return int(str(label).split()[0].replace(",", ""))
    except Exception:
        return 500


class CodeView(ttk.Frame):
    """带行号栏、可复制但不可编辑的代码/文本视图。"""

    def __init__(self, master, height: int = 12, gutter: bool = True, hbar: bool = True,
                 wrap: str = "none", **kw):
        super().__init__(master, style="Card.TFrame")
        self._gutter_on = gutter
        self.gutter = tk.Text(self, width=6, padx=6, pady=4, takefocus=0, borderwidth=0,
                              highlightthickness=0, background=COLORS["panel3"],
                              foreground=COLORS["muted"], font=FONT_MONO_SM, state="disabled",
                              wrap="none", cursor="arrow")
        self.text = tk.Text(self, height=height, wrap=wrap, borderwidth=0, highlightthickness=0,
                            background=COLORS["code_bg"], foreground=COLORS["code_fg"],
                            insertbackground=COLORS["code_fg"], selectbackground=COLORS["sel"],
                            font=FONT_MONO, padx=8, pady=4, undo=False, **kw)
        self.vbar = ttk.Scrollbar(self, orient="vertical", command=self._yview)
        self.hbar = ttk.Scrollbar(self, orient="horizontal", command=self.text.xview)
        self.text.configure(yscrollcommand=self._on_yscroll, xscrollcommand=self.hbar.set)

        if gutter:
            self.gutter.grid(row=0, column=0, sticky="ns")
        self.text.grid(row=0, column=1, sticky="nsew")
        self.vbar.grid(row=0, column=2, sticky="ns")
        if hbar:
            self.hbar.grid(row=1, column=1, sticky="ew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        self.text.configure(state="disabled")
        for widget in (self.text, self.gutter):
            widget.bind("<MouseWheel>", self._on_wheel)
            widget.bind("<Shift-MouseWheel>", self._on_shift_wheel)
        self.text.bind("<Control-c>", self._copy_selection)
        self.text.bind("<Control-a>", self._select_all)
        self.text.bind("<Button-3>", self._popup)
        self.text.tag_configure("hit", background="#3c5320", foreground="#f2ffdc")
        self.text.tag_configure("warnline", foreground=COLORS["warn"])
        self._menu = tk.Menu(self, tearoff=0, background=COLORS["panel2"], foreground=COLORS["fg"],
                             activebackground=COLORS["sel"], activeforeground="#ffffff", borderwidth=0)
        self._menu.add_command(label="复制选中", command=self._copy_selection)
        self._menu.add_command(label="全选", command=self._select_all)
        self._menu.add_separator()
        self._menu.add_command(label="复制全部内容", command=self.copy_all)

    # ------------------------------------------------------------- 基础操作
    def _on_wheel(self, event):
        self.text.yview_scroll(int(-event.delta / 120), "units")
        return "break"

    def _on_shift_wheel(self, event):
        self.text.xview_scroll(int(-event.delta / 120), "units")
        return "break"

    def _yview(self, *args):
        self.text.yview(*args)

    def _on_yscroll(self, first, last):
        self.vbar.set(first, last)
        if self._gutter_on:
            self.gutter.yview_moveto(first)

    def _copy_selection(self, event=None):
        try:
            sel = self.text.get("sel.first", "sel.last")
        except tk.TclError:
            return "break"
        self.clipboard_clear()
        self.clipboard_append(sel)
        return "break"

    def _select_all(self, event=None):
        self.text.tag_add("sel", "1.0", "end-1c")
        return "break"

    def _popup(self, event):
        try:
            self._menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._menu.grab_release()
        return "break"

    # ------------------------------------------------------------- 内容设置
    def set_lines(self, lines, start: int = 1, gutter_on: bool | None = None) -> None:
        if gutter_on is not None and gutter_on != self._gutter_on:
            self._gutter_on = gutter_on
            if gutter_on:
                self.gutter.grid(row=0, column=0, sticky="ns")
            else:
                self.gutter.grid_remove()
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", "\n".join(lines))
        self.text.configure(state="disabled")
        if self._gutter_on:
            nums = "\n".join(str(i) for i in range(start, start + max(len(lines), 1)))
            self.gutter.configure(state="normal")
            self.gutter.delete("1.0", "end")
            self.gutter.insert("1.0", nums)
            self.gutter.configure(state="disabled")
        self.text.yview_moveto(0.0)

    def set_text(self, text: str) -> None:
        self.set_lines((text or "").split("\n"))

    def get_text(self) -> str:
        return self.text.get("1.0", "end-1c")

    def copy_all(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.get_text())

    def highlight(self, needle: str, case_sensitive: bool = False) -> int:
        """高亮所有匹配并返回匹配次数。"""
        self.text.tag_remove("hit", "1.0", "end")
        if not needle:
            return 0
        count = tk.IntVar()
        start = "1.0"
        hits = 0
        while True:
            pos = self.text.search(needle, start, stopindex="end", nocase=not case_sensitive,
                                   count=count)
            if not pos or not count.get():
                break
            end = f"{pos}+{count.get()}c"
            self.text.tag_add("hit", pos, end)
            hits += 1
            start = end
            if hits > 5000:
                break
        return hits

    def see_line(self, lineno: int) -> None:
        self.text.see(f"{max(1, lineno)}.0")


class ScrollFrame(ttk.Frame):
    """可滚动的竖向容器（用于场景详情、速查手册等）。"""

    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        self.canvas = tk.Canvas(self, highlightthickness=0, background=COLORS["bg"],
                                borderwidth=0)
        self.vbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.body = ttk.Frame(self.canvas)
        self._win = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.canvas.configure(yscrollcommand=self.vbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.vbar.pack(side="right", fill="y")
        self.body.bind("<Configure>", self._on_body)
        self.canvas.bind("<Configure>", self._on_canvas)
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._wheel))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

    def _on_body(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas(self, event):
        self.canvas.itemconfigure(self._win, width=event.width)

    def _wheel(self, event):
        self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def clear(self):
        for child in self.body.winfo_children():
            child.destroy()

    def to_top(self):
        self.canvas.yview_moveto(0.0)

    def scroll_to(self, widget) -> None:
        """滚动到指定子控件的位置。"""
        if widget is None:
            return
        try:
            self.update_idletasks()
            total = max(self.body.winfo_height(), 1)
            y = widget.winfo_y()
            self.canvas.yview_moveto(max(0.0, min(1.0, (y - 12) / total)))
        except Exception:
            pass


class SecListsApp(tk.Tk):
    def __init__(self, root_dir: str, data_dir: str):
        super().__init__()
        self.root_dir = os.path.abspath(root_dir)
        self.data_dir = os.path.abspath(data_dir)
        self.out_dir = os.path.join(self.data_dir, "output")
        os.makedirs(self.out_dir, exist_ok=True)

        self.title("SecLists 使用助手 — 字典导航 / 场景引导 / 命令生成")
        self.geometry("1360x860")
        self.minsize(1100, 700)
        self.configure(background=COLORS["bg"])
        self.style = apply_theme(self)
        # apply_theme 会按本机实际字体改写 theme 模块里的 FONT_* 常量；
        # 本模块里那些常量是导入时的副本，建控件前必须同步一次（Linux 发行版字体差异大）。
        sync_fonts(globals())

        self.index = Index(self.root_dir, self.data_dir,
                           extra_skip=(os.path.basename(os.path.dirname(self.data_dir)),))
        self.q: "queue.Queue[dict]" = queue.Queue()
        self.cancel_search = threading.Event()
        self.cancel_lines = threading.Event()
        self.cancel_tool = threading.Event()
        self.busy = {"scan": False, "search": False, "lines": False, "tool": False}

        self.current_entry: FileEntry | None = None
        self.scope_rel = ""
        self.cmd_views: list[tuple[CodeView, str, dict]] = []
        self._nav_populated: set[str] = set()
        self._result_map: dict[str, tuple] = {}
        self._guide_filter_job = None
        self._nav_filter_job = None
        self._tool_files: list[str] = []
        self._poll_id = None
        self._closing = False
        self.headless = False

        self.target_var = tk.StringVar()
        self.style_var = tk.StringVar(value=STYLE_LABELS[0][0])
        self.status_var = tk.StringVar(value="正在扫描仓库…")
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_max = tk.DoubleVar(value=100)
        self.scope_var = tk.StringVar(value="全库（seclists-gui）")
        self.preview_info_var = tk.StringVar(value="在左侧双击任意字典文件即可预览")
        self.search_status_var = tk.StringVar(value="输入关键字后点「开始搜索」")
        self.tool_status_var = tk.StringVar(value="选择要处理的字典文件后执行")
        self.preview_limit_var = tk.StringVar(value="500 行")
        self.preview_enc_var = tk.StringVar(value="自动识别")
        self.wrap_var = tk.BooleanVar(value=False)

        self._build_menu()
        self._build_header()
        self._build_body()
        self._build_status()
        self._bind_keys()

        self.target_var.trace_add("write", lambda *a: self._on_target_changed())
        self.style_var.trace_add("write", lambda *a: self._on_target_changed())
        self.after(80, self._poll_queue)
        self.after(120, self._start_scan)
        self.after(400, self._set_sashes)

    def _set_sashes(self):
        """初始分隔条位置：左侧导航窄一些，内容区更宽。"""
        for pane, pos in ((getattr(self, "main_paned", None), 350),
                          (getattr(self, "guide_split", None), 292)):
            if pane is None:
                continue
            try:
                pane.sashpos(0, pos)
            except Exception:
                pass

    # ==================================================================== 构建
    def _build_menu(self):
        menubar = tk.Menu(self, background=COLORS["panel2"], foreground=COLORS["fg"],
                          activebackground=COLORS["sel"], activeforeground="#ffffff",
                          borderwidth=0)
        m_file = tk.Menu(menubar, tearoff=0, background=COLORS["panel2"], foreground=COLORS["fg"],
                         activebackground=COLORS["sel"], activeforeground="#ffffff")
        m_file.add_command(label="重新扫描仓库\tF5", command=self._start_scan)
        m_file.add_command(label="打开数据目录（缓存/输出）", command=lambda: self._reveal(self.data_dir))
        m_file.add_separator()
        m_file.add_command(label="退出\tCtrl+Q", command=self.destroy)
        menubar.add_cascade(label="文件", menu=m_file)

        m_nav = tk.Menu(menubar, tearoff=0, background=COLORS["panel2"], foreground=COLORS["fg"],
                        activebackground=COLORS["sel"], activeforeground="#ffffff")
        for idx, (tab, _key) in enumerate([("使用引导", "Ctrl+1"), ("字典预览", "Ctrl+2"),
                                           ("全库搜索", "Ctrl+3"), ("字典工具箱", "Ctrl+4"),
                                           ("速查手册", "Ctrl+5")]):
            m_nav.add_command(label=f"{tab}\t{_key}",
                              command=lambda i=idx: self.nb.select(i))
        menubar.add_cascade(label="跳转", menu=m_nav)

        m_help = tk.Menu(menubar, tearoff=0, background=COLORS["panel2"], foreground=COLORS["fg"],
                         activebackground=COLORS["sel"], activeforeground="#ffffff")
        m_help.add_command(label="合规提醒", command=lambda: self._info("合规提醒", ETHICS_NOTICE))
        m_help.add_command(label="关于本工具", command=self._about)
        menubar.add_cascade(label="帮助", menu=m_help)
        self.configure(menu=menubar)

    def _build_header(self):
        head = ttk.Frame(self, style="Header.TFrame", padding=(14, 10))
        head.pack(side="top", fill="x")

        left = ttk.Frame(head, style="Header.TFrame")
        left.pack(side="left", fill="x", expand=True)
        ttk.Label(left, text="📚 SecLists 使用助手", style="H1.TLabel").pack(anchor="w")
        self.repo_label = ttk.Label(left, text="", style="Panel.TLabel", foreground=COLORS["muted"],
                                    font=FONT_UI_SM)
        self.repo_label.pack(anchor="w")

        right = ttk.Frame(head, style="Header.TFrame")
        right.pack(side="right")
        ttk.Label(right, text="目标（域名 / IP / URL）", style="Panel.TLabel").grid(
            row=0, column=0, sticky="e", padx=(0, 6))
        entry = ttk.Entry(right, textvariable=self.target_var, width=34)
        entry.grid(row=0, column=1, sticky="w")
        ttk.Label(right, text="路径风格", style="Panel.TLabel").grid(
            row=0, column=2, sticky="e", padx=(14, 6))
        combo = ttk.Combobox(right, textvariable=self.style_var, state="readonly", width=26,
                             values=[label for label, _ in STYLE_LABELS])
        combo.grid(row=0, column=3, sticky="w")
        ttk.Button(right, text="重新扫描 (F5)", command=self._start_scan).grid(
            row=0, column=4, padx=(14, 0))
        self.derived_label = ttk.Label(right, text="", style="Panel.TLabel",
                                       foreground=COLORS["accent"], font=FONT_UI_SM)
        self.derived_label.grid(row=1, column=0, columnspan=5, sticky="e", pady=(4, 0))

    def _build_body(self):
        body = ttk.Frame(self, padding=(10, 6))
        body.pack(side="top", fill="both", expand=True)

        paned = ttk.Panedwindow(body, orient="horizontal")
        paned.pack(fill="both", expand=True)
        self.main_paned = paned

        # ---------------- 左侧导航
        nav = ttk.Frame(paned, style="Panel.TFrame", padding=8)
        paned.add(nav, weight=1)

        ttk.Label(nav, text="字典导航", style="Panel.TLabel", font=FONT_H2).pack(anchor="w")
        ttk.Label(nav, text="双击文件＝预览，右键＝复制路径", style="CardDim.TLabel",
                  font=FONT_UI_SM).pack(anchor="w", pady=(0, 6))
        self.nav_filter = ttk.Entry(nav)
        self.nav_filter.pack(fill="x")
        self.nav_filter.bind("<KeyRelease>", self._on_nav_filter)

        nav_tv_frame = ttk.Frame(nav, style="Panel.TFrame")
        nav_tv_frame.pack(fill="both", expand=True, pady=(6, 0))
        self.nav = ttk.Treeview(nav_tv_frame, columns=("size", "count"), show="tree headings",
                                selectmode="browse")
        self.nav.heading("#0", text="分类 / 目录 / 文件", anchor="w")
        self.nav.heading("size", text="大小", anchor="e")
        self.nav.heading("count", text="行数/文件数", anchor="e")
        self.nav.column("#0", width=300, stretch=True)
        self.nav.column("size", width=90, anchor="e", stretch=False)
        self.nav.column("count", width=110, anchor="e", stretch=False)
        nav_sb = ttk.Scrollbar(nav_tv_frame, orient="vertical", command=self.nav.yview)
        self.nav.configure(yscrollcommand=nav_sb.set)
        self.nav.pack(side="left", fill="both", expand=True)
        nav_sb.pack(side="right", fill="y")
        self.nav.tag_configure("top", foreground=COLORS["accent"])
        self.nav.tag_configure("dir", foreground=COLORS["fg_dim"])
        self.nav.tag_configure("file", foreground=COLORS["fg"])
        self.nav.tag_configure("hit", foreground=COLORS["ok"])
        self.nav.bind("<<TreeviewOpen>>", self._on_nav_open)
        self.nav.bind("<<TreeviewSelect>>", self._on_nav_select)
        self.nav.bind("<Double-1>", self._on_nav_double)
        self.nav.bind("<Button-3>", self._on_nav_menu)

        self.nav_menu = tk.Menu(self, tearoff=0, background=COLORS["panel2"], foreground=COLORS["fg"],
                                activebackground=COLORS["sel"], activeforeground="#ffffff")
        for label, fn in [("👀 预览此文件", self._nav_action_preview),
                          ("📋 复制本机路径", lambda: self._nav_action_copy("local")),
                          ("📋 复制 Kali 路径", lambda: self._nav_action_copy("kali")),
                          ("📋 复制相对路径", lambda: self._nav_action_copy("rel")),
                          ("📁 在资源管理器中显示", self._nav_action_reveal),
                          ("📝 用编辑器打开", self._nav_action_notepad),
                          ("📊 统计该目录行数", self._nav_action_count_dir),
                          ("🧰 加入工具箱", self._nav_action_toolbox)]:
            self.nav_menu.add_command(label=label, command=fn)

        self.nav_hint = ttk.Label(nav, text="", style="CardDim.TLabel", font=FONT_UI_SM,
                                  wraplength=330, justify="left")
        self.nav_hint.pack(anchor="w", pady=(6, 0))

        # ---------------- 右侧标签页
        self.nb = ttk.Notebook(paned)
        paned.add(self.nb, weight=4)
        self._build_guide_tab()
        self._build_preview_tab()
        self._build_search_tab()
        self._build_toolbox_tab()
        self._build_cheatsheet_tab()

    def _build_status(self):
        bar = ttk.Frame(self, style="Header.TFrame", padding=(12, 6))
        bar.pack(side="bottom", fill="x")
        ttk.Label(bar, textvariable=self.status_var, style="Panel.TLabel",
                  font=FONT_UI_SM).pack(side="left")
        self.progress = ttk.Progressbar(bar, variable=self.progress_var, maximum=100,
                                        length=200, mode="determinate")
        self.progress.pack(side="right")
        ttk.Label(bar, textvariable=self.scope_var, style="Panel.TLabel",
                  foreground=COLORS["muted"], font=FONT_UI_SM).pack(side="right", padx=12)

    def _bind_keys(self):
        self.bind("<F5>", lambda e: self._start_scan())
        self.bind("<Control-q>", lambda e: self.destroy())
        self.bind("<Control-f>", lambda e: self.nav_filter.focus_set())
        for i in range(5):
            self.bind(f"<Control-Key-{i + 1}>", lambda e, idx=i: self.nb.select(idx))
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ================================================================ 使用引导
    def _build_guide_tab(self):
        tab = ttk.Frame(self.nb, padding=10)
        self.nb.add(tab, text=" 🧭 使用引导 ")

        strip = ttk.Frame(tab, style="Card.TFrame", padding=10)
        strip.pack(fill="x")
        ttk.Label(strip, text="四步上手", style="CardH2.TLabel").grid(row=0, column=0, sticky="w",
                                                                      columnspan=4)
        for i, (title, body) in enumerate(QUICK_START_STEPS):
            cell = ttk.Frame(strip, style="Card.TFrame")
            cell.grid(row=1, column=i, sticky="nsew", padx=(0, 10))
            ttk.Label(cell, text=title, style="Card.TLabel", font=FONT_UI_B,
                      foreground=COLORS["accent"]).pack(anchor="w")
            ttk.Label(cell, text=body, style="CardDim.TLabel", font=FONT_UI_SM, wraplength=260,
                      justify="left").pack(anchor="w")
            strip.columnconfigure(i, weight=1)
        ttk.Label(strip, text=ETHICS_NOTICE, style="Card.TLabel", foreground=COLORS["warn"],
                  font=FONT_UI_SM, wraplength=1250, justify="left").grid(
            row=2, column=0, columnspan=4, sticky="w", pady=(6, 0))

        split = ttk.Panedwindow(tab, orient="horizontal")
        split.pack(fill="both", expand=True, pady=(10, 0))
        self.guide_split = split

        left = ttk.Frame(split, style="Panel.TFrame", padding=8)
        split.add(left, weight=1)
        ttk.Label(left, text="选择一个场景", style="Panel.TLabel", font=FONT_H2).pack(anchor="w")
        self.guide_filter = ttk.Entry(left)
        self.guide_filter.pack(fill="x", pady=(0, 6))
        self.guide_filter.bind("<KeyRelease>", self._on_guide_filter)
        gt_frame = ttk.Frame(left, style="Panel.TFrame")
        gt_frame.pack(fill="both", expand=True)
        self.guide_tree = ttk.Treeview(gt_frame, show="tree", selectmode="browse")
        self.guide_tree.column("#0", width=280, stretch=True)
        gsb = ttk.Scrollbar(gt_frame, orient="vertical", command=self.guide_tree.yview)
        self.guide_tree.configure(yscrollcommand=gsb.set)
        self.guide_tree.pack(side="left", fill="both", expand=True)
        gsb.pack(side="right", fill="y")
        self.guide_tree.tag_configure("group", foreground=COLORS["accent"])
        self.guide_tree.bind("<<TreeviewSelect>>", self._on_guide_select)
        self._fill_guide_tree()

        right = ttk.Frame(split, style="Panel.TFrame", padding=8)
        split.add(right, weight=4)
        self.guide_scroll = ScrollFrame(right, style="Panel.TFrame")
        self.guide_scroll.pack(fill="both", expand=True)

    def _fill_guide_tree(self, query: str = ""):
        tree = self.guide_tree
        tree.delete(*tree.get_children())
        q = (query or "").strip().lower()
        by_group: dict[str, list[dict]] = {}
        for sc in SCENARIOS:
            if q and q not in (sc["title"] + sc["summary"] + sc["id"]).lower():
                continue
            by_group.setdefault(sc["group"], []).append(sc)
        for gid, gname in GROUPS:
            items = by_group.get(gid)
            if not items:
                continue
            node = tree.insert("", "end", iid=f"g:{gid}", text=gname, open=bool(q), tags=("group",))
            for sc in items:
                tree.insert(node, "end", iid=f"s:{sc['id']}", text=f"  {sc['title']}")
        first = None
        for gid, _ in GROUPS:
            kids = tree.get_children(f"g:{gid}") if tree.exists(f"g:{gid}") else ()
            if kids:
                first = kids[0]
                break
        if first:
            tree.selection_set(first)
            tree.focus(first)

    def _on_guide_filter(self, _event=None):
        if self._guide_filter_job:
            self.after_cancel(self._guide_filter_job)
        self._guide_filter_job = self.after(200, lambda: self._fill_guide_tree(self.guide_filter.get()))

    def _on_guide_select(self, _event=None):
        sel = self.guide_tree.selection()
        if not sel:
            return
        iid = sel[0]
        if not iid.startswith("s:"):
            return
        sid = iid[2:]
        scenario = next((s for s in SCENARIOS if s["id"] == sid), None)
        if scenario:
            self._show_scenario(scenario)

    def _show_scenario(self, sc: dict):
        body = self.guide_scroll.body
        body.configure(style="Panel.TFrame")
        self.guide_scroll.clear()
        self.cmd_views = []
        self._cmd_anchor = None

        head = ttk.Frame(body, style="Panel.TFrame")
        head.pack(fill="x")
        ttk.Label(head, text=sc["title"], style="Panel.TLabel", font=FONT_H1).pack(side="left",
                                                                                   anchor="w")
        ttk.Button(head, text="↓ 命令模板", style="Tiny.TButton",
                   command=lambda: self.guide_scroll.scroll_to(self._cmd_anchor)).pack(side="right")
        badge_color = {"入门": COLORS["ok"], "进阶": COLORS["warn"], "高级": COLORS["danger"]}.get(
            sc.get("level", ""), COLORS["fg_dim"])
        ttk.Label(head, text=f"难度：{sc.get('level', '—')}", style="Panel.TLabel",
                  foreground=badge_color, font=FONT_UI_SM).pack(side="right", padx=10)
        ttk.Label(body, text=sc["summary"], style="Panel.TLabel", wraplength=980,
                  justify="left").pack(anchor="w", pady=(6, 0))
        if sc.get("why"):
            why = ttk.Frame(body, style="Panel.TFrame")
            why.pack(fill="x", pady=(4, 0))
            ttk.Label(why, text="为什么用这些字典：", style="Panel.TLabel", font=FONT_UI_B,
                      foreground=COLORS["accent"]).pack(side="left", anchor="n")
            ttk.Label(why, text=sc["why"], style="Panel.TLabel", foreground=COLORS["fg_dim"],
                      font=FONT_UI_SM, wraplength=900, justify="left").pack(side="left", anchor="w")

        # ---- 推荐字典
        ttk.Label(body, text="推荐字典（点「预览」看内容，点「复制」拿路径）", style="Panel.TLabel",
                  font=FONT_H2).pack(anchor="w", pady=(12, 4))
        lists = {item["key"]: item["path"] for item in sc.get("lists", [])}
        for item in sc.get("lists", []):
            card = ttk.Frame(body, style="Card.TFrame", padding=6)
            card.pack(fill="x", pady=2)
            top = ttk.Frame(card, style="Card.TFrame")
            top.pack(fill="x")
            exists = item["path"] in self.index.files or self.index.dirs.get(item["path"].rstrip("/")) is not None
            ttk.Label(top, text=item["path"], style="Card.TLabel", font=FONT_MONO_SM,
                      foreground=COLORS["fg"] if exists else COLORS["danger"],
                      wraplength=640, justify="left").pack(side="left", anchor="w")
            btns = ttk.Frame(top, style="Card.TFrame")
            btns.pack(side="right")
            ttk.Button(btns, text="预览", style="Tiny.TButton",
                       command=lambda p=item["path"]: self._preview_rel(p)).pack(side="left", padx=2)
            ttk.Button(btns, text="复制路径", style="Tiny.TButton",
                       command=lambda p=item["path"]: self._copy_path(p)).pack(side="left", padx=2)
            if exists and os.path.exists(self._abs(item["path"])):
                ttk.Button(btns, text="定位", style="Tiny.TButton",
                           command=lambda p=item["path"]: self._locate_rel(p)).pack(side="left", padx=2)
            ttk.Label(card, text=item.get("note", ""), style="CardDim.TLabel", font=FONT_UI_SM,
                      wraplength=940, justify="left").pack(anchor="w", pady=(4, 0))
            if not exists:
                ttk.Label(card, text="⚠ 本仓库中未找到该文件（可能被裁剪），可从左侧导航搜索同类字典。",
                          style="Card.TLabel", foreground=COLORS["warn"],
                          font=FONT_UI_SM).pack(anchor="w")

        # ---- 命令
        cmd_head = ttk.Label(body, text="命令模板（右上角填目标后自动替换；点「复制」粘贴到终端）",
                             style="Panel.TLabel", font=FONT_H2)
        cmd_head.pack(anchor="w", pady=(16, 4))
        self._cmd_anchor = cmd_head
        for cmd in sc.get("commands", []):
            card = ttk.Frame(body, style="Card.TFrame", padding=8)
            card.pack(fill="x", pady=3)
            ttk.Label(card, text=f"▸ {cmd['tool']}", style="Card.TLabel", font=FONT_UI_B,
                      foreground=COLORS["accent"]).pack(anchor="w")
            row = ttk.Frame(card, style="Card.TFrame")
            row.pack(fill="x", pady=(4, 0))
            view = CodeView(row, height=2, gutter=False, hbar=False)
            view.pack(side="left", fill="x", expand=True)
            ttk.Button(row, text="复制", style="Tiny.TButton",
                       command=lambda v=view: self._copy_view(v, "命令")).pack(side="left", padx=(6, 0))
            ttk.Button(row, text="▶ 在终端运行", style="Tiny.TButton",
                       command=lambda v=view, t=cmd["tool"]: self._run_in_terminal(v.get_text(), t)
                       ).pack(side="left", padx=(4, 0))
            self.cmd_views.append((view, cmd["cmd"], lists))
            if cmd.get("note"):
                ttk.Label(card, text=cmd["note"], style="CardDim.TLabel", font=FONT_UI_SM,
                          wraplength=940, justify="left").pack(anchor="w", pady=(4, 0))

        if sc.get("tips"):
            ttk.Label(body, text="提示与避坑", style="Panel.TLabel", font=FONT_H2).pack(
                anchor="w", pady=(16, 4))
            tip_card = ttk.Frame(body, style="Card.TFrame", padding=8)
            tip_card.pack(fill="x")
            for tip in sc["tips"]:
                ttk.Label(tip_card, text=f"• {tip}", style="CardDim.TLabel", wraplength=940,
                          justify="left").pack(anchor="w", pady=1)

        ttk.Frame(body, style="Panel.TFrame", height=16).pack()
        self._refresh_commands()
        self.guide_scroll.to_top()

    # ================================================================ 预览标签页
    def _build_preview_tab(self):
        tab = ttk.Frame(self.nb, padding=10)
        self.nb.add(tab, text=" 👀 字典预览 ")

        info = ttk.Frame(tab, style="Card.TFrame", padding=8)
        info.pack(fill="x")
        self.preview_info = ttk.Label(info, textvariable=self.preview_info_var, style="Card.TLabel",
                                      font=FONT_MONO_SM, wraplength=1100, justify="left")
        self.preview_info.pack(anchor="w")

        bar = ttk.Frame(tab, padding=(0, 8))
        bar.pack(fill="x")
        ttk.Label(bar, text="显示").pack(side="left")
        combo = ttk.Combobox(bar, textvariable=self.preview_limit_var, state="readonly", width=18,
                             values=PREVIEW_LIMITS)
        combo.pack(side="left", padx=(4, 10))
        combo.bind("<<ComboboxSelected>>", lambda e: self._reload_preview())
        ttk.Label(bar, text="编码").pack(side="left")
        enc = ttk.Combobox(bar, textvariable=self.preview_enc_var, state="readonly", width=10,
                           values=["自动识别", "utf-8", "cp1252", "latin-1", "utf-16"])
        enc.pack(side="left", padx=(4, 10))
        enc.bind("<<ComboboxSelected>>", lambda e: self._reload_preview())
        ttk.Checkbutton(bar, text="自动换行", variable=self.wrap_var,
                        command=self._apply_wrap).pack(side="left", padx=(0, 10))
        ttk.Label(bar, text="文件内搜索").pack(side="left")
        self.preview_find = ttk.Entry(bar, width=22)
        self.preview_find.pack(side="left", padx=4)
        self.preview_find.bind("<Return>", lambda e: self._find_in_preview())
        ttk.Button(bar, text="查找", style="Tiny.TButton", command=self._find_in_preview).pack(side="left")

        bar2 = ttk.Frame(tab, padding=(0, 0))
        bar2.pack(fill="x", pady=(0, 6))
        for label, fn in [("📋 复制路径", lambda: self._copy_current_path("local")),
                          ("🐧 复制 Kali 路径", lambda: self._copy_current_path("kali")),
                          ("📋 复制全部内容", self._copy_preview_all),
                          ("📊 统计行数", self._count_current),
                          ("💾 另存为…", self._save_preview_as),
                          ("📁 打开所在文件夹", lambda: self._reveal((self.current_entry or self._dummy()).path)),
                          ("📝 用编辑器打开", lambda: self._notepad((self.current_entry or self._dummy()).path)),
                          ("🔍 在该文件中搜索", self._search_in_current)]:
            ttk.Button(bar2, text=label, style="Tiny.TButton", command=fn).pack(side="left", padx=(0, 6))

        self.preview_view = CodeView(tab, height=28)
        self.preview_view.pack(fill="both", expand=True)

    def _apply_wrap(self):
        wrap = "word" if self.wrap_var.get() else "none"
        self.preview_view.text.configure(wrap=wrap)
        if wrap == "word":
            self.preview_view.hbar.grid_remove()
            self.preview_view.gutter.grid_remove()
            self.preview_view._gutter_on = False
        else:
            self.preview_view.hbar.grid()
            self.preview_view.gutter.grid()
            self.preview_view._gutter_on = True

    def _dummy(self):
        class _D:
            path = ""
        return _D()

    # ================================================================ 搜索标签页
    def _build_search_tab(self):
        tab = ttk.Frame(self.nb, padding=10)
        self.nb.add(tab, text=" 🔎 全库搜索 ")

        self.search_mode = tk.StringVar(value="content")
        self.search_scope = tk.StringVar(value="all")
        self.search_case = tk.BooleanVar(value=False)
        self.search_regex = tk.BooleanVar(value=False)
        self.search_textonly = tk.BooleanVar(value=True)
        self.search_maxmb = tk.StringVar(value="64")
        self.search_perfile = tk.StringVar(value="40")

        row1 = ttk.Frame(tab)
        row1.pack(fill="x")
        ttk.Label(row1, text="搜索方式").pack(side="left")
        ttk.Radiobutton(row1, text="按内容搜索（在字典里找关键字）", variable=self.search_mode,
                        value="content").pack(side="left", padx=6)
        ttk.Radiobutton(row1, text="按文件名搜索", variable=self.search_mode,
                        value="name").pack(side="left", padx=6)

        row2 = ttk.Frame(tab, padding=(0, 6))
        row2.pack(fill="x")
        ttk.Label(row2, text="范围").pack(side="left")
        ttk.Radiobutton(row2, text="全库", variable=self.search_scope, value="all").pack(side="left", padx=6)
        ttk.Radiobutton(row2, text="仅当前选中目录", variable=self.search_scope,
                        value="scope").pack(side="left", padx=6)
        ttk.Checkbutton(row2, text="仅文本文件", variable=self.search_textonly).pack(side="left", padx=(12, 0))
        ttk.Label(row2, text="单文件上限(MB)").pack(side="left", padx=(12, 2))
        ttk.Spinbox(row2, from_=1, to=2048, width=6, textvariable=self.search_maxmb).pack(side="left")
        ttk.Label(row2, text="每文件最多命中").pack(side="left", padx=(12, 2))
        ttk.Spinbox(row2, from_=1, to=500, width=6, textvariable=self.search_perfile).pack(side="left")

        row3 = ttk.Frame(tab)
        row3.pack(fill="x")
        ttk.Label(row3, text="关键字").pack(side="left")
        self.search_entry = ttk.Entry(row3)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=6)
        self.search_entry.bind("<Return>", lambda e: self._start_search())
        ttk.Checkbutton(row3, text="区分大小写", variable=self.search_case).pack(side="left", padx=(0, 6))
        ttk.Checkbutton(row3, text="正则", variable=self.search_regex).pack(side="left", padx=(0, 10))
        self.search_btn = ttk.Button(row3, text="开始搜索", style="Accent.TButton",
                                     command=self._start_search)
        self.search_btn.pack(side="left")
        self.search_stop_btn = ttk.Button(row3, text="停止", command=self._stop_search,
                                          state="disabled")
        self.search_stop_btn.pack(side="left", padx=6)
        ttk.Button(row3, text="导出结果", command=self._export_results).pack(side="left")

        row4 = ttk.Frame(tab, padding=(0, 6))
        row4.pack(fill="x")
        ttk.Label(row4, textvariable=self.search_status_var).pack(side="left")
        self.search_progress = ttk.Progressbar(row4, maximum=100, length=240)
        self.search_progress.pack(side="right")

        tv_frame = ttk.Frame(tab)
        tv_frame.pack(fill="both", expand=True)
        self.results = ttk.Treeview(tv_frame, columns=("line", "text"), show="tree headings",
                                    selectmode="browse")
        self.results.heading("#0", text="文件 / 命中", anchor="w")
        self.results.heading("line", text="行号", anchor="e")
        self.results.heading("text", text="内容", anchor="w")
        self.results.column("#0", width=380, stretch=False)
        self.results.column("line", width=80, anchor="e", stretch=False)
        self.results.column("text", width=760, stretch=True)
        rsb = ttk.Scrollbar(tv_frame, orient="vertical", command=self.results.yview)
        self.results.configure(yscrollcommand=rsb.set)
        self.results.pack(side="left", fill="both", expand=True)
        rsb.pack(side="right", fill="y")
        self.results.tag_configure("file", foreground=COLORS["accent"])
        self.results.bind("<Double-1>", self._on_result_open)

    # ================================================================ 工具箱
    def _build_toolbox_tab(self):
        tab = ttk.Frame(self.nb, padding=10)
        self.nb.add(tab, text=" 🧰 字典工具箱 ")

        hint = ttk.Frame(tab, style="Card.TFrame", padding=8)
        hint.pack(fill="x")
        ttk.Label(hint, text="把多份字典合并、去重、按长度/关键字过滤、截取前 N 行，另存为新字典。"
                             "结果默认写到 seclists-gui/data/output/ 下，不会改动 SecLists 原文件。",
                  style="CardDim.TLabel", font=FONT_UI_SM, wraplength=1150,
                  justify="left").pack(anchor="w")

        split = ttk.Panedwindow(tab, orient="horizontal")
        split.pack(fill="both", expand=True, pady=(10, 0))

        left = ttk.Frame(split, style="Panel.TFrame", padding=8)
        split.add(left, weight=1)
        ttk.Label(left, text="源字典", style="Panel.TLabel", font=FONT_H2).pack(anchor="w")
        lbf = ttk.Frame(left, style="Panel.TFrame")
        lbf.pack(fill="both", expand=True, pady=6)
        self.tool_list = tk.Listbox(lbf, selectmode="extended", background=COLORS["code_bg"],
                                    foreground=COLORS["fg"], selectbackground=COLORS["sel"],
                                    highlightthickness=0, borderwidth=0, font=FONT_MONO_SM)
        tsb = ttk.Scrollbar(lbf, orient="vertical", command=self.tool_list.yview)
        self.tool_list.configure(yscrollcommand=tsb.set)
        self.tool_list.pack(side="left", fill="both", expand=True)
        tsb.pack(side="right", fill="y")
        tb = ttk.Frame(left, style="Panel.TFrame")
        tb.pack(fill="x")
        for label, fn in [("＋ 添加文件…", self._tool_add_files),
                          ("↙ 用左侧选中", self._tool_add_selected),
                          ("－ 移除选中", self._tool_remove),
                          ("清空", self._tool_clear)]:
            ttk.Button(tb, text=label, style="Tiny.TButton", command=fn).pack(side="left", padx=(0, 4))
        self.tool_hint = ttk.Label(left, text="尚未选择文件", style="CardDim.TLabel", font=FONT_UI_SM)
        self.tool_hint.pack(anchor="w", pady=(4, 0))

        right = ttk.Frame(split, style="Panel.TFrame", padding=8)
        split.add(right, weight=3)

        opts = ttk.Frame(right, style="Card.TFrame", padding=10)
        opts.pack(fill="x")
        ttk.Label(opts, text="处理选项", style="CardH2.TLabel").grid(row=0, column=0, columnspan=6,
                                                                     sticky="w")
        self.tool_opts = {
            "dedup": tk.BooleanVar(value=True),
            "sort": tk.BooleanVar(value=False),
            "skip_empty": tk.BooleanVar(value=True),
            "skip_comments": tk.BooleanVar(value=False),
            "strip": tk.BooleanVar(value=True),
            "lower": tk.BooleanVar(value=False),
            "case_sensitive": tk.BooleanVar(value=False),
        }
        checks = [("去重", "dedup"), ("排序", "sort"), ("去掉空行", "skip_empty"),
                  ("去掉 # 注释行", "skip_comments"), ("去掉首尾空白", "strip"), ("转为小写", "lower"),
                  ("区分大小写（去重时）", "case_sensitive")]
        for i, (label, key) in enumerate(checks):
            ttk.Checkbutton(opts, text=label, variable=self.tool_opts[key],
                            style="Card.TCheckbutton").grid(row=1 + i // 4, column=i % 4,
                                                            sticky="w", padx=(0, 18), pady=2)

        self.tool_min = tk.StringVar(value="")
        self.tool_max = tk.StringVar(value="")
        self.tool_inc = tk.StringVar(value="")
        self.tool_exc = tk.StringVar(value="")
        self.tool_rx = tk.StringVar(value="")
        self.tool_head = tk.StringVar(value="")

        r = 3
        ttk.Label(opts, text="最小长度", style="Card.TLabel").grid(row=r, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(opts, textvariable=self.tool_min, width=8).grid(row=r, column=1, sticky="w", pady=(8, 0))
        ttk.Label(opts, text="最大长度", style="Card.TLabel").grid(row=r, column=2, sticky="w",
                                                                   padx=(12, 0), pady=(8, 0))
        ttk.Entry(opts, textvariable=self.tool_max, width=8).grid(row=r, column=3, sticky="w", pady=(8, 0))
        ttk.Label(opts, text="只取前 N 行", style="Card.TLabel").grid(row=r, column=4, sticky="w",
                                                                      padx=(12, 0), pady=(8, 0))
        ttk.Entry(opts, textvariable=self.tool_head, width=10).grid(row=r, column=5, sticky="w", pady=(8, 0))

        r += 1
        ttk.Label(opts, text="必须包含", style="Card.TLabel").grid(row=r, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(opts, textvariable=self.tool_inc).grid(row=r, column=1, columnspan=2, sticky="ew",
                                                         pady=(6, 0))
        ttk.Label(opts, text="必须排除", style="Card.TLabel").grid(row=r, column=3, sticky="w", pady=(6, 0))
        ttk.Entry(opts, textvariable=self.tool_exc).grid(row=r, column=4, columnspan=2, sticky="ew",
                                                         pady=(6, 0))
        r += 1
        ttk.Label(opts, text="正则过滤（只保留匹配行）", style="Card.TLabel").grid(row=r, column=0,
                                                                                   sticky="w", pady=(6, 0))
        ttk.Entry(opts, textvariable=self.tool_rx).grid(row=r, column=1, columnspan=5, sticky="ew",
                                                        pady=(6, 0))
        for c in (1, 2, 4, 5):
            opts.columnconfigure(c, weight=1)

        bar = ttk.Frame(right, padding=(0, 8))
        bar.pack(fill="x")
        ttk.Button(bar, text="执行并预览", style="Accent.TButton",
                   command=lambda: self._run_tool(save=False)).pack(side="left")
        ttk.Button(bar, text="保存为新字典…", command=lambda: self._run_tool(save=True)).pack(
            side="left", padx=6)
        self.tool_stop_btn = ttk.Button(bar, text="停止", command=self._stop_tool, state="disabled")
        self.tool_stop_btn.pack(side="left")
        ttk.Label(bar, textvariable=self.tool_status_var).pack(side="left", padx=12)
        self.tool_progress = ttk.Progressbar(bar, maximum=100, length=180)
        self.tool_progress.pack(side="right")

        self.tool_view = CodeView(right, height=16)
        self.tool_view.pack(fill="both", expand=True)

    # ================================================================ 速查手册
    def _build_cheatsheet_tab(self):
        tab = ttk.Frame(self.nb, padding=10)
        self.nb.add(tab, text=" 📖 速查手册 ")
        frame = ttk.Frame(tab)
        frame.pack(fill="both", expand=True)
        self.doc = tk.Text(frame, wrap="word", background=COLORS["code_bg"],
                           foreground=COLORS["code_fg"], borderwidth=0, highlightthickness=0,
                           padx=16, pady=12, font=FONT_UI, spacing1=2, spacing3=3)
        sb = ttk.Scrollbar(frame, orient="vertical", command=self.doc.yview)
        self.doc.configure(yscrollcommand=sb.set, state="disabled")
        self.doc.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.doc.tag_configure("h1", font=FONT_H1, foreground=COLORS["accent"], spacing1=14,
                               spacing3=8)
        self.doc.tag_configure("h2", font=FONT_H2, foreground=COLORS["ok"], spacing1=12, spacing3=6)
        self.doc.tag_configure("code", font=FONT_MONO, background="#0b0d11",
                               foreground="#cfe3ff", lmargin1=18, lmargin2=18, spacing1=1)
        self.doc.tag_configure("bullet", lmargin1=18, lmargin2=30)
        self.doc.tag_configure("plain", lmargin1=4)
        self._render_doc(CHEATSHEET.replace("<仓库根>", self.root_dir))
        self.doc.bind("<MouseWheel>", lambda e: self.doc.yview_scroll(int(-e.delta / 120), "units"))

    def _render_doc(self, md: str):
        self.doc.configure(state="normal")
        self.doc.delete("1.0", "end")
        in_code = False
        for raw in md.splitlines():
            line = raw.rstrip()
            if line.strip().startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                self.doc.insert("end", line + "\n", "code")
                continue
            if line.startswith("# "):
                self.doc.insert("end", line[2:].strip() + "\n", "h1")
            elif line.startswith("## "):
                self.doc.insert("end", line[3:].strip() + "\n", "h2")
            elif line.startswith("- ") or re.match(r"^\d+\.\s", line):
                self.doc.insert("end", line + "\n", "bullet")
            elif line.startswith("|"):
                self.doc.insert("end", line + "\n", "code")
            elif not line:
                self.doc.insert("end", "\n")
            else:
                self.doc.insert("end", line + "\n", "plain")
        self.doc.configure(state="disabled")

    # ================================================================ 扫描/索引
    def _start_scan(self):
        if self.busy["scan"]:
            return
        self.busy["scan"] = True
        self.status_var.set("正在扫描 SecLists 仓库…")
        self.repo_label.configure(text=f"仓库：{self.root_dir}")

        def worker():
            try:
                stats = self.index.scan(progress=lambda n, rel: self.q.put(
                    {"kind": "scan_progress", "n": n, "rel": rel}))
                self.q.put({"kind": "scan_done", "stats": stats})
            except Exception as exc:  # noqa: BLE001
                self.q.put({"kind": "error", "msg": f"扫描失败：{exc}"})

        threading.Thread(target=worker, daemon=True).start()

    def _on_scan_done(self, stats: dict):
        self.busy["scan"] = False
        per_top = stats.get("per_top", {})
        self.status_var.set(
            f"索引完成：{human_int(stats['files'])} 个文件 · {human_size(stats['size'])} · "
            f"{len(per_top)} 个分类 · {time.strftime('%H:%M:%S')}")
        self.progress_var.set(0)
        self._fill_nav()
        self._refresh_scenario_list_paths()

    def _refresh_scenario_list_paths(self):
        """索引完成后重画当前场景（让「未找到」标记变准确）。"""
        sel = self.guide_tree.selection()
        if sel and sel[0].startswith("s:"):
            sc = next((s for s in SCENARIOS if s["id"] == sel[0][2:]), None)
            if sc:
                self._show_scenario(sc)

    # ================================================================ 导航树
    def _fill_nav(self):
        self.nav.delete(*self.nav.get_children())
        self._nav_populated.clear()
        subdirs, root_files = self.index.children("")
        for top in subdirs:
            if top.startswith("."):
                continue
            icon, desc = CATEGORY_INFO.get(top, ("📁", ""))
            node = self.nav.insert("", "end", iid=top, text=f"{icon} {top}",
                                   values=(human_size(self.index.dir_info(top)["size"]),
                                           f"{self.index.dir_info(top)['count']} 文件"),
                                   tags=("top",), open=False)
            self.nav.insert(node, "end", iid=f"{top}/__placeholder__", text="…")
        for f in root_files:
            if f.startswith("."):
                continue
            e = self.index.files.get(f)
            if not e:
                continue
            self.nav.insert("", "end", iid=f, text=f"📄 {f}",
                            values=(human_size(e.size), ""), tags=("file",))
        self.nav_hint.configure(text="提示：展开分类找字典；不确定用哪个就打开「使用引导」。")

    def _on_nav_open(self, _event=None):
        iid = self.nav.focus()
        if not iid:
            return
        self._populate_nav_node(iid)

    def _populate_nav_node(self, rel: str):
        if rel in self._nav_populated or rel not in self.index.dirs:
            return
        self._nav_populated.add(rel)
        placeholder = f"{rel}/__placeholder__" if rel else "__placeholder__"
        if self.nav.exists(placeholder):
            self.nav.delete(placeholder)
        subdirs, files = self.index.children(rel)
        for d in subdirs:
            info = self.index.dir_info(d)
            node = self.nav.insert(rel, "end", iid=d, text=f"📁 {d.rsplit('/', 1)[-1]}",
                                   values=(human_size(info["size"]), f"{info['count']} 文件"),
                                   tags=("dir",))
            self.nav.insert(node, "end", iid=f"{d}/__placeholder__", text="…")
        for f in files:
            e = self.index.files.get(f)
            if not e:
                continue
            self.nav.insert(rel, "end", iid=f, text=f"  {e.name}",
                            values=(human_size(e.size), ""), tags=("file",))

    def _on_nav_select(self, _event=None):
        sel = self.nav.selection()
        if not sel:
            return
        rel = sel[0]
        if rel.endswith("__placeholder__") or rel in ("__placeholder__",):
            return
        if rel in self.index.dirs:
            info = self.index.dir_info(rel)
            self.scope_rel = rel
            self.scope_var.set(f"当前目录：{rel or '仓库根'}")
            icon, desc = CATEGORY_INFO.get(rel.split("/")[0], ("📁", ""))
            self.nav_hint.configure(
                text=f"{rel}\n{human_size(info['size'])} · {info['count']} 个文件\n{desc}")
            self.current_entry = None
        elif rel in self.index.files:
            self.current_entry = self.index.files[rel]
            self._update_preview_info()

    def _on_nav_double(self, _event=None):
        sel = self.nav.selection()
        if not sel:
            return
        rel = sel[0]
        if rel in self.index.files:
            self._preview_rel(rel)
        elif rel in self.index.dirs:
            self.nav.item(rel, open=not self.nav.item(rel, "open"))
            self._populate_nav_node(rel)

    def _on_nav_menu(self, event):
        row = self.nav.identify_row(event.y)
        if row:
            self.nav.selection_set(row)
            try:
                self.nav_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.nav_menu.grab_release()

    def _on_nav_filter(self, _event=None):
        if self._nav_filter_job:
            self.after_cancel(self._nav_filter_job)
        self._nav_filter_job = self.after(250, self._apply_nav_filter)

    def _apply_nav_filter(self):
        query = self.nav_filter.get().strip()
        if not query:
            self._fill_nav()
            return
        results = self.index.search_names(query, limit=800)
        self.nav.delete(*self.nav.get_children())
        node = self.nav.insert("", "end", iid="__results__",
                               text=f"🔎 文件名包含 “{query}” 的文件（{len(results)}）",
                               tags=("top",), open=True)
        for e in results:
            parent = e.rel.rsplit("/", 1)[0] if "/" in e.rel else ""
            self.nav.insert(node, "end", iid=e.rel, text=f"  {e.name}",
                            values=(human_size(e.size), ""), tags=("file",))
            _ = parent
        if not results:
            self.nav.insert(node, "end", iid="__none__", text="  （没有匹配的文件）")

    # ================================================================ 路径工具
    def _abs(self, rel: str) -> str:
        return os.path.join(self.root_dir, rel.replace("/", os.sep))

    def _style_key(self) -> str:
        for label, key in STYLE_LABELS:
            if label == self.style_var.get():
                return key
        return "local"

    def _path_for(self, rel: str, style: str | None = None) -> str:
        return render_path(rel, style or self._style_key(), self.root_dir)

    def _copy_path(self, rel: str):
        text = self._path_for(rel)
        self._clip(text)
        self.status_var.set(f"已复制路径：{text}")

    def _copy_current_path(self, style: str):
        if not self.current_entry:
            self._info("提示", "请先在左侧选择一个文件。")
            return
        text = self._path_for(self.current_entry.rel, style)
        self._clip(text)
        self.status_var.set(f"已复制路径：{text}")

    def _clip(self, text: str):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update_idletasks()

    def _copy_view(self, view: CodeView, what: str = "内容"):
        self._clip(view.get_text())
        self.status_var.set(f"已复制{what}到剪贴板")

    def _spawn(self, argv) -> bool:
        """启动一个外部程序；成功启动返回 True。"""
        try:
            subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             stdin=subprocess.DEVNULL, start_new_session=True)
            return True
        except (OSError, ValueError):
            return False

    def _file_manager_show(self, path: str) -> bool:
        """优先用 FileManager1 在文件管理器里「选中」该文件（GNOME/KDE/Nautilus 支持）。"""
        if not shutil.which("dbus-send"):
            return False
        uri = "file://" + urllib.parse.quote(os.path.abspath(path))
        try:
            rc = subprocess.run(
                ["dbus-send", "--session", "--dest=org.freedesktop.FileManager1",
                 "--type=method_call", "/org/freedesktop/FileManager1",
                 "org.freedesktop.FileManager1.ShowItems", f"array:string:{uri}", "string:"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3).returncode
            return rc == 0
        except Exception:  # noqa: BLE001
            return False

    def _reveal(self, path: str):
        if not path or not os.path.exists(path):
            self._info("提示", "路径不存在。")
            return
        target = os.path.normpath(path)
        if os.path.isfile(target) and self._file_manager_show(target):
            return
        folder = target if os.path.isdir(target) else os.path.dirname(target)
        for argv in (["xdg-open", folder], ["gio", "open", folder], ["nautilus", folder],
                     ["dolphin", folder], ["thunar", folder], ["pcmanfm", folder]):
            if shutil.which(argv[0]) and self._spawn(argv):
                return
        self._error("打开失败",
                    f"没有找到可用的文件管理器（xdg-open 等）。\n目录：{folder}")

    def _notepad(self, path: str):
        """用系统默认编辑器打开文件（xdg-open 优先，其次常见 GUI 编辑器）。"""
        if not path or not os.path.exists(path):
            self._info("提示", "文件不存在。")
            return
        target = os.path.normpath(path)
        for argv in (["xdg-open", target], ["gedit", target], ["kate", target],
                     ["mousepad", target], ["leafpad", target], ["code", target]):
            if shutil.which(argv[0]) and self._spawn(argv):
                return
        editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or "nano"
        self._run_in_terminal(f"{editor} {shlex.quote(target)}", "编辑器")

    def _run_in_terminal(self, cmd_text: str, tool: str = "") -> None:
        """Linux 版特有：把命令写成临时脚本，在新开的终端窗口里执行（执行前需要确认）。"""
        cmd_text = (cmd_text or "").strip()
        if not cmd_text:
            return
        preview = cmd_text if len(cmd_text) <= 600 else cmd_text[:600] + " …"
        if not self._confirm(
                "在终端中运行",
                f"{tool}\n\n将执行：\n\n{preview}\n\n"
                "请确认该目标在你的授权范围内。继续？"):
            return
        runner = os.path.join(self.data_dir, "run-command.sh")
        marker = "SECLISTS_GUI_CMD_EOF"
        try:
            with open(runner, "w", encoding="utf-8", newline="\n") as fh:
                fh.write("#!/usr/bin/env bash\n"
                         "# 由 SecLists 助手生成；可自行查看、修改、复制到别处执行\n"
                         "echo '── 本次执行的命令 ──'\n"
                         f"cat <<'{marker}'\n{cmd_text}\n{marker}\n"
                         "echo '──────────────────────'\n"
                         f"{cmd_text}\n"
                         "rc=$?\n"
                         "echo\necho \"[退出码 $rc]\"\n")
        except OSError as exc:
            self._error("写入脚本失败", str(exc))
            return
        inner = f"bash {shlex.quote(runner)}; echo; read -rp '按回车关闭窗口…' _"
        terminals = (
            ("x-terminal-emulator", ["x-terminal-emulator", "-e", "bash", "-lc", inner]),
            ("gnome-terminal", ["gnome-terminal", "--", "bash", "-lc", inner]),
            ("konsole", ["konsole", "-e", "bash", "-lc", inner]),
            ("xfce4-terminal", ["xfce4-terminal", "--command", f"bash -lc {shlex.quote(inner)}"]),
            ("mate-terminal", ["mate-terminal", "--", "bash", "-lc", inner]),
            ("tilix", ["tilix", "-e", "bash", "-lc", inner]),
            ("kitty", ["kitty", "bash", "-lc", inner]),
            ("alacritty", ["alacritty", "-e", "bash", "-lc", inner]),
            ("wezterm", ["wezterm", "start", "--", "bash", "-lc", inner]),
            ("xterm", ["xterm", "-e", "bash", "-lc", inner]),
        )
        for name, argv in terminals:
            if shutil.which(name) and self._spawn(argv):
                self.status_var.set(f"已在终端中启动（{name}）：{tool or '命令'}")
                return
        self._error("没有找到终端模拟器",
                    "未检测到可用终端（gnome-terminal / konsole / xfce4-terminal / xterm …）。\n\n"
                    f"命令已保存到：\n{runner}\n\n可手动执行：bash {runner}")

    def _locate_rel(self, rel: str):
        if rel in self.index.files:
            self._reveal(self._abs(rel))
        else:
            rel_dir = rel.rstrip("/")
            target = self._abs(rel_dir) if rel_dir else self.root_dir
            self._reveal(target)

    # ================================================================ 导航动作
    def _nav_selected_rel(self) -> str | None:
        sel = self.nav.selection()
        return sel[0] if sel else None

    def _nav_action_preview(self):
        rel = self._nav_selected_rel()
        if rel and rel in self.index.files:
            self._preview_rel(rel)

    def _nav_action_copy(self, style: str):
        rel = self._nav_selected_rel()
        if rel and (rel in self.index.files or rel in self.index.dirs):
            self._copy_path(rel)

    def _nav_action_reveal(self):
        rel = self._nav_selected_rel()
        if not rel:
            return
        self._reveal(self._abs(rel) if rel in self.index.files else self._abs(rel.rstrip("/")))

    def _nav_action_notepad(self):
        rel = self._nav_selected_rel()
        if rel and rel in self.index.files:
            self._notepad(self._abs(rel))

    def _nav_action_toolbox(self):
        rel = self._nav_selected_rel()
        if rel and rel in self.index.files:
            if self._abs(rel) not in self._tool_files:
                self._tool_files.append(self._abs(rel))
                self.tool_list.insert("end", rel)
                self._update_tool_hint()
            self.nb.select(3)

    def _nav_action_count_dir(self):
        rel = self._nav_selected_rel()
        if not rel:
            return
        if rel in self.index.files:
            self._count_current()
            return
        if self.busy["lines"]:
            self._info("提示", "已有统计任务在运行。")
            return
        self.busy["lines"] = True
        self.cancel_lines.clear()
        self.status_var.set(f"正在统计 {rel} 的行数…")

        def worker():
            total, files = self.index.count_lines_dir(
                rel, cancel=self.cancel_lines,
                progress=lambda i, n, name: self.q.put(
                    {"kind": "progress", "value": i, "max": n, "text": f"统计 {i}/{n}"}))
            self.q.put({"kind": "lines_dir_done", "total": total, "files": files, "rel": rel})

        threading.Thread(target=worker, daemon=True).start()

    # ================================================================ 预览
    def _preview_rel(self, rel: str, jump_line: int | None = None, highlight: str = ""):
        if rel in self.index.dirs or rel.rstrip("/") in self.index.dirs:
            self.nb.select(2)
            return
        entry = self.index.files.get(rel)
        if not entry:
            self._info("提示", f"本机仓库中没有找到：{rel}")
            return
        self.current_entry = entry
        self._load_preview(entry, jump_line=jump_line, highlight=highlight)
        self.nb.select(1)

    def _update_preview_info(self, lines: int | None = None, enc: str = ""):
        e = self.current_entry
        if not e:
            self.preview_info_var.set("在左侧双击任意字典文件即可预览")
            return
        cached = self.index.cache.get(e.rel, e.size, e.mtime)
        line_txt = human_int(lines if lines is not None else cached) if (
            lines is not None or cached is not None) else "未统计"
        self.preview_info_var.set(
            f"文件：{e.rel}\n大小：{human_size(e.size)}   行数：{line_txt}   "
            f"编码：{enc or '—'}   修改时间：{time.strftime('%Y-%m-%d %H:%M', time.localtime(e.mtime))}\n"
            f"本机路径：{e.path}")

    def _reload_preview(self):
        if self.current_entry:
            self._load_preview(self.current_entry)

    def _load_preview(self, entry: FileEntry, jump_line: int | None = None, highlight: str = ""):
        limit = _limit_value(self.preview_limit_var.get())
        if jump_line and jump_line > limit:
            limit = min(max(jump_line + 100, limit), 200000)
        enc_choice = self.preview_enc_var.get()
        enc = "auto" if enc_choice == "自动识别" else enc_choice
        t0 = time.time()
        lines, used_enc, truncated = self.index.read_lines(entry, limit=limit, encoding=enc)
        dt = (time.time() - t0) * 1000
        self.preview_view.set_lines(lines, start=1, gutter_on=not self.wrap_var.get())
        self._update_preview_info(enc=used_enc)
        tail = f"，仅显示前 {len(lines)} 行（文件更大）" if truncated else ""
        self.status_var.set(f"已加载 {entry.rel} 的 {len(lines)} 行，耗时 {dt:.0f} ms{tail}")
        if highlight:
            self.preview_view.highlight(highlight)
        if jump_line:
            self.preview_view.see_line(jump_line)
            self.preview_view.text.tag_add("sel", f"{jump_line}.0", f"{jump_line}.end")

    def _find_in_preview(self):
        needle = self.preview_find.get().strip()
        if not needle:
            return
        hits = self.preview_view.highlight(needle)
        self.status_var.set(f"在当前预览中高亮 {hits} 处匹配（仅限已加载的行）")

    def _copy_preview_all(self):
        if not self.current_entry:
            return
        if self.current_entry.size > 8 * 1024 * 1024:
            if not self._confirm(
                    "确认", f"该文件 {human_size(self.current_entry.size)}，"
                            f"复制全部内容相当于加载整个文件，可能卡顿。继续？"):
                return
        text = self.index.head_bytes(self.current_entry, max_bytes=64 << 20,
                                     encoding="auto" if self.preview_enc_var.get() == "自动识别"
                                     else self.preview_enc_var.get())
        self._clip(text)
        self.status_var.set(f"已复制 {self.current_entry.rel} 的全文（{human_size(len(text))} 字符）")

    def _count_current(self):
        if not self.current_entry:
            self._info("提示", "请先选择一个文件。")
            return
        if self.busy["lines"]:
            self._info("提示", "已有统计任务在运行。")
            return
        self.busy["lines"] = True
        entry = self.current_entry

        def worker():
            lines = self.index.count_lines(entry)
            self.q.put({"kind": "lines_done", "entry": entry, "lines": lines})

        threading.Thread(target=worker, daemon=True).start()
        self.status_var.set(f"正在统计 {entry.rel} 的行数…")

    def _save_preview_as(self):
        if not self.current_entry:
            return
        default = os.path.join(self.out_dir, self.current_entry.name)
        path = filedialog.asksaveasfilename(initialdir=self.out_dir,
                                            initialfile=os.path.basename(default),
                                            defaultextension=".txt")
        if not path:
            return
        text = self.preview_view.get_text()
        save_text(path, text.split("\n"))
        self.status_var.set(f"已另存为：{path}")

    def _search_in_current(self):
        if not self.current_entry:
            return
        self.search_mode.set("content")
        self.search_scope.set("scope")
        self.scope_rel = self.current_entry.rel
        self.scope_var.set(f"当前目录：{self.current_entry.rel}")
        self.nb.select(2)
        self.search_entry.focus_set()
        self.status_var.set("已把搜索范围切到当前文件，输入关键字后回车即可。")

    # ================================================================ 搜索
    def _start_search(self):
        if self.busy["search"]:
            return
        query = self.search_entry.get().strip()
        if not query:
            self._info("提示", "请输入要搜索的关键字。")
            return
        mode = self.search_mode.get()
        self.results.delete(*self.results.get_children())
        self._result_map.clear()

        if mode == "name":
            results = self.index.search_names(query, use_regex=self.search_regex.get(),
                                              case_sensitive=self.search_case.get(),
                                              text_only=False, limit=3000)
            node_map = {}
            for e in results:
                parent = e.rel.rsplit("/", 1)[0] if "/" in e.rel else "（仓库根）"
                if parent not in node_map:
                    node_map[parent] = self.results.insert("", "end", iid=f"d:{parent}",
                                                           text=f"📁 {parent}", open=True,
                                                           tags=("file",))
                iid = f"n:{e.rel}"
                self.results.insert(node_map[parent], "end", iid=iid, text=f"  {e.name}",
                                    values=("", human_size(e.size)))
                self._result_map[iid] = (e.rel, None)
            self.search_status_var.set(f"文件名匹配 {len(results)} 个文件")
            return

        root = self.scope_rel if self.search_scope.get() == "scope" else ""
        entries = [e for e in self.index.iter_files(root, text_only=self.search_textonly.get())]
        if not entries:
            self.search_status_var.set("该范围内没有可搜索的文本文件")
            return
        self.busy["search"] = True
        self.cancel_search.clear()
        self.search_btn.configure(state="disabled")
        self.search_stop_btn.configure(state="normal")
        self.search_progress.configure(maximum=len(entries), value=0)
        self.search_status_var.set(f"正在搜索 {len(entries)} 个文件…")
        self._search_file_nodes: dict[str, str] = {}
        self._search_hits = 0

        try:
            max_mb = int(self.search_maxmb.get())
        except ValueError:
            max_mb = 64
        try:
            per_file = int(self.search_perfile.get())
        except ValueError:
            per_file = 40
        # Tk 变量只能在主线程读取；先把取值固定下来再交给后台线程
        use_regex = bool(self.search_regex.get())
        case_sensitive = bool(self.search_case.get())
        cancel = self.cancel_search

        def worker():
            try:
                for entry, hits in self.index.search_content(
                        entries, query, use_regex=use_regex,
                        case_sensitive=case_sensitive, max_file_mb=max_mb,
                        per_file_hits=per_file, cancel=cancel,
                        progress=lambda i, n, h: self.q.put(
                            {"kind": "search_progress", "value": i, "max": n, "hits": h})):
                    self.q.put({"kind": "search_file", "entry": entry, "hits": hits})
            except ValueError as exc:
                self.q.put({"kind": "error", "msg": str(exc)})
            except Exception as exc:  # noqa: BLE001
                import traceback

                traceback.print_exc()
                self.q.put({"kind": "error", "msg": f"搜索出错：{exc}"})
            finally:
                self.q.put({"kind": "search_done"})

        threading.Thread(target=worker, daemon=True).start()

    def _stop_search(self):
        self.cancel_search.set()
        self.search_status_var.set("正在停止…")

    def _on_search_file(self, entry: FileEntry, hits):
        parent = entry.rel.rsplit("/", 1)[0] if "/" in entry.rel else "（仓库根）"
        if parent not in self._search_file_nodes:
            self._search_file_nodes[parent] = self.results.insert(
                "", "end", iid=f"d:{parent}", text=f"📁 {parent}", open=True, tags=("file",))
        iid = f"f:{entry.rel}"
        node = self.results.insert(self._search_file_nodes[parent], "end", iid=iid,
                                   text=f"  {entry.name} — {len(hits)} 处命中",
                                   values=("", human_size(entry.size)))
        self._result_map[iid] = (entry.rel, None)
        for lineno, text in hits:
            child = self.results.insert(node, "end", iid=f"{iid}#{lineno}",
                                        text="", values=(lineno, text))
            self._result_map[child] = (entry.rel, lineno)
        self._search_hits += len(hits)
        self.search_status_var.set(f"命中 {self._search_hits} 处…")

    def _on_result_open(self, _event=None):
        sel = self.results.selection()
        if not sel:
            return
        info = self._result_map.get(sel[0])
        if not info:
            return
        rel, lineno = info
        self._preview_rel(rel, jump_line=lineno, highlight=self.search_entry.get().strip())

    def _export_results(self):
        if not self._result_map:
            self._info("提示", "还没有搜索结果可导出。")
            return
        path = filedialog.asksaveasfilename(initialdir=self.out_dir, initialfile="search-results.tsv",
                                            defaultextension=".tsv")
        if not path:
            return
        rows = []
        for iid, (rel, lineno) in self._result_map.items():
            values = self.results.item(iid, "values")
            content = values[1] if len(values) > 1 else ""
            rows.append(f"{rel}\t{lineno if lineno else ''}\t{content}")
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("文件\t行号\t内容\n")
            fh.write("\n".join(rows) + "\n")
        self.status_var.set(f"搜索结果已导出：{path}")
        self._info("完成", f"已导出 {len(rows)} 条到\n{path}")

    # ================================================================ 工具箱
    def _update_tool_hint(self):
        total = 0
        for p in self._tool_files:
            try:
                total += os.path.getsize(p)
            except OSError:
                pass
        self.tool_hint.configure(
            text=f"已选择 {len(self._tool_files)} 个文件 · 合计 {human_size(total)}"
                 + ("（体量较大，去重/排序可能占用较多内存）" if total > 200 * 1024 * 1024 else ""))

    def _tool_add_files(self):
        paths = filedialog.askopenfilenames(initialdir=self.root_dir,
                                            title="选择要处理的字典文件")
        for p in paths:
            if p not in self._tool_files:
                self._tool_files.append(p)
                self.tool_list.insert("end", os.path.relpath(p, self.root_dir).replace("\\", "/"))
        self._update_tool_hint()

    def _tool_add_selected(self):
        sel = self.nav.selection()
        if not sel:
            self._info("提示", "请先在左侧导航选择文件（可按住 Ctrl 多选）。")
            return
        added = 0
        for rel in sel:
            if rel in self.index.files:
                p = self.index.files[rel].path
                if p not in self._tool_files:
                    self._tool_files.append(p)
                    self.tool_list.insert("end", rel)
                    added += 1
        self._update_tool_hint()
        if added:
            self.status_var.set(f"已加入工具箱 {added} 个文件")
        else:
            self._info("提示", "左侧选中的是目录。请在目录下选择具体文件；"
                               "或直接用「添加文件…」。")

    def _tool_remove(self):
        for idx in sorted(self.tool_list.curselection(), reverse=True):
            self.tool_list.delete(idx)
            del self._tool_files[idx]
        self._update_tool_hint()

    def _tool_clear(self):
        self.tool_list.delete(0, "end")
        self._tool_files.clear()
        self._update_tool_hint()

    def _tool_opts_dict(self) -> dict:
        opts = {k: v.get() for k, v in self.tool_opts.items()}
        for key, var in (("min_len", self.tool_min), ("max_len", self.tool_max),
                         ("include", self.tool_inc), ("exclude", self.tool_exc),
                         ("regex", self.tool_rx), ("head", self.tool_head)):
            opts[key] = var.get().strip()
        return opts

    def _run_tool(self, save: bool = False):
        if self.busy["tool"]:
            return
        if not self._tool_files:
            self._info("提示", "请先添加要处理的字典文件。")
            return
        opts = self._tool_opts_dict()
        out_path = None
        if save:
            default = "processed-" + time.strftime("%Y%m%d-%H%M%S") + ".txt"
            path = filedialog.asksaveasfilename(initialdir=self.out_dir, initialfile=default,
                                                defaultextension=".txt")
            if not path:
                return
            out_path = path
        self.busy["tool"] = True
        self.cancel_tool.clear()
        self.tool_stop_btn.configure(state="normal")
        self.tool_progress.configure(maximum=max(len(self._tool_files), 1), value=0)
        self.tool_status_var.set("正在处理…")
        files = list(self._tool_files)

        def worker():
            try:
                preview, stats = self.index.process_files(
                    files, opts, out_path=out_path, preview_limit=300, cancel=self.cancel_tool,
                    progress=lambda name, written: self.q.put(
                        {"kind": "tool_progress", "text": f"处理 {name}（已写 {human_int(written)} 行）"}))
                self.q.put({"kind": "tool_done", "preview": preview, "stats": stats,
                            "out": out_path})
            except Exception as exc:  # noqa: BLE001
                self.q.put({"kind": "error", "msg": f"处理失败：{exc}"})

        threading.Thread(target=worker, daemon=True).start()

    def _stop_tool(self):
        self.cancel_tool.set()
        self.tool_status_var.set("正在停止…")

    # ================================================================ 队列轮询
    def _poll_queue(self):
        if self._closing:
            return
        try:
            while True:
                msg = self.q.get_nowait()
                self._handle_message(msg)
        except queue.Empty:
            pass
        if not self._closing:
            self._poll_id = self.after(90, self._poll_queue)

    def _handle_message(self, msg: dict):
        kind = msg.get("kind")
        if kind == "scan_progress":
            self.status_var.set(f"正在扫描：已发现 {human_int(msg['n'])} 个文件（{msg['rel'][:80]}）")
        elif kind == "scan_done":
            self._on_scan_done(msg["stats"])
        elif kind == "progress":
            self.progress.configure(maximum=msg["max"])
            self.progress_var.set(msg["value"])
            self.status_var.set(msg.get("text", ""))
        elif kind == "lines_done":
            self.progress_var.set(0)
            self.busy["lines"] = False
            self._update_preview_info(lines=msg["lines"])
            self.status_var.set(f"{msg['entry'].rel} 共 {human_int(msg['lines'])} 行")
        elif kind == "lines_dir_done":
            self.progress_var.set(0)
            self.busy["lines"] = False
            self.status_var.set(f"目录 {msg['rel']} 共 {human_int(msg['total'])} 行 / "
                                f"{msg['files']} 个文件")
            self._info("统计完成",
                       f"目录：{msg['rel']}\n文件数：{msg['files']}\n"
                       f"总行数：{human_int(msg['total'])}")
        elif kind == "search_progress":
            self.search_progress.configure(maximum=msg["max"])
            self.search_progress["value"] = msg["value"]
            self.search_status_var.set(f"已扫描 {msg['value']}/{msg['max']} 个文件，"
                                       f"命中 {msg['hits']} 处")
        elif kind == "search_file":
            self._on_search_file(msg["entry"], msg["hits"])
        elif kind == "search_done":
            self.busy["search"] = False
            self.search_btn.configure(state="normal")
            self.search_stop_btn.configure(state="disabled")
            stopped = "（已停止）" if self.cancel_search.is_set() else ""
            self.search_status_var.set(f"搜索结束{stopped}：共命中 {self._search_hits} 处。"
                                       f"双击结果可跳转到预览。")
            self.search_progress["value"] = 0
        elif kind == "tool_progress":
            self.tool_status_var.set(msg["text"])
            self.tool_progress["value"] = min(self.tool_progress["value"] + 1,
                                              self.tool_progress["maximum"])
        elif kind == "tool_done":
            self.busy["tool"] = False
            self.tool_stop_btn.configure(state="disabled")
            stats = msg["stats"]
            self.tool_progress["value"] = 0
            if msg.get("out"):
                self.tool_view.set_lines([f"# 已保存到：{msg['out']}"] +
                                         (msg["preview"] or [])[:300])
                self.tool_status_var.set(
                    f"已写出 {human_int(stats['out_lines'])} 行 → {os.path.basename(msg['out'])}")
                self._clip(msg["out"])
                self._info("完成",
                           f"已保存：{msg['out']}\n\n"
                           f"输入 {human_int(stats['in_lines'])} 行 → 输出 "
                           f"{human_int(stats['out_lines'])} 行（过滤掉 "
                           f"{human_int(stats['skipped'])} 行）\n路径已复制到剪贴板。")
            else:
                self.tool_view.set_lines(msg["preview"] or ["（没有输出，检查过滤条件）"])
                self.tool_status_var.set(
                    f"预览：{human_int(stats['out_lines'])} 行（已过滤 {human_int(stats['skipped'])} 行）")
        elif kind == "error":
            self._error("出错", msg["msg"])
            self.busy = {k: False for k in self.busy}
            self.search_btn.configure(state="normal")
            self.search_stop_btn.configure(state="disabled")
            self.tool_stop_btn.configure(state="disabled")

    # ================================================================ 其他
    def _on_target_changed(self):
        self._refresh_commands()

    def _refresh_commands(self):
        targets = derive_targets(self.target_var.get())
        if targets["host"]:
            self.derived_label.configure(
                text=f"解析 → host: {targets['host']}    domain: {targets['domain']}    "
                     f"url: {targets['url']}")
        else:
            self.derived_label.configure(text="未填目标时，命令里的 {url}/{host}/{domain} 会保留成占位符")
        style = self._style_key()
        for view, template, lists in self.cmd_views:
            text = render_command(template, lists, targets, style, self.root_dir)
            view.set_text(text)

    def _about(self):
        self._info(
            "关于",
            "SecLists 使用助手 v1.0（Linux 版）\n\n"
            "本地 Tkinter 图形界面：不监听端口、不联网、不修改 SecLists 原有文件。\n"
            f"仓库：{self.root_dir}\n"
            f"数据目录：{self.data_dir}\n"
            f"字体：{FONT_UI[0]} / {FONT_MONO[0]}\n\n"
            "功能：场景引导 / 字典预览 / 全库搜索 / 字典工具箱 / 速查手册。\n"
            "命令卡片支持「▶ 在终端运行」，会新开终端执行（WSL 需 WSLg 或 X server）。")

    def _on_close(self):
        self.destroy()

    def report_callback_exception(self, exc, val, tb):  # noqa: N802 (Tk 约定)
        """Tkinter 默认会把回调里的异常悄悄打到 stderr；.pyw 下用户看不到，这里显式提示。"""
        import traceback

        text = "".join(traceback.format_exception(exc, val, tb))
        try:
            sys.stderr.write(text)
        except Exception:
            pass
        if self.headless:
            print("[callback-error] " + text.replace("\n", " | ")[:400], flush=True)
            return
        try:
            self.status_var.set(f"界面回调出错：{val}")
        except Exception:
            pass

    def destroy(self):
        self._closing = True
        if self._poll_id:
            try:
                self.after_cancel(self._poll_id)
            except Exception:
                pass
            self._poll_id = None
        try:
            self.index.cache.save(force=True)
        except Exception:
            pass
        try:
            super().destroy()
        except Exception:
            pass

    # ================================================================ 弹窗收口
    # 自检（无人应答）时不能弹模态框，否则会永久阻塞；统一走这几个入口。
    def _info(self, title: str, msg: str) -> None:
        if self.headless:
            print(f"[info] {title}: {msg}", flush=True)
            self.status_var.set(msg.splitlines()[0] if msg else title)
            return
        messagebox.showinfo(title, msg)

    def _error(self, title: str, msg: str) -> None:
        if self.headless:
            print(f"[error] {title}: {msg}", flush=True)
            self.status_var.set(f"{title}：{msg.splitlines()[0]}")
            return
        messagebox.showerror(title, msg)

    def _confirm(self, title: str, msg: str) -> bool:
        if self.headless:
            print(f"[confirm:auto-yes] {title}: {msg}", flush=True)
            return True
        return messagebox.askyesno(title, msg)

    # ================================================================ 自检
    def _say(self, bucket: list, line: str) -> None:
        """收集自检结论；无头模式下同时打印，便于定位卡在哪一步。"""
        bucket.append(line)
        if self.headless:
            print(line, flush=True)

    def _wait_for_scan(self, timeout: float = 180.0) -> bool:
        """等索引扫描完成。

        注意：扫描是由 after(120, ...) 触发的，自检开始得比它早时 busy["scan"] 还是
        False，直接判「已完成」会拿到空索引 —— 所以先等它启动，必要时手动触发一次。
        """
        start_deadline = time.time() + 5.0
        while (not self.busy["scan"] and not self.index.files
               and time.time() < start_deadline and not self._closing):
            try:
                self.update()
            except tk.TclError:
                return False
            time.sleep(0.02)
        if not self.busy["scan"] and not self.index.files:
            self._start_scan()
        deadline = time.time() + timeout
        while self.busy["scan"] and time.time() < deadline and not self._closing:
            try:
                self.update()
            except tk.TclError:
                return False
            time.sleep(0.03)
        return not self.busy["scan"] and bool(self.index.files)

    def _pump_until(self, predicate, timeout: float = 90.0) -> bool:
        """在自检里驱动事件循环，直到条件成立或超时。"""
        deadline = time.time() + timeout
        while time.time() < deadline and not self._closing:
            try:
                self.update()
            except tk.TclError:
                return False
            if predicate():
                return True
            time.sleep(0.02)
        return predicate()

    def selftest(self) -> tuple[bool, list[str]]:
        report: list[str] = []
        ok = True
        self.headless = True  # 自检无人应答：禁止弹模态框，否则会永久阻塞
        self.update_idletasks()
        self.update()
        if not self._wait_for_scan():
            return False, ["✗ 索引扫描超时"]
        stats = self.index.stats()
        self._say(report, f"索引：{stats['files']} 个文件 / {human_size(stats['size'])} / "
                      f"{len(stats['per_top'])} 个顶层分类")
        if stats["files"] < 1000:
            ok = False
            self._say(report, "✗ 文件数量异常偏少")

        missing = []
        for sc in SCENARIOS:
            for item in sc.get("lists", []):
                p = item["path"].rstrip("/")
                if p not in self.index.files and p not in self.index.dirs:
                    missing.append(f"{sc['id']} → {item['path']}")
        if missing:
            ok = False
            self._say(report, f"✗ 有 {len(missing)} 个场景字典路径不存在：")
            report.extend("    " + m for m in missing)
        else:
            self._say(report, f"✓ {sum(len(s.get('lists', [])) for s in SCENARIOS)} 个场景字典路径全部存在")

        groups = {g for g, _ in GROUPS}
        bad_groups = sorted({s["group"] for s in SCENARIOS} - groups)
        if bad_groups:
            ok = False
            self._say(report, f"✗ 未知分组：{bad_groups}")

        ids = [s["id"] for s in SCENARIOS]
        if len(ids) != len(set(ids)):
            ok = False
            self._say(report, "✗ 场景 id 有重复")

        self.target_var.set("https://demo.example.com/app?id=1")
        self.update()
        for sc in SCENARIOS:
            try:
                self._show_scenario(sc)
                self.update_idletasks()
            except Exception as exc:  # noqa: BLE001
                ok = False
                self._say(report, f"✗ 场景 {sc['id']} 详情渲染失败：{exc}")
        self._say(report, f"✓ {len(SCENARIOS)} 个场景详情均可渲染")
        if self.cmd_views:
            sample = self.cmd_views[0][0].get_text()
            self._say(report, f"  命令示例：{sample[:110]}")
        self._say(report, f"✓ 主题与字体：{FONT_UI[0]} / {FONT_MONO[0]}")

        # 预览与搜索的快速验证
        first = self.index.get("Discovery/Web-Content/quickhits.txt")
        if first is None and self.index.files:
            first = next(iter(self.index.files.values()))
        if first is None:
            ok = False
            self._say(report, "✗ 索引为空，无法验证预览/搜索（检查仓库路径是否可读）")
            self._say(report, f"  仓库路径：{self.root_dir}")
            report.extend(self._layout_report())
            return ok, report
        self._preview_rel(first.rel)
        self.update()
        loaded = len(self.preview_view.get_text().split("\n"))
        self._say(report, f"✓ 预览 {first.rel}：{loaded} 行")
        lines = self.index.count_lines(first)
        self._say(report, f"✓ 行数统计 {first.rel}：{human_int(lines)} 行")

        hit_count = 0
        for entry, hits in self.index.search_content([first], "admin", per_file_hits=5):
            hit_count += len(hits)
        self._say(report, f"✓ 内容搜索自检：quickhits 中含 'admin' 的 {hit_count} 处")

        # ---- 工具箱自检：去重 + 长度过滤 + 落盘
        wanted = ["Discovery/Web-Content/quickhits.txt", "Discovery/Web-Content/common.txt"]
        src = [self._abs(p) for p in wanted if p in self.index.files]
        if not src:
            src = [e.path for e in list(self.index.iter_files("Discovery/Web-Content",
                                                              text_only=True))[:2]]
        if src:
            opts = {"dedup": True, "sort": False, "skip_empty": True, "skip_comments": True,
                    "strip": True, "lower": False, "case_sensitive": False,
                    "min_len": "3", "max_len": "", "include": "", "exclude": "",
                    "regex": "", "head": ""}
            tmp_out = os.path.join(self.out_dir, "_selftest-output.txt")
            preview, stats = self.index.process_files(src, opts, out_path=tmp_out, preview_limit=0)
            exists = os.path.exists(tmp_out)
            size = os.path.getsize(tmp_out) if exists else 0
            written = 0
            if exists:
                with open(tmp_out, "r", encoding="utf-8", errors="replace") as fh:
                    written = sum(1 for _ in fh)
                try:
                    os.remove(tmp_out)
                except OSError:
                    pass
            self._say(report, f"✓ 工具箱自检：{len(src)} 个文件 输入 {human_int(stats['in_lines'])} 行 → "
                          f"输出 {human_int(stats['out_lines'])} 行（过滤 {human_int(stats['skipped'])} 行），"
                          f"落盘 {human_int(written)} 行 / {human_size(size)}")
            if stats["out_lines"] == 0 or written != stats["out_lines"] or stats["out_lines"] > stats["in_lines"]:
                ok = False
                self._say(report, "✗ 工具箱输出与落盘行数不一致")

        report.extend(self._layout_report())
        report.extend(self._async_report())
        return ok, report

    def _async_report(self) -> list[str]:
        """走完整 UI 链路（后台线程 + 队列 + 控件刷新）验证搜索与工具箱。"""
        out: list[str] = []
        # ---- 全库搜索（限定一个小目录，快速但走完整流程）
        scope = "Discovery/Variables" if "Discovery/Variables" in self.index.dirs else "Discovery"
        self.search_mode.set("content")
        self.search_scope.set("scope")
        self.scope_rel = scope
        self.search_textonly.set(True)
        self.search_entry.delete(0, "end")
        self.search_entry.insert(0, "key")
        self._start_search()
        finished = self._pump_until(lambda: not self.busy["search"], 120)
        rows = len(self._result_map)
        self._say(out, f"{'✓' if finished and rows else '✗'} 界面搜索链路：范围 {scope}，关键字 'key'，"
                   f"结果节点 {rows} 个，状态「{self.search_status_var.get()}」")
        if not finished or not rows:
            self._say(out, "    （搜索链路异常：未在超时内完成或没有结果）")

        # ---- 结果双击跳转到预览
        first_child = None
        for iid in list(self._result_map):
            if "#" in iid:
                first_child = iid
                break
        if first_child:
            self.results.selection_set(first_child)
            self._on_result_open()
            self.update()
            entry = self.current_entry.rel if self.current_entry else "—"
            self._say(out, f"✓ 搜索结果双击跳转：已打开 {entry}")

        # ---- 工具箱（界面按钮链路）
        src_rel = "Discovery/Web-Content/quickhits.txt"
        if src_rel in self.index.files:
            self._tool_files = [self._abs(src_rel)]
            self.tool_list.delete(0, "end")
            self.tool_list.insert("end", src_rel)
            self.tool_min.set("3")
            self._run_tool(save=False)
            done = self._pump_until(lambda: not self.busy["tool"], 120)
            text = self.tool_view.get_text()
            self._say(out, f"{'✓' if done and text else '✗'} 界面工具箱链路："
                       f"{self.tool_status_var.get()}，预览 {len(text.splitlines())} 行")
            if not done or not text:
                self._say(out, "    （工具箱链路异常：未完成或没有输出）")
        return out

    def _layout_report(self) -> list[str]:
        """逐个标签页实际排版后测量控件尺寸，用于无图形环境下确认布局正常。"""
        out: list[str] = []
        # 先回到用户打开界面时看到的那个场景，度量才有意义
        sel = self.guide_tree.selection()
        if sel and sel[0].startswith("s:"):
            sc = next((s for s in SCENARIOS if s["id"] == sel[0][2:]), None)
            if sc:
                self._show_scenario(sc)
        self.update_idletasks()
        self.update()
        try:
            self._set_sashes()
        except Exception:
            pass
        self.update_idletasks()
        self.update()
        checks = [
            ("左侧导航树", self.nav),
            ("标签页容器", self.nb),
            ("场景列表", self.guide_tree),
            ("场景详情容器", self.guide_scroll.canvas),
        ]
        bad: list[str] = []
        for name, widget in checks:
            w, h = widget.winfo_width(), widget.winfo_height()
            self._say(out, f"  {name}: {w}×{h}")
            if w < 40 or h < 20:
                bad.append(name)
        # 逐页切换后再测量（未选中的标签页 Tk 不会排版）
        tab_widgets = [
            ("字典预览 → 文本区", 1, lambda: self.preview_view.text),
            ("全库搜索 → 输入框", 2, lambda: self.search_entry),
            ("全库搜索 → 结果树", 2, lambda: self.results),
            ("字典工具箱 → 文件列表", 3, lambda: self.tool_list),
            ("字典工具箱 → 预览区", 3, lambda: self.tool_view.text),
            ("速查手册 → 文本区", 4, lambda: self.doc),
        ]
        for name, index, getter in tab_widgets:
            self.nb.select(index)
            self.update_idletasks()
            self.update()
            widget = getter()
            w, h = widget.winfo_width(), widget.winfo_height()
            self._say(out, f"  {name}: {w}×{h}")
            if w < 60 or h < 20:
                bad.append(name)
        self.nb.select(0)
        self.update_idletasks()
        self.update()
        anchor = getattr(self, "_cmd_anchor", None)
        if anchor is not None:
            try:
                y = anchor.winfo_y()
                height = max(self.guide_scroll.canvas.winfo_height(), 1)
                if y < height:
                    self._say(out, f"✓ 场景「{self.guide_tree.item(self.guide_tree.selection()[0], 'text').strip()}」"
                               f"的命令区在首屏内（y={y}px / 可视 {height}px）")
                else:
                    self._say(out, f"! 命令区在首屏下方 {y - height}px 处（可用「↓ 命令模板」跳转）")
            except Exception:
                pass
        tabs = [self.nb.tab(i, "text").strip() for i in range(self.nb.index("end"))]
        self._say(out, f" 标签页：{tabs}")
        self._say(out, f" 场景树节点数：{len(self.guide_tree.get_children())} 个分组 / "
                   f"{len(SCENARIOS)} 个场景")
        self._say(out, f" 导航树顶层节点：{len(self.nav.get_children())} 个")
        self._say(out, f" 详情面板子控件：{len(self.guide_scroll.body.winfo_children())} 个")
        try:
            from tkinter import font as tkfont

            ui_actual = tkfont.Font(font=self.doc.cget("font")).actual().get("family", "?")
            mono_actual = tkfont.Font(font=self.preview_view.text.cget("font")).actual().get("family", "?")
            same = str(ui_actual).lower() == str(FONT_UI[0]).lower()
            out.append(f" 实际字体：界面 {ui_actual} / 等宽 {mono_actual}"
                       + ("（与请求一致 ✓）" if same else f"（请求 {FONT_UI[0]}，Tk 已回退 !）"))
        except Exception as exc:  # noqa: BLE001
            out.append(f" 字体解析检查跳过：{exc}")
        if bad:            self._say(out, f"✗ 以下控件尺寸异常：{bad}")
        else:
            self._say(out, "✓ 各区域尺寸正常（含各标签页实际排版）")
        return out


def launch_capture(root_dir: str, data_dir: str, out_dir: str) -> int:
    """开发用（配合 Xvfb）：等索引完成后再逐个标签页截图，避免截到「还在扫描」的中间态。

    依赖 xwd（x11-apps）。每张图对应一个标签页，文件名 tab<N>-<名字>.xwd。
    """
    app = SecListsApp(root_dir, data_dir)
    os.makedirs(out_dir, exist_ok=True)
    names = ["guide", "preview", "search", "toolbox", "cheatsheet"]
    state = {"i": 0, "waited": 0.0, "shot": 0}

    def fail_no_xwd() -> None:
        print("[capture] 找不到 xwd，请先安装 x11-apps：sudo apt install x11-apps", flush=True)
        app.destroy()

    if not shutil.which("xwd"):
        app.after(100, fail_no_xwd)
        app.mainloop()
        return 1

    def pump() -> None:
        if app.busy["scan"] or not app.index.files:
            state["waited"] += 0.25
            if state["waited"] > 180:
                print("[capture] 索引等待超时，按当前状态继续截图", flush=True)
            else:
                app.after(250, pump)
                return
        index = state["i"]
        if index >= len(names):
            print(f"[capture] 完成：{state['shot']}/{len(names)} 张 → {out_dir}", flush=True)
            app.destroy()
            return
        app.nb.select(index)
        for _ in range(3):
            app.update_idletasks()
            app.update()
            time.sleep(0.15)
        path = os.path.join(out_dir, f"tab{index}-{names[index]}.xwd")
        try:
            subprocess.run(["xwd", "-id", str(app.winfo_id()), "-silent", "-out", path],
                           check=True, timeout=60)
            if os.path.exists(path):
                state["shot"] += 1
            print(f"[capture] tab{index} ({names[index]}) -> {path}", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[capture] tab{index} 截图失败：{exc}", flush=True)
        state["i"] += 1
        app.after(400, pump)

    app.after(300, pump)
    app.mainloop()
    return 0

def launch(root_dir: str, data_dir: str, selftest: bool = False, initial_tab: int = 0) -> int:
    app = SecListsApp(root_dir, data_dir)
    if initial_tab and 0 <= initial_tab < 5:
        app.after(500, lambda: app.nb.select(initial_tab))
    if selftest:
        try:
            ok, report = app.selftest()
        except BaseException as exc:  # noqa: BLE001
            import traceback

            app.destroy()
            print("自检过程中出错：")
            traceback.print_exc()
            return 1
        app.destroy()
        print("=" * 68)
        print("SecLists 助手自检报告")
        print("=" * 68)
        for line in report:
            print(line)
        print("=" * 68)
        print("结果：" + ("全部通过 ✅" if ok else "存在问题 ❌"))
        return 0 if ok else 1
    try:
        app.mainloop()
    finally:
        app.destroy()
    return 0
