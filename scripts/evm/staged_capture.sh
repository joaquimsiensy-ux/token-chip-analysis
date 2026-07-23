#!/bin/bash
# 分段采集驱动（HyperSync v2 官方客户端）：规避代理长连接劣化 stall——段级几分钟短跑，
# 每段独立 run_*/done.json 幂等可续；失败段清残迹 retry-once 再 FATAL。
# 适用场景：v2 直连被掐 / clash 代理长连接偶发 stall（详见 data-pipeline-evm-channels §3.1）。
# 用法：staged_capture.sh <token_addr> <hypersync_url> <outdir> <bound1> <bound2> [bound3 ...]
#   bounds=段边界块号（升序 ≥2 个；首个=起始块，末个=终止块；相邻两个为一段 [from,to)）
#   例：staged_capture.sh 0x3d4f0513... https://bsc.hypersync.xyz data/v2 44000000 50000000 60000000 111481700
#   段大小经验值：按 ~100 万事件/段折算块距，单段控制在几分钟内完成
# 环境变量：CONCURRENCY（默认 10）
# 来源：BANANAS31(BSC) 2026-07-22 实战模板参数化收编（v3.25.0）
set -u
V2="$(dirname "$0")/fetch_hypersync_v2.py"
CONCURRENCY="${CONCURRENCY:-10}"
if [ $# -lt 5 ]; then
  echo "用法: $0 <token_addr> <hypersync_url> <outdir> <bound1> <bound2> [bound3 ...]" >&2
  exit 2
fi
TOK=$1; URL=$2; OUTDIR=$3; shift 3
BOUNDS=("$@")
n=${#BOUNDS[@]}
for ((i=0; i<n-1; i++)); do
  FROM=${BOUNDS[$i]}; TO=${BOUNDS[$((i+1))]}
  if [ -f "$OUTDIR/run_${FROM}/done.json" ]; then
    echo "[skip] segment ${FROM} done"
    continue
  fi
  # 无 done.json 的 parquet 无 footer 不可读：清残迹重跑
  rm -rf "$OUTDIR/run_${FROM}"
  echo "[start] segment ${FROM} -> ${TO} $(date +%H:%M:%S)"
  python3 "$V2" --url "$URL" --token-addr "$TOK" \
    --outdir "$OUTDIR" --concurrency "$CONCURRENCY" --to-block "$TO" "$FROM"
  rc=$?
  echo "[end] segment ${FROM} rc=${rc} $(date +%H:%M:%S)"
  if [ $rc -ne 0 ]; then
    echo "[retry-once] segment ${FROM}"
    rm -rf "$OUTDIR/run_${FROM}"
    python3 "$V2" --url "$URL" --token-addr "$TOK" \
      --outdir "$OUTDIR" --concurrency "$CONCURRENCY" --to-block "$TO" "$FROM" || {
        echo "[FATAL] segment ${FROM} failed twice"; exit 1; }
  fi
done
echo "[ALL-DONE] $(date +%H:%M:%S)"
