import ssl
import unittest
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

from _paths import FIXTURES

import collect_feeds as cf

CST = timezone(timedelta(hours=8))


class NormalizeUrlTest(unittest.TestCase):
    def test_strips_tracking_fragment_and_slash(self):
        self.assertEqual(
            cf.normalize_url("https://Example.com/news/model-a/?utm_source=rss&id=7#top"),
            "https://example.com/news/model-a?id=7",
        )

    def test_default_port_and_root(self):
        self.assertEqual(cf.normalize_url("HTTPS://EXAMPLE.COM:443/"), "https://example.com/")

    def test_keeps_meaningful_query(self):
        self.assertEqual(cf.normalize_url("https://a.com/p?b=2&a=1&fbclid=x"), "https://a.com/p?b=2&a=1")


class ParseFeedTest(unittest.TestCase):
    def test_rss2(self):
        entries = cf.parse_feed((FIXTURES / "rss2.xml").read_bytes())
        self.assertEqual([e["title"] for e in entries], ["Model A released", "Old post", "No date post"])
        self.assertEqual(entries[0]["published"], datetime(2026, 10, 6, 10, 0, tzinfo=timezone.utc))
        self.assertIsNotNone(entries[0]["published"].tzinfo)
        self.assertIsNone(entries[2]["published"])

    def test_atom_prefers_alternate_and_falls_back_to_id(self):
        entries = cf.parse_feed((FIXTURES / "atom.xml").read_bytes())
        self.assertEqual(entries[0]["url"], "https://example.org/papers/b")
        self.assertEqual(entries[1]["url"], "https://example.org/papers/c")
        self.assertEqual(entries[1]["title"], "Paper C")

    def test_atom_published_wins_over_earlier_updated(self):
        entries = cf.parse_feed((FIXTURES / "atom_updated_first.xml").read_bytes())
        self.assertEqual(entries[0]["published"], datetime(2026, 10, 7, 14, 42, tzinfo=timezone(timedelta(hours=-4))))

    def test_updated_used_only_as_fallback(self):
        entries = cf.parse_feed((FIXTURES / "atom.xml").read_bytes())
        self.assertEqual(entries[0]["published"], datetime(2026, 10, 5, 8, 0, tzinfo=timezone.utc))

    def test_html_entities_unescaped(self):
        entries = cf.parse_feed((FIXTURES / "atom_updated_first.xml").read_bytes())
        self.assertEqual(entries[0]["title"], "Everything announced at Microsoft\u2019s event")

    def test_relative_links_resolved_against_feed_url(self):
        entries = cf.parse_feed((FIXTURES / "rss_relative.xml").read_bytes(), base_url="https://ernie.baidu.com/blog/index.xml")
        self.assertEqual(entries[0]["url"], "https://ernie.baidu.com/blog/posts/ernie-5.1-0508-release/")
        self.assertEqual(entries[1]["url"], "https://ernie.baidu.com/blog/posts/day-only/")

    def test_date_only_is_midnight_utc8(self):
        entries = cf.parse_feed((FIXTURES / "rss_relative.xml").read_bytes())
        self.assertEqual(entries[1]["published"], datetime(2026, 10, 6, tzinfo=CST))


class JsonChannelsTest(unittest.TestCase):
    def test_hf_models(self):
        entries = cf.parse_hf_models((FIXTURES / "hf_models.json").read_bytes())
        self.assertEqual([e["url"] for e in entries], ["https://huggingface.co/Qwen/Qwen-Image-2.1-PE-I2I", "https://huggingface.co/Qwen/Qwen4-0.5B"])
        self.assertEqual(entries[0]["kind"], "model")
        self.assertEqual(entries[0]["published"], datetime(2026, 9, 20, 8, 0, tzinfo=timezone.utc))

    def test_gh_repos_skip_forks_and_unescape(self):
        entries = cf.parse_gh((FIXTURES / "gh_repos.json").read_bytes())
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["kind"], "repo")
        self.assertIn("A & B bench", entries[0]["title"])

    def test_gh_releases_skip_drafts(self):
        entries = cf.parse_gh((FIXTURES / "gh_releases.json").read_bytes())
        self.assertEqual([e["kind"] for e in entries], ["release"])
        self.assertEqual(entries[0]["title"], "GitHub release：v1.2.0")

    def test_hf_daily_papers(self):
        entries = cf.parse_hf_daily_papers((FIXTURES / "hf_daily_papers.json").read_bytes())
        self.assertEqual(entries[0]["arxiv_id"], "2610.08448")
        self.assertEqual(entries[0]["upvotes"], 153)
        self.assertEqual(entries[0]["kind"], "paper")

    def test_hf_blog_publisher(self):
        self.assertEqual(cf.hf_blog_publisher("https://huggingface.co/blog/nvidia/nemotron-ioi"), "nvidia")
        self.assertEqual(cf.hf_blog_publisher("https://huggingface.co/blog/some-post"), "Hugging Face")
        self.assertIsNone(cf.hf_blog_publisher("https://example.com/blog/a/b"))


class FilterDedupeTest(unittest.TestCase):
    def test_since_and_dedupe_keeps_higher_tier(self):
        records = [
            {"title": "A (media)", "url": "https://example.com/a/?utm_medium=x", "published": "2026-10-06T10:00:00+00:00", "tier": "T2", "source": "M"},
            {"title": "A", "url": "https://EXAMPLE.com/a", "published": "2026-10-06T10:00:00+00:00", "tier": "T0", "source": "Co"},
            {"title": "old", "url": "https://example.com/old", "published": "2026-09-21T10:00:00+00:00", "tier": "T0", "source": "Co"},
            {"title": "undated", "url": "https://example.com/u", "published": "", "tier": "T0", "source": "Co"},
        ]
        out = cf.filter_and_dedupe(records, cf.parse_since("2026-10-01"))
        self.assertEqual([r["title"] for r in out], ["A", "undated"])
        self.assertEqual(out[0]["url"], "https://example.com/a")
        self.assertEqual(out[0]["published"], "2026-10-06T18:00:00+08:00")

    def test_mixed_timezones_sorted_by_instant(self):
        # 字符串排序会把 -04:00 的 14:42 排在 +00:00 的 20:00 前面；按时刻 18:42Z 早于 20:00Z
        entries = cf.parse_feed((FIXTURES / "atom_updated_first.xml").read_bytes())
        out = cf.filter_and_dedupe([{**e, "tier": "T2"} for e in entries], None)
        self.assertEqual([r["title"] for r in out], ["Later UTC post", "Everything announced at Microsoft\u2019s event"])
        self.assertEqual(out[0]["published"], "2026-10-08T04:00:00+08:00")
        self.assertEqual(out[1]["published"], "2026-10-08T02:42:00+08:00")

    def test_since_without_timezone_is_utc8(self):
        self.assertEqual(cf.parse_since("2026-10-01").utcoffset().total_seconds(), 8 * 3600)


class CoverageTest(unittest.TestCase):
    def test_window_not_covered(self):
        since = cf.parse_since("2026-10-01")
        entries = [{"published": datetime(2026, 10, 6, tzinfo=CST)}, {"published": datetime(2026, 10, 7, tzinfo=CST)}]
        warns = cf.coverage_warnings(entries, 2, 50, since)
        self.assertEqual(len(warns), 1)
        self.assertIn("未覆盖完整窗口", warns[0])

    def test_truncated_inside_window(self):
        since = cf.parse_since("2026-10-01")
        entries = [{"published": datetime(2026, 10, 7, 12, tzinfo=CST)}]
        warns = cf.coverage_warnings(entries, 224, 1, since)
        self.assertEqual(len(warns), 1)
        self.assertIn("被截断：共 224 条", warns[0])
        self.assertIn("窗口前段缺失", warns[0])

    def test_truncated_outside_window_is_silent(self):
        since = cf.parse_since("2026-10-01")
        entries = [{"published": datetime(2026, 9, 30, tzinfo=CST)}]
        self.assertEqual(cf.coverage_warnings(entries, 1255, 1, since), [])

    def test_truncated_without_window_warns(self):
        warns = cf.coverage_warnings([{"published": datetime(2026, 9, 30, tzinfo=CST)}], 10, 1, None)
        self.assertIn("被截断", warns[0])

    def test_covered(self):
        since = cf.parse_since("2026-10-01")
        self.assertEqual(cf.coverage_warnings([{"published": datetime(2026, 9, 29, tzinfo=CST)}], 1, 50, since), [])


class FakeFetcher:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def __call__(self, url, timeout, headers, context):
        self.calls.append((url, headers, context))
        resp = self.responses[url.split("?date=")[0] if "?date=" in url else url]
        if isinstance(resp, Exception):
            raise resp
        return resp


class CollectTest(unittest.TestCase):
    def config(self):
        return {
            "companies": [
                {"name": "Co", "rss": "https://co.example/feed.xml", "status": "ok", "fetch": "http", "headers": "browser"},
                {"name": "Lab", "hf_api": "https://huggingface.co/api/models?author=Qwen", "gh_api": "https://api.github.com/orgs/QwenLM/repos", "status": "ok", "fetch": "js"},
                {"name": "PageOnly", "blog": "https://p.example", "status": "page-only", "fetch": "js", "note": "x"},
                {"name": "Pending", "rss": "https://t.example/feed", "status": "tbd", "fetch": "http", "note": "x"},
            ],
            "media": [
                {"name": "LP", "rss": "https://lp.example/feed", "status": "ok", "fetch": "http", "ca_root": "https://letsencrypt.org/certs/gen-y/root-yr.pem", "note": "x"},
            ],
        }

    def test_collect_channels_headers_coverage_and_failures(self):
        ssl_err = urllib.error.URLError(ssl.SSLCertVerificationError(1, "certificate verify failed"))
        fetcher = FakeFetcher({
            "https://co.example/feed.xml": (FIXTURES / "atom_updated_first.xml").read_bytes(),
            "https://huggingface.co/api/models?author=Qwen": (FIXTURES / "hf_models.json").read_bytes(),
            "https://api.github.com/orgs/QwenLM/repos": (FIXTURES / "gh_repos.json").read_bytes(),
            "https://lp.example/feed": ssl_err,
        })
        since = cf.parse_since("2026-10-01")
        records, failures, rows, manual = cf.collect(self.config(), ["companies", "media"], False, 5, 50, since=since, fetcher=fetcher)
        called = {c[0] for c in fetcher.calls}
        self.assertNotIn("https://t.example/feed", called)
        self.assertEqual({s["name"] for _, s in manual}, {"PageOnly", "Pending"})
        co_headers = next(h for u, h, _ in fetcher.calls if u.startswith("https://co.example"))
        self.assertIn("Sec-Fetch-Mode", co_headers)
        self.assertEqual(len(failures), 1)
        self.assertIn("root-yr.pem", failures[0][1])
        self.assertIn("不要跳过校验", failures[0][1])
        kinds = {r["kind"] for r in records}
        self.assertEqual(kinds, {"news", "model", "repo"})
        warned = {label for label, _, _, warns in rows if warns}
        self.assertIn("Co.rss", warned)  # 最早一条 10-07 晚于窗口起点 10-01
        md = cf.status_markdown(len(rows) + len(failures), failures, rows, manual, since)
        self.assertIn("未覆盖完整窗口", md)
        self.assertIn("本次未抓到", md)
        self.assertIn("PageOnly", md)

    def test_truncation_keeps_newest(self):
        fetcher = FakeFetcher({"https://co.example/feed.xml": (FIXTURES / "atom_updated_first.xml").read_bytes()})
        cfg = {"companies": [self.config()["companies"][0]]}
        records, failures, rows, _ = cf.collect(cfg, ["companies"], False, 5, 1, since=None, fetcher=fetcher)
        self.assertEqual([r["title"] for r in records], ["Later UTC post"])
        self.assertIn("被截断", rows[0][3][0])

    def test_papers_api_queries_each_day(self):
        fetcher = FakeFetcher({"https://huggingface.co/api/daily_papers": (FIXTURES / "hf_daily_papers.json").read_bytes()})
        cfg = {"paper_sources": [{"name": "HF Papers", "papers_api": "https://huggingface.co/api/daily_papers", "status": "ok", "fetch": "http"}]}
        now = datetime(2026, 10, 8, 9, 0, tzinfo=CST)
        records, failures, _, _ = cf.collect(cfg, ["paper_sources"], False, 5, 50, since=cf.parse_since("2026-10-01"), now=now, fetcher=fetcher)
        self.assertEqual(failures, [])
        self.assertEqual(len(fetcher.calls), 8)
        self.assertTrue(fetcher.calls[0][0].endswith("?date=2026-10-08"))
        self.assertEqual(records[0]["kind"], "paper")


    def test_papers_api_skips_missing_day(self):
        body = (FIXTURES / "hf_daily_papers.json").read_bytes()

        def fetcher(url, timeout, headers, context):
            if url.endswith("2026-10-08"):
                raise urllib.error.HTTPError(url, 400, "Bad Request", {}, None)
            return body

        cfg = {"paper_sources": [{"name": "HF Papers", "papers_api": "https://huggingface.co/api/daily_papers", "status": "ok", "fetch": "http"}]}
        now = datetime(2026, 10, 8, 9, 0, tzinfo=CST)
        records, failures, _, _ = cf.collect(cfg, ["paper_sources"], False, 5, 50, since=cf.parse_since("2026-10-06"), now=now, fetcher=fetcher)
        self.assertEqual(failures, [])
        self.assertTrue(records)


class TlsAndHeadersTest(unittest.TestCase):
    def test_default_context_verifies(self):
        ctx = cf.ssl_context(None)
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(ctx.check_hostname)

    def test_ca_bundle_appends_and_still_verifies(self):
        pem = Path(ssl.get_default_verify_paths().cafile or "")
        if not pem.is_file():
            self.skipTest("本机没有可用的 CA 文件")
        ctx = cf.ssl_context(str(pem))
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(ctx.check_hostname)
        self.assertGreater(ctx.cert_store_stats()["x509_ca"], 0)

    def test_missing_ca_bundle_raises(self):
        with self.assertRaises(OSError):
            cf.ssl_context("/nonexistent/bundle.pem")

    def test_no_switch_to_disable_verification(self):
        src = (Path(cf.__file__)).read_text(encoding="utf-8")
        self.assertNotIn("CERT_NONE", src)
        self.assertNotIn("_create_unverified_context", src)
        self.assertNotIn("check_hostname = False", src)

    def test_header_profiles(self):
        self.assertIn("topmind-research/", cf.build_headers("default")["User-Agent"])
        self.assertIn("Sec-Fetch-Mode", cf.build_headers("browser"))
        self.assertNotIn("User-Agent", cf.build_headers("none"))
        self.assertEqual(cf.build_headers(None, "application/json")["Accept"], "application/json")
        with self.assertRaises(ValueError):
            cf.build_headers("bogus")

    def test_per_source_ca_bundle_relative_to_sources(self):
        self.assertEqual(cf.resolve_ca({"ca_bundle": "certs/root.pem"}, None, Path("/cfg")), "/cfg/certs/root.pem")
        self.assertEqual(cf.resolve_ca({}, "/cli.pem", Path("/cfg")), "/cli.pem")


if __name__ == "__main__":
    unittest.main()
