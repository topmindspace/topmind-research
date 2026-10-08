# 升级、交接与沉淀

本技能不自动升级深挖、不自动写记忆、不自动修改配置。以下动作都只在回执里列为建议，用户确认后再执行。

## collect → analyze

1. collect 周报末尾列出「analyze 候选」，最多 3 条，每条写理由：用户指定的方向 / 新模型或新论文发布 / 重大融资并购或高管变动 / 排序前 3 且有 T0 原文。
2. 用户点名某条后才进入 analyze。用户在请求里已明确说「扫完把 X 深挖一下」时，视为已确认。
3. 交接内容：原始条目、已收集的来源链接、排序得分与理由。analyze 不重复抓取 collect 已拿到的来源，只补缺。

## 沉淀（collect / analyze 完成后）

1. **报告落盘**
   - 在 topmind 工作区内、能确定专题：写到 `{大类}/{专题}/YYYY-MM-DD-{题目}.md`（与 topmind-organize「综合默认落专题根」一致）。
   - 能确定大类但没有专题：写到大类根目录，回执里建议是否开专题。
   - 确定不了：按 topmind-capture 的规则进收件箱。
   - 不在 topmind 工作区：交付在对话里，或写到用户指定的目录。
   - frontmatter：`source_type: ai-derived`、`as_of: YYYY-MM-DD`、`sources: <来源数>`、`produced_by: topmind-research/<mode>`。
2. **记忆**：回执里给出不超过 5 行的结论摘要，问用户是否交给 topmind-memory 记下。用户不确认就不写。
3. **信源变更**：研究中发现值得长期追踪的新信源、或现有信源失效，在回执里列为「信源候选」（名称、URL、验证方式、验证日期），由用户决定是否改 `config/sources.yaml`。
4. **出稿**：用户要发文时，把事实表（`assets/templates/fact-sheet.md`）交给 topmind-briefs / topmind-wechat-post / topmind-x-article，写作技能直接引用表里的事实和来源，不再重复核验同一批事实。

## 边界示例

- 「OpenAI 发了新模型」→ collect 收录；「这个新模型的技术报告讲了什么」→ analyze。
- 「这周有什么新工具」→ collect；「对比 A 和 B 两个工具的架构」→ analyze。
- 「大家怎么评价这个新模型」→ last30days。
- 「把我这周存的几篇论文笔记整理一下」→ topmind-organize。
