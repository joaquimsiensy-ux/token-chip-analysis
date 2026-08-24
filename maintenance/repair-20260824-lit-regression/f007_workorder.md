# 工单 F-007：末点对账与闭合校验的堆叠集合按 series_format 定义（fresh 会话可独立执行）

一句话目标：修复「锁仓/销毁」桶在校验端被一刀切豁免导致的 EVM dead-sink 型假红（LIT 案首证），修法=堆叠集合按 series_format 由共享函数内部固定映射；先红后绿。

## 【开工门禁】（不符即写停工报告 f007_done_attempt1_stopped.md 并停）
- 仓库：/Users/uravvv/.claude/skills/token-chip-analysis
- `git branch --show-current` 必须是 `fix/lit-regression-v6522`
- `git rev-parse HEAD` 必须以 `0d4ceb5` 开头
- `git status --short` 除 `maintenance/repair-20260824-lit-regression/` 下文件外必须干净

## 背景

LIT 案（ETH，evm-dict + mint_total_legacy，0xdead 烧毁配入「锁仓/销毁」阵营，供应恒定；末点「锁仓/销毁」1.5639%、散户 6.5733%）末点对账假红。根因：校验端 `BURN_EXEMPT_KEYS=("burn_cum_pct","锁仓/销毁")` 一刀切豁免，但 EVM 生产端两种分母口径都把「锁仓/销毁」计入堆叠。净口径（EVM 默认）下同型案会在更早的逐点闭合环假红。用户已裁决两口径一起修。

## 第一步：独立核实（不要盲信本工单，逐项给"属实/不属实＋理由"写进 done 报告）

| # | 声称 | 证据锚 |
|---|---|---|
| 1 | 生产端 legacy：stack=全桶含「锁仓/销毁」，散户=100−known；不输出 burn_cum_pct/_meta | scripts/evm/replay_pass2.py:84-86,101-106,142-145 |
| 2 | 生产端 net：stack 仅排除旧自动桶"销毁"（0x0），「锁仓/销毁」仍在 known 内；burn_cum_pct 为独立披露轨道 | replay_pass2.py:86,139-145 |
| 3 | 校验端闭合一刀切：net 检 s_non、total 检 s_all，豁免集不分 format | scripts/lib/camp_series_provenance.py:59,373-385 |
| 4 | 末点对账：BURN_EXEMPT 桶 continue 不入 spec_sum，散户残差=100−spec_sum → legacy dead-sink 假红 | camp_series_provenance.py endpoint_reconcile spec 循环（约 :754-790） |
| 5 | sol-rows 的「锁仓/销毁」=分母外真烧毁披露桶，豁免正确、必须保持 | scripts/solana/replay_edges.py:648,657 |
| 6 | validate_series_payload 生产调用仅 state_from_facts.py:123（手填）/:157（绑定）；endpoint_reconcile 仅 state_from_facts.py:169 与 audit_release_gate.py:1363 | 自行 rg 全库复扫确认 |
| 7 | 若仅把豁免集做成参数替换，total 分支 s_all 仍会把豁免键加回合计，"burn_cum_pct 永远豁免"无法由结构保证 | camp_series_provenance.py:382-383 |

## 第二步：施工（先红后绿；加固方向如下，是否细部调整你自己判，但不变量不得偏离）

**不变量**：校验端对每桶"是否参与堆叠合计"的唯一权威=该 series_format 生产端的堆叠语义，由共享函数内部固定映射，不暴露给调用者自由指定。evm-dict→豁免集 `("burn_cum_pct",)`（「锁仓/销毁」参与，不分口径）；sol-rows/sol-anchor-rows→豁免集 `BURN_EXEMPT_KEYS`；无 format→dual 兼容行为逐字不变。另：`evm-dict + mint_total_legacy` 序列含 `burn_cum_pct` 键即拒（生产端 legacy 从不输出它）。

**改动白名单（只许动这些文件）**：
1. `scripts/lib/camp_series_provenance.py`：
   - 新增内部映射函数（如 `stack_exempt_for(series_format)`），返回上述固定映射；不接受外部传任意豁免集。
   - `validate_series_payload()` 新增可选参数 `series_format=None`：None=既有行为逐字不变（dual/net/total 现状逻辑保留）；有值=闭合式统一为实际堆叠键单式 `|Σ(series 键−该 format 豁免集)−100|≤tol`，不再借 net/total 分叉决定 burn 键归属（closure_mode/denominator 的合法性校验保留）；`evm-dict+mint_total_legacy` 含 burn_cum_pct → 显式拒。
   - `endpoint_reconcile()` evm-dict 分支：BURN_EXEMPT spec 桶保持登记 burn_recon（末点单桶比对不变），新增 `spec_sum += recon`，条件仅 `fmt=="evm-dict"`（不看 denominator）；sol-rows 分支维持 continue 不加。
   - docstring/注释同步：模块 docstring、BURN_EXEMPT_KEYS 邻接注释（:56-58）、closure_mode_for() docstring（:313-318）、validate_series_payload() docstring（:329-339）中"净/total 决定 burn"旧模型表述改为 format 分家表述，每处带生产端代码行号依据。
2. `scripts/report/state_from_facts.py`：`bind_series_source()`:157 改传 `series_format=sidecar["series_format"]`；:154-156 F-C4 注释同步。手填路径 :123 逐字不动。
3. 新测试文件 `scripts/tests/test_lit_regression_f007.py`（测试清单见下）。
4. 本工程档案目录下的证据/报告文件。

**测试清单（每条独立用例，红绿断言明确）**：
- 原反例（先红后绿）：LIT 型夹具（evm-dict + mint_total_legacy + 0xdead 入「锁仓/销毁」，散户=100−全栈）→ 修前红在 endpoint_reconcile 散户残差；修后绿。
- 同族变体：同夹具 net 口径（current_net_supply）→ 修前红在闭合环；修后绿。
- 一排一进：net 案同时有非零 burn_cum_pct 与非零「锁仓/销毁」→ 修后绿，断言前者被豁免、后者计入合计。
- 一致性闸：mint_total_legacy 序列携带 burn_cum_pct → 拒。
- 防伪不回退：①散户末点篡改+3pp→仍红；②「锁仓/销毁」桶值篡改→burn_recon 单桶比对仍红；③net 口径以 burn_cum_pct 蹭堆叠救缺口→仍红；④denominator 非法值→仍红。
- 手填路径逐字不变：无 format 调用的 dual 行为回归断言。
- sol-rows 绿例回归：Solana 含「锁仓/销毁」夹具仍绿。

**先红采证**：改代码前先写测试文件，在当前 HEAD 上跑，把原反例＋同族变体的 FAIL 原始输出（含 EXIT_CODE）留档 `f007_red_evidence.txt`；改后全绿留档 `f007_green_evidence.txt`。防伪/一致性闸等"修后仍红"用例在绿证阶段一并验证。

**定向回归（绿证阶段跑，结果进 green_evidence）**：`test_repair_batch_c.py`、`test_a4_gate.py`、`test_sqd_consumer_v4.py`、`test_state_from_facts.py`、`test_audit_release_gate.py`。

## 收尾
- done 报告 `f007_done.md` 按 F-005 九段结构（结论/基线与施工边界/改动清单/前后对照〔贴改前改后原文＋文件:行号依据〕/先红后绿原始输出/残留清点〔rg 旧口径表述与旧逻辑残留，逐条归类〕/lint 与测试证据/发现项只记不修/收工边界）。
- 归因栏三选一＋至少一个最强替代解释及不采纳理由（本 finding 预判"历史漏检"——BURN_EXEMPT 一刀切自设计起即与 evm-dict 生产端不一致，须自行验证并写明为何排除"半修残留/新引入"）。
- 自产文档零 EOF 空行、零行尾空格；原始输出留档含空白字符则登记 `diff_check_exemptions.md`（本目录，格式参照 maintenance/repair-20260823-sqd-gap/diff_check_exemptions.md）。
- 本批不动：版本三件/CHANGELOG/SUITE 登记/契约/references 文档（留批 3 收口）。

## 边界（硬性）
- **禁改**：scripts/report/wave_scan.py、scripts/report/entity_source_trace.py、scripts/solana/sqd_cache_identity.py（三文件被溯源台账哈希绑定，改一字节=全部存量案算法漂移拒绝）；scripts/evm/replay_pass2.py、scripts/evm/replay_duck.py、scripts/solana/replay_edges.py（生产端语义不动）；scripts/lib/case_paths.py（F-008 批的白名单，本批不碰）。
- 白名单外文件一律不改；不 commit（Fable 代 commit）；不联网；工单外新发现只记录进 done 报告"发现项"不修。
