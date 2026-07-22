#!/bin/sh
# 夜间自动采集 wrapper（3.18.0，launchd 从 com.chip-analysis.nightly-collect 调起）。
# 约定：<工作根>/collect_plans/pending_plan.json 存在即开采，采完按结果改名归档：
#   退出 0 → done_plan_<ts>.json   2 → gaps_plan_<ts>.json   其他 → failed_plan_<ts>.json
#   退出 3 → 队列单实例锁被占（白天会话还在采）：**保留 pending 不改名**，明晚重试
# 无 pending 文件时静默退出——定时器每天都醒，有没有活干由文件说了算。
# run_id（C2）：本脚本生成 <ts>p<pid> 传给 run_guarded --run-id，run_guarded 再经
#   CHIP_RUN_ID 环境变量传给 collect_queue——一次夜采全链路同一 id，产物不互覆盖。
# 用法（用户侧）：睡前让 Claude 生成 plan 存为 pending_plan.json 即可；日志 nightly.log。
# 卸载定时器：launchctl bootout gui/$(id -u)/com.chip-analysis.nightly-collect
BASE="/Users/uravvv/Desktop/老公用/fable筹码分析"
PLANS="$BASE/collect_plans"
PENDING="$PLANS/pending_plan.json"
PY=/usr/local/bin/python3
SKILL="$HOME/.claude/skills/token-chip-analysis"
LOG="$PLANS/nightly.log"

[ -f "$PENDING" ] || exit 0
mkdir -p "$PLANS"
TS=$(date +%Y%m%d_%H%M)
RUN_ID="${TS}p$$"
echo "===== nightly_collect $TS 发现 pending_plan，开跑 run_id=$RUN_ID =====" >> "$LOG"
# 直接前台跑（launchd 本身即后台），run_guarded 提供内存/磁盘水位守护
"$PY" "$SKILL/scripts/run_guarded.py" --name "nightly" --run-id "$RUN_ID" \
    --mem-ceiling-gb 6 --min-free-disk-gb 8 --out-dir "$PLANS" \
    -- "$PY" "$SKILL/scripts/collect/collect_queue.py" "$PENDING" >> "$LOG" 2>&1
RC=$?
if [ "$RC" = 3 ]; then
  # 另一个采集实例在跑（多半是白天手动会话没收工）——不动 pending，明晚自动重试
  echo "===== nightly_collect $TS rc=3 队列锁被占，保留 pending 明晚重试 =====" >> "$LOG"
  exit 0
fi
case "$RC" in
  0) DST="done_plan_$TS.json" ;;
  2) DST="gaps_plan_$TS.json" ;;
  *) DST="failed_plan_$TS.json" ;;
esac
mv "$PENDING" "$PLANS/$DST"
echo "===== nightly_collect $TS 结束 rc=$RC -> $DST =====" >> "$LOG"
exit 0
