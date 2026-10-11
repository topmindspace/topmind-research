import unittest

from _paths import FIXTURES, SKILL

import check_citations as cc


class CheckCitationsTest(unittest.TestCase):
    def test_ok_report(self):
        errors, warnings, urls = cc.check((FIXTURES / "report_ok.md").read_text(encoding="utf-8"))
        self.assertEqual(errors, [])
        self.assertEqual(len(urls), 3)

    def test_bad_report(self):
        errors, _, _ = cc.check((FIXTURES / "report_bad.md").read_text(encoding="utf-8"))
        text = "\n".join(errors)
        self.assertIn("[3] 重复", text)
        self.assertIn("[4] 在来源表里不存在", text)
        self.assertIn("[2] 在正文没有被引用", text)
        self.assertIn("[2] 缺少「访问", text)
        self.assertIn("[3] 缺少 URL", text)

    def test_missing_sources_section(self):
        errors, _, _ = cc.check("正文 [1]。\n")
        self.assertTrue(any("没有「## 来源」" in e for e in errors))

    def test_heading_synonyms(self):
        text = "正文 [1]。\n\n## 参考资料\n\n[1] A · B · T0 · 发布 2026-10-06 · 访问 2026-10-08 · https://e.com/a\n"
        errors, warnings, _ = cc.check(text)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_tier_published_and_paywall_warnings(self):
        text = "正文 [1]。\n\n## 来源\n\n[1] A · WSJ · 访问 2026-10-08 · https://www.wsj.com/tech/x\n"
        errors, warnings, _ = cc.check(text)
        self.assertEqual(errors, [])
        joined = "\n".join(warnings)
        self.assertIn("缺少级别", joined)
        self.assertIn("缺少「发布", joined)
        self.assertIn("付费墙", joined)

    def test_count_sentences(self):
        cited, total = cc.count_sentences((FIXTURES / "report_ok.md").read_text(encoding="utf-8"))
        self.assertEqual(cited, 2)
        self.assertGreaterEqual(total, 4)

    def test_templates_pass_with_placeholders(self):
        for name in ("analyze-report.md", "collect-weekly.md", "fact-sheet.md"):
            text = (SKILL / "assets" / "templates" / name).read_text(encoding="utf-8")
            errors, warnings, _ = cc.check(text, allow_placeholders=True)
            self.assertEqual(errors, [], name)
            self.assertTrue(warnings, name)


if __name__ == "__main__":
    unittest.main()
