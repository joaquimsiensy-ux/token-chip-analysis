# 工单复核 R1 提示词（只读）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`。
2. 只读：不修改、不新建文件、不 commit、离线。
3. 报告全文打印到 stdout，首行固定：`# 工单复核 R1：通过` 或 `# 工单复核 R1：退回`。

## 任务
复核 `maintenance/repair-20260916-drift-audit/workorder_r1.md`（依据 `blind_r1_report.md`）。对 §2 每一条逐项核：
a) **锚文本**在指定文件里 `grep -F` 是否命中**恰 1 处**且行号一致（行号错即退回，列出实际行号）；
b) **替换文本**是否与 `scripts/` 现行代码事实一致（如 D5 恒等式、D12 键集、D13 解析顺序、D18 SRC_PRIORITY 数值、C1 finalized 压界、F1 五查定义）；引用的章节/条目名是否真实存在（如"data-pipeline-solana-capture §7 第 7 条""tiering §6a""scan-schemas 对账 wrapper 表""methods 行为指纹总纲"）；
c) 是否会撞 `scripts/tests/contract_manifest.json` 的 needle（required 被删或 banned 被引入）、`casebook_lint.py` 六字段结构、`test_g3_docs_guards.py` 的段落断言；
d) **同族遗漏**：同一旧口径在白名单文件里是否还有其他副本没被本工单覆盖（只报白名单内的；白名单外的另列"建议下轮"）；
e) §1.1 字节约束是否可行（估算净增减）；§0.3 白名单是否恰好覆盖 §2 全部改动；
f) 替换文本本身是否引入新的漂移或误导。
不评价 D1 暂缓决定本身，但若你认为 D1 的"改文本掩盖"存在合理替代方案可以提。

## 输出格式
```
# 工单复核 R1：通过|退回
## 逐条核对表
| 条目 | 锚命中 | 事实一致 | needle/守卫 | 意见 |
## 退回理由（若退回）
## 修订建议（逐条，给可直接粘贴的修订文本）
## 同族遗漏（白名单内 / 建议下轮）
```
