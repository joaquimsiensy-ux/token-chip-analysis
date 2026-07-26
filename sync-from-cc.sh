#!/usr/bin/env bash
# 把 Claude Code 侧（main 分支）的迭代同步到 codex 侧（codex 分支）。
# 用法：bash "${CODEX_HOME:-$HOME/.codex}/skills/token-chip-analysis/sync-from-cc.sh"
# 说明见同目录 SYNC.md
set -uo pipefail

WT="${CODEX_HOME:-$HOME/.codex}/skills/token-chip-analysis"
cd "$WT" || { echo "❌ 找不到 codex 侧 skill 目录：$WT"; exit 1; }

echo "═══ 1/4 检查当前状态 ═══"
BR=$(git rev-parse --abbrev-ref HEAD)
if [ "$BR" != "codex" ]; then
  echo "❌ 当前不在 codex 分支（在 $BR），停止。"; exit 1
fi
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "❌ 有没提交的改动，先提交再同步："
  git status --short | grep -v '^??'
  echo
  echo "   提交命令：cd $WT && git add -A && git commit -m \"改了什么\""
  exit 1
fi
echo "✅ 工作区干净，当前在 codex 分支"

echo
echo "═══ 2/4 看看 Claude Code 侧有什么新东西 ═══"
AHEAD=$(git rev-list --count codex..main)
if [ "$AHEAD" -eq 0 ]; then
  echo "✅ 已是最新，Claude Code 侧没有新提交，无需同步。"; exit 0
fi
echo "有 $AHEAD 个新提交待同步："
git log --oneline --no-decorate codex..main | head -20
[ "$AHEAD" -gt 20 ] && echo "  …（还有 $((AHEAD-20)) 个）"

echo
echo "═══ 3/4 合并 ═══"
if git merge main --no-edit; then
  echo "✅ 自动合并成功，无冲突"
else
  echo
  echo "⚠️  有冲突，需要人工解。冲突文件："
  git diff --name-only --diff-filter=U | sed 's/^/   /'
  echo
  echo "   解冲突规矩见 SYNC.md「解冲突的规矩」一节："
  echo "     · 纯加法冲突 → 两边都留，CC 的排前面"
  echo "     · 各自改写   → 看谁是超集；各有独有信息就实质合并，一条不丢"
  echo "   解完执行：git add -A && git commit"
  echo "   想反悔执行：git merge --abort"
  exit 2
fi

echo
echo "═══ 4/4 跑测试验收 ═══"
if python3 scripts/tests/run_all.py; then
  echo
  echo "✅ 同步完成，测试全过。"
  git log --oneline -1
else
  echo
  echo "❌ 测试没过——合并结果有问题，别就这么用。"
  echo "   回退命令：git reset --hard HEAD~1"
  exit 3
fi
