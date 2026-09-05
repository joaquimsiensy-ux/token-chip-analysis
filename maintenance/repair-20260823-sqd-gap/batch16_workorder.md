# 批 16 工单：camp_series_provenance._resolve_ref 增加"登记路径按案根解析"兜底（sqd_repair 修复缓存深层路径）

- 来源：ARC −2 主线（arc-9f 会话）2026-08-30 派单；调度方（Fable）已只读核实根因成立。
- 基线：以本工单入库后的 main HEAD 为准（开工先 `git status --short` 须为空，否则停工汇报）。
- 现象（大白话）：ARC 案跑 `state_from_facts.py … --series-source data/camp_share_series.json` 正式编译，
  1.5 小时后被 `SeriesProvenanceError: sidecar reconcile.inputs.soltx_meta（soltx-….repaired.meta.json）在序列目录与案根两层内都找不到` 拦死。
- 根因：`scripts/lib/camp_series_provenance.py:179-201 _resolve_ref` **只取 basename** 在 `search_dirs`
  （两处调用分别为 `[series_path.parent, series_path.parent.parent]` :226 与 `[Path(rr).parent, Path(rr).parent.parent]` :629）
  两层找实物；而 solana-reconcile/v4 收据登记的 `inputs.soltx_meta.path` 是
  `data/sqd_repair/<sha>/gen-<gid>/soltx-….repaired.meta.json`（data/ 下第三层），basename 搜索必然找不到。
  下游 :647 又要求 `resolver_meta_path.resolve() == meta_path.resolve()`，所以"往 data/ 复制同名副本"过不了；
  symlink 明文拒收。对照：深验器 `scripts/lib/solana_exact_validate.py:354 _safe_case_path` 解析同一批
  inputs 用的是**案根相对完整路径**（:375/:885），所以 −1 的收据能过深验、编译器却找不到——两处口径不一致。
  凡走 sqd_gap_repair 修复缓存的 Solana 案都会撞上，不只 ARC。

## 行号锚文本（开工先逐条核对，任一不符即停工汇报）

| 行 | 锚文本 |
|---|---|
| camp_series_provenance.py:179 | `def _resolve_ref(ref: dict, label: str, search_dirs) -> Path:` |
| :180 | `    """按 basename 在 series 目录与其父目录（案根）两层内找实物并三验。` |
| :187 | `    name = Path(str(ref["path"])).name` |
| :200-201 | `    raise SeriesProvenanceError(` / `        f"sidecar {label}（{name}）在序列目录与案根两层内都找不到")` |
| :226 | `    search_dirs = [series_path.parent, series_path.parent.parent]` |
| :229 / :232 / :235 | `_resolve_ref(sidecar["camps_spec"], …` / `_resolve_ref(sidecar["final_balances"], …` / `_resolve_ref(ref, f"inputs.{name}", search_dirs)` |
| :629 | `        receipt_dirs = [Path(rr).parent, Path(rr).parent.parent]` |
| :631 / :633 / :635 | `_resolve_ref(inputs.get("soltx_meta"), …` / `…("holders_owners"), …` / `…("holders_snapshot_meta"), …` |
| :647 | `        if resolver_meta_path.resolve() != meta_path.resolve():` |
| solana_exact_validate.py:354 | `def _safe_case_path(case_root, rel):` |

## 改动面

### 1. `_resolve_ref` 兜底（唯一生产改动点）

- 保持现有两层 basename 搜索逐字不动（含 symlink 拒收、size/sha256 三验、返回首个命中）。
- 两层都未命中后，**再**尝试"登记路径按案根解析"：对 `search_dirs` 中每个 base（顺序不变），
  `cand = Path(base) / ref["path"]`（登记的相对路径原样拼接，不取 basename），须同时满足：
  ①`ref["path"]` 非绝对、各段不含 `""`/`.`/`..`；②从 base 起**逐段**检查无 symlink（与 `_safe_case_path`
  同口径，不只查末端）；③`cand.resolve()` 落在 `Path(base).resolve()` 之内（containment）；
  ④`cand.is_file()` 且 size、sha256 与登记全等（任一不等即 raise，不再试下一个 base——与现有 basename
  段"命中即三验、不匹配即 raise"口径一致）。命中返回 `cand`。
- 全部失败后错误文案改为：`sidecar {label}（{name}）在序列目录与案根两层内按文件名找不到，按登记路径 {ref["path"]!r} 解析亦未命中`（保留原句前半段的关键词"找不到"，既有测试若按关键词断言不被破坏——先 grep 既有测试用的断言词再定稿）。
- docstring 补一句：登记路径兜底只接受案根内相对路径，sha256 仍是权威身份。
- **不改**调用点 :226/:229-235/:629/:631-635（search_dirs 已含案根，兜底自然覆盖）、:647 resolver 等值检查、
  `solana_exact_validate.py`。

### 2. 同族口径核查（只核、按实况报，不扩改动面）

- grep 全库其他"按 basename 在若干目录里找登记文件"的地方（关键词 `Path(str(ref["path"])).name`、`.name` +
  `is_file()` 组合），逐处给行号与结论：是否同样会被 sqd_repair 深层路径卡住。已知同族：`audit_release_gate.py`
  `_recon_owner_snapshot` 静态段（:700 附近 `name = Path(str(ref.get("path") or "")).name` 起的搜索）——那段是
  批 15 明令禁改的静态段，**只报不改**，写进 done 让调度方裁决。

### 3. 测试（先红后绿）

新文件 `scripts/tests/test_batch16_resolve_ref_case_path.py`，登记进 `scripts/tests/run_all.py` SUITE 末尾
（`# Batch 16：…` 注释 + `SUITE += […]`，计数 +1），形态照 test_batch13/15（`--r1` 只跑红例，main 返回码）。
- R1 红：临时案根 `data/sqd_repair/<sha>/gen-x/soltx-a.repaired.meta.json` 深层实物 + 收据/sidecar 登记该相对路径 →
  修前 `_resolve_ref(ref, "reconcile.inputs.soltx_meta", [案根/data, 案根])` 抛"找不到"；修后返回该深层路径。
  红证据（HEAD、命令、退出码、异常原文）先于生产改动写入 `maintenance/repair-20260823-sqd-gap/batch16_red_evidence.txt`。
- N1：登记路径含 `..`（`data/../outside.json`）→ 拒；N2：登记路径为绝对路径 → 拒（不走兜底）；
  N3：路径链中间目录是 symlink（`data/sqd_repair -> 案外目录`）→ 拒；N4：深层实物 size 或 sha256 与登记不符 → 拒；
  N5：basename 两层命中的老形态（实物就在 data/ 或案根）行为零变化（含命中但 sha 不符即 raise，不落到兜底）；
  N6：端到端——用既有能过 `registry_anchor_check` 的最小 fixture（看 test_repair_batch_d / test_reconcile_v4_receipt
  的 solana 序列夹具怎么造）把 soltx_meta 实物挪到 `data/sqd_repair/<sha>/gen-x/` 并同步 resolver 所需的正式缓存布局
  → `registry_anchor_check` PASS（证明 :647 等值与兜底路径一致）。若 N6 夹具成本过高（resolver 正式缓存布局复杂），
  允许降级为"monkeypatch `resolve_formal_cache` 返回该深层 meta 路径"并在 done 里说明降级理由。
- 既有测试零变化：`test_a4_gate.py`、`test_lit_regression_f007.py`、`test_reconcile_v4_receipt.py`、
  `test_repair_batch_c.py`、`test_repair_batch_d.py`、`test_review_20260804_p105.py`、`test_sqd_consumer_v4.py`
  不改一字保持绿。

### 4. 版本与 CHANGELOG（6.53.2）

- 五处同步：`VERSION`、`pyproject.toml`、`SKILL.md` 版本注释、`CHANGELOG.md` 版本索引顶部新行、详情段
  `## [6.53.2] - 2026-08-30 — 序列来源链登记路径按案根解析兜底（sqd_repair 修复缓存深层路径）`，六栏格式照 6.53.1。
  跑 `changelog_lint.py` 与 `test_version_consistency.py`。

### 5. 完工报告 `maintenance/repair-20260823-sqd-gap/batch16_done.md`

逐节对照、`git diff --stat`、同族口径核查表、红证据引用、沙箱 run_all 结果（两个 loopback 纵切片 EPERM 如实报，
本机全套由调度方复跑）。

## 边界与禁改

- **白名单**：`scripts/lib/camp_series_provenance.py`（仅 `_resolve_ref` 函数体与 docstring）、新建
  `scripts/tests/test_batch16_resolve_ref_case_path.py`、`scripts/tests/run_all.py`（末尾追加）、`VERSION`、
  `pyproject.toml`、`SKILL.md`、`CHANGELOG.md`、`maintenance/repair-20260823-sqd-gap/batch16_red_evidence.txt|batch16_done.md`。
- **禁改**：`solana_exact_validate.py`、`audit_release_gate.py`、`shared_release_receipt.py`、`state_from_facts.py`、
  `_resolve_ref` 之外的任何函数、任何既有测试文件、任何案卷目录。
- 离线；不 commit；不写任何 key；行号与描述不一致、红造不出、夹具成本失控——三种情况都停工写 done 汇报。
