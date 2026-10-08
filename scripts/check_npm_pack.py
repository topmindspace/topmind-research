#!/usr/bin/env python3
"""按 `npm pack --dry-run --json` 的实际文件清单检查 npm 包内容。

- 必须有：技能目录 topmind-research/ 下所有 git 跟踪的文件（缓存除外），以及根目录的 package.json、README、LICENSE、CHANGELOG
- 不得有：仓库根的 tests/、evals/、scripts/、.github/，以及 __pycache__/、*.pyc、.env、.topmind/
只用 Python 标准库；需要本机有 npm。
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIRED_ROOT = {"package.json", "README.md", "README.en.md", "LICENSE", "CHANGELOG.md"}
FORBIDDEN_PREFIX = ("tests/", "evals/", "scripts/", ".github/", "release-assets/")
FORBIDDEN_PART = ("__pycache__/", ".topmind/")


def packed_files() -> tuple[set[str], dict]:
    npm = shutil.which("npm")
    if not npm:
        raise SystemExit("未找到 npm")
    out = subprocess.run(
        [npm, "pack", "--dry-run", "--json", "--ignore-scripts"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout
    info = json.loads(out)[0]
    return {f["path"] for f in info["files"]}, info


def tracked_skill_files() -> set[str]:
    out = subprocess.run(
        ["git", "ls-files", "topmind-research"], cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout
    return {p for p in out.splitlines() if p and "__pycache__/" not in p and not p.endswith(".pyc")}


def main() -> int:
    files, info = packed_files()
    problems: list[str] = []
    for p in sorted(files):
        if p.startswith(FORBIDDEN_PREFIX) or any(x in p for x in FORBIDDEN_PART) or p.endswith((".pyc", ".pyo")) or Path(p).name == ".env":
            problems.append(f"不应进包：{p}")
    for p in sorted(REQUIRED_ROOT - files):
        problems.append(f"缺少：{p}")
    for p in sorted(tracked_skill_files() - files):
        problems.append(f"技能文件未进包：{p}")
    if "topmind-research/SKILL.md" not in files:
        problems.append("缺少：topmind-research/SKILL.md")
    print(f"npm pack --dry-run：{info['name']}@{info['version']}，{info['entryCount']} 个文件，"
          f"tarball {info['size']} B，解包 {info['unpackedSize']} B")
    if problems:
        print("FAIL：npm 包内容不符合预期")
        for x in problems:
            print(f"  - {x}")
        return 1
    print("PASS：npm 包只含技能目录与根说明文件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
