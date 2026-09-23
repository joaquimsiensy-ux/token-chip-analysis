# 工单 W1 v1 — Solana 交易版本上限常量化 ＋ 修复产物「前代认领」机制（→ 9.1.0）

> 背景（调度方已亲核，2026-09-23）：Solana 主网已出现**交易版本 1**（PYTHIA 案 slot 447210248：`maxSupportedTransactionVersion: 0` 报 RPC -32015；改 1 返回 851 笔，其中 legacy 785 / v0 65 / v1 1，v1 消息体多 `transactionConfig` 字段；Helius 对 2/255 也接受，节点只做数值比较）。钉版 skill 内 13 个文件 17 处把该参数写死为 0。官方修复脚本 `sqd_gap_repair.py` 遇 v1 区块直接 `ValueError` 退出（`:892`），PYTHIA 正式 α 修复停在 157,345/157,700。
> 改脚本 ⇒ `producer.sha256` 变 ⇒ `plan_digest` 变（`sqd_repair_core.py:80`）⇒ 旧 `pending-53127bb63fad4994` 无法 `--resume`（`:724-726` header 整体相等比较）。已完成的 157,345 个 slot 是在版本 0 下**成功**读出的，逻辑上不含 v1 交易，证据可继承。用户裁决：修常量 ＋ 加「经审计的前代产物认领」，原则**能删不加、能改不加、skill 上下文（references/SKILL.md）尽量不增**。

## 0. 纪律

- 0.1 开工先 `git status --short` 必须为空、分支为 `fix/solana-txv1`；本仓库是主仓库的克隆，**不 push、不动 main**。
- 0.2 **禁读 `~/.codex` 下任何文件**（启动搜索的自动披露除外，之后不再读）；禁读 `~/Documents`、`~/Desktop`（案卷不在施工范围，且沙箱读不到）。
- 0.3 **白名单（可写）**：
  - 生产：`scripts/lib/solana_attested_session.py`、`scripts/lib/solana_exact_validate.py`、`scripts/lib/solana_observation.py`、`scripts/solana/sqd_gap_repair.py`、`scripts/solana/{probe_window_moves,fast_probe_tops,decode_txs,decode_txs_v2,whale_deep,audit_closed_accounts,gas_origin,stake_decode,probe_escrows,trace_wallet}.py`、`scripts/lib/producer_history.py`
  - 测试：`scripts/tests/test_sqd_gap_repair.py`、`scripts/tests/invariant_scan.py`、`scripts/tests/test_batch4_invariant_guards.py`
  - 文档：`references/scan-schemas.md`（仅 §14.8）、`references/data-pipeline-solana-capture.md`（仅「正式产物窄门」第 2 条）、`CHANGELOG.md`
  - 版本登记：`VERSION`、`pyproject.toml:15`、`SKILL.md:23`
  - 完成报告：本目录 `W1_done.md`、`W1_red_evidence.txt`
- 0.4 **不改**：`scripts/solana/sqd_repair_core.py`（`compute_plan_digest` 绑定语义不动）、`scripts/solana/sqd_cache_identity.py`、`scripts/solana/replay_edges.py`、`scripts/tests/test_producer_registry_current.py`（必须原样 PASS）、`scripts/tests/test_batch8_repair_scale.py`、`scripts/tests/test_batch7_validator_coverage_gaps.py`（必须原样 PASS）、`commands-staging/*`、`invariant_manifest`/`contract_manifest`。
- 0.5 工单里任何行号与实况不符即停工写报告，不要猜。行号旁均附锚文本。
- 0.6 先红后绿：`W1_red_evidence.txt` 记①基线 `python3 -c 'import ast,sys;...'` 或 grep 证明 17 处字面量 0；②基线上 §2 的 adopt 向量不存在（`repair --help` 无 `--adopt-pending`）；③基线 `load_resume_slots` 对 params_digest 为版本 1 模板的行不计入 completed（用 E27 现有夹具改一行台账即可）。
- 0.7 **不跑 `run_all.py`**（调度方本机跑）。定向跑（全部 PASS，贴尾行）：`test_sqd_gap_repair.py`、`test_batch8_repair_scale.py`、`test_batch7_validator_coverage_gaps.py`、`test_producer_registry_current.py`、`test_batch4_invariant_guards.py`、`invariant_scan.py`、`test_batch3_solana_producers.py`、`test_r9_batch3_solana_observation.py`、`test_review_solana_integrity.py`、`test_param_scripts.py`、`changelog_lint.py`。带 `MPLCONFIGDIR=$HOME/.matplotlib`。沙箱不通外网，一切离线。
- 0.8 **边做边 commit**（每节一个 commit，中文 message 前缀 `W1(n):`），不 push。§3 登记必须是**代码 commit 之后的独立 commit**（条目 `commit` 字段填代码 commit 的完整哈希）。
- 0.9 完成报告 `W1_done.md`：改动清单（文件:行）、与工单差异、定向测试尾行、红证据路径、自报是否读过禁读路径。

## 1. 改动 A：交易版本上限常量化（能删的删）

### 1.1 常量落点 `scripts/lib/solana_attested_session.py`
该模块是叶子（只 import `endpoint_identity`，`:10`）。在模块级常量区新增：
```python
# Solana 主网 2026-09 起出现版本 1 交易；本仓库所有 getBlock/getTransaction 请求声明的最高交易版本。
# 升版本只改这里 + producer_history 登记 + CHANGELOG；版本 0..此值的请求模板在修复续跑/认领里均视为等价（§2.3）。
SOLANA_MAX_SUPPORTED_TX_VERSION = 1
```

### 1.2 去重：修复请求模板只留一份
- `scripts/lib/solana_exact_validate.py:1208-1216`（锚 `def _repair_getblock_params_digest(slot):` … `"maxSupportedTransactionVersion": 0}],`）与 `scripts/solana/sqd_gap_repair.py:627-633`（锚 `def _rpc_body(slot):`）是同一模板的两份拷贝。改为：
  - validator 内新增公开函数 `repair_getblock_body(slot, max_version=SOLANA_MAX_SUPPORTED_TX_VERSION)` 返回 body dict（内容即原模板，版本字段用参数）；`_repair_getblock_params_digest(slot, max_version=SOLANA_MAX_SUPPORTED_TX_VERSION)` 改为 `sha256_bytes(canonical_json(repair_getblock_body(slot, max_version)))`。
  - `sqd_gap_repair.py` 的 `_rpc_body(slot)` 改为 `return repair_getblock_body(slot)`（从 `solana_exact_validate` 导入，该文件 `:27` 已 `from solana_exact_validate import …`，加名字即可），删除本地模板。
- `solana_exact_validate.py` 增 `from solana_attested_session import SOLANA_MAX_SUPPORTED_TX_VERSION`（照 `:26-29` 的 try/except 相对导入写法）。

### 1.3 其余 15 处字面量改引用常量（grep 实况，施工时 `grep -rn maxSupportedTransactionVersion scripts --include=*.py` 复核，处数必须 =17）
| 文件 | 行 | 处理 |
|---|---|---|
| `scripts/lib/solana_observation.py` | 270 | `:19` 已 `from solana_attested_session import (…` → 加名字；字面量改常量 |
| `scripts/solana/probe_window_moves.py` | 121 | `:25` 已 `sys.path.insert(0, … / "lib")` → 其后加 `from solana_attested_session import SOLANA_MAX_SUPPORTED_TX_VERSION`；字面量改常量 |
| `scripts/solana/fast_probe_tops.py` | 54 | 同上（`:15` 已有 lib path） |
| `scripts/solana/decode_txs.py` | 39 | **无 lib path**（`:8-11` 为 `import argparse, json, sys, time` / `from pathlib import Path` / `import requests` / `from decode_txs_v2 import …`）→ 在 `:9` 后照兄弟脚本加一行 `sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))`（确认已 `import sys`）＋ import；字面量改常量 |
| `scripts/solana/decode_txs_v2.py` | 295、340 | `:24` 已有 lib path |
| `scripts/solana/whale_deep.py` | 64、154 | `:22` 已有 |
| `scripts/solana/audit_closed_accounts.py` | 230、419、482 | `:40` 已有 |
| `scripts/solana/gas_origin.py` | 81 | `:18` 已有 |
| `scripts/solana/stake_decode.py` | 96 | `:22` 已有 |
| `scripts/solana/probe_escrows.py` | 150 | `:20` 已有 |
| `scripts/solana/trace_wallet.py` | 76 | `:14` 已有 |

### 1.4 守卫（防再写死）
- `scripts/tests/invariant_scan.py`：照 `bare_rpc_pool_errors`（`:337`）风格新增 `hardcoded_tx_version_errors(*, files=None, root=ROOT)`：对 `production_files()` 做 AST 扫描，任何 `ast.Dict` 键为常量字符串 `"maxSupportedTransactionVersion"` 且值为 `ast.Constant`（数字字面量）即报一条错误（文件:行）；接入 `main()` 的汇总（照既有检查的接线方式）。
- `scripts/tests/test_batch4_invariant_guards.py`：照 `test_bare_rpc_pool_injection`（`:25`）新增一条注入测试：拷贝任一白名单脚本到临时目录、把常量引用改回字面量 `0`，断言扫描报错；原文件断言 0 错。

## 2. 改动 B：`repair --adopt-pending <旧 pending 目录>`（经审计的前代产物认领）

### 2.1 语义（一句话）
当前 producer 的 plan 与旧 pending 的 plan **除 `producer.sha256` 外完全一致**、且旧 producer 是 `producer_history` 登记的 ACTIVE 哈希时，把旧 pending 台账「成功前缀中证据对齐的最长前缀」逐行迁入新 pending，并在新台账 header 留下可复验的认领记录；之后走普通 `--resume` 只补拉剩余 slot。**不改任何已存在的证据文件、不改台账行内容、不重编 seq。**

### 2.2 CLI 与入口（`sqd_gap_repair.py`）
- `:1544`（锚 `item.add_argument("--resume", action="store_true")`）旁增 `item.add_argument("--adopt-pending", help=argparse.SUPPRESS 或简短英文 help)`。
- 规则：`--adopt-pending` **必须与 `--resume` 同给**（否则 `ValueError("--adopt-pending requires --resume")`）；新 pending 的 `rpc_ledger.jsonl` 必须不存在或只有 header（否则 `ValueError("adopt requires an empty target ledger")`，防重复/交叉认领）。
- 接线点：`:1273-1276`（锚 `pending.mkdir(exist_ok=args.resume)` … `evidence_dir.mkdir(exist_ok=True)`）之后、进入 `_live_payloads`（`:961`）之前调用 `adopt_predecessor_pending(Path(args.adopt_pending), pending, plan)`。认领只做迁入，续跑逻辑不动。

### 2.3 校验（fail-closed，任一不满足即 `ValueError`，零迁移）
`adopt_predecessor_pending(old, pending, plan)`：
1. `old` 必须是目录、名字形如 `pending-<16hex>`；`old_rows = _read_ledger_prefix(old / "rpc_ledger.jsonl")` 非空；`old_rows[0]["schema"] == "sqd-solana-rpc-ledger/v1"`；`old_rows[0]["plan_digest"]` == 目录名后缀；`old_rows[0]["reference"] == _ledger_header(plan)["reference"]`（同参考源同指纹）。
2. **前代可复现**：`candidates = historical_producer_hashes("scripts/solana/sqd_gap_repair.py", "sqd-solana-repair-bundle/v1") - {plan["producer"]["sha256"]}`；对每个 sha 构造 plan 深拷贝、`producer.sha256 = sha`、`compute_plan_digest(副本) == old_rows[0]["plan_digest"]` 者即前代；无命中 → `ValueError("adopt: predecessor plan_digest is not reproducible from a registered producer")`。（`sqd_gap_repair.py` 需新增 `from producer_history import historical_producer_hashes  # noqa: E402`（LIB 已在 `:20` 进 sys.path）与 `import shutil`；`compute_plan_digest` 已在 `:32` 导入。）
3. **行/证据对齐**：把 `load_resume_slots`（`:716-757`）拆成两段以复用：`_verify_ledger_rows(pending, rows, header)`（即 `:727-757` 的逻辑，返回 completed 集）+ 外壳 `load_resume_slots` 调它。**改 `:750-751`**（锚 `expected_params = sha256_bytes(canonical_json(_rpc_body(slot)))`）：接受集合 `{_repair_getblock_params_digest(slot, v) for v in range(SOLANA_MAX_SUPPORTED_TX_VERSION + 1)}`（版本 0..当前均等价：低版本参数下**成功**返回的区块，按节点语义不含更高版本交易，响应字节与高版本参数下相同）。认领采纳 = 旧 rows[1:] 中**从头起连续**、每行都被 `_verify_ledger_rows` 判 completed 的最长前缀（遇第一条未对齐行即止，其后不采纳；这样 seq 天然连续，不需改写）。采纳 0 行 → `ValueError("adopt: no adoptable prefix")`。
4. **迁入**：对每个采纳 slot，`os.link(old/evidence/<slot>.sqd.json, pending/evidence/…)` 与 `.ref.json` 同理（跨设备 `OSError(EXDEV)` 回退 `shutil.copy2`）；目标已存在则要求 JSON 相等，否则 `ValueError`。然后 `_publish_bytes_exclusive(pending/"rpc_ledger.jsonl", _jsonl_bytes([new_header] + 采纳行))`，行原样（含原 seq/ts/params_digest）。
5. **header 认领记录**：`new_header = _ledger_header(plan)` 加键 `"adopted": {"predecessor_plan_digest": …, "predecessor_producer_sha256": …, "rows": n, "source": str(old.relative_to(case_root)) 或绝对路径脱敏后, "ts": int(time.time())}`。

### 2.4 让 header 校验认得认领记录（三处）
- `sqd_gap_repair.py:724-726`（锚 `or rows[0] != header:`）与 `:1401`（锚 `if not complete_rows or complete_rows[0] != ledger_header:`）：比较改为「去掉 `adopted` 键后相等」；若台账 header 含 `adopted`，**每次续跑/发布都复验** §2.3 第 2 条（前代可复现、sha 已登记）和 `adopted["rows"] <= 数据行数`，失败即 `ValueError("adopted predecessor record is not verifiable")`。抽一个私有函数 `_verify_adopted_record(header, plan)` 两处共用。
- `scripts/lib/solana_exact_validate.py` 深验：`:1533`（锚 `or ledger_row.get("params_digest") != _repair_getblock_params_digest(slot) \`）改为「不在版本 0..当前的接受集合内」；`:1297-1313` 附近增：若 `ledger_header` 含 `adopted`，则键集必须恰为 `{predecessor_plan_digest, predecessor_producer_sha256, rows, source, ts}`、`predecessor_producer_sha256 ∈ historical_producer_hashes("scripts/solana/sqd_gap_repair.py", REPAIR_BUNDLE_SCHEMA)`、`predecessor_plan_digest` 为 16 位 hex 且 `!= digest`、`0 < rows <= ledger_data_count`，否则 `reasons.append("RPC ledger adopted record invalid")`（深验无 plan，不重算前代 digest；重算在生产者续跑/发布时做）。

### 2.5 不做
- 不改 `compute_plan_digest`、不改 gid 物料、不加 bundle 顶层键（认领记录随 `rpc_ledger` 文件哈希进 bundle，`sqd_cache_identity.validate_repair_bundle` 键集不动）。
- 不读 STOPPED.json、不删旧 pending（审计留档）。

## 3. 登记 `scripts/lib/producer_history.py`
代码 commit 落定后，取 `git show <代码commit>:scripts/solana/sqd_gap_repair.py | shasum -a 256`，照 `:204-233`（四条 `4c5cd578…` 条目）格式追加 4 条（协议 `sqd-solana-cache/v4`、`sqd-solana-repair-bundle/v1`、`sqd-solana-coverage-resolution/v1`、`sqd-solana-repair-pointer/v1`），`reason` 写「9.1.0 registers the tx-version-1 producer (SOLANA_MAX_SUPPORTED_TX_VERSION + --adopt-pending); predecessor 25f04ff1… stays ACTIVE for adoption.」旧哈希 `25f04ff10bc494be977e4c5b3193c3a928c0764fa529d8d5a47563fe2a825e66` **保持 ACTIVE 不动**（认领依赖它）。`test_producer_registry_current.py` 必须 PASS。

## 4. 测试 `scripts/tests/test_sqd_gap_repair.py`
在 `batch3b_semantic_regressions()`（`:611`）E27(a)（`:712-752`）之后加 **E27(d) 认领向量**，复用 `build_batch3b_case`/`write_repair_fixture`/`repair_slot_responses` 与 E27(a) 的「配额 exit 3 留下一行」手法：
- 造旧 pending：跑到 exit 3 后，把 pending 改名为 `pending-<前代digest>`、header `plan_digest` 改为前代 digest、台账行 `params_digest` 改为版本 0 模板 digest（模拟旧 producer 请求）；前代 digest 的取得：monkeypatch `repair.historical_producer_hashes` 返回 `{FAKE_SHA, 当前sha…}`，前代 digest = `compute_plan_digest(plan 副本 producer.sha256=FAKE_SHA)`（plan 可从 `repair._plan…` 现有路径取，或从 header/bundle 反推；若取 plan 需要 ≤ 20 行辅助即可，否则在报告写明改用什么等价手法）。
- 正向：`repair … --resume --adopt-pending <旧>` 用**不含已采纳 slot** 的 fixture 跑完 exit 0（证明未重拉）；发布 gen 的 `rpc_ledger.jsonl` header 含 `adopted`（rows=1）、旧行原样、新行 params_digest 为版本 1 模板；`validate_repair_bundle_deep` PASS；旧 pending 目录与证据文件仍在。
- 负向（每条零迁移、新 pending 台账为空或不存在）：①FAKE_SHA 不在登记集 → 拒；②旧 header.reference.endpoint_fingerprint 改动 → 拒；③目标 ledger 已有一行 → 拒；④旧 `.ref.json` 的 `raw_response_sha256` 改坏 → 该行不采纳 → 「no adoptable prefix」拒；⑤不带 `--resume` → 拒。
- 深验负向：发布后把 header.adopted.predecessor_producer_sha256 改为未登记值 → `validate_repair_bundle_deep` FAIL（reasons 含 "adopted record invalid"）。

## 5. 文档（中文，只改这几处，不增段落）
- `references/scan-schemas.md` §14.8（`:998-1023`）：表内加 5 行可选字段 `header.adopted.{predecessor_plan_digest, predecessor_producer_sha256, rows, source, ts}`（必填=否；说明：认领自登记前代 producer 的 pending，续跑/发布时复验前代 digest 可复现）；不变量 `:1021` 那行改为「resume 以 (plan_digest, params_digest ∈ 版本 0..`SOLANA_MAX_SUPPORTED_TX_VERSION` 请求模板集, result_sha256) 判完成；header.adopted 存在时其前缀行来自前代 pending，seq 连续不重编」。
- `references/data-pipeline-solana-capture.md:198`（锚 `2. \`sqd_gap_repair.py/v1\` 只修已确认缺陷`）：句末补一句「producer 升版后旧 pending 可经 `--resume --adopt-pending <旧目录>` 认领（前代 sha 须在 producer_history 登记，台账 header 记 `adopted`）；所有 Solana RPC 请求的交易版本上限统一取 `solana_attested_session.SOLANA_MAX_SUPPORTED_TX_VERSION`。」
- `CHANGELOG.md`：版本索引与正文各加 **9.1.0**（次版本：新公开接口 `--adopt-pending` + 持久化契约扩展 `header.adopted`）；先跑 `changelog_lint.py`。
- `VERSION`→`9.1.0`；`pyproject.toml:15`、`SKILL.md:23` 同步。

## 6. 本工单不含（调度方后续在案卷侧做）
PYTHIA 案内 `scripts/collect_candidate_observations.py:736,754`、`scripts/et1_funder_validation.py:20,21` 的同款字面量；案运行时重钉到新 main；实际 `--adopt-pending` 续跑与 Helius 额度核查。
