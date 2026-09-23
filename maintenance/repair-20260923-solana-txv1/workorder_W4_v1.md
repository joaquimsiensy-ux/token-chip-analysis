# 工单 W4 v1 — 收官 review r1 三条 P2 措辞订正（纯文档，生产代码零改动）

> 来源：`final_review_r1_report.md`（P0/P1 0；FAIL 仅因沙箱不能创建临时目录致三项测试未跑，调度方本机全套 run_all 已绿）。四条 P2 中第一条（CHANGELOG 成本行移出）**不采纳**：CHANGELOG 头部规则要求「每条迭代条目附成本指标+质量指标」，该行是规则要求的登记项而非施工叙述。其余三条采纳。

## 0. 纪律
- 分支 `fix/solana-txv1`；开工 `git status --short` 为空；HEAD 是 `e47cde7` 的后代且 `git diff --stat e47cde7 HEAD` 只含 `maintenance/`；`.git` 只读、commit 由调度方代做；禁读 `~/.codex`（启动披露除外）、`~/Documents`、`~/Desktop`；离线；`MPLCONFIGDIR=$HOME/.matplotlib PYTHONDONTWRITEBYTECODE=1`。
- 白名单：`CHANGELOG.md`、`references/scan-schemas.md`、本目录 `W4_done.md`。只改下列 4 处，不加新句、不加新段。

## 1. 四处替换（锚文本须整段唯一命中，`grep -nF` 核对后再改）
1. `CHANGELOG.md:104` 锚 `ACTIVE 已登记且未被认领的直接前代 pending` → `ACTIVE 已登记且未含认领记录的历史 producer pending`（代码只要求前代 producer sha 在登记 ACTIVE 集合内且其 header 无 `adopted`，不检查版本相邻）。
2. `CHANGELOG.md:105` 锚 `能发现任何一侧的后续改写，但不能隔离它` → `在已发布清单不变时能发现任何一侧的后续改写，但不能隔离它`。
3. `references/scan-schemas.md:1029` 同一锚、同一替换（与第 2 条逐字一致）。
4. `references/scan-schemas.md:1031` 锚整行 `- 残缺尾行丢弃。` → `- 残缺尾行：当前 pending 的普通恢复会截掉并清理；来源 pending 的残尾只在解析时忽略，来源字节不变。`（对应生产者 `sqd_gap_repair.py` 中 `_parse_ledger_prefix` 对来源只读、`load_resume_slots` 对当前 pending 截尾的行为，施工前各 grep 一次核对，行为不符即停工写明）。

## 2. 验证
`changelog_lint.py`、`docs_lint.py --all`、`test_version_consistency.py` 尾行；`git diff --stat` 只含两个文件；`git diff` 中 `+` 行恰 4 行、`-` 行恰 4 行。

## 3. 完成
写 `W4_done.md`（4 处改动前后原文、核对结果、尾行、自报禁读），末尾「待调度方 commit」。
