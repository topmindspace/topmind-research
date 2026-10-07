---
name: topmind-research-collect
version: 0.2.0
description: >-
  应用调研与情报聚合：客观收集工具/应用/智能体/技能与新闻热点、大厂动态，
  去重聚合整理，按分类推荐。不做深度分析，需要深挖时按升级规则转 analyze。
  Use when 找工具、扫新闻、追踪大厂动态、每周情报 sweep、聚合推荐。
  Do NOT use for 论文精读与深度分析（→ topmind-research-analyze）。
action_category: research
triggers:
  - 找工具
  - 有什么新工具
  - 新闻热点
  - 大厂动态
  - 每周扫
  - 聚合推荐
triggers_cn:
  - 汇总一下
  - 最近有什么新的
  - 推荐几个
author: TopMindSpace
license: MIT
homepage: https://github.com/topmindspace/topmind-research#readme
updated: 2026-10-07
---

# topmind-research-collect · 应用调研与情报聚合

只做客观收集、聚合、推荐，不做深度分析、不下判断结论（"值得关注"可以，"建议买入"不行）。

## 信息源（可配置）

读仓库根 `config/sources.yaml`：
- `tool_sources`：GitHub Trending、AI 资讯站、Product Hunt 等
- `companies`：24 家 AI 公司/大厂的官网 blog 与新闻页
- `people`：关键人物（CEO/首席科学家）的公开动态
- `media`：第三方科技媒体

`config/categories.yaml` 定义聚合分类（新品发布/融资并购/开源项目/工具应用/人物动态/政策监管/行业数据/论文速递）。

## 工作流

1. **定范围**：用户给方向，或默认全量扫。一次只扫一个周期（周/日）。
   输入方式与增量机制见 `references/input-guide.md`（默认增量 sweep，带 watermark 去重）。
2. **并行扫**：按来源分组并行抓取（可借鉴 `wide_research` 的 manager+workers 模式），每条记录统一字段：标题/来源/时间/链接/一句话摘要。
3. **去重聚合**：同一事件多源合并，保留一手来源链接。
4. **评分排序**：按热度×相关性×新鲜度排序，取 Top N。
5. **核实门**：过 `references/verification.md`（关键事实双源交叉）。
6. **输出**：聚合周报 / X 短篇推荐 / 可直接喂给 briefs 的素材。
7. **沉淀**：入库储备（沿用 topmind-tool-scout 的储备库格式），命中升级线（见 `references/upgrade-rules.md`）的条目标记 `→analyze`。

## 输出要求

- 每条必带：来源链接、时间戳。
- 一手来源优先展示；转述注明"据XX报道"。
- 不确定的标"未核实"，不写进推荐语。
