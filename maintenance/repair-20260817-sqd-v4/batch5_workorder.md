# 批 5 工单：ARC 定向真采验收＋端到端注入＋版本收口

> 先读同目录 `PLAN.md` 与四份 batch*_done.md。分支 `fix/sqd-solana-v4` 续作（开工先收编本
> 工单）。本批允许**定向出网**（SQD portal 免认证只读、Solana 公共 RPC 只读）；
> ARC 案目录依旧**绝对只读**。合并 main 与 push 不在本批（由验收方在 opus 盲审后执行）。

## 任务

### T1 ARC 定向双 window 真采（v4 端到端实弹）

1. **碰撞窗**：从批 4 `oracle/arc_oracle_report.json` 的碰撞分布选 1-2 个高碰撞 slot 窗
   （每窗 ≤50,000 slot，采集分钟级）；用现役 v4 采集器对 ARC mint
   （`61V8vBaqAGMpgDQi4JcAwo1dmBGHsyhzodcPqnEVpump`）真采到本仓库
   `maintenance/repair-20260817-sqd-v4/live_windows/<窗名>/data/`（新目录，配 `--from/--to`
   或等价窗口参数按采集器实际 CLI）。
   验证：a) 落盘行为 7 元组且 `tx_index` 非空；b) 已知碰撞样本（同 slot 等额异 tx）在 v4
   产物中**保留多行**；c) 与 ARC 案 codex tx-aware 边表同窗行数一致（后者只读投影对照——
   v4 行去掉 tx/instr 两列后与 5 元组 multiset 相等）；d) meta v4 全字段（含
   `edge_logical_sha256`、`collector_sha256` 命中登记表）。
2. **独立抽样确认**：从碰撞窗任取 ≥3 组碰撞，向 SQD portal 重放原始查询核 `transactionIndex`，
   并用 Solana 公共 RPC `getBlock`（api-keys 附B 的免注册双节点路由，只读）按
   `(slot, tx_index)` 反查交易签名，确认两笔确为链上不同交易。证据（请求/响应摘录）落
   `live_windows/evidence.md`。
3. **owner-change 窗**：只读 ARC 案 `txowner_collect/` 与 `data/owner_authority_repairs.json`
   等产物寻找已发现的 owner 变更 slot；找到则对该窗真采验证双侧记账落盘；找不到可用窗则
   如实降级为"单元 fixture 覆盖（批 2 已有）＋案内扫描证据引用"，禁伪造。
4. **绿例防误伤窗**：选一个无碰撞低密度窗真采，v4 产物 5 元组投影与 ARC tx-aware 边表
   同窗逐边相等（除新列零差异）。

### T2 端到端破坏性注入三连（对 T1 真采实物）

复制 T1 产物到临时目录后注入（原件不动）：
1. 边文件任改 1 字节 → `replay_edges.py`（正式路径，reconcile 或等价读入）必拒；
2. meta `collector_sha256` 改为非登记哈希 → 对表校验必拒；
3. 把 v3 meta（案内样式，自行构造）换入 → 前置硬拒且拒绝文案正确。
每条注入按"注入须自证到达目标分支"纪律：先证明注入物真的走到被测校验点。

### T3 grep 清零与 legacy 白名单

全库机器扫描：正式路径零 5 元组解析残留。方法：rg 列出所有仍含 5 元组解析/构造的现役文件，
逐条归类（legacy 显式入口白名单 / 测试 fixture 合法 / 违规残留）。白名单与豁免理由落 done；
违规残留＝0 才收批。

### T4 文档收口与版本

- `data-pipeline-solana-capture.md` §12 "无 sig 粒度"过渡标注改为正文定稿（v4 语义）；
  全册与 `scan-schemas.md` 最后一致性通读（六视角⑤双向核对）。
- `CHANGELOG.md` 新增 6.49.0 条目（叙事完整：缺陷/ARC 实证/五批结构/@CX 三拦/防线）；
  `VERSION` → `6.49.0`。历史条目零改写。
- **数字口径纪律（批 4 oracle 翻案落笔）**：CHANGELOG 与一切新叙述必须采用修正口径——
  ①冻结 parts 域内机械证明的 DISTINCT 损失＝**11,502 行 / 8,487 碰撞组（最高 23 倍率）**；
  ②124,816＝ARC 两版全史行数差的**混合口径**（含两次采集间其他差异），禁再表述为
  "DISTINCT 吃掉 124,816 条"。同时在 `PLAN.md` 文件**尾部追加勘误注记**（原文不改写，
  历史记录不可为守卫改写纪律），指向 batch4_done.md §6.3。
- `runtime_docs_manifest.json`、契约表如有联动按机器清点同步。

### T5 收批全验

SUITE 全绿（含 invariant_scan）＋`docs_lint --all`＋契约路由测试；把 T1-T4 全部证据整理进
`batch5_done.md`。

## 禁动范围

采集器/消费端生产逻辑（批 2-4 已定型，发现问题记 done 遗留交盲审，禁顺手改）；
ARC 案目录只读；merge/push 不做。

## 交付物

`batch5_done.md`：双 window 采集参数与验证四项、独立抽样证据、注入三连自证记录、grep
清零白名单、版本 diff、SUITE 全绿输出、六视角①②自审、遗留事项（交 opus 盲审的自述风险清单）。
完成即停。
