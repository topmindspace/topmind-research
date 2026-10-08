#!/usr/bin/env python3
"""collect 的可选抓取脚本：读 sources.yaml 里的 rss 字段，按 watermark 过滤、URL 规范化去重，输出 JSONL。

只用 Python 标准库。用法（在技能目录 topmind-research/ 下执行）：

  python3 scripts/collect_feeds.py --sources config/sources.yaml --since 2026-10-01
  python3 scripts/collect_feeds.py --since 2026-10-01T08:00:00+08:00 --sections companies,media

每行输出一个 JSON：{"title", "url", "source", "published", "tier"}。
抓取失败的信源写到 stderr，不中断其他信源。没有 rss 字段的信源不处理，由 agent 按 references/collect.md 用浏览器或 WebFetch 读取。
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sources_config  # noqa: E402

UA = "Mozilla/5.0 (compatible; topmind-research-collect/0.2; +https://github.com/topmindspace/topmind-research)"
TRACKING_PARAMS = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "ref_src", "spm", "from", "source"}
CST = timezone(timedelta(hours=8))
MAX_WORKERS = 6


def normalize_url(url: str) -> str:
    """小写协议和域名，去掉默认端口、跟踪参数（utm_* 等）、# 锚点和路径末尾斜杠。"""
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    if parts.port and not ((scheme == "http" and parts.port == 80) or (scheme == "https" and parts.port == 443)):
        host = f"{host}:{parts.port}"
    path = parts.path or "/"
    if len(path) > 1:
        path = path.rstrip("/")
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in TRACKING_PARAMS
    ]
    return urlunsplit((scheme, host, path, urlencode(query), ""))


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _child_text(elem: ET.Element, *names: str) -> str:
    for child in elem:
        if _local(child.tag) in names and (child.text or "").strip():
            return child.text.strip()
    return ""


def parse_date(value: str) -> datetime | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        dt = None
    if dt is None:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def parse_feed(xml_bytes: bytes) -> list[dict[str, str]]:
    """解析 RSS 2.0 / RSS 1.0(RDF) / Atom，返回 [{title, url, published}]，published 为 ISO 字符串或空。"""
    root = ET.fromstring(xml_bytes)
    entries: list[dict[str, str]] = []
    for elem in root.iter():
        name = _local(elem.tag)
        if name not in ("item", "entry"):
            continue
        title = _child_text(elem, "title")
        link = ""
        for child in elem:
            if _local(child.tag) != "link":
                continue
            href = child.attrib.get("href")
            if href and child.attrib.get("rel", "alternate") == "alternate":
                link = href.strip()
                break
            if not href and (child.text or "").strip():
                link = child.text.strip()
                break
        if not link:
            guid = _child_text(elem, "guid", "id")
            if guid.startswith("http"):
                link = guid
        published = parse_date(_child_text(elem, "pubdate", "published", "updated", "date", "issued"))
        if title and link:
            entries.append({"title": " ".join(title.split()), "url": link, "published": published.isoformat() if published else ""})
    return entries


def fetch(url: str, timeout: float) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            data = gzip.decompress(data)
        return data


def parse_since(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=CST)
    return dt


def filter_and_dedupe(records: list[dict[str, str]], since: datetime | None) -> list[dict[str, str]]:
    """按 watermark 过滤（没有日期的条目保留，交给 agent 判断），按规范化 URL 去重，重复时保留级别更高的来源。"""
    best: dict[str, dict[str, str]] = {}
    order: list[str] = []
    for rec in records:
        if since is not None and rec.get("published"):
            dt = parse_date(rec["published"])
            if dt is not None and dt <= since:
                continue
        key = normalize_url(rec["url"])
        rec = {**rec, "url": key}
        if key not in best:
            best[key] = rec
            order.append(key)
        elif rec.get("tier", "T9") < best[key].get("tier", "T9"):
            best[key] = rec
    out = [best[k] for k in order]
    out.sort(key=lambda r: r.get("published") or "", reverse=True)
    return out


def collect(config: dict, sections: list[str], include_tbd: bool, timeout: float, max_per_feed: int):
    jobs = []
    for section in sections:
        for src in config.get(section, []):
            if not src.get("rss"):
                continue
            if src.get("status") != "ok" and not include_tbd:
                continue
            jobs.append((section, src))

    def run(job):
        section, src = job
        try:
            entries = parse_feed(fetch(src["rss"], timeout))[:max_per_feed]
        except (urllib.error.URLError, TimeoutError, ET.ParseError, OSError, ValueError) as exc:
            return src["name"], None, f"{type(exc).__name__}: {exc}"
        tier = sources_config.SECTION_TIER.get(section, "T2")
        return src["name"], [{**e, "source": src["name"], "tier": tier} for e in entries], None

    records, failures = [], []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        for name, recs, err in pool.map(run, jobs):
            if err:
                failures.append((name, err))
            else:
                records.extend(recs)
    return records, failures, len(jobs)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sources", default="config/sources.yaml")
    ap.add_argument("--since", help="watermark，ISO 日期或时间；不带时区按 UTC+8")
    ap.add_argument("--sections", default="companies,media,paper_sources")
    ap.add_argument("--include-tbd", action="store_true", help="也抓 status: tbd 的信源")
    ap.add_argument("--timeout", type=float, default=20)
    ap.add_argument("--max-per-feed", type=int, default=50)
    args = ap.parse_args(argv)

    config = sources_config.load(args.sources)
    since = parse_since(args.since) if args.since else None
    sections = [s.strip() for s in args.sections.split(",") if s.strip()]
    records, failures, total = collect(config, sections, args.include_tbd, args.timeout, args.max_per_feed)
    for rec in filter_and_dedupe(records, since):
        print(json.dumps({k: rec.get(k, "") for k in ("title", "url", "source", "published", "tier")}, ensure_ascii=False))
    print(f"[collect_feeds] 信源 {total} 个，失败 {len(failures)} 个", file=sys.stderr)
    for name, err in failures:
        print(f"[collect_feeds] 未抓到：{name}（{err}）", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
