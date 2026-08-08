# R9 批二施工进度：能力矩阵可执行化

## B2-G1：chain attestation 可执行适配器键

### RED

```text
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_r9_batch2_attestation_adapters.py
exit 1
ModuleNotFoundError: No module named 'attestation_adapters'
```

旧实现的等价攻击重放：将 `eth` / `sol` 的 `chain_attestation`
换成 `does-not-exist`，`fixture_missing_formal_capabilities()` 对两链均返回
`()`，即 `BUG_ACCEPTED=True`。

### GREEN

```text
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_r9_batch2_attestation_adapters.py
exit 0
PASS R9 B2-G1: attestation keys resolve to callable factories

PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_batch2_capability_matrix.py
exit 0
PASS B2-D: immutable release tier + capability closure + derived CLI choices

PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_r9_solana_attested_session.py
exit 0
PASS R9 SolanaAttestedSession: 6/6
```

结论：`evm-chain-id` 解析到 `net.attested_rpc_pool`，`solana-cluster`
解析到 `SolanaAttestedSession`；缺键、未知键、缺 module/attribute 或
非 callable target 都不得满足能力。在测试专用 R9 evidence 上下文中，
四链均先证明 ready，再逐链删键/换不存在 factory，对应链的
`formal_ready()` 均立即变为 false。

## B2-G2：六能力可执行化与 readiness 自然导出

### RED

```text
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_r9_batch2_executable_capabilities.py
exit 1
AssertionError: REQUIRED_FORMAL_CAPABILITIES != 六项可执行探针
```

旧实现此时 `formal_ready_chains()` 仍为 `{'eth','bsc','base','sol'}`，
`vertical_slice_verified=True` 是可直接照抄的布尔声明。

### GREEN

```text
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_r9_batch2_executable_capabilities.py
exit 0
PASS R9 B2-G2: six executable probes; only R9 vertical evidence missing

PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_chain_registry.py
exit 0
PASS: six executable probes drive release/identity consumers; R9 vertical evidence absent until batch 3; DEFAULT_RPC keys registered

PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_batch2_capability_matrix.py
exit 0
PASS B2-D: immutable release tier + capability closure + derived CLI choices

PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_batch2_registry_harness_hardening.py
exit 0
PASS B2F-G2: string-only readiness API + reversible immutable harness

PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/invariant_scan.py
exit 0
PASS invariant manifest: receipt_producers=49, receipt_consumers=53, transport_calls=58, atomic_writes=38, formal_entrypoints=58, exceptions=0
```

受影响的 `test_r7_findings.py`、`test_audit_release_gate.py`、
`test_handoff_manifest.py`（65 项）和 `test_round4_a5_seal.py` 均 exit 0。

结论：正式就绪严格由六探针导出：链身份会话、冻结目标、
会计/供应量、R9 纵切片证据、错链负测、失败产物门禁。批二中前三项与
后两项均解析到真实 callable；批三所属的 R9 纵切片 evidence registry
保持空。四条 formal-intent 链的唯一缺口均为
`vertical_slice_evidence`，`formal_ready_chains()==set()`，无手工禁用开关。

## B2-G3：Solana SQD 数据集适配器

### RED

```text
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_r9_batch2_solana_sqd_adapter.py
exit 1
ModuleNotFoundError: No module named 'solana_sqd_dataset'
```

### GREEN

```text
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_r9_batch2_solana_sqd_adapter.py
exit 0
PASS R9 B2-G3: SQD dataset scope fixed and Solana mainnet RPC anchored

PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_r9_solana_attested_session.py
exit 0
PASS R9 SolanaAttestedSession: 6/6
```

结论：数据集身份固定为 `solana-mainnet + mint + [from_slot,to_slot]`；
只接受真实 `SolanaAttestedSession`，错 genesis 时业务 `getSlot` 调用为 0，
且 RPC 锚定 slot 必须覆盖 SQD 区间。`rg` 确认适配器未被
`scripts/solana/` 或 `scripts/report/` 引用，本批未接数据消费 callsite。

## B2-G4：探索链降级保持与 SKILL 单口径

### RED

```text
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_chain_support_matrix.py
exit 1
AssertionError: frontmatter missing executable matrix phrase: 六项可执行能力
```

### GREEN

```text
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_chain_support_matrix.py
exit 0
PASS: formal-candidate matrix closes frontmatter + labels capability: ['base', 'bsc', 'eth', 'sol']; all await vertical slices; Robinhood/Arbitrum remain exploration

PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_batch2_robinhood_exploration.py
exit 0
PASS B2-E: RH exploration is blocked by READY/A4/A5/build/audit and exemption sentinel

PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_formal_chain_support.py
exit 0
PASS: Arbitrum collection/G8 capability retained; release/A4/A5/formal compile fail closed

PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/docs_lint.py --all
exit 0
PASS: 58 个文档，引用无断链、粗体配对完整（--all 全量模式）

wc -c SKILL.md
7707 SKILL.md
```

结论：SKILL frontmatter 明确四条 formal-intent 链的六探针口径，
批二后均因 R9 纵切片证据缺席而 not-ready；Robinhood 保留
`release_tier=exploration` 与 `evm_chain_id=None`，Arbitrum 保持探索档。
`SKILL.md` 为 7707B，未修改 VERSION 或 skill-version 注释。

## B2-G5：台账与全量收口

### RED（台账前态只读证据）

`ledger.md` 原 R9-05 行仅写“待批二/三 callsite+正式纵切片”，
R9-05 详情仍写“矩阵接入留批二/三”，未登记批二已完成的矩阵层；
`diff-finding-map.md` 无 `R9-B2-G1`～`R9-B2-G5` owner 行。

### GREEN

- `ledger.md` R9-05 最终结果：“批二矩阵层闭合，callsite 接入留批三；
  R9-05 尚未完全销账”。
- `diff-finding-map.md` 已登记 G1～G5 全部 owner，分组 SHA 留空待
  Fable 回填；当前未映射 hunk 自查计数=`0`。
- 边界扫描：`VERSION_UNCHANGED`；`SKILL.md=7707B`；
  `SolanaSqdDatasetAdapter` 未被 `scripts/solana/` / `scripts/report/` 引用。
- 生产矩阵实测：`formal_tier=['base','bsc','eth','sol']`，
  `formal_ready=[]`，四链唯一缺口均为 `('vertical_slice_evidence',)`。

### 全量 suite

沙箱内首跑：83/85 PASS；两个既有 loopback 纵切片因沙箱禁止
`bind(127.0.0.1)` 而 `PermissionError`，无代码断言失败。放行 loopback 后又暴露
旧 R8 测试假定生产四链 ready；已改为仅在测试专用、可恢复的真实
callable evidence 上下文中运行，不计入 R9 证据，退出后生产 readiness
仍为空。

```text
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_batch3_solana_vertical_slice.py
exit 0
PASS B3-SOL-E2E: real producer->runner->aggregator->READY->release

PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_batch3_evm_vertical_slice.py
exit 0
PASS B3-EVM-E2E: eth/bsc/base real slices; wrong chain has zero business RPC

PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py
exit 0
85/85 PASS
全部通过
```
