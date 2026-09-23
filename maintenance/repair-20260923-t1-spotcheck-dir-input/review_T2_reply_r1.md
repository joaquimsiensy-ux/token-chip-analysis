# 工单T2复核r1补发：退回

两层接线与 9.0.4 的修复方向成立，但 **v1 不能直接施工**：新增登记会使现有守卫出现两项失败；拟议代码改变了非法收据的异常处理；H16 有现成夹具可复用，不应保留免测出口；FR-03 仅改参数示例不足以说明文件登记接口；开工条件和必跑检查也存在纪律冲突。

以下是完整复核报告。事实与实验结果均来自上一轮只读核验，本次补发没有重新执行命令或读取文件。工单行号指 `maintenance/repair-20260923-t1-spotcheck-dir-input/workorder_T2.md` v1，源码行号指 `d2d6641`。

上一轮实际 HEAD 为 `e3b5ac4`，工作区干净；`scripts`、`references`、`SKILL.md`、`commands-staging`、`VERSION`、`pyproject.toml`、`CHANGELOG.md` 相对 `d2d6641` 无差异，因此源码核验适用于指定基线。

支持原方案的最强理由：旧哈希可以由 Git 复现，源码已有历史准入机制；复用机制并限定 EVM/time，可以恢复文件案兼容，无需改 schema 或普通文件契约。

反对直接批准的最强理由：已有历史准入机制不代表新增条目能自动通过全部守卫；runner `inputs` 可选，也不代表显式登记目录能够通过。决定是否可施工的关键是守卫同步、两层真实调用、可复用测试，以及能让使用者照做的接口说明。

**a）锚与行号**

对指定目标行逐项实际执行了 `grep -n -F -x`。行号全部与基线一致，但不是每行都唯一：

| 目标 | 匹配数 | 结论 |
|---|---:|---|
| `producer_history.py:241` | 1 | 通过 |
| `producer_history.py:242`，原文 `    },` | 29 | 不能作为独立唯一锚 |
| `producer_history.py:243`，原文 `)` | 1 | 通过 |
| `shared_release_receipt.py:1221`、`:1459`、`:1460` | 各 1 | 通过 |
| `test_recon_deep_reverify.py:593`、`:601` | 各 1 | 通过 |
| `references/data-pipeline-evm-recon.md:152` | 1 | 通过 |
| `CHANGELOG.md:13`、`:100` | 各 1 | 实际整行唯一；工单对 `:13` 只给了前缀 |
| `SKILL.md:23`、`pyproject.toml:15` | 各 1 | 通过 |

工单 **L37 建议整段替换为**：

> 锚：`scripts/lib/producer_history.py:241` 整行 `        "reason": "Batch 4 registers the v3 formal Solana window producer frozen at the T1 tip.",` 与 `:243` 整行 `)`，分别以 `grep -n -F -x` 核验恰 1 处且行号一致；同时核对 `:242` 整行为 `    },` 且位于两锚之间。`:242` 仅作相邻结构核对，不作为唯一锚。在 `:243` 之前插入登记条目。

工单 **L110** 应补全 `CHANGELOG.md:13` 的整行原文：

```text
- **9.0.3**（2026-09-23）修复 v2 目录输入的时间抽查收据绑定（QUQ 0922 案 ANOM-008）：生产者目录输入时 inputs.input 绑 anchor_plan 已签名输入清单，发布消费者对 kind=directory 验证清单身份、不重算目录哈希；文件分支校验顺序保留。schema/键不变，references/SKILL/commands 字节不增；测试 +1 目录回归用例；版本档位 修。
```

**b）来源断言、登记守卫与实际准入**

① **旧哈希亲核通过。**

实际执行工单指定命令：

```text
git show b52cbedf230218e5da46334cf99b7111235e8367:scripts/lib/time_spotcheck.py | shasum -a 256
```

得到：

```text
87bbad2246f07afa2db4b37a7289fff2fc6ac16387284411e75104e1109f0a39
```

`f4f8056` 的同文件也得到该值。当前源码哈希为：

```text
050e33c70c220698fe4e5d8e8993e7f6ce0a91bd613219228ebf15fc2dbef4b2
```

② **历史集合的过滤语义成立，但“守卫原样 PASS”不成立。**

`historical_producer_hashes`：

- 先检查全表 `status` 是否合法。
- 收集全表所有 `REVOKED` 哈希。
- 返回匹配 `script`、`protocol`、`ACTIVE` 且不在撤销集合中的哈希。
- 撤销优先不局限于同一个 script/protocol。

基线查询时间生产者的 v3 历史集返回 `set()`。

将工单原条目**仅加入进程内**的 `PRODUCER_HISTORY`，运行未修改的 `test_producer_registry_current.py` 的 `main()`，得到：

```text
FAIL  登记脚本集合与守卫清单一致
FAIL  当前哈希 scripts/lib/time_spotcheck.py time-spotcheck/v3 050e33c70c220698fe4e5d8e8993e7f6ce0a91bd613219228ebf15fc2dbef4b2: 改了生产者文件必须同步登记 scripts/lib/producer_history.py(git show <commit>:<script> 可复现的哈希)
producer registry: 2 FAIL
```

返回码为 **1**。该新条目的 Git 哈希复现检查本身通过。

原因是该守卫不只检查 Git 复现：

- `:35-37` 限制登记脚本集合。
- `:39-50` 要求非 `HISTORICAL_ONLY` 协议登记当前哈希。
- `:53-68` 检查登记哈希与 Git 对象一致。

六键、64 位哈希、40 位 commit 等结构断言，实际位于 `test_anchor_plan_v3.py:375-384`，不能全部归为 `test_producer_registry_current.py` 的能力。

最小修正是扩充现有“只登记历史身份”的精确协议对。

文件：`scripts/tests/test_producer_registry_current.py:24`

**整行原文：**

```python
HISTORICAL_ONLY = {("scripts/lib/anchor_plan.py", "anchor-plan/v2")}
```

**替换后整行：**

```python
HISTORICAL_ONLY = {("scripts/lib/anchor_plan.py", "anchor-plan/v2"), ("scripts/lib/time_spotcheck.py", "time-spotcheck/v3")}
```

相同集合也可按项目风格展开为：

```python
HISTORICAL_ONLY = {
    ("scripts/lib/anchor_plan.py", "anchor-plan/v2"),
    ("scripts/lib/time_spotcheck.py", "time-spotcheck/v3"),
}
```

同时把该文件 **`:21-23` 注释**替换为：

```python
# 默认验证器接受当前源码哈希；以下精确 script/protocol 对仅登记历史哈希。
```

内存加入这个精确对后，守卫 `main()` 返回 **0**；没有删除断言或跳过 Git 复现。

工单同步改法：

- **L16**：测试白名单增加 `scripts/tests/test_producer_registry_current.py`。
- **L17**：删除该文件的“不改”限制，替换为：

> `scripts/tests/test_producer_registry_current.py` 仅允许扩充 `HISTORICAL_ONLY` 的上述精确对及同步注释，检查逻辑不变。

- **L28 末句**替换为：

> `test_anchor_plan_v3.py` 原样验证六键、哈希及 commit 格式；`test_producer_registry_current.py` 按上述精确登记同步后须 PASS。

③ **§2.2 对两个验证器的职责描述需拆清。**

`receipt_validate.py:81-142` 检查仓库内常规生产者文件和 inputs，但：

- 没有 `RECON_PRODUCERS` 白名单。
- 不检查调用者传入的历史集是否对应 `producer.path`。

`repo_ref_ok:122-135` 才检查给定路径白名单、仓库内文件及哈希。

两者均接受：

```text
当前源码哈希 ∪ 显式传入的历史集
```

历史集不替代当前哈希，也不跳过后续语义校验。`REVOKED` 在历史查询中剔除哈希；这两个通用验证器本身没有全局撤销查询。

工单 **L78 建议替换为**：

> `repo_ref_ok` 核给定路径白名单、仓库内文件及当前/历史哈希；`validate_receipt` 核仓库内常规文件、当前/历史哈希及输入绑定，不自行核 script 与历史集的对应关系。该对应关系由本次限定查询保证；`:1461` 后全部逻辑不变。

④ **两层缺一不可，wrapper 在 envelope 之前。**

实际顺序：

```text
wrapper runner :1448
→ 各 item producer :1459
→ :1461 调 validate_reconciliation_check
→ envelope :1221
→ target、schema、输入及语义校验
```

对 wrapper 与 receipt 的 producer ref 均为旧哈希的 OPN 类案：

| 接线状态 | 拒绝位置及错误 |
|---|---|
| 只登记、不接线 | `:1459`，`is not current repository script` |
| 只接 envelope | 仍在 `:1459` 拒绝，尚未进入 envelope |
| 只接 wrapper | 到 `:1221` 后报 `producer hash mismatch` |
| 两层都接 | 才能继续后续全部语义校验 |

允许读取的 OPN RED 日志确有 wrapper 层错误。本轮没有访问或重跑真实案卷。

**c）修法精确性、异常处理回归与私有函数**

从各层自身 ref 取 path，并先限定为 EVM/time 白名单成员，符合 `validate_receipt` 的调用契约。由于当前白名单只有 `scripts/lib/time_spotcheck.py`，**守住同一 path 条件后**，固定 script 与取 ref.path 等价。

anchor_plan `:1007-1019` 使用固定 script，并在后续 `repo_ref_ok` 再核白名单；它支持两种 plan schema，所以 protocol 取 `plan_schema` 有实际意义。本次仅支持 `time-spotcheck/v3`，固定 protocol 合理。

“v2 一定报 unknown schema”需要收窄：只有 producer 哈希已获准，且此前 target、verdict、mode 等检查通过，才会到 `:1404`。陌生哈希仍先报 hash mismatch。

**异常处理回归的具体复现场景：**

- 收据 JSON 内容为 `[]`。
- 调用 `validate_reconciliation_check`。
- `key="balance"`、`family="evm"`。
- 内存替身仅提供该 JSON 内容，不替换 envelope 校验逻辑。

结果：

```text
基线：
ValueError:
reconciliation balance receipt envelope invalid: receipt must be an object；存量案例须重跑对应生产者获取当前回执
```

```text
工单拟议代码：
AttributeError:
'list' object has no attribute 'get'
```

原因是新增的：

```python
producer_ref = receipt.get("producer")
```

在 `validate_receipt` 之前无条件执行。这影响其他 key，不符合“行为不变”。另外，`producer.path` 为 list/dict 时，新增的 set membership 也可能提前抛 `TypeError`。

建议将两层准入条件收为一个私有函数，同时保留非法输入原有的拒绝路径。

需要校准提示词中的一个前提：**工单 §1.5 原文只禁止新增公开函数，没有禁止私有函数。**

工单 **L29 建议替换为**：

> 生产代码不新增公开函数、import 或模块常量；允许一个私有历史准入函数及局部变量。测试允许局部导入既有夹具，旧哈希使用函数内常量。

在 `scripts/report/shared_release_receipt.py:1208` 的整行锚：

```python
def validate_reconciliation_check(root, key, item, target, family):
```

之前插入：

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

**§2.2(a) 的完整替换文本：**

工单 L56-64 改用以下代码，替换源码 `:1221`。

整行原文：

```python
    envelope_errors = validate_receipt(receipt, case_root=root)
```

替换为：

```python
    envelope_errors = validate_receipt(
        receipt, case_root=root,
        allowed_producer_hashes=_time_producer_history(family, key, receipt))
```

保留原 `:1218` 的 `migration` 及 `:1219-1220` 注释。

**§2.2(b) 的完整替换文本：**

工单 L68-76 改用以下代码，替换源码 `:1459-1460`。

原文：

```python
        repo_ref_ok(item.get("producer"), RECON_PRODUCERS[family][key],
                    f"reconciliation {key}")
```

替换为：

```python
        repo_ref_ok(
            item.get("producer"), RECON_PRODUCERS[family][key],
            f"reconciliation {key}",
            allowed_hashes=_time_producer_history(family, key, item))
```

抽函数的价值是使两层共用一份限定规则，并集中处理类型边界；节省代码行数不是主要理由。

边界结论：

- 其他 key、Solana：不给历史集。
- 默认不传历史集：仍不接受非当前旧哈希。
- 文件/目录原有的身份、清单及输入绑定校验：不跳过。
- 历史准入没有 `kind=file` 条件。满足现有目录语义的 EVM/time v3 收据，同样可以携带登记旧哈希过哈希关。不能宣称历史豁免在技术上只覆盖文件输入。

工单 **L27 建议替换为**：

> 仅放宽 EVM/time/v3 的指定生产者哈希准入，不改文件/目录语义校验；该准入不额外按 input.kind 分流。默认不传历史集时仍拒非当前旧哈希。receipt_kernel/receipt_validate 字节不变。

**d）回归消费面与 manifest 登记**

按要求检索 `scripts/report`、`scripts/lib` 中的 `time_spotcheck.json`、`checks["time"]`、`RECON_PRODUCERS`，并补查 `time_spotcheck`、`validate_receipt` 和 producer 哈希引用。未发现第三个需要独立接历史集的时间生产者哈希消费点：

| 消费面 | 核验结论 |
|---|---|
| `handoff_manifest.py:349/:483` | 共用 `validate_reconciliation_report` |
| `handoff_manifest.py` AUTO_GATES | 重读 verdict/exit_code，不独立核 time producer 哈希 |
| `audit_release_gate.py:111-127` | 经 witness/validate_bundle 回到同一深验 |
| `shared_release_receipt.py:2052/:2106/:2113` | 转调用同一入口 |
| `reconciliation_report.py:369` reseal | 调 `validate_reconciliation_check`，受 envelope 修复覆盖 |
| 普通 runner `run_job` | 重新执行当前生产者 |
| `migrate_legacy_case.py:154-165` | 检查 anchor receipt 在场并提示重跑，无独立 time 哈希准入 |
| `stage2_closeout.py:636`、`build_html.py:432-433` | 经 `audit_release_gate` 消费 |

`invariant_manifest`、`contract_manifest` 不需新增登记：未新增 schema、生产入口或发布入口；`CT-RECON-03` 仍匹配 `time-spotcheck/v3`。

`invariant_scan` 按文件内 schema 消费集合计数，不按 `validate_receipt` 调用次数计数。实际在内存套用工单两块代码后调用 `scan_python`，扫描前后结果完全相同；现有 `receipt_consumers` 合计 **118**，`time-spotcheck/v3` 已在集合中。

这项结果不是完整 `invariant_scan` 或完整测试已跑过的声明。

**e）测试向量与 H16 的 17 行接法**

六类向量覆盖核心兼容需求，但原写法需要调整：

- H11/H12/H13 保留；每次 mutation 后更新 receipt 引用哈希。
- H14 除“verify_recon path＋时间旧哈希”，补“time_spotcheck path＋时间旧哈希”的跨查项变体，并明确应在 envelope 哈希层拒绝。
- H15 不能只断言 errors 非空，应传 `case_root=root`，断言恰为 `["producer hash mismatch"]`。
- H16 直接调用 `repo_ref_ok` 的价值有限，通用历史准入机制已有测试；应优先覆盖真实 wrapper 调用路径。
- 补最小类型边界：非对象收据保持 `ValueError`；非法 producer.path 不提前抛 `TypeError`；Solana 不取得时间历史集。

校准上一轮关于 H14 的表述：这些变体验证跨查项准入边界，**不能单独证明每个冗余条件都不可删除**，因为 key 条件与 producer 白名单可能相互兜底。

已实际查到以下夹具：

1. `scripts/tests/test_handoff_manifest.py:73` 的 `make_case`，在 `:175-218` 构造包含 supply_truth 的 EVM 四查 wrapper，支持 token/as_of_block 参数。
2. `scripts/tests/test_repair_batch_d.py:776-799` 的 `t_a5_same_source_negative`，复用 `test_audit_release_gate.py:273` 的 `build_case`，并真正调用 `validate_reconciliation_report`。
3. `test_batch11_frozen_bundle_binding.py:95-158` 是 Solana 夹具，还替换了 `validate_reconciliation_check`，不适合作为本次 EVM 两层接线的证明。

结论：**可以在 ≤30 行内复用夹具接出真实 wrapper 向量。**

工单 **L88 建议替换为**：

> H16 必须复用 `test_handoff_manifest.make_case`，在同一 time_dir 生成 EVM 四查 wrapper，time 项指向 H11 收据，并调用真实 `validate_reconciliation_report`；禁止替换 `repo_ref_ok`、`validate_receipt` 或 `validate_reconciliation_check`。补一个只破坏 wrapper producer 哈希的负例。真实 OPN verify 是补充复验，不替代本向量。

**放置位置与整行锚：**

文件：`scripts/tests/test_recon_deep_reverify.py`。

在现有 `:593` 整行：

```python
def main() -> None:
```

之前定义工单要求的：

```python
def _test_time_producer_history(root, receipt):
```

在现有 `:601` 整行：

```python
        _test_time_authority_vectors(time_dir, time_receipt)
```

之后插入：

```python
        _test_time_producer_history(time_dir, time_receipt)
```

以下 17 行放在新函数 `_test_time_producer_history` 内，H11 已生成 `h11_item`、已定义函数内 `old_hash` 之后。H11 必须另写新收据文件，不能覆盖原始收据。

复用的 helper：

- 外部夹具：`test_handoff_manifest.make_case`
- 本文件：`_write_json`、`_expect_error`
- H11 的 `h11_item` 可由既有 `_mutate_receipt` 生成，内部已使用 `_item`/`_ref` 更新文件引用。

**完整 17 行：**

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

`make_case` 的 plan 夹具使用 `fixture_` 前缀，不覆盖 `_produce_time` 的 `anchor_plan` 绑定。它会写 `time_spotcheck.json`，所以必须让 wrapper 指向 H11 另写的文件。

本轮只读，没有运行这个会落盘的夹具。≤30 行结论来自实际源码核验和上述具体接法，不是绿测声明。现有白名单内的 `test_recon_deep_reverify.py` 即可落地；无需增加测试文件。

工单 **L86 替换为**：

> H14：balance 收据分别使用原 verify_recon path＋时间旧哈希、time_spotcheck path＋时间旧哈希，均须报 envelope producer hash mismatch；沿用同一模式核 Solana 分支不取得时间历史集。

工单 **L87 替换为**：

> H15：`validate_receipt(H11 收据, case_root=root)` 不传 allowed，断言结果恰为 `['producer hash mismatch']`。

**f）FR-03 两行改法、原文及字节核算**

runner `inputs` 确实可选：

- `_validate_spec:225` 使用 `spec.get("inputs")`。
- `_input_items:68-70` 对 `None` 返回 `[]`。
- `snapshot_inputs:78-94` 因而得到 `{}`。
- `run_job:237-238` 仅在非空时把 inputs 写入 wrapper。

内存调用确认：`None`、`{}`、`[]` 都得到空快照 `{}`。

但显式填写目录仍会失败：`:56/:85` 要求文件。`handoff_manifest:301-315` 只逐项消费 `data_map.files`，不会替使用者展开目录。因此这些契约无需修改，使用说明仍需写清。

允许材料没有提供 QUQ wrapper、OPN 案内 rglob 脚本和 172 件清单；OPN RED 日志只有校验错误。有关案内自动登记的断言只能标为“调度方提供，未独立核验”。

时间脚本的 `--input` 示例确实只见于 `references/data-pipeline-evm-recon.md:152`；整个 references 另有 `data-pipeline-evm-channels.md:217` 的 multicall_balances `--input`，属于另一命令。

建议改两行，合计净减 **7 B**。

文件：`references/data-pipeline-evm-recon.md:152`

**整行原文，UTF-8、不含换行：111 B**

```text
python3 scripts/lib/time_spotcheck.py --plan anchor_plan.json --input <生成plan所用的merged转账数据> \
```

**替换后整行：110 B**

```text
python3 scripts/lib/time_spotcheck.py --plan anchor_plan.json --input <生成plan的同一文件或v2目录> \
```

这明确要求使用生成 plan 时的同一输入。`v2` 指目录形态，不要求目录名字必须字面等于 `data/v2`。

文件：`references/data-pipeline-evm-recon.md:158`

**整行原文，UTF-8、不含换行：326 B**

```text
- 产物 `time_spotcheck.json`（`time-spotcheck/v3`，target 绑定 chain/token/final-block，并绑定 plan、plan receipt、文件/清单与逐笔 RPC transcript；verdict/exit_code 为 0 PASS/2 FAIL/1 检测自身失败禁当 PASS）；split-run 案是 READY 必备件＋AUTO_GATES（handoff_manifest 重读防手报）。
```

**替换后整行：320 B**

```text
- 产物 `time_spotcheck.json`（`time-spotcheck/v3`）绑定 target、plan/receipt、文件或清单及 RPC transcript；exit 0/2/1＝PASS/FAIL/ERROR。EVM READY 必备，AUTO_GATES 重读。目录输入时 runner `inputs` 可省略；若登记则填清单/叶子文件，`data_map.files` 填叶子，均不填目录。
```

字节算法：

```text
:152：110 − 111 = −1 B
:158：320 − 326 = −6 B
合计：(110 + 320) − (111 + 326)
    = 430 − 437
    = −7 B
```

两行换行符数量不变，因此计入换行后的净变化仍为 −7 B。

工单 **L9 建议替换为**：

> FR-03：源码确认 runner.inputs 可省略；显式登记时仍只接受文件，data_map.files 也只登记文件。时间脚本的 --input 示例仅见 references/data-pipeline-evm-recon.md:152。改 :152 明确生成 plan 的同一输入，压缩 :158 并说明 runner 与 data_map 的文件登记规则；合计 -7 B。案内 rglob 与 172 件登记为调度方提供信息，本轮未独立核验。

工单 **L16 的文档范围**改为：

> 文档 `references/data-pipeline-evm-recon.md`，仅 `:152`、`:158` 两行。

工单 **L30 的文档字节约束**改为：

> `references/**/*.md` 仅改 `references/data-pipeline-evm-recon.md:152/:158`，合计净减 7 B；`SKILL.md` 仅改版本号，字节不变；`commands-staging/*.md` 不变。

工单 **L91-105** 使用上述两组整行原文、替换文和字节算法替代；**L121** 对应记录实际两行变化及同口径统计结果。

本方案只补接口说明，不新增登记器，不要求发布期重算目录，也不处置 FR-02 的强制冻结关联。

**g）上下文、CHANGELOG 长度与版本档位**

原方案 references `+1 B` 符合工单自己的 `≤+1 B` 上限，但不等于字面意义的“上下文不增”。上述两行方案为 `−7 B`，可同时满足说明完整和净不增。

上一轮实测：

- `SKILL.md`：8021 B。
- `commands-staging/*.md`：合计 8789 B。
- 未读取 attic 或历史字节表，因此没有把 references 总量 929092 声称为独立复核值。

拟议 CHANGELOG 索引行为 **415 B**，现有 `:13` 为 **406 B**；所检查的后续既有条目为 192–1373 B，属于既有量级，不构成阻塞。

仍可压缩。工单 **L113 建议替换为**以下 200 B 索引：

```text
- **9.0.4**（2026-09-23）登记旧 time-spotcheck/v3 哈希并接通 EVM 时间收据两层校验，恢复存量文件案兼容；补充同一输入目录用法。schema 不变，版本档位 修。
```

Git commit、review 编号、测试和字节细节留在详细段。

**9.0.4 的“修”档位恰当**：恢复既有协议收据的兼容性，不新增 schema 或公共使用能力。

**h）开工条件、禁区冲突、越界及 FR-01 完整性**

FR-01 的“登记＋两层消费者接线”在工单中均已包含，没有漏掉 reviewer 所说“仅添加条目不够”的核心子项。但验收实现遗漏守卫同步，并把真实 wrapper 回归设为可豁免，不能判定闭环。

**开工 HEAD 条件冲突**

工单 L14 硬要求 HEAD=`d2d6641`；上一轮实际 HEAD=`e3b5ac4`，已经包含工单自身存档提交。按 v1 必然停工，尽管相关源码没有变化。

工单 **L14 建议整段替换为**：

> - 0.1 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。开工先跑并贴进 `T2_done.md`：`git status --short`（须为空）与 `git rev-parse --short HEAD`（记录实际 HEAD）。执行 `git merge-base --is-ancestor d2d6641 HEAD`，须 exit 0；执行 `git diff --quiet d2d6641 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`，须 exit 0，以确认工单存档未改变本次审查的生产、测试和文档基线。行号继续以 `d2d6641` 为准；任一检查不符停工。

该改法允许工单自身存档，不放宽源码基线。

**changelog_lint.py 与禁读 archive 冲突**

`changelog_lint.py:16` 指向：

```text
archive/CHANGELOG-archive.md
```

`:41` 实际调用归档解析。这与工单 L15 禁读 `archive/` 冲突。没有测试依赖豁免，就不能要求施工者原样执行。

工单 **L21** 从施工者必跑清单移出 `changelog_lint.py`，并追加以下原文：

> `changelog_lint.py` 会读取禁读的 `archive/CHANGELOG-archive.md`，本轮不执行；由调度方在获准环境原样执行并回传退出码及尾行，不删除或绕过其归档检查。

工单 **L117 整行替换为**：

> - 写入后由调度方在获准环境运行 `python3 -B scripts/tests/changelog_lint.py`，须 PASS，并回传退出码及尾行；本轮因禁读 archive 不执行该项。

工单 **L121 的测试记录要求**补入：

> `changelog_lint.py` 分别记录“调度方待验”或调度方回传的实际结果；未取得结果不得记 PASS。

**执行纪律与范围**

上一轮全程离线、只读，无 commit，无文件新增、修改或删除；未读取 `~/.codex/`、memories、`archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`、其他 maintenance、Desktop 或 Documents。

未调用外部 API，也未运行会创建临时案卷的完整测试。一次 shell heredoc 因只读环境无法创建临时文件而被拒，随后改用 `python3 -B -c`；没有因此创建文件。最终 `git status --short` 仍为空。

本次仅补发报告，没有执行工具或改变以上状态。

**汇总表**

| 项目 | 判定 | 意见 |
|---|---|---|
| a）主要锚点及行号 | 通过 | 指定行号均与基线一致 |
| a）`:242` 唯一锚 | 退回 | 该行出现 29 次，改为两侧唯一锚＋相邻结构核对 |
| a）CHANGELOG `:13` 锚文本 | 建议 | 补全整行原文 |
| b）旧哈希及 Git 来源 | 通过 | `b52cbed…`、`f4f8056` 均复现旧哈希 |
| b）登记守卫原样通过 | 退回 | 实测 2 FAIL；须同步精确 `HISTORICAL_ONLY` 对 |
| b）两层顺序与必要性 | 通过 | wrapper 在 envelope 之前，两层缺一不可 |
| c）path/protocol 限定 | 通过 | 精确限定合理，固定 v3 protocol 合理 |
| c）非法收据异常处理 | 退回 | `[]` 从 ValueError 变成 AttributeError |
| c）私有函数 | 建议 | 共用一个准入函数；v1 未禁止私有函数 |
| c）目录收据边界措辞 | 建议 | 明确历史准入不按 input.kind 分流 |
| d）第三消费点 | 通过 | 未发现第三处需独立接线的 time 哈希消费点 |
| d）manifest 与计数 | 通过 | 无需新增登记；拟议改动扫描集合不变，仍为 118 |
| e）H16 免测出口 | 退回 | 已有 EVM 四查夹具，给出 17 行真实路径接法 |
| e）H14/H15 与类型边界 | 建议 | 收紧错误断言，补跨查项及非法类型边界 |
| f）runner.inputs 可选 | 通过 | 源码与内存调用均证实 |
| f）个案 rglob/172 件断言 | 退回 | 允许材料不足以独立核验，必须标明来源 |
| f）FR-03 一行方案 | 退回 | 建议两行补全接口说明，净减 7 B |
| g）CHANGELOG 索引长度 | 通过 | 属既有量级；另给更短文本 |
| g）9.0.4 修复档位 | 通过 | 恢复兼容，不改 schema |
| h）开工 HEAD 条件 | 退回 | 改为记录实际 HEAD 并核源码基线未变 |
| h）changelog_lint 禁区冲突 | 退回 | 交获准调度方原样执行并回传 |
| FR-01 范围完整性 | 通过 | 核心三项均涵盖；验收条件仍须修订 |
| FR-02 | 建议 | 维持另单，本单不宣称整轮收官 |

**最终判定：退回 v1 修订。** 上述替换文本是可供调度方直接修订工单的建议；本轮未修改工单或实施补丁。
