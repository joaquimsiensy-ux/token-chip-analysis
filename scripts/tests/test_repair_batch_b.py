#!/usr/bin/env python3
"""修复批 B 回归：F-03 快照闭合（两层）＋F-08 记录项三验，含消化循环第 1 轮对抗修复。

第 1 轮盲审抓的六项，全部在此有先红后绿的复现：
- P0-B1：final 轮 scan 换一份"同值换仓"快照能通关全链 → final 绑定 initial 快照 sha。
- P1-B3：闭合锚点从 onchain/total 改 mint_total（replay 侧），否则整类 form1 币被误杀。
  真案实测：APU(form2)/IQ(form1)/KOGE(form1) 均 sum(含 dead)==mint_total 逐 wei 精确。
- P1-B2：total_supply_raw/frozen 是调用者可注入的影子键，真实生产者只写
  onchain_total_supply/replay_net/mint_total——闭合分母不得依赖影子键；补真实收据形态用例。
- P2-B4：sum==mint 精确成立后超发/缺失侧一律零容差。
- P2-B5：记录项 path 钉白名单 {channels_preflight.json, holders_snapshot_meta.json}。
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCAN = ROOT / "scripts/report/holder_distribution_scan.py"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "scripts/report"))
sys.path.insert(0, str(ROOT / "scripts/lib"))
import holder_distribution_scan as dist  # noqa: E402

GATE = ROOT / "scripts/report/audit_release_gate.py"
_spec = importlib.util.spec_from_file_location("audit_release_gate_batchb", GATE)
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)

# 真案链上数字（reproduce_audit 级别的锚点，见工单实测段）：
APU_MINT = 420690000000000000000000000000       # form2 dead_sink，onchain==mint
APU_BURN = 82800853653911207346039942180
IQ_MINT = 31082094105963223790329250162         # form1 真 _burn，onchain==mint-burn
IQ_BURN = 8043180819409999643271509537

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    RESULTS.append((name, bool(ok), detail))
    print(("ok   " if ok else "FAIL ") + f"[{name}]" + ("" if ok else f" {detail}"))
    return bool(ok)


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_case(root: Path, balances: dict[str, int], *, mint: int | None = None,
              onchain: int | None = None, net: int | None = None, chain: str = "bsc",
              excluded: list[dict] | None = None, with_replay_stats: bool = False,
              shadow_only: bool = False, decision_rule: str = "primary_form1",
              burn_form=None) -> None:
    """最小合法案目录。

    默认写真实生产键（onchain_total_supply/replay_net）而非影子键；
    shadow_only=True 只写 total_supply_raw/net_supply_raw 影子键，用于 P1-B2 反例；
    with_replay_stats=True 落 **data/replay_stats.json 并由收据 inputs.replay_stats 绑定**
    ——照真实 APU 收据形态（真案 9/10 把 replay_stats 放子目录、由收据绑定，N-B1）。
    """
    snap = root / "data/holders_owners.json"
    write_json(snap, {owner: str(raw) for owner, raw in balances.items()})
    snapshot_sum = sum(balances.values())
    mint = snapshot_sum if mint is None else mint
    onchain = mint if onchain is None else onchain
    net = onchain if net is None else net
    # burn 的真实定义是 mint − replay_net（两形态通用）：form1 下 onchain==mint−burn 与之等价；
    # form2 下 onchain==mint、burn 仍是 mint−replay_net。写成 mint−onchain 会让 form2 夹具
    # 的 burn 恒为 0，与收据 replay_net 自相矛盾（真实 APU 收据验算：mint−replay_net==burn_total）。
    burn = mint - net
    if shadow_only:
        supply = {"schema": "supply-truth/v1", "verdict": "PASS", "exit_code": 0,
                  "total_supply_raw": str(mint), "net_supply_raw": str(net)}
    else:
        supply = {"schema": "supply-truth-receipt/v3", "verdict": "PASS", "exit_code": 0,
                  "chain": chain, "onchain_total_supply": str(onchain), "replay_net": str(net),
                  "mint_total": (str(mint) if not with_replay_stats else None),
                  "burn_total": (str(burn) if not with_replay_stats else None),
                  "decision_rule": decision_rule, "burn_form": burn_form}
    if with_replay_stats and chain != "solana":
        # 真案形态：实物在 data/ 子目录，收据 inputs 绑定它（不是案根裸件）
        stats = root / "data/replay_stats.json"
        write_json(stats, {"mint_total_wei": str(mint), "burn_total_wei": str(burn)})
        supply["inputs"] = {"replay_stats": {"path": str(stats.resolve()),
                                             "size": stats.stat().st_size,
                                             "sha256": sha(stats)}}
    write_json(root / "supply_truth.json", supply)
    write_json(root / "data_map.json", {
        "schema": "data-map/v1",
        "files": [{"path": "data/holders_owners.json", "sha256": sha(snap)}]})
    write_json(root / "candidate_screening.json", {
        "schema": "candidate-screening/v1", "auto_excluded_candidate": excluded or []})


def run_scan(case: Path, *extra: str):
    return subprocess.run([sys.executable, str(SCAN), "--case-dir", str(case),
                           "--stage", "initial", *extra], capture_output=True, text=True)


def smooth(n=240, scale=1) -> dict[str, int]:
    return {f"owner-{i:04d}": max(1, int(2_000_000 / (1.035 ** i))) * scale for i in range(n)}


DEAD = "0x000000000000000000000000000000000000dead"
ZERO = "0x0000000000000000000000000000000000000000"


# --------------------------------------------------------------------------
# F-03 第一层：build_scan 快照闭合（锚点=mint_total，零容差）
# --------------------------------------------------------------------------

def test_f03_snapshot_gap_rejected() -> None:
    """原反例：mint=100 而快照只有 1 个币，缺口 99% 必须拒。"""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        make_case(d, {"0xaaa": 1}, mint=100, onchain=100)
        p = run_scan(d)
        out = json.loads((d / "distribution_scan.json").read_text())
        check("F-03/1 快照缺口 99% 被拒", p.returncode == 2
              and out.get("exit_code") == 2
              and out.get("not_evaluable_reason") == "data_broken",
              f"rc={p.returncode} out={out.get('exit_code')} {p.stdout}{p.stderr}")


def test_f03_overshoot_rejected() -> None:
    """失败分支：快照和超过 mint 仍拒（零容差，1 wei 也不放）。"""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        make_case(d, {"0xaaa": 101}, mint=100, onchain=100)
        p = run_scan(d)
        check("F-03/1 快照超发 1 wei 被拒", p.returncode == 2, f"rc={p.returncode} {p.stdout}")


def test_p1b3_form1_real_receipt() -> None:
    """P1-B3：真实 form1 收据（IQ 数字，replay 侧 mint_total）——sum(含 0x0=burn)==mint 精确闭合放行。"""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        onchain = IQ_MINT - IQ_BURN
        private = {f"p{i:03d}": onchain // 120 for i in range(120)}
        remainder = onchain - sum(private.values())
        private["p000"] += remainder                       # 私人和精确 == onchain(流通)
        rows = dict(private)
        rows[ZERO] = IQ_BURN                                # 真 _burn 记账落 0x0
        make_case(d, rows, mint=IQ_MINT, onchain=onchain, net=onchain, chain="eth",
                  with_replay_stats=True, decision_rule="primary_form1",
                  excluded=[{"address": ZERO, "bucket": "burn_sentinel"}])
        p = run_scan(d)
        out = json.loads((d / "distribution_scan.json").read_text()) \
            if (d / "distribution_scan.json").is_file() else {}
        den = out.get("denominators") or {}
        binding = out.get("input_binding") or {}
        check("P1-B3 form1 真实收据对 mint_total 精确闭合放行", p.returncode == 0
              and out.get("exit_code") == 0
              and den.get("total_supply_raw") == str(IQ_MINT)          # 展示口径=mint
              and den.get("net_supply_raw") == str(onchain)            # 流通=onchain
              and isinstance(binding.get("mint_closure_anchor"), dict)
              and binding["mint_closure_anchor"].get("source") == "bound_replay_mint",
              f"rc={p.returncode} den={den} anchor={binding.get('mint_closure_anchor')} {p.stdout}{p.stderr}")
        # 篡改：私人少 1 wei（sum≠mint）→ 拒
        rows["p000"] -= 1
        make_case(d, rows, mint=IQ_MINT, onchain=onchain, net=onchain, chain="eth",
                  with_replay_stats=True, decision_rule="primary_form1",
                  excluded=[{"address": ZERO, "bucket": "burn_sentinel"}])
        p2 = run_scan(d)
        check("P1-B3 form1 快照少 1 wei 被拒（零容差）", p2.returncode == 2,
              f"rc={p2.returncode} {p2.stdout}{p2.stderr}")


def test_p1b3_form2_real_receipt() -> None:
    """P1-B3：真实 form2 收据（APU 数字）——onchain==mint，dead 持 burn，sum==mint 精确闭合放行。"""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        onchain = APU_MINT                                  # form2：onchain==mint
        flow = APU_MINT - APU_BURN                          # 非 dead 流通
        private = {f"p{i:03d}": flow // 120 for i in range(120)}
        private["p000"] += flow - sum(private.values())
        rows = dict(private)
        rows[DEAD] = APU_BURN                               # 转 dead 不减供给
        make_case(d, rows, mint=APU_MINT, onchain=onchain, net=flow, chain="eth",
                  with_replay_stats=True, decision_rule="sink_fallback_form2",
                  burn_form="dead_sink",
                  excluded=[{"address": DEAD, "bucket": "burn_sentinel"}])
        p = run_scan(d)
        out = json.loads((d / "distribution_scan.json").read_text()) \
            if (d / "distribution_scan.json").is_file() else {}
        den = out.get("denominators") or {}
        burn = (out.get("bucket_coverage") or {}).get("burn_sentinel") or {}
        check("P1-B3 form2 真实收据（dead-sink）精确闭合放行", p.returncode == 0
              and out.get("exit_code") == 0
              and den.get("total_supply_raw") == str(APU_MINT)
              and den.get("net_supply_raw") == str(flow)
              and burn.get("raw") == str(APU_BURN),
              f"rc={p.returncode} den={den} burn={burn} {p.stdout}{p.stderr}")


def test_p1b2_shadow_key_cannot_close() -> None:
    """P1-B2：只写影子键 total_supply_raw（无真实键、无 replay_stats）→ 闭合锚点拿不到 → 拒。

    修前反例：真实收据基础上再注入一个 total_supply_raw 影子键就把闭合闸放行（rc2→rc0）。
    """
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        # 只有影子键，快照残缺 → 修后闭合锚点无从取得，必须拒（影子键喂不动闭合）
        make_case(d, {"0xaaa": 1}, mint=100, shadow_only=True)
        p = run_scan(d)
        check("P1-B2 只有影子键时残缺快照仍被拒", p.returncode == 2,
              f"rc={p.returncode} {p.stdout}{p.stderr}")
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        # 真实收据缺口案 + 注入影子键 total_supply_raw=1（=快照和）妄图翻案 → 仍拒
        rows = {"0xaaa": 1}
        make_case(d, rows, mint=100, onchain=100, chain="eth", with_replay_stats=True)
        supply = json.loads((d / "supply_truth.json").read_text())
        supply["total_supply_raw"] = "1"                    # 注入影子键，等于快照和
        write_json(d / "supply_truth.json", supply)
        data_map = json.loads((d / "data_map.json").read_text())
        write_json(d / "data_map.json", data_map)
        p = run_scan(d)
        check("P1-B2 注入 total_supply_raw 影子键无法放大闭合闸", p.returncode == 2,
              f"rc={p.returncode} {p.stdout}{p.stderr}")


def test_p2b4_exact_closure_window() -> None:
    """P2-B4：删掉几个刚过 dust 线的 owner（旧 10bps 窗口内）→ 零容差下立即破坏闭合被拒。"""
    big = {"owner-000": 25 * 10 ** 16}
    for i in range(1, 99):
        big[f"owner-{i:03d}"] = int(75 * 10 ** 16 / 98)
    private = sum(big.values())
    tiny_each = private // 10 ** 7
    full = dict(big)
    for j in range(5):
        full[f"tiny-{j}"] = tiny_each + j
    mint = sum(full.values())
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        make_case(d, full, mint=mint, onchain=mint, chain="eth", with_replay_stats=True)
        p_full = run_scan(d)
        out_full = json.loads((d / "distribution_scan.json").read_text())
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        # 删掉 5 个极小 owner，但 mint 分母不动（模拟抹平快照翻 low_sample 的攻击）
        make_case(d, big, mint=mint, onchain=mint, chain="eth", with_replay_stats=True)
        p_cut = run_scan(d)
    check("P2-B4 抹平快照（旧窗口内）零容差下被拒", p_full.returncode == 0
          and out_full.get("verdict") == "ABNORMAL_SHAPE" and p_cut.returncode == 2,
          f"full={p_full.returncode}/{out_full.get('verdict')} cut={p_cut.returncode} {p_cut.stdout}{p_cut.stderr}")


def test_f03_closure_anchor_no_shadow_dependency() -> None:
    """守卫（N-B3 加强）：不再只扫比较行，改为扫 mint_closure_anchor 函数体＋功能反例。

    功能反例是关键：造一个"影子键 total_supply_raw 恰等于快照和、且没有任何合法锚点来源"
    的案子——正确行为是拿不到锚点直接拒；若锚点允许回退影子键，闭合就会通过（rc=0）。
    """
    import inspect
    body = inspect.getsource(dist.mint_closure_anchor) + inspect.getsource(dist._bound_replay_stats)
    shadow_in_anchor = re.search(r"(get|\[)\s*\(?\s*[\"'](total_supply_raw|frozen_total_supply_raw)", body)
    check("N-B3 锚点函数体内不出现影子键取值", not shadow_in_anchor,
          f"锚点函数体命中影子键取值: {shadow_in_anchor.group(0) if shadow_in_anchor else ''}")
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        rows = smooth(240)
        total = sum(rows.values())
        snap = d / "data/holders_owners.json"
        write_json(snap, {k: str(v) for k, v in rows.items()})
        # 影子键 == 快照和；真实键 onchain 缺席、无 mint_total、无绑定 replay_stats
        write_json(d / "supply_truth.json", {"schema": "supply-truth/v1", "verdict": "PASS",
                                             "exit_code": 0, "chain": "bsc",
                                             "total_supply_raw": str(total),
                                             "net_supply_raw": str(total)})
        write_json(d / "data_map.json", {"files": [{"path": "data/holders_owners.json",
                                                    "sha256": sha(snap)}]})
        write_json(d / "candidate_screening.json", {"auto_excluded_candidate": []})
        p = run_scan(d)
        # load_supply 允许影子键兜 onchain（展示用），但闭合锚点必须走 supply_truth_onchain
        # 而非影子键——这里断言"锚点来源不是影子键"，即便闭合数值恰好相等也要记明来源。
        out = json.loads((d / "distribution_scan.json").read_text()) \
            if (d / "distribution_scan.json").is_file() else {}
        src_name = ((out.get("input_binding") or {}).get("mint_closure_anchor") or {}).get("source")
        check("N-B3 影子键案的锚点来源不得记为 replay/影子键",
              p.returncode != 0 or src_name in {"supply_truth_onchain", "supply_truth_mint"},
              f"rc={p.returncode} source={src_name}")


def test_nb1_anchor_prefers_bound_receipt() -> None:
    """N-B1 攻击面：伪造的案根裸 replay_stats 配抹平快照，必须被拒（案根件不是锚点来源）。"""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        rows = smooth(240)
        true_mint = sum(rows.values())
        doctored = dict(rows)
        for k in sorted(rows)[-5:]:                       # 抹平 5 个最小 owner
            doctored.pop(k)
        cut_sum = sum(doctored.values())
        make_case(d, doctored, mint=true_mint, onchain=true_mint, chain="bsc",
                  with_replay_stats=True)                 # 收据绑 data/ 真值 mint
        # 攻击件：案根裸 replay_stats，mint 配合抹平快照
        write_json(d / "replay_stats.json",
                   {"mint_total_wei": str(cut_sum), "burn_total_wei": "0"})
        p = run_scan(d)
        check("N-B1 攻击面：伪案根 replay_stats+抹平快照被拒", p.returncode == 2,
              f"rc={p.returncode} {p.stdout}{p.stderr}")


def test_nb1_stale_root_file_ignored() -> None:
    """N-B1 误伤面：案根留一份陈旧 replay_stats，合法案必须照样通过（案根件被忽略）。"""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        rows = smooth(240)
        total = sum(rows.values())
        make_case(d, rows, mint=total, onchain=total, chain="bsc", with_replay_stats=True)
        write_json(d / "replay_stats.json",                # 陈旧件：mint 是真值的两倍
                   {"mint_total_wei": str(total * 2), "burn_total_wei": "0"})
        p = run_scan(d)
        out = json.loads((d / "distribution_scan.json").read_text()) \
            if (d / "distribution_scan.json").is_file() else {}
        anchor = (out.get("input_binding") or {}).get("mint_closure_anchor") or {}
        check("N-B1 误伤面：案根陈旧件被忽略，合法案放行",
              p.returncode == 0 and anchor.get("source") == "bound_replay_mint"
              and anchor.get("raw") == str(total),
              f"rc={p.returncode} anchor={anchor} {p.stdout}{p.stderr}")


def test_nb1_bound_stats_cross_check() -> None:
    """N-B1：绑定的 replay_stats 与收据 replay_net 不自洽（mint−burn≠replay_net）→ 拒。"""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        rows = smooth(240)
        total = sum(rows.values())
        make_case(d, rows, mint=total, onchain=total, chain="bsc", with_replay_stats=True)
        supply = json.loads((d / "supply_truth.json").read_text())
        supply["replay_net"] = str(total - 12345)          # 与 mint−burn 不符
        write_json(d / "supply_truth.json", supply)
        p = run_scan(d)
        check("N-B1 绑定 replay_stats 与 replay_net 不自洽被拒", p.returncode == 2,
              f"rc={p.returncode} {p.stdout}{p.stderr}")


def test_nb2_root_stats_symlink_failclosed() -> None:
    """N-B2：案根 replay_stats.json 是符号链接 → fail-closed exit 2，不再静默换档。"""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "case"
        d.mkdir(parents=True)
        rows = smooth(240)
        total = sum(rows.values())
        make_case(d, rows, mint=total, onchain=total, chain="bsc", with_replay_stats=True)
        outside = Path(td) / "outside_stats.json"
        write_json(outside, {"mint_total_wei": str(total), "burn_total_wei": "0"})
        os.symlink(outside, d / "replay_stats.json")
        p = run_scan(d)
        check("N-B2 案根 replay_stats 符号链接 fail-closed",
              p.returncode == 2 and "在场但非法" in (p.stdout + p.stderr),
              f"rc={p.returncode} {p.stdout}{p.stderr}")


def test_nb3_rounds_snapshot_sha_consistency() -> None:
    """N-B3：rounds 台账第 2 轮 snapshot_sha 与首轮不同 → validate_rounds_ledger 必报。"""
    rounds = [{"round_n": 1, "status": "UNEXPLAINED", "snapshot_sha": "a" * 64,
               "previous_entry_sha256": None}]
    second = {"round_n": 2, "status": "NORMAL", "snapshot_sha": "b" * 64,
              "previous_entry_sha256": dist.canonical_sha(rounds[0])}
    ledger = {"schema": dist.ROUNDS_SCHEMA, "rounds": rounds + [second], "terminal": None}
    errors = dist.validate_rounds_ledger(ledger)
    check("N-B3 跨轮 snapshot_sha 不一致必报",
          any("snapshot_sha" in x for x in errors), str(errors))
    # 防误伤：一致时不得误报
    same = dict(second, snapshot_sha="a" * 64)
    same["previous_entry_sha256"] = dist.canonical_sha(rounds[0])
    ok_ledger = {"schema": dist.ROUNDS_SCHEMA, "rounds": rounds + [same], "terminal": None}
    check("N-B3 跨轮 snapshot_sha 一致不误报",
          not any("snapshot_sha" in x for x in dist.validate_rounds_ledger(ok_ledger)),
          str(dist.validate_rounds_ledger(ok_ledger)))


def test_nb4_docs_denominator_semantics() -> None:
    """N-B4：denominators.total_supply_raw 语义已变为铸造总量，schema 段必须写明。"""
    text = (ROOT / "references/scan-schemas.md").read_text(encoding="utf-8")
    check("N-B4 scan-schemas 写明 total_supply_raw=mint_total（含已销毁）",
          "含已销毁" in text and "denominators" in text,
          "scan-schemas.md 未标注 denominators 语义变更")


# --------------------------------------------------------------------------
# F-03 第二层：audit_release_gate（new-analysis）交叉检查（initial）
# --------------------------------------------------------------------------

BINDING_ERROR = "分布快照未绑定对账 owner 快照"


def _p105():
    import test_review_20260804_p105 as p105
    return p105


def test_f03_gate_evm_same_total_swap() -> None:
    """原反例（EVM）：initial 同值换仓——总和一样、owner 分配不同的快照必须被拒。"""
    p105 = _p105()
    fixture = p105.fixture
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        report = fixture.build_case(root, historical=False)
        for name in p105.AUDIT_ONLY:
            (root / name).unlink(missing_ok=True)
        p105.add_new_analysis_distribution(root, report)
        errors = fixture.gate.run(root, report, profile="new-analysis")
        check("F-03/2 EVM 合法案（同一份快照喂四查与分布扫描）放行",
              not errors, str(errors))

        truth = json.loads((root / "data/holders_owners.json").read_text())
        keys = sorted(truth)
        swapped = dict(truth)
        swapped[keys[0]], swapped[keys[-1]] = truth[keys[-1]], truth[keys[0]]
        alt = root / "data/holders_owners_alt.json"
        p105.write_json(alt, swapped)
        assert sum(int(x) for x in swapped.values()) == sum(int(x) for x in truth.values())
        data_map = json.loads((root / "data_map.json").read_text())
        data_map["files"].append({"path": "data/holders_owners_alt.json", "sha256": sha(alt)})
        p105.write_json(root / "data_map.json", data_map)
        from formal_ready_test_harness import run_formal_script
        proc = run_formal_script(SCAN, ["--case-dir", str(root), "--stage", "initial",
                                        "--snapshot", "data/holders_owners_alt.json"])
        assert proc.returncode == 0, proc.stdout + proc.stderr
        errors = fixture.gate.run(root, report, profile="new-analysis")
        check("F-03/2 EVM initial 同值换仓被拒", any(BINDING_ERROR in x for x in errors), str(errors))


def _solana_case(root: Path, owners_sha: str, *, initial_sha: str = "b" * 64,
                 final_sha: str | None = None) -> dict:
    """手搓一个 Solana new-analysis 的 data + 落盘 supply_receipt/终态 final scan。"""
    final_sha = initial_sha if final_sha is None else final_sha
    bundle = root / "supply_receipt.json"
    write_json(bundle, {"schema": "solana-observation-bundle/v1",
                        "holder_outputs": {"accounts": {"path": "holders_accounts.json",
                                                        "size": 1, "sha256": "a" * 64},
                                           "owners": {"path": "holders_owners.json",
                                                      "size": 2, "sha256": owners_sha}}})
    final_scan = root / "dist_rounds/round_1/distribution_scan.json"
    write_json(final_scan, {"schema": "distribution-scan/v1", "stage": "final",
                            "input_binding": {"snapshot": {"path": "data/holders_owners.json",
                                                           "sha256": final_sha, "size": 3}}})
    return {
        "distribution_scan.json": {"schema": "distribution-scan/v1", "stage": "initial",
                                   "input_binding": {"snapshot": {
                                       "path": "data/holders_owners.json",
                                       "sha256": initial_sha, "size": 3}}},
        "reconciliation_report.json": {"schema": "reconciliation-report/v2",
                                       "target": {"chain": "solana", "token": "t",
                                                  "as_of_block": 1},
                                       "checks": {"supply": {"status": "PASS",
                                                             "receipt": {"path": "supply_receipt.json",
                                                                         "sha256": sha(bundle)}}}},
        "distribution_rounds.json": {"schema": "distribution-rounds/v1",
                                     "rounds": [{"round_n": 1, "status": "NORMAL"}],
                                     "terminal": {"round_n": 1, "status": "NORMAL",
                                                  "final_scan_path": "dist_rounds/round_1/distribution_scan.json"}},
    }


def test_f03_gate_solana_not_skipped() -> None:
    fn = getattr(gate, "check_distribution_snapshot_binding", None)
    if fn is None:
        check("F-03/2 Solana 分支存在", False, "audit_release_gate 缺 check_distribution_snapshot_binding")
        return
    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve()
        data = _solana_case(root, "b" * 64)
        errors: list[str] = []
        fn(root, data, "solana", errors)
        check("F-03/2 Solana initial+终态 sha 相符放行", not errors, str(errors))

        data = _solana_case(root, "c" * 64)                # bound=c，initial=b → initial 不符
        errors = []
        fn(root, data, "solana", errors)
        check("F-03/2 Solana initial 同值换仓被拒", any(BINDING_ERROR in x for x in errors), str(errors))

        # F-B1 Solana 侧：initial 相符但终态 final 换仓 → 仍拒
        data = _solana_case(root, "b" * 64, final_sha="d" * 64)
        errors = []
        fn(root, data, "solana", errors)
        check("F-03/2 Solana 终态 final 换仓被拒", any("终态 final" in x for x in errors), str(errors))

        data = _solana_case(root, "b" * 64)
        bundle = json.loads((root / "supply_receipt.json").read_text())
        bundle["holder_outputs"].pop("owners")
        write_json(root / "supply_receipt.json", bundle)
        data["reconciliation_report.json"]["checks"]["supply"]["receipt"]["sha256"] = \
            sha(root / "supply_receipt.json")
        errors = []
        fn(root, data, "solana", errors)
        check("F-03/2 Solana bundle 缺 owners 绑定被拒", bool(errors), str(errors))


def test_fb4_second_layer_failclosed_branches() -> None:
    """F-B4：第二层三条 fail-closed 分支定向红线（M12/M13/M14），各只坏一处。"""
    fn = gate.check_distribution_snapshot_binding
    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve()
        # M12：找不到四查收据文件（receipt.path 指向不存在文件）
        data = {"distribution_scan.json": {"input_binding": {"snapshot": {"sha256": "b" * 64}}},
                "reconciliation_report.json": {"checks": {"balance": {
                    "receipt": {"path": "nonexist_receipt.json", "sha256": "0" * 64}}}}}
        errors: list[str] = []
        fn(root, data, "eth", errors)
        check("F-B4/M12 找不到四查收据文件必报错",
              any("找不到四查" in x for x in errors), str(errors))
        # M13：initial scan 缺 snapshot.sha256
        data = {"distribution_scan.json": {"input_binding": {"snapshot": {}}},
                "reconciliation_report.json": {"checks": {}}}
        errors = []
        fn(root, data, "eth", errors)
        check("F-B4/M13 initial 缺 snapshot.sha256 必报错",
              any("snapshot.sha256" in x for x in errors), str(errors))
        # M14：链族判不出（chain_family 对未注册链族抛 ValueError）
        data = {"distribution_scan.json": {"input_binding": {"snapshot": {"sha256": "b" * 64}}},
                "reconciliation_report.json": {"checks": {}}}
        errors = []
        fn(root, data, "sui-unregistered", errors)
        check("F-B4/M14 链族判不出必报错",
              any("无法判定链族" in x or "未登记链族" in x for x in errors), str(errors))


def test_f03_gate_solana_producer_field_present() -> None:
    src = (ROOT / "scripts/solana/scan_token_accounts.py").read_text(encoding="utf-8")
    check("F-03/2 Solana 生产者仍输出 holder_outputs.owners",
          'holder_outputs={"accounts": ref(accounts_out), "owners": ref(owners_out)}' in src,
          "scan_token_accounts.py 的 holder_outputs 形态已变")


# --------------------------------------------------------------------------
# P0-B1：final 轮 scan 的快照必须绑定 initial scan 的快照
# --------------------------------------------------------------------------

def test_p0b1_final_snapshot_swap_rejected() -> None:
    """P0-B1：final 轮换一份同值换仓快照 → final 生成即拒（不再放行到 A5/发布闸）。"""
    p105 = _p105()
    fixture = p105.fixture
    from formal_ready_test_harness import run_formal_script
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        report = fixture.build_case(root, historical=False)
        for name in p105.AUDIT_ONLY:
            (root / name).unlink(missing_ok=True)

        balances = {f"owner-{i:03d}": max(1, int(2_000_000 / (1.035 ** i))) for i in range(240)}
        snap = root / "data/holders_owners.json"
        p105.write_json(snap, balances)
        p105.bind_balance_receipt_to_snapshot(root, snap)
        total = sum(balances.values())
        p105.write_json(root / "supply_truth.json", {
            "schema": "supply-truth-receipt/v3", "verdict": "PASS", "exit_code": 0,
            "chain": "bsc", "onchain_total_supply": str(total), "replay_net": str(total),
            "mint_total": str(total), "burn_total": "0", "decision_rule": "primary_form1"})

        keys = sorted(balances)
        swapped = dict(balances)
        swapped[keys[0]], swapped[keys[-1]] = balances[keys[-1]], balances[keys[0]]
        alt = root / "data/holders_owners_alt.json"
        p105.write_json(alt, swapped)
        p105.write_json(root / "data_map.json", {"files": [
            {"path": "data/holders_owners.json", "sha256": sha(snap)},
            {"path": "data/holders_owners_alt.json", "sha256": sha(alt)}]})
        p105.write_json(root / "candidate_screening.json", {"auto_excluded_candidate": []})

        p = run_formal_script(SCAN, ["--case-dir", str(root), "--stage", "initial"])
        assert p.returncode == 0, p.stdout + p.stderr

        for name, value in {
            "handoff_manifest.json": {"consumer_min_schema": "handoff/v3", "status": "READY",
                                      "run_id": "fixture"},
            "identity_snapshot_receipt.json": {"schema": "identity-snapshot-receipt/v1"},
            "entity_freeze.json": {"schema": "entity-freeze/v1", "revisions": []},
            "analysis-state.json": {"chain": "bsc", "whale_groups": []},
            "facts.json": {"entities": {}}, "evidence.json": {"source": "fixture"},
            "a4_claims.json": {"schema": "a4-claims/v2", "claims": [{"id": "C1"}]},
        }.items():
            p105.write_json(root / name, value)
        for name in ("membership_ledger.json", "position_ledger.json",
                     "economic_control_ledger.json", "address_classification.json"):
            p105.write_json(root / name, {"rows": []})
        p105.write_json(root / "a4_seal.json", {
            "schema": "a4-seal/v4", "verdict": "PASS", "chain": "bsc",
            "workflow_type": "new-analysis", "revision": 1, "previous_seal": None,
            "charts_dir": "charts/final", "claims": [{"id": "C1", "verdict": "CONFIRMED"}]})

        # 合法 final（同一份快照）先证明放行
        ok = run_formal_script(SCAN, ["--case-dir", str(root), "--stage", "final", "--round", "1"])
        check("P0-B1 final 用同一份 initial 快照放行", ok.returncode == 0,
              f"rc={ok.returncode} {ok.stdout}{ok.stderr}")
        # 攻击：final 改吃 alt 换仓快照 → 必须拒
        swap = run_formal_script(SCAN, ["--case-dir", str(root), "--stage", "final", "--round", "1",
                                        "--snapshot", "data/holders_owners_alt.json"])
        check("P0-B1 final 换仓快照被拒", swap.returncode == 2,
              f"rc={swap.returncode} {swap.stdout}{swap.stderr}")


# --------------------------------------------------------------------------
# F-08：validate_scan 记录项三验 + P2-B5 白名单
# --------------------------------------------------------------------------

def _initial_case(td: Path, *, with_preflight=True) -> Path:
    d = td
    make_case(d, smooth(240))
    if with_preflight:
        write_json(d / "channels_preflight.json", {"schema": "channels-preflight/v1"})
    p = run_scan(d)
    assert p.returncode == 0, p.stdout + p.stderr
    return d


def test_f08_forged_records_rejected() -> None:
    variants = {
        "缺件": lambda e: e.update({"path": "does-not-exist.json"}),
        "错 sha": lambda e: e.update({"sha256": "0" * 64}),
        "错 size": lambda e: e.update({"size": e["size"] + 1}),
    }
    for label, mutate in variants.items():
        with tempfile.TemporaryDirectory() as td:
            d = _initial_case(Path(td))
            scan = json.loads((d / "distribution_scan.json").read_text())
            entries = scan["input_binding"]["upstream_receipts"]
            assert entries, "夹具没记上游收据，反例失去意义"
            mutate(entries[0])
            write_json(d / "distribution_scan.json", scan)
            errors = dist.validate_scan(d, "distribution_scan.json", "initial")
            check(f"F-08 记录项{label}被拒", bool(errors), str(errors))


def test_p2b5_receipt_path_whitelist() -> None:
    """P2-B5：记录项 path 钉白名单——记一个白名单外的合法文件也必须拒。"""
    with tempfile.TemporaryDirectory() as td:
        d = _initial_case(Path(td))
        # 案根放一个白名单外的真文件，并伪造成 upstream_receipt 记录项
        other = d / "supply_truth.json"                     # 真实存在、非白名单
        scan = json.loads((d / "distribution_scan.json").read_text())
        scan["input_binding"]["upstream_receipts"].append(
            {"path": "supply_truth.json", "sha256": sha(other), "size": other.stat().st_size})
        write_json(d / "distribution_scan.json", scan)
        errors = dist.validate_scan(d, "distribution_scan.json", "initial")
        check("P2-B5 白名单外记录项被拒（即便文件真存在且 sha/size 对）",
              any("白名单" in x or "upstream" in x.lower() or "上游收据" in x for x in errors),
              str(errors))


def test_f08_unrecorded_disk_receipt_passes() -> None:
    with tempfile.TemporaryDirectory() as td:
        d = _initial_case(Path(td), with_preflight=False)
        write_json(d / "channels_preflight.json", {"schema": "channels-preflight/v1"})
        scan = json.loads((d / "distribution_scan.json").read_text())
        assert scan["input_binding"]["upstream_receipts"] == []
        errors = dist.validate_scan(d, "distribution_scan.json", "initial")
        check("F-08 磁盘有收据但 scan 未记录仍 PASS", not errors, str(errors))


def test_f08_absent_receipt_is_skipped_not_fatal() -> None:
    with tempfile.TemporaryDirectory() as td:
        d = _initial_case(Path(td), with_preflight=False)
        scan = json.loads((d / "distribution_scan.json").read_text())
        check("F-08 收据缺席＝跳过记录不报错",
              scan["input_binding"]["upstream_receipts"] == [] and scan["exit_code"] == 0,
              str(scan["input_binding"]["upstream_receipts"]))


def test_f08_illegal_receipt_producer_rejected() -> None:
    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "case"
        d.mkdir()
        make_case(d, smooth(240))
        outside = Path(td) / "outside_preflight.json"
        write_json(outside, {"schema": "channels-preflight/v1"})
        os.symlink(outside, d / "channels_preflight.json")
        p = run_scan(d)
        check("F-08 上游收据是符号链接 → 生产侧 exit 2",
              p.returncode == 2 and "上游收据" in (p.stdout + p.stderr),
              f"rc={p.returncode} {p.stdout}{p.stderr}")


def test_f08_docs_state_record_semantics() -> None:
    text = (ROOT / "references/scan-schemas.md").read_text(encoding="utf-8")
    check("F-08 scan-schemas 已改口为记录性收据在场即三验",
          "记录性收据" in text and "在场即三验" in text and "optional" in text,
          "scan-schemas.md 未同批改口")


def test_p1b2_docs_shadow_key_wording() -> None:
    """P1-B2：scan-schemas 把 total_supply_raw 当正式名的错误口径改掉。"""
    text = (ROOT / "references/scan-schemas.md").read_text(encoding="utf-8")
    check("P1-B2 scan-schemas 改用 mint_total 闭合口径且点明影子键",
          "mint_total" in text and ("影子键" in text or "onchain_total_supply" in text),
          "scan-schemas.md 未更新闭合锚点口径")


def test_fb5_docs_retro_not_deadlock_wording() -> None:
    """F-B5：改口径不改代码——scan-schemas 承认重验须重跑生产者、不闭合按 data_broken 拒收。"""
    text = (ROOT / "references/scan-schemas.md").read_text(encoding="utf-8")
    check("F-B5 scan-schemas 承认重验须重跑当前版本生产者且不闭合按 data_broken 拒",
          "重跑当前版本生产者" in text and "data_broken" in text
          and ("刻意收紧" in text or "不是回归" in text),
          "scan-schemas.md 未按 F-B5 改口径")


def test_fb6_docs_binding_strength_diff() -> None:
    """F-B6③：scan-schemas 如实写出 EVM/Solana 两侧绑定强度差异。"""
    text = (ROOT / "references/scan-schemas.md").read_text(encoding="utf-8")
    check("F-B6③ scan-schemas 写明 Solana holder_outputs.owners 暂无 validator 实物锚",
          "receipt_validate" in text and "holder_outputs" in text
          and ("无 validator" in text or "无实物锚" in text or "尚无实物锚" in text),
          "scan-schemas.md 未写明两侧绑定强度差异")


def test_c_deadsink_synthetic_green_under_mint_anchor() -> None:
    """锚点三向 c：既有 dead-sink 合成绿例（sum=mint≠net）在 mint 锚点下仍绿。"""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        private = smooth(240)
        flow = sum(private.values())
        dead = flow // 4                                   # dead 占 mint 的 20%
        mint = flow + dead
        rows = dict(private)
        rows[DEAD] = dead
        make_case(d, rows, mint=mint, onchain=mint, net=flow, chain="bsc",
                  with_replay_stats=True, decision_rule="sink_fallback_form2",
                  burn_form="dead_sink",
                  excluded=[{"address": DEAD, "bucket": "burn_sentinel"}])
        p = run_scan(d)
        out = json.loads((d / "distribution_scan.json").read_text()) \
            if (d / "distribution_scan.json").is_file() else {}
        den = out.get("denominators") or {}
        check("锚点c 合成 dead-sink 20%（sum=mint≠net）在 mint 锚点下仍绿",
              p.returncode == 0 and out.get("exit_code") == 0
              and den.get("total_supply_raw") == str(mint)
              and den.get("net_supply_raw") == str(flow) and mint != flow,
              f"rc={p.returncode} den={den} {p.stdout}{p.stderr}")


def main() -> int:
    test_f03_snapshot_gap_rejected()
    test_f03_overshoot_rejected()
    test_p1b3_form1_real_receipt()
    test_p1b3_form2_real_receipt()
    test_p1b2_shadow_key_cannot_close()
    test_p2b4_exact_closure_window()
    test_f03_closure_anchor_no_shadow_dependency()
    test_nb1_anchor_prefers_bound_receipt()
    test_nb1_stale_root_file_ignored()
    test_nb1_bound_stats_cross_check()
    test_nb2_root_stats_symlink_failclosed()
    test_nb3_rounds_snapshot_sha_consistency()
    test_nb4_docs_denominator_semantics()
    test_f03_gate_evm_same_total_swap()
    test_f03_gate_solana_not_skipped()
    test_fb4_second_layer_failclosed_branches()
    test_f03_gate_solana_producer_field_present()
    test_p0b1_final_snapshot_swap_rejected()
    test_f08_forged_records_rejected()
    test_p2b5_receipt_path_whitelist()
    test_f08_unrecorded_disk_receipt_passes()
    test_f08_absent_receipt_is_skipped_not_fatal()
    test_f08_illegal_receipt_producer_rejected()
    test_f08_docs_state_record_semantics()
    test_p1b2_docs_shadow_key_wording()
    test_fb5_docs_retro_not_deadlock_wording()
    test_fb6_docs_binding_strength_diff()
    test_c_deadsink_synthetic_green_under_mint_anchor()
    failed = [name for name, ok, _ in RESULTS if not ok]
    if failed:
        print(f"BATCH B FAIL {len(failed)}/{len(RESULTS)}: " + "; ".join(failed))
        return 1
    print(f"PASS batch B F-03/F-08 regressions {len(RESULTS)}/{len(RESULTS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
