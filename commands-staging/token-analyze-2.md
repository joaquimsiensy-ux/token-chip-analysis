---
description: 分段执行·判断段（−2）：verify fail-closed 后接 A3 判断层＋A4–A5（Fable 冷启动，消费 −1 交接契约）
argument-hint: <代币名或合约地址> full [补充信息]
---

调用 token-chip-analysis skill 的**分段执行·判断段（−2）**，标的与档位：**$ARGUMENTS**（档位只支持 `full`，缺失或不符时先问我）

唯一权威源＝`references/split-run.md` §3，开工序八步顺序执行，不可跳步：

1. **模型自检**：非 Fable/主力判断模型 → 警告我（不硬停）。
2. **`scripts/report/handoff_manifest.py verify --case-dir .` fail-closed**：exit 2 一律拒收（缺件/哈希漂移/gate 语义漂移/状态非 READY），报告缺什么让我裁决退回 −1 还是走旧单会话命令，**禁止带病开工**。
3. **数据保鲜检查**：默认按已有数据跑（报告如实标注数据时点）；仅当 cutoff 距今缺口 >72h 才弹警报 AskUserQuestion 停等我裁决，**绝不自动拉取**。
4. **必读件**：anomalies.json、四查结论、accounting_mode、点名式 CEX 黑箱关卡结论（若有）。
5. **候选覆盖自检**：用重放产物独立重算候选清单比对 candidate_universe，无缺漏才继续。
6. data_map.json 当索引按需读盘，禁整读大产物；candidate_screening.json 当裁决工作台。
7. **sealed/ 禁读令**：entity_freeze.json 落盘前禁读（`freeze --check-unseal` exit 0 才准）；冻结后 sealed 观察只作 A4 差异靶单——**不是证据、不算复核路数**。
8. 判断主序按 split-run §3.2：casebook 过闸 → 聚类合并裁决 → 临时实体 → 无下限成员完整性扫描 → wave/flow 候选逐条裁决 → `freeze` 落盘 → 正式 entity_identity_gate → 判级 → 阵营演变重放 → 状态评估 → A4 register/finalize 产 `a4-seal/v4`，并让 `dist-*` claims 与当前异常簇机器闭合 → final 分布扫描写 `dist_rounds/round_N/` → 新簇立即回流 A4；已覆盖异常跑五判据解释，未解释走成员级或盘面机制闭环后统一回流 A4 → 唯一终态才物化 `charts/final/holder_distribution_current.png` → `a5-report-seal/v3` → build_html G11。两轮仍非终态时必须让我选择第三轮或标准 waiver。A6 复盘仅我明确要求时跑。

三问一异常框架与铁律 7 条全程有效（同 /token-analyze）；只支持 full 档完整 HTML 报告；监控包默认不生成。
