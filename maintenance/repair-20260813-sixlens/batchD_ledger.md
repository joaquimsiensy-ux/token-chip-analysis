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

## 二b、批 C 沉淀：存量迁移上报项三则（裁判已裁决，均为"将来重编译该案时"的注意事项，当前零影响）

| 案 | 分类 | 裁决 |
|---|---|---|
| QUQ（监控在跑） | A 类·白名单口径 | 监控链路不走 compile_state，当前不受影响；下次重开案重编译时按案内证据把"狙击集团"归并现代阵营名（映射是分析判断，禁全局表） |
| TAG（HTML 升版重验交接中） | A 类·白名单口径 | 同上；届时与案目录 SKILL_PATCH_PROPOSAL.md 交接件一并处理，实体级分桶归并后的图形语义变化需案内确认 |
| MOG（最差点 idx 177 合计 99.7433，偏离 0.2567pp；工单初报"第 93 点差 0.056pp"经盲审复核更正，低估 4.6 倍） | C 类·真数据问题 | **不放宽容差**（0.05pp 是批 C 定案值）；0.26pp 量级已无"容差边界"争论空间，纯数据问题——将来重编译按 F-B5 口径先用当前版生产者重出序列，重出仍差再修数据。KOGE 日期轴重复同步更正为 2 处（idx 8、12） |

另：批 C 新契约面（figure2-check-receipt/v1、--exploration×2 CLI、camp-series sidecar 族）已由施工方记账，批 D 契约三件同步时统一登记。

## 二c、批 C 终验沉淀：R10 级三条（批 D 建 r10_ledger.md 时转入）

| # | 条目 | 要点 |
|---|---|---|
| C-R1 | `target.as_of_block` 无真实对锚（N-C5 前半） | 改成任意正整数照过；锚到案外链上证据属 F-12 地盘，锚到案内件只是多一个可伪造件——修法待设计 |
| C-R2 | sol 侧 `solana-reconcile/v2` 收据 schema 无身份键（N-C5 后半） | replay_edges.py:166 实物核实；加身份键属 producer schema 扩面；跨案复制收据当前可用 |
| C-R3 | sol 分支发布期复算路径未经真实案端到端验证 | 批 C 终验实测只覆盖 EVM 链路；将来补 C-R2 身份键时须同批做 sol 真实案端到端 |

批 C 残余边界准确口径（终验更正，已同步 scan-schemas §13）：控制案目录者手写一组互相自洽的案内小件（实测约 1.5KB、无需运行 producer）即可通过全部一致性校验——validator 是一致性校验器不是真实性证明器；此链上已无可机器闭合的下一层（终验逐个查证 channels_preflight 自身收据链/identity_gate 实物两个候选锚，均只是"多一个可伪造件"）。

## 二d、批 D 消化轮 1 遗留（盲审记账项，非 finding）

- **报错换岗致断言精度下降**：test_repair_batch_a N-1 用例（二选一 needle）与 test_handoff_manifest 两处（needle 放宽到"三策略主导终点翻转"共同串）——被拒面不减，但断言从"区分具体拦截分支"退化为"区分拒绝类别"，**将来旧闸被误删不会红**。若需恢复精度：为新旧两闸各立独立定向用例（分别只中和另一道）。
- **Solana 同案连续端到端差额（F-D3）**：EVM 已建同案连续链（t_fd3）；Solana 的 state→figures 段仍由批 C 另案链承载，同案接入的夹具成本（sol-rows replay 产物嫁接完整发布案）超消化轮预算——下轮或 R10 一并补（与 r10 C-R3 的 sol 真实案端到端同批做最省）。
- **check_bound_file 绝对路径无案根强制**：见 r10_ledger R10-15。
- **披露切片内残余绕路（N-D2，收口补丁登记）**：切片内三项（策略名/终点标识/份额）仍是独立子串搜，location 由收据自填可指向任意标题——盲审两实例可过：①被点名章节里写"否认性术语表"（内部标识 pro_rata…以上均非分析结论）；②location 写通用词"附录"命中任意附录标题。此属"validator 是一致性校验器不是真实性证明器"（批 C 终验/scan-schemas §13 已声明边界）的实例——作者在被点名章节堆砌三项串但不作真实披露＝蓄意伪装，F-12 边界同族；locations 是冻结的裁决内容（sha 三处咬死），第三方改不了，剩余主体是报告作者本人。若要再收一层：披露段结构化标记块（HTML 注释锚）属 R10 设计面。

## 三、状态

- 批 A：已收口（f575472/78d1c4c/8b089c3 系列，终复核零实质新 finding）
- 批 B：已收口（394ffbb 消化轮 1＋397e38f 消化轮 2；盲审终判"可收口，不需轮 3"；原 7 条 F-B* 全 CLOSED＋复核新引入 N-B1~4 全 CLOSED；遗留 R2-O1/R2-O2 即上表 B-4/B-5）
