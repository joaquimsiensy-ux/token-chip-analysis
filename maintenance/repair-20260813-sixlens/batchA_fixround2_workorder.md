# 修复批 A · 对抗复核消化轮 2（fixround2）

处理对象：`maintenance/repair-20260813-sixlens/batchA_adversarial_recheck.md` 新抓的 2 条 P1。
基线 commit：`78d1c4c`（轮 1 入库版）。本轮**只改不提交**，未动版本号、未动契约快照。

裁判定的四项全部落地：N-1 案根约束、N-2 Solana 实物比对、N-2 EVM 明示局限入档、测试锁定。

> ⚠️ **N-1 撞墙了，处置见第二节，请裁判过目。** 撞的是 `test_a4_gate` 的 P1-05
> ——那条链用 `shutil.copytree` 复制案目录。我**没有撤约束**，改的是复制案夹具，
> 理由和证据在下面，若裁判判定复制案发布属合法场景，需要回头重议 N-1。

---

## 一、两条 P1 改了什么（大白话）

### N-1（P1）实物对账的账本必须落在案根内

**原来的漏洞**：轮 1 装的实物对账，读的是"收据自己指的那个文件"。
上游 `validate_receipt` 只管"这个路径上的文件与收据登记的 size/sha 一致"，**不管它在哪**。
于是伪造者不用改收据里任何一个数，改成**绑另一本账**就行——那本账可以躺在案外任何地方，
案根里真正的账本原封不动、没人再看它一眼。

这条比一般伪造更该堵，因为伪造件**不需要进案目录**：
不会出现在 `audit_input_manifest.json` 的文件清单里、人工翻案子时看不见、
也不会和 balance/supply 两查收据绑定的同一份 stats 撞哈希——
它绕过的恰恰是本仓"内容绑定"防线的**全部可见性**。
强制在案根内之后，伪造者只能覆盖案里那份真账本，那会立刻把
balance/supply 两查收据的输入哈希打炸，一望即知。

**现在**：`_bound_replay_totals` 多收一个 `root` 参数，读文件前先判
`replay_path.relative_to(Path(root).resolve())`，落在案根外一律 fail-closed。
`resolve()` 已经跟完符号链接，所以"案内软链指向案外"也会被这一步拦下
（实测里这一条其实由**上游既有**的 `receipt_validate`"path is a symlink"先响，
新测试如实记成上游功劳，没往自己脸上贴金）。

裁判给的第二条建议（"必须与 balance/supply 两查收据绑同一份 stats"）
**本轮未做**——工单只点名了案根约束这一条，多一分不做。留作候选。

### N-2 Solana 半（P1）链上供给对回 bundle 实物

**原来**：`validate_reconciliation_check` 的 Solana 分支**已经把 observation bundle
读进内存**、拿它比过两处 slot，偏偏没把 `bundle.supply.amount` 和收据自报的
`onchain_total_supply` 比一比。病因和 F-A 一模一样：**手里握着实物，就是不对账**。
于是把 `onchain_total_supply` 改到与重放净供给相等，`decide()` 重算自洽、
容差 0bps 不用办 waiver，一个字段、一次编辑，FAIL 变 PASS。

**现在**：在既有 bundle 校验那段后面加整数比对，不符即拒。
两个数都先 `int(str(...))` 归一（bundle 里存的是十进制字符串），
转不成整数也 fail-closed 并带存量案重跑话术。

### N-2 EVM 半：代码不动，写成明示局限

EVM 侧案内确实没有第二份冻结块 totalSupply 实物可对：
`accounting_gate` 记的是 tip 与 tip−W 两点、不是冻结块；
`verify_recon` 的 `nominal_supply_raw` 来自 config 人工声明、不是链上观测。
按工单，代码不动，改为在 `references/independent-audit-protocol.md`
聚合器验证边界那段（"主动造假"那句之后）补一段明示局限，讲清楚：

> supply_truth 三个数里，`replay_net`（以及形态②的 `mint_total`/`burn_total`）都会和案内
> `replay_stats` 实物逐一对账，Solana 的 `onchain_total_supply` 也会和同案 bundle 的
> `supply.amount` 对账；**唯独 EVM 的 `onchain_total_supply` 是 RPC 现场观测的自报值，
> 案内没有第二份冻结块 totalSupply 实物可以交叉**，只能靠复跑生产者与 git 历史追责，
> 读者不要误以为消费侧四个数都对过账了。

要闭合它得让 supply_truth 额外落一份可绑定的链上观测件（像 Solana 的 bundle 那样），
已并入下面的批 D 台账。

---

## 二、⚠️ N-1 撞墙场景（请裁判过目）

### 撞的是什么

```
$ python3 scripts/tests/test_a4_gate.py     # 加上 N-1 约束、未动夹具时
FAIL  P1-05 全新分析无净室资产仍过必经共享门禁
[WARN] audit release gate: 共享发布 receipt: 收据绑定的 replay_stats 实物不在当前案根内——…
[FAIL] 未写出 …/case_new/new.html——1 条告警，修复后重跑（有 WARN 不许交付）
```

`test_a4_gate.py:254` 用 `shutil.copytree(d, new_d)` 复制出第二个案目录当"全新分析案"，
但复制出来的案子里，四查收据 `inputs` 记的还是**老案根**的绝对路径。
文件本身逐字节存在（copytree 不删源），所以 size/sha 三验一路放行，
只有新加的案根约束会拦——这正是 N-1 要拦的形状，只是这次是自己人。

### 我的处置：保约束，修夹具

在 `test_a4_gate.py` 加了 `rebind_case_inputs(old_root, new_root)`：
copytree 之后把复制案的收据输入重新指到它自己那份拷贝上，
并顺带刷新 `reconciliation_report.json` 里的收据 sha 与 `shared_release_receipt.json`
里的 wrapper sha。文件是逐字节拷贝，**size/sha 都不变，只有路径要搬家**——
这正是"重跑生产者"会得到的结果。

### 判定依据（为什么我认为这不是"合法场景被误伤"）

1. **全仓只有这一处复制案目录，且是测试夹具**：
   `rg "copytree|shutil.copy" scripts/ --glob '*.py'` 全库只有 `test_a4_gate.py:254`
   一处复制案目录，**零条生产路径**。生产链里 `reconciliation_report.py` 受控 runner
   在案目录里跑生产者，记下的绝对路径本来就在案根内。
2. **同一个校验函数早就拒绝复制案，只是拒别的输入**：
   Solana 的 observation bundle 走 `bundle_path.relative_to(root)`（**既有代码，非本轮**），
   复制案在 Solana 上一直过不了；tolerance waiver 走同一逻辑（F-G，轮 1 已入库并被复核判 FIXED）。
   P1-05 今天能过，只是因为它是 EVM 且没有 waiver——是**覆盖面的偶然**，不是设计保证。
3. **仓内对复制案的既定处置就是"重跑生产者"**：
   F-G 的报错文案（轮 1 写、复核判 FIXED）原话是"存量案或整目录复制过的案子…须重跑生产者"。
4. **P1-05 断言的主题没被动过**：它测的是"没有净室资产的全新分析仍须过共享门禁"，
   copytree 只是搭台用的脚手架。修完夹具，这条断言测的还是同一件事。

### 如果裁判判定复制案发布属合法场景

回退方式：删掉 `test_a4_gate.py` 第 289 行那一句 `rebind_case_inputs(d, new_d)` 调用
（函数定义留着不碍事），测试立刻复现撞墙；随后需要重议 N-1 的落地形态
（可选路线：只对"案外且不在 audit_input_manifest 清单里"的实物拒，
或按裁判建议的第二条改走"与 balance/supply 同源"判据）。
**我没有改动 N-1 的约束本体**，代码里那段案根判定原样在位。

---

## 三、diff-finding-map

### `scripts/report/shared_release_receipt.py`（+29 / −3）

| 位置（改后行号） | 改动 | finding |
|---|---|---|
| 139 | `_bound_replay_totals` 签名加 `root` | N-1 |
| 145–150 | 函数注释补"为什么必须在案根内"（可见性论证＋软链说明） | N-1 |
| 157–163 | `relative_to` 案根判定＋失败话术（沿用存量案重跑口径） | N-1 |
| 193 | `_validate_tolerance_policy` 里的调用改传 `root` | N-1 |
| 365 | 形态②分支里的调用改传 `root` | N-1 |
| 389–399 | Solana 分支：`bundle.supply.amount` 与 `onchain_total_supply` 整数比对 | N-2(Solana) |

### `references/independent-audit-protocol.md`（+1 / −0）

| 位置 | 改动 | finding |
|---|---|---|
| 第 154 行段末 | 补 EVM `onchain_total_supply` 无案内实物可交叉的明示局限 | N-2(EVM) |

### `scripts/tests/test_a4_gate.py`（+36 / −1）

| 位置 | 改动 | 归属 |
|---|---|---|
| import 行 | 从 `test_audit_release_gate` 多引入 `sha` | 夹具 |
| `rebind_case_inputs()` 新函数 | 复制案的收据输入重新指向自己那份拷贝 | N-1 撞墙处置（见第二节） |
| copytree 之后一行调用 | 同上 | 同上 |

### `scripts/tests/test_repair_batch_a.py`（+115 / −0）

| 新增 | 内容 | finding |
|---|---|---|
| `test_n1_replay_stats_must_live_inside_case_root` | ①绑案外伪造账本（内容自洽、sha/size 对得上）→ 拒；②案内软链指向案外 → 拒（如实记成上游 `receipt_validate` 先响） | N-1 |
| `_solana_case()` 帮手 | 跑一遍真实 Solana 生产链，可指定重放净供给 | N-2 |
| `test_n2_solana_onchain_bound_to_bundle_amount` | 真实 FAIL 局面（重放净 1000 / bundle 实物 100）后只抬 onchain → 拒 | N-2 |
| `test_n2_solana_honest_receipt_still_passes` | 绿例：诚实 Solana 收据仍放行，防新闸误伤 | N-2 |
| `main()` tests 列表 | 挂上以上三个 | — |

**一处施工返工值得记下**：这两个 Solana 测试第一版用了 `test_r9_batch3_release_guards.shared_module()`，
它按**路径重新 load** 模块，变异探针注入 `sys.modules` 的打断版本够不着它——
于是 P2/P3 两处变异"删掉校验测试仍全绿"，正是 F-C 骂过的"看着有测其实没测"。
改用模块级 `shared` 后两处立刻转红。**这条只有跑变异才抓得到，跑测试全绿看不出来。**

---

## 四、验收证据

### 4.1 批 A 专项测试

```
$ python3 scripts/tests/test_repair_batch_a.py
… （轮 1 的 14 项全绿，略）
PASS test_n1_replay_stats_must_live_inside_case_root
PASS test_n2_solana_onchain_bound_to_bundle_amount
PASS test_n2_solana_honest_receipt_still_passes
PASS batch A F-01/F-02 regressions 17/17
退出码 0
```

### 4.2 全量 SUITE

```
$ python3 scripts/tests/run_all.py
全部通过
退出码 0        （FAIL(rc=) 计数 0）
```
日志：`/private/tmp/batchA_probe/run_all_round2.log`。
`test_a4_gate.py` 单跑亦全绿（23 项），即工单点名要求的那条链。

### 4.3 两条 P1 攻击转拒

**N-1**（`exp_h_round2.py`，攻击脚本一个字没改）：

```
    案根里真实 replay_stats：{'mint_total_raw': '1', 'burn_total_raw': '0'}
    收据改绑的案外文件：/private/tmp/expH1-outside-…/replay_stats.json
[N-1 绑案外伪造账本] 被拒 ✅ 收据绑定的 replay_stats 实物不在当前案根内——存量案例须重跑对应生产者获取当前回执（对账实物必须与收据同案；存量案或整目录复制过的案子，收据里记的是老绝对路径）
```
（改前这一行是"放行 ❗"。）

**N-2 Solana**（`exp_i2_solana_onchain.py`，同样未改）：

```
[诚实跑] exit=2 verdict=FAIL replay_net=1000 onchain=100 （bundle 实物 supply.amount=100）
[伪造后] 收据自报 onchain=1000，同案 bundle 实物仍写着 100（消费侧已把 bundle 读进内存比 slot）
[结果] 被拒 ✅ solana supply_truth onchain_total_supply is not bound to bundle supply amount
```
（改前是"放行 ❗ —— onchain 与 bundle 实物没有对账"。）

**N-2 EVM**（`exp_h_round2.py` N-2 段）仍然放行 —— **按工单这是有意保留的已声明边界**，
已写进 `independent-audit-protocol.md`，并入批 D 台账。

### 4.4 变异抽查

脚本：`/private/tmp/batchA_probe/exp_l_mutation_fixround2.py`。

```
先跑未变异基线：全绿
P1  N-1 删掉 replay_stats 案根约束:                    变红 ✅ FAIL test_n1_replay_stats_must_live_inside_case_root
P2  N-2 删掉 Solana onchain 对账 bundle 实物:          变红 ✅ FAIL test_n2_solana_onchain_bound_to_bundle_amount
P3  N-2 把 Solana 对账改成恒真（防装了等于没装）:      变红 ✅ FAIL test_n2_solana_onchain_bound_to_bundle_amount
R1  轮1 F-A 主对账（replay_net vs 实物）:              变红 ✅
R2  轮1 F-B model_probe_block == tip_block:            变红 ✅
R3  轮1 F-A 形态②标量对账:                            变红 ✅
```
P1/P2 是工单要求的"各做一处删掉转绿"；P3 是边界外一步（不删、只改成恒真），
防的是"装了等于没装"；R1–R3 确认本轮改动没把轮 1 的防线打掉。
完整输出：`/private/tmp/batchA_probe/mutation_round2.log`。

### 4.5 零误伤

`exp_g_boundary.py` 六个"被拒"逐字对照，一条不少、报错原文一致；
exploration 绿例、合法 waiver 绿例、合法双时点绿例、诚实形态②绿例、
**新加的诚实 Solana 绿例**全部仍绿。
轮 1 的 `exp_a`／`exp_b`／`exp_d`／`exp_f` 全部重放，行为不变。

一处**报错换岗**（同样是被拒，只是换了更早的闸先响，如实记录）：
`exp_f_copiedcase.py` 的"复制到新路径后校验"，轮 1 报的是 tolerance waiver 越界，
现在报的是 replay_stats 不在案根内——同一个复制案，被更靠前的 N-1 约束先拦下，
两条话术给的都是"须重跑生产者"，处置指引一致。

**没有为了变绿放松任何既有断言。**

---

## 五、改了哪些文件（范围自查）

`git diff --numstat`（增行 / 删行 / 文件）：

```
  1    0   references/independent-audit-protocol.md
 29    3   scripts/report/shared_release_receipt.py
 36    1   scripts/tests/test_a4_gate.py
115    0   scripts/tests/test_repair_batch_a.py
```

铁律逐条自查：

- `VERSION` / `SKILL.md` 版本行 / `pyproject.toml` version：**未动**（`git diff` 零输出）
- `scripts/tests/contract_manifest.json`、`contract_ids_snapshot.json`：**未动**（同上）
- 批 B/C/D 生产文件：**未动**
- `git commit`：**未做**（HEAD 仍 `78d1c4c`）
- 约定范围外文件：**零**（`scripts/lib/supply_truth_gate.py` 本轮一个字没改）

未跟踪文件：`batchA_adversarial_recheck.md`（复核者交上来的输入）与本工单。

---

## 六、批 D 台账（本轮更新）

| 台账项 | 状态 |
|---|---|
| 政策拒绝时旧收据作废（F-D 后半） | 待批 D；复核者建议排前列，并补了 `publish_overwrite` 拒绝降级覆盖的新证据 |
| `approved_tolerance_bps` 硬顶（F-E 后半） | 待用户裁决；落地时须连 `observed_diff_bps` 的"预先虚报"一起管 |
| envelope inputs 相对路径根治（F-G 后半） | 待批 D；验收标准须写明"解析在案根内且与其他四查收据同源"，否则 N-1 那扇门照样开着 |
| **EVM `onchain_total_supply` 无案内实物可交叉（N-2 EVM 半）** | **本轮新增**：已写成明示局限入 `independent-audit-protocol.md`；根治方案＝让 supply_truth 额外落一份可绑定的链上观测件（对标 Solana bundle），可与相对路径根治一并设计锚定方案 |
| supply_truth 的 stats 须与 balance/supply 两查收据同源 | **本轮新增候选**：复核者对 N-1 的第二条建议，本轮未做（工单只点名案根约束） |

修复轮2完成
