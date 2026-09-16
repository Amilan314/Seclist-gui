#!/usr/bin/env bash
# ============================================================================
#  在 WSL / 任意 Linux 里一次性跑完「SecLists 助手（Linux 版）」的验证：
#     1. 环境快照（发行版 / WSL / 显示 / Python / Tkinter / 外部工具）
#     2. --doctor 环境自检
#     3. --selftest 全链路自检（无显示时自动尝试 xvfb-run）
#     4. 若图形环境可用，把界面以后台方式启动，便于从外面截图检查
#
#  用法：  bash devtools/wsl-test.sh [--no-gui]
#  日志：  与本脚本同目录的 wsl-test.log（在 Windows 上可直接打开）
# ============================================================================
set -uo pipefail

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APPDIR="$(dirname "$HERE")"
LOG="$HERE/wsl-test.log"
PY="${PYTHON:-python3}"
START_GUI=1
[ "${1:-}" = "--no-gui" ] && START_GUI=0

: > "$LOG"
exec > >(tee -a "$LOG") 2>&1

echo "########## SecLists GUI (Linux) verification ##########"
echo "时间        : $(date -Is)"
echo "脚本目录    : $HERE"
echo "应用目录    : $APPDIR"
echo

echo "--- 系统 ---"
uname -a
head -4 /etc/os-release 2>/dev/null
echo "WSL_DISTRO_NAME=${WSL_DISTRO_NAME:-（不是 WSL）}"
echo "WSL_INTEROP=${WSL_INTEROP:-（未设置）}"
echo
echo "--- 显示 ---"
echo "DISPLAY=${DISPLAY:-（空）}"
echo "WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-（空）}"
echo "XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-（空）}"
echo "XDG_SESSION_TYPE=${XDG_SESSION_TYPE:-（空）}"
echo
echo "--- Python ---"
command -v "$PY" || echo "找不到 $PY"
"$PY" --version 2>&1
"$PY" -c 'import tkinter, sys; print("tkinter", tkinter.TkVersion, "| python", sys.version.split()[0])' 2>&1
echo
echo "--- 可用截图/虚拟显示工具 ---"
for t in Xvfb xvfb-run xwd import convert scrot gnome-screenshot; do
  p="$(command -v "$t" 2>/dev/null)"
  printf '  %-18s %s\n' "$t" "${p:-✗}"
done
echo

echo "########## 1) --doctor ##########"
cd "$APPDIR" || exit 1
timeout 180 "$PY" SecListsAssistant.py --doctor
DOCTOR_RC=$?
echo "[doctor 退出码 = $DOCTOR_RC]"
echo

echo "########## 2) --selftest ##########"
SELFTEST_RC=999
if [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; then
  timeout 300 "$PY" SecListsAssistant.py --selftest
  SELFTEST_RC=$?
  echo "[selftest(原生显示) 退出码 = $SELFTEST_RC]"
fi
if [ "$SELFTEST_RC" != "0" ] && command -v xvfb-run >/dev/null 2>&1; then
  echo "--- 回退到 xvfb-run ---"
  timeout 300 xvfb-run -a --server-args="-screen 0 1400x900x24" \
      "$PY" SecListsAssistant.py --selftest
  SELFTEST_RC=$?
  echo "[selftest(xvfb) 退出码 = $SELFTEST_RC]"
fi
if [ "$SELFTEST_RC" = "999" ]; then
  echo "既没有可用显示，也没有 xvfb-run —— 无法做界面自检。"
  echo "安装虚拟显示： sudo apt install xvfb"
fi
echo

echo "########## 3) 图形环境与后台启动 ##########"
if [ "$START_GUI" = "1" ] && { [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; }; then
  rm -f /tmp/seclists-gui-bg.log
  nohup "$PY" SecListsAssistant.py --tab 0 >/tmp/seclists-gui-bg.log 2>&1 &
  GUI_PID=$!
  sleep 6
  if kill -0 "$GUI_PID" 2>/dev/null; then
    echo "界面已后台启动 PID=$GUI_PID  （供外部截图；测试完记得 kill）"
  else
    echo "界面启动后立即退出，日志："
    cat /tmp/seclists-gui-bg.log
  fi
else
  echo "跳过后台启动（无图形环境或 --no-gui）"
fi
echo

echo "########## 汇总 ##########"
echo "doctor   : $DOCTOR_RC   （0 = 环境就绪）"
echo "selftest : $SELFTEST_RC （0 = 全部通过）"
if [ "$DOCTOR_RC" = "0" ] && [ "$SELFTEST_RC" = "0" ]; then
  echo "结论：Linux 版在本地环境验证通过 ✅"
else
  echo "结论：需要看上面的具体报错 ❌"
fi
echo "日志：$LOG"
echo "########## done ##########"
