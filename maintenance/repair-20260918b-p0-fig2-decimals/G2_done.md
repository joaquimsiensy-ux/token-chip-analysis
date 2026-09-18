# 施工 G2：完成

工单：`workorder_G2_decimals.md` v4。开工与收工 HEAD：`6412d2e`，父提交 `5a3f6a6`，符合派工预期。四组新回归 RED→GREEN，20 项指定测试/守卫 PASS；本地 HTTP 纵切片因沙箱 EPERM，按 §0.8 例外交由调度方本机补验。

## §0.1 基线校验实录

命令一：

```sh
git status --short
```

exit 0，stdout 为空：

```text
```

命令二：

```sh
git diff --stat f1f473f3 HEAD -- scripts/lib/evm_observation.py scripts/evm scripts/lib/supply_truth_gate.py scripts/report/shared_release_receipt.py scripts/report/audit_release_gate.py scripts/tests/invariant_manifest.json scripts/tests/contract_manifest.json references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md
```

exit 0，stdout 为空：

```text
```

开工字节数（只 stat，不读取受限文档内容）：SKILL.md＝8021；commands-staging/*.md＝8798；references/**/*.md＝930061。

## 开工核实

- §2 指定整行锚用 `grep -n -F -x`、片段锚用 `grep -n -F` 核对，位置符合基线；shared_release_receipt.py 两个 schema 锚按 12/8 空格区分，分别唯一命中 1356/1761。
- accounting_gate.py:480 工单提供的是片段锚，实际行末还有中文注释。首轮误用 `-x` 未命中；按 §0.5 改用片段匹配 `grep -n -F` 后唯一命中 480，未改锚点或代码。
- test_handoff_manifest.py:157 的整行锚唯一，所在块为 149–159，无需块定位兜底。
- test_recon_deep_reverify.py:154 修改 balance 对账 transcript 的 result；:400 修改 time_spotcheck 证据块参数，均不属于 EVM observation transcript，不改。
- `rg -n '\bSEL_DECIMALS\b' scripts --glob '*.py' --glob '!__pycache__/**'` 仅命中 accounting_gate.py:74 定义，零使用。
- checks 非对象回归选在 test_review_20260804_p105.py；既有 a 例保留。

## 禁读披露

未读取 `~/.codex/`（包括 memories），未主动阅读、引用或改动任何指定禁区。未联网、未读取 API 密钥。§0.2 例外已由 docs_lint.py --all 与 test_repair_batch3_gates.py 的既有进程触发，详见下文。

## 施工结果与 RED→GREEN

已按 §2 修改 6 个生产文件、8 个测试文件、2 个清单、3 个文档。EVM 在同一冻结块哈希上采集 decimals()，bundle schema 升为 v2；transcript 固定为 9 笔；会计与发布校验沿已验证 bundle 读取 decimals，并同时约束 facts 与 verify_recon config。

RED 原始命令、异常全文和被测文件 SHA256 见 `G2_red_evidence.txt`，写入 RED 证据后才修改生产文件。取证前再次运行六个生产文件的 `git diff --exit-code`，exit 0、stdout 为空。

| 新用例 | 改前 RED | 改后 GREEN |
| --- | --- | --- |
| decimals 观测 / uint8 | 缺字段 KeyError；256 未拒收导致 AssertionError（分别取证） | 观测为 18；256 抛 uint8 错误 |
| accounting 与 bundle 不同 | checks.decimals 改为 2 仍通过公共 validator | ValueError 含 checks.decimals |
| c 例 facts/config 同改 2 | 完整 new-analysis 明确断言 errors == []；新双拒断言失败 | 同时出现 facts 与 config 对观测 0 的两条拒收 |
| EVM checks 非对象 | 合法 EVM 绑定，checks 改成列表仍 errors=[]，新断言失败 | 正常返回 checks 非对象错误，不抛异常 |

既有 a 例（facts=2、config=0）保持不动；RED 取证也实际验证了基线原本就拒收该例，不把它当成新修复的 RED。

关键 GREEN 原文：

```text
G2 c gate.run errors=['facts.token.decimals=2 与链上观测 0 不一致——state_source.facts_inputs.decimals 填错', 'verify_recon config.decimals=2 与链上观测 0 不一致——对账 human 供应量级自报']
PASS: G2 facts/config decimals 同改仍按观测双拒
G2 checks 非对象 errors=['facts.token.decimals 无链上观测来源可核（accounting_mode.checks.decimals 缺失或 checks 非对象）']
PASS: G2 EVM checks 非对象拒收且不抛异常
```

## §0.8 定向测试与守卫

各行均以 `PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/<文件>` 运行；docs_lint 加 `--all`。以下尾行来自实际进程输出。未运行 run_all.py。

| 脚本 | 结果 / exit | 输出尾行 |
| --- | --- | --- |
| `invariant_scan.py` | PASS / 0 | PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0 |
| `test_evm_observation.py` | PASS / 0 | PASS EVM observation bundle protocol: 11/11 |
| `test_evm_observation_nonempty_code.py` | PASS / 0 | PASS F-04 EVM nonempty code and ABI word checks: 5/5 |
| `test_evm_observation_release.py` | PASS / 0 | PASS workorder C EVM observation release: 12/12 |
| `test_supply_truth_gate.py` | PASS / 0 | supply_truth_gate 形态①/②离线契约测试全部通过 |
| `test_audit_release_gate.py` | PASS / 0 | PASS: audit_release_gate 净室资产/哈希/CEX受益权/阴性结论/图表封口与负钳零/对抗复核否决/四查WARN拦截/双线阈值/嵌套未决暴露/静置仓全集对账/日级峰值口径闭环十一类契约全过 |
| `test_handoff_manifest.py` | PASS / 0 | handoff_manifest 契约测试全部通过（283 项） |
| `test_review_20260804_p105.py` | PASS / 0 | PASS: P1-05 mandatory new-analysis vs independent-audit release profiles |
| `test_batch3_evm_vertical_slice.py` | 环境受限 / 1 | PermissionError: [Errno 1] Operation not permitted |
| `test_repair_batch_a.py` | PASS / 0 | PASS batch A F-01/F-02 regressions 45/45 |
| `test_repair_batch_d.py` | PASS / 0 | BATCH D 全部通过 |
| `test_batch13_accounting_target.py` | PASS / 0 | PASS batch13 accounting target regressions: 8/8 |
| `test_batch14_accounting_bundle_fallback.py` | PASS / 0 | batch14 tests=9 failed=0 |
| `test_recon_fifth_check.py` | PASS / 0 | GREEN 22 wave-scan/v4 与 flow-anomaly/v2 旧产物被 v5/v3 验收拒收 |
| `test_recon_deep_reverify.py` | PASS / 0 | PASS test_recon_deep_reverify |
| `test_batch11_frozen_bundle_binding.py` | PASS / 0 | PASS batch11 frozen/live binding regressions |
| `test_a4_gate.py` | PASS / 0 | a4_gate 契约测试全部通过（23 项） |
| `test_contract_routes.py` | PASS / 0 | PASS: R-01/R-02 注册表、ID 快照、五组锚与 SKILL 原子阶段双向闭合 |
| `test_commands_deploy_sync.py` | PASS / 0 | PASS: 4 份 staging/部署命令 SHA-256 逐文件一致 |
| `test_repair_batch3_gates.py` | PASS / 0 | PASS: 批3 deploy-sync/env-check/R10-ledger gates 回归全部通过 |
| `docs_lint.py --all` | PASS / 0 | PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式） |

纵切片按 §0.8 的明确例外处理：真实启动 `test_batch3_evm_vertical_slice.py`，在 `ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)` 的 socket.bind 阶段抛出 `PermissionError: [Errno 1] Operation not permitted`。没有绕过沙箱或改写测试；该项需调度方本机补验，不能计为 PASS。

补充执行 §1.3–§1.5 的离线断言（使用临时夹具，未增改仓库源码）：9 笔方法/seq 顺序、decimals 的 seq 6、所有状态读取共享冻结选择器、0/18/255 合法；bool、字符串、浮点、缺失、负数、256 拒收；旧 v1 schema 拒收。

```text
PASS G2 hard constraints: 9-call order/frozen selector; uint8 boundaries 0/18/255; invalid bool/non-int/missing/range rejected; legacy v1 rejected
```

## §1.1 文档字节数

仅通过 stat 统计大小；references/attic.md 不读内容。

| 范围 | 开工 | 改后 | 差额 |
| --- | ---: | ---: | ---: |
| SKILL.md | 8021 | 8021 | 0 |
| commands-staging/*.md | 8798 | 8798 | 0 |
| references/**/*.md | 930061 | 930076 | +15 |

对两个清单和三个文档逐字节比对 HEAD，确认只有 §2.7 / §2.10 明示替换：invariant 六处、contract 一处 schema 替换；三文档各一处 schema 替换；仅 data-pipeline-evm-recon.md 增加文本「、`decimals()`」的 15 字节。

## §1.2 git diff --stat

```text
 references/data-pipeline-evm-recon.md              |  2 +-
 references/independent-audit-protocol.md           |  2 +-
 references/scan-schemas.md                         |  2 +-
 scripts/evm/accounting_gate.py                     |  6 +--
 scripts/evm/observe_supply.py                      |  2 +-
 scripts/lib/evm_observation.py                     | 31 ++++++++----
 scripts/lib/supply_truth_gate.py                   |  4 +-
 scripts/report/audit_release_gate.py               | 39 +++++++-------
 scripts/report/shared_release_receipt.py           |  6 ++-
 scripts/tests/contract_manifest.json               |  2 +-
 scripts/tests/invariant_manifest.json              | 12 ++---
 scripts/tests/test_audit_release_gate.py           |  2 +-
 scripts/tests/test_batch3_evm_vertical_slice.py    |  2 +
 scripts/tests/test_evm_observation.py              | 11 +++-
 .../tests/test_evm_observation_nonempty_code.py    |  5 +-
 scripts/tests/test_evm_observation_release.py      | 24 +++++++--
 scripts/tests/test_handoff_manifest.py             |  2 +-
 scripts/tests/test_review_20260804_p105.py         | 59 ++++++++++++++++++++++
 scripts/tests/test_supply_truth_gate.py            | 10 ++--
 19 files changed, 164 insertions(+), 59 deletions(-)
```

上述是 `git diff --stat` 原始输出；新建的 G2_done.md、G2_red_evidence.txt 为未跟踪报告文件，不计入该命令的统计。工作树路径均在 §0.3 白名单内。

## §1.3 旧 v1 零命中

实际命令：

```sh
grep -rn --exclude-dir=__pycache__ --exclude='*.pyc' --exclude=attic.md 'evm-observation-bundle/v1' scripts references SKILL.md commands-staging
```

exit 1 表示零命中；stdout 为空：

```text
```

未删除既有 __pycache__ / *.pyc。

## 工单差异、开工核实与读取例外

- 无实施范围扩张、无生产行为偏离；新增私有 helper 位于获准的 test_review_20260804_p105.py。其参数取 2 时以 Decimal(N) / 100 保持原 raw supply，重绑两份 config 输入、wrapper 子收据 SHA，并调用 create_bundle。
- 开工锚与 transcript 核实结果见前文。accounting_gate.py:480 按片段锚处理，保留原行末注释。
- shared_release_receipt 的 _recon_bound_reality 与 validate_evm_observation_source_chain 已用 AST 定位源片段与 HEAD 逐字比较，完全不变；其余 §0.4 文件未改。
- §0.2 读取例外已触发：test_repair_batch3_gates.py 通过既有测试进程读取历史 R10 台账；docs_lint.py --all 执行仓库 Markdown 遍历及其 attic、archive/evals 检查。两脚本均 PASS；施工方未主动阅读、引用或修改这些禁区文件。
- 未读 ~/.codex/ 或 memories；未读 Desktop、Documents；未主动读取 archive、blind-reviews、.staging_*、attic 或被排除的历史 maintenance 内容。统计 references 总字节时只 stat。
- 全程离线，不 commit、不 push、不部署，不执行 stash/checkout/reset，不改版本与技能正文。
- 无停工点。待调度方本机补验的唯一环境项为前述本地 HTTP 纵切片；其余 20 项指定测试/守卫均已完成并通过。

## §2 逐文件 git diff 原文

以下保留 `git diff --no-ext-diff` 的实际输出，按文件排列；只包含 §2 指定文件。

```diff
diff --git a/references/data-pipeline-evm-recon.md b/references/data-pipeline-evm-recon.md
index c88bb7d..4f851b9 100644
--- a/references/data-pipeline-evm-recon.md
+++ b/references/data-pipeline-evm-recon.md
@@ -33,7 +33,7 @@ python3 scripts/evm/verify_recon.py <原参数> \
 | 有差异、说明不合格 | exit 1，且不覆盖原黄灯收据 | 原黄灯仍阻断 |
 | 无差异、却给说明 | exit 1，拒绝预填说明 | 无说明的干净 PASS 收据正常放行 |
 
-**供给真值闸的两种销毁形态（EVM `supply-truth-receipt/v4`，Solana `supply-truth-receipt/v3`）**：EVM formal 必须先运行 `scripts/evm/observe_supply.py`，在冻结块以 EIP-1898 `blockHash` 选择器读取 `totalSupply()`、`balanceOf(ZERO)` 与 `balanceOf(dead)`，落 `evm-observation-bundle/v1`＋调用 transcript；`accounting-gate/v2` 与 supply_truth v4 必须绑定同一 bundle，正式消费阶段不再现场 RPC。主规则继续按形态①校验
+**供给真值闸的两种销毁形态（EVM `supply-truth-receipt/v4`，Solana `supply-truth-receipt/v3`）**：EVM formal 必须先运行 `scripts/evm/observe_supply.py`，在冻结块以 EIP-1898 `blockHash` 选择器读取 `totalSupply()`、`decimals()`、`balanceOf(ZERO)` 与 `balanceOf(dead)`，落 `evm-observation-bundle/v2`＋调用 transcript；`accounting-gate/v2` 与 supply_truth v4 必须绑定同一 bundle，正式消费阶段不再现场 RPC。主规则继续按形态①校验
 `mint_total − burn_total` 与 bundle 的冻结块 `totalSupply()`；只有主规则 FAIL、EVM replay_stats
 同时带齐 ZERO/dead 的流入、流出与净额拆分时，才自动尝试形态②。形态②必须 wei 级同时满足：
 `mint_total == totalSupply()`、ZERO 事件流入等于链上 `balanceOf(ZERO)`、dead 事件净流入
diff --git a/references/independent-audit-protocol.md b/references/independent-audit-protocol.md
index 0f9fa69..fd2ad28 100644
--- a/references/independent-audit-protocol.md
+++ b/references/independent-audit-protocol.md
@@ -163,7 +163,7 @@ review_completeness.py
 
 `accounting_mode.json` 必须是当前 `scripts/evm/accounting_gate.py` 的 `accounting-gate/v2`（Solana 为 `scripts/solana/accounting_gate_sol.py` 的 `accounting-gate/v1`）exit 0 产物，并带脚本自身的 `producer.path/sha256`。
   `reconciliation_report.json` 必须由当前 `scripts/report/reconciliation_report.py` 读取 job spec 后受控启动各链对账生产者生成（EVM 四查、Solana 五查；键序见 scan-schemas §14.10，逐查生产者见 scripts/report/shared_release_receipt.py 的 RECON_PRODUCERS）。runner 要求 receipt 执行前不存在，逐项记录子进程 exit，并绑定 v2 target、生产者与输入/receipt 哈希；wrapper 顶层绑定 runner 自身路径与当前 SHA-256。聚合器逐类解析 schema、target、观测和 verdict，并拒绝无 runner 绑定或绑定哈希不符的 wrapper；旧案须重跑对应生产者与 runner。这里是内容绑定，不是单机执行证明：蓄意手拼者若正确填写当前 runner path/SHA-256 并伪造相互自洽的观测，聚合器无法仅凭 wrapper 识别；防线的实际作用是把“疏忽即可绕过”提高为必须显式填哈希、编造观测的主动造假，并由仓库 git 历史追踪代码变更。案目录里的同名/复制脚本即使 SHA-256 相同也不是生产者。
-  **明示局限（EVM 侧链上供给）**：EVM formal 先由 `observe_supply.py` 在同一冻结块哈希上读取 `totalSupply`、ZERO 与 dead 余额，落 `evm-observation-bundle/v1` 和调用 transcript；随后 `accounting-gate/v2` 与 `supply-truth-receipt/v4` 绑定同一 bundle，消费侧再把 `onchain_total_supply`、锚块和 sink 数值对回 bundle，达到与 Solana `accounting-gate/v1`＋`supply-truth-receipt/v3` 的案内 N-2 对账等深。shared 发布与 stage-1 READY handoff 都调用同一公共 validator，不能从 split 路线绕过。**bundle 是内容绑定，不是块真实性或 producer 真执行证明**：蓄意手拼者仍可同步伪造案内块头、响应和哈希链；`blockHash` 与 transcript 的价值是让第三方可拿到独立公共节点外部验真，不能把案内自洽写成案外真实。故 F-02 的裸标量缺口已闭合，外部真实性锚仍是开放边界。
+  **明示局限（EVM 侧链上供给）**：EVM formal 先由 `observe_supply.py` 在同一冻结块哈希上读取 `totalSupply`、ZERO 与 dead 余额，落 `evm-observation-bundle/v2` 和调用 transcript；随后 `accounting-gate/v2` 与 `supply-truth-receipt/v4` 绑定同一 bundle，消费侧再把 `onchain_total_supply`、锚块和 sink 数值对回 bundle，达到与 Solana `accounting-gate/v1`＋`supply-truth-receipt/v3` 的案内 N-2 对账等深。shared 发布与 stage-1 READY handoff 都调用同一公共 validator，不能从 split 路线绕过。**bundle 是内容绑定，不是块真实性或 producer 真执行证明**：蓄意手拼者仍可同步伪造案内块头、响应和哈希链；`blockHash` 与 transcript 的价值是让第三方可拿到独立公共节点外部验真，不能把案内自洽写成案外真实。故 F-02 的裸标量缺口已闭合，外部真实性锚仍是开放边界。
   `adversarial_review.json` 必须为 `adversarial-review/v4`：`claim_registry` 以 path/size/sha256/schema 绑定案内 `a4_claims.json`；每路 `adversarial-review-artifact/v2` 都绑定同一 registry sha。实体归因怀疑者的 `results[]` 逐条携带 claim_id、三档 verdict、evidence 与 alternative_explanations；每条 evidence 至少 10 个实义白名单字符，全部 claim-review artifacts 的 claim_id 并集必须覆盖 registry 且不得越界。完整性批评者改交全局 `findings[]`＋`non_covered[]`，这两类文本及 alternative_explanations 仍只要求至少一个实义字符。实义白名单覆盖 ASCII 可打印、拉丁补充与扩展、通用标点、CJK、假名、韩文音节和全角段；不在覆盖面的语种（如俄文、阿拉伯文）与纯 emoji 文本会被拒。外语原文证据应附一行中文说明，或保留 URL/数字等覆盖面内字符；中英文工作流不受影响，claim_id 不得含空格。两类角色都必须通过当前 runner 启动并留下 `adversarial-review-execution/v1`。
 
   每份 execution receipt 成功落盘后，runner 立即向案根 `adversarial_review_ledger.jsonl` 追加一行 `review-ledger/v1`；`seq` 从 1 连续，`prev_line_sha` 绑定前一行原始字节 SHA-256，首行写 `GENESIS`。同 `receipt_path` 重跑时保留历史行、末行作为有效行。ledger 拒绝多个不同 `receipt_path` 字符串指向同一实物文件，receipt 文件名只允许 ASCII 字母、数字、点、下划线与连字符。finalize 在 blocker 联动校验之后验证整条链，并要求有效行数量、有效 receipt SHA 数量与传入 receipts 数量相等，且 receipt SHA 集与传入 receipts 的磁盘字节 SHA 集精确相等；有效行还必须绑定当前 receipt 字节、角色和 artifact SHA。聚合件必填 `review_ledger={entries,active,tip_sha}`，shared validator 与委托它的 audit gate 会从 ledger 实物重算链、有效集、entries/active/tip_sha，并对有效行数量、有效 receipt SHA 数量与 aggregate reviews 数量做基数对账后再核 receipt SHA 集。
diff --git a/references/scan-schemas.md b/references/scan-schemas.md
index a55d788..f635bb2 100644
--- a/references/scan-schemas.md
+++ b/references/scan-schemas.md
@@ -385,7 +385,7 @@ TERMINAL = {
 
 闭合分母是 `mint_total` 不是 `onchain_total_supply`／`total_supply_raw`：replay 引擎对 sink 是记账不抹除，`sum(快照含 dead/zero) == mint_total` 恒成立——form2（转 dead 不减供给，`onchain==mint`）与 form1（真 `_burn`，`onchain==mint−burn`）都如此（APU／IQ／KOGE 真案逐 wei 实测）。若对 `onchain` 闭合，整类 form1 销毁币会被误杀。分母取值分链：EVM 取 `replay_stats.json` 的 `mint_total`（replay 产物，收据里有），Solana 取 `onchain_total_supply`（scanner `require_snapshot_closed` 已保证 `sum==supply` 精确，不套 EVM 的 replay mint 语义）。
 
-`total_supply_raw`／`frozen_total_supply_raw` 是**调用者可注入的影子键**（真实生产者 `supply_truth_gate` 只写 `onchain_total_supply`／`replay_net`／`mint_total`／`burn_total`）——闭合分母绝不取影子键，`net`（分布百分比分母）也优先取真实键 `replay_net`／`onchain_total_supply`。EVM formal 的 `onchain_total_supply` 来自已验证 `evm-observation-bundle/v1` 的冻结块 `total_supply_raw` 并由 `supply-truth-receipt/v4` 绑定，不再是消费时现场 RPC 自报；`net` 仍只用于分布百分比。冻结点后的链上销毁可令观测时点 `onchain_total_supply` 略低于冻结点 `replay_net`：扫描器仅在同一收据为 PASS/exit 0、`diff == replay_net-onchain_total_supply` 逐 raw 相等且 `diff*10000 <= tolerance_bps*onchain_total_supply` 时接受，并在 `denominators.supply_drift_raw` 留痕；任一字段缺失、失配或超容差仍 fail-closed。该交叉检查全程用整数运算，不改变 `net` 的分布百分比分母身份，也不放宽 Solana owner 快照对 `onchain` 的精确闭合。
+`total_supply_raw`／`frozen_total_supply_raw` 是**调用者可注入的影子键**（真实生产者 `supply_truth_gate` 只写 `onchain_total_supply`／`replay_net`／`mint_total`／`burn_total`）——闭合分母绝不取影子键，`net`（分布百分比分母）也优先取真实键 `replay_net`／`onchain_total_supply`。EVM formal 的 `onchain_total_supply` 来自已验证 `evm-observation-bundle/v2` 的冻结块 `total_supply_raw` 并由 `supply-truth-receipt/v4` 绑定，不再是消费时现场 RPC 自报；`net` 仍只用于分布百分比。冻结点后的链上销毁可令观测时点 `onchain_total_supply` 略低于冻结点 `replay_net`：扫描器仅在同一收据为 PASS/exit 0、`diff == replay_net-onchain_total_supply` 逐 raw 相等且 `diff*10000 <= tolerance_bps*onchain_total_supply` 时接受，并在 `denominators.supply_drift_raw` 留痕；任一字段缺失、失配或超容差仍 fail-closed。该交叉检查全程用整数运算，不改变 `net` 的分布百分比分母身份，也不放宽 Solana owner 快照对 `onchain` 的精确闭合。
 
 **闭合锚点的取值顺序（已绑定已验证的链路优先）**：① `supply_truth` 收据 `inputs.replay_stats` **绑定**的那份实物（已过 receipt 三验＋案根遏制，取值后再交叉验 `mint−burn == replay_net`）；② 收据的 `mint_total` 字段；③ `onchain_total_supply`。**案根裸 `replay_stats.json` 永远不是锚点来源**——真案 9/10 把它放 `data/`／`out/`／`replay/` 子目录并由收据绑定，把案根硬编码文件名排在第一，既让"抹平快照＋伪造一份未绑定案根件"直接过闸，又让"案根留一份陈旧件"把合法案误杀。合法但未绑定的案根同名件**忽略**（未绑定的文件不是证据，不该被采用，也不该有一票否决权）；它若**在场却非法**（符号链接／非普通文件）则 fail-closed 拒，与上面"在场非法不得静默漂白"同一把尺子。
 
diff --git a/scripts/evm/accounting_gate.py b/scripts/evm/accounting_gate.py
index 638138b..c73822f 100644
--- a/scripts/evm/accounting_gate.py
+++ b/scripts/evm/accounting_gate.py
@@ -71,9 +71,8 @@ SLOT_BEACON = "0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d5
 SEL_BALANCE = "0x70a08231"   # balanceOf(address)
 SEL_TOTSUP = "0x18160ddd"    # totalSupply()
 SEL_TRANSFER = "0xa9059cbb"  # transfer(address,uint256)
-SEL_DECIMALS = "0x313ce567"  # decimals()
 PROBE_ADDR = "0x0000000000000000000000000000000000012345"  # 模拟转账收款探针（无私钥地址）
-EVM_OBSERVATION_SCHEMA = "evm-observation-bundle/v1"
+EVM_OBSERVATION_SCHEMA = "evm-observation-bundle/v2"
 RECEIPT_SCHEMA_BY_MODE = {
     "formal": {"schema": "accounting-gate/v2"},
     "exploration": {"schema": "accounting-gate/v1"},
@@ -401,7 +400,7 @@ def main(argv=None):
     ap.add_argument("--samples", type=int, default=8)
     ap.add_argument("--sourcify", default="https://sourcify.dev/server")
     ap.add_argument("--out", default="accounting_mode.json")
-    ap.add_argument("--bundle", help="formal evm-observation-bundle/v1")
+    ap.add_argument("--bundle", help="formal evm-observation-bundle/v2")
     ap.add_argument("--exploration", action="store_true",
                     help="允许独立现场探测；formal 聚合器拒收 exploration")
     ap.add_argument("--as-of-block", type=int, default=None,
@@ -477,6 +476,7 @@ def main(argv=None):
             result["observed_anchor"] = {
                 "block": anchor["number"], "block_hash": anchor["block_hash"],
             }
+            result["checks"]["decimals"] = bundle["supply"]["decimals"]
         except Exception as exc:  # noqa: BLE001 - 观测件非法统一落同路径 FAIL 状态
             result["reasons"].append(str(exc))
             finish("unknown", "FAIL", 1)
diff --git a/scripts/evm/observe_supply.py b/scripts/evm/observe_supply.py
index ade9dcd..a33a96e 100644
--- a/scripts/evm/observe_supply.py
+++ b/scripts/evm/observe_supply.py
@@ -26,7 +26,7 @@ from receipt_kernel import (assert_distinct_paths, build_envelope,
                             publish_error_receipt, publish_txn)
 
 
-BUNDLE_SCHEMA = "evm-observation-bundle/v1"
+BUNDLE_SCHEMA = "evm-observation-bundle/v2"
 DEFAULT_RPC = {
     "eth": "https://ethereum-rpc.publicnode.com",
     "bsc": "https://bsc-dataseed.bnbchain.org",
diff --git a/scripts/lib/evm_observation.py b/scripts/lib/evm_observation.py
index 02a60cf..b77a5d0 100644
--- a/scripts/lib/evm_observation.py
+++ b/scripts/lib/evm_observation.py
@@ -4,6 +4,7 @@
 The bundle binds a normalized JSON-RPC request/result transcript, not proof
 that a remote node really executed the requests.  State reads use an EIP-1898
 canonical block-hash selector and fail closed when an endpoint cannot serve it.
+The same block also serves ``decimals()`` so consumers never take the token scale from caller config.
 """
 from __future__ import annotations
 
@@ -20,9 +21,10 @@ from solana_observation import assert_declared_slot
 from supply_semantics import DEAD, ZERO
 
 
-BUNDLE_SCHEMA = "evm-observation-bundle/v1"
+BUNDLE_SCHEMA = "evm-observation-bundle/v2"
 SEL_TOTSUP = "0x18160ddd"
 SEL_BALANCE = "0x70a08231"
+SEL_DECIMALS = "0x313ce567"
 BLOCK_BINDING = "eip1898-block-hash"
 _ADDRESS = re.compile(r"0x[0-9a-f]{40}")
 _HASH32 = re.compile(r"0x[0-9a-fA-F]{64}")
@@ -175,6 +177,7 @@ def observe_evm_supply(pool, chain, token, as_of_block, *, expected_chain_id):
                        "data": _balance_of_data(ZERO)}, block_selector]),
         ("eth_call", [{"to": canonical_token,
                        "data": _balance_of_data(DEAD)}, block_selector]),
+        ("eth_call", [{"to": canonical_token, "data": SEL_DECIMALS}, block_selector]),
     ]
     responses = pool.call_many(eth_calls, progress=False)
     _assert_endpoint(pool, attested_endpoint)
@@ -183,10 +186,13 @@ def observe_evm_supply(pool, chain, token, as_of_block, *, expected_chain_id):
     values = []
     for (method, params), response, label in zip(
             eth_calls, responses,
-            ("totalSupply", "balanceOf(ZERO)", "balanceOf(DEAD)")):
+            ("totalSupply", "balanceOf(ZERO)", "balanceOf(DEAD)", "decimals")):
         value, raw = _eth_call_value(response, label)
         _record(transcript, method, params, raw)
         values.append(value)
+    decimals = values[3]
+    if decimals > 255:
+        raise EvmObservationError(f"decimals() returned {decimals}, exceeds uint8")
 
     code_params = [canonical_token, block_selector]
     code_response = pool.call("eth_getCode", code_params)
@@ -225,6 +231,7 @@ def observe_evm_supply(pool, chain, token, as_of_block, *, expected_chain_id):
             "total_supply_raw": str(values[0]),
             "zero_balance_raw": str(values[1]),
             "dead_balance_raw": str(values[2]),
+            "decimals": decimals,
             "block_binding": BLOCK_BINDING,
         },
         "code": {"runtime_code_sha256": runtime_code_sha256},
@@ -260,11 +267,11 @@ def _transcript_path(bundle, bundle_path):
 
 
 def _validate_transcript(bundle, transcript):
-    if not isinstance(transcript, list) or len(transcript) != 8:
-        raise ValueError("observation transcript must contain exactly 8 calls")
+    if not isinstance(transcript, list) or len(transcript) != 9:
+        raise ValueError("observation transcript must contain exactly 9 calls")
     methods = [
         "eth_chainId", "eth_getBlockByNumber", "eth_blockNumber",
-        "eth_call", "eth_call", "eth_call", "eth_getCode",
+        "eth_call", "eth_call", "eth_call", "eth_call", "eth_getCode",
         "eth_getBlockByNumber",
     ]
     for index, (row, method) in enumerate(zip(transcript, methods)):
@@ -284,7 +291,7 @@ def _validate_transcript(bundle, transcript):
     if transcript[0]["params"] != []:
         raise ValueError("transcript eth_chainId params mismatch")
     if transcript[1]["params"] != expected_block_params \
-            or transcript[7]["params"] != expected_block_params:
+            or transcript[8]["params"] != expected_block_params:
         raise ValueError("transcript block params mismatch")
     if transcript[2]["params"] != []:
         raise ValueError("transcript eth_blockNumber params mismatch")
@@ -293,11 +300,12 @@ def _validate_transcript(bundle, transcript):
         [{"to": token, "data": SEL_TOTSUP}, selector],
         [{"to": token, "data": _balance_of_data(ZERO)}, selector],
         [{"to": token, "data": _balance_of_data(DEAD)}, selector],
+        [{"to": token, "data": SEL_DECIMALS}, selector],
     ]
     for offset, expected in enumerate(expected_call_params, start=3):
         if transcript[offset]["params"] != expected:
             raise ValueError(f"transcript eth_call params mismatch at seq {offset}")
-    if transcript[6]["params"] != [token, selector]:
+    if transcript[7]["params"] != [token, selector]:
         raise ValueError("transcript eth_getCode params mismatch")
 
     attestation = bundle["attestation"]
@@ -311,19 +319,19 @@ def _validate_transcript(bundle, transcript):
     if _quantity(transcript[2]["result"], "transcript tip") != anchor["tip_block"]:
         raise ValueError("transcript tip result mismatch")
     for offset, field in enumerate(
-            ("total_supply_raw", "zero_balance_raw", "dead_balance_raw"), start=3):
+            ("total_supply_raw", "zero_balance_raw", "dead_balance_raw", "decimals"), start=3):
         raw = transcript[offset]["result"]
         if not isinstance(raw, str) or not _HEX_VALUE.fullmatch(raw) \
                 or len(raw) != 66 or int(raw, 16) != int(supply[field]):
             raise ValueError(f"transcript {field} result mismatch")
-    code_raw = transcript[6]["result"]
+    code_raw = transcript[7]["result"]
     if not isinstance(code_raw, str) or not _HEX_DATA.fullmatch(code_raw) \
             or code_raw == "0x":
         raise ValueError("transcript eth_getCode result invalid")
     if hashlib.sha256(bytes.fromhex(code_raw[2:])).hexdigest() \
             != bundle["code"]["runtime_code_sha256"]:
         raise ValueError("transcript runtime code result mismatch")
-    recheck = _block(transcript[7]["result"], "transcript recheck block")
+    recheck = _block(transcript[8]["result"], "transcript recheck block")
     if recheck["number"] != anchor["number"] \
             or recheck["block_hash"] != anchor["recheck_block_hash"]:
         raise ValueError("transcript recheck block result mismatch")
@@ -390,6 +398,9 @@ def validate_evm_observation_bundle(
     supply = bundle.get("supply") or {}
     for field in ("total_supply_raw", "zero_balance_raw", "dead_balance_raw"):
         _non_negative_decimal(supply.get(field), f"supply.{field}")
+    decimals = supply.get("decimals")
+    if isinstance(decimals, bool) or not isinstance(decimals, int) or not 0 <= decimals <= 255:
+        raise ValueError("EVM observation bundle supply.decimals invalid (uint8 required)")
     if supply.get("block_binding") != BLOCK_BINDING:
         raise ValueError("EVM observation bundle supply block binding invalid")
     code = bundle.get("code") or {}
diff --git a/scripts/lib/supply_truth_gate.py b/scripts/lib/supply_truth_gate.py
index 86bbf78..3750a6c 100644
--- a/scripts/lib/supply_truth_gate.py
+++ b/scripts/lib/supply_truth_gate.py
@@ -89,7 +89,7 @@ WAIVER_TOLERANCE_BPS_CAP = 100
 TOLERANCE_WAIVER_SCHEMA = "tolerance-waiver/v1"
 OVER_CAP_APPROVAL_SCHEMA = "over-cap-approval/v1"
 SCHEMA_FAMILY = "supply-truth-receipt/"
-EVM_OBSERVATION_SCHEMA = "evm-observation-bundle/v1"
+EVM_OBSERVATION_SCHEMA = "evm-observation-bundle/v2"
 RECEIPT_SCHEMA_BY_MODE = {
     "formal_evm": {"schema": "supply-truth-receipt/v4"},
     "other": {"schema": "supply-truth-receipt/v3"},
@@ -538,7 +538,7 @@ def main(argv=None):
     ap.add_argument("--proxy")
     ap.add_argument("--observation-bundle",
                     help="formal 模式观测件：Solana=solana-observation-bundle/v1，"
-                         "EVM=evm-observation-bundle/v1")
+                         "EVM=evm-observation-bundle/v2")
     ap.add_argument("--min-context-slot", type=int, default=0,
                     help="Solana bundle snapshot lower-bound assertion")
     ap.add_argument("--tolerance-bps", type=int, default=10)
diff --git a/scripts/report/audit_release_gate.py b/scripts/report/audit_release_gate.py
index f8a4ef1..9442c59 100644
--- a/scripts/report/audit_release_gate.py
+++ b/scripts/report/audit_release_gate.py
@@ -1584,30 +1584,31 @@ def check_facts_vs_ledgers(case_dir: Path, facts, errors: list[str], receipt=Non
 
 
 def check_facts_decimals(case_dir: Path, facts, accounting, errors: list[str]):
-    """F05（7.2.1）：token.decimals 绑定链上观测——solana 家族取 accounting_mode.checks.decimals
-    （accounting_gate_sol 写出），evm 家族取 balance 对账收据绑定的 verify_recon config.decimals
-    （深验 witness 已缓存，不重跑）；取不到即拒，不让调用者自报数量单位。只挂 new-analysis，
-    不进共享 check_facts_vs_ledgers（stage2 收口/reseal 复用后者）。"""
+    """G2（repair-20260918b）：token.decimals 绑定链上观测——两链族一律取
+    accounting_mode.checks.decimals（solana 由 accounting_gate_sol 从 mint 写出；evm 由
+    accounting_gate 从 evm-observation-bundle/v2 的 supply.decimals 写出，
+    validate_accounting_receipt 已核其与 bundle 相等）；evm 另核 verify_recon config.decimals
+    与观测一致（human 供应量级不得自报）。取不到即拒。只挂 new-analysis。"""
     declared = ((facts or {}).get("token") or {}).get("decimals")
-    chain = str((accounting or {}).get("chain") or "")
-    observed = None
+    checks = (accounting or {}).get("checks") if isinstance(accounting, dict) else None
+    observed = checks.get("decimals") if isinstance(checks, dict) else None
+    if isinstance(observed, bool) or not isinstance(observed, int):
+        errors.append("facts.token.decimals 无链上观测来源可核（accounting_mode.checks.decimals 缺失或 checks 非对象）")
+        return
+    if declared != observed:
+        errors.append(f"facts.token.decimals={declared!r} 与链上观测 {observed} 不一致——state_source.facts_inputs.decimals 填错")
     try:
         import shared_release_receipt
-        family = shared_release_receipt.chain_family(chain)
-        if family == "solana":
-            observed = ((accounting or {}).get("checks") or {}).get("decimals")
-        else:
-            witness = _validate_reconciliation_report_once(case_dir)
-            bal = (witness.receipts or {}).get("balance") or {}
-            _, cfg = shared_release_receipt._bound_json_input(case_dir, bal, "config", "verify_recon config")
-            observed = cfg.get("decimals")
+        if shared_release_receipt.chain_family(str((accounting or {}).get("chain") or "")) != "evm":
+            return
+        witness = _validate_reconciliation_report_once(case_dir)
+        bal = (witness.receipts or {}).get("balance") or {}
+        _, cfg = shared_release_receipt._bound_json_input(case_dir, bal, "config", "verify_recon config")
     except Exception as exc:
-        errors.append(f"facts.token.decimals 无法取链上观测值: {exc}")
+        errors.append(f"verify_recon config.decimals 无法对链上观测: {exc}")
         return
-    if isinstance(observed, bool) or not isinstance(observed, int):
-        errors.append("facts.token.decimals 无链上观测来源可核（accounting_mode.checks/对账收据 config 缺 decimals）")
-    elif declared != observed:
-        errors.append(f"facts.token.decimals={declared!r} 与链上观测 {observed} 不一致——state_source.facts_inputs.decimals 填错")
+    if cfg.get("decimals") != observed:
+        errors.append(f"verify_recon config.decimals={cfg.get('decimals')!r} 与链上观测 {observed} 不一致——对账 human 供应量级自报")
 
 
 def check_figure2_receipt(case_dir: Path, d: dict, errors: list[str]):
diff --git a/scripts/report/shared_release_receipt.py b/scripts/report/shared_release_receipt.py
index 713d555..e3044c3 100644
--- a/scripts/report/shared_release_receipt.py
+++ b/scripts/report/shared_release_receipt.py
@@ -1353,7 +1353,7 @@ def validate_reconciliation_check(root, key, item, target, family):
             bundle_path = _bound_case_ref(
                 root, bundle_ref, "EVM supply_truth observation bundle")
             bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
-            _require(bundle.get("schema") == "evm-observation-bundle/v1",
+            _require(bundle.get("schema") == "evm-observation-bundle/v2",
                      "EVM supply_truth observation bundle schema invalid")
             from evm_observation import validate_evm_observation_bundle
             validate_evm_observation_bundle(
@@ -1758,7 +1758,7 @@ def validate_accounting_receipt(root, accounting=None, expected_target=None):
         bundle_path = _bound_case_ref(
             root, bundle_ref, "EVM accounting observation bundle")
         bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
-        _require(bundle.get("schema") == "evm-observation-bundle/v1",
+        _require(bundle.get("schema") == "evm-observation-bundle/v2",
                  "EVM accounting observation bundle schema invalid")
         from evm_observation import validate_evm_observation_bundle
         validate_evm_observation_bundle(
@@ -1773,6 +1773,8 @@ def validate_accounting_receipt(root, accounting=None, expected_target=None):
                  "EVM accounting observed anchor block mismatch")
         _require(observed.get("block_hash") == bundle["anchor"]["block_hash"],
                  "EVM accounting observed anchor block_hash mismatch")
+        _require(accounting["checks"].get("decimals") == bundle["supply"]["decimals"],
+                 "EVM accounting checks.decimals is not the bundle observed decimals")
         return target, accounting, sha(bundle_path)
 
     bundle_ref = accounting.get("observation_bundle")
diff --git a/scripts/tests/contract_manifest.json b/scripts/tests/contract_manifest.json
index d7829e2..4882fd9 100644
--- a/scripts/tests/contract_manifest.json
+++ b/scripts/tests/contract_manifest.json
@@ -147,7 +147,7 @@
     {"id":"CT-SEMANTIC-54","kind":"required","authority_file":"references/scan-schemas.md","needle":"flip-adjudications/v1","stages":["A3","A5"]},
     {"id":"CT-SEMANTIC-55","kind":"required","authority_file":"references/data-pipeline-solana-capture.md","needle":"NO_CLOSED_SAMPLED","stages":["A1-A2"]},
     {"id":"CT-SEMANTIC-56","kind":"required","authority_file":"references/analyze-workflow.md","needle":"supply_truth.json.superseded-","stages":["A2"]},
-    {"id":"CT-SEMANTIC-57","kind":"required","authority_file":"references/data-pipeline-evm-recon.md","needle":"evm-observation-bundle/v1","stages":["A2","A5"]},
+    {"id":"CT-SEMANTIC-57","kind":"required","authority_file":"references/data-pipeline-evm-recon.md","needle":"evm-observation-bundle/v2","stages":["A2","A5"]},
     {"id":"CT-SEMANTIC-58","kind":"required","authority_file":"references/data-pipeline-evm-recon.md","needle":"supply-truth-receipt/v4","stages":["A2","A5"]},
     {"id":"CT-SEMANTIC-59","kind":"required","authority_file":"references/data-pipeline-evm-recon.md","needle":"accounting-gate/v2","stages":["A2","A5"]},
     {"id":"CT-SEMANTIC-60","kind":"required","authority_file":"commands-staging/token-analyze-2.md","needle":"a5-report-seal/v3","stages":["A3-A5"]},
diff --git a/scripts/tests/invariant_manifest.json b/scripts/tests/invariant_manifest.json
index 5c13ed7..05aa987 100644
--- a/scripts/tests/invariant_manifest.json
+++ b/scripts/tests/invariant_manifest.json
@@ -60,7 +60,7 @@
   },
   {
    "schemas": [
-    "evm-observation-bundle/v1"
+    "evm-observation-bundle/v2"
    ],
    "script": "scripts/evm/observe_supply.py"
   },
@@ -104,7 +104,7 @@
   },
   {
    "schemas": [
-    "evm-observation-bundle/v1"
+    "evm-observation-bundle/v2"
    ],
    "script": "scripts/lib/evm_observation.py"
   },
@@ -348,7 +348,7 @@
  "receipt_consumers": [
   {
    "schemas": [
-    "evm-observation-bundle/v1"
+    "evm-observation-bundle/v2"
    ],
    "script": "scripts/evm/accounting_gate.py"
   },
@@ -398,7 +398,7 @@
   },
   {
    "schemas": [
-    "evm-observation-bundle/v1"
+    "evm-observation-bundle/v2"
    ],
    "script": "scripts/lib/evm_observation.py"
   },
@@ -417,7 +417,7 @@
   },
   {
    "schemas": [
-    "evm-observation-bundle/v1",
+    "evm-observation-bundle/v2",
     "over-cap-approval/v1",
     "tolerance-waiver/v1"
    ],
@@ -555,7 +555,7 @@
     "adversarial-review/v3",
     "adversarial-review/v4",
     "anchor-plan-receipt/v2",
-    "evm-observation-bundle/v1",
+    "evm-observation-bundle/v2",
     "evm-reconciliation-receipt/v3",
     "gmgn-divergence-note/v1",
     "over-cap-approval/v1",
diff --git a/scripts/tests/test_audit_release_gate.py b/scripts/tests/test_audit_release_gate.py
index 331b9de..9df1eb5 100644
--- a/scripts/tests/test_audit_release_gate.py
+++ b/scripts/tests/test_audit_release_gate.py
@@ -308,7 +308,7 @@ def build_case(root, historical=True):
         "execution_mode": "formal", "observation_bundle": bundle_abs,
         "observed_anchor": {"block": 123,
                             "block_hash": bundle["anchor"]["block_hash"]},
-        "checks": {"fot": {"status": "clean"}}})
+        "checks": {"fot": {"status": "clean"}, "decimals": 0}})
     producers = {"balance": "scripts/evm/verify_recon.py",
                  "supply": "scripts/evm/verify_recon.py",
                  "supply_truth": "scripts/lib/supply_truth_gate.py",
diff --git a/scripts/tests/test_batch3_evm_vertical_slice.py b/scripts/tests/test_batch3_evm_vertical_slice.py
index 943f9d3..a15599a 100644
--- a/scripts/tests/test_batch3_evm_vertical_slice.py
+++ b/scripts/tests/test_batch3_evm_vertical_slice.py
@@ -75,6 +75,8 @@ class FixtureHandler(BaseHTTPRequestHandler):
                 data = call.get("data", "")
                 if data.startswith("0x18160ddd"):
                     amount = type(self).supply
+                elif data.startswith("0x313ce567"):
+                    amount = 0
                 else:
                     address = "0x" + data[-40:]
                     block = params[1]
diff --git a/scripts/tests/test_evm_observation.py b/scripts/tests/test_evm_observation.py
index 52825e0..2295c21 100644
--- a/scripts/tests/test_evm_observation.py
+++ b/scripts/tests/test_evm_observation.py
@@ -48,7 +48,7 @@ class FakePool:
 
     def __init__(self, *, chain_id=CHAIN_ID, block_number=AS_OF,
                  invalid_call=False, reorg=False, eip1898_unsupported=False,
-                 endpoint_drift=False, endpoint="https://rpc.example.test"):
+                 endpoint_drift=False, endpoint="https://rpc.example.test", decimals=18):
         self.url = endpoint
         self.chain_id = chain_id
         self.block_number = block_number
@@ -56,6 +56,7 @@ class FakePool:
         self.reorg = reorg
         self.eip1898_unsupported = eip1898_unsupported
         self.endpoint_drift = endpoint_drift
+        self.decimals = decimals
         self.calls = []
         self.business_calls = 0
         self.block_reads = 0
@@ -84,7 +85,7 @@ class FakePool:
             if self.eip1898_unsupported:
                 return {"ok": False, "error": "rpc -32602: unsupported blockHash selector"}
             selector = params[0]["data"][:10]
-            values = {"0x18160ddd": 1_000_000, "0x70a08231": 7}
+            values = {"0x18160ddd": 1_000_000, "0x70a08231": 7, "0x313ce567": self.decimals}
             raw = "not-hex" if self.invalid_call else f"0x{values[selector]:064x}"
             return {"ok": True, "result": raw}
         if method == "eth_getCode":
@@ -133,6 +134,11 @@ def test_invalid_eth_call_result_rejected():
     expect_error(lambda: observe(FakePool(invalid_call=True)), "invalid")
 
 
+def test_decimals_observed_and_uint8_enforced():
+    assert observe()["supply"]["decimals"] == 18
+    expect_error(lambda: observe(FakePool(decimals=256)), "uint8")
+
+
 def test_pre_post_block_hash_mismatch_rejected():
     expect_error(lambda: observe(FakePool(reorg=True)), "recheck")
 
@@ -249,6 +255,7 @@ def main():
     tests = [
         test_wrong_chain_id_zero_business_calls,
         test_invalid_eth_call_result_rejected,
+        test_decimals_observed_and_uint8_enforced,
         test_pre_post_block_hash_mismatch_rejected,
         test_eip1898_unsupported_fails_closed_without_outputs,
         test_declared_as_of_block_mismatch_rejected,
diff --git a/scripts/tests/test_evm_observation_nonempty_code.py b/scripts/tests/test_evm_observation_nonempty_code.py
index fd2ecdb..9f894f5 100644
--- a/scripts/tests/test_evm_observation_nonempty_code.py
+++ b/scripts/tests/test_evm_observation_nonempty_code.py
@@ -99,7 +99,7 @@ def test_empty_runtime_code_hash_rejected_by_validator():
     core = observe()
     core["code"]["runtime_code_sha256"] = EMPTY_CODE_SHA256
     transcript = copy.deepcopy(core["_transcript"])
-    transcript[6]["result"] = "0x"
+    transcript[7]["result"] = "0x"
     with tempfile.TemporaryDirectory(prefix="evm-empty-code-hash-") as raw:
         case = Path(raw)
         bundle, bundle_path = persist_bundle(case, core, transcript)
@@ -113,7 +113,7 @@ def test_empty_runtime_code_hash_rejected_by_validator():
 def test_legacy_getcode_block_number_rejected_by_transcript_validator():
     core = observe()
     transcript = copy.deepcopy(core["_transcript"])
-    transcript[6]["params"] = [TOKEN, hex(AS_OF)]
+    transcript[7]["params"] = [TOKEN, hex(AS_OF)]
     with tempfile.TemporaryDirectory(prefix="evm-getcode-selector-") as raw:
         case = Path(raw)
         bundle, bundle_path = persist_bundle(case, core, transcript)
@@ -130,6 +130,7 @@ def test_zero_supply_deployed_contract_passes_full_chain():
         "total_supply_raw": "0",
         "zero_balance_raw": "0",
         "dead_balance_raw": "0",
+        "decimals": 0,
         "block_binding": "eip1898-block-hash",
     }
     assert core["code"]["runtime_code_sha256"] != EMPTY_CODE_SHA256
diff --git a/scripts/tests/test_evm_observation_release.py b/scripts/tests/test_evm_observation_release.py
index 9bea39a..4999420 100644
--- a/scripts/tests/test_evm_observation_release.py
+++ b/scripts/tests/test_evm_observation_release.py
@@ -61,13 +61,13 @@ def write_evm_bundle(root: Path, **kwargs) -> Path:
     if not transcript_path.is_absolute():
         transcript_path = root / transcript_path
     transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
-    for row in transcript[3:6]:
+    for row in transcript[3:7]:
         row["result"] = f"0x{int(row['result'], 16):064x}"
     selector = {
         "blockHash": bundle["anchor"]["block_hash"],
         "requireCanonical": True,
     }
-    transcript[6]["params"] = [bundle["target"]["token"], selector]
+    transcript[7]["params"] = [bundle["target"]["token"], selector]
     write(transcript_path, transcript)
     bundle["inputs"]["transcript"] = file_ref(
         transcript_path, shown=transcript_ref["path"])
@@ -109,7 +109,7 @@ def build_case(root: Path) -> dict:
         "observation_bundle": bundle_abs,
         "observed_anchor": {"block": AS_OF,
                             "block_hash": bundle["anchor"]["block_hash"]},
-        "checks": {"proxy": {"is_proxy": False}},
+        "checks": {"proxy": {"is_proxy": False}, "decimals": 0},
         "verdict": "PASS", "exit_code": 0,
     }
     write(root / "accounting_mode.json", accounting)
@@ -228,6 +228,23 @@ def test_accounting_anchor_mismatch_rejected():
                      "bundle anchor mismatch")
 
 
+def test_accounting_decimals_must_match_bundle():
+    with tempfile.TemporaryDirectory(prefix="evm-release-accounting-decimals-") as raw:
+        root = Path(raw)
+        build_case(root)
+        path = root / "accounting_mode.json"
+        accounting = json.loads(path.read_text(encoding="utf-8"))
+        accounting["checks"]["decimals"] = 2
+        write(path, accounting)
+        refresh_wrapper(root)
+        try:
+            shared.validate_accounting_receipt(root)
+        except ValueError as exc:
+            assert "checks.decimals" in str(exc), str(exc)
+        else:
+            raise AssertionError("accounting checks.decimals=2 accepted against bundle decimals=0")
+
+
 def test_supply_missing_bundle_rejected():
     with tempfile.TemporaryDirectory(prefix="evm-release-supply-missing-") as raw:
         root = Path(raw)
@@ -434,6 +451,7 @@ def main() -> int:
     tests = (
         test_accounting_missing_bundle_rejected,
         test_accounting_anchor_mismatch_rejected,
+        test_accounting_decimals_must_match_bundle,
         test_supply_missing_bundle_rejected,
         test_supply_n2_mismatch_rejected,
         test_accounting_supply_bundle_same_source_rejected,
diff --git a/scripts/tests/test_handoff_manifest.py b/scripts/tests/test_handoff_manifest.py
index 8024d8f..aeb8f72 100644
--- a/scripts/tests/test_handoff_manifest.py
+++ b/scripts/tests/test_handoff_manifest.py
@@ -154,7 +154,7 @@ def make_case(d, chain="eth", token=TOKEN, as_of_block=999):
         "observation_bundle": bundle_ref,
         "observed_anchor": {"block": as_of_block,
                             "block_hash": bundle["anchor"]["block_hash"]},
-        "checks": {"proxy": {"is_proxy": False}},
+        "checks": {"proxy": {"is_proxy": False}, "decimals": 0},
         "verdict": "PASS", "exit_code": 0,
     })
 
diff --git a/scripts/tests/test_review_20260804_p105.py b/scripts/tests/test_review_20260804_p105.py
index ce6d438..a7d598e 100644
--- a/scripts/tests/test_review_20260804_p105.py
+++ b/scripts/tests/test_review_20260804_p105.py
@@ -8,6 +8,7 @@ import json
 import subprocess
 import sys
 import tempfile
+from decimal import Decimal
 from pathlib import Path
 
 HERE = Path(__file__).resolve().parent
@@ -251,6 +252,61 @@ def add_new_analysis_distribution(root: Path, report: Path, decimals=0) -> None:
     assert p.returncode == 0, p.stdout + p.stderr
 
 
+def _rebind_config_decimals(root: Path, decimals: int) -> None:
+    path = root / "fixture_recon_config.json"
+    config = json.loads(path.read_text(encoding="utf-8"))
+    total = int(config["total_supply_human"])
+    config["decimals"] = decimals
+    config["total_supply_human"] = str(Decimal(total) / (10 ** decimals))
+    write_json(path, config)
+    wrapper_path = root / "reconciliation_report.json"
+    wrapper = json.loads(wrapper_path.read_text(encoding="utf-8"))
+    for key in ("balance", "supply"):
+        receipt_path = root / f"{key}_receipt.json"
+        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
+        receipt["inputs"]["config"] = fixture.artifact_ref(root, path)
+        write_json(receipt_path, receipt)
+        wrapper["checks"][key]["receipt"]["sha256"] = sha(receipt_path)
+    write_json(wrapper_path, wrapper)
+    from shared_release_receipt import create_bundle
+    create_bundle(root)
+
+
+def test_selfreported_decimals_rejected():
+    with tempfile.TemporaryDirectory() as td:
+        root = Path(td)
+        report = fixture.build_case(root, historical=False)
+        add_new_analysis_distribution(root, report, decimals=2)
+        _rebind_config_decimals(root, 2)
+        errors = fixture.gate.run(root, report, profile="new-analysis")
+        print(f"G2 c gate.run errors={errors!r}", flush=True)
+        assert any("facts.token.decimals=2 与链上观测 0 不一致" in error
+                   for error in errors), errors
+        assert any("verify_recon config.decimals=2 与链上观测 0 不一致" in error
+                   for error in errors), errors
+        print("PASS: G2 facts/config decimals 同改仍按观测双拒", flush=True)
+
+
+def test_evm_decimals_checks_non_object_rejected():
+    with tempfile.TemporaryDirectory() as td:
+        root = Path(td)
+        report = fixture.build_case(root, historical=False)
+        add_new_analysis_distribution(root, report, decimals=0)
+        facts = json.loads((root / "facts.json").read_text(encoding="utf-8"))
+        path = root / "accounting_mode.json"
+        accounting = json.loads(path.read_text(encoding="utf-8"))
+        errors = []
+        fixture.gate.check_facts_decimals(root, facts, accounting, errors)
+        assert errors == [], errors
+        accounting["checks"] = ["mistyped"]
+        write_json(path, accounting)
+        errors = []
+        fixture.gate.check_facts_decimals(root, facts, accounting, errors)
+        print(f"G2 checks 非对象 errors={errors!r}", flush=True)
+        assert any("checks 非对象" in error for error in errors), errors
+        print("PASS: G2 EVM checks 非对象拒收且不抛异常", flush=True)
+
+
 def main():
     with tempfile.TemporaryDirectory() as td:
         root = Path(td)
@@ -284,6 +340,9 @@ def main():
         assert errors == [], errors
         print("PASS: F05 decimals 一致放行（GREEN→GREEN）", flush=True)
 
+    test_selfreported_decimals_rejected()
+    test_evm_decimals_checks_non_object_rejected()
+
     print("PASS: P1-05 mandatory new-analysis vs independent-audit release profiles")
     return 0
 
diff --git a/scripts/tests/test_supply_truth_gate.py b/scripts/tests/test_supply_truth_gate.py
index 4533a97..9d61bcd 100644
--- a/scripts/tests/test_supply_truth_gate.py
+++ b/scripts/tests/test_supply_truth_gate.py
@@ -85,7 +85,7 @@ def split_stats(mint=APU_MINT, burn=APU_DEAD, zero=0, dead=APU_DEAD):
 
 
 def write_evm_bundle(root, *, token=TOKEN, chain="eth", as_of=123,
-                     total=APU_MINT, zero=0, dead=APU_DEAD):
+                     total=APU_MINT, zero=0, dead=APU_DEAD, decimals=0):
     """落一份通过工单 A 公共 validator 的 EVM 观测实物。"""
     endpoint = "https://rpc.example.test"
     block = {
@@ -112,9 +112,12 @@ def write_evm_bundle(root, *, token=TOKEN, chain="eth", as_of=123,
         {"seq": 5, "method": "eth_call",
          "params": [{"to": token, "data": balance(DEAD)}, selector],
          "result": word(dead)},
-        {"seq": 6, "method": "eth_getCode", "params": [token, selector],
+        {"seq": 6, "method": "eth_call",
+         "params": [{"to": token, "data": "0x313ce567"}, selector],
+         "result": word(decimals)},
+        {"seq": 7, "method": "eth_getCode", "params": [token, selector],
          "result": RUNTIME_CODE},
-        {"seq": 7, "method": "eth_getBlockByNumber",
+        {"seq": 8, "method": "eth_getBlockByNumber",
          "params": [hex(as_of), False], "result": block},
     ]
     transcript_path = root / "evm_observation_transcript.json"
@@ -133,6 +136,7 @@ def write_evm_bundle(root, *, token=TOKEN, chain="eth", as_of=123,
         "supply": {
             "total_supply_raw": str(total), "zero_balance_raw": str(zero),
             "dead_balance_raw": str(dead),
+            "decimals": decimals,
             "block_binding": "eip1898-block-hash",
         },
         "code": {"runtime_code_sha256": hashlib.sha256(
```
