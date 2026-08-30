# 批 15 工单：发布闸 B-7 三账对账源 + series cutoff 改冻结点投影（方案 A 同族第七/第八消费点）

- 裁决依据：延续用户 2026-08-26 方案 A（封账日对上即收，封账后差异不管）；本批计划经
  @CX codex 复核 + 用户 2026-08-30 批准（计划文件由调度方保管，本工单是自包含施工件）。
- 基线：本仓库 HEAD `d50b2f3` v6.53.0，工作树干净。**开工先 `git status --short` 必须为空，
  否则停工汇报。**
- 背景（大白话）：Solana 活链两态＝exact_reconcile 冻结块 < reconciliation_report
  wrapper 观察块（ARC：440368381 < 441940997）。批 10–14 已把六个"默认观察点＝冻结点"
  的消费点改成两态投影，中央选择器是 `shared_release_receipt.accounting_expected_target`
  （:1489–1504）＋ `validate_reconciliation_report(..., return_receipts=True)`（:1387–1486，
  冻结态分支 :1458–1485 已深验冻结 bundle 并证明 exact 收据 `inputs.holders_owners` 与冻结
  bundle owners 的 size+sha256 全等）。发布闸 `scripts/report/audit_release_gate.py` 里
  `check_formal_case_chain`（:284–311）已接这套投影。本批修同文件里**没接**的两处：
  1. `_recon_owner_snapshot`（:566–654）：三账 B-7 的对账源。Solana 分支只吃 `checks["supply"]`
     观察 bundle 的 owners、时点取 wrapper 观察块（:579）。冻结态下三账按冻结块建就被
     `check_three_ledgers` :710（时点）＋ :727–735（逐址等值）拒；按观察块建又与判级矛盾。
  2. `check_series_binding` 调用处（:1486–1489）：`release_target` 直接取 wrapper target，
     传到 :1384–1390 `registry_anchor_check(expected_cutoff_slot=…)`，而
     `scripts/lib/camp_series_provenance.py:699–702` 要求 `holders_snapshot_meta.target.as_of_block
     == cutoff`——冻结 meta 是冻结块，wrapper 是观察块，new-analysis 闸必炸。

## 行号锚文本（开工先逐条核对，任一不符即停工汇报，不要猜）

| 行 | 锚文本（原样） |
|---|---|
| audit_release_gate.py:285 | `    if isinstance(accounting, dict) and reconciliation_target is not None \` |
| :286 | `            and accounting.get("as_of_block") != reconciliation_block:` |
| :308 | `        except Exception:` |
| :311 | `            pass` |
| :566 | `def _recon_owner_snapshot(case_dir: Path, data: dict, chain, errors: list[str]):` |
| :567 | `    """B-7：取四查真正核过的那份 owner 余额映射与冻结时点，作三账 balance_source 的对账源。` |
| :572 | `    ——fail-loud，不静默降级为"跳过比对"。` |
| :624 | `            return None, as_of`（EVM 分支末尾） |
| :625 | `    # Solana：从 supply 收据（observation bundle）拿 holder_outputs.owners 实物` |
| :657 | `def check_three_ledgers(case_dir: Path, data: dict, errors: list[str], chain=None):` |
| :1103 | `SNAPSHOT_BINDING_BY_FAMILY = {` |
| :1127 | `def check_distribution_snapshot_binding(case_dir: Path, data: dict, chain, errors: list[str]):` |
| :1384 | `                expected_target = expected_target or {}` |
| :1389 | `                    expected_cutoff_slot=expected_target.get("as_of_block"),` |
| :1486 | `            release_target = ((data.get("reconciliation_report.json") or {})` |
| :1487 | `                              .get("target") or {})` |
| :1488 | `            check_series_binding(case_dir, state_obj, errors,` |
| :1489 | `                                 expected_target=release_target)` |
| shared_release_receipt.py:333 | `def _bound_case_ref(root, ref, label, *, base=None):` |
| :1387 | `def validate_reconciliation_report(root, expected_target=None, *, return_receipts=False):` |
| :1489 | `def accounting_expected_target(reconciliation_target, reconciliation_receipts):` |
| camp_series_provenance.py:700 | `        if snap_cutoff != cutoff or to > snap_cutoff:` |
| scripts/tests/run_all.py:183 | `SUITE += ['test_batch14_accounting_bundle_fallback.py']` |
| references/analyze-workflow.md:107 | `5. **当前持仓分布初判**：仅在 EF-3A 和 EF-3B 之后运行` 起的段 |
| references/split-run.md:53 | `  9. **当前持仓分布初判**：运行 \`holder_distribution_scan.py --stage initial\`…` |
| references/scan-schemas.md:378 | `分布扫描吃的那份 owner 快照，必须就是四查真正核过的那一份：…` |
| references/scan-schemas.md:1187 | `- exact 检查组合、inputs 案根哈希并调用独立深验。静态态（…）…冻结态（exact 早于 wrapper）则要求…` |
| CHANGELOG.md:13 | `- **6.53.0**（2026-08-27）持仓分布图升级为 matplotlib 双轴带标签图：…`（版本索引顶行） |
| CHANGELOG.md:76 | `## [6.53.0] - 2026-08-27 — 持仓分布图升级为 matplotlib 双轴带标签图` |
| pyproject.toml:15 | `version = "6.53.0"` |
| SKILL.md:23 | `<!-- skill-version-source: VERSION; skill-version: 6.53.0 -->` |
| VERSION:1 | `6.53.0` |

## 改动面

### 0. 先红（改任何生产代码之前）

- 先写新测试 `scripts/tests/test_batch15_three_ledgers_frozen.py`（见 §3），在**未改生产代码**的
  HEAD 上跑 `python3 scripts/tests/test_batch15_three_ledgers_frozen.py --r1`，把
  HEAD 哈希、命令、退出码、errors 原文与"恰好命中的断言"写进
  `maintenance/repair-20260823-sqd-gap/batch15_red_evidence.txt`。红证据的断言必须精确：
  R1 的 errors 里**只允许**出现 B-7 两类（"与四查冻结时点 … 不一致"＋"不等值"），不得夹杂
  缺件/其它错误——否则红证据无效，先修 fixture 再改代码。

### 1. audit_release_gate.py 新增共用助手（放在 `_recon_owner_snapshot` 之前）

`_frozen_consumer_target(case_dir, data, errors, label) -> tuple[dict|None, dict|None, dict|None]`
返回 `(expected_target, wrapper_target, receipts)`；语义与 :284–311 完全同款，但**失败要 append 错误**
（那里 `pass` 是因为下游唯一性检查兜底，这里没有）：

1. `accounting = data.get("accounting_mode.json")`、`recon = data.get("reconciliation_report.json")`；
   wrapper as_of = `recon["target"]["as_of_block"]`。若 `accounting.as_of_block == wrapper as_of`
   → 返回 `(None, None, None)` 表示"非两态，走原逻辑"，**不报错**。
2. 否则 `validate_reconciliation_report(case_dir, return_receipts=True)` →
   `expected = accounting_expected_target(target, receipts)`；任一异常 →
   `errors.append(f"{label}: accounting as_of_block={…!r} 与 wrapper {…!r} 不同，但冻结态深验未通过，无法确定对账时点: {exc}")`，返回 `(None, None, None)` 并让调用方**直接 return，不回落观察点**。
3. 自闭合校验：`canonical_target({"chain": accounting.chain, "token": accounting.token or accounting.mint,
   "as_of_block": accounting.as_of_block}) != expected` → append
   `f"{label}: accounting target 与中央选择器结果不一致"`，返回 `(None, None, None)`，调用方 return。
4. 返回 `(expected, canonical_target(target), receipts)`。

### 2a. `_recon_owner_snapshot` 冻结态分支（插入在 :624 之后、:625 之前）

- 调 §1 助手，label＝`"三账 balance_source 对账源"`。三元组为 None：若是"非两态"（accounting==wrapper）
  → 落回 :625 起原逻辑；若是报错路径（errors 已增长）→ `return None, None`。
- `expected["as_of_block"] < wrapper["as_of_block"]`（冻结态）：
  - `ref = receipts["exact_reconcile"]["inputs"]["holders_owners"]`；
  - `from shared_release_receipt import _bound_case_ref`；
    `frozen = _bound_case_ref(case_dir, ref, "三账 balance_source 冻结 exact holders_owners")`
    （与公共深验同一套规则：拒 `..`/文件 symlink/案外、接受案根内绝对路径、size+sha256 三验）；
    异常 → append `f"三账 balance_source 对账源: 冻结 exact holders_owners 实物不可用: {exc}"`，`return None, None`。
  - `owners = load_json(frozen, errors)`，非 dict → `return None, None`；
    转 `{str(k): int(str(v))}`，失败 append "…不是 owner->raw 映射" 后 `return None, None`；
  - 成功 `return (owners_map, expected["as_of_block"])`。
- `expected == wrapper`（非冻结态但走到这里，理论上被 §1 第 1 步拦）→ 落回原逻辑。
- **禁止**：basename 搜索、`regular_case_path`（它拒绝一切绝对路径，会收窄既有契约）。
- docstring :567–572 补一句："Solana 冻结态（exact 早于 wrapper）＝exact 收据 inputs.holders_owners
  实物＋冻结块；静态态＝observation bundle owners＋wrapper 块。"
- EVM 分支 :596–624 与静态段 :625–654 **逐字不动**（验收会 diff 这两段）。

### 2b. `check_series_binding` 的 `release_target`（:1486–1489）

- 改为：调 §1 助手，label＝`"发布期序列 cutoff 目标"`；非两态 → `release_target = wrapper`（原值，零变化）；
  冻结态 → `release_target = expected`（冻结）；报错路径 → **不调用** `check_series_binding`
  （错误已 append，避免以错误 target 再报一串噪音）。
- EVM/静态 Solana 行为逐字零变化。

### 2c. 文档（代码不改 holder_distribution_scan.py）

- `references/analyze-workflow.md:107` 段与 `references/split-run.md:53` 段：加"动态 Solana
  （exact 早于 wrapper）必须显式 `--snapshot data/observe_live/holders_owners.json`，因为
  `holder_distribution_scan.find_snapshot` 默认优先 `data/holders_owners.json`（冻结件），而发布闸
  分布绑定要求观察 owners"；给完整命令示例。
- `references/scan-schemas.md:378` 段末与 `:1187` 段末各补一句：分布扫描吃观察 owners；三账 B-7、
  series cutoff、accounting 等冻结账消费者吃 exact 收据 owners＋冻结块（同一中央选择器投影）。
- 文档改完跑 `python3 scripts/tests/docs_lint.py` 必须通过。

### 3. 测试 `scripts/tests/test_batch15_three_ledgers_frozen.py`（形态照 test_batch13_accounting_target.py，支持 `--r1`）

**第一层·单元红绿**——直接调 `gate.check_three_ledgers(root, data, errors, chain="sol")`，不跑 `gate.run`。
fixture：复用 `test_batch11_frozen_bundle_binding.build_case`（:95–149）＋其 `fake_check` patch 手法
（`shared.validate_reconciliation_check = fixture["fake_check"]`），加 `accounting_mode.json`
（as_of_block=冻结 500，chain/token 与 wrapper 一致）与 test_repair_batch_d 同形三账
（balances_snapshot / membership balance_source / position / economic）。
- R1：三账按冻结 500 绑冻结 owners → 修前 errors 恰含两类（时点不一致＋不等值）且无其它；修后 `errors == []`。
- N1：三账绑观察 501＋活 owners → 拒（时点＋不等值）。
- N2：篡改冻结 owners 实物内容（exact ref 不变）→ errors 含"冻结态深验未通过"，且无任何"不等值"（证明不回落）。
- N3：冻结 owners 文件换成指向活件的 symlink → 拒。
- N4a：真静态案（exact=wrapper=accounting=同一 slot，同一 owners）→ 通过（静态分支零变化）。
- N4b：动态案但 accounting.as_of_block 错填 wrapper 501 → 被 §1 第 3 步"accounting target 与中央选择器结果不一致"拒（不得称静态案）。
- N5：exact ref path 用案根内绝对路径（`str(root / "data/holders_owners.json")`）→ 通过；案外绝对路径 → 拒。
- N8（2c 配套）：动态 fixture 下 `holder_distribution_scan.find_snapshot`（或其等价入口）不带显式快照会选到 `data/holders_owners.json`（冻结件）；显式指定 observe_live 才是观察件。只断言选择结果，不改扫描器。

**第二层·完整动态集成**——`gate.run(root, report, profile="new-analysis") == []`。以
`test_repair_batch_d.build_solana_case`（:952–1233，当前静态）为基底造两态版：wrapper 及
balance/time/supply_truth 观察 slot；exact、accounting、三账、identity、series cutoff、
holders_snapshot_meta 冻结 slot；冻结 bundle 留冻结 owners；distribution initial/final 显式吃观察
owners；shared receipt / rounds / A4 / A5 绑定重签。
- N6：两态完整案修后 `== []`；修前红（至少含 series cutoff 不一致＋B-7 两类，红证据一并留）。
- N7：cutoff 被投成错值 → 拒。
- **止损条款**：两态化若涉及重签点 > 12 处，或本层施工超过 90 分钟仍未绿，**停下写进
  batch15_done.md 汇报**（列出已完成/卡在哪/预估），先交付第一层＋2a/2b/2c；不要硬冲。

**既有零变化**：`test_repair_batch_d.py`（t_b7 :795–831 / t_b1_b2）、`test_audit_release_gate.py`、
EVM 全套不改一字保持绿。

**SUITE 登记**：run_all.py :183 之后追加
`# Batch 15：发布闸 B-7 三账对账源＋series cutoff 冻结态投影（方案 A 第七/八消费点）。`
`SUITE += ['test_batch15_three_ledgers_frozen.py']`，140→141。

### 4. 版本与 CHANGELOG（6.53.1）

- 五处同步：`VERSION`、`pyproject.toml:15`、`SKILL.md:23`、`CHANGELOG.md:13` 索引顶部新增一行、
  `CHANGELOG.md:76` 之前新增 `## [6.53.1] - 2026-08-30 — 发布闸 B-7 三账对账源与 series cutoff 冻结态投影`，
  六栏格式照 6.53.0（出处与根因／设计与实现／消费面与防回流／测试／盲审与验收／成本-质量指标）。
  "盲审与验收"栏写"@CX 施工前复核＋codex 施工后盲审＋Fable 独立验收"，具体轮次由调度方验收后补。
- 写完跑 `python3 scripts/tests/changelog_lint.py` 与 `python3 scripts/tests/test_version_consistency.py`。

### 5. 完工报告 `maintenance/repair-20260823-sqd-gap/batch15_done.md`

- 逐条对照本工单各节写"做了/没做/为什么"；
- 附 `git diff --stat`；
- 附 as_of_block 消费点全扫核对结论（调度方已有初稿；你按实况复核，不同意处写出行号与理由）；
- 治理债登记：①`_bound_case_ref` 私有名被生产模块导入，建议下批加公开别名；②CHANGELOG 书面版本
  规则（修订号只用于文档小修）与批 10–15 实践矛盾；
- 最后本机跑 `python3 scripts/tests/run_all.py > /tmp/batch15_runall.txt 2>&1; echo rc=$?`，把
  最后 30 行与 rc 贴进报告（不走管道取退出码）。

## 边界与禁改面

- **白名单**（超出即违规）：`scripts/report/audit_release_gate.py`（仅 §1 新助手、§2a 插入段与
  docstring、§2b :1486–1489）、新建 `scripts/tests/test_batch15_three_ledgers_frozen.py`、
  `scripts/tests/run_all.py`（:183 后追加）、`references/analyze-workflow.md`、`references/split-run.md`、
  `references/scan-schemas.md`、`VERSION`、`pyproject.toml`、`SKILL.md`、`CHANGELOG.md`、
  `maintenance/repair-20260823-sqd-gap/batch15_red_evidence.txt`、`batch15_done.md`。
- **禁改**：`shared_release_receipt.py`、`check_three_ledgers` 本体（:657–842）、EVM 分支（:596–624）、
  静态段（:625–654）、`SNAPSHOT_BINDING_BY_FAMILY`、`check_distribution_snapshot_binding`、
  `holder_distribution_scan.py`、`camp_series_provenance.py`、批 10–14 已改面、任何既有测试文件。
- 离线完成（沙箱无外网）；不 commit（Fable 验收后代 commit）；ARC 案根等任何案卷目录一个字不动
  （也不要去读桌面/Documents 下的案卷，沙箱读不了且不需要）；不得把任何 API key 或
  `~/.claude/api-keys.md` 内容写进代码、测试、报告。
- 行号与描述不一致、fixture 造不出精确红、止损触发——三种情况都**停工写 done.md 汇报**，不要自行扩大改动面。
