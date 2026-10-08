#!/usr/bin/env python3
"""检查报告的 [n] 引用：编号连续、正文无悬空引用、来源表无未用条目、每条来源有 URL 和访问日期。

只用 Python 标准库。用法：

  python3 scripts/check_citations.py 报告.md
  python3 scripts/check_citations.py --allow-placeholders assets/templates/*.md   # 模板里的 YYYY-MM-DD / URL 占位只报警告
  python3 scripts/check_citations.py --check-urls 报告.md                         # 额外请求每个 URL，只报告

规则来源：references/verification.md 第三节。退出码：有错误为 1，否则为 0。
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

SOURCES_HEADING = re.compile(r"^#{2,3}\s*(来源|参考来源|Sources|References)表?\s*([（(][^）)]*[）)])?\s*$")
HEADING = re.compile(r"^#{1,3}\s")
BODY_REF = re.compile(r"(?<![!\w])\[(\d+)\](?![(:])")
DEF_LINE = re.compile(r"^\s*(?:[-*]\s+)?\[(\d+)\]\s*(.*)$")
URL = re.compile(r"https?://\S+")
ACCESS_DATE = re.compile(r"访问\s*(\d{4}-\d{2}-\d{2})")
PLACEHOLDER = re.compile(r"YYYY-MM-DD|\bURL\b")


def strip_code(lines: list[str]) -> list[str]:
    out, fenced = [], False
    for line in lines:
        if line.strip().startswith("```"):
            fenced = not fenced
            out.append("")
            continue
        out.append("" if fenced else re.sub(r"`[^`]*`", "", line))
    return out


def check(text: str, allow_placeholders: bool = False) -> tuple[list[str], list[str], list[tuple[int, str]]]:
    lines = strip_code(text.splitlines())
    errors: list[str] = []
    warnings: list[str] = []
    start = next((i for i, l in enumerate(lines) if SOURCES_HEADING.match(l)), None)
    body_refs: dict[int, int] = {}
    defs: list[tuple[int, str, int]] = []
    if start is None:
        for i, line in enumerate(lines, 1):
            for m in BODY_REF.finditer(line):
                body_refs.setdefault(int(m.group(1)), i)
        if body_refs:
            errors.append("正文有 [n] 引用，但没有「## 来源」一节")
        return errors, warnings, []
    end = next((j for j in range(start + 1, len(lines)) if HEADING.match(lines[j])), len(lines))
    for i, line in enumerate(lines, 1):
        if start < i - 1 < end:
            m = DEF_LINE.match(line)
            if m:
                defs.append((int(m.group(1)), m.group(2), i))
            continue
        for m in BODY_REF.finditer(line):
            body_refs.setdefault(int(m.group(1)), i)

    nums = [n for n, _, _ in defs]
    seen = set()
    for n, _, lineno in defs:
        if n in seen:
            errors.append(f"第 {lineno} 行：来源编号 [{n}] 重复")
        seen.add(n)
    if nums and sorted(seen) != list(range(1, max(seen) + 1)):
        missing = sorted(set(range(1, max(seen) + 1)) - seen)
        errors.append(f"来源编号不连续，缺少：{', '.join(f'[{n}]' for n in missing)}")
    for n, lineno in sorted(body_refs.items()):
        if n not in seen:
            errors.append(f"第 {lineno} 行：正文引用 [{n}] 在来源表里不存在")
    for n, _, lineno in defs:
        if n not in body_refs:
            errors.append(f"第 {lineno} 行：来源 [{n}] 在正文没有被引用")

    urls: list[tuple[int, str]] = []
    for n, rest, lineno in defs:
        url = URL.search(rest)
        if url:
            urls.append((n, url.group(0).rstrip(")>.,，。")))
        problems = []
        if not url:
            problems.append("缺少 URL")
        if not ACCESS_DATE.search(rest):
            problems.append("缺少「访问 YYYY-MM-DD」")
        for p in problems:
            msg = f"第 {lineno} 行：来源 [{n}] {p}"
            if allow_placeholders and PLACEHOLDER.search(rest):
                warnings.append(msg + "（模板占位）")
            else:
                errors.append(msg)
    return errors, warnings, urls


def check_url(url: str, timeout: float = 15) -> str:
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "Mozilla/5.0 topmind-research-citations"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return str(resp.status)
    except urllib.error.HTTPError as exc:
        return str(exc.code)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return type(exc).__name__


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("files", nargs="+")
    ap.add_argument("--allow-placeholders", action="store_true")
    ap.add_argument("--check-urls", action="store_true", help="请求每个来源 URL，只报告不影响退出码")
    args = ap.parse_args(argv)
    failed = False
    for f in args.files:
        errors, warnings, urls = check(Path(f).read_text(encoding="utf-8"), args.allow_placeholders)
        status = "FAIL" if errors else "OK"
        print(f"{status} {f}：来源 {len(urls)} 条有 URL，错误 {len(errors)}，警告 {len(warnings)}")
        for e in errors:
            print(f"  错误 {e}")
        for w in warnings:
            print(f"  警告 {w}")
        if args.check_urls:
            for n, url in urls:
                print(f"  [{n}] {check_url(url)} {url}")
        failed = failed or bool(errors)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
