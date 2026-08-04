# Filecoin 筹码分析脚本管道

来源：FIL(Filecoin) 分析会话实战产物, 2026-07。数据源为 **Filfox 免费 API**（`https://filfox.info/api/v1`，富豪榜/地址详情/流水/官方多签，只读 GET、节流约 2-3 req/s、断点续抓）+ CoinGecko 免费接口（辅助）。无需任何 key。

## 四个脚本的管道关系

```
fetch_data.py --data-dir <案目录/data> --smoke 10
                              ① 冒烟：只抓富豪榜前 10 名，验证 Filfox 通道与产物格式
        ↓ 通过后
fetch_data.py --data-dir <案目录/data>
                              ② 全量：富豪榜前 200 名（detail + 近6个月流水 + 最早流水）
                                 + 官方多签扫描（official_scan.json、official/<id>_transfers.json）
        ↓ 阶段二人工看数据，圈出 top200 的关键对手方地址
fetch_extra.py --data-dir <案目录/data> extra_addrs.txt
                              ③ 补抓：对手方地址逐个补拉（复用 fetch_data.fetch_address，
                                 每行一个地址，# 开头为注释）
        ↓ data/ 齐备后（纯本地计算，不再联网）
analyze_base.py               ④ 基础量化：逐地址净流量 / 首笔资金来源 / 互转图 / 官方地址流出
                                 产物 analysis/{top200_flows,common_funders,edges_top200,
                                                official_multisigs,daily_net}.json
        ↓
cluster.py                    ⑤ 关联聚类：E1 共同 funder / E2 互转边 / E3 vanity 尾缀，
                                 三类独立证据 + 置信度分级，产物 analysis/clusters.json
```

官方扫描仅在 `official_scan_receipt.json` 四桶闭合且 `failed=0` 时写正式结果；
`collection_manifest.json` 必须以 SHA-256 引用该子阶段 receipt。失败 ID 保留在 progress 中供重跑补查。

## 路径约定

`fetch_data.py` 和 `fetch_extra.py` 必须用 `--data-dir` 显式注入案目录；模块 import 不创建任何目录，只有 CLI `main()` 进入执行后才创建 `addr/` 和 `official/`。`analyze_base.py` 与 `cluster.py` 仍按所在工作目录的 `data/`/`analysis/` 运行，因此实战时把脚本拷到案目录，并将 `--data-dir` 指向该案目录的 `data/`；不要向 skill 目录写数据。

## 实战要点（原会话验证过的坑）

- 本机 Python 缺 CA 证书链，HTTP 统一走 `subprocess` + 系统 `curl`（系统证书）。
- 近 6 个月流水窗口起点 `CUTOFF` 与每地址翻页上限 `MAX_RECENT_PAGES`（30 页=3000 笔，超出记 truncated）按分析日期改。
- 富豪榜若出现重复地址，`analyze_base.py` 会 assert 拦下——先重抓再算。
- 聚类纪律：funder 为交易所/热钱包时 E1 证据作废（人人都从交易所提币）；互转边任一端为交易所则 E2 作废；vanity 尾缀只作弱证据不单独成簇。
