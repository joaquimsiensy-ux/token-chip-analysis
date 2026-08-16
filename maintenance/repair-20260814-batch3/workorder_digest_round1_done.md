# 消化轮 1 完工记录（BR1-01 / BR1-02 / BR1-03）

## 结论

本工单三项 finding 已按裁判定案落地：

- BR1-01：受控 run-role 每次成功 execution receipt 都追加到案根 `adversarial_review_ledger.jsonl` 的 `review-ledger/v1` 哈希链；finalize 对 ledger 当前有效 receipt SHA 集与传入 receipts 做精确集合对账，`adversarial-review/v4` 新增必填 `review_ledger.entries/active/tip_sha`；shared validator 从实物独立重验，audit 保持委托 shared。
- BR1-02：`test_commands_deploy_sync.py` 的 canonical home 和 deployed 根改为 `pwd.getpwuid(os.getuid()).pw_dir`，本文件内 `Path.home()` 清零；伪造进程 `HOME` 不再触发 rc0 SKIP。
- BR1-03：R10 台账守卫按节解析合法状态列，正文列的状态样式、无全角括号的版本状态字样、重复当前现役声明均 fail-closed；历史建档句不再参与现役数字对账。

未执行任何 git 写命令，未改版本件、CHANGELOG 或本工单禁触文件。`sync-from-cc.sh` 只存在于 Codex skill 侧且会执行 git merge/commit 类写操作，与本单“禁一切 git 写命令”冲突，因此未运行。

## 先红清单

所有临时复现脚本均写在 `/tmp`。生产代码未修改时先运行 `/tmp/digest_round1_red.py`，真实输出为：

```text
BR1-01_HEAD {
  role_rcs: [0, 0, 0],
  bad_artifact_exists: True,
  bad_receipt_exists: True,
  finalize_rc: 0,
  decision: PASS,
  shared_message: "",
  audit_errors: []
}
BR1-02_HEAD {
  rc: 0,
  stdout: "SKIP_NON_CANONICAL_CHECKOUT: /Users/uravvv/.claude/skills/token-chip-analysis"
}
BR1-03_HEAD {
  body_marker_failures: [],
  bare_status_failures: [],
  duplicate_active_failures: []
}
```

其中 duplicate-active 使用第二条同值 **19**，专门证明旧实现的 last-match-wins 会接受重复声明；正式回归按工单再覆盖第二条 **18**，要求命中“声明必须恰好一条”，而不是偶然命中数字不一致。

将新反例先写入正式测试、尚未改生产实现时：

```text
python3 scripts/tests/test_repair_batch3_f01.py
exit code: 1
9 failures: 省略不利 receipt；删中间行；改前行不重算 prev；
未登记 receipt；同路径重跑；ledger 缺失；aggregate tip 篡改；
ledger 末行篡改；正常 aggregate 缺 review_ledger 绑定。

python3 scripts/tests/test_repair_batch3_gates.py
exit code: 1
3 failures: 伪 HOME 仍 SKIP；正文状态样式仍被当状态；裸 CLOSED 仍被当 OPEN。
```

## 修后反例重放

同一 `/tmp/digest_round1_red.py` 在最终工作树重放：

```text
BR1-01: 三路 run-role 仍 rc0、坏件仍在盘；finalize rc2；
BLOCK: review ledger active receipt set differs from finalize receipts；
adversarial_review.json 未落盘。

BR1-02: HOME=<tmp> 后 rc0；输出为
PASS: 3 份 staging/部署命令 SHA-256 逐文件一致；
不含 SKIP_NON_CANONICAL_CHECKOUT。

BR1-03:
R10-8 正文注入 → “正文列出现状态样式标记”；
R10-1 裸 CLOSED → “状态字样未按枚举格式”；
追加第二条当前现役 → “当前现役声明必须恰好一条：实际 2 条”。
```

## 修后测试证据

```text
python3 scripts/tests/test_repair_batch3_f01.py
exit code: 0
末行: all batch3 F01 tests passed

python3 scripts/tests/test_repair_batch3_gates.py
exit code: 0
末行: PASS: 批3 deploy-sync/env-check/R10-ledger gates 回归全部通过

python3 scripts/tests/test_repair_batch2_f02.py
exit code: 0
末行: PASS workorder B F-02 regressions

python3 scripts/tests/test_review_20260804_p105.py
exit code: 0
末行: PASS: P1-05 mandatory new-analysis vs independent-audit release profiles

python3 scripts/tests/invariant_scan.py
exit code: 0
末行: PASS invariant manifest: receipt_producers=58, receipt_consumers=78,
transport_calls=62, atomic_writes=51, formal_entrypoints=58, exceptions=0
```

全量 suite 首次在 workspace-write 沙箱运行：

```text
python3 scripts/tests/run_all.py
exit code: 1
```

仅 `test_batch3_solana_vertical_slice.py` 与 `test_batch3_evm_vertical_slice.py` 因沙箱拒绝 `socket.bind(127.0.0.1, 0)` 报 `PermissionError: [Errno 1] Operation not permitted`；其余全部 PASS。未把环境失败记成全绿，也未改测试绕过。

随后在允许 loopback bind 的环境用完全相同命令重跑：

```text
python3 scripts/tests/run_all.py
exit code: 0
末行: 全部通过
```

两个 vertical slice 均真实 PASS。附加静态核验：`git diff --check` rc0；`rg 'Path.home()' scripts/tests/test_commands_deploy_sync.py` 为 0 matches；禁触路径 diff 扫描为 0 matches；两份 `_meaningful_text` 本体及两处指定 schema 探测锚无 diff。

## diff → finding 映射

| 文件 / hunk | finding / invariant | 目的与测试 owner |
|---|---|---|
| `scripts/report/adversarial_review_runner.py` ledger 常量、解析、append、active 绑定 | BR1-01：成功执行路次不能在 finalize 时事后省略 | 单次 `O_APPEND` 写行、连续 seq/prev 原始字节 SHA 链、同路径末行有效；F01 F 族 |
| `scripts/report/adversarial_review_runner.py` run-role 同路径重跑 | BR1-01 定案的合法重跑语义 | artifact/receipt 必须同在或同缺；每次成功重跑只追加 ledger，不删历史；F01 同路径 bad→clean |
| `scripts/report/adversarial_review_runner.py` finalize 集合对账与 aggregate 新键 | BR1-01：ledger 有效 receipt SHA 集必须精确等于传入集 | 省略、未登记、缺 ledger、断链均 rc2 且 aggregate 不落盘；F01 F 族 |
| `scripts/report/shared_release_receipt.py` ledger 重验 | BR1-01 消费侧独立性 | 从实物重算 chain/active/tip，核 aggregate 键类型与值、reviews receipt SHA 集；tip/末行双篡改回归 |
| `scripts/tests/test_repair_batch3_f01.py` F 族 | BR1-01 全部八类验收面 | 原反例、链破坏、未登记、合法重跑、缺失、双消费篡改、全链绿 |
| `scripts/tests/invariant_manifest.json` 三处 schema 登记 | BR1-01 producer/consumer 契约 | runner producer/consumer 与 shared consumer 登记 `review-ledger/v1`；invariant_scan owner |
| `scripts/tests/invariant_scan.py` 导入 schema 常量识别 | BR1-01 manifest 单源扫描 | 允许 shared 以 runner 的 `LEDGER_SCHEMA` 为单源声明消费，不另手抄 schema 字面量；invariant_scan owner |
| `references/independent-audit-protocol.md` 产物、机制、迁移、边界 | BR1-01 文档双向一致性 | 补 ledger 文件、aggregate 新键、重跑语义、旧案重跑和防伪窄口径；docs_lint/F02 文档契约 owner |
| `references/analyze-workflow.md` A4 步骤 5 | BR1-01 主流程产物契约 | run-role ledger 与 finalize 精确集合对账进入 A4 主干；docs_lint owner |
| `references/research-workflows.md` 对抗复核产物段 | BR1-01 研究 workflow 契约 | 补 ledger 文件、有效集、aggregate 绑定及不夸大边界；docs_lint owner |
| `scripts/tests/test_commands_deploy_sync.py` ACCOUNT_HOME/DEPLOYED/canonical | BR1-02：canonical 身份不可信进程 HOME | 系统账户 home 单源；gates F04 与 run_all owner |
| `scripts/tests/test_repair_batch3_gates.py` shadow-HOME 子进程回归 | BR1-02 最小反例 | 真 canonical 根＋假 HOME 不得 SKIP，rc 与真实 deployed 实况一致 |
| `scripts/tests/test_repair_batch3_gates.py` R10 分节列解析、裸词、现役唯一声明 | BR1-03：状态只能来自合法列且枚举 fail-closed | 三注入回归＋真实台账绿；gates F07 owner |
| `maintenance/repair-20260814-batch3/workorder_digest_round1_done.md` | 本工单验收记录 | 先红后绿、映射、六视角、边界与未修项 |

未映射 hunk：0。

## 六视角自审

### ① 字段来源审计

- ledger 的 `receipt_sha` 从成功落盘 receipt 当前字节计算，`artifact_sha` 从该 receipt 绑定的 artifact ref 取得；不是 finalize 调用者自报。
- finalize 重新读 ledger 原始字节计算每行 SHA、tip 和当前有效集，再用实际传入 receipt 字节 SHA 集对账。
- shared 重新读取 aggregate、ledger、receipt 与 artifact 实物；audit 未新增手抄逻辑，继续 100% 委托 shared。
- canonical home 来自系统账户数据库，不读进程 HOME；R10 状态只取按节确定的合法 Markdown cell。

### ② 失败分支审计

- ledger 缺失/空、JSON/键/schema/seq/prev/path/SHA/role 非法、活跃 receipt 改写或角色/artifact 绑定撕裂全部抛 `ValueError`。
- finalize 的 ledger 校验位于 blocker 联动之后、aggregate 写入之前；失败进入既有 rc2 路径，tmp 清理，正式 aggregate 不落盘。
- run-role 只有 artifact 与 receipt 同在时才允许覆盖重跑；只存在一个正式位时 fail-closed。ledger append 失败不会返回成功，遗留的未登记 receipt 也会被 finalize 集合闸拒绝。
- shared 的 `entries/active` 要求精确 int（bool 不冒充 0/1），`tip_sha` 要求 string 且整对象必须等于实物重算值。

### ③ 新格式的存量迁移

- `AGGREGATE_SCHEMA` 仍为同批尚无发布存量的 `adversarial-review/v4`，新增必填 `review_ledger`；无 ledger 的旧 v4 案在消费侧硬拒。
- 文档明确旧案不得手补 ledger/aggregate 字段，必须由当前 runner 重跑各角色并 finalize；新产物唯一生产者是 `adversarial_review_runner.py`。
- 同路径合法重跑保留 ledger 历史行，避免要求人工删除旧行；末行有效语义由生产与消费两侧一致执行。

### ④ 修复点的同族调用面

- producer/finalize：`adversarial_review_runner.py`。
- 正式消费者：`shared_release_receipt.py`；`audit_release_gate.py` 继续委托 shared，无第二套解析器。
- 存量正例生产口：F01/F02、`test_audit_release_gate.py`、`test_repair_batch_d.py` 均实际走 runner；全量 suite 已覆盖其连锁面。
- manifest 扫描器同步识别 imported `LEDGER_SCHEMA`，runner producer/consumer 与 shared consumer 三项均登记。

### ⑤ 双向一致性

- runner 行 schema、manifest、三份现役文档与 F01 tests 对 `review-ledger/v1`、文件名、末行有效、集合对账和 aggregate 三键表述一致。
- F02 精确契约 needle（含 `"resolved": bool`、scope_terms 与“删除该角色 artifact”字符串）保留；后者明确改写为“不再要求删除”，避免测试 needle 与新重跑语义冲突。
- `Path.home()` 在目标文件清零；纯函数 home 注入测试继续通过；真实 canonical＋shadow HOME 子进程回归进入全量 suite。
- R10 真实台账 27 条与唯一现役声明继续绿，历史建档句只作叙述、不参与机器对账。

### ⑥ 每道闸的可绕性

- finalize 少传已落账 receipt：有效 SHA 集不等，拒。
- finalize 多传未登记 receipt：有效 SHA 集不等，拒。
- 删除/改写 ledger 中间行：seq/prev 链拒；改写末行：aggregate tip 或活跃 receipt 绑定拒。
- 删除 ledger：finalize 和 shared 均拒；手抄 aggregate tip：shared/audit 双拒。
- 进程 HOME 覆盖不能改变 canonical 根；正文状态样式、裸版本状态、第二条现役声明不能改变 R10 机械状态。

## 防伪边界

本修复关死的是“已经跑了多路，finalize 时悄悄少传不利 receipt”的**事后省略**面。

“同一 receipt_path 重跑覆盖不利结果”与“整册 ledger 连同 receipt、artifact、aggregate 全套重造”仍属于蓄意伪造面；纯本地文件没有外部锚，无法阻止持同用户权限者重造一套自洽字节。本机制是防呆并提高伪造成本，不是完整性证明。

## 发现未修事项

- BR1-04 的 baseline 证据重建由裁判亲自处理，明确不在本单；本单未触碰 `baseline_run_all*.log`。
- 上述无外锚蓄意伪造边界按工单定案保留，不冒充已闭合。
- BR1-01/02/03 批准范围内未发现其他未修事项。

WORKORDER_DIGEST_ROUND1_COMPLETE
