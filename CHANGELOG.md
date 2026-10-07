# Changelog

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
