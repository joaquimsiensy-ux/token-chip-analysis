# 工单F02复核：通过

v2 已正确消化 F02-R1-01、F02-R1-02，未发现新增的退回项。

复核基于 HEAD `a1541898d953`；实际执行 `git diff --exit-code --no-ext-diff --no-textconv 8b041842 -- scripts`，输出为空、退出 0。F04/F05 尚未施工，依赖其落地的锚按待核项处理。

本轮完成源码核对、内存拼装编译，以及内存文件系统中的函数执行。三账校验、发布比较和选材函数使用源码原函数；未运行完整测试入口或磁盘 CLI，不把内存结果记作完整回归 PASS。

**1. R1-01：独立夹具与 §2.6 贯通用例已修正。**

- [test_report_facts.py](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_report_facts.py:12) 模块级仅导入依赖、加载 facts_gate、建立常量和定义函数；主入口受 `__main__` 保护。实际以 `-B` 导入，未触发建目录、写文件、子进程或网络。加载 facts_gate 的模块初始化不执行 build。
- `_r07_case` 经真实 derive 逻辑得到 `mode=formal`、total=`1000`、e1 current=`100`、label=`大庄#1`；peak=`150`，日期 `2026-01-02`，无 peak_overrides。
- [update()](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_stage2_closeout.py:144) 接受任意 case 根路径，按 `case / rel` 读改写；已在内存夹具验证其能更新 `root / "state_source.json"`。Path 实际导入于第 7 行，tempfile 于第 11 行；第 15 行已把 tests 目录加入导入路径。
- baseline 实际结果：token 无流通量键，空 flow 的 errors 为 `[]`，notes 含“未声明流通量”，不存在“包含下限”错误。
- 原样执行工单 §2.6 函数：基线前半通过，后半取新键时抛 `KeyError`；应用计划代码后全函数通过。声明 400 后，`100×5=500<1000`，同时 `500≥400`，确实单独命中流通量门槛。

临时目录环境已区分：`/private/tmp` 的本机目录权限为 `01777`；当前只读沙箱的 `os.access(W_OK | X_OK)` 返回 False，不能在本轮落盘创建夹具。本机无该沙箱限制时，目录权限允许普通用户创建；本轮未实际创建验证。[既有用例第 86 行](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_report_facts.py:86) 已使用同一目录，因此 v2 没有引入新的目录依赖。

**2. R1-02：兼容性表述及迁移范围已补齐。**

[§1.3](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918c-p1-f02-f04-f05/workorder_F02_circulating.md:23) 的三项承诺成立：未声明时仅 producer.sha256 随生产者源码变化；token 保持原三键；同版本重复 build 字节一致。内存执行实际验证了以上结果，以及旧 facts 在新生产者重算比较下仍通过。

发布比较实际在 [audit_release_gate.py:1567](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/audit_release_gate.py:1567) 移除整个 producer 块，因此不会因 producer.sha256 更新而拒绝保留的旧 facts。主动重 build 的文件哈希变化及绑定刷新要求，§1.3 已明确指向 §4。

[§4](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918c-p1-f02-f04-f05/workorder_F02_circulating.md:170) 已覆盖 A4、图 2 旁车及对账收据、工单、closeout 收据、A5/HTML；新增选材下限还须补流转图和报告引用。已核源码中的 A4 强制封入 facts、图 2 旁车 facts 哈希校验和 A5 对 A4 的绑定。reseal 末段只重填工单并 check，不生成 fig2-series，补充说明准确。

**3. §2 全部锚点及相关回归入口已核。**

下表行号为当前源码实测值：

| 工单位置 | 文件与行号 | 锚文本识别 | 命中数 |
|---|---|---|---:|
| §2.1 | [facts_gate.py:10](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/facts_gate.py:10) | token 示例整行 | 1 |
| §2.1 | facts_gate.py:66 | “可选，优先于 provenance 锚点…”整行 | 1 |
| §2.2 | facts_gate.py:380 | dual_basis 须为对象的 raise | 1 |
| §2.3 | facts_gate.py:477、478 | facts/token 初始化、保留的 entities/metrics 续行 | 各 1 |
| §2.4 | [stage2_closeout.py:209](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/stage2_closeout.py:209) | `circulating = int(circulating)` | 1 |
| §2.5 | [test_report_facts.py:326](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_report_facts.py:326) | 最后一个既有用例续行 | 1 |
| §2.5 上下文 | test_report_facts.py:327 | `assert not failures` 整行 | 1 |
| §2.5 | test_report_facts.py:328 | “21 类”打印整行 | 1 |
| §2.6 | [test_stage2_closeout.py:605](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_stage2_closeout.py:605) | `def facts_vs_ledgers_rejects_hand_edit(cases):` | 1 |
| §2.6 当前列表尾行 | test_stage2_closeout.py:631 | `facts_vs_ledgers_rejects_hand_edit]` | 1 |
| §2.6 F05 后列表尾行 | test_stage2_closeout.py | `facts_vs_ledgers_rejects_hand_edit, price_receipt_content_enforced]` | 0，待 F05 |

F05 工单 §2.5 明确生成最后一项锚；内存应用该尾行变更后命中 1 次，追加 F02 测试后 TESTS 也只登记一次。施工时仍须按工单重核唯一性，当前不记为已落地。

§2 两份生产文件及两份测试文件的计划修改均在内存中编译通过；Facts、gate_check、build_main 的 AST 保持不变。既有“raw=50、无 source”的直接消费者断言继续成立。

§0.8 新增 [test_repair_batch_d.py:1205](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_repair_batch_d.py:1205) 与本段相关：Solana 夹具通过 build_facts_from_ledgers 调用真实 facts build，未声明流通量；第 1281 行起另有 facts 手改及缺件的发布闸测试。纳入定向回归合理。

**4. flow_migration 三分支仍成立，分支①已得到贯通固化。**

| 裁决分支 | 应用 v2 后的内存执行结果 |
|---|---|
| ① 合法声明 400 | token 写出 raw 与 source/asof；发布重算 errors=`[]`；空 flow 报 `包含下限 ['e1'] != []`，NOTE 记录声明口径 |
| ② facts_inputs 写扁平键 | derive 明确抛 ValueError，文案含“键名错位” |
| ③ 无声明而手补 facts.token | 发布比较报 `facts.token 与三账重算值不一致` |

§2.6 将真实 derive 返回值直接交给 flow_selection_errors，验证了生产者到消费者的贯通；用例 22 另行验证合法声明的发布重算一致。

逐例结果与工单 RED 描述一致：22 为 KeyError→通过；23 六个变体分别为“应拒绝”断言失败→通过；24 前后均通过；§2.6 为前半通过、后半 KeyError→全函数通过。

**5. 版本与执行纪律。**

按 [追加裁决](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918c-p1-f02-f04-f05/ruling_20260918.md:36)，版本档位为 **9.0.0**，不再重议。

全程离线、只读；未读取 `~/.codex/`、memories 或其他禁读路径，未修改文件、未创建磁盘夹具、未 commit。报告全文已直接打印至 stdout。
