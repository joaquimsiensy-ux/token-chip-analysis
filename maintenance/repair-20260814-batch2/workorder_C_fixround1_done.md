# 工单 C 消化轮 1 完工记录

## 一、基线、授权与施工边界

- 当前分支：`repair-20260814-batch2`。
- 冻结 HEAD：`b9c682290a8341e3541ff4f208b0ea45db6eed17`。
- 本轮从已有未提交工作树续做；开工时工单 C 主体 8 个文件已经存在施工差异，
  `test_repair_batch_c.py` 已由上一轮扩至 216 checks。
- 裁判本轮追加授权只涉及 `scripts/tests/test_review_resume_integrity.py`：把非法 17 字符
  mint 换成合法 32--44 位 base58 mint，并补 canonical gzip 边文件夹具。
- 全程未执行任何 git 写命令；只用 `git status/diff/show/rev-parse/branch` 做只读核验。
- 未运行同步脚本，避免覆盖上一轮未提交施工成果。
- `scripts/tests/invariant_manifest.json` 无相关计数或契约行变化，故未修改。
- 开工时另有两份非本工单的未跟踪文件：`blindreview_B_round2.md`、
  `workorder_B_fixround2.md`；本轮未修改。
- `maintenance/repair-20260814-batch2/staging-pythia/` 与 PYTHIA 历史案根未读取、
  未运行、未改写；本轮全部验证使用临时夹具。

## 二、逐项处置（对照工单 11 条）

### 1. BC-01/BC-02：布尔与数值结论改为精确判定

- `camp_series_provenance.py` 对 `gate_pass` 改为 `is not True` 拒绝语义；字符串
  `"false"`/`"FAIL"`/`"0"`、`[false]`、整数 `1`、浮点 `0.1` 均不得冒充通过。
- consumer 独立要求 `negative_balance_count`、`snapshot_mismatch_count` 是精确
  `int 0`，拒绝 `bool`、字符串和浮点零；`net_supply_raw` 必须是在场的非负 `int`。
- `replay_edges.py` 对 snapshot `closed` 改为 `is True`，并将缺失 `supply_raw`
  从静默默认改为显式 `ValueError`；收据中的 `net_supply_raw` 改为整数输出。
- `test_repair_batch_c.py::t_blindreview_c_fixround1` 覆盖上述 truthy 非 True 六值、
  三个独立数值结论、缺 supply 与 snapshot 各组成条件。

同族命令：

```text
rg -n "if not \w+\.get\(|bool\(\w+\.get\(" scripts/solana scripts/lib scripts/report
```

处置结果：目标 `camp_series_provenance.py` 与 `replay_edges.py` 已零命中。剩余命中逐类
复核如下：

- `time_spotcheck.py:336,354` 是进程内 RPC 批结果的 `ok/result` 分流，不是持久化
  receipt/meta 放行闸；不属本族。
- `audit_release_gate.py:204,296,590,605,688,703,793,809,814` 是清单文本、数组或
  classification/dormant/claim 语义字段，不是本工单 Solana reconcile/snapshot meta
  消费链；不在本工单 series 段授权面。
- `fetch_sqd_transfers_v2.py:1040,1076` 是 collector 自有 `launch_covered` 回补状态与
  累积写值，不是 reconcile receipt/snapshot meta 的正式发布判定；本轮不改 collector。
- `facts_gate.py:221`、`state_from_facts.py:77,125`、
  `adjudication_validator.py:500` 是普通必填字符串/列表存在性检查；不属本族。
- `hypersync_recon.py:122`、`decode_txs_v2.py:63,139` 是业务行字段缺席/失败行筛选，
  不是布尔 receipt gate；不属本族。

### 2. BC-03：净供给交叉不再条件式跳过

- `endpoint_reconcile` 不再用 `net_registered is not None` 决定是否对账。
- 缺字段、布尔、字符串、浮点、负数全部拒绝；合法非负整数必须与终态余额合计精确相等。
- 回归锚覆盖删字段、字符串化整数以及 mismatch 被 `gate_pass=True` 掩盖的场景。

### 3. BC-04/BC-05/BC-06：假覆盖三重灾区与边实物最低闸

- BC-04：新增不传 `expected_chain/mint/cutoff` 直调 `registry_anchor_check` 的负向锚，
  身份预期不得从收据自报补空。
- BC-05：producer 要求 canonical
  `data/soltx-<sha256(mint)>.jsonl.gz` 在场且非空，重放后向 meta 登记
  `edge_file_size` 与 `edge_file_sha256`；legacy importer 同步登记两字段。
- consumer 编译点验边实物存在、非空、size 与 meta 相等；发布点通过
  `verify_edge_physical_sha=True` 额外重算物理 SHA-256。测试实测同 size 篡改在编译点
  按设计不重哈希、在发布点必拒；文档未夸大为消费侧重放边内容。
- producer 对已有 `edge_logical_sha256/edge_rows` 与本次真实重放不一致时拒绝覆盖，
  钉住 i14/i19 自报自洽旁路。
- BC-06：`snapshot_ok` 的 schema、mint、closed、supply、cutoff、owners ref 六项均有
  独立破坏锚，另有 owners 数值 mismatch 锚；任一破坏均不能发布通过。

### 4. 其余假覆盖注入逐项补负向锚

`test_repair_batch_c.py` 已把工单列出的注入点变成可区分的真实坏输入：

- i02：Solana rows 搭配 `chain=ethereum`；
- i04：`window.to` 高于案 cutoff；
- i09：v2 专用拒绝文案必须含“重跑 replay_edges reconcile”；
- i13：producer meta 的 schema/mint/window 三变体；
- i17：非 v2/v3 的第三 schema；
- i21：soltx meta schema/mint 错；
- i22：window `from > to`；
- i23：edge_count 的 0/负数/bool/浮点及大写 digest；
- i24：owners 实物 size 与登记撕裂；
- i26：receipt 与 meta 窗口错位；
- i27：snapshot schema/mint/target 三变体。

这些锚均构造“该闸独拦”的坏输入，不以宽松类型异常或通用 schema 错误冒充覆盖。

### 5. BC-07：mint 形态校验

- producer 与 consumer 分别实现/调用 32--44 字符 Solana base58 全匹配校验，要求原文
  `strip` 后不变，不做 `.lower()`。
- 负向族覆盖纯空白、尾随 U+200B/U+FEFF/U+3164/U+2800、含 `0OIl`、900 字符超长；
  两侧均独立拒绝。
- 本轮把 `test_review_resume_integrity.py` 的 `MintCaseSensitive` 改为
  `"MintCaseSensitive" + "1" * 15`（32 字符、合法 base58），并按其 SHA-256 创建真实
  `data/soltx-<key>.jsonl.gz` 与同 key meta；gzip 内逐行写入测试 edges 的 canonical
  JSONL，保留 H-06 的大小写敏感测试意图。

### 6. BC-08：`data_cutoff_slot` 登记与迁移指引

- `state_from_facts.py` 对 Solana formal source 缺 `token.data_cutoff_slot` 显式 BLOCK，
  错误串指向 `scan-schemas.md` 存量迁移段。
- `scan-schemas.md` 说明该字段是采集上界 slot，须与 reconcile `window.to`、snapshot
  cutoff 同源，并给出现存案从采集清单/snapshot meta 查值及不一致即停的规则。
- `report-template.md` 的 token 必填字段清单补 `mint/data_cutoff_slot`。

### 7. BC-09：`edge_extrema.ts` 降为记录字段

- consumer 仍要求 first/last `ts` 是合法整数，但排序、窗口与身份判定只比较 slot。
- 代码注释及 `scan-schemas.md` 明写 ts 只供人读时间参考，不再暗示 `(slot, ts)` 是机器
  身份防线。

### 8. BC-O5：正式 JSON 解析等深

- `camp_series_provenance.py` 使用本地 `_json_loads` 拒非有限数与 `RecursionError`，挂载到
  sidecar、supply truth、preflight、reconcile receipt、soltx meta、owners、snapshot、
  camps spec、final balances 等正式解析点。
- `replay_edges.py` 使用从 `supply_truth_gate` 引入的 `_reject_constant`，挂载到 config、
  soltx meta、边行、owners、snapshot、camps；主入口将 `RecursionError` 归政策拒绝 rc=2。
- `state_from_facts.py` 复用 consumer loader并将深 JSON 归 rc=2；
  `audit_release_gate.py` 的发布序列解析复用同一 consumer loader。
- importer 对 collect manifest/案内对象及 gzip edge row 同样拒非有限数和深 JSON。
- 回归对 receipt/meta/owners/snapshot/sidecar/manifest 各挂载点注入 NaN，并对 producer、
  compiler 的 `RecursionError` 验 rc=2。

### 9. BC-O6：duckdb 缺席改硬失败

- `test_repair_batch_c.main()` 的 duckdb import 失败从 `SKIP + rc=0` 改为
  `FAIL + rc=2`，不允许 216 checks 静默跳过。

### 10. BC-O1：importer 逻辑摘要口径统一

- `import_pythia_legacy.replay_edge_facts` 不再哈希 gzip 中的原始 JSONL 排版；解析并验型后，
  按 `json.dumps(row, ensure_ascii=False) + "\n"` 更新摘要，与
  `replay_edges._replay_with_evidence` 同口径。
- 回归用紧凑 JSON 输入证明 importer 输出的是规范化逻辑摘要，而不是物理排版摘要。

### 11. 登记不修

严格保留工单裁决的四项，见第七节；本轮未扩大产品语义或 profile 范围。

## 三、红到绿证据

### 1. 主体施工（上一轮）

主体生产代码与 `test_repair_batch_c.py` 的红到绿发生在上一轮会话。本会话只接收到当前
未提交工作树和用户交接说明，无法追溯上一轮测试先红时的原始命令输出、精确 rc 或失败
条数，因此不补写、猜测或把当前绿态冒充先红证据。当前 diff 能确认新增了
`t_blindreview_c_fixround1` 及对应生产修复；最终绿态由本轮重新执行的 216 checks 与全量
suite 证明。

### 2. 本轮授权夹具的可复验红到绿

修前执行：

```text
python3 scripts/tests/test_review_resume_integrity.py
rc=1
ValueError: mint 必须是 strip 后非空、32~44 字符的 Solana base58 地址
```

堆栈定位 `test_h06` 使用非法 17 字符 `MintCaseSensitive` 调用 `cmd_reconcile`。

修后差异：mint 扩为合法 32 字符 base58；新增 canonical SHA 命名的 gzip 边文件和 meta；
snapshot/target/两次 reconcile 调用统一使用同一 `mint` 变量。

修后执行同一命令：`rc=0`，末行：

```text
PASS: H-02/H-03 + R2 legacy manifest refresh + H-04/H-05/H-06
```

### 3. 最终验收

- `python3 scripts/tests/test_repair_batch_c.py`：`rc=0`，末行
  `PASS: repair batch C (F-05+F-04+fixround1) 216 checks`。
- `python3 scripts/tests/test_review_resume_integrity.py`：`rc=0`，H-02--H-06 全过。
- 沙箱内 `python3 scripts/tests/run_all.py`：`rc=1`；仅
  `test_batch3_solana_vertical_slice.py` 与 `test_batch3_evm_vertical_slice.py` 在业务断言前
  因 `ThreadingHTTPServer.bind(127.0.0.1)` 返回
  `PermissionError: [Errno 1] Operation not permitted`；其余项目均 PASS，包括 Batch C
  216 checks 与本轮 resume fixture。
- 在允许 loopback 的获准环境原命令复跑：`rc=0`；Solana/EVM vertical slice 均 PASS，
  汇总末行 `全部通过`。
- `git diff --check`：`rc=0`，无输出。

## 四、六视角自审 ①：字段来源与信任根

1. 案身份：编译期 chain/mint/cutoff 来自 `source.token`，发布期来自 release target；
   consumer 不从 reconcile receipt 自报补空。
2. 对账结论：`gate_pass` 只接受 literal True，负余额数、snapshot mismatch 数与净供给由
   consumer 分字段独立验，不把一个布尔值当全部事实。
3. 边实物：logical digest/count 来自 producer 同次遍历；物理 size/SHA 来自 canonical gzip
   实物。编译点与发布点的强度差异由显式参数和文档约束，不隐式偷换。
4. snapshot：schema/mint/target/cutoff/closed/supply/owners ref 均来自当前绑定实物并逐项验；
   owners 本体还经过 path/size/SHA 三验和余额对账。
5. JSON：producer 与 consumer 各有自己的有限数拒绝入口；lib 不反向 import report，
   consumer 也不依赖 producer receipt 的解析结论。
6. mint/slot：mint 按原文 base58 形态比较；slot 是窗口身份与顺序信任根，ts 只记录。

结论：本轮关键判断均闭合到独立案 target、当前绑定实物或 producer 实测字段；truthy 值、
缺字段、收据自报和文件名表象不能单独充当放行证据。

## 五、六视角自审 ②：失败路径、清理与边界

1. 非 literal True、错类型零、缺净供给、坏 mint、错窗口、错 schema、输入撕裂、NaN、
   深 JSON 均 fail-closed；CLI 深 JSON 归政策错误 rc=2。
2. producer 发现旧 meta 摘要/行数与真实重放不一致时先拒，不用新值覆盖旧错值制造自洽。
3. 边文件缺失/空/size 撕裂在编译点拒；同 size 物理篡改在发布点重哈希拒；该差异已有
   正反测试和文档，不把“编译点未重哈希”藏成隐含豁免。
4. 所有新增攻击与 mint/gzip 夹具均位于 `TemporaryDirectory`；没有写入真实 data、
   staging-pythia 或 PYTHIA 历史案根。
5. `test_review_resume_integrity.py` 的 gzip 文件在临时目录内真实创建并由 reconcile 消费，
   不以空占位文件绕过新契约。
6. 沙箱能力限制与业务失败分开记录，并在获准环境对完整同一命令复跑全绿；没有按两项
   SKIP 或把 90 项绿冒充全量绿。

结论：失败出口均保持拒绝，临时夹具自动清理，授权边界与历史案保护面未漂移。

## 六、保护面自证

五个禁止触碰文件的当前工作树 SHA-256 与 `HEAD=b9c6822...` 逐一相等：

| 文件 | 当前 SHA-256 | HEAD SHA-256 | 结论 |
|---|---|---|---|
| `scripts/lib/supply_truth_gate.py` | `2da44c487273ba7671a5b443ab28d7e9d46a58fc6e5282e501deb5e784506ba4` | `2da44c487273ba7671a5b443ab28d7e9d46a58fc6e5282e501deb5e784506ba4` | 一致 |
| `scripts/report/shared_release_receipt.py` | `e36ac47c244acf4695489a6f4c4a3072c197e1a4d7776159eeb4b8337b31ddd3` | `e36ac47c244acf4695489a6f4c4a3072c197e1a4d7776159eeb4b8337b31ddd3` | 一致 |
| `scripts/report/adversarial_review_runner.py` | `f51462b44ca27e35afcbbbbf4087e0b43ae67a9ebf6b0c708cbc90e211b1994d` | `f51462b44ca27e35afcbbbbf4087e0b43ae67a9ebf6b0c708cbc90e211b1994d` | 一致 |
| `scripts/tests/test_repair_batch_a.py` | `1cd68c2472ea63014428f645bf6354fbbee2abc8e3e1beb8f3e66c300e760614` | `1cd68c2472ea63014428f645bf6354fbbee2abc8e3e1beb8f3e66c300e760614` | 一致 |
| `scripts/tests/test_repair_batch2_f02.py` | `27845c39e04c68dfd62c39cca4661bf9ce96d228429747005b2d82819c94bd41` | `27845c39e04c68dfd62c39cca4661bf9ce96d228429747005b2d82819c94bd41` | 一致 |

目标状态命令：

```text
git status --short -- staging-pythia PYTHIA PYTHIA分析 maintenance/repair-20260814-batch2/staging-pythia
```

结果：`rc=0`，零输出。当前会话也未对仓外 PYTHIA 历史案根执行任何命令或写操作。

## 七、发现未修（R10 台账）

- **BC-O2**：migration collector 标识零消费者；consumer 是否必须感知迁移案/原生案属于
  产品语义，按裁决登记不修。
- **BC-O3**：`check_series_binding` 仅在 new-analysis profile 执行；扩到
  independent-audit 会影响存量复核工作流，按裁决登记不修。
- **BC-O4**：sidecar producer 字段无锚；属于“公开哈希不是签名”的既定设计边界，按裁决
  登记不修。
- **BC-O7**：consumer 无法辨别 hard-link 替身；这是 importer 允许 hard link 的设计依赖，
  按裁决接受在案。

除上述四项外，本工单声明的 BC-01--09、BC-O1/O5/O6/O8 施工面已完成并通过本轮验收；
消化循环最终闭合仍以盲审员 C 第二轮独立复核为准。

WORKORDER_C_FIXROUND1_COMPLETE
