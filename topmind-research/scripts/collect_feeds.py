#!/usr/bin/env python3
"""collect 的可选抓取脚本：读 sources.yaml 里的可机读渠道，按 watermark 过滤、URL 规范化去重，输出 JSONL。

只用 Python 标准库。用法（在技能目录 topmind-research/ 下执行）：

  python3 scripts/collect_feeds.py --sources config/sources.yaml --since 2026-10-01
  python3 scripts/collect_feeds.py --since 2026-10-01T08:00:00+08:00 --sections companies,media --report feeds-status.md
  python3 scripts/collect_feeds.py --since 2026-10-01 --ca-bundle /path/to/bundle.pem

读取的渠道：rss / rss_extra（RSS 或 Atom）、hf_api（Hugging Face 组织模型列表）、gh_api（GitHub 组织仓库或 releases）、
papers_api（Hugging Face 每日论文，按窗口逐日取）。list_api 和人看的列表页不处理，由 agent 按 references/collect.md 读取。

每行输出一个 JSON：title / url / source / published / tier / section / kind / channel / publisher，论文另有 arxiv_id，
HF 每日论文另有 upvotes。published 统一为 UTC+8 的 ISO 时间；只有日期的按当日 00:00（UTC+8）计。

覆盖检查：某个渠道抓到的最早一条仍晚于 --since，或条目数超过 --max-per-feed 被截断，都会在 stderr 写警告；
加 --report 时把「信源状态」写成 Markdown，周报照抄。证书校验始终开启；缺新根证书时用 --ca-bundle 追加，不要跳过校验。
"""
from __future__ import annotations

import argparse
import gzip
import html
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sources_config  # noqa: E402

VERSION = "0.2.1"
UA = f"Mozilla/5.0 (compatible; topmind-research/{VERSION} collect; +https://github.com/topmindspace/topmind-research)"
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}
# 按信源配置的请求头（sources.yaml 的 headers 字段）：default = 脚本自己的 UA；browser = 全套浏览器头；
# none = 不主动带 UA（urllib 会带自己的默认 UA）
HEADER_PROFILES = {"default": {"User-Agent": UA}, "browser": BROWSER_HEADERS, "none": {}}
CA_BUNDLE_ENV = "TOPMIND_CA_BUNDLE"
TRACKING_PARAMS = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "ref_src", "spm", "from", "source"}
CST = timezone(timedelta(hours=8))
MAX_WORKERS = 6
# 日期字段按优先级取，不按 XML 里出现的先后：发布时间优先，更新时间兜底
DATE_FIELDS = ("published", "pubdate", "issued", "date", "created", "updated", "modified")
ARXIV_ID = re.compile(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})")
PAPERS_API_MAX_DAYS = 8


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
    """按 names 的优先级取第一个非空子元素文本（不按文档顺序）。"""
    found: dict[str, str] = {}
    for child in elem:
        name = _local(child.tag)
        if name in names and name not in found and (child.text or "").strip():
            found[name] = child.text.strip()
    for name in names:
        if name in found:
            return found[name]
    return ""


def parse_date(value) -> datetime | None:
    """解析 RFC 822 / ISO 8601，返回带时区的 datetime。没有时区的按 UTC+8，只有日期的按当日 00:00（UTC+8）。"""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=CST)
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
        dt = dt.replace(tzinfo=CST)
    return dt


def to_cst_iso(dt: datetime | None) -> str:
    return dt.astimezone(CST).isoformat() if dt else ""


def clean_title(title: str) -> str:
    return " ".join(html.unescape(title or "").split())


def hf_blog_publisher(url: str) -> str | None:
    """Hugging Face 博客里其他组织发的文章（/blog/<org>/<slug>）按作者组织记发布方。"""
    parts = urlsplit(url)
    if (parts.hostname or "").lower() != "huggingface.co":
        return None
    segs = [s for s in parts.path.split("/") if s]
    if len(segs) >= 3 and segs[0] == "blog":
        return segs[1]
    if len(segs) == 2 and segs[0] == "blog":
        return "Hugging Face"
    return None


def parse_feed(xml_bytes: bytes, base_url: str = "") -> list[dict]:
    """解析 RSS 2.0 / RSS 1.0(RDF) / Atom，返回 [{title, url, published(datetime|None)}]。相对链接按 base_url 补全。"""
    root = ET.fromstring(xml_bytes)
    entries: list[dict] = []
    for elem in root.iter():
        if _local(elem.tag) not in ("item", "entry"):
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
            if guid.startswith(("http", "/")):
                link = guid
        if link and base_url and not urlsplit(link).scheme:
            link = urljoin(base_url, link)
        published = parse_date(_child_text(elem, *DATE_FIELDS))
        if title and link:
            entries.append({"title": clean_title(title), "url": link, "published": published})
    return entries


def parse_hf_models(data: bytes) -> list[dict]:
    """https://huggingface.co/api/models?author=<org>&sort=createdAt&direction=-1 的返回。"""
    out = []
    for m in json.loads(data):
        mid = m.get("id") or m.get("modelId")
        if not mid:
            continue
        out.append({
            "title": f"Hugging Face 新模型：{mid}",
            "url": f"https://huggingface.co/{mid}",
            "published": parse_date(m.get("createdAt") or ""),
            "kind": "model",
        })
    return out


def parse_gh(data: bytes) -> list[dict]:
    """GitHub 组织仓库列表（/orgs/<org>/repos?sort=created）或 releases 列表（/repos/<o>/<r>/releases）。"""
    out = []
    for r in json.loads(data):
        if "tag_name" in r:
            if r.get("draft"):
                continue
            name = r.get("name") or r["tag_name"]
            out.append({"title": f"GitHub release：{name}", "url": r.get("html_url", ""),
                        "published": parse_date(r.get("published_at") or r.get("created_at") or ""), "kind": "release"})
        elif r.get("full_name"):
            if r.get("fork"):
                continue
            desc = clean_title(r.get("description") or "")
            title = f"GitHub 新仓库：{r['full_name']}" + (f"（{desc[:60]}）" if desc else "")
            out.append({"title": title, "url": r.get("html_url", ""),
                        "published": parse_date(r.get("created_at") or ""), "kind": "repo"})
    return [e for e in out if e["url"]]


def parse_hf_daily_papers(data: bytes) -> list[dict]:
    """https://huggingface.co/api/daily_papers?date=YYYY-MM-DD 的返回。"""
    out = []
    for x in json.loads(data):
        paper = x.get("paper") or {}
        pid = paper.get("id")
        if not pid:
            continue
        out.append({
            "title": clean_title(x.get("title") or paper.get("title") or pid),
            "url": f"https://huggingface.co/papers/{pid}",
            "published": parse_date(x.get("publishedAt") or paper.get("publishedAt") or ""),
            "kind": "paper",
            "arxiv_id": pid,
            "upvotes": int(paper.get("upvotes") or 0),
        })
    return out


def ssl_context(ca_bundle: str | None) -> ssl.SSLContext:
    """系统默认 CA + 可选追加的 CA 文件。始终校验证书和主机名，不提供关闭校验的开关。"""
    ctx = ssl.create_default_context()
    if ca_bundle:
        ctx.load_verify_locations(cafile=ca_bundle)
    return ctx


def build_headers(profile: str | None, accept: str | None = None) -> dict[str, str]:
    if profile and profile not in HEADER_PROFILES:
        raise ValueError(f"未知 headers 取值：{profile}")
    headers = dict(HEADER_PROFILES[profile or "default"])
    headers["Accept-Encoding"] = "gzip"
    if accept:
        headers["Accept"] = accept
    return headers


def fetch(url: str, timeout: float, headers: dict[str, str] | None = None, context: ssl.SSLContext | None = None) -> bytes:
    req = urllib.request.Request(url, headers=headers if headers is not None else build_headers("default"))
    with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:
        data = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            data = gzip.decompress(data)
        return data


def parse_since(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=CST)
    return dt


def _sort_key(rec: dict) -> datetime:
    dt = parse_date(rec.get("published"))
    return dt if dt else datetime.min.replace(tzinfo=timezone.utc)


def filter_and_dedupe(records: list[dict], since: datetime | None) -> list[dict]:
    """按 watermark 过滤（没有日期的条目保留，交给 agent 判断），按规范化 URL 去重，重复时保留级别更高的来源。
    按带时区的 datetime 从新到旧排序；输出的 published 统一为 UTC+8 ISO 字符串。"""
    best: dict[str, dict] = {}
    order: list[str] = []
    for rec in records:
        dt = parse_date(rec.get("published"))
        if since is not None and dt is not None and dt <= since:
            continue
        key = normalize_url(rec["url"])
        rec = {**rec, "url": key, "published": to_cst_iso(dt)}
        if key not in best:
            best[key] = rec
            order.append(key)
        elif rec.get("tier", "T9") < best[key].get("tier", "T9"):
            best[key] = rec
    out = [best[k] for k in order]
    out.sort(key=_sort_key, reverse=True)
    return out


def coverage_warnings(entries: list[dict], total: int, max_per_feed: int, since: datetime | None) -> list[str]:
    """entries 是截断后保留的条目，total 是截断前的条目数。

    - 被截断且保留的最早一条仍晚于窗口起点（或没给窗口）：窗口内有条目被截掉，警告「被截断」
    - 没截断但最早一条晚于窗口起点：信源本身只给最近几条，警告「未覆盖完整窗口」
    截掉的全是窗口外的旧条目时不警告。"""
    dated = [e["published"] for e in entries if e.get("published")]
    oldest = min(dated) if dated else None
    gap = since is not None and oldest is not None and oldest > since
    truncated = bool(max_per_feed) and total > max_per_feed
    if truncated and (since is None or gap):
        where = f"，保留的最早一条 {to_cst_iso(oldest)[:16]} 晚于窗口起点 {to_cst_iso(since)[:16]}，窗口前段缺失" if gap else ""
        return [f"被截断：共 {total} 条，只保留最新 {max_per_feed} 条（--max-per-feed，0 = 不限）{where}"]
    if gap:
        return [f"未覆盖完整窗口：最早一条 {to_cst_iso(oldest)[:16]} 晚于窗口起点 {to_cst_iso(since)[:16]}，之前的条目需另查"]
    return []


def _daily_urls(base: str, since: datetime | None, now: datetime) -> list[str]:
    start = (since.astimezone(CST).date() if since else now.date() - timedelta(days=6))
    days = min((now.date() - start).days + 1, PAPERS_API_MAX_DAYS)
    sep = "&" if "?" in base else "?"
    return [f"{base}{sep}date={(now.date() - timedelta(days=i)).isoformat()}" for i in range(max(days, 1))]


def plan_jobs(config: dict, sections: list[str], include_tbd: bool) -> tuple[list[tuple[str, dict, str]], list[tuple[str, dict]]]:
    """返回 (要抓的 (分组, 信源, 渠道字段), 没有可抓渠道、须 agent 读页面的 (分组, 信源))。"""
    jobs, manual = [], []
    for section in sections:
        for src in config.get(section, []):
            if src.get("status") == "tbd" and not include_tbd:
                manual.append((section, src))
                continue
            channels = [f for f in sources_config.FEED_FIELDS if src.get(f)]
            if not channels:
                manual.append((section, src))
            for ch in channels:
                jobs.append((section, src, ch))
    return jobs, manual


def resolve_ca(src: dict, cli_ca: str | None, sources_dir: Path) -> str | None:
    if src.get("ca_bundle"):
        p = Path(os.path.expanduser(src["ca_bundle"]))
        return str(p if p.is_absolute() else sources_dir / p)
    return cli_ca


def collect(config: dict, sections: list[str], include_tbd: bool, timeout: float, max_per_feed: int,
            since: datetime | None = None, ca_bundle: str | None = None, sources_dir: Path = Path("."),
            now: datetime | None = None, fetcher=fetch):
    """抓取全部渠道。返回 (records, failures, status_rows, manual)。fetcher 可替换，便于测试。"""
    now = now or datetime.now(CST)
    jobs, manual = plan_jobs(config, sections, include_tbd)
    contexts: dict[str | None, ssl.SSLContext] = {}

    def ctx_for(path):
        if path not in contexts:
            contexts[path] = ssl_context(path)
        return contexts[path]

    def run(job):
        section, src, ch = job
        name = src["name"]
        label = f"{name}.{ch}"
        try:
            ctx = ctx_for(resolve_ca(src, ca_bundle, sources_dir))
            url = src[ch]
            if ch in ("rss", "rss_extra"):
                entries = parse_feed(fetcher(url, timeout, build_headers(src.get("headers")), ctx), base_url=url)
            elif ch == "hf_api":
                entries = parse_hf_models(fetcher(url, timeout, build_headers(src.get("headers"), "application/json"), ctx))
            elif ch == "gh_api":
                entries = parse_gh(fetcher(url, timeout, build_headers(src.get("headers"), "application/vnd.github+json"), ctx))
            else:  # papers_api：当天的列表可能还没生成（返回 400/404），单日失败跳过，全部失败才算没抓到
                entries, day_errors, urls = [], [], _daily_urls(url, since, now)
                for u in urls:
                    try:
                        entries.extend(parse_hf_daily_papers(fetcher(u, timeout, build_headers(src.get("headers"), "application/json"), ctx)))
                    except urllib.error.HTTPError as exc:
                        day_errors.append(f"{u.rsplit('=', 1)[-1]} HTTP {exc.code}")
                if len(day_errors) == len(urls):
                    raise ValueError("逐日请求全部失败：" + "；".join(day_errors))
        except ssl.SSLError as exc:
            return label, None, _ssl_hint(src, exc), []
        except urllib.error.URLError as exc:
            if isinstance(getattr(exc, "reason", None), ssl.SSLError):
                return label, None, _ssl_hint(src, exc.reason), []
            return label, None, f"{type(exc).__name__}: {exc}", []
        except (TimeoutError, ET.ParseError, OSError, ValueError) as exc:
            return label, None, f"{type(exc).__name__}: {exc}", []
        total = len(entries)
        entries.sort(key=lambda e: e["published"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        limit = 0 if ch == "papers_api" else max_per_feed
        if limit:
            entries = entries[:limit]
        warns = coverage_warnings(entries, total, limit, since if ch != "papers_api" else None)
        tier = sources_config.SECTION_TIER.get(section, "T2")
        kind_default = "paper" if section == "paper_sources" else "news"
        recs = []
        for e in entries:
            rec = {**e, "source": name, "tier": tier, "section": section, "channel": ch,
                   "kind": e.get("kind") or kind_default}
            rec["publisher"] = hf_blog_publisher(e["url"]) or name
            m = ARXIV_ID.search(e["url"])
            if m:
                rec["arxiv_id"] = m.group(1)
            recs.append(rec)
        in_window = sum(1 for e in entries if since is None or not e["published"] or e["published"] > since)
        return label, recs, None, [(label, total, in_window, warns)]

    records, failures, rows = [], [], []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        for label, recs, err, row in pool.map(run, jobs):
            if err:
                failures.append((label, err))
            else:
                records.extend(recs)
                rows.extend(row)
    return records, failures, rows, manual


def _ssl_hint(src: dict, exc: Exception) -> str:
    msg = f"SSL 证书校验失败：{exc}"
    if src.get("ca_root"):
        msg += f"。可能缺根证书，下载 {src['ca_root']} 后用 --ca-bundle（或环境变量 {CA_BUNDLE_ENV}）追加，不要跳过校验"
    else:
        msg += f"。如是本机 CA 库缺新根证书，用 --ca-bundle（或环境变量 {CA_BUNDLE_ENV}）追加，不要跳过校验"
    return msg


def status_markdown(total_jobs: int, failures, rows, manual, since: datetime | None) -> str:
    lines = ["## 信源状态（collect_feeds.py 自动生成）", ""]
    window = f"窗口起点 {to_cst_iso(since)[:16]}（UTC+8）" if since else "未指定窗口"
    lines.append(f"- 可机读渠道 {total_jobs} 个，抓到 {len(rows)} 个，失败 {len(failures)} 个；{window}")
    zero = [r[0] for r in rows if r[2] == 0]
    if zero:
        lines.append(f"- 抓到但窗口内 0 条（不是没抓到）：{'、'.join(zero)}")
    warned = [(r[0], w) for r in rows for w in r[3]]
    if warned:
        lines.append("- 覆盖警告：")
        lines.extend(f"  - {label}：{w}" for label, w in warned)
    if failures:
        lines.append("- 本次未抓到：")
        lines.extend(f"  - {label}（{err}）" for label, err in failures)
    if manual:
        lines.append("- 没有可机读渠道、须按页面读取（脚本未处理）：")
        for section, src in manual:
            lines.append(f"  - {src['name']}（{section}，fetch: {src.get('fetch', '?')}，status: {src.get('status', '?')}）")
    return "\n".join(lines) + "\n"


OUTPUT_FIELDS = ("title", "url", "source", "published", "tier", "section", "kind", "channel", "publisher", "arxiv_id", "upvotes")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sources", default="config/sources.yaml")
    ap.add_argument("--since", help="watermark，ISO 日期或时间；不带时区按 UTC+8")
    ap.add_argument("--sections", default="companies,media,paper_sources")
    ap.add_argument("--include-tbd", action="store_true", help="也抓 status: tbd 的信源")
    ap.add_argument("--timeout", type=float, default=20)
    ap.add_argument("--max-per-feed", type=int, default=100, help="每个渠道最多保留的条目数（按时间取最新），0 = 不限")
    ap.add_argument("--ca-bundle", default=os.environ.get(CA_BUNDLE_ENV),
                    help=f"追加信任的 CA 文件（PEM），用于本机缺新根证书的情况；也可用环境变量 {CA_BUNDLE_ENV}。证书校验不会关闭")
    ap.add_argument("--report", help="把信源状态写到这个 Markdown 文件，周报「信源状态」照抄")
    args = ap.parse_args(argv)

    config = sources_config.load(args.sources)
    since = parse_since(args.since) if args.since else None
    sections = [s.strip() for s in args.sections.split(",") if s.strip()]
    records, failures, rows, manual = collect(
        config, sections, args.include_tbd, args.timeout, args.max_per_feed,
        since=since, ca_bundle=args.ca_bundle, sources_dir=Path(args.sources).resolve().parent)
    for rec in filter_and_dedupe(records, since):
        print(json.dumps({k: rec[k] for k in OUTPUT_FIELDS if rec.get(k) not in (None, "")}, ensure_ascii=False))
    total = len(rows) + len(failures)
    print(f"[collect_feeds] 可机读渠道 {total} 个，失败 {len(failures)} 个", file=sys.stderr)
    for label, total_n, in_window, warns in rows:
        for w in warns:
            print(f"[collect_feeds] 警告：{label} {w}", file=sys.stderr)
    for label, err in failures:
        print(f"[collect_feeds] 未抓到：{label}（{err}）", file=sys.stderr)
    if args.report:
        Path(args.report).write_text(status_markdown(total, failures, rows, manual, since), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
