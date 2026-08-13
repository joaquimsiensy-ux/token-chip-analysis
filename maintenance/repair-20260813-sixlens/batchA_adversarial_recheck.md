# 修复批 A 消化循环第 1 轮 —— 闭环复核（盲审第二轮）

复核对象：commit `78d1c4c`（基线 `f575472`）。
复核人：与施工方不同线程的对抗审查者，只读代码、只跑测试，未改任何生产文件。
方法：先重放上一轮全部探针（`/private/tmp/batchA_probe/exp_a…exp_g` 与两套变异脚本），
再对本轮**新增代码**另起一轮视角①②攻击（`exp_h`～`exp_k`）。不采信工单自报，逐条实跑。

**结论：5 FIXED / 2 PARTIAL；新 finding 2 条，最高 P1。**
本轮修的六项半都真修上了（原攻击全部转拒、14 处新变异 13 处转红）；
但 F-A 那道 P1 只堵住了我上一轮填的那条具体走法，同一层楼还开着两扇门——
**换一本账（绑案外伪造 replay_stats）**和**改另一个没人对账的数（onchain）**，
两条都实测放行，其中 Solana 那条的实物就摆在消费侧已经读进内存的 bundle 里。

---

## 一、七条逐一判定

### F-A（P1 消费侧实物对账）→ **PARTIAL**

**已修上的部分**（实测转拒）：

```bash
python3 /private/tmp/batchA_probe/exp_a_replaynet.py
```

```text
[诚实跑 tolerance=10] exit=2 verdict=FAIL replay_net=1 onchain=100 diff_bps=9900.0
[绑定输入真值] replay_stats.json → mint=1 burn=0 净=1
[攻击结果] 被拒: ValueError: supply_truth replay_net 与绑定 replay_stats 实物的 mint−burn 不一致；存量案例须重跑对应生产者获取当前回执
```

形态②的 `mint_total/burn_total` 也一并绑上了（新测试 `test_fa_sink_fallback_scalars_bound_to_stats`
先跑出真实形态② PASS 收据再伪造，属于真红绿，不是摆设——变异 NM1/NM2 均转红可证）。

**缺口一（新 finding N-1，详见第二节）**：对账读的是"收据自己指的那个文件"，
可以指向案根之外的伪造账本，案根里那份真账本原封不动没人看。

**缺口二（新 finding N-2）**：三个数里 `onchain_total_supply` 仍是纯自报，
改它一个字段即可把 FAIL 翻成 PASS，不需要 waiver、不需要动任何文件。

**为什么判 PARTIAL 而不是 FIXED**：finding 原文的标题就是"消费侧的独立重算只是自报数字互相印证；
绕开整套 waiver 只需改一个数"。现在**改一个数**（onchain）依然成立，**换一本账**也依然成立。
我上一轮填的那条复现路径确实关了，这点如实记账。

### F-B（model_probe_block 消费校验）→ **FIXED**

```bash
python3 /private/tmp/batchA_probe/exp_b_probeblock.py
```

```text
[单改 tip_block：as_of=101 tip=101 而探测其实发生在 100] 被拒 ⛔ EVM accounting model_probe_block must equal tip_block
[删除 model_probe_block] 被拒 ⛔ model_probe_block missing or invalid
[model_probe_block=0（与 tip=100 自相矛盾）] 被拒 ⛔ must equal tip_block
[model_probe_block='不是数字'] 被拒 ⛔ missing or invalid
```

四个场景全转拒；变异 NM4（去掉 `probe == tip`）、NM5（去掉类型校验）都能把新测试打红。
想抬时点现在必须同时改两个字段且保持自洽——正是要的效果。

### F-C（测试补齐＋夹具失真修正）→ **FIXED**

上一轮 18 处变异里 9 处漏网，本轮重跑：

```bash
python3 /private/tmp/batchA_probe/exp_c_mutation.py
python3 /private/tmp/batchA_probe/exp_c2_mutation.py
```

M8/M9/M10/M11/M12/M14/M15/M16/M18 **全部由"仍然全绿"转为"变红"**；
M4/M13 因为修复动了那两段代码、老锚点失配，我用更新后的锚点重跑（`exp_j` 里的 M4'/M13'），
也都转红。夹具失真（拿 `raw_transfers` 冒充 replay_stats）已改为绑真实重放统计，
并特意避开 `replay_stats.json` 正名以防 a4_gate 链跑 replay_pass1 覆盖——这个细节是对的。

`consumer_case` 那个新夹具确实解决了"看着有测其实测的是既有掉包校验"的问题：
它跑完 producer 后把收据 inputs 的 size/sha **重新绑到变异后的 waiver 实物**上，
所以 `receipt_validate` 的掉包闸不会抢先响，消费侧新校验才真正被逼出红绿——
这一点我不是看注释信的，是靠 M10–M18 全部转红反证的。

一处残留（不算 finding）：消费侧 `observed_diff_bps` 的**类型**校验没有测试覆盖（变异 NM10 仍全绿），
但删掉它并不开洞——后面 `float(observed_diff)` 会自己炸：

```text
[现行代码 observed_diff_bps=字符串] 被拒 ✅ ValueError: tolerance waiver observed_diff_bps invalid
[删掉类型校验后 observed_diff_bps=字符串] 被拒 ✅ ValueError: could not convert string to float: '很大'
[删掉类型校验后 observed_diff_bps=数组] 被拒 ✅ TypeError: float() argument must be…not 'list'
```

补一条消费侧非数值反例即可闭合，优先级很低。

### F-D 前半（OSError 归 exit 1）→ **FIXED**；后半（旧收据作废）→ 批 D，但请看补充证据

```bash
python3 /private/tmp/batchA_probe/exp_d_exitcodes.py
```

```text
[waiver 权限不可读]   exit=1 收据=无 stderr=检测自身失败（exit 1，修通道重跑）: [Errno 13] Permission denied…waiver.json
[evidence 权限不可读] exit=1 收据=无 stderr=检测自身失败（exit 1，修通道重跑）: [Errno 13] Permission denied…evidence.txt
[超容差无 waiver 重跑] 第一次 exit=2 verdict=FAIL；第二次 exit=2；旧收据原地未动=True
```

同一类通道故障两处都归 exit 1，串线消除；`_waiver_file_ref` 里把"文件不存在"（政策）与
其他 OSError（通道）拆开的写法是对的。第三行是留给批 D 的那半——见第三节我的意见。

### F-E 前半（observed_diff_bps＋证据独立性）→ **FIXED**；后半（approved 硬顶）→ 批 D

```bash
python3 /private/tmp/batchA_probe/exp_h_round2.py   # N-3 段
```

```text
[observed 报小]  exit=2 收据=无 正式容差政策拒绝: 本次实际偏差 9900.0bps 超过 waiver 记录的 observed_diff_bps 100.0bps——裁决人没见过这么大的偏差…
[证据=replay_stats 自身] exit=2 收据=无 正式容差政策拒绝: waiver evidence_refs[0] 不得指向本次 replay_stats 输入自身，人工核对证据必须是独立文件
```

上一轮 exp_e 里那张"证据指向自己、批准 1e8"的 waiver 现在生产侧直接拒收（脚本跑到打印语句就
因为 receipt 为 None 崩了，就是被拒的直接证据）。生产/消费两侧都装了，变异 NM3/NM6/NM7/NM8/NM9 全红。
把 `assert_waiver_covers_diff` 的比较值取自同一个 `decide()` 返回、避免两处各算一遍在浮点边界分叉，
这个处理是对的。

一句提醒（归到批 D 那条政策项里，不单列 finding）：`observed_diff_bps` 和 `approved_tolerance_bps`
一样可以**预先虚报**——裁决人写 99999 就等于提前批了一个他没见过的偏差。
真要定硬顶，这两个数得一起管。

### F-F（文档同步）→ **FIXED**

闸头注补上了 `--tolerance-waiver` 全部必填项，退出码表改成"exit 2 看有没有落收据分两种语义"，
`references/analyze-workflow.md` 同步了同一句并写清了唯一合法通道。文字是大白话，
和 skill 的写作纪律一致。**唯一挂心**：这套判别法（"没落收据＝政策拒绝"）
依赖案目录里没有上一轮的旧收据——而那正是批 D 未修的那半。
文档里已经加了"也别把上一轮留在原地的旧收据当本轮结果"作为提醒，属可接受的临时处置；
批 D 修完后建议把这句提醒降级为机器保证。

### F-G 前半（误导文案）→ **FIXED**；后半（相对路径根治）→ 批 D

```bash
python3 /private/tmp/batchA_probe/exp_f_copiedcase.py
```

```text
[复制到新路径后校验] 被拒: 收据记录的 tolerance waiver 路径不在当前案根内——存量案例须重跑对应生产者获取当前回执（存量案或整目录复制过的案子，收据里记的是老绝对路径，不是 waiver 放错了地方）
```

文案现在指向真根因，不再把人往"waiver 放错地方"上引。

---

## 二、对本轮新代码的二次攻击（视角①②）

### N-1（**P1**）实物对账绑的是"收据自己指的那个文件"，可以指向案根之外的伪造账本

**一句话**：`_bound_replay_totals` 拿 `inputs.replay_stats.path` 直接 `resolve()` 后读文件，
既不要求它落在案根内，也不要求它和同案 balance/supply 两查收据绑的是同一份账本。
于是伪造者不用改收据里的数，改成**绑另一本账**就行——那本账可以躺在案外任何地方，
案根里真正的 `replay_stats.json` 原封不动、没人再看它一眼。

**实测**：

```bash
python3 /private/tmp/batchA_probe/exp_h_round2.py   # N-1 段
```

```text
    案根里真实 replay_stats：{'mint_total_raw': '1', 'burn_total_raw': '0'}
    收据改绑的案外文件：/private/tmp/expH1-outside-…/replay_stats.json   （内容 mint=100）
[N-1 绑案外伪造账本] 放行 ❗
```

真实局面是"重放净供给 1、链上 100"（10000% 对不上），伪造后消费侧全程放行。

**为什么这条比一般伪造更值得堵**：伪造账本**不需要进案目录**，
因此不会出现在 `audit_input_manifest.json` 的文件清单里、不会被人工翻案子时看见、
也不会和 balance/supply 两查收据绑定的同一份 stats 撞哈希——
换句话说，它绕过的恰恰是本仓"内容绑定"防线的全部可见性。
相比之下，如果强制在案根内，伪造者只能覆盖案里那份真账本，那会立刻把
balance/supply 两查收据的 input 哈希打炸，一望即知。

**建议修法**（不依赖批 D 的相对路径改造）：
1. `_bound_replay_totals` 增加 `root` 参数，用现成的 `_bound_case_ref` 判定
   （案根内 + 非符号链接 + size/sha 三验），落在案根外一律 fail-closed；
2. 再加一条同源校验：supply_truth 绑的 replay_stats 必须与 balance/supply 两查收据
   绑定的那份**同一路径同一哈希**（`verify_recon` 的收据本来就绑了它）。
**可行性我核对过**：现有全部夹具与产线都把 stats 落在案根内——
`test_repair_batch_a`（root/replay_stats.json）、`test_audit_release_gate` 与
`test_handoff_manifest`（root/fixture_replay_stats.json，本轮新加）、
`test_r9_batch3`（case/replay_stats.json）、两条 batch3 垂直切片与
`test_supply_truth_gate`（cwd=案根下的相对文件名 stats.json / stats_evm.json）。
上一轮曾因误伤 `test_a4_gate` 撤过一条案根约束，所以落地前请施工方实跑那条链确认，
但从夹具落位看条件已经变了。

### N-2（**P1**：Solana 有实物未对账；EVM 半属设计问题）`onchain_total_supply` 仍是纯自报

**一句话**：F-A 把三个数里的 `replay_net` 钉在实物上之后，最省事的走法就换成了改另一个数——
`onchain_total_supply` 改到与重放净供给相等，`decide()` 重算自洽、容差 0bps 不用办 waiver，
一个字段、一次编辑，FAIL 变 PASS。

**EVM 实测**：

```bash
python3 /private/tmp/batchA_probe/exp_h_round2.py   # N-2 段
```

```text
    真实链上=100、重放净=1（10000% 对不上）；只把 onchain 改成 1
[N-2 改 onchain 冒充闭合] 放行 ❗
```

**Solana 实测（这半是重点：实物就在手上没比）**：

```bash
python3 /private/tmp/batchA_probe/exp_i2_solana_onchain.py
```

```text
[诚实跑] exit=2 verdict=FAIL replay_net=1000 onchain=100 （bundle 实物 supply.amount=100）
[伪造后] 收据自报 onchain=1000，同案 bundle 实物仍写着 100（消费侧已把 bundle 读进内存比 slot）
[结果] 放行 ❗ —— onchain 与 bundle 实物没有对账
```

Solana 的链上供给本来就来自哈希绑定的 `bundle.json`（`supply.amount`），
而 `validate_reconciliation_check` 的 Solana 分支**已经把这个 bundle 读进内存**、
拿它比过两处 slot，偏偏没把 `supply.amount` 和收据自报的 `onchain_total_supply` 比一比。
这和 F-A 的病因一模一样：**手里握着实物，就是不对账**。

**建议修法**：
- Solana（现在就该修，2 行）：在既有 bundle 校验那段加
  `_require(str(receipt["onchain_total_supply"]) == str(bundle["supply"]["amount"]), …)`。
- EVM（批 D 设计项）：案内确实没有第二份冻结块 totalSupply 实物
  （`accounting_gate` 只在 rebase 检验里记 tip/tip−W 两点，不是冻结块；
  `verify_recon` 的 `nominal_supply_raw` 来自 config 人工声明，不是 RPC 观测），
  所以要么让 supply_truth 额外落一份可绑定的链上观测件（像 Solana 的 bundle 那样），
  要么就在 `independent-audit-protocol.md` 里把"EVM 侧链上供给无案内实物可对、
  只能靠复跑与 git 历史追责"写成明示局限，别让读者以为消费侧全都对过账了。
  两条路都行，但不能默认现状＝已闭合。

### 未发现问题的部分（实测过，没破）

- **新对账函数自身的失败分支全部 fail-closed**：旧格式 stats 解不出 mint/burn → 拒并给存量案重跑话术；
  绑定的实物被删 → 上游 envelope 校验先拒。（`exp_h` N-5a/N-5b）
- **零误伤**：`exp_g` 六个边界场景仍全部正确被拒；
  诚实的 EVM 形态①/形态② 收据、诚实的 Solana 收据、合法 waiver 绿例都照常通过。
- **exploration/formal 边界**未松动：exploration 收据（含手改 `mode=formal`）仍进不了正式聚合器。
- **本轮新代码的测试锁定度**：14 处新变异 13 处转红，唯一漏网 NM10 被 `float()` 兜住不成洞。
- **一条既有守卫的额外发现**（对批 D 有用）：`publish_overwrite` 拒绝把已有 PASS 收据降级覆盖
  （实测报 `existing PASS artifact cannot be downgraded`），所以"旧 PASS 收据挡住新 FAIL"
  会以 exit 1 写入失败的形式吵出来，不会静默——这降低了批 D 那条的紧迫性，但也说明
  旧收据留在原地会同时制造"读错"和"写不进"两种麻烦。

---

## 三、三项批 D 台账的定性意见

| 台账项 | 我的意见 |
|---|---|
| 政策拒绝时旧收据作废（F-D 后半） | **认可延后**，但建议排在批 D 前列。理由：F-F 新写的文档把"有没有落收据"当成分辨 exit 2 两种语义的**唯一线索**，而这条线索恰恰被旧收据污染；目前靠文档一句话提醒顶着。补充证据见上面 `publish_overwrite` 那条。 |
| `approved_tolerance_bps` 硬顶（F-E 后半） | **认可延后**，这是政策问题不是工程问题（谁有权批多大偏差、要不要二人复核），该由用户裁决。落地时请连 `observed_diff_bps` 的"预先虚报"一起管，只钳一个数没用。 |
| envelope inputs 相对路径根治（F-G 后半） | **认可延后**，但请把验收标准写清：不只是"案子能搬家"，还要"绑定的输入必须解析在案根内、且与其他四查收据同源"。否则改完相对路径，N-1 那扇门照样开着。 |

**有没有哪项其实必须现在修？** 三项本身都不必。
但**新 finding N-1 我建议本轮内补**——它直接架空本轮那道 P1 主修，
而修法只是给 `_bound_replay_totals` 加一次案根判定（`_bound_case_ref` 是现成的），
不依赖批 D 的相对路径改造。**N-2 的 Solana 半也建议现在修**，两行代码，
实物已经在同一个函数里读进内存了，属于典型的"顺手就能关、不关就一直开着"。

---

## 四、汇总

| finding | 判定 | 一句话 |
|---|---|---|
| F-A（P1） | **PARTIAL** | 我填的那条走法已堵；但"换一本账"（N-1）与"改 onchain"（N-2）两条同层旁路仍开着 |
| F-B | FIXED | 四个场景全转拒，双字段自洽，变异可证 |
| F-C | FIXED | 上轮 9 处漏网全部转红；夹具失真已修；残留一条无害的未覆盖分支 |
| F-D | FIXED（前半） | 两处通道故障统一 exit 1；后半按裁决入批 D，附新证据 |
| F-E | FIXED（前半） | observed_diff_bps 双侧强制＋证据独立性双侧强制，实测拦下 |
| F-F | FIXED | 用法与退出码语义已同步，文字合规；判别法依赖批 D 那半 |
| F-G | FIXED（前半） | 文案改到真根因；后半按裁决入批 D |

**新 finding：2 条，最高 P1**（N-1 绑案外伪造账本；N-2 onchain 未对账／Solana 侧实物在手未比）。
**全量 SUITE 复跑**：`python3 scripts/tests/run_all.py` → 退出码 0，末行"全部通过"，零 FAIL
（本机实跑，日志 `/private/tmp/batchA_probe/run_all2.log`；与修复前同一台机器的基线一致，
说明本轮六项半修复没有把任何既有绿例打红）。
**批 A 定向回归**：`test_repair_batch_a.py` 14/14 全绿（本机实跑，非引用工单）。

复核完成
