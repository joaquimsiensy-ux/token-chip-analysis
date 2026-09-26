# 收官审查（只读 codex）——修复工程 replay_duck --only-addrs 分桶流式补算 9.2.2

## 纪律
禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读本工程目录 `maintenance/repair-20260925-replay-only-addrs-scale/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`、`/Volumes`；不得进入 `/Users/uravvv/.claude/skills/token-chip-analysis`。只读、离线、不 commit、不新建/修改文件。工作目录＝`/Users/uravvv/.claude/worktrees/tca-only-addrs`（分支 `fix/replay-only-addrs-scale`）。**报告全文放在最终答复消息里**，首行固定 `# 收官审查：PASS` 或 `# 收官审查：FAIL`。沙箱若无可写临时目录，测试类项目标注"环境阻断"列入未完成项，改用纯内存 DuckDB 完成能做的部分。

## 背景（调度方提供的事实，你可以核对工程目录内文件）
- 起因：QUQ 案 −2 收官需 `data/peaks/block_precision_followup.json`（发布闸 `scripts/report/audit_release_gate.py` 硬绑 `replay_duck.py --only-addrs` 本体与脚本 sha）。原实现把 1.097 亿行 `raw_rows` 整表物化再全局去重，在本机六次实跑全部失败（临时盘 38–57 GiB 撞上限 4 次、DuckDB 8/12 GB 内存 OOM 2 次）。
- 修法：工单 `workorder_W1.md`（v3.1，经 codex 复核三轮 `review_W1_reply_r1..r3.md`），施工 `W1_done.md`，盲审 r1 PASS `blind_W1_reply_r1.md`（沙箱无临时目录，磁盘测试环境阻断；调度方本机 run_all 147/151，四红均环境项且补验转绿）。
- 调度方在真实 QUQ 数据上用 HEAD 脚本实跑的结果（数字来自案卷日志，你无权访问案卷，作为"声称"对待）：
  - 命令：`replay_duck.py --channels channels.json --out-dir <外接盘临时目录> --mem-limit 8GB --threads 4 --only-addrs needs_block_precision.json --only-addrs trigger_days.json`（HEAD b867f78 脚本，sha256 前 12 位 e58e9f127bfd）。
  - rc=0；墙钟 2099.81 s（user 7376.91 s，sys 294.77 s）；`/usr/bin/time -l` maximum resident set size 6,549,962,752 B，peak memory footprint 10,055,033,208 B；外接盘 `.duck_tmp` 峰值 13 GB。对照原实现六次失败：临时盘 38–57 GiB 撞上限、内存 OOM 7.4/7.4 GiB 与 11.1/11.1 GiB。
  - 日志：`value 最大位数=28 -> HUGEINT 路径`；`合计保留源行 109681418（only-addrs：不物化，冲突查重在分桶阶段执行）`；前三桶 `桶 0/22 行 4987771 冲突 0 过滤后 8903669 耗时 37.3s`、`桶 1/22 行 4984022 冲突 0 过滤后 8897082 耗时 58.4s`、`桶 2/22 行 4987362 冲突 0 过滤后 8904914 耗时 73.4s`（"过滤后"=该桶写入 ab_raw 的 (a,b,dd) 行数）；`[only-addrs] 汇总 K=22 总行数=109681418 最大桶行数=4990129 ab 行数=107361124 墙钟=1347.805s 源查询=44（分桶阶段）`；`[only-addrs] 块级精确峰值 51429 址（有事件 51177）`。
  - 收据 `block_precision_followup.json` 6,082,245 B：count=51429、engine=replay_duck.py、value_type=HUGEINT、producer.sha256 前 12 位 e58e9f127bfd、inputs 两项 sha 前 12 位 175707c4de17 / 1f81d2723e28、addresses 51429 条其中 peak>0 51177 条、顶层键 addresses/channels/count/engine/inputs/producer/schema/value_type。
  - 注意：ab 行数 107,361,124 ≈ 源行数，说明地址并集几乎命中全部事件（含流动性池/路由地址）；峰值段（分桶后）耗时 ≈ 2099−1348 ≈ 752 s。

## 任务
目标只有一个：判断"QUQ 那个问题"是否**真正解决**，而不是仅仅通过了测试。逐项：
1. **问题—修法对应**：读 HEAD `scripts/evm/replay_duck.py` 与 `git diff 8457f70 HEAD -- scripts/evm/replay_duck.py`。原六次失败的根因（全量物化 + 全局 GROUP BY 去重 + 临时盘溢写）在 only-addrs 路径上是否已被消除？还有没有任何一步会在 1.1 亿行上把全表或与之同量级的中间结果物化（包括 `ab_raw` 的累计规模：估算 1.1 亿源行、几乎所有行命中地址并集时 `ab_raw` 行数与最终 `GROUP BY a,b` 的内存/溢写量级，判断 8 GB 限额下是否可控）？给出你的估算依据。
2. **实跑数字自洽性**：用背景段的真实实跑数字核对：桶数 K 是否 = ceil(kept_rows/5,000,000)；桶行数之和是否 = 保留源行；每桶耗时与 RSS 是否与代码路径一致（不是全量物化能得到的数字）；收据 count/producer sha 与 HEAD 脚本 sha 是否一致（`shasum -a 256 scripts/evm/replay_duck.py` 自己算）。
3. **正确性残余风险**：分桶后是否有任何输入形态会让 only-addrs 结果与基线（8457f70）全量路径的 `peaks.json` 同地址不一致？至少用纯内存 DuckDB 独立构造 3 个刁钻夹具（跨桶同地址、桶内全部重复行、地址并集含 Z/DEAD 与非命中地址）对照基线副本（`git show 8457f70:scripts/evm/replay_duck.py`）。冲突拒绝是否仍 fail-closed。
4. **契约与守卫**：收据 schema（`scripts/tests/invariant_manifest.json` 中 `followup_peaks` 条目）、`os.replace` 原子写、发布闸绑定读取点（`audit_release_gate.py` 中读取 `block_precision_followup.json` 的段）是否与新脚本兼容；`invariant_scan.py`、`changelog_lint.py` 结果。
5. **版本与登记**：9.2.2 四处一致；CHANGELOG 详细段是否如实（不夸大：如实登记资源证据状态）。
6. **合并风险**：`git log --oneline 8457f70..HEAD` 与 `git diff --stat 8457f70 HEAD`；列出合并到 main 时可能冲突的文件（main 已由另一工程推进到 9.2.1 之后的提交，你只需按本分支改动面判断哪些文件高概率冲突）。
判定：只要第 1 或第 3 项发现真实缺陷即 FAIL（给最小复现）；否则 PASS，并列出未完成项与你实际执行的命令清单。
