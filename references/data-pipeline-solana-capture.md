# Solana 数据管线 · 采集与重建工程（data-pipeline-solana 分册 2/2）

> 母文档：`data-pipeline-solana.md`（已拆为薄路由索引页；来源声明与 `[VERIFIED·IO实录]` 等标注图例见索引页）。本册覆盖原 **§6 待重建脚本清单 / §7 验证清单 / §8 SQD 实测补充 / §9 锚点法演变重建 / §10 快照对比法增量更新 / §11 长币龄混合重建 / §12 销户账户覆盖审计 / §13 采集加速工程（13a–13d）**；§0–§5 见 `data-pipeline-solana-scan.md`。正文 §N 交叉引用一律为母文档节号。规则逐条原样迁移、零改写；最后整编 2026-07-22。

## 6. 待重建脚本清单（与 scripts/solana/README.md 同步）

IO 当时全程用会话内联 Python 完成、未沉淀成脚本文件；但找回的会话实录含全部内联代码（含 base58 手写实现、RPC 重试封装、pre/postTokenBalances 解码器），重建时可直接参照——实录存档见 `~/Desktop/老公用/fable筹码分析/windows IO筹码分析会话记录/26a24d6c-*.jsonl`（同上级目录还有当时的最终报告 `IO代币筹码分析报告.md`；若找不到则问用户要位置）。重建时逐个补上"限速可调、退避重试、断点续传、冒烟小样本先行"四件套：

1. **全量扫描器 `scan_token_accounts.py`**（通用，任何 SPL 代币复用）
   - getProgramAccounts 按 mint 过滤全量拉非零 token account（含 dataSlice 优化与 Token-2022 分支）；
   - 落盘原始账户表（account 地址 / owner / amount）。
2. **owner 聚合器**（可并入 1，也可单列）
   - 按 owner 去重聚合余额，输出"token account 数 vs 独立持有人数"双口径；
   - 产出五档分层集中度表 + 每 owner 的 token account 计数（老鼠仓排查输入）。
3. **vesting PDA / 托管识别器 `classify_top_holders.py`**（半通用）
   - Top N 地址批量走第 2 节两跳判别（Squads / Magna / System），结合本地标签库打 CEX / 金库 / vesting / 大户标签；
   - 内含月度机械解锁指纹检测 + 整除法反推 vesting 参数（第 3 节）。
4. **解锁款穿透追踪器 `trace_token_flow.py`**（通用）
   - 给定地址集拉近 90 天 SPL 转账，构建转账图谱（每条边带日期 + 精确金额，可直接渲染成报告里的 ASCII 图谱）；
   - 检测共用中转地址、按解锁日时间窗过滤、终点二分（CEX / 囤币）归类；
   - 实现要点 `[VERIFIED·IO实录]`（坑的完整版见 §3a）：
     - `getSignaturesForAddress` 按"交易提及该地址"索引——追代币流水要查 **token account 地址**而非 owner 钱包（他人发起的转入只会提及 token account）；`limit` 上限 1000，用 `before` 游标翻页到目标时间窗；
     - 逐笔解析优先读 `getTransaction(encoding=jsonParsed)` 的 `meta.preTokenBalances / postTokenBalances`：自带 owner 与 uiTokenAmount，能覆盖 CPI 内部转账，比解析 transfer 指令更稳；**必须按 mint 过滤 + decode 确认本尊有变动**（防投毒与他币污染，§3a）；
     - 转账指令里的 source/destination 是 token account 地址，映射回钱包必须经 tokenBalances 的 owner 字段，直接当钱包用会把图谱建错。
5. 补充资产：
   - `market_snapshot.py`：一键拉 CoinGecko 日线 + Coinglass OI/费率，输出量价结构摘要（通用）；
   - `cex_label_book.json`：手工维护的 Solana CEX 钱包标签库（每条带证据链接），跨项目累积复用价值最高。
- 工程纪律 `[INFERRED，来自前次报告硬伤]`：同一地址在正文/附录多处引用时，必须由脚本从落盘数据统一生成，交付前做全文地址一致性自查——前次报告曾出现正文与附录同一托管地址写法不一致的硬伤；关键字符串（地址/哈希）一律取自落盘文件，禁止从终端打印输出复制补全。

## 7. 验证清单（2026-07-12 经 IO 实录考古大幅勾销，遗留项如下）

原"首战验证清单"多数项已被找回的 IO 会话实录回答（getProgramAccounts 行为=§1、组合过滤生效=§1、Squads/Magna ID=§2、Solscan WebFetch 不可直读=§0b、DropsTab/Tokenomist/Coinglass 可达=§4）。**遗留待验证**：

- [x] ~~Token-2022 大扫描分支~~ 已实战：CLUDE(Solana) 2026-07-13，走 api.mainnet-beta 无 dataSize 全扫（§0a/§1），脚本 `scan_token_accounts.py` 已收编
- [ ] `is_on_curve` 预筛提速（§2）未实战验证
- [ ] 双 RPC 屏蔽面可能随时间漂移——publicnode 报 `Request blocked` / mainnet-beta 报 429 时按 §0a 矩阵换位，若矩阵本身失效则当场更新本文档
- [ ] 本机（Mac + clash）对 publicnode 大扫描的真实表现（IO 实录环境为 Windows 直连，本机未跑过百 MB 级响应）
- [ ] 五档分层默认档位是否适配目标代币的供应量级，不适配就按数量级平移
- [ ] 分析收尾按阶段 6 复盘：本文档逐条修订 + 重建脚本沉淀进 scripts/solana/ 并更新其 README.md

---

## 8. 后续实测补充（2026-07-12，来自另一项目的 Solana meme 币分析实战，置信度高于上文反推内容）

以下通道已在真实分析中跑通，标注 [实测·他场景]，直接可用：

1. **全量转账首选 SQD portal**（portal.sqd.dev，免 key 免代理）——直接补上"免费 RPC 无 archive 历史回放"的洞。已收编为独立脚本 `scripts/solana/fetch_sqd_transfers.py`（v1.3 自 meme 项目 chip_analysis.py 提取，逻辑未动；自带断点缓存于工作目录 `data/soltx-<小写mint>.jsonl.gz`、回补验证与墙钟保险丝，用法见脚本 docstring；原始出处 `~/Desktop/老公用/meme币叙事总结/scripts/chip_analysis.py`）。转账边=同 tx 内 owner 级净变动贪心配对，from/to 为 ZERO 哨兵即铸造/销毁。**增量更新场景实战验证**：meta.json 的 next_slot 断点续拉无缝无重叠（"连续完成前缀"机制天然防 off-by-one），同目录直接重跑即增量拉取；34 链上小时增量（46 万 slot、483 边）约 10 分钟拉完，续拉后全量重放 vs 链上全扫快照逐地址零差异（来源：PUB(Solana) 增量更新，2026-07-15）。
   **吞吐量化预期（做计划时先算这笔账）**`[VERIFIED·CLUDE实战]`：pump.fun 发射日高密度段实测 90 分钟仅推进 2.3 链上小时（≈1.5x 实时）；常规密度段 240 分钟推进 16.5 小时（≈4x 实时）。推论：对 4-5 个月币龄的币做全程重放需 24h+ 挂机不现实——**Plan B 架构**（发射窗口 SQD 精确 + 核心实体 RPC 全流水逐笔 + 池子 CPMM 数学重建 + 散户残差 + 快照对账封口）是标准替代，其中 CPMM 中段实测端点偏差可达 35~49%（小时K取样的 10% 是侥幸值），报告必须声明"仅供形状参考"。（来源：CLUDE(Solana) 分析，2026-07-13）
2. **发射期精确定价**：GeckoTerminal 分钟 K `/ohlcv/minute?aggregate=1&limit=1000&before_timestamp=`（池创建起就有）；小时 K 翻页可拿全历史。pump.fun"发射即迁移"币无内盘 K 线，内盘成本用 GMGN dev avg_cost 近似。
3. **资金同源（gas 溯源）**：公共 RPC `getSignaturesForAddress`（翻到最老）+ `getTransaction(jsonParsed)` 找首笔 system transfer 入金 source；0.25s 间隔+走 clash 代理，45 地址约 4 分钟。识别马甲网络最有效的一招（母钱包收敛即实锤）。
4. **洗仓识别模式**（已两次实见）：老仓→一次性中转→全新地址 双跳、间隔约 20 秒、批量链条数分钟内完成——GMGN 会把新仓显示为 transfer_in+当日成本，必须重放溯源拆穿。
5. **★铸造边全清单必查（pump.fun 币拿到 SQD 边后的第一优先检查项）**`[VERIFIED·PUB实战]`：**pump.fun 创建交易的铸造边可以有 2 条**——bonding curve 拿 ~95.7%，**dev-buy 直分拿剩余部分，且收币地址可以不是 creator 本人**。PUB 教训：主分析阶段只盯 creator 地址，创建 tx 同秒直分给另一地址的 4.24% 供应被漏掉，靠对抗复核才抓回——而它恰是"项目方系已套现一轮"的最强证据，直接改写庄家定性。固化动作：边加载后第一步跑 `replay_edges.py mints` 列出**全部**铸造边及收币地址；creator 系集群从"创建 tx 的全部受益地址"起步，而非从 creator 单地址起步（来源：PUB(Solana) 分析，2026-07-14）。
6. **pump.fun 内盘 bonding curve 成本重建的参数校准法**`[VERIFIED·PUB实战]`：恒定乘积虚拟储备重建（标准参数 vs0=30 SOL / vt0=1,073,000,191）对**买入枚数逐位精确**（token 守恒不受 wash 影响），但 **SOL 成本系统性低估约 10%**（实际虚拟储备参数有偏移，PUB 实测 ≈32.5/1034M）。正解：关键笔（creator 买入等）用 `getTransaction` 的 preBalances/postBalances 拿链上实付真值校准；批量笔按"重建值 +10% 修正区间"报告。**另一坑：毕业迁移笔会混进"买家"列表**（外盘池地址一笔巨量"买入"且 SOL 数疑似 wSOL 双计）——重建时必须剔除迁移笔，迁移的真实 SOL 用 GT 外盘开盘价锚定。脚本 `scripts/solana/curve_cost.py`（--grad-price 自校准告警 / --exclude 剔迁移）（来源：PUB(Solana) 分析，2026-07-14）。

（来源：CLAW(Solana) 分析，2026-07-12，经 onchain-data-accounts 记忆转录；第 5/6 条为 PUB(Solana) 2026-07-14 补充）

## 9. 锚点法演变重建 + gas 溯源加固（LAYOFF(Solana) 2026-07-15 实战）

针对"4-5 个月币龄全量 SQD 挂机不现实"的 Plan B 的一个更轻量替代，已在 LAYOFF 跑通：

1. **锚点法演变重建（免全量 SQD，`scripts/solana/build_evolution.py`）**：不重放每一笔，而是——①`fetch_pool_sigs.py` 拉主池全史签名（LAYOFF 138 万签名，失败率 33% 属 pump AMM 正常，只用成功笔）；②等距抽 ~550 个签名做**池子余额锚点**（`decode_txs.py --pool <池owner>` 每笔落 `pool_balance`）；③核心实体（top 大户 + 离场盈利榜 + 上游中转，~65 个）用 `whale_deep.py` 拉 ATA 级全流水；④`build_evolution.py` 在 ~400 个时间点插值：各实体持仓从其逐笔流水累积、流动性池用锚点曲线、散户=总供应−已知−池−销毁残差。产出图1/图2 数据。**精度声明**：中小散户是残差估算，量级正确、单点精度有限，报告局限性须写明。
2. **decode 通道坑**：`getTransaction` 直连 `api.mainnet-beta` **恒 429**，必走 clash 代理（`decode_txs.py --proxy http://127.0.0.1:7897`）；requests.Session 连接复用比 curl 逐发快约 3 倍。dRPC 免费层 Solana 需付费（`chain is not available on freetier`），别用。
3. **gas 溯源翻页上限（`gas_fast.py`，gas_origin.py 的加固）**：原 `gas_origin.py` 的 `oldest_sigs` 翻到最老全部，遇高频中转（数千签名）**卡死**（LAYOFF 实测 20 地址跑 15 分钟）——加 `max_pages=2` 上限、超深标 approx；落仓户签名少一页到底、秒完成。**遗留 TODO：把 max_pages 回填进 skill 的 gas_origin.py。**
4. **★高频服务热钱包识别（聚类防污染，取代"任意 funder"）**：gas 聚类必须取每个地址**最早一笔 SOL 入金**的 funder，不是任意交互对手——否则会把持 426 SOL、近千签名仅覆盖 4 分钟（6000+笔/分钟级）的做市/服务热钱包（本次 `AgmLJBMD`，owner=System 但巨额+超高频）误当共同母钱包，把无关大户假合并。识别姿势：疑似共源 funder 先查 `getAccountInfo`（lamports 巨大）+ 近 1000 签名的时间跨度（<10 分钟即服务）。此坑由对抗复核抛出、主分析核实。（来源：LAYOFF(Solana) 分析，2026-07-15）
5. **发射窗 decode 的 AMM 路由噪声**：pump.fun 发射瞬间的 owner delta 会混入 AMM/路由中间账户的巨额瞬时余额（LAYOFF 实测单笔 delta 达总供应数十倍），**不能直接当持仓变动**——发射日 bundle 识别改用 GMGN bundler 标签兜底，别硬 decode 发射窗算 bundle 归属。
6. **pump.fun creator 履历 + set_creator 洗白识别（dev 背景调查核心）**`[VERIFIED·LAYOFF实战]`：①`frontend-api-v3.pump.fun/coins?creator=<addr>` 列 creator 名下全部发币（LAYOFF dev 名下 8 币，前作"Official 89 Coin"ATH $2.43M 后归零）；②**RugCheck 对 creator 的历史币报告会打「Creator history of rugged tokens」danger 标签**——查 dev rug 前科的免费权威源；③**set_creator 洗白**：pump.fun 支持发射后更换链上 creator，对比标的与 dev 其他币的 RugCheck creator 字段，creator 被换成干净关联账户=标的报告不再显示 dev 前科（LAYOFF 把 creator 从有 rug 史的主地址换成关联账户，RugCheck 对 LAYOFF 显示零风险）。
7. **Streamflow feePayer 洗筹指纹实战命中**`[VERIFIED·LAYOFF实战]`：gas 溯源出某归集地址 funder=`wdrwhnCv4pzW8beKsbPa4S2UDZrXenjg16KJdKSpb5u`（Streamflow 自动提取服务）= 该地址通过 Streamflow 收币、切断资金溯源（pipeline §2 已记的指纹，本次首次实战命中）；穿透去向靠 whale_deep 找谁收了它的币（LAYOFF 终点是已识别的关联组成员）。（来源：LAYOFF(Solana) 分析，2026-07-15）
8. **★scan_token_accounts.py 双坑（增量更新同目录二跑必踩）**`[VERIFIED·PUB增量实战]`：①Token-2022 `--datasizes all` 全扫**必须显式 `--rpc https://api.mainnet-beta.solana.com`**——脚本默认 rpc=publicnode 对 Token-2022 恒 504（§0a 已记，但默认参数会让人忘传）；②v2.8.0 前的 rpc_call 只查"文件存在且>0 字节"即判成功——**16 字节的 `error code: 504` 错误体被当有效缓存写入 `_gpa_raw_*.json`**，且缓存命中逻辑（>100B 即复用）会静默复用旧数据：PUB 增量实测"全扫成功"返回的实为 2 天前旧快照（质押池/creator 余额全是旧值），与重放对账假性炸出 24.6% 差异，靠**独立单查三点仲裁**（getTokenAccountsByOwner 逐个验关键地址）才定位真凶。对策：增量重扫前把旧 `_gpa_raw_*.json` 改名存档强制真扫；脚本已加固（返回体须为含 result 的合法 JSON 才落缓存+缓存命中打 mtime 告警，v2.8.0）。对账炸掉时的仲裁纪律：**先用第三通道单查 2-3 个关键地址定"谁是旧数据"，再决定修哪边**——别急着怀疑重放管道（来源：PUB(Solana) 增量更新，2026-07-15）。

## 10. 快照对比法增量更新（/token-update 的 Solana 特化形态，CLUDE 增量实战定型 2026-07-15）

旧研报为锚点法（非全量流水重放）时，增量更新**不必补拉全量转账**，走快照对比五步（1.8 天窗口全程 <1 小时数据成本）：

1. **新全量快照**：`scan_token_accounts.py`（Token-2022 记得 `--rpc api.mainnet-beta` + 先把旧 `_gpa_raw_*` 改名存档，见 §9.8）；同时 `getTokenSupply` 复验供给闭合（窗口内销毁体现在总量差）。
2. **快照 diff**：`snapshot_diff.py --old 旧owners --new 新owners --entities 实体表` → 实体逐址变动 + 大额变动榜（新面孔/清零标注）。**排名变化不是证据**（持有人增多会把静止地址挤出 topN），一切以余额 Δ 为准。
3. **窗口流转定性**：`probe_window_moves.py --targets 变动榜 --cutoff <ISO时间>` → 每址 pool_buy/pool_sell/direct_transfer 分类 + 直转对汇总（换仓/洗仓/归集识别）。**大额变动地址要 100% 覆盖定性，抽样会漏换仓对**（CLUDE 首轮抽 17 址被复核抓漏 1 对，补扫 38 址才闭合）；直转对金额取对手方 |Δ| 口径。
4. **对账三查（轻量版）**：新快照加总=getTokenSupply（diff=0）；top20 与 `getTokenLargestAccounts` 双源对表（活跃池允许时点差）；重点地址签名史净额 vs 快照 Δ 分毫互验。
5. **观察哨核查加固**：余额不变≠没动（可能转出又转回）——sentinel 级地址补签名列表验证（窗口内零签名才是硬结论）。

配套纪律：**cutoff 时间戳一律 `datetime.fromisoformat` 验算，禁止手算 unix 秒**（实战手算错 2 天导致签名史首跑作废，且错误 cutoff 不报错、只静默漏数据）；数据文件 meta 的 `updated` 字段是"最后写入时间"不是"覆盖范围"，增量起点判定看数据末行而非 meta（发射日流水文件 updated=07-13 但只覆盖 02-24，望文生义会把增量起点定错 4.5 个月）。（来源：CLUDE(Solana) 增量更新，2026-07-15）

## 11. 长币龄混合重建 + 高密度期定向采集（USELESS(Solana) 2026-07-21 实战）

§8"全程 SQD 重放不现实"与 §9 锚点法的合体升级——14 个月+币龄、13.5 万持仓账户量级标的实战定型：

1. **混合重建演变架构（长币龄标准件，两端精确、中段插值）**：①发射窗（发射日起 24-48h）用 `window_fetch.py` 拉全量边（精确——狙击/bundle 分析必须逐笔）②核心实体（庄/项目方/大户）ATA 级全流水（`whale_deep.py`，精确）③中段日级锚点前向填充（`anchor_sampler.py`）④**当前快照封口 + 末日快照注入**——把 data_cutoff 日全量快照作为最后一个锚点注入序列，修"清仓发生在锚点观测窗外则旧值永久残留"的系统性尾部误差。图 1/图 2 由 ①②③④ 合成，散户=残差；精度声明照 §9 写进局限性（来源：USELESS(Solana) 分析，2026-07-21）。合成器参考实现：GOAT 案 `compose_evolution.py`（锚点 owner 级前向填充 + 末日快照真值封口 + 发射日零基线 + 散户残差；**工作目录 GOAT分析/ 专属存档，非复用件**——实体分组、发射日、价格文件名按案硬编码，新案参考其算法结构重写；通用化抽象列遗留）（来源：GOAT(Solana) 分析，2026-07-22）。
2. **SQD 高密度期定向拉取用小段+并发（`window_fetch.py`）**：密集期（发射窗/事件日）正解=**2000 slot 小段 × 8 并发**，失败段落 `.gaps.json`（必须为空才算完整）。反面教训：fetch_sqd_transfers 的 50K 大段在发射期反复 curl 超时截断重试，120 分钟只推进 3.4 链上小时；小段版 29 秒拉完 1 万 slot、发射日 24h（16.5 万边）82 分钟零缺口。**gap 段补拉合并纪律（GOAT 实测坑）**：标 gap 的段**仍会写出部分数据**——补拉后与原文件 cat 追加合并=重复边（GOAT 案 9,212 行重复）；重复合并的快查指纹=**重放负余额账户数暴增**（534 → dedup 后 1）。正解：gap 段用补拉版**整段替换**（按 slot 区间切除旧段再并入）或合并后全字段 dedup；重放见两位数以上负余额账户，先查重复合并再查采集通道。另：发射窗峰值榜必剔 pump.fun 官方毕业迁移钱包（address-book Solana 平台表，20.7% 级协议常数过手），否则误判狙击集团（来源：GOAT(Solana) 分析，2026-07-22）。
3. **日级锚点采样（`anchor_sampler.py`）与它的观测边界（★阴性依据禁用）**：从新到旧滚动校准 slot↔ts（分段线性外推、漂移 >4h 自动重估，435 天约 5s/天）。**⚠观测窗真相**：名义 1h 窗（9000 slot）在高活跃期因响应截断实际仅 ~3.6 分钟，且 SQD tokenBalances 只记**发生变动**的账户——静止大户被系统性漏观测。因此**锚点单独不可作任何"某地址没动/没持仓"的阴性依据**，阴性结论必须快照或全流水兜底；锚点只用于正向变动观测与序列插值（对抗复核实测抓出，来源：USELESS(Solana) 分析，2026-07-21）。**【候选·单案】锚点复用两扫描（easy/混合重建建议必做步，零边际成本）**：锚点序列采完后顺手做 ①**全 owner 峰值普查**（阈值 ≥1.5% 总供应）——产出"历史大仓名单"（含已清仓离场者），补当前快照视角的系统性盲区（快照只见在场者）；②**全史前三涨跌日×锚点对照**——最大涨/跌日与该日锚点观测交叉，抓事件日实体动作指纹（如拉高日金库调拨）。GOAT 案完整性复核 4 条 must_add 有 3 条半源于缺这两步（历史离场大仓×2、离场庄扩容、事件日调拨）（来源：GOAT(Solana) 分析，2026-07-22）。
4. **publicnode 大扫描死角补充（§0a/§1 的边界）**：13.5 万 token account 量级的 mint，publicnode getProgramAccounts 恒 504（dataSlice 也救不回）；**api.mainnet-beta 做 SPL 大扫描会静默返回空结果**（不报错——危险，靠对账关卡拦住，勿当"该 mint 无账户"）。分片扫描（`scan_sharded.py`，amount 低位字节递归分片）可行但两个坑：①owner 位置 memcmp 必须整 32 字节（1 字节分片语法合法但过滤不生效）②零余额账户 8 字节 amount 全零、全部堆在全零前缀片——递归下钻全零前缀至 8 字节终点片直接跳过（分析只要非零余额）。USELESS 案分片全量未跑完（publicnode 间歇 504），对账改用"8 样本独立单查 + top20 对表"替代过关——**分片器待后续标的全量验证**。**死角地图更新（GOAT 实测）**：24.7 万 token account / 67MB 响应量级，Helius + `--compressed`(gzip) + 300s 长超时**一次拉全成功**（publicnode 恒 504、Helius 默认 120s 超时也断；见 §1 实测升级行）——大盘子 mint 的 GPA 正解就位，分片器降级为末位备选（来源：GOAT(Solana) 分析，2026-07-22）。
5. **whale_deep 按地址频率分派（先估频再选通道）**：深挖前先 getSignaturesForAddress 拉一页估频——高频地址（creator 类，签名 7 万+）ATA 级全 decode 需数小时/地址不可行，改**事件窗定向拉**（只 decode 关键时间窗）；低频囤仓户（15-172 笔）全量 decode 秒-分钟级。一刀切全量 decode 会把预算烧在单个高频地址上（来源：USELESS(Solana) 分析，2026-07-21）。**cap 截断样本的用途边界 + Helius 并发纪律（GOAT 增量）**：高频地址签名史翻到工具 cap（如 2000 笔）即**截断样本**——起点余额非零，**不可从零累积重建持仓时间线**，只能作"最近 N 笔行为定性样本"（流向画像/对手方指纹），时间线必须锚点/快照兜底且报告局限声明注明"截断样本"；Helius 免费档 10 RPS 是**账号级**配额——多进程并行互抢配额反而整体拖慢（实测 5 进程时单笔 decode 拖到 0.6-1.2s），正解 = `whale_deep.py --out` 分组独立文件防写冲突 + 总并发贴 10 RPS 不超发（来源：GOAT(Solana) 分析，2026-07-22）。
6. **letsbonk 平台币三件套（§8.5/§8.6 的平台变体，vs pump.fun 差异）**：①铸造边 2 条——curve 拿大头 + dev 直分一笔，且 **dev-buy 可在数秒内卖回**（实测 6 秒）制造"creator 已清仓"表象——creator 状态判定必须看直分笔的后续流向，不能只看当前余额；②**creator fee 走 Raydium Lock 的 burn&earn harvest 账本**（非 pump.fun 费领取模式）——费农收入=真实收益引擎，dev"弃盘与否"必查 harvest 流水；③毕业迁移约 20.7% 供应入 Raydium 池（来源：USELESS(Solana) 分析，2026-07-21）。

## 12. 销户账户覆盖审计（SQD 边集对账盲区加固，2026-07-21）

**盲区原理**：`getProgramAccounts` 快照只见**当前存活**的 token account；被 `closeAccount` 销户的账户（关闭前必归零）不影响期末供给闭合，但其全部中间路径（吸筹/中转/出货边）若被采集通道漏掉，"重放 vs 快照"对账**天然看不见**——快照侧根本没有这些账户。而销户恰是 bot/中转/洗仓账户的常态收尾动作。

**独立发现源**：普通 Transfer 指令不引用 mint，但 ①一切 token account 的初始化指令（initializeAccount/2/3、ATA create，含 inner CPI）**必引用 mint** ②交易 meta 的 pre/postTokenBalances 条目自带 mint+owner。因此"mint 自身签名史"与"区间内 getBlock 整块"是不依赖 GPA 快照、不依赖 SQD 自身的第三方账户目录——用它抽查 SQD 边集，专测销户账户的转账覆盖。

**脚本**：`scripts/solana/audit_closed_accounts.py <MINT> [--edges <soltx.jsonl.gz>]`（对旧研报目录审计用 `--edges/--out` 指路径）。流程=发现历史账户样本 → getMultipleAccounts 判存活/销户（此法 publicnode 屏蔽，走 api.mainnet-beta+代理）→ 销户账户拉自身签名史（销户后签名史仍可查，§3a 坑 4 同源事实）decode 实际转账 → 逐事件对照边集。

- **两种样本发现模式**（`--mode auto|sigs|blocks`，默认 auto）：sigs=mint 签名史抽样（全程边集适用；签名史新→老翻页，历史定向段边集会翻不到区间）；blocks=边集 slot 区间内均匀抽 getBlock 整块提取（定向段正解，免翻页）。auto 3 页探路未进区间自动切 blocks。
- **判定粒度声明**：覆盖=边集存在 slot 相同且 from/to 含该 owner 的边。SQD 边是 owner 级同 tx 净变动聚合、无 sig 字段，slot+owner 是可用最细粒度（同 slot 同 owner 多笔时有极低概率误判为覆盖，审计是抽查性质，接受）。边集区间外事件计 out_of_range 不算漏。
- **undetermined 语义（诚实纪律）**：深挖账户按结果分类 events_found / all_zero_delta / fetch_failed——后两类是"没查出来"不是"没事件"（高频中转户 delta 笔可能在 --deep-sigs 窗口外），不构成"无漏"证据；过半 undetermined 时脚本自动告警。
- **退出码**：0=抽样零漏边；2=发现漏边（对账 gate 语义，报告 missing_detail 带 tx 级证据）；1=运行失败/样本无效。
- **定位**：SQD 全量重放路线的对账**补充抽查项**（非硬 gate）——阶段 2 三查过后例行跑一次，发现 missing 才升级为堵漏行动（用 window_fetch 补拉缺口段）。首轮实证：PUB 全程边集 93/93 全覆盖（sigs 模式）、USELESS 定向段区间内 7/7 全覆盖（blocks 模式）——SQD 通道销户覆盖首次获得专项验证。

（来源：Helius vs SQD 采集通道交叉复核——codex 第二意见提议"用 mint 初始化历史反向审计数据湖"，本脚本为其工程化落地并经 PUB/USELESS 双案冒烟；2026-07-21）

## 13. Solana 采集加速工程（2026-07-21，@CX 交叉复核定案后实施）

**背景**：§8 吞吐量化（SQD 单流 1.5-4x 实时→全程重放不可行→被迫 §11 混合重建）的根因被实测翻案——瓶颈大头不是 SQD 服务端，是**明文传输浪费**（v1/window_fetch 的 curl 全部没开压缩）。本节三件新工程 + 一条新通道，全程重放对 2-6 个月币龄重新可行。

### 13a. 传输层实测真相（改变所有 SQD 件的三个数字）

- **gzip 压缩 = 21 倍**：同段对照实测明文 4.65 slots/s vs `--compressed` 98 slots/s（wSOL 高密度压测,压缩比 ~40x；普通 mint 预计 5-15x）。requests.Session 默认协商 gzip——**新脚本一律 requests,遗留 curl 件必须补 `--compressed`**。
- **限流真相**：文档标称 20 请求/10 秒,长流模式实测**碰不到**（串行 30 请求 0 个 429、8 路长流并发全 200）;真实瓶颈=**单 IP 总带宽整形 ~1MB/s**（3 路与 8 路聚合吞吐相同——加流数不加总量,多注册 key 无意义）。
- **服务端单响应上限**：解压后 ~32MB 自动截断,客户端按最后 slot 续拉即可（v1 的 50K 段超时死循环是明文时代 150 秒传不完一个响应所致,压缩后自愈）。
- **SQD gateway key**（api-keys.md 第 14 节,存 `~/.config/sqd/api-key`）：公共 datasets 路径实测**完全不认证**（真/假 key 全 200）,key 专属端点 URL 待用户从 portal.sqd.dev/app 后台 key 详情页抄回后启用（v2 采集器 `--url` 直接换）。

### 13b. 全程采集器 v2（`fetch_sqd_transfers_v2.py`,取代 v1 做全程重放）

三刀：requests.Session（连接复用+自动 gzip）/ 自适应区域并发（全局段队列动态领取,区域大小按耗时自动伸缩 1 万-100 万 slot,发射窗自动缩、死亡期自动放大）/ 全局令牌桶（默认 4 rps 防雪崩护栏——高密度段 1.6 会顶死请求数,实测教训）。失败区域重试 2 轮后进 gaps 继续别的段（修 v1"第一个未完段之后整体丢弃"缺陷）,gaps 非空退出码 2、清零前不得进重放。输出/断点与 v1 完全同构（v1 meta 自动迁移）。
**实测（BONK,全网顶级密度）**：40 万 slot（≈28 链上小时）+22.3 万边,三跑累计 ~11 分钟、缺口全自动补扫收敛,稳态 639 slots/s ≈ **255 倍实时**（vs v1 的 1.5-4 倍）;同类任务对照 window_fetch 82 分钟 → **约 7 倍**。普通密度币自适应放大区域后更快——**2-6 个月币龄全程重放=数小时级,夜间挂机稳稳可行**;§11 混合重建降级为超长币龄（1 年+）专用。

### 13c. 溯源解码 v2（`decode_txs_v2.py`,三板斧落地）

JSON-RPC batch + 跨地址共享 sig 缓存（`--cache-dir`,按 sig 前 2 字符 256 片）+ `--rpc` 端点可换。**mainnet-beta 实测硬墙**：batch 内子请求被**按方法逐个限流**（"Too many requests for a specific RPC call",20 笔只放行 ~9 笔）——batch 默认 8,429 子请求自动收回重试（绝不能记 decode_fail,首测 22/40 假失败的教训）。公共节点净速度收益约 1.5 倍;**真价值=①缓存**（关联地址重复交易第二址起零请求,实测 18/40 命中）**②Helius 就位即切**（`--rpc https://mainnet.helius-rpc.com/?api-key=<key>` 免代理 50 RPS,batch 可调大）。**Helius 已就位**（2026-07-21 用户 Google OAuth 注册,key 存 ~/.config/helius/api-key,api-keys.md 第 15 节）：端点国内直连免代理;**免费层不支持 batch**（403 码 -32403,单元素数组同拒）——正解=`--workers 6 --interval 0.12` 单笔并发贴满 10RPS,实测 40 笔 5.3s=7.5 笔/s（公共节点约 7 倍;45 址溯源老基准 4 分钟→约 35 秒）;archival 10 credits/笔,免费月额≈10 万笔。

### 13d. Solana HyperSync 通道（solana.hypersync.xyz,early access——第二引擎/指纹查询,非主力）

- **文档未载的隐藏能力（实测发现）**：`token_balances` 过滤器接受 **`mint` 键**（官方文档只写指令级过滤原语）——服务端 mint 过滤生效（100 slot 段全网无关数据被滤净,只回目标 mint 行）。字段全集=`slot/mint/owner/account/pre_amount/post_amount/transaction_index`,与 SQD tokenBalance 语义同构可直接喂 pair_tx 解析核。响应结构与 EVM 不同：**顶层直接放 instructions/token_balances 等数组**（无 data 包裹）,游标字段 next_slot。
- **吞吐判定（POC 2026-07-21）**：mint 过滤模式单通道 623 slots/s ≈ SQD 打平（"读取后过滤"型,非索引跳读）,未达"4 个月币≤2h"验收线（3600）;**但双通道同跑聚合 1,211 ≈ 两倍单跑**——瓶颈在各自服务端时间片,**与 SQD 并行分段有效叠加**（消耗 HyperSync Starter 付费请求,~2 rps,量级上 overage 费忽略不计）。
- **⚠完备性验收结论（3.18.0，2026-07-22 BONK 三区实测+Helius getTransaction 链上终审）：不通过，分区分级**——①摄取前沿附近（head-18 万 slot）：与 SQD 键 (slot,account,pre,post) 差集 0/0，关户/清仓行 78=78 零差，owner 语义=postOwner、关户行退 preOwner 与 SQD 逐字一致（这条是正面结果，§13d 旧"pre/post 语义未验收"就此翻篇）②近端 head-13~33 万：**乱序回填暂态洞**（静默空响应+next_slot 照常推进，实测吞 81 条边且洞至今未回填）③历史区**持久缺行越老越糟**：head-450 万缺 3.6%、head-1450 万缺 22%（成功交易的真实转账，链上终审证实 HS 侧缺失）。
- **定位（验收后降级）**：❌全程采集第二引擎**禁用**（代码已就位于 fetch_sqd_transfers_v2 `--hypersync` 开关，运行时打硬警示，仅限吞吐实验/对照——双引擎 1 万 slot 实测 1,175 slots/s ≈ 纯 SQD 2.2-2.8 倍，GA 后重验收即可启用，对账脚本 recon2.py 留 scratchpad 可复用）✅摄取前沿附近的对照源/指纹查询（fee_payer 服务端过滤仍是 SQD 没有的能力）仍可用。
- **工程坑三条**：①窗外与洞均**静默快进 next_slot**——靠响应判断完备性不可行，完备性只能靠第二源对账 ②token_balances 索引前沿滞后 `/height` 13-27 万 slot 且乱序回填，ceiling 探测结果会"倒退" ③transaction_index 编号体系与 SQD 不同（HS 含投票 tx）——跨源对账键必须去 tx_index。
- **边界**：滚动窗口 slot 391,791,680 起（≈196 天,持续前移）;early access schema 可变、实测服务端曾两次分钟级 SSL 整体断。

**遗留后续项**：①~~v2 整合 HyperSync 第二引擎~~ ②~~完备性验收~~（均 3.18.0 完成，验收不通过→禁用待 GA 重验）③Helius 注册（已就位,见 §13c）④SQD key 专属端点补录 ⑤实时 mint 档案（方案 4,用户暂缓）。

（来源：Solana 采集加速工程,@CX 三轮交叉复核 + 本机四组实测,2026-07-21;完备性验收与双引擎整合,2026-07-22）
