# 批 5 完工记录：ARC 真采、破坏性注入与 6.49.0 收口

日期：2026-08-18  
分支：`fix/sqd-solana-v4`  
开工基线：`8f2dd44`（批 4 完成态）  
范围：严格执行 `batch5_workorder.md`；不合并 `main`，不 push。

## 1. 结论

批 5 的 T1–T5 已全部完成：

- ARC 高碰撞窗与无碰撞绿例窗均由现役 v4 collector 真采，落在本仓库 `live_windows/`；
- 两窗 v4→5 字段投影与案内 tx-aware 边按 multiset 逐边零差；
- 三组同五字段碰撞经 SQD 原始 `transactionIndex` 与 Solana `getBlock` 六个不同签名交叉确认；
- 对真实碰撞窗副本执行单逻辑字节、未登记 collector hash、v3 meta 三种破坏性注入，均命中预期正式拒绝分支；
- 正式非白名单 Python 路径 5 元组解析/解包命中为 0；
- 文档、CHANGELOG 与版本锚统一收口到 `6.49.0`；
- `scripts/tests/run_all.py` 的 120 项全部通过，独立 invariant/docs/routes/version 复跑亦全部通过。

没有改动生产 `scripts/`，没有改写 ARC 案目录，没有合并或 push。

## 2. 开工收编与施工提交

工单先以独立提交收编，再按 T1–T4 小步提交：

```text
f828983 批5：收编ARC真采与版本收口工单
4dec51f 批5 T1：固化ARC双窗口真采证据
93f9af0 批5 T2：完成真采实物破坏性注入三连
43a5978 批5 T3：清点正式路径五元组残留与白名单
43b5b0a 批5 T4：收口SQD v4文档与版本6.49.0
```

本文件的收尾提交不列入上述开工至 T4 的冻结序列。

## 3. T1：ARC 定向双 window 真采

### 3.1 数据源与身份边界

- mint：`61V8vBaqAGMpgDQi4JcAwo1dmBGHsyhzodcPqnEVpump`；
- SQD：`https://portal.sqd.dev/datasets/solana-mainnet`，免认证、只读；
- Solana RPC：`api.mainnet-beta.solana.com`、`solana-rpc.publicnode.com`；
- 主网 `getGenesisHash`：`5eykt4UsFv8P8NJdTREpY1vzqKqZKvdpKuc147dw2N9d`；
- collector SHA-256：`2589f6a396c262d0747343ef21dee2bc7ba814eaa59eebdfa782fe9253c32212`，命中 ACTIVE producer 登记；
- ARC 案目录只读；命令、工具和产物均在本仓库执行/落盘。

### 3.2 双窗结果

| 窗口 | slot（含界） | slot 数 | v4 行 | 案内行 | 投影 multiset | 碰撞保留 |
|---|---:|---:|---:|---:|---|---|
| collision | 382697976–382714174 | 16,199 | 5,696 | 5,696 | live-only=0，case-only=0 | 85 组／额外 114 行／最高 5 倍 |
| green | 374331356–374344169 | 12,814 | 142 | 142 | live-only=0，case-only=0 | 0 组／额外 0 行 |

两窗 meta 均为 `sqd-solana-cache/v4`、严格 7 元组、
`edge_semantics=owner-net-greedy`、`order_exact=false`、
`dedupe=slot-txindex-digest/v1`，并与边实物行数及逻辑摘要相符：

- collision：`2fbb127d440d7ff7ef6082eba3521b7bc8eb43236b3740b3bfc39cb06a51b201`；
- green：`401682426db942bf58ea2241bdcc47aaf50b642b3495d02406f3ed63421b55ef`。

T5 从已提交实物重新执行：

```text
python3 maintenance/repair-20260817-sqd-v4/tools/live_window_verify.py
```

结果：`status=PASS`。

### 3.3 三组在线碰撞抽样

| slot | SQD transactionIndex | Solana `getBlock` 签名关系 | 结论 |
|---:|---|---|---|
| 382698123 | 241、1054 | 两个不同签名 | 两个不同真实交易 |
| 382700107 | 820、928 | 两个不同签名 | 两个不同真实交易 |
| 382701804 | 697、1200 | 两个不同签名 | 两个不同真实交易 |

三次 SQD 原始响应均为 HTTP 200，六笔 transaction 状态均为 `err=null`；三个 RPC block 的索引均在界内，六个签名互异。详细 owner 余额与签名见 `live_windows/evidence.md`。

### 3.4 owner-change 降级

案内 `owner_authority_repairs.json` 记录只读扫描 146,759 个 block 文件、9,163,215 条
tokenBalance，`repairs=[]`。因此没有可定向真采的 ARC owner-change 窗；按工单降级为批 2
fixture＋案内全量扫描证据，不构造也不声称 ARC 存在此实例。

## 4. T2：真实实物破坏性注入三连

所有注入只在系统临时目录复制 T1 collision 数据后实施。源 edge/meta 前后 SHA-256 分别保持：

- edge：`27d3a900e73832216b0e61fc622dbeb281feac2e9176585d79a0384ca7199917`；
- meta：`831887be6f11ead8210f06943ef34f86bc6463cf0e10a3fce1cbcadb4f8b3824`。

| 注入 | 自证 | 正式入口结果 | 目标分支 |
|---|---|---|---|
| 边逻辑流单字节 | offset 139，ASCII `6→8`，长度不变，Hamming=1 | rc=2：`BLOCK: SQD 缓存 meta.edge_logical_sha256 与实际边重放摘要不一致` | reconcile 实际遍历边后的逻辑摘要对表 |
| collector hash 未登记 | 改为 64 个 `f` | rc=1：`SQD v4 meta.collector_sha256 未命中 fetch_sqd_transfers_v2.py producer 登记` | `_validate_cache_meta` producer history 查表 |
| v3 meta | schema/version 降为 v3 | replay rc=1；collector rc=2，报“格式升级需全量重采” | formal v4 meta gate＋producer 网络前升级闸 |

第三项 collector 同时把 SQD/RPC 指向 `127.0.0.1:9`；返回的是旧 meta 专用升级拒绝，而非连接错误，证明拒绝发生在任何网络请求和 v4 part 写入之前。

T5 重放：

```text
python3 maintenance/repair-20260817-sqd-v4/tools/destructive_injection_verify.py
```

结果：三项 `target_branch_reached=true`，源实物不变，总状态 `PASS`。详细结构化输出见
`live_windows/injection_evidence.md`。

## 5. T3：grep 清零与 legacy 白名单

宽扫全仓 Python 解析/解包后，命中恰为 6 个文件：

- 现役显式 legacy 白名单：`replay_edges.py`、`wave_scan.py`、`audit_closed_accounts.py`；
- maintenance 只读/迁移工具：`import_pythia_legacy.py`、`arc_parts_oracle.py`、
  `live_window_verify.py`。

排除上述三份现役白名单及测试后，`scripts/` 正式路径命中为 0。三个现役白名单均需显式
`--legacy-sol5`，强制 `non_formal/order_ambiguous`，且不得进入 reconcile/evolution/READY。
完整命令、逐文件理由和测试豁免见 `grep_legacy_whitelist.md`。

## 6. T4：文档与版本收口

### 6.1 数字口径

现役口径已经固定为：

- 冻结 1,348 个 parts 域内：multiset 1,775,858 行，五字段 DISTINCT 1,764,356 行，机械可证损失
  **11,502 行／8,487 碰撞组／最高 23 倍率**；
- **124,816** 只是 ARC 两版全史边表行数差，混入两次采集间其他差异，不能称为纯 DISTINCT 损失。

`PLAN.md` 原文没有改写；只在文件尾部追加具名勘误注记。CHANGELOG 新增 6.49.0 索引和完整条目，明确缺陷、@CX 三项设计拦截、五批结构、纵深防线、实弹结果与范围。

### 6.2 运行文档与版本锚

- `references/data-pipeline-solana-capture.md` 已改为 v4 7 元组、transaction digest 去重、
  v4/legacy 两态分立；
- 文档诚实保留 `audit_closed_accounts.py` 当前覆盖谓词仍为 slot+owner，而不是把 7 元组误称为
  transaction-exact；
- `VERSION`、`SKILL.md`、`pyproject.toml` 三处统一为 `6.49.0`；
- `runtime_docs_manifest.json` 与 `contract_manifest.json` 既有登记已覆盖所改现役文档与契约锚，
  无需为凑变更而改写。

## 7. T5：收批全验

### 7.1 全仓 suite

```text
python3 scripts/tests/run_all.py
```

结果：退出码 0，**120/120 全部通过**。其中包括：

- `test_sqd_merge_equiv.py`；
- `test_spl_edge_core.py`；
- `test_sqd_collector_meta_v4.py`；
- `test_sqd_consumer_v4.py`；
- `test_collector_history.py`；
- `test_version_consistency.py`；
- 其余全仓登记测试。

### 7.2 工单点名独立复跑

| 命令 | 结果 |
|---|---|
| `python3 scripts/tests/invariant_scan.py` | PASS：63 producers、95 consumers、63 transport calls、54 atomic writes、58 formal entrypoints、exceptions=0 |
| `python3 scripts/tests/docs_lint.py --all` | PASS：58 个文档，无断链，粗体配对完整 |
| `python3 scripts/tests/test_contract_routes.py` | PASS：R-01/R-02、ID 快照、五组锚、SKILL 原子阶段双向闭合 |
| `python3 scripts/tests/test_version_consistency.py` | PASS：三处版本元数据一致为 6.49.0 |
| `git diff --check` | PASS |

## 8. ARC 案目录只读终检

T5 重哈希值与批 4/T1 开工值完全一致：

| 案内实物 | SHA-256 |
|---|---|
| `data/collector_part_manifest.json` | `bc72747223aa732f030c9badc982785745d8daba3c605b07abccbf2ac43c30b2` |
| `data/holders_owners.json` | `6dd0bb4c8061871586e0433eba1a9eb3e6dacc49f778a118a18ef5ca944d4abe` |
| `data/owner_authority_repairs.json` | `c40bfe79bb7beb241410e7d85d24473fcac0f2963d26c56562ae2c8bdde585fa` |
| tx-aware repaired edge | `9f08bab2f111ec21768a40ba3bc051d0276c5f05b7dc7918e41fda984279e71d` |
| tx-aware repaired meta | `e9d64a12b5a96b8c68352981285b2a066e16eca53609a32019299abef78605f6` |

## 9. 六视角自审

### 9.1 字段来源

- v4 边来自现役 SQD collector，`transactionIndex` 取自 SQD transaction/tokenBalance 原始字段；
- `instr_index=-1` 与 `order_exact=false` 成对，不伪造 instruction 顺序；
- `from/to/amt` 是 owner 余额净变化的确定性贪心配对，只声明 `owner-net-greedy`；
- 碰撞在线证据以 SQD 原始 transactionIndex 对照 Solana `getBlock` 同索引签名；
- 案内比较使用逐边 `Counter` multiset，不以总行数相同替代边相同；
- meta 的 collector identity、行数和逻辑摘要均从实物独立重算后对表。

### 9.2 失败路径

- 最初 urllib 访问公共 RPC 遇到 TLS/403，未记作成功；验收工具改用 `requests`，仍通过
  `SolanaAttestedSession` 先验 genesis，再执行业务请求；
- publicnode 对该访问方式返回 403，最终成功抽样节点为 `api.mainnet-beta.solana.com`；
- ARC owner-authority 扫描没有实例，按工单降级，不用 fixture 冒充真链发现；
- 三种破坏性注入均验证目标分支错误原文与返回码，不以“命令失败”笼统代替守卫命中；
- 全仓 suite 在允许 loopback `socket.bind` 的验收环境执行，退出码 0；没有把沙箱权限错误包装成绿；
- 正式非白名单 grep 的零命中以 `rg` rc=1 为预期并由包装命令转为 PASS，白名单逐项说明用途。

## 10. 改动清单

新增：

- `batch5_workorder.md`；
- `grep_legacy_whitelist.md`；
- `tools/live_window_verify.py`；
- `tools/destructive_injection_verify.py`；
- `live_windows/evidence.md`；
- `live_windows/injection_evidence.md`；
- collision/green 两窗各一份 v4 edge 与 meta；
- 本 `batch5_done.md`。

修改：

- `PLAN.md`（仅尾部追加勘误）；
- `references/data-pipeline-solana-capture.md`；
- `CHANGELOG.md`；
- `VERSION`、`SKILL.md`、`pyproject.toml`。

生产 `scripts/` 相对批 4 基线的改动：**0**。

## 11. 遗留与验收方关注点

1. `audit_closed_accounts.py` 默认已严格接 v4，但覆盖谓词仍是 slot+owner；签名尚未映射到
   `(slot,tx_index)`。本批已在现役文档明示，不能把该补充抽查称为 transaction-exact。
2. `fetch_sqd_transfers_v2.py` 内有一处旧“5 元组”内存估算注释；运行契约和正式输出均为 7 元组。
   本批没有为改注释而改变已登记 ACTIVE producer SHA，留给后续按 producer 轮换纪律处理。
3. ARC 案内没有 owner-change 真例；当前证据强度止于批 2 fixture＋案内 9,163,215 条
   tokenBalance 的零修复扫描。
4. 公共 RPC 的可达性依赖客户端传输实现；本批成功证据绑定到已记录的 genesis 与实际抽样响应，
   不外推为两个节点在所有客户端下都可用。

以上均不是本工单的未完成项，但应由 opus/Fable 验收时按声明强度复核。

## 12. 停止点

批 5 施工完成。按工单在写入并提交本文件后停止；不合并 `main`，不 push。
