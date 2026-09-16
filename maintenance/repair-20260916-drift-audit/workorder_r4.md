# 工单 R4：口径漂移与文档-代码不符修复（盲审 R4 消化）v1

内容基线：`388eed618c2426e476da30516f508dfe6fe9e782`（VERSION 7.1.1；R1/R2/R3 施工已落地）。来源：`blind_r4_report.md` 4 条（Fable 逐条亲核属实）。只改文本；`scripts/solana/decode_txs_v2.py:8` 文头注释同错已记入 `code_change_pending.md` 待用户决策，本单不动。

## §0 施工纪律（同工单 R3 §0；白名单与差异如下）
0.1 `git status --short` 为空；`git diff --stat 388eed6 HEAD -- SKILL.md references scripts commands-staging VERSION` 为空；不符停工。
0.2 禁读 `~/.codex/`、`archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`（只约束主动读取；运行 §1.2 守卫脚本属被测代码既有行为，允许并要求原样运行）。
0.3 **白名单**：`references/casebook/supply-accounting.md`、`references/analyze-workflow.md`、`references/data-pipeline-evm-channels.md`、`references/data-pipeline-solana-capture.md`，以及新建 `maintenance/repair-20260916-drift-audit/r4_done.md`。
0.4 删除 > 修改 > 新增；锚先 `grep -n -F` 核验恰 1 处且行号一致；不符停工；只动指定片段。
0.5 不 commit；不改 `scripts/`、不改 `contract_manifest.json`；撞 needle 停工汇报。

## §1 硬约束
1.1 字节：`SKILL.md` = 8021、`commands-staging/*.md` = 8798 不变；references 三组 glob 合计 ≤ 929969（基线 929905；四处逐字计算净增 +24/+18/+24/−2 = 64 B，实测数写入报告）。
1.2 守卫全绿（`docs_lint.py` 与 `--all`、`casebook_lint.py`、`changelog_lint.py`、`test_contract_routes.py`、`test_sixlens_docs.py`、`test_g3_docs_guards.py`、`test_version_consistency.py`），输出贴进 r4_done.md。
1.3 `git diff --stat` 只含白名单。

## §2 逐条施工

### D1 S-10 要求"图例条数＝传入阵营数"，与图一豁免键冲突
`references/casebook/supply-accounting.md:82`。锚：`出图后机械比较“图例条数＝传入阵营数”。` → `出图后核对 `fig1_legend_receipt.json`：实绘＋豁免键＝传入阵营键。`（依据 `scripts/report/standard_charts.py:178-192` `select_fig1_series` 返回实绘/豁免/拒绝三集合，豁免键由 `camp_series_provenance.py:75-84` 按 series_format 派生；report-template 第 15 条）

### D2 A6 固定"次版本＋1"，与版本号两维约定冲突
`references/analyze-workflow.md:198`。锚：`写入对应文件＋CHANGELOG 次版本＋1` → `写入对应文件＋CHANGELOG（版本号见 retrospective）`（依据 `references/retrospective.md:139` 与 `CHANGELOG.md:4`：主/次/修按变更性质分级）

### D3 dataseed 坑表"历史状态一律被拒"与 §3.6 浅窗口可查冲突
`references/data-pipeline-evm-channels.md:245`。锚：`getLogs 与历史状态一律被拒` → `getLogs 被拒；历史 state 仅浅窗口可查（§3.6）`（依据同文 §3.6 第 227 行"eth_call 历史 state 窗口 ~128 块"与 `scripts/evm/accounting_gate.py:307-310` 非 archive 收缩 64 块）

### D4 sig 缓存分片数写成固定 256
`references/data-pipeline-solana-capture.md:169`。锚：`按 sig 前 2 字符 256 片` → `按 sig 前 2 字符分片`（依据 `scripts/solana/decode_txs_v2.py:75` 文件名直接取 sig 前 2 字符，Base58 字母表下分片数非 256）

## §3 完成报告 `r4_done.md` 必含
①逐条改前→改后 diff；②§1.1 字节实测；③§1.2 原始输出；④`git diff --stat`；⑤差异/停工点；⑥禁读披露。
