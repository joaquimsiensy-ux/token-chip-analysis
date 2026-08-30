# scan-schemas — 机械扫描产物 schema 冻结（v6.20.0）

扫描、溯源和分布形态产物的**唯一权威字段定义**。实现脚本与契约测试对本文件写；改字段先改这里再改代码。
适用脚本：`wave_scan.py`（wave-scan/v5）、`flow_anomaly_scan.py`（flow-anomaly/v3）、
`entity_source_trace.py`（provenance-ledger/v2）、`holder_distribution_scan.py`（distribution-scan/v2）、
`distribution_explanation_check.py`（distribution-explanation/v1）和两类裁决台账。

## 本册路由

- §0 公共纪律；§1 wave-scan；§2 flow-anomaly；§3 裁决台账；§4 provenance-ledger；§5 PYTHIA fixture；§6 至 §11 是分布形态契约；§13 阵营序列 sidecar 与 burn 闭合口径；§14 是 Solana SQD 覆盖、修复代、exact reconcile 与派生边源绑定契约。

## 0. 四条公共纪律

1. **稳定 ID＝内容派生**：候选 ID 由其核心内容（成员集/面额/地址）哈希派生——内容变则 ID 变，旧裁决按 ID 对不上自动失效。
2. **裁决绑定候选内容哈希**：每条裁决记录 `candidate_sha256`＝裁决时该候选完整 JSON 的规范化哈希（`json.dumps(obj, sort_keys=True, ensure_ascii=False)` 的 sha256）。validator 重验：当前报告同 ID 候选哈希不一致＝候选内容已变＝裁决过期，exit 2。
3. **零静默截断**：所有成员/收方/来源数组全量落盘，数组长度必须等于对应 `*_count` 字段（闭合断言）；stdout 只显 top 不代表文件截断。
4. **本文件＝完整字段登记**（v6.8.1，codex 复核 P2 采纳）：脚本实际输出的每个字段都必须在此登记——未登记字段不得输出，登记了的不得静默删除；公共通用字段（`schema/generated_at/params/total_supply_raw/edges/note`）各产物一律在场，下文不再逐一重复。输入边表的唯一性由采集管线（four-check 对账）保证，扫描器不去重。Solana v4 以 `(slot,tx_index)` 标识交易，并对该交易完整边集计算排序后的 `tx_digest`：重复身份且 digest 相同只留一份，digest 不同硬失败。五元组没有交易身份，同字段重复可能是不同真实交易，禁止按五字段去重。

**Solana 输入边现役标准**：正式路径使用 7 元组
`[ts,slot,tx_index,instr_index,from,to,amt]`。SQD tokenBalances 只提供交易级 pre/post
快照，因此共享核产出的边固定 `instr_index=-1`、`edge_semantics="owner-net-greedy"`、
`order_granularity="transaction"`：它证明 owner 级净变化，但贪心配对只是推定关系，
**不证明链上精确 from→to**，也不能恢复交易内指令顺序；该哨兵必须对应 `order_exact=false`。旧 5 元组
`[ts,slot,from,to,amt]` 仅是 `legacy-sol5` 诊断格式，标记 `order_ambiguous/non-formal`，无法补回
交易身份且无迁移路径，正式使用须全量重采。

## 1. wave-scan/v5（wave_scan.py）

与 v1 的语义差异（**不得冒充 v1**，handoff 校验按版本严格匹配）：
扫描对象从"清零层"改为**全体历史峰值 ≥0.02% 地址**（三桶标签）；A 指纹两层（seed_window 触发→expanded_wave 生长）；C 口径改"峰值→30% 峰值耗时 ≤30 日"；D 参数四条合一；成员零截断；负余额升 exit 2；聚类时间轴用抗 dust 的 `first_meaningful_day`。
v3 与 v2 的差异（2026-08-02 codex 复核补闸）：**候选全集逐址落盘**——v2 只落 `scan_universe_count` 一个计数，孤仓不成波次/等额组就从产物消失、发布闸无从对账；v3 新增 `scan_universe` 逐址清单＋`must_adjudicate` 四类机械标记＋`must_adjudicate_count`，`dormant_warehouse_audit.json` 以 `universe_ref{path,sha256}` 绑定本报告，audit_release_gate 做哈希＋集合包含对账。
v4 与 v3 的差异（2026-08-18 SQD v4 消费端分立）：新增 `edge_order_granularity`、
`order_ambiguous`、`non_formal`。正式 SQD transaction-net 边虽为 v4 7 元组，但
`instr_index=-1`，所以 `edge_order_granularity="transaction"`、`order_ambiguous=true`、
`non_formal=false`；未来真实指令级边才可报 `instruction/false/false`。显式
`--legacy-sol5` 必须报 `legacy-slot/true/true`，handoff、裁决和发布链一律拒绝它。
正式 `--edges-sol` 不以 7 列外形判身份：必须同时提供 `--sol-cache-meta` 与 `--mint`，共享
校验器核对 v4 schema、mint、ACTIVE collector、逻辑摘要及行数；wave/flow/entity 三入口同闸，
entity 的 meta/mint 还要进入 input binding 并由 freeze 原命令重放。

v4→v5 的唯一变化是新增必填对象 `edge_source_binding{cache_kind,gid|null,soltx_edges_sha256,soltx_meta_sha256,edge_logical_sha256}`：Solana 必填且与 `solana-reconcile/v4` 全等，EVM 必须省略。其余 v4 字段和算法语义全部保留；正式链遇旧 v4 产物 fail-closed，并提示用当前边源重跑。

```
{
  "schema": "wave-scan/v5",
  "generated_at": ISO8601,
  "params": {…全部命令行参数…},
  "total_supply_raw": str,
  "edges": int,
  "edge_order_granularity": "transaction|instruction|log|source-defined|legacy-slot",
  "order_ambiguous": bool,
  "non_formal": bool,
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

## 2. flow-anomaly/v3（flow_anomaly_scan.py）

汇集点＋分发点两类候选。v1→v2（2026-08-02 用户拍板补两缝＋codex 交叉复核重构）：
缝1＝慢速线 500（H9 单案 6,503 收方校准）过宽，降 100；缝2＝pulse 只数 fresh 新收方，
"向已建仓老地址补货"完全隐形，新增 pulse_all 广义口径；spray 改**多命中结构**（pulse ⊂
pulse_all，单一 mode＋优先级只是选标签会丢证据）；出边零值过滤（amt>0，零值不许凑收方/
来源数）；金额阈值整数运算（meow 案纪律）；窗口浓度两键识别伪分发。参数出身＝PYTHIA
单案回测＋用户设定高召回初值，非多案校准。

v2→v3 的唯一变化是新增必填对象 `edge_source_binding{cache_kind,gid|null,soltx_edges_sha256,soltx_meta_sha256,edge_logical_sha256}`：Solana 必填且与 `solana-reconcile/v4` 全等，EVM 必须省略。其余 v2 字段和算法语义全部保留；正式链遇旧 v2 产物 fail-closed，并提示用当前边源重跑。

```
{
  "schema": "flow-anomaly/v3",
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

**validator 拒绝规则（八类契约测试全覆盖，v6.8.1 加固）**：①缺文件；②源报告候选 ID 集 ≠ 裁决 ID 集（少裁/多裁/未知 ID），源报告 schema 错版/重复候选 ID 同拒；③重复裁决 ID；④candidate_sha256 与当前源报告不符（候选内容已变）；⑤accepted+excluded ∪ ≠ 候选成员全集（部分成员未裁；eqg 候选按收方集）；⑥tier_impact 三字段任一与机器重算不符（伪造）；
  ⑦verdict 语义交叉约束——pattern_confirmed 必须 accepted 非空＋linked_entity_id＋evidence 非空，excluded/unresolved 必须 accepted 为空，excluded_members 逐条必须有非空 reason，candidate_kind 必须与机器一致，adjudicated_at 必须已填；⑧实体名册绑定（`validate --entity-file`，freeze 强制传入）——linked_entity_id 必须存在于名册、accepted 成员必须已落入该实体名册，存在 pattern_confirmed 而未传名册即拒。
  unresolved 且机器判 could_change_tiering=true → freeze exit 2。

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
独立顺序敏感性阻断。Solana 现役 7 元组标准为
`[ts,slot,tx_index,instr_index,from,to,amt]`；其中 SQD transaction-net 边固定
`instr_index=-1`，只能确定交易粒度顺序，必须置 `order_exact=false`。只有输入给出真实非负
instruction index 时，才允许声明可恢复交易内精确执行顺序；旧 5 元组仍是非正式诊断输入。

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
    "algorithm_params": {"depth_limit", "facility_min_degree", "node_budget", "edge_budget",
                         "flip_adjudications": {"path","bytes","sha256"}|null}
                        # flip_adjudications＝翻转裁决收据文件引用（§4a，批 D F-06）；
                        # 6.39.4 旧式 acknowledged_flips 字符串数组已废除，freeze 见之即拒
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

`source.argument` 按 `kind` 分家：sol/duckdb＝文件；evm_v2＝目录，即 `run_*/logs.parquet` 与 `run_*/blocks.parquet` 的父目录；`source.files` 逐件绑定实际输入文件（`scripts/report/handoff_manifest.py:701-737,1221-1249`）。

**硬规则**（复核翻案教训，全部进契约测试）：
- 支路级停止：设施来的支路停（记 BOUNDARY/facility 或 UNRESOLVED/facility_candidate），同一钱包的其他支路必须继续穿透（3yMk 教训：EwUU8oi 来的 8.77% 停、10 条 W1 支路继续）——BFS 终点判定逐节点独立，天然成立。
- "DEX 池流出"只能记 `dex_pool` 边界，**不得写成"swap 买入"**（现有数据无对价腿）。
- 设施认定：标签库确证＝`facility_confirmed`；启发式命中（对手方≥1000 且双向）只记 `facility_candidate` 归 UNRESOLVED。
- 实体内部先收缩单一超级账户，内部互转不记账不重复计源；`--entity-file` 强制 {str: 非空 str 数组}、同址跨实体即拒。
- 深度上限（默认 10 跳）记 `depth_limit`、BFS 节点预算超限记 `budget_truncated`、账户被取用时库存不足记 `data_gap`（短缺显式入账）——全部 UNRESOLVED **不静默丢弃**；子图边数超 `--edge-budget` 直接 exit 2（不静默采样）。
- **双维敏感性阻断**：pro_rata 主法出数，fifo/lifo 上下界同跑；任一 stock>0 锚点的第一大终点条目在三策略间不一致，或 `order_ambiguous` >0.5% 锚点库存 → 汇总 false、脚本 exit 2。freeze 不读取 stable 自报作裁决，而从 `policy_details` 重算，并核验 `input_binding` 后以当前代码和当前原始边真实重放；语义摘要不一致即拒。
- **freeze 可复现绑定**：source files 必须同时出现在已 verify 的 manifest artifacts 与 data_map；标签、实体文件、完整源边、total supply、manifest run/scope（cutoff/block/denominators）、算法脚本与参数逐项哈希绑定。任一变化都必须重跑 provenance 并追加 freeze revision；`check-unseal` 复核所有当前绑定文件哈希。

### 4a. flip-adjudications/v1（翻转裁决收据，批 D F-06）

真实三策略主导翻转（多来源结构）的**唯一**人工放行通道。6.39.4 的 `--acknowledge-flip ENTITY:ANCHOR:REASON` 字符串格式**已废除**——任意 10 字符理由即可解除发布阻断、且无任何消费者核对披露，是被审查判死的口子。现行 `--acknowledge-flip <收据文件路径>`。

```
{
  "schema": "flip-adjudications/v1",
  "approved_by": str,                       # 裁决主体（非空）
  "user_decided_at_utc": ISO8601Z,          # 用户裁决时间（UTC，必须 Z 结尾）
  "entity_file": {"path","size","sha256"},  # 名册绑定：收据同目录内相对路径三验，
                                            #   且 sha 必须＝本次运行 --entity-file 内容
  "evidence_refs": [{"path","size","sha256"}…],  # ≥1 份独立人工核对证据（收据同目录内，
                                            #   拒绝绝对路径/越界/符号链接；不得是名册自身；
                                            #   实物 ≥16 字节——形式下限，内容真伪机器验不了）
  "adjudications": [{
    "entity_id": str, "anchor": "peak|current",
    "reason": str,                          # ≥10 字符
    "flip_fingerprint": sha256,             # ＝该锚点三策略 policy_details 规范化子集 sha
                                            #   （canonical JSON of {"policy_details": {pro_rata,fifo,lifo}}）
    "disclosure": {
      "top_by_policy": {"pro_rata": {"terminal": [kind,sub,via], "share_pct": "12.34"},
                        "fifo": {…}, "lifo": {…}},   # 与明细重算值逐项相等（防收据写假数）
      "report_locations": [str…]            # 报告可核位置（非空）
    }
  }…]
}
```

消费面三处同源（实现共享在 `handoff_manifest.py`，不手抄）；evm_v2 重放前另有 argument 字符闸＋目录集合闸，当前命中集合必须与 `source.files` 精确相等，任一差集非空即在临时文件与子进程之前拒绝（`scripts/report/handoff_manifest.py:701-737,1221-1259`）：
- **trace**（producer）：重算当前运行每个真实翻转锚点的指纹与三策略 top/份额，与收据行逐项相等才 `publishable`；收据行指向非真实翻转锚点＝不许预防性豁免，exit 2。**底层数据一变 → 明细变 → 指纹失配 → 收据自动失效，必须重裁**。
- **freeze 前置 3**（`recompute_provenance_sensitivity`）：只认 `input_binding.algorithm_params.flip_adjudications` 绑定的收据文件（三验＋指纹重算），**不再信 ledger 内嵌自报的 `acknowledged_flips`**；重放参数装配同收据还原。
- **A5 seal**（new-analysis）：披露核对**锚定 report_locations**（消化轮 1，F-D1）——位置串必须命中报告某一 Markdown 标题行，该标题切片内须同时含三策略名（**中英文别名族**任一即可：`pro_rata`｜按比例、`fifo`｜先进先出、`lifo`｜后进先出——中文报告不必塞英文标识符，N-D1）、每策略 top 终点标识串与份额数字（同段并列披露，全文他处偶然同串不作数）；收据实物按 ledger `input_binding` 绑定的 path＋sha 定位（与 freeze 同一份，F-D7）；同时校验 `provenance_ledger.json` 哈希＝`entity_freeze` 记录的 `provenance_ledger_sha256`（封死**单边改动**：改/删 ledger 而 freeze 记录在场必拒；`entity_freeze.json` 自身无上位 sha 锚，"连 freeze 一起改写"属 §13 批 C 终验定性的自洽小件残余边界——完整 new-analysis 案的双删由 final scan 的 `final_bindings.entity_freeze` 绑定拦截）。

**存量迁移声明**：6.39.4 后用过旧式 `--acknowledge-flip` 字符串确认的案子（已知：MOG），其 ledger `algorithm_params.acknowledged_flips` 为旧格式——重 freeze 时前置 3 与重放装配均按"旧确认不再受理"拒绝，**必须造 flip-adjudications/v1 收据后重跑 trace**；已冻结终态不受追溯影响。

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

## 6. distribution-scan/v2

本产物只计算冻结 cutoff 的当前 owner 快照。owner 快照必须对**铸造总量 `mint_total`（闭合锚点）逐 wei 精确闭合**（缺口和超发同拦，零容差，与供给真值那把 `--tolerance-bps` 各是各的旋钮）。

闭合分母是 `mint_total` 不是 `onchain_total_supply`／`total_supply_raw`：replay 引擎对 sink 是记账不抹除，`sum(快照含 dead/zero) == mint_total` 恒成立——form2（转 dead 不减供给，`onchain==mint`）与 form1（真 `_burn`，`onchain==mint−burn`）都如此（APU／IQ／KOGE 真案逐 wei 实测）。若对 `onchain` 闭合，整类 form1 销毁币会被误杀。分母取值分链：EVM 取 `replay_stats.json` 的 `mint_total`（replay 产物，收据里有），Solana 取 `onchain_total_supply`（scanner `require_snapshot_closed` 已保证 `sum==supply` 精确，不套 EVM 的 replay mint 语义）。

`total_supply_raw`／`frozen_total_supply_raw` 是**调用者可注入的影子键**（真实生产者 `supply_truth_gate` 只写 `onchain_total_supply`／`replay_net`／`mint_total`／`burn_total`）——闭合分母绝不取影子键，`net`（分布百分比分母）也优先取真实键 `replay_net`／`onchain_total_supply`。EVM formal 的 `onchain_total_supply` 来自已验证 `evm-observation-bundle/v1` 的冻结块 `total_supply_raw` 并由 `supply-truth-receipt/v4` 绑定，不再是消费时现场 RPC 自报；`net` 仍只用于分布百分比。冻结点后的链上销毁可令观测时点 `onchain_total_supply` 略低于冻结点 `replay_net`：扫描器仅在同一收据为 PASS/exit 0、`diff == replay_net-onchain_total_supply` 逐 raw 相等且 `diff*10000 <= tolerance_bps*onchain_total_supply` 时接受，并在 `denominators.supply_drift_raw` 留痕；任一字段缺失、失配或超容差仍 fail-closed。该交叉检查全程用整数运算，不改变 `net` 的分布百分比分母身份，也不放宽 Solana owner 快照对 `onchain` 的精确闭合。

**闭合锚点的取值顺序（已绑定已验证的链路优先）**：① `supply_truth` 收据 `inputs.replay_stats` **绑定**的那份实物（已过 receipt 三验＋案根遏制，取值后再交叉验 `mint−burn == replay_net`）；② 收据的 `mint_total` 字段；③ `onchain_total_supply`。**案根裸 `replay_stats.json` 永远不是锚点来源**——真案 9/10 把它放 `data/`／`out/`／`replay/` 子目录并由收据绑定，把案根硬编码文件名排在第一，既让"抹平快照＋伪造一份未绑定案根件"直接过闸，又让"案根留一份陈旧件"把合法案误杀。合法但未绑定的案根同名件**忽略**（未绑定的文件不是证据，不该被采用，也不该有一票否决权）；它若**在场却非法**（符号链接／非普通文件）则 fail-closed 拒，与上面"在场非法不得静默漂白"同一把尺子。

产物里 `denominators.mint_total_raw`＝**铸造总量 `mint_total`（含已销毁）**，不是链上流通量；真 `_burn` 案两者可差三成以上（IQ 差 34.9%）。引用该字段描述"总量"时必须按此口径，链上流通量看 `net_supply_raw`。（批 D schema 升 v2 落地：旧键名 `total_supply_raw` 语义误导已废除；6.39.5 及以前的存量 `distribution_scan.json` 是 v1 产物，重验必拒，须用当前扫描器重跑 initial/final——这与"扫描器算法哈希绑定、改代码即重跑"的既有迁移语义同款。）

`initial` 记录上游收据但不绑定 handoff manifest。上游收据是 **optional 的记录性收据**：案根没有那份文件就不记（split-run 下 −1 出 initial scan 时，−2 还没把 preflight 副本拷进案根），**在场即三验**——凡是记进 `upstream_receipts` 的条目，validate 都要核实文件存在且 sha256／size 与记录一致。校验方向只有"记录项 → 磁盘"这一条，反过来要求"磁盘上有的都得记"会把 6.39.5 修掉的三闸死环修回来。文件在场却非法（符号链接、指到案外、不是普通文件）时生产侧直接 exit 2，不做静默跳过。

分布扫描吃的那份 owner 快照，必须就是四查真正核过的那一份：EVM 比对四查 `balance` 收据的 `inputs.balances.sha256`，Solana 比对 observation bundle 的 `holder_outputs.owners.sha256`，**只比 sha256 不比 path**（两边路径形态本来就不同）。**initial 扫描与进报告的终态 final 扫描（`distribution_rounds.json` 的 `terminal.final_scan_path`）两份都要落在同一个四查 sha 上**——只绑 initial 挡不住 final 轮换一份同值换仓快照产终态判定（F-B1）。该交叉检查由 `audit_release_gate.py --profile new-analysis` 执行，**只放发布闸、不放进 validate**（终态 scan 是本轮新产，不涉及存量案追溯）。

动态 Solana 的分布扫描吃 observation bundle 的观察 owners；三账 B-7、series cutoff、accounting 等冻结账消费者则通过同一中央选择器投影，吃 exact 收据 `inputs.holders_owners` 实物＋冻结块。

**两侧绑定强度已对齐（批 D B-1 落地）**：EVM 的 `inputs.balances` 由 `receipt_validate.validate_receipt` 拿案内实物文件做 path/size/sha 三验；Solana 的 `holder_outputs.accounts/owners` 自批 D 起由 `validate_observation_bundle`（bundle_path 在场的消费侧）做同款文件级三验（查找目录＝收据 inputs 实物所在 work_dir → bundle 同目录 → 同目录 data/），缺件/换包/符号链接均拒。

`final` 绑定 READY `handoff/v3`、身份快照收据、当前 A4 seal、当前 entity freeze revision、三账、initial scan 和上一轮 final scan。

固定阈值如下：分箱倍率为 `sqrt(2)`，范围为私人可入箱供应的 `0.000001%` 至 `100%`，dust 线等于最低分箱边界，经济门为净供应 `2%`，低计数档至少 `5` 个 owner，基础分箱与平移分箱成员 Jaccard 至少 `0.8`，样本线为 `100` 个私人主箱 owner，未识别合约披露线为净供应 `1%`。鼓包检验的族错误率为 `1%`。头部基线为 top-1 `20%`、top-3 `30%`、top-5 `40%`、top-10 `50%`、HHI `0.05` 和相邻质量比 `8`。

鼓包检验的零假设是各档 owner 数服从均值为单调递减拟合值的独立 Poisson 分布。检验只取正偏离，使用单侧尾概率。所有可检档在同一轮按 Holm-Bonferroni 校正。少于 5 个 owner 的档不进入检验。基础分箱与平移半档复算都过统计门、经济门和 Jaccard 门后，簇才成立。多簇分别检验并全量落盘。

```
{
  "schema": "distribution-scan/v2",
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
    "upstream_receipts": [{"path", "sha256", "size"}],   // optional 记录性收据，在场即三验
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
  "denominators": {"mint_total_raw": str,     // ＝mint_total 铸造总量（含已销毁），非链上流通量
                     "net_supply_raw": str,     // ＝replay_net；仍是分布百分比分母
                     "supply_drift_raw": str,   // optional；仅 net>onchain 且收据容差内时＝net-onchain
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

`data_broken` 产物只保留 schema、stage、时间、exit code、阈值、verdict、reason、errors 和空异常簇，脚本返回 2。`low_sample` 必须带完整逐址分类、top-k、HHI、等额组和分区闭合结果，脚本返回 0。validate 会从绑定文件重新派生五桶、重新计算全部统计量并比较语义字段，并对 `upstream_receipts` 里**已记录**的每一项做存在＋sha256＋size 三验（记录性收据，缺席合法、在场即验）；`upstream_receipts` 本身不进语义逐位比较（6.39.5 三闸死环修复）。

**重验须重跑当前版本生产者（F-B5，修正旧口径）**：validate 内部经 `build_scan` 重算，闭合闸也在这条追溯路径上，且 `input_binding.algorithm.sha256` 绑脚本自身哈希——脚本改过一个字节，旧产物就对不上。所以存量案在 A5 重验前无论如何都要重跑对应生产者获取当前回执（与仓内既有的"存量案例须重跑对应生产者"一致），这**不是死锁**。重跑后仍不对铸造总量精确闭合的存量案按 `data_broken` 拒收，这是**刻意收紧不是回归**（基线时代只拦超发，残缺快照能过）。第二层交叉检查禁入 validate 只是不让"快照↔四查绑定"这一条追溯卡死，闭合闸的追溯收紧另算。

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

## 13. camp-series-provenance/v1（阵营序列 producer sidecar，camp_series_provenance.py）

**要解决的事**（F-04，2026-08-13）：图 1 的阵营序列此前是编报告的人自己填进 state 的数字，编译器不问出处——伪造序列能一路走到封章。本节把序列钉回重放产物：谁产的、用什么输入产的、产物本体的指纹是什么，全部落在序列文件旁边的 sidecar 里。

**producer 侧**：四族重放入口（`evm/replay_pass2.py`、`evm/replay_duck.py`、`solana/replay_edges.py evolution`、`solana/build_evolution.py`）写序列文件时**同步**写 `<序列名去 .json>.provenance.json`（如 `camp_series.json` → `camp_series.provenance.json`），共享实现 `scripts/lib/camp_series_provenance.py`（写法＝tmp＋os.replace 原子替换）。字段：

| 字段 | 含义 |
|---|---|
| `schema` | 恒 `camp-series-provenance/v1` |
| `producer` | 产者脚本仓库相对路径（如 `scripts/evm/replay_duck.py`） |
| `series_file` / `series_sha256` / `series_size` | 序列文件名与本体指纹（输出绑定） |
| `series_format` | `evm-dict`（EVM 两引擎）/ `sol-rows`（replay_edges）/ `sol-anchor-rows`（build_evolution，小样本辅助）/ `evm-entity-dict`（entity_series，图 2 原料） |
| `denominator` | `current_net_supply` / `mint_total_legacy` / `net_supply` / `config_total_supply`——只作口径声明，consumer 重算分母不信此处自报数字 |
| `camps_spec` | 阵营定义文件 `{path(basename), sha256, size}` |
| `final_balances` | 与本序列**同一次重放**落盘的终态余额快照（EVM＝`balances_final.json`；sol-rows＝`effective_balances.json`）——末点对账的快照锚 |
| `inputs` | `{语义名: {path, sha256, size}}`：EVM 必含 `replay_stats`；sol-rows 必含 `reconcile_receipt`（正式链）；Solana 收据 v4 把 v3 全字段装入 formal envelope（其中三项供应量 raw 值收紧为 JSON int），并强制 `target/mode/verdict/exit_code/producer/inputs/edge_source_binding`；同次重放实算的逻辑边摘要/行数继续对锚 cache meta，边实物的 size/sha256 则由 `inputs.soltx_edges` 与 `edge_source_binding` 绑定 |

**consumer 侧**（`state_from_facts.py --series-source <序列文件>`，正式编译必给）：①序列 sha 对 sidecar（落盘后改一字节即拒）；②camps_spec/final_balances/inputs 逐项三验（存在＋sha＋size，basename 只在序列目录与案根两层内找，符号链接拒）；③登记面命中——`evm-dict` 要求案内 `supply_truth.json` 在场且 sidecar 的 replay_stats sha 命中其绑定集合；`sol-rows` 只认 `solana-reconcile/v4`，由编译案 target 和发布 target 两处分别传入大小写敏感且满足 32~44 位 base58 形态的 mint/chain/cutoff，验收据 formal envelope 的 target/mode/verdict/exit_code、producer、base/repaired 对应的全部 inputs 实物、`edge_source_binding` 与当前 resolver 全等、`edge_extrema.slot ⊆ collection_window ≤ snapshot/target cutoff`，并将 `edge_digest/edge_count` 对锚 soltx meta；同时要求 `gate_pass is true`、`negative_balance_count` 与 `snapshot_mismatch_count` 均为精确整数 0、`net_supply_raw` 为在场的非负整数，且终态快照合计必须等于 `net_supply_raw`。v2/v3 均归 legacy，明确拒绝并要求重跑 `replay_edges reconcile`；④Solana 边完整性只声称到实际强度：编译点要求 resolver 选中的边文件实物在场且非空，并与 `inputs.soltx_edges.size` 对锚；发布点在此基础上再重算物理 sha256 对锚 `inputs.soltx_edges.sha256`。消费侧**不重放边内容**，逻辑内容完整性仍由 producer 同次重放得到的 digest/count 与 meta 拒绝记账、供给真值链和快照闭合共同保证；⑤**末点对账**＝从 camps spec＋final_balances 机械重算各 spec 阵营终点份额，与序列末点逐桶比对（容差 0.05pp，formal 写死），并按 `series_format` 分家：`evm-dict` 的「锁仓/销毁」是普通堆叠 spec 桶，计入 `Σspec` 与散户残差，`burn_cum_pct` 只作堆叠外披露且 legacy 序列不得含它；`sol-rows` 的「锁仓/销毁」是净供应分母外披露桶，不计入 `Σspec` 或散户残差，另按 burned/net_supply 重算比对；其余 spec 外动态桶（散户残差等）仍用恒等式 `100−Σspec` 双向比对（生产依据：`scripts/evm/replay_pass2.py:84-116,139-145`；`scripts/solana/replay_edges.py:648-657`）；⑥state 的 `camp_share_series` 由编译器从原生文件转换生成（sol-rows 的 `其他散户`/`首30分钟狙击者` 两个动态桶并入 `散户`，狙击窗明细在 `sniper_set.json` 不丢），source 手填了该字段就必须与转换结果逐点相等。`edge_extrema.ts` 仅是人读时间参考的记录字段；机器身份、窗口和顺序判定只认 slot，ts 不参与机器判定。`sol-anchor-rows` 不入正式编译链（锚点法小样本辅助、无对账链锚，正式序列走 replay_edges/replay_duck）。旧案无 sidecar → 不经 compile_state 的重绘路径照旧，无追溯卡死。

**camp_share_series 数值面（compile_state 无条件校验，与 --series-source 无关）**：桶名白名单＝`standard_charts.CAMP_ORDER_MODERN`（∪ `burn_cum_pct` 豁免键；legacy 名与实体级自造桶名新报告一律拒）；全值有限；按 `series_format` 派生的实际堆叠桶值域 [0,100]，堆叠外披露桶只验非负有限；日期轴统一 UTC 解析后严格递增无重复（naive 视为 UTC，带时区先换算再比）。

**formal 必经与探索豁免（F-C1 消化轮，轮 2 终关）**：`state_from_facts.py` 默认（formal）编译 **--series-source 必填**——缺席 BLOCK exit 2，来源绑定不挂可选参数；显式 `--exploration` 才可不带，产物 provenance 落 `series_binding="exploration-unbound"` 非正式标记。formal 绑定产物落 `series_binding="producer-sidecar"`＋`camp_series_sidecar` 块（producer/series_file/series_sha256/**series_format**）；`source.provenance` 不得预置这两个键（只能编译器按验证结果生成）。下游 `audit_release_gate`（new-analysis）复验：state 含 camp_share_series 就必须是 producer-sidecar 绑定、绑定的序列实物（案根与 data/ 两层）sha 一致，**且发布闸用编译器同一转换器（series_to_state_form）把序列实物重转换一遍与 state 的 camp_share_series 逐点比对**——sha 相符只证明文件没被改，重转换比对才证明 state 里的序列真是它转换来的（轮 2 终关：手改标记自补绑定块、formal 编译后篡改 series 两类攻击同死）；**发布期还复算整条来源链**（轮 3 N-C4：复用编译期同三件纯函数——sidecar 实物强制在场＋输出 sha＋输入三验 → supply_truth/target/preflight 登记面锚 → camps spec 末点对账，且绑定块 producer 须与磁盘 sidecar 实物一致）——"自造原生格式文件＋state 用它的转换结果＋绑定块自填"的同步一致造假在此拦死，剩余残余=控制案目录者手写一组互相自洽的案内小件（终验实测约 1.5KB、无需运行 producer 即可自洽——validator 是一致性校验器不是真实性证明器，F-12 已接受边界同族，此链上不再有可机器闭合的下一层）。绑定路径的闭合按 sidecar `series_format` 精确堆叠闭合：`evm-dict` 的「锁仓/销毁」参与堆叠且只豁免 `burn_cum_pct`（legacy 序列不得含该键），`sol-rows` 的「锁仓/销毁」与 `burn_cum_pct` 均在堆叠外，`sol-anchor-rows` 无豁免；`denominator` 只校验登记值合法，不再推导堆叠语义。无 `series_format` 的手填路径才保留 dual/net/total 历史双式行为（生产依据：`scripts/evm/replay_pass2.py:84-116,139-145`；`scripts/solana/replay_edges.py:648-657`）。登记面命中是结构化校验：EVM supply_truth.json 须过 schema/verdict/exit_code 与 target/preflight 锚；Solana reconcile v4 则由编译与发布两处各自传入案 target，逐项验证 formal envelope 的 target/mode/verdict/exit_code、大小写敏感 mint、窗口、producer、base/repaired 条件 inputs、`edge_source_binding` 与当前 resolver 全等及边摘要对锚——"含某个 sha 字符串的任意 JSON"不算登记面；v2/v3 legacy 收据一律拒收并要求重跑。figure2 对账收据的 series 与 facts 两个输入实物**无条件**三段验（缺席/符号链接/sha 不符均拒，N-C1：不跑 check 手写收据不再可行）。

**存量迁移（F-C2 定口径，2026-08-13 全库普查 34 个含 series 的 state）**：数值面白名单对存量案是**硬迁移**——"旧案无追溯卡死"只对 sidecar 链成立（不经 compile_state 的 fig1 旧案重绘可使用 CAMP_ORDER legacy 键，但 fig1 入口已由 `select_fig1_series()` 白名单硬拒覆盖，不再允许白名单外键静默漏图），任何存量案**重编译 state 即撞新闸**。三类处置：①旧标签体系/自造桶名（狙击集团、大庄Gate、W系做市体系一类，数值面本身干净）＝口径不兼容——不重编译不受影响；重编译须先按**案内证据**把桶归入 `CAMP_ORDER_MODERN` 现代名，**映射是分析判断不是机械替换**（同名"狙击集团"在不同案里可能是散户层也可能是庄，禁全局映射表）；②旧 schema 形态（camp_share_series 非 {dates,series}，21 例）＝本批之前 compile_state 的结构检查就拒，非本批引入，不适用新口径；③真数据问题（日期轴重复、单点闭合超差）＝刻意收紧，重编译须先修数据或用当前版 producer 重出序列（F-B5 模式）。Solana 案重编译还要求 `source.json.token.data_cutoff_slot` 必填：它是本案采集上界 slot，必须与 reconcile 收据 `collection_window.to_slot` 和 snapshot cutoff 同源；存量案从案内采集清单的冻结/采集上界字段或 `holders_snapshot_meta.target.as_of_block` 查得，二者不一致时先停止并修复采集链，不得任选一个补填。

**burn 口径定案（rg 全库落锤，防 100% 闭合闸误杀 burn 案）**：堆叠语义以 producer 的 `series_format` 为唯一分家键，不按分母名称猜测。`evm-dict` 中「锁仓/销毁」是普通堆叠桶，参与同点 100% 闭合和散户残差；现代净供应输出另带 `burn_cum_pct` 作为堆叠外披露，legacy 序列不得含该键。`sol-rows` 中「锁仓/销毁」是 minted−burned 净供应分母外披露桶，不参与堆叠；`sol-anchor-rows` 中它写入 camp_raw、参与 total_supply 下的 100% 闭合，且 `burn_cum_pct` 出现即拒。formal 只验该 format 实际堆叠键之和≈100；只有无 `series_format` 的手填路径保留 dual 双式。堆叠外披露桶单独验非负有限、不设 100 上界；全桶全零点豁免。轴/元数据键（`dates`/`ts`/`_meta`/`_supply_raw`）不是桶，转换层剔除或转为 dates（生产依据：`scripts/evm/replay_pass2.py:84-116,139-145`；`scripts/solana/replay_edges.py:648-657`）。

## 14. Solana SQD 覆盖、修复代与第五查契约（批 1 冻结）

本节逐字段登记 `maintenance/repair-20260823-sqd-gap/contracts_draft/*.json` 的 `batch1-frozen` 契约。实现不得从本节猜默认值；缺字段、条件字段置 `null`、文件引用不在案根、哈希或当前指针不一致均 fail-closed。所有落盘 JSON 禁浮点，整数（含金额）使用 JSON int。

### 14.1 `sqd-solana-coverage/v1`

- 生产者：`sqd_coverage_probe.py`（计划目标脚本）
- 消费者：solana_exact_validate.py；replay_edges.py reconcile；coverage resolver
- 草案来源：`sqd-solana-coverage_v1.json`（PLAN.md §4.2.1）

| 字段 | 类型 | 必填 | 说明与约束 |
|---|---|---|---|
| `schema` | string | 是 | 协议名；sqd-solana-coverage/v1 |
| `version` | integer | 是 | 协议版本；类型由 schema/version 简写推断 |
| `chain` | string | 是 |  |
| `mint` | string | 是 |  |
| `probe_id` | string (sha256 hex prefix) | 是 | 去 probe_id 后规范化 coverage_map 的 sha256 前16位 |
| `producer.path` | string | 是 |  |
| `producer.sha256` | string (sha256 hex) | 是 |  |
| `sqd.endpoint_fingerprint` | string | 是 |  |
| `sqd.dataset` | string | 是 | solana-mainnet |
| `sqd.metadata_normalized` | object | 是 | 含稳定身份 dataset_id/start_block/real_time，也含 finalized_head/number/hash/height 等动态 head 观测；共享地图复用时按稳定/动态/未知三类校验：稳定字段全等，动态字段走单调与历史锚，未知字段 fail-closed |
| `sqd.metadata_sha256` | string (sha256 hex) | 是 |  |
| `sqd.finalized_head_at_scan` | integer | 是 | 共享地图复用必检：当前 finalized head 不得小于此值，地图区间不得超过此值 |
| `sqd.query_body_sha256` | string (sha256 hex) | 是 | 共享地图复用必检：必须等于当前标准 SQD counts 查询模板哈希 |
| `scan_ranges` | array[object] | 是 | 元素 from_slot,to_slot,mode；mode=full/map-reuse/recheck；并集覆盖案区间 |
| `sample_ranges` | array[object] | 否 | 不计入覆盖并集 |
| `era_params.window` | integer | 是 | 1000000 |
| `era_params.min_headers` | integer | 是 | 10000 |
| `era_params.min_ratio_num` | integer | 是 | 99 |
| `era_params.min_ratio_den` | integer | 是 | 100 |
| `slot_counts.path` | string | 是 | slot_counts.bin.gz |
| `slot_counts.size` | integer | 是 |  |
| `slot_counts.sha256` | string (sha256 hex) | 是 |  |
| `slot_counts.from_slot` | integer | 是 |  |
| `slot_counts.to_slot` | integer | 是 |  |
| `slot_counts.encoding` | string | 是 | u8:0=UNSCANNED,1=NO_HEADER,2=HEADER_ZERO_NONCE,n>=3→nonce_count=n-2，255饱和 |
| `skipped_confirmation` | object\|null | 是 |  |
| `skipped_confirmation.method` | string | 是 | getBlocks |
| `skipped_confirmation.commitment` | string | 是 | finalized |
| `skipped_confirmation.reference_head_at_check` | integer | 是 |  |
| `skipped_confirmation.endpoint_fingerprint` | string | 是 |  |
| `skipped_confirmation.blocks_bitmap` | object | 是 | path,size,sha256,from_slot,to_slot,encoding |
| `skipped_confirmation.ranges` | array[object] | 是 | from,to,response_sha256,count,response_ok,array_monotonic_unique,array_in_range |
| `shared_map` | object\|null | 是 | asset_path,version,sha256,supersedes,generated_at,reused_ranges,unverified_ranges,recheck_stats,canary{slots[64],counts_sha256,verified_at} |
| `ledger` | object | 是 | path,size,sha256,requests,success_ranges_sha256 |
| `summary` | object | 是 | 饱和计数 |
| `verdict` | string | 是 | NO_KNOWN_NONCE_OMISSION_DETECTED/DEFECTS_CONFIRMED/INCONCLUSIVE；须重算 |
| `scan_ranges[].from_slot` | integer | 是 |  |
| `scan_ranges[].to_slot` | integer | 是 |  |
| `scan_ranges[].mode` | string | 是 | full/map-reuse/recheck |
| `skipped_confirmation.blocks_bitmap.path` | string | 是 |  |
| `skipped_confirmation.blocks_bitmap.size` | integer | 是 |  |
| `skipped_confirmation.blocks_bitmap.sha256` | string (sha256 hex) | 是 |  |
| `skipped_confirmation.blocks_bitmap.from_slot` | integer | 是 |  |
| `skipped_confirmation.blocks_bitmap.to_slot` | integer | 是 |  |
| `skipped_confirmation.blocks_bitmap.encoding` | string | 是 | one-bit per slot；1=getBlocks 列出该 slot |
| `skipped_confirmation.ranges[].from` | integer | 是 |  |
| `skipped_confirmation.ranges[].to` | integer | 是 |  |
| `skipped_confirmation.ranges[].response_sha256` | string (sha256 hex) | 是 |  |
| `skipped_confirmation.ranges[].count` | integer | 是 |  |
| `skipped_confirmation.ranges[].response_ok` | boolean | 是 |  |
| `skipped_confirmation.ranges[].array_monotonic_unique` | boolean | 是 |  |
| `skipped_confirmation.ranges[].array_in_range` | boolean | 是 |  |
| `shared_map.asset_path` | string | 是 |  |
| `shared_map.version` | string | 是 |  |
| `shared_map.sha256` | string (sha256 hex) | 是 |  |
| `shared_map.supersedes` | string\|null | 是 |  |
| `shared_map.generated_at` | string | 是 |  |
| `shared_map.reused_ranges` | array[object] | 是 | 本案实际复用的连续子区间；不含未验证段及案区间外 slot |
| `shared_map.unverified_ranges` | array[object] | 是 | 首轮请求失败且末尾统一重试仍失败的原始 recheck 区间；元素为 from_slot,to_slot |
| `shared_map.recheck_stats` | object | 是 | `verified`/`unverified`/`retried` 均按 recheck 连续请求区间计数；retried 是首轮失败后进入末尾重试的区间数 |
| `shared_map.canary.slots` | array[integer] | 是 | 长度64 |
| `shared_map.canary.counts_sha256` | string (sha256 hex) | 是 |  |
| `shared_map.canary.verified_at` | string | 是 |  |
| `ledger.path` | string | 是 |  |
| `ledger.size` | integer | 是 |  |
| `ledger.sha256` | string (sha256 hex) | 是 |  |
| `ledger.requests` | integer | 是 |  |
| `ledger.success_ranges_sha256` | string (sha256 hex) | 是 |  |

不变量：

- scan_ranges 并集覆盖案区间；sample_ranges 不计入。
- `identity-anchor` ledger 行记录本次 SQD 对历史锚 slot 的块号/块哈希实测，固定 `counts_coverage=false`。identity-anchor 行只证明历史锚，不计入 counts 覆盖并集；只有实际连续拉取的 `recheck` 行才声明对应重验点覆盖。
- recheck 每个连续请求区间分为 verified（完整返回且逐 slot 等于资产）、mismatch（完整返回但至少一值不同）、request-failed（transport 失败、part 缺失、返回长度短于请求区间或 worker 异常）。首轮 request-failed 区间在同一并发池末尾统一重试一次；失败行直接 `counts_coverage=false`。
- 任一 mismatch 仍使整张地图回退 full，原因保持 `recheck-mismatch:<slot>`；canary 值逐值不等仍为 `canary-counts-changed`。canary 所在区间重试后仍 request-failed 时整图回退，原因为 `canary-recheck-unavailable`。
- 非 canary 区间重试后仍失败时写入 `unverified_ranges`，对应复用字节清零并由 full 补扫；其余已验证字节继续复用。`map-reuse` ledger 行和 scan_ranges 条目按 `reused_ranges` 每个连续子区间逐段生成，`response_sha256` 只哈希该段实际复用字节，不得覆盖未验证段或案区间外 slot；若本案没有可复用子区间，则不得生成 map-reuse 行。
- 无 UNSCANNED；解压长度等于区间长度；ledger 成功区间并集无洞且等于 scan_ranges 并集。
- skipped_confirmation.ranges[] 每段字段恰为 {from,to,response_sha256,count,response_ok,array_monotonic_unique,array_in_range}。
- complete 不落盘；离线 validator 的 complete 合取式＝response_ok ∧ array_monotonic_unique ∧ array_in_range ∧ (to−from+1) ≤ 500,000 ∧ reference_head_at_check ≥ to ∧ 位图该段长度 == to−from+1 ∧ popcount == count ∧ count ≤ 区间长度。
- array_monotonic_unique 与 array_in_range 是生产时对原始响应数组的断言结果；任一为 false 则该段 unconfirmed，其 NO_HEADER 保持未确认，有效 verdict 为 INCONCLUSIVE；--live-canary 重拉若干段与位图切片对表。
- era_params 固定为 {window:1000000,min_headers:10000,min_ratio_num:99,min_ratio_den:100}；判定使用整数交叉相乘 nonce_blocks*min_ratio_den >= header_blocks*min_ratio_num。
- summary/verdict 从 slot_counts 重算。
- 探针不可变；重跑产生新 probe_id。
- 探针发布协议：data/sqd_coverage/pending-<scan_id>/ 写齐 coverage_map.json、slot_counts.bin.gz、blocks.bin.gz、ledger.jsonl 并逐文件 fsync → fsync 施工目录 → os.rename(pending-<scan_id>, <probe_id>) → fsync data/sqd_coverage 父目录 → .lock 独占内 CAS → 锁内 publish_overwrite CURRENT → 锁内 fsync 指针父目录。

注记：

- metadata_normalized 与 summary 子字段未完全展开。
- skipped_confirmation 与离线 complete 按 errata E2 重裁冻结。
- 探针发布协议按 errata E9 冻结；scan_id 仅作临时目录名。

### 14.2 `sqd-solana-coverage-pointer/v1`

- 生产者：`sqd_coverage_probe.py`（计划目标脚本）
- 消费者：coverage resolver；replay_edges.py reconcile
- 草案来源：`sqd-solana-coverage-pointer_v1.json`（PLAN.md §4.2.1 ＋ PLAN_errata_batch0.md E9/E10）

| 字段 | 类型 | 必填 | 说明与约束 |
|---|---|---|---|
| `schema` | string | 是 | sqd-solana-coverage-pointer/v1 |
| `target.chain` | string | 是 | solana |
| `target.token` | string | 是 | mint |
| `target.as_of_block` | integer | 是 | slot_counts.to_slot |
| `mode` | string | 是 | formal |
| `verdict` | string | 是 | PASS |
| `exit_code` | integer | 是 | 0 |
| `producer` | object | 是 | path,sha256 |
| `inputs.coverage_map` | object | 是 | path,size,sha256；案根相对路径 data/sqd_coverage/<probe_id>/coverage_map.json |
| `inputs.slot_counts` | object | 是 | path,size,sha256；案根相对路径 data/sqd_coverage/<probe_id>/slot_counts.bin.gz |
| `inputs.ledger` | object | 是 | path,size,sha256；案根相对路径 data/sqd_coverage/<probe_id>/ledger.jsonl |
| `inputs.blocks_bitmap` | object | 否 | path,size,sha256；仅 skipped_confirmation 非 null 时出现；否则省略而非 null |
| `probe_id` | string | 是 | coverage_map 去 probe_id 后规范化内容 sha256 前16位 |
| `supersedes` | string\|null | 是 | 发布时所见 CURRENT.probe_id；无 CURRENT 时为 null |
| `published_at` | string | 是 |  |
| `producer.path` | string | 是 |  |
| `producer.sha256` | string (sha256 hex) | 是 |  |
| `inputs.coverage_map.path` | string | 是 |  |
| `inputs.coverage_map.size` | integer | 是 |  |
| `inputs.coverage_map.sha256` | string (sha256 hex) | 是 |  |
| `inputs.slot_counts.path` | string | 是 |  |
| `inputs.slot_counts.size` | integer | 是 |  |
| `inputs.slot_counts.sha256` | string (sha256 hex) | 是 |  |
| `inputs.ledger.path` | string | 是 |  |
| `inputs.ledger.size` | integer | 是 |  |
| `inputs.ledger.sha256` | string (sha256 hex) | 是 |  |
| `inputs.blocks_bitmap.path` | string | 否 |  |
| `inputs.blocks_bitmap.size` | integer | 否 |  |
| `inputs.blocks_bitmap.sha256` | string (sha256 hex) | 否 |  |

不变量：

- inputs 四项固定为 coverage_map、slot_counts、ledger、blocks_bitmap；blocks_bitmap 仅在 skipped_confirmation 非 null 时出现，否则省略而非 null。
- resolver 校验 inputs.coverage_map.sha256==sha256(coverage_map 文件) 且 probe_id 重算一致。
- 施工目录 pending-<scan_id> 完整持久化并原子改名为 <probe_id> 后，才允许锁内发布 CURRENT。
- 锁内 CAS 要求 pointer.supersedes==当前 CURRENT.probe_id；无 CURRENT 时 supersedes 为 null。
- 若 CURRENT.probe_id==pointer.probe_id 且 CURRENT.inputs.coverage_map.sha256==sha256(<probe_id>/coverage_map.json)，不改 CURRENT，只补 fsync 指针父目录并成功返回退出码 0，日志标 idempotent-republish。
- 仅同 probe_id 幂等条件不满足时按原 CAS；CAS 失败不得覆盖。

注记：

- E3 字段表作废，以 errata E9 为准。
- 探针指针同构幂等分支按 errata E10 冻结。

### 14.3 `sqd-solana-coverage-resolution/v1`

- 生产者：`sqd_gap_repair.py`（计划目标脚本）
- 消费者：solana_exact_validate.py；bundle builder
- 草案来源：`sqd-solana-coverage-resolution_v1.json`（PLAN.md §4.2.4）

| 字段 | 类型 | 必填 | 说明与约束 |
|---|---|---|---|
| `schema` | string | 是 | sqd-solana-coverage-resolution/v1 |
| `mint` | string | 是 |  |
| `plan_digest` | string | 是 |  |
| `coverage.probe_id` | string | 是 |  |
| `coverage.map_sha256` | string (sha256 hex) | 是 |  |
| `census[].slot` | integer | 是 |  |
| `census[].state_in_map` | string | 是 |  |
| `census[].result` | string | 是 | confirmed_nonce_defect/confirmed_other_defect/confirmed_missing_block/refuted |
| `census[].sqd_tx_count` | integer | 是 |  |
| `census[].sqd_blockhash` | string | 是 |  |
| `census[].ref_tx_count` | integer | 是 |  |
| `census[].ref_nonvote_count` | integer | 是 |  |
| `census[].ref_blockhash` | string | 是 |  |
| `census[].missing_total` | integer | 是 |  |
| `census[].missing_nonce` | integer | 是 |  |
| `census[].missing_err_excluded` | integer | 是 |  |
| `census[].evidence.sqd` | object | 是 | path,size,sha256 |
| `census[].evidence.ref` | object | 是 | path,size,sha256 |
| `effective_verdict` | string | 是 | 展示值，须重算 |
| `census[].evidence.sqd.path` | string | 是 |  |
| `census[].evidence.sqd.size` | integer | 是 |  |
| `census[].evidence.sqd.sha256` | string (sha256 hex) | 是 |  |
| `census[].evidence.ref.path` | string | 是 |  |
| `census[].evidence.ref.size` | integer | 是 |  |
| `census[].evidence.ref.sha256` | string (sha256 hex) | 是 |  |

不变量：

- 所有候选有归宿。
- 任一 confirmed=>DEFECTS_CONFIRMED。
- 未归宿候选=>INCONCLUSIVE。

### 14.4 `sqd-solana-repair-layer/v1`

- 生产者：`sqd_gap_repair.py`（计划目标脚本）
- 消费者：solana_exact_validate.py；bundle builder；merged edge producer
- 草案来源：`sqd-solana-repair-layer_v1.json`（PLAN.md §4.2.2）

| 字段 | 类型 | 必填 | 说明与约束 |
|---|---|---|---|
| `header.schema` | string | 是 | sqd-solana-repair-layer/v1 |
| `header.mint` | string | 是 |  |
| `header.plan_digest` | string | 是 |  |
| `header.base.edge_sha256` | string (sha256 hex) | 是 |  |
| `header.base.meta_sha256` | string (sha256 hex) | 是 |  |
| `header.coverage.probe_id` | string | 是 |  |
| `header.coverage.map_sha256` | string (sha256 hex) | 是 |  |
| `header.reference.kind` | string | 是 | helius-getBlock |
| `header.reference.endpoint_fingerprint` | string | 是 |  |
| `header.producer.path` | string | 是 |  |
| `header.producer.sha256` | string (sha256 hex) | 是 |  |
| `transaction.signature` | string | 是 | 唯一键 |
| `transaction.slot` | integer | 是 |  |
| `transaction.reference_position` | integer | 是 |  |
| `transaction.nonvote_ordinal` | integer | 是 |  |
| `transaction.nonce` | boolean | 是 |  |
| `transaction.class` | string | 是 | nonce/other/missing_block |
| `transaction.edges` | array[array] | 是 | [ts,slot,nonvote_ordinal,-1,from,to,amt]；多边；edge_sort_key 排序 |
| `transaction.evidence.sqd` | string | 是 |  |
| `transaction.evidence.ref` | string | 是 |  |

不变量：

- header 含 plan_digest、不含 gid。
- 唯一键 signature。
- 只含 meta.err==null 交易。
- edges 使用 pair_tx 7元组语义。

### 14.5 `sqd-solana-slot-index-map/v1`

- 生产者：`sqd_gap_repair.py`（计划目标脚本）
- 消费者：solana_exact_validate.py；merged edge producer
- 草案来源：`sqd-solana-slot-index-map_v1.json`（PLAN.md §4.2.7）

| 字段 | 类型 | 必填 | 说明与约束 |
|---|---|---|---|
| `header.schema` | string | 是 | sqd-solana-slot-index-map/v1 |
| `header.mint` | string | 是 |  |
| `header.plan_digest` | string | 是 |  |
| `row.slot` | integer | 是 |  |
| `row.blockhash` | string | 是 |  |
| `row.map` | array[array] | 是 | [sqd_index,nonvote_ordinal,signature] |
| `row.sqd_count` | integer | 是 |  |
| `row.ref_nonvote_count` | integer | 是 |  |

不变量：

- 三列各自唯一双射且单调递增。
- 每条 base 边 (slot,tx_index) 恰有一解；无解中止。

### 14.6 `sqd-solana-repair-bundle/v1`

- 生产者：`sqd_gap_repair.py`（计划目标脚本）
- 消费者：solana_exact_validate.py；repair resolver；CURRENT publisher
- 草案来源：`sqd-solana-repair-bundle_v1.json`（PLAN.md §4.2.3）

| 字段 | 类型 | 必填 | 说明与约束 |
|---|---|---|---|
| `schema` | string | 是 | sqd-solana-repair-bundle/v1 |
| `mint` | string | 是 |  |
| `plan_digest` | string | 是 |  |
| `gid` | string | 是 |  |
| `kind` | string | 是 | repair |
| `mode` | string | 是 | formal/exploration |
| `producer` | object | 是 |  |
| `base` | object | 是 | edge_file,meta_file,edge_sha256,meta_sha256,edge_logical_sha256,edge_rows,finalized_upper_slot |
| `coverage` | object | 是 | probe_id,map{path,size,sha256},slot_counts{…} |
| `coverage_resolution` | object | 是 | path,size,sha256 |
| `repair_layer` | object | 是 | path,size,sha256,transactions,edges |
| `slot_index_map` | object | 是 | path,size,sha256,slots |
| `evidence_manifest` | object | 是 | path,size,sha256 |
| `merged` | object | 是 | edge_file,meta_file,edge_sha256,meta_sha256,edge_logical_sha256,edge_rows |
| `reference` | object | 是 | kind,endpoint_fingerprint,source；source=live/local-evidence-cache |
| `rpc_ledger` | object | 是 | path,size,sha256,requests,credits_estimate |
| `supersedes` | string\|null | 是 |  |
| `generated_at` | string | 是 | 类型为推断 |
| `producer.path` | string | 是 |  |
| `producer.sha256` | string (sha256 hex) | 是 |  |
| `base.edge_file` | string | 是 |  |
| `base.meta_file` | string | 是 |  |
| `base.edge_sha256` | string (sha256 hex) | 是 |  |
| `base.meta_sha256` | string (sha256 hex) | 是 |  |
| `base.edge_logical_sha256` | string (sha256 hex) | 是 |  |
| `base.edge_rows` | integer | 是 |  |
| `base.finalized_upper_slot` | integer | 是 |  |
| `coverage.probe_id` | string | 是 |  |
| `coverage.map.path` | string | 是 |  |
| `coverage.map.size` | integer | 是 |  |
| `coverage.map.sha256` | string (sha256 hex) | 是 |  |
| `coverage.slot_counts.path` | string | 是 |  |
| `coverage.slot_counts.size` | integer | 是 |  |
| `coverage.slot_counts.sha256` | string (sha256 hex) | 是 |  |
| `coverage_resolution.path` | string | 是 |  |
| `coverage_resolution.size` | integer | 是 |  |
| `coverage_resolution.sha256` | string (sha256 hex) | 是 |  |
| `repair_layer.path` | string | 是 |  |
| `repair_layer.size` | integer | 是 |  |
| `repair_layer.sha256` | string (sha256 hex) | 是 |  |
| `repair_layer.transactions` | integer | 是 |  |
| `repair_layer.edges` | integer | 是 |  |
| `slot_index_map.path` | string | 是 |  |
| `slot_index_map.size` | integer | 是 |  |
| `slot_index_map.sha256` | string (sha256 hex) | 是 |  |
| `slot_index_map.slots` | integer | 是 |  |
| `evidence_manifest.path` | string | 是 |  |
| `evidence_manifest.size` | integer | 是 |  |
| `evidence_manifest.sha256` | string (sha256 hex) | 是 |  |
| `merged.edge_file` | string | 是 |  |
| `merged.meta_file` | string | 是 |  |
| `merged.edge_sha256` | string (sha256 hex) | 是 |  |
| `merged.meta_sha256` | string (sha256 hex) | 是 |  |
| `merged.edge_logical_sha256` | string (sha256 hex) | 是 |  |
| `merged.edge_rows` | integer | 是 |  |
| `reference.kind` | string | 是 |  |
| `reference.endpoint_fingerprint` | string | 是 |  |
| `reference.source` | string | 是 | live/local-evidence-cache |
| `rpc_ledger.path` | string | 是 |  |
| `rpc_ledger.size` | integer | 是 |  |
| `rpc_ledger.sha256` | string (sha256 hex) | 是 |  |
| `rpc_ledger.requests` | integer | 是 |  |
| `rpc_ledger.credits_estimate` | integer | 是 |  |

不变量：

- merged.edge_rows==base.edge_rows+repair_layer.edges。
- mode==formal 当且仅当 reference.source==live。
- exploration 不发指针。
- refuted-only 不产代不发指针。

### 14.7 `sqd-solana-repair-pointer/v1`

- 生产者：receipt_kernel.publish_overwrite（由 sqd_gap_repair.py 调用）
- 消费者：repair resolver；solana_exact_validate.py
- 草案来源：`sqd-solana-repair-pointer_v1.json`（PLAN.md §4.2.3）

| 字段 | 类型 | 必填 | 说明与约束 |
|---|---|---|---|
| `schema` | string | 是 | sqd-solana-repair-pointer/v1 |
| `target.chain` | string | 是 | solana |
| `target.token` | string | 是 |  |
| `target.as_of_block` | integer | 是 | base.finalized_upper_slot |
| `mode` | string | 是 | formal |
| `verdict` | string | 是 | PASS |
| `exit_code` | integer | 是 | 0 |
| `producer` | object | 是 |  |
| `inputs.bundle` | object | 是 | path,size,sha256 |
| `gid` | string | 是 |  |
| `supersedes` | string\|null | 是 |  |
| `published_at` | string | 是 | 类型为推断 |
| `producer.path` | string | 是 |  |
| `producer.sha256` | string (sha256 hex) | 是 |  |
| `inputs.bundle.path` | string | 是 |  |
| `inputs.bundle.size` | integer | 是 |  |
| `inputs.bundle.sha256` | string (sha256 hex) | 是 |  |

不变量：

- bundle.supersedes==切换瞬间 CURRENT.gid；无 CURRENT 时为 null。
- bundle.base.edge_sha256==当前 base 哈希。
- 若 CURRENT.gid==bundle.gid 且 CURRENT.inputs.bundle.sha256==sha256(gen-<gid>/bundle.json)，不改 CURRENT，只补 fsync 指针父目录并成功返回退出码 0，日志标 idempotent-republish。
- 仅同 gid 幂等条件不满足时按原 CAS；CAS 失败不得覆盖。

注记：

- 同 gid 幂等分支按 errata E10 冻结。

### 14.8 `sqd-solana-rpc-ledger/v1`

- 生产者：`sqd_gap_repair.py`（计划目标脚本）
- 消费者：--resume；bundle rpc_ledger；operator diagnostics
- 草案来源：`rpc_ledger.json`（PLAN.md §4.2.10）

| 字段 | 类型 | 必填 | 说明与约束 |
|---|---|---|---|
| `header.schema` | string | 是 | rpc_ledger.jsonl 首行 header；sqd-solana-rpc-ledger/v1 |
| `header.plan_digest` | string | 是 | rpc_ledger.jsonl 首行 header；其后逐行不重复；等于 pending-<plan_digest> 目录名且等于 bundle.plan_digest |
| `header.reference.kind` | string | 是 | rpc_ledger.jsonl 首行 header |
| `header.reference.endpoint_fingerprint` | string | 是 | rpc_ledger.jsonl 首行 header |
| `seq` | integer | 是 |  |
| `ts` | integer | 是 |  |
| `method` | string | 是 | getBlock/getBlocks |
| `params_digest` | string | 是 |  |
| `slot` | integer | 否 |  |
| `range` | array\|object | 否 | 类型为推断 |
| `endpoint_fingerprint` | string | 是 |  |
| `http_status` | integer | 是 |  |
| `bytes` | integer | 是 |  |
| `credits_estimate` | integer | 是 |  |
| `result_sha256` | string (sha256 hex) | 是 |  |
| `attempt` | integer | 是 |  |

不变量：

- slot/range 按 method 二选一。
- 异常先 redact，key 不落盘。
- resume 以 (plan_digest,params_digest,result_sha256) 判完成；plan_digest 取自首行 header。
- header.plan_digest==所在 pending-<plan_digest> 目录名==bundle.plan_digest。
- 残缺尾行丢弃。

注记：

- range 形状未写明，类型为推断。
- 首行 header 按 errata E6 增补；逐行字段保持 PLAN §4.2.10 不变。

### 14.9 `solana-reconcile/v4`

- 生产者：scripts/solana/replay_edges.py reconcile
- 消费者：shared_release_receipt.validate_reconciliation_check；handoff_manifest.py verify；audit_release_gate.py；camp_series_provenance.py
- 草案来源：`solana-reconcile_v4.json`（PLAN.md §4.2.8）

| 字段 | 类型 | 必填 | 说明与约束 |
|---|---|---|---|
| `schema` | string | 是 | solana-reconcile/v4 |
| `target.chain` | string | 是 | solana |
| `target.token` | string | 是 |  |
| `target.as_of_block` | integer | 是 |  |
| `mode` | string | 是 | formal |
| `verdict` | string | 是 | gate_pass true⇒PASS；gate_pass false⇒FAIL；由 receipt_kernel.finalize_envelope 强制一致 |
| `exit_code` | integer | 是 | gate_pass true⇒0；gate_pass false⇒2；由 receipt_kernel.finalize_envelope 强制一致 |
| `producer` | object | 是 |  |
| `inputs.soltx_edges` | object | 是 | path,size,sha256 |
| `inputs.soltx_meta` | object | 是 | path,size,sha256 |
| `inputs.holders_owners` | object | 是 | path,size,sha256 |
| `inputs.holders_snapshot_meta` | object | 是 | path,size,sha256 |
| `inputs.coverage_map` | object | 是 | path,size,sha256 |
| `inputs.coverage_slot_counts` | object | 是 | path,size,sha256 |
| `inputs.coverage_pointer` | object | 是 | path,size,sha256；案根 data/sqd_coverage/CURRENT.json；必填；绑定发布时 CURRENT 的当前内容 |
| `inputs.coverage_resolution` | object | 否 | repaired；base 省略 |
| `inputs.repair_bundle` | object | 否 | repaired；base 省略 |
| `inputs.repair_pointer` | object | 否 | repaired；base 省略 |
| `edge_source_binding.cache_kind` | string | 是 | base/repaired |
| `edge_source_binding.gid` | string\|null | 是 |  |
| `edge_source_binding.soltx_edges_sha256` | string (sha256 hex) | 是 |  |
| `edge_source_binding.soltx_meta_sha256` | string (sha256 hex) | 是 |  |
| `edge_source_binding.edge_logical_sha256` | string (sha256 hex) | 是 |  |
| `coverage_effective_verdict` | string | 是 |  |
| `gate_pass` | boolean | 是 |  |
| `negative_balance_count` | integer | 是 |  |
| `snapshot_mismatch_count` | integer | 是 |  |
| `minted_raw` | JSON int | 是 | v3 string → v4 JSON int（E14）；禁止字符串整数 |
| `burned_raw` | JSON int | 是 | v3 string → v4 JSON int（E14）；禁止字符串整数 |
| `snapshot_supply_raw` | JSON int | 是 | v3 string → v4 JSON int（E14）；禁止字符串整数 |
| `net_supply_raw` | integer | 是 |  |
| `edge_digest` | string | 是 |  |
| `edge_count` | integer | 是 |  |
| `cli.--as-of-slot` | integer | 是 |  |
| `cli.--receipt` | string | 否 | argv 内且预先不存在；默认 data/reconcile_receipt.json |
| `inputs.soltx_edges.path` | string | 是 |  |
| `inputs.soltx_edges.size` | integer | 是 |  |
| `inputs.soltx_edges.sha256` | string (sha256 hex) | 是 |  |
| `inputs.soltx_meta.path` | string | 是 |  |
| `inputs.soltx_meta.size` | integer | 是 |  |
| `inputs.soltx_meta.sha256` | string (sha256 hex) | 是 |  |
| `inputs.holders_owners.path` | string | 是 |  |
| `inputs.holders_owners.size` | integer | 是 |  |
| `inputs.holders_owners.sha256` | string (sha256 hex) | 是 |  |
| `inputs.holders_snapshot_meta.path` | string | 是 |  |
| `inputs.holders_snapshot_meta.size` | integer | 是 |  |
| `inputs.holders_snapshot_meta.sha256` | string (sha256 hex) | 是 |  |
| `inputs.coverage_map.path` | string | 是 |  |
| `inputs.coverage_map.size` | integer | 是 |  |
| `inputs.coverage_map.sha256` | string (sha256 hex) | 是 |  |
| `inputs.coverage_slot_counts.path` | string | 是 |  |
| `inputs.coverage_slot_counts.size` | integer | 是 |  |
| `inputs.coverage_slot_counts.sha256` | string (sha256 hex) | 是 |  |
| `inputs.coverage_pointer.path` | string | 是 | data/sqd_coverage/CURRENT.json |
| `inputs.coverage_pointer.size` | integer | 是 |  |
| `inputs.coverage_pointer.sha256` | string (sha256 hex) | 是 | 必须等于 CURRENT.json 当前内容 sha256 |
| `inputs.coverage_resolution.path` | string | 否 |  |
| `inputs.coverage_resolution.size` | integer | 否 |  |
| `inputs.coverage_resolution.sha256` | string (sha256 hex) | 否 |  |
| `inputs.repair_bundle.path` | string | 否 |  |
| `inputs.repair_bundle.size` | integer | 否 |  |
| `inputs.repair_bundle.sha256` | string (sha256 hex) | 否 |  |
| `inputs.repair_pointer.path` | string | 否 |  |
| `inputs.repair_pointer.size` | integer | 否 |  |
| `inputs.repair_pointer.sha256` | string (sha256 hex) | 否 |  |
| `producer.path` | string | 是 |  |
| `producer.sha256` | string (sha256 hex) | 是 |  |

继承字段（现役基线逐键抄录）：

| 字段 | 源码行 | v4/v3 类型修订 |
|---|---:|---|
| `schema` | 356 |  |
| `chain` | 356 |  |
| `mint` | 356 |  |
| `collection_window` | 357 |  |
| `collection_window.from_slot` | 357 |  |
| `collection_window.to_slot` | 357 |  |
| `edge_extrema` | 358 |  |
| `edge_extrema.first` | 358 |  |
| `edge_extrema.first.slot` | 270 |  |
| `edge_extrema.first.ts` | 270 |  |
| `edge_extrema.last` | 358 |  |
| `edge_extrema.last.slot` | 270 |  |
| `edge_extrema.last.ts` | 270 |  |
| `edge_digest` | 359 |  |
| `edge_count` | 359 |  |
| `producer` | 360 |  |
| `producer.path` | 360 |  |
| `producer.sha256` | 361 |  |
| `inputs` | 362 |  |
| `inputs.soltx_meta` | 362 |  |
| `inputs.soltx_meta.path` | 122 |  |
| `inputs.soltx_meta.size` | 122 |  |
| `inputs.soltx_meta.sha256` | 123 |  |
| `inputs.holders_owners` | 363 |  |
| `inputs.holders_owners.path` | 122 |  |
| `inputs.holders_owners.size` | 122 |  |
| `inputs.holders_owners.sha256` | 123 |  |
| `inputs.holders_snapshot_meta` | 364 |  |
| `inputs.holders_snapshot_meta.path` | 122 |  |
| `inputs.holders_snapshot_meta.size` | 122 |  |
| `inputs.holders_snapshot_meta.sha256` | 123 |  |
| `minted_raw` | 365 | v3: string → v4: JSON int（E14） |
| `burned_raw` | 365 | v3: string → v4: JSON int（E14） |
| `net_supply_raw` | 366 |  |
| `negative_balance_count` | 367 |  |
| `snapshot_present` | 367 |  |
| `snapshot_meta_present` | 368 |  |
| `snapshot_closed` | 368 |  |
| `snapshot_supply_raw` | 369 | v3: string → v4: JSON int（E14） |
| `snapshot_mismatch_count` | 370 |  |
| `gate_pass` | 370 |  |

不变量：

- inherited_fields 所列 v3 字段全部保留。
- base 模式省略后三 inputs，不写 null。
- --as-of-slot==快照slot==finalized_upper_slot。
- coverage 当前性深验：data/sqd_coverage/CURRENT.json 当前内容 sha256==receipt.inputs.coverage_pointer.sha256，pointer.inputs.coverage_map.path==receipt.inputs.coverage_map.path，且 probe_id 重算一致；CURRENT 更新后旧 receipt 一律 FAIL。
- gate_pass is True ⇒ verdict=PASS 且 exit_code=0；gate_pass is False ⇒ verdict=FAIL 且 exit_code=2；receipt_kernel.finalize_envelope 强制，validator 校验三者互洽。
- 不回写 base meta edge_file_size/sha256。
- minted_raw、burned_raw、snapshot_supply_raw 在 v4 必须是 JSON int；字符串整数拒收。

注记：

- inherited_fields 从 scripts/solana/replay_edges.py 的 cmd_reconcile 现役 v3 receipt 写出点逐键抄录（代码基线 f06078e）。
- 唯一删除项：不再回写 base meta 的 edge_file_size/edge_file_sha256；这是写入副作用删除，不是 receipt 字段删除。

### 14.10 `reconciliation-report/v3`

- 生产者：scripts/report/reconciliation_report.py
- 消费者：shared_release_receipt.validate_reconciliation_report；handoff_manifest.py verify；audit_release_gate.py
- 草案来源：`reconciliation-report_v3.json`（PLAN.md §4.4.4）

| 字段 | 类型 | 必填 | 说明与约束 |
|---|---|---|---|
| `schema` | string | 是 | reconciliation-report/v3 |
| `family` | string | 是 | 由 target 推导，不接受外部声明；evm/solana |
| `checks` | object | 是 | 单层 checks{<key>:...}；不得嵌套 checks.evm/checks.solana；family=evm 时固定顺序 balance,supply,supply_truth,time；family=solana 时固定顺序 supply,balance,supply_truth,time,exact_reconcile |
| `checks.exact_reconcile.receipt→schema` | string | family==solana 的引用实物内必填；family==evm 无该 item | `solana-reconcile/v4`；不是 wrapper item 直属字段 |
| `checks.exact_reconcile.receipt→mode` | string | family==solana 的引用实物内必填；family==evm 无该 item | `formal`；不是 wrapper item 直属字段 |
| `checks.exact_reconcile.receipt→gate_pass` | boolean | family==solana 的引用实物内必填；family==evm 无该 item | `true`；不是 wrapper item 直属字段 |
| `checks.exact_reconcile.receipt→negative_balance_count` | integer | family==solana 的引用实物内必填；family==evm 无该 item | `0`；不是 wrapper item 直属字段 |
| `checks.exact_reconcile.receipt→snapshot_mismatch_count` | integer | family==solana 的引用实物内必填；family==evm 无该 item | `0`；不是 wrapper item 直属字段 |
| `job_spec.slot_binding` | argv 约束 | dynamic Solana 必填 | balance／supply_truth／time 必须消费 `{observed_as_of_block}`；`exact_reconcile` 的 argv 禁止出现该占位符，且 `--as-of-slot` 必须是账本缓存 `finalized_upper_slot` 的非负整数字面量 |
| `cli.--reseal` | string | 否 | 仅 EVM |

继承字段（现役基线逐键抄录）：

| 字段 | 源码行 | v4/v3 类型修订 |
|---|---:|---|
| `schema` | 119 |  |
| `target` | 120 |  |
| `producer` | 121 |  |
| `verdict` | 122 |  |
| `exit_code` | 123 |  |
| `checks` | 124 |  |
| `inputs` | 209 |  |
| `error` | 276 |  |

不变量：

- wrapper 一律 v3；v2 fail-closed。
- checks 保持单层 checks{<key>}；family=evm 的键集恰为 balance,supply,supply_truth,time，family=solana 的键集恰为 supply,balance,supply_truth,time,exact_reconcile，顺序固定。
- EVM reseal 从四份 receipt 重建，不信旧 wrapper；失败拒绝。
- Solana v2 重跑 v4 exact+五项。
- `checks.exact_reconcile` 的 wrapper item 固定绑定 `{status,exit_code,process_exit_code,producer,receipt}`；上表五个 v4 字段位于 `receipt{path,size,sha256}` 引用的实物内，由公共 validator 打开后深验，不是 item 直属字段。该 item 仅 family=solana 必填；family=evm 必须省略，出现即拒。
- 动态 Solana wrapper 的观测 target 可以晚于第五查的冻结 target；仅 `exact_reconcile` 放宽为 chain/token 全等且 `0 ≤ receipt.as_of_block ≤ wrapper.as_of_block`。其余 Solana checks 与全部 EVM checks 仍要求 receipt target 和 wrapper target 全等。
- exact 检查组合、inputs 案根哈希并调用独立深验。静态态（exact 与 wrapper 的 `as_of_block` 相等）继续要求 exact 与 supply 的 `holders_owners` 是同一文件；冻结态（exact 早于 wrapper）则要求 exact 快照的 sha256+size 与案内 `data/solana_observation_bundle_frozen.json` 的 `holder_outputs.owners` 全等，且该冻结 bundle 经过与活 supply bundle 同深度的案根信封、schema、主网 genesis attestation、closed/closure 与 target 深验，并同时进入 handoff 的 data_map/artifacts。大白话：活观测回答“现在”，冻结快照回答“封账点”，不再强迫两者共用文件；防伪改由冻结 bundle 的内容指纹承担。独立深验仍把 `receipt.target.as_of_block` 正向绑定到 receipt 所绑 `soltx_meta.finalized_upper_slot`，不得拿任意旧时点收据冒充冻结点。
- 动态 Solana 的分布扫描固定消费观察 owners；三账 B-7、series cutoff、accounting 等冻结账消费者固定消费 exact 收据 owners＋冻结块，并由同一个中央选择器完成投影。

注记：

- inherited_fields 从 scripts/report/reconciliation_report.py 的 _base_wrapper 及后续 inputs/error 填充处逐键抄录（代码基线 f06078e），按 errata E7 前移冻结。
- checks 形状按 errata E12 冻结为单层。
- checks.exact_reconcile 的条件必填规则按 errata E18 冻结；批 6 只把五个 v4 字段明确为 referenced receipt fields，与现役 runner/validator 结构对齐。

### 14.13 `edge_source_binding（edge-source-binding/v1）`

- 生产者：replay_edges.py reconcile / cache resolver
- 消费者：wave-scan/v5；flow-anomaly/v3；entity_source_trace；curve_cost；audit_closed_accounts；evolution/sol-rows sidecar；handoff verify；audit_release_gate；camp compiler
- 草案来源：`edge_source_binding.json`（PLAN.md §4.2.9）

| 字段 | 类型 | 必填 | 说明与约束 |
|---|---|---|---|
| `cache_kind` | string | 是 | base/repaired |
| `gid` | string\|null | 是 |  |
| `soltx_edges_sha256` | string (sha256 hex) | 是 |  |
| `soltx_meta_sha256` | string (sha256 hex) | 是 |  |
| `edge_logical_sha256` | string (sha256 hex) | 是 |  |

不变量：

- wave v5/flow v3：Solana 必填，EVM 省略。
- 在场或被引用即与 exact receipt 逐字段全等。
- 旧 wave v4/flow v2 fail-closed 提示重跑。

### 14.11 `wave-scan/v5` 与 v4 的差异段

- 生产者：`scripts/report/wave_scan.py`；消费者：handoff、audit release、candidate adjudication。
- v5 保留 v4 全部字段，仅新增顶层 `edge_source_binding`。Solana 必填，EVM 省略；禁止写 `null` 代替省略。
- `edge_source_binding` 的逐字段定义与全等规则见 §14.13。旧 `wave-scan/v4` 在正式链 fail-closed，并提示以当前边源重跑。

不变量：

- Solana v5 的 `edge_source_binding` 必须与 `solana-reconcile/v4` exact receipt 逐字段全等。
- EVM v5 不得出现 `edge_source_binding`。

### 14.12 `flow-anomaly/v3` 与 v2 的差异段

- 生产者：`scripts/report/flow_anomaly_scan.py`；消费者：handoff、audit release、candidate adjudication。
- v3 保留 v2 全部字段，仅新增顶层 `edge_source_binding`。Solana 必填，EVM 省略；禁止写 `null` 代替省略。
- `edge_source_binding` 的逐字段定义与全等规则见 §14.13。旧 `flow-anomaly/v2` 在正式链 fail-closed，并提示以当前边源重跑。

不变量：

- Solana v3 的 `edge_source_binding` 必须与 `solana-reconcile/v4` exact receipt 逐字段全等。
- EVM v3 不得出现 `edge_source_binding`。

### 14.14 路由、术语与机械针

- `exact_reconcile` 是 Solana 受控对账的第五项，引用 `solana-reconcile/v4`；`reconciliation-report/v3` 的 `checks.exact_reconcile.*` 在 Solana 条件必填，在 EVM 必须省略。
- `sqd_gap_repair.py/v1` 是 repaired cache 的 collector 身份；正式 resolver 只接受当前 `CURRENT.json` 指向、bundle 哈希命中且绑定当前 base 的代。
- `reference-nonvote-ordinal/v1` 表示缺陷 slot 内按参考源非投票交易序号统一重编号；`slot_index_map` 必须证明 SQD index、签名与 nonvote ordinal 三列双射。
- “有块头但零 AdvanceNonce”是 coverage 指纹：存在 SQD 块头但该 slot 的 AdvanceNonce 计数为零；它只是机械候选，必须经 resolution 确认后才能成为修复依据。
- 探针与 repair 的 `CURRENT.json` 均是最后发布的 kernel 指针；pending 或无当前指针的孤儿 gen 不得进入 formal。

生产者/消费者路由：

| 协议族 | 生产者 | 消费者 |
|---|---|---|
| coverage + coverage pointer | `sqd_coverage_probe.py` | repair planner、`solana_exact_validate.py`、reconcile |
| resolution/layer/map/bundle/repair pointer/rpc ledger | `sqd_gap_repair.py` | resolver、`validate_repair_bundle`、`solana_exact_validate.py` |
| `solana-reconcile/v4` | `scripts/solana/replay_edges.py` | reconciliation wrapper、camp sidecar、handoff、audit release |
| wave v5 / flow v3 | wave/flow scanners | adjudication、handoff、audit release |
