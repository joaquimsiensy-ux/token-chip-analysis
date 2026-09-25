**结论：需修改后再派。** 根因判断正确，四条判据能补上本次 CLI 漏封，但工单尚未明确误封代价、其他出口的边界和必须通过的集成测试。

本次只读核对了工单、代码、版本历史及公共标签表；未联网、未改文件、未读取案目录。工单中的具体案情数量未独立复验。

1. **根因描述准确，但有两处措辞应修正。**

   [labels_resolver.py:198](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/labels/labels_resolver.py:198) 先对 category 去空白，再于第 216 行推导 `serial = (category == SERIAL_CATEGORY)`；`SERIAL_CATEGORY` 是 `serial-actor`。它不是“所有惯犯相关信息”的总标记。

   [label_lookup.py:146](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/labels/label_lookup.py:146) 第 151 行确实只检查 `row.get('serial')`；第 147–148 行明确要求整行隐藏，防止风险段泄露。JSON 第 174–177 行仍输出风险和来源，根因成立。

   curation 改类别、保留旧风险和来源的机制也成立：[add_labels.py:150](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/labels/add_labels.py:150) 第 151–154 行合并来源及风险，第 155–164 行覆盖分类等字段。

   建议把“整行原样进公共输出”改成“未封存，相关字段继续进入公共输出”——JSON 实际选择字段，文本实际分段展示。另外，**`--unseal` 不依赖 `serial` 定义**；保持定义不变的充分理由是其他决策消费者依赖它，例如 `cluster.py:130` 的惯犯豁免。

2. **四条判据对当前 CLI 的结构化信息足够，但“包含”必须定义清楚。**

   `risk_partition` 由 `risk_flags` 派生（resolver 第 321–327 行），`sections.serial` 由 category 派生（lookup 第 64–65 行），所以不必再增加这两项重复判据。`source` 能兜住只剩来源标记的行。

   但直接做字符串子串判断会扩大范围：例如假设值 `not-serial-offender`、`non-serial-offenders` 也会命中。建议明确采用：

   - `serial`：当前 resolver 产出布尔值；明确是否严格要求 `True`。
   - category：规范化后精确匹配 `SERIAL_CATEGORY`。
   - risk_flags：解析后精确匹配旗标。
   - source：按 `+` 拆分后精确匹配 `serial-offenders` 来源项。

   四条判据不能保证 `name/evidence` 等自由文本绝无历史案信息。因此工单应限定为“封存带上述结构化标记的行”，不能把本单验收写成所有公共输出的全面无泄露保证。

3. **会封存非 `serial-actor` 行，而且设施信息损失已经有实际影响面。**

   只读聚合当前 8 个公共 `labels-*.csv`：共 471,661 行；按工单条件命中 2,959 行，其中 **10 行 category 不是 `serial-actor`，7 行 tier 为 `exclude`**。本次未发现仅因子串边界而额外命中的存量行，但这不能替代边界测试。

   支持整行封存的理由：这些行仍带历史惯犯信息，继续输出会破坏盲化。反对直接整行封存的理由：curation 可能已纠正身份；隐藏后连设施身份、`no_merge`、`exclude` 和其他有效风险都会一起消失。依赖 CLI 输出的下游可能把公共设施当未知地址，造成错误合并或持仓归属。

   **“带历史标记”不等于“当前确为惯犯”。** 建议函数说明改成“是否含须盲化的惯犯层标记”，并在工单明确：是否接受这类混合行暂时失去设施信息。直接使用 resolver 的决策不会因本次 CLI 修改而改变，不能笼统宣称所有聚类都会受影响。

4. **`risk_flags` 在实际库中是字符串；工单的列表支持属于额外兼容。**

   公共表全部为字符串；[risk_flags.py:24](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/labels/risk_flags.py:24) 只接受字符串或 `None`，按 `|` 分隔，列表会抛 `TypeError`。resolver 加载时检查但保留原字符串；风险分区内的各项才是列表。

   工单覆盖了字符串、列表两种正例，但缺少空值、缺字段、多旗标及相似子串反例。应说明：列表支持仅限新辅助函数的输入兼容，**不代表 resolver 或文本输出已支持列表**；文本第 202 行仍调用 `.strip()`。

5. **消费者覆盖不完整；文本模式没有旁路，其他入口有。**

   | 位置及行号 | 核对结果 |
   |---|---|
   | [label_lookup.py:158](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/labels/label_lookup.py:158)，163–179、184–208 | JSON、文本都消费过滤后的 `hits`。工单对此判断正确。 |
   | 同文件 103–121、123 | `--unseal` 在计算盲化状态之前读取并输出封存详情；同时指定盲化参数或保留环境变量也会揭盲。它是显式揭盲入口，应写清优先级及 A4 例外，不能默认受新函数保护。 |
   | [analyze_holdings.py:192](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/evm/analyze_holdings.py:192)，198–203、221–224 | **确定存在同类漏封**：仅 `serial=True` 才跳过；`serial=False + serial-offender` 仍输出风险。 |
   | [replay_edges.py:64](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/replay_edges.py:64)，69–79 | 只按 `serial` 隐藏；其余行直接显示 name/category。不会直接打印风险或来源，但名称仍可能携带历史信息。 |
   | [build_evolution.py:107](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/build_evolution.py:107)，108–121 | exclude 分支先于 serial 分支；设施行的名称、类别可直接输出，不受新函数保护。 |
   | [cluster.py:200](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/evm/cluster.py:200)，200–202、233–242 | 名称、设施标签进入 JSON／文本，没有盲化判断。 |
   | [entity_identity_gate.py:334](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/entity_identity_gate.py:334)，338–340、349–361 | name/category/tier/source 直接写入产物，没有盲化判断；若盲化期调用，可输出惯犯来源。 |

   `LabelResolver.get()`、`policy()`、`resolve_file()` 本身也不盲化：分别见 resolver 第 248–269、300–317、398–409 行，其中 `policy()` 返回完整 `row`。

   在检索的 `scripts` 源码范围内，未发现其他脚本直接 `import label_lookup`；生产消费者主要直接 import resolver。**把函数放在 CLI 内，不会自动覆盖它们。** 工单应明确本单仅修 CLI，并登记其余出口另单处理。

6. **版本方向正确，登记要求应直接列全。**

   `git log -3 -- CHANGELOG.md` 得到 `64f4d1a`、`f78b5c4`、`22654a8`。最新一次只是调整 9.2.0 内容；真正的 9.2.0 升版提交是 `f78b5c4`，同步修改了：

   `VERSION`、`pyproject.toml`、`SKILL.md` 版本注释、`CHANGELOG.md`。

   当前均为 9.2.0，修复升 9.2.1 符合现有规则。[test_version_consistency.py:12](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_version_consistency.py:12) 第 12–23 行还要求 CHANGELOG **顶部索引和首个详情条目**同时一致，不能只加一条中文文字。

   “不改 SKILL 正文”不必然禁止修改版本注释，但应明确允许更新第 23 行版本元数据。历史条目、schema 版本及 producer 历史理由中的旧版本号无需全局替换。

   预提交三检实际为 `.git/hooks/pre-commit:6–8` 的 `changelog_lint`、`docs_lint`、`env_check`；工单应点名，版本一致性另验。

7. **测试与验收目前过弱，应取消“只测纯函数也可交付”。**

   纯函数全绿不能证明 CLI 接线、封存写入和公共输出正确。“`hit=false` **或不出现命中字段**”也过宽，空输出都可能被误当成功。

   建议强制集成测试验证：退出码为 0；单链 JSON 对目标地址返回 `hit:false` 且不带标签字段；封存保留原始信息；普通设施仍命中；文本模式、环境变量模式及非盲化对照符合预期。补 category-only、source-only 和相似子串反例。

   已有 [test_cluster_quality.py:34](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_cluster_quality.py:34) 的最小 CSV 构造，以及第 64–107 行的盲化／揭盲测试可参考，“构造成本过高”没有必要作为降级验收口子。

   [run_all.py:10](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/run_all.py:10) 使用显式 `SUITE`，第 215–219 行逐项执行；应写“加入 SUITE”，不是“进入发现范围”。

8. **另有三处施工边界应补清。**

   - `--chain all`：lookup 第 154–155 行不会把封存行加入 misses，因此工单“该地址进 misses”只适用于单链模式。
   - CLI 第 25 行仍声明“设施类输出不受影响”，与新增混合设施行整行封存不一致；这是主改文件内的说明，应同步限定为“不含惯犯标记的设施行”。
   - 工单既要求临时目录测试，又要求“不删文件”；已有测试使用 `TemporaryDirectory` 自动清理。应明确临时测试产物的创建、读取、清理是否允许，并区分合成测试目录与禁止读取的真实案目录，避免施工方自行解释。
---
【调度方融合记录 2026-09-25】八条全部采纳并写入工单 v2：①措辞改"未封存、相关字段继续进入公共输出"，补 `--unseal` 不依赖 serial、保持定义的理由为 cluster.py:130 等消费者；②判据改精确匹配（category strip 后等于常量；risk_flags 按 `|` 解析；source 按 `+` 拆分），不加 risk_partition/sections；③裁决：混合行整行封存，代价写进 CHANGELOG；④risk_flags 实为字符串，list 仅函数输入兼容，非法类型 fail-closed；⑤本单只修 CLI，其余六处出口登记 README 后续单候选；⑥版本四处点名（VERSION/pyproject/SKILL.md 第 23 行/CHANGELOG 索引+详情），预提交三检点名；⑦集成测试强制，取消降级口，加入 run_all SUITE，补相似子串/空值/缺字段反例；⑧`--chain all` 不加 misses 沿旧、第 25 行注释同步改、临时目录允许自动清理但禁读真实案目录。
