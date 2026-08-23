---
project: repair-20260823-sqd-gap
title: SQD 覆盖闸 ＋ 修复生产者窄门（token-chip-analysis skill v6.52.0）
status: batch0-frozen（待 codex 只读终审 → 批 1 准入）
baseline: main=f06078e (v6.51.0)
target_version: 6.52.0
source_plan: ~/.claude/plans/codex-id-019ff65c-98f8-71a0-a73c-102b53-quizzical-zebra.md (r7.1, user-approved 2026-08-23)
source_plan_sha256: 506cdcbe7938ad6e79eb539e793fa0f47081426f3f21d7dada404cb021a9ad93
frozen_at: 2026-08-23
errata: PLAN_errata_batch0.md（批 0 勘误与补全 7 条，正文不改，冲突处以 errata 为准）
note: 正文为计划原文逐字节落盘；frontmatter 之后的内容 sha256 == source_plan_sha256（见 batch0_done.md 实证）
---
# ARC A2 残差 → Solana SQD 缺陷修复：两会话总结 ＋ skill v6.52.0 详细施工计划（r7.1：消化 codex r6 复核 4 项窄阻塞＋r7 复核 2 项文字一致性修订 → 用户审批）

> 状态：**plan mode，未动任何文件。** 本文件＝"总结＋详细计划"正文（等价于 §5 的"批 0 设计冻结件"）。
> 版本脉络：r1 → codex 4 硬伤 → r2 → 用户 8 条裁决（§7）→ r3 → codex"不可开工"（§6.2）→ r4 → codex"不可开工"（§6.3）→ r5 → codex"不可开工"（§6.4）→ r6 → **codex"不可开工"（§6.5，4 项窄阻塞：bundle↔meta 哈希环／目录 fsync／金额规范化与 v4 int 冲突／getBlocks 实物未绑定／repaired 组合规则，全部核实属实）→ r7 → **codex r7 复核：设计项全部闭合，仅余 2 项文字一致性（resolution 残留 gid／bundle·layer 漏 plan_digest／先红 29 拆三组）已按其原话修订（§6.6）→ r7.1（本稿）** → 用户审批 → 退出 plan mode 开工（批 0 落盘 PLAN.md 后由 codex 只读终审一次作为批 1 准入闸）。
> 两份会话原始记录：codex `~/.codex/sessions/2026/08/12/rollout-…-019ff65c-98f8-71a0-a73c-102b53a846c4.jsonl`（43 MB，08-12→08-23）；Claude Code `~/.claude/projects/-Users-uravvv-Desktop-----fable----/cc7af5d3-….jsonl`（08-20→08-23）。
> 证据总文：`~/Documents/5.6筹码分析/ARC分析/diagnosis_20260823/sqd_query_variants/FINDINGS_sqd_omission_rootcause.md`（§0–§10）。
> 标【codex】＝来自 codex 复核；其余为 Fable 调查与判断。skill 仓库 `~/.claude/skills/token-chip-analysis`，main=f06078e，v6.51.0，run_all SUITE 124 项。

---

## 0. Context（为什么要做这件事）

ARC（Solana，mint `61V8vBaqAGMpgDQi4JcAwo1dmBGHsyhzodcPqnEVpump`）是 skill v6.50.0 切 v4 采集后的第一个实战案，也是 SQD v4 根治工程的"后置条件验证案"。结果 −1 阶段被 A2 对账卡死 3 天：**根因在上游数据源——SQD 的 Solana 数据集本身按 slot 区段漏记 durable-nonce 交易**；skill 侧不是代码 bug，而是两处设计缺陷：①正式验收只验"缓存是谁产的、格式对不对"，不验"SQD 这段数据全不全"，也没给"上游缺数据"留任何合法补数通道；②文档把 SQD 的交易编号当成链上位置（错误前提）。数据源缺、唯一生产者只会从该数据源产数、对账门不放行 → 诚实执行者被锁死。codex 在"不改 skill"前提下追了 48 小时"数学清零"，因身份键用错而发散（26→990），直到 08-23 Fable 找到真根因、用"路 A"（按缺陷区段逐块从 Helius 补、按签名对照）83 条修复边把账补平。

现在要做两件事：① 把"为什么卡、为什么清不了、最后怎么清的"讲清楚；② 把这套已验证的清零方法**产品化进 skill**（覆盖探针 ＋ 修复生产者窄门 ＋ 闸接到必经之路 ＋ 文档前提更正），让今后所有 Solana 案都能按标准流程过 A2，而不是每案手工救火。

---

## 1. 两个会话发生了什么（时间线）

### 1.1 codex 会话（用户直接指挥 codex，08-12 → 08-23 04:02 UTC）

| 日期(UTC) | 发生了什么 | 结果 |
|---|---|---|
| 08-12 | 用户令"做 ARC −1 阶段 full 模式"。codex 冻结身份/快照（供应 999,982,741 ARC、45,823 owner），起 SQD 全史采集（1.32 亿 slot） | 采集挂后台，进度 6% |
| 08-13→08-16 | 采集停滞 69 小时（PID 丢失）；用户令按 v6.45.0 检查 | 覆盖 85.9%，handoff 不存在，判"未完成" |
| 08-16→08-18 | 续采完成 26,515,084 边（v3 口径）。首次对账：**6 负余额＋41 不一致**。codex 判为"owner 变更（SetAuthority）漏记"，起 20 小时 owner-correction 全量重扫；同时试 Dune 快方案 | Dune 因 402 datapoint 限额失败；全量重扫跑完但最终合并 exit 1（DuckDB 空 part bug） |
| 08-19 | 用户令"继续完成 −1"。codex 同步 skill 到 **v6.50.0**（v4 7 元组硬门禁），证实旧 16 条 owner-correction 是假修正（`repairs=[]`），旧 v3 缓存缺 tx_index 不可迁移 → **第三次全量重采**。用户质问"为什么又重采"，令先停；codex 说明后用户批准"从 v4 断点恢复" | v4 全量 26,515,100 条严格 7 元组，0 缺口 0 重叠，producer 哈希 ACTIVE，验收 PASS |
| 08-20 00:18 | 旧冻结快照 producer 哈希不匹配 → 批准刷新快照到 slot 440,368,381 并增量扩边 | 26,595,333 行 |
| 08-20 01:40 | **A2 精确对账 FAIL**：供应闭合，但 **3 负余额＋23 快照不匹配＝26 个残差 owner，残差总和 0** → `gate_pass=false`，codex 写 anomalies 停工、handoff 标 BLOCKED | 申请 26 owner 定向补证 |
| 08-20 02:35 | 3 个负余额账户补证：Helius getBlock 有、**SQD 同 slot 只返回块头没 tokenBalances** → 3 笔交易 SQD 漏记实锤（双源原始文件带哈希） | 修得了 2 个负余额，PNLC 仍残差，24 owner 未闭合 |
| 08-20 02:37 | codex **主动修正**："只批 24 地址补证仍完不成 −1"——审计出 5 条：`replay_edges.py` 只认 `fetch_sqd_transfers_v2.py/v4` 登记缓存；采集器只能从 SQD 产数；registry 无 Helius 替换式修复生产者；冒用哈希＝虚假溯源；`window_fetch.py` 是窗口收据协议。给两路线：①补证＋给 skill 加修复生产者；②等 SQD 上游补数 | 标 BLOCKED |
| 08-20 03:44 | 用户裁决："批准 24 地址窄范围补证，**skill 不批准修改**" | 补证完：60 候选/48 缺失，仍 24 residual |
| 08-20 05:52–14:03 | 用户问"怎么才能闭合"→codex 做全量差分（61 笔缺边，残差 24→**10**，L1 消 94.5%——**全程最佳时刻**）→ 用户下令："在 skill 暂不修改的条件下继续争取**数学清零**，目标是通过清零看 skill 该怎么改" | 从此任务目标变成"清零" |
| 08-20 14:43→08-21 03:41 | 逐轮申请最小外延：12 账户/两个 ±20k slot 窗口/1,783 笔 → 残差 10→**53**（42 个新对手方）→130 笔→69→1 笔→70→54 账户签名页→39 笔→76→6 笔…… 用户多次"批准"，最后 08-21 03:41 **"在数学清零前你的操作我都批准"** | 残差单调上升，codex 解释为"残差搬家/交易图前沿未闭包" |
| 08-21 05:05→09:34 | 第 3 轮撞到合法 burn（脚本假设每笔 owner 净和为 0）停；用户 09:15 要求"大白话解释非零原因"；codex 给出"SQD 漏记＋错记、总量对分配错、26→270 是前沿扩张"的解释；用户令"继续追完全部遗漏交易" | 写成**无人值守自动循环**（唯一停止条件：清零或 200 轮） |
| 08-21 10:03→08-23 03:59 | 自动循环 172 轮、历史外延 902 个 20k-slot 范围；累计处理 89,041 身份、41,967 笔"替换"；残差 315→457→585→738→834→974→**990**（第 154 轮后完全空转）；Helius getTransaction 89,624 次＋签名页 1,956 次；08-22 两次汇报均"运行健康但离清零不可量化" | 用户 08-23 03:58 **"暂停一切，我觉得你方向跑偏了"**；codex 终止 3 进程、删监控、保留全部产物 |

**codex 守住的底线**：没改 skill、没动正式 v4 缓存、没冒用哈希、每步留证可审计、逐次申请批准。**codex 的短板**：把"诊断"升格成"清零"后没有止损判据、没有归因、身份键错用（见 §3）。

### 1.2 Claude Code 会话（Fable 调度，08-20 03:23 → 08-23 08:06 UTC）

| 时间(UTC) | 用户问/令 | Fable 做了什么 / 结论 |
|---|---|---|
| 08-20 03:23 | "到底是 skill 有问题还是 codex 有问题？" | 逐条核实 codex 5 条论断**全部属实**：不是 bug，是**设计空白**（防伪体系隐含"SQD 数据完整"假设，无受控修复门）；SQD 漏记是管线级问题（影响所有 Solana 案） |
| 08-20 03:42/03:47 | "不改 skill 能完成 −1 吗？能不能告诉 −2 的 AI 特殊处理？" | **不能**：handoff 状态由 AUTO_GATES 从产物自动读、禁人工声明；−2 第一步 `handoff_manifest.py verify` 对 BLOCKED exit 2 拒收；"特殊处理"只剩裸奔或造假两条路 |
| 08-23 03:27 | "codex 清零几十小时没清零，方法有没有问题？" | **方向性错误**：逐笔补账追开放集合不收敛；无止损线；两天没归因；没给残差分类。承认调度疏漏（放行补证时未设止损/预算/汇报节点） |
| 08-23 03:59 | 裁决三条：叫停循环；任务改"归因＋分类"；报 Helius 用量 | 循环已被操作者侧停（03:59）；派 codex 工单（Helius≤500/SQD≤50、30 分钟无进展即 BLOCKER、完成即停）。首派 6 分钟硬停（沙箱不通外网→报错回显含 key 的 URL）→ 建议轮换 Helius key；续跑 27 分钟交诊断报告，验收 PASS |
| 08-23 04:53 | 报告四答案 | SQD 漏"DEX CPI depth-2 行"硬下界 13,425 笔；990 残差＝218 漏/0 归属差/739 伪影；41 候选 15 受影响；Helius 估 ≥121 万 credits。**Fable 保留两点**：739"伪影"标签偏强；最关键没分清"数据集真缺 vs 问法错" |
| 08-23 05:03 | "先做第①个，弄清楚到底什么问题" | Fable 本机亲跑 4,257 次 SQD 免费探针＋7 次 Helius getBlock：**①不是问法问题**（7 种问法/两端点/整块无过滤/±5 slot 全无）；**②真根因＝SQD 按 slot 区段漏全部 durable-nonce 交易**（3 实锤块 nonce 403/403 缺、在场 0 笔 nonce；跨时代 4 健康块 nonce 全在）；稠密地图钉 **38 段 6,632 slot（2026-06-13/15/16）**；**③撞破更大的坑：SQD transactionIndex＝去投票后重编号≠RPC 位置** → codex 报告的 13,425/Meteora-Raydium/335-38/218-739 全建立在编号错位污染样本上（抽 80 块 404 笔按签名 404/404 都在 SQD）→ 正式勘误；循环发散机制＝双计 |
| 08-23 05:59 | "改完 skill 能解决 SQD 缺交易吗？缺的数据怎么补？" | **改 skill 补不了数据，但不改 skill 也补不进去**。补数只有"换源按区段重抓"：路 A Helius 逐块 getBlock（推荐）/路 B Dune·BigQuery（只配做复核源）/路 C 等 SQD 重灌（不可控） |
| 08-23 06:03 | "先试试路 A 能不能走通，数据补不上改 skill 也没用" | 试跑 426 slot：426/426 成功、blockhash 一致、SQD 全子集；循环已知 16/16 找到、owner 净额逐字节一致；20 条修复边；FmVGD/2T5WL/265q1W 精确归零；4,260 credits。**路 A 走通** |
| 08-23 06:32 | "跑剩余 36 段，先把 ARC 数学清零，再看怎么改 skill；codex 干活你验收" | Fable 本机拉 6,206 slot（62k credits/42 GB/54 分钟）→61 边；codex 离线影子对账（两轮工单）；并入 81 条后 22/26 归零，剩两对等额反向残差；**余额连续性二分**（SQD 免费）＋金库 pre/post 断点 → 拉 56 块抓到最后两笔（单 slot 缺陷 426,869,468 ＋ 地图跨度外 427,406,628）；**83 条边并入 → 负余额 0/不匹配 0/供应差 0/26/26 CLOSED/新增 0**，codex 影子对账与 Fable 独立重放逐值一致。**检测器定型**："SQD 有块头但零 AdvanceNonce ＝ 缺陷候选"逐 slot 判（6/6 命中 0 误报），游程阈值法作废 |
| 08-23 08:06 | "把会话 ID 发给我" | 会话结束。待裁决：skill 三处改动设计、ARC −1 去向、Helius key 轮换 |

---

## 2. 为什么原版 skill 会被 ARC 卡住（大白话）

用"记账系统"比喻：skill 的规矩是 **只有 SQD 拉回来的流水单才算正式凭证，每张凭证都要盖官方采集器的章（哈希），账本必须和银行当天余额逐户分毫不差才放行**。这套规矩本身是对的（防造假、防装死），但它隐含了一个没人写出来的假设——**SQD 的底账是完整的**。ARC 案把这个假设踩穿了。锁死的四个环：

1. **数据源缺数据（环一，根因）**：SQD solana-mainnet 数据集在 2026-06-13/15/16 的 **38＋ 个短区段（合计 6,632＋ slot，最长 926 slot≈6 分钟）** 里把所有 **durable-nonce 交易**（交易所提币/做市/机器人离线签名常用，第一条指令是 System `AdvanceNonceAccount`）**整笔丢掉**，区段内 nonce 交易 100% 缺（外加 ~0.5% 零散非 nonce 交易）。ARC 恰有 70 笔成功的 nonce 转账落在这些区段（其中 #1 大户 u6PJ8→44P5Ct 的 673.9B raw 大额流水 SQD 完全看不见）。缺陷可短至 1 个 slot、可出现在地图跨度之外（后两笔即是）。真实缺口≈供应 0.145%，但触及 41 候选中 5 个、Top200 中 9 个。
2. **唯一合法生产者只会从这个数据源产数（环二）**：`fetch_sqd_transfers_v2.py` 是 producer registry 里唯一的 Solana 全史采集器；它查的就是 SQD tokenBalances；SQD 没有的它永远产不出来。v4 采集器自身验证 PASS（0 缺口 0 重叠、哈希命中）——**它是清白的**，DISTINCT 吃边 bug 已被 v6.49.0 修好。
3. **对账门（环三）——纪律性 fail-closed，且机器层有缺口**【codex 修正后表述】：A2 精确重放对账（`replay_edges.py reconcile`）= 整数重放 vs 链上冻结快照逐 owner 相等；负余额/快照不匹配/供应差/残差任一非零 → `gate_pass=false`。按流程纪律执行者必须写 anomalies 停工、handoff 标 BLOCKED → −2 第一步 `verify` exit 2 拒收。ARC 是 codex 守纪律停下的。**但机器层其实有缺口**：handoff READY 必备件只强制四查 wrapper `reconciliation_report.json`（Solana 的 balance/time 生产者是 `anchor_sampler.py` 日级锚点抽样，文档自述"静止大户系统性漏观测"），**并不强制读 `data/reconcile_receipt.json` 的 `gate_pass`**；精确 gate_pass 只在 −2/−3 序列编译（`camp_series_provenance.py:522`）才被强制。→ 一个不守纪律的执行者理论上能 generate READY 带病进 −2。这是本轮必须一并堵的洞（§4.4.4）。
4. **防伪闸不认任何外来数据（环四）**：`sqd_cache_identity.py:40-55/65-73` 只接受 meta 为 `sqd-solana-cache/v4` 且 `collector_sha256` 命中 `fetch_sqd_transfers_v2.py` 登记哈希的缓存；registry 没有任何"替换式修复生产者"；`window_fetch.py` 是窗口收据协议不能产全史缓存；`replay_edges.py` 只读单文件无合并入口；冒用哈希被负测试当场拒（codex 实跑证明）。

→ **环一缺 × 环二只会从环一拿 × 环三不放行 × 环四不让补 = 诚实执行者被锁死**。skill 侧的性质：不是 bug，是**两处设计缺陷**【codex 补充】——①正式验收只验缓存身份/格式/producer 哈希，不验 SQD 数据集覆盖，也没有受控修复通道；②文档 `data-pipeline-solana-capture.md:94/156-157` 写着"签名可按位置反查 / signature→(slot,tx_index) 经 getBlock 映射"——**前提错误**（SQD 的 tx_index 是去投票后重编号，不是链上位置），代码没踩（对账用 slot+owner 粒度），但直接误导了后面 codex 的清零循环。

附带两个"为什么拖了这么久"的非根因因素：① 08-12 起三次全量采集（v3→owner-correction→v4），前两次因 skill 升版 v4 硬门禁作废（旧 v3 缺 tx_index 不可迁移）；② 08-18 第一次对账的 47 项残差被误判为"owner 变更漏记"追了一整天（后证 `repairs=[]`，真凶是 DISTINCT 吃边，v6.49.0 修）。

---

## 3. 为什么 codex 的"数学清零"在数学上清不了零 ——以及最后是怎么清零的

### 3.1 codex 的方法（逐账户 BFS 补账）
发现某 owner 残差 → 拉该账户签名页 → 逐笔 `getTransaction` → 与正式 v4 按 **(slot, tx_index)** 比对 → 正式里没有的判"缺失"补入 → 对手方因此出现新残差 → 再拉对手方……（自动循环：每轮冻结一个 20k-slot 历史外延范围重复上述过程）。

### 3.2 三层原因，层层致命

**第一层（致命 bug）——身份键错位 → 双计 → 发散。** SQD 的 `transactionIndex` 是**去掉投票交易后从 0 重新连续编号**（健康块 439000000 实测：== 非投票序号 438/438，== 绝对位置 0/438），而 codex 拿 Helius getBlock 的**绝对位置**去 SQD 的 (slot, index) 集合里找；找不到就判"SQD 缺失"——其实抽 80 块 404 笔**按签名 404/404 都在 SQD**、正式缓存里对应边都在。于是循环把缓存里本来就有的交易又补了一遍：A 多记 100、B 少记 100 → 每补一笔假缺失就**制造一对新的假残差**。这就是 26→10→53→69→…→990 发散、"每补 100 笔多 2 个不平账户"、总和恒 0（后来 −60,954＝合法 burn）但 L1 膨胀到 3.49% 供应的机制。codex 报告里的"硬下界 13,425 笔""Meteora/Raydium CPI 特征""335/38 同 index 冲突""218/739 分类""全史 667,186 笔"**全部是编号错位的假象**（已正式勘误，FINDINGS §5）。
> 这一坑的根子在 skill 文档 capture.md 的错误前提，codex 按文档办事——这点要公平记。

**第二层（结构缺陷）——即使身份键对了，逐账户 BFS 也证明不了"补全"。** 真正的漏记是**按 slot 区段（时间）分布**的，不是按账户分布的；BFS 只能补"已知账户"的交易，永远不知道还有谁参与过，没有任何停止判据能告诉它"补到这里就全了"。循环 48 小时落盘的真缺 nonce 交易只有 59 笔，而全集是 70 笔成功交易——**少的 11 笔里就有最后两对残差**。反过来，按区段逐块扫（路 A）一次就拿到全集，且每笔自带"SQD 普查无＋Helius 块内有"的双源证明。

**第三层（调度/方法论）——目标跑偏、无止损、无归因。** 用户 08-20 14:03 把任务从"补证/诊断"改成"数学清零"；发散信号 08-20 下午（10→53）就出现，codex 解释成"残差搬家、前沿未闭包"继续扩，08-21 写成无人值守循环，唯一停止条件＝清零或 200 轮；两天没做"SQD 漏的到底是哪类"的归因，也没区分漏交易/归属差异/伪影。Fable 这边也有责任：放行补证时没给止损线/RPC 预算/汇报节点（已写入调度纪律）。

### 3.3 为什么最后清得了零（方法对了就 4 小时），以及"清零"的边界
**根因先行**（7 种问法证明不是问法问题 → nonce 交易区段性缺失 → 稠密地图 38 段）→ **正确身份**（签名，不是 index）→ **正确缺失集定义**（缺陷区段内 Helius 块签名集 − SQD 同 slot 签名集）→ **同口径产边**（skill 自带 `owner_deltas_by_tx`/`pair_tx` 一行没改）→ **独立真值互证**（循环已知 43/43、16/16 逐字节一致）→ **漏网补捞**（余额连续性二分定位单 slot 缺陷/跨度外缺陷）→ 83 条边 → 26/26 归零、新增 0、非残差 owner 零触及（两套算法互证）。成本：Helius ≈69k credits（月额 1M）、SQD 免费 ≈1 万次、4 小时。对比 codex：Helius ≈9 万次（估 ≥121 万 credits）、48 小时、残差 990。

**边界（【codex 补充】必须写明）**：期末 A2 清零 ≠ 历史边完整——一笔漏记若"先转出后转回"、或相关账户已销户，期末余额可完全抵消而 A2 看不见（文档 capture.md §12 本就承认销户路径逃过快照对账）。所以覆盖探针不能只在 A2 FAIL 时才跑（见 §4.1）；本次证明的是"ARC 的账能平"，不证明 38＋2 处就是 SQD 的全部缺陷。

---

## 4. 修复方案 · skill v6.52.0「SQD 覆盖闸 ＋ 修复生产者窄门」详细设计（r6 定稿）

### 4.0 一句话 ＋ 用户裁决如何落进设计 ＋ r5→r6 变更摘要
**不碰 v4 采集器、不改 7 元组协议、base 缓存不可变、不重采**——新增两件工具（①探针：列出 SQD 的"坏 slot"名单，逐 slot 计数阵列可被任何人重算；②修复生产者：只对坏 slot 从 Helius 按签名补回本 mint 的边，产出"不可变 base ＋ 独立修复层 ＋ 可重建合并缓存 ＋ 绑定三者的 bundle"，按**代（generation）**内容寻址、发布顺序崩溃安全、指针"比较再换"），把闸接到必经之路（Solana 精确对账升为受控对账第五项并进 READY 硬闸；覆盖报告是精确对账的强制输入；修复缓存只认登记过的修复生产者；所有正式入口经 resolver；**所有 Solana 派生产物与精确对账收据交叉绑定同一份边源**；validator 离线独立重算），最后改正错误前提的文档、加判例 S-12、加调度纪律。

用户 8 条裁决（§7）的落点：①立项＋本文件即详细计划→codex 复核→用户审批；②采集器不升 v5；③探针务实模式（共享地图）；④**参考源无预算上限、无公共 RPC 备胎**——工具只记台账不设闸，配额错误结构化识别后干净停工并汇报（用户自行换 key）；⑤ARC 正式修复走 Helius live（≈68k credits）；⑥共享全史缺陷地图做、**不向 SQD 报缺陷**；⑦Helius key **不轮换**（用户接受风险，记录在案）；⑧codex 报告数字勘误写进判例与 CHANGELOG。

**r6→r7 变更摘要（源自 codex r6 复核 4 项窄阻塞，Fable 核实后全部采纳）**：(1) **消除哈希环**：合并缓存 meta 不再含 bundle 哈希/gid，只含 `plan_digest`＋base 哈希；gid 标签只出现在 bundle 与指针；绑定方向单向 bundle→各文件（4.2.3 依赖图）；(2) **目录持久化**：改名前 fsync 代目录、切 CURRENT 后锁内 fsync 指针父目录（`publish_overwrite` 只 fsync 文件内容）；(3) 规范化里**金额用 JSON int**（与 v4 `validate_edge_row` 正整数契约一致），不再写"十进制字符串"；(4) getBlocks 结果**落盘位图实物**并绑定（validator 可离线验长度/popcount/范围，原数组单调唯一为生产时断言＋live canary 可复核）；(5) **repaired 组合规则收紧**：代绑定的 resolution 重算必须为 DEFECTS_CONFIRMED、每条修复交易/每个重映射 slot 有 confirmed census 支撑、当前 coverage 全部候选 ⊆ 当前代 census slot 集（新候选未覆盖 ⇒ FAIL）。

**r5→r6 变更摘要（源自 codex r5 复核 4 项设计阻塞＋补丁，Fable 核实后全部采纳）**：(1) **删除"撤销代退回 base"**——SQD 事后回填不会补进不可变的旧 base，退回 base 等于再丢边；定案：**一旦发布修复代，base 永不再是该案正式账本**；SQD 回填后旧代仍有效（其证据是历史事实）；新候选/映射无解 ⇒ 新代 supersedes 旧代；**base 重采（edge_sha 变化）⇒ 旧代自动作废**（resolver 校验代绑定的 base 哈希）；(2) 发布顺序改为 **pending 内写齐含 bundle（最后、fsync）→ 原子改名 gen-<gid> → fsync 父目录 → 锁内 CAS 切 CURRENT**（`supersedes == 切换瞬间 CURRENT.gid`），崩溃任一点可恢复、`--resume` 对已完成 gen 幂等补发指针；(3) gid/plan_digest 规范化**写死**：`json.dumps(sort_keys=True, separators=(",",":"), ensure_ascii=False)` UTF-8、整数用 int、金额用十进制字符串、表按指定键排序、并纳入 `kind`/`supersedes`；(4) getBlocks `complete` 由机械条件派生（成功响应、区间 ≤500,000、数组严格递增唯一且 ⊂[from,to]），不信生产者布尔；(5) **wave-scan/v4→v5、flow-anomaly/v2→v3** 承载 `edge_source_binding`（破坏性契约变更必须升版，scan-schemas 既有规则）；curve/audit_closed 等非 READY 必备件"在场或被引用即强制绑定并验证"；(6) wave/flow/entity 显式路径必须配 `--case-root`（拒 symlink、不猜 cwd）；(7) producer 登记统一为 **6 条**；(8) validator 增加可选 `--live-canary N`（联网抽检证据块 blockhash/签名集，opus 攻击验收用）。

### 4.1 以后 Solana 代币怎么清零 —— 标准作业流程（SOP）

```
−1 阶段（Solana 案）
 A1 v4 全史采集（fetch_sqd_transfers_v2.py，不变）→ base 缓存 data/soltx-<h>.jsonl.gz ＋ .meta.json（此后不可变；任何程序不得回写；重采＝新 base，旧修复代全部作废）
 A2.0 ★SQD 覆盖探针 sqd_coverage_probe.py → data/sqd_coverage/<probe_id>/{coverage_map.json, slot_counts.bin.gz, ledger.jsonl} ＋ CURRENT.json 指针（不可变、内容寻址）
      策略（务实模式，用户裁决③）：复用未过期的共享全史缺陷地图 ＋ 全扫地图未覆盖/新增区间 ＋ 逐 slot 复核地图命中的已知缺陷/已驳回 slot ＋ 确定性健康 canary 复核
            ＋ 确定性历史抽样（只作附加证据，不计入覆盖并集）＋（A2.2 β 兜底）；地图过期/SQD 指纹变化/canary 任一变动 → 自动升级为逐案全区间扫
      判法：逐 slot 四态 HEALTHY（块内 ≥1 AdvanceNonce）/ NO_HEADER（SQD 无块头）/ DEFECT_CANDIDATE（有块头但零 nonce）/ ERA_UNCERTAIN（零 nonce 但时代指纹无效）；
            NO_HEADER 经参考源 getBlocks（finalized）核对 → SKIPPED_CONFIRMED 或 MISSING_BLOCK 候选；核对不成立 ⇒ 保持 unconfirmed ⇒ INCONCLUSIVE；
            时代校准（冻结参数）：1,000,000-slot 窗，ratio＝有 nonce 块/有块头块 ≥ 0.99 且有块头块 ≥ 10,000 才视为指纹有效；
            候选一律须在 A2.2 由签名普查确认；未确认 ⇒ 有效 verdict=INCONCLUSIVE
      verdict ∈ {NO_KNOWN_NONCE_OMISSION_DETECTED, DEFECTS_CONFIRMED, INCONCLUSIVE}——只描述"已知 omission class"，不声称完整覆盖
 A2.1 精确重放对账 replay_edges.py reconcile（四项判据不变：负余额/快照不匹配/供应差/逐 owner 残差）
      新增：coverage 为强制输入（存在、覆盖并集 ⊇ [from_slot, finalized_upper_slot]、producer 登记、SQD 指纹一致）；resolver 决定消费 base 还是修复代；
            receipt 升 solana-reconcile/v4（envelope 化，直接绑定 soltx_edges/meta/coverage/resolution/bundle）；
            组合规则：cache_kind=base 只允许有效 verdict=NO_KNOWN…；cache_kind=repaired 合法 ⇔ 当前代绑定的 resolution 重算为 DEFECTS_CONFIRMED ∧ 每条修复交易/每个重映射 slot 有 confirmed census 支撑
            ∧ 当前 coverage 全部候选 ⊆ 当前代 census slot 集（最新 coverage 可为 NO_KNOWN…，但出现未被当前代覆盖的新候选 ⇒ FAIL）；INCONCLUSIVE 一律 FAIL；
            finalized_upper_slot == 快照 slot == --as-of-slot（不再允许 >=）
 A2.2 若 coverage 有候选，或 A2.1 有残差 → ★修复生产者 sqd_gap_repair.py（产出一个新"代"）
      α（按清单）：对每个候选 slot：Helius getBlock(full) ＋ SQD 同 slot 全交易普查（index,signature,err,blockhash）→ 按签名差集 →
           确认分类：missing_nonce>0 ⇒ confirmed_nonce_defect；仅非 nonce 差集 ⇒ confirmed_other_defect；整块无 SQD 头 ⇒ confirmed_missing_block；差集空 ⇒ refuted
           → 只取本 mint 的 pre/post tokenBalances，err==null 的交易 → owner_deltas_by_tx/pair_tx 产 7 元组边（一笔交易可多边，按签名分组落盘）；
           该 slot 的 base 边 ＋ 修复边整块统一到参考源"非投票序号"（映射须双射，见 4.3.3）；逐 slot 落盘双源规范化证据表
      β（残差驱动兜底）：对残差 owner 做"余额连续性二分"（SQD 免费 tokenBalances 探针，每 owner ≤40 次）定位首个对不上的 slot → 断点邻域探针指纹 → 纳入候选 → 回 α
      前置一致性检查（每 slot，生产时）：coverage 阶段与 repair 阶段 SQD 签名集哈希一致、拟修复签名当前仍不在 SQD、blockhash/查询体/端点一致；任一变化 → 本次生产中止（已发布旧代不受影响）
      产物：施工目录 data/sqd_repair/<h>/pending-<plan_digest>/ → 写齐含 bundle.json → 算 gid 原子改名 gen-<gid>/ → 锁内 CAS 发布 data/sqd_repair/<h>/CURRENT.json（kernel 收据）
      止损（方法论，不是花钱闸；用户裁决④＝无预算上限）：β ≤3 轮；残差 owner 数不降反升即停；修复后 A2.1 仍 FAIL → BLOCKED（写 anomalies）；禁止逐账户 BFS 补账、禁止"再找几笔"；
            Helius 配额/限流（结构化 402/429 或配额错误体）→ 首次确定性配额错误即停止派发、落盘 pending-<plan_digest>/STOPPED.json、汇报，用户换 key 后 --resume 续跑
 A2.3 重跑 A2.1（resolver 解析修复代）→ gate_pass=true → 受控对账 runner 第五项 exact_reconcile PASS → A3（所有派生产物绑定同一边源）→ handoff READY
```
大白话：先用免费探针把 SQD 的"坏块"名单列出来（整张逐块计数表可被别人重算）→ 只对坏块从第二家（Helius）拉原始块、只补 SQD 确实没有的交易 → 坏块整块按链上真实顺序重新排号 → 每笔补账都带"SQD 没有＋Helius 有＋两家块哈希一致"三重证据 → 原始账本一字不动、补丁按"代"单独存、合并账本可随时重算、指针最后才切且切前要核对"我接的是不是当前那一代" → 重新对账 → 账平才放行，而且后面所有分析产物都必须注明用的是哪一代账本，和对账收据对得上 → 账还不平就按规矩停下写报告，**不再允许无限追账**；修过账的案子不会再退回原始账本（原始账本缺的边不会自己长回来），除非整个重采。

### 4.2 数据协议与 schema（逐字段；全部登记进 `references/scan-schemas.md`）

#### 4.2.0 规范化与哈希（全工程统一，写进 `sqd_repair_core` 与独立 validator 两份实现）
- 规范化 JSON＝`json.dumps(obj, sort_keys=True, separators=(",",":"), ensure_ascii=False).encode("utf-8")`；**整数字段（含 slot/tx_index/ts/金额 `amt`）一律 JSON int**（Python 任意精度整数，与 v4 `validate_edge_row` 正整数契约一致，`spl_edge_core.py:19-35`）；签名/地址/哈希用原文字符串；禁止浮点、禁止把整数写成字符串。
- **绑定依赖图（无环）**：`evidence/*` → `evidence_manifest` → `coverage_resolution`（含 plan_digest，不含 gid）→ `repair_layer`（header 含 plan_digest）→ `slot_index_map` → `merged 边文件` → `merged meta`（含 plan_digest、base 哈希，**不含 bundle 哈希/gid**）→ gid（由以上规范化内容计算）→ `bundle.json`（含 gid、以上全部文件的 `{path,size,sha256}`）→ `CURRENT.json`（含 gid、bundle 哈希）。gid 标签只出现在 bundle 与指针；validator 对 repaired meta 的绑定方向＝从 CURRENT→bundle→`merged.meta_sha256` 单向核对，并要求 `meta.plan_digest == bundle.plan_digest`。**统一规定——必须含 `plan_digest` 的文件**：coverage_resolution、repair_layer header、slot_index_map header、merged meta、bundle、STOPPED.json；**不含**的文件：evidence/*（由 evidence_manifest 哈希绑定）、evidence_manifest、merged 边文件、CURRENT（含 gid 与 bundle 哈希即可）。validator 要求上述"必须含"的文件 plan_digest 全等，且 bundle.gid 重算一致。
- 表排序：census 按 `slot`；transactions 按 `signature`；每笔 `edges` 按 `edge_sort_key`；slot_index_map 按 `slot` 再 `sqd_index`；evidence_manifest 按 `path`；candidate_slots 按 slot 升序去重。
- `plan_digest`＝sha256(规范化{base.edge_sha256, base.meta_sha256, coverage.probe_id, coverage.map_sha256, candidate_slots, mode, reference.kind, reference.endpoint_fingerprint, producer.sha256}) 前 16 位。
- `gid`＝sha256(规范化{plan 输入全部字段, kind:"repair", supersedes:<gid|null>, census 表, transactions 表, slot_index_map 表, evidence_manifest 表, mode, reference.source}) 前 16 位。**进入 gid 的任何内容都不含 gid 字段**；文件中的 `gid` 只是标签，validator 重算比对。

#### 4.2.1 探针产物（不可变、内容寻址）`data/sqd_coverage/<probe_id>/`＋`data/sqd_coverage/CURRENT.json`
- `probe_id`＝coverage_map 规范化内容（去 `probe_id` 字段）sha256 前 16 位。
- `coverage_map.json`（`sqd-solana-coverage/v1`）：`schema/version`、`chain/mint`、`producer{path,sha256}`、`sqd{endpoint_fingerprint, dataset:"solana-mainnet", metadata_normalized{dataset_id,start_block,real_time,…}, metadata_sha256, finalized_head_at_scan, query_body_sha256}`、`scan_ranges[{from_slot,to_slot,mode:"full"|"map-reuse"|"recheck"}]`（**并集必须 ⊇ 案区间；`sample_ranges[]` 另列不计入并集**）、`era_params{window:1000000,min_headers:10000,min_ratio:0.99}`（冻结）、`slot_counts{path:"slot_counts.bin.gz",size,sha256,from_slot,to_slot,encoding:"u8: 0=UNSCANNED, 1=NO_HEADER, 2=HEADER_ZERO_NONCE, n>=3 → nonce_count=n-2 (255 饱和)"}`、`skipped_confirmation{method:"getBlocks",commitment:"finalized",reference_head_at_check,endpoint_fingerprint,blocks_bitmap{path:"blocks.bin.gz",size,sha256,from_slot,to_slot,encoding:"u1 per slot, 1=getBlocks 列出该 slot"},ranges:[{from,to,response_sha256,count,response_ok,array_monotonic_unique:bool}]}|null`（**`complete` 不落盘为自报布尔，由 validator 从位图实物机械派生**：response_ok ∧ to−from+1 ≤ 500,000 ∧ reference_head_at_check ≥ to ∧ 位图该段长度 == to−from+1 ∧ popcount == count ∧ count ≤ 区间长度；原数组"严格递增唯一、⊂[from,to]"为生产时断言并记录，`--live-canary` 可重查若干段与位图切片对表——诚实边界：离线只能验位图自洽，不能重放 RPC 响应）、`shared_map{asset_path,version,sha256,supersedes,generated_at,reused_ranges[],canary{slots[64],counts_sha256,verified_at}}|null`、`ledger{path,size,sha256,requests,success_ranges_sha256}`、`summary{…（饱和计数）}`与 `verdict`（**派生展示值，validator 必须从 slot_counts 重算**）。
- `slot_counts.bin.gz`：案区间逐 slot u8 阵列——validator 由它重算四态、时代校准、候选清单与 summary；**强制：无 UNSCANNED 残留、解压长度 == to−from+1、ledger 成功区间并集无洞且 == scan_ranges 并集**；canary 可对任意 slot 免费重查 SQD。
- `ledger.jsonl`：逐请求 `{seq, ts, query_body_sha256, from, to, http_status, bytes, response_sha256, slots_covered, ok}`。
- 探针产物一经写出不再修改；再跑产生新 `probe_id` 并重指 CURRENT（旧目录保留）；`CURRENT.json` 为 kernel 收据（`sqd-solana-coverage-pointer/v1`，PASS），锁内发布。

#### 4.2.2 修复层 `gen-<gid>/repair_layer.jsonl`（`sqd-solana-repair-layer/v1`，按签名分组）
首行 header：`{"schema":"sqd-solana-repair-layer/v1","mint":…,"plan_digest":…,"base":{"edge_sha256":…,"meta_sha256":…},"coverage":{"probe_id":…,"map_sha256":…},"reference":{"kind":"helius-getBlock","endpoint_fingerprint":…},"producer":{path,sha256}}`（含 plan_digest、不含 gid）；
其后每行一笔交易：`{"signature":…,"slot":…,"reference_position":int,"nonvote_ordinal":int,"nonce":bool,"class":"nonce"|"other"|"missing_block","edges":[[ts,slot,nonvote_ordinal,-1,from,to,amt],…],"evidence":{"sqd":"evidence/<slot>.sqd.json","ref":"evidence/<slot>.ref.json"}}`——**唯一键＝signature**（一笔交易可多边，`pair_tx` 语义），`edges` 内按 `edge_sort_key` 排序；只含 `meta.err==null` 的交易。

#### 4.2.3 代目录、bundle、指针与发布协议
- 目录：`data/sqd_repair/<h>/pending-<plan_digest>/`（施工期）→ `data/sqd_repair/<h>/gen-<gid>/`（完成后原子改名）；`data/sqd_repair/<h>/CURRENT.json`（指针）；`data/sqd_repair/<h>/.lock`（发布锁）。`<h>`＝sha256(mint) 与 base 同键（大小写敏感，多 mint 天然隔离）。
- `bundle.json`（`sqd-solana-repair-bundle/v1`）：`{schema, mint, plan_digest, gid, kind:"repair", mode:"formal"|"exploration", producer, base{edge_file,meta_file,edge_sha256,meta_sha256,edge_logical_sha256,edge_rows,finalized_upper_slot}, coverage{probe_id,map{path,size,sha256},slot_counts{…}}, coverage_resolution{path,size,sha256}, repair_layer{path,size,sha256,transactions,edges}, slot_index_map{path,size,sha256,slots}, evidence_manifest{path,size,sha256}, merged{edge_file,meta_file,edge_sha256,meta_sha256,edge_logical_sha256,edge_rows}, reference{kind,endpoint_fingerprint,source:"live"|"local-evidence-cache"}, rpc_ledger{path,size,sha256,requests,credits_estimate}, supersedes:<gid>|null, generated_at}`。
- 恒等式：`merged.edge_rows == base.edge_rows + repair_layer.edges`；`mode=="formal"` ⇔ `reference.source=="live"`；exploration 代**不得发布指针**；refuted-only（无 confirmed、无 remap/add）**不产代、不发指针**。
- **发布协议（崩溃安全，按 4.2.0 依赖图顺序）**：①pending 内按依赖图用 `publish_exclusive` 依次写 evidence/evidence_manifest/resolution/layer/map/merged 边/merged meta（各文件含 plan_digest、不含 gid/bundle 哈希）并逐文件 fsync → ②算 gid（4.2.0）→ ③pending 内最后写 `bundle.json`（exclusive，fsync）→ ④自验（深验）→ ⑤**fsync pending 目录本身**（`os.open(dir)`＋`os.fsync`；`publish_*` 只 fsync 文件内容）→ ⑥`os.rename(pending-<plan_digest>, gen-<gid>)` 原子改名 → ⑦fsync 父目录 `data/sqd_repair/<h>/` → ⑧取 `.lock`（`fcntl.flock` 独占）→ 读 CURRENT → 校验 `bundle.supersedes == CURRENT.gid`（无 CURRENT 时须为 null）且 `bundle.base.edge_sha256 == 案根 base 当前哈希` → `receipt_kernel.publish_overwrite` 写 CURRENT（PASS 收据 `{schema:"sqd-solana-repair-pointer/v1", target{chain,token,as_of_block=base.finalized_upper_slot}, mode:"formal", verdict:"PASS", exit_code:0, producer, inputs{bundle{path,size,sha256}}, gid, supersedes, published_at}`）→ ⑨**锁内 fsync 指针父目录** → 释放锁。CAS 失败（CURRENT 已被更新代抢先）⇒ 本代保留为孤儿、报错退出，不覆盖。
- **崩溃恢复**：①–⑤崩溃 ⇒ pending 残留，`--resume` 按 plan_digest 续（已写文件按哈希复用，bundle 重算）；⑥–⑦崩溃 ⇒ rename 原子，只存 pending 或 gen 之一；⑧前崩溃 ⇒ gen 完整但无指针：`--resume` 发现 gen-<gid> 含自洽 bundle 即只做 ⑧⑨（幂等补发）；resolver 始终只认"CURRENT 有效 ∧ inputs.bundle 哈希命中 ∧ bundle 自洽 ∧ bundle.base.edge_sha256 == 当前 base"的代，`pending-*`/孤儿 `gen-*` 一律忽略。
- **代的生命周期（定案，取代 r5 的撤销代）**：base（无指针）→ gen-A（formal）→ [新候选/映射无解] → gen-B supersedes A；SQD 事后回填**不改变**任何已发布代的有效性（其证据是采集当时的历史事实，merged 数据仍正确）；**base 重采**（`data/soltx-<h>.jsonl.gz` 哈希变化）⇒ 所有代自动失效（resolver 校验不过 ⇒ 硬错，提示重跑探针/修复）；**不存在"退回 base"的正式路径**——旧 base 缺的边不会因 SQD 回填而出现在旧 base 文件里；用户若要"不用修复代"只能走 exploration 或重采新 base。

#### 4.2.4 `coverage_resolution.json`（`sqd-solana-coverage-resolution/v1`，由修复生产者写，探针文件不动）
`{schema, mint, plan_digest, coverage{probe_id,map_sha256}, census:[{slot, state_in_map, result:"confirmed_nonce_defect"|"confirmed_other_defect"|"confirmed_missing_block"|"refuted", sqd_tx_count, sqd_blockhash, ref_tx_count, ref_nonvote_count, ref_blockhash, missing_total, missing_nonce, missing_err_excluded, evidence{sqd{path,size,sha256}, ref{path,size,sha256}}}], effective_verdict（展示值）}`——exact validator 以 coverage_map 候选集 ∪ census 重算有效 verdict：所有候选必须有归宿，任一 confirmed ⇒ DEFECTS_CONFIRMED；有未归宿候选 ⇒ INCONCLUSIVE。

#### 4.2.5 规范化证据表 `gen-<gid>/evidence/<slot>.sqd.json` / `<slot>.ref.json`
- sqd：`{slot, blockhash, parent_slot, transactions:[{index, signature, err}], query_body_sha256, response_sha256}`；
- ref：`{slot, blockhash, parent_slot, block_time, transactions:[{position, signature, is_vote, is_nonce, err}], missing_detail:[{signature, account_keys_full, pre_token_balances(mint), post_token_balances(mint)}], raw_response_sha256}`（原始 7MB 块默认不留，`--keep-raw` 可留；ledger 记 raw sha256，canary 重拉可对表）。
- `evidence_manifest.json`：全部证据文件 `{path,size,sha256}` 清单（进 gid）。

#### 4.2.6 合并缓存 meta `gen-<gid>/soltx-<h>.repaired.meta.json`
与 base v4 meta 同契约（`schema:"sqd-solana-cache/v4"`, `version:4`, `edge_schema/edge_semantics/order_granularity/order_exact=False`, `from_slot/finalized_upper_slot` 同 base），差异：`collector:"sqd_gap_repair.py/v1"`、`collector_sha256`（命中 `scripts/solana/sqd_gap_repair.py`/`sqd-solana-cache/v4` 登记）、`edge_logical_sha256/edge_rows`（生产者建立）、`edge_file_size/edge_file_sha256`（生产者同时写出，消费端不回写）、`plan_digest`、`base_meta_sha256`、`base_edge_sha256`、`repair{slots_confirmed,slots_remapped,edges_added}`（展示值）。**不含 gid、不含 bundle 哈希**（避免 bundle↔meta 环；代归属由 CURRENT→bundle→`merged.meta_sha256` 单向绑定＋`plan_digest` 相等核对）。

#### 4.2.7 `slot_index_map.jsonl`
首行 header：`{"schema":"sqd-solana-slot-index-map/v1","mint":…,"plan_digest":…}`；其后每行一个被重编号 slot：`{"slot","blockhash","map":[[sqd_index,nonvote_ordinal,signature],…],"sqd_count","ref_nonvote_count"}`；`sqd_index`、`signature`、`nonvote_ordinal` 三列各自唯一（双射），单调递增；该 slot 每条 base 边 `(slot,tx_index)` 恰有一解（无解＝SQD 状态已变 → 本次生产中止）。

#### 4.2.8 `solana-reconcile/v4`（`replay_edges.py reconcile`，envelope 化）
在 v3 字段全保留基础上：`schema:"solana-reconcile/v4"`、`target{chain:"solana",token:mint,as_of_block:<快照 slot>}`、`mode:"formal"`、`verdict/exit_code`（与 gate_pass 同值）、`producer`、`inputs{soltx_edges, soltx_meta, holders_owners, holders_snapshot_meta, coverage_map, coverage_slot_counts, [coverage_resolution, repair_bundle, repair_pointer]}`（全部 `{path,size,sha256}` 案根相对；**base 模式省略** 后三键，不置 null）、`edge_source_binding{cache_kind:"base"|"repaired", gid|null, soltx_edges_sha256, soltx_meta_sha256, edge_logical_sha256}`、`coverage_effective_verdict`、`gate_pass`、`negative_balance_count`、`snapshot_mismatch_count`、`net_supply_raw`、`edge_digest/edge_count`。CLI 新增 `--as-of-slot`（runner 以 `{observed_as_of_block}` 注入；须 == holders_snapshot_meta.target.as_of_block == cache finalized_upper_slot）、`--receipt <path>`（runner 要求 receipt 路径在 argv 内且不预先存在；默认仍写 `data/reconcile_receipt.json`）。**不再回写 base meta 的 `edge_file_size/sha256`**（现 :312-314 删除；camp_series :608-609 改读 receipt.inputs.soltx_edges）。

#### 4.2.9 `edge_source_binding` 与承载产物升版
`{cache_kind, gid|null, soltx_edges_sha256, soltx_meta_sha256, edge_logical_sha256}`——承载产物：**`wave-scan/v5`**（由 v4 升，Solana 产物必填、EVM 省略）、**`flow-anomaly/v3`**（由 v2 升，同规则）、`entity_source_trace` 产物（其 input binding 已含 meta/mint，加 gid/边哈希）、`curve_cost` 产物、`audit_closed_accounts` 报告、evolution/sol-rows sidecar。规则：**在场或被引用即强制绑定并验证**——handoff verify / audit_release_gate 对案根内存在的上述任一 Solana 产物（READY 必备与否不论）及 data_map 引用的产物，要求其 binding 与 exact receipt 的 `edge_source_binding` **逐字段全等**（不等＝旧代/旧 base 派生产物携带，拒）；camp 编译同样强制。存量 v4/v2 产物 ⇒ 按版本严格匹配 fail-closed 提示重跑（scan-schemas 既有规则）。

#### 4.2.10 `rpc_ledger.jsonl`（Solana 侧首次逐笔 RPC 台账）
`{"seq","ts","method":"getBlock"|"getBlocks","params_digest","slot"|"range","endpoint_fingerprint","http_status","bytes","credits_estimate","result_sha256","attempt"}`；异常文本经 `redact`（key 永不落盘）；`--resume` 以 `(plan_digest, params_digest, result_sha256)` 判已完成，残缺尾行丢弃不计。

### 4.3 算法与判法

#### 4.3.1 探针（移植 ARC 案已验证代码：`probe_lib.sqd()`＋`scan_nonce_windows.nonce_count`＋`dense_nonce_map.nonce_block_map`＋`finalize_after_dense.presence()`）
查询体：`{"type":"solana","fromBlock":a,"toBlock":b,"includeAllBlocks":true,"fields":{"block":{"number":true},"instruction":{"transactionIndex":true}},"instructions":[{"programId":["11111111111111111111111111111111"],"d4":["0x04000000"]}]}`，游标分页≈450 slot/请求；每请求写台账并填 slot_counts；`--workers`（默认 4）；`--known-map <path>`；`--full`；`--sample <n>`（只作附加证据）；NO_HEADER 确认：参考源 `getBlocks(from,to)`（commitment finalized；每次 ≤500,000 slot；`complete` 机械派生见 4.2.1；不成立 ⇒ 该区间 unconfirmed ⇒ INCONCLUSIVE）→ 在列表中的 NO_HEADER ⇒ MISSING_BLOCK 候选，不在 ⇒ SKIPPED_CONFIRMED；成本实话：全程 1.34 亿 slot 约 270 次调用、返回≈1.3 亿个 slot 号≈数百 MB——**结果存进共享地图复用**，每案只对新区间补做；**禁止游程阈值法**（测试守卫）。
共享全史地图资产：`assets/sqd-solana-coverage-map/<YYYYMMDD>.json`＋同名 `.counts.bin.gz`＋`.blocks.bin.gz`（getBlocks 结果位图）（git 版本化；ARC 全区间扫即第一版），字段＝4.2.1 去 mint 的超集＋`supersedes`＋`ttl_days:30`＋`canary{slots[64],counts}`；每案复用时必做：TTL 未过期、SQD metadata 规范化字段与端点指纹一致、**全部已知 defect/refuted slot 逐 slot 复核**、canary 64 slot 计数一致；任一不符 → 复用结论作废升全扫。过期地图只能当提示。**不向 SQD 报缺陷（用户裁决⑥）。**

#### 4.3.2 修复生产者 α/β（移植 `routeA_full/run_full.py` 的 `helius_block`/`tx_records`/`is_nonce`/`b58decode`/`process`/`ledger`/`redact` 与 `hunt_step2_bisect.py`）
- 参考源：Helius `getBlock` params `{"commitment":"finalized","transactionDetails":"full","encoding":"json","rewards":false,"maxSupportedTransactionVersion":0}`；经 `scripts/lib/net.py`（本工程给 `curl_json` 加 `http_status`＋`no_retry_statuses`，见 4.4.6）；key 只从 `~/.config/helius/api-key` 读（`--reference-rpc` 可指别的端点但**不自动降级公共 RPC**，用户裁决④）；开工前打印预计 slot/请求/credits（信息，不是闸）。
- SQD 普查：同 slot `transactions:[{}]`＋fields `block:{number,hash,parentSlot}` `transaction:{transactionIndex,signatures,err}`，`includeAllBlocks:true`。
- 缺失集＝参考块非投票交易签名 − SQD 签名集；投票判定＝任一顶层指令 programId 为 Vote 程序；nonce 判定＝System 指令 data 小端 u32==4；分类规则见 4.1。
- 产边：只对 `meta.err==null` 的缺失交易，取 `preTokenBalances/postTokenBalances` 中 `mint==本 mint` 的 owner 级 delta → `spl_edge_core.owner_deltas_by_tx` → `pair_tx`（与采集器同一函数，不改），`ts=blockTime`；按签名分组落盘。
- β：对残差 owner 的正式边活动 slot 序列做二分，比较 SQD `tokenBalances` 探针 `postAmount` 与重放余额；断点邻域（±64 slot）跑探针指纹；命中候选入清单回 α。≤3 轮。
- 子命令：`plan`（产候选清单、plan_digest 与预估）/`repair`（产新代，`--resume` 幂等含补发指针）/`verify <gid>`（深验并退出，`--live-canary N` 可选联网抽检）；`--blocks-cache <dir>` 只产 `mode=exploration` 代且不发指针。

#### 4.3.3 同 slot 顺序语义【codex 驳回 offset 后定案】
缺陷 slot 的 base 边与修复边整块统一到参考源"非投票序号"（＝SQD 健康块 index 的同一语义）：用 SQD 普查 (index,signature) 与参考块 (位置,签名,isVote) 按签名建**双射**映射；base 该 slot 每条边 tx_index 必须恰有一解；修复边取其非投票序号；非缺陷 slot 原样。`order_exact` 仍 False（instr_index=-1），但跨交易顺序在缺陷 slot 内恢复真实（`curve_cost` 逐笔储备更新、`entity_source_trace` chain_pos2 顺序模拟不受伪顺序污染）。

#### 4.3.4 合并缓存构造与确定性
merged ＝ [base 非缺陷 slot 行 ∪ base 缺陷 slot 行（tx_index 重映射）∪ 修复边] 按 **`spl_edge_core.edge_sort_key()`**（`(slot, tx_index, from, to, amt_text)`，现役 canonical v4 输出序）排序写出；逐行序列化与采集器一致；`edge_logical_sha256` 按 `_replay_with_evidence` 同算法建立（replay 侧稳定排序不改变同交易多边的文件相对顺序，摘要一致）。代的生命周期见 4.2.3。

### 4.4 代码改动清单（文件级；行号以 main=f06078e 为准）

#### 4.4.1 新件
- `scripts/solana/sqd_coverage_probe.py`（producer：`sqd-solana-coverage/v1`、`sqd-solana-coverage-pointer/v1`；transport 经 net.py；原子写；台账）。
- `scripts/solana/sqd_gap_repair.py`（producer：合并缓存 meta `sqd-solana-cache/v4`、`sqd-solana-repair-bundle/v1`、`sqd-solana-coverage-resolution/v1`、`sqd-solana-repair-pointer/v1`；子命令 `plan|repair|verify`）。
- `scripts/solana/sqd_repair_core.py`（生产者侧纯函数核：规范化/plan_digest/gid、签名差集、vote/nonce 判定、映射构造、合并构造、发布协议）。
- `scripts/lib/solana_exact_validate.py`（**独立 validator，不 import replay_edges/sqd_repair_core**：重放 edge 文件算余额/mint/burn/net/负余额/逐 owner mismatch/digest/count；由 slot_counts 重算四态/候选/时代/有效 verdict 与 UNSCANNED/长度/台账无洞/getBlocks complete；重算 merged==f(base,layer,map) 逐行等价、映射双射、签名 ∉ SQD 集、err 排除、blockhash 一致；重算 gid；校验 `upper==snapshot==target`、代绑定 base 哈希 == 当前 base；formal 拒 exploration 代；校验 `edge_source_binding` 全等；可选 `--live-canary N` 联网抽检证据块 blockhash/签名集）。
- `assets/sqd-solana-coverage-map/`（首版由 ARC 全区间扫产生，见 4.6）。

#### 4.4.2 身份闸、resolver 与正式路径规则（`scripts/solana/sqd_cache_identity.py`、`scripts/solana/spl_edge_core.py:230 soltx_cache_paths`、`scripts/lib/producer_history.py`）
- `validate_cache_meta_v2(meta, mint, *, case_root, meta_path)`（正式路径新入口；旧 `validate_cache_meta` 仅 legacy/探索保留）：collector **闭集映射** `COLLECTORS = {"fetch_sqd_transfers_v2.py/v4": {script, kind:"base"}, "sqd_gap_repair.py/v1": {script, kind:"repaired"}}`；producer 登记按条目 script 查 `historical_producer_hashes(script,"sqd-solana-cache/v4")`；**正式路径规则**：`case_root` 必须显式传入（不猜 cwd）、拒 symlink；`meta_path` 必须 ∈ {`<case_root>/data/soltx-<h>.meta.json`（base）, `<case_root>/data/sqd_repair/<h>/gen-<CURRENT.gid>/soltx-<h>.repaired.meta.json`（repaired）}，CURRENT 按 `case_root＋mint` 查找——复制到别处的 base/meta 一律拒；CURRENT 有效时 base meta 拒；kind=repaired ⇒ 经 CURRENT→bundle 核对 `bundle.merged.meta_sha256 == sha256(meta 文件)`、`meta.plan_digest == bundle.plan_digest`、`meta.base_edge_sha256 == 当前 base` 并浅验 bundle；返回 `(frm, upper, kind, gid, binding)`。
- `validate_repair_bundle(bundle_path, *, deep)`：浅验＝schema/kind/mode formal/producer 登记/CURRENT 一致/base 哈希一致/全部文件哈希绑定/evidence_manifest 完整/行数恒等式/resolution 覆盖候选/gid 标签一致；深验＝委托 `solana_exact_validate` 重算全部绑定关系与 gid。任一不符即拒（**无静默回退 base**）。
- **resolver** `resolve_formal_cache(mint, case_root) -> (edge_path, meta_path, kind, gid, binding)`：读 `CURRENT.json`（kernel 收据校验）→ 代目录 → 浅验 → 返回合并缓存对；指针/bundle/base 哈希任一无效＝硬错；无指针 ⇒ base 对（gid=null）。调用点：`replay_edges.load_edges`（:172-201）与 `cmd_reconcile`（:299-300）、`curve_cost.load_edges`（:52-55）、`camp_series_provenance`（:582-607 改 `edge_path_for_meta` 按闭集 kind 推导并绑定 v4 receipt）、`audit_closed_accounts.py:243` 默认路径走 resolver（显式 `--edges` 强制 non-formal 标记）、`wave_scan.load_sol`（:104-119，flow/entity 复用）新增 `--case-root` 必填、经 `validate_cache_meta_v2`（glob 结果必须恰为 resolver 解析出的唯一文件）并把返回的 `binding` 写进报告 `edge_source_binding`。
- `producer_history.py` 新增 **6 条** ACTIVE（probe：coverage/v1、coverage-pointer/v1；repair：cache/v4、repair-bundle/v1、coverage-resolution/v1、repair-pointer/v1），六字段、`git show <commit>:<script> | shasum -a 256` 可复算——在脚本定稿 commit 之后的收口 commit 里补登，**登记后 producer 不得再改**；fetch 两条与 window_fetch 不动。
- `scripts/hooks/guard_file_ops.py:24-29` RAW_PATTERNS 增加 `/data/sqd_repair/` 与 `/data/sqd_coverage/` 下全部规范件（bundle/repair_layer/slot_index_map/coverage_resolution/rpc_ledger/evidence/repaired 缓存与 meta/CURRENT.json/.lock）——只允许生产者写。

#### 4.4.3 `replay_edges.py reconcile` → `solana-reconcile/v4`
`cmd_reconcile`（:292-375）：resolver 取缓存；读 coverage（CURRENT→probe 目录；缺失/并集不覆盖/producer 未登记/SQD 指纹不一致/UNSCANNED 残留 ⇒ FAIL）；kind=repaired ⇒ 深验 bundle ＋ 组合规则（4.1：代 resolution 重算 DEFECTS_CONFIRMED、逐修复交易/重映射 slot 有 confirmed 支撑、当前 coverage 候选 ⊆ 代 census slot 集）；有效 verdict 重算；INCONCLUSIVE ⇒ FAIL；DEFECTS_CONFIRMED 且 cache_kind=base ⇒ FAIL；`--as-of-slot == snapshot slot == finalized_upper_slot`（:337-343 `>=` 改 `==`）；receipt 按 4.2.8 envelope 化（`receipt_kernel.build_envelope/finalize_envelope`），含 `edge_source_binding`；删除 :312-314 base meta 回写；`--receipt`。`evolution`（:538-542）绑定 receipt 不变并写 sidecar binding。

#### 4.4.4 受控对账第五项 `exact_reconcile`、wrapper v3 与 READY 硬闸【codex 方案】
- `scripts/report/shared_release_receipt.py:53-65` `RECON_PRODUCERS["solana"]` 加 `"exact_reconcile": {"scripts/solana/replay_edges.py"}`；新增 `RECON_CHECK_KEYS = {"evm": ("balance","supply","supply_truth","time"), "solana": (…,"exact_reconcile")}`；`:1358-1387` wrapper 校验：schema **一律 `reconciliation-report/v3`**（EVM 四项/Solana 五项；v2 全部 fail-closed，提示 EVM 用 `--reseal`、Solana 重跑 v4 exact＋五项）；`validate_reconciliation_check`（:1164）新增 `family=="solana" and key=="exact_reconcile"` 分支：schema `solana-reconcile/v4`、mode formal、`gate_pass is True`、两计数精确 0、`cache_kind` 与有效 verdict 组合合法（4.1）、inputs 全在案根且哈希可核、`inputs.holders_owners` 与 supply 观测 bundle 的 `holder_outputs.owners` 同一文件、**调用 `solana_exact_validate` 深验**。
- `scripts/report/reconciliation_report.py:19 CHECK_KEYS` → 按家族；`:161/165/210` 按家族取键；wrapper 产 v3；dynamic_solana 顺序 `(supply, balance, supply_truth, time, exact_reconcile)` 且 `:189-195` 占位符要求加入 exact_reconcile；`:248-253` Solana token 比较去 `.lower()` 改用 `canonical_target()` 分家族规则；新增 `--reseal <旧 wrapper>`（仅 EVM；重新深验四份 receipt 实物、从实物重建 target/checks、不信旧 wrapper 状态、以当前 runner 原子重封 v3；任一 receipt 验不过 ⇒ 拒并提示重跑）。
- `scripts/report/audit_release_gate.py:467 check_reconciliation` 改为直接复用 `shared_release_receipt.validate_reconciliation_report()`（深验）＋ 在场/被引用 Solana 派生产物 `edge_source_binding` 全等检查。
- `scripts/lib/camp_series_provenance.py:404-405` `RECONCILE_SCHEMA="solana-reconcile/v4"`，v3 归 LEGACY；`:507-580` 校验加 `cache_kind/gid/coverage_effective_verdict/inputs.soltx_edges/coverage/bundle`，调用 `solana_exact_validate` 深验，sidecar `edge_source_binding` 与 receipt 全等；`:608-609` 改读 receipt inputs。
- `handoff_manifest.py`：`AUTO_GATES` 键 `reconciliation_four_checks` → **`reconciliation_checks`**（旧键只作读入别名）；`CONTRACT_FILES` 不加动态名，改为 **"exact_reconcile receipt 引用的全部文件必须同时进入 data_map 与 manifest artifacts，verify 检查"**（:210-222）；`WAVE_SCHEMA`→`wave-scan/v5`、flow 检查→`flow-anomaly/v3`（:395-440）；verify 对 Solana 调用 `validate_reconciliation_report()`（深验）＋ **在场/被引用的 wave/flow/entity/curve/audit_closed 产物 `edge_source_binding` 与 exact receipt 全等**。
- 次选（若第五项方案施工受阻）：handoff 内 Solana 专用深验 gate。

#### 4.4.5 明确不动
`fetch_sqd_transfers_v2.py`（一行不改、哈希不变、两条登记不变）、`spl_edge_core.py` 的 7 元组/语义常量/`edge_sort_key`（只加 resolver 辅助函数）、`window_fetch.py`、EVM 侧产物语义（wave/flow 升版对 EVM 只是版本号，字段不增）、既有 base v4 缓存（不可变、不重采、不回写）、`anchor_sampler.py`。

#### 4.4.6 运行安全（用户裁决④ 的安全落法）
`scripts/lib/net.py:51-62/110-125` `curl_json` 的 error 负载增加 `http_status`（curl `-w '%{http_code}'` 解析）与 `retryable:bool`，新增参数 `no_retry_statuses=()`；修复生产者对 402/429 及 Helius 配额错误体首次确定性命中即停止派发（在途请求完成后落账）、写 `pending-<plan_digest>/STOPPED.json{reason,cursor}`、退出码 3；`--resume` 按 4.2.10 幂等；所有异常/stderr/ledger 先过 `endpoint_identity.redact_endpoint_text`；方法论止损（β≤3/残差不降即停/禁 BFS）保留。

### 4.5 文档 / 判例 / 契约 / 测试 / 版本

#### 4.5.1 文档（措辞要点）
- `references/data-pipeline-solana-capture.md`：新增 `### 13e. SQD 数据集已知缺陷与覆盖健康闸`（缺陷事实＋四态指纹判法＋getBlocks 跳块确认及其前提与成本＋探针/修复生产者/代/bundle/指针/发布协议＋"修过账不退回 base、重采即作废"＋共享地图生命周期（TTL/已知 slot 复核/canary）＋"无预算上限、Helius 唯一参考源、配额耗尽停工换 key"＋与 A2 的关系＋派生产物绑定＋止损纪律）；**更正** `:94` 覆盖谓词、`:98` 定位句（探针＋exact_reconcile 是硬 gate）、`:117-126` provenance 段补代/bundle 信任前提（仍非密码学签名，F2-03 边界不变）、`:128-134` 补"无块头的最终确认靠参考源 getBlocks"、`:143` 收尾合并契约补"修复代合并同用 edge_sort_key"、`:156-157`（删"签名可按该位置反查"；tx_index 是 SQD 内部去投票重编号；缺陷 slot 修复后统一为参考源非投票序号；跨源身份只用签名）、`:218` 拼接句指向修复生产者正规化。
- `references/data-pipeline-solana.md` 路由表加两行；`references/split-run.md` §1.3 A2 行（"四查"→"EVM 四查 / Solana 五查＝四查＋精确重放 exact_reconcile，wrapper v3；A2 FAIL 处置＝先探针归因→α/β，禁止逐账户 BFS 补账"）＋A3 第 7/8 步 schema 升 v5/v3 与 binding 句＋§2.2 gate 记录句（:105，AUTO_GATES 键名）＋状态机句（:107）＋产物表（:85/:87）；`references/analyze-workflow.md` A2 主序与 wave/flow 版本；`references/scan-schemas.md` 登记 4.2 全部 schema＋wave v5/flow v3 差异段；`scripts/solana/README.md`；`references/environment.md` 一句；`references/maintenance-review-repair.md` 加"开放式诊断/补证工单四件套（止损判据/外部额度台账/汇报节点/目标对齐）"；`commands-staging/token-analyze-1.md`＋已部署 `~/.claude/commands/token-analyze-1.md` 同步一句；SKILL.md **零字节新增**（现 7961/8192B）。
- `references/casebook/supply-accounting.md` 新增 **S-12「SQD Solana 缺陷区段与跨源编号错位」【机制成立】**（S-08 已被 methods 续册占用）：触发＝Solana 重放残差总和 0、负余额成对、残差 owner 少但金额精确、对手方集中在交易所/做市；禁止推断＝采集器 bug / owner 变更漏记 / 用逐账户补账追清零 / 拿 Helius·RPC 位置当 SQD index 比对并判"缺失"；必做区分＝探针指纹（有块头零 AdvanceNonce）＋按签名核对＋余额连续性二分；证据上限＝无探针结论只能写"残差未归因"；指针＝capture.md 13e；案源＝ARC 2026-08-20/23（含 codex 2026-08-23 诊断报告"硬下界 13,425 笔/Meteora-Raydium 特征/218-739 分类"系编号错位假象的勘误口径，用户裁决⑧）。`casebook_lint` 单册上限 25 条内（现 10 条）。
- `CHANGELOG.md` 6.52.0 索引行＋详情（含勘误口径一句）；`VERSION`/`pyproject.toml`/SKILL.md 注释四文件五处同步；`changelog_lint` 先跑。

#### 4.5.2 契约与测试登记
- `scripts/tests/invariant_manifest.json`：receipt_producers（probe 2 协议、repair 4 协议、replay_edges 加 `solana-reconcile/v4`、wave/flow 升版 schema）；receipt_consumers（resolver/validate_repair_bundle/solana_exact_validate 调用点）；transport_calls ＋2；atomic_writes ＋2；**formal_entrypoints ＋3**（probe、repair、`scripts/solana/replay_edges.py`）；`minimum_counts` 相应上调；`invariant_scan.py:81 FORMAL_E2E_REQUIRED_PRODUCERS["sol"]` 加 probe 与 replay_edges（repair 走缺陷纵切片）；`:99 FAILURE_ARTIFACT` 覆盖加 replay_edges 与 repair。
- `contract_manifest.json`＋`contract_ids_snapshot.json`：新 required needles——`sqd-solana-coverage/v1`、`sqd-solana-coverage-resolution/v1`、`sqd-solana-repair-bundle/v1`、`sqd-solana-repair-pointer/v1`、`solana-reconcile/v4`、`reconciliation-report/v3`、`wave-scan/v5`、`flow-anomaly/v3`、`exact_reconcile`、`sqd_gap_repair.py/v1`、`edge_source_binding`、`有块头但零 AdvanceNonce`、`reference-nonvote-ordinal/v1`、`CURRENT.json`；banned——`签名需要时可按该位置反查`、`signature→(slot,tx_index) 映射经 getBlock`、`reconciliation_four_checks`（仅别名处豁免）、`wave-scan/v4`/`flow-anomaly/v2`（仅版本差异说明与 CHANGELOG/archive 豁免）；snapshot 集合相等验收。
- wave/flow 升版影响面（本次 grep）：`scripts/lib/wave_contract.py`、`scripts/report/{wave_scan,flow_anomaly_scan,handoff_manifest,audit_release_gate,adjudication_validator}.py`、`scripts/tests/{test_wave_scan,test_flow_anomaly,test_handoff_manifest,test_audit_release_gate,test_adjudication_validator,test_evm_observation_release,test_repair_batch_d}.py`、`contract_manifest.json`、`invariant_manifest.json`、`references/{split-run,analyze-workflow,scan-schemas}.md`。
- `runtime_docs_manifest.json`：不新增 references 文档则不动；若新建运行时参考件必须登记。
- 新测试（四件，SUITE 冻结 124→**128**）：`test_sqd_coverage_probe.py`、`test_sqd_gap_repair.py`、`test_reconcile_v4_receipt.py`、`test_recon_fifth_check.py`；先红清单 31 项见 §5。
- 需回归/更新的现有测试与 fixture：`sqd_v4_test_fixture.py`、`test_sqd_consumer_v4.py`、`test_batch6_sqd_v4_blind_review.py`、`test_review_resume_integrity.py`、`test_repair_batch_a/c/d.py`、`test_sqd_merge_equiv.py`、`test_wave_scan.py`、`test_flow_anomaly.py`、`test_entity_source_trace.py`、`test_handoff_manifest.py`、`test_reconciliation_runner.py`、`test_batch2_ready_reconciliation.py`、`test_batch3_solana_producers.py`、`test_batch3_solana_vertical_slice.py`、`test_r9_batch3_dynamic_runner.py`、`test_audit_release_gate.py`、`test_adjudication_validator.py`、`test_evm_observation_release.py`、`test_formal_chain_support.py`、`test_exemption_guards.py`、`test_net_result.py`、`test_anchor_plan_v3.py`（producer_history git 复算）、`invariant_scan.py`、Solana 纵切片。
- **性能验收项**：ARC（26.6M 行）上实测 `solana_exact_validate` 单次峰值内存与 5 个必经入口累计耗时并记入 done 报告；若单次 >5 分钟，批 5 评估"深验结果 attestation 缓存"（只改性能不改判据，另立裁决）。

### 4.6 ARC 案收尾路径（skill v6.52.0 合并后；用户裁决③⑤⑥）
1. `sqd_coverage_probe.py --full` 扫 ARC 全区间（306,451,717→440,368,381 ≈1.34 亿 slot ≈30 万次免费 SQD 请求，4 线程≈1 天后台；NO_HEADER 用 Helius getBlocks 确认≈270 次、数百 MB）——**同时就是共享全史缺陷地图第一版**；预期命中 38＋2 处及可能新发现；时代校准数据第一次拿到。
2. `sqd_gap_repair.py repair` **正式代走 Helius live**（≈6.8k 块≈68k credits，约 1 小时；无预算闸）；`--blocks-cache diagnosis_20260823/routeA_*/blocks/` 只产 exploration 代作离线回归（证明 83 条边可复算、确定性）；live 代对已知缺陷块＋两笔 hunt 块＋健康块 canary 对照。
3. `replay_edges.py reconcile`（v4）→ `gate_pass=true` → 受控对账 runner（v3 wrapper 含第五项）PASS → A3（wave v5/flow v3/distribution 等重跑以带 binding）→ `handoff generate --mode full` → `verify` READY → −2。
4. 销账：`sqd-v4-rootcure-project` 后置条件（A2 0/0）；ARC `anomalies.json` 阻断项引用 gid 关闭。

### 4.7 关键取舍（r7）
| 取舍 | 选择 | 不选的替代与理由 |
|---|---|---|
| 采集器带签名（升 v5） | **本轮不升**（用户裁决②） | 7 元组全链契约变更＋存量 v4 作废重采 |
| 修复产物架构 | **不可变 base＋独立修复层＋可重建合并缓存＋bundle＋代内容寻址＋pending→gen 原子改名＋锁内 CAS 指针＋resolver 单入口**【codex】 | 固定文件名/无 CAS＝覆盖旧代、并发错切、崩溃半代 |
| 回到 base | **不存在正式路径**；SQD 回填不影响已发布代；base 重采 ⇒ 代全作废【codex r5】 | r5"撤销代退回 base"会把补回的边再丢一遍 |
| gid | **由不含 gid 的规范化内容计算**，编码/排序/类型写死，含 kind/supersedes/mode/参考源/证据清单 | r4 自引用；r5 规范化未冻结 |
| 同 slot 顺序 | **缺陷 slot 整块统一参考源非投票序号＋双射映射表**【codex】 | offset 破坏 curve/entity 跨交易顺序 |
| 合并排序键 | **复用 `edge_sort_key()`**【codex】 | 自定义键同交易多边并列→摘要漂移 |
| 探针策略 | **务实模式**（用户裁决③）＋TTL/已知 slot 复核/canary；slot_counts 含 UNSCANNED；getBlocks complete 机械派生 | 严格模式每老币多 1 天 |
| 参考源与预算 | **Helius 唯一参考源、无预算上限、无公共备胎**（用户裁决④）；结构化配额错误停工 | 预算闸/备胎被用户否决；方法论止损保留 |
| 闸挂哪里 | **exact_reconcile 进受控对账第五项；wrapper 一律 v3（EVM 四/Solana 五）＋`--reseal` 迁移**【codex】 | v2 legacy 需历史 runner 信任链 |
| 深验/浅验 | reconcile/shared_release/handoff verify/audit_release/camp 深验（独立模块）；其余浅验但必经 resolver＋正式路径集合规则＋`--case-root`＋**派生产物 edge_source_binding 全等（在场即验）** | 只深验不交叉绑定＝旧 base 派生产物可携带进 READY【codex】 |
| 承载 binding 的产物版本 | **wave-scan/v5、flow-anomaly/v3**（升版） | 同版本加必填字段＝破坏性契约变更【codex r5；scan-schemas 既有规则】 |
| verdict 命名 | `NO_KNOWN_NONCE_OMISSION_DETECTED / DEFECTS_CONFIRMED / INCONCLUSIVE`；探针不可变、确认单列 resolution【codex】 | "CLEAN"夸大；probe 被 repair 改写＝provenance 撕裂 |
| 判例编号 | **S-12** | S-08 已被 methods 续册占用 |
| 共享地图 | 做（skill 资产）；**不报 SQD**（用户裁决⑥） | — |
| Helius key | **不轮换**（用户裁决⑦） | — |

---

## 5. 施工与验收（调度隔离模式）
- **分工**：codex 施工（companion 工单制 `task --write --fresh`，白名单文件、带行号、先红后绿、不 commit）；Fable 验收＋代 commit；opus 盲审（攻击型）；联网步骤（SQD/Helius 实测、canary、ARC 全扫）Fable 本机代跑；工单四件套（止损判据/外部额度台账/汇报节点/目标对齐）。
- **批 0 ＝ 本文件 r7.1**（六轮 codex 复核见 §6 ＋ 用户批准；PLAN.md 落盘后 codex 只读终审一次作为批 1 准入闸）。批 0 冻结的 15 项决策：①探针产物不可变、确认单列 resolution（4.2.1/4.2.4）；②双源规范化证据表与 evidence_manifest＋getBlocks 位图实物（4.2.1/4.2.5）；③规范化/plan_digest/gid 定义＋无环绑定依赖图（4.2.0）；④发布协议（pending 内含 bundle→fsync 代目录→改名→fsync 父目录→锁内 CAS 指针→fsync 指针父目录）与崩溃恢复（4.2.3）；⑤代的生命周期：不退回 base、SQD 回填不影响已发布代、base 重采作废（4.2.3）；⑥修复层按签名分组、唯一键 signature（4.2.2）；⑦canonical 排序＝`edge_sort_key`（4.3.4）；⑧wrapper v3 一律＋`--reseal`＋exact receipt 完整 inputs（4.2.8/4.4.4）；⑨formal 禁 local-evidence-cache（4.2.3）；⑩正式路径集合规则＋`--case-root`＋resolver（4.4.2）；⑪`edge_source_binding` 交叉绑定＋wave v5/flow v3＋在场即验（4.2.9/4.4.4）；⑫地图 TTL/已知 slot 复核/canary/时代参数/UNSCANNED/getBlocks 机械 complete（4.2.1/4.3.1）；⑬结构化配额停工＋plan_digest 绑定 resume（4.4.6）；⑭深验由独立模块实现、性能实测、不预设 attestation（4.4.1/4.5.2）；⑮producer 六协议逐条登记＋两段 commit（4.4.2/§5）。开工后首动作：在 skill 仓库建 `maintenance/repair-20260823-sqd-gap/PLAN.md`（本文件 §4–§5 落盘）＋ 契约草案 JSON ＋ ARC base/83 边/快照/证据完整哈希 manifest。
- **先红清单（31 项，批 1 先全部红）**：(1) `gate_pass=false` 仍可 generate READY；(2) 同 slot 错序修复边改变 curve/entity 结果；(3) `sample` 段冒充全覆盖；(4) coverage 文件被 repair 改写；(5) 同签名多边被去重丢边；(6) 第二代覆盖旧代文件；(7) bundle 未写完/指针未发的 gen 被 resolver 当有效代；(8) local-evidence-cache 代进 formal；(9) 显式 base 路径绕 resolver（wave/flow/entity/curve/camp/audit_closed 六入口各一）；(10) refuted-only 产代；(11) `repair_bundle:null` 过 envelope；(12) cache upper 与快照 slot 不等仍 PASS；(13) base meta 被 reconcile 回写；(14) audit_release 只看 status 放行坏 receipt；(15) base 重采后旧代仍被消费；(16) gid 含自引用/exploration 与 formal 同目录/同内容不同 supersedes 同 gid；(17) 复制 base 到别目录显式传入绕过；(18) CAS：supersedes≠当前 CURRENT 仍能切指针；(19) 旧 base 派生 wave/flow 产物携带进 READY（binding 不等）；(20) slot_counts 含 UNSCANNED/长度不符/台账有洞仍 PASS；(21) getBlocks `complete` 自报 true 但数组不递增/越界/超 500k 仍被信；(22) wave v4/flow v2 旧产物被 v5/v3 验收接受；(23) 无 `--case-root` 或 symlink 案根被正式路径接受；(24) curve/audit_closed 在场但 binding 不等仍 READY；(25) merged meta 含 bundle 哈希/gid（环）或 bundle.merged.meta_sha256 不等仍被认；(26) 代目录/指针父目录未 fsync 即认发布完成（注入模拟崩溃）；(27) 规范化把金额写成字符串仍得同一 gid；(28) getBlocks 位图长度/popcount/范围不符仍判 complete；(29a) repaired 代绑定的 resolution 重算非 DEFECTS_CONFIRMED 仍 PASS；(29b) 某条修复交易或某个重映射 slot 在 census 中无 confirmed 行支撑仍 PASS；(29c) 当前 coverage 出现未被当前代 census 覆盖的新候选仍 PASS。
- **六批**：1 契约冻结与登记面（invariant/contract/scan-schemas/producer_history 骨架、先红 31 项）→ 2 coverage 探针＋地图生命周期＋getBlocks 确认＋Fable 本机起 ARC 全区间扫（后台 1 天，与后续批并行）→ 3 代/修复层/resolution/bundle/发布协议/CAS/resolver/浅深 validator＋`--blocks-cache` 离线回归 83 边 → 4 消费端与顺序语义（replay/curve/camp/wave v5/flow v3/entity/audit_closed 回归、binding 写入、`--case-root`、映射表、net.py 结构化状态）→ 5 exact_reconcile 第五项＋receipt v4＋wrapper v3＋`--reseal`＋runner/validator/audit_release/camp/handoff 同步＋深验性能实测 → 6 文档/判例 S-12/契约 needle/版本五处/CHANGELOG＋本机 E2E（ARC probe→Helius live repair→reconcile→五查→A3 重跑→READY）。
- **commit 策略（两段）**：每批验收后一 commit（脚本先定稿）；收口 commit 再补登 producer_history 六条哈希、契约快照、版本五处、CHANGELOG（首行＝CHANGELOG 标题）；登记后 producer 不得再改；合并 main 后 push。
- **验收四范式**：①原始复现独立重放（ARC 83 边/26 owner 归零，Fable `indep_after_check` 复算）②边界外一步攻击（opus：伪造 coverage verdict、stale map、区间缺口、冒用 base 哈希、修复 slot 越界、签名重新出现在 SQD、local cache 少块/篡改、不同 mint/cutoff、手改 manifest 绕 READY、key 脱敏、bundle 验不过是否回退、指针指向孤儿代、复制 base 绕过、旧派生产物携带、并发双代抢切、伪造证据块经 `--live-canary` 抽检）③破坏性注入自证到达目标分支 ④grep 清零（旧前提句 0 命中）。四类反例【codex】：无缺陷路径（NO_KNOWN…＋base 直过）、SQD 回填后旧代仍有效＋新代 supersedes、崩溃原子性/重复修复幂等、同 slot 顺序敏感等价性。
- **施工中按清单完成（非批 0 阻塞）【codex r5】**：深验性能实测、128 项回归、ARC live E2E、六条 producer hash 最终登记。
- **收工**：版本五处 6.52.0、`changelog_lint` 先跑、SUITE 128/128、push；档案落 `maintenance/repair-20260823-sqd-gap/`；ARC 收尾按 §4.6。

---

## 6. codex 第二意见与融合记录

### 6.1 r1 → r2（2026-08-23 04:35）
codex："方向正确；批准立项，驳回 r1 实现设计，先补批 0"。采纳：READY 链机器缺口措辞、skill 两处设计缺陷措辞、期末清零≠历史完整、不可变 base＋修复层＋合并缓存＋bundle、驳回 offset→整块非投票序号、闭集映射＋离线重算、第五项＋receipt v4、不只 FAIL 触发/地图生命周期/不叫 CLEAN、重灌检测、routeA 只作离线回归、同族面清单、批 0＋六批＋四类反例。

### 6.2 r3 复核（07:33–07:43，"不可开工"）→ r4 消化
16 处代码引用全部属实；A1–A8/B/C/D/E/F/G/H/I 全部采纳（探针可重算阵列、resolution 分离、按签名分组、双源证据绑定、formal 拒 local cache、receipt 直绑边文件与不回写 base meta、独立深验模块、`upper==snapshot==target`、SKIPPED 独立确认、分类统一、时代参数冻结、地图 TTL/复核/canary、`edge_sort_key`、双射、代内容寻址、崩溃协议、refuted-only 留 base、深验面与绕过面、wrapper v3、AUTO_GATES 键、runner `.lower()`、net.py 结构化状态、resume 绑定、脱敏、同族面十项、S-12、批 0 十二项、两段 commit、先红 15 项）。

### 6.3 r4 复核（07:54–08:03，"不可开工"）→ r5 消化
引用核实属实。采纳：gid 去自引用；指针用 PASS 收据＋`publish_overwrite`；plan_digest＋pending 目录；（撤销代——r6 撤回）；UNSCANNED 态；getBlocks 前提/成本；正式路径集合规则；`edge_source_binding` 交叉绑定；一律 v3＋`--reseal`；多协议登记；性能验收项；先红 20 项。

### 6.4 r5 复核（2026-08-23 08:08–08:17，"不可开工"，4 项设计阻塞）→ r6 消化
Fable 核实引用（`receipt_kernel.py:590-600` 单文件原子、`scan-schemas.md:32-39` 新字段＝版本差异、`wave_scan.py:104-119` glob 接受、`shared_release_receipt.py:102-115` 只认当前脚本哈希、`handoff_manifest.py:65-88` READY 必备清单）——全部属实。逐项裁定：

| 项 | codex 意见（摘要） | Fable 裁定 | r6 落地 |
|---|---|---|---|
| 阻塞 1 | 撤销代退回旧 base 语义错误（旧 base 缺的边不会因 SQD 回填出现） | **采纳（我的错误）**：删除撤销代；已发布代不受回填影响；base 重采 ⇒ 代作废；无"退回 base"正式路径 | 4.2.3/4.3.4/4.1 |
| 阻塞 2 | 先改名后写 bundle 留崩溃窗口；`publish_overwrite` 无多文件/CAS 保证 | **采纳**：pending 内最后写 bundle→改名→fsync→锁内 CAS | 4.2.3 |
| 阻塞 3 | gid 规范化未冻结；未纳入 kind/supersedes | **采纳** | 4.2.0 |
| 阻塞 4 | 同版本加必填字段＝破坏性变更，应升 wave v5/flow v3 | **采纳** | 4.2.9/4.4.4/4.5.2 |
| 补 1 | getBlocks `complete` 须机械派生 | **采纳** | 4.2.1 |
| 补 2 | resume 在 rename 后崩溃的恢复未定义 | **采纳**（幂等补发指针） | 4.2.3 |
| 补 3 | 多协议登记数不一致（五/六） | **采纳**：统一 6 条 | 4.4.2/§5 |
| 补 4 | `--case-root` 显式、拒 symlink、不猜 cwd | **采纳** | 4.4.2 |
| 补 5 | `--reseal` 条件（仅 EVM、重新深验实物、不信旧 wrapper、原子输出） | **采纳** | 4.4.4 |
| 补 6 | curve/audit_closed 非 READY 必备："在场或被引用即强制绑定并验证" | **采纳** | 4.2.9/4.4.4 |
| 补 7 | 深验性能/128/ARC E2E/哈希登记＝施工中完成 | **采纳** | §5 |

### 6.5 r6 复核（2026-08-23 08:22–08:31，"不可开工"，4 项窄阻塞）→ r7 消化
Fable 核实引用（`spl_edge_core.py:19-35` 金额必须正整数；`receipt_kernel.py:327/590` 只 fsync 文件内容；`wave_contract.py:1` 严格契约 v4）——全部属实。逐项裁定：

| 项 | codex 意见（摘要） | Fable 裁定 | r7 落地 |
|---|---|---|---|
| 阻塞②残 | bundle 绑 meta 哈希、meta 又含 bundle 哈希＝环；resolution/meta 在 gid 算出前就要写 gid | **采纳（设计错误）**：meta/resolution/layer/map 只含 plan_digest，gid 只在 bundle 与指针；绑定单向 | 4.2.0 依赖图、4.2.3、4.2.6、4.4.2 |
| 阻塞②残 | `publish_overwrite`/`_stage` 不 fsync 目录 | **采纳**：改名前 fsync 代目录、切指针后锁内 fsync 父目录 | 4.2.3 |
| 阻塞③残 | "金额用十进制字符串"与 v4 正整数契约冲突 | **采纳**：一律 JSON int | 4.2.0 |
| 补丁①残 | getBlocks 只存哈希/计数，实物未绑定 | **采纳**：位图实物落盘＋离线可验项＋诚实边界 | 4.2.1 |
| 生命周期 | 定案正确；但 repaired"任何非 INCONCLUSIVE"可被利用 | **采纳**：代 resolution 重算 DEFECTS_CONFIRMED＋逐项 confirmed 支撑＋新候选须被当前代覆盖 | 4.1、4.4.3 |
| 其余 | 阻塞①④、补丁③–⑦已闭合 | — | — |

### 6.6 r7 复核（2026-08-23 08:30–08:39）→ r7.1 文字一致性修订
codex 判"不可开工"但阻塞已收窄为**两项契约文字冲突＋一项先红反例拆分**，无新设计问题：①§4.2.0 说 resolution 不含 gid 而 §4.2.4 仍列 `gid（标签）`；bundle 字段表与 layer header 漏写 `plan_digest`；须统一"哪些前置文件必须含 plan_digest"；②先红第 29 项须拆成三组独立反例（重算非 DEFECTS_CONFIRMED／修复交易或重映射 slot 缺 confirmed 支撑／新候选未覆盖）。已确认的闭合：金额 JSON int（`spl_edge_core.py:19`）、getBlocks 位图实物与诚实边界、目录 fsync 补法"必要且充分"（`receipt_kernel.py:327/590`）、依赖图本身无环、九步协议语义完整（第九步编号补上）。**r7.1 逐字落实**：4.2.4 去 gid 加 plan_digest；4.2.2/4.2.3/4.2.7 补 plan_digest；4.2.0 新增"必须含/不含 plan_digest 文件清单"；§5 第 29 项拆 29a/b/c（先红 31 项）；步骤⑨编号。codex 明示其余（producer/validator/先红后绿/live canary/E2E）属施工清单。

**收口说明**：六轮 codex 复核（r1/r3/r4/r5/r6/r7）每轮阻塞项单调收窄（4 硬伤→P0/P1/P2 清单→5→4→4→2 文字项），最后一轮无设计级阻塞；Fable 判断 r7.1 可作批 0 冻结件交用户审批。为保留 codex 的最终签字权，批 0 第一动作（PLAN.md 落盘）之后、批 1 编码之前，再由 codex 只读终审一次作为准入闸（若其再提设计级异议，先报用户再开工）。

---

## 7. 用户裁决记录（2026-08-23，8 条已定）
1. **立项**：改 skill；Fable 写详细计划（本文件）→ codex 复核 → 用户审批。
2. **采集器签名**：选 A——本轮不升 v5。
3. **探针策略**：选 A——务实模式（共享地图＋增量全扫＋已知段复核＋抽样＋β）。
4. **参考源预算**：**不设上限、不用公共 RPC 备胎**；额度用完用户再注册新 key。（设计落点：只记台账、结构化配额错误干净停工；方法论止损 β≤3 轮/残差不降即停/禁 BFS 保留——防发散不是省钱，用户如不要可再裁。）
5. **ARC 正式修复参考源**：选 A——Helius live（≈68k credits）。
6. **共享全史缺陷地图**：做（ARC 全区间扫即第一版）；**不向 SQD 报告缺陷**。
7. **Helius key**：不轮换（用户判无资金风险、接受）。
8. **判例与 CHANGELOG**：写入（codex 报告数字勘误口径入 S-12 与 6.52.0 条目）。

---

## 8. 给用户的大白话摘要（审批时看这一节就够）
- **要做什么**：给 skill 加两件工具——"坏块探测仪"（免费，列出 SQD 哪些区块缺数据，整张逐块计数表可被别人重算核对）和"补账机"（只对坏块从 Helius 拉原始区块、按每笔交易的签名补回 SQD 确实没有的流水；原账本不动、补丁按"代"单独存、合并账本可随时重算、指针最后才切且切前核对"接的是不是当前那一代"；修过账的案子不会再退回原始账本，除非整个重采）；再把"精确对账必须全平"接进正式放行闸（以前这道闸在机器层有漏洞），所有读账本的入口统一走"解析器"，所有分析产物都要注明用的是哪一代账本并与对账收据对得上；改掉文档里的错误说法，写一条判例防止以后再犯"拿位置当编号"的错。
- **不做什么**：不改采集器、不重采 ARC、不碰 EVM 侧的数据语义、不设 Helius 花费上限、不设免费备胎、不换 key、不向 SQD 报告。
- **codex 六轮复核**：第一轮 4 处硬伤→改；第二轮判"不可开工"列 P0/P1/P2→全部消化；第三轮 5 项（含我的"代编号自引用"真错误）→全部消化；第四轮 4 项（含我的"撤销代退回原账本"真错误）→全部消化；第五轮 4 项窄阻塞（含我的"bundle 与 meta 互含哈希成环"错误）→全部消化；第六轮只剩 2 处文字前后不一致＋1 条测试拆分，已按它原话改完（本稿 r7.1），设计层面没有未闭合项。开工后第一步（计划落进 skill 仓库）再让 codex 只读终审一次，它若再提设计级异议我会先报你。
- **风险与边界**：①Helius 免费档每月 100 万 credits，ARC 修复约 6.8 万；没有预算闸意味着坏块特别多的币可能一次烧掉大半月额度——工具会记台账、额度耗尽时干净停下等你换 key；②探针只能发现"nonce 交易缺失/整块缺失"这两类已知缺陷，别的缺陷类型不保证；③修复产物的防伪仍是"公开哈希绑定"不是密码学签名（与现有体系同级，可选联网抽检加固）；④对账 wrapper 升 v3、波次/资金流报告升版后，以前的 Solana 案若要重新发布要按新流程重跑，EVM 旧案可用"只重封不重跑"的迁移命令（波次/资金流报告 EVM 侧也要重跑一次才能重新发布——只是版本号，数据语义不变）。
- **工期与顺序**：批 0（本文件）→ 你批准 → 六批施工（估 4–6 天，codex 施工/Fable 验收/opus 盲审）→ 同时后台跑 ARC 全区间探针（≈1 天，免费）→ 合并 v6.52.0 → ARC 用新流程补账→过闸→READY→进 −2。
- **你后续还要做的**：审批本计划；六批结束后看一次验收报告；ARC 过闸后决定是否进 −2。
