# 修复批 B 工单（F-03＋F-08）

基线：`main@e1bd7dd`（v6.39.5，批 A 已收口）。本批只处理分布扫描族的 F-03、F-08；未提交 git。

## 五栏工单

### ① 不变量

#### F-03 第一层：owner 快照必须对冻结 total supply 双向闭合

- 快照里所有 owner 余额加起来，必须约等于 `supply_truth.json` 的 `total_supply_raw`。
  **两个方向都拦**：多出来拦，少了同样拦。旧版只拦"多出来"，等于放行"只装了 1% 的残缺快照"——
  99% 的持仓连同头部集中度、鼓包、未识别合约桶被整段藏掉，且 final scan 会沿用同一份快照，
  一路污染到最终报告。
- **闭合分母是 `total` 不是 `net`。** 五桶分区物理上包含 `burn_sentinel`，dead 地址本来就在快照里；
  按 `net` 闭合会把 mint 100／burn 20 这种合法 dead-sink 案当成"少了 20%"误杀。`net` 只用来算
  分布百分比（`bucket_coverage`、经济门、head top-k 都用它），不参与闭合。
- 公式 `|Σ余额 − total| × 10000 ≤ total × 10`，**整数交叉乘法**。18 位面额下 `total` 动辄 10²⁴ 量级，
  先算 `total * 10 / 10000` 再比会引入浮点误差；交叉乘法全程走 Python 大整数，逐 wei 精确。
- **容差 `SNAPSHOT_CLOSURE_TOLERANCE_BPS = 10` 独立写死在本脚本，不读 supply_truth 收据里的
  `tolerance_bps`。** 这是刻意设计：批 A 的 F-02 给供给真值容差装了 waiver 出口，
  如果本闸复用同一个数，用户一批准供给真值放宽到 10000bps，快照闭合闸会跟着一起被松掉。
  两个不变量两把旋钮，谁也别连带谁。
- 实现是 `raise` 式检查，**零新增输出字段、`semantic_payload` 零改动**——不给 A5 终态案重验加新的
  比对面。（脚本本体改动会改 `input_binding.algorithm.sha256`，这是分布闸自诞生起就有的算法绑定
  语义，任何一次修 bug 都会让旧 scan 需要重跑，与本批设计无关。）

#### F-03 第二层：分布快照必须就是四查真正核过的那一份

- `data_map.json` 只能证明"这份文件被登记过"，登记两份就绕过去了。真正堵住**同值换仓**
  （另存一份总和一样、owner 分配是编的快照）只能靠哈希等值：
  - **EVM**：`distribution_scan.input_binding.snapshot.sha256` == 四查 `balance` 收据的
    `inputs.balances.sha256`（`verify_recon.py` 无条件绑定该输入）。
  - **Solana 不跳过**：== observation bundle 的 `holder_outputs.owners.sha256`
    （`scan_token_accounts.py` 无条件输出）。跳过 Solana 会留一个完整的绕过口子。
- **只比 sha256，不比 path。** Solana bundle 里记的是 basename（`holders_owners.json`），
  EVM 收据里记的是喂给 verify_recon 的绝对路径，两边路径形态天生不同，比 path 只会误伤。
- **只在 `--profile new-analysis` 跑，禁止放进 `validate_scan`。** 存量终态案走的是
  independent-audit，不会被追溯卡死；放进 validate 会连锁卡死 A5 重验与 handoff verify。
- 这条检查是**一致性校验器**：它证明"分布扫描和四查吃的是同一份字节"，不证明那份字节是链上真值。
  真值由四查收据自己那条链（envelope 三验＋producer 白名单＋`decide()` 重算）负责。

#### F-08：已记录的上游收据，记了就得三验

- `upstream_receipts` 是**记录性收据**：案根没有那份文件就不记（split-run 下 −1 出 initial scan 时，
  −2 还没把 preflight 副本按 G8 要求拷进案根），这是合法的。
- 但**凡是记进列表的条目，validate 就必须核实文件存在＋sha256＋size 三项全对**。旧版
  schema 文档宣称"initial 绑定上游收据"，产物里也确实躺着 `upstream_receipts`，可 validator
  一个字节都不核——这是"可伪造的证据外观"，比不写这个字段更坏。
- **校验方向只有"记录项 → 磁盘"这一条，不能反过来。** 要求"磁盘上有的都必须被记"会把 6.39.5
  修掉的 split-run 三闸死环原样修回来（G8 要求副本在案根、A5 重验要求清单不漂移，两者物理互斥）。
- 生产侧 `except ValueError: pass` 必须拆成两种情况：**文件不在场＝跳过记录**（合法）；
  **文件在场却非法**（符号链接、指到案外、不是普通文件）＝ exit 2。旧版一律吞掉，等于把掉包过的
  收据静默漂白成"本来就没有"。

### ② 同族 rg 清单

#### A. 容差/闭合类旋钮（查证"新容差有没有和别的闸串线"）

```text
rg -n --glob '*.py' --glob '!scripts/tests/**' 'TOLERANCE|tolerance_bps|_BPS\b|10000|闭合' scripts
```

| 位置 | 是什么 | 与本批的关系 |
|---|---|---|
| `holder_distribution_scan.py:51` `SNAPSHOT_CLOSURE_TOLERANCE_BPS = 10` | 本批新增：快照闭合容差 | 本批唯一新旋钮，独立写死 |
| `supply_truth_gate.py:68` `FORMAL_TOLERANCE_BPS_MAX = 10` | 批 A 的供给真值容差上限 | **刻意不复用**：那把带 waiver 出口，串线会连带松动本闸 |
| `shared_release_receipt.py:183/200/235` `tolerance_bps`／`approved_tolerance_bps` | 批 A 的 waiver 复核面 | 与本批零耦合，本批未动 |
| `handoff_manifest.py:629`、`entity_source_trace.py:613` `stock * 10000 < total` | 尘埃库存判据（0.01% 线） | 同款交叉乘法写法，不是容差旋钮，本批未动 |
| `entity_identity_gate.py:154` owner 全集对 total supply 闭合 | 身份闸的**精确**闭合（零容差） | 同族但更严，无需改；本批不放宽它 |
| `handoff_manifest.py:650/974`、`entity_source_trace.py:751`、`a4_gate.py:262`、`adjudication_validator.py` 各处"不闭合" | 溯源构成/簇 ID/名册闭合 | 名字撞车、语义无关，本批未动 |

查证结论：全库只有这一处新容差，没有第二份手抄的 10bps；供给真值那把与本批这把在代码上完全不通。

#### B. `upstream_receipts` 消费面（查证"改了会波及谁"）

```text
rg -n 'upstream_receipts' scripts references
```

运行时只有 `holder_distribution_scan.py` 四处：生产（:544）、语义剔除（:587-592，6.39.5 修的死环，本批保留）、
新增三验（:791-798）。文档三处已同批改口。**没有第二个消费者**，改动面收敛。

#### C. `validate_scan` 调用面（查证"三验会连带卡死谁"）

```text
rg -n 'validate_scan' scripts --glob '*.py'
```

| 调用点 | 传的 stage | 会不会被新三验波及 |
|---|---|---|
| `audit_release_gate.py:838` | `initial` | **会**——这正是要收紧的正面 |
| `handoff_manifest.py:391`（子进程 CLI） | `initial` | **会**——READY 闸自动跟着变强，finding 里"handoff 只是调用同一个弱 validator"从根上闭合 |
| `distribution_explanation_check.py:85` | `final` | 不会：final 产物没有 `upstream_receipts` 键 |
| `a5_report_seal.py:57` | `final` | 不会：同上，**存量终态案不会被追溯卡死** |
| `holder_distribution_scan.py:853`（record-round） | `final` | 不会：同上 |

### ③ 三件套测试与先红后绿

新文件 `scripts/tests/test_repair_batch_b.py`，已**显式**写进 `scripts/tests/run_all.py` 的 `SUITE`
（紧跟 `test_repair_batch_a.py`，run_all 无自动发现）。

先红命令：`python3 scripts/tests/test_repair_batch_b.py`，修前退出码 `1`，16 条里 10 条红：

```text
FAIL [F-03/1 快照缺口 99% 被拒] rc=0 out=0 PASS: initial NOT_EVALUABLE -> .../distribution_scan.json
FAIL [F-03/1 10bps 边界整数精确（内 PASS / 外 1 wei 即拒）] edge=0 over=0
FAIL [F-03/1 闭合容差是独立写死的 10bps 且不读收据容差] const=None
FAIL [F-03/2 EVM 同值换仓被拒] []
FAIL [F-03/2 Solana 分支存在] audit_release_gate 缺 check_distribution_snapshot_binding
FAIL [F-08 记录项缺件被拒] []
FAIL [F-08 记录项错 sha被拒] []
FAIL [F-08 记录项错 size被拒] []
FAIL [F-08 上游收据是符号链接 → 生产侧 exit 2] rc=0 PASS: initial NORMAL_SHAPE -> .../distribution_scan.json
FAIL [F-08 scan-schemas 已改口为记录性收据在场即三验] scan-schemas.md 未同批改口
BATCH B FAIL 10/16
```

修后同命令退出码 `0`，18/18 全绿（Solana 分支修好后多出 2 条子用例）：

```text
ok   [F-03/1 快照缺口 99% 被拒]
ok   [F-03/1 dead-sink 20% 合法绿例（sum=total≠net）]
ok   [F-03/1 10bps 边界整数精确（内 PASS / 外 1 wei 即拒）]
ok   [F-03/1 快照和超发被拒]
ok   [F-03/1 闭合容差是独立写死的 10bps 且不读收据容差]
ok   [F-03/2 EVM 合法案（同一份快照喂四查与分布扫描）放行]
ok   [F-03/2 EVM 同值换仓被拒]
ok   [F-03/2 Solana 快照 sha 相符放行]
ok   [F-03/2 Solana 同值换仓被拒]
ok   [F-03/2 Solana bundle 缺 owners 绑定被拒]
ok   [F-03/2 Solana 生产者仍输出 holder_outputs.owners]
ok   [F-08 记录项缺件被拒]
ok   [F-08 记录项错 sha被拒]
ok   [F-08 记录项错 size被拒]
ok   [F-08 磁盘有收据但 scan 未记录仍 PASS]
ok   [F-08 收据缺席＝跳过记录不报错]
ok   [F-08 上游收据是符号链接 → 生产侧 exit 2]
ok   [F-08 scan-schemas 已改口为记录性收据在场即三验]
PASS batch B F-03/F-08 regressions 18/18
```

覆盖矩阵：

| 类别 | 用例 | 口径 |
|---|---|---|
| 原反例 | F-03/1 快照缺口 | `total=100`／快照只有 1 个币，修前 exit 0 且 `snapshot_total_raw=1`，修后 exit 2＋`data_broken` |
| 原反例 | F-03/2 EVM 同值换仓 | 案内另存一份"总和一模一样、首尾两个 owner 对调"的快照，两份文件各自哈希自洽、data_map 都登记，只有交叉检查抓得到 |
| 原反例 | F-08 记录项缺件／错 sha／错 size | 三个变体分别改 `path`／`sha256`／`size`，修前 `validate_scan` 返回 `[]` |
| 同族变体 | 10bps 边界大整数 | `total=10²⁴`，缺口恰好 10²¹（＝10bps）放行，10²¹+1（多 1 wei）即拒——浮点实现做不到这个精度 |
| 同族变体 | Solana 分支 | sha 相符放行／同值换仓拒／bundle 缺 `owners` 绑定拒，三态齐全 |
| 失败分支 | 快照超发 | 和大于 total 且越过容差仍拒，旧版强度没丢 |
| 失败分支 | 上游收据是符号链接 | 生产侧 exit 2 并在报错里点名"上游收据"，不再静默跳过 |
| **合法绿例** | dead-sink 20% | 240 个私人 owner＋dead 桶占 total 的 20%，`sum=total≠net`，放行且 `denominators` 里 total/net 确实不等、burn 桶余额正确 |
| **合法绿例** | EVM 完整新分析案 | 同一份快照喂四查与分布扫描 → 发布闸零错误 |
| **合法绿例** | 磁盘有收据但 scan 未记录 | 案根事后多出 `channels_preflight.json`、scan 记录为空 → 仍 PASS（6.39.5 死环不复发） |
| **合法绿例** | 收据缺席 | 案根没有收据 → 生产侧照常 exit 0 并记空表 |
| 在场率守卫 | Solana 生产者字段 | 源码断言 `holder_outputs={"accounts": …, "owners": …}` 仍在，生产者一改名本条先红 |
| 文档同批 | scan-schemas 改口 | 断言"记录性收据"＋"在场即三验"＋"optional"三个词都在 |

#### 施工前的字段在场率实测（不靠读码推断）

Solana 那条绑定的字段是不是真的存在，用**真跑一遍生产者**确认，不是看代码猜的：起 b3 夹具 RPC、
跑 `scripts/solana/scan_token_accounts.py` 产出真 bundle，实测结果——

```text
bundle top keys: [... 'holder_outputs', ...]
holder_outputs: {"accounts": {"path": "holders_accounts.json", "size": 111, "sha256": "64e20eac…"},
                 "owners":   {"path": "holders_owners.json",   "size": 47,  "sha256": "616db46a…"}}
data/holders_snapshot_meta.json → outputs.holders_owners 同一份 ref
owners 落盘位置：data/holders_owners.json（＝分布扫描 find_snapshot 的默认候选之一）
```

两个结论：①字段无条件在场；②生产路径上 scanner 写的 owners 文件**就是**分布扫描默认会找到的那个文件，
所以 Solana 侧这条等值在真实案子里天然成立，不是给存量案设的路障。

#### 变异自检（证明这几道闸真的被测到，不是"看着有测"）

对每一处新校验做"删掉→跑测试"注入，注入前已备份两个生产文件
（`/tmp/hds.bak_20260813_103422`、`/tmp/arg.bak_20260813_103422`），每轮跑完立即按备份还原：

| 变异 | 注入内容 | 测试反应 |
|---|---|---|
| M1 | 第一层闭合退回 `if snapshot_sum > total` | 退出码 1；红：快照缺口 99%、10bps 边界 |
| M2 | 摘掉 `run()` 里第二层的调用 | 退出码 1；红：EVM 同值换仓 |
| M3 | 摘掉 validate 的记录项三验循环 | 退出码 1；红：记录项缺件／错 sha／错 size |
| M4 | 生产侧退回 `except ValueError: pass` | 退出码 1；红：上游收据符号链接 |
| M5 | Solana 绑到 `holder_outputs.accounts` 而非 `owners` | 退出码 1；红：Solana 快照 sha 相符放行 |

五处新校验全部"删掉即红"，无一处是摆设。还原后 `test_repair_batch_b.py` 退出码 0。

### ④ 新建代码六视角①②自审

#### 视角①：字段来源（这个数是谁给的，可不可信）

- **F-03/1**：`snapshot_sum` 只来自本次解析的快照文件（`parse_snapshot` 已拒重复 owner、拒非法 raw、
  拒负数），`total` 只来自 `load_supply` 读的 `supply_truth.json`，容差是模块常量。三个来源没有一个
  是调用者能通过 CLI 拨动的——CLI 没有、也不会加容差参数。
- **F-03/2**：快照 sha 取自 scan 产物的 `input_binding.snapshot.sha256`，该条目在同一次
  `validate_scan` 里已被 `_verify_bound` 对着磁盘实物三验过；对照值取自四查收据，而四查收据在同一次
  `run()` 里已由 `shared_release_receipt.validate_bundle` 深验过（schema、producer 仓库白名单、
  target 三键、envelope inputs 逐项三验）。**两边都不是自报数**，比的是两条已验链的交汇点。
- **残余边界（如实标注）**：这条检查证明的是"同一份字节"，不证明那份字节是链上真值。要伪造它，
  得连四查收据一起造——那已经落到 F-12 已接受边界（伪造整案数据链）的同一档，不是本批新开的口子。
- **另一条残余（实测过，不是推测）**：分布闸自己读的 `supply_truth.json` 只看该文件的
  `verdict/exit_code`，不验它是不是生产者产的收据；单独跑分布扫描时，手写一份小 total 的
  supply_truth 可以让残缺快照"闭合"。查证结论是这条在**发布路径上封死**：EVM/Solana 的四查 job spec
  里 supply_truth 生产者的 `--out` 就是案根 `supply_truth.json`（实测 b3 两条纵切片 spec 皆如此），
  发布闸会对同一个文件跑 `decide()` 重算＋formal 容差钳制＋envelope 三验。分布闸不重复造第二道
  收据验证，避免与批 A 的判定链形成两份手抄。
- **F-08**：三验的比对对象是 scan 里记录的 `path/sha256/size`，实物由 `safe_file` 取（拒符号链接、
  拒 `..`、拒越界、拒非普通文件），哈希与大小当场重算。记录项自报的只有"我声称绑了这份文件"，
  它是否成立完全由磁盘实物裁定。

#### 视角②：失败分支（出错时会不会假装没事）

- **F-03/1**：`raise` 走 `cmd_scan` 既有的兜底——落 `data_broken` 产物（exit_code 2）并
  `return 2`，不会留下一个 exit 0 的半成品 scan。已实测：缺口案的产物里
  `exit_code=2`、`not_evaluable_reason="data_broken"`。
- **F-03/2**：所有异常口径都走 `errors.append` 而不是抛出——缺 scan、缺 sha、链族判不出、
  找不到四查收据、收据里没有绑定字段、sha 不符，**六条分支全部 fail-closed 落错误**，
  没有一条是"读不到就跳过"。`load_json` 失败也会把解析错误塞进同一个 errors 表。
- **skip 分支的诚实交代**：`case_chain` 为假时不跑本检查。查过 `check_formal_case_chain` 的三条
  返回 None 路径（链声明缺失／链声明不一致／链不在正式矩阵），每一条都**先 append 了自己的错误**
  再 return None，所以"跳过本检查"永远伴随一条已存在的 BLOCK，构不成放行口子
  （`test_formal_chain_support`、`test_batch2_robinhood_exploration` 两条既有用例正面覆盖）。
- **F-08 生产侧**：只对"文件压根不在场"放行，判据是 `not exists() and not is_symlink()`——
  指向不存在目标的**悬空符号链接**（`exists()` 假但 `is_symlink()` 真）不会被误判成缺席，
  照样送进 `safe_file` 炸掉。目录占名同理会炸。
- **F-08 validate 侧**：非数组、条目非对象、缺件、错 sha、错 size 全部 raise，被 `validate_scan`
  外层收成 `scan 不可重验: …` 错误项，`cmd_validate` 返回 2。没有任何一条吞异常。

自审没发现需要继续改码的批 B 缺口。

### ⑤ 归因预判（git log 查证）

#### F-03：历史漏检，`a262b18`（2026-08-05，分布扫描器初版）

```text
git log --oneline -S '快照 raw 和大于冻结 total supply' -- scripts/report/holder_distribution_scan.py
=> a262b18 feat: add holder distribution scanner
```

只有这一条记录，说明单边检查从脚本诞生那天起就是这样，不是后来某次修复改坏的。
根因＝写的时候只想到"别超发"这一种数据错误，没把"快照残缺"当成同一个不变量的另一半。

#### F-08：修复中新引入，`2ebd885`（2026-08-12，v6.39.5）——**并且做了取证，不是照抄 codex 的结论**

`upstream_receipts` 这个字段自 `a262b18` 就存在，validator 也从来没有专门三验过它。但 6.39.5 之前，
它被 `semantic_payload` 的逐位语义比较**顺带兜住了**：重算会照磁盘实物重新收录收据，伪造的记录项
和重算结果对不上就报"语义与独立重算不一致"。6.39.5 为了修 split-run 三闸死环把它剔出语义比较，
**顺带把这层顺带的覆盖也拆了，且没有补上定向检查**——这才是"可伪造的证据外观"真正诞生的时刻。

取证方式：把 `2ebd885^` 版本的脚本单独 checkout 到临时目录，用同一个伪造反例跑旧 validator——

```text
旧版基线 validate: []
旧版对伪造记录项 validate: ['scan 语义与独立重算不一致']
```

旧版确实拦得住。所以修法只能是"补定向三验"，**不能**是"把 upstream_receipts 放回语义比较"——
后者会把 TAG 案实撞的三闸死环原样修回来。

## diff-finding-map

| 文件／hunk | finding | 归属说明 |
|---|---|---|
| `holder_distribution_scan.py` 模块 docstring（`@@ -17,2 +17,4`） | F-03＋F-08 | 把双向闭合、容差独立、记录性收据语义写进脚本自述 |
| `holder_distribution_scan.py` 新常量 `SNAPSHOT_CLOSURE_TOLERANCE_BPS`（`@@ -45,0 +48,4`） | F-03 | 独立旋钮＋"为什么不复用供给真值容差"的设计意图注释 |
| `holder_distribution_scan.py` `build_scan` 闭合检查（`@@ -503,2 +509,9`） | F-03 | 单边 `>` 换成整数交叉乘法双向闭合，分母 total 不是 net |
| `holder_distribution_scan.py` `build_scan` 上游收据收录（`@@ -523,2 +536,8`） | F-08 | `except: pass` 拆成"缺席跳过／在场非法炸" |
| `holder_distribution_scan.py` `validate_scan` 记录项三验（`@@ -768,0 +788,11`） | F-08 | 已记录条目逐项存在＋sha＋size，方向只走"记录项→磁盘" |
| `audit_release_gate.py` 新函数 `check_distribution_snapshot_binding`（`@@ -726,0 +727,49`） | F-03 第二层 | EVM／Solana 双分支交叉检查，只比 sha 不比 path |
| `audit_release_gate.py` `case_chain = check_formal_case_chain(...)`（`@@ -758 +807`） | F-03 第二层 | 接住已有返回值判链族，未改该函数行为 |
| `audit_release_gate.py` new-analysis 块内调用（`@@ -792,0 +842,2`） | F-03 第二层 | 挂在 new-analysis 必经路径上，不进 validate_scan |
| `references/scan-schemas.md` 三处改口 | F-03＋F-08 | 双向闭合口径＋记录性收据 optional/在场即三验＋第二层交叉检查说明 |
| `references/analyze-workflow.md` A3 第 5 步 | F-03 第二层 | −1 必须用同一份快照喂 verify_recon 与 initial scan |
| `references/split-run.md` −1 第 9 步 | F-03 第二层＋F-08 | 同上＋记录性收据口径 |
| `scripts/tests/test_repair_batch_b.py` | F-03＋F-08 | 原反例、同族变体、失败分支、四条合法绿例、在场率守卫 |
| `scripts/tests/run_all.py` | F-03＋F-08 | 显式挂载新回归文件 |
| `scripts/tests/test_review_20260804_p105.py` 夹具 | F-03 第二层 | 新增 `bind_balance_receipt_to_snapshot`：四查 balance 收据绑同一份快照后重建 shared receipt |
| `scripts/tests/test_a4_gate.py` 夹具 | F-03 第二层 | 同款绑定，供 P1-05 全新分析构建路径使用 |
| 本工单 | F-03＋F-08 | 五栏、红绿、变异、rg、取证与残余边界落盘 |

**两处夹具改动的性质说明**：不是"为了转绿改弱断言"，而是把夹具补成合规的真实工作流形态——
原夹具的四查 balance 收据绑的是一份 `raw_transfers.jsonl`，与分布扫描吃的 owner 快照根本不是同一个
文件，那是夹具失真，不是新检查过严。两个夹具原有的断言一条没动、没删、没放宽，只增加了绑定步骤；
证据是 `test_a4_gate` 仍 23 项全过、`test_review_20260804_p105` 的两条 profile 断言原样通过。

## 新契约面清单（批 D 统一登记）

- 新模块常量：`holder_distribution_scan.SNAPSHOT_CLOSURE_TOLERANCE_BPS = 10`。
- 新发布闸检查函数：`audit_release_gate.check_distribution_snapshot_binding(case_dir, data, chain, errors)`。
- 既有字段的新强制语义：
  - owner 快照对 `total_supply_raw` 双向闭合，容差 10bps（分母 total，不是 net）。
  - `input_binding.upstream_receipts` 明确为 optional 记录性收据；在场即三验；在场但非法则生产侧 exit 2。
  - new-analysis 发布要求 `input_binding.snapshot.sha256` 等于四查 `balance` 收据的
    `inputs.balances.sha256`（EVM）／observation bundle 的 `holder_outputs.owners.sha256`（Solana）。
- 新工作流硬性：−1 的 `verify_recon --balances` 与 `holder_distribution_scan --stage initial`
  必须吃同一个快照文件。

按铁律，本批**没有**改 `scripts/tests/contract_manifest.json` 与 `scripts/tests/contract_ids_snapshot.json`；
统一契约快照登记留批 D。

## 存量案迁移后果（如实标注，供批 D 写 CHANGELOG）

1. 分布扫描脚本本体改动会改 `input_binding.algorithm.sha256`，存量 scan 重验必须重跑 initial/final scan——
   这是分布闸自诞生起的算法绑定语义，任何一次改这个文件都一样，不是本批新增的迁移负担。
2. F-08 三验只落在 **initial** scan 上（final 产物没有该字段），`a5_report_seal`／
   `distribution_explanation_check`／`record-round` 三条 final 路径**不会**被追溯卡死。
3. 会被新拦的存量形态只有一种：−1 记录了 preflight，随后案根那份文件被换成字节不同的副本。
   这本来就该拦——记录说绑了 A，磁盘上躺的是 B。
4. 快照闭合的**超发侧口径按计划从"零容差"变成"10bps 容差"**（计划定案的对称窗口）。这是本批唯一一处
   放宽，如实记在此处：旧版 `sum = total + 1` 会拒，新版在 10bps 内放行。理由是块高差会让快照两侧
   都产生漂移，单侧零容差与双侧闭合不自洽；越过 10bps 的超发仍拒（已有用例覆盖）。

## 验证与最终退出码

全部在本次施工环境实跑采集：

| 命令 | 退出码 | 摘要 |
|---|---|---|
| `python3 -m py_compile`（两个生产文件） | `0` | — |
| `python3 scripts/tests/test_repair_batch_b.py` | `0` | batch B F-03/F-08 regressions 18/18 |
| `python3 scripts/tests/test_distribution_gate.py` | `0` | distribution gate red-green contract |
| `python3 scripts/tests/test_a4_gate.py` | `0` | 23 项全过 |
| `python3 scripts/tests/test_audit_release_gate.py` | `0` | 十一类契约全过 |
| `python3 scripts/tests/test_review_20260804_p105.py` | `0` | new-analysis vs independent-audit profile |
| `python3 scripts/tests/test_handoff_manifest.py` | `0` | 67 项 |
| `python3 scripts/tests/invariant_scan.py` | `0` | producers=52 / consumers=57 |
| `python3 scripts/tests/docs_lint.py --all` | `0` | 58 个文档，引用无断链、粗体配对完整 |
| `git diff --check` | `0` | — |
| **`python3 scripts/tests/run_all.py`** | **`0`** | **SUITE 93 项全通过，0 FAIL** |

- 版本三处 `VERSION`、`SKILL.md`、`pyproject.toml` 均未改，保持 6.39.5。
- 两份批 D 契约快照未改；批 C／D 生产文件（state_from_facts／standard_charts／replay_pass2／
  replay_duck／replay_edges／build_evolution／entity_source_trace／handoff_manifest／
  a5_report_seal／fetch_hypersync_v2）一个都没动——`git diff --name-only` 过滤实测为空。
- 未 commit。

## commands-staging 与部署同步

**本批文档改动未触及 commands-staging 的命令契约文本。** 三份命令文件里
`holder_distribution_scan`／`verify_recon`／`balances`／"快照" 全部零命中（rg 实测 0 行），
命令正文不描述分布扫描的快照来源，因此无需改命令、无需部署同步。

按 R10"deploy sync 是弱闸不可依赖"的要求，另附**独立实测**的 SHA 全等记录（不引用该测试的 rc=0）：

```text
token-analyze-1.md  staging=9832eace6960bb66…  deployed=9832eace6960bb66…  SAME
token-analyze-2.md  staging=510152a8a40efcc3…  deployed=510152a8a40efcc3…  SAME
token-analyze.md    staging=f227da3bddcee26b…  deployed=f227da3bddcee26b…  SAME
```

本批完成
