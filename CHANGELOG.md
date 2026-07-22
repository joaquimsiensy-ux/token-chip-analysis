# CHANGELOG — token-chip-analysis（活跃窗口）

版本规则（v3.0 起两维制，详见 references/retrospective.md「版本号约定」）：
- **skill 版本**：主=架构级重构；次=每次**分析复盘**迭代 +1；修=文档小修
- **labels 数据版本**：标签库扩容/重建记 `labels vX.Y` 前缀条目，不再占用 skill 次版本号
红线：条目只记工具性知识（数据源/坑/方法/脚本），禁止记录任何代币的分析结论。
每条迭代条目附成本指标（轮次数/Bash 调用数/交付用时）+ 质量指标（初稿关键结论数/复核判定分布/漏检实体数/传播级数字错误数，v3.0 起，见 retrospective 步骤 1）。
**写入前必跑 `python3 scripts/tests/changelog_lint.py`**（防撞号/倒排——两者都实际发生过）。
本文件只保留最近 ~10 版（整编时滚动）；更早的完整迭代史在 `CHANGELOG-archive.md`，考古规则来源先 grep 该文件。

已知版本事故存档（保留原貌，不改写历史）：
- **2.21.0 重复 ×2**（2026-07-17 两个并行会话撞号：「标签库 v4.1」与「BEGGAR 复盘」各自 +1 —— git 化前无并发防护的实证；两条均保留原号，引用时注意区分）
- **2.24.0/2.25.0 曾物理倒排**（同日并行会话插入位置错位）——2026-07-18 稳定化时仅调整排列顺序，两条内容一字未动

## 版本索引（活跃窗口，新在上）
- **3.17.0 2026-07-22 GOAT(Solana) easy 二战复盘：长币龄混合重建工程加固+CEX 间调度商指纹**：Helius 大扫描 300s+gzip 通道（24.7 万账户 67MB 一次拉全，分片器降末位）/window_fetch gap 合并重复坑+负余额指纹/whale_deep cap 截断语义+10RPS 并发纪律/pump.fun 毕业迁移钱包入 address-book（发射窗峰值榜必剔）/编造地址 base58 侧五六犯；candidate 2 组（CEX 间库存调度商指纹 state-anomaly §9c+锚点复用两扫描 §11.3）；whale_deep 三参数悬账收编+scan_token_accounts --compressed/--timeout；easy 成本基准 GOAT 行（2-3h 档初步稳定）
- **3.16.0 2026-07-22 B 档五项收官：/collect-data 批量预采集+网络层异步化+复核 workflow 固化+Sourcify/DefiLlama 双通道+文件守卫 hook（非复盘专项）**：@CX 方案 B 档全部落地——新命令 /collect-data（collect_queue.py 多币串行队列，EVM 五链+Solana，manifest 记账/残缺 run 隔离/断点幂等，CAKE 296 万行+wSOL 缺口态+错址 fail-closed 三路实测）；net.py+rpc_batch.py 进程内异步替代 curl 子进程树（httpx+tenacity+msgspec，40 址与 curl 逐项等价）；adversarial-review 固化 workflow（schema 强制裁决 JSON+同批并行 fan-out，冒烟 2 路 100s）；Sourcify 合约身份批查（sourcify_check.py，v2 直连免 key，代理实现名一次拿到）；DefiLlama 老币历史价格主兜底（llama_price.py，CAKE 2020 起 2117 点全史实测）；guard_file_ops hook（Read 巨文件拦截+原始采集产物写保护，热加载实证）+PostCompact 提醒；HyperSync key 固化 ~/.config/hypersync/token
- **3.15.0 2026-07-22 QUQ(BSC) 完整版复盘+逢5轻整编**：公共基础设施先验三测（部署早于代币=强公共信号+同模板 code size 指纹——449e 大翻案教训）/寄存仓移仓指纹（监管点名对齐+3天原路等额往返）/净成本病态敏感双口径（正式：净额<毛额1%禁点估计,+剔自控镜像流第三口径）/bot 营运峰≠EOA 囤仓峰入 §9b 排代际/R2 备择解释路对结构性定性必设；快照缺块坑（供给闭合对缺整行免疫,done.json 前置第5查+负余额指纹）/手写地址第四犯工具化 real_addr/bscscan WebFetch 截断地址禁入产物/HyperSync v2 增量 4s+补丁段核验；整编：高扇出三判据两案转正、CEX 事件驱动做市纪律降档存档、5 条标疑、归档滚动 12+1 条（3.6.0 缺失正文补档）；D3 三大文档拆分推迟单独会话
- **3.14.0 2026-07-22 DuckDB 重放/缩图引擎三阶段落地（非复盘专项，@CX 交叉复核方案执行）**：亿级样本主路径换列式引擎——新件 7（replay_duck 合一引擎 v1CSV+v2parquet 双输入/cluster_prep_duck 缩图件+cluster --prep/golden_baseline 回归门禁/test_engine_equivalence hypothesis 性质测试/env_check 版本锁/run_guarded 长跑监督器/pyproject+requirements.lock 依赖锁）；等价实证=ASTEROID+SIREN 七项全等（含 merged.csv 逐字节）+QUQ 1.03 亿行三件逐键全等+聚类四类判定全等；性能=QUQ 核心重放 31s（原数十分钟）/缩图 19.5s 出 76 万聚合边/SIREN 7.1GB 守限（旧外推 19GB）；DuckDB 数字安全坑 6 条实测入 data-pipeline-evm §12（UHUGEINT SUM 退化 DOUBLE/VARINT 乘法退化/hex cast 位宽/temp 磁盘 GB-GiB/块界感知去重/窗口成本）；三缺口修复（pass1 坏行记账/cluster 阈值整数化/dedup 重组冲突检测）+排序确定化；changelog_lint 自动 hook 进 settings.json
- **3.13.0 2026-07-22 QUQ(BSC) easy 模式首战复盘**：币安 Alpha 场内 K 线端点（bapi alpha-trade/klines，374 天窗口**非全史**）+CMC 全史日线 EVM 侧二案复用；「接力库存仓」盘型入 state-anomaly §9b（主仓多代交棒直转·数十倍总量/净持≈0 执行枢纽网/「自持↔池↔CEX 场内」三态日轮转 30-50% 锯齿/量能市值数十倍倒挂——体系判定靠直转边不靠 gas，「独立做市商」备择每案独立走）；单 tick V3 NFT 头寸=零滑点自转刷量设施指纹；枢纽三段处理法（度>200 不作扩散桥/种子枢纽保留成员资格/NPM·EntryPoint·1inch 事后卫生检查强制收尾）；key_edges 设施边排除→来源拆解选择偏差（daily_delta 缺口法兜底）+亿级 edges 流式写；easy 首战成本基准单币 ~2.5h（采集 67min）
- **3.12.1 2026-07-21 公共数仓准入验证+BigQuery 复核通道正式化（非复盘专项）**：ASTEROID(ETH) 5 代表日 132,471 行三源对账——AWS v1.0/eth 与 BigQuery goog 官方版均与 HyperSync **逐行字节级等价**（键零差集/值零不一致）,"数仓质量≤HyperSync"疑虑在 ETH 段实证解除；分工定稿（用户拍板）：主力=HyperSync 不变、BigQuery=备用+出错复核源（新件 fetch_bigquery.py,仅 ETH,定向日期查询实测 12GiB/次推翻旧估 200-500GiB,免费 1TiB/月≈85 次复核）、AWS=等价但 pass（S3 无服务端过滤整分区下载 60 分钟,手工方法留档 §11 应急可复活,新鲜度实测 T+1~T+2 优于 sonarx T+7）；GCP 资产一次性开通（sandbox 项目+OAuth 缓存,api-keys.md 第 16 节;新账号 ToS 403 坑实测）；新源准入通用纪律定型（四型代表日+键值集合对账,禁品牌信任替代逐行对账）；data-pipeline-evm 新增 §11
- **3.12.0 2026-07-21 简化筛查模式 /token-easy-analysis + 图 1 价格右轴（非复盘专项）**：新命令+新分册 easy-workflow.md（E0–E7）——引擎与完整版同强度（采集/对账三查/深度关联全套/复核路数一分不减），砍背调（问 4 整路）与完整报告，交付两件套单页 HTML（图 1+按实体结构细分的阵营快照表+判定块含 Alpha 黑箱占比）+analysis-state.json 必落盘；绝不自动转正式，人工决策后 /token-analyze 同目录衔接（E7 继承清单+隔日增量拼接）；E6 复盘按需触发（有工具性增量才走全套）；场景=币安 Alpha/现货初筛 60+ 候选批量找高控盘标的，档 A 预估单币省 30-40%。standard_charts.plot_camp_evolution 新增 price_series 参数（右轴黑线白描边/量程>30x 自动对数/图例并轴单位/裁剪到阵营时间范围，demo+AKE 真数据双验证），完整版图 1 同步升级为必传，旧调用兼容
- **3.11.3 2026-07-21 Solana 采集加速工程（非复盘专项，@CX 三轮交叉复核）**：SQD 传输层真相实测（gzip=21 倍·明文是 §8"1.5-4x 实时"的真凶/限流 20req10s 长流碰不到·真瓶颈=单 IP 带宽整形 1MB/s·多 key 无意义/单响应解压 32MB 上限）；新件 2（fetch_sqd_transfers_v2 全程采集器：requests+自适应区域并发+全局令牌桶+gaps 重试,BONK 实测 639 slots/s=255 倍实时、三跑缺口自动收敛,2-6 个月币全程重放复活、§11 混合重建降级为 1 年+币龄专用 / decode_txs_v2 溯源：JSON-RPC batch+跨地址 sig 缓存+429 收回重试,mainnet-beta 方法级限流 ~10 笔窗实测,Helius 就位即切）；新通道 Solana HyperSync（隐藏 mint 服务端过滤实测——文档未载,`token_balances` 收 `mint` 键;单通道 623 打平 SQD 未达 3600 验收线,双引擎并行聚合 1211 有效叠加;fee_payer 指纹查询独有;滚动窗 196 天）；SQD gateway key 登记（公共端点不认证,专属端点待用户后台抄回）；data-pipeline-solana 新增 §13；成本：44 轮/约 60 Bash/2.5h；遗留 5 项见 §13 尾
- **3.11.2 2026-07-21 采集加速工程（非复盘专项）：HyperSync Starter 付费档+官方客户端 v2+多源对账闸门**：全量采集小时级→分钟级（SIREN 全史 21,689,815 条 18.8 分钟=19,265 条/s，vs 免费层当年 1568 万条 5.2h，同口径 23 倍）；新件 3（fetch_hypersync_v2 官方客户端 1 万条/s=18 倍付费单进程 / fetch_sqd_evm 免 key 对照源·SQD 无自助付费档 / transfers_lib 多源集合对账 fail-closed+block_hash 防重组去重键+部署块·锚点跨币缓存）；v1/par 付费参数化+8 列兼容；§1 决策树重写（v2 首选）；数仓 D/E 评估结论存档待准入（AWS bnb 无 logs·sonarx T+7 / BigQuery 无聚簇老币单查 200-500GiB / Dune 按 MB 计费大币不成立 / Solana HyperSync 滚动窗 ~196 天）
- **3.11.1 2026-07-21 销户账户覆盖审计（SQD 对账盲区加固，非复盘专项）**：data-pipeline-solana 新增 §12（GPA 快照只见存活账户→已 closeAccount 者的中间路径是"重放 vs 快照"对账天然盲区；mint 初始化史+tokenBalances=独立账户目录；sigs/blocks 双模式选路；slot+owner 判定粒度；undetermined 诚实纪律；退出码 gate 语义）+ 脚本收编 audit_closed_accounts.py（PUB 全程 93/93、USELESS 定向段 7/7 双案冒烟，SQD 销户覆盖首获专项验证）。来源：Helius vs SQD 采集通道 @CX 交叉复核，codex 反向审计法提议的工程化
- **3.11.0 2026-07-21 USELESS(Solana) 全量复盘：letsbonk 长币龄混合重建 + CEX 托管层指纹**：data-pipeline-solana 新增 §11 六件（混合重建演变架构·末日快照注入/SQD 高密度期 2000 slot 小段×8 并发/日级锚点观测边界·阴性依据禁用/publicnode 大扫描死角·mainnet-beta 静默空/whale_deep 按频分派/letsbonk 三件套）+§4 增 Vybe v4 top-holders（Solana CEX 标签荒最大补丁·余额虚高 113% 只用标签）/CMC data-api 全史日线/fapi fundingRate 500 条墙≠上线日/RugCheck knownAccounts 剔除表；方法 1 候选（CEX 提币囤仓的托管/储备层指纹组）+2 正式（同分钟批量出账伪影二见/发射窗"净拿>0"过滤禁令·闪电套利层）；脚本收编 3（window_fetch/anchor_sampler 参数化/scan_sharded 待验）；environment 增 heredoc 全角标点坑
- **3.10.0 2026-07-21 LPT(ETH+Arbitrum) 全量复盘：质押型代币首战**：data-pipeline-evm 新增 §10 质押型标的范式六件（权益=ERC20+bonded 合并口径·金库残差/账本状态机重放+事件自带总额校准锚点/已铸未领桶/TransferBond 暗道审计/L1→L2 迁移月双计坑/月度峰值口径）+§9 增量（HyperSync 同 key 多端点限流共享+二战数据点）+§4 三行（subgraph 前端 bundle 白嫖法/web3_sha3+openchain 事件签名正反解/Poloniex 老币早期价格）+§5 Burn 独立事件幽灵差额排查；supply-recon 增 CMC/CG 冻结快照必查（LPT 案低报 11%）；方法 4 条 candidate（高扇出≠服务商三判据/CEX 质押产品三件套/机构托管轮换链指纹/庄不成立呈现范式）+2 正式（月末快照天然原子化+脉冲月双报/落盘取值纪律扩至 topic0）；脚本收编 fetch_hypersync_logs.py（合约全事件版）
- 3.9.0 SQD(Arbitrum) | 3.8.x SIREN报告可读性+时区 | 3.7.0 AKE(BSC) | 3.6.0 SIREN(BSC) | 3.5.0 ASTEROID(ETH)+逢5整编
- 3.4.0 VIRTUAL(Base+ETH) 多链 | 3.3.0 体检修复 | 3.2.0 监控包按需化 | 3.1.0 成本三刀 | 3.0.0 稳定化
- 2.29.0 jesse(Base) | 2.28.0 哈基米(BSC)
- （3.9.0 及更早正文共 61 条 → CHANGELOG-archive.md，含 3.6.0 补档）

## [3.17.0] - 2026-07-22 — GOAT(Solana) easy 二战复盘：长币龄混合重建工程加固 + CEX 间调度商指纹

> retro 原料=GOAT分析/findings.md E6 素材清单（easy 交付后新会话执行）；用户批"全部写入"。Solana 侧 easy 首例：651 天 pump.fun 毕业币、7.6 万独立 owner、§11 混合重建全程实战。

**数据工程 5 条（正式）**：
- **Helius 大扫描通道打通**：24.7 万 token account / 67MB 响应，publicnode 恒 504、Helius 默认 120s 超时同样断——Helius + curl `--compressed`(gzip) + 300s 长超时一次拉全（§1 实测升级行 + §11.4 死角地图更新，scan_sharded 分片器降末位备选）；`scan_token_accounts.py` 加 `--timeout` 参数并内置 `--compressed`
- **window_fetch gap 段补拉合并纪律**（§11.2）：标 gap 的段仍写出部分数据，补拉后 cat 追加合并=9,212 行重复边；快查指纹=**重放负余额账户数暴增**（534→dedup 后 1）；正解=gap 段整段替换或全字段 dedup，两位数以上负余额先查重复再查通道
- **whale_deep cap 截断样本用途边界 + Helius 并发纪律**（§11.5）：签名史翻到 cap（2000 笔）即截断样本——起点非零禁从零累积持仓线，只作行为定性样本、时间线锚点/快照兜底；Helius 免费档 10 RPS 为账号级配额，多进程互抢反拖慢（5 进程实测单笔 decode 0.6-1.2s），正解=`--out` 分组并行+总并发贴限速
- **pump.fun→Raydium 官方毕业迁移钱包入 address-book**（`39azUYFW…jUJjg`）：毕业储备 2.069 亿枚 ≈20.7% 供应协议常数、Withdraw 指令数十秒过手——**发射窗重放峰值榜必剔**（GOAT 初稿误判"狙击集团 20.69%"被复核 REFUTED 的直接教训；§8.6 成本侧"迁移笔剔除"的实体识别侧补全）
- **编造地址第五六犯（base58 侧首发）**：funder 截断补全+基础设施地址拼写——evidence-wording 第 10 条适用范围明确为"一切链的完整地址字面量"，real_addr 反查纪律对 Solana 同样强制

**方法 candidate 2 组**：
- **【候选·单案】CEX 间库存调度商指纹**（state-anomaly 新 §9c）：零 DEX 交互（数百笔抽样解码）/精确定额轮发一所一线/凌晨日结节奏/多币种枢纽+闲置质押理财/双向大流量只报净向——P0 大仓的备择定性五判据，破"吸筹—拉盘—出货"框架硬套；配套"同类前例结局对照法"（锚点峰值普查出历史大仓名单→按画像匹配已离场同类作情景参照）
- **【候选·单案】锚点复用两扫描**（§11.3 + easy-workflow E3）：全 owner 峰值普查（≥1.5% 档，含已离场者）+ 全史前三涨跌日×锚点对照，零边际成本——GOAT 案完整性复核 4 条 must_add 有 3 条半源于缺这步

**脚本**：`whale_deep.py` --rpc/--proxy/--out 三参数收编（3.14.0 注记的他会话悬账，本条入库）；`scan_token_accounts.py` --compressed/--timeout；GOAT 案 `compose_evolution.py`（混合重建合成器）按红线 5 判标的专属件留工作目录存档，§11.1 注明"非复用件"

**easy 成本基准**：GOAT 行追加——Solana 长币龄混合重建与 BSC 亿级刷量盘同落 2-3h 档，单币基准初步稳定

**遗留**：①window_fetch gap 补拉替换/dedup 逻辑脚本化（本次仅入文档纪律）②Helius 300s 大扫描通道单案实证，下个大盘子 Solana 币复验③compose_evolution 通用化抽象④标的专属 TODO 4 条留 GOAT findings.md（E7 转正式时继承，不占 skill 条目）
**成本指标**：192 回合 / 139 Bash / 报告交付 2h06m（09:08→11:14，全程含 E6 素材沉淀 ~3h）
**质量指标**：初稿关键结论 ~16（判定块 4 直答+硬结论 12）；复核 4 路=1 CONFIRMED 加强 / 1 WEAKENED 定性改写 / 1 REFUTED 实体作废 + 审计 5 PASS·2 FAIL·3 WARN + 完整性 4 must_add 全采；漏检实体 3（离场庄三仓扩容、峰值 8.80% 历史大仓、4.73% 波段仓）；传播级数字错误 6（含发射窗统计重复合并 bug 修正）

## [3.16.0] - 2026-07-22 — B 档五项收官（非复盘专项，@CX 方案第二批）

> 3.14.0 三阶段（A 档+B6/B7/B9）交付后用户批"B 档也全部做"，其中 B12 附加三条需求：一个会话采集多币、专门命令 /collect-data、只采集不自动分析。本条为 B5/B8/B10/B11/B12 全部落地 + B7 补遗。

**B12 /collect-data 批量预采集（重头戏，用户三需求全兑现）**：
- 新件 `scripts/collect/collect_queue.py`：多币串行队列（HyperSync 限流 key 级共享+SQD 单 IP 带宽整形，串行是正解）——EVM 五链（bsc/eth/base/arbitrum/robinhood 走 fetch_hypersync_v2，部署块自动探测进全局缓存 deploy_blocks.json）+ Solana（fetch_sqd_transfers_v2，launch_ts 建议必给否则仅回看 90 天）；产物直接落 `<币名>分析/data/` 标准布局，分析会话零搬迁复用+断点续拉增量
- 行为契约：manifest（collect_manifest.json）逐项原子记账；残缺 run（无 done.json）改名 partial_run_* 隔离不删除（防污染下游 glob，遵守删除纪律）；单项失败不阻塞后续；退出码 0/2/1=全成/有缺口/有失败（按严重度 failed>gaps）；--resume 跳 done 项，不带也幂等
- 实测三路全过：CAKE(BSC) 早期 130 万块段 296 万行 220s（部署块 694452 自动探测）+ 幂等重跑 1.6s；wSOL 保险丝断开走 done_with_gaps 缺口注记；错误地址探测扫全链零命中 fail-closed 报"检查链路由"
- 新命令 `~/.claude/commands/collect-data.md`：解析多币清单→Solana 顺手查发射时间→生成 plan→run_guarded 脱管跑→只报采集事实不给结论；SKILL.md 阶段 1 + easy-workflow E1 加"预采集衔接"段（开工先查既有产物，禁从零重采）
- HyperSync Starter key 固化 `~/.config/hypersync/token`（chmod 600，长跑不挂进程列表；api-keys.md 第 1 节登记）

**B5 网络层进程内异步（买稳定性不是速度）**：新件 `scripts/lib/net.py`（httpx AsyncClient+异步令牌桶贴配额+tenacity 统一重试+msgspec 解析回退 stdlib；RpcPool 逐笔并发兼容 Helius 禁 batch）+首个消费者 `scripts/lib/rpc_batch.py`（批量 getCode 判 EOA/收据/任意方法 CLI，--browser-ua 治 robinhood WAF）；BSC publicnode 40 址实测与 curl 单发逐项等价、零失败（对照期 curl 裸发正好被瞬时抖动打中一次=重试价值的反证）；边界=CF/指纹敏感站点仍走 curl、在役老脚本不强改；三库进 pyproject+requirements.lock+env_check（14 关键依赖）；environment.md 沙箱节追加根治通道

**B8 对抗复核并行 fan-out 固化**：新件 `~/.claude/workflows/adversarial-review.js`（怀疑者×N+完整性批评同批并行、prompt 骨架内置、VERDICT schema 强制 JSON 输出根治坑表 #2、args 字符串化兼容层治坑表 #3——冒烟首跑就撞上该坑，兼容层实证必要）；冒烟 2 agent 100s：CONFIRMED 重算零偏差+完整性批评自发识破合成数据指纹；research-workflows §2 新增执行规范（同批并行=独立性正确形态/missing 非空必补跑/分歧以硬重算证据为准不投票）

**B10 Sourcify 合约身份批查（聚类前设施识别第三通道）**：新件 `scripts/labels/sourcify_check.py`——v2 API 国内直连免 key（0.2s 间隔 10 连发无 429），verified 合约名+代理实现名一次拿到（FiatTokenProxy→FiatTokenV2_2）；404=无源码≠EOA（判 EOA 仍用 getCode）；标的合约通用模板名（如 QUQ="Token"）本身即分析信号；⚠v1 批量端点 brownout 弃用至 2027-01 只走 v2 逐址；evm §4 入表+api-keys 免注册通道登记

**B11 DefiLlama 老币历史价格主兜底**：新件 `scripts/prices/llama_price.py`（series 分段拉 chart 端点全史日线单段 500 点上限自动分段/spot 批量单时点；输出与 CG market_chart 同构下游零改动；未收录 exit=3 别拿空当零价）；CAKE 2020-09 起 2117 点全史+2021-04 峰值 $42.46 抽查实测；CG 免费层 365 天墙的正解，Poloniex candles 降为其后备；evm §4 入表

**B7 补遗（守卫 hooks）**：新件 `scripts/hooks/guard_file_ops.py` 挂 settings.json PreToolUse——①Read 整读巨型数据文件拦截（二进制>1MB/文本>5MB，导向 duckdb 定向抽取）②Write/Edit 覆盖原始采集产物拦截（run_*/logs.parquet、soltx-* 只许采集器写）；pipe-test 四用例+本会话热加载实证（258MB parquet 当场被拦，顺带证明 settings watcher 对既有文件生效=3.14.0 遗留⑦翻篇）；PostCompact hook 注入"压缩后先重读落盘状态"提醒

**遗留**：①workflow 按名调用（Workflow({name})）不认 ~/.claude/workflows/ 用户全局目录（实测只列内置），须用 scriptPath 绝对路径——但 Skill 列表已识别其 meta，是否为加载时序问题下次会话验证 ②collect_queue 未覆盖 Hyperliquid/Filecoin（管道特殊用得少，遇到走原管道）③Solana 发射时间探测未自动化（命令层由 Claude 查填）④rpc_batch 尚无 nonce/traces 模式（按需加）
**成本指标**：~35 轮 / ~30 Bash / 约 1.5h；冒烟 workflow 2 agent 110k tokens；HyperSync 测试消耗 ~300 万行请求（Starter 档 <$0.5）

## [3.15.0] - 2026-07-22 — QUQ(BSC) 完整版复盘 + 逢5轻整编

> retro 原料=QUQ 分析目录 retro_notes.md（阶段 6 断点新会话执行）；用户批"全部写入 + 轻整编"（D1 归档滚动+D2 候选清点本次做，D3 文档拆分单独会话）。v3.13.0 已入 easy 首战复盘，本条为完整版增量。

**数据工程 4 条（正式）**：
- HyperSync v2 增量拉取实测（付费档 7 万块 2.3 万条 4s）+ 补丁段重叠核验法（补拉段落盘 patch 目录按 (tx,log_index) 键对比）→ evm §1；v2 parquet 资产做增量不走 pull_inc.py（面向 v1 CSV），直接 v2 新起 run → update-workflow U1
- **快照缺块坑**：重放跑在尾部采集完成前 → 快照缺尾部 ~980 块/682 条；**供给闭合恒等式对"缺整行"免疫**（借贷两边同缺、sum 恒=TOTAL 照过），只有 RPC 抽查负余额能暴露；对策=重放前 done.json 前置完整性检查（evm §5 新增第 5 查）；"期初 0 地址转出变负"=上游有洞指纹
- bscscan WebFetch 返回地址是省略号截断形态（`0xe096774F...BD5E2f603`），禁入任何产物 → evm §7.2
- 手写补全地址**第四犯**：纪律已有仍在脚本层再犯（camp 脚本首版 6 址 40-hex 中段凭记忆写入、equal 匹配全 miss 静默零输出）——工具化对策=脚本内 `real_addr(prefix)` 从落盘数据反查+断言唯一，代码禁手打 40 位字面量 → evidence-wording 第 10 条追加

**方法 5 条（1 正式 + 3 候选 + 1 注记）**：
- 【候选·单案】**公共基础设施先验三测**（getCode / 部署时间 vs 代币创建时间——早于代币=强公共信号（机制性子判据）/ 是否服务其他代币）+ 同模板合约对 code size 指纹 → entity-cluster §6。本次最大翻案来源：R2 复核据此 REFUTED"专属归集器"初判（1/9 项），主叙事"五代接力"整体改写为"bot 合约对+EOA 接力"两段式
- 【候选·单案】**寄存仓移仓指纹**（监管事件时点对齐 + 经枢纽收付 + ~3 天原路等额往返 = 移仓躲避非撤离；名单口径与实体维度分开表述）→ state-anomaly §7
- **净成本双口径与病态敏感声明（正式，机制=差分放大相对误差）**：净额<毛额 1% 禁报点估计浮盈；报"净成本≈0+现持市值"+近 90 天稳健口径；另算剔除体系自控镜像流后的"对外部实体真实交换"第三口径（QUQ 案镜像流占 91%）→ entity-cluster §6b
- 【候选·单案】**bot 合约瞬时峰≠EOA 囤仓峰**（合约 peak 是营运过手峰，排代际叙事时执行层/库存层分开）→ state-anomaly §9b 排代际纪律 + 枢纽定性引三测
- R2 型（备择解释）怀疑者对"归集器/枢纽/主仓"类结构性定性必设一路：REFUTED 计数低≠收益低，单条可重写主叙事 → evidence-wording 强度配置注记

**逢5轻整编（D1+D2；D3 推迟）**：
- **候选清点（21 条）**：转正 1——"高扇出≠公共服务商"三判据（LPT+QUQ 两案，§146 预告的合并兑现，标记改【正式·两案】）；降档 1——"CEX 上线事件驱动做市商身份判定纪律"（VIRTUAL 2026-07-18 入库超 8 版无第二案，正文删除、全文存档见下）；标疑 5——公共代买枢纽四特征 / 非关联组双口径 / 锁仓池动态性复核 / 世代阵营划分法 / 死币复活亚型分流（各附保留理由行内注记，下次整编复审）；其余 14 条未超版保留
- **归档滚动**：3.9.0~2.28.0 共 12 条正文移入 CHANGELOG-archive.md；**3.6.0 正文条目历史缺失**（并行会话时期只写了索引行）以索引行内容补档入 archive，版本序恢复完整；活跃索引区同步压缩
- **降档存档【CEX 上线事件驱动做市商的身份判定纪律】原文**：多地址在某 CEX 上线公告后、开盘前窗口集体激活并高频作业，只构成事件驱动型做市实体；"受该 CEX 委托做市"必须另查其全部流水与该 CEX 全部已标注钱包（热/冷/托管）的直接往来笔数——零直接往来时委托关系"不能确认也不能排除"，降级表述并把独立高频商作同等备择并列；上线时间强相关是行为证据不是身份证据（来源：VIRTUAL(Base+ETH) 多链分析，2026-07-18；3.15.0 整编降档，异案复现即复活）
- **D3 遗留（单独会话执行）**：data-pipeline-evm ~76KB / playbook-entity-cluster ~78KB / data-pipeline-solana ~65KB 三份超 60KB 整编线待主题拆分（拆分纪律=先冻结规则清单再逐条迁移核对，禁凭印象重写）

**质量 4 指标**：初稿关键结论 ~20（TL;DR 四问+特有 6）；复核判定 CONFIRMED 多数 / WEAKENED 1（净成本表述）/ REFUTED 1（449e 定性，连带改写体系叙事）；漏检 4 处全吸收（R5 完整性路抓出：寄存仓层/Alpha 搬运腿/V4 刷量环/沉睡大户）；传播级数字错误 0（R3 审计 7+13 项零误差；口径修正 3：215 址/毛净混淆/48.81% 口径）；另记数据洞 1（快照缺块，修复后全量重跑）
**成本 3 指标**：上下文峰值 ~33 万（超 30 万参考线，原因如实=重放修复+R2 大翻案连续作业、断点不划算）；子代理背调 4 + 复核 5 全后台并行；轮次/Bash 数未记录
**遗留**：QUQ 标的专属深挖 TODO 6 条留分析目录 retro_notes.md §五（下次 /token-update 取用）；本次脚本全为工作目录私有薄壳，无收编项

## [3.14.0] - 2026-07-22 — DuckDB 重放/缩图引擎三阶段落地（非复盘专项）

> 起因：用户问"筹码分析有什么优化建议"，@CX 交叉复核（codex 读代码后指出真瓶颈=亿级数据反复装进 Python 对象层，非采集/网络），融合方案获批后按"基线→改造→对表→亿级实测→监督器/依赖锁/hooks"三阶段执行。全程纪律：先建可证明等价的基线，再做任何优化——"快了但数字错了"是本工作流最贵的事故。

**新工程件 7**：
- **replay_duck.py**（scripts/evm）：pass1+pass2 合一列式引擎，v1 7列 CSV 与 v2 parquet 目录双输入自适应；`--emit-csv` 逐字节复刻旧 merged.csv；uint256 策略=≤37 位 HUGEINT 快路径/超界 VARINT 慢路径全程无浮点；reject 记账+同键异值硬退+空 ts 硬退（比旧引擎严）。
- **cluster_prep_duck.py**（scripts/evm）：亿级明细→edges_agg/bal/profile 三件全整数聚合 parquet；v2 输入块界感知去重（per-run 元数据定重叠区间，仅重叠段 shuffle）；派生表全部从 edges_agg 算（(f,t) 聚合保和）。
- **cluster.py --prep 模式**：四容器内存装载改读缩图件，判定语义零变化（ASTEROID 沙盘四类判定产物全等）；gatekeeper 新增 scan_profiles 聚合底数入口（浮点派生表达式与 funnel_profile 逐条同构）。
- **golden_baseline.py**（scripts/bench 新目录）：产物规范化指纹 snapshot/compare，stats 按 8 契约键判等（引擎扩展字段忽略）。
- **test_engine_equivalence.py**：hypothesis 随机边角数据（mint/burn/自转/同块多事件/零值/38+ 位大值/负余额盘）双引擎对表，进 run_all 全家桶。
- **env_check.py + pyproject.toml + requirements.lock**（A4 依赖锁）：关键 11 依赖版本冻结+全家桶内校验；刻意不用 venv（保住"系统 python3 直接跑"的全部既有入口），升级流程=先全家桶+基线对表再更新 lock。
- **run_guarded.py**（scripts/）：长跑监督器——脱管+任务树 RSS 上限+系统可用内存下限双水位+状态 JSON 原子写；替代裸 nohup。

**等价实证与性能**（细节与验收口径=data-pipeline-evm 新 §12）：ASTEROID 140 万行/SIREN 2169 万行三通道与旧引擎七项全等（含 merged.csv 逐字节哈希）；QUQ 1.03 亿行与 replay_pass1_quq 原产物 stats 11 键+balances 51,871 址+daily_delta 196 万键逐键逐值全等，peaks 两口径不变量零违例；性能=QUQ 核心重放 31s、缩图 19.5s/1.35GB 出 76.2 万聚合边（rustworkx 连通分量 0.35s——"先缩图再换库"实证：缩图后图算法不再是瓶颈，纯 UF 亦亚秒）、SIREN 峰值 7.1GB 守 8GB 限（旧引擎外推 ~19GB 不可行）。

**旧引擎三缺口修复（fail-closed）**：①replay_pass1 解析异常静默 continue→坏行计数+样本+默认即退（--allow-bad-rows 显式放行）；②cluster R1 边阈值/集群准入浮点累计→整数交叉乘法（0.005%=1/20000、0.01%=1/10000 精确等价）；③transfers_lib dedup 主键统一 (block,tx,log_index)+重组冲突（同键双 hash）硬退——曾双计。另修 cluster 输出排序非确定性（并列余额+set 迭代序→加 addr tiebreaker）。修复后 ASTEROID 重跑与基线 7 项全等（合法输入行为不变实证）。

**DuckDB 1.5.4 数字安全坑 6 条（全部实测踩出,§12 详表）**：UHUGEINT SUM 静默退化 DOUBLE / VARINT 乘法退化 DOUBLE（仅加法/SUM 精确）/ hex cast 位宽限制（32 字节 value 两段 HUGEINT 法）/ make_timestamp 不吃 UBIGINT+day 保留字 / temp 磁盘为亿级真瓶颈（max_temp_directory_size 十进制解析,全局 (tx,li) 去重 1 亿行需 >37GB→块界感知去重）/ 亿级窗口峰值 432s 为最重一环（easy 场景可跳）。

**自动化**：~/.claude/settings.json 新增 PostToolUse hook——Edit/Write 命中本仓库 CHANGELOG.md 后自动跑 changelog_lint，FAIL 时 exit 2 阻断反馈（撞号/倒排两次实际事故的制度化防线；若配置当次会话未热加载,重启后生效）。

**遗留（下次验收/优化点）**：①块末峰值窗口 432s 待优化（先按终态/流量粗筛候选再窗口）；②v2 输入超 127bit value 的 UDF 十进制慢路径未实现（触发即硬退提示,常规币不会触发）；③data-pipeline-evm 69.8KB→本条后更超 60KB 整编线（下次整编拆分）；④equivalence 测试未覆盖多通道段拼接（SIREN 实数据已覆盖）；⑤pueue 队列工具未装（夜间批量采集队列场景按需 brew install pueue,run_guarded 已覆盖单任务守护）。

成本指标：轮次 ~70 / Bash 调用 ~55 / 交付约 3.5h（含 QUQ 亿级三跑与两次 temp 爆仓排障）。质量指标：对表 FAIL 后翻案 0（全部一次通过或定位为口径/展示差异）；hypothesis 10 例边角全过；性能回归门禁（run_all 6/6 + env_check）全绿。

## [3.13.0] - 2026-07-22 — QUQ(BSC) easy 模式首战复盘

> easy 模式（/token-easy-analysis，v3.12.0 新增）首个实战标的：four.meme 发射、币安 Alpha 在架的亿级转账刷量盘（1.03 亿条 Transfer，HyperSync v2 付费档 67 分钟采完，对账三查全过）。E0–E6 全流程走通，两件套交付。复盘在轻上下文新会话执行（成本纪律刀 2 第 6 条）。

**新数据源 2（数据工程，直接正式）→ data-pipeline-evm §4**：
- **币安 Alpha 场内 K 线**：`www.binance.com/bapi/defi/v1/public/alpha-trade/klines?symbol=ALPHA_{alphaId}USDT&interval=1d`——Alpha 黑箱唯一的场内量价直查通道（标准币安 12 列 K 线含 trades 笔数，bapi 信封）；⚠实测单次返回 374 天且首行晚于上架日（窗口/limit 上限，翻页未测）——**非全史**，更早段配 CMC 全史日线补。
- **CMC data-api 全史日线 EVM 侧二案复用**：USELESS(Solana) 首测（437 点）后 QUQ(BSC) 复用 488 点全覆盖——跨链通用兜底地位确认，EVM §4 补行与 solana §4 互引。

**新盘型 1（候选·单案）→ state-anomaly 新 §9b「接力库存仓（Alpha 刷量盘）」**：库存=做量原料非待派发筹码，按吸筹/派发框架解读会错判。四指纹：①主仓多代接力+交棒直转（换代互转达总量数十倍、单笔数十% 整仓移交）②净持≈0 执行枢纽网（与主仓百万笔级互转）③「自持↔DEX 池↔CEX 场内托管」三态日轮转 30-50% 总量（日度曲线同步锯齿=真实倒仓非毛刺）④量能/市值数十倍倒挂。纪律：体系判定靠交棒直转边**不靠 gas**（各代 funder 独立=钱包卫生干净不构成反证）；「独立第三方做市商」备择每案必须独立走；CEX 托管曲线大幅波动属此盘型常规操作，单独看会误报"进所出货"。

**新指纹 1（候选·单案）→ state-anomaly §9**：**单 tick V3 NFT 头寸=零滑点自转刷量设施**——最窄 tick 区间（tickLower/tickUpper 差一个 tickSpacing）的集中流动性=自转特制场地；NonfungiblePositionManager positions() 查区间宽度；GoPlus lp_holders 报单址 99.9%+ 时先辨池版本（V3/V4 LP 是 NFT 非 ERC20）。

**聚类方法 1（候选·单案）→ entity-cluster §6**：**枢纽三段处理法**——①度>200 不作扩散桥（既有剔除规则的 BFS 执行形态）②种子枢纽保留成员资格（剔边不剔身份；为 LPT"高扇出≠公共服务商"三判据的第二案方向印证，整编时合并裁决）③事后公共合约卫生检查强制收尾（NPM/EntryPoint/1inch 等；QUQ 案复核剥离 34 址执行通道、现仓影响仅 0.04%）。

**工程坑 2 → data-pipeline-evm §6**：①key_edges 提取排除设施边→来源拆解**选择偏差**（刷量盘大头恰经池/枢纽走），daily_delta 缺口法兜底；②亿级 edges 提取禁攒内存，流式 append 落盘（7.3GB 实证）。

**easy 首战成本基准 → easy-workflow.md 新节**：单币全程 ~2.5h（采集 67min 占大头），亿级刷量盘属重型样本、普通量级预期显著更短。

成本指标：交付 ~2.5h（采集 67min）；轮次/Bash 计数未导出（分析会话与复盘会话分离，原会话未记录）。质量指标：初稿关键结论 9；对抗复核 4 路=3 CONFIRMED + 1 备择解释 REFUTED（主结论存活），实质修正 5（1 归属翻案：首日大买家独立大户→项目方关联分配仓 / 1 证据降档 / 1 成员剥离 34 址 / 2 措辞补证）；复核翻出漏检 P0/P1 实体 0；传播级数字错误 0。

另：本次 git 收口 3.12.0/3.12.1 两会话的未提交悬账（先补 commit 纯 3.12.x 文件，共享文件随本条 commit 进库——见 git log）。

## [3.12.1] - 2026-07-21 — 公共数仓准入验证 + BigQuery 复核通道正式化（非复盘专项）

> 起因：v3.11.2 数仓 D/E 评估后用户挂起待验证（"找已分析币看数据是否完全一致,检验过后再决定"）。本次用 ASTEROID(ETH,22 个月史,140 万条) 抽 5 代表日执行分区级准入,验证全过后用户拍板分工。全程未动采集主力选型。

**准入实证（当日实测）**：
- **抽样设计**：部署日 2024-09-10(创世+发射窗 14,447)/低活日 2025-01-03(47)/极稀日 2025-03-01(全天 1 条,阴性边界)/峰值日 2026-04-19(Musk 事件 114,010,压力面)/近期日 2026-07-17(3,966,新鲜度面),合计 132,471 行。
- **双仓皆 PASS**：AWS v1.0/eth raw logs 自解码与 BigQuery goog 官方版 raw logs 自解码,均与本地 HyperSync 基准**逐行字节级等价**——键 (block,tx,log_index) 零差集、值 (from,to,value) 零不一致。传递性下 AWS=BigQuery 亦等价。
- **成本实测**：BigQuery 定向查询(按币活跃日限日期分区)仅扫 12.0 GiB——**推翻 v3.11.2 存档的"老币单查 200-500GiB"悲观估算**(那是无日期限定的全表扫口径),免费 1TiB/月≈85 次复核;AWS 侧 4.9GB/60 分钟(瓶颈=用户宽带 1.7MB/s;S3 无服务端过滤,单币复核也须整分区下载,99%+ 流量为无关合约数据)。
- **AWS 新鲜度实测 T+1~T+2**(07-21 已见 07-19 分区),优于 sonarx base/arbitrum 的 T+7——修正 v3.11.2"官方宣称日更不成立"仅适用 sonarx 表的边界。

**分工定稿（用户 2026-07-21 拍板）**：采集主力=HyperSync Starter+v2 不变;**BigQuery=备用+出错复核源**;**AWS=已验证等价但 pass**(太慢),不做采集器、手工方法留档应急。BSC 对照源仍只有 SQD(两仓均不覆盖 BSC,格局未变);Base sonarx 未做准入。

**新件与文档**：
- **fetch_bigquery.py**(scripts/evm 第 12 件)：goog 官方数据集薄采集器——参数化(config bigquery 节+--dates/--from-date)、强制日期条件(防全史扫爆额度)、dry run 熔断(max_scan_gib 默认 200GiB)、输出与 fetch_sqd_evm 同款标准 8 列、对账走 transfers_lib merge;冒烟=2 日 48 行与基准六字段全等、凭据缓存零弹窗。
- **data-pipeline-evm §11 新节**：准入实证数字/分工定稿/BigQuery 操作要点(raw logs 自解码禁 token_transfers 表-跨仓通用/ToS 403 坑:新 Google 账号必须网页接受条款否则 API 建项目 403 `Callers must accept Terms of Service`)/AWS 手工方法留档(匿名桶列目录+逐 row-group 选列过滤)/**新源准入通用纪律**(四型代表日+键值集合对账全等才准入,禁止品牌信任替代逐行对账);§1 决策树+通道表各加 BigQuery 行。
- **GCP 资产开通并登记 api-keys.md 第 16 节**：sandbox 项目 chip-recon-77201(免绑卡)+OAuth 凭据缓存 ~/.cache/pydata_google_auth/(scope=cloud-platform,复用免弹窗)。

成本指标：轮次 ~12 / Bash 调用 ~20 / 交付约 2h(含 60 分钟 AWS 下载挂机与用户 OAuth/ToS 两次搭手)。质量指标：非复盘条目按修号+1(3.12.0→3.12.1,并行会话已占 3.11.3/3.12.0,写前重读索引防撞号);冒烟发现 0 缺陷;本次验证脚本自身的负面路径(ToS 403/项目创建假成功)均实测记档。

## [3.12.0] - 2026-07-21 — 简化筛查模式 /token-easy-analysis + 图 1 价格右轴（非复盘专项）

> 起因：用户从 SIREN 受启发做"币安系高流通候选"初筛（60+ 币），逐个完整分析成本不可行，需要筛查档位。方案讨论三轮定档 A：深度关联与对抗复核用户点名不可省（怕漏伪装分散庄），砍背调与完整报告（省 30-40%）；HyperSync Starter 付费后采集退出瓶颈位。开工时 skill v3.11.3。

**新增**：
- **命令 `/token-easy-analysis`** + 分册 `references/easy-workflow.md`（E0–E7）：E0=完整版阶段 0 原样（初筛清单地址可采信但多链硬关卡不可跳）；E1 三路采集砍背调路（不碰 Firecrawl/推特，问 4 以局限声明代之）；E2 三查原样；E3 引擎同强度（阵营表按实体结构细分粒度不降；Alpha 在架必算黑箱占比进判定块）；E4 复核路数不减、复核面自然缩；E5 两件套单页 HTML（图 1 必传价格+阵营快照表+判定块 3–5 行+局限声明）+ analysis-state.json 必落盘 + 工作目录沿用 `<代币>分析/` 转正式零搬迁；E6 复盘按需（有工具性增量走全套，无增量一行收）；E7 转正式衔接（同次产物直接继承免"沿用须检验"，隔日以上先按 U1 增量拼接；已 CONFIRMED 项不重跑复核）
- **standard_charts.plot_camp_evolution 新增 `price_series` 可选参数**（2026-07-21 用户定"价格+筹码对照"）：右轴价格黑线（白描边，堆叠色块上唯一不撞色组合）；默认线性对齐图 2 直觉，量程 max/min > PRICE_LOG_SWITCH_RATIO(30) 自动切对数；单位并入图例条目（右轴 ylabel 与外置图例同位会重叠，实测踩过）；图例 x 锚 1.01→1.075 给右轴刻度让位（线性轴多位小数刻度会被压住，实测踩过）；价格序列自动裁剪到阵营时间范围防 x 轴撑出堆叠区。demo 合成数据 + AKE 真实数据（13.6x 线性档）双验证通过。**完整版图 1 同步升级为必传**（report-template 三张标准图表格已改），不传保持纯占比图（旧报告基线重绘兼容）
- SKILL.md 新增「简化筛查模式」节 + 分册清单行；build_html.py 零改动（质检本就是"md 引用什么检什么"，单图天然兼容）

**纪律边界**：一币一会话铁律不变，跨币汇总矩阵不进分析会话（用户在独立轻会话用各币 analysis-state.json 纯机械拼表）；判定块只给参考意见绝不自动转正式。

## [3.11.3] - 2026-07-21 — Solana 采集加速工程：SQD v2 采集器 + 溯源批量化 + Solana HyperSync 通道（非复盘专项）

> 起因：3.11.2 解决 EVM 侧后，Solana 侧同题（§8 实测 SQD 单流 1.5-4x 实时→全程重放不可行→§11 混合重建凑合）。@CX 交叉复核后用户拍板方案 1/2/3/5（方案 4 实时档案暂缓）。最大翻案：**"SQD 慢"的真凶是明文传输**——v1/window_fetch 的 curl 全没开压缩，gzip 同段对照 21 倍（4.65→98 slots/s）。开工时 skill v3.11.2。

**通道/坑（全部当日实测，详见 data-pipeline-solana §13）**：
- **SQD 传输层三个数字**：gzip=21 倍；限流 20req/10s 长流碰不到（串行 30 请求 0 429、8 路并发全 200），真瓶颈=单 IP 带宽整形 ~1MB/s（3 路≈8 路聚合——**多注册 key 无意义**，用户问过此路）；单响应解压 ~32MB 上限按最后 slot 续拉即可（v1 50K 段超时死循环=明文 150s 传不完一响应，压缩后自愈）
- **fetch_sqd_transfers_v2.py**（scripts/solana 新件，全程重放主力）：requests.Session（自动 gzip+连接复用）+自适应区域并发（全局段队列动态领取、区域 1 万-100 万 slot 按耗时伸缩）+全局令牌桶（默认 4rps；1.6 在高密度段顶死请求数的教训）+gaps 重试 2 轮后继续（修 v1"首个未完段后整体丢弃"）。BONK 实测 40 万 slot+22.3 万边三跑 ~11 分钟缺口自动收敛，稳态 639 slots/s=**255 倍实时**（对照 window_fetch 同类 82 分钟→约 7 倍）——**2-6 个月币全程重放复活（数小时级），§11 混合重建降级为 1 年+币龄专用**。冒烟抓 2 个并发 bug（按空洞分配首扫并发恒 1→全局段队列；初始单段 6 worker 扑空 5 个退出→在飞计数等待）
- **decode_txs_v2.py**（scripts/solana 新件，溯源三板斧）：JSON-RPC batch+跨地址 sig 缓存（256 片；实测 18/40 命中零请求——关联地址重复交易极多）+429 子请求收回重试（首测 22/40 假失败的 bug 教训）。**mainnet-beta 硬墙实测：batch 子请求按方法逐个限流**（"Too many requests for a specific RPC call"，20 笔放行 ~9）→batch 默认 8、公共节点净提速仅 ~1.5 倍；真价值=缓存+Helius 就位即切（--rpc 参数）。Helius 注册待用户搭手（Google OAuth 需真实浏览器；纯邮箱 07-09 被 bot 拒 2 次勿盲试；只注册免费层用于溯源——付费档"不买"决策见 3.11.2 不变）
- **Solana HyperSync 通道开通**（solana.hypersync.xyz，early access，现役付费 key 直用）：**实测发现文档未载的 mint 服务端过滤**（`token_balances` 收 `mint` 键，字段 slot/mint/owner/account/pre_amount/post_amount/transaction_index 与 SQD 同构直喂 pair_tx）；响应结构顶层数组（无 EVM 的 data 包裹）、游标 next_slot。吞吐：单通道 623 slots/s 打平 SQD（"读取后过滤"型），未达 3600 验收线；**双通道同跑聚合 1,211≈两倍——并行分段有效叠加**；fee_payer 服务端过滤=SQD 没有的洗仓指纹查询。滚动窗 slot 391.79M 起 ≈196 天，窗外老币无效；mint 过滤 pre/post 语义（关户行）未验收
- **SQD gateway key 登记**（api-keys.md 第 14 节，~/.config/sqd/api-key）：公共 datasets 路径完全不认证（真假 key 全 200，Bearer/X-API-Key/query 三形态无差别）——专属端点 URL 待用户从 portal.sqd.dev/app 后台 key 详情页抄回

成本指标：轮次 ~44 / Bash 调用 ~60 / 交付约 2.5h（不含评估轮）。质量指标：v2 三跑缺口收敛+输出与 v1 逐字段同构验证；decode v2 40 签名 fail=0+缓存命中验证；POC 双通道对照实验定量（623/639/1211 三数字）；遗留 5 项显式记录（§13 尾）。

## [3.11.2] - 2026-07-21 — 采集加速工程：HyperSync Starter 付费档 + 官方客户端 v2 + 多源对账闸门（非复盘专项）

> 起因：采集全量转账事件占全流程时间大头，用户决策付费提速。评估期与 codex 三轮 @CX 交叉复核（加速方案全景 / 数仓一致性三问 / Helius·SQD 付费选型纠偏），最终选型：EVM=HyperSync Starter（$70/月）+官方客户端；SOL=维持 SQD Portal 免费层（Helius 不买——"按 mint 拉全量转账"在 Solana 结构性不存在，50RPS 凑等价结果一个中型币要 17h+烧光月额；Solana HyperSync 已上线 early access 但滚动窗仅 ~196 天）；AWS/BigQuery 数仓（D/E）暂缓，待用户抽已分析币做分区级准入验证。开工时 skill v3.11.1。

**通道/坑（全部当日实测）**：
- **HyperSync Starter 付费档接入**（key 登记 api-keys.md 第 1 节；100rpm 基础+overage 5x=500rpm，超量按请求计费单币 <$1）：0.12s 间隔 **429=0**（免费层同参数 173 次/时级腰斩）；但 v1 手写轮询单进程吞吐仅 552-792 条/s（ETH RTT~0.2s / BSC RTT~0.6s）——**付费买到的是限速层解除与高峰稳定性，吞吐瓶颈=RTT×串行等待，解药=官方客户端自动并发**（付费不换客户端只吃到零头）
- **fetch_hypersync_v2.py 官方客户端采集器**（scripts/evm 新件；`pip install hypersync`，Rust 内核自动并发+Parquet 直写，concurrency=10 默认；url 用裸域名不带 /query；断点=run_*/done.json 记 next_block）：CAKE 90,719 行/9s=**10,080 条/s**（18 倍于付费 v1 单进程）；**SIREN 全史 21,689,815 条 1126s=18.8 分钟**（19,265 条/s；vs 免费层当年 1568 万条 5.2h，同口径 **23 倍**；行数落在当时估算 22.6M/上限 25M 区间内）
- **fetch_sqd_evm.py SQD Portal 薄采集器**（scripts/evm 新件；免 key，公共限流 20 请求/10s，实测 280 条/s）：定位=HyperSync 平台级故障预案+数仓切源准入对照源，平时不跑；SQD Portal **无自助付费档**（官网 "pricing coming soon"，2026-07-21 核实——想付费也没有产品可买）
- **transfers_lib.py 多源对账闸门**（scripts/evm 新件，M 工程件核心）：标准 8 列含 block_hash，去重键 (block_hash,tx,log_index) 防链重组；merge_sources 两两重叠块区**集合级对账，不等即 exit(3) fail-closed**（PING 案跨源 uniqueId 双计 5485 负余额事故的制度化防线；负面测试：故意删 1 行被精确指认 tx+log_index）；**三源交叉实测 SQD×v1×v2 同区间逐行一致**；配套 ~/.cache/chip-analysis/ 部署块缓存 get_deploy_block + 时间戳锚点库 add_anchors/estimate_ts 跨币复用（发射窗精确配价仍禁用插值）
- v1/par 付费参数化+block_hash 列：新文件 8 列（尾列 block_hash），老 7 列文件续拉自动维持老格式（表头探测）；par 版 sleep 配置化，付费档全局请求率 workers×(1/sleep)≤8/s，超了只会互相挤兑
- **数仓 D/E 评估结论存档**（暂缓实施，待准入）：AWS 公共数据湖 v1.0/eth 有 token_transfers+logs（⚠token_transfers 有浮点精度事故公开报告，只可走 raw logs 自解码）、sonarx base/arbitrum 表**实测滞后 T+7**（官方宣称日更不成立）、**bnb 只有 blocks+transactions 无 logs**（BSC 走不通）；BigQuery 无 BSC/Base、goog 官方版 ETH 滞后 12-15 分钟、token_transfers 无 token_address 聚簇（老币单查扫 200-500GiB，免费 1TiB/月仅够 2-5 次，超量 $6.25/TiB 便宜但需绑卡）；Dune 2026-04 起按导出 MB 计费（Free 20cr/MB·2500cr/月≈3-5 个 10 万行小币，千万行大币成本结构不成立——**BSC 大币正解=HyperSync 付费而非 Dune 付费**）

成本指标：轮次 ~28 / Bash 调用 ~40 / 交付约 2h（不含前三轮评估会话）。质量指标：非复盘条目按修号 +1（3.11.1 先例）；POC 三组验收（条/秒、429=0、同区间逐行 diff=0）全过；fail-closed 负面测试通过；SIREN 全史行数与当时估算闭合。

## [3.11.1] - 2026-07-21 — 销户账户覆盖审计：SQD 边集对账盲区加固（非复盘专项）

> 起因：评估 Helius 付费通道时经 @CX 交叉复核确认"按 mint 拉全量转账"在 Solana RPC 层不存在（普通 Transfer 指令不引用 mint），连带发现现行对账体系的结构性盲区——GPA 快照只见存活账户，已 closeAccount 销户者（bot/中转/洗仓的常态收尾）若被采集通道漏边，"重放 vs 快照"对账看不见（关闭前必归零，期末供给照样闭合）。codex 第二意见提议的反向审计法当日工程化落地。开工时 skill v3.11.0。

- **data-pipeline-solana §12 新节**：盲区原理 / 独立发现源（初始化指令必引 mint + pre/postTokenBalances 自带 mint·owner，双通道并集收集器——tokenBalances 通道产率高一个量级）/ sigs·blocks 双模式（--mode auto 3 页探路未进区间自动切 blocks；历史定向段边集签名史新→老翻页到不了区间，正解=区间内 getBlock 整块提取）/ slot+owner 判定粒度声明（SQD 边无 sig 字段）/ **undetermined 诚实纪律**（深挖账户 all_zero_delta·fetch_failed 分类="没查出来"≠"没事件"，不构成"无漏"证据，过半自动告警）/ 退出码 gate 语义（0 零漏边·2 发现漏边·1 失败）/ 定位=阶段 2 三查后例行抽查项（非硬 gate，missing 才升级堵漏）
- **脚本收编 audit_closed_accounts.py**（scripts/solana 第 22 件）
- **首轮实证**：PUB 全程边集 93/93 全覆盖（sigs 模式）、USELESS 定向段区间内 7/7（blocks 模式，14 事件 out_of_range 正确跳过）——SQD 通道销户覆盖首次获得专项验证；冒烟自身抓出两处设计修正（定向段翻页不可达 → blocks 模式；深挖零事件静默当"无事件" → undetermined 分类）

成本指标：轮次 ~14 / Bash 调用 ~11 / 交付约 1.5h（含双案冒烟与两轮设计修正）。质量指标：非复盘条目按修号 +1（次号保留给分析复盘，依版本规则）；冒烟发现设计缺陷 2 处、交付前全部修复。

## [3.11.0] - 2026-07-21 — USELESS(Solana) 全量复盘：letsbonk 长币龄标的混合重建 + CEX 托管层指纹

> letsbonk 平台币首战（与 pump.fun 的平台差异成体系记录）；14 个月+币龄、13.5 万持仓账户量级的 Solana meme 标的，混合重建演变架构（两端精确、中段插值）实战定型。开工时 skill v3.10.0。

**通道/坑（数据工程类，直接正式）**：
- **data-pipeline-solana §11 新节·长币龄混合重建+高密度期定向采集六件**：①混合重建演变架构（发射窗全量边+核心实体 ATA 流水+日级锚点前向填充+当前快照封口；**末日快照注入**修"清仓发生在锚点观测窗外则旧值永久残留"的尾部误差）②SQD 高密度期正解=2000 slot 小段×8 并发（发射日 24h/16.5 万边 82 分钟零缺口 vs 50K 大段 120 分钟仅推 3.4 链上小时）③**日级锚点观测边界**（高活跃期名义 1h 窗实际仅 ~3.6 分钟且只记变动账户——锚点单独禁作阴性依据，须快照/流水兜底；复核 3 实测抓出）④publicnode 大扫描死角（13.5 万账户 mint 恒 504；**api.mainnet-beta SPL 大扫静默返回空**=危险靠对账拦；owner memcmp 必须整 32 字节；amount 低位分片全零前缀逐层下钻跳过）⑤whale_deep 按地址频率分派（先一页估频：高频 7 万签名地址改事件窗定向拉，低频囤仓户秒级全 decode）⑥letsbonk 三件套（铸造边 2 条+dev-buy 数秒可卖回制造"creator 清仓"表象/creator fee 走 Raydium Lock burn&earn harvest 账本=真实收益引擎必查/毕业迁移 20.7% 入 Raydium）
- §4 辅助数据面 4 处：**Vybe v4 top-holders=Solana CEX 标签荒的最大补丁**（`/v4/tokens/<mint>/top-holders` 单页 1000 owner 级自带 Gate/Kraken/MEXC/KuCoin/Coinbase/Crypto.com/Wintermute/KOL/MEV Bot 标注；⚠余额字段系统性虚高——top1000 加总=总供应 113%，只用标签、余额链上为准）；**CMC data-api chart range=ALL** 全史日线（USELESS 案 437 点，补 GeckoTerminal 180 天回溯墙）；**fapi fundingRate 只回最近 500 条、接口首条≠永续上线日**（据此误判币安永续上线日、事件线调研纠正的实锤）；RugCheck insiderNetworks 免费层 accounts=None 再确认+**knownAccounts 388 条 AMM 池标签可作基础设施剔除表**
- GMGN bundler 标签≠发射日链上事实二见实证（带 bundler 标签的 top 大户实为毕业+6h 外盘买家）——§4"标签是线索不是定论"追加实证
- environment.md Shell 坑：**heredoc 内联 Python 对中文 str.replace 全角标点必须逐字符对准**（半角写法静默不生效无报错），中文精确替换一律 Edit 工具

**方法（playbook）**：
- 【候选·单案】**CEX 提币"囤仓大户"的托管/储备层判定指纹组**（entity-cluster §4）：跨户 raw 级逐位相等转账+同秒多户+整点提币窗+持仓篮子镜像+durable nonce/系统地址注资，满足多条即判托管/储备层——"提币囤仓=大户建仓"叙事整体反转为中性所方调度、CEX 托管合计上修；前置层**"同分钟批量注资/出账=交易所批次伪影"升正式**（机制二见：充值侧 AKE 71 址同批/提币侧本案），时间对齐类关联必先拉同窗全量做对照组
- 正式（机制明确）：**发射窗协同分层禁止只用"净拿>0"过滤**（entity-cluster §6a 流量/存量条扩展）——该过滤静默丢弃"毛量巨大、净额≈0"的闪电套利层（52 址毛量 86.94%/净持仓 0），"最强协同组"帽子戴错组（复核 1 REFUTED 实锤）；bundle/狙击分析必须流量、存量双口径各自分层再交叉
- report-template 流转图：**footnote 承载复核后行为链定性**=自解释验收的有效形态（读者只看图即得复核后最终定性）

**脚本**：收编 3——`window_fetch.py`（SQD 定向小段窗+并发，失败段 gaps.json 落盘）/`anchor_sampler.py`（日级锚点滚动校准；**参考锚定点已参数化**进 config.json ref_slot/ref_ts，收编时去除标的写死值）/`scan_sharded.py`（amount 低位递归分片，**分片逻辑可行、全量因 publicnode 间歇 504 未跑完待验**）；案例专属不收编（留 USELESS 目录存档）：build_camp_series/make_charts/make_flows/launch_analysis/gate2_reconcile

**Known Gaps（USELESS 遗留，增量更新时核）**：①分片全量扫描未完成（publicnode 间歇 504），对账已用 8 样本独立单查+top20 对表替代过关，全量 owner 口径快照缺 ②MfDuWeq 中枢（62.8% 供给历史过手）未穿透，复核 3 建议补观察哨 ③F8/dev 发射前 SOL 注资源未穷尽（主钱包签名过多，免费 RPC 翻页仅覆盖 2025-08 后）④锚点 fail 6 天（05-11/12/13 发射期由精确数据覆盖；09-19/20、06-24 插值）⑤发射 24h 末 12 址接盘大户（合计 16.4%）离场路径未逐个溯源（现全归零）

**质量指标**：初稿关键结论 6 条；复核判定 CONFIRMED 5 / WEAKENED 3 / REFUTED 5；漏检实体 2（F8↔dev 关联、闪电套利层）；传播级数字错误 2（囤仓群文图口径分叉、dev 收益 74 倍失真）——全部在交付前修正。
**成本指标**：交付用时约 15 小时（跨夜，含约 6 小时后台挂机）；上下文峰值约 17 万；Bash 调用密集但多为并行采集（轮次数未单独计数）。

## [3.10.0] - 2026-07-21 — LPT(ETH+Arbitrum) 全量复盘：质押型代币首战 + "庄不成立"呈现范式

> 首个原生质押体系标的（BondingManager 质押账本、记账式通胀、L1→L2 迁移史、TGE 8 年老币），与 meme 盘/VC 币（SQD）互补的第三类标的。双链合计 2.6GB/856 万事件重放；开工时 skill v3.8.1、写入时接 v3.9.0（并行会话竞态已按其 §9 做增量、未重复建节）。

**通道/坑（数据工程类，直接正式）**：
- **data-pipeline-evm §10 新节·质押型代币标的范式六件**：①权益=ERC20+bonded 合并口径（金库 Minter 行替换为残差，防与穿透归属双计）②质押账本状态机重放（topic_map 落盘纪律+Bond 事件自带事后总额做校准锚点+老事件联表 Transfer 补金额）③记账式通胀"已铸未领"桶单列（LPT 案 639 万=11.6% 总供给，既非协议自有也非可动用流通）④TransferBond 类非 Transfer 换手暗道审计（LPT 案 1,774 万枚/1.1 万笔；迁移中继批量落账=公共通道不作关联边）⑤L1→L2 迁移月双计坑（迁移不发 L1 Unbond，实体峰值虚增近一倍 19.4%→12.4%；对策=L1 账本截断在迁移前最后完整月+衔接毛刺写局限性）⑥月度粒度峰值口径
- §9 Arbitrum 增量：**HyperSync 限流是 key 级共享、不是端点独立**（eth+arbitrum 同 key 三进程并发时 arbitrum 429 密集、串行恢复）；二战数据点 129.4 万条 Transfer 97 分钟/40.9 万条合约全事件 26 分钟
- §4 三行：**The Graph 官方 subgraph 免 key 白嫖法**（explorer 前端 bundle grep `gateway.thegraph` 附近提取 NEXT_PUBLIC_ 内联 key——"前端直连 subgraph"项目通用，质押账本快照与链上重放双源互验）；事件签名 topic0 正算 `web3_sha3` RPC+反查 openchain lookup（⚠参数名是 `event` 不是 `topic`，用错全空不报错）；**Poloniex candles=2021 前老币价格唯一免费源**（CoinGecko `/coins/{id}/history` 免费层对老币历史全 no-price 41 连败、币安月度包仅覆盖上所后）
- §5 对账差额排查加一条：**2017 老版 OZ `burn()` 只发 Burn 事件不发 Transfer** 的幽灵差额（重放净供给>链上 totalSupply，LPT 案 604 枚）——web3_sha3 算 topic0 后 HyperSync 定向拉几秒查完；新链侧"Burn+Transfer(to=0x0) 双发"路径勿双扣
- supply-recon §1/§2：**CMC/CG 供给数据可能是冻结快照**（两家同值且精确对应链上历史时点值=快照冻结，LPT 案冻结 5 个月低报 11%）——老通胀币供给必须链上实查、第三方注明抓取时点；合并口径/已铸未领桶规则版；校准锚点范式通用规则

**方法（candidate 级，单案待复现转正）**：
- **"高扇出≠公共服务商"反向判据**（entity-cluster §6）：扇出度高（508 对手方）不足以判服务商——流量集中度（单一对手 45%）+生命周期同步性（与实体同日启停）+下游网络跨代连续性三条全中=实体自有分发网应并入（吞吐口径）；与"行为半枢纽剔除"分工明确（剔除管"不串外人"、本条管"不排自家"）——R4 复核推翻初判的教训
- **交易所质押产品识别三件套**（entity-cluster §3）：①资金 99%+ 溯至 CEX 热钱包本体且大额回流本体（散户做不到）②链上试水恰在该所 staking 产品官宣前数周（Wayback 对时间线）③受托节点专业且几乎专属——命中即归 CEX 桶不判庄；LPT 案把"全网最大神秘巨鲸 6.96%"翻案为 Bitvavo 产品
- **机构托管"逐月换仓轮换链"指纹**（entity-cluster §4）：每月整仓转新址+40+ 跳+余额守恒+OTC 台起点=托管安全轮换非出货；与"传动链分批剥离出金"（主仓递减+剥离额有出金去向=离场）按余额守恒性区分
- **"庄不成立"老基础设施币呈现范式**（entity-cluster §6）：报告价值支点改为①第三方供给口径纠错②托管化趋势量化③机构体系全周期故事（含离场价位与当前作业模式）④通胀分配结构；四问照答，"无庄"用全谱系阴性排查支撑（含 TransferBond 暗道审计）
- 正式 2 条（机制明确直入）：**月末快照粒度天然 sig 原子化**（月末余额已结清体系内互转）+月内脉冲被平滑的代价（离场清算月含一次性脉冲时以相邻月常态口径双报）（§6a）；**落盘取值纪律扩展覆盖 topic0/事件签名**（从 topic_map JSON 取不从记忆敲——手敲 TransferBond topic0 错一段扫出 0 笔 silent fail 实录）（§6）

**脚本**：
- 收编 `scripts/evm/fetch_hypersync_logs.py`：HyperSync 合约**全事件**版（不筛 topic、保留 topic0-3+data、断点续传）——BondingManager 类质押账本采集通用件
- 留工作目录（专属存档非复用件，pipeline §10 已注明）：rebuild_stake_ledger.py/rebuild_stake_l1.py（Livepeer 状态机重放，"事件自带绝对值做校准锚点"范式已入 playbook）、build_evolution.py（双链 ERC20+质押合并月度权益引擎，结构可参考）、fetch_subgraph.py（subgraph 批量分页快照模板）

**Known Gaps（LPT 遗留，增量更新时核）**：①Bitvavo 中转A 2026-07-20 新出 16.6 万去向未落定（数据截止时在途，观察哨候选）②疑似关联对（Coinbase 双 55 万仓）待互转证据③现役第三大委托人 0x5509be53(120 万,2.17%) 身份未明④传动链末端 123.3 万去向不明（0x0eb93a59 之后）⑤轮换链 B 仍月末活跃轮换中⑥labels 库 miss-queue：Upbit 4 址（route2 high 置信）建议回填主库、0xca07de3e（轮换链B跳板）等未标注⑦GoPlus 报 token owner 0x8dddb96c… 与 explorer controller 0xf96d54e4… 不一致未闭合（权限归属细节，不影响结论）

**质量指标**：初稿核心结论 13 条；复核判定 CONFIRMED 2 / WEAKENED 1 / REFUTED 0 + 数字修正 3 + 完整性补录 4；漏检实体 2 址（复核补）；传播级数字错误 2 处（实体峰值 19.4% 迁移双计、通胀总额少 9,195——桥中悬空在途提现）——全部在复核层拦截，未出报告。
**成本指标**：双链合计原始数据 2.6GB/856 万事件；墙钟约 5.5 小时（采集 2.3h 并行）；轮次数/Bash 调用数未单独计数（收尾会话另计）。
