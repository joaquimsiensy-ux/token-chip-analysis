# 批 4 工单：采集侧摘要闭环＋producer 登记＋invariant 清零＋ARC parts oracle

> 先读同目录 `PLAN.md` 与三份 batch*_done.md。分支 `fix/sqd-solana-v4` 续作（开工先收编本
> 工单为独立 commit）。**本批解禁采集器一处**（T1 摘要字段），登记面全面解冻。
> **收批标准＝SUITE 全绿含 invariant_scan（本工程首次零 FAIL 收批）。**

## 任务

### T1 采集器 meta 补 `edge_logical_sha256`（批 3 遗留 2 闭环）

批 3 发现工单前提错误：采集器实际不写 `edge_logical_sha256`，消费端 reconcile 现为
"meta 有值必须一致、缺失原子回填"。本批闭环：`merger.finalize()` 成功后、meta 原子发布前，
对最终 gz 逐行按与 `replay_edges` 正式路径**同一算法**计算逻辑摘要与行数写入 meta
（`edge_logical_sha256`＋`edge_rows`）。两侧同算法必须有对测（采集器产 meta → replay 重算
一致；篡改一行 → replay 拒）。此改动后采集器文件定型，为 T2 登记基准。

### T2 producer 登记与消费端对表闭环（Solana 侧归属防线收口）

- T1 commit 落定后，按 `git show <T1后commit>:scripts/solana/fetch_sqd_transfers_v2.py |
  shasum -a 256` 把采集器登记进 `scripts/lib/producer_history.py`
  （script＋protocol `sqd-solana-cache/v4`＋status ACTIVE＋commit＋reason，准入纪律照旧：
  禁 dirty hash）；`window_fetch.py`（protocol `solana-window-fetch-receipt/v3`）同登记。
- `replay_edges.py` 与 `camp_series_provenance.py` 正式路径新增对表校验：v4 meta 的
  `collector_sha256` 必须命中 `historical_producer_hashes(script, protocol)` 的 ACTIVE 集合
  （protocol＋script path＋hash＋status 四要素）；不命中→fail-closed 拒。
  测试：正版哈希过；伪造/改装采集器哈希拒（这是 ARC hotfix 冒名场景的永久拦截）；
  REVOKED 语义沿用现有 hash-wide 优先级。
- 维护规则写进 done：今后任何采集器改动 commit 后必须同步追加登记条目，否则新采数据会被
  消费端拒——这是防线的日常代价，明示不隐藏。

### T3 invariant_manifest 机器清点清零

以收批时 `invariant_scan.py` 实际输出为准（批 3 报 18 条，T1 可能再增 finalize/persist
locator 差异——**不照抄任何预数**），逐条把登记表升到与现役代码一致：v3→v4 schema 替换、
wave-scan/v4、window receipt v3、consumer 组合、atomic_writes locator。禁删除与本工程无关
的条目；每条差异的处置在 done 列清单。

### T4 ARC parts 六件套 oracle（验收工具，一次性运行）

**案目录只读铁律**：ARC 案 `/Users/uravvv/Documents/5.6筹码分析/ARC分析/` 只准读，
禁任何写入/重命名/删除。oracle 工具与产物全部落本仓库 `maintenance/repair-20260817-sqd-v4/tools/`
与 `.../oracle/`。

工具脚本（独立实现，不 import 生产合并器——oracle 与被测物解耦）：
1. **parts manifest 冻结**：定位 ARC 案的 1348 个 parts（案内 `data/collector_part_manifest.json`
   有清单与路径线索），逐个记录 文件名/字节/行数/SHA256/slot 区间，落
   `oracle/arc_parts_manifest.json`；
2. **区间不重叠证明**：按 slot 区间排序验证两两互斥（重叠即如实记录，不隐藏）；
3. **双语义合并对照**：multiset（UNION ALL）vs 五字段 set（DISTINCT）双跑（DuckDB，
   注意内存参数），固化总行数差（预期 124,816——**以实测为准**，不符照实报）；
4. **碰撞分布**：碰撞组数、每组倍率分布、按 slot 密度分布，落 JSON；
5. **owner 末态差异**：两套合并结果各自做简化余额重放（+to/−from，ZERO 哨兵按铸销），
   对照差异 owner 数与负余额 owner 数（预期与 ARC 案 820 负余额量级吻合；案内
   `data/holders_owners.json` 只读可用则加一层快照对照，不可用则如实降级）；
6. **两路径等价压测**：oracle 自身的两条实现路径（内存/DuckDB）对同一输入逐字节等价。

产物：`oracle/arc_oracle_report.json`＋done 报告叙述。运行时间预计 10-30 分钟，属一次性
验收件**不进 SUITE**；SUITE 只进可移植 fixture。

### T5 五件回归完整性核对

逐条确认已在 SUITE：①同 slot 等额双 tx 保留（批 2 T1a）②owner 变更错账（批 2 T2a）
③pair_tx 打乱性质（批 1）④同交易跨 part 重复留一（批 2 T1b）⑤同五字段不同 tx_index 留二
（批 2 T1a 变体）。缺项补齐；`run_all.py` 登记完整性核对（新增测试全部在 SUITE 硬编码清单）。

## 禁动范围

采集器仅 T1 一处解禁（摘要字段），其余逻辑禁动；消费端仅 T2 对表校验解禁；
VERSION/CHANGELOG（批 5）；EVM 侧；ARC 案目录只读。

## 交付物

`batch4_done.md`：T1 两侧同算法对测证据、T2 登记条目与对表拒绝红→绿、T3 逐条差异处置清单
＋invariant_scan 零差异输出、T4 oracle 报告要点（行数差实测值、碰撞分布、owner 末态对照）、
T5 核对表、SUITE 全绿输出、六视角①②自审、遗留事项。完成即停，不开批 5。
