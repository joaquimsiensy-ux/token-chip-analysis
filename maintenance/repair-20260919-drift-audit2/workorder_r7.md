# 工单 R7：v9.0.1 口径漂移与文档-代码不符 3 条纯文本修复 v1

内容基线：`fc704de`（R6 施工落地后的内容态；施工 HEAD 可含 maintenance/ 提交，但 §0.1 差异校验须为空）。来源：盲审 R7a 2 条 minor（`blind_r7a_report.md`）＋ R7b 1 条 nit（`blind_r7b_report.md`），Fable 逐条亲核两侧原文属实。本单全部为纯文本修复，零代码改动；**所有锚均为目标文件整行原文，按代码块内整行字面处理**。

## §0 施工纪律
0.1 开工先确认 `git status --short` 为空并记录施工 HEAD；`git diff --stat fc704de HEAD -- SKILL.md references scripts commands-staging VERSION CHANGELOG.md` 须为空，不符即停工汇报。
0.2 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）、`archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`（§1.1 统计字节时 attic.md 只计大小不读内容；守卫脚本自身遍历文档属被测代码既有行为，允许并要求原样运行）；`maintenance/` 下只读本工程目录。
0.3 **白名单**：`references/monitoring-package.md`、`references/data-pipeline-solana-capture.md`、`references/data-pipeline-solana-scan.md`，以及新建 `maintenance/repair-20260919-drift-audit2/r7_done.md`。
0.4 删除 > 修改 > 新增；每处锚必须是目标文件整行原文，以 `grep -n -F -x` 核验恰 1 处且行号一致；不符停工；按整行替换，其他行不动。
0.5 不 commit、不 push、不部署；不改 `scripts/`、`commands-staging/`、`CHANGELOG.md`、两份 manifest。

## §1 硬约束
1.1 字节：`SKILL.md` = 8021、`commands-staging/*.md` 合计 = 8789 不变；references 三组 glob（`references/*.md references/casebook/*.md references/labels/*.md`）合计 ≤ 929539（基线 929528；三处整行替换按 UTF-8 字面模拟净增 11 B → 929539：D1 +48、D2 -30、D3 -7；实测数写入报告，须等于该值。D1 为准确性必要的最小增量：不加则宏化报告补嵌后数字原样输出且零 WARN，无条件加 `--facts` 又会让无 facts.json 的老案报文件不存在）。
1.2 守卫全绿：`python3 scripts/tests/docs_lint.py`、`docs_lint.py --all`、`casebook_lint.py`、`changelog_lint.py`、`test_contract_routes.py`、`test_sixlens_docs.py`、`test_g3_docs_guards.py`、`test_version_consistency.py`、`test_commands_deploy_sync.py`，原始输出贴进 r7_done.md。
1.3 `git diff --stat` 只含 §0.3 白名单。

## §2 逐条施工（锚均为整行，已由 Fable 逐行匹配验为恰 1 处；行号以 `fc704de` 内容态为准）

### D1（R7a D1）监控包默认重编译命令未传 facts，写宏的报告补嵌后宏原样输出
`references/monitoring-package.md:117`。锚（整行）：
```
3. 默认重跑 `build_html.py --mode legacy-recompile --degrade-reason "买入后补嵌监控 JSON，未改分析结论" --md 报告.md --out 报告.html --json appendix.json`——这是合法重编译但带显式水印。若要维持正式身份，必须把 `appendix.json` 加入 `a4_gate.py finalize --seal-files ...` 重新封口，再按原工作流用 `build_html.py --mode analysis-new|analysis-audit ... --a4-seal a4_seal.json --json appendix.json` 走完整门禁；未进入 seal 的 JSON 一律 BLOCK，不存在 skip 开关。
```
→（仅在 `--json appendix.json\`` 之后插入括注，其余逐字不动）
```
3. 默认重跑 `build_html.py --mode legacy-recompile --degrade-reason "买入后补嵌监控 JSON，未改分析结论" --md 报告.md --out 报告.html --json appendix.json`（写宏的报告须加 `--facts facts.json`）——这是合法重编译但带显式水印。若要维持正式身份，必须把 `appendix.json` 加入 `a4_gate.py finalize --seal-files ...` 重新封口，再按原工作流用 `build_html.py --mode analysis-new|analysis-audit ... --a4-seal a4_seal.json --json appendix.json` 走完整门禁；未进入 seal 的 JSON 一律 BLOCK，不存在 skip 开关。
```
依据 `scripts/report/build_html.py:267`（`--facts` 可选参数，"不给则旧行为不变"）、`:305-306`（legacy-recompile 只拒 `--a4-seal/--a5-seal`，不拒 `--facts`）、`:419-424`（仅 `if a.facts:` 才渲染宏）、`scripts/report/facts_gate.py:557-561`（`state_path` 可为 None）；`references/report-template.md:214`（报告 md 实体数字一律写宏）。措辞"写宏的报告须加"而非无条件加：老案（如 QUQ）报告无 facts.json。

### D2（R7a D2）SQD 专属端点已定论不存在，仍列为未撤销待办
`references/data-pipeline-solana-capture.md:178`。锚（整行）：
```
**遗留后续项**：①~~v2 整合 HyperSync 第二引擎~~ ②~~完备性验收~~（均 3.18.0 完成，验收不通过→禁用待 GA 重验）③Helius key 运行时检测（见 §13c）④SQD key 专属端点补录 ⑤实时 mint 档案（方案 4,用户暂缓）。
```
→（删去"④SQD key 专属端点补录 "并把⑤改编号为④，其余逐字不动）
```
**遗留后续项**：①~~v2 整合 HyperSync 第二引擎~~ ②~~完备性验收~~（均 3.18.0 完成，验收不通过→禁用待 GA 重验）③Helius key 运行时检测（见 §13c）④实时 mint 档案（方案 4,用户暂缓）。
```
依据同文件 `:110`（公共 datasets 不认证、"不存在专属端点 URL，无需再等用户抄回"，2026-07-21 定论 07-25 复核确认）。

### D3（R7b D1）小节标题"三个坑"而正文列九项
`references/data-pipeline-solana-scan.md:119`。锚（整行）：
```
### 3a. 流水追踪的三个 Solana 特有坑
```
→
```
### 3a. 流水追踪的Solana 特有坑
```
依据同文件 `:121-129` 编号 1–9 共九项（`### 3a.` 到 `### 3b.` 之间正则 `^\d+\. ` 计数 9）。

## §3 完成报告 `r7_done.md` 必含
①逐条改前→改后 diff；②§1.1 字节实测（三组数）；③§1.2 各守卫原始输出；④`git diff --stat`；⑤差异/停工点；⑥禁读披露。
