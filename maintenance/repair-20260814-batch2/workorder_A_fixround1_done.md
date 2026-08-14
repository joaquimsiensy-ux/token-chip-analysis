# 工单 A 消化轮 1 完工记录

施工分支：`repair-20260814-batch2`。开工时工作树干净。本轮未执行任何 git 写命令，未提交。

## 变更范围

- `scripts/lib/supply_truth_gate.py`：生产侧 waiver/approval 校验、收据 inputs 绑定。
- `scripts/report/shared_release_receipt.py`：消费侧独立 waiver/approval 校验；未改工单 B adversarial 段。
- `scripts/tests/test_repair_batch_a.py`：13 个 fixround 定向测试及夹具重绑定。
- `references/analyze-workflow.md`：A2 容差凭据契约四处对齐。
- 本文件：施工、双跑与自审记录。

## 首轮红态

先只改测试，不改生产代码，运行：

```text
python3 scripts/tests/test_repair_batch_a.py
BATCH A FAIL 10/38
```

失败项与盲审发现对应如下：

- F-A1：`test_fixround_fa1_zero_width_text_end_to_end` 红。首个实测为 approval `nonce=U+200B`，生产 `rc=0` 且落 `PASS`；同轮 `_meaningful_text` 尚不存在。
- F-A2：`test_fixround_fa2_giant_integer_end_to_end_and_archive` 红，实测 `OverflowError` 逃逸，`live=True`、`archives=0`；20 万层 waiver/approval 两项均实测 `rc=1`、旧 PASS 留在原位、归档数 0。
- F-A3：生产行为已有三值闸，新增“approved=150、observed=50、tolerance=50、actual=50、无 approval”独立锚在基线即绿；缺陷是此前无单独守卫。进程内把该闸阈值变异为不可达后，锚测试转红并观察到 `rc=0/PASS`。
- F-A4：库函数第四值防线基线存在，直调锚在基线即绿；进程内绕过该阈值后测试按预期红：`库函数直调未拦 actual diff > 100 且无 over-cap approval`。
- F-A5：两条 NaN 防线基线存在，独立锚在基线即绿；分别把 `_reject_constant` 变异为放行、把 `_finite_number` 变异为恒真后，两次均 `EXPECTED_RED`。
- F-A6：`test_fixround_fa6_workflow_wording_matches_contract` 红，首个缺失锚为“含超出 float 范围的巨整数”。
- F-A7：`test_fixround_fa7_approval_lifetime_both_sides` 红，31 天 approval 实测生产 `rc=0/PASS`；9999 年同族尚可复用。
- F-A8：`test_fixround_fa8_approval_receipt_input_binding` 红，生产收据 inputs 只有 replay_stats 与 tolerance_waiver，缺 over_cap_approval。
- F-A9：`test_fixround_fa9_approval_cannot_double_as_evidence` 红，approval 兼任 evidence 时生产 `rc=0/PASS`。
- F-A10：`test_fixround_fa10_two_side_behavior_vectors` 红，`10**400` 在两侧 `_finite_number` 均返回 True，且两侧尚无 `_meaningful_text`。

F-A3～F-A5属于“实现存在但缺独立锚”，所以红态用进程内变异证明；变异只在 `unittest.mock` 上下文内生效，不写仓库文件。输出为：

```text
EXPECTED_RED F-A3_three_value: ... rc=0 ... verdict=PASS ...
EXPECTED_RED F-A4_fourth_value: 库函数直调未拦 actual diff > 100 且无 over-cap approval
EXPECTED_RED F-A5_parse_constant: supply_truth_gate._reject_constant accepted NaN
EXPECTED_RED F-A5_finite_number
```

## 逐项处置

1. **F-A1 实义字符**：生产侧与消费侧各自实现 `_meaningful_text`，逐字符排除空白及 Unicode `Cf/Cc/Zs/Zl/Zp`；approval 的 `nonce/user_approval/reported_to_user/approved_by` 与 waiver 的 `approved_by/reason` 全部改用该判定。测试覆盖 U+200B、U+FEFF、U+2060 逐字段双侧拒；U+3000 继续拒；前后带空格的正常中英文继续过。
2. **F-A2 巨整数与递归 JSON**：两侧 `_finite_number` 对 int 先做 `float()` 可转换性检查并捕获 `OverflowError`；生产/消费各两个 waiver/approval JSON 解析点显式捕获 `RecursionError`。`assert_waiver_covers_diff` 同时补非有限输入收口。巨整数与两类 20 万层 JSON 均归政策内容错误；生产 `exit 2`，旧 PASS 仅归档一件。
3. **F-A3 三值主闸锚**：新增 approved 为唯一超顶值的生产侧定向测试；移除/绕过该闸即红。
4. **F-A4 第四值直调锚**：保留 `assert_waiver_covers_diff` 的 actual over-cap 检查，补直接调用测试，并在代码注明“CLI 链上三值闸先拦；此处保护库函数单独调用”。
5. **F-A5 NaN 双防线锚**：两侧分别直测 `_reject_constant` 与 `json.loads(..., parse_constant=...)`，并分别直测 `_finite_number(nan/inf)` 为 False；任一防线变异均红。
6. **F-A6 文档对齐**：A2 明确巨整数不有限、人工文本须含实义字符、凭据内容解析异常归 exit 2 并作废旧收据，以及 exit 1 只保留读不动等通道故障。
7. **F-A7 有效期上限**：两侧强制 `expires_at_utc - user_decided_at_utc <= 30 天`；29 天双侧通过，31 天和 9999 年双侧拒绝。
8. **F-A8 审计可见性**：waiver 在场且引用 approval 时，生产收据 `inputs.over_cap_approval` 绑定其 path/size/sha256；消费侧要求该 input 在场且解析为 waiver 引用的同一实物。缺失与改绑等字节副本均拒绝。
9. **F-A9 evidence 独立性**：生产/消费均解析 evidence 实物集合，并禁止任何 evidence 路径等于 over-cap approval 实物。
10. **F-A10 两侧行为守卫**：新增 `_finite_number`、`_meaningful_text`、`_canonical_request_sha256` 行为向量比对；比较行为与期望值，不比较源码文本。

## 绿态与双跑证据

定向绿跑：

```text
python3 scripts/tests/test_repair_batch_a.py
PASS batch A F-01/F-02 regressions 38/38
```

其中 F-A1 为 3 种不可见字符 × approval 4 字段 × 生产/消费，加 waiver 2 字段 × 生产/消费；F-A2 端到端确认巨整数、深层 waiver JSON、深层 approval JSON 全部拒绝，生产侧每案 `rc=2`、正式收据不存在、`superseded-*` 恰好 1 件。

全量首跑（受限沙箱）：

```text
python3 scripts/tests/run_all.py
2 项失败
test_batch3_solana_vertical_slice.py: socket.bind 127.0.0.1 -> PermissionError [Errno 1]
test_batch3_evm_vertical_slice.py: socket.bind 127.0.0.1 -> PermissionError [Errno 1]
其余全部 PASS；test_repair_batch_a.py = 38/38
```

按环境规则在允许 loopback 的沙箱外原命令复跑：

```text
python3 scripts/tests/run_all.py
rc=0
test_batch3_solana_vertical_slice.py PASS
test_batch3_evm_vertical_slice.py PASS
全部通过
```

格式检查：

```text
git diff --check
rc=0
```

## 自审

- 文件边界：业务变更仅 4 个文件，另新增本完工记录；未改 VERSION、CHANGELOG、pyproject、SKILL、contract/invariant 基线或其他工单文件。
- 工单 B 保护：`shared_release_receipt.py` 从 `def validate_adversarial_review` 至 EOF 的 SHA256 修前、修后均为 `956498347f17edd6196cf28029bb77f411bd436338ca1623e25e27cc8741b740`。
- shared 侧实际变更仅 import 与 waiver/approval 相关 helper、校验函数；adversarial 聚合、角色、coverage 与 release 逻辑零改动。
- 两侧独立纪律：`_meaningful_text` 与 `_finite_number` 在生产/消费各自实现；测试只比行为向量，不把消费侧改成调用生产侧私有函数。
- 错误分层：JSON 内容损坏/递归过深/非有限数值统一进入政策拒绝或消费 BLOCK；文件读取 `OSError` 仍维持通道故障语义。
- 正例保持：普通 ≤100bps waiver、合法 >100bps approval、29 天 approval、正常中英文文本均通过；原批 A/B/C/D 及全量 suite 全绿。
- git 纪律：仅使用只读 `git branch/status/diff` 做边界与格式核验；未执行 add/commit/checkout/reset/restore/rebase/merge 等写命令。

工单 A 消化轮 1 施工完成。
