#!/usr/bin/env python3
"""文件操作守卫 hook（B7 补遗，2026-07-22）——两类拦截：

1. Read 整读巨型数据文件 → deny：大 CSV/parquet 整读进上下文既烧 token 又截断无用，
   正确姿势是 duckdb/python 定向抽取（data-pipeline-evm §12 / 坑表 #4 的制度化）。
   阈值：二进制数据格式(parquet/gz/feather/arrow/duckdb) >1MB；
        文本数据(csv/jsonl/txt/log/json) >5MB。
2. Write/Edit 覆盖原始采集产物 → deny：run_*/logs.parquet、soltx-*.jsonl.gz 等
   只能由采集器写入——分析层误覆盖原始数据=不可逆事故（fail-closed）。

接 settings.json PreToolUse（matcher Read 与 Write|Edit 各挂一次）。
放行=静默 exit 0；拦截=输出 permissionDecision deny + 原因。
"""
import json
import os
import re
import sys

BIN_EXT = {".parquet", ".gz", ".feather", ".arrow", ".db", ".duckdb"}
TXT_EXT = {".csv", ".jsonl", ".txt", ".log", ".json"}
BIN_LIMIT = 1 * 1024 * 1024
TXT_LIMIT = 5 * 1024 * 1024

# 原始采集产物（只允许采集器写）
RAW_PATTERNS = [
    re.compile(r"/data/v2/(partial_)?run_[^/]+/(logs|blocks)\.parquet$"),
    re.compile(r"/data/soltx-[^/]+\.jsonl\.gz$"),
    re.compile(r"/data/soltx-[^/]+\.meta\.json$"),
]


def deny(reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }}, ensure_ascii=False))
    sys.exit(0)


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)  # 载荷异常时放行，守卫自身绝不阻塞正常工作
    tool = payload.get("tool_name") or ""
    fp = (payload.get("tool_input") or {}).get("file_path") or ""
    if not fp:
        sys.exit(0)

    if tool == "Read":
        ext = os.path.splitext(fp)[1].lower()
        try:
            size = os.path.getsize(fp)
        except OSError:
            sys.exit(0)
        if ext in BIN_EXT and size > BIN_LIMIT:
            deny(f"拦截整读二进制数据文件（{size/1048576:.1f}MB）：Read parquet/gz 无意义且烧上下文。"
                 f"用 duckdb 定向查询（SELECT ... FROM read_parquet(...) LIMIT）或 python 抽样代替。")
        if ext in TXT_EXT and size > TXT_LIMIT:
            deny(f"拦截整读巨型数据文件（{size/1048576:.1f}MB）：整读进上下文会截断且烧 token。"
                 f"用 head/grep/duckdb/python 定向抽取所需字段，或 Read 加 offset/limit 只取头部确认结构。")
        sys.exit(0)

    if tool in ("Write", "Edit"):
        for pat in RAW_PATTERNS:
            if pat.search(fp):
                deny("拦截覆盖原始采集产物：run_*/logs.parquet、soltx-*.jsonl.gz 只能由采集器"
                     "（fetch_hypersync_v2 / fetch_sqd_transfers_v2）写入。"
                     "分析层需要衍生数据时另存新文件，绝不改原始层。")
        sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
