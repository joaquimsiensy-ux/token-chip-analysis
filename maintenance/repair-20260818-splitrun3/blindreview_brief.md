# 盲审任务书（v6.50.0 split-run 三段化工程）

对象：分支 fix/splitrun3-20260818 相对 main（e1be99a）的全部改动。`git diff main...HEAD` 加 untracked 的 commands-staging/token-analyze-3.md 与 maintenance/repair-20260818-splitrun3/。

改动主旨（供盲审者建立预期，不构成辩护）：
- 分段执行 −1/−2 扩为 −1/−2/−3：新增 /token-analyze-3 装配段命令＋split-run §3b（A5 装配执行侧独立会话）；−2 收口前移＝报告正文成稿＋四条收口自查＋产 a5_assembly_workorder.json 即停
- ET-1 报警地址证据采集前置 −1（停止线拆"归属定性深挖禁做/证据采集可做"，保守超集分母，et1_evidence_packs.json optional 但存在即入 manifest allowlist）
- context-discipline 刀 1 机械档扩为 14 项公告＋2b 六条纪律（唯一权威源制），research-workflows §二b 钉法改指针
- 新契约 CT-SEMANTIC-61/62、CT-BANNED-16；deploy-sync EXPECTED 与 batch3 COMMANDS 扩四元＋−3 四类负例
- 版本 6.50.0（跳 6.49.0，被并行 sqd 分支占用）

**已声明的残余风险（用户拍板接受，重复报告不计为 finding）**：装配工单无 validator、不进 handoff manifest；图表应有基数/fig2 实体线覆盖完整性/渲染输入与 check 输入同一性/工单字段完备性属文字纪律（split-run §3b.5 已如实声明）；−2 公告外包靠条文无机器闸。
**预期红（不计 finding）**：worktree 内 test_commands_deploy_sync 红（部署 cp 在合并 main 后执行，CHANGELOG 已注明）。

## 正常盲审（codex）视角清单（六视角逐条过，每条写明检查了哪些文件）

① 字段来源审计：新契约/snapshot/fixture 的值有没有抄错来源；done 报告自报的验收结果与实物一致吗
② 失败分支审计：token-analyze-3.md 与 §3b 每个"自检/核对"步骤有没有静默继续的分支
③ 存量迁移：旧案目录（无装配工单）撞上新 −2/−3 命令会发生什么；单会话 /token-analyze 是否不受影响
④ 同族调用面：−1/−2/−3 与单会话命令四处、split-run/analyze-workflow/context-discipline/SKILL.md 的分段表述是否等深一致
⑤ 双向一致性：本次 15 个文件里同一事实的副本有没有互相矛盾（特别是 −2 收口点、ET-1 归属、外包档位的 N 处表述）
⑥ 可绕性：三条新契约锁的 needle 是否真锁得住 −3 命令的关键语义；4 类新负例是否真红

## 攻击型验收（opus）向量清单（逐向量实跑取证，BREACH/DEFENDED/WEAK 三级判定）

V1 needle 削除攻击：把 split-run §3.2 或 token-analyze-2/3 的契约 needle 短语改掉/删掉，docs_lint 或语义层测试必须红——逐条实际改、实际跑、恢复
V2 契约绕过：token-analyze-3.md 注入 "A5 seal v2" 或删 "G11"，验证 banned/required 两向都拦（docs_lint 层与 deploy-sync 语义层）
V3 fixture 负例真伪：test_repair_batch3_gates 的 −3 四类负例逐个人为破坏其断言目标，确认负例不是恒真测试
V4 编号/口径漂移残留：全库 rg 扫"两段旧口径"（−1/−2 不带 −3 的表述、A4–A5 收口、四入口、三命令/三文件字样）是否清零（历史叙述行与 archive/maintenance 除外，逐条裁决）
V5 半升级模拟：只 cp 部分命令文件到临时目录模拟部署漂移，deploy-sync 是否逐文件抓漂移
V6 快照双向：contract_ids_snapshot 删一条/加一条假 id，test_contract_routes 双向必红
V7 文档间矛盾狩猎：token-analyze-3.md 六步 vs split-run §3b vs SKILL.md 五入口行，找任何一处执行者按 A 文档做会违反 B 文档的情形
V8 越权边界：§3b 修错三分类的"最小机械修正"定义是否存在可被扩大解释为改数字/结论的措辞漏洞

裁定纪律：每个 BREACH 附可复现命令与输出；改动现场的攻击试验完成后必须恢复原状（git checkout 或还原编辑），报告里写明已恢复。
