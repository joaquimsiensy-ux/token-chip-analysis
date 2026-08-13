# 修复批 A 消化循环第 2 轮 —— 终复核（盲审第三轮）

复核对象：commit `8b089c3`（基线 `78d1c4c`）。
复核人：与施工方不同线程的对抗审查者，只读代码、只跑测试，未改任何生产文件。
方法：重放上一轮两条 P1 攻击脚本（不采信工单自报）＋对新增的两处校验另起一轮①②攻击
（`exp_l`/`exp_m`/`exp_n`）＋独立评估 P1-05 撞墙裁决（用"去掉夹具重绑"反证）。

**结论：上一轮 2 项未闭合全部 FIXED；实质新 finding 零；撞墙裁决认可。**

---

## 一、终判

### F-A（P1，上一轮 PARTIAL）→ **FIXED**

上一轮判 PARTIAL 的两条理由现在各有交代：

| 上轮缺口 | 现状 | 实测 |
|---|---|---|
| N-1 换一本账（绑案外伪造账本） | 关闭 | `exp_h` 转拒 |
| N-2 改 onchain（Solana 半） | 关闭 | `exp_i2` 转拒 |
| N-2 改 onchain（EVM 半） | 按裁决入批 D＋写入明示局限 | 仍可放行，但已在协议文档写死"不得默认为已闭合" |

EVM 那半我上一轮给的验收口径原话是"要么补观测件、要么写成明示局限，两条路都行，
但不能默认现状＝已闭合"。施工方走了第二条：`references/independent-audit-protocol.md`
新增段落，把"哪三个数对过账、唯独 EVM 的链上供给没有第二份实物"讲清楚了，
并点名 `accounting_gate` 记的是 tip 与 tip−W、`verify_recon` 的 `nominal_supply_raw`
来自 config 人工声明——这两条与我实测的事实一致，没有粉饰。按我自己给的口径，**F-A 终判 FIXED**。

### N-1（P1）→ **FIXED**

```bash
python3 /private/tmp/batchA_probe/exp_h_round2.py     # 原样重放，未改脚本
```

```text
    案根里真实 replay_stats：{'mint_total_raw': '1', 'burn_total_raw': '0'}
    收据改绑的案外文件：/private/tmp/expH1-outside-…/replay_stats.json   （内容 mint=100）
[N-1 绑案外伪造账本] 被拒 ✅ 收据绑定的 replay_stats 实物不在当前案根内——存量案例须重跑对应生产者获取当前回执…
```

绕路也堵住（`exp_l`）：案内软链指向案外 → 被拒（`path is a symlink`，如实说这条是**上游既有**
`receipt_validate` 拦的，新测试的注释也这么写，没有冒功）；`..` 路径穿越 → 被拒
（`path contains traversal`，同为既有防线）。

**不误伤合法布局**（`exp_m`，这是加约束最该验的一面）：

```text
[案根平铺 stats]        生产 exit=0 verdict=PASS → 消费侧放行 ✅ 未误伤
[案根 data/ 子目录 stats] 生产 exit=0 verdict=PASS → 消费侧放行 ✅ 未误伤
[案外 stats]            生产 exit=0（生产侧不拦）→ 消费侧被拒，话术指向"对账实物必须与收据同案"
```

受控 runner 以 `cwd=案根` 启动生产者、文档也一律用相对文件名，所以线上跑法全在案根内；
子目录布局同样放行，没有把 `data/` 这类常见摆法误杀。

### N-2（P1）→ **Solana 半 FIXED；EVM 半按裁决闭合（我认可）**

```bash
python3 /private/tmp/batchA_probe/exp_i2_solana_onchain.py   # 原样重放
```

```text
[诚实跑] exit=2 verdict=FAIL replay_net=1000 onchain=100 （bundle 实物 supply.amount=100）
[伪造后] 收据自报 onchain=1000，同案 bundle 实物仍写着 100
[结果] 被拒 ✅ solana supply_truth onchain_total_supply is not bound to bundle supply amount
```

整数比对（不是字符串比对）是对的：bundle 里 amount 存的是字符串，
`int(str(...))` 两边归一，不会因为"100"与"0100"这类写法差异造成假红。

### 三项批 D 台账（上一轮已认可延后）——本轮状态确认

旧收据作废、`approved_tolerance_bps` 硬顶、inputs 相对路径根治，本轮均未动，符合裁决；
`exp_h` 里 N-4（天价 waiver 仍放行）与 `exp_d` 第三行（政策拒绝后旧收据原地未动）
重放结果与上一轮一致，说明这三项确实是"记账未修"而不是被悄悄改动过。台账现 5 项。

---

## 二、撞墙裁决独立评估（test_a4_gate P1-05）——**认可，不构成"为绿改弱"**

我没有只读工单，而是把夹具里那一行重绑**去掉**再跑一遍 a4_gate，看它红在哪：

```bash
# 内存里把 rebind_case_inputs(d, new_d) 换成 pass，磁盘不动
FAIL  P1-05 全新分析无净室资产仍过必经共享门禁
[WARN] audit release gate: 共享发布 receipt: 收据绑定的 replay_stats 实物不在当前案根内——…
[FAIL] 未写出 …/case_new/new.html——1 条告警，修复后重跑
```

四条判据：

1. **断言主题没变**：`check("P1-05 全新分析无净室资产仍过必经共享门禁", p.returncode == 0
   and p_build.returncode == 0 and os.path.isfile(new_out))` 这行一字未动，
   diff 里只多了一行夹具调用，没有改判据、没有放宽期望。
2. **门禁仍在必经路径上，用例不是空跑**：去掉重绑后 23 项里**只红这一项**，
   且红的原因**只有案根约束这一条**——说明共享发布校验器确实被 P1-05 走到，
   其余全部校验（四查收据、实物对账、容差政策、双时点）也都还在跑。
3. **重绑是等效重跑，不是伪造**：`copytree` 出来的文件逐字节相同，
   `rebind_case_inputs` 只把收据里记的绝对路径前缀搬家、再重算随之改变的收据哈希与
   wrapper/shared 的登记哈希——生产者在新目录重跑会得到同样内容（收据里除输入绝对路径外
   没有任何字段依赖案目录位置）。它没有编造观测、没有跳过任何校验。
4. **裁决前提我复核过**：
   - 全库零生产路径复制案目录——`rg copytree|cp -r|cp -a|rsync scripts/ references/ SKILL.md`
     的命中全部是 "hypersync" 里含 "rsync" 的假阳性，没有一处真的复制案目录；
   - 同款案根约束**不是本轮新造的口径**：Solana observation bundle 的
     `bundle_path.relative_to(root)` 在**批 A 之前的基线 `2ebd885` 就已存在两处**
     （`git show 2ebd885:scripts/report/shared_release_receipt.py` 第 212／285 行），
     tolerance waiver 也从批 A 首版起就这么要求；
   - 复制案在 N-1 之前**本来就发不了版**：我轮 1 的 `exp_f` 实测过——原案一删，
     上游 envelope 校验就以"input replay_stats invalid: No such file"拦死。
   所以 N-1 没有新造出一类不兼容，只是把既有口径推广到 replay_stats，而 P1-05 那份
   复制案夹具本来就是踩在"非合法发布场景"上，撞墙属于夹具与现实口径的历史欠账。

一句提醒（不是 finding）：`rebind_case_inputs` 本质是"手工改收据再重算哈希"，
这正是 `independent-audit-protocol.md` 禁止在生产上做的事。它现在只活在测试文件里、
docstring 也写明是模拟重跑，没问题；但**不要把它搬进任何 ops/生产脚本**，
搬过去就是一把现成的伪造工具。建议后续谁看到它被 import 到 `scripts/` 下要当场拦。

---

## 三、对新增代码的①②攻击结果

### 视角①（字段来源／循环信任）

- 案根约束的判据来自**校验器自己算的案根**（`Path(root).resolve()`）与
  **收据自报的路径**之比，判的是"你指的这个位置在不在我管的地界内"——
  不存在拿自报值当观测值的问题。
- Solana amount 比对的两边：一边是收据自报，一边是**同案哈希绑定的 bundle 实物**，
  且该 bundle 本身还要过 `validate_observation_bundle`（内含 gpa/mint_raw/token_supply
  三方金额全等校验，`solana_observation.py:571`）。不是自己报自己验。

### 视角②（失败分支）

| 攻击 | 结果 |
|---|---|
| 案内软链 → 案外伪造账本 | 被拒（既有 symlink 闸） |
| `案根/../案外/fake.json` 路径穿越 | 被拒（既有 traversal 闸） |
| 案外伪造账本 | 被拒（本轮新约束） |
| 旧格式 stats 解不出 mint/burn | 被拒（fail-closed，带存量案重跑话术） |
| 绑定实物被删 | 被拒（上游 envelope 先拦） |
| Solana bundle amount 与收据不符 | 被拒（本轮新比对） |
| 案根内／案根 data/ 子目录的诚实 stats | 放行（零误伤） |

### 变异法（新代码是否真被测试锁住）

```bash
python3 /private/tmp/batchA_probe/exp_n_mutation3.py
```

```text
P1  案根约束整段删掉:              变红 ✅ FAIL test_n1_replay_stats_must_live_inside_case_root
P1' 案根约束改成恒真（只废判据）:  变红 ✅ FAIL test_n1_…
P2  Solana amount 比对删掉:        变红 ✅ FAIL test_n2_solana_onchain_bound_to_bundle_amount
P3  Solana amount 解析失败改放行:  仍然全绿 ❌（见下，判为不可达防御分支）
R1  轮 1 replay_net 实物对账:      变红 ✅（防线未回退）
R2  model_probe == tip:            变红 ✅
R3  observed_diff_bps 覆盖检查:    变红 ✅
```

`test_repair_batch_a` 17/17、`test_a4_gate` 23/23 本机实跑全绿。
施工方自查出的"Solana 测试假绿（按路径重载模块导致变异探针够不着）"确已修正——
我的探针注入 `sys.modules`，P2 能把 `test_n2_…` 打红，证明这条测试真的咬着新代码。

---

## 四、未列为 finding 的观察（附判据，供裁判覆核）

我这三轮一直用同一条判据立 finding：**校验器手里已经握着能拆穿它的实物，却不去比对**
（F-A 的 replay_stats、N-1 的案根可见性、N-2 的 bundle amount 都是这一类）。
下面三条实测过、但按这条判据都不成立，所以不立 finding：

1. **伪造账本改放案根内、另起文件名，仍可放行**（`exp_l` C 组实测：案根里真账本
   `mint=1` 原封不动，另放一份 `replay_stats_v2.json` 写 `mint=100` 并改绑，消费侧放行）。
   不立的理由：①它要求伪造件**进案目录**，正是 N-1 想要的性质，也是协议文档明示的
   "主动造假"band 内（"必须显式填哈希、编造观测"）；②EVM 上攻击者有更便宜的既有通道
   （改 onchain，一个字段、零文件，已裁决入批 D 并写明局限），关掉它不改变最短路径；
   ③Solana 上没有第二份收据绑 replay_stats，**校验器手里没有可对而不对的实物**，
   不符合我的立案判据。
   **建议**：把我轮 1 提过的第二条修法（supply_truth 绑的 stats 必须与 balance/supply
   两查收据绑的是同一份）并进批 D 那条"EVM 链上观测件"一起做——两条一起做才有净收益。
   顺带更正我轮 2 报告里的一句话：`check_manifest` 只校验**清单里列了的**文件，
   并不强制案内每个文件都进清单，所以那份伪造件的可见性是"在案目录里、人能看见、
   会被打包交接"，不是"必然出现在 manifest 清单里"——这点我上轮说过头了。
2. **P3 那条解析分支没测试覆盖**：`bundle["supply"]["amount"]` 非整数时才会走到，
   而 `validate_observation_bundle` 在更早一步就要求三方金额字符串全等且可 int 化，
   所以这是不可达的防御性分支，删了也不开洞（删掉后两边归零反而放行，但构造不出触发它的合法 bundle）。
3. **案外 stats 的失败点偏晚**：生产侧照常 exit 0 PASS，要到发布聚合时才拒。
   文档与受控 runner 的跑法都在案根内，属于非路径上的用法，且 fail-closed、话术清楚，
   不构成实质缺陷；真要打磨可在生产侧加一句提醒，属工艺不属缺陷。

---

## 五、汇总

| 项 | 终判 |
|---|---|
| F-A（P1，上轮 PARTIAL） | **FIXED**（EVM 自报边界按我给的第二条口径以明示局限闭合） |
| N-1（P1） | **FIXED**（攻击转拒＋绕路两条由既有闸兜住＋零误伤＋变异双变体全红） |
| N-2（P1） | **Solana 半 FIXED**；EVM 半按裁决入批 D＋协议写入明示局限，**认可** |
| 三项批 D 台账 | 状态未变，符合裁决 |
| P1-05 撞墙裁决 | **认可**：断言主题未变、门禁仍必经、重绑等效重跑、裁决三条前提我逐条复核成立 |

**实质新 finding：零。**
**全量 SUITE**：本机 `python3 scripts/tests/run_all.py` → 退出码 0，92 项全 PASS、零 FAIL
（日志 `/private/tmp/batchA_probe/run_all3.log`）；`test_repair_batch_a` 17/17、
`test_a4_gate` 23/23，均为本机实跑而非引用工单。三轮下来同一台机器同一条基线，
本批六项半＋两条 P1 修复没有打红任何既有绿例。

终复核完成
