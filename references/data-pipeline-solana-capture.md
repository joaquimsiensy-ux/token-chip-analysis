# Solana 数据管线 · 采集与重建工程（data-pipeline-solana 分册 2/2）

> 母文档：`data-pipeline-solana.md`（薄路由索引页；来源声明与标注图例见索引页）。本册覆盖 **§6 脚本资产 / §7 验证清单 / §8 SQD 实测补充 / §9 锚点法演变重建 / §10 快照对比法增量更新 / §11 长币龄混合重建 / §12 销户账户覆盖审计 / §13 采集加速工程（13a–13d，13d 已禁用） / §14 日级快照重建 / §15 pump.fun 长内盘重建**；§0–§5 见 `data-pipeline-solana-scan.md`。正文 §N 交叉引用一律为母文档节号。

## 6. 脚本资产（README 另存 3 项低优先待建项，两批清单勿混）

核心脚本已收编（`scan_token_accounts.py`/`fast_probe_tops.py`/`fetch_sqd_transfers[_v2].py`/`decode_txs_v2.py` 等；"classify_top_holders"未独立成脚本，其功能由 scan_token_accounts 的 owner 聚合＋fast_probe_tops 画像覆盖；现役全清单见 `scripts/solana/README.md`）；getSignaturesForAddress 按 token account 索引、tokenBalances owner 映射等实现坑的完整版在 §3a（scan 分册）。IO 原始会话实录存档：`~/Desktop/老公用/fable筹码分析/windows IO筹码分析会话记录/26a24d6c-*.jsonl`。

- 工程纪律（保留，来自前次报告硬伤）：同一地址在正文/附录多处引用时，必须由脚本从落盘数据统一生成，交付前做全文地址一致性自查；关键字符串（地址/哈希）一律取自落盘文件，禁止从终端打印输出复制补全。

## 7. 验证清单（2026-07-12 经 IO 实录考古大幅勾销）

多数项已被 IO 实录回答（getProgramAccounts/组合过滤/Squads ID/Solscan 不可直读/情报源可达）；Token-2022 大扫描已实战收编（CLUDE 07-13）。**遗留待验证**：

- [ ] `is_on_curve` 预筛提速（§2）未实战验证
- [ ] 双 RPC 屏蔽面可能随时间漂移——publicnode `Request blocked` / mainnet-beta 429 时按 §0a 矩阵换位，矩阵失效当场更新本文档
- [ ] 本机（Mac + clash）对 publicnode 百 MB 级大扫描的真实表现未跑过
- [ ] 五档分层默认档位不适配目标供应量级时按数量级平移

---

## 8. 后续实测补充（2026-07-12，来自另一项目的 Solana meme 币分析实战，置信度高于上文反推内容）

以下通道已在真实分析中跑通，标注 [实测·他场景]，直接可用：

1. **全量转账＝SQD portal**（portal.sqd.dev，免 key 免代理）——采集器现役 **v2**（§13b；v1 断点/输出同构自动迁移）。转账边=同 tx 内 owner 级净变动贪心配对，from/to 为 ZERO 哨兵即铸造/销毁；断点续拉增量无缝无重叠（meta next_slot"连续完成前缀"天然防 off-by-one，PUB 07-15 实测续拉后重放 vs 链上快照逐地址零差异）。
   **吞吐与架构选择**：v2 稳态约 255 倍实时（§13a 传输层翻案了旧的 1.5-4x 数字）——2-6 个月币龄全程重放数小时级；§11 混合重建（发射窗精确+核心实体流水+CPMM 重建+快照封口）降级为超长币龄（1 年+）专用。CPMM 数学重建中段端点偏差实测可达 35~49%，报告必须声明"仅供形状参考"（CLUDE 07-13）。
2. **发射期精确定价**：GeckoTerminal 分钟 K `/ohlcv/minute?aggregate=1&limit=1000&before_timestamp=`（池创建起就有）；小时 K 翻页可拿全历史。pump.fun"发射即迁移"币无内盘 K 线，内盘成本用 GMGN dev avg_cost 近似。
3. **资金同源（gas 溯源）**：公共 RPC `getSignaturesForAddress`（翻到最老）+ `getTransaction(jsonParsed)` 找首笔 system transfer 入金 source；0.25s 间隔+走 clash 代理，45 地址约 4 分钟。识别马甲网络最有效的一招（母钱包收敛即实锤）。
4. **洗仓识别模式**（已两次实见）：老仓→一次性中转→全新地址 双跳、间隔约 20 秒、批量链条数分钟内完成——GMGN 会把新仓显示为 transfer_in+当日成本，必须重放溯源拆穿。
5. **★铸造边全清单必查（pump.fun 币拿到 SQD 边后的第一优先检查项）**`[VERIFIED·PUB实战]`：**pump.fun 创建交易的铸造边可以有 2 条**——bonding curve 拿 ~95.7%，**dev-buy 直分拿剩余部分，且收币地址可以不是 creator 本人**。PUB 教训：主分析阶段只盯 creator 地址，创建 tx 同秒直分给另一地址的 4.24% 供应被漏掉，靠对抗复核才抓回——而它恰是"项目方系已套现一轮"的最强证据，直接改写庄家定性。固化动作：边加载后第一步跑 `replay_edges.py mints` 列出**全部**铸造边及收币地址；creator 系集群从"创建 tx 的全部受益地址"起步，而非从 creator 单地址起步（PUB，07-14）。
6. **pump.fun 内盘 bonding curve 成本重建的参数校准法**`[VERIFIED·PUB实战]`：恒定乘积虚拟储备重建（标准参数 vs0=30 SOL / vt0=1,073,000,191）对**买入枚数逐位精确**（token 守恒不受 wash 影响），但 **SOL 成本系统性低估约 10%**（实际虚拟储备参数有偏移，PUB 实测 ≈32.5/1034M）。正解：关键笔（creator 买入等）用 `getTransaction` 的 preBalances/postBalances 拿链上实付真值校准；批量笔按"重建值 +10% 修正区间"报告。**另一坑：毕业迁移笔会混进"买家"列表**（外盘池地址一笔巨量"买入"且 SOL 数疑似 wSOL 双计）——重建时必须剔除迁移笔，迁移的真实 SOL 用 GT 外盘开盘价锚定。脚本 `scripts/solana/curve_cost.py`（--grad-price 自校准告警 / --exclude 剔迁移）（PUB，07-14）。

（CLAW，07-12，经 onchain-data-accounts 记忆转录；第 5/6 条为 PUB 07-14 补充）

## 9. 锚点法演变重建 + gas 溯源加固（LAYOFF(Solana) 2026-07-15 实战）

针对"4-5 个月币龄全量 SQD 挂机不现实"的 Plan B 的一个更轻量替代，已在 LAYOFF 跑通：

1. **锚点法演变重建（免全量 SQD，`scripts/solana/build_evolution.py`）**：不重放每一笔，而是——①`fetch_pool_sigs.py` 拉主池全史签名（LAYOFF 138 万签名，失败率 33% 属 pump AMM 正常，只用成功笔）；②等距抽 ~550 个签名做**池子余额锚点**（`decode_txs.py --pool <池owner>` 每笔落 `pool_balance`）；③核心实体（top 大户 + 离场盈利榜 + 上游中转，~65 个）用 `whale_deep.py` 拉 ATA 级全流水；④`build_evolution.py` 在 ~400 个时间点插值：各实体持仓从其逐笔流水累积、流动性池用锚点曲线、散户=总供应−已知−池−销毁残差。产出图1/图2 数据。**精度声明**：中小散户是残差估算，量级正确、单点精度有限，报告局限性须写明。
2. **decode 通道坑**：`getTransaction` 直连 `api.mainnet-beta` **恒 429**，必走 clash 代理（`decode_txs.py --proxy http://127.0.0.1:7897`）；requests.Session 连接复用比 curl 逐发快约 3 倍。dRPC 免费层 Solana 需付费（`chain is not available on freetier`），别用。
3. **gas 溯源翻页上限（`gas_fast.py`，gas_origin.py 的加固）**：原 `gas_origin.py` 的 `oldest_sigs` 翻到最老全部，遇高频中转（数千签名）**卡死**（LAYOFF 实测 20 地址跑 15 分钟）——加 `max_pages=2` 上限、超深标 approx；落仓户签名少一页到底、秒完成。**遗留 TODO：把 max_pages 回填进 skill 的 gas_origin.py。**
4. **★高频服务热钱包识别（聚类防污染，取代"任意 funder"）**：gas 聚类必须取每个地址**最早一笔 SOL 入金**的 funder，不是任意交互对手——否则会把持 426 SOL、近千签名仅覆盖 4 分钟（6000+笔/分钟级）的做市/服务热钱包（本次 `AgmLJBMD`，owner=System 但巨额+超高频）误当共同母钱包，把无关大户假合并。识别姿势：疑似共源 funder 先查 `getAccountInfo`（lamports 巨大）+ 近 1000 签名的时间跨度（<10 分钟即服务）。此坑由对抗复核抛出、主分析核实。（LAYOFF，07-15）
5. **发射窗 decode 的 AMM 路由噪声**：pump.fun 发射瞬间的 owner delta 会混入 AMM/路由中间账户的巨额瞬时余额（LAYOFF 实测单笔 delta 达总供应数十倍），**不能直接当持仓变动**——发射日 bundle 识别改用 GMGN bundler 标签兜底，别硬 decode 发射窗算 bundle 归属。
6. **pump.fun creator 履历 + set_creator 洗白识别（dev 背景调查核心）**`[VERIFIED·LAYOFF实战]`：①`frontend-api-v3.pump.fun/coins?creator=<addr>` 列 creator 名下全部发币（LAYOFF dev 名下 8 币，前作"Official 89 Coin"ATH $2.43M 后归零）；②**RugCheck 对 creator 的历史币报告会打「Creator history of rugged tokens」danger 标签**——查 dev rug 前科的免费权威源；③**set_creator 洗白**：pump.fun 支持发射后更换链上 creator，对比标的与 dev 其他币的 RugCheck creator 字段，creator 被换成干净关联账户=标的报告不再显示 dev 前科（LAYOFF 把 creator 从有 rug 史的主地址换成关联账户，RugCheck 对 LAYOFF 显示零风险）。
7. **Streamflow feePayer 洗筹指纹实战命中**`[VERIFIED·LAYOFF实战]`：gas 溯源出某归集地址 funder=`wdrwhnCv4pzW8beKsbPa4S2UDZrXenjg16KJdKSpb5u`（Streamflow 自动提取服务）= 该地址通过 Streamflow 收币、切断资金溯源（pipeline §2 已记的指纹，本次首次实战命中）；穿透去向靠 whale_deep 找谁收了它的币（LAYOFF 终点是已识别的关联组成员）。（LAYOFF，07-15）
8. **★scan_token_accounts.py 双坑（增量更新同目录二跑必踩）**`[VERIFIED·PUB增量实战]`：①Token-2022 `--datasizes all` 全扫**必须显式 `--rpc https://api.mainnet-beta.solana.com`**——脚本默认 rpc=publicnode 对 Token-2022 恒 504（§0a 已记，但默认参数会让人忘传）；②v2.8.0 前的 rpc_call 只查"文件存在且>0 字节"即判成功——**16 字节的 `error code: 504` 错误体被当有效缓存写入 `_gpa_raw_*.json`**，且缓存命中逻辑（>100B 即复用）会静默复用旧数据：PUB 增量实测"全扫成功"返回的实为 2 天前旧快照（质押池/creator 余额全是旧值），与重放对账假性炸出 24.6% 差异，靠**独立单查三点仲裁**（getTokenAccountsByOwner 逐个验关键地址）才定位真凶。对策：增量重扫前把旧 `_gpa_raw_*.json` 改名存档强制真扫；脚本已加固（返回体须为含 result 的合法 JSON 才落缓存+缓存命中打 mtime 告警，v2.8.0）。对账炸掉时的仲裁纪律：**先用第三通道单查 2-3 个关键地址定"谁是旧数据"，再决定修哪边**——别急着怀疑重放管道（PUB 更新，07-15）。

## 10. 快照对比法增量更新（/token-update 的 Solana 特化形态，CLUDE 增量实战定型 2026-07-15）

旧研报为锚点法（非全量流水重放）时，增量更新**不必补拉全量转账**，走快照对比五步（1.8 天窗口全程 <1 小时数据成本）：

1. **新全量快照**：`scan_token_accounts.py`（Token-2022 记得 `--rpc api.mainnet-beta` + 先把旧 `_gpa_raw_*` 改名存档，见 §9.8）；同时 `getTokenSupply` 复验供给闭合（窗口内销毁体现在总量差）。
2. **快照 diff**：`snapshot_diff.py --old 旧owners --new 新owners --entities 实体表` → 实体逐址变动 + 大额变动榜（新面孔/清零标注）。**排名变化不是证据**（持有人增多会把静止地址挤出 topN），一切以余额 Δ 为准。
3. **窗口流转定性**：`probe_window_moves.py --targets 变动榜 --cutoff <ISO时间>` → 每址 pool_buy/pool_sell/direct_transfer 分类 + 直转对汇总（换仓/洗仓/归集识别）。**大额变动地址要 100% 覆盖定性，抽样会漏换仓对**（CLUDE 首轮抽 17 址被复核抓漏 1 对，补扫 38 址才闭合）；直转对金额取对手方 |Δ| 口径。
4. **对账三查（轻量版）**：新快照加总=getTokenSupply（diff=0）；top20 与 `getTokenLargestAccounts` 双源对表（活跃池允许时点差）；重点地址签名史净额 vs 快照 Δ 分毫互验。
5. **观察哨核查加固**：余额不变≠没动（可能转出又转回）——sentinel 级地址补签名列表验证（窗口内零签名才是硬结论）。

配套纪律：**cutoff 时间戳一律 `datetime.fromisoformat` 验算，禁止手算 unix 秒**（实战手算错 2 天导致签名史首跑作废，且错误 cutoff 不报错、只静默漏数据）；数据文件 meta 的 `updated` 字段是"最后写入时间"不是"覆盖范围"，增量起点判定看数据末行而非 meta（发射日流水文件 updated=07-13 但只覆盖 02-24，望文生义会把增量起点定错 4.5 个月）。（CLUDE 更新，07-15）

## 11. 长币龄混合重建 + 高密度期定向采集（USELESS(Solana) 2026-07-21 实战）

§8"全程 SQD 重放不现实"与 §9 锚点法的合体升级——14 个月+币龄、13.5 万持仓账户量级标的实战定型：

1. **混合重建演变架构（长币龄标准件，两端精确、中段插值）**：①发射窗（发射日起 24-48h）用 `window_fetch.py` 拉全量边（精确——狙击/bundle 分析必须逐笔）②核心实体（庄/项目方/大户）ATA 级全流水（`whale_deep.py`，精确）③中段日级锚点前向填充（`anchor_sampler.py`）④**当前快照封口 + 末日快照注入**——把 data_cutoff 日全量快照作为最后一个锚点注入序列，修"清仓发生在锚点观测窗外则旧值永久残留"的系统性尾部误差。图 1/图 2 由 ①②③④ 合成，散户=残差；精度声明照 §9 写进局限性（USELESS，07-21）。合成器参考实现：GOAT 案 `compose_evolution.py`（锚点 owner 级前向填充 + 末日快照真值封口 + 发射日零基线 + 散户残差；**工作目录 GOAT分析/ 专属存档，非复用件**——实体分组、发射日、价格文件名按案硬编码，新案参考其算法结构重写；通用化抽象列遗留）（GOAT，07-22）。
2. **SQD 高密度期定向拉取用小段+并发（`window_fetch.py`）**：密集期（发射窗/事件日）正解=**2000 slot 小段 × 8 并发**，失败段落 `.gaps.json`（必须为空才算完整）。反面教训：fetch_sqd_transfers 的 50K 大段在发射期反复 curl 超时截断重试，120 分钟只推进 3.4 链上小时；小段版 29 秒拉完 1 万 slot、发射日 24h（16.5 万边）82 分钟零缺口。**gap 段补拉合并纪律（GOAT 实测坑）**：标 gap 的段**仍会写出部分数据**——补拉后与原文件 cat 追加合并=重复边（GOAT 案 9,212 行重复）；重复合并的快查指纹=**重放负余额账户数暴增**（534 → dedup 后 1）。正解：gap 段用补拉版**整段替换**（按 slot 区间切除旧段再并入）或合并后全字段 dedup；重放见两位数以上负余额账户，先查重复合并再查采集通道。另：发射窗峰值榜必剔 pump.fun 官方毕业迁移钱包（address-book Solana 平台表，20.7% 级协议常数过手），否则误判狙击集团（GOAT，07-22）。
3. **日级锚点采样（`anchor_sampler.py`）与它的观测边界（★阴性依据禁用）**：从新到旧滚动校准 slot↔ts（分段线性外推、漂移 >4h 自动重估，435 天约 5s/天）。**⚠观测窗真相**：名义 1h 窗（9000 slot）在高活跃期因响应截断实际仅 ~3.6 分钟，且 SQD tokenBalances 只记**发生变动**的账户——静止大户被系统性漏观测。因此**锚点单独不可作任何"某地址没动/没持仓"的阴性依据**，阴性结论必须快照或全流水兜底；锚点只用于正向变动观测与序列插值（对抗复核实测抓出，来源：USELESS(Solana) 分析，2026-07-21）。**【候选·单案】锚点复用两扫描（easy/混合重建建议必做步，零边际成本）**：锚点序列采完后顺手做 ①**全 owner 峰值普查**（阈值 ≥1.5% 总供应）——产出"历史大仓名单"（含已清仓离场者），补当前快照视角的系统性盲区（快照只见在场者）；②**全史前三涨跌日×锚点对照**——最大涨/跌日与该日锚点观测交叉，抓事件日实体动作指纹（如拉高日金库调拨）。GOAT 案完整性复核 4 条 must_add 有 3 条半源于缺这两步（历史离场大仓×2、离场庄扩容、事件日调拨）（GOAT，07-22）。
4. **publicnode 大扫描死角补充（§0a/§1 的边界）**：13.5 万 token account 量级的 mint，publicnode getProgramAccounts 恒 504（dataSlice 也救不回）；**api.mainnet-beta 做 SPL 大扫描会静默返回空结果**（不报错——危险，靠对账关卡拦住，勿当"该 mint 无账户"）。分片扫描（`scan_sharded.py`，amount 低位字节递归分片）可行但两个坑：①owner 位置 memcmp 必须整 32 字节（1 字节分片语法合法但过滤不生效）②零余额账户 8 字节 amount 全零、全部堆在全零前缀片——递归下钻全零前缀至 8 字节终点片直接跳过（分析只要非零余额）。USELESS 案分片全量未跑完（publicnode 间歇 504），对账改用"8 样本独立单查 + top20 对表"替代过关——**分片器待后续标的全量验证**。**死角地图更新（GOAT 实测）**：24.7 万 token account / 67MB 响应量级，Helius + `--compressed`(gzip) + 300s 长超时**一次拉全成功**（publicnode 恒 504、Helius 默认 120s 超时也断；见 §1 实测升级行）——大盘子 mint 的 GPA 正解就位，分片器降级为末位备选（GOAT，07-22）。
5. **whale_deep 按地址频率分派（先估频再选通道）**：深挖前先 getSignaturesForAddress 拉一页估频——高频地址（creator 类，签名 7 万+）ATA 级全 decode 需数小时/地址不可行，改**事件窗定向拉**（只 decode 关键时间窗）；低频囤仓户（15-172 笔）全量 decode 秒-分钟级。一刀切全量 decode 会把预算烧在单个高频地址上（USELESS，07-21）。**cap 截断样本的用途边界 + Helius 并发纪律（GOAT 增量）**：高频地址签名史翻到工具 cap（如 2000 笔）即**截断样本**——起点余额非零，**不可从零累积重建持仓时间线**，只能作"最近 N 笔行为定性样本"（流向画像/对手方指纹），时间线必须锚点/快照兜底且报告局限声明注明"截断样本"；Helius 免费档 10 RPS 是**账号级**配额——多进程并行互抢配额反而整体拖慢（实测 5 进程时单笔 decode 拖到 0.6-1.2s），正解 = `whale_deep.py --out` 分组独立文件防写冲突 + 总并发贴 10 RPS 不超发（GOAT，07-22）。
6. **letsbonk 平台币三件套（§8.5/§8.6 的平台变体，vs pump.fun 差异）**：①铸造边 2 条——curve 拿大头 + dev 直分一笔，且 **dev-buy 可在数秒内卖回**（实测 6 秒）制造"creator 已清仓"表象——creator 状态判定必须看直分笔的后续流向，不能只看当前余额；②**creator fee 走 Raydium Lock 的 burn&earn harvest 账本**（非 pump.fun 费领取模式）——费农收入=真实收益引擎，dev"弃盘与否"必查 harvest 流水；③毕业迁移约 20.7% 供应入 Raydium 池（USELESS，07-21）。

## 12. 销户账户覆盖审计（SQD 边集对账盲区加固，2026-07-21）

**盲区原理**：`getProgramAccounts` 快照只见**当前存活**的 token account；被 `closeAccount` 销户的账户（关闭前必归零）不影响期末供给闭合，但其全部中间路径（吸筹/中转/出货边）若被采集通道漏掉，"重放 vs 快照"对账**天然看不见**——快照侧根本没有这些账户。而销户恰是 bot/中转/洗仓账户的常态收尾动作。

**独立发现源**：普通 Transfer 指令不引用 mint，但 ①一切 token account 的初始化指令（initializeAccount/2/3、ATA create，含 inner CPI）**必引用 mint** ②交易 meta 的 pre/postTokenBalances 条目自带 mint+owner。因此"mint 自身签名史"与"区间内 getBlock 整块"是不依赖 GPA 快照、不依赖 SQD 自身的第三方账户目录——用它抽查 SQD 边集，专测销户账户的转账覆盖。

**脚本**：`scripts/solana/audit_closed_accounts.py <MINT> [--edges <soltx.jsonl.gz>]`（对旧研报目录审计用 `--edges/--out` 指路径）。流程=发现历史账户样本 → getMultipleAccounts 判存活/销户（此法 publicnode 屏蔽，走 api.mainnet-beta+代理）→ 销户账户拉自身签名史（销户后签名史仍可查，§3a 坑 4 同源事实）decode 实际转账 → 逐事件对照边集。

- **两种样本发现模式**（`--mode auto|sigs|blocks`，默认 auto）：sigs=mint 签名史抽样（全程边集适用；签名史新→老翻页，历史定向段边集会翻不到区间）；blocks=边集 slot 区间内均匀抽 getBlock 整块提取（定向段正解，免翻页）。auto 3 页探路未进区间自动切 blocks。
- **判定粒度声明**：覆盖=边集存在 slot 相同且 from/to 含该 owner 的边。SQD 边是 owner 级同 tx 净变动聚合、无 sig 字段，slot+owner 是可用最细粒度（同 slot 同 owner 多笔时有极低概率误判为覆盖，审计是抽查性质，接受）。边集区间外事件计 out_of_range 不算漏。
- **undetermined 语义（诚实纪律）**：深挖账户按结果分类 events_found / all_zero_delta / fetch_failed——后两类是"没查出来"不是"没事件"（高频中转户 delta 笔可能在 --deep-sigs 窗口外），不构成"无漏"证据；过半 undetermined 时脚本自动告警。
- **退出码**：0=抽样零漏边；2=发现漏边（对账 gate 语义，报告 missing_detail 带 tx 级证据）；1=运行失败/样本无效。
- **定位**：SQD 全量重放路线的对账**补充抽查项**（非硬 gate）——阶段 2 四查过后例行跑一次，发现 missing 才升级为堵漏行动（用 window_fetch 补拉缺口段）。首轮实证：PUB 全程边集 93/93 全覆盖（sigs 模式）、USELESS 定向段区间内 7/7 全覆盖（blocks 模式）——SQD 通道销户覆盖首次获得专项验证。

（Helius vs SQD 采集通道交叉复核——codex 第二意见提议"用 mint 初始化历史反向审计数据湖"，本脚本为其工程化落地并经 PUB/USELESS 双案冒烟；07-21）

## 13. Solana 采集加速工程（2026-07-21，@CX 交叉复核定案后实施）

**背景**：§8 吞吐量化（SQD 单流 1.5-4x 实时→全程重放不可行→被迫 §11 混合重建）的根因被实测翻案——瓶颈大头不是 SQD 服务端，是**明文传输浪费**（v1/window_fetch 的 curl 全部没开压缩）。本节三件新工程 + 一条新通道，全程重放对 2-6 个月币龄重新可行。

### 13a. 传输层实测真相（改变所有 SQD 件的三个数字）

- **gzip 压缩 = 21 倍**：同段对照实测明文 4.65 slots/s vs `--compressed` 98 slots/s（wSOL 高密度压测,压缩比 ~40x；普通 mint 预计 5-15x）。requests.Session 默认协商 gzip——**新脚本一律 requests,遗留 curl 件必须补 `--compressed`**。
- **限流真相**：文档标称 20 请求/10 秒,长流模式实测**碰不到**（串行 30 请求 0 个 429、8 路长流并发全 200）;真实瓶颈=**单 IP 总带宽整形 ~1MB/s**（3 路与 8 路聚合吞吐相同——加流数不加总量,多注册 key 无意义）。
- **服务端单响应上限**：解压后 ~32MB 自动截断,客户端按最后 slot 续拉即可（v1 的 50K 段超时死循环是明文时代 150 秒传不完一个响应所致,压缩后自愈）。
- **SQD gateway key**（api-keys.md 第 15 节「SQD Portal」,存 `~/.config/sqd/api-key`）：公共 datasets 路径实测**完全不认证**（真/假 key 全 200）——**直接匿名调用即可,不需要配 key**。该 key 实为旧版 SDK 网关用途,Portal 正式 key 体系官方尚未上线,**不存在"专属端点 URL",无需再等用户抄回**（2026-07-21 定论,2026-07-25 复核确认）。

### 13b. 全程采集器 v2（`fetch_sqd_transfers_v2.py`，全程重放主力）

三刀：requests.Session（连接复用+自动 gzip）/ 自适应区域并发（全局段队列动态领取,区域大小按耗时自动伸缩 1 万-100 万 slot,发射窗自动缩、死亡期自动放大）/ 全局令牌桶（默认 4 rps 防雪崩护栏——高密度段 1.6 会顶死请求数,实测教训）。失败区域重试 2 轮后进 gaps 继续别的段（修 v1"第一个未完段之后整体丢弃"缺陷）,gaps 非空退出码 2、清零前不得进重放。输出/断点与 v1 完全同构（v1 meta 自动迁移）。
**实测（BONK,全网顶级密度）**：40 万 slot（≈28 链上小时）+22.3 万边,三跑累计 ~11 分钟、缺口全自动补扫收敛,稳态 639 slots/s ≈ **255 倍实时**（vs v1 的 1.5-4 倍）;同类任务对照 window_fetch 82 分钟 → **约 7 倍**。普通密度币自适应放大区域后更快——**2-6 个月币龄全程重放=数小时级,夜间挂机稳稳可行**;§11 混合重建降级为超长币龄（1 年+）专用。

#### SQD stream 响应语义（2026-07-26 实测定案,判完备性的地基）

判"这段扫完没有"只能靠下面四条,**别拿"响应有没有行"当失败信号**：
- **空区间不返回空**：区间内有块但该 mint 无数据时,服务端回**稀疏 header-only 行**标记扫描进度（实测 100 万 slot 的空区间回 20 行、推进到 +3,905;1000 万 slot 同样 20 行 640 字节）——客户端按最后 header 续拉即可,这是正常推进不是失败。
- **零行的唯一正常成因＝区间内一个块都没有**（Solana skipped slot 串,leader 没出块）。实证：BONK 现场 4 段复验,去掉 mint 过滤依然零行,而包围 ±60 有 103-112 个块。
- **HTTP 204 ＝ fromBlock 超出服务端已索引范围**（0 字节）。**绝不能判完成**——那是漏数据,只能按可重试失败处理。
- **`/head` 给的是 unfinalized head**,响应头 `x-sqd-finalized-head-number` 比它小约 2,900 slot（实测）。采集上界取 `/head` 没问题（实测到 head 仍正常返回数据）,但别拿两者的差当异常。

#### ⚠ 伪 scan-fail（3.34.0 修复,BONK 全史采集实测暴露）

**症状**：旧版把"HTTP 200 流完整读完但零行"与真失败一起归 `last is None` 重试后记 `gaps['scan-fail']`——纯空 slot 段永远补不回，以 `gaps == []` 为完成判据的调度器永远判不到完成（BONK 实测 365 段空洞、watchdog 反复重启空转约 24h）。

**修复**：`scan_area` 加 `complete` 标志（HTTP 200 + 无截断行 + 无连接层异常 = 流完整读完）,零行且 complete 时按两级判定——跨度 ≤ **`EMPTY_MAX`（默认 500 slot,`--empty-max` 可调）** 直接判完成；更宽的零行区间不放行,改用 **轻量块探针** `Fetcher.probe_blocks()` 实证（只要 `block.number`、不带任何 tokenBalance 过滤器,服务端扫描上限自动截断在 20 行——**实测封顶 640 字节 / 0.4-0.8 秒**）,探不出块才判完成,探到块＝服务端过滤路径异常仍按失败重试。每次判定 log 留痕并写入 `meta.empty_ok`（`{n, max, intervals}`）供事后审计：任取一段做 ±60 包围请求,应能拿到前后块且不含该段本身。
- BONK 现场分布：跨度 **1-13 slot、中位 2**——闸门 500 已是很宽的保守值,正常币不会踩到探针路径。
- **闸门的残余局限**：低活跃度币若真有 >500 slot 的连续无块段,会多花一次探针请求（不影响正确性,只是慢一点）；探针失败时仍按老路重试记 gap。

#### ⚠ 收尾全内存合并会 OOM 且可能留下损坏缓存（3.34.0 修复,同案暴露）

**症状**：旧版收尾全内存合并（含开局全量 load 旧缓存），千万行级分片峰值 13-19GB 必 OOM；且边算边写 gz，OOM 落在写入中途留下损坏缓存→下次启动触发"重新全量"，几小时工作作废（BONK 实测暴露）。

**修复三件**：
1. **超限自动降级磁盘外排**：预估行数（旧缓存精确行数 + parts 按采样均行长估算）> **`MERGE_INMEM_MAX_ROWS`（默认 800 万,`--merge-max-rows` 可调,约 2.8GB 峰值）** 即走 DuckDB 外排（`memory_limit=4GB` / `threads=4` / temp 落 `data/_merge_tmp`,实测 1.55 亿行约 11 分钟）；阈值内保持全内存（历史行为）。**无 duckdb 时告警后退回全内存**,不硬依赖。
2. **两条路径一律原子落盘**：临时文件写完再 `os.replace`,中途 OOM/断电既不毁旧缓存也不留残件；零边时不动缓存（同旧版语义）。
3. **旧缓存不再全量载入内存**：开局只做流式体检拿行数（块读计数 + gzip CRC 校验 + 抽验前几行 JSON）。

**外排与全内存的口径对齐三条（照抄,踩过）**：
- **金额可超 int64**（BONK 创世铸造边 amt = 10^19）——全程以 VARCHAR 取用（`x->>'$[i]'`）,**只有 slot / ts 才可 CAST 成 BIGINT** 用于排序,对 amt 做任何数值 CAST 都会溢出或失真。
- **必须按字段去重而非整行**：part 文件用紧凑格式 `separators=(",",":")` 写,而缓存 gz 用 `json.dumps` 默认格式（带空格）——同一条边两种写法的整行字符串不同,`SELECT DISTINCT x` 去不掉；先拆字段 DISTINCT,输出时再按 gz 的默认格式逐字段重建。
- **排序确定化**：`(slot, ts)` 主序之后补 `(from, to, amt文本)` 末位键。历史版只用 `(slot, ts)`,同键行序取决于 `set()` 哈希迭代顺序＝**同一份数据两次跑可能不同**；补齐后两条路径可逐字节对拍。amt 按**文本**比较（外排侧只能 VARCHAR,两边必须同口径）。

**守护**：`scripts/tests/test_sqd_merge_equiv.py`（已进 run_all 全家桶）——六条契约：两路径逐字节一致（含跨格式去重/超 int64/同 (slot,ts) 多行/ts=0）、大数保真、路径选择、原子落盘、零行判定五分支、scan_area 尾段零行判完成而真失败仍失败。真实端到端另验：BONK 定段采集（含已知 skipped slot 尾段）退出码 0 且 `gaps=[]`（旧版此处必记 scan-fail）、增量续拉 183→230 边无重复、强制外排路径旧行全保留。

#### ⚠ 同 slot 同额多笔边会被"去重"吃掉（TROLL 实测暴露，2026-07-29——检测与修复 SOP，根治待查）

**机制**：SQD 边表无 sig 字段，边=(slot, ts, from, to, amt) 元组——**同一 slot 内同两方、同金额的多笔真实转账，在边集里只剩一条**（TROLL 案真值账本逐 slot 对表：每个不一致 slot 主边集恰=真值的一半，两笔同额买入剩一笔，机制 100% 确认；丢失发生层未定位——SQD 响应本身或本地 set()/DISTINCT 合并均有嫌疑，根治调查列 Known Gaps）。**与 GOAT gap 合并坑（§11.2）恰成对偶**：GOAT 是 cat 追加造出假重复→靠 dedup 修复；TROLL 是 dedup 无法区分"重复采集"与"真实同字段多笔"→误杀真边。两案合读：**边无 sig 字段是根因，dedup 既是解药也是毒药**。
- **危害量化**：TROLL 案重放 vs 快照 |diff| 达 **8.127% 总供应**才收敛，受害者集中于"与池子同额多笔交互"的地址（高频往返 bot 为主，一日内两笔同额买入极常见）。
- **检测指纹**：重放 vs 快照差异呈**正负成对**（丢一笔买入→该地址虚低、池子虚高）、集中于高频地址；确认法=抽一个大差异地址做 ATA 签名史真值账本，逐 slot 对表看"边集=真值一半"形态。
- **修复 SOP（TROLL 验证收敛）**：差异地址（≥量级阈值，本案 ≥10 万枚）ATA 全史 decode（tx 级全边+sig 粒度）**替换式合并**进边集（按地址整体替换，不是追加）；池子/CEX 等设施侧差异由对手方 decode 附带修复；验证=受害地址全程锚点逐点吻合（本案 1760/1760）+末点阵营合计恰 100%。修不完的残差如实写局限性（本案残差 2.8% 声明为演变图中段 ≤±3pp 失真）。

（TROLL，07-29）

### 13c. 溯源解码 v2（`decode_txs_v2.py`,三板斧落地）

JSON-RPC batch + 跨地址共享 sig 缓存（`--cache-dir`,按 sig 前 2 字符 256 片）+ `--rpc` 端点可换。**mainnet-beta 实测硬墙**：batch 内子请求被**按方法逐个限流**（"Too many requests for a specific RPC call",20 笔只放行 ~9 笔）——batch 默认 8,429 子请求自动收回重试（绝不能记 decode_fail,首测 22/40 假失败的教训）。公共节点净速度收益约 1.5 倍;**真价值=①缓存**（关联地址重复交易第二址起零请求,实测 18/40 命中）**②Helius 就位即切**（`--rpc https://mainnet.helius-rpc.com/?api-key=<key>` 免代理 50 RPS,batch 可调大）。**Helius 已就位**（2026-07-21 用户 Google OAuth 注册,key 存 ~/.config/helius/api-key,api-keys.md 第 16 节「Helius」）：端点国内直连免代理;**免费层不支持 batch**（403 码 -32403,单元素数组同拒）——正解=`--workers 6 --interval 0.12` 单笔并发贴满 10RPS,实测 40 笔 5.3s=7.5 笔/s（公共节点约 7 倍;45 址溯源老基准 4 分钟→约 35 秒）;archival 10 credits/笔,免费月额≈10 万笔。
**⚠ urllib 逐笔新建连接对 Helius 会 sock_connect 挂死（TROLL 实测，2026-07-29）**：decode_txs_v2 在部分本机网络环境下逐笔 urlopen 挂起（即使 `ProxyHandler({})` 强制直连也不稳）——症状是单笔卡住无超时推进。绕行=手写 `http.client.HTTPSConnection` **keep-alive 长连接**版（8 线程 ~7 笔/s 稳定，TROLL 工作目录存档，收编待第二案复现）；根治通道=environment.md B5 的 `scripts/lib/net.py`（httpx 连接池），新写解码脚本直接用它，别再走 urllib。（TROLL，07-29）

### 13d. Solana HyperSync 通道（**已禁用**——完备性验收不通过，GA 后重验；全量细节见 git 3.18.x 条目）

- **判决（3.18.0，BONK 三区实测+Helius 链上终审，07-22）**：历史区持久缺行越老越糟（head-450 万缺 3.6%、head-1450 万缺 22%）、近端乱序回填暂态洞且**静默快进 next_slot**（单跑无法自知缺数据）——❌全程采集第二引擎**禁用**（fetch_sqd_transfers_v2 `--hypersync` 开关已带硬警示，仅限吞吐实验）；✅摄取前沿附近（约 20h 内）作对照源/指纹查询（fee_payer 服务端过滤是 SQD 没有的能力）仍可用。
- **GA 后重验路径**：对账脚本 `scripts/solana/hypersync_recon.py`（三区各跑一轮+Helius 终审定责）；mint 过滤隐藏能力、跨源对账三工程坑、双引擎吞吐 POC 细节从 git 考古（3.18.x）。
- **⚠混合分段提议已否决，勿再重议（07-22 @CX）**：滚动窗口是覆盖范围不是准确范围；洞静默→证明某段完整的唯一办法=SQD 重拉对账，HS 等于白跑；供给对账兜不住成对缺行（借贷双缺仍守恒），完备性必须落到边集合一致；SQD 全量恒为关键路径，双引擎不缩短认证耗时。

**遗留后续项**：①~~v2 整合 HyperSync 第二引擎~~ ②~~完备性验收~~（均 3.18.0 完成，验收不通过→禁用待 GA 重验）③Helius 注册（已就位,见 §13c）④SQD key 专属端点补录 ⑤实时 mint 档案（方案 4,用户暂缓）。

（Solana 采集加速工程,@CX 三轮交叉复核 + 本机四组实测,2026-07-21;完备性验收与双引擎整合,2026-07-22）

---

## 14. ★日级余额快照重建法（长币龄演变默认方法；GOAT 2026-07-26 翻案驱动）

### 14a. 先说清楚：§9 锚点法有一个会静默出错的缺陷

**缺陷**：`anchor_sampler.py` 只观测"每日约 1 小时窗口内发生变动"的账户（§9 已声明"静止地址系统性无观测"），画图脚本对未观测日做**前向填充**。一旦某地址长期没被采到，它最后一次观测值就会被一路复制到末尾，造出**幽灵持仓**。

**致命之处不在缺陷本身，而在它过不了任何现有关卡**：演变脚本惯例用"末日快照封口"（`bal_series[o][-1] = snap[o]`）——**最后一天永远是真值，于是余额对账、供给闭合、时间抽查全部通过**，错误全藏在中段。图上表现为一条平直阶梯，最后一天突然断崖归位，宽度不足 1 像素、肉眼不可见。

**GOAT 实证（2026-07-26）**：41 个跟踪地址中 **28 个锚点裸奔 >90 天**（最长 425 天）。交付时三查全过，实际**全部 7 个阵营的中后段数值都是错的**——离场庄虚高 12.10pp（真实 0.87% 被画成 12.97%）、散户虚低 12.95pp、CEX 托管虚高 6.93pp、其他大户虚低 4.97pp。图与报告正文自相矛盾（正文写"2025-10→2026-04 出货 9,825 万枚"，图上同期纹丝不动）却无人察觉，直到用户直接质疑图形才暴露。

**纪律**：①锚点法仅可用于**粗略趋势示意**，凡结论要引用某阵营某时点的具体数值，必须用下面的日采样法或全量重放；②任何"仅末日封口"的演变脚本，**必须在报告局限性里明写中段为插值**，且**禁止**把中段数值写进判定块；③演变图交付前跑一次自检——打印倒数第 2 天与最后 1 天的各阵营值，**若任一阵营跳变 >1pp 即为虚挂信号**（这一条 30 秒就能跑，本案若早跑可省整轮返工）。

### 14b. 日级余额快照重建法（本案验证可用，成本仅全量解码的 2%）

**核心思路**：不重放每一笔转账，而是**每天取一个真实余额快照**。前向填充仍然用，但这次有据——某日该账户无成功签名，就是真的没动过。

四步（脚本见 GOAT 案 `data/exit_trace/{daily_plan,decode_bal,rebuild_series}.py`，待收编 `scripts/solana/`）：
1. **拉全签名**：对每个跟踪 owner 的每个 ATA 拉完整签名史（`getSignaturesForAddress` 1000 笔/请求，实测 **1,600 笔/秒**，11.3 万笔的池子 ATA 仅 70 秒）。
2. **按日压缩**：签名倒序返回，**每日首次出现的即当日最后一笔**；剔除 `err != null` 的失败交易（不改变余额）。GOAT 实测 **45 万笔 → 8,302 个采样点（1.8%）**。
3. **解码取余额**：只解码这 8,302 笔，从 `meta.postTokenBalances` 取该 ATA 的**绝对余额**（不是 delta），需用 `accountIndex → accountKeys[i].pubkey` 映射出账户地址。
4. **重建序列**：每 ATA 按日填余额、无采样日沿用前值；owner = 各 ATA 求和；阵营 = 同阵营 owner 求和；散户 = 总供应 − 已知。

**三个必踩的坑**：
- **★投毒采样点不可当余额 0**：签名史里混着 address-poisoning 交易（§3a 坑 2），它们**提及了该账户但 postTokenBalances 里没有它**。若写成 `bals.get(ata, 0)`，持仓会被**错误归零**——GOAT 实测 99 个此类采样点，未修时小庄从 5.24% 掉成 3.72%、其他大户从 10.48% 掉成 7.19%。**正解=该 ATA 不在返回里就跳过这个采样点**（保持前值），绝不填 0。
- **并发要给解码让路**：拉签名与 `getTransaction` 抢同一份 RPS。Helius 免费层 10 RPS，实测 4 并发拉签名 + 6 workers 解码会触发限流退避，把 3 分钟的活拖成 53 分钟。拉签名阶段用 2 并发。
- **超高频 ATA 要设深度上限**：DEX 池/CEX 热钱包的 ATA 签名史可达数十万笔，脚本必须带 `CAP`（本案 25 万）与截断标记，否则单个地址能把整个计划卡死。

**验收标准**：重建末日值与 `getTokenAccountsByOwner` 实查逐地址对表，TOP12 须逐个吻合（本案唯一偏差是 CEX 地址在快照日之后的真实变动，属正常）。

（GOAT 全量流水重建翻案，07-26）

## 15. pump.fun 长内盘期全量重建（签名史双索引法；TROLL 2026-07-29 实战）

**适用场景**：老 pump.fun 币在内盘（bonding curve）滞留数月甚至一年以上才毕业——内盘期交易稀疏（TROLL 案 13 个月仅 ~1,600 笔），但**不能不采**：做量脉冲、早期集群、毕业前试盘仓全藏在这段。用 SQD 扫这段 slot 区间（TROLL 案 8 千万 slot）在死亡期每响应仅推进 ~3900 slot，工程上极不划算。与 §8 CLUDE"Plan B 混合架构"的分工：那是**高密度短币龄**的取舍方案；本节是**稀疏长内盘期**的全量精确解——稀疏恰恰使逐笔 decode 可行。

**方法（双索引 ∪ 迭代补边，TROLL 案 decode 零失败、1,413 边）**：
1. **curve PDA 签名史全翻**（getSignaturesForAddress 到最老）——内盘期所有对售货机的买卖必经它；
2. **∪ mint 签名史**（before 锚定翻老）——补 curve 索引外的铸造/销毁/初始化事件；
3. 两个索引合并 decode 全部 tx（tx 级全边，含 inner）；
4. **差异地址 ATA 迭代补边法**收敛盲区：重放期末 vs 毕业时点持仓对表，差异地址拉其 ATA 签名史补 decode——**理论盲区=双方 ATA 都已存在的用户间直转**（不经 curve 不经 mint），迭代到差异清零（TROLL 案 2 轮收敛，其中一笔 6 边巨型归集 tx 一次解决 38.6pp 差异）。
5. **独立通道抽验**：SQD 兜底扫一小段与 decode 结果逐边对表（TROLL 案创建窗 14/14 含笔数完全一致）。

**产出与衔接**：内盘边集（如 `data/curve_pre_edges.jsonl`）与主段 SQD 边集拼接为全史边集；衔接缝（锚点 slot 前后几万 slot）注意 mint 签名史补齐，否则供给闭合差在缝里（TROLL 案 119 枚差即衔接缝内协议销毁）。报告局限性声明理论盲区（供给闭合零差时可写"盲区规模可忽略"）。

**配套工程数字**：SQD 对"单一连续大空洞"**只有 1 个 worker 有效**——并发单位是空洞段，同段 4 进程分片互相拖慢（服务端时间片均分），单进程 ~3450 slots/s 反而最快，别对死亡期空洞开分片；高频 ATA（池子级）签名史翻页必须设 CAP（~20 页）防拖死；ATA 的 PDA 派生纯 Python 可推（ed25519 on-curve 检查 ~30 行，无需 solders 依赖——`entity_identity_gate.py` 已内置同款实现可抄）。

（TROLL，07-29——创建时点 2024-03-10 至毕业 2025-04-20 共 13 个月内盘期全量重建，供给闭合差 1.19e-5%）
