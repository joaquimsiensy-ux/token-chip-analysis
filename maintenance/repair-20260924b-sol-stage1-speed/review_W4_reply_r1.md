# 工单W4复核：退回

合并请求的方向成立，但 v1 存在源码事实错误、约束相互冲突、旧代兼容测试缺口，以及 producer 登记晚于正式验收的问题，尚不能直接派工。

复核基线：`HEAD=0ff40352cbb4e0b0264661d20868e29675c437b7`；包含 `cc6298b`，祖先检查 exit 0；工作树干净。全程离线、未修改文件、未 commit；未读取任何指定禁读路径。未运行会写临时文件或读取禁读夹具的测试，以下不把静态检查写成测试 PASS。

支持方案的最强依据是：两个请求针对同一 slot，合并既能减少一次请求，也能消除两次观测之间的状态漂移。反对直接施工的最强依据是：本地文档没有证明组合选择器的响应语义，而正式消费者也不会自动接受未登记的新 repair producer。决定能否收官的关键，是组合查询实测、旧新 evidence 混合认领测试，以及登记与验收的顺序。

**事实段 ①–⑥ 亲核结果**

| 事实 | 核对结果 |
|---|---|
| ① | `_fetch_live_slot:1022`、调用 `:1024`、一致性检查 `:1026`、Helius `:1030`、census `:1044`、块头对照 `:1052` 均准确。应称“无重试时两次 SQD 调用”；`nonce_count` 在 `:933`，`:934` 是响应序列化。157,700 个候选来自 README 的调度方报告，本仓库不能独立复算该业务数字。 |
| ② | 字段流向成立；具体 evidence 构造在 `:1284–1298`，不是函数定义行 `:1226`。validator 不重建 SQD 请求体摘要；也没有两组摘要必须不同的断言。`_verify_adopted_record:783` 不触及 `coverage_probe_*`，但还检查历史 producer、前代 plan digest、候选前缀，不能概括成“只核 ledger 行与 getBlock 参数”。 |
| ③ | transport 分流及 fixture digest 查表成立。`_probe_fingerprint:483` 确实使用 `sqd-probe`，必须保留。不过后续 `_fetch_live_slot` 为 α/β 候选共用。 |
| ④ | 夹具描述成立。Batch 8 在 `:61` **已有** census 分支；不能把 `:57` probe 分支简单改名。`:317` 明确是在测试 `_sqd_call_with_backoff`，并未调用 `_state_probe`。 |
| ⑤ | plan digest 绑定 producer sha 成立；`:47` 注释引述错误，实际是 `repair_getblock_body`。现役 repair sha 为 `3f89aab13054be76711d85d15a3e4f21d6113c35c905f55a8e60edb31ba8446b`，已登记。 |
| ⑥ | 两个独立模板存在，但 §13 没有组合选择器实录，不能证明组合响应中的 `instructions` 仍仅包含匹配指令。**需调度方本机实测。** |

以下各条均给出可替换进工单的文字。行号指本次 HEAD。

**1．必改：纠正事实⑤的注释引述**

依据：`scripts/solana/sqd_gap_repair.py:46–49` 实际说明共享交易版本常量及 `repair_getblock_body`；`scripts/solana/sqd_repair_core.py:59–82` 绑定 producer sha。

替换工单 **L9 事实⑤**：

> ⑤ `compute_plan_digest`（`scripts/solana/sqd_repair_core.py:59–82`）绑定 producer sha；`_plan`（`sqd_gap_repair.py:619–620`）取当前脚本文件 sha，因此本单修改该脚本会换代。`:46–49` 现有注释针对共享 `SOLANA_MAX_SUPPORTED_TX_VERSION` 与 `repair_getblock_body`，未提 `_census_body`。跨代认领须满足前代 sha 已登记、除 producer 外的 plan 身份可重现、成功记录构成候选前缀等条件；不是任意旧 pending 都能认领。登记与正式验收顺序按本单修订后的收官要求执行。

**2．必改；查询语义存疑：事实⑥不能把推断写成实录**

`data-pipeline-solana-capture.md:128–142` 证明的是进度行、零行、204 和流完整性；`:158–159` 说明交易索引及非投票交易口径。没有同时使用 `transactions`、`instructions` 的对照结果。

替换工单 **L10 事实⑥**：

> ⑥ 现有探针模板 `sqd_coverage_probe.py:128–136` 与 census 模板 `sqd_gap_repair.py:643–653` 分别证明两个选择器已有独立用法；`data-pipeline-solana-capture.md` §13 不包含组合选择器的响应实录。因此，“合并后同时获得 census 交易数组与仅匹配 AdvanceNonce 的指令数组”目前是待验证前提，需调度方本机实测。正式验收前，对同一 finalized slot 执行 probe-only、census-only、combined 三组查询：核对块头一致、combined 的交易内容与 census-only 相同、combined 的指令内容与 probe-only 相同。至少覆盖有匹配指令且同时含其他指令的块，以及零匹配指令的有头块；空数组是否省略单独记录。HTTP 错误、204、空响应或控制样本不满足条件均不能算验证成功。实测失败须退回方案，不得把全部指令数量当 nonce_count。

以下是供调度方执行的最小三组命令，**本次未执行**。`326000396` 只是仓库 census 测试使用的 slot，不能预先认定它满足正样本条件：

```sh
slot=326000396
for mode in probe census combined; do
  printf '\n%s\n' "$mode"
  python3 -c '
import json, sys
slot, mode = int(sys.argv[1]), sys.argv[2]
q = {
    "type": "solana", "fromBlock": slot, "toBlock": slot,
    "includeAllBlocks": True,
    "fields": {"block": {"number": True, "hash": True}}
}
if mode != "probe":
    q["transactions"] = [{}]
    q["fields"]["transaction"] = {
        "transactionIndex": True, "signatures": True, "err": True
    }
if mode != "census":
    q["instructions"] = [{
        "programId": ["11111111111111111111111111111111"],
        "d4": ["0x04000000"]
    }]
    q["fields"]["instruction"] = {"transactionIndex": True}
print(json.dumps(q))
' "$slot" "$mode" |
  curl --silent --show-error --fail-with-body --compressed \
    --max-time 60 \
    -H 'Content-Type: application/json' \
    --data-binary @- \
    --write-out '\nHTTP %{http_code}\n' \
    https://portal.sqd.dev/datasets/solana-mainnet/stream
done
```

**3．必改：`d4` 没有可导入常量，§1.4 与 §2.1 冲突**

`SYSTEM_PROGRAM` 定义在探针 `:42`；`"0x04000000"` 只是在 `sqd_query_body:135` 内直接写出的字符串。§1.4 要求两者都导入，§2.1 却要求复制字符串，不能同时满足。

建议通过已有模板复用，保持生产白名单不扩张。替换 **L27 §1.4、L34 §2.1**：

> 1.4 `_census_body` 保持现有 block/transaction fields、transactions 选择器及原有键的相对顺序，只追加探针所需的 instruction fields 与 instructions 选择器。通过本文件已导入的 `sqd_query_body(slot, slot)` 取得这两项，不新增或复制 SYSTEM_PROGRAM/d4 常量，不修改探针模板。
>
> 2.1 在 `_census_body` 内取得 `probe_body = sqd_query_body(slot, slot)`；在原 census 的 fields 中追加 `"instruction": probe_body["fields"]["instruction"]`，在顶层追加 `"instructions": probe_body["instructions"]`。其余字段保持原值；无需新增 import。

**4．必改：明确请求次数、β 范围及错误路径变化**

三个现状不能忽略：

- `_sqd_call_with_backoff:900–913` 最多调用 transport 四次；Helius pool `:181–190` 可切 key 重试。“恰一次实际请求”不成立。
- `_plan:607–608` 合并 α/β 候选，共用 `_fetch_live_slot`。改变该函数也改变 β 候选进入修复后的请求。
- 一致性检查仍可放在 Helius 前，但 census 从 Helius 后前移，错误优先级必然改变。

替换 **L24 §1.1、L26 §1.3**，并作为 **L35 §2.2 的补充**：

> 1.1 对本轮尚未恢复的 live 修复候选，每 slot 只执行一次合并 SQD 查询流程；无故障、无重试时为一次 sqd-census transport 调用，状态校验通过后执行一次 reference_pool.get_block。保留 SQD 重试与 Helius 多 key 故障转移，实际请求数可大于一；已恢复 slot 不再请求。β 搜索阶段的 `_beta_body`、`_probe_fingerprint` 及其请求模板保持不变；β 候选进入共用修复流程后同样使用合并查询。
>
> 1.3 与被替换的 `_state_probe` 保持相同的 present/nonce_count 计算：只统计 header.number 等于目标 slot 的块，匹配块超过一个则拒绝；无匹配块时 present=False、nonce_count=0；有匹配块时 nonce_count=`len(block.get("instructions") or [])`。缺键、null、空数组均按零处理。这里保存原始长度，不按 255 截断。coverage 普查的 `min(255, 2 + len(instructions))` 是另一个编码层，不是修复 nonce_count。`validate_coverage_state_consistency` 保持在 Helius 调用之前，函数判定与其自身异常文案不变。
>
> 2.2 补充：允许且须测试以下可观测变化：SQD 传输失败及重复块错误现在先于 Helius 发生；原两请求块头不一致错误被取消，重复块错误改为 census 文案。SQD 返回合法响应且状态匹配时，Helius pool 耗尽仍抛 QuotaStopped；若 SQD 自身先失败，则可能先返回普通错误而不进入额度停工路径。不得宣称全部异常顺序和文案不变。

ledger 的实际时序也应写清楚：

> `_fetch_live_slot` 只构造 ledger_row；slot 的成功行在 `_persist_live_slot` 写出两份 evidence 后才追加。初始化 ledger header 可早于网络请求。失败 slot 不追加成功行；QuotaStopped 由上层写 STOPPED 并返回 3。并发运行保留按候选顺序落盘、已完成前缀和取消未开始任务的既有规则，不保证错误发生时其他 worker 尚未发请求。

依据：`sqd_gap_repair.py:729–736、989–995、1120–1142、1164–1180、1463–1470`。

另外，“与探针完全一致”只能指旧 `_state_probe`：普查 `_scan_request:377–380` 还检查 instruction 数组类型并执行饱和编码；本单没有复制那套全部输入校验。

**5．必改：兼容性要求须区分“新采证据”与“认领证据”**

亲核结论：

- 深验不要求两组摘要互异，同值可通过这项检查。
- `_verify_adopted_record` 不读取 SQD evidence 摘要；`_verify_ledger_rows:745–779` 也不重建 census 请求。
- `_payload_from_evidence:978–985` 原样恢复旧摘要，因此旧分离摘要有可保留的路径。
- `sqd_repair_core.py` 没有其他 census 请求重算。其 `instructions` 用法在 `:183–201`，对象是参考交易 message，用来识别 vote/nonce，并不依赖 SQD census 块缺少 `instructions`。

实际执行的核对命令：

```text
grep -nE '_census_body|sqd_query_body' scripts/lib/solana_exact_validate.py
无输出，exit 1

grep -nE 'query.*sha256|coverage_probe_' scripts/lib/solana_exact_validate.py
相关检查位于 528–530、779–783、1151–1154、1601–1606
```

同时检查了该文件所有 SHA 计算入口；`:1225` 重建的是 **Helius getBlock** 请求摘要，不能把它误称为 SQD 重算。

替换 **L25 §1.2** 相关要求，并补入 **L41 深验测试**：

> 1.2 evidence/ledger/resolution/bundle schema 与字段名不变。本单新采集的 evidence，其 coverage_probe_query_sha256 与 query_body_sha256 相等、coverage_probe_response_sha256 与 response_sha256 相等；从前代恢复或认领的 evidence 保留原摘要，不要求两组相等，也不得改写以制造相等。允许同一新代同时包含前代分离摘要和本代合并摘要。formal nonce_count 继续为非负整数。
>
> 2.5 深验兼容：保留独立的旧格式证据构造，显式使用旧 probe-only 与 census-only 请求及分离响应计算摘要，不能随 `_census_body` 改动自动变成新格式。分别验证旧格式、新格式，以及“认领旧格式前缀＋新格式剩余 slot”的混合代。认领用例须断言旧 evidence 字节不变、旧 slot 无重新请求、新 slot 两组摘要相等、最终深验通过。

现有 `adoption_regressions:842–880` 先用当前生产者生成 pending，再换 producer 标识。因此改掉公共夹具后，它不能单独证明“真正的旧分离证据仍兼容”。本次只能确认源码支持该路径，不能报告旧代测试已经 PASS。

**6．必改：§2.5 的计数和故障测试不足，Batch 8 修改指令有误**

替换 **L39–41 §2.5** 的测试要求：

> - 测试计数在测试侧包装 transport，不向生产 `RepairFixtureTransport` 添加计数功能。对无重试、无额度切换、无 resume、无 β 搜索的正式运行，逐 slot 断言 sqd-census=1、sqd-probe=0、reference-getBlock=1；总数同时等于候选数。至少覆盖 workers=1 和现有并发路径，避免总数相等掩盖某 slot 重复、另一个漏调。
> - 三个基础向量明确前置状态与副作用：① DEFECT_CANDIDATE＋有头＋非空 instructions，拒绝且异常含指定状态变化文案，Helius 调用为零、无该 slot 成功 ledger 行；② 两个匹配目标 slot 的块，拒绝且异常含 duplicated，Helius 调用为零；③ DEFECT_CANDIDATE＋有头但缺 instructions 键，按零通过，并核 evidence 的 nonce_count 和摘要。
> - 补充 null/空数组、MISSING_BLOCK 的无头正例与有头反例；以 beta_candidate=True 的 HEALTHY 用例检查 253、255、256 条指令仍保存原始长度，避免把 coverage 编码误用于修复计数。
> - 对 SQD 重试耗尽与 Helius quota 组合故障，断言先后顺序、返回码、STOPPED 和成功 ledger 前缀符合 §1.3。保留现有额度切换、resume、并发有序落盘和 β 搜索回归。
> - `test_batch8_repair_scale.py:61–68` 已有 sqd-census 分支，在此追加 instructions；`:57–59` 的 sqd-probe 分支按是否仍有测试用途保留或删除，不得直接改名遮蔽现有 census 分支。`:316–322` 是 `_sqd_call_with_backoff` 重试测试，保留“四次调用、2/4/8 秒”断言，可增加 sqd-census 参数覆盖，不写“若针对 _state_probe”。
> - 深验、旧证据和混合认领测试按 §1.2 执行；新增测试必须接入这些脚本实际使用的 main 测试入口。

**7．必改：登记全留 W2，会留下正式消费者拒绝的新代**

用户特别要求检查的 `producer_sha == current_sha or ...`，只出现在 `solana_exact_validate.py:495–506` 的 **coverage producer** 校验。

修复正式入口 `sqd_cache_identity.py:143–147` 则要求：

```python
allowed = historical_producer_hashes(
    REPAIR_COLLECTOR_SCRIPT, "sqd-solana-cache/v4")
if bundle.get("producer", {}).get("sha256") not in allowed:
    raise ValueError("formal repair producer is not registered")
```

修复生产者发布后直接调用深验（`:1611`），可能通过并发布指针，但随后正式 resolver 会拒绝。现有消费者测试还在 `test_sqd_gap_repair.py:319–330` 临时替换登记查询，不能用它证明未登记状态可正式验收。

替换 **L1、L9、L17 中“登记归 W2”安排**，并补入 **§3 收官要求**：

> W4 施工者仍不修改 producer_history；调度方在 W4 代码冻结并提交后，立即按该可复算 commit 的脚本 sha 追加独立登记 commit，完成四个现有协议的 ACTIVE 登记，保留需要认领的前代记录。此登记步骤纳入 W4 收官前置条件，不等到 W2 结束。W2 负责版本与文档汇总。
>
> W4 收官须在登记完成后，以未替换历史登记查询的真实入口验证 `validate_repair_bundle(deep=True)` 和 `resolve_formal_cache`。仅直接调用 `validate_repair_bundle_deep` 或使用测试侧登记替身，不构成正式消费者验收。收官报告记录代码 commit、登记 commit 和对应 sha。

这不要求放宽 `sqd_cache_identity.py`，也不应给它增加“现役 sha 自动接受”的豁免。

**8．必改：测试纪律与禁读路径冲突；临时目录继承条款也不可照搬**

`test_sqd_gap_repair.py:226、427、436、544` 读取 `.staging_b3`；Batch 8 的 `main:328` 间接调用同一夹具函数。W1 §0.6 又要求在 `.staging_w1` 建临时目录并执行 `rm -rf`，与禁读及本会话删除纪律冲突。

替换工单 **L19–20 §0.6–0.7**：

> 0.6 离线、不 commit/push、禁 stash/checkout/reset；临时数据仅用环境允许的系统临时目录，不使用 `.staging_*`，不执行批量删除命令。环境禁止写入时，只做源码复核并如实列出未运行项。
>
> 0.7 保留定向测试清单，补入 `python3 -B scripts/tests/test_batch3c_census_fields.py`。运行前检查直接及间接夹具依赖。现有 `test_sqd_gap_repair.py` 与 `test_batch8_repair_scale.py` 依赖禁读 `.staging_b3`，施工者不得执行触及这些数据的用例；新增 W4 测试使用测试代码内构造的自包含数据。受限旧套件由调度方在其有权访问原夹具的验收环境运行并附结果。施工报告区分 PASS、FAIL、未运行及原因；调度方补齐必需结果后才可收官。

白名单本身足以完成合并及自包含新测试；`test_batch3c_census_fields.py:26–35` 无需修改，其现有断言允许新增 instruction fields，但它应加入运行清单。`producer_history.py` 的调度方登记属于上一条明确的独立收官步骤。

**9．建议：保留 ≤60 行上限，修正锚与事实②表述**

≤60 行并非不现实。本次只在内存中按 §2.1–2.4 构造直译版本，未写文件，差异估算为 **新增 19 行、删除 35 行，合计 54 行**，且语法解析通过；这只是可行性估算，不是施工或行为测试。无需仅凭复杂度提高上限。

替换 **L29 §1.6**：

> 1.6 生产文件增删合计 ≤60 行，以 `git diff --numstat <本单基线> -- scripts/solana/sqd_gap_repair.py` 统计；测试与报告不计入此限额。不得为压行数省略输入处理、改变既有重试或压缩可读性。生产范围不新增 CLI 参数。

替换 **L6 事实②末段、L36 §2.3**：

> 深验在 `solana_exact_validate.py:1594–1606` 对 nonce 状态及四个摘要字段进行检查，不重建 SQD 查询体，也不要求 probe/census 摘要互异。`_verify_adopted_record:783–815` 校验前代登记、plan digest、候选前缀及 getBlock 参数摘要，不触及 coverage_probe_*；`_verify_ledger_rows:745–779` 也不复算 SQD 摘要。
>
> 2.3 删除 `_state_probe` 前，在允许读取的源码范围内确认只有函数定义 `:917` 和调用 `:1024` 两处命中；“仅一处”指调用，不包含定义。删除后确认无剩余引用，保留 `_probe_fingerprint:483` 及其 sqd-probe transport 支持。

此外，当前 HEAD 尚为工单立项提交。**L14 §0.1 的 `<本单基线>` 必须在 W1 收官后填实，validator 等受 W1 影响的行号重新核对**，不能把当前审阅行号直接当后续施工锚。

| 条目 | 等级 | 依据文件:行 |
|---|---|---|
| 1. 事实⑤错误引述注释 | 必改 | `scripts/solana/sqd_gap_repair.py:46`；`scripts/solana/sqd_repair_core.py:59` |
| 2. 组合选择器缺实录 | 必改／语义存疑 | `references/data-pipeline-solana-capture.md:128`；`scripts/solana/sqd_coverage_probe.py:128` |
| 3. d4 导入要求不可执行 | 必改 | `scripts/solana/sqd_coverage_probe.py:42`、`:135` |
| 4. 请求次数、β 范围、错误时序 | 必改 | `scripts/solana/sqd_gap_repair.py:181`、`:607`、`:900`、`:989`、`:1022` |
| 5. 旧摘要与混合认领测试 | 必改 | `scripts/lib/solana_exact_validate.py:1601`；`scripts/solana/sqd_gap_repair.py:783`、`:978`；`scripts/tests/test_sqd_gap_repair.py:842` |
| 6. 计数及故障向量不足、Batch 8 指令错误 | 必改 | `scripts/tests/test_batch8_repair_scale.py:57`、`:61`、`:316`；`scripts/tests/test_sqd_gap_repair.py:702` |
| 7. 未登记 repair producer 阻断正式消费 | 必改 | `scripts/solana/sqd_cache_identity.py:143`；`scripts/lib/solana_exact_validate.py:495`；`scripts/tests/test_sqd_gap_repair.py:319` |
| 8. 禁读夹具、临时目录与验收清单冲突 | 必改 | `scripts/tests/test_sqd_gap_repair.py:226`；`scripts/tests/test_batch8_repair_scale.py:328`；`maintenance/repair-20260924b-sol-stage1-speed/workorder_W1.md:21` |
| 9. 行数上限可行，锚及表述需精确 | 建议 | `scripts/solana/sqd_gap_repair.py:917`、`:1024`；`scripts/tests/test_batch3c_census_fields.py:26`；`maintenance/repair-20260924b-sol-stage1-speed/README.md:14` |
