# 工单W4复核r2：退回

**剩余 1 项必改：事实⑥对实测结论的表述超过了 P2 已记录的证据。** r1 的其余 8 条已正确吸收；合并设计、旧证据兼容路径和施工白名单均具备可行性。

目标是减少每个修复候选的一次 SQD 查询，同时保留状态判断、census 交易内容和跨代认领能力。支持方案的最强依据是两个查询针对同一 slot，且 P2 已观察到组合响应同时包含交易和匹配指令。反对当前直接定形的关键是：**数量一致不能证明内容一致，现有记录也没有 census-only 对照。** 补齐这一证据即可消除本轮阻断，不需要改换方案。

复核基线为 `60c88b88a024bf463e819d846b1ba3a9e06c7ecd`。工作树干净；`cc6298b` 祖先检查 exit 0；生产源码等指定路径相对 `cc6298b` 的差异检查 exit 0。全程离线，未新建、修改文件，未 commit；未读取 `~/.codex/`、memories 或其他指定禁区。未运行测试，以下均为源码与文档静态复核结论。

下文工程文档路径均相对于 `maintenance/repair-20260924b-sol-stage1-speed/`。

**r1 九条吸收核对**

| r1 条目 | v2 落点 | 结论 |
|---|---|---|
| 1．纠正版本钉注释 | L10 事实⑤ | 已吸收，准确区分 `repair_getblock_body` 与 `_census_body`。 |
| 2．组合选择器实测 | L11 事实⑥ | **未完整吸收**：有正、零匹配样本，但缺三组内容对照，详见必改项。 |
| 3．复用 d4 选择器 | L28、L35 | 已吸收，通过已有 `sqd_query_body` 导入取得字段和选择器。 |
| 4．请求次数、β 范围、错误时序 | L25、L27、L36–37 | 已吸收，区分流程与实际重试次数，允许必要的异常顺序变化。 |
| 5．新采与认领证据区分 | L26、L46 | 已吸收，旧摘要保留，明确独立旧格式和混合代测试。 |
| 6．计数与故障测试 | L41–47 | 已吸收，逐 slot 计数、并发、边界计数和两类故障均有要求。 |
| 7．登记早于正式验收 | L18、L52 | 已吸收，WR-a 登记后使用真实入口验收，不放宽 resolver。 |
| 8．禁读夹具与临时目录 | L20–21、L46 | 已吸收，新增测试自包含，受限旧套件由调度方补验。 |
| 9．行数、锚与事实② | L7、L15、L19、L29–30 | 已吸收，差异按 W1 收官基线计算，派工时重新核行号。 |

**事实段与源码锚核对**

实际执行了 `grep -n -F -x -- '<完整原文行>' <文件>`，核对的 **49 条源码锚均恰命中一次，行号相符**；同时阅读了相关函数上下文。

| 事实 | 亲核结果 |
|---|---|
| ① | `sqd_gap_repair.py:1022/1024/1026/1030/1044/1052` 调用顺序准确；`:933` 保存原始指令数量；`:900` 重试、`:181` key 切换、`:607` α/β 候选合并均符合描述。 |
| ② | `:1284` evidence 构造、`:745` ledger 校验、`:783` 认领校验、`:978` 旧摘要恢复均成立。深验 `solana_exact_validate.py:1594–1606` 不要求两组摘要互异；搜索该文件无 `_census_body`、`sqd_query_body` 引用，`:1225` 重算的是 getBlock 请求摘要。 |
| ③ | live transport 在 `:108` 共用 SQD 端点；fixture 在 `:85` 按请求 digest 查表；β fingerprint 在 `:483`，确实应保留。 |
| ④ | 主夹具三类响应、Batch 8 已有 census 分支及四次调用／2、4、8 秒重试断言均准确。两个 `main` 行号准确。 |
| ⑤ | plan digest 绑定 producer sha、版本钉注释实际内容、正式 resolver 的登记要求均准确。 |
| ⑥ | P2 支持“观察到组合响应及指令数量一致”；不足以支持工单已写出的完整等价结论。 |

另在允许读取的 `scripts/solana`、`scripts/lib`、`scripts/tests` 范围搜索 `_state_probe`，仅命中定义 `:917` 和调用 `:1024`。

**1．必改：补齐实测对照，收窄事实⑥**

依据：`review_W4_reply_r1.md:38` 明确要求 probe-only、census-only、combined 三组对照；`fable_probes_20260924.md:16–22` 只有合并交易数量和单独探针指令数量。

具体缺口：

- 没有记录 combined 与 census-only 的交易内容是否相同。
- 指令数量同为 53，不能代替指令内容比较。
- P2 未记录三组共同块头的比较结果。
- P2 将样本标为 HEALTHY，但没有记录工单 L11 新增的“且含其他指令”这一控制条件。

这不证明方案错误；它证明“r1 第 2 条已完全落实”目前无法由指定证据复核。

**替换 `workorder_W4.md:L11` 事实⑥原文：**

> ⑥ **组合选择器实测状态**：调度方 2026-09-24 的 `fable_probes_20260924.md` §P2 已记录：slot 326000400 的 combined 响应包含 header/instructions/transactions，instructions 数量与单独探针均为 53；slot 326000396、426241113 的 combined 响应有块头、无 instructions 键，单独探针数量为零。该记录支持组合响应形态及指令数量一致，尚未记录 census-only 交易内容对照、probe-only 指令内容对照和三组共同块头一致性，亦未记录健康样本同时含非匹配指令的控制依据。调度方须在派工前补齐同一 finalized slot 的 probe-only、census-only、combined 三组对照：比较共同块头字段；比较 combined 与 census-only 的完整所选交易字段内容；比较 combined 与 probe-only 的 instruction 内容并保留重复项；记录缺键/null/空数组的原始形态。至少覆盖“有匹配且有非匹配指令”的有头块，以及零匹配有头块。全部一致后才将合并查询等价替代写为已验证结论；HTTP 错误或空返回不能替代上述有头样本。

**2．建议：补一类无目标块头的服务端样本**

P2 的三个样本全部有块头。工单也修复 `MISSING_BLOCK`，因此仍缺“无目标块头”这一响应类型。它与“有头但零匹配”不同：前者必须得到 `present=False`，后者是 `present=True、nonce_count=0`。

v2 L43 已要求离线正反例，故此项不另列为派工阻断。`null`、空数组、重复块、253/255/256 边界可由离线夹具覆盖，无需逐项增加在线实测。

**在 `workorder_W4.md:L11` 事实⑥后追加：**

> 建议实测另覆盖一个已独立确认 SQD 无目标块头的 finalized slot，记录三组查询的 HTTP 状态及原始响应形态，验证 combined 同样无目标块头。不得把失败、截断或来源不明的空响应计作该样本。此项补充服务端响应形态证据；§2.5 的 MISSING_BLOCK 离线正反例仍须执行。

**3．建议：给深验兼容测试补上可执行的自包含构造路线**

**§1.2 和 §2.5 可以在现有夹具体系构造，无需扩大白名单。**

已存在的部件包括：

- `test_sqd_gap_repair.py:170–222`：自包含的 10,000-slot coverage/base 构造器。
- `:277–302`：代码内构造的 nonce 缺失交易和余额变化，无需 `.staging_b3`。
- `:234–266、:396`：transport 响应及 fixture 写入器。
- `:820–954`：前代 plan 重建、前缀认领、旧证据不变和深验检查的现成组织方式。
- `sqd_gap_repair.py:232–238`：已存在且内容相等的 evidence 直接保留；`:978–985` 原样恢复旧摘要。

旧格式构造必须独立于新 `_census_body`；否则只换 producer 标识仍会生成“新格式伪装旧代”。此外，深验用例至少要有一个真实构造的 confirmed 缺失交易，以避免全部 refuted 导致不发布代、根本未到 bundle 深验入口。

**在 `workorder_W4.md:L46` 深验兼容条款后追加：**

> 构造路线：复用 `build_batch3b_case`，missing transaction 使用测试代码内构造的 nonce 交易及 token balance 变化，不调用 `staged_missing_transactions`。旧格式 helper 显式固定旧 probe-only/census-only 模板及各自响应，独立计算四个摘要并形成 evidence/ledger；选择已登记前代 sha，保持 base、coverage、候选及 reference 身份不变，重算前代 plan_digest。分别构造全旧格式、全新格式和旧前缀＋新剩余 slot 三类用例。用于发布及深验的用例至少包含一个 confirmed 缺失交易，避免 refuted-only 提前返回。各用例可单独调用，并同时接入现有 main；登记前的直接深验不替代 §3 登记后的正式入口验收。

**4．建议：明确 W1 保护边界，增加继承状态的合并路径回归**

**按现有串行派工方式，W1 与 W4 没有必然的函数修改冲突。** W1 只改本脚本 `validate_coverage_state_consistency`；W4 修改 `_census_body`、`_fetch_live_slot`、删除 `_state_probe` 并补注释，触点不重叠。

但两者存在语义衔接：W1 允许 β 候选中的 `INHERITED_REFUTED` 按“有头且零 nonce”通过。W4 必须保留这一判定，且共同测试文件的 `main` 不能覆盖掉 W1 新增用例。当前尚未有 W1 收官实现可供复核；填实 `<W4_BASE>` 后仍需重核。

**在 `workorder_W4.md:L27` §1.3 后追加：**

> 本条“函数判定与异常文案不变”以 `<W4_BASE>` 的 W1 收官实现为准；W4 不修改 `validate_coverage_state_consistency` 函数体，保留 W1 对 INHERITED_REFUTED 的 β 兼容及 α 拒绝规则。§2.5 增加自包含合并路径回归：INHERITED_REFUTED＋β＋有头＋零 nonce 通过；同状态非 β 拒绝；β 下无头或非零 nonce 拒绝，拒绝发生在 Helius 调用前。保留 W1 已加入测试文件及 main 的用例。差异与 ≤60 行额度仅相对填实后的 `<W4_BASE>` 计算。

| 条目 | 等级 | 依据文件:行 |
|---|---|---|
| 1．事实⑥缺三组内容对照，结论超出记录 | **必改** | `workorder_W4.md:11`；`review_W4_reply_r1.md:38`；`fable_probes_20260924.md:16` |
| 2．补无目标块头的实测样本 | 建议 | `fable_probes_20260924.md:18`；`workorder_W4.md:43`；`scripts/solana/sqd_gap_repair.py:583` |
| 3．明确自包含旧／新／混合证据构造路线 | 建议 | `scripts/tests/test_sqd_gap_repair.py:170`、`:277`、`:820`；`scripts/solana/sqd_gap_repair.py:1492` |
| 4．保护 W1 判定并补继承状态合并回归 | 建议 | `workorder_W1.md:21`、`:32`；`workorder_W4.md:27`、`:47`；`scripts/solana/sqd_gap_repair.py:576` |
