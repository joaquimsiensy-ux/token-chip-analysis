# 批 18 盲审消化工单(b18r1):witness 防伪造闭环 + manifest 分类器防御

基线:main=19c0fa6(v6.54.0)。盲审 review-mth382hf-wfap0k(base=e43a98f)三条发现全部 CONFIRMED,一次消化。
版本:6.54.0 → **6.54.1**(既定契约内修复/加固,按 v6.54.0 新版本规则的"修"档)。

## 纪律(与批 15-18 相同)
- 先红后绿:每条先在基线复现红,原文存 `maintenance/repair-20260823-sqd-gap/batch18_review_red_evidence.txt`,再动生产代码。
- 行号锚已由验收方亲核(以 19c0fa6 为准);若你 grep 发现锚点与工单不符,**立即停工**写明差异,不得自行改判。
- 白名单(只许改):`scripts/report/shared_release_receipt.py`、`scripts/report/handoff_manifest.py`、新测试 `scripts/tests/test_batch18_review_digest.py`、`scripts/tests/run_all.py`(SUITE 145→146)、`VERSION`、`pyproject.toml`、`SKILL.md`(:23 版本注释)、`CHANGELOG.md`、本目录 `batch18_review_red_evidence.txt`/`batch18_review_done.md`。`scripts/report/audit_release_gate.py` 原则不动;若消费点确需一行适配,done 里逐行说明理由。
- 禁改:既有任何测试的断言逻辑(含 batch18 两文件、批 15 N9/N10/N11);ARC 案根;entity_source_trace.py;solana_exact_validate.py;state_from_facts.py;任何 API key 不得出现在代码/测试/提交。
- 完工产物:done 报告写清每条的红证据位置、修法、既有测试零改动声明。

## F1(P1-a)witness 可伪造 → 构造私有化(身份注册表)
锚:`shared_release_receipt.py:1820-1829`(frozen dataclass,公开)、`:1832-1848`(witness_reconciliation_report)、`:1858-1864`(消费三验只有 isinstance/root/wrapper-sha)。
红:直构 `DeepReconciliationWitness(root=案根.resolve(), report_sha256=sha(真 wrapper), target=伪造, receipts=伪造)` 可通过三验;`dataclasses.replace(合法witness, target=伪造)` 同样通过。两式红证据都要。
修法(定形):
1. dataclass 改 `@dataclasses.dataclass(frozen=True, eq=False)`(eq=False 恢复 identity hash,现无任何调用依赖值等)。
2. 模块私有 `_ISSUED_WITNESSES = weakref.WeakSet()`;`witness_reconciliation_report` 构造后注册。这是唯一注册入口。
3. 消费三验增加第一条:`witness not in _ISSUED_WITNESSES → raise ValueError("reconciliation witness 无效/过期")`(文案不变,前缀层级不变——provider 在 validate_sources 原位调用,异常仍落 validate_bundle except 内)。
4. 大白话注释:为什么按身份不按值(值等的伪造品/replace 拷贝必须拒)。
绿测试:直构、replace 拷贝、值全等拷贝三式均拒;合法 witness 照常通过;批 15 N9(calls==1)/N10(calls==2)与批 18 N2/N4 不改断言跑绿。

## F2(P1-b)witness 只绑 wrapper → 绑定深验文件闭包
锚:`:1424-1433`(receipts 逐 check 构造)、`:1450-1494`(Solana exact_reconcile inputs.holders_owners、supply holder_outputs.owners(注意 base=receipt.parent 解析)、冻结态 SOLANA_FROZEN_OBSERVATION_BUNDLE)、`:1179`(validate_reconciliation_check,receipt 文件 ref 在 wrapper checks[key].receipt)。
红:合法 witness 构造后,改动 exact_reconcile 的 receipt 文件(不动 wrapper)→ 现三验仍通过(payload 消费旧缓存);改动 holders_owners 实物同理。两式红证据。
修法(定形):
1. witness 增字段 `bound_files`:tuple 化的 ((绝对resolved路径str, sha256), …)。构造时(真跑深验之后)收集闭包:wrapper 本体、每个 check 的 receipt 实物文件、各 receipts[key] 的 inputs/holder_outputs 中含 path+sha256 的 ref 所指实物、冻结态另加冻结 bundle。**路径解析不要重写**:优先从深验已解析出的引用复用;必要处用与深验同款的 _bound_case_ref/base= 语义解析后取 resolved 绝对路径。收集只收构造时磁盘上存在的实物,当场重算 sha(构造点=刚深验完,磁盘态=已验态)。纯函数夹具态(wrapper 缺失走空哨兵)允许 bound_files 为空。
2. 消费三验(现 :1858-1864)扩为:对 bound_files 逐一重哈希,任一文件缺失或 sha 不符 → 同一 ValueError("reconciliation witness 无效/过期")。wrapper sha 单验保留。
3. done 里写清闭包枚举依据(逐来源列锚点),并声明:这是文件级新鲜度指纹,不重跑深验逻辑,与批 15 缓存语义(N10 缓存态≡非缓存态)兼容。
绿测试:改 receipt 文件→拒;改实物→拒;不改→过;全部既有测试不改断言跑绿(重点:批 18 N11 两组 errors 逐字不变——默认不注入路径零变化)。

## F3(P2)_reverse_bound_reason 非对象 JSON 崩溃截断 → 类型防御
锚:`handoff_manifest.py:123-147`(:137-141 try 只包 safe_case_file+load_json;:144-146 `scan.get`/`(scan.get("input_binding") or {}).get` 在 try 外)、`:284-298`(data_map for 循环整体在 try 内,:297 except Exception 打印后 generate 继续——异常会放弃剩余条目)、`:249-253`(add_path 调用点)。
红:案内造 data_map 索引两个条目,第一个指向内容为 `[1, 2]`(合法 JSON 非对象)的 `data/x/distribution_scan.json`,第二个为普通文件 → 基线 generate:AttributeError 被 :297 吞、第二个条目未进 manifest(截断证据贴 artifacts 对比)。
修法(定形):`_reverse_bound_reason` 内:`load_json` 结果非 dict → return None(按普通产物收录,manifest 只做 sha 绑定,坏 JSON 也照常绑定,与"解析失败 return None"一致);`input_binding` 取值非 dict → 视同无绑定(不 raise)。:284-298 的既有 for-in-try 结构不动(只除掉批 18 引入的新异常源)。
绿测试:同夹具 generate 不截断,两条目均入 manifest;真 final 分布扫描(dict+stage=final+input_binding.handoff_manifest)仍被跳过(批 18 N5 语义不回退);非 dict input_binding(如字符串)的 scan 按普通产物收录。

## 测试与收尾
- 新文件 `scripts/tests/test_batch18_review_digest.py`(F1×1、F2×1、F3×1 起,负例如上,可合理分组);run_all SUITE 登记 145→146。
- 全量:run_all 146/146(超 10 分钟,由验收方本机 nohup 跑,你只需跑新文件+受影响面:test_batch18_shared_bundle_witness、test_batch18_manifest_stage2_loop、test_repair_batch1、test_r9_batch3_release_guards、test_reconcile_v4_receipt、test_handoff_manifest、changelog_lint、docs_lint --all、test_version_consistency)。
- 版本五处同步(VERSION/pyproject/SKILL.md:23/CHANGELOG 索引+详情),CHANGELOG 6.54.1 六栏,写明三条来源=批 18 盲审 P1×2+P2。
- 不 commit,施工完成即停,由验收方验收后提交。
