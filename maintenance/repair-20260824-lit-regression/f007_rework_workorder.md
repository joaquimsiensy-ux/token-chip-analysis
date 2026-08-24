# 工单 F-007 返工（round 2）：修正 sol-anchor-rows 豁免映射（fresh 会话可独立执行）

一句话目标：消化盲审 round1 唯一 BLOCK 项——sol-anchor-rows 的「锁仓/销毁」不得豁免（其生产端 build_evolution.py 把它计入 total 堆叠），按最小清单五条返工。

## 工单勘误（先读）
原工单 f007_workorder.md 第二步不变量中"`sol-rows`/`sol-anchor-rows`→豁免集 `BURN_EXEMPT_KEYS`"一句**事实错误**：该归并未核 sol-anchor-rows 的真实生产端。正确事实（盲审 round1 核实）：
- sol-anchor-rows 生产端=`scripts/solana/build_evolution.py:177-183`：「锁仓/销毁」写进 camp_raw、计入 known、散户=TOT−known、全桶除以 TOT 输出 → **「锁仓/销毁」参与 total-supply 堆叠，不得豁免**；
- 生产端不输出 `burn_cum_pct` → anchor 序列出现该键=数据链非法，显式拒。
其余原工单条款（EVM/sol-rows/手填/禁改边界）不变。

## 【开工门禁】
- 仓库：/Users/uravvv/.claude/skills/token-chip-analysis；分支 `fix/lit-regression-v6522`
- `git status --short` 应可见 F-007 round1 未提交改动（camp_series_provenance.py / state_from_facts.py 修改＋test_lit_regression_f007.py 新增）——在其上继续，不还原

## 第一步：独立核实
逐项核 build_evolution.py:177-183 的上述语义（属实/不属实＋理由进 done 增补节）；并 rg 确认没有其他 series_format 生产者被归并错误波及（SERIES_FORMATS 四值逐一有生产端依据：evm-dict=replay_pass2/replay_duck、sol-rows=replay_edges、sol-anchor-rows=build_evolution、evm-entity-dict=实体序列不走本闭合路径则说明依据）。

## 第二步：施工（盲审最小清单五条，逐条闭合）
1. `stack_exempt_for("sol-anchor-rows")` 改为**空豁免集**（全桶参与堆叠）；anchor 序列含 `burn_cum_pct` → 显式拒（与 evm-dict legacy 拒法同族，错误信息写明"build_evolution 不输出该键"）。
2. anchor 测试改真实形态：`40+35+25=100` 必须绿；`40+60+25=125` 必须红；`burn_cum_pct` 出现在 anchor → 拒。删除旧的错误 oracle 用例。
3. 同步模块 docstring、`validate_series_payload()` docstring、`stack_exempt_for` 注释：sol-anchor-rows 一行的语义依据改为 build_evolution.py 行号，**不得再用 replay_edges.py 证明 build_evolution.py 的语义**。
4. `f007_done.md` 增补"round2 返工"节：勘误说明＋改动前后对照＋归因（工单事实错误+施工方未独立核实 anchor 生产端）；不改写 round1 原文（历史记录不改写，增补节澄清）。
5. 重新生成绿证：全部 F-007 测试（含新 anchor 用例）＋五组定向回归（test_repair_batch_c.py、test_a4_gate.py、test_sqd_consumer_v4.py、test_state_from_facts.py、test_audit_release_gate.py）重跑，原始输出（含 EXIT_CODE）覆盖式写入 `f007_green_evidence.txt`（round1 绿证已被本次改动作废；红证 f007_red_evidence.txt 不动）。

## 边界
- 白名单：scripts/lib/camp_series_provenance.py、scripts/tests/test_lit_regression_f007.py、本工程档案目录。
- **本轮禁改**：scripts/report/state_from_facts.py（round1 改动已定型）；scripts/solana/build_evolution.py（生产端，只核不改）；原工单全部禁改文件照旧。
- 不 commit、不联网；工单外发现只记录。
