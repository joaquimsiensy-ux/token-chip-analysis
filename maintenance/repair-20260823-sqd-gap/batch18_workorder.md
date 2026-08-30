# 批 18 工单：四条裁决落地（②manifest 反绑产物豁免 / ③共享校验器接口转正 / ④版本规则文字 / ①R10-28 登记）→ 6.54.0

- 来源：用户 2026-08-30 裁决 1B/2A/3A/4A；实施计划已经 codex 只读复核并由用户批准（`~/.claude/plans/codex-cx-swirling-sifakis.md` 第六节为复核记录）。
- 基线：本工单入库后的 main HEAD（开工 `git status --short` 须为空，否则停工汇报）。当前版本 6.53.5（批 17 已入库）。
- 行号以下表锚文本为准，**开工先 `grep -n` 逐条核对**，任一不符即停工汇报（批 17 只改了 entity_identity_gate.py，本表其余文件行号不受影响）。

## 行号锚文本

| 行 | 锚文本 |
|---|---|
| scripts/report/handoff_manifest.py:81 | `    "flow_anomaly_report.json", ADJUDICATIONS_NAME, "provenance_ledger.json",` |
| :118-119 | `EXCLUDE_SUFFIXES = (…)` / `EXCLUDE_NAMES = {"config.json", MANIFEST_NAME}  # manifest 不含自身；…` |
| :223 / :232 / :237 | `    def add_path(rel):` / `    def discover(rel):` / `    def add_explicit(rel):` |
| :94-96 | distribution_scan「scan 不反绑 manifest；READY manifest 单向绑定 scan，避免 B-01 哈希循环」注释 |
| scripts/report/shared_release_receipt.py:333 | `def _bound_case_ref(root, ref, label, *, base=None):` |
| :1811 | `def validate_sources(root):` |
| :1816-1820 | EVM `validate_reconciliation_report(root, target, return_receipts=True)` / `else:` Solana `validate_reconciliation_report(root, return_receipts=True)` |
| :1857 | `def validate_bundle(root):` |
| :1872-1874 | `    except Exception as exc:` / `        errors.append(str(exc))` / `    return errors` |
| scripts/report/audit_release_gate.py:85-86 | `_RUN_DEEP_CACHE = None` / `_CACHE_MISS = object()` |
| :108 / :118 | `def _validate_reconciliation_report_once(case_dir: Path):` / `def _validate_shared_bundle_once(case_dir: Path):` |
| :345 / :549 / :643 | 三个 `_validate_reconciliation_report_once(case_dir)` 消费点 |
| :738 | `            from shared_release_receipt import _bound_case_ref` |
| CHANGELOG.md:4 | `- **skill 版本**：主=架构级重构；次=每次**分析复盘**迭代 +1；修=文档小修` |
| references/retrospective.md:139 | `- **skill 版本**（流程+方法，CHANGELOG 主条目）：主版本=架构级重构（工作流骨架变更）；次版本=每次**分析复盘**迭代 +1；修订号=文档小修/笔误。` |
| scripts/tests/test_repair_batch3_gates.py:557 | `    expected_ids = {f"R10-{number}" for number in range(1, 28)}` |
| maintenance/repair-20260813-sixlens/r10_ledger.md:69 | `…当前现役 = 27 − 15 = **12**。…` |
| scripts/report/holder_distribution_scan.py:672-695 | final 扫描 `common["handoff_manifest"] = {"run_id": manifest.get("run_id"), …}` 反绑段（只读参考，不改） |

## ② manifest 反绑产物豁免（handoff_manifest.py）

**大白话**：来源账本（provenance_ledger.json）自己记着 manifest 的 sha/run_id/scope；manifest 若再把账本收进去，两边互相记对方 → −2 期重跑 generate 必成死环（ARC 2026-08-30 实证，anomalies 第 22 条）。修法＝manifest 单向不收"反绑 manifest 的产物"；账本完整性由 entity_freeze / check-unseal / A5 单向绑定继续保障（与 :94-96 distribution_scan initial 先例同款）。

1. 新增模块级函数 `_reverse_bound_reason(case_dir, rel) -> str | None`（放在 `EXCLUDE_NAMES` 附近，带上面这段大白话注释）。判定**按规范相对路径＋内容，不按 basename**：
   - `rel == "provenance_ledger.json"`（案根精确路径）→ 返回 `"provenance_ledger 反绑 manifest 的 sha/run_id/scope"`；
   - `os.path.basename(rel) == "distribution_scan.json"` 且 `rel != "distribution_scan.json"`（非案根 initial）→ 读 JSON（读失败视为 None，不误杀）；`stage == "final"` 且 `(input_binding or {}).get("handoff_manifest")` 在场 → 返回 `"final 分布扫描反绑 manifest run_id/指纹"`；
   - 其它 → None。案根 initial `distribution_scan.json` **必需且允许**（REQUIRED_FOR_READY）。
2. `CONTRACT_FILES:81` 移除 `"provenance_ledger.json"`（注释一行说明去处）。
3. 三入口统一：
   - `add_path`（:223，discover/data_map 走这里）：`rel in seen` 判定之后、加入之前，`reason = _reverse_bound_reason(case_dir, rel)`；非 None → `print(f"[generate] 跳过反绑产物 {rel}: {reason}", file=sys.stderr)` 后 `return`（**不静默**）。
   - `add_explicit`（:237，`--include` 与 `--gate` 共用）：非 None → `print(f"[generate] 反绑产物禁止进入 manifest: {rel}: {reason}", file=sys.stderr)` 并 `sys.exit(2)`（或沿用该函数现有的错误退出形态，保证 `--gate` 也得到同一文案而不是"产物不存在"）。
4. **不改**：verify（:585-594 必备件重算）、freeze 前置 2/3、entity_freeze 写入、check-unseal、A5、`entity_source_trace.py`、`holder_distribution_scan.py`。
5. 文档：
   - `references/split-run.md` −2 段（grep "generate" 定位到 −2 期重跑 generate 的叙述处；找不到合适位置则在 −2 交接段末尾加）：「**首次 freeze 前**，−2 期可直接重跑 generate，随后重跑一次溯源（entity_source_trace）即收敛，不再需要移出账本；**freeze 之后**再 generate 会使 entity_freeze 记的 manifest sha/run_id 过期（check-unseal 拒），须连锁重跑 trace → freeze revision → 受影响的 A4 / final 分布扫描 / A5。」
   - `references/scan-schemas.md` manifest 段（:104-106 附近）登记"反绑产物规则"两类（案根 provenance_ledger.json；stage=final 且带 input_binding.handoff_manifest 的分布扫描），说明 discover/data_map 跳过并提示、--include/--gate 报错 exit 2。

## ③ 共享校验器接口转正（shared_release_receipt.py + audit_release_gate.py）

**大白话**：批 15 为了不改共享模块用了两个权宜：闸直接导入私有函数 `_bound_case_ref`；深验缓存靠"运行时临时把共享模块的函数换成带缓存的版本、用完换回"。现在给共享模块加正式入口，闸改用正式入口，**行为逐字不变**。

1. **公开别名**：在 `_bound_case_ref` 定义处改为 `def bound_case_ref(root, ref, label, *, base=None):`，补大白话 docstring（引用必须含 path/size/sha256 三字段；`base=` 相对基准；macOS alias/symlink 归一后必须在案根内；size 与 sha256 全等；返回 resolved Path），紧接其后 `_bound_case_ref = bound_case_ref  # 旧名保留：模块内 26 处调用与 test_reconcile_v4_receipt 不动`。闸 :738 改 `from shared_release_receipt import bound_case_ref`，:740 调用改名。
2. **深验见证对象**（防"调用者自称已深验"旁路）：共享模块新增
   ```python
   @dataclasses.dataclass(frozen=True)
   class DeepReconciliationWitness:
       root: Path            # 案根 resolve() 后
       report_sha256: str    # 深验当时 reconciliation_report.json 的 sha256
       target: dict
       receipts: dict

   def witness_reconciliation_report(root) -> DeepReconciliationWitness:
       """唯一合法产地：真跑一次 validate_reconciliation_report(root, return_receipts=True) 并记录案根与 wrapper 指纹。"""
       target, receipts = validate_reconciliation_report(root, return_receipts=True)   # 通过模块全局名查找（勿绑定局部别名）
       ...
   ```
   `validate_reconciliation_report` 必须以**模块全局名**调用（批 15 N9/N10 monkeypatch `shared.validate_reconciliation_report` 计数要能命中）。
3. **惰性 provider 参数**：`validate_bundle(root, *, reconciliation_provider=None)` → `validate_sources(root, *, reconciliation_provider=None)`。**仅 Solana 分支 :1819**：
   ```python
   else:
       if reconciliation_provider is not None:
           w = reconciliation_provider()
           if not isinstance(w, DeepReconciliationWitness) \
                   or w.root != Path(root).resolve() \
                   or w.report_sha256 != sha256(root / "reconciliation_report.json"):
               raise ValueError("reconciliation witness 无效/过期")
           recon_target, receipts = w.target, w.receipts
       else:
           recon_target, receipts = validate_reconciliation_report(root, return_receipts=True)
   ```
   EVM 分支 :1816（带 expected_target 的"不同源"校验）**不变仍真调**。默认 `None` → 行为逐字同现状。**provider 必须在 :1819 原位被调用**（深验异常仍落在 validate_bundle :1872 的 `except Exception` 内 → 闸 :1581 前缀"共享发布 receipt: …"不变；若在 validate_bundle 外预先调用，异常会被闸 :1583 收成"validator 失败: …"，N11 必红）。
4. **闸侧**：`_cached_reconciliation_report` 缓存值改为 witness（异常对象照旧缓存重抛）；`_validate_reconciliation_report_once(case_dir)` 改为 `lambda: witness_reconciliation_report(case_dir)` 并返回 witness；三个消费点 :345/:549/:643 改取 `w.target, w.receipts`（一行适配）；`_validate_shared_bundle_once` 改为
   `return shared_release_receipt.validate_bundle(case_dir, reconciliation_provider=lambda: _validate_reconciliation_report_once(case_dir))`，**删除**临时替换/`finally` 还原代码。
5. `handoff_manifest.py:44-50` 已绑定名导入**不动**；CHANGELOG 登记为"缓存/替换语义的治理边界"。

## ④ 版本规则文字（只改文档）

- `CHANGELOG.md:4` 改为：`- **skill 版本**：主=**不兼容**的工作流/schema/入口边界变更；次=**向后兼容**的新能力、新公开接口或持久化契约扩展（含分析复盘迭代）；修=既定契约内的修复、加固、回归补充与文档修订`
- `references/retrospective.md:139` 同义改写（保持同段其余条目与 :65/:75 的"次版本逢 0/5 整编"规则不动）。CHANGELOG 6.53.0 条目内"按书面规则升次版本"历史句不改。

## ① R10-28 登记（只改文档 + 守卫常量同步）

- `maintenance/repair-20260813-sixlens/r10_ledger.md` 第五节表格末尾追加一行（格式照 R10-19/R10-22：**不写【状态载体】**，"接受在案"写正文；守卫把无载体条目计为现役）：
  `| R10-28 | audit_release_gate._recon_owner_snapshot 静态 Solana 分支 owners 实物 basename-only 查找 | 2026-08-30 用户裁决接受在案（1B，更正风险描述后再次确认）：:756-785 丢弃登记路径目录段，搜索 gpa_rpc.path 父目录（绝对路径可指案外）/收据目录/data，命中判据仅 basename+is_file+非 symlink，无 size/sha256/containment，观察包登记的 owners sha256 未核；影响面仅静态 Solana 案 B-7（两态案走冻结分支 :730-755 已强绑定；EVM :701-717 已强绑定）；唯一防线=check_three_ledgers 逐址等值（挡内容不同，不挡配平替身）。修法线索：改用 shared_release_receipt.bound_case_ref 校验观察包登记 sha，与冻结分支同口径。来源：批 18 计划 @CX 复核 |`
- `scripts/tests/test_repair_batch3_gates.py:557` `range(1, 28)` → `range(1, 29)`（**只改这一常量**）。
- `r10_ledger.md:69` 之后追加一行 0830 落账说明（格式照 0816 那行），并把第六节"当前现役"声明改为 **13**（`27 − 15 + 1 = 13`，或按守卫 `ACTIVE_DECLARATION_RE` 认的格式写；先读 `test_repair_batch3_gates.py` 的正则确认）。
- CHANGELOG 6.54.0 条目末尾按先例写"R10-28 接受在案（用户 2026-08-30 裁决）"。

## 测试（先红后绿；红证据先于生产改动写入 `maintenance/repair-20260823-sqd-gap/batch18_red_evidence.txt`，含 HEAD/命令/退出码/原文）

### A. `scripts/tests/test_batch18_shared_bundle_witness.py`（登记 SUITE，143→144；形态照 test_batch16，`--r1` 只跑红例）
- R1 红：`validate_bundle(case_dir, reconciliation_provider=…)` 修前 `TypeError`；修后接受。
- N1：`shared.bound_case_ref is shared._bound_case_ref`；`inspect.getsource(audit_release_gate)` 不含 `_bound_case_ref`、不含 `shared_release_receipt.validate_reconciliation_report =`。
- N2：批 15 N6 完整动态案（复用 `test_batch15_three_ledgers_frozen` 的夹具/构造函数）上 monkeypatch 计数 `shared.validate_reconciliation_report`：`validate_bundle(root, reconciliation_provider=lambda: witness_reconciliation_report(root))` 计数 1 且 errors==[]；`validate_bundle(root)` 不注入亦计数 1。
- N3：EVM 案（`test_repair_batch_d` 或 `test_audit_release_gate` 的 EVM 夹具）注入 provider 不影响 :1816 真调（计数仍 1）。
- N4（伪造注入负例）：provider 返回 ①形状正确的裸 `(target, receipts)` 元组 ②另一案根产的 witness ③本案 witness 但随后篡改 `reconciliation_report.json` → 三种 errors 含"reconciliation witness 无效/过期"且不放行；④provider 抛异常 → errors 与不注入时深验抛同一异常逐字相同（闸层前缀"共享发布 receipt: "）。
- N11（语义锁定）：批 15 N6 案 `gate.run(profile="new-analysis")==[]`；篡改 `reconciliation_report.json` / `data/holders_owners.json` 后 `run()` 的 errors 与**改前实现**逐字相同——先在基线（改代码前）把两种篡改的 errors 原文记入红证据文件，改后断言全等，done 贴对照。
- 既有：批 15 N9 `calls==1`、N10 `calls==2` 不改断言跑绿；`test_r9_batch3_release_guards.py`、`test_reconcile_v4_receipt.py`、`test_repair_batch1.py`、`test_repair_batch_d.py` 不改一字。

### B. `scripts/tests/test_batch18_manifest_stage2_loop.py`（登记 SUITE，144→145；夹具照 `test_handoff_manifest.py` 的 make_provenance / generate / freeze 用法）
- R1 红（收敛测试；两次 generate **显式 `--run-id A` / `--run-id B`**，避免同秒碰撞）：generate(A) → 写账本反绑 A → 案根留着账本再 generate(B) → 重写账本反绑 B → verify + freeze。修前：第二次 generate 把账本收进 manifest，账本重写后 sha 漂移 → verify/freeze 前置 0 拒（红证据贴原文）；修后：manifest 不含账本，verify 过、freeze exit 0、entity_freeze 记到账本 sha。
- N1：manifest artifacts 不含 `provenance_ledger.json`，status 仍 READY；stderr 含"跳过反绑产物"。
- N2：`--include provenance_ledger.json` → exit 2 含"反绑产物禁止进入 manifest"；`--gate x:PASS:0:provenance_ledger.json` → 同款 exit 2（不是"产物不存在"）。
- N3：账本被篡改后 freeze 仍拒（沿用 test_handoff_manifest :411/:698 手法）。
- N4：旧版形态 manifest（手工把账本写进 artifacts 且 sha 正确）verify 仍过；账本改动后 verify 拒。
- N5：data_map 索引一份 `dist_rounds/round_1/distribution_scan.json`（`stage:"final"` + `input_binding.handoff_manifest`）→ generate 跳过并提示；`--include` 它 → exit 2；案根 initial `distribution_scan.json` 照常收录且 READY。
- N6：data_map 索引一份 basename 同为 `distribution_scan.json` 但无 final 绑定的普通文件（如 `data/x/distribution_scan.json`）→ 照常收录。
- 既有 `test_handoff_manifest.py`、`test_repair_g1_handoff_containment.py`（不受影响、不改）、`test_repair_batch_d.py`、`test_lit_regression_f008.py` 不改一字跑绿。

### C. 文档/台账
- `changelog_lint.py`、`docs_lint.py --all`、`test_version_consistency.py`、`test_repair_batch3_gates.py`（R10 守卫：ID 集合、状态枚举、现役计数）全过。

## 版本与 CHANGELOG（6.54.0）
- 五处同步（VERSION / pyproject.toml / SKILL.md 注释 / CHANGELOG 索引 / 详情）。详情标题
  `## [6.54.0] - 2026-08-30 — manifest 反绑产物豁免、共享校验器接口转正、版本规则文字收紧、R10-28 登记（四条裁决）`，六栏。
  升次版本理由（写进"设计与实现"栏）：manifest 收录契约可见变化（向后兼容）＋共享校验器新增公开接口（`bound_case_ref`、`DeepReconciliationWitness`/`witness_reconciliation_report`、`reconciliation_provider=`）——按本版起生效的新规则属"向后兼容的新公开接口/持久化契约扩展"。
- 完工报告 `maintenance/repair-20260823-sqd-gap/batch18_done.md`：逐节对照、`git diff --stat`、红证据引用、N 系列原文、N11 改前/改后 errors 对照、沙箱 run_all（两个 loopback EPERM 如实报）。

## 白名单 / 禁改
- 白名单：`scripts/report/handoff_manifest.py`（仅 CONTRACT_FILES、新函数、add_path、add_explicit）、`scripts/report/shared_release_receipt.py`（仅 bound_case_ref 改名+别名、witness 类与构造函数、validate_sources/validate_bundle 签名与 :1819 分支）、`scripts/report/audit_release_gate.py`（仅 :85-134 缓存段、:345/:549/:643 一行适配、:738-741）、新建两个测试文件、`scripts/tests/run_all.py`（末尾追加两行）、`scripts/tests/test_repair_batch3_gates.py`（仅 :557 常量）、`maintenance/repair-20260813-sixlens/r10_ledger.md`、`references/split-run.md`、`references/scan-schemas.md`、`references/retrospective.md`、`CHANGELOG.md`、`VERSION`、`pyproject.toml`、`SKILL.md`、`maintenance/repair-20260823-sqd-gap/batch18_red_evidence.txt|batch18_done.md`。
- 禁改：`entity_source_trace.py`、`holder_distribution_scan.py`、`solana_exact_validate.py`、`state_from_facts.py`、`camp_series_provenance.py`、`entity_identity_gate.py`、任何既有测试文件的断言逻辑（`test_repair_batch3_gates.py:557` 除外）、任何案卷目录。
- 离线；不 commit；不写任何 key；行号与描述不一致、红造不出、夹具失控——停工写 done 汇报。
