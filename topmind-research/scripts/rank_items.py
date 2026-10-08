#!/usr/bin/env python3
"""collect 第 5 步「排序」的可选脚本：把候选条目分桶、打分、套公司上限和分类保底，输出前 N 条和排序记录。

只用 Python 标准库。用法（在技能目录 topmind-research/ 下执行）：

  python3 scripts/collect_feeds.py --since 2026-10-01 > feeds.jsonl
  python3 scripts/rank_items.py feeds.jsonl agent.jsonl --now 2026-10-08 --format md > ranking.md

输入是一个或多个 JSONL 文件，按规范化 URL 合并（后面文件里的非空字段覆盖前面的），所以 agent 可以只写
{"url": ..., "category": "融资并购", "meets_min": true} 这样的补充行。识别的字段：

  title / url / source / published / tier / section / kind / publisher / arxiv_id / upvotes   collect_feeds.py 输出
  company        归属公司；不写时 companies 分组的条目取 source
  category       config/categories.yaml 的 collect_categories 之一
  meets_min      true = 已达到 references/verification.md 第二节对该事实类型的最低要求
  direction_hit  true = 命中用户指定方向
  signal         论文筛选信号（如 "官方博客提及"），字符串或列表
  event          同一事件的合并键；同键条目合并为一条，级别最高的作主条目
  drop           true = agent 判定不收录（早于窗口、上期已收录等）

规则见 references/collect.md 第 5 步，本脚本是它的实现；两者不一致时以 collect.md 为准并修脚本。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import collect_feeds as cf  # noqa: E402
import sources_config  # noqa: E402

TIER_SCORE = {"T0": 3, "T1": 2, "T2": 1, "T3": 0}
SIGNAL_KINDS = ("model", "repo", "release")
DEFAULT_FLOOR = ("融资并购", "政策监管")


def load_jsonl(paths: list[str]) -> list[dict]:
    merged: dict[str, dict] = {}
    order: list[str] = []
    for path in paths:
        for lineno, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if not rec.get("url"):
                raise ValueError(f"{path} 第 {lineno} 行缺少 url")
            key = cf.normalize_url(rec["url"])
            if key not in merged:
                merged[key] = {}
                order.append(key)
            merged[key].update({k: v for k, v in rec.items() if v not in (None, "")})
            merged[key]["url"] = key
    out = []
    for key in order:
        rec = merged[key]
        if rec.get("drop"):
            continue
        if not rec.get("title"):
            print(f"[rank_items] 跳过：{key} 只有补充字段，没有对应条目", file=sys.stderr)
            continue
        out.append(rec)
    return out


def company_names(config: dict) -> set[str]:
    names = set()
    for src in config.get("companies", []):
        names.add(src["name"])
        names.update(part.strip() for part in src["name"].split("/") if part.strip())
    return names


def _canonical(name: str, companies: set[str]) -> str:
    low = name.lower()
    return next((c for c in companies if c.lower() == low), name)


def company_of(rec: dict, companies: set[str]) -> str:
    """归属公司：显式 company > 发布方（与信源不同时，如 HF 博客里 NVIDIA 发的文章）> companies 分组的信源名。"""
    if rec.get("company"):
        return _canonical(rec["company"], companies)
    publisher = rec.get("publisher")
    if publisher and publisher != rec.get("source"):
        return _canonical(publisher, companies)
    if rec.get("section") == "companies":
        return rec.get("source", "")
    if publisher and _canonical(publisher, companies) in companies:
        return _canonical(publisher, companies)
    return ""


def merge_events(records: list[dict]) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    out: list[dict] = []
    for rec in records:
        if rec.get("event"):
            if rec["event"] not in groups:
                groups[rec["event"]] = []
                out.append({"__event__": rec["event"]})
            groups[rec["event"]].append(rec)
        else:
            out.append(rec)
    result = []
    for rec in out:
        if "__event__" not in rec:
            result.append(rec)
            continue
        members = sorted(groups[rec["__event__"]], key=lambda r: (r.get("tier", "T9"), r.get("published", "")))
        primary = dict(members[0])
        primary["also"] = [{"title": m["title"], "url": m["url"], "source": m.get("source", ""), "tier": m.get("tier", "")} for m in members[1:]]
        for m in members[1:]:
            for k in ("category", "company", "direction_hit"):
                if not primary.get(k) and m.get(k):
                    primary[k] = m[k]
        if any(m.get("meets_min") is True for m in members):
            primary["meets_min"] = True
        result.append(primary)
    return result


def source_score(rec: dict) -> int:
    tier = TIER_SCORE.get(rec.get("tier", ""), 0)
    if rec.get("meets_min") is True:
        return 3
    if rec.get("meets_min") is False:
        return min(tier, 2)
    return tier


def fresh_score(rec: dict, today) -> int:
    dt = cf.parse_date(rec.get("published"))
    if dt is None:
        return 0
    days = (today - dt.astimezone(cf.CST).date()).days
    if days <= 2:
        return 2
    if days <= 7:
        return 1
    return 0


def score(rec: dict, today, companies: set[str]) -> dict:
    company = company_of(rec, companies)
    rel = (2 if rec.get("direction_hit") else 0) + (1 if company and company in companies else 0)
    parts = {"来源": source_score(rec), "相关": rel, "新鲜": fresh_score(rec, today)}
    return {**rec, "company": company, "score_parts": parts, "score": sum(parts.values())}


def _signals(rec: dict) -> list[str]:
    sig = rec.get("signal") or []
    return [sig] if isinstance(sig, str) else list(sig)


def _order_key(rec: dict):
    dt = cf.parse_date(rec.get("published"))
    ts = dt.timestamp() if dt else float("-inf")
    return (-rec["score"], -ts, rec.get("tier", "T9"), rec.get("title", ""))


def merge_papers(records: list[dict]) -> list[dict]:
    """arXiv 条目与 HF 每日论文按 arxiv_id 合并，主链接用 arXiv，带上点赞数。"""
    by_id: dict[str, dict] = {}
    out = []
    for rec in records:
        aid = rec.get("arxiv_id")
        if rec.get("kind") != "paper" or not aid:
            out.append(rec)
            continue
        if aid not in by_id:
            by_id[aid] = rec
            out.append(rec)
            continue
        keep = by_id[aid]
        other = rec
        if "huggingface.co/papers" in keep["url"] and "arxiv.org" in other["url"]:
            keep, other = other, keep
            out[out.index(by_id[aid])] = keep
            by_id[aid] = keep
        keep["upvotes"] = max(int(keep.get("upvotes") or 0), int(other.get("upvotes") or 0))
        keep["signal"] = _signals(keep) + [s for s in _signals(other) if s not in _signals(keep)]
    return out


def rank(records: list[dict], today, companies: set[str], top: int = 15, company_cap: int = 3,
         paper_max: int = 5, min_upvotes: int = 10, signal_max: int = 10,
         floor: tuple[str, ...] = DEFAULT_FLOOR) -> dict:
    records = merge_papers(merge_events(records))
    scored = [score(r, today, companies) for r in records]
    main, papers_pool, signals_pool = [], [], []
    for rec in scored:
        if rec.get("kind") == "paper":
            papers_pool.append(rec)
        elif rec.get("kind") in SIGNAL_KINDS and rec.get("meets_min") is not True:
            signals_pool.append(rec)
        else:
            main.append(rec)

    # 主榜：分数 → 发布时间 → 级别；同一公司最多 company_cap 条
    main.sort(key=_order_key)
    selected, truncated, per_company = [], [], {}
    for rec in main:
        key = rec.get("company") or rec.get("publisher") or rec.get("source", "")
        if len(selected) >= top:
            truncated.append({**rec, "cut_reason": "名次在前 N 之后"})
        elif company_cap and per_company.get(key, 0) >= company_cap:
            truncated.append({**rec, "cut_reason": f"同一公司已有 {company_cap} 条"})
        else:
            selected.append(rec)
            per_company[key] = per_company.get(key, 0) + 1

    # 分类保底：融资并购、政策监管各保 1 个名额，条件是有达到核验最低要求的条目
    protected: set[str] = set()
    for cat in floor:
        if any(r.get("category") == cat for r in selected):
            protected.update(r["url"] for r in selected if r.get("category") == cat)
            continue
        cand = next((r for r in truncated if r.get("category") == cat and r.get("meets_min") is True), None)
        if cand is None:
            continue
        victims = [r for r in selected if r["url"] not in protected and r.get("category") not in floor]
        if len(selected) < top:
            victim = None
        elif victims:
            victim = victims[-1]
        else:
            continue
        truncated.remove(cand)
        cand = {k: v for k, v in cand.items() if k != "cut_reason"}
        cand["floor"] = cat
        selected.append(cand)
        protected.add(cand["url"])
        if victim is not None:
            selected.remove(victim)
            truncated.insert(0, {**victim, "cut_reason": f"让位给「{cat}」保底条目"})
    selected.sort(key=_order_key)
    truncated.sort(key=_order_key)

    # 论文：只有带筛选信号的进「论文速递」
    picked_papers, pool_left = [], []
    for rec in papers_pool:
        sigs = _signals(rec)
        if int(rec.get("upvotes") or 0) >= min_upvotes:
            sigs = sigs + [f"HF 每日论文 {rec['upvotes']} 赞"]
        if rec.get("direction_hit"):
            sigs = sigs + ["命中用户方向"]
        if sigs:
            picked_papers.append({**rec, "signals": sigs})
        else:
            pool_left.append(rec)
    picked_papers.sort(key=lambda r: (-len(r["signals"]), -int(r.get("upvotes") or 0)) + _order_key(r))
    signals_pool.sort(key=_order_key)
    return {
        "main": selected,
        "truncated": truncated,
        "papers": picked_papers[:paper_max],
        "papers_overflow": picked_papers[paper_max:],
        "papers_pool_count": len(pool_left),
        "signals": signals_pool[:signal_max],
        "signals_count": len(signals_pool),
    }


def _fmt_parts(rec: dict) -> str:
    p = rec["score_parts"]
    return f"{p['来源']} | {p['相关']} | {p['新鲜']} | {rec['score']}"


def to_markdown(result: dict, today, top: int) -> str:
    lines = ["## 排序记录", "",
             f"规则见 references/collect.md 第 5 步。今天按 {today.isoformat()}（UTC+8）计；只有日期的条目按当日 00:00 计。", "",
             f"### 主榜（前 {top}）", "", "| 名次 | 条目 | 公司 / 来源 | 分类 | 来源分 | 相关 | 新鲜 | 总分 | 备注 |", "|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(result["main"], 1):
        note = f"保底：{r['floor']}" if r.get("floor") else ""
        lines.append(f"| {i} | {r['title']} | {r.get('company') or r.get('source', '')} | {r.get('category', '')} | {_fmt_parts(r)} | {note} |")
    lines += ["", "### 截断条目", "", "| 条目 | 公司 / 来源 | 来源分 | 相关 | 新鲜 | 总分 | 原因 |", "|---|---|---|---|---|---|---|"]
    for r in result["truncated"]:
        lines.append(f"| {r['title']} | {r.get('company') or r.get('source', '')} | {_fmt_parts(r)} | {r['cut_reason']} |")
    lines += ["", "### 论文速递（有筛选信号）", ""]
    if result["papers"]:
        for r in result["papers"]:
            lines.append(f"- {r['title']}（{r.get('source', '')}；信号：{'、'.join(r['signals'])}）{r['url']}")
    else:
        lines.append("- 无（候选论文都没有筛选信号）")
    lines.append(f"- 候选池里没有筛选信号、未入选的论文：{result['papers_pool_count']} 篇；有信号但超出名额：{len(result['papers_overflow'])} 篇")
    lines += ["", f"### 发布信号（HF / GitHub，共 {result['signals_count']} 条，列前 {len(result['signals'])} 条；核实为正式发布后可标 meets_min 进主榜）", ""]
    for r in result["signals"]:
        lines.append(f"- {r['title']}（{r.get('company') or r.get('source', '')}，{(r.get('published') or '日期不详')[:10]}）")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("inputs", nargs="+", help="JSONL 文件，按顺序合并")
    ap.add_argument("--sources", default=str(Path(__file__).resolve().parent.parent / "config" / "sources.yaml"))
    ap.add_argument("--now", help="今天的日期或时间（UTC+8），默认当前时间")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--company-cap", type=int, default=3, help="主榜同一公司最多几条，0 = 不限")
    ap.add_argument("--paper-max", type=int, default=5)
    ap.add_argument("--min-upvotes", type=int, default=10, help="HF 每日论文点赞数达到多少算筛选信号")
    ap.add_argument("--floor", default=",".join(DEFAULT_FLOOR), help="保底分类，逗号分隔；空字符串 = 不保底")
    ap.add_argument("--format", choices=("jsonl", "md"), default="jsonl")
    args = ap.parse_args(argv)

    today = (cf.parse_since(args.now) if args.now else datetime.now(cf.CST)).astimezone(cf.CST).date()
    companies = company_names(sources_config.load(args.sources))
    floor = tuple(c.strip() for c in args.floor.split(",") if c.strip())
    result = rank(load_jsonl(args.inputs), today, companies, args.top, args.company_cap,
                  args.paper_max, args.min_upvotes, floor=floor)
    if args.format == "md":
        sys.stdout.write(to_markdown(result, today, args.top))
    else:
        for bucket in ("main", "truncated", "papers", "signals"):
            for i, rec in enumerate(result[bucket], 1):
                print(json.dumps({"bucket": bucket, "rank": i, **rec}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
