# 施工 T1: 停工

本次未完成，停在 A 段 RED 之后、生产代码修改之前。不是锚点不一致：工单锚点均匹配。阻断来自既有测试执行路径与明确禁读纪律冲突。

## 基线与核锚

- 仓库：当前独立克隆；分支 `fix/three-items-20260916`。
- HEAD：`ea11a6dfb7a1d123e2f1d74183fb13fc0c9aee5d`；开工 `git status --short` 为空。
- 工单全文已读；指定行号与锚文本用 `nl -ba` 核对一致，详见 `t1_anchor_check.txt`。

## 阻断证据

`handoff_manifest.py:201–207` 的 `git_sha` 会通过 `git -C <展开后的目录> rev-parse --short=12 HEAD` 读取对应安装目录的 Git 元数据。`cmd_generate` 的 414–415 行无条件分别传入 `~/.claude/skills/token-chip-analysis` 和 `~/.codex/skills/token-chip-analysis`。前者在工单中禁止触碰，后者在用户纪律中明确禁止读取任何文件。

A 段既有全量测试包含 generate，B 段与 run_all 同样会走该路径。未执行这些 generate 调用。没有读取上述目录，也未修改 `git_sha` 或给生产代码添加跳过逻辑。

尝试通过 macOS `sandbox-exec` 额外禁止读取这些目录，仅用 `/usr/bin/true` 探测可用性；exit 71，原文 `sandbox-exec: sandbox_apply: Operation not permitted`。因此该隔离方案在本执行环境不可用。完整命令保存在 `t1_anchor_check.txt`。

恢复施工需要具备可强制禁读这些目录的测试环境，或在工单中明确允许测试层隔离安装目录 Git SHA 探测。当前没有擅自加入此测试行为变更。

## 已完成的 A 段 RED

准确命令、退出码、stdout/stderr 原文、测试与生产文件 SHA256 均在 `t1_red_evidence.txt`。

1. 独立调用 `test_members_sidecar_contract`：exit 1。模板键/旁车契约 FAIL；非法旁车目录拒绝契约 FAIL；两个模板命令各自的新台账与 force 旧台账保护共四案，因为旧代码缺少 `write_members_sidecar`，捕获 AttributeError 并记录 FAIL，未提前中止其他独立用例。
2. 修改 fill_all 联动读取后单独执行：exit 1，记录预期 FileNotFoundError。未声称其后既有用例已运行。
3. `python3 scripts/tests/test_distribution_gate.py`：exit 1。此前 29 项通过，在新增“distribution-template 旁车在场”断言 FAIL 后返回；后续用例未执行。

尚未进行生产修改、A GREEN、B RED/GREEN、C RED/GREEN、docs_lint 或 run_all。没有全套结果行，不应将本次记录视为完成或验收通过。

## 已改动文件

- `scripts/tests/test_adjudication_validator.py`：新增旁车独立契约用例、旁车联动读取、旧台账兼容用例；独立契约挂入 main 首次 fill_all 之前。
- `scripts/tests/test_distribution_gate.py`：改为旁车读取，新增存在性与源候选成员集合一致性断言。
- `maintenance/repair-20260916-three-items/t1_capture.py`：命令、退出码、原始输出、SHA256 的证据采集器。
- `maintenance/repair-20260916-three-items/t1_red_evidence.txt`：已执行的三次 RED 原文。
- `maintenance/repair-20260916-three-items/t1_anchor_check.txt`：核锚、未改生产/文档哈希、阻断代码与沙箱探测记录。
- 本停工报告。

生产文件、test_handoff_manifest.py、文档均未修改。现有测试断言未改，新增兼容用例和集合一致性断言尚未跑到。保留当前测试施工进度，不回滚、不提交。

## 文档字节数

| 文件 | 改前 wc -c | 停工时 wc -c |
| --- | ---: | ---: |
| references/split-run.md | 28162 | 28162 |
| references/scan-schemas.md | 104942 | 104942 |

## 差异与遗留

- 工单没有指定如何隔离 generate 的两侧安装目录 Git SHA 探测；本次因此在生产修改前停工。
- A 剩余生产实现及全部 GREEN、B、C、run_all、最终 t1_done.md 全部待完成。
- 本次无网络调用、无 Git 写操作、无 commit；工作树修改仅在白名单内。未生成表示完成的 t1_done.md。
