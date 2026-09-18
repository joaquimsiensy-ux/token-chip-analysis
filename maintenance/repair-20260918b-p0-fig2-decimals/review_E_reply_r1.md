# 工单E复核：退回

确认两处登记计数需要修订。“来源／观测”断言已对上生产者写出点。复核基线为 HEAD `499d00d`，完整报告已打印到 stdout。

**E-R1-01：schema 替换数与当前命中总数需要分清。**

工单位置：[workorder_E_version.md:29](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918b-p0-fig2-decimals/workorder_E_version.md:29)，原文：“scripts/manifest/references 共 18 处字面量同步”。

实际执行排除禁读路径的 `grep -rn --exclude-dir=__pycache__ … 'evm-observation-bundle/v2' scripts references`，当前共 **19 处＝scripts 9＋invariant_manifest 6＋contract_manifest 1＋references 3**。

新增的一处由 `grep -n -F 'evm-observation-bundle/v2' scripts/report/audit_release_gate.py` 定位：

```text
1589:    accounting_gate 从 evm-observation-bundle/v2 的 supply.decimals 写出，
```

`9ecc962` 差分确实移除 18 处旧 v1、加入 19 处 v2。因此，**18 是既有字面量替换数，19 是当前全量命中数**。

修订建议：写明“18 处既有 v1 字面量同步为 v2，另新增 1 处来源说明；当前共 19 处”，同步订正验收计数口径。

**E-R1-02：G2 盲审未整跑数量少计 1 项。**

工单位置：[workorder_E_version.md:30](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918b-p0-fig2-decimals/workorder_E_version.md:30)，原文：“codex 沙箱因临时目录/socket 权限未整跑 17 项”。

`grep -n -F '17 个入口' maintenance/repair-20260918b-p0-fig2-decimals/blind_G2_reply_r1.md` 命中第 14 行，原文摘录：

> 全部 21 个测试入口均已尝试。`invariant_scan`、`docs_lint --all`、`test_commands_deploy_sync` 完整通过；17 个入口因临时目录权限未完成，纵切片因 `socket.bind EPERM` 未完成。

实际未整跑为 **18 项＝17 项临时目录受限＋1 项 socket 受限**。

修订建议：改为“盲审 18 项未整跑（17 项临时目录权限、1 项纵切片 socket 权限）”，保留本机补验说明。

**其余实际核验结果：**

- **锚点与版本**：指定锚经 `grep -n -F` 各恰命中一次，位于 CHANGELOG:13、:95。VERSION、pyproject.toml:15、SKILL.md:23 均为 7.2.1；改为 8.0.0 等长，SKILL 字节不变。
- **提交范围**：G1 总计 7 文件，其中功能范围为 2 生产＋2 测试，另有 3 份 maintenance 材料；G2 总计 21 文件，其中功能范围为 6 生产＋8 测试＋2 清单＋3 文档，另有 2 份 maintenance 材料。生产文件合计 8；两份 manifest 仅替换 schema。
- **来源链**：`evm_observation.py:27` 定义 selector，第 180 行发起冻结块第 4 笔 eth_call，第 234 行写 `supply.decimals`；`accounting_gate.py:466` 验 bundle，第 479 行写 `checks.decimals`；`shared_release_receipt.py:1776` 核两者相等；`audit_release_gate.py:1593` 起读取 checks，第 1610 行核 config 与观测相等。7.2.1 基线确实没有 decimals 调用，旧闸确实读取 config 自报值。
- **函数与行为**：所列符号及 `_g1_case_1..4` 均存在。G1 必画前缀、去重、集合差、closeout 复用及发布期重算与文案一致；非必画空序列绿例保留。四类指定错误文案均找到对应源码。transcript 恰 9 笔且方法序一致；uint8 校验及旧 v1 拒收成立。
- **字节**：仅用 stat 元数据统计，references **930076 B**、SKILL **8021 B**、commands-staging **8798 B**。结合基线记录与差分，references 恰增 15 B，仅来自 `data-pipeline-evm-recon.md`；另外两册仅等长替换 schema。
- **轮次与台账**：G1 两轮为退回／通过，首轮 3 条；G2 四轮为退回／退回／退回／通过，退回数依次 7／3／1。两份盲审 r1 首行均 PASS。Q1–Q8 齐全，Q1/Q2/Q5/Q6、用户裁决及反例复现描述均与记录一致。
- **迁移与版本依据**：supply_truth producer 哈希失效、wrapper 子项引用刷新、shared receipt 自身 producer 与输入绑定重建，三类分述均与指定代码位置一致。v1→v2 不兼容符合 CHANGELOG 主版本规则及 8.0.0 裁决。
- **体例与校验**：日期、破折号、粗体小节、成本-质量指标与既有条目一致。当前 `test_version_consistency` 实跑 PASS；四文件变更的内存预演也通过原测试函数。活跃条目 **77→78**，无撞号、倒排；新增粗体配对及 SKILL 字节上限通过。
- **完整性与红线**：G1 closeout 复用、非标 ERC20 目标行为、Solana 相等性另单均已登记；未发现其他应登记事项遗漏或新增代币分析结论。

完整 `changelog_lint`、`docs_lint --all` 会读取禁区，本轮未运行；仅完成允许范围内的源码核对和内存预演，未将其表述为全量 lint PASS。未重跑 G1/G2 验收。

全程离线，未读取 `~/.codex/`、memories 或列明禁区内容，未修改文件、未 commit；结束时工作树干净。
