# F-009 批 3 收口施工完成报告

## 结论

- F-009 登记面已按工单完成：版本三件为 `6.52.2`，SUITE 由 129 增至 131，契约与 ID 快照由 195 增至 197，现役文档已按 `series_format` 分家并补齐 evm_v2 目录输入/集合闸语义。
- 四项完成标准均 PASS：`changelog_lint.py`、`test_version_consistency.py`、`docs_lint.py --all`、`test_contract_routes.py` 全部 `EXIT_CODE=0`。
- `run_all.py` 实跑 131 项：129 PASS／2 FAIL。仅 `test_batch3_solana_vertical_slice.py` 与 `test_batch3_evm_vertical_slice.py` 因沙箱禁止 `127.0.0.1` bind，均为 `PermissionError: [Errno 1] Operation not permitted`；按工单不改测试、不伪报全绿。
- 本批未 commit、未联网、未改 F-007/F-008 已提交代码或工单禁改文件。

## 1. 开工门禁

命令：

```text
$ git branch --show-current
fix/lit-regression-v6522
$ git show -s --format='%h %s' 333144e
333144e repair-20260824-lit-regression 批1 F-007：堆叠豁免集按 series_format 内部固定映射（LIT dead-sink 假红修复）……
$ git show -s --format='%h %s' 6fdf911
6fdf911 repair-20260824-lit-regression 批2 F-008：evm_v2 目录参数重放前集合闸（7b99867 收口误伤回归修复）……
$ git status --short
(无输出)
EXIT_CODE=0
```

门禁结论：分支匹配；F-007=`333144e`、F-008=`6fdf911` 均为最近提交；开工时工作树干净。

## 2. 登记面施工

### 2.1 版本三件与 CHANGELOG

- `VERSION`：`6.52.2`
- `pyproject.toml [project].version`：`6.52.2`
- `SKILL.md`：仅版本注释等长替换为 `6.52.2`；`wc -c SKILL.md`=`7961`，满足 `≤8192`。
- `CHANGELOG.md`：新增 6.52.2 索引与详情，覆盖 F-007、F-008、SUITE 129→131、契约 195→197，并含成本/质量指标行。

### 2.2 SUITE

新增工单指定块：

```python
SUITE += ["test_lit_regression_f007.py", "test_lit_regression_f008.py"]  # v6.52.2 repair-20260824-lit-regression
```

AST 计数原始输出：

```text
SUITE_COUNT 131
SUITE_TAIL ['test_batch7_validator_coverage_gaps.py', 'test_lit_regression_f007.py', 'test_lit_regression_f008.py']
EXIT_CODE=0
```

runner 实际执行证据见 §6：F-007=`SUMMARY: 15/15 PASS`；F-008=`SUMMARY: 46/46 PASS`。

### 2.3 references 文档

- `references/scan-schemas.md` §4：明确 `source.argument` 为 sol/duckdb 文件、evm_v2 目录；补上 evm_v2 字符闸与“当前命中集合必须与 `source.files` 精确相等”的目录集合闸。
- `references/scan-schemas.md` §13 三处改为 `series_format` 分家：末点对账、formal 闭合、burn 口径均写明 `evm-dict`／`sol-rows`／`sol-anchor-rows` 的实际堆叠语义，并逐处带 `replay_pass2.py:84-116,139-145`、`replay_edges.py:648-657` 生产依据。
- `references/report-template.md:203`：formal 改为按 `series_format` 精确堆叠闭合；仅无 format 手填路径保留 dual。
- `references/split-run.md` §2.2 核对无旧表述，不需修改。

### 2.4 契约

- 新增 `CT-BANNED-23`：authority=`references/scan-schemas.md`，needle=`净分母族只认非 burn 之和`。
- 新增 `CT-SEMANTIC-63`：authority=`references/scan-schemas.md`，needle=`当前命中集合必须与 \`source.files\` 精确相等`。
- `contract_manifest.json` 与排序后的 `contract_ids_snapshot.json` 均为 197 条。
- 三判据：旧 banned needle 修前在 authority 精确命中；修后 authority 零命中；新 `series_format` 文案不含该旧字面。旧字面在 `contract_manifest.json` 的 banned needle 自身出现是契约定义，不是 authority 回流。

## 3. 定向验证原始证据

```text
$ python3 scripts/tests/changelog_lint.py
PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 44 条 + 归档 139 条
EXIT_CODE=0

$ python3 scripts/tests/test_version_consistency.py
PASS: M-03 version metadata consistent at 6.52.2
EXIT_CODE=0

$ python3 scripts/tests/docs_lint.py --all
PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）
EXIT_CODE=0

$ python3 scripts/tests/test_contract_routes.py
PASS: R-01/R-02 注册表、ID 快照、五组锚与 SKILL 原子阶段双向闭合
EXIT_CODE=0
```

F-007/F-008 定向测试原始摘要：

```text
$ python3 scripts/tests/test_lit_regression_f007.py
PASS: LIT legacy dead-sink endpoint
PASS: LIT net dead-sink closure
PASS: EVM net burn plus dead-sink
PASS: legacy burn_cum_pct consistency gate
PASS: retail endpoint tamper
PASS: dead-sink endpoint tamper
PASS: burn cannot rescue stack gap
PASS: illegal denominator
PASS: no-format dual compatibility
PASS: fixed format mapping
PASS: EVM dead-sink range
PASS: Solana burn disclosure
PASS: Solana anchor real stack
PASS: Solana anchor false oracle
PASS: Solana anchor burn_cum_pct consistency gate
SUMMARY: 15/15 PASS
EXIT_CODE=0

$ python3 scripts/tests/test_lit_regression_f008.py
PASS: real multi-run evm_v2 provenance replay
PASS: unregistered run_evil/logs.parquet rejected pre-spawn
PASS: symlink run directory rejected pre-spawn
PASS: deleted registered file rejected pre-spawn
PASS: descendant parquet symlink rejected pre-spawn
PASS: argument absolute rejected pre-spawn
PASS: argument dotdot rejected pre-spawn
PASS: argument ordinary-file rejected pre-spawn
PASS: argument empty rejected pre-spawn
PASS: argument dot rejected pre-spawn
PASS: argument asterisk rejected pre-spawn
PASS: argument question rejected pre-spawn
PASS: argument left-bracket rejected pre-spawn
PASS: argument right-bracket rejected pre-spawn
PASS: argument single-quote rejected pre-spawn
PASS: argument backslash rejected pre-spawn
PASS: argument newline rejected pre-spawn
PASS: argument control rejected pre-spawn
PASS: argument C1 U+0085 rejected by character gate pre-spawn
PASS: argument middle symlink rejected pre-spawn
PASS: duplicate source.files path rejected pre-spawn
PASS: non-object source.files record rejected pre-spawn
PASS: non-string source.files path rejected pre-spawn
PASS: registered pattern-external file rejected pre-spawn
PASS: safe_case_dir exported
PASS: safe_case_dir legal directory
PASS: safe_case_dir rejects ''
PASS: safe_case_dir rejects ' '
PASS: safe_case_dir rejects '/private/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/f008_q573s8_b/safe_dir/a/b'
PASS: safe_case_dir rejects 'a//b'
PASS: safe_case_dir rejects 'a/./b'
PASS: safe_case_dir rejects 'a/../b'
PASS: safe_case_dir rejects 'linked'
PASS: safe_case_dir rejects 'a/file'
PASS: safe_case_dir rejects 'missing'
PASS: safe_case_file still accepts regular file
PASS: safe_case_file still rejects directory
PASS: AST source guard wave_scan.load_evm_v2 frozen definitions and consumers
PASS: AST source guard entity_source_trace.source_binding all glob calls
PASS: AST source guard rejects concatenated third glob self-negative
PASS: AST wave guard rejects logs AugAssign self-negative
PASS: AST wave guard rejects blocks alias consumption self-negative
PASS: AST wave guard rejects swapped logs/blocks file mapping self-negative
PASS: AST wave guard rejects swapped logs/blocks SQL slots self-negative
PASS: sol replay dispatch remains green
PASS: duckdb replay dispatch remains green
SUMMARY: 46/46 PASS
EXIT_CODE=0
```

定向 F-007 首次运行另有 Matplotlib 因默认配置目录不可写而改用 `/var/folders/.../T/matplotlib-*` 的提示，不影响测试，退出码为 0。

## 4. 残留清点

命令范围：现役 `references/` 与 `scripts/`，排除 `archive/`、`maintenance/` 历史档案。

```text
$ rg -n --glob '!archive/**' --glob '!maintenance/**' '净分母族只认非 burn 之和|total 族只认全桶之和|两族不得互救' references scripts
scripts/tests/contract_manifest.json:200:    {"id":"CT-BANNED-23",..."needle":"净分母族只认非 burn 之和"...}
EXIT_CODE=0
```

归类：唯一精确命中是 `CT-BANNED-23` 自身，authority `references/scan-schemas.md` 为零命中；这是防回流契约，不是旧规则注释。`scripts/tests/test_repair_batch_c.py` 中“同点双式闭合／净分母族”字样属于无 `series_format` 的手填兼容回归，生产实现明确继续保留该历史路径，不是 formal 绑定路径的一刀切规则。`references/split-run.md` 对旧字面、`series_format` 均无命中，无需同步。

## 5. 其余登记核对

```text
$ python3 scripts/tests/invariant_scan.py
PASS invariant manifest: receipt_producers=75, receipt_consumers=112, transport_calls=65, atomic_writes=56, formal_entrypoints=61, exceptions=0
EXIT_CODE=0

$ git diff --exit-code HEAD -- scripts/tests/invariant_manifest.json
EXIT_CODE=0

$ git diff --exit-code HEAD -- scripts/lib/producer_history.py scripts/evm/collector_history.py
EXIT_CODE=0

$ git diff --exit-code HEAD -- scripts/report/wave_scan.py scripts/report/entity_source_trace.py scripts/solana/sqd_cache_identity.py scripts/evm/replay_pass2.py scripts/evm/replay_duck.py scripts/solana/replay_edges.py
(无输出)
EXIT_CODE=0
```

判断：F-007/F-008 的 `safe_case_dir`、常量与校验逻辑没有触发 invariant 计数变化，无需改 `invariant_manifest.json`。生产端产物字节零变化，本批不新增 `producer_history`／`collector_history` 条目。工单列明的禁改生产文件均与 HEAD 一致。

### 5.1 round2 返工

- 勘误：§5 原命令中的错误路径 `scripts/wave_scan.py`、`scripts/entity_source_trace.py`，分别修正为真实路径 `scripts/report/wave_scan.py`、`scripts/report/entity_source_trace.py`；§8 总边界命令同步显式使用真实路径。
- 归因：施工方自拟核验命令时发生路径笔误；`git diff --exit-code HEAD -- <不存在的路径>` 仍返回 0，该语义未暴露笔误，导致 Round 1 证据无效。
- 返工实跑：§5 六个禁改文件命令与 §8 invariant/history/六个禁改文件总边界命令均无原始输出，退出码均为 0；据此重新确认这些文件与 HEAD 一致。
- 边界记录：Round 2 当前 `git status --short` 还列出未跟踪的 `f009_rework_workorder.md` 与 `f009_review_verdict_round1.md`；二者是本轮指定的只读输入，不是施工方修改或自产文件。九个已跟踪登记面与全部代码均未在本轮改动。

## 6. 全量 run_all 原始失败证据与汇总

命令：`python3 scripts/tests/run_all.py`

原始失败块：

```text
--- test_batch3_solana_vertical_slice.py 完整输出 ---
Traceback (most recent call last):
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_batch3_solana_vertical_slice.py", line 646, in <module>
    raise SystemExit(main())
                     ~~~~^^
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_batch3_solana_vertical_slice.py", line 641, in main
    test_r9_solana_pythia_mainnet_vertical_slice()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/formal_capability_probes.py", line 145, in guarded
    return function(*args, **kwargs)
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_batch3_solana_vertical_slice.py", line 625, in test_r9_solana_pythia_mainnet_vertical_slice
    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/socketserver.py", line 457, in __init__
    self.server_bind()
    ~~~~~~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/http/server.py", line 148, in server_bind
    socketserver.TCPServer.server_bind(self)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/socketserver.py", line 478, in server_bind
    self.socket.bind(self.server_address)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
PermissionError: [Errno 1] Operation not permitted

--- test_batch3_evm_vertical_slice.py 完整输出 ---
Traceback (most recent call last):
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_batch3_evm_vertical_slice.py", line 353, in <module>
    raise SystemExit(main())
                     ~~~~^^
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_batch3_evm_vertical_slice.py", line 344, in main
    test_r9_eth_mainnet_vertical_slice()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/formal_capability_probes.py", line 145, in guarded
    return function(*args, **kwargs)
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_batch3_evm_vertical_slice.py", line 330, in test_r9_eth_mainnet_vertical_slice
    _run_registered_chain("eth")
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_batch3_evm_vertical_slice.py", line 281, in _run_registered_chain
    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/socketserver.py", line 457, in __init__
    self.server_bind()
    ~~~~~~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/http/server.py", line 148, in server_bind
    socketserver.TCPServer.server_bind(self)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/socketserver.py", line 478, in server_bind
    self.socket.bind(self.server_address)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
PermissionError: [Errno 1] Operation not permitted
```

原始 runner 尾部：

```text
FAIL(rc=1)  test_batch3_solana_vertical_slice.py (无输出)
FAIL(rc=1)  test_batch3_evm_vertical_slice.py (无输出)
      PASS  test_lit_regression_f007.py SUMMARY: 15/15 PASS
      PASS  test_lit_regression_f008.py SUMMARY: 46/46 PASS
========================================================
2 项失败——修完再收工
EXIT_CODE=1
```

实数结论：SUITE=131，PASS=129，FAIL=2；两项 FAIL 均为沙箱 loopback bind 权限限制，其余 129 项全绿。

## 7. 发现项与边界

1. 无新增生产逻辑 finding；本批只收登记面。
2. 全量仅有工单预告的两项 loopback 环境失败，未改测试绕过。
3. 施工期间出现一个非本批创建的未跟踪工程档案 `maintenance/repair-20260824-lit-regression/legacy_evm_v2_ledger_inventory.md`。它在开工门禁时不存在，后续由并发外部流程产生；位于 maintenance 允许目录，本批未读取、未修改、未删除，也不归入 F-009 自产文件。
4. `references/` 与 `scripts/` 的旧 formal 一刀切表述已清零；唯一精确旧 needle 命中为新增 banned 契约自身。无 format 手填兼容测试保留是 F-007 明定边界。
5. 未 commit；Fable 代 commit。未联网。

## 8. 最终自检

```text
$ git diff --check
(无输出)
EXIT_CODE=0

$ rg -n '[ \t]+$' CHANGELOG.md SKILL.md VERSION pyproject.toml references/report-template.md references/scan-schemas.md scripts/tests/contract_ids_snapshot.json scripts/tests/contract_manifest.json scripts/tests/run_all.py maintenance/repair-20260824-lit-regression/f009_closeout_done.md
(无输出)
EXIT_CODE=1（rg 零命中的正常退出码）

$ python3 <AST/JSON 只读计数>
SUITE=131 CONTRACTS=197 SNAPSHOT=197
F007_REGISTERED 1
F008_REGISTERED 1
EXIT_CODE=0

$ git diff --exit-code HEAD -- scripts/tests/invariant_manifest.json scripts/lib/producer_history.py scripts/evm/collector_history.py scripts/report/wave_scan.py scripts/report/entity_source_trace.py scripts/solana/sqd_cache_identity.py scripts/evm/replay_pass2.py scripts/evm/replay_duck.py scripts/solana/replay_edges.py
(无输出)
BOUNDARY_DIFF_EXIT=0
```

自产 Markdown 均以单个 LF 结尾，无 EOF 空白行；`git diff --check` 无行尾空格或空白错误。最终四项强制命令复跑仍全部 `EXIT_CODE=0`：

```text
PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 44 条 + 归档 139 条
PASS: M-03 version metadata consistent at 6.52.2
PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）
PASS: R-01/R-02 注册表、ID 快照、五组锚与 SKILL 原子阶段双向闭合
```

F-009 自产变更文件 SHA-256（done 报告自身哈希在最终交接消息给出）：

```text
fd7caddd90dec3cc94e5559533df4efed03576b6a1741dfb6889101d34bcd6a3  VERSION
fc94bef1ab05959834f6c1d9a1e3ff9cff1201c25937f03620ad8456c42f260e  pyproject.toml
b86571aa3ee950b2112afbad56066022808d4af8f706f24a33e503404e800467  SKILL.md
3014bbd8658b0e1448d3cd5349d92cc9deac2847b401562e40f4b7be574b1d16  CHANGELOG.md
81ea366f3515f39414ca4fa1762a8be235458523751da4ff7a4730d44120efba  scripts/tests/run_all.py
227bca96f5ccc314a1cd476800a671ec88f293ddf631c67ad75a35abb3c8d550  references/scan-schemas.md
c75d977ee282a1b1a2553541a13ec09018298ffbcaa3de18d020160d8dbd9b48  references/report-template.md
852278a674b50941b7e5d063c9da51daaf995321b95216f5fe380e65b55cfbbe  scripts/tests/contract_manifest.json
b28e4b5d9bd15259d0d8139c8ee78eec186e72cbe8f05b5c6914bb8f04e1e322  scripts/tests/contract_ids_snapshot.json
```

最终状态只含上述 9 个已跟踪登记面改动、F-009 done 报告，以及 §7 已声明的并发外来 maintenance 档案；无白名单外已跟踪改动。
