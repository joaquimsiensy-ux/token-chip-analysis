# 施工 T1：停工

停工发生于 §0.7 基线 RED 取证，尚未修改生产、测试、文档或版本文件。工单 §2.3 指定的 `root = Path(td)` 在本机默认临时目录环境中，使 main 在 mock `build_envelope` 之前被输出路径校验拒绝；因此无法按指定夹具取得第一项 RED，也无法把该用例如文落地后报 PASS。按派工指令“施工中若发现工单与代码不符，停工写 T1_done_attempt1_stopped.md，不得自行改方案”停工。

## 开工基线

工作目录：`/Users/uravvv/.claude/skills/token-chip-analysis`；分支：`main`。

```text
$ git rev-parse HEAD
e498a1d6ae689a0b7d9751468ef074fd21a9e49f
$ git status --short
（空输出）
$ git diff --stat f4f80567c21f HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md
（空输出）
```

两项基线均通过；所有施工整行锚均通过 `grep -n -F -x` 核验恰一处、行号一致（见文末记录）。

开工检查：

```text
$ python3 -B scripts/tests/invariant_scan.py
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0
exit=0
```

## 停工证据与三项 RED 结果

详细输出：[T1_red_evidence.txt](T1_red_evidence.txt)。三项各用独立临时夹具，逐项捕获异常，第一项失败不跳过后项。仓库测试文件未改；只在 `/private/tmp/t1_red.py` 中将测试模块 `_produce_plan` 的函数定义在内存扩展为工单指定目录夹具，24 行 logs/blocks、原 anchor_plan 参数与调用保持一致。三份计划均真实生成并通过 load_validated_plan 和 validate_semantic_replay，矩阵点 4、强制点 9；没有用缺失 helper 的 AttributeError 代替 RED。

1. **生产者 main 接线：未取得预期 RED，构成停工原因。** argv、mock 与工单指定方式一致；main 返回 1，但 mock 没有被调用，`captured={}`，没有输出收据。实际 stderr：

   ```text
   [fatal] output/transcript 路径冲突: output parent contains symlink: /var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/t1_red_1_wgq27upl/time_spotcheck.json
   ```

   探针随后访问 `captured["input"]` 所报 `KeyError: 'input'` 是上述前置拒绝的结果，不是本任务原缺陷的 RED。第一次运行已出现相同行为；只改进临时脚本日志后再次运行，三项独立结果一致，证据文件保存第二次完整输出。
2. **消费者目录放行：RED 已复现。** 清单绑定的合法目录计划被基线拒绝：`time plan authority chain broken: time plan input identity is not a regular file`。
3. **消费者清单篡改：负例保持 PASS。** 清单 input.sha256 改为 64 个 0 后，拒绝：`time plan authority chain broken: plan receipt envelope invalid: ['input input_manifest size mismatch']`。此项本来就不要求变红。

阻断的代码与环境依据：

- `scripts/lib/time_spotcheck.py:409` 在 `build_envelope` 之前调用 `assert_distinct_paths(a.out, a.transcript_out)`；其异常由 `:410–412` 捕获并返回 1。
- `scripts/lib/receipt_kernel.py:732–734` 对每个输出路径调用 `_secure_target`；`:248–249` 遇父路径 symlink 直接抛出 `output parent contains symlink`。
- 当前 `TMPDIR=/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/`，`tempfile.gettempdir()` 保留 `/var` 前缀，`Path('/var').is_symlink()` 为 True。
- 工单 §2.3 的 `root = Path(td)`、`out = root / "time_spotcheck.json"` 未归一输出路径；消费者允许系统目录别名，不等于 receipt_kernel 的输出路径也允许父级 symlink。工单“fake_envelope 抛出后被捕获返回 1”的接线前提在当前环境不成立。
- 此错误不是 `No usable temporary directory found`，故不套用 §0.8 的 `SANDBOX-BLOCKED` 豁免。

待修订工单后重派：可审查的最小候选是将新用例中的 `root = Path(td)` 改为 `root = Path(td).resolve()`，使输出路径使用真实目录，并同步规定 RED 夹具使用同一写法；本次未应用、未据此继续取证或施工，也未修改 TMPDIR 绕过。

## 执行范围与未执行项

§2.1–2.5 均未执行；无生产 diff 行号、无新回归用例、版本仍为 9.0.2。未运行 §0.8 的八项完工定向验收；仅开工 invariant 已按上述命令运行且 PASS。没有运行 run_all.py，没有运行真实案卷判断链，没有外部网络调用，没有 commit/push/stash/checkout/reset。

字节前后（未施工，元数据合计；未读取 references/attic.md 内容）：

| 范围 | 开工 B | 停工 B |
| --- | ---: | ---: |
| SKILL.md | 8021 | 8021 |
| commands-staging/*.md | 8789 | 8789 |
| references/**/*.md | 929092 | 929092 |
| references/data-pipeline-evm-recon.md:158，不含换行 | 326 | 326 |

与工单差异：只有上述 main 接线前置阻断；未自行改方案。未创建 T1_done.md，避免误标完成。

## 施工锚核验原始匹配

每项均由 `grep -n -F -x -- <整行原文> <目标文件>` 得到，校验输出恰一行且行号符合工单；非唯一事实引用按指定函数/唯一 target 行的相邻上下文核验。

```text
scripts/lib/time_spotcheck.py:180:def validate_semantic_replay(plan, raw_input, *, mem_limit="6GB", threads=4):
scripts/lib/time_spotcheck.py:415:    target = {"chain": a.chain, "token": token, "as_of_block": a.final_block}
scripts/lib/time_spotcheck.py:420:                                          "input": a.input},
scripts/report/shared_release_receipt.py:1033:        identity = plan_receipt.get("input_identity")
scripts/report/shared_release_receipt.py:1043:                 "plan input manifest differs from signed receipt binding")
scripts/tests/test_anchor_plan_v3.py:99:def _produce_plan(root):
scripts/tests/test_anchor_plan_v3.py:521:def main():
references/data-pipeline-evm-recon.md:158:- 产物 `time_spotcheck.json`（`time-spotcheck/v3`，target 绑定 chain/token/final-block，并绑定 plan、plan receipt、merged input 与逐笔 RPC transcript；verdict/exit_code 为 0 PASS/2 FAIL/1 检测自身失败禁当 PASS）；split-run 案是 READY 必备件＋AUTO_GATES（handoff_manifest 重读防手报）。
VERSION:1:9.0.2
pyproject.toml:15:version = "9.0.2"
SKILL.md:23:<!-- skill-version-source: VERSION; skill-version: 9.0.2 -->
CHANGELOG.md:13:- **9.0.2**（2026-09-19）口径漂移与文档-代码不符审计第二期闭环（针对 7.2.0→9.0.1 六版代码大改而文档零改动）：codex 两路盲审十三轮（a 路全范围术语表法 9→2→3→4→2→2→2→2→1→1→2→0→1，b 路 7.2.0 起代码变更区专审 0→0→2→1→1→0→1→2→2→0→0→0→0；用户裁决 R13 修完即收官），十二份工单皆先 codex 只读复核（退回 9 次全在派工前拦下）再 codex 施工，38 条/21 文件纯文本修复，零代码改动；references 930076→929092（净减 984 B）、SKILL.md 8021 不变、commands-staging 8798→8789；范围外残留一条登记（fetch_sqd_transfers_v2 帮助文字，改则变采集器 sha）。
CHANGELOG.md:99:## [9.0.2] - 2026-09-19 — 口径漂移与文档-代码不符审计第二期闭环（零代码改动）
```

## 最终工作树

```text
$ git diff --stat f4f80567c21f -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md
（空输出）
$ git status --short
?? maintenance/repair-20260923-t1-spotcheck-dir-input/T1_done_attempt1_stopped.md
?? maintenance/repair-20260923-t1-spotcheck-dir-input/T1_red_evidence.txt
```

禁读路径披露：未读取 ~/.codex/（含 memories），未读取 archive/、blind-reviews/、.staging_*、references/attic.md 内容、其他历史 maintenance 目录、Desktop 或 Documents。无禁读路径读取。
