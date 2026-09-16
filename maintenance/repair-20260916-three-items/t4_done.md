# 施工 T4: 停工

四个白名单文件已按工单落地 `7.1.1`。四条 Python 验收全部执行：前三条 exit 0，`run_all` exit 1，**148 PASS / 3 FAIL / 151 项**。不满足 §3 完成条件，不声明完成或全绿。

## 基线与范围

- 工单：`workorder_t4_version.md`，磁盘版本 v2.1（v2 加 r2 非阻断措辞修订）；已读取 `t4_review_reply.txt`、`t4_review_reply_r2.txt`。
- 分支：`fix/three-items-20260916`；开工与结束 HEAD 均为 `f7749a616893ee833fcb0319293afb3a6cbe6cc3`。
- 开工 `git status --porcelain=v1 --untracked-files=all`：exit 0，输出为空。
- 开工 `/tmp/w3_acceptance` HEAD 与仓库一致，porcelain 输出为空。
- 仓库仅修改下列四文件，另新增本报告；不 commit，未执行 stash/checkout/reset。

| 文件 | `git diff --numstat HEAD` 新增 | 删除 | 改动 |
|---|---:|---:|---|
| `CHANGELOG.md` | 11 | 0 | §2 索引一行、详细段逐字插入；去掉两处插入后与 HEAD 原文件逐字节相同 |
| `VERSION` | 1 | 1 | `7.1.0` → `7.1.1`，保留末尾 LF |
| `pyproject.toml` | 1 | 1 | 仅第 15 行 version |
| `SKILL.md` | 1 | 1 | 仅第 23 行版本注释 |

`archive/CHANGELOG-archive.md` 未改。未重新评价 T1/T2/T3，未修改 `references/` 或 `scripts/`。

## 四条 Python 验收

原命令以 `PYTHONDONTWRITEBYTECODE=1` 环境执行，使 run_all 子进程也不产生字节码缓存；未修改测试代码或跳过测试。每条命令的完整输出及退出码 JSON 位于 `/private/tmp/t4-version-w_4qur43/`，文件名分别为 `changelog_lint`、`test_version_consistency`、`docs_lint`、`run_all`，扩展名为 `.log` / `.json`。

| 命令 | 退出码 | 关键输出 |
|---|---:|---|
| `python3 -B scripts/tests/changelog_lint.py` | 0 | PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 73 条 + 归档 139 条 |
| `python3 -B scripts/tests/test_version_consistency.py` | 0 | PASS: M-03 version metadata consistent at 7.1.1 |
| `python3 -B scripts/tests/docs_lint.py --all` | 0 | PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式） |
| `python3 -B scripts/tests/run_all.py` | **1** | **148 PASS / 3 FAIL / 151 项**；`3 项失败——修完再收工` |

全套运行时间（UTC）：`2026-09-16T13:36:41.313256+00:00` → `2026-09-16T14:19:15.433363+00:00`，耗时 2554.120 秒。151 项均有最终状态；计数从原始汇总逐项解析，保存在 `run_all_summary.json`。

改前 `python3 -B scripts/tests/changelog_lint.py`：exit 0，关键输出为：

```text
PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 72 条 + 归档 139 条
```

改后活跃 **73** 条、归档 **139** 条，活跃条数增加 **1**。

`wc -c SKILL.md`：改前 **8,024 B**，改后 **8,024 B**，相等。VERSION 保持 `7.1.1\n`（6 B）。

## run_all 三项失败逐项归因

| 失败入口 | 子命令退出码 | 证据与归因 |
|---|---:|---|
| `test_batch3_solana_vertical_slice.py` | 1 | `:625` 创建 `ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)`，在 `socket.bind` 抛出 `PermissionError: [Errno 1] Operation not permitted`。环境限制：回环端口绑定被拒；该纵切片未通过，不能算 PASS。 |
| `test_batch3_evm_vertical_slice.py` | 1 | `:281` 创建相同本地 fixture server，在 `socket.bind` 抛出同一 `PermissionError`；从 ETH 纵切片入口进入后失败。环境限制：回环端口绑定被拒；该入口未通过，不能推断其余链的纵切片通过。 |
| `test_stage2_reseal.py` | 1 | `dry_run_touches_nothing` 在 `overlay_acceptance()` 的 `:621` 白名单断言处失败；本单必需报告 `maintenance/repair-20260916-three-items/t4_done.md` 不在 W3 的 allowed 集合中。此入口为 **20/21 PASS**。归类为 **T4 交付文件集合与 W3 验收白名单的契约冲突**，不是临时目录、回环绑定或验收 worktree 缺失。 |

关键原始错误：

```text
PermissionError: [Errno 1] Operation not permitted
FAIL  dry_run_touches_nothing: AssertionError: 白名单外变更，停止验收：['maintenance/repair-20260916-three-items/t4_done.md']
stage2_reseal: 20/21 PASS
FAIL(rc=1)  test_batch3_solana_vertical_slice.py (无输出)
FAIL(rc=1)  test_batch3_evm_vertical_slice.py (无输出)
FAIL(rc=1)  test_stage2_reseal.py    stage2_reseal: 20/21 PASS
3 项失败——修完再收工
```

本报告在运行全套前建立，使验收覆盖包含 T4 报告的交付文件集合。W3 断言位于 `:625` 的 `shutil.copyfile` 之前，实际在复制前退出。未改白名单、未移走报告、未跳过该测试、未覆盖或清理预建 worktree。

**停止处置：** 两项环境失败须由调度方在同一最终树本机补验；W3 白名单冲突须由调度方另行明确兼容方式，不能只凭换环境视为消失。本单不修改测试或扩大白名单。

CHANGELOG 中“合并树全套 run_all 通过”及本机覆盖的文字按 §2 原文保留；**本次实际结果为 148 PASS / 3 FAIL，尚无调度方同一最终树补验通过证据**，不能引用该文案冒充本次全绿。

## 结束状态与保护范围

结束 `git status --porcelain=v1 --untracked-files=all`：exit 0，输出为：

```text
 M CHANGELOG.md
 M SKILL.md
 M VERSION
 M pyproject.toml
?? maintenance/repair-20260916-three-items/t4_done.md
```

- `git diff --exit-code HEAD -- references/ scripts/`：**exit 0**，输出为空。
- `git diff --check`：**exit 0**，输出为空。
- `/tmp/w3_acceptance` 结束 porcelain：**exit 0**，输出为空；HEAD 仍为 `f7749a616893ee833fcb0319293afb3a6cbe6cc3`。
- 预建 worktree 的前后快照完全相同：**1,279 个文件内容摘要、83 个目录**，无新增、删除或内容变化。`w3_before.json` / `w3_after.json` 位于上述日志目录，两者 SHA-256 均为 `4f17e271a7d2e0f9ce45706f7fe9c4fb2ab536d891939e625e4c4bd71a6e2f21`。
- 结束 Git 检查的命令、退出码、stdout/stderr 已保存为 `final_scope_checks.json`；结束 porcelain 另存 `final_status.txt`。

四个验收输入的最终 SHA-256：

| 文件 | SHA-256 |
|---|---|
| `CHANGELOG.md` | `ab29857a5a852e7d45c53e1a54c7d4b4f01fe841460342ed18f9a4a88aa6ff3d` |
| `VERSION` | `511a8bbd0ef0e332c8286ff60c232bfc1c804c0ba11eee76606cdfdc1722de92` |
| `pyproject.toml` | `742ff68cdaf4c253ebe2f223cbd61eb02f35ee9715ed55fefd1644cfbecbde73` |
| `SKILL.md` | `f09ed4f8c4e4fad4626404296eda23c071ace45014479186b0dd38ae5122c3cb` |

## 执行偏差

开工时施工者读取过 `/Users/uravvv/.codex/memories/MEMORY.md`，不符合本次禁止施工者读取 `/Users/uravvv/.codex/` 的要求；随后停止访问该目录。该偏差独立于测试结果，不得声明完整遵守禁读边界。
