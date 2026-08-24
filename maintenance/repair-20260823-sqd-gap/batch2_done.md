# 批 2 施工报告：SQD 覆盖探针（DONE）

## 结论

批 2 已按复工工单完成。开工门禁在更正后的 21 行清单上 **21/21 OK**；`sqd_coverage_probe.py`、coverage validator、共享地图生命周期、getBlocks 确认、fixture transport、E20 probe 半边与离线回归均已落地。

批 1b 的 probe 五项红证 `(3)(20)(21)(28)(30)` 已全部转绿，probe 测试为 **9/9 PASS**。最终 `run_all.py` 为 **120 PASS / 4 FAIL**；四项均是工单指定的后续登记缺口或沙箱回环 `EPERM`，没有本批回归。完整证据见 `batch2_green_evidence.txt`。

基线保持：分支 `fix/sqd-gap-v6520`，HEAD `733c4aed0eb18364f4c2a6a2dc98772ae68db422`，`VERSION=6.51.0`。未 commit、未切分支、未联网。

## 交付内容

### 覆盖探针

新增 `scripts/solana/sqd_coverage_probe.py`：

- 生产 `sqd-solana-coverage/v1` 与 `sqd-solana-coverage-pointer/v1`；产物位于 `<case-root>/data/sqd_coverage/<probe_id>/`，指针为 `CURRENT.json`。
- SQD 查询固定为 `includeAllBlocks:true`、System Program、AdvanceNonce `d4=0x04000000`，按约 450 slot 分页；并行任务区间互不重叠。
- u8 逐 slot 计数为 `0=UNSCANNED, 1=NO_HEADER, 2=HEADER_ZERO_NONCE, n>=3 => nonce_count=n-2`，255 饱和。
- 四态、三值 verdict、候选排序去重和 E8 时代校准均采用整数交叉相乘；没有游程阈值判定。
- getBlocks 先取 finalized head，再按不超过 500,000 slot 分段；记录逐段六项事实并生成 u1 位图。`complete` 不落盘，由 validator 按八项合取式重算。
- SQD 未扫完保持 UNSCANNED、不发布 CURRENT、exit 2；`--resume` 只补缺口。
- getSlot/getBlocks 的 402/429 或 Helius 配额错误第一次确定后停止派发，落 `STOPPED.json`，exit 3；`--resume` 延续同一 pending 身份。
- 默认只从 `~/.config/helius/api-key` 读取 key；`--reference-rpc` 可覆盖，不降级公共 RPC。错误、URL、ledger 和控制台文本统一脱敏。
- 隐藏的 `--transport-fixture` 仅替换传输层，请求按摘要读 fixture，发布协议和产物语义不变；E20 纵切片真实 subprocess 使用该入口。
- `--dry-run` 不创建案目录或产物，只报告 slot 数、最坏/乐观请求数和地图复用计划。

### 共享地图生命周期

探针的 `--known-map` 实现了以下 fail-closed 复用门：

- `ttl_days=30` 未过期；
- `sqd.metadata_normalized` 与 endpoint fingerprint 相等；
- companion counts/blocks 的路径、长度与 SHA-256 有效；
- 已知 candidate/refuted slot 全部逐 slot recheck；
- 恰好 64 个 canary slot 与 counts 逐值相等。

通过时写 `map-reuse`，地图外/新增区间写 `full`，复核写 `recheck`；失败时记录 `shared_map.fallback_reason` 并升级全扫。`sample_ranges` 只作附加证据，不进入 formal 覆盖并集。目录契约说明新增于 `assets/sqd-solana-coverage-map/README.md`；本批未放首版共享数据。

### 发布协议与原子性

实现了 `pending-<scan_id>` 写齐、逐文件 fsync、pending 目录 fsync、rename 为不可变 `<probe_id>`、父目录 fsync、`.lock` 独占、锁内 CAS、kernel 覆盖写 CURRENT、锁内指针父目录 fsync。

`probe_id` 由去掉自身字段后的 coverage map 规范化内容重算。同 probe_id 且同哈希为 `idempotent-republish`，只补 fsync；CAS 失败保留已发布 generation 并拒绝改 CURRENT。发布前后均调用独立 coverage validator 自验。

### Coverage validator

新增 `scripts/lib/solana_exact_validate.py`，文件顶部分明标注 coverage（批 2）、repair（批 3）、reconcile（批 5）；本批只实现 coverage 段，未 import `replay_edges` 或 `sqd_repair_core`。

纯函数入口 `validate_coverage(case_root, coverage_path, pointer_path, case_from_slot, case_to_slot)` 返回 `{ok, reasons, recomputed}`，重算并拒绝：

- 浮点规范化、probe_id、producer/hash、SQD metadata/hash；
- 四态、时代、candidate_slots 和有效 verdict；
- UNSCANNED、解压长度错误、ledger 成功并集有洞/不等 scan_ranges/不覆盖案区间；
- getBlocks 八项合取式、位图长度/popcount/范围；
- pointer 条件 inputs、路径逃逸/软链、文件 size/hash、target/envelope；
- `supersedes` 链断裂、循环或不可追溯。

### 网络结果、守卫与 E20

- `scripts/lib/net.py` 的错误负载增加 `http_status:int|null`、`retryable:bool`，新增 `no_retry_statuses=()`；默认重试行为不变，错误文本在本层脱敏。
- `scripts/hooks/guard_file_ops.py` 登记 `/data/sqd_coverage/` 规范件、指针、锁和 pending 生命周期文件，沿用现役 producer-only 写守卫。
- `scripts/tests/invariant_manifest.json` 将 probe/coverage validator 的 locator、schema 和语义核对到实际实现，未删除批 1b 的后续批次登记。
- `scripts/tests/test_batch3_solana_vertical_slice.py` 在注册 target 的可达闭包中，以字面脚本路径真实 subprocess 执行 fixture probe 并检查四件产物与 CURRENT。AST 结果已由 `['replay_edges.py', 'sqd_coverage_probe.py']` 收窄为仅 `['replay_edges.py']`。

## 白名单改动清单

| 文件 | 改动 |
|---|---|
| `scripts/solana/sqd_coverage_probe.py` | 新增覆盖生产者、CLI、fixture transport、共享地图与发布生命周期 |
| `scripts/lib/solana_exact_validate.py` | 新增独立 coverage validator；repair/reconcile 段仅保留批次边界注释 |
| `scripts/lib/net.py` | HTTP 状态、retryable、no_retry_statuses 与错误脱敏 |
| `scripts/hooks/guard_file_ops.py` | 增加 sqd_coverage 规范件写守卫 |
| `assets/sqd-solana-coverage-map/README.md` | 共享资产 schema、伴随文件、TTL/supersedes/canary 说明 |
| `scripts/tests/test_sqd_coverage_probe.py` | 五项红转绿及九组离线协议测试 |
| `scripts/tests/test_net_result.py` | net 新字段、默认重试、402 不重试与脱敏断言 |
| `scripts/tests/fixtures/sqd_coverage/{happy,quota,resume_fail}/responses.json` | 2,362 bytes 离线请求摘要 fixture |
| `scripts/tests/invariant_manifest.json` | locator/semantics/schema 与实际实现对齐 |
| `scripts/tests/test_batch3_solana_vertical_slice.py` | E20 probe formal subprocess 证据 |
| `maintenance/repair-20260823-sqd-gap/batch2_green_evidence.txt` | 红绿对照、终态测试与全量 suite 输出 |
| `maintenance/repair-20260823-sqd-gap/batch2_done.md` | 本报告 |

工作区另有复工前/施工中由用户侧提供的 `batch2_done_attempt1_stopped.md` 与 `batch3_workorder.md`，本批未修改。

## 验证结果

- staging SHA-256 门禁：21/21 OK。
- `test_sqd_coverage_probe.py`：9/9 PASS；五项红证全部转绿。
- `test_net_result.py`：PASS。
- `test_contract_routes.py`：PASS。
- 六个本批 Python 文件 `py_compile`：PASS。
- fixture 总大小：2,362 bytes，小于 200 KB。
- `formal_e2e_provenance_errors()`：仅剩 `scripts/solana/replay_edges.py`。
- `run_all.py`：120 PASS / 4 FAIL。

### run_all 四项逐条解释

1. `invariant_scan.py`：**预期先红（登记缺口）**，20 项已降为 16 项。剩余均指向批 3 repair、批 5 replay/reconcile、wave v5、flow v3 或对应 future consumer/registry；probe 和 coverage validator 的登记已闭合。
2. `test_batch3_solana_vertical_slice.py`：**沙箱环境红**。本批新增的 fixture probe 在回环监听之前已真实 subprocess 成功；随后既有 `ThreadingHTTPServer` bind 因 `PermissionError: [Errno 1] Operation not permitted` 失败。
3. `test_batch3_evm_vertical_slice.py`：**沙箱环境红**。同一既有回环 bind EPERM，与本批无关。
4. `test_batch4_invariant_guards.py:198`：**预期 E20 红**。probe 半边已闭合，只剩 `replay_edges.py`，按工单留待批 5。

批 1b 另外三份测试继续以 repair/reconcile 缺口先红，逐项输出已收入绿证，没有被删项或伪绿。

## Fable 本机联网冒烟建议

下列命令应在有 `~/.config/helius/api-key` 且可联网的 Fable 本机执行；每个 case-root 使用独立新目录。ARC mint 为 `61V8vBaqAGMpgDQi4JcAwo1dmBGHsyhzodcPqnEVpump`。

```bash
# 1. ARC 已知缺陷区段
python3 scripts/solana/sqd_coverage_probe.py \
  --mint 61V8vBaqAGMpgDQi4JcAwo1dmBGHsyhzodcPqnEVpump \
  --case-root /ABS/PATH/arc-coverage-defect \
  --from-slot 426649000 --to-slot 426670000 --full --workers 4

# 2. 健康区段 439,000,000 ± 1,000
python3 scripts/solana/sqd_coverage_probe.py \
  --mint 61V8vBaqAGMpgDQi4JcAwo1dmBGHsyhzodcPqnEVpump \
  --case-root /ABS/PATH/arc-coverage-healthy \
  --from-slot 438999000 --to-slot 439001000 --full --workers 4

# 3. 含 NO_HEADER 的小区段（staging 采样显示 426665000 无 header）
python3 scripts/solana/sqd_coverage_probe.py \
  --mint 61V8vBaqAGMpgDQi4JcAwo1dmBGHsyhzodcPqnEVpump \
  --case-root /ABS/PATH/arc-coverage-no-header \
  --from-slot 426664500 --to-slot 426665500 --full --workers 4
```

若收到 exit 2 或 3，在同一命令末尾加 `--resume`；不要换 case-root。冒烟后对 defect 区间将 `slot_counts.bin.gz` 解压成逐 slot u8，与 `.staging_b2/arc_reference/sqd_query_variants/dense_map_final.json` 逐 slot 比对，并运行独立 validator：

```bash
python3 - <<'PY'
import json
from pathlib import Path
from scripts.lib.solana_exact_validate import validate_coverage

case = Path('/ABS/PATH/arc-coverage-defect').resolve()
pointer_path = case / 'data/sqd_coverage/CURRENT.json'
pointer = json.loads(pointer_path.read_text())
coverage_path = case / 'data/sqd_coverage' / pointer['probe_id'] / 'coverage_map.json'
print(json.dumps(validate_coverage(
    case, coverage_path, pointer_path, 426649000, 426670000),
    ensure_ascii=False, indent=2, sort_keys=True))
PY
```

全史扫描先 dry-run，再启动新案；首次运行不加 `--resume`，中断/配额停工后原命令追加 `--resume`：

```bash
python3 scripts/solana/sqd_coverage_probe.py \
  --mint 61V8vBaqAGMpgDQi4JcAwo1dmBGHsyhzodcPqnEVpump \
  --case-root /ABS/PATH/arc-coverage-full \
  --from-slot 306451717 --to-slot 440368381 --full --workers 4 --dry-run

python3 scripts/solana/sqd_coverage_probe.py \
  --mint 61V8vBaqAGMpgDQi4JcAwo1dmBGHsyhzodcPqnEVpump \
  --case-root /ABS/PATH/arc-coverage-full \
  --from-slot 306451717 --to-slot 440368381 --full --workers 4
```

全扫验收并由独立 validator 通过后，再按 `assets/sqd-solana-coverage-map/README.md` 生成首版共享地图三件套；本批没有预置或伪造数据资产。

## 停止线

批 2 到此完成并停止。未触碰 `fetch_sqd_transfers_v2.py`、`replay_edges.py`、`spl_edge_core.py`、`producer_history.py`、`run_all.py`、版本文件、CHANGELOG、SKILL、PLAN/errata/契约草案或 references；未施工批 3 repair、批 5 reconcile，未 commit。
