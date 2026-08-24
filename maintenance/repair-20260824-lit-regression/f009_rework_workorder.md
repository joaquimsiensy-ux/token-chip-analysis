# 工单 批3返工（round 2）：修正 done 报告禁改核验证据路径（fresh 会话可独立执行）

一句话目标：消化盲审 round1 唯一 BLOCK 项——f009_closeout_done.md §5 禁改文件核验命令用了不存在的路径导致该行证据无效，用真实路径重跑并修正报告。

## 盲审认定的事实（f009_review_verdict_round1.md）
- done 报告 :189 的命令写的是 `scripts/wave_scan.py`、`scripts/entity_source_trace.py`——两路径不存在，真实路径为 `scripts/report/wave_scan.py`、`scripts/report/entity_source_trace.py`。
- `git diff --exit-code HEAD -- <不存在的路径>` 恒返回 0，因此该 EXIT_CODE=0 不能证明禁改文件未被改。
- 盲审已用真实路径独立复核：全部禁改文件确实与 HEAD 一致——**纯证据缺陷，九个登记面文件与生产代码零问题**。

## 施工清单（只动 done 报告一个文件）
1. 修正 `f009_closeout_done.md` §5 该命令行为真实路径，并真实重跑：
   `git diff --exit-code HEAD -- scripts/report/wave_scan.py scripts/report/entity_source_trace.py scripts/solana/sqd_cache_identity.py scripts/evm/replay_pass2.py scripts/evm/replay_duck.py scripts/solana/replay_edges.py`
   把真实原始输出与 EXIT_CODE 写回报告。
2. §8 末尾 `BOUNDARY_DIFF_EXIT` 一行若同源于该错误路径命令，同步用真实路径重跑并更新。
3. 报告内新增一小节「round2 返工」：写明勘误内容（错误路径原文→真实路径）、归因（施工方自拟核验命令时路径笔误，未被 EXIT_CODE 语义暴露）；不改写报告其余任何段落。
4. 重跑后确认 done 报告自身仍零行尾空格、零 EOF 空行（`git diff --check` 语义）。

## 边界
- 白名单：仅 `maintenance/repair-20260824-lit-regression/f009_closeout_done.md`。
- **九个登记面文件与全部代码一律不动**；不 commit、不联网；发现新问题只记录不修。
