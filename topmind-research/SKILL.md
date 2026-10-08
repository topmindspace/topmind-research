---
name: topmind-research
description: >-
  AI 行业情报与研究（topmind）。collect 模式按 config/sources.yaml 扫中美 AI 公司官方公告、
  技术报告与论文源，去重聚合成周报或快讯素材；analyze 模式围绕一个明确问题精读论文、
  技术报告或做横向对比，产出带置信度与逐句来源的研究报告。Use when 追踪大厂动态、
  AI 周报 sweep、读论文、解读技术报告或 system card、对比模型或工具、核实融资额 / 估值 /
  数字口径、topmind-research。
  Do NOT use for 社区口碑与近 30 天讨论（→ last30days）、每日精选例行（→ TopStream每日精选）、
  整理已存笔记或专题内总结（→ topmind-organize）、出稿发文（短稿或快讯 → topmind-briefs，
  公众号排版与定稿 → topmind-wechat，其他长文 → topmind-write；未安装 → topmind-write）。
license: MIT
compatibility: >-
  Needs web search and web fetch. Sub-agents and a browser are optional (falls back to
  sequential work and marks pages it cannot load). Python 3.9+ only for the optional
  scripts. Writes reports into a topmind workspace when one is present.
metadata:
  version: "0.2.0"
  author: TopMindSpace
  homepage: https://github.com/topmindspace/topmind-research#readme
  updated: "2026-10-08"
  action_category: research
  triggers: 大厂动态, AI 周报, 情报 sweep, 读论文, 论文精读, 技术报告解读, system card, 模型对比, 融资核实, 估值核实, topmind-research
---

# topmind-research · AI 情报与研究

两种模式，同一套核验口径和产出模板。所有路径相对本技能目录。

| 模式 | 做什么 | 不做什么 |
|---|---|---|
| collect | 按信源清单扫官方公告、技术报告、论文与工具源，去重聚合，出周报或快讯素材 | 不下结论，不做深度分析 |
| analyze | 围绕一个明确问题精读一手资料、横向对比，出研究报告和已核验事实表 | 不做泛泛汇总 |

## 先读哪份

| 条件 | 必读 |
|---|---|
| 扫动态、周报、大厂动态、找新工具 | `references/collect.md` + `config/sources.yaml` |
| 读论文、解读技术报告、对比、深挖一个问题 | `references/analyze.md` |
| 交付前（两种模式都要） | `references/verification.md` |
| 用户给的输入形式不清楚 | `references/input-guide.md` |
| collect 条目要不要转 analyze、产出放哪 | `references/upgrade-rules.md` |
| 中断后继续 | `references/state.md` |
| 用户要求调用 Gemini Deep Research | `references/backend-gemini.md` |
| 碰到人名、产品名译法 | `references/errata.md` |

模板在 `assets/templates/`：`collect-weekly.md`、`analyze-report.md`、`fact-sheet.md`、`research-brief.md`、`state.md`。

## 模式判断

1. 「这周有什么新的 / 汇总一下大厂动态 / 推荐几个新工具」→ collect。
2. 「这篇论文说了什么 / 解读这份技术报告 / A 和 B 对比」→ analyze。
3. 两者都有（「扫一遍，值得的再细读」）→ 先 collect，在周报末尾列出 analyze 候选，用户点名后再进 analyze。用户授权深挖但没点名时，也是列候选、问用户选哪条，不由 agent 代选。
4. 核实融资额、估值、用户数等第三方数字（「各家报道不一样，到底是多少」）→ analyze 单点档位，按 `references/verification.md` 第二节要 2 个独立来源。
5. 对象是工作区里已存的笔记 → 交给 topmind-organize，本技能不处理。
6. 要的是社区口碑、X/Reddit/HN 讨论 → 交给 last30days；collect 周报需要「社区反应」一节时，按 `references/collect.md` 调用它。

## 共同铁律

- 交付前必须过 `references/verification.md`，未通过不交付。
- 每个事实句带 `[n]` 引用，文末来源表写明级别（T0–T3）、发布日期、访问日期。
- 不自动写记忆、不自动改 `config/sources.yaml`、不自动升级深挖、不自动调用出稿技能：都只在回执里列为建议，用户确认后再做。
- 出稿交接：短稿或快讯 → topmind-briefs（附已核验事实表），公众号排版与定稿 → topmind-wechat，其他长文 → topmind-write；对应技能未安装 → topmind-write。
- 子 agent 并行上限 6 个，子 agent 不得再派子 agent（细则见 `references/analyze.md`）。
- 推测与事实分开写，推测段落标「（推测）」。
- 只用公开信息；不收录私人联系方式；配置文件里不放任何密钥。
