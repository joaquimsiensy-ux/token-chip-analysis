# 工单 R6：口径漂移与文档-代码不符修复（盲审 R6 消化）v1

内容基线：`03e7c65b3963979586a1b2dcd80680c91a0f5672`（VERSION 7.1.1；R1–R5 施工已落地）。来源：`blind_r6_report.md` 1 条（Fable 亲核属实）。只改文本；无新增需改代码项。

## §0 施工纪律（同工单 R5 §0；白名单与差异如下）
0.1 `git status --short` 为空；`git diff --stat 03e7c65 HEAD -- SKILL.md references scripts commands-staging VERSION` 为空；不符停工。
0.2 禁读 `~/.codex/`、`archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`（只约束主动读取；运行 §1.2 守卫脚本属被测代码既有行为，允许并要求原样运行）。
0.3 **白名单**：`references/playbook-entity-cluster-methods.md`，以及新建 `maintenance/repair-20260916-drift-audit/r6_done.md`。
0.4 删除 > 修改 > 新增；锚先 `grep -n -F` 核验恰 1 处且行号一致；不符停工；只动指定片段。
0.5 不 commit；不改 `scripts/`、不改 `contract_manifest.json`；撞 needle 停工汇报。

## §1 硬约束
1.1 字节：`SKILL.md` = 8021、`commands-staging/*.md` = 8798 不变；references 三组 glob 合计 ≤ 929833（基线 929888；一处逐字计算净减 -55 B，实测数写入报告）。
1.2 守卫全绿（`docs_lint.py` 与 `--all`、`casebook_lint.py`、`changelog_lint.py`、`test_contract_routes.py`、`test_sixlens_docs.py`、`test_g3_docs_guards.py`、`test_version_consistency.py`），输出贴进 r6_done.md。
1.3 `git diff --stat` 只含白名单。

## §2 逐条施工

### D1 公共 CEX 热钱包同源边"仅当同 48h 窗＋行为指纹一致才升中等"的例外，与同文第 117 行"不可作共同资金来源证据"、第 247 行"funder 未证私人不得作合并边"冲突
`references/playbook-entity-cluster-methods.md:155`。锚：`默认剔除，仅当"同 48h 窗 + 行为指纹一致"才升中等。` → `一律剔除。`（删除例外：同窗批次注资已在同句单列为中等证据、行为指纹按各自规则独立计，公共来源不再借道成边；与 :117、:247 一致）

## §3 完成报告 `r6_done.md` 必含
①改前→改后 diff；②§1.1 字节实测；③§1.2 原始输出；④`git diff --stat`；⑤差异/停工点；⑥禁读披露。
