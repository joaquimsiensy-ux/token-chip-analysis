# scan-schemas — 机械扫描产物 schema 冻结（v6.8.0）

四个扫描/溯源产物的**唯一权威字段定义**。实现脚本与契约测试对本文件写；改字段先改这里再改代码。
适用脚本：`wave_scan.py`（wave-scan/v2）、`flow_anomaly_scan.py`（flow-anomaly/v1）、
`entity_source_trace.py`（provenance-ledger/v1）、裁决台账（candidate-adjudications/v1，−2 判断层手工产出、validator 机器校验）。

## 0. 三条公共纪律

1. **稳定 ID＝内容派生**：候选 ID 由其核心内容（成员集/面额/地址）哈希派生——内容变则 ID 变，旧裁决按 ID 对不上自动失效。
2. **裁决绑定候选内容哈希**：每条裁决记录 `candidate_sha256`＝裁决时该候选完整 JSON 的规范化哈希（`json.dumps(obj, sort_keys=True, ensure_ascii=False)` 的 sha256）。validator 重验：当前报告同 ID 候选哈希不一致＝候选内容已变＝裁决过期，exit 2。
3. **零静默截断**：所有成员/收方/来源数组全量落盘，数组长度必须等于对应 `*_count` 字段（闭合断言）；stdout 只显 top 不代表文件截断。

## 1. wave-scan/v2（wave_scan.py）

与 v1 的语义差异（**不得冒充 v1**，handoff 校验按版本严格匹配）：
扫描对象从"清零层"改为**全体历史峰值 ≥0.02% 地址**（三桶标签）；A 指纹两层（seed_window 触发→expanded_wave 生长）；C 口径改"峰值→30% 峰值耗时 ≤30 日"；D 参数四条合一；成员零截断；负余额升 exit 2；聚类时间轴用抗 dust 的 `first_meaningful_day`。

```
{
  "schema": "wave-scan/v2",
  "generated_at": ISO8601,
  "params": {…全部命令行参数…},
  "total_supply_raw": str,
  "edges": int,
  "scan_universe_count": int,          # 峰值≥门槛的地址总数（不做现仓过滤）
  "retention_buckets": {"cleared": int, "partial_exit": int, "retained": int},
  "negative_balance_addrs": int,       # >0 且触发闸条件时脚本已 exit 2，正常产物恒 0 或未达实质线
  "first_meaningful_ratio": float,     # 抗 dust 阈值：首日末余额≥自身峰值×此比例才算有意义首建
  "waves": [{
    "id": "wave-<sha256(','.join(sorted(addrs)))[:12]>",
    "seed_window": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD",
                     "member_count": int, "combined_peak_pct": float},   # 触发证据：真实 7 日窗自身达标
    "build_window": [start, end],      # expanded_wave 生长后的全窗
    "launch_window": bool,
    "cohort_hint": str|null,           # B≈0 且成员巨多 → 外部用户潮提示（保持 v6.6.1 原样）
    "member_count": int,
    "combined_peak_pct": float, "combined_peak_date": date,
    "final_pct": float,
    "retention_buckets": {"cleared": int, "partial_exit": int, "retained": int},
    "fingerprints": {
      "A_seed_window": true,
      "B_feeder_exclusive": {"members": int, "rate": float, "hit": bool},   # 算法保持 v6.6.1 原样
      "C_peak_to_30pct": {"days": int|null, "hit": bool}   # 峰值→30%峰值耗时；null=数据末仍未跌破
    },
    "score": int,                      # 1 + B_hit + C_hit（公式保持 v6.6.1 结构）
    "recycle_top": [{"to": addr, "pct": float}],
    "members": [{"addr", "first_in", "first_meaningful", "peak_pct",
                  "retention_bucket": "cleared|partial_exit|retained",
                  "feeder_exclusive": bool}]   # 全量，len == member_count
  }],
  "equal_amount_groups": [{             # D 四条合一：同精确面额＋单笔≥0.001%供应＋7日滑窗≥20收方＋组合计≥1%供应
    "id": "eqg-<amount_raw>-<sha256(','.join(sorted(recipients)))[:8]>",
    "amount_raw": str,
    "recipients": int, "tx_count": int,
    "group_total_pct": float,          # 该面额全部转账（排 mint/burn 哨兵）合计过手 / 总供应
    "densest_7d_window": {"start": date, "recipients": int},   # 触发证据
    "window": [first, last], "window_days": float,             # 展示字段（时间紧凑度不做过滤）
    "top_sender": addr, "top_sender_recv_share": float,
    "top_sender_global_out_degree": int,   # 主发送方全局 distinct 收方数——设施撞衫裁决必看
    "retention": float,
    "members": [addr…]                  # 全量收方，len == recipients
  }],
  "requires_adjudication": bool,
  "note": str
}
```

**D 裁决纪律**（写给 −2）：每个等额组必查 `top_sender_global_out_degree`——上千＝场内设施整数面额"撞衫"（用户买整数金额自然撞面额），可批量定性关闭；个位数＝定向分仓信号。

## 2. flow-anomaly/v1（flow_anomaly_scan.py）

汇集点＋分发点两类候选（codex 第三路①②；参数全部为待回测初值，不是拍板值）。

```
{
  "schema": "flow-anomaly/v1",
  "generated_at": ISO8601, "params": {…}, "total_supply_raw": str,
  "eligible_universe_count": int,      # 合格地址（历史峰值≥0.02%）数——来源/收方均不限清零层
  "sinks": [{                          # 汇集点：滚动窗内从多来源收币
    "id": "sink-<addr>",
    "addr": addr,
    "best_window": {"start": date, "end": date,
                     "inflow_pct": float, "source_count": int},
    "sources": [{"addr", "pct", "retention_bucket"}],   # 全量，len == best_window.source_count
    "launch_window": bool
  }],
  "sprays": [{                         # 分发点：双模式（PYTHIA 回测校准）
    "id": "spray-<addr>",
    "addr": addr,
    "mode": "pulse|slow_spray",
    #   pulse＝脉冲式：滑窗内向新地址群集中灌仓（escrow 型）——窗内新收方 ≥20 且流出 ≥2%
    #   slow_spray＝慢速批发：匀速出货任何滑窗都不突出（H9 三派发器型）——
    #     全史 distinct 收方 ≥500 且全史流出 ≥2%
    "all_time": {"outflow_pct": float, "recipient_count": int, "fresh_recipient_count": int},
    "best_window": {…}|null,           # pulse 时非空
    "recipients": [addr…],             # pulse：全量，len == best_window.new_recipient_count
    "recipients_top": [addr…],         # slow_spray：按累计收量 top ≤500（显式摘要非静默截断，
                                       #   全量数在 all_time.recipient_count）
    "launch_window": bool              # 发射窗打标不滤
  }],
  "requires_adjudication": bool
}
```

公共纪律：唯一转账去重、mint/burn 排除、known-entity 内部流转不计（有实体表时）、分母与 cutoff 与 wave_scan 完全一致。"新地址"判定复用 wave-scan 的 `first_meaningful_day` 抗 dust 定义。
滑窗判定纪律：达标窗＝**同一窗内同时**满足金额线与数量线（在全部达标窗中取金额最大者展示）——不得先取金额最大窗再验数量（PYTHIA 回测实证：Q1 金额最大窗 22.2% 恰好来源仅 4 个被拒，而另存在 14 来源/18.8% 的双达标窗）。

**sink/spray 的裁决对象**：枢纽地址本身（sources/recipients 是证据不是裁决对象）——candidate-adjudications 对此两类候选的成员全集＝`{addr}` 单元素集（§3 validator 按候选类型区分校验）。

## 3. candidate-adjudications/v1（−2 判断层产出，validator 校验）

wave/flow/eqg 全部候选的**成员级**裁决台账。freeze 前 validator 全量校验，缺漏即 exit 2。

```
{
  "schema": "candidate-adjudications/v1",
  "case": str, "adjudicated_at": ISO8601,
  "source_reports": {"wave_scan_report.json": sha256, "flow_anomaly_report.json": sha256},
  "adjudications": [{
    "candidate_id": str,               # 必须与源报告候选 ID 严格一致
    "candidate_sha256": str,           # 裁决时源候选完整 JSON 规范化哈希（§0.2）
    "candidate_verdict": "pattern_confirmed|excluded|unresolved",
    "accepted_members": [addr…],       # 判入协同实体的成员（候选天然混入独立地址，必须成员级处置）
    "excluded_members": [{"addr", "reason"}],
    "linked_entity_id": str|null,      # pattern_confirmed 时并入/新建的实体 ID
    "evidence": [str…],                # 证据引用（文件/查询/判例）
    "tier_impact": {                   # 防自证免责：数值机器算，人工只能解释
      "max_possible_impact": {"combined_peak_pct": float, "nearest_tier_line": str,
                               "could_change_tiering": bool},   # validator 重算比对，人工不得改数
      "note": str
    }
  }]
}
```

**validator 拒绝规则（六类契约测试全覆盖）**：①缺文件；②源报告候选 ID 集 ≠ 裁决 ID 集（少裁/多裁/未知 ID）；③重复 ID；④candidate_sha256 与当前源报告不符（候选内容已变）；⑤accepted+excluded ∪ ≠ 候选成员全集（部分成员未裁；eqg 候选按收方集）；⑥could_change_tiering 与机器重算不符（伪造 tier_impact）。unresolved 且机器判 could_change_tiering=true → freeze exit 2。

## 4. provenance-ledger/v1（entity_source_trace.py）

已知实体每址币源溯源台账。**记账分母两锚点**（不对全史毛流入归一化——周转会重复计源）。

```
{
  "schema": "provenance-ledger/v1",
  "generated_at": ISO8601, "case": str, "total_supply_raw": str,
  "entities": [{
    "entity_id": str,
    "member_count": int,
    "anchors": {
      "current":  {"stock_raw": str, "composition": [TERMINAL…], "direct_upstream": [UPSTREAM…]},
      "peak":     {"date": date, "stock_raw": str, "composition": [TERMINAL…], "direct_upstream": [UPSTREAM…]}
    },
    # direct_upstream＝锚点库存的**第一跳**构成（直接上家聚合，"进货单"）——与 composition
    # （终点构成）互补：W1 漏检教训正是 Q1 进货单上 9 根 W1 藤裸露却无人看；直接上家是
    # 中间节点会被继续穿透，终点构成里不可见，故单列。UPSTREAM = {"addr", "pct_of_anchor", "raw"}
    "turnover": {"gross_in_raw": str, "gross_out_raw": str},        # 毛流转另计，不参与构成归一化
    "closure_check": {"current_sum_pct": float, "peak_sum_pct": float}   # 两锚点各 Σ=100%±容差
  }],
  "unresolved_total_pct": float,
  "bounds_sensitivity": {"method": "pro-rata", "conservative_vs_aggressive_verdict_stable": bool}
}

TERMINAL = {
  "kind": "PROVEN_ORIGIN|BOUNDARY|UNRESOLVED",
  "subkind":  # PROVEN_ORIGIN: mint|launch_alloc|proven_airdrop|proven_vesting
              # BOUNDARY: dex_pool|cex_confirmed|facility_confirmed|bridge
              # UNRESOLVED: data_gap|depth_limit|same_slot_scc|prune_residual|facility_candidate
  "via": addr|null,                    # 边界地址/断点地址
  "pct_of_anchor": float, "raw": str,
  "evidence_level": "label_confirmed|onchain_pattern|heuristic",
  "path_len": int
}
```

**硬规则**（复核翻案教训，全部进契约测试）：
- 支路级停止：设施来的支路停（记 BOUNDARY/facility 或 UNRESOLVED/facility_candidate），同一钱包的其他支路必须继续穿透（3yMk 教训：EwUU8oi 来的 8.77% 停、10 条 W1 支路继续）。
- "DEX 池流出"只能记 `dex_pool` 边界，**不得写成"swap 买入"**（现有数据无对价腿）。
- 设施认定：标签库确证＝`facility_confirmed`；启发式命中（对手方≥1000 且双向）只记 `facility_candidate` 归 UNRESOLVED。
- 实体内部先收缩单一边界，内部互转不追溯不重复计源。
- 同 slot 环（无 tx 内序号）SCC 收缩记 `same_slot_scc`；深度上限（默认 10 跳）记 `depth_limit`；剪枝残差全部入 UNRESOLVED **不静默丢弃**。
- pro-rata 主法＋保守/激进上下界：界内终点类别与判级不变→过，变→阻断发布。

## 5. PYTHIA 回测锚点（fixture 权威值；实现落地时实测填入 tests/fixtures/pythia_anchors.json）

| 闸 | 锚点义务 |
|---|---|
| A | 存在 7 日种子窗 ≥20 员且合并峰 ≥10%（W1 金标窗）；expanded_wave 覆盖 W1 341 址 ≥85% |
| B | W1 候选 B rate / exclusive 数与实现后实测基线一致（算法保持 v6.6.1；扫描对象扩大后数值允许与 v6.6.1 清零层版不同，以新实测为准并记录两版数字） |
| C | W1 峰→30% 实测 72 天不触发＝预期（负例）；头注注记 |
| D | 四条合一下 PYTHIA 恰报 7 组、44 分仓（1e12 面额）置顶（组过手 33.66%）且 ID 稳定 |
| flow | 汇集点 Q1 与 3yMk 过阈值；分发点 H9 三派发器（合计 13.47% 派 6,503 收方）命中 |
| 溯源 | Q1 峰值锚点构成表 9 个 W1 直接上家现形；3yMk 支路停 EwUU8oi 而 10 条 W1 支路穿透 |

回测仅 PYTHIA 单案（用户拍板）；flow 参数初值与误报水平缺第二币对照校准——未来首个新案实战时如实标注此局限。
