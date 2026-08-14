# 批 D 批内对抗审查（盲审）

- **审查对象**：`b3ee352`（基线 `97b2c65`）——F-07 handoff/refresh 真事务两阶段提交、F-06 flip 裁决收据链（`flip-adjudications/v1`，trace／freeze 前置 3／A5 三处消费）、GPT-F-06 销户审计 fail-open 收口、台账八项（A-1／A-3／A-5／B-1／B-4／B-5／B-6／B-7）、契约三件同步（manifest＋snapshot 146 条＋CT-SEMANTIC-49~56）、版本收口 6.40.0、验收件（反例三脚本／端到端绿例／弱闸旁证）
- **审查方式**：只读仓库生产文件（本审查对生产树零改动）。变异实验全部在副本 `/private/tmp/batchD_probe/repo/` 上做，逐条 `git checkout` 还原后 `git status` 复核为空。工作树接手时干净，`git rev-parse HEAD = b3ee352`，无漂移
- **基线核对（独立复跑，不引用施工方自报）**：
  - `python3 scripts/tests/run_all.py` → **EXIT=0，"全部通过"**（`test_repair_batch_d.py` 确在 SUITE 显式清单内并实跑）
  - `python3 scripts/tests/invariant_scan.py` → **rc=0**（producers=54／consumers=63／transport=62／atomic=46／formal=58／exceptions=0）
  - `counterexamples/` 五脚本独立重放 → **全 rc=0**（含批 A/B 存量两个回归无损）
  - 三命令 staging／部署 SHA 独立实测 → **三条全 EQUAL 且与工单 §九记录逐字符相同**；`python3 -V` = 3.14.6，与工单一致
  - 施工方自报的红绿状态**属实**
- **结论**：**8 条 finding，最高 P1**。事务性那一半（F-07）是本批质量最高的部分，我把注入点从施工方的 1 个扩到 8 个（含 3 文件深度、prepare 期、双回滚失败）全部守住"全有或全无"；**收据链那一半的两处外沿没关严**——A5 披露核对仍被盲审当初点名的同一个攻击（无关文本）打穿，冻结后换收据全链无人报警

| 编号 | 严重度 | 一句话 |
|---|---|---|
| F-D1 | **P1** | A5 披露"实文核对"是整篇 Markdown 子串搜：一段完全不提翻转的附录（含相同地址串与占位数字）实测直接 `DISCLOSED`；收据里的 `report_locations` 被强制非空却**全库零消费者**；份额数字那半边**无测试锁**（中和后全绿） |
| F-D2 | P2 | `freeze --check-unseal` 的冻结绑定清单未随 F-06 扩展：冻结后**改写或删除** flip 裁决收据实测 rc=0 放行（对照组删 `labels_file` rc=2）——裁决主体／时间／理由／证据冻结后可任意改写 |
| F-D3 | P2 | 端到端绿例是**两个不同案的两段拼接**，接缝（figures 真实产物 → A4 finalize 消费）从未在同一案内传递过，不满足 plan :95「走完 state_from_facts→figures→A4 finalize→A5 seal」的原意——正是盲审当初否决「拿别段覆盖冒充」的同一手法 |
| F-D4 | P2 | 收据的"人工裁决"面**零机器强度**且**未进残余边界声明**：20 行脚本自算指纹＋自填披露，裁决人写 `x`、时间写 1970、证据挂 1 字节垃圾文件 → trace rc=0＋freeze recompute 零 fail |
| F-D5 | P2 | GPT-F-06 自报"深挖全 fetch_failed 由②的 mock 一并覆盖"**证伪**：②实际只产出两条 reason，该判据中和后批 D 全测＋invariant_scan 全绿（变异存活）；`CLEAN`（充分零漏→exit 0）这一格**全库无用例** |
| F-D6 | P3 | F-07 **prepare 期**失败会泄漏正在写的那个临时件（`staged.append` 在写完之后，清理循环遍历不到它）；prepare 期注入**无用例**，而 plan 与验收矩阵都点了这一格 |
| F-D7 | P3 | 收据路径三处口径不一致：trace 收任意路径、freeze 收案根内任意名、A5 **硬编码 `flip_adjudications.json`**——合法改名案在 A5 被误伤拒；且 A5 读的收据与 ledger 绑定的那份**未互绑 sha**，可用甲收据过 freeze、乙收据过 A5 |
| F-D8 | P3 | 三处表述强于实现：文档／CHANGELOG 的"封死 freeze 后删/换 ledger 旁路"实测只封死单边改动；`audit_closed_accounts` 早退路径**不落报告**故 `status` 无从辨；A-1 政策拒绝出口对"参数打错"也归档旧收据 |

---

## 一、施工方自报属实性核对（逐条）

| 自报项 | 核对结论 |
|---|---|
| `run_all.py` 全量 EXIT=0、`test_repair_batch_d` 入 SUITE | **属实**，独立复跑一致 |
| 三守卫（changelog_lint／docs_lint／invariant_scan）PASS | **属实**，invariant_scan 独立复跑 rc=0，计数与自报一致 |
| 契约 manifest 146 条与 snapshot **双向相等** | **属实且是结构性校验**（`assert_contract_ids_match` 用集合差集算 missing/extra，非只比数量；文件内自带删一条/加一条的内存反例） |
| CT-SEMANTIC-49~56 每条 needle 在权威文档实测在场 | **属实**，八条逐一 grep 命中（49/50/53/55/56 各 1 处，51/52 各 2 处，54 三处），语义与所在段落对得上。**但 CT-SEMANTIC-56 的 needle 是裸单词 `superseded`**，强度低于同批其他七条（schema 串／专名），文档改写时极易被无关句子顶住 |
| F-07 注入测试断言的是"**字节回滚原样**"不是只断言退出码 | **属实**。`after == originals` 逐文件比字节，且另断言无 tmp/bak/recover 残留；注入还带命中标志（第 4 次 `os.replace`＋stderr 含注入串） |
| 变异法 5/5"删掉即红" | **未逐条复验**（不重复施工方已做的），我改为独立扩面，**扩出 2 条存活变异**（见 F-D1／F-D5）——说明 5/5 这个数字本身没问题，但覆盖面不够宽 |
| counterexamples 三新脚本独立可重放 rc=0 | **属实**（连同存量两脚本共 5 个全 rc=0） |
| R10 弱闸旁证：三命令 staging/部署 SHA 全等、Python 3.14.6 | **属实**，我独立重跑 `shasum -a 256`，三条 SHA 与工单逐字符相同；解释器版本一致（21 依赖未逐个复验） |
| 工单末行"未 git commit（HEAD 仍 97b2c65）" | **与落盘不符**：`b3ee352` 已带批 D 全文 message 落在 main。技术结论不受影响，记录以免引用工单文字时误判节拍（批 C 同一现象已记过一次） |
| A-2／A-4 评估结论（不做，留 R10-12／R10-13） | **理据成立**：A-2 确实是政策决定（现行 `FORMAL_TOLERANCE_BPS_MAX` 只管无 waiver 路径，有 waiver 时 `approved_tolerance_bps` 无上限属实）；A-4 确属新功能面。r10_ledger 13 条与 CHANGELOG 的"6＋2＋3＋2"口径对得上 |

### 五处披露的逐处判定（任务点名项）

**三处夹具失真修复**——工单口径是"全量首跑抓获的三处"，不是全部夹具改动（实际动到夹具的测试文件有 6 个，§七清单列全了，口径需注明但不算漏报）。

| # | 处 | 断言零删改？ | 被拒面不减？ | 判定 |
|---|---|---|---|---|
| 1 | `test_batch3_solana_vertical_slice` 加 `align_ledgers_to_owner_snapshot`（对齐 `solana_scan_work/holders_owners.json`） | ✓ 断言一行未动，只在 run 之前加夹具对齐 | ✓ B-7 是**新增**拒绝面，原有拒绝面无一条被撤 | **属实**。原夹具三账写死 `0xabc@123`，在真实 Solana 切片里本来就是失真件 |
| 2 | `test_batch3_evm_vertical_slice` 同上（对齐 `balances_evm.json`），helper 内连带同步 `audit_input_manifest` 登记与 `reproduce_receipt.input_manifest.sha256` | ✓ | ✓ | **属实**。连带同步是必须的——重写 `balances_snapshot.json` 而不更新冻结输入清单会制造第二处假红，属于夹具自洽维护 |
| 3 | `test_repair_batch_b::test_fb6_docs_binding_strength_diff` 断言从"文档写明 Solana 暂无实物锚"改为"文档写明已对齐＋文件级三验" | ✓ 断言强度未降（两条 needle 都是必须在场） | ✓ | **属实，但性质是断言语义反转**：守的不变量（文档与实况一致）没变，实况被 B-1 改了所以断言跟着改，逻辑成立。已独立核实 `scan-schemas.md:352` 的新文案确实写了"已对齐"与"文件级三验"且描述准确 |

另需记录：`test_handoff_manifest::make_case` 与 `test_audit_release_gate::build_case` 也补了 `balance/supply` 收据的 `inputs.replay_stats`（A-5）。我独立核了 `verify_recon.py:66-68` 的真实 `build_envelope`，inputs 确实是 `config／balances／replay_stats／gmgn` 四件套——**"补成真实生产形态"属实，不是为过闸编造**。

**两处报错换岗**（实际是三处，第三处在工单 §③ 单独提了）：

| # | 处 | 被拒面 | 判定 |
|---|---|---|---|
| 1 | `test_repair_batch_a::test_n1_...` 从单 needle `"不在当前案根内"` 改为接受 `("不在当前案根内", "escapes case root")` 二选一 | **不减**（同一攻击仍被拒，只是被更靠前的 `validate_receipt(case_root=…)` 先拦） | **属实**。代价是断言精度下降：现在无法再区分是新闸还是旧闸拦的，将来旧闸被误删不会红。可接受，但值得在台账留一句 |
| 2 | `test_handoff_manifest` 两处 needle `"机器从明细重算"` → `"三策略主导终点翻转"` | **不减**；第二处是 NOT-in 断言，新 needle 覆盖面更宽反而**更严** | **属实**。代价同上：新 needle 同时命中 `recompute` 与 `verify_flip_receipt_against_ledger` 两条不同路径的文案，断言从"区分具体分支"退化为"区分翻转类拒绝" |
| 3 | `t_f06_receipt_unit_negatives` 名册改动用例接受"名册"或"entity_file"两条文案 | **不减**（ref 三验先拦，内容比对兜底） | **属实**，工单已如实记 |

---

## 二、逐条 finding

### F-D1（P1）A5 披露"实文核对"＝全文子串搜，盲审点名的原攻击仍然打得穿

**实测**（`/private/tmp/batchD_probe/attack_a5_disclosure.py`，真跑 trace 造真实翻转案）：

```
真实翻转锚点 (E1,current)/(E1,peak)：
  pro_rata top=[BOUNDARY,cex_confirmed,AAAA] 50.00%
  fifo     top=[BOUNDARY,dex_pool,BBBB]     100.00%
  lifo     top=[BOUNDARY,cex_confirmed,AAAA] 100.00%
攻击报告全文（一个字没提翻转/多策略/敏感性）：
  # 某代币筹码分析报告
  ## 附录 F：随机抽样校验串
  本次抽样校验串为 AAAA、BBBB、CCCC，用于比对采集完整性，与结论无关。
  ## 附录 G：占位数值
  下表为排版占位，非真实数据：50.00 / 100.00 / 12.34。
>>> 结果：DISCLOSED（收据里 report_locations 声称的 "§翻转披露" 在报告中根本不存在）
```

根因在 `a5_report_seal.py:88-91`：`if ident not in report_text or (share and share not in report_text)` ——两个纯子串判断、彼此独立、不要求同段同行同表，且 `report_locations` 从头到尾没有任何消费者（`grep report_locations scripts/` 只有 schema 校验处与文档）。真实报告里 `share` 是两位小数百分比（"50.00"）、`ident` 在 `terminal[2]` 为空时会退到 `terminal[1]`（交易所名一类），两者在任何一份真报告里几乎必然偶然在场——这道闸对真实案的强度接近零。

plan 的原话是"flip claim 结构化携带三策略 top 名称与份额数字**＋报告可核位置**，A5 对报告 Markdown 逐项核对这些值真实在场"，盲审给的立项理由是"只验 claim ID 在场挡不住无关文本"。修复后**同一句攻击词原样成立**，位置那一半根本没做。

**份额那半边还没有测试锁**：把 `or (share and share not in report_text)` 整段中和（只查 ident），`test_repair_batch_d` 与 `test_round4_a5_seal` 双双 rc=0。原因是原反例文本是"只字未提翻转"——既缺 ident 也缺 share，只靠 ident 就够拒。

**修法方向**（不替施工方定稿）：核对锚定到 `report_locations` 声明的章节切片内（按 Markdown 标题定位后只在该切片里找 ident＋share，且要求两者同切片），或者要求披露以固定标记块（如 `<!-- flip-disclosure: E1/current -->`）落地后逐块比对；同时补"无关文本含相同数字"的红例与"share 缺失但 ident 在场"的独立红例。

### F-D2（P2）冻结后换掉/删掉裁决收据，`--check-unseal` 全程不报警

**实测**（`attack_unseal_receipt.py`，真跑 `handoff_manifest.py freeze --check-unseal`）：

```
基线（收据原样）                        rc=0  允许揭盲
攻击A 冻结后改收据内容（裁决人→"冻结后偷偷换的人"、时间→1999、理由整句换） rc=0  未被察觉
攻击B 冻结后直接删掉收据                rc=0  未被察觉
对照C 冻结后删 labels_file（在既有清单里） rc=2  ✗ 绑定文件不存在
```

根因在 `handoff_manifest.py:1058-1090`：`checks` 五元组与 `bound_records` 收集的是 `source.files／algorithm.files／entity_file／labels_file／handoff_manifest／data_map`，**`algorithm_params` 整个没被遍历**——而 F-06 恰恰把收据引用放进了 `algorithm_params.flip_adjudications`。这段代码自己的注释写着"只验 ledger 自身哈希会漏掉『ledger 未动、raw/labels 已换』的揭盲绕过"，收据正是同一类。

后果：`approved_by`／`user_decided_at_utc`／`reason`／`evidence_refs` 这些"人工裁决存证"字段在冻结之后可以任意改写而全链无一处报错；删掉收据后揭盲照放（只有在恰好有真实翻转且跑到 A5 时才会被"案根缺 flip_adjudications.json"拦住）。这是同族调用面（视角④）没关到等深。

### F-D3（P2）端到端绿例是两案拼接，接缝无覆盖，不满足 plan 原意

plan 验证方案第 4 条原文：「新建/扩展**走完** `state_from_facts→figures→A4 finalize→A5 seal` 的 EVM＋Solana（含 burn）**各一条**端到端用例」，而且这条是盲审**翻案**加的，翻案理由写得很直白：「batch3 纵切片只到 audit release，不含 state→fig1→A4→A5——**不能冒充该段覆盖**」。

工单 §六自报的落法是：`state_from_facts→figures` 段由批 C 的 `test_repair_batch_c` 承载，`figures check→A4 finalize→A5 seal` 段由 `test_a4_gate` 承载，"两段共享 figures check 节点"。

判定：**不满足**。两段跑在两个不同的案上，共享的是"figures check 这个环节类型"，不是同一个案里同一份产物的传递。接缝处（`figures_from_facts` 真实产出的图与 `figure2-check-receipt` → A4 finalize 真实消费）在全库没有任何一条用例走过。这与盲审当初否决的手法是同一个：拿另一段的覆盖冒充本段。六个卡死点里"末点对账"和"A5 终态重验"两点的载体也分别落在这两段，接缝断裂时正好从缝里漏过去。

批 D 新增的 B-2 Solana `run()` 端到端确实是真增量（我确认它真跑分布扫描／figure2 check／A5 seal／adversarial runner），但它的起点是发布闸，不是 `state_from_facts`，补不上这条缝。

### F-D4（P2）收据的"人工裁决"面零机器强度，且没进残余边界声明

**实测**（`attack_receipt_strength.py`）：一段 20 行脚本，指纹用公开函数 `flip_fingerprint(pd)` 自算、披露值用 `ledger_real_flips` 自算，`approved_by="x"`、`user_decided_at_utc="1970-01-01T00:00:00Z"`、`reason="0123456789"`（恰好 10 字符无实质）、`evidence_refs` 挂一个 1 字节的 `junk.bin`、`report_locations=["x"]` → **trace rc=0，publishable=True，freeze recompute fails=[]**。

这本身与 `tolerance-waiver/v1` 先例同款（工单明说"强度同 F-02 waiver"），可以接受为设计边界。**问题在于没有如实声明**：工单 §④"残余边界（如实声明）"列了四条（旧式参数分支不可达／B-7 Solana 报错不指路／A5 只覆盖 new-analysis／F-07 收尾分支无用例），**没有这一条**；`scan-schemas.md` §4a 也没写。而本工程反复强调的元规则正是"内部自洽≠真实性，每轮再独立绕闸"与"如实声明残余边界"。

顺带：`evidence_refs` 的约束是"收据同目录内、非名册自身、三验通过"——1 字节任意文件即满足，"独立人工核对证据"这个措辞比实现强。

### F-D5（P2）GPT-F-06 的覆盖自报证伪，且 CLEAN 正例整格无用例

工单 §③ 写：「undetermined 过半与"深挖全 fetch_failed"由②的 mock 一并覆盖」。

**实测证伪**（`attack_gptf06_matrix.py`）：

```
② 的实际 invalid_reasons（deep_account_classes = all_zero_delta:1）：
   - 抽到 1 个销户账户但核到的区间内事件为 0（checked=0 且 closed>0…）
   - undetermined（all_zero_delta+fetch_failed）过半
   → 「深挖账户全部 fetch_failed」这条根本没出现
我另造的单独场景（getSignaturesForAddress 返回 None）才命中该 reason，rc=1 正确
```

**变异确认无锁**：把 `if deep_done and acct_cls["fetch_failed"] == deep_done:` 那两行整段删掉 → `test_repair_batch_d.py` rc=0、`invariant_scan.py` rc=0（副本实测，已还原）。

另外 **`CLEAN` 这一格全库没有用例**：施工方五格是 ①gma 失败 ②checked=0 ③NO_CLOSED_SAMPLED ④LEAK_FOUND ⑤墙钟，唯独缺"充分零漏→exit 0"这个最常见的正常出口。我独立构造后实测行为正确（`rc=0 status=CLEAN events={checked:1,covered:1,missing:0}`），但**行为对不等于有锁**——plan 验证方案第 2 条把"充分零漏→0"和其他格并列写在反例矩阵里。

### F-D6（P3）F-07 prepare 期泄漏临时件，且该格无用例

**实测**（`attack_f07_txn.py`，8 个注入点）：

| 场景 | rc | 判定 | 残留 |
|---|---|---|---|
| 2 文件 @第4次 replace（施工方原测） | 2 | 全无（字节原样） | 无 |
| 2 文件 @第3次（第二文件 done→bak） | 2 | 全无 | 无 |
| 2 文件 @第2次（第一文件 tmp→done） | 2 | 全无 | 无 |
| 2 文件 @第1次（第一文件 done→bak） | 2 | 全无 | 无 |
| **3 文件** @第6次 | 2 | 全无 | 无 |
| **3 文件** @第5次 | 2 | 全无 | 无 |
| **3 文件 prepare 期** `json.dump` 第 2 次抛 OSError | 2 | 全无（正式件没动） | **泄漏 `.done.json.refresh-tmp.<pid>` 1 个** |
| 3 文件 @6 且回滚 @7 失败 | 1 | 混合态（设计如此）＋`.recover` 1 个 | 符合设计 |
| 3 文件 @6 且两条回滚 @7@8 都失败 | 1 | 混合态＋`.recover` 2 个 | 符合设计 |

数据面的"全有或全无"在我扩的所有 commit 期注入点上都守住了，这部分质量很高。唯一瑕疵在 prepare 期：`fetch_hypersync_v2.py:335-345` 的 `staged.append(...)` 在 `with tmp.open(...)` **写完之后**，所以正在写的那个 tmp 一旦抛错就永远进不了 `staged`，`except BaseException` 里的清理循环遍历不到它，留在 `run_*/` 下。不影响正确性（glob 只匹配 `done.json`），是卫生问题；但 plan 与验收矩阵都点了"prepare 期失败"这一格，**工单 §③ 的 F-07 用例清单里没有 prepare 期注入**，所以这个泄漏是被漏测漏出来的。修法：先 `staged.append` 占位再写，或清理改为按命名模式 `glob(".*.refresh-tmp.<pid>")` 扫。

### F-D7（P3）收据路径三处口径不一致；A5 与 freeze 消费的收据未互绑

- trace：`--acknowledge-flip <任意路径>`，收据可在案外（`bound_ref` 只把 evidence 限制在**收据同目录**内，收据本身位置不限）
- freeze：`check_bound_file(case_dir, flips_ref)` 要求案根内，**文件名不限**
- A5：`Path(root)/"flip_adjudications.json"` **硬编码**

实测：把收据改名为 `flips_receipt.json`（案根内、trace/freeze 全合法）→ A5 抛 `溯源存在真实翻转锚点但案根缺 flip_adjudications.json 裁决收据`。方向是 fail-closed，但**误伤的是合法案**，且报错不提示"改名即可"。

同一根因还带出：A5 打开的是案根固定文件名那一份，**从不校验它与 ledger `input_binding` 绑定的那份是同一实物**。实测把 A5 侧收据的 `approved_by` 换成"完全没参与过的另一个人"、时间改 1999 → 仍 `DISCLOSED`（指纹与披露由 ledger 重算，一致即可）。也就是甲收据过 freeze、乙收据过 A5 是可行的。修法：A5 改为按 ledger `input_binding.algorithm_params.flip_adjudications` 的 path＋sha 定位并三验，与 freeze 同一口径。

### F-D8（P3）三处表述强于实现

1. **"封死 freeze 后删/换 ledger 旁路"**（CHANGELOG 6.40.0 条目、`scan-schemas.md:319`、`a5_report_seal.py:44` 注释）。实测边界：
   - 改 ledger 不改 freeze → **拒** ✓
   - 删 ledger 但 freeze 记录在 → **拒** ✓
   - **删 freeze ＋ 删 ledger → `NO_LEDGER` 放行**
   - **freeze 抹掉 `provenance_ledger_sha256` 字段 ＋ 删 ledger → 放行**
   - **抹掉 `policy_details` ＋ 同步改写 freeze 记录的 sha → `NO_FLIPS` 放行**（报告一个字不提翻转）

   根因是 `entity_freeze.json` 自身**全库没有任何 sha 级完整性锚**（`grep entity_freeze scripts/report scripts/lib scripts/evm` 只有 A5 读、handoff 写、holder_distribution_scan 读 revisions 长度）。这落在批 C 终验已定性的残余边界（"控制案目录者手写一组自洽小件即可过一致性校验"）里，不是新洞，但"封死旁路"这个说法应改为"封死单边改动"，免得将来被引用成比实际更强。

2. **`audit_closed_accounts` 早退路径不落报告**：`if not sigs` / `if not inits` 两处 `sys.exit(1)` 在写报告之前，实测"无 init 事件"场景 rc=1 且 `audit.json` 不存在。`data-pipeline-solana-capture.md:97` 的 status 契约把四个 status 写成了报告的固有字段，没说明"还有一类失败根本没有报告"——`closed=0` 弱结论与查询失败在**有报告时**可辨（这一半做到了），无报告时只能看 stderr。

3. **A-1 的 `policy_reject` 出口对"参数打错"也归档旧收据**：`supply_truth_gate.py` 第一个 `policy_reject` 挂在 `--tolerance-bps < 0` 上——手滑传个负数就会把上一轮合法 PASS 收据改名归档。作废是不销毁的（可改回来），但"政策拒绝＝旧收据不可信"的语义不该覆盖"参数写错了"。

---

## 三、变异法独立扩面（不复验施工方的 5 条，只扩新面）

| # | 变异 | 结果 |
|---|---|---|
| M1 | 删掉 `audit_closed_accounts` 的「深挖全 fetch_failed → INVALID_SAMPLE」判据 | **存活**（batch_d rc=0、invariant_scan rc=0）→ F-D5 |
| M2 | 删掉 A5 披露核对的 `share not in report_text` 半边 | **存活**（batch_d rc=0、round4_a5_seal rc=0）→ F-D1 |
| M3 | F-07 注入点扩到 8 处（含 3 文件、prepare 期、双回滚失败） | 7 处守住不变量，1 处（prepare）泄漏临时件 → F-D6 |
| M4 | A5 旁路矩阵 6 组（删 freeze／抹字段／抹明细／同步改 sha／收据改名／换裁决人） | 4 组通过、2 组被拒 → F-D1／F-D7／F-D8 |
| M5 | `--check-unseal` 收据改写＋删除，带 `labels_file` 对照组 | 收据两组全放行、对照组被拒 → F-D2 |

变异全部在副本做，逐条 `git checkout` 还原，收工时 `git status --porcelain` 为空；生产树全程零改动。

---

## 四、终判

**不建议原样收口，先消化 F-D1。**

F-D1 是"原 finding 没真正闭合"——盲审给 F-06 加披露实文核对时点名的攻击词就是"无关文本"，改完之后同一句攻击原样成立，而且份额那半边连测试锁都没有。这条不修，`flip-adjudications/v1` 这套链条里唯一有真实执行力的环节（披露）就是空的，剩下的指纹绑定只保证"收据跟着数据变"，保证不了"读者真被告知"。

F-D2／F-D3／F-D4／F-D5 建议同轮一起关，四条都是本工程自己定的元规则被违反的实例（同族等深、闸须为必经之路、如实声明残余边界、不信自报），修法都不大：D2 是往 `bound_records` 加一个键；D4／D5 分别是补一句声明和补两个用例；D3 需要新写一条端到端用例，成本最高但正是 plan 点名要的。

F-D6／F-D7／F-D8 可入台账或随手带上，不阻塞。

另外三件与技术无关但要记：①工单末行"未 commit"与落盘不符（第二次出现，建议节拍文案统一改成"由裁判代 commit"）；②CT-SEMANTIC-56 的裸单词 needle 建议换成更长的锚串；③`test_repair_batch_a`／`test_handoff_manifest` 的报错换岗虽然被拒面不减，但断言精度确有下降，值得在台账留一句，免得将来旧闸被误删时没人红。

对抗审查完成
