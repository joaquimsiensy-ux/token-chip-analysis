# Solana 数据管线 · RPC 扫描与托管判别（data-pipeline-solana 分册 1/2）

> 母文档：`data-pipeline-solana.md`（薄路由索引页；来源声明与标注图例见索引页）。本册覆盖 **§0/0a/0b 通道速查·双 RPC 互补矩阵·死亡名单 / §1 全量持仓扫描 / §2/2a 托管类型判别 / §3/3a/3b 行为特征与流水坑 / §4 辅助数据面 / §5 架构约束与观测边界**；§6–§13 见 `data-pipeline-solana-capture.md`。正文 §N 交叉引用一律为母文档节号。

## 本册路由

- §0 通道与死亡名单；§1 持仓扫描；§2/§2a 托管判别；§3/§3a/§3b 行为与流水；§4 辅助面；§5 观测边界。

## 0. 通道速查

| 用途 | 通道 | 要点 |
|---|---|---|
| **全量持仓快照（getProgramAccounts 大扫描）** | 公共 RPC `https://solana-rpc.publicnode.com` | 免 key；实测放行 99–117MB 级全量响应（IO 8.5 万账户约 45s，timeout 给 90s+） |
| 账户历史 / 钱包持仓画像 | 公共 RPC `https://api.mainnet-beta.solana.com` | 免 key；限速紧（间隔 ≥0.12s、退避重试），本机走 clash 代理 `[实测·他场景]` |
| 单地址 / 单笔交易核验、公开标签 | Solscan 网页（`solscan.io/token/<MINT>`、`/account/<ADDR>`） | 免 key；浏览器可看，**WebFetch 直读被 Cloudflare 拦**（见死亡名单）；作报告可验证性背书 |
| 全量历史转账（archive 回放） | SQD portal（见 §8，后续实战补入） | 免 key 免代理，补公共 RPC 无历史回放的洞 `[实测·他场景]` |
| 深挖升级通道（增强 API） | Helius | 运行前检测 `~/.config/helius/api-key`：存在则按 Helius 参数跑，缺失则降级公共 RPC（key 注册沿革见 CHANGELOG） `[实测·他场景]` |
| 量价 / 衍生品 / 解锁表 | CoinGecko / fapi.binance.com / Coinglass / DropsTab + Tokenomist | 见第 4 节 |

### 0a. 双公共 RPC 互补矩阵（关键工程事实）

两个免费 RPC 各屏蔽不同方法，**必须按方法路由，单节点走不通全程**：

| 方法 | publicnode | api.mainnet-beta | 用途 |
|---|---|---|---|
| getProgramAccounts（SPL Token 大扫描） | ✅ 放行（117MB 也给） | 未试（预期拒绝） | 全量持仓快照 |
| getProgramAccounts（**Token-2022** 大扫描） | ❌ 504（无 dataSize 过滤与 dataSize=170 均超时——疑无 Token-2022 mint 二级索引） | ✅ **放行**（无 dataSize 全扫 16,186 账户 4.6MB 45s，走代理）——与 SPL 行为相反 | Token-2022 币全量快照（CLUDE，07-13） |
| getTokenLargestAccounts | ✅ | ❌ 持续 429（sleep 也无用） | top20 冒烟 |
| getAccountInfo / getTokenSupply | ✅ | ✅ | owner 解析、供应 |
| getMultipleAccounts | ❌ 屏蔽（`Request blocked: blocked parameter`） | ✅（上限 100 键） | 批量 owner 解析 |
| getTokenAccountsByOwner | ❌ 同上屏蔽 | ✅ | 钱包全持仓画像（§3） |
| getSignaturesForAddress / getTransaction | ⚠️ **仅近 ~3–4 天**（老账户静默返回空数组，勿误判"无历史"） | ✅ 全史（bigtable，limit 上限 1000） | 流水追踪 |

- publicnode 的屏蔽报错是 `-32602 Request blocked. Details: blocked parameter`——遇到即换 api.mainnet-beta，不要重试。
- **publicnode 的历史签名只保留 ~3–4 天（外部 CLAW/FyedK 分析实测，2026-07）**：`getSignaturesForAddress` 对更老的账户**静默返回空数组、不报错**——绝不能据此判"该地址无历史/休眠"（同 ETH mevblocker 静默丢日志坑）。凡追历史流水必走 api.mainnet-beta（bigtable 全史）；publicnode 只做当前状态大扫描与近几天流水加速。
- 批量 owner 解析的省事路线：与其在 getMultipleAccounts 上折腾，不如全量扫描时一次 `dataSlice{32,40}` 把 owner 带出来（§1）。

### 0b. 免费通道死亡名单（实测不可用，别再试）

- Solscan API：`api.solscan.io`/`api-v2.solscan.io` 被 Cloudflare 拦（返回 Just a moment 页），`pro-api.solscan.io` 401 需 token；**WebFetch 抓 solscan.io 页面同样被拦**——标签只能靠 WebSearch 搜地址字符串间接命中
- `rpc.ankr.com/solana`：403 需 API key
- `solana.drpc.org`：400（外部 CLAW 考古，2026-07）
- extrnode：SSL 错误（外部 CLAW 考古，2026-07）
- solana.fm API：502（不稳，不可依赖）
- Birdeye `public-api.birdeye.so`：401 需 key
- Arkham `intel.arkm.com`/`arkm.com`：WebFetch 403，免费程序化不可用
- **GMGN 全路径（含 API 与网页）被 Cloudflare 拦**：UA+Referer 伪装无效（实测 2026-07-13，未穷尽住宅代理等绕过手段；gmgn-* skills 的正规 key 通道不受影响，本条指免 key 抓取路线）（CLUDE，07-13）
- web.archive.org CDX 对 `x.com/<个人页>` 常年零快照（官推旧用户名回溯此路不通；twitterscore 付费版未试）（CLUDE，07-13）

## 1. 全量持仓扫描（getProgramAccounts + owner 去重）

- 核心调用（打 publicnode，见 §0a）：
  ```json
  {"jsonrpc":"2.0","id":1,"method":"getProgramAccounts","params":[
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
    {"encoding":"base64",
     "dataSlice":{"offset":32,"length":40},
     "filters":[{"dataSize":165},{"memcmp":{"offset":0,"bytes":"<MINT>"}}]}
  ]}
  ```
- SPL token account 定长 165 字节，布局：`mint` 在 offset 0（32B）、`owner` 在 offset 32（32B）、`amount` 在 offset 64（8B，u64 LE）。`memcmp offset=0` 按 mint 过滤；**dataSlice 第一次就切 `{32,40}` 把 owner+amount 一起带出**——IO 实录曾先切 `{64,8}` 只拿 amount，随即发现缺 owner 被迫整段重拉 117MB，白耗一轮。
- **口径红线：token account 数 ≠ 持有人数。** Solana 特有：一个 owner 可开多个 token account（ATA + 辅助账户），必须按解析出的 owner 字段去重后才是独立持有人数（IO 实录：85,847 非零账户 → 去重 85,811 独立 owner）。两个数都要留存，分开报告。
- 容量参考：8.5 万非零账户规模，`dataSlice{32,40}` 响应 117MB / `{64,8}` 响应 99MB，publicnode 均 HTTP 200 放行，耗时约 40–45s——curl `-m 90` 起步，落盘（`-o`）后本地解析，不要过管道。getProgramAccounts **无分页**，一次全量返回；被拒/超时的备选顺序：加 dataSlice 减负 → 换 Helius（**实测升级**：24.7 万账户 67MB 响应量级，publicnode 恒 504、Helius 默认 120s 超时同样断——正解 = Helius + curl `--compressed`(gzip) + 300s 长超时一次拉全，`scan_token_accounts.py --rpc <helius> --timeout 300` 已固化；来源：GOAT(Solana) 分析，2026-07-22）。
- 坑预警（Token-2022 实测升级）`[VERIFIED·CLUDE实战]`：先 `getAccountInfo(<MINT>)` 看 mint 归属程序。若是 Token-2022（`TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb`）：①pump.fun 新币标准是 Token-2022，账户主流 dataSize=165 与 170 双形态并存，但**还有零星其他 dataSize**（CLUDE 实测 165/170 双扫漏 14 个账户 0.036% 供应，对账不闭合）——正解是 **api.mainnet-beta 无 dataSize 过滤全扫**（见 §0a Token-2022 行，publicnode 此路 504）+ `memcmp offset=0` 按 mint 过滤；②扫描器默认 `--datasizes auto`：Token-2022 强制 all，SPL 用 165；Token-2022 显式 165/170 会拒绝，账户加总不等于 `getTokenSupply` 也不会写正式 holders 产物。（CLUDE，07-13；2026-08-02 加固）
- 冒烟与交叉校验：正式扫描前先 `getTokenSupply(<MINT>)`（链上总供应）+ `getTokenLargestAccounts(<MINT>)`（top 20 token account）各打一发，扫描结果的总和与 top 榜必须能对上（IO 实录：扫描加总 799,211,891 vs getTokenSupply 799,211,890.5，个位级吻合）。
- 解码要点：dataSlice 返回 base64，解码后 `bytes[0:32]` = owner（base58 编码回地址串，可纯 Python 手写无外部依赖）、`bytes[32:40]` = amount（u64 LE 原始数）；UI 数量换算用 `getTokenSupply` 返回的 `decimals`，不要自己去 mint 账户抠字节。
- **G8 离线重放契约**：`holders_snapshot_meta.json` 绑定的每个 GPA `raw_artifact` 不是“有文件有哈希”即算通过；identity emitter/check 必须调用 `scan_token_accounts.py` 的同一套 `parse_gpa_response`＋`parse_token_accounts`，从原始 RPC JSON 重做 base64 解码、跨 dataSlice/pubkey 去重、账户明细和 owner 聚合，并要求逐条等于 `holders_accounts.json`/`holders_owners.json`；同时解析 supply receipt 的 `result.value.amount` 与 `supply_raw` 闭合。round4b 格式存量若 raw/supply 实物完整可直接重新 emit；缺失或重放不一致则必须重跑 `scan_token_accounts.py`，禁止手补 meta/hash。
- 供给基线双口径纪律：链上实查总供应（精确到个位）与 CMC/CoinGecko 流通量是两套数——流通量链上算不出来，必须借第三方口径。全文分开使用、分开标注来源，禁止混用。
- 分层默认档位（按供应量级可调）：`≥100万 / 10–100万 / 1–10万 / 1千–1万 / <1千` 五档，产出集中度画像表——它是整份报告的定量地基。
- 扫描副产品 = 老鼠仓排查输入：统计 Top N 每个 owner 的 token account 数量、余额分布、建仓时间同步性，排查蚂蚁搬家式多钱包暗仓；**阴性结论也写进报告**（防读者高估链上暗仓风险）。

## 2. 托管类型判别（owner 程序 → 托管协议）

Solana 特有优势：program-owned PDA 让托管类型可以直接从账户归属读出来，无需像 EVM 那样啃字节码或赌浏览器标签。

- 两跳判别流程：
  1. 取 token account 的 owner 字段值 X（这是 authority 地址，可能是钱包也可能是 PDA）；
  2. `getAccountInfo(X)`（`dataSlice{0,0}` 零字节切片省流量）看 X 本身归哪个程序所有：`1111...`（System Program）= 普通钱包；已知托管程序 = 对应协议 PDA；返回 null（NOT_EXIST）= 从未注资的 PDA（多签 vault 常见形态）。
  - 预筛提速：PDA 必 off-curve，先做 `is_on_curve` 检查可省一半 RPC 调用 `[知识补充]`。
- 已知程序映射（本地维护"程序 ID → 托管协议"映射表，逐战累积）：
  - **Squads 多签程序 `SQDS4ep65T869zMMBKyuUq6aD6EgTu8psMjkvj52pCf`** → 官方金库佐证（CEX 不会用 Squads 管钱包）。识别姿势：金库大额转出交易的 instructions 里出现该程序 ID；再叠加项目官方代币分配文档对表（分配结构、总量、年限）完成定性。
  - **Magna vesting 程序 `magnaSHyv8zzKJJmr8NSz5JXmtdGDTTFPEADmvNAwbj`** → 线性解锁托管 PDA（token account 的 owner 直接是它），特征为持续（小时级）匀速释放。
  - **Streamflow 锁仓程序 `strmRqUCoQUgGUan5YhzUZa6KqdzwX5L6FpUxfmKg5m`**（外部 CLAW 分析实测，2026-07）→ 锁仓 escrow 的 token 账户 authority = 账户自身；stream 元数据账户（owner=strm 程序）可 **raw 解码锁仓参数**：定位 mint 的 32 字节偏移 `moff` 后，`sender@moff-128`、`recipient@moff-64`，参数区 `start/deposited/period/amount_per_period/cliff` 在 `moff+148` 起的 u64 序列（flags+stream_name 紧随）。**懒人路线**：GMGN holders 的 `streamflow_status` 字段直接给 `next_unlock_time/current_locked_amount`，无需手解，与链上互验即可。
    **固定偏移速查（data_len=1104 版布局，CLUDE 实战三处互验）**`[VERIFIED·CLUDE实战]`：offset 9=创建时间、**33=end_time（到期）**、409=start、417=net_deposited、441=cliff 时间（33/409/441 对一次性 cliff 流三处同值互验）；**cancelable_by_sender/recipient、transferable_by_sender/recipient、automatic_withdrawal 标志位必读**——`period=1s+cliff_amount=全额`=一次性 cliff 到期全解，transferable=0 直接反证"受益权可场外转让"风险提示（写"锁仓可转让"之前必查此位）；automatic_withdrawal=0 则到期后币不自动离开 escrow，观察哨要按"历史到期→处置最长空窗"设过渡期防误报。解码脚本 `scripts/solana/probe_escrows.py`，调用时用必填 `--targets-file` 注入本案 `{address, label}` JSON 数组。（CLUDE，07-13）
    - **"即建即提"洗筹指纹（CLAW 实测）**：操盘方用即建即提 stream 做一跳中转，切断"老仓→新仓"的直接转账链路伪装成独立成本；识别锚点 = 提取 tx 的 **feePayer = Streamflow 自动提取服务 `wdrwhnCv4pzW8beKsbPa4S2UDZrXenjg16KJdKSpb5u`**，多笔提取共用此 feePayer = 同一批操作，据此把散落的"新钱包"归回原实体。
    - **recipient 激活状态检测**（外部 CLAW 考古，2026-07）：对 stream 的 recipient 地址查账户存在性——账户不存在（fresh keypair 从未注资）= 收款人从未动过，锁仓休眠中；配套受益人时序画像：发射后分钟级首买 = 先验知情，发射前数天新建并注资 = 预谋配置。
    - **措辞纪律：锁仓流的可转让性以该 stream 实例的 transferable_by_* 标志位为唯一裁决**（外部 CLAW 考古，2026-07；与上方"标志位必读"条呼应）——transferable=1 时解锁权可私下转售且不在代币转账留痕，"锁仓至 2030"≠"当前受益人持有至 2030"，结论措辞必须带此提示；transferable=0 则直接反证该风险，禁写"可转让"。
- 官方金库确认后必须追下游：高频（数小时一轮）向数十个地址小额发放 = 排放/奖励发放行为指纹，据此把"金库流出"与"抛售"区分开。

### 2a. 自建质押/托管合约判别五步法（transfer_in 大户 → 官方质押池的完整判定链）`[VERIFIED·PUB实战]`

**触发纪律：任何 transfer_in 型大户（GMGN transfer_in 标签 / 多地址转入 / 短期大额累积——表面完全符合"归集庄"画像），owner 程序两跳判别必须先于庄家定性**——PUB 实测一个 13.57% 供应的"疑似 dev 系分仓"经此流程反转为官方质押池（币的主人是各质押用户），初判若直接进报告即整案定性错误。判定五步：

1. `getAccountInfo(地址)` 看 owner 程序——非 System Program 即程序托管 PDA；
2. 对该程序账户查 `executable=true` + loader 是否 `BPFLoaderUpgradeab1e11111111111111111111111`（可升级 loader）；
3. 解析 ProgramData：程序账户 `data[4:36]` = ProgramData 地址 → 其元数据含部署/最后升级 slot（与项目公告时间对表，"公告质押上线当日部署"即时间闭环）；
4. **ProgramData `data[13:45]` = upgrade_authority——必查是否已放弃/转多签**。未放弃 = 项目方保有单方面升级程序、理论上转走全部托管资产的能力——**这必须写进报告风险章**（PUB 案：质押池托管 13.57% 供应而升级权未放弃，是全案最大结构风险，由对抗复核 RPC 抓出）；
5. 部署者（upgrade_authority 持有人）首笔 gas 溯源——来自 creator/项目方钱包即闭环"官方部署"定性。

**配套账本验证**（`scripts/solana/stake_decode.py` 自动做）：池的全部 token account 签名史 decode → 逐用户存/取账本 → **账本净额合计 vs 池链上余额精确对表**；"支付奖励"（用户取回>本金）与"自由赎回"记录是排除"归集仓伪装成质押池"的关键证据。**质押池确认后，全部持仓/留存分析必须做质押修正**（有效持仓=现货+池内份额，`replay_edges.py evolution --stake-pool`），否则质押大户被误判清仓（同 playbook §8 HYPE 教训的 Solana 特化）。（PUB，07-14）

## 3. 行为特征识别库（标签缺失时的兜底判据）

证据强度低于公开标签，措辞只能给到"疑似/高度疑似"。逐条：

- **月度机械解锁指纹**：每月同一日（常锚定 TGE 周年日）+ 金额分毫不差的转账。用整除关系反推 vesting 参数：固定月度额能整除出圆整总分配额与标准月数（12/24/36/48）→ 还原出合约参数。机械性是区分"合约解锁"与"主观卖出"的硬指纹。
- **整数余额 + 长期不动** = 冷储特征。
- **CEX 冷钱包动态指纹**：某大户向**已知 CEX 热钱包**调拨**多种不同代币**（一次性或数日内连续多币种）= 交易所冷→热内部补库存，据此可把"神秘大户"改判为该 CEX 冷钱包。静态指纹（整数余额）与动态指纹（多币种供热钱包）互补。
- **同时是多个热门币的最大持仓者** = CEX 归集钱包特征。免费源确证不了归属哪家时，定性降级为"疑似 CEX"并在表格明写"未能免费确证"。
- **钱包全持仓画像判托管**：`getTokenAccountsByOwner`（打 api.mainnet-beta，publicnode 屏蔽）列出钱包全部 SPL 持仓——数十个币种、多为大额圆整数、SOL 余额≈0 = 托管/金库/多签特征（正常交易钱包必须留 SOL 付 gas）。
- **币安 Alpha 集齐率判别法** `[VERIFIED·PENGUIN关卡]`：对"多币种高频大仓"，getTokenAccountsByOwner 全持仓 × 币安 Alpha bapi 全量表（Solana 链 ~70 币）取交集——**覆盖率 ~90% 以上（几乎集齐 Alpha 名单）≈ Alpha 专属托管库存仓**：普通用户不会恰好持有交易所 Alpha 在架的几乎全部币种，集齐只有所方库存仓才会发生。**低集齐率不足以正判托管、也不能反向认定非托管**——巨鲸/庄家同样可以一个钱包放多种代币，身份另找正向证据（标签/链根/gas supplier 体系/批次伪影等）。配套强指纹：流水走 vanity 批量程序（如 BN111 前缀）+fee payer 多址轮换代付+与零余额执行仓对倒+执行仓直连多 DEX 池=所级托管执行体系；已确认地址见 address-book Solana 节（2026-07-22 实测 94% 库存仓实证；2026-08-02 用户修订只留高档正判）。
- **高频小额、多收款人** = 运营/发薪钱包。
- **从 Coinbase Prime 提币** = 机构托管专用通道（散户不会用），直接锚定该地址背后是机构实体——集群定性的关键旁证。
- **解锁款穿透追踪的终点二分**：每笔解锁款穿透中转层追到终点——进 CEX 热钱包 = 进入可售状态（派发倾向）；进囤币钱包 = 被收走（吸筹倾向）。同一 vesting 源按月对比终点变化，可捕捉行为拐点（全案最强证据的产生方式）。
- **轮换出货通道指纹**：同一 vesting 源每月固定经同一中转、但**每月更换下游地址**（4 月进 CEX、5 月进新地址 A、6 月进新地址 B…）= 刻意轮换出货路径规避追踪，本身即"有意隐匿的处置行为"的行为证据。
- **共用中转地址（共同出纳）**：两个"独立"大户在各自解锁日把钱汇入同一个中转地址，且中转链路闭合归集到同一囤币钱包 → 高度疑似同一实体/利益联盟。措辞锁定"高度疑似"，绝不写成确权（也可能是做市商/OTC 同时服务多个独立客户）。
- **观察哨衔接**：解锁款追踪的结论要落成可证伪检验点——下一个解锁日的解锁款去向即天然观察哨，报告里预先写明"结论强化条件"与"反转条件"两个方向，下次分析直接验收。

### 3a. 流水追踪的三个 Solana 特有坑

1. **签名史归属**：代币流水查 token account/ATA，不以 owner 签名条数替代；owner 与 ATA 均须记录查询范围。判例见 casebook E-16。
2. **签名列表投毒**：只有 pre/postTokenBalances 中目标主体余额真实变化才算活动；签名提及不等于本人操作。判例见 casebook E-16。
3. **decode 按 mint 过滤**：先过滤目标 mint 并核 decimals，再解释金额与动作。判例见 casebook S-04。
4. **高频 owner 史稀释**：改查目标 ATA 全签名；ATA 销户时从已知交易反查 accountIndex 后补扫。判例见 casebook S-04。
5. **镜像 vanity dust 投毒**：完整地址逐字节比对并核余额腿；密集同窗签名不得成关联边。判例见 casebook E-10。
6. **中转窗 NET 校验**：窗口解码后必须验证物理净额；出现负净额立即补全签名史。判例见 casebook S-04。
7. **纯接收方漏边**：边表不配平的节点必须走 ATA 级补扫，全部净流闭合后才可发布。判例见 casebook S-04。
8. **ATA trace 资金侧**：用 owner 主钱包的原生币变化定性买入/领费；只有 ATA 的 sol_delta 不得作动作分类。判例见 casebook S-05。
9. **CEX 精确注资型定投**：可写交易所提币后定投画像；资金源在 CEX 截断时不得确证独立或项目方归属。判例见 casebook C-07。

### 3b. Solana 控盘团伙（庄）识别指纹（外部 FyedK/CLAW 协同集群分析，2026-07）

meme/微盘"庄"（多钱包控盘团伙）的关联硬证据（任一即可，叠加为铁案），与 analysis-playbook §6 通用聚类规则配合、是其 Solana 特化：

1. **同 slot 原子下单**：多钱包在完全相同 block 同买同卖 → 单控制端 bundle（用 pre/postTokenBalances 差分定位每钱包买卖，按 `(mint,side)` 聚合看是否同 slot）——最强铁证。
2. **跨组同区块交易**：某代币被两组钱包在同一 block 买入（常见于旧组收工/新组开工的交接点，掉队钱包混进新组 bundle）。
3. **共用归集口/中转**：不同组利润流入同一归集地址，或同一中转既收 A 组款又给 B 组发起始 gas。
4. **机器人 + 优先费指纹**：同一交易 bot（如 Axiom `FLASHX8DrLbgeR8FcfNV1F5krxYcYMUdBkrP1EPBtxB9`）+ 同一套**离散 cu_price 预设档**（某案 436363 / 800000 / 2.5M / 3.636M / 6.667M microLamports 五档）——普通用户不会用这套组合，是技术指纹（用户说"gas 都一样"即指此）；优先费按买/卖分固定档位也算。cu_price 从 ComputeBudget 指令 `SetComputeUnitPrice`（data 首字节 3）解析。
5. **金额分档 + ±10% 抖动**：多钱包买入额几乎相同但带随机偏移（反聚类伪装）= 脚本驱动铁证。
6. **母钱包代付创建落仓户 ATA**：落仓/收币钱包**收币前无任何链上生命**（首笔即被注资），其 token account 的租金由**付款方母钱包代付创建**（同一 tx 里母钱包既转币又付 ATA 创建费）——收款方是母钱包凭空生成的空壳，比"gas 同源"更强的控盘指纹（换钱包也换不掉这个"凭空生成收款方"的结构）。识别=对疑似落仓户查最老签名，看首笔是否为对手方 createAssociatedTokenAccount+transfer 同 tx（OPAL(Solana) 实测 2026-07-14）。
7. **跨地址凑整回补**：N 笔零散金额（30万/180万/80万…）从一个地址精确凑齐**整数目标**（如 1,000 万整）补入另一地址，使多个落仓户终局配比落成整数（如 25/25/20 万）——**跨地址的全局配平只有单一记账者能做到**，是"单一控制端"的强指纹（独立主体不会为凑别人仓位的整数而分15笔转账）。识别锚点=某中转的净持仓被一串碎额转账修剪到整数（OPAL(Solana) 实测 2026-07-14）。

**逆向找历代马甲（最高价值的一招）**：庄的冷门微盘常是自买自卖 wash trading、外部买家≈0，根本没有跟单狗——所以"最近的同款买家"往往就是庄自己的历代钱包。**总归集口的历史流入地址列表 = 庄的历代马甲归集头名录**（某案总归集口两年 154 个流入地址）。比 co-buyer 扫描高效得多。（此洞察跨链通用，已提炼进 analysis-playbook §6。）

**资金闭环典型**：CEX（多为币安热钱包 `5tzFkiKscX…`，余额百万级 SOL 可验证）提现 → 分发/中转钱包 → 各代马甲交易 → 组内归集头 → 总归集口 → 100% 存回币安 = 庄是币安实名用户。

**换钱包后第一时间识别的三死穴**：①固定归集口/核心中枢新流出的零历史地址 = 新马甲；②bot+cu_price 预设档的同 slot 多钱包 bundle 行为指纹（钱包可换、打法不变）；③同区块多钱包 + 最终币安回流。狙击盘还常 100% 经 Axiom Trade 路由（`FLASHX8…`）+ 防抢跑标记账户 `jitodontfrontB1111111TradeWithAxiomDotTrade`。

## 4. 辅助数据面

- **GMGN 单币深挖接口 ⚠️ 2026-07-13 实测已失效**：UA+Referer 伪装被 Cloudflare 全路径拦截（下述端点当日全 403/JS challenge，未穷尽住宅代理绕法；正规 key 通道 gmgn-* skills 不受影响）。以下记录保留供风控放松后重探（原实测 2026-07 初可用）：
  - `gmgn.ai/vas/api/v1/token_holders/sol/<mint>?limit=100`：前 100 持有人全字段，`maker_token_tags` 直接标 creator/dev_team/**bundler/sniper**/transfer_in、`is_suspicious`、`streamflow_status`（锁仓）、`history_transfer_in/out_amount`、`buy/sell_amount_cur`、`native_balance`、`start/end_holding_at`（进出场时间）
  - `/vas/api/v1/token_traders/sol/<mint>?limit=100&orderby=realized_profit`：top100 盈利榜（同字段结构）
  - `/vas/api/v1/token_trades/sol/<mint>?limit=100&maker=<wallet>`：**按钱包过滤的逐笔成交**（带 tx_hash/priority_fee/tip），`data.next` cursor 分页——溯源单钱包买卖节奏利器；不带 maker 返回空
  - `/api/v1/token_stat/sol/<mint>`：holder_count/top_10_holder_rate/dev_team_hold_rate；`/api/v1/token_holder_stat/sol/<mint>`：dev_count/**sniper_count/bundler_count/fresh_wallet_count**（一眼看清庄家结构）
  - `/defi/quotation/v1/tokens/kline/sol/<mint>?resolution=1d`：日 K
  - **口径坑**：GMGN holders 是**当前**持仓口径，与 RugCheck（账户总数口径）可差 2–20 倍，两者交叉验证不互替。GMGN 的 bundler/sniper 标签是线索不是定论，仍须落链上 §3b 指纹确认（二见实证：某 top 大户带 bundler 标签、链上实为毕业+6h 才进场的外盘买家——直接采信会把建仓时点/成本全判错；来源：USELESS(Solana) 分析，2026-07-21）。
- **pump.fun coin API**：v1（frontend-api）已死（530）；**v3 可用**——`frontend-api-v3.pump.fun` 拿代币元数据/creator/description（外部 CLAW 考古，07）。**v3 的 creator 履历三端点**（走 clash 代理，dev 前科调查核心通道）：①`/coins?creator=<addr>&limit=100&includeNsfw=true` = creator 名下全部发币记录；②`/users/<addr>` = 平台账号画像（用户名/关注数/是否绑定 X）——**x_username=null 可证明"链上 creator 与官推无平台级绑定"**（官推侦查的链上侧交叉证据）；③`/balances/<addr>` = 站内持仓视角（不含毕业后链上 SPL 持仓，引用须注明口径）（PUB，07-14）。
- **RugCheck `api.rugcheck.xyz/v1/tokens/<mint>/report`（免 key）**（外部 SGL/CLAW 分析实测，2026-07）：一次拿 topHolders（含 owner+pct+**insider 标记**）+ markets（LP 名单）+ **insiderNetworks**（转账关联的内幕簇，直接给出关联地址网络）+ launchpad——**是 `getTokenLargestAccounts` 恒 429 的最佳替代**（§0a），insider 关联比自建聚类省事，但仍按 analysis-playbook §6 硬规则复核。
  **坑：免费层 insiderNetworks 的 size 字段有值但 accounts 成员列表可为空**——只能当线索计数用，成员名单要自建聚类复现（PUB，07-14；USELESS 案 07-21 再确认免费层 accounts=None）。**knownAccounts 字段实测 388 条 AMM 池/基础设施标签，可直接作算集中度前的剔除表**（USELESS，07-21）。
  **坑：`detectedAt` 是 RugCheck 索引器首见时间，不是发射时间**——老币可差出几个月（TROLL 实测差 145 天：真实创建 2024-03-10，detectedAt 2024-08-02），据此定"发射窗"会漏掉整段早期历史（TROLL 案初稿因此漏了创建 tx 的 dev 闪电轮与 2024-08 做量集群所在的整个时段）。**发射时点唯一正解=curve/mint ATA 最早签名核实到秒**（getSignaturesForAddress 翻到最老；
  pump.fun frontend-api-v3 的 created_timestamp 可作秒级互证）（TROLL，07-29）。
- **GMGN 正规 key 通道 CLI 的两个高价值参数**（gmgn-* skills，Cloudflare 拦的是免 key 抓取，此通道不受影响）：`token holders --tag`（smart_degen/sniper/bundler/transfer_in 等 10 类标签过滤）与 `traders --order-by profit`（盈利榜）——transfer_in 过滤结果是 §2a 判别流程的候选入口（PUB，07-14）。
- **Bags 平台盘专项**（外部 SGL/P0 分析，2026-07）：算集中度前必先剔平台基础设施——链上 creator 统一 `BAGSB9TpG…`（平台署名非项目方）、平台金库 `FhVo3mqL…` 恰持**每币 17% 整数配额**（单日 3000+ 签名高频机器钱包）；mint 后缀 BAGS；`bags.fm` 代币页可查创作者费累计领取额（=项目方还在乎的链上心跳）。整数配额（17.001%/20.001%）= 设计分配非市场吸筹。
- **Solscan**：地址公开标签（CEX/项目方）、逐笔交易历史核验；RPC 侧等价物为 `getSignaturesForAddress` + `getTransaction`。报告页眉声明"所有关键地址均可在 Solscan 点击验证"作为可验证性背书（注意 WebFetch 抓不了 Solscan，背书是给人手点的）。
- **衍生品结构化首选 `fapi.binance.com`（币安永续 API，免 key）** `[07-12 本机直连实测]`：
  - 资金费率史：`/fapi/v1/fundingRate?symbol=<SYM>USDT&limit=90`（返回逐 8h 费率）
  - OI 历史：`/futures/data/openInterestHist?symbol=<SYM>USDT&period=1d&limit=30`（响应还自带 `CMCCirculatingSupply` 字段，是流通量口径的又一免费来源）
  - 本机直连可用——**api.binance.com 被 451 拦但 fapi.binance.com 没拦**（与 data-api.binance.vision 同属绕拦通道）。OI 降+价升+费率中性 = 现货驱动反弹的标准证据组合。
  - **坑：/fapi/v1/fundingRate 只返回最近 500 条（约 166 天），接口首条≠永续上线日**——据此判上市时间会系统性晚判（USELESS 案据此误判币安永续上线日，靠事件线外部调研才纠正）；上线日用公告/事件线定，费率史只当近期窗口用（USELESS，07-21）
- **Coinglass** `coinglass.com/currencies/<SYMBOL>`：OI/费率的网页兜底（标的没上币安永续时用）。
- **解锁表多源交叉**：DropsTab `dropstab.com/coins/<slug>/vesting` + Tokenomist `tokenomist.ai/<slug>`（+CryptoRank/Coinglass vesting 页）+ 链上机械解锁指纹（第 3 节）互验；下一个解锁日的时间和量往往是全案最重要的单一外部信息。
- **Vybe v4 top-holders（Solana CEX 标签荒的最大补丁）**：`api.vybenetwork.xyz/v4/tokens/<mint>/top-holders?limit=1000&page=N`（header `x-api-key`，key 见 api-keys.md 第 13 节「Vybe」）单页 1000 个 **owner 级**持仓自带标注，实测命中 Gate/Kraken/MEXC/KuCoin/Coinbase/Crypto.com/Wintermute/KOL/MEV Bot——免费可用源里最好的 Solana CEX/机构标签面。**⚠余额字段系统性虚高不可用**（top1000 加总=总供应 113%）：只用它的标签，余额一律以链上快照为准（USELESS，07-21）
- **CMC data-api 全史日线**：`api.coinmarketcap.com/data-api/v3/cryptocurrency/detail/chart?id=<cmc_id>&range=ALL` 一次拿发射日起全史日级量价（USELESS 案 437 点全覆盖）——补 GeckoTerminal 公共 API 只回溯 180 天的洞；cmc_id 从币页 URL/search 端点拿（USELESS，07-21）
- **CoinGecko**（`/api/v3/coins/<id>/market_chart?vs_currency=usd&days=90&interval=daily`）：近 90 天日线量价结构。**坑：coin id ≠ 项目名/slug**（io.net 的 id 是 `io` 不是 `io-net`），先查 `/api/v3/coins/list` 或 search 端点确认 id；免费层限速紧，失败等 30s 重试。
- **CoinMarketCap**：流通量口径来源（与链上总供应分开标注，见第 1 节）。
- **项目官方 tokenomics 文档**：分配结构对表，用于金库/排放池定性。
- **CEX Proof-of-Reserve 审计 PDF**：免费且权威的交易所链上钱包地址来源（例：Bybit 官网 PoR 审计 PDF 确证其 Solana 钱包）。
- **WebSearch 裸搜地址字符串**（带引号精确匹配）：噪音大（TikTok 垃圾页居多）但能命中 PoR PDF/链上侦探推文（Onchain Lens 类）/媒体标注（BlockTempo/DA Labs 类）——Solscan API 全灭后这是免费标签的主通道；两地址可 `"A" OR "B"` 合并搜。主流 CEX 的 Solana 钱包**没有统一官方标签库**，只能拼凑，每条标注留证据链接。
- **独立反叙事信源**：对项目方利好（回购/销毁等）不直接采信，找第三方独立审查口径核查成色（销毁是公开市场买入还是排放池自燃？年销毁对冲多少年排放？启动时点是否精准卡在解锁日？）。

## 5. 架构约束与观测边界（必须写进报告局限性声明）

- **免费公共 RPC 无 archive 历史回放** → IO 时代的三段式架构：
  1. 当前全量快照（第 1 节）；
  2. 近 90 天逐笔交易追踪（`getSignaturesForAddress` + `getTransaction`）；
  3. 更早的筹码变迁依赖第三方图表平台口径。
  **2026-07-12 起此限制已被 §8 的 SQD portal 全量转账通道解决**——三问一异常框架的全历史演变重放（问 3）走 SQD；三段式仍是 SQD 不可用时的降级架构，届时第 3 段依赖必须写进局限声明。
- 公共 RPC 实测参数 `[实测·他场景]`：请求间隔 ≥0.12s、走 clash 代理；退避重试 + 断点续传是采集脚本标配（IO 实录：逐笔 decode 配 1.2–1.5s 间隔 + 每请求最多 4 次重试稳定跑通）。
- **CEX 内部账本不上链**：所内换手、做市商行为完全不可见。只能靠量价结构 + 衍生品指标（OI/费率）间接推断，不对 CEX 内行为下强结论；措辞永远带"链上可观测范围内"限定。
- **Solana CEX 标签覆盖缺口**：OKX/Bitget/Upbit 等所的 Solana 钱包免费源基本查不到 → CEX 托管总量可能被系统性低估，合计数旁必须注明。
- **集群判定 = 强推断非确权**：共用中转 + 时序同步是图谱强推断，不构成确权；证据链逐条列出让读者自判，局限性单列一条。
