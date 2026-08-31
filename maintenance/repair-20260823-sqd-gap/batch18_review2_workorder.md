# 批 18 第二轮盲审消化工单(b18r2):witness payload 冻结 + 文件闭包完备化

基线:main=8ae0f63(v6.54.1)。第二轮盲审 review-mthvbju6(base=19c0fa6)两条 P1 均 CONFIRMED,一次消化。
版本:6.54.1 → **6.54.2**(既定契约内加固)。

## 纪律(与 b18r1 相同)
- 先红后绿:红证据原文存 `maintenance/repair-20260823-sqd-gap/batch18_review2_red_evidence.txt`,取证于任何生产改动之前。
- 白名单:`scripts/report/shared_release_receipt.py`、`scripts/tests/test_batch18_review_digest.py`(**只许追加新测试函数,不许改既有断言**)、`VERSION`、`pyproject.toml`、`SKILL.md`(:23)、`CHANGELOG.md`、本目录 `batch18_review2_red_evidence.txt`/`batch18_review2_done.md`。其余一律禁改(含 handoff_manifest.py、audit_release_gate.py、scripts/lib 全部、既有测试断言、ARC 案根、API key)。
- 锚点以 8ae0f63 为准,开工先 grep 亲核;不符即停工。
- 完工不 commit。

## F1(P1)witness payload 可原地篡改 → payload 摘要冻结
锚:`shared_release_receipt.py` 中 `DeepReconciliationWitness`(frozen=True, eq=False,字段 root/report_sha256/target/receipts/bound_files)——frozen 只挡字段再赋值,`target`/`receipts` 是可变 dict,合法签发后原地改内容,身份检查(同一对象)与 bound_files 重哈希全过,消费假 payload。
红:真实签发 witness 后 `witness.target["as_of_block"] += 1`(或改 receipts 嵌套值),`validate_bundle(root, reconciliation_provider=lambda: witness)` 在基线返回 `[]`。
修法(定形):
1. witness 增字段 `payload_sha256`:签发时对 `(target, receipts)` 做 canonical JSON 摘要(`json.dumps(..., sort_keys=True, ensure_ascii=False, separators=(",",":"))` 后 sha256;模块内 :230 附近已有 canonical 摘要先例,能复用就复用)。
2. 消费三验增加:重算 payload 摘要,不符 → 同一 `ValueError("reconciliation witness 无效/过期")`。
3. 纯函数夹具态(wrapper 缺失空哨兵)同样计算 payload 摘要,行为不变。
绿:原地篡改 target/receipts(各一式)均拒;未篡改照常通过。

## F2(P1)闭包只扫 inputs/holder_outputs 两节 → 递归 ref 形状扫描
锚:`_reconciliation_bound_files`(v6.54.1 新增,只收 wrapper、checks[key].receipt、各 receipt 的 inputs/holder_outputs 两节、冻结 bundle)。深验实际还解引用(亲核证据,:1179-1330):Solana supply receipt 顶层 `receipt["output"]`(:1241 后 ref_ok);supply_truth 的 `inputs.observation_bundle` 所指 bundle 被整个读入深验(:1310-1320),bundle 内部又有 holder_outputs 实物 ref(solana_observation.py:638 自行核 sha);另有 `_validate_tolerance_policy`/`_bound_replay_totals`/`_validate_anchor_receipt`/`_validate_evm_reconciliation_receipt`/envelope `validate_receipt`(receipt_validate.py)各自解引用。**手工枚举必漏且随深验演进回归**;三处哈希实现分散(shared.sha :85、solana_observation.sha256_bytes、receipt_validate 自带 digest),无单一汇聚点可挂记录器且 lib 层禁改。
修法(定形——形状驱动递归扫描,过严方向安全):
1. `_reconciliation_bound_files` 重写:从 wrapper 出发做 BFS。对当前 JSON 文档递归遍历一切嵌套节点,凡 `dict` 含字符串 `path` 键即视为文件引用候选;解析基准依次尝试 ①案根 ②该 ref 所在 JSON 文件的父目录(覆盖 holder_outputs 相对 receipt 目录的语义),每个基准下 resolve 后必须仍在案根内(containment,拒 symlink),存在且是文件 → 登记 `(绝对路径, 当前磁盘 sha)`;两个基准都命中且不同文件 → 都登记(过严安全)。
2. 登记到的 `.json` 文件若未扫描过 → 读入(解析失败跳过)继续递归;硬上限:文件数 ≤128、递归深度合理,防环(按绝对路径去重)。
3. wrapper 本体与冻结 bundle 照旧必收;b18r1 的 RECON_CHECK_KEYS 定向收集可保留为并集或由扫描覆盖后删除,done 说明取舍。
4. 大白话注释写明设计:闭包宁多勿漏——多绑无关文件的代价只是 witness 提前过期重签(闸每 run 重验一次),漏绑才是放行过期证据。
红:真实签发 witness 后,篡改 supply receipt 顶层 `output` 所指实物(基线闭包未含它)→ `validate_bundle(..., provider)` 基线返回 `[]`;有第二漏项(如 supply_truth 绑的 observation bundle 文件本体)也一并取证更佳。
绿:上述篡改均拒;未篡改照常通过;闭包集合断言含 output 实物与 bundle 本体。

## 回归与收尾
- 既有全部测试不改断言跑绿,重点:`test_batch18_review_digest.py` 既有 3 组、`test_batch18_shared_bundle_witness.py` 6 组(N11 errors 逐字)、`test_batch15_three_ledgers_frozen.py` 12 组(N9 calls==1/N10 calls==2——bound_files 扫描在签发时一次完成,不得增加深验调用次数)、`test_r9_batch3_release_guards.py`、`test_reconcile_v4_receipt.py`、`test_repair_batch1.py`。
- 新测试追加进 `test_batch18_review_digest.py`(F1×1、F2×1,进该文件 main 列表);SUITE 分母不变(146)。
- 版本五处同步 6.54.2;CHANGELOG 六栏,来源=批 18 第二轮盲审 P1×2。
- 定向自测范围同 b18r1;全量 146 由验收方本机 nohup。
