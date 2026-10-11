#!/usr/bin/env python3
"""检查 topmind-research/config/sources.yaml。

  python3 scripts/check_sources.py            # 字段检查 + 逐个请求 URL（可达性只报告，不影响退出码）
  python3 scripts/check_sources.py --offline  # 只做字段检查（CI 每次提交跑）
  python3 scripts/check_sources.py --strict --report sources-report.md   # 每周巡检用

退出码：字段检查不通过为 1；加 --strict 时，status: ok 的信源出现「失效」（HTTP 404/410、域名解析失败、连接被拒）为 2。
403、429、5xx、超时、证书链问题记为「警告」，不影响退出码：这些多半是反爬或临时故障，要人工判断。
在 GitHub Actions 里运行时，失效与警告会输出成 ::error:: / ::warning:: 注释，并把报告追加到运行摘要。
本脚本不修改 sources.yaml；可达性结果需要人工判断后再改配置。
"""
from __future__ import annotations

import argparse
import os
import re
import socket
import ssl
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "topmind-research"
sys.path.insert(0, str(SKILL / "scripts"))
import collect_feeds  # noqa: E402
import sources_config  # noqa: E402

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
SECTIONS = {"companies", "people", "media", "benchmarks", "newsletters", "tool_sources", "paper_sources"}
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HANDLE = re.compile(r"^[A-Za-z0-9_]{1,15}$")
# 取值含义见 sources.yaml 文件头
STATUSES = ("ok", "page-only", "blocked", "tbd")
FETCHES = ("http", "browser", "js", "api", "x")
HEADER_PROFILES = ("default", "browser", "none")
X_STATUSES = ("confirmed", "none", "unverified", "candidate")
LIST_API_METHODS = ("GET", "POST")


def _check_people(item: dict, where: str) -> list[str]:
    errors: list[str] = []
    handle = item.get("x_handle", "")
    x_status = item.get("x_status")
    if x_status is not None and x_status not in X_STATUSES:
        errors.append(f"{where}: x_status 应为 {' / '.join(X_STATUSES)}")
    if handle is None:
        # null = 已核实本人没有 X 账号（或无法核实本人账号），必须写依据
        if x_status != "none" or not item.get("note"):
            errors.append(f"{where}: x_handle 为 null 时须写 x_status: none 和 note（依据）")
    elif handle == "TBD":
        if x_status in ("confirmed", "none"):
            errors.append(f"{where}: x_handle 为 TBD 时 x_status 不能是 {x_status}")
        if x_status == "candidate" and not item.get("note"):
            errors.append(f"{where}: x_status: candidate 须在 note 写明候选账号")
    elif not HANDLE.match(handle or ""):
        errors.append(f"{where}: x_handle 应为 TBD、null 或合法用户名")
    else:
        if not DATE.match(item.get("x_verified_at") or ""):
            errors.append(f"{where}: 已填 x_handle 须写 x_verified_at")
        if x_status not in (None, "confirmed"):
            errors.append(f"{where}: 已填 x_handle 时 x_status 只能是 confirmed")
    for f in ("weibo",):
        if item.get(f) and not item[f].startswith("https://"):
            errors.append(f"{where}: {f} 须为 https")
    return errors


def validate(config: dict) -> list[str]:
    errors: list[str] = []
    unknown = set(config) - SECTIONS
    if unknown:
        errors.append(f"未知分组：{', '.join(sorted(unknown))}")
    names: set[tuple[str, str]] = set()
    for section, items in config.items():
        for item in items:
            name = item.get("name") or ""
            where = f"{section}/{name or '?'}"
            if not name:
                errors.append(f"{where}: 缺少 name")
            if (section, name) in names:
                errors.append(f"{where}: name 重复")
            names.add((section, name))
            if section == "people":
                errors.extend(_check_people(item, where))
                continue
            status = item.get("status")
            if status not in STATUSES:
                errors.append(f"{where}: status 应为 {' / '.join(STATUSES)}")
            if item.get("fetch") not in FETCHES:
                errors.append(f"{where}: fetch 应为 {' / '.join(FETCHES)}")
            if "verified_at" in item and not DATE.match(item["verified_at"] or ""):
                errors.append(f"{where}: verified_at 格式应为 YYYY-MM-DD")
            if status != "ok" and not item.get("note"):
                errors.append(f"{where}: status: {status} 须在 note 写明原因")
            machine = [f for f in sources_config.MACHINE_FIELDS if item.get(f)]
            if status == "ok" and item.get("fetch") in ("js", "x") and not machine:
                errors.append(f"{where}: 列表页需 {item.get('fetch')} 才能读、又没有可机读渠道，status 不能是 ok（用 page-only 或 blocked）")
            if status == "page-only" and item.get("fetch") != "js":
                errors.append(f"{where}: status: page-only 只用于 fetch: js（页面能打开但列表靠前端渲染）")
            if item.get("fetch") == "api" and not item.get("list_api") and not any(item.get(f) for f in ("hf_api", "gh_api")):
                errors.append(f"{where}: fetch: api 须写 list_api")
            if item.get("list_api_method") and item["list_api_method"] not in LIST_API_METHODS:
                errors.append(f"{where}: list_api_method 应为 GET 或 POST")
            if item.get("headers") and item["headers"] not in HEADER_PROFILES:
                errors.append(f"{where}: headers 应为 {' / '.join(HEADER_PROFILES)}")
            if item.get("x_account") and not HANDLE.match(item["x_account"]):
                errors.append(f"{where}: x_account 应为不带 @ 的用户名")
            if item.get("ca_root") and not item["ca_root"].startswith("https://"):
                errors.append(f"{where}: ca_root 须为 https")
            if item.get("ca_root") and not item.get("note"):
                errors.append(f"{where}: 写了 ca_root 须在 note 说明缺哪张根证书")
            if item.get("ca_bundle"):
                errors.append(f"{where}: ca_bundle 是本机路径，不要提交进仓库；用 --ca-bundle 参数或 TOPMIND_CA_BUNDLE 环境变量")
            urls = [item[f] for f in sources_config.URL_FIELDS if item.get(f)]
            if not urls:
                errors.append(f"{where}: 没有任何 URL 字段")
            for u in urls:
                if not u.startswith("https://"):
                    errors.append(f"{where}: URL 须为 https：{u}")
    return errors


def probe(url: str, timeout: float, headers: dict[str, str] | None = None, context=None) -> str:
    req = urllib.request.Request(url, headers=headers if headers is not None else {"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:
            return str(resp.status)
    except urllib.error.HTTPError as exc:
        return str(exc.code)
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", None)
        if isinstance(reason, ssl.SSLError):
            return "SSLError"
        if isinstance(reason, (TimeoutError, socket.timeout)):
            return "Timeout"
        if isinstance(reason, socket.gaierror):
            return "gaierror"
        if isinstance(reason, ConnectionRefusedError):
            return "ConnectionRefusedError"
        return type(exc).__name__
    except (TimeoutError, socket.timeout):
        return "Timeout"
    except OSError as exc:
        return type(exc).__name__


def reachability(config: dict, timeout: float, ca_bundle: str | None = None) -> list[tuple[str, str, str, str, str, str]]:
    """按各信源的 headers 档位请求（没写时用浏览器 UA）；list_api 需要 POST，不在这里探测。证书校验始终开启。"""
    ctx = collect_feeds.ssl_context(ca_bundle)
    jobs = []
    for section, items in config.items():
        if section == "people":
            continue
        for item in items:
            for f in sources_config.URL_FIELDS:
                if item.get(f) and f != "list_api":
                    jobs.append((section, item["name"], f, item[f], item.get("status", ""), item.get("headers")))
    def one(j):
        headers = collect_feeds.build_headers(j[5]) if j[5] else {"User-Agent": UA}
        return probe(j[3], timeout, headers, ctx)
    with ThreadPoolExecutor(max_workers=6) as pool:
        codes = list(pool.map(one, jobs))
    return [(s, n, f, u, st, c) for (s, n, f, u, st, _h), c in zip(jobs, codes)]


HARD_HTTP = {"404", "410"}
HARD_ERRORS = {"gaierror", "ConnectionRefusedError"}


def classify(code: str) -> str:
    """把探测结果分成 ok / broken（失效）/ warn（警告）。"""
    if code[:1] in ("2", "3"):
        return "ok"
    if code in HARD_HTTP or code in HARD_ERRORS:
        return "broken"
    return "warn"


def summarize(results: list[tuple[str, str, str, str, str, str]]) -> tuple[list, list, list]:
    """只对 status: ok 的信源算失效和警告；其余状态（blocked / tbd / page-only）本来就预期打不开，单独列出。"""
    broken, warn, expected = [], [], []
    for row in results:
        kind = classify(row[5])
        if kind == "ok":
            continue
        if row[4] != "ok":
            expected.append(row)
        elif kind == "broken":
            broken.append(row)
        else:
            warn.append(row)
    return broken, warn, expected


def render_report(broken: list, warn: list, expected: list, total: int, field_errors: list[str]) -> str:
    lines = ["# 信源巡检报告", "",
             f"- 探测 URL：{total}",
             f"- 失效（status: ok 但 404/410/连不上）：{len(broken)}",
             f"- 警告（status: ok 但 403/429/5xx/超时/证书）：{len(warn)}",
             f"- 预期打不开（status 不是 ok）：{len(expected)}",
             f"- 字段检查问题：{len(field_errors)}", ""]
    for title, rows in (("失效", broken), ("警告", warn), ("预期打不开", expected)):
        if not rows:
            continue
        lines += [f"## {title}", "", "| 结果 | 信源 | 字段 | status | URL |", "|---|---|---|---|---|"]
        lines += [f"| {c} | {s}/{n} | {f} | {st} | {u} |" for s, n, f, u, st, c in rows]
        lines.append("")
    if field_errors:
        lines += ["## 字段检查", ""] + [f"- {e}" for e in field_errors] + [""]
    lines.append("处理方式：失效项人工确认后改 `topmind-research/config/sources.yaml`（换 URL 或改 status 并写 note）；警告项连续多周出现再处理。")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sources", default=str(SKILL / "config" / "sources.yaml"))
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--timeout", type=float, default=20)
    ap.add_argument("--ca-bundle", default=os.environ.get(collect_feeds.CA_BUNDLE_ENV),
                    help="追加信任的 CA 文件（PEM），用于本机缺新根证书；不会关闭证书校验")
    ap.add_argument("--strict", action="store_true",
                    help="status: ok 的信源出现失效（404/410/连不上）时退出码为 2")
    ap.add_argument("--report", help="把巡检结果写成 Markdown 报告")
    args = ap.parse_args(argv)
    config = sources_config.load(args.sources)
    errors = validate(config)
    counts = {k: len(v) for k, v in config.items()}
    print(f"分组条目数：{counts}")
    for st in STATUSES[1:]:
        hits = [f"{s}/{i['name']}" for s, items in config.items() for i in items if i.get("status") == st]
        print(f"status: {st}（{len(hits)}）：{', '.join(hits) or '无'}")
    handles_tbd = [i["name"] for i in config.get("people", []) if i.get("x_handle") == "TBD"]
    print(f"x_handle 为 TBD（{len(handles_tbd)}）：{', '.join(handles_tbd) or '无'}")
    broken: list = []
    if not args.offline:
        print("可达性：")
        results = reachability(config, args.timeout, args.ca_bundle)
        for section, name, field, url, status, code in results:
            flag = "  " if code.startswith(("2", "3")) else "!!"
            print(f"  {flag} {code:>14}  {section}/{name}.{field}  [{status}]  {url}")
        broken, warn, expected = summarize(results)
        print(f"失效 {len(broken)}，警告 {len(warn)}，预期打不开 {len(expected)}（共 {len(results)} 个 URL）")
        if os.environ.get("GITHUB_ACTIONS") == "true":
            for kind, rows in (("error", broken), ("warning", warn)):
                for s, n, f, u, _st, c in rows:
                    print(f"::{kind} title=信源{'失效' if kind == 'error' else '警告'}::{s}/{n}.{f} {c} {u}")
        report = render_report(broken, warn, expected, len(results), errors)
        if args.report:
            Path(args.report).write_text(report, encoding="utf-8")
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary, "a", encoding="utf-8") as fh:
                fh.write(report)
    if errors:
        print(f"FAIL: 字段检查 {len(errors)} 处")
        for e in errors:
            print(" ", e)
        return 1
    print("PASS: 字段检查通过")
    if args.strict and broken:
        print(f"FAIL: {len(broken)} 个 status: ok 的信源失效，见上方列表或报告")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
