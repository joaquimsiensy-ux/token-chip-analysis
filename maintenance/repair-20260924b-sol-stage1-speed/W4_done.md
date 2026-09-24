# W4 完成：合并候选 slot 的 SQD 请求；离线施工验证通过，WR-a 登记及正式入口验收待调度方

## 结果与边界

- α/β 候选修复共用一次合并 SQD 查询流程，无故障时逐 slot 为 `sqd-census=1`、`sqd-probe=0`、`reference-getBlock=1`；workers=1、4 均已验证。β 搜索查询保持不变。
- 状态校验仍在 Helius 之前；重复目标块报 `SQD census duplicated slot ...`。SQD 重试耗尽优先返回 2；SQD 合法且状态匹配后，Helius 额度耗尽返回 3、写 STOPPED，并保留成功 ledger 前缀。恢复不重采已完成 slot。
- 新采 evidence 两组请求／响应摘要分别相等。独立旧格式模板构造的全旧、全新、认领旧前缀＋新剩余 slot 三类产物均通过直接深验；旧 evidence 字节和旧 ledger 行原样保留，旧 slot 无重新请求。三类均包含 confirmed 缺失 nonce 交易。
- 生产增删合计 52 行，未超过 60 行。AST 对比确认仅 `_census_body`、`_fetch_live_slot` 和删除 `_state_probe` 涉及函数变化；W1 状态校验、β 搜索、退避、恢复、落盘及并发调度函数未变。schema、CLI、历史登记和版本文件未改。
- 未联网、未 commit/push、未 stash/checkout/reset、未建 worktree、未执行批量删除。只写三份白名单代码／测试文件、本报告，以及系统 tempfile 内的测试产物和运行器。

## §0.1 开工核验

工作目录：`/Users/uravvv/.claude/skills/token-chip-analysis`。

```text
W4_BASE=cfe2f41132bd3f162f3d356f359c9eba72a500d3

$ git status --short
（空，exit 0）

$ git rev-parse HEAD
83ca8394bcba5ebad136056354a031c7ae38a88c

$ git merge-base --is-ancestor "$W4_BASE" HEAD
（空，exit 0）

$ git diff --quiet "$W4_BASE" HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md assets
（空，exit 0）

$ git merge-base --is-ancestor cc6298b HEAD
（空，exit 0）
```

结束时 HEAD 仍为 `83ca8394bcba5ebad136056354a031c7ae38a88c`。结束检查另发现 `maintenance/repair-20260924b-sol-stage1-speed/workorder_W2.md` 出现外部修改；本轮未写入或恢复该文件。

## 整行锚与引用核验

首次修改前用 `grep -n -F -x` 核验，以下整行均恰好命中一次：

```text
scripts/solana/sqd_gap_repair.py
46:# 版本钉：共享常量/请求模板变化不会改变本脚本 sha（只哈希本文件）。升 SOLANA_MAX_SUPPORTED_TX_VERSION
643:def _census_body(slot):
917:def _state_probe(transport, slot, *, retry=False):
1022:def _fetch_live_slot(slot, state, beta_slots, reference_pool, sqd_transport,

scripts/tests/test_sqd_gap_repair.py
1321:def main():

scripts/tests/test_batch8_repair_scale.py
61:            if kind == "sqd-census":
325:def main():
```

删除前源码引用检索 `rg -n '_state_probe' scripts references --glob '!attic.md'`：

```text
scripts/solana/sqd_gap_repair.py:917:def _state_probe(transport, slot, *, retry=False):
scripts/solana/sqd_gap_repair.py:1024:    present, nonce_count, probe_query_sha, probe_response_sha = _state_probe(
```

替换调用后、删除定义前再次检索仅剩定义。删除后检索 scripts、references（排除 attic.md）、SKILL.md、commands-staging、VERSION、pyproject.toml、CHANGELOG.md、assets：无剩余引用，rg exit 1。`_probe_fingerprint` 与生产 `sqd-probe` transport 支持保留。

## 实际改动

当前行号：

- `scripts/solana/sqd_gap_repair.py:48`：增加三行 9.2.0 producer 换代注释；`:647/:655/:658`：复用探针选择器；`:1009-1021`：合并请求、目标块去重、原始 nonce 计数和摘要；原 `:917-937` 的 `_state_probe` 已删除，原第二次 census 及两请求块头不一致检查已删除。
- `scripts/tests/test_sqd_gap_repair.py:252`：census 夹具增加 instructions；`:1323-1581`：自包含交易、18 个状态／响应向量、单线程／并发正式请求计数、固定旧模板及三类深验；`:1583` 接入 main，W1 用例保留。
- `scripts/tests/test_batch8_repair_scale.py:66`：census 夹具增加 instructions；`:313-389`：probe/census 两类退避及组合故障、自包含并发／额度切换／恢复回归；`:393` 接入 main。

```text
$ git diff --numstat "$W4_BASE" -- scripts/solana/sqd_gap_repair.py scripts/tests/test_sqd_gap_repair.py scripts/tests/test_batch8_repair_scale.py
19  33  scripts/solana/sqd_gap_repair.py
81  12  scripts/tests/test_batch8_repair_scale.py
263  1  scripts/tests/test_sqd_gap_repair.py

$ git diff --stat "$W4_BASE" -- . ':!maintenance'
 scripts/solana/sqd_gap_repair.py          |  52
 scripts/tests/test_batch8_repair_scale.py |  93
 scripts/tests/test_sqd_gap_repair.py      | 264
 3 files changed, 363 insertions(+), 46 deletions(-)

$ git diff --check
（空，exit 0）
```

## 测试结果

每个生产施工点修改后均立即完成对应检查：查询字段／键顺序；单请求及 Helius 前拒绝；删除引用与 β helper 保留；版本注释／语法。新增两份测试分别即时执行通过，再完成以下定向检查。

使用 `python3 -B` 与 `PYTHONDONTWRITEBYTECODE=1`；10 项均 exit 0。完整定向运行通过临时 `sitecustomize` 对 Python 进程及子进程禁止读取禁区、禁止 socket.connect；日志无禁读／网络拦截事件。两套受限测试仅标记允许子集通过，不宣称原始整套通过。

| 检查 | 状态 | 验收输出尾行 |
| --- | --- | --- |
| test_sqd_gap_repair.py | PASS，允许子集 | `PASS test_sqd_gap_repair allowed subset; 4 staging-dependent functions skipped` |
| test_batch8_repair_scale.py | PASS，允许子集＋自包含 W4 | `PASS test_batch8_repair_scale allowed subset and W4 self-contained cases` |
| test_batch3c_census_fields.py | PASS | `PASS batch3c census fields match the SQD contract` |
| test_sqd_coverage_probe.py | PASS | `PASS SQD coverage probe: 20/20 offline groups` |
| test_batch3_solana_producers.py | PASS | `PASS B3-G2: Solana slot/envelope/txn/timestamp producer guards` |
| test_repair_batch1.py | PASS | `PASS v6.41.0 batch1 steps 1-6 RV-07/RV-04/RV-17/F-03/F-01/A5v3/F-04` |
| test_reconcile_v4_receipt.py | PASS | `GREEN 32 verdict/exit_code/gate_pass 三元互洽` |
| invariant_scan.py | PASS | `PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=62, formal_entrypoints=61, exceptions=0` |
| test_batch4_invariant_guards.py | PASS | `PASS B4-G1: bare pool / labels / vertical slice / denominator injections` |
| test_exemption_guards.py | PASS | `PASS: exemption guards (EX-01 full-F-03)` |

上述为 stdout 的验收尾行；stderr 中故障注入产生的预期失败文案不表示套件失败。W4 新增用例还明确验证缺键/null/空数组、MISSING_BLOCK 无头正例和有头反例、HEALTHY β 的 253/255/256 原始指令长度、INHERITED_REFUTED 的 β 正例与 α／无头／非零拒绝。拒绝向量的 Helius 调用数为 0，失败 slot 无成功 ledger 行。

未运行，调度方本机补验：

- `test_sqd_gap_repair.py` 的 `functional_repair_regressions`、`blocks_cache_end_to_end`、`live_mock_transport_regression`、`batch3b_semantic_regressions`：会读取 `.staging_b3`，运行 main 时用临时 `patch.object` 跳过，未改测试文件中的原用例。
- `test_batch8_repair_scale.py` 原 main 中依赖 `staged_missing_transactions(20)` 的数据入口：未运行。原并发／热切换／跨 key 恢复函数已另用 W4 自包含交易运行通过，不能替代原禁读夹具验收。
- `run_all.py`、`docs_lint.py`、`changelog_lint.py`：未运行，待调度方验收。
- WR-a 登记后的真实 `validate_repair_bundle(deep=True)` 和 `resolve_formal_cache`：未运行，原因见下节。既有 W1／消费者测试使用的测试侧历史登记替身不构成该验收。

测试日志与临时受限运行器位于系统 tempfile：`/private/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/w4-checks-gnagilos/`。

## 新 producer 摘要与收官前置

```text
$ shasum -a 256 scripts/solana/sqd_gap_repair.py
15822564046e654b46300edcc26aeb51b397217ecce0fb555df0e891d98a1a33  scripts/solana/sqd_gap_repair.py
```

代码 commit：未创建。登记 commit：未创建。本轮没有修改 producer_history，也没有添加现役 sha 自动接受豁免。

调度方须在 W4 代码 commit 后按 `workorder_WR.md` 的 WR-a，以该 commit 对应脚本 sha 追加四协议 ACTIVE 登记；再用自包含夹具、未经替换的真实历史登记查询验证 `validate_repair_bundle(deep=True)` 与 `resolve_formal_cache`，并记录代码 commit、登记 commit、sha。当前直接深验通过不等于正式消费入口验收完成。

## 禁读披露

本轮未读取 `~/.codex/` 或 memories；未读取 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`、Desktop、Documents，以及指定目录以外的 maintenance。没有读取用户 API 密钥登记文件，没有外部 API 调用；额度切换测试使用临时虚构 key。源码中出现禁读路径字面量仅用于识别并跳过相关测试，没有打开对应数据。
