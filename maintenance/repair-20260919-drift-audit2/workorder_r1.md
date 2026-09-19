# 工单 R1：v9.0.1 口径漂移与文档-代码不符 9 条纯文本修复 v2

内容基线：`3942c23`（VERSION 9.0.1；施工 HEAD 可含 maintenance/ 提示词与报告提交，但 §0.1 差异校验须为空）。来源：盲审 R1a（5 条）＋ R1b（6 条）去重后 9 条，Fable 逐条亲核两侧原文属实（`blind_r1a_report.md`、`blind_r1b_report.md`）。本单全部为纯文本修复，零代码改动。v2 吸收 codex 复核 r1（`review_wo1_reply.md`）：D2 锚去前导空格、D3/D4/D5/D6/D7 改用更短替换文本、预算按新文本重算；**所有锚与替换文本均为代码块内整行，不含首尾空白**。

## §0 施工纪律
0.1 开工先确认 `git status --short` 为空并记录施工 HEAD；`git diff --stat 3942c23 HEAD -- SKILL.md references scripts commands-staging VERSION CHANGELOG.md` 须为空，不符即停工汇报。
0.2 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）、`archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`（§1.1 统计字节时 attic.md 只计大小不读内容；守卫脚本自身遍历文档属被测代码既有行为，允许并要求原样运行）。
0.3 **白名单**：`references/independent-audit-protocol.md`、`references/report-template.md`、`references/data-pipeline-evm-recon.md`、`CHANGELOG.md`、`commands-staging/token-analyze-2.md`，以及新建 `maintenance/repair-20260919-drift-audit2/r1_done.md`。
0.4 删除 > 修改 > 新增；每处锚先 `grep -n -F` 核验恰 1 处且行号一致；不符停工；只动指定片段，锚外一字不动。
0.5 不 commit、不 push、不部署 `~/.claude/commands/`（部署由 Fable 做）；不改 `scripts/`、`contract_manifest.json`、`invariant_manifest.json`。

## §1 硬约束
1.1 字节：`SKILL.md` = 8021 不变；references 三组 glob（`references/*.md references/casebook/*.md references/labels/*.md`，含 attic.md 与 *.bak_* 文件）合计 ≤ 930160（基线 930076，`stat -f %z` 逐文件求和；Fable 本机按 v2 七处替换逐字模拟净增 +69 B → 930145，预算留至 +84 B；实测数写入报告）；`commands-staging/*.md` 合计 = 8789（基线 8798，D9 删"第⑤条"净减 9 B）。
1.2 守卫全绿：`python3 scripts/tests/docs_lint.py`、`docs_lint.py --all`、`casebook_lint.py`、`changelog_lint.py`、`test_contract_routes.py`、`test_sixlens_docs.py`、`test_g3_docs_guards.py`、`test_version_consistency.py`，原始输出贴进 r1_done.md。`test_commands_deploy_sync.py` 在本单施工后**预期 FAIL**（token-analyze-2.md 与已部署版不一致，部署由 Fable 做后复验），照跑并贴输出，不算停工条件。
1.3 `git diff --stat` 只含 §0.3 白名单。

## §2 逐条施工（锚均已由 Fable `grep -c -F` 验为恰 1 处）

### D1（R1b D1）钱包自持公式漏排 expanded 成员
`references/independent-audit-protocol.md:162`。锚：`wallet_self_held_raw == Σ position.amount_raw` → `wallet_self_held_raw == Σ strict 成员的 position.amount_raw`。依据 `scripts/report/audit_release_gate.py:918-921`（membership 为 `expanded` 的位置金额累入 `expanded_by_entity`，`wallet_by_entity` 只累其余有效成员）与 `:944-946`（按 `wallet_by_entity` 核 `wallet_self_held_raw`）；同文 `:161` "每个有效成员 Σ amount_raw == as_of_balance_raw" 与代码 `:924-930` 一致，不动。

### D2（R1b D2）state_source 排他句与 facts build 必填输入冲突
`references/report-template.md:203`。锚（整行片段，首字符为反引号）：
```
`facts.json` 唯一拥有 entity_id/label/成员/current_raw/peak_raw；`state_source.json` 只承载它没有的分析时点、实体 type/status、逐址快照余额、vault 与 provenance。
```
→
```
`facts.json` 由 `facts_gate.py build` 生成（人工声明取自 `state_source.facts_inputs`）；`state_source.json` 另承载分析时点、实体 type/status、逐址快照余额、vault 与 provenance。
```
依据 `scripts/report/facts_gate.py:357-371`（build 要求 `state_source.facts_inputs` 对象在场且 `symbol`/`decimals`/`entity_labels` 必填）。

### D3（R1b D3＝R1a D1）exit 3 人工对图回退已被 −2 收口拒
`references/report-template.md:278`。锚：`双源都无该币（Robinhood 链类）exit 3 回退人工对 Dexscreener 图` → `exit 3（ALL_SKIP）须换源重跑，−2 收口只接 PASS/WARN`（ALL_SKIP 指所选第二源全部抽样点 SKIP，不必证明"双源都无该币"，故删该前缀）。依据 `scripts/prices/price_check.py:209-210`（ALL_SKIP 退出 3）与 `scripts/report/stage2_closeout.py:294-296`（verdict 非 PASS/WARN 即 BLOCK）。

### D4（R1b D4＝R1a D2）峰值宏可承载 override 覆盖值
`references/report-template.md:215`。锚（首字符为反引号，尾字符为全角逗号）：
```
`{{e.peak_share}}` 只代表日末序列峰值；日内事件占比禁用宏，
```
→
```
`{{e.peak_share}}` 代表 facts 绑定的峰值，粒度按来源标明；未绑定该峰值的日内事件占比，
```
`:216`（"必须以逐事件重放值手写并标明"单笔/日内"，同时并列日末与日内口径。"）不动，与新 `:215` 连读成句。依据 `scripts/report/facts_gate.py:441`（override `peak_raw` 覆盖锚点）、`:480`（写入 `ent["peak_raw"]`）、`:131-132`（宏直接渲染该值）。

### D5（R1b D5＝R1a Q1）CHANGELOG 9.0.0 同条目"均可选"含实际必填字段
`CHANGELOG.md:117`。锚：`2，均可选）` → `2）`（删除"均可选"消歧；流通量两键可选已由同条目 `:113` 说明）。依据 `scripts/report/stage2_closeout.py:300-303`（`price_file_sha256` 缺失即拒）与同条目 `:112`。改后必过 `changelog_lint.py`。

### D6（R1b D6）"每次 check 都落收据"与格式拒绝分支不符
`references/report-template.md:222`。锚：
```
**每次 check（PASS/FAIL、formal/exploration）都落 `figure2_check_receipt.json` 留痕收据**
```
→
```
**终值对账结果（PASS/FAIL、formal/exploration）均写 `figure2_check_receipt.json` 收据**
```
依据 `scripts/report/figures_from_facts.py:375-382`（政策拒绝、输入缺失、series 顶层非数组三类前置拒绝不写收据）与 `:383-390`（终值对账 PASS/FAIL 均写）。

### D7（R1a D3）预筛脚本默认 1% 高于文档最低线
`references/data-pipeline-evm-recon.md:136`。锚：
```
**今按 1% 预筛会把 0.1%–1% 区间候选不可逆滤掉**
```
→
```
**须显式传 `--pct`＝上述最低枚数/总供应量，勿沿用默认 0.01（1%）**
```
依据 `scripts/evm/peaks_daily.py:89`（`--pct` 默认 0.01，口径为占总供应）、`:97`（阈值＝总供应×pct）、`:121`（按累计流入筛候选）；代码默认值按 `CHANGELOG.md:149` 所记 P2 登记不改。

### D8（R1a D4）"≤500 点"与序列编译行为不符
`references/report-template.md:200`。锚：`（≤500 点，重绘图 1 基线）` → `（重绘图 1 基线）`。依据 `scripts/lib/camp_series_provenance.py:293`（dates 原样）与 `scripts/report/state_from_facts.py:141`、`:172-177`（手填序列须与 producer 转换结果逐点相等，不抽稀）。`references/monitoring-package.md:103` 的监控包采样密度是另一产物的独立要求，不动。

### D9（R1a D5）−2 命令引用不存在的 §3b.3 第⑤条
`commands-staging/token-analyze-2.md:16`。锚：`按 §3b.3 第⑤条自查申报` → `按 §3b.3 自查申报`。依据 `references/split-run.md:168-172`（§3b.3 仅一段正文，无分条）。

## §3 完成报告 `r1_done.md` 必含
①逐条改前→改后 diff；②§1.1 字节实测（三组数）；③§1.2 各守卫原始输出（含 deploy_sync 的预期 FAIL）；④`git diff --stat`；⑤差异/停工点；⑥禁读披露。
