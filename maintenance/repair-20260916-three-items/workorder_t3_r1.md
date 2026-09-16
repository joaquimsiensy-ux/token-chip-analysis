# 工单 T3-r1 v2（返修单；v2 融合 codex 复核 `t3_r1_review_reply.txt`：验收基线改为返修开始时工作树、报告文件列入白名单、§2.4 措辞；出处：codex 盲审 `t3_blind_reply.txt` 第 8 项 P2 阻断＋非阻断建议）：测试审计钩子补齐"相对路径写 open 不得静默跳过"

> 主工单 `workorder_t3.md`（v5.1）全部条款继续有效；本单只补一处测试监测器缺口与一处证据文件勘误。**生产代码 `scripts/report/handoff_manifest.py` 一字不改。**

## §0 白名单（只允许改这两个文件；另允许**新增**一份施工报告 `maintenance/repair-20260916-three-items/t3_r1_done.md`）
- `scripts/tests/test_handoff_manifest.py`：仅限 `test_t3_readonly_queries` 内嵌包装脚本的 `hook()` 函数 `open` 分支（约 :729-735）与 `selftest` 合成事件段（约 :758-770）＋对应 `check(...)` 断言（:784-787）。其他既有函数与其他六组子测不动。
- `maintenance/repair-20260916-three-items/t3_scope_evidence.txt`：删除"新增函数 add_path/discover/add_explicit/bound_ref"四行（它们在 HEAD 已存在，属报告笔误；不改工具输出格式）。

## §1 缺口（已由盲审用真实事件核实）
`open` 审计事件参数只有 `(path, mode, flags)`，不带 `dir_fd`。`os.open(rel, flags, dir_fd=fd)` 触发的事件里 `path` 是相对路径，钩子当前固定传 `belongs(path, None)`，按进程工作目录解析，会把案内写入判成案外并静默丢弃，违反主工单 §5 ⑦"无法归属的写事件记为'未归属写事件'，不得静默跳过"。

## §2 修法（最小；只改测试）
1. `hook()` 的 `open` 分支：判定为写事件后，若 `path` 不是 `int` 且 `os.fsdecode(path)` 不是绝对路径（`os.path.isabs` 为假），**不做归属判断**，直接 `events.append({'event': 'open', 'args': repr(args), 'scope': '未归属写事件'})` 并 `return`。绝对路径与 fd 路径逻辑不变。
2. `selftest` 段追加一例合成事件：`sys.audit('open', 'probe_rel', None, os.O_WRONLY | os.O_CREAT)`（相对路径、整数 flags）。放在现有最后一例 `os.rename` 源端之后。
3. `check(...)` 断言相应调整：`len(alarms) == 8`；新增 `alarms[7]["event"] == "open" and alarms[7]["scope"] == "未归属写事件"`；原有 `alarms[:3]` 事件序列与 `alarms[4]["scope"]` 断言保持。check 文案末尾追加"/相对路径"。
4. 正例命令的"日志为空"断言不变——生产段用 `safe_case_file` 返回的绝对路径且为默认读模式 `open`（:1415、:1576），不应触发新规则；若触发则保持 FAIL，不得放宽断言（"未归属"不证明案内写入，但正例出现任何写事件都须查明）。

## §3 完成标准
- **基线**：施工开始前先记快照 `git status --porcelain` ＋ 白名单外全部已改/未跟踪文件的 `shasum`（工作树此时已含 T3 主工单四个 M 文件与 t3_* 证据，它们不是本单改动）。验收＝施工后与该快照比：只有 §0 两个文件内容变化、只新增 `t3_r1_done.md`；`git diff HEAD -- scripts/report/handoff_manifest.py references/ | shasum` 施工前后完全一致（生产代码与文档零增量）。
- `python3 -B scripts/tests/test_handoff_manifest.py` exit 0，PASS 计数（由测试末尾汇总行输出）= 283（本单只改既有 `check` 的断言内容，不增条数；若实现上拆成新 check 则如实报告新计数并说明）。
- `t3_r1_done.md` 记：改动行号、测试退出码与 PASS 数、施工前后快照比对结果与生产 diff shasum。不 commit；不动 CHANGELOG/VERSION/pyproject。
