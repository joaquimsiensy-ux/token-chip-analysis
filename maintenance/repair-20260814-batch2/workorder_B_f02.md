# 工单 B（F-02）：对抗复核结构化最低要求（adversarial-review/v2→v3）

> 批 2 第二单，工单 A 验收合格后开工。总计划见 plan.md「三、F-02」节。
> 施工纪律同工单 A：禁 git 写命令；完成后写 `workorder_B_done.md`（改动清单＋红→绿双跑证据＋六视角①②自审＋发现未修节）。

## 0. 背景一句话

对抗复核 runner 只验 exit 0＋非空文件（2 字节 "ok" 即过），发布闸只验角色名子串＋blocker 自报 resolved——复核可空壳。要求产物携带机器可验的客观结构（复核了哪些结论、每条裁决与证据），不判断观点对错。

## 1. 不变量

对抗复核产物必须结构化绑定权威 claims 表：每条结论至少被一路复核（并集覆盖），每条裁决携带非空证据，registry 内容以 sha 绑定（防 id 不变正文被换）；runner/消费侧两侧等深，空洞文本任何一侧都过不去。

## 2. 同族清单

```
rg -ln "adversarial-review" --glob '!maintenance/**' --glob '!archive/**' --glob '!blind-reviews/**'
rg -ln "adversarial_review_runner|check_adversarial|ADVERSARIAL_RUNNERS" --glob '!maintenance/**'
```
已知命中：`scripts/report/adversarial_review_runner.py`（runner）、`scripts/report/shared_release_receipt.py`（validate_sources :532-553＋import validate_review_receipt :17＋ADVERSARIAL_RUNNERS :43＋逐 review 调用 :545）、`scripts/report/audit_release_gate.py`（check_adversarial :821-839＋调用 :1122）、`scripts/tests/invariant_manifest.json:134,350,814,960`、测试 `test_audit_release_gate.py`／`test_repair_batch_d.py`／`test_round4b_provenance.py`、文档 `references/independent-audit-protocol.md:156-158`＋`references/analyze-workflow.md` A4 章。rg 出新命中一并处理。

## 3. 修改内容

1. 聚合 schema 升 `adversarial-review/v3`，新增必填 `claim_registry: {path,size,sha256,schema}` 指向案内 `a4_claims.json`（执行态权威表——independent-audit 的 claim_registry.json↔a4_claims.json 对账已由 a4_gate finalize 强制，本单不重做，两 profile 统一绑 a4_claims.json）。消费侧独立重算 sha 比对。
2. 每路 claim-review artifact（role=entity_attribution_skeptic 等）从自由文本改为结构化 JSON：
   `{"schema":"adversarial-review-artifact/v1", "role":..., "registry_sha256":..., "results":[{"claim_id":..., "verdict":"CONFIRMED|WEAKENED|REFUTED", "evidence":[非空字符串数组], "alternative_explanations":[...]}]}`。
   artifact 的 registry_sha256/role 必须与其 execution receipt 及聚合层一致（防撕裂）。
3. completeness_critic 的 artifact 为全局检查件：`{"schema":"adversarial-review-artifact/v1", "role":"completeness_critic", "registry_sha256":..., "findings":[...], "non_covered":[...]}`（findings 数组必在场可为空、non_covered 必在场——漏报声明），不逐条投票。
4. **覆盖语义＝并集覆盖**：全部 claim-review artifacts 的 claim_id 并集 ⊇ registry 全部 claim id；artifact 不得含 registry 外的 claim_id（多也不行）；claim_id 不得重复（同一 artifact 内）。
5. runner `run_review`：staging 落盘后校验 artifact 结构（按 role 分型校验），不合格→ValueError exit 2 且清理 staging 零残留。
6. 新增 finalize 聚合子命令（挂 adversarial_review_runner.py 的 CLI）：读 a4_claims.json＋各 execution receipt＋artifacts＋blockers 输入，校验后原子产出 v3 聚合件 `adversarial_review.json`（tmp+fsync+os.replace，仿既有 receipt 落盘模式）；任何输入缺失/验不过→exit 2 不落半成品。
7. 消费侧：`validate_sources` 等深重验（结构/并集覆盖/registry sha/撕裂检查）；`check_adversarial` 升 v3（schema 串＋claim_registry 在场＋blocking_findings 结构）；三处 artifact 校验逻辑抽公共纯函数（建议放 runner 模块，shared/audit import），禁三份手抄。
8. `blocking_findings` 元素：`{id 非空且聚合内唯一, resolved:bool}` 必填；resolved=true 时 `resolution` 非空。
9. 存量：v2 fail-closed 拒绝（错误信息指明须按 v3 重跑对抗复核）。CHANGELOG 记录存量影响：AKE/B2/MOG/TAG 至少四案 v2 在盘，不重跑发布闸不受影响，重发布须重做复核。
10. 文档：independent-audit-protocol.md §156-158 命令段更新（含 finalize 聚合器用法）；analyze-workflow.md A4 章补一句 v3 产物要求；invariant_manifest 相关条目同步。

## 4. 三件套测试（先红后绿）

a. 原反例：entrypoint 只写 2 字节 "ok"（blind-reviews/r9/45bf8f3/round-a-sixlens.md 存档反例）→ 当前 runner 放行（红证据双跑记录），修后 runner 拒。
b. 同族变体：
- verdict 非法枚举；evidence 为 `[]`／`[""]`／`"ok"` 字符串（类型错）；
- 并集缺一条 claim；artifact 多一条 registry 外 claim；同 artifact 重复 claim_id；
- registry_sha256 与 execution receipt 撕裂；runner 完成后改写 a4_claims.json → 消费侧拒；
- blocker 空 id／聚合内重复 id／resolved:true 无 resolution；
- v2 旧收据 → 拒且信息含重跑指引。
c. 失败分支：
- artifact JSON 损坏 → runner exit 2 且 staging/正式位零残留（列 ls 证据）；
- finalize 聚合器：缺 execution receipt／缺 artifact／registry 不在场 → 逐条 exit 2 零半成品。
d. 绿例防误伤：
- 合规两角色（skeptic 结构化 results 全覆盖＋critic 全局件）→ runner/finalize/消费侧全链绿；
- 受影响存量夹具全面排查升级：`test_audit_release_gate.py`（build_case 及其共享者）、`test_repair_batch_d.py`（Solana 同构 build）、`test_round4b_provenance.py`——entrypoint 全部改产合规 JSON，逐一跑绿；
- `python3 scripts/tests/run_all.py` 全绿。

## 5. 六视角①②自审（完工摘要必填）

①每个新字段的信任根（registry sha 是否消费侧独立重算？覆盖集合是否从 artifact 实物重建而非聚合层自报？）；②每条失败路径 fail-closed＋staging/tmp 零残留。

## 6. 归因预判

历史漏检（runner 自 f45c04f 引入即无内容校验）。本单闭合；范围增项（finalize 聚合器）按计划已获批。

## 7. 验收口径

裁判独立跑：原反例复现（修后拒）＋三个受影响测试文件各自 rc=0＋run_all 全绿＋git diff 逐文件审。
