# 批 3 施工报告：SQD gap repair 生产与发布协议（未闭合）

## 结论

批 3 已在 `fix/sqd-gap-v6520`、`HEAD=4046690` 上完成白名单内的主要生产、
resolver、validator、离线缓存与 shared-map 代码。定向测试中
`test_sqd_gap_repair.py` 与 `test_sqd_coverage_probe.py` 全绿，
`test_reconcile_v4_receipt.py` 的本批项 (17) 已由红转绿；全套为
`120/124 PASS`，四个失败均是工单明确允许的后续缺口或沙箱回环 EPERM。

但协议逐条复核发现 β、前置一致性、STOPPED/resume 三项没有被当前冻结契约提供
足够输入，也没有被当前实现完整闭合，详见“发现项”第 6–8 项。因此本报告不能把
批 3 判为完成；测试全绿只证明已覆盖的机械路径，不等于工单全文验收通过。

本批没有改动 `fetch_sqd_transfers_v2.py`、`replay_edges.py`、批 4/5 消费端、
`producer_history.py`、`run_all.py`、版本文件、references、PLAN/errata 或契约草案，
没有切分支、联网或提交 commit。

## 改动清单

### 生产与纯函数核

- `scripts/solana/sqd_repair_core.py`（新）：
  `canonical_json`、`compute_plan_digest`、`compute_gid`、签名差集、vote/nonce
  判定、缺失分类、owner delta 产边、slot 双射、base 重映射、确定性合并、
  logical evidence、routeA cache 解析。
- `scripts/solana/sqd_gap_repair.py`（新）：
  `plan|repair|verify`，fixture/live transport，`--blocks-cache` exploration，
  resolution/layer/map/evidence/merged cache/bundle/rpc_ledger，配额 STOPPED，
  resume、不可变代发布、CURRENT CAS、E10 幂等、深验和可选 live canary。
- `scripts/solana/spl_edge_core.py`：新增 `sqd_repair_paths`；原有产边语义不改。

### resolver、身份闸与独立 validator

- `scripts/solana/sqd_cache_identity.py`：
  `validate_repair_bundle`、`validate_cache_meta_v2`、repaired-meta 校验、
  `resolve_formal_cache`；有 CURRENT 时 fail-closed，不向 base 静默回落，忽略
  pending/无指针孤儿代。
- `scripts/lib/solana_exact_validate.py`：
  独立重建 shared map、repair pointer/bundle、resolution、layer、slot map、
  evidence、merged cache、gid/plan_digest/file refs；支持 `verify --live-canary N`
  的参考块 hash 与签名序列抽检。
- `scripts/solana/sqd_coverage_probe.py`：新增 `export-shared-map`，从已发布且
  CURRENT 匹配的 probe 确定性导出 JSON/counts/blocks 三件套。

### 守卫、manifest、测试与 fixture

- `scripts/hooks/guard_file_ops.py`：纳入 repair 正式产物路径守卫。
- `scripts/tests/invariant_manifest.json`：登记本批 producer/consumer/transport/
  atomic/formal surface；不替批 4 补 replay 半边。
- `scripts/tests/test_sqd_gap_repair.py`：本批 RED 项转 GREEN，并覆盖规范化、
  gid/E17、routeA 样本真值、原始 SQD `transactionIndex` 保留、映射/合并、
  CAS/幂等、exploration/formal、mock transport、`--blocks-cache` 深验和不发指针。
- `scripts/tests/test_sqd_coverage_probe.py`：第 12 组 shared-map 导出、确定性、
  独立复验与篡改拒绝。
- `scripts/tests/test_reconcile_v4_receipt.py`：(17) 改为 GREEN 断言。
- `scripts/tests/fixtures/sqd_repair/vectors.json`：规范化/gid/plan_digest 小向量。

## 协议落地对照

| 权威条款 | 落地 |
|---|---|
| 4.2.0 规范化 | 递归 canonical JSON；key 排序；整数限定；拒绝 float、非法数字 key 与字符串金额；plan/gid 均复算。 |
| 4.2.0 `plan_digest` | 绑定 base、coverage、候选、mode、reference fingerprint 与 producer；resume 以同 digest 识别 pending。 |
| 4.2.0 `gid` | 去除自引用字段，绑定 plan、mode、supersedes、resolution/layer/map/evidence；validator 独立复算。 |
| 4.2.3 九步发布 | pending 建立 → 证据/层/映射/merged → ledger 定稿 fsync → gid → bundle → pending 目录 fsync → exclusive rename 为 immutable gen → 深验 → CURRENT CAS；代目录、父目录、指针父目录均耐久化。 |
| 4.2.3 CAS/崩溃恢复 | 锁内比较 expected CURRENT/supersedes；旧 immutable gen 可恢复；pending 与无指针 orphan 不被 resolver 接纳。 |
| 4.2.4 resolution | census 按 slot 唯一排序，机械派生 `INCONCLUSIVE` / `DEFECTS_CONFIRMED` / `NO_KNOWN_NONCE_OMISSION_DETECTED`；formal 必须由 confirmed evidence 支撑。 |
| 4.2.7 映射 | SQD `(index,signature)` 与参考 `(position,signature,isVote)` 建双射，统一到非投票序号；缺陷 slot base 边必须恰一解。 |
| 4.2.10 rpc_ledger | header 后逐请求记录 seq/ts/method/params digest/slot/fingerprint/status/bytes/credits/result digest/attempt；配额首命中写 STOPPED。 |
| E10 幂等 | 同 gid 且同 bundle hash 的补发返回 `idempotent-republish`；不同内容碰撞、CURRENT 漂移均硬错。 |
| E17 | `rpc_ledger` 绑定 plan，但明确不进入 gid；改变台账不改变内容代身份，validator 仍独立验 ledger schema/ref。 |

## 红到绿

- `test_sqd_gap_repair.py`：
  (2)(4)(5)(6)(7)(8)(10)(15)(16)(18)(25)(26)(27)(29a)(29b)(29c)
  全部从 `batch1b_red_evidence.txt` 的 RED 转为 GREEN。
- `test_reconcile_v4_receipt.py`：(17) 从“正式路径外复制 meta 被接受”转为
  `validate_cache_meta_v2` fail-closed GREEN。
- `test_sqd_coverage_probe.py`：12/12；增补的 export-shared-map 组通过。
- 完整命令、退出码与允许红说明见 `batch3_green_evidence.txt`。

## 发现项

1. `invariant_scan.py` 仍有 10 个显式缺口：wave v5、flow v3、reconcile v4、
   validator reconcile 段及 replay 正式 E2E/失败产物注册半边。这是批 4/5 范围，
   本批按硬纪律只记录，未越界修正。
2. 新 formal generation 的 producer-history 正式登记必须在后续 closing commit 完成；
   本批按禁改清单未动 `producer_history.py`。因此 resolver 对“未登记生产者”的正式代
   继续 fail-closed；mock 测试只证明生产/发布机械闭环，不等于完成发布登记。
3. 沙箱禁止 loopback bind，Solana/EVM 两个 vertical-slice 测试均为
   `PermissionError: [Errno 1] Operation not permitted`；不是本批代码失败。
4. E21/E22（含 shared map `refuted_slots` 规则）仍待裁决；首版导出按增补要求固定
   `refuted_slots: []`，未自行扩张语义。
5. 当前沙箱只以 staging 原始样本与 mock transport 验证，未宣称完成 ARC 的
   6,759 块/83 边 Fable 机器验收；该验收必须按下节命令在持有全缓存的本机执行。
6. 工单要求 `--residual-owners` 在生产者内执行通用 β 余额连续性二分，但冻结的
   contracts/scan-schema 没有定义该文件的结构，仓库也没有“residual owner → token
   account → 初始余额/活动边集合”的标准产物。当前实现只从该文件提取已定位的
   `candidate_slots`/slot 字段并纳入 α；没有凭空发明 owner/account schema，也没有把
   ARC 的两个硬编码账户带进生产代码。因此“每 owner ≤40 次 SQD tokenBalances 二分、
   ±64 指纹、≤3 轮残差趋势”尚未闭合。这是本批实质未完成项。
7. 工单要求比较“coverage 阶段与 repair 阶段 SQD 签名集哈希”，但冻结的
   `sqd-solana-coverage/v1` 只保存 nonce slot counts/bitmap/ledger，不保存逐候选 slot
   的全交易签名集或其 hash；当前 repair 只能保存并核对 repair 当次的 SQD census，
   独立 validator 无法重建跨阶段等值关系。若不先裁定由哪个产物承载该 hash，直接加
   字段会违反“契约草案/scan-schemas 不动”的硬纪律。
8. 当前配额路径能在 402/429 首命中写 `STOPPED.json` 并退出 3，但 `_live_payloads`
   在抛出 `QuotaStopped` 时不会把此前已完成请求的 ledger/payload 交回 pending；
   `--resume` 也会重新请求候选，而不是按 `(plan_digest, params_digest,
   result_sha256)` 跳过已完成项。因此“在途落账＋逐请求幂等续跑”尚未闭合，现有测试
   也没有工单要求的 STOPPED/resume/崩溃三段故障注入。该项必须先红后绿补做。
9. coverage resolution 冻结 schema 没有持久化 plan 的完整 candidate set；独立
   validator 可从 coverage map 重建 coverage candidates，却不能从 plan_digest
   反推出额外 β candidates。当前 producer 会在进程内检查候选全归宿，但离线 verifier
   对 β 候选的完整性缺少独立证据。这与第 6 项同属契约承载缺口，未猜测扩 schema。

## Fable 本机复验建议

以下从本仓库根目录运行。先核对三处 cache 合计必须是 6,759 个块文件：

```bash
ARC="/Users/uravvv/Documents/5.6筹码分析/ARC分析"
MINT="61V8vBaqAGMpgDQi4JcAwo1dmBGHsyhzodcPqnEVpump"
PILOT="$ARC/diagnosis_20260823/routeA_pilot/blocks"
FULL="$ARC/diagnosis_20260823/routeA_full/blocks"
HUNT="$ARC/diagnosis_20260823/routeA_full/hunt_remaining/blocks"
find "$PILOT" "$FULL" "$HUNT" -type f \( -name '*.json' -o -name '*.json.gz' \) | wc -l
```

产 exploration 代（可重复 `--blocks-cache`，不会发布 CURRENT）：

```bash
OUT=$(python3 scripts/solana/sqd_gap_repair.py repair \
  --mint "$MINT" --case-root "$ARC" \
  --blocks-cache "$PILOT" --blocks-cache "$FULL" --blocks-cache "$HUNT")
printf '%s\n' "$OUT"
GID=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["gid"])' <<<"$OUT")
GEN="$ARC/data/sqd_repair/$MINT/gen-$GID"
python3 scripts/solana/sqd_gap_repair.py verify "$GID" \
  --mint "$MINT" --case-root "$ARC"
```

把 generation 的 repair layer 与三份冻结真值逐边比较，并核对 83/83 与 merged
行数恒等式：

```bash
python3 - "$GEN" \
  "$ARC/diagnosis_20260823/routeA_pilot/repair_edges_pilot.jsonl" \
  "$ARC/diagnosis_20260823/routeA_full/repair_edges_full.jsonl" \
  "$ARC/diagnosis_20260823/routeA_full/hunt_remaining/repair_edges_hunt.jsonl" <<'PY'
import collections, json, pathlib, sys
gen = pathlib.Path(sys.argv[1])
rows = [json.loads(x) for x in (gen / "repair_layer.jsonl").read_text().splitlines() if x]
actual = [tuple(edge) for row in rows[1:] for edge in row["edges"]]
truth = []
for name in sys.argv[2:]:
    truth += [tuple(json.loads(x)["edge"]) for x in pathlib.Path(name).read_text().splitlines() if x]
assert len(truth) == 83, len(truth)
assert collections.Counter(actual) == collections.Counter(truth), (len(actual), len(truth))
bundle = json.loads((gen / "bundle.json").read_text())
assert bundle["merged"]["edge_rows"] == bundle["base"]["edge_rows"] + len(actual)
print("PASS: 83/83 edges; merged row identity; deep verify PASS")
PY
```

对 ARC 已发布全扫 probe 导出首版 shared map（显式 version 使输出可重放）：

```bash
PROBE_ID=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["probe_id"])' \
  "$ARC/data/sqd_coverage/CURRENT.json")
python3 scripts/solana/sqd_coverage_probe.py export-shared-map \
  --case-root "$ARC" --probe-id "$PROBE_ID" \
  --out assets/sqd-solana-coverage-map --version 20260823
python3 scripts/solana/sqd_coverage_probe.py export-shared-map \
  --case-root "$ARC" --probe-id "$PROBE_ID" \
  --out assets/sqd-solana-coverage-map --version 20260823
```

第二次导出必须是字节幂等；再运行 `test_sqd_coverage_probe.py` 的第 12 组逻辑或
独立 `validate_shared_map` 校验 JSON 与两个二进制 hash/range/encoding/canary。
