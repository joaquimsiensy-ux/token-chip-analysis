# 7.0.3 → 7.0.4 施工交接

**r4b 最终裁决范围：按 r3_fix_ruling.md 末尾勘误，唯一精确不变的数量为整数路径 stock_raw。令 B=4·n·2^-52·S+2（n=模拟消费边数，S=total_supply raw），①非 UNRESOLVED 构成键逐键 raw、②data_gap/fp_residual 合桶量（gap704+residual704 对 gap703）、③构成 Σraw、④逐笔短缺与 7.0.3 的差均检查 |Δ|≤B；闭合 pct 差≤B/stock_raw×100（stock>0）。原始 data_gap/fp_residual 标签逐键差仅记录为标签迁移量，不判界、不承诺相同。Δ 可正可负；展示值、事件计数、三策略 policy_details 和翻转指纹不承诺不变。改标签在 float 之上会对全部构成产生 ulp 级扰动，7.0.3 与 7.0.4 都是浮点近似，无优劣。APU/PYTHIA 既有 224 锚点只读复核的非 UNRESOLVED 键、合桶量、Σraw 与 pct 差均为 0；原始标签迁移另列。**

**r4 的 684 次原始标签“超界”按勘误保留为标签迁移历史，不计 r4b 数量界失败。原始 r4 日志及退出码不改写；当前终态与新七项检查见文末“r4b 续工记录”。本轮保持全程离线，不重跑全套/APU/PYTHIA，不 commit。**

T6 有界差分通过，原参数正式跑因旧收据指纹失配 exit 2；T7 同输入双版本对照完成。全套结果由调度方沙箱外提供，指定文件为 run_all_fable.log；当前到位状态见第 4 节。本机沙箱的 145/147 结果保留，不记为本机全绿。

## 1. 改动清单

- 基线 HEAD：`2000b6e78f790ee0ed348cc2ecb8eae796d5136e`；`3b29e38` 为其祖先。初始工作区干净，工单行号与锚文本全部一致，无锚点不符停工事件。
- 生产逻辑仅改 A1：新增 GAP_EPS_REL/gap_eps；EPS 以上、gap_eps 以下或等于阈值的短缺记 UNRESOLVED/fp_residual，本版 take 返回的短缺原样入桶，两版 take 结果可不同；数量承诺及原始标签迁移口径见置顶范围。账户 EPS、账户类及闭合门禁保持原样。
- VERSION、pyproject.toml、SKILL.md 同步 7.0.4；补 7.0.3/7.0.4 CHANGELOG、schema 登记和回归断言。
- 既有测试、handoff_manifest.py、test_sqd_gap_repair.py、test_handoff_manifest.py、invariant_manifest.json、PYTHIA fixture、run_all.py 保持；SUITE 仍 147 项。见 scope_checks.json 与 final_scope_checks.json。
- 原输入清单 33/33、APU 补件 1/1、PYTHIA 补件 2/2 已校验并复检；没有改收据或原案输入。新增输出仅存隔离暂存目录。
- 全程离线，未访问 /Users/uravvv/Documents、未 fetch、未 commit；暂存目录已被忽略。

| 文件 | 新增行 | 删除行 |
|---|---:|---:|
| `CHANGELOG.md` | 19 | 0 |
| `SKILL.md` | 1 | 1 |
| `VERSION` | 1 | 1 |
| `maintenance/repair-20260915-eps-residual/apu_diff.json` | 12560 | 0 |
| `maintenance/repair-20260915-eps-residual/apu_formal_attempt1_trace_704.log` | 3 | 0 |
| `maintenance/repair-20260915-eps-residual/apu_formal_attempt1_trace_704_run.json` | 6 | 0 |
| `maintenance/repair-20260915-eps-residual/apu_formal_followup.log` | 334 | 0 |
| `maintenance/repair-20260915-eps-residual/apu_formal_followup.stderr.txt` | 0 | 0 |
| `maintenance/repair-20260915-eps-residual/apu_formal_followup_result.json` | 40 | 0 |
| `maintenance/repair-20260915-eps-residual/apu_regression.md` | 276 | 0 |
| `maintenance/repair-20260915-eps-residual/apu_trace_704_diagnostic.log` | 334 | 0 |
| `maintenance/repair-20260915-eps-residual/apu_trace_704_diagnostic_run.json` | 6 | 0 |
| `maintenance/repair-20260915-eps-residual/capture_red.py` | 46 | 0 |
| `maintenance/repair-20260915-eps-residual/changelog_lint.log` | 1 | 0 |
| `maintenance/repair-20260915-eps-residual/changelog_lint_followup.log` | 1 | 0 |
| `maintenance/repair-20260915-eps-residual/check_results.json` | 27 | 0 |
| `maintenance/repair-20260915-eps-residual/compare_apu.py` | 104 | 0 |
| `maintenance/repair-20260915-eps-residual/compare_pythia.py` | 112 | 0 |
| `maintenance/repair-20260915-eps-residual/docs_lint.log` | 1 | 0 |
| `maintenance/repair-20260915-eps-residual/docs_lint_followup.log` | 1 | 0 |
| `maintenance/repair-20260915-eps-residual/done.md` | 124 | 0 |
| `maintenance/repair-20260915-eps-residual/done_attempt1_partial.md` | 99 | 0 |
| `maintenance/repair-20260915-eps-residual/final_scope_checks.json` | 31 | 0 |
| `maintenance/repair-20260915-eps-residual/finalize_apu.py` | 36 | 0 |
| `maintenance/repair-20260915-eps-residual/finalize_scope.py` | 46 | 0 |
| `maintenance/repair-20260915-eps-residual/fixtures_lint.log` | 1 | 0 |
| `maintenance/repair-20260915-eps-residual/fixtures_lint_followup.log` | 1 | 0 |
| `maintenance/repair-20260915-eps-residual/followup_checks.json` | 27 | 0 |
| `maintenance/repair-20260915-eps-residual/followup_staging_checks.json` | 44 | 0 |
| `maintenance/repair-20260915-eps-residual/invariant_scan.log` | 1 | 0 |
| `maintenance/repair-20260915-eps-residual/pythia_diff.json` | 1713 | 0 |
| `maintenance/repair-20260915-eps-residual/pythia_extra_input_checks.json` | 16 | 0 |
| `maintenance/repair-20260915-eps-residual/pythia_input_probe.json` | 104 | 0 |
| `maintenance/repair-20260915-eps-residual/pythia_regression.md` | 89 | 0 |
| `maintenance/repair-20260915-eps-residual/pythia_run_703.log` | 30 | 0 |
| `maintenance/repair-20260915-eps-residual/pythia_run_703.stderr.txt` | 0 | 0 |
| `maintenance/repair-20260915-eps-residual/pythia_run_703_result.json` | 27 | 0 |
| `maintenance/repair-20260915-eps-residual/pythia_run_704.log` | 30 | 0 |
| `maintenance/repair-20260915-eps-residual/pythia_run_704.stderr.txt` | 0 | 0 |
| `maintenance/repair-20260915-eps-residual/pythia_run_704_result.json` | 27 | 0 |
| `maintenance/repair-20260915-eps-residual/red_evidence.txt` | 588 | 0 |
| `maintenance/repair-20260915-eps-residual/red_setup_attempt.txt` | 557 | 0 |
| `maintenance/repair-20260915-eps-residual/run_all_eps.exit` | 1 | 0 |
| `maintenance/repair-20260915-eps-residual/run_all_eps.log` | 199 | 0 |
| `maintenance/repair-20260915-eps-residual/run_all_fable_result.json` | 9 | 0 |
| `maintenance/repair-20260915-eps-residual/run_all_result.json` | 14 | 0 |
| `maintenance/repair-20260915-eps-residual/run_apu.py` | 28 | 0 |
| `maintenance/repair-20260915-eps-residual/run_checks.py` | 23 | 0 |
| `maintenance/repair-20260915-eps-residual/run_followup.py` | 63 | 0 |
| `maintenance/repair-20260915-eps-residual/scope_checks.json` | 62 | 0 |
| `maintenance/repair-20260915-eps-residual/staging_recheck.log` | 33 | 0 |
| `maintenance/repair-20260915-eps-residual/t7_ruling.md` | 25 | 0 |
| `maintenance/repair-20260915-eps-residual/test_entity_source_trace.log` | 107 | 0 |
| `maintenance/repair-20260915-eps-residual/test_version_consistency.log` | 1 | 0 |
| `maintenance/repair-20260915-eps-residual/write_done.py` | 87 | 0 |
| `pyproject.toml` | 1 | 1 |
| `references/scan-schemas.md` | 9 | 3 |
| `scripts/report/entity_source_trace.py` | 30 | 10 |
| `scripts/tests/test_entity_source_trace.py` | 184 | 0 |

## 2. 与工单差异

- 以调度方补充裁决覆盖初次卡点；初次 PARTIAL 交接保存在 done_attempt1_partial.md，仅作历史记录。
- T6：补件后原参数（含 --acknowledge-flip）正式重跑一次。验收改为“已完成的诊断 T4 数量证据 + 正式 fail-closed 记录”；旧收据 8/10 失配属设计内行为，不修改收据或参数凑通过。
- T7：按 t7_ruling.md 改为 7.0.3/7.0.4 同输入双跑；使用 entity_file_flat.json 的 7 实体 102 址，不与历史 fixture 锚点作相等断言，不要求旧 W1/标签快照，不改 fixture。
- run_all：本机两项 socket.bind PermissionError 属环境限制。按裁决不再重跑；全套结果由调度方沙箱外提供，引用 run_all_fable.log，归属不混写。
- 旧算法由 git show HEAD:scripts/report/entity_source_trace.py 导出；为满足 __file__ 相邻依赖，逐字复制到临时 scripts/report/trace_703.py，链接未改动依赖，设置 PYTHONPATH；未改旧算法。
- 初次 RED 布局缺 lib 的失败保存在 red_setup_attempt.txt，不计有效 RED。修复布局后于生产代码未修改时重新取证，见 red_evidence.txt。
- T8 在既有 test_entity_source_trace.py 复用完整 READY 案根与 subprocess harness，未用新增测试文件/SUITE +1 备选。

## 3. RED → GREEN

- RED 算法 SHA-256：`ff4b640a1adbcecf8f3651efbda04493d3085754f939da1ef23b8d9f2efe0fc3`。T1 旧版 CLI exit 0、data_gap_events=1、两锚点 raw="1"；T2① 旧版 raw="100"。三策略明细、闭合、命令、退出码和原文见 red_evidence.txt。
- 新断言运行于未改动 7.0.3：exit 1，12 项预期失败；A1 修复后 test_entity_source_trace.py：exit 0，105 check PASS、0 失败，含原有全部断言与 T1–T5。
- T8：新 trace → freeze exit 0；同一案根换回旧算法账本 → freeze exit 2，stderr 含“算法哈希已变化”。
- T6：105 实体、210 锚点，T4 和三策略数量失败均为 0；data_gap 条目 105 → 0，fp_residual 105；非 gap/residual 的策略 raw 变化为 0；指纹变化 118/210。TE-02/TE-04 尘埃字段保持。
- T6 原参数正式跑：exit 2，旧收据 8/10 指纹不匹配；完整 stderr 与拒收原文见 apu_regression.md。118 个变化指纹全部对应旧 data_gap 明细，由调度方核实；CHANGELOG 已写明须重新裁决。
- T7：两版 exit 2，阻断原因文本相同；均落账本，7 实体、14 锚点，T4 数量失败 0。逐终点 raw、逐实体 gap/residual 事件见 pythia_diff.json / pythia_regression.md。

## 4. 命令与结果

| 命令 | 实际结果 | 证据 |
|---|---|---|
| `python3 scripts/tests/changelog_lint.py` | exit 0；补充消费面说明后复检 exit 0 | changelog_lint.log / changelog_lint_followup.log |
| `python3 scripts/tests/docs_lint.py --all` | exit 0；补充文档后复检 exit 0 | docs_lint.log / docs_lint_followup.log |
| `python3 scripts/tests/test_version_consistency.py` | exit 0 | test_version_consistency.log |
| `python3 scripts/tests/invariant_scan.py` | exit 0 | invariant_scan.log |
| `python3 scripts/tests/fixtures_lint.py` | exit 0；裁决后复检 exit 0 | fixtures_lint.log / fixtures_lint_followup.log |
| `python3 scripts/tests/test_entity_source_trace.py` | exit 0；105 check PASS | test_entity_source_trace.log |
| 本机 `python3 scripts/tests/run_all.py` | exit 1；145 PASS / 2 FAIL；未重试 | run_all_eps.log / run_all_eps.exit / run_all_result.json |
| 调度方沙箱外 `python3 scripts/tests/run_all.py` | 全套由调度方沙箱外提供:全部通过(run_all_fable.log)；147/147 PASS | run_all_fable.log |
| `python3 maintenance/repair-20260915-eps-residual/run_followup.py apu` | 子进程 exit 2；旧收据指纹拒收 | apu_formal_followup_result.json / apu_regression.md |
| `python3 maintenance/repair-20260915-eps-residual/run_followup.py pythia` | 子进程 703/704 exit [2, 2] | pythia_run_703_result.json / pythia_run_704_result.json |
| `python3 maintenance/repair-20260915-eps-residual/compare_pythia.py` | exit 0；同输入/退出码/原因及可得数量检查通过 | pythia_diff.json / pythia_regression.md |
| `git diff --check`；受保护文件与范围核对 | exit 0；PASS | final_scope_checks.json |

本机全套仅 test_batch3_solana_vertical_slice.py:625 与 test_batch3_evm_vertical_slice.py:281 在 ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler) 的 socket.bind 处 PermissionError: [Errno 1] Operation not permitted；没有修改断言或绕过环境限制。

已核对调度方 `run_all_fable.log`：147 项均 PASS，末行“全部通过”；`test_batch3_solana_vertical_slice.py` 与 `test_batch3_evm_vertical_slice.py` 均在沙箱外 PASS。全套由调度方沙箱外提供:全部通过(run_all_fable.log)。本次仅读取日志收口，未重跑 run_all。

## 5. 已知未修

- float64 根因未移除；极端累加序列仍可能超过 gap_eps 并记 data_gap。int(float) 截断为 raw="0" 的既有现象未修。
- 冻结生产文件 docstring 的“数量不变”不能作跨版本精确承诺，逐笔短缺同样可能变化；措辞留待下一版本修正，r4 不改生产文件。
- fp_residual 仍属 UNRESOLVED，本版 take 返回的短缺原样入桶并计入未决；非 UNRESOLVED 构成键、gap/residual 合桶量和逐笔短缺按置顶范围判界，没有扩大账户 EPS 或闭合容差。
- 三策略 policy_details 实际变化的锚点，其翻转指纹变化、旧裁决收据失配，须重新裁决（APU 实测 118/210，全部含旧 data_gap）；小供应量 gap_eps==EPS 下真实 data_gap 锚点明细不变，收据仍匹配。旧账本整体 freeze 重放与 --check-unseal 另因算法文件哈希漂移被拒，与收据是否匹配无关；本次不代改收据。
- PYTHIA 历史 q1 data_gap_events=2191 仅信息性并列；不据此声称新旧历史锚点相同，也不输出代币判断。
- 本机 socket.bind 限制仍存在；T6/T7 均已完成，调度方沙箱外全套日志已核对为 147/147 PASS，证据已闭合。未 commit。

## r2 修复记录

### F1 / F2 / F3 改动

- **F1 — 修正数量承诺与 T4**：r2 在当时 `scripts/tests/test_entity_source_trace.py:198–238` 新增通用比较与逐策略检查；其数量界及后续精确承诺均已由 r4 替换为置顶“唯一精确 + 四项界 + pct 界”。既有两组 T4 样例的 Σraw 相同与 gap 拆分相等断言保留。r2 在当时 `:315–360` 新增 `test_eps_residual_mixed()`、`:411` 接入既有入口，7.0.3 对照继续使用 `eps_baseline_script()` 的 `3b29e38` 原文件与既有 CLI 布局。
- **F1 — 文档与真实账本复算**：r2 在 `CHANGELOG.md`、`references/scan-schemas.md`、本文件及两案回归 Markdown 记录每笔短缺数量与两案差 0；其中数量承诺现按 r4b 勘误统一为 stock_raw 唯一精确，非 UNRESOLVED 构成键/合桶量/短缺的双向界及 pct 界，原始标签迁移按 r4b 勘误只记录，见置顶说明。`plan_v2_approved.md` 留存审批历史。
- **F2 — 缩小收据失配范围**：`CHANGELOG.md:93`、本文件 `:124` 改为“三策略 policy_details 实际变化的锚点”；保留 APU 118/210 的实测范围，明确小供应量 gap_eps==EPS 的真实 data_gap 可保持明细及收据匹配，旧账本算法哈希拒收另行成立。
- **F3 — 更正全套结果登记**：`run_all_fable_result.json:2–15` 更新为 `status=PASS`、`pass=147`、`fail=0`、`log=run_all_fable.log`，同步既有 passed/failed/log_file 字段，记录日志哈希、核对时间及 SUITE 顺序匹配。原日志未单列进程退出码，exit_code 保留 null 并解释；本轮没有重跑全套。

### T4-mixed 实测

同日精确顺序：`X→A 2^60`、`X→A 1`、`A→D 2^60`；供应量 `10·2^90`。以下结果在 current、peak 两锚点均成立。`stock_raw` 由整数边表独立核算、三策略共用；账本主构成为 pro_rata。

| 策略 | stock_raw（两版） | Σraw 7.0.3 | Σraw 7.0.4 | 差值 / residual raw 7.0.4 | 闭合 pct（两版） |
|---|---|---|---|---|---|
| pro_rata | 2^60 | 2^60 | 2^60+1 | 1 / 1 | 100.0 |
| fifo | 2^60 | 2^60 | 2^60 | 0 / 0 | 100.0 |
| lifo | 2^60 | 2^60 | 2^60+1 | 1 / 1 | 100.0 |

裁决第 3 条的 `7.0.4 合计=2^60+1` 落在账本主构成；FIFO 先取走大额层，1 raw 残差留在 A，因此其 D 锚点差 0。此策略差异与盲审 R1 原表、原命令复现一致，未改生产代码以制造三策略相同的合计。

### 测试命令、退出码与原始输出

以下七项由 `python3 -B maintenance/repair-20260915-eps-residual/run_checks_r2.py` 执行，调度脚本 exit 0；对子进程设置 `PYTHONDONTWRITEBYTECODE=1`。结果及被测文件哈希见 `check_results_r2.json`，调度日志见 `run_checks_r2.log`。

| 命令 | 退出码 | 输出文件 |
|---|---:|---|
| `python3 -B scripts/tests/test_entity_source_trace.py` | 0；200 check PASS、0 FAIL | test_entity_source_trace_r2.log |
| `python3 -B scripts/tests/test_version_consistency.py` | 0 | test_version_consistency_r2.log |
| `python3 -B scripts/tests/changelog_lint.py` | 0 | changelog_lint_r2.log |
| `python3 -B scripts/tests/docs_lint.py --all` | 0 | docs_lint_r2.log / docs_lint_final_r2.log |
| `python3 -B scripts/tests/invariant_scan.py` | 0 | invariant_scan_r2.log |
| `python3 -B scripts/tests/fixtures_lint.py` | 0 | fixtures_lint_r2.log |
| `git diff --check` | 0 | git_diff_check_r2.log / git_diff_check_final_r2.log |

- 既有 69 处 check 调用的断言表达式全部保留；原日志 105 项通过检查在本轮全部执行并通过，新增 T4-mixed 51 项通过检查，其余新增检查覆盖通用 T4 的主构成及逐策略不变量。见 `assertion_preservation_r2.json`。
- `python3 -B maintenance/repair-20260915-eps-residual/r1_reproduction_r2.py`：exit 0，逐字提取盲审 R1 的 Python 代码，仅内存复现 mixed / small_flip；见 `r1_reproduction_r2.log`、`precheck_results_r2.json`。写 CHANGELOG 前的 lint 同为 exit 0，见 `changelog_lint_before_r2.log`。
- `python3 -B maintenance/repair-20260915-eps-residual/verify_existing_evidence_r2.py`：exit 0，只读四份已落盘账本；APU 210 + PYTHIA 14 = 224 锚点合计差 0，当时检查失败 0（r3 已按新裁决的界重新只读复核）；非零库存锚点可得三策略共 666 组比较通过（630 + 36），另 2 个零库存锚点未输出策略明细。四份账本 SHA-256 前后相同；见 `ledger_recheck_r2.json`、`existing_evidence_r2.log`。同一命令只读核对既有 Fable 全套日志的 147 PASS、0 FAIL 与 SUITE 顺序，再更新 F3 JSON。
- `python3 -B maintenance/repair-20260915-eps-residual/verify_scope_r2.py`：exit 0；相对施工前冻结的 1062 个文件，既有文件只改本轮七个指定文件，无越界改动或删除，新增文件均在工单目录且带 `_r2` 后缀；见 `scope_before_r2.json`、`scope_after_r2.json`、`scope_verification_r2.log`。文档收尾复检与退出码另见 `final_checks_r2.json`。
- HEAD 仍为 `2000b6e78f790ee0ed348cc2ecb8eae796d5136e`，分支仍为 main；生产 `entity_source_trace.py` SHA-256 仍为 `e85acee4e9a98a664d9b4881ca33177003aa9455261109a01e111e6faeda3cd1`。受保护代码、测试、fixture、版本文件及原裁决/计划均未作 r2 改动；全程离线，未读取禁用归档目录或禁用 tag，未重跑 APU/PYTHIA，未 commit。

**r2 原交付记录：COMPLETE，七项指定检查退出码全部为 0；随后盲审 r2 推翻 F1 的数量界，转入本文件 r3 修复记录处置。**

## r3 修复记录

### 裁决与改动文件

历史记录：r3 依据 `r2_fix_ruling.md` 施工，随后 `blind_review_r3.md` 的 A/B 反例推翻其逐笔短缺与非 UNRESOLVED raw 的精确承诺。当前有效范围以置顶 r4b 说明及 `r3_fix_ruling.md` 勘误为准。r3 使用的 `abs(Δ) * 2**52 <= 4*n*S + 2*2**52` 判界形式保留，现按 r4b 勘误用于非 UNRESOLVED 构成键、合桶量和逐笔短缺；原始 r3 证据文件未改。

| 文件与当前行 | r3 改动 |
|---|---|
| `scripts/tests/test_entity_source_trace.py:198–317` | 新界函数、真实双版本内存模拟与逐笔短缺旁录；当时通用 T4 的精确比较与主构成/三策略舍入界（精确承诺现已撤回）。 |
| `scripts/tests/test_entity_source_trace.py:349,391,398–409` | 既有 T4 两例及 T4-mixed 传入同一边表作为 n；既有具体断言保留。 |
| `scripts/tests/test_entity_source_trace.py:443–544,596–597` | 新增并接入 T4-mixed-b、T4-stress。 |
| `CHANGELOG.md:92–94` | 当时登记精确承诺与双向舍入界（数量承诺现由 r4 接替）；注明 docstring 解释及下一版修词待办；登记新增测试。 |
| `references/scan-schemas.md:329–330` | §4 当时登记 Δ/n/S 与双向界（精确承诺现由 r4 接替）。 |
| `maintenance/repair-20260915-eps-residual/apu_regression.md:3,249` | 210 锚点、630 组策略按新界只读复核；明确逐笔短缺不在既有账本中。 |
| `maintenance/repair-20260915-eps-residual/pythia_regression.md:3` | 14 锚点、36 组策略按新界只读复核；说明两个零库存锚点无策略明细。 |
| `maintenance/repair-20260915-eps-residual/done.md:3,5,123,133–134,166,170,172` | 替换数量承诺，标明 r2 记录被新裁决接替，登记 docstring 已知未修并追加本节。 |
| `maintenance/repair-20260915-eps-residual/verify_existing_evidence_r3.py:1–100` | 新增四份账本只读复算器，仅写 r3 证据。 |
| `maintenance/repair-20260915-eps-residual/run_checks_r3.py:1–48` | 新增七项检查调度、原始日志、退出码与哈希登记。 |
| `maintenance/repair-20260915-eps-residual/verify_scope_r3.py:1–92` | 新增范围、断言保留、日志绑定、HEAD 与输入哈希核验。 |

原始 69 处 check 表达式全部保留；r2 的 84 处中，仅按裁决替换两处通用旧界，其余 82 处全部保留，当前共 100 处。原日志 105 项检查全部重新执行通过；r2 的 200 项中，撤销旧界对应 24 项，其余 176 项全部重新执行通过。完整测试共 **7492 check PASS、0 FAIL**；见 `assertion_preservation_r3.json`，本轮测试差分另存 `test_change_r3.patch`。

### T4-mixed-b 实跑

同日精确顺序 `X→A 2^60`、`X→A 129`、`A→D 2^60`，供应量 `10·2^90`。以下结果在 current、peak 均成立；两版 stock_raw 均为 `2^60`，三策略按 raw 复算闭合 pct 均为 `100.0`，主构成展示值同为 `100.0`，全部在新界内。

| 策略 | 7.0.3 gap raw | 7.0.4 gap raw | 7.0.4 residual raw | Δ |
|---|---:|---:|---:|---:|
| pro_rata | 2^60 | 2^60−256 | 128 | −128 |
| fifo | 2^60 | 2^60 | 0 | 0 |
| lifo | 2^60 | 2^60−128 | 129 | +1 |

实跑值与裁决建议一致；主构成合计明确断言为旧版 `2^60`、新版 `2^60−128`。原 T4-mixed（第二笔 1 raw）及两组旧 T4 样例同时通过。

### T4-stress 实测

- 固定种子 `20260915`，**200 组**、每组 **3–8 边**，两版真实 `trace_entity()` 在内存 HUGEINT 边表上执行；三策略 × 两锚点共 **1200 组比较**。账户旁录仅委托真实实现并以 float.hex 保留逐笔短缺的所有位；未替换数值计算。
- 大短缺采样 `2^50…2^62`，小短缺采样 `1…4096`（本次抽到 `33…4086`）；供应量 `10·2^90`。74 组另有非空 mint 构成；库存额外与独立整数边表余额逐锚点核对。
- **max|Δ| = 788 raw；出现 2 次；超界次数 0。** 出现次数按上述 1200 个策略锚点计：case 101、n=8、pro_rata 的 current 与 peak，Δ 均为 `−788`。负差 360 次、正差 270 次、差 0 共 570 次；当轮旧通用精确比较失败 0（其承诺随后被盲审 r3 反证）。
- 结果来自最终指定测试日志 `test_entity_source_trace_r3.log` 的 `T4_STRESS_SUMMARY`，可读摘要及日志哈希见 `t4_stress_summary_r3.json`；先行定向试跑另存 `t4_stress_probe_r3.log`。

### APU / PYTHIA 只读复核

`python3 -B maintenance/repair-20260915-eps-residual/verify_existing_evidence_r3.py` 退出 **0**。从四份原有账本读取两版相同的供应量及各实体 `simulation.edges_simulated`，以整数交叉相乘重新检查每个主构成和每组可得策略明细，未运行两案 trace。

| 案例 | 锚点 | 策略比较 | 最大绝对差 raw | 超界 | n 范围 |
|---|---:|---:|---:|---:|---:|
| APU | 210 | 630 | 0 | 0 | 2–576383 |
| PYTHIA | 14 | 36 | 0 | 0 | 3978561–4816134 |
| 合计 | 224 | 666 | 0 | 0 | — |

全部 stock_raw、非 gap/residual 来源 raw、主构成闭合 pct 展示值相同，合计差全为 0；PYTHIA 另 2 个零库存锚点没有策略明细。既有账本不含逐笔短缺入桶轨迹，该项由 T4 合成测试覆盖。四份账本哈希与施工前冻结值逐一相同；证据见 `ledger_recheck_r3.json`、`existing_evidence_r3.log`。

### 七项命令与退出码

以下由 `python3 -B maintenance/repair-20260915-eps-residual/run_checks_r3.py` 执行，调度脚本退出 **0**，对子进程设置 `PYTHONDONTWRITEBYTECODE=1`。命令、耗时、日志 SHA-256 与被测文件 SHA-256 见 `check_results_r3.json`，逐项调度输出见 `run_checks_r3.log`。

| 命令 | 退出码 | 原始输出 |
|---|---:|---|
| `python3 -B scripts/tests/test_entity_source_trace.py` | 0 | `test_entity_source_trace_r3.log` |
| `python3 -B scripts/tests/test_version_consistency.py` | 0 | `test_version_consistency_r3.log` |
| `python3 -B scripts/tests/changelog_lint.py` | 0 | `changelog_lint_r3.log` |
| `python3 -B scripts/tests/docs_lint.py --all` | 0 | `docs_lint_r3.log` |
| `python3 -B scripts/tests/invariant_scan.py` | 0 | `invariant_scan_r3.log` |
| `python3 -B scripts/tests/fixtures_lint.py` | 0 | `fixtures_lint_r3.log` |
| `git diff --check` | 0 | `git_diff_check_r3.log` |

写 CHANGELOG 前的 lint 退出 0，见 `changelog_lint_before_r3.log`。本段落盘后的文档/差分复检见 `final_checks_r3.json`、`docs_lint_final_r3.log`、`git_diff_check_final_r3.log`；最终范围核验见 `scope_before_r3.json`、`scope_after_r3.json`、`scope_verification_r3.log`。

### 范围与终态

- 相对本轮施工前冻结的 **1092 个文件**，仅改变上表六个既有白名单文件，新增脚本与证据均位于工单目录、文件名带 `_r3`；无删除或越界变更。
- 分支仍为 `main`，HEAD 仍为 `2000b6e78f790ee0ed348cc2ecb8eae796d5136e`，工作树版本仍为 `7.0.4`；既有未提交生产与版本改动保留，本轮未 commit。
- `scripts/report/entity_source_trace.py` SHA-256 仍精确等于 `e85acee4e9a98a664d9b4881ca33177003aa9455261109a01e111e6faeda3cd1`。其 docstring 措辞留待下一版本修正，已列入已知未修。
- 全程离线；未读取用户禁用的归档目录或 tag；未重跑全套、APU 或 PYTHIA；旧裁决、F2/F3 收据及全套结果文件未改动。

**r3 原交付记录：COMPLETE，七项指定命令退出码全为 0；随后盲审 r3 的 A/B 反例推翻 F1 的精确承诺，转入下文 r4 修复记录。该历史状态不代表 r4 已完成。**


## r4 修复记录

### 结论与裁决范围

**r4 历史终态：BLOCKED。** 当时将裁决①“每条构成 raw”按原始标签分别判界，300 组压力测试记录 **684 次原始标签逐键“超界”**。该历史数值及原始日志如实保留。后续 `r3_fix_ruling.md` 勘误已明确：原始 data_gap/fp_residual 标签差是标签迁移量，只记录、不判界；这 684 次不计 r4b 数量界失败。r4b 继续保留 A/B 与既有具体断言，重跑结果见文末。

现行勘误后的数量要求完整登记于本文置顶、CHANGELOG 7.0.4 与 scan-schemas §4：stock_raw 唯一精确；非 UNRESOLVED 构成键逐键 raw、gap/residual 合桶量、Σraw、逐笔短缺检查 |Δ|≤B，B=4·n·2^-52·S+2；stock>0 的闭合 pct 差检查 B/stock×100；展示值不承诺相同；计数、policy_details、翻转指纹不承诺不变。改标签在 float 之上会对全部构成产生 ulp 级扰动，7.0.3 与 7.0.4 都是浮点近似，无优劣。原始标签迁移与该数值扰动分别披露；F2 的“实际变化的锚点收据失配”范围保留。

### 改动文件与行

| 文件与当前行 | r4 改动 |
|---|---|
| `scripts/tests/test_entity_source_trace.py:198,258` | 整数/有理数判界；逐键 raw、UNRESOLVED 合计、Σraw、逐笔短缺、raw 复算 pct 与展示 pct 界；缺席键按 0 对齐。float.hex 旁录转 Fraction 保留短缺差的全部位。 |
| `scripts/tests/test_entity_source_trace.py:507–552,710–711` | 新增 T4-mixed-c（A）、T4-mixed-d（B）及入口；按真实两版实现的实跑值断言并输出 JSON。 |
| `scripts/tests/test_entity_source_trace.py:555` | 固定种子 300 组，mint/外部转入可落中间账户，允许超余额转出；分键类记录最大差与超界次数，超界保留 FAIL。 |
| `CHANGELOG.md:92–95` | 替换旧精确承诺；登记全部数量及 pct 界、两版无优劣、计数/明细/指纹可变，以及原始标签口径的实测超界。 |
| `references/scan-schemas.md:328–331` | §4 同步最终要求，解释本版短缺原样入桶不代表两版短缺相同，区分原始标签迁移和合桶后的数量。 |
| `maintenance/repair-20260915-eps-residual/apu_regression.md:3,249` | 210 锚点与 630 组策略的全部原始键、合桶键、合计和 pct 只读复核。 |
| `maintenance/repair-20260915-eps-residual/pythia_regression.md:3` | 14 锚点与 36 组策略的全部键只读复核，两个零库存锚点不作 pct 除零。 |
| `maintenance/repair-20260915-eps-residual/done.md:3,5,12,123–124,133–134,176–184,213,248,251` | 修正承诺与历史状态，撤回生产 docstring 的旧解释，追加本节。 |
| `maintenance/repair-20260915-eps-residual/verify_existing_evidence_r4.py:1` | 新增四份账本全部键的独立有理数复核器，只写 r4 证据。 |
| `maintenance/repair-20260915-eps-residual/run_checks_r4.py:1` | 七项命令、退出码、原始日志、耗时及 SHA-256 登记。 |
| `maintenance/repair-20260915-eps-residual/verify_scope_r4.py:1` | 白名单、断言保留、日志绑定、HEAD、生产与账本哈希核验；区分范围 PASS 和测试 FAIL。 |
| `maintenance/repair-20260915-eps-residual/reproduce_label_migration_r4.py:1` | 从最终压力日志提取最大超界见证，只读内存重放并披露两版原始标签及合桶值。 |

原始 **69 处 check** 表达式全部保留；原日志 **105 项**检查全部重执行通过。r3 的 100 处 check 中按本轮授权替换 4 处通用精确比较，并把压力组数文案从 200 改为 300，其余 95 处保留；当前共 109 处。`test_eps_residual()`、`test_eps_residual_mixed()`、`test_eps_residual_mixed_b()` 的完整函数 AST 均与施工前相同。最终测试为 **21472 check PASS、685 FAIL**：684 个原始 UNRESOLVED 标签逐键超界，加 1 个“超界次数为零”汇总断言。见 assertion_preservation_r4.json、test_change_r4.patch；没有删去失败样本或改生产实现凑通过。

### 反例 A / B 两版实跑值

两例共同前三笔为 `X→A H, Z→A H, X→A 257`，H=2^60，S=10·2^90；第四笔 A 为 `A→D H`，B 为 `A→D 2H+512`。全部同日、顺序精确。下面锚点结果在 current、peak 均成立；n=4，B=43980465111042 raw，两例各项均在界内。

| 反例 / 字段 | 7.0.3 | 7.0.4 |
|---|---:|---:|
| A / 主策略 mint raw | 576460752303423488 | 576460752303423360 |
| A / 主策略 Σraw | 1152921504606847104 | 1152921504606846848 |
| A / stock_raw | 1152921504606846976 | 1152921504606846976 |
| A / 最后一笔 pro_rata 短缺 | 0 | 0 |
| B / 主策略 mint raw | 1152921504606846976 | 1152921504606846976 |
| B / 主策略 Σraw | 2305843009213694720 | 2305843009213694209 |
| B / stock_raw | 2305843009213694464 | 2305843009213694464 |
| B / 最后一笔 pro_rata 短缺 | 512 | 0 |
| B / 最后一笔 fifo 短缺 | 255 | 255 |
| B / 最后一笔 lifo 短缺 | 0 | 0 |
| A 与 B / 主构成闭合展示 pct | 100.0 | 100.0 |

A 的主策略 mint Δ=-128，UNRESOLVED 合计三策略差为 pro_rata=-128、fifo=0、lifo=0；B 为 pro_rata=-511、fifo=0、lifo=+1。逐笔短缺以 float.hex 保留原值；完整 current/peak、三策略差、边表与日志绑定见 t4_counterexamples_r4.json（来自最终 test_entity_source_trace_r4.log）。

### T4-stress 分键类实测

- 固定种子 **20260915**，**300 组**、每组 **3–8 边**；S=12379400392853802748991242240 raw。两版真实 trace_entity 在内存 HUGEINT 边表上运行，未替换数值算法。
- 三策略×两锚点共 **1800** 组策略比较；加主构成后，每个合计类共有 **2400** 次比较。stock_raw 逐锚点另与独立整数边表余额核对，全部相同。
- 116 组有 mint，其中 **91 组 mint 进入中间账户**；**300 组外部转入中间账户**，**158 组出现超余额转出**。大额采样 2^50…2^62，小额实抽 2…4081 raw。

| 键类 / 数量 | 比较次数 | max\|Δ\| | 单位 | 超界次数 |
|---|---:|---:|---|---:|
| UNRESOLVED 合计（gap704+residual704 对 gap703） | 2400 | 1536 | raw | 0 |
| 非 UNRESOLVED 构成键 | 866 | 32 | raw | 0 |
| 逐笔短缺 | 4761 | 1024 | raw | 0 |
| 构成 Σraw | 2400 | 1536 | raw | 0 |
| 原始 UNRESOLVED 标签迁移（r4 当时分别套界） | 4558 | 2251799813685574 | raw | **684（历史值；现仅记录）** |
| raw 复算闭合 pct | 2400 | 5/22517998136858 | pct | 0 |
| 主构成闭合展示 pct | 600 | 0 | pct | 0 |

表中 raw/pct 判界分别使用 B 和 B/stock×100，未在 float 上计算或放宽界。完整分键类见证、输入覆盖和最终日志 SHA-256 见 t4_stress_summary_r4.json；先行试跑保留于 t4_stress_probe_r4.log。

**最大标签迁移见证（r4 当时套界）：case 270，n=8，current/fifo（peak 同样）。** B=87960930222082 raw。两版 gap raw 为 16466286137573640 → 14214486323888066，Δ=-2251799813685574，约为 -25.6B；新版 residual=2251799813685573。gap/residual 合桶后的 Δ=-1，stock_raw 两版均为 16466286137573639。大差来自原始标签迁移，不能将它称为 ulp 级数量误差，也不能据合桶后的界通过宣称原始逐键测试通过。

离线复现命令：`python3 -B maintenance/repair-20260915-eps-residual/reproduce_label_migration_r4.py`，实际退出 **1**（成功复现原始逐键超界），原始输出见 label_migration_reproduction_r4.log；脚本从最终压力日志提取边表并重新运行两版真实实现。

### APU / PYTHIA 224 锚点全部键只读复核

`python3 -B maintenance/repair-20260915-eps-residual/verify_existing_evidence_r4.py` 退出 **0**。从四份原有账本读取相同的供应量及各实体 simulation.edges_simulated，独立用整数/Fraction 检查所有主构成与三策略原始键、合桶对齐键、UNRESOLVED 合计、Σraw 和 pct，未重跑两案 trace。

| 案例 | 锚点 | 策略明细 | 原始键比较 | 合桶对齐键比较 | 原始键 max\|Δ\| raw | 对齐键 max\|Δ\| raw | 超界 |
|---|---:|---:|---:|---:|---:|---:|---:|
| APU | 210 | 630 | 10034 | 9716 | 478750745388 | 0 | 0 |
| PYTHIA | 14 | 36 | 482 | 451 | 0 | 0 | 0 |
| 合计 | 224 | 666 | 10516 | 10167 | — | 0 | 0 |

两案 stock_raw 全部精确相同；非 UNRESOLVED raw、UNRESOLVED 合计、Σraw、闭合 pct 实测差均为 0。APU 原始标签的 616 个非零变化位置另列，不能写成原始逐键差全为 0。n 范围分别为 2–576383 与 3978561–4816134，B/S≤4.3e-9；PYTHIA 两个零库存锚点不除以零，raw 仍已覆盖。四份账本 SHA-256 与施工前逐一相同。逐键两版 raw、Δ、界、输入绑定和哈希见 ledger_recheck_r4.json / existing_evidence_r4.log；原账本不含逐笔短缺轨迹，该项的覆盖来自合成 T4。

### 七项命令与退出码

以下由 `python3 -B maintenance/repair-20260915-eps-residual/run_checks_r4.py` 执行，调度脚本退出 **1**；七项全部执行并保留原始输出。子进程环境 PYTHONDONTWRITEBYTECODE=1；命令、耗时、日志与被测文件 SHA-256 见 check_results_r4.json / run_checks_r4.log。

| 命令 | 退出码 | 原始输出 |
|---|---:|---|
| `python3 -B scripts/tests/test_entity_source_trace.py` | **1** | test_entity_source_trace_r4.log |
| `python3 -B scripts/tests/test_version_consistency.py` | 0 | test_version_consistency_r4.log |
| `python3 -B scripts/tests/changelog_lint.py` | 0 | changelog_lint_r4.log |
| `python3 -B scripts/tests/docs_lint.py --all` | 0 | docs_lint_r4.log |
| `python3 -B scripts/tests/invariant_scan.py` | 0 | invariant_scan_r4.log |
| `python3 -B scripts/tests/fixtures_lint.py` | 0 | fixtures_lint_r4.log |
| `git diff --check` | 0 | git_diff_check_r4.log |

本节落盘后的文档/差分复检见 final_checks_r4.json、docs_lint_final_r4.log、git_diff_check_final_r4.log；范围及断言证据见 scope_before_r4.json、scope_after_r4.json、scope_verification_r4.log、assertion_preservation_r4.json。范围 PASS 仅表示未越界与证据绑定正确，不替代测试退出码 1。

### 范围与终态

- 相对施工前冻结的 **1122 个文件**，仅修改上述六个既有白名单文件；新增脚本/证据均在本工单目录且文件名带 `_r4`。无删除、无越界文件改动。
- main / HEAD `2000b6e78f790ee0ed348cc2ecb8eae796d5136e` / 工作树 VERSION `7.0.4` 均保持，既有未提交生产与版本改动保留，本轮未 commit。
- `scripts/report/entity_source_trace.py` SHA-256 仍为 `e85acee4e9a98a664d9b4881ca33177003aa9455261109a01e111e6faeda3cd1`；四份输入账本哈希未变。
- 全程离线；未读禁用的归档目录或 tag；未重跑全套/APU/PYTHIA；未改生产代码、handoff_manifest.py、受保护测试、fixture、旧裁决和旧结果文件。

**r4 历史终态：BLOCKED。原始标签的 684 次“超界”现按勘误归为标签迁移记录，不再算数量界失败；原 r4 日志与退出码保持历史原样。r4b 按其余判界和七项实跑结果收口，见后续记录。**

## r4b 续工记录

### 终态与勘误落实

**终态：COMPLETE。** 按 `r3_fix_ruling.md` 末尾“## 勘误”落实键对齐口径：**非 UNRESOLVED 构成键逐键判界；data_gap/fp_residual 合桶后判界；原始标签逐键差仅记录为标签迁移量，不判界。** stock_raw 精确比较、Σraw、逐笔短缺、pct 的界及既有具体断言均保留，B=4·n·2^-52·S+2 未放宽。r4 历史记录的 684 次原始标签“超界”如实保留，现归为标签迁移历史，不计 r4b 数量界失败。

### 改动文件与行

| 文件与当前行 | r4b 改动 |
|---|---|
| `scripts/tests/test_entity_source_trace.py:258–286` | 原始 UNRESOLVED 标签逐条输出 T4_LABEL_MIGRATION，保留 key、两版 raw、Δ，标记 bound_checked=false；不调用判界。非 UNRESOLVED 键仍逐键判界。 |
| `scripts/tests/test_entity_source_trace.py:547` | A/B 结果汇总只计实际判界的失败；具体预期值保持。 |
| `scripts/tests/test_entity_source_trace.py:635–661` | 分键类区分判界次数与仅记录项；迁移类 bounded_comparisons=0、out_of_bound_count=null，汇总失败仅包含承诺范围。 |
| `CHANGELOG.md:92–95` | 写明非 UNRESOLVED 逐键和 gap/residual 合桶范围，原始标签只记录；r4 的 684 次改为历史迁移记录。 |
| `references/scan-schemas.md:329–331` | §4 同步勘误口径与验证范围，保留 pct/计数/明细/指纹不承诺及两版无优劣。 |
| `maintenance/repair-20260915-eps-residual/done.md:3,5,12,124,134,176,255,257,310,316,355` | 置顶改为 r4b 有效范围；r4 BLOCKED 明确为历史结果，保留原始日志/数值，追加本节。 |
| `maintenance/repair-20260915-eps-residual/run_checks_r4b.py:1` | 新七项调度与 `_r4b` 日志、退出码、耗时、文件/日志 SHA-256。 |
| `maintenance/repair-20260915-eps-residual/verify_scope_r4b.py:1` | 四文件白名单、断言、固定输入、标签记录、其余判界、七项证据绑定与现有账本哈希核验。 |

原始 **69 处 check**、r4 的 **109 处 check** 表达式全部保留；五个具体样例函数（两组旧 T4 所在 test_eps_residual、mixed、mixed-b、mixed-c、mixed-d）的完整 AST 未变。原日志 105 项检查全部执行通过。r4 原始标签的 **4632 次执行**逐项转换为迁移记录，记录与旧判界位置一一对应；其余旧通过项全部再次通过。最终指定测试为 **17525 check PASS、0 FAIL**。见 assertion_preservation_r4b.json、ruling_scope_review_r4b.json 与 test_change_r4b.patch。

### T4-stress 与 A/B 实跑

固定种子仍为 **20260915**，**300 组**、每组 **3–8 边**、S=10·2^90；压力测试生成器和输入循环 AST 与 r4 完全相同，未换样本。116 组含 mint，其中 91 组进入中间账户；300 组外部转入中间账户；158 组超余额转出。两版 stock_raw 与独立整数边表余额全部相同。

| 键类 / 数量 | 比较或记录次数 | max\|Δ\| | 单位 | 判界结果 |
|---|---:|---:|---|---|
| gap/residual 合桶量 | 2400 | 1536 | raw | 超界 0 |
| 非 UNRESOLVED 构成键 | 866 | 32 | raw | 超界 0 |
| 逐笔短缺 | 4761 | 1024 | raw | 超界 0 |
| 构成 Σraw | 2400 | 1536 | raw | 超界 0 |
| raw 复算闭合 pct | 2400 | 5/22517998136858 | pct | 超界 0 |
| 主构成闭合展示 pct | 600 | 0 | pct | 超界 0 |
| 原始 UNRESOLVED 标签迁移 | 4558 | 2251799813685574 | raw | 仅记录，不判界 |

全部受约束项超界 **0**。迁移类有 **4270** 个非零差位置；不把未判界写成“超界 0”。各类比较次数和最大差与 r4 完全相同，变化仅为勘误规定的承诺范围。三策略×两锚点共 1800 组策略比较，表中合计类另含主构成，故为 2400；全部逐条迁移记录在 test_entity_source_trace_r4b.log 的 T4_LABEL_MIGRATION 行，分键类摘要见 t4_stress_summary_r4b.json。

A/B 两版实跑值与 r4 完全一致，current/peak 均通过；完整证据见 t4_counterexamples_r4b.json：

| 反例 / 字段 | 7.0.3 | 7.0.4 |
|---|---:|---:|
| A / 主策略 mint raw | 576460752303423488 | 576460752303423360 |
| A / 最后一笔 pro_rata 短缺 | 0 | 0 |
| B / 主策略 mint raw | 1152921504606846976 | 1152921504606846976 |
| B / 最后一笔 pro_rata 短缺 | 512 | 0 |

两例 stock_raw 两版相同，主构成闭合展示 pct 本次均为 100.0；这仍是具体样例实测，不扩展为通用展示值不变承诺。

### 既有 224 锚点证据复核

本轮复用哈希冻结的 ledger_recheck_r4.json 中两版原始 raw，按勘误重新计算非 UNRESOLVED 逐键、gap/residual 合桶、Σraw、pct 的界，并核对四份现存账本的 SHA-256。未重跑 APU/PYTHIA trace，未改两案回归文件或原始证据。

APU 210 锚点、630 组策略与 PYTHIA 14 锚点、36 组策略，共 **224 锚点、666 组策略**；stock_raw 相同，受约束数量差均为 0，超界 0。原始 UNRESOLVED 标签只记录：APU 有 616 个非零迁移位置，最大迁移量 478750745388 raw；这些原始标签量不参与判界。证据来源 SHA-256、重算结果与四份输入哈希核验见 ruling_scope_review_r4b.json 的 ledger_scope_review。

### 七项命令与退出码

`python3 -B maintenance/repair-20260915-eps-residual/run_checks_r4b.py` 实际退出 **0**。子进程 PYTHONDONTWRITEBYTECODE=1，七项全部实际运行；原始输出、命令、耗时、退出码、日志及被测文件 SHA-256 见 check_results_r4b.json / run_checks_r4b.log。

| 命令 | 退出码 | 原始输出 |
|---|---:|---|
| `python3 -B scripts/tests/test_entity_source_trace.py` | 0 | test_entity_source_trace_r4b.log |
| `python3 -B scripts/tests/test_version_consistency.py` | 0 | test_version_consistency_r4b.log |
| `python3 -B scripts/tests/changelog_lint.py` | 0 | changelog_lint_r4b.log |
| `python3 -B scripts/tests/docs_lint.py --all` | 0 | docs_lint_r4b.log |
| `python3 -B scripts/tests/invariant_scan.py` | 0 | invariant_scan_r4b.log |
| `python3 -B scripts/tests/fixtures_lint.py` | 0 | fixtures_lint_r4b.log |
| `git diff --check` | 0 | git_diff_check_r4b.log |

本节落盘后的文档/差分复检见 final_checks_r4b.json、docs_lint_final_r4b.log、git_diff_check_final_r4b.log；最终范围及哈希核验见 scope_before_r4b.json、scope_after_r4b.json、scope_verification_r4b.log、ruling_scope_review_r4b.json。

### 范围与终态

- 施工前冻结 **1153 个文件**，本轮仅修改测试、CHANGELOG、scan-schemas 和 done.md 四个既有白名单文件；新增脚本与证据均在工单目录且文件名带 `_r4b`。没有删除或越界修改，勘误文件及原 `_r4` 证据文件均保持本轮起点哈希。
- 分支 main、HEAD `2000b6e78f790ee0ed348cc2ecb8eae796d5136e`、工作树 VERSION `7.0.4` 不变；本轮不 commit。
- 生产 `scripts/report/entity_source_trace.py` SHA-256 仍为 `e85acee4e9a98a664d9b4881ca33177003aa9455261109a01e111e6faeda3cd1`；四份原始账本哈希不变。
- 全程离线；未读取禁用归档目录或 tag；未重跑全套/APU/PYTHIA，未改生产代码、受保护测试或 fixture。

**r4b 终态：COMPLETE。勘误范围已落实；300 组压力测试受约束项超界 0，七项指定命令退出码全为 0，既有具体断言、原始标签迁移记录、范围及生产/账本哈希核验通过。**

## r5 收尾记录

**终态：COMPLETE。** M1/M3/N2/N3/N4 已处理；本节记录 r5 结果，前文 r4/r4b 记录保留为历史。M2/N1 按本工单列为已知未处理。

### 改动

| 项目 | 文件 | r5 改动 |
|---|---|---|
| M1 | `CHANGELOG.md:13` | 改为“短缺入桶不丢弃（逐笔短缺值本身有舍入界，见详细段）”，与 T4-mixed-d 的 512→0 一致。 |
| M3 | `scripts/tests/test_entity_source_trace.py` | 仅实际合桶的 `UNRESOLVED/data_gap`、`UNRESOLVED/fp_residual` 原始键记录标签迁移；其余 UNRESOLVED 键与非 UNRESOLVED 键一样逐键判界，覆盖主构成与三策略、current/peak。 |
| N2 | `done.md:7` | “T6 数量不变量通过”改为“T6 有界差分通过”。 |
| N3 | `pythia_regression.md` | e_lp 行增加脚注：事件计数不承诺不变，拆桶舍入使部分边界短缺落到 EPS 以下而不再产生事件，因此 3+11139=11142，比旧计数 11145 少 3 次。 |
| N4 | `CHANGELOG.md` 7.0.4 详细段、`references/scan-schemas.md` §4 | 在 B 界定义后补充“单笔转账金额不超过总供应量”的域假设；`r3_fix_ruling.md` 保持原样。 |

### 验证与退出码

`python3 -B maintenance/repair-20260915-eps-residual/run_checks_r5.py` 退出 **0**。子进程设置 `PYTHONDONTWRITEBYTECODE=1`；七项命令、退出码、耗时、文件和日志 SHA-256 见 `check_results_r5.json` / `run_checks_r5.log`。

| 命令 | 退出码 | 原始日志 |
|---|---:|---|
| `python3 -B scripts/tests/test_entity_source_trace.py` | 0 | `test_entity_source_trace_r5.log` |
| `python3 -B scripts/tests/test_version_consistency.py` | 0 | `test_version_consistency_r5.log` |
| `python3 -B scripts/tests/changelog_lint.py` | 0 | `changelog_lint_r5.log` |
| `python3 -B scripts/tests/docs_lint.py --all` | 0 | `docs_lint_r5.log` |
| `python3 -B scripts/tests/invariant_scan.py` | 0 | `invariant_scan_r5.log` |
| `python3 -B scripts/tests/fixtures_lint.py` | 0 | `fixtures_lint_r5.log` |
| `git diff --check` | 0 | `git_diff_check_r5.log` |

- 指定测试 **17525 check PASS、0 FAIL**，包含 T4 T1、多来源、mixed、mixed-b、mixed-c、mixed-d 及全部 T4-stress；T4-mixed-d 的逐笔短缺仍为 **512→0**。反例原始摘要见 `t4_counterexamples_r5.json`。
- T4-stress 固定种子 **20260915**、**300 组**、三策略×两锚点 **1800 组**策略比较；合桶量/非 UNRESOLVED 键/逐笔短缺的 max|Δ| 仍为 **1536/32/1024 raw**，受约束项超界 **0**。`B=4·n·2^-52·S+2`、样本参数和既有具体断言均未修改。摘要见 `t4_stress_summary_r5.json`。
- 原有压力样本中的 UNRESOLVED 原始键均为 gap/residual，4558 条迁移记录仍不逐键判界；其他子类的比较器行为另用 `m3_comparator_probe_r5.py` 验证，退出 **0**。保持 stock_raw、Σraw、合桶量和 pct 不变，仅在 order_ambiguous/depth_limit/budget_truncated/facility_candidate 之间转移 raw：四组界内 +2 控制通过，八组 ±3 超界注入均被新比较器拒绝，旧比较器均误放；gap/residual 纯标签迁移仍通过，共 **13 例**。这些人为注入是预期拒绝探针，不是 T4 实跑的超界。证据见 `m3_comparator_probe_r5.log`。
- 仅 `eps_compare_quantities` 函数 AST 改变；109 处既有 `check` 表达式全部保留，判界函数、全部具体样例和压力生成器 AST 均不变。
- 本节落盘后再次运行 `docs_lint --all`、`git diff --check`，退出码均为 **0**；见 `final_checks_r5.json`、`docs_lint_final_r5.log`、`git_diff_check_final_r5.log`。

### 已知未处理

- **M2**：压力样本总供应量远大于单笔金额，现有界断言对紧界的鉴别力不足；本轮不补同量级样本、不修改压力参数，也不以压力通过宣称已解决该问题。
- **N1**：冻结生产文件 docstring/注释仍有“数量不变”“数量原样保留，只改标签”的旧措辞；按工单不修改，留待后续处理。

### 范围与完整性

- 施工前冻结 **1180 个文件**；仅修改本工单五个既有白名单文件，新增证据均位于本工单目录并带 `_r5` 后缀。无删除、无白名单外改动；增量补丁见 `change_r5.patch`，最终核验见 `scope_before_r5.json`、`scope_after_r5.json`、`scope_verification_r5.log`。
- 分支 `main`、HEAD `2000b6e78f790ee0ed348cc2ecb8eae796d5136e`、VERSION `7.0.4` 和 Git index 均保持施工起点状态；未 commit。
- 生产 `scripts/report/entity_source_trace.py` SHA-256 仍为 `e85acee4e9a98a664d9b4881ca33177003aa9455261109a01e111e6faeda3cd1`；`r3_fix_ruling.md` 及其他既有非白名单文件哈希保持不变。
- 全程离线；未读取禁用归档目录或禁用 tag。
