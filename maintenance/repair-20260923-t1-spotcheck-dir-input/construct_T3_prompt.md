# 施工任务 T3（codex --write，按下方工单 v2 逐条执行）

## 派工基线
- 派工基线：main 分支、HEAD 为包含本提示词文件的最新提交（本提示词入库后 HEAD 才定，故**不以具体 SHA 判定**）；基线判定只看工单 §0.1：`git status --short` 为空、`git merge-base --is-ancestor 2197505 HEAD` exit 0、`git diff --quiet 2197505 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md` exit 0；行号以 `2197505` 为准（首次修改前统一核锚）。
- 本任务是**施工**，不是复核：按工单 §2 逐条落地、按 §0.7 先取 RED、按 §0.8 跑定向测试（`changelog_lint.py` 本轮不跑，记"调度方待验"）、按 §3 写完成报告 `T3_done.md` 到工单所在目录 `maintenance/repair-20260923-t1-spotcheck-dir-input/`。
- 纪律以工单 §0 为准（禁读 `~/.codex/`——插件启动搜索若已读 memories 披露一次，之后不再读；白名单；不 commit/push；禁 stash/checkout/reset；锚不符即停工）。工单已由 codex 只读复核两轮通过（`review_T3_reply_r1/r2.md`），施工中若发现工单与源码事实不符，停工报告，不自行改方案。
- 临时目录用 `tempfile` 并 `Path(td).resolve()`（macOS `/var` symlink 坑）；沙箱不能 bind loopback 的测试记 SANDBOX-BLOCKED。
- stdout 首行固定 `# 施工 T3：完成` 或 `# 施工 T3：停工`；停工报告名 `T3_done_attempt1_stopped.md`；末尾披露是否读过禁读路径。

---

# 工单 T3（v2，融合 codex 复核 r1 全部意见）：目录输入案发布期重算目录完整身份（FR-02 方案 C，限目录案）—— 版本 9.0.5

> 出处：codex 收官 review r1 FR-02（P1，`final_review_T1_reply_r1.md`）＋ r2 §c 技术意见（`final_review_T2_reply_r2.md`）：目录输入案通过后，覆写 `data/v2` 叶子（同大小改中间字节亦可）而不重跑时间抽查，READY/verify/发布闸仍 exit 0；文件输入案则立即被拒。用户 2026-09-23 裁决：**选 C，限目录案**——时间收据 `input_identity.kind == "directory"` 时，发布消费者重算目录完整身份（叶子集合＋逐文件 sha256）并与签名身份全等；文件分支逐字不动；同样流程（工单→codex 复核→施工→盲审→收官 review）。
> v2 变更（`review_T3_reply_r1.md`）：①入口/缓存/witness 边界精确化；1.1 补共享发布收据须重建；1.2 身份相等前提；1.3/2.1(c) 简化为两行全等校验不包异常；0.5 锚核验时点；步骤 4/5/6 修正（固定搬移位置、symlink needle、文件分支 needle `time plan input identity sha256 mismatch`）；索引行 233→176 B；详细段补成本与存量影响。
> 事实（调度方本机亲核，基线 HEAD `2197505`，9.0.4）：
> ① 正式 EVM READY（`handoff_manifest.py:349`）、verify（`:483`）、`validate_bundle`（`shared_release_receipt.py:2172`→`validate_sources:2122`）与发布闸（`audit_release_gate.py:543`→`_validate_reconciliation_report_once`→`witness_reconciliation_report:2068`）均通过 `validate_reconciliation_report` → `validate_reconciliation_check:1421` → `_validate_time_receipt:1085` → `_validated_time_plan_authority`（`:987-`）到达目录分支 `:1045-1059`（注释 `:1047` 明写"不重算哈希"）。发布闸内 witness 深验按案根在单次 `run()` 内缓存（`:1833` 建、`:1837` finally 清空），退出即清空；EVM `validate_sources:2120-2123` 不使用该 provider，另行深验——正常一次发布闸因此重算目录两次。此修复检查本次深验时的目录实物，不扩展 witness 对签发后目录叶子变化的保证（witness `:1895-1902` 只覆盖直接引用、`:2059-2061` 不打开清单；"同一次发布执行中继续改目录"或"长期保留 witness 后直接消费"不在本单保证内，属可接受边界）。
> ② 重算函数已有：`scripts/lib/anchor_selection.input_identity(raw_path)`（`:75-103`）返回 `({"path": str(resolved), "kind": "directory", "size", "sha256"}, files)`，目录内 symlink/无文件抛 `ValueError`；生产者 `anchor_plan.py` 与语义重放用的就是它，签名身份 `plan_receipt.input_identity` 正是其返回值（`anchor_plan.py:148` 直接取该 dict，`:176/:195/:207` 写入 plan/manifest/receipt，不改形态）。
> ③ 成本实测（`T3_cost_quq_v2_identity.log`）：QUQ 案 v2 目录 7.62 GB / 61 文件，`input_identity` 3.5 s，`match_signed=True`（QUQ 的规模、耗时与身份相等结果见该日志；本单不展示该案完整身份）。`shared_release_receipt.py` 已 `sys.path.insert(0, lib)`（`:21`），`anchor_selection` 只 import 标准库/duckdb/`anchor_point_contract`，无环。
> ④ 交接对 >64 MiB 文件用头尾分片指纹（codex r2 实测同大小改中间字节可躲过），故不能靠 data_map 叶子核验替代完整哈希；本单不动 handoff_manifest。

## 0. 开工纪律

- 0.1 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。开工先跑并贴进 `T3_done.md`：`git status --short`（须为空）与 `git rev-parse --short HEAD`（记录实际 HEAD）；`git merge-base --is-ancestor 2197505 HEAD` 须 exit 0；`git diff --quiet 2197505 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md` 须 exit 0。行号以 `2197505` 为准；任一不符**停工**。
- 0.2 **禁读** `~/.codex/`（启动搜索若已读 memories 披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`、本目录以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop` 下任何案卷。本目录内可读：`workorder_T1.md`、`workorder_T2.md`、`final_review_T1_reply_r1.md`、`final_review_T2_reply_r2.md`、`FR02_decision_page.md`、`T3_cost_quq_v2_identity.log`、`review_T3_reply_*.md`。`changelog_lint.py` 读 archive：本轮不执行，由调度方在获准环境执行并回传。
- 0.3 **白名单**（可写）：生产 `scripts/report/shared_release_receipt.py`；测试 `scripts/tests/test_anchor_plan_v3.py`；版本登记 `VERSION`、`pyproject.toml:15`、`SKILL.md:23`、`CHANGELOG.md`；完成报告 `T3_done.md`、`T3_red_evidence.txt`（本目录）。
- 0.4 **不改**：`scripts/lib/anchor_selection.py`（`input_identity` 是生产者与消费者共用的身份定义，不动）、`scripts/lib/receipt_kernel.py`、`scripts/lib/receipt_validate.py`、`scripts/lib/time_spotcheck.py`、`scripts/lib/anchor_plan.py`、`scripts/report/handoff_manifest.py`、`scripts/report/audit_release_gate.py`、`references/**`、`commands-staging/*`、`invariant_manifest`/`contract_manifest`。
- 0.5 所有施工锚在首次修改前统一核验：目标文件整行原文以 `grep -n -F -x -- '<整行>' <文件>` 命中恰 1 处且基线行号一致，不符**停工**。修改后的行号允许随插入自然移动（如 import 插入后目录分支行号 +1），完成报告记录实际 diff 行号。
- 0.6 离线；不 commit、不 push；禁 stash/checkout/reset；不建 worktree。
- 0.7 先红后绿，写 `T3_red_evidence.txt`：基线上按 §2.2 的 test_17 步骤——目录夹具消费者放行后，覆写 `v2/run_1/logs.parquet` 为同长度不同内容（翻转末字节），再调 `_shared_authority` → **基线仍放行**（这就是 FR-02）；再删一个叶子/加一个叶子 → 基线仍放行。三条贴命令与输出。
- 0.8 不跑 `run_all.py`（调度方本机跑）。定向跑（全部须 PASS，贴尾行）：`python3 -B scripts/tests/test_anchor_plan_v3.py`、`test_time_spotcheck.py`、`test_recon_deep_reverify.py`、`test_handoff_manifest.py`、`test_audit_release_gate.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py`、`invariant_scan.py`。`test_batch3_evm_vertical_slice.py` 沙箱不能 bind loopback 记 SANDBOX-BLOCKED。测试带 `MPLCONFIGDIR=$HOME/.matplotlib`（若可写）；临时目录 `Path(td).resolve()`。

## 1. 硬约束

- 1.1 身份校验逻辑只改 `kind=directory` 块；文件分支 `:1036-1039` 与其后既有逻辑逐字不变，文件时间证据的校验顺序、放行/拒收和错误文本保持不变。修改本文件会改变共享发布收据的 `producer.sha256`（`create_bundle:2154` 写入本文件 SHA、`validate_bundle:2177-2179` 要求与当前源码一致）；文件案与目录案的旧 `shared_release_receipt.json` 均须用现有 `create_bundle` 流程重建，不能据此声称共享发布产物字节不变（此影响自 9.0.3 起本已存在，本单不新增类别）。不得为兼容旧共享发布收据放宽校验。
- 1.2 重算用 `anchor_selection.input_identity`（新增**一行** import，与 `:37-48` 风格一致、按现有顺序放在 `from anchor_point_contract import (...)` 之前），比对方式＝返回身份 dict 与签名 `identity` **全等**（path/kind/size/sha256 四键；生产期与消费期均使用 resolve 后绝对路径。同一物理路径、相同叶子集合和文件字节下，两次身份相等；实际搬移导致旧引用失效时，由既有文件绑定或目录存在性／案根包含检查拒绝，本单不新增迁移支持）。不自造哈希算法、不比对子集。
- 1.3 重算放在 `:1056-1059` 既有目录检查之后；直接调用 `input_identity` 并全等比较。symlink、无普通文件等 `ValueError` 沿用本函数外层 authority-chain 上下文（`:1080-1081` 统一加 `time plan authority chain broken:` 前缀），不增加局部异常包装。
- 1.4 不新增公开函数/模块常量；允许 1 行 import；生产改动 ≤ 12 行（含注释订正，简化案为 import 1＋注释 1＋校验 2）。
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
            _require(input_identity(directory)[0] == identity,
                     "time plan input directory content differs from signed identity")
```

- 说明：`_require(cond, msg)` 为本文件既有 helper（`:145-147`，抛 `ValueError`）；`directory` 为 `:1055` 已定义的 `Path`；`input_identity` 自身对目录内 symlink/无普通文件抛 `ValueError`，经外层 `:1080-1081` 加前缀后已足够定位，不另包装。若施工时发现 `:1055-1059` 原文与工单出处①所述不一致，停工报告。

### 2.2 `scripts/tests/test_anchor_plan_v3.py` —— 回归

- 新增 `test_17_directory_input_recomputed_at_consumption()`，定义在 `:600` 整行 `def main():`（唯一）之前（`main` 按名字自动收集，无需接线；尾行将变 `anchor-plan v3: 17/17 PASS`）。复用 `_produce_plan(root, directory=True)`、`_shared_authority`、`_expect_reject`（`_ref` 由现有 helper 内部使用；本测试**不需要** `_refresh_receipt`，不得为了让负例通过而刷新签名身份或输入清单）；夹具目录 `root / "v2" / "run_1" / {logs,blocks}.parquet`。步骤（每步之后恢复原状并断言再次放行）：
  1. 放行基线：`_shared_authority(root, manifest_path, plan_path, receipt_path) == plan`。
  2. **同长度覆写**：读 `logs.parquet` 字节，翻转末字节写回（长度不变）→ `_expect_reject(..., "time plan input directory content differs from signed identity")`；写回原字节 → 放行。
  3. **新增叶子**：写 `run_1/extra.bin` → 拒（同 needle）；删除 → 放行。
  4. **删除叶子**：将 `source / "run_1" / "blocks.parquet"` rename 到同一案根下且预先不存在的 `root / "blocks.bak"`（已移出身份根 `root/v2`，仍有 logs 故走身份不等而非空目录异常）；调用消费者须以 `time plan input directory content differs from signed identity` 拒绝；移回原路径后再次放行。
  5. **目录内 symlink**：创建 `run_1/link.parquet -> logs.parquet`；调用消费者须以既有 helper 的文本 `input directory contains symlink` 拒绝；删除该链接后再次放行。
  6. **文件分支对照**：在已创建的独立 `root2` 中调用 `_produce_plan(root2, directory=False)`；先断言 `_shared_authority` 放行，再同长度翻转 CSV 末字节，断言既有生产错误文本 `time plan input identity sha256 mismatch`（`_shared_authority` 重算输入引用后旧签名 identity 在 `:1037` 被拒）；恢复原字节后再次放行。不得修改文件分支生产错误文本，不刷新计划或收据。
- RED（§0.7）：基线上步骤 2/3/4 均放行。

### 2.3 版本登记 9.0.5

- `VERSION` `9.0.4`→`9.0.5`；`pyproject.toml:15` `version = "9.0.4"`→`"9.0.5"`；`SKILL.md:23` `<!-- skill-version-source: VERSION; skill-version: 9.0.4 -->`→`9.0.5`。
- `CHANGELOG.md:13` 整行原文（唯一）：

```text
- **9.0.4**（2026-09-23）登记旧 time-spotcheck/v3 哈希并接通 EVM 时间收据两层校验，恢复存量文件案兼容；补充同一输入目录用法。schema 不变，版本档位 修。
```

  之前插入一行（176 B）：

```text
- **9.0.5**（2026-09-23）修复目录案消费期漏验：重算完整身份，拒叶子覆写、增删及 symlink（FR-02 C）；文件分支、schema 不变，档位 修。
```

- `CHANGELOG.md:101` 整行 `## [9.0.4] - 2026-09-23 — 时间抽查历史生产者登记与发布两层校验接线`（唯一）之前插入 `## [9.0.5]` 详细段（同格式四条：出处与裁决 / 改法与成本 / 字节与测试 / 成本-质量指标），末尾空一行。成本写明 QUQ 日志单次完整身份计算为 3.5 s（7.62 GB / 61 文件），正常 verify 重算一次、EVM 发布闸两次，分别估计增加约 3.5 s／7 s；兼容范围写明文件时间校验分支不变，但所有旧 shared_release_receipt.json 因本文件 producer.sha256 改变须重建（自 9.0.3 起已如此）。`changelog_lint.py` 由调度方执行。

## 3. 完成报告 `T3_done.md`

首行 `# T3 完成：<一句话>` 或 `# T3 停工：<原因>`。含：开工基线四项输出；RED 三条（指向 `T3_red_evidence.txt`）；每条施工实际 diff 行号与行数（生产 ≤ 12 行自证）；§0.8 尾行（SANDBOX-BLOCKED、changelog_lint 待验单列）；字节三处（SKILL 8021 不变、commands-staging 8789 不变、references 929085 不变）；`git diff --stat 2197505 -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`；未做/存疑逐条。
