# 批 7 收敛确认（三审·防御回归验证）

- 日期：2026-08-18
- 分支：`fix/sqd-solana-v4`
- 验证 HEAD：`f530f73b511a59053da2f14c7e3a4d7dd0cddd46`
- 基线：`2fb1924`
- 生产解释器：`/usr/local/bin/python3`
- 验证性质：只读独立重做；未用 `batch7_done.md` 自报数字作证据
- 构造与篡改目录：`/private/tmp/batch7-verify3-pn6pl1tq/`
- 双 PATH SUITE 目录：`/private/tmp/batch7-suite-nxikb_rv/`

## 总判定

**PASS——T1–T6 全部 CONFIRMED，无 BREACH、无 WEAK，可合并。**

有一项非代码 NOTE：受限沙箱内首次全量 SUITE 有 2 个 loopback fixture 因
`socket.bind(127.0.0.1)` 返回 `EPERM` 而失败；随后在获准的非沙箱环境对同一 HEAD 重跑完整双 PATH，
两轮均为 `121/121`、exit 0、无 skip。该环境阻断未被冒充为全绿，原始失败日志与最终全绿日志均见 T5。

## T1 改动面与零 diff 独立核对——CONFIRMED

命令：

```text
git branch --show-current
git rev-parse HEAD
git diff --stat 2fb1924..HEAD
git diff --name-status 2fb1924..HEAD
git diff --exit-code 2fb1924..HEAD -- \
  scripts/solana/fetch_sqd_transfers_v2.py VERSION CHANGELOG.md
```

真实输出：

```text
fix/sqd-solana-v4
f530f73b511a59053da2f14c7e3a4d7dd0cddd46

 maintenance/repair-20260817-sqd-v4/PLAN.md         |   9 +
 maintenance/repair-20260817-sqd-v4/batch6_done.md  |   9 +
 maintenance/repair-20260817-sqd-v4/batch7_done.md  | 315 +++++++++++++++++++++
 .../repair-20260817-sqd-v4/batch7_workorder.md     | 140 +++++++++
 references/data-pipeline-solana-capture.md         |  11 +
 scripts/solana/curve_cost.py                       |  33 ++-
 scripts/solana/replay_edges.py                     |  48 +++-
 scripts/tests/test_sqd_consumer_v4.py              |  71 +++++
 8 files changed, 612 insertions(+), 24 deletions(-)

M maintenance/repair-20260817-sqd-v4/PLAN.md
M maintenance/repair-20260817-sqd-v4/batch6_done.md
A maintenance/repair-20260817-sqd-v4/batch7_done.md
A maintenance/repair-20260817-sqd-v4/batch7_workorder.md
M references/data-pipeline-solana-capture.md
M scripts/solana/curve_cost.py
M scripts/solana/replay_edges.py
M scripts/tests/test_sqd_consumer_v4.py

三文件联合 diff exit=0（无 stdout）
```

判定：全部改动文件已列出。生产/测试改动恰好只有工单指定的
`curve_cost.py`、`replay_edges.py`、`test_sqd_consumer_v4.py`；另外 5 个为本批维护/说明文档。
`fetch_sqd_transfers_v2.py`、`VERSION`、`CHANGELOG.md` 零 diff。未发现额外生产文件改动。

## T2 F2-01：curve_cost 归属闭合——CONFIRMED

独立脚本：`maintenance/repair-20260817-sqd-v4/verify3/verify_t2_t4.py`。每例均在独立临时目录真跑：

```text
/usr/local/bin/python3 scripts/solana/curve_cost.py \
  Curve11111111111111111111111111111111111 \
  --grad-price 1 --mint So1AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
```

正式留存运行：

```text
PYTHONDONTWRITEBYTECODE=1 /usr/local/bin/python3 \
  maintenance/repair-20260817-sqd-v4/verify3/verify_t2_t4.py
exit 0
```

真实逐例输出：

```text
T2 unregistered_collector: rc=2 output_exists=False tail=BLOCK: SQD v4 meta.collector_sha256 未命中 fetch_sqd_transfers_v2.py producer 登记
T2 wrong_logical_digest: rc=2 output_exists=False tail=BLOCK: SQD v4 meta 的边摘要/行数与实际边文件不一致
T2 wrong_edge_rows: rc=2 output_exists=False tail=BLOCK: SQD v4 meta 的边摘要/行数与实际边文件不一致
T2 one_logical_byte_tamper: rc=2 output_exists=False tail=BLOCK: SQD v4 meta 的边摘要/行数与实际边文件不一致
T2 valid_v4: rc=0 output_exists=True tail=Buyer11111111111111111111111111111111111  买              1 枚  付    0.000 SOL    1笔  首笔 01-01 00:01
T2 shared_validator: identity=true call=validate_cache_meta(meta, mint, legacy_sol5=False)
```

判定：四个攻击例均 exit 2 且不产生 `data/curve_costs.json`；合法 v4 meta 使用真实 ACTIVE
collector hash、正确逻辑摘要和行数后 exit 0，产出包含买家且 `tokens=1.0` 的成本结论，未误伤。
`inspect.getsource` 与函数对象 identity 同时证明调用的是共享
`sqd_cache_identity.validate_cache_meta`，不是消费端复制的弱校验。

可选红态旧版对照未执行；不影响现役四拒一放的独立实证。

## T3 F2-04：reconcile 单次冻结读取——CONFIRMED

时序：临时边文件先由 `_read_frozen_formal_edges` 冻结；在 `_replay_with_evidence` 返回后，把磁盘 gzip
替换为同压缩尺寸、不同内容的版本；随后检查发布 meta/receipt 和正式下游
`registry_anchor_check(..., verify_edge_physical_sha=True)`。

真实输出：

```text
边数=1  时间范围 01-01 00:01:40 → 01-01 00:01:40
铸造=100  销毁=0  净=100
负余额地址数=0
快照 supply=100  重放净-快照差=0
全 owner 对账：1/1 一致
重放末态已写 data/replay_final_balances.json
T3 frozen_sha=82a06cdfb422a768c8a5c23c51f52f1687fbea5dbec039df38225c00567c1947 disk_after_swap_sha=f6fdba2b884342ed0b1eacee1454c85d85132eb673d16180e86192999bd28330 receipt_edge_digest=ce67ff4865b3a050543c69bb61f9242073891a61840cb01e56fd385771c70b29 gate_pass=True
T3 downstream_reject=Solana 边文件物理 sha256 与 soltx meta 登记不一致
T3 inspect sha256_file_args=['producer_path'] helper_read_bytes=true
```

判定：receipt 的逻辑摘要和 meta 的物理 hash 均绑定替换前的单次冻结字节；替换后的磁盘件即使大小相同，
仍被发布侧物理 SHA 核验拒绝。对 `cmd_reconcile` 源码做 AST 检查，仅发现
`sha256_file(producer_path)`；边文件物理身份来自 `_read_frozen_formal_edges(edge_path)` 内单次
`path.read_bytes()`，没有对边文件二次 `sha256_file` 读盘。

## T4 冻结读取边界 fail-closed——CONFIRMED

真实输出：

```text
T4 symlink: reject=SQD 边文件是符号链接，拒绝 reconcile: .../t4/symlink.gz
T4 empty_file: reject=SQD 边文件为空: .../t4/empty.gz
T4 bad_gzip: reject=SQD 边文件 gzip/UTF-8 非法: .../t4/bad_gzip.gz: Not a gzipped file (b'no')
T4 bad_utf8: reject=SQD 边文件 gzip/UTF-8 非法: .../t4/bad_utf8.gz: 'utf-8' codec can't decode byte 0xff in position 0: invalid start byte
T4 bad_json: reject=soltx edge row 第 1 行 非法: Expecting property name enclosed in double quotes: line 2 column 1 (char 2)
T4 non_7_tuple: reject=第 1 行必须是 ['ts', 'slot', 'tx_index', 'instr_index', 'from', 'to', 'amt'] 七元组
T4 memory_disk_mismatch: reject=reconcile 内存边与冻结边文件不一致 receipt_exists=false
RESULT T2-T4 CONFIRMED
```

判定：7 个边界例全部 fail-closed；内存/冻结磁盘撕裂时没有生成 reconcile receipt。无放行。

验证脚本 NOTE：初版夹具因替换前后 gzip size 不等而由自检先停；第二版又因错误串必须含字面 `JSON`
的过窄断言先停。两处均只修改允许目录下的验证脚本，未修改生产/测试/文档源；最终留存脚本以同尺寸
替换件隔离 SHA 锚，并按真实“非法”语义断言，完整 exit 0。早期脚本还曾用 `TemporaryDirectory`
自动清理其系统临时夹具树；发现这与“禁止批量删除目录”纪律冲突后，已改为 `mkdtemp` 并保留正式证据
目录 `/private/tmp/batch7-verify3-pn6pl1tq/`。该偏差仅涉及早期临时夹具，没有删除或改动仓库文件。

## T5 双 PATH 全量 SUITE——CONFIRMED

SUITE 在 `/private/tmp/batch7-suite-nxikb_rv/repo` 的本地纯复制 clone 中执行；clone HEAD 为
`f530f73b511a59053da2f14c7e3a4d7dd0cddd46`。脚本对子进程使用的两条命令是：

```text
/usr/local/bin/python3 scripts/tests/run_all.py
env PATH=/usr/bin:/bin /usr/local/bin/python3 scripts/tests/run_all.py
```

### 默认 PATH

沙箱外完整日志：`/private/tmp/batch7-suite-nxikb_rv/suite_default.log`。

独立解析真实输出：

```text
PASS 121
FAIL 0
SKIP 0
SUMMARY ['全部通过']
```

日志尾：

```text
      PASS  test_anchor_plan_v3.py   anchor-plan v3: 15/15 PASS
      PASS  test_done_v4_collector.py PASS: U2 done/v4 collector + C12 recovery (24/24)
      PASS  test_csv_resume_collector_gate.py PASS: hash-wide REVOKED rejects current collector at startup
========================================================
全部通过
```

### `PATH=/usr/bin:/bin`

执行：

```text
PYTHONDONTWRITEBYTECODE=1 /usr/local/bin/python3 \
  maintenance/repair-20260817-sqd-v4/verify3/verify_t5.py \
  --reuse-clone /private/tmp/batch7-suite-nxikb_rv/repo --minimal-only
```

真实输出：

```text
suite_clone=/private/tmp/batch7-suite-nxikb_rv/repo HEAD=f530f73b511a59053da2f14c7e3a4d7dd0cddd46
T5 PATH=/usr/bin:/bin: rc=0 PASS=121 FAIL=0 SKIP=0 summary=全部通过 log=/private/tmp/batch7-suite-nxikb_rv/suite_minpath.log
T5 clone_status=clean
RESULT T5 MINIMAL_PATH CONFIRMED
```

### 环境阻断原始记录（NOTE，不计代码失败）

同一脚本首次在受限沙箱内运行时，119 项通过，以下两项因禁止 loopback bind 而失败：

```text
FAIL(rc=1)  test_batch3_solana_vertical_slice.py (无输出)
FAIL(rc=1)  test_batch3_evm_vertical_slice.py (无输出)
PermissionError: [Errno 1] Operation not permitted
2 项失败——修完再收工
```

两处 traceback 均落在 `ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)` 的
`self.socket.bind(self.server_address)`。没有把该次 119/121 写成全绿；获准解除沙箱后按原命令完整重跑，
得到上面的双 121/121。

## T6 F2-03 文档诚实性——CONFIRMED

真字节 SHA-256：

```text
30e7057c43da8a084612042bc62cb5ee8092c14c4f58f4909e2aa38e49bc0743  references/data-pipeline-solana-capture.md
d7ca41739eef62af2e914970057541418882c86fc6a8b9b62874438169bf8131  maintenance/repair-20260817-sqd-v4/PLAN.md
7322baf4ebcda5a7dcfeb98c32394f69f4046d7d5ef1a6923cb392289f57a77b  maintenance/repair-20260817-sqd-v4/batch6_done.md
```

关键真字节：

```text
references/data-pipeline-solana-capture.md:121: ...不是密码学签名。
references/data-pipeline-solana-capture.md:123: 这套防线假设工作目录的 data/ 可信。
references/data-pipeline-solana-capture.md:125: 抵抗这种主动伪造需要签名或独立链上重验，是根治宣告后的独立工程；本轮不实现...

PLAN.md:99: collector_sha256 ...不是密码学签名...
PLAN.md:100: ...假设 data/ 目录可信...
PLAN.md:101-102: ...不防具备本地写权限的对手同时伪造...；抗主动伪造需要签名或独立链上重验...不在本工程实现范围内。

batch6_done.md:322: ...“建立归属根基”“打断自证环”等措辞；当前文件真字节并无这两个原句...
batch6_done.md:324-326: ...只建立本地文件的完整性和版本对齐...假设 data/ 目录可信，不能证明边确实来自链上，也不防...主动伪造者。collector_sha256 是...公开哈希而非密码学签名。
```

判定：三处均明确把现役能力限制为本地完整性/版本对齐；明确 `data/` 可信前提；明确公开 hash 不是签名；
明确不抗能整体写盘的主动伪造者；明确签名/独立链上重验属于未实现的独立后续工程。没有把未实现防御虚称
为“已修”或“已建立根基”。`batch6_done.md` 中两处强措辞仅作为“工单称有、真字节并无”的被否定引文，
不是现役能力宣告。

## 证据与只读边界收口

验证件和日志 SHA-256：

```text
53cdd296a793b1e3fe06a6368ced4390ea0dea9489934f7161ce468dfa07c2f0  maintenance/repair-20260817-sqd-v4/verify3/verify_t2_t4.py
fe21341ff7505b7bc2f52160dea084dc962ecb1db77b77350f84c75dd034bb81  maintenance/repair-20260817-sqd-v4/verify3/verify_t5.py
1fadda1382b8cb3d4918e10cc3976985d599f683e42ccc00b57f03984cbe2c2d  /private/tmp/batch7-suite-nxikb_rv/suite_default.log
1fadda1382b8cb3d4918e10cc3976985d599f683e42ccc00b57f03984cbe2c2d  /private/tmp/batch7-suite-nxikb_rv/suite_minpath.log
```

写交付前的源树核对：

```text
git diff --exit-code
tracked_diff_rc=0

git status --short --branch --untracked-files=all
## fix/sqd-solana-v4
?? maintenance/repair-20260817-sqd-v4/batch7_verify_workorder.md
?? maintenance/repair-20260817-sqd-v4/opus_review_round1.md
?? maintenance/repair-20260817-sqd-v4/verify3/verify_t2_t4.py
?? maintenance/repair-20260817-sqd-v4/verify3/verify_t5.py
```

前两份未跟踪审查文档在本轮开工前已存在；本轮仓库写入仅为允许的 `verify3/` 两个验证脚本和本交付
`batch7_verify.md`。未改生产/测试/既有文档源，未 commit、merge、push。
