#!/usr/bin/env python3
"""检查版本号一致：根 package.json、topmind-research/package.json、SKILL.md 的 metadata.version、CHANGELOG 最近一个已发布版本。

只用 Python 标准库。CHANGELOG 的「Unreleased」段不参与比较。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "topmind-research"


def skill_version(text: str) -> str | None:
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return None
    v = re.search(r"^\s+version:\s*['\"]?([^'\"\s]+)['\"]?\s*$", m.group(1), re.M)
    return v.group(1) if v else None


def changelog_version(text: str) -> str | None:
    for m in re.finditer(r"^##\s+\[?v?(\d+\.\d+\.\d+)", text, re.M):
        return m.group(1)
    return None


def collect() -> dict[str, str | None]:
    return {
        "package.json": json.loads((ROOT / "package.json").read_text(encoding="utf-8")).get("version"),
        "topmind-research/package.json": json.loads((SKILL / "package.json").read_text(encoding="utf-8")).get("version"),
        "topmind-research/SKILL.md metadata.version": skill_version((SKILL / "SKILL.md").read_text(encoding="utf-8")),
        "CHANGELOG.md 最近已发布版本": changelog_version((ROOT / "CHANGELOG.md").read_text(encoding="utf-8")),
    }


def main() -> int:
    versions = collect()
    for k, v in versions.items():
        print(f"  {k}: {v}")
    values = set(versions.values())
    if None in values or len(values) != 1:
        print("FAIL: 版本号不一致或缺失")
        return 1
    print(f"PASS: 版本号一致（{values.pop()}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
