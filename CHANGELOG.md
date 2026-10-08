# Changelog

## Unreleased

### 结构优化（不兼容变更）

- 三个技能合并为单技能 `topmind-research`，collect / analyze 改为技能内的两种模式；`topmind-research-collect`、`topmind-research-analyze` 不再单独安装，旧安装需删除后重新复制 `topmind-research/` 目录
- `config/`、`references/` 移入技能目录，技能目录自包含，路径一律相对技能根目录
- 根 `package.json`、技能 `package.json` 版本与 `SKILL.md` 对齐为 0.2.0，补充 repository 字段
- 去掉对外部技能 topmind-tool-scout 和宿主未必提供的 wide_research 工具的引用，工具储备条目格式写入 `references/collect.md`

### 核验门优化

- `references/verification.md` 按事实类型定核验强度：公司发布 1 个 T0 并标厂商口径，第三方数字 2 个独立来源，论文以原文为准，传闻不进结论
- 逐句 `[n]` 引用与统一来源表格式，交付前做引用支撑检查并写核验记录
- 译名教训移到 `references/errata.md`

### 工作流优化

- analyze 增加研究简报与计划确认、投入档位（单点 / 对比 / 综述）、子 agent 并行上限 6 且不递归、最多 2 轮补洞、研究完成后单次写作
- collect 明确与 last30days、TopStream每日精选的分工，排序规则可判定，URL 规范化去重
- 不再自动写记忆、自动改 `sources.yaml`、自动升级深挖，统一改为回执建议 + 用户确认
- 新增断点续跑状态文件（`references/state.md`）与五个输出模板（`assets/templates/`），沉淀 frontmatter 与 topmind-organize 约定对齐

### 信源优化

- `sources.yaml` 逐条核验（2026-10-08），新增 `rss`、`fetch`、`verified_at`、`note` 字段；列表页改为各家新闻页
- 新智元地址更正为 aiera.com.cn；字节改为 Seed 官网；小米改为 MiMo 官网；LMArena 补地址
- 无法确认的信源标 `status: tbd` 并写明原因：Meta、Perplexity、百度、华为、商汤、晚点 LatePost
- Hacker News 交给 last30days；Papers with Code 跳转到 HF Papers，移出
- 人物 X 账号补全 7 个（经 X 接口核对），其余 8 人保留 TBD

### 特性支持

- 可选脚本：`scripts/collect_feeds.py`（RSS 抓取、去重、JSONL 输出）、`scripts/check_citations.py`（引用检查）
- 仓库检查与 CI：版本一致、技能内引用完整、信源字段、隐私扫描、单元测试、`agentskills validate`；每周信源可达性巡检
- 可选 Gemini Deep Research 后端说明（`references/backend-gemini.md`），仅在用户明确要求时使用
- 评测集 `evals/queries.yaml`（20 条）与打分表 `evals/rubric.md`
- 英文 README

## 0.2.0 — 2026-10-07

- 信息源扩充：核实 xAI（x.ai/news）、MiniMax（minimax.io）；新增 benchmarks（Artificial Analysis、LMArena）、newsletters（TLDR AI、The Batch）、论文源（Papers with Code、Semantic Scholar）、工具源（Product Hunt、Hacker News）、媒体（晚点 LatePost）；关键人物增至 16 位
- 工作流优化：新增 `references/input-guide.md`（输入方式矩阵、增量 sweep watermark 机制、analyze 置信度标注）
- 核实机制新增第五节隐私保护：只收录公开信息源，输出脱敏，配置中禁放密钥
- 状态为 tbd 的来源待后续核实后转正

## 0.1.0 — 2026-10-07

- 首版：`topmind-research` 路由 + `topmind-research-collect` + `topmind-research-analyze`
- 配置化：`config/sources.yaml`（20 余家公司/关键人物/媒体/论文源/工具源）、`config/categories.yaml`
- 核实机制 `references/verification.md`、升级/回流规则 `references/upgrade-rules.md`
- 吸收替代 `topmind-tool-scout`（储备库格式与 2026-W41 成果迁移）
