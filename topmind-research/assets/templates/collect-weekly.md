---
title: AI 情报周报 YYYY-Www
source_type: ai-derived
produced_by: topmind-research/collect
as_of: YYYY-MM-DD
watermark: YYYY-MM-DDTHH:MM:SS+08:00
sources: 0
---

# AI 情报周报 YYYY-Www（YYYY-MM-DD 至 YYYY-MM-DD）

## 本周要点

1. **标题**：50 字内说明发生了什么 [1]
2. …

## 新品发布

- **条目标题**：摘要（厂商口径的表述照标）[n]
  - 其他来源：媒体名 [n]

## 公司动态

## 融资并购

## 开源项目 / 工具应用

## 论文速递

（只收有筛选信号的论文：HF 每日论文点赞 ≥ 10、官方博客或技术报告提及、命中用户方向，最多 5 篇；每条写明信号。）

## 人物动态

## 政策监管

## 行业数据

（分类取自 `config/categories.yaml` 的 `collect_categories`，没有条目的分类删掉。）

## 社区反应（可选，来自 last30days）

- **发布名称**：2–3 句社区讨论要点。据 last30days 汇总，社区讨论，非事实核验。

## analyze 候选（需用户确认）

| # | 条目 | 理由 |
|---|---|---|
| 1 | … | 新模型发布，有 T0 技术报告 |

## 信源状态

（以 `scripts/collect_feeds.py --report` 的输出为底稿，补上页面读取结果。三种情况分开写，只有第一种能说明「没有发布」。）

- 抓到但窗口内 0 条：信源名
- 本次未抓到：信源名（原因：需浏览器 / 前端渲染 / 超时 / 证书 / 页面改版）
- 覆盖不全：信源名（未覆盖完整窗口，缺 MM-DD 至 MM-DD / 被截断，共 N 条只保留 M 条）
- 使用了 ok 以外状态的信源：信源名（page-only / blocked / tbd）
- 论文候选池：N 篇，有筛选信号入选 N 篇

## 来源

[1] 标题 · 发布方 · T0 · 发布 YYYY-MM-DD · 访问 YYYY-MM-DD · URL

## 排序记录（可选）

规则见 `references/collect.md` 第 5 步，可用 `scripts/rank_items.py --format md` 生成。

| 名次 | 条目 | 公司 / 来源 | 分类 | 来源分 | 相关 | 新鲜 | 总分 | 备注 |
|---|---|---|---|---|---|---|---|---|
| 1 | … | … | … | 3 | 1 | 2 | 6 | |

截断条目（有 T0/T1 支撑、未进正文，供人工判断）：

- 条目：截断原因（名次 / 同一公司已有 3 条 / 让位给保底条目）

## 核验记录

检查 N 句，改写 N 句，删除 N 句（带引用句数可用 `scripts/check_citations.py --count` 统计）；打不开的链接：…

---

## 回执（可选，交付说明，非周报正文）

1. watermark：本次收录条目中最新的发布时间与写入位置
2. 社区反应：last30days 状态（已配置 / 未配置 / 未安装）与处理方式
3. 工具储备条目：是否交给 topmind-capture（需用户确认）
4. 信源候选：是否修改 `config/sources.yaml`（需用户确认）
5. analyze 候选：请用户点名
6. 出稿建议：短稿或快讯 → topmind-briefs，公众号 → topmind-wechat-post，其他 → topmind-write（不自动调用）
