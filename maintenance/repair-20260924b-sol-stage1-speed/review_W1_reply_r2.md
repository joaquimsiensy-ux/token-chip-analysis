# 工单W1复核r2：退回

v2 尚不能直接派工。确定阻断集中在四处：**修复来源字段写错、资产见证的校验边界不完整、`--no-repair` 未闭合冲突处理、链式 evidence 转换规则互相矛盾**。β 最小改法、白名单和 10,000 块头夹具可行，无须推翻整体方案。

本次 HEAD＝`60c88b88a024bf463e819d846b1ba3a9e06c7ecd`，包含 `cc6298b`；指定生产路径相对该提交无差异，工作树前后干净。全程离线，未读取禁区、`~/.codex/` 或 memories；未新建、修改文件或 commit。执行了整行 `grep -n -F -x` 和纯内存验证，未执行会落盘的测试套件。

支持方案的最强理由是：复用既有 census 结论能省去重复的整块下载，JSON 副本及索引数组也能以较小成本保存来源关系。反对当前定稿的最强理由是：继承会直接移除候选；若实际产物字段、来源证据和冲突处置没有绑定完整，就可能拒绝合法发布件，或继续传播已被推翻的驳回。v2 已明确接受零 nonce 重查的残余风险，本轮不再要求扩大查询范围。

以下工单行号均指 [workorder_W1.md](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260924b-sol-stage1-speed/workorder_W1.md)。

**事实段①—⑨亲核结果**

对所引事实及范围执行了 106 项整行匹配检查；另核了修改锚和本轮发现涉及的字段锚。

| 事实 | 结果 |
|---|---|
| ① | 行号与行为对应。`actual` 写入实际在 probe:629、639；v2 写的范围各少包含最后一行，属于定位精度问题。 |
| ② | 正确。coverage 不落盘 states；`compute_probe_id:84` 位于 `solana_exact_validate.py`，宜写明文件。 |
| ③ | 正确。summary 为 11 键，三个结果全等比较；refuted 当前只检查形态。 |
| ④ | 正确。`:858` 导出有效候选，`:859` 恒为空 refuted。 |
| ⑤ | 正确。α/β 准入、硬编码 `state_in_map`、真实 `coverage_state`、修复指针检查范围及 refuted-only 行为均对应。 |
| ⑥ | 正确。生产直接调用为三处；另两处消费重算 states。 |
| ⑦ | 正确。资产时间和 153,667 个候选对应，refuted 为空。 |
| ⑧ | 正确。probe 仅登记 shared-map 消费；validator 已登记所需修复协议。 |
| ⑨ | 正确。显式 tests 列表存在；纯内存复现得到 64 块头时两个 ERA_UNCERTAIN，10,000 块头时两个候选。 |

工单明确给出的函数/语义行修改锚均能唯一命中。范围内的重复行不能逐行作为唯一锚，详见建议项 7。

**1．必改：§2.2 把 bundle 与 resolution 的 coverage 字段混用了，且漏掉部分 r1 绑定**

定位：工单 **54–58 行**；锚「校验器新增 helper」。

实际产物：

- bundle：`coverage.probe_id`、`coverage.map{path,size,sha256}`、`coverage.slot_counts`。
- resolution：`coverage.probe_id`、`coverage.map_sha256`、`plan_candidates.coverage/beta`；**没有 producer 字段**。
- producer 来自 `bundle.producer`。
- `validate_repair_pointer` 的 `expected_mint` 是 keyword-only，工单调用形式也应修正。

源码依据：[修复产物构造](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_gap_repair.py:1483)、[bundle.coverage](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_gap_repair.py:1587)、[指针函数签名](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/solana_exact_validate.py:1039)。

可替换 §2.2 helper 步骤 1–4 中对应原文：

> 调用 `validate_repair_pointer(pointer, expected_mint=mint, expected_gid=gid, expected_bundle_sha256=sha256_file(bundle_path))`，并检查返回结果；保留 CURRENT 引用路径、size、sha256 及目录约束。
>
> bundle 校验 schema、kind、mint、gid、formal/live；`bundle.coverage.probe_id == expected_probe_id`。`bundle.coverage.map` 是文件引用，须解析到本次已经验证的源 coverage_map，核对 path、size、sha256，其中 `bundle.coverage.map.sha256 == coverage_map_sha256`。不得读取不存在的 `bundle.coverage.map_sha256`。
>
> `bundle.coverage_resolution` 的 path、size、sha256 绑定所读 resolution。resolution 校验 schema、mint、合法且与 bundle 相同的 plan_digest；其 `coverage.probe_id == expected_probe_id` 且 `coverage.map_sha256 == coverage_map_sha256`。producer 校验明确作用于 `bundle.producer`，resolution 没有 producer 字段。
>
> `resolution.plan_candidates` 包含 `coverage`、`beta` 两个集合；两者均为严格整数、升序唯一数组，排除 bool；coverage 与当前有效候选完全相同。计划候选取两者并集，census 须覆盖该并集，不得把 β 行限制在 coverage 候选内。result 仅允许 `refuted`、`confirmed_missing_block`、`confirmed_nonce_defect`、`confirmed_other_defect`；按处置重算 effective_verdict，formal 发布来源须为 `DEFECTS_CONFIRMED`。
>
> own_refuted 仅取 result 为 refuted、coverage_state 为 DEFECT_CANDIDATE、与已验证源 coverage 重算状态相同、源 counts 为 2 的行；`sqd_nonce_count_at_repair == 0`，`missing_total == missing_nonce == missing_err_excluded == 0`，以上计数均为严格整数；`sqd_blockhash` 与 `ref_blockhash` 均为非空字符串且相等。`sqd_tx_count`、`ref_tx_count`、`ref_nonvote_count` 为非负严格整数。不得使用 state_in_map 判断真实分类。helper 须明确取得已验证源 coverage 的起始 slot、counts 与重算 states，避免重复执行整套 coverage 校验。

census 字段依据：[sqd_gap_repair.py:1336](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_gap_repair.py:1336)。这不是可留到施工时“按实际确认”的命名小节；现稿照写会读错字段。

**2．必改：JSON 副本不能提供不存在的 counts 值，且 evidence 必须与副本内容绑定**

定位：工单 **68、77–81 行**；锚「`source_ref` 实物存在」。

两项问题：

- 资产 JSON 的 `slot_counts` 只有文件引用、区间及编码，没有任意 slot 的 counts 值。第 78 行“读副本 JSON 即可”不成立。
- 第 78 行要求 origin 索引对应，却没有明确要求 coverage 中的 `refuted_evidence` 与副本 evidence 全等。只核索引和合法时间格式，无法防止修改 coverage 中的 `origin_generated_at` 后绕过原始时效。

另须区分：副本 evidence 的 `refuted_count` 针对**完整资产映射**，不能按本案继承子集重新校验，否则部分区间复用会误拒。

依据：[资产元数据实际字段](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/solana_exact_validate.py:785)、工单第 47、68、78、81 行。

推荐保留轻量 JSON 成员见证，直接替换第 78、81 行：

> `source_ref` 指向随本案发布的原资产 JSON 原始字节。检查文件 size、sha256，并要求 `source_ref.sha256 == shared_map.sha256 == inherited_refuted.asset_sha256`。解析副本，检查 refuted_slots/refuted_origin/refuted_evidence 的完整结构、索引范围及计数关系。索引必须是严格整数且满足 `0 <= index < len(refuted_evidence)`。
>
> coverage 中的 `inherited_refuted.refuted_evidence` 必须与副本的 refuted_evidence 全等；逐 slot 查出它在副本 refuted_slots 中的位置，要求 coverage 的 origin 等于该位置的 refuted_origin。副本 evidence 的 refuted_count 按副本完整映射核验，不按本案继承子集核验。
>
> JSON 副本证明来源资产声明的成员关系及证据对应，不包含源二进制逐 slot 实测值。源 counts==2 由探针加载原三件套时通过 validate_shared_map 和本次 recheck 检查；跨机离线校验依赖已声明的可信来源前提，并独立核本案 counts==2、复用区间及 recheck 记录。不得声称仅凭 JSON 副本重新验证了源二进制 counts。
>
> 每个 slot 的 origin_generated_at 必须取自经上述绑定的副本证据项，再按 coverage 记录的 verified_at 核验 30 天有效期；不得使用未经副本绑定的 coverage 自报时间。

若必须保留“离线重新核验源 counts”这一更强要求，则应明确把源 counts 二进制也随发布件携带并核引用；不能继续保留“若需要再读”的可选表述。

**3．必改：`--no-repair` 不能成为传播已确认缺陷的旁路**

定位：工单 **62–63 行**；锚「分支：给 `--repair-gid`」。

r1 第 9 条明确要求：`--no-repair` 只跳过自有驳回导出，不能重新输出与当前 census 冲突的继承驳回。v2 没有说明 CURRENT 存在且给 `--no-repair` 时，`confirmed_slots` 从何取得；步骤 4 却依赖它。

可替换第 62 行：

> 给 `--repair-gid`：按 §2.2 helper 核验指定的当前已发布代，取得 own_refuted 与 confirmed_slots；失败报错。未给任何选项且 CURRENT 存在：按现有提示报错。给 `--no-repair` 且 CURRENT 存在：从 CURRENT 取得 gid，仍用同一 helper 核验当前发布来源并取得 confirmed_slots，但强制 own_refuted 为空；校验失败报错，不得按“无冲突”继续导出。无 CURRENT 时，own_refuted 与 confirmed_slots 均为空。`--no-repair` 跳过自有驳回的输出，不跳过当前 confirmed 冲突检查。

在第 99 行测试后追加：

> 当前 census 对继承 R1 给出 confirmed 时，分别以 `--repair-gid` 和 `--no-repair` 导出，两者均必须剔除 R1；`--no-repair` 下 CURRENT 或来源绑定损坏必须报错。

依据：[r1 第 9 条](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260924b-sol-stage1-speed/review_W1_reply_r1.md:200)、[β 纳入计划候选](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_gap_repair.py:607)。

**4．必改：链式 evidence 不能既“原样带出”又改变字段契约**

定位：工单 **47、61、63 行**；锚「`inherited`＝源 coverage」。

第 47 行要求 inherited 的四个修复字段为 null、producer 为源 coverage producer；第 61 行却要求 evidence 原样，只明确修改 kind、asset_sha256 和保留 origin。将 repair-census 证据按后者转换，会留下非空修复字段和修复 producer，与自身 schema 矛盾。

过滤 slot 后还必须重新计数和重排索引；coverage 内保留完整来源 evidence 与导出资产重新分组是两个不同阶段。

可替换第 61 行，并合并第 63 行 evidence 生成要求：

> 链式导出使用已经通过 validate_coverage 的继承记录。按每个 slot 的来源索引取得原证据，再创建新的 inherited 证据项，不得把整项原样复制后仅修改 kind。新项的 kind 为 inherited；source_mint、probe_id、producer 分别取当前源 coverage 的 mint、probe_id、producer；repair_gid、plan_digest、resolution_sha256、bundle_sha256 全部设为 null；asset_sha256 取源 shared_map.sha256；origin_generated_at 保留对应来源项的原值，origin_asset_sha256 按 §1.7 的统一规则处理。
>
> 完成 raw_candidates 求交、confirmed 冲突剔除和原始时效过滤后，再按最终 slot 集生成 refuted_evidence/refuted_origin；删除没有剩余 slot 的证据项，重新编号索引，并按最终映射重算 refuted_count。coverage 中用于见证的来源 evidence 保持原样；新导出资产中的 evidence 按本段转换。

追加测试原文：

> 覆盖 repair-census→inherited→inherited 的两次链式转换，以及只继承原证据部分 slot 的场景；每次导出均检查修复字段 null、producer 归属、索引重排、refuted_count 和 origin_generated_at，且 validate_shared_map 通过。

依据为工单第 47、61、63、68 行；这是 v2 内部规则冲突。

**5．建议：把资产副本发布方式直接定形，避免施工时再猜协议**

定位：工单 **69 行**；锚「资产副本」。

现有协议可以实现，无须修改 `receipt_kernel.py`：

- `RawBytes` 可以保留原始字节。
- 副本可由 coverage_map 中的引用间接绑定到 CURRENT。
- `_same_generation`、`_clear_pending` 确实有硬编码文件清单。
- pointer inputs 也有严格键集检查，随意加键会拒绝发布。
- coverage_map 含自身 probe_id 所参与的哈希材料，因此其中的 source_ref 不应使用含最终 probe_id 的路径。

可替换第 69 行：

> 继承非空时，在计算 probe_id 前，以 `publish_exclusive(pending / "shared_map_source.json", RawBytes(source_bytes))` 写入已校验资产的原始字节；用 `_sha_ref` 生成 generation-relative 的 `source_ref.path="shared_map_source.json"`，并核其 sha256 与 shared_map.sha256 相同。校验器以 coverage_path.parent 为引用基准调用 `_check_file_ref`，并约束结果就是该代内的副本文件。
>
> 副本通过 coverage_map 的 source_ref→coverage_map 哈希→CURRENT 引用形成绑定；无需新增 pointer.inputs 键。将副本名称加入 `_same_generation` 和 `_clear_pending` 的清单，保留文件 fsync、施工目录 fsync、rename 后父目录 fsync、CURRENT 更新后指针父目录 fsync。无继承时允许副本不存在。补充携带副本的幂等重发与冲突检查测试。

依据：[RawBytes](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/receipt_kernel.py:181)、[发布清单](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_coverage_probe.py:1007)、[发布流程](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_coverage_probe.py:1029)、[pointer 键集](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/solana_exact_validate.py:536)。

**6．建议：明确 recheck 专用检查，补齐针对新设计的负例**

定位：工单 **80、93、97 行**。

`_success_ranges` 不能直接充当继承 recheck 校验器。纯内存亲核：

```text
完整成功但 counts_coverage=false → 不返回区间
请求 0..9、只返回 0..4 → 返回成功区间 0..4，无 reasons
```

这符合它计算 counts 覆盖的原用途，但不满足继承所需的完整重查条件。此外，现有 ledger 的 `response_sha256` 是响应摘要，没有保存逐 slot 响应内容，不能把摘要格式合法当成实测值验证。

可在第 80 行后追加：

> 继承使用专用 recheck 检查，不直接把 `_success_ranges` 返回区间当作继承证明。严格要求 provider=SQD、mode=recheck、ok=true、完整覆盖请求区间，并核查询摘要及结果绑定；独立处理 counts_coverage=false 的跨案记录。实现报告须说明结果绑定依据，不能仅检查 response_sha256 为 hex64 就宣称重算了响应值。不得为了继承而放宽现有 counts 覆盖规则。

在第 97 行后追加：

> 增加 fallback_reason 与非空继承并存、仅篡改 coverage 中 origin_generated_at 而副本不变、负数/bool/越界 origin 索引、部分继承导致 evidence 计数不同，以及 `--no-repair` 下 confirmed 冲突的负例。所有篡改均同步更新外层引用，使检查实际到达对应继承规则。

10,000 块头夹具本身可行：9,998 个 code=3＋两个 code=2 满足时代门槛；full 扫描共 **23 页**，末页 100 slots。recheck 按连续已知点区间生成，不能也机械切成同一套 full 分页。当前第 93 行已正确区分两者。

依据：[成功区间 helper](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/solana_exact_validate.py:413)、[响应 ledger](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_coverage_probe.py:327)、[recheck 调度](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_coverage_probe.py:573)。

**7．建议：修正事实段的范围精度与唯一锚表述**

定位：工单 **6–8 行**。

可替换对应短句：

> 行号范围用于事实定位；明确列出的修改锚须以完整语义行执行 `grep -n -F -x` 并恰命中一处，不要求范围内每一行唯一。
>
> 首轮与重试的 actual 写入范围分别为 probe:625–629、635–639；唯一锚可用对应 for 行。`compute_probe_id` 定义在 `scripts/lib/solana_exact_validate.py:84`。

亲核重复行包括 probe:629/639、774/780、607/777/782，以及 validator:246 的闭合括号；不影响事实成立，但不能作为唯一施工锚。

**8．建议：简化 `origin_asset_sha256` 的语义**

定位：工单 **35、47 行**。

“首次导出为 null，之后原样带出”会使新产生的所有链路都一直为 null；它因此不能实现“该证据首次进入的资产 sha”的描述。原始时效真正依靠的是 `origin_generated_at` 及其与来源副本的绑定。

若保留该字段，可直接替换其定义：

> `origin_asset_sha256` 为首次承载该证据的资产摘要。直接 census 首次导出时为 null，以避免资产自引用；第一次链式导出时，若来源项为 null，则填写直接来源资产 sha256；后续链式导出原样保留非空值。该字段用于溯源，不参与延长有效期；origin_generated_at 在上述转换中始终不变。

这需要同步修订第 61 行的“origin 原样”例外，并补一条两次链式导出的断言。

**β 兼容与白名单结论**

§1.4 的最小改法正确。对源码函数做纯内存 AST 修改，仅把新状态加入已有的零 nonce 状态分支，结果如下：

| 输入 | 修改后的预期行为 |
|---|---|
| 非 β、INHERITED_REFUTED | 仍由 α 准入检查拒绝 |
| β、有块头、nonce=0 | 接受 |
| β、无块头或 nonce>0 | 拒绝 |
| 深验对应状态 | 使用相同判据 |

白名单已覆盖必要的三个生产文件。未发现必须修改 `sqd_repair_core.py`、`replay_edges.py` 或 manifest 的理由；相关组合路径测试可以放入已获准的测试文件。此结论是源码及纯内存验证，不是新实现测试套件已通过。

**r1 的 13 条吸收对照**

| r1 条目 | v2 吸收结果 |
|---|---|
| 1．事实及锚 | 基本正确；范围精度见建议 7。 |
| 2．残余风险 | 正确吸收，§1.2 已明确。 |
| 3．成员证明与跨边界重查 | 部分吸收；副本方案可行，证据全等绑定和 counts 边界须按必改 2 修订。 |
| 4．raw/effective 候选分离 | 正确吸收，§2.2 步骤 1 已改为 raw。 |
| 5．修复来源绑定 | 未完整吸收；bundle 字段错误，resolution map_sha 和 beta 合法性遗漏，见必改 1。 |
| 6．β 兼容 | 正确吸收，最小改法及白名单成立。 |
| 7．原始时效 | 原则正确；证据绑定及链式转换仍须修订，见必改 2、4。 |
| 8．兼容性 | 正确吸收；区分分类兼容、旧产物兼容、同版本确定性。 |
| 9．CLI | 互斥参数及变量来源已吸收；`--no-repair` 冲突处置未闭合，见必改 3。 |
| 10．测试 | 大部分正确；夹具可行，仍需补上述针对性负例。 |
| 11．AST 与白名单 | 正确吸收；校验器 helper 方案符合现有消费者登记。 |
| 12．禁读与清理 | 正确吸收；全量 lint 转调度方验收，禁区夹具用例明确排除。 |
| 13．行数/字节限制 | 正确吸收为审查指标。 |

| 条目 | 等级 | 依据文件:行 |
|---|---|---|
| 1．修复来源实际字段与绑定 | 必改 | `workorder_W1.md:55–58`；`sqd_gap_repair.py:1336,1483,1587`；`solana_exact_validate.py:1039,1500` |
| 2．副本证据绑定、源 counts 边界 | 必改 | `workorder_W1.md:47,68,78,81`；`solana_exact_validate.py:785` |
| 3．`--no-repair` confirmed 冲突 | 必改 | `workorder_W1.md:62–63`；`review_W1_reply_r1.md:200`；`sqd_gap_repair.py:607` |
| 4．链式 evidence 转换 | 必改 | `workorder_W1.md:47,61,63,68` |
| 5．副本发布协议定形 | 建议 | `sqd_coverage_probe.py:1007,1019,1029,1343`；`solana_exact_validate.py:376,536`；`receipt_kernel.py:181,574` |
| 6．recheck 专用检查及测试补齐 | 建议 | `solana_exact_validate.py:413`；`sqd_coverage_probe.py:327,573`；`workorder_W1.md:93–100` |
| 7．事实范围及唯一锚精度 | 建议 | `sqd_coverage_probe.py:625,629,635,639`；`solana_exact_validate.py:84` |
| 8．origin_asset_sha256 的首次填充 | 建议 | `workorder_W1.md:35,47,61` |
