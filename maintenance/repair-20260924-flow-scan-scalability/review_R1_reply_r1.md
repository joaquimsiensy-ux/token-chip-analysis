# 工单R1复核：退回

方向成立，但 v1 尚不能直接施工。主要阻断项是：**字节等价承诺与基线排序行为冲突、空集合兼容未定义、基线副本缺依赖路径、第 17 例零值边无法通过 Solana 装载，以及亿级物化的资源边界未交代清楚。**

支持此方案的最强理由：四处逐候选查询确实反复读取 `eflow`，物化可以消除重复 parquet 解码和 blocks 聚合。反对直接放行的最强理由：候选相关边仍可能接近全量，且查询组织变化会改变已有并列项顺序。真正需要裁定的是：**接受既有非确定并列项的等价边界，还是继续要求任意输入逐字节一致。后者不能由当前方案保证。**

复核对象：[workorder_R1.md](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260924-flow-scan-scalability/workorder_R1.md)。以下“工单 L…”均指该文件 v1 行号。

核验环境与边界：

- HEAD：`8379655eb634265957680d7e4a3a4745bf824ec6`；包含 `634c083`，祖先检查 exit 0。
- 开始、结束的 `git status --short` 均为空；工单指定生产范围相对 `634c083` 无差异。
- 本机 DuckDB 与 `requirements.lock` 均为 **1.5.4**。
- 全程离线、未 commit、未新建或修改文件。未读取 `~/.codex/`、memories 或其他禁读内容。
- 完成源码、整行锚、内存 SQL/函数微实验；**未运行会落盘的回归套件或 parquet 夹具**。QUQ 案卷实测数字只能确认为工单引述，不能独立核实。

**a）锚与事实段：部分通过，须修正**

实际逐行执行了 `grep -n -F -x`，结果如下。

| 文件与行号 | 核验结果 |
|---|---|
| flow `64–65`、`70–71` | 均唯一；`log()` 的 `print()` 没有 `file=sys.stderr`，实际写 stdout |
| flow `113–137` | `113–135` 均唯一；`136–137` 是空行，各命中 33 处 |
| flow `209–213` | 均唯一；`213` 是 `info` 查询，**不是 sentinels** |
| flow `215` | `sentinels = {Z, DEAD} \| exclude`，唯一 |
| flow `223–231` | 除 `228` 的 `else:` 命中两处外，均唯一 |
| flow `235`、`237–240`、`244–248`、`259–262` | 均唯一，与对应查询事实一致 |
| flow `288–291`、`296–299`、`377–380` | 均唯一，与对应查询事实一致 |
| flow `385–403` | 除 `401` 的 `if a.edges_sol:` 命中两处外，均唯一 |
| CHANGELOG `13`、`103` | 整行均唯一，位置正确 |
| SKILL `23`、pyproject `15`、VERSION `1` | 均唯一，版本均为 `9.1.0` |

事实①的四处查询和两处预筛定位正确。事实④还需明确：`params` 是 **`vars(a)` 去掉 `out`**，不是完整 `vars(a)`。

工单 L17 建议替换为：

> - 0.5 首次修改前，以目标块内可唯一识别的非空整行为锚，执行 `grep -n -F -x -- '<整行>' <文件>`，须恰命中 1 处且基线行号一致；随后逐行核对完整目标块。空行、重复的 `else:` 和 `if a.edges_sol:` 不作独立唯一锚。修改后行号可自然移动，完成报告记录实际 diff 行号。

工单 L8 中 `params` 句替换为：

> `params` 在 `:388` 记录 `vars(a)` 中除 `out` 外的全部键值；相同输入路径与参数下保持一致。

**b）等价性：窗口算法成立，报告字节等价不成立**

**① `IN` / `NOT IN` 与空集合**

对相同的非 NULL 成员集合，字面量列表与子查询的成员判断等价；**全小写并不是等价成立的必要条件**，保留原字符串才是必要条件。正式 Solana 地址保留大小写，现有测试也使用 `Src0`、`SinkA` 等字符串。

空集合存在真实差异：

| 表达式 | 基线空列表拼接 | 真正空子查询 |
|---|---:|---:|
| `'x' IN …` | false | false |
| `'' IN …` | **true** | **false** |
| `'x' NOT IN …` | true | true |
| `'' NOT IN …` | **false** | **true** |

原因是基线空列表会变成 `IN ('')`，它不是空集合。

- `sentinels` 固定包含 `Z` 和 `DEAD`，正常生产执行中 `sent` 不为空。
- `eligible - sentinels` 可以为空。
- 正式 Solana 拒绝空地址，正常 EVM 地址也非空；但 `attach_duckdb()` 没有非空地址校验。因此“非 NULL、全小写”仍不足以证明任意输入等价。
- 本机还实测：`con.executemany(..., [])` 抛 `InvalidInputException`，不能无条件插入空候选集。

工单 L6 建议替换为：

> ② `eligible` 位于 `:209–210`，`info` 位于 `:212–213`，`sentinels` 位于 `:215`；字面量列表位于 `:235/:230`。地址集必须保留原字符串，不做 lower。非空集合使用成员相同且不含 NULL 的临时表时，IN/NOT IN 判断等价。`sentinels` 固定包含 Z、DEAD，不会为空；`eligible - sentinels` 为空时，基线实际执行 `IN ('')`，新 elig 表须保留一行空字符串以兼容该行为。任何空参数列表不得直接传给 executemany。

**② `sink_net` 公式**

数学上成立，但 SQL 必须对**入、出两个 SUM 分别补零**：

```sql
COALESCE(SUM(amt) FILTER (WHERE t = X AND f <> t), 0)
-
COALESCE(SUM(amt) FILTER (WHERE f = X AND t <> f), 0)
```

仅在相减之后 `COALESCE(..., 0)` 不等价：只有入边、没有出边时，第二个 SUM 为 NULL，会把实际净流入错误变成 0。内存实测：只有 7 单位入边的地址，基线为 7，未分别补零的表达式为 NULL。

逐项结果：

- 自转 `f=t=X`：基线贡献 0，新公式两侧均排除，等价。
- `amt=0`：贡献 0；保留或过滤零值边无法靠最终 SUM 区分。
- X 同时属于 presink 与 elig：净流入**不能附加 elig 过滤**，否则会漏算非合格来源、哨兵及其他出入边。
- 两个 presink 地址互转：应分别记一笔正值、一笔负值；不能只按其中一端归属。
- `eflow` 中无贡献行：返回 0。

工单 L28 建议替换为：

> - 1.4 `sink_net` 对每个 presink 地址 X，等于 `COALESCE(SUM(amt) FILTER (WHERE t=X AND f<>t),0) - COALESCE(SUM(amt) FILTER (WHERE f=X AND t<>f),0)`。来源为 eflow，不施加 elig/sent 或 amt>0 过滤；无对应聚合行取 0。自转贡献 0；两个 presink 地址互转时两端分别计入，不重复记账。

**③ `best_window_scan` 同 ts 行序**

工单对**函数返回值**的证明成立，未发现符合其正整数输入条件的反例：

- `125–126`：新增 key 计数并累加正金额。
- `127–132`：同 ts 组使用相同截止时间，过期的旧时间组最终全部移出。
- 组内继续加入正金额，窗口金额严格增加，distinct key 不减少。
- 因此组内中间位置若达标，组末也达标且金额更大。
- `133` 的严格 `>` 使不同时间组的等额最大窗取较早遇到者；时间组顺序没有改变。
- `134` 保存的是 key 集合，同组排列不改变最终集合。

亲测 24 种组内排列，返回值一致。

但是，[flow_anomaly_scan.py:254](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/flow_anomaly_scan.py:254) 后续构造 `src_pct` 时保留首次出现顺序，`:279` 仅按**四舍五入后的 pct** 排序。同 ts 同额来源反转后：

```text
best_window_scan：两次均返回 (20, {'a','b'}, 0, 0)
sources：一次为 [a,b]，另一次为 [b,a]
```

此外还有 sinks、sprays 的同排序键并列，以及 `recipients_top` 的同额排序和第 500 名边界并列。`json.dumps(sort_keys=True)` **不会排序数组**。

工单 L7 建议替换为：

> ③ `best_window_scan(:113–135)` 在按 ts 升序、金额为正整数的输入下，对同 ts 行序不敏感；此结论只覆盖函数返回的金额、key 集合和窗口端点，不覆盖整个报告的数组顺序。`sources(:254–279)` 同 pct 项、`sinks(:282)` 同窗口 pct 项、`sprays(:383)` 同全史 pct 项，以及 `recipients_top(:377–381)` 同累计金额项存在基线未规定的并列顺序；第 500 名并列还可能改变所选地址集合。

工单 L25 建议替换为以下**需由工单采纳的契约修订**，不能由施工者自行放宽：

> - 1.1 保持判据、阈值、字段、排序键、ID、params 键集及确定性计算结果不变，不新增 CLI 参数。无输出排序键并列的固定夹具，报告除 generated_at 外须逐字节相等。已有并列项单独核验：仅允许相同生产排序键组内重排；recipients_top 第 500 名并列时，允许从相同累计金额的边界组中选择不同成员，但须满足数量、唯一性、全部严格高于边界者均入选且低于边界者均不入选。其他差异一律失败。日志沿用现有 log() 的 stdout 行为。

**④ entity 抵消**

通过。三张数据表均从 `eflow` 物化，能继承 `:223–227` 的同实体抵消；跨实体边继续保留。前提是继续使用已验证唯一地址归属的 `entmap`，且不把物化来源改回 `edges`。

**⑤ `info` / retention**

通过。`info`、`eligible`、`build_addr_summary`、`data_first_day` 继续来自原始 `edges/addr`，则：

- `retention_bucket(info[f][1], info[f][0])` 不变；
- fresh 首建日判断不变；
- 历史峰值、当前余额不变。

不应通过筛选后的物化表重建 `info`，也不应因净流入已聚合而删除它。

**c）修法与内存：保留三张数据表合理，但应收紧描述**

三张数据表不是理论上的最少表数，但属于改动小、口径清楚的方案：

- `sink_edges` 只含合格来源的正值入边，不能直接据此算全史净流入。
- 合并 `sink_net` 与 `sink_edges`，必须扩大边集或重复附带聚合值，增加过滤逻辑和存储；不建议。
- `presink/prespray` 需要某种可复用的候选关系，但**不需要先 fetch 到 Python 再 executemany 插回去**。直接 CTAS 预筛结果更简单，也避开空列表异常。
- 去掉候选关系而重复展开预筛子查询，可能再次重扫 `eflow`。

工单 L27 建议替换为：

> - 1.3 `elig(addr)`、`sent(addr)` 保留地址原字符串，插入空集合前必须判空，并按事实②兼容 elig 空集合。`presink(addr)`、`prespray(addr)` 直接使用 `CREATE TEMP TABLE ... AS SELECT t/f AS addr FROM eflow ... GROUP BY ... HAVING ...` 物化预筛结果；候选遍历从对应临时表读取，不要求 Python 往返插入。删除失去引用的 elig_ph/sent_ph。

工单 L39、L42 中“紧接着建 presink/prespray”分别替换为：

> 将该预筛查询直接改为 `CREATE TEMP TABLE presink AS SELECT t AS addr ...`，随后读取 `SELECT addr FROM presink` 供遍历。

> 将该预筛查询直接改为 `CREATE TEMP TABLE prespray AS SELECT f AS addr ...`，随后读取 `SELECT addr FROM prespray` 供遍历。

`1.6` 的 **≤90 行、≤2 helper 足够作为当前方案约束**。我在内存中拼接了一份未落盘的示意改法：含 CTAS 候选表、空 elig 兼容、单次净额扫描、候选列排序和阶段释放，共 **+46/−26＝72 行、1 个私有 helper**，尚未加入 docstring 和资源日志。此计数只说明预算可行，不代表实现已经通过回归。

`sink_net AS ...` 还应定形，避免施工者写成对数千候选的 OR 非等值连接。可采用：

```sql
CREATE TEMP TABLE sink_net AS
SELECT CASE WHEN k = 0 THEN t ELSE f END AS addr,
       SUM(CASE WHEN k = 0 THEN amt ELSE -amt END) AS net
FROM eflow CROSS JOIN (VALUES (0), (1)) sides(k)
WHERE f <> t
  AND CASE WHEN k = 0 THEN t ELSE f END
      IN (SELECT addr FROM presink)
GROUP BY 1
```

本机内存 `EXPLAIN` 显示一次 eflow 扫描、两行常量展开和半连接，没有相关 `DELIM_JOIN`；双方均为候选时能各记一端。正式 EVM VIEW 仍须另验实际计划。

工单 L26 建议替换为：

> - 1.2 仅重组 sink/spray 阶段查询：两次预筛与三次数据物化各至多读取 eflow 一次；装载、addr 概要与 data_first_day 不计入该五次上限。CTAS 语句数不等于实际源扫描次数，须用 EXPLAIN 核验。四处逐候选查询只读物化表。sink_net 不得通过候选数规模的非等值连接恢复 O(候选数×全边数) 工作量。

内存判断：

- `sink_net` 最多约候选数行，很小。
- 两张边表的行数由**候选相关边数**决定，最坏各接近全量。
- 按两个 42 字节 EVM 地址、8 字节 ts、16 字节 amt 粗估，单份 1.097 亿行仅字段有效载荷已约 **11.8 GB**；两份约 **23.7 GB**。这不是 DuckDB 实际占用预测：压缩可能降低，字符串结构、排序和连接工作区又会增加。
- DuckDB 内存库临时数据**支持溢写磁盘，不是超过 memory_limit 就必然 OOM**。本机设置显示默认 `temp_directory='.tmp'`、临时盘上限默认取可用空间的 90%；安装二进制也包含临时缓冲驱逐和临时盘上限诊断。
- 但磁盘不可写、空间不足、不可驱逐分配，以及 Python `fetchall()` 占用仍可导致失败。`--mem-limit` 不约束 Python 列表、集合和字典。
- 未按候选地址组织的巨大临时表仍可能被逐候选全扫。物化能省解码成本，却不能自动保证总处理量可接受。

工单 L29 建议替换为：

> - 1.5 物化容量按实际相关边数评估，不以候选数代替。保持 --mem-limit 语义及默认 temp_directory；日志记录 DuckDB 版本、有效 memory_limit/temp_directory/max_temp_directory_size，以及三张数据表行数。sink 阶段结束后逐表释放 sink_edges、sink_net，再建立 spray_edges。边表按候选列组织（sink 为 t,ts；spray 为 f,ts），并以实际查询计划和候选查询耗时验证过滤效果。耗时报告记录峰值 RSS 与可取得的临时盘峰值；明确 Python fetchall 不受 memory_limit 约束。未获亿级实跑证据前，只声明消除了逐候选底层全量重扫，不声明亿级必可完成。

**d）0.7 证据设计：不足以证明 1.1，需补三入口和构造断言**

30 万边、3,000 地址、400 天可以作为回归规模，不能证明任意输入等价，也不能代表亿级资源行为。现有设计还缺：

- 显式多窗口累计构造；
- 区分顶层 `mode` 与 `mode_hits`：两个 pulse 会自动让 pulse_all 命中数达两例，可能根本没测到“老收方补货”；
- 无 entity、同实体抵消、跨实体保留的分支覆盖；
- exclude 变体是否实际改变输出的断言；
- 空 elig、空候选、自转、非合格来源入边；
- 排序并列和第 500 名并列边界；
- `--duckdb` 与 `--edges-evm-v2` 入口。

工单 L19 建议替换为：

> - 0.7 先冻结夹具和基线报告，施工后以同一夹具、相同输入路径及参数重跑。主夹具保留 ≥3,000 地址、≥300,000 边、跨度 ≥400 天；断言顶层 mode 为 pulse、pulse_all、slow_spray 的地址各 ≥2，并另列 mode_hits 分布；sink ≥5，其中包含多窗口累计高于最佳单窗者及同址 sink/spray。至少一个纯 slow_spray 有 >500 收方。分别运行无 entity、有 entity、有 entity 加 exclude 三个变体，断言同实体边被抵消、跨实体边保留、exclude 确实改变相关候选或金额。另设空 elig、空候选、自转、零值、非合格来源入边及排序并列微夹具。无并列主夹具去掉 generated_at 后逐字节比较；并列微夹具按 1.1 专项验证，不能仅排序所有数组掩盖差异。补跑 --duckdb 和 --edges-evm-v2 两个入口，各入口内部做基线/施工后对照；记录每个变体的覆盖断言与结果。

EVM 夹具**技术上可离线合成**。本轮只读限制不允许实际写 parquet；施工阶段可复用 [test_lit_regression_f008.py:74](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_lit_regression_f008.py:74) 的列结构和编码方法，批量写入，避免一条边一个 run。

具体写法如下；`evm_edges` 使用固定映射得到的 lowercase 40-hex 地址，保留 Z/DEAD，按两个互斥 block 区间分段：

```python
# 仅用于施工阶段临时夹具；不修改现有 write_run。
for part, (lo, hi) in enumerate(((0, len(evm_edges)//2),
                                (len(evm_edges)//2, len(evm_edges)))):
    run_dir = v2_root / f"run_{part}"
    run_dir.mkdir(parents=True)
    con = duckdb.connect()
    con.execute("""CREATE TABLE logs(
        transaction_hash VARCHAR, log_index BIGINT, block_number BIGINT,
        topic1 VARCHAR, topic2 VARCHAR, data VARCHAR)""")
    con.execute("CREATE TABLE blocks(number BIGINT, timestamp VARCHAR)")
    logs, blocks = [], []
    for i in range(lo, hi):
        ts, f, t, amt = evm_edges[i]
        bn = i + 1
        logs.append((f"0x{bn:064x}", 0, bn,
                     f[2:].rjust(64, "0"), t[2:].rjust(64, "0"),
                     f"0x{amt:064x}"))
        blocks.append((bn, str(ts)))
    con.executemany("INSERT INTO logs VALUES (?,?,?,?,?,?)", logs)
    con.executemany("INSERT INTO blocks VALUES (?,?)", blocks)
    con.execute(f"COPY logs TO '{run_dir / 'logs.parquet'}' (FORMAT PARQUET)")
    con.execute(f"COPY blocks TO '{run_dir / 'blocks.parquet'}' (FORMAT PARQUET)")
    con.close()
```

同一 `evm_edges` 再写入 `edges(ts BIGINT,f VARCHAR,t VARCHAR,amt HUGEINT)` 的 DuckDB 文件即可覆盖另一路。EVM 对照还须确认：

- 实际进入“run 块区间互斥——VIEW 轻路径”；
- 解码后边数、金额、地址与夹具一致；
- EVM 报告没有 `edge_source_binding`。

跨入口报告的 `params` 和 Solana binding 天然不同，不能要求跨入口只去掉 `generated_at` 就字节相等；严格比较应在**各入口的新旧脚本之间**进行。

**基线副本 import：原写法不充分。**

`wave_scan.py:68–76` 根据自身位置导入 `../lib`、`../solana`。仅将两个文件放在同一临时目录，亲测报：

```text
ModuleNotFoundError: No module named 'wave_contract'
```

补入仓库依赖路径后，两个基线模块在内存中成功加载，`flow.load_sol is wave.load_sol` 为 true。

工单 L18 末尾追加：

> 基线子进程显式设置 `PYTHONPATH=<repo>/scripts/lib:<repo>/scripts/solana:<repo>/scripts/report`，使用 `python3 -B <tempdir>/flow_baseline.py ...`；同目录 wave_scan.py 仍由基线副本优先导入。开工门禁保证这些共享依赖与 634c083 一致。基线与施工后运行复用同一份已生成的输入和 formal_cli_args，不分别重建带不同路径的夹具。

**e）第 17 例：可构造，但原要求不最小且有错误**

- 双身份 MixedHub 可构造。
- 现有测试 `:101–109` 已有 **600 收方的 SlowSpray**，无需再造第二个；补 `recipients_top` 长度断言即可。
- 正式 Solana `wave_scan.py:172–181` 明确拒绝 `amount<=0`。零值边不能加入现有 `run()` 主夹具。
- 零值加不加 `amt>0` 都不改变净额，不能证明“未加过滤”。若需要区分两种实现，可在 `--duckdb` 微夹具中加入该入口现有装载器接受的负值边。
- 百分比断言必须有 `*100.0`，并与生产保持相同运算顺序。
- 测试尾行打印的是“失败项数”，没有“16 例总数”可直接 `+1`。

工单 L49 建议替换为：

> - 新增第 17 例 MixedHub：复用既有 SRC，5 个来源于 day 700 各向 MixedHub 转入 6×10^9，MixedHub 于 day 701 向 20 个新收方各转出 10^9。断言 MixedHub 同时出现在 sinks 与 sprays，净流入为 `round((5*6*10**9 - 20*10**9) * 100.0 / TOTAL, 4)`；可增加同日正值自转，预期净额不变。复用既有 SlowSpray，断言 `len(recipients_top)==500` 且 `all_time.recipient_count==600`。零值边放入独立 --duckdb 或 EVM 微夹具，不能加入正式 Solana 夹具；零值结果不变不能作为未添加 amt>0 过滤的证明。补充非合格来源入边和单侧净流入用例。文件头追加第 17 条说明；保留尾行实际失败项计数逻辑。

**f）回归面：没有发现源码哈希绑定；保留转导入即可**

- `test_reconcile_v4_receipt.py:362` 直接引用 `flow_anomaly_scan.load_sol`。保持 flow `:64–65` 的转导入不变即可；不能因 `main()` 中仍能间接调用而删除公开模块属性。
- `invariant_scan.scan_python()` 对当前 flow 的实际返回为：

```text
producers = {'flow-anomaly/v3'}
consumers = set()
transports = set()
atomic_writes = set()
```

  其扫描 schema、网络调用、原子写入和入口结构，不解析 SQL 口径。只调整内部 SQL、私有 helper，不应改变登记结果。
- `test_batch4_invariant_guards` 检查上述守卫及注册生产链，没有 flow SQL 模板钉定。
- F008 的 parquet AST 守卫保护 `load_evm_v2`；本单不改 wave，保持不受影响。
- `test_exemption_guards` 保护 `multicall_balances` 的生产可达性，与本 SQL 改动无直接关系。

按要求执行了限定现役目录、排除禁区的 `grep -rn`：

```sh
grep -rn -E \
  --include='*.py' --include='*.json' --include='*.md' \
  --exclude='attic.md' \
  --exclude-dir='archive' --exclude-dir='blind-reviews' \
  --exclude-dir='.hypothesis' --exclude-dir='.staging_*' \
  --exclude-dir='__pycache__' \
  -e 'flow_anomaly_scan|flow_anomaly_report' \
  scripts references commands-staging
```

关键命中及意义：

| 位置 | 实际绑定内容 |
|---|---|
| invariant_manifest `200–202`、`1259` | schema、脚本路径、入口登记 |
| handoff_manifest `553–559` | 报告 schema 与必要字段 |
| adjudication_validator `425`、`480` | **报告文件**哈希 |
| shared_release_receipt `1564–1613` | Solana 派生报告的边源 binding |
| handoff_manifest `1192–1202` | provenance 绑定 entity_source_trace、wave 等依赖，未包含 flow |
| scripts/lib/producer_history.py | 未命中 flow |

因此，在核查的现役链中，**没有发现 flow_anomaly_scan.py 源码哈希绑定**；不能据此说报告文件也没有哈希绑定。重跑报告仍可能影响依赖其文件哈希的裁决产物。

工单 L8 末尾建议追加：

> `test_reconcile_v4_receipt.py:362` 依赖 flow.load_sol 转导入，须保持。现役发布链未发现 flow 脚本源码哈希钉定，但 candidate adjudication/handoff 绑定报告文件本身；源码兼容不代表任意重写报告后下游哈希自动兼容。以上为静态核查，施工后仍执行 0.9 定向回归。

**g）原则与版本档位：修版合适，索引文本超限**

- `references/**`、`commands-staging/*` 零改动，SKILL 仅版本号：合适。
- 按 `CHANGELOG.md:4`，既定契约内的性能修复记 **修**，`9.1.1` 合适。
- 工单 L57 索引行实测 **206 B，不含换行；207 B，含换行**，超过其自身 ≤200 B 限制。
- “亿级可完成”及“报告字节不变”都超出了现有可证明范围。

工单 L1 建议替换为：

> # 工单 R1（v2）：flow_anomaly_scan 候选边物化，消除逐候选底层全量重扫——版本 9.1.1

工单 L57 建议替换为下文，UTF-8 **含换行 158 B**：

> - **9.1.1**（2026-09-24）flow 扫描候选边物化，消除逐候选底层全量重扫（QUQ ANOM-009）；参数、schema 与判据不变，档位 修。

工单 L64 中“等价性证据摘要”建议替换为：

> 等价性证据摘要：逐项列明三种输入入口、entity/exclude 变体、无并列夹具字节比较及并列微夹具专项结果；耗时证据须附 DuckDB 版本、有效资源设置、候选数、物化行数、查询计划、墙钟和峰值 RSS，未知或无法测得项明确标注。

其中“references/commands 不变，各贴 wc -c 合计”建议替换为：

> references 与 commands-staging 的零改动使用 git diff 验证，字节合计仅作辅助记录；总字节数相同不能证明内容未改。遵守禁读路径，不为统计字节而读取 references/attic.md。

| 审项 | 结论 | 施工前必须处理 |
|---|---|---|
| a 锚与事实 | 部分通过 | sentinels 改为 `:215`；区分唯一锚与上下文行；更正日志和 params 描述 |
| b① 集合替换 | 退回 | 明确空 elig 的 `IN ('')` 兼容；空 executemany 判空；不 lower 地址 |
| b② 净流入 | 有条件通过 | 两侧分别补零；全量 eflow 口径；双方候选互转正确记账 |
| b③ 同 ts | 函数通过、字节承诺退回 | 补 sources 并列反例；修订 1.1 与比较器 |
| b④⑤ entity/info | 通过 | 物化读 eflow，概要和 info 保持原来源 |
| c 修法与资源 | 有条件通过 | 三数据表保留；候选 CTAS；固定净额计划；补内存、磁盘及临时表重扫边界 |
| d 等价性证据 | 退回 | 补三入口、构造断言、并列专项及基线 import 路径 |
| e 第 17 例 | 退回 | 复用既有 SlowSpray；移出 Solana 零值边；按生产公式断言 |
| f 回归与哈希 | 静态核查通过 | 保留 load_sol 转导入；施工后执行定向回归 |
| g 原则与档位 | 修版通过 | 缩短索引行；删除未经验证的完成性和全局字节承诺 |