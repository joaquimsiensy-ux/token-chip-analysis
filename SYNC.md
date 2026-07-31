# 双线 skill 同步说明（codex 侧）

这份 skill 有两个副本，各自迭代，通过 git 单向同步：

| | 路径 | 分支 | 规则 |
|---|---|---|---|
| **Claude Code 版** | `~/.claude/skills/token-chip-analysis` | `main` | 只管自己迭代，**永不合并 codex 的东西** |
| **codex 版（本目录）** | `~/.codex/skills/token-chip-analysis` | `codex` | 自己迭代 **＋** 定期吸收 main 的迭代 |

两个目录共用同一个 git 仓库（本目录是 main 目录的 git worktree），所以同步不需要拷贝文件。

## 独立分享包

对外分享的 ZIP 是不含 `.git` 的固定快照。收件人解压到 Codex skills 目录后，
`sync-from-cc.sh` 检测不到本 skill 自己的 Git worktree 或本地 `main` 分支时会提示
“使用包内已通过测试的固定快照”并返回 0，不会阻断分析。分享包不会自动获得维护者
后续的 CC 更新；需要由维护者重新同步、验证并分发新 ZIP。

---

## 日常怎么用

### 0）跑任何筹码分析之前 —— 硬性前置，先同步

```bash
bash ~/.codex/skills/token-chip-analysis/sync-from-cc.sh
```

这条已写进 codex 版 `SKILL.md` 的「Codex 运行适配 → 第 0 步」，codex 每次加载 skill 都会读到，
所以正常情况下它会自己执行，你不用记。

脚本依次做四件事：检查工作区 → 列出 CC 侧的新提交 → 合并 → 跑全部测试。
退出码 0 正常开工；1 是有未提交改动挡路；2 是有冲突（**先解冲突再开工**）；3 是测试没过（必须停）。

**为什么是硬性**：CC 侧的迭代里有引擎级缺陷修复（比如 3.34.0 修 Solana 采集器、3.35.0 揭露锚点法
"三查全过但中段数值全错"）。用旧版本跑出来的结论可能整篇是错的，而同步通常只要几十秒。

### 1）在 codex 侧改了东西 → 立刻提交

别攒着，未提交的改动会挡住下次同步：

```bash
cd ~/.codex/skills/token-chip-analysis
python3 scripts/tests/run_all.py                  # 全过才提交
git add -A && git commit -m "c1.1.0 改了什么"
```

版本号用 `c` 前缀（见下方约定 1），CHANGELOG 写 `CHANGELOG-codex.md`（见约定 2）。
提交时 pre-commit 钩子会自动跑三检，不过关会拦下来。

---

## 三条约定（2026-07-26 用户拍板，改了会重新引入冲突）

1. **版本号**：CC 侧走主线数字版本号（约定时为 `3.x.x`，现已迭代至 `6.x.x`）；codex 侧新条目一律用 `c` 前缀（`c1.0.0`、`c1.1.0`…），
   两条轴彻底分开。历史上 3.26.0~3.30.0 有 6 个号在两边含义不同，是分叉时没约定造成的，
   原貌保留在 `CHANGELOG-codex.md` 顶部说明里。

2. **CHANGELOG 分家**：
   - `CHANGELOG.md` = CC 侧的迭代史，**codex 侧一个字都不要改**（改了下次同步必冲突）
   - `CHANGELOG-codex.md` = codex 侧自己的迭代史，CC 侧没有这个文件，永不冲突

3. **标签库 CC 单向下发**：`references/labels/**` 和 `scripts/labels/sources/**`
   以 Claude Code 侧为唯一真源，codex 侧**不要直接改**。
   codex 侧跑分析新发现了惯犯地址或未命中地址，回灌到 CC 侧那份，下次同步自然下来。

> 为什么要这三条：不这么约定的话，每次同步这几个文件都会打架，
> 而它们恰恰是最难人工判断对错的（几千行 CSV、几百 KB 的 CHANGELOG）。
> 立了约定之后，实测首次同步 54 个文件里只有 7 个需要人工看。

---

## 解冲突的规矩

- **纯加法冲突**（两边各加了不同的新条目）→ 两边都保留，**CC 的排前面、codex 的排后面**
  （这样 CC 下次在原位置追加时上文不变，能少一次冲突）
- **同一处两边各自改写** → 不许简单二选一。先看谁是谁的超集：
  是超集就取超集；各有独有信息就实质合并，两边的信息一条都不能丢
- **解完必须跑** `python3 scripts/tests/run_all.py`，全过才算数

---

## 出问题了怎么办

**同步到一半想反悔**：
```bash
cd ~/.codex/skills/token-chip-analysis && git merge --abort
```
回到同步前的状态，什么都没变。

**想看 codex 侧到底改过哪些东西**（相对分叉点 v3.25.0）：
```bash
cd ~/.codex/skills/token-chip-analysis && git diff --stat 29a211a codex
```

**彻底回到某次同步之前**：
```bash
cd ~/.codex/skills/token-chip-analysis && git log --oneline -10
```
找到想回去的那次 commit，然后 `git reset --hard <前7位>`（⚠️ 会丢弃之后的改动）。

**完整备份**：`~/.codex/skills/token-chip-analysis.BACKUP_20260726_125936.tar.gz`
（2026-07-26 建立双线机制前的原始状态，24MB）

---

## 分叉与首次同步的事实记录

- 分叉点：CC 仓库 `29a211a` = **v3.25.0（2026-07-23 10:02）**
- codex 侧分叉后独有迭代：8 个版本 + `agents/openai.yaml` + 三份 references 分册
  （economic-control-accounting / independent-audit-protocol / lp-fee-accounting）
  + `scripts/report/audit_release_gate.py` 及其测试
- 首次同步（2026-07-26）：合入 CC 侧 3.26.0→3.35.0，54 文件约 +10300 行，
  人工解 7 个文件 8 处冲突，`run_all.py` 14 项全过
- 首次同步顺带修复：codex 侧 `serial_actors.csv` 曾被打成 2 行（原 1856 行惯犯库
  几乎清空），已从 CC 侧恢复为 2160 行
