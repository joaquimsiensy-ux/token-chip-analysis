# 工单 W1 v3 — Solana 交易版本上限常量化 ＋ 修复产物「前代认领」机制（→ 9.1.0）

> v2→v3 变更（吸收 codex 复核 r2 `review_W1_r2_report.md` 8 条）：①§2.1/§5 措辞改为「来源可信是输入前提；目录归属与深验只验证本案归属与结构/内容一致性」；②全部目标冲突预验放到首个 link/copy 之前，「零落盘」定义为验证拒绝时产物状态不变；③认领台账改用既有 `publish_exclusive + RawBytes` 原子提交，写清提交前/后的恢复路径，仅 `EXDEV` 触发复制回退；④§2.5 固定键映射（`coverage.map.sha256`、`resolution.plan_candidates` 两组并集），validator 用私有独立摘要函数并补与 core 的一致性向量，verifier 收不含 header 的数据行；⑤保留硬链接并写明共享 inode 联动边界；⑥§1.2 触发器简化为显式 `if MAX != 1: raise`，并补「共享模板语义变化须同步改 producer/登记」；⑦§4 修正矛盾断言与三处构造；⑧补残尾只读、最长前缀、预验/提交中断、同步篡改边界、独立版本 1 请求与 v1/transactionConfig 输入向量。
> v1→v2 变更见 `workorder_W1_v2.md` 首段。
>
> 背景（调度方亲核，案卷数字为外部背景）：Solana 主网已出现交易版本 1（slot 447210248：`maxSupportedTransactionVersion: 0` 报 -32015；改 1 返回 851 笔含 1 笔 v1，v1 消息体多 `transactionConfig`；Helius 对 2/255 也接受）。钉版 skill 13 文件 17 处写死 0；`sqd_gap_repair.py:892` 遇 v1 直接 `ValueError`。改脚本 ⇒ `producer.sha256` 变 ⇒ `plan_digest` 变（`sqd_repair_core.py:80`）⇒ 旧 pending 无法 `--resume`。用户裁决：修常量＋加「经审计的前代产物认领」；原则**能删不加、能改不加、references/SKILL.md 上下文尽量不增**。

## 0. 纪律

- 0.1 开工 `git status --short` 为空（`.staging_b3/` 被 .gitignore 忽略、不算脏）、分支 `fix/solana-txv1`；本仓库是克隆，**不 push、不动 main**。
- 0.2 **禁读 `~/.codex`**（启动自动披露除外）；禁读 `~/Documents`、`~/Desktop`。
- 0.3 **白名单（可写）**：
  - 生产：`scripts/lib/solana_attested_session.py`、`scripts/lib/solana_exact_validate.py`、`scripts/lib/solana_observation.py`、`scripts/solana/sqd_gap_repair.py`、`scripts/solana/{probe_window_moves,fast_probe_tops,decode_txs,decode_txs_v2,whale_deep,audit_closed_accounts,gas_origin,stake_decode,probe_escrows,trace_wallet}.py`、`scripts/lib/producer_history.py`
  - 测试：`scripts/tests/test_sqd_gap_repair.py`、`scripts/tests/invariant_scan.py`、`scripts/tests/test_batch4_invariant_guards.py`
  - 文档：`references/scan-schemas.md`（仅 §14.8 表与不变量）、`references/data-pipeline-solana-capture.md`（仅「正式产物窄门」第 2 条句末）、`CHANGELOG.md`
  - 版本：`VERSION`、`pyproject.toml:15`、`SKILL.md:23`
  - 报告：本目录 `W1_done.md`、`W1_red_evidence.txt`
- 0.4 **不改**：`scripts/solana/sqd_repair_core.py`、`scripts/solana/sqd_cache_identity.py`、`scripts/solana/replay_edges.py`、`scripts/lib/receipt_kernel.py`、`scripts/tests/test_producer_registry_current.py`、`test_batch8_repair_scale.py`、`test_batch7_validator_coverage_gaps.py`、`test_version_consistency.py`（均须原样 PASS）、`commands-staging/*`、`invariant_manifest`/`contract_manifest`。
- 0.5 行号与实况不符即停工写报告（行号为施工前基线 `813ca6d`，旁附锚文本）。
- 0.6 先红后绿 `W1_red_evidence.txt`：①基线 grep/AST 证明 13 文件 17 处字面量 0；②基线 argparse 无 `--adopt-pending`；③基线 `load_resume_slots` 对 params_digest 为版本 1 模板的行不计入 completed；④隔离进程 `python3 -c "import scripts.lib.solana_attested_session"` 基线报 `No module named 'endpoint_identity'`。
- 0.7 **不跑 `run_all.py`**（调度方本机跑）。定向跑全部 PASS 并贴尾行：`test_sqd_gap_repair.py`、`test_batch8_repair_scale.py`、`test_batch7_validator_coverage_gaps.py`、`test_producer_registry_current.py`、`test_version_consistency.py`、`test_batch4_invariant_guards.py`、`invariant_scan.py`、`test_r9_solana_attested_session.py`、`test_r9_batch2_solana_sqd_adapter.py`、`test_sqd_coverage_probe.py`、`test_batch2d_stream_tail.py`、`test_f03_sharedmap_reuse.py`、`test_reconcile_v4_receipt.py`、`test_batch3c_census_fields.py`、`test_batch3_solana_producers.py`、`test_sqd_collector_meta_v4.py`、`test_sqd_consumer_v4.py`、`test_r9_batch3_solana_observation.py`、`test_review_solana_integrity.py`、`test_param_scripts.py`、`test_repair_batch1.py`、`test_repair_batch_d.py`、`changelog_lint.py`、`docs_lint.py --all`；隔离进程 `python3 -c "import scripts.lib.solana_attested_session, scripts.lib.solana_exact_validate"` 须成功。带 `MPLCONFIGDIR=$HOME/.matplotlib`。`test_batch3_solana_vertical_slice.py` 沙箱不能 bind loopback 时记 SANDBOX-BLOCKED。离线施工。
- 0.8 **边做边 commit**（每节一个，message 前缀 `W1(n):`），不 push。§3 登记是**代码 commit 之后的独立 commit**。
- 0.9 `W1_done.md`：改动清单（文件:行）、与工单差异、定向测试尾行、红证据、自报是否读过禁读路径。

## 1. 改动 A：交易版本上限常量化

### 1.1 常量落点 `scripts/lib/solana_attested_session.py`
唯一仓库内依赖是 `endpoint_identity`（`:10`，锚 `from endpoint_identity import public_endpoint, redact_endpoint_text`）。
- `:10` 改为 try/except 包导入回退（照 `solana_exact_validate.py:26-29`：先绝对导入，`ImportError` 回退 `from .endpoint_identity import …`）。
- `:18`（锚 `SOLANA_MAINNET_GENESIS_HASH = `）之后新增：
```python
# Solana 主网 2026-09 起出现版本 1 交易；本仓库所有 getBlock/getTransaction 请求声明的最高交易版本。
# 升此值、或改动修复请求模板（repair_getblock_body）任何字段语义时，须同步改 sqd_gap_repair.py 的版本钉
# （使 producer 换代并在 producer_history 登记）并记 CHANGELOG。
SOLANA_MAX_SUPPORTED_TX_VERSION = 1
```

### 1.2 去重：修复请求模板只留一份
- `scripts/lib/solana_exact_validate.py:1208-1216`（锚 `def _repair_getblock_params_digest(slot):`）与 `scripts/solana/sqd_gap_repair.py:627-633`（锚 `def _rpc_body(slot):`）是同一模板两份拷贝。validator 内新增 `repair_getblock_body(slot, max_version=SOLANA_MAX_SUPPORTED_TX_VERSION)` 返回 body dict；`_repair_getblock_params_digest(slot, max_version=SOLANA_MAX_SUPPORTED_TX_VERSION)` 改为其 digest。`sqd_gap_repair.py` 的 `_rpc_body(slot)` 改为 `return repair_getblock_body(slot)`（`:27` 已 `from solana_exact_validate import …`，加名字），删除本地模板。
- `solana_exact_validate.py` 增 `from solana_attested_session import SOLANA_MAX_SUPPORTED_TX_VERSION`（照 `:26-29` try/except 写法）。
- **producer 换代钉**（`sqd_gap_repair.py` 模块级、import 之后）：
```python
# 版本钉：共享常量/请求模板变化不会改变本脚本 sha（:607-608 只哈希本文件）。升 SOLANA_MAX_SUPPORTED_TX_VERSION
# 或改 repair_getblock_body 任何字段语义时必须改这里 ⇒ producer 换代 ⇒ producer_history 登记。
if SOLANA_MAX_SUPPORTED_TX_VERSION != 1:
    raise RuntimeError("repair producer tx-version pin must be updated")
```
（用 if/raise，不用 `assert`；不要写成 `X = SOLANA_MAX_SUPPORTED_TX_VERSION` 之类使检查失效的形式。）

### 1.3 其余 15 处字面量改引用常量（施工前基线 17 处；施工后 grep 命中数不再要求等于 17）
| 文件 | 行 | 处理 |
|---|---|---|
| `scripts/lib/solana_observation.py` | 270 | `:19` 已 `from solana_attested_session import (…` → 加名字 |
| `scripts/solana/probe_window_moves.py` | 121 | `:25` 已 `sys.path.insert(0, … / "lib")` → 其后加 `from solana_attested_session import SOLANA_MAX_SUPPORTED_TX_VERSION` |
| `scripts/solana/fast_probe_tops.py` | 54 | 同上（`:15`） |
| `scripts/solana/decode_txs.py` | 39 | `:8` 已 `import argparse, json, sys, time`、`:9` Path、`:11` 导入 decode_txs_v2；无显式 lib 路径 → `:9` 后加 `sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))` ＋ import |
| `scripts/solana/decode_txs_v2.py` | 295、340 | `:24` 已有 lib path |
| `scripts/solana/whale_deep.py` | 64、154 | `:22` |
| `scripts/solana/audit_closed_accounts.py` | 230、419、482 | `:40` |
| `scripts/solana/gas_origin.py` | 81 | `:18` |
| `scripts/solana/stake_decode.py` | 96 | `:22` |
| `scripts/solana/probe_escrows.py` | 150 | `:20` |
| `scripts/solana/trace_wallet.py` | 76 | `:14` |

### 1.4 守卫
- `scripts/tests/invariant_scan.py`：照 `bare_rpc_pool_errors`（`:337`）新增 `hardcoded_tx_version_errors(*, files=None, root=ROOT)`：AST 扫 `production_files()`，`ast.Dict` 键为常量字符串 `"maxSupportedTransactionVersion"` 且值为数字 `ast.Constant` 即报错（文件:行）；接入 `:1330`（锚 `errors += bare_rpc_pool_errors()`）同一汇总路径。
- `scripts/tests/test_batch4_invariant_guards.py`：照 `:25-32` 的极小源码样本写法加一条注入测试（临时文件含 `{"maxSupportedTransactionVersion": 0}` 报错；含常量引用不报错）。

## 2. 改动 B：`repair --resume --adopt-pending <旧 pending 目录>`

### 2.1 契约
认领＝**可信输入的结构迁移**。前提：旧 pending 是本案本 mint 的 repair parent 内、由 `producer_history` 登记的 ACTIVE 前代 producer 产出、自身未被认领过的直接前代，其冻结摘要物料（base 两哈希、coverage probe_id/map_sha256、候选集合、mode、参考源 kind/指纹）与当前 plan 一致、仅 producer.sha256 不同。动作：把其台账「成功前缀中证据对齐的最长前缀」逐行迁入新 pending，header 留可复验 `adopted` 记录；随后普通 `--resume` 只补拉剩余 slot。**不改旧目录任何字节、不改台账行字段值、不重编 seq。** 措辞纪律：**来源可信是输入前提**；目录归属检查与深验只验证本案归属及结构/内容一致性，不提供来源真实性或对抗性证明（文档照此）。

### 2.2 CLI 与入口（`sqd_gap_repair.py`）
- `:1544`（锚 `item.add_argument("--resume", action="store_true")`）旁增 `item.add_argument("--adopt-pending")`。
- 规则：须与 `--resume` 同给（否则 `ValueError("--adopt-pending requires --resume")`）；目标 `pending/rpc_ledger.jsonl` **必须不存在**（否则 `ValueError("adopt requires no target ledger")`——含提交完成后的重复认领：此时用普通 `--resume`）。
- 接线：`:1273-1276`（锚 `pending.mkdir(exist_ok=args.resume)` … `evidence_dir.mkdir(exist_ok=True)`）之后、`_live_payloads`（`:961`）之前调用 `adopt_predecessor_pending(Path(args.adopt_pending), pending, plan, parent)`；`:1234-1269` 已发布代恢复分支不改（其复验由 §2.5 深验覆盖）。
- 新增 import：`from producer_history import historical_producer_hashes  # noqa: E402`（LIB 已在 `:20` 进 sys.path）、`import errno`、`import shutil`；`:26`（锚 `from receipt_kernel import publish_exclusive, publish_overwrite`）加 `RawBytes`。

### 2.3 校验与迁入（fail-closed）
`adopt_predecessor_pending(old, pending, plan, parent)`，分「预验」与「提交」两阶段；**预验阶段任一失败 `ValueError` 且产物状态不变**（允许入口已建的空 `pending/evidence` 目录存在）：
1. 归属：`old.resolve()` 是目录、`old.resolve().parent == parent.resolve()`、`old` 自身非符号链接、`old.resolve() != pending.resolve()`、名字形如 `pending-<16hex>`。
2. 旧台账**纯读取**：从 `_read_ledger_prefix`（`:682-706`；`:703` `handle.write(clean)` 会重写文件）抽出纯解析 `_parse_ledger_prefix(raw: bytes) -> rows`（残缺尾行只在内存忽略），`_read_ledger_prefix` 改为调它后再落盘；认领只用 `_parse_ledger_prefix(old_ledger.read_bytes())`。`rows` 非空；`rows[0]["schema"] == "sqd-solana-rpc-ledger/v1"`；`rows[0]["plan_digest"]` == 目录名后缀；`rows[0]["reference"] == _ledger_header(plan)["reference"]`；`"adopted" not in rows[0]`。
3. 前代可复现：`candidates = historical_producer_hashes("scripts/solana/sqd_gap_repair.py", "sqd-solana-repair-bundle/v1") - {plan["producer"]["sha256"]}`；逐 sha 深拷贝 plan、置 `producer.sha256`、`compute_plan_digest(副本) == rows[0]["plan_digest"]` 者为 `predecessor_sha`；无命中 → `ValueError("adopt: predecessor plan_digest is not reproducible from a registered producer")`。
4. 行/证据对齐：把 `load_resume_slots`（`:716-757`）拆为 `_verify_ledger_rows(pending, data_rows, header) -> completed`（`:727-757` 逻辑，**入参是不含 header 的数据行**）＋外壳 `load_resume_slots(pending, header, plan=None)`（返回 `(completed, data_rows)`，**两参数调用兼容**，`test_batch8_repair_scale.py:203-204`；`plan=None` 只允许无 `adopted` 的台账，含 `adopted` 而无 plan → `ValueError`）。`:750-751`（锚 `expected_params = sha256_bytes(canonical_json(_rpc_body(slot)))`）改为接受集合 `{_repair_getblock_params_digest(slot, v) for v in range(SOLANA_MAX_SUPPORTED_TX_VERSION + 1)}`——语义：**同一请求模板下显式声明版本 0..当前、且成功返回完整区块的历史证据**可继续作为原请求的证据；旧行保留自己的 params_digest 与 result_sha256。采纳集＝旧数据行中从头连续、每行被判 completed 的最长前缀（首个未对齐行即止）；采纳行的 slot 序列必须是 `plan["candidate_slots"]`（`:595-596` 排序去重后的列表）的**前缀**（否则 `ValueError("adopt: adopted slots are not a candidate prefix")`）；采纳 0 行 → `ValueError("adopt: no adoptable prefix")`。
5. 目标冲突预验（**在任何 link/copy 之前**遍历全部采纳 slot）：`pending/evidence/<slot>.sqd.json`/`.ref.json` 若已存在，必须与旧文件 JSON 相等，否则 `ValueError("adopt: target evidence conflicts")`。
6. 提交阶段：逐份 `os.link(src, dst)`（dst 已存在且相等则跳过）；仅 `OSError` 且 `errno == errno.EXDEV` 时回退 `shutil.copy2` 并复核 sha256 相等，其他 `OSError` 原样抛出。全部证据就位后用**原子发布**写台账：`publish_exclusive(pending / "rpc_ledger.jsonl", RawBytes(_jsonl_bytes([new_header] + 采纳行)))`（`receipt_kernel.py:574-587` 先暂存 fsync 再硬链接发布），再 `_fsync_dir(pending)`（`:196`）。`_jsonl_bytes` 重新 canonical 编码：**行字段值不变、字节可不同**。
7. 恢复边界：台账提交前中断 → 目标 ledger 仍不存在，重跑同一 `--resume --adopt-pending` 命令即可（证据 link 幂等）；提交后中断 → 改用普通 `--resume`。
8. 硬链接边界（文档照写）：新旧 pending 的采纳证据共享 inode；发布后 evidence_manifest 深验（`solana_exact_validate.py:1357-1361` → `_repair_ref:892-904` 重算大小与哈希）能发现任何一侧的后续改写，但不能隔离它——本流程及任何后续流程**禁止原地改写已链接证据**（只允许删除目录项或原子替换）。
9. `new_header = _ledger_header(plan)` 加 `"adopted": {"predecessor_plan_digest": rows[0]["plan_digest"], "predecessor_producer_sha256": predecessor_sha, "rows": n, "source": old.name, "ts": int(time.time())}`。

### 2.4 生产者侧复验
新增 `_verify_adopted_record(header, data_rows, plan)`（`data_rows` 不含 header）：`adopted` 为 dict、键集恰为 `{predecessor_plan_digest, predecessor_producer_sha256, rows, source, ts}`、digest 为 16hex 且 `!= header["plan_digest"]`、sha 为 64hex 且 `∈ historical_producer_hashes(...repair-bundle/v1)`、rows 为正 int（排除 bool）且 `<= len(data_rows)`、source 为 str、ts 为 int；**重算**：深拷贝 plan 置 `producer.sha256 = sha` 后 `compute_plan_digest == predecessor_plan_digest`；前 `rows` 行 params_digest ∈ 接受集合。
- `:724-726`（锚 `or rows[0] != header:`）与 `:1401`（锚 `if not complete_rows or complete_rows[0] != ledger_header:`）：比较改为「去掉 `adopted` 后相等」；含 `adopted` 时调 `_verify_adopted_record`（`:972` 处 `_live_payloads` 调 `load_resume_slots` 时传入其已有的 `plan` 参数 `:962`）。

### 2.5 深验 `scripts/lib/solana_exact_validate.py`
- `:1533`（锚 `or ledger_row.get("params_digest") != _repair_getblock_params_digest(slot) \`）改为「不在 0..当前接受集合」。
- 参考源指纹等式：在 `:1328-1331`（锚 `"params_digest", "endpoint_fingerprint",`）所在的数据行循环内就地比较 `row["endpoint_fingerprint"] == ledger_header["reference"]["endpoint_fingerprint"]`，且 header 该值 `== bundle["reference"]["endpoint_fingerprint"]`；否则 `reasons.append("RPC ledger reference fingerprint mismatch")`。
- `adopted`：结构检查放在 header 读取附近（键集/格式/rows ≤ 数据行数，同 §2.4）；**摘要重算放在 `:1457`**（锚 `all_candidates = set(plan_candidates["coverage"]) | set(`）之后、仅当 header 含 `adopted` 时执行。validator **不导入** `sqd_repair_core`（`:9-10`、`:1221` 要求独立于 producer；隔离进程实测 core 依赖 `spl_edge_core` 不可达），改为私有函数 `_plan_digest_from_generation(bundle, resolution, producer_sha256)`：按 `sqd_repair_core.py:65-82` 的物料结构与 16hex 截断独立实现（注释指向原函数），复用本文件 `canonical_json:50`/`sha256_bytes:66`。键映射固定：`base.edge_sha256`/`base.meta_sha256` ← `bundle.base`（写出 `sqd_gap_repair.py:1436-1437`）；`coverage.probe_id` ← `bundle.coverage.probe_id`（`:1441`）；`coverage.map_sha256` ← **`bundle.coverage.map.sha256`**（`:1442-1443` 经 `_file_ref`）；`candidate_slots` ← `sorted(set(resolution.plan_candidates.coverage) | set(resolution.plan_candidates.beta))`（`:1346`；validator `:1434-1457` 已校验形状）；`mode` ← `bundle.mode`；`reference.kind`/`endpoint_fingerprint` ← `bundle.reference`（`:1451`）；`producer.sha256` ← 参数。验证：`_plan_digest_from_generation(…, bundle.producer.sha256) == bundle.plan_digest` 且 `_plan_digest_from_generation(…, adopted.predecessor_producer_sha256) == adopted.predecessor_plan_digest`；前 `rows` 行 params_digest ∈ 接受集合；缺键/形状错转为 `reasons.append("RPC ledger adopted record invalid")`，不泄漏 `KeyError/TypeError`。

### 2.6 不做
不改 `compute_plan_digest`/gid 物料/bundle 顶层键；不读 STOPPED.json；不删旧 pending；不支持多代链式认领；不新建通用迁移框架或共享模块。

## 3. 登记 `scripts/lib/producer_history.py`
代码 commit 落定后取 `git show <代码commit>:scripts/solana/sqd_gap_repair.py | shasum -a 256`，照 `:204-233`（四条 `4c5cd578…`）格式追加 4 条（协议 `sqd-solana-cache/v4`、`sqd-solana-repair-bundle/v1`、`sqd-solana-coverage-resolution/v1`、`sqd-solana-repair-pointer/v1`），reason：`9.1.0 registers the tx-version-1 producer (SOLANA_MAX_SUPPORTED_TX_VERSION + --adopt-pending); predecessor 25f04ff1… stays ACTIVE for adoption.` 旧哈希 `25f04ff10bc494be977e4c5b3193c3a928c0764fa529d8d5a47563fe2a825e66` 保持 ACTIVE。`test_producer_registry_current.py`（`:43-50`）PASS。

## 4. 测试 `scripts/tests/test_sqd_gap_repair.py`
在 `batch3b_semantic_regressions()`（`:611`）E27(a)（`:712-768`，止于锚 `assert interrupted_pointer["gid"] == uninterrupted_pointer["gid"]`）之后加 **E27(d)**，复用 `build_batch3b_case`（`:165`）、`repair_slot_responses`（`:229`）、`write_repair_fixture`（`:391`）与 E27(a) 手法；行数不硬压。
- 取 plan：`fp = repair.reference_endpoint_identity("fixture://helius")["sha256"]`（字面值取 `:1601`）；`plan, _, _ = repair._plan(case, MINT, reference_fingerprint=fp)`（`:584`，blocks_cache/beta 与 CLI 一致）；前代用真实 ACTIVE sha `OLD = 25f04ff1…`：`previous = deepcopy(plan); previous["producer"]["sha256"] = OLD; previous["plan_digest"] = repair.compute_plan_digest(previous)`。
- 造旧 pending：跑到配额 exit 3 留一行后，改名 `pending-<previous digest>`、header plan_digest 改前代值、行 params_digest 改版本 0 模板 digest。**已采纳 slot 的响应不得含 version 1 交易**（历史版本 0 成功证据前提）。
- 正向：`repair … --resume --adopt-pending <旧>` 用不含已采纳 slot 的 fixture 跑完 exit 0；发布 gen 台账 header 含 `adopted`（rows=1、sha=OLD）、旧行字段值原样、新行 params_digest 为版本 1 模板；`validate_repair_bundle_deep` PASS；认领前后对旧 `rpc_ledger.jsonl` 与证据取 sha256 相等。
- **独立验证版本 1 行为**：新拉取的第二个 slot 的 fixture 响应含一笔 `version: 1`、`message.transactionConfig` 的交易；用 transport 夹具（或 monkeypatch `reference_pool.get_block`）**独立断言**实际送出的 body `maxSupportedTransactionVersion == 1`；新行 params_digest 与一个**测试内显式写定**（不经 `_rpc_body`）的版本 1 body digest 相等。
- 残尾只读：旧台账追加残缺尾行（如 `{"seq":`）后认领仍成功，认领前后旧 ledger 字节哈希不变。
- 最长前缀：旧台账两行、首行对齐、第二行 `.ref.json` 的 `raw_response_sha256` 改坏 → 只采纳首行（rows=1），第二个 slot 由 fixture 补拉。
- 入口负向（断言「失败前后目标状态不变」）：①**未登记 producer**：取一个确认不在 ACTIVE 集的 64hex sha，代入当前 plan 算 digest，同步更名旧目录与 header → 拒；②旧 header.reference.endpoint_fingerprint 改动 → 拒；③目标 ledger 已存在（只有 header）→ 拒，且该 ledger 字节不变；④旧 `.ref.json` `raw_response_sha256` 改坏（单行）→ `no adoptable prefix`；⑤不带 `--resume` → 拒；⑥旧目录拷贝到别的 parent → 拒；⑦旧 header 自带 `adopted` → 拒；⑧候选集外 slot：同步改该行 slot、params_digest、两份证据文件名及其内 slot 使身份检查全部对齐，再断言候选前缀检查拒绝。
- 预验/提交边界：⑨目标 evidence 里预置与旧文件不等的 `<slot>.sqd.json`（第二个采纳 slot）→ 预验拒绝且第一个 slot 的文件未被 link；⑩提交前中断：monkeypatch `publish_exclusive` 抛异常 → 目标 ledger 不存在、证据已 link，重跑同命令成功。
- 同步篡改边界（明确记为信任边界，不断言必拒）：同时改行 `result_sha256` 与 `ref.raw_response_sha256` 为同一伪值 → 认领通过，注释说明这属于来源可信前提。
- 深验负向（改文件后同步更新 `bundle.rpc_ledger` 的 size/sha256；`compute_gid:90-92` 排除 rpc_ledger 故不必重算 gid）：①`adopted.predecessor_producer_sha256` 改未登记值 → FAIL 含 "adopted record invalid"；②`adopted.predecessor_plan_digest` 改另一 16hex → 同 FAIL；③某数据行 `endpoint_fingerprint` 改动 → FAIL 含 "reference fingerprint mismatch"；④与 core 一致性：对发布 gen 断言 `_plan_digest_from_generation(bundle, resolution, bundle.producer.sha256) == repair.compute_plan_digest(plan)`。

## 5. 文档（中文，只改既有条目）
- `references/scan-schemas.md` §14.8（`:998-1023`）：表内加「`header.adopted` | object | 否 | 可选；存在时下列五子字段全部必填」＋五行 `header.adopted.{predecessor_plan_digest, predecessor_producer_sha256, rows, source, ts}`（说明：认领自同 parent、登记 ACTIVE 前代 producer 的 pending；续跑/发布/深验均重算前代 digest；来源可信是输入前提，目录归属与深验只验证本案归属及一致性；采纳证据与旧 pending 共享 inode，禁止原地改写）；不变量 `:1021` 改为「resume 以 (plan_digest, params_digest ∈ 同模板显式版本 0..`SOLANA_MAX_SUPPORTED_TX_VERSION` 集, result_sha256) 判完成；header.adopted 存在时其前 rows 行迁自前代 pending，字段值不变、seq 连续」。
- `references/data-pipeline-solana-capture.md:198`（锚 `2. \`sqd_gap_repair.py/v1\` 只修已确认缺陷`）句末补：「producer 升版后同案旧 pending 可经 `--resume --adopt-pending <旧目录>` 认领（前代 sha 须在 producer_history 登记、台账 header 记 `adopted`、深验重算前代 digest；来源可信是前提）；Solana 请求的交易版本上限统一取 `SOLANA_MAX_SUPPORTED_TX_VERSION`，升版本或改修复请求模板须同步换代 producer。」
- `CHANGELOG.md`：索引与正文加 **9.1.0**（次版本：新公开接口 `--adopt-pending`＋契约扩展 `header.adopted`；常量化与 v1 修复）；先 `changelog_lint.py`。
- `VERSION`→`9.1.0`；`pyproject.toml:15`、`SKILL.md:23` 同步；`test_version_consistency.py` PASS。

## 6. 不含（调度方在案卷侧做）
PYTHIA 案内脚本同款字面量、案运行时重钉、实际 `--adopt-pending` 续跑、Helius 额度核查。
