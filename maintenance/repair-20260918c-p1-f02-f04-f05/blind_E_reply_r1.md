# 盲审 E：FAIL

审查范围：`0f6f4e47a65f..8e193f2a5107e6478855e4fcda3db6398699a596`。报告全文已打印到 stdout。

唯一失败项是 a) 的文件范围：实际包含 **6 个文件**，要求为 **4 个**。版本、文案及事实抽核通过。

**E-B1-01：版本登记差异包含额外文件**

文件:行：

- `maintenance/repair-20260918c-p1-f02-f04-f05/E_done.md:1`
- `maintenance/repair-20260918c-p1-f02-f04-f05/blind_E_prompt.md:1`

事实：除四个指定文件外，diff 还新增上述两个文件。此处为新增整文件定位，仅依据路径及差异统计，未读取正文。

后果：不满足“diff 只含这四个文件”，按结论规则必须判 FAIL。工单允许新增 E_done.md，不能覆盖本次明确限定的四文件范围。

建议：拆分 maintenance 记录与版本登记，并提供只含四个文件的审查区间后复审。

其余核对结果：

- **a) 内容通过**：VERSION:1、pyproject.toml:15、SKILL.md:23、CHANGELOG 最新索引 :13 和详细标题 :97 均为 `9.0.0`。SKILL.md 前后均为 **8021 B**；三个版本文件仅有指定替换。`references/`、`scripts/`、`commands-staging/` 零差异。
- **b) 通过**：按工单 §2 第 4 项原文重建 CHANGELOG，逐字节一致。索引紧邻原 8.0.0 行之前；详细段紧邻原 8.0.0 标题之前，段后恰空一行。共新增 12 行，其他字节零改动。
- **c) 通过**：以下 13 项机器核验均符合记录。

| 断言 | 证据 |
|---|---|
| F04：+82/−4，三文件 | `d11730d^..d11730d -- scripts/` |
| F05：+144/−10，三文件 | `47e9efb^..47e9efb -- scripts/` |
| F02：+92/−3，四文件 | `3ab1874^..3ab1874 -- scripts/` |
| `price_receipt_errors` 函数存在 | scripts/report/stage2_closeout.py:243 |
| `PRICE_POINT_STATUSES` 四种状态一致 | scripts/report/stage2_closeout.py:240 |
| 收据输出 `price_file_sha256` | scripts/prices/price_check.py:195 |
| token 写入 `circulating_supply_source` | scripts/report/facts_gate.py:504 |
| RPC 拒绝文案逐字存在 | scripts/lib/net.py:300 |
| FAIL/ALL_SKIP 拒绝文案逐字存在 | scripts/report/stage2_closeout.py:277 |
| 纯申报拒绝文案逐字存在 | scripts/report/stage2_closeout.py:257 |
| 扁平键“键名错位”文案存在 | scripts/report/facts_gate.py:384 |
| getcode 校验正则一致 | scripts/lib/rpc_batch.py:84 |
| Q15 存在且唯一 | maintenance/repair-20260918c-p1-f02-f04-f05/code_change_pending.md:19 |

从 `8b041842` 到三个施工 commit 的 scripts 累计差异分别为 **+82/−4、+226/−14、+317/−16**；最终八文件，与各段增量及累计记录相符。

d) 执行结果：

| 命令 | 结果 |
|---|---|
| `python3 -B scripts/tests/test_version_consistency.py` | exit 0；`PASS: M-03 version metadata consistent at 9.0.0` |
| `python3 -B scripts/tests/changelog_lint.py` | **SKIPPED-BY-RULE**；源码 :16、:27、:41 明确读取 archive，未启动 |
| `python3 -B scripts/tests/docs_lint.py --all` | **SKIPPED-BY-RULE**；源码 :272、:306 枚举并读取 archive 文件，未启动 |

两项跳过不计 FAIL。全程离线、只读，未 commit、未改文件；未读取 `~/.codex/`、memories 或指定禁读文件正文。
