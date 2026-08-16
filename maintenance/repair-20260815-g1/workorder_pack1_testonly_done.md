# AI-1 Pack 1 test-only 施工报告

日期：2026-08-15
范围：F-02、F-11、F-12 的 test-only 阶段
结论：新负向测试已在未修复生产代码上稳定变红；指定防退化与无关回归保持绿色。未修改任何生产文件、`commands-staging/` 或 `references/` 文件；未执行 git 操作。

## 改动文件

- `scripts/tests/test_repair_g1_audit_report.py`：新增 F-02 白盒、真实 CLI、传 report 哈希不符及 new-analysis None 四例。
- `scripts/tests/contract_manifest.json`：新增 CT-SEMANTIC-60、CT-BANNED-15。
- `scripts/tests/contract_ids_snapshot.json`：同步新增上述两个 ID。
- `scripts/tests/test_commands_deploy_sync.py`：从 manifest 单源读取 command 契约；对 staging/deployed 双侧叠加 required/banned 语义检查；manifest 缺失、损坏、空或无 command 契约均 FAIL；SHA 层保留原样。
- `scripts/tests/test_repair_batch3_gates.py`：补齐临时 manifest 注入、双侧同旧文本但 SHA 相等、deployed 单侧 banned、manifest 缺失不得 SKIP 的回归。
- `scripts/tests/test_batch2_p3_hardening.py`：新增 U+200B 中嵌、U+3164 尾嵌、14 个残余不可见码位逐个中嵌、大写与非 ASCII 变体。
- `scripts/tests/test_batch1_risk_flags.py`：新增 resolver 层内嵌零宽旗标必须传播 ValueError。
- `scripts/tests/test_repair_g1_risk_flags_pipeline.py`：新增 lint、LabelResolver eager load、analyze_holdings 无部分产物三层负向测试。
- `maintenance/repair-20260815-g1/workorder_pack1_testonly_done.md`：本报告。

## 红绿实况

| 命令/检查 | 状态 | 实况与红因定位 |
|---|---|---|
| `python3 scripts/tests/test_repair_g1_audit_report.py` | 预期红（rc=1） | 白盒在测试 :62 失败，`run(..., None, independent-audit)` 返回 `[]`；CLI 在 :74 失败，实况 rc=0 且打印 PASS。根因是生产 :769 仅在 `if report:` 时核验哈希，CLI 默认 independent-audit（:1273）仍把 None 传入 run（:1283）。同文件传 report 哈希不符例（:81）绿；new-analysis None 自有文案例（:89）绿。 |
| `python3 scripts/tests/docs_lint.py` | 预期红（rc=1） | manifest :153 的 required `a5-report-seal/v3` 缺失，:154 的 banned `A5 seal v2` 回捡；现役旧文本在 `commands-staging/token-analyze-2.md:17`。 |
| `python3 scripts/tests/test_commands_deploy_sync.py` | 预期红（rc=1） | staging 与 deployed 双侧均在语义层报 required 缺失（检查器 :98）和 banned 回捡（:103），共 4 项；没有 SHA 豁免。 |
| `python3 scripts/tests/test_repair_batch3_gates.py` | 绿（rc=0） | F-11 双侧同旧文本但 SHA 相等的主变异（:147）被语义层拒绝；deployed 单侧 banned 同时触发 SHA/语义两层（:158）；manifest 缺失不得借 SKIP（:190）；全文件其余 F04/F05/F07 回归均绿。 |
| `python3 scripts/tests/test_batch2_p3_hardening.py` | 预期红（rc=1） | 测试 :42 汇总显示 18 个非法向量全部被接受；生产 parser :29 只裁边界后直接返回原 token，没有正向白名单 fullmatch。 |
| `python3 scripts/tests/test_batch1_risk_flags.py` | 预期红（rc=1） | resolver 传播断言 :65 失败；`risk_partition` 在生产 :324 将脏 token 分类为 unknown，没有 ValueError。 |
| `python3 scripts/tests/test_repair_g1_risk_flags_pipeline.py` | 预期红（rc=1） | lint :77 红：扫完 2 行但只报“白名单外旗标”，未报 risk_flags 脏字符类错误（现生产 parse/canonical 在 validate_labels.py:93-94）；eager load :88 红：构造 resolver 不抛（labels_resolver.py:226 仅并表）；产物层 :137 红：analyze_holdings rc=0，并生成 4 个 JSON，构造 resolver 位于生产 :95，首个产物早至 :122。 |
| `python3 scripts/tests/test_audit_release_gate.py` | 绿（rc=0） | 既有独立审计发布闸全套回归通过。 |
| `python3 scripts/tests/test_contract_routes.py` | 绿（rc=0） | manifest/snapshot 双向对账通过，新增 ID 同步正确。 |

## Hunk 映射

| 文件/hunk | invariant | finding | 目的 | test owner |
|---|---|---|---|---|
| `test_repair_g1_audit_report.py` 全文件 | independent-audit 无报告实物不得 PASS | F-02 | 固化白盒入口、真实 CLI 入口及两条防退化例 | F-02 |
| `contract_manifest.json:153-154` | command A5 schema 必须为 v3 且旧串禁回捡 | F-11 | 建 required/banned 单源契约对 | F-11 |
| `contract_ids_snapshot.json:16,115` | manifest 与 ID 快照双向闭合 | F-11 | 登记 CT-BANNED-15/CT-SEMANTIC-60 | F-11 |
| `test_commands_deploy_sync.py:42-106` | command 语义检查不可空跑 | F-11 | 解析 manifest 并双侧验证 required/banned | F-11 |
| `test_commands_deploy_sync.py:135-136` | 语义层只能叠加于 SHA 严判 | F-11 | 在 SHA 循环后追加语义失败，不改 SHA 结果 | F-11 |
| `test_commands_deploy_sync.py:143-153` | manifest 不可用不得 SKIP | F-11 | 在非 canonical 缺部署目录分支前 fail-closed | F-11 |
| `test_repair_batch3_gates.py:80-109,139-164,181-192` | 参数注入夹具也必须执行单源语义与 manifest 门禁 | F-11 | 保持既有 F04 绿并加入 F-11 主变异/同族/失败分支 | F-11 |
| `test_batch2_p3_hardening.py:20-42` | token 必须 fullmatch `[a-z0-9-]+` | F-12 | 覆盖内嵌不可见、大写、非 ASCII 同族 | F-12 |
| `test_batch1_risk_flags.py:60-65` | resolver 不得把脏 flag 降级为 unknown | F-12 | 固化 ValueError 传播 | F-12 |
| `test_repair_g1_risk_flags_pipeline.py` 全文件 | 脏库无正式成功且无完成产物 | F-12 | 覆盖行级 lint、eager consumer、真实脚本产物边界 | F-12 |

未映射 hunk：0。

## 问题与自行决策

- `analyze_holdings.py` 没有 labels_dir 参数。为避免触碰禁改的 `references/`，测试在临时目录复制生产脚本、resolver、parser 的原始字节，借其相对路径注入脏标签库；因此没有降级为仅测 resolver，且所有运行产物只落在临时目录。
- 新语义要求 manifest 读不到或为空必须 FAIL，与旧 F04“非 canonical 且部署目录缺失即可 SKIP”夹具冲突。已把旧夹具收紧为：manifest 缺失先 FAIL；manifest 有效而仅部署目录缺失时仍保留原 canonical/non-canonical 行为。
- 本阶段刻意不改 `commands-staging/token-analyze-2.md:17`，所以 docs_lint 与真实 deploy-sync 的语义红是本工单要求的先红证据，不是施工遗漏。
- 未跑 `run_all.py`：当前候选按设计包含多项预期红；已逐个运行全部涉及文件及用户指定的两个无关绿测试。
