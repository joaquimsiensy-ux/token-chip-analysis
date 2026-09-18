# 工单F07复核：退回

发现 **4 项需修订**。锚点核验通过；APU channels 的实际位置和唯一性尚未核实，不计入这 4 项。报告全文已打印到 stdout，未写文件。

**F07-R1-01｜合法 trigger_days 输入会被误认作产物目录**

工单位置：[§1.3、§2.1](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918-p0-f04-f07/workorder_F07.md:21)，重点为第 31–54、60–73 行。

事实：[peaks_daily.py:91](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/evm/peaks_daily.py:91) 接受任意路径的 `--trigger-days` JSON；第 178–186 行读取原始清单，第 202 行另写输出。因此，以下布局符合现行接口：

```text
--trigger-days data/trigger_days.json --out-dir data/peaks_daily
```

拟改规则会把 `data` 和 `data/peaks_daily` 都认作产物根。使用原函数与工单代码块进行内存模拟，得到：

```text
原始触发日清单 + 完整峰值产物：
  基线：[]
  拟改后：案内出现多个峰值产物目录（data, data/peaks_daily）

只有原始触发日清单：
  基线：[]
  拟改后：缺 peaks_summary.json

只有 channels.json：
  两者均：[]
```

修订建议：区分原始输入与生成产物，补充上述同名布局的兼容性用例。若坚持将文件名全部保留给产物，须明确新增命名限制及输入清单迁移办法，不能只要求“清理陈旧目录”。

**F07-R1-02｜迁移说明遗漏触发日活跃候选**

工单位置：[§1.4，第 22 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918-p0-f04-f07/workorder_F07.md:22)：`只对 needs 并集地址`。

事实，`grep -n -F` 核得：

```text
scripts/report/audit_release_gate.py:1175:    union |= td_union
scripts/report/audit_release_gate.py:1199:    if td_union and bound.get("trigger_days.json") != trig_sha:
```

实际义务是 **needs 各档地址 ∪ 触发日活跃候选**，并绑定相应 trigger 哈希。needs 为空、触发日候选非空时，只传 needs 会被引擎的空并集检查拒绝；needs 非空时也可能漏掉触发日专有地址。

修订建议：明确同时传入同一产物目录中的：

```text
--only-addrs needs_block_precision.json --only-addrs trigger_days.json
```

并说明首个输入决定收据落点，依据为 `replay_duck.py:411`。

**F07-R1-03｜“成本小”遗漏全量通道处理成本**

工单位置：§1.4，第 22 行。

事实，`grep -n -F` 核得：

```text
scripts/evm/replay_duck.py:653:    chans = preflight_channels(a.channels, a.out_dir)
scripts/evm/replay_duck.py:666:    rej = build_events(con, chans)
scripts/evm/replay_duck.py:685:        raise SystemExit(followup_peaks(con, a, vt))
```

`build_events:160–179` 先物化全部通道的 `raw_rows`，再去重生成 `events`；名单过滤发生在后面的 `followup_peaks` 中。地址少不能直接推出重跑成本小，尤其本计划要求引擎哈希变化后重跑。

修订建议：改为“限制峰值聚合地址范围，但仍执行全量通道校验、读取和去重；耗时与临时空间按案量评估”。

**F07-R1-04｜F12 例外挂错测试文件**

工单位置：[§0.8，第 15 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918-p0-f04-f07/workorder_F07.md:15)。

事实：

```text
grep -n -F 'def dry_run_touches_nothing(cases):' scripts/tests/test_stage2_reseal.py
516:def dry_run_touches_nothing(cases):
```

`test_stage2_closeout.py` 中没有该用例。`run_all.py:209–210` 也分别登记了这两个测试文件。

修订建议：删除挂在 `test_stage2_closeout.py` 后的例外，要求本段定向清单全部 PASS；将 F12 准确标为 `test_stage2_reseal.py::dry_run_touches_nothing`，交由调度方全套验收处理。

**其余实际核过的项目**

| 核查项 | 结果 |
|---|---|
| 锚点、行号 | 51 项机械检查通过，覆盖指定 audit、replay、测试锚点及函数边界。`:1094 return hits` 按原函数区间核验；`:1192 inputs` 限定 `check_daily_peaks`。`REPO` 位于测试第 15 行，用例 6 的旧文案断言位于第 1041 行。 |
| 定位过滤 | `_find_peaks_dirs` 的隐藏组件、`_history`、文件及祖先符号链接过滤与原函数一致。 |
| 四次 rglob | 确实遍历四遍。本仓库 scripts 树只读计数为 **30→120 次 scandir**；消费 followup 时 channels 查询还会增加一次遍历。建议改成单次遍历；没有大案实测，不将耗时推断单独列为退回项。 |
| channels 夹具 | R09 所用 `build_case` 链未发现既有 `channels.json` 冲突。`identity_gate_fixture.py:27` 虽使用同名文件，但属于 stage2 的独立夹具，没有与本组 R09 夹具叠加。 |
| producer 绑定 | `replay_duck.py:401–410` 确实读取当前自身 SHA，并写出 producer、channels、value_type、count。引擎等价测试调用该仓库脚本；但现有断言没有直接核验这四个字段，本轮未实跑引擎测试。 |
| count / addresses | 非 dict 时跳过 count 比较，随后 `:1201–1204` 仍明确拒绝 addresses。内存模拟得到“缺 addresses 映射”，不会因此放行。 |
| 其他回归夹具 | 三个指定测试及核到的共享构造链，没有自带这四件 peaks 产物的夹具。未发现新增定位规则会改变这些既有夹具的判定。 |
| §0.4、§4 | 删除 `:1113` 属于 §2.1 明示例外；其余受保护校验段保留。完整手写收据、channels 内容不验、峰值选型未冻结，均已明示留待后续，本次不扩修。 |
| invariant 登记 | `:75` 是 producer，`:479` 是 consumer，均已登记。基线 scanner 实跑 PASS；拟改文本的单文件扫描清单不变，无需增补登记或调整 minimum_counts。 |
| minimum_counts | 保持 **81 / 118 / 65 / 61 / 61**。 |
| 文档大小 | 仅用 stat 元数据核得：SKILL.md **8021**、references **930061**、commands-staging **8798**，与 §1.1 一致。 |

已按指定 `grep -rn` 检索三文件名并排除禁读项，生产者和消费者如下：

| 文件名 | 生产者 | 消费者 |
|---|---|---|
| `needs_block_precision.json` | `peaks_daily.py:172` | `replay_duck.py:334–368`、`audit_release_gate.py:1144–1200` |
| `trigger_days.json` | `peaks_daily.py:202` | `replay_duck.py:334–368`、`audit_release_gate.py:1127–1200`；另有任意命名的原始输入入口 |
| `block_precision_followup.json` | `replay_duck.py:411–415` | `audit_release_gate.py:1179–1229` |

其余源码命中为三个相关测试、`contract_manifest.json`、`references/playbook-entity-cluster-tiering.md` 和 `references/data-pipeline-evm-recon.md`。未发现其他生产脚本写出这三个固定文件名。

**测试结果及边界**

实际执行：

```text
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/test_audit_release_gate.py
```

退出 1，在第 480 行创建首个临时目录时失败：

```text
FileNotFoundError: [Errno 2] No usable temporary directory found ...
```

这是沙箱限制，尚未执行测试断言。

另用原函数、原 R09 用例和工单拟改代码进行了内存模拟；文件系统为虚拟实现，`build_case`、`gate.run` 被收窄为 `check_daily_peaks`，**不能替代完整测试**：

- 既有 **1–13**：基线与拟改后均通过。4 的少址、5 的 needs 哈希、10 的顶层及 inputs 形状、11 的地址项、12 的大小写归一、13 的非法 peak 根因均保留；6 按工单更新断言。
- 新 **14–20**：基线均为 `AssertionError: []`，拟改后均命中指定错误，符合 RED→GREEN。

未运行 `run_all.py`。静态排查及局部模拟未发现 F07 会使现有用例新增失败；不能据此宣称全套通过。

APU 实案仍待核实：指定 `D_done.md:645` 仅记载本机对照未由施工方执行，没有给出可用的 APU 绝对路径或 channels 唯一性证据。本次遵守禁读边界，未递归检查 Documents 案卷，因此不声称其 channels 在案内或唯一。

本轮离线、未改文件。开工 HEAD 为 `4931098`，工作树干净，scripts 与 `311e6c4` 无差异。收尾采样时 HEAD 已因并发工作变为 `1e5c7e0`，出现 F06 生产及测试改动、F06 证据文件和 F04 复核文件。**F07 工单、发布闸、replay 引擎、R09 测试、invariant manifest 五份复核输入的 SHA-256 均与开工一致**；并发改动不归入本次复核。