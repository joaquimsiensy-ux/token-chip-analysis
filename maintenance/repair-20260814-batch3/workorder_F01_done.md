# 工单 F01 完工记录

## 结论

F-01（R10-16/17）已按工单落地：A4 聚合升级为 `adversarial-review/v4`，artifact 升级为 `adversarial-review-artifact/v2`；runner finalize 与 shared 消费侧都会从哈希绑定的 artifact 字节重建 required blocker 集并做双向对账；evidence 与已填写的 resolution 均执行 10 个实义白名单字符门槛；entrypoint SHA-256 改为跨角色全局唯一。audit 继续 100% 委托 shared 深验。

未运行任何 git 写命令，未改版本件。

## 先红清单

生产代码尚未修改时，先新增 `scripts/tests/test_repair_batch3_f01.py`，随后执行：

```text
python3 scripts/tests/test_repair_batch3_f01.py
exit code: 1
```

真实先红共 25 项：

1. A 联动：finding 无账 → finalize rc2、不落盘、零残留
2. A 联动：non_covered 无账 → finalize rc2、不落盘、零残留
3. A 联动：REFUTED 无账 → finalize rc2、不落盘、零残留
4. A 账本：幽灵账拒绝
5. A 账本：同对象重复记账拒绝
6. A 多 artifact：两 critic 不同 finding 缺一账
7. A 多 artifact：两个 reviewer 同 claim REFUTED 仍需两项处置
8. A blocker 结构：多余 note 键拒绝
9. A blocker 结构：缺 source 拒绝
10. A blocker 结构：source 坏 kind 拒绝
11. A blocker 结构：source 零宽 ref 拒绝
12. A blocker 结构：source 多余键拒绝
13. A 消费侧独立重建：手抄 delete 账仍被 shared/audit 拒
14. A 消费侧独立重建：手抄 manual 账仍被 shared/audit 拒
15. B evidence 边界：ASCII 9
16. B evidence 边界：汉字 9
17. B evidence 边界：9 实义＋20 零宽
18. B evidence 边界：`ab       cd`
19. B resolution 边界：resolved=true 9
20. B resolution 边界：resolved=false 但写 9
21. B 消费侧独立门槛：重绑后 9 实义 evidence 仍拒
22. D v3 旧聚合 shared/audit 均拒且提示 v4 重跑
23. E protocol 文档含 source/refuted_claim/10 门槛/v4 重跑
24. E analyze-workflow 文档含 evidence 10 门槛与 v4
25. E research-workflows 文档含 artifact/v2 与联动越界

先红同时确认旧实现错误放行了本 finding：findings/non_covered/REFUTED 无账、幽灵或重复账、短 evidence/resolution，以及消费侧手抄删账。

## 修后绿证据

```text
python3 scripts/tests/test_repair_batch3_f01.py
exit code: 0
末行: all batch3 F01 tests passed

python3 scripts/tests/test_repair_batch2_f02.py
exit code: 0
末行: PASS workorder B F-02 regressions

python3 scripts/tests/invariant_scan.py
exit code: 0
末行: PASS invariant manifest: receipt_producers=59, receipt_consumers=77, transport_calls=63, atomic_writes=52, formal_entrypoints=58, exceptions=0

python3 scripts/tests/test_audit_release_gate.py
exit code: 0

python3 scripts/tests/test_repair_batch_d.py
exit code: 0
末行: BATCH D 全部通过
```

完整 suite 第一次在 workspace-write 沙箱内执行：

```text
python3 scripts/tests/run_all.py
exit code: 1
```

仅 `test_batch3_solana_vertical_slice.py` 与 `test_batch3_evm_vertical_slice.py` 因沙箱拒绝 `ThreadingHTTPServer.bind("127.0.0.1", 0)`，报 `PermissionError: [Errno 1] Operation not permitted`；其余项目全部 PASS。未把该环境失败记作全绿，也未修改测试绕过。

随后在允许 loopback bind 的环境完整重跑同一命令：

```text
python3 scripts/tests/run_all.py
exit code: 0
末行: 全部通过
```

其中两个 vertical slice 均真实 PASS；F01、f02、invariant_scan、audit、batch_d 与并存的 evmobs 测试也全部 PASS。

附加静态核验：`git diff --check` exit 0；`V3_RERUN_HINT` 已无现役引用；两份 `_meaningful_text` 本体、`shared_release_receipt.py` 的 `schema = receipt.get("schema")` 锚点及禁触路径均无本工单 diff。

## 改动文件清单

F01 新增或修改：

- `scripts/report/adversarial_review_runner.py`
- `scripts/report/shared_release_receipt.py`
- `scripts/report/audit_release_gate.py`
- `scripts/tests/test_repair_batch3_f01.py`（新增）
- `scripts/tests/test_repair_batch2_f02.py`
- `scripts/tests/test_audit_release_gate.py`
- `scripts/tests/test_repair_batch_d.py`
- `scripts/tests/invariant_manifest.json`
- `scripts/tests/run_all.py`
- `references/independent-audit-protocol.md`
- `references/analyze-workflow.md`
- `references/research-workflows.md`
- `maintenance/repair-20260814-batch3/workorder_F01_done.md`（本文件）

并存但非 F01、未由本工单修改：`scripts/tests/invariant_scan.py`、`scripts/evm/observe_supply.py`、`scripts/lib/evm_observation.py`、`scripts/tests/test_evm_observation.py`、`maintenance/repair-20260814-evmobs/`。`invariant_manifest.json` 与 `run_all.py` 中已有 evmobs hunk 原样保留，本工单只叠加 F01 条目。

## diff → finding 逐 hunk 映射

所有 F01 hunk 均映射到 codex review F-01（R10-16/17）；未映射 hunk 为 0。

| 文件 / hunk | finding 映射与作用 |
|---|---|
| `adversarial_review_runner.py` 常量区 | F-01 / R10-16/17：blocker 键、source kind、10 字符门槛、aggregate v4、artifact v2、v4 迁移提示。 |
| `adversarial_review_runner.py` `_has_min_meaningful_chars`、`_string_array`、evidence 挂载 | F-01 / R10-17：按既有白名单逐字符计数，evidence 每条至少 10 个实义字符；不抬高 alternative_explanations/critic 文本门槛。 |
| `adversarial_review_runner.py` `validate_blocking_findings` | F-01 / R10-16/17：按 id→resolved→键白名单→source→resolution 顺序校验；非 manual source 唯一；resolution 存在即执行 10 门槛。 |
| `adversarial_review_runner.py` `build_required_refs` / `validate_blocker_linkage` | F-01 / R10-16：以 artifact 相对路径＋JSON 位置机械生成 required 集；缺账、幽灵账均 fail-closed，缺账错误带原 finding 文本。 |
| `adversarial_review_runner.py` finalize 循环与封口前 | F-01 / R10-16：累积每份已验证 artifact（不被末份覆盖），全局 entrypoint SHA 去重，union coverage 后执行 linkage，再决定 PASS/BLOCKED。 |
| `shared_release_receipt.py` import、v4 分支、artifact 累积、entrypoint 与 linkage | F-01 / R10-16/17：消费侧从 execution receipt 绑定的 artifact 字节独立重建 required 集；v2/v3 fail-closed 迁移；跨角色 entrypoint 全局唯一。 |
| `audit_release_gate.py` import、docstring、错误分支 | F-01 / R10-16/17：v4/V4_RERUN_HINT 单源化；保持零新业务逻辑并委托 shared 深验。 |
| `invariant_manifest.json` runner producer/consumer、audit/shared consumer schema hunk | F-01 / R10-16/17：v4/artifact v2 机器契约与 v2/v3 拒绝字面量同步；minimum_counts 未降低。并存 evmobs hunk不归 F01。 |
| `test_repair_batch3_f01.py` 全文件 | F-01 A–E：联动、多 artifact、结构、10 字符边界、消费侧独立重建、entrypoint 身份、v3 迁移、文档契约先红后绿。 |
| `test_repair_batch2_f02.py` schema/source/hint/旧件断言 hunk | F-01 存量适配：artifact v2、manual source、v4 常量单源与迁移断言；保留原负例触发原因。 |
| `test_audit_release_gate.py` 两角色脚本与未决 blocker hunk | F-01 存量适配：role 注释使 entrypoint 字节分叉；artifact v2；manual source 保留“未决发布否决项”测试语义。 |
| `test_repair_batch_d.py` 两角色脚本 hunk | F-01 存量适配：role 注释使 entrypoint 字节分叉并升级 artifact v2。 |
| `run_all.py` F01 suite 条目 | F-01 回归门禁：新测试进入全量 suite。并存 evmobs 条目不归 F01。 |
| `independent-audit-protocol.md` 六个 hunk | F-01 / R10-16/17：联动阻断、entrypoint 定性、v4/artifact v2、evidence 10 门槛、四键 blocker/机械定位符、v2/v3 全程重跑迁移。 |
| `analyze-workflow.md` A4 hunk | F-01 / R10-16/17：主流程同步 v4、artifact v2、10 门槛及逐项 blocker 联动。 |
| `research-workflows.md` schema/evidence/越界 hunk | F-01 / R10-16/17：输出骨架升级 artifact v2，写明 10 门槛和 linkage 少记/多记拒绝。 |

## 六视角自审①：字段源头 / 信任边界

1. 生产侧 required 集来源：`finalize_review` 对每份 execution receipt 调用 `validate_review_receipt`；该函数验证当前 runner producer、entrypoint SHA、artifact path/size/SHA、registry SHA，并从实际 artifact 字节解析 `artifact_data`。`build_required_refs` 只从这些已验证字节和绑定的 artifact 相对路径生成 `(kind, ref)`，不信 blockers 或 aggregate 自报。
2. 消费侧 required 集来源：`validate_adversarial_review` 重新读取 aggregate 指向的 execution receipt 与 artifact 实物，重新验证所有绑定，再从自己拿到的 `artifact_data` 重建 required 集；手抄 aggregate 删除 blocker、把非 manual 改为 manual、或只保留循环末份都不能绕过。
3. `completeness_finding`、`non_covered` 的 ref 绑定 artifact 路径、数组名和下标；`refuted_claim` 额外绑定 claim_id，因此同文 finding 或不同 reviewer 对同 claim 的 REFUTED 不会被 set 折叠。
4. evidence 门槛在 `validate_review_artifact`，runner 使用 `supply_truth_gate._meaningful_text`，shared 消费时通过现有 kwargs 显式注入自己的 `_meaningful_text` 副本。两份 `_meaningful_text` 本体均未修改。

## 六视角自审②：失败分支 / 原子性

1. runner linkage 失败发生在 payload 写入前；异常进入既有 `except`，清理 tmp，CLI 返回 rc2，正式 `adversarial_review.json` 不落盘。新测试对 finding、non_covered、REFUTED、缺账、幽灵账、重复账均验证“不落盘＋零 staging/tmp 残留”。
2. evidence/结构校验在 controlled artifact 发布前失败，既有 run_review 清理 staging，artifact 与 execution receipt 正式位均不落盘。
3. 账全但仍有 `resolved=false` 是合法聚合状态：runner 原子落盘 `release_decision=BLOCKED`；shared/audit 消费侧均拒绝发布。此路径与 linkage 结构错误明确区分。
4. shared linkage、短 evidence 或 entrypoint 身份失败均为只读验证失败，不写共享 release receipt；audit 捕获并记录 v4 校验错误。手抄聚合删账/改 manual、重绑短 evidence、跨角色同 entrypoint 字节均有消费侧负测。
5. v2/v3 聚合在访问深层自报字段前即按 V4_RERUN_HINT 拒绝；迁移必须重跑两角色 runner＋finalize 全程。

## 发现未修事项

F01 范围内未发现未修事项。

环境记录：workspace-write 沙箱禁止 loopback bind，导致第一次 full suite 的两个 vertical-slice 环境失败；允许 loopback 后完整 suite rc0，故不属于代码缺口。evmobs 会话的并存改动和 done 文件属于另一工单，本工单未触碰、未裁决。

WORKORDER_F01_COMPLETE
