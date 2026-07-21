# Solana 数据管线（SPL 代币筹码分析）

> **来源声明（2026-07-12 修订）：本文档原自 IO 分析最终报告反推。IO 原始会话记录（Windows 电脑 jsonl，含全部思考过程与命令实录）已于 2026-07-12 由用户找回，全文经逐条比对核验：原 `[INFERRED]` 条目凡实录确认的已改标 `[VERIFIED·IO实录]`，并据实录补入反推不可能推出的坑（双 RPC 互补矩阵、方法级屏蔽、签名列表投毒等）。**
>
> 标注约定：
> - `[VERIFIED·IO实录]` = IO 会话命令与返回实录直接确认，可信度最高
> - `[INFERRED]` = 仍未经实录/复现验证的遗留条目，用前核实
> - `[实测·他场景]` = 本机其他项目实测过的工具性事实（见 api-keys.md / memory），可信度高
> - `[知识补充]` = SPL 通用常量与标准手法，用前顺手核实

## 0. 通道速查

| 用途 | 通道 | 要点 |
|---|---|---|
| **全量持仓快照（getProgramAccounts 大扫描）** | 公共 RPC `https://solana-rpc.publicnode.com` | 免 key；实测放行 99–117MB 级全量响应（IO 8.5 万账户约 45s，timeout 给 90s+）`[VERIFIED·IO实录]` |
| 账户历史 / 钱包持仓画像 | 公共 RPC `https://api.mainnet-beta.solana.com` | 免 key；限速紧（间隔 ≥0.12s、退避重试），本机走 clash 代理 `[实测·他场景]` |
| 单地址 / 单笔交易核验、公开标签 | Solscan 网页（`solscan.io/token/<MINT>`、`/account/<ADDR>`） | 免 key；浏览器可看，**WebFetch 直读被 Cloudflare 拦**（见死亡名单）；作报告可验证性背书 `[VERIFIED·IO实录]` |
| 全量历史转账（archive 回放） | SQD portal（见 §8，后续实战补入） | 免 key 免代理，补公共 RPC 无历史回放的洞 `[实测·他场景]` |
| 深挖升级通道（增强 API） | Helius | 自动注册被后端 bot 检测拒绝（2026-07 两次实测），需用户手动注册后把 key 放 `~/.config/helius/api-key`（chmod 600） `[实测·他场景]` |
| 量价 / 衍生品 / 解锁表 | CoinGecko / fapi.binance.com / Coinglass / DropsTab + Tokenomist | 见第 4 节 |

### 0a. 双公共 RPC 互补矩阵（关键工程事实）`[VERIFIED·IO实录]`

两个免费 RPC 各屏蔽不同方法，**必须按方法路由，单节点走不通全程**：

| 方法 | publicnode | api.mainnet-beta | 用途 |
|---|---|---|---|
| getProgramAccounts（SPL Token 大扫描） | ✅ 放行（117MB 也给） | 未试（预期拒绝） | 全量持仓快照 |
| getProgramAccounts（**Token-2022** 大扫描） | ❌ 504（无 dataSize 过滤与 dataSize=170 均超时——疑无 Token-2022 mint 二级索引） | ✅ **放行**（无 dataSize 全扫 16,186 账户 4.6MB 45s，走代理）——与 SPL 行为相反 | Token-2022 币全量快照（来源：CLUDE(Solana) 分析，2026-07-13） |
| getTokenLargestAccounts | ✅ | ❌ 持续 429（sleep 也无用） | top20 冒烟 |
| getAccountInfo / getTokenSupply | ✅ | ✅ | owner 解析、供应 |
| getMultipleAccounts | ❌ 屏蔽（`Request blocked: blocked parameter`） | ✅（上限 100 键） | 批量 owner 解析 |
| getTokenAccountsByOwner | ❌ 同上屏蔽 | ✅ | 钱包全持仓画像（§3） |
| getSignaturesForAddress / getTransaction | ⚠️ **仅近 ~3–4 天**（老账户静默返回空数组，勿误判"无历史"） | ✅ 全史（bigtable，limit 上限 1000） | 流水追踪 |

- publicnode 的屏蔽报错是 `-32602 Request blocked. Details: blocked parameter`——遇到即换 api.mainnet-beta，不要重试。
- **publicnode 的历史签名只保留 ~3–4 天（外部 CLAW/FyedK 分析实测，2026-07）**：`getSignaturesForAddress` 对更老的账户**静默返回空数组、不报错**——绝不能据此判"该地址无历史/休眠"（同 ETH mevblocker 静默丢日志坑）。凡追历史流水必走 api.mainnet-beta（bigtable 全史）；publicnode 只做当前状态大扫描与近几天流水加速。
- 批量 owner 解析的省事路线：与其在 getMultipleAccounts 上折腾，不如全量扫描时一次 `dataSlice{32,40}` 把 owner 带出来（§1）。

### 0b. 免费通道死亡名单（实测不可用，别再试）`[VERIFIED·IO实录]`

- Solscan API：`api.solscan.io`/`api-v2.solscan.io` 被 Cloudflare 拦（返回 Just a moment 页），`pro-api.solscan.io` 401 需 token；**WebFetch 抓 solscan.io 页面同样被拦**——标签只能靠 WebSearch 搜地址字符串间接命中
- `rpc.ankr.com/solana`：403 需 API key
- `solana.drpc.org`：400（外部 CLAW 考古，2026-07）
- extrnode：SSL 错误（外部 CLAW 考古，2026-07）
- solana.fm API：502（不稳，不可依赖）
- Birdeye `public-api.birdeye.so`：401 需 key
- Arkham `intel.arkm.com`/`arkm.com`：WebFetch 403，免费程序化不可用
- **GMGN 全路径（含 API 与网页）被 Cloudflare 拦**：UA+Referer 伪装无效（实测 2026-07-13，未穷尽住宅代理等绕过手段；gmgn-* skills 的正规 key 通道不受影响，本条指免 key 抓取路线）（来源：CLUDE(Solana) 分析，2026-07-13）
- web.archive.org CDX 对 `x.com/<个人页>` 常年零快照（官推旧用户名回溯此路不通；twitterscore 付费版未试）（来源：CLUDE(Solana) 分析，2026-07-13）

## 1. 全量持仓扫描（getProgramAccounts + owner 去重）

- 核心调用 `[VERIFIED·IO实录]`（打 publicnode，见 §0a）：
  ```json
  {"jsonrpc":"2.0","id":1,"method":"getProgramAccounts","params":[
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
    {"encoding":"base64",
     "dataSlice":{"offset":32,"length":40},
     "filters":[{"dataSize":165},{"memcmp":{"offset":0,"bytes":"<MINT>"}}]}
  ]}
  ```
- SPL token account 定长 165 字节，布局 `[VERIFIED·IO实录]`：`mint` 在 offset 0（32B）、`owner` 在 offset 32（32B）、`amount` 在 offset 64（8B，u64 LE）。`memcmp offset=0` 按 mint 过滤；**dataSlice 第一次就切 `{32,40}` 把 owner+amount 一起带出**——IO 实录曾先切 `{64,8}` 只拿 amount，随即发现缺 owner 被迫整段重拉 117MB，白耗一轮。
- **口径红线：token account 数 ≠ 持有人数。** Solana 特有：一个 owner 可开多个 token account（ATA + 辅助账户），必须按解析出的 owner 字段去重后才是独立持有人数（IO 实录：85,847 非零账户 → 去重 85,811 独立 owner）。两个数都要留存，分开报告 `[VERIFIED·IO实录]`。
- 容量参考 `[VERIFIED·IO实录]`：8.5 万非零账户规模，`dataSlice{32,40}` 响应 117MB / `{64,8}` 响应 99MB，publicnode 均 HTTP 200 放行，耗时约 40–45s——curl `-m 90` 起步，落盘（`-o`）后本地解析，不要过管道。getProgramAccounts **无分页**，一次全量返回；被拒/超时的备选顺序：加 dataSlice 减负 → 换 Helius `[知识补充]`。
- 坑预警（Token-2022 实测升级）`[VERIFIED·CLUDE实战]`：先 `getAccountInfo(<MINT>)` 看 mint 归属程序。若是 Token-2022（`TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb`）：①pump.fun 新币标准是 Token-2022，账户主流 dataSize=165 与 170 双形态并存，但**还有零星其他 dataSize**（CLUDE 实测 165/170 双扫漏 14 个账户 0.036% 供应，对账不闭合）——正解是 **api.mainnet-beta 无 dataSize 过滤全扫**（见 §0a Token-2022 行，publicnode 此路 504）+ `memcmp offset=0` 按 mint 过滤；②扫描器已固化 `scripts/solana/scan_token_accounts.py`（--datasizes all 或 165,170）。（来源：CLUDE(Solana) 分析，2026-07-13）
- 冒烟与交叉校验 `[VERIFIED·IO实录]`：正式扫描前先 `getTokenSupply(<MINT>)`（链上总供应）+ `getTokenLargestAccounts(<MINT>)`（top 20 token account）各打一发，扫描结果的总和与 top 榜必须能对上（IO 实录：扫描加总 799,211,891 vs getTokenSupply 799,211,890.5，个位级吻合）。
- 解码要点 `[VERIFIED·IO实录]`：dataSlice 返回 base64，解码后 `bytes[0:32]` = owner（base58 编码回地址串，可纯 Python 手写无外部依赖）、`bytes[32:40]` = amount（u64 LE 原始数）；UI 数量换算用 `getTokenSupply` 返回的 `decimals`，不要自己去 mint 账户抠字节。
- 供给基线双口径纪律 `[VERIFIED·IO实录]`：链上实查总供应（精确到个位）与 CMC/CoinGecko 流通量是两套数——流通量链上算不出来，必须借第三方口径。全文分开使用、分开标注来源，禁止混用。
- 分层默认档位（按供应量级可调）`[VERIFIED·IO实录]`：`≥100万 / 10–100万 / 1–10万 / 1千–1万 / <1千` 五档，产出集中度画像表——它是整份报告的定量地基。
- 扫描副产品 = 老鼠仓排查输入 `[VERIFIED·IO实录]`：统计 Top N 每个 owner 的 token account 数量、余额分布、建仓时间同步性，排查蚂蚁搬家式多钱包暗仓；**阴性结论也写进报告**（防读者高估链上暗仓风险）。

## 2. 托管类型判别（owner 程序 → 托管协议）

Solana 特有优势：program-owned PDA 让托管类型可以直接从账户归属读出来，无需像 EVM 那样啃字节码或赌浏览器标签。

- 两跳判别流程 `[VERIFIED·IO实录]`：
  1. 取 token account 的 owner 字段值 X（这是 authority 地址，可能是钱包也可能是 PDA）；
  2. `getAccountInfo(X)`（`dataSlice{0,0}` 零字节切片省流量）看 X 本身归哪个程序所有：`1111...`（System Program）= 普通钱包；已知托管程序 = 对应协议 PDA；返回 null（NOT_EXIST）= 从未注资的 PDA（多签 vault 常见形态）。
  - 预筛提速：PDA 必 off-curve，先做 `is_on_curve` 检查可省一半 RPC 调用 `[知识补充]`。
- 已知程序映射（本地维护"程序 ID → 托管协议"映射表，逐战累积）`[VERIFIED·IO实录]`：
  - **Squads 多签程序 `SQDS4ep65T869zMMBKyuUq6aD6EgTu8psMjkvj52pCf`** → 官方金库佐证（CEX 不会用 Squads 管钱包）。识别姿势：金库大额转出交易的 instructions 里出现该程序 ID；再叠加项目官方代币分配文档对表（分配结构、总量、年限）完成定性。
  - **Magna vesting 程序 `magnaSHyv8zzKJJmr8NSz5JXmtdGDTTFPEADmvNAwbj`** → 线性解锁托管 PDA（token account 的 owner 直接是它），特征为持续（小时级）匀速释放。
  - **Streamflow 锁仓程序 `strmRqUCoQUgGUan5YhzUZa6KqdzwX5L6FpUxfmKg5m`**（外部 CLAW 分析实测，2026-07）→ 锁仓 escrow 的 token 账户 authority = 账户自身；stream 元数据账户（owner=strm 程序）可 **raw 解码锁仓参数**：定位 mint 的 32 字节偏移 `moff` 后，`sender@moff-128`、`recipient@moff-64`，参数区 `start/deposited/period/amount_per_period/cliff` 在 `moff+148` 起的 u64 序列（flags+stream_name 紧随）。**懒人路线**：GMGN holders 的 `streamflow_status` 字段直接给 `next_unlock_time/current_locked_amount`，无需手解，与链上互验即可。
    **固定偏移速查（data_len=1104 版布局，CLUDE 实战三处互验）**`[VERIFIED·CLUDE实战]`：offset 9=创建时间、**33=end_time（到期）**、409=start、417=net_deposited、441=cliff 时间（33/409/441 对一次性 cliff 流三处同值互验）；**cancelable_by_sender/recipient、transferable_by_sender/recipient、automatic_withdrawal 标志位必读**——`period=1s+cliff_amount=全额`=一次性 cliff 到期全解，transferable=0 直接反证"受益权可场外转让"风险提示（写"锁仓可转让"之前必查此位）；automatic_withdrawal=0 则到期后币不自动离开 escrow，观察哨要按"历史到期→处置最长空窗"设过渡期防误报。解码脚本 `scripts/solana/probe_escrows.py`。（来源：CLUDE(Solana) 分析，2026-07-13）
    - **"即建即提"洗筹指纹（CLAW 实测）**：操盘方用即建即提 stream 做一跳中转，切断"老仓→新仓"的直接转账链路伪装成独立成本；识别锚点 = 提取 tx 的 **feePayer = Streamflow 自动提取服务 `wdrwhnCv4pzW8beKsbPa4S2UDZrXenjg16KJdKSpb5u`**，多笔提取共用此 feePayer = 同一批操作，据此把散落的"新钱包"归回原实体。
    - **recipient 激活状态检测**（外部 CLAW 考古，2026-07）：对 stream 的 recipient 地址查账户存在性——账户不存在（fresh keypair 从未注资）= 收款人从未动过，锁仓休眠中；配套受益人时序画像：发射后分钟级首买 = 先验知情，发射前数天新建并注资 = 预谋配置。
    - **措辞纪律：锁仓流不可撤销但可由受益人转让**（外部 CLAW 考古，2026-07）——解锁权可私下转售且不在代币转账留痕，"锁仓至 2030"≠"当前受益人持有至 2030"，涉及锁仓的结论措辞必须带此提示。
- 官方金库确认后必须追下游 `[VERIFIED·IO实录]`：高频（数小时一轮）向数十个地址小额发放 = 排放/奖励发放行为指纹，据此把"金库流出"与"抛售"区分开。

### 2a. 自建质押/托管合约判别五步法（transfer_in 大户 → 官方质押池的完整判定链）`[VERIFIED·PUB实战]`

**触发纪律：任何 transfer_in 型大户（GMGN transfer_in 标签 / 多地址转入 / 短期大额累积——表面完全符合"归集庄"画像），owner 程序两跳判别必须先于庄家定性**——PUB 实测一个 13.57% 供应的"疑似 dev 系分仓"经此流程反转为官方质押池（币的主人是各质押用户），初判若直接进报告即整案定性错误。判定五步：

1. `getAccountInfo(地址)` 看 owner 程序——非 System Program 即程序托管 PDA；
2. 对该程序账户查 `executable=true` + loader 是否 `BPFLoaderUpgradeab1e11111111111111111111111`（可升级 loader）；
3. 解析 ProgramData：程序账户 `data[4:36]` = ProgramData 地址 → 其元数据含部署/最后升级 slot（与项目公告时间对表，"公告质押上线当日部署"即时间闭环）；
4. **ProgramData `data[13:45]` = upgrade_authority——必查是否已放弃/转多签**。未放弃 = 项目方保有单方面升级程序、理论上转走全部托管资产的能力——**这必须写进报告风险章**（PUB 案：质押池托管 13.57% 供应而升级权未放弃，是全案最大结构风险，由对抗复核 RPC 抓出）；
5. 部署者（upgrade_authority 持有人）首笔 gas 溯源——来自 creator/项目方钱包即闭环"官方部署"定性。

**配套账本验证**（`scripts/solana/stake_decode.py` 自动做）：池的全部 token account 签名史 decode → 逐用户存/取账本 → **账本净额合计 vs 池链上余额精确对表**；"支付奖励"（用户取回>本金）与"自由赎回"记录是排除"归集仓伪装成质押池"的关键证据。**质押池确认后，全部持仓/留存分析必须做质押修正**（有效持仓=现货+池内份额，`replay_edges.py evolution --stake-pool`），否则质押大户被误判清仓（同 playbook §8 HYPE 教训的 Solana 特化）。（来源：PUB(Solana) 分析，2026-07-14）

## 3. 行为特征识别库（标签缺失时的兜底判据）

证据强度低于公开标签，措辞只能给到"疑似/高度疑似"。逐条 `[VERIFIED·IO实录]`：

- **月度机械解锁指纹**：每月同一日（常锚定 TGE 周年日）+ 金额分毫不差的转账。用整除关系反推 vesting 参数：固定月度额能整除出圆整总分配额与标准月数（12/24/36/48）→ 还原出合约参数。机械性是区分"合约解锁"与"主观卖出"的硬指纹。
- **整数余额 + 长期不动** = 冷储特征。
- **CEX 冷钱包动态指纹**：某大户向**已知 CEX 热钱包**调拨**多种不同代币**（一次性或数日内连续多币种）= 交易所冷→热内部补库存，据此可把"神秘大户"改判为该 CEX 冷钱包。静态指纹（整数余额）与动态指纹（多币种供热钱包）互补。
- **同时是多个热门币的最大持仓者** = CEX 归集钱包特征。免费源确证不了归属哪家时，定性降级为"疑似 CEX"并在表格明写"未能免费确证"。
- **钱包全持仓画像判托管**：`getTokenAccountsByOwner`（打 api.mainnet-beta，publicnode 屏蔽）列出钱包全部 SPL 持仓——数十个币种、多为大额圆整数、SOL 余额≈0 = 托管/金库/多签特征（正常交易钱包必须留 SOL 付 gas）。
- **高频小额、多收款人** = 运营/发薪钱包。
- **从 Coinbase Prime 提币** = 机构托管专用通道（散户不会用），直接锚定该地址背后是机构实体——集群定性的关键旁证。
- **解锁款穿透追踪的终点二分**：每笔解锁款穿透中转层追到终点——进 CEX 热钱包 = 进入可售状态（派发倾向）；进囤币钱包 = 被收走（吸筹倾向）。同一 vesting 源按月对比终点变化，可捕捉行为拐点（全案最强证据的产生方式）。
- **轮换出货通道指纹**：同一 vesting 源每月固定经同一中转、但**每月更换下游地址**（4 月进 CEX、5 月进新地址 A、6 月进新地址 B…）= 刻意轮换出货路径规避追踪，本身即"有意隐匿的处置行为"的行为证据。
- **共用中转地址（共同出纳）**：两个"独立"大户在各自解锁日把钱汇入同一个中转地址，且中转链路闭合归集到同一囤币钱包 → 高度疑似同一实体/利益联盟。措辞锁定"高度疑似"，绝不写成确权（也可能是做市商/OTC 同时服务多个独立客户）。
- **观察哨衔接**：解锁款追踪的结论要落成可证伪检验点——下一个解锁日的解锁款去向即天然观察哨，报告里预先写明"结论强化条件"与"反转条件"两个方向，下次分析直接验收。

### 3a. 流水追踪的三个 Solana 特有坑 `[VERIFIED·IO实录]`

1. **签名历史挂在 token account 上，不在 owner 钱包上**：对休眠大户的 owner 钱包查 `getSignaturesForAddress` 大概率 NO TXS（IO 实录 13 个大户 9 个如此）——他人发起的转入只"提及"token account。查代币流水一律查 token account 地址；owner 钱包有签名 ≠ 代币动过（见坑 2），token account 无签名 = 确凿休眠。
2. **签名列表投毒（address-poisoning）**：大钱包的签名列表被 pump AMM 垃圾交易污染——攻击者把知名大地址塞进自己交易的 accountKeys 或向其 ATA 转微量，制造"每天十几笔活动"假象（IO 实录 #1 金库表面日活 15 笔，decode 后本尊 IO 余额一年只动 1 次）。**活跃度判定必须 decode 交易看 pre/postTokenBalances 里本尊是否真有变动**，绝不能拿签名条数当活跃度。
3. **decode 必须按 mint 过滤**：大户签名史里混着它持有的其它代币的活动（IO 实录某 27.2M 大户最近 5 笔全是非目标代币交易）；金额解读还要防不同代币 decimals 差异造成的"天文数字转账"错觉——先按 mint 过滤再谈金额。
4. **高频钱包的 owner 级签名史稀释**（坑 1 的反面）：对 4,000+ 签名的高频 bot，owner 级取签名+均匀抽样 decode 可能**完全漏掉目标 mint 的关键买卖笔**（CLUDE 实测：两个隐鲸 160/4000 抽样 CLUDE 笔=0）。正解：查该 mint 的 token account（ATA）级签名史——只含目标币相关、通常 <30 条全量 decode；**ATA 已销户时**，从任一已知交易（哪怕只有一笔买入）的 pre/postTokenBalances 的 accountIndex 映射 accountKeys 反查出 account 地址，再对它 getSignaturesForAddress（地址签名史销户后仍可查）。固化于 `scripts/solana/probe_token_account_history.py`。（来源：CLUDE(Solana) 分析，2026-07-13）
5. **镜像 vanity dust 投毒（投毒坑 2 的升级变种）**：投毒 bot 仿冒**真实大额交易对手**的首尾字符生成 vanity 地址（仿 dev、仿中转、仿受赠户），在目标每笔操作后 16-19 秒内跟发 dust/空交易——密集同窗签名**绝不可当作钱包主人的关联操作证据**（CLUDE 实测某两仓 05-18 的 17+21 笔"同窗"全是第三方投毒）。取证一律全串比对。**反向价值**：投毒 bot 只仿真实对手，其选择性投毒本身可独立佐证两地址真有大额资金关系。（来源：CLUDE(Solana) 分析，2026-07-13）
6. **中转钱包按时间窗解码必须校验 NET≥0**：按"已知转账时间 ±N 天"窗口过滤签名再 decode 省时，但会漏窗外流入边，得出"净流出为负"的物理矛盾数（CLUDE 实测两中转 moves 只覆盖 16/54 与 14/41 笔）。中转/枢纽钱包尽量全签名解码；用窗口法必须做 NET 非负校验，不过即补扫。（来源：CLUDE(Solana) 分析，2026-07-13）
7. **owner 级签名史对"纯接收方"漏边、边表不配平**：按 owner 钱包（而非其目标币 ATA）拉签名史 decode 建转账图时，**纯接收巨仓的入账边可能整条缺失**（转入交易只提及收款 ATA，未把 owner 放进 accountKeys；owner 视角 getSignaturesForAddress 查不到）——表现为节点"流出>流入"的负净额（OPAL 拆仓网络实测：owner 版 6MLg 少 5000 万入账边、HpECTm 少 2800 万）。**正解=对不配平节点走 ATA 级补扫**（从已知边的 tx 反查出 owner 的目标币 account 地址，再 getSignaturesForAddress 该 ATA），全节点净流配平后边表才可信。已固化于 `probe_token_account_history.py` 与 1.12.0 的 `whale_deep.py`（三级 ATA 发现）。（来源：OPAL(Solana) 分析，2026-07-14）
8. **★ATA 级 trace 的 sol_delta 恒 0 → "费领取"系统性误判（资金侧盲区，后果最重的一条）**：对 token account（而非 owner 钱包）跑逐笔 trace 时，脚本取 `keys.index(w)` 的 lamports 变化——ATA 的 lamports 恒不动，`sol_delta` 恒≈0，于是"零 SOL 支出的池子流入"被顺势归类为"币本位创作者费领取"。CLUDE 增量复核实证：dev 全史 40+ 笔被旧报告标为"费领取"的主池流入，抽验 3/3 实为 dev 付整数 SOL（25-80 SOL/笔）的市场买入（主池 WSOL 侧同步增加分毫吻合）——整个"费收入账本"随之作废重算。**纪律：流入定性必须验证资金侧（owner 主钱包的 SOL 变化），不能只看币侧**；`trace_wallet.py` 已加 `owner_sol_delta` 字段（w 为 ATA 时自动补算 owner 的 lamports Δ，v2.9.0）——凡引用旧版 trace 产出的"费领取"标签一律视为未定性。（来源：CLUDE(Solana) 增量更新对抗复核，2026-07-15）
9. **"CEX 提币→精确金额买入"型定投钱包识别**：某地址每次买入前 1-2 分钟由固定热钱包**精确注入本次所需 SOL**（误差 <0.01），随即全额买入——注资方实测日交易 3,700~16,400 笔、durable-nonce 批量转账形态=CEX 提币热钱包。含义：①这是"从交易所定期提币定投"的钱包画像（非项目方马甲的典型形态）；②但资金源在 CEX 处**硬止**，链上无法证明也无法排除背后是谁——涉其归属的排除性结论措辞封顶"无罪推定"，不可写"确证独立"。（来源：CLUDE(Solana) 增量更新，2026-07-15）

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
- **pump.fun coin API**：v1（frontend-api）已死（530）；**v3 可用**——`frontend-api-v3.pump.fun` 拿代币元数据/creator/description（来源：外部 CLAW 考古，2026-07）。**v3 的 creator 履历三端点**（走 clash 代理，dev 前科调查核心通道）：①`/coins?creator=<addr>&limit=100&includeNsfw=true` = creator 名下全部发币记录；②`/users/<addr>` = 平台账号画像（用户名/关注数/是否绑定 X）——**x_username=null 可证明"链上 creator 与官推无平台级绑定"**（官推侦查的链上侧交叉证据）；③`/balances/<addr>` = 站内持仓视角（不含毕业后链上 SPL 持仓，引用须注明口径）（来源：PUB(Solana) 分析，2026-07-14）。
- **RugCheck `api.rugcheck.xyz/v1/tokens/<mint>/report`（免 key）**（外部 SGL/CLAW 分析实测，2026-07）：一次拿 topHolders（含 owner+pct+**insider 标记**）+ markets（LP 名单）+ **insiderNetworks**（转账关联的内幕簇，直接给出关联地址网络）+ launchpad——**是 `getTokenLargestAccounts` 恒 429 的最佳替代**（§0a），insider 关联比自建聚类省事，但仍按 analysis-playbook §6 硬规则复核。**坑：免费层 insiderNetworks 的 size 字段有值但 accounts 成员列表可为空**——只能当线索计数用，成员名单要自建聚类复现（来源：PUB(Solana) 分析，2026-07-14；USELESS 案 2026-07-21 再确认免费层 accounts=None）。**knownAccounts 字段实测 388 条 AMM 池/基础设施标签，可直接作算集中度前的剔除表**（来源：USELESS(Solana) 分析，2026-07-21）。
- **GMGN 正规 key 通道 CLI 的两个高价值参数**（gmgn-* skills，Cloudflare 拦的是免 key 抓取，此通道不受影响）：`token holders --tag`（smart_degen/sniper/bundler/transfer_in 等 10 类标签过滤）与 `traders --order-by profit`（盈利榜）——transfer_in 过滤结果是 §2a 判别流程的候选入口（来源：PUB(Solana) 分析，2026-07-14）。
- **Bags 平台盘专项**（外部 SGL/P0 分析，2026-07）：算集中度前必先剔平台基础设施——链上 creator 统一 `BAGSB9TpG…`（平台署名非项目方）、平台金库 `FhVo3mqL…` 恰持**每币 17% 整数配额**（单日 3000+ 签名高频机器钱包）；mint 后缀 BAGS；`bags.fm` 代币页可查创作者费累计领取额（=项目方还在乎的链上心跳）。整数配额（17.001%/20.001%）= 设计分配非市场吸筹。
- **Solscan**：地址公开标签（CEX/项目方）、逐笔交易历史核验；RPC 侧等价物为 `getSignaturesForAddress` + `getTransaction`。报告页眉声明"所有关键地址均可在 Solscan 点击验证"作为可验证性背书（注意 WebFetch 抓不了 Solscan，背书是给人手点的）`[VERIFIED·IO实录]`。
- **衍生品结构化首选 `fapi.binance.com`（币安永续 API，免 key）** `[VERIFIED·IO实录 + 2026-07-12 本机直连实测]`：
  - 资金费率史：`/fapi/v1/fundingRate?symbol=<SYM>USDT&limit=90`（返回逐 8h 费率）
  - OI 历史：`/futures/data/openInterestHist?symbol=<SYM>USDT&period=1d&limit=30`（响应还自带 `CMCCirculatingSupply` 字段，是流通量口径的又一免费来源）
  - 本机直连可用——**api.binance.com 被 451 拦但 fapi.binance.com 没拦**（与 data-api.binance.vision 同属绕拦通道）。OI 降+价升+费率中性 = 现货驱动反弹的标准证据组合。
  - **坑：/fapi/v1/fundingRate 只返回最近 500 条（约 166 天），接口首条≠永续上线日**——据此判上市时间会系统性晚判（USELESS 案据此误判币安永续上线日，靠事件线外部调研才纠正）；上线日用公告/事件线定，费率史只当近期窗口用（来源：USELESS(Solana) 分析，2026-07-21）
- **Coinglass** `coinglass.com/currencies/<SYMBOL>`：OI/费率的网页兜底（标的没上币安永续时用）`[VERIFIED·IO实录]`。
- **解锁表多源交叉** `[VERIFIED·IO实录]`：DropsTab `dropstab.com/coins/<slug>/vesting` + Tokenomist `tokenomist.ai/<slug>`（+CryptoRank/Coinglass vesting 页）+ 链上机械解锁指纹（第 3 节）互验；下一个解锁日的时间和量往往是全案最重要的单一外部信息。
- **Vybe v4 top-holders（Solana CEX 标签荒的最大补丁）**：`api.vybenetwork.xyz/v4/tokens/<mint>/top-holders?limit=1000&page=N`（header `x-api-key`，key 见 api-keys.md 第 12 节）单页 1000 个 **owner 级**持仓自带标注，实测命中 Gate/Kraken/MEXC/KuCoin/Coinbase/Crypto.com/Wintermute/KOL/MEV Bot——免费可用源里最好的 Solana CEX/机构标签面。**⚠余额字段系统性虚高不可用**（top1000 加总=总供应 113%）：只用它的标签，余额一律以链上快照为准（来源：USELESS(Solana) 分析，2026-07-21）
- **CMC data-api 全史日线**：`api.coinmarketcap.com/data-api/v3/cryptocurrency/detail/chart?id=<cmc_id>&range=ALL` 一次拿发射日起全史日级量价（USELESS 案 437 点全覆盖）——补 GeckoTerminal 公共 API 只回溯 180 天的洞；cmc_id 从币页 URL/search 端点拿（来源：USELESS(Solana) 分析，2026-07-21）
- **CoinGecko**（`/api/v3/coins/<id>/market_chart?vs_currency=usd&days=90&interval=daily`）：近 90 天日线量价结构 `[VERIFIED·IO实录]`。**坑：coin id ≠ 项目名/slug**（io.net 的 id 是 `io` 不是 `io-net`），先查 `/api/v3/coins/list` 或 search 端点确认 id；免费层限速紧，失败等 30s 重试。
- **CoinMarketCap**：流通量口径来源（与链上总供应分开标注，见第 1 节）`[VERIFIED·IO实录]`。
- **项目官方 tokenomics 文档**：分配结构对表，用于金库/排放池定性 `[VERIFIED·IO实录]`。
- **CEX Proof-of-Reserve 审计 PDF**：免费且权威的交易所链上钱包地址来源（例：Bybit 官网 PoR 审计 PDF 确证其 Solana 钱包）`[VERIFIED·IO实录]`。
- **WebSearch 裸搜地址字符串**（带引号精确匹配）：噪音大（TikTok 垃圾页居多）但能命中 PoR PDF/链上侦探推文（Onchain Lens 类）/媒体标注（BlockTempo/DA Labs 类）——Solscan API 全灭后这是免费标签的主通道；两地址可 `"A" OR "B"` 合并搜。主流 CEX 的 Solana 钱包**没有统一官方标签库**，只能拼凑，每条标注留证据链接 `[VERIFIED·IO实录]`。
- **独立反叙事信源**：对项目方利好（回购/销毁等）不直接采信，找第三方独立审查口径核查成色（销毁是公开市场买入还是排放池自燃？年销毁对冲多少年排放？启动时点是否精准卡在解锁日？）`[VERIFIED·IO实录]`。

## 5. 架构约束与观测边界（必须写进报告局限性声明）

- **免费公共 RPC 无 archive 历史回放** `[VERIFIED·IO实录]` → IO 时代的三段式架构：
  1. 当前全量快照（第 1 节）；
  2. 近 90 天逐笔交易追踪（`getSignaturesForAddress` + `getTransaction`）；
  3. 更早的筹码变迁依赖第三方图表平台口径。
  **2026-07-12 起此限制已被 §8 的 SQD portal 全量转账通道解决**——四问框架的全历史演变重放（问 3）走 SQD；三段式仍是 SQD 不可用时的降级架构，届时第 3 段依赖必须写进局限声明。
- 公共 RPC 实测参数 `[实测·他场景]`：请求间隔 ≥0.12s、走 clash 代理；退避重试 + 断点续传是采集脚本标配（IO 实录：逐笔 decode 配 1.2–1.5s 间隔 + 每请求最多 4 次重试稳定跑通）。
- **CEX 内部账本不上链**：所内换手、做市商行为完全不可见。只能靠量价结构 + 衍生品指标（OI/费率）间接推断，不对 CEX 内行为下强结论；措辞永远带"链上可观测范围内"限定 `[VERIFIED·IO实录]`。
- **Solana CEX 标签覆盖缺口**：OKX/Bitget/Upbit 等所的 Solana 钱包免费源基本查不到 → CEX 托管总量可能被系统性低估，合计数旁必须注明 `[VERIFIED·IO实录]`。
- **集群判定 = 强推断非确权**：共用中转 + 时序同步是图谱强推断，不构成确权；证据链逐条列出让读者自判，局限性单列一条 `[VERIFIED·IO实录]`。

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

1. **混合重建演变架构（长币龄标准件，两端精确、中段插值）**：①发射窗（发射日起 24-48h）用 `window_fetch.py` 拉全量边（精确——狙击/bundle 分析必须逐笔）②核心实体（庄/项目方/大户）ATA 级全流水（`whale_deep.py`，精确）③中段日级锚点前向填充（`anchor_sampler.py`）④**当前快照封口 + 末日快照注入**——把 data_cutoff 日全量快照作为最后一个锚点注入序列，修"清仓发生在锚点观测窗外则旧值永久残留"的系统性尾部误差。图 1/图 2 由 ①②③④ 合成，散户=残差；精度声明照 §9 写进局限性（来源：USELESS(Solana) 分析，2026-07-21）。
2. **SQD 高密度期定向拉取用小段+并发（`window_fetch.py`）**：密集期（发射窗/事件日）正解=**2000 slot 小段 × 8 并发**，失败段落 `.gaps.json`（必须为空才算完整）。反面教训：fetch_sqd_transfers 的 50K 大段在发射期反复 curl 超时截断重试，120 分钟只推进 3.4 链上小时；小段版 29 秒拉完 1 万 slot、发射日 24h（16.5 万边）82 分钟零缺口。
3. **日级锚点采样（`anchor_sampler.py`）与它的观测边界（★阴性依据禁用）**：从新到旧滚动校准 slot↔ts（分段线性外推、漂移 >4h 自动重估，435 天约 5s/天）。**⚠观测窗真相**：名义 1h 窗（9000 slot）在高活跃期因响应截断实际仅 ~3.6 分钟，且 SQD tokenBalances 只记**发生变动**的账户——静止大户被系统性漏观测。因此**锚点单独不可作任何"某地址没动/没持仓"的阴性依据**，阴性结论必须快照或全流水兜底；锚点只用于正向变动观测与序列插值（对抗复核实测抓出，来源：USELESS(Solana) 分析，2026-07-21）。
4. **publicnode 大扫描死角补充（§0a/§1 的边界）**：13.5 万 token account 量级的 mint，publicnode getProgramAccounts 恒 504（dataSlice 也救不回）；**api.mainnet-beta 做 SPL 大扫描会静默返回空结果**（不报错——危险，靠对账关卡拦住，勿当"该 mint 无账户"）。分片扫描（`scan_sharded.py`，amount 低位字节递归分片）可行但两个坑：①owner 位置 memcmp 必须整 32 字节（1 字节分片语法合法但过滤不生效）②零余额账户 8 字节 amount 全零、全部堆在全零前缀片——递归下钻全零前缀至 8 字节终点片直接跳过（分析只要非零余额）。USELESS 案分片全量未跑完（publicnode 间歇 504），对账改用"8 样本独立单查 + top20 对表"替代过关——**分片器待后续标的全量验证**。
5. **whale_deep 按地址频率分派（先估频再选通道）**：深挖前先 getSignaturesForAddress 拉一页估频——高频地址（creator 类，签名 7 万+）ATA 级全 decode 需数小时/地址不可行，改**事件窗定向拉**（只 decode 关键时间窗）；低频囤仓户（15-172 笔）全量 decode 秒-分钟级。一刀切全量 decode 会把预算烧在单个高频地址上（来源：USELESS(Solana) 分析，2026-07-21）。
6. **letsbonk 平台币三件套（§8.5/§8.6 的平台变体，vs pump.fun 差异）**：①铸造边 2 条——curve 拿大头 + dev 直分一笔，且 **dev-buy 可在数秒内卖回**（实测 6 秒）制造"creator 已清仓"表象——creator 状态判定必须看直分笔的后续流向，不能只看当前余额；②**creator fee 走 Raydium Lock 的 burn&earn harvest 账本**（非 pump.fun 费领取模式）——费农收入=真实收益引擎，dev"弃盘与否"必查 harvest 流水；③毕业迁移约 20.7% 供应入 Raydium 池（来源：USELESS(Solana) 分析，2026-07-21）。
