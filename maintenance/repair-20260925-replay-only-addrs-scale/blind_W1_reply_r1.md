# 盲审 W1 r1：PASS

按本次指定的“环境阻断不计 FAIL”口径判定。未发现违反 §1 契约的代码问题；**这不表示磁盘端到端测试和资源证据已全部复验通过**，未完成项见下文。

审查对象：`fix/replay-only-addrs-scale`，HEAD `b867f78`。Python 3.14，DuckDB 1.5.4。全程离线、未修改文件、未 commit，结束时工作树干净。未读取 `~/.codex/`、memories 或其他禁读内容；未读取施工者的完成报告、等价性记录和耗时记录。

**1. 范围：通过**

实际执行：

```sh
git status --short
git branch --show-current
git rev-parse --short HEAD
git diff --name-only bb8c871 HEAD -- . ':!maintenance/repair-20260925-replay-only-addrs-scale'
git diff bb8c871 HEAD -- SKILL.md pyproject.toml VERSION CHANGELOG.md
git diff bb8c871 HEAD -- references commands-staging scripts/tests/run_all.py scripts/tests/invariant_manifest.json
git diff 8457f70 HEAD -- scripts/evm/replay_duck.py
git diff --numstat 8457f70 HEAD -- scripts/evm/replay_duck.py
```

白名单范围输出恰为：

```text
CHANGELOG.md
SKILL.md
VERSION
pyproject.toml
scripts/evm/replay_duck.py
scripts/tests/test_engine_equivalence.py
```

`SKILL.md`、`pyproject.toml` 仅版本行变化；指定禁止修改路径 diff 为空。生产脚本改动为 `+92/-10`。

**2. 独立等价性：纯内存复现通过**

开工尝试：

```sh
mkdir -p "$PWD/.staging_blind_r1/tmp"
```

结果为 `Operation not permitted`，因此按要求改用纯内存 DuckDB。

独立驱动以 `python3 -B -c` 执行，基线源码直接取自：

```sh
git show 8457f70:scripts/evm/replay_duck.py
```

基线与 HEAD 源码未经修改，分别编译执行真实 `main()`，保留 `scripts/evm/replay_duck.py` basename。公共参数为：

```text
--channels /blindmem/channels.json
--out-dir /blindmem/out
--threads 2 --mem-limit 2GB --no-merged
--only-addrs /blindmem/needs.json
--only-addrs /blindmem/trigger.json
```

分别追加或不追加 `--force-varint`，环境变量取 `CHIP_REPLAY_SEG_ROWS=10`。

适配边界：文件扫描替换为内存输入关系，文件读写替换为内存字节对象；预检、磁盘检查及全量 provenance 文件验证未作为本次内存试验的验证对象。事件清洗、冲突检查、分桶、峰值计算和补算收据构造执行生产代码。

固定种子 `20260925`，夹具包含 52 条原始行、48 个唯一事件、8 个目标地址、6 桶，覆盖零事件地址、Z/DEAD、低门槛正峰值、同块自转净零及完全重复行。

关键输出：

```text
v1csv HUGEINT PASS buckets=[14,8,8,9,5,8]
v1csv VARINT  PASS buckets=[14,8,8,9,5,8]
v2    HUGEINT PASS buckets=[14,8,8,9,5,8]
v2    VARINT  PASS buckets=[14,8,8,9,5,8]
ALL_MEMORY_CHECKS_PASS
```

这里的 v1/v2 表示两种输入清洗 SQL 路径，未运行真实 CSV/parquet 文件解码。

两版收据的 `addresses` 均与独立 Python 块末累计计算逐键逐值相等。其中：

- 低门槛地址峰值为 `"1"`、首达块为 `100`，全量 `peaks.json` 不包含该地址。
- 零事件地址和仅自转地址均为 `{"peak":"0","peak_blk":null}`。
- 收据的 producer、channels、两项 inputs SHA 均按实际内存字节核验。
- 既有全量四产物的内存字节未被补算覆盖。

四类冲突分别独立运行；每类覆盖两种输入 SQL 路径、三条指定执行路径，以及“无旧收据／已有旧收据”两种状态，共 **48 次拒绝验证**：

| 冲突 | HEAD only-addrs | HEAD 全量 | 基线全量 |
|---|---|---|---|
| 同键异值 | 拒绝 | 拒绝 | 拒绝 |
| 同键跨块 | 拒绝 | 拒绝 | 拒绝 |
| 端点不同，仅一行命中 | 拒绝 | 拒绝 | 拒绝 |
| 两端均不命中 | 拒绝 | 拒绝 | 拒绝 |

均在冲突检查处返回非零，错误包含 `去重键对应多个不同事件内容`；无新收据，旧收据字节不变，未调用替换操作。另独立验证首桶 `0/6`、末桶 `5/6` 冲突，结果相同。

**3. 不物化与分桶：源码及内存执行证据通过**

实际执行连接的目录查询确认：

```text
duckdb_tables(): 无 raw_rows、events
duckdb_views():  raw_rows
```

执行日志没有全量 `raw_rows/events` CTAS；正常 6 桶实际执行 **12 条**桶源查询。首桶捕获的两条 SQL 如下，后续桶只改变桶号：

```sql
WITH g AS (
  SELECT tag, tx, li, COUNT(*) n,
         COUNT(DISTINCT (b, ts, frm, t2, v)) variants
  FROM raw_rows
  WHERE hash(tag, tx, li) % 6 = 0
  GROUP BY tag, tx, li
)
SELECT COALESCE(SUM(n), 0),
       COUNT(*) FILTER (WHERE variants > 1)
FROM g;
```

```sql
INSERT INTO ab_raw
WITH seg AS MATERIALIZED (
  SELECT ANY_VALUE(b) b, ANY_VALUE(frm) frm,
         ANY_VALUE(t2) t2, ANY_VALUE(v) v
  FROM raw_rows
  WHERE hash(tag, tx, li) % 6 = 0
    AND (frm IN (SELECT a FROM only_addrs)
         OR t2 IN (SELECT a FROM only_addrs))
  GROUP BY tag, tx, li
),
d AS (
  SELECT t2 AS a, b, CAST(v AS HUGEINT) AS d FROM seg
  UNION ALL
  SELECT frm, b, -CAST(v AS HUGEINT)
  FROM seg
  WHERE frm <> '0x0000000000000000000000000000000000000000'
)
SELECT a, b, SUM(d)
FROM d
WHERE a IN (SELECT a FROM only_addrs)
GROUP BY a, b;
```

对两条 SQL 实际运行了 `EXPLAIN`，计划显示桶 `FILTER` 位于事件去重 `HASH_GROUP_BY` 之前。由于采用内存输入，底层为 `SEQ_SCAN`；**未据此声称验证了原生文件扫描或解码 IO**。

桶后执行：

```sql
CREATE TABLE ab AS
SELECT a, b, SUM(dd) dd
FROM ab_raw GROUP BY a, b;
```

夹具有 15 组 `(a,b)` 需要跨桶合并；合并后重复 `(a,b)` 数为零。日志为：

```text
K=6 总行数=52 最大桶行数=14 ab 行数=41 源查询=12
```

其余验证：

- `kept_rows` 来自逐通道保留行 COUNT 累加的 `acc["_kept_rows"]`。
- 实际触发计数断言：`[fail-closed] 桶行数总和 52 != 保留源行 53`。
- `CHIP_REPLAY_SEG_ROWS` 为 `0/-1/abc/空串` 时，only-addrs 均 rc 2，且尚未执行源查询；全量均 rc 0。
- 37 位走 HUGEINT、38 位走 VARINT；空源、空桶、空地址并集、CSV NULL 值行行为符合基线。
- 52 条同键重复行集中一桶时触发 `52 > 4×10` 偏斜告警，结果仍与基线一致。
- 直接执行 `_peaks_python`，VARINT `ab` 的结果与独立 Python 期望相等。

`git diff` 加源码逐字比较确认：峰值 SQL、回退调用、收据构造及 `os.replace` 保持原文；`_peaks_python` 整函数未变。

**4. 全量路径：业务计算通过，文件 provenance 复验未完成**

源码逐字比较通过：

```text
replay_pass1
replay_pass2
emit_merged
_create_deltas_view
```

两种输入 SQL 路径均独立运行：

- 基线与 HEAD 全量 `--no-merged`：四个业务 JSON 相等。
- 带 `--camps`：`camp_series.json`、`entity_series.json` 相等。
- merged 使用 `--emit-csv`：CSV 字节相等。

全量 `replay_stats` 对比仅覆盖原生产计算字段；磁盘依赖的 `replay_provenance()` 返回部分未注入本次内存结果，不能视为已核验。真实 preflight、输入输出文件绑定、sidecar 落盘及 parquet merged 列入未完成项。

**5. 指定测试：2 项通过，8 项环境阻断，1 项禁读纪律阻断**

逐项以 `python3 -B` 执行入口，附加只读审计保护后通过 `runpy` 运行，防止测试间接读取禁读路径；未修改测试代码。

以下文件均位于 `scripts/tests/`：

| 测试入口 | rc | 结果 |
|---|---:|---|
| `test_engine_equivalence.py` | 1 | 环境阻断：无可用临时目录 |
| `test_audit_release_gate.py` | 1 | 同上 |
| `test_fault_injection.py` | 1 | 同上 |
| `test_repair_batch_c.py` | 1 | `/private/tmp` 创建目录被拒 |
| `test_repair_batch1.py` | 1 | Matplotlib 缓存及临时目录不可写 |
| `test_review_evm_integrity.py` | 1 | 无可用临时目录 |
| `fixtures_lint.py` | 0 | PASS |
| `invariant_scan.py` | 0 | PASS |
| `test_batch4_invariant_guards.py` | 1 | 无可用临时目录 |
| `test_exemption_guards.py` | 1 | 前三项通过，注入测试被临时目录阻断 |
| `changelog_lint.py` | 1 | 禁读保护阻止读取 archive |

主要环境异常：

```text
FileNotFoundError: [Errno 2] No usable temporary directory found
PermissionError: [Errno 1] Operation not permitted: '/private/tmp/...'
```

另直接调用新增的 `followup_bucketed_case()`，同样在创建临时目录时阻断，**未把它标为已通过**。

成功输出：

```text
fixtures_lint PASS：pythia_anchors.json 结构完整
PASS invariant manifest:
receipt_producers=81, receipt_consumers=118, transport_calls=65,
atomic_writes=62, formal_entrypoints=61, exceptions=0
```

**6. 版本登记：静态检查通过，历史资源数字未独立重测**

四处版本一致为 `9.2.2`；CHANGELOG 索引行含换行为 **179 B**；详细段恰四条。活跃 CHANGELOG 的 89 个版本条目独立检查通过。

成本登记与源码一致：正常每桶两条源查询，K=8/K=1 为 16/2 条；另计其他扫描，没有写成“K 次读取”，也没有把查询次数当作文件读取倍数。

CHANGELOG 明确登记了默认桶规模的既有宽键实验、`time -l` 测量阻断、平均规模非上限及不得外推亿级。这些**历史耗时、RSS 和大夹具数字本次未独立重测，不作为本次 PASS 的实测证据**。

**未完成项**

以下均未计为代码回归：

- 上表 8 项需要可写目录的测试，包括新增 `followup_bucketed_case`。
- `changelog_lint` 的 archive 对照：受本次禁读纪律限制。
- 真实 CSV/parquet 文件扫描、预检及全量 provenance/sidecar 绑定。
- 真实文件旧收据保护和操作系统层面的原子替换；本次仅验证内存行为与原代码未变。
- CHANGELOG 所载 200 万行及近 500 万唯一键实验的资源数字复测。

本次未发现需要提供代码失败最小复现的缺陷。