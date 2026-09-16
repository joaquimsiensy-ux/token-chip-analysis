# 工单 R3：口径漂移与文档-代码不符修复（盲审 R3 消化）v2

v2 变更（消化 `review_wo3_reply.md`）：D1 替换文本缩短；§1.1 预算改为逐字实算值。

内容基线：`66f45e4c6cc05be2d80278d81589b1ddb304b745`（VERSION 7.1.1；R1/R2 施工已落地）。来源：`blind_r3_report.md` 2 条＋待确认转正 F3（Fable 逐条亲核属实）。只改文本；无新增需改代码项。

## §0 施工纪律（同工单 R2 §0；白名单与差异如下）
0.1 `git status --short` 为空；`git diff --stat 66f45e4 HEAD -- SKILL.md references scripts commands-staging VERSION` 为空；不符停工。
0.2 禁读 `~/.codex/`、`archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`（只约束主动读取；运行 §1.2 守卫脚本属被测代码既有行为，允许并要求原样运行）。
0.3 **白名单**：`references/environment.md`、`references/scan-schemas.md`、`references/data-pipeline-solana-scan.md`，以及新建 `maintenance/repair-20260916-drift-audit/r3_done.md`。
0.4 删除 > 修改 > 新增；锚先 `grep -n -F` 核验恰 1 处且行号一致；不符停工；只动指定片段。
0.5 不 commit；不改 `scripts/`、不改 `contract_manifest.json`；撞 needle 停工汇报。

## §1 硬约束
1.1 字节：`SKILL.md` = 8021、`commands-staging/*.md` = 8798 不变；references 三组 glob 合计 ≤ 929905（基线 929831；本轮三处均为补正代码事实、无可删冗余，逐字计算净增 74 B，实测数写入报告）。
1.2 守卫全绿（`docs_lint.py` 与 `--all`、`casebook_lint.py`、`changelog_lint.py`、`test_contract_routes.py`、`test_sixlens_docs.py`、`test_g3_docs_guards.py`、`test_version_consistency.py`），输出贴进 r3_done.md。
1.3 `git diff --stat` 只含白名单。

## §2 逐条施工

### D1 Helius key 来源写成单文件，实际默认先读 key 池
`references/environment.md:18`。锚：`只从 `~/.config/helius/api-key` 读取` → `默认读 `~/.config/helius/api-keys`（key 池），空则回退 `~/.config/helius/api-key``（依据 `scripts/solana/sqd_gap_repair.py:46-47,122-133`）

### D2 slot-index-map 不变量误要求 signature 列单调递增
`references/scan-schemas.md:873`。锚：`三列各自唯一双射且单调递增。` → `三列各自唯一；行按 `sqd_index` 递增。`（依据生产者 `sqd_gap_repair.py:1094-1112` 按 index 排序、消费者 `solana_exact_validate.py:1558-1560` 查各列唯一与首列有序并按证据重算 ordinal 核对映射）

### F3 质押账本"精确对表"实为容差 2 raw（待确认转正）
`references/data-pipeline-solana-scan.md:100`。锚：`账本净额合计 vs 池链上余额精确对表` → `账本净额合计 vs 池链上余额对表（容差 ≤2 raw）`（依据 `scripts/solana/stake_decode.py:212`）

## §3 完成报告 `r3_done.md` 必含
①逐条改前→改后 diff；②§1.1 字节实测；③§1.2 原始输出；④`git diff --stat`；⑤差异/停工点；⑥禁读披露。
