# collect · 情报聚合

客观收集、去重、聚合、排序。可以写「值得关注」，不写「建议采用 / 建议买入」这类判断。

## 范围与分工

| 来源类型 | 谁负责 |
|---|---|
| 中美 AI 公司官方公告、技术报告、system card（`companies`） | collect |
| 论文源（`paper_sources`，只作候选池）、榜单（`benchmarks`）、媒体（`media`）、newsletter | collect |
| 新工具 / 新项目（`tool_sources`：GitHub Trending、Hugging Face 热门模型、Product Hunt） | collect |
| 社区讨论与口碑（X、Reddit、Hacker News、GitHub 讨论、YouTube） | last30days（见第 3 步） |
| 每日聚合站精选（AIHOT、X榜单、今日热榜） | TopStream每日精选，collect 不做日更 |

默认周期是一周。用户要求按天扫时，先提示每日精选已有例行，用户坚持再做。

## 工作流

时间一律按 UTC+8：窗口起止、「距今」、watermark 都用 UTC+8 写；只有日期没有时刻的条目按当日 00:00（UTC+8）计。

### 1. 定范围

- 读 `references/state.md` 指定位置的 collect watermark；有则只收 watermark 之后的内容，没有则收最近 7 天。用户说「全量重扫」时忽略 watermark。
- 用户给了方向（公司、分类、主题）就只扫相关信源；没给就扫 `config/sources.yaml` 的全部信源，按 `status` 处理：

| status | 怎么用 |
|---|---|
| ok | 正常扫 |
| page-only（可打开但不可机读） | 有浏览器就用浏览器看；没有就在「信源状态」写「没抓到（前端渲染）」 |
| blocked | 有浏览器就试；没有就用它的补充渠道（`rss_extra`、`x_account`），写明只覆盖了哪部分 |
| tbd | 可以看，但从它拿到的条目一律按 T2 以下处理，并在「信源状态」里列出 |

### 2. 抓取

- **可机读渠道先跑脚本**：`python3 scripts/collect_feeds.py --sources config/sources.yaml --since <watermark> --report feeds-status.md > feeds.jsonl`。它读 `rss`、`rss_extra`、`hf_api`、`gh_api`、`papers_api`，按发布时间（published 优先，updated 只作兜底）过滤、去重，输出 JSONL（title / url / source / published / tier / section / kind / channel / publisher），时间统一为 UTC+8。只用 Python 标准库。
- **覆盖警告照抄**：脚本对「最早一条仍晚于窗口起点」（RSS 只给最近几条）和「条目超过 `--max-per-feed` 被截断」写警告，`--report` 文件就是「信源状态」的底稿。有「未覆盖完整窗口」警告的信源，窗口前段要用列表页补查，补不了就在周报写明缺哪几天。
- **证书**：抓取报 SSL 证书错误时，多半是本机 CA 库缺新根证书。按该信源 `ca_root` 字段下载根证书，用 `--ca-bundle <文件>`（或环境变量 `TOPMIND_CA_BUNDLE`）追加后重试。不得跳过证书校验（不用 `curl -k`、不关校验开关）。
- **没有可机读渠道的信源**按 `fetch` 读页面：`http` 用宿主的网页抓取工具；`browser`（普通请求被拒）、`js`（列表靠前端渲染）宿主有浏览器就用浏览器，没有就在「信源状态」写「本次未抓到」，不要凭记忆补内容；`api` 按 `note` 调 `list_api`；`x` 用 `x_account` 的官方帖子确认发布。
- **官方 RSS 摘要**：正文页打不开（如 403）时，官方 RSS 的标题和摘要可作为「发布事实」（发布了什么、哪天发布）的 T0；数字、价格、基准、规格不得只凭摘要写入，要读到正文或其他 T0，读不到就写「未核实」。
- **发布方**：Hugging Face 博客里其他组织发的文章（`/blog/<组织>/...`）按该组织记发布方，脚本输出的 `publisher` 字段已处理。
- **并行**：宿主支持子 agent（如 Claude Code 的 Task、Codex 的 subagent）时，按信源分组并行，同时最多 6 个；不支持就串行。子 agent 只回传条目列表（标题 / 链接 / 发布时间 / 信源 / 级别 / 50 字内摘要），不回传网页全文，也不得再派子 agent。
- **预算**：一次周度 collect 参考 40–60 次工具调用（含脚本、页面读取和核验）。超过 80 次就收尾；单个信源连续 2 次超时或被拒就停下该信源，记进「信源状态」，不再重试。
- **信源状态要分清三种情况**：抓到了但窗口内 0 条；没抓到（失败、需浏览器、前端渲染）；抓到了但覆盖不全（覆盖警告）。只有第一种能说明「本周没有发布」。

### 3. 社区反应（可选）

本周有重大发布（新模型、新论文、重大融资并购）时，对其中最多 3 个补社区反应。先判断 last30days 是否可用：

| 状态 | 判断方法 | 怎么做 |
|---|---|---|
| 已安装且已配置 | `~/.agents/skills/last30days/SKILL.md` 存在（或宿主技能列表里有 last30days），且 `~/.config/last30days/.env` 里有 `SETUP_COMPLETE=true` | 调用 last30days（话题 = 发布名称），把它输出的 KEY PATTERNS 压缩成 2–3 句，标注「据 last30days 汇总，社区讨论，非事实核验」 |
| 已安装但未完成首次配置 | 技能在，配置文件不在或没有 `SETUP_COMPLETE=true` | 不替用户做配置选择（如 X 接入方式）；本节按下面的降级做法写；回执里提示用户运行一次 last30days 完成首次配置 |
| 未安装 | 以上路径都没有 | 按降级做法写；回执里提示可选安装 last30days |

降级做法：用宿主的网页搜索在 Hacker News、Reddit 找该发布的讨论帖，每个发布最多 2 帖，只列标题、链接、发帖日期，整节标「T3 社区线索，非 last30days 汇总」，不写「社区普遍认为」这类概括判断。搜不到写「未找到公开讨论」。宿主没有网页搜索时才跳过这一节，并在回执说明。

`config/sources.yaml` 的 `people` 列表只在 last30days 已配置 X 时有用；`x_handle` 为 TBD 或 null 的人物，用 `note` 里写的公司官方号代替。

### 4. 去重聚合

- URL 规范化后去重：小写域名，去掉 `utm_*` 等跟踪参数、`#` 锚点和末尾斜杠。
- 同一事件多源报道合并为一条，主链接用 T0，其他来源列在条目下。
- 同一事件已在上期周报出现且没有新进展的，不再收录。
- 排序前先剔除不收录的条目：客户案例、活动与会议推广、招聘与奖学金、游戏促销等与 AI 进展无关的公告，以及早于窗口的条目。用 `rank_items.py` 时在补充行里写 `"drop": true`。脚本只按规则打分，这一步的取舍由 agent 判断。

### 5. 排序

先分桶，再打分，最后套公司上限和分类保底。`scripts/rank_items.py` 实现了本节规则（输入 collect_feeds 的 JSONL，加上 agent 补充的条目和 `category`、`meets_min` 等字段，`--format md` 直接输出「排序记录」）；两者不一致时以本节为准。

**分桶**

| 桶 | 条目 | 进周报的条件 |
|---|---|---|
| 主榜 | 公司公告、技术报告、媒体报道、融资、政策、人事等 | 按分数取前 15 |
| 论文速递 | `paper_sources` 的论文（arXiv RSS、HF 每日论文） | 只作候选池。要有筛选信号才入选：HF 每日论文点赞 ≥ 10、公司官方博客或技术报告提及、命中用户方向；最多 5 篇。没有信号的不进周报，只在「信源状态」写候选池篇数 |
| 发布信号 | `hf_api`、`gh_api` 抓到的新模型、新仓库、release | 作线索列在「开源项目」或「信源状态」；核实是正式发布（有官方公告或模型卡说明）后按主榜条目打分 |

公司在自己博客或 HF 博客发的研究文章（如竞赛成绩、技术报告）属于主榜，不进论文桶。

**打分**

| 项 | 规则 | 分 |
|---|---|---|
| 来源 | 达到 `references/verification.md` 第二节对该事实类型的最低要求 3 · 有 T0/T1 但没达到 2 · 只有 T2 1 · 只有 T3 0 | 0–3 |
| 相关 | 命中用户指定方向 +2；公司在 `companies` 列表内 +1 | 0–3 |
| 新鲜 | 按 UTC+8 日历日算距今：≤2 天 2 · ≤7 天 1 · 更早或没有日期 0 | 0–2 |

例：公司自己的发布有 1 个官方原文即达标，记 3 分；融资额有 2 个独立来源且至少 1 个 T0 或 T1 即达标，记 3 分；只有一家媒体报道的融资记 1 分。

**取前 15**

1. 主榜按总分降序；同分按发布时间新者在前，再同按级别高者在前。
2. 同一公司在主榜最多 3 条，多出的进「截断条目」。
3. 分类保底：「融资并购」「政策监管」各保 1 个名额。前 15 里没有该分类、截断条目里有达到核验最低要求的，用它替换主榜最后一名，被替换的写进「截断条目」。
4. 截断条目中有 T0/T1 支撑的，在周报「排序记录」里列出，供人工判断。

### 6. 核验

过 `references/verification.md`。周报里每条至少有 1 个可打开的链接；数字类条目达到第二节的要求，达不到的写「未核实」且不进推荐语。

### 7. 输出

按 `assets/templates/collect-weekly.md` 写，「信源状态」以 `--report` 文件为底稿，补上页面读取的结果。需要出快讯时，挑出的条目按 `assets/templates/fact-sheet.md` 整理，在回执里建议交给出稿技能（见 `references/upgrade-rules.md`「出稿」），不自动调用。

### 8. 收尾

1. 更新 collect watermark（本次收录条目中最新的发布时间，用发布时间而不是更新时间），写到 `references/state.md` 指定的位置。
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
