# 修复批 A · 对抗审查消化轮 1（fixround1）

处理对象：`maintenance/repair-20260813-sixlens/batchA_adversarial.md` 里的 7 条 finding。
基线 commit：`f575472`（批 A 入库版）。本轮**只改不提交**，未动版本号、未动契约快照。
审查者的探针脚本原地复用（`/private/tmp/batchA_probe/`），本轮新增两个补充探针，见文末。

裁判定的七项工作全部落地：F-A、F-B、F-E 前半、F-D 前半、F-F、F-G 前半、F-C。
**未做**（本轮明确不在范围内，留给后续批次）：
`approved_tolerance_bps` 硬顶（属政策问题，待用户裁决）、
政策拒绝时把上一轮旧收据显式作废（F-D 后半）、
envelope inputs 改记相对路径（F-G 彻底方案，批 D 候选）、
`tolerance-waiver/v1` 进契约快照（批 D 统一登记）。

---

## 一、每条 finding 改了什么（大白话）

### F-A（P1）消费侧不再只拿收据自报的数字互相印证

**原来的漏洞**：发布校验器判"供给对不对得上"时，用的是收据自己写的三个数
（重放净供给 `replay_net`、链上总量 `onchain_total_supply`、容差 `tolerance_bps`）。
这三个数互相自洽就算过。于是攻击者不用申请任何人工裁决收据，
只要把收据里的 `replay_net` 改成跟链上一样、容差填 0、结论改 PASS，就能过闸——
而磁盘上那份被哈希绑死、校验器手里正拿着的 `replay_stats.json` 明明写着完全不同的数。

**现在**：校验器多做一步"把手上的两份东西对一对"。
读收据 `inputs.replay_stats` 绑定的那个文件（上游 `validate_receipt` 已经对它做过
"存在＋大小＋sha256"三验，这里直接读内容），
用生产侧同一个 `parse_replay_stats` 解出 mint / burn，要求 `mint − burn` 恰好等于收据自报的
`replay_net`，对不上就拒。解不出来（旧格式、字段缺失、文件不是 JSON 对象）
一律 fail-closed，话术沿用"存量案例须重跑对应生产者获取当前回执"——
**不是"没法核对就放行"**，这一条专门用变异 N2 锁住了。

形态②（`sink_fallback_form2`）那条分支的两个标量 `mint_total` / `burn_total` 同样对账。
这条不是顺手加的：形态②原来的闭合检查是 `mint == 链上总量` 且 `两个 sink 合计 == burn`，
攻击者把 `mint_total` 和 `onchain_total_supply` **同步**抬高，闭合仍然成立、
`replay_net` 也还对得上，整份收据自洽——只有回头对一眼 `replay_stats` 实物才看得出 mint 是编的。
新测试 `test_fa_sink_fallback_scalars_bound_to_stats` 就是照这个路子构造的。

`onchain_total_supply` 消费侧确实无源可对，按审查者的定性不动：它是 RPC 观测、不是重放产物。

### F-B（P2）`model_probe_block` 有消费方了

**原来**：批 A 特意加了 `model_probe_block` 记录"探测实际发生在哪个块"，
但全库只有生产侧写、没有任何校验器读。结果只要把 `tip_block` 一个字段抬上去就能过时点闸，
唯一能暴露这次抬价的字段没人看——删掉它、填 0、填字符串，发布链一律放行。

**现在**：`validate_sources` 的 EVM 分支加三条——
`model_probe_block` 必须是非负整数（`isinstance(x, bool)` 单独排掉，防 `True` 冒充 1）、
必须**等于** `tip_block`（生产侧本来就把同一个 tip 写进两个字段，等于零成本）、
且 `as_of_block ≤ model_probe_block`。
想抬时点得同时改两个字段，plan_review 里"语义字段不一致要拒"这一条才算真落地。

检查顺序特意排在 tip 那两条之后：`as_of > tip` 的老场景仍然先报 `tip_block` 的错，
既有断言的报错关键词不会被新检查抢走。

### F-E 前半（P2）waiver 纸面上要有裁决人实际看到的偏差，证据不能自证

`tolerance-waiver/v1` 还没进契约快照（批 D 才登记），现在改 schema 零迁移成本，所以本轮就改：

1. **新增必填 `observed_diff_bps`**——裁决人签字时看到的本次实际偏差。
   生产侧算出本次 `diff_bps` 后要求 `diff_bps ≤ observed_diff_bps`，超了就拒
   （裁决人没见过这么大的偏差 ＝ 这张收据失效，须重新人工裁决）。消费侧照抄同一条。
2. **`evidence_refs` 不得指向 replay_stats 自身**——resolve 之后路径相等即拒。
   "人工核对证据"不能就是本次输入自己，否则等于自己给自己作证。生产、消费两侧都装。

**浮点边界处理**（工单点名要求的）：比较用的偏差值两侧都直接取 `decide()` 的返回值，
不各算一遍——生产侧用 `decide()` 那一行算出来的 `diff_bps`，
消费侧把原本丢掉的第三个返回值接住（`recomputed_verdict, _, recomputed_diff_bps = decide(...)`）。
同一份输入、同一个函数、同一套浮点运算，不会在边界上分叉。
`onchain == 0` 时 `decide` 不产生比值（判据退化成严格相等，waiver 在那里买不到任何放宽），
两侧统一按 `0.0` 处理，写在函数注释里。

`approved_tolerance_bps` 硬顶按审查者的定性属政策问题，本轮不设，留用户裁决。

### F-D 前半（P2）"文件读不动"统一归 exit 1

**原来**：waiver 本体读不动 → `except (OSError, json.JSONDecodeError)` 一锅端，
报"JSON 损坏"再升格成政策错误 exit 2（明明是权限错误）；
而 waiver 里 `evidence_refs` 指的文件读不动 → exit 1。同一类环境故障走两条码。

**现在**：
- `load_tolerance_waiver` 读 waiver 正文改成两段——`read_text()` 的 OSError 原样往外抛
  （由 `main` 的 `except Exception` 归 exit 1），只有 `json.JSONDecodeError` 才升格成
  `TolerancePolicyError`（exit 2）。
- `_waiver_file_ref` 里 `resolve(strict=True)` 的异常也拆开：`FileNotFoundError` ＝
  waiver 内容不合法（exit 2），其余 OSError（权限等）＝通道故障（exit 1）；
  `stat()` / `_sha256_file` 两处读盘改成先算到局部变量、写明"OSError 归 exit 1"，
  从"碰巧落在 exit 1"变成"明写在那里"，日后有人加 try 包一层会被变异 N10 抓住。
- 消费侧同类分支也拆开：读不动报"文件读取失败（通道故障，非政策问题）"，
  JSON 坏了才报 "JSON invalid"。消费侧没有 1/2 分流，这里修的是**话术准确性**。

**exit 2 一码多义**的问题按工单要求只做文档侧说明（见 F-F），代码语义不动。

### F-F（P2）用户能看到的文档补齐

- `scripts/lib/supply_truth_gate.py` 头注：补 `--tolerance-waiver` 一整段用法
  （写清楚 waiver 里必须有什么），`--tolerance-bps` 那行点明"正式模式上限就是 10"；
  退出码表把 exit 2 拆成两种语义（**落了收据＝FAIL／没落收据＝容差政策拒绝**），
  exit 1 补上"含文件读不动一类通道故障"。
- `references/analyze-workflow.md` §3 第 3 步那句 exit 语义同步改写，
  并补一句"确实需要放大容差的特殊币，唯一合法通道是 `--tolerance-waiver`"外加 waiver 必填项清单，
  以及一句提醒：政策拒绝不是 FAIL，别把上一轮留在原地的旧收据当本轮结果。
- 契约快照两份文件按工单要求**不动**。

### F-G 前半（P2）复制案的报错文案不再误导

`tolerance waiver input escapes case root` 会把人往"waiver 放错地方了"上引，
而 waiver 明明就在案根里，真正原因是收据里记的是老绝对路径。
文案改成：
> 收据记录的 tolerance waiver 路径不在当前案根内——存量案例须重跑对应生产者获取当前回执
> （存量案或整目录复制过的案子，收据里记的是老绝对路径，不是 waiver 放错了地方）

**逻辑一个字没改**，只换文案。彻底方案（inputs 改记相对路径）超出本轮，留批 D。

### F-C（P2）测试补齐

审查者用变异法测出：消费侧新增的 waiver 校验约 45 行里，删掉 8 处本批测试仍然全绿。
根因之一是既有反例的构造方式——反例改完 waiver 就直接送去校验，
拦下它的其实是**既有的** `receipt_validate` 掉包校验（`input tolerance_waiver size/hash mismatch`），
根本轮不到消费侧新校验出手。

本轮新增的 `consumer_case()` 帮手补上了关键一步：**改完 waiver 后把收据 `inputs` 里的
size/sha 重新绑到新实物上**，模拟"攻击者手里握着整个案目录"，
逼消费侧新校验自己拦。六个新测试函数（详见第三节）就建在这个帮手上。

---

## 二、diff-finding-map（每个改动 hunk 归属哪条 finding）

### `scripts/lib/supply_truth_gate.py`

| 位置（改后行号） | 改动 | finding |
|---|---|---|
| 24–29 | 头注补 `--tolerance-waiver` 用法段、`--tolerance-bps` 标明正式上限 | F-F |
| 37–41 | 退出码表：exit 2 拆两义、exit 1 补"文件读不动" | F-F |
| 99–116 | `_waiver_file_ref`：`FileNotFoundError` 与其余 OSError 拆开；size/sha 读盘写明归 exit 1 | F-D |
| 131–140 | `load_tolerance_waiver`：读 waiver 正文与 JSON 解析拆成两段 | F-D |
| 140 | 必填组加 `observed_diff_bps` | F-E |
| 153–157 | `observed_diff_bps` 类型/非负校验 | F-E |
| 182–187 | `evidence_refs` 逐项与 `replay_stats` 比路径，相同即拒 | F-E |
| 191–205 | 新函数 `assert_waiver_covers_diff()` | F-E |
| 328 | `main` 里新增 `waiver_doc = None` 初始化 | F-E |
| 359 | `load_tolerance_waiver` 的返回值接住 waiver 正文 | F-E |
| 426–432 | `decide()` 之后调 `assert_waiver_covers_diff`，不过则 exit 2 | F-E |

### `scripts/report/shared_release_receipt.py`

| 位置（改后行号） | 改动 | finding |
|---|---|---|
| 20–21 | import 补 `parse_replay_stats` | F-A |
| 136–158 | 新增 `MIGRATION_HINT` 常量与 `_bound_replay_totals()` 帮手（含解不出即 fail-closed） | F-A |
| 173 | `decide()` 第三个返回值接住（`recomputed_diff_bps`） | F-E |
| 177–186 | 用帮手取实物 mint/burn，断言 `mint − burn == replay_net` | F-A |
| 197–201 | waiver 越界的报错文案改写 | F-G |
| 203–209 | 读 waiver：OSError 与 JSONDecodeError 拆开报错 | F-D |
| 213 | 必填组加 `observed_diff_bps` | F-E |
| 225–234 | `observed_diff_bps` 类型校验＋实际偏差覆盖校验 | F-E |
| 258–263 | `evidence_refs` 逐项与 `waiver_replay` 比路径 | F-E |
| 364–368 | 形态②分支：`mint_total`/`burn_total` 对账 replay_stats 实物 | F-A |
| 447–455 | EVM 分支：`model_probe_block` 类型／等于 tip／`as_of ≤ probe` 三条 | F-B |

### `references/analyze-workflow.md`

| 位置 | 改动 | finding |
|---|---|---|
| 第 66 行 | exit 2 两义说明＋`--tolerance-waiver` 合法通道与必填项清单 | F-F |

### `scripts/tests/test_repair_batch_a.py`

| 位置 | 改动 | finding |
|---|---|---|
| `SinkPool` 类 | 形态②测试用的 RPC 假件（多一个 `call_many`） | F-A（测试） |
| `FIXTURE_DIFF_BPS` 常量、`write_waiver` 增 `observed` 形参与 `observed_diff_bps` 字段 | 夹具跟上新 schema | F-E（测试） |
| `supply_item()` / `expect_check_rejection()` / `consumer_case()` | 消费侧反例基础设施（含重绑 size/sha 这一步） | F-C |
| `test_fc_producer_waiver_field_level_negatives` | 生产侧 7 条字段级反例（含 M8/M9 漏网两条＋F-E 四条） | F-C / F-E |
| `test_fc_consumer_side_waiver_negatives` | 消费侧 12 条反例（M10–M18 全覆盖＋F-E 三条） | F-C / F-E |
| `test_fa_consumer_reconciles_replay_net_against_bound_stats` | 改 `replay_net` 绕闸＋旧格式 stats fail-closed | F-A |
| `test_fa_sink_fallback_scalars_bound_to_stats` | 形态②绿例仍绿＋同步抬高 mint/链上被拒 | F-A |
| `test_fb_model_probe_block_has_a_consumer` | 时点闸四场景 | F-B |
| `test_fd_unreadable_files_all_land_on_exit_1` | 两处权限故障退出码必须一致（root 下自动跳过） | F-D |
| `main()` 的 tests 列表 | 挂上以上 6 个新测试 | F-C |

### `scripts/tests/test_audit_release_gate.py`、`scripts/tests/test_handoff_manifest.py`

| 改动 | 为什么 |
|---|---|
| supply_truth 收据的 `inputs.replay_stats` 从"绑一份 raw_transfers / holders_owners 无关文件"改成绑一份真的重放统计（`fixture_replay_stats.json`，mint=100 / burn=0，与收据 `replay_net=100` 一致） | F-A 的对账要读这份实物。原夹具属**失真**：它声称某文件是 replay_stats，其内容根本不是。这是把夹具改成"像真的一样"，不是放松任何断言 |

**为什么文件名叫 `fixture_replay_stats.json` 而不是 `replay_stats.json`**：
`test_a4_gate.py` 那条链会真跑一遍 `replay_pass1`，在同一个案目录里写出正牌
`replay_stats.json`（1018 字节的真实重放回执），把 48 字节的夹具文件覆盖掉，
于是收据里记的 size 对不上，`input replay_stats size mismatch`。
本轮第一版就是这么撞的，改名避开即愈。

---

## 三、验收证据

### 3.1 批 A 专项测试

```
$ python3 scripts/tests/test_repair_batch_a.py
PASS test_f01_no_code_failure_receipt_keeps_tip
PASS test_f01_shared_evm_timing_and_legal_dual_time
PASS test_f01_solana_not_subject_to_tip_check
PASS test_f02_formal_cap_and_exploration
PASS test_f02_waiver_negatives_and_failures
PASS test_f02_valid_waiver_and_shared_recompute
PASS test_f02_waiver_swap_integrity_counterexample
PASS test_f02_tolerance_cap_uses_producer_constant
PASS test_fc_producer_waiver_field_level_negatives
PASS test_fc_consumer_side_waiver_negatives
PASS test_fa_consumer_reconciles_replay_net_against_bound_stats
PASS test_fa_sink_fallback_scalars_bound_to_stats
PASS test_fb_model_probe_block_has_a_consumer
PASS test_fd_unreadable_files_all_land_on_exit_1
PASS batch A F-01/F-02 regressions 14/14
退出码 0
```

### 3.2 全量 SUITE

```
$ python3 scripts/tests/run_all.py
…
全部通过
退出码 0
```
日志：`/private/tmp/batchA_probe/run_all_after.log`。

**干净基线对照**：为了排除"跑基线时我正在改文件"的干扰，本轮另用
`git archive HEAD | tar -x -C /private/tmp/batchA_baseline_repo` 拉了一份 `f575472` 的
原样副本单独跑，结果同样是"全部通过 / 退出码 0"
（`/private/tmp/batchA_probe/run_all_clean_baseline.log`）。
即：改前改后都全绿，不是"本来就有红的被我盖过去"。

### 3.3 变异抽查（工单点名的七处全部转红）

脚本：`/private/tmp/batchA_probe/exp_c3_mutation_fixround1.py`
（改造自审查者的 `exp_c_mutation.py` / `exp_c2_mutation.py`，
沿用同一套"只在内存里打断生产代码、磁盘不动"的方法；
`M4`/`M13` 因本轮改动重新对准了锚点，其余 M 系列锚点原样）。

工单点名的七处：

```
先跑未变异基线：全绿
M8  生产侧 waiver 不再校验 approved_by:            变红 ✅ FAIL test_fc_producer_waiver_field_level_negatives
M9  生产侧 waiver 不再校验 user_decided_at_utc:    变红 ✅ FAIL test_fc_producer_waiver_field_level_negatives
M10 消费侧不验 approved_by:                        变红 ✅ FAIL test_fc_consumer_side_waiver_negatives
M12 消费侧不验 waiver target 全等:                 变红 ✅ FAIL test_fc_consumer_side_waiver_negatives
M14 消费侧不验 waiver 的 replay_stats 绑定收据输入: 变红 ✅ FAIL test_fc_consumer_side_waiver_negatives
M16 消费侧不验 approved_tolerance_bps 上限:        变红 ✅ FAIL test_fc_consumer_side_waiver_negatives
M18 消费侧 waiver 必填字段整组不验:                变红 ✅ FAIL test_fc_consumer_side_waiver_negatives
```

顺带把整张表跑完，**29 处全红，零漏网**（原表 M1–M18 全部转红，
其中 M8–M18 这 9 处正是审查者标 ❌ 的那批）；本轮新代码另立 N1–N10 十处变异同样全红：

```
N1  F-A 消费侧不再拿 replay_net 对账 replay_stats 实物         变红 ✅
N2  F-A 解不出 mint/burn 时不再 fail-closed（当成 0 放行）      变红 ✅
N3  F-A 形态②不再拿 mint/burn 对账实物                        变红 ✅
N4  F-B 不验 model_probe_block 类型                            变红 ✅
N5  F-B 不验 model_probe_block == tip_block                    变红 ✅
N6  F-E 消费侧不验证据独立于 replay_stats                      变红 ✅
N7  F-E 消费侧不验实际偏差落在 observed_diff_bps 内            变红 ✅
N8  F-E 生产侧不再核对 observed_diff_bps                       变红 ✅
N9  F-E 生产侧不验 observed_diff_bps 字段本身                  变红 ✅
N10 F-D 生产侧把读文件 OSError 又并回 JSON 损坏（升格政策错）   变红 ✅
```
完整输出：`/private/tmp/batchA_probe/mutation_after.log`。

### 3.4 攻击场景转拒实测

**F-A**（`exp_a_replaynet.py`，攻击脚本一个字没改）：

```
[诚实跑 tolerance=10] exit=2 verdict=FAIL replay_net=1 onchain=100 diff_bps=9900.0
[绑定输入真值] replay_stats.json → mint=1 burn=0 净=1
[攻击结果] 被拒: ValueError: supply_truth replay_net 与绑定 replay_stats 实物的 mint−burn 不一致；存量案例须重跑对应生产者获取当前回执
[对照组 抬容差] 被拒: supply_truth formal tolerance above 10bps lacks tolerance waiver
```
（改前这一行是"共享发布校验器 放行"。）

**F-B**（`exp_b_probeblock.py`，四个场景改前全是"放行 ✅"）：

```
[单改 tip_block：as_of=101 tip=101 而探测其实发生在 100] 被拒 ⛔  EVM accounting model_probe_block must equal tip_block
[删除 model_probe_block]                                 被拒 ⛔  EVM accounting model_probe_block missing or invalid
[model_probe_block=0（与 tip=100 自相矛盾）]             被拒 ⛔  EVM accounting model_probe_block must equal tip_block
[model_probe_block='不是数字']                           被拒 ⛔  EVM accounting model_probe_block missing or invalid
```

**F-D**（`exp_d_exitcodes.py`，前两行改前是 exit=2 / exit=1 分叉）：

```
当前 uid=502（非 0 才能让 chmod 000 生效）
[waiver 权限不可读]   exit=1 收据=无 stderr=检测自身失败（exit 1，修通道重跑）: [Errno 13] Permission denied: '…/waiver.json'
[evidence 权限不可读] exit=1 收据=无 stderr=检测自身失败（exit 1，修通道重跑）: [Errno 13] Permission denied: '…/evidence.txt'
[超容差无 waiver 重跑] 第一次 exit=2 verdict=FAIL；第二次 exit=2；旧收据原地未动=True
```
第三行的"旧收据原地未动"是 F-D 后半（作废旧收据），本轮不在范围内，如实留红。

**F-E**（`exp_e2_waiver_strength_after.py`，本轮新写——
原 `exp_e_waiver_strength.py` 假定这条路径能跑通生产侧，修复后拿不到收据会直接崩，
所以按新语义重写同一组场景）：

```
[证据就是 replay_stats 自身（原审查者的攻击）] exit=2 无收据 正式容差政策拒绝（exit 2）: waiver evidence_refs[0] 不得指向本次 replay_stats 输入自身，人工核对证据必须是独立文件
[waiver 不记录实际偏差（旧 schema）]           exit=2 无收据 正式容差政策拒绝（exit 2）: tolerance waiver schema 或必填字段不完整
[裁决人只见过 9899bps，实际 9900bps]           exit=2 无收据 正式容差政策拒绝（exit 2）: 本次实际偏差 9900.0bps 超过 waiver 记录的 observed_diff_bps 9899.0bps——裁决人没见过这么大的偏差，该收据失效，须重新人工裁决
[绿例：偏差如实记 9900bps + 独立证据]          exit=0 PASS
[绿例 消费侧] 通过 ✅
```

**F-G**（`exp_f_copiedcase.py`，逻辑不变、只看文案）：

```
[复制到新路径后校验] 被拒: 收据记录的 tolerance waiver 路径不在当前案根内——存量案例须重跑对应生产者获取当前回执（存量案或整目录复制过的案子，收据里记的是老绝对路径，不是 waiver 放错了地方）
```

### 3.5 不许误伤：既有红线仍红、既有绿例仍绿

`exp_g_boundary.py` 六个"被拒"场景逐字对照改前，一条不少、报错原文一致：

```
[exploration 10000bps] exit=0 mode=exploration verdict=PASS          ← 绿例仍绿
[exploration 收据直送发布链]      被拒 ✅ supply_truth receipt must be formal and bind replay_stats input
[exploration 收据手改 mode=formal] 被拒 ✅ supply_truth receipt must be formal and bind replay_stats input
[formal 10bps 真实 9900bps 偏差]  exit=2 verdict=FAIL
[formal 10bps 的 FAIL 收据]       被拒 ✅ reconciliation supply_truth wrapper/receipt verdict mismatch
[waiver 绑案内 stats、实跑喂案外同内容 stats] exit=2 被拒 ✅ waiver replay_stats 未绑定本次实际输入
```

另外三个合法绿例：
完整 waiver 通过（`test_f02_valid_waiver_and_shared_recompute`）、
exploration 通过（`test_f02_formal_cap_and_exploration`）、
合法双时点通过（`test_f01_shared_evm_timing_and_legal_dual_time` 第三段，as_of=1 / tip=100）
——全部仍绿。形态②的诚实收据也专门留了绿例断言，防止 F-A 的新闸装成误伤。

**没有为了变绿放松任何既有断言。** 三处夹具改动都是把夹具改得更像真的
（把假的 replay_stats 换成真的、避开与真实产物撞名），不是降低要求。

---

## 四、改了哪些文件（范围自查）

`git diff --numstat`（增行 / 删行 / 文件）：

```
  1    1   references/analyze-workflow.md
 63   12   scripts/lib/supply_truth_gate.py
 79   13   scripts/report/shared_release_receipt.py
  9    1   scripts/tests/test_audit_release_gate.py
  8    1   scripts/tests/test_handoff_manifest.py
273    1   scripts/tests/test_repair_batch_a.py
```

工作区另有一个未跟踪文件 `maintenance/repair-20260813-sixlens/batchA_adversarial.md`
（审查者交上来的盲审报告，本轮的输入，非本轮产物）。

铁律逐条自查：

- `VERSION` / `SKILL.md` 版本行 / `pyproject.toml` version：**未动**（仍 6.39.5，`git diff` 对这三个文件零输出）
- `scripts/tests/contract_manifest.json`、`contract_ids_snapshot.json`：**未动**（同上）
- 批 B/C/D 生产文件（`holder_distribution_scan` / `state_from_facts` / `entity_source_trace` /
  `fetch_hypersync_v2` 等）：**未动**
- `git commit`：**未做**（工作区保持已改未提交）
- 约定范围外文件：**零**

## 五、本轮新增/改造的探针脚本（都在 `/private/tmp/batchA_probe/`，非仓库文件）

| 脚本 | 用途 |
|---|---|
| `exp_c3_mutation_fixround1.py` | M4/M10–M18 重放（锚点重对）＋ 新代码 N1–N10 变异 |
| `exp_e2_waiver_strength_after.py` | F-E 两条新约束的红绿对照（替代崩掉的 `exp_e_waiver_strength.py`） |

`exp_a` / `exp_b` / `exp_d` / `exp_f` / `exp_g` 原样复用，一个字没改。

修复轮完成
