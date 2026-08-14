# 工单 C 消化轮 2 完工记录

## 施工基线与边界

- 分支：`repair-20260814-batch2`
- 施工前及完工时 HEAD：`6d49b04a0beb545296885389d11650cdaff3a03e`
- 未执行任何 git 写命令；未 commit、未 push。
- 生产代码仅改：`scripts/lib/camp_series_provenance.py`、
  `scripts/solana/replay_edges.py`、`scripts/report/audit_release_gate.py`。
- 回归仅改：`scripts/tests/test_repair_batch_c.py`。
- `scripts/report/state_from_facts.py` 与
  `maintenance/repair-20260814-batch2/import_pythia_legacy.py` 无需改：既有
  consumer 调用点与 producer 严格 JSON loader 已足够，本轮只需补边文件等深和
  audit 发布入口复用。
- `maintenance/repair-20260814-batch2/staging-pythia/`、PYTHIA 案根零触碰。
- 施工起点 `git status --short` 为空；最终盘点时另出现不在本工单范围的
  untracked `maintenance/repair-20260814-batch2/blindreview_B_round3.md`
  （mtime `2026-08-14T10:05:10-0400`）。本轮未创建、未读取内容、未修改或删除
  该文件；全库也无脚本引用该文件，按并发/外来资产保留。

## 逐项处置

### N-01：边文件 symlink 两侧等深

- consumer：`camp_series_provenance.registry_anchor_check` 在任何
  `is_file/stat/sha` 前先以 `is_symlink()` 拒绝 Solana 边文件。
- producer：`replay_edges.load_edges` 在 `gzip.open` 前拒 symlink；
  `cmd_reconcile` 的直调入口也在边文件登记/哈希前拒 symlink，避免绕过正式
  CLI 打开点。
- 回归：案外同内容 symlink（size/sha 均对）在 consumer 编译和 producer
  reconcile 两侧均拒；同内容 hard link 两侧均通过。

### N-02：发布点物理 SHA 接线锚

- 保持 `audit_release_gate.check_series_binding` 发布期来源链复算显式传入
  `verify_edge_physical_sha=True`。
- 新锚直接调用 `audit_release_gate.run(..., profile="new-analysis")`：边文件做
  同 size 单字节篡改，必须出现“物理 sha256”拒绝。
- 临时把接线改为 `False` 的 mutation 跑精确转红，恢复为 `True` 后转绿；因此
  删除接线或默认值漂移不再可能由全套测试静默放行。

### N-03/N-04：三类负向锚

- 编译点 `edge_file_size`：meta 登记为实物 size+1，更新 receipt 实物绑定后，
  编译仍因 `edge_file_size` 对锚拒绝。
- 编译点 `edge_file_sha256`：大写 64 hex 与 63 字符两种形态分别拒绝。
- producer `parse_constant`：在正式 soltx meta 的未使用字段注入 `NaN`，
  `cmd_reconcile` 在 JSON 解析层拒绝。
- 临时同时削掉 size 实物对锚、SHA 形态闸和 producer `parse_constant` 的
  mutation 跑精确红出上述 4 个检查；三处均已恢复。

### N-05：audit 发布 JSON 入口等深

- `audit_release_gate.load_json` 改为复用既有 `load_adversarial_json` 严格入口，
  未新造第三份 loader；由其统一挂载 `parse_constant` 拒绝与
  `RecursionError` 归类。
- reproduce output 原裸 `json.loads` 改走同一 `load_json`。
- 发布入口 `analysis-state.json` 注入 `NaN` 时，错误明确归类为
  `JSON无法读取 analysis-state.json`，不再落入逐点比对兜底；另有
  `RecursionError` 不外冒的直接锚。

### N-06

- 未执行。按工单属于裁判验收项（staging importer 全链重跑与
  migration receipt producer 指纹刷新）。

## 红到绿与 mutation 双跑证据

1. 新锚落地、生产代码未修时，定向 `t_fixround2()`：`rc=1`。
   精确红项：`N01 consumer symlink edge rejects`（实际编译 PASS）、
   `N01 producer symlink edge rejects`（实际 accepted）、
   `N05 release state NaN classified as invalid JSON`（NaN 被继续送入
   series_binding 比对）。
2. N-01/N-05 修复后定向跑：`rc=0`，`PASS fixround2 10 checks`。
3. N-02 接线 mutation（`True` 临时改 `False`）：`rc=1`，唯一红项
   `N02 release entry wires physical edge sha`；恢复 `True`。
4. N-03/N-04 mutation（临时削掉 size 实物对锚、SHA 形态闸、producer
   `parse_constant`）：`rc=1`，精确红项为 size 1 项、SHA 2 项、NaN 1 项；
   三处恢复后定向 10 checks 再次全绿。

说明：N-02/N-03/N-04 在原 HEAD 的生产行为本就拒绝，盲审定性是“闸存在、
删闸仍全绿”的假覆盖，故其有效先红证据是削闸 mutation，而不是虚构原行为放行。

## 验收结果

- `python3 scripts/tests/test_repair_batch_c.py`：`rc=0`，
  `PASS ... 226 checks`（由二轮盲审记录的 216 上升 10）。
- 沙箱内 `python3 scripts/tests/run_all.py`：除两项 loopback bind 外全部 PASS；
  两项失败均为 `ThreadingHTTPServer(("127.0.0.1", 0), ...)` 的
  `PermissionError: [Errno 1] Operation not permitted`，分别是 Solana/EVM
  vertical slice，尚未进入业务断言。
- 获准环境复跑同一 `run_all.py`：`rc=0`，`全部通过`；上述两项分别输出
  `PASS B3-SOL-E2E` 与 `PASS B3-EVM-E2E`。
- `git diff --check`：`rc=0`，无输出。

## A/B 资产与白名单自证

以下 worktree SHA-256 与 `git show HEAD:<path>` 重算逐项一致：

- `scripts/lib/supply_truth_gate.py`：
  `2da44c487273ba7671a5b443ab28d7e9d46a58fc6e5282e501deb5e784506ba4`
- `scripts/report/shared_release_receipt.py`：
  `db0c0489ede6a6255850207750ac053393d17ac1db100fb7ca20a0f0049e5ced`
- `scripts/report/adversarial_review_runner.py`：
  `1bf44ff1d7987a9b60ec16ac96502bfd06752ddaaff9ea9421c32092dde38d32`
- `scripts/report/a4_gate.py`：
  `d0fe28d9b090029a20bcbe3fba872eb9694479c79c75487b8430cf174afb059e`
- `scripts/tests/test_repair_batch_a.py`：
  `1cd68c2472ea63014428f645bf6354fbbee2abc8e3e1beb8f3e66c300e760614`
- `scripts/tests/test_repair_batch2_f02.py`：
  `d3d5c102900b91eee1faa9eec2a2bf80928fa86b6d203edd3278076d1d58c14a`

完工记录写入前，`git diff --name-only` 仅列四个获准施工文件；本记录因禁止
git 写命令而保持 untracked，由 `git status --short` 单独列出。
`state_from_facts.py`、`import_pythia_legacy.py`、`staging-pythia/` 专项 diff
均为空。最终 status 中另有上文已登记的外来 untracked
`blindreview_B_round3.md`，不计入本轮写入集合。

## 自审与发现未修

- symlink 检查均发生在打开、stat、sha 之前；hard link 仍按普通实物处理。
- 发布点测试走 `run(new-analysis)`，不是绕过发布路由直测底层函数。
- size、SHA 形态、producer NaN 均使用真实 receipt/meta/sidecar 链重新绑定，
  没有影子字段假绿。
- audit 两处 JSON 入口复用同一严格 loader；无第三份拒绝器。
- 本轮范围内未发现其他未修项。N-06 明确保留给裁判，不冒领完成。
