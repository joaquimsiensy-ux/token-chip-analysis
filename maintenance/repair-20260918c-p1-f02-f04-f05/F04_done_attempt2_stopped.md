# 施工 F04：停工

工单 §0.8 指定必跑的 `test_repair_batch_a.py` 会启动 §0.2 禁读范围内的历史 maintenance 脚本，两条纪律无法同时满足。本次在修改生产代码和测试之前停工；没有因 HEAD 的具体 SHA 停工，也没有自行跳过测试、复制历史脚本或改写执行方案。

工作目录：`/Users/uravvv/.claude/skills/token-chip-analysis`。
实际分支：`main`。
开工 HEAD：`38a0519f3e731da1b61a12226029b82901ca6511`。

## 停工点及源码证据

仅查看了获准范围内的 `scripts/tests/test_repair_batch_a.py`，未打开或执行下述历史文件。

该测试的第 565–575 行包含：

```python
def test_f02_waiver_swap_integrity_counterexample():
    script = (ROOT / "maintenance/repair-20260813-sixlens/counterexamples"
              / "waiver_swap_integrity.py")
    completed = subprocess.run(
        [sys.executable, str(script)], cwd=ROOT, text=True,
        capture_output=True, check=False,
    )
    assert completed.returncode == 0, (completed.stdout, completed.stderr)
    # 变长替换命中 size 一项；等长替换（字节数分毫不差）只能由 sha256 拦下。
    assert "input tolerance_waiver size mismatch" in completed.stdout, completed.stdout
    assert "input tolerance_waiver hash mismatch" in completed.stdout, completed.stdout
```

第 1645 行将此函数列入 `main()` 的测试列表，随后逐项调用；不是未使用的代码。执行工单要求的原始测试命令，会让 Python 子进程读取并执行 `maintenance/repair-20260813-sixlens/counterexamples/waiver_swap_integrity.py`，位于本工单目录之外。

- §0.2：禁读本工单目录以外的全部历史 maintenance 目录，没有测试依赖豁免。
- §0.8：要求原始 `test_repair_batch_a.py` 全部 PASS。
- §0.3：此测试文件及上述历史脚本均不在修改白名单。
- 派工纪律要求发现工单与代码不符即停工，不得自行改方案。因此没有启动该测试，也没有继续 §2 的施工。

恢复施工前需由调度方消除这一冲突，例如明确测试运行时对该历史依赖的读取权限，或修订测试要求。本次未替调度方选择方案。

## §0.1 开工检查原始输出

```console
$ git rev-parse HEAD
38a0519f3e731da1b61a12226029b82901ca6511
```

退出码 0。

```console
$ git status --short
```

stdout 为空，退出码 0，满足基线要求。

```console
$ git diff --stat 8b041842 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md
```

stdout 为空，退出码 0，满足基线要求。

## 已完成的修改锚及 import 核实

各锚均以 `grep -n -F -- <anchor> <file>` 核实，恰好一处，行号及整行内容均一致：

| 文件 | 基线行 | 结果 |
|---|---:|---|
| `scripts/lib/net.py` | 298 | `_one` 原返回语句唯一，PASS |
| `scripts/lib/rpc_batch.py` | 26 | `import re` 已存在且唯一，PASS |
| `scripts/lib/rpc_batch.py` | 82 | `if r["ok"]:` 起锚唯一，PASS |
| `scripts/lib/rpc_batch.py` | 85 | `is_contract` 止锚唯一，PASS |
| `scripts/tests/test_batch1_rpc_attestation.py` | 5 | `import asyncio` 唯一，PASS |
| `scripts/tests/test_batch1_rpc_attestation.py` | 7 | `import importlib.util` 唯一，PASS |
| `scripts/tests/test_batch1_rpc_attestation.py` | 327 | `def main():` 唯一，PASS |
| `scripts/tests/test_batch1_rpc_attestation.py` | 334 | 既有测试调用锚唯一，PASS |

测试文件既有 `json`、`sys`、`tempfile`、`Path`、`mock` 导入已核实。没有插入新的 import、函数或调用。

## §1.4 消费者逐项核实

以下行号均为未修改的基线。共 11 处，`time_spotcheck.py` 的余额和收据分别计数。

| 消费者 | 既有失败分支 |
|---|---|
| `scripts/lib/evm_observation.py:62–64` | 非成功响应抛 `EvmObservationError`。 |
| `scripts/lib/supply_truth_gate.py:484–486` | 非成功响应抛 `ValueError`。 |
| `scripts/evm/accounting_gate.py:121–126` | 按错误内容分类为 `RpcSemanticError` 或 `RpcNetError`。 |
| `scripts/evm/verify_recon.py:264–265` | 非成功或无有效 result 时抛 `ValueError`，文案含“无有效 result”。 |
| `scripts/lib/time_spotcheck.py:483–485` | 余额失败计 `RPC_ERR`；528–546 行按 ERROR 返回 1。487 行仍将合法 null 余额当 0。 |
| `scripts/lib/time_spotcheck.py:501–503` | 收据失败或 null 计 `RPC_ERR`；528–546 行按 ERROR 返回 1。 |
| `scripts/evm/fetch_alchemy.py:153–176` | 进入既有错误重试路径，耗尽后 `sys.exit(2)`。 |
| `scripts/evm/scan_bloxroute_seg.py:73–98` | 失败结果不当作日志列表，重试后记录失败段。 |
| `scripts/evm/pierce_stake.py:95–103` | 重试后警告并返回 `[None] * len(addrs)`。 |
| `scripts/evm/multicall_balances.py:69–81` | 批次失败后各地址置 `None`。 |
| `scripts/evm/lp_positions.py:132–134` | 失败或 null 收据由 `parse_receipt` 返回空列表。 |

核实结果与工单 §1.4 一致；这些分支并非全部显式失败退出。消费者的 null 处理没有修改。

## 开工 invariant_scan

```console
$ python3 -B scripts/tests/invariant_scan.py
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0
```

退出码 0；开工扫描通过，无差异报错。没有修改任何 manifest。

## §1.1 文档字节数

仅按工单使用元数据，未读取文档内容：

```console
$ stat -f %z SKILL.md
8021
$ find references -name '*.md' -print0 | xargs -0 stat -f %z | awk '{s+=$1} END{print s}'
930076
$ stat -f %z commands-staging/*.md | awk '{s+=$1} END{print s}'
8798
```

三项均与工单相符。

## 施工、RED 和定向测试状态

- §2.1、§2.2、§2.3 均未修改；对应 `git diff` 为空。
- 尚未进入 RED 取证阶段；所有新场景均未执行，不宣称 RED 或 GREEN。
- §0.8 仅执行了开工要求的 `invariant_scan.py`，结果如上；其余 13 个定向测试均未运行，不宣称 PASS。
- 未生成 `F04_done.md` 或 `F04_red_evidence.txt`。
- 仅更新白名单内本停工报告。`net.py` 的握手、轮转、请求函数和重试常量均未改动；`rpc_batch.py` 的任何分支均未改动。
- 没有修改台账 Q5/Q6/Q13；既有三端点轮转限制未处理。
- 全程离线；未运行 `run_all.py`；未 commit、push、部署，未执行 stash、checkout、reset，未删除文件。

## 报告写入后的工作区核验

<!-- F04_FINAL_STATE_START -->
```console
$ git status --short
 M maintenance/repair-20260918c-p1-f02-f04-f05/F04_done_attempt1_stopped.md

$ git diff --stat
 .../F04_done_attempt1_stopped.md                   | 146 +++++++++++++++++----
 1 file changed, 118 insertions(+), 28 deletions(-)

$ git diff --check

$ git diff -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md
```

所有命令退出码均为 0；最后两条命令 stdout 为空。变更仅有本停工报告，没有未跟踪文件。
<!-- F04_FINAL_STATE_END -->

禁读披露：未读取 `~/.codex/`（包括 memories）、`archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md` 的内容、本工单目录之外的历史 maintenance 文件、`/Users/uravvv/Desktop` 或 `/Users/uravvv/Documents`。上述历史脚本路径仅从获准测试源码获知，未打开或执行。references 字节总数检查只访问了工单明确要求的元数据。
