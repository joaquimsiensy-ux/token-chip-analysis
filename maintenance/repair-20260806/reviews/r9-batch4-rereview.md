# R9 批四·批内修复循环 1 增量复审报告（Opus 4.8 只读复审员）

复审区间 `65443cf..3f3fcd2`（`c121422`=消化主体，`3f3fcd2`=SHA 回填）。只读原 worktree；mutant 全在最小镜像 `$MIRROR`（cp scripts+references）跑。不出网、未改被审代码。

---

## 一、总裁决：BLOCK · 新 finding P0=0 / P1=0 / P2=1 / P3=0

**重点 finding F-B4-01 未真闭合——换语法就穿的半修残留。** 施工方 commit(`c121422`) 与 `b4_progress.md` 自称「F-B4-01 收紧为 import 身份+本地可达调用图+执行原语的机器判据」「5 finding 全部消化」「B4F2_COMPLETE」，但实测：**攻击样本只要不 import subprocess/os/harness、直接写裸限定名 `subprocess.run('scripts/...')` 字面（M6），或真 import 后在函数内把名字遮蔽成 None（M10），`formal_e2e_provenance_errors()` 照样返回 `[]` 放行。** 修复只堵住了施工方自己枚举的两种语法（本地 no-op wrapper、`if False` 死代码），一个更简单的同类语法直接穿，且现役测试完全未覆盖该变体。

其余 4 个 finding（F-B4-02/03/04/05）经独立 mutant + 反向不误伤验证，均真闭合。五守卫必经性成立。消化循环 1 的 G2/G3/G4/G5 改动未引入新洞。**唯一阻断项就是 F-B4-01 自报闭合与事实矛盾。**

> 裁决口径说明：本发新 finding 严重性为 P2（利用需内部改 `VERTICAL_SLICE_EVIDENCE_TARGETS`+塞假 target 文件，运行时另有 loopback E2E harness 兜底——虽解耦且沙箱 EPERM 未跑通）。若按「仅 P0/P1 才 BLOCK」的历轮惯例，本发可记「PASS 带 1×P2」；但本轮是**专门盯 F-B4-01 是否闭合的批内复审**，其唯一 P2 任务未达成且被自报为已闭合，故从严裁决 **BLOCK：F-B4-01 需二次消化**，不得带「已闭合」进入最终盲审。

---

## 二、5 finding 闭合裁定表

| finding | 前发定性 | 本发裁定 | 关键证据 | 归因 |
|---|---|---|---|---|
| **F-B4-01** G2 formal E2E `run` 执行真实性 | P2 半修残留 | **STILL-OPEN（P2）** | M6/M7/M8/M10 BYPASSED；M1/M2/M3 CAUGHT、M4/M5 不误伤、M9 REFUTED | **原 finding 未真闭合**（换语法就穿） |
| F-B4-02 failure contract 死代码充数 | P3 半修残留 | **CLOSED** | return 后死代码/`while False` CAUGHT；正常可达不误伤 | 原 finding 已闭合 |
| F-B4-03 顶层裸调 main() 漏检 | P3 新引入 | **CLOSED** | 顶层裸/guard `print(main())` CAUGHT；顶层 `sys.exit/raise SystemExit(main())` 不误伤 | 原 finding 已闭合 |
| F-B4-04 standalone 硬编码三入口 | P3 新引入 | **CLOSED** | 自动派生 8 个、现役 coverage_errors=[]、新 producer mutant 被抓 | 原 finding 已闭合 |
| F-B4-05 pool CSV→marker 非原子 | P3 新引入 | **CLOSED** | `publish_txn` 真回滚事务，第二件失败撤回第一件 CSV | 原 finding 已闭合 |

### F-B4-01 复现（重点）

镜像 `$MIRROR` 内 `python3 probe_reref.py` / `probe3.py`，均调 `formal_e2e_provenance_errors(targets={"sol":(样本, "test_fake_vertical_slice")})`：

| 变体 | 构造 | 期望 | 实测 |
|---|---|---|---|
| M0 现役四链真 target | `formal_e2e_provenance_errors()` | 不误伤 | **errors=[] CLEAN** ✓ |
| M1 本地 no-op `run()` | 施工方 B4F2-E2E-02 | CAUGHT | CAUGHT ✓ |
| M2 wrapper 内 `if False: subprocess.run` | 施工方 B4F2-E2E-03 | CAUGHT | CAUGHT ✓ |
| M3 断链多层 `run→_r2→_r3(空)` | 递归断链 | CAUGHT | CAUGHT ✓ |
| M4 真链多层 `run→_r2→subprocess.run` | 不误伤真链 | PASS | PASS ✓ |
| M5 `import subprocess as sp; sp.run` | 不误伤别名 | PASS | PASS ✓ |
| **M6 不 import，裸 `subprocess.run('scripts/..')`** | **换语法绕过** | CAUGHT | **PASS(errors=[]) BYPASSED** ✗ |
| **M7 不 import，裸 `os.execv(...)`** | **换语法绕过** | CAUGHT | **PASS(errors=[]) BYPASSED** ✗ |
| **M8 不 import，裸 `formal_ready_test_harness.run_formal_script(...)`** | **换语法绕过** | CAUGHT | **PASS(errors=[]) BYPASSED** ✗ |
| M9 `getattr(subprocess,'run')(...)` | 间接调用 | CAUGHT | CAUGHT ✓（不构成绕过） |
| **M10 `import subprocess` 后函数内 `subprocess=None` 再 `subprocess.run`** | **遮蔽绕过** | CAUGHT | **PASS(errors=[]) BYPASSED** ✗ |

**根因**：`invariant_scan.py:_is_execution_primitive` 对执行原语纯限定名字符串匹配白名单（`subprocess.run/Popen/check_*`、`os.exec*`、`formal_ready_test_harness.run_formal_script`）；`_resolved_call_name` 只在 `head in imports` 时才 resolve 别名，`head` 不在 import 表时**直接信任原名匹配白名单**（M6/M7/M8），且完全不追踪局部名字遮蔽（M10）。静态 AST 无法证明 `subprocess.run` 这个调用真的绑定到 subprocess 模块的 run。施工方新增的 import-alias 解析只保证了「合法别名执行不误伤」（M5 PASS），却没堵住「名字不真绑定执行模块」这一根因。绕过后 runner+5 producer 路径字面全被收进 `executed`，`observed` 满足，`errors=[]`。

**为何是 STILL-OPEN 而非新问题**：F-B4-01 的验收标准就是「`run` 执行真实性」；M6/M10 同属「伪造执行证据骗过 `formal_e2e_provenance_errors`」，是同一守卫、同一威胁，只是语法比施工方枚举的更简单。施工方在 B4F-G1「边界」段写了「不宣称防一切伪造，运行时由 loopback E2E harness 兜底」——该免责可解释「未做运行时密码学防伪」，但**不能解释「裸限定名字面无中生有制造静态执行证据」这种平凡绕过**，且 commit message 明确把「import 解析」列为已闭合能力，而 import 解析恰是漏洞面。

---

## 三、边界外一步逐项（消化循环 1 新引入/半修残留）

1. **B4F-G1 递归 wrapper 的性能/正确性**：递归终止防护到位——`_local_function_executes` 有 `visiting` 集、`_reachable_calls.visit_function` 有 `id(node)` visiting 集、`_local_function_closure` 有 `seen` 集，三处均防无限递归/循环调用；单文件 AST，无循环 import 风险。真链(M4)/别名(M5)不误伤。import 别名解析（`_execution_imports`）覆盖 `import subprocess as X` 与 `from subprocess import run`（M5 证明合法路径不误伤）。**唯一问题是根因白名单缺陷=F-B4-01 STILL-OPEN**，非递归/别名本身。
2. **B4F-G4 自动派生误伤**：`standalone_failure_artifact_producers()` 现役派生 8 个（fetch_pool_swaps/verify_recon/anchor_plan/supply_truth_gate/time_spotcheck/anchor_sampler/scan_token_accounts/window_fetch），代码 `- accounting - reconciliation` 扣除 registry 后登记；实测 `failure_artifact_coverage_errors()==[]`，**无把合法非 stale producer 误纳入导致的假红**。新 producer mutant（B4F2-STALE-04）稳定被抓。
3. **B4F-G5 pool 连带回归**：`fetch_pool_swaps.py` 仅改收尾落盘（`os.replace`+`publish_overwrite` → `publish_txn` 联合事务），HyperSync 采集循环（fetch 路径）未动；`publish_txn` 与 anchor/scan 同一 receipt-kernel 原语，异常分支 committed=False 时回滚已发布件；CSV consumer 读 out_path 语义不变，无回归。
4. **五守卫必经性**：`validate_manifest()` 第 64/67/68/69 行分别挂 `main_exit_propagation_errors`(F-B4-03)、`formal_e2e_provenance_errors`(F-B4-01)、`failure_artifact_contract_errors`(F-B4-02)、`failure_artifact_coverage_errors`(F-B4-04)；pool `dual_file_txn`(F-B4-05) 经 manifest `atomic_writes` 校验（`AtomicVisitor` 已识别 `publish_txn`）。`run_all.py` SUITE 挂载 `invariant_scan.py`+`test_batch4_invariant_guards.py`+`test_fetch_failclosed.py`+`test_r9_batch1_boundaries.py`。**全部必经，非旁挂。**

---

## 四、REFUTED-CANDIDATE

- **getattr 间接调用绕过**（任务变体④）：M9 CAUGHT。`_call_name(Call)==""`，getattr 调用不匹配白名单 → 不被当执行原语 → 无法制造证据。方向与绕过相反（顶多误伤现役，但现役不用 getattr）。REFUTED。
- **G4 自动派生误伤现役合法 producer**：`coverage_errors()==[]`，REFUTED。
- **G1 递归无终止/循环**：三处 visiting/seen 防护，REFUTED。
- **F-B4-02/03/04/05 未闭合**：独立 mutant 全部 CAUGHT + 反向不误伤，四条均 CLOSED，REFUTED。
- **消化循环 1 新引入新洞**：G2/G3/G4/G5 改动经 M2/M3/M4/C_reachable_ok/coverage 等反向检验无新增误伤/漏检，REFUTED。

---

## 五、工作区自查

- 只读原 worktree，未改被审代码；mutant 全在镜像 `$MIRROR`（cp scripts+references+VERSION+SKILL.md）。
- 未用 `du`/`find <大目录>`/`ls -R`/整树 `wc -l`；首条重命令即建镜像。未出网。
- 引用前 `sed -n`/`git diff`/`grep -n` 核对函数体；镜像 `invariant_scan.py` shasum=`a18ffa44…`（工作区干净=HEAD 3f3fcd2）。
- 报告写后 `ls -la` 确认落盘（见执行记录）。
- **未复现项**：运行时 loopback E2E harness 真跑（沙箱 `socket.bind` EPERM，与施工记录预告一致，两 vertical-slice 测试因此在本机 FAIL，非业务红）；M6 假 target 能否穿透 G3 装饰器+harness 真跑到发布路径未端到端验证——但 `formal_e2e_provenance_errors` 这道静态守卫被击穿本身已足以判 STILL-OPEN。

---

## 三行摘要

1. **总裁决 BLOCK**：重点 finding F-B4-01 未真闭合，换语法（裸限定名/局部遮蔽）就穿，自报「B4F2_COMPLETE」与事实矛盾。
2. **5 finding 闭合统计**：CLOSED 4（F-B4-02/03/04/05）、STILL-OPEN 1（F-B4-01）；新 finding P0=0 / P1=0 / **P2=1**（RR-01=F-B4-01 未闭合）/ P3=0。
3. **报告位置**：`r9-reviews/b4/rereview.md`。
