# W3 v18 调度方验收记录（Fable，2026-09-16）

按工单 `workorder_w3.md` §E 逐项亲跑。施工件由 codex 交付（见 `w3_done.md`）；本记录只写验收。

## 验收环境

- 主仓库 `~/.claude/skills/token-chip-analysis` HEAD `c897ecd`，工作树含 12 件未提交施工件。
- 验收 worktree `/tmp/w3_acceptance`（detached `c897ecd`，调度方预建，codex 叠加 12 件施工件）；验收前逐件 sha256 与主树相等（`w3_red_evidence.txt` 除外，它在续跑期间被追加）；`scripts/` 下无 `__pycache__`。
- 钉版对照：scratchpad worktree `wt_764b60c`（7.0.4）。W2 版对照：`git archive 82bb26c scripts references VERSION` 导出到 scratchpad `x_82bb26c`（非 worktree）。
- 真实案卷一律只读：FORGGIE/APU 直接跑只读命令并做跑前跑后快照；MELANIA/COLLECT/LIT 因 `check` 会写收据，改在 `rsync --link-dest` 硬链接副本上跑。
- 全程 `PYTHONDONTWRITEBYTECODE=1`；主仓库 `scripts/` 缓存已按用户裁决清空。

## 1. run_all 全套

- codex 沙箱内那份：pid 90935，`/tmp/run_all_w3.log`，结果由 codex 写入 `w3_done.md`（端口两项预期 PermissionError）。
- 调度方本机那份：在 `/tmp/w3_acceptance` 跑 `python3 -u -B scripts/tests/run_all.py`，pid 11989，日志见本文末尾附录 A。

**结果（两份互补，合计每项至少一处全绿）：**

| 份 | 运行处 | 结果 | 失败项与根因 |
|---|---|---|---|
| 调度方本机 | 验收树 `/tmp/w3_acceptance` | 149 PASS / 2 FAIL → 复跑后 **151/151** | `test_sqd_gap_repair.py`、`test_batch8_repair_scale.py` 均 `FileNotFoundError: .staging_b3/routeA_pilot/426649168.json.gz`：该目录被 `.gitignore:24`（`.staging_*/`）忽略，`git worktree add` 不带 ignored 文件。把主仓库该目录复制进验收树后两项单跑 rc=0（原文在附录 A 日志末尾）。跑后 `scripts/` 无 `__pycache__`，`git status --short` 仍为 12 件施工件。 |
| codex 沙箱 | 主仓库 cwd，pid 90935，`/tmp/run_all_w3.log`，08:38:58 退出 | 148 PASS / 3 FAIL | ①②`test_batch3_solana_vertical_slice.py`、`test_batch3_evm_vertical_slice.py`（无输出）＝沙箱禁绑本地端口，工单 §E 已预期；本机验收树同两项 PASS。③`test_stage2_reseal.py` 20/21：`dry_run_touches_nothing` 报 `白名单外变更 ['maintenance/repair-20260915-stage2-closeout/w3_acceptance_fable.md']`——调度方在主仓库同时新建本记录文件，被该用例的仓库树前后快照捕获；验收树同用例 21/21 PASS。属并发验收动作碰撞，非代码缺陷。 |

结论：W3 新增 `test_stage2_reseal.py` 21/21，SUITE 151 项在验收树全绿；codex 那份的三项失败各有环境原因且在本机验收树反证通过。

## 2. FORGGIE 已发布案发布闸（预期：钉版 PASS，HEAD BLOCK 且只因扫描器语义）

命令：`audit_release_gate.py --profile new-analysis --report <案根>/报告.md <案根>`（`--report` 按当前目录解析，须绝对路径）。

钉版 764b60c，exit 0：
```
PASS: new-analysis 必经发布门禁全部通过
```

验收 worktree（HEAD＋施工件），exit 2：
```
BLOCK: 独立复核发布硬闸未通过
- 持仓分布 initial scan: scan 语义与独立重算不一致
- A5 seal 重验: A5 seal 分布终态不可重验: 终态 final scan 重验失败: scan 语义与独立重算不一致
```

两条错误均为"scan 语义与独立重算不一致"，即 W1 改扫描器后旧案钉版机制生效，与工单预期一致，不是 W3 回归。案卷跑前跑后快照（全文件 sha 汇总 / 目录清单汇总）：`254370b753b60b89 ddeb00207ae7d33e` → 相同。

## 3. 三册手册字节与文档检查

```
   27804 references/split-run.md
   34333 references/analyze-workflow.md
   42499 references/report-template.md
  104636 total   （≤ 104962；report-template.md 未改）
```
- `docs_lint.py --all`：`PASS: 59 个文档，引用无断链、粗体配对完整`。五枚契约针（CT-WAVE-16/17/18、CT-DISTRIBUTION-15/16）由 docs_lint R-02 规则校验 required needle 闭合，在 `contract_manifest.json` 各 1 条。
- `changelog_lint.py`：PASS，活跃 72 条＋归档 139 条。
- `test_version_consistency.py`：`PASS: M-03 version metadata consistent at 7.1.0`。VERSION / pyproject / SKILL.md 标记 / CHANGELOG `[7.1.0] - 2026-09-16` 一致。

## 4. `stage2_closeout --help`

```
usage: stage2_closeout.py [-h] {check,fill-workorder,amend,reseal} ...
```

## 5. MELANIA / COLLECT / LIT 原案 `check` 回测（不回归）

做法：每案建硬链接副本，在同一副本上先后用 W2 版（82bb26c）与 W3 版（验收 worktree）跑 `stage2_closeout.py check --case-dir <副本> --report 报告.md`，比较 stdout 与 exit；每次跑完把生成的 `stage2_closeout_receipt.json` 移出副本。三案两版 exit 均 2，stdout `diff` 均 0 行，副本无临时残留。老案缺 W2 起要求的产物（工单/whale_series 等）故 BLOCK，与 W2 同——"不回归"指两版判定逐字一致。

W3 版输出原文：

LIT分析：
```
BLOCK: release_gate_dryrun
  共享发布 receipt: EVM accounting observation bundle file invalid or escapes case root
  记账模型公共 validator 未通过: EVM accounting observation bundle file invalid or escapes case root
  受控对账公共深验失败: reconciliation wrapper producer/runner is not current repository script
  持仓分布 initial scan: scan 语义与独立重算不一致
  允许 A5 缺席；在场 A5 仍由 check_formal_case_chain 核 chain。不装载 claim_registry.json，check_claims 不执行，claim_types 为空，historical-chart 检查跳过。dryrun 的 report 参数只检查非 None；报告内容与 sha 由 closeout #2/#5/#6/#7/#10/#11 承担
PASS: a4_seal_integrity
PASS: downstream_stale
  {"item": "adversarial_review.claim_registry", "expected": "e0304faf487ec2315d4182d4059b8ebe58428d5652a5cb972aaf245785b3d60d", "actual": "e0304faf487ec2315d4182d4059b8ebe58428d5652a5cb972aaf245785b3d60d", "status": "ok", "fix_order": "freeze → A4 register/finalize → 受影响复核路 → runner finalize → shared_release_receipt → rounds → A5"}
  {"item": "shared_release_receipt.adversarial_review", "expected": "db2d4f51a75573c74b91bbb533c9a295bed165a6f1d1b12552b4c8f4e0c5c510", "actual": "db2d4f51a75573c74b91bbb533c9a295bed165a6f1d1b12552b4c8f4e0c5c510", "status": "ok", "fix_order": "freeze → A4 register/finalize → 受影响复核路 → runner finalize → shared_release_receipt → rounds → A5"}
  {"item": "rounds.a4_seal_sha", "expected": "6fdecd64974098873fd4004933a4886810def7e2bc72de5d6ea7d4c994b080c5", "actual": "6fdecd64974098873fd4004933a4886810def7e2bc72de5d6ea7d4c994b080c5", "status": "ok", "fix_order": "freeze → A4 register/finalize → 受影响复核路 → runner finalize → shared_release_receipt → rounds → A5"}
  {"item": "rounds.entity_freeze_revision", "expected": 1, "actual": 1, "status": "ok", "fix_order": "freeze → A4 register/finalize → 受影响复核路 → runner finalize → shared_release_receipt → rounds → A5"}
  {"item": "dormant_warehouse_audit.universe_ref", "expected": "a93a42579288385fb5e2a1e28afa53d7504f8a0a18bab31985b2ac9e285270a2", "actual": "a93a42579288385fb5e2a1e28afa53d7504f8a0a18bab31985b2ac9e285270a2", "status": "ok", "fix_order": "freeze → A4 register/finalize → 受影响复核路 → runner finalize → shared_release_receipt → rounds → A5"}
  fix_order: freeze → A4 register/finalize → 受影响复核路 → runner finalize → shared_release_receipt → rounds → A5
PASS: identity_gate
PASS: a5_provenance_flip
  status=NO_FLIPS
BLOCK: a5_distribution
  ValueError: 终态 final scan 重验失败: scan 语义与独立重算不一致
BLOCK: caption_same_source
  图注与终态 scan 不同源: private_main 期望 ['80.36%'] 未出现
  图注与终态 scan 不同源: private_dust 期望 ['0.0004%'] 未出现
  图注与终态 scan 不同源: public_facility 期望 ['19.52%'] 未出现
  图注与终态 scan 不同源: unresolved_contract 期望 ['0.12%'] 未出现
  图注与终态 scan 不同源: burn_sentinel 期望 ['1.59%'] 未出现
  存在性检查，非逐桶配对
  NOTE: 图注未披露集中度数字
NOTE: dual_basis
  未声明双口径
BLOCK: fig2_series
  ValueError: 文件不存在: 'whale_series.provenance.json'
BLOCK: workorder
  WORKORDER BLOCK: bindings.final_scan_path: 存在 path=dist_rounds/round_1/distribution_scan.json 的绑定 != []
  WORKORDER BLOCK: fig3.events: 非空 list != {'path': 'fig3_events.json', 'sha256': '810542272bbfd6f02e5db4fc49e29ff5790151ea0feed487ebe37c66e2d2ac94', 'note': '11 条判断清单（−2 选材），desc 不带编号由绘图函数自动编号；正文第五章事件清单与此一一对应'}
  WORKORDER BLOCK: bindings.price_source_checks|price_source.dual_source_check: 双源检查对象在场 != 单源 DefiLlama 日频（TGE 2025-12-30 起）；首日 $2.73/低点 $0.81/末点 $3.56 与 TGE 期媒体报道及 CMC 页面量级一致（人工旁证），无第二程序化源——如实申报
  WORKORDER BLOCK: fig3.events_input: {path,sha256} 完整且 sha256 非空 != None
  WORKORDER BLOCK: fig2.lines[0].series_source.key: entity_series 中的 key != e_proj
  WORKORDER BLOCK: fig2.lines[1].series_source.key: entity_series 中的 key != e_s1
  WORKORDER BLOCK: fig2.lines[2].series_source.key: entity_series 中的 key != e_s2
  fig2 required 下限: ['e_proj', 'e_s1', 'e_s2']
  NOTE: 未声明流通量，门槛仅按总供应判
  flow 下限: ['e_proj']；图中实体: ['e_proj']
PASS: facts_gate
  G5 疑似手写百分比（新纪律：结论性百分比一律走宏；确认为非结论数字——如价格涨跌幅/费率——可交付）: 0% 0.01% 0.06% 0.1% 0.13% 0.14% 0.2% 0.6% 0.72% 0.76% 0.80% 1% 1.0082% 1.01% 1.24%
BLOCK: −2 收口未通过
rc=2
```

COLLECT分析：
```
BLOCK: release_gate_dryrun
  共享发布 receipt: EVM accounting observation bundle file invalid or escapes case root
  记账模型公共 validator 未通过: EVM accounting observation bundle file invalid or escapes case root
  受控对账公共深验失败: reconciliation wrapper producer/runner is not current repository script
  持仓分布 initial scan: scan 语义与独立重算不一致
  允许 A5 缺席；在场 A5 仍由 check_formal_case_chain 核 chain。不装载 claim_registry.json，check_claims 不执行，claim_types 为空，historical-chart 检查跳过。dryrun 的 report 参数只检查非 None；报告内容与 sha 由 closeout #2/#5/#6/#7/#10/#11 承担
PASS: a4_seal_integrity
PASS: downstream_stale
  {"item": "adversarial_review.claim_registry", "expected": "43ad46bb23cafe596050a6170e0040ceca7296e928f9601e837372789c61b45d", "actual": "43ad46bb23cafe596050a6170e0040ceca7296e928f9601e837372789c61b45d", "status": "ok", "fix_order": "freeze → A4 register/finalize → 受影响复核路 → runner finalize → shared_release_receipt → rounds → A5"}
  {"item": "shared_release_receipt.adversarial_review", "expected": "2ed2d7d6bc6c6a6f7d5f4b9bd31436c70173ecc436faa587da42dd969c6d8d0e", "actual": "2ed2d7d6bc6c6a6f7d5f4b9bd31436c70173ecc436faa587da42dd969c6d8d0e", "status": "ok", "fix_order": "freeze → A4 register/finalize → 受影响复核路 → runner finalize → shared_release_receipt → rounds → A5"}
  {"item": "rounds.a4_seal_sha", "expected": "42c635367c15034060adeaa2cec09d7ccc36abd267ccf0e0f78a2b6d98c14dbd", "actual": "42c635367c15034060adeaa2cec09d7ccc36abd267ccf0e0f78a2b6d98c14dbd", "status": "ok", "fix_order": "freeze → A4 register/finalize → 受影响复核路 → runner finalize → shared_release_receipt → rounds → A5"}
  {"item": "rounds.entity_freeze_revision", "expected": 3, "actual": 3, "status": "ok", "fix_order": "freeze → A4 register/finalize → 受影响复核路 → runner finalize → shared_release_receipt → rounds → A5"}
  {"item": "dormant_warehouse_audit.universe_ref", "expected": "f884a9fe8e0940b724a6fa66c0cc279d94e3a76585f3068080a835b0b7a41324", "actual": "f884a9fe8e0940b724a6fa66c0cc279d94e3a76585f3068080a835b0b7a41324", "status": "ok", "fix_order": "freeze → A4 register/finalize → 受影响复核路 → runner finalize → shared_release_receipt → rounds → A5"}
  fix_order: freeze → A4 register/finalize → 受影响复核路 → runner finalize → shared_release_receipt → rounds → A5
PASS: identity_gate
PASS: a5_provenance_flip
  status=NO_FLIPS
BLOCK: a5_distribution
  ValueError: 终态 final scan 重验失败: scan 语义与独立重算不一致
BLOCK: caption_same_source
  图注与终态 scan 不同源: private_main 期望 ['15.13%'] 未出现
  图注与终态 scan 不同源: private_dust 期望 ['0.0001%'] 未出现
  图注与终态 scan 不同源: public_facility 期望 ['84.87%'] 未出现
  存在性检查，非逐桶配对
  NOTE: unresolved_contract raw=0，退化为数字存在性检查
  NOTE: burn_sentinel 极小值，退化为数字存在性检查
  NOTE: 图注未披露集中度数字
NOTE: dual_basis
  未声明双口径
BLOCK: fig2_series
  ValueError: 文件不存在: 'whale_series.provenance.json'
BLOCK: workorder
  WORKORDER BLOCK: amendments[0].before_sha256: 非空字符串 != None
  WORKORDER BLOCK: amendments[0].after_sha256: 非空字符串 != None
  WORKORDER BLOCK: amendments[0].approved_by: 非空字符串 != None
  WORKORDER BLOCK: amendments[0].exact_change: before/after 字符串 != None
  WORKORDER BLOCK: amendments[0].before_sha256: 32c6787b02a2b693746309c6d417c00fc2645c215de27ae1893d60acbfc79458 != None
  WORKORDER BLOCK: amendments[1].trigger: 非空字符串 != None
  WORKORDER BLOCK: amendments[1].approved_by: 非空字符串 != None
  WORKORDER BLOCK: amendments[1].exact_change: before/after 字符串 != 仅将 5 个 blockquote callout 标记替换为 6.52.3 build_html 支持的 > i；结论、数字、实体、图引用及其余文本零改动
  WORKORDER BLOCK: amendments[1].before_sha256: None != 08d6d648fc4df5f92ca29e54493fd953f960f3888a2e1fe69b6a7e4dae66f51b
  WORKORDER BLOCK: amendments[2].trigger: 非空字符串 != None
  WORKORDER BLOCK: amendments[2].approved_by: 非空字符串 != None
  WORKORDER BLOCK: amendments[2].exact_change: before/after 字符串 != 仅将 5 组 > i 与紧随正文合并为 6.52.3 规定的单行 > i 文字；正文字符、宏、结论、数字、实体和图引用零改动
  WORKORDER BLOCK: bindings.final_scan_path: 存在 path=dist_rounds/round_1/distribution_scan.json 的绑定 != []
  WORKORDER BLOCK: bindings.price_source_checks|price_source.dual_source_check: 双源检查对象在场 != CMC 单源（BSC 上线于 12-27，Poloniex/DefiLlama 无更早数据可交叉；自报流通量已按 self_reported_unverified 声明）
  WORKORDER BLOCK: fig3.events_input: {path,sha256} 完整且 sha256 非空 != None
  fig2 required 下限: ['e_proj']
  NOTE: 未声明流通量，门槛仅按总供应判
  flow 下限: []；图中实体: ['proj-core']
PASS: facts_gate
  G5 疑似手写百分比（新纪律：结论性百分比一律走宏；确认为非结论数字——如价格涨跌幅/费率——可交付）: 0.3% 0.52% 0.60% 0.85% 0.87% 0.90% 1.95% 10% 100% 110% 12% 12.05% 14.09% 14.73% 16.44%
BLOCK: −2 收口未通过
rc=2
```

MELANIA分析：
```
BLOCK: release_gate_dryrun
  正式发布跨分区 target 不一致: as_of_block 声明矛盾: accounting_mode.json.as_of_block=443174082, reconciliation_report.json.target.as_of_block=444429622, shared_release_receipt.json.target.as_of_block=443174082, identity_snapshot_receipt.json.as_of_block=443174082
  共享发布 receipt: solana accounting observation bundle file invalid or escapes case root
  记账模型公共 validator 未通过: solana accounting observation bundle file invalid or escapes case root
  受控对账公共深验失败: reconciliation supply receipt envelope invalid: input supply_rpc invalid: input escapes case root；存量案例须重跑对应生产者获取当前回执
  持仓分布 initial scan: scan 语义与独立重算不一致
  发布期序列 cutoff 目标: accounting as_of_block=443174082/wrapper 444429622：冻结态深验未通过，无法确定对账时点: reconciliation supply receipt envelope invalid: input supply_rpc invalid: input escapes case root；存量案例须重跑对应生产者获取当前回执
  允许 A5 缺席；在场 A5 仍由 check_formal_case_chain 核 chain。不装载 claim_registry.json，check_claims 不执行，claim_types 为空，historical-chart 检查跳过。dryrun 的 report 参数只检查非 None；报告内容与 sha 由 closeout #2/#5/#6/#7/#10/#11 承担
PASS: a4_seal_integrity
PASS: downstream_stale
  {"item": "adversarial_review.claim_registry", "expected": "9deffcfabb905a69da3fc7e8f04b1c93f6cf51e10dec5a6295e74c4a718aa527", "actual": "9deffcfabb905a69da3fc7e8f04b1c93f6cf51e10dec5a6295e74c4a718aa527", "status": "ok", "fix_order": "freeze → A4 register/finalize → 受影响复核路 → runner finalize → shared_release_receipt → rounds → A5"}
  {"item": "shared_release_receipt.adversarial_review", "expected": "f82c1317d64b255768930a0f207c99f456a5cd8292710311650ca767ecda75f3", "actual": "f82c1317d64b255768930a0f207c99f456a5cd8292710311650ca767ecda75f3", "status": "ok", "fix_order": "freeze → A4 register/finalize → 受影响复核路 → runner finalize → shared_release_receipt → rounds → A5"}
  {"item": "rounds.a4_seal_sha", "expected": "a2785b4378dfe1b9f8599f425701332304d6308d505895b530eb5bfa545e5d53", "actual": "a2785b4378dfe1b9f8599f425701332304d6308d505895b530eb5bfa545e5d53", "status": "ok", "fix_order": "freeze → A4 register/finalize → 受影响复核路 → runner finalize → shared_release_receipt → rounds → A5"}
  {"item": "rounds.entity_freeze_revision", "expected": 1, "actual": 1, "status": "ok", "fix_order": "freeze → A4 register/finalize → 受影响复核路 → runner finalize → shared_release_receipt → rounds → A5"}
  {"item": "dormant_warehouse_audit.universe_ref", "expected": "736aac989fd1ab1f5e985d9bd75249a91b12b8d45d553e1180be1a121fa27a63", "actual": "736aac989fd1ab1f5e985d9bd75249a91b12b8d45d553e1180be1a121fa27a63", "status": "ok", "fix_order": "freeze → A4 register/finalize → 受影响复核路 → runner finalize → shared_release_receipt → rounds → A5"}
  fix_order: freeze → A4 register/finalize → 受影响复核路 → runner finalize → shared_release_receipt → rounds → A5
PASS: identity_gate
PASS: a5_provenance_flip
  status=NO_FLIPS
BLOCK: a5_distribution
  ValueError: 终态 final scan 重验失败: scan 语义与独立重算不一致
NOTE: caption_same_source
  存在性检查，非逐桶配对
  NOTE: unresolved_contract raw=0，退化为数字存在性检查
  NOTE: burn_sentinel raw=0，退化为数字存在性检查
  NOTE: 图注未披露集中度数字
NOTE: dual_basis
  未声明双口径
BLOCK: fig2_series
  ValueError: 文件不存在: 'whale_series.provenance.json'
BLOCK: workorder
  WORKORDER BLOCK: amendments[0].before_sha256: 非空字符串 != None
  WORKORDER BLOCK: amendments[0].after_sha256: 非空字符串 != None
  WORKORDER BLOCK: amendments[0].trigger: 非空字符串 != None
  WORKORDER BLOCK: amendments[0].approved_by: 非空字符串 != None
  WORKORDER BLOCK: amendments[0].exact_change: before/after 字符串 != None
  WORKORDER BLOCK: amendments[0].before_sha256: 69c339f01488e5a6d1844515fd220ca50ec55090e5f6f48a80fe096b161d10ef != None
  WORKORDER BLOCK: amendments[1].before_sha256: 非空字符串 != None
  WORKORDER BLOCK: amendments[1].after_sha256: 非空字符串 != None
  WORKORDER BLOCK: amendments[1].trigger: 非空字符串 != None
  WORKORDER BLOCK: amendments[1].approved_by: 非空字符串 != None
  WORKORDER BLOCK: amendments[1].exact_change: before/after 字符串 != None
  WORKORDER BLOCK: amendments[2].before_sha256: 非空字符串 != None
  WORKORDER BLOCK: amendments[2].after_sha256: 非空字符串 != None
  WORKORDER BLOCK: amendments[2].trigger: 非空字符串 != None
  WORKORDER BLOCK: amendments[2].approved_by: 非空字符串 != None
  WORKORDER BLOCK: amendments[2].exact_change: before/after 字符串 != None
  WORKORDER BLOCK: amendments[3].before_sha256: 非空字符串 != None
  WORKORDER BLOCK: amendments[3].after_sha256: 非空字符串 != None
  WORKORDER BLOCK: amendments[3].trigger: 非空字符串 != None
  WORKORDER BLOCK: amendments[3].approved_by: 非空字符串 != None
  WORKORDER BLOCK: amendments[3].exact_change: before/after 字符串 != None
  WORKORDER BLOCK: amendments[-1].after_sha256: 69c339f01488e5a6d1844515fd220ca50ec55090e5f6f48a80fe096b161d10ef != None
  WORKORDER BLOCK: bindings.price_source_checks|price_source.dual_source_check: 双源检查对象在场 != None
  WORKORDER BLOCK: fig3.volume: {path,sha256} 完整且 sha256 非空 != {'path': None, 'note': 'DefiLlama 日线无成交额字段，下格以 0 占位并在题注注明'}
  WORKORDER BLOCK: fig3.events_input: {path,sha256} 完整且 sha256 非空 != None
  WORKORDER BLOCK: fig2.lines[0].series_source: {path,sha256} 完整且 sha256 非空 != None
  WORKORDER BLOCK: fig2.lines[1].series_source: {path,sha256} 完整且 sha256 非空 != None
  WORKORDER BLOCK: fig2.lines[2].series_source: {path,sha256} 完整且 sha256 非空 != None
  WORKORDER BLOCK: fig3.volume.path: 案内普通文件 != 路径必须是案根内非空相对文件路径: None
  WORKORDER BLOCK: fig2.lines[0].series_source: 可读取的 entity_series != 路径必须是案根内非空相对文件路径: None
  WORKORDER BLOCK: fig2.lines[1].series_source: 可读取的 entity_series != 路径必须是案根内非空相对文件路径: None
  WORKORDER BLOCK: fig2.lines[2].series_source: 可读取的 entity_series != 路径必须是案根内非空相对文件路径: None
  fig2 required 下限: ['e_proj']
  NOTE: 未声明流通量，门槛仅按总供应判
  flow 下限: ['e_proj']；图中实体: ['e_proj']
PASS: facts_gate
  G5 疑似手写百分比（新纪律：结论性百分比一律走宏；确认为非结论数字——如价格涨跌幅/费率——可交付）: 0.0001% 0.0002% 0.0004% 0.00085% 0.001% 0.002% 0.0038% 0.03% 0.0468% 0.05% 0.1% 0.106% 0.108% 0.1127% 0.158%
BLOCK: −2 收口未通过
rc=2
```

## 6. APU 0914：`reseal --case-dir <APU> --report 报告.md --from a4 --dry-run`（只读；预期 A0.1 exit 2）

验收脚本 `apu_dryrun_verify.py`（照抄 `test_stage2_reseal.py::dry_run_touches_nothing` 的 compare()，REPO=`/tmp/w3_acceptance`，cwd=案根）：
- d0 自检：阻断器 finder 在父进程与 `-B` 子进程各拦一次 matplotlib，标记恰两行 → PASS。
- 普通组 exit 2，stdout 1602 B，stderr 空；阻断组 exit 2，stdout 逐字相同，stderr 无 "blocked"，标记文件不存在/为空。
- 零写入：跑前 / 普通组后 / 阻断组后三次 `os.walk` 路径→sha 映射（2744 文件）＋目录清单（49 目录）完全相同；`/tmp/w3_acceptance/scripts`（379 文件）同；`MPLCONFIGDIR` 空目录跑后仍空。
- A0.0 通过（未报"案根已迁移"，直接进 A0.1）。A0.1 先因绝对路径不一致触发，如实打印真实路径比较，并另行只读算出两组 sha/bytes：`entity_source_trace.py` 记录 `ff4b640a…/44747` vs 当前 `e85acee4…/46034`，与工单 §E 预期一致；`wave_scan.py`、`sqd_cache_identity.py` 内容相同仅路径不同。

stdout 原文：
```
A0.1 顶层 script_sha256｜记录=ff4b640a1adbcecf8f3651efbda04493d3085754f939da1ef23b8d9f2efe0fc3｜当前=e85acee4e9a98a664d9b4881ca33177003aa9455261109a01e111e6faeda3cd1（46034 bytes）
A0.1 文件 entity_source_trace.py｜记录 sha/bytes=ff4b640a1adbcecf8f3651efbda04493d3085754f939da1ef23b8d9f2efe0fc3/44747｜当前 sha/bytes=e85acee4e9a98a664d9b4881ca33177003aa9455261109a01e111e6faeda3cd1/46034
算法文件 entity_source_trace.py 漂移：算法文件绑定路径 /Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/entity_source_trace.py ≠ 当前验证器依赖 /private/tmp/w3_acceptance/scripts/report/entity_source_trace.py
单文件校验在路径比较处返回；上述当前 sha/bytes 为另外只读计算，未由单文件校验比较内容
A0.1 文件 wave_scan.py｜记录 sha/bytes=9f8c176eff0592f6173eb7d8b7edf28cd47c07f986f703af74f063c20cbcbdc8/46694｜当前 sha/bytes=9f8c176eff0592f6173eb7d8b7edf28cd47c07f986f703af74f063c20cbcbdc8/46694
算法文件 wave_scan.py 漂移：算法文件绑定路径 /Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/wave_scan.py ≠ 当前验证器依赖 /private/tmp/w3_acceptance/scripts/report/wave_scan.py
单文件校验在路径比较处返回；上述当前 sha/bytes 为另外只读计算，未由单文件校验比较内容
A0.1 文件 sqd_cache_identity.py｜记录 sha/bytes=1e39b2178831c29a446c545a1eab602cb4ab4c0391747913573e0f8efcc32ded/12974｜当前 sha/bytes=1e39b2178831c29a446c545a1eab602cb4ab4c0391747913573e0f8efcc32ded/12974
算法文件 sqd_cache_identity.py 漂移：算法文件绑定路径 /Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_cache_identity.py ≠ 当前验证器依赖 /private/tmp/w3_acceptance/scripts/solana/sqd_cache_identity.py
单文件校验在路径比较处返回；上述当前 sha/bytes 为另外只读计算，未由单文件校验比较内容
算法文件 entity_source_trace.py/wave_scan.py/sqd_cache_identity.py 漂移：须在与 freeze 记录同一 checkout 下运行，或在当前代码下重跑 provenance/freeze 链
```

APU 完整 closeout 按用户 2026-09-16 裁决本版不真跑，记 7.2 待办。

## 7. 未做与遗留

- 合并线 `merge_groups` 本版不支持（用户裁决留 7.2）。
- APU 0914 完整 closeout / 重封真跑（用户裁决先不跑）。
- 版本号与另一会话分支 `fix/three-items-20260916` 合并后统一。

## 附录 A　调度方本机 run_all 日志

完整日志入库为同目录 `w3_run_all_fable_151pass.log`（本机 run_all 全文＋两项复跑全文）。结尾（复跑最后三行）：

```
{"probe_id": "10c55ed528c57501", "status": "published", "verdict": "INCONCLUSIVE"}
{"gid": "9777529f6e981392", "plan_digest": "aa92881f8487a949", "repair_edges": 0, "status": "published"}
PASS batch8: key-neutral identity/pool failover/ordered workers/resume/streaming
```
（run_all 原始尾行为 `2 项失败——修完再收工`，两项失败已在复跑中清零。）

