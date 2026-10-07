---
name: topmind-research
version: 0.2.0
description: >-
  研究入口路由：把"找资料/看动态"分给 topmind-research-collect（客观收集、聚合整理、推荐），
  把"深挖/读论文/做分析"分给 topmind-research-analyze（深度研究、数据整理分析）。
  Use when 做研究、查资料、追踪大厂动态、读论文、行业调研、research。
  Do NOT use for 纯写作出稿（→ topmind-write / topmind-briefs）、X 运营段子（→ topmind-viral-posts）。
action_category: research
triggers:
  - 做研究
  - 查资料
  - 追踪动态
  - 读论文
  - 行业调研
  - 大厂动态
triggers_cn:
  - 研究一下
  - 帮我查查
  - 最新进展
  - 论文解读
author: TopMindSpace
license: MIT
homepage: https://github.com/topmindspace/topmind-research#readme
updated: 2026-10-07
---

# topmind-research · 研究入口路由

本技能不直接干活，只做路由。两个子技能分工如下：

| 子技能 | 定位 | 何时用 |
|---|---|---|
| `topmind-research-collect` | 客观收集、聚合整理、推荐 | 找工具/应用、扫新闻热点、追踪大厂动态、每周 sweep |
| `topmind-research-analyze` | 深度研究、论文精读、数据整理分析 | 读论文、解读技术报告、横向对比、深挖一个题目 |

## 路由规则

1. 用户要"看看有什么新的/汇总一下/推荐几个" → collect。
2. 用户要"深入讲讲/这篇论文说了什么/对比一下/分析数据" → analyze。
3. 一句话里两者都有（"扫一遍，有值得深挖的再细读"）→ 先 collect，命中升级线后转 analyze。
4. 纯写作出稿（写文章、发快讯）不归本路由，写完研究报告后如需出稿，转 `topmind-write` / `topmind-briefs`。

## A→B 升级规则

详见 `references/upgrade-rules.md`。核心三条：
- 用户明确指定深挖；
- collect 评分达到升级线（见 collect 的 rubric）；
- 重大发布/突发（新模型、新论文、新融资并购）默认升级。

## B→A 回流

analyze 的结论沉淀为知识：进用户记忆/专题，下次 collect 扫到相关动态时自动关联上下文。

## 配置

信息源、内容源、分类全部可配置，改 YAML 不用改技能：
- `config/sources.yaml`：公司、关键人物、媒体、论文源、工具源
- `config/categories.yaml`：collect 的聚合分类、analyze 的研究类型

改完在 README 记录变更日期。

## 核实铁律（两个子技能强制执行）

`references/verification.md` 是发布前的强制门：来源分级、一手优先、关键事实双源交叉、厂商口径标注、无法核实则删或明确标注。任何输出未经核实门不得交付。
