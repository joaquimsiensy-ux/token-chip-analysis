# 复核 W1 r1: 退回

总判定：常量化方向、17 处字面量清单和 9.1.0 档位基本成立；认领部分尚不能按本工单安全落地。阻断项是：**可伪造的前代归属、读取旧台账会写回、header-only 目标无法按指定方法发布、复验缺少上下文且遗漏恢复分支，以及新增依赖会破坏纯包导入。**

目标是保住已完成的采集证据，避免 producer 升版导致重拉。支持方案的最强理由是：显式版本 0 请求成功获得的完整区块，可以继续作为原请求的证据。反对当前方案的最强理由是：公开可计算的 plan_digest 和登记过的脚本哈希，不能证明某份文件确由该脚本、该案、该参考源产生。真正的分歧是“可信旧证据的结构迁移”，还是“面对可篡改文件也能证明历史来源”；v1 将两者混用了。

完整报告已打印到 stdout。全程未修改文件、未 commit，未运行会创建夹具的测试或 run_all.py；起止工作区均干净，分支为 fix/solana-txv1。未读取 `~/.codex`、`~/Documents`、`~/Desktop`。以下行号均为本次基线。

**1. 锚点与断言实证——退回：字面量清单通过，部分断言和范围表述需修订。**

grep 与 AST 均确认：**13 个文件、17 处数字字面量，值全部为 0**。共同锚文本为 `"maxSupportedTransactionVersion": 0`。

| 文件 | 实际行号 | 判定 |
|---|---|---|
| scripts/lib/solana_exact_validate.py | 1214 | 通过 |
| scripts/solana/sqd_gap_repair.py | 632 | 通过 |
| scripts/lib/solana_observation.py | 270 | 通过 |
| scripts/solana/probe_window_moves.py | 121 | 通过 |
| scripts/solana/fast_probe_tops.py | 54 | 通过 |
| scripts/solana/decode_txs.py | 39 | 通过 |
| scripts/solana/decode_txs_v2.py | 295、340 | 通过 |
| scripts/solana/whale_deep.py | 64、154 | 通过 |
| scripts/solana/audit_closed_accounts.py | 230、419、482 | 通过 |
| scripts/solana/gas_origin.py | 81 | 通过 |
| scripts/solana/stake_decode.py | 96 | 通过 |
| scripts/solana/probe_escrows.py | 150 | 通过 |
| scripts/solana/trace_wallet.py | 76 | 通过 |

“已导入/已有路径”断言：

- **通过**：sqd_gap_repair.py:20「sys.path.insert(0, str(LIB))」、:27「from solana_exact_validate import」、:32「canonical_json, compute_gid, compute_plan_digest」准确。
- **通过**：solana_observation.py:19「from solana_attested_session import」准确。
- **通过**：lib 路径锚「sys.path.insert」分别为 probe_window_moves.py:25、fast_probe_tops.py:15、decode_txs_v2.py:24、whale_deep.py:22、audit_closed_accounts.py:40、gas_origin.py:18、stake_decode.py:22、probe_escrows.py:20、trace_wallet.py:14。
- **通过**：decode_txs.py:8 已 import sys，:9 为 Path，:10 为 requests，:11 导入 decode_txs_v2；本文件确无显式 lib 路径。
- **退回**：solana_attested_session.py:10 确为 endpoint_identity 导入，但“只 import endpoint_identity”字面上不成立：:5–8 有标准库，:13 可选导入 certifi，:38 在导入时建立 SSL context。应改成“唯一仓库内依赖是 endpoint_identity”；不能据此视为无副作用的纯常量模块。
- **通过**：producer_history.py:204–233 四条均引用 commit 4c5cd578…，对应 sha256 为 25f04ff1…，均 ACTIVE。当前 sqd_gap_repair.py 实算哈希与工单完整值一致。:246「historical_producer_hashes」实行 **REVOKED 优先**，不能简化为“曾登记过”。

其余锚点：

- **通过**：sqd_repair_core.py:59–82「compute_plan_digest」；sqd_gap_repair.py:892「reference getBlock failed」、:627–633「_rpc_body」、:716–757「load_resume_slots」、:724–726 header 比较、:750–751 params 比较、:961「_live_payloads」、:1273–1276 创建目录、:1401 header 比较、:1544「--resume」。
- **通过**：solana_exact_validate.py:26–29 包导入回退、:1208–1216 请求摘要模板、:1297–1313 header/digest 检查、:1533 params 摘要检查。
- **通过**：invariant_scan.py:337「bare_rpc_pool_errors」；test_batch4_invariant_guards.py:25「test_bare_rpc_pool_injection」。
- **退回**：E27(a) 从 test_sqd_gap_repair.py:712 开始，完整段落到 **:768**「assert interrupted_pointer["gid"] == uninterrupted_pointer["gid"]」结束；:752 只是中段。“E27(a) 之后”应指 :768 之后。
- **退回**：守卫实际汇总在 invariant_scan.py:1268「validate_manifest」、:1330「errors += bare_rpc_pool_errors()」；main 在 :1403 调用它。应要求接入这条汇总路径。
- **通过**：scan-schemas.md:998–1023、:1021 resume 不变量；data-pipeline-solana-capture.md:198 第 2 条；pyproject.toml:15、SKILL.md:23 均准确。
- **未独立证实**：背景中的原案 slot、交易数量、完成进度、旧 pending 实物，以及 §6 案内脚本行号不在本仓库复核范围，只能标为调度方提供的背景。

修订建议：将“17 处”限定为**施工前基线**。去重模板并新增守卫、测试后，全文 grep 命中数不应继续要求等于 17。

**2. 认领机制安全性——退回：五步只能检查部分自洽关系，不能证明前代来源。**

（a）**plan_digest 不等于完整 plan 身份。**

sqd_repair_core.py:65「material =」实际绑定：

- base.edge_sha256、base.meta_sha256；
- coverage.probe_id、coverage.map_sha256；
- 去重排序后的 candidate_slots；
- mode；
- reference.kind、reference.endpoint_fingerprint；
- producer.sha256。

:82 将摘要截为 16 位 hex。

在旧 header 真实且未替换的前提下，普通 base、coverage、候选集合或参考源指纹差异会导致不匹配。跨 mint 通常也会因 base meta、coverage 内的 mint 导致哈希变化，不能说 mint 完全没有间接绑定。

但它不绑定 case_root、producer.path、reference.source、plan_candidates 的 coverage/beta 分组，也没有保存完整旧 plan。内存验证确认：改变这些非物料字段不改变摘要；改变 base 哈希或 endpoint_fingerprint 则改变摘要。

最小补法：保留 compute_plan_digest 不动，将契约改成“**冻结摘要物料一致**”，另显式检查目录归属和其他必要约束。若坚持“完整 plan 一致”，必须取得完整旧 plan；旧 header 做不到。

（b）**伪造旧 header 不需要破解哈希。**

攻击者同样可以把当前 plan 的 producer 换成公开 ACTIVE sha，计算前代 digest，改 header、改目录名，再放入自洽的行和证据。登记表证明的是脚本哈希可接受，不是文件的生产签名。

sqd_gap_repair.py:751–755 只检查 params、行指纹、两个 slot，以及 ref.raw_response_sha256 与行 result_sha256 相等。:1178–1190 保存的是投影证据和自报原始摘要，无法从该投影重新计算完整响应哈希。

因此：

- 修改 missing_detail 而保留 raw_response_sha256，不会被这一层发现。
- 同时修改行 result_sha256 和 ref.raw_response_sha256，仍能通过相等检查。
- 内存调用原 load_resume_slots，伪造证据字段及候选集外 slot=999 均能进入 completed。

这证明续跑检查缺口，**不等于声称所有伪造都能通过最终全部深验**。

最小补法：以既有、独立可信的审计快照绑定旧台账和证据文件摘要。若没有这种锚点，应将承诺限定为“可信输入的结构一致性迁移”。在同一可篡改目录新放一个自报哈希，不能证明历史来源。

（c）**跨案、跨 mint、跨参考源和重复认领仍有缺口。**

- 目录名校验不限制同案同 mint。字节相同的案卷克隆也能通过摘要。应要求 old 与 pending 位于同一规范化 repair parent，拒绝符号链接和 old==pending。
- 行指纹检查能拒绝未重标的不同来源行，但证据没有独立来源身份；重标 header/行仍不能证明真实来源。
- completed 未限制在计划候选集。应检查采纳 slot 属于计划并满足确定性候选顺序，保留 seq 连续与 slot 唯一检查。
- “目标已有数据行即拒”不能完整定义重复认领：header 已带 adopted、数据行为零的状态仍被允许。应拒绝已有 adopted，或明确定义按相同来源摘要幂等恢复。
- 旧 header 自身带 adopted 时，没有验证继承链。最省方案是只接受**未被认领过的直接前代**。

（d）**旧源不变、零迁移和指定发布方法互相冲突。**

- sqd_gap_repair.py:682「_read_ledger_prefix」会在 :700–705 规范化重写或截断尾行。用于 old 会改旧台账，即使随后认领失败。应拆出纯读取解析，或增加明确的只读模式。
- :204「_publish_bytes_exclusive」在 :207–210 遇到已有不同内容即抛 FileExistsError。允许“只有 header”的目标，再用它发布“新 header+行”必失败。最省修订是要求目标 ledger 不存在；否则需受锁保护的原子替换。
- 逐 slot link/copy，后续发现目标冲突时，之前的文件已迁入，违反零迁移。应完整预验后再落盘；I/O 中断则用暂存提交，或明确为“无有效台账发布、可幂等恢复”。
- os.link 共享 inode，旧证据后续原地修改会改变新产物。最小方案是复制并复核摘要；保留硬链接需要真实的源不可变保证。
- :229–230「_jsonl_bytes」会重新 canonical_json 编码。应区分“JSON 字段值不改”与“原始行字节不改”。

（e）**复验接口缺少必要上下文。**

_verify_adopted_record(header, plan) 没有行数，无法检查 rows 上界；现有 load_resume_slots(pending, header) 没有 plan，无法重算前代摘要。仅记录 rows=n，也不能绑定具体前 n 行内容。

最小补法：明确传入 plan 与数据行/计数；统一验证 adopted 类型、精确键集、sha/digest 格式、正整数 rows（排除 bool）、source/ts 类型和认领前缀。前代 sha 必须与重算命中的 sha 对应，不能分别验证两个互不关联的事实。

另有遗漏：sqd_gap_repair.py:1234–1269「resume_published_generation」成功后提前返回，绕过 :1401，必须补复验。source 所需 case_root 也不在拟定 helper 参数内，应明确取得方式。

**3. 版本等价断言——退回绝对“响应字节相同”的措辞；通过当前显式 0/1 接受集合的方向。**

Agave 官方实现 validate_version 返回**交易实际版本**：

- 省略 maxSupportedTransactionVersion：legacy 可以省略 version。
- 显式 Some(0)、Some(1)：legacy 都回显 `"legacy"`，v0 都回显 `0`。
- v1：max=0 时错误，max≥1 时回显 `1`。

因此，不能把“省略参数”的边界误套到“显式 0 与显式 1”。[Agave 官方实现](https://raw.githubusercontent.com/anza-xyz/agave/master/transaction-status/src/lib.rs)

官方文档也区分 `"legacy"`、数字和字段省略。[Solana JSON 结构](https://solana.com/docs/rpc/json-structures)

同一实现、同一区块及元数据、其他参数相同且完整成功返回时，提高显式版本上限不会因该字段本身改变旧交易的编码结果。但 RPC 不承诺跨请求、节点版本或供应商的 HTTP 响应逐字节一致。

而 sqd_gap_repair.py:893–902「raw = json.dumps(block, sort_keys=True, ...)」哈希的是**解析后的 block 重序列化结果**，不是 HTTP 原始响应。

修订建议：

- 接受当前显式 v=0、v=1 的同模板历史成功证据。
- 排除省略/null 参数、失败或不完整响应、其他请求字段变化。
- 保留旧请求自己的 params_digest 和结果摘要，不将其改写成新请求。
- 删除“未来任意 0..MAX 永久字节等价”的免审承诺。

**4. 下游消费者——退回：没有额外 header 键集拒收器，但有接口、导入和深验遗漏。**

solana_exact_validate.py 全部 rpc_ledger 消费点已核对：

| 位置与锚 | 实际检查 |
|---|---|
| :1248–1251「_repair_ref」 | 文件引用 |
| :1288–1298「_jsonl_header_count」 | header、行数、schema |
| :1305–1313「plan_digest」 | 代际摘要一致 |
| :1317–1347「_jsonl_data」 | 数据行键集、字段、seq、唯一 slot、requests |
| :1530–1536「ledger_row」 | params 与结果摘要 |
| :1541–1543「ledger_data_count」 | 请求数下界 |

没有 ledger header 精确键集断言。改 :1533 后，未发现另一个隐藏的单版本 params 摘要检查。

sqd_cache_identity.py:129–136「if set(bundle) != required」限制的是 **bundle 顶层**；:149–159 校验 ledger 文件 size/sha；:167–169 委托深验。replay_edges.py:432–434 同样走 deep=True。因此无需为 adopted 修改这两个文件，但必须正常更新 ledger 文件引用。

遗漏及补法：

1. **参考源等式缺失。** exact:1328–1331 只检查行指纹格式，:1338–1341 还将它从 ledger_by_slot 丢弃。应补 header.reference、每行 endpoint_fingerprint 与 bundle.reference 的对应等式。
2. **“深验无 plan 所以不能重算”不成立。** bundle.base、coverage.map.sha256/probe_id、resolution.plan_candidates、mode/reference/producer 已足够重建摘要物料，见 sqd_gap_repair.py:1341–1347、:1430–1452。应独立重算当前/前代摘要；只检查登记 sha 与 16hex，会放过任意不相等的假前代 digest。
3. **遗漏已发布代恢复分支。** :1234 提前恢复路径也应复验 adopted。
4. **纯包导入实证失败。** 隔离进程中，当前 `import scripts.lib.solana_exact_validate` 成功；`import scripts.lib.solana_attested_session` 报 `No module named 'endpoint_identity'`。原因是 session:10 只有绝对导入。validator 的外层回退不能解决内部依赖，应给 session 的 endpoint_identity 导入补回退。
5. **batch8 接口兼容。** test_batch8_repair_scale.py:171「direct_stream」使用缺字段 plan，:175 的 digest 是 64 位占位值；:203–204 仍按两参数调用 load_resume_slots。不能对所有无 adopted 台账强制完整 plan 或新增 16hex 约束。建议可选 plan 上下文，仅 adopted 路径要求完整物料。
6. **batch7 原样测试可保留。** test_batch7_validator_coverage_gaps.py:58–65 复用请求夹具，:84 调深验，未发现独立 header 键集或单版本常量断言；但它不会覆盖新认领漏洞。

**5. 最小化原则——通过总体范围，退回不必要增量和省略过头的承诺。**

可以进一步省：

- 不新建通用迁移框架或常量模块；现落点可保留，但修包导入。
- 守卫注入照 test_batch4_invariant_guards.py:27–32 写极小源码，不必复制整份生产脚本。
- references 只改现有契约表和不变量；capture.md 无需重复常量完整导入路径；SKILL.md 仅改版本标记。
- 将目标收窄为 ledger 不存在、来源为同 parent 的未认领直接前代，可减少大量边界分支。
- adopted 应写“父对象可选，存在时五个子字段全部必填”，不能五项均笼统写“否”。

不能省：

- 源只读、前缀和指纹检查、迁入前预验、已发布代恢复复验及篡改负测。
- 至少证明实际请求发送 1，并覆盖 v1/transactionConfig 输入；AST 无字面量不能证明行为正确。
- producer 依赖身份说明。sqd_gap_repair.py:607–608 只哈希本脚本。未来仅改共享常量或 validator 请求模板，producer.sha256/plan_digest **不会变化**。工单 :29“升版本只改这里 + 登记 + CHANGELOG”不完整。当前 W1 会改 producer，当前换代成立；未来仍需明确触发 producer 身份更新。

**6. 测试可行性——通过夹具复用；退回 FAKE_SHA 和计划取得方式的现写法。**

v1 原列“一个正向、五个入口负向、一个深验负向”，复用 E27(a) 变量及一个重置 helper，可组织在约 **100–120 行**新增代码内。这是静态实现估算，本次未落盘编写或运行；补齐安全向量后，不应继续硬压 120 行。

直接取 plan 无需反推：

```python
fp = repair.reference_endpoint_identity("fixture://helius")["sha256"]
plan, _, _ = repair._plan(case, MINT, reference_fingerprint=fp)
previous = copy.deepcopy(plan)
previous["producer"]["sha256"] = predecessor_sha
previous["plan_digest"] = repair.compute_plan_digest(previous)
```

锚：sqd_gap_repair.py:584「def _plan」、:623 返回三元组；CLI fixture 同源设置在 :1601、:1607。普通 E27(d) 使用默认空 beta_slots 即可。header 本来就没有 base/coverage/candidates，不能反推完整 plan。

更省的等价手法：

- **正向采用真实 ACTIVE 前代 25f04ff1…**。仅 monkeypatch repair.historical_producer_hashes，不会影响 exact:27/:29 自己导入的函数；顶层 exact 和 scripts.lib.exact 还可能是两个模块实例。按原文使用 FAKE_SHA，迁入后深验会拒绝。
- 从 E27(a) 模板复制隔离 case，留一行后改为前代目录/header及版本 0 行摘要，续跑夹具仅供第二个 slot。现成函数为 test_sqd_gap_repair.py:165「build_batch3b_case」、:229「repair_slot_responses」、:391「write_repair_fixture」。
- 深验负向修改 adopted 后，同步更新 bundle.rpc_ledger 的 size/sha256，再断言 adopted 专属理由，避免混入普通文件哈希失败。
- direct_stream 位于 test_batch8_repair_scale.py:171，只适合流式跳过和顺序检查：plan 缺字段、不产正式 bundle，不能替代 E2E。它在 :24 已导入 test_sqd_gap_repair，反向导入还可能制造双模块/循环依赖。
- v2 应补：同内容跨案、真实 ACTIVE sha 配假 digest、采纳行与证据同步篡改、已有 adopted、首行正确而后续错误、header-only 目标、旧台账残缺尾行保持原字节。

**7. 版本号——通过：9.1.0 符合两维规则。**

references/retrospective.md:139 的锚为“次版本=向后兼容的新能力、新公开接口或持久化契约扩展”。新增 `--adopt-pending` 和可选 header.adopted 属于次版本，不涉及 :140 的 labels 数据版本。

若只有常量化修复，修订号更适合；本工单包含新能力，9.1.0 有依据。前提是旧无 adopted 台账和版本 0 bundle 仍兼容。

当前 VERSION:1、pyproject.toml:15、SKILL.md:23 均为 9.0.3；CHANGELOG.md:13/100 为当前索引/正文，未发现已有 9.1.0。

修订建议：补跑 test_version_consistency.py:12–23，changelog_lint 不能替代版本元数据一致性检查。

**8. 回归面——退回：0.7 遗漏直接依赖和版本检查。**

以下测试均已挂载 run_all.py，无需修改套件登记：

| 影响路径、证据锚 | 0.7 遗漏的相关测试 |
|---|---|
| session：test_r9_solana_attested_session.py:14；test_r9_batch2_solana_sqd_adapter.py:12；run_all.py:24–27 | test_r9_solana_attested_session.py、test_r9_batch2_solana_sqd_adapter.py；间接的 test_r9_batch2_attestation_adapters.py |
| exact/coverage：test_sqd_coverage_probe.py:20、test_batch2d_stream_tail.py:17、test_f03_sharedmap_reuse.py:20；run_all.py:158–160 | test_sqd_coverage_probe.py、test_batch2d_stream_tail.py、test_f03_sharedmap_reuse.py |
| repair/深验：test_batch3c_census_fields.py:12、test_reconcile_v4_receipt.py:23/32、test_batch18_review_digest.py:66；run_all.py:162–165、:204 | test_batch3c_census_fields.py、test_reconcile_v4_receipt.py、test_batch18_review_digest.py；发布链 test_recon_fifth_check.py |
| 采集及完整 Solana 路径：test_sqd_collector_meta_v4.py:32、test_batch3_solana_vertical_slice.py:23–24；run_all.py:21、:65 | test_sqd_collector_meta_v4.py、test_sqd_consumer_v4.py、test_batch3_solana_vertical_slice.py |
| observation/冻结/发布：test_batch11_frozen_bundle_binding.py:18–19、test_r9_batch3_preflight.py:13、test_r9_batch3_release_guards.py:17；run_all.py:30–31、:174 | test_batch11_frozen_bundle_binding.py、test_r9_batch3_preflight.py、test_r9_batch3_release_guards.py |
| 工具脚本及登记：test_repair_batch1.py:529/:701–710、test_repair_batch_d.py:167/858/915/1246、test_anchor_plan_v3.py:375；run_all.py:97/100/150 | test_repair_batch1.py、test_repair_batch_d.py、test_anchor_plan_v3.py、test_review_resume_integrity.py、test_repair_batch_c.py |
| 身份下游：test_round4_identity_emitter.py:31、test_round4c_solana_provenance.py:85；run_all.py:81–82 | test_round4_identity_emitter.py、test_round4c_solana_provenance.py |
| exact 下游：test_batch16_resolve_ref_case_path.py:18；run_all.py:192 | test_batch16_resolve_ref_case_path.py |
| 守卫、文档、版本：test_r7_findings.py:198；run_all.py:10–11/:56/:59 | test_r7_findings.py、docs_lint.py --all、test_sixlens_docs.py、test_version_consistency.py |

建议 0.7 至少补入 session 自身、SQD adapter、coverage/stream-tail/sharedmap、reconcile_v4、batch3c、Solana vertical slice、工具脚本 batch1/batch_d 和版本一致性；其余交调度方全套回归确认。

另加隔离进程的纯包导入检查，否则测试预先把 lib 放入 sys.path，会掩盖导入回归。

四协议登记与代码 commit 分离方案成立，锚 test_producer_registry_current.py:43–50、:53–68；最终测试应在登记完成后进行。本次没有把静态检查写成测试实跑 PASS。

**建议的工单 v2 修订清单**

1. 修正“只导入”断言、E27(a) 结束行和守卫汇总函数；17 处仅作为施工前基线；原案数字标注外部背景。
2. 将“完整 plan 一致”改为准确的冻结物料一致；明确可信输入及独立审计锚点边界。
3. old 限于同 case/mint repair parent，拒绝符号链接、自认领和已有 adopted 的多代来源。
4. 旧台账使用纯读取解析，残缺尾行只在内存忽略，源文件字节不变。
5. 优先要求目标 ledger 不存在；全部预验后复制并验哈希，明确中断恢复和提交边界。
6. 落实 verifier 的 plan、行数/行内容参数；严格验证 adopted 和前缀；补已发布代恢复分支，保持旧两参数调用兼容。
7. 深验重建摘要物料，验证前代 sha/digest 对应；补 header、每行与 bundle 的参考源指纹等式。
8. 将版本兼容理由改为“接受原模板的历史成功证据”，删除绝对字节等价和未来自动等价承诺。
9. 修复 session 包导入回退；明确共享常量/模板升级也需触发 producer 身份更新。
10. E27(d) 正向使用真实 ACTIVE 前代，直接 `_plan` 取计划；深验负向更新文件引用以隔离原因，补篡改、跨案、重复认领和源不变向量。
11. 文档仅修改既有条目；adopted 可选、子字段条件必填；守卫注入使用最小源码样本。
12. 保留 9.1.0 和独立登记 commit；补 0.7 直接回归项、版本一致性和隔离包导入检查。
