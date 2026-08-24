## 裁决：BLOCK

九个登记面文件本身未发现逻辑、计数或白名单问题；阻断点在完成报告的验收证据不真实有效。

### 阻断问题

1. [f009_closeout_done.md](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260824-lit-regression/f009_closeout_done.md:189)

   报告声称用以下路径核验禁改文件：

   - `scripts/wave_scan.py`
   - `scripts/entity_source_trace.py`

   但这两个路径不存在，真实路径是：

   - `scripts/report/wave_scan.py`
   - `scripts/report/entity_source_trace.py`

   `git diff --exit-code HEAD -- <不存在的路径>` 仍会返回 0，因此该命令不能证明这两个禁改文件未被修改。报告随后在第 193、291–292 行把这个返回码当成完整边界证明，属于无效证据。

   我独立用真实路径核对后，两文件及其余禁改文件确实都与 HEAD 一致；所以这是完成报告的证据真实性缺陷，不是生产代码缺陷。按工单要求“逐项证据＋命令＋原始输出”，仍应修正报告并用真实路径重跑后才能入库。

### 其余核对结果

- `git diff --stat HEAD`：恰好 9 个已跟踪登记文件，`27 insertions / 10 deletions`；没有白名单外或禁改生产文件进入 tracked diff。
- 另有两个未跟踪 maintenance 文件：

  - `f009_closeout_done.md`：工单要求的报告。
  - `legacy_evm_v2_ledger_inventory.md`：非 F-009 产物，但位于工单明确允许的工程档案目录。提交 F-009 时应明确排除，不能使用无选择的 `git add -A`。

- 每个 tracked hunk 均有工单归属，未发现夹带改动。
- 版本三件均为 `6.52.2`；`SKILL.md` 仅等长替换版本注释，实际 `7961` 字节，未改正文。
- CHANGELOG 的 `SUITE 129→131`、契约 `195→197` 均与 HEAD 前后实数一致；成本/质量指标存在。
- `run_all.py` 新增块符合工单；AST 实数为 131，两项新测试各登记一次且文件存在。
- 文档语义与生产实现一致：

  - `evm-dict` 只豁免 `burn_cum_pct`，「锁仓/销毁」参与堆叠与散户残差。
  - `sol-rows` 的「锁仓/销毁」为堆叠外披露桶。
  - `sol-anchor-rows` 无豁免。
  - evm_v2 的 argument 字符闸、固定两类文件枚举及集合等式都发生在临时文件和重放子进程之前。
  - 未发现写过头或写错。

- 契约核对：

  - CT-BANNED-23：HEAD authority 精确命中一次；当前 authority 清零；新文案不含旧字面。
  - CT-SEMANTIC-63：authority 中精确命中一次。
  - manifest、snapshot 均为 197，ID 唯一、集合一致、snapshot 严格排序，五字段结构正确。

- 只读实跑通过：

  - `changelog_lint.py`
  - `test_version_consistency.py`
  - `docs_lint.py --all`

- 未直接运行 `test_contract_routes.py`：该脚本会创建 `TemporaryDirectory` 并写入临时夹具，违反本次“禁止创建任何文件”的硬约束。其与本次变更有关的真实 manifest、snapshot、needle、排序及 SKILL 路由条件已用不落盘检查独立通过；未看到导致该测试失败的登记问题。
- done 报告列出的九个文件 SHA-256 与当前实物全部一致。

结论：修正完成报告第 189 行的两个路径，并更新相应原始验证输出后，当前九个登记面改动预计可转为 PASS。
[exited with code 0]
