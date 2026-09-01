# 批 18 第三轮盲审消化工单 b18r3(v4,经三轮 codex 复核定形):witness 闭包改"一级新鲜度边界(frontier)" + batch_d 墙钟报告契约

基线:main 上本工单文件的历史版本为唯一与 50d7767(v6.54.2 代码终版)的树差异,代码零差异,按等价工作基线处理,不构成停工条件。
沿革:盲审三条(P1+P2×2)→v1/v2 复核退回(深验经 `solana_exact_validate.validate_repair_bundle_deep`(:1357)对 evidence manifest 逐件真哈希,ARC 正式代 gen-80c6929 实测 307,334 件/40.1GB,签发一次深验 >65 分钟)。
**用户裁决(2026-09-01):witness 防伪边界=钉一级输入(frontier),不冒充全量。语义已定,不再复议。** v3 复核落 5 条返修集,本 v4 全部吸收。
版本:6.54.2 → **7.0.0**(用户 2026-09-01 裁决:公开 witness 担保边界不兼容变更,升主版本)。

## 纪律
- 先红后绿,红证据存 `maintenance/repair-20260823-sqd-gap/batch18_review3_red_evidence.txt`。
- 白名单:`scripts/report/shared_release_receipt.py`、`scripts/solana/audit_closed_accounts.py`、`scripts/tests/test_batch18_review_digest.py`(既有断言只许随本契约变更同步且 done 逐条说明)、`references/scan-schemas.md`(登记 witness frontier 段)、`references/data-pipeline-solana-capture.md`(F4 文档)、`VERSION`、`pyproject.toml`、`SKILL.md`(:23)、`CHANGELOG.md`、本目录 red_evidence/done。
- **不触碰**:`scripts/lib/receipt_validate.py`、`scripts/lib/solana_observation.py`、`scripts/lib/solana_exact_validate.py`(frontier 方案无 observer)。
- **test_repair_batch_d.py 禁改**;其余禁改同前批(handoff_manifest、audit_release_gate、既有其他测试断言、ARC 案根只读、API key)。
- CHANGELOG 历史条目(6.54.1/6.54.2)中的 `bound_files` 为历史事实,**禁止全局替换**;仅在 7.0.0 条目写迁移说明。
- 锚点以 50d7767 为准,开工 grep 亲核,不符停工。完工不 commit。

## 第一部分:frontier 语义

### 语义定义(写进 docstring、CHANGELOG、scan-schemas.md 的 reconciliation 相关段)
witness 文件闭包字段改名 **`frontier_files`**:
- **担保**:签发后,wrapper(经 report_sha256)、各家族收据文件本体、各收据 JSON 一跳引用的实物任何字节变化,消费时必拒。
- **不担保**:更深层证据叶(如 repair bundle 引到的 evidence_manifest 内 30 万件)签发后的变化——签发那一刻它们刚被深验逐件核过,总清单指纹被一级文件锁死;此边界为用户裁决取舍,非遗漏。

### 实现定形(全部在 `shared_release_receipt.py`)
1. **重写 `_reconciliation_bound_files` → `_reconciliation_frontier_files(root, target, receipts)`**,删除递归发现全套(json_queue/scanned_json/BFS/discover 打开引用文件)。**任何被引用文件只哈希、绝不打开解析。** 枚举分**两层职责**:
   - **必选层(fail-closed,解析失败=拒签 raise,禁止静默跳过)**:施工者按 `validate_reconciliation_check` 各家族分支**逐条抄录**现行深验真实消费的 ref 及其 resolver,在模块内固化为家族级清单,done 里与代码逐条比对。至少含:
     * wrapper `checks[<key>].receipt` 各 ref → **用现行 `ref_ok` 同语义**解析(path+sha256,无 size 亦收);
     * EVM balance/supply/supply_truth 的 inputs(config/balances/replay_stats/transcript/observation_bundle 等,以 `_validate_evm_reconciliation_receipt` 与 supply_truth 分支实际消费为准)→ 用其现行 resolver(`_bound_case_ref`/`ref_ok`,含 base= 基准)同语义;
     * Solana exact_reconcile 的 inputs 全部(含 repair_bundle/repair_pointer/coverage_*);supply 的 `receipt["output"]`(path+sha256 形状,经 ref_ok);supply 的 `holder_outputs.owners/accounts` → **复刻 `solana_observation.py:601-641` 三基准先中即选语义**(inputs.gpa_rpc 实物父目录 → bundle/receipt 父目录 → receipt.parent/data);anchor(balance/time)收据的 output;
     * 冻结态显式补收 `SOLANA_FROZEN_OBSERVATION_BUNDLE`(沿用现行 :1921-1930 段);
     * 必选层 resolver 一律**复用/等价于现行消费函数的归一行为**(regular 的 macOS alias 归一、案内包含),不得用更窄的 candidate 重写——现行深验放行的布局 frontier 必须都能解析。
   - **兜底层(尽力,失败跳过)**:各收据 JSON 对象(内存中,不读盘)全树遍历,凡 `{"path","size","sha256"} ⊆ keys` 的 dict 且未被必选层覆盖,经 `candidate`(双基准:案根、该收据文件父目录;逐段 symlink 拒绝)解析,成功即绑;双基准命中**两个不同文件**时两个都绑(宁严;done 说明)。深度上限 64。
   - wrapper 本体**不入** frontier_files(report_sha256 已覆盖;R3-① 钉死)。
   - 哈希一律用新增分块流式 `_stream_sha(path)`(131072 块;不改全局 `sha()`)。
   - 上限哨兵 **512 件**(超过=形状污染,拒签 raise,不静默截断);**成本公式为 O(frontier 总字节),件数上限不封顶字节**——见 ARC 实测门。
2. `DeepReconciliationWitness.bound_files` → `frontier_files`(frozen dataclass 与类属性默认值同步)。payload_sha256、WeakSet 身份注册、report_sha256 语义不变。
3. 消费三验(:1988 附近):循环改 `frontier_files` + `_stream_sha`;缺失/symlink/不符 → 统一 `ValueError("reconciliation witness 无效/过期")`。
4. EVM 家族现行"忽略 provider、真调深验"路径**不变**(既有 N3 锁定);不宣称 collector 对 EVM 生效,若实现顺带通用须补 EVM 枚举单测。
5. 既有 `test_batch18_review_digest.py` 引用 bound_files 的断言同步改名;依赖递归发现深层文件的断言按新语义调整,done 逐条说明。

### 红绿(先红后绿;R2/R3/R4 顺序必须"签发→篡改→同一 witness 消费")
- **R1(P1)**:合成案 exact receipt inputs 绑 bundle.json,bundle 引 ≥200 个真实小文件三字段 ref 的 manifest 形状文件——基线签发 raise "文件闭包超过 128"(原文入红证据);修后签发成功(**红错必须发生在真实深验成功之后**,不得 monkeypatch 深验后单测旧 collector),frontier_files 含 bundle.json、不含叶。
- **R2**:批 15 动态案签发→篡改一级 owners 一字节→同一 witness 消费必拒。
- **R3**:①wrapper 不在 frontier_files 且签发后改 wrapper→消费必拒(report_sha256 路径);②冻结案 frozen bundle 在 frontier_files 且改之必拒。
- **R4(边界如实,三步断言,无替代分支)**:**真实 repaired exact-reconcile 夹具,必须走到 `validate_repair_bundle_deep` 的 evidence 逐件校验**。①签发后改叶(evidence 小文件),同一 witness 消费仍过;②不恢复叶,重新签发必因真实深验失败;③改 bundle/manifest 绑定本身,同一 witness 必拒。测试名点明 semantic boundary,注释引用户 2026-09-01 裁决。
- **Resolver 差异红测(v3 复核补)**:①holder 实物只在 gpa_rpc 实物父目录(bundle 分离布局)→ 必选层解析成功入 frontier(用窄 candidate 的实现会在此红);②中间 symlink 但终点在案根内、以及 macOS alias 布局 → 与现行深验同放行;③双基准同名不同内容干扰 → 两个都绑;④必选 ref 实物缺失 → 签发拒(不静默跳过)。
- **N**:批 15 N6 未篡改照过;N9 calls==1/N10 calls==2;N11 errors 逐字;review2_f1/f2 改名后保绿;EVM N3 保留。
- **ARC 只读实测门(验收方跑,done 写清命令)**:输出至少含 frontier 件数、总字节、最大五件、签发总耗时、frontier 哈希段耗时、同 witness 消费耗时。参考:ARC receipt inputs 声明字节合计约 743MB(本会话实测),**"<1GB/秒级"是待验假设非既定事实**;若实测显著超出(如总字节数 GB 级、消费分钟级),停工报验收方交用户重新裁决,不得强行判绿。

## 第二部分 F4:audit_closed_accounts 报告契约统一
锚(50d7767):`:49 T0=time.time()` 模块级;墙钟比较点 **:137/:165/:334/:376** 全 `time.time() > wall_dl`;`:474 elapsed_sec` 用 T0;**:313 auto 探路 `probe, _, _ = fetch_mint_sigs(...)` 丢弃 wall_hit**(:320 主路径有传播);5 个 `bail_invalid`(:293/:301/:304/:324/:350);:465 主路径才写 `sampled`;test_repair_batch_d.py:314 直接索引(基线 6/6 KeyError)。
修法(全部定死,施工零裁量):
1. **时间域统一**:删除全局 T0;`main()` 第一条业务语句 `started_at = time.monotonic()`;deadline(wall_dl)、全部 4 个比较点、`elapsed_sec` 一律 monotonic 域;`generated` 时间戳继续墙上时间。两域不得混用。
2. **:313 补传播**:auto 探路的 wall_hit 并入 `wall_flag["hit"]`(与 :322 同款)。
3. **单一 builder** 供 5 个早退与主路径共用,取得当前阶段/部分计数/wall 状态/直接原因;`sampled` 段完整键集=主路径现有键 + `sampling_phase` + `counts_complete`;`deep_account_classes` 保持三键零对象。
4. **`sampling_phase` 枚举固定**:`edges_missing`(:293)/`edges_invalid`(:301)/`edges_empty`(:304)/`signature_discovery`(:324)/`init_discovery`(:350)/`complete`(主路径)。
5. **`counts_complete` 规则固定**:5 个早退一律 `false`;完整走到主路径统一汇总点才 `true`。
6. 墙钟命中(任何阶段)统一在 `invalid_reasons` 追加含"墙钟"字样原因,`sampled.wall_truncated` 如实置位;墙钟触发的早退同时保留**直接失败原因+墙钟截断原因**两条,去重。
7. `references/data-pipeline-solana-capture.md:97` 附近同步。
8. **test_repair_batch_d.py 禁改**(新增字段不影响其索引与等值断言,天然兼容);`test_batch18_review_digest.py` 增加 **mock 单调时钟**(不依赖真实 sleep/极小时间边界)逐个覆盖 5 个 bail 点的契约测试:断言 phase 映射、counts_complete、wall_truncated、直接原因、墙钟原因、去重。红:mock 时钟推进越过 deadline,基线报告缺 `sampled` 键原文入红证据;修后同参数含全段,batch_d 连跑 5 次 rc=0 入绿段。

## 收尾
- 回归重点:test_batch18_review_digest 全部、test_batch18_shared_bundle_witness(N11 逐字)、test_batch15_three_ledgers_frozen(N9/N10)、test_reconcile_v4_receipt、test_repair_batch1、test_r9_batch3_release_guards、test_r9_batch3_solana_observation、test_repair_batch_d 连跑 5 次、changelog/docs/version lint。
- SUITE 分母 146 不变;版本五处 7.0.0;CHANGELOG 六栏,明确记"用户 2026-09-01 裁决:钉一级输入"与 frontier 担保/不担保边界;scan-schemas.md 登记 frontier 段。全量 146 由验收方本机 nohup。
