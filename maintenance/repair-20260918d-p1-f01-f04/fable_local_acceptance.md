# Fable 本机验收记录（repair-20260918d-p1-f01-f04）

> 由调度方（Fable）在本机执行，补 codex 只读沙箱跑不了的落盘测试；完整 stdout 见同目录 `fable_*.log`。环境统一 `export MPLCONFIGDIR=$HOME/.matplotlib`（macOS 27 字体枚举空的绕行，上轮台账 Q15）。日期均为 2026-09-18（本机时区）。

## 1. F04 定向测试（被验提交 de281c6，09-18 22:59，`fable_f04_local_tests.log`）
命令：`python3 -B scripts/tests/<t>` 逐个执行 `test_repair_batch_c.py`、`test_repair_batch_d.py`、`test_engine_equivalence.py`、`test_fault_injection.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py`、`invariant_scan.py`。结果 7/7 rc=0；尾行分别 `PASS: repair batch C (F-05+F-04+fixround1+fixround2) 263 checks`、`BATCH D 全部通过`、`PASS: 三引擎 gate/退出码 10 例 hypothesis 全等…`、`PASS: 故障注入 F0–F5…`、`PASS B4-G1…`、`PASS: exemption guards (EX-01 full-F-03)`、`PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0`。

## 2. F01 定向测试（被验提交 84e70e5，09-18 23:37，`fable_f01_local_tests.log`）
命令：同上逐个执行 `test_stage2_closeout.py`、`test_a4_gate.py`、`test_audit_release_gate.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py`、`invariant_scan.py`。结果 6/6 rc=0；尾行 `stage2_closeout: 30/30 PASS`、`a4_gate 契约测试全部通过（23 项）`、`PASS: audit_release_gate …十一类契约全过`、`PASS B4-G1…`、`PASS: exemption guards…`、`PASS invariant manifest: …exceptions=0`。

## 3. run_all 全套（被验提交 84e70e5，09-18 23:51 完成，`fable_run_all_84e70e5.log`）
命令：`cd <仓库根> && export MPLCONFIGDIR=$HOME/.matplotlib && nohup python3 -B scripts/tests/run_all.py > <log> 2>&1; echo RUNALL_EXIT=$?`。前置：`git -C /private/tmp/w3_acceptance checkout -q --detach 84e70e5`（验收 worktree 与被验提交同步；`test_stage2_reseal` 硬依赖），跑测期间零 commit。结果：PASS 计 151、FAIL 计 0，末三行 `test_stage2_reseal.py    stage2_reseal: 21/21 PASS` / `全部通过` / `RUNALL_EXIT=0`。验收 worktree 当前 HEAD 仍为 84e70e5（09-19 00:0x 复核）。268026c 及之后的提交仅改 `maintenance/`，scripts 与 84e70e5 无差（`git diff --stat 84e70e5 HEAD -- scripts` 为空）。

## 4. 九项守卫（被验提交 268026c，09-18 23:57）
命令：`python3 -B scripts/tests/<t>` 逐个执行。结果 9/9 rc=0；尾行：
- `changelog_lint.py`：`PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 79 条 + 归档 139 条`
- `docs_lint.py --all`：`PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）`
- `test_version_consistency.py`：`PASS: M-03 version metadata consistent at 9.0.0`
- `invariant_scan.py`：`PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0`
- `test_batch4_invariant_guards.py`：`PASS B4-G1: bare pool / labels / vertical slice / denominator injections`
- `test_exemption_guards.py`：`PASS: exemption guards (EX-01 full-F-03)`
- `test_g3_docs_guards.py`：`PASS: F-05 machine boundary`
- `casebook_lint.py`：`casebook lint 通过：6 册 38 条，ID 唯一、六字段齐全`
- `fixtures_lint.py`：`fixtures_lint PASS：pythia_anchors.json 结构完整（数值以文件为权威，回测后人工更新）`

## 5. 待补验
版本落地（工单 E）施工后：`test_version_consistency`（须 9.0.1）、`changelog_lint`（活跃 79→80）、`docs_lint --all`、`wc -c SKILL.md`＝8021，结果追加到本文件 §6。
