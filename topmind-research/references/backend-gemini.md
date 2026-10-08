# 可选后端：Gemini Deep Research

只在用户明确要求「用 Gemini Deep Research 跑」时使用。默认流程不调用，本技能也不内置调用脚本。

资料来源：Google AI for Developers「Gemini Deep Research agent」文档，访问 2026-10-08，https://ai.google.dev/gemini-api/docs/deep-research 。接口处于 preview，参数可能变化，用之前重新打开文档核对。

## 一、使用前确认

向用户确认三件事，确认后再开始：

1. **费用**：文档估算每个任务约 1–3 美元（`deep-research-preview-04-2026`），Max 版约 3–7 美元（`deep-research-max-preview-04-2026`），按用户自己的 Gemini API 账单计费。
2. **密钥**：用户自己在环境变量里提供 `GEMINI_API_KEY`。不得把密钥写进 `config/`、报告或状态文件。
3. **时长**：任务在后台运行，最长 60 分钟，多数在 20 分钟内完成。

## 二、调用方式（Interactions API）

- 只能通过 Interactions API 调用，必须 `background=True`（同时需要 `store=True`，SDK 默认开启）。
- 先用 `agent_config` 的 `collaborative_planning: True` 拿到研究计划，把计划和本技能的研究简报（`assets/templates/research-brief.md`）对齐，交用户确认。
- 用 `previous_interaction_id` 继续：修改计划时保持 `collaborative_planning: True`；用户批准后设为 `False` 开始执行。
- 轮询 `interactions.get(id)`，状态从 `in_progress` 变为 `completed` 或 `failed`。
- 默认工具：`google_search`、`url_context`、`code_execution`。不支持自定义 function calling 和结构化输出。

```python
from google import genai
client = genai.Client()  # 从环境变量读取 GEMINI_API_KEY
plan = client.interactions.create(
    agent="deep-research-preview-04-2026",
    input="<研究简报全文 + 输出格式要求 + 「查不到的数据写明查不到，不要估算」>",
    agent_config={"type": "deep-research", "thinking_summaries": "auto", "collaborative_planning": True},
    background=True,
)
# 轮询 client.interactions.get(plan.id)，计划确认后：
run = client.interactions.create(
    agent="deep-research-preview-04-2026",
    input="计划确认，开始执行",
    agent_config={"type": "deep-research", "collaborative_planning": False},
    previous_interaction_id=plan.id,
    background=True,
)
```

## 三、结果怎么用

1. Gemini 的报告本身不是来源。报告里的每个结论回到它引用的原始网页，按 `references/verification.md` 定级、核对，再写进本技能的报告。
2. 它引用的页面打不开或对不上的，按「无法核实」处理。
3. 中文厂商的信息，用 `config/sources.yaml` 里的官方信源补查一遍，Google 搜索对中文一手来源的覆盖不保证完整。
4. 最终报告按 `assets/templates/analyze-report.md` 输出，方法一节写明「检索由 Gemini Deep Research 完成，结论经本技能核验门复核」。
5. 交互 ID 记进状态文件（`references/state.md`），便于后续追问。
