# 批三（正式链纵切片）批内对抗审查报告

- **审查对象**：`/Users/uravvv/Documents/5.6筹码分析/r8-closure-worktree`，分支 `fix/r8-closure-20260806`
- **HEAD 核验**：`3df1234a5f293382dac3d1bad6748ca5405a824e`（符合工单 tip=3df1234），`git status --porcelain` 为空
- **区间**：`62efbf9..3df1234`，五 commit（B3-G1 `4ac3d04` / B3-G2 `d2e9409` / B3-G3 `73113ba` / B3-G4 `5c41f05` / 回填 `3df1234`），32 文件、+1155/-122
- **落真现状**：`formal_ready_chains()` = `{base, bsc, eth, sol}`，与 `formal_tier_chains()` 相等
- **纪律**：仓库零写入，临时件全在 `mktemp -d`，所有 Python 调用带 `PYTHONDONTWRITEBYTECODE=1`，未读 main 基线

---

## 一、总裁决

**BLOCK**。

| 定级 | 数量 | 编号 |
|---|---:|---|
| P0 | 0 | — |
| P1 | 0 | — |
| P2 | 1 | B3R-01 |
| P3 | 2 | B3R-02、B3R-03 |
| 点名问题 1 | P3（归批四挂账，不计入批内阻断） | B3R-Q1 |
| 观察 | 3 | OB-H、OB-I、OB-J |

**归因分布：新引入 3，半修残留 0，历史漏检 0。**

阻断依据：B3R-01 是本批重构引入的 fail-open 回归，同时违反 INV-03（verdict/exit code/进程退出必须一致）与 INV-04（失败产物不得留在可被正式消费的位置），且在两个 Solana producer 上同构存在。

**批三主体质量是好的**：三个纵切片测试真实（真实生产 CLI + loopback transport，零禁令 mock，无手写 PASS receipt 冒充正例），Solana slot/timestamp 边界全部 fail-closed，既有跨批回归件的改动逐条核对均属必然适配、无放松，suite 79/79 全绿。缺陷集中在"联合事务发布之后那道自检 raise"的处置路径上。

---

## 二、点名问题 1 的独立定级

### 结论：**P3，挂账批四，与你的预判一致。**

**现状核实**（`scripts/lib/chain_registry.py`）：

```python
_FORMAL_EVM = dict(
    ...
    handoff=True, audit_release=True, chain_attestation="evm-chain-id",
    vertical_slice_verified=True,      # 第 71 行，覆盖 eth/bsc/base
)
```

sol 记录第 138 行同样硬编码 `vertical_slice_verified=True`。`invariant_manifest.json` 本批只改了 schema→script 映射，未建立"声明 True 的链必须有对应纵切片测试在场且挂载"的绑定；`batch3-report.md` 对此零论证——三点与你的核查一致。

**与 R7-07 手工开关族病的距离——我判定为不同族**：

R7-07 的病灶是**结构性短路**：一个 `"formal": True` 布尔直接等于 readiness，绕过全部能力检查。批二把它改成 12 项能力闭合后，这个短路已被消除。现在 `vertical_slice_verified` 只是 12 项之一，缺任一项 readiness 即为假——它没有顶替其他 11 项的能力，不构成短路。整张 registry 本来就是声明式事实表，`labels_table=True`、`handoff=True` 同样是硬编码字面量，`vertical_slice_verified` 并不比它们更"手工"。

但有一点必须诚实指出，它使这项**比其余 11 项更需要机器绑定**：其余 11 项断言的是"代码里有没有这个适配器/生产者"，属**静态可验证**事实（scanner/manifest 能查脚本在不在）；而 `vertical_slice_verified` 断言的是"端到端测试跑通过了"，属**动态事实**，静态守卫天然更难绑定，也更容易在测试腐化后与现实脱节。所以它虽不是 R7-07 复发，却是 12 项里最脆弱的一项。

**定 P3 而非 P1/P2 的理由**：

1. **批三验收标准已实质达成**——这是决定性的。我独立验证了三个纵切片测试是真实的（见第四节）：真实生产 CLI 经 subprocess 执行、零禁令 mock、无手写 PASS receipt，loopback 只替换 HTTP 响应。所以 `vertical_slice_verified=True` 背后**有真实证据支撑**，不是空头声明。若纵切片测试是假的，我会直接升到 P1。
2. **现有防线非零**：`run_all.py` SUITE 显式挂载三个 `test_batch3_*.py`，删测试文件即红。绕过需"删文件 + 摘挂载"两步，且两步都在 diff 里可见，会被 review 与 diff→finding 映射拦截。
3. **反向绑定已存在**：`test_chain_registry.py`、`test_batch2_capability_matrix.py` 断言 `formal_ready_chains() == {四链}`，把 registry 改 False 会转红。缺的只是正向（True 但测试已不在）。
4. **同族一致性**：与 B1R-01 裸池守卫、OB-B labels 副本守卫同属"第二道机器绑定缺失"，三者一并归批四守卫工程处理，比零敲碎打更符合"减法周期"纪律。

**建议的批四守卫形态**（把两步绕过一并堵上，供批四采纳）：在 `invariant_scan.py` 增加一条——遍历 `CHAIN_REGISTRY` 中 `vertical_slice_verified=True` 的链，要求其对应纵切片测试文件**存在**且**在 `run_all.SUITE` 列表内**，双条件缺任一即红。这样"删文件"和"摘挂载"任一步都会被捕获。

---

## 三、发现清单

### B3R-01 ｜ P2 ｜ 主视角②失败分支审计（次④同族调用面）｜ 归因：**新引入**（`d2e9409`）

**联合事务发布后的自检 raise 触发时不撤回正式产物，且 PASS receipt 留在正式位置——exit 1 与落盘状态相矛盾**

**缺陷位置一**：`scripts/solana/window_fetch.py:238-243`

```python
            publish_txn(out_path, RawBytes(data_bytes), args.receipt, receipt)
            if partial.exists():
                partial.unlink()
            if __import__("hashlib").sha256(out_path.read_bytes()).hexdigest() != published["sha256"]:
                raise RuntimeError("联合发布后独立读者哈希不一致")
```

该 raise 发生在 `publish_txn` **已提交之后**，落入 `except` 块（`:249-257`）：

```python
    except Exception as exc:
        ...
        # 数据与完成 receipt 是一个发布事务：receipt 落盘失败时撤回本次正式文件。
        if published_current and out_path.exists():
            os.replace(out_path, partial)
        if backup and backup.exists():
            os.replace(backup, out_path)
        _publish_error(args.receipt, base_envelope, exc, run_id)
```

本批重构 PASS 路径时删除了 `published_current = True` 与 `backup = ...` 的赋值语句，两者恒为初始值 `False` / `None`（`:177-178`），因此**撤回逻辑成为死代码**，注释承诺的"撤回本次正式文件"完全落空。

**最小复现（破坏性注入，实测输出）**：

```
构造：realpath 临时根 + config.json；transport-only fake（net.curl_json 返回合法单块）
      monkeypatch window_fetch.publish_txn 使其写入与 data_bytes 不同的内容，
      模拟"事务提交后独立复核不一致"这一该检查专为捕获的场景
命令：window_fetch.main(["1","1", out, "--receipt", rcp, "--conc","1", "--endpoint", ...])

基线（未注入）：exit=0，out 存在，receipt verdict=PASS —— 正常
注入后：
  [window_fetch] ERROR → .../receipt.error.20260807T100839.493543Z.71246.json
  [window_fetch] 检测/提交失败（exit 1）: 联合发布后独立读者哈希不一致
  --- exit=1 ---
  out 文件存在: True
  out 内容: b'TAMPERED-NOT-THE-VERIFIED-BYTES\n'
  out 是否被撤回到 .partial: False
  receipt verdict: PASS | exit_code: 0 | schema: solana-window-fetch-receipt/v2
  目录残留: ['config.json','edges.jsonl','edges.jsonl.gaps.json',
             'receipt.error.<ts>.<pid>.json','receipt.json']
```

**比预期更严重的一点**：`_publish_error` 把错误回执写成**带时间戳的新文件**，并不覆盖 `receipt.json`。最终正式位置同时留下**未通过复核的数据**与**verdict=PASS 的回执**，仅退出码为 1。这正是 INV-03 所禁止的"verdict / exit code / 最终进程退出不一致"，以及 INV-04 所禁止的"失败产物留在可被正式消费的位置"。

**缺陷位置二（同构，未实测）**：`scripts/solana/anchor_sampler.py:288-290`

```python
        publish_txn(out, RawBytes(data_bytes), args.receipt, receipt)
        if __import__("hashlib").sha256(out.read_bytes()).hexdigest() != output_ref["sha256"]:
            raise RuntimeError("联合发布后独立读者哈希不一致")
    except Exception as exc:
        _error_receipt(args.receipt, base_envelope, exc)
```

同样在事务提交后自检并 raise，`except` 只调 `_error_receipt`（内部为 `publish_error_receipt`，同样写带时间戳的新文件），**连 window_fetch 那个已失效的撤回分支都没有**。我按④同族视角静态判定为同构缺口；受构造成本限制未实测，如实标注。

`scan_token_accounts.py:326-330` **不受影响**——它只做 `publish_txn` 并在失败时 `return 1`，没有事后自检 raise，而 `publish_txn` 自身是原子回滚单元（`receipt_kernel.py:361-401`）。

**触发可达性（如实评估）**：正常情况下 `publish_txn` 写入的就是 `data_bytes`，复核不会失败。真实触发路径是**并发**（两个实例写同一 out_path，A 提交后 B 覆盖，A 复核读到 B 的内容）或文件系统故障。作者主动加这道复核，说明认为该场景可能发生；既然认为可能发生，其处置失效即为真实缺陷。因触发需罕见外部条件、非攻击者可控，我定 **P2** 而非 P1；但由于同时违反两条核心不变量且产物层无兜底，若裁决方倾向从严，上调 P1 亦有充分依据。

**下游影响**：`solana-window-fetch-receipt/v2` 目前生产侧零消费者（`rg` 确认仅 producer 自身产出 + `invariant_manifest.json` 登记 schema），故坏 receipt 不会被直接消费；但**坏的 `edges.jsonl` 会进入正式分析链**（它是 Solana 边表，进 data_map 后由 handoff manifest 绑定哈希——若在 generate 之前即为坏内容，manifest 记录的就是坏文件哈希，自洽过闸）。

**修复建议**：把事后自检移到事务边界之内，或在 `except` 中恢复真实撤回——
1. 让 `publish_txn` 在提交前完成"写入内容 == 预期哈希"的校验（自检进事务），失败即走 kernel 自带回滚；
2. 若保留事后自检，则 `except` 必须把 `out_path` 移出正式位置（如 `os.replace(out_path, partial)`），并使 `receipt.json` 本身变为非 PASS（覆盖或删除），不能只旁写 error 文件；
3. 清除 `published_current` / `backup` 两个死变量，避免下一个读者误以为撤回逻辑仍有效；
4. anchor_sampler 按同一方案同步修（同族等深）。

---

### B3R-02 ｜ P3 ｜ 主视角①字段来源审计（次⑥闸可绕性）｜ 归因：**新引入**（`d2e9409`）

**生产代码为迁就旧测试的 mock 保留 2 元组兼容分支，且该分支使 receipt 的 timestamps 证据静默为空**

位置：`scripts/solana/window_fetch.py:182-187`

```python
    def work(seg):
        result = scan_seg(seg[0], seg[1], args.endpoint)
        if len(result) == 2:  # legacy test adapter; production returns bound timestamps.
            e, ok = result
            timestamps = []
        else:
            e, ok, timestamps = result
```

注释自认 "legacy test adapter"。其存在原因是本批给 `scan_seg` 增加了第三个返回值，而 `test_sixlens_receipts.py:232/244/251/258` 与 `test_r7_findings.py:199` 仍 `mock.patch.object(mod, "scan_seg", return_value=(edges, ok))` 返回 2 元组。正确做法是改这五处测试 mock，而不是在生产代码里加兼容分支。

**证据链后果**：走该分支时 `timestamps=[]`，receipt 的 `timestamps.segments` 记为 `{"min": None, "max": None}`。我 `rg` 全库确认**没有任何生产代码消费 window receipt 的 timestamps 字段**，因此该字段目前是只写不读的装饰性记录。本批"timestamp fail-closed"的真实防线在 `scan_seg` 内部（`:81-86` 的四条校验，见第五节，确实有效），但**落进 receipt 的时间戳证据无人校验、且可被兼容分支静默清空**。

**修复建议**：改五处测试 mock 为 3 元组返回，删除生产兼容分支；若要让 timestamps 成为真证据，需在下游（或 receipt validator）加"PASS 回执的 segments 时间戳不得全为 None"的校验。

---

### B3R-03 ｜ P3 ｜ 主视角⑤双向一致性 ｜ 归因：**新引入**（`5c41f05`）

**`diff-finding-map.md` 的 B3-G3 行文件清单多列一项，该文件实际归属 B3-G1**

map 的 B3-G3 行列出 16 个文件，其中含 `test_batch3_evm_vertical_slice.py`；但实测 `git show --stat 73113ba` 为 **15 文件**，且 `grep -c test_batch3_evm_vertical_slice` = **0**——该文件实际在 `4ac3d04`（B3-G1）中新增，而 B3-G1 行也已列出它。

属清单冗余（同一文件被两行认领），方向是"多列"而非"漏列"，**不产生未映射 hunk**，但违反 map"每个 hunk 有且只有一个 owner 行"的精度要求。

**修复建议**：从 B3-G3 行清单删除 `test_batch3_evm_vertical_slice.py`。

---

## 四、纵切片真实性纪律核查（工单重点 2）

### 4.1 禁令清单逐条比对

PLAN 禁令：端到端禁止 mock producer main、RPC 业务函数、scan 业务函数、receipt builder、runner、aggregator、validator；仅 transport 可 fake 并须登记。

| 测试文件 | mock/patch 命中 | 真实 CLI（subprocess） | 判定 |
|---|---|---|---|
| `test_batch3_evm_vertical_slice.py` | **零命中** | `accounting_gate.py`、`reconciliation_report.py`、`holder_distribution_scan.py`、`handoff_manifest.py generate/verify`、`shared_release_receipt.py`、`audit_release_gate.py` | **端到端合规** |
| `test_batch3_solana_vertical_slice.py` | **零命中** | `accounting_gate_sol.py`、`window_fetch.py`、`reconciliation_report.py`、`holder_distribution_scan.py`、`handoff_manifest.py`、`shared_release_receipt.py` | **端到端合规** |
| `test_batch3_solana_producers.py` | 有（`requests.post`、`net.curl_json`、`time.sleep`、`rpc_call`、`fetch_onchain_supply`、`subprocess.run`） | 否（`mock.patch.object(sys,"argv")` + 直调 `main()`） | **单元测试**，PLAN 明确允许"内部 mock 只能算单元测试" |

关键辨析：`test_batch3_solana_producers.py` 确实 mock 了 `rpc_call`（scan 业务函数）与 `fetch_onchain_supply`（业务函数），这在端到端里是禁令项——但它不是端到端件，而是 producer 负例单元集（`B3-SOL-PROD-01`～`06`）。端到端由 `test_batch3_solana_vertical_slice.py` 承担，该文件零 mock、走真实 `rpc_call` + loopback（与 transport 登记 `B3-SOL-E2E` 声明的 `scan_token_accounts.py:rpc_call` 一致）。**分层正确，无违规**。

### 4.2 loopback 是否只替换 HTTP 响应

`test_batch3_evm_vertical_slice.py:22-80` 的 `FixtureHandler` 只实现 `do_GET`（返 404）与 `do_POST`（按 `method` 返 JSON-RPC 结果 / 按 `/query` 返 HyperSync 结果）。它是纯 HTTP 层替身，不介入任何进程内函数。生产 CLI 通过 `--rpc/--hypersync/--sourcify` 指向该 endpoint。**符合 transport-only**。

### 4.3 正例是否真实生产 CLI 生成

`rg '"verdict":\s*"PASS"'` 在三个批三测试中**零命中**——无手写 PASS receipt 冒充正例。EVM 侧 `full_chain()`（`:163-205`）的做法是：先用 `make_case`/`build_case` 造基础案，随后**显式 unlink 掉全部 reconciliation 相关件与 shared receipt**，再由 `execute_real_slice()` 调真实 CLI 重新生成。这一"先删后真造"的手法有效排除了 fixture 残留冒充。**合规**。

### 4.4 transport 注入四条登记与实际代码对表

| 登记条目 | 声明 callsite | 实际 | 判定 |
|---|---|---|---|
| EVM JSON-RPC loopback | accounting_gate / verify_recon / supply_truth_gate / time_spotcheck → net.RpcPool | 相符 | 属实 |
| HyperSync `/query` | accounting_gate.py:hs_logs → requests.post | 相符（`FixtureHandler` `/query` 分支） | 属实 |
| Sourcify 404 | accounting_gate.py:check_permissions → requests.get | 相符（`do_GET` 返 404，走生产 404 分支；本批为此新增 `--sourcify` 参数） | 属实 |
| Solana JSON-RPC + SQD stream | accounting_gate_sol / scan_token_accounts.rpc_call / supply_truth_gate._post；anchor_sampler / window_fetch → net.curl_json | 相符（本批为此新增 `--endpoint` 参数） | 属实 |

四条登记均名实相符。一处表述偏宽见 OB-I。

---

## 五、Solana producer 边界外一步（工单重点 3）

### 5.1 冻结 slot 绑定可否被绕（slot 字段缺失/None）

生产判据（`scan_token_accounts.py:195-198, 245-248`）：

```python
    if supply_slot != args.as_of_slot:
        print(f"FATAL: getTokenSupply slot={supply_slot} != frozen slot={args.as_of_slot}", ...)
        return 1
...
        if gpa_slot != args.as_of_slot:
            print(f"FATAL: GPA slot={gpa_slot} != frozen slot={args.as_of_slot}", ...)
            return 1
```

解析侧实测（三种缺失形态）：

```
supply 无 context      : (None, 0, 10)
supply context 无 slot : (None, 0, 10)
gpa result 为裸 list   : ([], None)
gpa 有 context         : ([], 123)
```

三种缺失形态均得 `slot = None`，与 int 型 `as_of_slot` 比较恒不等 → `return 1`。**fail-closed，守住**，不存在"缺字段即放行"的软路径。

补充：`--as-of-slot` 为必填且 `< 0` 时 `ap.error`；`assert_distinct_paths(args.out, args.receipt)` 在写入前拦路径冲突。

### 5.2 window_fetch timestamp 校验边界

`window_fetch.py:81-86`：

```python
            ts = hdr.get("timestamp")
            if (isinstance(ts, bool) or not isinstance(ts, int)
                    or ts <= 0 or ts > 4102444800):
                page_valid = False
                break
```

| 边界 | 覆盖 | 说明 |
|---|:--:|---|
| `bool` 先查 | ✓ | `True`/`False` 是 `int` 子类，必须先排除，顺序正确 |
| 非 int（含 `None`、str） | ✓ | `not isinstance(ts, int)` |
| 0 与负数 | ✓ | `ts <= 0` |
| 上界 4102444800（2100-01-01） | ✓ | 防未来时间戳 |

四条边界完整，且失败走 `page_valid=False` → 段计入 `gaps` → `verdict=FAIL, exit_code=2`。**守住**。注意该校验的成果落进 receipt 后无人校验，且可被 B3R-02 的兼容分支清空。

### 5.3 anchor/window 联合事务失败路径

- `publish_txn`（`receipt_kernel.py:361-401`）内部为原子回滚单元：staged→backup→replace，任一步失败恢复双方；`committed=True` 之后的异常直接 `raise`，不做二次破坏。**事务内失败路径干净**。
- **事务外**（提交后的自检 raise）不干净——见 B3R-01。
- `test_sixlens_receipts.py:172-176` 有一条相关正向覆盖：mock `publish_txn` 抛 `OSError("disk full")`，断言 `not (work/"anchor_receipt.json").exists()`（"写回失败留下 PASS receipt"）。它测的是 **publish_txn 本身失败**，与 B3R-01 的"publish_txn 成功后自检失败"是不同分支，故未覆盖该缺口——印证盲区。

### 5.4 accounting `--as-of-slot` 与双字段下游一致性

`accounting_gate_sol.py:118-120` 同时写入两字段且同值：

```python
    result = {"schema": "accounting-gate/v1", "chain": "solana", "mint": a.mint,
              "as_of_slot": a.as_of_slot, "as_of_block": a.as_of_slot,
```

下游 `shared_release_receipt.validate_sources` 取 `accounting.get("as_of_block")` 构造 target，与 reconciliation wrapper 的 `target.as_of_block` 比对——两侧同源同值，**一致**。EVM 侧对称地新增 `result["as_of_block"] = tip`（`accounting_gate.py:426`）。未发现口径分叉。

---

## 六、EVM 错链反例的证明强度（工单重点 4）

### 6.1 计数机制

`test_batch3_evm_vertical_slice.py:43` 在 loopback **server 端**记录每个 JSON-RPC 方法：

```python
            method = body.get("method")
            type(self).methods.append(method)
```

断言（`:150-160`）：

```python
def wrong_chain_zero_business(case, chain, endpoint):
    prepare_inputs(case, chain, 100)
    FixtureHandler.chain_id = 999
    FixtureHandler.methods.clear()
    proc = run([... time_spotcheck.py ...], case, expect=1)
    assert proc.returncode != 0
    assert FixtureHandler.methods and set(FixtureHandler.methods) == {"eth_chainId"}, \
        (chain, FixtureHandler.methods)
```

**可信度评估：机制可信。** 三点理由：
1. 计数发生在 **fake server 收报文时**，不是客户端自报——任何业务 RPC 必须穿过 HTTP 才能到达，无法绕过计数；
2. 跑前 `methods.clear()`，排除前序污染；
3. `assert FixtureHandler.methods` 非空是关键的一半——它排除了"根本没发请求"的假通过，证明确实做了 chainId 探测后才停。

### 6.2 覆盖面的如实评估

`wrong_chain_zero_business` 只执行 **`time_spotcheck.py` 一个 CLI**，而 transport 登记把 test_id 写作 `B3-EVM-WRONG-ETH/BSC/BASE` 并列出四个 callsite（accounting_gate / verify_recon / supply_truth_gate / time_spotcheck）。声明覆盖面宽于实际执行面 → 记为 OB-I。

**不判为缺陷的理由**：错链零业务调用的逐调用点证明属批一职责，`test_batch1_rpc_attestation.py:190` 的 `test_each_formal_callsite_wrong_chain_zero_business` 已逐点覆盖（本批仅为其补 `final_block` 字段以适配新校验，见 7.1）。批三这条是端到端补充证明，不是唯一防线。

### 6.3 计数器的盲区

`do_POST` 中 `/query` 路径（HyperSync）走独立分支，**不进入 `methods` 计数**。若某个错链场景下发生了 HyperSync 调用，不会被这个断言捕获。当前 `wrong_chain_zero_business` 只跑 `time_spotcheck`（不调 HyperSync），故无实际影响 → 记为 OB-J，供扩展该反例到 `accounting_gate` 时注意。

---

## 七、既有测试适配有无削弱（工单重点 5）

逐一核对四个跨批回归件的改动，判断是"必然适配"还是"顺手放松"。

| 文件 | 改动 | 触发原因（生产侧） | 判定 |
|---|---|---|---|
| `test_batch1_rpc_attestation.py:193` | plan 增加 `"final_block": 10` | `time_spotcheck.py:101-105` 新增 `plan_final != a.final_block` 即 `return 2` | **必然适配**，断言强度不变 |
| `test_r7_findings.py:166,174` | mock 返回 slot `321`→`123`；断言 `observed_context_slot != 321`→`!= 123` | `supply_truth_gate.py:161-165` 新增 Solana `observed_context_slot != a.as_of_block` 即抛错 | **必然适配**。断言仍验证"receipt 记录了观测 slot 且等于 mock 值"，强度不变，仅取值随新约束调整 |
| `test_r7_findings.py:368,381` | 两处 plan 增加 `"final_block": 10` | 同上 time_spotcheck 新校验 | **必然适配** |
| `test_round4_identity_emitter.py:43-44` | argv 增加 `--as-of-slot 123 --out ... --receipt ...` | `scan_token_accounts.py` 三参数改必填 | **必然适配** |
| `test_sixlens_receipts.py:162,171,177` | `unlink()` → `unlink(missing_ok=True)` | anchor_sampler 改为末尾一次性发布，失败路径不再产出 `anchors.jsonl` | **适配**。严格说它移除了一个*隐含*断言（"上一步产生了该文件"），但该隐含断言并非测试目标，且新行为（失败不留数据）正是 fail-closed 改进 |
| `test_sixlens_receipts.py:174` | mock `publish_overwrite` → mock `publish_txn` | anchor_sampler 改用联合事务 API | **必然适配**。核心断言 `assert not (work/"anchor_receipt.json").exists(), "写回失败留下 PASS receipt"` **保留**，强度不变 |
| `test_sixlens_receipts.py:183` | `set(receipt["inputs"]["output"])` → `set(receipt["output"])` | anchor_sampler 把 output 从 envelope.inputs 移到顶层 `output_ref` | **必然适配**，仍校验 `{path,size,sha256}` 三键齐全 |
| `test_sixlens_receipts.py:159-162` | `no_converge(frm,to)` → `no_converge(frm,to,endpoint)` | `fetch_window` 新增 endpoint 形参 | **必然适配** |

**结论：八处改动全部为必然适配，未发现顺手放松的断言。** 未见删除断言、放宽比较符、或把负例改正例的情况。

### 7.1 harness 退化后旧 fixture 的正例价值

批三后 `formal_ready_chains()` 已真为四链，`formal_ready_test_harness.test_vertical_slices()` 的 patch 变为**幂等空操作**（把已为 True 的 `vertical_slice_verified` 再设 True）。本批相应改了 `formal_ready_test_harness.py`（8 行）与 `test_batch2_registry_harness_hardening.py`（4 行）、`test_batch2_capability_matrix.py`（9 行）的对表口径。

评估：旧 fixture 的正例价值**仍成立但性质改变**——它们从"靠 harness 才能走到 formal 分支"变成"生产本就 ready，harness 不再是前提"。这不削弱这些测试对各自契约的覆盖（它们验的是 handoff/A4/A5/release 契约，不是 readiness 本身）。harness 保留是合理的：它仍是 batch2 系列"退出后恢复原对象"等可逆性测试的被测对象，且若未来新增未验证链，它会重新变为有效开关。

### 7.2 批一批二边界抽查

| 抽查项 | 结果 |
|---|---|
| `test_batch1_rpc_attestation.py`（批一 RPC attestation 全套） | suite 内 PASS |
| `test_batch2_legacy_hardening.py`（含我第二/三轮的 B2F-LG-01~05） | suite 内 PASS |
| `test_batch2_registry_harness_hardening.py`（伪造 Mapping 拒绝、可逆性、字母序无泄漏） | suite 内 PASS |
| `test_batch2_robinhood_exploration.py`（RH 七面防回流 + 豁免哨兵） | suite 内 PASS |
| `test_chain_registry.py` / `test_batch2_capability_matrix.py`（能力矩阵对表） | suite 内 PASS |

**批一批二边界未回退。**特别确认：Robinhood 仍为 exploration、`formal_ready('robinhood')` 为假——四链落真未波及 RH 豁免。

---

## 八、未映射 hunk 独立复算（工单重点 6）

| 分组 / SHA | map 登记文件数 | `git show --stat` 实际 | 差异 |
|---|---:|---:|---|
| B3-G1 `4ac3d04` | 5 | 5 | 一致 |
| B3-G2 `d2e9409` | 8 | 8 | 一致 |
| B3-G3 `73113ba` | **16** | **15** | **多列 1**（`test_batch3_evm_vertical_slice.py` 实归 B3-G1）→ B3R-03 |
| B3-G4 `5c41f05` | 4 | 4 | 一致 |
| 回填 `3df1234` | 自指式 | 1（map 自身） | 一致 |

区间合计 32 文件（`diff-finding-map.md` 在 `5c41f05` 与 `3df1234` 各改一次，`--stat` 合并计一次，故 5+8+15+4+1=33 去重后为 32，吻合）。

**复算结果：未映射 hunk = 0。** 唯一偏差是 B3-G3 行"多列"（同一文件被两行认领），方向不产生无主 hunk，已记 B3R-03。

区间标注沿用第三轮确立的自指写法（`62efbf9..` 至本回填 commit 即候选 tip，并显式列出四个分组 SHA），与通例一致 ✓。

### "误落仓库的 6 个临时扫描产物已逐文件清理" 核实

- `git status --porcelain` → 空
- `find . -name "__pycache__" -not -path "./.git/*"` → 空
- `find . -maxdepth 2 -newermt 2026-08-06 -type f \( -name "*.json" -o -name "*.jsonl" \)` 排除台账与 manifest 后 → 空

**自报属实**，无夹带残留。

---

## 九、台账一致性比对（工单重点 7）

| 修复方陈述 | 我的独立核验 | 判定 |
|---|---|---|
| 四链纵切片为真实 producer→runner→aggregator→READY→release | 三个测试逐一核对：EVM/Solana E2E 零 mock 真实 CLI，producers 为单元级 | **属实** |
| transport 仅 fake 四条，已登记 | 四条与代码逐条对表相符（含本批为此新增的 `--sourcify`/`--endpoint` 参数） | **属实** |
| 错链业务 RPC=0 | 计数在 server 端、跑前清零、非空断言齐全，机制可信 | **属实**（覆盖面表述偏宽见 OB-I） |
| 临时扫描产物已逐文件清理 | git status 干净 + 无残留 | **属实** |
| suite 76→79 | 独立复跑 `全部通过 EXIT=0`，PASS 计数 **79** | **属实** |
| B3-G3 文件清单 | 多列 `test_batch3_evm_vertical_slice.py` | **不实**（清单冗余）→ B3R-03 |
| `batch3-report.md` 对 `vertical_slice_verified` 硬编码与测试在场性的绑定 | 全文零论证 | **缺项**（非不实）→ B3R-Q1 |
| anchor/window "data 与 receipt 联合事务发布并独立重算哈希" | 联合事务属实、独立重算属实；但**重算失败后的处置**未论证，实为不撤回 | **部分属实** → B3R-01 |

前三轮各抓到一处自报不实（harness"只在独立测试进程"、"reviews/ 零改动"、B2F-G3 清单漏列），本轮抓到一处清单冗余 + 一处"部分属实"，同一标准执行。

---

## 十、观察（不计入裁决）

- **OB-H**：`anchor_sampler.py` 由"逐天 append + `fsync`"改为"内存累积 `rows`，末尾一次性 `publish_txn`"。联合事务是批三的硬要求，但代价是 **resume 粒度从逐天退化为整轮**——长采集（数百天）中途崩溃/被 kill 时，本轮已完成天数全部丢失，下次从上次成功发布点重来。这是设计权衡而非 bug，但 `batch3-report.md` 未论证该退化，建议在运维文档注明，或考虑"周期性中间提交"折中。
- **OB-I**：transport 登记条目 `B3-EVM-WRONG-ETH/BSC/BASE` 列出四个 callsite，实际错链反例只执行 `time_spotcheck.py` 一个。逐调用点覆盖由批一 `test_each_formal_callsite_wrong_chain_zero_business` 承担，故非漏测，但登记表述宽于实际执行面，建议收窄措辞。
- **OB-J**：`FixtureHandler.do_POST` 的 `/query`（HyperSync）分支不计入 `methods`，错链断言存在计数盲区。当前反例不触发该路径，无实际影响；若将来把错链反例扩展到 `accounting_gate`，需先补上该分支的计数。

---

## 十一、执行命令清单

```bash
git -C <worktree> rev-parse HEAD                       # 3df1234a5f29...
git -C <worktree> diff --stat 62efbf9..3df1234         # 32 files, +1155/-122
git -C <worktree> show --stat --format="" <各 SHA>     # 映射复算
git -C <worktree> diff 62efbf9..3df1234 -- <逐生产文件>

# 静态核查
rg -n "mock|patch|monkeypatch" scripts/tests/test_batch3_*.py     # 端到端零 mock
rg -n '"verdict":\s*"PASS"' scripts/tests/test_batch3_*.py        # 无手写 PASS 正例
rg -n "solana-window-fetch-receipt" scripts/                      # 下游消费者
rg -n "published_current|backup" scripts/solana/window_fetch.py   # 死变量
rg -n "scan_seg" scripts/ | grep -v window_fetch.py               # 2 元组 mock 来源

# 动态验证（mktemp -d 的 realpath 根，全部 PYTHONDONTWRITEBYTECODE=1）
python3 $TD/inject.py <root>/base2 normal   # 基线 exit=0，产物正常
python3 $TD/inject.py <root>/inj2  inject   # 破坏性注入：exit=1 但坏数据+PASS receipt 残留
python3 $TD/slotedge.py                     # slot 缺失三形态均 None → fail-closed

# 全量回归与收尾
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py   # 全部通过 EXIT=0（79）
git -C <worktree> status --porcelain                         # 空
```

**方法自纠**：首次注入实验在 macOS `mktemp -d` 返回的 `/var/folders/...` 下运行，被 `_secure_target` 的逐级 symlink 检查拒于门外（`/var` → `/private/var`），两次跑都停在 `assert_distinct_paths` 的 exit 2，看似"守住"实为未进入被测路径。改用 `os.path.realpath` 解析后的根重跑才取得真实结论——这也反向印证了批一 receipt kernel 的 symlink 防护在真实文件系统上确实生效。

---

## 十二、复核方自我声明

- 仓库全程零写入：起止 `git status --porcelain` 均为空，无 `.pyc` / `__pycache__` 残留。
- 临时件全部位于 `mktemp -d`（含其 realpath 变体），所有 Python 调用带 `PYTHONDONTWRITEBYTECODE=1`。
- 未与施工线程通信；未读 main 基线、`~/.codex/`、MEMORY 或历史案例目录。
- 每条论断均先 Read 磁盘真实文件后作出。**已如实标注的未实测项**：`anchor_sampler.py` 的 B3R-01 同构缺口为静态判定（同族视角），受构造成本限制未做破坏性注入；window_fetch 侧已实测。
- 本次为批内对抗审查，非全库六视角扫描——"BLOCK/PASS"仅就本批区间与工单指定重点而言。
