# 断点续跑

## 状态文件放哪

| 环境 | analyze 状态目录 | collect watermark |
|---|---|---|
| topmind 工作区（根目录有 `topmind.yaml` 或 `.topmind/`） | `.topmind/research/{slug}/` | `.topmind/research/collect-watermark.md` |
| 其他 | 当前工作目录下 `research/{slug}/` | `research/collect-watermark.md` |

`{slug}`：日期 + 题目关键词，如 `2026-10-08-moe-progress`。

## analyze 状态目录内容

- `state.md`：按 `assets/templates/state.md` 维护，每完成一步更新一次。
- `findings/*.md`：子 agent 回传内容较多时写在这里，状态文件只记录路径。

## collect watermark 格式

```markdown
---
watermark: 2026-10-07T18:00:00+08:00   # 上次收录条目中最新的发布时间
last_run: 2026-10-08T09:30:00+08:00
scope: all                              # all 或用户指定的方向
---
```

## 恢复流程

1. 用户说「继续」或重新发起同一题目时，先找状态目录。
2. 读 `state.md`：确认简报、已完成子题、待办。
3. 只做待办；已完成子题的结论和来源直接沿用。
4. 状态文件超过 7 天：提醒用户资料可能过时，问是否沿用。
