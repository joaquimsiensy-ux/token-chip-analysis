# 批 16 盲审 R3 消化工单（1 条 P1：兜底越出本案）

- 基线：main `ce4e56c`（v6.53.2）。开工 `git status --short` 须为空（本工单已由调度方 commit 入库）。
- 盲审结论（codex review-mtfs5zg5 原文要点）：`camp_series_provenance.py:208-210` 新兜底把 `search_dirs` 每个
  base 都当 containment 根。序列文件放在案根的布局（`check_series_binding` 明确支持）下
  `load_series_with_sidecar` 传入 `[case_dir, case_dir.parent]`，登记路径写成 `sibling-case/data/reconcile_receipt.json`
  就能在 `case_dir.parent` 下命中**隔壁案子**的文件并通过 size/sha 三验——发布闸"只吃本案产物"的保证被打穿。
- 调度方核实的两条事实（决定修法）：①sidecar 自身登记 ref 一律只写文件名（:125 `return {"path": path.name, …}`），
  所以序列站点 :229-235（camps_spec / final_balances / inputs.*）**从不需要**登记路径兜底；②真正需要兜底的只有
  reconcile 收据 inputs（:631-635，v4 收据登记案根相对路径），而那里紧接着 :672 `resolve_formal_cache(expected_mint,
  Path(rr).parent.parent)` 已把"收据上两级"当案根。

## 修法（唯一案根，兜底只对 reconcile inputs）

1. `_resolve_ref(ref, label, search_dirs, *, case_root=None)`：
   - basename 两层段逐字不动；
   - **兜底仅在 `case_root is not None` 时执行**，且候选只有一个：`case_root / registered`；校验＝登记路径非绝对、无
     空段/`.`/`..`；从 `case_root.resolve()` 起逐段无 symlink；`cand.resolve()` 在 `case_root.resolve()` 之内；
     `is_file` 且 size+sha256 全等。不再遍历 `search_dirs` 当根。
   - `case_root is None` → 兜底不执行，报原"找不到"（文案保留"按登记路径解析亦未命中"仅在 case_root 给定时附加）。
2. 序列站点 :229-235：**不传 case_root**（sidecar 契约=文件名，恢复批 16 前语义）。
3. reconcile 站点 :631-635：传 `case_root=`，取值规则：
   - `registry_anchor_check(..., case_root=None)` 新增关键字参数；调用方给了就用（**发布闸 `audit_release_gate.py:1516`
     调用处传 `case_root=case_dir`**）；
   - 未给时：仅当收据所在目录名为 `data`（`Path(rr).parent.name == "data"`）才推导 `case_root = Path(rr).parent.parent`
     （与 :672 resolver 假设一致且排除"收据在案根→上两级是案外"的逃逸）；否则 `case_root=None`（不兜底）。
   - `state_from_facts.py:166` 调用处**不改**（走推导规则；ARC 收据在 data/ 下，推导即案根）。
4. 错误文案：找不到时若 case_root 给定，附"按登记路径 {path!r} 相对案根 {case_root} 解析亦未命中"。

## 测试（改 `scripts/tests/test_batch16_resolve_ref_case_path.py`，先红后绿）

- R2 红（改前）：案根布局＝`parent/caseA/`（series 放 caseA 根）与 `parent/caseB/data/x.json`；ref.path=`caseB/data/x.json`
  且 size/sha 与 caseB 实物一致 → 现行代码在 `search_dirs=[caseA, parent]` 下**命中 caseB**（红证据：返回路径落在 caseB）。
  改后：`case_root=caseA` → 拒（逃出案根/找不到），`case_root=None` → 拒。红证据追加到 `batch16_red_evidence.txt`（标 R3）。
- N7：`registry_anchor_check` 不传 case_root、收据在 `data/` → 推导案根，深层 soltx_meta 命中（沿用 N6 夹具）；
- N8：收据不在 `data/`（放案根）且不传 case_root → 不兜底、报找不到（不得命中父目录任何文件）；
- N9：显式 `case_root` 与推导值不同（指向案外）→ 以显式为准做 containment，仍拒；显式为本案根 → 命中；
- 既有 R1/N1–N6 断言保持（N1/N2/N3/N4 改为在 `case_root` 给定下验证）；N5 basename 优先零变化。
- `audit_release_gate` 调用处改动需一条回归：现有 `test_repair_batch_d.py` t_b1_b2 / 批 15 N6 完整案仍 `== []`（不改它们，跑绿即可）。

## 版本与文档

- 6.53.2 → **6.53.3**，五处同步；CHANGELOG 新条目 `## [6.53.3] - 2026-08-30 — 序列来源链登记路径兜底收窄为唯一案根（盲审 R3 P1）`，
  六栏；"盲审与验收"栏写"codex 盲审 R3 1 条 P1（兜底越出本案）已消化"。
- `batch16_done.md` 加"盲审 R3 消化"节（改动、红证据、N7–N9 原文、`git diff --stat`）。

## 白名单 / 禁改

- 白名单：`scripts/lib/camp_series_provenance.py`（`_resolve_ref`、`registry_anchor_check` 签名与 :631-635 传参、:229-235 不传）、
  `scripts/report/audit_release_gate.py`（**仅 :1516 `registry_anchor_check(` 调用处加 `case_root=case_dir`**，先 grep 亲核行号）、
  `scripts/tests/test_batch16_resolve_ref_case_path.py`、`VERSION`、`pyproject.toml`、`SKILL.md`、`CHANGELOG.md`、
  `maintenance/repair-20260823-sqd-gap/batch16_red_evidence.txt|batch16_done.md`。
- 禁改：`state_from_facts.py`、`solana_exact_validate.py`、`shared_release_receipt.py`、audit_release_gate 其他任何行、其他测试文件。
- 离线；不 commit；不写任何 key；行号不符/红造不出即停工汇报；沙箱 run_all 到 140/142（两个 loopback EPERM）如实报。
