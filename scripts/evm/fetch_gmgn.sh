#!/bin/bash
# GMGN 数据采集（免费 API，leaky-bucket 限速：info/security/pool 权重1，holders/traders 权重5）
# 来源：OPN(BSC) 分析会话实战产物, 2026-07。
# 用法：bash fetch_gmgn.sh <token_address> <chain1> [chain2...]   例：bash fetch_gmgn.sh 0x79... bsc eth
# 产物：gmgn/<chain>_*.json（--raw 单行 JSON）
set -u
T=$1; shift
mkdir -p gmgn

run() { local out=$1; shift
  echo "== $out ==" >&2
  gmgn-cli "$@" --raw > "gmgn/$out.json" 2>"gmgn/$out.err" || echo "FAIL $out" >&2
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
echo "GMGN DONE" >&2
# 提醒：holders 里的 native_transfer.from_address 是 gas 来源聚类的关键字段；
# traders_sellvol 是"操作者EOA"口径，地址可能不在 Transfer 事件里，刷量定性要克制。
