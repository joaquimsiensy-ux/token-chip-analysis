# 工单 W1（v2）：终态受控重开 + 快照登记解析 + 局限条目提取 + 标签库四址订正（7.0.4 → 7.1.0 第一批）repair-20260915-stage2-closeout

> v2（2026-09-16）：按 codex 只读复核 14 条（`scratchpad/cx_reply_w1.txt`，Fable 逐条亲核源码后）修订。改动点：行号订正五处；A1 补两处测试调用；A2 周期号与回执序号解耦、归档加 A4 快照副本、搬运回滚；A3 改为每轮绑定 `reopened_from_cycle`、回执完整性校验；A2 成功提示按真实状态机分支；B 续行规则收紧＋代码围栏＋适用范围声明；C 段命令改从仓库根、字段合并描述修正、**正式入库挪到 W2 验收之后**（标签 manifest 内容哈希进 scan 语义，入库会让 APU 0914 案的分布重验漂移，W2 验收要用它）；测试"先正例后负例"。

基线：`main = 764b60c`（7.0.4）。本单是已获用户审批的计划 `plan_v2_approved.md`（同目录）§2.5 / §2.6 / §2.7 的施工单；计划已经 codex 两轮只读复核。施工方按本单逐条执行，**先红后绿**，完工**不 commit**（Fable 验收后代 commit）。本批**不改版本号、不改 CHANGELOG、不改三册手册**（W3 统一做）。

## 0. 开工纪律

- 工作目录即本仓库物理路径 `/Users/uravvv/.claude/skills/token-chip-analysis`。开工先 `git status --short`，除本目录 `maintenance/repair-20260915-stage2-closeout/` 外须为空；`git rev-parse HEAD` 须为 764b60c 的后继（工单已 commit）。
- 行号旁附锚文本；若行号与锚文本不一致，**停工**写 `w1_done_attempt1_stopped.md` 汇报，不得自行猜改。
- **禁止**读取 `/Users/uravvv/.codex/` 下任何文件、`/Users/uravvv/.claude/skills/_archive/`、git tag `codex-frozen-20260915`。
- 离线完成，无网络调用；不 `git fetch`。**不改** `a4_gate.py` 的 `cmd_register`/`cmd_finalize`/`distribution_claim_source`；**不改** `holder_distribution_scan.py` 的 `validate_rounds_ledger`/`cmd_record_round`/`analyze`/`bin_scan`；**不改** `validate_labels.py`、`labels_resolver.py`、`add_labels.py`。
- 施工顺序 A → B → C → D。**C 段本批只做到 C1 写文件与 C2 的 `--dry`，不正式入库**（正式入库与 C3 验证在 W2 验收后由 Fable 另派）。每段先跑 RED 再改生产代码。RED 证据 `w1_red_evidence.txt` 每段必含：准确命令、退出码、输出原文、测试文件 sha256、被测生产文件 sha256。
- 全套 `run_all.py` 本机约 11 分钟：`nohup python3 scripts/tests/run_all.py > /tmp/run_all_w1.log 2>&1 &` 再等结果；禁止 `| tail`。
- 完工写 `w1_done.md`：改动文件清单、每段 RED→GREEN 命令与结果、run_all 结果行、与工单差异（若有）、遗留。

## 1. A 段：`scripts/report/holder_distribution_scan.py` —— 快照从登记解析 + `reopen-cycle`

### A1 `find_snapshot` 改为登记优先（`:187-197`，锚 `def find_snapshot(case_dir: Path, requested: str | None) -> tuple[Path, str]:` 至 `raise ValueError("找不到 A2 owner 快照 balances_final.json/holders_owners.json")`）

整段替换为（签名加 `stage`）：

```python
SNAPSHOT_CANDIDATES = ("data/balances_final.json", "data/holders_owners.json",
                       "balances_final.json", "holders_owners.json")


def find_snapshot(case_dir: Path, requested: str | None, stage: str) -> tuple[Path, str]:
    """owner 快照解析：显式指定 > final 取 initial scan 绑定 > initial 取 data_map 唯一登记候选。
    任何一路都不做"换一份文件再试"：登记/绑定不成立就停。data_map 唯一性与 sha 仍由
    verify_data_map 复核（显式指定也绕不过登记）。"""
    if requested:
        return safe_file(case_dir, requested, "快照"), requested
    if stage == "final":
        initial = load_json(safe_file(case_dir, "distribution_scan.json", "initial scan"))
        rel = ((initial.get("input_binding") or {}).get("snapshot") or {}).get("path")
        if not isinstance(rel, str) or not rel:
            raise ValueError("final 快照须从 initial scan 的 input_binding.snapshot 解析，绑定缺失或损坏")
        return safe_file(case_dir, rel, "initial 绑定快照"), rel
    obj = load_json(safe_file(case_dir, "data_map.json", "data_map"))
    registered = sorted({x.get("path") for x in _walk_entries(obj)
                         if x.get("path") in SNAPSHOT_CANDIDATES})
    if len(registered) != 1:
        raise ValueError("快照未在 data_map 唯一登记（候选名 "
                         f"{'/'.join(SNAPSHOT_CANDIDATES)}，登记到 {registered or '无'}）")
    return safe_file(case_dir, registered[0], "快照"), registered[0]
```

- `:625`（锚 `    snapshot, snapshot_rel = find_snapshot(case_dir, snapshot_arg)`）改为 `find_snapshot(case_dir, snapshot_arg, stage)`。
- `_walk_entries`（`:200`）定义在 `find_snapshot` 之后，Python 运行时解析没问题，不必移动；`load_json`（`:151`）同理。
- `verify_data_map`（`:211-220`）**不改**。
- **另两处直接调用必须同步**：`scripts/tests/test_batch15_three_ledgers_frozen.py:239`（锚 `default_path, default_rel = distribution.find_snapshot(root, None)`）改为 `find_snapshot(root, None, "initial")`；`:241`（锚 `explicit_path, shown_rel = distribution.find_snapshot(root, explicit_rel)`）改为 `find_snapshot(root, explicit_rel, "initial")`。**夹具勘误（v2.1，codex 停工记录核实）**：`test_batch11_frozen_bundle_binding.py:95-149` 的 `build_case`（batch15 `:30` 导入为 `build_frozen_case`）**不写** data_map；`:223-225` 那处登记属于 `test_n5_handoff_required_frozen_bundle`（`:214`），不在 N8 夹具链上且无 sha。因此**允许并要求**在 N8 用例 `build_unit_case(root)`（`:238`）之后补写真实登记：`{"files":[{"path":"data/holders_owners.json","sha256":<该文件 sha256>}]}` 到 `root/"data_map.json"`（用本文件已有 helper 或 `hashlib`/`json` 直接写）；`:242-244` 三条原断言逐字不变并须仍 PASS；生产侧登记优先规则不放宽。

### A2 新增子命令 `reopen-cycle`

用法：`holder_distribution_scan.py reopen-cycle --case-dir <案目录> --reason "<文>" [--dry-run]`。新增函数 `cmd_reopen_cycle(args)` 放在 `cmd_record_round`（`:1086`）之前、`validate_waiver`（`:1068`）之后。行为：

1. 台账 `distribution_rounds.json` 必须在场、`validate_rounds_ledger` 无错、`terminal` 非 None；否则 `print("BLOCK: ...")` 并 `return 2`（文案含"台账无 terminal，无需重开"或校验错误）。
2. 周期号 `N`：扫描 `data/stage2/` 下名字匹配 `^dist_cycle(\d+)` 的目录，取最大数字＋1（无则 1）；目标 `data/stage2/dist_cycle{N}/` 已存在即 BLOCK。（FORGGIE 现有 `dist_cycle1_v7j` 算作 1 → N=2；EGL1 有 `dist_cycle1/2/3_aborted` → N=4。）回执里的 `cycle` 就写这个 N；**回执不要求从 1 连续**（历史手工周期没有回执），只要求 `cycles[].cycle` 严格递增且每条都大于前一条。
3. 归档集合（**先全部检查、再一次性搬**，任一检查失败什么都不动）：
   - `distribution_rounds.json`；
   - `dist_rounds/` 整个目录（各轮 scan/图/解释文件都在其下）——用 `safe_file` 逐项核 `rounds[].final_scan_path`、`explanation_path`（非 None 时）都落在 `dist_rounds/` 内，否则 BLOCK（"台账引用了 dist_rounds/ 之外的文件，先手工归档"）；
   - `charts/final/holder_distribution_current.png`（= `terminal.final_chart_path`）：必须存在，且 `charts/final/` 下**只能有这一个文件**，否则 BLOCK（文案："charts/final 含其他文件——先归档 −3 图（reseal 第 0 步），reopen-cycle 只搬分布终态图"）。
   搬运用 `shutil.move`，目标保持相对结构：`data/stage2/dist_cycle{N}/distribution_rounds.json`、`.../dist_rounds/`、`.../charts/final/holder_distribution_current.png`。禁止任何 `rm`/`unlink`。
   - **A4 快照副本（copy，不 move）**：`a4_seal.json` 与其 `registry.path`（通常 `a4_claims.json`）复制到 `data/stage2/dist_cycle{N}/a4_snapshot/` 下同名。原因：旧解释件的重验（`distribution_explanation_check.py:82-95`）要读当时的 A4 seal 与 registry，新周期封新 rev 会覆盖活动路径；归档里留一份当时实物，历史周期才可复验。诚实边界：解释件 `evidence_refs` 指向的 sealed 文件（findings/facts/state 等）**不复制**（seal 内已记它们的 sha，可事后核对），回执 `note` 固定写这句。
   - **执行顺序**：①若案根已有 `distribution_reopen.json`，先 `validate_reopen_receipt` 通过（否则 BLOCK，什么都不动）；②全部前置检查；③按清单逐项 `shutil.move`，任一失败立即把已搬的按逆序搬回原位再 `return 1`（不是事务，但保证失败后活动路径完整）；④复制 A4 快照；⑤最后写回执（tmp + `os.replace`）。回执不在场而目标目录已在场 = 上次中断在 ③④ 之后 → BLOCK 提示手工核对。
4. 回执：案根 `distribution_reopen.json`（schema `distribution-reopen/v1`，`cycles: [...]` 追加，已存在则 `validate_reopen_receipt` 通过后追加）。每条 entry：
   ```
   {"cycle": N, "reason": <--reason 原文>, "ts_utc": utcnow(),
    "archived": [{"from": rel, "to": rel, "sha256": <搬前算，目录项按文件逐个列>}],
    "prior_terminal": <旧台账 terminal 对象原样>,
    "prior_ledger_sha256": <搬前 sha256_file(台账)>,
    "a4_seal_sha_at_reopen": <sha256_file(a4_seal.json)，缺文件则 None>}
   ```
   `archived` 里目录按其下每个文件各一条（`from`/`to` 为文件级相对路径），每条加 `"mode": "moved"|"copied"`（A4 快照副本为 copied），便于逐项重验；entry 另加 `"note"` 固定句（见上）。
5. `--dry-run`：只打印"将搬运 from → to"表与"将失效的下游件"（`a5_report_seal.json` 若在场、`a5_assembly_workorder.json` 的 `bindings.rounds`、终态图），不写不搬；退出 0。
6. 非 dry-run 成功：打印 `PASS: cycle {N} archived -> data/stage2/dist_cycle{N}/`，随后按真实状态机打印下一步（`a4_gate.py:282-284` 见 terminal 即拒 finalize；`cmd_record_round:1113-1119` NORMAL/LOW_SAMPLE 一 record 即终态）：
   - 「若 A4 claims 能与 initial scan 闭合：先 `a4_gate.py finalize` 封新 rev，再 `--stage final --round 1` → `record-round`（NORMAL/LOW_SAMPLE 直接终态）。」
   - 「若形态为 ABNORMAL 且需要 final scan 作 claim 来源：在当前 seal 下 `--stage final --round 1` → `record-round`（不带解释，得非终态 UNEXPLAINED）→ 补证据/复核 → `finalize` → `--stage final --round 2` 带 `--explanation` 终态。」
   - 「NORMAL/LOW_SAMPLE 形态**没有**"先建轮 1 再 finalize"的路径（轮 1 一 record 就终态，finalize 会被拒）。」
   退出 0。
7. `main`（`:1166` 锚 `    if argv and argv[0] in {"validate", "record-round"}:`）：集合加 `"reopen-cycle"`；该分支里 `--scan` 对 reopen-cycle 不适用——按子命令分别建参数（reopen-cycle 只要 `--case-dir`、`--reason`（required）、`--dry-run`）。

### A3 新周期首轮绑定 `reopened_from_cycle`

- 新增 `validate_reopen_receipt(case) -> dict`：读 `distribution_reopen.json`，校验 schema、`cycles` 非空且 `cycle` 严格递增；**最后一条**：`archived` 非空、`from` 集合与 `to` 集合各自无重复、必含 `from=="distribution_rounds.json"` 的 moved 条目、每项 `to` 用 `safe_file` 存在且 `sha256_file` 相等；用归档台账（那条 `to`）**重算** `prior_terminal`（其 `terminal` 对象）与 `prior_ledger_sha256`（其实物 sha），与回执自报值必须一致；`a4_seal_sha_at_reopen` 与 `a4_snapshot/a4_seal.json` 实物 sha 一致；返回**独立重建**的绑定对象 `{"cycle": n, "receipt": rel_entry(case, receipt_path), "prior_terminal": ..., "prior_ledger_sha256": ..., "a4_seal_sha_at_reopen": ...}`（字段取自回执最后一条）。任何不符 `raise ValueError`。
- `attach_round_binding`：在 `:910`（锚 `    scan["round"] = round_n`）之前、两个分支之外统一加：`scan["input_binding"]["reopened_from_cycle"] = validate_reopen_receipt(case) if (case / "distribution_reopen.json").is_file() else None`。**每轮 final scan 都带**（不只首轮），无回执时显式 `None`。原因（codex 推演）：只绑首轮时，删回执或改坏归档件后第二轮不会再核；"首轮"若按"文件不存在"定义，空台账在场时 producer 不加、validator 却拒，自相矛盾。
- `validate_scan`（`:1047-1050`，锚 `        if scan.get("stage") == "final":` … `            rebuilt["input_binding"]["round_binding"] = binding.get("round_binding")`）之后追加（每轮都核，不区分首轮）：
  ```python
            receipt_present = (case / "distribution_reopen.json").is_file()
            if receipt_present:
                rebuilt["input_binding"]["reopened_from_cycle"] = validate_reopen_receipt(case)
            elif binding.get("reopened_from_cycle") is not None:
                errors.append("scan 自报 reopened_from_cycle 但案根无 distribution_reopen.json")
            elif "reopened_from_cycle" in binding:
                rebuilt["input_binding"]["reopened_from_cycle"] = None
  ```
  存量案（无回执、旧轮次不带该键）：三个分支都不动 rebuilt → 与旧 scan 语义相同，兼容。有回执的案：每轮 scan 必须带且等于重建值。**注意**：旧周期已归档的轮次不会再被 `validate_scan` 重验（它们不在活动台账里），不要对归档轮调用完整 `validate_scan`（A4 换版后旧轮绑旧 seal 本就不可按当前输入重算，`:672-696`）。
  自报值**不复制**进 rebuilt，由 `semantic_payload` 比对抓不一致（`:706-727` 已把 `input_binding` 纳入语义比较，不改）。
- `cmd_record_round` 不改：无台账时自建（`:1101-1103`）且要求 round 1（`:1104-1105`）本就成立。

### A4 测试 `scripts/tests/test_reopen_cycle.py`（新文件）

风格沿 `test_distribution_gate.py`（`check()` 断言器，`main()` 汇总，失败 exit 1）；直接 `from test_distribution_gate import make_case, add_final_inputs, run_scan, smooth_balances, check, write_json, SCAN, sha`。每例独立 tempdir。用例：

1. `rejects_when_no_terminal`：initial + final round 1 未 record → `reopen-cycle` exit 2，文案含"terminal"。
2. `archives_and_allows_round1`：smooth 案 initial → final round 1 → record（NORMAL 终态，图落 `charts/final/`）→ `reopen-cycle --reason x` exit 0；断言：台账不存在、`dist_rounds/` 不存在、`charts/final/` 为空目录、`data/stage2/dist_cycle1/{distribution_rounds.json,dist_rounds/round_1/distribution_scan.json,charts/final/holder_distribution_current.png}` 在场且 sha 与回执 `archived` 一致、`distribution_reopen.json` 一条 cycle=1 且 `prior_terminal.round_n==1`；再 `final --round 1` exit 0 且 scan `input_binding.reopened_from_cycle.cycle==1`；`validate --expected-stage final` exit 0；`record-round` exit 0 → 新台账 round 1 终态、图重新物化。
3. `second_reopen_is_cycle2`：在 2 的基础上再 reopen → `dist_cycle2` 且回执两条。
4. `refuses_extra_final_chart`：终态后往 `charts/final/` 放一张 `x.png` → exit 2，台账与 `dist_rounds/` 原地未动。
5. `dry_run_moves_nothing`：`--dry-run` exit 0，文件系统与回执均不变。
6. `validator_rebuilds_reopen_binding`：对 2 中新周期 round 1 scan，**每个变异独立从基线副本出发、做完恢复**：(a) 篡改 `reopened_from_cycle.cycle=9` → validate 非 0；(b) 删除 `distribution_reopen.json` → validate 非 0；(c) 删掉 scan 中该字段（回执仍在）→ validate 非 0；(d) 改回执 `archived[0].sha256` → validate 非 0；(e) 改回执 `prior_ledger_sha256` → 非 0；(f) 回执 `archived` 清空 → 非 0；(g) 新周期第 2 轮 scan（若有）同样带字段且 (b) 对第 2 轮也拒。
7. `snapshot_prefers_registered`：`make_case` 后额外写一份**未登记**的 `data/balances_final.json`（旧固定顺序会先命中）→ initial scan exit 0 且 `input_binding.snapshot.path=="data/holders_owners.json"`。
8. `snapshot_two_registered_blocks`：data_map 再登记 `balances_final.json`（写同内容文件）→ initial exit 2，stderr 含"唯一登记"。
9. `final_snapshot_from_initial_binding_no_fallback`：正常 initial 后把 `distribution_scan.json` 的 `input_binding.snapshot.path` 改成不存在的路径 → `final --round 1` exit 2，stderr 含"initial"（不得回退到 data_map 自动选）。
10. `explicit_unregistered_snapshot_still_blocks`：先写一份**有效但未登记**的 `data/balances_final.json`（内容与登记快照相同），`--snapshot data/balances_final.json` → exit 2 且 stderr 含 data_map 登记错误（不能只因文件不存在而过）。
11. `reopen_then_finalize_then_round1_terminal`（集成，NORMAL 路径）：2 的状态 → `reopen-cycle` → `a4_gate.py finalize`（复用 `test_a4_gate` 的 finalize 调用方式或 `add_final_inputs` 的 seal 夹具，按现有夹具能做到的方式）→ `--stage final --round 1` → `record-round` 终态 NORMAL；断言新台账 rounds 长 1、terminal 在场、scan 带 `reopened_from_cycle.cycle==1`、`a5`/工单 bindings 未涉及。
12. `reopen_abnormal_round1_unexplained_then_round2`（集成，ABNORMAL 路径，复用 `test_distribution_gate.prepare_explanation_case:108`）：重开后 round 1 不带解释 → 非终态 UNEXPLAINED；此时 `a4_gate finalize` 不被 terminal 拒（`:282`）；round 2 带解释 → EXPLAINED 终态。若 `prepare_explanation_case` 夹具无法在重开后复用，写清原因跳过并在 done 标注。

RED：改 A1–A3 前跑本文件：1/2/3/5/6/11/12 因子命令不存在或字段缺失而红，7 因旧顺序命中未登记副本报 data_map 错而红。**负例的红不能靠 argparse 拒**：每个负例先断言同一夹具下正例（或命令本身）可用，再断言对应业务错误文案。红实证入 `w1_red_evidence.txt`。

既有 `test_distribution_gate.py` 全部 check **保持不变**并须仍 PASS（其夹具只登记 `data/holders_owners.json`，A1 兼容）。

## 2. B 段：`scripts/report/a4_gate.py` —— 子命令 `limits-extract`

### B1 新增 `cmd_limits_extract(a)`（放在 `cmd_finalize` 结束 `:484`（锚 `    return 0`）之后、`def main():`（`:487`）之前）

用法：`a4_gate.py limits-extract --case-dir <案目录> [--findings findings.md] [--out limits.json] [--heading <正则>]`；默认 `--heading '局限|观测边界'`。全部路径经 `safe_case_file(case_dir, rel, must_exist=...)`（`scripts/lib/case_paths.py:9`）围栏，`--out` 用 `must_exist=False`。

规则（十案实况：FORGGIE `## 10 观测边界与未决（…）` 用 `1. ` 编号（28 条）；EGL1（8）/APU（7）用 `- ` 项目符；COLLECT（11）从 `0. ` 起编；FUN/LIT/TAG 默认正则可得 3/5/6 条；**MELANIA/KAITO/BTW/MOG 没有独立"局限"标题，默认正则会明确拒绝（exit 2），这是设计内的拒绝而非静默丢条**——适用范围＝有独立局限/观测边界节的案；docstring 与 `--help` 写明这一点，不承诺换 `--heading` 就能收齐散落全稿的局限）：
1. 标题行 `^(#{2,6})\s+(.+?)\s*$`；标题文本 `re.search(heading_regex)` 命中数**必须恰为 1**，0 或 ≥2 → stderr 列出行号与标题并 exit 2（"用 --heading 精确指定"）。
2. 节体 = 该标题之后直到下一个级别 ≤ 该标题级别的标题（或文末）。
3. 条目起始行：`^(\d+)\.\s+(.*)$` 或 `^[-*]\s+(.*)$`（列首无缩进）。续行**只接受缩进行**（以空白开头的非空行）并入同条（单空格拼接，`strip()`）；列首无缩进且不是条目起始的非空行（如 `+ x`、`2) x`、`### 子标题`）→ exit 2（"局限节第 L 行既非条目也非缩进续行"），不静默并入；缩进行若本身匹配条目起始正则（缩进子列表）也当续行并入（原文保留，不拆条）。代码围栏：遇 ``` 行进入围栏，围栏内所有行（含 `#` 开头）不解析标题/条目，直到下一 ``` 行。空行结束当前条目；空行之后出现的非条目非空行 → exit 2（"局限节第 L 行无法归属到条目"）。首条之前的非空孤立文本 → exit 2。`--out` 解析后与 `--findings` 为同一文件 → exit 2（路径围栏不阻止覆盖输入）。
4. `id` 按**出现顺序** `LIM-01, LIM-02, …`（不用作者写的编号；COLLECT 从 0 起编时 `written_marker="0."` 仍是 `LIM-01`）。
5. 提取为空 → exit 2。
6. 输出 JSON（`indent=1, ensure_ascii=False`，**不含时间戳**，同输入两次运行字节相同）：
   ```
   {"schema": "a4-limits/v1",
    "findings": {"path": <rel>, "sha256": <sha256_file>},
    "heading": {"line": L, "level": n, "text": <标题文本>},
    "items": [{"id": "LIM-01", "index": 1, "written_marker": "1."|"-"|"*",
               "line": L, "text": <条目全文含续行>}, ...]}
   ```
   stdout 打印 `[limits-extract] N 条 → <out>`。
7. `main`（`:490-505`）：`sub.add_parser("limits-extract", help="从 findings 局限/观测边界节提取编号条目（供完整性路引用，禁硬编码文案）")` 加四个参数；`:505` 分派字典加 `"limits-extract": cmd_limits_extract`。模块 docstring（`:2-29`，用法段 `:19-26`）追加一行 `python3 a4_gate.py limits-extract --case-dir <案目录> [--findings findings.md] [--out limits.json] [--heading <正则>]`。

### B2 测试 `scripts/tests/test_a4_limits_extract.py`（新文件）

风格沿 `test_a4_gate.py`（黑盒 subprocess 调 CLI，`FAILS` 列表，exit 1）。tempdir 案目录，写 findings 后调用。用例：
1. 编号条目＋缩进续行＋加粗标记（模拟 FORGGIE）→ 3 条，`LIM-02.text` 含续行内容且无换行，`findings.sha256` 与实物一致；两次运行输出字节相同。
2. `- ` 项目符（模拟 EGL1）→ 正常提取，`written_marker=="-"`。
3. `0. ` 起编（模拟 COLLECT）→ 第一条 `id=="LIM-01"`、`written_marker=="0."`。
4. 标题多匹配（两个 `## ` 都含"局限"）→ exit 2，stderr 列两行号；`--heading '^10 '` 后 → exit 0。
5. 无匹配标题 → exit 2。
6. 节体为空 → exit 2。
7. 空行后有孤立段落 → exit 2 且提示行号。
8. `--out ../x.json` 越界 → 非 0；`--findings` 为符号链接 → 非 0。
9. 节体在文末（无后续标题）也能提取。

RED：改 B1 前跑本文件：正例 1/2/3/9 因 argparse `invalid choice` 红；负例 4–8 的断言写成"先断言正例可用（同夹具去掉致错因素后 exit 0），再断言 exit 2 且 stderr 含业务文案"，因此改前也红（正例不可用）。加用例 10：非缩进 `+ x` 行 → exit 2；用例 11：代码围栏内的 `## 局限` 与 `1. x` 不被当标题/条目；用例 12：`--out` 指向 findings 自身 → exit 2。

## 3. C 段：标签库四址订正（数据改动，不改代码）

### C1 补录文件
写 `maintenance/repair-20260915-stage2-closeout/curation_overrides_20260915_apu.csv`（**不要直接放进 `scripts/labels/sources/additions/`**——`add_labels.py:36-61`（锚 `def stage_archive(src):`），其中 `:41-42` 对已在 additions 目录的源文件直接返回、跳过 staging；归档由 add_labels 自己做）。表头 15 列同 `references/labels/labels-eth.csv:1`。四行（ETH，全部小写地址；`source=curation`；`added_date=verified_at=2026-09-15`；`risk_flags`/`source_snapshot_at`/`status`/`raw_labels` 留空）：

| address | name | category | tier | merge_policy | balance_policy | evidence |
|---|---|---|---|---|---|---|
| `0x0577eccc8fbe54b321d3bc8d4f1d09deb94d5a55` | Chainlink CCIP LockReleaseTokenPool（跨链锁仓池设施） | bridge | exclude | no_merge | exclude | Sourcify 全匹配 src/v0.8/ccip/pools/LockReleaseTokenPool.sol，部署块 21417044，构造参数首位＝APU 代币；APU-ETH-20260914 案 data/stage2/casebook_gate_log.md 异常①；此前全局库漏收 |
| `0x7a250d5630b4cf539739df2c5dacb4c659f2488d` | Uniswap V2 Router02（公共路由设施） | router | exclude | no_merge | exclude | Uniswap 官方 UniswapV2Router02 部署地址（Sourcify/Etherscan 合约名）；原库 Flashbots User/flashbots-user 系 Dune model=flashbots 误标（路由被 Flashbots 用户调用≠Flashbots 用户）；APU-ETH-20260914 案 gate log「硬边闭包提案裁决」修正 A |
| `0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad` | Uniswap Universal Router（公共路由设施；外部源误标 sandwich-bot） | router | exclude | no_merge | exclude | Sourcify 全匹配 UniversalRouter；APU-ETH-20260914 案 data/stage2/identity_cards.json code_kind.sourcify_name=UniversalRouter，入＝出 51.87%T、46,482 tx 同进同出＝公共路由无 MEV 关联；A4 完整性批评 F4＋C3 WEAKENED |
| `0x66a9893cc07d91d95644aedd05d03f95e1dba8af` | Uniswap Universal Router（公共路由设施；外部源误标 sandwich-bot） | router | exclude | no_merge | exclude | Sourcify 全匹配 UniversalRouter（第二部署）；APU-ETH-20260914 案 data/stage2/identity_cards.json 同款 code_kind；原库 Sandwich Attacker/sandwich-bot 系外部源把路由合约当 MEV 操作者误标；与 0x3fc91a3a… 同族订正 |

策略值与 APU 案内 `data/labels_final_v3.jsonl` 的 Universal Router 行（identity/allow/count）**故意不同**：`validate_labels.py:126`（锚 `if cat in FACILITY_MUST_EXCLUDE and r.get('tier') == 'identity':`）硬拒设施类目配 identity，且全量重建也会改为 exclude；本单不改校验器。

### C2 试跑（本批只到 `--dry`）
从**仓库根**调用（不要 `cd scripts/labels/sources` 连跑两条——第二条 `cd` 会相对已进入的目录再解析而失败；脚本用 `_HERE` 绝对定位库与门禁，不依赖 cwd，`add_labels.py:19-29/187-191`）：
```bash
python3 scripts/labels/add_labels.py maintenance/repair-20260915-stage2-closeout/curation_overrides_20260915_apu.csv --dry
```
预期摘要：3 行"分类覆盖"（三条旧记录在 `labels-eth.csv:115182/133302/133580`）、1 行新增（CCIP 池）。合并行为（`add_labels.py:150-164`）：`curation` 属高置信；非空 `name/category/tier/evidence/verified_at/added_date` 覆盖旧值；`merge_policy/balance_policy/source_snapshot_at/status` 仅在新值非空且旧行有该列时覆盖；`source` 追加（`+`）；`risk_flags` 取并集；**`raw_labels` 无合并逻辑保留旧值**；空输入不清旧 `source_snapshot_at/status`。
**正式入库（去掉 `--dry`）不在本批执行**：三闸 validate→benchmark→`labels_manifest --write`（`:187-196`）会改 `references/labels/manifest.json`，其内容哈希进分布扫描语义（`holder_distribution_scan.py:656/:715-718`），APU 0914 案的 scan 重验会随之漂移，而 W2 验收要在该案上跑完整 closeout。W2 验收后由 Fable 另派 W1-C 正式入库＋C3 验证。
### C3 验证（**正式入库那次**执行；本批不做，留作 W1-C 单的验收清单）
- `python3 scripts/labels/label_lookup.py --chain eth --json 0x0577eccc8fbe54b321d3bc8d4f1d09deb94d5a55 0x7a250d5630b4cf539739df2c5dacb4c659f2488d 0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad 0x66a9893cc07d91d95644aedd05d03f95e1dba8af`：四址命中，name/category/tier 为上表值，Router02 不再是 Flashbots User，两个 Universal Router 不再是 sandwich-bot。
- `grep -c` 四址在 `references/labels/labels-eth.csv` 各恰 1 行。
- `python3 scripts/tests/labels_manifest.py`（校验模式）exit 0。
- run_all 中 `test_review_labels.py`、`test_labels_resolver_guards.py`、`test_goldset_curated_rebuild.py`、`test_benchmark_labels.py`、`test_add_labels_rollback.py`、`../labels/check_manual_sync.py` 全 PASS。
- `roundtrip_check.py` 需先重建 `sources/out`（要重下载 dawsbot/brianleect 等大源，沙箱无网），且它另有缺表、决策字段退化、日期倒退检查（`roundtrip_check.py:109-145`）。验收分两段：**"W1-C 增量入库完成（三闸过、四址命中）"** 与 **"重建＋roundtrip 验收"**（Fable 本机有网时做）；两段都过才能写"标签修复已验收"。

## 4. D 段：测试登记

`scripts/tests/run_all.py:206`（锚 `SUITE += ['test_producer_registry_current.py']`）之后追加：
```python
# repair-20260915-stage2-closeout W1：分布台账终态受控重开+快照登记解析；a4_gate limits-extract。
SUITE += ['test_reopen_cycle.py', 'test_a4_limits_extract.py']
```

## 5. 完成标准
- A1–A3、B1 生产改动落地；A4、B2 新测试 GREEN；`test_distribution_gate.py`、`test_a4_gate.py`、`test_audit_release_gate.py`、`test_round4_a5_seal.py` 等既有测试不改断言且 PASS；run_all 全绿（分母 +2）。
- C 段：CSV 文件在场、`--dry` 摘要原文入 done（3 覆盖＋1 新增）；**不正式入库**。
- `w1_red_evidence.txt`、`w1_done.md` 在本目录；不 commit。
