import unittest

from _paths import SKILL

import check_skill_refs
import check_sources
import check_versions
import sources_config


class SourcesConfigTest(unittest.TestCase):
    def setUp(self):
        self.config = sources_config.load(SKILL / "config" / "sources.yaml")

    def test_schema(self):
        self.assertEqual(check_sources.validate(self.config), [])

    def test_parser_handles_quotes_and_comments(self):
        data = sources_config.parse('a:\n  - name: "x # y"  # 注释\n    url: https://e.com/#frag\n')
        self.assertEqual(data["a"][0], {"name": "x # y", "url": "https://e.com/#frag"})

    def test_parser_rejects_unknown_syntax(self):
        with self.assertRaises(ValueError):
            sources_config.parse("a:\n  - name: x\n      nested:\n  - [1, 2]\n")

    def test_no_community_sources(self):
        names = {i["name"] for items in self.config.values() for i in items}
        self.assertNotIn("Hacker News", names)
        self.assertNotIn("Papers with Code", names)

    def test_parser_null(self):
        data = sources_config.parse("people:\n  - name: A\n    x_handle: null\n    note: \"null\"\n")
        self.assertIsNone(data["people"][0]["x_handle"])
        self.assertEqual(data["people"][0]["note"], "null")

    def test_people_null_needs_status_and_note(self):
        bad = check_sources.validate({"people": [{"name": "A", "x_handle": None}]})
        self.assertTrue(any("null" in e for e in bad))
        ok = check_sources.validate({"people": [{"name": "A", "x_handle": None, "x_status": "none", "note": "依据"}]})
        self.assertEqual(ok, [])

    def test_people_candidate_needs_note(self):
        bad = check_sources.validate({"people": [{"name": "A", "x_handle": "TBD", "x_status": "candidate"}]})
        self.assertTrue(any("candidate" in e for e in bad))

    def test_status_values(self):
        bad = check_sources.validate({"media": [{"name": "X", "url": "https://x.com", "status": "ok_with_ca_note", "fetch": "html"}]})
        self.assertTrue(any("status" in e for e in bad))
        self.assertTrue(any("fetch" in e for e in bad))

    def test_js_page_without_machine_channel_is_not_ok(self):
        bad = check_sources.validate({"companies": [{"name": "X", "blog": "https://x.com", "status": "ok", "fetch": "js"}]})
        self.assertTrue(any("page-only" in e for e in bad))
        ok = check_sources.validate({"companies": [{"name": "X", "blog": "https://x.com", "status": "page-only", "fetch": "js", "note": "前端渲染"}]})
        self.assertEqual(ok, [])
        ok = check_sources.validate({"companies": [{"name": "X", "blog": "https://x.com", "status": "ok", "fetch": "js",
                                                    "hf_api": "https://huggingface.co/api/models?author=X"}]})
        self.assertEqual(ok, [])

    def test_ca_bundle_path_not_committed_and_headers_checked(self):
        bad = check_sources.validate({"media": [{"name": "X", "url": "https://x.com", "status": "ok", "fetch": "http",
                                                 "ca_bundle": "/opt/certs/bundle.pem", "headers": "chrome"}]})
        self.assertTrue(any("ca_bundle" in e for e in bad))
        self.assertTrue(any("headers" in e for e in bad))

    def test_company_x_accounts(self):
        accounts = {i["name"]: i.get("x_account") for i in self.config["companies"]}
        self.assertEqual(accounts["MiniMax"], "MiniMax_AI")
        self.assertEqual(accounts["字节跳动/Seed"], "ByteDanceSeed_")

    def test_tbd_has_note(self):
        bad = check_sources.validate({"media": [{"name": "X", "url": "https://x.com", "status": "tbd", "fetch": "http"}]})
        self.assertTrue(any("note" in e for e in bad))


class RepoChecksTest(unittest.TestCase):
    def test_versions_consistent(self):
        self.assertEqual(len(set(check_versions.collect().values())), 1)

    def test_skill_refs(self):
        self.assertEqual(check_skill_refs.scan(), [])


if __name__ == "__main__":
    unittest.main()
