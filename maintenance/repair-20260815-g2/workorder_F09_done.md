# 工单 F-09 施工报告

## 状态

**STOPPED_AWAITING_SCOPE_DECISION**。

F-09 白名单内实现与专属验证已完成；工单点名的三项存量回归因名单外 fixture 缺少新 v3 必填字段 `warnings: []` 打红。依工单“名单外打红停下请示”，未修改这些测试，未继续扩大测试或施工范围，未宣称整体验收完成。

全程未运行任何 git 命令。

## A. producer 完成项

- `scripts/evm/verify_recon.py` 新增 `--divergence-note <path>`。
- GMGN 重算差异大于 0、其他硬检查通过时保持 PASS/0，并写顶层 `warnings:["gmgn_divergence"]`；零差异写 `warnings:[]`。
- 无说明黄灯 stdout 明示 `gmgn_divergence_note.json` 与追加 `--divergence-note` 的重跑形态。
- 合法说明绑定到 `inputs.divergence_note`。
- 说明不覆盖当前差异、输入哈希不符、字段不合法或零差异预填说明时 exit 1；该专用错误路径不调用 ERROR receipt 写入，原收据逐字节保持不变。

## B. 新说明件契约完成项

生产侧独立实现了 `gmgn-divergence-note/v1` 验证器：

- 顶层与 request 精确键集；target 全等。
- config/balances/replay_stats/gmgn 四输入 sha256 全绑定。
- divergences 有序、地址唯一、Decimal 有限且使用规范字符串，并与本次重算集合逐项全等。
- request 规范 JSON 的 sha256 独立重算。
- findings 按地址一一覆盖；cause 只接受 `gmgn_data_lag`、`methodology_diff`、`gmgn_upstream_error`。
- explanation 至少 30 个白名单实义字符；可选 evidence_refs 约束为案根内非 symlink 普通文件并核 size/sha256。
- conclusion 必含“重放数据经查证无误”；investigator 有实义；时间严格为 `YYYY-MM-DDTHH:MM:SSZ` 且不晚于当前时间加一天。
- JSON NaN/Infinity 拒收。

## C. consumer 完成项

- `scripts/report/shared_release_receipt.py` 对账区新增刻意双写的独立说明验证器，未调用 producer 验证器。
- `warnings` 必须是无重复已知字符串数组。
- 实物重算 `diff_count>0` 与 `gmgn_divergence` 双向互锁。
- 有差异必须绑定并完整重验案根说明；无差异禁止绑定说明。
- handoff/audit 文件本身零修改，语义继续由 shared 调用链继承。
- shared 的 A4/adversarial 区未修改。

## D. 文档完成项

- `references/data-pipeline-evm-recon.md` §5 已把 top-N 冻结块 RPC raw balance 硬对账与 GMGN 0.15pp 黄灯对表拆开。
- 已写四态真值表、说明字段、三种 cause、`self_error` 必须修数据重跑、标准 conclusion 与重跑命令形态。
- `evm-observation-bundle/v1`、`supply-truth-receipt/v4`、`accounting-gate/v2` 三条 needle 保留。
- `references/analyze-workflow.md` 未修改。

## E. invariant 登记

首次扫描精确报告：

- 新 consumer 点：`scripts/evm/verify_recon.py` → `gmgn-divergence-note/v1`。
- `scripts/report/shared_release_receipt.py` 既有 consumer 集合新增同 schema。

据此只把 `receipt_consumers` 下限从 78 升到 80，并登记上述两处；未调整其他 minimum。复跑结果：

`PASS invariant manifest: receipt_producers=62, receipt_consumers=85, transport_calls=63, atomic_writes=54, formal_entrypoints=58, exceptions=0`

## F. 先红后绿与四态证据

红测见 `f09_red.log`：F-07 基线对差异返回 PASS/0，但访问 `warnings` 触发 `KeyError`，证明黄灯字段缺失。

专属绿测见 `f09_green.log`：

1. 有差异无说明：producer PASS/0＋黄灯；consumer 因缺说明拒绝。
2. 有差异合法说明：producer 带参重跑绑定成功；consumer 独立重验通过。
3. 缺覆盖、数值不符、输入哈希不符、非法 cause、26 字符说明、非法时间、错误 request sha：producer 均 exit 1，输出文件逐字节不变。
4. 无差异无说明：`warnings:[]` 且 consumer 通过；无差异带说明：producer exit 1 且不覆写。

消费侧另验了抹警告、假警告和案外说明引用。两侧行为向量覆盖合法件与 schema/target/input/divergence/request_sha/cause/explanation/conclusion/investigator/time 单点变异，逐项判定一致。

## 改动清单

白名单内：

- `scripts/evm/verify_recon.py`
- `scripts/report/shared_release_receipt.py`（仅对账相关 helper/路径）
- `references/data-pipeline-evm-recon.md`
- `scripts/tests/invariant_manifest.json`（仅 E 节登记）
- `scripts/tests/test_gmgn_divergence_note.py`（新文件）

工单证据：

- `maintenance/repair-20260815-g2/f09_red.log`
- `maintenance/repair-20260815-g2/f09_green.log`
- 本报告

禁碰文件未施工：VERSION、CHANGELOG、SKILL.md、r10_ledger.md、pyproject、run_all.py、contract manifests、audit_release_gate.py、handoff_manifest.py、analyze-workflow.md。

## 已通过验收项

- `python3 scripts/tests/test_gmgn_divergence_note.py`：exit 0。
- `python3 scripts/tests/test_recon_deep_reverify.py`：exit 0。
- `python3 scripts/tests/invariant_scan.py`：exit 0。
- `python3 scripts/tests/docs_lint.py --all`：exit 0。

## 名单外打红与请示

以下三项都在消费手造的零差异 `evm-reconciliation-receipt/v3` 时因缺少 `warnings:[]` 被拒：

| 名单外文件 | 结果 | 首个根因 |
|---|---:|---|
| `scripts/tests/test_sixlens_receipts.py` | exit 1 | 手造 v3 fixture 缺 `warnings:[]` |
| `scripts/tests/test_handoff_manifest.py` | exit 1 | READY/冻结调用链 fixture 缺 `warnings:[]`；后续 `entity_freeze.json` 不存在是前置失败的连锁结果 |
| `scripts/tests/test_audit_release_gate.py` | exit 1 | audit fixture 缺 `warnings:[]` |

这是 F-09 合同变更必然引发的 fixture 升级，不应通过“缺字段视为空数组”放宽 consumer，否则会违反 C 节“warnings 字段必须为数组”并让旧 v3 静默绕过新契约。

**请示：是否授权把白名单最小扩到上述 3 个测试文件，仅给其零差异 v3 fixture 补 `warnings: []`，随后重跑工单全部验收命令？** 若授权后出现新的名单外失败，将再次停工，不自行扩大范围。

## 补充轮（调度方验收注记）

codex 补充轮按裁决执行但漏写本节，由调度方（Fable）验收后补记实况：

- 实际改动比预授权更小：仅 `scripts/tests/test_audit_release_gate.py` 的公共
  `write_deep_recon_fixtures` helper 一行补 `"warnings": []`——sixlens/handoff
  两个测试复用该公共夹具（第 3 刀 D 节确立），一处修改三测试全绿。
- 调度方本机全量 `run_all.py` 101/101 全绿（含两个 loopback 纵切片）。
- 请示的三文件白名单实际只动用一个；无新增名单外失败。
