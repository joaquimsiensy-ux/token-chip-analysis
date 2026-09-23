# T2 完成：9.0.4 历史时间生产者登记与两层精确接线已落地，九项定向测试通过，调度方补验项单列

开工分支 main，实际 HEAD 为 `1624b86`；本轮未 commit/push。源码和测试按工单 v3.1 落地，FR-02 不在范围内。

## 开工基线与施工锚

工作目录：`/Users/uravvv/.claude/skills/token-chip-analysis`。

```text
$ git status --short
（无输出，exit 0）
$ git rev-parse --short HEAD
1624b86
$ git merge-base --is-ancestor d2d6641 HEAD
（无输出，exit 0）
$ git diff --quiet d2d6641 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md
（无输出，exit 0）
```

§2 全部整行施工锚在写入前按 `grep -n -F -x -- '<整行>' <文件>` 核验，均恰一处且与工单基线行号一致；producer_history.py:242 相邻结构为 `    },`。最初核验以 `-` 开头的文档行时漏了 grep 的 `--`，命令参数解析失败；补上后原文与行号完全吻合，未发生源码锚不符，未更改方案。

## RED 与历史哈希复现

完整证据见 [T2_red_evidence.txt](T2_red_evidence.txt)，在修改生产代码和测试前取得：

1. 基线上以 `python3 -B -c` 调用 `historical_producer_hashes("scripts/lib/time_spotcheck.py", "time-spotcheck/v3")`，输出 `set()`。
2. H11：当前生产者生成文件输入收据，另存新文件，仅将 receipt.producer.sha256 改为登记旧哈希，更新 item 引用后调真实 `validate_reconciliation_check`，抛出 `ValueError: reconciliation time receipt envelope invalid: producer hash mismatch；存量案例须重跑对应生产者获取当前回执`。
3. 引用调度方既有 `T2_red_evidence_opn_verify.log`，尾行为 `✗ reconciliation/accounting 公共深验失败: reconciliation time producer/runner is not current repository script`。exit 2 来自工单陈述，原日志未单列退出码；本轮未访问 OPN 案卷。

```sh
git show b52cbedf230218e5da46334cf99b7111235e8367:scripts/lib/time_spotcheck.py | shasum -a 256
```

```text
87bbad2246f07afa2db4b37a7289fff2fc6ac16387284411e75104e1109f0a39  -
```

## 实际施工位置

以下右侧均为施工后行号；左侧基线为 d2d6641。

| 工单 | 文件与实际位置 | 落地内容 |
| --- | --- | --- |
| §2.1 | scripts/lib/producer_history.py 原 :243 前 → :243–250 | 增加指定六键 ACTIVE 条目，commit/sha256 已由 git 复现 |
| §2.1 | scripts/tests/test_producer_registry_current.py 原 :21–24 → :21–25 | 替换注释、仅增精确 HISTORICAL_ONLY 对；main 与检查逻辑逐字不变 |
| §2.2(0) | scripts/report/shared_release_receipt.py 原 :1208 前 → :1208–1217 | 新增唯一私有历史准入函数，固定协议字面量 |
| §2.2(a) | 同文件原 :1221 → :1233–1235 | envelope 取 receipt 自身 producer.path 查询历史集 |
| §2.2(b) | 同文件原 :1459–1460 → :1473–1476 | wrapper 取 item 自身 producer.path 查询历史集 |
| §2.3 | scripts/tests/test_recon_deep_reverify.py 原 :593 前 → :593–659；原 :601 后 → :671 | 新增历史回归函数并调用，覆盖登记断言、H11–H16、非对象与非字符串 path |
| §2.4 | references/data-pipeline-evm-recon.md :152/:158 | 按工单整行替换，净减 7 B，换行数不变 |
| §2.5 | VERSION :1；pyproject.toml :15；SKILL.md :23 | 9.0.3 → 9.0.4 |
| §2.5 | CHANGELOG.md 原 :13 前 → :13；原 :100 前 → :101–107 | 200 B 索引行及四条详细说明，含来源 commit、review 编号、实际字节与测试边界 |

消费者未新增 import、模块常量或公开函数。其他 key 与 solana 传入 None；owner/producer 非对象、path 非字符串或不在 EVM/time 白名单时返回 None。当前哈希仍被接受，历史集不替代当前集；不按 input.kind 分流，目录仍须通过原有身份/清单/目录信任链。receipt_kernel/receipt_validate/time_spotcheck/anchor_plan/anchor_selection 逐字节未改，其余 §0.4 保护路径亦无 diff。

## 回归与 H16

- H11 登记旧哈希通过完整时间收据深验。
- H12 陌生哈希、H13 错误 path 均以 producer hash mismatch 拒绝。
- H14 balance 的 verify_recon 原 path 与 time_spotcheck path 两种组合均在 envelope 报 producer hash mismatch；Solana 准入函数返回 None。
- H15 默认 validate_receipt 不传 allowed 时结果严格等于 `["producer hash mismatch"]`。
- 收据 `[]` 仍抛含 receipt must be an object 的 ValueError；producer.path 为 list 返回 None，无 TypeError。
- H16 在同一 root 调 make_case，真实四查 wrapper 的 time 引用指向另存的 H11 文件；旧哈希正例通过，仅破坏 wrapper producer 哈希的负例按指定错误拒绝，恢复后再次通过。未 mock/替换 repo_ref_ok、validate_receipt、validate_reconciliation_check。
- 夹具冲突：仅有工单已知的 make_case 覆写 time_spotcheck.json；H11 另存文件规避了此覆盖。未出现额外冲突，未启用子目录兜底。后续既有时间回归也通过。

## 定向测试

全部下列执行命令均带 `MPLCONFIGDIR="$HOME/.matplotlib"` 与 `PYTHONDONTWRITEBYTECODE=1`，使用 `python3 -B`。本轮新增临时目录均用 tempfile 创建并 Path(...).resolve()；既有测试脚本原样执行。

| 命令 | exit | 结果 | 实测尾行 |
| --- | ---: | --- | --- |
| `python3 -B scripts/tests/test_producer_registry_current.py` | 0 | PASS | `producer registry: 0 FAIL` |
| `python3 -B scripts/tests/test_recon_deep_reverify.py` | 0 | PASS | `PASS test_recon_deep_reverify` |
| `python3 -B scripts/tests/test_anchor_plan_v3.py` | 0 | PASS | `anchor-plan v3: 16/16 PASS` |
| `python3 -B scripts/tests/test_time_spotcheck.py` | 0 | PASS | `time_spotcheck 契约测试全部通过（20 项）` |
| `python3 -B scripts/tests/test_handoff_manifest.py` | 0 | PASS | `handoff_manifest 契约测试全部通过（283 项）` |
| `python3 -B scripts/tests/test_audit_release_gate.py` | 0 | PASS | `PASS: audit_release_gate 净室资产/哈希/CEX受益权/阴性结论/图表封口与负钳零/对抗复核否决/四查WARN拦截/双线阈值/嵌套未决暴露/静置仓全集对账/日级峰值口径闭环十一类契约全过` |
| `python3 -B scripts/tests/test_batch4_invariant_guards.py` | 0 | PASS | `PASS B4-G1: bare pool / labels / vertical slice / denominator injections` |
| `python3 -B scripts/tests/test_exemption_guards.py` | 0 | PASS | `PASS: exemption guards (EX-01 full-F-03)` |
| `python3 -B scripts/tests/invariant_scan.py` | 0 | PASS | `PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0` |
| `python3 -B scripts/tests/test_batch3_evm_vertical_slice.py` | 1 | SANDBOX-BLOCKED | `PermissionError: [Errno 1] Operation not permitted` |
| `python3 -B scripts/tests/changelog_lint.py` | 未执行 | 调度方待验 | 无；不得记 PASS |

batch3 失败现场为 `test_batch3_evm_vertical_slice.py:283` 的 `ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)`，在 socket.bind 抛 `PermissionError: [Errno 1] Operation not permitted`。此项仅记 SANDBOX-BLOCKED，未声称通过。

九项定向测试退出码均为 0；其中深验回归首次施工后执行即通过，未重复运行。其他测试完整 stdout/stderr 暂存于 `/private/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/t2-directed-tests-8f5q_h_o/`；其退出码和尾行已保存在上表。changelog_lint 未运行，未绕过归档检查。

## 字节核验

文档行字节不含换行；已实际执行以下命令：

```sh
git show d2d6641:references/data-pipeline-evm-recon.md | sed -n '152p' | tr -d '\n' | wc -c
sed -n '152p' references/data-pipeline-evm-recon.md | tr -d '\n' | wc -c
git show d2d6641:references/data-pipeline-evm-recon.md | sed -n '158p' | tr -d '\n' | wc -c
sed -n '158p' references/data-pipeline-evm-recon.md | tr -d '\n' | wc -c
```

按上述顺序输出：`111`、`110`、`326`、`320`。算法：`(110 + 320) − (111 + 326) = −7 B`。

| 范围 | 施工前 B | 施工后 B | 差额 |
| --- | ---: | ---: | ---: |
| SKILL.md | 8021 | 8021 | 0 |
| commands-staging/*.md | 8789 | 8789 | 0 |
| references 三组 glob | 929092 | 929085 | −7 |

references 计数采用 `references/*.md`、`references/*/*.md`、`references/*/*/*.md` 三组文件大小之和：施工前 824137 + 104955 + 0；施工后 824130 + 104955 + 0，与递归 Markdown 总量一致。只读取文件 stat 元数据计数，未读取禁读文件正文。SKILL 仅版本标记改变；commands-staging 无 diff。CHANGELOG 新索引行 UTF-8 不含换行恰 200 B。

## 白名单与 diff

`git diff --check` exit 0。已核验受版本管理的改动恰为九个白名单文件；另有授权的本报告和 T2_red_evidence.txt。没有改 invariant_manifest/contract_manifest。

```text
$ git diff --stat d2d6641 -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md
 CHANGELOG.md                                    |  8 +++
 SKILL.md                                        |  2 +-
 VERSION                                         |  2 +-
 pyproject.toml                                  |  2 +-
 references/data-pipeline-evm-recon.md           |  4 +-
 scripts/lib/producer_history.py                 |  8 +++
 scripts/report/shared_release_receipt.py        | 22 ++++++--
 scripts/tests/test_producer_registry_current.py |  9 ++--
 scripts/tests/test_recon_deep_reverify.py       | 70 +++++++++++++++++++++++++
 9 files changed, 115 insertions(+), 12 deletions(-)
```

scripts 四文件合计 +102/−7；上述九文件合计 +115/−12。未 commit、push、stash、checkout、reset，未建 worktree，未进行外部网络访问。

## 未做与存疑事项

1. `python3 -B scripts/tests/changelog_lint.py`：调度方待验。按 §0.2 不读取 archive，也未移除或绕过其归档检查；须由调度方回传退出码与尾行。
2. `python3 -B scripts/tests/test_batch3_evm_vertical_slice.py`：SANDBOX-BLOCKED；调度方需在可 bind loopback 的环境补验。
3. `python3 -B scripts/tests/run_all.py`：按工单未执行，调度方待验。
4. 真实 OPN 案 verify：按工单未执行，调度方待复验；未访问任何 Desktop 案卷。
5. FR-02：本工单排除，另单由用户裁决。
6. 其余施工存疑事项：无。

禁读路径披露：本轮未读取 ~/.codex/（包括 memories），未读取 archive/、blind-reviews/、.staging_*、references/attic.md 正文、其他历史 maintenance 目录或 /Users/uravvv/Desktop 案卷。references 总字节统计仅使用文件大小元数据。
