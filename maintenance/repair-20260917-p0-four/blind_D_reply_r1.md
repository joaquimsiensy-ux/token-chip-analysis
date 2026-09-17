# 盲审 D：PASS

按 [workorder_D.md v4](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/workorder_D.md:1) 审查 `f9b3800..f583039`，未发现本段需要修复的 blocker、minor 或 nit。完整落盘测试受只读沙箱限制未重跑；以下区分独立核验与施工记录。

**六项不变量均成立。**

| 项目 | 核验事实与代码位置 |
|---|---|
| ① 递归定位 | [audit_release_gate.py:1077](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/audit_release_gate.py:1077) 使用 rglob，排除隐藏路径、`_history`、符号链接；`.duck_tmp` 属隐藏目录。1104–1113 行实现零份 return、多份拒；伴随文件相对唯一 summary 的父目录解析。 |
| ② needs 哈希 | [audit_release_gate.py:1144](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/audit_release_gate.py:1144) 检查实物存在、非符号链接、summary 登记 SHA 且与实际 SHA 相等；缺登记明确拒收。 |
| ③ 补算覆盖 | 同文件 1151–1175 行从 needs 各档及逐日 active_candidates 重算小写并集；1179–1230 行检查收据、schema、engine、inputs SHA、每址覆盖及 peak/peak_blk。触发日候选非空时额外要求绑定 trigger SHA。正峰值要求非负整数区块，零峰值要求 null。 |
| ④ summary 生产 | [peaks_daily.py:172](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/evm/peaks_daily.py:172) 写 needs 后计算实物 SHA；217–218 行登记文件名和哈希。L1/L2、默认门槛及原格式未变。 |
| ⑤ only-addrs | [replay_duck.py:376](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/evm/replay_duck.py:376) 仅对输入并集建立 ab；窗口 SQL 与基线全量逐字相同，无峰值门槛，无事件地址补 `0/null`，收据写首输入目录。671–677 行坏事件拒收但不写 replay_stats；684–685 行在 pass1/merged/pass2 前退出。 |
| ⑥ 原错误文案 | AST 提取比对确认原六条 errors 文案逐字保留，对应新文件 1119–1142 行。 |

`build_events`、`emit_merged`、`replay_pass2`、`_peaks_python` 原文未变；pass1 仅抽取 deltas，原 SQL 与剩余逻辑一致。发布闸指定修改区域以外，注释和空白也未变。

**六视角结论。**

| 视角 | 结论 |
|---|---|
| 字段来源 | 通过。哈希来自文件字节，并集来自 needs/trigger 实物；summary 候选计数不能覆盖实际并集。发布闸验证收据绑定、覆盖及形状；channels 同源验证仍是 §4 明定的 P13 另单。 |
| 失败分支 | 通过。多份、缺 SHA、SHA 不符、缺收据、少址、错误 schema/engine/inputs 均拒收。单故障根因可断言；独立错误允许累计，并非全局互斥。非法 peak 后立即 continue，不会追加虚假的“零峰值区块应为 null”。 |
| 存量迁移 | 通过。旧 summary 缺 needs SHA 必红是设计意图；零份 summary 直接 return。生产者已有生成合规产物的入口。 |
| 同族调用面 | 通过。搜索允许范围的 scripts/references 后，相关生产及消费点为 peaks_daily、replay_duck、audit_release_gate；测试读取者已同步，另有 test_repair_batch1 的子闸 mock，未见漏改的具名生产消费者。 |
| 双向一致性 | 通过。[recon:132](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-evm-recon.md:132)、[tiering:149](/Users/uravvv/.claude/skills/token-chip-analysis/references/playbook-entity-cluster-tiering.md:149) 的收据义务与代码对应；peaks_daily:64 的哈希说明对应实际输出。两文档仅作指定替换，日期戳保留。 |
| 检查点可绕性 | 通过指定场景。两份 summary 拒收；needs 实物改文件名因固定文件缺失而拒收，改档位键名仍遍历全部 values；旧 needs/trigger SHA 拒收；only-addrs 空并集、坏 JSON、坏候选形状退出 2。 |

**测试真实性已核验，未发现弱化既有断言。**

- RED 证据中的三个生产文件 SHA 均与 `git show f9b3800:<path>` 相符；证据文件自身 SHA 与 D_done 登记一致。D_done 内三份生产 diff 与提交实际 diff 一致。
- 提取原文 `_r09_case_1..13`，以文件内存替身执行峰值子闸：基线 1、3–11、13 为 RED，2、12 为 GREEN→GREEN；改后全部 GREEN。第 13 例基线确为 AttributeError，第 7 例补齐收据后放行。此验证替换了完整 gate.run，不代表完整发布闸测试。
- [followup_case:236](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_engine_equivalence.py:236) 在基线因不识别 only-addrs、收据不存在而失败；没有把 argparse 的退出 2 当作坏输入校验通过。坏事件在生成通道收据前加入，并断言 `bad_fields=1`，能够识别目标拒收分支。
- [test_peaks_daily.py:114](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_peaks_daily.py:114) 比较 needs 实物 SHA；基线没有对应 summary 字段，新增断言确实失败。
- [h 例:960](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_audit_release_gate.py:960) 补合法空 needs 和实算 SHA，保留原 trigger/上界断言，并追加 needs/followup 断言。没有豁免旧 summary；三个测试文件原有 assert 均保留。

本轮另用真实 DuckDB 内存 SQL 验证 HUGEINT、VARINT 和强制 Python 回退：两址分别为 `10^19@102`、`5×10^18@103`，无事件地址为 `0/null`；峰值为 1 的地址仍保留。重复 only-addrs 的并集及输入 SHA 正确。九种空/坏输入均 stderr＋exit 2、未更新收据。

执行原文坏事件分支时，新代码保持指定全量产物不变，旧分支会覆盖 replay_stats。上述文件操作均为内存替身，未执行完整 CLI。

**回归结果与未实跑项。**

[D_done.md:492](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/D_done.md:492) 包含 §0.8 全七项命令、退出码及结果尾行，未以 SKIP 代替 PASS：

| 命令文件 | 施工记录 | 本轮 |
|---|---|---|
| test_audit_release_gate.py | exit 0，十一类契约全过 | 完整测试未跑 |
| test_engine_equivalence.py | exit 0，R09 与三引擎检查 PASS | 完整测试未跑 |
| test_peaks_daily.py | exit 0，0 项失败 | 完整测试未跑 |
| test_batch15_three_ledgers_frozen.py | exit 0，12/12 | 未跑 |
| test_repair_batch_d.py | exit 0，全部通过 | 未跑 |
| test_stage2_closeout.py | exit 0，28/28 | 未跑 |
| invariant_scan.py | exit 0 | **实际执行 PASS** |

前六项需要创建落盘夹具，当前只读沙箱不允许，故未运行；施工记录未当成本轮独立复跑结果。run_all、完整 docs_lint、真实 APU 案均未运行。

本轮 scanner 实际输出：

```text
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0
```

**minimum_counts 判定：可接受的守卫收紧，不算越界。**

保留旧下限仍能通过，r1–r3 的“无需修改”在技术上成立；但 [v4 D5:368](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/workorder_D.md:368) 明写“minimum_counts 按实际”。此次 70→81、92→118、56→61 与实扫一致，没有放宽约束。逐项移除三处新增登记、还原下限后，manifest 与基线完全相同，未整体回填。

审查范围内 diff 恰为九个白名单文件。完整提交另含两份交付件和 `code_change_pending.md` 的两条 §4 调度方收尾登记；后者不在 §0.3 施工白名单，但有 §4 的明确任务依据，不认定为施工越界。SKILL.md、commands-staging 未被 diff 触及。

仅按 stat 核得：**references 930061 B、SKILL.md 8021 B、commands-staging 8798 B**，全部准确。`scripts/ references/` 的 diff --check 退出 0；全提交检查仅提示 D_done 原样 diff 代码块中的空白上下文行，不是生产代码空白改动。

全程离线只读，未改文件、未 commit，工具未读取禁读内容。开工和收尾工作树均为空；HEAD 从 `9a780a8` 并发前移至 `0aa235d`，最终复核的 16 份输入仍逐字节等于 `f583039`。

Codex session ID: 01a0b030-d494-7ea2-829b-4c9267b197f8
Resume in Codex: codex resume 01a0b030-d494-7ea2-829b-4c9267b197f8
