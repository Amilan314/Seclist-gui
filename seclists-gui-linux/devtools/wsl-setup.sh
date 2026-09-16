#!/usr/bin/env bash
# ============================================================================
#  为 WSL / Debian 系准备「SecLists 助手（Linux 版）」运行环境，然后跑验证。
#  需要以 root 运行（apt 安装），脚本会自己切回普通用户执行测试。
#
#  用法（在 Windows 上）：
#     wsl.exe -d Ubuntu -u root -e bash /mnt/e/.../devtools/wsl-setup.sh
#
#  安装内容（都已存在则跳过）：
#     python3-tk   图形界面必需
#     xvfb         无显示环境下的虚拟显示（回退用）
#     xterm        终端模拟器（命令卡片「▶ 在终端运行」用）
#     xdg-utils    文件管理器打开
#     fonts-wqy-microhei  体积很小的中文字体（避免中文显示成方框）
# ============================================================================
set -uo pipefail

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TEST="$HERE/wsl-test.sh"
LOG="$HERE/wsl-setup.log"

exec > >(tee -a "$LOG") 2>&1

echo "########## WSL 依赖准备 $(date -Is) ##########"
echo "whoami=$(id -un) uid=$(id -u)"

PKGS=(python3-tk xvfb x11-apps xterm xdg-utils fonts-wqy-microhei)

MISSING=()
for p in "${PKGS[@]}"; do
  if dpkg -s "$p" >/dev/null 2>&1; then
    echo "  已安装: $p"
  else
    echo "  待安装: $p"
    MISSING+=("$p")
  fi
done

if [ "${#MISSING[@]}" -gt 0 ]; then
  echo "--- apt-get update ---"
  apt-get update -qq || echo "[!] apt-get update 返回非 0（可能是网络/镜像问题）"
  echo "--- apt-get install ${MISSING[*]} ---"
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${MISSING[@]}"
  echo "[apt 退出码 = $?]"
fi

echo "--- 安装结果 ---"
for p in "${PKGS[@]}"; do
  if dpkg -s "$p" >/dev/null 2>&1; then
    printf '  %-22s ✓ %s\n' "$p" "$(dpkg -s "$p" | awk -F': ' '/^Version/{print $2}')"
  else
    printf '  %-22s ✗ 仍未安装\n' "$p"
  fi
done
python3 -c 'import tkinter; print("  tkinter ✓ Tk", tkinter.TkVersion)' 2>&1

# 用普通用户身份跑测试（保留 WSLg 的显示相关环境变量）
TARGET_USER="${WSL_USER:-$(id -un 1000 2>/dev/null || echo root)}"
echo
echo "########## 以 $TARGET_USER 身份运行验证 ##########"
runuser -u "$TARGET_USER" -- env \
  DISPLAY="${DISPLAY:-:0}" \
  WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}" \
  XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/1000}" \
  HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)" \
  TERM="${TERM:-xterm-256color}" \
  bash "$TEST"
TEST_RC=$?
echo "[wsl-test.sh 退出码 = $TEST_RC]"

echo
echo "########## Xvfb 虚拟显示截图（不受窗口遮挡影响） ##########"
runuser -u "$TARGET_USER" -- env \
  HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)" \
  bash "$HERE/xvfb-shot.sh"
SHOT_RC=$?
echo "[xvfb-shot.sh 退出码 = $SHOT_RC]"

# 清理前面 wsl-test.sh 留在 WSLg 上的后台界面
pkill -f "SecListsAssistant.py" 2>/dev/null && echo "已关闭后台界面进程"

echo "########## setup+test 结束 ##########"
