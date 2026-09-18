#!/usr/bin/env python3
"""P1-01 regressions: entity members always enter G8 and gate files are non-forgeable."""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "report"))
sys.path.insert(0, str(HERE))

import entity_identity_gate as gate
from identity_gate_fixture import write_binding


ADDR = "0x1234567890abcdef1234567890abcdef12345678"


def dump(path, obj):
    Path(path).write_text(json.dumps(obj), encoding="utf-8")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        state_path = Path(tmp) / "analysis-state.json"
        state = {"chain": "bsc", "whale_groups": [
            {"entity_id": "e1", "addresses": [ADDR]}]}
        dump(state_path, state)
        total, _ = write_binding(tmp, {ADDR: 100})
        snapshot = Path(tmp) / "balances_final.json"
        receipt = Path(tmp) / "identity_holders_receipt.json"
        gate_path = Path(tmp) / "identity_gate.json"
        built = gate.build(str(state_path), "bsc", str(snapshot), out_path=str(gate_path),
                           total_supply_raw=total, snapshot_receipt_path=str(receipt))
        row = built["rows"][0]
        assert row["flag"] == "BIG_UNLABELED" and built["n_flags"] == 1, \
            "无标签实体成员必须入 BIG_UNLABELED，不得由 share 决定"

        # 填写 resolution 后严格 gate 才可 PASS。
        built["rows"][0]["resolution"] = "查标签双源与 gas 溯源，确认非设施"
        dump(gate_path, built)
        assert gate.check(str(gate_path)) == 0

        forged = dict(built)
        forged["schema"] = "garbage"
        forged["n_addresses"] = 999
        forged["n_flags"] = 999
        forged["rows"] = [{**built["rows"][0], "flag": ""}]
        forged_path = Path(tmp) / "forged.json"
        dump(forged_path, forged)
        assert gate.check(str(forged_path)) != 0, "伪造 schema/计数/空 flag 必须拒绝"

        duplicate = json.loads(json.dumps(built))
        duplicate["rows"].append(dict(duplicate["rows"][0]))
        duplicate["n_addresses"] = 2
        duplicate["n_flags"] = 2
        duplicate_path = Path(tmp) / "duplicate.json"
        dump(duplicate_path, duplicate)
        assert gate.check(str(duplicate_path)) != 0, "重复地址必须拒绝"

        mismatch = json.loads(json.dumps(built))
        mismatch["rows"][0]["entity"] = "other"
        mismatch_path = Path(tmp) / "mismatch.json"
        dump(mismatch_path, mismatch)
        assert gate.check(str(mismatch_path)) != 0, "逐行实体必须与 state 一致"

        f06_a = json.loads(json.dumps(built))
        f06_a["rows"][0]["label"] = {"name": "public-infra", "category": "dex", "tier": "exclude", "source": "test"}
        f06_a["rows"][0]["flag"] = ""
        f06_a["rows"][0]["resolution"] = ""
        f06_a["n_flags"] = 0
        f06_a_path = Path(tmp) / "f06_a.json"
        dump(f06_a_path, f06_a)
        assert gate.check(str(f06_a_path)) != 0, "F06 清空 flag 不得解除 INFRA 义务"

        f06_b = json.loads(json.dumps(built))
        f06_b["rows"][0]["label"] = {"name": "public-infra", "category": "dex", "tier": "exclude", "source": "test"}
        f06_b["rows"][0]["flag"] = "INFRA_IN_ENTITY"
        f06_b["rows"][0]["resolution"] = ""
        f06_b["n_flags"] = 1
        f06_b_path = Path(tmp) / "f06_b.json"
        dump(f06_b_path, f06_b)
        assert gate.check(str(f06_b_path)) != 0, "F06 INFRA 无 resolution 仍拒（既有行为回归）"

        f06_c = json.loads(json.dumps(built))
        f06_c["rows"][0]["label"] = {"name": "public-infra", "category": "dex", "tier": "exclude", "source": "test"}
        f06_c["rows"][0]["flag"] = "INFRA_IN_ENTITY"
        f06_c["rows"][0]["resolution"] = "已核：DEX 池地址，已从实体成员剔除"
        f06_c["n_flags"] = 1
        f06_c_path = Path(tmp) / "f06_c.json"
        dump(f06_c_path, f06_c)
        assert gate.check(str(f06_c_path)) == 0, "F06 INFRA 带 resolution 放行"

    print("PASS: P1-01 无标签实体成员 + 严格 identity gate schema/计数/唯一性/实体绑定/F06 exclude 标签重推 INFRA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
