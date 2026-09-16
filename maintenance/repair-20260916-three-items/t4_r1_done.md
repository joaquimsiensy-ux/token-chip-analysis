# 施工 T4-r1: 完成

依据：`workorder_t4_r1.md` v1.1 与 `t4_r1_review_reply.txt`。验收范围为返修单 §3。

- cwd：`/Users/uravvv/.claude/worktrees/tca-three-items`
- 分支：`fix/three-items-20260916`
- 开工 HEAD：`7857f15f8ec7b2d41dccf25b3756631eb71fe3e5`
- 仅订正两个白名单文件的同一句，并按指定前缀将主工单标题 v2.1 改为 v2.2；另新增本报告。

## 开工状态

命令：`git status --porcelain=v1 --untracked-files=all`；退出码 **0**；stdout 为空，工作树干净。

改前基线命令：`python3 -B scripts/tests/changelog_lint.py`；退出码 **0**。

```text
PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 73 条 + 归档 139 条
```

## 差分与 §3 验收

| 命令 | 退出码 | 关键结果 |
| --- | --- | --- |
| `git diff --exit-code HEAD -- references/ scripts/ VERSION pyproject.toml SKILL.md` | 0 | stdout 为空；受保护路径无差分 |
| `git diff --numstat HEAD -- CHANGELOG.md` | 0 | 新增 1 行、删除 1 行 |
| `git diff --numstat HEAD -- maintenance/repair-20260916-three-items/workorder_t4_version.md` | 0 | 新增 2 行、删除 2 行 |
| 下列 `python3 -B -` 一致性验收 | 0 | 两文件均为旧句 0 次、新句 1 次；修改逐字符合授权；主工单 §2 两段代码块各在 CHANGELOG 中完整出现 1 次 |
| `python3 -B scripts/tests/changelog_lint.py` | 0 | 活跃 73 条、归档 139 条，与改前相同 |
| `python3 -B scripts/tests/test_version_consistency.py` | 0 | 版本元数据一致为 7.1.1 |
| `python3 -B scripts/tests/docs_lint.py --all` | 0 | 59 个文档通过 |

diff 行数原始输出：

```text
1	1	CHANGELOG.md
2	2	maintenance/repair-20260916-three-items/workorder_t4_version.md
```

三项检查关键输出：

```text
PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 73 条 + 归档 139 条
PASS: M-03 version metadata consistent at 7.1.1
PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）
```

一致性验收命令（读取主工单 §2 的代码块；返修单仅用于取得指定旧句和新句）：

````bash
python3 -B - <<'PY'
from pathlib import Path
import re
import subprocess
import textwrap

changelog_path = Path('CHANGELOG.md')
workorder_path = Path('maintenance/repair-20260916-three-items/workorder_t4_version.md')
repair = Path('maintenance/repair-20260916-three-items/workorder_t4_r1.md').read_text()
old, new = [block.rstrip('\n') for block in re.findall(r'^```[ \t]*\n(.*?)^```[ \t]*$', repair, re.M | re.S)]
for path in (changelog_path, workorder_path):
    actual = path.read_bytes()
    before = subprocess.check_output(['git', 'show', f'HEAD:{path.as_posix()}'])
    assert before.count(old.encode()) == 1 and before.count(new.encode()) == 0
    expected = before.replace(old.encode(), new.encode(), 1)
    if path == workorder_path:
        title = '# 工单 T4（v2.1，'.encode()
        assert expected.startswith(title)
        expected = '# 工单 T4（v2.2，r1 订正 T1 小节取成员文案；'.encode() + expected[len(title):]
    assert actual == expected, f'{path}: unexpected change'
    assert actual.count(old.encode()) == 0 and actual.count(new.encode()) == 1
    print(f'PASS: {path}: exact authorized changes; old=0; new=1')
section = workorder_path.read_text().split('## §2 ', 1)[1].split('## §3 ', 1)[0]
blocks = re.findall(r'^[ \t]*```[ \t]*\n(.*?)^[ \t]*```[ \t]*$', section, re.M | re.S)
assert len(blocks) == 2, len(blocks)
changelog = changelog_path.read_text()
for index, block in enumerate(blocks, 1):
    content = textwrap.dedent(block).rstrip('\n')
    count = changelog.count(content)
    assert content and count == 1, (index, count)
    print(f'PASS: master workorder section 2 block {index}: exact CHANGELOG match count={count}')
PY
````

一致性验收输出：

```text
PASS: CHANGELOG.md: exact authorized changes; old=0; new=1
PASS: maintenance/repair-20260916-three-items/workorder_t4_version.md: exact authorized changes; old=0; new=1
PASS: master workorder section 2 block 1: exact CHANGELOG match count=1
PASS: master workorder section 2 block 2: exact CHANGELOG match count=1
```

## 执行边界

本次离线施工，不 commit，未执行 stash/checkout/reset，未运行全套 `run_all`，未触碰 `/tmp/w3_acceptance`。本报告只确认本返修单 §3 验收通过。提交后的 `test_stage2_reseal.py` 由调度方按返修单另行执行，本次未运行。

## 收工状态

命令：`git status --porcelain=v1 --untracked-files=all`；退出码 **0**。实际输出仅有白名单两处修改和本报告：

```text
 M CHANGELOG.md
 M maintenance/repair-20260916-three-items/workorder_t4_version.md
?? maintenance/repair-20260916-three-items/t4_r1_done.md
```

`git rev-parse HEAD` 与 `git branch --show-current` 均退出 **0**，结果仍为开工 HEAD `7857f15f8ec7b2d41dccf25b3756631eb71fe3e5` 和分支 `fix/three-items-20260916`。`git diff --name-only HEAD` 退出 **0**，只列两个白名单文件。

