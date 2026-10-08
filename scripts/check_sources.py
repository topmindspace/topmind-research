#!/usr/bin/env python3
"""检查 topmind-research/config/sources.yaml。

  python3 scripts/check_sources.py            # 字段检查 + 逐个请求 URL（可达性只报告，不影响退出码）
  python3 scripts/check_sources.py --offline  # 只做字段检查（CI 每次提交跑）

字段检查不通过时退出码为 1。本脚本不修改 sources.yaml；可达性结果需要人工判断后再改配置。
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "topmind-research"
sys.path.insert(0, str(SKILL / "scripts"))
import sources_config  # noqa: E402

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
SECTIONS = {"companies", "people", "media", "benchmarks", "newsletters", "tool_sources", "paper_sources"}
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HANDLE = re.compile(r"^(TBD|[A-Za-z0-9_]{1,15})$")


def validate(config: dict) -> list[str]:
    errors: list[str] = []
    unknown = set(config) - SECTIONS
    if unknown:
        errors.append(f"未知分组：{', '.join(sorted(unknown))}")
    names: set[str] = set()
    for section, items in config.items():
        for item in items:
            name = item.get("name", "")
            where = f"{section}/{name or '?'}"
            if not name:
                errors.append(f"{where}: 缺少 name")
            if (section, name) in names:
                errors.append(f"{where}: name 重复")
            names.add((section, name))
            if section == "people":
                if not HANDLE.match(item.get("x_handle", "")):
                    errors.append(f"{where}: x_handle 应为 TBD 或合法用户名")
                if item.get("x_handle", "TBD") != "TBD" and not DATE.match(item.get("x_verified_at", "")):
                    errors.append(f"{where}: 已填 x_handle 须写 x_verified_at")
                continue
            if item.get("status") not in ("ok", "tbd"):
                errors.append(f"{where}: status 应为 ok 或 tbd")
            if item.get("fetch") not in ("http", "browser"):
                errors.append(f"{where}: fetch 应为 http 或 browser")
            if "verified_at" in item and not DATE.match(item["verified_at"]):
                errors.append(f"{where}: verified_at 格式应为 YYYY-MM-DD")
            if item.get("status") == "tbd" and not item.get("note"):
                errors.append(f"{where}: status: tbd 须在 note 写明待核原因")
            urls = [item[f] for f in sources_config.URL_FIELDS if f in item]
            if not urls:
                errors.append(f"{where}: 没有任何 URL 字段")
            for u in urls:
                if not u.startswith("https://"):
                    errors.append(f"{where}: URL 须为 https：{u}")
    return errors


def probe(url: str, timeout: float) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return str(resp.status)
    except urllib.error.HTTPError as exc:
        return str(exc.code)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return type(exc).__name__


def reachability(config: dict, timeout: float) -> list[tuple[str, str, str, str, str]]:
    jobs = []
    for section, items in config.items():
        if section == "people":
            continue
        for item in items:
            for f in sources_config.URL_FIELDS:
                if f in item:
                    jobs.append((section, item["name"], f, item[f], item.get("status", "")))
    with ThreadPoolExecutor(max_workers=6) as pool:
        codes = list(pool.map(lambda j: probe(j[3], timeout), jobs))
    return [(s, n, f, u, st, c) for (s, n, f, u, st), c in zip(jobs, codes)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sources", default=str(SKILL / "config" / "sources.yaml"))
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--timeout", type=float, default=20)
    args = ap.parse_args(argv)
    config = sources_config.load(args.sources)
    errors = validate(config)
    counts = {k: len(v) for k, v in config.items()}
    tbd = [f"{s}/{i['name']}" for s, items in config.items() for i in items if i.get("status") == "tbd"]
    handles_tbd = [i["name"] for i in config.get("people", []) if i.get("x_handle") == "TBD"]
    print(f"分组条目数：{counts}")
    print(f"status: tbd（{len(tbd)}）：{', '.join(tbd) or '无'}")
    print(f"x_handle 为 TBD（{len(handles_tbd)}）：{', '.join(handles_tbd) or '无'}")
    if not args.offline:
        print("可达性（只报告）：")
        for section, name, field, url, status, code in reachability(config, args.timeout):
            flag = "  " if code.startswith(("2", "3")) else "!!"
            print(f"  {flag} {code:>14}  {section}/{name}.{field}  [{status}]  {url}")
    if errors:
        print(f"FAIL: 字段检查 {len(errors)} 处")
        for e in errors:
            print(" ", e)
        return 1
    print("PASS: 字段检查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
