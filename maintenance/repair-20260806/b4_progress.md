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
- 绿：在 R8 `invariant_scan.py` 增加 AST 本地调用图闭包，从四条生产注册 target 出发，双向验证 target 被模块 `main()` 实际调用、可达 reconciliation runner、并可达链族关键 producer 集合。EVM 必含真实 anchor/accounting/verify/supply-truth/time producer；Solana 必含 scan/anchor/supply-truth/accounting/window producer。最终自审又加“`main` 已挂载+全套 producer 字面路径+零 subprocess”绕过 mutant：旧判据实测被穿，收紧后只计可达 `run/run_formal_script` 调用参数里的真实脚本；runner spec 的 producer 只在 controlled runner 命令实际在场时计入。手写样例稳定输出 `INJECT R9-B4-E2E-01 ... -> RED`，四条现役 target 零错误。
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
