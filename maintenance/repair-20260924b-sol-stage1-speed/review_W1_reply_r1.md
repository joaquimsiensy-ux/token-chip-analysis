# 工单W1复核：退回

存在会导致施工失败、错误放行或功能退化的确定问题，需先修订工单。核心阻断是：链式导出使用了错误的候选集合、跨机继承证明不足、新状态破坏 β 修复、发布代绑定不完整，以及白名单与 AST 守卫要求冲突。

本次基线为 `0ff40352cbb4e0b0264661d20868e29675c437b7`；包含 `cc6298b`，工单 §0.1 指定生产路径相对该提交无差异，工作树前后均干净。全程离线；未读取列明禁区、`~/.codex/` 或 memories；未修改、新建文件或 commit。执行了整行 `grep -n -F -x` 核验及纯内存反例检查，未运行会写文件或读取禁区的测试套件。

支持本案方案的最强理由是：源案的整块签名比对可跨 mint 复用，避免重复下载 Helius 大块数据，收益明确。反对现有设计的最强理由是：**“零 nonce 未变”不等于“交易集合未变”**，而继承会直接减少候选、允许 verdict 变为干净。真正需要定形的是：接受什么残余风险、如何证明继承来源，以及如何保留 β 独立发现缺陷的能力。

**1．必改：修正事实段与锚说明**

定位：工单第 5–12 行，事实①–⑦。

逐项亲核结果：

| 事实 | 核验结果 |
|---|---|
| ① | `:557/:573/:670/:743/:778` 均对应。`actual` 包含首轮及重试中**所有 verified 区间**的逐 slot 实测值，不只 canary；不含 mismatch、最终失败区间。`unverified` 在函数内部为 `[(start,end),…]`，写入 info 后为对象数组。失败段涉及 canary 时整图回退，不能概括为“只剔除该段”。 |
| ② | `:1228/:1313/:1333` 均对应。coverage_map 落盘 summary、candidate_slots、verdict，**不落盘 states**。 |
| ③ | `:223/:268/:676/:684–689/:711/:863/:877–880` 断言基本正确。summary 固定 11 键；三项比较确为对象/列表/字符串全等。现有 refuted 只验形态，没有语义核验。 |
| ④ | `:805/:859` 正确；还必须写明 `:858` 的候选来自 `validate_coverage()["recomputed"]["candidate_slots"]`。 |
| ⑤ | α 限制成立，但忽略 β。`_plan` 使用 coverage 候选与 β 候选的并集；未知状态即使属于 β 也会被拒。census 的 `state_in_map` 当前硬编码，真实分类在 `coverage_state`。 |
| ⑥ | 生产代码中直接调用 `classify_four_states` 是 **3 处**；`:1574` 和修复侧 `:1369` 是消费重算 states。后续使用会受新状态影响，不能写成无影响的映射。 |
| ⑦ | 仓库资产存在，refuted 为空；ARC 来源与 TROLL 案侧数据不能从本次可读资产独立确认。须区分仓库事实与调度方陈述。 |

summary 的 11 键为：

```text
slots, unscanned, healthy, no_header, header_zero_nonce,
defect_candidate, era_uncertain, skipped_confirmed,
missing_block_candidate, no_header_unconfirmed, saturated_nonce_count
```

可替换原文：

> ① `_recheck_known_slots` 在 `:625-629`、`:635-639` 收集首轮和重试中全部 verified 区间的逐 slot 实测值，并于 `:645-647` 返回 actual。unverified 在内部为 `(start,end)` 元组列表，`:747-748` 转换为 `{from_slot,to_slot}` 数组。非 canary 失败段局部剔除；canary 所在段最终失败则整图回退。异常分支 `:781-782` 将本轮 recheck 行的 counts_coverage 置 false，`:783` 写 fallback_reason，`:784` 返回 `info,None,None,None`。actual 当前未通过 `_load_known_map` 返回给 run_probe。
>
> ④ export 的 `:858` 使用源 coverage 校验后的有效候选；引入继承后，该集合与共享资产二进制重算候选不再相同，必须分别处理。
>
> ⑤ `_plan(:607-608)` 的修复候选为 coverage.candidate_slots 与 beta_slots 的并集。`validate_coverage_state_consistency` 对未知状态在 α、β 路径均拒绝。census.state_in_map 当前硬编码为 DEFECT_CANDIDATE（`:1337`），真实状态来自 coverage_state（`:1338`）。`sqd_cache_identity.sqd_repair_paths` 是从 spl_edge_core 导入的函数，其定义为 `sqd_repair_paths(case_root,mint)`（spl_edge_core.py:240），返回 mint 哈希命名的 parent、CURRENT.json、.lock（`:245-247`）。
>
> ⑥ classify_four_states 的生产直接调用共三处：probe:1313、validator:676、validator:877。修复生产与深验分别在 repair:1369、validator:1574 消费其 states，且后续进行状态语义检查；新状态必须同时适配这两条路径。
>
> ⑦ 仓库资产 20260827.json 的 generated_at 为 2026-08-25T03:17:11.217739+00:00，candidate_slots 数量为 153667，refuted_slots 为空。ARC 来源及 TROLL 案侧 155642 候选等信息属于调度方外部陈述，本次仓库复核未独立验证。

整行核验还发现：probe `:782` 的整行命中 3 处，validator `:246` 的 `    }` 命中 5 处。它们可作为范围中的行号，不能作为唯一修改锚。§0.5 应改为：

> 行号范围用于定位；唯一锚须选完整非空语义行，不选重复赋值或闭合括号。fallback 使用 probe:783 的完整赋值行，summary 初始化使用 validator:242 的完整字段行。

**2．必改：继承条件不能宣称证明“本案无需修复”**

定位：§1.2、第 27 行；§2.1、第 41 行。

源案 refuted 来自 Helius 非投票交易与 SQD 签名差集为空；当前重查查询只取块号和 AdvanceNonce 指令。删除一笔非 nonce 交易后，counts 仍可为 2。canary 检查同类计数，历史锚检查一个块哈希，finalized head 检查链高度；均未绑定 SQD 历史交易集合。

因此，“SQD 一变即回退全扫”不成立。全扫本身也仍是 nonce 普查。

可替换原文：

> 驳回继承复用源案的整块签名比对结论，本次只重新验证块头存在且 AdvanceNonce 计数仍为零。该条件不能识别 SQD 在同 slot 增删非 nonce 交易且计数保持零的变化。canary、历史块哈希锚和 finalized-head 检查不能消除此残余风险。仅在受检身份、块头或 nonce 计数变化时触发现有回退。
>
> 本方案依赖来源可信及 SQD 已驳回 slot 的相关历史交易集合未发生不可见退化；不得把 INHERITED_REFUTED 表述为本案重新证明了完整性。若要求证明交易集合未变，须保存源 census 的 slot 级交易身份摘要，并以独立 census 查询重查块哈希及规范化交易集合摘要；该查询不得改动现有普查模板哈希。

**建议**采用明确残余风险的最小方案完成当前提速目标；若不接受这一前提，则需要更强重查，原生产行数上限必须重估。

**3．必改：§1.4 不能仅凭自报 SHA、区间和计数完成独立复核**

定位：第 29、55、62 行。

存在三类问题：

- 资产缺席时，添加一个已有成功 recheck、counts=2 的普通候选，再同步修改 count、summary、候选和 probe_id，现有清单无法证明其不属于原资产 refuted。
- `refuted_count` 总和足够只证明数字够大，没有将某条证据绑定到具体 slot。
- probe `:774-777` 会将跨本案边界的成功 recheck 行设为 `counts_coverage=false`。`_successful_coverage_range` 因此返回 None，误拒实际已验证的本案内 slot。

此外，`_successful_coverage_range` 定义在 probe，不在独立 validator；不能在 validator 中直接调用未定义符号或反向引入生产脚本。

可替换原文：

> 非空继承必须携带可跨机验证的来源见证，能够依据 shared_map.sha256 复核原资产 refuted_slots 成员关系；不得仅比较两个自报 SHA。可携带原资产 JSON 原始字节或等价的可验证成员证明，不依赖原 asset_path 在目标机器存在。缺少见证时拒绝非空继承。该绑定证明内容一致性，来源可信仍为明确输入前提。
>
> 检查 shared_map 为成功复用、无 fallback_reason；slots/count/各区间均须严格类型合法，排除 bool，slot 必须位于本案范围后才能索引 counts。继承 slot 必须属于来源 refuted、来源值及本案实测值均为 2，位于实际 reused 范围且不在 unverified 范围。
>
> recheck 成功证明与 counts 覆盖证明分别核验。完整成功但跨案边界、counts_coverage=false 的 recheck 可证明其与本案交集内的 slot；不得因此将案外区间加入 counts 覆盖。验证完整返回、请求范围、查询身份和结果绑定，并拒绝失败、短返回、mismatch 及整图回退记录。独立实现于 validator，不反向导入 probe。
>
> 证据须绑定其支持的 slot 集或可验证映射；refuted_count 必须由该集合导出。校验失败追加原因并清空继承后重算；拒绝依据是 reasons 非空，不依赖“候选比较必失败”。

最后一句也需要修正：继承可能把本案原本的 `ERA_UNCERTAIN` 改为继承状态，清空后 candidate_slots 未必变化。

**4．必改：链式 export 必须区分原始候选与有效候选**

定位：§2.2 步骤 4–5，第 50–51 行。

现有 `:858` 使用有效候选。加入继承后，R1/R2 已被剔除；继续使用它导出，要么丢掉继承 refuted，要么被 `validate_shared_map` 的二进制候选全等检查拒绝。§2.6(e) 按原文无法完成。

可替换原文：

> 源案 validate_coverage 必须成功。随后另用源 counts、confirmation、bitmap 调用 classify_four_states，明确传空继承集，得到 raw_candidates。导出资产 candidate_slots 使用 raw_candidates；不得继续使用 checked.recomputed.candidate_slots。
>
> refuted_slots 为合法 own 与合法 inherited 的并集再与 raw_candidates 相交。仅允许因本案区间或时代窗口不同而不再属于 raw_candidates 的继承项被过滤，并输出原因计数；非法 own、来源绑定失败不得通过求交静默掩盖。证据计数与实际导出的 slot 集同步生成。

**5．必改：修复代绑定不足，且错误过滤 β census**

定位：§1.6；§2.2 步骤 2，第 31、48 行。

主要缺口：

- “已发布”与“CURRENT 若存在才核”矛盾：未发布 gen 也可能被接受。
- `validate_repair_pointer` 只核 envelope、mint、gid、bundle SHA，不核引用路径和 size。
- 缺 resolution schema、mint、coverage.map_sha256、bundle/reference.source 等绑定。
- `{所有 census slot} ⊆ coverage.candidate_slots` 会拒绝合法 β 修复。
- `state_in_map` 是硬编码，必须看 `coverage_state`。
- 后续 β 若对继承 slot 得到 confirmed，链式导出不能继续保留较旧 refuted。

可替换原文：

> `--repair-gid` 仅接受源案当前已发布 formal 代：修复 CURRENT.json 必须存在。校验 gid 为 16 位小写十六进制；调用 validate_repair_pointer 并检查结果；额外核 CURRENT 的 bundle 引用路径解析后恰指向选中 gen/bundle.json，size/sha256 与实物一致，路径不得逃逸修复目录。
>
> 校验 bundle schema/kind/mint/gid、mode=formal、reference.source=live；resolution schema/mint；bundle 与 resolution 的 coverage 均须绑定当前 probe_id 和当前 coverage_map 实物 SHA。coverage_resolution 引用路径、size、sha256 必须绑定所读文件。plan_digest 须合法且一致，producer 按规定的历史/现役集合验证。
>
> census 必须为 slot 严格整数、排序唯一的对象数组，result 使用已知枚举；plan_candidates.coverage 与当前有效候选相同，beta 为合法集合，census 处置须覆盖计划候选，effective_verdict 根据处置重算。不得要求全部 census slot 属于 coverage.candidate_slots。
>
> own 仅取 result=refuted、coverage_state=DEFECT_CANDIDATE、与源 coverage 重算状态相符、counts=2、修复 nonce_count=0、missing_total=0 且块哈希自洽的行。state_in_map 不作真实分类依据。exploration 代禁止导出。
>
> 当前 census 对 inherited slot 的 confirmed 处置优先于旧 refuted；导出时必须去除冲突继承项，不能静默续传。
>
> 本步骤深核发布指针及所消费的 bundle/resolution 绑定，不要求重放整个修复证据目录；后者仍依赖已声明的可信来源前提。

这里不必为“指针深验”强制扫描全部修复边和 getBlock 实物，但必须证明所读的确是当前发布代。

**6．必改：新状态会破坏 β 修复，不改清单必须调整**

定位：事实⑤⑥；§0.3–0.4；§2.4。

纯内存执行现有函数得到：

```text
INHERITED_REFUTED，beta_candidate=False → non-candidate coverage state entered alpha
INHERITED_REFUTED，beta_candidate=True  → SQD coverage state changed before repair
_repair_state_matches(INHERITED_REFUTED, True, 0) → False
```

因此 `:1369/:1574` 不是无影响的状态映射。

可替换原文：

> INHERITED_REFUTED 不进入 α 候选，但不得阻断独立 β 候选。允许最小修改 sqd_gap_repair.py::validate_coverage_state_consistency：保留 α 准入限制，仅在合法 β 路径把 INHERITED_REFUTED 按“有块头且 nonce_count=0”验证。同步修改 solana_exact_validate.py::_repair_state_matches，并保留 census/evidence.coverage_state 与重算状态全等。
>
> 将上述 sqd_gap_repair.py 修改加入白名单，删除其绝对不改限制；不得将新状态伪装成 DEFECT_CANDIDATE 绕过验证。

replay/exact_reconcile 的组合判定**不需要因新 verdict 修改**：无候选且无 unconfirmed 时，base 路径仍接受 `NO_KNOWN_NONCE_OMISSION_DETECTED`；repaired 路径仍要求有效修复、`DEFECTS_CONFIRMED` 和 census 覆盖当前候选。问题在继承证据与 β 状态兼容，不在这两处分支。

可补入 §1.3：

> VERDICTS 与 replay/exact_reconcile 组合规则保持不变；新增测试覆盖继承后 base 干净路径，以及 β 修复后的 repaired 路径。

**7．必改：链式继承必须保留原始证据时效**

定位：§1.6、§2.1 evidence、§2.2 步骤 1。

现有 export 用新源案 pointer.published_at 写 generated_at。每次重新发布再导出，都能刷新 TTL；nonce 不变并不能证明旧 census 仍有效。

可替换原文：

> refuted_evidence 保留初次直接 census 证明对应的 origin_generated_at 与 origin_asset_sha256；链式导出不得用后案 probe 发布时间重置该起点。多来源须保持 slot 与来源时效的对应。
>
> 继承要求当前时间未超过来源原始有效期；重新执行 nonce 重查不延长该有效期。无原始时效信息的非空 refuted 不可继续继承。仅重新执行满足要求的直接 census 才可建立新起点。跨机离线验证按本次探针的验证时点核验当时是否有效，不因日后重验时间推移而否定历史合法发布。

**建议**优先保留原始时效，而不是只限制链深；链深不能准确约束证据年龄。

**8．必改：兼容性要求中的 probe_id、states、空字段表述不成立**

定位：§1.1、第 26 行；§2.3、第 55 行；§2.6(a)；完成报告第 81 行。

`compute_probe_id` 哈希整个 coverage_map，仅删除 probe_id 自身；其中包含 producer.sha256。修改 probe 后，新产物 probe_id 本就应该变化。原测试通过不能证明“前后 ID 不变”。

另外，§2.3 无条件写入空 `inherited_refuted` 对象，会改变没有任何继承的产物结构；states 当前只在重算结果中。

可替换原文：

> 无实际继承时，分类函数的 summary/candidate_slots/verdict/states 与基线同输入结果完全一致；summary 及 shared_map 均不得新增 inherited_refuted 键。states 为分类器及 validator.recomputed 返回值，本单不新增 coverage_map.states 字段。
>
> 保持现役旧产物在新校验器下通过。修改 producer 后新生成产物的 probe_id 允许按现有算法变化，不要求前后相同；测试分别验证分类兼容性、旧产物兼容性和同版本确定性。
>
> 仅当实际继承集非空时写 shared_map.inherited_refuted，并增加 summary.inherited_refuted；计数必须等于实际分类为 INHERITED_REFUTED 的数量。

“summary 新键仅非空时存在”可以保留，**新校验器读旧产物**的兼容策略是合理的。改放 shared_map 也不能使旧校验器理解新候选/verdict，因此没有必要仅为此重设计 summary。

已核基线 probe SHA 登记在 coverage 与 pointer 两个历史协议中，旧产物兼容不要求在 W1 提前修改 producer_history。

**9．必改：CLI 条款互相矛盾，且 mint/current_path 未定义**

定位：§1.7、第 32 行；§2.2 第 45、48–49 行。

export parser 没有 mint 参数；mint 应取已验证 coverage。current_path 应在处理分支前计算。

可替换原文：

> build_export_parser 新增互斥参数 `--repair-gid <gid>` 与 `--no-repair`；§1.7 的 CLI 例外包含这两项。mint 取自已验证 coverage["mint"]，修复 parent/current_path 在分支前统一计算。
>
> 提供 repair-gid 时要求对应当前发布代验证通过；未提供任何选项且存在修复 CURRENT 时拒绝，并明确提示二选一；无 CURRENT 且无选项时允许仅导出继承部分。`--no-repair` 明确跳过自有修复驳回的导出，但不得重新输出已知与当前 census 冲突的继承驳回。

**10．必改：重写测试前提并补齐拒绝路径**

定位：§2.6(a)–(f)，第 71–77 行。

现有夹具体系可以构造全部场景，但不能直接沿用 64-slot 数据。实测：

```text
62 个 code=3 + 2 个 code=2：候选=[]，ERA_UNCERTAIN=2
9998 个 code=3 + 2 个 code=2：候选=[9998,9999]
```

可替换原文：

> 夹具在临时目录动态生成，不新增大型静态 fixture。使用同一 ERA 窗口内至少 10000 个块头，例如 9998 个 code=3、2 个 code=2，确保两目标 slot 是原始候选。按实际连续 recheck 区间及 full 扫描 450-slot 分页生成 request_digest 响应；retry 用 FixtureTransport 已支持的响应序列。
>
> (a) 从 validator.recomputed.states 按 `slot-from_slot` 取状态，检查继承集、候选、summary 和 verdict；不读取不存在的 coverage_map.states。
>
> (b) 为 mismatch 后的 full 扫描补全响应，确认回退成功发布且没有继承键；增加非 canary 失败段、失败后成功重试、canary 最终失败三种情况。
>
> (c) 成员篡改同时覆盖资产在场及资产缺席；增加 fallback 与继承并存、越界/负数/bool/重复 slot、unverified 重叠、短返回、证据与 slot 不匹配。修改 ledger 时同步更新 seq、size、sha、requests、成功区间摘要、coverage probe_id 和 CURRENT 引用，使测试真正到达继承验证。增加跨案边界成功 recheck 的正例。
>
> (d) 修复夹具包括符合绑定要求的 CURRENT、bundle 和 resolution；正例使用可发布的混合 confirmed/refuted census。负例包括无指针、错误 pointer 路径/size/hash/mint/gid、错误 map_sha、错误 schema、exploration、重复 census、错误 coverage_state、无效 producer、状态或计数矛盾。修改 counts 的语义负例同步更新二进制及其引用，避免仅命中物理哈希错误。
>
> (e) 被再次导出的源案必须有 getBlocks 证据；不得沿用现有 roundtrip 的 `--no-getblocks`。验证资产 candidate_slots 为 raw_candidates，refuted 仍包含 R1/R2；增加原始 TTL 过期及当前 census 推翻旧继承的负例。
>
> (f) 保留全部旧用例，新增无实际继承时不写新键、旧 producer 产物继续通过；覆盖 base/repaired 两条组合判定、β 命中继承 slot、resume 丢失继承后的保守分类。
>
> 新增测试函数必须加入本文件 main() 的显式 tests 列表。

`test_sqd_coverage_probe.py:743-760` 使用显式测试列表；只新增函数并不会执行。

**11．必改：AST 守卫影响与白名单必须协调**

定位：§0.3–0.4、§0.7。

没有发现针对 classify 参数列表或状态字符串集合的直接 AST 守卫；新增默认 keyword 参数本身不会报警。但按工单在 probe 中比较 repair bundle/resolution schema，会新增 schema 消费者。

纯内存调用现有扫描器已得到：

```text
AST_NEW_CONSUMERS:
sqd-solana-coverage-resolution/v1
sqd-solana-repair-bundle/v1
```

manifest 当前给 probe 只登记 shared-map schema。可替换原文：

> 优先把修复导出来源的 schema/绑定校验 helper 放在 solana_exact_validate.py，由 probe 调用；该 validator 已登记所需修复 schema，避免新增 probe 的 schema 消费面。若实现选择在 probe 中直接校验，则必须将 invariant_manifest.json 加入白名单并准确补登记；不得通过动态拼接 schema 字符串逃避扫描器。
>
> 保留 invariant_scan/test_batch4_invariant_guards 回归，新增 test_f03_sharedmap_reuse.py 定向回归；新状态 β 兼容必须有明确用例，不能以旧测试全部通过代替。

此方案也更有利于减少 probe 的改动量。除第 6 项所述 repair 文件外，replay_edges、sqd_repair_core 没有发现必须修改的理由；新增相关回归若放在已有 repair/reconcile 测试文件中，则相应文件也应加入白名单。

**12．必改：docs_lint 执行要求违反禁读纪律；清理命令也需删除**

定位：§0.6–0.7，第 21–22 行。

§14.1 增补字段本身不会触发 G3 文档守卫；`test_g3_docs_guards.py` 只读取 analyze-workflow 和 research-workflows。docs_lint 主要核路径、格式和契约 needle，保留现有针脚即可。

但原始 docs_lint：

- `:268` 枚举全部 references Markdown，包含 attic；
- `:129-133` 递归读取仓库 Markdown，未排除禁读目录。

可替换原文：

> 本单禁读纪律适用于子进程及测试脚本。原版 docs_lint 会读取禁区，本施工会话不运行原版全量检查，由有相应访问授权的调度方完成，并将结果附入验收；不得把未运行写成 PASS。施工侧只对本单允许访问的修改文档检查格式、链接及受影响契约针脚。
>
> 临时文件使用系统 tempfile；无法创建时停止对应测试并报告环境限制，不改用禁读 `.staging_*`。删除 `rm -rf` 清理指令；文件清理遵守一次一个明确路径的规则。

这是工单内部执行要求冲突，不是要求本次只读复核扩大权限。

**13．建议：行数上限与文档字节上限改为审查指标**

定位：§1.7、第 32 行；§2.5、第 67 行。

在补齐成员见证、发布绑定、链式时效、β 兼容后，≤140/≤120 的增删合计没有实现依据。不能断言绝对做不到，但不能作为已经验证可行的硬门槛。文档还需解释新增来源证明和残余风险，1200 B 同样过紧。

可替换原文：

> 优先使用现有 helper，并将继承证明与修复来源绑定集中在独立 validator；保持 probe 为编排和导出层。生产增删行数及文档字节数列入完成报告，不以原上限迫使压缩可读性或省略校验。超过原目标须逐项说明新增职责和复用情况。
>
> 不采用“保持旧 states、仅删除候选”的简化方式，因为它与当前分类重算契约不等价。summary 可选键方案保留；修复侧只增加 β 所需的最小状态适配。

| 条目 | 等级 | 依据文件:行 |
|---|---|---|
| 1．事实、actual/unverified、锚、外部陈述修正 | 必改；外部来源存疑 | `sqd_coverage_probe.py:625,641,774,858`；`sqd_gap_repair.py:607,1337`；`spl_edge_core.py:240` |
| 2．零 nonce 重查的残余风险 | 必改 | `sqd_coverage_probe.py:128,732`；`sqd_gap_repair.py:1044,1073,1333` |
| 3．成员证明、自报绕过、跨边界 recheck | 必改 | `sqd_coverage_probe.py:418,774`；`solana_exact_validate.py:413` |
| 4．raw/effective 候选分离 | 必改 | `sqd_coverage_probe.py:858`；`solana_exact_validate.py:676,877` |
| 5．发布指针、修复来源与 census 绑定 | 必改 | `solana_exact_validate.py:1039,1257,1500,1591`；`sqd_gap_repair.py:1337,1483` |
| 6．β 新状态兼容与白名单 | 必改 | `sqd_gap_repair.py:576,607,1026,1369`；`solana_exact_validate.py:1202,1574` |
| 7．链式证据不得刷新原始有效期 | 必改 | `sqd_coverage_probe.py:697,849`；工单 `workorder_W1.md:40,47` |
| 8．probe_id、states 与空字段兼容性 | 必改 | `solana_exact_validate.py:84,241,684`；`sqd_coverage_probe.py:1321,1337` |
| 9．CLI 矛盾及变量来源 | 必改 | `sqd_coverage_probe.py:815,1419`；工单 `workorder_W1.md:32,48,49` |
| 10．夹具前提、拒绝路径与测试注册 | 必改 | `test_sqd_coverage_probe.py:538,653,725,743`；`sqd_coverage_probe.py:45,93,825` |
| 11．AST 消费者登记与回归面 | 必改 | `invariant_scan.py:1165,1296`；`invariant_manifest.json:609,627`；`test_f03_sharedmap_reuse.py:170` |
| 12．docs_lint 禁读冲突与清理指令 | 必改 | `docs_lint.py:129,266`；`test_g3_docs_guards.py:78`；工单 `workorder_W1.md:21,22` |
| 13．生产行数与文档字节上限 | 建议 | 工单 `workorder_W1.md:32,67`；上述必改项新增职责 |
