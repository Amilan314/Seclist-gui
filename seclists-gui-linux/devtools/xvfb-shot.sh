#!/usr/bin/env bash
# ============================================================================
#  在 Xvfb 虚拟显示里跑「SecLists 助手（Linux 版）」并逐个标签页截图。
#  不依赖 WSLg，也不受窗口遮挡/前台权限影响，拿到的就是 Linux 端真实渲染结果。
#
#  截图由程序内部驱动（--capture）：它会先等索引扫描完成，再逐页用 xwd 抓
#  自己的窗口（按 X window id），所以不会截到「还在扫描」的中间状态。
#
#  依赖： xvfb, x11-apps（xwd）
#  用法： bash devtools/xvfb-shot.sh
#  产物： devtools/shots/tabN-*.png（由 xwd2png.py 从 .xwd 转换）
# ============================================================================
set -uo pipefail

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APPDIR="$(dirname "$HERE")"
SHOTS="$HERE/shots"
PY="${PYTHON:-python3}"
DISP=":99"
GEOM="1400x900x24"

mkdir -p "$SHOTS"
rm -f "$SHOTS"/*.xwd "$SHOTS"/*.png

for tool in Xvfb xwd; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "[x] 缺少 $tool。安装： sudo apt install xvfb x11-apps"
    exit 1
  fi
done

echo "启动 Xvfb $DISP ($GEOM) …"
Xvfb "$DISP" -screen 0 "$GEOM" -nolisten tcp >/tmp/xvfb.log 2>&1 &
XVFB_PID=$!
sleep 3
if ! kill -0 "$XVFB_PID" 2>/dev/null; then
  echo "[x] Xvfb 启动失败："; cat /tmp/xvfb.log; exit 1
fi

cleanup() {
  kill "$XVFB_PID" 2>/dev/null
  wait "$XVFB_PID" 2>/dev/null
}
trap cleanup EXIT

cd "$APPDIR" || exit 1
echo "--- 启动界面并逐页截图（内部会等索引完成） ---"
DISPLAY="$DISP" timeout 400 "$PY" SecListsAssistant.py --capture "$SHOTS"
CAP_RC=$?
echo "[capture 退出码 = $CAP_RC]"

echo "--- 转换 XWD -> PNG ---"
"$PY" "$HERE/xwd2png.py" "$SHOTS"
echo "产物目录：$SHOTS"
ls -l "$SHOTS"/*.png 2>/dev/null | awk '{print "  " $5 " bytes  " $9}'
