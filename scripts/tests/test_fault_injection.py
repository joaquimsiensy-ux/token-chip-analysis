#!/usr/bin/env python3
"""故障注入盲测烟雾集（3.18.0，@CX 融合方案第一档 Top2 起步版）。

golden_baseline 只能证明"新旧引擎一致"，证不了"两者都对"——本集在已知答案的
迷你账本上注入已知故障，断言引擎的**发现/拒绝行为**本身：
  F1 中段缺块（转账链断裂）   → 负余额指纹必须暴露（neg_balance_addrs>0 或 gate 失败）
  F2 同键异值（重组冲突形态） → replay_duck 必须硬退（fail-loud，绝不静默择一）
  F3 mint 事件缺失            → 期初 0 转出=负余额，gate 必须失败
  F4 尾部截断（QUQ 快照缺块实案形态）→ **盲区固定化**：供给闭合对"借贷两边同缺"
     免疫（gate 照过、负余额 0）——断言"抓不到"以钉死已知盲区，防有人误以为
     gate 覆盖了它；该洞的真防线=采集侧 done.json 前置完整性检查（evm §5 第 5 查）
  F5 通道段重叠声明            → 启动即 SystemExit 拦截（互斥硬约束）

新故障形态实战出现一次，就加一个 F 用例——盲区清单必须随事故增长。
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPLAY = os.path.join(HERE, "..", "evm", "replay_duck.py")

A, B, C, D = ("0x" + c * 40 for c in "abcd")
ZERO = "0x" + "0" * 40
HDR = "block,ts,tx,from,to,value,uniqueId\n"

# 基准账本：mint 1000 -> A；A->B 400；B->C 150；C->D 50。终态 A600 B250 C100 D50，和=1000
BASE_ROWS = [
    (100, 1700000000, "0xt1", ZERO, A, 1000, "log_0"),
    (110, 1700000600, "0xt2", A, B, 400, "log_0"),
    (120, 1700001200, "0xt3", B, C, 150, "log_0"),
    (130, 1700001800, "0xt4", C, D, 50, "log_0"),
]


def write_case(tmp, rows, hi=99999):
    csv_p = os.path.join(tmp, "part.csv")
    with open(csv_p, "w") as f:
        f.write(HDR)
        for r in rows:
            f.write(",".join(str(x) for x in r) + "\n")
    ch_p = os.path.join(tmp, "ch.json")
    json.dump({"channels": [{"lo": 0, "hi": hi, "tag": "t", "path": csv_p}]}, open(ch_p, "w"))
    return ch_p


def run_replay(ch_p, out_dir):
    p = subprocess.run([sys.executable, REPLAY, "--channels", ch_p, "--out-dir", out_dir],
                       capture_output=True, text=True)
    stats = {}
    sp = os.path.join(out_dir, "replay_stats.json")
    if os.path.exists(sp):
        stats = json.load(open(sp))
    return p.returncode, stats, p.stdout + p.stderr


def case_dir():
    return tempfile.mkdtemp(prefix="fault_")


def main():
    # F0 基准健康：合法账本必须全绿（其余用例的对照组）
    t = case_dir()
    rc, st, _ = run_replay(write_case(t, BASE_ROWS), os.path.join(t, "out"))
    assert rc == 0 and st.get("gate_pass") and st.get("neg_balance_addrs") == 0, \
        f"F0 基准应全绿: rc={rc} stats={st}"

    # F1 中段缺块：删掉 A->B（400），B 凭空转出 150 → B 负余额
    t = case_dir()
    rows = [BASE_ROWS[0], BASE_ROWS[2], BASE_ROWS[3]]
    rc, st, _ = run_replay(write_case(t, rows), os.path.join(t, "out"))
    assert st.get("neg_balance_addrs", 0) > 0 or not st.get("gate_pass"), \
        f"F1 中段缺块必须被负余额指纹暴露: {st}"

    # F2 同键异值：同 (block,tx,log_index) 两个不同 value → 必须硬退
    t = case_dir()
    rows = BASE_ROWS + [(110, 1700000600, "0xt2", A, B, 999, "log_0")]
    rc, st, out = run_replay(write_case(t, rows), os.path.join(t, "out"))
    assert rc != 0, f"F2 同键异值必须硬退（fail-loud），实得 rc=0: {out[-200:]}"

    # F3 mint 缺失：无铸造行，A 凭空转出 → 负余额 gate 失败
    t = case_dir()
    rows = BASE_ROWS[1:]
    rc, st, _ = run_replay(write_case(t, rows), os.path.join(t, "out"))
    assert st.get("neg_balance_addrs", 0) > 0 or not st.get("gate_pass"), \
        f"F3 mint 缺失必须被暴露: {st}"

    # F4 尾部截断（QUQ 快照缺块形态）：删最后一笔 C->D——借贷两边同缺，
    # 供给闭合恒等式免疫 → 断言 gate **照过**（盲区固定化：这类洞只有采集侧
    # done.json 前置检查与 RPC 抽查能抓，重放 gate 抓不到，谁都别指望它）
    t = case_dir()
    rows = BASE_ROWS[:-1]
    rc, st, _ = run_replay(write_case(t, rows), os.path.join(t, "out"))
    assert rc == 0 and st.get("gate_pass") and st.get("neg_balance_addrs") == 0, \
        f"F4 盲区固定化断言失败——若引擎新增了尾部截断检测，更新本用例与 evm §5 文档: {st}"

    # F5 通道段重叠：声明两个重叠区间 → 启动即拒
    t = case_dir()
    csv_p = os.path.join(t, "part.csv")
    open(csv_p, "w").write(HDR + "100,1700000000,0xt1," + ZERO + "," + A + ",1000,log_0\n")
    ch_p = os.path.join(t, "ch.json")
    json.dump({"channels": [{"lo": 0, "hi": 200, "tag": "x", "path": csv_p},
                            {"lo": 150, "hi": 300, "tag": "y", "path": csv_p}]},
              open(ch_p, "w"))
    rc, _, out = run_replay(ch_p, os.path.join(t, "out"))
    assert rc != 0 and "重叠" in out, f"F5 通道重叠必须启动即拒: rc={rc}"

    print("PASS: 故障注入 F0基准+F1缺块+F2同键异值+F3无mint+F4尾部截断盲区固定+F5通道重叠，六用例全过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
