# 工单 T2（v1）：time_spotcheck 旧生产者哈希登记＋发布校验器两层精确接线（收官 review FR-01）＋文档一行（FR-03）—— 版本 9.0.4

> 出处：`final_review_T1_reply_r1.md` FR-01（P1）与 FR-03（P2）。FR-02 不在本工单（边界重议交用户裁决，另单）。
> 事实（调度方本机亲核，基线 HEAD `d2d6641`）：
> ① 9.0.3 改动 `scripts/lib/time_spotcheck.py` 后其源码哈希由 `87bbad2246f07afa2db4b37a7289fff2fc6ac16387284411e75104e1109f0a39` 变为 `050e33c70c220698fe4e5d8e8993e7f6ce0a91bd613219228ebf15fc2dbef4b2`。旧哈希可由 `git show b52cbedf230218e5da46334cf99b7111235e8367:scripts/lib/time_spotcheck.py | shasum -a 256` 复现（f4f8056 同值）。
> ② `scripts/lib/producer_history.py` 无 `time_spotcheck.py` 条目；`historical_producer_hashes("scripts/lib/time_spotcheck.py", "time-spotcheck/v3")` 在基线返回空集。
> ③ 消费者两层均只认当前哈希：envelope 层 `shared_release_receipt.py:1221` `validate_receipt(receipt, case_root=root)` 未传 `allowed_producer_hashes`；wrapper 层 `:1459-1460` `repo_ref_ok(item.get("producer"), RECON_PRODUCERS[family][key], ...)` 未传 `allowed_hashes`。先例：anchor_plan 在 `:1007-1019` 两层接线（`historical_producer_hashes` → `validate_receipt(allowed_producer_hashes=)` 与 `repo_ref_ok(allowed_hashes=)`）。`historical_producer_hashes` 已在 `:44` import。
> ④ 真实存量案复现（只读）：`python3 -B scripts/report/handoff_manifest.py verify --case-dir <OPN 案>` 在 HEAD 下 exit 2：`✗ reconciliation/accounting 公共深验失败: reconciliation time producer/runner is not current repository script`（`T2_red_evidence_opn_verify.log`）。受影响存量案：OPN、BITCOIN（均 `time-spotcheck/v3`、producer 87bbad…、文件输入）；QUQ 已是新哈希不受影响。
> ⑤ FR-03：runner `inputs` 为可选（QUQ 案 wrapper `inputs` 为 null 仍四查 PASS）；`data_map.json` 由案内脚本 rglob 全部叶子产出（OPN 案 172 件含 `data/v2/run_*/logs.parquet`）；skill 文档中 `--input` 唯一用法说明是 `references/data-pipeline-evm-recon.md:152`，仍写"merged转账数据"。故 FR-03 只需改该行，runner/data_map 契约不动、不加说明。
> 用户裁决（2026-09-22）：codex 施工、codex 复核/盲审、收官 codex review；原则＝skill 上下文不增、能删不增、能改不增。

## 0. 开工纪律

- 0.1 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。开工先跑并贴进 `T2_done.md`：`git status --short`（须为空）；`git rev-parse --short HEAD`（须为 `d2d6641`）。不符**停工**。
- 0.2 **禁读** `~/.codex/`（启动搜索若已读 memories 披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、本目录以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop` 下任何案卷。本目录内可读：`workorder_T1.md`、`final_review_T1_reply_r1.md`、`T2_red_evidence_opn_verify.log`。
- 0.3 **白名单**（可写）：生产 `scripts/lib/producer_history.py`、`scripts/report/shared_release_receipt.py`；测试 `scripts/tests/test_recon_deep_reverify.py`；文档 `references/data-pipeline-evm-recon.md`（仅 §2.4 一行）；版本登记 `VERSION`、`pyproject.toml:15`、`SKILL.md:23`、`CHANGELOG.md`；完成报告 `T2_done.md`、`T2_red_evidence.txt`（写在本目录）。
- 0.4 **不改**：`scripts/lib/receipt_kernel.py`、`scripts/lib/receipt_validate.py`、`scripts/lib/time_spotcheck.py`、`scripts/lib/anchor_plan.py`、`scripts/lib/anchor_selection.py`、`scripts/report/handoff_manifest.py`、`scripts/report/reconciliation_report.py`、`scripts/tests/test_producer_registry_current.py`（它会自动验证新条目 git 可复现，必须原样 PASS）、`scripts/tests/test_anchor_plan_v3.py`、`commands-staging/*`、`invariant_manifest`/`contract_manifest`。
- 0.5 行号均指基线 `d2d6641`；施工锚使用目标文件**整行原文**，以 `grep -n -F -x '<整行>' <文件>` 核验恰 1 处且行号一致，不符**停工**。
- 0.6 离线；不 commit、不 push；禁 stash/checkout/reset；不建 worktree。
- 0.7 先红后绿，写 `T2_red_evidence.txt`：①基线上 `python3 -c` 调 `historical_producer_hashes("scripts/lib/time_spotcheck.py","time-spotcheck/v3")` 输出空集；②基线上按 §2.3 的 H11 向量（当前生产者产文件输入时间收据 → 把 `receipt.producer.sha256` 改为旧哈希并重写收据文件）调 `shared.validate_reconciliation_check(root,"time",item,TARGET,"evm")` 抛 `producer hash mismatch`；③引用 `T2_red_evidence_opn_verify.log`（调度方已取得，不必访问案卷）。
- 0.8 不跑 `run_all.py`（调度方本机跑）。定向跑（全部须 PASS，贴尾行）：`python3 -B scripts/tests/test_producer_registry_current.py`、`test_recon_deep_reverify.py`、`test_anchor_plan_v3.py`、`test_time_spotcheck.py`、`test_handoff_manifest.py`、`test_audit_release_gate.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py`、`invariant_scan.py`、`changelog_lint.py`。`test_batch3_evm_vertical_slice.py` 沙箱不能 bind loopback，记 SANDBOX-BLOCKED 由调度方补验。测试须带 `MPLCONFIGDIR=$HOME/.matplotlib`（若可写）。

## 1. 硬约束

- 1.1 历史哈希**只**对 `family == "evm" and key == "time"` 生效，两层（envelope `:1221`、wrapper `:1459`）都接；其他 key 与 solana 家族一律仍传 `None`（行为逐字不变）。
- 1.2 历史集的 `script` 参数取自被校验 ref 自身的 `producer.path`（envelope 层＝`receipt["producer"]["path"]`，wrapper 层＝`item["producer"]["path"]`），且仅当该 path `in RECON_PRODUCERS["evm"]["time"]` 时才查询；否则传 `None`。`protocol` 两层都用字面量 `"time-spotcheck/v3"`（与 `:1404` 同一字面量，不抽常量、不新增符号）。理由：`validate_receipt` docstring 要求调用方保证集合与 `producer.path` 对应；固定 protocol 使 v2 schema 旧收据在 `:1404` 以"unknown schema"被拒而非含混的"hash mismatch"。
- 1.3 不放宽：默认路径（不传 allowed）仍拒旧哈希；旧哈希收据仍须通过其后全部语义校验（`:1399-1407` formal/schema/`_validate_time_receipt`，含 9.0.3 的 identity/清单/目录信任链）。`receipt_kernel`/`receipt_validate` 字节不变。
- 1.4 登记条目必须 git 可复现（§出处①），`status: "ACTIVE"`，字段集合与既有条目完全一致（script/sha256/commit/protocol/status/reason 六键，commit 为 40 位）。`test_producer_registry_current.py` 原样 PASS。
- 1.5 不新增公开函数、不新增 import、不新增模块常量；允许局部变量。
- 1.6 文档：`references/**/*.md` 只改 `:152` 一行，净增 **≤ +1 B**（§2.4 给出原文与替换文，完成报告贴前后字节）；`SKILL.md` 8021 B 仅 `:23` 版本号 `9.0.3`→`9.0.4`（字节不变）；`commands-staging/*.md` 不变。
- 1.7 `git diff --stat` 只含 0.3 白名单。

## 2. 逐条施工

### 2.1 `scripts/lib/producer_history.py` —— 登记

- 锚：`:241` 整行 `        "reason": "Batch 4 registers the v3 formal Solana window producer frozen at the T1 tip.",`（唯一）；其后 `:242` 为 `    },`、`:243` 为 `)`。在 `:242` 与 `:243` 之间插入一条（保持元组末尾逗号风格）：

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

### 2.2 `scripts/report/shared_release_receipt.py` —— 消费者两层

- (a) envelope 层。锚：`:1221` 整行 `    envelope_errors = validate_receipt(receipt, case_root=root)`（唯一）。替换为（缩进 4 空格，保持 `:1218` `migration` 与 `:1219-1220` 注释原样在前）：

```python
    time_history = None
    producer_ref = receipt.get("producer")
    if (family == "evm" and key == "time" and isinstance(producer_ref, dict)
            and producer_ref.get("path") in RECON_PRODUCERS[family][key]):
        time_history = historical_producer_hashes(producer_ref["path"], "time-spotcheck/v3")
    envelope_errors = validate_receipt(receipt, case_root=root,
                                       allowed_producer_hashes=time_history)
```

- (b) wrapper 层。锚：`:1459` 整行 `        repo_ref_ok(item.get("producer"), RECON_PRODUCERS[family][key],`（唯一）与 `:1460` `                    f"reconciliation {key}")`。两行替换为：

```python
        producer_ref = item.get("producer")
        time_history = None
        if (family == "evm" and key == "time" and isinstance(producer_ref, dict)
                and producer_ref.get("path") in RECON_PRODUCERS[family][key]):
            time_history = historical_producer_hashes(producer_ref["path"], "time-spotcheck/v3")
        repo_ref_ok(producer_ref, RECON_PRODUCERS[family][key],
                    f"reconciliation {key}", allowed_hashes=time_history)
```

- 说明：`repo_ref_ok`（`:122-135`）与 `validate_receipt` 内部仍各自核 path 在白名单/是仓库常规文件，历史集只是把 `admitted` 多加旧哈希；`:1461` 之后逻辑不动。若施工时发现 `:1460` 整行原文与此不一致，停工报告。

### 2.3 `scripts/tests/test_recon_deep_reverify.py` —— 回归

- 新增私有函数 `_test_time_producer_history(root, receipt)`，在 `main()`（`:593`）中紧接 `:601` `_test_time_authority_vectors(time_dir, time_receipt)` 之后调用（同一 `time_dir`）。复用既有 helper（`_sha`/`_ref`/`_item`/`_write_json`/`_expect_error`/`_mutate_receipt`），不引入新夹具文件。旧哈希用模块级常量或函数内常量均可（不新增公开符号）。向量：
  - H11 正向：`producer_history.historical_producer_hashes("scripts/lib/time_spotcheck.py","time-spotcheck/v3")` 含旧哈希；把 `receipt["producer"]["sha256"]` 改为旧哈希写成新文件 → `shared.validate_reconciliation_check(root,"time",item,TARGET,"evm")` 通过（其余绑定不动）。
  - H12 负向：同上但 sha 改 `"0"*64` → 拒，错误含 `producer hash mismatch`。
  - H13 负向：`producer.path` 改 `"scripts/lib/anchor_plan.py"`＋旧哈希 → 拒（不得因历史集放行）。
  - H14 负向：对 `_produce_recon` 产出的 balance 收据把 `producer.sha256` 改为时间旧哈希 → `validate_reconciliation_check(root,"balance",...)` 拒（历史集不外溢到其他 key）。
  - H15 默认路径：`receipt_validate.validate_receipt(<H11 收据>)`（不传 allowed）返回非空 errors。
  - H16 wrapper 层：调 `shared.repo_ref_ok({"path":"scripts/lib/time_spotcheck.py","sha256":<旧哈希>}, shared.RECON_PRODUCERS["evm"]["time"], "reconciliation time", allowed_hashes=<历史集>)` 通过；不传 `allowed_hashes` 抛 `is not current repository script`。**另须**一条走 `:1459` 真实代码路径的向量：若本文件已有或可用 ≤ 30 行搭出 EVM 四查 wrapper（`reconciliation-report/v3`，checks 按 `RECON_CHECK_KEYS["evm"]` 顺序，`time` item 的 `producer.sha256` 用旧哈希、receipt 用 H11 文件）并调 `shared.validate_reconciliation_report(root, TARGET)`，则加之；若需要 supply_truth 等无现成夹具、成本明显超过 30 行，则在完成报告写明"wrapper 真实路径由调度方在存量案（OPN）verify 复验"，不硬凑。
- 测试文件在基线上先跑 H11 取 RED（§0.7②），施工后全绿。

### 2.4 `references/data-pipeline-evm-recon.md:152`

- 原文（整行，不含换行 111 B，末尾有一个空格加反斜杠续行符）：

```text
python3 scripts/lib/time_spotcheck.py --plan anchor_plan.json --input <生成plan所用的merged转账数据> \
```

- 替换为（不含换行 112 B，+1 B；仅尖括号内文字变，续行符原样）：

```text
python3 scripts/lib/time_spotcheck.py --plan anchor_plan.json --input <同plan的merged文件或data/v2目录> \
```

- 完成报告贴 `sed -n 152p … | tr -d "\n" | wc -c` 前后值（111 → 112）与 `references/**/*.md` 总字节前后（按 `T1_done_attempt2_stopped.md` 字节表同一口径：929092 → 929093）。

### 2.5 版本登记 9.0.4

- `VERSION`：`9.0.3` → `9.0.4`；`pyproject.toml:15` `version = "9.0.3"` → `"9.0.4"`；`SKILL.md:23` `<!-- skill-version-source: VERSION; skill-version: 9.0.3 -->` → `9.0.4`。
- `CHANGELOG.md:13`（整行原文以 `- **9.0.3**（2026-09-23）修复 v2 目录输入的时间抽查收据绑定` 开头，唯一）之前插入一行：

```text
- **9.0.4**（2026-09-23）9.0.3 收官 review FR-01：登记 pre-9.0.3 的 time-spotcheck/v3 生产者哈希（git 可复现 b52cbed）并在发布校验器 envelope/wrapper 两层仅对 evm/time 精确接线，存量文件输入案（OPN/BITCOIN 类）时间收据在 HEAD 恢复可验；默认路径与其他查项不放宽。FR-03：references:152 `--input` 说明补目录用法（+1 B）。版本档位 修。
```

- `CHANGELOG.md:100`（整行 `## [9.0.3] - 2026-09-23 — QUQ ANOM-008：v2 目录输入的时间抽查收据绑定对齐（生产者＋发布校验器）`，唯一）之前插入详细段（与 9.0.3 段同格式，含"出处与裁决 / 改法 / 字节与测试 / 成本-质量指标"四条，末尾空一行）。字节与测试条写实际 diff 数字。
- 写入后跑 `python3 scripts/tests/changelog_lint.py` 须 PASS。

## 3. 完成报告 `T2_done.md`

开工基线两项输出；RED 取证三条摘要（指向 `T2_red_evidence.txt`）；§2.1 登记 sha 复现命令与输出；每条施工的实际 diff 行号；§0.8 各命令尾行（含 SANDBOX-BLOCKED 项）；§2.4 前后字节；三处字节前后（SKILL 8021 不变、commands-staging 8789 不变、references 929092→929093，口径同 T1 完成报告字节表）；`git diff --stat d2d6641 -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`（只含白名单）；未做/存疑事项逐条列出，不得写"无"以外的含混话。首行固定格式：`# T2 完成：<一句话结论>` 或 `# T2 停工：<原因>`。
