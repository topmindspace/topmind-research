# topmind-research-analyze · 论文与资料深度研究

## 信息源（可配置）

读 `config/sources.yaml`：
- `paper_sources`：arXiv 分类、Hugging Face 论文榜
- `report_sources`：各公司研究报告、system cards、技术博客（见 `companies[].reports`）

用户直接给的资料（链接/PDF/文本）优先级最高。

`config/categories.yaml` 定义研究类型：论文深读 / 技术报告解读 / 横向对比 / 数据分析。

## 工作流

1. **定题**：一句话说清这次研究要回答什么问题。问题不清先问。
   输入方式（链接/文件/主题/对比）见 `references/input-guide.md`。
2. **并行深挖**：借鉴 `wide_research` 的 manager+workers 模式——一个 coordinator 按统一 schema 并行查多个源（论文原文、官方报告、第三方解读、相关数据），结果归一化。
3. **统一输出 schema**（每项研究必含）：
   - 一句话结论（带置信度：高/中/低，定义见 `references/input-guide.md`）
   - 关键数据/事实（带来源）
   - 方法与证据强度
   - 局限与反方观点
   - 来源清单
4. **核实门**：强制过 `references/verification.md`。论文类以原文为准，二手解读只作线索；数据类必须回一手出处；厂商自称数据标"厂商口径"。
5. **交付**：研究报告（Markdown），需要出稿时转 `topmind-write` / `topmind-briefs`。
6. **回流**：结论摘要写入用户记忆/专题，供 collect 下次关联（见 `references/upgrade-rules.md`）。

## 铁律

- 不编造数据，不脑补论文没写的东西；不确定的写"原文未提及"。
- 对比类必须说明对比口径（时间/版本/测试集），口径不一致不硬比。
- 时效：注明资料的发布时间，研究结论标注"截至XXXX-XX-XX"。
