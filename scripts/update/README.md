# scripts/update/ — /token-update 增量更新通用件（EVM）

v2.10.0 收编。抽象依据：/token-update 六次实战（RAXOL、Pointless、TRASH、VEX =
EVM/Robinhood 四次；PUB、CLUDE = Solana 两次）。本目录只放 **EVM 系**通用件；
**Solana 增量更新不用本目录**：全量流水续拉走 `scripts/solana/fetch_sqd_transfers.py`
断点续拉 + `replay_edges.py`，锚点法走 `snapshot_diff.py` + `probe_window_moves.py`
（data-pipeline-solana §10 快照对比法）。

## 与 update-workflow 步骤的映射（按使用顺序）

| 步骤 | 脚本 | 作用 | 实战出处 |
|---|---|---|---|
| U0 | `getcode_recheck.py` | 旧实体表全地址 getCode 复检（防公共合约随 appendix 传代） | VEX 显式脚本；TRASH/RAXOL 教训催生 |
| U0 | `rebuild_wei_balances.py` | 旧快照为 float"枚"格式时从旧全量重放 wei 快照+互验（顺带独立复验旧账本） | CASHCAT 增量 |
| U1 | `pull_inc.py` | 增量拉取：起点自动=旧数据末行块（含，重叠窗），拉完自动做重叠窗一致性校验 | RAXOL+VEX |
| U2 | `replay_inc.py` | 旧快照+增量→最新余额表；全局 (tx,logi) 去重；供给闭合；每地址窗口统计；`--full` 双路径互验 | 四战合并 |
| U2 | `verify_balances.py` | 抽样对表（实体表∪观察哨∪top20∪随机5）；归档块探测，精确相等口径 | 四战合并 |
| U3 | `analyze_inc.py` | 四态表 + 新庄候选双口径 + 观察哨 mode-aware 核查 + 窗口净额买卖榜 | 四战合并 |
| U5 | `camp_series_inc.py` | 阵营序列增量追加 + 重采样 ≤500 点，输出 report-template 格式（嵌 appendix、画图1） | 四战合并 |
| 按需 | `v3_positions.py` | V3 池 tick 级头寸重建（挂单墙监控正解） | ⚠ 单次实战（VEX），用前实价交叉验证方向 |

## 典型跑法

```bash
cd <旧研报目录>   # 含 config.json、appendix.json、data/
python3 <skill>/scripts/update/getcode_recheck.py
python3 <skill>/scripts/update/pull_inc.py                      # data/transfers_inc.jsonl.gz
python3 <skill>/scripts/update/replay_inc.py --old-balances data/balances_now.json \
        --full data/transfers.jsonl.gz                          # balances_new + window_stats
python3 <skill>/scripts/update/verify_balances.py
python3 <skill>/scripts/update/analyze_inc.py --old-balances data/balances_now.json
# ……人工分析（新庄溯源/对抗复核）后，编好 camps.json（±remap.json）……
python3 <skill>/scripts/update/camp_series_inc.py --camps camps.json \
        --old-balances data/balances_now.json
```

## 输入输出约定

- **config.json**（工作目录，见 `../robinhood/config.example.json`）：本目录脚本额外用到
  `rpc`（EVM RPC；Robinhood 链必须浏览器 UA，可选 `rpc_ua` 覆盖）与
  `pools`（`{地址: 标签}`，窗口买卖归因用；`pool`/`pool_manager`/`v2_pairs` 会自动并入）。
- **旧期末余额快照**：各期实战文件名不一（balances_now / balances_latest / balances /
  replay_final_balances），所以 `--old-balances` 必填不设默认；纯 dict 或带 `balances`
  键的格式都接受。**值必须是 wei（int/str）**——旧版研报快照可能是 float"枚"
  （CASHCAT 案 balances_final.json），float64 精度不足 wei 级，直接喂会错 10^18 倍：
  先跑 `rebuild_wei_balances.py` 从旧全量重放出 wei 快照再进 replay_inc。
- **balances_new.json（replay_inc 输出）**：带元信息
  `{"last_block","last_ts","cutoff_block","balances":{addr:str_wei}}` ——
  verify_balances 自动取 last_block 做归档块对账；下游脚本读入兼容两种格式。
- **camps.json / remap.json**（camp_series_inc 输入）：每次更新人工产出——地址→阵营
  归属与旧键名映射是分析结论，**不属于**可固化逻辑；阵营键名用 standard_charts
  的 CAMP_ORDER 标准名。

## 刻意不收编的部分（防单样本归因错误，四战证据一致）

- **build_appendix**（JSON 滚动更新）：主体 80–90% 是人工研判文案（addresses 的
  role/why、monitoring_advice、evidence），骨架仅存档/换算/降采样几行——降采样已并入
  camp_series_inc，其余按 update-workflow U5 的骨架清单手写（rebuild 范式，勿用 mutate）。
- **更新图表薄壳**：standard_charts 三函数已是通用渲染层；薄壳里的实体选择/阵营映射
  每次都变。
- **深挖/怀疑者脚本（deep_*/probe_*/scratch_*）与报价币侧哨兵核查**：每次问题不同，
  链/标的特异（TRASH 用 Blockscout ETH 侧、VEX 用 HyperSync USDG 侧）。

## 密钥纪律

HyperSync key 走 config.json `hypersync.key` 或环境变量 `HYPERSYNC_KEY`（登记见
`~/.claude/api-keys.md`），**不写死进任何脚本**——RAXOL 期 pull_incremental.py 曾把
key 明文硬编码，收编版已改。
