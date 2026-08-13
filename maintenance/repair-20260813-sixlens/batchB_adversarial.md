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

---

# 消化轮 1 复核（`394ffbb`）

- **复核对象**：`ee0e8e9 → 394ffbb`，施工方声称 F-B1~F-B7 全关
- **方式**：只读＋副本变异。钉死副本 `/private/tmp/batchB_probe/r1repo/`，三个主文件与 `git show 394ffbb:` 逐字节相同（scan／gate／test 三处 SAME 已核）。全量 `run_all.py` 在钉死副本上独立复跑 **EXIT=0**
- **结论**：**7 条全部 CLOSED**；但本轮新引入的闭合锚点自身带出 **4 条新 finding（2×P2＋2×P3）**，需要一个小范围的消化轮 2

| 编号 | 判定 | 依据（实测） |
|---|---|---|
| F-B1 | **CLOSED** | 两道独立防线都咬住，且都变异验证过 |
| F-B2 | **CLOSED** | 容差收到 0，原攻击当场 `data_broken` |
| F-B3 | **CLOSED** | path 白名单，含"边界外一步"变体 |
| F-B4 | **CLOSED** | 三条 fail-closed 分支各有定向红线 |
| F-B5 | **CLOSED** | 口径改正已落 `scan-schemas.md` |
| F-B6 | **CLOSED**（②按裁定收口） | ①③落地，②覆盖面判定见下 |
| F-B7 | **CLOSED** | 常量表＋成员检查，不再崩栈 |

## 1. 逐条重放

复现件 `/private/tmp/batchB_probe/recheck1.py`（攻击构造与轮 1 逐字相同，只按新夹具 API 改了 `make_case` 的参数名）：

```
[CLOSED] F-B1 生产侧：final 换仓快照  rc=2 BLOCK: distribution data_broken: final scan 快照与绑定的
         initial scan 快照不一致（final 轮不得更换 owner 快照）: initial=a195c14f4462…
[CLOSED] F-B1 合法案仍放行（防误伤）  []
[CLOSED] F-B1 发布闸终态分支：手改终态快照 sha  ['分布快照未绑定对账 owner 快照: 终态 final scan 的
         快照 sha256 与四查 balance 收据的 inputs.balances不一致（final 轮换仓/抹平快照逃不掉）']
[CLOSED] F-B2 原攻击（锚点不动抹平快照）  原案 verdict=ABNORMAL_SHAPE/rc=0 → 抹平后 rc=2
[CLOSED] F-B3 记录项换成案内别的真文件  ["上游收据 path 不在白名单 (…): supply_truth.json"]
[CLOSED] F-B3 边界外一步：白名单名加 ./ 前缀  ["上游收据 path 不在白名单 (…): ./channels_preflight.json"]
[CLOSED] F-B7 未登记链族不再崩栈  ["…未登记链族 'sui' 的快照绑定口径"]
```

- **F-B1** 关了两次：生产侧 `build_scan` final 分支强制"final 快照 sha == 绑定的 initial scan 快照 sha"，发布闸再把**终态 final scan** 也纳入同一条四查等值比对。我另做了第二道独立验证——先合法产完整案（gate 零报错），再**手改终态 scan 里记的快照 sha**，发布闸精确报出"终态 final"那条。轮 1 的端到端 BYPASS 不复存在。
- **F-B2** 死于零容差：删任何一个 owner 立刻破坏逐 wei 闭合。原攻击的 0.005bps 缺口不再有窗口可钻。
- **F-B4** 由 `test_fb4_second_layer_failclosed_branches` 三条定向用例接管；我把 M12 变异（找不到四查收据→静默 return）重放，**变红**（轮 1 时它能穿过全量 suite）。
- **F-B5** 已在 `scan-schemas.md` 写明"重验须重跑当前版本生产者…不闭合按 `data_broken` 拒收＝刻意收紧不是回归"，正是我建议的口径。

## 2. 特别盘点 a：mint 锚点落地态（我自己那条错判的更正）

**我轮 1 视角⑤ 判"total 锚未发现误伤"是错的。** 我当时只测了合成 dead-sink，没测过真实"真 `_burn`"案。用同级工作区真案产物**独立复算**（不看工单数字，自己读 `balances_final.json` + `replay_stats.json` 重算）：

| 案 | owners | sum(快照含 sink 行) | mint_total | sum==mint | mint−burn | sum==mint−burn |
|---|---:|---|---|:-:|---|:-:|
| APU | 32,635 | 420690000000000000000000000000 | 同左 | ✅ | 337889146346088792653960057820 | ❌ |
| IQ | 4,127 | 31082094105963223790329250162 | 同左 | ✅ | 23038913286553224147057740625 | ❌ |
| KOGE | 82,518 | 5000000000000000000000000 | 同左 | ✅ | 3379997186850493127129576 | ❌ |

**三案逐位与工单表一致，独立复现成立。** IQ 的 `0x0` 持 8.043e27、KOGE 的 `0x0` 持 1.62e24、APU 的 `dead` 持 8.28e28——快照确实带 sink 行。所以旧的 onchain/total 锚点会把 IQ（销毁 25.9%）、KOGE（销毁 32.4%）整类真 `_burn` 币按 `data_broken` 误杀，**锚点翻案成立，我的原判被推翻**。另核 APU 的真实收据：`onchain_total_supply == mint_total`、`replay_net == mint−burn`（form2 语义），工单表头把 onchain 写成 `mint−burn` 是笔误，不影响结论。

**两条误伤防线在 mint 锚下仍有效（实测）**：
- 我轮 1 的 dead-sink 20% 绿例（sum=mint≠net）重放 → `rc=0 / NORMAL_SHAPE`，`denominators` 与 `burn_sentinel` 都对；
- M3 族变异（把锚点从 mint 换成 net）→ **3 条红**（form1 真实收据、form2 真实收据、合成 dead-sink 全部被误杀并报警）。
- F-B2 攻击在容差 0 下真死（见上）。

## 3. 特别盘点 b：F-B6② 覆盖面裁定

**裁定：本轮可以收口，不立 finding；完整端到端保留在批 D 台账。** 理由三条：

1. 交付的不是纯内存桩——`_solana_case` 把 `supply_receipt.json` 与 `dist_rounds/round_1/distribution_scan.json` **真落盘**，`regular_case_path`／`load_json`／路径遏制这些真实机制都被走到；只有 recon wrapper 与 initial scan 两个 dict 是手搓的。
2. 覆盖了第二层 Solana 侧全部四条判定路径：sha 相符放行、initial 换仓拒、**终态 final 换仓拒**（F-B1 的 Solana 半边）、bundle 缺 `owners` 绑定拒。
3. 我做了一次"新校验删掉即红"抽查：把发布闸终态分支改成恒不报错 → 先红的正是 `F-03/2 Solana 终态 final 换仓被拒`，说明这层夹具**确实在钉生产代码**，不是摆设。

保留意见（不阻塞）：`chain_family` 到 `run()` 的这一段仍是 Solana 侧唯一没被真实案走过的接缝，加上 F-B6 已如实标注的"Solana 无实物锚"，两条一起留批 D。

## 4. 特别盘点 c：新增测试变异抽查

`/private/tmp/batchB_probe/mutate_r1.py`，8 条变异逐条注入后还原：

| 变异 | 结果 |
|---|---|
| N1 final 绑 initial 快照检查删除 | 变红（`P0-B1 final 换仓快照被拒`） |
| N2 发布闸终态分支改恒不报错 | 变红（`Solana 终态 final 换仓被拒`） |
| N4 上游收据白名单删除 | 变红（`P2-B5`） |
| N5 容差 0 放回 10bps | 变红（2 条） |
| N6 闭合锚点回退成 onchain | 变红（`P1-B3 form1 真实收据`） |
| N8 第二层 M12 分支静默放过 | 变红（`F-B4/M12`） |
| **N3 rounds 跨轮 `snapshot_sha` 一致性检查删除** | **全量 suite 仍全绿 → 见 N-B3** |
| **N7 锚点允许回退到影子键 `total_supply_raw`** | **仍全绿 → 见 N-B3** |

裁判点名的三处（final 绑定／mint 闭合／白名单）＋F-B4 三分支**确认删掉即红，非"为绿而绿"**。

**绿例误伤与断言强度**：钉死副本全量 `run_all` EXIT=0，无既有绿例被打掉。测试 diff 里没有 `assert` 被删改，只有新增。唯一需要记录的口径变动是 `test_a4_gate.add_distribution_initial` 改用案内真实 `balances_final.json`（1 owner）当快照，该案因此从"完整形态评估"落到 `low_sample` 终态——按批 A"夹具重绑等效重跑生产者"的先例这是**保真而非削弱**（原来那份 240-owner 合成快照与案根 replay 产物本就冲突），且完整形态评估路径仍由 p105 那条链覆盖（我的复核实测该案 final verdict = `NORMAL_SHAPE` 且发布闸零报错）。

## 5. 本轮新 finding

### N-B1 —— P2 —— 闭合锚点优先读**未被任何收据绑定**的案根 `replay_stats.json`

**一句话**：新的 `mint_closure_anchor` 取值顺序把"案根硬编码文件名 `replay_stats.json`"排在第一，把已被四查链验证的 `supply_truth.mint_total` 排在后面——分母这个新的关键字段回到了"自己报自己验"。

**实测（攻击面）**：抹平快照（删 5 个最小 owner）＋在案根丢一份配套的 `replay_stats.json`，收据里的真值 mint 与 `data/replay_stats.json` 都保持真实：

```
   收据 supply_truth.mint_total = 59127382（真值）
   data/replay_stats.mint       = 59127382（收据 inputs 常见绑定位置）
   案根 replay_stats.mint       = 59124503（未绑定，与抹平快照配套）
   抹平快照 sum = 59124503（少 5 个 owner）
   scan rc=0  锚点={'source': 'replay_mint', 'raw': '59124503', …}
   → 抹平快照凭未绑定的案根文件通过闭合
```

**实测（误伤面，更要命）**：案根留一份陈旧／异 cutoff 的 `replay_stats.json`，**合法快照直接被拒**：

```
   合法快照 + 案根陈旧 replay_stats → rc=2
   BLOCK: distribution data_broken: 快照 raw 和未对铸造总量 mint 精确闭合:
          快照=59127382 mint=118254764（replay_mint）容差=0bps
```

**为什么误伤面是真的**：真实案根本不把 replay_stats 放在案根。我扫了 9 个真案——IQ／QUQ／SQD／EGL1／BUILD／PING／BANANAS31／SIREN 全在 `data/`，KOGE 在 `data/replay/`，**只有 APU 在案根（且案根与 `data/` 两份并存，眼下 sha 相同纯属运气）**。也就是说施工方只在唯一一个"案根有"的案子上验证了主线取值路径，其余 8 个案子实际走的是 fallback ②。

**范围诚实标注**：这**不是**正式发布路径的新绕闸——发布闸仍把 initial 与终态 final 的快照 sha 双双钉在四查 `inputs.balances` 上，抹平快照要上报告仍得把四查收据一起伪造（F-12 既定边界）。暴露面是 −1 分段产物、`handoff_manifest` 与 `a4_gate` 的重验路径，以及上面那条对全体存量案生效的误伤。

**建议修法**：取值顺序倒过来并钉绑定——主源取 `supply_truth` 收据的 `mint_total`（它已由 `_bound_replay_totals` 对回收据 `inputs.replay_stats` 绑定的实物，且被 `replay_net == mint−burn` 交叉验过）；若仍要读 replay_stats 实物，就**读收据 `inputs.replay_stats` 指向的那份**，不要读硬编码的案根文件名。

### N-B2 —— P2 —— `replay_stats.json` 在场却非法时静默回退（与本批 F-08 定的规矩自相矛盾）

**一句话**：案根 `replay_stats.json` 是符号链接（或不是普通文件）时，`safe_file` 抛的 ValueError 被 `except ValueError: stats_path = None` 一把吞掉，锚点**无声无息换一档**继续算——正是本批 F-08 刚刚定性禁止的"在场却非法被静默漂白"，同一个文件里两套标准。

**实测**：

```
   案根 replay_stats.json → 指向案外文件的符号链接
   scan rc=0  锚点 = {'source': 'supply_truth_mint', 'raw': '59127382'}
   → 静默回退（未报错）
```

**建议修法**：照抄本批 F-08 的写法——`candidate.exists() or candidate.is_symlink()` 判在场，在场就必须 `safe_file` 成功，失败即 raise；只有"压根没有这份文件"才允许走下一档。

### N-B3 —— P3 —— 两条新防线零回归覆盖

**一句话**：`validate_rounds_ledger` 里新加的"跨轮 `snapshot_sha` 必须一致"（F-B1 的第三道保险）和"锚点不得用影子键"这条不变量，删掉／绕过后全量 suite 仍全绿。

**实测**：N3 与 N7 两条变异存活（见上表）。N7 能存活的原因很具体：守卫 `test_f03_closure_anchor_no_shadow_dependency` 只用正则扫**闭合比较那一行** `snapshot_sum.*total_supply_raw`，而分母是在 `mint_closure_anchor` 函数里选的——把影子键 fallback 加进那个函数，正则完全看不见。

**诚实定性**：两条当前代码都是对的，且各自都被更前面的防线遮住（每轮 final 都强制等于 initial 快照，所以跨轮 sha 天然一致）。属回归覆盖缺口，不是现存漏洞。

**建议修法**：①造一份"第 2 轮 `snapshot_sha` 与首轮不同"的 rounds 台账断言必红；②把影子键守卫从"扫比较行"改成"扫 `mint_closure_anchor` 函数体"或直接注入影子键跑一遍取值。

### N-B4 —— P3 —— `denominators.total_supply_raw` 语义变了但字段名与 schema 段没变

**一句话**：`analyze()` 的 total 参数换成 mint 锚点后，产物里 `denominators.total_supply_raw` 从"链上流通总量"变成"铸造总量（含已销毁）"，真 `_burn` 案两者能差三成以上，而 `scan-schemas.md` 的字段表原样未动。

**实测**（mint=2e22、销毁 20%）：

```
   mint=20000000000000000000000  链上流通 onchain=16000000000000000000000
   产物 denominators = {'total_supply_raw': '20000000000000000000000',
                        'net_supply_raw':   '16000000000000000000000', …}
   → total_supply_raw ＝ mint（含已销毁部分）
```

**范围**：全库代码消费者只有 `adjudication_validator.py:302` 读 `net_supply_raw`，**没有代码读 `total_supply_raw`**，所以不会算错数。风险纯在人读——按 IQ 的量级，照字面引用会把总量说高 34.9%。

**建议修法**：`scan-schemas.md` 的 `denominators` 字段表加一行注明 `total_supply_raw = mint_total（铸造总量，含已销毁）`；或干脆把键名改成 `mint_total_raw`（改名要连 schema 版本一起走，可留批 D）。

## 6. 复现件清单（本轮新增）

| 文件 | 用途 |
|---|---|
| `r1repo/` | `394ffbb` 钉死副本（三主文件逐字节核对 SAME），变异实验场，实验后逐条还原 |
| `recheck1.py` | F-B1／F-B2／F-B3／F-B7 攻击原样重放＋发布闸终态分支独立验证 |
| `probe4_anchor.py` | N-B1／N-B2／N-B4 的锚点攻击面与误伤面 |
| `mutate_r1.py` | 新校验 8 条变异抽查（N1~N8） |
| `run_all_r1.log` | 钉死副本全量 suite 独立复跑（EXIT=0） |

## 7. 终判

**批 B 不能就此收口，需要一个小范围的消化轮 2。** 原 7 条 finding 确实全关、且关得扎实（两条 P0 防线都经得起变异和边界外一步攻击），锚点翻案我也独立复算三案确认成立、我自己轮 1 的判断被正确推翻。但按 `maintenance-review-repair.md` §7.1「新引入不分严重度都要求修复后重审」，本轮**在修复中新引入**了 N-B1／N-B2 两条 P2——而且 N-B1 的误伤面对现有 9 个真案里的 8 个都成立，不是纸面风险。

轮 2 的范围很窄，估计一次施工就能收：**锚点取值顺序倒置并对绑定收据（N-B1）＋在场非法不静默回退（N-B2）＋两条红线补测（N-B3）＋文档一行（N-B4）**，其余部分不必返工。

消化轮 1 复核完成
