# 消化批施工完成报告

## 施工边界

- 工单：`maintenance/repair-20260818-splitrun3/digest_workorder.md`
- 开工 HEAD：`e1be99ab25c0a6f60091d7a7b635ab6097e532c8`
- 施工方式：仅修改工单白名单及 T8/T11 明确追加点名的文件；未执行 `git commit`。
- 开工时工作树已有多份未提交改动；本轮将其视为既有用户改动，未改动工单点名范围外的文件。

## T1～T11 完成情况

1. **T1**：CT-SEMANTIC-61/62 保持 ID 不变，needle 分别收紧为执行行中的 `a5_report_seal.py 产 \`a5-report-seal/v3\`` 与 `build_html --mode analysis-new 过 G10/G11`；命令文件锚前缀唯一计数为 1。
2. **T2**：先把 `seed_commands()` 的 token-analyze-3 合成内容改为 frontmatter＋正文执行序结构，再新增“双侧删除第 4 步、保留 description 与收工句”的第五类负例；测试夹具 needle 与生产 manifest 逐字节一致。
3. **T3**：report-template 顶部保留 A4 finalize 前禁物化硬序，并改成单会话/分段模式两态并列。
4. **T4**：split-run 顶部“两个开工序”改为“各段开工序”。
5. **T5**：token-analyze-3 第 2 步补入旧流程完成案分流；历史重编译走 `legacy-recompile`，不重跑 −2。
6. **T6**：split-run §3b.1 等深补入旧流程已完成 A5 案例边界。
7. **T7**：split-run §3b.3 回收 `holder_distribution_current.png` 新增重复字面；本文件该 needle 恢复唯一计数 1。
8. **T8**：sealed 禁读自查申报回填到 §2.3、§3b.2、§3b.3 与 token-analyze-2 第 7 步；自查由四条更新为五条。
9. **T9**：token-analyze-3 改为 split-run/analyze-workflow/report-template 三源指针；split-run §3b.1 回填开工五项自检，§3b.5 改为引用开工前置自检与交付自查。
10. **T10**：split-run 与 token-analyze-3 的修错三分类等深收窄；figure2_check 对账失败及 facts 数值不同源失败明确归第③类，禁止借“重跑”改数据或换选材。
11. **T11**：CHANGELOG 6.50.0 追加盲审消化记录，W-03/W-04 作为存量固有形态登记为后续升级候选。

## F-01 新负例红取证

按工单顺序，先完成 `seed_commands()` 合成内容改造，再写第五负例；此时测试夹具仍使用旧宽泛 needle。实跑：

```text
$ python3 scripts/tests/test_repair_batch3_gates.py
rc=1
FAIL  F01 −3 删执行步骤留描述与收工句仍被语义层拒绝  []
FAIL: 1 项批3 gates 回归失败：['F01 −3 删执行步骤留描述与收工句仍被语义层拒绝']
```

负例将 staging/deployed 两侧写成相同字节，删除正文执行序第 4 步，但保留 frontmatter 的 `a5-report-seal/v3`、`G11` 以及收工句。空失败清单 `[]` 证明旧宽泛 needle 未产生语义拒绝，且不是由 SHA 不一致代打红灯。

将生产 manifest 与测试夹具 needle 收紧到执行行完整锚句后，同一负例转绿：

```text
ok    F01 −3 删执行步骤留描述与收工句仍被语义层拒绝
PASS: 批3 deploy-sync/env-check/R10-ledger gates 回归全部通过
```

## 工单验收命令

| 命令 | exit | 输出摘要 |
|---|---:|---|
| `python3 scripts/tests/docs_lint.py --all` | 0 | `PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）` |
| `python3 scripts/tests/test_contract_routes.py` | 0 | `PASS: R-01/R-02 注册表、ID 快照、五组锚与 SKILL 原子阶段双向闭合` |
| `python3 scripts/tests/test_repair_batch3_gates.py` | 0 | F-01 新负例为 `ok`；`PASS: 批3 deploy-sync/env-check/R10-ledger gates 回归全部通过` |
| `rg -c -F "a5_report_seal.py 产" commands-staging/token-analyze-3.md` | 0 | `1` |
| `rg -n "两段开工序" references/split-run.md && echo 残留 || echo 清零` | 0 | `清零` |
| `python3 scripts/tests/changelog_lint.py` | 0 | `PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 39 条 + 归档 139 条` |

补充定向核对：`holder_distribution_current.png` 在 `references/split-run.md` 中计数为 1；本轮目标文件 `git diff --check` 通过。

## 收口

- 所有工单验收命令均通过。
- 未执行 git commit；交付保持未提交工作树状态。
