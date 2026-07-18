# 批量地址标签库（labels/）

**定位**：与 `address-book.md`（手工实战核验层，~180 条）互补的**批量兜底层**（v4.2 2026-07-17，七链 ~47.1 万条）。目的：CEX/桥/路由/协议/发射台等基础设施地址在聚类前被系统性识别剔除，不再等踩坑后回填；惯犯庄家（serial-actor）命中即高亮。
**防线定位（v4.2 起明确）**：静态库的目标是「**库里每条都对**」而非「全」——设施是开放集合永远追不全，"全"由**行为守门员**（`gatekeeper.py`，漏斗形状运行时判定）兜底，未知设施由守门员拦截→miss 队列→人工确认→回填本库，实战驱动闭环扩容。
**分工三层**：①本库批量查询（静态已知标签）→ ②address-book.md（实战核验、含机制注释）→ ③分析时动态判别（守门员漏斗指纹 + getCode/owner/行为画像，见各链 data-pipeline）。**三层是递进关系：库无记录≠白户**，新链新设施仍靠动态判别，判明后回填 manual 层。
**接入方式（v4）**：`labels_resolver.py` 共享内核——`label_lookup.py`（人工查询）、EVM `cluster.py`/`analyze_holdings.py`、SOL `replay_edges.py`/`build_evolution.py`（阵营体检）、HL `main_metrics.py` 均已默认接入（`--no-labels` 关闭）；表缺失/加载失败显式报 **degraded_mode**（"没命中"与"没加载"可区分），分析产物落 `labels_meta`。重建/扩容后必跑 `benchmark_labels.py` 回归基准。

## 文件与口径

| 文件 | 条数(2026-07-17 v4.2) | 说明 |
|---|---|---|
| labels-eth.csv | 140,029 | 主表（tornado-user 已拆 privacy 子表）；v4.2：**17 条 Alchemy/Candide/Stackup bundler+paymaster 从 identity 修正为 exclude**（长尾类目错标，会参与聚类的休眠炸弹）+EntryPoint v0.6+Relay 10 solver+Across/deBridge/LiFi/Socket 合约层 |
| labels-eth-privacy.csv | 166,690 | 隐私体积层：纯 tornado-user 行（resolver 加载时自动合并，对使用方透明） |
| labels-bsc.csv | 15,157 | v4.2：+Safe 官方部署家族 24（getCode 亲验）+Relay 4 solver+deBridge DLN 5+LiFi 3+Socket 2+EntryPoint v0.6；DxLock status 错位行源头修复 |
| labels-bsc-privacy.csv | 123,604 | BSC tornado-user（B8 已审计：spellbook 事件级模型+链上抽验 9/10 命中，数据为真） |
| labels-base.csv | 14,185 | v4.2：**+Base 活跃 bundler 24 + paymaster 12（HyperSync 7 日 33 万 UserOp 链上聚合，此前 AA 层=0 是 gas 溯源假金主最大盲区）**+Safe 家族 24+Relay 21 solver+Seaport/Banana Gun Router 错标修正 |
| labels-sol.csv | 8,180 | v4.2：+疑似 Upbit 热钱包 2（suspected-cex 禁边不剔仓）+Upbit 被黑攻击者 3（heist）；"疑似 OKX"改 suspected-cex；**韩所官方标签源系统性盲区**（见已知局限） |
| labels-robinhood.csv | 293 | v4.2：+Safe 家族 24（4663 官方 registry 有登记，getCode 亲验已部署）+Relay solver 第 5 个+EntryPoint v0.6/v0.7；TRASH 案 serial+21 等未归档增量已固化进 additions/ |
| labels-hyperliquid.csv | 936 | v4.1：+HyperCore 系统转移地址族 472（0x20+token index，spotMeta 确定性生成）+CEX 词典修 8 条+entity 二审 19 条；**赌池 no_merge 覆盖已进金标作 round-trip 活体断言（v4.2）** |
| labels-filecoin.csv | 25 | v4 首建：filfox 官方标签 f00–f0126 低位段；v4.2 起 filecoin/cluster.py 真正接入 resolver（此前 README 宣称接入与事实不符） |
| codehash-robinhood.csv | 3 模板 | 字节码组合指纹库（fingerprint_check.py，公共 bot 卖币合约三变体） |
| miss-queue/<chain>.csv | 滚动 | 实战 miss 队列：分析时自动记录的未命中高权重地址，人工审核后回填 |
| benchmark/ | goldset 567 条 | 回归金标（entity 281 + random-eoa 120 + infra 166）+ 历史 result JSON |

CSV 字段（v4 = 基础 9 列 + 6 扩展列）：`address, chain, name, category, tier, source, added_date, evidence, risk_flags, merge_policy, balance_policy, source_snapshot_at, verified_at, status, raw_labels`（扩展列旧行可为空，空值走 resolver 推导）。

## 决策语义（v4：三维拆分，替代"tier 单字段身兼多职"）

- **merge_policy**（能否作聚类合并边）：`no_merge` = tier=exclude **或** category ∈ {locker, airdrop-distributor, token-sale, charity, **launchpad, suspected-cex**（v4.2）}（公共多对一/一对多通道，合并全是假连——v3 只拦 locker 是逻辑洞，Multisender 类曾可合法缝假集群；launchpad 平台地址与用户的边全是公共通道边）。CSV 列非空时覆盖推导。
- **suspected-cex（v4.2 新类目）**：未确证设施的标准归宿——`identity + no_merge + count`（**禁边不剔仓**）。铁律：**"疑似/未确证"条目不得 tier=exclude**（万一它其实是大户，exclude 会把真实持仓静默藏掉；曾有"疑似 OKX 归集"直接 exclude 的先例）。确证后才升 cex/exclude。validate 不变量 14 强制。
- **balance_policy**（实体持仓怎么算）：`exclude`（设施，不计持仓/大户榜）| `bucket`（locker/分发器，锁仓量单列桶）| `count`（正常计入）。
- **exclude ≠ 从资金图删除**："经 XX 桥入金"的路径叙事保留，它们是边界节点不是空气。cluster.py 被拦地址落 `label_excluded_nodes` 供对账。
- **risk_flags 四档分区（白名单制，v4 修复"未知旗标一律 definitive"的休眠炸弹）**：
  - **definitive**（白名单精确命中或 `*-exploit` 后缀）：大户命中=必写进报告的重大信号；
  - **candidate**（scam-candidate 等社区单源）：降权提示，不作定性依据；
  - **privacy**（tornado-user）：只陈述"有 Tornado 使用记录"，不定性脏钱（纪律 9）；
  - **unknown**（白名单外一切旗标）：提示人工核验，不自动定性——构建端 validate_labels 同步强制白名单，未知旗标**禁止入库**。
- **serial-actor（惯犯庄家层，v4 新增）**：历史分析实锤收割集团地址（`accumulate_offenders.py` 从 15 份 appendix 聚合 196 址+人工白名单）。**不剔除、不禁边**（惯犯地址间本就同实体，正常聚类），命中即高亮"XX 案实锤惯犯"；跨案命中（首建即发现 CASHCAT 工作室 2 址现身 NOXA 案）是最高优先级信号。收纳纪律宁缺毋滥：「疑似/边界/观察」一律不收，纯"项目方"组不收（例外走人工白名单并注明记忆存档依据）。
- **旗标卫生规则（构建器强制）**：burn 地址剥全部旗标；exclude 设施剥行为型旗标（tornado-user），定性型保留（被制裁的 CEX 双属性并存）。

## 用法

```bash
# 聚类前把全部候选大户/关联地址过一遍（分析流程标准前置步骤，playbook §3 第零步）
python3 ~/.claude/skills/token-chip-analysis/scripts/labels/label_lookup.py --chain sol ADDR1 ADDR2 ...
python3 .../label_lookup.py --chain robinhood --file candidates.txt   # 文件每行一地址
cat addrs.txt | python3 .../label_lookup.py --chain bsc --misses      # --misses 列出未命中
python3 .../label_lookup.py --chain hyperliquid --json --file a.txt   # JSONL 机器可读（脚本管道）

# Robinhood 链疑似公共 bot 合约 → 查字节码模板指纹（新部署秒判）
python3 .../fingerprint_check.py --chain robinhood ADDR1 ADDR2
python3 .../fingerprint_check.py --chain robinhood --add ADDR --name "..." --evidence "..."  # 取样入库

# 增量入库（免重建）：补录 CSV → 合并进现库 + 自动校验
cd .../scripts/labels/sources && python3 ../add_labels.py my_additions.csv

# 惯犯层刷新（新分析归档后跑一次，然后入库）
python3 .../accumulate_offenders.py && cd sources && python3 ../add_labels.py serial_actors.csv
```
- lookup 输出七段：**SERIAL / RISK / RISK-CANDIDATE / RISK-UNKNOWN / EXCLUDE / IDENTITY / PRIVACY**，带来源、证据链与 policy 视图。
- 非 sol/eth/filecoin 链自动对 eth 表做 **EVM 同址联查**（cross_chain 提示级：EOA=同私钥可信；CREATE2 canonical=同部署流程；普通合约同址≠同实体）。**自动决策只认目标链直接命中**。
- 脚本内嵌入用 `labels_resolver.LabelResolver(chain)`：`get()` / `is_exclude()` / `no_merge()` / `balance_policy()` / `is_serial()` / `policy()`（完整决策视图）/ `risk_partition()`（四档）/ `warn_if_degraded()`（启动必调）/ `meta()`（写产物）。`append_misses()` 记 miss 队列。
- **miss 队列纪律**：cluster/analyze/replay-top 自动落盘"未命中的高度数节点/共同 funder/top 持仓"。定期人工审：跨 token 反复出现者优先核验（MM/基金/设施高概率），判明回填 manual 层——这是最省人力的扩容路径，取代"有什么源灌什么"。

## 数据源与重建

| 源 | 内容 | 置信 |
|---|---|---|
| manual/addressbook | 实战核验条目（含全部 Robinhood 独家）| 最高，优先级压过一切 |
| serial-offenders | 惯犯层（appendix 聚合+人工白名单，196 址）| 最高（实锤定性） |
| registry-official | 官方 deployment registry（Aerodrome/Clanker/Zora/Uniswap/Virtuals 官方仓库·npm 包·docs 亲验，Base 54 条首建）| 高（官方源） |
| manual-chainverify | 链上事件/RPC 亲验条目（Tornado BSC 合约、WHYPE）| 高（链上实测） |
| hypurrscan-aliases | Hyperliquid 463 实体 | 高（浏览器官方标签） |
| manual-filfox | Filecoin 官方 tag（f00–f0126）| 高（官方浏览器） |
| spellbook（Dune/hildobby）| EVM CEX 统一表 4957、SOL CEX 164、桥 177、基金 51 | 高（人工维护） |
| manual-rhdocs | Robinhood 官方 docs 协议合约 | 高（官方） |
| manual-ofac | OFAC SDN 制裁地址（**v4 起 EOA 才三链注入**，见下）| 高（权威原始源） |
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

**OFAC/ScamSniffer 跨链注入纪律（v4，codex 第二轮复核修正）**：先跑 `probe_codetype.py`（ETH 链批量 getCode，publicnode 须浏览器 UA）产出 codetype json → 构建器只对 **EOA** 三链注入（同私钥跨链同控成立）；**合约只入原链**（Tornado 等在他链是不同部署——2026-07-17 已清理 BSC/Base 各 147 条历史误注入）。codetype 文件缺失时构建器保守只入原链并告警。

**spellbook CEX 同纪律（v4.1，codex 第三轮复核）**：cex_evms 是同一批 4,957 地址三链展开——EOA 照入（同私钥），**某链无码但他链有码的行=合约空投影，skip**（2026-07-17 现库手术删 eth 24/bsc 93/base 414；多源行有独立链证据保留）。codetype 由 `probe_codetype.py` 对 `spellbook_cex_addrs.txt` 三链各跑一次（`spellbook_cex_codetype_{eth,bsc,base}.json`），缺失则照旧全入+告警。

**SOL 地址硬校验（v4.1，重大数据事故修复）**：spellbook cex_solana 混入 **55 条跨链垃圾**（BTC bech32/Cardano 切片/Elrond/hex 串——字符集+长度校验全过，纯属巧合）。`norm_addr` 已改为 **base58 解码必须恰好 32 字节**（validate/add_labels/构建器 upsert 全链路生效，重建自动过滤）。清洗审计记录：`sources/sol_cex_cleanup_20260717.json`（34 格式假+21 从未上链删除；14 条有历史签名但账户已回收标 historical）。教训：**上游"人工维护"≠格式可信，链上存在性是最后防线**。

**round-trip 铁律（v4.2，codex 第四轮复核修的三个断环）**：①`upsert()` 已支持 merge_policy/balance_policy 透传（此前硬编码空——重建丢手工策略）；②**`sources/additions/` 目录整目录进重建流**——add_labels.py 增量入库成功后自动把补录 CSV 归档于此，重建全量回放（此前 v4.1 七份增量文件不在重建源里，全量重建会静默丢约 250 条 registry 级标签；**additions/ 里的文件永不删除**）；③SOL spellbook 垃圾黑名单（`sol_cex_cleanup_20260717.json` 的 never 名单）进构建流——21 条"格式合法但链上从无签名"的跨链垃圾此前删除只做在现库，重建即复活（v4.2 干跑实测抓出）。**历史手术的固化文件**：`additions/curation_overrides_20260717.csv`（120 条 historical 状态）、`additions/recovered_increments_20260717.csv`（22 条未归档增量找回）。

重建：`sources/` 目录里 `python3 ../gen_manual_from_addressbook.py && python3 ../build_labels.py` → **双校验 PASS**（validate_labels 旗标白名单+status 枚举+设施类目/AA/疑似不变量 + check_manual_sync 双真源一致性，任一 FAIL 即拒绝发布）→ **发布前预检 `python3 ../benchmark_labels.py --labels-dir=sources/out`（v4.2 新参数）** → `cp out/labels-*.csv ../../../references/labels/` → **`python3 ../benchmark_labels.py --save` 回归 PASS 才算完（v4.2 起七链强制出现，缺链即 FAIL）**。构建器输出 v4 全列并自动拆 privacy 子表。**HL/FIL 两表由加工产物源直接进重建流**（`hyperliquid_additions.csv` / `filecoin_additions.csv`，分别由 `build_hyperliquid_labels.py` / `build_filecoin_labels.py` 维护——要刷新先跑它们再 build；这两个文件或 `official_registry.csv` 等 _EXTRA_SOURCES 缺失时构建器会告警，**此时勿 cp 覆盖现库**，否则 HL/FIL 表退化）。大文件源（accounts.csv/tokens.csv/brianleect）不在本地长存，重建前按下方命令重下载：
```bash
P=http://127.0.0.1:7897   # GitHub raw 国内走代理
curl -sL -x $P -o accounts.csv https://raw.githubusercontent.com/dawsbot/eth-labels/v1/data/csv/accounts.csv
curl -sL -x $P -o tokens.csv   https://raw.githubusercontent.com/dawsbot/eth-labels/v1/data/csv/tokens.csv
curl -sL -x $P -o brianleect_eth.json https://raw.githubusercontent.com/brianleect/etherscan-labels/main/data/etherscan/combined/combinedAllLabels.json
curl -sL -x $P -o brianleect_bsc.json https://raw.githubusercontent.com/brianleect/etherscan-labels/main/data/bscscan/combined/combinedAllLabels.json
for A in ETH BSC SOL; do curl -sL -x $P -o ofac_$(echo $A|tr A-Z a-z).txt \
  https://raw.githubusercontent.com/0xB10C/ofac-sanctioned-digital-currency-addresses/lists/sanctioned_addresses_${A}.txt; done
curl -sL -x $P -o scamsniffer_address.json https://raw.githubusercontent.com/scamsniffer/scam-database/main/blacklist/address.json
curl -s -x $P https://api.hypurrscan.io/globalAliases -o hypurrscan_aliases.json
# OFAC/ScamSniffer 更新后重跑 codetype（增量断点续跑）：
ETH_RPC="https://ethereum-rpc.publicnode.com" python3 ../probe_codetype.py ofac_eth.txt ofac_eth_codetype.json
ETH_RPC="https://ethereum-rpc.publicnode.com" python3 ../probe_codetype.py scamsniffer_address.json scamsniffer_codetype.json
```

**Dune 月度刷新流程**（credits 消耗大，按需执行）：①网页登录 dune.com 跑 query 7999252（免费层 API 不能 execute）→ ②`python3 dune_fetch_results.py ~/.config/dune/api-key 7999252 dune_labels_v2.csv` → ③tornado 版按 api-keys.md 第 13 节 SQL 临时替换再跑（29 万行 ≈500+ credits，非必要不刷）→ ④重跑 build_labels.py。坑：labels.addresses 语义键是 model_name 不是 category；SOL 地址 varbinary hex 须转 base58（构建器内置）。**B8 审计结论（2026-07-17）**：BSC tornado-user 来自 spellbook `tornado_cash_bnb` 解码事件模型（四面额合约 join transactions 取 from），链上抽验 9/10 命中——数据为真，语义正确；用户经 proxy `0x0d5550d5…` 调用（查交互勿直接 filter to=面额合约）。

## 使用纪律（KOL 层为主；codex 两轮复核融合）

1. **KOL 标签=「某时点有证据由该账号控制」，不是永久所有权**。报告措辞用"该地址曾由 X 自证/被 X 来源标注"，不写"X 控制该集群"（除非多钱包各有独立控制证据）。
2. **证据分级**（evidence 列已标）：A=本人公开自证；B=两独立来源+行为吻合；C=单源社区标注——**C 级只作候选展示，不作实体定论依据**。
3. GMGN 的 `smart-money` 是**行为标签不是人物身份**；tags 里带 `wash_trader` 的 KOL 战绩含刷量水分。
4. 推特 handle 会改名/转让——存的是抓取时点 handle，考证历史用 memory.lol。
5. **身份不随转账传播**：KOL 旧钱包给新钱包打过钱≠新钱包是 KOL。新钱包归属要独立证据。
6. 钱包被盗/转让后按事件时间切分：事件后的交易不归因原主。
7. CEX 热钱包照旧纪律：**全体用户共享，不可作地址关联依据**（见 address-book.md 头部）。
8. mev-bot 标签=Etherscan 认定的夹子/套利 bot；**发射狙击集团不在此列**，仍会正常进聚类——勿以为"跑过标签库=庄家已排除"。
9. **tornado-user 旗标的措辞纪律**：用过 Tornado ≠ 脏钱——报告写"该地址有 Tornado Cash 使用记录"陈述事实即可；但"庄家资金源头是 Tornado 提取"是必写的重大风险信号。name 区分 Depositor/Recipient（后者资金来源不可溯，信号更强）。
10. **serial-actor 纪律（v4）**：惯犯命中=触发深查，不=自动定罪——地址可能被转卖/弃用，按案源证据链+当前行为独立核验后才写进报告；措辞"该地址在 XX 案中被实锤为 YY 集团成员"。跨案命中必须写进报告。
11. **codehash 指纹纪律（v4）**：指纹命中=candidate 级（同模板 hash 不同可能是 immutable 差异，同 hash 也可能是代理壳）——**行为复核后才升 exclude**；指纹只缩小排查范围不下定论。

## 回归基准（扩容/重建后必跑）

`build_goldset.py`（15 份历史 appendix 抽 entity 281 + **random-eoa 负样本 120**（低频普通交易者，sha256 确定性抽样，v4 新增——修复 BSC/Robinhood 之外链 entity 金标趋零的门禁失衡）+ manual 设施）→ `benchmark_labels.py [--save]`。
- **硬断言**：entity+random-eoa 错误 exclude **必须为 0**（>0=聚类漏庄/误杀散户，exit 1）；manual 设施召回 **100%**。
- **弱门禁显式化（v4）**：entity+random-eoa 合计 <10 的链输出 ⚠️ 弱门禁警告——**该链 PASS 不代表有防线**，不再假装（当前弱门禁链：base/eth——无本地历史大数据可抽负样本）。
- 金标与库冲突时：浏览器官方标签亲验裁决，记入 `ARBITRATED`（首例：GME 案"L1 金主"实为 ChangeNOW 16）。
- 评价库以此基准与 Top-holder 命中率为准，**不以总行数**（privacy 层 29 万行不再计入主表口径，正是为了戒掉行数虚荣）。

## 行为守门员（gatekeeper.py，v4.2 新增——未知设施的兜底防线）

**动机**：静态库只防"已知的"设施；新桥/新所钱包/新 bot 每天在增长，漏一条就把成百上千散户缝成假庄家。而漏斗的行为学特征是**封闭知识**：多进多出、过手不留存、对手方分散——交易所热钱包/桥/路由不管叫什么名字，资金流形状都是漏斗；庄家是水库（进得多出得少、对手方集中）。

- **判定**（纯本地，零额外 RPC）：`FUNNEL` = fan_in≥30 且 fan_out≥30 且净留存率≤5% 且总笔数≥80 → 自动禁作合并边（与 exclude 同语义）；`FUNNEL_CANDIDATE` = 对手方总数≥120 且留存≤15% → 只提示不决策。
- **校准**（2026-07-17，bibi BSC 20.5 万转账 + TRASH Robinhood 9.9 万转账）：**47 个 appendix 实体地址误伤 0**（连候选提示都是 0）；已知设施交叉确认 10；净增益 8 个库外真漏斗（含一个 BSC 侧未标注的跨链同址服务合约，行为层直接抓住）。阈值改动必须重跑两案校准。
- **接入**：evm/cluster.py 默认启用（`--no-gatekeeper` 关闭）——R1 直转边与 R2 gas 种子双拦截；serial-actor/team 白名单豁免（它们的形状由案源证据定性）。命中明细落 `clusters.json.gatekeeper_blocked` 对账（防误伤不可审计）。
- **扩容闭环**：FUNNEL 命中且静态库无记录 → 自动进 miss 队列（最高优先级回填候选）→ 人工判明身份 → add_labels 回填本库。**行为发现→人工确认→静态库成长**，取代"审计轮脑补扩容"。
- 互补性实证：设施在单案数据切片里可能低频（形状显不出来）——静态库兜住；反之新设施库里没有——行为兜住。两道防线缺一不可。

## 运行时风险通道（v4.1 新增，与静态库互补）

**GoPlus 恶意地址体检**：`goplus_check.py --chain <链> --file <地址清单>`——address_security 是查询式 API（无法下载黑名单入库），做成分析时对候选大户的批量体检。免费 30 次/分钟（脚本自带 2.2s 限速+断点缓存）；EVM 链是主力（不带 chain_id 也可查通用库，OFAC 攻击地址实测命中 stealing_attack/源 SlowMist）；**Solana 覆盖未证实**（OFAC SOL 制裁地址实测返回全 0——SOL 结果仅供参考勿当"无风险"）。**纪律同 candidate 档**：命中=降权提示+人工核验线索，不作定性依据；报告措辞「GoPlus（数据源 XX）标注该地址有 XX 行为记录」。用法：playbook §3 第零步 label_lookup 之后对未命中库的候选跑。

## 已知局限

- **韩国四所 SOL 地址=公开标签源系统性盲区（v4.2 调研定论）**：Upbit/Bithumb/Coinone/Korbit 无官方 PoR 披露、Dune/spellbook/GMGN 全空（spellbook 的"Korbit"5 条是 BTC 地址错标已入黑名单；库里 Bithumb 开头两条是 validator vanity 陷阱勿认）。现有覆盖：疑似 Upbit 热钱包 2 条（被黑事件 signer 反查 B 级，suspected-cex 禁边不剔仓）+攻击者 3 条（heist）。**韩流币分析时韩所归集主要靠守门员行为拦截兜底**，判明后回填。
- **Base bundler/paymaster 名单是时点快照**（2026-07-17 起 7 日窗口，≥1000 笔/≥900 UserOp 阈值）：bundler EOA 会轮换新增——刷新用 scratchpad 同款 HyperSync 聚合法重跑；ETH 的 AA 层来自 dune（1184 条），BSC/Robinhood AA 流量近零暂无需专项。
- **SOL 覆盖薄的本质**：静态库标的是程序/CEX/KOL，真正持币的池子 vault/bonding curve 托管是 per-token PDA，**没法静态穷举**——由 data-pipeline-solana 动态判别负责。SOL 静态风险层仍缺（ScamSniffer 仅 EVM、GoPlus SOL 覆盖未证实）；运行时体检走 goplus_check.py（EVM 可用）。
- **SOL CEX 扩容妙法（v4.1 实战验证）**：GMGN holders API 的 `name` 字段是最高效标签通道——十个头部 meme 币 top100 扫一遍即覆盖主流 CEX 归集地址（本轮 MEXC/Gate 主力钱包即此法+链上亲验入库），后续扩容其他所直接复用。
- **Robinhood**：发射台工厂持续新增 per-launch 实例，增量靠现场 getCode+指纹库+Blockscout 核验回填；v4.1 起 `pull_verified_contracts.py` 定期增量拉 verified-contracts 候选池（sources/robinhood_verified_contracts.csv，同名家族=克隆工厂线索，人工审后按角色补录——**只产候选不自动入库**）。
- **做市商 taxonomy 碎裂**：Wintermute 等碎在 cex/dao-multisig/fund/market-maker/专名 5 类——查 MM 用名字 grep 别只查类目；v4 起 raw_labels 列保留原始标签（重建后生效），彻底归一列 P2。
- **EVM 三链 KOL 层薄**（各约 20 条）：GMGN track 单窗口去重约 120 钱包饱和，靠 accumulate_gmgn.py 滚动多跑。
- **Arbitrum Orbit 地址 aliasing**：L1 合约跨链调用到 Robinhood L2 时 msg.sender = L1 地址+0x1111…1111（模 2^160）——遇 0x1111…11 偏移特征先逆算再查 eth 表。
- **EIP-7702**：getCode 非空≠合约（可能是委托 EOA），判别见 address-book 7702 段。
- **时态字段已建但旧行未回填**：source_snapshot_at 按源推导已填；verified_at 只有 manual/registry/chainverify 层有值。热钱包会轮换——**大额结论落笔前对关键地址抽查现场行为**（纪律不变）。历史热钱包不删除（保留"曾属于"信息，分析旧数据时需要）。
- **Virtuals Base 侧 bonding/AgentFactory**：官方 docs 未公示地址，按"禁凭记忆"纪律未收——下次分析 Base agent 币时现场核验回填（miss 队列会自动抓到）。

## 扩容路线（△=codex 建议；✅=已落地）

- ✅ ~~P0 决策语义三维拆分 + risk 白名单 + NO_MERGE 扩类目~~（v4 2026-07-17）
- ✅ ~~P0 SOL/HL 主流程接 resolver + degraded_mode~~（v4）
- ✅ ~~P0 金标扩衡（random-eoa 负样本+弱门禁显式化）~~（v4）
- ✅ ~~P0 Base 定向补录（Aerodrome/Clanker/Zora/Uniswap V4/Virtuals 54 条官方亲验）~~（v4）
- ✅ ~~P1 实战 miss 队列~~ / ~~惯犯 serial-actor 层~~ / ~~Robinhood codehash 组合指纹~~ / ~~OFAC/ScamSniffer EOA 分流~~ / ~~时态字段~~ / ~~Hypurrscan 463 入库+HL pipeline~~ / ~~BSC tornado 审计~~（v4 全落地）
- ✅ ~~P2 Filecoin 表+f 地址规范化~~ / ~~tornado 拆独立 privacy 索引~~ / ~~manual 双真源校验~~（v4）
- ✅ ~~v4.1（2026-07-17 覆盖面专项，codex 第三轮复核）：spellbook CEX 三链合约投影分流（删 531）；SOL CEX 垃圾清洗 55 条+norm_addr base58 硬校验；HL CEX 词典/系统地址族 472/entity 二审；BSC 现役桥 30/router 18/locker 17/four.meme 家族 11；SOL 四所热钱包 23+Jupiter Lock/Bonfida/Boop；GoPlus 运行时通道；Robinhood verified-contracts 增量脚本~~
- ✅ ~~v4.2（2026-07-17 闭环专项，codex 第四轮复核）：round-trip 三断环修复（upsert policy 透传/additions 目录进重建流/SOL 垃圾黑名单）；ETH 17 条 AA identity 错标修正+构建器 AA/Seaport/设施类目归一规则；validate 不变量 11-14（status 枚举/设施≠identity/AA 必须 exclude/疑似不得 exclude）；benchmark 七链强制+--labels-dir 预检+policy 活体断言；行为守门员 gatekeeper.py（两案校准误伤 0）+cluster 接入+miss 联动；Filecoin cluster 接 resolver；Safe 官方家族 72（bsc/base/robinhood getCode 亲验）；Relay 22 solver+Across/deBridge/LiFi/Socket 合约层 95；Base bundler 24+paymaster 12（HyperSync 33 万 UserOp 聚合）；EntryPoint v0.6 四链；SOL 韩所疑似 2+heist 3~~
- **P1 余款** Base bundler/paymaster 快照定期刷新（HyperSync 聚合法已沉淀）；韩所 SOL 正式标签持续物色（当前守门员兜底）。
- **P1 余款** △ 协议官方 deployment registry 持续扩容（Safe deployments / Hyperlane 合约页——机制已建：official_registry.csv + add_labels.py，逐案补）。
- **P1 余款** Robinhood 工厂事件回放（PoolCreated/ProxyCreation）+ verified-contracts 候选池首轮人工审（同名家族→按角色补录）。
- **P1 余款** HL 系统地址族随新 spot 资产增量刷新（重跑 spotMeta 快照+build_hyperliquid_labels.py，机制已建）。
- **P2** 做市商 taxonomy 彻底归一（多值 roles；raw_labels 列已铺路）+ manual 层单一真源改造（check_manual_sync 已装牙齿，重构缓行）。
- **P2** SOL 风险层数据源物色（社区 drainer 库多为 EVM；SolanaFM/Solscan 标签 API 付费墙，待再评估）。
- **P2** △ CryptoScamDB：项目 2021 年后停更、数据陈旧误报风险大于价值——**评估后不接**（2026-07-17 决定）。
- **不接** △ WalletLabels（官方示例在 Solana 端点返回 EVM 地址，数据质量红旗）。
- **待补录**：神鱼（需人工 intel.arkm.com 补全后按纪律 6 入库）；大宇（来源推文已锁）；~~DxLock/FlokiFi/GemPad locker~~（✅ v4.1 已亲验入库，含 Mudra/DeepLock/CryptEx）；Time.fun 程序 ID（官网 TLS 拦+无 docs，暂无权威来源）；Boop 5 个 boop 前缀关联地址（fee/config/vault 类身份未定，暂不入表——见 sources/ 调研记录）。
