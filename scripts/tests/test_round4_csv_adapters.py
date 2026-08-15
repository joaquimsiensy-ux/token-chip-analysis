#!/usr/bin/env python3
"""Round4 P1-03: formal alternate CSV adapters emit native v2 receipts or declare nonformal."""
import json, sys, tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
EVM=HERE.parent / "evm"
sys.path.insert(0,str(EVM))

def main():
    from csv_collector_receipt import emit_native_receipt
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); data=root/"data.csv"
        data.write_text("block,ts,tx,log_index,from,to,value_raw,block_hash\n5,1,0xt,0,0xa,0xb,1,0xh\n")
        for name in ("fetch_sqd_evm.py",):
            out=root/(name+".json")
            emit_native_receipt(data,out,EVM/name,"0x"+"a"*40,"https://provider",0,10,10, fresh_output=True)
            d=json.loads(out.read_text())
            assert d["schema"]=="evm-collector-run/v2" and d["collector"]["path"]==name
        try:
            emit_native_receipt(data,root/"bad.json",EVM/"fetch_sqd_evm.py","0x"+"a"*40,
                                "https://provider",0,10,10,fresh_output=False)
        except ValueError:
            pass
        else:
            raise AssertionError("alternate formal adapter must reject unreceipted prefixes")
    for name in ("fetch_bigquery.py","scan_transfers.py","fetch_etherscan.py","fetch_alchemy.py"):
        text=(EVM/name).read_text()
        assert "FORMAL_CHANNEL_ELIGIBLE = False" in text, name
    print("PASS: alternate adapters are native-receipted or explicit nonformal")
    return 0
if __name__=="__main__": raise SystemExit(main())
