# 工单 F07 复核提示词（只读，r1）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260917-p0-four/` 以外的历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`（统计大小只用 stat）。
2. 只读、离线、不 commit、不改任何文件。报告全文打印到 stdout，首行固定为 `# 工单F07复核：通过` 或 `# 工单F07复核：退回`。退回时逐条给出：编号（F07-R1-NN）、工单位置、事实（附 `grep -n -F` 或代码原文）、修订建议。通过时也要列出你实际核过的项。
3. 这是对**修复计划**的复核，不是攻击式验收：目标是拦住工单里"想得不周"的地方——锚点错、修法有副作用、既有测试会变红、同族入口漏了、迁移代价没说清。

## 任务
复核 `maintenance/repair-20260918-p0-f04-f07/workorder_F07.md`（v1）。工作目录＝本仓库根（HEAD 含本工程工单 commit；`scripts/` 与 311e6c4 逐字节相同，行号按 311e6c4 核）。逐项核：
a) §2.1/§2.2/§2.3 每个锚文本 `grep -n -F` 恰 1 处且行号一致（`audit_release_gate.py` :1074/:1077/:1094/:1097-1103/:1104/:1112/:1113/:1132/:1147/:1179-1191/:1192/:1201-1204；`replay_duck.py` :405-410；`test_audit_release_gate.py` :977-999/:1001-1014/:1129-1154，以及 `^REPO` 常量与用例 6 的"多份"断言行）。注意 `:1192` 锚 `    items = fu.get("inputs")` 须限定在 `check_daily_peaks` 内核唯一性。
b) 修法正确性与副作用：①`_find_peaks_dirs` 四文件名 rglob 的性能（大案目录 rglob 四次）与过滤规则是否与原函数等价；②"有目录但缺 summary"拒——是否存在合法场景：案内只有 `trigger_days.json` 或 `channels.json` 之类同名文件出现在非 peaks_daily 目录（例如 `data/` 下另有 `trigger_days.json`）会被误判为峰值产物目录？`grep -rn "trigger_days.json\|needs_block_precision.json\|block_precision_followup.json" scripts/ references/` 列出所有生产者/消费者，判断是否只有 peaks_daily/replay_duck 产出这三个名字；③`channels` 按 basename 在案内 rglob 恰 1 个——真实案（APU 0801 路径见 `maintenance/repair-20260917-p0-four/D_done.md`）channels 文件是否在案内、是否唯一；夹具 `channels.json` 名字是否与既有夹具里其他文件冲突；④`producer.sha256` 绑定仓库当前 `replay_duck.py`：`test_engine_equivalence.py:257-313` 真跑 `--only-addrs` 的收据是否含 producer 且 sha 为当前文件（应是）；⑤`count` 检查在 addresses 非 dict 时是否被跳过。
c) 回归面：r09 既有 13 例用更新后的 `_r09_followup`（含 channels.json 写入）是否仍绿，尤其用例 4/5/10/11/12/13 各自对夹具的改写是否与新增字段冲突；`test_repair_batch_d.py`、`test_batch15_three_ledgers_frozen.py`、`test_stage2_closeout.py` 有无自带 peaks 产物夹具。
d) §2.3 新用例 14–20 的 RED/GREEN 在基线与改后是否成立（沙箱允许则实跑 `python3 -B scripts/tests/test_audit_release_gate.py`，否则静态推演注明）。
e) §0.4/§0.8/§1/§4 是否自洽；`invariant_manifest.json` 对 `block-precision-followup/v1` consumer 的登记（`:75`/`:479`）是否需随本改动更新；`minimum_counts` 是否受影响。
f) 有无任何一处会让 `run_all.py` 现有用例变红。
