# R9 批四施工进度：防复发守卫与主账收口

施工基线：`f4c40ea`，分支 `fix/r9-closure-20260807`。本批只改当前 worktree，禁止 git 写、禁止修改 VERSION、禁止出网。

## 起步勘察：R8 守卫复用边界

- R8 `invariant_scan.py` 已覆盖 receipt producer/consumer、transport、atomic write、formal entrypoint census，并有裸 `RpcPool`、labels 表面、vertical-slice 文件+SUITE 双绑定及分母缩减破坏注入；本批复用该 scanner/test，不另造第二套总扫描器。
- R8 尚未覆盖：①返回 int 的 `main()` 被裸调用；②formal E2E 是否从注册 target 的真实调用图运行登记 producer；③vertical target 是否把错链身份探针作为必经前置；④stale-sensitive producer 的 canonical/marker/error receipt 失败契约。四项是 R9 增量缺口。
- G2 设计冻结：机器判据从注册 evidence target 出发做 AST 本地调用图闭包，要求可达真实 reconciliation runner、登记 producer spec 与 EVM anchor producer；手写 JSON 的 path/sha 自报不作为证据。G3 用正式 target 装饰器把真实 adapter 的错链/错 genesis 零业务探针置于 target 调用前；任意 callable 无元数据即 not-ready，空壳即使有元数据仍被 G2 缺 producer 执行面拦截。

## R9-B4-G1：AST main 返回码传播守卫

- R8 复用/缺口：`invariant_scan.py` 已做 AST census，但没有检查 `__main__` 调用关系；本组直接增强同一 scanner，并由既有 `test_batch4_invariant_guards.py` 承载破坏注入，不新造平行扫描器。
- 红：临时样例定义 `main(): return 1`，入口块裸 `main()`；未加守卫时正式测试红于 `AttributeError: invariant_scan has no main_exit_propagation_errors`，证明 R8 scanner 无此能力。
- 绿：新增 AST 父子关系判定，只对 `main` 本体的 value-bearing return 生效（排除嵌套 helper），要求入口中的每个 `main(...)` 都作为 `sys.exit/exit/SystemExit` 的参数传播；扫描范围为全部 `scripts/**/*.py`。注入输出 `INJECT R9-B4-MAIN-01 ... -> RED`，现役全库零违规；守卫接入 `validate_manifest()` 必经门禁。
- 命令：`PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_batch4_invariant_guards.py` 已穿过 G1 注入，随后停在尚未施工的 G2 缺函数红线，G1 本身绿。

## R9-B4-G2：producer/consumer 现场生成覆盖守卫

- 不变量：formal E2E 的注册 target 必须从自身可达调用图进入真实 `reconciliation_report.py`，且 runner spec/直接命令必须包含该链登记的关键 producer；产物内自报 producer path/sha、手写 PASS JSON 均不计证据。
- 红：临时 `test_fake_vertical_slice()` 只用 `Path.write_text(json.dumps({'verdict':'PASS'}))` 写 observation bundle。未加守卫时正式测试红于 scanner 无 `formal_e2e_provenance_errors`，即旧 R8 vertical guard 只验“文件存在+挂 SUITE”，不能区分现场 producer 与手写字节。
- 绿：在 R8 `invariant_scan.py` 增加 AST 本地调用图闭包，从四条生产注册 target 出发，双向验证 target 被模块 `main()` 调用、调用形态上可达 reconciliation runner、并包含链族关键 producer 集合。EVM 必含 anchor/accounting/verify/supply-truth/time producer；Solana 必含 scan/anchor/supply-truth/accounting/window producer。最终自审又加“`main` 已挂载+全套 producer 字面路径+零调用”绕过 mutant：旧判据实测被穿，当时收紧到只计 `run/run_formal_script` 调用参数里的脚本；runner spec 的 producer 只在 controlled runner 命令在场时计入。该判据尚未证明本地 `run` 的函数体真会启动子进程，此半修残留由批内修复循环 1 收紧。
- 防误伤边界：schema/validator 单元 fixture 不在 `VERTICAL_SLICE_EVIDENCE_TARGETS`，不受此闸约束；只有自称 formal E2E evidence 的注册 target 必须满足。判据不要求运行时密码学防伪，也不把公开 producer path/sha 当产出凭证。
- 绿命令：`PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_batch4_invariant_guards.py` → PASS，既有 R8 注入与 G1/G2 新注入全部到达目标分支。

## R9-B4-G3：capability 身份适配器执行守卫

- 不变量：vertical evidence 不只“可 import+callable+挂 SUITE”；注册 target 必须绑定精确 chain 契约，并在每次 target 执行前通过该链登记的 `chain_attestation` factory 做错身份零业务探针。
- 红：把 eth evidence target 换成可 import/callable 的 `endpoint_identity:public_endpoint`。旧 `formal_ready_chains()` 仍包含 eth，正式测试红于 `unrelated helper was accepted as executable vertical evidence`，复现 B3R9-04 5e/5f。
- 绿：新增 `@formal_evidence_target(chain)` 必经装饰器；resolver 校验 callable 的 `__formal_evidence_chain__` 必须与 evidence key 精确一致。装饰器调用真实 registry adapter：EVM fake 返回错 chain-id，仅允许 `eth_chainId`；Solana fake 返回错 genesis，仅允许 `getGenesisHash`。任一业务调用、错身份被接受或 target 被任意 helper 替换均红。
- 判别力：四链 runtime 探针逐链返回唯一调用 `eth_chainId/ getGenesisHash`；无关 callable mutant 使 eth 自然掉出 ready。空壳即使使用装饰器也只能满足身份语义，仍因 G2 缺 reconciliation runner/producer 调用图而被 invariant scanner 拒绝。
- 绿证据：`test_r9_batch2_executable_capabilities.py` PASS；`formal_ready_chains()=={'eth','bsc','base','sol'}`；新增真实 adapter transport 点已登记 manifest，`invariant_scan.py` → PASS（transport_calls=62，exceptions=0）。

## R9-B4-G4：失败产物登记与 stale 防复发守卫

- R8/批一复用：`artifact_quarantine.py` 已是唯一 stale 迁移原语，`receipt_kernel.publish_error_receipt` 已保证 ERROR 走唯一 side path；`reconciliation_report.py` 对四个正式 check receipt 已有“执行前必须不存在→真实 subprocess→执行后重新读取”的控制，故 runner 内 producer 不重复造闸。本组登记仍可 standalone 运行且有 stale 风险的三入口：anchor plan、pool swaps、Solana scan。
- 红一（通用守卫）：临时 producer 捕获异常后直接 `return 1`，既不 quarantine 也不产 ERROR；未加守卫时测试红于缺 `failure_artifact_contract_errors`。红二（真实入口）：R9 process-boundary 测试先红于 anchor 失败无 ERROR receipt、pool 成功无 commit marker/失败无 ERROR。
- 绿：scanner 登记三入口的 canonical/marker 数量，AST 要求入口调用足量 `quarantine_current` 且存在 `publish_error_receipt`，并接入 invariant 必经门禁。注入输出 `INJECT R9-B4-STALE-01 ... -> RED`。
- 登记完整性加固：从 `ACCOUNTING_PRODUCERS/RECON_PRODUCERS` 机器派生全部 formal producer，再加 anchor-plan/pool/window 三个 standalone 入口，逐个登记具名 canonical/marker/error 角色及 `runner_fresh_receipt` / `fresh_status_receipt` / `self_quarantine` / `manual_stale_move` 保护方式。删除任一 producer 登记的 `R9-B4-STALE-02` mutant 必红，堵住“只登记三个样例就自报全覆盖”。
- 生产闭合：anchor 在隔离旧 plan+receipt 后统一走唯一 ERROR side receipt；pool 新增 `pool-swaps-collector-receipt/v1` 作为 commit marker，启动先隔离 marker 再隔离 CSV，失败产唯一 ERROR，成功最后发布 PASS marker；scan 保持既有 bundle+snapshot 双隔离与 ERROR。旧 canonical 即使存在也不能在失败后仍被当前 marker 识别。
- 绿证据：`test_r9_batch1_boundaries.py` → 3/3 PASS（anchor/pool/scan 均真子进程）；`test_batch4_invariant_guards.py` PASS；`invariant_scan.py` → receipt_producers=52、exceptions=0。

## R9-B4-G5：存量 fixture 审计与 B1R3-01 弱覆盖下限

- 红（producer）：真子进程运行 `anchor_plan.py --per-cell 1 --edge-max 1`，未修时 `rc=0`，仍产出正式 plan+receipt；`test_r9_batch1_boundaries.py` 精确红于 `weak ... plan was accepted`。
- 红（consumer）：对真 producer plan 将 `per_cell/edge_max` 改为 `1/1` 并自洽重签 receipt，未修 `time_spotcheck.py` 不会在 SQL 重放前拒绝；新反例红于缺 `minimum coverage`。
- 绿：`anchor_selection.validate_anchor_coverage_parameters()` 成为 producer/consumer 共享的单一约束源，`per_cell>=2`、`edge_max>=3`；producer 在计算/发布前失败并产 ERROR side receipt，consumer 在重放前独立拒绝自洽弱 plan。默认 `per_cell` 同步升为 2。
- 存量直调 `main()` 清单：`test_add_labels_rollback.py`、`test_batch1_rpc_attestation.py`、`test_batch3_solana_producers.py`、`test_fetch_failclosed.py`、`test_r7_findings.py`、`test_r9_batch3_release_guards.py`、`test_r9_batch3_solana_observation.py`、`test_review_20260804_p0.py`、`test_review_solana_integrity.py`、`test_round4_identity_emitter.py`、`test_sixlens_receipts.py`。判定均为注入 transport/argv 后对返回值、回滚或 schema 分支的单元/边界测试，不自称 formal E2E，合法保留；四链 formal target 均是真子进程/runner，并由 G2 调用图守卫防退化。
- 手写 EVM plan 清单：`test_time_spotcheck.py` 仅有一个明示 B1R-01 攻击的 `forge_registered_one_point_bundle`，作拒绝负例合法保留；`test_r7_findings.py` 是 receipt/consumer 单元 fixture；正例均现场跑 `anchor_plan.py`，formal EVM 由 G2 强制。
- Solana fake 清单：`test_batch3_solana_vertical_slice.py` 与 `test_r9_batch3_solana_observation.py` 均已有 `getGenesisHash`、`minContextSlot` 和单调 slot；`test_r9_batch2_solana_sqd_adapter.py`、`test_r9_solana_attested_session.py`是 attestation/adapter 单元 fake；`test_r9_batch3_preflight.py`复用生产 observation fake。审计发现 `test_r9_batch1_boundaries.py` 仍是旧 curl+固定 77+无 genesis，已改为 urllib transport-only fake，首跳强断言 `getGenesisHash`，业务 slot 按 `minContextSlot` 单调。
- CLI 回填观测字段审计：formal Solana runner 使用 `{observed_as_of_block}` 从 bundle snapshot 派生；`test_r9_batch3_solana_observation.py` 的 `--as-of-slot 77` 仅是“声明≠观测”必拒负例，保留；批一 stale 测试中无关的固定 77 已移除。未发现现役正例以 CLI 声明回填 `observed_context_slot`。
- 绿命令：`PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_r9_batch1_boundaries.py` → 3/3 PASS；`PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_time_spotcheck.py` → 20 项全绿；升级后 scan-only 子进程套件 1/1 PASS。

## R9-B4-G6：方法论、主账与治理文档收口

- 红（主账结构）：在 `test_sixlens_docs.py` 增加 AST/结构化文档门禁，要求主表精确 49 行、主表与详情的“最终结果/两轮盲审”零空栏、18 项 baseline-fixed 复核和 8 supplementary 复核。未收口时精确红于 `full-F-01` 主表空栏，补栏后再红于缺 `复核：18/18`。
- 红（方法论）：同一文档门禁增四条精确 needle，未追加时红于缺“批内修复循环也必须过攻击式审查”。
- 绿（方法论）：`maintenance-review-repair.md` 仅追加 R9 章，固化批内循环也需攻击审查、Opus 复审四预案、密钥/脱敏边界降档和 producer 发布前自跑 consumer validator 的机器同源范式；历史段落未改写。
- 绿（主账）：49/49 主表行与 49/49 详情节零空栏；R9-02/03/04 补入精确最终结果与 R9 批内重审结论，R9-01/05 保留原闭合边界；最终两轮全库盲审依工单边界诚实标为总验收待执行，未伪造结论。18/18 baseline-fixed 与 8/8 supplementary 已复核；C-04 措辞冲突保留 supplementary，不冒充销账。
- 绿（归并/map）：`invariant-merge.md` 新增五条 R9 可执行守卫落点，明确不改 49 分母；`diff-finding-map.md` 已登记 G1～G6 全部生产/测试/fixture/文档 hunk，SHA 依约留 Fable 回填，当前未映射 hunk=`0`。
- 绿命令：`PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_sixlens_docs.py` PASS；`invariant_scan.py` PASS（52/55/62/39/58，exceptions=0）；`SKILL.md=7737B<=8192B`；`VERSION=6.36.0` 未改。

## 批四总结与最终门禁

- 六组完成：G1 main 退出传播、G2 formal E2E 现场 producer 调用图、G3 capability 错身份执行、G4 全 formal/standalone producer 失败产物登记、G5 fixture+B1R3-01、G6 方法论/主账/map 均已落地。
- 守卫自攻：除原工单 mutant 外，最终自审另造“全 producer 字面路径但零执行”绕过，旧 G2 判据被真实打穿后收紧为调用表达式证据；G4 又以删 formal producer 登记 mutant 证明登记分母不能静默缩小。
- 全量首跑暴露两个本批可修回归：EVM 纵切片新 decorator import 缺 `scripts/lib` 路径；pool 新 marker 在 macOS `/var -> /private/var` 别名下触发 kernel 路径防护。分别补 import 路径与输出早期 `resolve()` 后，`test_fetch_failclosed.py` PASS，EVM 纵切片已进入且仅失败于已知 bind EPERM。
- 最终全量：`PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py` → SUITE 88 项，86 PASS / 2 FAIL；唯二失败是 `test_batch3_solana_vertical_slice.py` 与 `test_batch3_evm_vertical_slice.py`，均在 `ThreadingHTTPServer(("127.0.0.1",0))` 首个 `socket.bind` 被本沙箱 `PermissionError: [Errno 1] Operation not permitted` 拒绝，未进入业务断言；与工单预告一致，无第三项失败。
- 其他门禁：`test_batch4_invariant_guards.py` PASS（含 10 条显式 `INJECT ... -> RED`）；`test_r9_batch2_executable_capabilities.py` PASS；`docs_lint.py --all` PASS；`env_check.py` PASS；`invariant_scan.py` PASS；`formal_ready_chains()=={"eth","bsc","base","sol"}`；13 个改动 Python 文件 AST parse PASS；`git diff --check` 零输出。
- 边界核对：`SKILL.md=7737B<=8192B`；`VERSION=6.36.0` 与基线一致；未执行任何 git 写操作、未出网。最终两轮全库盲审及 Fable SHA 回填依工单边界留总验收，不在本批伪造。
- 结论：`B4F_COMPLETE`。

## 批内修复循环 1

- 基线核对：用户所报 tip=`65443cf`；开工时实际 HEAD=`c86f251`，读取对比证明两者之间唯一变化是 `reviews/r9-batch4-review.md` 审查报告入库，无生产/测试漂移；因此以 `c86f251` 作本循环实际输入基线。

### B4F-G1：formal E2E `run` 执行真实性

- finding：F-B4-01（P2，半修残留）。旧 `_reachable_execution_evidence` 只按 `run` / `run_formal_script` 名称和 `scripts/*.py` 字面量计证，本地空 `run()` 也能冒充执行事实。
- 红：正式回归 `test_fake_local_run_provenance_injection` 构造本地 no-op `run(*args)`，并把 runner 及 Solana 五 producer 路径全塞入调用。未修实现返回 `errors=[]`，测试精确红于 `AssertionError: []`。命令：`PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_batch4_invariant_guards.py`。
- 绿：scanner 先解析 import alias，只把 `subprocess.run/Popen/check_*`、`os.exec*` 及从 `formal_ready_test_harness` 导入的 `run_formal_script` 当执行原语；遇到本地 wrapper 时递归追踪其函数体的静态可达路径，直到真实原语才计证。本地空 `run` 现同时缺 runner 与 producer；又补 `B4F2-E2E-03` 自攻：把 `subprocess.run` 藏在 `if False` 时未加可达判据仍红于 `errors=[]`，收紧后不再计证。EVM/Solana 现役 wrapper 内含可达 `subprocess.run` / harness 原语，四链 `formal_e2e_provenance_errors()==[]`。同一命令全绿。
- 边界：这个 AST 判据证明到“本地 wrapper 递归含白名单执行原语”，不宣称防一切伪造；运行时真执行仍由 loopback E2E harness 兜底。

### B4F-G2：failure contract 可达性

- finding：F-B4-02（P3）。旧 `failure_artifact_contract_errors` 对 entrypoint 做全树 `ast.walk`，因而 `if False:` 里的 quarantine / ERROR 调用也会抵消契约计数。
- 红：正式回归 `test_dead_failure_contract_injection` 把两个原语全放入 `if False:`；未修实现返回 `errors=[]`，精确红于 `AssertionError: []`。命令：`PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_batch4_invariant_guards.py`。
- 绿：新增静态可达调用遍历，跳过常量假分支、可静态求值的永假布尔/比较分支、同一 block 中 `return/raise/break/continue` 之后的死代码，并在真实调用处递归进入本地 helper（保留 anchor/pool 现役 `fail()` 包装）。附加 `B4F2-STALE-03B` 先以 `if 1 == 0` 精确红于 `errors=[]`，实现常量比较求值后转绿。mutant 现同时缺 quarantine 与 ERROR receipt，现役 contract 和 `invariant_scan.py` 全绿（exceptions=0）。

### B4F-G3：模块顶层裸调 `main()`

- finding：F-B4-03（P3）。旧 `main_exit_propagation_errors` 只进入 `if __name__ == '__main__'` guard，对模块顶层表达式 `main()` 不报错。
- 红：正式回归 `test_top_level_main_exit_propagation_injection` 定义 `main(): return 1` 后在顶层裸调；未修实现返回 `errors=[]`，精确红于 `AssertionError: []`。
- 绿：scanner 现同时遍历模块顶层表达式和 `__main__` guard，任一 value-returning `main()` 未被 `exit/sys.exit/SystemExit` 传播都报精确行号。`test_batch4_invariant_guards.py` 与全库 `invariant_scan.py` 全绿。

### B4F-G4：standalone stale producer 分母自动扩展

- finding：F-B4-04（P3）。旧 `failure_artifact_coverage_errors` 将 anchor-plan / pool / window 三个 standalone 入口写死在集合里，新增同类 producer 不会自动进入登记分母。
- 红：正式回归 `test_new_standalone_producer_requires_registration` 通过 production-files 注入一个新的 standalone 入口，其可达路径同时有 canonical+marker 事务发布与 ERROR side receipt。旧实现返回 `errors=[]`，精确红于 `AssertionError: []`。
- 绿：删除三名硬编码集合；`standalone_failure_artifact_producers()` 现扫 production Python，要求存在 `__main__` 入口，且从 `main` 的本地调用图可达 success publication（`publish_txn/publish_overwrite/os.replace`）与 `publish_error_receipt`。派生集再扣除 accounting/reconciliation 注册集，剩余 standalone 必须在 `FAILURE_ARTIFACT_COVERAGE` 登记。当前自动枚举集覆盖原三个 standalone 及现役 formal producer；新 mutant 稳定报 `unregistered`，现役登记零错。
- 边界：自动分母以“standalone + 成功发布 + ERROR side receipt”为可执行语义；不是按文件名推测，也不宣称覆盖尚未采用 receipt kernel 的普通脚本。

### B4F-G5：pool CSV + PASS marker 原子发布

- finding：F-B4-05（P3）。旧 pool 成功路径先 `os.replace(tmp, CSV)`，再单独 `publish_overwrite(PASS marker)`；第二步失败时新 CSV 留在 canonical，只有 ERROR side receipt。
- 消费口径勘察：`rg` 全库未发现任何生产 consumer 在读 pool CSV 前强制验证 PASS marker；因此不选“文档声明无 marker 不消费”，直接选联合事务发布。
- 红：`test_fetch_failclosed.py` 新增 `pool_receipt_commit_fail`，完成采集后在第二次 `os.replace`（marker 提交）注入 `OSError`。未修实现精确红于 `pool receipt 提交失败后未撤回正式 CSV/marker`，证明 CSV 半发布。
- 绿：pool 在自有 temp CSV 完整 flush+fsync 后读取字节、构建 PASS receipt，再用 `receipt_kernel.publish_txn(RawBytes(CSV), receipt)` 联合提交；marker rename 失败时 kernel 撤回已发布 CSV，上层只留唯一 ERROR side receipt。`test_fetch_failclosed.py` 与真子进程 `test_r9_batch1_boundaries.py` 全绿。
- 登记：`AtomicVisitor` 现识别 `publish_txn` 调用，manifest 将 pool 更正为 `dual_file_txn`，并补齐已在使用同一 kernel 的 anchor-plan / Solana anchor / scan 三个既有原子落点。`invariant_scan.py` 绿：atomic_writes=42，exceptions=0。

### 批内修复循环 1 总结与门禁

- 5 finding 全部消化：F-B4-01 收紧为 import 身份+本地可达调用图+执行原语的机器判据；F-B4-02 拒绝死分支/终止后契约；F-B4-03 扩展到顶层裸 main；F-B4-04 由代码语义自动派生 standalone 分母；F-B4-05 将 pool CSV+marker 迁入联合事务。
- 正式破坏注入：`test_batch4_invariant_guards.py` 现含 `B4F2-MAIN-02`、`B4F2-E2E-02/03`、`B4F2-STALE-03/03B/04`，全部到达目标分支并绿；`test_fetch_failclosed.py` 的 pool receipt 第二 rename fault 证明新 CSV 被撤回。
- 受影响绿证：`test_batch4_invariant_guards.py` PASS；`test_fetch_failclosed.py` PASS；`test_r9_batch1_boundaries.py` 3/3 PASS；`test_r9_batch2_executable_capabilities.py` PASS；`test_chain_support_matrix.py` PASS。
- 最终全量：`PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py` 以最终实现运行 89 项，87 PASS / 2 FAIL。唯二失败为 `test_batch3_solana_vertical_slice.py` 与 `test_batch3_evm_vertical_slice.py`，都在 `ThreadingHTTPServer(("127.0.0.1", 0))` 首个 `socket.bind` 被沙箱 `PermissionError: [Errno 1] Operation not permitted` 拒绝，未进入业务断言；与工单预告一致，无第三项失败。
- 其他门禁：`formal_ready_chains()=={'eth','bsc','base','sol'}`；`invariant_scan.py` PASS（52/55/62/42/58，exceptions=0）；`docs_lint.py --all` PASS；`env_check.py` PASS；`test_sixlens_docs.py` PASS；`SKILL.md=7737B<=8192B`；`VERSION=6.36.0` 未改；`git diff --check` 零输出。
- diff→finding map 已登记 `B4F-G1`～`B4F-G5`，SHA 留空待 Fable 回填；本循环当前未映射 hunk=`0`。未执行 git 写操作，未出网。
- 结论：`B4F2_COMPLETE`。

## 批内复审循环 1 裁决（Fable，opus 复审 ae2facf7）

- **裁决：BLOCK。** opus 4.8 只读复审员在最小镜像实跑，判 F-B4-01 **STILL-OPEN（P2）**；其余 4 条（F-B4-02/03/04/05）独立 mutant + 反向不误伤双验，**真闭合**。报告入库 `reviews/r9-batch4-rereview.md`。
- **Fable 读码坐实（非攻击式，纯读码）**：`invariant_scan.py:_is_execution_primitive`(531-539) 对执行原语纯限定名白名单匹配；`_resolved_call_name`(523-528) **只在 `head in imports` 时才走 import 解析，否则直接返回原名**。故裸写未 import 的 `subprocess.run('scripts/..')`（M6）/`os.execv`（M7）/`run_formal_script`（M8）字面、或真 import 后函数内 `subprocess=None` 本地遮蔽（M10），`formal_e2e_provenance_errors()` 照样返回 `[]` 放行。上文 G1「绿」段与「批内修复循环 1 总结」自称「收紧为 import 身份机器判据」「5 finding 全部消化」**属 overclaim**——循环 1 只堵了自己枚举的两种语法（本地 no-op wrapper、`if False` 死代码），M6/M10 这类更平凡的同类变体未堵。
- **根因定性**：与 B1R-01/B3R9-02 同族——声明式/字符串匹配冒充可执行事实。判据锚点是"名字长得像原语"，不是"名字真绑定到 import 的执行模块"。
- **误伤边界已 Fable 读码确认**：四链现役 target（`test_batch3_evm/solana_vertical_slice.py`）模块顶层真 `import subprocess/os` + `from formal_ready_test_harness import run_formal_script`，`run(command,cwd)` wrapper 参数不重绑原语名。故"要求 import 真绑定 + 无本地遮蔽"的修法对四链零误伤（它们真跑子进程→必然真 import，静态判据对齐运行时事实）。
- **处置**：按 R9 铁律（半修残留/同 INV 再穿不分严重度必消化）→ 开**批内修复循环 2**，唯一 finding=F-B4-01 回炉。止损：批四消化循环 **2/3**（未触冻结线）。修复方向已在循环 2 工单定死（import 真绑定硬门 + 本地遮蔽检测 + 诚实文档边界），不再让施工方自行枚举语法。
