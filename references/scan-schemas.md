# scan-schemas — 机械扫描产物 schema 冻结（v6.8.1）

四个扫描/溯源产物的**唯一权威字段定义**。实现脚本与契约测试对本文件写；改字段先改这里再改代码。
适用脚本：`wave_scan.py`（wave-scan/v2）、`flow_anomaly_scan.py`（flow-anomaly/v1）、
`entity_source_trace.py`（provenance-ledger/v2）、裁决台账（candidate-adjudications/v1，−2 判断层手工产出、validator 机器校验）。

## 0. 四条公共纪律

1. **稳定 ID＝内容派生**：候选 ID 由其核心内容（成员集/面额/地址）哈希派生——内容变则 ID 变，旧裁决按 ID 对不上自动失效。
2. **裁决绑定候选内容哈希**：每条裁决记录 `candidate_sha256`＝裁决时该候选完整 JSON 的规范化哈希（`json.dumps(obj, sort_keys=True, ensure_ascii=False)` 的 sha256）。validator 重验：当前报告同 ID 候选哈希不一致＝候选内容已变＝裁决过期，exit 2。
3. **零静默截断**：所有成员/收方/来源数组全量落盘，数组长度必须等于对应 `*_count` 字段（闭合断言）；stdout 只显 top 不代表文件截断。
4. **本文件＝完整字段登记**（v6.8.1，codex 复核 P2 采纳）：脚本实际输出的每个字段都必须在此登记——未登记字段不得输出，登记了的不得静默删除；公共通用字段（`schema/generated_at/params/total_supply_raw/edges/note`）各产物一律在场，下文不再逐一重复。输入边表的唯一性由采集管线（four-check 对账）保证，扫描器不去重——同五元组合法重复真实存在（同秒同额多笔），fail-closed 去重会误杀。

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
  "negative_balance_addrs": int,       # 历史逐日末余额**最低点**为负的地址数（v6.8.1：不只看期末——
                                       #   "先负后回正"是数据缺失自愈假象；达闸条件时脚本已 exit 2）
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
    "densest_7d_window": {"start": date, "recipients": int},   # 触发证据：窗内 distinct 收方数
    "window": [first, last], "window_days": float,             # 展示字段（时间紧凑度不做过滤）
    "top_sender": addr,                # 触达 distinct 收方**最多**的发送方（按事件数选会被
                                       #   "对同一收方反复发"绑架，裁决问的是"这组收方主要是谁喂的"）
    "top_sender_recv_share": float,    # top_sender 触达的 distinct 收方 / 组收方总数
    "top_sender_global_out_degree": int,   # 主发送方全局 distinct 收方数——设施撞衫裁决必看
    "retention": float,
    "members": [addr…]                  # 全量收方，len == recipients
  }],
  # D 滑窗纪律（v6.8.1 codex 复核修复）：滑窗扫该面额**全部转账事件**、窗内动态数
  # distinct 收方——不得按"每收方首次收到该面额"去重（会吞掉复收事件：同批收方分两轮
  # 收同面额时第二轮全盲，与"任意 7 日滑窗 ≥N 个不同收方"定义不等价）。
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
  "generated_at": ISO8601, "params": {…}, "total_supply_raw": str, "edges": int,
  "eligible_universe_count": int,      # 合格地址（历史峰值≥0.02%）数——来源/收方均不限清零层
  "sinks": [{                          # 汇集点：滚动窗内从多来源收币
    "id": "sink-<addr>",
    "addr": addr,
    "best_window": {"start": date, "end": date,
                     "inflow_pct": float, "source_count": int},
    "balance": {"historical_peak_pct": float, "current_balance_pct": float},
    "all_time": {"net_inflow_pct": float, "qualified_inflow_pct": float},
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
  "requires_adjudication": bool,
  "note": str
}
```

公共纪律：mint/burn 排除；`--entity-file` 抵消只对**同一实体**内部流转生效（按 entity_id 分组，跨实体转账保留——v6.8.1：拍平成单一集合会把实体间真实转账当内部边删掉；同址跨实体名册即拒）；分母与 cutoff 与 wave_scan 完全一致；输入唯一性由采集管线保证（§0.4）。"新地址"判定复用 wave-scan 的 `first_meaningful_day` 抗 dust 定义。
滑窗判定纪律：达标窗＝**同一窗内同时**满足金额线与数量线（在全部达标窗中取金额最大者展示）——不得先取金额最大窗再验数量（PYTHIA 回测实证：Q1 金额最大窗 22.2% 恰好来源仅 4 个被拒，而另存在 14 来源/18.8% 的双达标窗）。

**sink/spray 的裁决对象**：枢纽地址本身（sources/recipients 是证据不是裁决对象）——candidate-adjudications 对此两类候选的成员全集＝`{addr}` 单元素集（§3 validator 按候选类型区分校验）。
sink 的判级最大影响不得只取单一最佳窗：validator 取 `best_window.inflow_pct`、
`balance.historical_peak_pct`、`balance.current_balance_pct`、`all_time.net_inflow_pct`
四者最大值。旧产物缺后三项即拒重跑，防多个不重叠小窗累计跨过 5% 判级线。

## 3. candidate-adjudications/v1（−2 判断层产出，validator 校验）

wave/flow/eqg 全部候选的**成员级**裁决台账。freeze 前 validator 全量校验，缺漏即 exit 2。

```
{
  "schema": "candidate-adjudications/v1",
  "case": str, "adjudicated_at": ISO8601,   # validate 时必须已填（未填即拒）
  "source_reports": {"wave_scan_report.json": sha256, "flow_anomaly_report.json": sha256},
  "adjudications": [{
    "candidate_id": str,               # 必须与源报告候选 ID 严格一致
    "candidate_kind": "wave|eqg|sink|spray",   # template 预填，validator 与机器判定比对
    "candidate_sha256": str,           # 裁决时源候选完整 JSON 规范化哈希（§0.2）
    "candidate_verdict": "pattern_confirmed|excluded|unresolved",
    "accepted_members": [addr…],       # 判入协同实体的成员（候选天然混入独立地址，必须成员级处置）
    "excluded_members": [{"addr", "reason"}],   # reason 逐条必填非空
    "linked_entity_id": str|null,      # pattern_confirmed 时并入/新建的实体 ID（必须存在于实体名册）
    "evidence": [str…],                # 证据引用（文件/查询/判例）；pattern_confirmed 时必须非空
    "tier_impact": {                   # 防自证免责：数值机器算，人工只能解释
      "max_possible_impact": {"combined_peak_pct": float, "nearest_tier_line": str,
                               "could_change_tiering": bool},   # validator 三字段逐一重算比对，人工不得改数
      "note": str
    },
    "_members_total": [addr…]          # template 预填的候选成员全集（⑤校验的机器参照；−2 填写时删除亦可，
                                       #   validator 以源报告重算为准不读此字段）
  }]
}
```

**validator 拒绝规则（八类契约测试全覆盖，v6.8.1 加固）**：①缺文件；②源报告候选 ID 集 ≠ 裁决 ID 集（少裁/多裁/未知 ID），源报告 schema 错版/重复候选 ID 同拒；③重复裁决 ID；④candidate_sha256 与当前源报告不符（候选内容已变）；⑤accepted+excluded ∪ ≠ 候选成员全集（部分成员未裁；eqg 候选按收方集）；⑥tier_impact 三字段任一与机器重算不符（伪造）；⑦verdict 语义交叉约束——pattern_confirmed 必须 accepted 非空＋linked_entity_id＋evidence 非空，excluded/unresolved 必须 accepted 为空，excluded_members 逐条必须有非空 reason，candidate_kind 必须与机器一致，adjudicated_at 必须已填；⑧实体名册绑定（`validate --entity-file`，freeze 强制传入）——linked_entity_id 必须存在于名册、accepted 成员必须已落入该实体名册，存在 pattern_confirmed 而未传名册即拒。unresolved 且机器判 could_change_tiering=true → freeze exit 2。

## 4. provenance-ledger/v2（entity_source_trace.py）

已知实体每址币源溯源台账。**记账分母两锚点**（不对全史毛流入归一化——周转会重复计源）。

**v2 算法冻结（正向模拟；v1 一律作废重跑）**：v1 的"截至 T 全部历史流入按金额归一化"
数学错误——比例守恒只在单次流出瞬间成立，流入流出交错时老来源被消耗的份额不会缩水
（反例：先收 A 100→转出 90→再收 B 90，真实库存 A 10%/B 90%，v1 算成 52.6/47.4；
2026-08-01 codex 验收 P0-1）。v2 改为**祖先子图正向模拟**：逆向 BFS 收集上游节点
（遇 mint/标签/设施终点停，深度＝距实体最短跳数）→ 子图内全部 ≤T 转账按可证链上位置
`(ts, slot/block, transaction_index, log/instruction_index)` 逐笔重演，每节点维护来源构成账户（流入转移入账、流出等比扣减，
实体成员收缩为单一超级账户）→ 锚点时刻账户向量＝库存终点构成。总量守恒由构造保证
（closure 降为实现自检）；回环天然良定义（v1 的 `same_slot_scc` 终点类别**废除**）；
禁止按地址拓扑重排同秒边。缺精确位置时保留 ingest 观察序，但同一最细粒度桶内
“既收又发”的流出来源整笔记 `UNRESOLVED/order_ambiguous`；占锚点库存 >0.5% 时
独立顺序敏感性阻断。Solana 旧 5 元组只有 slot，扩展 7 元组
`[ts,slot,tx_index,instruction_index,from,to,amt]` 才是精确序。

```
{
  "schema": "provenance-ledger/v2",
  "generated_at": ISO8601, "case": str, "params": {…}, "total_supply_raw": str,
  "input_binding": {
    "algorithm": {"script_sha256": str,
                  "files": {"entity_source_trace.py": {…}, "wave_scan.py": {…}},
                  "policies": [str…], "order_material_pct": float},
    "source": {"kind": "sol|evm_v2|duckdb", "argument": str, "edges_table": str|null,
               "files": [{"path", "bytes", "sha256"}…]},
    "entity_file": {"path", "bytes", "sha256"},
    "labels_file": {"path", "bytes", "sha256"}|null,
    "handoff_manifest": {"file": {…}, "run_id": str, "scope": object},
    "data_map": {"file": {…}, "paths": [str…]},
    "total_supply_raw": str,
    "algorithm_params": {"depth_limit", "facility_min_degree", "node_budget", "edge_budget"}
  },
  "entities": [{
    "entity_id": str,
    "member_count": int,
    "members_sha256": str,             # sha256(",".join(sorted(成员集)))——freeze 与名册逐实体绑定，
                                       #   名册改动后的旧台账自动失效（v6.8.1 P0-2 修复）
    "anchors": {
      "current":  {"stock_raw": str, "composition": [TERMINAL…], "direct_upstream": [UPSTREAM…]},
      "peak":     {"date": date, "stock_raw": str, "composition": [TERMINAL…], "direct_upstream": [UPSTREAM…]}
    },
    # direct_upstream＝**毛流入事实清单**（≤锚点时刻全史直接上家聚合，零分摊假设、
    # 不随流出扣减；分母＝毛流入总量）：W1 教训的本义是"Q1 从 20 家进过货、9 家是 W1"
    # ——这个事实与那批币现在还在不在无关。周转枢纽的现存库存构成会把早期藤蔓等比消耗
    # 殆尽（PYTHIA 实测 Q1 峰值现存构成 EwUU 100%，W1 藤全部衰减不可见），故进货单必须
    # 毛口径；与 composition（锚点库存终点构成）分母不同、各自成立、互为补充。
    # UPSTREAM = {"addr", "pct_of_gross_in", "raw"}
    "turnover": {"gross_in_raw": str, "gross_out_raw": str},        # 毛流转另计，不参与构成归一化
    "closure_check": {"current_sum_pct": float, "peak_sum_pct": float},  # 构造性守恒的实现自检；
                                       #   freeze 端不读此自报值，按 composition[].raw 重算
    "simulation": {"ancestors": int, "terminals": int, "depth_truncated": int,
                    "budget_truncated": int, "edges_simulated": int,
                    "order_ambiguous_groups": int, "order_ambiguous_events": int,
                    "data_gap_events": int}   # 诊断块
  }],
  "unresolved_total_pct": float,
  "bounds_sensitivity": {
    "methods": ["pro_rata", "fifo", "lifo"],   # 同一模拟骨架三种消耗策略＝真上下界
    "per_entity": {entity_id: {"stable": bool, "consumption_stable": bool,
                    "ordering_stable": bool,
                    "anchors": {anchor: {"top_by_policy": {policy: [kind, sub, via]|null},
                      "policy_details": {policy: [{"terminal": [kind,sub,via], "raw": str}…]},
                      "agree": bool,
                      "ordering_sensitivity": {"status": "RESOLVED|UNRESOLVED",
                        "order_ambiguous_raw": str, "order_ambiguous_pct": float,
                        "materiality_pct": 0.5, "stable": bool}}}},
    "conservative_vs_aggressive_verdict_stable": bool,
    "note": str
  }
}

TERMINAL = {
  "kind": "PROVEN_ORIGIN|BOUNDARY|UNRESOLVED",
  "subkind":  # PROVEN_ORIGIN: mint|launch_alloc|proven_airdrop|proven_vesting
              # BOUNDARY: dex_pool|cex_confirmed|facility_confirmed|bridge
              # UNRESOLVED: data_gap|depth_limit|budget_truncated|facility_candidate|order_ambiguous
  "via": addr|null,                    # 边界地址；via=null 的未决聚合条目按 subkind 合并
  "pct_of_anchor": float, "raw": str,
  "evidence_level": "label_confirmed|onchain_pattern|heuristic",
  "path_len": int|null                 # 终点的 BFS 最短跳数；via=null 聚合条目无单一路径，报 null
}
```

**硬规则**（复核翻案教训，全部进契约测试）：
- 支路级停止：设施来的支路停（记 BOUNDARY/facility 或 UNRESOLVED/facility_candidate），同一钱包的其他支路必须继续穿透（3yMk 教训：EwUU8oi 来的 8.77% 停、10 条 W1 支路继续）——BFS 终点判定逐节点独立，天然成立。
- "DEX 池流出"只能记 `dex_pool` 边界，**不得写成"swap 买入"**（现有数据无对价腿）。
- 设施认定：标签库确证＝`facility_confirmed`；启发式命中（对手方≥1000 且双向）只记 `facility_candidate` 归 UNRESOLVED。
- 实体内部先收缩单一超级账户，内部互转不记账不重复计源；`--entity-file` 强制 {str: 非空 str 数组}、同址跨实体即拒。
- 深度上限（默认 10 跳）记 `depth_limit`、BFS 节点预算超限记 `budget_truncated`、账户被取用时库存不足记 `data_gap`（短缺显式入账）——全部 UNRESOLVED **不静默丢弃**；子图边数超 `--edge-budget` 直接 exit 2（不静默采样）。
- **双维敏感性阻断**：pro_rata 主法出数，fifo/lifo 上下界同跑；任一 stock>0 锚点的第一大终点条目在三策略间不一致，或 `order_ambiguous` >0.5% 锚点库存 → 汇总 false、脚本 exit 2。freeze 不读取 stable 自报作裁决，而从 `policy_details` 重算，并核验 `input_binding` 后以当前代码和当前原始边真实重放；语义摘要不一致即拒。
- **freeze 可复现绑定**：source files 必须同时出现在已 verify 的 manifest artifacts 与 data_map；标签、实体文件、完整源边、total supply、manifest run/scope（cutoff/block/denominators）、算法脚本与参数逐项哈希绑定。任一变化都必须重跑 provenance 并追加 freeze revision；`check-unseal` 复核所有当前绑定文件哈希。

## 5. PYTHIA 回测锚点（fixture 权威值；实现落地时实测填入 tests/fixtures/pythia_anchors.json）

| 闸 | 锚点义务 |
|---|---|
| A | 存在 7 日种子窗 ≥20 员且合并峰 ≥10%（W1 金标窗）；expanded_wave 覆盖 W1 341 址 ≥85% |
| B | W1 候选 B rate / exclusive 数与实现后实测基线一致（算法保持 v6.6.1；扫描对象扩大后数值允许与 v6.6.1 清零层版不同，以新实测为准并记录两版数字） |
| C | W1 峰→30% 实测 72 天不触发＝预期（负例）；头注注记 |
| D | 四条合一下 44 分仓（1e12 面额）置顶且 ID 稳定（v6.8.1 全事件滑窗后组数/densest 以 fixture 新实测为准） |
| flow | 汇集点 Q1 与 3yMk 过阈值；分发点 H9 三派发器（合计 13.47% 派 6,503 收方）命中 |
| 溯源 | Q1 峰值锚点 direct_upstream 中 ≥9 个 W1 直接上家现形；3yMk 支路停 EwUU8oi 而 W1 支路穿透（path_len ≥2）；敏感性 stable（v2 正向模拟实测值以 fixture 为准，v1 数字作废） |

回测仅 PYTHIA 单案（用户拍板）；flow 参数初值与误报水平缺第二币对照校准——未来首个新案实战时如实标注此局限。
