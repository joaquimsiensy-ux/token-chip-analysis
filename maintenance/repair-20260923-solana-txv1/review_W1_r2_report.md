# 复核 W1 r2: 退回

v2 已解决 r1 的主要结构问题，但尚未逐条完整吸收。退回原因集中在：认领台账提交仍有断写恢复缺口；“来源真实性”措辞仍超出检查能力；producer 换代触发器只覆盖版本值、不覆盖共享模板变化；§4 存在矛盾断言并遗漏关键向量。新增锚点本身均准确；§2.5 所需摘要物料完整可取，不需要扩展 bundle 格式。

本次复核保持只读：分支 `fix/solana-txv1`，HEAD `21eb0de`；所核生产、测试及规范文件相对工单基线 `813ca6d` 无差异；起止 `git status --short` 均为空。未改文件、未 commit，未读取 `~/.codex`、`~/Documents`、`~/Desktop`。上一轮使用 `rg/nl`、AST 和 `python3 -B` 隔离导入检查；未运行会创建夹具的测试、未跑 `run_all.py`。本条直接输出完整报告，没有再次执行命令。

目标是让版本升级后的修复任务复用已有成功证据，避免重拉。支持 v2 的最强理由是：同模板历史成功请求的原始身份可以保留，现有文件又足够独立重算计划摘要。反对直接施工的最强理由是：工单仍把“结构自洽”“来源真实”“中断可恢复”混在部分承诺里。决定结论的变量是输入可信、证据是否仍会原地修改，以及提交是否原子完成；无需另建来源签名或通用迁移框架。

**一、r1 修订清单 1–12 的吸收情况**

| r1 项 | v2 对应位置 | 结论及具体修订 |
|---|---|---|
| 1. 修正锚点、基线数量、外部背景 | §1.1、§1.3、§1.4、§4；第 5 行 | **已落实。**唯一仓库内依赖、E27(a) 结束于 768、守卫汇总 1330、施工前 13 文件 17 处均准确。背景明确为调度方提供。 |
| 2. 冻结物料一致与可信输入边界 | §2.1，第 63 行 | **部分落实。**“冻结摘要物料一致”“不提供对抗性来源证明”正确，但同句“来源真实性由案卷目录归属与既有深验保证”仍错误。改为“来源可信是输入前提；目录归属和深验只验证本案归属及结构、内容一致性”。 |
| 3. 同 parent、拒绝符号链接、自认领、多代来源 | §2.3 步骤 1–2 | **已落实。**`old.resolve().parent` 与 `parent.resolve()` 比较，另拒绝 old 自身为符号链接、old==pending、旧 header 含 adopted，符合收窄范围。 |
| 4. 旧台账纯解析、不改残尾 | §2.3 步骤 2 | **实现要求已落实。**抽纯解析函数、仅普通 resume 可重写是可行的；§4 尚缺“认领旧台账带残尾仍原字节不变”的专属向量。 |
| 5. 目标不存在、完整预验、提交和恢复边界 | §2.2、§2.3 步骤 5 | **部分落实。**目标 ledger 不存在正确；硬链接可保留。但“全量预验”须明确包含所有既有目标证据冲突。指定的 `_publish_bytes_exclusive` 直接写最终文件，断写后 ledger 已存在，认领重跑会被自己拒绝。详见第四部分。 |
| 6. verifier 上下文、严格 adopted、恢复分支及兼容 | §2.3 步骤 4、§2.4、§2.2 | **基本落实。**plan 可选、行上下文、两参数兼容及已发布代通过 deep 复验都成立。须明确 `_verify_adopted_record` 的 rows 是“不含 header 的数据行”，外壳仍返回 `(completed, data_rows)`；plan=None 仅允许无 adopted 台账。 |
| 7. 深验重建摘要、sha/digest 配对、指纹等式 | §2.5 | **核心要求已落实，全部物料可取得。**应删掉“bundle 内等价候选集”的未落实分支，固定使用 resolution 两个候选数组的并集；选定 validator 私有摘要函数方案，见第三部分。 |
| 8. 历史成功证据，不承诺响应字节等价 | §2.3 步骤 4 | **已落实。**保留旧 params_digest/result_sha256，没有再声称不同请求响应字节必然相同。以后提高 MAX 仍应审查新的版本语义，当前 range 在 MAX=1 时就是显式 0/1。 |
| 9. session 包导入与共享依赖换代 | §1.1、§1.2 | **部分落实。**session 回退正确；REPAIR_TX_VERSION 可强制版本值变化时修改 producer，但共享模板的其他字段变化不会触发。补“任何影响修复请求语义的共享模板修改也必须同步修改 repair producer 并登记”；无需新建依赖哈希体系。 |
| 10. 真实前代、直接取 plan、隔离负测与补齐向量 | §4 | **部分落实。**真实 ACTIVE sha、`_plan`、同步更新 ledger 文件引用均正确；零落盘断言有矛盾，部分负向构造不精确，并遗漏残尾、最长前缀、同步篡改边界及 v1 输入验证。见第六部分。 |
| 11. 文档最小修改、条件必填、极小守卫样本 | §1.4、§5 | **基本落实。**adopted 可选、五子字段条件必填正确；§5 第 104 行仍重复“来源真实性由目录归属与深验保证”，须与第 2 项一起修掉。新增字段行属于原表扩展，没有必要再新增文档章节。 |
| 12. 9.1.0、独立登记、定向回归与隔离导入 | §0.7、§0.8、§3、§5 | **已落实 r1 建议的最低回归集合。**vertical slice 的 loopback 阻断单独记账、其余交调度方全套检查合理；不必把 r1 列举的所有间接回归全部塞回 0.7。 |

**二、新增锚点与断言亲核**

以下均由 `rg` 定位、`nl -ba` 读取上下文确认。

| 锚点 | 源码实际内容与判定 |
|---|---|
| `scripts/solana/sqd_gap_repair.py:584` | `def _plan(case_root, mint, blocks_cache=None, reference_fingerprint=None, beta_slots=())`；:623–624 返回三元组。准确。 |
| `scripts/solana/sqd_gap_repair.py:101` / `:1607` | 前者定义 `reference_endpoint_identity`，:106 返回 sha256；后者 CLI 取同函数结果。准确。但 fixture 的实际字符串是 :1601 的 `fixture://helius`，测试不能把工单中的省略号当字面值。 |
| `scripts/solana/sqd_gap_repair.py:962` | `_live_payloads` 的关键字参数已有 pending、plan、coverage_states；:972 调 `load_resume_slots` 时尚未传 plan。准确，接线只需在调用处传入。 |
| `scripts/solana/sqd_gap_repair.py:682–706` / `:703` | 读取、裁去残缺尾行、解析后重新 canonical 编码；:703 `handle.write(clean)`。准确，不能用于读取旧来源。 |
| `scripts/solana/sqd_gap_repair.py:204–210` | 已有同字节文件返回，不同内容抛 `FileExistsError`。准确；但 :211–216 是直接创建最终文件再写入，并非原子提交。 |
| `scripts/tests/test_batch8_repair_scale.py:203–204` | `load_resume_slots(pending, repair._ledger_header(plan))` 两参数调用。准确；:175–177 的 plan 不完整且 digest 为 64 位占位值，不能把 adopted 的完整检查强加给它。 |
| `scripts/lib/solana_exact_validate.py:1328–1331` | 仅验证 params_digest、endpoint_fingerprint、result_sha256 是 64hex；没有检查指纹相等。准确；:1338–1341 保存到 ledger_by_slot 时还丢弃了指纹，宜在当前行循环就地比较。 |
| `scripts/solana/sqd_gap_repair.py:1341–1347` | 写出 resolution.coverage 和 resolution.plan_candidates。准确，plan_candidates 是含 coverage、beta 的对象，不是候选数组。 |
| `scripts/solana/sqd_gap_repair.py:1430–1452` | bundle 写出 base、coverage、mode、producer、reference；coverage 的 map_sha256 位于 `coverage.map.sha256`。准确。 |

另复核：AST 仍为 **13 个生产文件、17 个数字字面量**；当前 repair 文件 SHA-256 正是：

```text
25f04ff10bc494be977e4c5b3193c3a928c0764fa529d8d5a47563fe2a825e66
```

`producer_history.py:213–216` 对 repair-bundle/v1 登记为 ACTIVE，:246 起的查询保留 REVOKED 优先规则。

**三、§2.5 摘要物料是否完整、导入是否可行**

结论：**全部可取。**r1 关于“现有文件足够”的判断成立，v2 无需添加任何 bundle 顶层键。必须区分 plan 的扁平 `map_sha256` 与 bundle 中嵌套的 `map.sha256`。

下表左列对应 `scripts/solana/sqd_repair_core.py:65–80` 的真实摘要物料；产物键的证据行是写出这些键的源码行。

| 摘要项 | 产物文件、键及源码依据 |
|---|---|
| `base.edge_sha256` | `bundle.json` → `base.edge_sha256`；`sqd_gap_repair.py:1436`。 |
| `base.meta_sha256` | `bundle.json` → `base.meta_sha256`；`sqd_gap_repair.py:1437`。 |
| `coverage.probe_id` | `bundle.json` → `coverage.probe_id`；`sqd_gap_repair.py:1441`。`resolution.coverage.probe_id` 也保存于 :1344。 |
| `coverage.map_sha256` | `bundle.json` → `coverage.map.sha256`；`sqd_gap_repair.py:1442–1443` 经 `_file_ref` 写出，`_file_ref:190–193` 明确生成 sha256。`resolution.coverage.map_sha256` 也保存于 :1345。不能读取不存在的 `bundle.coverage.map_sha256`。 |
| `candidate_slots` | `coverage_resolution.json` → `plan_candidates.coverage` 与 `plan_candidates.beta` 的去重排序并集；写出点 `sqd_gap_repair.py:1346`，原始构造 :595–617。validator:1434–1457 已检查两组并计算 all_candidates。 |
| `mode` | `bundle.json` → `mode`；`sqd_gap_repair.py:1433`。 |
| `reference.kind` | `bundle.json` → `reference.kind`；`sqd_gap_repair.py:1451` 整体保存 plan.reference，其 kind 在 :601 设定。 |
| `reference.endpoint_fingerprint` | `bundle.json` → `reference.endpoint_fingerprint`；`sqd_gap_repair.py:1451`，原始构造 :602–604。 |
| `producer.sha256` | `bundle.json` → `producer.sha256`；`sqd_gap_repair.py:1433`，原始生成 :607–608。前代重算时仅替换此项。 |

没有缺项；不需要替代数据源。`candidate_slots` 必须用两组并集，不能只用 coverage.candidate_slots、census 中的 slot、confirmed slot，或直接把 plan_candidates 对象交给 `compute_plan_digest`。

建议把结构检查保留在 header 读取附近，把摘要重算放到 validator:1457 已取得并校验 all_candidates 后；仅当 header 含 adopted 时执行，保护旧台账兼容。使用已验证的文件引用读取 resolution；缺键或形状错误应转成 adopted invalid 理由，不应泄漏 `KeyError/TypeError`。

只读内存验证提取了现有 `compute_plan_digest`，用含 coverage/beta 重叠候选的合成 plan 与上述 bundle/resolution 映射比较，摘要相等。该验证证明映射，没有冒充真实认领 E2E。

导入方面，隔离进程实际结果：

- `import scripts.lib.solana_exact_validate`：成功。
- `import scripts.lib.solana_attested_session`：失败，`No module named 'endpoint_identity'`，印证 §1.1 的回退必要。
- 仅加入 `scripts/lib` 后 `import sqd_repair_core`：失败，找不到模块。
- `import scripts.solana.sqd_repair_core`：失败，`No module named 'spl_edge_core'`。
- 同时加入 `scripts/lib`、`scripts/solana` 后顶层导入 core：成功。

原因是 core:11–12 仍绝对导入 `spl_edge_core`；修一个相对导入并不能自然解决整个层级。更重要的是 validator:9–10 和 :1221 明确要求独立于 producer/core。

最小方案：直接选用 v2 已允许的私有摘要重建函数，复用 validator:50–75 的 `canonical_json/sha256_bytes`，按 core:65–82 的字段、候选排序、16hex 截断独立实现并标出处。不新增 `sys.path` 操作、不改 core、不建立新共享模块。用同一完整物料向量比较两边摘要，并验证只换 producer 后前代摘要对应。

**四、§2.3 提交、预验与硬链接**

**1. “全量预验”仍需写实。**

v2 第 77 行将“dst 已存在则 JSON 相等否则 ValueError”放在逐份迁入叙述中。若实现也放在迁入循环，后面的冲突会留下前面已经迁入的文件。应先遍历全部待迁文件，检查既有 dst 的相等性及必要路径条件，再开始 link/copy。

“零落盘”应限定为验证拒绝时不新增或修改产物文件，允许此前已创建空 pending/evidence 目录；I/O 中断则允许保留未提交证据。这与 :1273–1276 的入口实际行为一致。

**2. 现有台账发布函数不能兑现完整中断恢复。**

`_publish_bytes_exclusive` 在 :211–216 用 `O_EXCL` 打开最终 ledger 后才写 payload。若写入中断，可能留下零字节、仅 header 或部分数据行的 ledger。下次 `--adopt-pending` 因“目标 ledger 必须不存在”拒绝；普通 `--resume` 也不能保证恢复完整认领记录。因此“ledger 不存在即可重跑”只覆盖证据迁入阶段，不覆盖最终 ledger 写入阶段。

最小修法已在仓库内：`receipt_kernel.RawBytes` 定义于 :41，:181–184 支持原始 bytes；`publish_exclusive:574–587` 先暂存再用硬链接原子发布，`_stage:327–336` 先写完并 fsync。认领路径改用：

```python
publish_exclusive(
    ledger_path,
    RawBytes(_jsonl_bytes([new_header] + adopted_rows)),
)
_fsync_dir(pending)
```

仅新增 `RawBytes` 导入即可，不必全局改 `_publish_bytes_exclusive`。提交前中断用相同 `--adopt-pending` 重试；ledger 已完整提交后按 §2.2 拒绝重复认领，使用普通 `--resume`。补测试分别覆盖这两个阶段。

跨卷分支也须写清：不同 st_dev 时直接复制，或尝试 link 后仅对 `errno.EXDEV` 回退；不能先把不同 st_dev 当作拒绝条件、又承诺回退复制。父目录 st_dev 只是预判，实际 link 错误才是最终依据；其他 `OSError` 不应一概降级复制。

**3. 硬链接相对复制：有额外联动风险，但没有必要因此否决当前方案。**

真实深验链为 `solana_exact_validate.py:1357–1361` → `_repair_ref:892–904`，确实重算每份 evidence 的大小和哈希。manifest 冻结后，旧路径的原地改写若改变共享 inode，新代证据也会改变，下一次深验会拒绝。它不会仅因硬链接就绕过该哈希检查。

但哈希能发现损坏，不能隔离损坏。复制后只修改旧文件不会破坏新代；硬链接后会同时破坏新代，反向原地写新代也会改变旧证据。这是额外的可用性与审计留档风险；删除旧目录项或用新文件原子替换旧路径则不会改新代 inode。

还应区分时间点：首次 manifest 生成前发生的变动，可能被新生成的哈希直接收录，不能声称“后续重算哈希必然证明迁入时未变”。这并不要求引入新的对抗性来源机制。

**对 r1 的表述作明确校准：不能把“硬链接”本身视为必须改成复制的阻断项。**在可信来源、旧证据不再原地写、发布后深验的既定流程里，可以保留硬链接；只需准确承认上述耦合，禁止本认领流程及后续复用流程原地改写已链接证据。42 GiB/39 GB 是调度方背景，本次未独立核实，也不据此要求另做大规模复制。

**五、§1.2 producer 换代触发器与最小化**

`REPAIR_TX_VERSION = 1` 加显式 if/raise 可以达到“共享版本上限变化必须同时改本 producer 文件”的目的。repair:607–608 只哈希本脚本，漏改本地版本就导入失败；同步修改后脚本哈希必变。这里不是 Python `assert`，`python -O` 不会关闭检查，应保留 if/raise。

但它不检查 producer_history 已登记新 sha，也不覆盖共享模板中的 commitment、encoding 等非版本字段变化；登记由既有 registry 测试把关，模板变化需在工单和代码注释中明确同步改 producer。

更省写法可直接在 producer 中写：

```python
if SOLANA_MAX_SUPPORTED_TX_VERSION != 1:
    raise RuntimeError("repair producer tx-version pin must be updated")
```

它与单独 REPAIR_TX_VERSION 常量加比较等效，省一个模块级名字。本地保留一个字面值不是无意义重复：它负责把共享配置变化反映到 producer 文件身份。不要改成：

```python
REPAIR_TX_VERSION = SOLANA_MAX_SUPPORTED_TX_VERSION
```

那样检查将失效。

其余可以省：不加通用迁移框架；不改 bundle 顶层、core、gid 物料；不增加 core 导入分支；不扩大 0.7 到全部间接回归；不因硬链接增加全量复制。

不能再省：提交原子性、全部目标冲突预验、严格且有数据行上下文的 adopted 检查、来源可信边界，以及真正验证版本 1 行为的测试。r1 对共享模板换代和 v1/transactionConfig 测试的要求，v2 仍省过头。

**六、§4 夹具可行性、矛盾及遗漏**

总体可实现，不需要修改 test_batch8 或另造夹具框架。`build_batch3b_case:165`、`repair_slot_responses:229`、`write_repair_fixture:391` 和 E27(a):712–768 已提供两候选 slot、配额中断、无已完成 slot 的续跑响应集。

逐项结论：

- **正向可构造。**用独立 case，fp 必须取 `fixture://helius`；`_plan` 的 blocks_cache/beta 参数与 CLI 保持一致。施工后新 producer sha 与真实 OLD 不同，改目录/header 即可模拟前代。旧行版本 0、剩余 slot 版本 1 并不矛盾。
- **“每条零落盘：目标 ledger 不存在”与负向③“目标 ledger 已存在”直接矛盾。**统一断言“失败前后目标状态不变”；③既有 ledger 应继续存在且字节不变，其他从空目标开始的用例才断言 ledger 不存在、无新增证据。
- **负向①把 header digest 改成任意 16hex，只能证明不可复现 digest 被拒，不能精确证明“未登记 producer 被拒”。**改为选取确认不在 ACTIVE 集的 64hex sha，代入当前 plan 计算 digest，并同步更名旧 pending 与 header；否则可能提前因目录名不匹配失败。
- **负向④可以构造。**只改 ref.raw_response_sha256，使它与行 result_sha256 不一致，命中 `no adoptable prefix`。
- **负向⑥、⑦均可构造。**跨 parent 用同内容拷贝即可；旧 header 增 adopted 应在来源检查阶段拒绝。
- **负向⑧若只改 row.slot，将先因请求摘要/证据文件不对齐进入 no adoptable prefix，测不到候选集守卫。**必须同步改该行的 slot、对应 params_digest、两份证据文件名及各自 slot，保持其他身份检查对齐，再断言候选集拒绝。
- **深验三项负向均可构造。**更新 bundle.rpc_ledger.size/sha256 后可隔离原因；仅修改 ledger 不必重算 gid，因为 `compute_gid:90–92` 明确排除 rpc_ledger。直接调用深验时不必人为更新 CURRENT；若走指针消费路径则另须更新相应 bundle 引用。
- **真实 sha 配假 digest 的深验负测已补，旧行证据摘要不对齐已补；这不等于已经覆盖“行 result_sha256 与 ref.raw_response_sha256 同时改成相同伪值”。**

还须补或明确：

1. **旧台账残尾只读。**旧台账加残缺尾行后认领成功，认领前后旧 ledger/证据字节哈希不变。现有 E27(a) 测的是普通 resume 的截尾，不替代认领只读测试。
2. **最长可采纳前缀。**首行证据正确、第二行不对齐，只采纳第一行，rows=1，后续按剩余 fixture 处理；保留连续 seq/唯一 slot。若继续要求确定性候选顺序，应明确按 plan.candidate_slots 的前缀核对，而不是只有集合包含。
3. **完整预验与提交边界。**加“前面目标无冲突、后面目标冲突”的预验负测及提交前/后的中断恢复向量，证明第四部分的提交边界。
4. **同步篡改的信任边界。**同步改行 result_sha256 与 ref.raw_response_sha256 时，来源可信模型不能凭空证明二者是假。可作为明确边界向量；不能强写“任意同步篡改必拒”。若要求拒绝某种语义篡改，必须选取已有独立约束能检出的具体不一致。
5. **独立验证版本 1 行为。**独立断言真正送给 transport 的 body 中 `maxSupportedTransactionVersion == 1`，并加入含 `version: 1`、`message.transactionConfig` 的响应输入。`repair_slot_responses:258` 用生产 `_rpc_body` 同源生成响应索引，单凭夹具通过会形成同源自证；新 ledger 摘要也应对一个显式写定版本 1 的独立预期比较。当前这两个测试文件没有 transactionConfig 覆盖。
6. **避免旧版本成功证据与 v1 响应自相矛盾。**模拟为旧版本 0 成功返回的已采纳 slot 不应含 version: 1 交易。把 v1 输入放到认领后新拉取的第二个 slot，避免新增测试自己违反历史成功证据前提。

**v3 修订清单**

1. 同步修订 §2.1/§5：“来源可信是前提；目录与深验验证归属及一致性”，删掉能够保证来源真实性的表述。
2. 将 §2.3 的所有既有目标证据冲突检查放到首个 link/copy 之前；“零落盘”改成验证拒绝时产物状态不变，允许空目录和明确的 I/O 中断残留。
3. 认领 ledger 改用现有 `publish_exclusive + RawBytes` 原子提交并同步目录；写清提交前重跑认领、提交后普通 resume；明确仅 `EXDEV` 触发复制回退。
4. 固定 §2.5 的键映射：`coverage.map.sha256`、`resolution.plan_candidates` 两组并集；使用 validator 私有独立摘要函数，补与 core 的物料一致性向量。明确 verifier 接收不含 header 的数据行。
5. 保留硬链接，说明共享 inode 的联动边界及不原地改写约束；不再把硬链接本身作为必须复制的阻断项。
6. §1.2 补共享请求模板语义变化必须同步改 producer/登记；本地版本触发器可保留或简化为显式 `if MAX != 1`，不能改成可被 `-O` 删除的 assert。
7. 修正 §4 的目标已有 ledger 断言、未登记 sha 的构造、候选集外 slot 的完整对齐构造，并固定 `fixture://helius`。
8. 补认领残尾不变、最长可采纳前缀、目标冲突预验、提交中断、同步篡改信任边界、独立版本 1 请求及 v1/transactionConfig 输入向量；v1 响应放在新拉取 slot。
