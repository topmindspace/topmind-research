import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

import _paths  # noqa: F401
import rank_items as ri

TODAY = date(2026, 10, 8)
COMPANIES = {"OpenAI", "Anthropic", "NVIDIA", "Google DeepMind", "Mistral AI", "阿里/千问", "阿里", "千问"}


def news(title, company, published="2026-10-07T10:00:00+08:00", tier="T0", **kw):
    return {"title": title, "url": f"https://{company.lower().replace(' ', '')}.example/{title.replace(' ', '-')}",
            "source": company, "section": "companies", "tier": tier, "published": published, "kind": "news", **kw}


def paper(i, **kw):
    return {"title": f"Paper {i}", "url": f"https://arxiv.org/abs/2610.0{6000 + i}", "source": "arXiv cs.CL",
            "section": "paper_sources", "tier": "T0", "published": "2026-10-07T12:00:00+08:00", "kind": "paper",
            "arxiv_id": f"2610.0{6000 + i}", **kw}


class ScoreTest(unittest.TestCase):
    def test_meets_min_gives_full_source_score_to_funding(self):
        rec = {"title": "X raises", "url": "https://tc.example/x", "source": "TechCrunch", "section": "media",
               "tier": "T2", "published": "2026-10-07", "kind": "news", "category": "融资并购", "meets_min": True}
        scored = ri.score(rec, TODAY, COMPANIES)
        self.assertEqual(scored["score_parts"], {"来源": 3, "相关": 0, "新鲜": 2})

    def test_meets_min_false_caps_at_two(self):
        scored = ri.score(news("A", "OpenAI", meets_min=False), TODAY, COMPANIES)
        self.assertEqual(scored["score_parts"]["来源"], 2)

    def test_hf_blog_publisher_counts_as_company(self):
        rec = {"title": "Nemotron", "url": "https://huggingface.co/blog/nvidia/x", "source": "Hugging Face",
               "section": "companies", "tier": "T0", "published": "2026-10-07", "kind": "news", "publisher": "nvidia"}
        scored = ri.score(rec, TODAY, COMPANIES | {"Hugging Face"})
        self.assertEqual(scored["company"], "NVIDIA")
        self.assertEqual(scored["score_parts"]["相关"], 1)
        rec = {**rec, "url": "https://huggingface.co/blog/LiquidAI/open-d1", "publisher": "LiquidAI"}
        self.assertEqual(ri.score(rec, TODAY, COMPANIES | {"Hugging Face"})["score_parts"]["相关"], 0)

    def test_freshness_by_utc8_calendar_day(self):
        # 2026-10-05T20:00Z 是 UTC+8 的 10-06 04:00，距 10-08 两天
        rec = news("A", "OpenAI", published="2026-10-05T20:00:00+00:00")
        self.assertEqual(ri.score(rec, TODAY, COMPANIES)["score_parts"]["新鲜"], 2)
        rec = news("B", "OpenAI", published="2026-10-01")
        self.assertEqual(ri.score(rec, TODAY, COMPANIES)["score_parts"]["新鲜"], 1)
        rec = news("C", "OpenAI", published="")
        self.assertEqual(ri.score(rec, TODAY, COMPANIES)["score_parts"]["新鲜"], 0)


class RankTest(unittest.TestCase):
    def test_papers_never_enter_main_and_need_signal(self):
        records = [news(f"N{i}", c) for i, c in enumerate(["OpenAI", "Anthropic", "NVIDIA"])]
        records += [paper(i) for i in range(20)]
        records.append(paper(99, signal="官方博客提及"))
        records.append(paper(98, upvotes=40))
        result = ri.rank(records, TODAY, COMPANIES, top=15)
        self.assertTrue(all(r["kind"] != "paper" for r in result["main"]))
        self.assertEqual({r["title"] for r in result["papers"]}, {"Paper 99", "Paper 98"})
        self.assertEqual(result["papers_pool_count"], 20)

    def test_hf_daily_merges_into_arxiv_by_id(self):
        hf = {"title": "Paper 1 (HF)", "url": "https://huggingface.co/papers/2610.06001", "source": "Hugging Face Papers",
              "section": "paper_sources", "tier": "T0", "published": "2026-10-07", "kind": "paper", "arxiv_id": "2610.06001", "upvotes": 50}
        result = ri.rank([hf, paper(1)], TODAY, COMPANIES)
        self.assertEqual(len(result["papers"]), 1)
        self.assertTrue(result["papers"][0]["url"].startswith("https://arxiv.org/"))
        self.assertEqual(result["papers"][0]["upvotes"], 50)

    def test_company_cap(self):
        records = [news(f"O{i}", "OpenAI", published=f"2026-10-07T0{i}:00:00+08:00") for i in range(5)]
        result = ri.rank(records, TODAY, COMPANIES, top=15, company_cap=3)
        self.assertEqual(len(result["main"]), 3)
        self.assertTrue(all("同一公司" in r["cut_reason"] for r in result["truncated"]))

    def test_category_floor_replaces_lowest(self):
        companies = ["OpenAI", "Anthropic", "NVIDIA", "Google DeepMind", "Mistral AI"]
        records = [news(f"N{i}", companies[i % 5], published=f"2026-10-07T10:{i:02d}:00+08:00") for i in range(15)]
        funding = {"title": "Startup raises B", "url": "https://tc.example/b", "source": "TechCrunch", "section": "media",
                   "tier": "T2", "published": "2026-10-04", "kind": "news", "category": "融资并购", "meets_min": True}
        unverified = {"title": "Rumor raise", "url": "https://tc.example/r", "source": "TechCrunch", "section": "media",
                      "tier": "T2", "published": "2026-10-07", "kind": "news", "category": "政策监管"}
        result = ri.rank(records + [funding, unverified], TODAY, set(companies), top=15)
        titles = [r["title"] for r in result["main"]]
        self.assertIn("Startup raises B", titles)
        self.assertNotIn("Rumor raise", titles)  # 没达到核验最低要求，不保底
        self.assertEqual(len(titles), 15)
        self.assertTrue(any("保底" in r["cut_reason"] for r in result["truncated"]))

    def test_release_signals_bucket(self):
        model = {"title": "Hugging Face 新模型：Qwen/X", "url": "https://huggingface.co/Qwen/X", "source": "阿里/千问",
                 "section": "companies", "tier": "T0", "published": "2026-10-07", "kind": "model"}
        confirmed = {**model, "title": "Hugging Face 新模型：Qwen/Y", "url": "https://huggingface.co/Qwen/Y", "meets_min": True}
        result = ri.rank([model, confirmed], TODAY, COMPANIES)
        self.assertEqual([r["title"] for r in result["signals"]], ["Hugging Face 新模型：Qwen/X"])
        self.assertEqual([r["title"] for r in result["main"]], ["Hugging Face 新模型：Qwen/Y"])

    def test_event_merge_keeps_t0_primary(self):
        a = news("SynthID", "Google DeepMind", event="synthid")
        b = {"title": "TC SynthID", "url": "https://tc.example/s", "source": "TechCrunch", "section": "media",
             "tier": "T2", "published": "2026-10-07", "kind": "news", "event": "synthid", "category": "政策监管"}
        result = ri.rank([b, a], TODAY, COMPANIES)
        self.assertEqual(len(result["main"]), 1)
        self.assertEqual(result["main"][0]["title"], "SynthID")
        self.assertEqual(result["main"][0]["category"], "政策监管")
        self.assertEqual(result["main"][0]["also"][0]["source"], "TechCrunch")

    def test_load_jsonl_merges_annotations_and_drop(self):
        with tempfile.TemporaryDirectory() as d:
            feed = Path(d) / "feed.jsonl"
            ann = Path(d) / "ann.jsonl"
            feed.write_text(json.dumps(news("A", "OpenAI")) + "\n" + json.dumps(news("B", "OpenAI")) + "\n", encoding="utf-8")
            ann.write_text(json.dumps({"url": news("A", "OpenAI")["url"] + "/?utm_source=x", "category": "新品发布"}) + "\n"
                           + json.dumps({"url": news("B", "OpenAI")["url"], "drop": True}) + "\n"
                           + json.dumps({"url": "https://only.example/annotation", "category": "x"}) + "\n", encoding="utf-8")
            recs = ri.load_jsonl([str(feed), str(ann)])
        self.assertEqual([r["title"] for r in recs], ["A"])
        self.assertEqual(recs[0]["category"], "新品发布")

    def test_markdown_output(self):
        result = ri.rank([news("A", "OpenAI"), paper(1)], TODAY, COMPANIES)
        md = ri.to_markdown(result, TODAY, 15)
        self.assertIn("## 排序记录", md)
        self.assertIn("候选池里没有筛选信号、未入选的论文：1 篇", md)


if __name__ == "__main__":
    unittest.main()
