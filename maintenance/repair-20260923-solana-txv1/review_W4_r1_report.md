[2026-09-23T08:34:56.738Z] Assistant message
# 复核 W4 v1: 退回

**第 2、3 处替换仍然承诺过宽；第 1、4 处成立，四个锚点和行号均准确。** 这是文档措辞问题，不是新增代码缺陷。

1. **P2 第一条“不采纳”：结论成立，理由应收窄。**

   [CHANGELOG.md:7](/Users/uravvv/.claude/tca-fix-txv1/CHANGELOG.md:7) 明确要求每条迭代附成本与质量指标；[CHANGELOG.md:107](/Users/uravvv/.claude/tca-fix-txv1/CHANGELOG.md:107) 的轮数、复核结果、调用成本、用时登记符合这一要求。因此，review §4 建议整行移出的处理不合适。

   但“规则要求登记”不能推出“不是施工叙述”。[工单:3](/Users/uravvv/.claude/tca-fix-txv1/maintenance/repair-20260923-solana-txv1/workorder_W4_v1.md:3) 可直接缩为：**“该行符合 CHANGELOG 头部成本与质量指标登记要求，保留。”** 本项只确认保留依据，不核验指标数值。

2. **四处新措辞：两处通过，两处需改。**

   - **第 1 处通过。** “未含认领记录”准确对应来源 header 不得存在 `adopted`；“历史 producer”消除了版本必须相邻的误解。代码排除当前 producer，再遍历登记历史哈希重算摘要，没有版本相邻判断。证据：[sqd_gap_repair.py:837](/Users/uravvv/.claude/tca-fix-txv1/scripts/solana/sqd_gap_repair.py:837)、[sqd_gap_repair.py:842](/Users/uravvv/.claude/tca-fix-txv1/scripts/solana/sqd_gap_repair.py:842)。ACTIVE 集合还按脚本、协议过滤，并由 REVOKED 优先排除：[producer_history.py:278](/Users/uravvv/.claude/tca-fix-txv1/scripts/lib/producer_history.py:278)。工单括注的“只要求”应理解为针对版本关系的解释，不能当作完整准入条件。
   - **第 2、3 处退回。** 加上“已发布清单不变”解决了同步修改清单的边界，但“任何一侧的后续改写”仍过宽。深验仅遍历清单路径，核对对应文件的大小与哈希，不读取来源 pending 的证据路径：[solana_exact_validate.py:1422](/Users/uravvv/.claude/tca-fix-txv1/scripts/lib/solana_exact_validate.py:1422)、[solana_exact_validate.py:898](/Users/uravvv/.claude/tca-fix-txv1/scripts/lib/solana_exact_validate.py:898)。**反例：只在来源端原子替换证据文件，目标文件和清单均不变，目标深验不会发现来源变化。** 两处原文末尾还明确允许原子替换。因此保证应限定到清单所列证据，或仍共享 inode 时的原地内容改写。
   - **第 4 处通过。** 来源解析只忽略末尾无换行的字节，不改来源；当前 pending 恢复调用清理函数，将完整行重新序列化后写回。证据：[sqd_gap_repair.py:689](/Users/uravvv/.claude/tca-fix-txv1/scripts/solana/sqd_gap_repair.py:689)、[sqd_gap_repair.py:707](/Users/uravvv/.claude/tca-fix-txv1/scripts/solana/sqd_gap_repair.py:707)、[sqd_gap_repair.py:733](/Users/uravvv/.claude/tca-fix-txv1/scripts/solana/sqd_gap_repair.py:733)、[sqd_gap_repair.py:834](/Users/uravvv/.claude/tca-fix-txv1/scripts/solana/sqd_gap_repair.py:834)。完整但非法的 JSON 行会报错，不属于被忽略的残尾。

3. **锚文本与行号：全部通过。**

   | 替换 | 实际位置 | 锚文本出现次数 |
   |---|---|---:|
   | 1 | [CHANGELOG.md:104](/Users/uravvv/.claude/tca-fix-txv1/CHANGELOG.md:104) | 1 |
   | 2 | [CHANGELOG.md:105](/Users/uravvv/.claude/tca-fix-txv1/CHANGELOG.md:105) | 1 |
   | 3 | [references/scan-schemas.md:1029](/Users/uravvv/.claude/tca-fix-txv1/references/scan-schemas.md:1029) | 1 |
   | 4 | [references/scan-schemas.md:1031](/Users/uravvv/.claude/tca-fix-txv1/references/scan-schemas.md:1031) | 1 |

   次数按各自目标文件统计；第 4 处为整行匹配，其余为行内片段匹配。

4. **有更短的改法，仍只替换现有四行。**

   - 第 1 处可用：`ACTIVE 已登记且 header 无 adopted 的历史 producer pending`。
   - 第 2、3 处将现有从“发布后 evidence_manifest”到“但不能隔离它”的整段统一替换为：  
     **`发布后 evidence_manifest 深验核对所列证据的大小与哈希，但不能隔离共享 inode 的原地改写`**。这直接描述实际校验范围，无须追加条件句。
   - 第 4 处可缩为：  
     **`- 残缺尾行：当前 pending 普通恢复时截除；来源 pending 仅解析时忽略，字节不变。`**

全程离线，未读取禁读目录，未修改文件或 commit；分支为 `fix/solana-txv1`，结束时工作区干净。本次结论基于文本与源码核对。
