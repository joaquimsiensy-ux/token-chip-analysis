#!/bin/bash
# GMGN 数据采集（免费 API，leaky-bucket 限速：info/security/pool 权重1，holders/traders 权重5）
# 来源：OPN(BSC) 分析会话实战产物, 2026-07。
# 用法：bash fetch_gmgn.sh <token_address> <chain1> [chain2...]   例：bash fetch_gmgn.sh 0x79... bsc eth
# 产物：gmgn/<chain>_*.json（--raw 单行 JSON）
set -u
T=$1; shift
mkdir -p gmgn
SUCCESS_COUNT=0
FAIL_COUNT=0
SUCCESS_LIST=""
FAIL_LIST=""

run() { local out=$1; shift
  echo "== $out ==" >&2
  local tmp="gmgn/$out.json.tmp"
  local final="gmgn/$out.json"
  local stale="gmgn/$out.json.stale"
  rm -f "$tmp"
  if gmgn-cli "$@" --raw > "$tmp" 2>"gmgn/$out.err"; then
    if python3 -c 'import json,sys;json.load(open(sys.argv[1]))' "$tmp" \
        >/dev/null 2>>"gmgn/$out.err"; then
      mv "$tmp" "$final"
      SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
      SUCCESS_LIST="${SUCCESS_LIST}${out}\n"
      return 0
    fi
    echo "FAIL ${out}（输出不是合法 JSON）" >&2
  else
    echo "FAIL ${out}（gmgn-cli 非零退出）" >&2
  fi
  rm -f "$tmp"
  if [ -f "$final" ]; then
    if ! mv -f "$final" "$stale"; then
      echo "FAIL ${out}（旧正式文件无法标记为 .stale）" >&2
    fi
  fi
  FAIL_COUNT=$((FAIL_COUNT + 1))
  FAIL_LIST="${FAIL_LIST}${out}\n"
  return 0
}

for CH in "$@"; do
  run "${CH}_info"    token info     --chain "$CH" --address "$T"; sleep 1
  run "${CH}_sec"     token security --chain "$CH" --address "$T"; sleep 1
  run "${CH}_pool"    token pool     --chain "$CH" --address "$T"; sleep 1
  run "${CH}_holders_top100" token holders --chain "$CH" --address "$T" --limit 100 --order-by amount_percentage; sleep 3
  run "${CH}_traders_amount" token traders --chain "$CH" --address "$T" --limit 100 --order-by amount_percentage; sleep 3
  run "${CH}_traders_sellvol" token traders --chain "$CH" --address "$T" --limit 100 --order-by sell_volume_cur; sleep 3
  run "${CH}_traders_profit" token traders --chain "$CH" --address "$T" --limit 100 --order-by profit; sleep 3
  for tag in smart_degen renowned fresh_wallet sniper bundler transfer_in dev; do
    run "${CH}_holders_$tag" token holders --chain "$CH" --address "$T" --limit 100 --tag $tag --order-by amount_percentage
    sleep 3
  done
done
printf 'GMGN 成功（%s）:\n%b' "$SUCCESS_COUNT" "$SUCCESS_LIST" >&2
printf 'GMGN 失败（%s）:\n%b' "$FAIL_COUNT" "$FAIL_LIST" >&2
if [ "$FAIL_COUNT" -gt 0 ]; then
  exit 1
fi
echo "GMGN DONE" >&2
# 提醒：holders 里的 native_transfer.from_address 是 gas 来源聚类的关键字段；
# traders_sellvol 是"操作者EOA"口径，地址可能不在 Transfer 事件里，刷量定性要克制。
