# W1 施工报告（2026-09-25）

状态：代码与验证记录完成；专项测试、版本一致性及预提交三检通过。全量 149/152，3 项环境失败；Git 写权限阻断提交，尚未满足“全过后 commit”的完整交付要求。

## 范围与裁决

- 依据 `workorder_W1.md` 正文 v2 施工；`review_W1_reply_r1.md` 中调度方标注采纳的八条全部按融合后的工单落实。
- 本轮动手前 `git status --porcelain=v1` 为空；起点为 `84006ae1ae2a7d156c563bdd67ad0022a4bf7291`。
- 仅修改工单允许的八个文件：CLI、新测试、SUITE、版本四处及本报告。未联网、未读取真实案目录、未主动删除文件；测试自行清理合成临时目录。
- `references/`、`commands/`、resolver、其他消费者及 `--unseal` 路径均未改动；后续出口已由调度方登记在本目录 README，无需重复修改。

## Diff 摘要

- `scripts/labels/label_lookup.py`：新增 `serial_marked(row) -> bool`。严格布尔 True、规范化 category、风险旗标、来源分项四条判据精确匹配；字符串风险复用既有解析器，list 逐项处理，非空非法类型保守封存。盲化过滤分支改用此函数；封存格式、单链 misses、跨链不增加 misses 的逻辑保持原样。模块说明限定为“不含惯犯标记的设施行不受影响”。
- `scripts/tests/test_label_blind_seal.py`：30 个纯函数正反例、5 个临时 CSV 黑盒 CLI 场景，共 6 个 unittest 方法。
- `scripts/tests/run_all.py`：显式加入新测试，SUITE 151→152。
- `VERSION`、`pyproject.toml`、`SKILL.md` 第 23 行版本注释、`CHANGELOG.md` 顶部索引与首个详情条目：9.2.0→9.2.1。SKILL 正文及历史版本记录未改。
- CHANGELOG 写明整行封存混合行的代价：A2–A3 暂时隐藏设施身份、no_merge、exclude 及其他有效标签，A4 揭盲恢复；历史标记不代表当前确为惯犯。其他消费者另单处理。

## 测试用例与实际输出

纯函数 12 正例：严格 True；类别单独命中及带空白；serial=False 但风险命中；多旗标及空白；list；来源单独命中及空白；非空 dict、整数、tuple。18 反例：缺字段、干净设施、False、整数 1/字符串 True 不冒充布尔 True、相似类别、空类别、风险 None/空串/仅分隔空白/空 list、list 与字符串相似子串、来源相似子串及空值。

5 个集成场景：`--blind-serial --json`、`CHIP_BLIND_SERIAL=1` JSON、盲化文本、非盲化 JSON 对照、`--chain all` JSON。每次独立临时 labels 与 sealed 目录；断言 exit 0、混合行只有 chain/address/hit:false、干净设施仍命中、原始信息与 serial=False 完整封存、封存详情不进入 stdout；非盲化恢复混合行命中，跨链不生成混合行 misses。

修复前运行新测试：4 个 CLI 场景 FAIL，非盲化对照 PASS；30 个纯函数 subtest 因函数尚未新增而 ERROR。实际结尾：

```text
Ran 6 tests in 0.209s
FAILED (failures=4, errors=30)
```

修复后 `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_label_blind_seal.py`，exit 0：

```text
test_all_chains_keeps_existing_no_miss_behavior ... ok
test_blind_environment ... ok
test_blind_json_flag ... ok
test_blind_text ... ok
test_nonblind_control ... ok
test_structured_markers ... ok
Ran 6 tests in 0.267s
OK
```

版本一致性与预提交三检，exit 0：

```text
PASS: M-03 version metadata consistent at 9.2.1
[pre-commit] changelog_lint...
PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 88 条 + 归档 139 条
[pre-commit] docs_lint...
PASS: 45 个文档，引用无断链、粗体配对完整
[pre-commit] env_check...
PASS: 21 个直接依赖逐项满足 pyproject→lock→installed；Python 3.14.6 满足 requires-python >=3.14
[pre-commit] 三检全过
```

`git diff --check`：exit 0，无输出。范围检查通过：工作树恰好八个允许文件变更，无删除项；SKILL 内容与 HEAD 相比仅版本元数据注释变化。

## 全量验收与基线

- 对照基线：CHANGELOG 9.2.0 的调度方记录为 150/151；唯一环境红项 `test_stage2_reseal.py`，原因“验收 worktree 缺失；须调度方预建”。本单不创建该外部验收 worktree，也不改该测试。
- 修复后的完整验收命令：`PYTHONDONTWRITEBYTECODE=1 python3 -u scripts/tests/run_all.py`，日志 `/private/tmp/W1_final_20260925.log`；exit 1，152 项中 **149 PASS / 3 FAIL**。没有跳过 SUITE 条目。
- 两项当前沙箱环境失败：`test_batch3_solana_vertical_slice.py:625`、`test_batch3_evm_vertical_slice.py:283` 创建 `ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)` 时，`socket.bind` 抛出 `PermissionError: [Errno 1] Operation not permitted`。两项都未改动，未尝试放宽测试或绕过端口权限。
- 第三项为已登记环境红项：`test_stage2_reseal.py` 内部 20/21 PASS，`dry_run_touches_nothing` 因“验收 worktree 缺失；须调度方预建”失败。未创建或读取真实案目录，也未创建该外部验收 worktree。
- 附加运行说明：曾在生产修改前启动额外 `run_all.py`，日志 `/private/tmp/W1_baseline_20260925.log`。耗时较长，停止进程组被系统以 Operation not permitted 拒绝；随后生产代码已修改，因此该运行不作为纯净基线，正式验收以修复后新启动的完整运行结果为准。
- 该附加运行已完成：exit 1，151 项中 148 PASS / 3 FAIL。失败为上述两项本地端口权限错误，以及 `test_stage2_reseal.py` 的 `dry_run_touches_nothing: AssertionError: 验收 worktree 缺失；须调度方预建`（该测试内部 20/21 PASS）。完整运行期间未跳过 SUITE 条目；此记录用于说明当前环境差异，不冒充全部通过。
- 逐项比较两轮汇总：151 个共同条目的 PASS/退出码完全一致；唯一新增项 `test_label_blind_seal.py` 为 PASS。相对调度方 150/151 的历史记录，多出的两项失败均为当前沙箱本地端口权限限制；未发现本单新增失败。

正式运行实际汇总摘录：

```text
FAIL(rc=1)  test_batch3_solana_vertical_slice.py (无输出)
FAIL(rc=1)  test_batch3_evm_vertical_slice.py (无输出)
      PASS  test_label_blind_seal.py (无输出)
FAIL(rc=1)  test_stage2_reseal.py    stage2_reseal: 20/21 PASS
3 项失败——修完再收工
```

新测试使用 unittest 向 stderr 输出，因此 run_all 的 stdout 尾行显示“无输出”；其六项完整输出已在上节记录。

## 只登记的文档矛盾

`references/analyze-workflow.md:88`：将盲化命中限定描述为 serial-actor，并笼统写“设施类标签照常输出”；与本单混合设施行整行封存的判据不一致。按工单仅记行号，未改正文。

## 提交

commit 哈希：无（未提交、未 push）。暂存本单七个代码/版本文件时，`git add` exit 128：

```text
fatal: Unable to create '/Users/uravvv/.claude/skills/token-chip-analysis/.git/index.lock': Operation not permitted
```

当前会话 `.git` 只读，无法暂存或提交；未绕过沙箱、未使用其他仓库伪造提交。计划中文提交信息：`修复标签盲化混合行漏封并升级至9.2.1`。需恢复本仓库 Git 写权限后，在全量验收结论符合工单的前提下完成提交。

## 调度方补记（2026-09-25，Fable）

- codex 沙箱 `.git` 只读无法提交，代码/版本七个文件由调度方原样提交：**commit `e1fa33f6a4c65cd1edfe9823ec956d6edbcbff7f`**（父提交 84006ae）。提交前 `git diff --stat` 核对只含工单允许的六个修改文件加一个新测试文件。
- 本机补验 codex 沙箱端口权限失败的两项：`test_batch3_solana_vertical_slice.py` rc=0、`test_batch3_evm_vertical_slice.py` rc=0。
- 本机全量 `run_all.py`（MPLCONFIGDIR=~/.matplotlib）：152 项中 151 PASS，唯一 FAIL=`test_stage2_reseal.py` dry_run_touches_nothing「验收 worktree 缺失」，与 9.2.0 基线同一环境项。日志在调度方 scratchpad `W1_runall_fable.log`。
- 本机 `test_label_blind_seal.py` 6/6 OK、`test_version_consistency.py` PASS 9.2.1。
