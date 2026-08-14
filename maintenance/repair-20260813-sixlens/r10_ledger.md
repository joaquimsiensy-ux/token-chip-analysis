# R10 台账（六视角修复工程 2026-08-13 收口时冻结；本轮未修，台账保留）

> 来源：plan.md 定案范围之外的存量/加深/评估项。下一轮修复工程（R10）开工时以本文件为完整候选清单。
> 引用纪律：每条的原始证据与最强反例在 `input_codex_review.md` / `input_gpt56_review.md` / 各批工单，动工前必读原文。

## 一、存量六条（plan 既定，用户 08-13 拍板留台账）

| # | 条目 | 一句话 | 修法线索 |
|---|---|---|---|
| R10-1 | F-09（=GPT-F-03）图 1 对未知阵营静默漏画 | figures wrapper 接受任意阵营，绘图层只取 CAMP_ORDER 交集，未知阵营无警告无非零退出 | 批 C 已在 compile_state 路径装白名单硬拒；**旧 state 直喂 fig1 的重绘路径不经 compile_state**，该路径仍开着——按 GPT-F-03 修法连 A5 图例集合绑定（R10-7）一起做 |
| R10-2 | F-10 对抗复核可空壳 | adversarial_review 的 reviews 只验角色名与 exit_code，内容可为空洞文本 | 复核产物结构化最低要求＋抽查锚 |
| R10-3 | F-11 replay gate fail-open 残留 | 历史漏检家族（同族采集器已修，个别入口未等深） | 按 GPT-F-05 证据点逐入口收口 |
| R10-4 | F-13 v2 采集器保留可选位置 api_token 且优先于环境变量/文件 | 令牌可进 ps；F-07 回归只列三支 v1 脚本 | 移除位置参数或降级其优先序，回归补 v2 |
| R10-5 | GPT-F-07 deploy-sync 两条假绿（弱闸） | 部署目录缺失打 SKIP 但 return 0；MIGRATION_CHANGED 豁免无期限 | 豁免加期限＋缺目录 fail；**本轮旁证**：批 D 工单附三命令 staging/部署 SHA 实测全等记录（不引用该弱闸 rc=0 作证据） |
| R10-6 | GPT-F-09 env_check 覆盖不足 | 不查 Python 版本（pyproject 要求 >=3.14）、KEY_PKGS 手写 14 个漏 7 个直接依赖 | KEY_PKGS 从 pyproject 机械生成＋requires-python 检查；**本轮旁证**：批 D 工单附解释器版本与全部直接依赖 version/import 实测记录 |

## 二、GPT 交叉对账加深两条

| # | 条目 | 一句话 |
|---|---|---|
| R10-7 | A5 seal 增图例集合绑定（GPT-F-03 修法后半） | A5 只绑最终 PNG 哈希，不重验图例集合——与 R10-1 同一威胁面，修图 1 白名单时同批把"图例集合"纳入 A5 绑定 |
| R10-8 | F-12 改名降权（GPT-F-10 修法） | `formal_ready` 静态声明可伪造属已接受边界；建议把字段名改为不承载"已验证"语义的中性名并在文档降权，消除"名字看起来像证明"的误导面 |

## 三、批 C 终验沉淀三条（batchD_ledger 二c 节转入）

| # | 条目 | 一句话 |
|---|---|---|
| R10-9（C-R1） | `target.as_of_block` 无真实对锚 | 改成任意正整数照过全部一致性校验；锚到案外链上证据属 F-12 地盘，锚到案内件只是多一个可伪造件——修法待设计 |
| R10-10（C-R2） | sol 侧 `solana-reconcile/v2` 收据 schema 无身份键 | replay_edges.py:166 实物核实；加身份键属 producer schema 扩面；跨案复制收据当前可用 |
| R10-11（C-R3） | sol 分支发布期复算路径未经真实案端到端验证 | 批 C 终验实测只覆盖 EVM 链路；将来补 C-R2 身份键时须同批做 sol 真实案端到端。（注：批 D 已补 Solana new-analysis 发布闸 run() 端到端夹具——B-2——但 check_series_binding 的 sol 序列复算段仍未经真实案数据验证，此条保留） |

## 四、批 D 评估留档两条（D-iv 评估产出，回传已报明）

| # | 条目 | 评估结论 |
|---|---|---|
| R10-12（A-2） | `approved_tolerance_bps` 硬顶＋`observed_diff_bps` 预先虚报 | **未被现行钳制实质覆盖，且属政策决定——待用户裁决，本轮不做**。核证：`FORMAL_TOLERANCE_BPS_MAX=10` 只钳"无 waiver 时容差 ≤10"；有 waiver 时 `approved_tolerance_bps` 无上限（写 100000 照过），`observed_diff_bps` 可预先写大值覆盖未来一切偏差——两个数合起来 waiver 可变万能通行证。复核者原话："这是政策问题不是工程问题（谁有权批多大偏差、要不要二人复核），该由用户裁决；落地时连 observed_diff_bps 的预先虚报一起管，只钳一个数没用。"待用户给出硬顶数值与复核规则后一并落地。 |
| R10-13（A-4） | EVM `onchain_total_supply` 链上观测件锚定 | **属新功能面设计活，与 A-3（路径语义改造）不顺手，本轮不做**；批 A 已有"明示局限"写入 `independent-audit-protocol.md` 兜底。设计要点留档：①对标 Solana observation bundle，造 EVM 链上观测收据 producer（attested eth_call totalSupply@as_of_block，经 net.attested_rpc_pool 出 attestation）；②supply_truth 额外落该观测件并入 inputs 绑定；③消费侧（shared_release_receipt supply_truth 分支）比对收据自报 onchain 与观测件数值——对齐 Solana 侧 N-2 修复的强度；④观测件须绑定端点指纹与 genesis/chainId 证明，防"观测件也自报"。 |

## 五、状态

- 建档：2026-08-13（批 D 收口时）。本轮（6.40.0）未修上述任何一条，CHANGELOG 已显式注明。
- 弱闸旁证（R10-5/6 相关）：见 `batchD_workorder.md` §旁证——三命令 staging/部署 SHA 实测全等记录＋解释器与直接依赖 version/import 实测记录，均为实测输出，不引用弱闸 rc=0。
