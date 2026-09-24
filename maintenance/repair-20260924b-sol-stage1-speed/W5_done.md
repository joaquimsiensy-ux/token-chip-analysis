# W5 完成：六处逐字替换已完成，四项定向测试通过

报告路径：`/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260924b-sol-stage1-speed/W5_done.md`

仅修改白名单四文件的六处指定片段及本报告。版本保持 9.2.0；未触发停工条件。部署同步测试按预期 FAIL，待调度方同步本机。

## 1. §0.1 开工检查

工作目录：`/Users/uravvv/.claude/skills/token-chip-analysis`

```text
$ git status --short
（输出为空）

$ git rev-parse HEAD
6dbe0889ff11de2235e491014e64470357e1d02d

$ W5_BASE=ef20dd825a0f3698bee79b6adfae59befcf6285d
$ git merge-base --is-ancestor "$W5_BASE" HEAD
（输出为空；exit 0）

$ git diff --quiet "$W5_BASE" HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md assets
（输出为空；exit 0）
```

## 2. 六处定位与差异范围

替换前对工单每个旧片段整段执行 `grep -n -F -e "<旧片段>" <文件>`，六次均 exit 0，均恰好一条匹配；另核实各旧片段在对应文件内恰好出现一次。

| 工单 | 文件 | grep 行号 | 匹配数 |
|---|---|---:|---:|
| §2.1 | references/split-run.md | 41 | 1 |
| §2.2 | commands-staging/token-analyze-1.md | 12 | 1 |
| §2.3 | assets/sqd-solana-coverage-map/README.md | 5 | 1 |
| §2.4 | CHANGELOG.md | 108 | 1 |
| §2.5 | CHANGELOG.md | 109 | 1 |
| §2.6 | CHANGELOG.md | 110 | 1 |

最终逐字节核对：四文件均等于 W5_BASE 内容仅应用指定六处替换后的结果，同行其他文字未变。

```text
$ git diff --numstat "$W5_BASE" -- . ':!maintenance'
3	3	CHANGELOG.md
1	1	assets/sqd-solana-coverage-map/README.md
1	1	commands-staging/token-analyze-1.md
1	1	references/split-run.md

$ git diff --stat "$W5_BASE" -- . ':!maintenance'
 CHANGELOG.md                             | 6 +++---
 assets/sqd-solana-coverage-map/README.md | 2 +-
 commands-staging/token-analyze-1.md      | 2 +-
 references/split-run.md                  | 2 +-
 4 files changed, 6 insertions(+), 6 deletions(-)
```

`git diff --check`：exit 0。未修改 scripts、SKILL.md、VERSION、pyproject.toml、CHANGELOG 索引与其他版本段、采集分册、资产数据或仓库外 commands。

## 3. UTF-8 字节预算

基线字节由 `git show "$W5_BASE:<路径>"` 输出交 `wc -c` 核对；与替换前工作文件一致。替换后再次执行 `wc -c`。

| 文件 | 替换前／W5_BASE | 替换后 | 净增 | 上限 |
|---|---:|---:|---:|---:|
| references/split-run.md | 28,064 B | 28,223 B | +159 B | 260 B |
| commands-staging/token-analyze-1.md | 2,382 B | 2,477 B | +95 B | 140 B |
| assets/sqd-solana-coverage-map/README.md | 6,601 B | 6,723 B | +122 B | 160 B |

三项均符合预算。

## 4. §0.7 测试结果

五项测试均通过内存运行器执行：`PYTHONDONTWRITEBYTECODE=1 python3 -B -c`，用 `runpy.run_path(..., run_name="__main__")` 保留测试入口及断言，并应用：

```python
patch.object(tempfile.TemporaryDirectory, "cleanup", lambda self: self._finalizer.detach())
```

未修改测试源码、断言或判定。下列为测试自身尾行，不含运行器追加的临时目录记录。

| 测试 | exit | 尾行原文 |
|---|---:|---|
| test_g3_docs_guards.py | 0 | PASS: F-05 machine boundary |
| test_review_scale_guards.py | 0 | PASS: M-04 bounded helpers, streaming parquet batches, and bound input manifests |
| test_sqd_coverage_probe.py | 0 | PASS SQD coverage probe: 24/24 offline groups |
| test_exemption_guards.py | 0 | PASS: exemption guards (EX-01 full-F-03) |
| test_commands_deploy_sync.py | 1（预期） | FAIL: commands-staging 与已部署命令不一致 |

部署同步失败完整原文：

```text
- SHA-256 不一致：token-analyze-1.md staging=298e969316788140d5d08e5d275daf8576f96cff01735c72c823591182041c2e deployed=9ef5219c7aa1fa69ae23d31c27a1fb6fe926e94cd2908fa8203c5a324d931bd6
FAIL: commands-staging 与已部署命令不一致
```

该结果符合工单预期，未修改部署版。`docs_lint.py`、`changelog_lint.py` 因读取禁区交调度方执行；本轮未运行 `run_all.py`。CHANGELOG 中既往验收结论按工单逐字归并，不作为本轮新增测试结果。

## 5. 保留的测试临时目录

26 个系统临时目录均已解除自动清理，测试后逐一确认仍存在。共同父目录为：

`/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/`

以下每行均为该父目录下的目录名，父目录与目录名拼接即完整路径：

```text
tmpbd13z550
tmpdojhr5qz
w2-find-svxyjx4g
w2-find-sort-b5kg2ypg
w2-find-bad-mhxae659
w2-find-errors-2ikstuz6
sqd-publish-8i1it7k9
sqd-cli-urpdxiaz
sqd-no-blocks-ic7iq6zf
sqd-resume-2pvw2azo
sqd-quota-xngnwktg
sqd-checkpoint-fjrz9ehk
sqd-dry-s_nun0qm
sqd-page-invalid-8n59gp28
sqd-page-pagination-b0gcs2_4
sqd-page-empty-3e5z3dak
sqd-map-ap5ce4z8
sqd-export-map-rqapqhs7
w1-inherit-ch_lzs8n
w1-tamper-k3uq86b3
w1f-conflicts-t2tms0b3
w1-export-repair-jkvtu01o
w1-chain-9grhcmej
w1-compat-ge3eqlmu
w1-origins-xzlnfsmj
tmp27pgoo9d
```

未对这些目录执行自动清理或批量删除。

## 6. 禁读与执行纪律披露

本轮未读取 `~/.codex/`，未启动 memories 搜索；未读取 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`、许可范围外的 maintenance、Desktop 或 Documents。测试及子进程按离线 fixture 路径执行，未访问上述禁区。

全程离线，未 commit、push、stash、checkout、reset，未建 worktree，未执行批量删除。仓库写入仅限白名单四文件和本报告；测试产物保留于上述系统临时目录。

