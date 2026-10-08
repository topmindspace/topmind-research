#!/usr/bin/env python3
"""检查技能目录自包含：SKILL.md 与 references/ 里提到的相对路径都存在，且不引用技能目录外的文件或已删除的旧技能。

只用 Python 标准库。路径按技能根目录（topmind-research/）解析，符合 Agent Skills 规范。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "topmind-research"
PATH_RE = re.compile(r"(?<![\w./-])((?:references|config|assets|scripts)/[\w./{}-]+\.(?:md|yaml|yml|py))")
FORBIDDEN = (
    (re.compile(r"\.\./"), "引用技能目录外的相对路径"),
    (re.compile(r"topmind-research-(collect|analyze)\b"), "引用已合并的旧子技能"),
    (re.compile(r"topmind-tool-scout"), "引用外部技能 topmind-tool-scout"),
    (re.compile(r"wide_research"), "引用宿主未必提供的工具 wide_research"),
)


def scan() -> list[str]:
    errors: list[str] = []
    files = [SKILL / "SKILL.md", *sorted((SKILL / "references").glob("*.md")), *sorted((SKILL / "assets").rglob("*.md"))]
    for f in files:
        rel = f.relative_to(ROOT)
        text = f.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            for m in PATH_RE.finditer(line):
                target = m.group(1).rstrip(".")
                if "{" in target:
                    continue
                if not (SKILL / target).exists():
                    errors.append(f"{rel}:{lineno}: 引用的文件不存在：{target}")
            for pat, label in FORBIDDEN:
                if pat.search(line):
                    errors.append(f"{rel}:{lineno}: {label}")
    lines = (SKILL / "SKILL.md").read_text(encoding="utf-8").count("\n") + 1
    if lines > 500:
        errors.append(f"SKILL.md 共 {lines} 行，超过规范建议的 500 行")
    return errors


def main() -> int:
    errors = scan()
    if errors:
        print(f"FAIL: {len(errors)} 处")
        for e in errors:
            print(" ", e)
        return 1
    print("PASS: 技能目录内引用完整，无外部依赖引用")
    return 0


if __name__ == "__main__":
    sys.exit(main())
