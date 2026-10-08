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
