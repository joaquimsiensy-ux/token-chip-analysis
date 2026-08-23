# 批 4 施工记录

## 状态

实现面已完成，但验收状态为 **BLOCKED_ACCEPTANCE**，不能宣称整批全绿。

- 分支：`fix/sqd-gap-v6520`
- 冻结 HEAD：`5782f76`
- 模式：离线、未 commit、未切分支
- 全量：124 项中 119 PASS、5 FAIL；其中 4 项属于工单允许的批 5/回环 EPERM，另 1 项是非白名单旧测与本批 resolver 契约冲突。
- 完整证据：[batch4_green_evidence.txt](batch4_green_evidence.txt)

## 改动清单

1. 正式 Solana 消费入口统一接入 `resolve_formal_cache(mint, case_root)`：
   replay evolution、curve、wave、flow、entity、audit_closed 默认入口和 camp registry。
2. `replay_edges` 保留批 5 前 reconcile 的无 `case_root` 兼容路径及一次性 WARN；
   evolution 强制 `--case-root`，sidecar 写入 resolver 原样返回的 `edge_source_binding`。
3. curve 产物升级为 `curve-cost/v1` 外壳并写 binding；同 slot 顺序使用
   `(slot, tx_index, instr_index, ts)`，消费 repaired CURRENT 的参考顺序。
4. audit_closed 无 `--edges` 时强制 `--case-root`；显式 `--edges` 强制标记
   `formal:false`、`non_formal_source:"explicit-edges"`。
5. wave 升 `wave-scan/v5`，flow 升 `flow-anomaly/v3`；Solana 写五键 binding，EVM 省略；
   handoff/adjudication/audit release 的版本判定和提示同步升级。
6. entity 的 `input_binding` 写入同一 binding；handoff freeze 重放把已绑定的 Solana
   边、meta、案根规范化为物理路径后传回 resolver。
7. camp sidecar 可写 binding；消费时始终经 resolver，sidecar 有 binding 时必须全等。
8. invariant manifest 对齐 wave v5、flow v3、curve-cost/v1，并登记
   `sqd-solana-beta-trace/v1` 的生产/消费代码点。
9. 测试夹具完成 v5/v3 和 Solana binding 升版；新增 repaired CURRENT 的 curve/entity
   顺序语义回归及六入口、旧版、case-root/symlink 反例。

## 红转绿

- (2)：由“消费者不会读 repaired CURRENT”转为 curve/entity 都消费 resolver 合并缓存，
  且 repaired 顺序与参考序号一致、结果区别于 base。
- (9)：replay evolution、curve、wave、flow、entity 的案外复制路径被拒；audit_closed
  显式路径降为 non-formal；camp 经 resolver。
- (22)：wave v4 / flow v2 被 v5/v3 验收面拒绝。
- (23)：正式路径缺 `--case-root` 或案根含 symlink 均拒绝。

批 5 既有 RED 保留：(12),(13),(31),(33),(11),(32),(14),(1),(19),(24)。未提前修改
reconcile v4、receipt/wrapper、第五项或 handoff binding 全等发布闸。

## 发现项与阻断

### 1. 非白名单旧测与新正式契约冲突

`test_repair_batch_c.py` 的 F04 正例把 meta 写到 `data/soltx-fixture.meta.json`，而不是
canonical `data/soltx-<sha256(mint)>.meta.json`。camp 现在按工单必须经 resolver，故正确拒绝
`canonical base cache pair is missing`。该测试不在本批白名单，未擅自修改；生产端也未添加
绕 resolver 的 fallback。这是当前唯一非“批 5/EPERM”全量红项，因此验收阻断。

### 2. Repaired producer history 仍冻结

本批禁止修改 `producer_history.py`，当前又没有 `sqd_gap_repair.py` 的可接受 producer hash。
语义测试只在 registry seam 注入 fixture 自报的精确 hash 来验证 resolver/消费者链。真实 repaired
代会继续 fail-closed，等待获授权的后续批次登记。

## 禁改区自检

- `replay_edges.cmd_reconcile` HEAD/工作树 AST 源段 SHA-256 同为
  `4fc634b36fb77dc5e91872e14c7ee6bd806d587a608002dc42e915dcb46daedb`，逐字相等。
- `shared_release_receipt.py`、`reconciliation_report.py`、`producer_history.py`、references、
  PLAN、errata、契约草案无改动。
- handoff `AUTO_GATES` 和 binding 全等检查无改动。
- `git diff --check` 通过；未 commit。

## Fable 本机复验

完整可复制命令及预期产物检查见
[batch4_green_evidence.txt](batch4_green_evidence.txt) 的 “FABLE LOCAL RECHECK” 节。先在无
repair CURRENT 的 ARC 案根验证 base：wave v5、flow v3、curve-cost/v1、audit_closed 都应写入
同一五键 binding；EVM wave/flow 必须省略该键。

## 批 4b 微修

本节覆盖上文 `BLOCKED_ACCEPTANCE` 状态：获授权升级旧 F04 正例夹具后，批 4 验收阻断已
解除。生产实现未改，也没有增加绕过 resolver 的 fallback。

- `scripts/tests/test_repair_batch_c.py` 的 F04 Solana 正例现在把 meta 写到规范路径
  `data/soltx-<edge_key>.meta.json`，`cache_meta_path` 同步指向该路径。
- `data/legacy.meta.json` 保持不动：它只用于 `import_pythia_legacy.py` 的显式 legacy
  fail-closed 负例，不进入 camp/formal resolver。其余经正式 resolver 消费的 Solana meta
  夹具已是规范路径。
- 这是夹具问题，不是生产问题：旧正例模拟的是 PLAN 4.4.2 明令拒绝的复制 base/meta；
  resolver 拒绝它正是契约行为。修正正例位置即可，不能削弱生产端正式读边界。

复验结果：

- `python3 scripts/tests/test_repair_batch_c.py`：exit 0，227 checks 全绿。
- `python3 scripts/tests/run_all.py`：exit 1，124 项中 120 PASS、4 FAIL；仅余
  `invariant_scan.py` 的 6 个批 5 预登记差异、`test_batch4_invariant_guards.py` 对同一批 5
  producer-execution 缺口的派生断言，以及 Solana/EVM 两个 vertical slice 在沙箱内绑定
  `127.0.0.1` 的 EPERM。无其他红项。

批 4b 离线完成，未 commit、未切分支；详细输出分类已追加到
[batch4_green_evidence.txt](batch4_green_evidence.txt)。

## Fable 验收记录（2026-08-23 晚）
- 离线：`test_repair_batch_c.py` 227 checks 全绿（批 4b 夹具规范路径后）；本机 `run_all.py` 122/124，仅剩 2 项批 5 预期红（invariant_scan 6 缺口＝replay reconcile v4 producer/exact_validate 消费点/formal E2E replay 半边/failure artifact＋`test_batch4_invariant_guards.py:198` 派生）；codex 沙箱的两个回环 EPERM 本机不存在。
- ARC 实机（base 案，无修复代）：`wave_scan --case-root` 产 `wave-scan/v5`，五键 `edge_source_binding{cache_kind:base, gid:null}` 与 ARC 边/meta/logical 三哈希逐一吻合；`flow_anomaly_scan` 产 `flow-anomaly/v3`，binding 与 wave **逐字段全等**。产物在 scratchpad，不入案根。
- 结论：批 4＋4b 验收 PASS。
