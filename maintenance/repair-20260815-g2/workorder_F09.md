# 工单 F-09：GMGN 对表黄灯制 + 查证说明放行（骑在 F-07 之上）

> 执行者：codex（纯施工，**禁止任何 git 操作**）
> 前置：第 3 刀（F-07）已合入——verify_recon 已是 `evm-reconciliation-receipt/v3`、gmgn rows 已 Decimal 化、consumer 已有 gmgn_comparison 实物重算。本刀在其上加黄灯语义。
> 总计划：同目录 plan.md 第 4 刀节。用户产品裁决：**差异不停工打警告；带警告的案发布前必须附合格人工查证说明才放行；查证发现自己算错必须修数据重跑，不得写说明放行。**

## A. producer `scripts/evm/verify_recon.py`

1. **黄灯标记**：gmgn_diff>0 且其他硬检查通过时，verdict 仍 PASS/exit 0（不动 receipt_kernel 的 VERDICT_EXITS），`finalize_envelope` 附加顶层 `warnings: ["gmgn_divergence"]`；零差异时 `warnings: []`。stdout 打印黄灯提示与补说明指引（含说明文件名与重跑命令形态）。
2. **新增可选参数 `--divergence-note <path>`**（先跑出黄灯收据 → 人工查证写说明 → 带参重跑绑定，与 supply_truth 的 tolerance-waiver 同款时序）：
   - 生产侧验证说明件（验证规则见 B 节，生产侧为第一份实现）；
   - 合格 → 绑进 envelope `inputs.divergence_note`，收据仍 PASS+warnings；
   - 说明覆盖不了**当前重算**的差异集合（多、少、数值不符都算）→ 硬退 exit 1（producer ERROR 路径），**不得覆盖已存在的黄灯收据**；
   - 零差异却给了 `--divergence-note` → 硬退（防预填空说明）。

## B. 新件 `gmgn-divergence-note/v1`（人工手写，无 producer 脚本——over-cap-approval 先例）

案根文件（惯例名 `gmgn_divergence_note.json`）。字段与验证规则（**生产/消费两侧各自独立实现验证器，刻意双写；只共享 schema 常量与阈值常量**——照 `supply_truth_gate._validate_over_cap_approval`（生产侧）与 `shared_release_receipt._validate_over_cap_approval`（消费侧）的双写纪律）：

- `schema`: 恰为 `"gmgn-divergence-note/v1"`；
- `request`: 恰好键集 `{target, inputs_sha256, divergences}`：
  - `target`：chain/token/as_of_block，与收据 target 全等；
  - `inputs_sha256`：恰好键集 `{config, balances, replay_stats, gmgn}`，四个 64hex——必须与收据 `inputs` 四实物的 sha256 逐一相等（同一说明不可跨输入版本复用）；
  - `divergences`：**有序列表**，与消费侧从实物重算的 DIFF 集合逐项相等（address 唯一、gmgn_pct/replay_pct/diff_pp 为 Decimal 规范字符串，解析层拒 NaN/Inf——`_reject_constant` 先例）；
- `request_sha256`：对 request 规范 JSON（sort_keys+紧凑分隔符）的 sha256 独立重算相等；
- `findings[]`：与 divergences 按 address 一一对应，每条：
  - `cause` ∈ `{gmgn_data_lag, methodology_diff, gmgn_upstream_error}`（**枚举故意不含 self_error**：查证发现重放侧算错时唯一出路是修数据重跑）；
  - `explanation`：过 `_meaningful_text` 同款实义判定（Unicode 白名单，防不可见字符充数）且 ≥30 实义字符；
  - `evidence_refs`：可选；若给，逐个按案根安全相对路径解析（拒 `..`/symlink/越根，`_bound_case_ref` 同款）且为普通文件；
- `conclusion`：实义文本，必须含"重放数据经查证无误"承诺语义（子串锚定即可，文档同步给标准句式）；
- `investigator`：实义文本；
- `investigated_at_utc`：严格 UTC 格式 `YYYY-MM-DDTHH:MM:SSZ`，不得晚于当前时间+1 天。

## C. consumer `scripts/report/shared_release_receipt.py`（EVM balance 分支内衔接 F-07 已有的 gmgn 重算）

1. `warnings` 字段合法性：数组、元素为已知串、无重复；
2. **互锁**：重算 diff_count>0 ⟺ `"gmgn_divergence" ∈ warnings`（两方向都拒：抹警告拒、假警告也拒）；
3. diff_count>0 → `inputs.divergence_note` 必须存在：案根内实物（路径安全同款）、B 节全部规则的**消费侧独立实现**重验、divergences 与消费侧自己重算的 DIFF 集合有序相等；
4. diff_count==0 → `inputs.divergence_note` 必须不存在；
5. handoff/audit 经调用链自动继承，不改那两个文件。

## D. 文档 `references/data-pipeline-evm-recon.md` §5 第 1 条改写

1. 黄灯制四态真值表写清：有差异无说明=收据 PASS 带警告但发布链阻断；有差异合格说明=带参重跑绑定后放行；说明不合格=生产侧硬退不覆盖原收据；无差异给说明=硬退。写明说明怎么写（字段、cause 三枚举、self_error 必须重跑）、标准 conclusion 句式、重跑命令形态。
2. **顺手修正既有文档-代码落差**：现第 12 行把"top-N RPC 直查"（判 FAIL 的 balance_reconciliation）与"GMGN top10 百分比对表"（0.15pp 容差）混写成一件"逐个对到个位数"的 gate——拆成两件如实写。
3. ⚠️ 本册正文三条契约 needle 必须原样保住：`evm-observation-bundle/v1`、`supply-truth-receipt/v4`、`accounting-gate/v2`（docs_lint 会拦）。若 F-07 已把本册某串升版并同步契约表，以当前树状态为准不回退。
4. 不动 `references/analyze-workflow.md`。

## E. 中心登记（跟刀走的部分）

- `scripts/tests/invariant_manifest.json`：`gmgn-divergence-note/v1` 的 schema 比较会被 AST 扫描器在 verify_recon.py（生产侧验证）与 shared_release_receipt.py（消费侧）两处抽为 consumer 点——按 `python3 scripts/tests/invariant_scan.py` 实际 diff 输出登记（勿手拍），`minimum_counts` 只升不降。
- 契约 needle 新条目（`CT-RECON-xx`）与 run_all 挂载仍归末刀，本刀不做。

## F. 新测试 `scripts/tests/test_gmgn_divergence_note.py`

自建 main() runner，夹具复用/仿照 F-07 的案根夹具：

- **四态真值表逐态**（每态明确断言拒绝方）：
  1. 有差异无说明：producer 出 PASS+warnings 收据（exit 0）；消费侧拒（发布链阻断）；
  2. 有差异合格说明：带参重跑绑定成功；消费侧全链绿；
  3. 说明不合格（覆盖缺一条/数值不符/inputs_sha256 有一个不匹配/cause 非法/explanation 26 字符/investigated_at 非法/request_sha256 错）：producer 侧硬退且原黄灯收据未被覆盖（文件对比断言）；
  4. 无差异给说明：producer 硬退；无差异收据 warnings 为空、消费侧不要求说明（绿）；
- 消费侧独立负例：绑定合格说明后人为抹 warnings → 拒；无差异收据人为加 warnings → 拒；inputs.divergence_note 指向案外 → 拒；
- **两侧行为向量等价守卫**（照 `scripts/tests/test_repair_batch_a.py:1583` 的 `test_fixround_fa10_two_side_behavior_vectors` 同款）：对同一组固定向量（合法件、各字段单点变异件）逐值断言生产侧与消费侧验证器判定一致，防双写漂移。

## 先红后绿纪律

新测试对基线（F-07 后、本刀前）跑：黄灯负例应体现"基线对 diff>0 静默放行、无说明也过消费面"（红），落 `f09_red.log`；施工后全绿落 `f09_green.log`。

## 验收标准

- 新测试绿；`test_recon_deep_reverify.py`、`test_sixlens_receipts.py`、`test_handoff_manifest.py`、`test_audit_release_gate.py` 回归绿；`invariant_scan.py` 绿；`docs_lint.py --all` 绿；
- done 报告 `workorder_F09_done.md`：改动清单、四态证据、双写等价守卫说明、manifest 登记 diff、存量影响。

## 硬约束

- 只改：`scripts/evm/verify_recon.py`、`scripts/report/shared_release_receipt.py`（限对账区）、`references/data-pipeline-evm-recon.md`、`scripts/tests/invariant_manifest.json`（限 E 节）、新测试文件；名单外打红停下请示。
- 禁碰：VERSION、CHANGELOG、SKILL.md、r10_ledger.md、pyproject、run_all.py、contract_manifest/snapshot、audit_release_gate.py、handoff_manifest.py、shared 的 A4/adversarial 区、analyze-workflow.md。
- 禁止一切 git 操作。
