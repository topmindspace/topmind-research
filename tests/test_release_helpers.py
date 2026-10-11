import json
import unittest

from _paths import ROOT

import changelog_section as cs


SAMPLE = """# Changelog

## Unreleased

- 待发

## 0.2.3 — 2026-10-08

### 特性支持

- 发 npm

## [0.2.2] - 2026-10-07

- 旧条目
"""


class ChangelogSectionTest(unittest.TestCase):
    def test_extracts_until_next_heading(self):
        body = cs.section(SAMPLE, "0.2.3")
        self.assertTrue(body.startswith("## 0.2.3 — 2026-10-08"))
        self.assertIn("- 发 npm", body)
        self.assertNotIn("0.2.2", body)

    def test_bracket_heading_and_last_section(self):
        body = cs.section(SAMPLE, "0.2.2")
        self.assertIn("- 旧条目", body)

    def test_missing_or_prefix_only(self):
        self.assertIsNone(cs.section(SAMPLE, "0.2.4"))
        self.assertIsNone(cs.section(SAMPLE, "0.2"))

    def test_current_version_has_notes(self):
        version = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["version"]
        text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIsNotNone(cs.section(text, version), f"CHANGELOG 缺少 {version} 段落")


class PackageJsonTest(unittest.TestCase):
    def test_publish_ready(self):
        pkg = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(pkg["name"], "@topmindspace/topmind-research")
        self.assertEqual(pkg.get("publishConfig", {}).get("access"), "public")
        self.assertIn("topmind-research/", pkg["files"])
        self.assertNotIn("private", pkg)


if __name__ == "__main__":
    unittest.main()
