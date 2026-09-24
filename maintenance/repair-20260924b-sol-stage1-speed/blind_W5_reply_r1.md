# W5盲审：PASS

审查基线：`ef20dd825a0f3698bee79b6adfae59befcf6285d`  
审查 HEAD：`64f4d1a676cbdeed880dd75cdb138bc72b9da990`

未发现阻断问题。收官 review 的 **P2、P3 均已在本次文档修正范围内关闭**。

**a）变更范围与逐字一致性：通过**

独立从 `workorder_W5.md` v3 §2 提取六组旧／新片段，在内存中对基线执行替换，再与 HEAD 整个文件逐字节比较，四文件全部一致。因此，六处新片段与工单逐字一致，同行其他文字及文件其他部分未变。

| 文件 | 变更行数 |
|---|---:|
| `references/split-run.md:41` | +1/−1 |
| `commands-staging/token-analyze-1.md:12` | +1/−1 |
| `assets/sqd-solana-coverage-map/README.md:5` | +1/−1 |
| `CHANGELOG.md:108–110` | +3/−3 |

限定范围仅上述四文件变化；`scripts/`、`SKILL.md`、`VERSION`、`pyproject.toml` 无变化，版本保持 `9.2.0`。`git diff --check` 通过。

**b）采纳纪律与真实退出码契约：通过**

[源码返回分支](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_coverage_probe.py:1689)与 [W2 §2.1](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260924b-sol-stage1-speed/workorder_W2.md:66)一致：扫描故障优先返回 1，否则有 chosen 返回 0，无 chosen 返回 2。

本轮还调用真实 `main()`，仅在内存中固定时间至旧资产有效期内，独立验证：

| 场景 | 实际结果 |
|---|---|
| 有合格地图 | exit 0，chosen 非空 |
| 有合格地图，追加 `--search-dir VERSION` | exit 1，chosen 仍非空 |
| 请求区间与地图不重叠 | exit 2，合法 JSON，chosen=null |
| 不重叠且追加上述扫描故障 | exit 1，chosen=null |
| 参数区间非法 | exit 2，无结果 JSON |

三处新文案均正确区分以上情况，堵住了“看到 chosen 就采用”和“看到 exit 2 就全扫”两种误用。

**c）CHANGELOG 事实归并：通过**

- **登记状态**：`WR-b_acceptance.md`、`WR-b_formal_entry.md` 支持新 probe 两协议登记及旧哈希保留。本轮另独立解析注册表，确认 `d4adc0c8…`、`c4980c98…` 各两条均为 ACTIVE；当前 probe 源码 SHA-256 与新登记一致。
- **验收状态**：`W2_acceptance.md` 支持两项 lint PASS；`WR-b_acceptance.md` 追记支持 run_all **150/151**、唯一 reseal 环境项及登记守卫 0 FAIL。WR-a、WR-b 正式入口报告均已有 PASS。
- **收官 review**：`review_final_reply_r1.md` 已有 PASS、P0/P1 为空；本次独立审查支持其 P2/P3 已修正。未将 W5 尚待追记的 run_all 写成新增 PASS。
- **W3 对照**：采用 `fable_probes_20260924.md` **P5** 的 `4,516,539→736,729 B`、gzip、规范化摘要相同，未混用 P1 数值。
- **W4 对照**：与 **P3** 准确一致——header 三方全等；transactions 仅比较 combined 与 census-only；instructions 仅比较 combined 与 probe-only。
- **“完整生产链路吞吐收益未证明”原文保留**，未把内容对照或单 slot 压缩结果扩大为完整吞吐收益。

**d）字节预算、粗体和链接：通过**

| 文件 | 基线字节 | HEAD 字节 | 净增／上限 |
|---|---:|---:|---:|
| references | 28,064 | 28,223 | +159／260 |
| commands | 2,382 | 2,477 | +95／140 |
| 资产 README | 6,601 | 6,723 | +122／160 |

六条变更行的粗体标记配对正确；其中七个 Markdown 链接目标均存在，包括两条新增正式入口报告链接。

**e）P2/P3 关闭判断**

- **P2 已关闭**：三处执行文档现在明确要求按退出码采纳结果，异常分支与源码及 W2 工单一致。
- **P3 已关闭**：过时的待登记、待验收、未记录表述已由有据可查的结果替换，并保留未通过项及收益边界。

**验证边界与纪律**

本轮独立完成差异重建、字节计算、源码契约核对、五组真实入口验证、登记与源码哈希核对、变更行格式及链接检查。未重跑完整回归、lint、正式产物生成或线上请求；历史验收结果属于记录交叉核查，未独立复验 reseal 环境归因或本机 commands 部署。

全程离线，无文件新增或修改、无 commit；结束时工作树干净，HEAD 未变。首次 heredoc 调用因沙箱禁止临时文件而未执行，随后改用 `python3 -B -c` 完成内存验证。未读取用户列明的禁区。