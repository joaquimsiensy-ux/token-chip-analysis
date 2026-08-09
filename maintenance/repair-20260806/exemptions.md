# 第四类豁免台账(正式发布路径外·非 Robinhood)

本台账登记走「④正式发布路径外豁免」的通用工具(非 Robinhood 专属——RH 豁免在 robinhood-impact.md,该文件 §5 明确要求通用工具豁免另建本台账,不混入 RH 台账)。每条豁免必须四要素齐全:豁免依据(可机器复核)、影响面、自动失效条件、批准记录。任一自动失效条件触发,豁免即失效,该项回炉按正式缺陷修复。

## EX-01:full-F-03(multicall_balances.py 精度/失败处理缺陷)

- **缺陷本体**(ledger full-F-03,P1):`scripts/evm/multicall_balances.py:31-35` 允许单 call 失败;`:57-83` 固定 `/1e18` 不读 decimals 且失败转 `None`;`:85-115` 无 receipt 仍写 JSON 并打印 `[done]`。缺陷本身不修,按本豁免保持。
- **豁免依据(三要素,2026-08-09 Fable 复核)**:
  1. **调用图**:生产代码(scripts/ 排除 tests/)零 import、零子进程引用该文件;全库引用仅三个测试文件(test_batch2_capability_matrix.py / test_param_scripts.py / test_batch1_rpc_attestation.py,均为传输合规回归,不消费其业务输出)。
  2. **formal registry**:reconciliation_report.py 的 producer 白名单、invariant_scan.py 的 formal 分母、formal_capability_probes.py 的 evidence targets 均零引用。
  3. **能力矩阵**:test_batch2_capability_matrix.py 中该文件属 `attested_evm_chains()` 探索组(仅要求传输 attested),不在 `formal_reconciliation_chains`/`formal_evm_chains` formal 派生组。
- **影响面**:仅手动探索用途的余额快照可能精度失真(非 18 decimals 代币)或静默缺数(失败转 None)。不进入任何正式产物、receipt、data map、release。
- **自动失效条件**(任一触发豁免失效,由 `scripts/tests/test_exemption_guards.py` 机器看护):
  1. 任何生产 .py import multicall_balances;
  2. 任何生产 .py 以字符串路径引用它(子进程调度);
  3. 它进入 formal producer registry / evidence targets;
  4. 它的 `--chain` 选项改从 formal 派生函数取值。
- **批准记录**:Fable 复核三要素后批准,2026-08-09,登记于 Round B 盲审消化(blind-reviews/r9/45bf8f3/round-b-ledger-replay.md 判 full-F-03 INCONSISTENT 的整改产物——原缺此台账与批准记录,主表"已登记"措辞先行于事实,本次补全手续)。
