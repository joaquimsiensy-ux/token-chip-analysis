# 工单 W1 v2 — Solana 交易版本上限常量化 ＋ 修复产物「前代认领」机制（→ 9.1.0）

> v1→v2 变更（吸收 codex 复核 r1 `review_W1_r1_report.md` 12 条）：①锚点订正（session 依赖表述、E27(a) 止于 `:768`、守卫汇总 `:1330`、17 处仅为施工前基线）；②认领契约改为「冻结摘要物料一致」＋「同案 repair parent 内、未被认领过的直接前代」，明确为可信输入的结构迁移，不承诺对抗性来源证明；③旧台账**纯读取**不落盘；④目标 `rpc_ledger.jsonl` 必须不存在；先全量预验再迁入；⑤硬链接保留（磁盘只剩 42 GiB，PYTHIA 证据 39 GB 不可复制；同卷 `st_dev` 校验，跨卷回退复制）；⑥验证器带 plan/行上下文，兼容旧两参数调用；⑦深验**重建摘要物料**重算当前与前代 digest，补参考源指纹等式；⑧版本等价措辞收窄为「同模板显式 0/1 的历史成功证据」；⑨修 session 包导入回退，加 producer 换代触发器；⑩测试用真实前代 sha＋`_plan` 取计划，补篡改/跨案/重复认领/源不变向量；⑪文档只改既有条目；⑫0.7 补回归项与隔离导入检查。
>
> 背景（调度方亲核，案卷数字为外部背景）：Solana 主网已出现交易版本 1（slot 447210248：`maxSupportedTransactionVersion: 0` 报 -32015；改 1 返回 851 笔含 1 笔 v1，v1 消息体多 `transactionConfig`；Helius 对 2/255 也接受）。钉版 skill 13 文件 17 处写死 0；`sqd_gap_repair.py:892` 遇 v1 直接 `ValueError`。改脚本 ⇒ `producer.sha256` 变 ⇒ `plan_digest` 变（`sqd_repair_core.py:80`）⇒ 旧 pending 无法 `--resume`。用户裁决：修常量＋加「经审计的前代产物认领」；原则**能删不加、能改不加、references/SKILL.md 上下文尽量不增**。

## 0. 纪律

- 0.1 开工 `git status --short` 为空、分支 `fix/solana-txv1`；本仓库是克隆，**不 push、不动 main**。
- 0.2 **禁读 `~/.codex`**（启动自动披露除外）；禁读 `~/Documents`、`~/Desktop`。
- 0.3 **白名单（可写）**：
  - 生产：`scripts/lib/solana_attested_session.py`、`scripts/lib/solana_exact_validate.py`、`scripts/lib/solana_observation.py`、`scripts/solana/sqd_gap_repair.py`、`scripts/solana/{probe_window_moves,fast_probe_tops,decode_txs,decode_txs_v2,whale_deep,audit_closed_accounts,gas_origin,stake_decode,probe_escrows,trace_wallet}.py`、`scripts/lib/producer_history.py`
  - 测试：`scripts/tests/test_sqd_gap_repair.py`、`scripts/tests/invariant_scan.py`、`scripts/tests/test_batch4_invariant_guards.py`
  - 文档：`references/scan-schemas.md`（仅 §14.8 表与不变量）、`references/data-pipeline-solana-capture.md`（仅「正式产物窄门」第 2 条句末）、`CHANGELOG.md`
  - 版本：`VERSION`、`pyproject.toml:15`、`SKILL.md:23`
  - 报告：本目录 `W1_done.md`、`W1_red_evidence.txt`
- 0.4 **不改**：`scripts/solana/sqd_repair_core.py`、`scripts/solana/sqd_cache_identity.py`、`scripts/solana/replay_edges.py`、`scripts/tests/test_producer_registry_current.py`、`test_batch8_repair_scale.py`、`test_batch7_validator_coverage_gaps.py`、`test_version_consistency.py`（均须原样 PASS）、`commands-staging/*`、`invariant_manifest`/`contract_manifest`。
- 0.5 行号与实况不符即停工写报告（行号旁均附锚文本，行号为施工前基线 `813ca6d`）。
- 0.6 先红后绿 `W1_red_evidence.txt`：①基线 grep/AST 证明 13 文件 17 处字面量 0；②基线 `repair --help`（或 argparse 解析）无 `--adopt-pending`；③基线 `load_resume_slots` 对 params_digest 为版本 1 模板的行不计入 completed；④隔离进程 `python3 -c "import scripts.lib.solana_attested_session"` 在基线报 `No module named 'endpoint_identity'`。
- 0.7 **不跑 `run_all.py`**（调度方本机跑）。定向跑全部 PASS 并贴尾行：`test_sqd_gap_repair.py`、`test_batch8_repair_scale.py`、`test_batch7_validator_coverage_gaps.py`、`test_producer_registry_current.py`、`test_version_consistency.py`、`test_batch4_invariant_guards.py`、`invariant_scan.py`、`test_r9_solana_attested_session.py`、`test_r9_batch2_solana_sqd_adapter.py`、`test_sqd_coverage_probe.py`、`test_batch2d_stream_tail.py`、`test_f03_sharedmap_reuse.py`、`test_reconcile_v4_receipt.py`、`test_batch3c_census_fields.py`、`test_batch3_solana_producers.py`、`test_sqd_collector_meta_v4.py`、`test_sqd_consumer_v4.py`、`test_r9_batch3_solana_observation.py`、`test_review_solana_integrity.py`、`test_param_scripts.py`、`test_repair_batch1.py`、`test_repair_batch_d.py`、`changelog_lint.py`、`docs_lint.py --all`；另隔离进程 `python3 -c "import scripts.lib.solana_attested_session, scripts.lib.solana_exact_validate"` 须成功。带 `MPLCONFIGDIR=$HOME/.matplotlib`。`test_batch3_solana_vertical_slice.py` 沙箱不能 bind loopback 时记 SANDBOX-BLOCKED 由调度方补验。离线施工。
- 0.8 **边做边 commit**（每节一个，message 前缀 `W1(n):`），不 push。§3 登记是**代码 commit 之后的独立 commit**。
- 0.9 `W1_done.md`：改动清单（文件:行）、与工单差异、定向测试尾行、红证据、自报是否读过禁读路径。

## 1. 改动 A：交易版本上限常量化

### 1.1 常量落点 `scripts/lib/solana_attested_session.py`
唯一仓库内依赖是 `endpoint_identity`（`:10`，锚 `from endpoint_identity import public_endpoint, redact_endpoint_text`；另有标准库、可选 certifi、导入时建 SSL context）。
- `:10` 改为 try/except 包导入回退（照 `solana_exact_validate.py:26-29` 写法：先 `from endpoint_identity import …`，`ImportError` 回退 `from .endpoint_identity import …`），使 `import scripts.lib.solana_attested_session` 在隔离进程可用。
- `:18`（锚 `SOLANA_MAINNET_GENESIS_HASH = `）之后新增：
```python
# Solana 主网 2026-09 起出现版本 1 交易；本仓库所有 getBlock/getTransaction 请求声明的最高交易版本。
# 升此值时须同步改 sqd_gap_repair.py 的 REPAIR_TX_VERSION（使 producer 换代并登记）并记 CHANGELOG。
SOLANA_MAX_SUPPORTED_TX_VERSION = 1
```

### 1.2 去重：修复请求模板只留一份
- `scripts/lib/solana_exact_validate.py:1208-1216`（锚 `def _repair_getblock_params_digest(slot):`）与 `scripts/solana/sqd_gap_repair.py:627-633`（锚 `def _rpc_body(slot):`）是同一模板两份拷贝。validator 内新增 `repair_getblock_body(slot, max_version=SOLANA_MAX_SUPPORTED_TX_VERSION)` 返回 body dict；`_repair_getblock_params_digest(slot, max_version=SOLANA_MAX_SUPPORTED_TX_VERSION)` 改为其 digest。`sqd_gap_repair.py` 的 `_rpc_body(slot)` 改为 `return repair_getblock_body(slot)`（`:27` 已 `from solana_exact_validate import …`，加名字），删除本地模板。
- `solana_exact_validate.py` 增 `from solana_attested_session import SOLANA_MAX_SUPPORTED_TX_VERSION`（照 `:26-29` try/except 写法）。
- **producer 换代触发器**：`sqd_gap_repair.py` 模块级加 `REPAIR_TX_VERSION = 1` 与 `if REPAIR_TX_VERSION != SOLANA_MAX_SUPPORTED_TX_VERSION: raise RuntimeError("REPAIR_TX_VERSION must be bumped with SOLANA_MAX_SUPPORTED_TX_VERSION")`（因 `:607-608` 只哈希本脚本，共享常量升级不会改变 producer.sha256；此触发器强制升版本时改本脚本 ⇒ 换代 ⇒ 登记）。

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
- `scripts/tests/test_batch4_invariant_guards.py`：照 `:25-32` `test_bare_rpc_pool_injection` 的**极小源码样本**写法加一条注入测试（临时文件含 `{"maxSupportedTransactionVersion": 0}` 报错；含常量引用不报错）。

## 2. 改动 B：`repair --resume --adopt-pending <旧 pending 目录>`

### 2.1 契约（一句话）
认领＝**可信输入的结构迁移**：旧 pending 必须位于当前案、当前 mint 的同一 repair parent 内，由 `producer_history` 登记的 ACTIVE 前代 producer 产出（冻结摘要物料——base 两哈希、coverage probe_id/map_sha256、候选集合、mode、参考源 kind/指纹——与当前 plan 完全一致，仅 producer.sha256 不同），且自身未被认领过；把其台账「成功前缀中证据对齐的最长前缀」逐行迁入新 pending，header 留可复验的 `adopted` 记录；随后普通 `--resume` 只补拉剩余 slot。**不改旧目录任何字节、不改台账行字段值、不重编 seq。** 来源真实性由案卷目录归属与既有深验保证，本机制不提供对抗性来源证明（文档照此措辞）。

### 2.2 CLI 与入口（`sqd_gap_repair.py`）
- `:1544`（锚 `item.add_argument("--resume", action="store_true")`）旁增 `item.add_argument("--adopt-pending")`。
- 规则：须与 `--resume` 同给（否则 `ValueError("--adopt-pending requires --resume")`）；目标 `pending/rpc_ledger.jsonl` **必须不存在**（否则 `ValueError("adopt requires no target ledger")`）。
- 接线：`:1273-1276`（锚 `pending.mkdir(exist_ok=args.resume)` … `evidence_dir.mkdir(exist_ok=True)`）之后、`_live_payloads`（`:961`）之前调用 `adopt_predecessor_pending(Path(args.adopt_pending), pending, plan, parent)`；`:1234-1269` 已发布代恢复分支不受影响（其复验由 §2.5 深验覆盖）。
- 新增 import：`from producer_history import historical_producer_hashes  # noqa: E402`（LIB 已在 `:20` 进 sys.path）、`import shutil`。

### 2.3 校验（fail-closed；任一不满足 `ValueError`，且**此前零落盘**）
`adopt_predecessor_pending(old, pending, plan, parent)`：
1. 归属：`old.resolve()` 是目录、其父目录 `== parent.resolve()`（同案同 mint repair parent）、`old` 非符号链接、`old.resolve() != pending.resolve()`、名字形如 `pending-<16hex>`。
2. 旧台账**纯读取**：从 `_read_ledger_prefix`（`:682-706`，锚 `handle.write(clean)` 在 `:703` 会重写文件）抽出纯解析函数 `_parse_ledger_prefix(raw_bytes) -> rows`（残缺尾行只在内存忽略），`_read_ledger_prefix` 改为调它后再落盘；认领只用 `_parse_ledger_prefix(old_ledger.read_bytes())`。`rows` 非空；`rows[0]["schema"] == "sqd-solana-rpc-ledger/v1"`；`rows[0]["plan_digest"]` == 目录名后缀；`rows[0]["reference"] == _ledger_header(plan)["reference"]`；`"adopted" not in rows[0]`（只认未被认领过的直接前代）。
3. 前代可复现：`candidates = historical_producer_hashes("scripts/solana/sqd_gap_repair.py", "sqd-solana-repair-bundle/v1") - {plan["producer"]["sha256"]}`；对每个 sha 深拷贝 plan、`producer.sha256 = sha`、`compute_plan_digest(副本) == rows[0]["plan_digest"]` 者即前代 sha（记为 `predecessor_sha`）；无命中 → `ValueError("adopt: predecessor plan_digest is not reproducible from a registered producer")`。
4. 行/证据对齐：把 `load_resume_slots`（`:716-757`）拆为 `_verify_ledger_rows(pending, rows, header, plan=None) -> completed`（`:727-757` 逻辑）＋外壳 `load_resume_slots(pending, header, plan=None)`（**保持两参数调用兼容**，`test_batch8_repair_scale.py:203-204` 仍按两参数调用）。`:750-751`（锚 `expected_params = sha256_bytes(canonical_json(_rpc_body(slot)))`）改为接受集合 `{_repair_getblock_params_digest(slot, v) for v in range(SOLANA_MAX_SUPPORTED_TX_VERSION + 1)}`——语义：**同一请求模板下显式声明版本 0..当前、且成功返回完整区块的历史证据**均可继续作为原请求的证据；旧行保留自己的 params_digest 与 result_sha256，不改写成新请求。采纳集＝旧 `rows[1:]` 中从头连续、每行被判 completed 的最长前缀（首个未对齐行即止）；每个采纳 slot 必须 `∈ set(plan["candidate_slots"])`（否则 `ValueError`）；采纳 0 行 → `ValueError("adopt: no adoptable prefix")`。
5. 全量预验后再迁入：对每个采纳 slot 的两份证据，`os.link(src, dst)`（先校验 `os.stat(old).st_dev == os.stat(pending).st_dev`；`OSError` 跨卷回退 `shutil.copy2` 并复核 sha256 相等）；`dst` 已存在则 JSON 相等否则 `ValueError`。然后 `_publish_bytes_exclusive(pending/"rpc_ledger.jsonl", _jsonl_bytes([new_header] + 采纳行))`（`_jsonl_bytes` 重新 canonical 编码：**行字段值不变、字节可不同**，文档照此写）。中断恢复：目标 ledger 不存在即可重跑认领（幂等：同源同前缀）。
6. `new_header = _ledger_header(plan)` 加 `"adopted": {"predecessor_plan_digest": rows[0]["plan_digest"], "predecessor_producer_sha256": predecessor_sha, "rows": n, "source": old.name, "ts": int(time.time())}`（`source` 只记目录名，不记绝对路径）。

### 2.4 生产者侧复验（两处共用）
新增 `_verify_adopted_record(header, rows, plan)`：`adopted` 为 dict、键集恰为 `{predecessor_plan_digest, predecessor_producer_sha256, rows, source, ts}`、digest 为 16hex 且 `!= header["plan_digest"]`、sha 为 64hex 且 `∈ historical_producer_hashes(...repair-bundle/v1)`、rows 为正 int（排除 bool）且 `<= len(rows)`、source/ts 类型正确、**重算**：深拷贝 plan 置 `producer.sha256 = sha` 后 `compute_plan_digest == predecessor_plan_digest`；前 `rows` 行 params_digest 必须 ∈ 接受集合（旧模板）。
- `:724-726`（锚 `or rows[0] != header:`）与 `:1401`（锚 `if not complete_rows or complete_rows[0] != ledger_header:`）：比较改为「去掉 `adopted` 后相等」；台账 header 含 `adopted` 时调 `_verify_adopted_record`（`:1401` 处有 plan；`load_resume_slots` 需 plan 时由 `_live_payloads` 传入——`plan` 已是其参数 `:962`）。

### 2.5 深验 `scripts/lib/solana_exact_validate.py`
- `:1533`（锚 `or ledger_row.get("params_digest") != _repair_getblock_params_digest(slot) \`）改为「不在 0..当前接受集合」。
- `:1297-1313` 附近：若 `ledger_header` 含 `adopted`：键集/格式/rows 上界同 §2.4；**重建摘要物料**（bundle.base 两哈希、bundle.coverage 的 probe_id/map_sha256、resolution.plan_candidates（或 bundle 内等价候选集，按 `sqd_gap_repair.py:1341-1347`、`:1430-1452` 写出的键实况取）、mode、reference.kind/endpoint_fingerprint、producer.sha256）用 `compute_plan_digest`（validator 需能导入 `sqd_repair_core`；若 lib 侧导入 `scripts/solana` 模块有层级问题，则在 validator 内复制 `:59-82` 的物料构造为私有函数并加注释指向原函数）验证：当前重算 == `bundle.plan_digest`，前代重算（换 `predecessor_producer_sha256`）== `predecessor_plan_digest`；前 `rows` 行 params_digest ∈ 接受集合；否则 `reasons.append("RPC ledger adopted record invalid")`。
- 参考源指纹等式（`:1328-1331` 附近）：`ledger_header.reference.endpoint_fingerprint == bundle.reference.endpoint_fingerprint`，且每数据行 `endpoint_fingerprint` 等于它；否则 `reasons.append("RPC ledger reference fingerprint mismatch")`。

### 2.6 不做
不改 `compute_plan_digest`/gid 物料/bundle 顶层键；不读 STOPPED.json；不删旧 pending；不支持多代链式认领。

## 3. 登记 `scripts/lib/producer_history.py`
代码 commit 落定后取 `git show <代码commit>:scripts/solana/sqd_gap_repair.py | shasum -a 256`，照 `:204-233`（四条 `4c5cd578…`）格式追加 4 条（协议 `sqd-solana-cache/v4`、`sqd-solana-repair-bundle/v1`、`sqd-solana-coverage-resolution/v1`、`sqd-solana-repair-pointer/v1`），reason：`9.1.0 registers the tx-version-1 producer (SOLANA_MAX_SUPPORTED_TX_VERSION + --adopt-pending); predecessor 25f04ff1… stays ACTIVE for adoption.` 旧哈希 `25f04ff10bc494be977e4c5b3193c3a928c0764fa529d8d5a47563fe2a825e66` 保持 ACTIVE。`test_producer_registry_current.py`（`:43-50`）PASS。

## 4. 测试 `scripts/tests/test_sqd_gap_repair.py`
在 `batch3b_semantic_regressions()`（`:611`）E27(a)（`:712-768`，止于锚 `assert interrupted_pointer["gid"] == uninterrupted_pointer["gid"]`）之后加 **E27(d)**，复用 `build_batch3b_case`（`:165`）、`repair_slot_responses`（`:229`）、`write_repair_fixture`（`:391`）与 E27(a) 手法；行数不硬压。
- 取 plan：`fp = repair.reference_endpoint_identity("fixture://…")["sha256"]`（照 `:1607` 的 CLI 同源设置）、`plan, _, _ = repair._plan(case, MINT, reference_fingerprint=fp)`（`:584`）；前代用**真实 ACTIVE sha** `25f04ff1…`：`previous = deepcopy(plan); previous["producer"]["sha256"] = OLD; previous["plan_digest"] = repair.compute_plan_digest(previous)`。
- 造旧 pending：跑到配额 exit 3 留一行后，改名为 `pending-<previous digest>`、header plan_digest 改前代值、行 params_digest 改版本 0 模板 digest（模拟旧 producer）。
- 正向：`repair … --resume --adopt-pending <旧>` 用**不含已采纳 slot** 的 fixture 跑完 exit 0；发布 gen 的台账 header 含 `adopted`（rows=1、sha=OLD）、旧行字段值原样、新行 params_digest 为版本 1 模板；`validate_repair_bundle_deep` PASS；旧目录字节不变（认领前后对旧 `rpc_ledger.jsonl` 与证据取 sha256 相等）。
- 入口负向（每条零落盘：目标 ledger 不存在、evidence 目录空）：①前代 sha 用未登记值（把旧 header digest 改为任意 16hex）→ 拒；②旧 header.reference.endpoint_fingerprint 改动 → 拒；③目标 ledger 已存在（哪怕只有 header）→ 拒；④旧 `.ref.json` `raw_response_sha256` 改坏 → 「no adoptable prefix」；⑤不带 `--resume` → 拒；⑥旧目录在别的 parent（拷贝到临时目录）→ 拒；⑦旧 header 自带 `adopted` → 拒；⑧采纳行 slot 不在候选集 → 拒。
- 深验负向（发布后改文件须同步更新 `bundle.rpc_ledger` 的 size/sha256，以隔离原因）：①`adopted.predecessor_producer_sha256` 改未登记值 → FAIL 含 "adopted record invalid"；②`adopted.predecessor_plan_digest` 改为另一 16hex（sha 仍真实）→ 同 FAIL（证明重算生效）；③某数据行 `endpoint_fingerprint` 改动 → FAIL 含 "reference fingerprint mismatch"。

## 5. 文档（中文，只改既有条目）
- `references/scan-schemas.md` §14.8（`:998-1023`）：表内加「`header.adopted` | object | 否 | 可选；存在时下列五子字段全部必填」＋五行 `header.adopted.{predecessor_plan_digest, predecessor_producer_sha256, rows, source, ts}`（说明：认领自同 parent、登记 ACTIVE 前代 producer 的 pending；续跑/发布/深验均重算前代 digest；来源真实性由目录归属与深验保证）；不变量 `:1021` 改为「resume 以 (plan_digest, params_digest ∈ 同模板显式版本 0..`SOLANA_MAX_SUPPORTED_TX_VERSION` 集, result_sha256) 判完成；header.adopted 存在时其前 rows 行迁自前代 pending，字段值不变、seq 连续」。
- `references/data-pipeline-solana-capture.md:198`（锚 `2. \`sqd_gap_repair.py/v1\` 只修已确认缺陷`）句末补：「producer 升版后同案旧 pending 可经 `--resume --adopt-pending <旧目录>` 认领（前代 sha 须在 producer_history 登记、台账 header 记 `adopted`、深验重算前代 digest）；Solana 请求的交易版本上限统一取 `SOLANA_MAX_SUPPORTED_TX_VERSION`。」
- `CHANGELOG.md`：索引与正文加 **9.1.0**（次版本：新公开接口 `--adopt-pending`＋契约扩展 `header.adopted`；常量化与 v1 修复）；先 `changelog_lint.py`。
- `VERSION`→`9.1.0`；`pyproject.toml:15`、`SKILL.md:23` 同步；`test_version_consistency.py` PASS。

## 6. 不含（调度方在案卷侧做）
PYTHIA 案内脚本同款字面量、案运行时重钉、实际 `--adopt-pending` 续跑、Helius 额度核查。
