#!/usr/bin/env python3
"""SQD 转账边重放引擎（所有 SQD 链分析的下游标准件）。

读 fetch_sqd_transfers_v2.py 落盘的 data/soltx-<sha256(原始mint)>.jsonl.gz。正式边格式为
[ts, slot, tx_index, instr_index, from_owner, to_owner, amount_raw]；旧 5 元组只允许通过
--legacy-sol5 做只读诊断，不能 reconcile/evolution。ZERO(0x00…00)=铸造/销毁哨兵。

子命令：
  reconcile             全量重放 → 供给闭合 + 全 owner 快照对账（机器 receipt；阶段2硬关卡）
                        需 data/holders_owners.json（scan_token_accounts.py 产物）
  trace <addr> [n]      单地址全部进出边（时间序，默认显示 200 条）
  top [n]               重放末态 top n（默认 30）
  sniper [分钟]         发射后 N 分钟内首次收币的地址集（狙击窗，默认 30）
  mints                 全部铸造/销毁边清单（★pump.fun 币第一优先检查项：
                        创建 tx 的铸造边可有多条，dev-buy 直分收币地址可不是 creator）
  evolution             小时级阵营占比序列（含质押修正）→ data/camp_share_series.json
                        + 有效持仓末态 data/effective_balances.json

mint 来源：--mint / MINT 环境变量 / 工作目录 config.json 的 mint 字段。
evolution 的阵营定义读 --camps camps.json：{"阵营名": [完整地址...]}；
"流动性池" 键列池子地址；质押池用 --stake-pool（或 config.json 的 stake_pools 数组）——
与质押池的边改写为 owner 的质押子仓（有效持仓=现货+质押），防质押潮造成阵营虚降
（判别质押池本身用 pipeline §2 五步法）。
发射时刻默认取首条铸造边 ts，--launch-ts 可覆盖。
来源：PUB(Solana) 分析 2026-07-14 收编（replay+camp_evolution 合并参数化）。
"""
import argparse, gzip, hashlib, io, json, os, re, sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# 批量标签库共享内核（v4 2026-07-17 接入 SOL 主流程；--no-labels 关闭）：
# top/sniper/trace 输出带标签标注（CEX/桥/程序/惯犯高亮），top 未命中大户落 miss 队列
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "labels"))
from camp_spec import validate_camp_spec
from receipt_kernel import build_envelope, finalize_envelope
from solana_exact_validate import validate_coverage
from supply_truth_gate import _reject_constant
from spl_edge_core import (EDGE_SCHEMA_FIELDS, EDGE_SEMANTICS,
                           INSTR_INDEX_TX_NET, ORDER_GRANULARITY_TX,
                           soltx_cache_paths, sqd_repair_paths)
from sqd_cache_identity import (SQD_CACHE_PROTOCOL, SQD_COLLECTOR_ID,
                                SQD_COLLECTOR_SCRIPT,
                                resolve_formal_cache,
                                validate_cache_meta as _validate_cache_meta,
                                validate_repair_bundle)
try:
    from labels_resolver import LabelResolver, append_misses
except Exception:
    LabelResolver = None
    append_misses = None
RESV = None


try:
    from labels_resolver import blind_serial_env, seal_serial_hits, blind_notice   # A2–A3 盲化、A4 揭盲
except Exception:
    blind_serial_env = lambda: False
    seal_serial_hits = blind_notice = None
_BLIND_SEALED = {}   # A2–A3 盲化期收集的 serial 命中（进程尾封存，A4 揭盲）


def lbl(addr):
    """输出行标注：命中标签库时返回 '  ⟨名字<类目>⟩'（serial 惯犯加🚨），未命中返回 ''。
    CHIP_BLIND_SERIAL=1（A2–A3 盲化、A4 揭盲）时 serial 命中返回 ''（等同未命中），详情进封存文件。"""
    if RESV is None:
        return ""
    r = RESV.get(addr)
    if not r:
        return ""
    if r.get("serial"):
        if blind_serial_env():
            if addr not in _BLIND_SEALED:
                _BLIND_SEALED[addr] = {"chain": "sol", "address": addr,
                                       **{k: v for k, v in r.items()}}
            return ""
        return f"  ⟨🚨惯犯:{r['name'][:36]}<{r['category']}>⟩"
    return f"  ⟨{r['name'][:36]}<{r['category']}>⟩"


def _flush_sealed():
    """A2–A3：盲化期收集 serial 命中并封存；A4 揭盲；提示恒定。"""
    if blind_serial_env() and seal_serial_hits is not None:
        p = seal_serial_hits(list(_BLIND_SEALED.values()), ".", "sol replay_edges")
        blind_notice(p)

ZERO = "0x" + "0" * 40
SOLANA_MINT_RE = re.compile(r"[1-9A-HJ-NP-Za-km-z]{32,44}")
def _json_loads(value, label="JSON"):
    try:
        return json.loads(value, parse_constant=_reject_constant)
    except (json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise ValueError(f"{label} 非法: {exc}") from exc


def _validate_mint(mint):
    if not isinstance(mint, str) or mint != mint.strip() \
            or SOLANA_MINT_RE.fullmatch(mint) is None:
        raise ValueError("mint 必须是 strip 后非空、32~44 字符的 Solana base58 地址")
    return mint


def resolve_mint(cli):
    if cli:
        return _validate_mint(cli)
    if os.environ.get("MINT"):
        return _validate_mint(os.environ["MINT"])
    p = Path("config.json")
    if p.exists():
        m = _json_loads(p.read_text(), "config.json").get("mint")
        if m:
            return _validate_mint(m)
    sys.exit("mint 未指定：--mint / MINT 环境变量 / config.json:mint")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _file_ref(path):
    path = Path(path)
    return {"path": path.name, "size": path.stat().st_size,
            "sha256": sha256_file(path)}


def _atomic_json(path, value):
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(value, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def _valid_nonnegative_int(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _validate_formal_edge(row, *, line_no=None):
    where = f"第 {line_no} 行" if line_no is not None else "边"
    if not isinstance(row, (list, tuple)) or len(row) != len(EDGE_SCHEMA_FIELDS):
        raise ValueError(f"{where}必须是 {list(EDGE_SCHEMA_FIELDS)} 七元组")
    ts, slot, tx_index, instr_index, src, dst, amt = row
    if not all(_valid_nonnegative_int(value) for value in (ts, slot, tx_index)):
        raise ValueError(f"{where} ts/slot/tx_index 必须为非布尔非负整数")
    if (not isinstance(instr_index, int) or isinstance(instr_index, bool)
            or instr_index != INSTR_INDEX_TX_NET):
        raise ValueError(f"{where} transaction-net instr_index 必须为 {INSTR_INDEX_TX_NET}")
    if not isinstance(src, str) or not src or not isinstance(dst, str) or not dst:
        raise ValueError(f"{where} from/to 必须为非空字符串")
    if not isinstance(amt, int) or isinstance(amt, bool) or amt <= 0:
        raise ValueError(f"{where} amount_raw 必须为正整数")
    return [ts, slot, tx_index, instr_index, src, dst, amt]


def _normalize_legacy_edge(row, *, line_no):
    if not isinstance(row, (list, tuple)) or len(row) != 5:
        raise ValueError(f"legacy-sol5 第 {line_no} 行必须是 5 元组，混合行宽拒绝")
    ts, slot, src, dst, amt = row
    if not _valid_nonnegative_int(ts) or not _valid_nonnegative_int(slot):
        raise ValueError(f"legacy-sol5 第 {line_no} 行 ts/slot 必须为非布尔非负整数")
    if not isinstance(src, str) or not src or not isinstance(dst, str) or not dst:
        raise ValueError(f"legacy-sol5 第 {line_no} 行 from/to 必须为非空字符串")
    if not isinstance(amt, int) or isinstance(amt, bool) or amt <= 0:
        raise ValueError(f"legacy-sol5 第 {line_no} 行 amount_raw 必须为正整数")
    # None 明示旧格式没有交易/指令身份；只有显式 legacy 路径会产生这类内存行。
    return [ts, slot, None, None, src, dst, amt]


_CASE_ROOT_WARNED = False


def load_edges(mint, *, legacy_sol5=False, case_root=None):
    _validate_mint(mint)
    binding = None
    if case_root is not None and not legacy_sol5:
        f, meta_f, _kind, _gid, binding = resolve_formal_cache(mint, case_root)
    else:
        key = hashlib.sha256(mint.encode("utf-8")).hexdigest()
        f = Path(f"data/soltx-{key}.jsonl.gz")
        meta_f = Path(f"data/soltx-{key}.meta.json")
        if not meta_f.exists():
            sys.exit(f"缓存 meta 不存在：{meta_f}")
        meta = _json_loads(meta_f.read_text(), "soltx meta")
        try:
            _validate_cache_meta(meta, mint, legacy_sol5=legacy_sol5)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        if not legacy_sol5:
            global _CASE_ROOT_WARNED
            if not _CASE_ROOT_WARNED:
                print("WARN: 正式路径须 --case-root（批 5 强制）", file=sys.stderr)
                _CASE_ROOT_WARNED = True
    if f.is_symlink():
        sys.exit(f"边文件是符号链接，拒绝重放：{f}")
    if not f.exists():
        sys.exit(f"边文件不存在：{f}（先跑 fetch_sqd_transfers_v2.py）")
    edges = []
    with gzip.open(f, "rt") as fh:
        for line_no, line in enumerate(fh, 1):
            if line.strip():
                row = _json_loads(line, f"soltx edge row 第 {line_no} 行")
                if legacy_sol5:
                    edges.append(_normalize_legacy_edge(row, line_no=line_no))
                else:
                    edges.append(_validate_formal_edge(row, line_no=line_no))
    if legacy_sol5:
        edges.sort(key=lambda e: (e[1], e[0]))
    else:
        edges.sort(key=lambda e: (e[1], e[2], e[3], e[0]))
    if case_root is None or legacy_sol5:
        return edges, meta_f
    return edges, meta_f, binding


def _read_frozen_formal_edges(path):
    """Read one immutable byte image for both physical identity and formal replay."""
    path = Path(path)
    if path.is_symlink():
        raise ValueError(f"SQD 边文件是符号链接，拒绝 reconcile: {path}")
    if not path.is_file():
        raise ValueError(f"SQD 边文件缺失: {path}")
    try:
        frozen = path.read_bytes()
    except OSError as exc:
        raise ValueError(f"SQD 边文件读取失败: {path}: {exc}") from exc
    if not frozen:
        raise ValueError(f"SQD 边文件为空: {path}")
    edges = []
    try:
        with gzip.open(io.BytesIO(frozen), "rt", encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, 1):
                if not line.strip():
                    continue
                row = _json_loads(line, f"soltx edge row 第 {line_no} 行")
                edges.append(_validate_formal_edge(row, line_no=line_no))
    except (OSError, EOFError, UnicodeDecodeError) as exc:
        raise ValueError(f"SQD 边文件 gzip/UTF-8 非法: {path}: {exc}") from exc
    if not edges:
        raise ValueError("边文件为空，无法生成正式 reconcile 收据")
    edges.sort(key=lambda edge: (edge[1], edge[2], edge[3], edge[0]))
    return edges, len(frozen), hashlib.sha256(frozen).hexdigest()


def replay(edges):
    bal = defaultdict(int)
    minted = burned = 0
    for ts, slot, _tx_index, _instr_index, src, dst, amt in edges:
        if src == ZERO:
            minted += amt
        else:
            bal[src] -= amt
        if dst == ZERO:
            burned += amt
        else:
            bal[dst] += amt
    return bal, minted, burned


def fmt_ts(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%m-%d %H:%M:%S")


def launch_ts_of(edges, override):
    if override:
        return override
    for ts, slot, _tx_index, _instr_index, src, dst, amt in edges:
        if src == ZERO:
            return ts
    return edges[0][0]


def _replay_with_evidence(edges):
    """同一次重放计算余额、逻辑边摘要与首末边；不对大边文件做第二次 IO。"""
    bal = defaultdict(int)
    minted = burned = 0
    digest = hashlib.sha256()
    first = last = None
    for edge in edges:
        ts, slot, _tx_index, _instr_index, src, dst, amt = _validate_formal_edge(edge)
        digest.update((json.dumps(list(edge), ensure_ascii=False) + "\n").encode("utf-8"))
        point = {"slot": slot, "ts": ts}
        if first is None:
            first = point
        last = point
        if src == ZERO:
            minted += amt
        else:
            bal[src] -= amt
        if dst == ZERO:
            burned += amt
        else:
            bal[dst] += amt
    if first is None:
        raise ValueError("边文件为空，无法生成正式 reconcile 收据")
    return bal, minted, burned, digest.hexdigest(), first, last


def _snapshot_target(meta):
    target = meta.get("target") or {}
    return target.get("as_of_block") if isinstance(target, dict) else None


def _case_input_path(case_root, ref, label):
    if not isinstance(ref, dict) or not isinstance(ref.get("path"), str):
        raise ValueError(f"{label} 缺 path 引用")
    rel = Path(ref["path"])
    if rel.is_absolute() or not rel.parts or any(part in {"", ".", ".."}
                                                 for part in rel.parts):
        raise ValueError(f"{label} path 非案根安全相对路径")
    root = Path(case_root).resolve()
    cursor = root
    for part in rel.parts:
        cursor /= part
        if cursor.is_symlink():
            raise ValueError(f"{label} path 含符号链接")
    path = cursor.resolve()
    if root not in path.parents or not path.is_file():
        raise ValueError(f"{label} 文件缺失或逃逸案根")
    return path


def _coverage_inputs(case_root, frm, upper):
    root = Path(case_root).resolve()
    pointer_path = root / "data/sqd_coverage/CURRENT.json"
    if not pointer_path.is_file():
        raise ValueError("coverage 强制输入缺失: data/sqd_coverage/CURRENT.json")
    pointer = _json_loads(pointer_path.read_text(encoding="utf-8"), "coverage CURRENT")
    pointer_inputs = pointer.get("inputs") if isinstance(pointer.get("inputs"), dict) else {}
    coverage_path = _case_input_path(root, pointer_inputs.get("coverage_map"),
                                     "coverage_map")
    counts_path = _case_input_path(root, pointer_inputs.get("slot_counts"),
                                   "coverage_slot_counts")
    checked = validate_coverage(root, coverage_path, pointer_path, frm, upper)
    if not checked["ok"]:
        raise ValueError("coverage 深验失败: " + "; ".join(checked["reasons"]))
    return pointer_path, pointer, coverage_path, counts_path, checked


def _cheap_reconcile_preflight(case_root, mint, as_of_slot):
    """Reject cheap formal-input defects before loading a potentially huge edge log."""
    _validate_mint(mint)
    if case_root is None:
        raise ValueError("reconcile 正式路径必须提供 --case-root")
    if not _valid_nonnegative_int(as_of_slot):
        raise ValueError("reconcile --as-of-slot 必须为非负整数")
    root = Path(case_root).resolve()

    coverage_pointer = root / "data/sqd_coverage/CURRENT.json"
    if not coverage_pointer.is_file():
        raise ValueError("coverage 强制输入缺失: data/sqd_coverage/CURRENT.json")
    _json_loads(coverage_pointer.read_text(encoding="utf-8"), "coverage CURRENT")

    snapshot_meta = root / "data/holders_snapshot_meta.json"
    if not snapshot_meta.is_file():
        raise ValueError("缺 holders_owners.json 或 holders_snapshot_meta.json")
    _json_loads(snapshot_meta.read_text(encoding="utf-8"),
                "holders_snapshot_meta.json")

    _base_edge, base_meta, _parts = soltx_cache_paths(mint, root / "data")
    if not base_meta.is_file():
        raise ValueError("canonical base cache pair is missing")
    _json_loads(base_meta.read_text(encoding="utf-8"), "base meta")


def cmd_reconcile(edges, dec, *, mint, cache_meta_path, case_root,
                  as_of_slot, receipt_path="data/reconcile_receipt.json",
                  edge_source_binding=None):
    """重放并发布 solana-reconcile/v4；mint 按 Solana base58 原文比较。"""
    _validate_mint(mint)
    if case_root is None:
        raise ValueError("reconcile 正式路径必须提供 --case-root")
    if not _valid_nonnegative_int(as_of_slot):
        raise ValueError("reconcile --as-of-slot 必须为非负整数")
    case_root = Path(case_root).resolve()
    cache_meta_path = Path(cache_meta_path)
    resolved_edge, resolved_meta, cache_kind, gid, resolved_binding = \
        resolve_formal_cache(mint, case_root)
    if resolved_meta.resolve() != cache_meta_path.resolve():
        raise ValueError("reconcile cache meta 不是 resolver 当前选择")
    if edge_source_binding is not None and edge_source_binding != resolved_binding:
        raise ValueError("reconcile 传入 edge_source_binding 与 resolver 不一致")
    edge_source_binding = resolved_binding
    cache_meta = _json_loads(cache_meta_path.read_text(encoding="utf-8"),
                             "SQD 缓存 meta")
    frm, to = cache_meta["from_slot"], cache_meta["finalized_upper_slot"]
    if as_of_slot != to:
        raise ValueError(
            "--as-of-slot 必须 == cache finalized_upper_slot；拒绝生成错时点 receipt")
    frozen_edges, _edge_file_size, edge_file_sha256 = _read_frozen_formal_edges(
        resolved_edge)
    supplied_edges = [_validate_formal_edge(edge) for edge in edges]
    if supplied_edges != frozen_edges:
        raise ValueError("reconcile 内存边与冻结边文件不一致")
    edges = frozen_edges
    bal, minted, burned, edge_digest, first, last = _replay_with_evidence(edges)
    # collector 已绑定逻辑摘要与行数；reconcile 只重算对表，绝不首次建立证据。
    if cache_meta["edge_logical_sha256"] != edge_digest:
        raise ValueError("SQD 缓存 meta.edge_logical_sha256 与实际边重放摘要不一致")
    if cache_meta["edge_rows"] != len(edges):
        raise ValueError("SQD 缓存 meta.edge_rows 与实际边数不一致")
    if edge_source_binding.get("soltx_edges_sha256") != edge_file_sha256:
        raise ValueError("resolver edge_source_binding 与冻结边物理哈希不一致")
    coverage_pointer_path, _coverage_pointer, coverage_path, counts_path, coverage = \
        _coverage_inputs(case_root, frm, to)
    coverage_doc = _json_loads(
        coverage_path.read_text(encoding="utf-8"), "coverage_map")
    cache_endpoint = cache_meta.get("endpoint_sha256")
    coverage_endpoint = (coverage_doc.get("sqd") or {}).get(
        "endpoint_fingerprint")
    if cache_endpoint is not None and cache_endpoint != coverage_endpoint:
        raise ValueError("coverage SQD endpoint 指纹与 soltx meta 不一致")
    coverage_effective_verdict = coverage["recomputed"]["verdict"]
    combination_ok = coverage_effective_verdict == \
        "NO_KNOWN_NONCE_OMISSION_DETECTED"
    repair_inputs = {}
    if cache_kind == "repaired":
        repair_parent, repair_pointer_path, _lock = sqd_repair_paths(case_root, mint)
        repair_pointer = _json_loads(
            repair_pointer_path.read_text(encoding="utf-8"), "repair CURRENT")
        bundle_path = _case_input_path(
            case_root, (repair_pointer.get("inputs") or {}).get("bundle"),
            "repair_bundle")
        base_edge, _base_meta, _parts = soltx_cache_paths(mint, case_root / "data")
        bundle = validate_repair_bundle(
            bundle_path, deep=True, case_root=case_root,
            current_base={"edge_sha256": sha256_file(base_edge)})
        generation = bundle_path.parent
        resolution_ref = bundle.get("coverage_resolution") or {}
        resolution_path = generation / str(resolution_ref.get("path") or "")
        if not resolution_path.is_file():
            raise ValueError("repair coverage_resolution 缺失")
        resolution = _json_loads(
            resolution_path.read_text(encoding="utf-8"), "coverage_resolution")
        current_candidates = set(coverage["recomputed"].get("candidate_slots", []))
        census_slots = {row.get("slot") for row in resolution.get("census", [])
                        if isinstance(row, dict)}
        coverage_effective_verdict = resolution.get("effective_verdict")
        combination_ok = (
            coverage_effective_verdict == "DEFECTS_CONFIRMED"
            and current_candidates.issubset(census_slots)
            and bundle.get("gid") == gid)
        repair_inputs = {
            "coverage_resolution": resolution_path,
            "repair_bundle": bundle_path,
            "repair_pointer": repair_pointer_path,
        }
    print(f"边数={len(edges):,}  时间范围 {fmt_ts(edges[0][0])} → {fmt_ts(edges[-1][0])}")
    print(f"铸造={minted:,}  销毁={burned:,}  净={minted-burned:,}")
    neg = {a: v for a, v in bal.items() if v < 0}  # 任意负余额=数据洞
    print(f"负余额地址数={len(neg)}" + (f"  最大负值={min(neg.values()):,}" if neg else ""))
    rb = {a: v for a, v in bal.items() if v > 0}
    snap_f = case_root / "data/holders_owners.json"
    meta_f = case_root / "data/holders_snapshot_meta.json"
    if not snap_f.is_file() or not meta_f.is_file():
        raise ValueError("缺 holders_owners.json 或 holders_snapshot_meta.json")
    mismatch, snapshot_ok, supply = [], False, None
    owners_ref = _file_ref(snap_f) if snap_f.exists() else None
    snap_meta = None
    if snap_f.exists() and meta_f.exists():
        snap_obj = _json_loads(snap_f.read_text(), "holders_owners.json")
        snap = {a: int(v) for a, v in snap_obj.items()}
        snap_meta = _json_loads(meta_f.read_text(), "holders_snapshot_meta.json")
        if "supply_raw" not in snap_meta:
            raise ValueError("holders_snapshot_meta.supply_raw 缺失，拒绝静默默认")
        try:
            registered_supply = int(snap_meta["supply_raw"])
        except (TypeError, ValueError) as exc:
            raise ValueError("holders_snapshot_meta.supply_raw 必须为整数") from exc
        supply = sum(snap.values())
        out_ref = ((snap_meta.get("outputs") or {}).get("holders_owners") or {})
        snapshot_slot = _snapshot_target(snap_meta)
        snapshot_ok = (snap_meta.get("schema") == "solana-holder-snapshot-v2"
                       and snap_meta.get("mint") == mint
                       and snap_meta.get("closed") is True
                       and registered_supply == supply
                       and isinstance(snapshot_slot, int) and not isinstance(snapshot_slot, bool)
                       and snapshot_slot == to == as_of_slot
                       and out_ref == owners_ref)
        print(f"快照 supply={supply:,}  重放净-快照差={minted-burned-supply:,}")
        for a in sorted(set(snap) | set(rb)):
            if rb.get(a, 0) != snap.get(a, 0):
                mismatch.append((a, snap.get(a, 0), rb.get(a, 0)))
        print(f"全 owner 对账：{len(set(snap)|set(rb))-len(mismatch)}/{len(set(snap)|set(rb))} 一致")
        for a, s_, r_ in mismatch[:12]:
            print(f"  MISMATCH {a}  快照={s_:,}  重放={r_:,}  差={r_-s_:,}")
    else:
        print("[FAIL] 缺 holders_owners.json 或 holders_snapshot_meta.json，快照关卡不完整")
    gate_pass = bool(not neg and snapshot_ok and supply == minted - burned
                     and not mismatch and combination_ok)
    # 所有 envelope 引用必须仍是本次计算实际消费的那一版实物；尤其禁止边文件在
    # 冻结读取后、签收据前被同路径换包，造成逻辑摘要与 inputs 哈希分属两版。
    if sha256_file(resolved_edge) != edge_file_sha256:
        raise ValueError("soltx_edges 在重放期间发生变化，拒绝签出混合版本 receipt")
    if sha256_file(cache_meta_path) != edge_source_binding.get("soltx_meta_sha256"):
        raise ValueError("soltx_meta 在重放期间发生变化，拒绝签出混合版本 receipt")
    receipt_inputs = {
        "soltx_edges": resolved_edge, "soltx_meta": cache_meta_path,
        "holders_owners": snap_f, "holders_snapshot_meta": meta_f,
        "coverage_map": coverage_path, "coverage_slot_counts": counts_path,
        "coverage_pointer": coverage_pointer_path, **repair_inputs,
    }
    envelope = build_envelope(
        "solana-reconcile/v4",
        {"chain": "solana", "token": mint, "as_of_block": as_of_slot},
        "scripts/solana/replay_edges.py", "formal",
        inputs=receipt_inputs, input_base=case_root)
    receipt = finalize_envelope(
        envelope, "PASS" if gate_pass else "FAIL", 0 if gate_pass else 2,
        chain="solana", mint=mint,
        collection_window={"from_slot": frm, "to_slot": to},
        edge_extrema={"first": first, "last": last},
        edge_digest=edge_digest, edge_count=len(edges),
        minted_raw=minted, burned_raw=burned, net_supply_raw=minted - burned,
        negative_balance_count=len(neg), snapshot_present=True,
        snapshot_meta_present=True, snapshot_closed=snapshot_ok,
        snapshot_supply_raw=supply, snapshot_mismatch_count=len(mismatch),
        edge_source_binding=edge_source_binding,
        coverage_effective_verdict=coverage_effective_verdict,
        gate_pass=gate_pass)
    shown_receipt = Path(receipt_path)
    if not shown_receipt.is_absolute():
        shown_receipt = case_root / shown_receipt
    shown_receipt = shown_receipt.resolve()
    if case_root not in shown_receipt.parents:
        raise ValueError("--receipt 必须位于案根内")
    _atomic_json(shown_receipt, receipt)
    _atomic_json(case_root / "data/replay_final_balances.json",
                 dict(sorted(rb.items(), key=lambda kv: -kv[1])))
    print("重放末态已写 data/replay_final_balances.json")
    return gate_pass


def cmd_trace(edges, addr, dec, limit):
    rows = [e for e in edges if e[4] == addr or e[5] == addr]
    print(f"{addr} 相关边 {len(rows)} 条（显示前 {limit}）")
    net = 0
    for ts, slot, _tx_index, _instr_index, src, dst, amt in rows[:limit]:
        d = "IN " if dst == addr else "OUT"
        other = src if dst == addr else dst
        net += amt if dst == addr else -amt
        print(f"{fmt_ts(ts)} {d} {amt/dec:>16,.2f}  对手 {other}{lbl(other)}")
    if len(rows) > limit:
        print(f"...({len(rows)-limit} 条省略)")
    print(f"净变动 {net/dec:,.2f}")


def cmd_top(edges, dec, n):
    bal, minted, burned = replay(edges)
    total = minted - burned
    top = sorted(bal.items(), key=lambda kv: -kv[1])[:n]
    for i, (a, v) in enumerate(top, 1):
        print(f"#{i:<3} {a}  {v/dec:>16,.0f}  {v/total*100:.3f}%{lbl(a)}")
    # 实战 miss 队列（v4）：top 未命中标签库的大户落盘，跨 token 反复出现者是设施/MM 候选
    if RESV is not None and append_misses is not None and RESV.table:
        miss = [(a, round(v / total * 100, 3), "SOL top 持仓未命中")
                for a, v in top if RESV.get(a) is None]
        tag = os.path.basename(os.getcwd())
        k = append_misses("sol", miss, f"{tag} replay-top")
        if k:
            print(f"（miss 队列新记 {k} 个未命中大户 → references/labels/miss-queue/sol.csv）")


def cmd_sniper(edges, dec, minutes, launch_ts):
    cutoff = launch_ts + minutes * 60
    first_in = {}
    for ts, slot, _tx_index, _instr_index, src, dst, amt in edges:
        if dst != ZERO and dst not in first_in:
            first_in[dst] = (ts, amt, src)
    snipers = {a: v for a, v in first_in.items() if v[0] <= cutoff}
    print(f"发射({fmt_ts(launch_ts)})后 {minutes} 分钟内首次收币地址：{len(snipers)} 个")
    for a, (ts, amt, src) in sorted(snipers.items(), key=lambda kv: kv[1][0]):
        print(f"{fmt_ts(ts)}  {a}{lbl(a)}  首笔 {amt/dec:>15,.0f}  来自 {src}{lbl(src)}")


def cmd_mints(edges, dec):
    total = sum(a for _, _, _, _, s, _, a in edges if s == ZERO) or 1
    print("铸造边（src=ZERO）全清单：")
    for ts, slot, _tx_index, _instr_index, src, dst, amt in edges:
        if src == ZERO:
            print(f"  {fmt_ts(ts)} slot={slot}  → {dst}  {amt/dec:,.0f}（{amt/total*100:.2f}% 铸造量）")
    print("销毁边（dst=ZERO）全清单：")
    n = 0
    for ts, slot, _tx_index, _instr_index, src, dst, amt in edges:
        if dst == ZERO:
            n += 1
            if n <= 30:
                print(f"  {fmt_ts(ts)} slot={slot}  {src} →  {amt/dec:,.0f}")
    if n > 30:
        print(f"  ...(销毁边共 {n} 条，仅显示前 30)")


def cmd_evolution(edges, dec, camps_file, stake_pools, edge_source_binding=None):
    # F-05 定案（rg 调用面：main --camps 默认 camps.json + test_review_resume_integrity，
    # 文档与真实案均无"无 camps 跑 evolution"的用法）：缺文件从"静默空 spec"改为硬拒——
    # 静默空 spec 的效果是全部地址落散户/狙击者两桶，序列外观正常实际零阵营。
    # 确需无阵营定义的探索跑，显式建一份内容为 {} 的 camps 文件表达意图。
    if not Path(camps_file).exists():
        print(f"[camp-spec] 阵营定义文件不存在：{camps_file}——evolution 必须显式给"
              f" camps（无阵营定义就放一份 {{}}），拒绝静默按空 spec 重放", file=sys.stderr)
        raise SystemExit(2)
    camps_def = _json_loads(Path(camps_file).read_text(), "camps spec")
    # 互斥校验（同营内+跨营重复硬拒 exit 2；Solana base58 原样不改写大小写），
    # 与 EVM 两引擎同一共享实现（scripts/lib/camp_spec.py）
    camps_def = validate_camp_spec(camps_def, chain_family="solana",
                                   source_label=str(camps_file))
    addr2camp = {}
    pools = set()
    for camp, addrs in camps_def.items():
        for a in addrs:
            addr2camp[a] = camp
        if camp == "流动性池":
            pools |= set(addrs)
    launch_ts = launch_ts_of(edges, None)

    # 第一遍：首30分钟狙击者（未列入阵营定义的首买地址）
    cutoff = launch_ts + 30 * 60
    first_in = {}
    for ts, slot, _tx_index, _instr_index, src, dst, amt in edges:
        if dst != ZERO and dst not in first_in:
            first_in[dst] = ts
    snipers = {a for a, ts in first_in.items()
               if ts <= cutoff and a not in pools and a not in stake_pools and a not in addr2camp}
    json.dump(sorted(snipers), open("data/sniper_set.json", "w"))
    print(f"首30分钟狙击者 {len(snipers)} 个（已写 data/sniper_set.json）")

    def camp_of(a):
        if a in addr2camp:
            return addr2camp[a]
        if a in snipers:
            return "首30分钟狙击者"
        return "其他散户"

    # 第二遍：重放（与质押池的边改写为 owner 质押子仓，有效持仓=现货+质押）
    spot, staked = defaultdict(int), defaultdict(int)
    minted_cum = burned = 0
    series = []
    cur_hour = None

    def snapshot(h):
        supply = minted_cum - burned
        agg = defaultdict(int)
        for bookmap in (spot, staked):
            for a, v in bookmap.items():
                if v > 0:
                    agg[camp_of(a)] += v
        row = {"ts": h, "_supply_raw": str(supply)}
        for c, v in agg.items():
            row[c] = round(v / supply * 100, 4) if supply > 0 else 0.0
        row["锁仓/销毁"] = round(burned / supply * 100, 4) if supply > 0 else 0.0
        series.append(row)

    for ts, slot, _tx_index, _instr_index, src, dst, amt in edges:
        h = ts - ts % 3600
        if cur_hour is not None and h != cur_hour:
            snapshot(cur_hour)
        cur_hour = h
        if src == ZERO:
            minted_cum += amt
        if dst in stake_pools and src != ZERO:
            spot[src] -= amt
            staked[src] += amt
            continue
        if src in stake_pools and dst != ZERO:
            staked[dst] -= amt
            spot[dst] += amt
            continue
        if src != ZERO:
            spot[src] -= amt
        if dst == ZERO:
            burned += amt
        else:
            spot[dst] += amt
    if cur_hour is not None:
        snapshot(cur_hour)

    json.dump(series, open("data/camp_share_series.json", "w"))
    print(f"阵营序列 {len(series)} 个小时点，已写 data/camp_share_series.json")
    if series:
        print("末态占比：", {k: v for k, v in series[-1].items() if k != "ts"})
    eff = defaultdict(int)
    for bookmap in (spot, staked):
        for a, v in bookmap.items():
            eff[a] += v
    print("\n质押修正后有效持仓 top15：")
    for a, v in sorted(((a, v) for a, v in eff.items() if v > 0), key=lambda kv: -kv[1])[:15]:
        final_supply = minted_cum - burned
        print(f"  {a}  {v/dec:>15,.0f}  {v/final_supply*100:.3f}%  "
              f"(现货{spot[a]/dec:,.0f}+质押{staked[a]/dec:,.0f})")
    json.dump({a: v for a, v in sorted(eff.items(), key=lambda kv: -kv[1]) if v != 0},
              open("data/effective_balances.json", "w"))
    print("有效持仓末态已写 data/effective_balances.json")
    # F-04：producer sidecar——effective_balances 是与本序列同一次重放的终态快照
    # （末点对账锚）；reconcile_receipt 在场即绑（正式编译链要求其在场且 gate_pass）
    from camp_series_provenance import write_series_sidecar
    _inputs = {"sniper_set": "data/sniper_set.json"}
    if Path("data/reconcile_receipt.json").exists():
        _inputs["reconcile_receipt"] = "data/reconcile_receipt.json"
    write_series_sidecar("data/camp_share_series.json",
                         producer="scripts/solana/replay_edges.py",
                         series_format="sol-rows", denominator="net_supply",
                         camps_spec_path=camps_file,
                         final_balances_path="data/effective_balances.json",
                         inputs=_inputs,
                         edge_source_binding=edge_source_binding)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["reconcile", "trace", "top", "sniper", "mints", "evolution"])
    ap.add_argument("arg", nargs="?", help="trace 的地址 / top 的 n / sniper 的分钟数")
    ap.add_argument("arg2", nargs="?", help="trace 的显示条数")
    ap.add_argument("--mint")
    ap.add_argument("--case-root",
                    help="案根；正式消费经 CURRENT-aware cache resolver（reconcile/evolution 必填）")
    ap.add_argument("--as-of-slot", type=int,
                    help="reconcile 冻结 slot；必须等于快照 slot 与 cache finalized_upper_slot")
    ap.add_argument("--receipt", default="data/reconcile_receipt.json",
                    help="reconcile 收据路径（默认 data/reconcile_receipt.json）")
    ap.add_argument("--decimals", type=int, default=6)
    ap.add_argument("--launch-ts", type=int, help="发射时刻 epoch（默认取首条铸造边）")
    ap.add_argument("--camps", default="camps.json", help="evolution 的阵营定义 JSON")
    ap.add_argument("--stake-pool", action="append", default=[],
                    help="质押/托管池 owner 地址（可多次；也可 config.json:stake_pools）")
    ap.add_argument("--no-labels", action="store_true", help="关闭批量标签库兜底")
    ap.add_argument("--legacy-sol5", action="store_true",
                    help="显式读取旧 5 元组做 non-formal/order-ambiguous 只读诊断")
    args = ap.parse_args()
    if args.cmd in {"reconcile", "evolution"} and not args.case_root:
        ap.error(f"{args.cmd} 正式路径必须提供 --case-root")
    if args.cmd == "reconcile" and args.as_of_slot is None:
        ap.error("reconcile 正式路径必须提供 --as-of-slot")
    try:
        global RESV
        if (LabelResolver is not None and "--no-labels" not in sys.argv
                and not args.legacy_sol5):
            RESV = LabelResolver("sol")
            RESV.warn_if_degraded()     # 降级=显式 stderr 警告（"没命中"≠"没加载"，v4）
            if blind_serial_env():
                import atexit
                atexit.register(_flush_sealed)   # A2–A3：serial 命中在进程尾封存，A4 揭盲
        elif LabelResolver is None:
            print("[labels][degraded_mode] labels_resolver 导入失败——本次运行无标签兜底", file=sys.stderr)
        mint = resolve_mint(args.mint)
        if args.cmd == "reconcile" and not args.legacy_sol5:
            _cheap_reconcile_preflight(args.case_root, mint, args.as_of_slot)
        dec = 10 ** args.decimals
        loaded = load_edges(
            mint, legacy_sol5=args.legacy_sol5, case_root=args.case_root)
        if args.case_root and not args.legacy_sol5:
            edges, cache_meta_path, edge_source_binding = loaded
        else:
            edges, cache_meta_path = loaded
            edge_source_binding = None
        if args.legacy_sol5:
            print("[legacy-sol5] non_formal=true order_ambiguous=true")
            if args.cmd in {"reconcile", "evolution"}:
                print("BLOCK: legacy-sol5 禁止 reconcile/evolution，拒绝生成正式链产物",
                      file=sys.stderr)
                return 2
        stake_pools = set(args.stake_pool)
        cfg = Path("config.json")
        if cfg.exists():
            stake_pools |= set(_json_loads(
                cfg.read_text(), "config.json").get("stake_pools", []))

        if args.cmd == "reconcile":
            if not cmd_reconcile(edges, dec, mint=mint,
                                 cache_meta_path=cache_meta_path,
                                 case_root=args.case_root,
                                 as_of_slot=args.as_of_slot,
                                 receipt_path=args.receipt,
                                 edge_source_binding=edge_source_binding):
                return 2
        elif args.cmd == "trace":
            if not args.arg:
                raise ValueError("trace 需要地址参数")
            cmd_trace(edges, args.arg, dec, int(args.arg2) if args.arg2 else 200)
        elif args.cmd == "top":
            cmd_top(edges, dec, int(args.arg) if args.arg else 30)
        elif args.cmd == "sniper":
            cmd_sniper(edges, dec, int(args.arg) if args.arg else 30,
                       launch_ts_of(edges, args.launch_ts))
        elif args.cmd == "mints":
            cmd_mints(edges, dec)
        elif args.cmd == "evolution":
            cmd_evolution(edges, dec, args.camps, stake_pools,
                          edge_source_binding=edge_source_binding)
    except (OSError, ValueError, json.JSONDecodeError, RecursionError) as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
