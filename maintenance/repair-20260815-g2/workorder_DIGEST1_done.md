# 工单 消化轮 1 施工报告（STOPPED：invariant manifest 待授权）

## 结论

plan 权威链消费侧缺失的根因已确认并完成代码修复；H1/H2/H3/H4/H5/H6/H10 与 H40 六计数字段已固化为回归负测，目标测试先红后绿。公共存量夹具已补成完整权威链，工单授权的四组关联测试全部通过。

但 `python3 scripts/tests/invariant_scan.py` 命中工单规定的停止条件：`shared_release_receipt.py` 新增消费 `anchor-plan/v2` 后，`scripts/tests/invariant_manifest.json` 的 `receipt_consumers` 登记仍是旧集合。该 manifest 属于工单禁改文件，因此未自行修改，也未继续跑 `run_all.py`。请融合方决定是否授权把该 schema 加入 manifest 后继续全量验收。

## 根因确认

旧 `_validate_time_receipt` 把 `inputs.plan` 直接当标准答案，只校验了 plan receipt 的 envelope/schema/verdict、receipt target 和 input SHA；没有证明被消费的 plan 就是 `anchor_plan.py` 签发的那份实物。攻击者可同步改 plan、rows、transcript 后绕过点位全量性与签发身份。

本次新增 `_validated_time_plan_authority`，所有权威链失败统一报 `time plan authority chain broken: ...`，并在进入 plan 点位与 transcript 深重验之前完成签发链闭合。

## 生产侧到消费侧逐项平移

| 生产侧 `time_spotcheck.py::load_validated_plan` | 消费侧 `shared_release_receipt.py` | 独立消费语义 |
|---|---|---|
| 69–77 | 922–935（并复用 316–341 的案根安全实物绑定） | plan/receipt 必须是案根内非 symlink 正规文件；JSON 可解析；receipt envelope、schema、PASS/0 合规 |
| 78–79 | 939–940 | plan schema 必须为 `anchor-plan/v2` |
| 80–88 | 930–937 | plan receipt 必须为 v2/PASS/0；producer 必须是当前仓 `scripts/lib/anchor_plan.py` 且哈希正确 |
| 89–95 | 941–949 | plan.target 与 receipt.target 全等；签发 target 与 time target 规范化全等；chain/token/final_block 兼容字段与 target 全等 |
| 96–97 | 950–951 | plan.producer 与 receipt.producer 全等 |
| 98–99 | 953–958 | plan.input 与 receipt.input_identity 全等，且二者解析到 time receipt `inputs.input` 的同一实物；不再只比 SHA |
| 100–102 | 960–963 | receipt input_manifest 是案根内 size+SHA 绑定实物，且 plan.input_manifest 与之全等 |
| 103–110 | 965–968（实物三验由 316–341 完成） | receipt.output 的 path/size/SHA 必须绑定被消费的同一个 plan 实物 |
| 111–112 | 969–970 | receipt.plan_schema 必须为 `anchor-plan/v2` |
| 113–114 | 971–974 | plan.generated_at 必须非空且与 receipt.generated_at 全等 |
| 115–117 | 975–981 | matrix/forced 必须为列表；probe_count 必须是非 bool 整数且等于实际点数 |
| H40 类型缺口 | 1038–1043 | points/balance_points/tx_points/exact_match/mismatch/rpc_err 六字段逐个先拒 bool，再要求 int |

## H 向量回归

`scripts/tests/test_recon_deep_reverify.py:219–348` 新增：

- H1：自写一点评估 plan 搭配另一份签发收据；
- H2：plan 砍成一点但 probe_count 仍为二；
- H3：receipt.output 指向另一份 plan；
- H4：plan schema 冒充；
- H5：plan target 换绑；
- H6：plan/receipt identity 换绑到同内容、不同路径的 input，专门防止“只比 SHA”；
- H10：`time_spotcheck.py` 冒充 anchor plan producer；
- H40：六个计数字段分别以 `True`/`False` 冒充 1/0；
- 绿例继续由真实 `anchor_plan.py` producer ref、完整 envelope/output/manifest/probe_count 链生成，并先经生产侧 `load_validated_plan` 后再送消费侧验证。

## 同族排查

- balance：标准答案是 `inputs.balances` 实物。`_recon_bound_reality` 先通过 `_bound_json_input` 做案根 path/size/SHA 三验，再从实物重建余额集合；`_validate_recon_balance` 从该集合重算 top-N 地址顺序、replay_raw、diff/status/计数，并逐行绑定 transcript。不存在另一个未经签发绑定的“答案 plan”。
- supply：同一入口绑定 config、balances、replay_stats 三份实物，并从实物重算 mint/burn、nominal、balance_sum、negative 集与 closed；`_validate_recon_supply` 逐字段对比重算结果。不存在 time 类标准答案来源缺口。
- anchor：`_validate_anchor_receipt` 先对 receipt.output 做案根 path/size/SHA 三验，再从 output 实物逐行重算日期范围、target identity、覆盖计数和失败列表。答案就是已绑定 output 实物，无同族缺口。

## 红绿与关联测试证据

- 红灯：`digest1_red.log`，退出码 1；明确列出 H1/H2/H3/H4/H5/H6/H10 和六个 H40 bool 字段全部被旧消费面放行。SHA256：`ccfd94c997924889f618fabb227f4ccd3035cb2434e984905f10a590cd3be6ee`。
- 绿灯：`digest1_green.log`，退出码 0，末行 `PASS test_recon_deep_reverify`。SHA256：`35357a38357972531089b0200b2061ad606b20c1acdb8e12357324c535aa1b85`。
- `test_audit_release_gate.py`：PASS。
- `test_sixlens_receipts.py`：PASS。
- `test_handoff_manifest.py`：68 项全部通过。
- `test_arbitrum_exploration_cli.py`：PASS。

存量适配仅修改授权的 `test_audit_release_gate.py::write_deep_recon_fixtures`：补 `kind`、generated_at、兼容 target 字段、plan producer/input_manifest、receipt plan_schema/output/probe_count，使公共 time 正例成为完整权威链。其三个调用方无需额外改动即通过。

## invariant 红灯与请示

命令：`python3 scripts/tests/invariant_scan.py`，退出码 1。

精确输出：

```text
FAIL receipt_consumers: code point missing from manifest: ('scripts/report/shared_release_receipt.py', (..., 'anchor-plan-receipt/v2', 'anchor-plan/v2', ...))
FAIL receipt_consumers: manifest point missing from code: ('scripts/report/shared_release_receipt.py', (..., 'anchor-plan-receipt/v2', ...))
invariant manifest FAIL: 2 discrepancy(s)
```

建议但未实施的 manifest 差异：

```diff
 "anchor-plan-receipt/v2",
+"anchor-plan/v2",
 "evm-observation-bundle/v1",
```

目标位置是 `scripts/tests/invariant_manifest.json` 的 `receipt_consumers` 中 `scripts/report/shared_release_receipt.py` 条目（当前约 468–489 行）。请授权融合方更新该禁改 manifest，随后重跑 invariant 与 `run_all.py`；当前未达到“除两个 loopback EPERM 外全绿”的最终验收状态。

## 施工边界

已修改/生成：

- `scripts/report/shared_release_receipt.py`
- `scripts/tests/test_recon_deep_reverify.py`
- `scripts/tests/test_audit_release_gate.py`
- `maintenance/repair-20260815-g2/digest1_red.log`
- `maintenance/repair-20260815-g2/digest1_green.log`
- 本报告

未修改生产侧 `time_spotcheck.py`、manifest/契约文件、VERSION/CHANGELOG/SKILL/r10 ledger、A4/adversarial 区；未执行任何 git 操作。

## 补充裁决执行记录（最终状态：ACCEPTED）

本节执行调度方在原工单末尾追加的“补充裁决（调度方）”。该裁决已授权登记
`scripts/tests/invariant_manifest.json`；本节结论取代上文“manifest 待授权”的
STOPPED 状态，同时保留原始停止经过作为审计记录。

### invariant 实况与登记 diff

授权前再次执行 `python3 scripts/tests/invariant_scan.py`，退出码 1；实际差异仍精确为
`scripts/report/shared_release_receipt.py` 的消费者 schema 集比 manifest 多
`anchor-plan/v2`，没有第二处生产代码点差异。

按扫描器实际集合登记：

```diff
 "minimum_counts": {
-  "receipt_consumers": 80,
+  "receipt_consumers": 81,
 }

 "script": "scripts/report/shared_release_receipt.py",
 "schemas": [
   "anchor-plan-receipt/v2",
+  "anchor-plan/v2",
   "evm-observation-bundle/v1",
 ]
```

`minimum_counts` 只升不降：本刀新增一个消费 schema，故底线从 80 升至 81；其余四项
底线保持原值。登记后的最终扫描输出（退出码 0）：

```text
PASS invariant manifest: receipt_producers=62, receipt_consumers=86, transport_calls=63, atomic_writes=54, formal_entrypoints=58, exceptions=0
```

### 全量验收中发现的授权夹具适配

登记后首次执行 `python3 scripts/tests/run_all.py`，除两个预期 loopback EPERM 外，
`test_a4_gate.py` 还暴露一处工单授权名单内的存量夹具适配缺口：测试用
`copytree` 把案子复制到 `case_new` 后，外层收据已经重绑，但新增权威链中的
`plan.input` / `plan_receipt.input_identity` 仍指向旧案根，消费侧按新断言正确拒绝：

```text
ValueError: time plan authority chain broken: time plan input identity file invalid or escapes case root
```

在 `test_a4_gate.py::rebind_case_inputs` 内做最小适配，等价模拟复制案根后重跑
`anchor_plan`：由内向外刷新 input identity、input manifest、plan、plan receipt、time
receipt 的 path/size/SHA 链；未放宽生产校验。适配后独立执行
`python3 scripts/tests/test_a4_gate.py`，退出码 0，末行：

```text
a4_gate 契约测试全部通过（23 项）
```

### 最终 run_all 输出与裁定

适配后再次执行 `python3 scripts/tests/invariant_scan.py`，仍为上述 PASS。随后重新执行
`python3 scripts/tests/run_all.py`；入口退出码为 1，仅因为工单明确豁免的两项测试在
当前沙箱不能绑定 `127.0.0.1`：

```text
FAIL(rc=1)  test_batch3_solana_vertical_slice.py
PermissionError: [Errno 1] Operation not permitted

FAIL(rc=1)  test_batch3_evm_vertical_slice.py
PermissionError: [Errno 1] Operation not permitted

PASS  invariant_scan.py
PASS  test_a4_gate.py          a4_gate 契约测试全部通过（23 项）
PASS  test_recon_deep_reverify.py PASS test_recon_deep_reverify
2 项失败——修完再收工
```

完整汇总中除上述两个 loopback `socket.bind` 沙箱能力失败外，其余项目全部 PASS；无
业务断言失败。按工单“沙箱内 run_all.py 除两个 loopback EPERM 外全绿”的验收口径，
本工单最终验收通过。

### 补充裁决新增改动边界

- 新增修改：`scripts/tests/invariant_manifest.json`（仅消费者 schema 登记与对应底线上调）。
- 授权适配：`scripts/tests/test_a4_gate.py`（仅复制案根时刷新 time plan 权威链夹具）。
- 未修改 `run_all.py`、生产侧 `time_spotcheck.py`、VERSION、CHANGELOG、SKILL.md、
  `r10_ledger.md`、`pyproject.toml` 或其他 manifest/契约文件。
- 全程未执行任何 git 操作。
