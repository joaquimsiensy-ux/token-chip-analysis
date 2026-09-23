# W1 施工报告（停于 §1 提交前）

状态：未完成。§1 代码及守卫已修改并通过本节验证；git add 被当前沙箱拒绝，尚无施工 commit。§2—§5 未施工。

## 开工核验

- `git status --short` 输出为空；分支 `fix/solana-txv1`。
- 开工 HEAD：`9f74b851935a4a97667108881dedd311f26ccde6`。
- 工单所列代码行号及锚文本已核对；相关生产、测试、契约及版本文件与 `813ca6d` 无差异。未发现需触发行号不符停工的情况。

## 已做改动（当前工作树行号）

- `scripts/lib/solana_attested_session.py:10, 22`
- `scripts/lib/solana_exact_validate.py:32, 1214, 1220, 1222`
- `scripts/lib/solana_observation.py:20, 271`
- `scripts/solana/audit_closed_accounts.py:41, 231, 420, 483`
- `scripts/solana/decode_txs.py:10, 42`
- `scripts/solana/decode_txs_v2.py:25, 296, 341`
- `scripts/solana/fast_probe_tops.py:16, 55`
- `scripts/solana/gas_origin.py:19, 82`
- `scripts/solana/probe_escrows.py:21, 151`
- `scripts/solana/probe_window_moves.py:26, 122`
- `scripts/solana/sqd_gap_repair.py:27, 42, 636`
- `scripts/solana/stake_decode.py:23, 97`
- `scripts/solana/trace_wallet.py:15, 77`
- `scripts/solana/whale_deep.py:23, 65, 155`
- `scripts/tests/invariant_scan.py:355, 1353`
- `scripts/tests/test_batch4_invariant_guards.py:36, 526`
- `maintenance/repair-20260923-solana-txv1/W1_red_evidence.txt:1`：修改代码前保存四项基线红证据。
- `maintenance/repair-20260923-solana-txv1/W1_done.md:1`：本停工报告。

改动内容：交易版本上限统一为 1；修复请求模板集中至 validator；补包导入回退、producer 版本钉、禁止数值字面量的 AST 守卫及注入测试。所有生产与测试改动均在 §0.3 白名单内。

## 与工单差异及理由

- 未能完成 §1 commit，故不进入 §2；§3 登记、§4 认领测试和 §5 版本/文档均未执行。
- 执行显式白名单文件的 `git add -- ...` 时退出码 128，原始错误如下：

```text
fatal: Unable to create '/Users/uravvv/.claude/tca-fix-txv1/.git/index.lock': Operation not permitted
```

- 当前会话将 `.git` 限制为只读，且禁止请求提权；不能在本会话内完成正常暂存与提交。未尝试绕过限制。
- 未执行 git commit（git add 已失败）；未 push，未操作 main。现有改动留在工作树，不能视作完整可发布修复，producer 登记尚未更新。

## 定向验证及尾行

下列 Python 验证均带 `MPLCONFIGDIR=$HOME/.matplotlib`、`PYTHONDONTWRITEBYTECODE=1`。

- `python3 scripts/tests/test_batch4_invariant_guards.py`：退出码 0；尾行：
```text
PASS B4-G1: bare pool / labels / vertical slice / denominator injections
```
- `python3 -c "import scripts.lib.solana_attested_session, scripts.lib.solana_exact_validate"`：退出码 0，标准输出/错误均为空（无尾行）。
- `git diff --check`：退出码 0，无输出。

§0.7 其余定向测试尚未运行；`test_batch3_solana_vertical_slice.py` 尚未运行，未标记 SANDBOX-BLOCKED；未运行 `run_all.py`。本报告不宣称全套 PASS。

## 红证据

路径：`maintenance/repair-20260923-solana-txv1/W1_red_evidence.txt`。
已复现：13 文件 17 处字面量 0；repair argparse 无 `--adopt-pending`；版本 1 模板摘要的成功行不计入 completed；隔离导入报 `No module named 'endpoint_identity'`。尾行：
```text
RED evidence complete: all four baseline assertions reproduced.
```

## 禁读路径与操作自报

- 未读取 `~/.codex` 下任何文件；未读取 `~/Documents`、`~/Desktop`。启动自动披露的技能目录信息未用于打开文件。
- 全程离线，未访问网络，未启动子代理。
- 未批量删除任何文件或目录；测试及红证据的临时夹具由测试自身清理。

## 待裁决

请调度方提供允许对本克隆 `.git` 正常写入的施工环境，以便先提交现有 §1 改动（`W1(1):` 中文主题及指定 Co-Authored-By），再继续 §2—§5。当前会话不能申请提权；未获得具备该能力的环境前，不继续跨节施工。恢复时应核对本报告记录的工作树改动，不能将其误当作开工前的外来脏文件。


## 第 2 段开工核验（2026-09-23）

- 当前分支 `fix/solana-txv1`；`git diff --stat` 为 16 个文件，与第 1 段「已做改动」一致；`git ls-files --others --exclude-standard` 无输出。未发现其他工作树改动。
- 本段用户指令覆盖前述「待裁决」中的 git 写入要求：`.git` 只读，git add/commit 由调度方完成，不以不能提交为停工理由。
- 已按顺序读取 A1、v5 与本报告；尚未修改生产或测试文件。

## 停工原因

A1 第 2 条的数量断言与实况不符，触发本段用户纪律第 7 条「工单里任何行号/断言与实况不符：停工」。

- 工单位置：`maintenance/repair-20260923-solana-txv1/workorder_W1_amendment_A1.md:7`。该条先单独规定 `sqd_gap_repair.py` 的导入调整，随后写「其余 11 个 `scripts/solana/*.py`」。
- 实况：该目录共 11 个文件使用 `from solana_attested_session import SOLANA_MAX_SUPPORTED_TX_VERSION`；扣除已经单列的 `sqd_gap_repair.py:27` 后，其余只有 10 个。清单及当前行号如下：
  - `scripts/solana/audit_closed_accounts.py:41`
  - `scripts/solana/decode_txs.py:12`
  - `scripts/solana/decode_txs_v2.py:25`
  - `scripts/solana/fast_probe_tops.py:16`
  - `scripts/solana/gas_origin.py:19`
  - `scripts/solana/probe_escrows.py:21`
  - `scripts/solana/probe_window_moves.py:26`
  - `scripts/solana/stake_decode.py:23`
  - `scripts/solana/trace_wallet.py:15`
  - `scripts/solana/whale_deep.py:23`

- 复核方式：`rg -n 'from solana_attested_session import SOLANA_MAX_SUPPORTED_TX_VERSION' scripts/solana`，并用 Python 枚举该目录的 `*.py` 文件复核，数量断言 `len(files) == 11 and len(remaining) == 10` 通过。
- 建议调度方将 A1 第 2 条「其余 11 个」更正为「其余 10 个」。没有擅自更改工单或按推测继续施工。

### 本段改动、差异及验证记录

- 仅追加 `maintenance/repair-20260923-solana-txv1/W1_done.md` 本段开工及停工记录；第 1 段 16 个生产/测试文件改动保持原状。
- A1、§2、§4 均未完成；§3、§5 未执行。与计划的差异原因是上述数量断言不符，不是 git 写权限。
- 测试尾行：无。本段在开工核验阶段触发停工，未运行 A1 验收、§0.7 定向测试或 registry 测试；不宣称任何测试 PASS。
- 未读取 `~/.codex`、`~/Documents`、`~/Desktop`；全程离线；未启动子代理；未执行 git add/commit/push；未删除文件。
- 本记录仅供调度方接手，不表示第 2 段施工完成。

待调度方 commit


## 第 2 段续工：A1 完成（2026-09-23）

- 开工仍为 `fix/solana-txv1`，第 1 段 16 文件差异，无其他改动；A1.1 已订正「其余 10 个」，前述停工原因已解除。§2、§4 所引用基线 `813ca6d` 行号及锚点已核对。
- 常量与三行注释移至 `scripts/lib/endpoint_identity.py:10`（定义 `:13`）；`scripts/lib/solana_attested_session.py` 恢复 HEAD 原字节，撤销常量和导入回退。
- 导入改指 endpoint_identity：`scripts/lib/solana_exact_validate.py:32`（含相对导入回退）、`scripts/lib/solana_observation.py:16`、`scripts/solana/sqd_gap_repair.py:24`；其余十文件为 `audit_closed_accounts.py:41`、`decode_txs.py:12`、`decode_txs_v2.py:25`、`fast_probe_tops.py:16`、`gas_origin.py:19`、`probe_escrows.py:21`、`probe_window_moves.py:26`、`stake_decode.py:23`、`trace_wallet.py:15`、`whale_deep.py:23`（均在 `scripts/solana/`）。decode_txs 的 lib path 保留。
- 与工单差异：仅按 A1 替代 v5 常量落点及隔离导入验收；endpoint_identity 的写入由 A1 明确授权。§3、§5 未执行。历史红证据④作废，勘误依据改记「常量在 session 时 invariant_scan 报 12 条 transport_calls 不符」（A1 调度方已给证据）。
- 验证环境：`MPLCONFIGDIR=$HOME/.matplotlib PYTHONDONTWRITEBYTECODE=1`；均使用 `python3 -B`。
  - `invariant_scan.py`：exit 0；尾行 `PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0`。
  - `test_batch4_invariant_guards.py`：exit 0；尾行 `PASS B4-G1: bare pool / labels / vertical slice / denominator injections`。
  - `python3 -B -c "import scripts.lib.endpoint_identity, scripts.lib.solana_exact_validate"`：exit 0，无输出。
- 未读禁区；离线；未启动子代理；未执行 git add/commit/push；未删除文件。


## 第 2 段：§2 完成（2026-09-23）

- `scripts/solana/sqd_gap_repair.py:689,707`：抽取只读解析，续跑外壳保留原落盘行为。
- 同文件 `:729,745,783`：兼容两参数续跑、独立数据行验真、0..当前版本摘要接受集合、认领记录形状与前代摘要复验。
- 同文件 `:816`：同 parent 直接前代校验、ACTIVE sha 摘要复现、最长对齐候选前缀、全目标冲突预验、硬链接与仅 EXDEV 原子复制、证据目录同步后原子提交 ledger。
- 同文件 `:1110,1415,1541`：live resume 传 plan、入口认领、发布前复验；CLI 加 `--adopt-pending` 并强制 `--resume`（`:1738`）。
- `scripts/lib/solana_exact_validate.py:1228`：独立重建 plan 摘要，固定 coverage.map.sha256 与 coverage/beta 并集映射；`:1337,1385,1520,1605`：认领记录形状/前代重算、参考源指纹一致、历史版本摘要接受集合。
- 与工单差异：无功能范围差异；§3、§5 未动。现有测试先出现一次本次编辑的续行语法错误，已修正；不涉及工单行号/断言不符。
- 验证环境同 A1；`test_sqd_gap_repair.py` exit 0，尾行 `GREEN 29c implemented validate_current_candidates 已实现`；`test_batch8_repair_scale.py` exit 0，尾行 `PASS batch8: key-neutral identity/pool failover/ordered workers/resume/streaming`。
- §4 故障向量及全量定向验收接续施工；当前不宣称全部验收完成。未读禁区、未联网、未启动子代理、未执行 git 写操作。


## 第 2 段：§4 代码完成，验收停工（2026-09-23）

- `scripts/tests/test_sqd_gap_repair.py:775`：E27(a) 后接 E27(d)；`:820` 新增 `adoption_regressions`，复用工单指定夹具函数。
- 同文件 `:863`：分别用两候选/三候选配额中断生成一行/两行来源，改为真实 ACTIVE 前代 `25f04ff1…` 摘要和版本 0 请求摘要，各向量独立复制。
- 同文件 `:910,956,969,995`：版本 1 实际请求与独立完整 body 摘要、深拷贝 v1/transactionConfig 交易、残尾只读、来源全文件哈希不变、硬链接 inode、当前/前代摘要与 coverage/beta 并集、深验篡改、最长对齐前缀。
- 同文件 `:1007,1071,1089,1112,1149`：入口/冲突负向①—⑨；目标 ledger 发布前中断⑩；提交后配额中断与普通 resume⑪；限定 EXDEV + 原子复制失败重试⑫；同步伪造哈希的可信来源边界。
- 与工单差异：E27(d) 由锚点调用同文件辅助函数承载；额外覆盖 header 指纹、adopted 为 null/rows 为 bool、无 plan 续跑拒绝。首次新增夹具测试因跨 slot 重用签名被深验拒绝，已将深拷贝交易的测试签名按 slot 唯一化后通过，不改生产逻辑。
- `test_sqd_gap_repair.py` exit 0；E27(d) 证据行：`GREEN E27(d): predecessor adoption/v1/torn tail/longest prefix/12 fault vectors/deep digest`；最终尾行：`GREEN 29c implemented validate_current_candidates 已实现`。
- `test_batch8_repair_scale.py` exit 0；尾行：`PASS batch8: key-neutral identity/pool failover/ordered workers/resume/streaming`。
- §4 新增测试已通过；全定向验收未通过，原因如下。§3、§5 未执行。

## 停工原因（本次续工，新发现）

工单 v5 的 §2.3 第 6 条、§0.4 与 §0.7 同时执行发生确定性冲突，依用户纪律第 7 条停工；未修改 manifest 或弱化扫描器。

- `workorder_W1_v5.md:89` 明确要求在认领提交阶段 `os.link(src, dst)`；已实现于 `scripts/solana/sqd_gap_repair.py:886`（函数 `adopt_predecessor_pending`）。
- `scripts/tests/invariant_scan.py:1113-1114` 的 `AtomicVisitor.visit_Call` 将每个直接 `os.link` 所在函数登记为原子写入点；`:1302-1303` 对照 manifest 检查遗漏。
- `scripts/tests/invariant_manifest.json:1186` 的既有 sqd_gap_repair 原子写入登记只有 `locator: main`，没有新增函数。
- `workorder_W1_v5.md:20`（§0.4）禁止改 invariant_manifest；`:23`（§0.7）又要求 invariant_scan PASS。按要求实现后的实况为 exit 1：

```text
FAIL atomic_writes: code point missing from manifest: ('scripts/solana/sqd_gap_repair.py', 'adopt_predecessor_pending')
invariant manifest FAIL: 1 discrepancy(s)
```

- A1 阶段扫描确实为绿；该新增不符由 §2 规定的原子链接引入，与已修复的 transport_calls 无关。
- 建议调度方勘误授权新增这个 atomic_writes 登记及相应计数，或明确另一种符合守卫的实现方案。当前不通过换名/别名隐藏 os.link，也不擅改 §0.4。
- 发现冲突后停止生产/测试代码修改；仅收集已启动的定向测试结果、核对保护文件并补交接报告。不是因为 git 只读停工。


## 第 2 段定向验收汇总及尾行

全部命令在仓库根目录执行，统一环境 `MPLCONFIGDIR=$HOME/.matplotlib PYTHONDONTWRITEBYTECODE=1`，形式为 `python3 -B scripts/tests/<下列脚本与参数>`；未跑 `run_all.py`。原始日志在 `/private/tmp/w1-final-directed/`，摘要 `summary.json`。下表自包含保留每项尾行，不依赖临时日志长期存在。

| 测试 | exit / 状态 | 实际最后一行 |
|---|---|---|
| `changelog_lint.py` | 0 / PASS | `PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 82 条 + 归档 139 条` |
| `docs_lint.py --all` | 0 / PASS | `PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）` |
| `invariant_scan.py` | 1 / FAIL（停工） | `invariant manifest FAIL: 1 discrepancy(s)` |
| `test_batch2d_stream_tail.py` | 0 / PASS | `PASS batch2d SQD stream tail: 4/4 groups` |
| `test_batch3_solana_producers.py` | 0 / PASS | `PASS B3-G2: Solana slot/envelope/txn/timestamp producer guards` |
| `test_batch3_solana_vertical_slice.py` | 1 / SANDBOX-BLOCKED | `PermissionError: [Errno 1] Operation not permitted` |
| `test_batch3c_census_fields.py` | 0 / PASS | `PASS batch3c census fields match the SQD contract` |
| `test_batch4_invariant_guards.py` | 0 / PASS | `PASS B4-G1: bare pool / labels / vertical slice / denominator injections` |
| `test_batch7_validator_coverage_gaps.py` | 0 / PASS | `批7 validator 覆盖缺口加固回归全部 GREEN (缺口1遍历主键 + 缺口3边slot窗口)` |
| `test_batch8_repair_scale.py` | 0 / PASS | `PASS batch8: key-neutral identity/pool failover/ordered workers/resume/streaming` |
| `test_f03_sharedmap_reuse.py` | 0 / PASS | `PASS F-03 shared-map reuse: 15/15 groups` |
| `test_param_scripts.py` | 0 / PASS | `PASS: 三脚本参数反例、旧案字面量与 cadence identity 绑定` |
| `test_producer_registry_current.py` | 1 / EXPECTED-FAIL | `producer registry: 4 FAIL` |
| `test_r9_batch2_solana_sqd_adapter.py` | 0 / PASS | `PASS R9 B2-G3: SQD dataset scope fixed and Solana mainnet RPC anchored` |
| `test_r9_batch3_solana_observation.py` | 0 / PASS | `PASS R9 B3-G1/G4: Solana observation protocol and negative variants` |
| `test_r9_solana_attested_session.py` | 0 / PASS | `PASS R9 SolanaAttestedSession: 10/10` |
| `test_reconcile_v4_receipt.py` | 0 / PASS | `GREEN 32 verdict/exit_code/gate_pass 三元互洽` |
| `test_repair_batch1.py` | 0 / PASS | `PASS v6.41.0 batch1 steps 1-6 RV-07/RV-04/RV-17/F-03/F-01/A5v3/F-04` |
| `test_repair_batch_d.py` | 0 / PASS | `BATCH D 全部通过` |
| `test_review_solana_integrity.py` | 0 / PASS | `PASS: B-06/B-07/B-08 + P1-03 v1/v2 decode retry, identity and failure receipts` |
| `test_sqd_collector_meta_v4.py` | 0 / PASS | `PASS: SQD v4 collector meta logical evidence matches replay` |
| `test_sqd_consumer_v4.py` | 0 / PASS | `PASS: SQD v4 consumer split-mode regressions` |
| `test_sqd_coverage_probe.py` | 0 / PASS | `PASS SQD coverage probe: 12/12 offline groups` |
| `test_sqd_gap_repair.py` | 0 / PASS | `GREEN 29c implemented validate_current_candidates 已实现` |
| `test_version_consistency.py` | 0 / PASS | `PASS: M-03 version metadata consistent at 9.0.3` |

- 汇总：25 项已运行；22 项 PASS，1 项 invariant FAIL，1 项 registry 预期 FAIL，1 项 vertical slice SANDBOX-BLOCKED。不宣称全套 PASS。
- registry 的四个 FAIL 均为当前 sqd_gap_repair producer sha 尚未登记，协议分别为 cache/v4、coverage-resolution/v1、repair-bundle/v1、repair-pointer/v1。工作树脚本 sha256：`977a4823f819559de070e53be681a66808861deb602fed108aa027c5af88c0c7`（仅供核对，不是代码 commit 证明）；按用户指令留待调度方 commit 后另派 §3。
- vertical slice 在 `ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)` → `socket.bind` 被沙箱拒绝；实际尾行如表，未当作代码回归或 PASS。
- `test_repair_batch_d.py` 出现 `$HOME/.matplotlib` 不可写提示，库自动使用系统临时缓存，最终 exit 0；命令仍遵循工单 MPLCONFIGDIR 设置。
- A1 指定隔离导入 `python3 -B -c "import scripts.lib.endpoint_identity, scripts.lib.solana_exact_validate"` 再次 exit 0，无输出。
- `git diff --check` exit 0，无输出。§0.4 保护文件、两个 manifest、commands-staging、producer_history、session 以及 §5 文档/版本文件逐字节与 HEAD 核对一致。
- 当前 18 个已跟踪文件有改动：第 1 段 session 改动已撤销，增加 endpoint_identity、test_sqd_gap_repair 与本交接报告；其余延续授权清单。新增认领实现及测试留在工作树，未暂存/提交。

## 本段最终交接状态

A1 完成且守卫通过；§2 认领代码已落地；§4 新增测试通过，但最终不变量验收因上述工单冲突停工。调度方需先裁决新增 atomic_writes 登记。§3 登记、§5 版本/文档未施工，版本仍为 9.0.3。报告前部的历史停工记录保留，当前状态以本段为准。

未读取 `~/.codex`、`~/Documents`、`~/Desktop`；离线施工，未访问外部 API；未启动子代理；未执行 git add/commit/push；未批量删除文件或目录（测试自身临时夹具按原有生命周期清理）。

待调度方 commit


## 第 3 段：A2 登记、v5 §3 producer_history、§5 文档与版本完成（2026-09-23）

### 开工核验与裁决执行

- 开工 `git status --short` 为空；`git branch --show-current` 为 `fix/solana-txv1`。第 1、2 段已由调度方提交，本段未执行任何 git 写操作。
- 首先读取 A2，再读取 v5 与 A1；核对本段使用的行号与锚点：manifest `:1186-1190`、invariant_scan `:1113-1114/:1302-1303`、producer_history 四条旧登记 `:204-233`、registry 守卫 `:43-50`、scan-schemas 表与不变量 `:998-1023`、capture `:198`、pyproject `:15`、SKILL `:23` 均符合。未发现本段工单行号或断言与实况不符。
- 执行 `git show a1f1594a144a9042a529e8c829e4afd2c63e7633:scripts/solana/sqd_gap_repair.py | shasum -a 256`，实得 `977a4823f819559de070e53be681a66808861deb602fed108aa027c5af88c0c7`，与 A2 一致；再次用 Python 核对该 git 对象与当前脚本 SHA256 相同。
- 按 A2 先仅补原子写入登记；invariant_scan 立即 exit 0，atomic_writes=62，无 semantics 不符。随后登记四协议，再完成文档、CHANGELOG 与版本。
- 修改 CHANGELOG 前先跑 changelog_lint，exit 0，尾行：`PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 82 条 + 归档 139 条`。

### 改动清单（本段完成后行号）

- `scripts/tests/invariant_manifest.json:1186`：只新增 `adopt_predecessor_pending` / `scripts/solana/sqd_gap_repair.py` / `multi_file_txn` 一条，紧邻该脚本既有 main 登记；原有条目保持不变。
- `scripts/lib/producer_history.py:235,243,251,259`：新增 cache/v4、repair-bundle/v1、coverage-resolution/v1、repair-pointer/v1 四条 ACTIVE 登记；commit 与 sha 使用上述 A2 参数，reason 原样按 v5 §3；旧 `25f04ff1…` 四条 ACTIVE 登记字节不变。
- `references/scan-schemas.md:1004`：§14.8 表新增 header.adopted 及五个子字段；`:1027` 更新 resume 历史请求版本集合，`:1028-1029` 写明「来源可信是输入前提」与硬链接成功时共享 inode、EXDEV 不共享、深验发现改写但不隔离、禁止原地改写的完整边界。
- `references/data-pipeline-solana-capture.md:198`：只在正式产物窄门第 2 条句末补认领接口、前代登记/摘要复验、可信输入前提及常量归属与 producer 换代要求。
- `CHANGELOG.md:13,101`：新增 9.1.0 索引与正文，说明新接口、header.adopted 契约扩展、交易版本 1 修复、恢复与信任边界、登记和验证依据；常量归属写 `endpoint_identity.SOLANA_MAX_SUPPORTED_TX_VERSION`。
- `VERSION:1`、`pyproject.toml:15`、`SKILL.md:23`：同步至 9.1.0；SKILL 只改版本注释。
- `maintenance/repair-20260923-solana-txv1/W1_done.md:219`：追加本段记录，历史记录不改。

### 与工单差异及范围复核

- 无实现范围差异。按 A2 仅放开 manifest 一条登记；按 A1/A2 将文档常量归属统一为 endpoint_identity；capture 中「来源可信是前提」按当前指令与 §2.1 写成「来源可信是输入前提」。
- 用户当前施工纪律覆盖 v5 §0.8：`.git` 只读，add/commit 留给调度方；本段登记基于已经落定的代码 commit。本段仅运行用户指定的十项定向测试，不重跑前两段其余测试；不运行 run_all.py。
- 结构核对通过：manifest 删除唯一新增项后与 HEAD 完全相同；producer_history 删除四条新项后与 HEAD 原登记序列完全相同，前代四条仍 ACTIVE；scan-schemas 的 §14.8 以外字节不变；capture 仅第 198 行追加，原句保留。
- 报告写入前 `git diff --name-only` 恰为上述八个登记/文档/版本文件，暂存区为空；生产逻辑、测试脚本、contract_manifest、commands-staging 及其余不改项均未改动。追加报告后共九个文件。
- 红证据沿用前两段 `W1_red_evidence.txt` 和本报告历史段落；本段未改红证据。A2 已解除第 2 段 atomic_writes 停工原因，registry 的四个预期 FAIL 也已消除。

### 本段定向测试尾行

全部从仓库根目录执行：`MPLCONFIGDIR="$HOME/.matplotlib" PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/<脚本与参数>`。下列十项全部 exit 0 / PASS；表中保留实际最后一行（registry 的 `0 FAIL` 与 SQD 的 `GREEN` 均为成功尾行）。

| 测试 | exit / 状态 | 实际最后一行 |
|---|---|---|
| `invariant_scan.py` | 0 / PASS | `PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=62, formal_entrypoints=61, exceptions=0` |
| `test_producer_registry_current.py` | 0 / PASS | `producer registry: 0 FAIL` |
| `test_version_consistency.py` | 0 / PASS | `PASS: M-03 version metadata consistent at 9.1.0` |
| `changelog_lint.py` | 0 / PASS | `PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 83 条 + 归档 139 条` |
| `docs_lint.py --all` | 0 / PASS | `PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）` |
| `test_sqd_gap_repair.py` | 0 / PASS | `GREEN 29c implemented validate_current_candidates 已实现` |
| `test_batch8_repair_scale.py` | 0 / PASS | `PASS batch8: key-neutral identity/pool failover/ordered workers/resume/streaming` |
| `test_batch4_invariant_guards.py` | 0 / PASS | `PASS B4-G1: bare pool / labels / vertical slice / denominator injections` |
| `test_r7_findings.py` | 0 / PASS | `PASS R7 regression suite: 15/15 observed green; EXPECTED_RED=0` |
| `test_sixlens_docs.py` | 0 / PASS | `PASS: 六视角批⑤大小口径与 archive 路由` |

- E27(d) 另有成功证据行：`GREEN E27(d): predecessor adoption/v1/torn tail/longest prefix/12 fault vectors/deep digest`。
- `git diff --check` exit 0，无输出。上述测试中的故障注入错误输出属于预期负向用例，均以进程 exit 0 和最终尾行为准。

### 纪律自报与交接

未读取 `~/.codex`、`~/Documents`、`~/Desktop`；仓库内 `SKILL.md` 仅作为授权版本目标读取和修改，未读取被禁止目录下的 Skill。全程离线，未访问外部 API；未启动子代理；未执行 git add/commit/push 或其他 git 写操作；未主动删除文件或目录（现有测试按自身生命周期清理临时夹具）。使用工单要求的 MPLCONFIGDIR，禁止生成 Python 字节码缓存。

本段 A2、§3、§5 已完成；版本 9.1.0，十项定向测试全部 PASS。本段工作区变更留给调度方审查与提交。

待调度方 commit
