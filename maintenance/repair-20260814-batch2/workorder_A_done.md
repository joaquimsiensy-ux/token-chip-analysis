# 工单 A（F-10）完工摘要

施工状态：完成。全程未执行 `git add`、`git commit`、`git push`、`git checkout` 或其他 git 写命令。

## 1. 同族复核

施工首步按工单原命令执行：

```text
rg -l "approved_tolerance_bps|observed_diff_bps|tolerance-waiver" --glob '!maintenance/**' --glob '!archive/**' --glob '!blind-reviews/**'
```

命中 8 个文件：工单已知 7 个文件之外，新增命中 `scripts/report/handoff_manifest.py`。复核结论：该文件仅在 flip 裁决收据注释中类比 `tolerance-waiver` 的设计边界，不生产、不消费、不校验 waiver/approval，故本单不改。`CHANGELOG.md` 命中为 6.39.6 历史台账正文，本单不倒改历史记录。

NaN 横扫确认 waiver/approval 的四个解析点已全部使用 `parse_constant=_reject_constant`：

- 生产侧：waiver、over-cap approval。
- 消费侧：waiver、over-cap approval。

其余 JSON 解析面按工单要求只登记，见“发现未修”。

## 2. 改动文件清单

1. `scripts/lib/supply_truth_gate.py`
   - 新增同源常量 `WAIVER_TOLERANCE_BPS_CAP = 100` 与 `over-cap-approval/v1` 生产侧校验。
   - waiver/approval JSON 拒绝 `NaN`、`Infinity`、`-Infinity`；数值字段要求有限、非负且类型正确。
   - 按批准值、记录偏差、申请容差三值先判超顶；实算偏差产生后再做第四值复核。
   - approval 安全相对路径、普通文件、size、sha256 三验；request 字段、规范哈希、replay_stats 实物、文本、UTC 时间和有效期逐项闭合。
2. `scripts/report/shared_release_receipt.py`
   - 从生产侧导入 100bps 常量。
   - 独立实现 waiver/approval 严格解析、四值 max 判区和 request_sha256 重算，不信生产侧自报。
3. `scripts/tests/test_repair_batch_a.py`
   - 扩展既有夹具族到 25 项；补原反例、边界/错位组合、approval 变体、非有限数、失败分类及普通/超顶绿例。
   - 存量 `FIXTURE_DIFF_BPS=9900` 的合法绿例统一生成有效 approval；消费侧变异均重绑 waiver size/sha，确保命中内容校验层。
4. `scripts/tests/invariant_manifest.json`
   - 在生产侧与消费侧两处登记 `over-cap-approval/v1`。
5. `references/analyze-workflow.md`
   - 写入 ≤10／>10~100／>100 三段分级表、四值 max、approval 流程、Fable 会话内报告/批复要求及防伪边界。
6. `maintenance/repair-20260814-batch2/workorder_A_done.md`
   - 本完工记录。

## 3. 红→绿双跑证据

### 3.1 修前干净红

生产代码未改时运行 `python3 scripts/tests/test_repair_batch_a.py`：`rc=1`，结尾为 `BATCH A FAIL 7/25`。原有 17 项与新绿例通过；7 个新增负向测试失败，说明旧实现仍放行反例。

三条原反例的修前直接证据：

- `approved_tolerance_bps=100000`、无 approval：生产侧 `rc=0`，落 `PASS` 收据。
- `observed_diff_bps=100000`、无 approval：生产侧 `rc=0`，落 `PASS` 收据。
- waiver 原文 `observed_diff_bps=NaN`：生产侧 `rc=0`，落 `PASS` 收据。

首次测试编写实跑曾为 `9/25`：除上述真实缺口外，包含两个新夹具构造错误（删除必填字段后误建 approval、消费初始合法件误用变异低批准值）。修正夹具后、仍未改生产代码，再跑得到上述干净 `7/25`，故最终红证据不混入测试自身错误。

### 3.2 每个新增测试的双跑结果

| 测试 | 修前 | 修后 |
|---|---|---|
| `test_f10_original_approved_over_cap_without_approval` | FAIL：旧生产侧 `rc=0` PASS | PASS：生产 `rc=2`，消费拒绝 |
| `test_f10_original_observed_over_cap_without_approval` | FAIL：旧生产侧 `rc=0` PASS | PASS：生产 `rc=2`，消费拒绝 |
| `test_f10_original_nonfinite_waiver_numbers` | FAIL：旧生产侧放行 NaN | PASS：NaN/±Infinity 两侧均拒 |
| `test_f10_boundaries_and_four_value_max` | FAIL：100.0001 裸 waiver 被放行 | PASS：100 放行；100.0001/101 及三组错位组合两侧拒绝 |
| `test_f10_approval_receipt_variants_both_sides` | FAIL：错误 request_sha256 被放行 | PASS：哈希/换 request/空 nonce/过期/未来时间/空批复/错 replay/低区坏引用两侧拒绝 |
| `test_f10_approval_nonfinite_numbers_both_sides` | FAIL：approval NaN 被忽略 | PASS：approval NaN/±Infinity 两侧拒绝 |
| `test_f10_approval_failure_classification_and_broken_json` | FAIL：缺 approval 文件被忽略 | PASS：缺件和坏 JSON 为 exit 2；chmod 000 为 exit 1 |
| `test_f10_green_ordinary_and_valid_over_cap_both_sides` | PASS（防误伤基线） | PASS：≤100 九字段 waiver 与 >100 完整 approval 均两侧放行 |

修后目标套件：`rc=0`，`PASS batch A F-01/F-02 regressions 25/25`。

三条原反例修后显式复现：

```text
PRODUCER approved=100000: rc=2 receipt=False error=waiver 超过 100bps，缺少 over-cap approval 引用
PRODUCER observed=100000: rc=2 receipt=False error=waiver 超过 100bps，缺少 over-cap approval 引用
PRODUCER observed=NaN: rc=2 receipt=False error=tolerance waiver JSON 损坏: JSON 非有限数值 NaN 不允许
CONSUMER approved=100000: rejected=tolerance waiver above 100bps lacks over-cap approval
CONSUMER observed=100000: rejected=tolerance waiver above 100bps lacks over-cap approval
CONSUMER observed=NaN: rejected=tolerance waiver JSON invalid: JSON non-finite number NaN is forbidden
```

### 3.3 其他验证

- `python3 scripts/tests/invariant_scan.py`：PASS，`receipt_producers=54, receipt_consumers=65, transport_calls=62, atomic_writes=46, formal_entrypoints=58, exceptions=0`。
- `python3 scripts/tests/docs_lint.py --all`：PASS，58 个文档无断链、粗体配对完整。
- `git diff --check`：PASS。
- `scripts/tests/invariant_manifest.json` JSON 解析：PASS。
- 沙箱内首次 `python3 scripts/tests/run_all.py`：除两个需要绑定 `127.0.0.1` fixture server 的 vertical-slice 测试因 `socket.bind EPERM` 外，其余全部 PASS；这是环境能力限制，不是业务失败。
- 允许本地回环监听后重跑同一 `python3 scripts/tests/run_all.py`：`rc=0`，两项 vertical slice 均 PASS，最终输出“全部通过”。

## 4. 六视角①②自审

### ① 字段来源／信任根

- waiver 的 target 必须与本次 CLI 冻结 target 全等；消费侧再与正式收据 target 全等。
- replay_stats 的信任根是 waiver/approval 同目录内安全相对路径指向的普通文件，生产侧和消费侧各自重做 path/size/sha256 三验；approval request 必须解析到 waiver 已绑定的同一 replay_stats 实物。
- `approved_tolerance_bps`、`observed_diff_bps` 来自 waiver；`requested_tolerance_bps` 必须等于本次 CLI/正式收据容差；实际偏差由生产侧 `decide()` 生成，消费侧从绑定 replay_stats、收据 onchain supply 与同源 `decide()` 独立重算。
- approval request 的 target、observed、requested、replay_stats、reason 均与本次 waiver/运行逐项绑定；request_sha256 由生产侧重算，消费侧使用自己实现的规范化 JSON＋SHA-256 再独立重算，没有导入或信任生产侧哈希函数。
- `user_approval`、`reported_to_user`、`approved_by` 是用户流程文本证据，机器只验证非空；`user_decided_at_utc` 与 `expires_at_utc` 由运行时时钟约束，决定时间不得晚于 now+1d、有效期须晚于决定时间且验收时未过期。按工单要求没有添加 approved_by 长度下限，也没有添加 2026-01-01 时间下界。
- nonce 机器校验为非空；跨案全局唯一性没有可信全局登记可查，仍由收据生成流程负责。旧批复复用风险由 request 全等、request_sha256、replay 实物绑定和过期时间共同阻断。
- 结论：字段来源闭合到本次运行/实物；消费侧独立完成关键重算。设计只防工作流走捷径和误操作，不声称抵御持同用户权限的恶意进程。

### ② 失败分支／清理

- 缺 approval 引用、引用不存在、路径越界/软链/非普通文件、size/sha 错、JSON 损坏/非有限数、schema/request/hash/字段/时间不符：生产侧统一抛 `TolerancePolicyError`，经既有 `policy_reject` 返回 exit 2，并执行 `invalidate_stale_receipt`；消费侧统一抛 `ValueError`，fail-closed。
- approval/waiver 实物因权限等读不动：OSError 不降格为政策错，生产侧走检测自身失败 exit 1；chmod 000 回归已命中。
- `policy_reject` 的旧收据归档若失败，既有分支升格 exit 1；本次所有新增政策错误均复用该唯一出口，没有旁路。
- 实际偏差在 `decide()` 后才可得；第四值复核失败也回到同一 `policy_reject`，不会先发布 PASS。
- 新代码不创建 production staging/tmp；测试全部使用 `TemporaryDirectory` 自动清理。完工时全仓扫描 `*.tmp`、`*.staging` 及本工单 superseded 临时件为零命中。
- 结论：新增校验均 fail-closed；政策错误/通道故障两义保持 exit 2/1 分离，归档失败继续升格 exit 1，零 staging/tmp 残留。

## 5. 发现未修

按工单“只登记不修”边界，以下非 waiver/approval 的 JSON 解析点仍使用 Python 默认非有限常量语义：

- `scripts/lib/supply_truth_gate.py`：旧收据作废判读、Solana observation bundle、replay_stats。
- `scripts/report/shared_release_receipt.py`：replay_stats、各类 producer receipt、observation bundle、reconciliation/accounting/adversarial/shared release JSON。

这些面不属于本单 waiver/approval 政策解析，未扩散修改，留裁判决定是否另开同族工单。

另：`scripts/report/handoff_manifest.py` 的新 rg 命中仅是注释；`CHANGELOG.md` 命中为历史台账。两者均无本单运行时缺口，未修改。
