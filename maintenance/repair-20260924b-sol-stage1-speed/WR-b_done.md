# WR-b 完成：两协议 ACTIVE 登记已追加，0.4 全部已运行检查通过，待调度方 0.7 验收

按 WR-b v2 仅修改 `scripts/lib/producer_history.py` 并新增本报告。在原元组闭合 `)` 前追加 coverage/v1、coverage-pointer/v1 两条 ACTIVE；原有 38 条登记（含 WR-a 四条）逐字不变，现共 40 条；未新增 shared-map 协议。

前置核对与复算（写入前完成）：

- 初始 `git status --short` 无输出，工作树干净。
- HEAD：`fcf81f062daa004a37862a92cfe1c488a98da2b0`。
- `git merge-base --is-ancestor f78b5c4575ebe1db36f2cf3a96e75b79731f3fc6 HEAD`：退出码 0。
- 目标脚本：`scripts/solana/sqd_coverage_probe.py`。
- 源码提交：`f78b5c4575ebe1db36f2cf3a96e75b79731f3fc6`。
- `git show 'f78b5c4575ebe1db36f2cf3a96e75b79731f3fc6:scripts/solana/sqd_coverage_probe.py' | shasum -a 256`：`d4adc0c88f87bc03b3d847db7df9c9f7e588cb503734dfd977b818b581d998d8`。
- `shasum -a 256 scripts/solana/sqd_coverage_probe.py`：`d4adc0c88f87bc03b3d847db7df9c9f7e588cb503734dfd977b818b581d998d8`。
- 工单填值：`d4adc0c88f87bc03b3d847db7df9c9f7e588cb503734dfd977b818b581d998d8`。三方一致。
- 两条 reason 均为：`9.2.0 驳回继承导出/继承（W1）＋find-known-map（W2）`。

差异：`producer_history.py` 为 +16/-0；本报告为 +108/-0；合计 +124/-0。`git diff --check` 通过；字节级追加核对及 AST 条目核对通过。

测试结果（均离线、Python `-B`；测试子进程继承 `PYTHONDONTWRITEBYTECODE=1`；下表列实际尾行）：

| 测试 | 退出码 | 尾行 |
|---|---:|---|
| `test_producer_registry_current.py` | 0 | `producer registry: 0 FAIL` |
| `test_batch3_solana_producers.py` | 0 | `PASS B3-G2: Solana slot/envelope/txn/timestamp producer guards` |
| `test_sqd_gap_repair.py`（四组临时跳过） | 0 | 原 main 尾行：`GREEN 29c implemented validate_current_candidates 已实现`；包装器尾行：`WR-b repair runner: exit=0, skipped=4` |
| `test_sqd_coverage_probe.py` | 0 | `PASS SQD coverage probe: 24/24 offline groups` |
| `test_f03_sharedmap_reuse.py` | 0 | `PASS F-03 shared-map reuse: 15/15 groups` |
| `invariant_scan.py` | 0 | `PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=62, formal_entrypoints=61, exceptions=0` |

注册表逐项判读：直接执行 `python3 -B scripts/tests/test_producer_registry_current.py`，53 项均为 `ok`，0 FAIL。下表按实际检查内容列出，Git 表按登记顺序列出；提交和 SHA 使用唯一前缀缩写，新增项完整值见上方复算记录。

| 检查项 | 结果 |
|---|---|
| 登记脚本集合与守卫清单一致 | ok |
| fetch_sqd_transfers_v2.py 必要协议在场 | ok |
| fetch_sqd_transfers_v2.py 当前哈希：sqd-solana-cache/v4 | ok |
| sqd_coverage_probe.py 必要协议在场 | ok |
| sqd_coverage_probe.py 当前哈希：sqd-solana-coverage-pointer/v1 | ok |
| sqd_coverage_probe.py 当前哈希：sqd-solana-coverage/v1 | ok |
| sqd_gap_repair.py 必要协议在场 | ok |
| sqd_gap_repair.py 当前哈希：sqd-solana-cache/v4 | ok |
| sqd_gap_repair.py 当前哈希：sqd-solana-coverage-resolution/v1 | ok |
| sqd_gap_repair.py 当前哈希：sqd-solana-repair-bundle/v1 | ok |
| sqd_gap_repair.py 当前哈希：sqd-solana-repair-pointer/v1 | ok |
| window_fetch.py 必要协议在场 | ok |
| window_fetch.py 当前哈希：solana-window-fetch-receipt/v3 | ok |

| 登记序号 | 脚本 | 协议 | commit 前缀 | 登记 SHA＝Git 实得 SHA 前缀 | Git 复现 |
|---:|---|---|---|---|---|
| 1 | anchor_plan.py | anchor-plan/v2 | 3b76db801309 | e5168a455d53 | ok |
| 2 | anchor_plan.py | anchor-plan/v2 | 0ec6d1e2365c | 1a461169f077 | ok |
| 3 | fetch_sqd_transfers_v2.py | sqd-solana-cache/v4 | 75aa622a5467 | 2589f6a396c2 | ok |
| 4 | fetch_sqd_transfers_v2.py | sqd-solana-cache/v4 | 47b3620fb2f7 | a94b193b94ba | ok |
| 5 | sqd_coverage_probe.py | sqd-solana-coverage/v1 | c2372635cf56 | e41370b185ae | ok |
| 6 | sqd_coverage_probe.py | sqd-solana-coverage-pointer/v1 | c2372635cf56 | e41370b185ae | ok |
| 7 | sqd_coverage_probe.py | sqd-solana-coverage/v1 | 55d4efede78f | bccf1802b6a5 | ok |
| 8 | sqd_coverage_probe.py | sqd-solana-coverage-pointer/v1 | 55d4efede78f | bccf1802b6a5 | ok |
| 9 | sqd_coverage_probe.py | sqd-solana-coverage/v1 | f0469a376c01 | be415db35525 | ok |
| 10 | sqd_coverage_probe.py | sqd-solana-coverage-pointer/v1 | f0469a376c01 | be415db35525 | ok |
| 11 | sqd_coverage_probe.py | sqd-solana-coverage/v1 | cdc4f87f8e3e | c4980c984b08 | ok |
| 12 | sqd_coverage_probe.py | sqd-solana-coverage-pointer/v1 | cdc4f87f8e3e | c4980c984b08 | ok |
| 13 | sqd_gap_repair.py | sqd-solana-cache/v4 | 5782f76773fa | c8beb16e998c | ok |
| 14 | sqd_gap_repair.py | sqd-solana-repair-bundle/v1 | 5782f76773fa | c8beb16e998c | ok |
| 15 | sqd_gap_repair.py | sqd-solana-coverage-resolution/v1 | 5782f76773fa | c8beb16e998c | ok |
| 16 | sqd_gap_repair.py | sqd-solana-repair-pointer/v1 | 5782f76773fa | c8beb16e998c | ok |
| 17 | sqd_gap_repair.py | sqd-solana-cache/v4 | 80ab2a380952 | da6eb283ab08 | ok |
| 18 | sqd_gap_repair.py | sqd-solana-repair-bundle/v1 | 80ab2a380952 | da6eb283ab08 | ok |
| 19 | sqd_gap_repair.py | sqd-solana-coverage-resolution/v1 | 80ab2a380952 | da6eb283ab08 | ok |
| 20 | sqd_gap_repair.py | sqd-solana-repair-pointer/v1 | 80ab2a380952 | da6eb283ab08 | ok |
| 21 | sqd_gap_repair.py | sqd-solana-cache/v4 | ddfeec1b307f | 60b48f86154d | ok |
| 22 | sqd_gap_repair.py | sqd-solana-repair-bundle/v1 | ddfeec1b307f | 60b48f86154d | ok |
| 23 | sqd_gap_repair.py | sqd-solana-coverage-resolution/v1 | ddfeec1b307f | 60b48f86154d | ok |
| 24 | sqd_gap_repair.py | sqd-solana-repair-pointer/v1 | ddfeec1b307f | 60b48f86154d | ok |
| 25 | sqd_gap_repair.py | sqd-solana-cache/v4 | 4c5cd578a5f1 | 25f04ff10bc4 | ok |
| 26 | sqd_gap_repair.py | sqd-solana-repair-bundle/v1 | 4c5cd578a5f1 | 25f04ff10bc4 | ok |
| 27 | sqd_gap_repair.py | sqd-solana-coverage-resolution/v1 | 4c5cd578a5f1 | 25f04ff10bc4 | ok |
| 28 | sqd_gap_repair.py | sqd-solana-repair-pointer/v1 | 4c5cd578a5f1 | 25f04ff10bc4 | ok |
| 29 | sqd_gap_repair.py | sqd-solana-cache/v4 | 7846184f9f2b | 3f89aab13054 | ok |
| 30 | sqd_gap_repair.py | sqd-solana-repair-bundle/v1 | 7846184f9f2b | 3f89aab13054 | ok |
| 31 | sqd_gap_repair.py | sqd-solana-coverage-resolution/v1 | 7846184f9f2b | 3f89aab13054 | ok |
| 32 | sqd_gap_repair.py | sqd-solana-repair-pointer/v1 | 7846184f9f2b | 3f89aab13054 | ok |
| 33 | window_fetch.py | solana-window-fetch-receipt/v3 | 75aa622a5467 | 56d94cbecf47 | ok |
| 34 | time_spotcheck.py | time-spotcheck/v3 | b52cbedf2302 | 87bbad2246f0 | ok |
| 35 | sqd_gap_repair.py | sqd-solana-cache/v4 | 59f88b84c9ab | 15822564046e | ok |
| 36 | sqd_gap_repair.py | sqd-solana-repair-bundle/v1 | 59f88b84c9ab | 15822564046e | ok |
| 37 | sqd_gap_repair.py | sqd-solana-coverage-resolution/v1 | 59f88b84c9ab | 15822564046e | ok |
| 38 | sqd_gap_repair.py | sqd-solana-repair-pointer/v1 | 59f88b84c9ab | 15822564046e | ok |
| 39 | sqd_coverage_probe.py | sqd-solana-coverage/v1 | f78b5c4575eb | d4adc0c88f87 | ok |
| 40 | sqd_coverage_probe.py | sqd-solana-coverage-pointer/v1 | f78b5c4575eb | d4adc0c88f87 | ok |

新增第 39、40 条分别对应 coverage/v1 与 coverage-pointer/v1；两条 Git 复现均通过，且两协议当前哈希检查均通过。repair 四协议当前哈希检查也全部通过。未触发停工条件。

未运行，调度方本机补验：

- `test_sqd_gap_repair.py::functional_repair_regressions`：直接读取 `.staging_b3`。
- `test_sqd_gap_repair.py::blocks_cache_end_to_end`：直接读取 `.staging_b3`。
- `test_sqd_gap_repair.py::live_mock_transport_regression`：经 `staged_missing_transactions` 读取 `.staging_b3`。
- `test_sqd_gap_repair.py::batch3b_semantic_regressions`（含其内部 adoption 回归）：经 `staged_missing_transactions` 读取 `.staging_b3`。

以上使用系统 tempfile 内的包装器，通过 `unittest.mock.patch.object` 临时跳过整个分组，未修改测试源码。当前 `test_sqd_coverage_probe.py` 未发现上述禁读依赖，24 组全部运行；未把跳过组计为通过。五项定向测试及 Python 子进程启用临时 audit hook，阻止禁读路径和联网，运行未触发拦截。

剩余失败明细：已运行检查无失败；上述四组未运行，不代表通过。测试日志中负向用例的预期错误输出不属于测试失败。

0.7 正式入口验收未执行：由调度方登记 commit 后执行真实 ACTIVE 双协议查询、自包含发布产物的真实 validate_coverage 兼容检查，以及仅内存移除两条登记的查询负对照。0.4 既有测试结果不替代 0.7 验收。

W1 过渡版本仅作施工测试，无需保留的正式产物。此结论沿用工单所载调度方前置核查；本次两条登记不覆盖 W1 过渡哈希 `ab2371f5…`。

全程未读取 `~/.codex/` 或 memories，未读取其他禁读目录；离线，无 commit/push、stash/checkout/reset、worktree 或批量删除操作。仓库交付文件仅为白名单中的源码文件及本报告；临时包装器与日志仅放在系统 tempfile。
