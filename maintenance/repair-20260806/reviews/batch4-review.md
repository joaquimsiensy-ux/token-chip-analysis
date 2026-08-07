# 批四（守卫 / fixture / 方法论）批内对抗审查报告

- **审查对象**：`/Users/uravvv/Documents/5.6筹码分析/r8-closure-worktree`，分支 `fix/r8-closure-20260806`
- **HEAD 核验**：`6b7ab8dbd34ee21be0d99b3378186c36c36ecf9b`（符合工单 tip=6b7ab8d），`git status --porcelain` 为空
- **区间**：`f2a6e41..6b7ab8d`，四 commit（B4-G1 `ba6b98e` / B4-G2 `1850205` / B4-G3 `1e3d5a6` / 回填 `6b7ab8d`），8 文件、+774/-77，**生产业务代码零改动**
- **纪律**：仓库零写入（全部注入在 `mktemp -d` realpath 根的仓库副本内进行），所有 Python 调用带 `PYTHONDONTWRITEBYTECODE=1`，未读 main 基线

---

## 一、总裁决

**BLOCK**。

| 定级 | 数量 | 编号 |
|---|---:|---|
| P0 | 0 | — |
| P1 | 0 | — |
| P2 | 0 | — |
| P3 | 2 | B4R-01、B4R-02 |
| 观察 | 2 | OB-K、OB-L |

**归因分布：新引入 2，半修残留 0，历史漏检 0。**

两项均为守卫自身的边角缺口，不影响已落地守卫的有效性。**批四主体交付质量高**：我对五类守卫逐一做边界外一步注入，**七个变体守住、一个漏检、一个诊断劣化**；其中批三我建议的"删测试文件 + 摘 SUITE 挂载"两步绕过已被双条件堵死（实测两步同时注入仍红）。8 个注入反例真实、配绿例防误伤、tempdir 隔离干净；fixture"零过时"自报经我独立抽查证实；六脚本"发布路径外"经机器判据证实；方法论 41 行纯追加、零删除、内容无美化；未映射 hunk = 0 且清单与 commit 边界完全一致；suite 80/80 全绿。

---

## 二、发现清单

### B4R-01 ｜ P3 ｜ 主视角④同族调用面（次⑤双向一致性）｜ 归因：**新引入**（`ba6b98e`）

**labels 链清单守卫的分母遗漏一个同形态面，且未给出排除理由**

`invariant_scan.py:40-48` 的 `LABEL_CHAIN_SURFACES` 登记七个面。我用 `rg` 独立复列 `scripts/labels/` 下全部链清单字面量后，确认存在**第八个同形态面**未被登记：

```
scripts/labels/accumulate_offenders.py:249
        if chain not in ('eth', 'bsc', 'base', 'sol', 'robinhood'):
            continue
```

它与守卫**已覆盖**的 `build_goldset.py:87/187`（`membership:chain:2` 定位器）形态完全相同——同为 `chain not in (元组字面量)` 的成员判断，同在 `scripts/labels/` 下。

**最小复现（对照式破坏性注入，仓库副本内）**：

```
基线                          rc=0，labels 相关行：无
A) 已覆盖面注入未注册链 polygon（build_goldset.py:87）
   → rc=1  FAIL labels surface scripts/labels/build_goldset.py:membership:chain:2
            has unregistered chains ['polygon']          守卫工作
B) 未覆盖面注入同样内容（accumulate_offenders.py:249）
   → rc=0  零命中                                        守卫静默漏检
```

**定级演变（如实记录）**：我最初依据 `archive/fix-worklogs/fix_v635_stage1_20260806.md:95` 将 `accumulate_offenders.py` 视为已登记 formal entrypoint，据此定 P2。随后按 PLAN"archive/CHANGELOG 不得作为验收证据、当前代码才是"的纪律改用机器判据复核：

```
registered_formal_entrypoints() 共 16 项
accumulate_offenders 在 formal 入口内: []   （不在）
```

该脚本当前不在 formal 发布可达图内，故**下调为 P3**。这一下调由我自己发现的反证驱动，非采信施工方说法。

**为何仍记为 finding 而非观察**：`batch4-report.md` §2.4 只描述了两类语义分配，未声称全库穷举，故不构成"声明不实"；但施工方在 `fix_v635_stage2` 中有过对同类字面量（`CHAIN_MAP`/`DUNE_CHAIN`/`CHAIN_BY_ID` 等别名表）逐条列出"保留字面并登记"排除理由的先例，本批对 `accumulate_offenders` 的链清单面**既未纳入也未说明排除理由**，属分母不全。危害限于惯犯库（线索级消费输入）的链清单与 registry 静默漂移。

**修复建议**：二选一——(a) 把该面加入 `LABEL_CHAIN_SURFACES`（`("scripts/labels/accumulate_offenders.py", "table", "membership:chain:1")`）；(b) 若有意排除，在 `batch4-report.md` 增列"已评估但排除的面 + 理由"小节，与 `fix_v635_stage2` 的排除表体例一致。

---

### B4R-02 ｜ P3 ｜ 主视角②失败分支审计 ｜ 归因：**新引入**（`ba6b98e`）

**`registered_formal_entrypoints()` 的派生源不合法时抛未捕获 `KeyError`，而非产出明确守卫诊断**

`invariant_scan.py:159-175` 直接对派生源做字典下标：

```python
    accounting = shared["ACCOUNTING_PRODUCERS"]
    producers = shared["RECON_PRODUCERS"]
    for family in families:
        paths.add(accounting[family])
        for allowed in producers[family].values():
            paths.update(allowed)
```

`families` 来自 `CHAIN_REGISTRY` 中 formal-ready 链的 `accounting_adapter`；`accounting` / `producers` 来自 `shared_release_receipt.py` 的 AST 字面量。两侧一旦不同步即 `KeyError`。

**最小复现（实测）**：把 `shared_release_receipt.py` 的 `ACCOUNTING_PRODUCERS` 改为 `{}`，跑 `invariant_scan.py`：

```
rc=1
        paths.add(accounting[family])
                  ~~~~~~~~~~^^^^^^^^
KeyError: 'solana'
>>> 是否异常逃逸(Traceback): True
```

**性质与危害**：退出码非零，**方向仍是 fail-closed，不造成假通过**。缺陷在可诊断性——运维看到的是 Traceback 而非"派生源缺 family 登记"的明确错误，且与守卫正常 FAIL 同为 exit 1、无法区分。更现实的触发场景不是"改坏代码"，而是**未来新增一条使用新 adapter family 的 formal 链**：registry 加了、`shared_release_receipt` 未同步，此时应得到"registry 与 producer registry 不同步"的清晰诊断，而非 KeyError。

**修复建议**：改为显式检查并追加 error——

```python
    missing = [f for f in families if f not in accounting or f not in producers]
    if missing:
        return None, [f"formal adapter family not registered in shared_release_receipt: {sorted(missing)}"]
```

或在调用处 `try/except KeyError` 转成 scanner error，使其与其他守卫的错误形态一致。

---

## 三、观察（不计入裁决）

- **OB-K｜裸池守卫对 import-as 别名不可见**。`BareRpcPoolVisitor.visit_Call` 判据为 `name == "RpcPool" or name.endswith(".RpcPool")`。实测：直接 `RpcPool('http://wrong')` → **红**（精确到 `fetch_alchemy.py:46 (main)`）；`from net import RpcPool as _P; _P('http://x')` → **静默**。`getattr(net,"RpcPool")()` 同理不可见。这落在"守卫防误用不防恶意"的威胁模型内，工单已允许如实记观察。唯一建议：`batch4-report.md:112` 的"任一……裸池……都会追加 scanner error"措辞略宽于实现（同报告 `B4-RPC-01` 行用了"**直接**"限定，是准确的），建议统一为"直接构造或属性访问构造"，并注明别名重绑定不在检测面内。
- **OB-L｜方法论第七节缺一条本轮反复付出代价的验收纪律**。第七节 7.4 写了"站到边界外一步再造变体"，但没有写"**必须自证注入真的到达了被测分支**"。这是本工程实测中反复出现的坑：我在批三消化两次遇到"看似有结论、实则没进入被测代码"——一次是 macOS `mktemp -d` 的 `/var/folders` symlink 被 `_secure_target` 在入口拒绝（exit 2 被误读为"守住"），一次是预建 `.partial` 目录被 `assert_distinct_paths` 提前拦下。建议 7.4 补一条：「注入反例必须断言命中**目标错误文本**，而非仅断言非零退出；退出码相同不等于走了同一条分支。」这属内容缺项而非写错，故记观察。

---

## 四、五类守卫的边界外一步（工单重点 1 —— 本批核心）

全部注入在仓库副本（`mktemp -d` realpath 根 + `shutil.copytree`）内进行，每组独立副本，原仓库零改动。

| # | 守卫 | 注入构造 | rc | 实测命中 | 判定 |
|---|---|---|---:|---|---|
| 1 | 裸池 | `fetch_alchemy.py` 内直接 `RpcPool('http://x')` | 1 | `FAIL bare RpcPool construction: scripts/evm/fetch_alchemy.py:46 (main)` | **守住** |
| 2 | 裸池 | `from net import RpcPool as _P; _P('http://x')` | 0 | 零命中 | **漏检** → OB-K（威胁模型内） |
| 3 | 纵切片 | 映射表删除 `sol` 条目（模拟新增 formal 链无映射） | 1 | `FAIL vertical slice mapping missing for sol` | **守住**（映射表自身漂移有守） |
| 4 | 纵切片 | 摘 `run_all.SUITE` 的 EVM 纵切片项 | 1 | `not mounted in run_all.SUITE`（base/bsc/eth 三链各一条） | **守住** |
| 5 | 纵切片 | **删测试文件 + 摘挂载两步**（我批三提出的绕过） | 1 | `test file missing` + `not mounted` 双条命中 | **守住**（B3R-Q1 双条件落地有效） |
| 6 | 分母 | `invariant_manifest.json` 整键删除 `formal_entrypoints` | 1 | `FAIL formal_entrypoints: denominator shrank below floor 58 -> 0` | **守住**（不止防收缩，整键删除也红） |
| 7 | labels | 已覆盖面注入未注册链 `polygon` | 1 | `has unregistered chains ['polygon']` | **守住** |
| 8 | labels | 未覆盖面注入同样内容 | 0 | 零命中 | **漏检** → B4R-01 |
| 9 | 派生源 | `ACCOUNTING_PRODUCERS = {}` | 1 | `KeyError: 'solana'` Traceback | **fail-closed 但诊断劣化** → B4R-02 |

### 4.1 逐项补充结论

- **裸池守卫的白名单精度**：豁免条件是 `rel == "scripts/lib/net.py" and locator == "attested_rpc_pool"`——同时绑定文件与**所在函数名**，不是整文件放行。若有人在 `net.py` 的其他函数里裸构造，仍会红。精度良好。
- **labels 两类语义分配正确**：`known` = `known_chains_for_release()`（含 arbitrum/robinhood 两条 exploration 链），`table` = `capability_chains("labels_table")`（含 robinhood）。**exploration 链在资产面未被逐出**——这正确，RH 的 `labels_table=True` 是既有能力事实，与 release tier 解耦（批二 RH 豁免七要素之一即"labels 表存在不抬升 tier"）。B4-LABEL-02 反例（摘掉 `BUILD_CHAINS` 的 robinhood → 红）正面锁住了这一点。
- **纵切片 SUITE 检查用 AST 而非字面 grep**：`_suite_entries()` 解析 `run_all.py` 的 `SUITE` 赋值与 `AugAssign`（`SUITE += [...]`）两种形态，比 grep 稳健——注释掉的行不会被误算为已挂载，字符串拼接改写也不会被 grep 蒙混。
- **纵切片反向绑定也在**：`for chain in sorted(set(mapping) - verified)` 会对"映射表里有但 registry 未验证"的链报错，双向对齐。

---

## 五、8 个注入反例的真实性（工单重点 2）

逐条核 `scripts/tests/test_batch4_invariant_guards.py`（136 行）：

| 反例 | 注入的是真违规样本吗 | 断言抓的是守卫红吗 | 绿例防误伤 |
|---|---|---|---|
| B4-RPC-01 | 真写 `from net import RpcPool` + `RpcPool('http://wrong')` 到临时文件 | `any("bare RpcPool" in e ...)` 精确文本 | `assert scan.bare_rpc_pool_errors() == []` |
| B4-LABEL-01 | 真改 `KNOWN_CHAINS` 加 `ghost` | `"unregistered" and "ghost"` | 有 |
| B4-LABEL-02 | 真删 `BUILD_CHAINS` 的 `robinhood` | `"missing labels_table chains" and "robinhood"` | `assert label_chain_surface_errors() == []` |
| B4-VS-01 | 真摘 `run_all.py` 的 SUITE 行 | `"not mounted in run_all.SUITE"` | 有 |
| B4-VS-02 | 映射改指 `test_does_not_exist.py` | `"test file missing" and "sol"` | `assert vertical_slice_errors() == []` |
| B4-INV17-01 | 真写 urllib 样本与变量 `cmd=['curl',...]` 样本 | `assert "urllib" in scan_python(...)[2]` / `"curl" in ...` | — |
| B4-INV17-02 | `manifest["formal_entrypoints"].pop()` | `"denominator" or "formal_entrypoints"` | 另断言三个必经 producer 在派生集内 |
| B4-RH-COUNT-01 | 文档 16/15 改成 15/14 | `"Robinhood inventory"` | `assert robinhood_inventory_errors() == []` |

**结论：八条全部真实。** 三点具体核验：

1. **断言抓的是守卫红而非碰巧异常**——全部用 `any(<精确错误文本> in error for error in errors)` 形式对返回的 error 列表做文本匹配，没有一条是 `assertRaises` 式的"只要抛异常就算通过"。
2. **每组配绿例**——五组在注入断言后紧跟 `assert scan.XXX() == []`（对真实仓库跑一次），确保守卫不误伤当前状态。这是"破坏性注入反证"的完整形态（坏例死 + 好例活）。
3. **注入清理干净**——`main()` 用 `tempfile.TemporaryDirectory` 包裹全部四个用例，每例再分配 `root/<index>` 子目录；`_copy_label_surfaces` 把源文件 `copyfile` 到临时根后才改。我复核后 `git status --porcelain` 为空，**未污染仓库**。

一处覆盖面比自报更宽：`B4-INV17-02` 只测了"pop 一个 entrypoint"，我另测"整键删除"同样红（第四节 #6），守卫比反例声称的更强。

---

## 六、fixture 审计"零过时"独立核验（工单重点 3）

自报方法（`batch4-report.md` §3）：范围 `scripts/tests/` 共 88 个文件，用 schema/legacy/API 全文 `rg`，聚焦 handoff 65 项与 B2 legacy hardening。该方法可复现，我据此独立抽查三个面：

**抽查①：手写 PASS receipt 的用途边界。** `rg '"verdict":\s*"PASS"' scripts/tests/*.py` 命中 8 个文件（p105 / sixlens / round4_a5_seal / reconciliation_runner / handoff_manifest / formal_chain_support / audit_release_gate / distribution_gate）。逐一看用途：均为**契约/validator 单元 fixture**（构造一个 receipt 交给校验器解释），符合方法论 7.5"手写 PASS receipt 只可用于单元 schema/validator fixture"。批三三个端到端件（`test_batch3_*`）此前我已确认零手写 PASS。**未见冒充端到端执行证据者。**

**抽查②：四个高频 schema 的生产定义 vs 测试引用一致性。**

| schema | 生产定义处 | 测试引用 | 一致 |
|---|---|---|:--:|
| `reconciliation-report/v2` | `scripts/report/reconciliation_report.py` | 3 文件 | ✓ |
| `shared-release-receipt/v1` | `scripts/report/shared_release_receipt.py` | — | ✓ |
| `solana-holder-snapshot/v3` | `scripts/solana/scan_token_accounts.py` | — | ✓ |
| `time-spotcheck/v2` | `scripts/lib/time_spotcheck.py` | 2 文件 | ✓ |

**抽查③：是否有测试断言已废弃的旧 schema（"字面绿、语义过时"的典型形态）。** `rg` 命中五处，逐个判读：

| 位置 | 旧 schema | 判读 |
|---|---|---|
| `test_handoff_manifest.py:435` | `wave-scan/v1` | **负例**（构造旧版断言被拒，见该文件 docstring 第 12 条） |
| `test_handoff_manifest.py:493` | `handoff/v1` | **负例**（legacy-read-only 路径测试） |
| `test_handoff_manifest.py:516` | `provenance-ledger/v1` | **负例**（freeze 溯源闸拒 v1） |
| `test_adjudication_validator.py:339` | `wave-scan/v1` | **负例** |
| `test_round4c_solana_provenance.py:51` | `solana-holder-snapshot-v2` | **现役并存 schema，非过时** |

最后一条最需要辨析，我做了独立确认：`scan_token_accounts.py` 现在**同时产出两代产物**——第 281 行的 `holders_snapshot_meta.json`（`solana-holder-snapshot-v2`）与第 299/313 行批三新增的 `solana-holder-snapshot/v3` + `-receipt/v3`；消费侧也分两路：`identity_snapshot_receipt.py:81` 要求 v2，`shared_release_receipt.py:153` 要求 receipt/v3。两代**并存服务不同证据链**，`invariant_manifest.json:230-232` 也同时登记三个 schema。故该 fixture 引用 v2 是正确的现役用法。

**结论：fixture"零过时"自报核验通过**，我未找到漏网的过时正例。

---

## 七、六脚本"发布路径外"判定抽查（工单重点 4）

抽 `trace_wallet` 与 `whale_deep` 两个，用**机器判据**而非仅 rg：

```
registered_formal_entrypoints() 共 16 项
  trace_wallet     在 formal 入口内: False
  whale_deep       在 formal 入口内: False
  stake_decode     在 formal 入口内: False
  build_evolution  在 formal 入口内: False
```

消费链复核：`trace_wallet` 的全库引用仅 `invariant_manifest.json`（登记）、`scripts/solana/README.md`（文档）与 `whale_deep.py`；而 `whale_deep.py:14` 对它的"引用"是 **docstring 中的分工说明**（"与 trace_wallet.py 的分工：trace_wallet 查 owner 级签名……"），**不是 import，无代码依赖**。`whale_deep` 自身被 `stake_decode.py` / `build_evolution.py` / 采集文档提及，同样不进 `scripts/report/` 发布链。

**判定属实：两者均在 formal 发布可达图之外。**

---

## 八、方法论写回核验（工单重点 5）

- **只追加**：`git diff --numstat` = `41 0`（41 行新增、**0 行删除**），既有一至六节逐字未动 ✓
- **内容与工程事实一致，未见美化**。逐条抽验：
  - 7.1 "连续三次消化仍引入新代码问题就冻结"——与 PLAN 止损条款一致，且这是对施工方**不利**的条款仍如实写入；
  - 7.3 引用的三条映射通例与我历轮提出的原文一致，且已含 B3FR-01 修正后的新通例（"物理归属行与语义 owner 行互相注明"）；
  - 7.4 "正例先删旧产物，再由真实 producer 重新生成"——对应批三 EVM 纵切片 `full_chain()` 的真实做法；
  - 7.5 transport 五字段与手写 receipt 边界——与 `transport-injections.json` 实际体例一致。
- **缺项（记 OB-L，不算 finding）**：未写"验收注入须自证到达目标分支"。至于 codex 后台任务僵死/假完成、客户端流中断这类**执行工艺坑**，我判断不属本文件定位（它是"给维护会话的修复闭环方法论"，僵死一类在 MEMORY 的专门条目有落点），未写不构成缺陷。

---

## 九、未映射 hunk 复算（工单重点 6）与 B3FR-01 修正核验（重点 7）

### 9.1 映射复算

| 分组 / SHA | map 登记 | 实际 `--stat` | 一致 |
|---|---:|---:|:--:|
| B4-G1 `ba6b98e` | 4 | 4（`invariant_scan.py`、`invariant_manifest.json`、`test_batch4_invariant_guards.py`、`run_all.py`） | ✓ |
| B4-G2 `1850205` | 1 | 1（`maintenance-review-repair.md`） | ✓ |
| B4-G3 `1e3d5a6` | 3 | 3（`ledger.md`、`diff-finding-map.md`、`batch4-report.md`） | ✓ |
| 回填 `6b7ab8d` | 自指式 | 1（map 自身） | ✓ |

**未映射 hunk = 0，且清单与 commit 边界逐文件吻合**——B3FR-01 确立的新通例（"清单以实际 commit 边界为准"）在本批被正确执行，Fable 回填时自称的"已核验一致"经我独立复核**属实**。

### 9.2 B3FR-01 修正核验

map 现行两行与实际 commit 对照：

| 行 | map 文件清单 | 实际 commit 文件 | 一致 |
|---|---|---|:--:|
| `B3F-G1` | `{window_fetch.py, anchor_sampler.py}; test_batch3_solana_producers.py` | `75d112f` = 同三项 | ✓ |
| `B3F-G2` | `{test_sixlens_receipts.py, test_r7_findings.py}` | `7c04b72` = 同两项 | ✓ |

互注表述亦已到位：B3F-G1 行注明"物理兼含 `B3R-02` 的 window_fetch timestamps hunk 与 `B3F-TS-01` 反例（语义 owner 见 B3F-G2 行）"；B3F-G2 行注明"其生产侧 hunk……因文件级 commit 物理落于 `B3F-G1`=`75d112f`，本行为语义 owner"。**修正与事实一致，B3FR-01 闭合。**

---

## 十、台账一致性与回归（工单重点 8）

| 修复方陈述 | 我的独立核验 | 判定 |
|---|---|---|
| 8 个注入反例红→绿 | 逐条核对构造与断言，全部真实 | **属实** |
| "scanner 无跳过参数；测试注入全部在系统临时目录，不改生产/labels/references 资产" | 复核后 `git status --porcelain` 为空 | **属实** |
| transport census 覆盖 requests/urllib/httpx/aiohttp/net/字面 curl/变量 curl | 代码逐条确认，且 `B4-INV17-01` 实测两类新增识别有效 | **属实** |
| labels 两类语义分配（known 六链 / table 五链） | 与 `known_chains_for_release()`、`capability_chains("labels_table")` 一致 | **属实** |
| fixture 审计零过时 | 三面独立抽查未见漏网 | **属实** |
| 六脚本未进入 formal release | 机器判据 + 消费链双验 | **属实** |
| 方法论"只追加闭环章节" | `numstat` = 41/0 | **属实** |
| `full-F-04` RH 数字动态守卫 | `robinhood_inventory_errors` 从磁盘逐次计数，注入 15/14 即红 | **属实** |
| suite 79→80 | 独立复跑 `全部通过 EXIT=0`，PASS 计数 **80** | **属实** |

**本轮未发现自报不实**（前五轮各抓到一处）。

**批一~三边界抽查不回退**：`test_batch1_rpc_attestation`、`test_batch2_legacy_hardening`、`test_batch2_registry_harness_hardening`、`test_batch2_robinhood_exploration`、`test_batch3_evm_vertical_slice`、`test_batch3_solana_vertical_slice`、`test_batch3_solana_producers` 均在 80/80 内 PASS。生产业务代码本批零改动，无回退面。

---

## 十一、执行命令清单

```bash
git -C <worktree> rev-parse HEAD                     # 6b7ab8dbd34e...
git -C <worktree> diff --stat f2a6e41..6b7ab8d       # 8 files, +774/-77
git -C <worktree> diff --numstat f2a6e41..6b7ab8d -- references/maintenance-review-repair.md   # 41 0
git -C <worktree> show --stat --format="" <各 SHA>   # 映射复算

# 独立复列 labels 面（B4R-01 的发现路径）
rg -n "'eth'.*'bsc'|\"eth\".*\"bsc\"|'eth'.*'base'" --glob 'scripts/labels/*.py' .

# 破坏性注入（仓库副本，realpath 根，全部 PYTHONDONTWRITEBYTECODE=1）
python3 $RT/g1.py <copy>   # labels 已覆盖面 vs 未覆盖面 对照注入
python3 $RT/g2.py <copy>   # 裸池×2 / 纵切片×3 / 分母 / 派生源 共 7 组

# 机器判据
python3 -c "... registered_formal_entrypoints() ..."   # 六脚本与 accumulate_offenders 归属

# 全量回归与收尾
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py   # 全部通过 EXIT=0（80）
git -C <worktree> status --porcelain                         # 空
```

---

## 十二、复核方自我声明

- 仓库全程零写入：所有破坏性注入在 `shutil.copytree` 出的副本内进行；起止 `git status --porcelain` 均为空。
- 临时件位于 `mktemp -d` 的 realpath 解析根，所有 Python 调用带 `PYTHONDONTWRITEBYTECODE=1`。
- 未与施工线程通信；未读 main 基线、`~/.codex/`、MEMORY 或历史案例目录。
- **一处定级演变已如实披露**：B4R-01 最初依据 `archive/fix-worklogs` 定 P2，后按 PLAN"archive 不得作为验收证据"纪律改用机器判据自我反证，下调为 P3。
- 本轮为批内对抗审查；"BLOCK"仅就本批区间与工单重点而言，两项 P3 均为守卫边角，不否定本批守卫主体的有效性。
