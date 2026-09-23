# 工单 W4 v2 — 收官 review r1 三条 P2 措辞订正（纯文档，生产代码零改动）

> 来源：`final_review_r1_report.md`（P0/P1 0；FAIL 仅因沙箱不能创建临时目录致三项测试未跑，调度方本机全套 run_all 已绿）。四条 P2 中第一条（CHANGELOG 成本行移出）**不采纳**：该行符合 CHANGELOG 头部成本与质量指标登记要求，保留。其余三条采纳。v2 吸收 codex 复核 r1（`review_W4_r1_report.md`，退回）：四处全部改用复核方给出的更短措辞，第 2/3 处不再用条件句而是直述校验范围。

## 0. 纪律
- 分支 `fix/solana-txv1`；开工 `git status --short` 为空；HEAD 是 `e47cde7` 的后代且 `git diff --stat e47cde7 HEAD` 只含 `maintenance/`；`.git` 只读、commit 由调度方代做；禁读 `~/.codex`（启动披露除外）、`~/Documents`、`~/Desktop`；离线；`MPLCONFIGDIR=$HOME/.matplotlib PYTHONDONTWRITEBYTECODE=1`。
- 白名单：`CHANGELOG.md`、`references/scan-schemas.md`、本目录 `W4_done.md`。只改下列 4 处，不加新句、不加新段。

## 1. 四处替换（锚文本须整段唯一命中，`grep -nF` 核对后再改）
1. `CHANGELOG.md:104` 锚 `ACTIVE 已登记且未被认领的直接前代 pending` → `ACTIVE 已登记且 header 无 adopted 的历史 producer pending`（代码只要求前代 producer sha 在登记 ACTIVE 集合内且其 header 无 `adopted`，不检查版本相邻）。
2. `CHANGELOG.md:105` 锚 `发布后 evidence_manifest 深验重算大小与哈希，能发现任何一侧的后续改写，但不能隔离它` → `发布后 evidence_manifest 深验核对所列证据的大小与哈希，但不能隔离共享 inode 的原地改写`（深验只遍历清单所列路径，不读来源 pending）。
3. `references/scan-schemas.md:1029` 同一锚、同一替换（与第 2 条逐字一致）。
4. `references/scan-schemas.md:1031` 锚整行 `- 残缺尾行丢弃。` → `- 残缺尾行：当前 pending 普通恢复时截除；来源 pending 仅解析时忽略，字节不变。`（对应生产者 `sqd_gap_repair.py` 中 `_parse_ledger_prefix` 对来源只读、`load_resume_slots` 对当前 pending 截尾的行为，施工前各 grep 一次核对，行为不符即停工写明）。

## 2. 验证
`changelog_lint.py`、`docs_lint.py --all`、`test_version_consistency.py` 尾行；`git diff --stat` 只含两个文件；`git diff` 中 `+` 行恰 4 行、`-` 行恰 4 行。

## 3. 完成
写 `W4_done.md`（4 处改动前后原文、核对结果、尾行、自报禁读），末尾「待调度方 commit」。
