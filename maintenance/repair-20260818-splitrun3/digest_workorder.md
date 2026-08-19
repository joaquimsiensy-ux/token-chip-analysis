# 消化批工单｜盲审 finding 修复（v6.50.0 工程）

> 执行者：codex（workspace-write）。工作目录：`/Users/uravvv/.claude/worktrees/tca-splitrun3`。
> 来源：codex 正常盲审 CONDITIONAL 三 finding（F-01 高/F-02 中/F-03 中）＋opus 攻击型验收结果（见附录，若有 BREACH/WEAK 由裁判补录）。只改点名项，白名单外不动。**不 commit**。

## 白名单

1. `scripts/tests/contract_manifest.json`（仅 CT-SEMANTIC-61/62 两条的 needle 值）
2. `scripts/tests/test_repair_batch3_gates.py`（新增"删执行步骤留描述"负例）
3. `references/report-template.md`（顶部物化顺序段）
4. `references/split-run.md`（:3 "两段开工序"残留＋§3b.1 旧案边界句）
5. `commands-staging/token-analyze-3.md`（第 2 步旧案分流半句）
6. ＋opus 报告点名的文件（裁判补录后生效）

## F-01（高）｜契约锚到真实执行步骤

**T1** `contract_manifest.json`：
- CT-SEMANTIC-61 needle 由 `a5-report-seal/v3` 改为 `a5_report_seal.py 产 \`a5-report-seal/v3\``（token-analyze-3.md 执行序第 4 步内的唯一完整锚句，frontmatter 不含）
- CT-SEMANTIC-62 needle 由 `G11` 改为 `build_html --mode analysis-new 过 G10/G11`（同第 4 步锚句，收工句不含）
- id 不变（snapshot 零改动）；(authority,needle) 对唯一性保持
- 改完先验证锚句在 staging 与（模拟）deployed 侧唯一存在：`rg -c -F "a5_report_seal.py 产" commands-staging/token-analyze-3.md` 应为 1

**T2** `test_repair_batch3_gates.py` 新增第五类负例：token-analyze-3.md 删除执行序第 4 步整行但保留 frontmatter description 与收工句——语义层校验必须 FAIL（此负例直接复现盲审 F-01 绕过反例）。实跑红取证。

## F-02（中）｜report-template 顶部物化顺序与新边界统一

**T3** `references/report-template.md` :8-10 段：保留"A4 finalize 前不得创建报告 Markdown、报告图片或 HTML"硬序（该硬序仍对），把"进入 A5 后一次生成报告.md＋标准图＋流转图＋seal/HTML"的旧单会话叙述改为两态并列：
- 单会话模式（/token-analyze）：维持原一次性物化顺序不变；
- 分段模式：−2 在 A4/A4.5 收口后亲笔写报告正文（含附录文字）并产装配工单；−3 进入 A5 装配，只物化三图/流转图/seal/HTML（split-run §3b）。
措辞以最小改动为准，不动本文件其他段（27 条契约 needle 全不在此段，但改前 rg 自查）。

**T4** `references/split-run.md` :3 "两段开工序"改"各段开工序"。

## F-03（中）｜旧完成案例的分流指引

**T5** `commands-staging/token-analyze-3.md` 第 2 步（装配工单检查）追加半句：`；若案目录已是旧流程完成态（a5_report_seal.json 或正式 HTML 已在场）而无工单，属历史完成案，−3 不支持迁移——历史重编译走 build_html --mode legacy-recompile（带水印），勿重跑 −2`。
**T6** `references/split-run.md` §3b.1 末追加一句：`旧流程已完成 A5 的历史案例（a5_report_seal.json/正式 HTML 在场而无工单）不属 −3 适用范围：历史重编译走 build_html --mode legacy-recompile；只有未完成 −2 收口的案例才回 −2 补收口。`

## opus 攻击结果消化（裁判已裁决：修 W-02/05/06/07，W-01=F-01 已覆盖，W-03/04 接受在案）

**T2 补充（opus 实施建议 1，先做再写 T2 负例）**：`test_repair_batch3_gates.py` 的 `seed_commands()` 中 token-analyze-3.md 的合成内容（现为单行 `"a5-report-seal/v3 G11\n"`）改造为 frontmatter＋正文执行序两段结构（frontmatter 含 `a5-report-seal/v3` 与 `G11` 字样、正文含 T1 两条新锚句），否则"删执行步骤留描述"负例测不出目标场景。T1 锚句写入 manifest 时与命令文件逐字节一致（含反引号与全角"产"）。

**T7（W-02）｜本次引入的 needle 稀释回收**：`references/split-run.md` §3b.3 第①条中 `charts/final/holder_distribution_current.png` 完整字符串改为不含该串的等义表述（如"终态分布图（charts/final/ 下唯一终版）在正文恰引用一次"）——基线时 CT-DISTRIBUTION-15 的 needle 在本文件唯一，§3b.3 新增第二处导致 §3.2 原句语义反转攻击不再触红；回收后 `rg -c -F "holder_distribution_current.png" references/split-run.md` 应回到 1。

**T8（W-05，高）｜sealed 自查申报回填落地点（三处等深）**：
- `references/split-run.md` §3b.3 增第⑤条：`⑤sealed/ 禁读令遵守自查申报（−2 全程未读 sealed/ 下任何文件；违规读取如实申报）`；
- §3b.2 `stage2_selfcheck` 字段说明由"§3b.3 四条＋刀 1 公告遵守申报"改"§3b.3 五条＋刀 1 公告遵守申报"；
- `commands-staging/token-analyze-2.md` 第 8 步收口句中"§3b.3 收口自查"处保持指针（§3b.3 已含第五条，无需展开）；第 7 步 sealed 禁读令句尾追加半句 `；交付收口时按 §3b.3 第⑤条自查申报`。
- `references/split-run.md` :115（§2.3 三层防线句）中"改挂 A5 交付"更新为"改挂 −2 收口自查（§3b.3 第⑤条）"。

**T9（W-06）｜−3 权威源三源化＋§3b 双向等深**：
- `commands-staging/token-analyze-3.md` :8 权威源句改为：`唯一分段权威源＝references/split-run.md §3b（分段边界与工单契约）；出图与发布纪律另见 analyze-workflow A5、结构措辞见 report-template（两者本册只指针）。硬性要点：`；
- `references/split-run.md` §3b 回填命令步骤 2/3 的权威条文：3b.1 末追加 `−3 开工前置：装配工单在场且可解析（缺件即停，禁自造）；A5 链前置产物五项自检＝a4_seal（a4-seal/v4 PASS）／报告.md sha 与工单一致／distribution_rounds 已终态／终态分布图已物化／facts 与 state 在场——任一缺失或漂移停下报用户，禁带病开工禁补票`；§3b.5 中"−3 自检"改"−3 开工前置自检（3b.1）与交付自查"消除未定义引用。

**T10（W-07）｜修错三分类①限定收窄（两处等深）**：`references/split-run.md` §3b.4 与 `commands-staging/token-analyze-3.md` 第 5 步同句等深修改：①由"图渲染/路径/receipt 类红灯"改为"图渲染失败、路径/receipt **缺件或落位**类红灯"；③追加 `；figure2_check 对账 FAIL、任何与 facts 数值不同源类失败同属本类（禁以"重跑"名义改数据或换选材）`。

**T11（W-03/W-04 接受在案登记）**：`CHANGELOG.md` 6.50.0 条目追加一行：`- **盲审消化**：codex 正常盲审 F-01/02/03＋opus 攻击 7 WEAK 中 5 项修复入盘（契约锚句化＋负例加深、report-template 物化两态、旧完成案分流、sealed 申报回填、三分类收窄、needle 稀释回收、权威源三源化）；W-03（banned 字面变体穿透）与 W-04（契约 needle 值无守卫、快照只锁 ID 集合）属契约体系存量固有形态，接受在案登记为后续升级候选`。（changelog_lint 复跑。）

## 验收命令

```
cd /Users/uravvv/.claude/worktrees/tca-splitrun3
python3 scripts/tests/docs_lint.py --all
python3 scripts/tests/test_contract_routes.py
python3 scripts/tests/test_repair_batch3_gates.py
rg -c -F "a5_report_seal.py 产" commands-staging/token-analyze-3.md
rg -n "两段开工序" references/split-run.md && echo 残留 || echo 清零
python3 scripts/tests/changelog_lint.py
```
外加 F-01 新负例的红取证记录。done 报告 `digest_done.md`。**不 commit。**
