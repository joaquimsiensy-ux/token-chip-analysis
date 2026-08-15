# 消化轮 2 完工记录（BR2-01 / BR2-02）

## 结论

工单两项 P2 已按定案闭合：

- BR2-01：ledger active 行新增 `(st_dev, st_ino)` 实物身份判重；finalize 与 shared 分别对 `active / active receipt SHA / receipts|reviews` 做三方基数对账；ledger parser 与 append 入口统一限制 receipt basename 为 `^[A-Za-z0-9._-]+$`。
- BR2-02：R10 守卫按六个 section 硬编码真实表列数与合法状态列；表头/分隔行参与列数校验；R10 条目必须首尾 `|`、列数精确；显式拒绝 `\|`；结构空白仅认 ASCII 空格/Tab；所有列扫描宽松 statusish 与裸词变体。
- `independent-audit-protocol.md` 已补实物身份、文件名字符集与基数对账口径。

未执行任何 git 写命令。`sync-from-cc.sh` 位于 Codex skill 侧且会在存在上游提交时执行 `git merge main --no-edit`，与本工单“禁一切 git 写命令”冲突，故按用户硬约束未运行。

## 先红证据

全部反例均在 `/tmp/tca-digest-round2.VCsqah/` 的无 `.git` 临时副本运行；临时复现脚本为 `/tmp/digest_round2_red.py`，HEAD 输出留档 `/tmp/digest_round2_red.log`，SHA-256：`173757d8eaefa799f0cf464a5da0a64c1cd7cde8aacd130b21e1a0e0de9d9863`。

生产实现未修改时的独立复现：

```text
BR2-01_ALIAS_HEAD:
same_inode=true, entries=3, active=3, reviews=2,
finalize_rc=0, shared_message="", audit_errors=[]

BR2-01_CARDINALITY_HEAD:
same_inode=false, entries=3, active=3, reviews=2,
finalize_rc=0, shared_message="", audit_errors=[]

BR2-01_PATH_SYNTAX_HEAD:
空格 basename append=ACCEPTED

BR2-02_HEAD:
combined=[], escaped_pipe=[], fullwidth_structure=[], raw_body_pipe=[]
```

先追加正式回归、仍未改生产实现时，在 `/tmp/.../repo-tests-red` 运行：

```text
python3 scripts/tests/test_repair_batch3_f01.py
exit code: 1
新增 6 failures：路径别名 finalize、路径别名 shared/audit、双路径名错误串、
独立基数 finalize、独立基数 shared/audit、basename parser+append。

python3 scripts/tests/test_repair_batch3_gates.py
exit code: 1
新增 5 failures：组合注入、转义竖线、ID cell 全角结构空白、
正文原始竖线、非状态列 statusish。
```

上述两次红测中，既有测试项全部保持通过。

## 修后反例重放

同一独立复现脚本对最终 `/tmp` 副本重放：

```text
BR2-01 大小写别名：finalize rc2
BLOCK: review ledger receipt paths identify the same physical file:
Critic_execution.json and critic_execution.json

BR2-01 独立基数：finalize rc2
BLOCK: review ledger cardinality differs from finalize receipts:
active=3 active_receipt_sha256s=2 finalize_receipts=2

BR2-01 空格 basename：
REJECTED: review execution receipt basename must match ^[A-Za-z0-9._-]+$

BR2-02 组合注入：
R10-1 列数与所在节表结构不符

BR2-02 其他格式反例：
转义竖线 → cell 内竖线不受支持；
ID cell 全角空格 → R10 条目格式无法识别；
正文原始竖线 → 列数与所在节表结构不符。
```

正式回归还手抄了旧式 aggregate，确认 finalize 已拒时 shared 与委托 shared 的 audit 仍会独立双拒，不依赖 finalize 代挡。

## diff → finding 映射

| 文件 / hunk | finding / invariant | 测试 owner |
|---|---|---|
| `scripts/report/adversarial_review_runner.py` basename 正则及 parser/append 双入口 | BR2-01：ledger receipt_path 只能是受控 ASCII basename | F01 空格 basename 双入口反例 |
| `scripts/report/adversarial_review_runner.py` active 实物身份表 | BR2-01：不同路径字符串不得指向同一 `(st_dev, st_ino)` | F01 大小写探针、双路径名错误串、手抄消费反例 |
| `scripts/report/adversarial_review_runner.py` finalize 三方基数 | BR2-01：SHA set 不得折叠 active 条数 | F01 独立不同 inode、相同 receipt bytes 反例 |
| `scripts/report/shared_release_receipt.py` shared 三方基数 | BR2-01：消费侧独立重验 `active/SHA/reviews` 基数 | F01 两类手抄 aggregate shared/audit 双拒 |
| `scripts/tests/test_repair_batch3_f01.py` F 族追加 | BR2-01 全部验收面与正常/同路径重跑不回退 | 本文件主测试及 run_all |
| `scripts/tests/test_repair_batch3_gates.py` section layout、结构 regex、statusish 全列扫描 | BR2-02：Markdown 列形态与状态来源 fail-closed | gates F07 五个新反例＋真实 27 条绿例 |
| `references/independent-audit-protocol.md` ledger 机制段 | BR2-01 文档与运行时双向一致 | docs_lint --all、F01 文档回归 |
| `maintenance/repair-20260814-batch3/workorder_digest_round2_done.md` | 本工单证据、边界与验收记录 | 完工门禁 |

未映射 hunk：0。

## 验收结果

以下命令均在 `/tmp/tca-digest-round2.VCsqah/repo-green1` 运行：

```text
python3 scripts/tests/test_repair_batch3_f01.py                 rc=0
python3 scripts/tests/test_repair_batch3_gates.py               rc=0
python3 scripts/tests/test_repair_batch2_f02.py                  rc=0
python3 scripts/tests/test_review_20260804_p105.py               rc=0
python3 scripts/tests/test_audit_release_gate.py                 rc=0
python3 scripts/tests/invariant_scan.py                          rc=0
```

invariant 结果：

```text
receipt_producers=58, receipt_consumers=78, transport_calls=62,
atomic_writes=51, formal_entrypoints=58, exceptions=0
```

全量 suite 静态枚举 99 项。workspace-write 沙箱内 `run_all.py` 为 97 PASS、2 FAIL；唯一两项失败均发生在测试业务断言前，原因是 `ThreadingHTTPServer(("127.0.0.1", 0))` 的 `socket.bind` 被沙箱以 `PermissionError: [Errno 1] Operation not permitted` 拒绝。随后在允许 loopback bind 的环境按原命令分别重跑：

```text
test_batch3_solana_vertical_slice.py  rc=0
PASS B3-SOL-E2E: real producer->runner->aggregator->READY->release

test_batch3_evm_vertical_slice.py     rc=0
PASS B3-EVM-E2E: eth/bsc/base slices + nonzero dead vertical closure
```

据此业务结果为 99/99 通过。另有 `git diff --check` rc0；该命令只读，未产生 git 写操作。

## 六视角自审

### ① 字段来源与身份

- `receipt_path` 仍来自 ledger 原始行；parser 与 append 使用同一 `RECEIPT_BASENAME_RE`，不存在只收紧一侧。
- 实物身份来自当前 receipt 的 `stat()`，以 `(st_dev, st_ino)` 判重；拒绝串同时列出先后两个 ledger 路径名。
- receipt SHA、role、artifact SHA 继续从当前实物重验，未改弱原有绑定。

### ② 基数与集合

- finalize 先验证 `len(active) == len(active receipt SHA set) == len(receipt_paths)`，再做 SHA 集合等值。
- shared 先验证 `len(active) == len(active receipt SHA set) == len(reviews)`，再做 SHA 集合等值；audit 继续 100% 委托 shared。
- 大小写别名与“不同 inode、同字节”分别覆盖身份闸和纯基数闸，避免只修本机大小写案例。

### ③ 失败分支与原子性

- alias、基数不等、非法 basename 都在 aggregate 原子写入前抛错，finalize rc2 且 `adversarial_review.json` 不落盘。
- shared/audit 对手抄 aggregate 独立硬拒；不是只靠 producer 路径挡住。
- ledger 缺失、断链、同精确路径覆盖重跑等 Round 1 分支仍由原回归覆盖并保持全绿。

### ④ R10 结构解析

- 六节真实列数硬编码为第一节 6 cells、其余各节 5 cells；第五节状态列为 cell 3，其余为 cell 2。
- 表头与分隔行进入列数校验但不计条目；R10 条目首尾 `|` 与精确 cell 数均 fail-closed。
- 结构 regex 不再使用 `\s`；candidate 探针显式包含 U+3000，仅用于把非法结构送入失败路径，严格 row regex 仍只接受 ASCII 空格/Tab。
- statusish 用 `[ \t　]` 扫描所有列；合法状态仍只认严格枚举与合法状态列。

### ⑤ 回归与反例所有权

- 先红脚本、正式测试先红、修后绿三层证据一致；不是只跑最终绿例。
- BR2-01 覆盖 alias、独立基数、parser/append、finalize/shared/audit、正常双路与同路径覆盖语义。
- BR2-02 覆盖组合攻击、escaped/raw pipe、全角结构位、非状态列 statusish、真实 27 条零误伤；Round 1 三反例不回退。

### ⑥ 范围、文档与禁触

- 业务改动只在工单指定的 runner、shared、F01 测试、gates 测试与 protocol；另新增本完工记录。
- `VERSION`、`CHANGELOG*`、`SKILL.md`、`pyproject.toml`、`maintenance/repair-20260814-evmobs/`、`scripts/tests/test_evm_observation.py`、`archive/**`、`blind-reviews/**`、两份 `_meaningful_text` 本体、两处 schema 探测锚行、`baseline_run_all*.log` 均零 diff。
- 当前另有用户提供且未跟踪的 `blindreview_round2.md`、`workorder_digest_round2.md`；二者未改写。

## 未修事项

- 本工单 BR2-01、BR2-02 范围内未修事项：无。
- Round 1 已明示的蓄意伪造边界不因本工单改变：同一精确 `receipt_path` 的受控覆盖重跑仍允许；纯本地无外锚时，整册 ledger、receipt 与 aggregate 全套重造仍无法由本机制证明未发生。
- 未改版本件，版本发布与 CHANGELOG 记账留给后续独立流程。

WORKORDER_DIGEST_ROUND2_COMPLETE
