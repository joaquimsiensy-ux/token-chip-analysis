# 盲审 F02：PASS

审对象：`922d6b2c66d5941ea6ce886ee26abcc1fd9b147e`，施工基线：`830ce9f8323b`。

按指定规则，a/b/c 全过，d 无真实 FAIL。指定测试 **1 项 PASS、8 项 SANDBOX-BLOCKED**，阻断项由调度方本机补验。完整报告已打印到 stdout。

**a）三条终点链路已独立复现**

自行构造 total=1000、e1 current=100、带合法峰值锚点的夹具。仅将夹具文件读写承接到内存，实际执行生产模块和校验逻辑，未复用新增测试断言。

| 分支 | 实测结果 |
|---|---|
| 声明贯通 | 无声明时 100/1000=10%，空 flow 的 `errors=[]`；声明流通量 400 后，生成两个新字段，100/400=25%，报 `WORKORDER BLOCK: flow.eligible_entity_ids: 包含下限 ['e1'] != []`。正常 facts 发布重算通过，补齐 e1 图后选材通过。 |
| 扁平键 | 明确抛出 `ValueError: facts_inputs.circulating_supply_raw 键名错位——流通量须写成 circulating_supply: {raw, asof, source}`。 |
| 手改 facts | 声明 400、facts 改为 401，发布闸报 `facts.token 与三账重算值不一致`。修改来源、增加 token 键、无声明手补 raw，也分别被拒。 |

对应位置：[facts_gate.py:383](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/facts_gate.py:383)、[stage2_closeout.py:202](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/stage2_closeout.py:202)、[audit_release_gate.py:1569](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/audit_release_gate.py:1569)。

**b）工单 v2 一致性通过**

解析块紧跟 `dual_basis` 的 raise；两个输入同时非法时，先报 dual_basis 错误。六类非法输入在 formal/exploration 路径均实际触发 `ValueError`：

| 类别／实测输入 | 拒绝文案 |
|---|---|
| 非 dict：`"400"` | `facts_inputs.circulating_supply 须为对象 {raw, asof, source}` |
| raw 非正整数：`400.5`、`True`、`"-1"`、`"0"` | 浮点/bool：`invalid literal for int()`；负数：`facts_inputs.circulating_supply.raw 不得为负: '-1'`；零：`facts_inputs.circulating_supply.raw 0 须在 (0, total_supply_raw=1000] 内` |
| raw > total：`"1001"` | `facts_inputs.circulating_supply.raw 1001 须在 (0, total_supply_raw=1000] 内` |
| 非严格 ISO：`"20260103"`、`"2026-02-30"` | `facts_inputs.circulating_supply.asof '<输入>' 非 YYYY-MM-DD` |
| source 空：`" "` | `facts_inputs.circulating_supply.source 须为非空口径说明（如 'CoinGecko circulating 2026-09-14'）` |
| 扁平键 | `facts_inputs.circulating_supply_raw 键名错位——流通量须写成 circulating_supply: {raw, asof, source}` |

另已核实：

- token 恰好新增两键；无声明时 token 序列化字节与基线相同。完整 facts 仅移除 `provenance.producer.sha256` 后，序列化字节相同；基线旧 facts 经 HEAD 发布闸仍通过。
- 实际 `build_main` 在内存文件 I/O 下重复执行，有／无声明均返回 0，输出字节相同。
- 新 NOTE 实际包含 `流通量 400（口径 independent F02 circulating，2026-01-03）`；无声明旧 NOTE 保留；只有 raw、无 source 的旧消费者输入仍正常返回。
- 工单允许的 `"+400"`、`" 400 "`、整数 `400` 均归一化为 `"400"`。
- 逐字比较确认 `Facts`、`gate_check`、override/峰值/证据校验、`build_main`、provenance 写出和公共 closeout 夹具未改。closeout 生产代码仅增加两行 NOTE，阈值、返回结构和原有 BLOCK 文案未改。

**c）白名单与字节数通过**

实跑：

```text
git diff --stat 830ce9f8323b HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md
```

结果：

```text
 scripts/report/facts_gate.py          | 30 ++++++++++++++++++++++++++-
 scripts/report/stage2_closeout.py     |  2 ++
 scripts/tests/test_report_facts.py    | 38 ++++++++++++++++++++++++++++++++++-
 scripts/tests/test_stage2_closeout.py | 25 ++++++++++++++++++++++-
 4 files changed, 92 insertions(+), 3 deletions(-)
```

仅按元数据统计，均符合要求且对应路径无基线差异：

| 路径 | 字节数 |
|---|---:|
| `SKILL.md` | 8021 |
| `references/**/*.md`，42 文件 | 930076 |
| `commands-staging/*.md`，4 文件 | 8798 |

审查结束时 scripts 工作树与 HEAD 一致，HEAD 未变化。

**d）指定命令与实际尾行**

相同尾行以 E1 引用，原文列于表后。

| 实跑命令 | 结果／尾行 |
|---|---|
| `python3 -B scripts/tests/test_report_facts.py` | SANDBOX-BLOCKED，退出 1；E2 |
| `python3 -B scripts/tests/test_stage2_closeout.py` | SANDBOX-BLOCKED，退出 1；E1 |
| `python3 -B scripts/tests/test_audit_release_gate.py` | SANDBOX-BLOCKED，退出 1；E1 |
| `python3 -B scripts/tests/test_state_from_facts.py` | SANDBOX-BLOCKED，退出 1；E3，异常链含 E1 |
| `python3 -B scripts/tests/test_build_html.py` | SANDBOX-BLOCKED，退出 1；E1 |
| `python3 -B scripts/tests/test_figures_from_facts.py` | SANDBOX-BLOCKED，退出 1；E1 |
| `python3 -B scripts/tests/test_a4_gate.py` | SANDBOX-BLOCKED，退出 1；E1 |
| `python3 -B scripts/tests/test_review_20260804_p105.py` | SANDBOX-BLOCKED，退出 1；E1 |
| `python3 -B scripts/tests/invariant_scan.py` | PASS，退出 0；尾行如下 |

E1：

```text
FileNotFoundError: [Errno 2] No usable temporary directory found in ['/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/', '/tmp', '/var/tmp', '/usr/tmp', '/Users/uravvv/.claude/skills/token-chip-analysis']
```

E2：

```text
PermissionError: [Errno 1] Operation not permitted: '/private/tmp/r07-facts-8t5amniq'
```

E2 来自测试显式指定 `/private/tmp` 后创建夹具目录失败，同属只读沙箱阻断，已单独保留实际错误。

E3：

```text
OSError: Matplotlib requires access to a writable cache directory, but there was an issue with the default path ({configdir}), and a temporary directory could not be created; set the MPLCONFIGDIR environment variable to a writable directory
```

invariant_scan 尾行：

```text
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0
```

**e）新增用例基线 RED 已核实**

用 `git show 830ce9f8323b:scripts/report/facts_gate.py` 及对应 closeout 基线源码在内存加载；提取新增用例原始函数和断言逐例执行，仅适配夹具文件 I/O。

| 新增用例 | 基线 | HEAD |
|---|---|---|
| 22 声明贯通 | RED：`KeyError 'circulating_supply_raw'` | GREEN |
| 23 raw=2000 | RED：AssertionError“应拒绝” | GREEN |
| 23 raw=0 | RED：AssertionError“应拒绝” | GREEN |
| 23 asof=20260103 | RED：AssertionError“应拒绝” | GREEN |
| 23 source 空 | RED：AssertionError“应拒绝” | GREEN |
| 23 非对象 | RED：AssertionError“应拒绝” | GREEN |
| 23 扁平键 | RED：AssertionError“应拒绝” | GREEN |
| 24 无声明手补 token | GREEN | GREEN |
| `circulating_supply_producer_to_consumer` | 前半通过；后半在 `test_stage2_closeout.py:692` 因 KeyError 变 RED | GREEN |

三段 `python3 -B -c` 内存审查脚本均退出 0，尾行：

```text
PASS: independently reproduced A1/A2/A3 and B runtime checks; no fixture/test assertions reused; no disk writes
PASS: exact new assertions: 22 + six 23 variants + closeout = 8 RED->GREEN; 24 = GREEN->GREEN; memory-only fixture I/O
PASS: protected code unchanged; reviewed scripts match current HEAD 922d6b2c66d5941ea6ce886ee26abcc1fd9b147e
```

全程离线、未改文件、未 commit、未使用 stash。未读取 `~/.codex/`、memories、两份施工方自述或其他禁读内容；文档体积核对仅用元数据。maintenance 仅按任务读取工单和裁定，未纳入代码审查。未运行 `test_stage2_reseal.py`。
