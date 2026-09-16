# 工单复核 R2 提示词（只读）——复核 workorder_r1.md v2

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`。
2. 只读：不修改、不新建文件、不 commit、离线。
3. 报告全文打印到 stdout，首行固定：`# 工单复核 R2：通过` 或 `# 工单复核 R2：退回`。

## 任务
复核 `maintenance/repair-20260916-drift-audit/workorder_r1.md`（v2）。上一轮意见在 `review_r1_reply.md`（v2 已按其修订）。重点：
a) v2 §2 每个锚文本 `grep -n -F` 是否恰 1 处且行号一致（注意 D13 的多行合并锚、split-run:53/scan-schemas:396 等同行两锚）；
b) 上一轮退回的 7 条理由是否全部消化；采纳后的替换文本是否仍与代码事实一致；
c) 新增的 F1 五处（context-discipline:27/58、scan-schemas:17/396/484）与 D8 四处（tiering:82 第二锚、scan:135/139、methods:134）替换文本是否引入新漂移或误导，是否撞 needle（`CT-*`）；
d) 全组内存模拟：§1.1 字节、casebook 六字段、G3 四项、needle 无损；
e) 白名单内是否仍有同族遗漏（白名单外只列"建议下轮"）。

## 输出格式
```
# 工单复核 R2：通过|退回
## 逐条核对表
| 条目 | 锚命中 | 事实一致 | needle/守卫 | 意见 |
## 退回理由（若退回）
## 修订建议（逐条，可直接粘贴）
## 同族遗漏（白名单内 / 建议下轮）
```
