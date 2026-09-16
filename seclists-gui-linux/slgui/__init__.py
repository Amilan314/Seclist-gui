# -*- coding: utf-8 -*-
"""SecLists 使用助手（Linux 版）—— 本地图形界面，不监听端口。

包结构：
    theme.py    配色、Linux 字体挑选与 ttk 主题
    indexer.py  SecLists 仓库索引、行数缓存、预览与内容搜索、字典工具箱
    catalog.py  分类说明、场景引导数据、命令模板、速查手册（与 Windows 版同源）
    app.py      Tkinter 主窗口（Linux 定制：xdg-open / 终端运行 / XDG 数据目录）
"""

__version__ = "1.0.0"
__all__ = ["__version__"]
