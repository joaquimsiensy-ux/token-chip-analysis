# F-008 evm_v2 重放前集合闸完成报告

## 结论

- F-008 已完成：`evm_v2` 的目录参数不再被通用常规文件闸误拒；真实两 run parquet 溯源台账可完成重放。
- 重放子进程启动前新增三层硬闸：argument 字符/案根目录 containment、固定两 pattern 的不跟随 symlink 枚举、当前命中集合与 `source.files` 登记集合严格相等。
- 完成物齐全：`f008_done.md`、`f008_red_evidence.txt`、`f008_green_evidence.txt`；新测试文件 `scripts/tests/test_lit_regression_f008.py` 为 40/40 PASS。
- 工单指定四组定向回归全部退出码 0：handoff 68 项、G1 containment 16/16、EVM observation release 11/11、audit release 十一类契约全过。
- 归因三选一：**修复中新引入**。`git show` 证明 `7b99867^` 的 `resolve_bound_path()` 仅作 `normpath`，`7b99867` 把它直接改为 `safe_case_file()`；后者明确只接受常规文件，因此原本合法的 evm_v2 目录从该提交起确定性报“路径不是常规文件”。
- 最强替代解释是“半修残留”：`7b99867` 的 containment 收口没有建立文件/目录类型分流，表面上可视为安全修复没做完。未采纳为主归因的理由是：LIT 正例在 `7b99867^` 的同一调用点可通过目录解析，而提交后的同一参数被新加入的文件类型断言直接拒绝，故回归触发点是该修复新引入；但“未登记新增文件可在拒绝前被 loader 读取”的集合缺口确属更早存在的历史漏检，本批一并闭合。

## 基线与施工边界

- 开工仓库：`/Users/uravvv/.claude/skills/token-chip-analysis`。
- 开工分支：`fix/lit-regression-v6522`，符合门禁。
- 开工 HEAD：`333144ebe5ac3c44a9ed749791209e41ce8f3837`；`git log --oneline -3` 首条为 F-007 裁判提交 `333144e`，符合门禁。
- 开工 `git status --short` 无输出，白名单目录外干净。
- 执行方式：离线、未 commit、未切分支；没有运行任何联网命令。工单自包含且禁止白名单外改动，因此未运行会改树的通用同步脚本。
- 生产代码只改 `scripts/lib/case_paths.py` 与 `scripts/report/handoff_manifest.py`；只新增工单允许的新测试及本目录三件档案。

### 第一步独立核实

| # | 裁决 | 独立理由 |
|---:|---|---|
| 1 | 属实 | `git show 7b99867^:scripts/report/handoff_manifest.py` 的 `:572-575` 仅检查非空后 `normpath`；`git show 7b99867:scripts/report/handoff_manifest.py` 的 `:625-627` 已改为 `safe_case_file`。开工 `case_paths.py:36-38` 对存在但非文件目标报“路径不是常规文件”。 |
| 2 | 属实 | 禁改生产端 `entity_source_trace.py:132-135` 将 `a.edges_evm_v2` 作为 argument，并用 `run_*/logs.parquet`、`run_*/blocks.parquet` 两个 glob 取文件；`:164-169` 把目录 argument 与逐件 file record 写入 binding。 |
| 3 | 属实 | 禁改消费端 `wave_scan.py:208-210` 构造相同两 pattern；`:214-218`、`:231-234` 将 pattern 字符串直接拼入 DuckDB `read_parquet` SQL 字面量。 |
| 4 | 属实 | 开工 handoff 对 `source.files` 只逐件走 `check_bound_file` 并要求路径同时出现在 manifest artifacts/data_map；manifest 与 data_map 本体另有完整哈希绑定，重放后 `provenance_semantic_sha` 终比。没有任何一处在 subprocess 前枚举 evm_v2 目录并比较“当前命中集合”，因此目录新增未登记 pattern 文件不会被这些防线提前发现。 |
| 5 | 属实 | `test_handoff_manifest.py:238-255` 的 `make_provenance()` 固定调用 `--edges-sol`；该文件 `:120-121` 的 `edges_evm_v2: data/v2` 只属于 wave report 参数夹具，不构成 evm_v2 provenance 重放正例。 |

五项均属实，锚点与实树语义一致，无需停工或猜测平移。

## 改动清单

1. `scripts/lib/case_paths.py`
   - 顶层 docstring 从“常规文件引用”扩为“常规文件与目录引用”。
   - 独立新增 `safe_case_dir(case_root, rel)`：拒空值、绝对路径、空段、`.`、`..`、逐段 symlink、realpath 越根；目标必须存在且为目录。
   - 未调用、重构或改写 `safe_case_file`；其函数体保持与开工 HEAD 逐字一致。
2. `scripts/report/handoff_manifest.py`
   - 新增 `EVM_V2_EDGE_NAMES=(logs.parquet, blocks.parquet)` 与 `EVM_V2_RUN_PREFIX=run_`，邻接注释明确三处同源、两个禁改算法文件及 AST 守卫。
   - 新增 evm_v2 argument 字符闸：拒 `* ? [ ] ' \\`、换行和全部控制字符，再走 `safe_case_dir`。
   - 新增两层 `os.scandir` 枚举：只认非 symlink 的 `run_*` 真目录及两个固定文件名；固定文件逐件走 `safe_case_file`，run 内 README 等 pattern 外普通文件不计入集合也不误拒。
   - `source.files` 逐条验证对象/path 字符串并显式拒重复；当前集合与登记集合双向做差，错误只披露总数及各方向前 10 项。
   - 集合闸通过后才创建 `.provenance-replay-*` tempfile 并启动 subprocess；sol/duckdb 继续走既有 `resolve_bound_path` 文件闸。
3. `scripts/tests/test_lit_regression_f008.py`
   - 新增真实两 run parquet、最小 ledger/manifest/data_map 闭环与端到端真实重放。
   - 新增未登记命中、run symlink、删件、后代文件 symlink、argument 路径/字符全集、重复/坏结构登记、pattern 外登记等攻击反例；每条同时断言未创建 replay tempfile、未启动 subprocess。
   - 新增 README 防误伤、safe_case_dir 单元面、safe_case_file 无串扰、sol/duckdb mock dispatch 绿例。
   - 新增 fail-closed AST 同源守卫，结构化锁定 loader/producer 的基目录、`run_*` 与精确两个 parquet 名称。
4. 工程档案
   - 新增红证、绿证与本完成报告。

## 前后对照

改前，所有 kind 的 argument 无条件走文件闸：

```python
kind = source.get("kind")
try:
    arg = resolve_bound_path(case_dir, source.get("argument"))
except ValueError as e:
    return [f"source argument 异常: {e}"]
```

改后，只有 `evm_v2` 走目录字符闸、目录 containment、固定集合枚举和集合等值；其余 kind 保留原文件闸：

```python
if kind == "evm_v2":
    arg = validate_evm_v2_argument(case_dir, argument)
    current_paths = enumerate_evm_v2_sources(case_dir, argument, arg)
    ...
    disk_only = sorted(current_paths - registered_set)
    ledger_only = sorted(registered_set - current_paths)
    if disk_only or ledger_only:
        return [bounded_error]
else:
    arg = resolve_bound_path(case_dir, source.get("argument"))
```

威胁模型：集合闸保证成立的前提是从集合校验完成到重放子进程退出期间，案目录没有并发写者。校验与实际读取之间仍有 TOCTOU 窗口，这是已知残余风险，不在 F-008 闭合范围；同一说明已写入生产代码邻接注释。

## 先红后绿原始输出

### RED

生产代码改动前运行：

```text
COMMAND: MPLCONFIGDIR=/tmp/f008-mpl-cache PYTHONPYCACHEPREFIX=/tmp/f008-pycache python3 scripts/tests/test_lit_regression_f008.py --red-only
FAIL: real multi-run evm_v2 provenance replay: ["source argument 异常: 路径不是常规文件: 'data/ethereum/v2'"]
SUMMARY: 0/1 PASS
EXIT_CODE=1
```

完整留档：`maintenance/repair-20260824-lit-regression/f008_red_evidence.txt`。

### GREEN

最终状态新测试摘要：

```text
PASS: real multi-run evm_v2 provenance replay
...
PASS: AST source guard entity_source_trace.source_binding exact two patterns
PASS: sol replay dispatch remains green
PASS: duckdb replay dispatch remains green
SUMMARY: 40/40 PASS
EXIT_CODE=0
```

新测试和四组定向回归的完整命令、stdout/stderr 与退出码逐字留档于 `maintenance/repair-20260824-lit-regression/f008_green_evidence.txt`（156 行）。

## 残留清点

- `rg` 与 AST 守卫确认 evm_v2 同源 pattern 仍只有两组：`run_*/logs.parquet`、`run_*/blocks.parquet`；基目录分别是 loader 的 `dir_` 与 producer 的 `a.edges_evm_v2`。
- `run_*` 目录内 pattern 外普通文件允许存在且不计入集合；若 ledger 反向登记这类文件，因集合不等而拒。
- 错误输出有界：只报 `disk_only_count`、`ledger_only_count` 及各方向前 10 项，不把大目录清单灌入日志。
- `safe_case_file` 函数体未改；sol/duckdb 分支仍用它，既有 containment 和 handoff 回归全绿。
- 集合闸不消除并发写者导致的 TOCTOU；没有把该残余风险描述为已修复。

## lint 与测试证据

- `PYTHONPYCACHEPREFIX=/tmp/f008-pycache python3 -m py_compile scripts/lib/case_paths.py scripts/report/handoff_manifest.py scripts/tests/test_lit_regression_f008.py`：退出码 0。
- `python3 scripts/tests/test_lit_regression_f008.py`：40/40 PASS，退出码 0。
- `python3 scripts/tests/test_handoff_manifest.py`：68 项全部通过，退出码 0。
- `python3 scripts/tests/test_repair_g1_handoff_containment.py`：16/16 PASS，退出码 0。
- `python3 scripts/tests/test_evm_observation_release.py`：11/11 PASS，退出码 0。
- `python3 scripts/tests/test_audit_release_gate.py`：十一类契约全过，退出码 0。
- `git diff --check`：无输出，退出码 0。
- 新测试与自产档案无行尾空格；红/绿原始留档也无行尾空格，因此无需新增 `diff_check_exemptions.md`。
- 未运行全量 `run_all.py`：工单验收面明确为新测试加四组定向回归，且本批禁止改 SUITE 登记；未把未运行项表述为已通过。

## 发现项（只记录，不修）

- `wave_scan.load_evm_v2` 把 `logs`/`blocks` pattern 直接拼入 DuckDB SQL 字面量，存在独立的 loader 注入面。本批已在 handoff 消费入口以 argument 字符闸挡住这些字符，但 `wave_scan.py` 是哈希绑定禁改文件，loader 本体未修；应另立项处理，不能把入口缓解写成全局根治。
- 未发现其他需要越出本工单白名单修复的问题。

## 收工边界

- 只修改 `scripts/lib/case_paths.py`、`scripts/report/handoff_manifest.py`；只新增 `scripts/tests/test_lit_regression_f008.py` 与本工单三件档案。
- 未改版本三件、CHANGELOG、SUITE、契约、references 文档；这些继续留给批 3 收口。
- 禁改文件 `wave_scan.py`、`entity_source_trace.py`、`sqd_cache_identity.py`、三个 replay 文件、`camp_series_provenance.py`、`state_from_facts.py` 的 SHA-256 均与开工冻结值一致。
- 未删除文件；未联网；未 commit；未 push。
- 三件完成物齐全且新测试全绿，F-008 到此收工，不进入 F-009。

## Round 2 返工闭合（2026-08-24）

### 结论

- round1 盲审的两项 BLOCK 已按 `f008_rework_workorder.md` 三条最小清单闭合。
- 字符闸现在拒绝完整 Unicode `Cc` 类控制字符；新增 U+0085（C1）反例，并明确断言由字符闸在 tempfile/subprocess 之前拒绝。
- AST 同源守卫现在逐个盘点目标函数内全部 `glob.glob` 调用；调用数、参数形状、冻结 pattern、基目录或消费点任一漂移，以及任何无法解析的构造，都会硬失败。
- `f008_green_evidence.txt` 已覆盖重建为 round2 的 158 行原始输出；F-008 为 42/42 PASS，四组定向回归均为退出码 0。round1 红证未改。

### 过度声明修正与前后对照

1. round1 `f008_done.md:41` 原文“换行和全部控制字符”在当时实现下过度声明：旧实现仅判 `ord(ch)<32` 或 `ord(ch)==127`，未覆盖 C1。
   - round2 准确实现：`scripts/report/handoff_manifest.py:36` 引入 `unicodedata`，`:701-708` 以 `unicodedata.category(ch)=="Cc"` 拒绝完整 Unicode `Cc` 类，同时保留 glob 元字符、单引号和反斜杠拒绝。
   - round2 反例：`scripts/tests/test_lit_regression_f008.py:249-256` 注入 U+0085，既要求错误命中“含 glob/SQL/控制字符”，又复用 `reject_before_replay` 证明 tempfile/subprocess 均未发生。
   - 修正后的准确表述：**evm_v2 argument 字符闸拒绝冻结字符集及所有 Unicode `Cc` 类控制字符；该结论仅适用于此入口字符闸。**
2. round1 `f008_done.md:49` 原文“fail-closed AST 同源守卫”在当时解析器会对未知形状返回 `None` 的情况下过度声明。
   - round2 准确实现：`scripts/tests/test_lit_regression_f008.py:319-332` 的形状解析器对未知/偏离构造直接抛错；`:343-385` 盘点 producer 全部三个 `glob.glob` 调用并精确冻结为一个 sol glob、两个 evm glob；`:398-451` 精确冻结 wave 的两个 `os.path.join` pattern 定义、唯一 `glob.glob(logs)` 调用和 `logs=4`、`blocks=1` 的全部消费点。
   - round2 自测反例：`scripts/tests/test_lit_regression_f008.py:464-479` 构造字符串拼接的第三个 glob，并断言守卫必须拒绝。
   - 修正后的准确表述：**当前两目标函数的冻结 AST 形状受 fail-closed 守卫约束；新增调用、无法解析、pattern/基目录/调用数/消费点偏离均失败。**

### Round 2 测试与边界

- `python3 scripts/tests/test_lit_regression_f008.py`：42/42 PASS，退出码 0。
- `python3 scripts/tests/test_handoff_manifest.py`：68 项全部通过，退出码 0。
- `python3 scripts/tests/test_repair_g1_handoff_containment.py`：16/16 PASS，退出码 0。
- `python3 scripts/tests/test_evm_observation_release.py`：11/11 PASS，退出码 0。
- `python3 scripts/tests/test_audit_release_gate.py`：十一类契约全过，退出码 0。
- `python3 -m py_compile scripts/report/handoff_manifest.py scripts/tests/test_lit_regression_f008.py` 与 `git diff --check`：退出码 0。
- 本轮未改 `scripts/lib/case_paths.py` 或九个禁改生产文件；未联网、未 commit、未删除文件，未进入 F-009。

## Round 3 返工闭合（2026-08-24）

### 结论

- round2 盲审唯一残余 BLOCK 已按 `f008_rework2_workorder.md` 三条逐项闭合；本轮只改测试与工程档案，生产代码零改动。
- `guard_wave_globs()` 现对 `load_evm_v2` 全函数 AST 中 `logs`/`blocks` 的每个绑定、声明、删除与读取节点逐项分类；任何未分类节点、额外绑定或非白名单读取均硬失败。
- 两个源码字符串注入变体已固化为自测：`logs += "/unexpected"` 与 `b2 = blocks` 均要求守卫抛出 `AssertionError`；最终绿证中两项均为 PASS。
- `f008_green_evidence.txt` 已覆盖重建为 round3 的 160 行原始输出；F-008 为 44/44 PASS，四组定向回归均为退出码 0。round1 红证未改。

### 三条返工逐项闭合

1. `scripts/tests/test_lit_regression_f008.py:388-416` 盘点不会表现为 `ast.Name` 的标识符绑定，包括参数、函数/类名、import alias、except alias、global/nonlocal、match 绑定和类型参数；命中 `logs`/`blocks` 即失败。
2. `scripts/tests/test_lit_regression_f008.py:443-524` 遍历全函数全部 `ast.Name`：每个变量只允许一次位于函数体顶层、单目标、无 type comment 的直接 `Assign`，且值必须为 `os.path.join(dir_, "run_*", <冻结常量文件名>)`；`AugAssign`、`AnnAssign`、`NamedExpr`、for/with target、嵌套/重复赋值、`del` 及任何其他 `Store`/`Del` 形状都会进入硬失败分支。
3. 同段将全部 `Load` 逐件归类：唯一允许的 glob 消费是精确 `glob.glob(logs)`；SQL 消费必须是无 conversion/format spec 且直接夹在 `read_parquet('` 与 `',` 之间的 f-string 槽位，并冻结为 logs 三处、blocks 一处。无法分类、计数漂移或新增白名单外消费均失败。

### 注入自测与先红后绿

- `scripts/tests/test_lit_regression_f008.py:527-558` 从当前 `wave_scan.py` 源码构造内存变体，不改生产文件；`:587-590` 分别注入 `logs += "/unexpected"` 和 `b2 = blocks`。
- 先加自测、尚未重写守卫时，完整 F-008 输出为 43/44 PASS、退出码 1；唯一失败为 `AST wave guard rejects logs AugAssign self-negative`，复现 round2 盲审缺口。blocks 别名消费已被旧读取计数拒绝，作为第二种攻击形状继续冻结。
- 守卫重写后相同完整测试为 44/44 PASS、退出码 0；两项源码变体均证实守卫会红。

### Round 2 过度声明再次修正

- round2 `f008_done.md:152-164` 所称“任一漂移都会硬失败”仍属过度声明，因为当时 `AugAssign` 的 `Store` 节点没有进入定义或读取盘点，`logs += "/unexpected"` 可漏过。
- round3 修正后的准确表述：**在 Python 当前 AST 可表示范围内，`load_evm_v2` 中标识符 `logs`/`blocks` 仅允许各一次冻结形状的顶层直接赋值；所有 `ast.Name` 绑定/删除/读取节点及不表现为 `ast.Name` 的已枚举标识符绑定均须被分类，只有冻结的 glob 与 read_parquet f-string 消费形状可放行，其他形状 fail-closed。**
- 此修正只约束测试中的源形状守卫，不把它表述为生产 loader 的运行时输入净化，也不扩大 F-008 的生产修复范围。

### Round 3 测试与边界

- `python3 scripts/tests/test_lit_regression_f008.py`：44/44 PASS，退出码 0。
- `python3 scripts/tests/test_handoff_manifest.py`：68 项全部通过，退出码 0。
- `python3 scripts/tests/test_repair_g1_handoff_containment.py`：16/16 PASS，退出码 0。
- `python3 scripts/tests/test_evm_observation_release.py`：11/11 PASS，退出码 0。
- `python3 scripts/tests/test_audit_release_gate.py`：十一类契约全过，退出码 0。
- 开工/收工 SHA-256 一致：`case_paths.py`=`bcc0952855c208a313a0584ee6faf3a89288f011e9de3ddfed15ea829723e562`，`handoff_manifest.py`=`f31aecbb73035ebd62ccd7a2ffad02b1a384fb1e9b10ec65c82421264717594d`，`wave_scan.py`=`9f8c176eff0592f6173eb7d8b7edf28cd47c07f986f703af74f063c20cbcbdc8`，`entity_source_trace.py`=`fe70ddc95aa2536423b8f149314cfc7d0fd1d9ddc9ed4c8b54341deff360cb2a`。
- round1 红证 SHA-256 开工/收工均为 `3a9eb7a6548c5cea599667a5b35eca0103f52613fa3295a99d87e03f2983bd97`；`python3 -m py_compile` 与 `git diff --check` 均为退出码 0。
- 本轮未改 `scripts/lib/case_paths.py`、`scripts/report/handoff_manifest.py`、`scripts/report/wave_scan.py` 或 `scripts/report/entity_source_trace.py`；未联网、未 commit、未删除文件，未进入 F-009。

## Round 4 返工闭合（2026-08-24）

### 结论

- round3 盲审的两个残余 BLOCK 已按 `f008_rework3_workorder.md` 四条逐项闭合；本轮只改 `scripts/tests/test_lit_regression_f008.py` 与本工程档案，生产代码零改动。
- `guard_wave_globs()` 不再用无身份的 `set(shapes)` 验收定义：`logs` 唯一映射固定为 `os.path.join(dir_, "run_*", "logs.parquet")`，`blocks` 唯一映射固定为 `os.path.join(dir_, "run_*", "blocks.parquet")`。
- `logs`/`blocks` 的五个读取节点均生成“变量名＋所属语句＋调用类型＋调用槽位＋f-string 槽位”签名，并以完整列表精确比对；不再用 logs 三处、blocks 一处的数量验收。
- 两个内存 AST 自测反例均已固化并转绿：交换 `logs`/`blocks` 文件名映射必拒，交换 `body` SQL 中 `logs`/`blocks` 消费槽位必拒。

### 四条返工逐项闭合

1. `scripts/tests/test_lit_regression_f008.py:530-586` 保留每变量唯一顶层直接 `Assign` 的形状约束，并在 `:574-586` 以变量名为键精确冻结 `logs→("run_*", "logs.parquet")`、`blocks→("run_*", "blocks.parquet")`；交换两者不再因集合相等而漏过。
2. `scripts/tests/test_lit_regression_f008.py:419-527` 生成读取签名；`:594-611` 冻结并精确比对五项签名全集：`glob.glob` 的 `If/arg[0]=logs`，`n_hi,mx` 的 `con.execute/arg[0]/fstring[0]=logs`，`body` 的 `direct-fstring/value/fstring[1]=logs` 与 `fstring[2]=blocks`，以及 `spans` 的 `con.execute/arg[0]/fstring[0]=logs`。重复、缺失、变量换位、所属语句或调用/槽位漂移均失败。
3. `scripts/tests/test_lit_regression_f008.py:648-700` 在内存深拷贝 AST 上分别交换文件名映射和 `body` SQL 槽位；`:733-736` 将两项作为独立自测。仅加自测、尚未修守卫时，完整 F-008 恰为 `44/46 PASS`、退出码 1，唯一失败就是这两项；守卫修正后为 `46/46 PASS`、退出码 0。
4. `f008_green_evidence.txt` 已覆盖重建为 round4 的 162 行原始输出：F-008 `46/46 PASS`，四组定向回归全部退出码 0；既有 `f008_red_evidence.txt` 内容与 SHA-256 均未改变。

### Round 3 过度声明修正

- round3 `f008_done.md:181` 所称“每个绑定、声明、删除与读取节点逐项分类；任何未分类节点、额外绑定或非白名单读取均硬失败”只在节点形状分类层面成立，未冻结定义变量与文件名的一一映射，也未冻结每个已分类 SQL 读取的具体槽位；两个交换反例因此仍可放行。
- round3 `f008_done.md:200` 所称“只有冻结的 glob 与 read_parquet f-string 消费形状可放行，其他形状 fail-closed”过度概括了当时的精度：当时只冻结消费类别与 `logs=3/blocks=1` 数量，没有冻结同一类别内部的语句、调用和槽位身份。
- round4 修正后的准确表述：**`load_evm_v2` 的 `logs`/`blocks` 定义受变量名到完整 `os.path.join` 形状的一一映射约束；所有读取节点须逐一匹配冻结的变量名、所属语句、调用类型、调用槽位及 f-string 槽位签名全集，定义互换或消费槽位互换均 fail-closed。**该结论仍只约束测试中的源码形状守卫，不扩张为生产 loader 的运行时输入净化结论。

### Round 4 测试与边界

- `python3 scripts/tests/test_lit_regression_f008.py`：46/46 PASS，退出码 0。
- `python3 scripts/tests/test_handoff_manifest.py`：68 项全部通过，退出码 0。
- `python3 scripts/tests/test_repair_g1_handoff_containment.py`：16/16 PASS，退出码 0。
- `python3 scripts/tests/test_evm_observation_release.py`：11/11 PASS，退出码 0。
- `python3 scripts/tests/test_audit_release_gate.py`：十一类契约全过，退出码 0。
- 开工/收工 SHA-256 一致：`case_paths.py`=`bcc0952855c208a313a0584ee6faf3a89288f011e9de3ddfed15ea829723e562`，`handoff_manifest.py`=`f31aecbb73035ebd62ccd7a2ffad02b1a384fb1e9b10ec65c82421264717594d`，`wave_scan.py`=`9f8c176eff0592f6173eb7d8b7edf28cd47c07f986f703af74f063c20cbcbdc8`，`entity_source_trace.py`=`fe70ddc95aa2536423b8f149314cfc7d0fd1d9ddc9ed4c8b54341deff360cb2a`。
- round1 红证 SHA-256 开工/收工均为 `3a9eb7a6548c5cea599667a5b35eca0103f52613fa3295a99d87e03f2983bd97`；round4 绿证 SHA-256 为 `d80c984909d78acdfee56336155073fd14c1997848df143cc7ac8fb05a61faa9`。
- 本轮未改任何生产代码；未联网、未 commit、未删除文件，未进入 F-009。
