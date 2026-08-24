# 工单 F-008：evm_v2 目录参数的"重放前集合闸"（fresh 会话可独立执行）

一句话目标：修复交接闸溯源重放对 evm_v2 目录参数的误拦（commit 7b99867 回归，LIT 案首撞），并加"重放前集合闸"关死"先读后拒"面；先红后绿。

## 【开工门禁】（不符即写停工报告 f008_done_attempt1_stopped.md 并停）
- 仓库：/Users/uravvv/.claude/skills/token-chip-analysis
- `git branch --show-current` 必须是 `fix/lit-regression-v6522`
- `git log --oneline -3` 中必须能看到 F-007 批已由裁判 commit（若 F-007 尚未入库则停工报告等调度）
- `git status --short` 除 maintenance/repair-20260824-lit-regression/ 下文件外必须干净

## 背景

交接闸 `handoff_manifest.py` 的 `validate_and_replay_provenance()` 把 `source.argument` 一律送进 `resolve_bound_path→safe_case_file`（只认常规文件）。但 evm_v2 的 argument 天生是目录（LIT ledger 实值 `"data/ethereum/v2"`）。commit 7b99867（2026-08-15 案根 containment 收口）前旧版 `resolve_bound_path` 只做 normpath、目录可过——这是确凿回归。另有既有缺口：登记文件逐件哈希校验不拦"目录里当前多出的未登记文件"，重放子进程会先读它（恶意 parquet 解析面/案外 symlink 读取面），拒绝发生在读取之后。

威胁模型（写入代码注释与 done）：集合闸的保证前提是"校验至重放子进程退出期间，案目录无并发写者"；校验与读取之间的 TOCTOU 窗口为已知残余风险，不在本次闭合范围。

## 第一步：独立核实（不盲信，逐项"属实/不属实＋理由"进 done）

| # | 声称 | 证据锚 |
|---|---|---|
| 1 | 7b99867 前 resolve_bound_path 只做 normpath；收口后换 safe_case_file 只认常规文件 | `git show 7b99867^:scripts/report/handoff_manifest.py`（旧版约 :572-575）；scripts/lib/case_paths.py:36-38 |
| 2 | evm_v2 argument=目录；生产端按 `run_*/logs.parquet`＋`run_*/blocks.parquet` 两 glob 登记 source.files | scripts/report/entity_source_trace.py:132-135,164-169 |
| 3 | 消费端 load_evm_v2 以同样两 pattern glob，并把 pattern 字符串拼进 DuckDB read_parquet SQL 字面量 | scripts/report/wave_scan.py:208-218 |
| 4 | 既有防线（source.files 逐件哈希＋manifest.artifacts/data_map 双绑定＋重放后语义摘要终比）都不拦"目录当前多出的未登记文件" | handoff_manifest.py（HEAD 版 validate_and_replay_provenance） |
| 5 | 现有 test_handoff_manifest.py 的 provenance 正例走 --edges-sol，`edges_evm_v2:"data/v2"` 仅是 wave 报告参数夹具，不构成 evm_v2 溯源正例 | scripts/tests/test_handoff_manifest.py:238 附近，自行核 |

## 第二步：施工（先红后绿；细部你自己判，不变量不得偏离）

**不变量**：溯源重放的一切输入实物必须在重放子进程启动前：①全部通过案根 containment（拒绝绝对路径/空段/`.`/`..`/逐段 symlink/realpath 越根）；②当前磁盘命中集合与 ledger 登记的 source.files 路径集合严格相等（多一个、少一个、登记重复都拒）。目录枚举自身不得跟随 symlink。

**改动白名单（只许动这些文件）**：
1. `scripts/lib/case_paths.py`：新增 `safe_case_dir(case_root, rel)`——校验强度与 safe_case_file 逐条同族（拒空值/绝对路径/空段/`.`/`..`、逐段拒 symlink、realpath 越根拒），额外要求目标存在且为目录。**独立实现，不重构 safe_case_file**（旧函数异常类型/must_exist 语义/逐段 symlink 行为逐字不变）。顶层模块 docstring（现为 "regular-file references" 表述）同步改写。
2. `scripts/report/handoff_manifest.py`（`validate_and_replay_provenance()` 及模块级）：
   - 模块级常量 `EVM_V2_EDGE_NAMES = ("logs.parquet", "blocks.parquet")` ＋ `EVM_V2_RUN_PREFIX = "run_"`，注释锚写明"与 wave_scan.load_evm_v2 / entity_source_trace.source_binding 的 run_*/logs.parquet、run_*/blocks.parquet 三处同源；那两文件禁改，同源性由守护测试锁死，唯一可改处在此"。
   - `kind=="evm_v2"` 分支，重放子进程启动前依序：
     a. argument 字符闸：除 containment 外额外拒绝 glob 元字符 `*` `?` `[` `]`、单引号 `'`、反斜杠、控制字符与换行（loader 把该路径拼进 glob 与 DuckDB SQL 字面量）；
     b. `safe_case_dir(case_dir, argument)` 目录 containment；
     c. 不跟随 symlink 的逐层枚举（不用递归 glob）：`os.scandir` 列直接子项，`entry.is_dir(follow_symlinks=False)` 且名字以 `run_` 开头才认作 run 目录（symlink 子目录当场拒）；每个 run 目录内只探测 `EVM_V2_EDGE_NAMES` 两个固定文件名，命中者逐件过 `safe_case_file`；run 目录内 pattern 外的普通文件不禁止存在（防误伤）但不计入集合；
     d. 集合闸：先逐条校验 source.files 记录结构（path 为字符串、无重复——重复即拒，不得被 set 静默去重），再比较"当前命中规范相对路径集合 === 登记路径集合"，任一方向差集非空即拒；错误信息有界（报总数＋各方向前 10 项）；
     e. 全部通过后才 mkstemp + subprocess 重放。
   - 其余 kind（sol/duckdb）继续走 resolve_bound_path 文件闸，逐字不动。
3. 新测试文件 `scripts/tests/test_lit_regression_f008.py`（清单见下）。
4. 本工程档案目录下的证据/报告文件。

**测试清单**：
- 原反例（先红后绿）：完整 evm_v2 溯源正例夹具（tmp 案根：run_1/logs.parquet＋blocks.parquet＋自造 ledger/manifest/data_map 最小闭环）→ 修前红（"路径不是常规文件"）；修后绿。须新造正例：单元层 mock ledger 断言分支行为＋至少一个真实最小 parquet 集成绿例（多 run 合法目录端到端过闸）。
- 攻击变体（全拒，且拒绝分支断言"未创建 .provenance-replay-* tempfile、未启动 subprocess"）：①目录塞未登记 run_evil/logs.parquet→拒；②run_evil 本身是指向案外目录的 symlink→拒（枚举层拒）；③登记文件被删→拒；④后代文件换成指向案外的 symlink→拒；⑤argument 为绝对路径/含 `..`/中段 symlink/指向普通文件/空串/`.`→拒；⑥argument 含 `*` `?` `[]` `'` 换行→拒；⑦source.files 含重复路径→拒；⑧source.files 登记了两 pattern 之外的文件→拒（集合不等）。
- 防误伤绿例：run 目录内存在 pattern 外普通文件（如 README）仍绿；sol/duckdb kind 冻结链仍绿。
- 同源守护测试：AST 级断言（非全文字符串匹配）——定位 `wave_scan.load_evm_v2` 与 `entity_source_trace.source_binding` 中的 glob 构造，断言 pattern 集与本闸常量精确相等、不存在第三个 evm glob、基目录分别为 `dir_`/`a.edges_evm_v2`；AST 解析失败或结构改写→fail-closed 红。
- safe_case_dir 单元面：合法目录过；上述路径类攻击逐条拒；与 safe_case_file 行为无串扰（safe_case_file 既有用例不受影响）。

**先红采证**：改代码前先写测试，在当前分支 HEAD 跑，原反例 FAIL 原始输出（含 EXIT_CODE）留档 `f008_red_evidence.txt`；改后全绿留档 `f008_green_evidence.txt`。

**定向回归（绿证阶段跑，结果进 green_evidence）**：`test_handoff_manifest.py`、`test_repair_g1_handoff_containment.py`、`test_evm_observation_release.py`、`test_audit_release_gate.py`。

## 收尾
- done 报告 `f008_done.md` 按 F-005 九段结构（同 f007 工单要求）。
- 归因栏三选一＋最强替代解释及不采纳理由（本 finding 预判"修复中新引入"——7b99867 收口把目录参数误收进文件闸；须自行验证）。
- 发现项（只记不修）：wave_scan.load_evm_v2 f-string 拼 DuckDB SQL 的注入面（本批以 argument 字符闸在消费入口挡住，loader 本体受禁改约束另立项）。
- 自产文档零 EOF 空行/行尾空格；原始输出留档含空白登记 diff_check_exemptions.md。
- 本批不动：版本三件/CHANGELOG/SUITE 登记/契约/references 文档（留批 3 收口）。

## 边界（硬性）
- **禁改**：scripts/report/wave_scan.py、scripts/report/entity_source_trace.py、scripts/solana/sqd_cache_identity.py（哈希绑定，改一字节=全部存量案算法漂移拒绝）；scripts/evm/replay_pass2.py、scripts/evm/replay_duck.py、scripts/solana/replay_edges.py；scripts/lib/camp_series_provenance.py、scripts/report/state_from_facts.py（F-007 批已收口面，本批不碰）。
- safe_case_file 函数体逐字不动（只在同文件新增 safe_case_dir 与模块 docstring 更新）。
- 白名单外文件一律不改；不 commit（Fable 代 commit）；不联网；工单外新发现只记录不修。
