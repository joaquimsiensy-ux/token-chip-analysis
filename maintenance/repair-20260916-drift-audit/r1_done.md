# 施工 R1：完成

按 `workorder_r1.md` v3 §0–§4 完成 23 个施工编号、66 处指定替换，修改 20 个白名单既有文件；另新建本报告。D1 按 §3 暂缓。§1.2 所列命令全部 exit 0；无契约 needle 冲突。

## 1. 开工基线与锚点校验

内容基线：`444544360179d5080657aafd5ad60a78fe89e9b3`；VERSION 7.1.1。施工 HEAD：`402b5710bff9de039c4ac94bc5a23fc68ee7dc68`，完工复查未变化。

工单 SHA-256：`147eaf0b186b73b8743126b8aacaa876a718bd03fc1dbf4cec0c6597da768f23`，写入前与完工时均核对一致。

以下为 §0.1 实际执行命令及原始 stdout；三条命令均 exit 0。第一、第三条输出为空（0 字节），开工工作区干净，指定范围相对内容基线无差异。

```console
$ git status --short
$ git rev-parse HEAD
402b5710bff9de039c4ac94bc5a23fc68ee7dc68
$ git diff --stat 4445443 HEAD -- SKILL.md references scripts commands-staging VERSION
```

在冻结改前文本上逐项实际执行 `grep -n -F -- <锚文本>`：66/66 均 exit 0、仅命中 1 行，且该行号与工单一致；每个锚文本出现次数也均为 1。整段替换另核验结束标记、缩进及范围边界。所有锚点通过后才写入，各文件按改前位置从后向前替换；写入前后用 SHA-256 校验冻结输入和预定结果。

## 2. §1.1 字节数实测

| 范围 | 改前字节 | 改后字节 | 净变化 | 验收 |
| --- | ---: | ---: | ---: | --- |
| `SKILL.md` | 8024 | 8021 | -3 | PASS：不大于 8024 |
| `references/*.md`、`references/casebook/*.md`、`references/labels/*.md` | 930850 | 929850 | -1000 | PASS：严格小于 930850 |
| `commands-staging/*.md` | 8798 | 8798 | 0 | PASS：不大于 8798 |

统计使用上述 glob 对应文件的 `stat().st_size` 求和，与拼接后的字节数一致；`references/attic.md` 只取大小，未读取内容。`references` 净减 1,000 字节。

## 3. 逐条改前 → 改后 diff

以下各编号分别以冻结改前文本为起点展示其指定替换，hunk 行号按该编号单独应用计算；其他编号造成的最终行偏移见工作区完整 diff。

### D2

```diff
--- a/references/data-pipeline-evm-recon.md
+++ b/references/data-pipeline-evm-recon.md
@@ -152,3 +152,3 @@
-python3 scripts/lib/time_spotcheck.py --plan anchor_plan.json --rpc <独立archive节点> \
-    --chain <eth|bsc|base|arbitrum> --token 0x标的 --out time_spotcheck.json \
-    --final-block <数据截止块>
+python3 scripts/lib/time_spotcheck.py --plan anchor_plan.json --input <生成plan所用的merged转账数据> \
+    --rpc <独立archive节点> --chain <eth|bsc|base> --token 0x标的 \
+    --out time_spotcheck.json --final-block <数据截止块>
```

### D3

```diff
--- a/references/data-pipeline-evm-sources.md
+++ b/references/data-pipeline-evm-sources.md
@@ -60 +60 @@
-### 8.1 全量转账双通道拓扑（与 BSC 经验相反：高峰期 Alchemy 是主力）
+### 8.1 全量转账通道实测（历史；Alchemy 已除名正式通道，正式 CSV 资格见 data-pipeline-evm-channels §1 末段）
@@ -63,2 +63 @@
-- **Alchemy base-mainnet getAssetTransfers 实测 ~230 条/s 稳定零限流**（代理经 `CHIP_PROXY`/`--proxy` 解析，见 `scripts/lib/proxy_config.py`；免费层 30M CU 拉 239 万条余量充足）——Base 高峰期 Alchemy 反而是主力通道（PING，07-17）
-- **分段接力法（双通道 2:1 提速）**：HyperSync 负责发射段（旧块），Alchemy 按 fromBlock/toBlock 切成多个块段并行接力拉近段；fetch_alchemy.py 已支持 `--config/--from-block/--to-block`（v2.26 参数化）（PING，07-17）
+- **Alchemy base-mainnet getAssetTransfers 实测 ~230 条/s 稳定零限流**（代理经 `CHIP_PROXY`/`--proxy` 解析，见 `scripts/lib/proxy_config.py`；免费层 30M CU 拉 239 万条余量充足）——仅探索采集可用，不产正式收据（PING，07-17）
```

### D4

```diff
--- a/references/data-pipeline-solana-capture.md
+++ b/references/data-pipeline-solana-capture.md
@@ -48 +48 @@
-1. **锚点法演变重建（免全量 SQD，`scripts/solana/build_evolution.py`）**：不重放每一笔，而是——①`fetch_pool_sigs.py` 拉主池全史签名；②等距抽签名做**池子余额锚点**（`decode_txs_v2.py --pool <池owner>` 每笔落 `pool_balance`）；③核心实体（top 大户 + 离场盈利榜 + 上游中转）用 `whale_deep.py` 拉 ATA 级全流水；④`build_evolution.py` 在时间点插值：各实体持仓从其逐笔流水累积、流动性池用锚点曲线、散户=总供应−已知−池−销毁残差。产出图1/图2 数据。**精度声明**：中小散户是残差估算，量级正确、单点精度有限，报告局限性须写明。
+1. **锚点法演变重建（免全量 SQD，`scripts/solana/build_evolution.py`）**：不重放每一笔，而是——①`fetch_pool_sigs.py` 拉主池全史签名；②等距抽签名做**池子余额锚点**（`decode_txs_v2.py --pool <池owner>` 每笔落 `pool_balance`）；③核心实体（top 大户 + 离场盈利榜 + 上游中转）用 `whale_deep.py` 拉 ATA 级全流水；④`build_evolution.py` 在时间点插值：各实体持仓从其逐笔流水累积、流动性池用锚点曲线、散户=总供应−已知−池−销毁残差。产出 `sol-anchor-rows` 序列，仅探索辅助、不进正式编译链（正式序列走 replay_edges/replay_duck）。**精度声明**：中小散户是残差估算，量级正确、单点精度有限，报告局限性须写明。
```

### D5

```diff
--- a/references/data-pipeline-evm-recon.md
+++ b/references/data-pipeline-evm-recon.md
@@ -13 +13 @@
-2. **全网余额和=0**：所有地址重建余额求和应为零（mint/burn 计入），不为零即漏了转账段。（SIREN，07）
+2. **全网余额和=mint_total**：重建余额按 raw integer 求和等于铸币总量（sink 收方照加），不等即对账失败，须排查数据或重放口径。（SIREN，07）
```

### D5b

```diff
--- a/references/playbook-supply-recon.md
+++ b/references/playbook-supply-recon.md
@@ -41 +41 @@
-- 全网余额和 = 0（mint 计负、burn 计正后逐笔累加）（SIREN，07）
+- 全网余额和 = mint_total（sink 收方照加；定义见 data-pipeline-evm-recon §5 第 2 条）（SIREN，07）
```

### D6

```diff
--- a/references/playbook-supply-recon.md
+++ b/references/playbook-supply-recon.md
@@ -42 +42 @@
-- 重建余额 vs GMGN top10 逐个对比，要求 **10/10 精确到个位**；实测数据到 97% 时对账 4/10 MISMATCH、补扫完成后 10/10 全过——证明该 gate 能兜住数据缺口（OPN，07）
+- 按 verify_recon 所选 top-N 与冻结块 RPC balanceOf 逐地址精确对账，差异或观测失败均阻断；GMGN top10 差异 ≥0.15pp 时记黄灯，并在发布前绑定合格查证说明（data-pipeline-evm-recon §5 第 1 条；OPN，07；08-15 黄灯制）
```

### D7

```diff
--- a/references/playbook-entity-cluster-tiering.md
+++ b/references/playbook-entity-cluster-tiering.md
@@ -31 +31 @@
-一个实体 = 可合并为单一持仓集群的全部地址。**合并口径含全部疑似关联地址（无论证据程度），同一时刻合并计算，禁止把各地址不同时刻的峰值跨时刻相加（会高估）**；单个成员不必各自过线。按下表打标签：
+一个实体 = 可合并为单一持仓集群的全部地址。**合并口径按 strict／expanded 双边界（见本册"历史静置仓反向扫描后的双边界峰值"条），同一时刻合并计算，禁止把各地址不同时刻的峰值跨时刻相加（会高估）**；单个成员不必各自过线。按下表打标签：
```

```diff
--- a/references/analyze-workflow.md
+++ b/references/analyze-workflow.md
@@ -145 +145 @@
-    刷量地址与发射窗协同实体均按该节判级，合并口径含全部疑似关联地址。
+    刷量地址与发射窗协同实体均按该节判级，合并口径按 strict／expanded 双边界。
```

### D8

```diff
--- a/references/playbook-entity-cluster-tiering.md
+++ b/references/playbook-entity-cluster-tiering.md
@@ -82 +82 @@
-- **“目标余额驱动”镜像指纹** — **触发条件**：两地址卖出量不同，但卖后余额 raw 级精确修剪到同一整数。**必做动作**：与先后手方向翻转共同检验，排除复制动作量的跟单解释。强度顺序为同额整数仓 < 秒级同步 < 目标余额驱动；三者叠加可到链上铁证。**阻断语义**：gas 不同源时只能写行为级同一实体，不得写资金同源。**权威脚本**：逐事件余额与动作顺序重放。案源：PUB 2026-07-14。
+- **“目标余额驱动”镜像指纹** — **触发条件**：两地址卖出量不同，但卖后余额 raw 级精确修剪到同一整数。**必做动作**：与先后手方向翻转共同检验，排除复制动作量的跟单解释。强度顺序为同额整数仓 < 秒级同步 < 目标余额驱动；三者叠加仍只作行为证据；定级须过 methods"行为指纹三问总闸与强弱两档"，无独立控制证据时最高为"高度疑似"。**阻断语义**：未补独立控制证据不得确证同一实体；gas 不同源不得写资金同源。**权威脚本**：逐事件余额与动作顺序重放。案源：PUB 2026-07-14。
```

```diff
--- a/references/data-pipeline-solana-scan.md
+++ b/references/data-pipeline-solana-scan.md
@@ -133 +133 @@
-meme/微盘"庄"（多钱包控盘团伙）的关联硬证据（任一即可，叠加为铁案），与 analysis-playbook §6 通用聚类规则配合、是其 Solana 特化：
+meme/微盘"庄"（多钱包控盘团伙）的关联候选指纹（定级须过 playbook-entity-cluster-methods"行为指纹三问总闸与强弱两档"；纯行为最高为"高度疑似"），与 playbook-entity-cluster-methods §6 通用聚类规则配合、是其 Solana 特化：
@@ -135 +135 @@
-1. **同 slot 原子下单**：多钱包在完全相同 block 同买同卖 → 单控制端 bundle（用 pre/postTokenBalances 差分定位每钱包买卖，按 `(mint,side)` 聚合看是否同 slot）——最强铁证。
+1. **同 slot 共现**：多钱包同 slot 同买同卖只作候选发现；用 pre/postTokenBalances 按 `(mint,side)` 定位后，须排除公共工具和协议机制；同 slot 本身不证明原子 bundle 或单一控制端。
@@ -138,4 +138,4 @@
-4. **机器人 + 优先费指纹**：同一交易 bot（如 Axiom `FLASHX8DrLbgeR8FcfNV1F5krxYcYMUdBkrP1EPBtxB9`）+ 同一套**离散 cu_price 预设档**（某案 436363 / 800000 / 2.5M / 3.636M / 6.667M microLamports 五档）——普通用户不会用这套组合，是技术指纹（用户说"gas 都一样"即指此）；优先费按买/卖分固定档位也算。cu_price 从 ComputeBudget 指令 `SetComputeUnitPrice`（data 首字节 3）解析。
-5. **金额分档 + ±10% 抖动**：多钱包买入额几乎相同但带随机偏移（反聚类伪装）= 脚本驱动铁证。
-6. **母钱包代付创建落仓户 ATA**：落仓/收币钱包**收币前无任何链上生命**（首笔即被注资），其 token account 的租金由**付款方母钱包代付创建**（同一 tx 里母钱包既转币又付 ATA 创建费）——收款方是母钱包凭空生成的空壳，比"gas 同源"更强的控盘指纹（换钱包也换不掉这个"凭空生成收款方"的结构）。识别=对疑似落仓户查最老签名，看首笔是否为对手方 createAssociatedTokenAccount+transfer 同 tx（OPAL(Solana) 实测 2026-07-14）。
-7. **跨地址凑整回补**：N 笔零散金额（30万/180万/80万…）从一个地址精确凑齐**整数目标**（如 1,000 万整）补入另一地址，使多个落仓户终局配比落成整数（如 25/25/20 万）——**跨地址的全局配平只有单一记账者能做到**，是"单一控制端"的强指纹（独立主体不会为凑别人仓位的整数而分15笔转账）。识别锚点=某中转的净持仓被一串碎额转账修剪到整数（OPAL(Solana) 实测 2026-07-14）。
+4. **机器人 + 优先费指纹**：同一交易 bot（如 Axiom `FLASHX8DrLbgeR8FcfNV1F5krxYcYMUdBkrP1EPBtxB9`）+ 同一套**离散 cu_price 预设档**（某案 436363 / 800000 / 2.5M / 3.636M / 6.667M microLamports 五档）——先检验同工具用户的组合普及率并排除公共预设；买/卖分档亦同，不直接作控制证据。cu_price 从 ComputeBudget 指令 `SetComputeUnitPrice`（data 首字节 3）解析。
+5. **金额分档 + ±10% 抖动**：近似买入额与偏移只作行为候选；须检验同期分母及工具/协议对照，不据此确证脚本驱动、反聚类意图或同一实体。
+6. **母钱包代付创建落仓户 ATA**：落仓/收币钱包**收币前无任何链上生命**（首笔即被注资），其 token account 的租金由**付款方母钱包代付创建**（同一 tx 里母钱包既转币又付 ATA 创建费）——只证明代付建户与转币，不证明付款方控制收款 owner；归属须另核收款方签名、后续处置与独立控制证据。识别=对疑似落仓户查最老签名，看首笔是否为对手方 createAssociatedTokenAccount+transfer 同 tx（OPAL(Solana) 实测 2026-07-14）。
+7. **跨地址凑整回补**：N 笔零散金额（30万/180万/80万…）从一个地址精确凑齐**整数目标**（如 1,000 万整）补入另一地址，使多个落仓户终局配比落成整数（如 25/25/20 万）——只作跨地址配额管理候选；须排除公共执行服务并补独立控制证据后再判同一实体。识别锚点=某中转的净持仓被一串碎额转账修剪到整数（OPAL(Solana) 实测 2026-07-14）。
```

```diff
--- a/references/playbook-entity-cluster-methods.md
+++ b/references/playbook-entity-cluster-methods.md
@@ -134 +134 @@
-- **vanity 定制地址的两种操盘方用法**（与上条"被投毒"相反，这是操盘方自用）：①**配对自证**——注资金主与收币大户地址共享 8–26 位十六进制**中段**（前后缀不同），=批量定制的配对地址，同一实体最硬指纹之一（铁证级；识别看中段不看前缀）；②**仿冒基建伪装**——生成前 12+ 位仿冒 LiFiDiamond/Relay 等真实路由的假基建 EOA 分发筹码，专骗肉眼排查。识别：与真基建地址逐位比对（前缀同、中段不同）+ `is_contract=false` + 无浏览器标签 + tx 数少。三条 vanity 规则合一：**凡涉 vanity 一律完整地址逐位核对**（外部 CASHCAT/GME 考古，07）
+- **vanity 定制地址的两种操盘方用法**（与上条"被投毒"相反，这是操盘方自用）：①**配对指纹候选**——注资金主与收币大户地址共享 8–26 位十六进制**中段**（前后缀不同），只作定制地址候选指纹；须过行为指纹三问总闸，不能仅据共享中段确证同一实体（识别看中段不看前缀）；②**仿冒基建伪装**——生成前 12+ 位仿冒 LiFiDiamond/Relay 等真实路由的假基建 EOA 分发筹码，专骗肉眼排查。识别：与真基建地址逐位比对（前缀同、中段不同）+ `is_contract=false` + 无浏览器标签 + tx 数少。三条 vanity 规则合一：**凡涉 vanity 一律完整地址逐位核对**（外部 CASHCAT/GME 考古，07）
```

### D9

```diff
--- a/references/data-pipeline-solana-capture.md
+++ b/references/data-pipeline-solana-capture.md
@@ -37 +37 @@
-3. **资金同源（gas 溯源）**：公共 RPC `getSignaturesForAddress`（翻到最老）+ `getTransaction(jsonParsed)` 找首笔 system transfer 入金 source；0.25s 间隔，代理经 `CHIP_PROXY`/`--proxy` 解析（`scripts/lib/proxy_config.py`）。识别马甲网络最有效的一招（母钱包收敛即实锤）。
+3. **资金同源（gas 溯源）**：公共 RPC `getSignaturesForAddress`（翻到最老）+ `getTransaction(jsonParsed)` 找首笔 system transfer 入金 source；0.25s 间隔，代理经 `CHIP_PROXY`/`--proxy` 解析（`scripts/lib/proxy_config.py`）。母钱包收敛只作候选线索，须先按 casebook E-05 排除公共服务来源，再补独立控制证据。
```

```diff
--- a/references/data-pipeline-solana-scan.md
+++ b/references/data-pipeline-solana-scan.md
@@ -85 +85 @@
-    - **"即建即提"洗筹指纹（CLAW 实测）**：操盘方用即建即提 stream 做一跳中转，切断"老仓→新仓"的直接转账链路伪装成独立成本；识别锚点 = 提取 tx 的 **feePayer = Streamflow 自动提取服务 `wdrwhnCv4pzW8beKsbPa4S2UDZrXenjg16KJdKSpb5u`**，多笔提取共用此 feePayer = 同一批操作，据此把散落的"新钱包"归回原实体。
+    - **"即建即提"洗筹指纹（CLAW 实测）**：操盘方用即建即提 stream 做一跳中转，切断"老仓→新仓"的直接转账链路伪装成独立成本；识别锚点 = 提取 tx 的 **feePayer = Streamflow 自动提取服务 `wdrwhnCv4pzW8beKsbPa4S2UDZrXenjg16KJdKSpb5u`**，多笔提取共用此 feePayer 只证明同用该服务，不作控制边；归属须沿代币流穿透（data-pipeline-solana-capture §9 第 7 条、casebook E-02/E-05）。
@@ -143 +143 @@
-**逆向找历代马甲（最高价值的一招）**：庄的冷门微盘常是自买自卖 wash trading、外部买家≈0，根本没有跟单狗——所以"最近的同款买家"往往就是庄自己的历代钱包。**总归集口的历史流入地址列表 = 庄的历代马甲归集头名录**（某案总归集口两年 154 个流入地址）。比 co-buyer 扫描高效得多。（此洞察跨链通用，已提炼进 analysis-playbook §6。）
+**归集口上游候选反查**：总归集口的历史流入地址仅作候选清单；逐址核验币流、公共服务属性与独立控制证据，不直接视为同一实体的历代马甲（casebook E-05）。（此方法跨链通用，见 playbook-entity-cluster-methods §6。）
```

### D10

```diff
--- a/references/casebook/entity-clustering.md
+++ b/references/casebook/entity-clustering.md
@@ -18,2 +18,2 @@
-- **必做区分检验**：**公共基础设施先验三测**（任一命中即出实体表、按设施单列）：①getCode 与已知协议标准字节码比对（PCS V3 池标准 22,962B 一比便知）；②部署时间早于代币创建＝公共设施；③多币服务检验（同时服务大量其他代币）。惯犯库入库前同一检验。另须：榜单 EOA 回 tx 层核 `msg.sender` 与事件主体；代理查 EIP-1967 slot+selector；共源地址先过标签库和半枢纽排除；vanity 标签用 getCode+行为复核；高吞吐枢纽算同 tx 等额配对率（近 100% 且零滞留＝管道）；发射窗 delta 排除 AMM/路由；Streamflow 只沿代币流穿透去向。
-- **证据要求（证据不足时的结论上限）**：三测做不全时"未定性合约持仓单列，不计入实体合并占比"；禁止默认并入。tx 主体、实现、配对率或服务面未闭合时一律保留为执行端/设施候选，不得成成员边。
+- **必做区分检验**：**公共基础设施先验四测**（按 playbook-entity-cluster-methods"公共基础设施先验四测"执行；未完成核验不得入成员或惯犯库，列为未定性；确认公共设施后按设施单列）。惯犯库入库前同一检验。另须：榜单 EOA 回 tx 层核 `msg.sender` 与事件主体；代理查 EIP-1967 slot+selector；共源地址先过标签库和半枢纽排除；vanity 标签用 getCode+行为复核；高吞吐枢纽算同 tx 等额配对率（近 100% 且零滞留＝管道）；发射窗 delta 排除 AMM/路由；Streamflow 只沿代币流穿透去向。
+- **证据要求（证据不足时的结论上限）**：四测做不全时"未定性合约持仓单列，不计入实体合并占比"；禁止默认并入。tx 主体、实现、配对率或服务面未闭合时一律保留为执行端/设施候选，不得成成员边。
```

### D11

```diff
--- a/references/playbook-evidence-wording.md
+++ b/references/playbook-evidence-wording.md
@@ -106 +106 @@
-- **★完整阴性结论高门槛**："发现一个实体"可由充分阳性证据成立；"全盘零庄/无其他实体"必须证明当前≥0.5% owner、历史峰值、已归零/回落/静置仓和边界外候选全部裁决，且量化CEX/OTC黑箱。抽样每址N笔、截断文件、稀疏锚点或未决候选任一存在时，不得发布完整阴性结论。（既有报告独立复核方法修正，07-26；逻辑机制规则）
+- **★完整阴性结论高门槛**："发现一个实体"可由充分阳性证据成立；"全盘零庄/无其他实体"必须证明当前达到其他大户线（tiering §6a：≥0.1% 总供应或 ≥0.2% 流通）的 owner、历史峰值、已归零/回落/静置仓和边界外候选全部裁决，且量化CEX/OTC黑箱。抽样每址N笔、截断文件、稀疏锚点或未决候选任一存在时，不得发布完整阴性结论。（既有报告独立复核方法修正，07-26；逻辑机制规则）
```

### D12

```diff
--- a/references/independent-audit-protocol.md
+++ b/references/independent-audit-protocol.md
@@ -166 +166 @@
-  `reconciliation_report.json` 必须由当前 `scripts/report/reconciliation_report.py` 读取 job spec 后受控启动四查生产者生成：balance/supply=`verify_recon.py`、supply_truth=`supply_truth_gate.py`、time=`time_spotcheck.py`（Solana 对应 anchor sampler 与 holder snapshot）。runner 要求 receipt 执行前不存在，逐项记录子进程 exit，并绑定 v2 target、生产者与输入/receipt 哈希；wrapper 顶层绑定 runner 自身路径与当前 SHA-256。聚合器逐类解析 schema、target、观测和 verdict，并拒绝无 runner 绑定或绑定哈希不符的 wrapper；旧案须重跑对应生产者与 runner。这里是内容绑定，不是单机执行证明：蓄意手拼者若正确填写当前 runner path/SHA-256 并伪造相互自洽的观测，聚合器无法仅凭 wrapper 识别；防线的实际作用是把“疏忽即可绕过”提高为必须显式填哈希、编造观测的主动造假，并由仓库 git 历史追踪代码变更。案目录里的同名/复制脚本即使 SHA-256 相同也不是生产者。
+  `reconciliation_report.json` 必须由当前 `scripts/report/reconciliation_report.py` 读取 job spec 后受控启动各链对账生产者生成（EVM 四查、Solana 五查；键序见 scan-schemas §14.10，逐查生产者见 scripts/report/shared_release_receipt.py 的 RECON_PRODUCERS）。runner 要求 receipt 执行前不存在，逐项记录子进程 exit，并绑定 v2 target、生产者与输入/receipt 哈希；wrapper 顶层绑定 runner 自身路径与当前 SHA-256。聚合器逐类解析 schema、target、观测和 verdict，并拒绝无 runner 绑定或绑定哈希不符的 wrapper；旧案须重跑对应生产者与 runner。这里是内容绑定，不是单机执行证明：蓄意手拼者若正确填写当前 runner path/SHA-256 并伪造相互自洽的观测，聚合器无法仅凭 wrapper 识别；防线的实际作用是把“疏忽即可绕过”提高为必须显式填哈希、编造观测的主动造假，并由仓库 git 历史追踪代码变更。案目录里的同名/复制脚本即使 SHA-256 相同也不是生产者。
```

### F1

```diff
--- a/references/playbook-supply-recon.md
+++ b/references/playbook-supply-recon.md
@@ -38 +38 @@
-**总原则：重建/采集结果必须与独立数据源精确对表后才允许进入分析。对不上 = 数据有洞 = 回去补数据，不是调整阈值或口头解释。** 分类权威源＝analyze-workflow **A2 四查**（余额对账/供给闭合/供给真值闸/时间抽查）——下方各链条目是历史实战沉淀的校验形态，归入四查框架执行、不替代四查分类。各链形态并列如下，做哪条链就执行哪套：
+**总原则：按 analyze-workflow A2 完成全部对账关卡后才进入分析；EVM 四查、Solana 五查（另含 exact_reconcile）。** 下方各链条目为历史校验形态，归入对账关卡执行、不替代正式查项；GMGN 黄灯处理见 data-pipeline-evm-recon §5 第 1 条。
@@ -48 +48 @@
-**Solana（⚠️ 过时的受限降级形态——SQD 全量重放上线后 Solana 走标准四查，见 data-pipeline-solana-capture；仅全量通道全部不可用时才降级至此）：**
+**Solana（⚠️ 过时的受限降级形态——SQD 全量重放上线后 Solana 走标准五查，见 data-pipeline-solana-capture；仅全量通道全部不可用时才降级至此）：**
```

```diff
--- a/references/analyze-workflow.md
+++ b/references/analyze-workflow.md
@@ -19 +19 @@
-  并冻结 `audit_input_manifest.json`，A2 完成四查对账。A3 起以净室协议重建实体、三账、历史序列和
+  并冻结 `audit_input_manifest.json`，A2 完成对账关卡。A3 起以净室协议重建实体、三账、历史序列和
@@ -46 +46 @@
-| 全新链 | 新链 SOP：先实测数据面并实现采集 receipt、四查、标签 resolver 与 G8 chain 适配；这些正式门禁未齐前只能交付明确降级的探索结果，不得编译正式 analysis |
+| 全新链 | 新链 SOP：先实测数据面并实现采集 receipt、按链定义的对账关卡、标签 resolver 与 G8 chain 适配；这些正式门禁未齐前只能交付明确降级的探索结果，不得编译正式 analysis |
@@ -112,5 +112,4 @@
-   **喂它的 owner 快照必须与 A2 四查里 `verify_recon --balances` 吃的是同一个文件**
-   （EVM 通常是 `balances_final.json`，Solana 是 scanner 自己产的
-   `data/holders_owners.json`）：发布闸 new-analysis 会拿分布快照的 sha256 去对四查
-   `balance` 收据的 `inputs.balances`（Solana 对 observation bundle 的
-   `holder_outputs.owners`），喂两份不同的文件即便总和相同也会被判"同值换仓"而拒。
+   **owner 快照须与 A2 的权威输入绑定一致**：
+   EVM 对 `balance` 收据的 `inputs.balances`；
+   Solana 对 observation bundle 的 `holder_outputs.owners`。
+   发布闸按 sha256 核对内容；即使总和相同，逐地址余额不同也会拒绝。
```

```diff
--- a/SKILL.md
+++ b/SKILL.md
@@ -32 +32 @@
-2. **对账关卡**：A2 四查（余额对账/供给闭合/供给真值闸/时间抽查）不过关不进分析。
+2. **对账关卡**：A2 对账关卡（EVM 四查／Solana 五查）不过关不进分析。
@@ -45 +45 @@
-| A2 对账关卡 | 余额/供给闭合/供给真值/时间抽查 | A2＋recon；supply_truth.json、anchor_plan.json、time_spotcheck.json | 四查不过不进 A3；gate 0 PASS/2 FAIL/1 修通道重跑 |
+| A2 对账关卡 | 余额/供给闭合/供给真值/时间抽查，Solana 加精确重放 | A2＋recon；supply_truth.json、anchor_plan.json、time_spotcheck.json | 不过不进 A3；gate 0 PASS/2 FAIL/1 修通道重跑 |
```

```diff
--- a/references/report-template.md
+++ b/references/report-template.md
@@ -90 +90 @@
-  对账关卡结果一句话（四查过关声明：余额对账/供给闭合/供给真值闸/时间抽查）
+  对账关卡结果一句话（EVM 四查／Solana 五查逐项过关声明）
```

```diff
--- a/references/split-run.md
+++ b/references/split-run.md
@@ -53 +53 @@
-  9. **当前持仓分布初判**：运行 `holder_distribution_scan.py --stage initial`，产 `distribution_scan.json` 和 `charts/distribution_stage1.png`。JSON 是 READY 必产件，工作图只供 −2 查看，不进 seal 或报告。initial 不绑定 handoff manifest。**快照单一来源硬性**：这一步吃的 owner 快照必须与 A2 四查 `verify_recon --balances` 吃的是同一个文件，别另存一份"内容一样"的副本——发布闸 new-analysis 拿 sha256 做等值比对（EVM 对四查 balance 收据的 `inputs.balances`，Solana 对 observation bundle 的 `holder_outputs.owners`），两份文件哪怕总和相同也会被判"同值换仓"直接拒。initial 记录的 `upstream_receipts` 是 optional 记录性收据：案根还没有 preflight 副本时不记是合法的，但记了就会被逐项三验。
+  9. **当前持仓分布初判**：运行 `holder_distribution_scan.py --stage initial`，产 `distribution_scan.json` 和 `charts/distribution_stage1.png`。JSON 是 READY 必产件，工作图只供 −2 查看，不进 seal 或报告。initial 不绑定 handoff manifest。**快照单一来源硬性**：分布快照须与 A2 的权威输入内容一致：EVM 对 `balance` 收据的 `inputs.balances`，Solana 对 observation bundle 的 `holder_outputs.owners`；发布闸按 sha256 核对，逐地址余额不同即使总和相同也拒绝。initial 记录的 `upstream_receipts` 是 optional 记录性收据：案根还没有 preflight 副本时不记是合法的，但记了就会被逐项三验。
@@ -98 +98 @@
-| 既有产物 | −1 | accounting_mode、链内 done.json/collection_manifest/receipt、四查 producer receipt、由 `reconciliation_report.py` 生成的 `reconciliation_report.json`、cluster_prep、address_bucket_series、价格序列；四查 receipt 格式零改动，wrapper 禁止手拼 |
+| 既有产物 | −1 | accounting_mode、链内 done.json/collection_manifest/receipt、A2 全部 producer receipt、由 `reconciliation_report.py` 生成的 `reconciliation_report.json`、cluster_prep、address_bucket_series、价格序列；各项 receipt 按现行 schema 提供，wrapper 禁止手拼 |
@@ -126 +126 @@
-4. **必读件**：anomalies.json、四查结论、accounting_mode、点名式 CEX 黑箱关卡结论（若有）。
+4. **必读件**：anomalies.json、对账结论、accounting_mode、点名式 CEX 黑箱关卡结论（若有）。
@@ -143 +143 @@
-- **不给 sealed 观察文件、不让它复核自己 −1 的产出物本身**（数据完整性由 −2 verify＋四查兜底，数据层疑点由 Claude 怀疑者路负责）;
+- **不给 sealed 观察文件、不让它复核自己 −1 的产出物本身**（数据完整性由 −2 verify＋A2 全部对账关卡兜底，数据层疑点由 Claude 怀疑者路负责）;
```

```diff
--- a/commands-staging/token-analyze-2.md
+++ b/commands-staging/token-analyze-2.md
@@ -13 +13 @@
-4. **必读件**：anomalies.json、四查结论、accounting_mode、点名式 CEX 黑箱关卡结论（若有）。
+4. **必读件**：anomalies.json、对账结论、accounting_mode、点名式 CEX 黑箱关卡结论（若有）。
```

```diff
--- a/references/context-discipline.md
+++ b/references/context-discipline.md
@@ -27 +27 @@
-   历史清单项（脚本跑批与重试循环/对账四查执行/键树与地址批查（`handoff_manifest.py inspect/lookup`）/大户批量排查/图表脚本执行/数据完整性验证/逐地址溯源 fan-out）继续有效；已归 −1 的项在 −1 内完成。
+   历史清单项（脚本跑批与重试循环/A2 对账执行/键树与地址批查（`handoff_manifest.py inspect/lookup`）/大户批量排查/图表脚本执行/数据完整性验证/逐地址溯源 fan-out）继续有效；已归 −1 的项在 −1 内完成。
@@ -58 +58 @@
-3. **数据不重采**：采集产物幂等续拉增量即可；对账四查若断前已过、数据未增量则不重跑，增量后必重跑。
+3. **数据不重采**：采集产物幂等续拉增量即可；A2 对账若断前已过、数据未增量则不重跑，增量后必重跑。
```

```diff
--- a/references/scan-schemas.md
+++ b/references/scan-schemas.md
@@ -17 +17 @@
-4. **本文件＝完整字段登记**（v6.8.1，codex 复核 P2 采纳）：脚本实际输出的每个字段都必须在此登记——未登记字段不得输出，登记了的不得静默删除；公共通用字段（`schema/generated_at/params/total_supply_raw/edges/note`）各产物一律在场，下文不再逐一重复。输入边表的唯一性由采集管线（four-check 对账）保证，扫描器不去重。Solana v4 以 `(slot,tx_index)` 标识交易，并对该交易完整边集计算排序后的 `tx_digest`：重复身份且 digest 相同只留一份，digest 不同硬失败。五元组没有交易身份，同字段重复可能是不同真实交易，禁止按五字段去重。
+4. **本文件＝完整字段登记**（v6.8.1，codex 复核 P2 采纳）：脚本实际输出的每个字段都必须在此登记——未登记字段不得输出，登记了的不得静默删除；公共通用字段（`schema/generated_at/params/total_supply_raw/edges/note`）各产物一律在场，下文不再逐一重复。输入边表的唯一性由采集管线（A2 对账关卡）保证，扫描器不去重。Solana v4 以 `(slot,tx_index)` 标识交易，并对该交易完整边集计算排序后的 `tx_digest`：重复身份且 digest 相同只留一份，digest 不同硬失败。五元组没有交易身份，同字段重复可能是不同真实交易，禁止按五字段去重。
@@ -396 +396 @@
-分布扫描吃的那份 owner 快照，必须就是四查真正核过的那一份：EVM 比对四查 `balance` 收据的 `inputs.balances.sha256`，Solana 比对 observation bundle 的 `holder_outputs.owners.sha256`，**只比 sha256 不比 path**（两边路径形态本来就不同）。**initial 扫描与进报告的终态 final 扫描（`distribution_rounds.json` 的 `terminal.final_scan_path`）两份都要落在同一个四查 sha 上**——只绑 initial 挡不住 final 轮换一份同值换仓快照产终态判定（F-B1）。该交叉检查由 `audit_release_gate.py --profile new-analysis` 执行，**只放发布闸、不放进 validate**（终态 scan 是本轮新产，不涉及存量案追溯）。
+分布扫描吃的那份 owner 快照，必须就是 A2 真正核过的那一份：EVM 比对 `balance` 收据的 `inputs.balances.sha256`，Solana 比对 observation bundle 的 `holder_outputs.owners.sha256`，**只比 sha256 不比 path**（两边路径形态本来就不同）。**initial 扫描与进报告的终态 final 扫描（`distribution_rounds.json` 的 `terminal.final_scan_path`）两份都要落在同一个 A2 快照 sha 上**——只绑 initial 挡不住 final 轮换一份同值换仓快照产终态判定（F-B1）。该交叉检查由 `audit_release_gate.py --profile new-analysis` 执行，**只放发布闸、不放进 validate**（终态 scan 是本轮新产，不涉及存量案追溯）。
@@ -484 +484 @@
-**重验须重跑当前版本生产者（F-B5，修正旧口径）**：validate 内部经 `build_scan` 重算，闭合闸也在这条追溯路径上，且 `input_binding.algorithm.sha256` 绑脚本自身哈希——脚本改过一个字节，旧产物就对不上。所以存量案在 A5 重验前无论如何都要重跑对应生产者获取当前回执（与仓内既有的"存量案例须重跑对应生产者"一致），这**不是死锁**。重跑后仍不对铸造总量精确闭合的存量案按 `data_broken` 拒收，这是**刻意收紧不是回归**（基线时代只拦超发，残缺快照能过）。第二层交叉检查禁入 validate 只是不让"快照↔四查绑定"这一条追溯卡死，闭合闸的追溯收紧另算。
+**重验须重跑当前版本生产者（F-B5，修正旧口径）**：validate 内部经 `build_scan` 重算，闭合闸也在这条追溯路径上，且 `input_binding.algorithm.sha256` 绑脚本自身哈希——脚本改过一个字节，旧产物就对不上。所以存量案在 A5 重验前无论如何都要重跑对应生产者获取当前回执（与仓内既有的"存量案例须重跑对应生产者"一致），这**不是死锁**。重跑后仍不对铸造总量精确闭合的存量案按 `data_broken` 拒收，这是**刻意收紧不是回归**（基线时代只拦超发，残缺快照能过）。第二层交叉检查禁入 validate 只是不让"快照↔A2 绑定"这一条追溯卡死，闭合闸的追溯收紧另算。
```

### D13

```diff
--- a/references/analyze-workflow.md
+++ b/references/analyze-workflow.md
@@ -117,3 +117 @@
-   动态 Solana（`exact_reconcile` 早于 wrapper）必须显式指定观察快照，因为
-   `holder_distribution_scan.find_snapshot` 默认优先 `data/holders_owners.json`（冻结件），
-   而发布闸的分布绑定要求 observation bundle 的观察 owners。完整命令：
+   动态 Solana（`exact_reconcile` 早于 wrapper）必须显式指定观察快照（`--snapshot`），因为发布闸的分布绑定要求 observation bundle 的观察 owners。完整命令：
```

```diff
--- a/references/split-run.md
+++ b/references/split-run.md
@@ -54 +54 @@
-     动态 Solana（`exact_reconcile` 早于 wrapper）必须显式使用观察 owners；`find_snapshot` 默认优先 `data/holders_owners.json`（冻结件），发布闸分布绑定却要求 observation bundle 的观察件。完整命令：`python3 scripts/report/holder_distribution_scan.py --case-dir . --stage initial --snapshot data/observe_live/holders_owners.json`。
+     动态 Solana（`exact_reconcile` 早于 wrapper）必须显式使用观察 owners（`--snapshot`），因为发布闸分布绑定要求 observation bundle 的观察件。完整命令：`python3 scripts/report/holder_distribution_scan.py --case-dir . --stage initial --snapshot data/observe_live/holders_owners.json`。
```

### D14

```diff
--- a/references/labels/README.md
+++ b/references/labels/README.md
@@ -8 +8 @@
-**接入方式（v4）**：`labels_resolver.py` 共享内核——`label_lookup.py`（人工查询）、EVM `cluster.py`/`analyze_holdings.py`、SOL `replay_edges.py`/`build_evolution.py`（阵营体检）均已默认接入（`--no-labels` 关闭）；表缺失/加载失败显式报 **degraded_mode**（"没命中"与"没加载"可区分），分析产物落 `labels_meta`。
+**接入方式（v4）**：`labels_resolver.py` 共享内核——`label_lookup.py`（人工查询）、EVM `cluster.py`/`analyze_holdings.py`、SOL `replay_edges.py`/`build_evolution.py`（阵营体检）均已默认接入；表缺失/加载失败显式报 **degraded_mode**（"没命中"与"没加载"可区分），分析产物落 `labels_meta`。
```

### D15

```diff
--- a/references/data-pipeline-evm-channels.md
+++ b/references/data-pipeline-evm-channels.md
@@ -69 +69 @@
-手搓 JSON 不构成迁移工具。v2 Parquet 通道则继续由 native done v3 +
+手搓 JSON 不构成迁移工具。v2 Parquet 通道则继续由 native done v4 +
```

### D16

```diff
--- a/references/data-pipeline-evm-channels.md
+++ b/references/data-pipeline-evm-channels.md
@@ -272 +271,0 @@
-| **transfers_lib 整表读大 parquet 必 OOM** | `iter_transfers` 内部 `pq.read_table` 整表载入，logs.parquet 数 GB 级（QUQ 案 6.6GB/1.03 亿行）直接 SIGKILL（exit 137、输出全空）。亿级全史扫描自写 pyarrow `ParquetFile.iter_batches(batch_size=20万, columns=['block_number','topic1','topic2','data'])` 流式，峰值内存 <1GB、约 2 分钟/亿行；日期用 blocks.parquet number→timestamp 映射 + `ts//86400` 整数日聚合（避免逐行 strftime）；跨 run 去重用块边界法 `[from_block,next_block)`（亿级 (tx,log_index) set 去重内存不可行） | （QUQ 投后，07-22） |
```

### D17

```diff
--- a/references/data-pipeline-evm-channels.md
+++ b/references/data-pipeline-evm-channels.md
@@ -259 +259 @@
-| four.meme 内盘量化 / 克隆快判 | 内盘额度恰 8 亿/80%，dev-buy 同 tx 按 bonding curve 买断内盘凑满即秒毕业、创世后约 8 块（~4s）TokenManager2 注 20% 入 Pancake V2；"创世同秒单钱包拿走 ~80%"=dev buy。`7777` 后缀=另一发射台 CREATE2（与 4444 并列，平台特征非指纹）。meme-api 全路径已 404，正身改看创世 tx HTML 是否触及 TokenManager2/部署器（创建者从合约页 Contract Creator 取，href 单引号，正则 `["']?`） | （外部 TCC/bibi 考古，07） |
+| four.meme 内盘量化 / 克隆快判 | 内盘额度恰 8 亿/80%，dev-buy 同 tx 按 bonding curve 买断内盘凑满即秒毕业、创世后约 8 块（~4s）TokenManager2 注 20% 入 Pancake V2；"创世同秒单钱包拿走 ~80%"=dev buy。`7777` 后缀=另一发射台 CREATE2（与 4444 并列，平台特征非指纹）。正身可试 meme-api（历史实测见 data-pipeline-evm-sources，当前可用性须实测），或查创世 tx HTML 是否触及 TokenManager2/部署器（创建者从合约页 Contract Creator 取，href 单引号，正则 `["']?`） | （外部 TCC/bibi 考古，07） |
```

### D18

```diff
--- a/references/labels/MAINTENANCE.md
+++ b/references/labels/MAINTENANCE.md
@@ -19 +19 @@
-| manual/addressbook | 实战核验条目（含全部 Robinhood 独家）| 最高，优先级压过一切 |
+| manual/addressbook | 实战核验条目（含全部 Robinhood 独家）| 次高（SRC_PRIORITY=0，仅低于 curation） |
```

### D19

```diff
--- a/references/split-run.md
+++ b/references/split-run.md
@@ -44,5 +44,5 @@
-- **A3 机械子层**（对照 analyze-workflow A3 主序编号）：
-  1. 地址身份标注**批量层**（主序第 1 项前半）：标签库/getCode/Sourcify/外部证据批查。**输出只写观察事实**：`observed_type`＋`source`＋`source_timestamp`＋`conflict_flags`；仅多源无冲突的公共设施可标 `auto_excluded_candidate`，最终排除权在 −2。
-  2. 金库与核心实体逐笔归因**跑批**（主序第 1 项中段的脚本执行侧）：产出流水，不定性。
-  3. 大户排查**批量层跑满**（主序第 5 项的批量侧）：当前 ≥0.1% 总供应或 ≥0.2% 流通全量＋历史越线＋归零/静置候选（`dormant_candidates` 并入 candidate_universe）× 标签库/惯犯库/指纹/funder 溯源四通道；无法机械定性者标 `needs_adjudication`（批量层跑满是防"候选海"倒灌 −2 的第一道闸）。对四通道报警地址，就地产 ET-1 证据采集包：分母＝报警地址的保守超集（−1 阶段无最终"其他大户"集合，宁多采不漏采），逐址采资金源/gas 注资/互转边/对手方清单，只记观察事实零定性，落 et1_evidence_packs.json；该件为 optional 产物，存在时必须经 generate 纳入 manifest allowlist 并登记 data_map 与 stage1_receipts（防交接后被改写）。归属定性深挖仍归 −2。
-  4. 聚类准备（主序第 1 项后半的算法侧）：cluster_prep ＋聚类算法**候选簇**——含拒绝边与孤立点**全量保留**，不只交"算法觉得相关"的簇；合并裁决权在 −2。
+- **A3 机械子层**：
+  1. 地址身份标注**批量层**：标签库/getCode/Sourcify/外部证据批查。**输出只写观察事实**：`observed_type`＋`source`＋`source_timestamp`＋`conflict_flags`；仅多源无冲突的公共设施可标 `auto_excluded_candidate`，最终排除权在 −2。
+  2. 金库与核心实体逐笔归因**跑批**：产出流水，不定性。
+  3. 大户排查**批量层跑满**：当前 ≥0.1% 总供应或 ≥0.2% 流通全量＋历史越线＋归零/静置候选（`dormant_candidates` 并入 candidate_universe）× 标签库/惯犯库/指纹/funder 溯源四通道；无法机械定性者标 `needs_adjudication`（批量层跑满是防"候选海"倒灌 −2 的第一道闸）。对四通道报警地址，就地产 ET-1 证据采集包：分母＝报警地址的保守超集（−1 阶段无最终"其他大户"集合，宁多采不漏采），逐址采资金源/gas 注资/互转边/对手方清单，只记观察事实零定性，落 et1_evidence_packs.json；该件为 optional 产物，存在时必须经 generate 纳入 manifest allowlist 并登记 data_map 与 stage1_receipts（防交接后被改写）。归属定性深挖仍归 −2。
+  4. 聚类准备：cluster_prep ＋聚类算法**候选簇**——含拒绝边与孤立点**全量保留**，不只交"算法觉得相关"的簇；合并裁决权在 −2。
```

### C1

```diff
--- a/references/data-pipeline-solana-capture.md
+++ b/references/data-pipeline-solana-capture.md
@@ -134 +134 @@
-- **`/head` 给的是 unfinalized head**,响应头 `x-sqd-finalized-head-number` 比它小约 2,900 slot（实测）。采集上界取 `/head` 没问题（实测到 head 仍正常返回数据）,但别拿两者的差当异常。
+- **`/head` 给的是 unfinalized head**,响应头 `x-sqd-finalized-head-number` 比它小约 2,900 slot（实测）。生产者上界不超过 finalized slot，并与 `/head`、可选 `--to-slot` 取较小值（`fetch_sqd_transfers_v2.py`），别拿两者的差当异常。
```

### C2

```diff
--- a/references/playbook-entity-cluster-methods.md
+++ b/references/playbook-entity-cluster-methods.md
@@ -171 +171 @@
-- **历史静置仓反向扫描硬闸（冻结实体前必做；正向 BFS 不能替代）** — **触发条件**：完成初步聚类、准备冻结实体/算峰值/出图。**必做动作**：生成 dormant_warehouse_audit.json；候选全集从三条现役机械通道取齐：wave_scan v3 全体历史峰值 ≥0.02% 地址、entity_source_trace direct_upstream、边界外一圈反查。scan_universe 必逐址记录峰值/现仓/留存桶与 must_adjudicate；必裁决包括峰值榜前 200、越线 ≥0.1%、回落 ≥80% 或静置 ≥30 天且峰值 ≥0.05%。以 universe_ref{path,sha256} 绑定审计。**阻断语义**：无产物、旧 v2、哈希/集合不闭合或有未裁决候选即 fail-closed。**权威脚本**：wave_scan v3、entity_source_trace、audit_release_gate。
+- **历史静置仓反向扫描硬闸（冻结实体前必做；正向 BFS 不能替代）** — **触发条件**：完成初步聚类、准备冻结实体/算峰值/出图。**必做动作**：生成 dormant_warehouse_audit.json；候选全集从三条现役机械通道取齐：wave_scan 全体历史峰值 ≥0.02% 地址、entity_source_trace direct_upstream、边界外一圈反查。scan_universe 必逐址记录峰值/现仓/留存桶与 must_adjudicate；必裁决包括峰值榜前 200、越线 ≥0.1%、回落 ≥80% 或静置 ≥30 天且峰值 ≥0.05%。以 universe_ref{path,sha256} 绑定审计。**阻断语义**：无产物、旧 v2、哈希/集合不闭合或有未裁决候选即 fail-closed。**权威脚本**：wave_scan、entity_source_trace、audit_release_gate。
```

### X1

```diff
--- a/references/data-pipeline-solana-scan.md
+++ b/references/data-pipeline-solana-scan.md
@@ -159 +159 @@
-- **RugCheck `api.rugcheck.xyz/v1/tokens/<mint>/report`（免 key）**（外部 SGL/CLAW 分析实测，2026-07）：一次拿 topHolders（含 owner+pct+**insider 标记**）+ markets（LP 名单）+ **insiderNetworks**（转账关联的内幕簇，直接给出关联地址网络）+ launchpad——**是 `getTokenLargestAccounts` 恒 429 的最佳替代**（§0a），insider 关联比自建聚类省事，但仍按 analysis-playbook §6 硬规则复核。
+- **RugCheck `api.rugcheck.xyz/v1/tokens/<mint>/report`（免 key）**（外部 SGL/CLAW 分析实测，2026-07）：一次拿 topHolders（含 owner+pct+**insider 标记**）+ markets（LP 名单）+ **insiderNetworks**（转账关联的内幕簇，直接给出关联地址网络）+ launchpad——**是 `getTokenLargestAccounts` 恒 429 的最佳替代**（§0a），insider 关联比自建聚类省事，但仍按 playbook-entity-cluster-methods §6 硬规则复核。
```

```diff
--- a/references/report-template.md
+++ b/references/report-template.md
@@ -34 +34 @@
-2. **每个庄什么类型？** ①单地址明牌 ②多地址·互转/gas 同源·明牌 ③伪装分散·行为指纹一致（类型学见 analysis-playbook §6a）
+2. **每个庄什么类型？** ①单地址明牌 ②多地址·互转/gas 同源·明牌 ③伪装分散·行为指纹一致（类型学见 playbook-entity-cluster-tiering §6a）
```

### D1（暂缓）

依 §3 本轮不施工；未修改代码，也未改动 `code_change_pending.md`。

## 4. §1.2 守卫命令与原始输出

执行环境设置 `PYTHONDONTWRITEBYTECODE=1`，以下命令及输出保持原样；全部 exit 0。

### 4.1 文档守卫

```console
$ python3 scripts/tests/docs_lint.py && python3 scripts/tests/docs_lint.py --all
PASS: 45 个文档，引用无断链、粗体配对完整
PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）
```

### 4.2 `casebook_lint.py`

```console
$ python3 scripts/tests/casebook_lint.py
casebook lint 通过：6 册 38 条，ID 唯一、六字段齐全
```

### 4.3 `changelog_lint.py`

```console
$ python3 scripts/tests/changelog_lint.py
PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 73 条 + 归档 139 条
```

### 4.4 `test_contract_routes.py`

```console
$ python3 scripts/tests/test_contract_routes.py
PASS: R-01/R-02 注册表、ID 快照、五组锚与 SKILL 原子阶段双向闭合
```

### 4.5 `test_sixlens_docs.py`

```console
$ python3 scripts/tests/test_sixlens_docs.py
PASS: 六视角批⑤大小口径与 archive 路由
```

### 4.6 `test_g3_docs_guards.py`

```console
$ python3 scripts/tests/test_g3_docs_guards.py
PASS: F-08 A0 exploration command
PASS: F-08 A2 formal rerun order
PASS: F-13 runner injection boundary
PASS: F-05 machine boundary
```

### 4.7 `test_version_consistency.py`

```console
$ python3 scripts/tests/test_version_consistency.py
PASS: M-03 version metadata consistent at 7.1.1
```

补充检查：`git diff --check` 实际执行 exit 0、stdout 为空；20 个修改文件的最终 SHA-256 全部等于按工单预先计算的结果。`git diff HEAD --stat -- scripts VERSION` 输出为空；暂存区无修改。

## 5. git diff --stat

```text
 SKILL.md                                      |  4 ++--
 commands-staging/token-analyze-2.md           |  2 +-
 references/analyze-workflow.md                | 19 ++++++++-----------
 references/casebook/entity-clustering.md      |  4 ++--
 references/context-discipline.md              |  4 ++--
 references/data-pipeline-evm-channels.md      |  5 ++---
 references/data-pipeline-evm-recon.md         |  8 ++++----
 references/data-pipeline-evm-sources.md       |  5 ++---
 references/data-pipeline-solana-capture.md    |  6 +++---
 references/data-pipeline-solana-scan.md       | 18 +++++++++---------
 references/independent-audit-protocol.md      |  2 +-
 references/labels/MAINTENANCE.md              |  2 +-
 references/labels/README.md                   |  2 +-
 references/playbook-entity-cluster-methods.md |  4 ++--
 references/playbook-entity-cluster-tiering.md |  4 ++--
 references/playbook-evidence-wording.md       |  2 +-
 references/playbook-supply-recon.md           |  8 ++++----
 references/report-template.md                 |  4 ++--
 references/scan-schemas.md                    |  6 +++---
 references/split-run.md                       | 20 ++++++++++----------
 20 files changed, 62 insertions(+), 67 deletions(-)
```

该命令只展示 20 个已跟踪文件的改动，全部在 §0.3 白名单内。本报告为新建且未暂存文件，不出现在普通 `git diff --stat` 中；完工范围核验另将其计入，共 21 个白名单路径。

## 6. 差异、停工点与访问纪律

- 指定施工文本与工单无差异；无锚点不唯一、行号不符、契约冲突或验收未通过的停工点。
- 辅助预检包装首次执行因 JSON 的 `null` 未经解析而抛出 `NameError`，发生在该次目标文件读取和写入之前；改用 `json.loads` 后完整重跑，66 项全部通过。未因此改动任何工单外文件。
- 未 commit、未 push、未部署 `~/.claude/commands/`；未修改 `scripts/`、`scripts/tests/contract_manifest.json`、VERSION 或工单本身。全程离线。
- 未执行 `test_commands_deploy_sync.py`：它不在 §1.2 必跑清单中；部署与部署后复验依 §0.5 留给 Fable。
- 是否读过 `~/.codex/`：未通过工具主动读取其中任何文件。会话启动时自动提供了历史记忆摘要，已在首次说明中如实披露；之后未读取该目录，也未把该摘要用于施工判断。
- 未主动读取 `archive/`、`blind-reviews/`、`.staging_*` 或 `references/attic.md` 的内容；守卫脚本自身既有遍历按用户授权执行。
