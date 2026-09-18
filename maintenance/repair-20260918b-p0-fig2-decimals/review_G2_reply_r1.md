# 工单G2复核：退回

核心修法成立，但工单有 **7 处需要修订**。完整报告、全部锚点实况、函数命中清单及 **205 行 decimals 命中归类**已打印到 stdout。

全程只读、离线，未修改文件；未读取 `~/.codex/`、启动 memories 或其他禁读内容。核查基线为 `f1f473f3`，工作区状态为空。以下区分内存实跑与静态推演。

**G2-R1-01：锚点不满足工单自己的停工规则。**

位置：工单 §0.5、§2.5:71、§2.6:81。

`grep -n -F` 实况：§2.5 带 12 个前导空格的原锚只命中 **1356**；1761 的缩进不同，不能称为“同款锚第 2 处”：

```python
1356:            _require(bundle.get("schema") == "evm-observation-bundle/v1",
1761:        _require(bundle.get("schema") == "evm-observation-bundle/v1",
```

§2.6 结束错误文案实际位于 **1610**，1611 是空行。

修订建议：为 1761 指定独立锚或明确函数内定位；结束锚改为 1610，并明确复合锚的匹配规则。

**G2-R1-02：遗漏一个必然变红的既有测试。**

位置：工单 §2.8:118、§0.8。

[test_evm_observation_nonempty_code.py:129](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_evm_observation_nonempty_code.py:129) 仍保留：

```python
assert core["supply"] == {
    "total_supply_raw": "0",
    "zero_balance_raw": "0",
    "dead_balance_raw": "0",
    "block_binding": "eip1898-block-hash",
}
```

改后实际字典新增 `"decimals": 0`。该断言已内存实跑：**基线 PASS，按计划改后 AssertionError**。

修订建议：工单补上该断言的字段更新。文件已经在白名单内。否则 §0.8“全部须 PASS”不能成立。

**G2-R1-03：新 c 例的基线前提错误，现成夹具也无法得到目标 GREEN。**

位置：工单 §2.9:129、§2.11。

有两个独立问题：

- 工单要求 `facts.decimals=0`、`config.decimals=2`，却称基线 `errors=[]`。基线代码取 `observed = cfg.get("decimals")`，实跑已经拒绝：

  ```text
  facts.token.decimals=0 与链上观测 2 不一致——state_source.facts_inputs.decimals 填错
  ```

- F05 a/b 使用的 `add_new_analysis_distribution()` 把总量改成 **59,127,382 raw**，并非 100。再硬改 `human="1", decimals=2`，既有深验会先报：

  ```text
  supply_closure nominal_supply_raw differs from bound artifacts
  ```

  按工单先调用 `create_bundle(root)`，会在这里抛错，走不到期待的 config 错误文案。

修订建议：使用明确的 raw=100 完整夹具，或者保持实际 N raw、令 `human=N/100`；同时补全 facts/state_source 也为 2 的条件，才能证明“基线放行→改后拒绝”。facts 保持 0 的专项例可以保留，但必须注明基线已拒。

**G2-R1-04：新函数会把字段误写升级成未捕获异常。**

位置：工单 §2.6:91。

新代码在 `try` 外执行：

```python
observed = ((accounting or {}).get("checks") or {}).get("decimals")
```

内存实跑 `checks=["mistyped"]`：

```text
基线：追加“facts.token.decimals 无法取链上观测值”并返回
改后：AttributeError: 'list' object has no attribute 'get'
```

`check_accounting` 记录错误后，发布流程仍会调用该函数；外围没有捕获此异常。

修订建议：先验证 `checks` 为 dict，或将读取纳入异常处理；保持返回拒收理由的行为，并补字段类型误写回归。

**G2-R1-05：必跑守卫与禁读纪律冲突。**

位置：工单 §0.2、§0.8、§2.10。

代码事实：

- `docs_lint.py:268/272/306` 会读取 `references/attic.md` 和 `archive/evals/`。
- `docs_lint.py:129–134` 递归读取全仓 Markdown，仅排除 `.git`，会进入禁止读取的历史 maintenance。
- `grep -rl contract_manifest scripts/tests/*.py` 实际找到 **4 个脚本**。其中 `test_repair_batch3_gates.py:578/581` 会读取被禁止的历史 `r10_ledger.md`。
- §2.10 原样递归搜索 `references` 也会读取 attic。

修订建议：明确守卫名称、读取边界及全量检查的执行阶段；若需要测试进程例外，应在工单中明写。当前纪律下不能要求全量运行后报告 PASS。本次未执行这些越界入口。

**G2-R1-06：“旧 schema 零命中”没有排除现存二进制缓存。**

位置：工单 §1.3、§2.10、§3。

原样执行搜索，除源码外还命中 **5 个已有 `.pyc`**，例如：

```text
Binary file scripts/lib/__pycache__/evm_observation.cpython-314.pyc matches
```

其余对应 `supply_truth_gate`、`observe_supply`、`accounting_gate`、`shared_release_receipt`。源码修改不保证更新缓存，`python -B` 也不会主动更新它们。

修订建议：把零命中判据限定为现役文本源码、JSON 和获准文档，排除 `__pycache__`、`*.pyc`；无需删除缓存。

**G2-R1-07：迁移说明漏掉存量 Solana 收据。**

位置：工单 §0.4、§4；`code_change_pending.md` Q5/Q7。

本段会修改两链共用的 `supply_truth_gate.py`。而 [receipt_validate.py:115](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/receipt_validate.py:115) 默认只接受当前生产者哈希：

```python
current_hash = _hash_file(producer_path)
allowed_hashes = {current_hash}
```

因此即使 Solana 算法不变，存量 Solana supply_truth 也会因 `producer hash mismatch` 失效。共享发布脚本自身变化，还会使旧 shared receipt 的 producer 哈希失效。

修订建议：补充 Solana 的 supply_truth、对账 wrapper、shared receipt 及下游重封成本。“钉版承接旧案”应指完整旧 checkout／执行环境，单填旧版本字段无效。

**已核成立的部分**

- 当前 EVM 生产者确实没有采集或写出 decimals；计划新增来源有明确生产者。
- Solana 的 `checks.decimals` 确实由 mint 数据写出，Q5 对缺少共享相等性检查的描述也准确。
- transcript 应为 **总计 4 笔 eth_call，仅新增 1 笔**；总记录数 9，code=7、recheck=8，自洽。
- `_validate_transcript` 仍返回 `None`；bundle validator 和 accounting validator 的返回类型保持不变。
- uint8 边界、非法字段类型、transcript 数值失配及旧 v1 拒收，均完成内存函数验证。
- `invariant_scan` 基线实跑 PASS；内存替换计划代码及六处登记后，**0 discrepancy**。
- 契约 ID 集合不变，v2 needle 能命中修改后的权威文档，无额外登记要求。
- 文档增量确为 **15 字节**，合计由 `930061` 到 `930076`。
- 已静态扫描登记的 **143 个测试文件**。确认新增的既有失败是 R1-02；清单外未确认第二项必然失败。没有将静态检查表述为全量测试 PASS。

**终点与版本判断**

G1：当前 HEAD 对“大庄#1＋空 series”仍返回 `([], 0)`。必须先落实 G1；其新增 missing 检查会产生：

```text
图 2 缺必画实体线 ['e1']（label 以 项目方/大庄/小庄/离场庄 起头的实体必须各有一条线；空 series 不得放行）
```

发布端经基线 `audit_release_gate.py:1645/1649` 重算拒绝，最终由 `build_html.py:489–493` 阻止落盘。

G2：对合法迁移后的 v2 案，观测及 accounting 为 0、config 为 2，新函数在工单 **107–108** 行必然追加：

```text
verify_recon config.decimals=2 与链上观测 0 不一致——对账 human 供应量级自报
```

但当前 c 例不能证明这条完整回归，必须先修 R1-03；仅凭旧 v1 被 schema 闸挡住，也不能替代该验证。

Q8 **“拒收合法旧 v1＝不兼容契约变更”表述准确**，按 `CHANGELOG.md:4` 属主版本档位；具体版本号可由收官段 E 处理。
