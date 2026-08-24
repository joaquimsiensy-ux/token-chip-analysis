# Solana 数据管线 · 采集与重建工程（data-pipeline-solana 分册 2/2）

> 母文档：`data-pipeline-solana.md`（薄路由索引页；来源声明与标注图例见索引页）。本册覆盖 **§6 脚本资产 / §7 验证清单 / §8 SQD 实测补充 / §9 锚点法演变重建 / §10 快照对比法增量更新 / §11 长币龄混合重建 / §12 销户账户覆盖审计 / §13 采集加速工程（13a–13d，13d 已禁用） / §14 日级快照重建 / §15 pump.fun 长内盘重建**；§0–§5 见 `data-pipeline-solana-scan.md`。正文 §N 交叉引用一律为母文档节号。

## 本册路由

- [§6–§10 脚本与基础重建](#6-脚本资产)：资产、验证、实测补充、锚点与快照。
- [§11 长币龄混合重建](#11-长币龄混合重建--高密度期定向采集uselesssolana-2026-07-21-实战)与[§12 销户覆盖](#12-销户账户覆盖审计sqd-边集对账盲区加固2026-07-21)。
- [§13 SQD 加速工程](#13-solana-采集加速工程2026-07-21cx-交叉复核定案后实施)：stream、全程采集、解码与 HyperSync 边界。
- [§14 日级余额快照](#14-日级余额快照重建法长币龄演变默认方法goat-2026-07-26-翻案驱动)。
- [§15 pump.fun 长内盘](#15-pumpfun-长内盘期全量重建签名史双索引法troll-2026-07-29-实战)。

## 6. 脚本资产

核心脚本已收编（`scan_token_accounts.py`/`fast_probe_tops.py`/`fetch_sqd_transfers_v2.py`/`decode_txs_v2.py` 等；"classify_top_holders"未独立成脚本，其功能由 scan_token_accounts 的 owner 聚合＋fast_probe_tops 画像覆盖；现役薄索引见 `scripts/solana/README.md`）；getSignaturesForAddress 按 token account 索引、tokenBalances owner 映射等实现坑的完整版在 §3a（scan 分册）。

- 工程纪律（保留，来自前次报告硬伤）：同一地址在正文/附录多处引用时，必须由脚本从落盘数据统一生成，交付前做全文地址一致性自查；关键字符串（地址/哈希）一律取自落盘文件，禁止从终端打印输出复制补全。

## 7. 验证清单

**遗留待验证**：

- [ ] `is_on_curve` 预筛提速（§2）未实战验证
- [ ] 双 RPC 屏蔽面可能随时间漂移——publicnode `Request blocked` / mainnet-beta 429 时按 §0a 矩阵换位，矩阵失效当场更新本文档
- [ ] 本机（Mac + 经 CHIP_PROXY/--proxy 解析的代理）对 publicnode 百 MB 级大扫描的真实表现未跑过
- [ ] 五档分层默认档位不适配目标供应量级时按数量级平移

---

## 8. 后续实测补充（2026-07-12，来自另一项目的 Solana meme 币分析实战，置信度高于上文反推内容）

以下通道已在真实分析中跑通，标注 [实测·他场景]，直接可用：

1. **全量转账＝SQD portal**（portal.sqd.dev，免 key 免代理）——采集器现役 **v2**，v4 正式边标准为 `[ts,slot,tx_index,-1,from,to,amt]`（§13b；`-1` 表示交易级净额边没有 instruction 顺序）；缓存使用 sha256(原始 mint) 路径。转账边=同 tx 内 owner 级净变动贪心配对，`edge_semantics="owner-net-greedy"`，from/to 为 ZERO 哨兵即铸造/销毁；它证明 owner 净变化，不证明链上精确 from→to。断点续拉按交易身份去重，meta 连续完成前缀防 off-by-one。
   **吞吐与架构选择**：v2 稳态约 255 倍实时（§13a 传输层翻案了旧的 1.5-4x 数字）——2-6 个月币龄全程重放数小时级；§11 混合重建（发射窗精确+核心实体流水+CPMM 重建+快照封口）降级为超长币龄（1 年+）专用。
2. **发射期精确定价**：GeckoTerminal 分钟 K `/ohlcv/minute?aggregate=1&limit=1000&before_timestamp=`（池创建起就有）；小时 K 翻页可拿全历史。pump.fun"发射即迁移"币无内盘 K 线，内盘成本用 GMGN dev avg_cost 近似。
3. **资金同源（gas 溯源）**：公共 RPC `getSignaturesForAddress`（翻到最老）+ `getTransaction(jsonParsed)` 找首笔 system transfer 入金 source；0.25s 间隔，代理经 `CHIP_PROXY`/`--proxy` 解析（`scripts/lib/proxy_config.py`）。识别马甲网络最有效的一招（母钱包收敛即实锤）。
4. **双跳换仓溯源**：老仓→一次性中转→新址的双跳必须重放溯源，禁止把前端 `transfer_in` 当独立新仓。（判例：casebook/entity-clustering.md E-04）
5. **铸造受益人全清单**：创建 tx 的全部铸造受益地址都作为 creator 系起点。（判例：casebook/entity-clustering.md E-12）
6. **bonding curve 成本校准**：枚数按 token 守恒重建；标准虚拟储备参数算出的 SOL 成本可能系统性低估约 10%，关键笔必须用 `getTransaction` 实付真值校准，批量值报告修正区间，并剔除毕业迁移笔。（判例：casebook/supply-accounting.md S-05）

（CLAW，07-12，经 onchain-data-accounts 记忆转录；第 5/6 条为 PUB 07-14 补充）

## 9. 锚点法演变重建 + gas 溯源加固（LAYOFF(Solana) 2026-07-15 实战）

针对"4-5 个月币龄全量 SQD 挂机不现实"的 Plan B 的一个更轻量替代，已在 LAYOFF 跑通：

1. **锚点法演变重建（免全量 SQD，`scripts/solana/build_evolution.py`）**：不重放每一笔，而是——①`fetch_pool_sigs.py` 拉主池全史签名；②等距抽签名做**池子余额锚点**（`decode_txs_v2.py --pool <池owner>` 每笔落 `pool_balance`）；③核心实体（top 大户 + 离场盈利榜 + 上游中转）用 `whale_deep.py` 拉 ATA 级全流水；④`build_evolution.py` 在时间点插值：各实体持仓从其逐笔流水累积、流动性池用锚点曲线、散户=总供应−已知−池−销毁残差。产出图1/图2 数据。**精度声明**：中小散户是残差估算，量级正确、单点精度有限，报告局限性须写明。
2. **decode 通道坑**：`getTransaction` 直连 `api.mainnet-beta` **恒 429**，须使用已配置代理（`decode_txs_v2.py --proxy "$CHIP_PROXY"`）；代理统一经 `CHIP_PROXY`/`--proxy` 解析（`scripts/lib/proxy_config.py`），不得写死端口。金额只用 raw integer，输出 `deltas_raw/pool_balance_raw + decimals`，UI 字段仅为精确十进制字符串；缓存及断点输出绑定 mint/pool/RPC，`decode_fail` 不算 done。v1 `decode_txs.py` 仅保留为逐笔兼容入口，已复用 v2 的输出身份、completed_sigs 和完整性 receipt；两版最终仍有失败签名都以非零退出。
3. **gas 溯源翻页上限（`gas_origin.py` 合并版）**：翻页上限已并入 `gas_origin.py`——默认 `max_pages=2`、超深地址标 `approx`，`--full` 恢复翻到最老的全量行为；落仓户签名少一页到底、秒完成。历史来源：gas_fast 加固，BONK 等案。
4. **服务 funder 排除**：gas 聚类只取最早 SOL 入金；候选 funder 必查余额与近千签名时间跨度。（判例：casebook/entity-clustering.md E-05）
5. **发射窗路由噪声**：owner delta 中的 AMM/路由瞬时余额不得直接判持仓。（判例：casebook/entity-clustering.md E-02）
6. **creator 履历与变更**：拉 creator 全发币履历、RugCheck 风险并对比 `set_creator` 前后身份。（判例：casebook/entity-clustering.md E-12）
7. **Streamflow feePayer**：服务 feePayer 不作控制边，去向必须靠代币流穿透。（判例：casebook/entity-clustering.md E-02/E-05）
8. **GPA 缓存与仲裁**：错误体禁缓存、缓存命中报告 mtime、增量前真扫；对账冲突先用第三通道查关键地址。（判例：casebook/supply-accounting.md S-04）

## 10. 快照对比法（已有快照之间的窗口流转复核）

旧研报为锚点法（非全量流水重放）时，增量更新**不必补拉全量转账**，走快照对比五步：

1. **新全量快照**：`scan_token_accounts.py`（Token-2022 记得 `--rpc api.mainnet-beta` + 先把旧 `_gpa_raw_*` 改名存档，见 §9.8）；同时 `getTokenSupply` 复验供给闭合（窗口内销毁体现在总量差）。
2. **快照 diff**：`snapshot_diff.py --old 旧owners --new 新owners --entities 实体表` → 实体逐址变动 + 大额变动榜（新面孔/清零标注）。**排名变化不是证据**（持有人增多会把静止地址挤出 topN），一切以余额 Δ 为准。
3. **窗口变动全覆盖定性**：`probe_window_moves.py --targets 变动榜 --cutoff <ISO时间>` → 每址 pool_buy/pool_sell/direct_transfer 分类 + 直转对汇总；大额变动地址必须 100% 覆盖，直转对按对手方 |Δ|。（判例：casebook/supply-accounting.md S-04）
4. **对账三查（轻量版）**：新快照加总=getTokenSupply（diff=0）；top20 与 `getTokenLargestAccounts` 双源对表（活跃池允许时点差）；重点地址签名史净额 vs 快照 Δ 分毫互验。
5. **观察哨核查加固**：余额不变≠没动（可能转出又转回）——sentinel 级地址补签名列表验证（窗口内零签名才是硬结论）。

配套纪律：cutoff 必须用 `datetime.fromisoformat` 验算；覆盖起点看数据末行，不看 `meta.updated`。（判例：casebook/supply-accounting.md S-06）

## 11. 长币龄混合重建 + 高密度期定向采集（USELESS(Solana) 2026-07-21 实战）

§8"全程 SQD 重放不现实"与 §9 锚点法的合体升级——14 个月+币龄、13.5 万持仓账户量级标的实战定型：

1. **混合重建演变架构（长币龄标准件，两端精确、中段插值）**：①发射窗（发射日起 24-48h）用 `window_fetch.py` 拉全量边（精确——狙击/bundle 分析必须逐笔）②核心实体（庄/项目方/大户）ATA 级全流水（`whale_deep.py`，精确）③中段日级锚点前向填充（`anchor_sampler.py`）④**当前快照封口 + 末日快照注入**——把 data_cutoff 日全量快照作为最后一个锚点注入序列，修"清仓发生在锚点观测窗外则旧值永久残留"的系统性尾部误差。图 1/图 2 由 ①②③④ 合成，散户=残差；精度声明照 §9 写进局限性（USELESS，07-21）。专案脚本不可直接复用：实体分组、发射日、价格文件名按案硬编码，新案仅参考算法结构重写；通用化抽象列遗留。
2. **SQD 高密度期定向拉取用小段+并发（`window_fetch.py`）**：密集期正解=**2000 slot 小段 × 8 并发**并强制 `--receipt`。gaps 非空时只留 `.partial`＋覆盖回执并 exit 2，正式文件名不存在；gaps 为空才原子发布。旧 gap 部分文件不得 cat 追加，补拉后整段替换或全字段 dedup；重放负余额暴增先查重复合并。发射窗峰值榜仍须剔除 pump.fun 官方毕业迁移钱包。
3. **日级锚点采样（`anchor_sampler.py`）与它的观测边界（★阴性依据禁用）**：正式运行强制 `--as-of-slot` 与 `--receipt`，receipt 绑定 mint/日期范围/覆盖；任一天 fetch_fail/no_converge 完整写结果后 exit 2。从新到旧滚动校准 slot↔ts；名义 1h 窗在高活跃期可能仅数分钟，且只记发生变动账户，静止大户仍系统性漏观测。
   因此**锚点单独不可作任何"某地址没动/没持仓"的阴性依据**，阴性结论必须快照或全流水兜底；锚点只用于正向变动观测与序列插值（对抗复核实测抓出，来源：USELESS(Solana) 分析，2026-07-21）。
   **【候选·单案】锚点复用两扫描（混合重建建议必做步，零边际成本）**：锚点序列采完后顺手做 ①**全 owner 峰值普查**（阈值 ≥1.5% 总供应）——产出"历史大仓名单"（含已清仓离场者），补当前快照视角的系统性盲区（快照只见在场者）；②**全史前三涨跌日×锚点对照**——最大涨/跌日与该日锚点观测交叉，抓事件日实体动作指纹（如拉高日金库调拨）。
4. **publicnode 大扫描死角补充（§0a/§1 的边界）**：13.5 万 token account 量级的 mint，publicnode getProgramAccounts 恒 504（dataSlice 也救不回）；**api.mainnet-beta 做 SPL 大扫描会静默返回空结果**（不报错——危险，靠对账关卡拦住，勿当"该 mint 无账户"）。
   分片扫描（`scan_sharded.py`，amount 低位字节递归分片）可行但两个坑：①owner 位置 memcmp 必须整 32 字节（1 字节分片语法合法但过滤不生效）②零余额账户 8 字节 amount 全零、全部堆在全零前缀片——递归下钻全零前缀至 8 字节终点片直接跳过（分析只要非零余额）。
   USELESS 案分片全量未跑完（publicnode 间歇 504），对账改用"8 样本独立单查 + top20 对表"替代过关——**分片器待后续标的全量验证**。**死角地图更新（GOAT 实测）**：24.7 万 token account / 67MB 响应量级，Helius + `--compressed`(gzip) + 300s 长超时**一次拉全成功**（publicnode 恒 504、Helius 默认 120s 超时也断；
   见 §1 实测升级行）——大盘子 mint 的 GPA 正解就位，分片器降级为末位备选（GOAT，07-22）。
5. **whale_deep 按地址频率分派（先估频再选通道）**：深挖前先 getSignaturesForAddress 拉一页估频——高频地址（creator 类，签名 7 万+）ATA 级全 decode 需数小时/地址不可行，改**事件窗定向拉**（只 decode 关键时间窗）；低频囤仓户（15-172 笔）全量 decode 秒-分钟级。一刀切全量 decode 会把预算烧在单个高频地址上。**cap 截断样本的用途边界 + Helius 并发纪律**：高频地址签名史翻到工具 cap（如 2000 笔）即**截断样本**——起点余额非零，**不可从零累积重建持仓时间线**，只能作"最近 N 笔行为定性样本"（流向画像/对手方指纹），时间线必须锚点/快照兜底且报告局限声明注明"截断样本"；Helius 免费档 10 RPS 是**账号级**配额——多进程并行互抢配额反而整体拖慢，正解 = `whale_deep.py --out` 分组独立文件防写冲突 + 总并发贴 10 RPS 不超发。
6. **letsbonk creator 经济流**：追踪 dev 直分后续流向、Raydium Lock harvest 与毕业迁移平台常数。（判例：casebook/entity-clustering.md E-12）

## 12. 销户账户覆盖审计（SQD 边集对账盲区加固，2026-07-21）

**盲区原理**：`getProgramAccounts` 快照只见**当前存活**的 token account；被 `closeAccount` 销户的账户（关闭前必归零）不影响期末供给闭合，但其全部中间路径（吸筹/中转/出货边）若被采集通道漏掉，"重放 vs 快照"对账**天然看不见**——快照侧根本没有这些账户。而销户恰是 bot/中转/洗仓账户的常态收尾动作。

**独立发现源**：普通 Transfer 指令不引用 mint，但 ①一切 token account 的初始化指令（initializeAccount/2/3、ATA create，含 inner CPI）**必引用 mint** ②交易 meta 的 pre/postTokenBalances 条目自带 mint+owner。因此"mint 自身签名史"与"区间内 getBlock 整块"是不依赖 GPA 快照、不依赖 SQD 自身的第三方账户目录——用它抽查 SQD 边集，专测销户账户的转账覆盖。

**脚本**：`scripts/solana/audit_closed_accounts.py <MINT> [--edges <soltx.jsonl.gz>]`（对旧研报目录审计用 `--edges/--out` 指路径）。流程=发现历史账户样本 → getMultipleAccounts 判存活/销户（此法 publicnode 屏蔽，走 api.mainnet-beta+代理）→ 销户账户拉自身签名史（销户后签名史仍可查，§3a 坑 4 同源事实）decode 实际转账 → 逐事件对照边集。

- **两种样本发现模式**（`--mode auto|sigs|blocks`，默认 auto）：sigs=mint 签名史抽样（全程边集适用；签名史新→老翻页，历史定向段边集会翻不到区间）；blocks=边集 slot 区间内均匀抽 getBlock 整块提取（定向段正解，免翻页）。auto 3 页探路未进区间自动切 blocks。
- **判定粒度声明（v4 定稿）**：默认正式入口只接受 v4 7 元组并校验 `tx_index/instr_index`；旧 5 元组只允许显式 `--legacy-sol5` 诊断，报告强制 `non_formal=true/order_ambiguous=true`，不得冒充正式输入。`audit_release_gate.py` 对 `dormant_warehouse_audit.json` 的这两个字段均要求显式 `false`，字段缺失或任一为真都阻断发布。base（未修复原账）的覆盖谓词仍只是“边集中存在同 slot 且 from/to 含该 owner 的边”，同 slot 同 owner 多笔可能误判；7 元组堵住格式降级与 DISTINCT 吃边，但不会把普通销户抽查自动升级为 transaction-exact（逐交易精确）。**缺陷 slot 经修复代替换后则已是 transaction-exact**：修复生产者按签名取参考源交易、统一重编号，`exact_reconcile` 再深验修复 bundle（成套证据包）与边源。跨源身份只认签名，不比较两个来源各自的交易位置编号。`CLEAN` 只按所走路径的已声明强度解释。
- **undetermined 语义（诚实纪律）**：深挖账户按结果分类 events_found / all_zero_delta / fetch_failed——后两类是"没查出来"不是"没事件"（高频中转户 delta 笔可能在 --deep-sigs 窗口外），不构成"无漏"证据；过半 undetermined＝样本无效（批 D GPT-F-06 起 exit 1，不再只告警）。
- **退出码**：0=抽样零漏边；2=发现漏边（对账 gate 语义，报告 missing_detail 带 tx 级证据）；1=运行失败/样本无效。**样本无效机器判据（批 D GPT-F-06 收口，任一命中即 exit 1）**：任一 getMultipleAccounts 批失败／深挖账户全部 fetch_failed／checked=0 且 closed>0／墙钟截断／undetermined 过半。
- **报告 status 契约（批 D）**：`CLEAN`（checked>0 零漏，exit 0）／`NO_CLOSED_SAMPLED`（抽样内无销户账户，审计对象为空——**弱结论**，exit 0，只证明"这批样本没有销户账户"，不冒充"销户路径零漏"强证明）／`LEAK_FOUND`（exit 2）／`INVALID_SAMPLE`（exit 1，`invalid_reasons` 逐条列明）。早退路径（边集缺失/签名史拉取失败/抽样零命中）同样落精简 status 报告——不存在"失败无报告"形态（消化轮 1 F-D8）。
- **定位**：销户抽查仍是补充证据；但 SQD coverage 探针（覆盖健康检查）和 Solana `exact_reconcile` 已是 A2 硬 gate。先由探针判健康或缺陷，再按 §13e 走修复生产者；禁止拿 `window_fetch` 追加几条边冒充缺口闭合。

（Helius vs SQD 采集通道交叉复核——codex 第二意见提议"用 mint 初始化历史反向审计数据湖"，本脚本为其工程化落地并经 PUB/USELESS 双案冒烟；07-21）

## 13. Solana 采集加速工程（2026-07-21，@CX 交叉复核定案后实施）


### 13a. 传输层实测真相（改变所有 SQD 件的三个数字）

- **gzip 压缩 = 21 倍**：同段对照实测明文 4.65 slots/s vs `--compressed` 98 slots/s（wSOL 高密度压测,压缩比 ~40x；普通 mint 预计 5-15x）。requests.Session 默认协商 gzip——**新脚本一律 requests,遗留 curl 件必须补 `--compressed`**。
- **限流真相**：文档标称 20 请求/10 秒,长流模式实测**碰不到**（串行 30 请求 0 个 429、8 路长流并发全 200）;真实瓶颈=**单 IP 总带宽整形 ~1MB/s**（3 路与 8 路聚合吞吐相同——加流数不加总量,多注册 key 无意义）。
- **服务端单响应上限**：解压后 ~32MB 自动截断,客户端按最后 slot 续拉即可（v1 的 50K 段超时死循环是明文时代 150 秒传不完一个响应所致,压缩后自愈）。
- **SQD gateway key**（api-keys.md 第 15 节「SQD Portal」,存 `~/.config/sqd/api-key`）：公共 datasets 路径实测**完全不认证**（真/假 key 全 200）——**直接匿名调用即可,不需要配 key**。该 key 实为旧版 SDK 网关用途,Portal 正式 key 体系官方尚未上线,**不存在"专属端点 URL",无需再等用户抄回**（2026-07-21 定论,2026-07-25 复核确认）。

### 13b. 全程采集器 v2（`fetch_sqd_transfers_v2.py`，全程重放主力）

三刀：requests.Session（连接复用+自动 gzip）/ 自适应区域并发（全局段队列动态领取,区域大小按耗时自动伸缩 1 万-100 万 slot,发射窗自动缩、死亡期自动放大）/ 全局令牌桶（默认 4 rps 防雪崩护栏——高密度段 1.6 会顶死请求数,实测教训）。失败区域重试 2 轮后进 gaps 继续别的段（修旧采集器"第一个未完段之后整体丢弃"缺陷）,gaps 非空退出码 2、清零前不得进重放。v4 正式缓存绑定原始 mint/endpoint、采集器启动哈希与 finalized 上界并使用 7 元组；按 `(slot,tx_index)` 的完整交易边集 digest 去重，同身份异 digest 硬失败。旧 v3 meta 与 5 元组没有交易身份、不可迁移，必须在任何网络请求及 v4 parts 创建前拒绝续跑并明示全量重采。
普通密度币自适应放大区域后更快——**2-6 个月币龄全程重放=数小时级,夜间挂机稳稳可行**;§11 混合重建降级为超长币龄（1 年+）专用。

#### v4 provenance 的保护范围与信任前提

`collector_sha256`、producer history、`edge_logical_sha256` 与 `edge_rows` 是完整性和版本对齐防线：
它们防止版本漂移、旧采集器产物误入正式链，以及未登记改装采集器冒充现役 producer。修复代还必须同时满足当前 base 绑定、coverage resolution（缺陷裁决）、repair bundle（修复证据包）、`CURRENT.json` 指针与 ACTIVE 修复生产者哈希；只拿一份 repaired meta（修复后元数据）不构成可信输入。登记哈希可由
`git show <commit>:<script> | shasum -a 256` 公开复算，**这些代、bundle 和哈希仍不是密码学签名**。

这套防线假设工作目录的 `data/` 可信。若对手已经能向该目录同时落盘自洽伪造的边、meta 与快照，
现有校验只能证明这些本地文件彼此一致，不能证明边确实来自链上采集，也不能阻止伪造件骗过
`gate_pass`。抵抗这种主动伪造需要签名或独立链上重验，是根治宣告后的独立工程；本轮不实现，也不得
把当前 provenance 宣称为具备该能力。

#### SQD stream 响应语义（2026-07-26 实测定案,判完备性的地基）

判"这段扫完没有"只能靠下面四条,**别拿"响应有没有行"当失败信号**：
- **空区间不返回空**：区间内有块但该 mint 无数据时,服务端回**稀疏 header-only 行**标记扫描进度（实测 100 万 slot 的空区间回 20 行、推进到 +3,905;1000 万 slot 同样 20 行 640 字节）——客户端按最后 header 续拉即可,这是正常推进不是失败。
- **零行的唯一正常成因＝区间内一个块都没有**（Solana skipped slot 串,leader 没出块）。实证：BONK 现场 4 段复验,去掉 mint 过滤依然零行,而包围 ±60 有 103-112 个块。
- **HTTP 204 ＝ fromBlock 超出服务端已索引范围**（0 字节）。**绝不能判完成**——那是漏数据,只能按可重试失败处理。
- **`/head` 给的是 unfinalized head**,响应头 `x-sqd-finalized-head-number` 比它小约 2,900 slot（实测）。采集上界取 `/head` 没问题（实测到 head 仍正常返回数据）,但别拿两者的差当异常。

SQD **无块头（NO_HEADER）**不能只靠 SQD 自己最终确认；前提是参考源可查询该时代且本轮额度可用，再用参考源 `getBlocks` 取得该区间真实出块位图逐 slot 对照。代价按区间长度近似线性增长，跨度大时应先按 coverage 分段，不得用一次超宽调用掩盖部分失败。

#### 空 slot 完成判定与 scan-fail 契约

- **触发条件**：scan_area 收到 HTTP 200，但流中没有数据行。
- **必做动作**：complete 仅在“HTTP 200 + 无截断行 + 无连接层异常”时为真。零行且 complete：跨度 ≤ EMPTY_MAX（默认 500 slot，可用 --empty-max 调整）直接完成；更宽区间必须调用 Fetcher.probe_blocks()，只请求 block.number、无 tokenBalance 过滤，服务端上限 20 行。探不出块才完成，探到块按过滤路径异常重试。每次裁决写日志与 meta.empty_ok {n,max,intervals}。
- **阻断语义/失败码**：HTTP 204、流不完整、探针失败、或探到块但 mint 流零行，均不得判完成；继续重试，最终进入 gaps[scan-fail]，gaps 非空退出码 2。
- **权威测试**：scripts/tests/test_sqd_merge_equiv.py 的零行五分支与 scan_area 尾段契约；端到端只要求退出码 0 且 gaps=[]。

#### 收尾合并与缓存原子性契约

- **触发条件**：旧缓存与本轮 parts 收尾合并。
- **必做动作**：预估行数 > MERGE_INMEM_MAX_ROWS（默认 800 万，可用 --merge-max-rows 调整）走 DuckDB 外排，memory_limit=4GB、threads=4、临时目录 data/_merge_tmp；阈值内走内存。无 DuckDB 时明确告警后回退内存。旧缓存只做流式行数、gzip CRC 与前几行抽验，不全量载入。
- **原子落盘**：内存/外排两条路径都先写临时文件再 os.replace；中断不得破坏旧缓存，零边不改缓存。
- **等价口径**：amt 可超 int64，外排全程按 VARCHAR；只允许 slot/ts/tx_index/instr_index CAST BIGINT。每个 source 内先规范化完整交易边集，跨 source 按 `(slot,tx_index)` 的 `tx_digest` 去重；同身份同 digest 留一份、异 digest 硬失败。排序固定走共享 `edge_sort_key`（边排序键）＝`(slot,tx_index,from,to,amt文本)`；base 与修复代合并也必须用同一键，确保内存/外排/修复三条路径逐字节一致。
- **阻断语义/失败码**：临时文件未完整、gzip/JSON 体检失败或合并异常，不得替换旧缓存，命令非零退出。
- **权威测试**：scripts/tests/test_sqd_merge_equiv.py；覆盖两路径等价、同交易跨 source 去重、同身份异 digest 拒绝、同五字段异 `tx_index` 留二、旧/混合行宽拒绝、超 int64、ts=0、大数保真、路径选择、原子落盘与零行判定。

历史症状与修复经过已由 3.34.0 CHANGELOG 记录，不进入现役执行页。

#### 无 sig 但有交易身份时的去重边界

SQD 不落盘签名不等于没有数据集内交易身份：请求与响应已有 `transactionIndex`，所以 v4 用
`(slot,tx_index)` 标识 SQD finalized 区间内的交易。**`tx_index` 是 SQD 内部排除投票交易后的重编号，不等于链上或 RPC 返回数组里的绝对位置**；缺陷 slot 修复后统一改用参考源非投票序号（`reference-nonvote-ordinal/v1`）。跨源身份只用交易签名，禁止拿两个来源的位置编号互比并据此判缺失。每笔交易先生成
完整 transaction-net 边集，再对排序后的边集计算 `tx_digest`；同一身份重复出现且 digest 相同
只留一份，digest 不同说明数据源对同一交易给出冲突内容，必须硬失败，禁止静默选一份或取并集。
旧 5 元组无法区分“同 slot、同额、同 owner 的两笔真实交易”与重复采集，按五字段 DISTINCT 会
误杀；它只允许走显式 legacy 诊断入口，不得生成 v4 meta/reconcile/READY，也不存在补身份迁移。
重放/快照差异正负成对时，仍以 ATA tx 级真值对受害地址做替换式修复并复验锚点，禁止追加式
补边。（判例：casebook/supply-accounting.md S-04）

### 13c. 溯源解码 v2（`decode_txs_v2.py`,三板斧落地）

JSON-RPC batch + 跨地址共享 sig 缓存（`--cache-dir`,按 sig 前 2 字符 256 片）+ `--rpc` 端点可换。**mainnet-beta 实测硬墙**：batch 内子请求被**按方法逐个限流**（"Too many requests for a specific RPC call"）——batch 默认 8,429 子请求自动收回重试，绝不能记 decode_fail。公共节点净速度收益约 1.5 倍；**真价值=①缓存**（关联地址重复交易第二址起零请求）**②Helius key 存在即切**。**运行前检测 `~/.config/helius/api-key`**：存在则按下列 Helius 参数跑，缺失则降级公共 RPC（key 注册沿革见 CHANGELOG）；端点国内直连免代理；**实测免费层不支持 batch**（403 码 -32403,单元素数组同拒），账号级上限 **10 RPS**——正解=`--rpc https://mainnet.helius-rpc.com/?api-key=<key> --workers 6 --interval 0.12` 单笔并发贴近上限；archival 10 credits/笔,免费月额≈10 万笔。更高套餐能力未经本管线实测，不得把 50 RPS 或可 batch 当通用口径。
**⚠ urllib 逐笔新建连接对 Helius 会 sock_connect 挂死**：decode_txs_v2 在部分本机网络环境下逐笔 urlopen 挂起（即使 `ProxyHandler({})` 强制直连也不稳）——症状是单笔卡住无超时推进。绕行=手写 `http.client.HTTPSConnection` **keep-alive 长连接**版；根治通道=environment.md B5 的 `scripts/lib/net.py`（httpx 连接池），新写解码脚本直接用它，别再走 urllib。

### 13d. Solana HyperSync 通道（**已禁用**——完备性验收不通过，GA 后重验；全量细节见 git 3.18.x 条目）

- **判决（3.18.0，BONK 三区实测+Helius 链上终审，07-22；v4 收口 2026-08-17）**：历史区持久缺行越老越糟（head-450 万缺 3.6%、head-1450 万缺 22%）、近端乱序回填暂态洞且**静默快进 next_slot**（单跑无法自知数据洞）——❌全程采集第二引擎**硬禁**；`fetch_sqd_transfers_v2 --hypersync` 与直接 `run(hs_cfg=...)` 均在首个业务请求前 exit 2，不再提供“仅实验”的隐含五元组出口。✅独立工具对摄取前沿附近（约 20h 内）作非正式对照源/指纹查询仍可用，但不得签发 v4 cache/meta。
- **GA 后重验路径**：对账脚本 `scripts/solana/hypersync_recon.py`（三区各跑一轮+Helius 终审定责）；mint 过滤隐藏能力、跨源对账三工程坑、双引擎吞吐 POC 细节从 git 考古（3.18.x）。
- **⚠混合分段提议已否决，勿再重议（07-22 @CX）**：滚动窗口是覆盖范围不是准确范围；洞静默→证明某段完整的唯一办法=SQD 重拉对账，HS 等于白跑；供给对账兜不住成对缺行（借贷双缺仍守恒），完备性必须落到边集合一致；SQD 全量恒为关键路径，双引擎不缩短认证耗时。

**遗留后续项**：①~~v2 整合 HyperSync 第二引擎~~ ②~~完备性验收~~（均 3.18.0 完成，验收不通过→禁用待 GA 重验）③Helius key 运行时检测（见 §13c）④SQD key 专属端点补录 ⑤实时 mint 档案（方案 4,用户暂缓）。

（Solana 采集加速工程,@CX 三轮交叉复核 + 本机四组实测,2026-07-21;完备性验收与双引擎整合,2026-07-22）

### 13e. SQD 数据集已知缺陷与覆盖健康闸

**先说结论**：SQD 会在 durable-nonce（耐久 nonce，一种不依赖近期 blockhash 的 Solana 交易）附近，按 slot 小区段把整笔交易静默漏掉。缺口可短到 1 个 slot，也可能落在旧共享地图跨度外；2026-06-13、06-15、06-16 的冻结实证共确认 **38＋2 段**。因此“下载成功、供给闭合、余额残差总和为 0”都不能单独证明边集完整。

**探针四态（`sqd_coverage_probe.py`）**：探针不是补边器，只负责给每个 slot 贴机械状态。

- `HEALTHY`：SQD 块头与 nonce 指纹符合该时代的健康基线。
- `NO_HEADER`：SQD 没给块头；最终是否真跳块必须由参考源 `getBlocks` 位图确认。
- `DEFECT_CANDIDATE`：典型指纹是 **“SQD 有块头但零 AdvanceNonce”**。这只是缺陷候选，不能直接当漏交易结论。
- `ERA_UNCERTAIN`：时代校准或样本量不足，现有阈值不能可靠下判；必须补探针，不得当健康。

`getBlocks` 确认的前提是参考源覆盖目标历史、返回完整、额度尚可；成本随待确认 slot 数增长。先用 SQD 块头和已知地图缩小范围，再逐 slot 核对，禁止对超宽区间一次请求后把部分结果当全量结果。

**正式产物窄门**（完整字段和消费者清单见 `scan-schemas.md` §14）：

1. 探针发布 `sqd-solana-coverage/v1` 和 `sqd-solana-coverage-pointer/v1`；`CURRENT.json` 是当前 coverage 的原子指针。
2. `sqd_gap_repair.py/v1` 只修已确认缺陷，产 `sqd-solana-coverage-resolution/v1`、repaired `sqd-solana-cache/v4`、`sqd-solana-repair-bundle/v1` 与 `sqd-solana-repair-pointer/v1`。交易按签名取参考源真值，并统一成 `reference-nonvote-ordinal/v1`。
3. pending（尚未发布目录）不能被消费；bundle、代、base、coverage 与指针必须全套同代。**修过账不退回 base、base 重采即代全作废**：resolver（正式边源解析器）一旦确认当前 base 需要修复，就不得静默回退原账；base 内容一变，旧修复代的绑定自然失效，必须重探、重修、重发。
4. A2 的 Solana 对账是五查：coverage 是 `exact_reconcile` 的强制输入；`solana-reconcile/v4` 与 wrapper `reconciliation-report/v3` 任一深验失败都停。下游 wave/flow/entity/curve/audit/evolution 产物必须带 `edge_source_binding`（边源绑定），并与 exact receipt 的 `{cache_kind,gid,soltx_edges_sha256,soltx_meta_sha256,edge_logical_sha256}` 全等。

**共享地图生命周期**：已知缺陷地图只省重复探测，不替代本案证据。地图 TTL（有效期）为 30 天；已知缺陷 slot 仍逐个复核；每次运行抽 canary（哨兵 slot）验证健康区和已知缺陷区，任一不符就停止复用并重建地图。

**参考源与额度**：正式修复的唯一参考源是 Helius。准确性优先，工单不设预算上限；但“无上限”不等于无限重试。遇配额耗尽或计费拒绝，先原子落 STOPPED/ledger（停工状态和额度台账），干净退出，再换已登记 key 续跑；禁止降级到另一 RPC 拼出“看起来闭合”的代。

**止损纪律**：先走 α（覆盖普查与签名差集），只有残差仍未归因才开 β（余额连续性二分）。β 最多 3 轮；一轮后残差数量/金额不下降就立即停，保留证据并上报。禁止对每个残差账户做 BFS（逐账户向外无限扩散补账）追求清零；那会把诊断变成不可审计的找数游戏。

---

## 14. ★日级余额快照重建法（长币龄演变默认方法；GOAT 2026-07-26 翻案驱动）

### 14a. 锚点法用途边界

锚点只作粗趋势；中段数值必须用日采样或全量重放。仅末日封口的序列须声明中段为插值，倒数第二日到末日任一阵营跳变 >1pp 即阻断交付。（判例：casebook/supply-accounting.md S-04）

### 14b. 日级余额快照重建法（本案验证可用，成本仅全量解码的 2%）

**核心思路**：不重放每一笔转账，而是**每天取一个真实余额快照**。前向填充仍然用，但这次有据——某日该账户无成功签名，就是真的没动过。

四步（脚本见 GOAT 案 `data/exit_trace/{daily_plan,decode_bal,rebuild_series}.py`，待收编 `scripts/solana/`）：
1. **拉全签名**：对每个跟踪 owner 的每个 ATA 拉完整签名史（`getSignaturesForAddress` 1000 笔/请求）。
2. **按日压缩**：签名倒序返回，**每日首次出现的即当日最后一笔**；剔除 `err != null` 的失败交易（不改变余额）。
3. **解码取余额**：只解码这 8,302 笔，从 `meta.postTokenBalances` 取该 ATA 的**绝对余额**（不是 delta），需用 `accountIndex → accountKeys[i].pubkey` 映射出账户地址。
4. **重建序列**：每 ATA 按日填余额、无采样日沿用前值；owner = 各 ATA 求和；阵营 = 同阵营 owner 求和；散户 = 总供应 − 已知。

**三个必踩的坑**：
- **投毒采样点不填 0**：ATA 不在 `postTokenBalances` 时跳过该采样点并保持前值。（判例：casebook/supply-accounting.md S-04）
- **并发要给解码让路**：拉签名与 `getTransaction` 抢同一份 RPS。Helius 免费层 10 RPS，实测 4 并发拉签名 + 6 workers 解码会触发限流退避，把 3 分钟的活拖成 53 分钟。拉签名阶段用 2 并发。
- **超高频 ATA 要设深度上限**：DEX 池/CEX 热钱包的 ATA 签名史可达数十万笔，脚本必须带 `CAP`（本案 25 万）与截断标记，否则单个地址能把整个计划卡死。

**验收标准**：重建末日值与 `getTokenAccountsByOwner` 实查逐地址对表，TOP12 须逐个吻合（本案唯一偏差是 CEX 地址在快照日之后的真实变动，属正常）。

（GOAT 全量流水重建翻案，07-26）

## 15. pump.fun 长内盘期全量重建（签名史双索引法；TROLL 2026-07-29 实战）

**适用场景**：老 pump.fun 币在内盘（bonding curve）滞留数月甚至一年以上才毕业——内盘期交易稀疏，但**不能不采**：做量脉冲、早期集群、毕业前试盘仓全藏在这段。用 SQD 扫这段 slot 区间在死亡期每响应仅推进 ~3900 slot，工程上极不划算。与 §8 CLUDE"Plan B 混合架构"的分工：那是**高密度短币龄**的取舍方案；本节是**稀疏长内盘期**的全量精确解——稀疏恰恰使逐笔 decode 可行。

**方法（双索引 ∪ 迭代补边）**：
1. **curve PDA 签名史全翻**（getSignaturesForAddress 到最老）——内盘期所有对售货机的买卖必经它；
2. **∪ mint 签名史**（before 锚定翻老）——补 curve 索引外的铸造/销毁/初始化事件；
3. 两个索引合并 decode 全部 tx（tx 级全边，含 inner）；
4. **差异地址 ATA 迭代补边法**收敛盲区：重放期末 vs 毕业时点持仓对表，差异地址拉其 ATA 签名史补 decode——**理论盲区=双方 ATA 都已存在的用户间直转**（不经 curve 不经 mint），迭代到差异清零。
5. **独立通道抽验**：SQD 兜底扫一小段与 decode 结果逐边对表。

**产出与衔接**：内盘边集（如 `data/curve_pre_edges.jsonl`）不得直接与 SQD base 手拼；先按 §13e 的修复生产者正规化（统一交易身份、`edge_sort_key`、bundle 与 `edge_source_binding`），再与主段正式边源拼成全史边集。衔接缝（锚点 slot 前后几万 slot）注意 mint 签名史补齐，否则供给闭合差在缝里。报告局限性声明理论盲区（供给闭合零差时可写"盲区规模可忽略"）。

**配套工程数字**：SQD 对"单一连续大空洞"**只有 1 个 worker 有效**——并发单位是空洞段，同段 4 进程分片互相拖慢（服务端时间片均分），单进程 ~3450 slots/s 反而最快，别对死亡期空洞开分片；高频 ATA（池子级）签名史翻页必须设 CAP（~20 页）防拖死；ATA 的 PDA 派生纯 Python 可推（ed25519 on-curve 检查 ~30 行，无需 solders 依赖——`entity_identity_gate.py` 已内置同款实现可抄）。

（TROLL，07-29——创建时点 2024-03-10 至毕业 2025-04-20 共 13 个月内盘期全量重建，供给闭合差 1.19e-5%）
