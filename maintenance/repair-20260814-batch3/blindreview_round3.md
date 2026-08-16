# repair-20260814-batch3 质量回归盲审（Round 3 终审）

## 总判定：CONDITIONAL（不可进入 closure / 不可合并 main）

审查对象冻结为消化轮 2 的 `f912c18483252b8901364b8c1db6b7607579e6e6..cdbac109f1d749d8fd4b907dab1ce99101496c37`，并以 `83394ab47ebd6e71ae54d83e485cd6e42f3b9349..cdbac109f1d749d8fd4b907dab1ce99101496c37` 做批 3 全批终态复核。

Round 2 的两个最小复现均已闭合：大小写别名 receipt 在同 inode 场景被实物身份闸拒绝，竖线推列＋全角空格状态组合被 statusish 与列数闸拒绝。正常两路和同精确路径重跑也未回退。消化轮 2 的 8 个 changed files 全部能映射到工单，未发现未授权业务改动。

但本轮发现 1 项新的同族 P2：R10 守卫仍会把未被两个 statusish 正则命中的未知/隐形状态标记静默解释为 OPEN。它违反 F-07 工单“格式认不出 → FAIL”的根不变量，因此即使当前真实台账内容正确，批 3 仍不能判 PASS，R10-5/6/16/17 不能在本状态下转 CLOSED，也不能合并 main。

## Findings

### BR3-01 — P2 — 未知或隐形状态标记仍被静默当作 OPEN，F-07 枚举 fail-closed 未闭合

- **所在文件行**：`scripts/tests/test_repair_batch3_gates.py:25-34,360-393`；承诺口径见 `maintenance/repair-20260814-batch3/workorder_closeout.md:23-29`。
- **归因**：BR1-03 / BR2-02 同族修复不全。
- **问题陈述**：严格枚举只匹配 `【CLOSED x.y.z】` 与 `【FIXED_PENDING_REVIEW x.y.z 批N】`；宽松扫描也要求字节中连续出现精确关键字 `CLOSED` 或 `FIXED_PENDING_REVIEW`。若状态格出现其他全角括号状态、关键字中插入不可见字符，或用 HTML 字符实体形成渲染后的 CLOSED，`status_markers` 与 `statusish` 都是空数组。代码随后无失败地执行 `status = ... else "OPEN"`。这把“没有状态标记的合法 OPEN”与“存在但无法识别的非法状态”混为同一种机器状态。
- **独立最小反例**：在 `/tmp/tca-round3.NQvqw5` 的 `cdbac10` 无 `.git` 副本中，以真实台账为基底，将 R10-1 的首个 `【CLOSED 6.41.0】` 分别替换为下列任一种，并把当前现役 `19` 同步改为 `20`：

  1. `【CLO<ZWSP>SED 6.41.0】`（`<ZWSP>` 为 U+200B，视觉上仍为 CLOSED）；
  2. `【CLOSED_PENDING 6.41.0】`；
  3. `【CLO&#83;ED 6.41.0】`（Markdown 渲染为 CLOSED）。

  三份副本调用 `r10_ledger_failures()` 的实测返回值均为 `[]`。
- **影响**：真实台账当前 27 条、现役 19 的内容没有被本反例证伪；被证伪的是守卫对未来 closure/台账漂移的 fail-closed 能力。一个肉眼看似有状态但机器不识别的条目可以在同步现役数后通过全套 gates，和前两轮“可见 CLOSED 被算作 OPEN”的事故类型相同。
- **必修建议**：

  1. 在合法状态 cell 上先识别“是否存在状态载体”，再判其是否为严格枚举；不能用“严格/宽松正则都没命中”直接代表 OPEN。
  2. 当前台账中全角 `【...】` 只承载状态，可对状态 cell 的括号载体做完整提取：存在任何非严格枚举载体即 FAIL；同时拒绝状态关键字中的 Unicode format/invisible 字符和 HTML 字符实体，或在受控规范化后发现与原字节不一致时 FAIL。
  3. 补正式回归：U+200B 插词、未知括号状态（如 `CLOSED_PENDING`）、HTML entity 三例均须红；真实 27 条、Round 1 三反例、Round 2 组合反例继续绿/红符合原语义。

## 前两轮与原始 finding 终态

| 项目 | 本轮结论 | 证据摘要 |
|---|---|---|
| F-01 / R10-16、R10-17 | 可 CLOSED | blocker 双向联动、10 字符门槛、entrypoint 身份、execution ledger、消费侧独立重验均通过；同路径覆盖与无外锚整套重造边界如实保留。 |
| F-04 / R10-5 | 可 CLOSED | 无界迁移豁免已删除；canonical 根不受 `HOME` 改写；缺目录与逐文件 SHA 漂移均 fail-closed。 |
| F-05 / R10-6 | 可 CLOSED | 直接依赖由 pyproject 机械派生，direct→唯一 lock pin→installed 与 requires-python 全部闭合；平面 lock 的残留传递 pin 边界已明示。 |
| F-07 | **不可 CLOSED** | 当前台账内容正确，但枚举守卫仍有 BR3-01 的未知/隐形状态载体假绿。 |
| BR1-01 | CLOSED | 省略已落账不利 receipt 的本尊复跑 rc2；BR2-01 的路径别名/基数补钉本轮也通过。 |
| BR1-02 | CLOSED | 伪 `HOME` 不再触发 canonical rc0 SKIP。 |
| BR1-03 | 原三个反例已闭合；根因未终态 CLOSED | 正文伪标记、裸状态、重复现役声明均拒；BR3-01 证明未知状态载体仍可静默当 OPEN。 |
| BR1-04 | CLOSED | exact parent 基线已重建；旧日志 STALE、旧 invariant 与过宽 diff-check 宣称均有修正记录。 |
| BR2-01 | CLOSED | 大小写别名、硬链接别名、不同 inode 同字节基数折叠均拒；正常两路与同精确路径重跑保绿。 |
| BR2-02 | 本尊 CLOSED；同族新增 BR3-01 | 竖线＋全角空格组合、转义/原始竖线、全角结构空白、非状态列 statusish 均拒。 |

## 验证清单

### 1. Round 2 两个最小复现

- **BR2-01 大小写别名**：`case_insensitive=true`、`same_inode=true`，三次 run-role 均 rc0；finalize rc2，错误为 `review ledger receipt paths identify the same physical file: Critic_execution.json and critic_execution.json`；`adversarial_review.json` 不存在。
- **BR2-02 组合输入**：`r10_ledger_failures()` 同时返回“正文列出现状态样式标记”和“列数与所在节表结构不符”。

### 2. 新守卫边界与既有绿例

- 不同 basename 的硬链接 receipt 指向同一 inode：finalize rc2，不落 aggregate。
- 不同 inode、相同 receipt 字节造成 `active=3 / SHA=2 / receipts=2`：正式回归 rc0，反例被基数闸拒。
- receipt basename 的空格输入：parser 与 append 两入口均拒；实现的 `^[A-Za-z0-9._-]+$` 与协议一致。
- 正常 claim＋critic 两路：finalize rc0，shared 空错误，audit `[]`。
- 同精确 `receipt_path` 重跑：finalize rc0，aggregate 为 `entries=3, active=2`，shared/audit 全绿，未误伤已批准重跑语义。
- R10 的 escaped pipe、raw body pipe、全角 ID 空白、非状态列全角 statusish、表头多列：均被拒。
- 新增 BR3-01 三个未知/隐形状态反例：均假绿 `[]`，正式 suite 尚无 owner。

### 3. diff 授权与全批映射

- `git diff f912c18..cdbac10`：8 个 changed files。新增 Round 2 报告、工单、done；业务 hunk 仅 protocol、runner、shared、F01 tests、gates tests，逐项对应 D2-01/D2-02；未发现未授权改动。
- `git diff 83394ab..cdbac10`：39 个 changed files，均可映射到 F-01、F-04、F-05、F-07、Round 1/2 消化、基线证据重建或批准的版本/文档收口；未发现额外业务功能混入。
- 禁触路径 `maintenance/repair-20260814-evmobs/`、`scripts/tests/test_evm_observation.py`、`archive/`、`blind-reviews/` 在全批 diff 中均为零；`run_all.py` 的 99 项也不含 `test_evm_observation.py`。
- `git diff --check f912c18..cdbac10` rc0。全批 `git diff --check` 仅报告两份 baseline 原始日志各两处尾空格；排除这两份保真日志后代码/文档 rc0，与 BR1-04 修正记录一致。

### 4. 文档、版本与实现一致性

- `VERSION` 与 `pyproject.toml` 均为 6.43.0；version/changelog/docs lint 全绿。
- `independent-audit-protocol.md` 对实物身份判重、受控 basename、三方基数、同路径重跑及无外锚边界的描述与 runner/shared 当前实现一致。
- R10 台账当前仍把 R10-5/6/16/17 标为 `FIXED_PENDING_REVIEW 6.43.0 批3`，现役 19，尚未提前写 CLOSED。
- 唯一文档/实现断点是 BR3-01：工单明确“格式认不出 → FAIL”，实现却对未知/隐形状态载体返回 OPEN 且无 failure。

### 5. 定向测试与全量 suite

以下命令均在 `/tmp/tca-round3.NQvqw5` 的 `cdbac10` 副本运行：

```text
python3 scripts/tests/test_repair_batch3_f01.py       rc=0
python3 scripts/tests/test_repair_batch3_gates.py     rc=0
python3 scripts/tests/test_repair_batch2_f02.py        rc=0
python3 scripts/tests/test_review_20260804_p105.py     rc=0
python3 scripts/tests/test_audit_release_gate.py       rc=0
python3 scripts/tests/invariant_scan.py                rc=0
```

invariant 输出为 `receipt_producers=58, receipt_consumers=78, transport_calls=62, atomic_writes=51, formal_entrypoints=58, exceptions=0`。

`run_all.py` 静态枚举 99 项。受限沙箱内 97 PASS；仅 Solana/EVM 两条 vertical slice 在业务断言前因 `socket.bind(127.0.0.1, 0)` 被拒而失败。随后在允许 loopback 的同一副本按原命令复跑：

```text
test_batch3_solana_vertical_slice.py  rc=0
PASS B3-SOL-E2E: real producer->runner->aggregator->READY->release

test_batch3_evm_vertical_slice.py     rc=0
PASS B3-EVM-E2E: eth/bsc/base slices + nonzero dead vertical closure
```

因此业务测试可合成为 99/99 通过；但绿 suite 不覆盖 BR3-01，不能据此推翻该 finding。

## 终审处置

本轮不是 PASS。先修 BR3-01 并补三个同族反例，再至少复跑 `test_repair_batch3_gates.py`、`invariant_scan.py` 与 `run_all.py`。在该项闭合前：

- R10-5/6/16/17 不转 CLOSED；
- 不执行批 3 closure；
- 不合并 main。

BLINDREVIEW_ROUND3_COMPLETE
