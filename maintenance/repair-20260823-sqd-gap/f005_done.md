# F-005 Solana reconcile v3/v4 文档漂移更正完成报告

## 结论

- F-005 的三处文档漂移、`CT-BANNED-22` 防再漂守卫、ID 快照和 6.52.1 版本登记均已完成。
- 定向红→绿成立；docs lint、CHANGELOG lint、契约快照和版本一致性均通过。
- 完整 129 项 `run_all.py` 已实际运行，结果为 127 PASS／2 FAIL。两项失败都发生在测试 fixture 的 `127.0.0.1` 监听绑定，原始异常为 `PermissionError: [Errno 1] Operation not permitted`；当前受限沙箱不允许 loopback bind。没有把该环境失败伪报成 129/129，也没有越过白名单修改测试或扫描器。

## 基线与施工边界

- 开工 HEAD：`8fb6c04`
- 开工 `VERSION`：`6.52.0`
- 开工工作树：干净
- 执行方式：离线、未 commit、未切分支。
- `SKILL.md` 开工与收工均为 7961B，只改版本注释行。
- 写入严格限制在工单列出的 8 个白名单文件；没有修改任何 `scripts/lib`、`scripts/report`、`scripts/solana`、`docs_lint.py` 或其他扫描器实现。

## 改动清单

1. `references/scan-schemas.md`：更正 inputs 表格、consumer 登记面、formal 来源链三处 v3 正向旧口径；正式 current 改为 v4 envelope，v2/v3 明确归 legacy。
2. `scripts/tests/contract_manifest.json`：新增 banned 契约 `CT-BANNED-22`，精确禁止 `references/scan-schemas.md` 出现 `只认 \`solana-reconcile/v3\``。
3. `scripts/tests/contract_ids_snapshot.json`：同步加入 `CT-BANNED-22`，契约分母 194→195。
4. `CHANGELOG.md`：新增 6.52.1 索引和详情，注明来源是外部全量审查 finding，并登记三处更正和守卫。
5. `VERSION`、`pyproject.toml`、`SKILL.md`：版本同步为 6.52.1。
6. `maintenance/repair-20260823-sqd-gap/f005_done.md`：本报告。

## 三处更正前后对照

### 1. inputs 表格

更正前：

```text
Solana 收据 v3 自带同次重放实算的逻辑边摘要/行数并对锚 cache meta；cache meta 另登记 edge_file_size＋edge_file_sha256 物理指纹
```

更正后：

```text
Solana 收据 v4 把 v3 全字段装入 formal envelope（其中三项供应量 raw 值收紧为 JSON int），并强制 target/mode/verdict/exit_code/producer/inputs/edge_source_binding；同次重放实算的逻辑边摘要/行数继续对锚 cache meta，边实物的 size/sha256 则由 inputs.soltx_edges 与 edge_source_binding 绑定
```

代码依据：

- `scripts/lib/receipt_kernel.py:126-177`：构造并终结带 target、producer、mode、inputs、verdict、exit_code 的 envelope。
- `scripts/solana/replay_edges.py:498-527`：冻结并三验本次实际消费的 inputs，签出 `solana-reconcile/v4`，写入 `edge_source_binding`。
- `scripts/lib/solana_exact_validate.py:1502-1550`：校验 target、三元 verdict、条件 input key set 与 binding 形状。

### 2. consumer 登记面

更正前：

```text
sol-rows 只认 solana-reconcile/v3；验 producer、三输入实物；v2 明确拒绝；边实物对锚 cache meta 的 edge_file_size/edge_file_sha256。
```

更正后：

```text
sol-rows 只认 solana-reconcile/v4；验 formal envelope 的 target/mode/verdict/exit_code、producer、base/repaired 条件 inputs、edge_source_binding 与当前 resolver 全等；v2/v3 均归 legacy 并要求重跑；边实物对锚 inputs.soltx_edges.size/sha256。
```

代码依据：

- `scripts/lib/camp_series_provenance.py:407-408`：current=`solana-reconcile/v4`，legacy={`v2`,`v3`}。
- `scripts/lib/camp_series_provenance.py:517-524`：v2/v3 单独按 legacy fail-closed，其他非 v4 schema 也拒收。
- `scripts/lib/camp_series_provenance.py:535-593`：校验 gate、精确整数、案 target、窗口、摘要与 producer。
- `scripts/lib/camp_series_provenance.py:595-649`：解析条件 inputs，要求 receipt/sidecar/resolver 的 `edge_source_binding` 全等，并按编译/发布强度校验边实物 size/sha256。
- `scripts/report/shared_release_receipt.py:1359-1369`：exact reconcile 只接受 v4 formal 全平并调用独立深验。

### 3. formal 来源链段

更正前：

```text
Solana reconcile v3 则由编译与发布两处各自传入案 target，逐项验证大小写敏感 mint、窗口、producer、三输入和边摘要对锚。
```

更正后：

```text
Solana reconcile v4 则由编译与发布两处各自传入案 target，逐项验证 formal envelope 的 target/mode/verdict/exit_code、大小写敏感 mint、窗口、producer、base/repaired 条件 inputs、edge_source_binding 与当前 resolver 全等及边摘要对锚；v2/v3 legacy 收据一律拒收并要求重跑。
```

代码依据同上；独立深验入口为 `scripts/lib/solana_exact_validate.py:1561`。

受保护的 `references/scan-schemas.md:41`、`:121`、§14.9（收工时 `:1001-1009`）未修改。

## banned needle 设计与先红后绿

选择的 needle：

```text
只认 `solana-reconcile/v3`
```

理由：它在更正前的正向 current consumer 句精确命中一次；更正后清零；合法的“v2/v3 legacy 拒收”不含该字面。现有 `docs_lint.py` 会直接读取 manifest 中指定的 `authority_file`，所以能够覆盖 `references/scan-schemas.md`，而该条不会扫描 CHANGELOG/archive。

### RED

登记 `CT-BANNED-22` 并同步快照后、文档更正前运行：

```bash
python3 scripts/tests/docs_lint.py --all
```

原始输出：

```text
FAIL: 禁用 needle 回捡 CT-BANNED-22: references/scan-schemas.md → 只认 `solana-reconcile/v3`
EXIT_CODE=1
```

### GREEN

完成文档更正后运行同一命令：

```text
PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）
EXIT_CODE=0
```

快照定向测试：

```bash
python3 scripts/tests/test_contract_routes.py
```

原始输出：

```text
PASS: R-01/R-02 注册表、ID 快照、五组锚与 SKILL 原子阶段双向闭合
EXIT_CODE=0
```

JSON/快照复算：

```text
manifest_json=PASS
snapshot_json=PASS
manifest_count=195 snapshot_count=195 sorted_equal=True
```

## `solana-reconcile/v3` 全量残留清点

命令：

```bash
rg -n 'solana-reconcile/v3' references/ scripts/
```

原始输出与分类：

```text
scripts/lib/camp_series_provenance.py:408:LEGACY_RECONCILE_SCHEMAS = {"solana-reconcile/v2", "solana-reconcile/v3"}
```

- 合法 legacy 拒收集合；不是正向 current 口径。

```text
scripts/tests/contract_manifest.json:198:    {"id":"CT-BANNED-22","kind":"banned","authority_file":"references/scan-schemas.md","needle":"只认 `solana-reconcile/v3`","stages":["A3","A5"]}
```

- 守卫定义自身；只在指定 authority file 查找禁词。

```text
scripts/tests/test_sqd_gap_repair.py:629:            "schema": "solana-reconcile/v3", "gate_pass": False,
scripts/tests/test_sqd_gap_repair.py:685:            "schema": "solana-reconcile/v3", "gate_pass": True}), encoding="utf-8")
```

- 两处均为 repair 回归的旧 schema fixture；不是现役 schema 声明或 consumer 正向接受口径。

`references/` 残留为零；不存在未归类的正向 current v3 口径。

## 版本、lint 与全测证据

### 版本三件一致

```text
VERSION=6.52.1
pyproject.toml:15:version = "6.52.1"
SKILL.md:23:<!-- skill-version-source: VERSION; skill-version: 6.52.1 -->
SKILL.md bytes=7961
```

版本测试原始输出：

```text
PASS: M-03 version metadata consistent at 6.52.1
```

### CHANGELOG lint

写入前基线原始输出：

```text
PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 42 条 + 归档 139 条
EXIT_CODE=0
```

写入后原始输出：

```text
PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 43 条 + 归档 139 条
```

### docs lint

```text
PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）
```

### 完整 run_all

命令：

```bash
python3 scripts/tests/run_all.py
```

runner 实际分母：129。结果：127 PASS／2 FAIL，退出码 1。两项失败的原始输出：

```text
--- test_batch3_solana_vertical_slice.py 完整输出 ---
Traceback (most recent call last):
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_batch3_solana_vertical_slice.py", line 646, in <module>
    raise SystemExit(main())
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_batch3_solana_vertical_slice.py", line 641, in main
    test_r9_solana_pythia_mainnet_vertical_slice()
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/formal_capability_probes.py", line 145, in guarded
    return function(*args, **kwargs)
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_batch3_solana_vertical_slice.py", line 625, in test_r9_solana_pythia_mainnet_vertical_slice
    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/socketserver.py", line 457, in __init__
    self.server_bind()
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/http/server.py", line 148, in server_bind
    socketserver.TCPServer.server_bind(self)
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/socketserver.py", line 478, in server_bind
    self.socket.bind(self.server_address)
PermissionError: [Errno 1] Operation not permitted

--- test_batch3_evm_vertical_slice.py 完整输出 ---
Traceback (most recent call last):
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_batch3_evm_vertical_slice.py", line 353, in <module>
    raise SystemExit(main())
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_batch3_evm_vertical_slice.py", line 344, in main
    test_r9_eth_mainnet_vertical_slice()
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/formal_capability_probes.py", line 145, in guarded
    return function(*args, **kwargs)
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_batch3_evm_vertical_slice.py", line 330, in test_r9_eth_mainnet_vertical_slice
    _run_registered_chain("eth")
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_batch3_evm_vertical_slice.py", line 281, in _run_registered_chain
    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/socketserver.py", line 457, in __init__
    self.server_bind()
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/http/server.py", line 148, in server_bind
    socketserver.TCPServer.server_bind(self)
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/socketserver.py", line 478, in server_bind
    self.socket.bind(self.server_address)
PermissionError: [Errno 1] Operation not permitted
```

runner 终端汇总原文：

```text
FAIL(rc=1)  test_batch3_solana_vertical_slice.py (无输出)
FAIL(rc=1)  test_batch3_evm_vertical_slice.py (无输出)
2 项失败——修完再收工
```

与本工单直接相关的 suite 项均为 PASS：

```text
PASS  changelog_lint.py
PASS  docs_lint.py --all
PASS  test_contract_routes.py
PASS  test_version_consistency.py
PASS  test_sqd_consumer_v4.py
PASS  test_sqd_gap_repair.py
PASS  test_reconcile_v4_receipt.py
PASS  test_recon_fifth_check.py
PASS  test_batch7_validator_coverage_gaps.py
```

## 发现项（只记录，不修正）

1. 当前执行沙箱禁止进程监听 loopback，即使地址为 `127.0.0.1:0`；因此两个真实 fixture vertical slice 无法在本会话内达到绿态。这是环境权限阻断，不是本次文档/manifest 改动导致的测试断言失败。按白名单和“不改扫描器/代码”边界，未修改测试绕过该限制。
2. 未发现其他工单外问题。

## 收工边界

- `git diff --check`：无输出，退出码 0。
- 未联网、未 commit。
- 未删除文件。
- 未改 §14 或原 :41/:121 的正确 v4 表述。
- 未改白名单外文件。
