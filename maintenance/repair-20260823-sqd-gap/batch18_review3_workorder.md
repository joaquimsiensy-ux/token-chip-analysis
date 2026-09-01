# 批 18 第三轮盲审消化工单 b18r3(v3,用户 2026-09-01 裁决定形):witness 闭包改"一级新鲜度边界(frontier)" + batch_d 墙钟报告契约

基线:main=50d7767(v6.54.2);当前 HEAD 与其树差异仅为本工单文件的历史版本,验收方确认按等价工作基线处理,不构成停工条件。
沿革:第三轮盲审 review-mti7cloy 三条(P1+P2×2)CONFIRMED → v1 复核四条退回 → v2("深验实录 observer")复核再退回,理由=深验实际会经 `solana_exact_validate.validate_repair_bundle_deep`(:1357)对 evidence manifest **逐件真哈希**(ARC 正式代 gen-80c6929 实测 307,334 件/40.1GB,签发一次深验 >20 分钟),"实录闭包只有几十个文件"前提不成立;全量实录则每次消费重读 40GB,凭证免重跑意义归零。
**用户裁决(2026-09-01):witness 防伪边界=钉一级输入(frontier),不冒充全量。** 本 v3 按此定形。
版本:6.54.2 → **6.54.3**。

## 纪律
- 先红后绿,红证据存 `maintenance/repair-20260823-sqd-gap/batch18_review3_red_evidence.txt`。
- 白名单:`scripts/report/shared_release_receipt.py`、`scripts/solana/audit_closed_accounts.py`、`scripts/tests/test_batch18_review_digest.py`(既有断言只许随本契约变更同步且 done 逐条说明)、`references/data-pipeline-solana-capture.md`、`VERSION`、`pyproject.toml`、`SKILL.md`(:23)、`CHANGELOG.md`、本目录 red_evidence/done。
- **不再触碰**(v2 计划取消):`scripts/lib/receipt_validate.py`、`scripts/lib/solana_observation.py`、`scripts/lib/solana_exact_validate.py`——frontier 方案无 observer 钩子。
- **test_repair_batch_d.py 禁改**;其余禁改同前批(handoff_manifest、audit_release_gate、既有其他测试断言、ARC 案根只读、API key)。
- 锚点以 50d7767 为准,开工 grep 亲核,不符停工。完工不 commit。

## 第一部分(消化盲审 P1+P2×2):frontier 语义

### 语义定义(须写进 docstring、CHANGELOG 与 scan-schemas 类文档段)
witness 的文件闭包字段改名 **`frontier_files`**,明确担保边界:
- **担保**:签发后,wrapper 报告(经 report_sha256)、各家族收据文件本体、以及各收据 JSON 内**一跳引用**的实物(inputs.*/output/holder_outputs.* 等三字段 ref)任何一个字节变化,消费时必被拒。
- **不担保**:更深层的证据叶文件(如 repair bundle 引到的 evidence_manifest 内 30 万件)签发后的变化——它们在签发那一刻刚被深验逐件核过,且其总清单指纹被一级文件(bundle.json 等)锁死;想改叶而不被发现只有 witness 存活的分钟级窗口,且下一次深验必炸。此边界是用户裁决的取舍,不是遗漏。

### 实现定形(全部在 `shared_release_receipt.py`)
1. **重写 `_reconciliation_bound_files` → `_reconciliation_frontier_files(root, target, receipts)`**:
   - 删除 v6.54.2 的递归发现全套:`json_queue`/`scanned_json`/BFS while 循环/`discover` 对引用文件的打开与再扫描。**任何被引用文件只哈希、绝不打开解析。**
   - 保留并复用 `candidate`(双基准 root+收据文件父目录、逐段 symlink 拒绝、案根包含)。
   - 枚举来源恰为两层:①重读 `root/reconciliation_report.json`,取 `checks[<key>].receipt` 各 ref → 解析为收据文件路径,绑定;②对每份收据的 **JSON 对象**(即 `receipts[key]`,内存中,不再读盘)全树遍历,凡 `dict` 且 `{"path","size","sha256"} ⊆ keys` 的节点视为一级 ref,拿 `path` 经 candidate 解析(双基准:案根、该收据文件父目录),成功即绑定;解析失败/案外/symlink → 跳过(与深验对可选输入的容忍一致)。遍历深度上限沿用 64。
   - ③Solana 冻结态显式补收 `SOLANA_FROZEN_OBSERVATION_BUNDLE`(沿用现行 :1921-1930 段逻辑)。
   - **wrapper 本体不入 frontier_files**(其新鲜度由 `report_sha256` 单验覆盖,不重复);此取舍由 R3-① 测试钉死。
   - 哈希一律用新增的分块流式 `_stream_sha(path)`(131072 块;不改全局 `sha()`,回归面隔离)——一级输入含数百 MB 边文件,整读不可取。
   - 上限哨兵 **512**(一级面实测 ~10-30 件;超过=形状污染,拒签 raise,不静默截断)。
   - 返回 `tuple(sorted({resolved: digest}.items()))`,语义与旧 bound_files 相同。
2. **DeepReconciliationWitness 字段改名** `bound_files` → `frontier_files`(frozen dataclass 同步;类属性默认值同步)。payload_sha256(b18r2)、WeakSet 身份注册(b18r1)、report_sha256 语义全部不变。
3. **消费三验**(:1988 附近):循环改用 `frontier_files` + `_stream_sha` 重哈希;缺失/symlink/不符→统一 `ValueError("reconciliation witness 无效/过期")`,文案不变。
4. 既有 `test_batch18_review_digest.py` 中引用 `bound_files` 的断言同步改名;凡断言"某文件在闭包内"的,逐条核对该文件是否属一级面(receipt 实物/inputs 实物/bundle 本体应仍在;若有断言依赖递归发现的深层文件,按新语义调整并在 done 逐条说明)。

### 红绿(先红后绿;R2/R3 顺序必须是"签发 → 篡改 → 用同一 witness 消费")
- **R1(P1 复现)**:合成夹具案,exact receipt inputs 绑一个 bundle.json,bundle 引用一个含 ≥200 个真实小文件三字段 ref 的 evidence_manifest 形状文件——基线(50d7767)签发 raise "文件闭包超过 128"(红证据存原文);修后签发成功,frontier_files **含** bundle.json、**不含** manifest 引用的那批叶文件。
- **R2(担保面生效)**:批 15 动态案,先签发 witness → 篡改一份一级输入实物(如 holders_owners.json 一个字节)→ 用**同一** witness 消费 → 必拒"witness 无效/过期"。(签发前篡改的对照属 N,不算 R 证据。)
- **R3(边界分离断言,两条)**:①wrapper 本体不在 frontier_files,但签发后篡改 wrapper → 消费必拒(report_sha256 路径生效);②冻结态案 frozen observation bundle 在 frontier_files,签发后改其任一字节 → 必拒。
- **R4(边界如实声明)**:合成案中造一个"深层叶文件"(被 bundle 形状清单引用、但不被任何收据一跳引用)→ 签发后篡改它 → 同一 witness 消费**不拒**(测试名点明 semantic boundary,注释引用户 2026-09-01 裁决);随后**重新签发**(重跑深验)→ 若夹具深验路径核该文件则必拒;若夹具深验不核它,则断言链式锁(bundle 清单文件本身在 frontier,改清单必拒)。
- **N**:批 15 N6 案未篡改照常通过;N9 calls==1/N10 calls==2 不变;N11 errors 逐字不变;review2_f1(payload 篡改)/review2_f2 同步改名后保绿。
- **ARC 只读实测**(验收方跑,你在 done 写清命令):签发一次报告墙钟与 frontier 件数/字节(预期 ~10-30 件、<1GB);消费验签耗时应为秒级。此为 P1 真实闭环证据。

## 第二部分 F4(既有 flaky,非盲审):audit_closed_accounts 报告契约统一
锚:`scripts/solana/audit_closed_accounts.py`——:49 `T0` 模块导入时初始化(同解释器多次 `main()` 继承旧时钟;batch_d 正是此调法,test_repair_batch_d.py:166);:282 deadline 复用旧时钟;早退 `bail_invalid` 共 **5 个调用点**(:293/:301/:304/:324/:350,边集缺失/解析失败/空边集/空签名史/零初始化事件),全部不写 `sampled` 段;:465 主路径才写全段;test_repair_batch_d.py:314 直接索引 `report["sampled"]["wall_truncated"]`,负载敏感(基线 6/6 复现 KeyError)。
修法(经 codex 两轮复核意见定形):
1. 删除全局时钟语义:`main()` 第一条业务语句记录 `started_at = time.monotonic()`,deadline 与 `elapsed_sec` 均由它计算;`generated` 时间戳继续用墙上时间。
2. 单一 report/sampled builder 供早退与主路径共用;`sampled` 段字段与主路径同构,未及采样的计数填 0,并**同时保留** `sampling_phase`(枚举:走到哪一阶段)与 `counts_complete: bool` 两字段,写清"填 0=未采样"与"实际查得 0"的区别(schema 一次定死,文档同步)。
3. 墙钟命中(任何阶段)统一在 `invalid_reasons` 追加含"墙钟"字样的原因,`sampled.wall_truncated` 如实置位;墙钟触发的早退同时保留**直接失败原因+墙钟截断原因**两条,去重。
4. `references/data-pipeline-solana-capture.md:97` 附近"早退是精简 status 报告"的描述同步更新。
5. **test_repair_batch_d.py 禁改**,其 ⑤ 断言须在任何负载下天然成立;在 `test_batch18_review_digest.py` 增加覆盖**全部 5 个 bail_invalid 调用点**的契约测试:每个早退分支报告都含同构 `sampled` 段(含两新字段)、墙钟触发时含"墙钟"原因。
6. 红测**不得依赖真实 sleep 与极小时间边界**:mock 单调时钟确定性推进越过 deadline,基线报告缺 `sampled` 键原文入红证据;修后同参数含全段,且 batch_d 连跑 5 次 rc=0(记入绿段)。

## 收尾
- 回归重点:test_batch18_review_digest 全部、test_batch18_shared_bundle_witness(N11 逐字)、test_batch15_three_ledgers_frozen(N9/N10)、test_reconcile_v4_receipt、test_repair_batch1、test_r9_batch3_release_guards、test_repair_batch_d 连跑 5 次、changelog/docs/version lint。
- SUITE 分母 146 不变;版本五处 6.54.3;CHANGELOG 六栏(第一部分=盲审三条经用户裁决定形为 frontier 语义并写明担保/不担保边界,第二部分=既有 flaky 收口);CHANGELOG 明确记"用户 2026-09-01 裁决:钉一级输入"。全量 146 由验收方本机 nohup。
