#!/usr/bin/env python3
"""Shared native receipt emitter called only by supported CSV collectors at successful completion."""
from __future__ import annotations
import json, os
from pathlib import Path
from channels_preflight import _csv_stats, _sha256_file
SUPPORTED={"fetch_sqd_evm.py","fetch_alchemy.py"}

def emit_native_receipt(data_path, receipt_path, collector_path, token, provider_url,
                        requested_from, requested_to, provider_next_block, *, fresh_output):
    data, collector = Path(data_path).resolve(), Path(collector_path).resolve()
    if collector.name not in SUPPORTED or not collector.is_file():
        raise ValueError("collector is not an approved formal CSV adapter")
    if not fresh_output:
        raise ValueError("formal alternate adapter cannot sign an existing unreceipted prefix")
    if any(isinstance(x,bool) or not isinstance(x,int) for x in
           (requested_from,requested_to,provider_next_block)) \
            or requested_from >= requested_to or provider_next_block < requested_to:
        raise ValueError("collector bounds/cursor do not prove completion")
    rows,lo,hi=_csv_stats(data)
    if rows and (lo < requested_from or hi >= requested_to):
        raise ValueError("CSV rows escape requested interval")
    size=data.stat().st_size; digest=_sha256_file(data)
    payload={"schema":"evm-collector-run/v2","status":"PASS",
      "producer":"csv_collector_receipt.py/v1",
      "collector":{"path":collector.name,"sha256":_sha256_file(collector)},
      "query":{"token":str(token).lower(),"query_schema":"erc20-transfer-fields/v2",
               "provider_url":str(provider_url),"requested_from":requested_from,
               "requested_to":requested_to},
      "completion":{"reason":"requested_bound_reached","next_block":provider_next_block},
      "segments":[{"requested_from":requested_from,"requested_to":requested_to,
                   "provider_next_block":provider_next_block,
                   "output_prefix":{"size":size,"sha256":digest}}],
      "output":{"path":str(data),"size":size,"sha256":digest,"rows":rows,
                "min_block":lo,"max_block":hi}}
    target=Path(receipt_path).resolve(); target.parent.mkdir(parents=True,exist_ok=True)
    tmp=target.with_name(f".{target.name}.tmp.{os.getpid()}")
    with tmp.open("x",encoding="utf-8") as f:
        json.dump(payload,f,ensure_ascii=False,indent=2); f.write("\n"); f.flush(); os.fsync(f.fileno())
    os.replace(tmp,target)
    return payload
