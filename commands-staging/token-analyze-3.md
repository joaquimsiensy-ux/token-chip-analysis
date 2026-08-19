---
description: 分段执行·装配段（−3）：消费 −2 装配工单跑 A5 装配（三图＋流转图＋a5-report-seal/v3＋build_html G11＋发布闸），完成即停（适配 Opus 执行）
argument-hint: <代币名或合约地址> full [补充信息]
---

调用 token-chip-analysis skill 的**分段执行·装配段（−3）**，标的与档位：**$ARGUMENTS**（档位只支持 `full`，缺失或不符时先问我）

唯一分段权威源＝references/split-run.md §3b（分段边界与工单契约）；出图与发布纪律另见 analyze-workflow A5、结构措辞见 report-template（两者本册只指针）。硬性要点：

1. **模型自检**：本段设计给 Opus 执行（省判断模型额度）；检测到自己是 Fable/主力判断模型 → 提示"装配段建议换 Opus 会话"后继续（不硬停）。
2. **装配工单检查**：案根 `a5_assembly_workorder.json` 在场且可解析；缺件即停，提示先跑 −2 收口，禁自造工单；若案目录已是旧流程完成态（a5_report_seal.json 或正式 HTML 已在场）而无工单，属历史完成案，−3 不支持迁移——历史重编译走 build_html --mode legacy-recompile（带水印），勿重跑 −2。
3. **A5 链前置产物自检（只读核对，禁重造禁补票）**：a4_seal.json（a4-seal/v4 且 PASS）＋报告.md（sha256 与工单一致）＋distribution_rounds.json 已到唯一终态＋charts/final/holder_distribution_current.png 已物化＋facts.json 与 analysis-state.json 在场；任一缺失或漂移 → 停下报我裁决退回 −2，禁带病开工。
4. **执行序（split-run §3b.4）**：fig1（figures_from_facts.py fig1 从 state 直出，overlay 按工单）→ fig2（按工单 required_entity_ids 装配 whale_series.json **落案根**，figures_from_facts.py check 产 figure2_check_receipt 后出图）→ fig3（按工单 events 清单出图）→ 流转图逐张按工单 spec 指针 figures_from_facts.py flow 渲染 → 报告图片引用三方核对（工单有序清单／报告 IMG 正则重取／实产文件，三方精确一致）→ a5_report_seal.py 产 `a5-report-seal/v3` → build_html --mode analysis-new 过 G10/G11 与发布闸 exit 0。输出一律限 `charts/final/`，禁写案外路径。
5. **修错循环三分类**：图渲染失败、路径/receipt **缺件或落位**类红灯 → 自修重跑；报告.md 的逐字模板句或图路径字符串错 → 最小机械修正并逐条记工单 amendments 哈希链；**涉及数字/实体名/结论措辞的改动一律停工退回 −2；figure2_check 对账 FAIL、任何与 facts 数值不同源类失败同属本类（禁以"重跑"名义改数据或换选材）**。
6. **收工**：报 G11 与发布闸结果＋交付自查申报（图 2 实体线=工单 required 清单、流转图张数=工单 eligible 清单、amendments 全记录），完成即停；A6 复盘仅我明确要求时执行。
