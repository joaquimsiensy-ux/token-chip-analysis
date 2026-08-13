# 批 B 批内对抗审查（盲审）

- **审查对象**：`ee0e8e9`（基线 `e1bd7dd`）——F-03 两层＋F-08，含两个夹具修正与三处文档改口
- **审查方式**：只读＋跑测试。所有生产文件零改动；变异实验在仓库副本 `/private/tmp/batchB_probe/mutrepo/` 上做，做完逐条还原
- **基线核对**：`scripts/tests/test_repair_batch_b.py` 18/18 绿；`scripts/tests/run_all.py` 全部通过（EXIT=0）。施工方自报的红绿状态属实
- **⚠ 工作树漂移声明**：审查进行中（本机 11:40–11:42）有**并行线程**在同一工作树上动 `holder_distribution_scan.py` 与 `test_repair_batch_b.py`（改闭合锚点为 replay 侧 `mint_total`、容差收到 0、加收据白名单等），其 WIP 当时是红的（5/26 FAIL）。**那些改动不是本审查者所为**（本审查全程只读，变异实验一律在 `/private/tmp/batchB_probe/mutrepo/` 副本上做）。为免混淆，本报告全部 finding 与复现均**钉死在 `ee0e8e9` 提交态**：副本三文件与 `git show ee0e8e9:` 逐字节相同（scan `3ee2c4b6…`／gate `00ce2e57…`／test `0b34780e…`），F-B1／F-B2 已用钉死副本重跑复现、结论一字不变。若并行线程的 WIP 已覆盖某些条目（从其测试名看至少 P0-B1／P2-B4／P2-B5 与本报告的 F-B1／F-B2／F-B3 同题），请以合并后的实际代码为准复核，别把两边的编号混着引
- **结论**：**7 条 finding，最高 P0**。批 B 修的两层里，第一层（闭合）成立且反例齐；第二层（快照绑定）只挡住了 initial 那份扫描，**真正进报告的 final 轮次扫描完全没绑**，F-03 原始 finding 写明的影响路径（污染最终报告）原样敞着

| 编号 | 严重度 | 一句话 |
|---|---|---|
| F-B1 | **P0** | 第二层只绑 initial scan；final 轮次 scan 换一份"同值换仓"快照，record-round→A5 seal→发布闸全链放行 |
| F-B2 | P2 | 10bps 对称窗口配上"100 个主箱 owner"的样本线阶跃，0.005bps 的代价就能把 ABNORMAL_SHAPE 翻成 low_sample 终态 |
| F-B3 | P2 | F-08 的三验只验内容不验身份：`upstream_receipts` 改指案内任意一份文件（连工作图 PNG 都行）照样 PASS |
| F-B4 | P2 | 第二层三条 fail-closed 分支零回归覆盖——把它们改成静默放过，全量 suite 依然全绿 |
| F-B5 | P2 | 工单"A5 终态案重验不死锁"这句口径不成立：闭合闸经 build_scan 进了 validate 的追溯路径，存量案实测被拒 |
| F-B6 | P3 | Solana 侧的锚点 `holder_outputs.owners` 全库没有任何 validator 校验过，比 EVM 侧弱一档，而文档称两侧等强；且 Solana 分支从未端到端跑过发布闸 |
| F-B7 | P3 | 链族分派用的是只有两个键的裸字典下标，将来加第三个链族时 KeyError 直接崩栈逃出闸函数（潜伏） |

---

## 视角① 字段来源

**闭合用的 `total_supply_raw` 从哪来、能不能被同一伪造方顺手改掉？**

来自 `load_supply()` 读案根的 `supply_truth.json`（`holder_distribution_scan.py:213-225`），只看 verdict/exit_code 和数值本身。造假者当然能把它改成"正好等于快照和"。但这不构成新问题：`supply_truth.json` 本身归 F-02 那把闸和四查 `supply_truth` 收据管，闭合闸的定位是**一致性校验器不是真实性证明器**（批 A 已定调）。它的增量价值是把"分布扫描"和"供给真值"这两个本来各说各话的产物钉在一起——这个价值成立。**此项未发现 finding。**

**第二层交叉的两个 sha，各自的信任根是什么？有没有"自己报自己验"？**

- 扫描侧 `input_binding.snapshot.sha256`：由 `validate_scan` 的 `_verify_bound` 拿案内实物文件重算（`holder_distribution_scan.py:764-768`），**有实物锚**。
- EVM 侧 `inputs.balances.sha256`：由 `receipt_validate.validate_receipt` 逐个 input 做 path/size/sha 三验（`scripts/lib/receipt_validate.py:87-107`），**有实物锚**。我原本怀疑这是纯自报字段，实测推翻了自己的怀疑——记录在此以免复审者重走这条路。
- Solana 侧 `holder_outputs.owners.sha256`：**没有任何实物锚**，见 F-B6。

**旁证核对**：真 producer `scripts/evm/verify_recon.py:65-66` 确实写 `inputs={"config":…, "balances": balances_path}`，键名对得上，不存在"闸认的字段生产者不产"的误伤。

## 视角② 失败分支

第一层的边界分支都对：`total=0`／`net>total` 在 `load_supply` 先炸；空快照在 `parse_snapshot` 先炸；负数在 `strict_raw` 先炸；差一丝（10bps 外 1 wei）实测拒（见 M5 变异）。生产侧 raise 一律被 `cmd_scan` 兜成 `data_broken` 产物＋exit 2，fail-closed。

F-08 的"缺席跳过／在场非法"分流没有串线：`Path.exists()` 跟符号链接，断链符号链接靠 `is_symlink()` 兜住，两者都会落到 `safe_file` 上炸——实测符号链接 exit 2（既有用例已覆盖）。

**但第二层自己的三条失败分支没有任何回归钉着**，见 **F-B4**。

## 视角③ 绕闸

- **同值换仓在两层都被拦吗**：第一层按定义拦不住（总和不变）；第二层在 **initial** 上确实拦得住（既有用例实测）。**但 final 轮次扫描不在第二层射程内**——见 **F-B1**，这是本次审查的主结论。
- **exploration／独立审计 profile 走不走第二层**：不走，但 `independent-audit` 也不跑 `validate_scan`、A5 的 `distribution_bundle` 对它直接返回 `NOT_APPLICABLE`，分布语义整体不在该 profile 的射程内；而且新分析案缺 `audit_input_manifest.json`／`claim_registry.json`／`reproduce_audit.py`，换 profile 会被"缺必需资产"直接拦。**不构成绕闸通道，未发现 finding。**
- **有没有别的入口能产 distribution_scan 不过闭合**：`--output` 能改产物落点、`--snapshot` 能改吃哪份快照，但两者都必经 `build_scan`，闭合逃不掉；手写产物会被 `validate_scan` 的重算撞死；`migrate_legacy_case.py` 只修 data_map 的 `sha256:` 前缀，不碰闭合。**未发现新入口。**
- **10bps 对称窗口能塞进什么攻击**：见 **F-B2**。

## 视角④ 测试有效性

**变异法独立重放**（脚本 `/private/tmp/batchB_probe/mutate.py`＋`mutate2.py`，15 条变异逐条注入后还原）：

| 变异 | 结果 |
|---|---|
| M1 闭合闸回退成 6.39.5 的单向 `sum>total` | 变红（2 条） |
| M2 只拦超发不拦缺口 | 变红（2 条） |
| M3 闭合分母从 total 换成 net | 变红（dead-sink 绿例被误杀，防误伤守卫有效） |
| M4 容差 10bps 放宽到 100bps | 变红（2 条） |
| M5 整数交叉乘法改成 float 除法 | 变红（大整数边界用例咬住） |
| M6 发布闸不挂第二层 | 变红 |
| M7 第二层 sha 比对恒真 | 变红（2 条） |
| M8 Solana 绑到 `holder_outputs.accounts` | 变红 |
| M9 F-08 三验整段删除 | 变红（3 条） |
| M10 F-08 方向写反（要求磁盘现有项必须被记录） | 变红（合法绿例咬住，死环防线有效） |
| M11 生产侧回到 `except ValueError: pass` | 变红 |
| M15 三验只查存在不查 sha/size | 变红（2 条） |
| **M12／M13／M14 第二层三条失败分支改成静默放过** | **全量 suite 依然全绿 → 见 F-B4** |

施工方自报的"五处新校验删掉即红"属实，且我把变异面扩到 12 条仍全红，只有第二层的三条失败分支是空档。

**两个夹具修正是否改弱了原用例的断言主题**：没有。两处都是**纯新增行**（`git show ee0e8e9 -- scripts/tests/test_a4_gate.py scripts/tests/test_review_20260804_p105.py` 全是 `+`，零 `assert` 被删改）。做的事是把四查 balance 收据的 `inputs.balances` 重新指到本案自己的 owner 快照（原来错绑 `raw_transfers.jsonl`，本来就是夹具失真）。

- p105 版直接调 `create_bundle(root)` ＝重跑生产者；
- a4_gate 版是手工改 `shared["inputs"]["reconciliation_report.json"]["sha256"]`——我核对了 `create_bundle` 的 payload 形态（`shared_release_receipt.py:536-539`）：`inputs` 就是 `{文件名: {path, sha256}}` 的平铺表，除该文件外其余项内容未变，手改这一项与重跑 `create_bundle` **逐字节等价**。

按批 A "夹具重绑等效重跑生产者＝合法、改弱断言＝违规"的撞墙裁决先例，**两处均合法，未发现 finding。**

## 视角⑤ 误伤面

- **dead-sink 案（sum=total≠net）**：绿例在案且 M3 变异会把它咬红，防线有效。**未发现误伤。**
- **Solana burn 案**：Solana 的 burn 直接减 mint supply，`scan_token_accounts` 自己就强制 `sum_accounts_raw == supply_raw` 三方相等，闭合到 total 天然成立。**未发现误伤。**
- **第二层禁入 validate_scan 有没有守住**：守住了，`check_distribution_snapshot_binding` 只在 `audit_release_gate.run()` 的 `profile == "new-analysis"` 分支里被调用，`validate_scan` 里没有它。**但第一层从后门进了追溯路径**，见 **F-B5**。
- **复制案语义与批 A 案根约束的交互**：批 A 的 N-1 给 `replay_stats` 上了"必须在案根内"的约束，本批的 EVM 锚点 `inputs.balances` 没有同款约束（`receipt_validate._regular_file` 在 `root=None` 分支允许绝对路径指到案外）。我核过这条**在本条链上不构成漏洞**：第二层只比 sha，而被比的分布快照必须在案内（`safe_file` 强制案内、拒符号链接），sha 相等即内容相等，案外那份只能是同内容副本，藏不住东西。**不立 finding，但属"同族约束不等深"，建议记批 D 台账。**
- 顺带一条同族观察（不立 finding）：案内声明"owner 余额快照"的地方现在有三处——分布扫描的 `input_binding.snapshot`、四查 balance 收据的 `inputs.balances`、三账的 `balance_source`（`audit_release_gate.py:335-356`）。批 B 只把前两处钉在一起，且只钉 initial 那一轮；`balance_source` 与四查之间仍无等值绑定。

---

# Findings 详表

## F-B1 —— P0 —— 第二层只绑 initial scan，进报告的 final 轮次扫描完全没绑

**一句话**：分布扫描的第二层交叉检查只对 `distribution_scan.json`（initial）生效；决定报告结论的 final 轮次扫描可以吃另一份"总和一模一样、owner 分配不同"的快照，record-round → A5 seal → 发布闸全链零报错。

**为什么是 P0**：与父 finding F-03 同一威胁模型（能跑管线的内部人）、同一影响路径。F-03 原文写的就是"final scan 会沿用同一快照，因此可污染最终报告"——这条前提在代码里并不成立（`--snapshot` 可以点名任何一份登记在 data_map 里的文件），所以 P0 的影响路径没关上。报告里唯一那张持仓分布图 `charts/final/holder_distribution_current.png` 和 `dist-*` 结论都来自 final 轮次扫描（`a5_report_seal.py:44-66`、`a4_gate.py:234-247`）。严重度按父 finding 继承，复审者若认为"initial 已绑住案内快照集合"足以降档，可下调至 P1。

**实测复现**：`/private/tmp/batchB_probe/probe1_final_swap.py`（完全复刻 `test_review_20260804_p105.add_new_analysis_distribution` 的合法流程，只把 final 那一步的 `--snapshot` 换成同值换仓的 alt 文件）

```
$ python3 /private/tmp/batchB_probe/probe1_final_swap.py
initial 用的快照 = data/holders_owners.json a195c14f4462
final scan rc = 0 PASS: final NORMAL_SHAPE -> …/dist_rounds/round_1/dis
final  用的快照 = data/holders_owners_alt.json 90663f6f0dde
record-round rc = 0 PASS: round 1 -> NORMAL
A5 seal rc = 0
发布闸 new-analysis errors = []
final verdict = NORMAL_SHAPE | initial verdict = NORMAL_SHAPE
initial 快照 sha != final 快照 sha ? True
RESULT: BYPASS(发布闸放行)
```

alt 快照的构造与既有 EVM 反例逐字相同：`swapped[keys[0]], swapped[keys[-1]] = truth[keys[-1]], truth[keys[0]]`（把 owner-000 的 2,000,000 挪给 owner-239），总和逐位不变。同一份 alt 喂给 **initial** 会被第二层当场拒（既有用例 `F-03/2 EVM 同值换仓被拒` 已证），喂给 **final** 全链放行。

**建议修法**：把交叉检查扩到终态 final scan——发布闸 new-analysis 分支里读 `distribution_rounds.json` 的 `terminal.final_scan_path`，把那份 scan 的 `input_binding.snapshot.sha256` 一并纳入同一个等值比对（EVM 对 `inputs.balances`，Solana 对 `holder_outputs.owners`）。**仍然放发布闸、不要放 validate_scan**——终态 scan 是本轮新产的，不涉及存量案追溯。附带效果：F-B2 的窗口攻击在 final 侧也一并被堵。
成本更低的等价做法（若嫌读台账麻烦）：直接比"final scan 的 snapshot sha == initial scan 的 snapshot sha"，因为 initial 那份已经被钉在四查上了。

## F-B2 —— P2 —— 10bps 窗口配上样本线阶跃，0.005bps 就能翻判定

**一句话**：闭合容差是 10bps，而"主箱 owner 数 <100 就转小样本模式"是个阶跃；删掉几个刚过 dust 线的极小 owner 只花 0.005bps，就能把 `ABNORMAL_SHAPE`（含 head_concentration 异常簇、必须进 A4 裁决）变成 `NOT_EVALUABLE/low_sample`，而 low_sample 在 `record-round` 里是**终态**（`holder_distribution_scan.py` 的 `status="LOW_SAMPLE"; terminal=True`），不进 A4 复议。

**这是残留不是回归**：修复前删多少 owner 都不拦，修复后至少被压到 10bps 以内。但 10bps 的窗口对这个阶跃来说仍然绰绰有余。

**实测复现**：`/private/tmp/batchB_probe/probe2_window.py`

```
== 原始快照（104 个主箱 owner）==
  rc = 0 | verdict = ABNORMAL_SHAPE | 主箱 owner 数 = 104 | 异常簇 = ['bin_count_bump', 'head_concentration']
== 删掉 5 个刚过 dust 线的 owner 后 ==
  删掉的量 = 500000000010 / total = 1000000500000000018 → 缺口 0.005000 bps（窗口 10 bps）
  rc = 0 | verdict = NOT_EVALUABLE | 理由 = low_sample | 主箱 owner 数 = 99 | 异常簇 = []
  small_sample_mode.complete = True
RESULT: 翻转成立
```

注意被藏掉的东西并没有消失：`small_sample_mode.top_k` 里 top-1 仍然是净供应的 25%（头部基线是 20%），但小样本模式不产异常簇，于是没有任何 `dist-*` claim 需要 A4 裁决。

**与 F-B1 的组合**：在 new-analysis 的 **initial** 那一轮，这个攻击被第二层挡住（改快照就改 sha）；在 **final** 那一轮没人挡，两条 finding 叠加即完整可用。

**建议修法**（任选其一或叠加）：
1. `low_sample` 不再无条件终态：`small_sample_mode.top_k` 命中头部基线时改判 `REQUIRES_A4_REFLOW` 或强制披露——这条最治本，且与窗口大小无关；
2. 把 owner 计数也纳入闭合口径（例如与四查 balance 收据 `observations.balance_reconciliation.checked` 做数量级比对）；
3. 关掉 F-B1 后，本条在正式发布路径上的可利用面自动收敛到 −1 阶段内部。

## F-B3 —— P2 —— F-08 三验只验内容不验身份

**一句话**：`validate_scan` 对 `upstream_receipts` 逐项验"存在＋sha＋size"，但不验**记的是哪份文件**——把记录项改成案内任意一份真实文件（`supply_truth.json`、甚至工作图 PNG），三验全过。

F-08 原文的指控是"字段继续以'绑定'形态出现在产物，实际不构成证据"。修法关掉了"指向不存在的文件／伪 sha／伪 size"三种伪造，但"换成另一份真文件"这一种还在——产物里那条 `upstream_receipts` 仍然不能告诉复核者当初到底用的哪份 preflight 收据。

**实测复现**：

```
生产者记录的 upstream_receipts = ['channels_preflight.json']
换成 supply_truth.json 后 validate_scan = []
RESULT: 记录项身份不受约束（三验只验内容不验是哪份）
换成工作图 PNG 后 validate_scan = []
```

**建议修法**：三验前加一条白名单——`path` 必须落在 `{"channels_preflight.json", "holders_snapshot_meta.json"}` 内且不得重复。方向仍是"记录项 → 磁盘"，不会把 6.39.5 修掉的三闸死环带回来（缺席照样合法）。三行代码。

## F-B4 —— P2 —— 第二层三条 fail-closed 分支零回归覆盖

**一句话**：把第二层的三条失败分支从"报错"改成"静默 return"，**全量 suite 依然全绿**——这三条最该 fail-closed 的路径没有任何回归钉着。

**实测复现**：`/private/tmp/batchB_probe/mutate2.py`，每条变异后跑 `scripts/tests/run_all.py`

```
[**存活**] M12 第二层：找不到四查收据文件时静默放过 (all suite) rc=0   全部通过
[**存活**] M13 第二层：scan 缺 snapshot.sha256 时静默放过 (all suite) rc=0   全部通过
[**存活**] M14 第二层：链族判不出时静默放过 (all suite) rc=0   全部通过
```

**诚实定性**：这三条分支当前**代码是对的**（都 append 了 error），而且实践中都被更早的闸遮住——`checks.balance.receipt.path` 由 `reconciliation_report.case_path` 生成，路径形态天然合法；缺 `snapshot.sha256` 的 scan 会先被 `validate_scan` 撞死；链族判不出在只有 evm/solana 两族时不可达。所以这是**回归覆盖缺口，不是当前可利用漏洞**。风险在于：日后任何人把这三处改松，全库测试不会吭一声。

顺带一条实测差异（说明分支并非纯理论）：第二层用的 `regular_case_path` 拒中间路径段的符号链接，而 `shared_release_receipt.regular` 只查最后一段——两者对 `link/r.json` 的判定不同（前者 None、后者 OK），所以"找不到收据文件"这条分支确实可达。

**建议修法**：补三条定向红线用例（各造一个只坏这一处的案子，断言 errors 里有对应那句），挂进 `test_repair_batch_b.py`。

## F-B5 —— P2 —— "A5 终态案重验不死锁"这句口径不成立

**一句话**：第二层特意禁入 `validate_scan` 是为了防存量终态案被追溯卡死，但**第一层的闭合闸经 `build_scan` 从后门进了同一条追溯路径**（`validate_scan` 里 `rebuilt = build_scan(...)`），存量案实测被拒。

**实测复现**：`/private/tmp/batchB_probe/probe3_retro.py`（用 `git show e1bd7dd:` 取出的基线脚本产存量 scan，再用当前脚本重验）

```
A 基线产 scan（缺口 5%）rc = 0 | verdict = NORMAL_SHAPE
A 新版 validate rc = 2
   BLOCK: distribution scan validate | - scan 不可重验: 快照 raw 和未对冻结 total supply 闭合: 快照=59127382 total=62239349 容差=10bps
B 基线产 scan（完全闭合）rc = 0
B 新版 validate rc = 2
   BLOCK: distribution scan validate | - scan 语义与独立重算不一致
  存量 scan 记的 algorithm.sha256 = a4d810f0411154d5
  当前脚本 sha256                = 3ee2c4b647338996
```

两件事要分开看：
- **A 是本批新引入的追溯面**：基线时代合法（只拦超发）的存量案，现在重验必拒。这属于**刻意收紧**、方向没错，但工单不能写成"不死锁"。
- **B 是既有机制**：`input_binding.algorithm.sha256` 绑的是脚本自身哈希，只要脚本改过一个字节，所有旧产物的 `semantic_payload` 就对不上。这不是本批造成的（6.39.x 每次改这个脚本都一样），但它顺带说明：**"把第二层挡在 validate_scan 外面"买到的追溯保护本来就很有限**——存量案在 A5 重验前无论如何都得重跑生产者。

**建议修法**：不改代码，改口径。工单／`scan-schemas.md` 把"A5 终态案重验不死锁"改写成："重验须重跑当前版本生产者（与仓内既有的『存量案例须重跑对应生产者获取当前回执』一致）；重跑后不闭合的存量案按 `data_broken` 拒收，这是刻意收紧不是回归。"

## F-B6 —— P3 —— Solana 侧锚点没有实物锚，且分支从未端到端跑过

**一句话**：第二层 Solana 侧比对的 `holder_outputs.owners.sha256`，全库没有任何 validator 校验过它对应的文件，比 EVM 侧弱一档；而 `scan-schemas.md` 把两侧写成等强（"同值换仓也逃不掉"）。

**实测复现**：

```
$ grep -rn "holder_outputs" scripts/ --include='*.py' | grep -v tests/
scripts/solana/scan_token_accounts.py:293:   holder_outputs={"accounts": ref(accounts_out), "owners": ref(owners_out)})
scripts/report/audit_release_gate.py:754-755: （本批新增的读取点）
```

全库只有"生产者写"和"本批新增的闸读"两处，`validate_observation_bundle`（`scripts/lib/solana_observation.py:529+`）通篇不提 `holder_outputs`；receipt 信封校验器也只管 `inputs`：

```
validate_receipt(holder_outputs 全是假的) = []     # path="根本不存在.json", size=-1, sha256="deadbeef"
```

对照 EVM 侧：`inputs.balances` 被 `receipt_validate.validate_receipt` 拿实物文件三验。

**另一半**：全量 suite 里 6 处 `profile="new-analysis"` 的发布闸调用（`test_audit_release_gate.py:262/270/277`、`test_repair_batch_b.py:180/198`、`test_review_20260804_p105.py:103`）**全部是 bsc 夹具**；Solana 分支只有 `test_repair_batch_b.test_f03_gate_solana_not_skipped` 直接调函数、手搓 `data` 字典的单元测试，从没经过 `run()`。施工方补的"生产者字段在场率守卫"（源码字符串断言）是个合理的次优替代，但挡不住 `run()` 路径上的形态漂移。

**诚实定性**：可利用性与 EVM 侧差别不大（两边的造假者都得重穿收据链），所以给 P3。真正的问题是**文档宣称的强度高于实际**，以及 Solana 端到端零覆盖。

**建议修法**：①第二层对 Solana 顺手多比一层——bundle 的 `output` 字段已被 `ref_ok` 绑到案内实物快照，可核对其中的 owners 集合与分布快照一致；或直接给 `holder_outputs` 补文件级三验（放 `validate_observation_bundle` 里）。②补一个 Solana new-analysis 的发布闸端到端夹具。③在①落地前，`scan-schemas.md` 把两侧强度差异如实写出来。

## F-B7 —— P3（潜伏）—— 链族分派用裸字典下标，KeyError 逃出闸函数

**一句话**：`key, label, reader = {...}[family]`（`audit_release_gate.py:750-756`）只有 `evm`／`solana` 两个键、没有成员检查，且这一句在 `try` 块**外面**；将来加第三个链族时会抛未捕获 KeyError，从 `run()` 一路逃到 CLI 崩栈，`--json-out` 也不会落盘。

**实测复现**（monkeypatch 模拟未来新增链族）：

```
srr.chain_family = lambda c: "sui"
g.check_distribution_snapshot_binding(d, data, "sui", errors)
→ 未捕获异常逃出闸函数: KeyError: 'sui'
```

当前不可达（`chain_family` 对未注册链族先抛 ValueError，被上面的 `except` 接住）。但 skill 明写"全新链须先补齐采集、对账、身份门禁适配器"，这条路迟早会走到。仓内同族写法（`shared_release_receipt.py:449` 的 `RECON_PRODUCERS[family][key]`）前面都有成员检查。

**建议修法**：把字面量提成模块级常量 `SNAPSHOT_BINDING_BY_FAMILY`，取值前判 `if family not in …: errors.append(…); return`。三行。

---

## 复现件清单

全部在 `/private/tmp/batchB_probe/`，只读仓库、不改生产文件：

| 文件 | 用途 |
|---|---|
| `probe1_final_swap.py` | F-B1：final 轮次扫描换 alt 快照走完整发布链 |
| `probe2_window.py` | F-B2：10bps 窗口内的样本线翻转 |
| `probe3_retro.py` | F-B5：基线脚本产的存量 scan 在新版下重验 |
| `mutate.py` / `mutate2.py` | 视角④：15 条变异注入＋还原（M12/M13/M14 跑全量 suite） |
| `mutrepo/` | 仓库副本（变异实验场，实验后逐条还原，跑完仍 18/18＋全量绿） |
| `baseline_scan.py` | `git show e1bd7dd:scripts/report/holder_distribution_scan.py` 导出件 |
| `probe1_pinned.py` / `probe2_pinned.py` | 同上两条探针的钉死副本版（ROOT 指 `mutrepo`），用于排除工作树漂移干扰，输出与原版一字不差 |

## 收口建议

- **F-B1 必须本批内关**（P0，且修法很小：发布闸里把终态 final scan 一并纳入同一个 sha 等值比对）。关掉它，F-B2 在正式发布路径上的可利用面同时收敛。
- F-B3／F-B4／F-B7 都是三行级的补丁，建议随 F-B1 一起做完。
- F-B5 是改口径不是改代码。
- F-B6 的①②可评估后进批 D 台账，③（文档如实写强度差）建议本批就改。

对抗审查完成
