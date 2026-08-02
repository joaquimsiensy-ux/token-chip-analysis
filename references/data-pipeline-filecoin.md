# Filecoin (FIL) 数据管线参考

> 适用场景：对 Filecoin 原生代币做筹码分析的数据采集与口径处理。主力数据源 = Filfox 浏览器 API（免费、无 key、实测无限速），价格与元数据 = CoinGecko 免费 API，全程零付费额度。
> 注意：第 4 节的口径修正全部是 Filfox 这一家 API 的私有返回约定，不是链上通用语义——换任何数据源（Filscan、Glif、Lotus 直连等）都要重新核定。

> 来源声明：本册规则除特别标注外，均源自 FIL(Filecoin) 分析实测（2026-07），不再逐条标注。

> 发布边界：现有 `fetch_data.py` 只能产 `restricted/top-200-windowed` 数据（富豪榜前 200、近 6 个月、每地址最多 3000 笔），不得称“Filecoin 全量重放”。每页必须有连续完成原因；网络失败不落正式缓存，最终 `collection_manifest.json` 显式记录 restricted scope 与限制，并以哈希引用官方 ID 扫描子阶段 receipt。

## 0. 开工检查清单（每条都有对应踩坑记录，别跳）

- [ ] HTTP 客户端：用 `subprocess.run(['curl','-s',...])` 走系统证书链，禁止 urllib 裸连 HTTPS（本机 Python 缺 CA 链会 `SSL: CERTIFICATE_VERIFY_FAILED`，曾白跑一整轮冒烟约 5 分钟）。
- [ ] 富豪榜分页只用 `pageSize` 参数，`count` 参数已失效且口径不同（第 4 节坑 ①）。
- [ ] 冒烟阶段必须同时验证「抓得到」和「口径对」：唯一性断言 + 跨页自洽校验。
- [ ] 流水三坑修正内置进脚本：带符号求和、五元组去重、互转边 abs(value) 去重键（第 4 节坑 ②③）。
- [ ] 地址字符串一律取自落盘 JSON，禁止从终端截断输出复制补全（第 6 节）。
- [ ] 全量抓取放后台跑（单轮实耗 34–70 分钟），等待期间并行做地址考证等不依赖全量数据的工作。

## 1. 数据面总览

### 1.1 Filfox API（主力，base = `https://filfox.info/api/v1`）

| 端点 | 拿什么 | 关键字段 |
|---|---|---|
| `GET /overview` | 全网供给与快照 | totalSupply / circulatingSupply / multisig 锁仓总量 / 活跃矿工数 / 价格 |
| `GET /rich-list?pageSize=100&page=N` | 富豪榜（全量口径） | balance / availableBalance / createHeight / lastSeen / actor |
| `GET /address/<addr>` | 地址详情 | 官方标签 tag / multisig 锁仓明细 / ownedMiners / transferCount |
| `GET /address/<addr>/transfers?pageSize=100&page=N` | 逐笔转账流水 | from / to / value / timestamp / message / type |

要点：
- 供给口径自检：拿到 overview 后先验证总量恒等式 `totalSupply = vested + mined + reserveDisbursed`（与 Lotus 官方口径一致）；不满足说明抓取或口径理解有误，先修管线再分析。
- 富豪榜 actor 字段区分 account / storageminer / multisig / evm；全量榜前 200 约含 140 account + 40 storageminer + 14 multisig + 若干 evm，只有全量口径才能把「可流通筹码」和「锁定筹码」分开。
- 地址详情对不存在的地址返回 HTTP 404 + JSON（statusCode:404），不会中断批量扫描，按 statusCode 跳过即可，可放心扫段。
- 转账流水单页上限 100 条，倒序返回（最新在前）。
- 最早流水定位：先读 totalCount，直接跳最后 1–2 页，无需顺序翻完——首笔资金来源（funder）是聚类的核心输入。

冒烟示例（写脚本前先手动跑通）：

```bash
curl -s 'https://filfox.info/api/v1/overview'
curl -s 'https://filfox.info/api/v1/rich-list?pageSize=100&page=0'
curl -s 'https://filfox.info/api/v1/address/f0121'
curl -s 'https://filfox.info/api/v1/address/f0121/transfers?pageSize=100&page=0'
```

### 1.2 CoinGecko（元数据与价格，免费无 key）

- 元数据：`GET https://api.coingecko.com/api/v3/coins/filecoin`。
- 日线价格：`GET /coins/filecoin/market_chart?vs_currency=usd&days=180&interval=daily`，够做近 6 个月价格与链上净流量的叠加分析。

### 1.3 限速与吞吐（实测）

- Filfox 连发 8 次全部 HTTP 200，未观察到任何限速；脚本节流设 THROTTLE=0.1s 即可。
- 每次 curl 新建 TLS 连接自带约 0.3–0.5s 开销，叠加节流后实际吞吐约 2–3 req/s——瓶颈在连接开销不在限速。
- 规模参考：前 200 地址全量抓取（详情 + 多页流水）单轮后台任务实耗 34–70 分钟；三个后台任务（首轮抓取 / 并行考证 / 补抓）从发起到完成均超 30 分钟。

## 2. 官方地址库：扫创世 actor ID 段（免费拿项目方地址库的关键一招）

- 手法：对 f00–f0126 逐个调 `GET /address/f0<N>`，批量收集所有带官方 tag 的地址。
- 原理：Filecoin actor ID 按创建顺序递增，创世实体集中在低位 ID 段。EVM/Solana 地址是哈希/公钥派生，没有低位 ID 可扫——此招仅限 Filecoin。
- 已确认官方标签：f0121 = Filecoin Foundation；f0117–f0120 = Protocol Labs 系列；f090 = 挖矿储备；段内另有 Faucet、Burn 等系统地址。
- 不存在的 ID 返回 404 JSON，脚本按 statusCode 跳过，不影响扫描完整性。
- 用途：这批地址是「项目方 vs 市场」资金流向判定的锚点，也是聚类里官方体系的种子标签。

## 3. multisig 锁仓明细：链上直读，无需外部解锁表

- `GET /address/<multisig地址>` 直接返回 vesting 原生字段：initialBalance、unlock 起止 epoch、当前可用余额与锁定余额。
- 官方 vesting 因此可全部链上直读验证，不依赖任何第三方解锁表——vesting 是 Filecoin multisig actor 的协议原生能力，可信度高于外部数据源。
- 对比其他链：EVM 的 vesting 是各家自写合约，只能靠第三方解锁表 + 行为指纹反推；Filecoin 无此负担。
- 操作要求：富豪榜里所有 actor=multisig 的条目（前 200 中约 14 个）逐个走地址详情读锁仓字段，才能把「锁定筹码」从「可流通筹码」中剥出来。

## 4. Filfox 口径三坑与专用处理

### 坑 ①：rich-list 的 `count` 分页参数已失效

- 症状：`count=50&page=0..3` 四页返回同样的前 50 条 → 榜单只有 50 个唯一地址、同一地址出现 4 次、占比统计全错。
- 更隐蔽的一层：count 口径只返回过滤后的 account 榜，漏掉 storageminer / multisig / evm，无法区分可流通与锁定筹码。
- 解法：一律用 `pageSize` 分页（pageSize=100&page=0/1 取前 200）。
- 自检两连（冒烟阶段就做，别等分析阶段才发现）：
  - 抓榜后立即 assert 无重复地址。
  - 跨页自洽校验：`pageSize=100&page=1` 的第 51 条 == `pageSize=50&page=3` 的第 1 条。
- 代价参考：冒烟只验「抓得到」没验「口径对」，曾导致一轮 34 分钟全量抓取整体作废、再花 70 分钟补抓约 150 个地址，合计浪费约 1.5 小时挂钟时间。

### 坑 ②：transfers 的 value 自带方向符号

- 约定：流入为正、流出为负；净流量 = 直接对带符号 value 求和，不要再按 type 判方向。
- 反面教材：按 `type=="receive"` 把 value 当正数累加，方向与幅度双错——曾造成单地址净流量被虚算至 1.7 倍、另一地址净买入方向整体算反。

### 坑 ③：倒序分页漂移 + 同笔双计

- 漂移：抓取期间出新块使倒序分页整体后移，同一笔流水重复入库；入库前必须按 `(message, type, from, to, value)` 五元组全局去重。
- 双计：同一笔转账在双方地址的流水中各出现一次且符号相反；做互转边统计时去重键必须用 `abs(value)`，否则边权重翻倍。

### 补充 A：高频热钱包流水截断的补偿

- 交易所热钱包 transferCount 可达 51 万笔量级，逐笔抓完不现实：设截断上限，并在落盘数据里记 truncated 标志。
- 截断地址的账面净流量必然低估，必须用「链上余额变化」（期初/期末 balance 差）独立复核补偿；实测截断地址的账面口径与余额复核口径可差出千万级 FIL。
- 通用纪律：净流量类关键数字一律做余额变化交叉验证；两口径对不上，先查数据管线再下结论。

## 5. 采集与分析脚本用法（scripts/filecoin/）

执行顺序：`fetch_data.py --smoke 10` → 冒烟自检通过 → 全量后台跑 → `analyze_base.py` → `cluster.py`；中途冒出新地址用 `fetch_extra.py` 补抓。

- `fetch_data.py` — 主抓取：富豪榜前 200（pageSize 口径）→ 每地址详情 + 近 6 月流水 + 最早流水 → 创世 ID 段官方标签扫描 → CoinGecko 180 天价格。要点：
  - 官方 ID `f00–f0160` 扫描以 `requested/succeeded/not_found/failed` 四桶落 `official_scan_receipt.json`；404 进 not_found，网络/API 错误进 failed。任一 failed 都 BLOCK 且非零退出，不写正式 `official_scan.json`。`official_scan_progress.json` 保留已成功与待重试 ID，重跑只补查 failed；旧版孤立 `official_scan.json` 不再能短路。
  - 全部请求走 subprocess 调系统 curl，规避本机 Python SSL 证书坑（另一条路是 certifi，本管线选了 curl）。
  - `--smoke N`：先抓前 N 名冒烟（建议 N=10），冒烟必须包含第 4 节坑 ① 的唯一性断言与跨页自洽校验。
  - 每地址落盘独立 JSON 作断点文件；修口径后重跑只补抓新增地址，不重抓已有的。
  - 高频地址自动截断并打 truncated 标志，下游必须按补充 A 做余额复核补偿。
- `fetch_extra.py` — 临时补抓个别地址的小脚本，分析中途新发现的对手方地址用它，不重跑主抓取。
- `analyze_base.py` — 基础量化：每地址近 6 月净流量（带符号求和 + 五元组去重）、首笔资金来源 funder 分组、top200 互转边（abs(value) 去重键）、官方 multisig 统计；内置富豪榜唯一性断言。第 4 节全部口径修正已内含——改动前先读懂原有修正逻辑，别顺手删掉。
- `cluster.py` — 关联聚类：共同资金来源 + 直接互转等证据 → 连通分量 + 证据打分；输入依赖 analyze_base 的产物格式，两者要配套改。

## 6. FIL 特有坑

### f0/f1 地址双别名

- 同一账户存在两个等价地址形态：f0 短 actor ID 与 f1/f3 公钥派生 robust 地址，不同接口/字段返回的形态可能不一致。
- 处理：抓地址详情时同时记录两种形态、建立双向映射；聚类与去重前统一主键，否则同一账户会被拆成两个「地址」重复计数。

### 地址完整性纪律（截断补全必错）

- 地址一律从落盘 JSON 取完整字符串。终端打印会截断到约 25 字符，凭记忆补全必错——Filecoin 地址末段是校验和，补全出来的是不存在或错误的地址，表现为连环失败三部曲：JSON 解析报错 → 查到 balance=0 的空地址 → 404。
- bash 双引号内嵌 `python -c` 再拼 curl 的转义极易出错；复杂请求直接写成 python 脚本，脚本内 `subprocess.run(['curl', ...])`。

### 地址投毒（address poisoning / vanity 前缀伪装）

- Filecoin 上存在投毒攻击：攻击者生成与真实对手方前缀相同的 vanity 地址，向大户发尘埃转账。按前缀匹配或按小额流水做资金上游归因会中招——曾有 3 个投毒地址被初版误判为大户资金上游，靠对抗复核识破后剔除。
- 防御三条：
  - 资金上游归因只认大额转账，设金额阈值过滤尘埃流水。
  - 一律比对完整地址，禁止任何形式的前缀/后缀匹配。
  - 地址关联类结论写入报告前必须过一轮对抗复核。

## 7. 交付前链上复核（廉价且必做）

- 报告引用的关键转账（抽 3 笔量级即可）交付前用脚本自动与 Filfox 实时 API 比对日期/金额/对手方，全部一致才交付。
- 净流量、实体持仓占比等关键数字用「链上余额变化」独立口径复核（见第 4 节补充 A），账面流水口径与余额口径互为校验。
