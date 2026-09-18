# 工单 E（v2，融合 codex 复核 r1 两条 E-R1-01/02）：版本落地 8.0.0 —— repair-20260918b-p0-fig2-decimals 收官（G1 图 2 必画下限 / G2 EVM decimals 链上观测 bundle v2）

> 性质：**纯文档/元数据工单**，零生产代码、零测试代码、零手册改动。**档位＝8.0.0（主）**，用户 09-18 裁决原话"升主版本 8.0.0 吧"：G2 把 EVM 观测 bundle schema 从 `evm-observation-bundle/v1` 升为 `v2` 且旧 v1 一律拒收，属**不兼容的持久化 schema 变更**，符合 CHANGELOG 头部"主=不兼容的工作流/schema/入口边界变更"。7.2.0/7.2.1 历史条目中"档位待追认"文字**不回改**。
> v2 变更（`review_E_reply_r1.md`）：E-R1-01 schema 计数分清"18 处既有替换／当前 19 处命中（含 docstring 新增 1 处）"；E-R1-02 G2 盲审未整跑改 18 项（17 临时目录＋1 socket）。
> 内容基线：HEAD 以 `construct_E_prompt.md` 派工副本首行标注为准；两段施工 commit：G1 7a21bf1、G2 9ecc962。

## §0 纪律与白名单
- 禁读 `~/.codex/`（启动搜索若已读 memories 披露一次）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260918-p0-f04-f07/` 与本目录以外的历史 maintenance 目录、`/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。离线。不 commit（Fable 验收后提交）。禁 stash/checkout/reset。
- **只允许修改四个文件**：`CHANGELOG.md`、`VERSION`、`pyproject.toml`（仅 :15 `version =` 一行）、`SKILL.md`（仅 :23 版本注释一行）；另允许新增 `maintenance/repair-20260918b-p0-fig2-decimals/E_done.md`。`references/`、`scripts/` 一字不动。
- 本单是 G1/G2 的版本登记，不重新评价两段施工；若 §2 文案与仓库事实不符（行号、字节、命令名、测试名、计数），退回本单而不是自行改写事实。

## §1 目标
VERSION（权威）= `pyproject.toml` `version` = CHANGELOG 最新条目 = `SKILL.md:23` 注释 全部为 `8.0.0`；CHANGELOG 新增索引一行与详细条目一段，体例与 7.2.1/7.2.0 一致；`test_version_consistency` 绿、`wc -c SKILL.md` 改前后相等（8021，`7.2.1`→`8.0.0` 等长）；`changelog_lint`、`docs_lint --all` 因读取 `archive/` 由调度方本机跑（施工方不跑；调度方施工前基线"活跃 77 条"，施工后复跑确认 78）。

## §2 改法（逐文件）
1. `VERSION`：`7.2.1` → `8.0.0`（保持原有换行形态）。
2. `pyproject.toml:15`：`version = "7.2.1"` → `version = "8.0.0"`。
3. `SKILL.md:23`：`<!-- skill-version-source: VERSION; skill-version: 7.2.1 -->` → `… 8.0.0 -->`（字节数不变）。
4. `CHANGELOG.md` 两处插入（施工者不运行 `changelog_lint`）：
   - 在索引区 `:13`（锚 `- **7.2.1**（2026-09-18）codex 7.2.0 六视角 review 主轨四条 P0 修复`，行首片段）**之前**插入一行，逐字：
     ```
     - **8.0.0**（2026-09-18）codex 7.2.1 六视角 review 两条 P0 修复，EVM 观测 bundle schema 升 v2（旧 v1 一律拒收，故记主版本）：G1 图 2 校验器 `fig2_check_errors` 增必画下限——label 以 项目方/大庄/小庄/离场庄 起头的实体须各有一条线，缺线/重复线/空 series 一律拒（原先空 series 可 PASS 0 条），closeout 选材复用同一规则、发布闸重算自动继承；G2 EVM 观测 `observe_evm_supply` 在冻结块补第 4 笔 eth_call `decimals()`（uint8），transcript 8→9 笔，bundle `supply.decimals`，accounting 写 `checks.decimals`＝观测值，shared receipt 核 checks≡bundle，发布闸 `check_facts_decimals` 两链族统一读 `accounting.checks.decimals` 并对 EVM 另核 verify_recon config.decimals≡观测（原先拿 config 自报当"链上观测"）。references +15 B（仅补 `decimals()` 一词），SKILL/commands 不变。峰值 override 自写证据与 metrics 自报按"威胁模型＝自己人"裁决登记残余不修。
     ```
   - 在 `:95`（锚 `## [7.2.1] - 2026-09-18 — codex 7.2.0 六视角 review 主轨四条 P0 修复`，行首片段）**之前**插入下面整段（段后空一行再接原 7.2.1 标题），逐字：
     ```
     ## [8.0.0] - 2026-09-18 — codex 7.2.1 六视角 review 两条 P0 修复（图 2 必画下限 / EVM decimals 链上观测，observation bundle v2）

     - **出处与裁决**：codex 对 7.2.1（f1f473f3）的六视角 review 判 BLOCK、P0×7。调度方对照判定：7.2.1 四条中 F06/F07 彻底修好；F04（图 2）主体修好但"空 series 放行"残余被升 P0（本轮 F01）；F05 半修复——decimals 那半的工单前提错误（把 verify_recon **config**.decimals 当"链上观测"，而 EVM 观测生产者从未请求 `decimals()`，两轮工单复核与盲审都没拆穿；本轮 F07）。用户 09-18 裁决：①峰值 override 自写证据、metrics 自报（本轮 F06）坚持"威胁模型＝自己人"，登记为已知残余不修；②修本轮 F01（→G1）与 F07（→G2）；③F02/F03/F04 净室轨仍缓修 P1；④版本升主 8.0.0。修的终点＝review 附录 C 反例（`empty_figure2`、`decimals_selfreport`）在 HEAD 上必变拒，由盲审方独立复现，不以盲审 PASS 为准。
     - **G1**（`figures_from_facts.fig2_check_errors`；`stage2_closeout.fig2_selection_errors`）：新增 `FIG2_REQUIRED_LABEL_PREFIXES=("项目方","大庄","小庄","离场庄")` 与 `fig2_required_entity_ids(entities)`；校验器对同一实体第二条线拒"线重复出现"，末尾对必画集合减已见集合求差，缺线报"图 2 缺必画实体线 […]（…空 series 不得放行）"；closeout 选材改为调用同一函数（消灭第二份前缀规则）；发布闸 `check_figure2_receipt` 7.2.1 起发布期重算，自动继承。既有非必画实体（观察实体/默认 label）的空 series 绿例保持绿。`test_figures_from_facts` 4b/4c、`test_repair_batch_c._g1_case_1..4`（先执行两端再汇总断言）。盲审独立复现：原反例基线 check rc 0/收据 PASS/消费者 errors=[] → HEAD rc 1/FAIL/拒；192 组输入新旧 closeout 输出相同。
     - **G2**（`evm_observation.observe_evm_supply`；`observe_supply.py`；`accounting_gate.py`；`supply_truth_gate.py`；`shared_release_receipt.validate_accounting_receipt`；`audit_release_gate.check_facts_decimals`）：观测在冻结块哈希（EIP-1898）补第 4 笔 eth_call selector `0x313ce567`（`decimals()`），返回值按 uint8（0–255）校验，transcript 恰 9 笔（`eth_chainId, eth_getBlockByNumber, eth_blockNumber, eth_call×4, eth_getCode, eth_getBlockByNumber`），bundle 新增 `supply.decimals`，schema `evm-observation-bundle/v1`→**`v2`**（既有 18 处 v1 字面量同步为 v2＝scripts 8＋invariant_manifest 6＋contract_manifest 1＋references 3，另在 `check_facts_decimals` docstring 新增 1 处来源说明，当前 v2 全量命中 19 处；`validate_evm_observation_bundle` 对非 v2 抛 ValueError，旧 v1 bundle 任何消费者一律拒）；accounting_gate 验 bundle 后写 `checks.decimals=bundle.supply.decimals`；shared receipt EVM 分支核 `checks.decimals≡bundle.supply.decimals`；发布闸 `check_facts_decimals` 两链族统一读 `accounting.checks.decimals`（checks 非对象走拒收，不抛异常），EVM 另核 verify_recon `config.decimals≡观测`，不一致报"与链上观测 … 不一致——对账 human 供应量级自报"。非标准 ERC20（无 decimals()）在观测阶段 FAIL 属目标行为。测试：8 夹具文件 transcript 下标顺延＋`decimals` 字段；新 RED 用例四组（decimals 观测/uint8 越界拒、accounting `checks.decimals`≠bundle 拒、`test_review_20260804_p105` c 例 facts/config 同改 decimals=2 并重绑哈希→基线 `[]`→改后双拒、EVM checks 非对象返回拒收不抛异常）。盲审独立复现：raw_supply 不变、config 0/100→2/1 重绑哈希，对账深验仍通过但发布闸双拒；accounting 与 bundle 不同值亦拒。
     - **工艺**：每段工单先 codex 只读复核（G1 两轮：r1 退回 3 条→v2 r2 通过；G2 四轮：r1 退回 7 条→v2 r2 退回 3 条→v3 r3 退回 1 条→v4 r4 通过），按意见修订后 codex 写模式施工，Fable 本机验收（白名单 diff 对照工单、定向测试、字节）后 commit，再 codex 常规盲审：G1 r1 PASS、G2 r1 PASS（codex 沙箱 18 项未整跑＝17 项临时目录权限＋1 项纵切片 socket 权限，由调度方本机 21 项定向＋docs_lint --all 全 PASS 补足，含 `test_batch3_evm_vertical_slice`）。复核提示词新增固定一条"专门核每个'来源'断言是否真有生产者写出该字段"（F05 事故教训）；盲审提示词新增"终点判据：独立复现 review 反例在 HEAD 变拒"。只读复核与盲审并行派、施工串行；施工中不 commit。
     - **字节与测试**：references 930061→930076（+15，仅 `data-pipeline-evm-recon.md` 补 `、\`decimals()\``）、SKILL.md 8021、commands-staging 8798 不变；`invariant_manifest`/`contract_manifest` 仅 v1→v2 字面量；本机 run_all 150/151＋`test_stage2_reseal` 补验 21/21（唯一失败为已知环境项：验收 worktree `/tmp/w3_acceptance` 须同步当前 HEAD，同步后重跑全绿）＝151/151；九项守卫全 PASS。登记不修台账 `maintenance/repair-20260918b-p0-fig2-decimals/code_change_pending.md` Q1–Q8（Q1 峰值 override/metrics 残余按自己人模型不修；Q2 净室三条 P1；Q5 Solana 侧 `checks.decimals`↔bundle 相等性另单；Q6 非标 ERC20 观测 FAIL 属目标行为）。
     - **档位与迁移说明**：8.0.0（主）——EVM 观测 bundle schema v1→v2 不兼容，旧 v1 bundle 在 HEAD 下 BLOCK。存量迁移代价分三类：①**supply_truth 收据（两链）**：producer `supply_truth_gate.py` 被改，旧收据 producer 哈希失效（Solana 算法未变也不例外）；②**reconciliation wrapper**：自身 producer 未改，但 supply_truth 子项的 producer/receipt 引用须随①刷新（重跑 `reconciliation_report`）；③**shared receipt**：自身 producer `shared_release_receipt.py` 被改，且下游输入绑定须重建。EVM 案另须重跑观测三件（`observe_supply` 产 v2 bundle→`accounting_gate`→下游）。旧案只能在钉版的完整旧 checkout/执行环境下发布，单填旧版本字段无效；新版重发布须整链重跑 supply_truth→reconciliation_report→shared receipt→下游封口。G1 侧：旧图 2 PASS 收据若绑定的 series 缺必画线/重复线，发布期重算即拒，重装配 series→重跑 `figures_from_facts check`→更新受影响下游封口。
     - **成本-质量指标**：生产逻辑文件 8（figures_from_facts、stage2_closeout、evm_observation、observe_supply、accounting_gate、supply_truth_gate、shared_release_receipt、audit_release_gate）、新公开入口 0、新持久化 schema 1（bundle v2 替代 v1）、新增 SUITE 入口 0；外部网络调用 0（观测改动全部以测试假池验证）；不运行真实案卷判断链，判断结论不自动变更。
     ```
   - 其他行不动；`archive/CHANGELOG-archive.md` 不动。

## §3 验收（施工者自跑并记入 E_done.md）
- `git status --porcelain=v1 --untracked-files=all` 只列四个文件（M）与 `E_done.md`（??）；`git diff --exit-code HEAD -- references/ scripts/` 退出码 0。
- `python3 -B scripts/tests/test_version_consistency.py` exit 0；`wc -c SKILL.md` 改前后均 8021。**不跑** `changelog_lint`、`docs_lint --all`（读 archive/，调度方本机跑并记 77→78）、不跑 run_all（调度方已跑并填入 §2）。

## §4 报告 `E_done.md`
首行 `# 施工 E：完成` 或 `# 施工 E：停工`；列四文件各自 diff 行数、`test_version_consistency` 退出码与输出行、`wc -c SKILL.md` 两值。不 commit。
