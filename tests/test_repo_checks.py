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

    def test_old_wechat_skill_name_is_forbidden(self):
        def hits(line):
            return [label for pat, label in check_skill_refs.FORBIDDEN if pat.search(line)]
        self.assertTrue(hits("公众号排版与定稿 → topmind-wechat，其他长文"))
        self.assertEqual(hits("公众号排版与定稿 → topmind-wechat-post，其他长文"), [])


class SourcesWeeklyTest(unittest.TestCase):
    ROWS = [
        ("companies", "A", "blog", "https://a.example", "ok", "200"),
        ("companies", "B", "blog", "https://b.example", "ok", "404"),
        ("companies", "C", "rss", "https://c.example", "ok", "gaierror"),
        ("companies", "D", "blog", "https://d.example", "ok", "403"),
        ("media", "E", "url", "https://e.example", "ok", "Timeout"),
        ("media", "F", "url", "https://f.example", "ok", "SSLError"),
        ("companies", "G", "blog", "https://g.example", "blocked", "404"),
    ]

    def test_classify(self):
        self.assertEqual(check_sources.classify("200"), "ok")
        self.assertEqual(check_sources.classify("301"), "ok")
        self.assertEqual(check_sources.classify("404"), "broken")
        self.assertEqual(check_sources.classify("410"), "broken")
        self.assertEqual(check_sources.classify("gaierror"), "broken")
        for code in ("403", "429", "503", "Timeout", "SSLError", "RemoteDisconnected"):
            self.assertEqual(check_sources.classify(code), "warn", code)

    def test_summarize_only_counts_ok_sources(self):
        broken, warn, expected = check_sources.summarize(self.ROWS)
        self.assertEqual([r[1] for r in broken], ["B", "C"])
        self.assertEqual([r[1] for r in warn], ["D", "E", "F"])
        self.assertEqual([r[1] for r in expected], ["G"])

    def test_report_lists_sections(self):
        broken, warn, expected = check_sources.summarize(self.ROWS)
        report = check_sources.render_report(broken, warn, expected, len(self.ROWS), ["x: 缺少 name"])
        for word in ("## 失效", "## 警告", "## 预期打不开", "## 字段检查", "companies/B"):
            self.assertIn(word, report)

    def test_strict_exit_code(self):
        rows = [("companies", "B", "blog", "https://b.example", "ok", "404")]
        orig = check_sources.reachability
        check_sources.reachability = lambda *a, **k: rows
        try:
            import contextlib, io, os
            from unittest import mock
            env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_ACTIONS", "GITHUB_STEP_SUMMARY")}
            with mock.patch.dict(os.environ, env, clear=True), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(check_sources.main(["--strict"]), 2)
                self.assertEqual(check_sources.main([]), 0)
        finally:
            check_sources.reachability = orig

    def test_weekly_workflow_does_not_swallow_failures(self):
        from _paths import ROOT
        wf = (ROOT / ".github" / "workflows" / "sources-weekly.yml").read_text(encoding="utf-8")
        self.assertNotIn("|| true", wf)
        self.assertIn("--strict", wf)


if __name__ == "__main__":
    unittest.main()
