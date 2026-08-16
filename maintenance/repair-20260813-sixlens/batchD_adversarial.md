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
| A-2／A-4 评估结论（不做，留 R10-12／R10-13） | **理据成立**：A-2 确实是政策决定（现行 `FORMAL_TOLERANCE_BPS_MAX` 只管无 waiver 路径，有 waiver 时 `approved_tolerance_bps` 无上限属实）；A-4 确属新功能面。r10_ledger 13 条与 CHANGELOG 的"6＋2＋3＋2"口径对得上【终验勘误（BLOCKER-1）：本断言落盘晚于消化轮 1 追加 R10-14/15，写下时已失真——实为 15 条，CHANGELOG 已订正为"6＋2＋3＋2＋2"】 |

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

---

# 消化轮 1 复核（对象 `da8da71`，基线 `b3ee352`）

- **方式**：只读＋副本变异。副本 `/private/tmp/batchD_probe/repo2/`（`git rev-parse HEAD = da8da71`），7 条变异逐条注入后 `p.write_text(orig)` 还原，收工 `git status --porcelain` 为空；生产树全程零改动
- **基线独立复跑**：`run_all.py` **EXIT=0**；`invariant_scan.py` rc=0（producers=54／consumers=63／atomic=46，与轮 0 一致）
- **攻击重放脚本**：`attack_r1_fd1.py`（F-D1 六例）、`attack_r1_others.py`（F-D2/4/7/8 十例）、`/tmp/mut_r1.py`（7 条变异）

## 1. F-D1~F-D8 逐条判定

| 编号 | 判定 | 复核证据（我自己重放的，不引用工单自报） |
|---|---|---|
| F-D1 | **CLOSED** | 原攻击（无关附录散落全文）→ 拒「披露位置在报告中不存在」；裁判点名的"标题同名但内容在别章"→ 拒「缺策略名 pro_rata」；绿例真披露段照过。存活变异 M2（份额半边）**转红**；位置锚整体中和（切片退化全文）**转红**。`report_locations` 从装饰字段变成真消费者 |
| F-D2 | **CLOSED** | 冻结后改写收据（换裁决人＋换理由）→ rc=2「绑定文件哈希/大小漂移: flip_adjudications.json」；删收据 → rc=2「绑定文件不存在」；复原 → rc=0。变异（`bound_records.append` 改 pass）**转红** |
| F-D3 | **CLOSED（EVM 一条，Solana 差额已如实入账）** | 逐段核 `t_fd3`：①`build_evm_case` 真跑 replay_duck→`compile_state` formal（断言 `series_binding=="producer-sidecar"`）②同案 `figures_from_facts check` 真产 `figure2_check_receipt.json` ③**A4 finalize 的 `--seal-files` 真封 `analysis-state.json`＋`figure2_check_receipt.json`**——①②的真实产物在同案被 A4 封口，这就是原 finding 指的那道接缝 ④A5 同案收口绑 A4。①→②无直接数据流是**生产架构本身如此**（`figures check` 吃 facts＋whale_series，不吃 state，`report-template.md:220` 为证），不是测试偷工。Solana 同案链未建已写进工单 §一并落 `batchD_ledger` 二d |
| F-D4 | **CLOSED** | sanity 闸实测：`x`/1970/1 字节 → 拒（approved_by 占位）；仅抬时间、仅抬证据仍拒；**全部踩线（`xy`/2026/16 字节垃圾）→ 通过**——这正是工单 §四1 与 §4a 声明的边界（"机器验不了裁决实质真伪，只拦形式上就不是裁决的收据"）。**声明与实现一致，我原 finding 的核心诉求（未声明）已闭合** |
| F-D5 | **CLOSED** | 存活变异 M1（删「深挖全 fetch_failed」判据）**转红**，红在新用例「F-D5 深挖全 fetch_failed → exit 1（独立判据，有测试锁）」；CLEAN 格已补用例；工单主动更正了"由②一并覆盖"的错误自报 |
| F-D6 | **CLOSED** | 变异（`staged.append` 挪回写后）**转红**，红在「正式件原样＋零临时件泄漏」并打印出泄漏的 `.done.json.refresh-tmp.31086`——正是我轮 0 抓的那个文件名 |
| F-D7 | **CLOSED** | 案外收据 → trace rc=2「必须在案根内」；改名收据 `flips_receipt.json` → A5 **DISCLOSED 不再误伤**；A5 侧换收据（裁决人换人）→ 拒「sha256/size 不符」，"甲收据过 freeze、乙收据过 A5"封死；变异（互绑改 `if False`）**转红** |
| F-D8 | **CLOSED（三小项全落地，无台账搪塞）** | ①表述改准：`scan-schemas §4a:320`／a5 docstring／CHANGELOG 均改成"封死**单边改动**"并点名 freeze 无上位 sha 锚属批 C 残余边界；**评估落点真落地**——发布闸 new-analysis 段接入 A5 seal 重验，变异删除该段 → **转红**（完整案删 `entity_freeze` 后发布闸不再报错）。单元层双删仍 `NO_LEDGER` 通过，但已声明为"无溯源案语义、机器锚在发布闸层"，与实现一致 ②早退落 `INVALID_SAMPLE` 报告（边集缺失用例 rc=1＋报告在场）③负容差实测 rc=2、旧 PASS 收据字节原地未动、零归档件 |

**变异电池 7/7 全红**（含轮 0 的两条存活变异 M1／M2 双双转红）：M1 fetch_failed 判据／M2 份额半边／MD1 位置锚／MD2 冻结绑定／MD3 prepare append／MD4 收据 sha 互绑／MD5 发布闸 A5 重验。

## 2. 新 finding（3 条，全部轮 1 新引入）

| 编号 | 严重度 | 轮 1 新引入 | 一句话 |
|---|---|---|---|
| N-D1 | P2 | 是 | 披露核对要求报告实文里出现**英文策略名** `pro_rata/fifo/lifo`——纯中文真实写法实测被拒，而 `report-template.md` 对此零提及 |
| N-D2 | P3 | 是 | 切片内仍是三项独立子串搜、location 由收据自填可指向任意标题：**否认性术语段**与**通用词 location** 两例实测通过；工单"那这段事实上就是披露本身"表述强于实现 |
| N-D3 | P3 | 是 | new-analysis 发布闸新增"必须带 `--report`"硬性要求未进 `analyze-workflow.md`／`independent-audit-protocol.md` 的命令描述 |

### N-D1（P2）中文报告被新闸误伤

实测（`attack_r1_fd1.py` 变体 D）：报告段落写成真实交付形态——

```
## 翻转披露
本实体存在双来源结构，三种库存消耗口径给出的主导终点不一致：
按比例口径主导终点为 AAAA（50.00%）；先进先出口径为 BBBB（100.00%）；
后进先出口径为 AAAA（100.00%）。结论按多口径并列披露。
→ 被拒：报告披露段（翻转披露）缺策略名 pro_rata
```

这是**真正合格的并列披露**，却过不了闸。契约只写在 `scan-schemas.md §4a:320`（schema 页），`report-template.md` grep `pro_rata|fifo|lifo|并列披露` **零命中**——写报告的人按模板写就必卡。报错文案会指路（"缺策略名 pro_rata"），所以不会静默出错，但"为过闸在中文报告里塞英文标识符"是个坏的产品决定。

修法建议（择一）：①策略名接受英文标识符**或**其中文对照词（`pro_rata|按比例`、`fifo|先进先出`、`lifo|后进先出`）；②去掉策略名检查，改为要求三个 `(ident, share)` 对**全部**落在同一切片（并列性由"三组不同终点/份额同段出现"体现）；③保留现状但同批把要求写进 `report-template.md` 的图表/披露章节。无论哪种，都要补一条中文真实披露的绿例。

### N-D2（P3）切片内的残余绕路，且工单表述又强于实现

工单 §一 F-D1 段写：「攻击者若想伪装：得在报告里造一个被收据 locations 点名的章节、里面同段写全三策略名＋正确终点＋正确份额——**那这段事实上就是披露本身**」。两个反例证伪：

```
[变体B] ## 翻转披露
        （本节为脚本自检占位，与结论无关）内部标识 pro_rata / fifo / lifo；
        校验串 AAAA、BBBB；占位数值 50.00、100.00。以上均非分析结论。
        → 通过 DISCLOSED

[变体C] 收据 report_locations 写通用词 "附录"，命中报告里任意一个附录标题
        ## 附录 A：术语
        pro_rata / fifo / lifo 为内部标识；AAAA、BBBB 为校验串；50.00 与 100.00 为占位数值。
        → 通过 DISCLOSED
```

即"一段明确写着与结论无关的术语表"就能满足披露义务。这一层残余本身可接受（属作者蓄意伪装＝F-12 同族），**问题是表述**：F-D8 刚整改完"表述强于实现"，同一类问题在轮 1 的工单里复发。建议把这句改成"剩余可绕路＝作者在被点名章节里堆砌三项串但不作真实披露，属 F-12 边界同族"，与 §4a 同步。

### N-D3（P3）新硬性要求没进工作流文档

`audit_release_gate.run()` 的 new-analysis 段新增 `report is None → errors`。`analyze-workflow.md:166` 只写「强制 `audit_release_gate --profile new-analysis`」，没有 `--report` 字样；`independent-audit-protocol.md:163` 的完整命令带 `--report` 但那是另一条 profile。既有测试全绿（都带 `--report`），所以只是文档欠账，不是线上缺陷。

## 3. 批 A/B/C 已收口实现的抽查（裁判点名 4）

- 轮 1 共 16 文件，其中生产文件 7 个：`a5_report_seal`／`handoff_manifest`／`entity_source_trace`／`audit_release_gate`／`fetch_hypersync_v2`／`supply_truth_gate`／`audit_closed_accounts`。逐 hunk 对 diff-finding-map，**全部落在 F-D1~F-D8 的 owner 范围内**，无游离 hunk
- **既有测试文件零改动**：`test_repair_batch_a/b/c`、`test_handoff_manifest`、`test_a4_gate`、`test_review_20260804_p105`、两个 batch3 切片本轮**一个字没动**，`run_all` 仍全绿——本轮没有出现"为让新闸过而改既有测试"
- 批 A 的 F-02 容差钳制未被削弱：`supply_truth_gate` 只把 `--tolerance-bps < 0`（参数错）从 `policy_reject` 摘出来，`> FORMAL_TOLERANCE_BPS_MAX and not waiver` 分支原样走 `policy_reject`（作废语义保留），实测负容差 rc=2 且不归档、超钳容差路径未动
- 批 B 的 B-7／B-1 与批 C 的序列链本轮未被触及（`audit_release_gate` 的改动只在 `run()` 尾部新增 A5 重验块，`check_three_ledgers` 一行未改）

## 4. 终判

**批 D 可收口。**

八条 finding 全部 CLOSED 且逐条有我自己重放的转拒/转红证据，7 条变异全红（含轮 0 两条存活变异转红），没有一条走"台账搪塞"。F-D3 的接缝、F-D8 的评估落点这两处最容易糊弄的地方，施工方都做成了真机器件（A4 同案封口真实产物、A5 重验进发布必经路），变异删掉即红。

三条新 finding 无一是安全洞：**N-D1 是纯误伤面，建议随收口一并改掉**（改一行判据＋补一条中文绿例＋`report-template.md` 补一句，成本约 30 分钟），否则下一个带 flip 的真实 new-analysis 案会在 A5 卡住；N-D2／N-D3 属改口与文档欠账，入台账即可。若裁判希望零遗留收口，把 N-D1 并进本轮再复跑一次 `run_all` 即可，不必单开消化轮 2。

消化轮 1 复核完成

---

# 收口补丁单点点验（对象 `aa4c7ad`，基线 `da8da71`）

只读＋副本 `/private/tmp/batchD_probe/repo3/`（`git rev-parse --short HEAD = aa4c7ad`），变异后 `git checkout` 还原、`git status` 为空；生产树全量 `run_all.py` **EXIT=0**。

## 1. N-D1 场景重放（`attack_r2_fd1.py`，六例）

| 场景 | 结果 | 应然 |
|---|---|---|
| 绿例 真披露段（英文策略名） | DISCLOSED | ✓ |
| **变体D 纯中文真实披露**（按比例/先进先出/后进先出，无英文标识符） | **DISCLOSED** | ✓ **N-D1 已修** |
| 原攻击 无关附录散落全文 | 拒「披露位置在报告中不存在」 | ✓ 未被放宽 |
| 变体A 标题同名但内容在别章 | 拒「缺策略名 pro_rata（可写 pro_rata / 按比例 任一）」 | ✓ 未被放宽 |
| **变体E 中文披露但份额写错**（99.99/88.88/77.77） | 拒「缺 pro_rata 份额数字 '50.00'」 | ✓ 别名族**只**放宽策略名写法，终点标识与份额判据一字未动 |
| 变体B／C（否认性术语表／通用词 location） | 仍通过 | ✓ 与登记的 N-D2 残余一致，未扩大 |

改动面核对：`FLIP_POLICY_ALIASES` 三组等价词，a5 侧 `policy not in section` → `any(alias in section ...)`，**其余判据零改动**；ident/share 两条检查原样。

## 2. 变异抽验

删掉三组中文别名（`("pro_rata", "按比例")` → `("pro_rata",)` 等）→ `test_repair_batch_d.py` **EXIT=1 转红**，红在中文绿例：`ValueError: 报告披露段（翻转披露）缺策略名 pro_rata（可写 pro_rata 任一）`。施工方"删中文别名即红"自报**属实**。

## 3. N-D2 登记与表述改准

- `batchD_ledger` 二d 新增登记条目：明写"切片内三项仍是独立子串搜""location 由收据自填可指向任意标题"，两实例逐条列出，归入"validator 是一致性校验器不是真实性证明器"（§13 已声明边界），并给出再收一层的方向（披露段结构化标记块，R10 设计面）
- 工单 `:16` 的原句已**就地改准**：「那这段事实上就是披露本身」→「切片内三项仍是独立子串搜——作者在被收据点名的章节里堆砌三项串但不作真实披露…可以过闸，属 F-12 已接受边界同族」。**与我的实测逐字相符，不再表述强于实现**
- N-D3：`analyze-workflow.md` 报告入口段已补「new-analysis 发布闸必须带 `--report`」并说明 fail-closed 理由；`report-template.md` 另补第 ④ 条披露章节写法（含中英文任一的明示与 `（50.00%）` 形态示例）——报告作者按模板写即可过闸，文档欠账清零

## 4. 点验结论

**N-D1 点验 PASS**（修好且无副作用：放宽面精确限于策略名写法，三条拒绝面原样，变异转红有锁）。

**批 D 收口。** 八条盲审 finding 全 CLOSED、三条复核新 finding 中 P2 的 N-D1 已修、N-D2／N-D3 已登记与改口，无阻塞项。

收口补丁点验完成
