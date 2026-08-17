# EVM 链数据管道 · 采集通道与决策树（data-pipeline-evm 分册 1/3）

> 母文档：`data-pipeline-evm.md`（薄路由索引页，文档级引言与时效纪律见索引页）。本册覆盖 **§1 全量转账通道决策树 / §2 死亡名单 / §3 各通道操作细节 / §6 BSC 专属坑表 / §7 零门槛免注册通道**；§4/§8/§9/§10 见 `data-pipeline-evm-sources.md`，§5/§11/§12 见 `data-pipeline-evm-recon.md`。正文 §N 交叉引用一律为母文档节号（本册未含的按索引页对照表跳册）。

## 本册路由

- §1 通道决策树；§2 死亡名单；§3 通道操作；§6 BSC 坑表；§7 零门槛通道。

## 1. 全量转账通道决策树（BSC）

先估数据量（预估纪律见 §6），再选通道：

```
预估 Transfer 总条数？（先抽样发射首月外推，报保守上限）
├─ 任何量级【v3.11.2 起默认,Starter 付费 key 在役】
│     → ① HyperSync 官方客户端 v2【首选】（scripts/evm/fetch_hypersync_v2.py，
│          Rust 自动并发+Parquet 直写）
│       ② v1 手写轮询【兜底】（fetch_hypersync.py，无 pip 环境/逐字段调试用）
├─ < 300 万条且 ≤60 天新盘（手头无任何 key 的冷启动）→ bloXroute getLogs 分段扫描（scripts/evm/scan_bloxroute_seg.py）
├─ HyperSync 平台级故障 / 数仓切源正式替代 → SQD Portal 薄采集器（须原生 v2 receipt）（fetch_sqd_evm.py，免 key）
├─ HyperSync 结果可疑 / 对账 gate 挂了后的独立诊断【仅 ETH 主网，非正式 channel】→ BigQuery goog 官方公共数据集
│     （fetch_bigquery.py,定向日期查询 ~12GiB/次,免费 1TiB/月;定位=备用+复核,不用于常态采集,详见 §11）
├─ 跨链代币的 ETH 主网侧补充【非正式 channel】→ Etherscan V2 免费 key（仅 chainid=1，fetch_etherscan.py）
└─ 任何情况下都别碰 ──→ §2 死亡名单端点（禁止重探）

落盘与合并纪律（v3.11.2 起）：小样本多源产物经 `transfers_lib.py merge` 合并（默认最多
100 万行，超过即拒）；正式大数据统一走 `replay_stream.py` 的 DuckDB 流式入口，禁止把
亿级事件交给内存排序。两种入口都必须保留 input manifest。重叠块区
集合级对账，不等即 exit(3) fail-closed；
标准 8 列含 block_hash，去重键 (block_hash,tx,log_index) 防链重组。
channels.json 的 path 字段语义（2026-07-25 SPX6900 实测坑）：hypersync_v2 通道的 path
指向 **v2 采集根目录**（如 data/v2，内含分段 parquet 全集），**不是单次 run 子目录**——
分段采集/断点续拉的币该目录下有多段产物，把某段 run 目录填进 path 会静默漏段；
续拉与重放引用 channels.json 时按根目录读全段。

**channels.json v2 完整性契约（P0 硬闸）**：三个 replay 入口在读取任何事件前共用
`channels_preflight.py`。顶层必须有 `schema=evm-channels/v2`、`token`、
`expected_from`、`expected_to`；每段必须有 `path/format/lo/hi/tag/receipt`。排序后首尾
必须等于全局边界，相邻段必须 `next.lo == prev.hi`。通道 receipt schema 为
`evm-channel-receipt/v2`，必须绑定同一 token/tag/区间、数据统计及当前文件哈希。CSV 还必须
引用 adapter 成功收尾时原生生成的 `evm-collector-run/v2`：collector 当前脚本哈希、provider、
冻结块界、SQD provider 哨兵行给出的严格前进且到达目标的扫描前沿，以及连续 segment
output-prefix hash chain 全部重验。SQD 实测在零匹配区间也返回首末 header-only 哨兵，故空正文
属于协议异常，不能推进扫描前沿；Alchemy 仅有分页 pageKey，没有 provider 侧块进度证据。
空段不接受操作者文字证明；同一 native receipt chain 本身必须证明扫描到冻结上界。预检成功或
阻断都落 `<out-dir>/channels_preflight.json`，BLOCK 必须非零退出。PASS 产物还必须记录当前
`channels_preflight.py` producer、manifest 哈希、每段 channel/native collector receipt 哈希以及
实际 CSV/Parquet `inputs` 的 path/size/SHA-256；三个 replay 引擎在 `replay_stats.json` 记录当前
引擎 producer，并绑定该 preflight、完全相同的 inputs 和 `balances_final.json` 输出。G8 emitter
会从 manifest 重新运行同一个 preflight validator 并重验上述链，不能把两份互相咬合的 JSON
当作采集/重放执行证明。旧 preflight/stats 不允许手工补 producer 或哈希：必须让对应生产 replay
引擎从 `channels.json` 重新预检并完整重放，生成新 stats 后再 emit identity receipt。

正式 HyperSync CSV 首段必须是运行前不存在的新文件：

```bash
python3 scripts/evm/fetch_hypersync.py <lo> --token-file ~/.config/hypersync/token --token-addr 0x... \
  --to-block <hi排他> --out data/full.csv --receipt data/full.collector.json
python3 scripts/evm/make_channel_receipt.py \
  --data data/full.csv --format v1csv --token 0x... --lo <lo> --hi <hi> --tag primary \
  --collector-receipt data/full.collector.json --out data/full.receipt.json
```

延长冻结上界时，collector 必须带 `--resume-receipt data/full.collector.json`；它先重验旧
CSV 的每个历史 prefix，再从前一 `requested_to` 续采并发布加长 chain。没有前驱 receipt 的
**存量 legacy CSV** 不可补签或手工迁移：另名归档，重新从冻结 `lo` 采到 `hi`。SQD 的正式
fresh-output 命令同样带 `--receipt`；Alchemy/BigQuery/bloXroute/Etherscan 只作诊断或补充。
数据变化后必须由生产 collector 重采/续采，再重跑 `make_channel_receipt.py`；测试 fixture 或
手搓 JSON 不构成迁移工具。v2 Parquet 通道则继续由 native done v3 +
`make_channel_receipt.py --format v2` 生成，无 `--collector-receipt` 参数。

```json
{"schema":"evm-channels/v2","token":"0x...","expected_from":0,"expected_to":200,
 "channels":[
   {"path":"data/part0.csv","format":"v1csv","lo":0,"hi":100,"tag":"p0",
    "receipt":"data/part0.receipt.json"},
   {"path":"data/v2","format":"v2","lo":100,"hi":200,"tag":"p1",
    "receipt":"data/part1.receipt.json"}]}
```
```

分叉依据：bloXroute 8 并发扫 249.6 万行约 80 分钟，量级再大耗时不可控且免注册通道无 SLA；HyperSync 免费层拉 1568 万条约 5.2 小时（OPN/SIREN，07）；**Starter 付费档（$70/月,100rpm+overage 5x=500rpm）+官方客户端后，同类量级压至半小时内**（v3.11.2 POC，2026-07-21，详见下表）。

配套缓存（transfers_lib.py，存 `~/.cache/chip-analysis/`，跨币跨会话复用）：
- **部署块缓存** `get_deploy_block(chain, token, fetch_fn)`——每币首次定位后永存，免每次从 0 扫空段；
- **时间戳锚点库** `add_anchors(chain, pairs)` / `estimate_ts`——按链累积复用，v2 产物的 blocks.parquet (number,timestamp) 直接喂入，新币插值免重复采锚点（⚠发射窗口精确配价仍禁用插值，恒定偏差坑见 §6）。

**增量拉取（研报更新/补尾场景）**：v2 对增量天然友好——同一 run 根目录下新起 run（from_block=上次 done.json 的 next_block）即可；**补丁段重叠核验法**：对怀疑有洞的区间补拉一段落盘独立 patch 目录，按 (tx,log_index) 键与主数据对比，零差即证该段完整、有差即用 patch 覆盖。

**存量 HyperSync v2 目录迁移（增量更新前置）**：2026-08-02 之前的
`hypersync-v2-done/v2` 没有 `files` 实体回执，不得直接被新续拉器信任；更早的
太古 done（无 `schema` 字段、只有 from_block/next_block/token/url 五键，APU 案
ANOM-012 实证形态）同样由本命令迁移——parquet 列集经实读硬验与现行采集器查询
形态一致后重建全部边界与文件指纹。QUQ、
PYTHIA、TROLL 类存量币在下次增量采集或投后更新前，先对该币的 v2
采集根目录依次执行显式恢复与迁移（存量目录一律不由升级过程自动改动）：

```bash
python3 scripts/evm/fetch_hypersync_v2.py \
  --recover-identity --outdir <案目录/data/v2>
python3 scripts/evm/fetch_hypersync_v2.py \
  --refresh-manifests --outdir <案目录/data/v2>
```

两种模式都不访问 HyperSync、不需要 API token。recover 先要求根目录只含合法编号的
`run_*`，且每段恰有普通文件 done.json/logs.parquet/blocks.parquet 三件套；拒绝 symlink、
孤儿文件、空 run 与未识别残件，并重验 token/url/query 同一性和 Parquet 实物，随后签发
`hypersync-capture-identity/v2`（`recovered=true`、`lineage=unknown`）。refresh 再对全部
`run_*/done.json` 做两阶段重验，
逐 run 实读 logs/blocks Parquet 的 schema、行数、块范围、logs→blocks 关联完整性、
size 与 SHA-256；全部通过后才原子将 v2/v3/pre-schema done 升为
`hypersync-v2-done/v4`，旧段明确记为 `legacy-unattributed` 并绑定迁移前整份 done 字节哈希
及 migrator 身份。多段 pre-schema 目录须显式加 `--capture-from <冻结下界>`，禁止猜测
共同起点。任一 run
缺文件、截断、schema 错或区间/关联异常时，命令列出具体 `run_*` 并非零退出，
**不改写任何 done.json**。只有迁移 PASS 后才运行常规 fetch 命令从最大已验
`next_block` 续拉；迁移失败不得删 done 绕过，应重拉损坏 run。

| 通道 | 注册要求 | 限速实测 | 吞吐实测 | 断点续传 | 脚本 | 来源 |
|---|---|---|---|---|---|---|
| **HyperSync 官方客户端 v2（Starter 付费档,现役首选）** | Starter $70/月 | 官方客户端并发 | — | done manifest v4 绑定 token/url/capture bounds/query/client、逐段 collector，并对 logs/blocks Parquet 分别记 size/rows/min/max/sha256；续传与 staged skip 都重验可读性/schema/范围/哈希 | fetch_hypersync_v2.py | （2026-08-17 加固） |
| envio HyperSync v1 手写轮询（兜底） | 同上 key 通用 | 付费买到的是高峰稳定性,大标的提速必须换 v2 | — | from_block 起点 + 增量写 CSV（v3.11.2 起新文件 8 列含 block_hash,老 7 列续拉自动兼容） | fetch_hypersync.py | （SIREN 07；哈基米 429 实测 07-18；v3.11.2 付费实测 07-21） |
| SQD Portal 薄采集器（故障预案+正式替代；须 `--receipt`） | 免 key 免注册（portal.sqd.dev 公共端点;注册 gateway key 免费可选更稳） | 公共限流 20 请求/10s,sleep 0.5 保守;无自助付费档（官网 pricing coming soon,2026-07-21 核实） | ~280 条/s——平时不跑,HyperSync 平台级故障或数仓切源准入对照时才上;**对账关卡（余额对账/时间抽查）的代表日双源对照亦用它**（独立索引商） | CSV 末行块+1 | fetch_sqd_evm.py | （v3.11.2,2026-07-21） |
| BigQuery goog 官方公共数据集（诊断复核、**非正式 channel，仅 ETH**） | Google 账号 OAuth 一次(凭据缓存后免弹窗)+GCP sandbox 项目(免绑卡,见 api-keys.md 第 17 节「Google Cloud / BigQuery」) | 免费 1 TiB/月查询量;熔断线 config max_scan_gib(默认 200GiB) | 服务端过滤只回传命中行,13 万行 ~1 分钟;定向日期查询 ~12GiB/次≈月额度可复核 85 次 | 无需(按日期范围幂等重查) | fetch_bigquery.py | （v3.12.1 准入实证,2026-07-21） |
| Alchemy getAssetTransfers（仅探索采集，不支持正式 receipt） | 免费 key（dashboard.alchemy.com 国内直连） | 平台级 429 全局限流，高峰期可整夜不可用 | 1000 条/页 | 读 CSV 末行区块置 fromBlock（勿依赖 pageKey） | fetch_alchemy.py | （SIREN，07） |
| bloXroute getLogs（近期原始分片，**非正式 channel**） | 免注册 | ⚠**并发承受力已变**（2026-07-19 SIREN 实测）：8 并发 curl 线程池整体挂死零产出、requests 3 线程 0.5s 间隔稳定；历史窗口比 07-18 更宽（下界块 100.1M~101.5M ≈55-60 天，二分探测）——**窗口是动态的，用前必二分**。降级为"近期段快扫" | requests 3 线程 万块段 ~50 段/4 分钟（SIREN 396 万条约 30 分钟）；旧 8 并发数字已不可复现 | done-segments 清单 + 失败段补扫 | scan_bloxroute_seg.py（requests.Session） | （OPN 07；哈基米 窗口实测 07-18；SIREN 并发/窗口实测 07-19） |
| Etherscan V2（补充证据、**非正式 channel，仅 ETH 主网**） | 用户免费 key | 免费层限速未成瓶颈 | tokentx 每页 10000 条 | 按返回末行 block 续页 | fetch_etherscan.py | （OPN，07） |
| envio HyperSync **ETH 主网**（eth.hypersync.xyz） | 同上免费 token | — | — | 同 BSC 版（fetch_hypersync 断点续传版） | fetch_hypersync.py | — |

**替代 CSV 正式资格**：只有 `fetch_sqd_evm.py` 在显式冻结块界、输出与 receipt 路径运行前均不存在并成功收尾时，可用 `--receipt` 产生 `evm-collector-run/v2`；preflight 会校验当前或 git 考证的历史登记 adapter 脚本哈希（`collector_history.py`）。Alchemy 仅有分页 pageKey、没有 provider 侧块进度证据，v2 块游标语义不成立，故已降级为仅探索采集并除名正式通道；恢复资格需升版为分型收据。BigQuery 是日期切片复核，bloXroute 是近期分片，Etherscan 是补充 API；这些非正式采集器代码均声明 `FORMAL_CHANNEL_ELIGIBLE = False`，不得写入正式 `channels.json`。旧 CSV 无法升级：另名归档后由 SQD 生产 adapter 从冻结下界重采。

## 2. 死亡名单（实测不可用，3 个月内禁止重探）

免费匿名的 BSC 历史 getLogs 通道整体已死，唯一例外是 bloXroute。（OPN/SIREN，07）

> 时效纪律（v1.3）：本表实测于 2026-07。免费层政策季度级变化——任何条目距实测超过 3 个月后若确有需要，允许花 1 分钟小请求重探一次，复活/仍死都把本表日期更新；3 个月内维持禁令（重探是历史上最大的轮次浪费源之一）。否定性结论的入库纪律见 retrospective.md 红线 4。

| 端点/通道 | 实测症状 | 来源 |
|---|---|---|
| bsc-dataseed 系（bnbchain 官方） | getLogs 连 span=100 都报 -32005 limit exceeded；仅可做轻查询（见 §6） | （OPN/SIREN，07） |
| publicnode | 老区块要求 archive token | （OPN/SIREN，07） |
| dRPC 匿名（bsc.drpc.org） | 限 10000 块/次且 "Too many request" 频发，全链扫必卡死在重试 | （OPN/SIREN，07） |
| dRPC 注册免费 key（lb.drpc.org） | 持续 429；>10000 块不支持；network=bsc-archive / bsc-full 是非法名——注册了也没用 | （SIREN，07） |
| Alchemy eth_getLogs 免费层 | 限 10 个区块范围；但同一 key 换 alchemy_getAssetTransfers 方法即可用，别因此弃掉 key | （SIREN，07） |
| Etherscan 免费 key + chainid=56 | "Free API access is not supported for this chain"，两次会话都把它当过首选然后报废 | （OPN/SIREN，07） |
| api.bscscan.com v1 | 已 deprecated | （OPN，07） |
| 1rpc.io | getLogs 限 50 块 | （OPN/SIREN，07） |
| blastapi | getLogs 限 10 块 | （OPN/SIREN，07） |
| meowrpc | 不支持 getLogs | （OPN，07） |
| llamarpc / blockpi | 返回异常 | （OPN，07） |
| zan.top | 要注册 | （OPN，07） |
| 48.club | 限 5000 块且 "header not found" 不稳定 ⚠️**并非全废，见 §7.1**：外部会话实测它是**唯一可用的免费历史 getLogs 端点**，"不稳定"真相=只保留最近 ~6 天块，用于 6 天内新盘可用 | （OPN，07；外部 CZ/TCC 考古修正，07） |
| nodies / ankr / merkle / omniatech | 限范围/限量/限流，均无法扫全史 | （OPN/SIREN，07） |
| Routescan | 不支持 BSC（`chain not supported`） | （外部 CZ 考古，07） |
| `api-legacy.bubblemaps.io` | 返回 400——Bubblemaps legacy API 已死（BSC/ETH 两场会话独立验证） | （外部 CZ/ASTEROID 考古，07） |
| CryptoCompare min-api histoday | 已并入 CoinDesk、强制要求 API key——免 key 历史日K时代结束；TGE 老币全史价格改走 Gate 现货日K（§4） | （SQD，07-20） |

## 3. 各通道操作细节

### 3.1 envio HyperSync（scripts/evm/fetch_hypersync.py）
- POST `https://bsc.hypersync.xyz/query`；header `Authorization: Bearer {TOKEN}`；body 含 `from_block`、`logs: [{address, topics}]`、`field_selection`。（SIREN，07）
- 匿名（无 token）已不可用；token 让用户到 app.envio.dev 注册——控制台在用户（中国）网络打不开需 VPN，但 API 端点直连可用，"控制台打不开 ≠ API 不可用"。（SIREN，07）
- archive_height 到最新块，全史无缺口；换 token 地址与链子域名即可用于其他 HyperSync 支持链。（SIREN，07）
- token 取用优先级为：显式 `--token-file` > `HYPERSYNC_TOKEN` > 默认 `~/.config/hypersync/token`；三支 v1 脚本与现役 v2 入口都禁止位置参数明文 token，非法输入也不得把 secret 回显到 stdout/stderr。换 key 时原始存放文件与 `~/.claude/api-keys.md` §1 登记同步。
- **transactions 端点做 BNB 注资溯源**：body `{"transactions":[{"to":[addr]}],"field_selection":{"transaction":["block_number","from","to","value"]}}`（value 为 hex）——单址全链入金一次查询 ~2.3s 到 tip，比逐块扫快几个量级；⚠25 址×全链批量会 10 分钟超时，可用姿势=关键地址单址逐查 / 发射窗小块段批量（from/to_block 圈定）。（哈基米，07-18）
- 【历史降级·新案禁用】分段多进程姿势：复制脚本改 OUT 与 to_block 边界（`if nxt >= BOUND: break`）、sleep 提至 0.5s，各进程独立 CSV 事后按 (tx,log_index) 去重合并；改 config 后重启前删本地缓存的段清单文件。（哈基米，07-18）现行主线为 v2 Parquet/done manifest。
- **多会话共享 key 限速冲突**：并行分析会话同打一个 HyperSync key/端点会互相触发 429（SQD 案与另一标的采集会话撞车实测）——开工前 `ps aux | grep fetch_hypersync` 查有无在跑进程；撞车时不必停工，调低单会话吞吐预期、靠 429 退避共存。（SQD，07-20）**限流是 key 级共享、不是端点独立**——同 key 打不同链子域（eth+arbitrum）并发同样互抢限额；多链标的的分链采集按链串行或错峰，别指望换端点绕开限额。（LPT，07-21）
- **分段采集**：`staged_capture.sh` 进入 skip 循环前先要求根 `capture_identity.json` 在场，缺失即 FATAL 并指向 `--recover-identity`；只在 done manifest 的 token/url/from/to/query/collector 全字段及 Parquet 实物一致时跳段。残段移入 `outdir/quarantine/` 保留诊断现场，不再递归删除；正式 preflight 前须把该诊断目录移出采集根。失败 retry-once 后仍失败即停。

- **★稀疏事件（单池单 topic）别用 HyperSync 全链扫，改「已有 Transfer 反查 tx → 打回执」**：HyperSync 按"扫过的块量"分批返回，对稀疏匹配（如某一个池的 `Mint` 事件）实测每次只推进 **~5,400 块 / 12 秒**——扫 1.1 亿块要几十小时，且中途看不出异常（进程活着、只是慢）。**正解**：从已落盘的全量 Transfer 里筛出"该合约 ↔ 任意地址、金额 ≥ 门槛"的交易去重得 tx 列表，再并发 `eth_getTransactionReceipt` 逐个解析。**反过来**：块区间已知的小范围精确查询（如追某个 tokenId 的 ERC721 Transfer）用 HyperSync **一次返回**，比公共 RPC 的 `eth_getLogs` 省事——后者在 BSC 公共节点超 5,000 块即 `-32005 limit exceeded`。选型口诀：**大范围稀疏→反查回执；小范围精确→HyperSync**。（KOGE 第二轮追加取证，07-25）
- **v2 响应里的 log 字段是 `topic0/topic1/topic2/topic3` 分列，不是 `topics` 数组**：按 `l['topics'][0]` 取会直接 `KeyError`（与 `eth_getLogs` 的 RPC 返回结构不同，混用两套代码时高发）；`field_selection.log` 里也要逐个列名申请。同理 `transaction`/`block` 的字段名各自独立申请。（KOGE 第二轮追加取证，07-25）

- **v2 resume 语义**：只消费同 `capture_from` 且身份完全一致的 manifests；边界必须满足 `capture_from<=from<to=next<=本次to`。`hypersync-v2-done/v4` 将 `logs.parquet` 与 `blocks.parquet` 的 size/rows/min_block/max_block/sha256 分别落盘，并逐段记录 collector。collector 哈希在进程启动时冻结、写 done 前复验；这是防误漂移的自报绑定，不宣称抵抗能同时伪造脚本与收据的攻击者。原生 v4 必须有可验 collector；迁移 v4 必须是 `collector=null`、`collector_provenance=legacy-unattributed` 与完整迁移记录，下游显示 `UNKNOWN_LEGACY`，不得渲染为已验证。done 经临时文件、fsync、rename 原子发布；`find_resume_block` 与 `staged_capture.sh` skip 前重读两个 Parquet 并重算全部字段。遇 v2/v3/pre-schema 存量 done 先 recover 再 refresh，禁止手改 `files`。跨标的、跨端点、坏边界、缺文件、截断或 hash 漂移、`start>=to` 全部 fail-closed，禁止“空完成”。

### 3.2 Alchemy getAssetTransfers（scripts/evm/fetch_alchemy.py）
- POST `https://bnb-mainnet.g.alchemy.com/v2/{KEY}`，method=`alchemy_getAssetTransfers`，params 含 `contractAddresses`、`category:["erc20"]`、`maxCount:"0x3e8"`、`pageKey` 分页；返回自带时间戳。（SIREN，07）
- pageKey 有有效期，长任务中断后必过期：断点续拉一律读 CSV 末行区块号置 fromBlock 重开游标，容忍少量重复、下游按 tx hash 去重。（SIREN，07）
- 会遇平台级 429（"global traffic"，与自身配额无关、恢复时间不可控）：脚本内置指数退避（最长 20 分钟）+ 外层 while 冷却重启；卡点超 1-2 小时必须并行准备第二通道并用 AskUserQuestion 摆路径，绝不单通道死等。（SIREN，07）
- **正式资格已除名**：该协议的 pageKey 只证明分页关系，不能证明 provider 已扫描到某个块上界，因此不支持 `evm-collector-run/v2` 正式 receipt，仅可探索采集。恢复资格需先升版为能表达分页完成证据的分型收据。

### 3.3 bloXroute getLogs 扫块

正式操作入口为 `scripts/evm/scan_bloxroute_seg.py`。旧 `scan_transfers.py` 仅保留历史/诊断用途，不得作为正式或冷启动主线。
- 断点续传：done-segments 清单跳过已完成段；多线程必留失败段，扫完自动列 remaining 并补扫，remaining=0 才算采集完成。（OPN，07）
- 起始块定位：勿用 eth_getCode 二分找部署块（免费节点历史状态请求被拒，会找错块导致空扫秒退）；改按"块时间戳 >= 已知安全起始日期"二分，起始日期用 GMGN start_holding_at 或跨链铸造日锚定，多扫无害。（OPN/SIREN，07）
- 同脚本顺带采时间戳锚点：每隔固定块距 eth_getBlockByNumber 取块头时间戳（数百个锚点几分钟采完），分析期 bisect 线性插值，省数千次逐块 RPC。（OPN，07）
- **起点缓存坑**：`<chain>_scan_meta.json` 缓存 start_block/head，改 config 的 start_time_utc 后必须删除该文件才会重新二分，否则沿用旧起点空跑。（哈基米，07-18）
- HTTP 客户端用 subprocess 调系统 curl（或 requests），绝不裸 urllib——macOS 证书链坑两次会话都踩过。（OPN/SIREN，07）

### 3.4 Etherscan V2（scripts/evm/fetch_etherscan.py，仅 ETH 主网）
- `https://api.etherscan.io/v2/api?chainid=1&module=account&action=tokentx|txlist|txlistinternal&apikey=KEY`；tokentx 每页 10000 条，按末行 block 续页拉全。（OPN，07）
- 免费 key 仅 chainid=1 可用；跨链代币的 ETH 侧全量转账、金库地址 txlist/txlistinternal（vesting 释放追踪）都走它。（OPN，07）

### 3.5 Multicall3 批量余额（scripts/evm/multicall_balances.py）
- 参数化调用：`python3 scripts/evm/multicall_balances.py --token 0x... --input addresses.txt --out balances.json [--rpc URL ...]`。默认 4 个公共节点仅适用于 BSC；跨链必须显式传对应链的 `--rpc`，禁止改源码注入标的。
- eth_call 到 Multicall3（`0xca11bde05977b3631167028862be2a173976ca11`，各 EVM 链同地址）的 aggregate3，手工 ABI 编解码，≤200 地址/批；近千地址几十秒查完。（SIREN，07）
- 反例：逐地址 eth_call 串行查 990 地址 10 分钟命令超时（exit 143），别走。（SIREN，07）
- 纪律：先用 2 个地址小样本打印原始 RPC 响应验证编解码再放量；异常必须落日志绝不吞。（SIREN，07）
- 地址清单文件须纯地址一行一个，任何附加字段都会污染 calldata。（SIREN，07）

### 3.6 记账模型 gate 的通道实测（accounting_gate.py，3.19）

- **BSC dataseed**：eth_call 历史 state 窗口 **~128 块且节点池深浅抖动**（150 块探测过、边缘偶发 missing trie node——gate 的 rebase 两时点已收缩到 64 块保命中）；支持 **eth_simulateV1**（模拟转账读实收的兜底路）；getLogs 拒(-32005)。bsc/eth publicnode 全 archive 墙（128 块内也拒）；dRPC 免费层限速凶只配兜底。
- **Alchemy ETH 免费层：eth_call 全历史 archive**（100 万块前实测通）→ ETH 侧 gate 事件窗口自动放大到 1 万块、rebase 窗口 7200 块，检测强度远超 BSC；但 getLogs 限 10 块——事件一律走 HyperSync。`.g.alchemy.com` 的代理经 `CHIP_PROXY`/`--proxy` 解析（`scripts/lib/proxy_config.py`），不再内置固定端口。
- **fee-on-transfer 双路互补**：事件差值覆盖池路径，`eth_simulateV1` 兜底低活跃场景；事件差值只取单侧干净样本。（判例：casebook/supply-accounting.md S-05）
- **PAXG 链上转账费现役为 0**（曾经 0.02% 是老黄历）——勿再当税币验收样本；**HOGE 2% 税硬编码在合约里，是稳定的 BLOCK 回归样本**。
- Helius getAccountInfo(jsonParsed) 对 Token-2022 扩展解析完整（BERN transferFeeConfig 全字段直出），无需手动解 TLV。
- BSC 非 archive 下 rebase 属弱检测（64 块≈3 分钟窗口抓不到 24h 周期 rebase，脚本 warnings 自我声明）——BSC 币强怀疑 rebase 时用 HyperSync 拉单地址全史微重放核对。

## 6. BSC 专属坑表

| 坑 | 识别/处理 | 来源 |
|---|---|---|
| Binance Alpha 2.0 Router 托管黑箱 | BSC meme 生态特有：单一 Alpha 托管合约可能就是 top1 holder 且份额巨大，绝不能当成"庄家地址"分析。识别=WebFetch bscscan 官方标签 + 工厂合约 getPair 分清主池/尘埃池；处理=与 CEX 热钱包一并归入"不可穿透黑箱"，报告显式给黑箱占比与单一实体份额上限，措辞一律带"链上可证范围内"限定 | （SIREN，07） |
| **Alpha 转正币安现货后 Router 黑箱消失** | bapi 全量表 `listingCex=True`（Alpha 转正现货）的币：Alpha 端 offline=True/canTransfer=False，**Alpha 2.0 Router 托管随转正清空迁移**——转正币无 Alpha Router 黑箱，币安黑箱=常规充提托管热钱包体系，黑箱盘点按普通 CEX 口径做即可，勿再找 Router 大仓 | （BANANAS31，07-22） |
| **BSC 历史段块时长** | 历史时间一律取区块时间戳差，禁止用块数×固定块时长折算 | （判例：casebook/supply-accounting.md S-06） |
| **TokenManager 流量/存量口径** | TokenManager 毛流出禁作份额；必须净重放并核毕业时点存量 | （判例：casebook/supply-accounting.md S-05） |
| 新 key 不探测就承诺方案 | 任何新 key 到手先做 1 分钟能力探测：eth_blockNumber + 一次真实 getLogs（或一页 transfers），确认块范围上限/限速/链覆盖后再写进计划 | （SIREN，07） |
| 用户网络可达性 | 让用户注册任何站点前，先在用户机器上 `curl -s -o /dev/null -w '%{http_code}' {url}` 预检，且"控制台打不开 ≠ API 端点不可用" | （SIREN，07） |
| 数据量按市值臆测 | 先拉发射首月抽样外推总量，向用户报保守上限；"转账笔数/市值异常比"本身可写进报告当信号 | （SIREN，07） |
| dataseed 只能做轻查询 | eth_blockNumber / eth_getBlockByNumber / eth_call / eth_getCode（latest 状态）正常，可做时间戳锚点与工厂 getPair；getLogs 与历史状态一律被拒 | （OPN/SIREN，07） |
| 部署块 getCode 二分失效 | 免费节点拒历史 eth_getCode（archive 请求），二分会找错块 → 改用块头时间戳二分定起始块（非 archive 请求） | （OPN/SIREN，07） |
| 通道切换不清观察哨 | 废弃一条数据通道时，同步 TaskStop 与之绑定的 until-grep 观察哨/循环任务 | （SIREN，07） |
| zsh 裸 glob 杀命令链 | 后台命令 `rm -f part_*.csv && python3 ...` 在 glob 无匹配时报 "no matches found" 并中断整条链，扫块脚本被连带杀掉 → 用 `rm -f ... 2>/dev/null \|\| true` 或拆成两条命令 | （OPN，07） |
| 锚点插值发射窗口系统偏差 | 每 10 万块锚点线性插值在发射窗口可有 +100s 级恒定偏差（BSC 出块速率变化）。分钟 K 配价前必须 RPC 实查 2-3 个关键块定量偏差，发射窗口改用"精确锚定块 + 实测出块间隔外推"（如 ts=mint_ts+(blk-mint_blk)*0.45）；小时/日级分析不受影响 | （bibi，07-12） |
| GoPlus is_contract 判定 | `is_contract=1` 必须复核 EIP-7702 委托与 `eth_getCode` 的 `0xef0100` 前缀 | （判例：casebook/entity-clustering.md E-01） |
| GMGN 卖出榜 EOA 身份 | 榜单操作者 EOA 不等于 Transfer 主体，必须在 tx 层核实 `msg.sender` 与事件主体 | （判例：casebook/entity-clustering.md E-02） |
| 代理合约身份 | 读取 EIP-1967 implementation slot 并核字节码 selector；页面文本不作最终证据 | （判例：casebook/entity-clustering.md E-01/E-02） |
| 共源 Router 排除 | 共源边的源地址先过标签库与半枢纽排除，再进入聚类 | （判例：casebook/entity-clustering.md E-02） |
| V4 池发现与量能 | V4 单例必须纳入池发现；量能真实性检查必须包含 V4 毛量占比 | （判例：casebook/supply-accounting.md S-04） |
| **V4 PoolManager 标签复核** | vanity 全零前缀命中攻击者/bot 标签时，必须 `getCode` + 行为复核 | （判例：casebook/entity-clustering.md E-02） |
| **V4/Infinity 单例余额归属** | 单例余额只作上界；精确归属须逐头寸闭合，权威见 `lp-fee-accounting.md` | （判例：casebook/supply-accounting.md S-07） |
| CEX 归集身份 | 必须核下游对象身份，禁止只凭高入度低出度判 CEX | （判例：casebook/cex-custody.md C-06） |
| DexScreener dexId "uniswap" 无版本标注可能是 V3 池 | Swap topic：V3=`0xc42079f9…`、V2=`0xd78ad95f…`；dexId 只写 "uniswap" 不标版本时，先按 log topic 判池版本再解析，按错版本解析买卖归因全错 | （外部 bibi 考古，07） |
| four.meme 内盘量化 / 克隆快判 | 内盘额度恰 8 亿/80%，dev-buy 同 tx 按 bonding curve 买断内盘凑满即秒毕业、创世后约 8 块（~4s）TokenManager2 注 20% 入 Pancake V2；"创世同秒单钱包拿走 ~80%"=dev buy。`7777` 后缀=另一发射台 CREATE2（与 4444 并列，平台特征非指纹）。meme-api 全路径已 404，正身改看创世 tx HTML 是否触及 TokenManager2/部署器（创建者从合约页 Contract Creator 取，href 单引号，正则 `["']?`） | （外部 TCC/bibi 考古，07） |
| **PancakeSwap/Uniswap V3 topic** | Pancake V3=`0x19b47279…`（7×32B），Uniswap V3=`0xc42079f9…`（5 字段）；目标池静默 0 行即阻断并复核 topic/布局 | （判例：casebook/supply-accounting.md S-04） |
| four.meme creator/收币实体 | 同收币地址不得直接判项目方马甲；平台 creator 与收币实体按身份权威规则分账 | （判例：casebook/entity-clustering.md E-12） |
| **币安 Alpha 结算引擎桥** | 高吞吐 + 净持≈0 + 交易所/路由/池对手方应归 CEX 基础设施，不得判庄 | （判例：casebook/cex-custody.md C-01） |
| **CEX 归集批次节奏** | 充值时间对齐必须建同窗对照组；同窗地址数 >10 时该时序零区分力 | （判例：casebook/entity-clustering.md E-04） |
| **dust/funder 与幽灵地址** | 投毒/公共 funder 不作聚类边；进入实体表的地址必须在 `merged.csv` 验存在性与走量 | （判例：casebook/entity-clustering.md E-05/E-10） |
| **Alpha Box Router 充值** | 必须拆托管系新币与库存回充；领取人即领即抛与项目方出货并列 | （判例：casebook/cex-custody.md C-01/C-04） |
| **key_edges 来源拆解** | `daily_delta` 缺口显著即回全量补齐该仓该窗完整边，禁止用筛选产物反证来源 | （判例：casebook/supply-accounting.md S-04） |
| **亿级 edges 提取禁止攒内存** | 1 亿条级转账逐行提边时 list 攒内存会 OOM/假死——一律边读边流式 append 落盘，聚合统计另做二遍 pass；产物文件在交接包标注"勿整读" | （QUQ，07-22） |
| **币安 Alpha 积分倍数 mulPoint 直查** | `www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list`（免 key 国内直连，~656 币）每币带 **`mulPoint`=当前积分倍数**及 listingTime/volume24h/count24h/holders/score。Alpha 在架标的量能判读**第一步先查此字段**；⚠只有当前值无历史接口，历史轨迹靠政策线锚点+快讯/推特回溯 | （QUQ 投后，07-22） |
| **Alpha 积分政策时间线锚点 + 量能断崖三因鉴别** | 政策线：2025 年中 BSC 币全板块 2x → **2025-09-04 取消**（BSC 双倍与 Alpha 2.0 限价单双倍一并废止，改新 TGE 30 天 4x）→ **2026-07-22 Alpha CEX 限价单买 BSC 币 4x**（挽回板块流量新政）。Alpha 币量能台阶/断崖先对政策线，再三因鉴别：①个币处分（mulPoint 降档）②板块政策变化 ③**竞价性分流**（更高倍数/更低磨损的新载体抢走刷分大军——刷分量是"倍数×磨损成本"性价比的函数）。鉴别三件套=mulPoint 直查+**对照币实验**（同板块 2-3 币 GT 日 K 同窗看是否同跌，同跌=板块性非个币）+xapi `search_posts_all` 断崖窗口±3 天搜刷分社区实时讨论（⚠中文**带引号词组零命中**，拆开词搜）。QUQ 案：07-14 单日腰斩且随后 8 天窄带平稳（窄带新平台=新配额指纹），判③——美股代币 4x+磨损低 15 倍分流，对照币同窗 -93% 更狠、QUQ 仍全表量第一=分流非处分 | （QUQ 投后，07-22） |
| **Alpha 场内↔链上量能迁移** | 链上量归零先查同期场内量与政策；托管转移不得直接写出货 | （判例：casebook/cex-custody.md C-01） |
| **全史 DEX 成交量硬算（池腿法）** | 每笔 swap 必有一条代币进/出池的 Transfer 腿：POOLS={各直连池+V4 PoolManager 单例}，from/to 恰一侧在集合=计一腿（**单边口径**），池↔池转账（V3↔V4 摆深度）自动排除；**LP 加撤剔除**=lp_events 的 mint（进池）+collect（出池）amount 按日减（burn 只记账无 Transfer 勿剔）。价格三源拼接：CG（365d 窗）+DefiLlama historical 逐日（2025 起 BSC 小币覆盖好，发射数日内即有价）+GT day 线只留 ~181 天。**费反推独立交叉验证器**：V3 全史 collect−burn 双边费 ÷ 池费率 = 名义成交额，与池腿实算互验；CG 聚合口径预期偏高 | （QUQ 投后，07-22） |
| **transfers_lib 整表读大 parquet 必 OOM** | `iter_transfers` 内部 `pq.read_table` 整表载入，logs.parquet 数 GB 级（QUQ 案 6.6GB/1.03 亿行）直接 SIGKILL（exit 137、输出全空）。亿级全史扫描自写 pyarrow `ParquetFile.iter_batches(batch_size=20万, columns=['block_number','topic1','topic2','data'])` 流式，峰值内存 <1GB、约 2 分钟/亿行；日期用 blocks.parquet number→timestamp 映射 + `ts//86400` 整数日聚合（避免逐行 strftime）；跨 run 去重用块边界法 `[from_block,next_block)`（亿级 (tx,log_index) set 去重内存不可行） | （QUQ 投后，07-22） |
| **V3/V4 LP 费与回执速查** | 四层费口径与公式统一见 `lp-fee-accounting.md`；回执速查最小规则：按 PoolManager/直连池腿分 V4/V3，费率读池状态，路由抽成按拆腿输入和对用户付出 | （判例：casebook/supply-accounting.md S-07） |
| **TVL 伪影与 LP 归属** | 官方头寸查 `ownerOf`/NFT 状态链；receipt 净现金流只证明投入提取；池属以目标时点可证 LP 归属为准 | （判例：casebook/supply-accounting.md S-07） |
| **枢纽性质裁决** | 用同 tx 等额转入转出配对率区分原子过账管道与余额滞留仓库 | （判例：casebook/entity-clustering.md E-02） |
| **V3/V4 TVL** | 必须以 `slot0` + 两侧 `balanceOf` 第一方复算，禁止直采 V2 式等值估算 | （判例：casebook/supply-accounting.md S-07） |

## 7. 零门槛免注册通道（外部会话考古 2026-07 补充）

> 本节来自另一台电脑对 CZ/TCC/人生K线/bibi(BSC)、ASTEROID/OPN(ETH) 的独立分析实战。与 §1–§3 的本机通道（bloXroute/HyperSync/Alchemy）**互补**：这套通道**完全免注册免 key**，适合"手头无任何 key、临时快速起手分析新盘"的冷启动；代价是历史保留窗口短或需网页抓取。用前仍按 §6 做 1 分钟能力探测（政策季度级变化）。

### 7.1 BSC：`0.48.club` 是唯一可用的免费历史 getLogs 端点
- 免 key 免注册，**实测唯一能服务历史 eth_getLogs 的免费端点**，5000 块/请求（~1000–2500 logs/s），支持宽 topic-OR（40 个 padded 地址塞一个 topic 数组 OK）；也支持 eth_call / eth_getCode / eth_getTransactionReceipt。**不支持 JSON-RPC batch**（发单请求，并发 ~8 可），Python requests 偶发 SSL EOF 重试即可。
- **致命保留限制**：只保留最近 **~1.14M 块 ≈ 6 天**（二分实测边界，更早 getBlockByNumber 返 null、getLogs 报错）——**只够 6 天内新盘，几个月前历史无用**。且 eth_call/eth_getCode 只在 `"latest"` 有效，任何历史块参数返 `-32000 not supported`（state 不归档，连 30 分钟前都查不到）。保留窗口探测通用法（适用任何新免费端点）：probe 当前块 −10万/−100万/−500万 的 getBlockByNumber/getLogs，二分收敛，几分钟测清历史窗口边界。
- 推论：0.48.club 上 getCode/eth_call **不能**二分定位老合约创建块（state 非归档）→ 改用 BscScan 合约页 "Contract Creator … at txn" 直接拿创建 tx→回执→blockNumber。

### 7.2 BSC：BscScan 网页直抓（免 key 深度历史，反爬已摸透）
服务端渲染、**普通 Chrome UA 的 fetch 即可过 Cloudflare**（无需 firecrawl/浏览器），是"无 key 时逐个大户深度溯源"的主通道：
- 单地址转账史：`bscscan.com/tokentxns?a=<addr>&p=<N>&ps=100`（硬上限 ~10 页×100 行/地址；超活跃 bot 会被截断——**别据截断数据推"钱包年龄/建仓时间"**，翻不完必须在报告标注"建仓可能更早"）
- 持有人榜：`bscscan.com/token/generic-tokenholders2?m=normal&a=<token>&p=<N>&ps=100`（ps 被强制 50、最多 20 页=前 1000 名，meme 币通常覆盖 99%+ 供应；行内自带公共标签如 MEXC/Null）
- 地址概览：`bscscan.com/address/<addr>` 拿 Public Name Tag / Contract Creator / "Funded By"（href 用单引号，正则要 `["']?` 容单双引号）。⚠ WebFetch 抓此类页面返回的地址常是省略号截断形态（`0xe096774F...BD5E2f603`），截断地址禁止进任何产物——一律回本地落盘数据前缀反查完整地址（evidence-wording 落盘取值纪律）
- **并发 >1 必触发限流返回空页**（3 线程实测 16/43 失败）→ **必须单线程 0.6–1s 间隔**；失败地址单线程重试即 100% 成功。
- 行级解析坑（血泪）：①时间戳在 `class='showLocalDate'` 的 span **文本**里（不是 data-timestamp 属性）；②方向靠 `>IN</span>`/`>OUT</span>` badge（tokentxns 行不把自身地址渲染成链接，只有对手方在 `data-highlight-target`——只存对手方会丢方向）；③数量在 `td_showAmount` 的 `data-bs-title`（全精度｜$价）；④**持有人榜百分比列常年显示 0.0000%（BscScan 自身坏的），持仓数量要取百分比单元格的前一格**——"取行内第一个大数"的偷懒解析会把排名数字（第 101 名起 >100）当持仓。
- 已死端点：`token/generic-tokentxns2`（按币种过滤单地址史）返回 "unexpected error"；`advanced-filter` 页被 Cloudflare 403。替代=全局 tokentxns 抓回后按行内 `/token/<ca>` 链接过滤目标币。
- **工程模式——磁盘缓存抓取层**：批量直抓统一封装为"单线程限速 + 磁盘缓存（`sha1(url)` 作缓存文件名，命中即免请求）"——反复抓同址零成本、中断重跑断点友好，是 BscScan 串行慢速纪律下的效率补偿（外部 bibi 会话 fetchlib.py 模式，2026-07）。

### 7.3 ETH 主网：`rpc.mevblocker.io` 全史 getLogs（免 key）
- **支持全区块段 eth_getLogs**（不像 BSC 各免费端点限几十块），按 Transfer topic 的 from/to 过滤，每地址 2 次调用即拿全史台账；偶发 429 退避。这是 ETH 侧**无 key 全史通道**（§1 的 ETH 侧只有 Etherscan V2 免费 key 路线，此为零门槛补充）。
- **免 key RPC 台账校验**：必须以链上 `balanceOf(latest)` 逐钱包对账；历史快照用 archive `balanceOf` 独立重建，不能只信台账累加。（判例：casebook/supply-accounting.md S-04）
- **老币/百万级转账的免 key 采集拓扑**：全量拉取不现实时，改对 top ~200 持有人 + 关键地址**逐地址定向拉台账**（from/to 各一次 getLogs），全部台账逐一 balanceOf 对账（unreconciled=0 才放行）；代价=非 top 持有人行为不可见，报告声明口径（外部 ASTEROID：134 万笔转账标的，201 个台账全对平）。
- 大窗口 getLogs 分片纪律：块范围自适应二分细分片，<250 块仍失败才放弃该段。
- 首笔注资溯源：`eth.blockscout.com/api?module=account&action=txlist|txlistinternal&sort=asc&offset=1` 一次调用拿钱包首笔注资交易（免 key，资金溯源关键）。
- **`eth.blockscout.com/api/v2` 与 Robinhood 链 Blockscout 同栈同端点**（holders 分页 / token counters / smart-contracts 合约名与 implementation（识别 proxy/EIP-7702 delegate）/ internal-transactions 全套可用，端点细节见 data-pipeline-robinhood-channels.md）——ETH 侧持有人榜、地址画像、合约识别的免 key 主通道（外部 ASTEROID 考古，2026-07）。
- 其他 ETH 免费端点：`ethereum-rpc.publicnode.com` 近期块 getLogs 可 2 万块/请求（老块要 key）——⚠️ 块限两说：外部 ASTEROID 实测为 5 万块/次需分片，政策会变，用前 1 分钟实测取当前值；`eth.drpc.org` archive+10000 块 free 但 CU 频控紧。

### 7.4 省请求取证技巧（外部 OPN/ASTEROID 实战）
- **mint 常在合约创建那笔 tx（constructor 铸造）**：`eth_getCode` 二分定位创建块 → `eth_getBlockReceipts` 一次拿整块回执 → 本地过滤 Transfer(from=0x0)，绕开 getLogs 范围限制。⚠️ **与 §3.3/§6 冲突**：本机 bloXroute/免费节点实测"拒历史 eth_getCode（archive 请求）、二分会找错块"；外部实测"bsc-dataseed 的 eth_getCode 是 archive、可查任意历史状态"。**两说并存**——用前对目标节点实测一次历史 getCode 是否被拒：被拒→按块头时间戳二分（§3.3）；不被拒→getCode 二分更省请求。
- **锁仓盘往往集中在另一条链**（外部 OPN：BSC 只放流通盘，8 亿 vesting 全在 ETH、转账极稀疏一次 getLogs 拿完）——全量扫描前先判"要不要扫这条链"，别对着流通链扫全量却漏了锁仓链（呼应 analysis-playbook §1 多口径）。
- `topics:[Transfer,[from1,from2,…]]`（topic1 传数组=OR）一次查多个金库桶流出；查"金库动没动"最省的是 `balanceOf(latest)` 对比初始分配额，有变动再回头扫 log 找 tx 证据。

### 7.5 BSC 老币（超出 48club 6 天窗口）免 key 三段拼接采集拓扑

适用：老币 + 手头无任何 key 的冷启动（外部 人生K线(BSC) 实战 47 分钟交付验证）。三段互补拼接：

1. **近 6 天全量 getLogs**（48club，§7.1）→ 当前筹码结构与本轮爆量归因；
2. **BscScan 网页直抓深历史**（§7.2）→ 创世取证（token 页 Contract Creator 段）+ 前排大户 `tokentxns?a=` 建仓史（≤10页×100 上限，翻不完标注"建仓可能更早"）+ generic-tokenholders2 持有人榜；
3. **GT 日线价格轴**（只留 ~180 天，§4）+ 关键放量日与链下事件（上所/Alpha 公告等）对齐。

- **输出形态随之改变**（全史演变曲线在此拓扑下不可得，报告口径必须声明）：**结构快照**（当前各阵营占比）+ **6 天净变动表** + **大户建仓时间线**。⚠️ **边界：此路线不满足 /token-analyze 的交付合同**（正式分析要求全史演变），只能作预检/受限快照用；正式分析必须补全史（拿 key 走 HyperSync 等全量通道）或明确告知用户后中止。
- **fresh/old 大户分层**：用 6 天窗口把前排大户分为"本窗口进场新大户 vs 更早老持仓"两层，直答"这波爆量谁在买"。

（本节来源：外部电脑 BSC/ETH 分析考古，2026-07；原始会话见 `windows虚拟机cc会话记录/`）


### 7.6 Blockscout v2 持有人榜与地址画像（ETH / Base / Arbitrum，免 key）
端点 `https://<eth|base|arbitrum>.blockscout.com/api/v2/...`，普通 Chrome UA 直连，无需 key。三件套：
- 持有人榜 `/tokens/{addr}/holders`——**不支持 `limit` 参数**（传了返 422 `Unexpected field: limit`），只能用响应里的 `next_page_params` 逐页翻，50 条/页；items 带 `address.name` 公共标签（RewardTracker / UniswapV2Pair / GnosisSafeProxy / 交易所名等），是免费认所的第一道。
- 代币元信息 `/tokens/{addr}`——`total_supply`（raw）/`decimals`/`holders_count`。
- 地址画像 `/addresses/{a}`（`coin_balance` 原生币余额、`is_contract`）+ `/addresses/{a}/tokens?type=ERC-20`（持币种类）+ `/addresses/{a}/counters`（`transactions_count` = 主动发起交易数）+ `/addresses/{a}/token-transfers?type=ERC-20&token=<币>`（按币种过滤的单地址流水，分页同上）。
- **持有人榜不作余额权威源**：Blockscout 只用于找候选/标签；结论余额必须经全量重放或 `balanceOf` 复核。（判例：casebook/supply-accounting.md S-04）
- 同源提示：`transactions_count` 与 `eth_getTransactionCount`（nonce）不是一回事但同向；判"从未主动签发交易"以 **nonce 为准**（见 playbook-entity-cluster-methods §6 nonce 基准率法）。

### 7.7 Avalanche：Routescan API（免 key，snowtrace 已 403）
`https://api.routescan.io/v2/network/mainnet/evm/43114/erc20/{token}/holders?limit=100`，免 key 直连、`link.nextToken` 翻页，返回 `address`/`balance`(raw)/`percentage`（**小数形态，0.300574 即 30.06%**）。
- 死路记录（2026-07-26 实测）：`snowtrace.io/api/v2/...` 返 **403**；`avalanche.blockscout.com` **不存在**（404 default backend）；`bsc.blockscout.com` 同样 404——**BSC 无 Blockscout 实例，持有人榜只能走 §7.2 BscScan 网页**。
- 用途：多链标的的分支链快照（GMX 的 Avalanche 侧占其全局链上量 5.46%，看板口径未覆盖，实查该侧另有 22.73% 在 CEX）。
