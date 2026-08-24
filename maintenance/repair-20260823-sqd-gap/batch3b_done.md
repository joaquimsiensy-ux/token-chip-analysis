# 批 3b 完工报告：E25 / E26 / E27

批 3 自报发现项 #6/#7/#8/#9 已按最高权威 errata E25–E27 落到生产者、
独立 validator、契约草案和故障注入测试。专项 repair 与 coverage 测试全绿；全仓
`run_all.py` 为 120/124 PASS，四个失败仅落在工单允许的 invariant/batch4/沙箱
回环类别。没有联网、commit 或切分支，也没有施工批 4/5。

开工与收工均核对 `fix/sqd-gap-v6520 @ c237263`。`.staging_b2` 为 21/21 OK，
`.staging_b3` 为 14/14 OK；工单锚点逐项命中。`replay_edges.py` 的现役读写代码
确认两份余额输入都是 `{owner: int}`，没有猜测 `holders_owners.json` 的键名。

## 改动点

- `scripts/solana/sqd_repair_core.py`
  - `derive_residual_owners`：以两侧 owner 并集、缺侧补 0、owner 排序，机械推导
    replay != snapshot 的残差；gate_pass=true 直接空集；支持显式子集。
  - `owner_activity`：按正式 base 边逐 slot 聚合 owner delta 并生成含当前 slot 的
    确定性重放余额序列。
- `scripts/solana/sqd_gap_repair.py`
  - `run_beta_search`：绑定三份现役输入，按 owner 做不超过 40 个余额探针，定位
    首个 mismatch 活动 slot，并对 +/-64 slot 运行 nonce 指纹；候选进入 plan。
  - 选择了对 `sqd_coverage_probe.sqd_query_body` 的只读 import；未复制、未修改探针。
  - `validate_coverage_state_consistency`、`_live_payloads`：live 下在 paid getBlock 前
    重跑同查询体，核对重算 coverage 状态；census 绑定真实响应 hash、签名差集与
    blockhash。cache exploration 明确写 null nonce recheck。
  - `load_resume_slots`、逐 slot pending 落账、残缺尾行恢复、STOPPED completed_slots、
    immutable gen 恢复和 resume CAS 漂移硬错。
- `scripts/lib/solana_exact_validate.py`
  - `validate_beta_trace`：独立核三输入 path/size/hash、残差、probe match、精确
    +/-64 window、指纹候选并集与排序。
  - `validate_repair_bundle_deep`：独立重算 coverage 状态；核 plan_candidates、
    beta trace、候选 census 全归宿、formal nonce/state/hash、ledger/evidence 三元绑定。
- `scripts/tests/test_sqd_gap_repair.py`
  - 新增 E25 E2E/篡改/子集/无残差、E26 状态漂移，以及 E27 402、残缺尾行、
    rename-CAS 崩溃、CURRENT 漂移三类故障注入红到绿。
- 契约草案
  - `sqd-solana-coverage-resolution_v1.json`：plan_candidates、coverage_state、
    sqd_nonce_count_at_repair。
  - `evidence_tables.json`：sqd-solana-beta-trace/v1 与 E26 evidence 字段。
  - `rpc_ledger.json`：completed_slots、逐 slot 落账、三元跳过及 gid 等价规则。
  - `INDEX.json`：更新 E25–E27 errata hash 与修订记录。

## E25 / E26 / E27 落地对照

| 裁定 | 落地 |
|---|---|
| E25 三输入 | `data/reconcile_receipt.json`、`replay_final_balances.json`、`holders_owners.json` 全部以案根相对 path/size/sha256 绑定。 |
| E25 残差与子集 | 两侧 owner 并集、缺侧为 0、排序；`--residual-owners` 只过滤，不再充当候选 slot 文件。 |
| E25 β 探针 | owner 活动 slot 余额连续性二分；每 owner 探针缓存且上限 40；断点精确 +/-64 nonce 指纹；`--beta-rounds` 只接受 1..3。 |
| E25 留痕 | 有残差才写 `evidence/beta_trace.json` 并进入 evidence_manifest/gid；resolution 持久化 `plan_candidates{coverage,beta}`，plan 候选是二者排序并集。 |
| E25 validator | 输入 hash、残差、probe、window、fingerprint、candidate union、resolution 与全候选 census 归宿均独立重算；一字节篡改拒收。 |
| E26 状态一致 | 每个 live 候选在 paid RPC 前以 probe 原查询体重查；状态不一致直接异常退出并保留 pending。 |
| E26 双源一致 | SQD census 保留真实 query/response hash；拟修复签名必须不在 census 签名集；SQD/参考 blockhash 必须相等。 |
| E26 离线深验 | census/evidence 的 coverage_state 必须等于 slot_counts+bitmap 重算；formal nonce 非 null 且满足状态语义；cache exploration 只允许 null。 |
| E27 在途落账 | 每个成功 slot 先 fsync SQD/ref evidence 对，再 append+fsync ledger；首个 402/429 写 STOPPED 的 cursor/plan_digest/completed_slots，退出 3。 |
| E27 resume | 仅 header plan_digest、精确 getBlock params digest、ref raw result hash、endpoint 与双 evidence slot 全部对齐才跳过；只截断未完成尾行，完整坏行硬错。 |
| E27 gid/CAS | rpc_ledger 仍不进 gid；中断续跑 gid 与一次跑通相同；rename 后孤儿 gen 可补发；CURRENT 漂移硬错不覆盖。 |

## 红到绿

生产改动前，六个机制门全部 RED：E25 beta E2E、E25 tamper、E26 state、
E27(a) quota、E27(b) crash、E27(c) CAS。改动后相同门全部 GREEN，并由真实
fixture E2E 和故障注入覆盖；完整输出见 `batch3b_green_evidence.txt`。

## 发现项

1. `invariant_scan.py` 当前为 12 discrepancy。除既有 wave/flow/reconcile/replay
   后续缺口外，新的 `sqd-solana-beta-trace/v1` 被扫描为 producer/validator schema，
   但 `scripts/tests/invariant_manifest.json` 不在批 3b 白名单。未用拆字符串方式隐藏，
   也未越界登记；留后续获准批次闭合。
2. `references/scan-schemas.md` §14 是 batch1-frozen，尚未登记 E25 的 beta trace 与
   plan_candidates、E26 的 coverage_state/repair nonce，以及 E27 STOPPED
   completed_slots；§14.8 已有三元 resume/残尾规则。依工单只记录，留批 6 更新。
3. c237263 原样的 `test_reconcile_v4_receipt.py` 仍有批 4/5 RED 9/23/12/13/31/
   33/11/32，项 (17) 为 GREEN。本批没有改 consumer 或该测试。
4. 两个 vertical-slice 测试因沙箱禁止 127.0.0.1 bind 报 EPERM；不是本批回归。
5. 本沙箱没有 ARC 的 6,759 个本机块缓存，也按纪律未联网；因此没有声称完成
   26 owner、两个已知断点或 83/83 边的 Fable 实机验收。
6. 新 producer 的正式 history 登记仍是批 3 已记录的 closing 边界；本批禁改
   `producer_history.py`，未越界处理。

## Fable 本机复验命令

以下均从仓库根运行。

### 1. ARC `plan --beta` 联网干跑

该命令只用 SQD 免费 beta/probe 查询定位候选；仍按生产入口读取本机 Helius endpoint
身份用于 plan fingerprint，但不发 paid getBlock：

```bash
ARC="/Users/uravvv/Documents/5.6筹码分析/ARC分析"
MINT="61V8vBaqAGMpgDQi4JcAwo1dmBGHsyhzodcPqnEVpump"
BETA_OUT="/private/tmp/arc-sqd-beta-plan.json"
python3 scripts/solana/sqd_gap_repair.py plan \
  --mint "$MINT" --case-root "$ARC" --beta --beta-rounds 3 >"$BETA_OUT"
python3 - "$BETA_OUT" <<'PY'
import json, sys
p = json.load(open(sys.argv[1]))
t = p["beta_trace"]
owners = [row["owner"] for row in t["residual_owners"]]
slots = t["candidate_slots"]
assert owners == sorted(set(owners)) and len(owners) == 26, len(owners)
assert p["plan_candidates"]["beta"] == slots
assert any(abs(s - 426_869_468) <= 64 for s in slots), slots
assert any(abs(s - 427_406_628) <= 64 for s in slots), slots
print("PASS beta:", len(owners), "residual owners;", len(slots), "candidate slots")
PY
```

### 2. ARC `--blocks-cache` exploration 与 83 边真值

```bash
PILOT="$ARC/diagnosis_20260823/routeA_pilot/blocks"
FULL="$ARC/diagnosis_20260823/routeA_full/blocks"
HUNT="$ARC/diagnosis_20260823/routeA_full/hunt_remaining/blocks"
find "$PILOT" "$FULL" "$HUNT" -type f \( -name '*.json' -o -name '*.json.gz' \) | wc -l
# 上一行必须为 6759。

OUT=$(python3 scripts/solana/sqd_gap_repair.py repair \
  --mint "$MINT" --case-root "$ARC" \
  --blocks-cache "$PILOT" --blocks-cache "$FULL" --blocks-cache "$HUNT")
printf '%s\n' "$OUT"
GID=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["gid"])' <<<"$OUT")
MINT_KEY=$(python3 -c 'import hashlib,sys; print(hashlib.sha256(sys.argv[1].encode()).hexdigest())' "$MINT")
GEN="$ARC/data/sqd_repair/$MINT_KEY/gen-$GID"
python3 scripts/solana/sqd_gap_repair.py verify "$GID" \
  --mint "$MINT" --case-root "$ARC"

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
    truth += [tuple(json.loads(x)["edge"])
              for x in pathlib.Path(name).read_text().splitlines() if x]
assert len(truth) == 83, len(truth)
assert collections.Counter(actual) == collections.Counter(truth), (len(actual), len(truth))
bundle = json.loads((gen / "bundle.json").read_text())
assert bundle["mode"] == "exploration"
assert bundle["merged"]["edge_rows"] == bundle["base"]["edge_rows"] + len(actual)
print("PASS: 83/83 edges; exploration; merged row identity")
PY
```
