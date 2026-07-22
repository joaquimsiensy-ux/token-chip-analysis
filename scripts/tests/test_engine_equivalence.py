#!/usr/bin/env python3
"""新旧重放引擎等价性性质测试（hypothesis 随机边角数据，A1 回归门禁的活体部分）。

随机生成转账流——覆盖 mint / burn(0x0+dead) / 自转 / 同块多事件 / value=0 /
38+ 位大值(触 VARINT 路径) / 无序阵营映射 / 负余额盘(gate fail 场景)——分别喂给
旧引擎（replay_pass1+replay_pass2）与 DuckDB 引擎（replay_duck），用 golden_baseline
契约做 7 项对表，断言全等。

已知有意行为差异（不在等价断言范围）：
  - 同 (tag,tx,li) 键不同内容：旧=静默 keep-last，新=fail-closed 硬退（生成器不生成此类）
  - 新引擎 replay_stats 多 reject 记账扩展字段（契约键对比时忽略）
环境无 duckdb 时整测试 SKIP（离线全家桶不因缺依赖挂）。
用法：python3 scripts/tests/test_engine_equivalence.py   （约 30-60 秒）
"""
import datetime, json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
EVM = os.path.join(HERE, "..", "evm")
sys.path.insert(0, os.path.join(HERE, "..", "bench"))

try:
    import duckdb  # noqa: F401
except ImportError:
    print("SKIP: duckdb 未安装，等价性测试跳过")
    sys.exit(0)
try:
    from hypothesis import given, settings, strategies as st, HealthCheck
except ImportError:
    print("SKIP: hypothesis 未安装，等价性测试跳过")
    sys.exit(0)

import golden_baseline as gb

Z = "0x0000000000000000000000000000000000000000"
DEAD = "0x000000000000000000000000000000000000dead"
ADDRS = [f"0x{i:040x}" for i in range(0xa1, 0xa7)]   # 6 个普通地址


def _write_inputs(tmp, events):
    """events: [(from,to,value,block_step)] -> v1 7列 CSV + channels/camps。"""
    rows, blk, li = [], 100, 0
    day0 = datetime.date(2026, 1, 1)
    for frm, to, val, step in events:
        blk += step
        ts = (day0 + datetime.timedelta(days=blk // 4)).isoformat() + "T12:00:00"
        tx = f"0x{li:064x}"
        rows.append((blk, ts, tx, frm, to, val, f"{tx}:log:{li}"))
        li += 1
    with open(os.path.join(tmp, "transfers.csv"), "w") as f:
        f.write("block,ts,tx,from,to,value,uniqueId\n")
        for r in rows:
            f.write(",".join(str(x) for x in r) + "\n")
    json.dump({"channels": [{"path": "transfers.csv", "lo": 0,
                             "hi": 99999999999, "tag": "t"}]},
              open(os.path.join(tmp, "channels.json"), "w"))
    json.dump({"camps": {"阵营A": [ADDRS[0], ADDRS[1]], "阵营B": [ADDRS[2]],
                         "销毁": [DEAD]},
               "entities": {"实体X": [ADDRS[1], ADDRS[2]]}},
              open(os.path.join(tmp, "camps.json"), "w"))


def _run(tmp, cmd):
    p = subprocess.run([sys.executable] + cmd, cwd=tmp,
                       capture_output=True, text=True, timeout=120)
    return p


# 事件生成：首笔保证 mint>0（旧 pass2 以 mint_total 为分母，=0 会除零——两引擎同约束）
_addr = st.sampled_from(ADDRS)
_to_any = st.sampled_from(ADDRS + [Z, DEAD])
_val = st.one_of(st.integers(0, 10**21),
                 st.integers(10**37, 10**45))          # 大值段触 VARINT 路径
_step = st.sampled_from([0, 0, 1, 1, 5])               # 0=同块多事件
_ev = st.tuples(st.sampled_from(ADDRS + [Z]), _to_any, _val, _step)


@settings(max_examples=10, deadline=None,
          suppress_health_check=[HealthCheck.too_slow])
@given(first_mint=st.integers(10**18, 10**22), evs=st.lists(_ev, min_size=0, max_size=40))
def equivalence_case(first_mint, evs):
    events = [(Z, ADDRS[0], first_mint, 1)] + list(evs)
    with tempfile.TemporaryDirectory() as tmp:
        _write_inputs(tmp, events)
        old_out, new_out = os.path.join(tmp, "old"), os.path.join(tmp, "new")
        os.makedirs(old_out)
        p1 = _run(tmp, [os.path.join(EVM, "replay_pass1.py"),
                        "--channels", "channels.json", "--out-dir", old_out])
        assert p1.returncode == 0, f"旧 pass1 异常退出:\n{p1.stdout}\n{p1.stderr}"
        p2 = _run(tmp, [os.path.join(EVM, "replay_pass2.py"), "camps.json",
                        "--data-dir", old_out])
        assert p2.returncode == 0, f"旧 pass2 异常退出:\n{p2.stdout}\n{p2.stderr}"
        pd = _run(tmp, [os.path.join(EVM, "replay_duck.py"),
                        "--channels", "channels.json", "--out-dir", new_out,
                        "--camps", "camps.json", "--emit-csv",
                        "--threads", "2", "--mem-limit", "2GB"])
        # gate fail（负余额盘）时新引擎 exit 4 属预期；其余非零=真异常
        assert pd.returncode in (0, 4), f"replay_duck 异常退出:\n{pd.stdout}\n{pd.stderr}"
        sa, sb = gb.snapshot(old_out, "old"), gb.snapshot(new_out, "new")
        for k in gb.STATS_CONTRACT:
            assert sa["replay_stats"].get(k) == sb["replay_stats"].get(k), \
                f"stats.{k} 不等: {sa['replay_stats'].get(k)} vs {sb['replay_stats'].get(k)}\n输入:{events}"
        for k in ["merged_csv", "balances_final", "peaks", "mint_ledger",
                  "camp_series", "entity_series"]:
            assert sa[k] == sb[k], f"{k} 不等\n输入:{events}"


def main():
    equivalence_case()
    print("PASS: 新旧引擎等价性 10 例随机边角数据全过（含 VARINT 大值/负余额/同块多事件）")


if __name__ == "__main__":
    main()
