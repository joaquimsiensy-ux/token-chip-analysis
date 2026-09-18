# 工单F07复核：退回

发现 **1 项需修订：定位范围的文字说明与拟改代码矛盾**。r1 四条退回的功能修订均已闭合。未发现本方案必然使既有 `run_all` 用例新增失败的证据；完整测试受只读沙箱阻断，不能宣称全绿。

**F07-R2-01｜§4 错把“只剩 followup”列为可绕过，标题仍沿用“四件”**

工单位置：[workorder_F07.md:139](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918-p0-f04-f07/workorder_F07.md:139)，以及第 1、27 行标题；对照 §1.3 和 §2.1 第 32–57、63–76 行。

事实，`grep -n -F` 核得：

```text
33:                        "block_precision_followup.json")
139:- 改名 `needs_block_precision.json`＋`peaks_summary.json` 两件同时改名（只剩 followup 或全部改名）仍可绕过定位：全部改名＝等价于"没跑 peaks_daily"，属口径选择未冻结的同一残余。
```

拟改代码明确把 followup 作为定位依据，随后检查 summary 是否存在。使用工单代码进行局部内存模拟：

```text
案内只有 block_precision_followup.json：
基线：[]
拟改后：峰值产物目录 . 缺 peaks_summary.json（needs/trigger/followup 在场而 summary 缺席＝改名或残缺产物，拒）
```

因此，“只剩 followup 仍可绕过”不成立。第 1、27 行“四件任一”也与已经删除 trigger_days 的三件集合不一致。r1 对 §4 的概括通过遗漏了这一矛盾，本轮据上述直接证据修正。

修订建议：§4 改为“summary、needs、followup 三件生成产物均不存在或均改名时，仍无法区分未跑 peaks_daily 与隐藏全部产物；只剩 followup 时会因缺 summary 被拒”。第 1、27 行同步改成“三件生成产物任一”。无需因此扩大生产修复范围。

**r1 四项处置核验**

| r1 项 | v2 处置与核验 |
|---|---|
| R1-01 原始 trigger 被误判 | §1.3、`PEAKS_DAILY_PRODUCTS` 已移除 trigger_days；14/20 拦住 summary 缺席且 needs 在场；21/22 保留原始 trigger 的合法布局。局部模拟符合预期。 |
| R1-02 迁移漏触发日候选 | §1.4 双 `--only-addrs` 与 `replay_duck.py:334–368` 的并集、输入哈希记录一致；第 411 行确由首个输入决定收据落点。 |
| R1-03 成本低估 | §1.4 已说明全量通道校验、读取、去重及临时空间成本；与 `:653/:666/:685`、`build_events:160–179` 一致。 |
| R1-04 F12 归属错误 | §0.8 要求本段定向清单全部 PASS；例外准确指向 `test_stage2_reseal.py::dry_run_touches_nothing`（`:516`），交由调度方全套验收。 |

**实际核过的其余项目**

| 核查项 | 结果 |
|---|---|
| 锚点 | **34 项机械检查通过**，含 33 项 `grep -n -F` 及 `^REPO`。`return hits` 限定 `:1077–1094`；`inputs` 限定 `check_daily_peaks`。`REPO=:15`，“多份”断言 `:1041`。 |
| 基线行号 | 指定 audit `:1074/:1077–1094/:1097–1113/:1132/:1147/:1179–1192/:1201–1204`，replay `:334–368/:405–411`，测试 `:977–999/:1001–1014/:1129–1154`，均与 `311e6c4` 相同。 |
| 定位过滤 | 对保留的三件文件，隐藏组件、`_history`、常规文件和符号链接过滤保持原语义；trigger 被排除是有意修订。`channels.json` 本身不构成峰值产物目录。 |
| 遍历成本 | 当前 Python 3.14.6、scripts 树计数：v1 四次 rglob 为 **120 次 scandir**，v2 单次 `rglob("*.json")` 为 **60 次**。“一次 rglob”不等于每目录仅一次 scandir；未实测大案耗时。 |
| channels 过滤 | `.duck_tmp`、`_history` 下副本被路径组件规则排除；rglob 默认不递归目录符号链接，文件符号链接也被显式排除。模拟“案根 channels＋隐藏/历史副本＋channels_preflight”得到 `[]`；增加第二份可见 channels 后得到命中 2 个的拒绝。 |
| channels 夹具 | R09 的 `build_case` 构造链没有既有 `channels.json`，新增文件不冲突。`identity_gate_fixture.py:27` 的同名文件属于另一个夹具链。 |
| producer 绑定 | `replay_duck.py:403–410` 读取自身 SHA 并写 producer/channels/value_type/count。`test_engine_equivalence.py:246–256` 调用该仓库脚本；现有断言未直接逐项核这四字段，本轮未实跑引擎测试。 |
| count / addresses | 非 dict 时跳过 count 比较，随后 `:1201–1204` 拒绝。局部模拟得到“缺 addresses 映射”，不会因此放行。 |
| 其他回归夹具 | `test_repair_batch_d`、`test_batch15_three_ledgers_frozen`、`test_stage2_closeout` 及核到的共享构造链没有自带三件 peaks 生成产物。未发现新增定位规则会改变它们的既有正例。 |
| §0.4 保护段 | 删除 `:1113` 的 pd 赋值属于 §2.1 明示例外；其余 summary/trigger/needs、inputs/addresses 校验保留。 |
| invariant 登记 | `:75` 是 producer，`:479` 是 consumer，均已登记。基线 scanner **实跑 PASS**；拟改文本的单文件扫描结果与基线完全相同，无需增补登记。`minimum_counts` 保持 **81 / 118 / 65 / 61 / 61**。 |
| §1.1 字节数 | 仅按 stat 元数据核得 SKILL.md **8021**、references **930061**、commands-staging **8798**，一致。 |

按要求检索 `scripts/`、`references/` 并排除 `attic.md` 后，固定文件名的生产者、消费者如下：

| 文件名 | 生产者 | 消费者 |
|---|---|---|
| `needs_block_precision.json` | `peaks_daily.py:172` | `replay_duck.py:334–368`；`audit_release_gate.py:1144–1200` |
| `trigger_days.json` | `peaks_daily.py:202` | `replay_duck.py:334–368`；`audit_release_gate.py:1127–1200`；另有 `peaks_daily.py:91/:178` 的任意路径原始输入入口 |
| `block_precision_followup.json` | `replay_duck.py:411–415` | `audit_release_gate.py:1179–1229` |

其余命中为三个相关测试、`contract_manifest.json` 及两份现行 references 文档；未发现其他生产脚本写出上述固定文件名。原始 trigger 文件名不能专属于产物目录，v2 的排除方向正确。

**RED/GREEN 与完整正例边界**

实际执行：

```text
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/test_audit_release_gate.py
exit_code=1
test_audit_release_gate.py:480 → tempfile.TemporaryDirectory()
FileNotFoundError: [Errno 2] No usable temporary directory found ...
```

这是沙箱限制，尚未执行测试断言。

另将原 `check_daily_peaks`、原 R09 用例及工单拟改代码放入内存文件系统模拟；其中 `build_case` 和 `gate.run` 被收窄到日级峰值检查，不能替代完整测试：

| 用例 | 基线 | 拟改后 |
|---|---|---|
| 既有 1–13 | 13/13 通过 | 13/13 通过；用例 6 按工单更新文案断言 |
| 新 14–20 | 均未命中期望错误，RED；`errors=[]` | 均命中指定错误，GREEN |
| 新 21/22 | GREEN，`errors=[]` | GREEN，`errors=[]` |

4 的少址、5 的 needs 哈希、10 的顶层/inputs 形状、11 的地址项、12 的大小写归一、13 的非法 peak 根因均保留，未与新增字段冲突。

`build_case(historical=False)` 在完整 `gate.run` 下的**已知预期错误集合为 `[]`**；现有 [test_repair_batch_d.py:809](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_repair_batch_d.py:809) 明确用 `assert not gate.run(root, report)` 约束这一正例。静态核对未发现 21/22 会被其他已知错误文案误伤；完整闸结果本轮未实测。用例 22 落地时还需创建 `data` 父目录，现有 `write_json:36–37` 不会自动创建目录。

**APU 实案与复核边界**

APU 0914 案根 channels 唯一、另有 channels_preflight，属于工单第 4 行提供的调度方核验事实；不同 basename 不会互相命中。`D_done.md:645` 只记载施工方未执行 APU 本机对照，没有可供本轮核查的绝对路径。遵守 Documents 禁读要求，本轮未独立检查 APU 0801/0914 案盘，不将其标作本轮实测。

开工 HEAD=`4278857`，收尾 HEAD=`92ff4fe`；开工存在并发 F06 两份脚本改动及两份未跟踪证据，收尾工作树干净。**九份复核输入 SHA-256 复采一致**；F07 目标代码相对 `311e6c4` 无差异，并发变更不归入本次复核。

报告全文已打印到 stdout，未写报告文件；本轮离线、未改文件、未 commit，未运行 `run_all.py`，工具未访问禁读路径。