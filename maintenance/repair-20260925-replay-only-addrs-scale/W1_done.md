# W1 完成：9.2.2 地址补算改为去重键哈希分桶，等价性及定向测试通过；time -l RSS 测量受环境阻断

施工结果：`--only-addrs` 使用 raw_rows VIEW，按完整 `(tag,tx,li)` 哈希分桶；每桶先全桶查冲突，再过滤与去重，最终合并跨桶 `(a,b)`。生产 +92/−10，共 102 行，新增私有 helper 1 个、新 CLI 0 个。全量计算函数、峰值窗口与回退、收据构造和原子写出通过源码逐字核验。

## 开工基线与边界

工作目录 `/Users/uravvv/.claude/worktrees/tca-only-addrs`，开工四项原始结果：

```text
$ git status --short
（空，exit 0）
$ git rev-parse --abbrev-ref HEAD
fix/replay-only-addrs-scale
$ git rev-parse --short HEAD
bb8c871
$ git merge-base --is-ancestor 8457f70 HEAD
（无输出，exit 0）
```

START=`bb8c871`。§2 指定的生产锚 89/160/376/652/666/681/685、测试锚 83/143/318、版本锚 VERSION:1 / pyproject.toml:15 / SKILL.md:23、CHANGELOG:13/106 均经 `grep -n -F -x` 检查唯一命中且行号相符，并读取完整修改块。模块 docstring 起始锚为第 2 行。没有 commit/push、stash/checkout/reset/rebase，也没有创建 worktree 或进入主仓库。

基线副本由 `git show 8457f70:scripts/evm/replay_duck.py` 生成，保留 `scripts/evm/replay_duck.py` basename；运行时 PYTHONPATH 指向本工作树 scripts/evm 与 scripts/lib。基线 sha256 为 `c3a6123a4b57b22f7dc0ef7b553a5b2322acf9b4a697bc7d2acd1a59cf54a85d`，施工脚本为 `e58e9f127bfd2720d417870bed6183b9f4eccc188edd79b4c4cc4db358a8112d`。每次收据分别验证真实脚本和输入摘要，没有修改 provenance 来通过比较。

临时目录使用 `tempfile.mkdtemp()` 并 `Path(...).resolve()`；系统临时目录可写，无需 `.staging_w1`。开工磁盘可用 69,222,400,000 B，所有重放前检查不少于 20 GiB。数据保留在临时目录，未清理；位置见下文复现信息。

## 先红后绿

生产文件仍与基线逐字相同时，单独运行新增 `followup_bucketed_case()`，rc=1，失败于分桶断言：

```text
assert len(buckets) == 6 and {k for _, k, _ in buckets} == {"6"}, p.stdout
AssertionError: v2=[100,160) v2 收 300 条
合计事件 280
value 最大位数=21 -> HUGEINT 路径
[only-addrs] 块级精确峰值 6 址（有事件 5）→ .../block_precision_followup.json
```

基线没有桶日志，未在预检阶段误失败。施工后同用例 rc=0：

```text
PASS: W1 300 行/6 桶、Python 块末峰值、低门槛、重复行、跨块冲突、非法环境变量
```

## §0.7 等价性证据 1–7

详细断言、命令、rc、超时与执行路径见 [W1_equivalence.txt](W1_equivalence.txt)，生成器见 [W1_fixture_tools.py](W1_fixture_tools.py)。

1. 主夹具：固定种子 20260925，DuckDB 向量化生成 1,999,000 唯一事件并复制 1,000 原始行，合计保留 2,000,000 行；6,004 地址、同块多事件、mint 与 Z/DEAD burn、最大 v 为 31 位。v1csv 与两个连续互斥区间 `[100,1000100)` / `[1000100,2000100)` 的 v2 run 由同一事件集生成，分别重建 done 元数据，全部 run 完成后签发采集根收据；两格式预检通过。
2. 补算对照：needs 字典与 trigger_days 并集 1,055 址，含零事件、纯出方、纯入方、Z/DEAD 和低于全量门槛的正峰值 1。双格式 K=8 与默认 K=1 均与基线 only-addrs 收据逐键逐值相等；纯出方及零事件地址都是 peak=0/peak_blk=null。K=8 实际桶行数 `[249665,250200,250045,249729,250811,249882,249821,249847]`，总和 2,000,000，最大 250,811。
3. 全量路径：双格式三份业务 JSON 全等，stats 全字段比较。producer/preflight/inputs/outputs 按真实文件独立重验，仅允许脚本 SHA 差异与已证明业务键相等后的余额 JSON 键序摘要差异；差异逐项写入证据。补算前后全量四产物原始字节不变。主夹具含负余额纯出方，因此基线/施工全量均为 gate rc4，这是预期输入特性；小夹具的 merged CSV 字节、parquet 行、camps/pass2 业务 JSON、stats 与绑定对照均通过且 rc0。
4. 冲突：双格式各自独立执行同键异值、跨块、端点不同且仅一行命中、两端均未命中，以及实际 hash 首桶 0/4、末桶 3/4。每种 4 行、K=4、并集 5 址；跨块 v2 另分成两个 run，覆盖同通道跨 run。先预检通过，再要求基线全量/施工全量/施工 only-addrs 都在冲突检查处拒绝；无新收据，旧收据字节保留，全部通过。
5. 边界：37/38 位、force-varint、首达峰值、全零增量、空并集、非法 SEG_ROWS 四值（仅补算 rc2，全量 rc0）、非空并集零保留事件、空桶、9 行同键落同桶且 SEG_ROWS=1 的严格 >4× 偏斜告警均通过。v1 NULL 值源行的 reject、拒绝行为和结果与基线一致（2 源行，1 保留行，bad/out 均 0，原全量 n_dedup_removed=1 的既有计数保持）。另以三键落三个不同桶的同块 +10/−10、下块 +5 验证 VARINT 跨桶合并；真实窗口与人为触发 Python 回退两条路径均返回 peak5，而非块内伪峰10。
6. 执行路径：记录真实连接上的 duckdb_tables()/duckdb_views()、执行 SQL、原生扫描 EXPLAIN 投影。raw_rows 为 VIEW、无 events 表；K=8/K=1 分别恰有 16/2 条完整键 GROUP BY 源查询，每条都带当前桶谓词；没有全量 raw_rows/events CTAS。DuckDB 1.5.4 原生 parquet 节点名实际为 READ_PARQUET（工单称 PARQUET_SCAN），如实保存原计划。ab_raw 最终 DROP，ab 跨桶按 `(a,b)` 聚合。
7. 运行记录：每个变体的命令、engine rc、launcher rc、行数/K/地址并集和结论均有记录；主重放超时 900s，小反例 120s，常驻回归 300s，生成 600s。等价性没有 SKIP；非法环境变量与空并集在桶循环前拒绝，K 记未执行（证据末尾另列输入行数与并集）；指定 time -l RSS 方法单独标为 INCOMPLETE，不混写 PASS。工具记录中的早期测量/计划断言纠正详见差异说明，接受结果是最终成功运行。

## §0.8 资源证据

完整日志与每桶耗时、SQL/EXPLAIN、连接设置见 [W1_timing.txt](W1_timing.txt)。DuckDB 1.5.4；重放统一 `--mem-limit 2GB --threads 2`，连接实际显示 memory_limit=`1.8 GiB`，threads=2，temp 路径与 max_temp_directory_size 均从执行连接打印。

| 格式 / 路径 | 墙钟 s | 峰值 RSS B（getrusage） | 1 秒采样临时盘峰值 B |
|---|---:|---:|---:|
| CSV 基线 | 10.03 | 1,489,387,520 | 0 |
| CSV K=8 | 21.82 | 441,188,352 | 0 |
| CSV 默认 K=1 | 11.26 | 1,271,005,184 | 0 |
| v2 基线 | 1.77 | 1,501,609,984 | 0 |
| v2 K=8 | 4.82 | 460,750,848 | 0 |
| v2 默认 K=1 | 1.78 | 1,274,691,584 | 0 |

默认规模补测 4,999,000 唯一键，tx 66 / 地址 42 / ts 19 / v 37 字符，单桶完整键 GROUP BY + COUNT DISTINCT 成功：墙钟 6.64s，RSS 2,269,954,048 B，临时盘采样峰值 779,812,864 B，输入 parquet 103,269,669 B。进程 RSS 包含 DuckDB 内存预算外开销；该结果不代表桶大小或内存有硬上限。

生成阶段另以同种子补测：22.180s（外层采样计时），输入/生成目录采样峰值 567,380,056 B、生成临时盘采样峰值 0；原冻结夹具未重写。主夹具初次最终输入目录 567,437,894 B；全量输出目录 CSV/v2 为 641,741/642,844 B，补算收据另为 99,470 B。每秒采样可能漏短暂峰值。K=8 比基线 RSS 更低但墙钟更长，属于以 IO 换内存，不外推亿级数字。

正常每桶两条源查询，此外逐通道 reject=1、保留行 COUNT=1，v2 probe=1，maxlen=1；预检的摘要/元数据读取另计，失败取样额外 1 条源查询已在日志标注。源查询次数不等于完整文件字节读取倍数。

未完成的指定测量方式：macOS `/usr/bin/time -l` 能打印墙钟，但读取 kern.clockrate 被沙箱拒绝，launcher rc1，不能生成其 RSS 报告。每次引擎真实 rc 单独记录，RSS 改由同一子进程 getrusage 记录（macOS 单位 B）。完整最小复现：

```text
$ /usr/bin/time -l /usr/bin/true
        0.00 real         0.00 user         0.00 sys
time: sysctl kern.clockrate: Operation not permitted
exit 1
```

因此“time -l RSS 方法验收”保留为环境未完成项；没有把替代读数标成 time -l 成功。

## 实际 diff 行号与范围

| 文件 | 当前改动位置 |
|---|---|
| scripts/evm/replay_duck.py | 35–40 说明、52 常量；97/103/125/166/171–176 build_events；393–443 分桶 helper；446/451–461 followup 路由；727–733 环境变量；747/762–767 main |
| scripts/tests/test_engine_equivalence.py | 17 import；83/111–145 v2 构造器；150–152 _run；325–401 新用例；409 main 调用 |
| VERSION / pyproject.toml / SKILL.md | 1 / 15 / 23，仅版本登记 |
| CHANGELOG.md | 13 索引（含换行 179 B）；107–113 详细段 |

新增报告与证据文件均在本工单目录白名单内。Git 对未跟踪文件不计入 diff --stat，下面另列它们；不执行 git add。

`git diff --stat 8457f70`：

```text
 CHANGELOG.md                                       |   8 +
 SKILL.md                                           |   2 +-
 VERSION                                            |   2 +-
 .../construct_W1_prompt.md                         | 131 ++++++
 .../review_W1_prompt.md                            |  16 +
 .../review_W1_prompt_r2.md                         |  19 +
 .../review_W1_prompt_r3.md                         |  19 +
 .../review_W1_reply_r1.md                          | 508 +++++++++++++++++++++
 .../review_W1_reply_r2.md                          | 348 ++++++++++++++
 .../review_W1_reply_r3.md                          | 223 +++++++++
 .../workorder_W1.md                                | 118 +++++
 pyproject.toml                                     |   2 +-
 scripts/evm/replay_duck.py                         | 102 ++++-
 scripts/tests/test_engine_equivalence.py           | 106 ++++-
 14 files changed, 1582 insertions(+), 22 deletions(-)
```

`git diff --stat START`（START=bb8c871）：

```text
 CHANGELOG.md                             |   8 +++
 SKILL.md                                 |   2 +-
 VERSION                                  |   2 +-
 pyproject.toml                           |   2 +-
 scripts/evm/replay_duck.py               | 102 ++++++++++++++++++++++++++---
 scripts/tests/test_engine_equivalence.py | 106 ++++++++++++++++++++++++++++---
 6 files changed, 200 insertions(+), 22 deletions(-)
```

未跟踪交付：W1_done.md、W1_equivalence.txt、W1_timing.txt、W1_fixture_tools.py。`references/**`、`commands-staging/*` 及工单列出的禁止修改文件 diff 为空；`git diff --check` 通过。

## §0.9 定向测试尾行

均以 `python3 -B scripts/tests/<名称>.py` 执行，外层每项 timeout=600s；没有运行 run_all.py。Hypothesis 存储重定向至自建临时目录，未使用工作树 .hypothesis。

`test_engine_equivalence.py`：rc=0，19.043s

```text
PASS: W1 300 行/6 桶、Python 块末峰值、低门槛、重复行、跨块冲突、非法环境变量
PASS: 三引擎 gate/退出码 10 例 hypothesis 全等；gate PASS 六产物全等；gate FAIL 正式序列零产物；VARINT 双引擎确定性对表通过
PASS: R09 块级补算峰值等价、零事件地址、非法输入与坏事件不覆盖全量产物
```

`test_audit_release_gate.py`：rc=0，62.970s

```text
PASS: audit_release_gate 净室资产/哈希/CEX受益权/阴性结论/图表封口与负钳零/对抗复核否决/四查WARN拦截/双线阈值/嵌套未决暴露/静置仓全集对账/日级峰值口径闭环十一类契约全过
ok    16 F07 followup producer sha 过期拒
ok    17 F07 followup channels 缺席拒
ok    18 F07 followup channels sha 不符拒
ok    19 F07 count 不一致拒
ok    20 F07 只有 needs/trigger 无 summary 拒
ok    21 F07 兼容：原始触发日清单在 data/ 不被误判（GREEN→GREEN）
ok    22 F07 兼容：只有原始触发日清单、无峰值产物（GREEN→GREEN）
```

`test_fault_injection.py`：rc=0，1.552s

```text
PASS: 故障注入 F0–F5 + P0-02 四类通道完整性×三引擎 + R1 receipt 生成/漂移
```

`test_repair_batch_c.py`：rc=0，359.220s

```text
PASS: repair batch C (F-05+F-04+fixround1+fixround2) 263 checks
[camp-spec] camps 含非法阵营名: ''
[camp-spec] camps 阵营「散户」是 EVM 引擎的残差桶（100−已知阵营），不得在 spec 里配置——显式配置会让 replay_pass2/replay_duck 同日写两个元素；把这些地址归入其他阵营或删掉
[camp-spec] /var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/tmpmvsg2_8q/entity_camps.json JSON 重复键 'So1AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'——同一地址写了两遍（后值会静默覆盖前值），先修文件再重放
[camp-spec] 阵营定义文件不存在：camps.json——evolution 必须显式给 camps（无阵营定义就放一份 {}），拒绝静默按空 spec 重放
[camp-spec] camps_dup.json 地址 So1AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA 同时归入阵营「营1」与「营2」（原文 'So1AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'）——阵营互斥，JSON 键序决定归属是静默错误，先修 spec 再重放
/Users/uravvv/.matplotlib is not a writable directory
Matplotlib created a temporary cache directory at /var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/matplotlib-t9vspfdx because there was an issue with the default path ({configdir}); it is highly recommended to set the MPLCONFIGDIR environment variable to a writable directory, in particular to speed up the import of Matplotlib and to better support multiprocessing.
Matplotlib is building the font cache; this may take a moment.
```

`test_repair_batch1.py`：rc=0，14.191s

```text
PASS 1 segs (0 gaps) in 0s -> /private/tmp/repair-batch1-iqzojva3/window/window.jsonl
PASS v6.41.0 batch1 steps 1-6 RV-07/RV-04/RV-17/F-03/F-01/A5v3/F-04
Matplotlib is building the font cache; this may take a moment.
[window_fetch] ERROR → /private/tmp/repair-batch1-iqzojva3/window/window_receipt.error.20260926T023701.560455Z.55762.json
[window_fetch] 检测/提交失败（exit 1）: receipt switch injected
[window_fetch] ERROR → /private/tmp/repair-batch1-iqzojva3/window/window_receipt.error.20260926T023701.563445Z.55762.json
[window_fetch] 检测/提交失败（exit 1）: post-receipt data cleanup injected
findfont: Failed to find font weight normal, now using 300.
```

`test_repair_batch_d.py`：rc=0，96.120s

```text
ok    F-D3 ③ A4 finalize 同案封口 figures/state 产物
ok    F-D3 ④前置：fig1 producer 落 legend receipt
ok    F-D3 ④ A5 seal 同案收口（state→figures→A4→A5 全链一案贯通）
================================================
BATCH D 全部通过
/Users/uravvv/.matplotlib is not a writable directory
Matplotlib created a temporary cache directory at /var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/matplotlib-6jc835t2 because there was an issue with the default path ({configdir}); it is highly recommended to set the MPLCONFIGDIR environment variable to a writable directory, in particular to speed up the import of Matplotlib and to better support multiprocessing.
Matplotlib is building the font cache; this may take a moment.
```

`test_review_evm_integrity.py`：rc=0，0.240s

```text
PASS: B-01 payload mismatches and B-02 rejected rows fail closed
[inputs] sha256 /var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/tmp4hsy9zh9/a.csv=557e9657255ff768f3dc84d389d4ec3fc189851fde82255ed60aecaae868643c /var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/tmp4hsy9zh9/b.csv=ccb2a9998547afc6ae7a692b1010db3de32df27a158235dbc235da0c865f9c51
[FAIL-CLOSED] 跨源同 (tx,log_index) payload 冲突 1 条(样本 [{'key': ('0xtx', 0), 'a': (100, '0xtx', 0, '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', 100, '0xhash'), 'b': (100, '0xtx', 0, '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 100, '0xhash')}])
[inputs] sha256 /var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/tmpz9sznbi7/a.csv=557e9657255ff768f3dc84d389d4ec3fc189851fde82255ed60aecaae868643c /var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/tmpz9sznbi7/b.csv=ce4646145d1de54904d918e62d43fa0b6f34df59017d3358bb55ddb63ed35ce2
[FAIL-CLOSED] 跨源同 (tx,log_index) payload 冲突 1 条(样本 [{'key': ('0xtx', 0), 'a': (100, '0xtx', 0, '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', 100, '0xhash'), 'b': (101, '0xtx', 0, '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', 100, '0xhash')}])
[inputs] sha256 /var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/tmp794jzdii/a.csv=557e9657255ff768f3dc84d389d4ec3fc189851fde82255ed60aecaae868643c /var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/tmp794jzdii/b.csv=dfa9ffd59e45535b5527510075cff50cd61c148bac98ee941fd9990a8424057a
[FAIL-CLOSED] 跨源同 (tx,log_index) payload 冲突 1 条(样本 [{'key': ('0xtx', 0), 'a': (100, '0xtx', 0, '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', 100, '0xhash'), 'b': (100, '0xtx', 0, '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', 100, '0xother')}])
[inputs] sha256 /var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/tmpbwiimqlg/a.csv=557e9657255ff768f3dc84d389d4ec3fc189851fde82255ed60aecaae868643c /var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/tmpbwiimqlg/b.csv=25742aa1537bac662d36f0e78627ba15c542068882c5f4bdec7e484272ef7409
```

`test_review_resume_integrity.py`：rc=0，5.649s

```text
PASS: H-02/H-03 + U2b staged first capture + R2 legacy manifest refresh + H-04/H-05/H-06
阵营序列 2 个小时点，已写 data/camp_share_series.json
末态占比： {'_supply_raw': '200', 'A营': 50.0, 'B营': 50.0, '锁仓/销毁': 0.0}

质押修正后有效持仓 top15：
  A              100  50.000%  (现货100+质押0)
  B              100  50.000%  (现货100+质押0)
有效持仓末态已写 data/effective_balances.json
```

`test_apu_legacy_gaps.py`：rc=0，3.268s

```text
PASS: APU 存量缺口工单契约测试全绿
ok    t3.迁移后现行校验器消费通过
ok    t3.candidate 条目补 id（保留 cid）
ok    t3.迁移产备份
ok    t3.迁移幂等（重跑不重复改写）
ok    t3.无 id 无 cid 条目拒绝迁移且不改写
ok    t3.登记哈希失配时拒绝迁移 data_map（fail-closed）

```

`fixtures_lint.py`：rc=0，0.021s

```text
fixtures_lint PASS：pythia_anchors.json 结构完整（数值以文件为权威，回测后人工更新）
```

`invariant_scan.py`：rc=0，4.067s

```text
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=62, formal_entrypoints=61, exceptions=0
```

`test_batch4_invariant_guards.py`：rc=0，12.340s

```text
PASS B4F2C2 local binding forms + nested scope boundary
PASS B4-G1: bare pool / labels / vertical slice / denominator injections
PASS B4F2C2 M4/M5 import bindings + four live ready chains
INJECT R9-B4-STALE-01 failed producer leaves old canonical -> RED
INJECT B4F2-STALE-03 dead quarantine/error calls -> RED
INJECT B4F2-STALE-03B constant-false contract calls -> RED
INJECT R9-B4-STALE-02 remove formal producer artifact registration -> RED
INJECT B4F2-STALE-04 newly added standalone producer -> RED
```

`test_exemption_guards.py`：rc=0，0.432s

```text
PASS EX-01: --chain choices remain exploration-derived
PASS: exemption guards (EX-01 full-F-03)
PASS EX-01: no production import/string reference to multicall_balances
PASS EX-01: absent from formal producer registry / evidence targets
INJECT EX-01-RED production import -> RED
```

`changelog_lint.py`：rc=0，0.022s

```text
PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 89 条 + 归档 139 条
```

## 与工单差异、未完成项与交接

- 未完成项仅为指定 `/usr/bin/time -l` RSS 方法的环境阻断，已有等价用途的 getrusage 数据与完整异常；不伪称原方法通过。
- Native EXPLAIN 的 READ_PARQUET 名称按 DuckDB 1.5.4 实际输出记录；同义名称修正不改算法。证据工具曾因 launcher rc 与 engine rc 混用、计划节点别名、重复运行 SQL 日志未先截断而停止，修正后重跑，最终逐项断言通过。初次生成的 scratch_peak=0 未采样表述已在证据末尾明确更正，并另跑生成阶段采样，未沿用该零值作为测量证据。
- _write_v2_inputs 在工单建议的 duplicate_rows/bounds 之外增加默认 None 的 conflict 测试参数，保证冲突在 parquet/done/receipt 生成前注入，既有调用行为不变。
- 新测试先红在生产脚本与基线逐字相同的状态执行；随后冻结双格式基线收据，才修改生产文件。最终报告与资源摘要引用的是纠正测量工具后的成功运行。
- 合并与真实案卷不在本次授权施工范围内。调度方合并后必须用最终合并版 replay_duck.py --only-addrs 重建 QUQ 案卷收据，再执行 stage2_closeout check 与发布闸；旧收据不得沿用、不得手改 producer sha。施工夹具不替代案卷重跑。

复现用临时根目录：`/private/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/w1-zw0vnb4p`。顺序执行 W1_fixture_tools.py 的 baseline / candidate / supplement / edges / varint_merge 模式可生成证据（全新临时根须先按 §0.6 放置基线副本；重跑生成与小夹具应使用新的临时根）。最终磁盘可用 67,584,000,000 B。

禁读路径披露：未读取 ~/.codex/（包括 memories），未读取主仓库、Desktop、Documents、Volumes、blind-reviews、references/attic.md 或既有 .staging_*、.hypothesis，也未主动打开历史 maintenance 文件作为施工上下文。但按 §0.9 点名运行的 changelog_lint 内部读取了 archive/CHANGELOG-archive.md；test_repair_batch_c 的测试流程引用并运行历史 maintenance/repair-20260814-batch2/ 内 importer。这里如实披露测试内部读取，不将其表述为“所有禁读路径均零读取”。
