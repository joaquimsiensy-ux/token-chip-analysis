# 盲审R1 r1：FAIL

被审 HEAD：`22654a8f64e8f8b9bfbdb18eb2f6c724d15886ba`，基线：`634c083`。

**已确认违反范围白名单，足以判 FAIL。** 计算层独立复现未发现差异，但当前沙箱禁止临时目录写入，三入口正式对照和五项测试未能完成，不能签发完整验收通过。

1. **范围：FAIL**

`git diff --stat 634c083 HEAD` 共涉及 21 个文件，其中白名单内 10 个、白名单外 11 个。以下文件均位于 `maintenance/repair-20260924-flow-scan-scalability/`：

```text
R1_fable_ctas_probe.md
construct_R1_prompt.md
review_R1_prompt.md
review_R1_prompt_r2.md
review_R1_prompt_r3.md
review_R1_reply_r1.md
review_R1_reply_r2.md
review_R1_reply_r3.md
workorder_R1.md
workorder_R1_v1.md
workorder_R1_v2.md
```

工单允许读取其中部分文件，不等于 §0.3 允许它们出现在指定差异内。本次按用户明确指定的 `634c083..HEAD` 判定，没有自行排除工单或复核文档。

最小复现：

```bash
git diff --name-only 634c083 HEAD -- maintenance/repair-20260924-flow-scan-scalability/workorder_R1.md
```

实际输出：

```text
maintenance/repair-20260924-flow-scan-scalability/workorder_R1.md
```

以下命令无差异输出，退出码为 0：

```bash
git diff --exit-code 634c083 HEAD -- references commands-staging
```

2. **等价性：计算层通过；正式三入口验收未完成**

独立生成固定种子 `92401` 夹具：**300,000 边、3,349 地址、跨度 1,009 天**。未使用施工者夹具脚本或证据文件。

由于不能写临时目录，本次将 `git show 634c083:...` 取得的 flow、wave 基线源码载入内存，用相同边集执行新旧计算逻辑；文件装载入口和报告输出通过内存适配。**这不等同于工单 §0.6 要求的基线文件子进程及三入口正式运行。**

三个主变体去除 `generated_at` 后，保留数组原序逐字节相等：

| 变体 | sinks | 顶层 pulse / pulse_all / slow_spray | mode_hits 三口径计数 |
|---|---:|---|---|
| 无 entity | 6 | 3 / 2 / 2 | 3 / 5 / 2 |
| 有 entity | 5 | 3 / 2 / 2 | 3 / 5 / 2 |
| entity＋exclude | 4 | 2 / 2 / 2 | 2 / 4 / 2 |

已独立断言：

- 老收方补货为 `pulse_all`，fresh 收方数为 0；纯慢速候选超过 500 收方。
- 存在多窗口累计高于最佳单窗，以及同址 sink/spray。
- 同实体边消除、跨实体边保留；exclude 实际改变候选集合。
- 空 elig 时，空字符串来源仍进入预筛和候选行；新旧集合、行内容一致，并验证单侧净流入。
- 自转、非合格来源、同时间同金额来源并列与空候选均符合契约。
- 负值微夹具净流入 **1.01%→1.03%**；合格流入仍为 **3.0%**、来源仍为 **5**、正值收方仍为 **20**；零值独占收方未进入集合。
- top500 微夹具有 **550 收方**，其中 **40 个同额收方跨越第 500 名**；核验数量、唯一性、严格高于边界者全部入选、低于边界者全部排除。只对契约允许的并列部分作等价处理。

`--edges-sol` 正式 binding、EVM 两 run parquet 装载及真实 DuckDB 文件入口均未完成，故第 2 项不能记完整 PASS。

3. **源扫描：内存执行计划符合上限**

对上述全部变体实际执行 `EXPLAIN (FORMAT JSON)`：

```text
5 source statements
1 edges scan node per source statement
candidate queries: materialized tables only
DELIM_JOIN: absent
```

两次预筛、三次物化各含一个底层 `edges` 扫描节点。sink 候选、spray 候选和 top500 查询只读对应物化表；净额一次读取 `sink_net` 后使用字典。entity 变体亦通过相同断言。

未取得真实 EVM parquet 入口的执行计划，因此该入口仍属于验收缺项。

4. **保序与过滤：独立规模检查通过**

DuckDB **1.5.4**、8 线程；有效内存限制 **7.4 GiB**，默认临时目录 `.tmp`。独立构造 300 万行、300 个候选键，调用 HEAD 的 `_materialize_edges`，核验 rowid 顺序、`EXPLAIN ANALYZE` 扫描统计及 12 次点查中位耗时：

| 表 | rowid 顺序下降次数 | 排序表扫描行数 | 无序对照扫描行数 | 排序表／无序点查中位数 |
|---|---:|---:|---:|---|
| `sink_edges` | 0 | 120,832 | 3,000,000 | 9.886／18.684 ms |
| `spray_edges` | 0 | 120,832 | 3,000,000 | 10.381／19.541 ms |

每次点查返回 10,000 行。扫描统计证明本夹具确实发生过滤裁剪，结论不只依赖耗时下降。

成功建表和故意触发建表异常后，均确认 `preserve_insertion_order` 恢复为 `false`。源码亦确认 sink 两张表在 spray 物化前释放。未据此外推亿级表现。

5. **指定测试：2 项通过，5 项受环境阻断**

实际逐条运行：

```bash
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR="$HOME/.matplotlib" python3 -B scripts/tests/<下表文件>
```

| 文件 | 实际结果 |
|---|---|
| `test_flow_anomaly.py` | exit 1，创建临时目录失败；17 例未完成 |
| `test_wave_scan.py` | exit 1，创建临时目录失败 |
| `test_reconcile_v4_receipt.py` | exit 1，`/tmp` 创建目录被拒 |
| `fixtures_lint.py` | exit 0，PASS |
| `invariant_scan.py` | exit 0，PASS |
| `test_batch4_invariant_guards.py` | exit 1，创建临时目录失败 |
| `test_exemption_guards.py` | 前三项只读检查通过；临时目录创建失败，整体 exit 1 |

通过项实际输出：

```text
fixtures_lint PASS：pythia_anchors.json 结构完整（数值以文件为权威，回测后人工更新）
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=62, formal_entrypoints=61, exceptions=0
```

环境阻断最小复现：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/test_flow_anomaly.py
```

实际异常：

```text
FileNotFoundError: [Errno 2] No usable temporary directory found in [...]
```

`test_reconcile_v4_receipt.py` 则明确返回：

```text
PermissionError: [Errno 1] Operation not permitted: '/tmp/batch5d-macos-ancestor-...'
```

这些是环境阻断，未据此认定生产代码回归。

6. **版本与改动量：通过**

- `VERSION`、`pyproject.toml`、`SKILL.md`、CHANGELOG 均登记 `9.1.1`。
- CHANGELOG 索引行含换行 **158 B**，详细段 **4 条**。
- `SKILL.md` 仅版本行变化。
- 生产文件 **+49/−26，共 75 行**，低于 110 行上限。
- 一个新增私有 helper；未见新增 CLI 参数或删除既有公开属性。
- `wave_scan.py`、`scripts/lib`、`scripts/solana` 相对基线零改动。

全程离线，未读取禁读路径、施工过程记录、施工者等价性/耗时证据或探针内容；未修改仓库文件、未 commit。结束时工作区状态与开始一致，仅有原先存在的未跟踪文件 `blind_R1_prompt_r1.md`。
