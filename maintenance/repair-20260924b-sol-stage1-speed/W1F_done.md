# W1F 完成：事实检查后补齐 recheck 缺失 slot，A/B 冲突回归通过

已按 W1F v2 完成。生产仅替换两行，增删合计 4 行；全部已运行的定向测试 exit 0。依赖 `.staging_b3` 的 4 个测试入口未运行，调度方本机补验。未触发停工条件。

**§0.1 开工检查**

工作目录：`/Users/uravvv/.claude/skills/token-chip-analysis`。

```text
W1F_BASE=65132abda8253cf34562f92f726d311d9a32b4f8
git status --short
（空）
git rev-parse HEAD
2a25873933e5c48bbb6a26f5b1fc2d57f3f4e7eb
git merge-base --is-ancestor "$W1F_BASE" HEAD
exit 0
git diff --quiet "$W1F_BASE" HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md assets
exit 0
```

**改动与锚点**

通读工单及目标函数后，改前执行以下两条命令，各恰命中 1 处：

```text
grep -n -F -x '            raise ValueError("empty recheck response facts invalid")' scripts/lib/solana_exact_validate.py
566:            raise ValueError("empty recheck response facts invalid")
grep -n -F -x '    return values' scripts/lib/solana_exact_validate.py
586:    return values
```

- `scripts/lib/solana_exact_validate.py:567`：空响应事实检查通过后，返回请求区间全 1 映射。
- `scripts/lib/solana_exact_validate.py:586`：非空完整响应全部事实检查通过后，为缺失 slot 补 1。
- 保留 `values = {}`、逐块赋值、首块绑定、完整性检查、非 recheck 早退及 `_validated_inherited` 原样；未改探针、schema、summary/verdict。
- `scripts/tests/test_sqd_coverage_probe.py:981`：新增夹具，复用 `_w1_reseal` 重绑 ledger、成功区间摘要、probe_id、CURRENT 引用及代目录。
- 同文件 `:1009`、`:1030`：新增冲突/正例/首块事实回归及 helper 解码回归；`:1331`、`:1332` 登记 main。

```text
git diff --numstat "$W1F_BASE" -- scripts/lib/solana_exact_validate.py scripts/tests/test_sqd_coverage_probe.py
2       2       scripts/lib/solana_exact_validate.py
76      0       scripts/tests/test_sqd_coverage_probe.py
git diff --check
exit 0
```

另新增本报告。映射规模随请求区间长度增长；本单未引入区间宽度上限。

**反例与正例证据**

修改生产代码前，使用与 W1F_BASE 一致的生产文件及新增 tempfile 夹具复现：

```text
W1F_BASE empty: ok=True reasons=[] state=INHERITED_REFUTED
W1F_BASE prefix: ok=True reasons=[] state=INHERITED_REFUTED
```

修复后 A（正确证明 + 空响应）和 B（正确证明 + 仅返回 501 的完整响应）均拒收，reasons 含完整理由 `inherited refuted recheck results conflict`。单条正确证明、两条一致证明均通过且 reasons 为空；新增用例均检查无引用、摘要、seq 或 probe_id 错误。

伪报 `returned_from=500` 的前缀空洞响应被 `inherited refuted recheck complete response facts invalid` 拒收；helper 单测中正确的 `returned_from=501` 返回 `{500: 1, 501: 2}`。该解码正例未作为正常生产者的 verified 发布产物。既有跨案边界、canary、部分继承、失败重试及 unverified 排除回归保留并通过。

**§0.7 测试尾行**

以下完整入口使用 `PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/<文件名>`，均 exit 0：

| 入口 | 尾行 |
| --- | --- |
| `test_sqd_coverage_probe.py` | `PASS SQD coverage probe: 20/20 offline groups` |
| `test_f03_sharedmap_reuse.py` | `PASS F-03 shared-map reuse: 15/15 groups` |
| `test_batch3_solana_producers.py` | `PASS B3-G2: Solana slot/envelope/txn/timestamp producer guards` |
| `test_reconcile_v4_receipt.py` | `GREEN 32 verdict/exit_code/gate_pass 三元互洽` |
| `invariant_scan.py` | `PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=62, formal_entrypoints=61, exceptions=0` |
| `test_batch4_invariant_guards.py` | `PASS B4-G1: bare pool / labels / vertical slice / denominator injections` |
| `test_exemption_guards.py` | `PASS: exemption guards (EX-01 full-F-03)` |

`test_sqd_gap_repair.py`：在临时 Python 进程中用 `unittest.mock.patch.object` 将以下 4 个入口替换为打印 SKIP，再执行原 main；未修改测试文件。其余路径（含 W1 自包含继承/beta/reconcile、机制检查、顺序语义与消费者回归）通过，exit 0。尾行：

```text
PASS SQD gap repair: safe main paths; 4 staging-dependent entrypoints skipped
```

以下入口直接或间接依赖 `.staging_b3`，均为「未运行，调度方本机补验」：

- `functional_repair_regressions`
- `blocks_cache_end_to_end`
- `live_mock_transport_regression`
- `batch3b_semantic_regressions`（含其内部调用的 adoption 回归）

**禁读与操作披露**

未读取 `~/.codex/` 或 memories；未读取 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`、Desktop、Documents。maintenance 下仅读取本工单目录的 `workorder_W1F.md` 及本报告。测试执行前检查源码中的禁读夹具依赖，并跳过上述入口；读取源码内的路径字符串未访问对应目录。

全程离线；仅修改白名单两个代码文件并新增本报告。测试使用系统 tempfile，禁写字节码缓存；未 commit、push、stash、checkout、reset 或创建 worktree，未执行批量删除操作。
