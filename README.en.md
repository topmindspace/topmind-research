# topmind-research

An AI-industry intelligence and research skill (one skill, two modes). [中文](README.md)

| Mode | Purpose |
|---|---|
| collect | Sweep official announcements, technical reports, paper feeds and tool sources from US and Chinese AI companies listed in `config/sources.yaml`; deduplicate and group them into weekly or flash-brief material |
| analyze | Answer one clearly scoped question by close-reading papers and technical reports or running a side-by-side comparison; deliver a report with confidence levels, sentence-level citations, and a verified fact sheet |

Outputs are written in Chinese by default.

## Install

The skill directory is `topmind-research/`. Copy the whole directory into your host's skills folder; it is self-contained.

```bash
# Claude Code
cp -r topmind-research ~/.claude/skills/
# Codex
cp -r topmind-research ~/.codex/skills/
```

## Layout

```
topmind-research/
├── SKILL.md                 # mode routing, shared rules, conditional file index
├── references/              # collect / analyze workflows, verification gate, follow-up rules, resume, optional backend
├── assets/templates/        # weekly brief, research report, fact sheet, research brief, state file
├── config/                  # sources.yaml (sources), categories.yaml (categories)
└── scripts/                 # optional: source fetcher, ranking, citation checker (Python standard library only)
evals/                       # trigger and output test cases with a scoring rubric
scripts/                     # repository CI checks
tests/                       # unit tests
```

## Design

- **Configurable sources**: edit YAML under `topmind-research/config/`. Each source carries `status` (ok / page-only / blocked / tbd), `fetch` (http / browser / js / api / x), `verified_at`, and optional machine-readable channels (`rss`, `rss_extra`, `hf_api`, `gh_api`, `papers_api`, `list_api`).
- **Verification gate**: `references/verification.md` sets the bar per fact type (T0–T3 source tiers, vendor-claim labels), requires `[n]` citations on every factual sentence, and a citation-support check before delivery.
- **Effort scaling**: analyze starts with a research brief, picks an effort tier (single fact / comparison / survey), caps parallel sub-agents at 6, runs at most two gap-filling rounds, and writes once after research is complete.
- **No silent side effects**: the skill never writes memory, edits `sources.yaml`, or starts a deep dive on its own; it lists suggestions and waits for the user.
- **Neighbouring skills**: community buzz goes to last30days, daily digests to TopStream每日精选, organising stored notes to topmind-organize, publishing is suggested in the receipt: short drafts to topmind-briefs, WeChat articles to topmind-wechat, everything else to topmind-write.
- **Optional backend**: `references/backend-gemini.md` describes running Gemini Deep Research when the user explicitly asks for it.

## Versioning and checks

- The root `package.json`, `topmind-research/package.json`, `metadata.version` in `SKILL.md`, `VERSION` in `scripts/collect_feeds.py` and the CHANGELOG must match; `scripts/check_versions.py` enforces this. Versions bump from the lowest digit.
- Run every check locally: `bash scripts/ci_checks.sh` (the official validator runs only if `pip install skills-ref` is available).
- Source reachability: `python3 scripts/check_sources.py` (also runs weekly in CI, report-only).
