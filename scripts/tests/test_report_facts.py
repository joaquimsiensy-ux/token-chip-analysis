#!/usr/bin/env python3
"""报告编译化（facts_gate）离线测试（3.18.0）：宏渲染 / 语义 gate 四条契约。"""
import importlib.util
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FG = os.path.join(HERE, "..", "report", "facts_gate.py")
spec = importlib.util.spec_from_file_location("facts_gate", FG)
fg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fg)

FACTS = {
    "token": {"symbol": "TT", "decimals": 18, "total_supply_raw": str(10**9 * 10**18)},
    "entities": {
        "e1": {"label": "大庄#1", "tier": "P0",
               "addresses": ["0xAA00000000000000000000000000000000000001",
                             "0xAA00000000000000000000000000000000000002"],
               "current_raw": str(278_400_000 * 10**18),
               "peak_raw": str(687_000_000 * 10**18), "peak_date": "2026-05-01"},
    },
    "metrics": {"m_alpha": {"num_raw": str(376_000_000 * 10**18),
                            "den": "total_supply", "desc": "Alpha托管"}},
}
STATE_OK = {"whale_groups": [
    {"label": "大庄#1", "addresses": ["0xaa00000000000000000000000000000000000001",
                                      "0xaa00000000000000000000000000000000000002"]}]}


def facts_obj():
    return fg.Facts(json.loads(json.dumps(FACTS)))


def main():
    # 1) 宏渲染：组合宏格式与百分比精度
    f = facts_obj()
    md = "问1：{{e1.label}} 当前 {{e1.amount_share}}（峰值 {{e1.peak_share}}，{{e1.naddr}} 址）；Alpha {{m:m_alpha}}。\n\n{{appendix_b}}"
    out = f.render(md)
    assert "大庄#1 当前 2.78亿枚【总量27.84%】" in out, out[:120]
    assert "峰值 68.70%" in out and "2 址" in out and "Alpha 37.60%" in out
    assert "`0xAA00000000000000000000000000000000000001`" in out, "附录B应含完整地址"
    errs, notes = fg.gate_check(f, STATE_OK, out)
    assert not errs, f"合法输入不应报错: {errs}"

    # 2) G1 成员集合不一致必炸（state 少一个地址）
    f2 = facts_obj()
    out2 = f2.render(md)
    bad_state = {"whale_groups": [{"label": "大庄#1",
                 "addresses": ["0xaa00000000000000000000000000000000000001"]}]}
    errs, _ = fg.gate_check(f2, bad_state, out2)
    assert any("G1" in e and "成员集合不一致" in e for e in errs), f"应报 G1: {errs}"

    # 3) G4 宏名打错必炸（渲染期抛 KeyError）
    f3 = facts_obj()
    try:
        f3.render("{{e1.shrae}}")
        raise AssertionError("拼错宏字段应抛 KeyError")
    except KeyError:
        pass
    try:
        f3.render("{{e_ghost.share}}")
        raise AssertionError("不存在的实体应抛 KeyError")
    except KeyError:
        pass

    # 4) G5 手写百分比检出（27.84% 来自宏=白名单；99.99% 手写=检出）
    f4 = facts_obj()
    out4 = f4.render("{{e1.share}} 而某处手写了 99.99% 的数字")
    _, notes = fg.gate_check(f4, None, out4)
    assert notes and "99.99%" in notes[0] and "27.84%" not in notes[0], f"G5 差集错误: {notes}"

    # 5) G2 供给上界：实体持仓超总供应必炸
    over = json.loads(json.dumps(FACTS))
    over["entities"]["e1"]["current_raw"] = str(2 * 10**9 * 10**18)
    over["entities"]["e1"]["peak_raw"] = str(2 * 10**9 * 10**18)
    errs, _ = fg.gate_check(fg.Facts(over))
    assert any("G2" in e for e in errs), f"应报 G2: {errs}"

    print("PASS: facts 宏渲染/附录B同源/G1集合gate/G4宏名gate/G5手写检出/G2上界，五契约全过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
