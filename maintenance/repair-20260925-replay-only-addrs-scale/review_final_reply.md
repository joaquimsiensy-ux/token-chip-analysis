# 收官审查：PASS

**未发现第 1、3 项要求判 FAIL 的真实缺陷。修复确实移除了 QUQ 原失败路径中的全量事件物化及全局事件键去重；独立内存对照未发现结果回归。**

但不能把结论扩大为“全程固定内存、没有亿级中间表、8 GB 对任意输入都足够”。`ab_raw`、最终聚合和峰值窗口仍需处理亿级数据。调度方提供的成功实跑数字与代码相容，原始案卷、完整日志和收据未由我独立核验。

审查分支为 `fix/replay-only-addrs-scale`，HEAD 为 `75f7501`；其脚本与实跑所指 `b867f78` **逐字节相同**。工作树干净，全程未修改文件、未联网、未 commit，未读取所列禁区。

**1．问题—修法对应：通过，但仍依赖溢写**

[replay_duck.py](/Users/uravvv/.claude/worktrees/tca-only-addrs/scripts/evm/replay_duck.py:171) 的新入口确实：

- 将 `raw_rows` 建为 VIEW，跳过全量 `raw_rows/events` 表物化。
- 将 `(tag,tx,li)` 冲突检查与去重限制在当前哈希桶内。
- 每桶先检查全部保留行，再过滤地址、去重及聚合；未命中地址的冲突仍会拒绝。
- 仅保留本桶的 `seg`，跨桶累计的是三列 `(a,b,dd)`。

因此，旧版宽事件表叠加全局去重的瓶颈被消除。**临时盘溢写没有被消除，只是处理对象变窄、事件键聚合规模变小。**

[最终合并位置](/Users/uravvv/.claude/worktrees/tca-only-addrs/scripts/evm/replay_duck.py:439) 仍执行：

```sql
CREATE TABLE ab AS
SELECT a, b, SUM(dd) dd FROM ab_raw GROUP BY a, b;
```

量级估算如下：

| 项目 | 估算与依据 |
|---|---|
| `ab_raw` 上界 | 每个去重事件至多贡献两个端点，故不超过 `2×109,681,418 = 219,362,836` 行 |
| 根据前三桶估计 | 三桶写入 26,705,665 行，对应源行 14,959,155；若有代表性，累计约 **195,807,531 行** |
| 最终 `ab` | 声称 **107,361,124 行**；这是跨桶合并后的数量 |
| 三列逻辑载荷 | 地址 42 字节、区块 8 字节、HUGEINT 16 字节，按 66 字节/行估算 |
| `ab_raw` 逻辑载荷 | 约 **12.04 GiB**；按上述上界约 **13.48 GiB** |
| 最终 `ab` 逻辑载荷 | 约 **6.60 GiB** |

这些不是 RSS 或磁盘实测值。字符串描述符、哈希状态、对齐和并行局部聚合会增加开销；编码、压缩和溢写会降低驻留量。例如按每行额外 16 字节字符串描述符估算，最终 `ab` 已约 **8.20 GiB**，尚未计哈希表。

**所以最终 `GROUP BY a,b` 不能指望全部驻留于 8 GB 内。** 创建 `ab` 时 `ab_raw` 尚未删除，峰值窗口随后还处理全量 `ab`。我用本机 DuckDB 1.5.4 的 `EXPLAIN` 确认保留了全局 `HASH_GROUP_BY`，窗口计划包含 `CTE/CTE_SCAN/WINDOW/HASH_JOIN`。

对本次声称的 QUQ 输入，8 GB 配置配合约 13 GB 临时盘完成运算，在量级上合理；没有证据表明只是把旧瓶颈原样搬家。但这不是任意输入的资源保证：

- 500 万是目标平均桶规模，偏斜只告警。
- V2 的区块元数据聚合及连接仍保留，规模取决于唯一块数。
- 原有 CSV 预检还会逐行累计块号列表，不能将本次修复概括为所有输入格式的全入口恒定内存。

后两项均为既有路径，未发现它们构成本次 QUQ 已知失败的残留阻断。

**2．实跑数字自洽性：相容，部分只能核对声称**

| 核对项 | 结果 |
|---|---|
| 桶数 | `ceil(109681418 / 5000000) = 22`，正确 |
| 平均桶行数 | 4,985,519；声称最大桶 4,990,129，分布合理 |
| 桶行数之和 | 汇总声称等于 109,681,418；代码有不等即退出的断言。仅提供前三桶，无法独立重加全部 22 桶 |
| 前三桶合计 | 14,959,155；其余 19 桶应合计 94,722,263 |
| 分桶源查询数 | `2×22 = 44`，与代码一致；不含前置扫描，也不等于完整文件字节读取 44 遍 |
| RSS | 6,549,962,752 B ≈ **6.10 GiB** |
| peak memory footprint | 10,055,033,208 B ≈ **9.36 GiB**，不可与 RSS 混用 |
| CPU/墙钟 | `(7376.91+294.77)/2099.81 ≈ 3.65`，与四线程执行相容 |

前三桶 37.3/58.4/73.4 秒与反复扫描、累计中间结果及内存压力相容，**但耗时和低 RSS 本身不能证明没有全量物化**；该判断来自源码分支及实际执行 SQL。

需纠正三处解释：

1. **107,361,124 是最终 `ab` 行数，不是累计 `ab_raw` 行数。** 它接近源行数，单独不能证明地址并集命中了几乎全部事件。
2. `2099.81−1347.805=752.005` 秒还包含分桶计时开始前的预检、扫描等工作，不能全部算作峰值窗口耗时。
3. 日志“有事件 51177”实际统计正峰值地址。其余 `51429−51177=252` 个地址不一定没有事件，也可能有事件但峰值不为正。

我计算的脚本完整 SHA256：

```text
e58e9f127bfd2720d417870bed6183b9f4eccc188edd79b4c4cc4db358a8112d
```

与声称的 producer 前缀一致。收据 `count=51429` 与所述 addresses 条数一致，但收据完整 producer、两项 inputs SHA、channels 绑定及文件大小只能保留为调度方声称。

**3．正确性残余风险：独立对照通过**

使用 DuckDB **1.5.4 纯内存连接**，从：

```text
git show 8457f70:scripts/evm/replay_duck.py
```

取得基线源码，在内存中执行其原函数。对照包括基线全量 `replay_pass1` 产生的 `peaks.json`、基线补算结果、新补算结果和独立 Python 整数累计结果。

文件扫描替换为同结构内存表，JSON 输出及 `os.replace` 使用内存模拟；未运行原生文件读取和通道预检。

| 独立夹具 | 实际结果 |
|---|---|
| 跨桶同地址、同区块：6 行、K=3，按真实 hash 让两条事件分别落桶 0/1；含自转及重复到达最高峰 | 全等；A 峰值 100、首达块 1，B 峰值 50、块 2 |
| 全部重复：12 行同键同内容、K=6，全部落一个桶，其余为空桶 | 只计一次，峰值 91；偏斜告警出现，结果正确 |
| 地址并集含 Z、DEAD、未发生事件地址，另有完全未命中的转账 | 全等；Z 峰值 35、DEAD 峰值 40；无正峰地址返回 `"0"/null` |

上述三类还通过了 **V2 SQL 内存对照**，执行了原始值域探测、十六进制解码和区块时间连接逻辑。

补充验证也通过：

- 非空地址并集、零保留事件。
- 大整数 VARINT，以及小值强制 VARINT。
- 强制窗口失败后的 HUGEINT/VARINT Python 回退：同块跨桶 `+10/−10`、下块 `+5`，结果为峰值 **5**，没有产生块内伪峰 10。
- 低于全量门槛的正峰值仍由 only-addrs 输出；这是既有契约，不是与基线不一致。

冲突方面，分别在首桶和末桶构造四种反例，共 **8 例**：

- 同键异值；
- 同键跨块；
- 端点不同且仅一行命中；
- 两端均不命中。

基线全量与新补算均在冲突检查处拒绝，内存模拟的旧收据均保持不变；V2 未命中地址的跨块冲突也拒绝。

等价性的关键是：完整去重键相同必落同桶；桶内仍按完整键分组，哈希碰撞不影响去重；冲突检查通过后，地址过滤与去重可交换；最终再次合并 `(a,b)`，保证窗口及 Python 回退看到每块完整净增量。未发现此链条存在缺口。

**4．契约与守卫：兼容；完整 changelog 检查未执行**

[invariant_manifest.json](/Users/uravvv/.claude/worktrees/tca-only-addrs/scripts/tests/invariant_manifest.json:967) 的 `followup_peaks` 条目登记的是 `overwrite_single`；producer 条目另登记 `block-precision-followup/v1`，均保持匹配。

源码对照确认：

- 峰值窗口、回退、收据构造和原子替换尾段未改变。
- 仍写入首个 `--only-addrs` 文件所在目录。
- 先关闭同目录 `.tmp` 文件，再执行 `os.replace(tmp,out)`。
- 发布闸仍检查 schema、engine、当前脚本完整 SHA、案内 channels 文件、inputs SHA、count、地址覆盖和峰值字段。[读取位置](/Users/uravvv/.claude/worktrees/tca-only-addrs/scripts/report/audit_release_gate.py:1192)

实际守卫结果：

```text
PASS invariant manifest:
receipt_producers=81, receipt_consumers=118,
transport_calls=65, atomic_writes=62,
formal_entrypoints=61, exceptions=0
```

`changelog_lint.py` 默认读取禁止访问的 `archive/`。我未执行该读取，仅在进程内跳过归档解析，运行其余原逻辑：**活跃 89 条通过**。这不代表完整 lint 通过。

实际文件系统的原子替换、磁盘故障注入及完整发布闸未重跑，列入未完成项。

**5．版本与登记：通过**

四处均为 **9.2.2**：

- `VERSION:1`
- `pyproject.toml:15`
- `SKILL.md:23`
- `CHANGELOG.md` 索引及详细段

CHANGELOG 表述没有夸大为“无溢写”或“亿级资源上限已证明”。它区分了 `getrusage` RSS 与受阻的 `/usr/bin/time -l` 测量，并明确默认桶规模不能外推任意亿级或偏斜输入。

抽查工程资源日志，4,999,000 宽键聚合、RSS 2,269,954,048 B、临时盘采样 779,812,864 B 和 `time` 墙钟 6.64 秒均有对应记录。QUQ 后续实跑尚未写入该详细段，但现有登记没有冒充已独立验证该实跑。

附带检查：全分支 `git diff --check` 报告工程证据 `W1_timing.txt` 六处尾随空格；生产代码、测试及四处版本文件的定向检查通过。该问题不影响本次运行判定。

**6．合并风险**

`8457f70..HEAD` 共七个提交：

```text
75f7501  收官审查提示词及 QUQ 实跑声称
b6c57ef  W1 盲审记录
b867f78  9.2.2 实现及测试
bb8c871  工单 v3.1、复核 r3
6ca25c7  工单 v3、复核 r2
49f2eb2  工单 v2、复核 r1
681e44c  初始工单
```

差异共 **21 个文件，+8,780/−22**；其中生产脚本 **+92/−10**，其余主要为测试、版本登记及工程证据。

按改动面判断，未读取 main：

| 冲突概率 | 文件及原因 |
|---|---|
| 高 | `VERSION`、`pyproject.toml`、`SKILL.md`：版本号位置重叠或版本语义冲突 |
| 高 | `CHANGELOG.md`：顶部索引、详细段插入位置及可能的版本撞号 |
| 视另一工程改动而定 | `scripts/evm/replay_duck.py`：涉及入口、事件构建和补算函数 |
| 视另一工程改动而定 | `scripts/tests/test_engine_equivalence.py`：共享夹具 helper、运行 helper、main 调用点 |
| 低 | 本工程唯一目录下的新增文档和证据 |

合并时须重新核对版本四处一致。最终脚本字节若变化，当前收据的 producer SHA 将失配，必须用最终脚本重跑，不能手改收据摘要。

**未完成项**

1. **环境阻断**：无可写临时目录，未重跑磁盘版 `test_engine_equivalence.py`、磁盘资源测试、真实原子替换及完整发布闸；内存测试不替代这些项目。
2. **访问纪律阻断**：完整 `changelog_lint.py` 的归档及活跃—归档边界检查；仅活跃部分通过。
3. **证据不可访问**：QUQ 原始输入、22 桶完整日志、实际收据和资源采样；未独立验证 rc、完整摘要与实跑资源峰值。
4. 合并后的最终版本、案卷补算及发布闸属于后续交接，本次未执行。

**实际执行命令清单**

同类源码读取合并列示；内联 Python 均通过 `python3 -B -c` 执行，未保存脚本文件。

```text
pwd
git status --short
git status --porcelain
git branch --show-current
git rev-parse HEAD
git log --oneline 8457f70..HEAD
git log --format='%h %s' 8457f70..HEAD
git diff --stat 8457f70 HEAD
git diff --name-only 8457f70 HEAD
git diff 8457f70 HEAD -- scripts/evm/replay_duck.py
git diff 8457f70 HEAD -- scripts/tests/test_engine_equivalence.py
git diff 8457f70 HEAD -- CHANGELOG.md SKILL.md VERSION pyproject.toml
git diff --numstat 8457f70 HEAD -- scripts/evm/replay_duck.py
git diff --check 8457f70 HEAD
git diff --check 8457f70 HEAD -- scripts/evm/replay_duck.py scripts/tests/test_engine_equivalence.py VERSION pyproject.toml SKILL.md CHANGELOG.md
git show 8457f70:scripts/evm/replay_duck.py
git show b867f78:scripts/evm/replay_duck.py
shasum -a 256 scripts/evm/replay_duck.py
command -v python3
python3 -B -c 'import duckdb; print(duckdb.__version__)'
```

另执行：

- `cat/sed/rg`：读取生产脚本、发布闸、manifest、两项守卫、通道预检、相关导入和版本文件；工程文档仅访问获准工程目录。
- 内联 Python：受禁读/禁写审计钩子保护的 `invariant_scan`、活跃 CHANGELOG 检查和临时目录权限检查；禁区读取尝试为零。
- 内联 Python：CSV SQL 内存夹具、冲突反例、VARINT、强制回退、V2 SQL 内存夹具。
- 内联 Python：源码/AST 不变性、DuckDB 执行计划、资源算术及 `b867f78` 脚本字节一致性检查。
- 一次 `python3 -B - <<'PY'` 尝试被 shell 以 `can't create temp file for here document: operation not permitted` 拒绝；随后全部改用 `-c`。