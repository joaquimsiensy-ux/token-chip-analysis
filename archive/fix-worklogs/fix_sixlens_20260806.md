# 第六轮六视角修复进度

- 冻结基线：`main@fca61ad528005eb8ee9d9a85efb09dcf76fbc042`
- 边界：只修 F-01～F-13；禁改 `VERSION`、`CHANGELOG.md`、`pyproject.toml`、`SKILL.md` 版本注释、`archive/`、`scripts/tests/contract_manifest.json`、`contract_ids_snapshot.json`；不执行 git 写操作。
- 纪律：各批先补测试并记录 RED，再改实现转 GREEN；新代码按六视角①字段来源、②失败分支复审。

## 批① F-02/F-03/F-04/F-05

### F-02：EVM recon 假成功

1. **不变量**：白名单 EVM recon 必须从参数化输入和 RPC 实测自产绑定 chain/token/end_block 的 v2 回执；硬不一致 exit 2，RPC/工具错误 exit 1，仅全通过 exit 0。
2. **同族清单**：`rg -n "verify_recon|supply_truth_gate|time_spotcheck|reconciliation-report/v2" scripts references commands-staging --glob '*.{py,json,md}'` → 生产者 `verify_recon.py`、`supply_truth_gate.py`、`time_spotcheck.py`；消费者 `shared_release_receipt.py`、`audit_release_gate.py`；夹具 `test_audit_release_gate.py`、`test_round4b_provenance.py`、`test_handoff_manifest.py`。
3. **三件套测试**：原反例＝供给不闭合 exit 2；同族变体＝单地址余额不一致 exit 2；失败分支＝RPC/输入错误 exit 1 且无 PASS。
4. **新代码①②自审**：GREEN 后复核：字段只来自指定文件哈希和 RPC 响应，不接受 wrapper 自报；供给/余额不一致=2，RPC/输入/写回错误=1，均有离线反例。
5. **归因**：历史漏检。

### F-03：聚合器信任自报

1. **不变量**：聚合器逐类解析 receipt，复核 schema、target、必要观测、verdict/exit_code；wrapper 自报与回执不一致、未知 schema 一律拒绝。
2. **同族清单**：`rg -n "RECON_PRODUCERS|validate_sources|reconciliation-report/v2|receipt" scripts/report scripts/tests --glob '*.{py,json}'` → 唯一共享聚合器 `shared_release_receipt.py`，发布调用方 `audit_release_gate.py`，主要夹具 `test_audit_release_gate.py`、`test_round4b_provenance.py`。
3. **三件套测试**：原反例＝`{"anything":true}` 拒绝；同族变体＝合法 schema 但 target 错拒绝；失败分支＝verdict/exit 自相矛盾或未知 schema 拒绝并提示旧案重跑 v2。
4. **新代码①②自审**：GREEN 后复核：逐类 validator 只信 receipt 本体并与 accounting target 绑定；任意 JSON、target 漂移、wrapper/verdict 矛盾、未知 schema 均阻断。
5. **归因**：历史漏检。

### F-04：Solana anchor 失败返回 0

1. **不变量**：任一天 fetch_fail/no_converge 均完整记录后 exit 2；receipt 绑定 mint、日期范围、覆盖与失败明细。
2. **同族清单**：`rg -n "anchor_sampler|fetch_fail|no_converge|time.*receipt|balance.*receipt" scripts references --glob '*.{py,md,json}'` → `anchor_sampler.py`、`shared_release_receipt.py`、`analyze-workflow.md`、`data-pipeline-solana-capture.md`；无专属测试。
3. **三件套测试**：原反例＝fetch_fail exit 2；同族变体＝no_converge exit 2；失败分支＝结果/receipt 写失败 exit 1，不留 PASS receipt。
4. **新代码①②自审**：GREEN 后复核：mint/日期来自 config+CLI，覆盖从实际结果重算；fetch_fail/no_converge=2，receipt 写失败=1，均不产 PASS。
5. **归因**：历史漏检。

### F-05：Solana window gaps 假完成

1. **不变量**：gaps 为空才原子发布正式文件和 PASS receipt；有 gap 仅留 `.partial` 与诊断并 exit 2。
2. **同族清单**：`rg -n "window_fetch|gaps.json|scan_seg|partial" scripts/solana references --glob '*.{py,md}'` → `window_fetch.py` 主入口，`fetch_sqd_transfers_v2.py` 同解析族，`data-pipeline-solana-capture.md` 要求 gaps 为空。
3. **三件套测试**：原反例＝一段失败无正式文件；同族变体＝全段成功才正式 rename+PASS receipt；失败分支＝写/rename/receipt 异常 exit 1 且无正式文件。
4. **新代码①②自审**：GREEN 后复核：覆盖来自 segment 结果；gap=2 且仅 partial，写回=1；刷新失败会撤回新文件并恢复旧正式字节。
5. **归因**：历史漏检。

## 批② F-06/F-07/F-08

### F-06：非法块区间零请求假成功

1. **不变量**：正式块区间采集器在创建任何产物前拒绝负数、空区间和反向区间。
2. **同族清单**：`rg -n "from.block|to.block|from_block|to_block" scripts/evm/fetch_pool_swaps.py scripts/evm/fetch_hypersync.py scripts/evm/fetch_hypersync_logs.py` → pool 无校验；hypersync 正式 receipt 需上界但缺非负/顺序校验；logs 是动态 tip legacy 入口且无冻结上界。
3. **三件套测试**：原反例＝pool 10→10、100→10；同族变体＝负值及 hypersync 正式非法区间；失败分支＝均 exit 2 且零产物。
4. **新代码①②自审**：GREEN 后复核：只用 argparse 整数并在网络/开文件前校验；相等、反向、负值均 exit 2 且零产物。
5. **归因**：半修残留。

### F-07：采集中途失败遗留正式文件

1. **不变量**：新正式采集先写临时文件，全区间完成后原子提交；续段失败保留原前缀，不能污染正式文件。
2. **同族清单**：`rg -n "open\(.*out|os.replace|NamedTemporary|\.partial|receipt" scripts/evm/fetch_pool_swaps.py scripts/evm/fetch_hypersync.py scripts/evm/fetch_hypersync_logs.py` → 三者均直写正式路径；hypersync 仅 receipt 原子写；logs 无 receipt。
3. **三件套测试**：原反例＝pool 第一页成功第二页失败无正式文件；同族变体＝hypersync 新文件失败无正式文件、续段失败原文件字节不变；失败分支＝提交失败不打印 COMPLETE/不产 receipt。
4. **新代码①②自审**：GREEN 后复核：完成性来自游标/冻结上界；中途失败清临时并保持原文件，CSV/receipt 任一提交失败会整笔回滚。
5. **归因**：半修残留。

### F-08：GMGN 失败保留旧正式结果

1. **不变量**：同一目标的新运行失败时，旧正式 JSON 必须改名 `.stale`，不能继续伪装本次结果。
2. **同族清单**：`rg -n "fetch_gmgn|\.stale|GMGN DONE|tmp" scripts/evm scripts/tests --glob '*.{sh,py}'` → 脚本只清 `.tmp`；`test_fetch_gmgn_sh.py` 各场景分目录，缺 success→failure。
3. **三件套测试**：原反例＝同目录 success→failure 留 stale；同族变体＝success→invalid 同样 stale；失败分支＝无旧文件只清 temp，不伪造 stale。
4. **新代码①②自审**：GREEN 后复核：stale 仅针对精确同名旧正式文件；命令失败/非法 JSON 均移为 stale 且总退出非零，不打印 DONE。
5. **归因**：新引入。

## 批③ F-09/F-10

### F-09：增量标签绕过 benchmark/manifest

1. **不变量**：任何现役标签写入口机器强制 validate+benchmark+manifest；任一步失败恢复全部表和旧 manifest。
2. **同族清单**：`rg -n "validate_labels|benchmark_labels|labels_manifest|add_labels|build_labels" scripts/labels scripts/tests references/labels --glob '*.{py,md}'` → 全量流程三闸齐全；`add_labels.py` 仅 validate，成功后提前删备份；`labels_manifest.py --write` 可落印。
3. **三件套测试**：原反例＝benchmark 退化回滚原表；同族变体＝新建表 benchmark 失败删除；失败分支＝benchmark/manifest 异常均回滚，成功才清备份。
4. **新代码①②自审**：GREEN 后复核：门禁来自真实子进程退出码；validate/benchmark/manifest 任一非零或异常均统一恢复表和旧 manifest。
5. **归因**：半修残留。

### F-10：roundtrip 漏行为字段

1. **不变量**：roundtrip 比较 resolver 消费的全部行为字段；仅显式 provenance 白名单可差异且输出 WARN。
2. **同族清单**：`rg -n "DECISION_FIELDS|risk_flags|merge_policy|balance_policy|raw_labels|source_snapshot_at" scripts/labels scripts/tests references/labels --glob '*.{py,md}'` → `risk_flags` 被 resolver/增量合并消费但未比较；15 列 schema 含 provenance 字段。
3. **三件套测试**：原反例＝risk_flags 单侧丢失 FAIL；同族变体＝新增行为字段逐项漂移 FAIL；失败分支＝source/evidence/added_date/verified_at/source_snapshot_at/raw_labels 只 WARN 且可通过。
4. **新代码①②自审**：GREEN 后复核：值直接来自两边 CSV；risk_flags 纳入硬比较，六个 provenance 白名单字段逐项 WARN，缺表/读取失败仍 fail-closed。
5. **归因**：半修残留。

## 批④ F-01/F-13

### F-01：正式 provenance 可省标签

1. **不变量**：正式 provenance 必须绑定非空标签快照；无标签只能显式探索，探索 ledger 不得 freeze。
2. **同族清单**：`rg -n "labels-file|no-labels|allow-no-labels|provenance-ledger|labels_file" scripts/report scripts/evm scripts/solana scripts/tests references --glob '*.{py,md,json}'` → 生产者 `entity_source_trace.py` 标签可选；消费者 `handoff_manifest.py` 仅非空验证；其余 no-labels 为 cluster/replay 辅助，不生产 provenance ledger。
3. **三件套测试**：原反例＝正式缺 labels exit 2；同族变体＝显式探索产 exploration ledger；失败分支＝freeze/verify 对 null labels 或 exploration ledger 拒绝。
4. **新代码①②自审**：GREEN 后复核：标签来自真实文件哈希，探索标记由 CLI 生成；正式缺标签=2，探索/null-label ledger 在 freeze 首层即拒。
5. **归因**：历史漏检。

### F-13：READY 范围参数可省略

1. **不变量**：READY handoff 必须冻结已知 chain 与非空 contract，generate/verify 两侧独立重验。
2. **同族清单**：`rg -n "--chain|--contract|scope.*chains|KNOWN_CHAINS|EVM_CHAINS|default=None" scripts/report scripts/evm scripts/solana scripts/robinhood --glob '*.py'` → handoff 两参数 default None；identity/accounting 正式入口已 required；其余待裁决项列于下方。
3. **三件套测试**：原反例＝READY 缺 chain/contract 拒绝；同族变体＝未知 chain 拒绝；失败分支＝verify 空 chains/未知 chain/空 contract 拒绝，PARTIAL 不误收紧。
4. **新代码①②自审**：GREEN 后复核：scope 来自 CLI，generate/verify 独立对已知链重验；READY 缺/未知链、空 contract 均 exit 2，PARTIAL 不误收紧。
5. **归因**：历史漏检。

#### 同族范围参数待 Fable 裁决

- `fetch_sqd_evm.py --to-block=None`：正式 receipt 已强制上界；非 receipt 动态 tip 暂不改。
- `fetch_alchemy.py --to-block=None`：历史 latest 采集入口；迁移面超出本批，暂不改。
- `fetch_hypersync_v2.py` legacy collect `--to-block=None`：另有 finalize 强制上界，暂不改。
- `pull_lp_events.py --to-block=None`：专项 LP 工具，不是 handoff 范围真源，暂不改。
- `cluster_sensitivity.py --chain=None`、`price_check.py --chain=None`、`decode_txs*.py --mint=None`：探索/分析辅助，不产 READY/freeze 范围，暂不改。
- `anchor_plan.py --token=None`：time_spotcheck 自身强制 token；暂不改。

## 批⑤ F-11/F-12

### F-11：SKILL 大小双口径

1. **不变量**：现役只有“7.5KB 预警、8192B 硬上限”一套口径。
2. **同族清单**：对旧单阈值及 `8192|7.5KB` 做全库检索 → `retrospective.md:91` 残留旧单阈值；`docs_lint.py:300-302` 为 8192B；60KB 分册规则不属于本不变量。
3. **三件套测试**：原反例＝现役旧单阈值清零；同族变体＝文档含 7.5KB/8192B；失败分支＝docs_lint 继续守硬上限。
4. **新代码①②自审**：无新代码，只收敛文档事实源。
5. **归因**：半修残留。

### F-12：casebook 回流 archive

1. **不变量**：分析会话 casebook 不得路由 archive；候选归档只由复盘维护流程处理。
2. **同族清单**：`rg -n "archive/evals|archive/" SKILL.md references scripts/tests/docs_lint.py --glob '*.{md,py}'` → `casebook/README.md:31` 与 `retrospective.md:94`；按裁决只改前者，后者及豁免不动。
3. **三件套测试**：原反例＝casebook 不再含 archive/evals；同族变体＝retrospective 登记保持；失败分支＝archive 和 docs_lint 零改动。
4. **新代码①②自审**：无新代码，单行文本小手术。
5. **归因**：历史漏检。

## 批次结果

| 批次 | RED | GREEN | 新增测试 | ①②自审 |
|---|---|---|---|---|
| ① | RED：缺 v2 validator、失败脚本返回 0 | GREEN：伪回执/target 漂移/三生产者失败与提交回滚全过 | `test_sixlens_receipts.py` | 字段实算；所有异常 1/2 收口 |
| ② | RED：非法区间产正式 CSV；旧 GMGN 未 stale | GREEN：非法区间、分页失败、双文件事务、stale 全过 | 扩展 `test_fetch_failclosed.py`、`test_fetch_gmgn_sh.py` | 游标实算；失败零提交/恢复旧产物 |
| ③ | RED：benchmark 未阻断；risk_flags 漂移被接受 | GREEN：三闸回滚与行为字段比较全过 | 扩展 `test_add_labels_rollback.py`、`test_roundtrip_check.py` | 子闸退出码实测；任一失败统一回滚 |
| ④ | RED：正式无标签/空 scope 均放行 | GREEN：正式/探索边界与双侧 scope 重验全过 | 扩展 `test_entity_source_trace.py`、`test_handoff_manifest.py` | 文件哈希/CLI scope 实取；缺失即 2 |
| ⑤ | RED：casebook 回流 archive；旧单阈值 | GREEN：定向文档测试与全库检索通过 | `test_sixlens_docs.py` | 无新代码 |

## 最终验收

- `python3 scripts/tests/run_all.py`：最终轮 exit 0，汇总“全部通过”。首轮 3 个迁移夹具失败已修并在后两轮全绿。
- 禁改项差异复核：`VERSION`、`CHANGELOG.md`、`pyproject.toml`、`SKILL.md`、`archive/`、两份 contract registry 均零差异。
- 旧大小单阈值现役残留：全库限定检索 0 命中。
- 临时副作用：无 `.tmp`、`.bak`、`.previous.*` 遗留；测试误归档 fixture 已在发现时删除。
- 最终新代码①②复审：补做 window 旧正式文件恢复、HyperSync CSV/receipt 双文件提交故障注入；均经历 RED→GREEN，最终 suite 覆盖。

## 每批实际修改文件

- 批①：`scripts/evm/verify_recon.py`、`scripts/lib/{supply_truth_gate,time_spotcheck}.py`、`scripts/solana/{anchor_sampler,window_fetch,scan_token_accounts}.py`、`scripts/report/shared_release_receipt.py`、相关 workflow/recon/Solana/audit 文档与测试。
- 批②：`scripts/evm/{fetch_pool_swaps,fetch_hypersync,fetch_hypersync_logs}.py`、`fetch_gmgn.sh`、`test_fetch_failclosed.py`、`test_fetch_gmgn_sh.py`。
- 批③：`scripts/labels/{add_labels,roundtrip_check}.py`、`test_add_labels_rollback.py`、`test_roundtrip_check.py`。
- 批④：`scripts/report/{entity_source_trace,handoff_manifest}.py`、`references/split-run.md`、`commands-staging/token-analyze-1.md`、对应测试。
- 批⑤：`references/casebook/README.md`、`references/retrospective.md`、`test_sixlens_docs.py`。
- 共用：`scripts/tests/run_all.py`、`test_sixlens_receipts.py`；为新返回码/schema 迁移同步更新既有夹具。
