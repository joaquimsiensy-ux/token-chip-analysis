# 工单 T4-r1（v1.1，codex 复核通过并采纳两条措辞建议；出处：codex 盲审 `t4_blind_reply.txt` ⑤ 阻断）：CHANGELOG 7.1.1 条目一句事实订正

> 主工单 `workorder_t4_version.md`（v2.1）全部条款继续有效；本单只订正一句登记文案，并同步主工单 §2 代码块，保持"工单代码块＝CHANGELOG 逐字"。

## §0 纪律与白名单
- 同主工单 §0（禁读 `/Users/uravvv/.codex/`、`/Users/uravvv/.claude/skills/_archive/`；不 checkout tag；离线；不 commit；禁 stash/checkout/reset）。
- **只允许修改**：`CHANGELOG.md`（仅 7.1.1 条目「备份堆积与台账瘦身（T1）」小节内的一句）、`maintenance/repair-20260916-three-items/workorder_t4_version.md`（仅 §2 详细条目代码块内的同一句＋标题版本号标记 v2.1→v2.2）；另允许**新增** `t4_r1_done.md`。`references/`、`scripts/`、`VERSION`、`pyproject.toml`、`SKILL.md` 一字不动。

## §1 缺口
`CHANGELOG.md:96`（7.1.1 条目 T1 小节）写"`test_adjudication_validator`/`test_distribution_gate` 改从源 fixture 取成员"。实际（盲审核实）：`scripts/tests/test_adjudication_validator.py:100` 读取模板生成的 `.members.json` 旁车再取 `side[candidate_id]`；`scripts/tests/test_distribution_gate.py:377` 同样读旁车，:378–384 另与源扫描集合对照，:388–389 填裁决仍用旁车。实现符合 T1 工单 :62；错在登记文案。

## §2 修法（两处同一句，逐字）
把
```
`test_adjudication_validator`/`test_distribution_gate` 改从源 fixture 取成员并保留"老台账带该字段仍 PASS"用例
```
替换为
```
`test_adjudication_validator`/`test_distribution_gate` 改从模板生成的 `.members.json` 旁车取成员（后者另与源扫描集合对照）并保留"老台账带该字段仍 PASS"用例
```
- 位置①：`CHANGELOG.md` 7.1.1 条目「**备份堆积与台账瘦身（T1）**」一行内（约 :96）。
- 位置②：`workorder_t4_version.md` §2 第二个代码块内对应句；并把首行标题 `# 工单 T4（v2.1，` 改为 `# 工单 T4（v2.2，r1 订正 T1 小节取成员文案；`（其余不动）。
- 该句在两文件中各出现且仅出现一次；改后两文件中该句仍逐字相同。

## §3 验收
- `git status --porcelain=v1 --untracked-files=all` 只列 `CHANGELOG.md`、`workorder_t4_version.md`（M）与 `t4_r1_done.md`（??）。
- `git diff --exit-code HEAD -- references/ scripts/ VERSION pyproject.toml SKILL.md` 退出码 0。
- `git diff --numstat HEAD -- CHANGELOG.md` 为 `1 1`。
- 主工单 `workorder_t4_version.md` §2 两段代码块（去缩进）仍逐字在 CHANGELOG 中（可用 python 读该工单 ``` 块比对；勿误取本返修单的旧/新句代码块）。
- `python3 -B scripts/tests/changelog_lint.py`、`test_version_consistency.py`、`docs_lint.py --all` 均 exit 0。
- 全套 `run_all` 本单不要求（只改 CHANGELOG 与工单文案，不改生产／测试代码；读取 CHANGELOG 的 `changelog_lint`、`test_version_consistency` 已在本单验收内）；提交后由调度方在最终树本机单跑 `test_stage2_reseal.py` 记入验收。

## §4 报告 `t4_r1_done.md`
首行 `# 施工 T4-r1: 完成` 或 `停工`；列两文件 diff 行数、§3 各命令退出码与关键输出。不 commit。
