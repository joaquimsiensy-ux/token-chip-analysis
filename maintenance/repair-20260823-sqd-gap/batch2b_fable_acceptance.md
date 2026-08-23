# 批 2 ＋ 2b Fable 验收记录（2026-08-23）

## 结论
**批 2（探针＋coverage validator＋net.py 结构化状态＋guard）与批 2b（SQD 游标分页返工）验收 PASS，可 commit。**
codex 自报不作数，以下全部为 Fable 本机独立复跑。

## 1. 离线
- `python3 scripts/tests/test_sqd_coverage_probe.py` → 10/10 PASS（含批 2b 新增：分页截断 B2B-PAGE-01 先红后绿、空响应、越界/乱序/重复页 fail-closed、并发分片游标）。
- `git diff --check` 干净；三文件 `py_compile` 通过。
- `run_all.py`：120 PASS / 4 FAIL，与批 2 汇报一致；4 红＝invariant_scan 对批 3–5 未交付件的"先红登记"（wave v5/flow v3/reconcile v4/validator reconcile 段/sqd_gap_repair 四协议/sqd_cache_identity 消费点）＋ `test_batch4_invariant_guards.py:198`（E20 replay 半边）＋两个回环监听 EPERM（本机沙箱既有）。无新增回归。

## 2. 联网冒烟（三段，新案根 `scratchpad/probe_smoke_b2b/{defect,healthy,noheader}`）
| 段 | 区间 | slots | healthy | no_header | zero_nonce | verdict | validator | SQD 页数 | 续页 | 游标违规 | SQD 块头数 vs getBlocks 链上块数 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 缺陷 | 426,649,000–426,670,000 | 21,001 | 15,995 | 143（全部 SKIPPED_CONFIRMED） | 4,863（全 ERA_UNCERTAIN） | INCONCLUSIVE | ok | 94 | 47 | 0 | 20,858 == 20,858 |
| 健康 | 438,999,000–439,001,000 | 2,001 | 1,997 | 4（确认跳块） | 0 | NO_KNOWN_NONCE_OMISSION_DETECTED | ok | 8 | 3 | 0 | 1,997 == 1,997 |
| 跳块 | 426,664,500–426,665,500 | 1,001 | 631 | 12（确认跳块） | 358（ERA_UNCERTAIN） | INCONCLUSIVE | ok | 5 | 2 | 0 | 989 == 989 |

- 批 2 首版的 6,079 个假 NO_HEADER（分页截断误判）已消失；三段 **SQD 块头数恰等于 getBlocks 链上块数**，NO_HEADER 与真跳块完全重合；ledger `seq` 连续、每个续页 `from == 上一页 returned_to+1`、页覆盖并集＝案区间、`empty_response_count=0`。
- 每页实际 `slots_covered` 最大 387（<450 经验上界），证明游标续页确有必要。

## 3. 与路 A 逐块真值交叉表（缺陷段，4,774 个路 A 拉过的 slot）
| 探针状态 | 路 A | 数量 |
|---|---|---|
| NO_HEADER | status=SKIPPED（sqd_tx=0） | 61 |
| ZERO_NONCE | sqd_tx>0 且 missing_nonce>0（缺陷） | 4,710 |
| ZERO_NONCE | sqd_tx=0 且 missing_nonce=0（链上纯投票块） | 3 |
| **(NO_HEADER, sqd_tx>0)** | — | **0** |
| **(HEALTHY, missing_nonce>0)** | — | **0** |

## 4. 新发现（重要，影响 ARC 收尾与计划假设）
### 4.1 稠密地图漏掉的"微缺陷段"
探针在缺陷段内另找到 **150 个路 A 未覆盖的 ZERO_NONCE slot，成 27 个游程，长度几乎全是 5/10/15（像 SQD 入库分块粒度）**，均不贴着已知 38 段。实测：SQD 免费普查三个游程（426651583–601 共 19 块、426649073–077、426668663–677）每块 500–1,000 笔交易但零 AdvanceNonce；Helius getBlock 对照 426651590：链上 83 笔 nonce 交易（40 笔成功）、426649075：74 笔（40 成功）→ **SQD 里都是 0 ⇒ 真缺陷**。结论：老稠密地图（游程阈值法）不完整，"缺陷可短至 1 slot"成立；ARC 在这些微段里有无交易要靠批 3 逐 slot 普查（α）。
### 4.2 健康期的"单块零 nonce"候选是良性的、但普查要花钱
420,000,000–420,049,999（健康期 5 万 slot）：26 个单块/短游程零 nonce（0.05%），时代校准有效 → 全部 DEFECT_CANDIDATE。SQD 普查：17 个块 SQD 内非投票交易＝0、6 个 1–50 笔、3 个 58/107/203 笔。Helius 对照 3 个：420008956 链上非投票 203 笔＝SQD 203、零 nonce；420047316 107＝107、零 nonce；420003646 纯投票块 → **全部良性（薄块/纯投票块本来就没 nonce），普查会 refuted**。
成本推论：按 0.05% 外推全史 1.34 亿 slot ≈ **6.7 万个良性候选 × 10 credits ≈ 67 万 credits** 只为驳回——计划 §4.6 的"≈68k credits"只算了已知缺陷块，没算这一项。→ 决策点 E22。
### 4.3 时代校准阈值与缺陷密度耦合
缺陷段窗口比率 0.77（4,863/20,858）→ 全部 ERA_UNCERTAIN。按 100 万 slot 桶算时，若某桶缺陷密度 >1%（已知 38 段＋微段集中在 06-13/15/16 三天≈桶 426–427，有可能超过），该桶全部缺陷被判 ERA_UNCERTAIN → 按计划文本 INCONCLUSIVE ⇒ FAIL，且 α 只普查 DEFECT_CANDIDATE ⇒ 越缺越修不了。→ 决策点 E21（ARC 全扫的逐桶统计出来后报用户拍板）。

## 5. 吞吐标定（ARC 全扫工期）
5 万 slot、`--no-getblocks`：8 线程 57 s、16 线程 29 s（≈1,724 slot/s，近线性）→ 1.34 亿 slot ≈ **21.6 小时**（16 线程）。探针目前只在整趟结束/配额停工时写 `resume_state.json`，中途被杀全丢 → 开跑前补定期检查点（批 2c）。

## 6. 外部额度台账（本次验收）
Helius getBlock ×5（426651590、426649075、420008956、420047316、420003646）≈ 50 credits；SQD 免费请求 ≈ 420 次（三段冒烟 107 页＋标定 240 页＋普查 ~70 次）。key 经 stdin 传 curl，未进命令行/日志/产物。

## 7. 遗留/交接
- 批 2c：定期 resume 检查点（见工单）。
- 批 3 工单补第 10 条：探针 `export-shared-map`（共享地图资产导出）。
- E21/E22 记入 errata 标"待用户裁决"，ARC 全扫结束后连同逐桶统计一起报。
- 冒烟产物（含 probe 发布目录）留在 scratchpad，不入库。
