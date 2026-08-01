---
description: 分段执行·判断段（−2）：verify fail-closed 后接 A3 判断层＋A4–A5（Fable 冷启动，消费 −1 交接契约）
argument-hint: <代币名或合约地址> <easy|full> [补充信息]
---

调用 token-chip-analysis skill 的**分段执行·判断段（−2）**，标的与档位：**$ARGUMENTS**（档位 easy|full 必填，缺失先问我）

唯一权威源＝`references/split-run.md` §3，开工序八步顺序执行，不可跳步：

1. **模型自检**：非 Fable/主力判断模型 → 警告我（不硬停）。
2. **`scripts/report/handoff_manifest.py verify --case-dir .` fail-closed**：exit 2 一律拒收（缺件/哈希漂移/gate 语义漂移/状态非 READY），报告缺什么让我裁决退回 −1 还是走旧单会话命令，**禁止带病开工**。
3. **数据保鲜检查**：默认按已有数据跑（报告如实标注数据时点）；仅当 cutoff 距今缺口 >72h 才弹警报 AskUserQuestion 停等我裁决，**绝不自动拉取**。
4. **必读件**：anomalies.json、四查结论、accounting_mode、E0b 结论（若有）。
5. **候选覆盖自检**：用重放产物独立重算候选清单比对 candidate_universe，无缺漏才继续。
6. data_map.json 当索引按需读盘，禁整读大产物；candidate_screening.json 当裁决工作台。
7. **sealed/ 禁读令**：entity_freeze.json 落盘前禁读（`freeze --check-unseal` exit 0 才准）；冻结后 sealed 观察只作 A4 差异靶单——**不是证据、不算复核路数**。
8. 判断主序按 split-run §3.2：casebook 过闸 → 聚类合并裁决 → 临时实体 → 无下限成员完整性扫描 → wave_scan 候选逐条裁决 → 反证检查 → `freeze` 落盘 → 正式 entity_identity_gate → 判级 → needs_adjudication 裁决 → 阵营演变重放 → 状态评估 → A4（外部异构路按 §3.3 收紧；开工 `a4_gate.py register`、收尾 `finalize` 封口产 a4_seal.json——**封口前禁画图/写报告/编 HTML**，6.7.0 顺序硬闸）→ A5 即收工（报告图一律 charts/final/、build_html `--a4-seal` 必传；A6 复盘仅我明确要求时跑）。

三问框架与铁律 7 条全程有效（同 /token-analyze）；easy 档交付两件套、full 档完整 HTML 报告；监控包默认不生成。
