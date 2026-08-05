# scan-schemas — 机械扫描产物 schema 冻结（v6.20.0）

扫描、溯源和分布形态产物的**唯一权威字段定义**。实现脚本与契约测试对本文件写；改字段先改这里再改代码。
适用脚本：`wave_scan.py`（wave-scan/v3）、`flow_anomaly_scan.py`（flow-anomaly/v2）、
`entity_source_trace.py`（provenance-ledger/v2）、`holder_distribution_scan.py`（distribution-scan/v1）、
`distribution_explanation_check.py`（distribution-explanation/v1）和两类裁决台账。

## 本册路由

- §0 公共纪律；§1 wave-scan；§2 flow-anomaly；§3 裁决台账；§4 provenance-ledger；§5 PYTHIA fixture；§6 至 §11 是分布形态契约。

## 0. 四条公共纪律

1. **稳定 ID＝内容派生**：候选 ID 由其核心内容（成员集/面额/地址）哈希派生——内容变则 ID 变，旧裁决按 ID 对不上自动失效。
2. **裁决绑定候选内容哈希**：每条裁决记录 `candidate_sha256`＝裁决时该候选完整 JSON 的规范化哈希（`json.dumps(obj, sort_keys=True, ensure_ascii=False)` 的 sha256）。validator 重验：当前报告同 ID 候选哈希不一致＝候选内容已变＝裁决过期，exit 2。
3. **零静默截断**：所有成员/收方/来源数组全量落盘，数组长度必须等于对应 `*_count` 字段（闭合断言）；stdout 只显 top 不代表文件截断。
4. **本文件＝完整字段登记**（v6.8.1，codex 复核 P2 采纳）：脚本实际输出的每个字段都必须在此登记——未登记字段不得输出，登记了的不得静默删除；公共通用字段（`schema/generated_at/params/total_supply_raw/edges/note`）各产物一律在场，下文不再逐一重复。输入边表的唯一性由采集管线（four-check 对账）保证，扫描器不去重——同五元组合法重复真实存在（同秒同额多笔），fail-closed 去重会误杀。

## 1. wave-scan/v3（wave_scan.py）

与 v1 的语义差异（**不得冒充 v1**，handoff 校验按版本严格匹配）：
扫描对象从"清零层"改为**全体历史峰值 ≥0.02% 地址**（三桶标签）；A 指纹两层（seed_window 触发→expanded_wave 生长）；C 口径改"峰值→30% 峰值耗时 ≤30 日"；D 参数四条合一；成员零截断；负余额升 exit 2；聚类时间轴用抗 dust 的 `first_meaningful_day`。
v3 与 v2 的差异（2026-08-02 codex 复核补闸）：**候选全集逐址落盘**——v2 只落 `scan_universe_count` 一个计数，孤仓不成波次/等额组就从产物消失、发布闸无从对账；v3 新增 `scan_universe` 逐址清单＋`must_adjudicate` 四类机械标记＋`must_adjudicate_count`，`dormant_warehouse_audit.json` 以 `universe_ref{path,sha256}` 绑定本报告，audit_release_gate 做哈希＋集合包含对账。

```
{
  "schema": "wave-scan/v3",
  "generated_at": ISO8601,
  "params": {…全部命令行参数…},
  "total_supply_raw": str,
  "edges": int,
  "scan_universe_count": int,          # 峰值≥门槛的地址总数（不做现仓过滤）
  "scan_universe": [{                  # v3 新增：全集逐址落盘（len == scan_universe_count，零截断）
    "addr": str, "peak_raw": str, "peak_pct": float, "final_raw": str,
    "retention_bucket": "cleared|partial_exit|retained",
    "first_meaningful_day": date, "last_active_day": date,
    "must_adjudicate": bool,           # 四类机械命中任一即 true——静置仓审计候选必须全覆盖
    "must_reasons": ["peak_top200"|"peak_ge_0.1pct"|"drawdown_ge_80pct"|"dormant_ge_30d"]
  }],                                  #   （回落/静置两类带 ≥must-dormant-pct(默认0.05%) 历史大仓门槛）
  "must_adjudicate_count": int,
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

**D 裁决纪律**（写给 −2）：每个等额组必查 `top_sender_global_out_degree`——上千＝场内设施整数面额"撞衫"（用户买整数金额自然撞面额），可批量定性关闭；个位数＝定向分仓信号。**字段口径澄清（2026-08-02）**：该字段名带 "global" 但实际口径是**本币种全史边表的 distinct 收方数**（工程实现口径），不是跨币种全历史出度——它只是裁决参考；枢纽终裁按 methods §6 硬规则块"中间节点三段式检验"的全历史口径（普通＋内部交易）人工核查。

## 2. flow-anomaly/v2（flow_anomaly_scan.py）

汇集点＋分发点两类候选。v1→v2（2026-08-02 用户拍板补两缝＋codex 交叉复核重构）：
缝1＝慢速线 500（H9 单案 6,503 收方校准）过宽，降 100；缝2＝pulse 只数 fresh 新收方，
"向已建仓老地址补货"完全隐形，新增 pulse_all 广义口径；spray 改**多命中结构**（pulse ⊂
pulse_all，单一 mode＋优先级只是选标签会丢证据）；出边零值过滤（amt>0，零值不许凑收方/
来源数）；金额阈值整数运算（meow 案纪律）；窗口浓度两键识别伪分发。参数出身＝PYTHIA
单案回测＋用户设定高召回初值，非多案校准。

```
{
  "schema": "flow-anomaly/v2",
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
  "sprays": [{                         # 分发点：三口径多命中（v2；一址一条 entry）
    "id": "spray-<addr>",
    "addr": addr,
    "mode": "pulse|pulse_all|slow_spray",
    #   主定性标签，取序 pulse > pulse_all > slow_spray（fresh 灌新仓语义最尖）；
    #   pulse＝fresh 脉冲：14 日滑窗内 fresh 边（该笔发生日==收方 first_meaningful_day）
    #     流出 ≥2% 且窗内 fresh 新收方 ≥20（escrow 灌新仓型）
    #   pulse_all＝广义脉冲（v2 新增，堵"向已建仓老地址补货"盲区）：14 日滑窗内全部出边
    #     流出 ≥2% 且窗内 distinct 收方（不限新老）≥20；数学上 pulse ⊂ pulse_all
    #   slow_spray＝慢速批发：全史 distinct 收方 ≥100 且全史流出 ≥2%（匀速出货任何
    #     滑窗都不突出，H9 派发器型兜底；旧线 500 系单案过宽初值，v2 降 100）
    "mode_hits": {                     # 三口径命中事实全记录——顶层 mode 只是主标签，
      "pulse":      {"hit": bool, "best_window": {…}},   # 不得当作"未命中其他口径"的
      "pulse_all":  {"hit": bool, "best_window": {…}},   # 证据；未命中口径无 best_window
      "slow_spray": {"hit": bool}                        # 键；slow_spray 永不带窗
    },
    "all_time": {"outflow_pct": float, "recipient_count": int, "fresh_recipient_count": int},
    "best_window": {…}|null,           # 主模式的窗（slow_spray 主模式＝null）。统一键，
    #   不按 mode 换名：start/end/outflow_pct/recipient_count（窗内全体 distinct 收方）/
    #   fresh_recipient_count（窗内首建当日收方）＋浓度两键 top1_recipient_share_pct/
    #   meaningful_recipient_count（窗内收 ≥0.001% 供应的收方数，线与 wave D 指纹一致）
    #   ——浓度识别"1 笔大额＋N 粉尘凑双线"伪分发，只报不拒，裁决时必看
    "recipients": [addr…],             # pulse 主模式＝主窗 fresh 收方全量（len ==
    #   best_window.fresh_recipient_count）；pulse_all 主模式＝主窗全体收方全量（len ==
    #   best_window.recipient_count）——validator 做闭合校验
    "recipients_top": [addr…],         # slow_spray 主模式：按累计收量 top ≤500（显式摘要
    #   非静默截断，全量数在 all_time.recipient_count）
    "launch_window": bool              # 主模式窗起点（slow_spray 用首出账日）是否落在
                                       #   数据首日+3 内；打标不滤
  }],
  "requires_adjudication": bool,
  "note": str
}
```

公共纪律：mint/burn 排除；`--entity-file` 抵消只对**同一实体**内部流转生效（按 entity_id 分组，跨实体转账保留——v6.8.1：拍平成单一集合会把实体间真实转账当内部边删掉；同址跨实体名册即拒）；分母与 cutoff 与 wave_scan 完全一致；输入唯一性由采集管线保证（§0.4）。"新地址"判定复用 wave-scan 的 `first_meaningful_day` 抗 dust 定义。v2 两条：sink/spray 扫描一律过滤零值边（`amt > 0`——零值转账不许凑来源/收方数）；金额阈值全部整数运算（`pct_to_raw`，浮点比较漏"恰好整数枚"边界）。
v2 残余缝（诚实声明，验收时如实转告）：收方 20~99 且任何 14 日窗不达双线的慢速分发／<20 收方的集中拆分／全史流出 <2%／一实体轮换多个发送地址各 <2%（entity-file 只抵消内部边，不按实体聚合外发）／先发少数中间仓再二跳分散的多跳分发——本闸均不可见，归 analyze-workflow 覆盖真空声明。
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
| flow | 汇集点 Q1 与 3yMk 过阈值（v2 实测 sink ID 集合零漂移）；分发点 H9 三派发器全部命中，mode 按实测——DWVG/8WwV＝pulse_all（全收方口径有双达标窗；旧备注"任何 14 日窗 <0.2%"仅 fresh 口径成立，v2 订正）、5Gpc＝slow_spray；Q1 spray 保持 pulse；spray 20→28（缝修复预期增量：4 slow→pulse_all＋净新增 6 pulse_all/2 slow）；pulse_all 最大候选 6bh2zL8 入锚 |
| 溯源 | Q1 峰值锚点 direct_upstream 中 ≥9 个 W1 直接上家现形；3yMk 支路停 EwUU8oi 而 W1 支路穿透（path_len ≥2）；敏感性 stable（v2 正向模拟实测值以 fixture 为准，v1 数字作废） |

回测仅 PYTHIA 单案（用户拍板）；flow 参数初值与误报水平缺第二币对照校准——未来首个新案实战时如实标注此局限。

## 6. distribution-scan/v1

本产物只计算冻结 cutoff 的当前 owner 快照。`initial` 绑定上游收据但不绑定 handoff manifest。`final` 绑定 READY `handoff/v3`、身份快照收据、当前 A4 seal、当前 entity freeze revision、三账、initial scan 和上一轮 final scan。

固定阈值如下：分箱倍率为 `sqrt(2)`，范围为私人可入箱供应的 `0.000001%` 至 `100%`，dust 线等于最低分箱边界，经济门为净供应 `2%`，低计数档至少 `5` 个 owner，基础分箱与平移分箱成员 Jaccard 至少 `0.8`，样本线为 `100` 个私人主箱 owner，未识别合约披露线为净供应 `1%`。鼓包检验的族错误率为 `1%`。头部基线为 top-1 `20%`、top-3 `30%`、top-5 `40%`、top-10 `50%`、HHI `0.05` 和相邻质量比 `8`。

鼓包检验的零假设是各档 owner 数服从均值为单调递减拟合值的独立 Poisson 分布。检验只取正偏离，使用单侧尾概率。所有可检档在同一轮按 Holm-Bonferroni 校正。少于 5 个 owner 的档不进入检验。基础分箱与平移半档复算都过统计门、经济门和 Jaccard 门后，簇才成立。多簇分别检验并全量落盘。

```
{
  "schema": "distribution-scan/v1",
  "stage": "initial|final",
  "generated_at_utc": ISO8601,
  "exit_code": 0|2,
  "thresholds": {
    "bin_ratio": "sqrt(2)", "bin_min_private_pct": 0.000001,
    "bin_max_private_pct": 100.0, "dust_private_pct": 0.000001,
    "economic_gate_net_pct": 2.0, "minimum_bin_owner_count": 5,
    "shift_jaccard_min": 0.8, "sample_line": 100,
    "unresolved_contract_disclosure_net_pct": 1.0,
    "poisson_family_alpha": 0.01, "multiple_testing": "Holm-Bonferroni",
    "low_count_rule": "observed_owner_count>=5",
    "head_top_k_net_pct": {"1": 20.0, "3": 30.0, "5": 40.0, "10": 50.0},
    "head_hhi": 0.05, "head_adjacent_mass_ratio": 8.0,
    "explanation_member_coverage_min": 0.8,
    "explanation_residual_cluster_pct_max": 1.0
  },
  "input_binding": {
    "snapshot": {"path", "sha256", "size"},
    "data_map": {"path", "sha256", "size"},
    "supply_truth": {"path", "sha256", "size"},
    "exclusion_sources": [{"path", "sha256", "size"}],
    "exclusion_derivation_sha256": sha256,
    "algorithm": {"name", "files": [{"path", "sha256", "size"}], "sha256"},
    "thresholds_sha256": sha256,
    "recognition_rules": {"version", "sha256"},
    "labels_manifest": {"path", "sha256", "size"}|null,
    "upstream_receipts": [{"path", "sha256", "size"}],
    "handoff_manifest": null|{"path", "sha256", "size", "run_id"},
    "final_bindings": {filename: {"path", "sha256", "size"}},
    "entity_freeze_revision": int, "a4_seal_revision": int
  },
  "partition": {
    "private_main": [{"owner", "raw"}], "private_dust": [{"owner", "raw"}],
    "public_facility": [{"owner", "raw"}],
    "unresolved_contract": [{"owner", "raw"}],
    "burn_sentinel": [{"owner", "raw"}]
  },
  "partition_check": {"closed": true, "snapshot_total_raw": str,
    "bucket_total_raw": str, "owner_count": int,
    "bucket_owner_counts": {bucket: int}, "dust_cutoff_raw": str},
  "verdict": "NORMAL_SHAPE|ABNORMAL_SHAPE|NOT_EVALUABLE",
  "not_evaluable_reason": null|"low_sample|data_broken",
  "errors": [str],
  "denominators": {"total_supply_raw": str, "net_supply_raw": str,
                     "private_boxable_supply_raw": str},
  "bucket_coverage": {bucket: {"raw": str, "net_supply_pct": float}},
  "owner_count_private_main": int,
  "disclosure_required": bool,
  "base_bins": [{"index", "upper_private_pct", "owner_count",
                   "expected_owner_count", "raw_balance"}],
  "shifted_bins": [{"index", "upper_private_pct", "owner_count",
                      "expected_owner_count", "raw_balance"}],
  "concentration": {"top_k_net_pct", "hhi", "top1_to_top2_ratio", "triggered_k"},
  "abnormal_clusters": [{
    "cluster_id": str, "trigger": "bin_count_bump|head_concentration",
    "bin_start": int, "bin_end": int, "shift_bin_start": int,
    "shift_bin_end": int, "shift_jaccard": float, "p_values": [float],
    "owner_count": int, "raw_balance": str, "net_supply_pct": float,
    "members": [{"owner", "raw"}], "metrics": object
  }],
  "small_sample_mode": null|{"complete": true,
    "owner_classifications": [{"owner", "raw", "bucket"}],
    "top_k": {"1": float, "3": float, "5": float, "10": float},
    "hhi": float, "equal_amount_groups": [{"raw_each", "owners", "combined_raw"}],
    "partition_closed": true},
  "round": int, "previous_round": int|null, "previous_round_entry_sha256": sha256|null
}
```

`data_broken` 产物只保留 schema、stage、时间、exit code、阈值、verdict、reason、errors 和空异常簇，脚本返回 2。`low_sample` 必须带完整逐址分类、top-k、HHI、等额组和分区闭合结果，脚本返回 0。validate 会从绑定文件重新派生五桶、重新计算全部统计量并比较语义字段。

## 7. distribution-explanation/v1

每个异常簇必须同时通过位置、成员、数量、证据和传播五项检查。成员覆盖率至少为 `0.8`。未解释余额不得超过该簇余额的 `1%`。证据必须在当前 A4 seal 的封口资产或 claim 引用文件内。传播检查绑定当前 `facts.json` 和 `analysis-state.json` 的哈希。

```
{
  "schema": "distribution-explanation/v1", "generated_at_utc": ISO8601,
  "verdict": "EXPLAINED|UNEXPLAINED",
  "scan": {"path", "sha256"}, "a4_seal": {"path", "sha256"},
  "thresholds": {"member_coverage_min": 0.8,
                   "residual_cluster_pct_max": 1.0},
  "cluster_results": [{"cluster_id", "claim_id",
    "checks": {"position": bool, "members": bool, "quantity": bool,
                "evidence": bool, "propagation": bool},
    "member_coverage": float, "alien_members": [addr],
    "explained_raw": str, "residual_raw": str,
    "residual_cluster_pct": float,
    "verdict": "EXPLAINED|UNEXPLAINED"}],
  "errors": [str]
}
```

## 8. distribution-adjudications/v1

```
{
  "schema": "distribution-adjudications/v1", "case": str,
  "adjudicated_at": ISO8601,
  "source_scan": {"path", "sha256"},
  "adjudications": [{
    "candidate_id": "dist-<cluster_id>",
    "candidate_kind": "distribution_bin_count_bump|distribution_head_concentration",
    "candidate_sha256": sha256,
    "candidate_verdict": "pattern_confirmed|excluded|unresolved",
    "accepted_members": [addr], "excluded_members": [{"addr", "reason"}],
    "linked_entity_id": str|null, "evidence": [str],
    "raw_balance": str, "net_supply_pct": float,
    "_members_total": [addr]
  }]
}
```

validator 对候选文件、schema、ID 集、重复 ID、候选哈希、成员全集、verdict 语义、实体名册和 raw 数值执行八类拒绝。全部 unresolved 候选的余额合计达到净供应 `2%` 时拒绝冻结。

## 9. pattern-resolutions/v1

```
{
  "schema": "pattern-resolutions/v1", "resolved_at_utc": ISO8601,
  "source_scan": {"path", "sha256"},
  "path_a_excluded_reason": str,
  "resolutions": [{
    "cluster_id": str,
    "mechanism_code": "cex_occlusion|dust_poisoning|quota_airdrop|accounting_mechanism|unidentified_facility|other",
    "verdict": "CONFIRMED|REFUTED|UNRESOLVED",
    "affected_members": [addr], "raw_balance": str,
    "evidence_refs": [str]
  }]
}
```

`other` 也必须填写 mechanism_code、affected_members、raw_balance 和 evidence_refs。任一 `UNRESOLVED` 会阻断“异常已解释”的发布结论。核查提取出明确成员名单时，成员必须转入 distribution-adjudications/v1。

## 10. distribution-rounds/v1

```
{
  "schema": "distribution-rounds/v1", "created_at_utc": ISO8601,
  "rounds": [{"round_n": int, "snapshot_sha": sha256,
    "exclusion_derivation_sha": sha256, "entity_freeze_revision": int,
    "a4_seal_sha": sha256, "final_scan_path": str, "final_scan_sha": sha256,
    "explanation_path": str|null, "explanation_sha": sha256|null,
    "verdict": "NORMAL_SHAPE|ABNORMAL_SHAPE|NOT_EVALUABLE",
    "status": "NORMAL|LOW_SAMPLE|EXPLAINED|UNEXPLAINED|REQUIRES_A4_REFLOW|WAIVED",
    "new_clusters": [str], "ts_utc": ISO8601,
    "previous_entry_sha256": sha256|null}],
  "terminal": null|{"round_n": int,
    "status": "NORMAL|LOW_SAMPLE|EXPLAINED|WAIVED",
    "final_scan_path": str,
    "final_chart_path": "charts/final/holder_distribution_current.png"}
}
```

轮号必须从 1 严格递增。每轮绑定上一条完整记录哈希。到达 terminal 后不得追加。终态前不得在 `charts/final/` 物化分布图。final scan 声明非首轮但台账缺失时拒绝继续。

## 11. distribution-exception-receipt/v1

```
{
  "schema": "distribution-exception-receipt/v1",
  "user_decided_at_utc": ISO8601, "round_n": int,
  "unexplained_clusters": [str], "unexplained_raw": str,
  "a4_seal_sha256": sha256, "final_scan_sha256": sha256,
  "rounds_sha256": sha256
}
```

收据只在两轮仍未终态后生效。A5 seal 绑定完整收据。报告必须披露未解释簇和余额。

## 12. 分布形态定标锚点

| 数据 | 结果 |
|---|---|
| QUQ 探索集 | 51,871 个非零地址。终裁库存层当前非零 58 址，合计占固定总供应 27.805299342960172%。最大成员占 27.63881821625497%，top-1 对下一名余额比 65.92115888828673，HHI 为 0.07644066964322206。头部集中度触发器命中。 |
| PYTHIA 探索集 | 37,888 个 owner。46 址各持有 1,000,000 枚，合计占冻结供应 4.608488643331846%。基础分箱命中 33 至 35 档，平移分箱命中 32 至 34 档，成员 Jaccard 为 0.852。 |
| TROLL 保留集 | `soltx` 元数据写明 `launch_covered=false`，本轮不作为完整保留集。 |
| 合成盘 | 覆盖正常长尾、鼓包、等额组、头部集中、粉尘长尾、设施分桶、黑箱披露、经济门边界、99-owner 小样本、分箱平移和多簇。 |

QUQ 与 PYTHIA 只用于算法层探索定标。防伪链测试使用合成 fixture。阈值出身是两案探索定标和合成盘，缺少完整保留集与多案校准。
