# 批 B 工单｜外围文档指针批：刀 1 公告＋归属注（v6.50.0 工程）

> 执行者：codex（workspace-write）。工作目录：`/Users/uravvv/.claude/worktrees/tca-splitrun3`。前置：批 A 已验收。
> 白名单外文件被改动＝违规。**不 commit**。【定稿文本】逐字落盘；【改动要点】按要点成文保持原文件风格。

## 白名单（5 个文件）

1. `references/context-discipline.md`
2. `references/analyze-workflow.md`
3. `references/playbook-entity-cluster-tiering.md`
4. `references/report-template.md`
5. `references/research-workflows.md`

## 五栏

**① 不变量**：(a) analyze-workflow.md 27 条契约 needle 与 4 组硬编码文本断言全部存活（本批只加句不改句）；(b) tiering 7 条 needle 存活；(c) context-discipline 改后条目编号全册无重号；(d) 刀 1 公告成为外包清单唯一权威源——其余四文件相关表述全部为指针。
**② 同族清单**（施工前跑，记录进 done）：
```
rg -n "opus" references/context-discipline.md references/research-workflows.md   # 外包档位表述全部出现点
rg -n "^\d+\." references/context-discipline.md                                   # 编号现状（两个 6. 并存 bug）
rg -n "报警才人工深挖|人工深挖" references/                                        # ET-1 深挖表述出现面
rg -n "split-run −1/−2|−1/−2" references/context-discipline.md                    # 三段化同步点
```
**③ 三件套（文档适配）**：(a) 编号修复先证现状（rg 记录两个 6. 并存）后证修复（rg 全册编号唯一）；(b) 口径漂移扫描三条（验收命令）作同族变体检验；(c) docs_lint --all 全绿。
**④ 新建条文自审**：刀 1 公告每一项是否写清"外包什么/留什么"，无一项把裁决字段划给子代理。
**⑤ 归因预判**：新引入；风险集中在编号改一半与 needle 误伤。

---

## 施工任务

### T1｜`references/context-discipline.md` 刀 1 重写＋编号修复

**T1.1（:12 机械档清单替换）**——原"外包清单·机械档（opus+high）"整条替换为【定稿文本，逐字落盘】：

```markdown
2. **外包清单·机械档（opus+high）——本清单是 −2 会话机械外包的唯一权威源（v6.50.0 公告）**：
   ①候选覆盖自检（钉 opus——防与 −1 主轨 GPT-5.6 同族自验；主线看差异清单＋输入哈希＋各通道计数，不是只看一句结论）；
   ②聚类证据卡片装配（全量包纪律：必含拒绝边/孤立点/公共设施反证/完整邻域，禁"挑最相关"；主线保留按需查原始数据权）；
   ③ET-2 成员完整性扫描执行（展开规则/深度主线先定死；子代理只报新增候选＋证据路径，不收编）；
   ④wave/flow/分布候选证据包（三级产物边界：脚本收据→子代理全量证据包→裁决台账判断字段【verdict/accepted_members/excluded_members.reason/evidence/linked_entity_id】主线亲填后跑 validator）；
   ⑤entity_source_trace 溯源执行＋新支路枚举（支路定性、翻转裁决留主线；用户裁决类绝不代行）；
   ⑥EF-1/EF-2 数值计算层（LP/vault/份额可赎回量、静置区间统计；evidence_grade 与 strict/expanded/excluded 及 decision_reason 是实体边界裁决，主线亲写）；
   ⑦阵营演变重放执行＋断言检查（主线先锁名册/阵营映射/分母）；
   ⑧state_source 装配＋state_from_facts.py 编译执行（analysis-state.json 是编译产物，不存在"起草"）；
   ⑨状态评估统计包（固定口径全列：内部互转/DEX/CEX/LP 分列、毛净流分列，防单一数字诱导定性）；
   ⑩A4 材料脚本执行（cluster_sensitivity/惯犯揭盲/本地反例）；claims 由主线先列目录，子代理只做 ID 与 schema 转写＋配数据路径与哈希；
   ⑪A4.5 执行侧脚本（final 分布扫描/五判据检查/轮次绑定）；
   ⑫重点实体 dossier 装配（模板唯一权威源＝research-workflows §二b，此处只指针）；
   ⑬判级数值工作表（联合峰值/日终 L1/L2 上界/strict-expanded 双边界/距门槛差值；判级本身留主线）；
   ⑭A4 翻案传播审计（裁决吸收后机械核查 findings/facts/state/claims/阵营序列/图表输入是否同步，列残留旧数；修改裁决留主线）。
   历史清单项（标准脚本跑批与重试循环/对账四查执行侧/标签库批量 lookup/大户批量排查/图表脚本执行/数据完整性验证/逐地址溯源 fan-out）继续有效，其中分段模式下已归 −1 的项在 −1 会话内自然完成。
2b. **外包纪律（与清单同权威）**：sealed/ 禁读令与 CHIP_BLIND_SERIAL 盲化对子代理同样生效（外包 prompt 必带）；装配材料的子代理线程不得充当 A4 怀疑者；子代理只写非权威中间产物，权威台账/seal/freeze 由主线亲填亲跑；零结果必附输入哈希＋行数＋区间自证；能由脚本生成的字段一律脚本产、禁模型手抄转录，进结论链数字主线抽查还原；−2 交付时自查申报本公告遵守情况（挂 A5 交付自查，与 sealed 自查申报同款形态）。
```

**T1.2（:13/:14 判断档与禁区）**：内容不变；若 T1.1 引入 2b 导致条目结构变化，保持 3.（判断档）4.（禁止外包）原文逐字不动。

**T1.3（:16 第 6 条三段化）**：改为"**分段执行（split-run.md）＝本刀机械/判断分工的会话级形态**：−1 机械段整会话交 GPT-5.6（codex 主轨）/Opus（备轨），−2 判断段主力模型同目录冷启动（会话内机械环节按本节公告外包），−3 装配段新开 Opus 会话消费装配工单——边界/交接契约/开工序以该手册为唯一权威源。"

**T1.4（编号修复）**：刀 2 现有条目 6–10 重排为 7–11，刀 3 条目 11–13 重排为 12–14；改后 `rg -n "^\d+\." references/context-discipline.md` 全册编号唯一递增（2b 除外）。

**T1.5（:21 刀 2 阅读条）**："split-run −1/−2 先读 split-run.md"改"split-run −1/−2/−3 先读 split-run.md"。

⚠ 本文件在 docs_lint execution_docs 禁词扫描内：不得出现"读 CHANGELOG…版本号"类句式。

### T2｜`references/analyze-workflow.md` 两处纯增句（不改任何既有句）

- :133-135「判级（含 ET-1）」段内"报警才人工深挖"句后增：`分段执行时报警地址证据采集归 −1（只记观察事实，split-run §1.3），人工深挖定性归 −2（§1.4）。`
- :176「## A5 报告」标题下首段前增一句：`分段执行时本阶段的装配执行归 −3（split-run §3b）；−2 收口于报告正文＋装配工单。`

### T3｜`references/playbook-entity-cluster-tiering.md` :44 一处

ET-1 定义句"**ET-1 其他大户批量排查**＝label_lookup＋惯犯库＋行为指纹＋funder 批量溯源全部跑，报警者再人工深挖"改为"**ET-1 其他大户批量排查**＝label_lookup＋惯犯库＋行为指纹＋funder 批量溯源全部跑；报警者先做证据采集（资金源/gas/互转/对手方，观察事实层，分段模式归 −1），再人工深挖定性（判断层，分段模式归 −2）"。本行外一字不动。

### T4｜`references/report-template.md` :269 一处

「## 交付前 checklist」标题下增一句：`分段模式下本清单的渲染/seal/HTML 项由 −3 执行、正文项由 −2 执行，归属见 split-run §3b。`

### T5｜`references/research-workflows.md` §二b 钉法改指针

:147 标题行与 :149 定位段中的"模型 opus + effort high"与"（成本纪律刀 1 外包禁区不变）"表述保留语义但改为指针化：模型钉法句改为"模型档位与禁止外包边界的唯一权威源＝context-discipline 刀 1（机械档 opus+high；Agent 直调只能钉 model、要钉 effort 走 Workflow 派），本节不另存副本"。模板本体（第 1/2/3/4 节输入输出）一字不动——它仍是 dossier 模板的唯一权威源。

---

## 验收命令

```
cd /Users/uravvv/.claude/worktrees/tca-splitrun3
python3 scripts/tests/docs_lint.py --all
python3 scripts/tests/test_contract_routes.py
rg -n "^\d+\." references/context-discipline.md            # 编号唯一递增（含 2b 特例）
rg -n "报警才人工深挖" references/                          # 只允许 analyze-workflow/tiering 改后表述，不许旧句独存
rg -n "A3 判断层＋A4–A5" SKILL.md references/ commands-staging/ && echo "旧口径残留!" || echo "旧口径清零"
rg -n "effort.?high" references/research-workflows.md      # 应只剩指针句一处
python3 scripts/tests/test_repair_batch_a.py && python3 scripts/tests/test_g3_docs_guards.py   # analyze-workflow 硬编码断言存活
```

## 完成标准

五文件改动落盘；验收全绿；done 报告 `batchB_done.md`（含编号修复前后 rg 对照）。**不 commit。**
