# 批 4 施工交付：采集摘要闭环、producer 登记、invariant 清零与 ARC parts oracle

## 1. 结论

批 4 已严格按 `T1 → T2 → T3 → T4 → T5` 完成并停工，没有启动批 5。

- SQD v4 采集器在最终 gz 合并成功后、正式 meta 原子发布前，重读最终边文件并写入
  `edge_rows` 与 `edge_logical_sha256`；采集侧与 replay 侧对同一 7 元组采用同一规范化算法，
  实物篡改或坏行均 fail-closed。
- `fetch_sqd_transfers_v2.py` 与 `window_fetch.py` 已按 T1 的干净 commit 实物登记到
  `producer_history.py`；replay 与 camp 正式路径均要求 collector 的 script、protocol、hash、
  ACTIVE 状态四要素对表通过。
- `invariant_manifest.json` 按机器实扫的 18 条差异逐项更新；最终 `invariant_scan.py` 零差异。
- ARC 1348 个冻结 parts 已由独立 oracle 完成清单、区间、双语义、碰撞、owner 末态、双路径等价
  六项核验，且前后重哈希证明案目录未被改写。
- 五件指定回归均在 `run_all.py` 硬编码 SUITE 中。最终全量 SUITE 120/120 PASS，包含
  `invariant_scan.py` 与 Solana/EVM 两项 loopback 纵切片。

## 2. 开工序与边界

- 分支：`fix/sqd-solana-v4`。
- 批 3 交付基线：`4c6720c`。
- 开工前已全文读取：`PLAN.md`、`batch1_done.md`、`batch2_done.md`、`batch3_done.md`、
  `batch4_workorder.md`。
- 工单先以独立 commit `7fb89df 批4：收编采集摘要与登记守卫工单` 收编，之后才改代码。
- 解禁范围严格限于：T1 采集器摘要字段、T2 replay/camp 对表、T3 登记表、T4 本仓库
  maintenance oracle、T5 测试。VERSION/CHANGELOG、EVM 生产侧均未改。
- ARC 案 `/Users/uravvv/Documents/5.6筹码分析/ARC分析/` 全程只读；工具与产物只落本仓库。

## 3. T1：采集器 meta 逻辑摘要闭环

### 3.1 缺口与归因

批 3 已实证原工单前提不成立：现役采集器成功产出边文件后，meta 没有 `edge_rows` 和
`edge_logical_sha256`，只能由 replay 后补。该问题归类为**老问题修复不全（半修残留）**：消费侧
已有摘要重算与回填，但“采集成功即绑定实际边实物”尚未闭合，不是本批新设计的功能扩张。

### 3.2 实现

`scripts/solana/fetch_sqd_transfers_v2.py` 新增 `logical_edge_evidence(cache_fp)`：

1. 只在 `merger.finalize()` 成功后读取最终 gz；
2. 每行 JSON 必须通过既有 `validate_edge_row` 的严格 7 元组校验；
3. 对规范化 `json.dumps(list(edge), ensure_ascii=False) + "\n"` 流式计算 SHA-256，并计行数；
4. 空文件、坏 JSON、坏行宽或坏类型均拒绝，不发布成功 meta；
5. 重算行数必须与 merger 结果一致，再由 `persist_meta` 原子写入两字段。

### 3.3 红 → 绿证据

- 红 commit `ed1ec93`：真实 producer 完成 1 条边，但 meta 缺少两字段，新增测试明确失败。
- 绿 commit `75aa622`：producer→replay 对同一文件得到相同逻辑摘要；篡改一行后 replay 拒绝；
  采集器面对最终 gz 的坏行也拒绝。
- 定向回归：`test_sqd_collector_meta_v4.py`、`test_sqd_merge_equiv.py`、
  `test_sqd_consumer_v4.py`、`test_r9_batch3_solana_observation.py` 全过。

T1 定型 commit 的完整 SHA 为：

```text
75aa622a546755a7848d211739a75f7b31f9e59b
```

## 4. T2：producer 登记与消费端对表

### 4.1 干净实物登记

登记哈希均来自 T1 commit 的 `git show <commit>:<path> | shasum -a 256`，没有登记 dirty
工作树：

| script | protocol | status | commit | SHA-256 |
|---|---|---|---|---|
| `scripts/solana/fetch_sqd_transfers_v2.py` | `sqd-solana-cache/v4` | ACTIVE | `75aa622a...` | `2589f6a396c262d0747343ef21dee2bc7ba814eaa59eebdfa782fe9253c32212` |
| `scripts/solana/window_fetch.py` | `solana-window-fetch-receipt/v3` | ACTIVE | `75aa622a...` | `56d94cbecf476b632c814a57b245c58397087dd105406e2538cac47c2fa6661c` |

### 4.2 消费链闭环

- `replay_edges.py` 正式 v4 loader 要求 collector ID 为 `fetch_sqd_transfers_v2.py/v4`，且
  `collector_sha256` 命中该 script＋protocol 的 ACTIVE 历史集合。
- `camp_series_provenance.py` 在已有 meta、摘要、行数、窗口、边实物锚定上增加同一归属校验。
- `historical_producer_hashes` 保留 hash-wide REVOKED 优先级：同一 hash 只要有 REVOKED，
  任何 ACTIVE 条目都不能把它重新放行。

### 4.3 红 → 绿证据与归因

- 红 commit `26f99cb`：格式完整但伪造的 `collector_sha256` 可被旧 replay 接受，证明冒名缺口真实。
- 绿 commit `b9e02f3`：正版 hash 通过；未登记/改装 hash 在 replay 与 camp 均拒绝；
  hash-wide REVOKED 反例仍拒绝。
- T2 收紧后，首轮全量测试暴露三处既有正式 fixture 未携带 collector 归属。这是
  **本批修复中新引入的测试夹具断裂**，不是应放宽生产校验的理由。`ef6117d` 仅让三个 fixture
  从 `producer_history` 取现役 hash；Resume Integrity、Batch C 227 checks、Batch D 均定向通过。

**日常维护规则**：今后任何正式采集器改动，必须先提交干净 commit，再按新实物追加
`producer_history.py` 条目；否则新采数据会被 replay/camp 拒绝。这是归属防线的必要维护成本，
不得通过登记 dirty hash、伪造旧 hash 或放宽消费者来规避。

## 5. T3：invariant manifest 机器清点清零

T3 开始前实际运行 `invariant_scan.py`，得到 18 条差异；没有照抄预数。逐项处置如下：

### 5.1 receipt producers：6 条

- `wave_scan.py`：删除已不存在的 `wave-scan/v3` 映射，登记 `wave-scan/v4`。
- `fetch_sqd_transfers_v2.py`：删除 `sqd-solana-cache/v3`，登记 `sqd-solana-cache/v4`。
- `window_fetch.py`：删除 `solana-window-fetch-receipt/v2`，登记 v3。

三组均各含“code 有而 manifest 缺”和“manifest 有而 code 无”，共 6 条。

### 5.2 receipt consumers：10 条

- `camp_series_provenance.py`：正式 cache 组合 v3→v4。
- `adjudication_validator.py`：wave 组合 v3→v4。
- `handoff_manifest.py`：保留历史 v1/v2/v3，同时补现役 v4。
- `curve_cost.py`：新增 `sqd-solana-cache/v4` 消费登记。
- `fetch_sqd_transfers_v2.py`：新增 v4 cache 自消费登记。
- `replay_edges.py`：保留显式 legacy v3，同时补正式 v4。

对应 6 条 code 缺登记和 4 条过时组合，共 10 条。

### 5.3 atomic writes：2 条

- `fetch_sqd_transfers_v2.py` locator 从已不承载写入的 `run` 改为真实 `persist_meta`：一增一删，
  共 2 条。

最终机器输出：

```text
PASS invariant manifest: receipt_producers=63, receipt_consumers=95, transport_calls=63, atomic_writes=54, formal_entrypoints=58, exceptions=0
```

## 6. T4：ARC parts 六件套独立 oracle

### 6.1 工具、输入与解耦

- 工具：`maintenance/repair-20260817-sqd-v4/tools/arc_parts_oracle.py`。
- 产物：`oracle/arc_parts_manifest.json`、`oracle/arc_oracle_report.json`。
- 工具没有 import 生产合并器；内存路径与 DuckDB 路径是两套独立实现。
- 输入为案内 `collector_part_manifest.json` 指向的 1348 个冻结 parts，仅覆盖该清单的 slot
  区间；oracle 是一次性验收件，没有加入 SUITE。

### 6.2 六件套实测结果

1. **manifest 冻结**：1348/1348 个文件的文件名、字节、行数、SHA-256、最小/最大 slot 与案内
   源 manifest 一致；总行数 1,775,858。
2. **区间不重叠**：排序后检查 1347 对相邻区间，重叠 0 对。
3. **双语义合并**：multiset 1,775,858 行；五字段 DISTINCT 1,764,356 行；差 11,502 行。
4. **碰撞分布**：8,487 个碰撞组；倍率分布为
   `2:6679, 3:1205, 4:351, 5:116, 6:68, 7:20, 8:15, 9:12, 10:7, 11:7, 12:3, 14:1, 15:1, 21:1, 23:1`。
5. **owner 末态**：multiset 与 DISTINCT 有 110 个 owner 末态不同；负余额 owner 分别为
   6,070 与 6,078。可读 snapshot 的 mismatch 仅作诊断：multiset 47,786、DISTINCT 47,820。
6. **双路径逐字节等价**：内存/DuckDB 两路 multiset 与 DISTINCT 的行数、字节数、SHA-256
   完全一致；multiset SHA 为 `8e943837...d089d79`，DISTINCT SHA 为 `b105dcae...b652e24`。

运行耗时 20.976 秒，oracle 状态 `PASS`。

### 6.3 对工单预期的反证与证据边界

- 工单的 124,816 行只是“预期，以实测为准”。冻结 parts 的实测差为 **11,502**，且与案内
  源 manifest 自报的 `duplicate_extra_row_count=11502` 完全一致，因此 124,816 被
  `REFUTED_BY_FROZEN_PARTS_AND_SOURCE_MANIFEST`，不能继续作为事实引用。
- 案内既有“约 820 个负余额”来自不同/更完整的样本口径；本 oracle 只重放 1348 个局部 slot
  parts，缺少区间前置余额与区间外事件，不能把 6,070/6,078 与 820 作同口径比较。snapshot
  mismatch 同样只说明局部重放不等于完整末态，不能反向归因给 DISTINCT。

### 6.4 ARC 只读证明

- oracle 完成后重哈希全部 1348 parts，`changed_parts=[]`。
- 源 manifest 前后 size/SHA-256 一致：568,819 bytes，
  `bc72747223aa732f030c9badc982785745d8daba3c605b07abccbf2ac43c30b2`。
- snapshot 前后 size/SHA-256 一致：2,694,062 bytes，
  `6dd0bb4c8061871586e0433eba1a9eb3e6dacc49f778a118a18ef5ca944d4abe`。
- `read_only_verification.verified=true`，案目录没有写入、重命名或删除。

## 7. T5：五件回归完整性核对

| 工单要求 | SUITE 实物 | 结论 |
|---|---|---|
| 同 slot 等额双 tx 保留 | `test_sqd_merge_equiv.py::c1a_distinct_poison` | 保留两个不同 tx_index，PASS |
| owner 变更错账 | `test_spl_edge_core.py::test_migration_equivalence_and_owner_authority` | owner authority 与迁移等价回归，PASS |
| `pair_tx` 打乱性质 | `test_spl_edge_core.py::test_random_shuffle_is_byte_deterministic` | 随机打乱仍字节确定，PASS |
| 同交易跨 part 重复留一 | `test_sqd_merge_equiv.py::c1_c2_equivalence` | 同一交易跨来源去重，PASS |
| 同五字段不同 tx_index 留二 | `test_sqd_merge_equiv.py::c1a_distinct_poison` | tx_index 1/2 均保留，PASS |

两个承载文件与本批新增 `test_sqd_collector_meta_v4.py`、扩充的
`test_sqd_consumer_v4.py` 均在 `run_all.py` 的硬编码 `SUITE` 中；T4 oracle 明确不在 SUITE。

## 8. 最终 SUITE

首轮沙箱内全量运行出现 5 项失败：两项纵切片因 `socket.bind(127.0.0.1)` 被环境 EPERM 阻断；
另三项是 T2 严格归属校验发现的旧 fixture 缺字段。后者已由 `ef6117d` 修复并定向全绿；前者在
获准允许本机 loopback 夹具监听后重跑，不再有环境失败。

最终执行：

```text
python3 scripts/tests/run_all.py
```

结果：

```text
120/120 PASS
invariant_scan.py PASS
test_batch3_solana_vertical_slice.py PASS
test_batch3_evm_vertical_slice.py PASS
全部通过
exit 0
```

版本一致性测试仍报告 `6.48.1`；本批没有修改 VERSION/CHANGELOG。

## 9. 六视角①字段来源自审

- **边内容**：摘要只来自 `merger.finalize()` 后的最终 gz 实际逐行重读，不信 merger 自报摘要。
- **格式身份**：采集与 replay 都严格验证 v4 七元组，摘要算法不靠行宽猜测或调用者声明。
- **producer 身份**：collector ID、script path、protocol、hash、status 分账校验；hash 来自干净
  git object，不来自当前工作树。
- **窗口与计数**：meta 的 `edge_rows` 同时受最终遍历计数、merger 计数和消费侧重算约束。
- **逻辑与物理绑定**：逻辑摘要防规范化内容漂移；既有 size/sha256 继续绑定物理边文件。
- **oracle 身份**：ARC oracle 自己实现解析/合并，不复用被验生产 merger；两条实现路径再互证。

## 10. 六视角②失败分支自审

- 最终 gz 为空、坏 JSON、非 7 元组、字段类型非法、非正金额：采集成功 meta 不发布。
- merger 行数与最终重读行数不等：采集器拒绝 finalize 成功状态。
- meta 摘要与 replay 重算不一致：replay 拒绝；篡改一行反例已锁定。
- collector ID 错、hash 未登记、script/protocol 错配或 hash-wide REVOKED：replay/camp 均拒绝。
- 登记 dirty hash：流程上被“先 commit、后 git show 登记”禁止，测试再用 git object 验证条目。
- invariant code/manifest 任一增删漂移：`invariant_scan.py` 阻断收批。
- ARC parts 缺失、symlink、清单字段不符、区间重叠、双路径字节不等或前后哈希变化：oracle FAIL。
- 既有 fixture 因新 guard 断裂：只修 fixture 的正式 provenance，不放松生产校验。

## 11. commit 台账（不含本文件交付 commit）

```text
7fb89df 批4：收编采集摘要与登记守卫工单
ed1ec93 批4 T1：固化采集侧逻辑摘要红态反例
75aa622 批4 T1：采集成功元数据绑定逻辑边摘要
26f99cb 批4 T2：固化Solana采集器冒名红态反例
b9e02f3 批4 T2：登记Solana生产者并校验采集归属
fbe2160 批4 T3：按机器清点清零不变量登记差异
e688f20 批4 T4：固化ARC parts独立只读oracle
ef6117d 批4 T5：同步既有正式夹具的采集归属
```

## 12. 禁动范围、遗留与停工

- 相对批 3 基线 `4c6720c`，`git diff -- VERSION CHANGELOG.md` 为空。
- 相对批 3 基线，`git diff --name-only -- scripts/evm` 为空；EVM 生产侧未动。
- ARC 案目录只读证明见第 6.4 节；案外只新增本仓库 oracle 工具与产物。
- 本批没有遗留业务失败、invariant 差异或未登记的新 producer。
- 工作树中另有未跟踪 `batch5_workorder.md`，它不属于本批施工产生物，未读取、未修改、未暂存。

批 4 到此停止，不启动、不施工批 5。
