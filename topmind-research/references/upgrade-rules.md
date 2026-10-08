# collect → analyze 升级规则 / analyze → collect 回流规则

## 升级（collect → analyze）

满足任一条即升级：

1. **用户明确指定**：用户说"深挖/细读/分析一下"。
2. **命中评分线**：collect 评分（热度×相关性×新鲜度）Top 3，或单条被标记为"重大"。
3. **重大发布/突发**：新模型、新论文、新融资并购、高管变动——默认升级，不等评分。

升级时 collect 必须移交：原始条目 + 已收集的来源链接 + 初步评分理由。analyze 不得重复做 collect 已完成的抓取。

## 回流（analyze → collect）

1. analyze 每份研究报告输出一份"结论摘要"（≤5 行），写入用户记忆/专题。
2. collect 下次 sweep 扫到同一主题的新动态时，自动关联历史结论摘要作上下文。
3. analyze 发现的"值得持续追踪"事项（如某公司的月度发布节奏），可写入 `config/sources.yaml` 的备注，collect 后续覆盖。

## 边界示例

- "OpenAI 发了新模型" → collect 出快讯；"这个新模型的技术报告讲了什么" → analyze。
- "这周有什么新工具" → collect；"对比一下 A 和 B 两个工具的架构" → analyze。
