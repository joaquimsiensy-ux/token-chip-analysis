# 工单 T3（v1）：目录输入案发布期重算目录完整身份（FR-02 方案 C，限目录案）—— 版本 9.0.5

> 出处：codex 收官 review r1 FR-02（P1，`final_review_T1_reply_r1.md`）＋ r2 §c 技术意见（`final_review_T2_reply_r2.md`）：目录输入案通过后，覆写 `data/v2` 叶子（同大小改中间字节亦可）而不重跑时间抽查，READY/verify/发布闸仍 exit 0；文件输入案则立即被拒。用户 2026-09-23 裁决：**选 C，限目录案**——时间收据 `input_identity.kind == "directory"` 时，发布消费者重算目录完整身份（叶子集合＋逐文件 sha256）并与签名身份全等；文件分支逐字不动；同样流程（工单→codex 复核→施工→盲审→收官 review）。
> 事实（调度方本机亲核，基线 HEAD `2197505`，9.0.4）：
> ① 唯一消费点：`scripts/report/shared_release_receipt.py:_validated_time_plan_authority`（`:987-`）目录分支 `:1045-1059`，注释 `:1047` 明写"不重算哈希"。READY 生成（`handoff_manifest.py:349`）、verify（`:483`）、发布闸（`audit_release_gate.py:111-127` 经 `_validate_reconciliation_report_once`）与 `validate_bundle` 均经 `validate_reconciliation_report` → `_validate_time_receipt` → 此函数，故一处改动覆盖全部入口。
> ② 重算函数已有：`scripts/lib/anchor_selection.input_identity(raw_path)`（`:75-103`）返回 `({"path": str(resolved), "kind": "directory", "size", "sha256"}, files)`，目录内 symlink/无文件抛 `ValueError`；生产者 `anchor_plan.py` 与语义重放用的就是它，签名身份 `plan_receipt.input_identity` 正是其返回值（QUQ 案 `anchor_plan.receipt.json` 实证 path 为绝对路径、kind=directory、size 7624197683）。
> ③ 成本实测（`T3_cost_quq_v2_identity.log`）：QUQ 案 v2 目录 7.62 GB / 61 文件，`input_identity` 3.5 s，与签名身份全等。`shared_release_receipt.py` 已 `sys.path.insert(0, lib)`（`:21`），`anchor_selection` 只 import 标准库/duckdb/`anchor_point_contract`，无环。
> ④ 交接对 >64 MiB 文件用头尾分片指纹（codex r2 实测同大小改中间字节可躲过），故不能靠 data_map 叶子核验替代完整哈希；本单不动 handoff_manifest。

## 0. 开工纪律

- 0.1 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。开工先跑并贴进 `T3_done.md`：`git status --short`（须为空）与 `git rev-parse --short HEAD`（记录实际 HEAD）；`git merge-base --is-ancestor 2197505 HEAD` 须 exit 0；`git diff --quiet 2197505 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md` 须 exit 0。行号以 `2197505` 为准；任一不符**停工**。
- 0.2 **禁读** `~/.codex/`（启动搜索若已读 memories 披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`、本目录以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop` 下任何案卷。本目录内可读：`workorder_T1.md`、`workorder_T2.md`、`final_review_T1_reply_r1.md`、`final_review_T2_reply_r2.md`、`FR02_decision_page.md`、`T3_cost_quq_v2_identity.log`、`review_T3_reply_*.md`。`changelog_lint.py` 读 archive：本轮不执行，由调度方在获准环境执行并回传。
- 0.3 **白名单**（可写）：生产 `scripts/report/shared_release_receipt.py`；测试 `scripts/tests/test_anchor_plan_v3.py`；版本登记 `VERSION`、`pyproject.toml:15`、`SKILL.md:23`、`CHANGELOG.md`；完成报告 `T3_done.md`、`T3_red_evidence.txt`（本目录）。
- 0.4 **不改**：`scripts/lib/anchor_selection.py`（`input_identity` 是生产者与消费者共用的身份定义，不动）、`scripts/lib/receipt_kernel.py`、`scripts/lib/receipt_validate.py`、`scripts/lib/time_spotcheck.py`、`scripts/lib/anchor_plan.py`、`scripts/report/handoff_manifest.py`、`scripts/report/audit_release_gate.py`、`references/**`、`commands-staging/*`、`invariant_manifest`/`contract_manifest`。
- 0.5 施工锚使用目标文件**整行原文**，`grep -n -F -x -- '<整行>' <文件>` 恰 1 处且行号一致，不符**停工**。
- 0.6 离线；不 commit、不 push；禁 stash/checkout/reset；不建 worktree。
- 0.7 先红后绿，写 `T3_red_evidence.txt`：基线上按 §2.2 的 test_17 步骤——目录夹具消费者放行后，覆写 `v2/run_1/logs.parquet` 为同长度不同内容（翻转末字节），再调 `_shared_authority` → **基线仍放行**（这就是 FR-02）；再删一个叶子/加一个叶子 → 基线仍放行。三条贴命令与输出。
- 0.8 不跑 `run_all.py`（调度方本机跑）。定向跑（全部须 PASS，贴尾行）：`python3 -B scripts/tests/test_anchor_plan_v3.py`、`test_time_spotcheck.py`、`test_recon_deep_reverify.py`、`test_handoff_manifest.py`、`test_audit_release_gate.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py`、`invariant_scan.py`。`test_batch3_evm_vertical_slice.py` 沙箱不能 bind loopback 记 SANDBOX-BLOCKED。测试带 `MPLCONFIGDIR=$HOME/.matplotlib`（若可写）；临时目录 `Path(td).resolve()`。

## 1. 硬约束

- 1.1 **只动目录分支**：`identity.get("kind") == "directory"` 块内新增重算＋全等校验；文件分支（`:1036-1039`）与其后全部逻辑逐字不变。文件输入路径的放行/拒收与错误文本顺序不变。
- 1.2 重算用 `anchor_selection.input_identity`（新增**一行** import，与 `:37-48` 风格一致、按现有顺序放在 `from anchor_point_contract import (...)` 之前），比对方式＝返回身份 dict 与签名 `identity` **全等**（path/kind/size/sha256 四键；path 为生产时 `str(resolve())`，消费期同样 resolve，案根未迁移即相等；案根迁移本已被 `:1056-1059` 拒）。不自造哈希算法、不比对子集。
- 1.3 顺序：重算放在 `:1056-1059`（案根内目录存在性）**之后**，即先便宜检查再读盘。`input_identity` 抛出的 `ValueError`（目录内 symlink、无普通文件）须包成带上下文的 `ValueError`（`_require` 风格，前缀 `time plan input directory`），不得裸抛、不得吞掉。
- 1.4 不新增公开函数/模块常量；允许 1 行 import＋若干局部变量；生产改动 ≤ 12 行（含注释订正）。
- 1.5 文档字节：`references/**`、`commands-staging/*` **零改动**；`SKILL.md` 仅 `:23` 版本号；CHANGELOG 索引行 ≤ 200 B。
- 1.6 `git diff --stat` 只含 0.3 白名单。

## 2. 逐条施工

### 2.1 `scripts/report/shared_release_receipt.py`

- (a) import。锚：`:39` 整行 `from anchor_point_contract import (LEGACY_FINAL_BLOCK_EDGE_KIND, V2_SCHEMA,`（唯一）之前插入一行：

```python
from anchor_selection import input_identity
```

- (b) 注释订正。锚：`:1047` 整行 `            # 清单正文 input 须与签名身份全等，目录只做案根内存在性检查，不重算哈希`（唯一）替换为：

```python
            # 清单正文 input 须与签名身份全等；目录先查案根内存在性，再重算完整身份（9.0.5，FR-02 方案 C）
```

- (c) 重算。锚：`:1059` 整行 `                     "signed directory identity is not a directory inside the case root")`（唯一）之后插入：

```python
            try:
                recomputed, _ = input_identity(directory)
            except ValueError as exc:
                raise ValueError(f"time plan input directory identity recompute failed: {exc}") from exc
            _require(recomputed == identity,
                     "time plan input directory content differs from signed identity")
```

- 说明：`_require(cond, msg)` 为本文件既有 helper（抛 `ValueError`）；`directory` 为 `:1055` 已定义的 `Path`。若施工时发现 `:1055-1059` 原文与工单出处①所述不一致，停工报告。

### 2.2 `scripts/tests/test_anchor_plan_v3.py` —— 回归

- 新增 `test_17_directory_input_recomputed_at_consumption()`，定义在 `:600` 整行 `def main():`（唯一）之前（`main` 按名字自动收集，无需接线；尾行将变 `anchor-plan v3: 17/17 PASS`）。复用 `_produce_plan(root, directory=True)`、`_shared_authority`、`_expect_reject`、`_ref`、`_refresh_receipt`；夹具目录 `root / "v2" / "run_1" / {logs,blocks}.parquet`。步骤（每步之后恢复原状并断言再次放行）：
  1. 放行基线：`_shared_authority(root, manifest_path, plan_path, receipt_path) == plan`。
  2. **同长度覆写**：读 `logs.parquet` 字节，翻转末字节写回（长度不变）→ `_expect_reject(..., "time plan input directory content differs from signed identity")`；写回原字节 → 放行。
  3. **新增叶子**：写 `run_1/extra.bin` → 拒（同 needle）；删除 → 放行。
  4. **删除叶子**：把 `blocks.parquet` 改名到 `root` 外的临时位置或 `root/blocks.bak`（注意 `root/blocks.bak` 不在 `v2` 内）→ 拒；移回 → 放行。
  5. **目录内 symlink**：`run_1/link.parquet -> logs.parquet` → `_expect_reject(..., "time plan input directory identity recompute failed")`（needle 含 `symlink`）；删除 → 放行。
  6. **文件分支不受影响**：`_produce_plan(root2, directory=False)` 后覆写 CSV 末字节 → 仍由既有 `time plan input identity`/sha 校验拒（needle 沿用现有测试断言文本，不得新增文件分支 needle）。
- RED（§0.7）：基线上步骤 2/3/4 均放行。

### 2.3 版本登记 9.0.5

- `VERSION` `9.0.4`→`9.0.5`；`pyproject.toml:15` `version = "9.0.4"`→`"9.0.5"`；`SKILL.md:23` `<!-- skill-version-source: VERSION; skill-version: 9.0.4 -->`→`9.0.5`。
- `CHANGELOG.md:13` 整行原文（唯一）：

```text
- **9.0.4**（2026-09-23）登记旧 time-spotcheck/v3 哈希并接通 EVM 时间收据两层校验，恢复存量文件案兼容；补充同一输入目录用法。schema 不变，版本档位 修。
```

  之前插入一行（≤ 200 B）：

```text
- **9.0.5**（2026-09-23）目录输入案发布期重算目录完整身份并与签名身份全等（FR-02 方案 C，限目录案；文件分支不变）：叶子覆写/增删/symlink 一律拒。schema 不变，版本档位 修。
```

- `CHANGELOG.md:101` 整行 `## [9.0.4] - 2026-09-23 — 时间抽查历史生产者登记与发布两层校验接线`（唯一）之前插入 `## [9.0.5]` 详细段（同格式四条：出处与裁决 / 改法与成本（写入 QUQ 实测 7.62 GB / 61 文件 / 3.5 s）/ 字节与测试 / 成本-质量指标），末尾空一行。`changelog_lint.py` 由调度方执行。

## 3. 完成报告 `T3_done.md`

首行 `# T3 完成：<一句话>` 或 `# T3 停工：<原因>`。含：开工基线四项输出；RED 三条（指向 `T3_red_evidence.txt`）；每条施工实际 diff 行号与行数（生产 ≤ 12 行自证）；§0.8 尾行（SANDBOX-BLOCKED、changelog_lint 待验单列）；字节三处（SKILL 8021 不变、commands-staging 8789 不变、references 929085 不变）；`git diff --stat 2197505 -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`；未做/存疑逐条。
