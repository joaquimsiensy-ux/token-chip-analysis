# 批 5 T1：ARC 定向双 window 真采证据

## 1. 边界与数据源

- mint：`61V8vBaqAGMpgDQi4JcAwo1dmBGHsyhzodcPqnEVpump`。
- SQD：`https://portal.sqd.dev/datasets/solana-mainnet`，免认证只读；采集命令显式传
  `--key-file /dev/null`。
- Solana RPC：按附 B 双节点顺序使用 `api.mainnet-beta.solana.com`、
  `solana-rpc.publicnode.com`；成功抽样节点为前者。
- 主网身份：每个 RPC 会话在业务请求前先验 `getGenesisHash`，观察值为
  `5eykt4UsFv8P8NJdTREpY1vzqKqZKvdpKuc147dw2N9d`。
- ARC 案目录只做投影读取；采集、验证工具和全部产物均在本仓库
  `maintenance/repair-20260817-sqd-v4/live_windows/`。

## 2. 双 window 参数与离线核验

| 窗口 | slot（含界） | v4 行数 | ARC tx-aware 5 元组行数 | 逐边 multiset | 碰撞 |
|---|---:|---:|---:|---|---|
| collision | 382697976–382714174 | 5,696 | 5,696 | 双向差集 0 | 85 组、额外 114 行、最高 5 倍 |
| green | 374331356–374344169 | 142 | 142 | 双向差集 0 | 0 组、额外 0 行 |

两窗均由现役 `fetch_sqd_transfers_v2.py` 真采，无缺口。验证工具逐行要求严格 7 元组、
`tx_index` 为非布尔非负整数、`instr_index=-1`、金额为正整数；再去掉 tx/instr 两列，与案内
`*-txaware-repaired.jsonl.gz` 同窗 5 元组按 `Counter` 做 multiset 对照，不以行数相等代替逐边相等。

meta 核验结果：

| 项目 | collision | green |
|---|---|---|
| schema/version | `sqd-solana-cache/v4` / 4 | 同左 |
| edge schema | `[ts,slot,tx_index,instr_index,from,to,amt]` | 同左 |
| semantics/order | `owner-net-greedy` / transaction / `order_exact=false` | 同左 |
| dedupe | `slot-txindex-digest/v1` | 同左 |
| collector SHA-256 | `2589f6a396c262d0747343ef21dee2bc7ba814eaa59eebdfa782fe9253c32212` | 同左 |
| ACTIVE 登记 | PASS | PASS |
| edge rows | 5,696 | 142 |
| logical SHA-256 | `2fbb127d440d7ff7ef6082eba3521b7bc8eb43236b3740b3bfc39cb06a51b201` | `401682426db942bf58ea2241bdcc47aaf50b642b3495d02406f3ed63421b55ef` |
| meta 偏差 | 0 | 0 |

复算命令：

```text
python3 maintenance/repair-20260817-sqd-v4/tools/live_window_verify.py
```

结果：`status=PASS`。

## 3. SQD 原始查询与 Solana `getBlock` 抽样

三组均向 SQD `/stream` 重放单 slot 原始请求，核心请求摘录如下；`<slot>` 分别替换为表中 slot：

```json
{
  "type": "solana",
  "fromBlock": "<slot>",
  "toBlock": "<slot>",
  "fields": {
    "block": {"number": true, "timestamp": true},
    "transaction": {"transactionIndex": true, "err": true},
    "tokenBalance": {
      "transactionIndex": true,
      "account": true,
      "preMint": true,
      "postMint": true,
      "preOwner": true,
      "postOwner": true,
      "preAmount": true,
      "postAmount": true
    }
  },
  "tokenBalances": [
    {"postMint": ["61V8vBaqAGMpgDQi4JcAwo1dmBGHsyhzodcPqnEVpump"], "transaction": true},
    {"preMint": ["61V8vBaqAGMpgDQi4JcAwo1dmBGHsyhzodcPqnEVpump"], "transaction": true}
  ]
}
```

RPC 请求统一为：

```json
{"method":"getBlock","params":["<slot>",{"commitment":"finalized","encoding":"json","transactionDetails":"full","rewards":false,"maxSupportedTransactionVersion":0}]}
```

响应摘录与交叉确认：

| slot / 五元组金额 | SQD `transactionIndex` 与源 owner 余额摘录 | `getBlock` 签名摘录 | 结论 |
|---|---|---|---|
| 382698123 / 14,137,829,709 | 241: `2786439094381→2772301264672`; 1054: `2772301264672→2758163434963`; 两笔 `err=null` | 241: `4tvD1eccUy4T12sP95dyZbxbg2tRBjn5CHV8vDiF1nQA8jVoKsfkAAC95aYjLe23k1ub4hZC5VwrFAd8aJaSHdxM`; 1054: `3RL2ypTGeVYKiiYPoWgGMZmHzZjGscT63uCKpVzSYtPAwzLGmABo5iXjcjGygSPRWxXiNHWvCCpunNU9bn7ESA1G` | 同额同五元组，两个不同链上交易 |
| 382700107 / 13,359,922,378 | 820: `2987754864587→2974394942209`; 928: `2974394942209→2961035019831`; 两笔 `err=null` | 820: `LyCwwVggvnB4uhnJK1jW85cRaiyxyk3kywbQ4NhhVyrxCLxGnR7r4MxhYJ8sHA8MnGmmixQ7U6GGuJxNsjHgYV2`; 928: `4762tQdcvRnbGkaVnREKfh6PvGiNr6vgGtenwrfA36ekxu9Zp6HsY2AqbxgTmkx7FkNvrKyd4GKwDnBMmy52hGYQ` | 同额同五元组，两个不同链上交易 |
| 382701804 / 14,050,110,913 | 697: `2323268107365→2309217996452`; 1200: `2281117774626→2267067663713`; 两笔 `err=null` | 697: `61UM7MYesWLgBd6YKvFWvQ9fdAJMViQNReANGBqGGQKQ8c7nc6YrV1BoaDnKkQb9LvwjsTkG13xaFipy5oyHF7Lr`; 1200: `28ZvKjTmEAbgBMbhYcHAtEimjRMm7R3wBdRzM7AoG2nbPbt9gCTBPp88w41a3ru5Y7WCAnBxJMreBDTMbCYag93p` | 同额同五元组，两个不同链上交易 |

三次 SQD 均 HTTP 200，六个 `transactionIndex` 均存在于原始 tokenBalance 与 transaction 状态中；
三个 `getBlock` 的交易总数分别为 1,226、1,419、1,365，索引均在界内，六个签名互异。

在线复算命令：

```text
python3 maintenance/repair-20260817-sqd-v4/tools/live_window_verify.py --online
```

结果：3/3 组 `PASS`，总状态 `PASS`。

## 4. owner-change 窗降级

案内 `data/owner_authority_repairs.json` 是 `solana-owner-authority-repair/v1` 的 PASS 产物：只读扫描
146,759 个冻结 block 文件、9,163,215 条 tokenBalance，`repairs=[]`。没有已发现的 ARC owner
变更 slot 可供定向真采，因此严格按工单降级为：

1. 案内全量扫描证据未找到可用窗；
2. owner 双侧记账由批 2 的 `test_spl_edge_core.py` fixture 覆盖；
3. 不构造、不声称 ARC 存在 owner-change 实例。
