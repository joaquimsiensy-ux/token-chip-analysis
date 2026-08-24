# 批 2b 返工报告：SQD 游标分页（DONE）

## 结论

Fable 联网冒烟发现的分页截断误判已修复。旧实现把单次响应未返回的请求尾部直接写成 NO_HEADER；新实现只提交到本页最后返回块 `L`，再从 `L+1` 继续请求同一分片，直至覆盖分片终点。HTTP 200 空数组是唯一允许一次覆盖剩余请求尾部的情形，并显式写 `empty_response:true`。

修复前反例稳定得到错误 counts `[1,2,1,1]`；修复后同一 fixture 得到 `[1,2,4,3]`，两页实际覆盖无洞。分页/空响应/越界/乱序/重复/并发分片/validator/不发布门禁均已离线回归，probe suite 为 **10/10 PASS**。

基线保持：分支 `fix/sqd-gap-v6520`，HEAD `733c4aed0eb18364f4c2a6a2dc98772ae68db422`，`VERSION=6.51.0`。未 commit、未切分支、未联网。

## 根因与修复

### 旧行为

`_scan_request(start,end)` 只调用一次 SQD stream，预先把整个 `[start,end]` 初始化为 NO_HEADER，并把 `slots_covered` 固定写成 `end-start+1`。SQD 响应若在 `L<end` 截断，`L+1..end` 虽未取回，也被提交成 NO_HEADER。

这与 Fable 反例完全一致：第一响应截断在约 426,649,372，后续实际存在的块头被误判；getBlocks 因而把大量假 NO_HEADER 升为 missing-block candidate。

### 新行为

- `_scan_request(cur,end)` 校验返回块号严格递增唯一且全部位于 `[cur,end]`。
- 非空页令 `L=returned_to`，只生成长度 `L-cur+1` 的 counts；其中出现的块按 nonce 计数，未出现的 slot 才是 NO_HEADER。
- `_scan_partition` 在同一 worker 内把游标推进到 `L+1`，重复请求至分片末端；每个约 450-slot 调度分片独立推进，不共享游标。
- HTTP 200 空数组覆盖 `[cur,end]`，全部写 NO_HEADER，同时记录 `empty_response:true`、`returned_from/to:null`、`n_blocks:0`。
- 越界、乱序或重复块号使该页 `ok:false`、`slots_covered:0`，不提交该页 counts；剩余 slot 保持 UNSCANNED，最终 exit 2 且不发布 CURRENT。
- 并发结果按分片起点、页内游标排序后落 ledger，seq 仍为全局零基连续序号。

## Ledger 与 validator

每个 SQD 页现在记录：

`seq, ts, provider, mode, query_body_sha256, from, to, returned_from, returned_to, n_blocks, slots_covered, empty_response, http_status, bytes, response_sha256, ok`。

其中 `to` 是请求的分片终点，不再被当成实际覆盖终点。producer 和 `validate_coverage` 均按：

```text
[from, from + slots_covered - 1]
```

重算成功覆盖并集。validator 还检查：

- `slots_covered` 为正整数且不越过请求 `to`；
- 非空页 `returned_to == from+slots_covered-1`，returned facts 与 n_blocks 类型有效；
- 空页必须覆盖请求尾部，returned facts 为 null/0；
- `recomputed.empty_response_count` 单列成功空页数；
- 实际 ledger 并集必须无洞、等于 scan_ranges，并覆盖案区间。

## Dry-run

`--dry-run` 不再把 `ceil(slots/450)` 表述为确定或最坏请求数，而输出：

- `estimated_sqd_requests_lower_bound`；
- known-map 可复用时的下界；
- `sqd_request_estimate.uncertain=true`；
- 450 是经验性每页 slot 上界假设，SQD 页可能在请求终点前截断。

## 契约与文档差异

按工单允许范围，小修：

- `contracts_draft/sqd-solana-coverage_v1.json` 增加分页 ledger 字段，冻结实际覆盖公式、非法页 fail-closed 与空响应语义；
- `contracts_draft/INDEX.json` 记录批 2b 的 Fable 反例驱动修订。

`references/scan-schemas.md` §14.1 当前只登记 coverage map 中 `ledger{path,size,sha256,requests,success_ranges_sha256}`，没有展开 ledger.jsonl 的分页字段，也仍只用“ledger 成功区间”概述并集，未写明 `[from,from+slots_covered-1]`。依工单本批只记录该差异，未修改 reference；留待批 6 统一同步。

## 红→绿证据

修复前：

```text
AssertionError: ('RED B2B-PAGE-01 truncated page tail was classified NO_HEADER',
                bytearray(b'\x01\x02\x01\x01'))
exit_code=1
```

修复后：

```text
GREEN B2B-PAGE-01 cursor follows truncated page tail
PASS SQD coverage probe: 10/10 offline groups
exit_code=0
```

完整红绿与测试输出见 `batch2b_green_evidence.txt`。

## 回归结果

- `test_sqd_coverage_probe.py`：10/10 PASS。
- 三文件 `py_compile`：PASS。
- coverage contract 与 INDEX JSON 解析：PASS。
- `test_contract_routes.py`：PASS。
- `test_net_result.py`：PASS。
- `formal_e2e_provenance_errors()`：仍仅 `scripts/solana/replay_edges.py`。
- `invariant_scan.py`：仍为批 2 已知 16 项 future 登记，无新增差异。
- 分页核心修复后的 `run_all.py`：120 PASS / 4 FAIL，与批 2 完全相同；四项仍是 invariant 16 项、两个回环监听 EPERM、E20 replay 半边。
- 全量后只补 known-map dry-run 展示字段、并发分页断言和契约 mode 描述；随后重新执行 10/10 专项、py_compile、JSON/contract route 与 `git diff --check`，均通过。
- fixture 总大小 4,440 bytes，低于 200 KB。

## 批 2b 白名单改动

| 文件 | 改动 |
|---|---|
| `scripts/solana/sqd_coverage_probe.py` | 分页游标、页级 ledger、非法页 fail-closed、实际覆盖并集、dry-run 下界 |
| `scripts/lib/solana_exact_validate.py` | 按实际覆盖重算、空响应事实校验与计数 |
| `scripts/tests/test_sqd_coverage_probe.py` | 分页截断、空响应、三类非法页、并发分片与 validator 回归 |
| `scripts/tests/fixtures/sqd_coverage/pagination/responses.json` | 两页截断 fixture |
| `scripts/tests/fixtures/sqd_coverage/empty/responses.json` | HTTP 200 空数组 fixture |
| `scripts/tests/fixtures/sqd_coverage/invalid_pages/responses.json` | 越界/乱序/重复 fixture |
| `maintenance/repair-20260823-sqd-gap/contracts_draft/sqd-solana-coverage_v1.json` | 仅 ledger 字段与对应不变量/注记 |
| `maintenance/repair-20260823-sqd-gap/contracts_draft/INDEX.json` | 仅增加批 2b ledger 修订记录 |
| `maintenance/repair-20260823-sqd-gap/batch2b_green_evidence.txt` | 红绿与回归证据 |
| `maintenance/repair-20260823-sqd-gap/batch2b_done.md` | 本报告 |

工作树中批 2 已有的其他改动保持原状；用户侧新增的 `batch2_smoke_defect_run1.out`、`batch2b_workorder.md`、`batch3_workorder.md` 及 attempt1 存档均未修改。

## Fable 本机复验建议

请用新 case-root 重跑，避免把旧错误 generation 与新结果混在同一验收目录：

```bash
python3 scripts/solana/sqd_coverage_probe.py \
  --mint 61V8vBaqAGMpgDQi4JcAwo1dmBGHsyhzodcPqnEVpump \
  --case-root /ABS/PATH/arc-coverage-defect-b2b \
  --from-slot 426649000 --to-slot 426670000 --full --workers 4

python3 scripts/solana/sqd_coverage_probe.py \
  --mint 61V8vBaqAGMpgDQi4JcAwo1dmBGHsyhzodcPqnEVpump \
  --case-root /ABS/PATH/arc-coverage-healthy-b2b \
  --from-slot 438999000 --to-slot 439001000 --full --workers 4

python3 scripts/solana/sqd_coverage_probe.py \
  --mint 61V8vBaqAGMpgDQi4JcAwo1dmBGHsyhzodcPqnEVpump \
  --case-root /ABS/PATH/arc-coverage-no-header-b2b \
  --from-slot 426664500 --to-slot 426665500 --full --workers 4
```

验收要点：

1. 缺陷区段 no_header 应回落到约 143 个真跳块加极少数例外，不应继续出现 6,079。
2. 与路 A 4,774-slot 交叉表不得再有 `(NO_HEADER, sqd_tx>0)`。
3. 对每个 SQD page，下一行 `from` 应等于上一成功非空页 `returned_to+1`；页覆盖总和应覆盖案区间。
4. 检查 `empty_response:true` 行并与 getBlocks 位图/census 对表，不把它当成未审计事实。
5. 三个 case 的 `validate_coverage(...)["ok"]` 均应为 true。

validator 调用沿用批 2 报告中的方式，把 case-root 与 slot 上下界替换为对应区段即可。

## 停止线

批 2b 到此完成并停止。未修改白名单外文件，未联网、未 commit、未施工批 3 或批 5。
