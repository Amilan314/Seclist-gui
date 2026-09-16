# -*- coding: utf-8 -*-
"""SecLists 使用助手启动入口。

用法：
    双击本文件（或运行同目录的「启动SecLists助手.cmd」）即可打开图形界面。
    命令行自检：python SecListsAssistant.pyw --selftest
"""

from __future__ import annotations

import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

DATA_DIR = os.path.join(HERE, "data")


def find_repo_root() -> str:
    """定位 SecLists 仓库根目录。"""
    candidates = []
    env = os.environ.get("SECLISTS_ROOT")
    if env:
        candidates.append(env)
    candidates.append(os.path.dirname(HERE))
    for cand in candidates:
        if not cand:
            continue
        if os.path.isdir(os.path.join(cand, "Discovery")) and \
                os.path.isdir(os.path.join(cand, "Passwords")):
            return os.path.abspath(cand)
    cur = os.path.dirname(HERE)
    for _ in range(4):
        if os.path.isdir(os.path.join(cur, "Discovery")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return os.path.dirname(HERE)


def report_crash(exc: BaseException, gui: bool = True) -> None:
    text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(os.path.join(DATA_DIR, "error.log"), "a", encoding="utf-8") as fh:
            fh.write(text + "\n" + "-" * 60 + "\n")
    except Exception:
        pass
    if not gui:
        print(text, file=sys.stderr)
        return
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("SecLists 助手启动失败",
                             f"{exc}\n\n详细信息已写入：\n{DATA_DIR}\\error.log")
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
    try:
        initial_tab = int(_arg_value("--tab", "0"))
    except ValueError:
        initial_tab = 0
    root_dir = find_repo_root()
    try:
        from slgui.theme import enable_dpi_awareness
        from slgui.app import launch

        enable_dpi_awareness()
        return launch(root_dir, DATA_DIR, selftest=selftest, initial_tab=initial_tab)
    except BaseException as exc:  # noqa: BLE001
        report_crash(exc, gui=not selftest)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
