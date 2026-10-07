# topmind-research

AI 情报与深度研究技能组：一个路由 + 两个子技能。

| 技能 | 定位 |
|---|---|
| `topmind-research` | 入口路由：只分流，不干活 |
| `topmind-research-collect` | 应用调研与情报聚合：工具/应用/新闻/大厂动态，客观收集、聚合、推荐 |
| `topmind-research-analyze` | 论文与资料深度研究：精读论文、解读报告、横向对比、数据分析 |

## 设计

- **配置化**：信息源、内容源、分类全部在 `config/` 里改 YAML，不用改技能。
  - `config/sources.yaml`：20 余家 AI 公司/大厂、关键人物、媒体、论文源、工具源
  - `config/categories.yaml`：聚合分类与研究类型
- **核实机制**：`references/verification.md` 是强制门——来源分级、一手优先、关键事实双源交叉、厂商口径标注、无法核实则删或标注。
- **升级/回流**：`references/upgrade-rules.md` 定义 collect→analyze 升级线与 analyze→collect 知识回流。

## 前身

本仓库吸收并替代 `topmind-tool-scout`（工具星探）：其储备库格式与第一期成果（2026-W41）迁移到 collect，`topmind-tool-scout` 本体归档。

## 版本

- root `package.json` 与各技能 `package.json` 的 version 保持一致
- 发版前检查：SKILL.md frontmatter / README / CHANGELOG 版本引用一致
