# 批量地址标签库（labels/）——使用篇

> **分析时读本文件即可**；重建/扩容/审计/发布看 `MAINTENANCE.md`（维护篇，v3.0 稳定化拆分——分析会话不再背维护史）。

**定位**：与 `address-book.md`（手工实战核验层，~180 条）互补的**批量兜底层**（v4.2+ 2026-07-18，七链 ~47.1 万条）。目的：CEX/桥/路由/协议/发射台等基础设施地址在聚类前被系统性识别剔除，不再等踩坑后回填；惯犯庄家（serial-actor）命中即高亮。
**防线定位**：静态库的目标是「**库里每条都对**」而非「全」——设施是开放集合永远追不全，"全"由**行为守门员**（`gatekeeper.py`，漏斗形状运行时判定）兜底，未知设施由守门员拦截→miss 队列→人工确认→回填本库，实战驱动闭环扩容。
**分工三层**：①本库批量查询（静态已知标签）→ ②address-book.md（实战核验、含机制注释）→ ③分析时动态判别（守门员漏斗指纹 + getCode/owner/行为画像，见各链 data-pipeline）。**三层是递进关系：库无记录≠白户**，新链新设施仍靠动态判别，判明后回填 manual 层。
**接入方式（v4）**：`labels_resolver.py` 共享内核——`label_lookup.py`（人工查询）、EVM `cluster.py`/`analyze_holdings.py`、SOL `replay_edges.py`/`build_evolution.py`（阵营体检）、HL `main_metrics.py`、FIL `cluster.py` 均已默认接入（`--no-labels` 关闭）；表缺失/加载失败显式报 **degraded_mode**（"没命中"与"没加载"可区分），分析产物落 `labels_meta`。

## 文件一览

| 文件 | 条数（v4.2） | 一句话 |
|---|---|---|
| labels-eth.csv（+privacy 166,690） | 140,029 | 主表；tornado-user 拆 privacy 子表，resolver 加载时自动合并 |
| labels-bsc.csv（+privacy 123,604） | 15,157 | BSC 主表+tornado 隐私层（数据已审计为真） |
| labels-base.csv | 14,185 | 含 AA 层（bundler/paymaster 36 条——gas 溯源假金主盲区的解药） |
| labels-sol.csv | 8,180 | validator/KOL/CEX/程序；韩所盲区见已知局限 |
| labels-robinhood.csv | 293 | 含 serial-actor 177 条（惯犯层主战场） |
| labels-hyperliquid.csv | 936 | 含 HyperCore 系统转移地址族 472 |
| labels-filecoin.csv | 25 | filfox 官方标签低位段 |
| codehash-robinhood.csv | 3 模板 | 字节码组合指纹（fingerprint_check.py） |
| miss-queue/<chain>.csv | 滚动 | 分析时自动记录的未命中高权重地址，人工审后回填 |

CSV 字段（基础 9 列 + 6 扩展列）：`address, chain, name, category, tier, source, added_date, evidence, risk_flags, merge_policy, balance_policy, source_snapshot_at, verified_at, status, raw_labels`（扩展列旧行可为空，空值走 resolver 推导）。

## 决策语义（v4 三维拆分）

- **merge_policy**（能否作聚类合并边）：`no_merge` = tier=exclude **或** category ∈ {locker, airdrop-distributor, token-sale, charity, launchpad, suspected-cex}（公共多对一/一对多通道，合并全是假连；launchpad 平台地址与用户的边全是公共通道边）。CSV 列非空时覆盖推导。
- **suspected-cex**：未确证设施的标准归宿——`identity + no_merge + count`（**禁边不剔仓**）。铁律：**"疑似/未确证"条目不得 tier=exclude**（万一它其实是大户，exclude 会把真实持仓静默藏掉）。确证后才升 cex/exclude。
- **balance_policy**（实体持仓怎么算）：`exclude`（设施，不计持仓/大户榜）| `bucket`（locker/分发器，锁仓量单列桶）| `count`（正常计入）。
- **exclude ≠ 从资金图删除**："经 XX 桥入金"的路径叙事保留，它们是边界节点不是空气。cluster.py 被拦地址落 `label_excluded_nodes` 供对账。
- **risk_flags 四档分区（白名单制）**：**definitive**（白名单精确命中或 `*-exploit` 后缀：大户命中=必写进报告的重大信号）| **candidate**（scam-candidate 等社区单源：降权提示，不作定性依据）| **privacy**（tornado-user：只陈述"有 Tornado 使用记录"，不定性脏钱）| **unknown**（白名单外：提示人工核验，不自动定性）。
- **serial-actor（惯犯庄家层）**：历史分析实锤收割集团地址（3.18.0 起 1741 址，双源自动回灌——appendix.json + analysis-state.json，不买入的筛查案也进）。**不剔除、不禁边**（惯犯地址间本就同实体，正常聚类），命中即高亮"XX 案实锤惯犯"；跨案命中是最高优先级信号。**每次分析交付后固定动作**：`accumulate_offenders.py --apply`（含 manifest 落印）。⚠收纳是组级的（实锤组全组地址进库）——大组（如 QUQ 215 址 bot 体系、SIREN 散仓网）含一次性执行地址，命中远端成员时按"提示不定罪"复核，别直接当工作室核心。**跨案身份冲突检测（3.19 内置；3.19.1 起设施级硬闸）**：候选地址同时是主库设施身份（cex/infra/bridge/dex/bundler/paymaster/mev）或命中 benchmark 设施金标时，写 `sources/serial_conflicts_<日期>.json/.md` 报告，且 **primary/goldset-infra 级冲突地址被硬闸拦在 serial_actors.csv 外**（--apply 与手动 add_labels 两条入库路径一并挡住；secondary/cross_chain 仅提示）——设施被误收进庄家成员表入库会**高置信覆盖掉主库设施行、聚类禁边失效**（实案全程：QUQ 案大庄#1 误吸 PancakeSwap Infinity Vault（0x238a…，其 QUQ 余额仅 1.5 万枚纯属流经关联），2026-07-22 --apply 覆盖事故→用户裁决=curation 恢复主库设施身份+QUQ 案侧摘出成员表 215→214+加本硬闸）。**被拦地址逐条裁决**，三选一：①案源实体划分误吸设施→修该案 whale_groups 重跑（曲线/份额在案侧注记"下次更新重算"）②主库标签错→走 curation override（MAINTENANCE.md；add_labels 的 HIGH_TRUST_PREFIX 含 curation，增量入库即可压掉现行）③确属庄家自建专用设施→手工编辑 CSV 单独 add_labels 并在 evidence 注明裁决依据（绕闸必须人工显式动作，无 --force）。
- **标签时效（3.18.0，提示不定罪）**：resolver 输出附 `stale_days`（距最近核验/快照/入库天数）与 `stale_hint`（时效敏感类目 cex/suspected-cex/infra/bridge/bundler/paymaster/mev 超 90 天）。纪律：①stale_hint 命中且该标签**驱动了剔除/合并决策**时，交付前对该地址浏览器/RPC 复核一次，不得裸信过期设施标签（Bitget 热钱包误判、Base bundler 轮换两案教训）；②自动决策**不因库龄变老而失效**（防设施剔除整体瓦解）；③人工确认已失效的行标 `status=deprecated/rotated/historical`——余额侧自动回退（不剔仓），**聚类禁边保留**（全历史重放里退役设施活跃期的边仍是公共边）；④单源标签（source 单一且非 manual/registry）不得独自驱动实体合并或剔除，须第二证据。

## 用法（分析流程标准前置步骤，playbook §3 第零步）

```bash
# 聚类前把全部候选大户/关联地址过一遍
python3 ~/.claude/skills/token-chip-analysis/scripts/labels/label_lookup.py --chain sol ADDR1 ADDR2 ...
python3 .../label_lookup.py --chain robinhood --file candidates.txt   # 文件每行一地址
cat addrs.txt | python3 .../label_lookup.py --chain bsc --misses      # --misses 列出未命中
python3 .../label_lookup.py --chain hyperliquid --json --file a.txt   # JSONL 机器可读（脚本管道）

# Robinhood 链疑似公共 bot 合约 → 查字节码模板指纹（新部署秒判）
python3 .../fingerprint_check.py --chain robinhood ADDR1 ADDR2
```
- lookup 输出七段：**SERIAL / RISK / RISK-CANDIDATE / RISK-UNKNOWN / EXCLUDE / IDENTITY / PRIVACY**，带来源、证据链与 policy 视图。
- 非 sol/eth/filecoin 链自动对 eth 表做 **EVM 同址联查**（cross_chain 提示级：EOA=同私钥可信；CREATE2 canonical=同部署流程；普通合约同址≠同实体）。**自动决策只认目标链直接命中**。
- 脚本内嵌入用 `labels_resolver.LabelResolver(chain)`：`get()` / `is_exclude()` / `no_merge()` / `balance_policy()` / `is_serial()` / `policy()`（完整决策视图）/ `risk_partition()`（四档）/ `warn_if_degraded()`（启动必调）/ `meta()`（写产物）。`append_misses()` 记 miss 队列。
- **miss 队列纪律**：cluster/analyze/replay-top 自动落盘"未命中的高度数节点/共同 funder/top 持仓"。定期人工审：跨 token 反复出现者优先核验（MM/基金/设施高概率），判明回填 manual 层——最省人力的扩容路径。
- 入库/回填/重建 → 一律看 MAINTENANCE.md（`add_labels.py` 有 curation 层语义，别裸用）。

## 行为守门员（gatekeeper.py，使用视角）

未知设施的兜底防线：漏斗形状（多进多出、过手不留存、对手方分散）运行时判定，`FUNNEL` 命中自动禁作合并边（与 exclude 同语义），`FUNNEL_CANDIDATE` 只提示不决策。evm/cluster.py 默认启用（`--no-gatekeeper` 关闭）——R1 直转边与 R2 gas 种子双拦截；serial-actor/team 白名单豁免。命中明细落 `clusters.json.gatekeeper_blocked` 对账。两案校准误伤 0（阈值与校准纪律见 MAINTENANCE）。互补性：设施在单案切片里可能低频（形状显不出）——静态库兜住；新设施库里没有——行为兜住。

## 运行时风险通道（GoPlus 恶意地址体检）

`goplus_check.py --chain <链> --file <地址清单>`——查询式 API（无法下载黑名单入库），分析时对候选大户批量体检。免费 30 次/分钟（脚本自带 2.2s 限速+断点缓存）；EVM 链是主力；**Solana 覆盖未证实**（OFAC SOL 制裁地址实测返回全 0——SOL 结果仅供参考勿当"无风险"）。**纪律同 candidate 档**：命中=降权提示+人工核验线索，不作定性依据；报告措辞「GoPlus（数据源 XX）标注该地址有 XX 行为记录」。用法：label_lookup 之后对未命中库的候选跑。

## 使用纪律（报告措辞与证据边界；codex 两轮复核融合）

1. **KOL 标签=「某时点有证据由该账号控制」，不是永久所有权**。报告措辞用"该地址曾由 X 自证/被 X 来源标注"，不写"X 控制该集群"（除非多钱包各有独立控制证据）。
2. **证据分级**（evidence 列已标）：A=本人公开自证；B=两独立来源+行为吻合；C=单源社区标注——**C 级只作候选展示，不作实体定论依据**。
3. GMGN 的 `smart-money` 是**行为标签不是人物身份**；tags 里带 `wash_trader` 的 KOL 战绩含刷量水分。
4. 推特 handle 会改名/转让——存的是抓取时点 handle，考证历史用 memory.lol。
5. **身份不随转账传播**：KOL 旧钱包给新钱包打过钱≠新钱包是 KOL。新钱包归属要独立证据。
6. 钱包被盗/转让后按事件时间切分：事件后的交易不归因原主。
7. CEX 热钱包照旧纪律：**全体用户共享，不可作地址关联依据**（见 address-book.md 头部）。
8. mev-bot 标签=Etherscan 认定的夹子/套利 bot；**发射狙击集团不在此列**，仍会正常进聚类——勿以为"跑过标签库=庄家已排除"。
9. **tornado-user 旗标的措辞纪律**：用过 Tornado ≠ 脏钱——报告写"该地址有 Tornado Cash 使用记录"陈述事实即可；但"庄家资金源头是 Tornado 提取"是必写的重大风险信号。name 区分 Depositor/Recipient（后者资金来源不可溯，信号更强）。
10. **serial-actor 纪律（与铁律 1 的张力，明文划界）**：惯犯层保存的是**历史案的实锤定性**，与铁律 1"结论不复用"存在张力——划界如下：惯犯命中=**改变搜索优先级的提示线索**（触发深查、跨案命中必须写进报告），**不=本案定罪**——地址可能被转卖/弃用，写进报告前必须有**本案独立证据链**（当前行为+案源证据并列呈现）；措辞固定为"该地址在 XX 案中被实锤为 YY 集团成员，本案中其行为 ZZ"。警惕确认偏差：命中惯犯后对其"有罪推定"式取证是被禁止的——阴性排查照做，查完独立成立才写。
11. **codehash 指纹纪律**：指纹命中=candidate 级（同模板 hash 不同可能是 immutable 差异，同 hash 也可能是代理壳）——**行为复核后才升 exclude**；指纹只缩小排查范围不下定论。

## 已知局限（分析时的盲区地图）

- **韩国四所 SOL 地址=公开标签源系统性盲区**：Upbit/Bithumb/Coinone/Korbit 无官方 PoR、Dune/spellbook/GMGN 全空。现有覆盖：疑似 Upbit 热钱包 2 条（suspected-cex 禁边不剔仓）+攻击者 3 条（heist）。**韩流币分析时韩所归集主要靠守门员行为拦截兜底**，判明后回填。
- **Base bundler/paymaster 名单是时点快照**（2026-07-17，7 日窗口）：bundler EOA 会轮换——遇 AA 大户先核时效（刷新法见 MAINTENANCE）。
- **SOL 覆盖薄的本质**：静态库标的是程序/CEX/KOL，真正持币的池子 vault/bonding curve 托管是 per-token PDA，**没法静态穷举**——由 data-pipeline-solana 动态判别负责。SOL 静态风险层仍缺（ScamSniffer 仅 EVM、GoPlus SOL 未证实）。
- **Robinhood**：发射台工厂持续新增 per-launch 实例，增量靠现场 getCode+指纹库+Blockscout 核验回填。
- **做市商 taxonomy 碎裂**：Wintermute 等碎在 cex/dao-multisig/fund/market-maker/专名 5 类——查 MM 用名字 grep 别只查类目；raw_labels 列保留原始标签。
- **EVM 三链 KOL 层薄**（各约 20 条）。
- **Arbitrum Orbit 地址 aliasing**：L1 合约跨链调用到 Robinhood L2 时 msg.sender = L1 地址+0x1111…1111（模 2^160）——遇 0x1111…11 偏移特征先逆算再查 eth 表。
- **EIP-7702**：getCode 非空≠合约（可能是委托 EOA），判别见 address-book 7702 段。
- **时态**：热钱包会轮换——**大额结论落笔前对关键地址抽查现场行为**；历史热钱包不删除（保留"曾属于"信息，分析旧数据时需要）。
