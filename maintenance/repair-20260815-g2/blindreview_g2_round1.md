# g2 组盲审 round1（独立红队 · 边界外变异复核）

- 复核对象：`ddba187..861a234`（4577106 F-04 / 9d2f97c F-10 / 4a43234 F-07 / daaed16 F-09 / 861a234 中心登记）
- 复核方式：只读复核。**未复用仓库自带测试**（那是被测对象），全部向量由独立探针脚本现造现跑。
- 探针位置：`/private/tmp/g2probe/`（不入仓库树）。仓库 tracked 文件零改动，无 git 写操作。
- 向量总数：**209**（round1 主轮 134 + time 补充轮 50 + round2 复验 25）；BREACH **7（均已于消化轮关闭）**；PARTIAL **8**。
- ⚠ **补充轮曾改变总判定**：主轮（F-04/F-07 balance 面/F-09/F-10）零 BREACH，但 time 查攻击轮（§八·补充）打出 7 个 BREACH，根因是 plan 与 plan_receipt 之间缺内容绑定 → 当时判 **BLOCK**。
- ✅ **消化轮 `55f2c44` 后经 round2 复验（见文末 round2 节）**：7 条 BREACH 逐条关闭，边界外 17 个新向量无新 BREACH。**现行总判定：CONDITIONAL —— 可交付。**
- 阅读顺序提示：下面 §一～§九 是 round1 当时的记录（总判定栏仍写 BLOCK，属历史状态）；**以文末 round2 节的判定为准**。

---

## 一、结论先行

| 刀 | 主题 | 向量数 | BREACH | PARTIAL | 判定 |
|---|---|---|---|---|---|
| F-04 | EVM 观测件拒空 code / 66 字符 ABI word / EIP-1898 同分叉 | 28 | 0 | 0 | **PASS** |
| F-10 | Arbitrum 探索档兑现 + 正式面 mode+formal_ready 双断言 | 18 | 0 | 0 | **PASS** |
| F-07 | 四查子收据消费侧从实物独立重算（balance/supply 面，schema v3） | 43 | 0 | 1 | **PASS（附 1 项纵深）** |
| F-07 | 同上 —— **time 面**（§八·补充轮） | 50 | **7** | 2 | **FOUND-ISSUE** |
| F-09 | GMGN 黄灯制 + 人工查证说明放行 | 45 | 0 | 3 | **PASS（附 3 项瑕疵）** |
| 末刀 | 中心登记（run_all/契约） | — | — | — | 见 §八 复核边界 |

**总判定：BLOCK —— 建议先修 time 面 plan 绑定再融合。**

- BREACH（能过发布闸的真绕过）：**7**，全部集中在 F-07 的 time 那一查，同一根因（plan 权威性未验），修一处可关四条
- PARTIAL：**6**（主轮 4 + time 轮 2），P2/P3，不单独阻断
- 其余四刀（F-04 / F-10 / F-09 / F-07 的 balance+supply 面）在 134 个向量下**全部守住**，本身可交付

**必须讲清的归因**：这**不是 F-07 造成的回归**。基线 `ddba187` 的 time 那一查只有一行 `schema == "time-spotcheck/v2"`，`_validate_time_receipt` 整个函数是 F-07 新建的——补充轮里 H11–H39 那 30 个向量（rows 与 plan 点位一一对应、transcript 逐笔绑定、六计数重算、PASS 不容 MISMATCH）在基线全都能过，现在全被拦住。F-07 把 time 面从"几乎不设防"提到了"逐笔重算"，方向完全正确。

问题出在一处：**这道新防线把"标准答案"的来源（plan）当成可信输入，却没验证这份 plan 是不是权威签发的那一份。** 重算做得再严，只要攻击者能自己定义标准答案，重算就失去意义。

一句话说人话：查作业查得很仔细——每道题都重算了、答案对不上就打回。但**没检查手里这份"标准答案"是不是老师发的**。学生自己伪造一份只剩一道题的答案卡递上来，照样算全对。

---

## 二、我的信任模型（判定 BREACH 的尺子）

复核前先钉死攻击者能力，否则"攻穿"没有标准：

- **攻击者可以**：任意手写收据 JSON（不必经生产者脚本）；任意改写案根内的输入实物文件（config/balances/replay_stats/gmgn/transcript/plan/note）并重算其 size+sha256 让 envelope 层重新自洽；任意改 observations 的自报计数与摘要，并让"改一个字段同时改它的自报摘要"联动。
- **攻击者不可以**：改仓库里的生产者脚本（`validate_receipt` 对 producer 做路径白名单+哈希绑定）；伪造真实 RPC 节点的响应（系统在 `evm_observation.py` 开头已显式声明：bundle 绑的是"请求/响应记录"，不证明远端真的执行过——这是全系统的公开边界，不算本次五刀的缺陷）。
- **BREACH 判定线**：在上述能力内，让一份与绑定实物**矛盾**的证据通过消费面（`validate_reconciliation_check` / `validate_reconciliation_report` / `validate_evm_observation_bundle`）。

---

## 三、F-04：EVM 观测件（28 向量 / 0 BREACH）

**不变量**：正式 EVM 供给观测 bundle 必须拒绝冻结块上 runtime code 为空的目标（EOA / 未部署地址）；totalSupply、balanceOf 的 eth_call 返回值必须是严格 32 字节 ABI word（66 字符）；getCode 与三笔 eth_call 必须锚定同一 EIP-1898 blockHash。

探针：`/private/tmp/g2probe/f04_probe.py`

| 编号 | 攻击面 | 构造方法 | 预期 | 实际 | 判定 |
|---|---|---|---|---|---|
| D00 | 基线 | 合法 bundle + 8 条 transcript | 接受 | 接受 | 基线有效 |
| D01 | 空 code | `getCode` 返回 `0x`（EOA） | 拒 | 拒：runtime code sha256 identifies empty bytecode | blocked |
| D02 | 边界 | code = `0x00` 单零字节 | 接受 | 接受 | 合法（非空 code，EOA 返回的是 `0x` 不是 `0x00`） |
| D03 | 空 code | bundle 里 `runtime_code_sha256` 直接填空串哈希 | 拒 | 拒：同上 | blocked |
| D04 | 空 code | transcript 层 code 改 `0x` | 拒 | 拒 | blocked |
| D05 | 空 code | transcript 层 code 改 `""` | 拒 | 拒 | blocked |
| D06 | 空 code | transcript 层 code 改 `null` | 拒 | 拒 | blocked |
| D07 | ABI word | totalSupply 返回 `0x0` 短值 | 拒 | 拒：transcript total_supply_raw result mismatch | blocked |
| D08 | ABI word | totalSupply 返回 `0x` 空值 | 拒 | 构造期即失败（`int("0x",16)` 无法成值），等价拒 | blocked |
| D09 | ABI word | totalSupply 返回 68 字符（超长） | 拒 | 拒 | blocked |
| D10 | ABI word | totalSupply 返回 65 字符（奇数长度） | 拒 | 拒 | blocked |
| D11 | ABI word | totalSupply 用 `0X` 大写前缀 | 拒 | 拒 | blocked |
| D12 | ABI word | balanceOf(ZERO) 返回 `0x0` | 拒 | 拒：transcript zero_balance_raw result mismatch | blocked |
| D13 | 大小写 | balanceOf(DEAD) 用大写 hex，仍 66 字符 | 接受 | 接受 | 合法（RPC 大小写不敏感，值相等） |
| D14 | EIP-1898 | getCode 用旧协议块号 `hex(as_of)` | 拒 | 拒：transcript eth_getCode params mismatch | blocked |
| D15 | EIP-1898 | getCode 锚另一分叉 blockHash | 拒 | 拒 | blocked |
| D16 | EIP-1898 | getCode selector 的 `requireCanonical=False` | 拒 | 拒 | blocked |
| D17 | EIP-1898 | totalSupply 锚另一分叉 blockHash | 拒 | 拒：eth_call params mismatch at seq 3 | blocked |
| D18 | 规范化 | getCode selector 两个键顺序颠倒 | 接受 | 接受 | 合法（JSON 对象无序，dict 比较不看键序） |
| D19 | 分叉 | anchor 的 recheck 哈希 ≠ block_hash | 拒 | 拒 | blocked |
| D20 | 分叉 | recheck 块换成另一分叉 | 拒 | 拒 | blocked |
| D21 | 模式 | mode 改 exploration 混入正式面 | 拒 | 拒：must be PASS/0 | blocked |
| D22 | 身份 | producer 换成别的仓库脚本 | 拒 | 拒：producer hash mismatch | blocked |
| D23 | 结构 | transcript 加到 9 条 | 拒 | 拒：must contain exactly 8 calls | blocked |
| D24 | 联动 | bundle.supply 与 transcript 不符 | 拒 | 拒 | blocked |
| D25 | 语义 | `block_binding` 改成块号语义 | 拒 | 拒 | blocked |
| D26 | 边界 | tip 块早于锚点块 | 拒 | 拒 | blocked |
| D27 | 规范化 | supply 用前导零 | 拒 | 拒：must be a non-negative decimal string | blocked |

**结论：该刀在 24 个攻击向量下未攻穿**（另 4 个为合法语义的预期接受）。三层收紧（producer / transcript / validator）等深，没有出现"某一层漏检"的缝隙——D01/D03/D04/D05/D06 从五个不同入口打空 code，全部被拦。

---

## 四、F-10：Arbitrum 探索档隔离（18 向量 / 0 BREACH）

**不变量**：Arbitrum（release_tier=exploration）可以跑探索档对账 CLI，但正式发布消费面必须同时拒绝 mode≠formal 与 target.chain 非 formal_ready 的收据。

探针：`/private/tmp/g2probe/f10_probe.py`

| 编号 | 攻击面 | 构造方法 | 预期 | 实际 | 判定 |
|---|---|---|---|---|---|
| G1 | 消费面 | arbitrum 收据，mode 字段整体改写成 `formal` | 拒 | 拒：正式对账消费面只接受 formal-ready 链 | blocked |
| G2 | 消费面 | arbitrum + mode=exploration | 拒 | 拒：receipt must be formal | blocked |
| G3 | 别名绕过 | 链名写别名 `arb` 伪装 | 拒 | 拒（`resolve_alias` 先归一，formal_ready 仍 False） | blocked |
| G4 | 分支覆盖 | arbitrum 走 supply 分支 | 拒 | 拒 | blocked |
| G5 | 基线对照 | eth + formal | 接受 | 接受 | 基线有效（证明拒绝来自链策略而非夹具坏了） |
| G6 | wrapper 层 | `reconciliation_report.json` 的 target.chain=arbitrum，连 wrapper 一起改 | 拒 | 拒：wrapper 层 formal_ready 断言先炸 | blocked |
| G7 | 策略函数 | `resolve_execution_mode(arbitrum, False, balance)` | 抛错 | 抛：探索档链必须显式 --exploration | blocked |
| G8 | 策略函数 | `resolve_execution_mode(arbitrum, True, balance)` | exploration | exploration | 符合 |
| G9 | 策略函数 | `resolve_execution_mode(eth, False, balance)` | formal | formal | 符合 |
| G10 | 策略函数 | `resolve_execution_mode(eth, True, balance)` | exploration | exploration | 符合 |
| G11 | 执行集 | polygon（unsupported tier）进可执行集 | 抛错 | 抛：不在 balance 可执行集 | blocked |
| G12 | CLI 层 | `verify_recon --chain arbitrum` 不带 `--exploration` | 非零退出 | rc=2 | blocked |
| G13 | CLI 层 | `verify_recon --chain polygon` | 非零退出 | rc=2（不在 choices） | blocked |
| G14 | 判定面 | `formal_ready` 对 arbitrum / arb / arbitrum one / robinhood / polygon（5 个子项） | 全 False | 全 False | blocked |

**结论：该刀在 17 个攻击向量下未攻穿。** 防线是三重的：CLI 层（执行集 + 必须显式 `--exploration`）、单查层（mode==formal **且** formal_ready）、wrapper 层（报告 target 也验 formal_ready）。把 mode 字段整体改写成 `formal` 这种"连自报摘要一起伪造"的手法（G1/G6）没有用——因为 `formal_ready` 是从链注册表的能力闭包算出来的，不读收据里的任何自报字段。执行集放宽没有给正式发布面开旁路。

---

## 五、F-07：四查子收据消费侧深重验（43 向量 / 0 BREACH / 1 PARTIAL）

**不变量**：消费侧必须从绑定的输入实物独立重算，而不是只看自报计数。

探针：`/private/tmp/g2probe/f07_probe.py`（批1，改 observations）、`f07b_probe.py`（批2，改输入实物 + 重算哈希）、`f07c_crossdepth.py`（批3，纵深交叉验证）

### 批 1：保持实物不变，只篡改收据 observations（16 向量）

| 编号 | 攻击面 | 构造方法 | 预期 | 实际 | 判定 |
|---|---|---|---|---|---|
| A1 | 状态谎报 | chain_raw≠replay 却谎称 status=OK | 拒 | 拒：status is inconsistent with diff_raw | blocked |
| A2 | （无效向量） | chain_raw 设为与实物相同 | 接受 | 接受 | 无效向量，记录留档 |
| A2b | 数值注水 | chain_raw 注水但 transcript 仍真实 | 拒 | 拒：diff_raw is not recomputed | blocked |
| A3 | 隐藏 | 删除最大户行并同步减计数 | 拒 | 拒：address sequence differs from bound balances | blocked |
| A4 | 排序 | rows 顺序颠倒（试非确定性排序） | 拒 | 拒：address sequence 不符 | blocked |
| A5 | 覆盖面 | top_n=1（合法缩小抽查面） | 接受 | 接受 | 见 PARTIAL-2 |
| A6 | 闭合 | supply_closure.balance_sum 改错 | 拒 | 拒：differs from bound artifacts | blocked |
| A7 | 未知字段 | supply_closure 加额外字段 | 接受 | 接受 | 无收益（被比对的字段逐个重算） |
| A8 | 计数 | matched 注水成 99 | 拒 | 拒：matched differs from rows | blocked |
| A9 | 账本 | replay_raw 与 balances 实物不符 | 拒 | 拒 | blocked |
| A10 | 规范化 | chain_raw 加前导零 | 拒 | 拒：must use canonical integer spelling | blocked |
| A11 | 类型 | requested_top_n = True（bool 混入 int） | 拒 | 拒：must be a positive integer | blocked |
| A12 | 语义标签 | selection 改成 `all_holders` | 拒 | 拒：selection semantics invalid | blocked |
| A13 | 未知字段 | observations 顶层加 key | 接受 | 接受 | 无收益 |
| A14 | 伪摘要 | 收据顶层塞 `injected_summary{all_ok:true}` | 接受 | 接受 | 无收益（消费面不读未知字段，只读重算项） |
| A15 | 注入 | 追加一行伪造地址 | 拒 | 拒：address sequence 不符 | blocked |
| A16 | 字段缺失 | 删除 rpc_errors 字段 | 拒 | 拒：rpc_errors differs from rows | blocked |

### 批 2：攻击者完全控制输入实物（改文件 + 重算 sha256，22 向量）

| 编号 | 攻击面 | 构造方法 | 预期 | 实际 | 判定 |
|---|---|---|---|---|---|
| B1 | 改账 | 改 balances 并同步改 rows/transcript | 拒 | 拒：gmgn rows differ from bound CSV/balances | blocked |
| B2 | 改账 | B1 + 同步改 mint | 拒 | 拒：同上 | blocked |
| B3 | 全联动 | 改 balances+replay_stats+config+transcript+gmgn 全部联动自洽 | — | 单查面接受；**四查面被 supply_truth 拦**（见 E2/E4） | blocked（纵深） |
| B4 | transcript | 多一条记录 | 拒 | 拒：length does not match balance rows | blocked |
| B5 | transcript | seq 不连续 | 拒 | 拒 | blocked |
| B6 | transcript | params 块高改成 as_of−1（跨块取值） | 拒 | 拒：do not bind row address/block | blocked |
| B7 | transcript | `to` 指向另一个代币合约 | 拒 | 拒 | blocked |
| B8 | transcript | `data` 查的是别的地址（张冠李戴） | 拒 | 拒 | blocked |
| B9 | transcript | method 换成 `eth_getBalance`（原生币余额冒充 ERC20） | 拒 | 拒：must be eth_call | blocked |
| B10 | transcript | result 用 `0x` 空值 | 拒 | 拒：is not hex | blocked |
| B11 | 重复键 | balances 出现同址大小写重复 | 拒 | 拒：balance_sum differs from bound artifacts | blocked |
| B12 | 双写分叉 | replay_stats 用 max_block=0 + last_block=真值 | 拒 | 拒：cutoff 不符 | blocked（另见 PARTIAL-4） |
| B13 | 负数 | balances 含负余额 | 拒 | 拒 | blocked |
| B14 | 非有限数 | gmgn pct = NaN | 拒 | 拒：must be finite | blocked |
| B15 | 数值边界 | gmgn pct 用 400 位超大整数 | 拒 | 拒 | blocked |
| B16 | 路径逃逸 | transcript 换成指向案外的 symlink | 拒 | 拒：envelope invalid（symlink） | blocked |
| B17 | 路径逃逸 | inputs.balances 绑案外绝对路径 | 拒 | 拒：input escapes case root | blocked |
| B18 | 绑定缺失 | 删除 inputs.transcript 绑定 | 拒 | 拒：must bind path/size/sha256 | blocked |
| B19 | 截止块 | replay_stats 截止块 ≠ target | 拒 | 拒 | blocked |
| B20 | 目标 | config.token ≠ target.token | 拒 | 拒 | blocked |
| B21 | schema | v2 收据混入正式面 | 拒 | 拒：expected v3 | blocked |
| B22 | 覆盖面 | ZERO/DEAD 占据 top2，真大户被挤出 top_n=3 | — | 接受 | **PARTIAL-2** |

### 批 3：纵深交叉验证（判定 B3 定级，5 向量）

| 编号 | 攻击面 | 构造方法 | 预期 | 实际 | 判定 |
|---|---|---|---|---|---|
| E1 | 基线 | 诚实 supply_truth（mint=链上真值） | 接受 | 接受 | 基线有效 |
| E2 | B3 纵深 | mint 改小 1e18，观测件保持真实链上值 | 拒 | 拒：primary_verdict 与 decide 独立重算值不一致 | blocked |
| E3 | 容差蒙混 | 改账 + 容差调到 100bps | 拒 | 拒：formal tolerance above 10bps lacks waiver | blocked |
| E4 | 极小偏差 | 改账 1 wei + 0 容差 | 拒 | 拒：同 E2 | blocked |
| E5 | 分账本 | 给 verify_recon 用假账、supply_truth 用真账 | 拒 | 代码面确认：report 层强制三份 replay_stats sha256 全等 | blocked |

**结论：该刀在 39 个攻击向量下未攻穿，另 1 项纵深（PARTIAL-2）。**

关于 B3 的定级说明（这是本次最需要讲清楚的一处）：单看 balance/supply 一查，攻击者把 5 份实物全部改到互相自洽确实能过——但这**不是 F-07 的漏洞**，而是"离线全套伪造"这个更大的边界。E2/E4 证明：只要伪造者动了重放账本的 mint，`supply_truth` 那一查就会用独立重算的 `decide()` 把它抓出来，因为该查的"链上总量"绑定的是观测件（F-04 的 bundle），跟 config 里写什么无关。E5 证明伪造者也不能"两本账各查各的"。所以在四查体系里 B3 不成立，判 blocked。F-07 的真实价值由 A1–A16、B1–B2 证明：**改一处就炸**，把低成本的"只改收据"伪造彻底堵死了。

---

## 六、F-09：GMGN 黄灯制与查证说明（45 向量 / 0 BREACH / 3 PARTIAL）

**不变量**：GMGN 对表差异 >0 时收据仍 PASS 但打黄灯；带黄灯的案发布前必须附一份合法人工查证说明才放行；生产侧与消费侧刻意双写，判定不得分叉。

探针：`/private/tmp/g2probe/f09_probe.py`（互锁 + 说明件 + 分叉扫描）、补测见 §六.3

### 6.1 黄灯互锁与说明件（28 向量）

| 编号 | 攻击面 | 构造方法 | 预期 | 实际 | 判定 |
|---|---|---|---|---|---|
| C00 | 基线 | 合法黄灯 + 合法说明 | 接受 | 接受 | 基线有效 |
| C01 | 抹黄灯 | 有差异但 warnings 清空 | 拒 | 拒：warnings do not interlock with recomputed divergences | blocked |
| C02 | 抹黄灯 | 有差异但**删除** warnings 字段（缺失 vs 空值） | 拒 | 拒：must be a duplicate-free known-string array | blocked |
| C03 | 缺说明 | 有差异但不绑 divergence_note | 拒 | 拒：requires inputs.divergence_note | blocked |
| C04 | 反向 | 无差异却绑 note | 拒 | 拒：zero divergence must not bind note | blocked |
| C05 | 反向 | 无差异却加 warnings | 拒 | 拒（互锁是双向的） | blocked |
| C06 | 数组 | warnings 重复两次 | 拒 | 拒 | blocked |
| C07 | 数组 | warnings 混入未知字符串 `reviewed_ok` | 拒 | 拒 | blocked |
| C08 | 类型 | warnings 改成字符串而非数组 | 拒 | 拒 | blocked |
| C09 | 旧说明复用 | 说明绑旧输入哈希 | 拒 | 拒：inputs_sha256.gmgn mismatch | blocked |
| C10 | 覆盖不全 | 说明的 divergences 写成空集合 | 拒 | 拒：does not cover recomputed divergences | blocked |
| C11 | self_error | cause 写 `self_error`（重放侧自己算错） | 拒 | 拒：cause invalid | blocked |
| C12 | self_error | cause 写 `replay_error` | 拒 | 拒 | blocked |
| C13 | 不可见字符 | explanation 用 60 个零宽空格充数 | 拒 | 拒：explanation too short | blocked |
| C14 | 空洞充数 | explanation 用 40 个 ASCII 点 | 拒 | **接受** | **PARTIAL-1** |
| C15 | 长度 | explanation 只有 5 个字 | 拒 | 拒 | blocked |
| C16 | 语义否定 | conclusion 含承诺句但整句语义相反 | 拒 | **接受** | **PARTIAL-1** |
| C17 | 承诺句 | conclusion 缺承诺句 | 拒 | 拒：lacks required attestation | blocked |
| C18 | 哈希 | request_sha256 填错 | 拒 | 拒 | blocked |
| C19 | 时间造假 | investigated_at 填 2030 年 | 拒 | 拒：later than now+1d | blocked |
| C20 | 时间格式 | investigated_at 带毫秒 | 拒 | 拒：must use YYYY-MM-DDTHH:MM:SSZ | blocked |
| C21 | 额外字段 | note 塞 `approved: true` | 拒 | 拒：fields invalid（严格集合相等） | blocked |
| C22 | 顺序 | divergences 顺序颠倒 | 拒 | 拒：does not cover recomputed divergences | blocked |
| C23 | 顺序 | findings 顺序错位 | 拒 | 拒：findings[0] address mismatch | blocked |
| C24 | 别名 | note.target 链名写 `ethereum` 别名 | 拒 | 拒：request.target mismatch | blocked |
| C25 | 非有限数 | divergence 的 diff_pp = NaN | 拒 | 拒：must be finite | blocked |
| C26 | 路径 | note 放案内子目录 | 接受 | 接受 | 合法 |
| C27 | 路径逃逸 | note 换成指向案外的 symlink | 拒 | 拒：envelope invalid | blocked |

### 6.2 生产/消费双写分叉扫描（16 向量）

同一份说明件同时喂给生产侧 `verify_recon._validate_gmgn_divergence_note` 与消费侧 `shared_release_receipt._validate_gmgn_divergence_note`，比对两侧判定是否一致。

| 编号 | 变异 | producer | consumer | 是否分叉 |
|---|---|---|---|---|
| F0 | 合法基线 | accept | accept | 一致 |
| F1 | explanation 全角句号 ×40 | accept | accept | 一致 |
| F2 | explanation 全角空格 ×40 | reject | reject | 一致 |
| F3 | explanation 软连字符 ×40 | reject | reject | 一致 |
| F4 | investigator 零宽字符 | reject | reject | 一致 |
| F5 | evidence_refs 案外绝对路径 | reject | reject | 一致 |
| F6 | evidence_refs 合法同目录 | accept | accept | 一致 |
| F7 | evidence_refs 路径逃逸 `../..` | reject | reject | 一致 |
| F8 | target.as_of_block 字符串化 | reject | reject | 一致 |
| F9 | gmgn_pct 非规范拼写 `60.50` | reject | reject | 一致 |
| F10 | divergence address 大写 | reject | reject | 一致 |
| F11 | conclusion 仅承诺句本身 | accept | accept | 一致 |
| F12 | 时间用 `+00:00` 偏移 | reject | reject | 一致 |
| F13 | findings 缺 cause 字段 | reject | reject | 一致 |
| F14 | cause 大写变体 | reject | reject | 一致 |
| F15 | inputs_sha256 大写 hex | reject | reject | 一致 |
| **F16** | **evidence_refs 案内绝对路径** | **reject** | **accept** | **★分叉 → PARTIAL-3** |

**结论：该刀在 41 个攻击向量下未攻穿。** 黄灯互锁（`(warning in warnings) == bool(divergences)`）是双向的，抹黄灯、假黄灯、字段删除三条路全堵死；说明件与输入哈希、差异集合、顺序、时间、schema 全绑定，旧说明无法复用到新差异；`self_error` 场景确实没有放行出口（cause 白名单只有 gmgn_data_lag / methodology_diff / gmgn_upstream_error 三个值，且 conclusion 强制含"重放数据经查证无误"承诺句——真是重放侧算错的话，人只能写假话才能放行，责任落到署名的 investigator 头上，设计上闭合）。双写实现 16 个向量判定完全一致，只在 F16 一处分叉。

---

## 七、发现汇总（PARTIAL 逐条）

| 编号 | 级别 | 位置 | 一句话 |
|---|---|---|---|
| PARTIAL-1 | P3 | `shared_release_receipt.py:778-792`、`verify_recon.py:227-251` | 查证说明的 explanation 可用 40 个点、conclusion 可用语义相反的整句蒙混——机器只验字符类与长度，验不了自然语言语义 |
| PARTIAL-2 | P2 | `shared_release_receipt.py:638-641`、`:684` | 链上余额抽查的覆盖面完全由生产侧 `top_n` 决定，消费面只要求"至少 1 行非 sink"，不设下限也不看占比 |
| PARTIAL-3 | P3 | `verify_recon.py:239` vs `shared_release_receipt.py:786` | 双写分叉：案内**绝对路径**的 evidence_ref，生产侧拒、消费侧收 |
| PARTIAL-4 | P3 | `verify_recon.py:332` vs `shared_release_receipt.py:578-580` | 双写分叉：取重放截止块，生产侧用 `or`（0 会掉进 fallback）、消费侧用 `is None` 判断 |

### PARTIAL-1（P3）：说明件的语义充数

- **复现**：`cd /private/tmp/g2probe && python3 f09_probe.py`，看 C14、C16 两行。
- **构造**：C14 把 `findings[0].explanation` 换成 `"." * 40`；C16 把 conclusion 写成"本次差异尚未查明，不能断言重放数据经查证无误，需继续排查"。两者都过消费面。
- **最强反驳（为什么不是误报）**：任务书 (b) 点名了"explanation 空洞充数"这一向量，它确实成立——C13 证明设计者认真做了不可见字符防线（零宽、全角空格、软连字符全被拦），但"可打印字符重复"这一类没拦住。
- **为什么只判 P3 不判 BREACH**：这需要人**主动伪造**一份说明，而说明里有 investigator 署名、UTC 时间戳、输入哈希三重留痕，事后可追责；且 C16 这类语义造假在原理上不可机器闭合（40 个真实汉字写的胡话同样绕得过任何长度阈值）。
- **可选加固（低成本、只对 C14 那一类有效）**：对 explanation 增加"去重后字符数下限"或拒绝单一字符高频重复；C16 建议不修，作为已知边界写进文档。

### PARTIAL-2（P2）：抽查覆盖面无下限

- **复现**：`cd /private/tmp/g2probe && python3 f07_probe.py`（看 A5）、`python3 f07b_probe.py`（看 B22）。
- **构造**：A5 直接把 `requested_top_n` 设成 1；B22 把大额筹码放进 ZERO/DEAD 让它们占满 top2，真大户被挤出 `top_n=3` 的窗口。两者都过消费面。
- **最强反驳**：`supply_closure` 只保证总量闭合（balance_sum == mint == nominal），**藏不掉总量，但藏得掉"某个地址的余额是否与链上一致"**。如果重放把 A 的币记到 B 名下，总量仍然闭合，而逐地址 RPC 核对若不覆盖这两个地址就发现不了——这正是庄家识别最吃紧的地方。
- **为什么只判 P2 不判 BREACH**：`requested_top_n` 明文记在收据里，人工复核一眼可见；默认值 15；且这不是本次五刀引入的回归（F-07 之前同样没有下限），属于纵深加厚项。
- **可选加固**：消费面对 `requested_top_n` 设下限（如 ≥15），或改为"必须覆盖到累计占比 X% 为止"。

### PARTIAL-3（P3）：双写分叉——案内绝对路径 evidence_ref

- **复现**：见本报告 §六.2 F16 一行；一次性脚本已跑，输出为
  `producer(verify_recon) = reject(GMGN 查证说明 evidence_refs 必须是安全相对路径)` / `consumer(shared_release) = accept`。
- **构造**：合法 note，把 `findings[0].evidence_refs[0].path` 写成案内文件的**绝对路径**（size/sha256 均正确）。
- **最强反驳**：这是刻意双写的两份实现，任务书 (d) 要求找判定分叉——确实存在这一个。
- **为什么只判 P3**：方向是"生产侧更严、消费侧更宽"，攻击者要利用它必须手写收据绕过生产者；即便消费侧接受，`_bound_case_ref` 仍强制该文件在案根内、非 symlink、size+sha256 匹配，拿不到任何伪造收益。实际影响是可移植性：用绝对路径写的说明，案目录一搬家就失效。
- **可选加固**：消费侧对 evidence_refs 也显式拒绝绝对路径，与生产侧对齐。

### PARTIAL-4（P3）：双写分叉——截止块的 `or` 与 `is None`

- **复现**：`cd /private/tmp/g2probe && python3 f07b_probe.py`，看 B12 行（该向量本身 blocked）。
- **构造**：`replay_stats` 写 `max_block=0` 且 `last_block=真值`。生产侧 `stats.get("max_block") or stats.get("last_block")` 会把 0 当假值掉进 fallback 取 last_block；消费侧 `if stats_end is None` 只在缺失时 fallback，取到 0。
- **最强反驳**：这是同一个语义在两处写了两种取法，属实的实现分叉。
- **为什么只判 P3**：仅在 `as_of_block == 0`（冻结块＝创世块）这种不现实的场景下两侧才会理解不同，且方向仍是生产侧更严，B12 实测被拦。
- **可选加固**：两处统一为 `is None` 判断。

---

## 八、复核边界（没覆盖到的面，如实交代）

1. **末刀 861a234（中心登记）未做独立攻击**：该刀是把 4 个测试挂进 `run_all`（SUITE 105）并登记契约 CT-RECON-01/02/03，本身不含安全断言。我核对了它改的是登记面而非判定面，但**没有独立重跑全量 suite**（那是被测对象的自证，且耗时长）；"105 全绿"这一说法我未复验。
2. **未做真实 RPC 纵切片**：全部向量为离线夹具，没有连真实节点跑 loopback。F-04 的 EIP-1898 锚定在真实节点上的行为（例如节点不支持 blockHash selector 时是否 fail-closed）未实证。
3. **Solana 侧只做了代码面审读**：`_validate_anchor_receipt` 与 solana supply 分支我通读了逻辑，但未构造 Solana 夹具做变异（本次五刀主要落在 EVM 侧）。
4. ~~**`_validate_time_receipt`（time 那一查）未做变异攻击**~~ → **已补，见 §八·补充**。原判断"结构与 balance 侧同构且同等严格"**被自己的补充轮推翻**：重算部分确实同等严格，但 plan 权威性验证缺失，打出 7 个 BREACH。教训留档：读代码得出的"同构即同强"结论不可信，必须真造夹具打一遍。
5. **未验证发布闸上游**：我打的是 `validate_reconciliation_check` / `validate_reconciliation_report` / `validate_evm_observation_bundle` 三个消费面入口，没有从 `audit_release` / `handoff` 完整走一遍端到端发布流程。
6. **并发与文件系统竞态未测**：receipt_kernel 的 supersede 锁、publish_txn 回滚等路径不在本次范围。
7. **time 轮的 anchor_plan 生产端未攻**：补充轮打的是消费面。生产侧 `load_validated_plan` 的 8 项绑定我逐条读过并用作"消费侧应当补齐什么"的对照，但没有独立攻击 `anchor_plan.py` 本身。

---

## 八·补充：time 查攻击轮（50 向量 / 7 BREACH / 2 PARTIAL）

**不变量**：`time-spotcheck/v3` 的消费面必须从绑定的输入实物（plan / plan_receipt / input / transcript）独立重算，而不是只看自报计数。

探针：`/private/tmp/g2probe/f07d_time.py`（复现：`cd /private/tmp/g2probe && python3 f07d_time.py`）

夹具说明：完全离线自造一份 time 证据包——merged input、anchor-plan/v2、anchor-plan-receipt/v2（producer 用真实的 `scripts/lib/anchor_plan.py`）、time-spotcheck/v3 收据、transcript。默认 3 个点位（2 个 balance 点 + 1 个 tx 点）全 OK。

### 8·补.1 绑定链面（H1–H10）—— 7 个 BREACH 中的 6 个出在这里

| 编号 | 攻击面 | 构造方法 | 预期 | 实际 | 判定 |
|---|---|---|---|---|---|
| H0 | 基线 | 3 点全 OK 的自造证据包 | 接受 | 接受 | 基线有效 |
| H1 | **plan 换绑** | plan 砍成 1 个点（rows/transcript 同步只留 1 条），plan_receipt 保持"3 点"签发 | 拒 | **接受** | **BREACH-T1** |
| H2 | **plan 换绑** | 同 H1，且把 plan_receipt.probe_count 显式写成 3（与 plan 的 1 点公然矛盾） | 拒 | **接受** | **BREACH-T2** |
| H3 | **plan 换绑** | plan_receipt.output 指向另一份 plan（path/size/sha256 全不符） | 拒 | **接受** | **BREACH-T3** |
| H4 | plan 校验 | plan.schema 写成 `attacker-freestyle/v9` | 拒 | **接受** | **BREACH-T4** |
| H5 | plan 校验 | plan.target 写成另一条链的另一个代币（bsc / 0xfff…） | 拒 | **接受** | **BREACH-T5** |
| H6 | input 绑定 | plan_receipt.input_identity 换绑别的 input | 拒 | 拒：bound input differs from time receipt input | blocked |
| H7 | input 绑定 | plan.input 换绑别的 input | 拒 | 拒：plan input differs from time receipt input | blocked |
| H8 | 签发有效性 | plan_receipt 是 FAIL | 拒 | 拒：schema/verdict invalid | blocked |
| H9 | 签发有效性 | plan_receipt schema 降版 v1 | 拒 | 拒 | blocked |
| H10 | **签发身份** | plan_receipt.producer 换成 `time_spotcheck.py`（非 anchor_plan.py） | 拒 | **接受** | **BREACH-T6** |

### 8·补.2 plan multiset 与点位对应（H11–H19）

| 编号 | 攻击面 | 构造方法 | 预期 | 实际 | 判定 |
|---|---|---|---|---|---|
| H11 | 重复点 | plan 有同一点 ×2，rows 只给 1 行 | 拒 | 拒：rows do not correspond one-to-one | blocked |
| H12 | 重复点 | plan 同一点 ×2，rows 给 2 行 | 接受 | 接受 | 合法（multiset 计数相等） |
| H13 | 顺序 | rows 顺序与 plan 不同（transcript 同步重排） | 接受 | 接受 | 合法（Counter 比较，顺序无关；transcript 仍逐笔绑 rows） |
| H14 | 漏查 | rows 漏掉一个 plan 点 | 拒 | 拒 | blocked |
| H15 | 加塞 | rows 多一个 plan 外的点 | 拒 | 拒 | blocked |
| H16 | 类型挪移 | balance 点伪装成 tx 行 | 拒 | 拒 | blocked |
| H17 | 类型挪移 | tx 点伪装成 balance 行 | 拒 | 拒 | blocked |
| H18 | tx 单点变异 | tx 行 from 改成别的地址 | 拒 | 拒 | blocked |
| H19 | tx 单点变异 | tx 行 to 改成别的地址 | 拒 | 拒 | blocked |

### 8·补.3 tx / balance 行与 transcript 逐笔对应（H20–H32）

| 编号 | 攻击面 | 构造方法 | 预期 | 实际 | 判定 |
|---|---|---|---|---|---|
| H20 | tx 值 | plan+row 的 expect_raw 一起注水到 999，transcript 仍是 333 | 拒 | 拒：tx row 0 differs from transcript | blocked |
| H21 | tx 日志 | transcript 日志的 address 换成别的代币合约 | 拒 | 拒 | blocked |
| H22 | tx 日志 | transcript topic0 换成非 Transfer 事件 | 拒 | 拒 | blocked |
| H23 | tx 块 | row.receipt_block 与 transcript 的 blockNumber 不符 | 拒 | 拒 | blocked |
| H24 | tx 块 | plan 的 tx 点不指定 block（block=None） | — | 接受 | **PARTIAL-T2**（放弃块校验） |
| H25 | balance 值 | row.chain_raw ≠ transcript 解出的值 | 拒 | 拒 | blocked |
| H26 | balance 值 | row.diff_raw 未重算 | 拒 | 拒 | blocked |
| H27 | 规范化 | expect_raw 用前导零 `0111` | 拒 | 拒：must use canonical integer spelling | blocked |
| H28 | balance 块 | transcript 块高与 row.block 不符 | 拒 | 拒：transcript params mismatch | blocked |
| H29 | balance 址 | transcript 查的是别的地址 | 拒 | 拒 | blocked |
| H30 | transcript | seq 不连续 | 拒 | 拒 | blocked |
| H31 | transcript | 条数 ≠ rows | 拒 | 拒 | blocked |
| H32 | transcript | 与 rows 整体错位（右移一位） | 拒 | 拒 | blocked |

### 8·补.4 六计数与结构面（H33–H49）

| 编号 | 攻击面 | 构造方法 | 预期 | 实际 | 判定 |
|---|---|---|---|---|---|
| H33 | 计数注水 | points = 99 | 拒 | 拒：counters differ from rows | blocked |
| H34 | 计数注水 | balance_points = 99 | 拒 | 拒 | blocked |
| H35 | 计数注水 | tx_points = 99 | 拒 | 拒 | blocked |
| H36 | 计数注水 | exact_match = 99 | 拒 | 拒 | blocked |
| H37 | 计数谎报 | 实有 MISMATCH 行却把 mismatch 谎报 0 | 拒 | 拒 | blocked |
| H38 | 夹带 | PASS 收据夹带 MISMATCH 行（计数如实） | 拒 | 拒：PASS receipt contains MISMATCH/RPC_ERR row | blocked |
| H39 | 夹带 | PASS 收据夹带 RPC_ERR 行 | 拒 | 拒 | blocked |
| H40 | bool 混入 | 六计数用 `True` 而非 `1`（rows 恰好 1 行） | 拒 | **接受** | **BREACH-T7**（实为 P3，见下） |
| H41 | 字段缺失 | 删除 rows 字段 | 拒 | 拒 | blocked |
| H42 | 空值 | rows = `[]` | 拒 | 拒 | blocked |
| H43 | 字段缺失 | 删除 mismatch 计数 | 拒 | 拒 | blocked |
| H44 | 绑定缺失 | 删除 inputs.transcript | 拒 | 拒 | blocked |
| H45 | 绑定缺失 | 删除 inputs.plan_receipt | 拒 | 拒 | blocked |
| H46 | 枚举 | row.status 用未知值 `SKIPPED` | 拒 | 拒 | blocked |
| H47 | 枚举 | row.type 用未知值 | 拒 | 拒 | blocked |
| H48 | schema | v2 收据混入正式面 | 拒 | 拒：expected time-spotcheck/v3 | blocked |
| H49 | 模式 | mode = exploration | 拒 | 拒：must be formal | blocked |

### 8·补.5 BREACH 定级与修复

**BREACH-T1/T2/T3/T4/T5/T6 —— 同一根因：消费侧未验 plan 的权威性**

- **级别：P1（偏 P0，见下方判断依据）**
- **位置**：`scripts/report/shared_release_receipt.py:919-940`（`_validate_time_receipt` 开头的绑定段）
- **复现**：`cd /private/tmp/g2probe && python3 f07d_time.py`，看 H1/H2/H3/H4/H5/H10 六行
- **危害**：time 这一查是正式发布四查之一。攻击者可以把抽查点位从 N 个砍到 1 个自选的点（H1/H2），或直接拿一份为别的代币/别的 plan 签发的 plan_receipt 来配自己写的 plan（H3/H5），甚至用任意仓库脚本当 plan 签发者（H10）。结果是：**时间维度的抽查形同虚设，而收据表面上完全合规、四查全 PASS**。
- **对比证据（这不是我苛求）**：生产侧 `scripts/lib/time_spotcheck.py:68-118` 的 `load_validated_plan` 对同一组文件做了 8 项绑定——plan.target==receipt.target、plan.producer==receipt.producer、plan.input==receipt.input_identity、input_manifest 绑定、**receipt.output 的 path/size/sha256 必须就是这份 plan 文件**、plan_schema、generated_at 一致、**probe_count == 实际点位数**。消费侧只抄了其中第 3 项（input_identity）。**同一套语义，两侧强度悬殊。**
- **最强反驳（为什么不是误报）**：三点。① 消费侧重验的全部意义就是"不信生产侧自报"——整套 receipt kernel / validator 双写体系（`receipt_validate.py` 开头明写"不 import receipt_kernel，重新实现一遍，这样发射端的 bug 不能机械地自证"）的设计前提就是消费面是最后一道闸；② H10 证明连"拿一份真实签发件"都不需要，攻击者可离线自造全套；③ 其余三查（balance/supply/supply_truth）都做了实物级绑定（replay_stats 三查同源、observation bundle 的 N-2 绑定），唯独 time 面把标准答案的来源放行了，是明显的不对称。
- **P0 还是 P1 的判断依据**（交融合方定夺）：若采信"手写收据属于威胁模型内"（我倾向此说，理由见上①），则是 **P0**；若认为正式流程必经生产者、手写收据不在威胁模型内，则降为 **P1**（上游 `load_validated_plan` 兜得住）。无论哪种，**都必修**。
- **修复建议**（消费侧补齐，逐条对齐生产侧）：
  1. `plan_receipt["output"]` 用 `_bound_case_ref` 解析，必须解析到 inputs.plan 的同一个文件，且 size/sha256 相等 ← 关掉 T1/T3
  2. `plan_receipt["probe_count"] == len(matrix_points) + len(forced_points)` ← 关掉 T2
  3. `plan_receipt["producer"]["path"] == "scripts/lib/anchor_plan.py"`（用现成的 `repo_ref_ok` 走白名单+哈希）← 关掉 T6
  4. `plan["schema"] == "anchor-plan/v2"` ← 关掉 T4
  5. `canonical_target(plan["target"]) == canonical_target(target)` ← 关掉 T5
  6. 顺带：`plan["generated_at"] == plan_receipt["generated_at"]`
- **回归护栏建议**：上述每条各加一个负测（先红后绿），并把 H1/H3/H10 三个夹具作为固化用例。

**BREACH-T7（H40）—— 六计数可用 bool 冒充 int**

- **级别：P3**（编号上算 BREACH 是因为"预期拒却接受"，但**无实际收益**，不阻断）
- **位置**：`scripts/report/shared_release_receipt.py:990-996`
- **原因**：Python 里 `True == 1` 成立，六计数的比较没有像 balance 面那样加 `not isinstance(x, bool)`（对比 `:639` 的 `requested_top_n` 就做了）。
- **为什么无收益**：这些计数仍必须等于从 rows 重算出的真值，`True` 只在计数恰为 1 时能蒙混，不能用来隐藏任何行。
- **修复**：六计数比较前加 bool 拒绝，与 `:639` 对齐。

**PARTIAL-T1（P2）：plan 点位数量本身无下限**

- 即使修好 T1–T6，只要权威 plan 本身只有 1 个点，time 查也只查 1 个点。plan 的点位规模由 `anchor_plan.py` 的 per_cell/edge_max 参数决定，消费面不设下限。与主轮 PARTIAL-2（balance 面 top_n 无下限）同族，建议一并考虑。

**PARTIAL-T2（P3）：tx 点可不指定块（H24）**

- 位置：`shared_release_receipt.py:915`（`_tx_transcript_matches` 的 `block_ok`）。plan 的 tx 点若 `block=None`，则"这笔转账发生在哪个块"不被校验，只验事件五元组。修好 plan 权威性后危害有限，建议在 `anchor_plan.py` 侧强制 tx 点必带 block，或消费侧对 `block is None` 显式拒绝。

---

## 九、总判定

**BLOCK —— 先修 time 面 plan 绑定，再进融合。**

- 向量总数 **184**；BREACH **7**；PARTIAL **6**
- BREACH 全部集中在 F-07 的 time 那一查，且六条同源——**按上面 6 条修复建议改一处 `_validate_time_receipt`，T1–T6 可一次关闭**，T7 再加一行 bool 拒绝
- 其余四刀（F-04 / F-10 / F-09 / F-07 的 balance+supply 面）在 134 个向量下全部守住，**本身没有阻断问题**

处理优先级建议：

| 优先级 | 项 | 说明 |
|---|---|---|
| **必修（阻断）** | BREACH-T1~T6 | 消费侧补 6 项 plan 绑定，配负测 |
| 顺手修 | BREACH-T7、PARTIAL-3、PARTIAL-4、PARTIAL-1 的 C14 半 | 都是几行的类型/一致性对齐 |
| 下轮排期 | PARTIAL-2、PARTIAL-T1 | 抽查覆盖面下限（balance top_n 与 plan 点位数同族问题） |
| 建议不修 | PARTIAL-1 的 C16 半、PARTIAL-T2 | 语义真伪不可机器闭合，写进文档作已知边界 |

另请注意 §八 复核边界第 1、2、3、5、6、7 条——末刀 SUITE 105、真实 RPC 纵切片、Solana 侧变异、端到端发布流程、并发竞态、anchor_plan 生产端，本轮均未覆盖。

---

*复核员：独立红队（Opus 5）。探针脚本保留在 `/private/tmp/g2probe/`：`fixtures.py`（自洽基线夹具生成器）、`f04_probe.py`、`f07_probe.py`、`f07b_probe.py`、`f07c_crossdepth.py`、`f07d_time.py`（time 补充轮）、`f09_probe.py`、`f10_probe.py`、`f07e_round2.py`（round2 复验）。仓库 tracked 文件零改动，全程无 git 写操作。*

---

# round2 复验（消化轮 `55f2c44` 之后）

- 复核对象：`55f2c44` 的 `_validated_time_plan_authority`（12 项绑定平移）+ 六计数 bool 拒绝
- 探针：`/private/tmp/g2probe/f07e_round2.py`（复现：`cd /private/tmp/g2probe && python3 f07e_round2.py`）
- 新增向量 **25**（重放 8 + 边界外 17）；累计 **209**
- **结果：round1 的 7 条 BREACH 全部关闭，round2 无新 BREACH。总判定 BLOCK → CONDITIONAL。**

## 十、方法说明：为什么先造 J0 基线

我原 round1 的 time 夹具没有 `plan.producer`、`plan.input_manifest`、`plan_receipt.inputs.input_manifest` 这些字段——直接拿旧夹具重跑，新代码会因**字段缺失**而拒，那样得到的"全部 blocked"是假象，什么都证明不了。

所以 round2 先重建了一份**在新代码下能通过的完整权威链基线 J0**（12 项绑定全部满足，3 个点位全 OK）。J0 实测 **ACCEPTED** —— 有了这个前提，后面每一条 blocked 才能归因到攻击本身。

## 十一、重放 round1 的 BREACH 向量（8 向量，全部关闭）

| 编号 | 原 BREACH | 重放结果 | 拦截点 |
|---|---|---|---|
| J0 | （基线） | ACCEPTED | 完整权威链可通过，前提成立 |
| H1 | T1 plan 砍成 1 点、签发件仍报 3 点 | **blocked** | `probe_count differs from consumed plan` |
| H2 | T2 plan 1 点 + probe_count 谎报 3 | **blocked** | 同上 |
| H3 | T3 签发件 output 指向另一份 plan | **blocked** | `signed plan output file invalid or escapes case root` |
| H4 | T4 plan.schema 随便写 | **blocked** | `plan schema must be anchor-plan/v2` |
| H5 | T5 plan.target 指向别的币 | **blocked** | `plan target differs from signed receipt target` |
| H6 | （round1 本就 blocked，调度方清单多列了一条） | **blocked** | `plan input identity differs from signed receipt` |
| H10 | T6 签发者冒充（用 time 脚本当 plan 签发者） | **blocked** | `producer/runner path is not whitelisted` |
| H40 | T7 六计数用 bool `True` | **blocked** | `counter points must be an integer, not a boolean` |

**结论：round1 的 T1–T7 七条 BREACH 逐条复验关闭**（H6 本轮一并验，保持 blocked）。修复方向与我的建议一致，且做得更彻底——我提了 6 条，实现平移了 12 条（多做了 `plan.producer == 签发件 producer`、`input_manifest` 双向绑定、`identity_path == input_path` 对象身份三项）。

## 十二、边界外再一步：攻新函数本身（17 向量）

| 编号 | 攻击面 | 构造方法 | 预期 | 实际 | 判定 |
|---|---|---|---|---|---|
| I1 | **信任根** | 全套离线自造权威链：plan + plan_receipt 全部字段自洽，plan 只放 1 个自选点 | 拒 | **接受** | **PARTIAL-R2A**（见下） |
| I2 | 白名单归一 | producer.path 写 `./scripts/lib/anchor_plan.py` | 拒 | 拒：not whitelisted | blocked |
| I3 | 白名单归一 | producer.path 写 `scripts/lib/../lib/anchor_plan.py` | 拒 | 拒：envelope invalid（traversal） | blocked |
| I4 | 类型 | 六计数用 float `1.0`（bool 已拒，float 呢） | 拒 | 拒：must be an integer | blocked |
| I5 | 类型 | probe_count 用 float `3.0` | 拒 | 拒：probe_count differs | blocked |
| I6 | 路径身份 | 签发件 output 指向**同内容**的副本 `plan_copy.json` | 拒 | 拒：signed output is not the consumed plan object | blocked |
| I7 | 别名 | plan 与签发件 target 都用 `ethereum`，time 收据用 `eth` | — | 接受 | **合法**（我预期设错，见下） |
| I8 | 覆盖面灌水 | 3 个**完全相同**的点凑够 probe_count=3 | — | 接受 | **PARTIAL-R2B**（前瞻） |
| I9 | 实义字符 | generated_at 两边都写 `"   "`（三个空格） | 拒 | **接受** | **P3-R2C** |
| I10 | 类型 | matrix_points = None | 拒 | 拒：plan matrix_points invalid | blocked |
| I11 | 路径 | 签发件 output 用案内绝对路径 | 接受 | 接受 | 合法（同 round1 PARTIAL-3 同族） |
| I12 | 绑定 | plan.producer 哈希与签发件不符 | 拒 | 拒：plan producer differs | blocked |
| I13 | 绑定 | 签发件缺 inputs.input_manifest | 拒 | 拒：must bind path/size/sha256 | blocked |
| I14 | 绑定 | plan.input_manifest 哈希与签发件不符 | 拒 | 拒：input manifest differs | blocked |
| I15 | 降版 | 签发件 plan_schema 降到 v1 | 拒 | 拒：plan_schema mismatch | blocked |
| I16 | 兼容字段 | plan.final_block 与 target.as_of_block 不符 | 拒 | 拒：compatibility target fields diverge | blocked |

### PARTIAL-R2A（P2）：修复关掉了"混搭"，但关不掉"全套自造"

- **现象**：I1 里我离线自造了 plan 与 plan_receipt 的**全部**字段（producer 写 `scripts/lib/anchor_plan.py` 并抄上仓库里那个文件的真实哈希），plan 里只放 1 个自选点位，12 项绑定全部自洽 → 通过。原 T1 想达到的效果（把 time 抽查砍到 1 个自选点）仍可达成。
- **但这不是消化轮的锅，修复确实有效**，理由要说清楚：
  - `repo_ref_ok` 校验的是"producer 字段声明的脚本在白名单里、且该脚本文件的哈希对得上"——这是一条**声明**，不是密码学**签名**。整个 receipt 体系里没有任何一份收据是防伪造的（我 round1 判 F-04/F-09/F-10 为 PASS 时，用的基线夹具同样全是自造的）。
  - 修复的实质收益是**把攻击门槛从"拿到任意一份真实签发件即可混搭"提升到"必须伪造整条签发链"**。前者在"攻击者无法伪造签发件"这个更严格的假设下依然成立，后者不成立。这是实质性提升，T1 判为已关闭是站得住的。
- **剩余风险**：这条与 round1 的 **PARTIAL-T1（plan 点位数量本身无下限）实为同一件事**，round2 予以确认并升格描述：plan 说查几个点就查几个点，**没有任何外部事实约束它**，也**没有纵深兜底**。对比 balance 面——那里的"标准答案"（balances.json）被 replay_stats 三查同源、supply_truth 的 decide 重算、observation bundle 的 N-2 绑定交叉锁死（主轮 E2/E4/E5 实证），伪造一处就炸；plan 没有任何等价的交叉锁。
- **建议**（不阻断本次融合，下一轮排期）：给 plan 点位规模设可核验的下限或与案子事实挂钩，例如按 `date_range` 天数/`per_cell` 推出应有点数并在消费侧重算，或把 anchor_plan 的参数纳入 `audit_input_manifest` 一并锁定。

### PARTIAL-R2B（P2，前瞻性）：probe_count 可被重复点灌水

- **现象**：I8 用 3 个**完全相同**的点位凑满 `probe_count=3`，rows 给 3 行相同记录，通过。表面"抽查了 3 个点"，实际只覆盖 1 个不同点位。
- **为什么现在无独立危害**：既然 I1 证明 plan 可自造，攻击者直接写 1 个点即可，不必灌水。
- **为什么仍要记**：这是对**未来修复**的前瞻攻击——一旦按 PARTIAL-R2A 的建议加"点位数下限"，重复点填充就是绕过那个下限的现成手法。**修下限时必须用去重后的点位数（`len(set(...))`），不能用 `len()`。**

### P3-R2C（I9）：generated_at 只验非空，不验实义字符

- **位置**：`shared_release_receipt.py`，`_require(isinstance(generated_at, str) and bool(generated_at) and ...)`
- `bool("   ")` 为真，所以三个空格能过。无安全危害（该字段只用于两边一致性比对），但与 F-09 面对人工文本一律走 `_meaningful_text` 的严格标准不一致。
- **建议**：改用 `_meaningful_text(generated_at)`，或至少 `generated_at.strip()`。

### I7 说明：这是我的向量预期设错，不是缺陷

plan 与签发件的 target 都写 `ethereum`、time 收据写 `eth` 时通过——这是**正确行为**：`plan.target == plan_receipt.target` 走全等（两边一致），跨到 time 收据时走 `canonical_target` 归一（`ethereum` 是注册表认可的 `eth` 别名）。如实留档：本向量应判"合法接受"。附带一条 P3 观察——生产侧 `time_spotcheck.py` 主流程另有 `plan_chain != a.chain` 的字面比较，对别名比消费侧更严，属无害的双写差异。

## 十三、round2 总判定

**CONDITIONAL —— 可交付（BLOCK 解除）。**

| 项 | round1 | round2 |
|---|---|---|
| 累计向量 | 184 | **209** |
| BREACH | 7（全在 time 面） | **0 新增；原 7 条逐条复验关闭** |
| PARTIAL | 6 | **8**（新增 R2A、R2B；R2A 与原 PARTIAL-T1 合并计为同一件事的确认） |

- 消化轮 `55f2c44` 的修复**有效且超出我的建议**（我提 6 条，实现平移 12 条），重放 8 向量全部被拦，且拦截理由逐条对得上预期拦截点
- 边界外 17 个新向量中 13 条被拦；4 条通过里，1 条是我预期设错（I7）、1 条是合法路径形态（I11）、2 条归入 PARTIAL（R2A 信任根边界、R2B 前瞻灌水）
- **剩余待办（不阻断）**：PARTIAL-R2A/R2B（plan 点位规模无外部约束，修下限时须用去重计数）、P3-R2C（generated_at 实义字符），以及 round1 未消化的 PARTIAL-1/2/3/4

## 十四、round2 复核边界

1. 本轮只打 time 面。消化轮 done 报告称"balance/supply/anchor 三分支同族排查零缺口"，**我未独立复验该结论**——建议下一轮针对这三个分支的"标准答案来源"各打一轮（尤其 anchor 那一查的 output 绑定）。
2. 未复验 SUITE 105 全绿、未跑固化的回归负测（按调度方要求不信其自报，全部结论来自我自己的探针）。
3. §八 复核边界的其余各条（真实 RPC 纵切片、Solana 侧、端到端发布流程、并发竞态、anchor_plan 生产端）本轮仍未覆盖。

---

*round2 复核员：独立红队（Opus 5）。探针 `/private/tmp/g2probe/f07e_round2.py`。仓库 tracked 文件零改动，无 git 写操作。*
