# 工单 T2（v2，融合 codex 复核 r1 全部意见）：time_spotcheck 旧生产者哈希登记＋发布校验器两层精确接线（收官 review FR-01）＋文档一行（FR-03）—— 版本 9.0.4

> 出处：`final_review_T1_reply_r1.md` FR-01（P1）与 FR-03（P2）。FR-02 不在本工单（边界重议交用户裁决，另单）。
> 事实（调度方本机亲核，基线 HEAD `d2d6641`）：
> ① 9.0.3 改动 `scripts/lib/time_spotcheck.py` 后其源码哈希由 `87bbad2246f07afa2db4b37a7289fff2fc6ac16387284411e75104e1109f0a39` 变为 `050e33c70c220698fe4e5d8e8993e7f6ce0a91bd613219228ebf15fc2dbef4b2`。旧哈希可由 `git show b52cbedf230218e5da46334cf99b7111235e8367:scripts/lib/time_spotcheck.py | shasum -a 256` 复现（f4f8056 同值）。
> ② `scripts/lib/producer_history.py` 无 `time_spotcheck.py` 条目；`historical_producer_hashes("scripts/lib/time_spotcheck.py", "time-spotcheck/v3")` 在基线返回空集。
> ③ 消费者两层均只认当前哈希：envelope 层 `shared_release_receipt.py:1221` `validate_receipt(receipt, case_root=root)` 未传 `allowed_producer_hashes`；wrapper 层 `:1459-1460` `repo_ref_ok(item.get("producer"), RECON_PRODUCERS[family][key], ...)` 未传 `allowed_hashes`。先例：anchor_plan 在 `:1007-1019` 两层接线（`historical_producer_hashes` → `validate_receipt(allowed_producer_hashes=)` 与 `repo_ref_ok(allowed_hashes=)`）。`historical_producer_hashes` 已在 `:44` import。
> ④ 真实存量案复现（只读）：`python3 -B scripts/report/handoff_manifest.py verify --case-dir <OPN 案>` 在 HEAD 下 exit 2：`✗ reconciliation/accounting 公共深验失败: reconciliation time producer/runner is not current repository script`（`T2_red_evidence_opn_verify.log`）。受影响存量案：OPN、BITCOIN（均 `time-spotcheck/v3`、producer 87bbad…、文件输入）；QUQ 已是新哈希不受影响。
> ⑤ FR-03：源码确认 runner `inputs` 可省略（`_validate_spec:225`/`_input_items:68-70`/`run_job:237-238`）；显式登记时仍只接受文件（`:56/:85`），`data_map.files` 也只登记文件（`handoff_manifest:301-315`）。时间脚本 `--input` 示例仅见 `references/data-pipeline-evm-recon.md:152`。处置＝改 `:152` 明确"生成 plan 的同一输入"，压缩 `:158` 并补 runner 与 data_map 的文件登记规则，合计 −7 B；契约不动。（调度方提供、复核未独立核验：QUQ 案 wrapper `inputs` 为 null 仍四查 PASS；OPN 案 data_map 172 件含 v2 叶子，由案内 rglob 脚本产出。）
> v2 变更（`review_T2_reply_r1.md`）：登记守卫 `test_producer_registry_current.py` 须同步精确 `HISTORICAL_ONLY` 对（否则 2 FAIL）；两层准入收为一个私有函数 `_time_producer_history`（修 `[]` 收据从 ValueError 变 AttributeError 的回归）；H16 改为复用 `test_handoff_manifest.make_case` 走真实 wrapper 路径；H14/H15 收紧；FR-03 改两行 −7 B；开工 HEAD 条件改为祖先＋源码基线无差；`changelog_lint.py` 因读 archive 改由调度方执行；`:242` 锚改两侧唯一锚；CHANGELOG 索引行压到 200 B。
> 用户裁决（2026-09-22）：codex 施工、codex 复核/盲审、收官 codex review；原则＝skill 上下文不增、能删不增、能改不增。

## 0. 开工纪律

- 0.1 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。开工先跑并贴进 `T2_done.md`：`git status --short`（须为空）与 `git rev-parse --short HEAD`（记录实际 HEAD）。执行 `git merge-base --is-ancestor d2d6641 HEAD`，须 exit 0；执行 `git diff --quiet d2d6641 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`，须 exit 0，以确认工单存档未改变本次审查的生产、测试和文档基线。行号继续以 `d2d6641` 为准；任一检查不符**停工**。
- 0.2 **禁读** `~/.codex/`（启动搜索若已读 memories 披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、本目录以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop` 下任何案卷。本目录内可读：`workorder_T1.md`、`final_review_T1_reply_r1.md`、`review_T2_reply_r1.md`、`T2_red_evidence_opn_verify.log`。`changelog_lint.py` 会读取禁读的 `archive/CHANGELOG-archive.md`，本轮不执行；由调度方在获准环境原样执行并回传退出码及尾行，不删除或绕过其归档检查。
- 0.3 **白名单**（可写）：生产 `scripts/lib/producer_history.py`、`scripts/report/shared_release_receipt.py`；测试 `scripts/tests/test_recon_deep_reverify.py`、`scripts/tests/test_producer_registry_current.py`（仅允许扩充 `HISTORICAL_ONLY` 的 §2.1 精确对及同步注释，检查逻辑不变）；文档 `references/data-pipeline-evm-recon.md`（仅 §2.4 两行 `:152`、`:158`）；版本登记 `VERSION`、`pyproject.toml:15`、`SKILL.md:23`、`CHANGELOG.md`；完成报告 `T2_done.md`、`T2_red_evidence.txt`（写在本目录）。
- 0.4 **不改**：`scripts/lib/receipt_kernel.py`、`scripts/lib/receipt_validate.py`、`scripts/lib/time_spotcheck.py`、`scripts/lib/anchor_plan.py`、`scripts/lib/anchor_selection.py`、`scripts/report/handoff_manifest.py`、`scripts/report/reconciliation_report.py`、`scripts/tests/test_anchor_plan_v3.py`（原样验证登记条目六键、64 位哈希、40 位 commit 格式）、`scripts/tests/test_handoff_manifest.py`（只 import 复用 `make_case`）、`scripts/tests/test_audit_release_gate.py`、`commands-staging/*`、`invariant_manifest`/`contract_manifest`。
- 0.5 行号均指基线 `d2d6641`；施工锚使用目标文件**整行原文**，以 `grep -n -F -x '<整行>' <文件>` 核验恰 1 处且行号一致，不符**停工**。
- 0.6 离线；不 commit、不 push；禁 stash/checkout/reset；不建 worktree。
- 0.7 先红后绿，写 `T2_red_evidence.txt`：①基线上 `python3 -c` 调 `historical_producer_hashes("scripts/lib/time_spotcheck.py","time-spotcheck/v3")` 输出空集；②基线上按 §2.3 的 H11 向量（当前生产者产文件输入时间收据 → 把 `receipt.producer.sha256` 改为旧哈希并重写收据文件）调 `shared.validate_reconciliation_check(root,"time",item,TARGET,"evm")` 抛 `producer hash mismatch`；③引用 `T2_red_evidence_opn_verify.log`（调度方已取得，不必访问案卷）。
- 0.8 不跑 `run_all.py`（调度方本机跑）。定向跑（全部须 PASS，贴尾行）：`python3 -B scripts/tests/test_producer_registry_current.py`、`test_recon_deep_reverify.py`、`test_anchor_plan_v3.py`、`test_time_spotcheck.py`、`test_handoff_manifest.py`、`test_audit_release_gate.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py`、`invariant_scan.py`。`changelog_lint.py` 本轮不执行（见 0.2），完成报告记"调度方待验"，未取得结果不得记 PASS。`test_batch3_evm_vertical_slice.py` 沙箱不能 bind loopback，记 SANDBOX-BLOCKED 由调度方补验。测试须带 `MPLCONFIGDIR=$HOME/.matplotlib`（若可写）。

## 1. 硬约束

- 1.1 历史哈希**只**对 `family == "evm" and key == "time"` 生效，两层（envelope `:1221`、wrapper `:1459`）都接；其他 key 与 solana 家族一律仍传 `None`（行为逐字不变）。
- 1.2 历史集的 `script` 参数取自被校验 ref 自身的 `producer.path`（envelope 层＝`receipt["producer"]["path"]`，wrapper 层＝`item["producer"]["path"]`），且仅当该 path `in RECON_PRODUCERS["evm"]["time"]` 时才查询；否则传 `None`。`protocol` 两层都用字面量 `"time-spotcheck/v3"`（与 `:1404` 同一字面量，不抽常量、不新增符号）。理由：`validate_receipt` docstring 要求调用方保证集合与 `producer.path` 对应；固定 protocol 使 v2 schema 旧收据在 `:1404` 以"unknown schema"被拒而非含混的"hash mismatch"。
- 1.3 仅放宽 EVM/time/v3 的指定生产者哈希准入，不改文件/目录语义校验；该准入不额外按 `input.kind` 分流（满足目录语义的 EVM/time v3 收据同样可携带登记旧哈希过哈希关，不得宣称历史豁免只覆盖文件输入）。默认不传历史集时仍拒非当前旧哈希；旧哈希收据仍须通过其后全部语义校验（`:1399-1407` formal/schema/`_validate_time_receipt`，含 9.0.3 的 identity/清单/目录信任链）。`receipt_kernel`/`receipt_validate` 字节不变。
- 1.4 登记条目必须 git 可复现（§出处①），`status: "ACTIVE"`，字段集合与既有条目完全一致（script/sha256/commit/protocol/status/reason 六键，commit 为 40 位；`test_anchor_plan_v3.py` 原样验证格式）。`test_producer_registry_current.py` 按 §2.1 精确登记同步后须 PASS（它要求非 `HISTORICAL_ONLY` 的脚本登记当前哈希，故不同步则 2 FAIL）。
- 1.5 生产代码不新增公开函数、import 或模块常量；允许一个私有历史准入函数 `_time_producer_history` 及局部变量。测试允许局部导入既有夹具，旧哈希使用函数内常量。
- 1.6 文档：`references/**/*.md` 仅改 `references/data-pipeline-evm-recon.md:152/:158` 两行，合计净减 **7 B**（§2.4 给出整行原文与替换文，完成报告贴前后字节）；`SKILL.md` 8021 B 仅 `:23` 版本号 `9.0.3`→`9.0.4`（字节不变）；`commands-staging/*.md` 不变。
- 1.7 `git diff --stat` 只含 0.3 白名单。

## 2. 逐条施工

### 2.1 `scripts/lib/producer_history.py` —— 登记

- 锚：`:241` 整行 `        "reason": "Batch 4 registers the v3 formal Solana window producer frozen at the T1 tip.",` 与 `:243` 整行 `)`，分别以 `grep -n -F -x` 核验恰 1 处且行号一致；同时核对 `:242` 整行为 `    },` 且位于两锚之间（该行全文件出现 29 次，仅作相邻结构核对，不作唯一锚）。在 `:243` 之前插入一条（保持元组末尾逗号风格）：

```python
    {
        "script": "scripts/lib/time_spotcheck.py",
        "sha256": "87bbad2246f07afa2db4b37a7289fff2fc6ac16387284411e75104e1109f0a39",
        "commit": "b52cbedf230218e5da46334cf99b7111235e8367",
        "protocol": "time-spotcheck/v3",
        "status": "ACTIVE",
        "reason": "v9.0.4 registers the pre-9.0.3 time-spotcheck/v3 producer: 9.0.3 changed only the directory-input binding, so file-input receipts it signed stay valid.",
    },
```

- 自核：`git show b52cbedf230218e5da46334cf99b7111235e8367:scripts/lib/time_spotcheck.py | shasum -a 256` 首段须等于登记 sha256，贴进完成报告。
- 守卫同步（`scripts/tests/test_producer_registry_current.py`）：`:24` 整行原文 `HISTORICAL_ONLY = {("scripts/lib/anchor_plan.py", "anchor-plan/v2")}`（唯一）替换为：

```python
HISTORICAL_ONLY = {
    ("scripts/lib/anchor_plan.py", "anchor-plan/v2"),
    ("scripts/lib/time_spotcheck.py", "time-spotcheck/v3"),
}
```

  并把 `:21-23` 三行注释（以 `# receipt_validate.py:115-116 默认以当前文件哈希为允许集；登记表两条只是` 起、`# validate_receipt(...) 证明当前哈希无错误。豁免仅限下述精确协议对。` 止）替换为一行：

```python
# 默认验证器接受当前源码哈希；以下精确 script/protocol 对仅登记历史哈希。
```

  检查逻辑（`:35-68`）不动。

### 2.2 `scripts/report/shared_release_receipt.py` —— 消费者两层

- (0) 私有准入函数。锚：`:1208` 整行 `def validate_reconciliation_check(root, key, item, target, family):`（唯一）之前插入（前后各空两行）：

```python
def _time_producer_history(family, key, owner):
    if family != "evm" or key != "time" or not isinstance(owner, dict):
        return None
    producer = owner.get("producer")
    if not isinstance(producer, dict):
        return None
    path = producer.get("path")
    if not isinstance(path, str) or path not in RECON_PRODUCERS["evm"]["time"]:
        return None
    return historical_producer_hashes(path, "time-spotcheck/v3")
```

- (a) envelope 层。锚：`:1221` 整行 `    envelope_errors = validate_receipt(receipt, case_root=root)`（唯一）。替换为（保留原 `:1218` `migration` 及 `:1219-1220` 注释）：

```python
    envelope_errors = validate_receipt(
        receipt, case_root=root,
        allowed_producer_hashes=_time_producer_history(family, key, receipt))
```

- (b) wrapper 层。锚：`:1459` 整行 `        repo_ref_ok(item.get("producer"), RECON_PRODUCERS[family][key],`（唯一）与 `:1460` 整行 `                    f"reconciliation {key}")`。两行替换为：

```python
        repo_ref_ok(
            item.get("producer"), RECON_PRODUCERS[family][key],
            f"reconciliation {key}",
            allowed_hashes=_time_producer_history(family, key, item))
```

- 说明：`repo_ref_ok`（`:122-135`）核给定路径白名单、仓库内文件及当前/历史哈希；`validate_receipt` 核仓库内常规文件、当前/历史哈希及输入绑定，不自行核 script 与历史集的对应关系——该对应关系由 `_time_producer_history` 的限定查询保证；两者均接受"当前源码哈希 ∪ 显式传入的历史集"，历史集不替代当前哈希、不跳过后续语义校验。非对象收据（如 `[]`）必须仍由 `validate_receipt` 报 `receipt must be an object` 走原 ValueError 路径（函数把非 dict 直接返回 None）；`producer.path` 为 list/dict 时不得提前抛 TypeError。`:1461` 之后逻辑不动。若施工时发现 `:1460` 整行原文与此不一致，停工报告。

### 2.3 `scripts/tests/test_recon_deep_reverify.py` —— 回归

- 新增私有函数 `_test_time_producer_history(root, receipt)`，定义在 `:593` 整行 `def main() -> None:` 之前；在 `main()` 中 `:601` 整行 `        _test_time_authority_vectors(time_dir, time_receipt)` 之后插入 `        _test_time_producer_history(time_dir, time_receipt)`。复用既有 helper（`_sha`/`_ref`/`_item`/`_write_json`/`_expect_error`/`_mutate_receipt`），旧哈希用函数内常量 `old_hash`。每次 mutation 后另写新收据文件并更新 item 引用（`_mutate_receipt` 已内置），不覆盖原始收据。向量：
  - 登记断言：`producer_history.historical_producer_hashes("scripts/lib/time_spotcheck.py","time-spotcheck/v3")` 含 `old_hash`。
  - H11 正向：`receipt["producer"]["sha256"]` 改 `old_hash` → `shared.validate_reconciliation_check(root,"time",h11_item,TARGET,"evm")` 通过；保留 `h11_item` 供 H16。
  - H12 负向：sha 改 `"0"*64` → 拒，错误含 `producer hash mismatch`。
  - H13 负向：`producer.path` 改 `"scripts/lib/anchor_plan.py"`＋`old_hash` → 拒。
  - H14 跨查项：对 `_produce_recon` 产出的 balance 收据分别使用①原 `verify_recon.py` path＋`old_hash`、②`scripts/lib/time_spotcheck.py` path＋`old_hash`，`validate_reconciliation_check(root,"balance",...)` 均须报 envelope `producer hash mismatch`；沿用同一模式断言 `shared._time_producer_history("solana","time",{"producer":{"path":"scripts/solana/anchor_sampler.py","sha256":old_hash}})` 返回 None（Solana 不取得时间历史集）。
  - H15 默认路径：`receipt_validate.validate_receipt(<H11 收据 dict>, case_root=root)` 不传 allowed，断言结果恰为 `["producer hash mismatch"]`。
  - 类型边界：①收据文件内容为 `[]` 时 `validate_reconciliation_check(root,"time",...)` 仍抛 `ValueError` 且含 `receipt must be an object`；②`producer.path` 为 list 时 `_time_producer_history("evm","time",{"producer":{"path":["x"]}})` 返回 None 不抛。
  - H16 真实 wrapper 路径（必做，禁止免测出口）：复用 `test_handoff_manifest.make_case` 在同一 `root` 生成 EVM 四查 wrapper，time 项指向 H11 收据，调用真实 `shared.validate_reconciliation_report(root, TARGET)`；禁止替换/mock `repo_ref_ok`、`validate_receipt`、`validate_reconciliation_check`。另加一个只破坏 wrapper producer 哈希的负例。参考接法（放在 `h11_item` 与 `old_hash` 之后，共 17 行；`make_case` 的 plan 夹具用 `fixture_` 前缀不覆盖 `_produce_time` 的 anchor_plan 绑定，但它会写 `time_spotcheck.json`，故 wrapper 必须指向 H11 另写的文件；若实跑发现 `make_case` 与既有夹具其他文件冲突，改在 `root` 下新建子目录重新 `_produce_time` 后再做 H11/H16，并在完成报告说明）：

```python
    from test_handoff_manifest import make_case
    make_case(str(root), token=TARGET["token"],
              as_of_block=TARGET["as_of_block"])
    report_path = root / "reconciliation_report.json"
    wrapper = json.loads(report_path.read_text())
    old_ref = {"path": "scripts/lib/time_spotcheck.py", "sha256": old_hash}
    wrapper["checks"]["time"] = {**h11_item, "producer": old_ref}
    _write_json(report_path, wrapper)
    shared.validate_reconciliation_report(root, TARGET)
    wrapper["checks"]["time"]["producer"]["sha256"] = "0" * 64
    _write_json(report_path, wrapper)
    _expect_error(
        lambda: shared.validate_reconciliation_report(root, TARGET),
        "reconciliation time producer/runner is not current repository script")
    wrapper["checks"]["time"]["producer"]["sha256"] = old_hash
    _write_json(report_path, wrapper)
    shared.validate_reconciliation_report(root, TARGET)
```

- 真实 OPN 案 verify 由调度方补充复验，不替代 H16。测试文件在基线上先跑 H11 取 RED（§0.7②），施工后全绿。

### 2.4 `references/data-pipeline-evm-recon.md` —— 两行，合计 −7 B

- `:152` 整行原文（UTF-8、不含换行 111 B，末尾空格＋反斜杠续行符）：

```text
python3 scripts/lib/time_spotcheck.py --plan anchor_plan.json --input <生成plan所用的merged转账数据> \
```

  替换为（110 B；"v2"指目录形态，不要求目录名字面等于 data/v2）：

```text
python3 scripts/lib/time_spotcheck.py --plan anchor_plan.json --input <生成plan的同一文件或v2目录> \
```

- `:158` 整行原文（326 B）：

```text
- 产物 `time_spotcheck.json`（`time-spotcheck/v3`，target 绑定 chain/token/final-block，并绑定 plan、plan receipt、文件/清单与逐笔 RPC transcript；verdict/exit_code 为 0 PASS/2 FAIL/1 检测自身失败禁当 PASS）；split-run 案是 READY 必备件＋AUTO_GATES（handoff_manifest 重读防手报）。
```

  替换为（320 B）：

```text
- 产物 `time_spotcheck.json`（`time-spotcheck/v3`）绑定 target、plan/receipt、文件或清单及 RPC transcript；exit 0/2/1＝PASS/FAIL/ERROR。EVM READY 必备，AUTO_GATES 重读。目录输入时 runner `inputs` 可省略；若登记则填清单/叶子文件，`data_map.files` 填叶子，均不填目录。
```

- 字节算法：(110+320) − (111+326) = −7 B；换行数不变。完成报告贴两行 `sed -n Np … | tr -d "\n" | wc -c` 前后值，与 `references/**/*.md` 总字节前后（按 `T1_done_attempt2_stopped.md` 字节表同一口径：929092 → 929085）。

### 2.5 版本登记 9.0.4

- `VERSION`：`9.0.3` → `9.0.4`；`pyproject.toml:15` `version = "9.0.3"` → `"9.0.4"`；`SKILL.md:23` `<!-- skill-version-source: VERSION; skill-version: 9.0.3 -->` → `9.0.4`。
- `CHANGELOG.md:13` 整行原文（唯一）：

```text
- **9.0.3**（2026-09-23）修复 v2 目录输入的时间抽查收据绑定（QUQ 0922 案 ANOM-008）：生产者目录输入时 inputs.input 绑 anchor_plan 已签名输入清单，发布消费者对 kind=directory 验证清单身份、不重算目录哈希；文件分支校验顺序保留。schema/键不变，references/SKILL/commands 字节不增；测试 +1 目录回归用例；版本档位 修。
```

  之前插入一行（200 B）：

```text
- **9.0.4**（2026-09-23）登记旧 time-spotcheck/v3 哈希并接通 EVM 时间收据两层校验，恢复存量文件案兼容；补充同一输入目录用法。schema 不变，版本档位 修。
```

- `CHANGELOG.md:100`（整行 `## [9.0.3] - 2026-09-23 — QUQ ANOM-008：v2 目录输入的时间抽查收据绑定对齐（生产者＋发布校验器）`，唯一）之前插入详细段（与 9.0.3 段同格式，含"出处与裁决 / 改法 / 字节与测试 / 成本-质量指标"四条，末尾空一行）。字节与测试条写实际 diff 数字。
- 写入后由调度方在获准环境运行 `python3 -B scripts/tests/changelog_lint.py`，须 PASS，并回传退出码及尾行；本轮因禁读 archive 不执行该项。详细段写明 git commit、review 编号、测试与字节细节（索引行不写）。

## 3. 完成报告 `T2_done.md`

开工基线两项输出；RED 取证三条摘要（指向 `T2_red_evidence.txt`）；§2.1 登记 sha 复现命令与输出；每条施工的实际 diff 行号；§0.8 各命令尾行（含 SANDBOX-BLOCKED 项；`changelog_lint.py` 记"调度方待验"）；§2.4 两行前后字节与算法；三处字节前后（SKILL 8021 不变、commands-staging 8789 不变、references 929092→929085，口径同 T1 完成报告字节表）；H16 是否发生夹具冲突及处理；`git diff --stat d2d6641 -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`（只含白名单）；未做/存疑事项逐条列出，不得写"无"以外的含混话。首行固定格式：`# T2 完成：<一句话结论>` 或 `# T2 停工：<原因>`。
