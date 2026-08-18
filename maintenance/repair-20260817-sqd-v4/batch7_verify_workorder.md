# 批 7 收敛确认工单（三审·防御回归验证）

> 分支 `fix/sqd-solana-v4`（只读验证，**禁改任何生产/测试/文档源，禁 commit/merge/push**；
> 本工单与你的验证脚本、交付 md 可写）。生产解释器 `/usr/local/bin/python3`（duckdb 等依赖在此，
> 系统 python3 缺依赖会假失败，一律用绝对路径解释器）。ARC 案目录
> `/Users/uravvv/Documents/5.6筹码分析/ARC分析/` 绝对只读。验证脚本落
> `maintenance/repair-20260817-sqd-v4/verify3/`（新目录），构造/篡改一律在系统临时目录复制副本上做，
> 绝不动仓库原件。

## 背景
opus 二审对 v6.49.0 判 BLOCK，批 7 消化了三项 finding（F2-01 curve_cost 归属缺口 BREACH、
F2-04 reconcile TOCTOU、F2-03 provenance 威胁模型边界=接受项）。本工单是**独立重放二审已知攻击、
断言批 7 修复后这些攻击被拒**的确定性防御回归验证——不是开放式渗透，是"跑回归断言防线生效"。
**你要独立重做，不引用任何既有 done 报告的自报数字作为证据**（done 只当线索）。

## 任务

### T1 改动面与零 diff 独立核对
`git diff --stat 2fb1924..HEAD`：列出全部改动文件；断言 `scripts/solana/fetch_sqd_transfers_v2.py`、
`VERSION`、`CHANGELOG.md` **零 diff**；生产/测试改动应仅 `curve_cost.py`、`replay_edges.py`、
`test_sqd_consumer_v4.py`。任何多出的生产文件改动＝异常，记录。

### T2 F2-01 回归：curve_cost 归属闭合（四拒一不误伤）
现役 `scripts/solana/curve_cost.py`，构造一条合法 7 元组边 + 五份 meta，真跑其正式入口
（`main()` 或 load 路径，按实际 CLI），断言：
1. `collector_sha256` 填未登记值（如 64 个 f）→ **拒**，不产 `data/curve_costs.json`；
2. `collector_sha256` 抄公开常量但 `edge_logical_sha256` 填错 → **拒**；
3. `edge_rows` 填错（与实际边数不符）→ **拒**；
4. 边文件被篡改 1 字节但 meta 不变（摘要不符）→ **拒**；
5. 合法 v4 meta（collector 抄真实 ACTIVE 常量 + 正确 edge_logical + 正确 edge_rows）+ 匹配边 →
   **正常通过产出成本结论**（证明修复不误伤）。
用 `inspect.getsource` 证明 curve_cost 真的调用共享 `sqd_cache_identity.validate_cache_meta`
（不是又自写一份弱校验）。可选：`git show <F2-01红态commit>:scripts/solana/curve_cost.py` 载入旧版，
证明例 1 在旧版曾 rc=0 产结论（攻击曾有效）。

### T3 F2-04 回归：reconcile 单次冻结读取
现役 `replay_edges.py` reconcile 路径：模拟"replay 读入后替换磁盘 gzip"的 TOCTOU 时序，断言
批 7 单次 `read_bytes()` 冻结读取使 receipt 的物理 hash 与逻辑边**同源**、替换后的磁盘件被下游
物理锚核验**拒绝**（或整体 fail-closed）。用 `inspect.getsource` 确认 reconcile 函数体内
`sha256_file(` 已不再对边文件二次读盘（对 producer_path 的那次是脚本自身指纹，非边文件，属正常）。

### T4 批 7 新洞：冻结读取边界 fail-closed
对 `_read_frozen_formal_edges`（replay_edges.py 新增）构造边界输入，逐例断言 fail-closed：
symlink 边文件 / 空文件 / 坏 gzip / 坏 UTF-8 / 坏 JSON / 非 7 元组行 / 内存边与冻结磁盘边不一致。
任一放行＝BREACH，记录。

### T5 双 PATH 全量 SUITE
`/usr/local/bin/python3 scripts/tests/run_all.py` 与
`env PATH=/usr/bin:/bin /usr/local/bin/python3 scripts/tests/run_all.py` 各跑一次；
脚本捕获退出码 + 计数 PASS/FAIL + 抓汇总行（别整段回显）；断言两次均 121/121、exit 0、无 skip。

### T6 F2-03 文档诚实性
读 `references/data-pipeline-solana-capture.md` 新增段、`PLAN.md` 尾部、`batch6_done.md` §11 真字节，
断言：没有把"未实现的主动伪造防御"虚称"已修/已建立根基"；威胁模型边界（假设 data/ 可信、
不抗能写盘的整体伪造对手、根治需签名/链上重验属独立后续工程）表述诚实、无夸大。

## 交付
`maintenance/repair-20260817-sqd-v4/batch7_verify.md`：T1-T6 逐项 CONFIRMED/异常 + 实证命令与真实输出
（含红态对照如做）+ 任何 BREACH/WEAK/NOTE + 总判定（PASS 无异常可合并 / BLOCK 有异常）。
完成即停，不 merge 不 push。
