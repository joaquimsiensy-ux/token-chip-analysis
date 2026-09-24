# 收官review R1：PASS

**PASS 仅针对 R1 的修复目标：逐候选底层 parquet 重扫已消除，独立对照未发现判据或报告回归。不能据此宣称“所有全表扫描已消除”或“任意亿级输入必能完成”。** 本轮未发现 P0/P1；四项 P2 残余见后文。

审查对象为 `HEAD=38b8aa1`，基线为 `634c083`。全程离线，未读取 `~/.codex/`、memories 或其他禁读路径，未修改仓库文件、未 commit。

**1. 扫描机制：通过，但物化表仍有最坏全扫路径**

实际执行：

```sh
git diff 634c083 HEAD -- scripts/report/flow_anomaly_scan.py
nl -ba scripts/report/flow_anomaly_scan.py
mkdir -p "$PWD/.staging_review_r1/tmp" && export TMPDIR="$PWD/.staging_review_r1/tmp"
```

建目录返回 `Operation not permitted`。按本轮允许的替代方案，使用内存 DuckDB 完成验证；**未完成真实两 run parquet 文件夹具的独立 EXPLAIN**。

内存探针的实际执行入口为：

```sh
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH="$PWD/scripts/lib:$PWD/scripts/solana:$PWD/scripts/report" \
python3 -B -c '<内联审查代码>'
```

内联代码通过 `git show 634c083:scripts/report/flow_anomaly_scan.py` 读取基线，在内存加载两个版本；仅将输入装载、连接和报告文件输出适配为内存对象，保留实际扫描 SQL、地址概要及报告计算逻辑。对实际执行 SQL 逐条运行 `EXPLAIN (FORMAT JSON)`。

| HEAD 查询 | 实测底层 `source_edges` 扫描算子数 |
|---|---:|
| `presink` 预筛 | 1 |
| `sink_edges` 物化 | 1 |
| `sink_net` 聚合 | 1 |
| `prespray` 预筛 | 1 |
| `spray_edges` 物化 | 1 |
| 逐 sink 查询 | 0，只读 `sink_edges` |
| 逐 spray 查询 | 0，只读 `spray_edges` |
| 慢速收方 top500 | 0，只读 `spray_edges` |

`sink_net` 计划为一次源扫描、两侧展开及 `HASH_JOIN`，没有 `DELIM_JOIN`，没有候选数规模的重复源扫描。净额逐候选读取已变成 `net_map.get(t, 0)`。

按工单统计边界，排除装载、地址概要和 `data_first_day`：

- **基线：**源查询次数为 `2 + Cs + Hs + Cp + L`。其中 `Cs/Cp` 为 sink/spray 预筛候选数，`Hs` 为最终命中的 sink 数，`L` 为需要 top500 的慢速分发点数。
- **HEAD：**两次预筛、三次物化，共 **5 条源查询，各至多一次源扫描**；空集合可能进一步被优化。
- EVM VIEW 装载器中，每次展开源查询包含 logs 和 blocks 两个 parquet 数据集读取。此项来自未改动源码核查；本轮没有独立运行 parquet 文件计划，不能将内存计划冒充 parquet 实测。

关键实现见 [flow_anomaly_scan.py:255](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/flow_anomaly_scan.py:255)。

**物化表点查并非索引查询。** 我另外生成两种地址分布的 100 万行内存表，实际执行：

```sql
SET preserve_insertion_order=true;
CREATE OR REPLACE TEMP TABLE spray_edges AS
SELECT ... FROM range(1000000) q(i) ORDER BY f, ts;

EXPLAIN (ANALYZE, FORMAT JSON)
SELECT ts,t,amt FROM spray_edges WHERE f=? ORDER BY ts;
```

每种均为 100 个候选地址，每个地址 10,000 行：

| 地址分布 | 扫描类型 | 返回行数 | `operator_rows_scanned` |
|---|---|---:|---:|
| 分散的十六进制地址 | `SEQ_SCAN` | 10,000 | 122,880 |
| 共享长前缀的合法地址 | `SEQ_SCAN` | 10,000 | **1,000,000** |

两种表均有 9 个 row group，按 `rowid` 检查排序下降次数均为 0。说明排序确实生效，但不能保证跳块。

因此，最坏情况下，物化表扫描工作量仍可达：

`O(Cs × Ns + (Cp + L) × Np)`

`Ns/Np` 分别为两张物化边表行数，均可能接近全量边数。**修复消除了逐候选 parquet 解码、blocks 聚合连接和实体视图重复展开，没有消除所有候选数乘边数的最坏成本。**

**2. 等价性：三组自设计对抗场景通过**

使用上述内存执行入口，执行两个版本的实际 `main()`；报告仅移除 `generated_at`，不重排数组，再按相同 JSON 序列化方式比较。

| 自设计场景 | 关键输出与断言 |
|---|---|
| A：同址 sink/spray，混入自转、非合格来源、负值和零值边 | `BYTE_EQUAL=True`；`Hub` 同时命中；合格流入 `3.1%`、净流入 `0.911%`、来源 5 个、收方 20 个 |
| B：实体抵消与排除候选两个变体 | 两次均 `BYTE_EQUAL=True`；同实体来源与 Hub 抵消后 sink 消失，跨实体分发保留；exclude 含 Hub 后两类候选均消失 |
| C：空 elig，包含空字符串来源 | `BYTE_EQUAL=True`；新旧预筛均为 `[('EmptySink',)]`；候选边均为 `[(0, '', 'EmptySink', 50000)]`，最终 sink 也一致 |

C 额外直接执行基线条件，避免只比较最终空报告：

```sql
SELECT t FROM eflow
WHERE f IN ('') AND t NOT IN (?,?)
  AND f<>t AND amt>0
GROUP BY t HAVING SUM(amt)>=0 ORDER BY t;

SELECT ts,f,t,amt FROM eflow
WHERE t='EmptySink' AND f IN ('') AND f<>t AND amt>0
ORDER BY ts;
```

另补测两项：

- **top500 并列：**520 个收方，490 个严格高于边界、30 个处于边界；新旧均选出 500 个唯一地址，全部较高者入选，仅从边界组补足，其余报告完全相等，符合 §1.1。
- **大整数：**约 `10^35` 量级场景 `BYTE_EQUAL=True`。`HUGEINT_MAX=2^127−1` 场景在新旧共同的 `build_addr_summary` 阶段均报 `OutOfRangeException`；更小的近边界探针还触发既有 DECIMAL 转换/乘法限制。不能宣称整个 HUGEINT 输入域都受支持，但未发现本补丁新增差异。

**3. 资源风险：阶段释放有效，不存在容量保证**

实际验证包含：

```sql
SELECT current_setting('memory_limit');
SELECT current_setting('temp_directory');
SELECT current_setting('max_temp_directory_size');

SELECT table_name FROM information_schema.tables
WHERE table_name IN ('sink_edges','sink_net');
```

关键输出：

```text
memory_limit=7.4 GiB
temp_directory=.tmp
max_temp_directory_size=90% of available disk space
STAGE_DROP_REMAINING []
INSERTION_ORDER False
EXCEPTION_RESTORE_FALSE PASS
```

异常测试实际调用：

```python
_materialize_edges(con, "bad", "SELECT * FROM table_does_not_exist")
```

捕获 `CatalogException` 后，`preserve_insertion_order` 已恢复为 `false`。正常路径也恢复为 `false`。

资源结论：

- sink 两张表确实在 spray 物化之前删除，避免两张大边表同时存活。
- 两张边表容量按相关边数增长，最坏分别接近全量；排序和聚合还需要工作空间。
- 超过 `memory_limit` 不等于必然 OOM，DuckDB 可以溢写；但仍可能因内存不足、临时盘限额或可用空间不足而失败。
- `fetchall()`、Python 列表、集合及报告对象不受 DuckDB 内存限额约束。
- `DROP TABLE` 不等于立即降低进程 RSS。最后一个 sink 的 Python `rows`、`net_map` 等仍有引用；其中旧 `rows` 会跨越 spray 物化阶段。

本轮没有可写临时盘，**未独立测量溢写峰值或亿级容量上界**。

我读取了允许目录中的 `R1_quq_live_run.log` 和 `R1_dispatcher_live_acceptance.jsonl`，记录与调度方所述一致：109,681,418 边，sink/spray 物化分别 26,094,518 / 106,359,203 行，结果 1,779 / 69，`rc=0`，4,947.8 秒，RSS 6,302.8 MiB。这是**调度方运行记录核对，非本轮独立重跑**；约 10 GB 临时盘及约 70 分钟 Python 阶段仍按调度方观察引用。

**4. 回归面：两项通过，四项环境阻断**

实际以 `TMPDIR="$PWD/.staging_review_r1/tmp"`、`PYTHONDONTWRITEBYTECODE=1` 执行：

| 实际命令 | 本轮结果 |
|---|---|
| `python3 -B scripts/tests/test_flow_anomaly.py` | 环境阻断：创建临时目录失败，全部用例未完成 |
| `python3 -B scripts/tests/test_wave_scan.py` | 同上 |
| `python3 -B scripts/tests/fixtures_lint.py` | **PASS，rc=0** |
| `python3 -B scripts/tests/invariant_scan.py` | **PASS，rc=0** |
| `python3 -B scripts/tests/test_batch4_invariant_guards.py` | 环境阻断：创建临时目录失败 |
| `python3 -B scripts/tests/test_exemption_guards.py` | 前三项检查 PASS，注入测试创建临时目录失败 |

共同阻断输出为 `FileNotFoundError: No usable temporary directory found`。按本轮约定不计 FAIL，也不记成测试通过。

`invariant_scan.py` 关键输出：

```text
PASS invariant manifest:
receipt_producers=81, receipt_consumers=118,
transport_calls=65, atomic_writes=62,
formal_entrypoints=61, exceptions=0
```

冻结目录检查实际执行：

```sh
git diff --exit-code 634c083 HEAD -- \
  scripts/report/wave_scan.py scripts/lib scripts/solana \
  references commands-staging
```

**无 diff，exit 0。**

**5. 版本与文档：通过**

实际执行版本 diff、Python 字段解析及：

```sh
git diff --numstat 634c083 HEAD -- \
  scripts/report/flow_anomaly_scan.py scripts/tests/test_flow_anomaly.py
```

关键输出：

```text
VERSIONS 9.1.1 9.1.1 9.1.1 CHANGELOG True INDEX_BYTES 157
49  26  scripts/report/flow_anomaly_scan.py
22   1  scripts/tests/test_flow_anomaly.py
```

`VERSION`、`pyproject.toml`、`SKILL.md` 和 CHANGELOG 当前条目一致为 **9.1.1**；SKILL 仅版本号变化。

CHANGELOG 对改动机制、差异行数和等价性边界的描述与核查一致；历史测试、计时数字能在工程记录中找到对应内容，但不是本轮复测成绩。其“未验证亿级实跑”反映施工时状态，未纳入后来的调度方记录，措辞保守，**没有夸大为“亿级必可完成”**。

**6. 残余问题分级**

**P0：无。P1：本轮未发现。**

| 等级 | 残余问题 | 分级依据 |
|---|---|---|
| P2 | 物化表点查最坏仍全表扫 | 已用 100 万行长前缀地址夹具复现；影响通用扩展性，但没有恢复逐候选 parquet 重扫 |
| P2 | Python 滑窗可能出现平方级工作量 | `best_window_scan` 每次刷新最佳窗均复制 `set(cnt)`；独立计数中，4,000 行复制 8,001,810 个集合成员，8,000 行复制 32,003,810 个。属于基线既有逻辑，与调度方剩余耗时观察相容 |
| P2 | 内存、临时盘及 Python 对象峰值未被硬性约束 | 有溢写和阶段释放，但不能保证任意亿级输入完成；缺少最坏规模独立资源测量 |
| P2 | 极端大整数仍可能在共用地址概要阶段溢出 | 新旧均复现，发生在本轮重组查询之前，属于既有支持边界 |

最后实际执行 `git status --short`，**stdout 为空**；HEAD 仍为 `38b8aa1`。`.staging_review_r1` 检查结果为 `staging_exists False`，没有临时产物残留。

清理时请求的 `rm -rf` 被自动审批规则拒绝，原因是禁止 `rm -f` 类命令；随后以只读检查确认目录从未创建，无需删除。
