# R9 批一 · 批内对抗审查报告

- **审查对象**：`/Users/uravvv/Documents/5.6筹码分析/r9-closure-worktree`，分支 `fix/r9-closure-20260807`，HEAD `144c6528f12b15eee6bada7cec22353fb2fbb3db`
- **审查区间**：`63cf715..144c652`（5 commit：`85753da` / `2f197d2` / `592b0c2` / `35c94eb` / `144c652`）；22 文件、85 hunk
- **审查角色**：批内质量核验员，只读沙箱。全程未对 worktree 做任何 git 写操作或文件增删改（`git status --short` 空、HEAD 未动）
- **审查模型身份（如实登记）**：**Claude Opus 5**，模型 ID `claude-opus-5[1m]`，以 Claude Code / Claude Agent SDK 子代理身份运行。
  PLAN-R9 第二节角色表规定批内对抗审查由「Opus 4.8 子代理」执行，并写明「Opus 4.8 不得由其他模型静默替代；执行环境无法调度时，本批不得开工，须报告用户裁决」。本次实际调度到的是 Opus 5。此处**显式登记不做静默替代**，是否接受该替代由裁判/用户裁决；报告其余部分按既定标准执行。
- **审查日期**：2026-08-07

---

## 1. 裁决

### **BLOCK**

一句话理由：批一在进程退出码、pool/scan 旧件隔离、纵切片消灭手写 plan 三条主线上确实做实了，但 **R9-02 自己写下的不变量「consumer 只接收可独立校验的真实 producer receipt」并未闭合——一份完全手写、producer 声明为仓库内某个 Markdown 文档的 plan+receipt，被 `time_spotcheck.py` 在 dry-run 与正式路径上双双接受（exit 0）**；同时新登记的正式 producer `anchor_plan.py` 没有同步获得本批为 pool/scan 施加的 stale 隔离语义，失败重跑后旧 plan+receipt 仍留在正式位置并被 consumer 当作本次结果。两项均为 P1 且均属「老问题修复不全（半修残留）」，按 `maintenance-review-repair.md` §7.1「新引入、半修残留不分严重度，都要修复后重审」，不能放行。

**finding 计数**：4 项 —— P1 × 2、P2 × 1、P3 × 1。
**严格三分类**：老问题修复不全 2（B1R-01、B1R-02）；修复中新引入 2（B1R-03、B1R-04）；历史漏检 0。

> 说明：PLAN 明确留给批二/三/四的工作（R9-01 实现、Solana 正式 callsite 接入、能力矩阵改造、批四 AST/producer 守卫）**不计入 finding**。施工方在 `b1_progress.md` 中对 R9-01、R9-05 均如实声明「本批不宣告销账」，这一点经核查属实，未发现把未销账 finding 谎报为已修的情况。B1R-01 之所以成立，是因为它落在批一**已宣告闭环**的 R9-02 范围内。

---

## 2. Finding 明细

### B1R-01｜P1｜老问题修复不全（R9-02 半修残留）｜consumer 未绑定 producer 身份，完全手写的 plan+receipt 可通过

**违反的不变量**：R9-02 工单第 1 栏（`b1_progress.md`）自写——「正式 EVM plan 必须由**登记 producer** 针对同一 chain/token/final block 和真实输入生成……consumer 只接收**可独立校验的真实 producer receipt**」。PLAN 批一原文亦为「`time_spotcheck.py` 只接受**真实生产者生成**并通过 receipt 校验的 v2 plan」。

**代码证据**：

- `scripts/lib/time_spotcheck.py:60-61`：`if plan.get("producer") != receipt.get("producer"): raise ...` —— 只做 **plan 与 receipt 两方之间**的一致性比较。
- `scripts/lib/time_spotcheck.py:47-88` 全函数 `load_validated_plan`：无任何一处把 `producer.path` 约束为 `scripts/lib/anchor_plan.py`。
- `scripts/lib/receipt_validate.py:75-84`：producer 校验仅为「路径是仓库内的普通文件」+「sha256 与该文件当前内容一致」。**任何**仓库内文件都能满足。

因此 `plan.producer == receipt.producer` 且哈希自洽，即可通过；两个条件都在攻击者/测试作者的完全控制之下。

**最小反例**（脚本：`/private/tmp/r9b1/attack_forged_plan.py`）：手写 plan、receipt 与 input manifest，producer 声明为 `references/maintenance-review-repair.md`（一份纯 Markdown 维护文档），抽查点缩减为 1 个。

```text
forged producer: references/maintenance-review-repair.md (a Markdown doc, NOT anchor_plan.py)
$ time_spotcheck.py --plan <forged> --dry-run --chain eth --token 0xdeadbeef --final-block 300 --out ...
STDOUT: {"dry_run": true, "balance_points": 1, "tx_points": 0, "total": 1, "need_final_block": 0}
EXIT CODE: 0
>>> ATTACK SUCCEEDED (consumer accepted a hand-forged plan)
```

**正式（非 dry-run）路径同样穿透**——伪造 plan 越过 receipt 闸进入业务 RPC 阶段，报错来自 RPC 不可达而非 plan 校验：

```text
$ time_spotcheck.py --plan <forged> --chain eth --token 0xdeadbeef --final-block 300 \
      --rpc http://127.0.0.1:1/nope --out ...
stderr: [time_spotcheck] ERROR → .../rcpt.error.20260807T161131.825881Z.40061.json
>>> plan/receipt 校验已通过、进入业务(RPC)阶段
```

**旁证（施工方自己的测试里就有这把钥匙）**：`scripts/tests/test_time_spotcheck.py:49-62` 的 `refresh_bundle()` 在改写 plan 后重算 `receipt.output.size/sha256` 与 `probe_count`，注释写明「负例允许重签 fixture 以抵达业务分支」。这说明「plan 与 receipt 一起改」在 receipt 层不被拦是**已知且被使用**的性质；用例 7 只覆盖了「改 plan 不改 receipt」。

**影响**：plan 规定的是 A2 时间抽查的**覆盖面**（时间三段 × 余额档 + 强制覆盖点）。伪造 plan 等于允许调用方自选覆盖面——把分层抽查缩水成任意 1 个易过的锚点，而产出的 time-spotcheck receipt 仍然 PASS，且 `probe_count` 由伪造者自填、与伪造 plan 自洽。R9-02 修复要求末句「不得手写正例输入」在实现层没有闭合，当下只靠测试自愿遵守。

**最强替代解释及不采纳理由**：最强替代解释是判「**修复中新引入**」——`load_validated_plan` 是本批全新代码，producer 身份校验缺口长在新代码上；而原报告 R9-02 点名的断契约（producer 无 `--final-block`、consumer 必失败）确已实证闭合，符合定义二「旧绕过已关闭、repair diff 造成新的错误接受面」。**不采纳**：`maintenance-review-repair.md` §二规则 1 规定「只要无法排除旧不变量仍在原入口/同族正式入口被击穿，按老问题修复不全，**不得用『这段 return/字段是新写的』降格**」。本反例正是在**原入口** `time_spotcheck.py` 上，同时击穿 R9-02 工单第 1 栏不变量的两个分句（「由登记 producer 生成」「consumer 只接收可独立校验的真实 producer receipt」），规则 1 优先于规则 2，故从严归「老问题修复不全」。两类归因都会触发重审，此判定不改变止损计数的发生，只改变应修的流程段（此处指向「工单纪律／修复深度」而非「修复流程自审」）。

**修复方向（供参考，不代替施工方设计）**：consumer 侧把 `producer.path` 约束到登记 producer 集合（可从 `invariant_manifest.json` 的 `receipt_producers` 派生，避免再造一份事实源）；或让 receipt 携带一个 consumer 可独立重算、而手写方无法伪造的绑定量。

---

### B1R-02｜P1｜老问题修复不全（R9-03/R9-04 同族未关到同一深度）｜`anchor_plan.py` 无 stale 隔离，失败后旧 plan+receipt 仍是 current

**违反的不变量**：INV-03/INV-04 同族——「本轮启动前旧 canonical 必须退出当前正式位置，失败不得留下本轮可消费结果」（R9-03 工单第 1 栏原文）。本批已为 `fetch_pool_swaps.py`、`scan_token_accounts.py` 实现 `quarantine_current`，但同批新登记的正式 receipt producer `anchor_plan.py` 未实现。

**代码证据**：

- `scripts/lib/anchor_plan.py` 全文件无 `quarantine_current` / stale 语义（对照 `scripts/evm/fetch_pool_swaps.py:63-74`、`scripts/solana/scan_token_accounts.py:41-53`）。
- `scripts/lib/anchor_plan.py:357-361`（探测点越界 `return 2`）、`:381-384`（receipt 构造失败 `return 1`）、`:424-429`（发布失败 `return 1`）——三个失败出口全部位于 `publish_txn(jp, plan, rp, receipt)` 之前，本次不发布任何东西，于是**上一次的 `anchor_plan.json` + `anchor_plan.receipt.json` 原封不动留在 `--out-dir`**。
- 本批已把 `scripts/lib/anchor_plan.py` 登记进 `scripts/tests/invariant_manifest.json` 的 `receipt_producers`（新增 3 个 schema），即它已是正式 receipt producer，却未同步纳入 `atomic_writes` 的 `quarantine_current` 语义（该表本批只为 pool 与 scan 各加了一条）。

**最小反例**（脚本：`/private/tmp/r9b1/attack_anchor_stale.py`）：同一 `--out-dir`，第一次用合法输入成功产出 plan，第二次换成含越界块的输入使 producer 失败。

```text
run1 (good input) rc = 0
  plan input sha256 = 3e4b82a6abaf48a5   points = 5
run2 (bad input, SAME out-dir) rc = 2
  stderr: [fatal] anchor plan probe boundary invalid: matrix_points[0].day_end_block=999 outside final_block=300
  plan  still present after failure: True
  receipt still present after failure: True
  any .stale quarantine file: NONE
  plan input sha256 now = 3e4b82a6abaf48a5 (unchanged)

consumer after FAILED producer run: rc = 0
  stdout: {"dry_run": true, "balance_points": 4, "tx_points": 1, "total": 5, "need_final_block": 0}
>>> STALE FAIL-OPEN CONFIRMED
```

即：producer 本次运行失败（rc=2），consumer 却拿着**上一次**的 plan 正常 exit 0，且该 plan 绑定的是**上一次输入文件**的哈希——没有任何环节核对「这个输入哈希是不是本次的数据」。

**测试为何没抓到**：`scripts/tests/test_r9_batch1_boundaries.py:167-178` 的 producer 越界负例使用**全新目录** `bad-plan`，只断言 `not (bad_dir / "anchor_plan.json").exists()`。这与原报告批评 `test_fetch_failclosed.py` 的措辞完全同型——「中途失败 fixture 也使用全新输出路径，没有做『先成功／预置旧 canonical，再失败』的正例审计」。R9-03、R9-04 的测试都补了「先成功再失败」与「预置旧件」，唯独 anchor 这一组没有。

**根因物证**：R9-03 工单第 2 栏的同族 rg 命令为 `rg -n "stale|partial|tmp|next_block|return [12]|__main__" scripts/evm scripts/solana` ——**扫描范围不含 `scripts/lib`**，而本批新建/改造的两个正式件 `anchor_plan.py`、`time_spotcheck.py` 恰好都在 `scripts/lib`。这正是方法论④「同族清单没做全」的直接证据。

**影响**：EVM A2 时间抽查的正式工作流是「重采数据 → 重跑 anchor_plan → 跑 time_spotcheck」。数据重采后 plan 生成失败是常见情形，此时下游拿到的是上一轮的抽查计划，而 receipt 链条完全自洽、无从察觉。

**最强替代解释及不采纳理由**：
- 替代解释①「**历史漏检**」——`anchor_plan.py` 在基线 `63cf715` 前就是覆盖写、失败留旧文件，缺陷早于本轮。**不采纳**：规则 3 要求判历史漏检必须**同时排除前两类**。本缺陷所属不变量（INV-03/INV-04「旧 canonical 必须退出当前正式位置」）正是 R9-03/R9-04 本批修复的不变量，`anchor_plan.py` 是同一不变量的同族正式 producer，符合规则 1「同族正式入口仍可击穿」，因此不能降格。
- 替代解释②「**修复中新引入**」——本批才把 `anchor_plan.py` 升级为 receipt producer、并让 consumer 强绑 receipt，是这一步才使「旧 plan 被当作本次结果」具备正式发布可达性。**不采纳**：规则 1 优先于规则 2；且此处失守的是同族清单的完整性（rg 范围漏 `scripts/lib`），对应的流程段是「工单纪律」，与「老问题修复不全」的指向一致。

---

### B1R-03｜P2｜修复中新引入｜`SolanaAttestedSession` 的信任锚可由调用者覆盖，且与 docstring 声明的「唯一注入边界」矛盾

**代码证据**：

- `scripts/lib/solana_attested_session.py:36-37`：`def __init__(self, endpoints, *, expected_genesis=SOLANA_MAINNET_GENESIS_HASH, request_json=None, timeout=30)` —— 可信 mainnet genesis 是一个**可被调用方替换**的关键字参数。
- `scripts/lib/solana_attested_session.py:30-34` docstring：「`request_json` **is the only test injection boundary**」——但 `expected_genesis` 事实上构成第二个注入边界，且它直接就是信任锚本身（视角⑤双向一致性不符）。

**最小反例**（脚本：`/private/tmp/r9b1/attack_session.py`，用例 A3）：

```text
=== A3: caller-supplied trust anchor (expected_genesis override) ===
  business result on a FORKED cluster: {'value': 'business-data'}
  business RPC count: 1  methods: ['getGenesisHash', 'getAccountInfo']
  >>> ANCHOR OVERRIDE SUCCEEDED
```

endpoint 返回的 genesis 是 `FORKchain111…`（非 mainnet），只要构造时传入同一个值，业务 RPC 照常执行——attestation 形式上发生了，实质上退化成「自己和自己比」。

**为何是 P2 而非 P1**：批一按 PLAN 不接入正式 callsite（经核查 `getGenesisHash` 仅出现在该原语与其测试两个文件中，`accounting_gate_sol.py` 与 `chain_registry.py` 未改），因此当前**不可达正式发布路径**。但 PLAN 批二要把 `chain_attestation` 变成「能解析到真实 session factory」的适配器键——一旦某个 factory 传入自定义 genesis，能力矩阵就会再次变成「声明当证明」，即 R9-05 原样复发。

**最强替代解释及不采纳理由**：最强替代解释是「这不算缺陷——默认值正确、参数是 keyword-only、覆盖它属于调用方自负责任」。**不采纳**：视角①的判据是「关键字段的值是从原始数据算出来的，还是调用者自报的？**自报的一律不信**」，而 expected genesis 是整条 attestation 链的信任根；R9-05 的成因恰恰就是「把声明当证明」，公共原语在同一处留下自报入口，等于把同族缺陷的复发口预置在批二的必经之路上。归「修复中新引入」而非「历史漏检」，因为该文件系本批全新建（规则 3 不满足）。

---

### B1R-04｜P3｜修复中新引入（无主改动／夹带）｜`invariant-merge.md` 删除了「拆分/合并不变量须经 Fable 批准」的治理条文，且不在 map 声明的修改目的内

**证据**：`maintenance/repair-20260806/invariant-merge.md` 第 4 行，本批删除了原文：

> 状态：**已由 Fable 冻结（2026-08-06，总验收裁判复核通过）**。20 个种子零变更获准；INV-20 零 primary、保留为豁免防回流 secondary 守卫获准；44 项 primary 分配与六同族组归并经逐项对照复核。**此后拆分/合并不变量必须经 Fable 批准并同步 ledger 双台账，不得在验收阶段为销账临时改组。**

替换文本保留了「R8 已冻结」「R9 不拆分/合并」的事实陈述，但**加粗部分那条面向未来的治理纪律消失了**。

`diff-finding-map.md` 中 `R9-B1-G6` 行声明的修改目的是「49 项主账、primary INV、唯一覆盖类别、严格三分类与本批逐组证据/owner 单源落盘」——**不涵盖删除一条治理纪律**。按 PLAN「`diff→finding` 映射覆盖每个变更块；无主改动一律视为夹带并 BLOCK」，此 hunk 属无主改动。

**影响**：事实层面本批确实没有拆分/合并不变量（我已复算，见 §5），所以无实质损害；但该条文是防止「验收阶段为销账临时改组不变量分母」的守卫，删除后下一轮失去这层约束。这与仓库自身记录的教训「历史记录不可为守卫改写」同型。

**最强替代解释及不采纳理由**：最强替代解释是「这只是把 R8 阶段性表述更新为 R9 现状的正常改写，属 G6 目的内」。**不采纳**：更新阶段状态并不需要删除一条与阶段无关、面向所有后续轮次的批准要求；且若确属必要，按 §7.3「每个 hunk 必须同时有 invariant、finding/豁免、目的和测试 owner」，应在 map 中显式登记「移除某条治理条文」的目的与理由，而非隐含在「单源落盘」里。

---

## 3. 六视角逐视角结论

视角定义以 `references/maintenance-review-repair.md` §一为准。每条列出实际检查的文件与攻击方式；**「守住项」= 我实际构造了攻击但没有穿透的点**。

### ① 字段来源审计（关键字段是原始数据算出的，还是调用者自报的）

**检查文件**：`scripts/lib/anchor_plan.py`、`scripts/lib/time_spotcheck.py`、`scripts/lib/receipt_validate.py`、`scripts/lib/receipt_kernel.py`（`build_envelope`/`finalize_envelope`/`_producer_ref`/`_file_ref`/`_checked_target`）、`scripts/lib/solana_attested_session.py`、`scripts/evm/fetch_pool_swaps.py`、`scripts/solana/scan_token_accounts.py`。

**结论：两处失守。**

- **B1R-01**：`producer` 字段虽由 producer 写入，但 consumer 侧无法区分「anchor_plan.py 写的」与「任何人写的」，等价于自报。`b1_progress.md` B1-G4 的自审结论「final block/探测点/输入/producer 均来自 producer 计算并双文件绑定」中，前三项属实，**「producer」一项的绑定不成立**——双文件绑定只证明 plan 与 receipt 互相一致，不证明二者出自登记 producer。
- **B1R-03**：`expected_genesis` 允许调用方自报信任锚。

**守住项**：

| 攻击 | 方式 | 结果 |
|---|---|---|
| 篡改 plan 保 receipt | 改 `plan.seed` 后不动 receipt | 拒（`plan receipt output size/hash mismatch`），`test_time_spotcheck` 用例 7 亦覆盖 |
| 换用另一份合法 receipt | receipt 绑定 `output.path`（resolve 后比对）+ `output.sha256` + `size` | 不可换：除非另一份 receipt 对应的 plan 路径与字节完全相同 |
| plan/receipt 走 symlink | `load_validated_plan` 首两行 `is_symlink()` 拒 | 拒 |
| Solana genesis 结果非字符串／空串 | `_attest` 强制 `isinstance(observed, str) and observed` | 拒 |
| Solana 响应 `{"error": ...}` 或缺 `result` | `_request` 三重判定 | 拒 |

### ② 失败分支审计（fail-closed 还是 warning 后装成功）

**检查文件**：六个改造入口（`fetch_pool_swaps.py`、`scan_token_accounts.py`、`accounting_gate.py`、`entity_identity_gate.py`、`cadence_fingerprint.py`、`golden_baseline.py`）、`anchor_plan.py`、`time_spotcheck.py`、`solana_attested_session.py`。

**结论：本批主线做实了，无新 finding。**

真实 subprocess 逐分支验证（非直接调用 `main()`）：

| 目标 | 注入 | rc | 正式位置状态 |
|---|---|---|---|
| pool | 缺 `next_block` | 2 | 无 current CSV（旧件已隔离为 `.stale.<ns>.<pid>`） |
| pool | network / parse / stalled cursor / 非法区间 | 均非零 | 无 current |
| pool | 旧 canonical 是**目录** | 1 | fail-closed，未强行覆盖 |
| pool | 旧 canonical 是**指向外部文件的 symlink** | 0（成功路径） | symlink 本身被隔离，外部 victim 文件内容完好，新 canonical 为普通文件 |
| scan | 路径冲突 / supply slot / GPA slot / 发布失败 / network / parse / 会计不闭合 | 均非零 | 无 current marker |
| scan | 预置旧 snapshot+PASS marker 后失败 | 非零 | data 与 marker 双双退出 current |
| anchor_plan | 探测点越界 | 2 | 新目录下不产出 plan/receipt（但见 B1R-02：同目录重跑时旧件不退位） |
| time_spotcheck | plan/receipt 各类不一致 | 2 | 在任何业务 RPC 前拒绝 |

**注入自证到达目标分支的一次返工（如实登记）**：我首次构造「scan 的旧 marker 是目录」用例时把工作区放在 `/tmp/...`，被 `scan_token_accounts.py` 的**前置 symlink 路径闸**拦下（macOS 的 `/tmp` 本身是 `/private/tmp` 的 symlink），报错为 `output parent contains symlink`——**注入未到达目标分支，此时的「守住」是假的**。按 §7.4「注入须自证到达目标分支」改用 `/private/tmp` 重做，才真正到达路径检查分支（`output destination is not a regular file`，rc=2）。

**一项观察（不列 finding，供裁判裁决）**：当旧 data 是目录、旧 marker 是合法 PASS receipt 时，脚本在**参数/路径校验阶段**即 rc=2 退出，此时旧 marker 仍留在 current 位置。严格照 PLAN「任一分支失败都不能留下当前有效 marker」可判违规；但该失败发生在任何业务动作之前（语义等同「本次运行没启动」）且进程 fail-closed，若为满足字面要求而在参数校验前就删/移 marker，反而会让一次拼错路径毁掉正式产物。我认为现状可辩护，故不计 finding，但如实登记该语义缺口。

### ③ 新格式的存量迁移（旧数据怎么办、新产物谁生成）

**检查文件**：`anchor_plan.py`（v2 plan + `anchor-plan-receipt/v2` + `anchor-plan-input/v1`）、`time_spotcheck.py`、`test_batch3_evm_vertical_slice.py`、`test_r7_findings.py`、`test_batch1_rpc_attestation.py`、`invariant_manifest.json`。

**结论：新产物的生成方已落实，但存量旧件的退位没做——即 B1R-02。**

- 新产物谁生成：`anchor_plan.py`，且三处既有测试（EVM 纵切片、R7-13、批一 RPC 错链）已全部改为**现场运行真实 producer**，手写 `plan_evm.json` / `mismatch.json` / `good.json` 均已删除。这一条做得扎实，是本批的实质进步。
- 旧数据怎么办：**答不上**。基线上已存在的 v1 plan（无 `schema`/`final_block`/receipt）会被 consumer 直接拒（fail-closed，方向正确），但**上一轮生成的合法 v2 plan 在 producer 失败后继续冒充本次结果**（B1R-02）。
- schema 串同族搜索（§六「升 schema 必 rg 全库连下游一起升」）：`rg "anchor-plan/v2|anchor-plan-receipt/v2"` 命中生产件 2、测试 1、manifest 1，无遗漏下游。

### ④ 修复点的同族调用面

**检查方式**：不采信自报清单，独立做全库 AST 扫描。

- 第一版扫描器把嵌套函数内的 `return` 误算进 `main()`，得出 11 个「违规」（含 `build_html.py`、`cluster.py` 等）。**核对后确认全是误报**——那些 return 都在 `main()` 内部定义的闭包里。据此重写扫描器（只统计不进入嵌套 `FunctionDef` 的顶层 return）。
- 修正后结果：**全库 0 命中**「`main()` 顶层返回非零/表达式 + `__main__` 裸调用」。仓库自身登记的 58 项 `formal_entrypoints` 逐一核对通过；`scripts/solana/accounting_gate_sol.py` 虽是裸 `main()`，但其内部用 `sys.exit(code)` 传播，不构成穿 0。
- **守住项**：我原本准备以「六入口只与 `formal_entrypoints` 交集 3 个、清单外还有 4 个正式入口是裸调用」立 finding，实测证伪后撤回。如实登记这次撤回。

**失守**：R9-03 工单的同族 rg 范围为 `scripts/evm scripts/solana`，**不含 `scripts/lib`**，而本批两个正式件都在 `scripts/lib` —— 直接导致 B1R-02。

### ⑤ 双向一致性（文档／schema／CLI／测试的 N 份副本互相对得上吗）

**检查文件**：`invariant_manifest.json`、`invariant-merge.md`、`ledger.md`、`diff-finding-map.md`、`b1_progress.md`、`references/maintenance-review-repair.md`、`solana_attested_session.py` docstring。

- `invariant_scan.py` 双向对账 PASS，计数与 `b1_progress.md` 自报逐字一致（见 §5）。
- `invariant_scan.py --self-test` 的 delete/add 两类破坏注入均稳定红，守卫本身可信。
- **失守 1（B1R-03 的一部分）**：`solana_attested_session.py` docstring 声称 `request_json` 是唯一注入边界，与 `expected_genesis` 的实际可注入性矛盾。
- **失守 2（B1R-04）**：`invariant-merge.md` 的治理条文被删且无 owner。
- ledger 的 44→49 改写、`maintenance-review-repair.md` §二的归因定义改写，逐行核对后与 G6 声明目的一致，属正常。

### ⑥ 每道闸的可绕性（是必经之路吗）

**逐闸结论**：

| 闸 | 是否必经 | 攻击与结果 |
|---|---|---|
| `load_validated_plan`（plan↔receipt 绑定） | 必经（dry-run 与正式路径共用，位于 `main()` 首段） | **可绕**：手写 plan+receipt 双双通过（B1R-01）。三种点名攻击（换 receipt／篡改 plan 保 receipt／篡改 receipt 保 plan）均被挡 |
| producer 探测点越界先验 | 必经 | **守住**：`--final-block` 传 `3.5` / `abc` / `True` / `0x12` / `300.0` 均被 argparse 拒，`-1` 被显式拒；`" 300 "` 被 int() 正常解析为 300（语义正确，无害）。consumer 侧另有一道独立的 query block 越界校验（`time_spotcheck.py:176-181`），构成纵深 |
| `getGenesisHash` 保留字 | — | **守住**：`getgenesishash`、`GetGenesisHash`、`" getGenesisHash"`、`["getGenesisHash"]`、`("getGenesisHash",)`、`{"m":"x"}` 六种变体，或被 `ValueError` 拒，或仍先触发 attestation；**业务调用数恒为 0**。该保留字实为防混淆而非安全边界——即便移除它，`call()` 也必先经 `_attest` |
| 错 genesis 时业务调用 = 0 | 必经 | **守住**：单 endpoint 与 failover 场景下业务调用均为 0 |
| failover 后重验 | 必经 | **守住**：`_advance()` 清空 `_attested_endpoint`，下一 endpoint 必重验 |
| 并发下的先验证后业务 | 必经 | **守住**：6 线程并发，方法序列首个恒为 `getGenesisHash`，且 1 个 endpoint 只 attest 1 次（`RLock` 覆盖 attest+business 全程，无 TOCTOU 窗口） |
| 信任锚 | — | **可绕**：`expected_genesis` 可覆盖（B1R-03） |
| pool/scan 启动隔离 | 必经（在 transport 前） | **守住**：目录/symlink/隔离失败三类分支均 fail-closed |
| anchor_plan 旧件退位 | **不存在这道闸** | B1R-02 |

---

## 4. diff→finding 独立复算

**方法**：`git diff --unified=0 63cf715..144c652` 逐文件统计 `@@` 数，得**总计 85 hunk / 22 文件**；再不看 map、按 diff 内容独立判定每个 hunk 属于哪一组，最后与 `diff-finding-map.md` 的 R9 批一表对账。

| 文件 | hunk | 我的独立归属 | map 声明 | 对账 |
|---|---:|---|---|---|
| `maintenance/repair-20260806/b1_progress.md` | 1 | G6 / G7 | G6、G7 行均列 | ✓ |
| `maintenance/repair-20260806/diff-finding-map.md` | 3 | G6 / G7 + `144c652` 自指回填 | 同（§7.3 通例允许自指计入） | ✓ |
| `maintenance/repair-20260806/invariant-merge.md` | 10 | G6（其中 1 处含目的外删除） | G6 | 9 ✓ / 1 见 B1R-04 |
| `maintenance/repair-20260806/ledger.md` | 9 | G6 | G6 | ✓ |
| `references/maintenance-review-repair.md` | 2 | G6 | G6 | ✓ |
| `scripts/bench/golden_baseline.py` | 1 | G2 | G2 | ✓ |
| `scripts/evm/accounting_gate.py` | 1 | G2 | G2 | ✓ |
| `scripts/evm/cadence_fingerprint.py` | 1 | G2 | G2 | ✓ |
| `scripts/evm/fetch_pool_swaps.py` | 4 | G2 | G2 | ✓ |
| `scripts/lib/anchor_plan.py` | 12 | G4 | G4 | ✓ |
| `scripts/lib/solana_attested_session.py` | 1 | G5 | G5 | ✓ |
| `scripts/lib/time_spotcheck.py` | 8 | G4 | G4 | ✓ |
| `scripts/report/entity_identity_gate.py` | 1 | G2 | G2 | ✓ |
| `scripts/solana/scan_token_accounts.py` | 4 | G2 ×1（`__main__`）+ G3 ×3（`import os`、`quarantine_current` 定义、调用） | G2「`__main__` hunk」+ G3「quarantine hunk」 | ✓（`import os` 未逐字点名，属 G3 直接依赖，接受） |
| `scripts/tests/invariant_manifest.json` | 6 | G7 | G7 | ✓ |
| `scripts/tests/run_all.py` | 1 | G1 + G5（单 hunk 内两行挂载） | 「同文件两个新增行分别归 G1/G5」 | ✓ |
| `scripts/tests/test_batch1_rpc_attestation.py` | 2 | G4 | G4 | ✓ |
| `scripts/tests/test_batch3_evm_vertical_slice.py` | 5 | G4 | G4 | ✓ |
| `scripts/tests/test_r7_findings.py` | 5 | G4 | G4 | ✓ |
| `scripts/tests/test_r9_batch1_boundaries.py` | 1 | G1 + G4 | G1 行（G4 行亦列该文件） | ✓ |
| `scripts/tests/test_r9_solana_attested_session.py` | 1 | G5 | G5 | ✓ |
| `scripts/tests/test_time_spotcheck.py` | 6 | G4 | G4 | ✓ |
| **合计** | **85** | | | |

**结论**：

- 按「每个 hunk 是否有 owner」判据：**未映射 hunk = 0**，与自报的 `0` 一致。
- 按 §7.3 的完整判据（「每个 hunk 必须同时有 invariant、finding/豁免、**目的**和测试 owner」）：**1 处 hunk 内含声明目的之外的改动**——`invariant-merge.md` 删除治理条文（B1R-04）。这不是「多了一个无 owner 的 hunk」，而是「有 owner 的 hunk 里夹带了目的外的内容」，逐 hunk 计数抓不到，需要读 diff 正文才能发现。
- 未发现「顺手整理」式的格式化夹带；`git diff --check` 无告警；无 `.pyc` / `__pycache__` 进入版本控制。

---

## 5. 自报声明验证表

**原则：不信自报，每条用我自己的命令重跑。**

| # | `b1_progress.md` 的声明 | 我的验证命令 | 我的结果 | 属实 |
|---:|---|---|---|:--:|
| 1 | 全量 `82/82 PASS`，末行「全部通过」 | `python3 scripts/tests/run_all.py`（完整输出落盘，不截断） | exit 0；82 个 PASS 行；末行「全部通过」 | ✅ |
| 2 | 既有 loopback 纵切片受沙箱 `bind(127.0.0.1)` 限制，需沙箱外运行 | 同上，在本审查环境直接运行 | 本环境**允许** loopback bind，两项纵切片无需特殊处理即通过 | ✅（环境差异，非缺陷） |
| 3 | 六文件均 `raise SystemExit(main())`，裸 `main()` 扫描 0 命中 | `rg -n -U 'if __name__ == .__main__.:\n +main\(\)' <六文件>` | 0 命中（rg exit 1） | ✅ |
| 4 | 全库无「`main()` 返回非零却裸调用」 | 自写 AST 扫描器（排除嵌套函数干扰），覆盖全库 `.py`（除 `.git`/`__pycache__`/`archive`） | 0 命中；58 项 `formal_entrypoints` 逐一核对通过 | ✅ |
| 5 | 未改 `VERSION`，仍 `6.36.0` | `cat VERSION`；`git diff --stat 63cf715..144c652 -- VERSION` | `6.36.0`；diff 为空 | ✅ |
| 6 | 未改 `chain_registry.py`、`accounting_gate_sol.py` | `git diff --stat 63cf715..144c652 -- <两文件>` | diff 为空 | ✅ |
| 7 | `getGenesisHash` 只存在于新原语及其测试，未接正式 callsite | `rg -l "getGenesisHash" --type py .` | 恰好 2 个文件：`scripts/lib/solana_attested_session.py`、`scripts/tests/test_r9_solana_attested_session.py` | ✅ |
| 8 | invariant census = `49/53/58/39/58`，exceptions=0 | `python3 scripts/tests/invariant_scan.py` | `receipt_producers=49, receipt_consumers=53, transport_calls=58, atomic_writes=39, formal_entrypoints=58, exceptions=0` | ✅ |
| 9 | `--self-test` delete/add 两类注入均稳定红 | `python3 scripts/tests/invariant_scan.py --self-test` | 两条均 `RED (rc=1)`，self-test exit 0 | ✅ |
| 10 | ledger `49` 行、`49` 唯一，R9 五 ID 各 1 次 | 自写解析器，按「## 二」段落边界精确取行 | 49 行 / 49 唯一 / 无重复 / R9-01～05 各 1 次 | ✅ |
| 11 | primary INV 求和 `49`，分布 `[3,3,5,3,2,3,3,4,2,3,3,1,2,2,4,1,1,3,1,0]` | 同上，按 primary 列聚合 | 求和 49；分布**逐位完全一致** | ✅ |
| 12 | `docs_lint.py --all` → PASS 58 个文档 | `python3 scripts/tests/docs_lint.py --all` | `PASS: 58 个文档，引用无断链、粗体配对完整` | ✅ |
| 13 | 未映射 hunk = 0 | 独立复算 85 hunk（见 §4） | 有 owner 层面 0；但 1 处 hunk 含目的外删除 | ⚠ 部分 |
| 14 | 施工期未做 git 写操作；`git status --short` 无施工变更 | `git status --short`；`git rev-parse HEAD` | 输出为空；HEAD = `144c652`，分支 `fix/r9-closure-20260807` | ✅ |
| 15 | R9-01 本批不实现、不宣告修复；R9-05 只完成公共原语、不宣告销账 | 读 `b1_progress.md` 措辞 + 核对第 6、7 条的代码事实 | 措辞如实，代码事实相符，**未发现把未销账 finding 谎报为已修** | ✅ |
| 16 | B1-G4 自审：「final block/探测点/输入/**producer** 均来自 producer 计算并双文件绑定」 | 构造手写 plan+receipt 攻击（B1R-01） | 前三项属实；**「producer」一项不成立**——双文件绑定只证明两份文件互相一致，不证明出自登记 producer | ❌ |
| 17 | R9-02 已红→绿闭环 | 复跑原反例 + 边界外一步攻击 | 原反例确已关闭（旧 producer 无 `final_block` → consumer rc=2 的路径已消失）；但**工单不变量未闭合**（B1R-01） | ⚠ 部分 |
| 18 | R9-03 / R9-04 已红→绿闭环 | 真实 subprocess 逐分支复跑 + 目录/symlink/预置旧件边界攻击 | **完全属实**，未攻穿 | ✅ |

**汇总**：18 条中 14 条完全属实、2 条部分属实、1 条不成立、1 条为环境差异。施工方在「哪些没做」上的陈述是诚实的；失准之处集中在 B1-G4 对自身修复深度的评价（第 16、17 条）。

---

## 6. 实际运行过的关键命令清单

全部命令的工作目录为 worktree 或 `/private/tmp/r9b1`；对仓库只读，临时产物一律落在系统 tempdir。

**仓库状态与 diff 复算**

```bash
git log --oneline -8
git diff --stat 63cf715..144c652
git diff --unified=0 63cf715..144c652 | grep -c "^@@"            # → 85
for f in $(git diff --name-only 63cf715..144c652); do \
    git diff --unified=0 63cf715..144c652 -- "$f" | grep -c "^@@"; done
git diff 63cf715..144c652 -- scripts/lib/anchor_plan.py
git diff 63cf715..144c652 -- scripts/lib/time_spotcheck.py scripts/evm/fetch_pool_swaps.py \
    scripts/solana/scan_token_accounts.py
git diff 63cf715..144c652 -- references/maintenance-review-repair.md \
    maintenance/repair-20260806/invariant-merge.md
git diff 63cf715..144c652 -- scripts/tests/test_batch3_evm_vertical_slice.py \
    scripts/tests/test_r7_findings.py scripts/tests/test_batch1_rpc_attestation.py
git status --short && git rev-parse HEAD
```

**自报声明重验**

```bash
python3 scripts/tests/run_all.py                    # 82 PASS / exit 0（完整输出，未截断）
python3 scripts/tests/invariant_scan.py
python3 scripts/tests/invariant_scan.py --self-test
python3 scripts/tests/docs_lint.py --all
rg -n -U 'if __name__ == .__main__.:\n +main\(\)' <六个入口文件>     # 0 命中
rg -l "getGenesisHash" --type py .                                   # 2 个文件
python3 /private/tmp/r9b1/scan_entry2.py            # 全库 AST 入口扫描（修正嵌套函数误报后）
# ledger 49 行/唯一/primary 求和/分布，按「## 二」段落边界精确解析
```

**边界外一步攻击（全部为我新写，非复跑施工方反例）**

```bash
python3 /private/tmp/r9b1/attack_forged_plan.py     # B1R-01：手写 plan+receipt，producer 冒充为 .md 文档
                                                    # → dry-run exit 0；正式路径亦越过 receipt 闸
python3 /private/tmp/r9b1/attack_anchor_stale.py    # B1R-02：同 out-dir 先成功后失败 → 旧 plan 仍 current
python3 /private/tmp/r9b1/attack_session.py         # A1 保留字大小写 / A2 batch 走私 / A3 信任锚覆盖 / A4 并发
python3 /private/tmp/r9b1/attack_stale_edges.py     # E1 旧件为目录 / E2 旧件为 symlink / E3-E4 scan 隔离边界
                                                    # （E3/E4 首跑被 /tmp symlink 前置闸拦下，
                                                    #   未到达目标分支，改 /private/tmp 重做）
# anchor_plan --final-block 类型边界：3.5 / abc / -1 / True / 0x12 / " 300 " / 300.0
```

**攻击脚本留存位置**：`/private/tmp/r9b1/`（`attack_forged_plan.py`、`attack_anchor_stale.py`、`attack_session.py`、`attack_stale_edges.py`、`scan_entry2.py`），供裁判独立复现。

---

## 附：给下一批的提醒（不构成 finding）

1. B1R-01 与 PLAN 批四「producer/consumer 守卫：正式 E2E 的关键输入必须由登记生产者在测试中现场生成；手写 plan、receipt 或 PASS JSON 不计作端到端覆盖」是同一件事的两个层面。批四那道守卫管的是**测试**，B1R-01 暴露的是**生产 consumer 自身**分辨不了——建议两者一并设计，避免守卫只在测试侧成立。
2. B1R-03 会在批二「`chain_attestation` 改为适配器键、矩阵加载时必须能解析到真实 session factory」时进入正式路径，建议在批二开工前先收口，否则 R9-05 会以「factory 传了自定义 genesis」的形式原样复发。
3. `.stale.<time_ns>.<pid>` 文件目前只生成、不清理，会在正式产物目录长期堆积；若下游存在 glob 匹配（如 `pool_swaps*`），存在被误读的可能。建议登记清理策略或改用隔离子目录。
