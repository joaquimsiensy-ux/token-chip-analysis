# 盲审 F07：FAIL

发现 **1 项 minor**：存量迁移命令缺少必填参数，照报告执行无法生成新收据。生产代码与工单指定改法逐字节一致，未发现其他本段缺陷。完整回归受只读沙箱阻断，未认定本轮全绿。

审查范围为 `0b0a5f6..a201c63`。开工、收尾 HEAD 均为 `a8928e1`，工作树均干净；整个 `scripts/` 与目标提交一致。报告全文已打印到 stdout，未写文件。

**F07-B1-01｜minor｜存量迁移命令遗漏 `--out-dir`**

位置：[F07_done.md:470](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918-p0-f04-f07/F07_done.md:470)；同一遗漏见 [workorder_F07.md:24](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918-p0-f04-f07/workorder_F07.md:24)。

事实：报告给出的完整迁移命令只有 `--channels` 和两次 `--only-addrs`，但 [replay_duck.py:638](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/evm/replay_duck.py:638) 明确设置：

```python
ap.add_argument("--out-dir", required=True)
```

本轮实际执行：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/evm/replay_duck.py --channels channels.json --only-addrs peaks_daily_out/needs_block_precision.json --only-addrs peaks_daily_out/trigger_days.json
```

退出码 **2**，错误为：

```text
replay_duck.py: error: the following arguments are required: --out-dir
```

这是参数解析失败，尚未读取案卷或生成产物，与沙箱无关。本段开始拒收旧 followup，但所附迁移命令无法执行。

修法：报告和工单补上 `--out-dir <补算工作目录>`，保留两次 `--only-addrs`；说明工作目录用于通道预检和临时数据，followup 仍落在首个名单所在目录。

归因：工单原有遗漏被本提交新增报告沿用，属于迁移说明缺陷，不是本次 Python 实现回归。

**工单不变量与原始反例**

以下发布闸行号均指 `scripts/report/audit_release_gate.py` 的目标提交。

| 核查项 | 结论与代码证据 |
|---|---|
| §2.1 三件生成产物任一定位 | 闭合。`:1077` 定义 summary/needs/followup；`:1087` 单次遍历；`:1091`、`:1095` 排除隐藏、历史和符号链接路径；`:1101` 按目录去重。 |
| 无产物、多个目录、缺 summary | 闭合。`:1114` 保留无产物 return；`:1116` 拒绝多个目录；`:1123` 拒绝缺失或链接 summary。trigger 不在定位集合中，合法原始输入布局保留。 |
| §2.2 四字段绑定 | 闭合。`:1206` 校验 producer 路径及当前引擎 SHA；`:1212` 查找案内唯一 channels 常规文件并核 SHA；`:1222` 限定 HUGEINT/VARINT；`:1225` 对比 count 与 addresses 长度。错误继续累加。 |
| 既有保护段 | 保留。`:1127` 起的 summary/trigger/needs 校验、`:1188` 的地址并集、`:1227` 起的 inputs/addresses 校验，与基线对应片段一致；契约针未改。 |
| §2.3 用例 | 落实。`scripts/tests/test_audit_release_gate.py:995` 补全夹具；`:1134` 起增加 14–22；`:1046` 按授权调整用例 6 文案；`:1249` 改为动态总数。 |

工单头部两类反例均闭合：

- **F07-rename**：summary 单独改名后，仍由 needs/followup 定位，进入“缺 summary”拒绝。
- **F07-selfreport**：同 schema、仅 engine/inputs/addresses 的收据，命中 producer、channels、value_type、count 错误。

以上经基线静态推演及局部内存对照核验；未实跑原始 `build_html --mode analysis-new` 端到端反例。

**六视角**

| 视角 | 结论 |
|---|---|
| ① 字段来源 | 本段通过。`replay_duck.py:401` 起读取真实 channels 和自身文件计算 SHA，`:405` 写出四字段；消费侧重新计算哈希和地址条数。完整伪造收据仍属 §4 明示残余。 |
| ② 失败分支 | 本段通过。缺件、重复目录、绑定失败均进入 errors；非 dict addresses 由发布闸 `:1237` 拒绝，没有新增 warning 后放行分支。 |
| ③ 存量迁移 | 存在上述 minor。双名单并集、首个输入决定落点分别与 `replay_duck.py:334`、`:411` 一致，但命令漏必填参数。 |
| ④ 同族调用面 | 通过。检索 `scripts/` 未见旧 finder 残留调用或另一份峰值消费实现。`build_html.py:433`、`stage2_closeout.py:563` 共用发布闸，发布闸 `:1852` 无条件调用本检查。 |
| ⑤ producer/consumer 双向一致 | 字段与格式一致；CLI 迁移说明遗漏计入上述同一问题。`peaks_daily.py:172`、`:202`、`:211` 的产物与消费约定一致。引擎等价测试没有逐项断言四个绑定字段，也未把真实收据送入完整发布闸，不能将其 PASS 尾行视为该完整链路的证明。 |
| ⑥ 检查点可绕性 | 工单范围内闭合。最小手写收据、summary 改名、只剩 followup、绑定字段清空均被拒。正式 HTML 将闸错误加入 warns，`build_html.py:489` 在写文件前退出。完整伪造、三件全部隐藏、channels 内容不重验，按 §4 保留，不另报缺陷。 |

**测试真实性**

已用 `git show 0b0a5f6:scripts/report/audit_release_gate.py` 核对基线。RED 记录的生产 SHA256 与基线 blob 精确一致；测试 SHA256 与 `a201c63` 测试文件精确一致。取证命令提取实际 AST 用例，未替换 gate。

- **14、20**：基线仅搜索 summary，零命中即 return，故缺 summary 断言得到 `AssertionError: []`。
- **15–19**：基线未消费新增字段，相应破坏不会进入 errors；五个 RED 与代码行为一致。
- **21、22**：基线本就忽略单独的原始 trigger，GREEN→GREEN 合理。
- **既有 1–13**：AST 比对仅发现用例 6 的授权文案调整，未弱化断言。新增七个负例均要求命中特定错误，能区分改前改后。

独立局部内存对照得到：基线原有 **13/13**、修改后 **22/22**；新 14–20 对基线全部 RED，21/22 为 GREEN。另核了空字段、只有 followup、channels 重名及隐藏副本、VARINT。

该模拟替换了文件系统及 JSON 读取，并将 `build_case/gate.run` 收窄到日级峰值检查，**不能替代完整测试**。辅助探针首次误期待空 inputs 的形状错误，已按实际契约更正为哈希绑定错误；仓库测试未修改。

**回归与执行边界**

`F07_done.md:351` 起具备全部七项命令、结果尾行及 exit_code=0；报告内完整 diff 与目标提交机械比对一致。施工记录与本轮执行分列如下：

| §0.8 检查 | done 所载结果 | 本轮独立执行 |
|---|---|---|
| `test_audit_release_gate.py` | PASS，十一类契约全过 | 尝试执行，退出 1；`:480` 首个临时目录创建失败，未执行断言。 |
| `test_engine_equivalence.py` | R09 补算、三引擎等价 PASS | 未实跑，需要可写临时产物。 |
| `test_peaks_daily.py` | PASS：0 项失败 | 未实跑，同上。 |
| `test_batch15_three_ledgers_frozen.py` | PASS，12/12 | 未实跑，同上。 |
| `test_repair_batch_d.py` | BATCH D 全部通过 | 未实跑，同上。 |
| `test_stage2_closeout.py` | 28/28 PASS | 未实跑，同上。 |
| `invariant_scan.py` | PASS，81/118/65/61/61，exceptions=0 | **实跑 PASS，退出 0，计数一致。** |

沙箱错误为 `FileNotFoundError: [Errno 2] No usable temporary directory found ...`，不计入缺陷。未运行 `run_all.py`。

**工单符合度与纪律**

`scripts/` diff 仅两份白名单文件，**148 行新增、18 行删除**；全提交另增两份白名单施工证据。生产文件按工单三个代码块及指定 docstring 从基线重建后逐字节相等，包含注释和空白，未发现工单外生产改动。

`invariant_manifest.json` 无缺项且未改；两份 EVM producer、contract manifest 未改。`references/`、`SKILL.md`、`commands-staging/` 的提交 diff 为空；`git diff --check` 通过。

本轮离线、只读，未改文件、未 commit。平台启动时自动注入了记忆摘要；本轮未读取 `~/.codex/` 文件或采用历史结论，未主动读取禁读路径。按任务读取六视角规范，指定 scanner 按原程序执行；未审查其他段。