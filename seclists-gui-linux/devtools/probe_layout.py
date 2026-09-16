#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""开发辅助：把「使用引导」页面在启动状态下的真实几何量出来。

用途：确认字典卡片、命令框是否真的渲染出来了（命令框背景色是 code_bg，
在截图里数不到该颜色时，用它区分「被滚动到折叠线以下」和「根本没渲染」。

用法： python3 devtools/probe_layout.py [仓库根目录]
"""

from __future__ import annotations

import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(HERE)
sys.path.insert(0, APP_DIR)
os.environ.setdefault("SECLISTS_GUI_DATA", os.path.join(APP_DIR, "data-probe"))

from slgui.app import SecListsApp  # noqa: E402
from slgui.theme import COLORS  # noqa: E402


def main() -> int:
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(APP_DIR)
    app = SecListsApp(root, os.environ["SECLISTS_GUI_DATA"])
    app.headless = True
    deadline = time.time() + 120
    while time.time() < deadline and not app.index.files:
        app.update()
        time.sleep(0.02)
    while app.busy["scan"] and time.time() < deadline:
        app.update()
        time.sleep(0.02)
    for _ in range(5):
        app.update()
        time.sleep(0.05)

    canvas = app.guide_scroll.canvas
    print(f"仓库        : {app.root_dir}")
    print(f"索引文件数  : {len(app.index.files)}")
    print(f"详情画布    : {canvas.winfo_width()}×{canvas.winfo_height()}"
          f"   scrollregion={canvas.cget('scrollregion')}")
    print(f"当前场景    : {app.guide_tree.item(app.guide_tree.selection()[0], 'text').strip()}"
          if app.guide_tree.selection() else "当前场景    : （未选中）")
    print("详情面板子控件（自上而下）:")
    for child in app.guide_scroll.body.winfo_children():
        label = ""
        try:
            label = str(child.cget("text"))[:48]
        except Exception:
            kids = [g for g in child.winfo_children() if g.winfo_class() == "TLabel"]
            if kids:
                label = str(kids[0].cget("text"))[:48]
        print(f"  {child.winfo_class():<10} y={child.winfo_y():<5} h={child.winfo_height():<5} "
              f"w={child.winfo_width():<5} {label}")

    print(f"命令视图数量: {len(app.cmd_views)}  (code_bg={COLORS['code_bg']})")
    for view, _template, _lists in app.cmd_views[:4]:
        text = view.text
        print(f"  命令框文本区: {text.winfo_width()}×{text.winfo_height()} "
              f"mapped={bool(text.winfo_ismapped())} | {view.get_text()[:70]}")
    app.destroy()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
