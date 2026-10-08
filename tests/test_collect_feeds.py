import unittest

from _paths import FIXTURES

import collect_feeds as cf


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
        self.assertTrue(entries[0]["published"].startswith("2026-10-06T10:00:00"))
        self.assertEqual(entries[2]["published"], "")

    def test_atom_prefers_alternate_and_falls_back_to_id(self):
        entries = cf.parse_feed((FIXTURES / "atom.xml").read_bytes())
        self.assertEqual(entries[0]["url"], "https://example.org/papers/b")
        self.assertEqual(entries[1]["url"], "https://example.org/papers/c")
        self.assertEqual(entries[1]["title"], "Paper C")


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

    def test_since_without_timezone_is_utc8(self):
        self.assertEqual(cf.parse_since("2026-10-01").utcoffset().total_seconds(), 8 * 3600)


if __name__ == "__main__":
    unittest.main()
