#!/usr/bin/env python3
"""读取 config/sources.yaml 的最小解析器（只用 Python 标准库）。

只支持本仓库 sources.yaml 用到的子集：
  顶层 `分组名:`，下面是 `- key: value` 开头的列表项，列表项内是 `key: value` 标量。
  支持 `#` 注释、单双引号字符串；不带引号的 `null` / `~` 读成 None。不支持嵌套映射、多行字符串、流式写法。
"""
from __future__ import annotations

import re
from pathlib import Path

SECTION_RE = re.compile(r"^([A-Za-z_][\w-]*):\s*$")
ITEM_RE = re.compile(r"^\s+-\s+([A-Za-z_][\w-]*):\s*(.*)$")
FIELD_RE = re.compile(r"^\s+([A-Za-z_][\w-]*):\s*(.*)$")


def _strip_comment(value: str) -> str:
    """去掉行尾注释；引号内的 # 保留。URL 里的 # 前面没有空格，不会被当成注释。"""
    out = []
    quote = None
    for i, ch in enumerate(value):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "#" and (i == 0 or value[i - 1] in " \t"):
            break
        out.append(ch)
    return "".join(out).strip()


def _scalar(raw: str) -> str | None:
    value = _strip_comment(raw)
    if value in ("null", "~", "Null", "NULL"):
        return None
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        value = value[1:-1]
    return value


def parse(text: str) -> dict[str, list[dict[str, str | None]]]:
    data: dict[str, list[dict[str, str | None]]] = {}
    section: str | None = None
    item: dict[str, str | None] | None = None
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = SECTION_RE.match(line)
        if m:
            section = m.group(1)
            data[section] = []
            item = None
            continue
        m = ITEM_RE.match(line)
        if m and section is not None:
            item = {m.group(1): _scalar(m.group(2))}
            data[section].append(item)
            continue
        m = FIELD_RE.match(line)
        if m and item is not None:
            item[m.group(1)] = _scalar(m.group(2))
            continue
        raise ValueError(f"sources.yaml 第 {lineno} 行无法解析：{line!r}")
    return data


def load(path: str | Path) -> dict[str, list[dict[str, str | None]]]:
    return parse(Path(path).read_text(encoding="utf-8"))


# 信源分组到来源级别的默认映射（见 references/verification.md 第一节）
# benchmarks 记 T1：独立评测方只对它自己发布的评测结果算 T1
SECTION_TIER = {
    "companies": "T0",
    "paper_sources": "T0",
    "benchmarks": "T1",
    "media": "T2",
    "newsletters": "T2",
    "tool_sources": "T2",
}

# 人看的页面
PAGE_FIELDS = ("blog", "news", "reports", "url", "trending", "sitemap", "podcast")
# 可机读渠道：rss / rss_extra 为 RSS 或 Atom；hf_api、gh_api、papers_api 为 JSON（collect_feeds.py 会解析）；
# list_api 为站点自己的列表接口（collect_feeds.py 不解析，agent 按 note 调用）
FEED_FIELDS = ("rss", "rss_extra", "hf_api", "gh_api", "papers_api")
MACHINE_FIELDS = FEED_FIELDS + ("list_api",)
URL_FIELDS = PAGE_FIELDS + MACHINE_FIELDS
