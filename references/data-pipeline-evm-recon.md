# EVM 链数据管道 · 对账与重放引擎（data-pipeline-evm 分册 3/3）

> 母文档：`data-pipeline-evm.md`（已拆为薄路由索引页，文档级引言与时效纪律见索引页）。本册覆盖原 **§5 对账 gate / §11 公共数仓准入实证与分工定稿 / §12 DuckDB 重放/缩图引擎**；§1/§2/§3/§6/§7 见 `data-pipeline-evm-channels.md`，§4/§8/§9/§10 见 `data-pipeline-evm-sources.md`。正文 §N 交叉引用一律为母文档节号。规则逐条原样迁移、零改写；最后整编 2026-07-22。

## 5. 对账 gate（数据不闭合不进分析）

标准四件套，全过才允许跑下游分析：
1. **重建余额 vs GMGN top10 精确对表**：全量转账逐笔累加重建每地址余额，与 GMGN top10 逐个对到个位数。曾在扫块进度 97% 时 4/10 MISMATCH、补扫 remaining=0 后 10/10 全 OK——证明该 gate 能兜住数据缺口；预跑一次有提前暴露口径问题的价值，但通过判定只认补扫完成之后。（来源：OPN(BSC) 分析，2026-07）
2. **全网余额和=0**：所有地址重建余额求和应为零（mint/burn 计入），不为零即漏了转账段。（来源：SIREN(BSC) 分析，2026-07）
3. **总量恒等式 wei 级闭合**：跨链代币各链余量之和 ≈ 总供应，精确到 wei。（来源：OPN(BSC) 分析，2026-07）
4. **时间戳锚点插值抽查**：锚点表（每隔固定块距，或每 100 万块一个）bisect 线性插值出的日期，抽几笔与浏览器页面核对。（来源：OPN/SIREN(BSC) 分析，2026-07）
5. **重放前置完整性检查（快照缺块防护，重放开跑前做）**：核对全部采集 run 的 done.json——next_block 全部达到目标块、mtime 晚于最后一次采集启动，才允许重放（实锤：重放跑在尾部 run 拉完前 13 分钟，快照缺尾部 ~980 块/682 条）。**机制警示：供给闭合恒等式（上面第 2/3 查）对"缺整行"免疫**——整行缺失时借贷两边同时缺、sum 恒等于 TOTAL 照样通过，此类洞只有 RPC 抽查负余额能暴露；增量重放出现"期初为 0 的地址转出变负"=上游快照有洞的指纹，见到即停下补数据。（来源：QUQ(BSC) 完整版分析，2026-07-22）

**对账比对的 DuckDB 两坑（2026-07-25 实测，两个都会静默产生错误结论）**：
- **`read_csv` 把 wei 值推断成 DOUBLE → 制造全量假差集**：独立源 CSV 与主数据做六元组比对时，`read_csv`/`read_csv_auto` 会把 20+ 位的 wei 十进制串推断为 DOUBLE，精度丢失导致**每一行都对不上**（看起来像"数据源完全不一致"的灾难性结论）。对账读 CSV 一律 `all_varchar=true` 后显式 `CAST(... AS HUGEINT)`。
- **`others` 是保留字，不可作列别名**：`SUM(...) AS others` 直接语法错误（`Parser Error: syntax error at or near "others"`）。聚合列命名避开 `others`/`day`/`filter` 等保留字。
（来源：BUILDon(BSC) 分析，2026-07-25）
- **区块号区间不可用于估算时间分布（传播级错误源）**：据"96% 的转账落在块 50M–72M"推出"96% 发生在
  2025 上半年"，实测**只有 32.78%**（H2 反而占 61.64%）——BSC 2025 年把出块时间从 3 秒压到 0.75 秒，
  **同样块跨度对应的真实时长差 4 倍**。任何"某时期占比"类结论一律 join 区块时间戳按日/月归集后再统计，
  禁止块号线性外推。对所有近年提速过的链（BSC/Arbitrum/opBNB…）都成立。（来源：KOGE(BSC) 分析，2026-07-25）

**对账差额排查步骤（供给恒等式不闭合时按序查）——查完常规漏段后必查 Burn/Mint 独立事件**：2017 老版 OpenZeppelin `burn()` 只发 `Burn(address,uint256)` **不发 Transfer**——只采 Transfer topic 重放会出现"重放净供给 > 链上 totalSupply"的幽灵差额（LPT 案 604 枚，burner 主力=治理合约每次投票烧 100）。排查法：web3_sha3 算 Burn/Mint topic0 后 HyperSync 定向拉（几秒）；注意新链侧可能是"Burn 事件+Transfer(to=0x0) 双发"路径（此时 Burn 事件是 Transfer 的子集，不另计，勿双扣）。链无关坑，凡 2018 前老合约必查。（来源：LPT(ETH+Arbitrum) 分析，2026-07-21）

加分项：重建结果与第三方链上分析师独立披露的同口径数字对表，独立吻合是结论可信度的最强背书（具体数字属于当次报告，不进本手册）。（来源：SIREN(BSC) 分析，2026-07）

## 11. 公共数仓准入实证与分工定稿（ASTEROID(ETH) 三源对账,2026-07-21）

**准入实证**：ASTEROID(ETH,22 个月史) 抽 5 代表日——部署日(14,447)/低活日(47)/极稀日(全天 1 条)/峰值日(Musk 事件 114,010)/近期日(3,966)——合计 132,471 行,AWS 公共数据湖 v1.0/eth 与 BigQuery goog 官方版**双双与 HyperSync 基准逐行字节级等价**（键 (block,tx,log_index) 零差集、值 (from,to,value) 零不一致）。"HyperSync vs 公共数仓谁的质量高"在 ETH 段的实证答案：三源等价。

**分工定稿（用户 2026-07-21 拍板）**：
- **采集主力=HyperSync Starter + v2 官方客户端**（不变,见 §1 首选）。
- **BigQuery=备用+出错复核源**（`fetch_bigquery.py`,仅 ETH——goog 数据集无 BSC/Base）：HyperSync 结果可疑、对账 gate 挂了、或平台级故障时上。**成本实测推翻旧估**：按币活跃日限定日期分区后单次只扫 ~12GiB（旧悲观估算 200-500GiB 是无日期限定的全表扫）,免费 1TiB/月≈85 次复核。
- **AWS 数据湖=已验证等价但 pass 掉**（用户拍板：太慢）：S3 无服务端过滤,单币复核也必须整分区下载（99%+ 流量是无关合约数据）,宽带 1.7MB/s 实测 5 分区 4.9GB/60 分钟。**不做采集器**;仅当需要"与 Google/Envio 都无利益关系的第三独立源"或前两家全挂时手工走。
- BSC 的独立对照源仍只有 SQD Portal（AWS bnb 无 logs 表、BigQuery 无 BSC——格局未变）;Base 的 sonarx 表(T+7)未做准入测试。

**BigQuery 操作要点**（细节见 fetch_bigquery.py docstring）：
- 表 `bigquery-public-data.goog_blockchain_ethereum_mainnet_us.logs`（列含 topics REPEATED/block_hash/removed）,raw logs 自解码,**禁用现成 token_transfers 解码表**（AWS 侧同名表有浮点精度事故公开前科,规则跨仓通用）。
- 查询必带日期条件（脚本强制,防全史扫爆额度）+ dry run 熔断（config `max_scan_gib`）。
- 一次性前置已完成态：GCP sandbox 项目+OAuth 凭据缓存见 api-keys.md 第 17 节「Google Cloud / BigQuery」;**新 Google 账号首次用 GCP 必须网页接受 ToS**,否则 API 建项目 403 `Callers must accept Terms of Service`（2026-07-21 实测,console.cloud.google.com 勾一次即解）。
- 产物=标准 8 列 CSV(与 fetch_sqd_evm 同款),对账走 `transfers_lib.py merge`（fail-closed）。

**AWS 手工方法留档**（pass 但方法保号,应急可复活）：匿名公开桶 `aws-public-blockchain.s3.us-east-2.amazonaws.com`（免账号,list-type=2 列目录）,`v1.0/eth/logs/date=YYYY-MM-DD/` 每日单 parquet 0.5-1.15GB;**新鲜度实测 T+1~T+2**（优于 sonarx base/arbitrum 的 T+7）;逐 row-group 读+address/topic0 过滤自解码（本次验证脚本逻辑存 CHANGELOG v3.12.1 条目所述会话,核心=pyarrow read_row_group 选列+topics array 解 from/to/value）。

**新源准入通用纪律**（本次定型,适用任何未来数据源）：抽代表日分区（部署/极稀/峰值/近期四型必含）→ 与主通道按 (block,tx,log_index) 键+(from,to,value) 值集合对账 → 全等才准入该链该历史段;禁止拿"品牌可信"替代逐行对账。

## 12. DuckDB 重放/缩图引擎（亿级样本主路径，2026-07-22 三样本对表定版）

**定位（选型决策）**：`replay_duck.py`（pass1+pass2 合一）与 `cluster_prep_duck.py`+`cluster.py --prep` 是**千万行以上样本的重放与聚类主路径**；旧引擎（replay_pass1/2 纯 Python 逐事件）保留为小样本快速路径与黄金基准。动机=旧引擎内存随事件数线性涨（140 万行实测 1.22GB → 亿级外推 ~90GB，16GB 机器不可行）；DuckDB 路径内存设上限、超限落盘外排。

**等价性实证（改任何引擎前先读这段的验收口径）**：三样本七项全等——ASTEROID(ETH,140 万行,v1 CSV 单通道)、SIREN(BSC,2169 万行,三通道段拼接)与旧引擎产物 **7 项逐字段全等**（replay_stats 契约 8 键 / merged.csv 逐字节哈希含 \r\n / balances_final / peaks / mint_ledger / camp_series / entity_series）；QUQ(BSC,1.03 亿行,v2 parquet) 与 replay_pass1_quq 原产物 **stats 11 键 + balances 51,871 址 + daily_delta 1,959,664 键逐键逐值全等**（peaks 口径不同：QUQ=事件级、标准=块末级，弱验证"事件级≥块末"零违例、98.3% 相等）。聚类侧 ASTEROID 沙盘老路 vs --prep **四类判定产物全等**（clusters/gatekeeper_blocked/label_excluded_nodes/team_downstream）。

**性能基准（M3/16GB 实测）**：
| 样本 | 旧引擎 | DuckDB 路径 |
|---|---|---|
| ASTEROID 140 万行 | pass1 6.7s/1.22GB + pass2 2.1s | 合一 6.1s/1.4GB（小样本无优势,CSV 解析占大头） |
| SIREN 2169 万行 | 外推 ~19GB 内存（不可行边缘） | 167s / 峰值 7.1GB（守 8GB 限） |
| QUQ 1.03 亿行 | 纯 Python 专用变体数十分钟级 | 核心重放(余额+daily) **31s**；含块末峰值窗口 7.8min/8.1GB |
| QUQ 缩图 | cluster 老路四容器不可行 | **19.5s/1.35GB** → 76.2 万聚合边；rustworkx 连通分量 0.35s |

**用法**：
- 重放：`python3 replay_duck.py --channels channels.json --out-dir data [--camps camps.json] [--emit-csv] [--mem-limit 8GB]`。通道 path 为**目录即自动走 v2 parquet**（run_*/logs.parquet+blocks join），文件走 v1 7 列 CSV；`--emit-csv` 产旧格式 merged.csv（对表/未迁移下游）。
- 缩图：`python3 cluster_prep_duck.py <chain> [--dir 工作目录 | --v2 <v2目录>]` → data/cluster_prep/ 三件（edges_agg/bal/profile 全整数 parquet）→ `python3 cluster.py <chain> --prep`。千万行以下 cluster.py 老路照旧。
- 长跑守护：`python3 scripts/run_guarded.py --name X --mem-ceiling-gb 12 --detach -- <命令>`（脱管+双内存水位+状态 JSON 原子写；替代裸 nohup，防沙箱连带清理与 OOM 假死）。
- **回归门禁（A1 纪律，硬性）**：动引擎/换库版本后必跑 ①`scripts/tests/run_all.py`（含 hypothesis 等价性测试+env_check 版本锁）②`scripts/bench/golden_baseline.py snapshot+compare` 对 ASTEROID 重跑对表。基线快照与对比口径见该脚本 docstring。

**DuckDB 1.5.4 实测坑清单（数字正确性级，逐条都踩过）**：
- **UHUGEINT 的 SUM 静默退化 DOUBLE**（返回 1e+32 的 float）——无符号 128 位不可用于聚合；用 **HUGEINT**（SUM 精确返 int，溢出硬报错不环绕，窗口 SUM 同）。
- **VARINT（=BIGNUM）乘法退化 DOUBLE**（`'2'::VARINT*'3'::VARINT` → DOUBLE）；加法/SUM 精确。VARINT 只作超 37 位十进制的 SUM 慢路径（~5x 慢），**任何乘法场景禁用**。
- **hex 字符串 cast 有位宽限制**：`'0xff'::UBIGINT` 可用，64-hex 全串 cast 任何整数型都报错——32 字节 value 用**两段法**：`('0x'||substr(data,35,16))::UBIGINT::HUGEINT * 2^64 + ('0x'||substr(data,51,16))::UBIGINT::HUGEINT`（前提高 32 hex 全零，物化前必探测，QUQ 28 位安全）。
- **hex cast 的位宽限制按目标类型而定，`HUGEINT` 比 `UBIGINT` 更严**（TOSHI 案补测，2026-07-26）：上条说的 `'0xff'::UBIGINT` 可用，但 **`'0x…'::HUGEINT` 一律报错**（`Could not convert string '0x00000046d1…' to INT128`），**截短到 24 hex 仍报错**——即"带 `0x` 前缀转 HUGEINT"这条路根本不通，别浪费时间试截长度。中等规模（≤ 千万行级）的省事解法：**DuckDB 只做过滤/投影，把 `data` 原样取回 Python 侧用 `int(d,16)` 转**（TOSHI 1660 万行 fetchmany(1e6) 分批处理，分钟级完成，内存可控）；亿级仍走上条两段 UBIGINT 法。
- **余额重放禁用浮点：float 累加会造出假的供给闭合残差**（TOSHI 案，2026-07-26）：以 `int(d,16)/1e18` 逐条累加 1660.9 万条后，重放正余额合计比 `totalSupply` 多 **181,938.49 枚**，一度被当成"漏采/重复事件"排查（外部复核也据此质疑重放逻辑有系统性缺陷）；改用**整数 raw units** 累加、最后一步才除 1e18，**全部余额代数和精确 = 0、非零地址代数和与 totalSupply 差 0.000000**。纪律：①对账口径一律用整数 raw；②报"闭合"时必须报**含负余额的代数和**而不是"正余额合计"——只报正余额会把负余额地址的缺口藏起来（该案确有一址重放 −181,938.49 而链上实查 +13.12，即约 18.2 万枚转入未被事件捕获，占供应 0.000043%，是真实数据缺口，需单列而非被浮点残差掩盖）。
- `make_timestamp()` 不吃 UBIGINT，参数先 `::BIGINT`；`day` 是保留字，列别名必须 `"day"`。
- **temp 磁盘是亿级聚合的真瓶颈**（非内存）：`SET max_temp_directory_size` 按十进制解析（40GB=37.2GiB）；(tx,li) 全局去重 shuffle 1 亿行需 >37GB temp——**v2 输入用块界感知去重**（per-run min/max 元数据秒查→仅重叠区间 GROUP BY，非重叠直通零 shuffle；QUQ 4 段零重叠 19.5s 完成）；派生表一律从 edges_agg 算（(f,t) 聚合保和），禁止对原始行做 (a,p) 双向 2 亿行聚合（首跑 46.5GB 爆仓教训）。
- 块末峰值窗口（PARTITION BY addr ORDER BY block 亿级）是最重一环——**3.19 已上两级候选预筛**（replay_duck 内置默认开）：一级=累计流入恒等上界（峰值≤Σ入账，不达 `peak_min×0.8` 者必不进 peaks），二级=正块净增更紧上界（峰值≤Σmax(dd,0)，同块进出抵消地址被精准滤掉）；两级全整数恒等推理只多收不漏收，精确窗口 SQL 逐字未动只缩输入集合，QUQ/ASTEROID 逐键全等实证。实测：QUQ 峰值段 657s→~330s（**2.0x**；刷量盘是最不利盘型——真达标 21,826 址刚性占 ab 45%，收益天花板 ~2.5x）；ASTEROID 常规盘型筛除 92.8% 地址。⚠**终态余额预筛不完备**（峰值高后清仓者终态=0 会漏），只有流量口径上界可用；HUGEINT SUM 溢出自动回退 VARINT 重算。新参数 `--no-merged`（亿级基准跑省盘）；`[peak]` 分段计时打印。峰值非必需场景（easy 初筛）仍可跳。
- **build_events 亿级全局宽键去重是当前真瓶颈（3.19 顺带发现，待修）**：QUQ v2 直读 1.03 亿行 temp 需求 >114.5GiB 本机三跑三败——而 v2 五 run 块段实测**零重叠**，全局去重对其是纯开销恒等映射（上表 QUQ "7.8min/8.1GB" 实为 events 层起算）。修复方向=build_events 引入块界感知去重（重叠区间才 GROUP BY，非重叠直通，同 cluster_prep_duck 既有做法）；巨分区（单址 1,443 万行）窗口 DuckDB 疑似串行，是预筛后剩余耗时大头。

**§12b 亿级流式重放（`replay_stream.py`，2026-07-25 收编）——上条"待修瓶颈"的现成出路**：
样本达**亿级、或可用磁盘不足样本体积 4 倍**时，replay_duck 的两次物化不可行，改走
`scripts/evm/replay_stream.py`：字段解码与产物口径逐字对齐 replay_duck，但**不物化任何中间表**，
直接对 parquet 流式聚合——hash aggregate 内存需求由"行数级"降到"唯一地址数级"。
实测 KOGE(BSC) **3.595 亿行 185 秒**完成（bal 55s/supply 20s/meta+inflow 63s/落盘 28s），
峰值内存 2.4GB、**temp 全程 0 字节**；同机 replay_duck 无法完成。
- **合法性前提＝去重可跳过，必须先验证**：`(block,tx,log_index)` 的 block 分量决定分段 →
  跨段不可能重复，故"把全块空间切 N 段逐段 GROUP BY 查重"**等价于全局查重但零 shuffle**
  （8 段扫 3.6 亿行 87 秒）。脚本内置 `--verify-dedup`（默认开），发现重复即 fail-closed 退回 replay_duck；
  通道块区间重叠同样直接拒跑。单 run 采集通常零重复，多 run 拼接/断点续拉过的必须验。
- 用法同 replay_duck：`--channels channels.json --out-dir data`；产物同名同格式（balances_final/
  mint_ledger/replay_stats/inflow/addr_meta/blockts.parquet），供给闭合挂同样 exit 4。
- ⚠**等价性回归待补**：尚未与 replay_duck 做黄金基准对表（KOGE 案无小样本基准）。首次用于新标的时，
  取一个 ≤200 万行块区间两引擎各跑一次、比对 balances_final/mint_ledger/supply 三键后再放量。
- **峰值不由它产**（亿级块末窗口同样爆盘）——配套 `peaks_daily.py`，见 §12c。
（来源：KOGE(BSC) 分析，2026-07-25）

**§12c 峰值日级两级口径（`peaks_daily.py`）——刷量盘块末窗口的替代件**：
块级 `(addr,block)` 聚合 + `PARTITION BY addr ORDER BY block` 窗口在刷量盘上是灾难：
KOGE 一级 inflow 预筛（≥0.1% 供应）后**仍剩 157,459 个候选**，块级 dd 表 3 分钟吃 19GB temp 直奔爆盘。
改日级后 6,217 候选 / 734,079 行 / **164 秒**完成。两级口径保证判级不失真：
`L1 日末峰值`（主口径）+ `L2 日内恒等上界 Σmax(day_delta,0)`（≥ 任意时刻真实峰值，全整数恒等）；
凡 L1 未达门槛但 L2 达标者落 `needs_block_precision.json`，对这批（通常个位数）再补块级精确值——**只多查不漏查**。
- **候选门槛按"判级需求"定，别照抄 0.1%**：恒等式保证峰值 ≥pct 的地址必在 `inflow ≥pct` 内，
  而判级实际只需 ≥1%（其他大户线）。KOGE 实测 ≥0.1% 有 131,833 址、**≥1% 只有 6,217 址，差 21 倍**。
- **附带收获**：产出的 daily_delta 同时就是阵营/实体日序列的原料，一举两得。
（来源：KOGE(BSC) 分析，2026-07-25）

**fail-closed 强化（新引擎内建，比旧引擎严）**：坏行 reject 记账（n_source_rows/n_bad_fields/n_out_of_segment/n_dedup_removed 进 stats）；同去重键不同事件内容=数据损坏硬退（旧引擎静默 keep-last）；空 ts 硬退（旧引擎归上一有效日的未定义行为）；供给闭合 gate 挂 → exit 4。同批修复旧引擎三缺口：replay_pass1 坏行计数+`--allow-bad-rows`（默认 0 即退）、cluster R1/准入阈值整数交叉乘法（曾浮点累计）、transfers_lib dedup 重组冲突检测（同 (block,tx,li) 双 hash 硬退,曾双计）。cluster 输出排序加确定性 tiebreaker（并列余额曾致同数据两跑输出不同）。

通用环境坑（macOS SSL 证书、reportlab 中文字体、前台 sleep 被 Block 等）不在本文重复，见 skill 其他参考文档与 memory（mac-python-pdf-environment.md、onchain-data-accounts.md）。
