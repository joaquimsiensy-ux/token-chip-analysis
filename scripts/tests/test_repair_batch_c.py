#!/usr/bin/env python3
"""六视角修复批 C（F-05＋F-04）回归测试。

F-05 阵营 spec 四族等深（scripts/lib/camp_spec.py 共享实现）：
  互斥阵营重复地址（同营内＋跨营，含 EVM 大小写变体）硬拒 exit 2；查重在
  set() 化之前、按链规范化之后；build_evolution 的 {addr: camp} 形态在 JSON
  解析层（object_pairs_hook）拒重复键；replay_edges 缺 camps 文件硬拒
  （rg 定案：全库无"无 camps 跑 evolution"的合法用法，显式空 spec {} 才合法）。

F-04 阵营序列 producer→consumer 链（scripts/lib/camp_series_provenance.py）：
  ①CAMP_ORDER 拆现代/legacy 两段（合并保原序），compile_state 白名单 import
    现代段（禁手抄）；②数值面：有限数/值域/同点双式闭合（burn 桶豁免口径）/
    日期轴 UTC 严格递增；③producer sidecar：四族写 `<series>.provenance.json`，
    consumer（state_from_facts --series-source）验输出 sha＋输入三验＋登记面
    命中＋camps spec 末点对账；④figures_from_facts check 的 --tol-pp formal
    写死、仅 --exploration 可覆盖。

真实产物形态用例（批 B 教训：夹具键名与生产者不符=影子键假绿）：EVM 链用
replay_duck 真跑产出（含 burn 的 camp_series.json 真形态）；Solana 链用
replay_edges reconcile+evolution 真跑产出（含 锁仓/销毁 行内桶真形态）。
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
for sub in ("tests", "lib", "evm", "solana", "report"):
    p = str(ROOT / "scripts" / sub)
    if p not in sys.path:
        sys.path.insert(0, p)

from sqd_v4_test_fixture import write_coverage_fixture

Z = "0x" + "0" * 40
A = "0xa000000000000000000000000000000000000001"
B = "0xb000000000000000000000000000000000000002"
C = "0xc000000000000000000000000000000000000003"
SA = "So1AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
SB = "So1BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"

PASSED = []


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name}: {detail}")
    PASSED.append(name)


def run(cmd, cwd, env=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    return subprocess.run([sys.executable] + [str(x) for x in cmd],
                          cwd=str(cwd), capture_output=True, text=True,
                          timeout=300, env=e)


def file_ref(path: Path):
    return {"path": path.name, "size": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def write_json(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    return path


def write_sol_edges(path: Path, edges):
    """Write the canonical gzip edge object used by reconcile-chain tests."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for edge in edges:
            fh.write(json.dumps(list(edge), ensure_ascii=False) + "\n")
    return path


def formal_sol_meta(mint, from_slot, to_slot, edges):
    from producer_history import historical_producer_hashes
    collector_hashes = historical_producer_hashes(
        "scripts/solana/fetch_sqd_transfers_v2.py", "sqd-solana-cache/v4")
    assert collector_hashes, collector_hashes
    logical = hashlib.sha256()
    for edge in edges:
        logical.update(
            (json.dumps(list(edge), ensure_ascii=False) + "\n").encode("utf-8")
        )
    write_coverage_fixture(Path.cwd(), mint=mint,
                           from_slot=from_slot, to_slot=to_slot)
    return {
        "schema": "sqd-solana-cache/v4", "version": 4, "mint": mint,
        "collector": "fetch_sqd_transfers_v2.py/v4",
        "collector_sha256": next(iter(sorted(collector_hashes))),
        "edge_schema": ["ts", "slot", "tx_index", "instr_index", "from", "to", "amt"],
        "edge_semantics": "owner-net-greedy",
        "order_granularity": "transaction", "order_exact": False,
        "from_slot": from_slot, "finalized_upper_slot": to_slot,
        "edge_logical_sha256": logical.hexdigest(), "edge_rows": len(edges),
    }


def run_reconcile_v4(module, edges, dec, *, mint, cache_meta_path):
    return module.cmd_reconcile(
        edges, dec, mint=mint, cache_meta_path=cache_meta_path,
        case_root=Path.cwd(), as_of_slot=3)


def run_evolution_v4(module, edges, dec, camps_file, stake_pools):
    receipt = Path("data/reconcile_receipt.json")
    binding = None
    if receipt.is_file():
        binding = json.loads(receipt.read_text(encoding="utf-8")).get(
            "edge_source_binding")
    return module.cmd_evolution(
        edges, dec, camps_file, stake_pools, edge_source_binding=binding)


# ── F-05：共享校验单元面 ─────────────────────────────────────────


def t_f05_unit():
    from camp_spec import validate_camp_spec, load_addr_camp_json

    def rejected(camps, family):
        try:
            validate_camp_spec(camps, chain_family=family)
            return False
        except SystemExit as exc:
            return exc.code == 2

    # 原反例：同址跨营（JSON 后键静默夺走归属）
    check("F05 跨营重复硬拒 exit2",
          rejected({"camp_A": [A], "camp_B": [A]}, "evm"))
    # 同族变体：EVM 大小写变体绕精确匹配
    check("F05 跨营大小写变体硬拒",
          rejected({"camp_A": ["0xAbC0000000000000000000000000000000000001"],
                    "camp_B": ["0xabc0000000000000000000000000000000000001"]}, "evm"))
    check("F05 同营内重复硬拒", rejected({"camp_A": [A, A]}, "evm"))
    check("F05 同营内大小写变体硬拒",
          rejected({"camp_A": [A, A.upper().replace("0X", "0x")]}, "evm"))
    # Solana base58 大小写敏感：大小写不同=不同地址，合法（防误伤）
    out = validate_camp_spec({"营1": [SA], "营2": [SA.lower()]}, chain_family="solana")
    check("F05 solana 大小写敏感不误杀", out["营1"] == [SA])
    check("F05 solana 字面同址跨营硬拒",
          rejected({"营1": [SA], "营2": [SA]}, "solana"))
    # 失败分支：值非列表 / 非法阵营名
    check("F05 值非列表硬拒", rejected({"camp_A": "not-a-list"}, "evm"))
    check("F05 空阵营名硬拒", rejected({"": [A]}, "evm"))
    # 绿例：规范化返回（EVM lower、保序）
    out = validate_camp_spec({"甲": ["0xAbC0000000000000000000000000000000000001", B]},
                             chain_family="evm")
    check("F05 EVM 规范化 lower 保序",
          out["甲"] == ["0xabc0000000000000000000000000000000000001", B])

    # {addr: camp} 形态：JSON 重复键在解析层拒（解析后永远查不到）
    with tempfile.TemporaryDirectory() as td:
        dup = Path(td) / "entity_camps.json"
        dup.write_text('{"%s": "项目方", "%s": "大庄"}' % (SA, SA), encoding="utf-8")
        try:
            load_addr_camp_json(dup)
            check("F05 JSON 重复键解析层拒", False, "重复键被接受")
        except SystemExit as exc:
            check("F05 JSON 重复键解析层拒", exc.code == 2, f"code={exc.code}")
        ok = Path(td) / "ok.json"
        ok.write_text(json.dumps({SA: "项目方", SB: "大庄"}), encoding="utf-8")
        obj = load_addr_camp_json(ok)
        check("F05 addr:camp 合法绿例", obj == {SA: "项目方", SB: "大庄"})


# ── EVM 真实产物工厂（replay_duck 真跑，含 burn）───────────────────


def build_evm_case(td: Path, camps_obj, *, expect_rc=0):
    from evm_channel_fixture import write_csv_channel_receipt
    rows = [
        (100, "2026-01-01T10:00:00", "0x" + "1" * 64, Z, A, 1000),   # mint
        (105, "2026-01-02T10:00:00", "0x" + "2" * 64, A, B, 400),
        (110, "2026-01-03T10:00:00", "0x" + "3" * 64, A, C, 100),
        (115, "2026-01-04T10:00:00", "0x" + "4" * 64, B, Z, 50),     # burn
    ]
    src = td / "transfers.csv"
    with src.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["block", "ts", "tx", "from", "to", "value", "uniqueId"])
        for i, (b, ts, tx, frm, to, v) in enumerate(rows):
            w.writerow([b, ts, tx, frm, to, v, f"{tx}:log:{i}"])
    write_csv_channel_receipt(td, "t", src, A, 0, 999999)
    (td / "channels.json").write_text(json.dumps(
        {"schema": "evm-channels/v2", "token": A, "expected_from": 0,
         "expected_to": 999999,
         "channels": [{"path": "transfers.csv", "lo": 0, "hi": 999999,
                       "tag": "t", "format": "v1csv", "receipt": "t.receipt.json"}]}))
    (td / "camps.json").write_text(json.dumps(camps_obj, ensure_ascii=False))
    p = run([ROOT / "scripts/evm/replay_duck.py", "--channels", "channels.json",
             "--out-dir", "data", "--camps", "camps.json", "--no-merged"], td)
    assert p.returncode == expect_rc, \
        f"replay_duck rc={p.returncode}≠{expect_rc}: {p.stdout[-400:]} {p.stderr[-400:]}"
    return p


def write_supply_truth(td: Path):
    """真实生产者形态（supply_truth_gate.py 收据：schema/verdict/exit_code/
    target 三键/inputs.replay_stats，TAG 案实物核对）——F-C3 起登记面结构化
    三验＋N-C3 起 target 案身份锚（token 对案内 channels_preflight.json），
    影子 schema（如自造 supply-truth/v1）会被拒。"""
    import hashlib
    stats = td / "data/replay_stats.json"
    (td / "supply_truth.json").write_text(json.dumps(
        {"schema": "supply-truth-receipt/v3", "verdict": "PASS", "exit_code": 0,
         "target": {"chain": "bsc", "token": A, "as_of_block": 120},
         "onchain_total_supply": "950", "replay_net": "950", "chain": "bsc",
         "inputs": {"replay_stats": {
             "path": "data/replay_stats.json",
             "sha256": hashlib.sha256(stats.read_bytes()).hexdigest(),
             "size": stats.stat().st_size}}}))


def write_facts_source(td: Path):
    (td / "facts.json").write_text(json.dumps(
        {"token": {"symbol": "TT", "decimals": 0, "total_supply_raw": "950"},
         "entities": {"e1": {"label": "大庄#1", "addresses": [B],
                             "current_raw": "350", "peak_raw": "400"}}}))
    (td / "source.json").write_text(json.dumps(
        {"schema": "analysis-state-source/v1",
         "token": {"chain": "bsc", "data_cutoff": "2026-01-04T23:59:59Z",
                   "skill_version": "6.39.5"},
         "entity_annotations": {"e1": {"type": "single", "status": "holding"}},
         "address_balances": {B: "350"}, "vault_addresses": [],
         "provenance": {"skill_commit": "batchc", "data_sources": ["replay"]}}))


def compile_state_cli(td: Path, *extra):
    return run([ROOT / "scripts/report/state_from_facts.py", "--facts", "facts.json",
                "--source", "source.json", "--out", "analysis-state.json",
                *extra], td)


def t_f05_evm_engines():
    """两 EVM 引擎同批同深度：重复 spec 双双 exit 2；合法 spec 双双照常出货。"""
    dup_spec = {"camps": {"camp_A": [A], "camp_B": [A]}, "entities": {}}
    ok_spec = {"camps": {"项目方": [A], "大庄": [B]}, "entities": {"实体X": [B]}}
    with tempfile.TemporaryDirectory() as s:
        td = Path(s)
        p = build_evm_case(td, dup_spec, expect_rc=2)
        check("F05 replay_duck 跨营重复 exit2", "camp-spec" in p.stderr, p.stderr[-300:])
    with tempfile.TemporaryDirectory() as s:
        td = Path(s)
        build_evm_case(td, ok_spec)
        # 同一 merged 数据喂旧引擎 replay_pass2（需 merged.csv）——重跑带 --emit-csv
        p = run([ROOT / "scripts/evm/replay_duck.py", "--channels", "channels.json",
                 "--out-dir", "data", "--emit-csv"], td)
        assert p.returncode == 0, p.stderr[-300:]
        (td / "camps_dup.json").write_text(json.dumps(dup_spec, ensure_ascii=False))
        p = run([ROOT / "scripts/evm/replay_pass2.py", "camps_dup.json",
                 "--data-dir", "data"], td)
        check("F05 replay_pass2 跨营重复 exit2",
              p.returncode == 2 and "camp-spec" in p.stderr,
              f"rc={p.returncode} {p.stderr[-300:]}")
        p = run([ROOT / "scripts/evm/replay_pass2.py", "camps.json",
                 "--data-dir", "data"], td)
        check("F05 replay_pass2 合法 spec 绿例", p.returncode == 0, p.stderr[-300:])
        check("F04 replay_pass2 sidecar 落盘",
              (td / "data/camp_series.provenance.json").is_file()
              and (td / "data/entity_series.provenance.json").is_file())


def t_f04_evm_chain():
    """EVM 端到端（含 burn 的 dead-sink 型绿例）＋sidecar/登记面/末点对账反例族。"""
    ok_spec = {"camps": {"项目方": [A], "大庄": [B]}, "entities": {"实体X": [B]}}
    with tempfile.TemporaryDirectory() as s:
        td = Path(s)
        build_evm_case(td, ok_spec)
        sc = td / "data/camp_series.provenance.json"
        check("F04 replay_duck sidecar 落盘", sc.is_file())
        doc = json.loads(sc.read_text())
        check("F04 sidecar 键面完整",
              doc["schema"] == "camp-series-provenance/v1"
              and doc["series_format"] == "evm-dict"
              and doc["camps_spec"]["sha256"] and doc["final_balances"]["sha256"]
              and doc["inputs"]["replay_stats"]["sha256"], json.dumps(doc)[:200])
        write_supply_truth(td)
        write_facts_source(td)

        # 绿例：全链 PASS（burn 案：burn_cum_pct 5.2632、非 burn 桶闭合 100）
        p = compile_state_cli(td, "--series-source", "data/camp_series.json")
        check("F04 EVM 端到端绿例（含 burn）", p.returncode == 0, p.stdout + p.stderr)
        st = json.loads((td / "analysis-state.json").read_text())
        check("F04 state 注入 sidecar 溯源",
              st["provenance"]["camp_series_sidecar"]["producer"]
              == "scripts/evm/replay_duck.py")
        check("F04 转换器丢 _meta 保 burn_cum_pct",
              "_meta" not in st["camp_share_series"]["series"]
              and "burn_cum_pct" in st["camp_share_series"]["series"])

        # 反例：缺 sidecar
        os.rename(sc, td / "data/camp_series.provenance.json.bak")
        p = compile_state_cli(td, "--series-source", "data/camp_series.json")
        check("F04 缺 sidecar 拒", p.returncode == 2 and "sidecar" in p.stdout,
              p.stdout)
        os.rename(td / "data/camp_series.provenance.json.bak", sc)

        # 反例：序列落盘后被改动（输出 sha 绑定）
        series_path = td / "data/camp_series.json"
        original = series_path.read_text()
        tampered = json.loads(original)
        tampered["大庄"][-1] = 30.0
        tampered["散户"][-1] = round(100 - tampered["项目方"][-1] - 30.0, 4)
        series_path.write_text(json.dumps(tampered, ensure_ascii=False))
        p = compile_state_cli(td, "--series-source", "data/camp_series.json")
        check("F04 序列篡改被输出 sha 拦", p.returncode == 2
              and "sha256 与 sidecar 登记不一致" in p.stdout, p.stdout)

        # 反例：伪序列＋自造 sidecar（sha 全自洽、登记面也命中）→ 末点对账独立拦截
        from camp_series_provenance import write_series_sidecar
        write_series_sidecar(series_path, producer="scripts/evm/replay_duck.py",
                             series_format="evm-dict",
                             denominator="current_net_supply",
                             camps_spec_path=td / "camps.json",
                             final_balances_path=td / "data/balances_final.json",
                             inputs={"replay_stats": td / "data/replay_stats.json"})
        p = compile_state_cli(td, "--series-source", "data/camp_series.json")
        check("F04 伪序列双喂被末点对账拦", p.returncode == 2
              and "末点对账失败" in p.stdout, p.stdout)
        series_path.write_text(original)
        write_series_sidecar(series_path, producer="scripts/evm/replay_duck.py",
                             series_format="evm-dict",
                             denominator="current_net_supply",
                             camps_spec_path=td / "camps.json",
                             final_balances_path=td / "data/balances_final.json",
                             inputs={"replay_stats": td / "data/replay_stats.json"})

        # 反例：camps spec 落盘后被改——等长篡改（B→C 同长）打 sha 分支，
        # 增长篡改打 size 分支（三验的两个失败分支都要命中）
        camps_path = td / "camps.json"
        camps_orig = camps_path.read_text()
        camps_path.write_text(camps_orig.replace(B, C))
        p = compile_state_cli(td, "--series-source", "data/camp_series.json")
        check("F04 spec 等长篡改被 sha 三验拦", p.returncode == 2
              and "camps_spec sha256 不匹配" in p.stdout, p.stdout)
        camps_path.write_text(json.dumps(
            {"camps": {"项目方": [A, C], "大庄": [B]}, "entities": {}},
            ensure_ascii=False))
        p = compile_state_cli(td, "--series-source", "data/camp_series.json")
        check("F04 spec 增长篡改被 size 三验拦", p.returncode == 2
              and "camps_spec size 不匹配" in p.stdout, p.stdout)
        camps_path.write_text(camps_orig)

        # 反例：登记面缺席 / replay_stats 不命中
        st_path = td / "supply_truth.json"
        st_orig = st_path.read_text()
        st_path.unlink()
        p = compile_state_cli(td, "--series-source", "data/camp_series.json")
        check("F04 无 supply_truth 拒", p.returncode == 2
              and "supply_truth" in p.stdout, p.stdout)
        st_obj = json.loads(st_orig)
        st_obj["inputs"]["replay_stats"]["sha256"] = "0" * 64
        st_path.write_text(json.dumps(st_obj))
        p = compile_state_cli(td, "--series-source", "data/camp_series.json")
        check("F04 replay_stats sha 未命中登记面拒", p.returncode == 2
              and "inputs.replay_stats.sha256" in p.stdout, p.stdout)
        st_path.write_text(st_orig)

        # 反例：source 手填 series 与 producer 转换结果分叉
        src_obj = json.loads((td / "source.json").read_text())
        src_obj["camp_share_series"] = {"dates": ["2026-01-01"],
                                        "series": {"大庄": [40.0], "散户": [60.0]}}
        (td / "source.json").write_text(json.dumps(src_obj, ensure_ascii=False))
        p = compile_state_cli(td, "--series-source", "data/camp_series.json")
        check("F04 手填 series 与 producer 分叉拒", p.returncode == 2
              and "只有一个事实源" in p.stdout, p.stdout)
        write_facts_source(td)

        # 绿例回归：反例注入全部还原后整链仍 PASS（防测试自身留脏）
        p = compile_state_cli(td, "--series-source", "data/camp_series.json")
        check("F04 反例还原后整链复绿", p.returncode == 0, p.stdout + p.stderr)


# ── Solana 真实产物链（replay_edges reconcile+evolution，含 burn）──────


def t_f05_f04_solana_chain():
    from camp_series_provenance import write_series_sidecar  # noqa: F401 (对称导入)
    edges = [
        [3600, 1, 0, -1, Z, SA, 1000],      # mint 1000 -> SA
        [7200, 2, 0, -1, SA, SB, 300],
        [10800, 3, 0, -1, SA, Z, 100],      # burn 100 → net 900
    ]
    old = os.getcwd()
    with tempfile.TemporaryDirectory(prefix="c-f09-sol-", dir="/private/tmp") as s:
        td = Path(s)
        os.chdir(td)
        try:
            import importlib
            import replay_edges as re_mod
            importlib.reload(re_mod)
            Path("data").mkdir()
            edge_key = hashlib.sha256(SA.encode("utf-8")).hexdigest()
            write_sol_edges(Path(f"data/soltx-{edge_key}.jsonl.gz"), edges)
            Path("data/holders_owners.json").write_text(
                json.dumps({SA: 600, SB: 300}))
            owners_ref = file_ref(Path("data/holders_owners.json"))
            Path("data/holders_snapshot_meta.json").write_text(
                json.dumps({"schema": "solana-holder-snapshot-v2", "mint": SA,
                            "target": {"chain": "solana", "token": SA,
                                       "as_of_block": 3},
                            "closed": True, "supply_raw": "900",
                            "outputs": {"holders_owners": owners_ref}}))
            cache_meta = Path(f"data/soltx-{edge_key}.meta.json")
            cache_meta.write_text(json.dumps(formal_sol_meta(SA, 1, 3, edges)))
            check("SOL reconcile gate_pass",
                  run_reconcile_v4(re_mod, edges, 1, mint=SA,
                                   cache_meta_path=cache_meta) is True)

            # F-05：缺 camps 文件硬拒（rg 定案）；显式空 spec {} 合法
            try:
                run_evolution_v4(re_mod, edges, 1, "camps.json", set())
                check("F05 evolution 缺 camps 硬拒", False, "缺文件被接受")
            except SystemExit as exc:
                check("F05 evolution 缺 camps 硬拒", exc.code == 2, f"{exc.code}")
            Path("camps_dup.json").write_text(
                json.dumps({"营1": [SA], "营2": [SA]}, ensure_ascii=False))
            try:
                run_evolution_v4(re_mod, edges, 1, "camps_dup.json", set())
                check("F05 evolution 跨营重复硬拒", False, "重复被接受")
            except SystemExit as exc:
                check("F05 evolution 跨营重复硬拒", exc.code == 2, f"{exc.code}")
            Path("camps_empty.json").write_text("{}")
            run_evolution_v4(re_mod, edges, 1, "camps_empty.json", set())
            check("F05 evolution 显式空 spec 合法",
                  Path("data/camp_share_series.json").is_file())

            # 正式 spec 重跑（真实产物形态：行内 锁仓/销毁 桶、_supply_raw 元键）
            Path("camps.json").write_text(
                json.dumps({"项目方": [SA], "大庄": [SB]}, ensure_ascii=False))
            run_evolution_v4(re_mod, edges, 1, "camps.json", set())
            rows = json.loads(Path("data/camp_share_series.json").read_text())
            check("SOL 序列行内 burn 桶在场",
                  rows[-1]["锁仓/销毁"] > 0 and "_supply_raw" in rows[-1],
                  json.dumps(rows[-1], ensure_ascii=False))
            sc = Path("data/camp_share_series.provenance.json")
            check("F04 replay_edges sidecar 落盘", sc.is_file())
            doc = json.loads(sc.read_text())
            check("F04 sol sidecar 绑 reconcile+effective",
                  doc["series_format"] == "sol-rows"
                  and doc["inputs"].get("reconcile_receipt")
                  and doc["final_balances"]["path"] == "effective_balances.json",
                  json.dumps(doc)[:300])

            # consumer 全链（Solana burn 案绿例：锁仓/销毁≈11.11% 口径感知通过）
            Path("facts.json").write_text(json.dumps(
                {"token": {"symbol": "ST", "decimals": 0,
                           "total_supply_raw": "900"},
                 "entities": {"e1": {"label": "大庄#1", "addresses": [SB],
                                     "current_raw": "300", "peak_raw": "300"}}}))
            Path("source.json").write_text(json.dumps(
                {"schema": "analysis-state-source/v1",
                 "token": {"chain": "solana",
                           "mint": SA, "data_cutoff_slot": 3,
                           "data_cutoff": "2026-01-05T00:00:00Z",
                           "skill_version": "6.39.5"},
                 "entity_annotations": {"e1": {"type": "single",
                                               "status": "holding"}},
                 "address_balances": {SB: "300"}, "vault_addresses": [],
                 "provenance": {"skill_commit": "batchc",
                                "data_sources": ["sqd"]}}))
            p = compile_state_cli(td, "--series-source",
                                  "data/camp_share_series.json")
            check("F04 Solana 端到端绿例（含 burn）", p.returncode == 0,
                  p.stdout + p.stderr)
            st = json.loads(Path("analysis-state.json").read_text())
            check("F04 sol 转换器：锁仓/销毁保留、_supply_raw 剔除、ts 转 ISO",
                  "锁仓/销毁" in st["camp_share_series"]["series"]
                  and "_supply_raw" not in st["camp_share_series"]["series"]
                  and st["camp_share_series"]["dates"][0].endswith("Z"))

            # F-09 原反例：净供给相同的乙案只改 target mint，甲案 v3 receipt/sidecar
            # 整体复制（sidecar 哈希已自洽）也必须由编译调用点的预期身份拒绝。
            source_path = Path("source.json")
            source_orig = source_path.read_text()
            other = json.loads(source_orig)
            other["token"]["mint"] = SA.lower()
            source_path.write_text(json.dumps(other))
            p = compile_state_cli(td, "--series-source", "data/camp_share_series.json")
            check("F09 state_from_facts 跨案 receipt 复制拒",
                  p.returncode == 2 and "大小写敏感" in p.stdout, p.stdout)
            source_path.write_text(source_orig)

            # 发布调用点独立取 reconciliation target；不能复用编译时 source 自报。
            from audit_release_gate import check_series_binding
            errors = []
            check_series_binding(td, st, errors, expected_target={
                "chain": "solana", "token": SA.lower(), "as_of_block": 3})
            check("F09 audit_release_gate 独立身份校验命中",
                  any("大小写敏感" in x for x in errors), errors)

            rr = Path("data/reconcile_receipt.json")
            rr_orig = rr.read_text()

            def receipt_rejected(name, mutate, needle):
                doc = json.loads(rr_orig)
                mutate(doc)
                rr.write_text(json.dumps(doc))
                run_evolution_v4(re_mod, edges, 1, "camps.json", set())
                got = compile_state_cli(td, "--series-source",
                                        "data/camp_share_series.json")
                check(name, got.returncode == 2, got.stdout)
                rr.write_text(rr_orig)
                run_evolution_v4(re_mod, edges, 1, "camps.json", set())

            receipt_rejected("F09 身份键缺失拒", lambda d: d.pop("mint"), "mint")
            receipt_rejected("F09 mint 不符拒", lambda d: d.update(mint=SB), "mint")
            receipt_rejected("F09 mint 大小写变体拒",
                             lambda d: d.update(mint=SA.lower()), "大小写敏感")
            receipt_rejected("F09 producer path 错拒",
                             lambda d: d["producer"].update(path="replay_edges.py"),
                             "producer")
            receipt_rejected("F09 producer sha 错拒",
                             lambda d: d["producer"].update(sha256="0" * 64),
                             "producer")
            receipt_rejected("F09 edge digest 改写拒",
                             lambda d: d.update(edge_digest="0" * 64),
                             "edge_digest")
            receipt_rejected("F09 edge count 改写拒",
                             lambda d: d.update(edge_count=d["edge_count"] + 1),
                             "edge_digest/edge_count")
            receipt_rejected("F09 extrema 越窗拒",
                             lambda d: d["edge_extrema"]["last"].update(slot=4),
                             "edge_extrema")
            receipt_rejected("F09 v2 存量 fail-closed",
                             lambda d: d.update(schema="solana-reconcile/v2"),
                             "重跑 replay_edges reconcile")

            # 同 mint 不同 cutoff：收据窗口本身可早于 cutoff，但 snapshot 必须是
            # 同一案 target；这里只改编译案 target，必须拒绝。
            other = json.loads(source_orig)
            other["token"]["data_cutoff_slot"] = 4
            source_path.write_text(json.dumps(other))
            p = compile_state_cli(td, "--series-source", "data/camp_share_series.json")
            check("F09 同 mint 不同 cutoff 拒",
                  p.returncode == 2 and "cutoff" in p.stdout, p.stdout)
            source_path.write_text(source_orig)

            # meta 与 owners 分属两快照：inputs 虽各自三验可过，snapshot 内绑定必须拒。
            other_owners = Path("data/holders_owners_other.json")
            other_owners.write_text(json.dumps({SA: 600, SB: 300}))
            receipt_rejected(
                "F09 meta/owners 快照撕裂拒",
                lambda d: d["inputs"].update(holders_owners=file_ref(other_owners)),
                "撕裂")

            # 反例：reconcile_receipt gate_pass=false → 拒
            bad = json.loads(rr_orig)
            bad["gate_pass"] = False
            rr.write_text(json.dumps(bad))
            run_evolution_v4(re_mod, edges, 1, "camps.json", set())  # 重挂 sidecar 绑新收据
            p = compile_state_cli(td, "--series-source",
                                  "data/camp_share_series.json")
            check("F04 reconcile FAIL 序列拒入编译", p.returncode == 2
                  and "gate_pass" in p.stdout, p.stdout)
            rr.write_text(rr_orig)
            run_evolution_v4(re_mod, edges, 1, "camps.json", set())
            p = compile_state_cli(td, "--series-source",
                                  "data/camp_share_series.json")
            check("F04 sol 反例还原后复绿", p.returncode == 0, p.stdout + p.stderr)

            # F-09 层 a：同一 Solana 夹具案继续走 figures→A4 finalize→A5 seal。
            # 不另建第二案，也不复制别案 seal/figure 产物。
            from formal_ready_test_harness import run_formal_script
            want = 300 / 900 * 100
            write_json(Path("whale_series.json"), [
                {"entity_id": "e1", "label": "大庄#1", "pct": [round(want, 4)]}])
            figures = ROOT / "scripts/report/figures_from_facts.py"
            p = run([figures, "check", "--facts", "facts.json",
                     "--series", "whale_series.json"], td)
            fig_receipt = Path("figure2_check_receipt.json")
            check("F09 Solana 同案 ② figures check",
                  p.returncode == 0 and fig_receipt.is_file()
                  and json.loads(fig_receipt.read_text()).get("verdict") == "PASS",
                  p.stdout + p.stderr)

            write_json(Path("supply_truth.json"), {
                "schema": "supply-truth-receipt/v3", "verdict": "PASS",
                "exit_code": 0, "chain": "solana",
                "target": {"chain": "solana", "token": SA, "as_of_block": 3},
                "onchain_total_supply": "900", "replay_net": "900"})
            write_json(Path("data_map.json"), {"files": [{
                "path": "data/holders_owners.json",
                "sha256": hashlib.sha256(
                    Path("data/holders_owners.json").read_bytes()).hexdigest()}]})
            write_json(Path("candidate_screening.json"),
                       {"auto_excluded_candidate": []})
            dist = ROOT / "scripts/report/holder_distribution_scan.py"
            p = run_formal_script(dist, ["--case-dir", str(td), "--stage", "initial"])
            assert p.returncode == 0, p.stdout + p.stderr

            Path("findings.md").write_text("# findings\n大庄#1 现仓 300。\n",
                                           encoding="utf-8")
            write_json(Path("identity_gate.json"),
                       {"chain": "solana", "verdict": "PASS"})
            gate = ROOT / "scripts/report/a4_gate.py"
            claims = write_json(Path("claims_in.json"), [{
                "id": "C1", "text": "大庄#1 现仓 300（33.33% 供应）",
                "files": ["data/effective_balances.json"],
                "report_locations": ["report.md:1"]}])
            p = run([gate, "register", "--case-dir", str(td),
                     "--claims-file", str(claims)], td)
            assert p.returncode == 0, p.stdout + p.stderr
            verdicts = write_json(Path("verdicts.json"),
                                  [{"id": "C1", "verdict": "CONFIRMED"}])
            p = run([gate, "finalize", "--case-dir", str(td),
                     "--verdicts-file", verdicts.name, "--seal-files",
                     "findings.md,analysis-state.json,facts.json,identity_gate.json,"
                     "figure2_check_receipt.json", "--workflow-type", "new-analysis"], td)
            seal = Path("a4_seal.json")
            check("F09 Solana 同案 ③ A4 finalize",
                  p.returncode == 0 and seal.is_file()
                  and json.loads(seal.read_text()).get("workflow_type") == "new-analysis",
                  p.stdout + p.stderr)

            for name, value in {
                "handoff_manifest.json": {"consumer_min_schema": "handoff/v3",
                                          "status": "READY", "run_id": "f09-sol"},
                "identity_snapshot_receipt.json": {
                    "schema": "identity-snapshot-receipt/v1"},
                "entity_freeze.json": {"schema": "entity-freeze/v1", "revisions": []},
                "membership_ledger.json": {"rows": []},
                "position_ledger.json": {"rows": []},
                "economic_control_ledger.json": {"rows": []},
                "address_classification.json": {"rows": []},
            }.items():
                write_json(Path(name), value)
            p = run_formal_script(dist, ["--case-dir", str(td), "--stage", "final",
                                         "--round", "1"])
            assert p.returncode == 0, p.stdout + p.stderr
            p = run_formal_script(dist, [
                "record-round", "--case-dir", str(td), "--scan",
                "dist_rounds/round_1/distribution_scan.json"])
            assert p.returncode == 0, p.stdout + p.stderr
            final_scan = json.loads(
                Path("dist_rounds/round_1/distribution_scan.json").read_text())
            sentence = ("形态统计因样本不足未做,以逐址集中度事实替代"
                        if final_scan.get("not_evaluable_reason") == "low_sample"
                        else "当前快照呈正常形态;这只表示本闸未检出结构性畸形,不等于没有庄。")
            # 批 1 A5 v3 把图 1 legend receipt 纳入 new-analysis 必经信任根；
            # 此处必须走真实 fig1 producer，不能手补收据或放宽 A5 守卫。
            fig1 = Path("charts/final/fig1.png")
            p = run([figures, "fig1", "--state", "analysis-state.json",
                     "--out", str(fig1)], td)
            check("F09 Solana 同案 ④ fig1/legend receipt",
                  p.returncode == 0 and fig1.is_file()
                  and Path("fig1_legend_receipt.json").is_file(),
                  p.stdout + p.stderr)
            report = Path("report.md")
            report.write_text(
                "# Solana 同案端到端报告\n大庄#1 现仓 300。\n" + sentence
                + "\n\n![阵营演变](charts/final/fig1.png)\n"
                + "\n![持仓分布](charts/final/holder_distribution_current.png)\n",
                encoding="utf-8")
            a5 = ROOT / "scripts/report/a5_report_seal.py"
            p = run_formal_script(a5, ["--case-dir", str(td), "--report", str(report),
                                       "--a4-seal", str(seal), "--out",
                                       str(Path("a5_report_seal.json"))])
            check("F09 Solana 同案 ⑤ A5 seal（state→figures→A4→A5）",
                  p.returncode == 0 and Path("a5_report_seal.json").is_file(),
                  p.stdout + p.stderr)
        finally:
            os.chdir(old)


# ── build_evolution（第四族）CLI 面 ──────────────────────────────


def t_f05_f04_build_evolution():
    old = os.getcwd()
    with tempfile.TemporaryDirectory() as s:
        td = Path(s)
        os.chdir(td)
        try:
            Path("config.json").write_text(json.dumps(
                {"total_supply": 1000, "decimals": 0, "launch_ts": 1000,
                 "data_cutoff_ts": 2000}))
            Path("data").mkdir()
            Path("data/whale_deep.json").write_text(json.dumps(
                {SA: {"rows": [{"blockTime": 1500, "delta_raw": 100}]}}))
            Path("data/decoded_anchors.jsonl").write_text(
                json.dumps({"ts": 1500, "pool_balance": 50,
                            "pool_balance_raw": 50}) + "\n")
            # F-05 原反例：JSON 重复键（同址两阵营）在解析层拒
            Path("data/entity_camps.json").write_text(
                '{"%s": "项目方", "%s": "大庄"}' % (SA, SA))
            p = run([ROOT / "scripts/solana/build_evolution.py"], td)
            check("F05 build_evolution JSON 重复键 exit2",
                  p.returncode == 2 and "重复键" in p.stderr,
                  f"rc={p.returncode} {p.stderr[-300:]}")
            # 绿例＋sidecar（sol-anchor-rows）
            Path("data/entity_camps.json").write_text(
                json.dumps({SA: "项目方"}, ensure_ascii=False))
            p = run([ROOT / "scripts/solana/build_evolution.py"], td)
            check("F05 build_evolution 合法绿例", p.returncode == 0,
                  p.stderr[-300:])
            sc = Path("data/camp_series.provenance.json")
            check("F04 build_evolution sidecar 落盘（四族等深）",
                  sc.is_file() and json.loads(sc.read_text())["series_format"]
                  == "sol-anchor-rows")
            # sol-anchor-rows 不入正式编译链（小样本辅助件、无对账链锚）
            Path("facts.json").write_text(json.dumps(
                {"token": {"symbol": "ST", "decimals": 0,
                           "total_supply_raw": "1000"},
                 "entities": {"e1": {"label": "大庄#1", "addresses": [SB],
                                     "current_raw": "1", "peak_raw": "1"}}}))
            Path("source.json").write_text(json.dumps(
                {"schema": "analysis-state-source/v1",
                 "token": {"chain": "solana", "data_cutoff": "x",
                           "skill_version": "6.39.5"},
                 "entity_annotations": {"e1": {"type": "single",
                                               "status": "holding"}},
                 "address_balances": {SB: "1"}, "vault_addresses": [],
                 "provenance": {"skill_commit": "c", "data_sources": ["a"]}}))
            p = compile_state_cli(td, "--series-source", "data/camp_series.json")
            check("F04 sol-anchor-rows 拒入正式编译", p.returncode == 2
                  and "不接入正式编译链" in p.stdout, p.stdout)
        finally:
            os.chdir(old)


# ── F-04 数值面单元族（白名单/值域/闭合/日期轴）──────────────────────


def t_f04_payload_unit():
    from camp_series_provenance import (SeriesProvenanceError,
                                        validate_series_payload)
    import standard_charts as scharts

    # CAMP_ORDER 拆分：合并保原序（与拆分前清单逐项快照比对）＋白名单同源 import
    expected = ["项目方", "大庄", "小庄", "离场庄", "刷量地址", "CEX资金通道",
                "CEX托管", "疑似CEX托管", "流动性池", "其他大户", "历史大户",
                "散户", "桥锁仓", "锁仓/销毁", "狙击集团", "庄家TOP1",
                "庄家其他组", "首30分钟狙击者", "其他散户", "销毁"]
    check("F04 CAMP_ORDER 合并保原序", scharts.CAMP_ORDER == expected,
          str(scharts.CAMP_ORDER))
    check("F04 两段无重叠且并集=全量",
          not set(scharts.CAMP_ORDER_MODERN) & set(scharts.CAMP_ORDER_LEGACY)
          and scharts.CAMP_ORDER_MODERN + scharts.CAMP_ORDER_LEGACY
          == scharts.CAMP_ORDER)
    from camp_series_provenance import modern_camp_whitelist
    check("F04 白名单=现代段同源 import（禁手抄）",
          modern_camp_whitelist() == set(scharts.CAMP_ORDER_MODERN))

    def rejected(css, needle):
        try:
            validate_series_payload(css)
            return False, "accepted"
        except SeriesProvenanceError as exc:
            return needle in str(exc), str(exc)

    def cs(dates, series):
        return {"dates": dates, "series": series}

    # F-04 最小反例：注入 -899 / 999 的自报数字
    ok, msg = rejected(cs(["2026-01-01"], {"大庄": [-899.0], "散户": [999.0]}),
                       "为负")
    check("F04 负值拒", ok, msg)
    ok, msg = rejected(cs(["2026-01-01"], {"大庄": [999.0], "散户": [0.0]}),
                       "超出 100")
    check("F04 超 100 拒", ok, msg)
    ok, msg = rejected(cs(["2026-01-01"], {"大庄": [float("nan")], "散户": [100.0]}),
                       "非有限")
    check("F04 NaN 拒", ok, msg)
    ok, msg = rejected(cs(["2026-01-01"], {"大庄": [30.0], "散户": [30.0]}),
                       "不闭合")
    check("F04 合计 60 不闭合拒", ok, msg)
    ok, msg = rejected(cs(["2026-01-01"], {"大庄": [80.0], "散户": [50.0]}),
                       "不闭合")
    check("F04 合计 130 不闭合拒", ok, msg)
    ok, msg = rejected(cs(["2026-01-01"], {"狙击集团": [40.0], "散户": [60.0]}),
                       "白名单外")
    check("F04 legacy 桶名拒", ok, msg)
    ok, msg = rejected(cs(["2026-01-01"], {"大庄Gate": [40.0], "散户": [60.0]}),
                       "白名单外")
    check("F04 实体级自造桶名拒（TAG 实测形态）", ok, msg)
    # 日期轴族
    ok, msg = rejected(cs(["2026-01-02", "2026-01-01"],
                          {"大庄": [40.0, 40.0], "散户": [60.0, 60.0]}), "非严格递增")
    check("F04 日期倒序拒", ok, msg)
    ok, msg = rejected(cs(["2026-01-01", "2026-01-01"],
                          {"大庄": [40.0, 40.0], "散户": [60.0, 60.0]}), "非严格递增")
    check("F04 日期重复拒", ok, msg)
    ok, msg = rejected(cs(["2026-13-45"], {"大庄": [40.0], "散户": [60.0]}),
                       "无法按 UTC 解析")
    check("F04 非法日期拒", ok, msg)
    # 时区换算后倒挂：+08:00 的 09:00 = UTC 01:00，早于前一点 UTC 02:00
    ok, msg = rejected(cs(["2026-01-01T02:00:00", "2026-01-01T09:00:00+08:00"],
                          {"大庄": [40.0, 40.0], "散户": [60.0, 60.0]}), "非严格递增")
    check("F04 时区换算倒挂拒（naive-aware 混用）", ok, msg)
    # 绿例族
    validate_series_payload(cs(["2026-01-01T01:00:00", "2026-01-01T10:00:00+08:00"],
                               {"大庄": [40.0, 40.0], "散户": [60.0, 60.0]}))
    check("F04 naive-aware 混用 UTC 轴递增绿例", True)
    validate_series_payload(cs(["2028-02-28", "2028-02-29", "2028-03-01"],
                               {"大庄": [40.0] * 3, "散户": [60.0] * 3}))
    check("F04 闰日绿例", True)
    validate_series_payload(cs(["2026-01-01", "2026-01-02"],
                               {"大庄": [0.0, 40.0], "散户": [0.0, 60.0]}))
    check("F04 全零点（供应未产生）豁免绿例", True)
    # burn 双式闭合：净分母族（非 burn=100，burn 桶另计、可 >100）
    validate_series_payload(cs(["2026-01-01"],
                               {"大庄": [40.0], "散户": [60.0],
                                "burn_cum_pct": [120.0]}))
    check("F04 净分母 burn>100 合法绿例", True)
    # total 分母族（锁仓/销毁参与闭合：40+40+20=100）
    validate_series_payload(cs(["2026-01-01"],
                               {"大庄": [40.0], "散户": [40.0],
                                "锁仓/销毁": [20.0]}))
    check("F04 total 分母 burn 参与闭合绿例", True)
    # 两式都不中：40+40+锁仓30 → 非burn 80、全桶 110
    ok, msg = rejected(cs(["2026-01-01"], {"大庄": [40.0], "散户": [40.0],
                                           "锁仓/销毁": [30.0]}), "不闭合")
    check("F04 双式均不中拒", ok, msg)
    # burn 桶负值仍拒（豁免只豁闭合与上界，不豁非负有限）
    ok, msg = rejected(cs(["2026-01-01"], {"大庄": [40.0], "散户": [60.0],
                                           "burn_cum_pct": [-1.0]}), "为负")
    check("F04 burn 桶负值拒", ok, msg)


def t_fixround1():
    """消化轮第 1 轮（F-C1~F-C6）回归。EVM 真跑链复用 build_evm_case。"""
    from camp_series_provenance import (SeriesProvenanceError, closure_mode_for,
                                        validate_series_payload,
                                        write_series_sidecar)
    ok_spec = {"camps": {"项目方": [A], "大庄": [B]}, "entities": {"实体X": [B]}}
    with tempfile.TemporaryDirectory() as s:
        td = Path(s)
        build_evm_case(td, ok_spec)
        write_supply_truth(td)
        write_facts_source(td)

        # F-C1 原反例：手编"5%→88.8% 吸筹"序列、不带 --series-source → 拒
        src_obj = json.loads((td / "source.json").read_text())
        src_obj["camp_share_series"] = {
            "dates": ["2026-08-01", "2026-08-02", "2026-08-03"],
            "series": {"项目方": [5.0, 40.0, 88.8], "散户": [95.0, 60.0, 11.2]}}
        (td / "source.json").write_text(json.dumps(src_obj, ensure_ascii=False))
        p = compile_state_cli(td)
        check("FC1 手编序列无绑定被 formal 必经拒", p.returncode == 2
              and "--series-source" in p.stdout, p.stdout)
        # exploration 显式豁免 → 放行但产物带非正式标记
        p = compile_state_cli(td, "--exploration")
        check("FC1 exploration 放行且落非正式标记", p.returncode == 0, p.stdout)
        st = json.loads((td / "analysis-state.json").read_text())
        check("FC1 exploration 标记 exploration-unbound",
              st["provenance"]["series_binding"] == "exploration-unbound"
              and "camp_series_sidecar" not in st["provenance"],
              json.dumps(st["provenance"], ensure_ascii=False))
        # source 预置伪 formal 标记 → 拒（标记只能编译器生成）
        src_obj["provenance"] = {"skill_commit": "c", "data_sources": ["d"],
                                 "series_binding": "producer-sidecar"}
        (td / "source.json").write_text(json.dumps(src_obj, ensure_ascii=False))
        p = compile_state_cli(td, "--exploration")
        check("FC1 预置绑定标记被拒", p.returncode == 2 and "预置" in p.stdout,
              p.stdout)
        write_facts_source(td)
        # formal 绑定绿例：产物带 producer-sidecar 标记
        p = compile_state_cli(td, "--series-source", "data/camp_series.json")
        check("FC1 formal 绑定绿例", p.returncode == 0, p.stdout + p.stderr)
        st = json.loads((td / "analysis-state.json").read_text())
        check("FC1 formal 标记 producer-sidecar",
              st["provenance"]["series_binding"] == "producer-sidecar")

        # F-C1 下游闸（audit_release_gate.check_series_binding 单元级）
        import audit_release_gate as gate
        errs = []
        gate.check_series_binding(td, st, errs)
        # state 绑定的序列实物在 data/ 层 → 应零错
        check("FC1 下游闸 producer-sidecar 绿例", errs == [], str(errs))
        errs = []
        bad_st = json.loads(json.dumps(st))
        bad_st["provenance"]["series_binding"] = "exploration-unbound"
        gate.check_series_binding(td, bad_st, errs)
        check("FC1 下游闸拒 exploration 产物",
              any("producer-sidecar" in x for x in errs), str(errs))
        errs = []
        bad_st = json.loads(json.dumps(st))
        del bad_st["provenance"]["series_binding"]
        del bad_st["provenance"]["camp_series_sidecar"]
        gate.check_series_binding(td, bad_st, errs)
        check("FC1 下游闸拒无标记手编 state",
              any("series_binding" in x for x in errs), str(errs))
        errs = []
        bad_st = json.loads(json.dumps(st))
        bad_st["provenance"]["camp_series_sidecar"]["series_sha256"] = "0" * 64
        gate.check_series_binding(td, bad_st, errs)
        check("FC1 下游闸拒实物 sha 不符",
              any("不一致" in x for x in errs), str(errs))
        errs = []
        gate.check_series_binding(td, {"chain": "bsc", "whale_groups": []}, errs)
        check("FC1 下游闸对无序列 state 不强加", errs == [], str(errs))

        # ── 消化轮 2：F-C1 终关（自证式→内容重转换比对）两攻击 ──
        import hashlib as _h2
        series_file = td / "data/camp_series.json"
        real_sha = _h2.sha256(series_file.read_bytes()).hexdigest()
        # 攻击 A（盲审）：exploration/手编 state 手写 producer-sidecar 标记＋自补
        # sidecar 块指向案内真实序列文件（sha/format 全真）——但 state 里的
        # camp_share_series 是伪造的 → 内容重转换比对拒
        fake_state = {
            "camp_share_series": {"dates": ["2026-08-01"],
                                  "series": {"项目方": [88.8], "散户": [11.2]}},
            "provenance": {"series_binding": "producer-sidecar",
                           "camp_series_sidecar": {
                               "producer": "scripts/evm/replay_duck.py",
                               "series_file": "camp_series.json",
                               "series_sha256": real_sha,
                               "series_format": "evm-dict"}}}
        errs = []
        gate.check_series_binding(td, fake_state, errs)
        check("FC1终关 攻击A：伪 state 自补真 sidecar 块被内容比对拒",
              any("重转换" in x for x in errs), str(errs))
        # 攻击 B（盲审）：formal 合法产物编译后篡改 camp_share_series 一个值
        # （provenance 原样不动）→ 内容重转换比对拒
        tampered_state = json.loads(json.dumps(st))
        tampered_state["camp_share_series"]["series"]["大庄"][-1] = 30.0
        errs = []
        gate.check_series_binding(td, tampered_state, errs)
        check("FC1终关 攻击B：编译后篡改 series 被内容比对拒",
              any("重转换" in x for x in errs), str(errs))
        # 绑定块缺 series_format（旧轮 1 产物/伪造块）→ 拒
        no_fmt = json.loads(json.dumps(st))
        del no_fmt["provenance"]["camp_series_sidecar"]["series_format"]
        errs = []
        gate.check_series_binding(td, no_fmt, errs)
        check("FC1终关 绑定块缺 series_format 拒",
              any("series_format" in x for x in errs), str(errs))

        # ── 消化轮 3（N-C4）：同步一致造假——发布期复算整条来源链 ──
        # 攻击 C'（盲审原样）：自造原生格式序列文件＋state 用它的转换结果＋
        # 绑定块自填（sha/format 全自洽）——轮 2 的重转换比对必然通过，
        # 必须被"sidecar 实物强制在场"拦下
        from camp_series_provenance import series_to_state_form
        fake_native = {"dates": ["2026-01-01", "2026-01-02"],
                       "项目方": [5.0, 88.8], "散户": [95.0, 11.2]}
        fake_path = td / "data/camp_series_v2.json"
        fake_path.write_text(json.dumps(fake_native, ensure_ascii=False))
        fake_sha = _h2.sha256(fake_path.read_bytes()).hexdigest()
        sync_fake = {
            "camp_share_series": series_to_state_form(fake_native, "evm-dict"),
            "provenance": {"series_binding": "producer-sidecar",
                           "camp_series_sidecar": {
                               "producer": "scripts/evm/replay_duck.py",
                               "series_file": "camp_series_v2.json",
                               "series_sha256": fake_sha,
                               "series_format": "evm-dict"}}}
        errs = []
        gate.check_series_binding(td, sync_fake, errs)
        check("NC4 同步一致造假被 sidecar 实物强制拦下",
              any("provenance sidecar" in x for x in errs), str(errs))
        # 强化：连 sidecar 也自造（公开函数）且绑真 replay_stats/spec/终态快照
        # → 登记面全过，但伪末点被末点对账复算拦死（最后一层机器可闭合边界）
        from camp_series_provenance import write_series_sidecar
        write_series_sidecar(fake_path, producer="scripts/evm/replay_duck.py",
                             series_format="evm-dict",
                             denominator="current_net_supply",
                             camps_spec_path=td / "camps.json",
                             final_balances_path=td / "data/balances_final.json",
                             inputs={"replay_stats": td / "data/replay_stats.json"})
        errs = []
        gate.check_series_binding(td, sync_fake, errs)
        check("NC4 自造 sidecar 全套绑真件仍被末点对账复算拦下",
              any("末点对账失败" in x for x in errs), str(errs))
        fake_path.unlink()
        (td / "data/camp_series_v2.provenance.json").unlink()
        # 误伤三查①：formal 正常产物（案内 sidecar/supply_truth/preflight 全链
        # 在场）发布期复算零 error——上方 "FC1 下游闸 producer-sidecar 绿例"
        # 在本轮已含三件套复算，此处显式复跑一次坐实
        errs = []
        gate.check_series_binding(td, st, errs)
        check("NC4 误伤查① formal 正常产物复算放行", errs == [], str(errs))
        # 误伤三查②③（无序列 state 不强加 / exploration 标记拒）由既有
        # "FC1 下游闸对无序列 state 不强加" 与 "FC1 下游闸拒 exploration 产物"
        # 两 check 覆盖（本轮语义未变，回归即证）

        # F-C3：伪 supply_truth（46 字节式 {"sha256": ...}）→ 拒；无 schema → 拒
        st_path = td / "supply_truth.json"
        st_orig = st_path.read_text()
        import hashlib as _h
        stats_sha = _h.sha256((td / "data/replay_stats.json").read_bytes()).hexdigest()
        good_target = {"chain": "bsc", "token": A, "as_of_block": 120}
        st_path.write_text(json.dumps({"sha256": stats_sha}))
        p = compile_state_cli(td, "--series-source", "data/camp_series.json")
        check("FC3 任意 JSON 冒充 supply_truth 拒", p.returncode == 2
              and "不是合法供给真值收据" in p.stdout, p.stdout)
        # 带真 schema+target 但 sha 塞在顶层任意位置（修前全文包含式会放行）→ 仍拒
        st_path.write_text(json.dumps(
            {"schema": "supply-truth-receipt/v3", "verdict": "PASS",
             "exit_code": 0, "chain": "bsc", "target": good_target,
             "sha256": stats_sha}))
        p = compile_state_cli(td, "--series-source", "data/camp_series.json")
        check("FC3 sha 不在 inputs.replay_stats 特定位置拒", p.returncode == 2
              and "缺 inputs.replay_stats.sha256" in p.stdout, p.stdout)
        # verdict 非 PASS → 拒
        obj = json.loads(st_orig)
        obj["verdict"] = "FAIL"
        st_path.write_text(json.dumps(obj))
        p = compile_state_cli(td, "--series-source", "data/camp_series.json")
        check("FC3 supply_truth 非 PASS 拒", p.returncode == 2
              and "非 PASS/exit 0" in p.stdout, p.stdout)
        # N-C3（消化轮 2）：盲审 1792B 全套伪造链＝schema/verdict/位绑定全对但
        # **缺 target 三键** → 拒（案身份锚）
        obj = json.loads(st_orig)
        del obj["target"]
        st_path.write_text(json.dumps(obj))
        p = compile_state_cli(td, "--series-source", "data/camp_series.json")
        check("NC3 全套伪造链缺 target 三键拒", p.returncode == 2
              and "缺合法 target 三键" in p.stdout, p.stdout)
        # target 齐但 token 与案内采集链身份件不符（复制他案收据）→ 拒
        obj = json.loads(st_orig)
        obj["target"] = dict(good_target, token="0x" + "f" * 40)
        st_path.write_text(json.dumps(obj))
        p = compile_state_cli(td, "--series-source", "data/camp_series.json")
        check("NC3 target.token 不对案内 preflight 锚拒", p.returncode == 2
              and "channels_preflight" in p.stdout, p.stdout)
        # target.chain 与顶层 chain 撕裂 → 拒
        obj = json.loads(st_orig)
        obj["target"] = dict(good_target, chain="eth")
        st_path.write_text(json.dumps(obj))
        p = compile_state_cli(td, "--series-source", "data/camp_series.json")
        check("NC3 target.chain 与顶层撕裂拒", p.returncode == 2
              and "顶层 chain 不一致" in p.stdout, p.stdout)
        st_path.write_text(st_orig)

        # 小事①（盲审更正变异表第 11 条）：只改序列中间点（末点/桶名/闭合全不变）
        # → 输出 sha 闸独立命中
        series_p = td / "data/camp_series.json"
        orig = series_p.read_text()
        tam = json.loads(orig)
        tam["项目方"][1] = round(tam["项目方"][1] - 1.0, 4)
        tam["散户"][1] = round(tam["散户"][1] + 1.0, 4)
        series_p.write_text(json.dumps(tam, ensure_ascii=False))
        p = compile_state_cli(td, "--series-source", "data/camp_series.json")
        check("FC 中间点篡改被输出 sha 独立拦截", p.returncode == 2
              and "sha256 与 sidecar 登记不一致" in p.stdout, p.stdout)
        series_p.write_text(orig)

        # F-C6：balances_final 缺席 → replay_pass2 生产侧当场硬拒（不再静默少绑）
        p = run([ROOT / "scripts/evm/replay_duck.py", "--channels", "channels.json",
                 "--out-dir", "data", "--emit-csv"], td)
        assert p.returncode == 0, p.stderr[-200:]
        (td / "data/balances_final.json").rename(td / "data/balances_final.bak")
        p = run([ROOT / "scripts/evm/replay_pass2.py", "camps.json",
                 "--data-dir", "data"], td)
        check("FC6 replay_pass2 缺终态快照生产侧硬拒", p.returncode == 2
              and "pass1 终态快照" in p.stderr, f"rc={p.returncode} {p.stderr[-200:]}")
        (td / "data/balances_final.bak").rename(td / "data/balances_final.json")

        # F-C6：sidecar 写入 fsync 对齐 receipt_kernel 先例（源码契约断言）
        import inspect
        import camp_series_provenance as csp_mod
        body = inspect.getsource(csp_mod.write_series_sidecar)
        check("FC6 sidecar 写入含 fsync", "os.fsync" in body and "os.replace" in body)

    # F-C4：闭合互救关死（单元级，sidecar 口径单式）
    check("FC4 净分母口径映射", closure_mode_for("current_net_supply") == "net"
          and closure_mode_for("net_supply") == "net")
    check("FC4 total 口径映射", closure_mode_for("mint_total_legacy") == "total"
          and closure_mode_for("config_total_supply") == "total")

    def rejected(css, mode):
        try:
            validate_series_payload(css, closure_mode=mode)
            return False
        except SeriesProvenanceError:
            return True

    hijack_net = {"dates": ["2026-01-01"],
                  "series": {"大庄": [55.0], "散户": [40.0],
                             "burn_cum_pct": [5.0]}}   # 非burn=95、burn 恰补 5
    check("FC4 净分母族缺口不得靠 burn 蹭 s_all", rejected(hijack_net, "net"))
    check("FC4 同构造在 dual 宽式下确实曾放行（互救实证）",
          not rejected(hijack_net, "dual"))
    hijack_total = {"dates": ["2026-01-01"],
                    "series": {"大庄": [60.0], "散户": [40.0],
                               "锁仓/销毁": [7.0]}}     # s_non=100、s_all=107
    check("FC4 total 族超发不得靠 s_non 蹭过", rejected(hijack_total, "total"))
    check("FC4 burn 案单式绿例（净族）", not rejected(
        {"dates": ["2026-01-01"],
         "series": {"大庄": [40.0], "散户": [60.0], "burn_cum_pct": [120.0]}},
        "net"))
    check("FC4 burn 案单式绿例（total 族）", not rejected(
        {"dates": ["2026-01-01"],
         "series": {"大庄": [40.0], "散户": [40.0], "锁仓/销毁": [20.0]}},
        "total"))
    try:
        closure_mode_for("nonsense")
        check("FC4 未知口径拒", False)
    except SeriesProvenanceError:
        check("FC4 未知口径拒", True)


def t_fc5_receipt_chain():
    """F-C5：check 落收据（PASS/FAIL/exploration 全留痕）＋发布闸复验。"""
    fff = ROOT / "scripts/report/figures_from_facts.py"
    import audit_release_gate as gate
    with tempfile.TemporaryDirectory() as s:
        td = Path(s)
        (td / "facts.json").write_text(json.dumps(
            {"token": {"symbol": "TT", "decimals": 0, "total_supply_raw": "1000"},
             "entities": {"e1": {"label": "大庄#1", "addresses": [A],
                                 "current_raw": "278", "peak_raw": "300"}}}))
        (td / "ws.json").write_text(json.dumps(
            [{"entity_id": "e1", "ts": ["2026-01-01"], "pct": [27.8]}]))
        p = run([fff, "check", "--facts", "facts.json", "--series", "ws.json"], td)
        rcpt_path = td / "figure2_check_receipt.json"
        check("FC5 formal PASS 落收据", p.returncode == 0 and rcpt_path.is_file(),
              p.stdout)
        rcpt = json.loads(rcpt_path.read_text())
        check("FC5 收据字段（formal/默认容差/PASS/双输入 sha）",
              rcpt["schema"] == "figure2-check-receipt/v1"
              and rcpt["mode"] == "formal" and rcpt["tol_pp"] == 0.05
              and rcpt["verdict"] == "PASS"
              and len(rcpt["facts"]["sha256"]) == 64
              and len(rcpt["series"]["sha256"]) == 64, json.dumps(rcpt)[:300])
        errs = []
        gate.check_figure2_receipt(td, rcpt, errs)
        # series 实物（ws.json）在案根且 sha 一致 → 发布闸绿
        check("FC5 发布闸复验绿例", errs == [], str(errs))
        # exploration 放宽运行同样留痕，且发布闸现形
        p = run([fff, "check", "--facts", "facts.json", "--series", "ws.json",
                 "--tol-pp", "99", "--exploration"], td)
        check("FC5 exploration 运行留痕", p.returncode == 0 and rcpt_path.is_file())
        rcpt = json.loads(rcpt_path.read_text())
        check("FC5 exploration 收据如实记录 mode/tol",
              rcpt["mode"] == "exploration" and rcpt["tol_pp"] == 99.0)
        errs = []
        gate.check_figure2_receipt(td, rcpt, errs)
        check("FC5 发布闸拒 exploration 收据",
              any("exploration" in x for x in errs)
              and any("tol_pp" in x for x in errs), str(errs))
        # FAIL 对账也留痕，发布闸拒 verdict!=PASS
        (td / "ws.json").write_text(json.dumps(
            [{"entity_id": "e1", "ts": ["2026-01-01"], "pct": [30.0]}]))
        p = run([fff, "check", "--facts", "facts.json", "--series", "ws.json"], td)
        rcpt = json.loads(rcpt_path.read_text())
        check("FC5 FAIL 对账留痕", p.returncode == 1 and rcpt["verdict"] == "FAIL")
        errs = []
        gate.check_figure2_receipt(td, rcpt, errs)
        check("FC5 发布闸拒 FAIL 收据", any("非 PASS" in x for x in errs), str(errs))
        # 对账后序列被改动 → 发布闸抓实物 sha 不符
        (td / "ws.json").write_text(json.dumps(
            [{"entity_id": "e1", "ts": ["2026-01-01"], "pct": [27.8]}]))
        run([fff, "check", "--facts", "facts.json", "--series", "ws.json"], td)
        rcpt = json.loads(rcpt_path.read_text())
        (td / "ws.json").write_text(json.dumps(
            [{"entity_id": "e1", "ts": ["2026-01-01"], "pct": [27.81]}]))
        errs = []
        gate.check_figure2_receipt(td, rcpt, errs)
        check("FC5 对账后改序列被实物 sha 抓获",
              any("实物不一致" in x for x in errs), str(errs))

        # ── 消化轮 2：N-C1 手写收据攻击（不跑 check 纯手写）──
        import hashlib as _h3
        facts_sha = _h3.sha256((td / "facts.json").read_bytes()).hexdigest()
        ws_sha = _h3.sha256((td / "ws.json").read_bytes()).hexdigest()
        # 攻击 b（盲审）：series.path 写不存在的名字（轮 1 条件式整段跳过）→ 拒
        errs = []
        gate.check_figure2_receipt(td, {
            "schema": "figure2-check-receipt/v1", "mode": "formal",
            "tol_pp": 0.05, "verdict": "PASS",
            "series": {"path": "charts/other_series.json", "sha256": "a" * 64},
            "facts": {"path": "facts.json", "sha256": facts_sha}}, errs)
        check("NC1 手写收据 series 实物缺席拒",
              any("不在案根" in x for x in errs), str(errs))
        # 攻击 c（盲审）：series sha 真、facts sha 乱填（轮 1 完全不验）→ 拒
        errs = []
        gate.check_figure2_receipt(td, {
            "schema": "figure2-check-receipt/v1", "mode": "formal",
            "tol_pp": 0.05, "verdict": "PASS",
            "series": {"path": "ws.json", "sha256": ws_sha},
            "facts": {"path": "facts.json", "sha256": "b" * 64}}, errs)
        check("NC1 手写收据 facts sha 乱填拒",
              any("facts" in x and "不一致" in x for x in errs), str(errs))
        # 收据缺 facts 绑定段 → 拒
        errs = []
        gate.check_figure2_receipt(td, {
            "schema": "figure2-check-receipt/v1", "mode": "formal",
            "tol_pp": 0.05, "verdict": "PASS",
            "series": {"path": "ws.json", "sha256": ws_sha}}, errs)
        check("NC1 收据缺 facts 绑定拒",
              any("缺 facts 绑定" in x for x in errs), str(errs))


def t_f04_tolpp_clamp():
    """--tol-pp 同族钳制（同 F-02 模式）：formal 写死默认值，仅 --exploration 可覆盖。"""
    fff = ROOT / "scripts/report/figures_from_facts.py"
    with tempfile.TemporaryDirectory() as s:
        td = Path(s)
        (td / "facts.json").write_text(json.dumps(
            {"token": {"symbol": "TT", "decimals": 0, "total_supply_raw": "1000"},
             "entities": {"e1": {"label": "大庄#1", "addresses": [A],
                                 "current_raw": "278", "peak_raw": "300"}}}))
        (td / "ws.json").write_text(json.dumps(
            [{"entity_id": "e1", "ts": ["2026-01-01"], "pct": [27.9]}]))
        # 27.9 vs 27.8：差 0.1pp——formal(0.05) 应 FAIL
        p = run([fff, "check", "--facts", "facts.json", "--series", "ws.json"], td)
        check("F04 formal 默认容差照常判 FAIL", p.returncode == 1
              and "不同源" in p.stdout, f"rc={p.returncode} {p.stdout}")
        # formal 下改 --tol-pp → 政策拒（fail-loud，不静默夹回）
        p = run([fff, "check", "--facts", "facts.json", "--series", "ws.json",
                 "--tol-pp", "0.5"], td)
        check("F04 formal 改 tol-pp 政策拒", p.returncode not in (0, 1)
              and "--exploration" in (p.stdout + p.stderr),
              f"rc={p.returncode} {p.stdout} {p.stderr}")
        # exploration 显式声明 → 允许覆盖并放行
        p = run([fff, "check", "--facts", "facts.json", "--series", "ws.json",
                 "--tol-pp", "0.5", "--exploration"], td)
        check("F04 exploration 显式覆盖放行", p.returncode == 0
              and "[exploration]" in p.stdout, f"rc={p.returncode} {p.stdout}")
        # 显式传默认值（无放大）formal 照常可跑
        (td / "ws.json").write_text(json.dumps(
            [{"entity_id": "e1", "ts": ["2026-01-01"], "pct": [27.8]}]))
        p = run([fff, "check", "--facts", "facts.json", "--series", "ws.json",
                 "--tol-pp", "0.05"], td)
        check("F04 formal 显式默认值绿例", p.returncode == 0, p.stdout)


def t_f09_importer_fail_closed():
    """legacy importer 三条失败分支：坏 meta／缺 GPA／逻辑摘要不符。"""
    importer_path = (ROOT / "maintenance/repair-20260814-batch2/"
                     "import_pythia_legacy.py")
    spec = importlib.util.spec_from_file_location("f09_pythia_importer", importer_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    with tempfile.TemporaryDirectory(prefix="c-f09-import-", dir="/private/tmp") as raw:
        root = Path(raw)
        (root / "data").mkdir()
        edge = root / "data/edge.jsonl.gz"
        with gzip.open(edge, "wt") as fh:
            fh.write(json.dumps([1, 1, Z, SA, 1]) + "\n")
        meta = root / "data/legacy.meta.json"
        meta.write_text(json.dumps({"version": 1, "from_slot": 1,
                                    "launch_covered": True}))
        manifest = {
            "schema": mod.MANIFEST_SCHEMA, "chain": "solana",
            "mint": mod.EXPECTED_MINT, "edge_rows": mod.EXPECTED_ROWS,
            "edge_logical_sha256": mod.EXPECTED_EDGE_DIGEST,
            "frozen_cutoff_slot": mod.EXPECTED_CUTOFF,
            "coverage_front_slot": mod.EXPECTED_CUTOFF, "gaps": [],
            "edge_source": "data/edge.jsonl.gz",
            "collector_meta_path": "data/legacy.meta.json",
            "supply_raw": "1",
        }
        (root / "collect_manifest.json").write_text(json.dumps(manifest))
        try:
            mod.validate_manifest(root)
            check("F09 importer 坏 meta fail-closed", False, "坏 meta 被接受")
        except mod.ImportFailure as exc:
            check("F09 importer 坏 meta fail-closed", "version=2" in str(exc), str(exc))

        meta.write_text(json.dumps({"version": 2, "from_slot": 1,
                                    "launch_covered": True}))
        try:
            mod.replay_gpa(root, manifest)
            check("F09 importer 缺 GPA fail-closed", False, "缺 GPA 被接受")
        except mod.ImportFailure as exc:
            check("F09 importer 缺 GPA fail-closed", "raw GPA" in str(exc), str(exc))

        try:
            mod.replay_edge_facts(edge)
            check("F09 importer 逻辑哈希不符 fail-closed", False, "坏摘要被接受")
        except mod.ImportFailure as exc:
            check("F09 importer 逻辑哈希不符 fail-closed",
                  "edge 逻辑事实差异" in str(exc), str(exc))
        check("F09 importer 失败分支零 migration receipt",
              not (root / "migration_receipt.json").exists())


def t_blindreview_c_fixround1():
    """BC-01~09 + 16 项假覆盖 + O1/O5 的破坏性负向锚。"""
    import importlib
    import replay_edges as re_mod
    from camp_series_provenance import (SeriesProvenanceError,
                                        load_series_with_sidecar,
                                        registry_anchor_check)

    failures = []

    def probe(name, condition, detail=""):
        if condition:
            PASSED.append(name)
        else:
            failures.append(f"{name}: {detail}")

    edges = [
        [3600, 1, 0, -1, Z, SA, 1000],
        [7200, 2, 0, -1, SA, SB, 300],
        [10800, 3, 0, -1, SA, Z, 100],
    ]
    old_cwd = os.getcwd()
    with tempfile.TemporaryDirectory(prefix="c-blind-fix1-", dir="/private/tmp") as raw:
        td = Path(raw)
        os.chdir(td)
        try:
            importlib.reload(re_mod)
            data = Path("data")
            data.mkdir()
            edge_key = hashlib.sha256(SA.encode("utf-8")).hexdigest()
            edge_path = write_sol_edges(data / f"soltx-{edge_key}.jsonl.gz", edges)
            meta_path = data / f"soltx-{edge_key}.meta.json"
            owners_path = data / "holders_owners.json"
            snapshot_path = data / "holders_snapshot_meta.json"
            owners_path.write_text(json.dumps({SA: 600, SB: 300}))

            def good_snapshot():
                return {
                    "schema": "solana-holder-snapshot-v2", "mint": SA,
                    "target": {"chain": "solana", "token": SA,
                               "as_of_block": 3},
                    "closed": True, "supply_raw": "900",
                    "outputs": {"holders_owners": file_ref(owners_path)},
                }

            def good_meta():
                return formal_sol_meta(SA, 1, 3, edges)

            write_json(snapshot_path, good_snapshot())
            write_json(meta_path, good_meta())
            probe("BC fixture producer green",
                  run_reconcile_v4(re_mod, edges, 1, mint=SA,
                                   cache_meta_path=meta_path) is True)
            Path("camps.json").write_text(
                json.dumps({"项目方": [SA], "大庄": [SB]}, ensure_ascii=False))
            run_evolution_v4(re_mod, edges, 1, "camps.json", set())
            Path("facts.json").write_text(json.dumps(
                {"token": {"symbol": "ST", "decimals": 0,
                           "total_supply_raw": "900"},
                 "entities": {"e1": {"label": "大庄#1", "addresses": [SB],
                                       "current_raw": "300", "peak_raw": "300"}}}))

            def source_doc(mint=SA, cutoff=3):
                return {
                    "schema": "analysis-state-source/v1",
                    "token": {"chain": "solana", "mint": mint,
                              "data_cutoff_slot": cutoff,
                              "data_cutoff": "2026-01-05T00:00:00Z",
                              "skill_version": "6.39.5"},
                    "entity_annotations": {"e1": {"type": "single",
                                                    "status": "holding"}},
                    "address_balances": {SB: "300"}, "vault_addresses": [],
                    "provenance": {"skill_commit": "batchc-blind",
                                   "data_sources": ["sqd"]},
                }

            write_json(Path("source.json"), source_doc())
            rr_path = data / "reconcile_receipt.json"

            def compile_now():
                return compile_state_cli(td, "--series-source",
                                         "data/camp_share_series.json")

            def bind_receipt(doc):
                write_json(rr_path, doc)
                run_evolution_v4(re_mod, edges, 1, "camps.json", set())

            def restore_chain(*, rewrite_series=False):
                owners_path.write_text(json.dumps({SA: 600, SB: 300}))
                write_json(snapshot_path, good_snapshot())
                write_json(meta_path, meta_good)
                write_json(rr_path, rr_good)
                if rewrite_series:
                    run_evolution_v4(re_mod, edges, 1, "camps.json", set())
                write_json(Path("source.json"), source_doc())
                return True

            fixture_compile = compile_now()
            probe("BC fixture consumer green", fixture_compile.returncode == 0,
                  fixture_compile.stdout + fixture_compile.stderr)
            rr_good = json.loads(rr_path.read_text())
            meta_good = json.loads(meta_path.read_text())
            compiled_good = json.loads(
                (data / "camp_share_series.json").read_text())
            from camp_series_provenance import series_to_state_form, endpoint_reconcile
            compiled_good = series_to_state_form(compiled_good, "sol-rows")

            def direct_receipt_result(doc, *, needle=None,
                                      verify_edge_physical_sha=False):
                write_json(rr_path, doc)
                direct_sidecar = {"series_format": "sol-rows",
                                  "denominator": "net_supply"}
                direct_resolved = {
                    "inputs.reconcile_receipt": rr_path,
                    "camps_spec": Path("camps.json"),
                    "final_balances": data / "effective_balances.json",
                }
                try:
                    kwargs = {
                        "expected_chain": "solana", "expected_mint": SA,
                        "expected_cutoff_slot": 3,
                    }
                    import inspect
                    if verify_edge_physical_sha:
                        if "verify_edge_physical_sha" not in inspect.signature(
                                registry_anchor_check).parameters:
                            return False, "registry has no physical-sha release mode"
                        kwargs["verify_edge_physical_sha"] = True
                    registry_anchor_check(
                        direct_sidecar, direct_resolved,
                        data / "camp_share_series.json",
                        **kwargs)
                    endpoint_reconcile(direct_sidecar, compiled_good,
                                       direct_resolved)
                    return False, ""
                except (SeriesProvenanceError, TypeError) as exc:
                    text = str(exc)
                    return True, text

            # BC-01/i25: truthy but not literal True must all fail closed.
            truthy_non_true = ["false", "FAIL", "0", [False], 1, 0.1]
            for idx, value in enumerate(truthy_non_true):
                doc = json.loads(json.dumps(rr_good))
                doc["gate_pass"] = value
                rejected, detail = direct_receipt_result(doc, needle="gate_pass")
                probe(f"BC01 gate_pass truthy-nonTrue #{idx + 1}",
                      rejected, f"value={value!r} {detail}")
            write_json(rr_path, rr_good)

            # BC-03 and the independent numeric conclusions under gate_pass.
            for field, value in (("net_supply_raw", None),
                                 ("negative_balance_count", 1),
                                 ("snapshot_mismatch_count", 1)):
                doc = json.loads(json.dumps(rr_good))
                if value is None:
                    doc.pop(field)
                else:
                    doc[field] = value
                    doc["gate_pass"] = True
                rejected, detail = direct_receipt_result(doc, needle=field)
                probe(f"BC01/03 consumer independent {field}",
                      rejected, detail)
            write_json(rr_path, rr_good)
            for field in ("negative_balance_count", "snapshot_mismatch_count"):
                for idx, value in enumerate((False, "0", 0.0)):
                    doc = json.loads(json.dumps(rr_good))
                    doc[field] = value
                    rejected, detail = direct_receipt_result(doc, needle=field)
                    probe(f"BC01 exact-int-zero {field} #{idx + 1}",
                          rejected, detail)
            doc = json.loads(json.dumps(rr_good))
            doc["net_supply_raw"] = str(doc["net_supply_raw"])
            rejected, detail = direct_receipt_result(doc, needle="net_supply_raw")
            probe("BC03 net_supply_raw literal nonnegative int", rejected, detail)
            write_json(rr_path, rr_good)

            # BC-04/i10: direct call cannot omit independently supplied identity.
            sidecar, _raw, resolved = load_series_with_sidecar(
                data / "camp_share_series.json")
            try:
                registry_anchor_check(sidecar, resolved,
                                      data / "camp_share_series.json")
                direct_rejected = False
            except SeriesProvenanceError as exc:
                direct_rejected = "expected_chain" in str(exc)
            probe("BC04 registry direct-call identity None rejects", direct_rejected)

            # BC-05: consumer must touch the canonical edge object.
            edge_backup = edge_path.with_name(edge_path.name + ".bak")
            edge_path.rename(edge_backup)
            rejected, detail = direct_receipt_result(rr_good, needle="边文件")
            probe("BC05 missing edge object rejects",
                  rejected, detail)
            edge_backup.rename(edge_path)

            # v4 深验在 compile/release 两点都验证 receipt 绑定的边实物哈希。
            original_edge_bytes = edge_path.read_bytes()
            tampered = bytearray(original_edge_bytes)
            tampered[-1] ^= 1
            edge_path.write_bytes(bytes(tampered))
            compile_rejected, compile_detail = direct_receipt_result(rr_good)
            probe("BC05 compile point verifies physical sha",
                  compile_rejected, compile_detail)
            release_rejected, release_detail = direct_receipt_result(
                rr_good, needle="物理 sha256", verify_edge_physical_sha=True)
            probe("BC05 release point verifies physical sha",
                  release_rejected, release_detail)
            edge_path.write_bytes(original_edge_bytes)

            # Producer must reject a meta summary that disagrees with replayed rows.
            bad_meta = json.loads(meta_path.read_text())
            bad_meta["edge_logical_sha256"] = "0" * 64
            write_json(meta_path, bad_meta)
            try:
                run_reconcile_v4(re_mod, edges, 1, mint=SA,
                                 cache_meta_path=meta_path)
                summary_rejected = False
            except ValueError as exc:
                summary_rejected = "摘要" in str(exc)
            probe("BC05 i14/i19 bad meta summary rejects", summary_rejected)
            restore_chain()

            # BC-02 + BC-06/i28: every snapshot_ok component gets a negative anchor.
            for idx, value in enumerate(truthy_non_true):
                snap = good_snapshot()
                snap["closed"] = value
                write_json(snapshot_path, snap)
                try:
                    accepted = run_reconcile_v4(re_mod,
                        edges, 1, mint=SA, cache_meta_path=meta_path) is True
                except (ValueError, SystemExit):
                    accepted = False
                probe(f"BC02 closed truthy-nonTrue #{idx + 1}", not accepted,
                      f"value={value!r} accepted={accepted}")
                restore_chain()

            snap = good_snapshot()
            snap.pop("supply_raw")
            write_json(snapshot_path, snap)
            try:
                run_reconcile_v4(re_mod, edges, 1, mint=SA,
                                 cache_meta_path=meta_path)
                missing_supply_loud = False
            except ValueError as exc:
                missing_supply_loud = "supply_raw" in str(exc)
            probe("BC02 missing snapshot supply_raw explicitly rejects",
                  missing_supply_loud)
            restore_chain()

            snapshot_mutations = [
                ("schema", lambda d: d.update(schema="bad")),
                ("mint", lambda d: d.update(mint=SB)),
                ("closed", lambda d: d.update(closed=False)),
                ("supply", lambda d: d.update(supply_raw="901")),
                ("cutoff", lambda d: d["target"].update(as_of_block=2)),
                ("owners-ref", lambda d: d["outputs"]["holders_owners"].update(
                    sha256="0" * 64)),
            ]
            for name, mutate in snapshot_mutations:
                snap = good_snapshot()
                mutate(snap)
                write_json(snapshot_path, snap)
                try:
                    accepted = run_reconcile_v4(re_mod,
                        edges, 1, mint=SA, cache_meta_path=meta_path) is True
                except (ValueError, SystemExit):
                    accepted = False
                probe(f"BC06 snapshot_ok negative {name}", not accepted,
                      f"accepted={accepted}")
                restore_chain()
            write_json(owners_path, {SA: 599, SB: 301})
            snap = good_snapshot()
            snap["outputs"]["holders_owners"] = file_ref(owners_path)
            write_json(snapshot_path, snap)
            probe("BC06 owner mismatch independently rejects",
                  run_reconcile_v4(re_mod, edges, 1, mint=SA,
                                   cache_meta_path=meta_path) is False)
            restore_chain()
            write_json(rr_path, rr_good)

            def receipt_case(name, mutate, needle):
                doc = json.loads(json.dumps(rr_good))
                mutate(doc)
                rejected, detail = direct_receipt_result(doc, needle=needle)
                probe(name, rejected, detail)
                write_json(rr_path, rr_good)

            receipt_case("i02 wrong chain", lambda d: d.update(chain="ethereum"),
                         "chain")
            receipt_case("i04 window.to above cutoff",
                         lambda d: d["collection_window"].update(to_slot=4),
                         "cutoff")
            receipt_case("i09 v2 dedicated rerun guidance",
                         lambda d: d.update(schema="solana-reconcile/v2"),
                         "重跑 replay_edges reconcile")
            receipt_case("i17 third schema rejects",
                         lambda d: d.update(schema="solana-reconcile/v999"),
                         "schema 必须")
            receipt_case("i22 window from greater than to",
                         lambda d: d["collection_window"].update(from_slot=4),
                         "from_slot 大于")
            for idx, value in enumerate((0, -1, True, 1.5)):
                receipt_case(f"i23 edge_count invalid #{idx + 1}",
                             lambda d, value=value: d.update(edge_count=value),
                             "正整数")
            receipt_case("i23 digest uppercase rejects",
                         lambda d: d.update(edge_digest=d["edge_digest"].upper()),
                         "小写 sha256")
            # i13 producer meta legality (schema/mint/window) is independently anchored.
            producer_meta_cases = [
                ("schema", lambda d: d.update(schema="bad")),
                ("mint", lambda d: d.update(mint=SB)),
                ("window", lambda d: d.update(from_slot=4,
                                               finalized_upper_slot=3)),
            ]
            for name, mutate in producer_meta_cases:
                doc = good_meta()
                mutate(doc)
                write_json(meta_path, doc)
                try:
                    run_reconcile_v4(re_mod, edges, 1, mint=SA,
                                     cache_meta_path=meta_path)
                    rejected = False
                except ValueError as exc:
                    rejected = "v4 meta" in str(exc)
                probe(f"i13 producer meta {name} rejects", rejected)
                restore_chain()

            def consumer_file_case(name, path, doc, receipt_key, needle):
                write_json(path, doc)
                receipt = json.loads(rr_path.read_text())
                receipt["inputs"][receipt_key] = file_ref(path)
                if receipt_key == "holders_owners":
                    snap = json.loads(snapshot_path.read_text())
                    snap["outputs"]["holders_owners"] = file_ref(path)
                    write_json(snapshot_path, snap)
                    receipt["inputs"]["holders_snapshot_meta"] = file_ref(snapshot_path)
                rejected, detail = direct_receipt_result(receipt, needle=needle)
                probe(name, rejected, detail)
                restore_chain()

            bad = json.loads(meta_path.read_text())
            bad["schema"] = "bad"
            consumer_file_case("i21 soltx meta schema", meta_path, bad,
                               "soltx_meta", "schema/mint")
            bad = good_meta()
            bad["mint"] = SB
            consumer_file_case("i21 soltx meta mint", meta_path, bad,
                               "soltx_meta", "schema/mint")
            bad = json.loads(json.dumps(meta_good))
            bad["from_slot"] = 0
            consumer_file_case("i26 receipt/meta window mismatch", meta_path, bad,
                               "soltx_meta", "采集窗口撕裂")
            bad = json.loads(snapshot_path.read_text())
            bad["schema"] = "bad"
            consumer_file_case("i27 snapshot schema", snapshot_path, bad,
                               "holders_snapshot_meta", "schema/mint/target")
            bad = good_snapshot()
            bad["mint"] = SB
            consumer_file_case("i27 snapshot mint", snapshot_path, bad,
                               "holders_snapshot_meta", "schema/mint/target")
            bad = good_snapshot()
            bad["target"]["token"] = SB
            consumer_file_case("i27 snapshot target", snapshot_path, bad,
                               "holders_snapshot_meta", "schema/mint/target")
            bad = good_snapshot()
            bad["outputs"]["holders_owners"]["size"] += 1
            write_json(snapshot_path, bad)
            receipt = json.loads(rr_path.read_text())
            receipt["inputs"]["holders_snapshot_meta"] = file_ref(snapshot_path)
            receipt["inputs"]["holders_owners"] = dict(
                bad["outputs"]["holders_owners"])
            rejected, detail = direct_receipt_result(receipt, needle="size")
            probe("i24 owners physical size mismatch",
                  rejected, detail)
            restore_chain()

            # BC-O5: every formal JSON mount rejects non-finite constants.
            rr_good = json.loads(rr_path.read_text())
            receipt_nan = dict(rr_good)
            receipt_nan["unused_nonfinite_probe"] = float("nan")
            rejected, detail = direct_receipt_result(receipt_nan, needle="非有限数")
            probe("BCO5 receipt NaN parse_constant", rejected, detail)
            restore_chain()

            meta_nan = json.loads(meta_path.read_text())
            meta_nan["unused_nonfinite_probe"] = float("nan")
            write_json(meta_path, meta_nan)
            receipt = json.loads(rr_path.read_text())
            receipt["inputs"]["soltx_meta"] = file_ref(meta_path)
            rejected, detail = direct_receipt_result(receipt, needle="非有限数")
            probe("BCO5 soltx meta NaN parse_constant", rejected, detail)
            restore_chain()

            snap_nan = good_snapshot()
            snap_nan["unused_nonfinite_probe"] = float("nan")
            consumer_file_case("BCO5 snapshot meta NaN parse_constant",
                               snapshot_path, snap_nan,
                               "holders_snapshot_meta", "非有限数")

            owners_path.write_text(
                '{"%s":600,"%s":300,"probe":NaN}' % (SA, SB))
            snap = good_snapshot()
            snap["outputs"]["holders_owners"] = file_ref(owners_path)
            write_json(snapshot_path, snap)
            receipt = json.loads(rr_path.read_text())
            receipt["inputs"]["holders_owners"] = file_ref(owners_path)
            receipt["inputs"]["holders_snapshot_meta"] = file_ref(snapshot_path)
            rejected, detail = direct_receipt_result(receipt, needle="非有限数")
            probe("BCO5 owners NaN parse_constant", rejected, detail)
            restore_chain()

            sc_path = data / "camp_share_series.provenance.json"
            sc_doc = json.loads(sc_path.read_text())
            sc_doc["unused_nonfinite_probe"] = float("nan")
            write_json(sc_path, sc_doc)
            try:
                load_series_with_sidecar(data / "camp_share_series.json")
                sidecar_nan_rejected = False
                sidecar_nan_detail = "accepted"
            except SeriesProvenanceError as exc:
                sidecar_nan_rejected = "非有限数" in str(exc)
                sidecar_nan_detail = str(exc)
            probe("BCO5 sidecar NaN parse_constant", sidecar_nan_rejected,
                  sidecar_nan_detail)
            run_evolution_v4(re_mod, edges, 1, "camps.json", set())

            importer_path = (ROOT / "maintenance/repair-20260814-batch2/"
                             "import_pythia_legacy.py")
            spec = importlib.util.spec_from_file_location(
                "bc_pythia_importer", importer_path)
            importer = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(importer)
            manifest_nan = td / "manifest_nan.json"
            manifest_nan.write_text('{"schema":"x","probe":NaN}')
            try:
                importer.read_object(manifest_nan, "collect_manifest")
                manifest_nan_rejected = False
            except importer.ImportFailure as exc:
                manifest_nan_rejected = "非有限数" in str(exc)
            probe("BCO5 collect_manifest NaN parse_constant",
                  manifest_nan_rejected)

            # RecursionError at the decoder boundary is policy rejection rc=2.
            import state_from_facts as state_mod
            original_state_loads = state_mod.json.loads
            state_mod.json.loads = lambda *a, **k: (_ for _ in ()).throw(
                RecursionError("deep JSON"))
            try:
                try:
                    state_rc = state_mod.main([
                        "--facts", "facts.json", "--source", "source.json",
                        "--out", "deep-state.json", "--series-source",
                        "data/camp_share_series.json"])
                except RecursionError:
                    state_rc = 1
            finally:
                state_mod.json.loads = original_state_loads
            probe("BCO5 state RecursionError -> rc2", state_rc == 2,
                  f"rc={state_rc}")

            original_load_edges = re_mod.load_edges
            original_argv = sys.argv[:]
            re_mod.load_edges = lambda mint, **kwargs: (_ for _ in ()).throw(
                RecursionError("deep JSON"))
            sys.argv = ["replay_edges.py", "reconcile", "--mint", SA,
                        "--no-labels"]
            try:
                try:
                    replay_rc = re_mod.main()
                    replay_rc = 0 if replay_rc is None else replay_rc
                except RecursionError:
                    replay_rc = 1
                except SystemExit as exc:
                    replay_rc = exc.code
            finally:
                re_mod.load_edges = original_load_edges
                sys.argv = original_argv
            probe("BCO5 producer RecursionError -> rc2", replay_rc == 2,
                  f"rc={replay_rc}")

            # BC-08: missing cutoff gives the migration instruction, not a generic None error.
            src = source_doc()
            del src["token"]["data_cutoff_slot"]
            write_json(Path("source.json"), src)
            got = compile_now()
            probe("BC08 missing data_cutoff_slot migration guidance",
                  got.returncode == 2 and "scan-schemas.md 存量迁移段" in got.stdout,
                  got.stdout[-220:])
            write_json(Path("source.json"), source_doc())

            # BC-07: producer and consumer independently reject the full malformed mint family.
            malformed_mints = [
                "   ", SA + "\u200b", SA + "\ufeff", SA + "\u3164",
                SA + "\u2800", SA[:-4] + "0OIl", "1" * 900,
            ]
            for idx, bad_mint in enumerate(malformed_mints):
                with tempfile.TemporaryDirectory(prefix="c-mint-", dir="/private/tmp") as mint_raw:
                    mint_td = Path(mint_raw)
                    os.chdir(mint_td)
                    Path("data").mkdir()
                    bad_edge_key = hashlib.sha256(bad_mint.encode("utf-8")).hexdigest()
                    bad_edge = write_sol_edges(
                        Path(f"data/soltx-{bad_edge_key}.jsonl.gz"), edges)
                    bad_meta_path = Path(f"data/soltx-{bad_edge_key}.meta.json")
                    bad_owners = Path("data/holders_owners.json")
                    write_json(bad_owners, {SA: 600, SB: 300})
                    bad_snapshot = Path("data/holders_snapshot_meta.json")
                    write_json(bad_snapshot, {
                        "schema": "solana-holder-snapshot-v2", "mint": bad_mint,
                        "target": {"chain": "solana", "token": bad_mint,
                                   "as_of_block": 3},
                        "closed": True, "supply_raw": "900",
                        "outputs": {"holders_owners": file_ref(bad_owners)}})
                    write_json(bad_meta_path, formal_sol_meta(bad_mint, 1, 3, edges))
                    try:
                        run_reconcile_v4(re_mod, edges, 1, mint=bad_mint,
                                         cache_meta_path=bad_meta_path)
                        producer_rejected = False
                    except (ValueError, SystemExit) as exc:
                        producer_rejected = "mint" in str(exc)
                    probe(f"BC07 producer malformed mint #{idx + 1}",
                          producer_rejected, repr(bad_mint[-12:]))

                    try:
                        registry_anchor_check(
                            {"series_format": "sol-rows",
                             "edge_source_binding": rr_good["edge_source_binding"]},
                            {"inputs.reconcile_receipt": td / "data/reconcile_receipt.json"},
                            td / "data/camp_share_series.json",
                            expected_chain="solana", expected_mint=bad_mint,
                            expected_cutoff_slot=3)
                        consumer_rejected = False
                    except SeriesProvenanceError as exc:
                        consumer_rejected = "mint" in str(exc)
                    probe(f"BC07 consumer malformed mint #{idx + 1}",
                          consumer_rejected, repr(bad_mint[-12:]))
                os.chdir(td)

            # BC-O1: importer digest is the normalized replay_edges logical form.
            compact_edge = td / "compact.jsonl.gz"
            compact_row = [1, 1, Z, SA, 1]
            with gzip.open(compact_edge, "wt", encoding="utf-8") as fh:
                fh.write(json.dumps(compact_row, separators=(",", ":")) + "\n")
            expected_digest = hashlib.sha256(
                (json.dumps(compact_row, ensure_ascii=False) + "\n").encode()
            ).hexdigest()
            old_rows = importer.EXPECTED_ROWS
            old_digest = importer.EXPECTED_EDGE_DIGEST
            old_cutoff = importer.EXPECTED_CUTOFF
            importer.EXPECTED_ROWS = 1
            importer.EXPECTED_EDGE_DIGEST = expected_digest
            importer.EXPECTED_CUTOFF = 1
            try:
                facts = importer.replay_edge_facts(compact_edge)
                normalized = facts["sha256"] == expected_digest
            except importer.ImportFailure:
                normalized = False
            finally:
                importer.EXPECTED_ROWS = old_rows
                importer.EXPECTED_EDGE_DIGEST = old_digest
                importer.EXPECTED_CUTOFF = old_cutoff
            probe("BCO1 importer normalized logical digest", normalized)
        finally:
            os.chdir(old_cwd)

    if failures:
        raise AssertionError("BC blind fixround1 failures:\n" + "\n".join(failures))


def t_fixround2():
    """N-01~N-05：边文件等深、发布接线与严格 JSON 挂载点回归锚。"""
    import importlib
    import audit_release_gate as gate_mod
    import replay_edges as re_mod

    failures = []

    def probe(name, condition, detail=""):
        if condition:
            PASSED.append(name)
        else:
            failures.append(f"{name}: {detail}")

    edges = [
        [3600, 1, 0, -1, Z, SA, 1000],
        [7200, 2, 0, -1, SA, SB, 300],
        [10800, 3, 0, -1, SA, Z, 100],
    ]
    old_cwd = os.getcwd()
    with tempfile.TemporaryDirectory(prefix="c-fixround2-", dir="/private/tmp") as raw, \
            tempfile.TemporaryDirectory(prefix="c-fixround2-link-",
                                        dir="/private/tmp") as link_raw:
        td = Path(raw)
        link_dir = Path(link_raw)
        os.chdir(td)
        try:
            importlib.reload(re_mod)
            data = Path("data")
            data.mkdir()
            edge_key = hashlib.sha256(SA.encode("utf-8")).hexdigest()
            edge_path = write_sol_edges(
                data / f"soltx-{edge_key}.jsonl.gz", edges)
            edge_bytes = edge_path.read_bytes()
            meta_path = data / f"soltx-{edge_key}.meta.json"
            owners_path = write_json(data / "holders_owners.json",
                                     {SA: 600, SB: 300})
            snapshot_path = data / "holders_snapshot_meta.json"
            write_json(snapshot_path, {
                "schema": "solana-holder-snapshot-v2", "mint": SA,
                "target": {"chain": "solana", "token": SA,
                           "as_of_block": 3},
                "closed": True, "supply_raw": "900",
                "outputs": {"holders_owners": file_ref(owners_path)},
            })
            write_json(meta_path, formal_sol_meta(SA, 1, 3, edges))
            assert run_reconcile_v4(re_mod,
                edges, 1, mint=SA, cache_meta_path=meta_path) is True
            Path("camps.json").write_text(
                json.dumps({"项目方": [SA], "大庄": [SB]}, ensure_ascii=False))
            run_evolution_v4(re_mod, edges, 1, "camps.json", set())
            write_json(Path("facts.json"), {
                "token": {"symbol": "ST", "decimals": 0,
                          "total_supply_raw": "900"},
                "entities": {"e1": {"label": "大庄#1", "addresses": [SB],
                                      "current_raw": "300", "peak_raw": "300"}},
            })
            source_good = {
                "schema": "analysis-state-source/v1",
                "token": {"chain": "solana", "mint": SA,
                          "data_cutoff_slot": 3,
                          "data_cutoff": "2026-01-05T00:00:00Z",
                          "skill_version": "6.39.5"},
                "entity_annotations": {"e1": {"type": "single",
                                                "status": "holding"}},
                "address_balances": {SB: "300"}, "vault_addresses": [],
                "provenance": {"skill_commit": "batchc-fixround2",
                               "data_sources": ["sqd"]},
            }
            write_json(Path("source.json"), source_good)
            rr_path = data / "reconcile_receipt.json"
            rr_good = json.loads(rr_path.read_text())
            meta_good = json.loads(meta_path.read_text())

            def compile_now():
                return compile_state_cli(
                    td, "--series-source", "data/camp_share_series.json")

            assert compile_now().returncode == 0

            def restore_chain(*, compile_state=False):
                if edge_path.is_symlink() or edge_path.exists():
                    edge_path.unlink()
                edge_path.write_bytes(edge_bytes)
                write_json(meta_path, meta_good)
                write_json(rr_path, rr_good)
                run_evolution_v4(re_mod, edges, 1, "camps.json", set())
                write_json(Path("source.json"), source_good)
                if compile_state:
                    return compile_now()
                return None

            def install_external_link(kind):
                target = link_dir / f"{kind}-same-content.gz"
                target.write_bytes(edge_bytes)
                edge_path.unlink()
                if kind == "symlink":
                    edge_path.symlink_to(target)
                else:
                    os.link(target, edge_path)

            # N-01 consumer：边实物换成案外同内容 symlink，size/sha 均仍相符。
            install_external_link("symlink")
            got = compile_now()
            probe("N01 consumer symlink edge rejects",
                  got.returncode == 2
                  and ("符号链接" in got.stdout or "symlink" in got.stdout),
                  got.stdout + got.stderr)
            restore_chain()

            # N-01 producer：直走 reconcile 入口，同一 symlink 必须在打开前拒绝。
            install_external_link("symlink")
            try:
                run_reconcile_v4(re_mod, edges, 1, mint=SA,
                                 cache_meta_path=meta_path)
                producer_symlink_rejected = False
                producer_symlink_detail = "accepted"
            except (ValueError, SystemExit) as exc:
                producer_symlink_rejected = "符号链接" in str(exc)
                producer_symlink_detail = str(exc)
            probe("N01 producer symlink edge rejects",
                  producer_symlink_rejected, producer_symlink_detail)
            restore_chain()

            # hard link 是 importer 的既定落盘方式，两侧均不可误杀。
            install_external_link("hardlink")
            try:
                producer_hardlink_green = run_reconcile_v4(re_mod,
                    edges, 1, mint=SA, cache_meta_path=meta_path) is True
            except (ValueError, SystemExit):
                producer_hardlink_green = False
            if producer_hardlink_green:
                run_evolution_v4(re_mod, edges, 1, "camps.json", set())
                hardlink_compile = compile_now()
            else:
                hardlink_compile = None
            probe("N01 hardlink producer+consumer green",
                  producer_hardlink_green and hardlink_compile is not None
                  and hardlink_compile.returncode == 0,
                  "producer rejected" if hardlink_compile is None
                  else hardlink_compile.stdout + hardlink_compile.stderr)
            restore_chain(compile_state=True)

            def bind_bad_edge_ref(mutate):
                receipt = json.loads(json.dumps(rr_good))
                mutate(receipt["inputs"]["soltx_edges"])
                write_json(rr_path, receipt)
                run_evolution_v4(re_mod, edges, 1, "camps.json", set())
                return compile_now()

            # N-03：v4 不再回写 base meta；物理 size/sha 只由 receipt input 绑定。
            got = bind_bad_edge_ref(
                lambda ref: ref.update(size=edge_path.stat().st_size + 1))
            probe("N03 compile receipt edge size mismatch rejects",
                  got.returncode == 2 and "size" in got.stdout,
                  got.stdout + got.stderr)
            restore_chain()

            # N-03：sha 形态分别锚定大写与长度错误。
            for label, bad_sha in (
                    ("uppercase", rr_good["inputs"]["soltx_edges"]["sha256"].upper()),
                    ("short", "a" * 63)):
                got = bind_bad_edge_ref(
                    lambda ref, bad_sha=bad_sha: ref.update(sha256=bad_sha))
                probe(f"N03 compile receipt edge sha256 {label} rejects",
                      got.returncode == 2 and "sha256" in got.stdout,
                      got.stdout + got.stderr)
                restore_chain()

            # N-04：producer 正式 meta 解析挂载点必须拒绝 NaN；字段故意未被业务读取。
            meta_text = json.dumps(meta_good, ensure_ascii=False)
            meta_path.write_text(meta_text[:-1] + ', "unused_probe": NaN}')
            try:
                run_reconcile_v4(re_mod, edges, 1, mint=SA,
                                 cache_meta_path=meta_path)
                producer_nan_rejected = False
                producer_nan_detail = "accepted"
            except (ValueError, SystemExit) as exc:
                producer_nan_rejected = "非有限数" in str(exc)
                producer_nan_detail = str(exc)
            probe("N04 producer parse_constant mount rejects NaN",
                  producer_nan_rejected, producer_nan_detail)
            restore_chain(compile_state=True)

            # N-02：直接走 audit_release_gate.run 的 new-analysis 发布入口。
            # 同 size 篡改只有 registry_anchor_check 的物理 sha 模式能抓到。
            write_json(Path("reconciliation_report.json"), {
                "target": {"chain": "solana", "token": SA,
                           "as_of_block": 3},
            })
            tampered = bytearray(edge_bytes)
            tampered[-1] ^= 1
            edge_path.write_bytes(tampered)
            release_errors = gate_mod.run(td, None, profile="new-analysis")
            probe("N02 release entry wires physical edge sha",
                  any("sha256 mismatch" in item or "物理 sha256" in item
                      for item in release_errors),
                  "\n".join(release_errors))
            restore_chain(compile_state=True)

            # N-05：主入口 state 的 NaN 必须在 JSON 层归类，而非落到逐点比较。
            state_path = Path("analysis-state.json")
            state_good = state_path.read_text()
            state_path.write_text('{"camp_share_series": NaN}')
            release_errors = gate_mod.run(td, None, profile="new-analysis")
            probe("N05 release state NaN classified as invalid JSON",
                  any("JSON无法读取 analysis-state.json" in item
                      and ("non-finite" in item or "非有限" in item)
                      for item in release_errors),
                  "\n".join(release_errors))
            state_path.write_text(state_good)

            # 同一 loader 对 RecursionError 归类为 policy BLOCK，不向外冒泡。
            original_loads = gate_mod.json.loads
            gate_mod.json.loads = lambda *a, **k: (_ for _ in ()).throw(
                RecursionError("deep release JSON"))
            recursion_errors = []
            try:
                loaded = gate_mod.load_json(state_path, recursion_errors)
            except RecursionError:
                loaded = None
            finally:
                gate_mod.json.loads = original_loads
            probe("N05 release loader classifies RecursionError",
                  loaded == {} and any("JSON无法读取 analysis-state.json" in item
                                       for item in recursion_errors),
                  str(recursion_errors))
        finally:
            os.chdir(old_cwd)

    if failures:
        raise AssertionError("BC fixround2 failures:\n" + "\n".join(failures))


def main():
    try:
        import duckdb  # noqa: F401
    except ImportError:
        print("FAIL: duckdb 未安装，批 C 回归依赖不可静默跳过")
        return 2
    t_blindreview_c_fixround1()
    t_f05_unit()
    t_f05_evm_engines()
    t_f04_evm_chain()
    t_f05_f04_solana_chain()
    t_f05_f04_build_evolution()
    t_f04_payload_unit()
    t_f04_tolpp_clamp()
    t_f09_importer_fail_closed()
    t_fixround1()
    t_fc5_receipt_chain()
    t_fixround2()
    print(f"PASS: repair batch C (F-05+F-04+fixround1+fixround2) "
          f"{len(PASSED)} checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
