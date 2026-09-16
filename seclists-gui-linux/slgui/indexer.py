# -*- coding: utf-8 -*-
"""SecLists 仓库索引：扫描、行数缓存、文件预览、内容搜索、字典工具。

所有耗时操作都提供「可取消 + 进度回调」的形式，供界面在后台线程里调用。
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterator, List, Optional, Sequence, Tuple

SKIP_DIRS = {".git", "__pycache__", ".idea", ".vscode", "node_modules"}

BINARY_EXTS = {
    ".zip", ".gz", ".tgz", ".tar", ".7z", ".rar", ".bz2", ".xz", ".jar", ".war",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".ico", ".webp", ".tif", ".tiff",
    ".mp3", ".mp4", ".avi", ".mov", ".wav", ".pdf", ".doc", ".docx", ".xls",
    ".xlsx", ".ppt", ".pptx", ".exe", ".dll", ".so", ".bin", ".iso", ".db",
    ".sqlite", ".cap", ".pcap", ".swf", ".class", ".pyc", ".woff", ".woff2",
    ".ttf", ".eot", ".otf", ".cap", ".evtx", ".msi", ".deb", ".rpm",
}

TEXT_EXTS = {
    ".txt", ".md", ".csv", ".tsv", ".lst", ".list", ".dic", ".fuzz", ".xml",
    ".json", ".yaml", ".yml", ".ini", ".conf", ".cfg", ".log", ".py", ".sh",
    ".ps1", ".bat", ".rb", ".pl", ".php", ".asp", ".aspx", ".jsp", ".js",
    ".html", ".htm", ".sql", ".rules", ".ext", ".wordlist", ".txt2", ".nse",
}

CHUNK = 1 << 20  # 1 MiB


def human_size(num: int) -> str:
    num = float(num or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num < 1024 or unit == "TB":
            return f"{int(num)} B" if unit == "B" else f"{num:.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} TB"


def human_int(num: int) -> str:
    try:
        return f"{int(num):,}"
    except Exception:
        return str(num)


def is_probably_text(rel: str) -> bool:
    ext = os.path.splitext(rel)[1].lower()
    if ext in BINARY_EXTS:
        return False
    if ext in TEXT_EXTS:
        return True
    return True  # 没有扩展名的字典文件（如 Massdns 结果）大多也是文本


def looks_binary(path: str, sniff: int = 4096) -> bool:
    try:
        with open(path, "rb") as fh:
            head = fh.read(sniff)
    except OSError:
        return True
    if not head:
        return False
    if b"\x00" in head:
        return True
    text_chars = bytes(range(0x20, 0x7F)) + b"\r\n\t\f\b\x1b"
    nontext = sum(1 for b in head if b not in text_chars and b < 0x80)
    return nontext / max(len(head), 1) > 0.30


@dataclass
class FileEntry:
    rel: str          # 相对仓库根，统一用 / 分隔
    path: str         # 本机绝对路径
    size: int
    mtime: float

    @property
    def name(self) -> str:
        return self.rel.rsplit("/", 1)[-1]

    @property
    def ext(self) -> str:
        return os.path.splitext(self.rel)[1].lower()

    @property
    def top(self) -> str:
        return self.rel.split("/", 1)[0]

    def as_dict(self) -> dict:
        return {"rel": self.rel, "path": self.path, "size": self.size, "mtime": self.mtime}


class LineCache:
    """行数缓存：<data>/linecounts.json，键为相对路径。"""

    def __init__(self, cache_file: str):
        self.cache_file = cache_file
        self.data: Dict[str, list] = {}
        self._dirty = 0
        self._lock = threading.Lock()
        self.load()

    def load(self) -> None:
        try:
            with open(self.cache_file, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            if isinstance(raw, dict):
                self.data = {k: v for k, v in raw.items() if isinstance(v, list) and len(v) == 3}
        except Exception:
            self.data = {}

    def save(self, force: bool = False) -> None:
        if not force and self._dirty < 25:
            return
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            tmp = self.cache_file + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self.data, fh)
            os.replace(tmp, self.cache_file)
            self._dirty = 0
        except Exception:
            pass

    def get(self, rel: str, size: int, mtime: float) -> Optional[int]:
        rec = self.data.get(rel)
        if not rec:
            return None
        if int(rec[0]) != int(size) or abs(float(rec[1]) - float(mtime)) > 1:
            return None
        try:
            return int(rec[2])
        except Exception:
            return None

    def put(self, rel: str, size: int, mtime: float, lines: int) -> None:
        with self._lock:
            self.data[rel] = [int(size), float(mtime), int(lines)]
            self._dirty += 1


class Index:
    """SecLists 仓库索引。"""

    def __init__(self, root: str, data_dir: str, extra_skip: Sequence[str] = ()):
        self.root = os.path.abspath(root)
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.skip_dirs = set(SKIP_DIRS) | {d for d in extra_skip if d}
        self.cache = LineCache(os.path.join(self.data_dir, "linecounts.json"))
        self.files: Dict[str, FileEntry] = {}
        self.dirs: Dict[str, dict] = {}          # rel -> {"subdirs":[...], "files":[...], "size":int, "count":int}
        self.scanned_at = 0.0
        self.total_size = 0

    # ---------------------------------------------------------------- 扫描
    def scan(self, progress: Optional[Callable[[int, str], None]] = None) -> dict:
        files: Dict[str, FileEntry] = {}
        dirs: Dict[str, dict] = {"": {"subdirs": [], "files": [], "size": 0, "count": 0}}
        count = 0
        root = self.root
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if d not in self.skip_dirs)
            rel_dir = os.path.relpath(dirpath, root).replace("\\", "/")
            if rel_dir == ".":
                rel_dir = ""
            node = dirs.setdefault(rel_dir, {"subdirs": [], "files": [], "size": 0, "count": 0})
            for d in dirnames:
                child = f"{rel_dir}/{d}" if rel_dir else d
                node["subdirs"].append(child)
                dirs.setdefault(child, {"subdirs": [], "files": [], "size": 0, "count": 0})
            for fn in sorted(filenames):
                rel = f"{rel_dir}/{fn}" if rel_dir else fn
                try:
                    st = os.stat(os.path.join(root, rel.replace("/", os.sep)))
                except OSError:
                    continue
                files[rel] = FileEntry(rel=rel, path=os.path.join(root, rel.replace("/", os.sep)),
                                       size=st.st_size, mtime=st.st_mtime)
                node["files"].append(rel)
                count += 1
                if progress and count % 500 == 0:
                    progress(count, rel)
        # 自底向上汇总目录大小与文件数
        for rel in sorted(dirs.keys(), key=lambda r: r.count("/"), reverse=True):
            node = dirs[rel]
            node["size"] = sum(files[f].size for f in node["files"])
            node["count"] = len(node["files"])
            if rel:
                parent = rel.rsplit("/", 1)[0] if "/" in rel else ""
                pnode = dirs.setdefault(parent, {"subdirs": [], "files": [], "size": 0, "count": 0})
                pnode["size"] += node["size"]
                pnode["count"] += node["count"]
        self.files = files
        self.dirs = dirs
        self.total_size = sum(f.size for f in files.values())
        self.scanned_at = time.time()
        if progress:
            progress(count, "")
        return self.stats()

    def stats(self) -> dict:
        per_top: Dict[str, dict] = {}
        root_files = 0
        for e in self.files.values():
            if "/" not in e.rel:
                root_files += 1
                continue
            top = e.top
            if top.startswith("."):
                continue
            rec = per_top.setdefault(top, {"count": 0, "size": 0})
            rec["count"] += 1
            rec["size"] += e.size
        return {"files": len(self.files), "size": self.total_size, "per_top": per_top,
                "root_files": root_files, "dirs": max(0, len(self.dirs) - 1)}

    def get(self, rel: str) -> Optional[FileEntry]:
        return self.files.get(rel.replace("\\", "/"))

    def children(self, rel: str) -> Tuple[List[str], List[str]]:
        node = self.dirs.get(rel or "", {"subdirs": [], "files": []})
        return list(node["subdirs"]), list(node["files"])

    def dir_info(self, rel: str) -> dict:
        return self.dirs.get(rel or "", {"size": 0, "count": 0, "subdirs": [], "files": []})

    def iter_files(self, prefix: str = "", text_only: bool = False) -> Iterator[FileEntry]:
        prefix = (prefix or "").replace("\\", "/").strip("/")
        for rel, e in self.files.items():
            if prefix and not (rel == prefix or rel.startswith(prefix + "/")):
                continue
            if text_only and not is_probably_text(rel):
                continue
            yield e

    def subdirs_of_top(self, top: str) -> List[str]:
        return sorted(self.children(top)[0])

    # ------------------------------------------------------------ 行数统计
    def count_lines(self, entry: FileEntry, use_cache: bool = True) -> int:
        if use_cache:
            hit = self.cache.get(entry.rel, entry.size, entry.mtime)
            if hit is not None:
                return hit
        lines = 0
        last_byte = b"\n"
        try:
            with open(entry.path, "rb") as fh:
                while True:
                    chunk = fh.read(CHUNK)
                    if not chunk:
                        break
                    lines += chunk.count(b"\n")
                    last_byte = chunk[-1:]
        except OSError:
            return 0
        if last_byte not in (b"\n", b""):
            lines += 1
        self.cache.put(entry.rel, entry.size, entry.mtime, lines)
        self.cache.save()
        return lines

    def count_lines_dir(self, rel: str, cancel: Optional[threading.Event] = None,
                        progress: Optional[Callable[[int, int, str], None]] = None) -> Tuple[int, int]:
        """统计目录下所有文本文件的行数，返回 (行数, 文件数)。"""
        total_lines = 0
        total_files = 0
        entries = [e for e in self.iter_files(rel) if is_probably_text(e.rel)]
        n = len(entries)
        for i, e in enumerate(entries, 1):
            if cancel and cancel.is_set():
                break
            total_lines += self.count_lines(e)
            total_files += 1
            if progress and (i % 5 == 0 or i == n):
                progress(i, n, e.rel)
        self.cache.save(force=True)
        return total_lines, total_files

    # -------------------------------------------------------------- 预览
    def detect_encoding(self, entry: FileEntry) -> str:
        try:
            with open(entry.path, "rb") as fh:
                head = fh.read(262144)
        except OSError:
            return "utf-8"
        if head.startswith(b"\xef\xbb\xbf"):
            return "utf-8-sig"
        if head.startswith(b"\xff\xfe"):
            return "utf-16"
        if head.startswith(b"\xfe\xff"):
            return "utf-16"
        try:
            head.decode("utf-8")
            return "utf-8"
        except UnicodeDecodeError:
            return "cp1252"

    def read_lines(self, entry: FileEntry, limit: int = 500, encoding: str = "auto",
                   start: int = 1) -> Tuple[List[str], str, bool]:
        """读取前 limit 行（start 之前的行会被跳过但仍计入）。

        返回 (行列表, 实际编码, 是否还有更多)。
        """
        enc = self.detect_encoding(entry) if encoding in ("auto", "", None) else encoding
        lines: List[str] = []
        truncated = False
        idx = 0
        max_lines = max(1, int(limit))
        try:
            with open(entry.path, "r", encoding=enc, errors="replace", newline="") as fh:
                for raw in fh:
                    idx += 1
                    if idx < start:
                        continue
                    lines.append(raw.rstrip("\r\n"))
                    if len(lines) >= max_lines:
                        truncated = True
                        break
        except OSError:
            return [], enc, False
        return lines, enc, truncated

    def head_bytes(self, entry: FileEntry, max_bytes: int = 8 << 20, encoding: str = "auto") -> str:
        enc = self.detect_encoding(entry) if encoding in ("auto", "", None) else encoding
        try:
            with open(entry.path, "rb") as fh:
                data = fh.read(max_bytes)
        except OSError:
            return ""
        return data.decode(enc, errors="replace")

    # -------------------------------------------------------------- 搜索
    def search_names(self, query: str, use_regex: bool = False, case_sensitive: bool = False,
                     text_only: bool = False, limit: int = 2000) -> List[FileEntry]:
        if not query:
            return []
        try:
            pat = re.compile(query if use_regex else re.escape(query),
                             0 if case_sensitive else re.IGNORECASE)
        except re.error:
            return []
        out: List[FileEntry] = []
        for rel in sorted(self.files):
            if text_only and not is_probably_text(rel):
                continue
            if pat.search(rel):
                out.append(self.files[rel])
                if len(out) >= limit:
                    break
        return out

    def search_content(self, entries: Sequence[FileEntry], pattern: str, use_regex: bool = False,
                       case_sensitive: bool = False, max_file_mb: int = 64, per_file_hits: int = 40,
                       total_hits: int = 5000, cancel: Optional[threading.Event] = None,
                       progress: Optional[Callable[[int, int, int], None]] = None
                       ) -> Iterator[Tuple[FileEntry, List[Tuple[int, str]]]]:
        """流式产出 (文件, [(行号, 内容)])。"""
        if not pattern:
            return
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            pat = re.compile(pattern if use_regex else re.escape(pattern), flags)
        except re.error as exc:
            raise ValueError(f"正则表达式无效：{exc}")
        max_bytes = max_file_mb * 1024 * 1024
        total = 0
        hits_total = 0
        n = len(entries)
        for i, entry in enumerate(entries, 1):
            if cancel and cancel.is_set():
                return
            if progress and (i % 3 == 0 or i == n):
                progress(i, n, hits_total)
            if not is_probably_text(entry.rel):
                continue
            if entry.size > max_bytes:
                continue
            enc = self.detect_encoding(entry)
            hits: List[Tuple[int, str]] = []
            try:
                with open(entry.path, "r", encoding=enc, errors="replace", newline="") as fh:
                    for lineno, raw in enumerate(fh, 1):
                        line = raw.rstrip("\r\n")
                        if pat.search(line):
                            if len(line) > 300:
                                line = line[:300] + " …"
                            hits.append((lineno, line))
                            hits_total += 1
                            if len(hits) >= per_file_hits or hits_total >= total_hits:
                                break
            except OSError:
                continue
            if hits:
                total += 1
                yield entry, hits
            if hits_total >= total_hits:
                return

    # --------------------------------------------------------- 字典工具箱
    def process_files(self, paths: Sequence[str], opts: dict, out_path: Optional[str] = None,
                      preview_limit: int = 0, cancel: Optional[threading.Event] = None,
                      progress: Optional[Callable[[str, int], None]] = None
                      ) -> Tuple[List[str], dict]:
        """按选项处理字典文件。

        返回 (预览行, 统计 dict)。out_path 不为空时同时写文件。
        """
        preview: List[str] = []
        stats = {"in_lines": 0, "out_lines": 0, "unique": 0, "skipped": 0,
                 "max_len": 0, "min_len": 10 ** 9, "sum_len": 0, "files": 0, "encoding_hits": 0}
        seen = set()
        do_dedup = bool(opts.get("dedup"))
        do_sort = bool(opts.get("sort"))
        min_len = int(opts.get("min_len") or 0)
        max_len = int(opts.get("max_len") or 0)
        inc = (opts.get("include") or "").strip()
        exc = (opts.get("exclude") or "").strip()
        rx = (opts.get("regex") or "").strip()
        case_sensitive = bool(opts.get("case_sensitive"))
        keep_head = int(opts.get("head") or 0)
        flags = 0 if case_sensitive else re.IGNORECASE
        rx_pat = None
        if rx:
            rx_pat = re.compile(rx if opts.get("regex_is_regex", True) else re.escape(rx), flags)
        inc_pat = re.compile(re.escape(inc), flags) if inc else None
        exc_pat = re.compile(re.escape(exc), flags) if exc else None

        buffer: List[str] = []
        fh_out = None
        try:
            if out_path:
                os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
                fh_out = open(out_path, "w", encoding="utf-8", errors="replace", newline="\n")

            def emit(text: str) -> bool:
                stats["out_lines"] += 1
                stats["sum_len"] += len(text)
                stats["max_len"] = max(stats["max_len"], len(text))
                stats["min_len"] = min(stats["min_len"], len(text))
                if fh_out is not None:
                    fh_out.write(text + "\n")
                elif preview_limit and len(preview) < preview_limit:
                    preview.append(text)
                if keep_head and stats["out_lines"] >= keep_head:
                    return False
                return True

            for p in paths:
                if cancel and cancel.is_set():
                    break
                stats["files"] += 1
                if progress:
                    progress(os.path.basename(p), stats["out_lines"])
                enc = "utf-8"
                try:
                    with open(p, "rb") as probe:
                        head = probe.read(262144)
                    try:
                        head.decode("utf-8")
                    except UnicodeDecodeError:
                        enc = "cp1252"
                        stats["encoding_hits"] += 1
                except OSError:
                    continue
                if do_sort:
                    buffer = []
                try:
                    with open(p, "r", encoding=enc, errors="replace", newline="") as fh:
                        for raw in fh:
                            if cancel and cancel.is_set():
                                break
                            line = raw.rstrip("\r\n")
                            stats["in_lines"] += 1
                            if opts.get("strip"):
                                line = line.strip()
                            if opts.get("lower"):
                                line = line.lower()
                            if opts.get("skip_empty") and not line:
                                stats["skipped"] += 1
                                continue
                            if opts.get("skip_comments") and line.lstrip().startswith("#"):
                                stats["skipped"] += 1
                                continue
                            if min_len and len(line) < min_len:
                                stats["skipped"] += 1
                                continue
                            if max_len and len(line) > max_len:
                                stats["skipped"] += 1
                                continue
                            if inc_pat and not inc_pat.search(line):
                                stats["skipped"] += 1
                                continue
                            if exc_pat and exc_pat.search(line):
                                stats["skipped"] += 1
                                continue
                            if rx_pat and not rx_pat.search(line):
                                stats["skipped"] += 1
                                continue
                            if do_dedup:
                                key = line if case_sensitive else line.lower()
                                if key in seen:
                                    stats["skipped"] += 1
                                    continue
                                seen.add(key)
                            if do_sort:
                                buffer.append(line)
                                continue
                            if not emit(line):
                                raise StopIteration
                except StopIteration:
                    break
                if not do_sort and stats["out_lines"] and not preview_limit and fh_out is None:
                    pass
            if do_sort:
                buffer.sort()
                for line in buffer:
                    if cancel and cancel.is_set():
                        break
                    try:
                        if not emit(line):
                            break
                    except StopIteration:
                        break
        finally:
            if fh_out is not None:
                fh_out.close()
        stats["unique"] = len(seen) if do_dedup else stats["out_lines"]
        if stats["min_len"] == 10 ** 9:
            stats["min_len"] = 0
        return preview, stats


def save_text(path: str, lines: Sequence[str], append: bool = False) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    mode = "a" if append else "w"
    with open(path, mode, encoding="utf-8", newline="\n") as fh:
        for line in lines:
            fh.write(line + "\n")
    return path
