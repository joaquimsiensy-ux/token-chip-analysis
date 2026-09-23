# W4 完工记录

按本目录最高版本 `workorder_W4_v2.md` 的 §0–§3 完成；生产代码零改动。

## 开工与锚文本核对

- 开工 `git status --short` 输出为空；分支为 `fix/solana-txv1`。
- `git merge-base --is-ancestor e47cde7 HEAD` 退出码 0；`git diff --stat e47cde7 HEAD` 与 `git diff --name-only e47cde7 HEAD` 确认仅有 `maintenance/` 下 7 个文件。
- 修改前使用 `grep -nF -e '<锚>'` 核对：四处锚分别在 `CHANGELOG.md:104`、`CHANGELOG.md:105`、`references/scan-schemas.md:1029`、`references/scan-schemas.md:1031` 各唯一命中；第四处同时确认整行一致。

## 四处改动前后原文

1. `CHANGELOG.md:104`
   - 前：`ACTIVE 已登记且未被认领的直接前代 pending`
   - 后：`ACTIVE 已登记且 header 无 adopted 的历史 producer pending`
2. `CHANGELOG.md:105`
   - 前：`发布后 evidence_manifest 深验重算大小与哈希，能发现任何一侧的后续改写，但不能隔离它`
   - 后：`发布后 evidence_manifest 深验核对所列证据的大小与哈希，但不能隔离共享 inode 的原地改写`
3. `references/scan-schemas.md:1029`
   - 前：`发布后 evidence_manifest 深验重算大小与哈希，能发现任何一侧的后续改写，但不能隔离它`
   - 后：`发布后 evidence_manifest 深验核对所列证据的大小与哈希，但不能隔离共享 inode 的原地改写`
4. `references/scan-schemas.md:1031`
   - 前：`- 残缺尾行丢弃。`
   - 后：`- 残缺尾行：当前 pending 普通恢复时截除；来源 pending 仅解析时忽略，字节不变。`

## 行为核对

- 施工前分别用 `grep -nF` 核对 `def _parse_ledger_prefix(` 和 `def load_resume_slots(`，定义各唯一命中。`scripts/solana/sqd_gap_repair.py:689–704` 仅对内存中的 bytes 取完整行；来源在第 834 行通过 `read_bytes()` 传入解析器，不改来源字节。当前 pending 普通恢复在第 733 行调用 `_read_ledger_prefix`，该函数在第 707–719 行将清理后的完整行写回并同步。行为与工单一致。
- `adopt_predecessor_pending` 第 837–853 行拒绝来源 header 含 `adopted`，遍历登记历史 producer 集合重算 digest；`scripts/lib/producer_history.py:278` 的 `historical_producer_hashes` 返回排除 REVOKED 后的匹配 ACTIVE 集合，无版本相邻检查。
- `scripts/lib/solana_exact_validate.py:1422–1426` 遍历 manifest 所列证据路径；来源目录名用于认领记录校验，不作为该证据遍历的读取目录。

## 验证结果与尾行

以下三项均使用 `MPLCONFIGDIR="$HOME/.matplotlib" PYTHONDONTWRITEBYTECODE=1` 执行，退出码均为 0：

- `python3 scripts/tests/changelog_lint.py`
  - 尾行：`PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 83 条 + 归档 139 条`
- `python3 scripts/tests/docs_lint.py --all`
  - 尾行：`PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）`
- `python3 scripts/tests/test_version_consistency.py`
  - 尾行：`PASS: M-03 version metadata consistent at 9.1.0`

`git diff --check` 通过；`git diff --stat` 仅含 `CHANGELOG.md` 和 `references/scan-schemas.md`，汇总为 `2 files changed, 4 insertions(+), 4 deletions(-)`。排除 diff 文件头后的 `+` 行恰 4 行、`-` 行恰 4 行；每个文档各增加 2 行、删除 2 行。本完工记录为新增未跟踪文件，不计入上述未暂存 diff。

## 纪律自报

全程离线；未读取 `~/.codex`、`~/Documents`、`~/Desktop`；未执行 git 写操作，未执行 `git add` 或 `git commit`；未删除文件。仅修改授权的两个文档并新增本记录，保留 CHANGELOG 成本行。

待调度方 commit
