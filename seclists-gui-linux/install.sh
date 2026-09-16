#!/usr/bin/env bash
# ============================================================================
#  把「SecLists 使用助手」装进当前用户的应用菜单（不需要 root）
#
#    ./install.sh              安装
#    ./install.sh --uninstall  卸载
#
#  做的事：
#    1. 在 ~/.local/share/applications/ 写一个 seclists-gui.desktop
#    2. 在 ~/.local/bin/ 建一个 seclists-gui 软链接
#    3. 刷新桌面数据库（有 update-desktop-database 时）
#  不会复制、不会修改 SecLists 仓库本身。
# ============================================================================
set -uo pipefail

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
BIN_DIR="$HOME/.local/bin"
DESKTOP="$APP_DIR/seclists-gui.desktop"
LINK="$BIN_DIR/seclists-gui"

if [ "${1:-}" = "--uninstall" ]; then
  rm -f "$DESKTOP" "$LINK"
  command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APP_DIR" 2>/dev/null
  echo "已卸载：$DESKTOP 与 $LINK"
  exit 0
fi

mkdir -p "$APP_DIR" "$BIN_DIR"

cat > "$DESKTOP" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=SecLists 使用助手
Name[en]=SecLists Assistant
GenericName=Wordlist navigator
Comment=浏览与检索 SecLists 字典，生成可直接执行的命令
Comment[en]=Browse SecLists wordlists and generate ready-to-run commands
Exec=$HERE/seclists-gui %u
Path=$HERE
Icon=utilities-terminal
Terminal=false
Categories=Utility;Security;Development;
Keywords=seclists;wordlist;dictionary;pentest;security;
StartupNotify=true
EOF

chmod +x "$HERE/seclists-gui" "$HERE/SecListsAssistant.py" 2>/dev/null
ln -sf "$HERE/seclists-gui" "$LINK"

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APP_DIR" 2>/dev/null

echo "安装完成："
echo "  菜单项 : $DESKTOP"
echo "  命令   : $LINK  （若 ~/.local/bin 不在 PATH，请把它加进去，或直接用 $HERE/seclists-gui）"
echo
echo "提示：仓库位置可用 SECLISTS_ROOT 指定；数据目录默认在 ~/.local/share/seclists-gui"
