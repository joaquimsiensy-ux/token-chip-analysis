#!/usr/bin/env python3
"""APU 案（ANOM-012）暴露的存量迁移/生产者缺口三件工单的契约测试。

工单一：replay 引擎必须在 replay_stats.json 写覆盖截止块 max_block（=preflight
  声明 expected_to−1，来源是重验过的 preflight 而非引擎自报），verify_recon 以它
  断言重放范围对齐对账目标块——此前 producer 从不写、consumer 必读，真实 EVM
  管线首跑必断（测试全绿是因为 fixture 手写 stats 掩盖了断链）。
工单二：无 schema 字段的太古 done.json（v1 采集时代）必须有官方迁移路径
  （fetch_hypersync_v2 --refresh-manifests 同源重验升级），禁止手拼绑定件。
工单三：旧 −1 产物格式与现行校验器的漂移必须有官方迁移命令（fail-closed）。
"""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
EVM = ROOT / "scripts/evm"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(EVM))
sys.path.insert(0, str(ROOT / "scripts/lib"))

from evm_channel_fixture import write_csv_channel_receipt  # noqa: E402

FAILS = []
Z = "0x0000000000000000000000000000000000000000"
TOKEN = "0x" + "a1" * 20
ADDR_A = "0x" + "b2" * 20
ADDR_B = "0x" + "c3" * 20


def check(name, cond, detail=""):
    if not cond:
        FAILS.append(name)
        print(f"FAIL  {name}  {detail}")
    else:
        print(f"ok    {name}")


def run(cmd, cwd=None):
    return subprocess.run([sys.executable] + [str(x) for x in cmd],
                          cwd=cwd, capture_output=True, text=True, timeout=300)


def _write_v1_pipeline(tmp, expected_from=0, expected_to=1000):
    """最小 v1csv 合规通道：3 笔事件 + collector/channel receipt + channels.json。"""
    rows = [
        (10, "2026-01-01T12:00:00", "0x" + "01" * 32, Z, ADDR_A, 10**21, "u:log:0"),
        (20, "2026-01-02T12:00:00", "0x" + "02" * 32, ADDR_A, ADDR_B, 3 * 10**20, "u:log:1"),
        (30, "2026-01-03T12:00:00", "0x" + "03" * 32, ADDR_B, ADDR_A, 10**19, "u:log:2"),
    ]
    data = Path(tmp) / "transfers.csv"
    with data.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["block", "ts", "tx", "from", "to", "value", "uniqueId"])
        w.writerows(rows)
    write_csv_channel_receipt(tmp, "t", data, TOKEN, expected_from, expected_to)
    json.dump({"schema": "evm-channels/v2", "token": TOKEN,
               "expected_from": expected_from, "expected_to": expected_to,
               "channels": [{"path": "transfers.csv", "lo": expected_from,
                             "hi": expected_to, "tag": "t", "format": "v1csv",
                             "receipt": "t.receipt.json"}]},
              open(os.path.join(tmp, "channels.json"), "w"))


def _run_verify_recon(tmp, stats_path, end_block, out_name):
    """跑 verify_recon 到早期检查段（config 不带 RPC）；返回 (proc, receipt|None)。"""
    cfg = Path(tmp) / "vr_config.json"
    json.dump({"token": TOKEN, "decimals": 18, "total_supply_human": "1000"},
              open(cfg, "w"))
    gmgn = Path(tmp) / "vr_gmgn.csv"
    gmgn.write_text("address,pct\n", encoding="utf-8")
    balances = Path(tmp) / "duck" / "balances_final.json"
    out = Path(tmp) / out_name
    p = run([EVM / "verify_recon.py", "--config", cfg, "--balances", balances,
             "--replay-stats", stats_path, "--gmgn", gmgn, "--chain", "eth",
             "--token", TOKEN, "--end-block", str(end_block), "--out", out])
    # ERROR 时 receipt kernel 落到 <stem>.error.<run_id>.json 侧路径，canonical 不动
    candidates = [out] + sorted(out.parent.glob(out.stem + ".error.*json"))
    receipt = next((json.load(open(c)) for c in candidates if c.is_file()), None)
    return p, receipt


def ticket1_replay_stats_max_block():
    """工单一三件套：真实引擎产物必须自带覆盖截止块，verify_recon 契约走通。"""
    expected_to = 1000
    with tempfile.TemporaryDirectory() as raw_tmp:
        # macOS 的 /var→/private/var 符号链接会被 receipt kernel 的路径安全检查拒绝
        tmp = str(Path(raw_tmp).resolve())
        _write_v1_pipeline(tmp, 0, expected_to)
        duck_out = Path(tmp) / "duck"
        p = run([EVM / "replay_duck.py", "--channels", "channels.json",
                 "--out-dir", duck_out, "--threads", "2", "--mem-limit", "2GB"],
                cwd=tmp)
        check("t1.duck 引擎跑通", p.returncode == 0, p.stdout[-400:] + p.stderr[-400:])
        stats_path = duck_out / "replay_stats.json"
        stats = json.load(open(stats_path)) if stats_path.is_file() else {}
        # a. 原反例：真实 duck 产物必须写 max_block == expected_to−1（采集覆盖语义，
        #    非最后事件块——尾部空块不改变覆盖声明）
        check("t1.duck stats 写覆盖截止块 max_block",
              stats.get("max_block") == expected_to - 1,
              f"max_block={stats.get('max_block')!r}")

        # b. 同族变体：replay_pass1 同输入同深度
        pass1_out = Path(tmp) / "old"
        pass1_out.mkdir()
        p1 = run([EVM / "replay_pass1.py", "--channels", "channels.json",
                  "--out-dir", pass1_out], cwd=tmp)
        check("t1.pass1 引擎跑通", p1.returncode == 0, p1.stdout[-300:] + p1.stderr[-300:])
        s1_path = pass1_out / "replay_stats.json"
        s1 = json.load(open(s1_path)) if s1_path.is_file() else {}
        check("t1.pass1 stats 同族同深度写 max_block",
              s1.get("max_block") == expected_to - 1,
              f"max_block={s1.get('max_block')!r}")

        # a2. 消费连线：verify_recon 吃真实 duck 产物必须通过截止块检查
        #（config 不带 RPC → 修复后应推进到"缺 RPC"，而非死于截止块契约）
        if stats_path.is_file():
            p2, receipt = _run_verify_recon(tmp, stats_path, expected_to - 1, "vr1.json")
            err = str((receipt or {}).get("error", ""))
            check("t1.verify_recon 通过真实产物的截止块检查",
                  "截止块" not in err and "缺 RPC" in err,
                  f"exit={p2.returncode} error={err!r}")

            # c. 失败分支：篡改 max_block 后 verify_recon 必须 fail-closed 拒绝
            bad = dict(stats)
            bad["max_block"] = expected_to + 7
            bad.pop("last_block", None)
            bad_path = Path(tmp) / "bad_stats.json"
            json.dump(bad, open(bad_path, "w"))
            p3, r3 = _run_verify_recon(tmp, bad_path, expected_to - 1, "vr2.json")
            err3 = str((r3 or {}).get("error", ""))
            check("t1.篡改 max_block 被 verify_recon 拒绝",
                  p3.returncode != 0 and "截止块" in err3,
                  f"exit={p3.returncode} error={err3!r}")


def _make_prehistoric_v2_run(root, run_from, rows, blocks, *, done_extra=None,
                             token=TOKEN, url="https://eth.hypersync.xyz"):
    """造太古 v2 采集 run：真实 Parquet + 无 schema 字段的五键 done.json。

    模拟 v1 采集时代的存量数据（非伪造 PASS 证据——太古 done 本来就无任何回执）；
    Parquet 列集/类型对齐真实存量（APU 案实况：UBIGINT 块号 + hex VARCHAR 时间戳）。
    rows: [(log_index, tx, block_hash, block_number, data, topic1, topic2)]
    blocks: [(number, hex_ts)]
    """
    import duckdb
    run_dir = Path(root) / f"run_{run_from}"
    run_dir.mkdir(parents=True)
    con = duckdb.connect()
    con.execute("""CREATE TABLE logs (log_index UBIGINT, transaction_hash VARCHAR,
        block_hash VARCHAR, block_number UBIGINT, data VARCHAR,
        topic1 VARCHAR, topic2 VARCHAR)""")
    con.executemany("INSERT INTO logs VALUES (?,?,?,?,?,?,?)", rows)
    con.execute(f"COPY logs TO '{run_dir / 'logs.parquet'}' (FORMAT parquet)")
    con.execute("CREATE TABLE blocks (number UBIGINT, timestamp VARCHAR)")
    con.executemany("INSERT INTO blocks VALUES (?,?)", blocks)
    con.execute(f"COPY blocks TO '{run_dir / 'blocks.parquet'}' (FORMAT parquet)")
    con.close()
    done = {"next_block": max(b for b, _ in blocks) + 1, "from_block": run_from,
            "elapsed_s": 1.0, "token": token, "url": url}
    done.update(done_extra or {})
    json.dump(done, open(run_dir / "done.json", "w"))
    return run_dir


def _topic_addr(addr):
    return "0x" + addr[2:].rjust(64, "0")


def _data_value(value):
    return "0x" + format(value, "x").rjust(64, "0")


def ticket2_prehistoric_v2_migration():
    """工单二三件套：太古 done 官方迁移→receipt→preflight→真实引擎全链。"""
    refresh = lambda outdir: run([EVM / "fetch_hypersync_v2.py",
                                  "--refresh-manifests", "--outdir", outdir])
    recover = lambda outdir: run([EVM / "fetch_hypersync_v2.py",
                                  "--recover-identity", "--outdir", outdir])
    with tempfile.TemporaryDirectory() as raw_tmp:
        tmp = Path(raw_tmp).resolve()
        v2root = tmp / "v2"
        rows = [
            (0, "0x" + "01" * 32, "0x" + "d1" * 32, 100,
             _data_value(10**21), _topic_addr(Z), _topic_addr(ADDR_A)),
            (1, "0x" + "02" * 32, "0x" + "d2" * 32, 150,
             _data_value(3 * 10**20), _topic_addr(ADDR_A), _topic_addr(ADDR_B)),
        ]
        blocks = [(100, "0x65e6f973"), (150, "0x65e70000")]
        _make_prehistoric_v2_run(v2root, 100, rows, blocks)
        expected_to = 151  # done.next_block

        # a. 先显式恢复 unknown-lineage identity，再由官方迁移入口接住太古 done。
        recovered = recover(v2root)
        check("t2.太古目录显式恢复 identity 成功", recovered.returncode == 0,
              recovered.stdout[-200:] + recovered.stderr[-200:])
        p = refresh(v2root)
        check("t2.太古 done 官方迁移成功",
              p.returncode == 0 and "upgraded=1" in p.stdout,
              f"exit={p.returncode} out={p.stdout[-200:]} err={p.stderr[-200:]}")
        done_after = json.load(open(v2root / "run_100" / "done.json"))
        check("t2.迁移后 done 升为现行 schema 且边界重建",
              done_after.get("schema") == "hypersync-v2-done/v4"
              and done_after.get("capture_from") == 100
              and done_after.get("to_block") == expected_to
              and done_after.get("refreshed_from_schema") == "pre-schema-v1"
              and done_after.get("collector") is None
              and done_after.get("collector_provenance") == "legacy-unattributed"
              and isinstance(done_after.get("files"), dict),
              f"done={ {k: done_after.get(k) for k in ('schema', 'capture_from', 'to_block')} }")
        check("t2.恢复签发 capture_identity.json",
              (v2root / "capture_identity.json").is_file())
        check("t2.迁移幂等（重跑 already_v4）",
              "already_v4=1" in refresh(v2root).stdout)

        # 连线：官方 receipt 生成器 → preflight → 真实引擎（工单一 stream 同族深度）
        receipt_out = tmp / "v2.receipt.json"
        p = run([EVM / "make_channel_receipt.py", "--data", v2root, "--format", "v2",
                 "--token", TOKEN, "--lo", "100", "--hi", str(expected_to),
                 "--tag", "v2", "--out", receipt_out])
        check("t2.迁移后可产 evm-channel-receipt/v2", p.returncode == 0,
              p.stdout[-200:] + p.stderr[-200:])
        json.dump({"schema": "evm-channels/v2", "token": TOKEN,
                   "expected_from": 100, "expected_to": expected_to,
                   "channels": [{"path": str(v2root), "lo": 100, "hi": expected_to,
                                 "tag": "v2", "format": "v2",
                                 "receipt": str(receipt_out)}]},
                  open(tmp / "channels.json", "w"))
        stream_out = tmp / "stream"
        p = run([EVM / "replay_stream.py", "--channels", tmp / "channels.json",
                 "--out-dir", stream_out, "--threads", "2", "--mem-limit", "2GB"])
        stream_stats_path = stream_out / "replay_stats.json"
        stream_stats = (json.load(open(stream_stats_path))
                        if stream_stats_path.is_file() else {})
        check("t2.迁移后通过 preflight 且 replay_stream 跑通",
              p.returncode == 0 and stream_stats.get("gate_pass") is True,
              f"exit={p.returncode} err={p.stderr[-300:]}")
        check("t1.stream stats 同族同深度写 max_block",
              stream_stats.get("max_block") == expected_to - 1,
              f"max_block={stream_stats.get('max_block')!r}")

    # b. 同族变体：缺 next_block 的太古 done 拒绝迁移
    with tempfile.TemporaryDirectory() as raw_tmp:
        tmp = Path(raw_tmp).resolve()
        v2root = tmp / "v2"
        _make_prehistoric_v2_run(v2root, 100,
                                 [(0, "0x" + "01" * 32, "0x" + "d1" * 32, 100,
                                   _data_value(10**21), _topic_addr(Z), _topic_addr(ADDR_A))],
                                 [(100, "0x65e6f973")])
        done_path = v2root / "run_100" / "done.json"
        d = json.load(open(done_path))
        del d["next_block"]
        json.dump(d, open(done_path, "w"))
        p = recover(v2root)
        check("t2.缺 next_block 的太古 done 拒绝恢复",
              p.returncode != 0 and "边界" in p.stderr,
              f"exit={p.returncode} err={p.stderr[-200:]}")

    # c. 失败分支（两阶段事务）：一个 run 数据越界 → 全拒且好 run 的 done 不被改写
    with tempfile.TemporaryDirectory() as raw_tmp:
        tmp = Path(raw_tmp).resolve()
        v2root = tmp / "v2"
        _make_prehistoric_v2_run(v2root, 100,
                                 [(0, "0x" + "01" * 32, "0x" + "d1" * 32, 100,
                                   _data_value(10**21), _topic_addr(Z), _topic_addr(ADDR_A))],
                                 [(100, "0x65e6f973")])
        # run_200 声明 [200,251) 但塞进块 300 的行——数据实物越出 done 声明
        _make_prehistoric_v2_run(v2root, 200,
                                 [(0, "0x" + "03" * 32, "0x" + "d3" * 32, 300,
                                   _data_value(10**20), _topic_addr(ADDR_A), _topic_addr(ADDR_B))],
                                 [(300, "0x65e71111")], done_extra={"next_block": 251})
        good_before = (v2root / "run_100" / "done.json").read_bytes()
        p = recover(v2root)
        check("t2.越界 run 使恢复整体拒绝（fail-closed）", p.returncode != 0,
              f"exit={p.returncode} out={p.stdout[-150:]}")
        check("t2.两阶段事务：好 run 的 done 未被改写",
              (v2root / "run_100" / "done.json").read_bytes() == good_before)
        check("t2.整体拒绝时不补建 capture_identity",
              not (v2root / "capture_identity.json").exists())


def _sha256(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _make_legacy_case(tmp):
    """造旧 −1 案目录：data_map 带 sha256: 前缀、candidate_universe 只有 cid、
    anchor_plan 无 kernel receipt——APU 案 ANOM-012 三处漂移的最小化石。"""
    case = Path(tmp) / "case"
    case.mkdir()
    snap = case / "owners_snapshot.json"
    snap.write_text(json.dumps({ADDR_A: "1000"}), encoding="utf-8")
    json.dump({"schema": "data-map/v1", "case_id": "legacy",
               "items": {"snap": {"path": "owners_snapshot.json",
                                  "bytes": snap.stat().st_size,
                                  "sha256": "sha256:" + _sha256(snap)},
                         "gone": {"path": "data/cleaned_away.parquet",
                                  "sha256": "sha256:" + "ab" * 32},
                         "note": {"path": "readme.txt",
                                  "sha256": "not-a-hash-value"}}},
              open(case / "data_map.json", "w"))
    json.dump({"schema": "candidate-universe/v1",
               "candidates": [
                   {"cid": "C001", "address": ADDR_A, "reasons": ["current_above_line"]},
                   {"cid": "C002", "address": ADDR_B, "reasons": ["historical_peak"]},
               ]},
              open(case / "candidate_universe.json", "w"))
    json.dump({"schema": "anchor-plan/v2", "matrix_points": []},
              open(case / "anchor_plan.json", "w"))
    return case


def ticket3_legacy_case_migration():
    """工单三三件套：旧 −1 产物格式漂移的官方迁移命令（fail-closed）。"""
    migrate = ROOT / "scripts/report/migrate_legacy_case.py"

    # a. 原反例：旧案三处漂移 → 官方迁移 → 现行校验器消费通过
    with tempfile.TemporaryDirectory() as raw_tmp:
        case = _make_legacy_case(Path(raw_tmp).resolve())
        sys.path.insert(0, str(ROOT / "scripts/report"))
        from holder_distribution_scan import verify_data_map  # noqa: E402
        try:
            verify_data_map(case, "owners_snapshot.json", case / "owners_snapshot.json")
            pre_rejected = False
        except ValueError:
            pre_rejected = True
        check("t3.迁移前 data_map 前缀被现行校验器拒", pre_rejected)

        p = run([migrate, "--case-dir", case])
        check("t3.迁移命令存在且报告缺 anchor receipt（exit 2）",
              p.returncode == 2 and "anchor_plan" in (p.stdout + p.stderr),
              f"exit={p.returncode} out={p.stdout[-250:]} err={p.stderr[-250:]}")
        dm = json.load(open(case / "data_map.json"))
        check("t3.data_map 前缀已剥且非哈希值未被误剥",
              dm["items"]["snap"]["sha256"] == _sha256(case / "owners_snapshot.json")
              and dm["items"]["gone"]["sha256"] == "ab" * 32
              and dm["items"]["note"]["sha256"] == "not-a-hash-value",
              f"snap={dm['items']['snap']['sha256'][:20]}")
        try:
            verify_data_map(case, "owners_snapshot.json", case / "owners_snapshot.json")
            post_ok = True
        except ValueError as exc:
            post_ok = False
            print("   verify_data_map:", exc)
        check("t3.迁移后现行校验器消费通过", post_ok)
        cu = json.load(open(case / "candidate_universe.json"))
        check("t3.candidate 条目补 id（保留 cid）",
              all(c.get("id") == c.get("cid") and "id" in c and "address" in c
                  and "reasons" in c for c in cu["candidates"]))
        check("t3.迁移产备份",
              bool(list(case.glob("data_map.json.bak_migrate_*"))
                   and list(case.glob("candidate_universe.json.bak_migrate_*"))))
        # 幂等：重跑只剩 anchor receipt 待重跑，不再产新备份
        n_bak = len(list(case.glob("*.bak_migrate_*")))
        p2 = run([migrate, "--case-dir", case])
        check("t3.迁移幂等（重跑不重复改写）",
              p2.returncode == 2 and len(list(case.glob("*.bak_migrate_*"))) == n_bak,
              f"exit={p2.returncode}")

    # b. 同族变体：条目既无 id 也无 cid → 拒绝迁移该文件
    with tempfile.TemporaryDirectory() as raw_tmp:
        case = _make_legacy_case(Path(raw_tmp).resolve())
        cu_path = case / "candidate_universe.json"
        cu = json.load(open(cu_path))
        del cu["candidates"][1]["cid"]
        json.dump(cu, open(cu_path, "w"))
        before = cu_path.read_bytes()
        p = run([migrate, "--case-dir", case])
        check("t3.无 id 无 cid 条目拒绝迁移且不改写",
              p.returncode == 2 and cu_path.read_bytes() == before,
              f"exit={p.returncode}")

    # c. 失败分支：登记文件哈希失配 → data_map 拒绝洗白、原文件不动
    with tempfile.TemporaryDirectory() as raw_tmp:
        case = _make_legacy_case(Path(raw_tmp).resolve())
        (case / "owners_snapshot.json").write_text("{\"tampered\": true}",
                                                   encoding="utf-8")
        dm_path = case / "data_map.json"
        before = dm_path.read_bytes()
        p = run([migrate, "--case-dir", case])
        check("t3.登记哈希失配时拒绝迁移 data_map（fail-closed）",
              p.returncode == 2 and dm_path.read_bytes() == before
              and "失配" in (p.stdout + p.stderr),
              f"exit={p.returncode} out={p.stdout[-200:]}")


def main():
    ticket1_replay_stats_max_block()
    ticket2_prehistoric_v2_migration()
    ticket3_legacy_case_migration()
    if FAILS:
        print(f"\n{len(FAILS)} 项失败: {FAILS}")
        sys.exit(1)
    print("\nPASS: APU 存量缺口工单契约测试全绿")


if __name__ == "__main__":
    main()
