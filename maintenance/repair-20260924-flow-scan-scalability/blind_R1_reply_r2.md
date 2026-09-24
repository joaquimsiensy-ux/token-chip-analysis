# 盲审R1 r2：PASS

按本轮“环境阻断不计 FAIL”的规则判定。**未发现代码失败项，但正式三入口对照、真实 EVM parquet 执行计划及五个测试未完成，不能理解为全部验收已通过。**

审查对象：`634c083..81269f81f7de6e6684f3f9f064911e70dd63ece6`。全程离线、未修改仓库文件、未 commit。未读取 `~/.codex/`、memories 或其他禁读内容；未读取施工者证据、历史审查报告或探针结论。

**1. 范围：通过**

按指定命令排除本工程文档目录后，输出恰为：

```text
CHANGELOG.md
SKILL.md
VERSION
pyproject.toml
scripts/report/flow_anomaly_scan.py
scripts/tests/test_flow_anomaly.py
```

其他核验：

- `references/`、`commands-staging/`、`scripts/lib/`、`scripts/solana/`、`scripts/report/wave_scan.py` 零改动。
- `SKILL.md`、`pyproject.toml` 均仅版本行变化。
- 生产改动 `+49/-26`，合计 75 行，未超过 110 行；新增一个私有 helper。
- 无新增 CLI 参数，原公开导入保留。

**2. 等价性：内存补充验证通过；正式入口验证未完成**

独立生成夹具，固定随机种子 `20260924`。未复用施工者夹具或报告。

受文件系统限制，补充验证采用独立 Python 子进程：基线源码通过 `git show 634c083:...` 获取，基线 `wave_scan` 同样来自该提交；显式设置工单要求的 `PYTHONPATH`。仅把文件装载和报告写出替换为内存输入、输出，执行实际 `main()` 和地址概要计算。

**这不是工单 §0.6 的落盘基线副本运行，也不计作正式三入口完成。**

主夹具：301,431 条边、4,342 个地址、跨度 719 天。

| 变体 | sinks / sprays | 顶层 pulse / pulse_all / slow_spray | mode_hits 三口径计数 | 比较 |
|---|---:|---:|---:|---|
| 无 entity | 7 / 7 | 3 / 2 / 2 | 3 / 5 / 2 | 通过 |
| 有 entity | 7 / 7 | 3 / 2 / 2 | 3 / 5 / 2 | 通过 |
| entity＋exclude | 6 / 6 | 2 / 2 / 2 | 2 / 4 / 2 | 通过 |

三个主变体均在仅去掉 `generated_at` 后，按原数组顺序重新序列化逐字节相等。另断言：

- sink、spray 的生产排序键及各 sink 的来源 pct 无并列。
- 老收方补货型 `pulse_all` 的 fresh 计数为 0。
- 存在全史累计流入高于最佳单窗的 sink。
- `Hub5` 同时为 sink、spray。
- 两个纯慢速分发地址各有 600 收方，`recipients_top` 长度 500。
- 同实体边抵消、跨实体来源保留；exclude 确实移除相关候选。

微夹具结果：

| 项目 | 独立核验结果 |
|---|---|
| 空 elig | `eligible_universe_count=0`；空字符串来源仍进入预筛及候选行，新旧一致；没有只比较最终空 sinks |
| 空候选 | 预筛为空、报告 sinks/sprays 为空，新旧一致 |
| 自转、非合格来源 | 自转不贡献净额；非合格来源计净额、不计合格流入或 sources |
| MixedHub | 净流入 `1.01%`，合格流入 `3.0%`，5 个来源、20 个正值收方 |
| 负值与零值 | 指定负值边使净流入变为 `1.03%`；其他上述计数不变；仅零值入边收方未入选 |
| 同 ts 同额来源 | 仅按相同 pct 组允许重排后比较，其他字段一致 |
| top500 边界 | 540 收方，其中 50 个同额跨越边界；数量 500、无重复、严格高于边界者全部入选、低于者全部排除、金额降序均通过 |

并列比较没有对所有数组统一排序。

此外，直接提取 HEAD 的 `sink_net` SQL，与基线聚合表达式逐地址对照：

```text
PASS sink_net OnlyIn baseline=head= 13
PASS sink_net OnlyOut baseline=head= -3
PASS sink_net A baseline=head= -17
PASS sink_net B baseline=head= 17
PASS sink_net Self baseline=head= 0
PASS sink_net Absent baseline=head= 0
```

覆盖单侧流入、单侧流出、候选互转、自转、无聚合行、非合格来源及负值贡献。

**3. 源扫描：内存执行计划通过；真实 parquet 计划未完成**

对上述八组内存对照，实际捕获 HEAD 执行的 SQL 并运行 `EXPLAIN (FORMAT JSON)`：

| 语句 | 每条计划中的源边表扫描数 |
|---|---:|
| `presink` | 1 |
| `sink_edges` | 1 |
| `sink_net` | 1 |
| `prespray` | 1 |
| `spray_edges` | 1 |

合计五条读取 `eflow` 的阶段语句，符合 §1.2。`sink_net` 计划没有 `DELIM_JOIN`，没有按候选数扩张的 OR 连接。

共对 **72 次候选 SQL 调用**逐次解释并断言：

- sink 候选只读 `sink_edges`。
- spray 候选及 top500 只读 `spray_edges`。
- 净额通过已加载的 `net_map.get()` 查询。
- 候选 SQL 均未重新读取源边表。

真实 EVM parquet 装载路径未运行，因此不将上述结果冒充其执行计划。

**4. 保序与过滤效果：独立内存探针通过**

使用 HEAD 实际 `_materialize_edges` helper，独立构造 300 万行、300 个候选键、8 线程的交错边表。DuckDB 为 `1.5.4`。

| 指标 | sink_edges | spray_edges |
|---|---:|---:|
| 行数 | 3,000,000 | 3,000,000 |
| 按 rowid 检查候选列、ts 下降次数 | 0 | 0 |
| 建表后 preserve_insertion_order | false | false |
| 总 row groups / 目标键涉及 row groups | 25 / 1 | 25 / 1 |
| 点查返回行数 | 10,000 | 10,000 |
| `EXPLAIN ANALYZE` 实际扫描行数 | 120,832 | 120,832 |
| 有序表点查中位数，15 次 | 15.464 ms | 12.503 ms |
| 交错源表同查询中位数，15 次 | 23.219 ms | 23.174 ms |

计划保留候选过滤及 `ORDER BY ts`。实际扫描统计少于全表行数，结合存储段范围证明本夹具上的过滤有效，结论不只依赖耗时下降。

另故意令 CTAS 抛出异常，确认 `finally` 仍恢复 `preserve_insertion_order=false`。源码亦确认 sink 两表在构建 spray 表前释放。

未验证亿级规模、磁盘溢写或真实 parquet 性能。

**5. 七个测试：全部实际调用，两个完成通过、五个环境阻断**

| 文件 | 退出码 | 结果 |
|---|---:|---|
| `test_flow_anomaly.py` | 1 | 创建临时目录失败，17 例未完成 |
| `test_wave_scan.py` | 1 | 创建临时目录失败 |
| `test_reconcile_v4_receipt.py` | 1 | 显式创建 `/tmp` 子目录失败 |
| `fixtures_lint.py` | 0 | PASS |
| `invariant_scan.py` | 0 | PASS |
| `test_batch4_invariant_guards.py` | 1 | 创建临时目录失败 |
| `test_exemption_guards.py` | 1 | 前三项通过，注入测试创建临时目录失败 |

完成项实际输出：

```text
fixtures_lint PASS：pythia_anchors.json 结构完整（数值以文件为权威，回测后人工更新）
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=62, formal_entrypoints=61, exceptions=0
```

**6. 版本登记：通过**

四处登记一致为 `9.1.1`。CHANGELOG 索引行含换行 **158 B**，详细段恰有四条：出处与裁决、改法、字节与测试、成本-质量指标。

其中引用施工者性能数字的文字仅视为声称，本报告未将其作为复现证据。

**实际执行的命令清单**

目录为用户指定工作目录。范围、版本与基线核查执行了：

```bash
mkdir -p "$PWD/.staging_blind_r2/tmp" && export TMPDIR="$PWD/.staging_blind_r2/tmp"

git status --short
git rev-parse HEAD
git merge-base --is-ancestor 634c083 HEAD
git diff --stat 634c083 HEAD
git diff --name-only 634c083 HEAD -- . ':!maintenance/repair-20260924-flow-scan-scalability'
git diff --numstat 634c083 HEAD -- scripts/report/flow_anomaly_scan.py
git diff 634c083 HEAD -- scripts/report/flow_anomaly_scan.py scripts/tests/test_flow_anomaly.py VERSION pyproject.toml SKILL.md CHANGELOG.md
git diff --name-only 634c083 HEAD -- references commands-staging scripts/lib scripts/solana scripts/report/wave_scan.py
cat maintenance/repair-20260924-flow-scan-scalability/workorder_R1.md
```

七个测试分别以以下环境实际调用：

```bash
export TMPDIR="$PWD/.staging_blind_r2/tmp"
export PYTHONDONTWRITEBYTECODE=1
export MPLCONFIGDIR="$HOME/.matplotlib"

python3 -B scripts/tests/test_flow_anomaly.py
python3 -B scripts/tests/test_wave_scan.py
python3 -B scripts/tests/test_reconcile_v4_receipt.py
python3 -B scripts/tests/fixtures_lint.py
python3 -B scripts/tests/invariant_scan.py
python3 -B scripts/tests/test_batch4_invariant_guards.py
python3 -B scripts/tests/test_exemption_guards.py
```

另实际运行了 `python3 -B -c` 内联审计程序，未写入文件：

- 固定种子夹具生成、八组基线/HEAD 子进程对照、逐候选执行计划断言。
- 300 万行保序、存储段范围、`EXPLAIN ANALYZE` 及点查计时。
- 提取生产 `sink_net` SQL 的单侧净额验证、helper 异常恢复验证。
- CHANGELOG 索引 UTF-8 字节及详细段条数检查。

基线源码获取命令在内存对照子进程中实际执行：

```bash
git show 634c083:scripts/report/flow_anomaly_scan.py
git show 634c083:scripts/report/wave_scan.py
```

**未完成项与环境最小复现**

开工执行指定创建命令即失败：

```text
mkdir: /Users/uravvv/.claude/skills/token-chip-analysis/.staging_blind_r2: Operation not permitted
```

之后仍显式设置了 `TMPDIR` 并调用七个测试。落盘基线副本尝试：

```bash
export TMPDIR="$PWD/.staging_blind_r2/tmp"
export PYTHONPATH="$PWD/scripts/lib:$PWD/scripts/solana:$PWD/scripts/report"
git show 634c083:scripts/report/flow_anomaly_scan.py > "$TMPDIR/flow_baseline.py"
```

输出：

```text
zsh:3: no such file or directory: /Users/uravvv/.claude/skills/token-chip-analysis/.staging_blind_r2/tmp/flow_baseline.py
```

因此以下未完成：§0.6 落盘基线副本运行、正式 `--edges-sol` / `--edges-evm-v2` / `--duckdb` 对照、真实 EVM parquet `EXPLAIN`，以及上表五个测试。均为**环境阻断、非代码回归**，按本轮规则不计 FAIL。

五个测试的完整异常如下。

`test_flow_anomaly.py`：

```text
Traceback (most recent call last):
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_flow_anomaly.py", line 321, in <module>
    sys.exit(main())
             ~~~~^^
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_flow_anomaly.py", line 70, in main
    d = str(Path(tempfile.mkdtemp(prefix="flow_test_")).resolve())
                 ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/tempfile.py", line 370, in mkdtemp
    prefix, suffix, dir, output_type = _sanitize_params(prefix, suffix, dir)
                                       ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/tempfile.py", line 127, in _sanitize_params
    dir = gettempdir()
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/tempfile.py", line 312, in gettempdir
    return _os.fsdecode(_gettempdir())
                        ~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/tempfile.py", line 305, in _gettempdir
    tempdir = _get_default_tempdir()
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/tempfile.py", line 222, in _get_default_tempdir
    raise FileNotFoundError(_errno.ENOENT,
                            "No usable temporary directory found in %s" %
                            dirlist)
FileNotFoundError: [Errno 2] No usable temporary directory found in ['/Users/uravvv/.claude/skills/token-chip-analysis/.staging_blind_r2/tmp', '/tmp', '/var/tmp', '/usr/tmp', '/Users/uravvv/.claude/skills/token-chip-analysis']
```

`test_wave_scan.py`：

```text
Traceback (most recent call last):
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_wave_scan.py", line 258, in <module>
    sys.exit(main())
             ~~~~^^
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_wave_scan.py", line 62, in main
    d = tempfile.mkdtemp(prefix="wave_scan_test_")
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/tempfile.py", line 370, in mkdtemp
    prefix, suffix, dir, output_type = _sanitize_params(prefix, suffix, dir)
                                       ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/tempfile.py", line 127, in _sanitize_params
    dir = gettempdir()
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/tempfile.py", line 312, in gettempdir
    return _os.fsdecode(_gettempdir())
                        ~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/tempfile.py", line 305, in _gettempdir
    tempdir = _get_default_tempdir()
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/tempfile.py", line 222, in _get_default_tempdir
    raise FileNotFoundError(_errno.ENOENT,
                            "No usable temporary directory found in %s" %
                            dirlist)
FileNotFoundError: [Errno 2] No usable temporary directory found in ['/Users/uravvv/.claude/skills/token-chip-analysis/.staging_blind_r2/tmp', '/tmp', '/var/tmp', '/usr/tmp', '/Users/uravvv/.claude/skills/token-chip-analysis']
```

`test_reconcile_v4_receipt.py`：

```text
Traceback (most recent call last):
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_reconcile_v4_receipt.py", line 633, in <module>
    sys.exit(main())
             ~~~~^^
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_reconcile_v4_receipt.py", line 429, in main
    case_root_symlink_semantics()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_reconcile_v4_receipt.py", line 249, in case_root_symlink_semantics
    with tempfile.TemporaryDirectory(prefix="batch5d-macos-ancestor-",
         ~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                     dir="/tmp") as raw:
                                     ^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/tempfile.py", line 907, in __init__
    self.name = mkdtemp(suffix, prefix, dir)
                ~~~~~~~^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/tempfile.py", line 381, in mkdtemp
    _os.mkdir(file, 0o700)
    ~~~~~~~~~^^^^^^^^^^^^^
PermissionError: [Errno 1] Operation not permitted: '/tmp/batch5d-macos-ancestor-fnm96dy3'
```

`test_batch4_invariant_guards.py`：

```text
Traceback (most recent call last):
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_batch4_invariant_guards.py", line 557, in <module>
    raise SystemExit(main())
                     ~~~~^^
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_batch4_invariant_guards.py", line 522, in main
    with tempfile.TemporaryDirectory(prefix="batch4-invariant-") as td:
         ~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/tempfile.py", line 907, in __init__
    self.name = mkdtemp(suffix, prefix, dir)
                ~~~~~~~^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/tempfile.py", line 370, in mkdtemp
    prefix, suffix, dir, output_type = _sanitize_params(prefix, suffix, dir)
                                       ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/tempfile.py", line 127, in _sanitize_params
    dir = gettempdir()
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/tempfile.py", line 312, in gettempdir
    return _os.fsdecode(_gettempdir())
                        ~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/tempfile.py", line 305, in _gettempdir
    tempdir = _get_default_tempdir()
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/tempfile.py", line 222, in _get_default_tempdir
    raise FileNotFoundError(_errno.ENOENT,
                            "No usable temporary directory found in %s" %
                            dirlist)
FileNotFoundError: [Errno 2] No usable temporary directory found in ['/Users/uravvv/.claude/skills/token-chip-analysis/.staging_blind_r2/tmp', '/tmp', '/var/tmp', '/usr/tmp', '/Users/uravvv/.claude/skills/token-chip-analysis']
```

`test_exemption_guards.py`：

```text
PASS EX-01: no production import/string reference to multicall_balances
PASS EX-01: absent from formal producer registry / evidence targets
PASS EX-01: --chain choices remain exploration-derived
Traceback (most recent call last):
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_exemption_guards.py", line 99, in <module>
    raise SystemExit(main())
                     ~~~~^^
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_exemption_guards.py", line 92, in main
    with tempfile.TemporaryDirectory() as tmp:
         ~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/tempfile.py", line 907, in __init__
    self.name = mkdtemp(suffix, prefix, dir)
                ~~~~~~~^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/tempfile.py", line 370, in mkdtemp
    prefix, suffix, dir, output_type = _sanitize_params(prefix, suffix, dir)
                                       ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/tempfile.py", line 127, in _sanitize_params
    dir = gettempdir()
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/tempfile.py", line 312, in gettempdir
    return _os.fsdecode(_gettempdir())
                        ~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/tempfile.py", line 305, in _gettempdir
    tempdir = _get_default_tempdir()
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/tempfile.py", line 222, in _get_default_tempdir
    raise FileNotFoundError(_errno.ENOENT,
                            "No usable temporary directory found in %s" %
                            dirlist)
FileNotFoundError: [Errno 2] No usable temporary directory found in ['/Users/uravvv/.claude/skills/token-chip-analysis/.staging_blind_r2/tmp', '/tmp', '/var/tmp', '/usr/tmp', '/Users/uravvv/.claude/skills/token-chip-analysis']
```

收尾时尝试指定的 `rm -rf "$PWD/.staging_blind_r2"`，平台执行审查拒绝，理由为禁止 `rm -f` 类命令。随后只读确认该目录不存在（从未创建成功），无需删除任何文件。**最终 `git status --short` 为空，`staging_exists = False`。**
