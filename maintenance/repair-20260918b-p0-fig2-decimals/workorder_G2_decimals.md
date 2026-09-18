# 工单 G2（v2，融合 codex 复核 r1 七条 G2-R1-01…07 与 G1-R1-03）：EVM decimals 绑定链上观测——observation bundle v2 补 decimals()，闸侧两链族统一读观测 —— repair-20260918b-p0-fig2-decimals 第二段

> 出处：codex 对 7.2.1（f1f473f3）六视角 review F07（P0，半修复）：7.2.1 F05 新增的 `audit_release_gate.check_facts_decimals`（`:1586-1611`）EVM 分支取 verify_recon **config**.decimals 当"链上观测"，而 `scripts/lib/evm_observation.observe_evm_supply`（`:120-232`）只请求 totalSupply/balanceOf(ZERO)/balanceOf(DEAD)/getCode，从未请求 `decimals()`（选择器 0x313ce567）——闸核的是两份自报是否一致。反例（review 附录 C `decimals_selfreport`）：raw_supply=100 不变，config 由 decimals=0/human=100 改为 decimals=2/human=1 并更新内容哈希，`_recon_bound_reality`（shared_release_receipt `:605-610`）nominal=1×10²=100 仍闭合，decimals 专项闸与完整 new-analysis 发布 errors=[]。用户 09-18 裁决：修（补链上采集，不选"EVM 显式拒"）。总原则：skill 上下文不增、能删不增、能改不增。
> 修法（单一来源链）：①观测生产者在同一冻结块哈希上多发一笔 `eth_call decimals()`，进 transcript（8→9 笔）与 bundle `supply.decimals`，schema 升 `evm-observation-bundle/v2`（旧 v1 是没有 decimals 的产物，不得静默当 v2 消费）；②EVM 会计闸 `accounting_gate.py` 从已验 bundle 把 `checks.decimals` 写进 accounting_mode；③共享校验器 `validate_accounting_receipt` EVM 分支核 `accounting.checks.decimals == bundle.supply.decimals`；④发布闸 `check_facts_decimals` 两链族统一读 `accounting.checks.decimals`（删 EVM 读 config 的分支），EVM 另核 verify_recon `config.decimals == 观测`（human 供应量级不再自报）。Solana 侧（accounting_gate_sol 从 mint 真写出 `checks.decimals`）不动。
> v2 变更（`review_G2_reply_r1.md`）：R1-01 §2.5 两处 schema 锚按缩进区分（12 空格＝:1356、8 空格＝:1761），§2.6 止锚改 :1610；R1-02 §2.8 补 `test_evm_observation_nonempty_code.py:129-134` 的 supply 字典断言加 `"decimals": 0`；R1-03（同 G1-R1-03）§2.9 c 例重设计——facts/state_source 与 config 同改 2、human＝N/100、观测 0，基线才放行；R1-04 §2.6 新函数先验 `checks` 为 dict，字段误写走拒收而非抛异常，并补回归；R1-05 §0.2 为守卫/测试进程立精确读取例外，§0.8 点名四个契约守卫脚本；R1-06 §1.3/§2.10/§3 零命中判据排除 `__pycache__`/`*.pyc`/attic；R1-07 §4 与台账 Q7 补两链存量 supply_truth/shared receipt 因 producer 哈希变化整体失效的迁移代价。
> 内容基线：`f1f473f3`（v7.2.1）加本工程已入库 commit（含 G1 施工 commit）；本段触及文件在开工时与 f1f473f3 逐字节相同（G1 不触及它们）。

## 0. 开工纪律

- 0.1 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。开工先跑并贴进 `G2_done.md`：`git status --short`（须为空）；`git diff --stat f1f473f3 HEAD -- scripts/lib/evm_observation.py scripts/evm scripts/lib/supply_truth_gate.py scripts/report/shared_release_receipt.py scripts/report/audit_release_gate.py scripts/tests/invariant_manifest.json scripts/tests/contract_manifest.json references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`（须为空）。不空即停工写 `G2_done_attempt1_stopped.md`。
- 0.2 **禁读** `~/.codex/`；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260918-p0-f04-f07/` 与本目录以外的历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。**精确读取例外（R1-05）**：§0.8 要求运行的守卫/测试进程会自行读取上述禁区（`docs_lint.py:129-134` 递归全仓 Markdown、`:268/272/306` 读 attic 与 archive/evals；`test_repair_batch3_gates.py:578/581` 读历史 `r10_ledger.md`）——允许进程自行读取，施工方不得主动阅读、引用或改动这些文件；done 里如实注明例外被哪个脚本触发。
- 0.3 **白名单**——生产：`scripts/lib/evm_observation.py`、`scripts/evm/observe_supply.py`、`scripts/evm/accounting_gate.py`、`scripts/lib/supply_truth_gate.py`、`scripts/report/shared_release_receipt.py`、`scripts/report/audit_release_gate.py`；测试：`scripts/tests/test_evm_observation.py`、`test_evm_observation_nonempty_code.py`、`test_supply_truth_gate.py`、`test_evm_observation_release.py`、`test_audit_release_gate.py`、`test_handoff_manifest.py`、`test_batch3_evm_vertical_slice.py`、`test_review_20260804_p105.py`；清单：`scripts/tests/invariant_manifest.json`（仅 6 处 `evm-observation-bundle/v1`→`v2`）、`scripts/tests/contract_manifest.json`（仅 `:150` needle v1→v2）；文档（**仅 §2.10 列出的字符替换**）：`references/data-pipeline-evm-recon.md`、`references/independent-audit-protocol.md`、`references/scan-schemas.md`；本目录新建 `G2_done.md`、`G2_red_evidence.txt`，停工时 `G2_done_attempt1_stopped.md`。
- 0.4 **不改**：`scripts/lib/solana_observation.py`、`scripts/solana/accounting_gate_sol.py`、`scripts/evm/verify_recon.py`、`scripts/report/facts_gate.py`、`handoff_manifest.py`、`receipt_kernel.py`/`receipt_validate.py`；`shared_release_receipt._recon_bound_reality`（`:592-635`）、`validate_evm_observation_source_chain`（`:1809`）；`SKILL.md`、`commands-staging/`、`VERSION`、`pyproject.toml`、`CHANGELOG.md`；其他测试只跑不改（若 §0.8 定向清单外的测试因本段变红，停工汇报，不自行扩白名单）。
- 0.5 行号均指施工前基线；锚 `grep -n -F` 恰 1 处且行号一致，不符**停工**。删除 > 修改 > 新增。
- 0.6 离线（companion 沙箱无网；本段所有 RPC 均为测试假池/本地假服务）；不 commit、不 push、不部署；禁 stash/checkout/reset。
- 0.7 先红后绿：§2.11 新用例在改生产代码前逐例取 RED 写 `G2_red_evidence.txt`。
- 0.8 不跑 `run_all.py`。定向跑（全部须 PASS）：`python3 -B scripts/tests/test_evm_observation.py`、`test_evm_observation_nonempty_code.py`、`test_evm_observation_release.py`、`test_supply_truth_gate.py`、`test_audit_release_gate.py`、`test_handoff_manifest.py`、`test_review_20260804_p105.py`、`test_repair_batch_a.py`、`test_repair_batch_d.py`、`test_batch13_accounting_target.py`、`test_batch14_accounting_bundle_fallback.py`、`test_recon_fifth_check.py`、`test_recon_deep_reverify.py`、`test_batch11_frozen_bundle_binding.py`、`test_a4_gate.py`、`python3 -B scripts/tests/invariant_scan.py`、`python3 -B scripts/tests/docs_lint.py --all`、契约守卫四脚本 `test_contract_routes.py`、`test_commands_deploy_sync.py`、`test_repair_batch3_gates.py`（读取禁区按 §0.2 例外）与 `docs_lint.py` 本身。`test_batch3_evm_vertical_slice.py` 需绑 127.0.0.1（沙箱可能 EPERM）：能跑则跑，不能跑如实写 done 由调度方本机补验。

## 1. 硬约束

- 1.1 文档字节：`SKILL.md` 8021、`commands-staging/*.md` 8798 不变；`references/**/*.md` 合计由 930061 变为 **930076**（仅 §2.10 的 +15 字节：`、\`decimals()\``，其余 v1→v2 替换零增减）。命令同工单 G1 §1.1。
- 1.2 `git diff --stat` 只含 0.3 白名单。
- 1.3 旧 v1 bundle **不得**被任何消费者接受：`validate_evm_observation_bundle` 对 schema≠v2 抛 ValueError；`accounting_gate`/`supply_truth_gate`/`shared_release_receipt` 三处 schema 字面量同步 v2。零命中判据（R1-06）限定现役文本源码/JSON/获准文档：`grep -rn --exclude-dir=__pycache__ --exclude='*.pyc' --exclude=attic.md 'evm-observation-bundle/v1' scripts references SKILL.md commands-staging` 改后须为 0 命中；既有 `.pyc` 缓存命中不计、不删。
- 1.4 transcript 契约：恰 9 笔，方法序 `eth_chainId, eth_getBlockByNumber, eth_blockNumber, eth_call×4, eth_getCode, eth_getBlockByNumber`；第 4 笔 eth_call（seq 6）为 decimals()；既有下标引用全部顺延（见 §2.1）。
- 1.5 `decimals()` 返回值按 uint8 校验（0–255），超出即 EvmObservationError；bundle 校验同样拒非 int/bool/越界。

## 2. 逐条施工

### 2.1 `scripts/lib/evm_observation.py`

- `:23`（锚 `BUNDLE_SCHEMA = "evm-observation-bundle/v1"`）→ `"evm-observation-bundle/v2"`。
- `:25`（锚 `SEL_BALANCE = "0x70a08231"`）之后新增 `SEL_DECIMALS = "0x313ce567"`。
- 模块 docstring `:6`（锚 `canonical block-hash selector and fail closed when an endpoint cannot serve it.`）之后追加一行：`The same block also serves ``decimals()`` so consumers never take the token scale from caller config.`
- `:172-178`（起锚 `    eth_calls = [`，止锚 `    ]`＋下一行 `    responses = pool.call_many(eth_calls, progress=False)`）：在 DEAD 那条之后追加 `        ("eth_call", [{"to": canonical_token, "data": SEL_DECIMALS}, block_selector]),`。
- `:186`（锚 `            ("totalSupply", "balanceOf(ZERO)", "balanceOf(DEAD)")):`）→ `            ("totalSupply", "balanceOf(ZERO)", "balanceOf(DEAD)", "decimals")):`。
- `:189`（锚 `        values.append(value)`）之后（循环外）新增：

```python
    decimals = values[3]
    if decimals > 255:
        raise EvmObservationError(f"decimals() returned {decimals}, exceeds uint8")
```

- `:228`（锚 `            "block_binding": BLOCK_BINDING,`）之前插入 `            "decimals": decimals,`。
- `:263`（锚 `    if not isinstance(transcript, list) or len(transcript) != 8:`）→ `!= 9`；`:264` 文案 `exactly 8 calls` → `exactly 9 calls`。
- `:265-269` methods 列表：`"eth_call", "eth_call", "eth_call", "eth_getCode",` → `"eth_call", "eth_call", "eth_call", "eth_call", "eth_getCode",`。
- `:287`（锚 `            or transcript[7]["params"] != expected_block_params:`）→ `transcript[8]`。
- `:292-296` `expected_call_params`：在 DEAD 条目后追加 `        [{"to": token, "data": SEL_DECIMALS}, selector],`。
- `:300`（锚 `    if transcript[6]["params"] != [token, selector]:`）→ `transcript[7]`。
- `:314`（锚 `            ("total_supply_raw", "zero_balance_raw", "dead_balance_raw"), start=3):`）→ `("total_supply_raw", "zero_balance_raw", "dead_balance_raw", "decimals"), start=3):`（`int(supply[field])` 对 int 与十进制串都成立，`:317` 不改）。
- `:319`（锚 `    code_raw = transcript[6]["result"]`）→ `transcript[7]`；`:326`（锚 `    recheck = _block(transcript[7]["result"], "transcript recheck block")`）→ `transcript[8]`。
- `:393`（锚 `    if supply.get("block_binding") != BLOCK_BINDING:`）之前插入：

```python
    decimals = supply.get("decimals")
    if isinstance(decimals, bool) or not isinstance(decimals, int) or not 0 <= decimals <= 255:
        raise ValueError("EVM observation bundle supply.decimals invalid (uint8 required)")
```

### 2.2 `scripts/evm/observe_supply.py`
- `:29`（锚 `BUNDLE_SCHEMA = "evm-observation-bundle/v1"`）→ v2。

### 2.3 `scripts/evm/accounting_gate.py`
- `:74`（锚 `SEL_DECIMALS = "0x313ce567"  # decimals()`）**删除**（全仓 grep 仅此一处定义、零使用；观测在 evm_observation 完成，会计闸不再现场读 decimals）。
- `:76`（锚 `EVM_OBSERVATION_SCHEMA = "evm-observation-bundle/v1"`）→ v2；`:404` help 文案 `formal evm-observation-bundle/v1` → v2。
- `:477-479`（锚 `            result["observed_anchor"] = {` … `            }`）之后、`:480`（锚 `        except Exception as exc:  # noqa: BLE001`）之前插入 `            result["checks"]["decimals"] = bundle["supply"]["decimals"]`。说明：`result["checks"]` 在 `:443` 已初始化为 `{}`；此处仍在 `try` 内，bundle 已过 `validate_evm_observation_bundle`。

### 2.4 `scripts/lib/supply_truth_gate.py`
- `:92`（锚 `EVM_OBSERVATION_SCHEMA = "evm-observation-bundle/v1"`）→ v2；`:541`（锚 `                         "EVM=evm-observation-bundle/v1")`）→ v2。

### 2.5 `scripts/report/shared_release_receipt.py`
- `:1356`（锚＝12 个前导空格 `            _require(bundle.get("schema") == "evm-observation-bundle/v1",`，唯一）→ v2；`:1761`（锚＝8 个前导空格 `        _require(bundle.get("schema") == "evm-observation-bundle/v1",`，唯一，位于 `validate_accounting_receipt`）→ v2。两锚以缩进区分，`grep -n -F` 各恰 1 处。
- `:1775`（锚 `                 "EVM accounting observed anchor block_hash mismatch")`）之后、`:1776`（锚 `        return target, accounting, sha(bundle_path)`）之前插入：

```python
        _require(accounting["checks"].get("decimals") == bundle["supply"]["decimals"],
                 "EVM accounting checks.decimals is not the bundle observed decimals")
```

### 2.6 `scripts/report/audit_release_gate.py` —— `check_facts_decimals` 改单一来源

`:1586-1610`（起锚 `def check_facts_decimals(case_dir: Path, facts, accounting, errors: list[str]):`，止锚 `:1610` `        errors.append(f"facts.token.decimals={declared!r} 与链上观测 {observed} 不一致——state_source.facts_inputs.decimals 填错")`；`:1611` 空行保留）整函数替换为：

```python
def check_facts_decimals(case_dir: Path, facts, accounting, errors: list[str]):
    """G2（repair-20260918b）：token.decimals 绑定链上观测——两链族一律取
    accounting_mode.checks.decimals（solana 由 accounting_gate_sol 从 mint 写出；evm 由
    accounting_gate 从 evm-observation-bundle/v2 的 supply.decimals 写出，
    validate_accounting_receipt 已核其与 bundle 相等）；evm 另核 verify_recon config.decimals
    与观测一致（human 供应量级不得自报）。取不到即拒。只挂 new-analysis。"""
    declared = ((facts or {}).get("token") or {}).get("decimals")
    checks = (accounting or {}).get("checks") if isinstance(accounting, dict) else None
    observed = checks.get("decimals") if isinstance(checks, dict) else None
    if isinstance(observed, bool) or not isinstance(observed, int):
        errors.append("facts.token.decimals 无链上观测来源可核（accounting_mode.checks.decimals 缺失或 checks 非对象）")
        return
    if declared != observed:
        errors.append(f"facts.token.decimals={declared!r} 与链上观测 {observed} 不一致——state_source.facts_inputs.decimals 填错")
    try:
        import shared_release_receipt
        if shared_release_receipt.chain_family(str((accounting or {}).get("chain") or "")) != "evm":
            return
        witness = _validate_reconciliation_report_once(case_dir)
        bal = (witness.receipts or {}).get("balance") or {}
        _, cfg = shared_release_receipt._bound_json_input(case_dir, bal, "config", "verify_recon config")
    except Exception as exc:
        errors.append(f"verify_recon config.decimals 无法对链上观测: {exc}")
        return
    if cfg.get("decimals") != observed:
        errors.append(f"verify_recon config.decimals={cfg.get('decimals')!r} 与链上观测 {observed} 不一致——对账 human 供应量级自报")
```

说明：调用点 `:1910` 不动；`_validate_reconciliation_report_once`/`_bound_json_input`/`chain_family` 均为 7.2.1 已用接口；R1-04：`checks` 非 dict（如 `["mistyped"]`）走"缺失或非对象"拒收，不得抛 AttributeError（基线对此返回拒收理由，须保持）。

### 2.7 `scripts/tests/invariant_manifest.json` / `contract_manifest.json`
- invariant `:63/:107/:351/:401/:420/:558` 六处 `"evm-observation-bundle/v1"` → v2（只改字符串，不动结构）；contract `:150` needle v1→v2。改后跑 `invariant_scan.py`，若报其他缺项**停工汇报**。

### 2.8 测试夹具顺延（transcript 9 笔 + decimals）
- `test_evm_observation.py:87`（锚 `            values = {"0x18160ddd": 1_000_000, "0x70a08231": 7}`）→ `values = {"0x18160ddd": 1_000_000, "0x70a08231": 7, "0x313ce567": self.decimals}`；`FakePool.__init__` 签名（`:49-51`）加 `decimals=18`，`:58` 之后 `self.decimals = decimals`。
- `test_evm_observation_nonempty_code.py:102`（锚 `    transcript[6]["result"] = "0x"`）→ `[7]`；`:116`（锚 `    transcript[6]["params"] = [TOKEN, hex(AS_OF)]`）→ `[7]`（ContractPool 对一切 eth_call 返 ZERO_WORD → decimals 0，合法）；**R1-02**：`:129-134` 的 `assert core["supply"] == {...}` 字典在 `"dead_balance_raw": "0",` 之后加 `"decimals": 0,`（否则该既有断言必然变红）。
- `test_supply_truth_gate.py:87-88` `write_evm_bundle` 签名加 `decimals=0`；`:112-118` transcript：在 DEAD（seq 5）后插入 `{"seq": 6, "method": "eth_call", "params": [{"to": token, "data": "0x313ce567"}, selector], "result": word(decimals)}`，getCode 改 seq 7、recheck 改 seq 8；`:133-137` core supply 加 `"decimals": decimals`。
- `test_evm_observation_release.py:64`（锚 `    for row in transcript[3:6]:`）→ `[3:7]`；`:70`（锚 `    transcript[6]["params"] = [bundle["target"]["token"], selector]`）→ `[7]`；`:112`（锚 `        "checks": {"proxy": {"is_proxy": False}},`）→ `"checks": {"proxy": {"is_proxy": False}, "decimals": 0},`。
- `test_audit_release_gate.py:311`（锚 `        "checks": {"fot": {"status": "clean"}}})`）→ `"checks": {"fot": {"status": "clean"}, "decimals": 0}})`。
- `test_handoff_manifest.py:157`（锚 `        "checks": {"proxy": {"is_proxy": False}},`，开工核实唯一性；不唯一则以 `:149-159` 块定位）→ 加 `"decimals": 0`。
- `test_batch3_evm_vertical_slice.py:76-77`（锚 `                if data.startswith("0x18160ddd"):` / `                    amount = type(self).supply`）之后插入 `                elif data.startswith("0x313ce567"):` / `                    amount = 0`（真 CLI 链：observe_supply→accounting_gate 写 checks.decimals=0→supply_truth；该测试若沙箱 EPERM 不能跑，如实写 done）。
- `test_recon_deep_reverify.py:154/:400` 的 `transcript[...]` 属 verify_recon/time_spotcheck transcript，与本段无关——开工核实后写 done，不改。

### 2.9 新用例（RED）
- `test_audit_release_gate.py` 或 `test_review_20260804_p105.py`（择一，写 done）：R1-04 回归——`accounting_mode.json` 的 `checks` 改为 `["mistyped"]` 喂 `gate.check_facts_decimals(root, facts, accounting, errors)`，断言 errors 含 `缺失或非对象` 且**不抛异常**（基线：返回拒收理由；改后须保持——GREEN→GREEN 但文案变化，记入证据）。
- `test_evm_observation.py`：新 `test_decimals_observed_and_uint8_enforced()`：`observe()["supply"]["decimals"] == 18`（RED：基线 KeyError）；`expect_error(lambda: observe(FakePool(decimals=256)), "uint8")`（RED）；挂进 `main()` 列表。
- `test_evm_observation_release.py`：新用例（挂进该文件既有用例注册方式）：`build_case` 后把 `accounting_mode.json` 的 `checks.decimals` 改 2、重算 wrapper/manifest 所需 sha（照该文件既有 `refresh_wrapper` 惯例）→ `shared.validate_accounting_receipt(root)` 抛含 `checks.decimals` 的 ValueError（RED：基线不核）。
- `test_review_20260804_p105.py`：在 F05 decimals a/b 两例（`:271-285`）之后新增 **c 例**（R1-03 重设计——基线必须真放行）：`report = fixture.build_case(root, historical=False)`（照 a/b）→ `add_new_analysis_distribution(root, report, decimals=2)`（facts/state_source decimals＝2；该夹具把 owner 快照总量改为 N raw 并已重建 balance/supply/supply_truth 与 config：`fixture_recon_config.json` decimals=0、`total_supply_human=str(N)`）→ 读 config，取 `N = int(config["total_supply_human"])`，改为 `decimals=2`、`total_supply_human=str(Decimal(N) / 100)`（nominal＝N/100×10²＝N raw，`_recon_bound_reality` 仍闭合）→ 对 `balance_receipt.json`、`supply_receipt.json` 两收据把 `inputs.config` 的 size/sha256 重算（形状照 `test_audit_release_gate.artifact_ref` `:49`）→ `reconciliation_report.json` 的 `checks[balance|supply].receipt.sha256` 重算 → `create_bundle(root)`（照 `:218-219` 惯例）→ **基线**：`gate.run(root, report, profile="new-analysis")` 须 `== []`（facts 2 vs config 2 互证放行——这就是 review 反例；把这条"基线放行"也写进 RED 证据）→ **改后**：errors 同时含 `facts.token.decimals=2 与链上观测 0 不一致` 与 `verify_recon config.decimals=2 与链上观测 0 不一致`。另保留 a 例（facts 2/config 0）不动，并在 done 注明 a 例基线本就拒。允许在本文件内新增私有 helper（如 `_rebind_config_decimals(root, decimals)`）。

### 2.10 文档（仅字符替换，零新增句）
- `references/data-pipeline-evm-recon.md:36`：``读取 `totalSupply()`、`balanceOf(ZERO)` 与 `balanceOf(dead)` `` → ``读取 `totalSupply()`、`decimals()`、`balanceOf(ZERO)` 与 `balanceOf(dead)` ``（+15 字节）；同行 `evm-observation-bundle/v1` → v2。
- `references/independent-audit-protocol.md:166`：`evm-observation-bundle/v1` → v2。
- `references/scan-schemas.md:388`：`evm-observation-bundle/v1` → v2。
- 改后按 §1.3 的排除式 grep 须 0 命中（attic/`__pycache__` 不计）；`docs_lint.py --all` 与四个契约守卫 PASS（读取禁区按 §0.2 例外）。

### 2.11 RED 证据清单
§2.9 三处新用例改生产代码前逐例取证（AssertionError/异常原文、命令、被测文件 sha256）写 `G2_red_evidence.txt`。

## 3. 完成报告 `G2_done.md` 必含

①0.1 两条命令输出；②§2 各处 `git diff` 原文（按文件）；③RED 摘要；④0.8 各测试结果尾行（含未能跑的项及原因）；⑤1.1 三个字节数；⑥`git diff --stat`；⑦§1.3 排除式 grep 改后输出（须空）；⑧与工单差异/停工点（含 §2.8 各"开工核实"结果）；⑨禁读披露。stdout 首行 `# 施工 G2：完成` 或 `# 施工 G2：停工`。

## 4. 登记不修（`code_change_pending.md` Q5–Q8，调度方维护）

- Solana 侧 checks.decimals↔bundle 相等性另单；非标准 ERC20 在观测阶段 FAIL 属目标行为；存量 EVM 案 v1 bundle BLOCK、迁移＝重跑观测三件＋下游重建；版本档位已裁决 8.0.0。
- **R1-07 迁移代价补全**：本段改动 `supply_truth_gate.py` 与 `shared_release_receipt.py`，`receipt_validate.py:115-116` 默认只认当前 producer 哈希 → **两链**存量 `supply_truth` 收据、对账 wrapper 与 shared receipt 在 HEAD 下一律 `producer hash mismatch` 失效（Solana 算法未变也不例外）；旧案只能在钉版的完整旧 checkout/执行环境下发布，单填旧版本字段无效；要在新版重发布须整链重跑 supply_truth→reconciliation_report→shared receipt→下游封口。
