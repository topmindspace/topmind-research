# collect · 情报聚合

客观收集、去重、聚合、排序。可以写「值得关注」，不写「建议采用 / 建议买入」这类判断。

## 范围与分工

| 来源类型 | 谁负责 |
|---|---|
| 中美 AI 公司官方公告、技术报告、system card（`companies`） | collect |
| 论文源（`paper_sources`）、榜单（`benchmarks`）、媒体（`media`）、newsletter | collect |
| 新工具 / 新项目（`tool_sources`：GitHub Trending、Hugging Face 热门模型、Product Hunt） | collect |
| 社区讨论与口碑（X、Reddit、Hacker News、GitHub 讨论、YouTube） | last30days（见第 3 步） |
| 每日聚合站精选（AIHOT、X榜单、今日热榜） | TopStream每日精选，collect 不做日更 |

默认周期是一周。用户要求按天扫时，先提示每日精选已有例行，用户坚持再做。

## 工作流

### 1. 定范围

- 读 `references/state.md` 指定位置的 collect watermark；有则只收 watermark 之后的内容，没有则收最近 7 天。用户说「全量重扫」时忽略 watermark。
- 用户给了方向（公司、分类、主题）就只扫相关信源；没给就扫 `config/sources.yaml` 中 `status: ok` 的全部信源。`status: tbd` 的信源可以看，但从它拿到的条目一律按 T2 以下处理，并在周报「信源状态」里列出。

### 2. 抓取

- 有 `rss` 字段的信源：优先读 RSS。可以跑 `python3 scripts/collect_feeds.py --sources config/sources.yaml --since <watermark>`，它输出去重后的 JSONL（字段：title / url / source / published / tier），只用 Python 标准库。
- `fetch: browser` 的信源（普通 HTTP 请求会被拒）：宿主有浏览器就用浏览器打开；没有就在「信源状态」里写「本次未抓到」，不要凭记忆补内容。
- 其余信源用宿主的网页抓取工具读列表页。
- 并行：宿主支持子 agent（如 Claude Code 的 Task、Codex 的 subagent）时，按信源分组并行，同时最多 6 个；不支持就串行。子 agent 只回传条目列表（标题 / 链接 / 发布时间 / 信源 / 级别 / 50 字内摘要），不回传网页全文，也不得再派子 agent。

### 3. 社区反应（可选）

本周有重大发布（新模型、新论文、重大融资并购）时，对其中最多 3 个调用 last30days（话题 = 发布名称），把它输出的 KEY PATTERNS 压缩成 2–3 句，放进周报「社区反应」一节，标注「据 last30days 汇总，社区讨论，非事实核验」。没有安装 last30days 时跳过这一节并在回执里说明。`config/sources.yaml` 的 `people` 列表可作为 last30days 的 X 账号输入。

### 4. 去重聚合

- URL 规范化后去重：小写域名，去掉 `utm_*` 等跟踪参数、`#` 锚点和末尾斜杠。
- 同一事件多源报道合并为一条，主链接用 T0，其他来源列在条目下。
- 同一事件已在上期周报出现且没有新进展的，不再收录。

### 5. 排序

每条按三项打分，相加后降序，默认取前 15 条：

| 项 | 规则 | 分 |
|---|---|---|
| 来源 | 有 T0 原文 3 · 最高 T1 2 · 最高 T2 1 · 只有 T3 0 | 0–3 |
| 相关 | 命中用户指定方向 +2；公司在 `companies` 列表内 +1 | 0–3 |
| 新鲜 | 距今 ≤2 天 2 · ≤7 天 1 · 更早 0 | 0–2 |

同分时按发布时间新者在前。

### 6. 核验

过 `references/verification.md`。周报里每条至少有 1 个可打开的链接；数字类条目达到第二节的要求，达不到的写「未核实」且不进推荐语。

### 7. 输出

按 `assets/templates/collect-weekly.md` 写。需要出快讯时，挑出的条目按 `assets/templates/fact-sheet.md` 整理后交给 topmind-briefs。

### 8. 收尾

1. 更新 collect watermark（本次收录条目中最新的发布时间），写到 `references/state.md` 指定的位置。
2. 工具 / 项目类条目按下面的「工具储备条目」格式整理，在回执里列出，问用户是否用 topmind-capture 收进工作区。
3. 周报末尾列出「analyze 候选」（最多 3 条，附理由），由用户决定是否深挖，见 `references/upgrade-rules.md`。

## 工具储备条目

```yaml
title: 工具或项目名
url: https://...            # 官方仓库或官网
source_type: external-capture
captured_at: 2026-10-08T09:00:00+08:00
category: 工具应用           # 取自 config/categories.yaml 的 collect_categories
summary: 50 字内，说清做什么、给谁用
evidence: GitHub 星数 / 发布说明链接 / 榜单位置（写明查询日期）
status: candidate            # candidate → 用户确认后由 topmind-capture 落盘
```
