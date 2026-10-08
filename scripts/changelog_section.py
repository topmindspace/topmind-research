#!/usr/bin/env python3
"""从 CHANGELOG.md 取出指定版本的段落，打印到 stdout，用作 GitHub Release 说明。

用法：python3 scripts/changelog_section.py 0.2.3
找不到该版本或段落为空时退出码 1（Release 流程随之失败，不发一个没有说明的版本）。
只用 Python 标准库。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def section(text: str, version: str) -> str | None:
    head = re.compile(r"^##\s+\[?v?" + re.escape(version) + r"\]?(?:\s|$)", re.M)
    m = head.search(text)
    if not m:
        return None
    nxt = re.compile(r"^##\s", re.M).search(text, m.end())
    body = text[m.start(): nxt.start() if nxt else len(text)].strip()
    # 只有标题、没有正文时视为空
    return body if body.count("\n") >= 1 else None


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("用法：changelog_section.py <version>", file=sys.stderr)
        return 2
    version = argv[1].lstrip("v")
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    body = section(text, version)
    if not body:
        print(f"CHANGELOG.md 里没有 {version} 的段落（或段落为空）", file=sys.stderr)
        return 1
    print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
