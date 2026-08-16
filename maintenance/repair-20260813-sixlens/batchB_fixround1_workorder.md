# 批 B 消化循环第 1 轮工单（盲审 7 条 finding + 裁判追加 4 项）

审查对象：`ee0e8e9`（批 B 收口态）。盲审终版 `batchB_adversarial.md` 判"不该原样收口"，7 条 finding（1 P0/4 P2/2 P3）。本轮合并处理裁判原 6 项工单 + 追加 4 项（F-B4/F-B5/F-B6②③/F-B7）。未提交 git。

编号对照（盲审自给）：F-B1＝原工单第 1 项（final 绑定）、F-B2＝原工单第 4 项（容差收回）、F-B3＝原工单第 5 项（白名单）。

## 一句话结论

盲审两条端到端攻击（probe1 final 换仓 BYPASS、probe2 10bps 窗口翻转）现已全部转拒；第一层闭合锚点经**真案三向实测**从 total/onchain 改到 replay 侧 `mint_total`（form1 误杀论证成立、未撞坑）；影子键根除、白名单、第二层三条 fail-closed 定向红线、F-B7 潜伏防御、两处文档改口全部落地。`test_repair_batch_b` 33/33，`run_all` 全量退出码 0。

---

## 锚点三向实测（裁判硬要求，撞坑即停——未撞坑）

盲审终版对第一层 total 锚点判"成立、未发现误伤"，但它**没测过真实 form1 案**。分歧收敛为一个纯代码事实：**分布快照导出含不含 sink 地址行**。用仓库同级工作区的真案产物逐 wei 实测（`APU分析0801`/`IQ分析`/`KOGE分析` 的 `balances_final.json` + `replay_stats.json`）：

| 案 | 形态 | mint_total | onchain(=mint−burn) | sum(快照含 dead/0x0) | sum==mint? | sum==onchain? |
|---|---|---|---|---|---|---|
| APU | form2 dead_sink | 420690000000000000000000000000 | 337889146346088792653960057820 | 420690000000000000000000000000 | ✅ | ❌ |
| IQ | form1 真 _burn | 31082094105963223790329250162 | 23038913286553224147057740625 | 31082094105963223790329250162 | ✅ | ❌ |
| KOGE | form1 真 _burn | 5000000000000000000000000 | 3379997186850493127129576 | 5000000000000000000000000 | ✅ | ❌ |

**结论**：三案（含两个真 form1）balances_final **都含 sink 地址行**（IQ/KOGE 的 `0x0` 持 burn、APU 的 `dead` 持 burn），`sum == mint_total` 逐 wei 成立，`sum ≠ onchain`。所以：

- 对 onchain/total 闭合会把 IQ（销毁 25.9%）、KOGE（销毁 32.4%）整类 form1 币误杀 → **盲审 F-B3(P1-B3) 成立，total 锚点错**。
- 改 mint_total 锚点后，三向实测全过：
  - **a. 真实 form1**（IQ 数字，链上 totalSupply < mint）：mint 锚精确闭合放行 → `test_p1b3_form1_real_receipt` 绿。
  - **b. 真实 form2**（APU 数字）：mint 锚精确闭合放行 → `test_p1b3_form2_real_receipt` 绿。
  - **c. 既有 dead-sink 绿例**（sum=mint≠net）：mint 锚下仍绿 → `test_c_deadsink_synthetic_green_under_mint_anchor` 绿。
- 盲审 M3 变异（锚点换 net）在新锚点下依然会误杀 dead-sink（防误伤守卫仍有效，见变异表）。

**未撞坑**，无需上报选边。

---

## 逐条修法与证据

### F-B1（P0）final 轮快照绑定——原工单第 1 项

**攻击**（probe1，已复现）：第二层只绑 initial `distribution_scan.json`；final 轮 `--snapshot` 换一份同值换仓快照，record-round→A5 seal→发布闸全链 `BYPASS(发布闸放行)`。

**修法（两道，纵深）**：
1. 生产侧（`holder_distribution_scan.build_scan` final 分支）：final 轮的 `input_binding.snapshot.sha256` 必须 == 它绑定的 initial scan 的 snapshot sha，不等即 `data_broken` exit 2。生产时就挡住换快照。
2. 发布闸（`audit_release_gate.check_distribution_snapshot_binding`，new-analysis）：除 initial 外，**读 `distribution_rounds.json` 的 `terminal.final_scan_path`，把终态 final scan 的 snapshot sha 一并纳入同一个四查 sha 等值比对**（盲审建议的台账版）。EVM 对 `inputs.balances`、Solana 对 `holder_outputs.owners`。**只放发布闸、不进 validate_scan**。
3. 跨轮：`validate_rounds_ledger` 要求各轮 `snapshot_sha` 与首轮一致（原来只记不比）。

**反例测试**：`test_p0b1_final_snapshot_swap_rejected`（照 probe1 构造：initial 用真快照过，final `--snapshot` 换 alt 换仓快照）——合法 final 放行、换仓 final `rc=2`。Solana 侧终态换仓由 `test_f03_gate_solana_not_skipped` 的"终态 final 换仓被拒"覆盖。

### F-B2（P2）10bps 窗口翻转——原工单第 4 项

**攻击**（probe2，已复现）：删 5 个刚过 dust 线的 owner（缺口 0.005bps）把 `ABNORMAL_SHAPE` 翻成 `low_sample` 终态。

**修法**：`SNAPSHOT_CLOSURE_TOLERANCE_BPS = 10 → 0`（逐 wei 精确闭合）。依据＝三向实测 `sum==mint` 逐 wei 成立，且快照与 totalSupply 同 `as_of_block` 冻结无块高漂移，超发/缺失侧都不需要任何窗口。收 0 后删任何 owner 立即破坏闭合。

**反例测试**：`test_p2b4_exact_closure_window`（probe2 同构：删 5 个极小 owner）→ `rc=2` 被拒；`test_f03_overshoot_rejected` 超发 1 wei 也拒。

### F-B3（P2）白名单——原工单第 5 项

**攻击**：F-08 三验只验内容不验身份，`upstream_receipts` 改指案内任意真文件（`supply_truth.json`、工作图 PNG）照样 PASS。

**修法**：`validate_scan` 三验前加 `UPSTREAM_RECEIPT_WHITELIST = ("channels_preflight.json", "holders_snapshot_meta.json")`，path 不在白名单即拒（build_scan 只会记这两个名）。方向仍是"记录项→磁盘"，不复活 6.39.5 死环。

**反例测试**：`test_p2b5_receipt_path_whitelist`（记 `supply_truth.json`，文件真存在、sha/size 全对）→ 被拒。

### F-B4（P2，追加）第二层三条 fail-closed 分支定向红线

盲审 M12/M13/M14：把第二层"找不到四查收据文件／initial 缺 snapshot.sha256／链族判不出"三条改成静默 return，全量 suite 仍全绿＝零回归覆盖。

**修法**：补 `test_fb4_second_layer_failclosed_branches`，各造只坏一处的 data 调 `check_distribution_snapshot_binding`，断言 errors 含对应文本（"找不到四查"／"snapshot.sha256"／"无法判定链族|未登记链族"）。变异验证（见下表）三条改静默后各自定向用例变红。

### F-B5（P2，追加）改口径不改代码

盲审 probe3：工单/文档"A5 终态案重验不死锁"不成立——第一层闭合闸经 `build_scan` 进了 `validate_scan` 追溯路径，存量案实测被拒。

**修法**（`references/scan-schemas.md`，不改代码）：改写为"重验须重跑当前版本生产者（`input_binding.algorithm.sha256` 绑脚本自身哈希，脚本改一字节旧产物即对不上，与仓内既有『存量案例须重跑对应生产者』一致），这不是死锁；重跑后仍不对铸造总量精确闭合的存量案按 `data_broken` 拒收，是**刻意收紧不是回归**。第二层交叉检查禁入 validate 只保护『快照↔四查绑定』这一条，闭合闸的追溯收紧另算。"

**反例测试**：`test_fb5_docs_retro_not_deadlock_wording`（断言"重跑当前版本生产者"＋"data_broken"＋"刻意收紧/不是回归"三串在文档）。

### F-B6（P3，追加，本轮只做②③）

- **②Solana new-analysis 经 run() 端到端**：本轮以落盘版单元夹具补强——`test_f03_gate_solana_not_skipped` 改为落盘 `supply_receipt.json`（真 holder_outputs.owners）＋终态 `dist_rounds/round_1/distribution_scan.json`＋`distribution_rounds.json` terminal，覆盖 initial 相符放行／initial 换仓拒／**终态 final 换仓拒**／bundle 缺 owners 拒四态。（说明：完整"真跑 scan_token_accounts→reconciliation→run() 发布闸"的 Solana new-analysis 端到端夹具工程量大，`test_batch3_solana_vertical_slice` 已有真跑基建但走 independent-audit；本轮落盘版单元夹具已让第二层 Solana 分支的四条判定路径都被执行到，完整 run() 端到端夹具记为批 D 候选。）
- **③文档如实写强度差异**（`scan-schemas.md`）：EVM `inputs.balances` 有 `receipt_validate.validate_receipt` 实物三验；Solana `holder_outputs.owners` **目前全库无 validator 实物三验、无实物锚**（`validate_observation_bundle` 只校验 `inputs`），只有本闸一处 sha 等值。给 `holder_outputs` 补文件级三验（盲审建议①）记批 D 台账。
- 反例测试：`test_fb6_docs_binding_strength_diff`。

### F-B7（P3 潜伏，追加）链族分派

**修法**：把 `check_distribution_snapshot_binding` 里的裸字典下标 `{...}[family]` 提成模块常量 `SNAPSHOT_BINDING_BY_FAMILY`，取值前加成员检查（`if family not in ...: errors.append(...); return`），不再让 KeyError 逃出闸函数。

**诚实标注**：该成员检查**当前不可达**——`chain_family` 只返回 evm/solana，第三族在 `chain_family` 就抛 ValueError 被上面的 `except` 接住（M14 测的正是这条）。所以变异删掉成员检查**存活**（见变异表），这是防未来加链族的潜伏防御，不是当前活漏洞。与盲审 P3 定性一致。

---

## a4_gate 夹具修复（本轮最费时的真实工程细节）

改 mint_total 锚点后 `test_a4_gate` 的 P1-05 红，根因是**夹具缝合冲突**（非生产代码问题）：a4_gate 的 case 是 audit 案，真跑过 `replay_pass1` 产出真实 `replay_stats.json`（mint=100、1 owner）＋`balances_final.json`（sum=100）＋`identity_gate.json`（total=100）一整套自洽产物，G8 identity_gate 靠它们互证；而原 `add_distribution_initial` 另造 240-owner 快照（sum=59127382）与这套脱节。闭合锚点走 replay 侧 mint 后，distribution 快照与案根 replay(100) 冲突。

修法（`add_distribution_initial`）：让分布快照直接用案内真实 `balances_final.json`（全案同一个 100，零人为数字），不再另造 240-owner 制造两套供给量。owner 少落 `low_sample`（合法终态）。连带修 `finish_distribution_normal`：A5 seal 对 `low_sample` 要求的强制披露句是 `"形态统计因样本不足未做,以逐址集中度事实替代"`（与 NORMAL 句不同），按 final scan verdict 选对应句。改动全在测试夹具，纯新增/对齐、无断言删改。

---

## 变异验证（各"删掉即红"，备份 `/tmp/hds.r1_*`、`/tmp/arg.r1_*`，逐条还原）

| 变异 | 结果 | 咬住的用例 |
|---|---|---|
| 闭合回退单向（缺口/抹平不拦） | 变红（4 条） | 快照缺口 99%、form1 少 1 wei、P1-B2 影子键、P2-B4 |
| mint 锚点换成 onchain（误杀 form1） | 变红 | P1-B3 form1 精确闭合放行 |
| final 绑定 initial 快照检查删 | 变红 | P0-B1 final 换仓被拒 |
| upstream 白名单删 | 变红 | P2-B5 白名单外记录项被拒 |
| 发布闸终态 final 检查删 | 变红 | F-03/2 Solana 终态 final 换仓被拒 |
| F-B4/M12 找不到四查收据静默放过 | 变红 | F-B4/M12 |
| F-B4/M13 缺 snapshot.sha256 静默放过 | 变红 | F-B4/M13 |
| F-B4/M14 链族判不出静默放过 | 变红 | F-B4/M14 |
| F-B7 family 成员检查删 | **存活** | 潜伏防御，当前不可达（chain_family 先抛），如实标注 |

裁判点名的三处（final 绑定、mint_total 闭合、白名单）＋ F-B4 三分支全部"删掉即红"。

---

## 红绿证据

- 先红（代码未改 mint_anchor 时）：`test_repair_batch_b` 6/26 FAIL——form1 误杀、10bps 放行抹平、anchor 未实现、final 换仓放行、白名单缺、文档口径。
- 后绿：`test_repair_batch_b` **33/33**；`run_all` 全量 **EXIT=0**（含 a4_gate 23 项、distribution_gate、handoff 67 项、audit_release_gate、p105、batch3 双纵切片）。

---

## diff-finding-map（每 hunk 归属）

| 文件／hunk | finding | 归属 |
|---|---|---|
| `holder_distribution_scan.py` 常量：`SNAPSHOT_CLOSURE_TOLERANCE_BPS=0`、`MINT_BURN_FIELD_PAIRS`、`UPSTREAM_RECEIPT_WHITELIST` | F-B2/P1-B3/F-B3 | 零容差、replay mint 字段、白名单 |
| `holder_distribution_scan.load_supply` 重写（onchain/net 优先真实键） | P1-B2 | 去影子键作 net/onchain 来源 |
| `holder_distribution_scan.mint_closure_anchor`（新函数） | P1-B3/P1-B2 | 分链闭合锚点，绝不取影子键 |
| `holder_distribution_scan.build_scan` 闭合改 anchor+零容差、denominators total=mint | F-B2/P1-B3 | 第一层锚点翻案 |
| `holder_distribution_scan.build_scan` final 分支 initial 快照一致性检查 | F-B1 | 生产侧挡 final 换仓 |
| `holder_distribution_scan.validate_scan` upstream 白名单 | F-B3 | 记录项 path 钉白名单 |
| `holder_distribution_scan.validate_rounds_ledger` 各轮 snapshot_sha 一致 | F-B1 | 跨轮快照不得更换 |
| `audit_release_gate.SNAPSHOT_BINDING_BY_FAMILY`（模块常量）+ `_scan_snapshot_sha` | F-B7 | 链族分派提常量 |
| `audit_release_gate.check_distribution_snapshot_binding` 重写：成员检查+终态 final 覆盖 | F-B1/F-B7/F-B4 | 发布闸终态绑定、成员检查、三条 fail-closed |
| `references/scan-schemas.md` 闭合锚点/影子键口径 | P1-B3/P1-B2 | 文档同批改口 |
| `references/scan-schemas.md` 重验须重跑生产者 | F-B5 | 改口径 |
| `references/scan-schemas.md` EVM/Solana 强度差异 | F-B6③ | 如实标注 |
| `test_repair_batch_b.py` 重构+新增用例 | 全部 | 33 条红绿+变异守卫 |
| `test_a4_gate.py` add_distribution_initial/finish 夹具修复 | 连带 | 缝合冲突+low_sample 披露句 |
| `test_distribution_gate.py`/`test_handoff_manifest.py`/`test_review_20260804_p105.py` supply_truth 补真实键 | P1-B2 | 夹具补 onchain_total_supply/mint_total（纯新增，无断言改） |

## 新契约面清单（批 D 统一登记）

- `holder_distribution_scan.SNAPSHOT_CLOSURE_TOLERANCE_BPS` 语义改为 0（逐 wei 精确）。
- 新函数 `holder_distribution_scan.mint_closure_anchor`；新常量 `MINT_BURN_FIELD_PAIRS`、`UPSTREAM_RECEIPT_WHITELIST`。
- `input_binding` 新增 `mint_closure_anchor`（source/raw[/replay_stats]）。
- 闭合分母语义：EVM=`replay_stats.mint_total`／Solana=`onchain`，绝不取 `total_supply_raw`/`frozen_total_supply_raw` 影子键。
- `audit_release_gate.SNAPSHOT_BINDING_BY_FAMILY`（模块常量）、`_scan_snapshot_sha`；发布闸 new-analysis 增验终态 final scan 快照绑定。
- 批 D 台账候选：给 Solana `holder_outputs.owners` 补文件级 validator 三验（F-B6①）；Solana new-analysis 完整 run() 端到端夹具（F-B6②补强）。

未改 `contract_manifest.json`/`contract_ids_snapshot.json`，统一留批 D。

## 边界与部署

- **越界检查**：生产文件只动 `audit_release_gate.py`（批 B 第二层，裁判明示可动）与 `holder_distribution_scan.py`（批 B 主改）；批 C/D 十个生产文件（state_from_facts/standard_charts/replay_pass2/replay_duck/replay_edges/build_evolution/entity_source_trace/handoff_manifest/a5_report_seal/fetch_hypersync_v2）逐一 `git diff --quiet` 确认**未动**。版本三处（VERSION/SKILL.md/pyproject）与两份契约快照未动。未 commit。**无越界。**
- **commands-staging**：本轮文档只改 `references/scan-schemas.md`（非命令契约文本），未触及 commands-staging；三命令 staging/部署 SHA 保持第一轮实测的全等态（本轮未动命令文件）。

修复轮完成
