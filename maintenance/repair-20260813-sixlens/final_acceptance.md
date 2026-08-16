# 最终快照验收（六视角修复工程 A–D 四批收口）

验收人：Fable 5（独立总验，未参与任何一批施工/盲审）
快照：`main@aed974e`，VERSION `6.40.0`，工作树干净（`git status` 空），`origin/main` 与本地同点
依据：`plan.md` §验证方案（最终快照验收，经盲审重写）第 1–6 条（第 7 条 commit+push 归裁判）
纪律：生产树只读；一切注入实验在副本 `/private/tmp/final_probe/repo`（rsync 全量副本，排除 .git）
原始日志：`/private/tmp/final_probe/`（run_all.log / ce_*.log / tb_*.log / lint_*.log / notes.md）

---

## 条 1：run_all 全量绿 ＋ SUITE 显式清单在列

**执行记录**

- `python3 scripts/tests/run_all.py` → **RC=0**，末行「全部通过」；日志 99 行，96 条 `PASS` 行，`FAIL` 计数 0。
- SUITE 与磁盘双向对账（自写脚本，解析 `run_all.py` 中 `def main` 之前的全部 `'*.py'` 字面量）：
  - 磁盘 `scripts/tests/test_*.py` 共 **87** 个；
  - 不在 SUITE 的 test 文件：**[]**；SUITE 有而磁盘无：**[]** ——**双向完全一致，无漏挂、无幽灵条目**。
- 本工程新增测试文件（`git diff --stat 2ebd885..aed974e -- scripts/tests/`）只有四个：
  `test_repair_batch_a.py` / `_b.py` / `_c.py` / `_d.py`，**四个全部在 SUITE 显式清单**
  （a/b/c 在主列表，d 由 `SUITE += ['test_repair_batch_d.py']` 追加，注释标 v6.40.0）。
- 四批工单里出现过的全部测试文件名（`grep` 抽取，17 个）逐一核对：全部存在于磁盘且全部在 SUITE。
  其余为存量文件的扩写（`test_a4_gate` / `test_audit_release_gate` / `test_handoff_manifest` /
  `test_state_from_facts` / `test_review_20260804_p105` / 两条 batch3 纵切片 / `test_distribution_gate`），本就在列。

**judgment：PASS**

---

## 条 2：反例矩阵逐条重放（plan :91-93）

`counterexamples/` 五个脚本**独立重放，全部 rc=0**：

| 脚本 | rc | 命中记录（摘） |
|---|---|---|
| `waiver_swap_integrity.py` | 0 | A 变长替换 643→658 命中 `input tolerance_waiver size mismatch`；B 等长替换 643=643 命中 `input tolerance_waiver hash mismatch` |
| `fake_series_dualfeed.py` | 0 | 末点对账拦 A（伪 sidecar 自洽）／单一事实源拦 B（双喂）／绿例 C 不误伤 |
| `flip_receipt_chain.py` | 0 | 五反例＋freeze 重验＋A5 实文披露核对全绿 |
| `refresh_txn_rollback.py` | 0 | 字节回滚原样／回滚失败保留 `.recover`／只读目录 exit 2 |
| `closed_audit_failopen.py` | 0 | 五场景退出码与 status 契约全对齐 |

清单其余条目逐条定位到实现载体并**逐条独立执行**（自写 driver 单函数调用，非整文件跑）：

| plan 清单条 | 实现载体（文件::用例） | 执行结果 |
|---|---|---|
| 拒 F-02 超钳容差无 waiver | `test_repair_batch_a.py::test_f02_formal_cap_and_exploration` ＋ `::test_f02_waiver_negatives_and_failures` | rc=0；条 3 中独立注入命中 `正式模式 --tolerance-bps 上限为 10；超出必须提供 --tolerance-waiver` |
| 拒 F-03 快照缺口 | `test_repair_batch_b.py::test_f03_snapshot_gap_rejected` ＋ `::test_f03_overshoot_rejected` | ok「快照缺口 99% 被拒」「超发 1 wei 被拒」 |
| 拒 F-03 同值换仓 EVM | `test_repair_batch_b.py::test_f03_gate_evm_same_total_swap` | ok「EVM initial 同值换仓被拒」（同用例先落合法绿例） |
| 拒 F-03 同值换仓 Solana | `test_repair_batch_b.py::test_f03_gate_solana_not_skipped` | ok「initial 同值换仓被拒」「终态 final 换仓被拒」「bundle 缺 owners 绑定被拒」 |
| 拒 F-04 值域／闭合／日期轴／白名单外键 | `test_repair_batch_c.py::t_f04_payload_unit` | 负值／超 100／NaN／合计 60／合计 130／legacy 桶名／实体级自造桶名／日期倒序／日期重复／非法日期／时区换算倒挂 **全部被拒** |
| 拒 F-04 伪序列双喂 source 与 --series-source | `counterexamples/fake_series_dualfeed.py` ＋ `test_repair_batch_c.py::t_f04_evm_chain`（「伪序列双喂被末点对账拦」「手填 series 与 producer 分叉拒」） | rc=0 |
| 拒 F-05 跨阵营重复＋大小写变体＋JSON 重复键 | `test_repair_batch_c.py::t_f05_unit` ＋ `::t_f05_f04_build_evolution` | 跨营重复／跨营大小写变体／同营内重复／同营内大小写变体／solana 字面同址跨营／值非列表／空阵营名 全拒；`load_addr_camp_json` 与 `build_evolution` 两处 JSON 重复键在**解析层** exit 2 |
| 拒 F-06 无收据翻转＋指纹不匹配旧收据 | `counterexamples/flip_receipt_chain.py`（`test_repair_batch_d.py::t_f06_trace_receipt_chain` 等三函数） | rc=0；条 3 独立注入命中 `裁决收据指纹与当前三策略明细不符——底层数据已变化，旧裁决失效，须重新裁决`（`handoff_manifest.py:803-804`） |
| 拒 F-08 记录项缺件／错 sha／错 size／越界／符号链接 | `test_repair_batch_b.py::test_f08_forged_records_rejected`（缺件/错 sha/错 size）、`::test_p2b5_receipt_path_whitelist`（越界＝白名单外，文件真存在且 sha/size 正确仍拒）、`::test_f08_illegal_receipt_producer_rejected`（符号链接，生产侧 exit 2） | 全拒 |
| 拒 GPT-F-06 mock RPC 全失败／部分失败／checked=0 且 closed>0 | `counterexamples/closed_audit_failopen.py`（`::t_gptf06_closed_audit`） | rc=0，五场景 |
| 绿例 F-01 双时点 `as_of=1, tip=100` | `test_repair_batch_a.py::test_f01_shared_evm_timing_and_legal_dual_time` 第三段 | rc=0，`validate_sources(root)["as_of_block"]==1` |
| 绿例 F-03 dead-sink 20%（sum=total≠net） | `test_repair_batch_b.py::test_c_deadsink_synthetic_green_under_mint_anchor` | ok「合成 dead-sink 20%（sum=mint≠net）在 mint 锚点下仍绿」 |
| 绿例 F-04 Solana burn 案 | `test_repair_batch_c.py::t_f05_f04_solana_chain` | ok「SOL 序列行内 burn 桶在场」「F04 Solana 端到端绿例（含 burn）」「sol 转换器：锁仓/销毁保留」 |
| 绿例 F-04 合法多阵营案 | `test_repair_batch_c.py::t_f04_evm_chain` ＋ `::t_f05_evm_engines` | ok「replay_pass2 合法 spec 绿例」「EVM 端到端绿例（含 burn）」 |
| 绿例 F-08 磁盘有 receipt 但 scan 未记录仍 PASS | `test_repair_batch_b.py::test_f08_unrecorded_disk_receipt_passes` | ok |

**F-07 断言核对（plan 明文点名）**：`test_repair_batch_d.py::t_f07_refresh_transaction` 第二段
断言体为 `rc == 2 and after == originals and residue == []`，其中
`originals = {p: p.read_bytes() for p in dones}`、`after = {p: p.read_bytes() for p in dones}`
——**断言对象确为「全部 done.json 逐字节与注入前相同」**，不是「报错干净」；另附命中标志断言
（`calls["n"] >= 4` ＋ stderr 含注入串），先证到达提交分支。条 3 中我用自己的注入独立复现。

**F-08「越界」口径说明（诚实记录，非缺口）**：消费侧 `validate_scan` 先做 path 白名单
（`UPSTREAM_RECEIPT_WHITELIST` 只允许 `channels_preflight.json` / `holders_snapshot_meta.json`），
白名单严格强于「案根越界」检查，因此越界形态必被白名单先拒，无法单独走到 `relative_to` 分支；
案根越界的独立定向用例在 `test_repair_batch_a.py::test_n1_replay_stats_must_live_inside_case_root`
（该用例注释已如实写明是被更靠前的 `validate_receipt(case_root=…)` 拦下）。

**judgment：PASS**（清单每一条都找到载体、都独立跑过、结果与清单一致）

---

## 条 3：破坏性注入反证抽查（12 道，A/B/C/D 各 3 道）

全部在副本 `/private/tmp/final_probe/repo` 上跑，注入脚本 `/private/tmp/final_probe/inject.py`
（注入与断言均由验收人自写，不复用四批测试的断言）。每道：注入坏产物 → 断言**命中目标分支的具体错误文本** → 还原 → 复绿核对。

| # | 注入 | 命中标志（实测原文，截断） | 命中 | 还原复绿 |
|---|---|---|---|---|
| A-1 | F-01：EVM accounting `as_of=101 / tip=100` 倒挂 | `EVM accounting as_of_block must be <= tip_block` | ✅ | ✅ 改回 `as_of=1/tip=100` → `validate_sources` 通过 |
| A-2 | F-02：formal 模式 `--tolerance-bps 10000` 且不给 waiver | `正式模式 --tolerance-bps 上限为 10；超出必须提供 --tolerance-waiver`（rc=2、无收据落盘） | ✅ | ✅ 补合法 waiver 后 rc=0 且收据落盘 |
| A-3 | F-02：waiver `approved_tolerance_bps=5000` < 收据 tolerance 10000（sha/size 已重绑，掉包闸不代劳） | `supply_truth tolerance exceeds waiver approved_tolerance_bps` | ✅ | ✅ 改回 approved=10000 → 消费侧放行 |
| B-1 | F-03：快照少 10^6 wei（mint 60127382 vs 快照 59127382） | `BLOCK: distribution data_broken: 快照 raw 和未对铸造总量 mint 精确闭合: 快照=59127382 mint=60127382（supply_truth_mint）容差=0bps`，rc=2 | ✅ | ✅ 还原 mint → rc=0 |
| B-2 | F-08：`upstream_receipts[0].sha256` 改 `0*64` | `scan 不可重验: 上游收据哈希或大小漂移: channels_preflight.json` | ✅ | ✅ 还原字节 → `validate_scan` 返回空 |
| B-3 | F-03 第二层：EVM initial 同值换仓（总和不变、owner 分配互换，重跑 scan 绑到 alt 快照） | `分布快照未绑定对账 owner 快照: initial distribution_scan 的快照 sha256 与四查 balance 收据的 inputs.balances 不一致（同值换仓也逃不掉）` | ✅ | ✅ 基线 errors=[]、还原（scan+data_map+alt 一起还原）errors=[] |
| C-1 | F-05：`{camp_A:[X], camp_B:[X]}` 跨阵营重复 | `[camp-spec] camps 地址 0xa00…01 同时归入阵营「camp_A」与「camp_B」…阵营互斥…`，SystemExit 2 | ✅ | ✅ 换合法 spec → 返回两阵营 |
| C-2 | F-04：序列值 `-899.0` | `桶「大庄」[0] 为负: -899.0`（SeriesProvenanceError） | ✅ | ✅ 40/60 合法载荷通过 |
| C-3 | F-04：日期轴倒序 `2026-01-02, 2026-01-01` | `日期轴非严格递增：dates[1]='2026-01-01'（UTC …）不晚于前一点（UTC …）——倒序/重复/时区换算倒挂都不许` | ✅ | ✅ 正序通过 |
| D-1 | F-06：flip 收据 `flip_fingerprint` 换成 `deadbeef*8` | trace rc=2，`裁决收据指纹与当前三策略明细不符——底层数据已变化，旧裁决失效，须重新裁决`（与「未获裁决收据覆盖」分支文案不同，确证走的是指纹分支） | ✅ | ✅ 换回机械重算的真指纹收据 → rc=0 |
| D-2 | GPT-F-06：`getMultipleAccounts` 返回 None（批失败） | 报告 `status=INVALID_SAMPLE`、`invalid_reasons=["getMultipleAccounts 批失败 1 批（存活/销户判定对这些账户是盲的）"]`、rc=1 | ✅ | ✅ 换正常 mock → rc=0 `status=NO_CLOSED_SAMPLED`（边界弱结论，不冒充零漏） |
| D-3 | F-07：第 4 次 `os.replace`（＝第二文件提交）抛 OSError | 到达标志 `calls=6 ≥ 4` ＋ stderr 含 `acceptance-injected`；rc=2；两份 done.json **字节全等注入前**；残留列表 `[]` | ✅ | ✅ 无注入重跑 rc=0，两 run 全升 v3 |

均以「具体错误文本 / status 字段 / 字节全等」为命中判据，**没有任何一道靠非零退出码凑数**。

**judgment：PASS**

---

## 条 4：端到端绿例与六卡死点

**EVM 同案连续链（t_fd3）实跑**：`test_repair_batch_d.py::t_fd3_e2e_single_case_evm` rc=0，四段接缝逐个绿：

- ① `ok F-D3 ① state_from_facts formal 编译（series 绑定链）`（`provenance.series_binding == "producer-sidecar"`）
- ② `ok F-D3 ② figures check 末点对账＋留痕收据（同案）`（`figure2_check_receipt.json` verdict=PASS）
- ③ `ok F-D3 ③ A4 finalize 同案封口 figures/state 产物`（`a4_seal.workflow_type=new-analysis`）
- ④ `ok F-D3 ④ A5 seal 同案收口（state→figures→A4→A5 全链一案贯通）`

数据面为批 C 真实 `replay_duck` 产物（mint 1000 / burn 50 的 dead-sink 形态），非手搓 JSON。

**六个卡死点逐一定位＋实跑**：

| 卡死点 | 覆盖用例（文件::用例名） | 实跑证据 |
|---|---|---|
| Solana tip | `test_repair_batch_a.py::test_f01_solana_not_subject_to_tip_check`；端到端＝`test_repair_batch_d.py::t_b1_b2_solana_new_analysis` | rc=0（Solana accounting 抹掉 tip_block/model_probe_block 仍通过前缀校验）；`ok B-2 Solana new-analysis run() 端到端绿例（发布闸零 error）` |
| A5 终态重验 | `test_repair_batch_d.py::t_fd3_e2e_single_case_evm` ④；发布必经路绿例＝`test_repair_batch_b.py::test_f03_gate_evm_same_total_swap` 基线 | `ok F-D3 ④ …`；条 3 B-3 实测基线 `errors=[]`；接入点核实在 `audit_release_gate.py:1145-1152`（`a5_report_seal.validate_seal` 入 `run()`） |
| Solana series | `test_repair_batch_c.py::t_f05_f04_solana_chain` | `F04 Solana 端到端绿例（含 burn）`、`F04 sol 转换器：锁仓/销毁保留、_supply_raw 剔除、ts 转 ISO` |
| 末点对账 | `t_fd3` ②；误伤查＝`test_repair_batch_c.py::t_fixround1` | `ok F-D3 ② …`；`NC4 误伤查① formal 正常产物复算放行`（同函数内两条造假被拦：`NC4 同步一致造假被 sidecar 实物强制拦下`、`NC4 自造 sidecar 全套绑真件仍被末点对账复算拦下`） |
| dead-sink 闭合 | `test_repair_batch_b.py::test_c_deadsink_synthetic_green_under_mint_anchor`；`t_fd3` 数据面 | `ok 锚点c 合成 dead-sink 20%（sum=mint≠net）在 mint 锚点下仍绿` |
| burn 合计 | `test_repair_batch_c.py::t_f04_payload_unit`（`F04 净分母 burn>100 合法绿例`、`F04 total 分母 burn 参与闭合绿例`、`FC4 burn 案单式绿例（净族）`、`FC4 burn 案单式绿例（total 族）`、反向 `F04 burn 桶负值拒`）；Solana 行内桶＝`t_f05_f04_solana_chain`（`SOL 序列行内 burn 桶在场`） | 全部在 `PASSED` 名单内（本次独立跑取 `C.PASSED` 实测，命中 12 条 burn/末点相关绿例） |

**Solana 拼接段声明核对**：`batchD_ledger.md` §二d 第二条如实写明——
「EVM 已建同案连续链（t_fd3）；Solana 的 state→figures 段仍由批 C 另案链承载，同案接入的夹具成本
超消化轮预算——下轮或 R10 一并补（与 r10 C-R3 的 sol 真实案端到端同批做最省）」。
我独立复核批 C 的 Solana 链确实止于 `compile_state`（`t_f05_f04_solana_chain` 末尾读 `analysis-state.json`，
不进 figures/A4/A5），与该声明一致，**没有拿两案拼接冒充同案连续链**。

**judgment：PASS**（六卡死点全有绿例并实跑；EVM 四段接缝一案贯通；Solana 同案连续链缺口已如实声明——见 NOTE-1）

---

## 条 5：版本收口

**执行记录（全部独立跑）**

- 三处版本：`VERSION`=`6.40.0`；`SKILL.md:23` `<!-- skill-version-source: VERSION; skill-version: 6.40.0 -->`；
  `pyproject.toml:15` `version = "6.40.0"` —— **三处一致**。`test_version_consistency.py` 独立跑 rc=0。
- `changelog_lint.py` rc=0（版本号唯一、顺序正确；活跃 26 条＋归档 139 条）
- `docs_lint.py --all` rc=0（58 个文档，引用无断链、粗体配对完整）
- `invariant_scan.py` rc=0（receipt_producers=54 / consumers=63 / transport=62 / atomic_writes=46 / formal_entrypoints=58 / exceptions=0）
- `test_contract_routes.py` rc=0；我另做独立双向对账：`contract_manifest.json` 146 条（全唯一）
  vs `contract_ids_snapshot.json` 146 条（全唯一），**两向差集均为空**。
- CHANGELOG `[6.40.0]` 条目覆盖面核对：批 A/批 B/批 C/批 D 四段齐全；
  **两笔追认在场**——「流程债追认（D-1）：`11193f6`/`b9f8871` 两笔无版本号提交在此追认…禁止倒插历史版本号」；
  **R10 声明在场**——「R10 台账（本轮未修，台账保留）…→ `r10_ledger.md`」；另有 D-3 存量迁移后果三条。
- `r10_ledger.md` 在场。**实际条目 15 条**（编号 R10-1…R10-15，无跳号无重号），分节计数：
  一、存量 6；二、GPT 加深 2；三、批 C 转入 3；四、批 D 评估 2；**四b、批 D 消化轮 1 追加 2**（R10-14 freeze 自身完整性锚、R10-15 `check_bound_file` 绝对路径无案根强制）。

**发现的账实不符（BLOCKER-1）**

台账文件本身正确（15 条，含批 D 消化沉淀件），但**两处引用停在 13 条**：

1. `CHANGELOG.md:58` 的 R10 条目枚举「存量 6 条＋加深 2 条＋批 C 终验 3 条＋批 D 评估 2 条」＝13，
   **未列消化轮 1 追加的 R10-14/15**；
2. `batchD_adversarial.md:39` 明文断言「r10_ledger 13 条与 CHANGELOG 的『6＋2＋3＋2』口径对得上」，
   而该盲审文件的落盘时间（08-14 01:09）晚于 R10-14/15 的追加（`batchD_fixround1_workorder.md:82`
   已登记「r10_ledger.md | R10-14 追加」），**该断言在写下时已经失真**；
3. `batchD_workorder.md:118` 同样写「r10_ledger.md（13 条）」。

性质：文档口径级，不影响任何机器闸（plan :96 明文只要求「CHANGELOG 显式注明本轮未修、台账保留」
＋「台账文件落盘含 GPT 修法建议与加深项」，这两点都满足）。但按本次验收的核账口径「条目数与各处引用一致」，
**记 FAIL**。修法＝改 CHANGELOG 那一行的枚举为「…＋批 D 消化轮 1 追加 2 条（freeze 完整性锚、
check_bound_file 案根强制）」共 15 条，并把 `batchD_adversarial.md:39` 的「13 条对得上」订正。

**judgment：FAIL**（三处 6.40.0、四 lint、契约 146 双向闭合、CHANGELOG 覆盖面全部 PASS；
唯一失分＝R10 台账条目数与 CHANGELOG／两份工单引用不一致，15 vs 13）

---

## 条 6：R10 弱闸旁证独立重跑

不引用 `test_commands_deploy_sync.py` / `env_check.py` 的 rc=0，全部自测。

**① 三命令 staging vs 部署 SHA（`shasum -a 256` 直算，2026-08-14）**

```
token-analyze.md    staging=f227da3bddcee26b6a5d89fd325026a46bd208dd4f18017b670bf97f1280296e  deployed=同值  EQUAL
token-analyze-1.md  staging=9832eace6960bb6626a2b6e55f4c88745c5ffa33c640bc7eb97c71544aa0f215  deployed=同值  EQUAL
token-analyze-2.md  staging=510152a8a40efcc3f9b9a166b17d612b5166365baca22a6554771014cadebce6  deployed=同值  EQUAL
```

部署目录 `~/.claude/commands/` 实际内容＝三个现役 md ＋ 三个 `.bak_*` 退役备份
（`collect-data.md.bak_20260805_021359`、`token-easy-analysis.md.bak_20260805_012552`、
`token-update.md.bak_20260805_012552`）——退役件已改名，不占现役文件名，迁移窗口关闭。
与 `batchD_workorder.md §九` 记录的三个 SHA **逐字符相同**（先例记录属实，非事后补写）。

**② 解释器与全部直接依赖 version＋import 实测**

解释器 `Python 3.14.6`（`/usr/local/bin/python3`），满足 `requires-python >=3.14`。
从 `pyproject.toml [project].dependencies` 机械抽取 **21 个**直接依赖，逐个 `importlib.metadata.version`
＋逐个真 `import`：

```
duckdb 1.5.4 / pyarrow 25.0.0 / pandas 3.0.3 / numpy 2.5.0 / hypersync 1.2.0 / requests 2.34.2 /
certifi 2026.6.17 / httpx 0.28.1 / tenacity 9.1.4 / msgspec 0.21.1 / networkx 3.6.1 /
rustworkx 0.18.0 / hypothesis 6.158.1 / psutil 7.2.2 / matplotlib 3.11.0 / reportlab 5.0.0 /
pypdf 6.14.2 / PyMuPDF 1.27.2.3（import fitz）/ openpyxl 3.1.5 /
google-cloud-bigquery 3.42.2（import google.cloud.bigquery）/ pydata-google-auth 1.9.1
```

**21/21 版本满足声明下界、21/21 import OK、0 异常**，与批 D 工单 §九记录逐项一致。

**judgment：PASS**

---

## 汇总

| 条 | 结论 |
|---|---|
| 1 run_all 全量绿＋SUITE 在列 | PASS |
| 2 反例矩阵逐条重放 | PASS |
| 3 破坏性注入反证（12 道） | PASS |
| 4 端到端绿例＋六卡死点 | PASS |
| 5 版本收口 | **FAIL**（R10 台账 15 条 vs 引用 13 条） |
| 6 R10 弱闸旁证独立重跑 | PASS |

**BLOCKER**

- BLOCKER-1：R10 台账账实不符。`r10_ledger.md` 实际 15 条，`CHANGELOG.md:58` 枚举 13 条、
  `batchD_workorder.md:118` 写「13 条」、`batchD_adversarial.md:39` 断言「13 条…对得上」。
  文档口径级、不影响机器闸；修法＝CHANGELOG 那一行补上批 D 消化轮 1 追加的 R10-14/15，
  并订正两份工单/盲审文件的计数。

**NOTE（台账级）**

- NOTE-1：plan :95 字面要求「EVM＋Solana 各一条走完 `state_from_facts→figures→A4 finalize→A5 seal`
  的端到端用例」，Solana 侧只到 `compile_state`，figures/A4/A5 段仍由另案承载。
  已在 `batchD_ledger.md` §二d 如实声明并指向 R10（与 C-R3 同批做最省），**不是隐瞒**，
  但严格论 plan :95 的 Solana 半条未兑现。
- NOTE-2：F-08 的「越界」形态在消费侧被 path 白名单先拒，走不到 `relative_to` 分支；
  白名单严格强于越界检查，故无实害。案根越界的独立定向用例在
  `test_repair_batch_a.py::test_n1_replay_stats_must_live_inside_case_root`，
  且该用例注释已如实写明是被更靠前的 `validate_receipt(case_root=…)` 拦下（报错换岗，已在
  `batchD_ledger.md` §二d 第一条登记为断言精度记账项）。
- NOTE-3：`~/.claude/commands/` 中三份 `.bak_*` 退役备份长期在场；`test_commands_deploy_sync.py`
  的 `RETIRED` 集合按原名判断，改名备份不会被拦。不影响本轮，登记备查。

**终判：有阻塞须处理**——六条中五条 PASS，唯一失分是 BLOCKER-1 的文档计数账实不符（一行 CHANGELOG 改动即可清）。
除此之外，机器面（全量 suite、反例矩阵、12 道注入、六卡死点绿例、契约 146 双向闭合、弱闸旁证）**全部独立复现通过**，
工程实体质量达到可交付标准。

最终快照验收完成

---

## BLOCKER-1 清账复核

复核快照：`main@1315751`（`aed974e` → `1315751`），工作树干净，`origin/main` 与本地同点。

**① CHANGELOG 枚举 vs `r10_ledger.md` 实况**

- 台账实况（机械解析）：编号 R10-1…R10-15 连续无跳号无重号，**共 15 条**；
  分节计数 一 6 ／ 二 2 ／ 三 3 ／ 四 2 ／ 四b 2。
- `CHANGELOG.md:58` 改后枚举：`6 ＋ 2 ＋ 3 ＋ 2 ＋ 2`，分项和 **15**，句内自报合计 **15**
  ——分项和、自报合计、台账实况**三者相等**。
- 新增两条的描述与台账逐条对得上：R10-14「entity_freeze 案外 sha 锚设计」＝台账四b「`entity_freeze.json`
  自身完整性锚」；R10-15「check_bound_file 绝对路径案根强制」＝台账四b 同名条。
- 句尾勘误声明在场：「（终验 BLOCKER-1 勘误：此前枚举漏计消化轮追加两条）」。

**② 两处勘误追注表述核对（`git show 1315751` 逐 hunk 读）**

- `batchD_workorder.md:118`：原句「r10_ledger.md（13 条）」**一字未改**，句后追注
  「【终验勘误（BLOCKER-1）：消化轮 1 追加 R10-14/15 后实为 15 条，见 final_acceptance.md；
  本句为主施工时点的历史记录，原文保留】」——**表述准确**：该工单落盘于主施工时点（消化轮 1 之前），
  当时 13 条属实，追注把"当时对、后来被追加改写"的时序讲清楚了，没有把历史记录说成错误。
- `batchD_adversarial.md:39`：原句「r10_ledger 13 条与 CHANGELOG 的"6＋2＋3＋2"口径对得上」**一字未改**，
  句后追注「【终验勘误（BLOCKER-1）：本断言落盘晚于消化轮 1 追加 R10-14/15，写下时已失真——实为 15 条，
  CHANGELOG 已订正为"6＋2＋3＋2＋2"】」——**表述准确**，与本报告条 5 认定的性质（盲审断言写下时已失真，
  非事后变化）完全一致，且未改写盲审历史结论。
- 两处均为**追注不改写**，符合本仓库"历史记录不可为守卫改写"的既定纪律（v6.18.0 教训）。

**③ 两道 lint 独立复跑（不引用裁判自报）**

```
changelog_lint.py    RC=0  PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 26 条 + 归档 139 条
docs_lint.py --all   RC=0  PASS: 58 个文档，引用无断链、粗体配对完整（--all 全量模式）
```

**判定：BLOCKER-1 CLEARED。** 账实一致（15==15==15）、两处勘误追注表述准确且未改写历史、两道 lint 独立复跑 rc=0。
条 5 由 FAIL 转 **PASS**，六条全 PASS。NOTE-1/2/3 维持台账处置，不需动作。

**最终交付判定：工程可交付。**

最终快照验收完成（含 BLOCKER-1 清账复核）
