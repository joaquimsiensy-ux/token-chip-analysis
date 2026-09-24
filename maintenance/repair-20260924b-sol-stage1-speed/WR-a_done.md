# WR-a 完成：repair 四协议 ACTIVE 已追加，正式入口待调度方验收

按 WR-a v2 完成登记与指定检查。注册表守卫仍有工单允许的 probe 两项 FAIL，不能记作整体 PASS；未触发工单停工条件。

- 施工 HEAD：`c3660b1f05398bd9a0015c353db399f6361c65ce`。
- 源码 commit：`59f88b84c9ab9eeb95c92a15e342d8cbe09925db`。
- 开工工作树干净；`git merge-base --is-ancestor <源码 commit> HEAD` 退出码 0。
- 登记 commit：待调度方提交；本次未 commit、push、stash、checkout、reset 或创建 worktree。
- 全程离线；未读取 `~/.codex/` 或 memories，未读取工单禁读路径；测试临时目录由系统 tempfile 创建。

写入前执行：

```sh
git show "59f88b84c9ab9eeb95c92a15e342d8cbe09925db:scripts/solana/sqd_gap_repair.py" | shasum -a 256
shasum -a 256 scripts/solana/sqd_gap_repair.py
```

Git 对象、工作树、工单填值三方均为：
`15822564046e654b46300edcc26aeb51b397217ecce0fb555df0e891d98a1a33`。

变更仅涉及两份白名单文件：

- `scripts/lib/producer_history.py`：在原第 283 行元组闭合前追加四条同构 ACTIVE 条目，`+32/-0`；全部 34 条既有条目及其余原文件字节保持不变。
- `maintenance/repair-20260924b-sol-stage1-speed/WR-a_done.md`：新增本报告，`+68/-0`（未跟踪新文件，单独计数）。
- reason 均为「9.2.0 α/β 候选修复状态探针并入 census 请求（W4）」；未新增 shared-map 或 WR-b 登记。
- `git diff --check` 通过。补充“仅追加”校验初次因临时脚本把边界换行多算一行而 AssertionError；修正临时脚本后通过，生产文件未因此调整。

指定测试均设置 `PYTHONDONTWRITEBYTECODE=1`，使用 `python3 -B`；除 repair 的内存跳过包装外，直接运行 `scripts/tests/` 下对应文件。

| 检查 | 退出码 | 实际尾行与判定 |
| --- | --- | --- |
| test_batch3_solana_producers.py | 0 | `PASS B3-G2: Solana slot/envelope/txn/timestamp producer guards` |
| test_sqd_gap_repair.py（跳过下列四函数） | 0 | `GREEN 29c implemented validate_current_candidates 已实现`；仅已运行部分通过 |
| test_sqd_coverage_probe.py | 0 | `PASS SQD coverage probe: 20/20 offline groups` |
| test_f03_sharedmap_reuse.py | 0 | `PASS F-03 shared-map reuse: 15/15 groups` |
| invariant_scan.py | 0 | `PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=62, formal_entrypoints=61, exceptions=0` |
| test_producer_registry_current.py | 1 | `producer registry: 2 FAIL`；符合本阶段预期，非整体 PASS |

注册表逐项判读：

| 新增 repair 协议 | 当前哈希检查 | 新增登记 Git 复现 |
| --- | --- | --- |
| sqd-solana-cache/v4 | ok | ok |
| sqd-solana-repair-bundle/v1 | ok | ok |
| sqd-solana-coverage-resolution/v1 | ok | ok |
| sqd-solana-repair-pointer/v1 | ok | ok |

全部 38 条登记的 Git 复现均为 ok；脚本集合、必要协议及其余当前哈希检查均为 ok。剩余失败仅为 `scripts/solana/sqd_coverage_probe.py` 当前哈希 `ab2371f5350f6eb2be38a32c72a0703c258c2ea760f59fcc7f7dacfbf6dcde86` 尚未登记：

1. `sqd-solana-coverage/v1`：FAIL，留待 WR-b。
2. `sqd-solana-coverage-pointer/v1`：FAIL，留待 WR-b。

repair 测试使用 `unittest.mock.patch.object` 在内存中跳过以下函数后调用原 `main()`，未修改测试文件；以下各项均为「未运行，调度方本机补验」：

- `functional_repair_regressions`：直接读取 `.staging_b3`。
- `blocks_cache_end_to_end`：直接读取 `.staging_b3`。
- `live_mock_transport_regression`：通过 `staged_missing_transactions` 读取 `.staging_b3`。
- `batch3b_semantic_regressions`：通过同一 helper 读取 `.staging_b3`，其内部 `adoption_regressions` 亦未运行。

W1 自包含用例与 W4 三组用例均执行并通过；W4 三条结果为：

```text
PASS W4 combined state/duplicate/missing/null/empty/raw counts/inherited vectors
PASS W4 formal per-slot single census/zero probe/single Helius workers=1,4
PASS W4 old/new/mixed evidence deep validation; old bytes/ledger preserved; no refetch
```

0.7 正式入口验收：未执行，待调度方登记 commit 后验收。需对全旧、全新、混合三类产物分别用未替换历史注册查询的真实模块执行 `validate_repair_bundle(deep=True)` 与 `resolve_formal_cache`，核对 repaired 类型、gid、binding 及 CURRENT 所选 edge/meta。上述单测通过不替代该项验收。
