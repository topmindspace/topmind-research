# topmind-research

AI 行业情报与研究技能（单技能，两种模式）。[English](README.en.md)

| 模式 | 定位 |
|---|---|
| collect | 按 `config/sources.yaml` 扫中美 AI 公司官方公告、技术报告、论文与工具源，去重聚合成周报或快讯素材 |
| analyze | 围绕一个明确问题精读论文、技术报告或做横向对比，产出带置信度与逐句来源的研究报告和已核验事实表 |

## 安装

本技能**没有发布到 npm**，`npm i @topmindspace/topmind-research` 会返回 404。技能目录是 `topmind-research/`，目录内自包含，不依赖仓库根的其他文件。两种装法任选：

**方式一：skills CLI（[vercel-labs/skills](https://github.com/vercel-labs/skills)，需要 Node.js 22+）**

```bash
# 装到当前项目（.claude/skills/ 等，按所选宿主）
npx skills add topmindspace/topmind-research --agent claude-code
# 装到用户级目录
npx skills add topmindspace/topmind-research --agent claude-code -g
```

CLI 只会复制 `topmind-research/` 这个技能目录，仓库根的 `evals/`、`tests/`、`scripts/` 不会进宿主。

**方式二：git clone 后复制**

```bash
git clone --depth 1 https://github.com/topmindspace/topmind-research.git
# Claude Code
cp -r topmind-research/topmind-research ~/.claude/skills/
# Codex
cp -r topmind-research/topmind-research ~/.codex/skills/
```

升级时先删掉宿主里旧的 `topmind-research/` 再复制；改过 `config/sources.yaml` 的先备份再合并回去。

不要用 topmind-skills 的 pack 安装器装本仓库：它会把仓库根的 `evals/`、`LICENSE`、`README.md` 一并铺进技能目录。

## 目录

```
topmind-research/
├── SKILL.md                 # 模式判断 + 共同铁律 + 按条件加载的文件索引
├── references/              # collect / analyze 流程、核验、升级与沉淀、断点续跑、可选后端
├── assets/templates/        # 周报、研究报告、事实表、研究简报、状态文件模板
├── config/                  # sources.yaml（信源）、categories.yaml（分类）
└── scripts/                 # 可选：信源抓取、排序、引用检查（仅 Python 标准库）
evals/                       # 发版前跑的小评测集与评分标准
scripts/                     # 仓库 CI 检查
tests/                       # 单元测试
```

## 设计

- **配置化**：信源、分类在 `topmind-research/config/` 里改 YAML，不用改技能。每个信源带 `status`（ok / page-only / blocked / tbd）、`fetch`（http / browser / js / api / x）和 `verified_at`；中国厂商补了 Hugging Face 组织 API、GitHub 组织仓库等可机读发布信号。
- **核验门**：`references/verification.md` 按事实类型定核验强度，逐句 `[n]` 引用，交付前做引用支撑检查。
- **与 topmind 衔接**：报告落盘到专题（topmind-organize 约定），记忆只建议不自动写，出稿时在回执建议交给 topmind-briefs（短稿）、topmind-wechat-post（公众号）或 topmind-write，并附已核验事实表。
- **与邻近技能分工**：社区口碑交给 last30days，每日聚合站精选交给 TopStream每日精选，已存笔记的整理交给 topmind-organize。

## 版本与检查

- 根 `package.json`、`topmind-research/package.json`、`SKILL.md` 的 `metadata.version`、`scripts/collect_feeds.py` 的 `VERSION` 与 CHANGELOG 保持一致，由 `scripts/check_versions.py` 检查。版本号从最小位升起。
- 本地跑全部检查：`bash scripts/ci_checks.sh`（需要 `pip install skills-ref` 才会跑官方校验器，没装会跳过并提示）。
- 信源可达性巡检：`python3 scripts/check_sources.py --strict --report sources-report.md`。CI 每周一跑一次：字段检查不通过、或 `status: ok` 的信源失效（404/410、域名解析失败、连接被拒）时运行标红；403、429、5xx、超时、证书链问题记为警告注释。报告写进运行摘要并保留为 artifact，不自动改配置、不自动开 issue。
