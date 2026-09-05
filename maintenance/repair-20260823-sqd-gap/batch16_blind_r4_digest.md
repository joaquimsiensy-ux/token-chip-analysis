# 批 16 盲审 R4 消化工单（1 条 P1：案根隔离未贯彻到全部解析/校验路径）

- 基线：main `057235c`（v6.53.3）。开工 `git status --short` 须为空（本工单已由调度方 commit 入库）。
- 盲审结论（codex review-mtfthihc 原文要点）：`case_root` 只约束了 `_resolve_ref` 的登记路径兜底段；
  ①basename 段仍先在 `receipt_dirs=[rr.parent, rr.parent.parent]` 命中即返回，序列/收据放案根时第二层＝案目录的
  **父目录**，父目录直系下同名同 sha 的输入会被接受；②`validate_reconcile_receipt_deep(rr, case_root=Path(rr).parent.parent)`
  （:593-594）与 `resolve_formal_cache(expected_mint, Path(rr).parent.parent)`（:679）根仍按收据位置推导，不用调用方给的案根；
  ③`load_series_with_sidecar` 按 `[series.parent, series.parent.parent]` 解析出的 `resolved` 各路径（含 `inputs.reconcile_receipt`
  本身）未做案根 containment，收据本身就可以来自父目录直系。
- 调度方核实：成立。比 R3 难利用（需把文件放在案目录父目录**直系**，非隔壁案子内），但"案根给了就必须贯彻到底"是同一条隔离保证。

## 修法（`registry_anchor_check` 内统一"有效案根"，None 时零变化）

1. 在 `registry_anchor_check` 开头（`dirs = […]` :510 之前）算 **有效案根** `effective_root`：
   - `case_root` 给定 → `Path(case_root).resolve()`；
   - 未给定且 `fmt == "sol-rows"` 且 `Path(rr).parent.name == "data"` → `Path(rr).parent.parent.resolve()`（即现 :662-664 规则前移，
     evm-dict 未给定时 → None）；否则 None。
   - 新增私有助手 `_within_root(path, root) -> bool`（`resolve()` 后等于 root 或 root 在 parents 中）。
2. `effective_root` 非 None 时，**先于任何读取/深验**：对 `resolved` 中每个路径（camps_spec / final_balances / inputs.*）做 containment，
   任一在案根外 → `SeriesProvenanceError(f"sidecar {key} 实物 {p} 位于案根 {effective_root} 之外，拒收")`。
3. `dirs`（:510，evm-dict 找 supply_truth.json）与 `receipt_dirs`（:661）在 `effective_root` 非 None 时过滤为只保留案根内目录
   （顺序不变；过滤后为空即报"案根内找不到"）。
4. 深验 :593-594 改 `case_root=effective_root if effective_root is not None else Path(rr).parent.parent`；
   resolver :679 同款。`reconcile_case_root` 变量改为直接用 `effective_root`（None 时兜底不执行，与 6.53.3 一致）。
5. `case_root is None` 且不可推导（evm-dict，或 sol-rows 收据不在 data/）→ 全部行为逐字与 6.53.3 相同。
   `state_from_facts.py` 不改：其收据在 data/ 下时推导根＝原 `rr.parent.parent`，深验/resolver 根值不变，只多出第 2 条 containment
   （序列与收据都在 data/ 时 search_dirs 都在案根内，零影响）。

## 测试（改 `scripts/tests/test_batch16_resolve_ref_case_path.py`，先红后绿）

- R3 红（改前）：`parent/caseA/` 序列与 sidecar 放 caseA 根；`inputs.reconcile_receipt` 实物放 `parent/reconcile_receipt.json`
  （sha/size 与登记一致）→ `load_series_with_sidecar` 解析到父目录文件；`registry_anchor_check(..., case_root=caseA)` 修前抛出的
  异常文案**不含**"位于案根"（被深验/resolver 等后续步骤以别的理由拦，或未拦）——红证据记录实际异常原文；修后第一条错误即
  "位于案根 … 之外"。
- R4 红（改前）：收据在 caseA 根、`inputs.holders_owners` 实物只在 `parent/` 直系（basename 同名同 sha）→ 修前 `_resolve_ref`
  经 `receipt_dirs` 命中父目录文件（可用 N7–N9 的夹具方式让前置步骤通过，或直接断言 `_resolve_ref(ref, label,
  [caseA, parent], case_root=caseA)` 返回父目录路径作为红证据）；修后 `receipt_dirs` 过滤 → "找不到"。
  ⚠ 若 `_resolve_ref` 层面修：允许在 `case_root` 给定时把 basename 段的 search_dirs 也过滤到案根内（与第 3 条等价，二选一，done 说明）。
- N10：`case_root=None`、收据不在 data/ → 行为与 6.53.3 全同（沿用 N8 断言）；N11：`case_root=None`、收据在 data/、序列在案根、
  某 `resolved` 输入实物在父目录直系 → 推导根后被 containment 拒；N12：EVM `evm-dict` + `case_root` 给定 + supply_truth.json
  只在父目录直系 → 拒（"案根内找不到"）；既有 R1/R2/N1–N9 断言不变。
- 红证据追加到 `batch16_red_evidence.txt`（标 R4，含 HEAD/命令/退出码/原文）。回归：`test_repair_batch_d.py`、批 15 N6、
  `test_sqd_consumer_v4.py`、`test_reconcile_v4_receipt.py` 不改一字跑绿。

## 版本与文档

- 6.53.3 → **6.53.4**，五处同步；CHANGELOG 新条目 `## [6.53.4] - 2026-08-30 — 序列来源链案根隔离贯彻到收据、输入、深验与 resolver（盲审 R4 P1）`，六栏；
  "盲审与验收"栏写"codex 盲审 R4 1 条 P1（案根未贯彻全路径）已消化"。
- `batch16_done.md` 加"盲审 R4 消化"节（改动、红证据、N10–N12 原文、`git diff --stat`）。

## 白名单 / 禁改

- 白名单：`scripts/lib/camp_series_provenance.py`（`registry_anchor_check` 与 `_resolve_ref`、新私有助手）、
  `scripts/tests/test_batch16_resolve_ref_case_path.py`、`VERSION`、`pyproject.toml`、`SKILL.md`、`CHANGELOG.md`、
  `maintenance/repair-20260823-sqd-gap/batch16_red_evidence.txt|batch16_done.md`。
- 禁改：`load_series_with_sidecar`、`audit_release_gate.py`、`state_from_facts.py`、`solana_exact_validate.py`、`sqd_cache_identity.py`、
  `shared_release_receipt.py`、其他测试文件。
- 离线；不 commit；不写任何 key；行号不符/红造不出即停工汇报；沙箱 run_all 到 140/142（两个 loopback EPERM）如实报。
