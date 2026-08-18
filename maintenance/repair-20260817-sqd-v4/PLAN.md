# Solana 采集器"DISTINCT 吃边"根治工程（v6.49.0）总纲

> 本件是本工程唯一权威计划（用户 2026-08-17 批准，@CX codex 复核意见已融合）。
> 施工方为 codex（分批工单，见同目录 batchN_workorder.md）；验收方为 Fable（调度不施工）；
> 攻击型盲审由 opus 子代理执行。工作目录＝skill 库本仓库；**禁止触碰任何案目录**
> （尤其 /Users/uravvv/Documents/5.6筹码分析/ARC分析/ ——另一施工进程的现场）。

## 背景（缺陷定案）

`scripts/solana/fetch_sqd_transfers_v2.py` 落盘 5 元组边 `[ts, slot, from, to, amount_raw]`
无交易身份；合并阶段（`:771`）`SELECT DISTINCT` 按五字段去重，把同 slot 等额的多笔真实交易
（pump.fun 高频常态）误当重复删除。ARC 案实证：被吃 124,816 条边 → 重放 820 负余额 / 1,152
快照错配 → A2 对账闸 fail-closed 拦停全案。三个实锤：

1. `references/scan-schemas.md:17` 早有"同五元组合法重复真实存在，fail-closed 去重会误杀"
   明文规矩——采集器违反自家文档。
2. `transactionIndex` 已在请求、已在用（`:282,:293` by_tx 分组键），落盘时被丢（`:293-296`
   循环变量 `ti` 未进元组）。加身份零额外请求。
3. 库内已定稿官方 7 元组标准 `[ts, slot, tx_index, instr_index, from, to, amt]`
   （`scan-schemas.md:206`；`wave_scan.py:107-118` 现役读入口）。

## @CX 复核拦下的三个设计错误（方案已修入，施工时不得回退）

1. **pair_tx 并非确定性**：`:151` 排序键只有 `-amount`，等额时继承 SQD 返回序（dict 插入序）——
   同一交易两次采集可配出不同边。等额多方反例：A、B 各 −10；C、D 各 +10，不同返回序可配出
   A→C/B→D 或 A→D/B→C。
2. **instr_index=-1 不能对应 order_exact=True**：wave_scan 对 7 元组无条件 `order_exact=True`
   （语义＝可唯一恢复链上执行顺序），而交易级净额边在交易内无序；`entity_source_trace.simulate`
   （`:419`）会对同桶边按任意 ingest 序过账制造伪因果。修法＝instr=-1 ⇒ `order_exact=False`。
3. **owner 净额边只是推定配对**：`A:-100, B:+70, C:+30` 证明余额变化，证明不了 A 分别流向谁。
   schema 必须声明 `edge_semantics="owner-net-greedy"`，不得冒充精确转账边。

## 方案定型（全批共同遵守）

- **语义**：边＝transaction-net 推定边；7 元组 `[ts, slot, tx_index, instr_index, from, to, amt]`，
  `instr_index=-1` 哨兵（tokenBalances 是交易级 pre/post 快照，SQD 服务端字段枚举无 instruction
  字段；pair_tx 本就是交易级净额口径）。不落盘签名（按 (slot, tx_index) 可反查）。
- **meta 升 `sqd-solana-cache/v4`**，新增：`collector_sha256`（启动冻结）、`edge_schema`、
  `edge_semantics="owner-net-greedy"`、`order_granularity="transaction"`、`dedupe_identity`、
  `finalized_upper_slot`。
- **去重契约＝交易身份级**：以 finalized 区间内 `(slot, tx_index)` 为交易身份，对每笔交易的
  完整边集算排序后 `tx_digest`；重复身份 digest 相同→留一份；**digest 不同→硬失败**
  （数据源冲突禁静默取并集）。
- **输入卫生 fail-closed**：`tx_index` 必须非布尔非负整数；金额解析失败/owner 缺失从静默跳过
  改为整段重试或失败。
- **owner-authority 错账并刀修**（`:285`）：拆两个 owner 级 delta（preOwner: −preAmount /
  postOwner: +postAmount，同 owner 自然合并为 post−pre），附七条硬规则：请求并核验
  `account/preMint/postMint`；只计目标 mint 侧；同 `(tx_index, account)` 重复检测防双计；
  非零金额缺 owner→硬失败；非法/负金额→硬失败；close+reinit 换 mint 不得计入；
  Token-2022 transfer-fee/withheld 独立 fixture。
- **消费端两态分立**：正式路径（新采/reconcile/READY/发布）只认 v4 meta＋7 元组，混合行宽拒绝，
  禁按行长度静默嗅探；诊断路径显式 `--legacy-sol5` 入口，输出强制标 `order_ambiguous/non-formal`，
  不得生成 v4 meta/v4 reconcile/READY。
- **HyperSync 分支硬禁**（v4 下 exit 2；该通道在案"已禁用勿启"，不能留第二种隐含五元组出口）。
- **共享核**：pair_tx＋owner 解析＋sha256(mint) 路径解析抽单一纯函数模块，
  `fetch_sqd_transfers_v2.py`/`window_fetch.py`/`curve_cost.py`/`audit_closed_accounts.py` 共用。
- v3 meta 与旧 `.parts` 在创建/读取 v4 parts **之前**硬拒（防混格式污染）；5 元组无法补身份、
  无迁移路径，拒绝时明示全量重采。
- 旧案处置："gate-PASS＝无碰撞"是错的（环形/互抵删边末态无痕）；旧案不重跑，建 v4 风险复核
  名单交用户；v3 缓存文件留盘不销毁。

## 批次（顺序执行，每批独立工单）

1. 语义冻结＋共享核（pair_tx 双键＋打乱性质测试先红后绿）
2. 采集器 v4（7 元组＋tx_digest 去重＋输入卫生＋owner 七硬规则＋meta v4＋前置硬拒＋HyperSync 禁）
3. 消费端两态分立（replay_edges/wave_scan/传导件/audit_closed_accounts/curve_cost/window_fetch/
   camp_series_provenance）
4. 登记守卫测试（producer_history 两步登记；invariant_manifest 机器清点；测试面改写＋五件新回归＋
   ARC parts oracle；run_all 登记）
5. 验收收口（ARC 定向双 window 真采；绿例；grep 清零；破坏性注入；CHANGELOG/VERSION 6.49.0）

## 全程纪律（每批工单默认继承）

- 分支 `fix/sqd-solana-v4`，基线 main=e1be99a（6.48.1）；开工必验 `git status` 干净；
  批内小步 commit（中文信息，仿库内惯例）；**修复批次冻结**：一轮修复期间不掺新功能。
- 每个 bug 按维护件 `references/maintenance-review-repair.md` 第三节五栏工单填全才动手；
  修复新建代码本身按六视角①②自审。
- 先红后绿：红态测试输出必须保存进交付物（不许只自报）；验收方将按"grep 清零不信自报、
  破坏性注入反证、边界外一步攻击"复核。
- VERSION/CHANGELOG 只在批 5 统一 bump；历史 CHANGELOG 不许改写。
- 交付物：每批 `maintenance/repair-20260817-sqd-v4/batchN_done.md`（改动清单、五栏台账、
  红→绿证据、SUITE 结果、遗留事项、归因预判）。完成即停等验收。
