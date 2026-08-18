# 批 5 T3：5 元组 grep 清零与 legacy 白名单

## 1. 扫描方法

先对全仓（排除 `.git`，不排除 maintenance 历史）宽扫 `legacy-sol5/legacy_sol5/5 元组/五元组`、
`len(row) ==/!= 5`、五变量解包与五列构造；再对所有 Python 文件执行结构命中清单：

```text
rg -l "len\([^\n]+\)\s*(==|!=)\s*5|ts,\s*slot,\s*(src|from|f),\s*(dst|to|t),\s*(amt|amount)\s*(=|\)\))" \
  . --glob '*.py' --glob '!.git/**' --glob '!**/__pycache__/**' | sort
```

只有 8 个文件命中（其中 1 个是守卫测试自身登记的正则）：

```text
maintenance/repair-20260814-batch2/import_pythia_legacy.py
maintenance/repair-20260817-sqd-v4/tools/arc_parts_oracle.py
maintenance/repair-20260817-sqd-v4/tools/live_window_verify.py
scripts/report/wave_scan.py
scripts/solana/audit_closed_accounts.py
scripts/solana/fetch_sqd_transfers_v2.py
scripts/solana/replay_edges.py
scripts/tests/test_batch6_sqd_v4_blind_review.py
```

正式非白名单零命令：

```text
rg -n "len\([^\n]+\)\s*(==|!=)\s*5|ts,\s*slot,\s*(src|from|f),\s*(dst|to|t),\s*(amt|amount)\s*(=|\)\))" \
  scripts --glob '*.py' --glob '!scripts/tests/**' \
  --glob '!scripts/report/wave_scan.py' \
  --glob '!scripts/solana/audit_closed_accounts.py' \
  --glob '!scripts/solana/fetch_sqd_transfers_v2.py' \
  --glob '!scripts/solana/replay_edges.py'
```

实际 rc=1（`rg` 零命中），守卫包装输出：

```text
PASS: 正式非白名单 Python 路径 5 元组解析/解包命中=0
```

## 2. 现役 legacy 解析白名单

| 文件 | 允许点 | 与正式路径隔离证据 | 结论 |
|---|---|---|---|
| `scripts/solana/replay_edges.py` | `_normalize_legacy_edge` 解析严格 5 元组 | 只有 `--legacy-sol5` 才进入；要求 v3 meta；控制台强制 `non_formal=true order_ambiguous=true`；`reconcile/evolution` 明确 BLOCK；正式分支调用严格 7 元组 `_validate_formal_edge` | 白名单 |
| `scripts/report/wave_scan.py` | `load_sol(..., legacy_sol5=True)` | 只有 `--legacy-sol5`＋`--edges-sol` 才进入；receipt 强制 `non_formal/order_ambiguous`；默认分支按 `EDGE_SCHEMA_FIELDS` 要求 7 元组 | 白名单 |
| `scripts/solana/audit_closed_accounts.py` | `load_edge_index(..., legacy_sol5=True)` | 只有 `--legacy-sol5` 才进入；报告强制 `non_formal/order_ambiguous`；默认分支调用 `validate_edge_row` 严格 7 元组；该入口仅保留 slot+owner 旧案覆盖审计 | 白名单 |

## 2.1 HyperSync 五元组构造死代码豁免

| 文件 | 允许点 | 不可达证据 | 结论 |
|---|---|---|---|
| `scripts/solana/fetch_sqd_transfers_v2.py:448` | `HyperSyncFetcher.scan_area` 内 `edges.append((ts, slot, f, t, amt))` | `run(hs_cfg=...)` 在 `:967-969` 首个业务请求前 exit 2；CLI `--hypersync` 在 `:1327-1329` 同样前置 exit 2。正式 v4 只走 SQD Fetcher，不能抵达该构造。 | **死代码豁免**；不是现役 legacy 入口。若任一前置拒绝被移除，须先删除或升级此构造并重新登记 producer。 |

另有 4 个现役文件仅出现 legacy 防线文案，不解析 5 元组：

- `entity_source_trace.py`、`flow_anomaly_scan.py`：参数在正式传导链入口直接拒绝；
- `adjudication_validator.py`、`handoff_manifest.py`：拒收 non-formal/legacy 诊断件进入裁决或 READY。

## 3. maintenance 与测试豁免

| 文件/目录 | 豁免理由 |
|---|---|
| `maintenance/repair-20260814-batch2/import_pythia_legacy.py` | 冻结的旧批次 PYTHIA staging importer，不在 `scripts/` 现役面，不签发 v4 producer 身份 |
| `maintenance/repair-20260817-sqd-v4/tools/arc_parts_oracle.py` | 批 4 一次性只读 oracle，职责就是读取冻结的旧 5 元组 parts 比较 multiset 与 DISTINCT |
| `maintenance/repair-20260817-sqd-v4/tools/live_window_verify.py` | 批 5 一次性验收工具，只读案内 5 元组 tx-aware 对照，和本仓库 v4 7 元组投影做 multiset 比较 |
| `scripts/tests/` | fixture/负测，不是生产入口；legacy/v3 相关命中只在 6 个测试文件中 |
| maintenance `*.md/*.log/staging-*` | 历史工单、交付证据、日志或冻结 staging 实物；不属于现役代码路由，禁止为 grep 数字改写历史 |

测试路径相关文件机器清单：

```text
scripts/tests/test_entity_source_trace.py
scripts/tests/test_flow_anomaly.py
scripts/tests/test_r9_batch3_solana_observation.py
scripts/tests/test_repair_batch_d.py
scripts/tests/test_sqd_consumer_v4.py
scripts/tests/test_wave_scan.py
scripts/tests/test_batch6_sqd_v4_blind_review.py
```

## 4. 结论

- 现役正式**可达**路径 5 元组解析/构造违规：**0**。
- 现役 legacy 解析白名单：**3 个文件**，均由显式 CLI 开关隔离并带 non-formal/READY 阻断。
- HyperSync 不可达五元组构造死代码豁免：**1 个文件、1 处**，两条前置硬拒证据如上。
- maintenance 一次性读取豁免：**3 个文件**。
- 为清零数字而改写历史文档/日志：**0**。
