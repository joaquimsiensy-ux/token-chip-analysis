# 标签库维护手册（MAINTENANCE.md）

> **本文件只在维护标签库时读**（重建/扩容/审计/发布）；分析时只读 `README.md`（使用篇）。

labels 数据版本独立于 skill 版本；已发布版本与逐表变更见 CHANGELOG。

**发布库维护纪律（v4.2+ 稳定化定，2026-07-18）**：
- **curation 层（SRC_PRIORITY = -1，高于 manual/addressbook）**：`additions/curation_overrides_*.csv` 的 source 一律写 `curation`。根因：add_labels.py 对同级采用"新条目覆盖"、build_labels.py 采用"先到保留"——两语义不一致曾致 12 行 v4.2 精修（Relay solver 官方 API 亲验等）在全量重建时被 gen_manual 泛化行回退（列级 diff 实测抓出，已救回 `curation_overrides_20260718.csv`）。**今后凡"直改发布库"级别的精修，必须同步固化为 curation override 文件**，否则下次重建即回退。
- **高优先级源覆盖语义**：upsert 的 evidence/verified_at/status 三列随优先级覆盖（有值才覆盖）——curation/manual 层的权威证据出处才能真正生效。
- **benchmark fail-fast**：`--labels-dir` 找不到任何 labels-*.csv 时 FAIL 退出（此前路径错→空表→"错误 exclude=0"恒真假 PASS，预检门禁可被 cwd 错误静默绕过；README 预检命令须在 `scripts/labels/` 下运行）。
- **roundtrip_check.py 进发布流程**（见下方重建步骤）。

## 数据源清单

| 源 | 内容 | 置信 |
|---|---|---|
| curation | 人工精修固化（additions/curation_overrides_*.csv） | 最高（压过一切，v4.2+ 稳定化设立） |
| manual/addressbook | 实战核验条目（含全部 Robinhood 独家）| 最高，优先级压过一切 |
| serial-offenders | 惯犯层（appendix/state 双源自动回灌+人工白名单，随案滚动，07-31 时点约 1,740 址）| **线索级**（案内定性、多数案源未经用户复核，v6.2.0 降级定调——消费纪律见 labels/README serial-actor 段，禁当最高置信源用） |
| registry-official | 官方 deployment registry（Aerodrome/Clanker/Zora/Uniswap/Virtuals 官方仓库·npm 包·docs 亲验，Base 54 条首建）| 高（官方源） |
| manual-chainverify | 链上事件/RPC 亲验条目（如 Tornado BSC 合约）| 高（链上实测） |
| spellbook（Dune/hildobby）| EVM CEX 统一表 4957、SOL CEX 164、桥 177、基金 51 | 高（人工维护） |
| manual-rhdocs | Robinhood 官方 docs 协议合约 | 高（官方） |
| manual-ofac | OFAC SDN 制裁地址（v4 起 EOA 才三链注入，见下）| 高（权威原始源） |
| solprog / jup-official | SOL 程序 RPC 核验 + Jupiter API 97 条 | 高 |
| dune-labels | Dune labels.addresses 精选（query **7999252**）| 高（identifier 类）/中（persona 行为类） |
| dawsbot（eth-labels）| Etherscan 系官方标签快照（活跃维护）| 中高 |
| brianleect | 同上 2023-10 停更快照（交叉补充）| 中 |
| gmgn / kolscan | KOL/聪明钱钱包（滚动积累）| 中 |
| scamsniffer | 2,530 条 drainer/钓鱼——只入 `scam-candidate` 候选层 | 中（社区上报） |
| manual-hldocs | HyperCore 系统地址族（官方 docs 规则确定性生成+RPC 亲验，v4.1）| 高（官方规则） |
| defillama-por | 交易所自报 DefiLlama 透明度面板的储备地址（v4.1 SOL 四所）| 中（交易所自报，C 级） |
| chain-inference | 链上行为推断条目（four.meme fee、Mudra fee 等，非官方口径）| 中低（推断，报告引用需注明） |
| bitquery-community | 第三方数据商标注（Believe Authority 等）| 低（C 级单源） |

## 注入与清洗纪律（历史审计定论，重建时自动生效）

**OFAC/ScamSniffer 跨链注入（v4，codex 第二轮复核修正）**：先跑 `probe_codetype.py`（ETH 链批量 getCode，publicnode 须浏览器 UA）产出 codetype json → 构建器只对 **EOA** 三链注入（同私钥跨链同控成立）；**合约只入原链**（Tornado 等在他链是不同部署——2026-07-17 已清理 BSC/Base 各 147 条历史误注入）。codetype 文件缺失时构建器保守只入原链并告警。

**spellbook CEX 同纪律（v4.1，codex 第三轮复核）**：cex_evms 是同一批 4,957 地址三链展开——EOA 照入（同私钥），**某链无码但他链有码的行=合约空投影，skip**（2026-07-17 现库手术删 eth 24/bsc 93/base 414；多源行有独立链证据保留）。codetype 由 `probe_codetype.py` 对 `spellbook_cex_addrs.txt` 三链各跑一次（`spellbook_cex_codetype_{eth,bsc,base}.json`），缺失则照旧全入+告警。

**SOL 地址硬校验（v4.1，重大数据事故修复）**：spellbook cex_solana 混入 **55 条跨链垃圾**（BTC bech32/Cardano 切片/Elrond/hex 串——字符集+长度校验全过，纯属巧合）。`norm_addr` 已改为 **base58 解码必须恰好 32 字节**（validate/add_labels/构建器 upsert 全链路生效，重建自动过滤）。清洗审计记录：`sources/sol_cex_cleanup_20260717.json`（34 格式假+21 从未上链删除；14 条有历史签名但账户已回收标 historical）。教训：**上游"人工维护"≠格式可信，链上存在性是最后防线**。

**round-trip 铁律（v4.2，codex 第四轮复核修的三个断环）**：①`upsert()` 支持 merge_policy/balance_policy 透传（此前硬编码空——重建丢手工策略）；②**`sources/additions/` 目录整目录进重建流**——add_labels.py 增量入库成功后自动把补录 CSV 归档于此，重建全量回放（此前 v4.1 七份增量文件不在重建源里，全量重建会静默丢约 250 条 registry 级标签；**additions/ 里的文件永不删除**）；③SOL spellbook 垃圾黑名单（`sol_cex_cleanup_20260717.json` 的 never 名单）进构建流——21 条"格式合法但链上从无签名"的跨链垃圾此前删除只做在现库，重建即复活（v4.2 干跑实测抓出）。历史手术固化文件：`additions/curation_overrides_20260717.csv`（120 条 historical 状态）、`additions/recovered_increments_20260717.csv`（22 条未归档增量找回）、`additions/curation_overrides_20260718.csv`（12 条精修救回）。

## 重建与发布流程（v4.2+，顺序不可乱）

**在 `scripts/labels/` 目录执行**（benchmark 的 --labels-dir 按 cwd 解析，在 sources/ 里跑会 fail-fast 拒绝）：

```bash
cd ~/.claude/skills/token-chip-analysis/scripts/labels
( cd sources && python3 ../gen_manual_from_addressbook.py && python3 ../build_labels.py )
#    ↑ 构建末尾自动跑 validate_labels + check_manual_sync 双校验，任一 FAIL 拒绝发布
python3 roundtrip_check.py                       # 发布版 ⊆ 新构建（行级收敛门禁，稳定化新增）
python3 benchmark_labels.py --labels-dir=sources/out   # 发布前预检（fail-fast 已装）
cp sources/out/labels-*.csv ../../references/labels/   # 发布
python3 benchmark_labels.py --save               # 回归 PASS 才算完（七链强制出现，缺链即 FAIL）
python3 ../tests/labels_manifest.py --write      # 发布落印（校验和 manifest；add_labels 增量入库后同样要 --write）
```

- 构建器输出 v4 全列并自动拆 privacy 子表。
- 大文件源（accounts.csv/tokens.csv/brianleect）不在本地长存，重建前重下载：

```bash
P=http://127.0.0.1:7897   # GitHub raw 国内走代理
curl -sL -x $P -o accounts.csv https://raw.githubusercontent.com/dawsbot/eth-labels/v1/data/csv/accounts.csv
curl -sL -x $P -o tokens.csv   https://raw.githubusercontent.com/dawsbot/eth-labels/v1/data/csv/tokens.csv
curl -sL -x $P -o brianleect_eth.json https://raw.githubusercontent.com/brianleect/etherscan-labels/main/data/etherscan/combined/combinedAllLabels.json
curl -sL -x $P -o brianleect_bsc.json https://raw.githubusercontent.com/brianleect/etherscan-labels/main/data/bscscan/combined/combinedAllLabels.json
for A in ETH BSC SOL; do curl -sL -x $P -o ofac_$(echo $A|tr A-Z a-z).txt \
  https://raw.githubusercontent.com/0xB10C/ofac-sanctioned-digital-currency-addresses/lists/sanctioned_addresses_${A}.txt; done
curl -sL -x $P -o scamsniffer_address.json https://raw.githubusercontent.com/scamsniffer/scam-database/main/blacklist/address.json
# OFAC/ScamSniffer 更新后重跑 codetype（增量断点续跑）：
ETH_RPC="https://ethereum-rpc.publicnode.com" python3 ../probe_codetype.py ofac_eth.txt ofac_eth_codetype.json
ETH_RPC="https://ethereum-rpc.publicnode.com" python3 ../probe_codetype.py scamsniffer_address.json scamsniffer_codetype.json
```

**增量入库（免重建）与惯犯层刷新**：

```bash
cd sources && python3 ../add_labels.py my_additions.csv        # 合并进现库 + 自动 validate（FAIL 还原）
python3 ../accumulate_offenders.py && cd sources && python3 ../add_labels.py serial_actors.csv
```
- add_labels 成功后补录 CSV 自动归档进 additions/（round-trip 保证）；**人工精修（改 name/evidence/category 级别）不要走 add_labels 常规层——写成 curation override 文件**（source=curation），否则重建时会被 manual 同级"先到保留"规则回退。

**Dune 月度刷新**（credits 消耗大，按需执行）：①网页登录 dune.com 跑 query 7999252（免费层 API 不能 execute）→ ②`python3 dune_fetch_results.py ~/.config/dune/api-key 7999252 dune_labels_v2.csv` → ③tornado 版按 api-keys.md 第 14 节「Dune」 SQL 临时替换再跑（29 万行 ≈500+ credits，非必要不刷）→ ④重跑重建流程。坑：labels.addresses 语义键是 model_name 不是 category；SOL 地址 varbinary hex 须转 base58（构建器内置）。**B8 审计结论（2026-07-17）**：BSC tornado-user 来自 spellbook `tornado_cash_bnb` 解码事件模型（四面额合约 join transactions 取 from），链上抽验 9/10 命中——数据为真，语义正确；用户经 proxy `0x0d5550d5…` 调用（查交互勿直接 filter to=面额合约）。

## 回归基准（扩容/重建后必跑）

`build_goldset.py`（15 份历史 appendix 抽 entity 281 + **random-eoa 负样本 120**（低频普通交易者，sha256 确定性抽样，v4 新增——修复 BSC/Robinhood 之外链 entity 金标趋零的门禁失衡）+ manual 设施）→ `benchmark_labels.py [--save]`。
- **硬断言**：entity+random-eoa 错误 exclude **必须为 0**（>0=聚类漏庄/误杀散户，exit 1）；manual 设施召回 **100%**。
- **弱门禁显式化（v4）**：entity+random-eoa 合计 <10 的链输出 ⚠️ 弱门禁警告——**该链 PASS 不代表有防线**，不再假装（当前弱门禁链：base/eth——无本地历史大数据可抽负样本）。
- 金标与库冲突时：浏览器官方标签亲验裁决，记入 `ARBITRATED`（首例：GME 案"L1 金主"实为 ChangeNOW 16）。
- 评价库以此基准与 Top-holder 命中率为准，**不以总行数**（privacy 层 29 万行不计入主表口径，正是为了戒掉行数虚荣）。

## 守门员维护（gatekeeper.py 阈值与校准）

- 判定阈值：`FUNNEL` = fan_in≥30 且 fan_out≥30 且净留存率≤5% 且总笔数≥80；`FUNNEL_CANDIDATE` = 对手方总数≥120 且留存≤15%。
- **校准基线**（2026-07-17，bibi BSC 20.5 万转账 + TRASH Robinhood 9.9 万转账）：47 个 appendix 实体地址误伤 0（连候选提示都 0）；已知设施交叉确认 10；净增益 8 个库外真漏斗。**阈值任何改动必须重跑两案校准**。
- 扩容闭环：FUNNEL 命中且静态库无记录 → 自动进 miss 队列（最高优先级回填候选）→ 人工判明身份 → add_labels 回填。行为发现→人工确认→静态库成长，取代"审计轮脑补扩容"。

## 开放扩容路线
- **P1 余款** Base bundler/paymaster 快照定期刷新（HyperSync 聚合法已沉淀；2026-07-17 快照，≥1000 笔/≥900 UserOp 阈值，bundler EOA 会轮换）；韩所 SOL 正式标签持续物色（当前守门员兜底）。
- **P1 余款** △ 协议官方 deployment registry 持续扩容（Safe deployments / Hyperlane 合约页——机制已建：official_registry.csv + add_labels.py，逐案补）。
- **P1 余款** Robinhood 工厂事件回放（PoolCreated/ProxyCreation）+ verified-contracts 候选池首轮人工审（`pull_verified_contracts.py` 定期增量拉，同名家族=克隆工厂线索，**只产候选不自动入库**）。
- **P1 余款** ETH/BSC/Base 主流 DEX V3/V4 池按 factory 事件批量入库（SPX6900 案 2 个 UniswapV3Pool 不在库、以"18 址归集点"面目误导一轮狙击集团分析——pool-probe 四测能证伪但要多付一轮；标签库前置拦截＝零轮成本。方法同上条 Robinhood 工厂回放线：HyperSync 按 factory 地址过滤 PoolCreated（V4 加 PoolManager Initialize）一次拉全链池地址表，dex 类目 tier=exclude 入库后 cluster resolver 直接拦截；topic0 实施时经 openchain.xyz lookup 核验，勿凭记忆写）（2026-07-25）。
- **P2** 做市商 taxonomy 彻底归一（多值 roles；raw_labels 列已铺路）+ manual 层单一真源改造（check_manual_sync 已装牙齿，重构缓行）。
- **P2** SOL 风险层数据源物色（社区 drainer 库多为 EVM；SolanaFM/Solscan 标签 API 付费墙，待再评估）。
- **P2** △ CryptoScamDB：2021 年后停更、误报风险大于价值——**评估后不接**（2026-07-17 决定）。
- **不接** △ WalletLabels（官方示例在 Solana 端点返回 EVM 地址，数据质量红旗）。
- **待补录**：神鱼（需人工 intel.arkm.com 补全后按纪律 6 入库）；大宇（来源推文已锁）；Time.fun 程序 ID（官网 TLS 拦+无 docs，暂无权威来源）；Boop 5 个 boop 前缀关联地址（fee/config/vault 类身份未定，暂不入表——见 sources/ 调研记录）。

## SOL CEX 扩容妙法（v4.1 实战验证）

GMGN holders API 的 `name` 字段是最高效标签通道——十个头部 meme 币 top100 扫一遍即覆盖主流 CEX 归集地址（MEXC/Gate 主力钱包即此法+链上亲验入库），后续扩容其他所直接复用。
