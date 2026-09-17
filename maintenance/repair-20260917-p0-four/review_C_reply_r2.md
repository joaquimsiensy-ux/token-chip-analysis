# 工单C复核：退回

v2 尚不能直接施工。发现遗漏的必红回归、reseal 验收白名单冲突，以及代码、夹具和输入校验问题。**原 C-R05 的 ledger 字节漂移已经修正，但 reseal 验收尚未闭合。**

完整报告已打印到 stdout。基线 HEAD 为 `a308e13ad01f83af9a30002ccb23f8b00b78fd1b`；白名单文件与 `8ead156` 无差异；开工、收尾工作树均为空。

1. **C-R04-r2｜P1：遗漏经 build_html 进入 new-analysis 的成功夹具。**

   工单位置：[§0.3、§0.8、C4](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/workorder_C.md:12)。

   事实：`test_a4_gate.py:378-381` 手写无 provenance 的 facts；`:490-497` 复制后仅更新分布和 camp；`:529-535` 要求 `analysis-new` 构建成功。实际调用链为：

   ```text
   build_html.py:254  "analysis-new": "new-analysis"
   build_html.py:434  profile=formal_modes[a.mode]
   build_html.py:489  if warns:
   build_html.py:493      sys.exit(1)
   ```

   对该 facts 执行拟议 C2，实得：

   ```text
   facts.json 缺 provenance 绑定块——须由 facts_gate.py build 从三账生成，禁手写
   ```

   因此成功断言必红；`run_all.py:84` 已登记该测试。共享助手不会自动覆盖这个调用点。

   **修订建议：**将 [test_a4_gate.py](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_a4_gate.py:496) 加入白名单和回归清单，在 case_new 的 add_camp_series 之后、finalize 之前调用助手，保留 `e1→实体1` 标签和 HTML 成功生成断言。

2. **C-R05-r2｜P1：未提交改动会被 reseal 的旧验收白名单拒绝。**

   工单位置：[§0.8、C4-a′](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/workorder_C.md:424)。

   事实：`test_stage2_reseal.py:528-529` 从当前仓库运行时调用 `overlay_acceptance()`；`:614-619` 仍是 W3 旧白名单：

   ```text
   620:    overlay = changed | untracked
   621:    assert overlay <= allowed, "白名单外变更，停止验收：" ...
   ```

   内存集合核对发现，本段七个生产/测试改动路径不被接受，包括 facts_gate.py、audit_release_gate.py、test_stage2_closeout.py 和共享助手文件；C_done/C_red 创建后也不被接受。即使预建 worktree 存在且 HEAD 正确，仍会失败。该测试在 `run_all.py:210` 登记。

   **修订建议：**更新 [overlay 白名单](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_stage2_reseal.py:614)，仅加入本段授权增量，保留 HEAD、逐文件 SHA、精确文件集合和零写入检查；或明确等价的调度方验收路径。这不是沙箱失败。

3. **C-R09｜P2：C3 插入块有语法错误，另有两处施工定位不准。**

   工单位置：[C3:347](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/workorder_C.md:347)、§0.4:13、C4-b:431。

   事实：以下说明位于要求插入的 Python 代码块内，没有注释符：

   ```text
   （stage2 收口不传 receipt；图 2 收据绑定由发布闸验。）
   ```

   原样 `ast.parse` 实得：

   ```text
   SyntaxError: invalid character '（' (U+FF08)
   ```

   此外，现有 run_checks 是 **11 个** record，§0.4 却写“现有 12 个”；C4-b 所称 `t_b2` 不存在，真实唯一锚为：

   ```text
   1245:def t_b1_b2_solana_new_analysis():
   ```

   `:1246` 是 import 行，同文出现三次。

   **修订建议：**说明移出代码块或加 `#`；§0.4 改为“现有 11 个”；C4-b 使用真实函数名和完整 with 块结束位置。独立 with 方案本身已解决 r1 的拆断调用问题。

4. **C-R10｜P2：P105 改造会生成违反既有 G2 的 facts。**

   工单位置：[C4-0、C4-c](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/workorder_C.md:433)。

   事实：`test_review_20260804_p105.py:142-147` 生成 owner-000=`2000000`，并把三账 e1 对齐到它；`:209-212` 调用 augment_gate 时没有 rows，命中：

   ```text
   identity_gate_fixture.py:57:
       balances = {"0x" + "f" * 40: 100}
   ```

   助手因此生成 current=peak=`2000000`、total_supply_raw=`100`。内存执行既有 facts gate 实得：

   ```text
   G2 Σ实体当前持仓 2000000 超过总供应 100
   ```

   空 whale_series 不检查缺失的实体线，C2 又仅与同一组输入重算比较，因此两者仍可零错误。

   **修订建议：**在 P105 中将 identity snapshot、receipt、gate 一起绑定到真实 owner 快照及供应量，再 build facts，并用既有 G2 验证正例。不能只改总供应字段而保留旧收据。

5. **C-R11｜P2：“严格非有限策略”存在可复现漏口。**

   工单位置：[C1:71、:206，C2:335](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/workorder_C.md:335)。

   事实：C1 使用普通 `json.load(fh)`；现有 `audit_release_gate.py:1225-1227` 只有 `parse_constant=reject_constant`。它拒绝 NaN/Infinity 字面量，但 `1e999` 被解析为 `inf`，不经过 parse_constant。

   内存反例：state_source 的 metrics 值为 Infinity，derive 接受并生成 formal facts；将 facts 中该值编码为 `1e999`。实际 loader 加拟议 C2 得到：

   ```text
   errors == []
   metrics.value == inf
   ```

   这是既有 loader 漏口被新生成链继承；上述零错误仅指新比对函数。

   **修订建议：**C1 输入读取及正式 facts 校验明确拒绝非有限浮点，包括指数溢出；补 NaN、Infinity、1e999 反例。

**其余逐项核验**

| 项目 | 实际核验结果 |
|---|---|
| a 锚点 | 已执行 `grep -n -F` 核对指定生产文件、测试删除块/插入点、三处计数、a4_gate:52、模板:212。明确引号锚对应基线；C4-b 定位问题见 C-R09。 |
| b REQUIRED 范围 | 已追踪 batch_d→batch15→batch18、batch13/recon_fifth、P105→batch B。batch15 动态改造未修改新绑定输入；chain=None 不增加深验调用次数；batch18 精确错误集合涉及的变更文件不在新绑定输入内。遗漏为 test_a4_gate。 |
| b 其他入口 | test_audit_release_gate:469-484 是非空/子串断言；formal_chain_support、robinhood、batch C、G1 cross-target 检查特定错误类别；batch1 缩小 REQUIRED 测单项缺件。R9 CLI 未传 profile，走默认 independent-audit。未发现这些入口因 REQUIRED 新增而必红。 |
| c stage2 夹具 | 已追到 augment_gate→write_binding→CSV→replay_pass1；0xabc 未遇地址长度门禁。distribution/camp 使用 balances_final；build 位于 identity 最后改写后、finalize 前；A4 自动封入 facts/identity。finish_distribution_normal 不覆盖已有三账。ENTITY_ADDR 仅涉及拟改/删除的三处。完整建案未实跑。 |
| d derive | 延迟 import 成立；助手按普通模块名及 P105 的 importlib 别名均成功装载。economic 条目作实体键、strict 成员作 addresses，符合经济控制下限和 entity_id 契约。basename 检查拒绝绝对路径、点段、子目录和叶子符号链接。 |
| d 消费者 | 逐个检查 Facts、state 编译、figures、stage2 dual/fig2_selection/workorder、A4/A5、build_html；没有拒绝新顶层 provenance 的键白名单。facts_inputs 不会展开进 state。 |
| d peak_date=None | 宏实际输出字符串 `"None"`；state 读取 peak_raw，不读 peak_date，纯编译验证通过；fig2 不消费该日期，flow 宏可能显示 `"None"`。正式闸仍拒绝 exploration。 |
| e 篡改与路径 | current、peak、addresses、total_supply、新增实体五类反例全部被 C2 拦截。loader 实测会跟随符号链接，regular_case_path 返回 None，所以工单的“若不拒则补判断”分支必须实施。figure2 本名判断兼容现有 facts.json 引用。 |
| f 新 record | 三处 `==11` 已找齐，未发现其他同义收据计数断言。三个变体返回应使 record BLOCK 的错误，分别含 e1/provenance/exploration。`:246-259`、`:447` 后的直接函数检查不执行新 record。Cases.fresh 完整 PASS 未实跑。 |
| g Solana | owners_path 在 :966 定义，:1056 align 时可用；e1=ownersol1，amount=60，助手得到 current=peak=60、total=100。空 series 可接受；收据在 build 后生成。指定正例未发现新增必红点，但未标为集成 GREEN。 |
| h 新用例 | v2 实为 C4-d 的 **12 组**。独立内存案：基线 **0/12**，缺 derive/build API；拟议 C1/C2 **12/12**。实际调用 check_three_ledgers(chain=None)，核了快照 SHA/as_of_block 和三种空账。build 参数/返回码通过直接调用 build_main 验证，未跑外部 CLI。 |
| i 登记 | 对拟议源码作内存覆盖，真实 scanner/manifest validator 增补后 `errors=[]`。producer 79→80、consumer 115→117、atomic 59→60；transport=65、formal_entrypoints=61 不变。minimum_counts 无须上调。 |
| j 文档 | 唯一子串 **58→53 B**；stat 合计 references **930070→930065**，commands-staging=8798，SKILL.md=8021。替换行粗体标记配对、引用可解析，八条模板契约保持。完整 docs_lint 未运行。 |
| k 同族路径 | Facts/figures/state、A4/A5、distribution_explanation_check 未独立验证 facts provenance；正式 build_html analysis-new 经发布闸覆盖。stage2 `--receipt-only` 仍只比收据/文件哈希，新增重算在完整 check/amend。independent-audit、legacy 不属本段 REQUIRED 范围。 |

**r1 八条处置**

| 原编号 | v2 状态 |
|---|---|
| C-R01 | 顺序设计闭合：distribution/camp→provenance→build→finalize。 |
| C-R02 | REQUIRED＋figure2 本名检查已补；须实施 regular_case_path 条件分支。 |
| C-R03 | 闭合：先验非空及第 12 组反例。 |
| C-R04 | 未闭合：遗漏 test_a4_gate；P105 供应量不一致。 |
| C-R05 | **原漂移闭合**：真实 helper 内存执行两次，ledger 均为 1034 B、字节完全相同；重写后 facts 比对无误。验收路径另有白名单冲突。 |
| C-R06 | 独立 with 方案闭合；函数定位须更正。 |
| C-R07 | 闭合：docs_lint 移交调度方。 |
| C-R08 | 已区分源码基线与施工 HEAD；仓库尚无 construct_C_prompt.md，派工时须提供正确 HEAD。 |

实际运行的基线 `test_report_facts.py` 既有契约通过。完整 build_release_case、stage2/reseal、发布/绘图集成测试和 run_all 未执行。完整 state 编译曾被 Matplotlib 缓存写入限制阻断，后续只验证纯编译逻辑。

全程离线、零文件写入、未 commit。禁读路径内容未读取；禁读 references 文件仅参与 stat 统计。收尾 `git status`、`git diff --stat` 均为空。

Codex session ID: 01a0af88-ab23-7aa0-ad7a-fac5f441c97c
Resume in Codex: codex resume 01a0af88-ab23-7aa0-ad7a-fac5f441c97c
