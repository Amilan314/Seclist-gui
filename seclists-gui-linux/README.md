# SecLists 使用助手 · Linux 版

浏览、检索、理解 SecLists 的几千份字典，并把「该用哪份字典 + 完整命令」直接摆到你面前，
一键复制或直接在你的终端里跑起来。

- 原生 Tkinter 窗口：**不监听任何端口、不起 Web 服务、不联网**
- **不修改 SecLists 的任何原文件**；工具箱产生的新字典写到 `~/.local/share/seclists-gui/output/`
- 只用 Python 标准库（Tkinter + bash），不需要 pip / venv
- 与 Windows 版共享同一套知识库（23 个场景、128 条字典路径、速查手册）

---

## 1. 依赖

```bash
# Debian / Ubuntu / Kali / Mint
sudo apt update && sudo apt install python3-tk

# Fedora / RHEL
sudo dnf install python3-tkinter

# Arch / Manjaro
sudo pacman -S tk

# openSUSE
sudo zypper install python3-tk
```

中文字体（界面中文显示成方框时才需要）：

```bash
sudo apt install fonts-noto-cjk        # 或 fonts-wqy-microhei
```

可选：`xdg-utils`（文件管理器打开）、任意终端模拟器（`xterm` / `gnome-terminal` / `konsole` …）。

---

## 2. 快速开始

```bash
cd seclists-gui-linux

./seclists-gui                 # 启动图形界面
./seclists-gui --doctor        # 只看环境报告（不需要图形界面）
./seclists-gui --selftest      # 无头自检：索引 / 场景 / 预览 / 搜索 / 工具箱全链路
./seclists-gui --tab 3         # 启动后直接打开「字典工具箱」（0~4）

./install.sh                   # 装进应用菜单（~/.local/share/applications）
./install.sh --uninstall       # 卸载菜单项
```

直接跑 Python 也可以：

```bash
python3 SecListsAssistant.py --doctor
```

### 仓库位置怎么找

按顺序尝试：`$SECLISTS_ROOT` → `/usr/share/seclists` → `/opt/SecLists` → `~/SecLists` →
`~/seclists` → 本工具所在目录的上一级 → 逐级向上查找。找不到时用环境变量指定：

```bash
export SECLISTS_ROOT=/mnt/e/SecLists      # 换成你的实际仓库路径
```

---

## 3. 界面

| 区域 | 作用 |
|---|---|
| 顶部「目标」 | 填域名 / IP / URL，命令里的 `{url}` `{host}` `{domain}` 自动替换 |
| 顶部「路径风格」 | **本机路径**（Linux 绝对路径）/ **Kali 路径**（`/usr/share/seclists/…`）/ **相对路径** |
| 左侧导航 | 按分类展开字典；双击＝预览，右键＝复制路径 / 在文件管理器中显示 / 用编辑器打开 / 统计行数 / 加入工具箱 |
| 🧭 使用引导 | 23 个实战场景：用哪些字典、为什么、完整命令、避坑提示 |
| 👀 字典预览 | 行号预览、行数统计、编码识别、文件内查找 |
| 🔎 全库搜索 | 按内容或文件名搜索全部字典，双击结果跳到预览对应行 |
| 🧰 字典工具箱 | 合并 / 去重 / 排序 / 去注释 / 长度过滤 / 关键字过滤 / 正则过滤 / 截取，另存为新字典 |
| 📖 速查手册 | 工具↔字典对照表、常见坑、Linux/WSL 小贴士 |

### Linux 版相比 Windows 版的不同

| 能力 | 说明 |
|---|---|
| **▶ 在终端运行** | 命令卡片上新增按钮：把命令写成一个临时脚本（`~/.local/share/seclists-gui/run-command.sh`，可自行查看），在新终端窗口里执行，跑完保留窗口显示退出码。执行前会二次确认 |
| 打开文件 | `xdg-open`，找不到则退到 `gedit` / `kate` / `mousepad` / `code`，再不行就在终端里用 `$EDITOR` |
| 在文件管理器中显示 | 优先 `dbus-send` 调 FileManager1 **选中该文件**，否则 `xdg-open` 打开所在目录 |
| 路径风格 | 「本机路径」是 Linux 绝对路径（WSL 下就是 `/mnt/e/...`） |
| 数据目录 | 走 XDG：`~/.local/share/seclists-gui`（可用 `SECLISTS_GUI_DATA` 改） |
| 环境自检 | `--doctor` 检查 Tkinter、显示服务、中文字体、外部工具、终端模拟器、仓库位置 |
| HiDPI | `export SECLISTS_GUI_SCALING=1.5` 调整整体缩放 |

### 快捷键

`Ctrl+1`~`Ctrl+5` 切换标签页 · `Ctrl+F` 跳到文件名搜索 · `F5` 重新扫描 · `Ctrl+Q` 退出

---

## 4. 在 WSL 里使用

```bash
# 1) 确认图形能力（Windows 11 或已更新的 Windows 10 自带 WSLg）
echo "$DISPLAY $WAYLAND_DISPLAY"        # WSLg 下通常有值

# 2) 装依赖
sudo apt install python3-tk fonts-noto-cjk xterm

# 3) 跑起来（仓库在 Windows 盘上时的路径）
cd /mnt/e/SecLists/seclists-gui-linux   # 换成你的实际路径
./seclists-gui
```

几点注意：

- **没有 WSLg** 时窗口弹不出来：要么升级 WSL（`wsl --update`），要么在 Windows 上装 X server 并
  `export DISPLAY=$(ip route list default | awk '{print $3}'):0`。
- 仓库在 Windows 盘（`/mnt/...`）上时，`/mnt` 走 9p 协议，**扫描会明显慢于 ext4**（本仓库 6000+ 文件，
  第一次索引约几秒到几十秒），之后有缓存。
- WSL 里算出来的「本机路径」是 `/mnt/e/...`，这种路径**只能在 WSL 里用**。要粘到 Kali 上执行，
  把顶部「路径风格」切到 **Kali 路径**（`/usr/share/seclists/...`）。
- WSL 中的 GUI 进程可以直接操作 `/mnt/c`、`/mnt/e` 下的文件，工具不会改动仓库内容。

---

## 5. 目录结构

```
seclists-gui-linux/
├─ seclists-gui                  启动器（bash，可直接双击/执行）
├─ SecListsAssistant.py          入口：仓库定位、XDG 数据目录、--doctor / --selftest
├─ install.sh                    安装/卸载应用菜单项
├─ slgui/
│  ├─ app.py                    主窗口与五个标签页（含 ▶ 在终端运行）
│  ├─ catalog.py                分类说明、23 个场景、命令模板、速查手册
│  ├─ indexer.py                索引、行数缓存、预览、内容搜索、字典工具箱
│  └─ theme.py                  配色 + Linux 字体挑选 + ttk 主题
└─ devtools/                     开发辅助（可删）
   ├─ wsl-setup.sh              在 WSL 里装依赖并跑完整验证 + 截图（需 root）
   ├─ wsl-test.sh               环境快照 + doctor + selftest
   ├─ xvfb-shot.sh              Xvfb 虚拟显示下逐标签页截图
   ├─ xwd2png.py                XWD → PNG（纯标准库）
   ├─ analyze_shot.py           截图像素统计校验
   ├─ rowprofile.py             输出截图逐行主色带，判断各区域落在哪一行
   ├─ probe_layout.py           量出引导页启动时的真实几何（卡片/命令框位置与尺寸）
   └─ shots/                    Xvfb 下抓的五个标签页截图
```

运行期数据（都不在仓库里）：

```
~/.local/share/seclists-gui/
├─ linecounts.json               行数缓存（按文件大小+修改时间失效）
├─ output/                       工具箱导出的新字典
├─ run-command.sh                「▶ 在终端运行」最后一次生成的脚本
└─ error.log                     启动异常日志
```

---

## 6. 环境变量

| 变量 | 作用 |
|---|---|
| `SECLISTS_ROOT` | 指定 SecLists 仓库根目录 |
| `SECLISTS_GUI_DATA` | 指定数据目录（缓存 / 输出），默认 `~/.local/share/seclists-gui` |
| `SECLISTS_GUI_SCALING` | Tk 缩放，例如 `1.5`（HiDPI 字太小时用） |
| `PYTHON` | 启动器使用的解释器，默认 `python3` |
| `VISUAL` / `EDITOR` | 没有 GUI 编辑器时，「用编辑器打开」用它 |

---

## 7. 排查

**窗口出不来 / 报 `no display name and no $DISPLAY environment variable`**
先跑 `./seclists-gui --doctor`。WSL 看 WSLg（`wsl --update`），SSH 用 `ssh -X`。

**中文是方框**
`sudo apt install fonts-noto-cjk`，然后重开程序；`--doctor` 里的「中文字体」会显示有没有。

**点「▶ 在终端运行」没反应**
没有可用终端模拟器：`sudo apt install xterm`。命令同时保存在
`~/.local/share/seclists-gui/run-command.sh`，可手动 `bash` 执行。

**复制之后粘贴不出来**
X11 剪贴板由本程序持有：粘贴时窗口要还开着。关窗后再粘贴会拿不到内容——需要长期保留时，
用「另存为」把内容写成文件。

**在 `/mnt/...` 上扫描很慢**
把仓库放到 Linux 文件系统（如 `~/SecLists`）会快很多。行数统计有缓存，第二次很快。

**某份字典显示「未找到」**
该副本可能被裁剪过，用左侧文件名搜索或「全库搜索」找替代字典。

---

## 8. 自检与开发

改动代码后：

```bash
# 一键（WSL 里推荐，需 root）：装依赖 → doctor → selftest → Xvfb 逐页截图
sudo bash devtools/wsl-setup.sh

# 或者分步：
python3 SecListsAssistant.py --doctor        # 环境报告（不需要图形界面）
python3 SecListsAssistant.py --selftest      # 全链路自检
bash devtools/wsl-test.sh                    # 快照 + doctor + selftest（无显示时自动 xvfb-run）
bash devtools/xvfb-shot.sh                   # Xvfb 下逐标签页截图 → devtools/shots/

# 截图/几何排查
python3 devtools/analyze_shot.py devtools/shots     # 像素统计校验
python3 devtools/rowprofile.py devtools/shots/tab0-guide.png 40   # 逐行主色带
python3 devtools/probe_layout.py             # 引导页启动时的真实几何
python3 SecListsAssistant.py --capture 某目录 # 程序内部等索引完成后逐页截图（需 xwd）
```

`--selftest` 会校验：索引文件数与体积、**128 条场景字典路径是否真实存在**、23 个场景详情能否渲染、
五个标签页的实际排版尺寸、等宽/界面字体是否被 Tk 回退、以及预览 / 行数统计 / 内容搜索 / 工具箱
的**完整后台线程链路**。

`slgui/catalog.py` 与 Windows 版同源；如果只改了场景内容或文案，记得两边同步。

### 已验证环境

- Windows 11 + WSL2（Ubuntu 24.04，内核 6.18，WSLg 1.0.73）：`--doctor` 环境就绪，
  `--selftest` 全部通过，Xvfb 下五个标签页截图渲染正常（中文字体 WenQuanYi Micro Hei）
- 仓库位于 `/mnt/e/...`（drvfs）：首次索引约 6300 个文件，可用（比 ext4 慢）

---

## 9. 合规提醒

⚠️ 本工具生成的命令是**真实攻击命令**，字典本身也包含口令库、WebShell、Zip 炸弹等敏感样本。
**只对你自己拥有或已获书面授权的目标使用**。未授权扫描、爆破、上传测试在多数司法辖区属违法行为。
高风险动作（在线爆破、Zip 炸弹、部署 WebShell、`sqlmap --os-shell`）请先确认授权范围与回滚方案。
