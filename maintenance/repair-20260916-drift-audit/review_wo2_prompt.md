# 工单 R2 复核提示词（只读）

## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`（含通配读取）。
2. 只读、离线、不 commit。报告打印到 stdout，首行：`# 工单R2复核：通过` 或 `# 工单R2复核：退回`。

## 任务
复核 `maintenance/repair-20260916-drift-audit/workorder_r2.md`（依据 `blind_r2_report.md`）：
a) 每个锚 `grep -n -F` 恰 1 处且行号一致；
b) 替换文本与 `scripts/` 代码事实一致（D1 V4 符号方向与 traps 第 12 条编号、D2 DEFAULT_ROOT/跨案行为、D3 cost_engine 输入形态、D4 REMAINDER、D5 wave/flow 六字段齐全而分布扫描不齐、D6 `--pools` 回退与 `--out` 默认值、D7 accumulate_offenders 默认输出路径、D8 §4 表项、F2 chain_registry robinhood 档位）；
c) needle/守卫/字节可行性；d) 白名单内同族遗漏（白名单外只列"建议下轮"）；e) 替换文本是否引入新漂移。

## 输出格式
```
# 工单R2复核：通过|退回
## 逐条核对表
| 条目 | 锚命中 | 事实一致 | needle/守卫 | 意见 |
## 退回理由
## 修订建议（可直接粘贴）
## 同族遗漏（白名单内 / 建议下轮）
```
