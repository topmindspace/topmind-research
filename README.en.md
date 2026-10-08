# topmind-research

An AI-industry intelligence and research skill (one skill, two modes). [中文](README.md)

| Mode | Purpose |
|---|---|
| collect | Sweep official announcements, technical reports, paper feeds and tool sources from US and Chinese AI companies listed in `config/sources.yaml`; deduplicate and group them into weekly or flash-brief material |
| analyze | Answer one clearly scoped question by close-reading papers and technical reports or running a side-by-side comparison; deliver a report with confidence levels, sentence-level citations, and a verified fact sheet |

Outputs are written in Chinese by default.

## Install

The skill directory is `topmind-research/` and it is self-contained. The npm package [`@topmindspace/topmind-research`](https://www.npmjs.com/package/@topmindspace/topmind-research) is published from 0.2.3 on (0.2.2 and earlier have no npm package; use options 2–4). Pick one:

**Option 1: npm, then copy into your skills folder**

`npm i` alone only puts the package in `node_modules`, where your agent will not find it. Copy it over:

```bash
npm i @topmindspace/topmind-research
# Claude Code
cp -r node_modules/@topmindspace/topmind-research/topmind-research ~/.claude/skills/
# Codex
cp -r node_modules/@topmindspace/topmind-research/topmind-research ~/.codex/skills/
```

**Option 2: skills CLI ([vercel-labs/skills](https://github.com/vercel-labs/skills), Node.js 22+)**

```bash
# project scope (.claude/skills/ etc., depending on the agent)
npx skills add topmindspace/topmind-research --agent claude-code
# user scope
npx skills add topmindspace/topmind-research --agent claude-code -g
```

The CLI copies only the `topmind-research/` skill directory; the repo-level `evals/`, `tests/` and `scripts/` stay out of your host.

**Option 3: GitHub Release zip**

Download `topmind-research.zip` from [Releases](https://github.com/topmindspace/topmind-research/releases). Its top level is `topmind-research/`, so unzip it straight into your skills folder:

```bash
unzip topmind-research.zip -d ~/.claude/skills/
```

**Option 4: git clone and copy**

```bash
git clone --depth 1 https://github.com/topmindspace/topmind-research.git
# Claude Code
cp -r topmind-research/topmind-research ~/.claude/skills/
# Codex
cp -r topmind-research/topmind-research ~/.codex/skills/
```

To upgrade, delete the old `topmind-research/` in your host first, then copy or unzip; back up `config/sources.yaml` if you edited it.

Do not use the topmind-skills pack installer for this repo: it copies the repo-level `evals/`, `LICENSE` and `README.md` into the skill folder.

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
- **Neighbouring skills**: community buzz goes to last30days, daily digests to TopStream每日精选, organising stored notes to topmind-organize, publishing is suggested in the receipt: short drafts to topmind-briefs, WeChat articles to topmind-wechat-post, everything else to topmind-write.
- **Optional backend**: `references/backend-gemini.md` describes running Gemini Deep Research when the user explicitly asks for it.

## Versioning and checks

- The root `package.json`, `topmind-research/package.json`, `metadata.version` in `SKILL.md`, `VERSION` in `scripts/collect_feeds.py` and the CHANGELOG must match; `scripts/check_versions.py` enforces this. Versions bump from the lowest digit.
- Run every check locally: `bash scripts/ci_checks.sh` (the official validator runs only if `pip install skills-ref` is available).
- Source reachability: `python3 scripts/check_sources.py --strict --report sources-report.md`. The weekly CI run turns red when the field check fails or a `status: ok` source is broken (404/410, DNS failure, connection refused); 403, 429, 5xx, timeouts and certificate-chain problems become warning annotations. The report goes to the run summary and an artifact; nothing is edited and no issue is opened automatically.
