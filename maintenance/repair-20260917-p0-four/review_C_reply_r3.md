# 工单C复核：通过

v3 对 r2 五条意见的处置已闭合，未发现需要退回的新增问题或可确认的必红回归。**这是工单复核通过，不代表改后集成验收完成。**

基线 HEAD：`04cae51552056bde5eb63e235ef466fed73ecb6a`。白名单源码与 `8ead156` 无差异；开工、收尾 `git status` 和 `diff --stat` 均为空。报告全文已打印到 stdout。

| r2 编号 | v3 处置核验 |
|---|---|
| C-R04-r2 | C4-e 已覆盖 `case_new`。顺序为 distribution → camp/identity 更新 → build facts → A4 finalize → figure2/fig1 → A5 → analysis-new。e1 标签及成员与 state 一致；d 案只走 analysis-audit，保留手写 facts 合理。 |
| C-R05-r2 | 不扩 reseal 白名单的方案成立：调度方提交、同步 worktree 并保持干净后，overlay 为空。worktree 子进程自行建立 seed，ledger 的算法 `path` 与该 checkout 一致。21 例未实跑。 |
| C-R09 | C3 说明已移出代码块；现有 record 为 11 项；独立反例位于 `test_repair_batch_d.py:1282` 前，并在 main 的 `:1700` 后登记，符合既有 `check` 调用方式。拟议 C1/C2/C3 源码 `ast.parse` 通过。 |
| C-R10 | 无 state/渲染文本时，自检执行 G2/G3，G6 仅产生 NOTE；G1/G7、G4/G5 跳过。四处夹具的 current/total 分别为 `100/100`、`100/100`、`60/100`、`2000000/59127382`，内存 build 与自检均通过。 |
| C-R11 | 严格 loader 拒绝 `NaN`、`Infinity`、`-Infinity`、`1e999`、`-1e999`；整数字面量不经过 `parse_float`，普通小数通过。正常 build 后向 facts.metrics 注入 `1e999`，被 C2 比对拒绝。 |

实际核验范围与结果：

| 项目 | 结果与证据 |
|---|---|
| a 锚点 | 所列生产、测试定位及工单明确锚点已执行 `grep -n -F`：命中唯一、行号一致，多行上下文相符。P105 identity 写出锚为 `:216`；模板子串唯一位于 `:212`。 |
| b REQUIRED 范围 | 已追踪 batch_d → batch15 → batch18_shared_bundle_witness，并补查 batch18_review_digest；P105 → batch B；stage2/reseal；case_new。变量 profile、CLI 和 build_html 间接入口已查。`test_audit_release_gate.py:469–485` 只要求非空/指定子串；其他相关负例或分类筛选断言不要求零错误。R9 CLI 未传 profile，仍走 independent-audit。 |
| c stage2 建案 | `0xabc` 经真实 CSV 重放逻辑可用；`ENTITY_ADDR` 仅有 `:49/:54/:58` 三处，均被改删覆盖。distribution/camp 使用 balances_final 并对齐三账；build 位于最后一次 identity 改写之后。A4 自动封入 facts/identity；`finish_distribution_normal` 不覆盖已有三账。`Cases.fresh` 重绑文件不属于新增 facts 输入绑定集合，未见新增 seal 漂移。完整 `build_release_case/check_result` 未实跑。 |
| d derive 与消费者 | 双向延迟 import 成立；economic 条目作 entity_id、strict 成员作 addresses，与文档口径一致。evidence 路径检查拒绝绝对路径、子目录、点段及叶子符号链接。逐个检查 Facts、state 编译、figures、stage2 dual/fig2_selection/workorder、A4/A5、build_html，未见拒绝新增 provenance 顶层键的白名单。 |
| d `peak_date=None` | Facts 宏会输出字符串 `"None"`；state 编译读取 peak_raw，figure2 不依赖该日期，flow 宏可能显示 `"None"`。正式发布/收口仍拒绝 exploration。 |
| e 比对与路径 | current、peak、addresses、total_supply、新增实体五类手改均被独立内存反例拦截。按工单 `:355` 加入必须实施的 `regular_case_path` 检查后，符号链接被拒；`load_json` 本身仍会跟随链接。figure2 本名检查兼容现有 facts.json 收据。 |
| f 新 record | 三处 `==11` 断言已找齐，改成 12 覆盖执行计数；未见其他相关收据计数约束。实际执行新增 record：代表性 seed PASS；三个变体分别 BLOCK，detail 含 `e1/provenance/exploration`。`:246–259` 与 `:447` 后直接函数检查不执行新 record。`:586` 的 `other ten checks` 注释可顺手改成 `other eleven checks`，不影响执行。 |
| g Solana 夹具 | `owners_path` 在 `:966` 定义、`:1056` 对齐；首个 owner 为 `ownersol1=60`，三账 e1 与之相等，identity total=100，override peak=60。build 在 figure2/A4/A5 之前。真实 figure2 纯函数对空 series 返回 `([],0)`；指定成功断言未发现新增必红点。 |
| h C4-d | 针对 14 组要求进行了独立内存验证：基线因新增 API 不存在而 RED，拟议代码 14/14 通过。调用真实 `check_three_ledgers(chain=None)`，包含 balance_source SHA/as_of_block 校验。确定性及参数验证直接调用 `build_main`，未执行外部 CLI。 |
| i invariant 登记 | 对拟议源码作内存覆盖，实际 scanner 检出 producer `79→80`、consumer `115→117`、atomic `59→60`，transport 不变。按 C5 增补后，真实 manifest validator 返回 `[]`；`minimum_counts` 无须上调。 |
| j 文档 | 替换精确为 `58→53 B`；stat 合计 references `930070→930065`，SKILL.md=8021、commands-staging=8798。该行粗体配对、引用解析及八条模板契约均保持。未运行全量 docs_lint。 |
| k 回归与同族入口 | 未发现 §0.8 或 run_all 既有断言因本段必红。Facts/figures/state、独立 A4/A5、distribution_explanation_check 不自行重算 facts provenance；完整 new-analysis 发布和 stage2 check/amend 由本段覆盖。receipt-only 仍验收据/哈希；independent-audit、legacy 不属本段 REQUIRED 范围。 |
| l r1 八条 | C-R01 顺序、C-R02 REQUIRED/本名/链接检查、C-R03 非空账、C-R04 夹具覆盖、C-R05 ledger 前移与幂等、C-R06 独立反例、C-R07 docs_lint 移交、C-R08 源码基线与施工 HEAD 区分，均未重开。共享助手通过普通模块名和 P105 的 importlib 别名均可取得。 |
| m 新增绑定 | 在内存文件系统中执行原 `write_binding → replay_pass1 → emit_evm`：240 个 owner 完整保留，总量 `59127382`，owner-000=`2000000`，身份收据校验 `errors=[]`。`augment_gate` 默认空 rows/单 rows 两分支与旧实现产物逐字节相等。真实 reseal helper 在同一 checkout 重写 ledger 字节不变，facts 比对仍为 `[]`；模拟 worktree 路径下同样成立。 |

两点需要保留在交接中：

- **P105 不能作为 G8 全绿证据。** 其既有 identity_bridge 子目录布局及缺失 n_addresses/n_flags，使 `validate_gate` 返回三项错误；发布闸成功用例并不调用该 G8。这是原夹具边界，未由 v3 引入。P105/batch_d 发布闸绿例也不等于完整 HTML 的 G1/G8 绿例。
- 工单 `:5` 的复用关系描述不精确：batch13 使用 `test_r9_batch3_release_guards.build_case`，recon_fifth 自建夹具；实际额外复用 batch15 的还有 `test_batch18_review_digest`。它已间接获得共享 build 改造，不构成遗漏必红点。

原版 `test_report_facts.py` 七契约实际运行通过。**完整 stage2/reseal、发布/绘图集成、§0.8 全组及 run_all 未执行**；本环境只读，内存验证未计作落盘集成 GREEN。

全程离线、零文件写入、未 commit。未读取 `~/.codex/`、仓库禁读路径或 Desktop 内容；禁读 references 文件仅参与 stat 统计。

Codex session ID: 01a0afa0-db5b-74e0-8407-c3c73f178265
Resume in Codex: codex resume 01a0afa0-db5b-74e0-8407-c3c73f178265
