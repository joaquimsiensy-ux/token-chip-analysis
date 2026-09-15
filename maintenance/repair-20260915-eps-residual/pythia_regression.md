# PYTHIA 同输入双版本回归

- r4：按 r3_fix_ruling.md，只读四份既有账本，逐一检查全部构成键、UNRESOLVED 合计、Σraw 和 pct；唯一精确的输出数量为 stock_raw，其余分别按 B=4·n·2^-52·S+2 与 B/stock_raw×100 判界，不要求展示值相同。PYTHIA 的 14 锚点、36 组策略明细共核对 482 个原始键位置，全部 Δ=0；另 2 个零库存锚点无策略明细，其 raw 仍已检查，pct 界不作除零计算。 gap/residual 合桶对齐后所有来源键 Δ=0，UNRESOLVED 合计、Σraw 和 pct 差均为 0；全部检查通过。两案合计 224 锚点、666 组策略明细；原始标签迁移与合桶后数值分别披露，不混作同一口径。四份输入账本 SHA-256 未变，未重跑 trace；逐键两版 raw、Δ、界与哈希见 ledger_recheck_r4.json / existing_evidence_r4.log。既有账本不含逐笔短缺轨迹，该项由 T4 合成测试覆盖。

- 依据：t7_ruling.md；同一 DuckDB、7 实体 102 址、供应量 998158041739995、edge_budget 5000000；其余默认，allow-no-labels。
- 原清单 33/33 与 PYTHIA 补充清单 2/2 校验通过；fixture 未修改。
- 退出码：7.0.3 = 2；7.0.4 = 2；阻断原因文本相同：True。
- 账本落盘：[True, True]；T4 失败数：0。
- 历史 fixture q1_peak_anchor.simulation.data_gap_events = 2191，仅信息性并列；与本次实体口径、版本不同，不作相等断言。
- 全量终点 raw 对照与断言见 pythia_diff.json。

## 7.0.3 实际运行

```sh
/usr/local/bin/python3 /var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/eps_703_followup_6g5gmgch/scripts/report/trace_703.py --duckdb /Users/uravvv/.claude/skills/token-chip-analysis/.staging_eps/pythia/s2_work.duckdb --edges-table edges --entity-file /Users/uravvv/.claude/skills/token-chip-analysis/.staging_eps/pythia/entity_file_flat.json --allow-no-labels --total-supply 998158041739995 --edge-budget 5000000 --out /Users/uravvv/.claude/skills/token-chip-analysis/.staging_eps/pythia/t7_compare/ledger_703.json
```

- cwd：`/Users/uravvv/.claude/skills/token-chip-analysis`；exit 2；耗时 560.186 秒。
- 算法 SHA-256：`ff4b640a1adbcecf8f3651efbda04493d3085754f939da1ef23b8d9f2efe0fc3`。
- 完整日志：`pythia_run_703.log`；stderr 文件：`pythia_run_703.stderr.txt`。

### stderr 原文（空则标明）

```text
(empty; 0 bytes)
```

### 阻断原因原文（stdout）

```text
[source_trace]   ✗ e_cex_binance_alpha current 三策略主导终点翻转未获裁决收据覆盖——真实多来源结构须 flip-adjudications/v1 书面裁决后重跑
[source_trace]   ✗ e_cex_binance_alpha peak 三策略主导终点翻转未获裁决收据覆盖——真实多来源结构须 flip-adjudications/v1 书面裁决后重跑
[source_trace]   ✗ e_h9 current 三策略主导终点翻转未获裁决收据覆盖——真实多来源结构须 flip-adjudications/v1 书面裁决后重跑
[source_trace] 敏感性不稳：消费策略主导翻转未获合法裁决收据覆盖，或事件顺序未决量达到实质线——结论不得发布（exit 2）。真实多来源结构须造 flip-adjudications/v1 裁决收据（含逐锚点 flip_fingerprint 与三策略披露）后 --acknowledge-flip <收据> 重跑；顺序未决须补齐 block/slot + tx + log/instruction 序号
```

## 7.0.4 实际运行

```sh
/usr/local/bin/python3 /Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/entity_source_trace.py --duckdb /Users/uravvv/.claude/skills/token-chip-analysis/.staging_eps/pythia/s2_work.duckdb --edges-table edges --entity-file /Users/uravvv/.claude/skills/token-chip-analysis/.staging_eps/pythia/entity_file_flat.json --allow-no-labels --total-supply 998158041739995 --edge-budget 5000000 --out /Users/uravvv/.claude/skills/token-chip-analysis/.staging_eps/pythia/t7_compare/ledger_704.json
```

- cwd：`/Users/uravvv/.claude/skills/token-chip-analysis`；exit 2；耗时 529.334 秒。
- 算法 SHA-256：`e85acee4e9a98a664d9b4881ca33177003aa9455261109a01e111e6faeda3cd1`。
- 完整日志：`pythia_run_704.log`；stderr 文件：`pythia_run_704.stderr.txt`。

### stderr 原文（空则标明）

```text
(empty; 0 bytes)
```

### 阻断原因原文（stdout）

```text
[source_trace]   ✗ e_cex_binance_alpha current 三策略主导终点翻转未获裁决收据覆盖——真实多来源结构须 flip-adjudications/v1 书面裁决后重跑
[source_trace]   ✗ e_cex_binance_alpha peak 三策略主导终点翻转未获裁决收据覆盖——真实多来源结构须 flip-adjudications/v1 书面裁决后重跑
[source_trace]   ✗ e_h9 current 三策略主导终点翻转未获裁决收据覆盖——真实多来源结构须 flip-adjudications/v1 书面裁决后重跑
[source_trace] 敏感性不稳：消费策略主导翻转未获合法裁决收据覆盖，或事件顺序未决量达到实质线——结论不得发布（exit 2）。真实多来源结构须造 flip-adjudications/v1 裁决收据（含逐锚点 flip_fingerprint 与三策略披露）后 --acknowledge-flip <收据> 重跑；顺序未决须补齐 block/slot + tx + log/instruction 序号
```

## 逐实体事件数

| 实体 | data_gap_events 旧→新 | fp_residual_events 旧→新 |
|---|---:|---:|
| e_dev | 2054 → 0 | 0 → 2054 |
| e_h9 | 1991 → 0 | 0 → 1991 |
| e_cex_binance_alpha | 2099 → 0 | 0 → 2099 |
| e_lp[^event-count] | 11145 → 3 | 0 → 11139 |
| hx_rotator_0109 | 2092 → 0 | 0 → 2092 |
| hx_supply_chain | 2009 → 0 | 0 → 2009 |
| hx_hub_2q5w9t | 2078 → 0 | 0 → 2078 |

[^event-count]: 事件计数不承诺不变；拆桶后的浮点舍入使部分边界短缺落到 EPS 以下，不再产生事件，因此新计数 3 + 11139 = 11142，比旧计数 11145 少 3 次，不要求两版事件数守恒。

## 逐锚点数量

| 实体 | 锚点 | stock_raw 旧/新相同值 | Σraw 旧/新相同值 | data_gap 旧→新 | fp_residual 新 | T4 |
|---|---|---:|---:|---:|---:|---|
| e_dev | current | 0 / 0 | 0 / 0 | 0 → 0 | 0 | PASS |
| e_dev | peak | 64393693625888 / 64393693625888 | 64393693625888 / 64393693625888 | 0 → 0 | 0 | PASS |
| e_h9 | current | 12061341704660 / 12061341704660 | 12061341704654 / 12061341704654 | 0 → 0 | 0 | PASS |
| e_h9 | peak | 183760117556662 / 183760117556662 | 183760117556656 / 183760117556656 | 0 → 0 | 0 | PASS |
| e_cex_binance_alpha | current | 155377793096056 / 155377793096056 | 155377793096047 / 155377793096047 | 0 → 0 | 0 | PASS |
| e_cex_binance_alpha | peak | 188065369215802 / 188065369215802 | 188065369215795 / 188065369215795 | 0 → 0 | 0 | PASS |
| e_lp | current | 36254349538946 / 36254349538946 | 36254349538936 / 36254349538936 | 6827586 → 6827586 | 0 | PASS |
| e_lp | peak | 135324577844399 / 135324577844399 | 135324577844395 / 135324577844395 | 0 → 0 | 0 | PASS |
| hx_rotator_0109 | current | 0 / 0 | 0 / 0 | 0 → 0 | 0 | PASS |
| hx_rotator_0109 | peak | 36399538236003 / 36399538236003 | 36399538235998 / 36399538235998 | 0 → 0 | 0 | PASS |
| hx_supply_chain | current | 44201009748514 / 44201009748514 | 44201009748510 / 44201009748510 | 0 → 0 | 0 | PASS |
| hx_supply_chain | peak | 123461079593822 / 123461079593822 | 123461079593817 / 123461079593817 | 0 → 0 | 0 | PASS |
| hx_hub_2q5w9t | current | 121855801177 / 121855801177 | 121855801173 / 121855801173 | 0 → 0 | 0 | PASS |
| hx_hub_2q5w9t | peak | 90729347866833 / 90729347866833 | 90729347866828 / 90729347866828 | 0 → 0 | 0 | PASS |
