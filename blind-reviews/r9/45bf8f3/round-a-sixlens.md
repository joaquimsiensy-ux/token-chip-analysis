# Round A：六视角全库独立质量核验

## 0. 核验边界与基线

- 仓库：`/Users/uravvv/Documents/5.6筹码分析/r9-closure-worktree`
- 分支/HEAD：`fix/r9-closure-20260807` / `45bf8f31fde258af833697510bb3aadc51e3f88a`（与任务给定短 SHA 一致）。
- 起始工作树：`git status --short --branch` 显示分支行及既有未跟踪目录 `?? r9-reviews/`；本轮不读写该目录。本轮审查没有对报告外路径执行写命令，动态反例均使用系统临时目录。
- **终态完整性异常**：结束前第二次 `git status --short --branch` 新增 `M maintenance/repair-20260806/ledger.md`、`M scripts/tests/run_all.py`、`?? maintenance/repair-20260806/exemptions.md`、`?? scripts/tests/test_exemption_guards.py`。四项时间戳为 2026-08-09 04:11–04:13 -0400，均在本轮核验期间；`run_all.py` diff 还新增了测试挂载。仅凭 git 状态不能认定写入来源，但它们不在本轮授权写入范围，且起始状态不存在。为避免把两个工作树状态混成一份“当前状态”结论，本报告保留变更前 45bf8f3 快照的已完成证据，停止在污染后的工作树继续重跑，完成信号改为 `ROUNDA_ABORT`。
- 范围：读 `SKILL.md`、`references/`、`maintenance/`；生产代码与测试限定在 `scripts/`。未扫描数据目录，未使用 `du`、`find` 或 `ls -R`，未出网，未执行 git 写操作。
- 方法：完整读取 `references/maintenance-review-repair.md`（169 行），严格按其六视角执行。`scripts/` 范围共 288 个文件：`evm` 34、`solana` 24、`report` 25、`lib` 16、`labels` 69、`robinhood` 16、`prices` 2、`bench` 2、其他顶层/钩子 3；其中测试目录 97 个文件。
- 动态基线：
  - `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/invariant_scan.py`：exit 0，`receipt_producers=52, receipt_consumers=55, transport_calls=62, atomic_writes=42, formal_entrypoints=58, exceptions=0`。
  - `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py`：89 项中 87 PASS、2 FAIL。失败仅为 `test_batch3_solana_vertical_slice.py` 与 `test_batch3_evm_vertical_slice.py` 在 `ThreadingHTTPServer(("127.0.0.1", 0), ...)` 的 `server_bind()` 遭沙箱 `PermissionError: [Errno 1] Operation not permitted`；没有到达被测业务链。按任务约定登记为环境未执行，不据此判代码 finding。

## 1. 视角①：字段来源审计

### 实际核验动作

- 读码：`scripts/lib/receipt_kernel.py`、`scripts/lib/receipt_validate.py`、`scripts/report/reconciliation_report.py`、`scripts/report/shared_release_receipt.py`、`scripts/report/adversarial_review_runner.py`、`scripts/report/audit_release_gate.py`、`scripts/report/a4_gate.py`、`scripts/report/a5_report_seal.py`。
- 交叉对表：以 `invariant_manifest.json` 的 52 个 producer / 55 个 consumer 为分母，检查公共 envelope 的 target、producer SHA、input size/SHA、verdict/exit_code 是否由独立 validator 重验；再沿正式发布入口核对 reconciliation 四查与 adversarial review 的字段来源。
- 动态反例：在临时目录写一个 review entrypoint，仅向受控输出写 2 字节 `ok` 并 exit 0，分别以 `entity_attribution_skeptic`、`completeness_critic` 运行 `run_review()`；两个 execution receipt 均被 `validate_review_receipt()` 接受，拼成 `adversarial-review/v2` 后 `audit_release_gate.check_adversarial()` 返回 `errors=[]`。

### 结果

- 对账四查字段不是只信 wrapper：`shared_release_receipt.py` 会打开子 receipt、核 target/schema/业务观察量，并核当前 producer/runner SHA；该面未发现新缺口。
- receipt 公共 envelope 的 producer/input/verdict 具备独立重验；事务发布与失败 side receipt 有常驻注入测试，本轮门禁通过。
- 对抗复核的“确实执行过有内容的复核”仍是自报：runner 只要求产物非空，发布闸只看角色名、blocker resolved 与 release_decision，不验证产物 schema、命题覆盖、重算证据或 finding 内容。见 RA-04。

## 2. 视角②：失败分支审计

### 实际核验动作

- 全库检索生产代码的 `warning/WARN`、宽泛 `except`、裸 `pass`、`gate_pass`、返回码传播及 canonical artifact 写入点；重点读 `replay_pass1.py`、`replay_pass2.py`、`replay_duck.py`、`replay_stream.py`、`replay_edges.py`、`build_html.py` 与 receipt kernel。
- 用 `invariant_scan.py`/`test_batch4_invariant_guards.py` 核整数 `main()` 退出码传播、失败产物登记、可达 quarantine/ERROR 调用；两项均在全量 suite 中通过。
- 动态反例：临时构造一条“未 mint 即由普通地址转出”的合法 receipted EVM 通道，使 `replay_pass1.py` 产出 `gate_pass=false, neg_balance_addrs=1`；记录 pass1 与紧随其后的 pass2 进程返回码和产物。

### 结果

- 正式 DuckDB/stream 重放、四查 runner、build_html 和 receipt producer 的主要失败分支能非零退出且保护旧 PASS 产物。
- 旧但仍被文档保留为小样本正式路径的 `replay_pass1.py` 在对账 gate 明确失败时仍 exit 0；`replay_pass2.py` 不检查 gate 又继续 exit 0 并生成正式命名序列。反例实测 `PASS1_FAILING_GATE_RC 0 gate_pass False neg 1`、`PASS2_AFTER_FAILED_GATE_RC 0`。见 RA-05。

## 3. 视角③：新格式的存量迁移

### 实际核验动作

- 全库交叉搜索 `schema`/`v1`/`v2`/`v3`、`legacy`、`migration`、`存量`，并读：`handoff_manifest.py` 的 v1→v2 legacy-read-only 路由、`shared_release_receipt.py` 的 v2 强制重跑提示、`fetch_hypersync_v2.py` 的 done manifest 刷新器、`fetch_sqd_transfers_v2.py` 的 v3 cache identity 兼容归一化。
- 核生产者/消费者同版：以 `invariant_scan.py` 的 schema census 与 `test_commands_deploy_sync.py`、`test_version_consistency.py`、`test_contract_routes.py`、`docs_lint.py --all` 结果交叉验证；均在本轮全量测试 PASS。
- 检查旧案是否被静默提升为正式件：handoff v1 只能显式 `--legacy-read-only`，`audit_release_gate.py`/`build_html.py` 会拒绝 legacy marker 进入新正式发布。

### 结果

- 当前主干的新 receipt/schema 均有明确“重跑 producer”或显式 legacy-read-only 路径，未发现旧字节被静默当成当前正式 PASS 的确证反例。
- 该视角的异常落在“输入格式约束缺失”而非 schema 迁移：阵营配置宣称互斥却没有 validator；同一地址重复登记会被后项静默覆盖。见 RA-02。

## 4. 视角④：修复点的同族调用面

### 实际核验动作

- 以关键概念全库 `rg`：`camp_share_series`、`addr2camp`、`gate_pass`、`formal_ready`、`VERTICAL_SLICE_EVIDENCE_TARGETS`、`HYPERSYNC_TOKEN`、`api_token`、`--token-file`、receipt schema；逐一对照 EVM/Solana、旧/新 replay、producer/consumer、正式/探索入口。
- 代码同族对表：
  - 阵营：`replay_pass2.py`、`replay_duck.py`、`replay_edges.py`、`state_from_facts.py`、`figures_from_facts.py`、`standard_charts.py`。
  - 正式链：`chain_registry.py`、`formal_capability_probes.py`、`shared_release_receipt.py`、`audit_release_gate.py`、两条 vertical slice 测试。
  - HyperSync：`fetch_hypersync.py`、`fetch_hypersync_logs.py`、`fetch_pool_swaps.py`、`fetch_hypersync_v2.py` 与 `test_token_no_positional.py`。
- `for p in scripts/tests/test_*.py; ... rg -q -F "$b" scripts/tests/run_all.py` 无输出：所有 `test_*.py` 均已挂入 `run_all.py`，未发现孤儿测试文件。
- `PYTHONDONTWRITEBYTECODE=1` AST 解析 `scripts/` 下 228 个 Python 文件：0 失败；全部 shell 脚本逐个 `bash -n`：PASS。

### 结果

- chain registry、labels 链面、正式 producer 分母、receipt producer/consumer 和全部 test 挂载面由现有自动守卫覆盖，本轮未发现新增漏项。
- 阵营互斥不变量在两个 EVM 实现都没有 validator，并在 Solana 同族入口也采用无冲突检测的后项覆盖；本轮对 EVM 两实现做了读码对表、对旧 Python 路径做了动态反例。见 RA-02。
- 三支 v1 HyperSync 脚本已有 F-07 回归，现役首选 `fetch_hypersync_v2.py` 却未纳入同族清单，仍保留位置明文 token。见 RA-07。

## 5. 视角⑤：双向一致性

### 实际核验动作

- 文档→代码：核 `SKILL.md` 正式链矩阵、A0–A6 路由、key 取用纪律、图 1 同源声明、legacy 路由；追到 `chain_registry.py`、CLI argparse、state compiler、chart generator 和 release gate。
- 代码→文档：从 argparse/schema 常量反查 `references/`；执行 `docs_lint.py --all`、`test_contract_routes.py`、`test_version_consistency.py`、`test_chain_support_matrix.py`、`test_formal_chain_support.py`、`test_commands_deploy_sync.py`（均由本轮全量 suite 实际执行且 PASS）。
- 数值契约：对 `report-template.md` “图 1 从 state 直出/图层同源”与 `state_from_facts.py`、`figures_from_facts.py`、`standard_charts.py` 双向对表；动态喂入事实实体当前占比 25%，但 state source 自报“大庄 0%、任意阵营 -899%、散户 999%”。
- 图例契约：动态传入 `大庄=60%` 与未知阵营 `40%`，截获真实 Matplotlib 图例。

### 结果

- 版本、正式链支持范围、契约路由和 58 份运行时文档引用均一致。
- “图层同源”只做到“图读取 state”，没有做到“state 的阵营序列来自已对账重放”；编译器接受上述自报异常序列且不与 facts/原始重放对账。见 RA-01。
- `figures_from_facts.py` 自报处理 2 个阵营，真实图例只有 `大庄`，未知阵营 40% 被静默过滤；文档把防错责任留给人工目检，正式门禁未覆盖。见 RA-03。
- key 纪律在 v1 三入口与现役 v2 入口不一致。见 RA-07。

## 6. 视角⑥：每道闸的可绕性

### 实际核验动作

- 对正式构建主路读码：`build_html.py --mode analysis-new|analysis-audit` 的 facts/state/A4/A5 必填、`audit_release_gate.run()`、`shared_release_receipt.validate_bundle()`、A4 revision 链、A5 Markdown/图片/分布终态绑定；全量相关测试均 PASS。
- 破坏性注入：
  1. 对正式 E2E AST 守卫构造模块级 `subprocess = Dummy()`，函数内保留六个真实脚本字面调用；执行 scanner 与样本。
  2. 对 adversarial review 用只写 `ok` 的 entrypoint 生成两角色 receipt，再调发布闸检查。
  3. 对图 1 注入未登记阵营，核实际 legend。
  4. 对旧 EVM replay 注入 gate-fail 数据，串行跑 pass1/pass2。
- 正向反证：`test_batch4_invariant_guards.py`、`test_reconciliation_runner.py`、`test_audit_release_gate.py`、`test_build_html.py`、`test_a4_gate.py`、`test_round4_a5_seal.py` 全部 PASS；说明其点名反例仍关闭，不能据此推出未测变体也关闭。

### 结果

- build_html 的正式模式选择、A4/A5 seal 路径、shared receipt 与正式链矩阵是必经路，本轮没有找到省略参数或换 legacy 模式伪装成正式件的路径。
- E2E provenance 元守卫可被模块级重绑定绕过；实测 scanner `errors=[]`，样本 exit 0，但六次只是 Dummy 调用、零生产进程。见 RA-06。
- adversarial review gate 可由两个 2 字节 `ok` 产物满足。见 RA-04。
- 图 1、旧 replay 的旁路分别见 RA-03、RA-05。
- **疑点待证（不计 finding）**：`replay_edges.py:238` 在 `--camps` 文件不存在时把配置当 `{}`，仍生成“首 30 分钟狙击者/其他散户”序列并 exit 0；本轮反例证实行为，但现役文档没有明确该文件在 bootstrap 场景是否必须存在，无法排除这是有意的探索模式，故不把猜测写成缺陷。

## 7. 发现清单

### RA-01 — `camp_share_series` 是未绑定原始重放的调用者自报字段

- **文件:行**：`scripts/report/state_from_facts.py:85-95`；下游 `scripts/report/figures_from_facts.py:93-125`。
- **严重度**：**P0（数据错误）**。
- **归因**：历史漏检。`git blame` 显示该校验自 `9179d330` 起即只验容器与长度，早于本轮 R9 基线；未找到它属于既有 finding 或本轮 repair diff 的证据。
- **问题**：正式图 1 的阵营序列来自 `state_source.json`，编译器只验证 `dates/series` 类型和等长，不验证值是有限数、范围在 `[0,100]`、同点闭合、标准阵营名、末点与 facts/余额一致，也不绑定 replay receipt/输入哈希。`provenance.skill_commit/data_sources` 也只是非空字符串自报。A4/A5 只封口错误字节，不能把自报值变成链上事实。
- **复现/验证**：临时 Python harness 调 `compile_state()`：facts 中 `e1.current_raw=2500,total=10000`（真实当前 25%），source 注入 `大庄=0, 任意阵营=-899, 散户=999`；函数无异常并原样返回。实测输出：`FACT_ENTITY_CURRENT_SHARE 25.0` 与 `ACCEPTED_CAMP_SERIES {...-899.0...999.0}`。
- **最强替代解释**：state source 本来就负责承载 facts 没有的序列。**不采纳理由**：承载不等于可自报；正式文档把它称为“图层同源”，而当前没有任何 raw-derived producer/receipt 或数学约束能重验该关键字段。

### RA-02 — 互斥阵营重复地址被静默后项覆盖

- **文件:行**：`scripts/evm/replay_pass2.py:28-34,80-90`；同族 `scripts/evm/replay_duck.py:360-368`；同形 Solana 入口 `scripts/solana/replay_edges.py:237-243`。
- **严重度**：**P0（数据错误）**。
- **归因**：历史漏检。两套 EVM 行分别源自仓库早期实现与 `ff477632`，早于 R9；当前台账未点名这一输入不变量。
- **问题**：`replay_pass2.py` 自述 `camps.json` 阵营互斥，但代码用 `addr2camp[addr] = camp`，重复地址由 JSON 后出现的阵营静默夺走；DuckDB 版本还明确注释“后配置覆盖先前”。错误输出仍各阵营加总 100%，外观正常，无法靠总和检查发现。
- **复现/验证**：临时 `merged.csv` 仅含向地址 A mint 100，`camps.json={camp_A:[A],camp_B:[A]}`；运行 `python3 scripts/evm/replay_pass2.py camps.json --data-dir data`。实测 exit 0，`camp_A:[0.0], camp_B:[100.0], 散户:[0]`。
- **最强替代解释**：后项覆盖可被解释为配置优先级。**不采纳理由**：生产 docstring 明写“阵营互斥”，没有任何优先级 schema；同一输入仅交换 JSON 键顺序就改变数据结论。

### RA-03 — 正式图 1 对未知阵营静默漏画

- **文件:行**：`scripts/report/state_from_facts.py:85-92`、`scripts/report/figures_from_facts.py:93-125`、`scripts/report/standard_charts.py:141-172`。
- **严重度**：**P1（逻辑缺陷）**。
- **归因**：历史漏检。过滤逻辑自仓库初始实现即存在；R9 未触及该不变量。
- **问题**：state compiler/fig1 wrapper 接受任意阵营键，wrapper 还打印输入阵营数；真正绘图时只取 `CAMP_ORDER` 交集，未知阵营无 warning、无非零退出。正式 A5 只绑定 PNG 哈希，不重验图例与 state 阵营集合一致，因此可交付缺失整类持仓的图。
- **复现/验证**：向 `plot_camp_evolution()` 传 `大庄=60%`、`未登记但有效阵营=40%`，截获真实 Matplotlib legend；实测 `INPUT_CAMPS ['大庄','未登记但有效阵营']`，`RENDERED_LEGEND ['大庄']`，`OMITTED ['未登记但有效阵营']`。
- **最强替代解释**：`CAMP_ORDER` 白名单防止非标准命名污染正式图。**不采纳理由**：白名单拒绝应 fail-closed；静默丢 40% 数据并把检查留给人工目检不是安全拒绝。

### RA-04 — 对抗复核只证明“脚本写了非空字节”，不证明复核内容

- **文件:行**：`scripts/report/adversarial_review_runner.py:44-80,92-113`；`scripts/report/audit_release_gate.py:706-724`。
- **严重度**：**P1（逻辑缺陷）**。
- **归因**：历史漏检。runner 的非空产物契约源自 `f45c04f6`，发布侧弱语义更早存在；均早于 R9 基线。
- **问题**：entrypoint 可为案目录内任意 Python 文件；runner 只要求 exit 0 且 staging 非空。validator 只核路径/大小/SHA；发布闸只核两个角色名、blocker 的 `resolved` 和 release decision。没有 artifact schema、claim 覆盖、重算证据、finding 明细或最小内容要求，因而“对抗复核必做”可被形式化空壳满足。
- **复现/验证**：临时 entrypoint 仅执行 `Path(CHIP_REVIEW_OUTPUT).write_text('ok')`；两角色分别 `run_review()`、`validate_review_receipt()` 均通过，随后 `check_adversarial()` 实测 `AUDIT_CHECK_ERRORS []`。
- **最强替代解释**：机器无法判断自然语言复核质量，只能证明流程确实执行。**不采纳理由**：无需机器判断结论对错，也至少能强制结构化 claim IDs、覆盖集合、重算引用和 finding 数；当前连这些客观字段都没有。

### RA-05 — 小样本 EVM 重放 gate 失败仍双重 exit 0

- **文件:行**：`scripts/evm/replay_pass1.py:129-151`；`scripts/evm/replay_pass2.py:26-27,94-115`。对照正确同族：`scripts/evm/replay_duck.py:540-549`。
- **严重度**：**P1（逻辑缺陷）**。
- **归因**：历史漏检。pass1 行来自仓库早期实现；R9 只补了 provenance，没有补失败退出。
- **问题**：pass1 已算出 `gate_pass=false` 并打印负余额，却无 return/`SystemExit(4)`；pass2 只读 `mint_total_wei`，不要求 `gate_pass=true`，继续产 `camp_series.json`/`entity_series.json`。文档仍把这组旧引擎保留为小样本快速路径。
- **复现/验证**：临时 receipted channel 放一条“普通地址 A 未 mint 即向 B 转 100”的事件；串行运行 pass1/pass2。实测 `PASS1_FAILING_GATE_RC 0 gate_pass False neg 1`，随后 `PASS2_AFTER_FAILED_GATE_RC 0` 并产序列。
- **最强替代解释**：后续 `identity_snapshot_receipt.py` 与正式 release gate 会拒绝 `gate_pass=false`。**不采纳理由**：这降低为 P1 而非 P0，但不能使上游 exit 0 合法；pass2 是明确的下游分析入口，已被允许在坏账上生成正式命名产物。

### RA-06 — formal E2E provenance 守卫可被模块级重绑定绕过

- **文件:行**：`scripts/tests/invariant_scan.py:509-520,647-753`；readiness 只解析 callable/挂载/装饰器：`scripts/lib/formal_capability_probes.py:190-225`。
- **严重度**：**P2（质量隐患）**。
- **归因**：老问题修复不全（半修残留）。当前代码注释已明确 `KNOWN-OPEN` 且无独立 runtime backstop；它仍属于 F-B4-01 的同一“伪执行证据”不变量。
- **问题**：scanner 记住顶层 import 名，但不检查其后模块级重绑定；函数内看见 `subprocess.run([...scripts/...])` 字面即计真实执行。readiness 又只要求目标可调用、测试挂 SUITE、装饰器 chain 正确，不执行独立来源证明。
- **复现/验证**：临时样本先 `import subprocess`，再顶层 `subprocess=Dummy()`；target 内保留 runner+五个 Solana producer 的六个字面调用。实测 `formal_e2e_provenance_errors(...)=[]`，样本 exit 0，`DUMMY_CALLS 6`，没有启动生产进程。
- **最强替代解释**：这是已诚实登记、经用户裁决降级接受的内部元守卫边界。**不采纳理由**：裁决能说明风险被接受，不能把可复现缺口变成无问题；本报告按当前质量事实仍记 P2，并不把它夸大成外部 P0/P1。

### RA-07 — 现役 HyperSync v2 仍接受位置明文 token，同族回归漏入口

- **文件:行**：`scripts/evm/fetch_hypersync_v2.py:274-296`；同族测试清单 `scripts/tests/test_token_no_positional.py:1-14`；key 纪律 `SKILL.md:35`。
- **严重度**：**P2（质量隐患）**。
- **归因**：老问题修复不全（半修残留）。F-07 回归只枚举三支 v1 脚本，漏掉文档标为现役首选的 v2 采集器。
- **问题**：v2 的 `api_token` 仍是可选位置参数，且优先级高于环境变量和 token-file；告警后照常返回，使密钥进入 shell history/进程列表。现有 `test_token_no_positional.py` 不包含该文件，所以全量 suite 仍绿。
- **复现/验证**：导入模块后调用 `resolve_token(SimpleNamespace(api_token='DUMMY_POSITIONAL_TOKEN', token_file='/definitely/missing'))`；实测先打印 ps 可见警告，再输出 `POSITIONAL_TOKEN_ACCEPTED True`。
- **最强替代解释**：代码明确称为旧用法兼容。**不采纳理由**：兼容性不能凌驾于当前 key 纪律，且这是现役首选采集器；安全迁移应拒绝明文位置参数并给出改用文件/环境变量的硬错误。

## 8. 没查的部分

- **限定范围外**：未读取/扫描仓库大体量数据目录、archive 考古区及既有未跟踪 `r9-reviews/`；这是任务明定范围与防卡死纪律。
- **外部真实性**：不出网，未连真实 RPC/API，未重放真实链上标的；因此不能验证当前第三方端点、链上 mainnet 样本或现存裁判 JSON 的外部真实性。
- **两条 loopback 纵切片**：EVM/Solana 测试因沙箱禁止本地监听未到业务分支；其余 87 项通过，不能替代这两项的非沙箱复跑。
- **规模/性能**：未用真实亿级 Parquet/CSV 做 OOM、耗时和并发压力测试；只核现有离线测试、静态边界与小型临时反例。
- **逐文档语义**：`docs_lint --all` 覆盖 58 份文档的链接/结构，关键契约做了双向读码；没有逐字人工审阅 `references/` 每一段业务方法论或每个 labels 数据行。
- **疑点未定**：Solana 缺 camps 文件仍生成序列的行为因规范不够明确，仅登记在视角⑥，不计入问题数。

总体判断：**ROUNDA_ABORT（终态工作树并发变化）**；对起始 45bf8f3 快照的质量判断为 **BLOCK**，87/89 测试通过与静态 census PASS 不能抵消 2 个可复现 P0、3 个 P1。  
问题计数：P0 2 / P1 3 / P2 2 / P3 0  
报告路径：`/Users/uravvv/Documents/5.6筹码分析/r9-closure-worktree/blind-reviews/r9/45bf8f3/round-a-sixlens.md`
