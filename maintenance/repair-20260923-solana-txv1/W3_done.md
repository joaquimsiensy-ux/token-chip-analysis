# W3 v2 完成记录

## 改动与基线

- 开工 `git status --short` 为空；分支为 `fix/solana-txv1`。
- `git merge-base --is-ancestor e44551a HEAD` 退出码为 0；`git diff --stat e44551a HEAD` 仅含 `maintenance/` 下 6 个文件。
- 工单引用的测试行 974、987 与生产校验行 1353、1529、1534 均与实况一致；生产文件位于 `scripts/lib/solana_exact_validate.py`。
- 唯一测试改动：`scripts/tests/test_sqd_gap_repair.py:987`，将旧 lambda 改为：

```python
lambda rows: rows[0]["adopted"].update(predecessor_plan_digest=wrong_digest, source="pending-" + wrong_digest)
```

- 复用第 974 行的 `wrong_digest`；预期 reason 仍为 `"adopted record invalid"` 子串；生产代码零改动。
- 测试 diff：`1 file changed, 1 insertion(+), 1 deletion(-)`；新增交付件为本文件。

## 隔离证据

核验脚本通过 Python 标准输入在内存中执行，未写入仓库。使用原 `adoption_regressions` 构造 fixture，在第 980 行执行前通过 `sys.settrace` 捕获局部变量并停止原函数；此前原第 950–951 行已确认该 gen 深验通过。随后从同一有效 case/gen 独立复制两份输入，分别施加旧、新向量；均按原循环重写 ledger 并更新 bundle 外层 `rpc_ledger.size`、`rpc_ledger.sha256`。

每份输入单独使用 `unittest.mock.patch.object(exact, "_plan_digest_from_generation", wraps=真实函数)`，独立重置 spy 后只调用一次 `validate_repair_bundle_deep`。fixture 构造、正向核验和独立 digest 重建均在 spy 计数区间外。

| 向量 | 单次 deep_check 内调用次数 | 第三个位置参数（按调用顺序） | reasons |
| --- | ---: | --- | --- |
| 旧：仅 `predecessor_plan_digest="0" * 16` | 0 | `[]` | `["RPC ledger adopted record invalid"]` |
| 新：`predecessor_plan_digest=wrong_digest`，`source="pending-" + wrong_digest` | 2 | 当前代 SHA → 前代 SHA，具体值见下 | `["RPC ledger adopted record invalid"]` |

1. 当前代 SHA：`3f89aab13054be76711d85d15a3e4f21d6113c35c905f55a8e60edb31ba8446b`
2. 前代 SHA：`25f04ff10bc494be977e4c5b3193c3a928c0764fa529d8d5a47563fe2a825e66`

新向量两次调用的第一个位置参数均断言等于更新外层 ledger size/hash 后的 bundle，第二个位置参数均断言等于有效 gen 的 coverage resolution；无关键字参数。两组结果均断言 `ok == False` 且 reasons 包含要求的子串。

独立重算并断言：

- `wrong_digest = 0000000000000000`
- 当前代 digest：`e0c872db24591e86`，等于原 plan digest。
- 真实前代 digest：`70b925d97e6adb38`，等于原 adopted record 中的前代 digest。
- `wrong_digest` 同时不等于上述两个真实 digest。

隔离核验退出码 0；尾行：`GREEN W3 isolated old=0 new=2; SHA order and digest inequalities verified`。
临时证据：`/private/tmp/W3-v2-isolation-x75ssnoo/evidence.json`（不入仓库）。

## 完整测试与纪律自报

- 离线运行：`MPLCONFIGDIR="$HOME/.matplotlib" PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_sqd_gap_repair.py`，退出码 0；隔离核验使用相同环境变量。
- 完整测试尾行：`GREEN 29c implemented validate_current_candidates 已实现`。
- 完整测试日志：`/private/tmp/W3_v2_test_sqd_gap_repair.log`（不入仓库）。
- `git diff --check` 通过；最终工作区差异仅为白名单测试文件和本交付件。
- 自报：未读取 `~/.codex`、`~/Documents`、`~/Desktop`；未使用网络；未执行 Git 写操作，未 add/commit；隔离脚本未入仓库。

待调度方 commit
