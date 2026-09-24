# W1盲审：FAIL

发现 **1 项阻断问题**：校验器会接受相互矛盾的 recheck 响应，继续把该 slot 判为 `INHERITED_REFUTED`。这违反工单 §1.5、§2.4 的独立拒收要求。

审查范围：`6b36dcdd043d0b2b51c03de9ab0bb555b25f436a..65132abda8253cf34562f92f726d311d9a32b4f8`，限定 `scripts references assets`。

**阻断问题：完整响应中的“无块头”没有参与冲突检查**

位置：[solana_exact_validate.py:562](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/solana_exact_validate.py:562)、[solana_exact_validate.py:644](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/solana_exact_validate.py:644)。

同一继承 slot 存在两条自报 `verified` 的完整 recheck：

- 第一条响应包含该 slot，零 nonce，解码值为 `2`。
- 第二条响应为空，按探针 `_scan_request` 的语义，该请求区间解码值为 `1`，表示无块头。
- 两条响应各自的大小、摘要、请求摘要及返回字段均正确。

实际实现对第二条返回 `{}`，没有返回或比较隐含的 `1`；合并结果保留第一条的 `2`。最终 `validate_coverage()` 返回：

```text
ok=True
reasons=[]
states=['INHERITED_REFUTED']
```

独立验证了第二种同源反例：完整、非空响应只返回后一个 slot，缺少前一个继承 slot，也被接受。问题不局限于空数组。

正常探针是否会生成这种矛盾记录，不是本项结论的前提；本工单明确要求校验器拒绝自报字段与响应实物不一致的输入。

**可复现命令**

在指定工作目录执行以下命令。文件内容全部存在内存中，仅替换文件读取接口；没有替换任何校验函数，没有落盘、联网或修改文件。每次均重新计算 ledger 引用、coverage 摘要、probe_id 和 CURRENT 引用。

```bash
python3 -B -c '
import sys, io, gzip
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path[:0] = ["scripts/lib", "scripts/solana"]
import solana_exact_validate as v
import sqd_coverage_probe as p

J, H = v.canonical_json, v.sha256_bytes
root = Path("/__w1_memory_case__")
gen = root / "data/sqd_coverage/g"
fs = {}

def put(name, value):
    fs[str(gen / name)] = value

def ref(name, base=gen):
    path = gen / name
    raw = fs[str(path)]
    return dict(path=str(path.relative_to(base)), size=len(raw), sha256=H(raw))

e = dict(kind="repair-census", source_mint="M", probe_id="1"*16,
    repair_gid="2"*16, plan_digest="3"*16, resolution_sha256="4"*64,
    bundle_sha256="5"*64, producer=dict(path="p", sha256="6"*64),
    refuted_count=1, origin_generated_at="2026-09-01T00:00:00+00:00",
    origin_asset_sha256=None, asset_sha256=None)
put("shared_map_source.json", J(dict(schema=v.SHARED_MAP_SCHEMA,
    candidate_slots=[0], refuted_slots=[0], refuted_origin=[0],
    refuted_evidence=[e])))
source = ref("shared_map_source.json")
claim = dict(slots=[0], count=1, origin=[0], refuted_evidence=[e],
    asset_sha256=source["sha256"], source_ref=source,
    verified_at="2026-09-24T00:00:00+00:00")
counts = bytes([2])
shared = dict(sha256=source["sha256"], inherited_refuted=claim,
    reused_ranges=[dict(from_slot=0, to_slot=0)], unverified_ranges=[])
reuse = dict(provider="shared-map", mode="map-reuse", ok=True,
    counts_coverage=True, slots_covered=1,
    query_body_sha256=H(J(dict(asset=source["sha256"]))),
    response_sha256=H(counts))
reuse.update({"from":0, "to":0})

def recheck(blocks):
    row = dict(provider="SQD", mode="recheck", ok=True, http_status=200,
        counts_coverage=True, recheck_outcome="verified", slots_covered=1,
        query_body_sha256=H(J(p.sqd_query_body(0,0))),
        recheck_response=blocks, response_sha256=H(J(blocks)),
        bytes=len(J(blocks)), n_blocks=len(blocks), empty_response=not blocks,
        returned_from=0 if blocks else None,
        returned_to=0 if blocks else None)
    row.update({"from":0, "to":0})
    return row

producer = dict(path="scripts/solana/sqd_coverage_probe.py",
    sha256=v.sha256_file(Path("scripts/solana/sqd_coverage_probe.py")))
original_open, original_stat, original_file = Path.open, Path.stat, Path.is_file

def memopen(path, mode="r", *a, **kw):
    if str(path) in fs:
        raw = fs[str(path)]
        return io.BytesIO(raw) if "b" in mode else io.StringIO(raw.decode())
    return original_open(path, mode, *a, **kw)

def memstat(path, *a, **kw):
    if str(path) in fs:
        return SimpleNamespace(st_size=len(fs[str(path)]), st_mode=0o100644)
    return original_stat(path, *a, **kw)

for conflict in (False, True):
    rows = [reuse, recheck([dict(header=dict(number=0), instructions=[])])]
    if conflict:
        rows.append(recheck([]))
    put("slot_counts.bin.gz", gzip.compress(counts, mtime=0))
    put("ledger.jsonl", b"\n".join(
        J(dict(row,seq=i)) for i,row in enumerate(rows)))
    classified = v.classify_four_states(
        counts, 0, inherited_refuted=frozenset([0]))
    c = dict(schema=v.COVERAGE_SCHEMA, version=1, chain="solana", mint="M",
        producer=producer, era_params=v.ERA_PARAMS,
        sqd=dict(dataset="solana-mainnet", endpoint_fingerprint="fixture",
            metadata_normalized={}, metadata_sha256=H(J({})),
            finalized_head_at_scan=1,
            query_body_sha256=p.sqd_query_template_sha256()),
        scan_ranges=[dict(from_slot=0,to_slot=0,mode="map-reuse")],
        shared_map=shared, skipped_confirmation=None,
        slot_counts=dict(ref("slot_counts.bin.gz"),
            from_slot=0,to_slot=0,encoding=v.COUNT_ENCODING),
        ledger=dict(ref("ledger.jsonl"),requests=len(rows),
            success_ranges_sha256=H(J([[0,0]]))))
    c.update({key:classified[key]
        for key in ("summary","candidate_slots","verdict")})
    c["probe_id"] = v.compute_probe_id(c)
    put("coverage_map.json", J(c))
    pointer = dict(schema=v.COVERAGE_POINTER_SCHEMA,
        target=dict(chain="solana",token="M",as_of_block=0),
        mode="formal",verdict="PASS",exit_code=0,producer=producer,
        probe_id=c["probe_id"],published_at="2026-09-24T00:00:01+00:00",
        supersedes=None,
        inputs={key:ref(name,root) for key,name in [
            ("coverage_map","coverage_map.json"),
            ("slot_counts","slot_counts.bin.gz"),
            ("ledger","ledger.jsonl")]})
    pp = root / "data/sqd_coverage/CURRENT.json"
    fs[str(pp)] = J(pointer)
    with patch.object(Path,"open",memopen), patch.object(Path,"stat",memstat), \
         patch.object(Path,"is_file",
             lambda path: str(path) in fs or original_file(path)):
        result = v.validate_coverage(root,gen/"coverage_map.json",pp,0,0)
    print("conflict=", conflict, "ok=", result["ok"],
          "reasons=", result["reasons"],
          "states=", result["recomputed"]["states"])
'
```

预期：`conflict=False` 通过；`conflict=True` 拒收，包含 `inherited refuted` 理由，并清空继承后重算。

实际：

```text
conflict= False ok= True reasons= [] states= ['INHERITED_REFUTED']
conflict= True ok= True reasons= [] states= ['INHERITED_REFUTED']
```

建议修复：对完整请求区间内未返回块头的 slot，按探针一致的规则视为 `1`，参与继承条件和跨记录冲突检查。补充“完整空响应冲突”和“非空完整响应缺少继承 slot”两项负例；不能只相信 `recheck_outcome="verified"`。

**各审查项结果**

| 项目 | 独立审查结果 |
|---|---|
| a：白名单、不改清单、schema 消费 | 通过。差异只有指定 8 个文件，逐文件增删行数与完成报告一致。修复脚本仅改指定函数。`git diff --check` 通过。 |
| b：无继承兼容 | 48 组分类输入与基线结果全等；仓库旧资产 `20260827.json` 在新校验器下通过；使用旧 producer 哈希的无继承内存产物通过。无继承新增键及旧发布案实物的验证边界见下文。 |
| c：探针继承条件、时效 | 静态检查确认六条件均在路径中：成功复用、来源成员、实测与资产值均为 2、实际复用区间、排除未验证区间、逐证据项原始时效。链式转换保留原始时间。 |
| d：校验器独立拒收 | **失败，原因如上。** 其他已独立运行的负例均拒收，详见下方。 |
| e：helper 与导出 | 静态核对了 CURRENT、bundle 文件引用、resolution map 摘要、bundle producer、计划并集、own_refuted 条件。`--no-repair` 仍调用 helper 并剔除 confirmed；链式字段清空、索引重排及 `origin_asset_sha256` 规则符合工单。未独立执行完整导出流程。 |
| f：β 兼容 | 独立运行状态矩阵通过：β 仅接受有块头且零 nonce；α 保留拒绝；`_repair_state_matches` 同步。 |
| g：副本发布协议 | 静态确认副本先于 probe_id 落盘，加入 `_same_generation/_clear_pending`，未新增 pointer.inputs 键。未执行真实发布及 fsync 测试。 |
| h：测试登记与完成报告 | 六个新增 coverage 测试及 β 测试均已登记。源码覆盖了工单列举的主要场景，但遗漏上述两种隐含值冲突。完成报告的改动统计吻合；其“完整响应、逐 slot 值独立复核”的表述不足以覆盖本次反例。 |

独立运行的 invariant 结果：

```text
PASS invariant manifest: receipt_producers=81, receipt_consumers=118,
transport_calls=65, atomic_writes=62, formal_entrypoints=61, exceptions=0
```

**已独立执行的其他拒收检查**

以下不一致输入均使完整 `validate_coverage()` 拒收，并产生 `inherited refuted` 理由：

- 三方摘要不一致、副本缺失、副本实物大小/摘要不符。
- evidence 与副本不全等；origin 为 bool、越界或合法索引错绑成员。
- 本案 counts 改为 3，并同步重算 map-reuse 响应摘要。
- 自报复用区间与 ledger 不一致，或继承 slot 落入 unverified。
- 缺 recheck、短返回、失败记录、明确 mismatch、查询或响应摘要错误。
- 重算响应摘要后，实测值仍与继承要求不符。
- 非空继承与 fallback 并存。
- 原始证据过期；精确 30 天通过，超过 1 秒拒收。

另外确认：部分继承保留完整来源 evidence 可以通过；有效 `counts_coverage=False` recheck 可以参与继承证明。

**未独立验证的范围与纪律披露**

本次没有运行会创建临时文件的整套测试，也没有运行 `run_all.py`、`docs_lint.py`、`changelog_lint.py` 或触及 `.staging_b3` 的用例。实际发布、resume、完整导出链、base/repaired 组合路径及旧发布案实物未独立重跑；`W1_acceptance.md` 中的相关 PASS 仅作为调度方证据，未冒充本次结果。

全程只读、离线，无文件新建或修改，无 commit。未读取 `~/.codex/`、memories 或其他指定禁读内容；工作区前后均干净。
