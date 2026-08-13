# 批 D 增量台账（批 A/B 施工与对抗审查沉淀）

> 本文件只收批 A/批 B 过程中新沉淀的批 D 项，plan.md 批 D 节既定项（F-06/F-07/GPT-F-06/流程债/版本收口/契约三件同步/R10 台账落盘）不重复登记。批 D 开工时以「plan.md 批 D 节 ＋ 本文件」为完整清单。

## 一、批 A 沉淀（原始表述见 batchA_fixround2_workorder.md §六）

| # | 台账项 | 要点 |
|---|---|---|
| A-1 | 政策拒绝时旧收据作废（F-D 后半） | 复核者建议排前列；`publish_overwrite` 拒绝降级覆盖的新证据在案 |
| A-2 | `approved_tolerance_bps` 硬顶（F-E 后半） | **待用户裁决**；落地须连 `observed_diff_bps` 的"预先虚报"一起管 |
| A-3 | envelope inputs 相对路径根治（F-G 后半） | 验收标准必须写明"解析在案根内且与其他四查收据同源"，否则 N-1 那扇门照样开着 |
| A-4 | EVM `onchain_total_supply` 链上观测件锚定（N-2 EVM 半） | 明示局限已入 independent-audit-protocol.md；根治＝supply_truth 额外落可绑定链上观测件（对标 Solana bundle），与 A-3 一并设计 |
| A-5 | supply_truth 的 stats 须与 balance/supply 两查收据同源 | N-1 第二建议，批 A 只做了案根约束 |

记录不修类（证据强度参数，非判定翻转参数）：accounting `--samples`、verify_recon `--top-n`、anchor_sampler 覆盖窗。

## 二、批 B 沉淀（原始表述见 batchB_adversarial.md 及两轮修复工单）

| # | 台账项 | 要点 |
|---|---|---|
| B-1 | Solana `holder_outputs` 文件级三验（F-B6①） | 放 validate_observation_bundle；当前该锚点无 validator 实物锚、弱 EVM 一档（文档已如实写明） |
| B-2 | Solana new-analysis 发布闸 run() 完整端到端夹具（F-B6②） | 轮 1 以落盘版单元夹具（四条判定路径含终态换仓拒）替代，盲审裁定够本轮收口，端到端补齐留此 |
| B-3 | denominators 键名升版 `mint_total_raw`（N-B4 后半） | 语义已如实写进 scan-schemas.md；改键名属 schema 升版，随批 D 契约三件同步做 |
| B-4 | 扫描器自身对收据 `inputs.replay_stats` 补 sha/size 比对（R2-O1，P3） | 约 3 行；同时把"已由 receipt_validate 做过三验"的 docstring 过度宣称改准。非轮 2 新引入，发布路径有 receipt_validate 兜底 |
| B-5 | 「绑定实物必须在案根内」fail-closed 分支补红线用例（R2-O2，P3） | 批 A N-1 把案根约束定为 P1 级要求，该分支目前变异存活 |
| B-6 | EVM `inputs.balances` 无案根约束（同族约束不等深） | 盲审视角⑤不立 finding 台账项；与 A-3/A-4 同族，一并设计 |
| B-7 | `balance_source` 与四查 balance 收据无等值绑定 | 案内"owner 余额快照"声明有三处，批 B 只钉了前两处（且 final 绑定已在轮 1 补上）；第三处 audit_release_gate.py:335-356 的三账 balance_source 仍游离 |

## 三、状态

- 批 A：已收口（f575472/78d1c4c/8b089c3 系列，终复核零实质新 finding）
- 批 B：已收口（394ffbb 消化轮 1＋397e38f 消化轮 2；盲审终判"可收口，不需轮 3"；原 7 条 F-B* 全 CLOSED＋复核新引入 N-B1~4 全 CLOSED；遗留 R2-O1/R2-O2 即上表 B-4/B-5）
