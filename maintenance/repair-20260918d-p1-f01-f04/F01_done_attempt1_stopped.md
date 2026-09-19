# 施工 F01：停工

开工基线检查发现工作区不干净，触发工单 §0.1 的强制停工条件。本次仅新建此停工报告，未修改生产代码、测试或既有文件，未开始 RED 取证。

## 开工记录

工作目录：`/Users/uravvv/.claude/skills/token-chip-analysis`

```text
$ git rev-parse HEAD
7a0b083c66f54017b640486bac2d88483eedf273

$ git branch --show-current
main

$ git status --short
 M maintenance/repair-20260918d-p1-f01-f04/blind_F01_prompt.md

$ git diff --stat 868d3f61 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md
 scripts/lib/camp_spec.py             |  5 ++++-
 scripts/tests/test_repair_batch_c.py | 15 +++++++++++++++
 2 files changed, 19 insertions(+), 1 deletion(-)

$ git diff --stat 868d3f61 HEAD -- scripts/prices scripts/report scripts/tests/test_stage2_closeout.py references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md
```

上述五条命令均退出 0；最后一条命令无输出。分支、广范围差异及 §0.1 窄范围差异符合要求，但 `git status --short` 非空，不能开工。未打开或修改已有变更的 `blind_F01_prompt.md`，未判断其内容或来源。

## 执行范围与未执行项

- §2 生产代码与测试变更：未执行，无本次施工代码 diff。
- §0.7 / §2.3 六段 RED：6b、6c、6d、6e、6f、6g 均未执行，未创建 `F01_red_evidence.txt`。
- 锚点核验及开工 `invariant_scan.py`：未执行，因先决基线检查已失败。
- §0.8 定向测试：`test_stage2_closeout.py`、`test_a4_gate.py`、`test_audit_release_gate.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py`、`invariant_scan.py` 均未执行，无测试尾行或 PASS 声明。
- reseal 未实跑、交调度方本机补验；本次施工未完成，尚未到补验阶段。
- §1.1 三项字节数：未实测；未修改 `SKILL.md`、`references/`、`commands-staging/`。
- 未运行 `run_all.py`，未 commit、push、部署、stash、checkout 或 reset，未删除文件，未访问网络。
- 与工单差异 / 停工点：仅 §0.1 工作区不干净；没有自行变更施工方案。未创建完成报告 `F01_done.md`。

## 写入报告后的工作区复查

```text
$ git diff --stat
 maintenance/repair-20260918d-p1-f01-f04/blind_F01_prompt.md | 8 ++++----
 1 file changed, 4 insertions(+), 4 deletions(-)

$ git status --short
 M maintenance/repair-20260918d-p1-f01-f04/blind_F01_prompt.md
?? maintenance/repair-20260918d-p1-f01-f04/F01_done_attempt1_stopped.md
?? maintenance/repair-20260918d-p1-f01-f04/final_review_prompt.md
```

上述两条命令均退出 0。`git diff --stat` 不包含未跟踪文件；本次唯一写入为此停工报告。复查时额外出现的 `final_review_prompt.md` 不是本次创建，未打开或修改；其来源未核查。停工决定仍基于最初的 §0.1 检查结果。

## 禁读披露

未读取 `~/.codex/`（包括 memories），未打开 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`/Users/uravvv/Desktop`、`/Users/uravvv/Documents`，未打开本工单目录以外的历史 maintenance 文件内容。

首次定位工单的 `rg --files` 检索范围过宽，枚举了其它历史 maintenance 目录中的少量 F01 文件名；没有打开、读取其文件内容、复制或修改这些文件。该目录枚举偏离禁读范围要求，在此明确披露；发现基线不符后未继续搜索。所有测试均未运行，因此也没有测试子进程访问历史 maintenance 文件。
