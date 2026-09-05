# 批 17 工单（紧急）：G8 身份闸链名别名归一（entity_identity_gate.validate_gate）

- 来源：ARC −2 主线（arc-9f 会话）2026-08-30 派单；调度方（Fable）已只读核实根因成立并经 codex 计划复核。
- 基线：本工单入库后的 main HEAD（开工 `git status --short` 须为空，否则停工汇报）。当前版本 6.53.4。
- 现象（大白话）：Solana 在 skill 里有规范键 `sol` 与别名 `solana`。G8 身份闸 `--chain` 只收 `sol`；编译器
  `state_from_facts.py:136` 把 analysis-state 顶层 chain 写成 `token.chain`＝`solana`（批 16 已确认 Solana 案必须是
  `solana`）。`validate_gate` 拿两个字符串裸比 → 报「chain 与 state 不绑定: gate='sol' state='solana'」，`--check` EXIT=1；
  `build_html.py:457-460` 共用同一 `validate_gate`。结果＝Solana 案凡绑定 state_from_facts 产物的 G8 结构上不可能过闸。
- 仓库先例：`audit_release_gate.normalize_chain`（:64-65）＝`chain_registry.resolve_alias`；`a4_gate.py:144-151` 先归一再比。

## 行号锚文本（开工先逐条核对，任一不符即停工汇报）

| 行 | 锚文本 |
|---|---|
| scripts/report/entity_identity_gate.py:46 | `from chain_registry import identity_chains` |
| :191 | `    state_chain = state.get('chain') or (state.get('token') or {}).get('chain')` |
| :192-193 | `    if state_chain != chain:` / `        errors.append(f'chain 与 state 不绑定: gate={chain!r} state={state_chain!r}')` |
| :299 | `def build(state_path, chain, snapshot_path=None, out_path=None, *,` |
| scripts/lib/chain_registry.py:197 | `def resolve_alias(value):` |
| scripts/tests/test_round4_identity_emitter.py:29 | `def run_solana(root):` |
| scripts/report/identity_snapshot_receipt.py:142 | `def emit_solana(mint,block,snapshot,meta,total,out):` |
| scripts/tests/run_all.py:192 | `SUITE += ['test_batch16_resolve_ref_case_path.py']` |

## 改动面

### 1. 生产（唯一改动点：`validate_gate` 两处）
- `:46` 改为 `from chain_registry import identity_chains, resolve_alias`（**不要**导入 audit_release_gate，避免循环依赖）。
- `:191-193` 改为双向归一比较，错误文案**保留原始值**：
  ```python
  state_chain = state.get('chain') or (state.get('token') or {}).get('chain')
  if resolve_alias(state_chain) != resolve_alias(chain):
      errors.append(f'chain 与 state 不绑定: gate={chain!r} state={state_chain!r}')
  ```
- **不改**：`:141`（snapshot receipt adapter 严格比较——正式 emitter 写的是规范链键）、`:173-175`（gate chain 仍限定 identity_chains）、
  `build()`（:299 起，不比 state chain）、`build_html.py`、`a4_gate.py`、`audit_release_gate.py`、`state_from_facts.py`。

### 2. 测试（先红后绿）：新建 `scripts/tests/test_batch17_identity_chain_alias.py`
- 登记 `run_all.py` :192 之后：`# Batch 17：G8 链名别名归一` + `SUITE += ['test_batch17_identity_chain_alias.py']`（142→143）。
- 形态照 test_batch16（`--r1` 只跑红例，main 返回码）。
- **夹具（必须真实 Solana 路线）**：`identity_gate_fixture.write_binding` 只会造 EVM（内部跑 replay_pass1 + emit_evm，收据 emitter 拒绝
  `sol`），**禁用**。改用 `test_round4_identity_emitter.run_solana(root)` 造 snapshot+meta，再 `identity_snapshot_receipt.emit_solana(mint,
  slot, snap, meta, total, out)` 产 identity 收据，然后 `entity_identity_gate.build(state_path, "sol", snapshot_path=…, out_path=…,
  total_supply_raw=…, snapshot_receipt_path=…)` 产 gate.json，把 flag 行填 resolution 后 `validate_gate(gate_path, state_path)`。
  若 build 路线夹具成本失控（>60 分钟），允许降级为"手工构造与 build 输出同形的 gate.json（snapshot_binding 用 emit_solana 收据真值）"，
  在 done 说明降级理由；但 R1 必须真实走到 :191-193（不许 patch 掉前置校验）。
- R1 红：state 顶层 `chain="solana"`（token.chain 同）、gate chain `sol` → 修前 errors **恰为**一条
  `chain 与 state 不绑定: gate='sol' state='solana'`（无其它错误，证明红只来自别名）；修后 `== []`。
  红证据（HEAD、命令、退出码、errors 原文）先于生产改动写入 `maintenance/repair-20260823-sqd-gap/batch17_red_evidence.txt`。
- N1：state `chain="sol"`（旧形态）仍 `== []`（零回退）。
- N2：state `chain="bsc"` + gate `sol` → errors 含 `chain 与 state 不绑定: gate='sol' state='bsc'`（错链不放行，且文案保留原始值）。
- N3：state 顶层缺 `chain`、只有 `token.chain="solana"` → `== []`（:191 回退取值路径）。
- N4：`build_html` 共用函数不另测，done 注明。
- 既有 `test_review_20260804_p201.py`、`test_round4_identity_emitter.py`、`test_repair_batch_d.py` 不改一字保持绿。

### 3. 版本与 CHANGELOG（6.53.5）
- 五处同步：`VERSION`、`pyproject.toml`、`SKILL.md` 版本注释、`CHANGELOG.md` 索引顶部新行、详情段
  `## [6.53.5] - 2026-08-30 — G8 身份闸链名别名归一（Solana sol/solana 裸比较拦死 state_from_facts 产物）`，六栏格式照 6.53.4。
  跑 `changelog_lint.py` 与 `test_version_consistency.py`。

### 4. 完工报告 `maintenance/repair-20260823-sqd-gap/batch17_done.md`
逐节对照、`git diff --stat`、红证据引用、N1–N3 原文、沙箱 run_all 结果（两个 loopback 纵切片 EPERM 如实报，本机全套由调度方复跑）。

## 边界与禁改
- **白名单**：`scripts/report/entity_identity_gate.py`（仅 :46 与 :191-193）、新建 `scripts/tests/test_batch17_identity_chain_alias.py`、
  `scripts/tests/run_all.py`（末尾追加）、`VERSION`、`pyproject.toml`、`SKILL.md`、`CHANGELOG.md`、
  `maintenance/repair-20260823-sqd-gap/batch17_red_evidence.txt|batch17_done.md`。
- **禁改**：其它任何生产文件、任何既有测试文件、任何案卷目录、`handoff_manifest.py`/provenance 路径（本批不许碰）。
- 离线；不 commit；不写任何 key；行号与描述不一致、红造不出、夹具失控——停工写 done 汇报。
