# 批 1 工单：语义冻结＋共享核抽取＋pair_tx 确定性修复

> 先读同目录 `PLAN.md` 全文（工程总纲与全程纪律）。本批只做下列任务，禁越批施工。

## 开工序

1. `git -C <仓库根> status` 检查：**除 `maintenance/repair-20260817-sqd-v4/` 下的调度件
   （PLAN.md、batch*_workorder.md 等，由调度方放置）外必须干净**；确认 HEAD=e1be99a（6.48.1）。
2. `git checkout -b fix/sqd-solana-v4`；**首个 commit＝把 `maintenance/repair-20260817-sqd-v4/`
   现有调度件收编入库**（提交信息注明"工程调度件收编"）。
3. 跑一遍 `python3 scripts/tests/run_all.py` 记录基线全绿（保存输出摘要进 done 报告）。

## 任务

### T1 【修复工单·五栏】pair_tx 非确定性

```text
bug：pair_tx 等额时输出依赖 SQD 返回序，同一交易两次采集可配出不同边
1. 不变量：同一笔交易的 tokenBalance 记录集合，无论以何种顺序输入，pair_tx 必须
   产出逐字节相同的边集合（采集重放确定性——这是 v4 交易身份去重的前提）。
2. 同族清单：rg 全库列出 pair_tx 的全部实现/复制点（已知 fetch_sqd_transfers_v2.py:151-168
   与 window_fetch.py 内的复制版；rg 确认有无第三处），全部一起修。
3. 三件套测试：
   a. 原反例（先红）：等额多方 fixture（A、B 各 −10；C、D 各 +10），对现行单键排序
      以两种不同输入顺序调用，断言输出不同 → 红；修复后断言任意打乱输出逐字节一致 → 绿。
   b. 同族变体：随机化性质测试——随机生成 delta 集合（含等额、含超 int64 金额、含 ZERO
      哨兵参与的 mint/burn 边），随机 shuffle N 轮，输出必须恒等。
   c. 失败分支：非法输入（金额非整数、owner 为 None）必须抛错 fail-closed，不得静默跳过
      （注意：本批只加共享核入口的校验骨架，采集器调用侧的整段失败语义属批 2，不在本批改）。
4. 新建代码自审：共享核模块按六视角①②过一遍，结论写进 done 报告。
5. 归因预判：历史漏检（缺陷在 v2 采集器诞生起即存在，非某次修复引入）。
```

修法：正负两侧排序键改 `(-amount, owner)` 双键（owner 为 str 全序）。

### T2 共享核抽取（结构任务）

新建 `scripts/solana/spl_edge_core.py`（纯函数模块，无 IO、无网络）：
- `pair_tx(delta)`（含 T1 确定性修复）；
- owner delta 归集辅助（本批**原样迁移**现行为——`owner = post or pre` 的 owner-authority
  语义缺陷属批 2 修，本批禁止顺手改，防批次污染验收基线）；
- `soltx_cache_paths(mint, data_dir)`：sha256(mint) 路径三件套解析（从
  fetch_sqd_transfers_v2.cache_paths 迁移语义）。
`fetch_sqd_transfers_v2.py` 与 `window_fetch.py` 改为 import 共享核；`curve_cost.py`、
`audit_closed_accounts.py` 的旧小写 mint 路径**本批不动**（属批 3 消费端），只在共享核里
把公共函数备好。

迁移等价守卫：迁移前后对固定 fixture（含非等额常规场景）输出逐字节一致；等额场景按
新确定性序（在测试中显式断言新序）。

### T3 语义冻结（文档＋机器件同 commit）

- `references/scan-schemas.md`：§边格式段——7 元组由"扩展"改"现役标准"；新增 transaction-net
  语义定义（`edge_semantics="owner-net-greedy"`、`order_granularity="transaction"`、
  instr_index=-1 哨兵含义、"推定配对≠链上精确 from→to 关系"声明）；`:17` "同五元组合法重复"
  措辞升级为身份化表述（5 元组降级 legacy 诊断格式）。
- `references/data-pipeline-solana-capture.md`：§8 边语义补 tx_index；§13b "无 sig 同 slot
  同额多笔的去重边界"小节整段重写为交易身份口径；§12:94 "无 sig 粒度"声明标注将随 v4 作废
  （正文改写属批 3 落地后，本批先加过渡标注，避免文档超前于代码）。
- 机器件同 commit：语义常量落进 `spl_edge_core.py`（如 `EDGE_SEMANTICS = "owner-net-greedy"`、
  `ORDER_GRANULARITY_TX = "transaction"`、`INSTR_INDEX_TX_NET = -1`、7 元组字段序常量），
  供批 2/3 引用——防"文档先行无机器件"漂移。
- 注意 `scripts/tests/runtime_docs_manifest.json` 与契约 `CT-SEMANTIC-29`（needle
  `data/soltx-*.jsonl.gz`，authority=analyze-workflow.md）：文档修订不得破坏既有 needle 命中；
  改后跑契约/不变量扫描确认。

### T4 测试落位

新测试文件 `scripts/tests/test_spl_edge_core.py`（T1 三件套＋T2 迁移等价）；
`scripts/tests/run_all.py` SUITE 登记。全 SUITE 必须全绿后才准 commit 收批。

## 禁动范围（越线＝流程事故）

- 不改 `replay_edges.py`/`wave_scan.py`/`flow_anomaly_scan.py`/`entity_source_trace.py`/
  `camp_series_provenance.py`/`audit_closed_accounts.py`/`curve_cost.py` 的任何行为（批 3）。
- 不改 meta schema/落盘行格式/合并器（批 2）——本批产出物仍是 5 元组现行为，只是内部实现
  搬进共享核＋pair_tx 确定性修复。
- 不动 `producer_history.py`/`invariant_manifest.json`（批 4）、不 bump VERSION（批 5）。
- 不触碰任何案目录与 EVM 侧脚本。

## 交付物

`maintenance/repair-20260817-sqd-v4/batch1_done.md`：改动文件清单（含行数）、五栏台账、
红→绿测试输出原文（红态与绿态各一段）、基线与收批两次 run_all 输出摘要、同族 rg 清单及
逐条处置、新建代码六视角①②自审结论、遗留事项。完成即停，等验收，不开批 2。
