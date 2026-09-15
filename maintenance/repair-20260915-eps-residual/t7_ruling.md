# T7(PYTHIA 对表)调度方裁决 · 2026-09-15

## 停工原因(codex 首派提问,成立)
`scripts/tests/fixtures/pythia_anchors.json` 的 `provenance_v2` 段只记了 `run_params.edge_budget=5000000`,
没有实体成员、标签、W1 名单;且该段自声明"v6.8.1 历史诊断,因 Solana 5 元组缺 tx/instruction 精确顺序
已失去发布资格,禁止引用为当前稳定结论"(`_note_v2`),`sensitivity_stable=false`。
PYTHIA 案卷从未生成过 7.0.x 溯源账本;其 DuckDB `edges` 表只有 5 列(ts, slot, f, t, amt),无 tx/instruction 序号。
因此"与 provenance_v2 锚点逐项相等"在前提上不可达,与 7.0.4 改动无关。

## 裁决:T7 改为"同输入双版本对照",不与 fixture 锚点比对、不更新 fixture
1. 输入(已预置,先校验 `cd .staging_eps/pythia && shasum -a 256 -c STAGING_SHA256_pythia_extra.txt` 2 项 OK;
   `s2_work.duckdb` 在原 `STAGING_SHA256.txt` 中):
   - `--duckdb .staging_eps/pythia/s2_work.duckdb --edges-table edges`
   - `--entity-file .staging_eps/pythia/entity_file_flat.json`(由案卷 `s2_entity_members.json` 的 `entities.*.members*` 列表平铺而成,7 实体 102 址,跨实体无重复;原文件同目录留档)
   - `--total-supply 998158041739995`(fixture `total_supply_raw`)
   - `--allow-no-labels`(PYTHIA 案无 `{addr:{kind,name}}` 标签文件;探索模式,ledger 标 exploration,本项只做 trace 不做 freeze)
   - `--edge-budget 5000000`(fixture `run_params`),其余参数取默认;`--out` 指向隔离副本目录,案根即该目录
2. 用 7.0.3 基线(`git show HEAD:scripts/report/entity_source_trace.py` 落到临时文件,PYTHONPATH 指向 scripts/report)与 7.0.4 工作树版本,对**完全相同**的命令各跑一次,记录:退出码、stderr 尾、若 exit 2 记阻断原因原文。
3. 断言(写入 `pythia_regression.md`,只记数字不记结论):
   - 两版退出码相同;若 exit 2,阻断原因文本相同(order_ambiguous 超 0.5% 属预期,是 5 元组数据的固有结果,与本次改动无关);
   - 若账本落盘:按实体×锚点×终点键对齐,T4 不变量全部成立(`stock_raw` 相同、Σraw 相同、除 data_gap/fp_residual 外每条 raw 相同、`data_gap(7.0.3) == data_gap(7.0.4) + fp_residual(7.0.4)`);逐实体记录 `data_gap_events` / `fp_residual_events` 前后值;
   - 与 fixture 的 `q1_peak_anchor.simulation.data_gap_events=2191` 只做**信息性**并列记录(不同实体口径、不同版本,不作断言)。
4. `pythia_anchors.json` **不改**;`fixtures_lint.py` 须仍绿。
5. 若 trace 在两版下都因预算/顺序问题 exit 2 且未落账本,则 T7 证据 = "两版行为一致(退出码+原因)",在 done.md 明写"T7 数量不变量未能在 PYTHIA 上取证,由 T6 APU 全量 105 实体承担",不得静默。
6. 运行时长不设上限但须落日志到 `maintenance/repair-20260915-eps-residual/pythia_run_703.log` / `pythia_run_704.log`;不要读 `/Users/uravvv/Documents`。
