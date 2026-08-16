# 修复批 A 批内对抗审查（盲审）

审查对象：commit `f575472`（基线 `2ebd885`）的代码与测试部分。
审查人：与施工方不同线程的对抗审查者，只读代码、只跑测试，未改任何生产文件。
实测脚本落在 `/private/tmp/batchA_probe/`（exp_a…exp_g），每条 finding 都有可复现命令。

**结论：7 条 finding，最高 P1。** 两条 P0 的"正面"都确实修上了（原反例先红后绿可复现），
但新装的两道闸各留了一条更省事的旁路，消费侧新代码的绝大部分没有测试锁住。

---

## 视角①：字段来源（有没有"自己报自己验"）

### F-A（P1）消费侧的"独立重算"只是三个自报数字互相印证；绕开整套 waiver 只需改一个数

**缺陷一句话**：`_validate_tolerance_policy` 用收据自报的 `replay_net`／`onchain_total_supply`／
`tolerance_bps` 重算判定，而这三个数没有任何一个被拿去和已经哈希绑定、就躺在案根里的
`replay_stats.json` 对过账——于是"抬容差"这条路被堵死，"改重放净供给"这条路照走，
连人工裁决收据都不用办。

**实测复现**：

```bash
python3 /private/tmp/batchA_probe/exp_a_replaynet.py
```

```text
[诚实跑 tolerance=10] exit=2 verdict=FAIL replay_net=1 onchain=100 diff_bps=9900.0
[绑定输入真值] replay_stats.json → mint=1 burn=0 净=1
[攻击结果] 共享发布校验器 放行 —— 无 waiver、容差 0bps，而绑定输入实际净供给=1、链上=100
[对照组 抬容差] 被拒: supply_truth formal tolerance above 10bps lacks tolerance waiver
```

复现要点（不依赖脚本也能重做）：跑一次真实 FAIL 的 supply truth，然后只把收据里的
`replay_net` 改成与 `onchain_total_supply` 相等、`tolerance_bps` 改成 0、
`primary_verdict/verdict` 改 PASS、`exit_code` 改 0，**并把 `inputs.tolerance_waiver` 整个删掉**，
`inputs.replay_stats` 原样留着（磁盘文件一个字节没动，sha 仍然对得上），
再调 `shared.validate_reconciliation_check(...)`——放行。

**为什么这不算"已知的验证器不能证真"**：`independent-audit-protocol.md` 说聚合器抓不住
"填对哈希又编出互相自洽观测"的主动造假——这条我认。但本例造出来的观测**不自洽**：
它和同一个案子里被哈希绑定、校验器已经握在手里的 `replay_stats.json` 直接打架。
让校验器把手上两份东西对一对，不需要它证明任何链上真相。
工单 ④ 视角①写的"producer 和 consumer 不形成'自己说自己对'的单点信任"，
以及 commit message 的"消费侧同源重算 primary_verdict"，就这条路而言不成立。

**建议修法**（约 5 行，依赖已经 import 的模块）：
`_validate_tolerance_policy` 里加一段——读 `inputs.replay_stats` 绑定的那个文件，
`supply_truth_gate.parse_replay_stats` 解出 mint/burn，
要求 `mint - burn == int(receipt["replay_net"])`；解不出来就 fail-closed（旧格式走"存量案重跑"话术）。
`sink_fallback_form2` 分支里 `mint_total`／`burn_total` 两个标量同理。
`onchain_total_supply` 消费侧确实无源可对，但它是 RPC 观测、不是重放产物，
现在最软的一环恰恰是重放侧，而重放侧有源可对。

---

### F-B（P2）新加的 `model_probe_block` 没有任何消费方，时点闸只挂在一个自报字段上

**缺陷一句话**：F-01 特意加了 `model_probe_block` 来"诚实记录探测时点"，
但全库只有生产者写、没有任何校验器读，于是把 `tip_block` 一个字段抬上去就能过时点闸，
而唯一能暴露这次抬价的字段没人看——删掉它、填 0、填字符串，发布链一律放行。

**实测复现**：

```bash
rg -n "model_probe_block" --glob '*.py' scripts/ | grep -v scripts/tests
# 只有 scripts/evm/accounting_gate.py:435 一处写入，零处读取

python3 /private/tmp/batchA_probe/exp_b_probeblock.py
```

```text
[单改 tip_block：as_of=101 tip=101 而探测其实发生在 100] 放行 ✅  accounting: as_of=101 tip=101 probe=100 → 发布 target.as_of_block=101
[删除 model_probe_block] 放行 ✅  accounting: as_of=1 tip=100 probe=<无此字段>
[model_probe_block=0（与 tip=100 自相矛盾）] 放行 ✅
[model_probe_block='不是数字'] 放行 ✅
```

**建议修法**：消费侧 EVM 分支再加两句——`model_probe_block` 必须是非负整数、
且**等于** `tip_block`（生产侧本来就把同一个 `tip` 写进两个字段，等于零成本），
再要求 `as_of_block <= model_probe_block`。这样想过时点闸就得同时改两个字段，
而且 plan_review 里 codex 提的"语义字段不一致要拒"才算真正落地——现在这一条没落。

---

### F-E（P2）一张 waiver 能把供给真值闸整体关掉，而裁决人签字的那张纸上没有他实际看到的偏差

**缺陷一句话**：`approved_tolerance_bps` 没有上限、waiver 里也不记录本次实际偏差
（`diff_bps`／`onchain_total_supply` 都不在必填里），
`evidence_refs` 只要求"案内存在的普通文件且 sha/size 对得上"——
指向本次运行自己的 `replay_stats.json` 也算"人工核对证据"。
于是"人工裁决"能落到纸面的实质内容只剩一行自由文本理由。

**实测复现**：

```bash
python3 /private/tmp/batchA_probe/exp_e_waiver_strength.py
```

```text
[生产侧] exit=0 verdict=PASS 重放净=1 链上=100 偏差=9900.0bps 容差=100000000bps
[这张 waiver 的全部人工内容] approved=100000000bps approved_by='risk-committee@example.test' 证据=['replay_stats.json'] 理由='特殊迁移币已人工核对，批准本次供给真值容差。'
[waiver 里有没有记录实际偏差] diff_bps 字段存在=False，onchain 字段存在=False
[消费侧] 共享发布校验器 放行 —— 99% 供给对不上仍算 PASS
```

**和仓内先例的差距**：`holder_distribution_scan.validate_waiver` 把 waiver 绑到
`final_scan_sha256`／`rounds_sha256`／`a4_seal_sha256`——绑的是**被豁免的那个结果**，
裁决人签的是他看见的东西。tolerance waiver 只绑输入侧（工单里写明是有意为之），
输入定了结果基本也就定了，所以差距不像表面那么大；
真正的缺口是**纸面上没有那个数**：事后翻案时无从判断裁决人当时是否知道偏差有 9900bps。

**建议修法**：waiver 增必填 `observed_diff_bps`（人工看到的实际偏差），
生产侧要求"本次算出的 `diff_bps` ≤ waiver 记录的 `observed_diff_bps`"，
消费侧照抄这一条；`evidence_refs` 禁止指向本次 envelope 输入自身（至少要与 `replay_stats` 不同路径）。
`approved_tolerance_bps` 是否设硬顶交用户裁决——设了就不是"人工可以放行任何情况"了，属政策问题不是工程问题。

---

## 视角②：失败分支（fail-closed／退出码分流）

新闸的判定分支本身都是 fail-closed，实测没抓到静默 pass 的分支
（`_require` 全部抛 ValueError，`TolerancePolicyError` 优先于 `except Exception` 捕获，
exploration 收据进不了正式聚合器——见视角③）。但退出码分流有一处串线：

### F-D（P2）同一类"文件读不动"故障，退出码分成两档；且 exit 2 现在一码三义

**缺陷一句话**：waiver 本体读不动 → exit 2 并报"JSON 损坏"（其实是权限错误）；
waiver 里 `evidence_refs` 指的文件读不动 → exit 1。
同一类环境故障走两条码，且 exit 2 现在同时表示"供给不闭合 FAIL"（有收据）、
"argparse 参数错"、"容差政策拒绝"（无收据），调用方没法只看码分辨。

**实测复现**：

```bash
python3 /private/tmp/batchA_probe/exp_d_exitcodes.py
```

```text
当前 uid=502（非 0 才能让 chmod 000 生效）
[waiver 权限不可读] exit=2 收据=无 stderr=正式容差政策拒绝（exit 2）: tolerance waiver JSON 损坏: [Errno 13] Permission denied: '…/waiver.json'
[evidence 权限不可读] exit=1 收据=无 stderr=检测自身失败（exit 1，修通道重跑）: [Errno 13] Permission denied: '…/evidence.txt'
[超容差无 waiver 重跑] 第一次 exit=2 verdict=FAIL；第二次 exit=2；旧收据原地未动=True
```

根因在 `supply_truth_gate.py:116-119`：`except (OSError, json.JSONDecodeError)` 把两类合并成
"JSON 损坏"再升格成政策错误（exit 2）；而 `_waiver_file_ref` 里的 `_sha256_file` 抛 OSError
没被包，落到外层 `except Exception` → exit 1。工单 ④ 视角②写的"三类语义没有混在一起"被实测推翻。

**第三行输出的补充风险**：政策拒绝走 exit 2 且不落收据，上一轮的旧 `supply_truth.json` 原地不动。
正式发布路径不受影响（`reconciliation_report.py` 受控 runner 有"receipt pre-exists 就拒跑"，
见 `scripts/report/reconciliation_report.py:180`——读码确认，未单独实测），
但 `references/analyze-workflow.md` 教的是人工直接敲命令，
人按文档把 exit 2 读成"该币 FAIL，余额改走实时直查"，手边还留着一份上一轮的 PASS 收据——
这是个真会踩的坑。

**建议修法**：读文件的 OSError 一律归 exit 1（检测自身失败，修通道重跑），
只有"内容/政策不合法"才 exit 2；`_waiver_file_ref` 的 sha 计算也包一层保持一致。
政策拒绝时把 `--out` 指向的旧收据显式作废（写 error receipt 或删除），别留在原地。

### F-F（P2）新旗标与新硬顶在用户能看到的文档里一个字都没有，退出码契约现在是残的

**缺陷一句话**：`--tolerance-waiver` 和"formal 模式 10bps 硬顶"没有进入
闸自身的用法头注、`references/`、`SKILL.md`、`CHANGELOG.md` 任何一处；
`supply_truth_gate.py` 头注仍写"`--tolerance-bps N` 容差，默认 10（0.1%）"、退出码仍是干净三档，
`references/analyze-workflow.md` 的 exit 2 定义（"FAIL＝该币余额禁用重放结果…"）现在不完整。

**实测复现**：

```bash
rg -n "tolerance-waiver|tolerance_waiver" references/ SKILL.md CHANGELOG.md   # 零命中
rg -n "tolerance" references/analyze-workflow.md SKILL.md                      # 零命中
sed -n '22,34p' scripts/lib/supply_truth_gate.py                               # 用法与退出码表未更新
```

**说明**：`contract_manifest.json` / `contract_ids_snapshot.json` 的登记是工单明示留批 D 的，
不在本条范围内；本条说的是操作者当场要读的用法与退出码语义。
真遇到需要放大容差的币，操作者按现有文档根本不知道有 waiver 这条合法通道。

**建议修法**：闸头注补一行 `--tolerance-waiver`、退出码表补"政策拒绝（无收据）"这一类；
`analyze-workflow.md` §3 第 3 步那句 exit 语义同步。批 D 收口时和契约快照一起做也行，
但别漏在"契约登记"名下——那两份快照不含 CLI 用法文本。

---

## 视角③：绕闸（别的入口／别的参数组合／别的调用序）

除 F-A（不碰容差、不办 waiver，直接改重放净供给，走的就是另一条门）外，
**其余绕闸设想全部实测被拒，未发现新的独立旁路**：

```bash
python3 /private/tmp/batchA_probe/exp_g_boundary.py
```

```text
[exploration 10000bps] exit=0 mode=exploration verdict=PASS
[exploration 收据直送发布链] 被拒 ✅ supply_truth receipt must be formal and bind replay_stats input
[exploration 收据手改 mode=formal] 被拒 ✅ supply_truth receipt must be formal and bind replay_stats input
[formal 10bps 真实 9900bps 偏差] exit=2 verdict=FAIL
[formal 10bps 的 FAIL 收据] 被拒 ✅ reconciliation supply_truth wrapper/receipt verdict mismatch
[waiver 绑案内 stats、实跑喂案外同内容 stats] exit=2 被拒 ✅ waiver replay_stats 未绑定本次实际输入
```

另外查过并确认没问题的几条：
- 另一个发布入口 `audit_release_gate.run()` 是**无条件**调 `shared_release_receipt.validate_bundle`
  （`scripts/report/audit_release_gate.py:762`），EVM 时点闸在这条路上也必经，没有绕过。
- 受控 runner 逐项透传 job spec 的 `argv`，`--tolerance-waiver` 在正式路径上够得着，
  waiver 通道不是"装了用不了"。
- `supply_truth` 的生产者被 `repo_ref_ok` 钉死在 `scripts/lib/supply_truth_gate.py` 并比对当前 sha，
  没有第二个能产 `supply-truth-receipt/v3` 的入口。

一条**非绕闸、但方向相反**的误伤记在这里：

### F-G（P2）案目录被复制到新路径后，带 waiver 的收据必被拒，且报错把人往错误方向引

**实测复现**：

```bash
python3 /private/tmp/batchA_probe/exp_f_copiedcase.py
```

```text
[原案目录] exit=0 verdict=PASS
[收据里记录的 waiver 路径] /private/tmp/expF-orig-…/waiver.json     ← 绝对路径
[原地校验] 通过
[复制到新路径后校验] 被拒: tolerance waiver input escapes case root
[原案已不存在时校验] 被拒: reconciliation supply_truth receipt envelope invalid: input replay_stats invalid: …No such file…；存量案例须重跑对应生产者获取当前回执
```

**如实定性**：根因是既有的 envelope 输入绝对路径绑定（原案一旦不在，任何带 inputs 的收据都过不了），
**不是本批引入**。本批的问题在两点：一是工单 ④ 自述"shared 曾要求普通 replay_stats 必须位于案根内，
会误伤复制案例；该非工单约束已删除"——实测显示带 waiver 的复制案仍然过不了，自述给人"复制案已修好"的错觉；
二是新报错文案 `tolerance waiver input escapes case root` 会把人往"waiver 放错地方了"上引，
而 waiver 明明就在案根里，真正原因是收据里记的是老路径。

**建议修法**：消费侧判 waiver 位置时，用"收据所在案根 + 记录路径的 basename/相对部分"重定位
（和 `_bound_case_ref` 同一套 base 逻辑），路径对不上时的文案改成"收据记录的输入路径与当前案根不一致，
存量案或复制案须重跑生产者"。彻底方案（inputs 记相对路径）超出批 A，建议记进批 D 候选。

---

## 视角④：测试有效性

用"内存里打断生产代码、磁盘不动"的变异法测了 18 处（脚本 `exp_c_mutation.py` / `exp_c2_mutation.py`，
每次把改过的模块塞进 `sys.modules` 再跑 `test_repair_batch_a.main()`）。

### F-C（P2）消费侧新增的 waiver 校验约 45 行几乎没有测试锁住：删掉 8 处，本批测试仍然全绿

**实测复现**：

```bash
python3 /private/tmp/batchA_probe/exp_c_mutation.py    # 生产侧 + 时点闸 9 处
python3 /private/tmp/batchA_probe/exp_c2_mutation.py   # 消费侧 waiver 分支 9 处
```

```text
M1 消费侧只验 tip 在场、不验 as_of<=tip: 变红 ✅
M2 消费侧不再重算 primary_verdict: 变红 ✅
M3 消费侧不再要求高容差配 waiver: 变红 ✅
M4 生产侧不再逐项验 evidence_refs: 变红 ✅
M5 生产侧取消 formal 容差钳制: 变红 ✅
M6 生产侧不写 model_probe_block: 变红 ✅
M7 生产侧 waiver 不再校验 target 全等: 变红 ✅
M8 生产侧 waiver 不再校验 approved_by: 仍然全绿 ❌
M9 生产侧 waiver 不再校验 user_decided_at_utc: 仍然全绿 ❌
M10 消费侧不验 approved_by: 仍然全绿 ❌
M11 消费侧不验 user_decided_at_utc: 仍然全绿 ❌
M12 消费侧不验 waiver target 全等: 仍然全绿 ❌
M13 消费侧不验 evidence_refs 逐项绑定: 仍然全绿 ❌
M14 消费侧不验 waiver 的 replay_stats 绑定收据输入: 仍然全绿 ❌
M15 消费侧不验 waiver schema: 仍然全绿 ❌
M16 消费侧不验 approved_tolerance_bps 上限: 仍然全绿 ❌
M17 时点闸误伤 Solana（去掉 family==evm 限定）: 变红 ✅
M18 消费侧 waiver 必填字段整组不验: 仍然全绿 ❌
```

即：本批消费侧新增的校验里只有三件事被断言锁住——EVM 时点闸（在 `validate_sources`）、
重算矛盾与"高容差必须有 waiver"（在 `_validate_tolerance_policy`）；
而"这张 waiver 本身是不是合法"的全部校验——schema、必填组、裁决主体、UTC 时间、target 全等、
批准上限、replay 绑定、evidence 绑定——一条都没测。全库也只有本批测试碰过 tolerance waiver
（`rg -l "tolerance_waiver" scripts/` 只有生产/消费两个源文件 + 本批测试 + 反例脚本），
所以不是"别的测试文件替它测了"。

两处生产侧漏网（M8/M9）根因是反例写法：`lambda w: w.pop("approved_by")` 打中的是"必填组"分支，
`approved_by` 专用的"非空白字符串"检查和 `user_decided_at_utc` 的整段时间校验从来没被触发。

**顺带一条定性**：`waiver_swap_integrity.py` 这个"边界外攻击"反例拦下换件的是**既有**的
`receipt_validate.validate_receipt`（错误原文 `input tolerance_waiver size/hash mismatch`
唯一产地是 `scripts/lib/receipt_validate.py:103,105`），不是本批任何新代码——
证据就是上面 M10–M18 把消费侧新校验删光，这条反例测试照样绿。
工单把它记成"防线单点但必经"是诚实的，但拿它当**本批新装防线**的边界外验收会高估新代码。

**建议修法**：
1. 把 `test_f02_waiver_negatives_and_failures` 那 5 个反例在消费侧再跑一遍
   （构造好收据 + waiver 后调 `validate_reconciliation_check`），一份反例喂两侧；
2. 补两条生产侧反例：`approved_by` 填全空白串、`user_decided_at_utc` 填 `"2026-13-45"`（或去掉 Z）；
3. 消费侧补 schema 名写错、必填缺一个、evidence sha 改错三条。

其余测试有效性检查结果（未发现问题）：
- `test_f01_solana_not_subject_to_tip_check` 不是空跑——哨兵 `AccountingPassed` 打在
  `validate_reconciliation_report`（`shared_release_receipt.py:412`），在时点闸之后，M17 变红可证。
- `test_f02_tolerance_cap_uses_producer_constant` 虽然是 import 来的同一个对象、看着像恒真断言，
  但它锁的是"两侧取值不许分叉"这个实质属性：若有人改成手抄字面量、日后生产侧调数，该断言仍会变红。不算缺陷。
- 全量 SUITE 在本机复跑结果见文末。

---

## 汇总

| 编号 | 严重度 | 视角 | 一句话 |
|---|---|---|---|
| F-A | **P1** | ①③ | 消费侧重算只对自报数字，改 `replay_net` 即可绕开整套容差钳制与 waiver |
| F-B | P2 | ① | `model_probe_block` 零消费方，时点闸单字段可过 |
| F-C | P2 | ④ | 消费侧 waiver 校验 8 处删掉测试仍全绿；换件反例测的是既有防线 |
| F-D | P2 | ② | 同类文件故障 exit 2/1 串线且文案误导；exit 2 一码三义、政策拒绝留旧收据 |
| F-E | P2 | ① | waiver 可把不变量整体关掉，纸面上没有裁决人实际看到的偏差 |
| F-F | P2 | ② | 新旗标/新硬顶未进用户可见文档，退出码契约残缺（契约快照登记已明示留批 D，不计） |
| F-G | P2 | ③ | 复制案带 waiver 必被拒且报错误导（根因既有，自述"已修好"与实测不符） |

**没有 finding 的部分**：视角③除 F-A 外未发现新的绕闸路径（exploration/formal 边界、
第二发布入口、生产者白名单、受控 runner 透传四项均实测符合预期）；
新校验分支未发现静默 pass（fail-closed 成立）。

**建议处置顺序**：F-A 本批内补（改动小、正好补在这次动过的函数里，不补则 F-02 的"正式模式供给真值闸
形同虚设"这句话仍然成立，只是换了条路）→ F-C（测试补齐，成本低）→ F-B → F-D/F-F → F-E/F-G 可入批 D。

**全量 SUITE 复跑（本机，未变异）**：`python3 scripts/tests/run_all.py` → 退出码 0，末行"全部通过"，
日志留在 `/private/tmp/batchA_probe/run_all.log`。
（工单⑤记的是 rc=1、`test_batch3_solana_vertical_slice.py` 等 2 项未进业务断言；
本机这 2 项也是 PASS，属环境差异，不影响本批结论。本次盲审所有 finding 都不是"测试跑不起来"类问题。）

对抗审查完成
