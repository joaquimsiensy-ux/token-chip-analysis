# 盲审 B：PASS

审查范围：`0877f71..03507cb -- scripts/`，工单文件头为 **v2**；已核对施工报告、RED 证据及 r1/r2 复核记录。未发现违反本段不变量、弱化既有断言或引入回归的缺陷。**完整回归受只读沙箱阻止，本轮未取得完整脚本 PASS。**报告全文已打印到 stdout。

当前 HEAD 为 `1e830b6`；已确认所审代码、证据及相关调用面与 `03507cb` 相同。以下代码行号对应施工后版本。

**a、b｜不变量与六视角**

生产文件：[scripts/report/audit_release_gate.py](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/audit_release_gate.py:782)。

1. **字段来源：PASS。**  
   :915–919 将 expanded 单独汇总；:940–944 强制申报 wallet 等于 strict 位置之和；:949–966 保留设施逐项校验及 confirmed 加总闭合。:971–985 重新计算下限，上限至少为下限＋expanded。wallet 虽先读取申报字段，但此前等值检查已约束它；错误不会被后续区间检查清除，原“自报 300”反例被拒绝。

2. **失败分支：PASS。**  
   :973 按成员身份判断 expanded，零余额成员也要求字段；:974–977 拒绝缺字段。:979–981 拒绝显式 null、非数组及非两元素数组，无 expanded 时同样执行。:983–987 校验整数端点、下限相等及上限下界；既有整数解析器 :417–434、:601–603 对非法数值登记错误。错误最终使 CLI 返回 BLOCK/2（:1709–1718）。

3. **存量迁移：PASS。**  
   无 expanded 且无区间字段时，严格成员汇总与原算法相同，新增分支不产生错误。已核 [batch15 夹具 :57–83](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_batch15_three_ledgers_frozen.py:57)，以及 [batch_d :1056](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_repair_batch_d.py:1056) 调用的 [三账生成函数 :151–180](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_audit_release_gate.py:151)：均为 strict、无 range。未验证 Desktop 上的实际存量案。

4. **同族调用面：PASS。**  
   检索 scripts 同族字段和调用点后，未发现第二处经济控制区间计算。:584–598 的 `check_ledger` 检查账本结构和未决项；`run()` 内部路径在 :1612–1616 先逐账检查，再调用 `check_three_ledgers`。其他生产读取处 [holder_distribution_scan.py:395](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/holder_distribution_scan.py:395)、:686 及 [stage2_closeout.py:858](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/stage2_closeout.py:858) 用于分区来源或文件绑定，没有另一套 strict/expanded 金额口径。

5. **双向一致性：PASS。**  
   已核对 [economic-control-accounting.md:40](/Users/uravvv/.claude/skills/token-chip-analysis/references/economic-control-accounting.md:40)–44、:80、:93，以及 [playbook-entity-cluster-tiering.md:145](/Users/uravvv/.claude/skills/token-chip-analysis/references/playbook-entity-cluster-tiering.md:145)、:150：strict 钱包＋已闭合设施构成下限，expanded 只增加上限。允许上限超过成员金额合计符合疑似设施权益口径；超额部分来源校验仍按工单保留为 P10。

6. **检查点可绕性：PASS。**  
   :907–909 对未映射、跨实体及 excluded 位置行追加错误，虽不 `continue`，后续分流不会消除错误。:920–928 保留 expanded 逐地址闭合；:915 的 `setdefault` 保留纯 expanded 实体的集合键，:989–992 继续检查成员、位置和经济控制实体集合。余额来源绑定 :877–892 原样保留。

**c｜测试与 RED 真实性**

已通过指定 `git show` 读取基线并静态推演；另在内存中执行基线及施工后原函数、十例原断言。文件读写使用内存替身，夹具采用原 `build_case` 中四条余额/三账生成语句；未执行完整 `build_case` 或 `gate.run`。

| 用例 | 基线断言 | 施工后断言 |
|---|---|---|
| 1 默认绿例 | 失败：100 != 300 | 通过，`errors == []` |
| 2 原反例 | 失败：错误列表为空 | 通过，拒绝 300 != 100 |
| 3 上限 250 | 失败：没有区间诊断 | 通过 |
| 4 下限 90 | 失败：没有区间诊断 | 通过 |
| 5 上限 350 | 失败：100 != 300 | 通过，`errors == []` |
| 6 一元素数组 | 失败：没有形状诊断 | 通过 |
| 7 显式 null | 失败：没有形状诊断 | 通过 |
| 8 expanded 缺字段 | 失败：没有缺字段诊断 | 通过 |
| 9 strict 三种区间状态 | 两个合法分支通过；上限 99 分支失败 | 全部通过 |
| 10 expanded 缺位置 | 通过，既有回归断言 | 通过 |

结果与 [B_red_evidence.txt:13](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/B_red_evidence.txt:13)–27 一致：基线 **9/10 失败**，施工后 **10/10 通过**。第 10 例及第 9 例合法分支属于回归检查，无须改前变红。

[新测试 :557–710](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_audit_release_gate.py:557) 每例独立夹具、逐例捕获断言并汇总，没有短路后续 RED。绿例 1/5 使用空错误断言；第 9 例包含式断言符合 v2 工单。**既有断言全部逐字保留。**

:596–602 的 `chain=None` 只跳过四查 owner 来源检查；生产 :818–825、:877–892 的快照哈希、schema、时点和成员余额绑定仍执行，因此空错误断言对三账单元范围有效。

额外内存核验 **15 项通过**，覆盖哈希漂移、零余额 expanded、strict 显式 null、非法端点、设施加总、纯 expanded 实体及坏位置/集合闭合；该内存执行期间外部 I/O 尝试为 0。

RED 中生产基线、测试文件的 SHA256，以及 B_done 中施工后 SHA256，均与对应提交 blob 一致。证据内容与代码行为一致；历史执行时序仍来自施工记录。

**d｜回归与执行限制**

[B_done.md:148](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/B_done.md:148)–163 分别记录三个测试 `exit_code=0`，尾行已与脚本实际成功分支核对：

```text
PASS: audit_release_gate 净室资产/哈希/CEX受益权/阴性结论/图表封口与负钳零/对抗复核否决/四查WARN拦截/双线阈值/嵌套未决暴露/静置仓全集对账/日级峰值口径闭环十一类契约全过
PASS batch15 frozen consumers: 12/12
BATCH D 全部通过
```

本轮两项指定命令均实际尝试，均 `exit_code=1`：

- `python3 -B scripts/tests/test_audit_release_gate.py`：在 :455 创建首个临时目录时出现 `FileNotFoundError: No usable temporary directory found`，未进入用例验证。
- `python3 -B scripts/tests/test_batch15_three_ledgers_frozen.py`：12 例全部因创建 `/private/tmp/batch15-*` 被拒而出现 `PermissionError`，尾行为 `FAIL batch15 frozen consumers: 12/12`。

这些属于沙箱环境失败，未计作代码缺陷。`test_repair_batch_d.py`、`run_all.py` 和实际 APU 存量案本轮未实跑；内存结果不替代完整回归。

**e｜工单符合度**

- 提交范围仅四个白名单文件：两份代码、`B_done.md`、`B_red_evidence.txt`；合计 **436 行新增、2 行删除**。`references/`、`SKILL.md`、`commands-staging/` 零 diff。
- 从基线按工单 B1/B2 套用后，与生产文件逐字一致，包括注释及空白；受保护片段全部未变。
- 测试仅在原 :554 后、原 :556 前新增 **156 行**；移除新增块后与基线逐字一致。第 9 例先保存错误再统一断言，并打印合法分支，符合逐例 RED 取证要求，可接受。
- 元数据字节数为 **8021 / 930070 / 8798**，与工单一致。
- `git diff --check 0877f71..03507cb -- scripts/` 通过。全四文件检查返回 2，仅提示 `B_done.md:50、:67、:94` 行尾空格；它们是原始 diff 代码块中空上下文行的前缀。该代码块已逐字匹配真实 diff，属于可接受的证据格式。
- 开工、收工工作树状态均为空；未改文件、未联网、未 commit。未读取禁读路径内容，未扩展审查其他施工段。

Codex session ID: 01a0af64-6380-7712-95e6-23623066d20d
Resume in Codex: codex resume 01a0af64-6380-7712-95e6-23623066d20d
