# 工单 W1：终态受控重开 + 快照登记解析 + 局限条目提取 + 标签库四址订正（7.0.4 → 7.1.0 第一批）repair-20260915-stage2-closeout

基线：`main = 764b60c`（7.0.4）。本单是已获用户审批的计划 `plan_v2_approved.md`（同目录）§2.5 / §2.6 / §2.7 的施工单；计划已经 codex 两轮只读复核。施工方按本单逐条执行，**先红后绿**，完工**不 commit**（Fable 验收后代 commit）。本批**不改版本号、不改 CHANGELOG、不改三册手册**（W3 统一做）。

## 0. 开工纪律

- 工作目录即本仓库物理路径 `/Users/uravvv/.claude/skills/token-chip-analysis`。开工先 `git status --short`，除本目录 `maintenance/repair-20260915-stage2-closeout/` 外须为空；`git rev-parse HEAD` 须为 764b60c 的后继（工单已 commit）。
- 行号旁附锚文本；若行号与锚文本不一致，**停工**写 `w1_done_attempt1_stopped.md` 汇报，不得自行猜改。
- **禁止**读取 `/Users/uravvv/.codex/` 下任何文件、`/Users/uravvv/.claude/skills/_archive/`、git tag `codex-frozen-20260915`。
- 离线完成，无网络调用；不 `git fetch`。**不改** `a4_gate.py` 的 `cmd_register`/`cmd_finalize`/`distribution_claim_source`；**不改** `holder_distribution_scan.py` 的 `validate_rounds_ledger`/`cmd_record_round`/`analyze`/`bin_scan`；**不改** `validate_labels.py`、`labels_resolver.py`、`add_labels.py`。
- 施工顺序 A → B → C → D。每段先跑 RED 再改生产代码。RED 证据 `w1_red_evidence.txt` 每段必含：准确命令、退出码、输出原文、测试文件 sha256、被测生产文件 sha256。
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

### A2 新增子命令 `reopen-cycle`

用法：`holder_distribution_scan.py reopen-cycle --case-dir <案目录> --reason "<文>" [--dry-run]`。新增函数 `cmd_reopen_cycle(args)` 放在 `cmd_record_round`（`:1086`）之前、`validate_waiver`（`:1068`）之后。行为：

1. 台账 `distribution_rounds.json` 必须在场、`validate_rounds_ledger` 无错、`terminal` 非 None；否则 `print("BLOCK: ...")` 并 `return 2`（文案含"台账无 terminal，无需重开"或校验错误）。
2. 周期号 `N`：扫描 `data/stage2/` 下名字匹配 `^dist_cycle(\d+)` 的目录，取最大数字＋1（无则 1）；目标 `data/stage2/dist_cycle{N}/` 已存在即 BLOCK。（FORGGIE 现有 `dist_cycle1_v7j` 须算作 1。）
3. 归档集合（**先全部检查、再一次性搬**，任一检查失败什么都不动）：
   - `distribution_rounds.json`；
   - `dist_rounds/` 整个目录（各轮 scan/图/解释文件都在其下）——用 `safe_file` 逐项核 `rounds[].final_scan_path`、`explanation_path`（非 None 时）都落在 `dist_rounds/` 内，否则 BLOCK（"台账引用了 dist_rounds/ 之外的文件，先手工归档"）；
   - `charts/final/holder_distribution_current.png`（= `terminal.final_chart_path`）：必须存在，且 `charts/final/` 下**只能有这一个文件**，否则 BLOCK（文案："charts/final 含其他文件——先归档 −3 图（reseal 第 0 步），reopen-cycle 只搬分布终态图"）。
   搬运用 `shutil.move`，目标保持相对结构：`data/stage2/dist_cycle{N}/distribution_rounds.json`、`.../dist_rounds/`、`.../charts/final/holder_distribution_current.png`。禁止任何 `rm`/`unlink`。
4. 回执：案根 `distribution_reopen.json`（schema `distribution-reopen/v1`，`cycles: [...]` 追加，已存在则 `validate_reopen_receipt` 通过后追加）。每条 entry：
   ```
   {"cycle": N, "reason": <--reason 原文>, "ts_utc": utcnow(),
    "archived": [{"from": rel, "to": rel, "sha256": <搬前算，目录项按文件逐个列>}],
    "prior_terminal": <旧台账 terminal 对象原样>,
    "prior_ledger_sha256": <搬前 sha256_file(台账)>,
    "a4_seal_sha_at_reopen": <sha256_file(a4_seal.json)，缺文件则 None>}
   ```
   `archived` 里目录按其下每个文件各一条（`from`/`to` 为文件级相对路径），便于逐项重验。
5. `--dry-run`：只打印"将搬运 from → to"表与"将失效的下游件"（`a5_report_seal.json` 若在场、`a5_assembly_workorder.json` 的 `bindings.rounds`、终态图），不写不搬；退出 0。
6. 非 dry-run 成功：打印 `PASS: cycle {N} archived -> data/stage2/dist_cycle{N}/；下一步：final --round 1（会自动绑定 reopened_from_cycle）`，退出 0。
7. `main`（`:1166` 锚 `    if argv and argv[0] in {"validate", "record-round"}:`）：集合加 `"reopen-cycle"`；该分支里 `--scan` 对 reopen-cycle 不适用——按子命令分别建参数（reopen-cycle 只要 `--case-dir`、`--reason`（required）、`--dry-run`）。

### A3 新周期首轮绑定 `reopened_from_cycle`

- 新增 `validate_reopen_receipt(case) -> dict`：读 `distribution_reopen.json`，校验 schema、`cycles` 非空且 `cycle` 从 1 连续递增、最后一条 `archived` 每项 `to` 用 `safe_file` 存在且 `sha256_file` 相等；返回**独立重建**的绑定对象 `{"cycle": n, "receipt": rel_entry(case, receipt_path), "prior_terminal": ..., "prior_ledger_sha256": ..., "a4_seal_sha_at_reopen": ...}`（字段取自回执最后一条）。任何不符 `raise ValueError`。
- `attach_round_binding` 无台账分支（`:903-909`，锚 `    else:` … `        ledger_entry = None`）之后、`:910`（锚 `    scan["round"] = round_n`）之前：若 `case / "distribution_reopen.json"` 在场且无台账（即本分支）→ `scan["input_binding"]["reopened_from_cycle"] = validate_reopen_receipt(case)`。有台账时不加（周期内后续轮靠哈希链）。
- `validate_scan`（`:1047-1050`，锚 `        if scan.get("stage") == "final":` … `            rebuilt["input_binding"]["round_binding"] = binding.get("round_binding")`）之后追加：
  ```python
            claimed = binding.get("reopened_from_cycle")
            receipt_present = (case / "distribution_reopen.json").is_file()
            if claimed is not None and not receipt_present:
                errors.append("scan 自报 reopened_from_cycle 但案根无 distribution_reopen.json")
            if claimed is None and receipt_present and scan.get("round") == 1:
                errors.append("重开后的首轮 final scan 必须绑定 reopened_from_cycle")
            if claimed is not None and receipt_present:
                rebuilt["input_binding"]["reopened_from_cycle"] = validate_reopen_receipt(case)
  ```
  自报值**不复制**进 rebuilt，由 `semantic_payload` 比对抓不一致（`:706-730` 已把 `input_binding` 纳入语义比较，不改）。
- `cmd_record_round` 不改：无台账时自建且要求 round 1（`:1101-1103`）本就成立。

### A4 测试 `scripts/tests/test_reopen_cycle.py`（新文件）

风格沿 `test_distribution_gate.py`（`check()` 断言器，`main()` 汇总，失败 exit 1）；直接 `from test_distribution_gate import make_case, add_final_inputs, run_scan, smooth_balances, check, write_json, SCAN, sha`。每例独立 tempdir。用例：

1. `rejects_when_no_terminal`：initial + final round 1 未 record → `reopen-cycle` exit 2，文案含"terminal"。
2. `archives_and_allows_round1`：smooth 案 initial → final round 1 → record（NORMAL 终态，图落 `charts/final/`）→ `reopen-cycle --reason x` exit 0；断言：台账不存在、`dist_rounds/` 不存在、`charts/final/` 为空目录、`data/stage2/dist_cycle1/{distribution_rounds.json,dist_rounds/round_1/distribution_scan.json,charts/final/holder_distribution_current.png}` 在场且 sha 与回执 `archived` 一致、`distribution_reopen.json` 一条 cycle=1 且 `prior_terminal.round_n==1`；再 `final --round 1` exit 0 且 scan `input_binding.reopened_from_cycle.cycle==1`；`validate --expected-stage final` exit 0；`record-round` exit 0 → 新台账 round 1 终态、图重新物化。
3. `second_reopen_is_cycle2`：在 2 的基础上再 reopen → `dist_cycle2` 且回执两条。
4. `refuses_extra_final_chart`：终态后往 `charts/final/` 放一张 `x.png` → exit 2，台账与 `dist_rounds/` 原地未动。
5. `dry_run_moves_nothing`：`--dry-run` exit 0，文件系统与回执均不变。
6. `validator_rebuilds_reopen_binding`：对 2 中新周期 round 1 scan：(a) 篡改 `reopened_from_cycle.cycle=9` → validate 非 0；(b) 删除 `distribution_reopen.json` → validate 非 0；(c) 删掉 scan 中该字段（回执仍在）→ validate 非 0；(d) 改回执 `archived[0].sha256` → validate 非 0。
7. `snapshot_prefers_registered`：`make_case` 后额外写一份**未登记**的 `data/balances_final.json`（旧固定顺序会先命中）→ initial scan exit 0 且 `input_binding.snapshot.path=="data/holders_owners.json"`。
8. `snapshot_two_registered_blocks`：data_map 再登记 `balances_final.json`（写同内容文件）→ initial exit 2，stderr 含"唯一登记"。
9. `final_snapshot_from_initial_binding_no_fallback`：正常 initial 后把 `distribution_scan.json` 的 `input_binding.snapshot.path` 改成不存在的路径 → `final --round 1` exit 2，stderr 含"initial"（不得回退到 data_map 自动选）。
10. `explicit_unregistered_snapshot_still_blocks`：`--snapshot data/balances_final.json`（未登记）→ exit 2（既有行为，作回归）。

RED：改 A1–A3 前跑本文件：1/2/3/5/6 因子命令不存在或字段缺失而红，7 因旧顺序命中未登记副本报 data_map 错而红。红实证入 `w1_red_evidence.txt`。

既有 `test_distribution_gate.py` 全部 check **保持不变**并须仍 PASS（其夹具只登记 `data/holders_owners.json`，A1 兼容）。

## 2. B 段：`scripts/report/a4_gate.py` —— 子命令 `limits-extract`

### B1 新增 `cmd_limits_extract(a)`（放在 `cmd_finalize` 结束 `:484`（锚 `    return 0`）之后、`def main():`（`:487`）之前）

用法：`a4_gate.py limits-extract --case-dir <案目录> [--findings findings.md] [--out limits.json] [--heading <正则>]`；默认 `--heading '局限|观测边界'`。全部路径经 `safe_case_file(case_dir, rel, must_exist=...)`（`scripts/lib/case_paths.py:9`）围栏，`--out` 用 `must_exist=False`。

规则（十案实况：FORGGIE `## 10 观测边界与未决（…）` 用 `1. ` 编号；EGL1/APU 用 `- ` 项目符；COLLECT 从 `0. ` 起编；条目可能有缩进续行）：
1. 标题行 `^(#{2,6})\s+(.+?)\s*$`；标题文本 `re.search(heading_regex)` 命中数**必须恰为 1**，0 或 ≥2 → stderr 列出行号与标题并 exit 2（"用 --heading 精确指定"）。
2. 节体 = 该标题之后直到下一个级别 ≤ 该标题级别的标题（或文末）。
3. 条目起始行：`^(\d+)\.\s+(.*)$` 或 `^[-*]\s+(.*)$`（列首无缩进）。续行：紧随条目之后、非空、且不是新条目起始的行（含缩进行）并入同条（以单空格拼接，`strip()`）。空行结束当前条目。空行之后出现的非条目非空行 → exit 2（"局限节第 L 行无法归属到条目"），不静默丢弃。
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
7. `main`（`:490-505`）：`sub.add_parser("limits-extract", help="从 findings 局限/观测边界节提取编号条目（供完整性路引用，禁硬编码文案）")` 加四个参数；`:505` 分派字典加 `"limits-extract": cmd_limits_extract`。模块 docstring（`:1-30`）用法段追加一行 `python3 a4_gate.py limits-extract --case-dir <案目录> [--findings findings.md] [--out limits.json] [--heading <正则>]`。

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

RED：改 B1 前跑本文件：argparse 报 `invalid choice: 'limits-extract'` 全红。

## 3. C 段：标签库四址订正（数据改动，不改代码）

### C1 补录文件
写 `maintenance/repair-20260915-stage2-closeout/curation_overrides_20260915_apu.csv`（**不要直接放进 `scripts/labels/sources/additions/`**——`add_labels.py:29-41`（锚 `def stage_archive(src):`）对已在 additions 目录的源文件跳过 staging，归档由 add_labels 自己做）。表头 15 列同 `references/labels/labels-eth.csv:1`。四行（ETH，全部小写地址；`source=curation`；`added_date=verified_at=2026-09-15`；`risk_flags`/`source_snapshot_at`/`status`/`raw_labels` 留空）：

| address | name | category | tier | merge_policy | balance_policy | evidence |
|---|---|---|---|---|---|---|
| `0x0577eccc8fbe54b321d3bc8d4f1d09deb94d5a55` | Chainlink CCIP LockReleaseTokenPool（跨链锁仓池设施） | bridge | exclude | no_merge | exclude | Sourcify 全匹配 src/v0.8/ccip/pools/LockReleaseTokenPool.sol，部署块 21417044，构造参数首位＝APU 代币；APU-ETH-20260914 案 data/stage2/casebook_gate_log.md 异常①；此前全局库漏收 |
| `0x7a250d5630b4cf539739df2c5dacb4c659f2488d` | Uniswap V2 Router02（公共路由设施） | router | exclude | no_merge | exclude | Uniswap 官方 UniswapV2Router02 部署地址（Sourcify/Etherscan 合约名）；原库 Flashbots User/flashbots-user 系 Dune model=flashbots 误标（路由被 Flashbots 用户调用≠Flashbots 用户）；APU-ETH-20260914 案 gate log「硬边闭包提案裁决」修正 A |
| `0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad` | Uniswap Universal Router（公共路由设施；外部源误标 sandwich-bot） | router | exclude | no_merge | exclude | Sourcify 全匹配 UniversalRouter；APU-ETH-20260914 案 data/stage2/identity_cards.json code_kind.sourcify_name=UniversalRouter，入＝出 51.87%T、46,482 tx 同进同出＝公共路由无 MEV 关联；A4 完整性批评 F4＋C3 WEAKENED |
| `0x66a9893cc07d91d95644aedd05d03f95e1dba8af` | 同上 | router | exclude | no_merge | exclude | 同上 |

策略值与 APU 案内 `data/labels_final_v3.jsonl` 的 Universal Router 行（identity/allow/count）**故意不同**：`validate_labels.py:126`（锚 `if cat in FACILITY_MUST_EXCLUDE and r.get('tier') == 'identity':`）硬拒设施类目配 identity，且全量重建也会改为 exclude；本单不改校验器。

### C2 入库
```bash
cd scripts/labels/sources && python3 ../add_labels.py ../../../maintenance/repair-20260915-stage2-closeout/curation_overrides_20260915_apu.csv --dry
cd scripts/labels/sources && python3 ../add_labels.py ../../../maintenance/repair-20260915-stage2-closeout/curation_overrides_20260915_apu.csv
```
先 `--dry` 看摘要（预期：3 行"分类覆盖"、1 行新增），再正式入库。add_labels 自带 validate→benchmark→labels_manifest --write 三闸与归档（`add_labels.py:188-194`）；成功后 `scripts/labels/sources/additions/curation_overrides_20260915_apu.csv` 应出现（归档副本，**永不删除**）。三闸任一 FAIL 即停工汇报，不得改校验器或数据凑过。

### C3 验证（全部结果原文入 `w1_done.md`）
- `python3 scripts/labels/label_lookup.py --chain eth --json 0x0577eccc8fbe54b321d3bc8d4f1d09deb94d5a55 0x7a250d5630b4cf539739df2c5dacb4c659f2488d 0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad 0x66a9893cc07d91d95644aedd05d03f95e1dba8af`：四址命中，name/category/tier 为上表值，Router02 不再是 Flashbots User，两个 Universal Router 不再是 sandwich-bot。
- `grep -c` 四址在 `references/labels/labels-eth.csv` 各恰 1 行。
- `python3 scripts/tests/labels_manifest.py`（校验模式）exit 0。
- run_all 中 `test_review_labels.py`、`test_labels_resolver_guards.py`、`test_goldset_curated_rebuild.py`、`test_benchmark_labels.py`、`test_add_labels_rollback.py`、`../labels/check_manual_sync.py` 全 PASS。
- **不跑** `roundtrip_check.py`（需先重建 `sources/out`，重建要重下载 dawsbot/brianleect 等大源，沙箱无网）；done 里注明"roundtrip 待 Fable 本机有网重建后跑"。

## 4. D 段：测试登记

`scripts/tests/run_all.py:206`（锚 `SUITE += ['test_producer_registry_current.py']`）之后追加：
```python
# repair-20260915-stage2-closeout W1：分布台账终态受控重开+快照登记解析；a4_gate limits-extract。
SUITE += ['test_reopen_cycle.py', 'test_a4_limits_extract.py']
```

## 5. 完成标准
- A1–A3、B1 生产改动落地；A4、B2 新测试 GREEN；`test_distribution_gate.py`、`test_a4_gate.py`、`test_audit_release_gate.py`、`test_round4_a5_seal.py` 等既有测试不改断言且 PASS；run_all 全绿（分母 +2）。
- C 段四址入库、三闸通过、归档副本在场。
- `w1_red_evidence.txt`、`w1_done.md` 在本目录；不 commit。
