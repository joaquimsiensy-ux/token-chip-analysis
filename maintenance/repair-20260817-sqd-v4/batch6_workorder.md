# 批 6 工单：opus 盲审消化轮（BLOCK → 消化 4 BREACH + 2 WEAK）

> 先读同目录 `PLAN.md` 与五份 `batch*_done.md`，再读本工单。分支 `fix/sqd-solana-v4`
> 续作（开工先把本工单收编为独立 commit）。
> 背景：opus 攻击型盲审对 v6.49.0 判 **BLOCK**，实证击穿 4 BREACH + 2 WEAK + 若干 NOTE。
> 本批是同一版本（6.49.0，尚未合并）内的收口消化，不 bump 版本。

## 施工总纪律

1. **先复核后修**：每条 finding 动手前先给 `CONFIRMED` / `REFUTED` 判断，附**能跑的独立
   证据**——REFUTED 不接受空口否认，必须有反证命令/构造输入证明盲审看错了。属实项才修。
2. **先红后绿**：每条修复先提交一个能复现缺陷的红态测试（committed red），再修到绿。
3. **归因最小化**：本轮必然要改生产逻辑（就是修生产 bug），但每处改动写清"改了什么、为什么、
   最小影响面"。禁顺手重构无关代码。
4. **采集器改动＝两步登记**：任何改到 `scripts/solana/fetch_sqd_transfers_v2.py` 的 finding
   （F-02/F-03/F-05/F-06 可能涉及），按批 4 两步登记纪律：先形成含新采集器的 commit，再单独
   commit 用 `git show <commit>:scripts/solana/fetch_sqd_transfers_v2.py | shasum -a 256` 把新哈希
   登记进 `producer_history.py`；否则消费端对表会自拒新产物。旧哈希按 REVOKED/ACTIVE 语义处理，
   别直接抹掉历史条目。
5. ARC 案目录 `/Users/uravvv/Documents/5.6筹码分析/ARC分析/` **绝对只读**；merge/push 不做（验收方在
   opus 二审后执行）。
6. **收批标准＝SUITE 全绿（含本批新增防回归用例）＋每条 finding 处置台账**。

---

## F-01 [BREACH-01 · P0 正式链回归] EVM/duckdb 边源被 formal 闸判成 legacy 拒收

**定位**：`scripts/report/wave_scan.py:640-648`（granularity 赋值：evm-v2 → `"log"`、
duckdb → `"source-defined"`）；`scripts/report/adjudication_validator.py:88-92` 与
`scripts/report/handoff_manifest.py:400-405`（判据 `granularity not in ("transaction","instruction")`
→ 判成 legacy 诊断产物拒收）。

**复核**：真跑 `wave_scan.py --duckdb <构造库>`（或 `--edges-evm-v2`）产出真实 v4 报告，喂
`adjudication_validator` 与 `handoff_manifest` verify，确认 EVM/duckdb 产物是否真被拒。

**修法**：把 formal 判据从"granularity 白名单只含 transaction/instruction"改为
"`non_formal is False` 且 granularity ∈ **全链白名单** `{transaction, instruction, log,
source-defined}`"。三处判据（validator/handoff/以及任何同款判据）一并改，保持一致。

**防回归（本条重中之重）**：opus 指出 SUITE 里"真跑生产器"与"跑消费闸"从不相交——所有 wave
fixture 都硬写 Solana 专属的 `transaction`，连名字带 EVM 的测试也用 Solana 值，属结构性假覆盖。
**必须补一条端到端 SUITE 用例**：真跑 `wave_scan --duckdb`（或 `--edges-evm-v2`）→ 其真实产物
喂 `handoff verify` / `adjudication_validator`，断言非 Solana granularity 能正常过 formal 闸。
不接受再用手写固定 granularity 的 fixture 糊弄。

---

## F-02 [BREACH-02 · P0 归属防线根基] meta digest 字段缺席即放行＋无条件回填＝洗白器

**定位**：`scripts/solana/replay_edges.py:312-317`（`old_digest = cache_meta.get("edge_logical_sha256")`；
`if old_digest is not None and old_digest != edge_digest:` 缺席即跳过校验）、`:324-328`（随后无条件
把本次算出的摘要回填 meta 并原子发布）。

**复核**：构造一份 v4 meta，`pop` 掉 `edge_logical_sha256` 与 `edge_rows` 两字段（`collector_sha256`
保留真值），配任意伪造边文件，跑正式 `cmd_reconcile`，确认能否拿到 `gate_pass=True` 的 receipt。

**修法**：v4 meta 中 `edge_logical_sha256`/`edge_rows` 改为**必填**，缺失即 BLOCK；把这两字段的
存在性与一致性校验**前移到 `_validate_cache_meta`**（不要等到 `cmd_reconcile` 才查）；`cmd_reconcile`
取消"缺席回填"语义，改为纯校验（有值必须一致、缺值直接拒）。
- 前置约束确认：批 4 T1 已让采集器 `finalize` 成功后必写这两字段，所以正式 v4 产物必带；legacy 路径
  不产 v4 meta。请复核确认没有别的合法路径依赖 reconcile 的回填来"首次建立绑定"——若有，那条路径
  要改成由采集器负责写、reconcile 只读校验。
- `scripts/lib/camp_series_provenance.py` 的对锚校验同步（它比对 `cache_meta["edge_logical_sha256"]
  == receipt.edge_digest`，两者若都是同一次伪造 reconcile 写的就必然自洽——修法要打断这个自证环）。

**防回归**：破坏性注入补第 4 项（digest/rows 字段缺席 → 必拒）；单测覆盖 `_validate_cache_meta`
遇缺字段 meta 直接 BLOCK。

---

## F-03 [BREACH-03 + WEAK-03 · P1] non_formal 只来自 CLI 开关，legacy 补零可洗成 formal

**定位**：`scripts/report/wave_scan.py:786`（`"non_formal": bool(a.legacy_sol5)`）；wave_scan 全程
不读 cache meta、不验 mint、不验 collector。经 `wave_scan.load_sol` 加载的 `flow_anomaly_scan.py`、
`entity_source_trace.py` 同样不验。

**复核**：把旧 5 元组机械补两常量列（`tx_index=0, instr_index=-1`，零新信息）成 7 元组，走**正式
入口**（不加 `--legacy-sol5`）跑 wave_scan，确认能否产出 `non_formal=False` 的 v4 报告并过裁决。

**修法**：wave_scan（及经它加载的 flow/entity 传导件）对 `--edges-sol` 正式路径**强制读 meta ＋
collector 对表**，`non_formal` 由 meta 身份**派生**而非 CLI 开关自报。与 F-02 的 meta 校验复用同一
套 v4 身份校验（`_validate_cache_meta` 或抽公共件），别各写一份。

**防回归**：补零洗白输入 → 正式入口必拒的用例（红→绿）。

---

## F-04 [BREACH-04 · P1] dormant 审计 non_formal 标记全仓无人消费（死字段）

**定位**：`scripts/solana/audit_closed_accounts.py:60,439-440`（写 `non_formal`/`order_ambiguous`
标记）；全仓 `non_formal` 消费点（`handoff_manifest.py:401`、`audit_release_gate.py:846`、
`adjudication_validator.py:89`）全部只读 **wave** 报告的标记，dormant 自己写的标记无人读。

**复核**：`check_dormant` 产 `non_formal=True` 的 legacy 产物喂 `audit_release_gate`，确认它是否与
formal 产物零差别通过（对照组：把 wave 报告改成 non_formal=true 应被拒，证明闸本身是活的）。

**修法**：把 dormant 审计的 `non_formal`/`order_ambiguous` 接进 `check_dormant` / `audit_release_gate`
消费链。**顺带全仓审一遍"写了标记但无人消费"的死字段**，列清单进 done（防同类漏接）。

**防回归**：legacy dormant 产物过发布闸 → 必拒的用例。

---

## F-05 [WEAK-01 · 契约漏洞] ExtMerger 非法输入面比 MemMerger 松

**定位**：`scripts/solana/fetch_sqd_transfers_v2.py:818-838`（`ExtMerger._validate` 只校验 `f_type`/
`t_type` 是 VARCHAR，未校验 `ts/tx_index/amt` 的 JSON 类型，且 `regexp_full_match(amt,'[0-9]+')`
允许前导零 → `finalize` 拼接产出语法非法的 gz）。对照 `spl_edge_core.py:19-35` 的 `validate_edge_row`
要求真 int。

**复核**：同一份非法 part（amt 为 JSON 字符串 `"5"` / 前导零 `"007"` / ts、tx_index 为字符串）分别
喂 MemMerger 与 ExtMerger，确认输出不等价。

**修法**：`ExtMerger._validate` 补 `json_type($[0]/$[2]/$[6])` 类型校验 + 禁前导零，与
`spl_edge_core.validate_edge_row` 对齐，恢复 `batch2_done.md §7` 宣称的"两路径逐字节一致"契约。

**防回归**：两路径对非法输入等价拒绝的契约测试。

---

## F-06 [WEAK-02 · 验收面漏扫] HyperSync 死代码 5 元组构造未被白名单覆盖

**定位**：`scripts/solana/fetch_sqd_transfers_v2.py:448`（`edges.append((ts, slot, f, t, amt))`，
在 `HyperSyncFetcher.scan_area` 内）。该代码因 `run()` 开头 `if hs_cfg is not None: raise SystemExit(2)`
（`:958-960`）与 CLI `--hypersync`（`:1318-1320` 附近）前置硬拒而不可达——是死代码非活缺陷，但
`grep_legacy_whitelist.md` 的扫描正则末尾强制 `=` 匹配不到 `append((...))` 构造形式，导致漏扫，
"正式非白名单命中=0"是正则口径造出来的。

**处置**（二选一，理由写 done）：
- a) 修正 `grep_legacy_whitelist.md` 扫描正则以覆盖构造形式（`append((ts, slot, ...))`），并把
  `:448` 显式列入"死代码豁免"白名单；**（倾向此项——不额外触发采集器 producer 重登记）**
- b) 随 HyperSync 整段死代码一并删除（更彻底，但改采集器 → 走 F 纪律 4 两步重登记）。

---

## F-07 [NOTE-03 · 口径残留] batch2_workorder.md 旧 124816 表述

**定位**：`batch2_workorder.md:17` 仍写"ARC 案 124,816 条"且无勘误标注。历史件不改写——仅在该行
**补一句指向** `PLAN.md` 尾部勘误 / `batch4_done.md §6.3` 的修正口径（124,816＝混合口径，非纯
DISTINCT 损失；域内机械可证＝11,502 行/8,487 组）。

---

## NOTE 顺修评估（低成本则修，否则记遗留交盲审）

- **NOTE-02**：`replay_edges.py:186-189` 接受 `instr_index >= -1`，`spl_edge_core.py:28-29` 严格
  `== -1`，同族未等深。当前无 instruction 级生产者时不构成 bug，统一成本低可顺修（把 replay 也收严
  到 `== -1`，未来真有 instruction 级边再一起放宽）。
- **NOTE-01**（reconcile TOCTOU：`:309` 内存 edges vs `:327` 磁盘 sha256_file 两次读之间可被替换）、
  **NOTE-04**（`pair_tx` 对 `{S:-12,R:+10}` 配出 `S→ZERO` 销毁边、withheld 形态假设）：评估记录，
  非本轮必修则入遗留清单交 opus 二审。

---

## 交付物

`batch6_done.md`：
- 每条 finding 的 `CONFIRMED`/`REFUTED` 复核证据（含 REFUTED 的反证）；
- 修法 diff 要点、先红后绿证据（红态 commit 哈希）；
- 若动采集器：producer 两步重登记记录（新哈希 + git show 复现）；
- SUITE 全绿输出（含新增端到端 EVM/duckdb 用例、注入第 4 项、各红→绿单测）；
- F-04 的"死字段"全仓审计清单；
- 六视角①②自审、遗留清单（交 opus 二次盲审的自述风险）。

完成即停，不 merge 不 push，等 opus 二次盲审。

---

## F-08 [验收方发现 · 批 6 补丁] SUITE 新测试硬依赖外部 rg 二进制，无 rg 环境假失败

**定位**：`scripts/tests/test_batch6_sqd_v4_blind_review.py:231`（F-06 用例
`subprocess.run(["rg", ...])`）。验收方环境 PATH 无 `rg` → `FileNotFoundError` → 该测试
rc=1「无输出」→ SUITE 120/121 FAIL。施工环境恰好有 rg 才自报全绿——发布门禁测试不可携带
环境外部二进制依赖。

**修法**：该用例改**纯 Python 实现**（`re` 模块等价扫描目标文件与模式；注意 rg 正则语法与
Python re 的差异要等价转换并自证——用一个已知命中/一个已知不命中的样例断言扫描器本身有效）。
**禁止用 `shutil.which('rg')` 缺失即 skip 的降级**——skip 即假覆盖，恰是本工程反对的。
顺带机器排查批 6 全部新增/改动测试还有无同类外部二进制依赖（`rg`/`fd` 等非 POSIX 必备命令），
有则一并改纯 Python。修完在**不含 rg 的 PATH** 下亲跑该测试与全量 SUITE 证明可移植
（如 `env PATH=/usr/bin:/bin python3 ...`）。红→绿纪律照旧（红态=当前 FileNotFoundError 即为
天然红，绿态 commit 修复）。追加到 `batch6_done.md` 一节「F-08 补丁」，完成即停。
