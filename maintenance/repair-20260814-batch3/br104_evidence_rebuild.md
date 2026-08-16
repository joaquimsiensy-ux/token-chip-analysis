# BR1-04 证据重建记录（裁判亲自处置，不假手施工方）

盲审 finding BR1-04（P2）指出批 3 的基线证据与完工宣称存在漂移。裁判逐条复验属实，处置如下。

## 1. 基线日志重建

- **新基线**：`baseline_run_all_83394ab.log`——在 `83394ab`（批 3 exact parent）的临时 worktree 上全量重跑产出，文件头部带 commit SHA、命令、日期、cwd。结果：**97 项全绿 rc=0**，零 evmobs 项。CHANGELOG 6.43.0 条目"main@83394ab 97 项全绿 rc0"的宣称自此有真凭据。
- **旧 `baseline_run_all.log` 定性 STALE**：该文件如实记录了开工时工作区的 98 项实测——当时主工作区检出在 evmobs 分支 tip 411bf18，且含未跟踪的并行测试 `test_evm_observation.py`（第 99 行可见）。其内容真实，错的是"main@83394ab 基线"的名分。按"历史记录不可为守卫改写"纪律，文件保留原样不改写、不删除；今后引用基线一律以 `baseline_run_all_83394ab.log` 为准。

## 2. 完工记录宣称修正（原 done 文件不改写，此处为修正记录）

- **`workorder_F01_done.md` 的 invariant 计数**（59/77/63/52）：系 rebase 剥离前、含 evmobs 并行改动的工作区实测值，不能代表批 3 分支。批 3 收口刀（1da3f22）实测为 57/76/62/51/58；消化轮 1 落地 `review-ledger/v1` 后为 58/78/62/51/58（producer/consumer 各 +1/+2）。以每次 `invariant_scan.py` 当次输出为准。
- **`workorder_F01_done.md` 与 `workorder_closeout_done.md` 的"git diff --check 无空白错误"宣称**：范围过宽，实测 `git diff --check 83394ab..HEAD` 在旧 baseline log 内报 2 处尾空格（`baseline_run_all.log:43,61`，系 run_all 原始输出保真，非代码文件）。修正口径：**代码与文档文件无空白错误**；证据 log 文件的原始输出尾空格如实保留，不为守卫清洗。

## 3. 先红时序的定性

盲审正确指出：测试与修复同 commit 落盘，git 历史无法独立证明"先红"时序，done 文件中的先红清单属自报证据。本批如实接受该定性，不冒充可独立验证；消化轮 1 起，先红复现脚本落 `/tmp` 且 done 文件记录 HEAD 现象原文，性质仍为自报留档、供盲审抽查复跑。

## 4. candidate 日志计划

candidate 全量日志须绑定最终 HEAD 才有意义。计划：盲审 Round 2 通过、closure 收尾后，在合并前的最终 commit 上产 `candidate_run_all_<sha>.log`（同样带 SHA/命令/日期头）一次性存档。
