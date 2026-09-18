# 工单E复核：退回

v1 有 6 处登记表述需要修订，不能原样派施工。9.0.0 的主版本档位成立；本次不重新评价三段施工。报告全文已打印到 stdout。

复核对象：[workorder_E_version.md](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918c-p1-f02-f04-f05/workorder_E_version.md)，基线 `8b041842`，HEAD `250630cd07d7`。以下工单行号均指该文件。

1. **E-R1-01：修复项严重级别记错。**  
   **工单位置：** §2.4，索引第 22 行、详细段标题第 26 行。  
   **事实：** “三条 P1 修复”与[裁决表](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918c-p1-f02-f04-f05/ruling_20260918.md:7)不符：F02、F04 是 P1，F05 是 P2；F05 工单导语同样标为 P2。  
   **修订建议：** 两处统一改为“三条修复（P1×2、P2×1）”。

2. **E-R1-02：流通量选材逻辑归属错误。**  
   **工单位置：** §2.4，第 28 行“出处与裁决”、第 31 行“F02”。  
   **事实：** `state_from_facts` 没有按流通量判断必画的逻辑；其 [compile_state](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/state_from_facts.py:62)读取总供应量、decimals、symbol，占比按总供应计算。既有流通量选材分支实际位于 [stage2_closeout.flow_selection_errors](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/stage2_closeout.py:202)。  
   **修订建议：** 两处均明确写为 `stage2_closeout.flow_selection_errors`，删除对 `state_from_facts` 的这一归因。

3. **E-R1-03：F02 的 RED→GREEN 数量多记一例。**  
   **工单位置：** §2.4，第 32 行“工艺”。  
   **事实：** [盲审逐例结果](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918c-p1-f02-f04-f05/blind_F02_reply_r1.md:114)为：用例 22 一例、用例 23 六例、贯通用例一例，共 **8 例 RED→GREEN**；用例 24 是 **GREEN→GREEN**。第 130 行汇总明确如此，施工记录也一致。  
   **修订建议：** 改为“9 例逐例复算：8 例 RED→GREEN、1 例 GREEN→GREEN”。

4. **E-R1-04：存量描述混淆收据与引用字段，并扩大了盘点结论。**  
   **工单位置：** §2.4，第 34 行“档位与迁移说明”的存量括注。  
   **事实：** [台账 Q8/Q9](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918c-p1-f02-f04-f05/code_change_pending.md:12)中，ARC 的内联 dict 是引用结构，旧收据是其所指文件；Q9 的字符串是 `price_source.dual_source_check` 字段值，并非收据格式。Q9 还限定“无顶层引用时基线已拒”。允许材料没有支持“其余为字符串或 null”这一全量盘点断言。  
   **修订建议：** 按 Q8 列明四类拒收对象；ARC 写成“引用结构可保留，所指旧收据须迁移”；字符串内联按 Q9 保留分支条件，删除无依据的“其余……null”概括。

5. **E-R1-05：F02“无迁移”漏掉适用条件。**  
   **工单位置：** §2.4，第 34 行末句。  
   **事实：** [F02 工单 §4](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918c-p1-f02-f04-f05/workorder_F02_circulating.md:170)仅对“未声明且保留原 facts.json”的旧案免迁移。主动重 build 会改变文件哈希，须刷新相关绑定；新增流通量声明还可能要求补流转图。该条件已经在 F02 r1/r2 复核中明确。  
   **修订建议：** 改为“未声明且保留原 facts 的旧案无需迁移；主动重 build 后须刷新 A4、图 2 旁车/对账收据、工单与 closeout、A5/HTML 绑定；新命中下限时补图及报告引用”。

6. **E-R1-06：持久化字段计数口径不一致。**  
   **工单位置：** §2.4，第 35 行“成本-质量指标”。  
   **事实：** 按该句列举的生产者输出键计算，[price_check](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/prices/price_check.py:195)新增 `price_file_sha256`，[facts_gate](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/facts_gate.py:503)新增 `token.circulating_supply_raw`、`token.circulating_supply_source`，合计 **3 个输出字段**。把 facts 两键合为一项是在数契约扩展组数。  
   **修订建议：** 改为“新增产物字段 3（收据 1、facts.token 2）”，或明确写“持久化产物契约扩展 2 处，共新增 3 个输出键”。

其余实际核对结果：

- **锚点与字节：** VERSION 现值为 `8.0.0\n`；pyproject 第 15 行、SKILL 第 23 行、CHANGELOG 第 13/96 行均准确，指定锚各唯一。内存替换后四处版本一致为 9.0.0，SKILL 仍为 8021 字节，活跃条目 78→79。基线、HEAD、工作区的 references Markdown／SKILL／commands-staging Markdown 均为 **930076／8021／8798**，对应版本登记前内容无差异。
- **代码与过程：** 三段提交分别为 **+82/−4、+144/−10、+92/−3**；合并 diff 为 **8 文件、+317/−16**。除上述指认外，所述 envelope/getcode、价格收据校验、流通量生产与发布重算的函数、字段、文案与 diff 相符。复核轮次 **F04 3→2→通过、F05 5→3→通过、F02 2→通过**，合计 15 条意见；盲审 **F04 FAIL→PASS、F05 PASS、F02 PASS**，均与回复一致。两次停工原因分别为派工 HEAD 被提示词提交推进、必跑测试的历史 maintenance 依赖与禁读纪律冲突。
- **测试记录：** 定向 **14/6/11** 与 done 文件及施工提交登记一致；F05 reseal **21/21** 有提交 `830ce9f` 登记，F02 后 run_all **151/151**、九项守卫 PASS 有提交 `f2d02cd` 登记。静态核得 SUITE 前后均 151 项，包含 21 项用例的 reseal。收官回复中的三反例、F05 九场景、F02 五分支及交叉五组与工单描述相符。
- **档位与 F05 迁移步骤：** 旧有效收据因缺必需字段而被拒，符合 CHANGELOG 第 4 行的不兼容契约主版本规则，也有追加裁决支持。禁用 amend、完整 check 后 receipt-only、APU 暂不重跑、ALL_SKIP 影响四条正式候选链且不限币龄，与 F05 导语及 Q8/Q14 一致。
- **其他指标与体例：** 生产逻辑文件 5、新公开入口 0、新增 SUITE 入口 0，与 diff 一致；外部网络 0 与离线替身及既有执行记录一致。索引确为一行；详细段沿用“出处与裁决→修复项→工艺→字节与测试→档位与迁移→成本-质量”的六类顺序。实际顶级 bullet 数为 **本单 8、8.0.0 条目 7、7.2.1 条目 9**，并非固定六条，因此不把数量差异列为退回项。

本轮只读、离线，未改文件、未 commit，结束时工作区干净；未读取禁区或 memories。字节统计对禁读文档只使用大小元数据。测试通过数字依据既有记录核对，本轮未重跑回归或 lint；版本替换仅在内存中验证。
