# token-chip-analysis `main` 全目录六视角 review

- 审查日期：2026-08-13
- 唯一审查对象：`/Users/uravvv/.claude/skills/token-chip-analysis`
- 分支：`main`
- 冻结提交：`2ebd885d1a1364779338e02f8f30e991eec2302d`
- 版本：`6.39.5`
- 审查副本：由上述本地仓库以 `--single-branch --branch main --no-local` 克隆到临时目录；所有读码、测试和反例均在冻结副本上完成
- 方法权威源：`references/maintenance-review-repair.md` 第一节末尾“标准 review 指令模板”及第二节强制归因
- 结论：**BLOCK**

## 1. 先说结论

本轮不是“整体看了一遍”，而是对 `main` 的 450 个 tracked 文件全部做了字节级读取和按类型检查，再对活跃代码、文档、schema、CLI、测试和发布门禁按六视角交叉追踪。共确认 **13 项有效 finding：P0 5 项、P1 6 项、P2 2 项**。

最严重的三个新证据是：

1. `accounting_gate.py --as-of-block` 只把调用者给的块高写进收据；实际模型探测仍在当前 tip/`latest` 执行。实测可产出 `target.as_of_block=1`、`tip_block=100` 的 `PASS`，而共享发布校验只按前者与其他收据对齐。
2. `supply_truth_gate.py` 的正式模式允许任意 `--tolerance-bps`，共享发布校验没有固定阈值或 waiver。实测重放净供给 `1`、链上供给 `100`（偏差 99%）在 `--tolerance-bps 10000` 下 `PASS/exit 0`。
3. `holder_distribution_scan.py` 只拒绝 owner 快照总和“超过”总供应，不要求闭合到总供应，也不把该快照与四查实际消费的 balances 文件绑定。实测快照只含总供应 1% 时，scan 仍 `exit 0`，独立 `validate` 返回空错误列表。

因此，全量 suite 最终全绿不能推翻本报告。现有 suite 没覆盖上述反例，而且本轮另复现了现存 R10 候选与四个修复代码自身的新缺口。

## 2. 范围与全量覆盖

### 2.1 文件分母

| 类别 | 文件数 | 本轮动作 |
|---|---:|---|
| tracked 文件总数 | 450 | 450/450 读取；附录逐文件列路径、字节数、SHA-256 与审查标签 |
| Python | 243 | 全部 UTF-8/tokenize 读取并 AST parse；其中活跃生产脚本 138、测试/守卫 94、archive/maintenance Python 11 |
| Markdown | 111 | 全文读取；活跃 48、maintenance/archive/blind review 63；历史件只用于归因和迁移谱系，不冒充当前运行口径 |
| CSV | 45 | 全部逐行解析，共 507,013 行；列宽一致 |
| gzip CSV | 2 | 全量解压并逐行 CSV 解析，共 352,196 行；两文件均固定 7 列 |
| JSON / JSONL | 33 / 1 | 全部解析；JSONL 逐行解析 |
| TXT / shell / TOML / lock / 无扩展 | 8 / 2 / 1 / 1 / 2 | 全文读取；shell 逐个 `bash -n` |
| PNG | 1 | 文件签名、Pillow 解码与 `verify()` 通过（2306×1101 RGBA） |

CSV 与 gzip 合计实际读取 **859,209 行**。没有抽样读取数据文件。

### 2.2 跳过项

没有文件被跳过。六视角并非对每种文件都具有相同语义：

- CSV/gzip/PNG 等数据资产没有“异常分支”或“门禁入口”，故视角②/⑥记为“不适用”，但仍完成全字节、格式、manifest/消费者引用检查。
- `archive/`、`maintenance/`、`blind-reviews/` 是历史/验收记录，不作为当前生产入口；它们仍被全文读取，用于视角③迁移谱系、④同族修复面和强制归因。
- 测试文件不被当成生产证据；逐个检查是否挂入 `run_all.py`、fixture 是否手写 PASS 冒充端到端、是否覆盖生产路径。83 个 `test_*.py` 全部挂载，无孤儿测试。

## 3. 测试与机器检查

### 3.1 全量 suite

- 沙箱内 `python3 scripts/tests/run_all.py`：92 PASS，2 条 vertical-slice 因 `socket.bind(127.0.0.1)` 被环境 `EPERM` 拦截，未进入业务逻辑。
- 在允许 loopback 的同一冻结副本补跑：
  - `test_batch3_solana_vertical_slice.py`：PASS，真实 producer→runner→aggregator→READY→release。
  - `test_batch3_evm_vertical_slice.py`：PASS，eth/bsc/base slices 与 nonzero-dead closure。
- 合并口径：**94/94 suite 项均完成且通过**。

这只证明既有回归集合通过；本报告的反例是 suite 之外的独立检查。

### 3.2 其他全量检查

- 243/243 Python AST parse；2/2 shell `bash -n`。
- `docs_lint.py --all`：58 个运行时文档引用通过；但它没有检查“收据字段是否真的被 validator 重验”，故未发现 F-08。
- `invariant_scan.py`：52 producer、55 consumer、43 atomic write、58 formal entrypoint 的登记检查通过；其静态 E2E 来源证明仍有仓库明确登记的 KNOWN-OPEN，见 F-12。
- 8 个发布标签表与 `references/labels/manifest.json` 指纹一致。
- 83/83 `test_*.py` 出现在 `run_all.py`，0 个孤儿测试、0 个陈旧挂载名。

## 4. Findings（按严重度）

### F-01 — P0 — accounting 收据把调用者块高冒充实际观测块

- 视角：①字段来源、⑤双向一致性、⑥闸可绕性
- 归因：**修复中新引入**（`5ada7c0`，v6.39.3）
- 证据：`scripts/evm/accounting_gate.py:391-395,429-438,445-486`；`scripts/report/shared_release_receipt.py:263-277,295-299`
- 问题：`result["as_of_block"]` 直接取 `a.as_of_block`，但合约代码读取明确使用 `eth_getCode(..., "latest")`，rebase/FOT/事件窗口也全部以 tip 运行。共享发布校验把这个自报块高构造成正式 target，只验证与 reconciliation/adversarial target 相等，不验证 `tip_block == as_of_block`，也没有历史块观测收据。
- 最小反例：离线 fake RPC 返回 tip=100，以 `--as-of-block 1` 运行。结果为 `PASS/exit 0`，收据 `as_of_block=1`、`tip_block=100`；RPC 调用含 `eth_getCode(..., "latest")`。
- 最强替代解释：帮助文字已诚实声明“模型探测仍在当前 tip”，所以这是有意设计。**不采纳**：诚实注释不能把 tip 观测变成 block 1 观测；下游把该字段当成三键 target 做正式同一时点闭合，语义上已经冒充。

### F-02 — P0 — 供给真值硬闸的正式容差可由调用者任意放大

- 视角：①字段来源、⑤双向一致性、⑥闸可绕性
- 归因：**历史漏检**（`--tolerance-bps` 自 `cce3e94`/v6.0.0 即存在；不属于既有 finding，也不是 v6.38 repair 新增）
- 证据：`scripts/lib/supply_truth_gate.py:76-83,159-178,268-332`；`scripts/report/shared_release_receipt.py:162-206`
- 问题：正式模式允许任意整数 `--tolerance-bps`，未限定非负、上限或 canonical 10 bps。共享发布 validator 不检查阈值，也不重算 `diff_bps <= tolerance_bps` 的政策合法性。生产者可以合法地产出弱化后的 PASS 收据并进入正式聚合。
- 最小反例：`replay_net=1`、`onchain_total_supply=100`、`--tolerance-bps 10000`，实际输出 `PASS/exit 0`、`diff_bps=9900.0`。
- 最强替代解释：CLI 参数可能是有意给特殊币种调容差。**不采纳**：正式工作流与 schema 没有 override/waiver/审批绑定；一个“硬闸”不能仅靠调用者随意扩大到 100% 后仍被共享发布校验无条件接受。

### F-03 — P0 — 分布硬闸接受未闭合的 owner 快照

- 视角：①字段来源、②失败分支、⑥闸可绕性
- 归因：**历史漏检**（`a262b189` 初始引入即只检查 `sum > total`）
- 证据：`scripts/report/holder_distribution_scan.py:139-168,195-219,498-525,752-790`；`scripts/report/handoff_manifest.py:388-395`
- 问题：scan 只在 `sum(balances) > total` 时失败，缺少 `sum == total` 或与经四查 balances 输入同文件/同哈希的约束。`data_map` 只证明“这份文件被登记”，不证明它是全量 owner 快照；handoff 只是调用同一个弱 validator。
- 最小反例：`total_supply_raw=100`、owner 快照只有 `{"0xaaa":"1"}`，合法 data_map 与 PASS supply_truth。`build_scan` 产 `exit_code=0`，`snapshot_total_raw=1`，随后 `validate_scan(..., "initial") == []`。
- 影响：漏掉 99% owner 可把真实鼓包、头部集中度和未知合约桶全部隐藏；final scan 会沿用同一快照，因此可污染最终报告。
- 最强替代解释：四查对账会保证另一个 balances 文件闭合。**不采纳**：代码没有把 distribution snapshot 的 path/SHA 与 reconciliation receipt 的 balances input 做等值绑定；data_map 可同时登记多份文件。

### F-04 — P0 — `camp_share_series` 仍是未绑定重放的调用者自报字段

- 视角：①字段来源、⑤双向一致性、⑥闸可绕性
- 归因：**历史漏检**（既有 R10 候选 RA-01，当前 main 未修）
- 证据：`scripts/report/state_from_facts.py:85-107`；下游 `scripts/report/figures_from_facts.py:93-125`
- 问题：compiler 只验 `dates/series` 容器和长度，不验有限数、0–100 值域、同点闭合、标准阵营名、末点对 facts，也不绑定 replay receipt/输入哈希。A4/A5 只能封住这些错误字节，不能把自报数变成链上事实。
- 最小反例：facts 实体当前份额 25%，source 注入 `大庄=0、任意阵营=-899、散户=999`，`compile_state()` 接受并原样输出。
- 最强替代解释：facts 没有历史序列，source 本来就负责承载。**不采纳**：承载不等于无需来源证明或数学约束。

### F-05 — P0 — 互斥阵营重复地址仍被后项静默覆盖

- 视角：①字段来源、④同族调用面、⑤双向一致性
- 归因：**历史漏检**（既有 R10 候选 RA-02，当前 main 未修）
- 证据：`scripts/evm/replay_pass2.py:2-10,26-38`；同族 `scripts/evm/replay_duck.py:371-380`、`scripts/solana/replay_edges.py:237-245`
- 问题：文档声明“阵营互斥”，代码却以 `addr2camp[address] = camp` 静默覆盖；DuckDB 版甚至明确保留“后配置覆盖先前”。交换 JSON 键顺序即可改变归属，最终加总仍为 100%，外观正常。
- 最小反例：同一地址同时放入 camp_A/camp_B，100% 余额被 JSON 后出现的 camp_B 获得，exit 0。
- 最强替代解释：后项覆盖可作为优先级。**不采纳**：没有优先级 schema，且生产 docstring 明示互斥。

### F-06 — P1 — 翻转闸可用任意 10 字符理由解除，未绑定披露或用户裁决

- 视角：①字段来源、⑤双向一致性、⑥闸可绕性
- 归因：**修复中新引入**（`018c46f`，v6.39.4）
- 证据：`scripts/report/entity_source_trace.py:655-674,765-826`；`scripts/report/handoff_manifest.py:595-665`
- 问题：真实 FIFO/LIFO 主导来源翻转原本 `exit 2`；新版只要求 `ENTITY:ANCHOR:REASON` 且 reason 长度 ≥10，即把 `publishable` 改为 true。没有用户决定收据、evidence 引用，也没有 A4/A5 检查报告确实按多策略并列披露。
- 最小反例：既有翻转 fixture 加 `--acknowledge-flip ex:current:aaaaaaaaaa` 后 `exit 0`；ledger 同时显示 `stable=false`、`publishable=true`。
- 最强替代解释：这只是分析师对真实多来源结构的人工判断通道。**不采纳**：字符串长度不是判断证据；代码承诺的“并列披露”没有任何 consumer 执行。

### F-07 — P1 — 多 manifest 迁移在写失败时不是全有或全无

- 视角：②失败分支、③存量迁移、④同族调用面
- 归因：**修复中新引入**（`da2c398`，v6.39.0）
- 证据：`scripts/evm/fetch_hypersync_v2.py:277-311,414-427`；`maintenance/repair-20260809-apu-legacy/WORKORDER_apu_legacy_gaps.md` 的“两阶段全验证-或-全不写”不变量
- 问题：函数先验证全部候选，但提交阶段逐个 `atomic_write_json`。第二个写入失败时，第一个已经升级，函数抛错并留下新旧 schema 混合状态；CLI 还只捕获 `ValueError`，`OSError` 直接 traceback。
- 最小反例：两个 legacy `done.json`，向第二次 `atomic_write_json` 注入 `OSError`。结果 `run_1=hypersync-v2-done/v3`、`run_2=legacy`。
- 最强替代解释：重跑会把剩余文件补齐。**不采纳**：可恢复不等于事务成立；持久性第二写失败时会长期保留部分迁移，且工单明确承诺“全不写”。

### F-08 — P1 — v6.39.5 后 initial `upstream_receipts` 可伪造且 validator 明确忽略

- 视角：①字段来源、⑤双向一致性、⑥闸可绕性
- 归因：**修复中新引入**（`2ebd885`，v6.39.5）
- 证据：`scripts/report/holder_distribution_scan.py:520-526,554-575,752-790`；`references/scan-schemas.md:299-302,326-339`
- 问题：schema 权威文档写“initial 绑定上游收据”，JSON 结构也列 `upstream_receipts`；当前 `semantic_payload()` 却无条件删除该字段，`validate_scan()` 也不逐项 `_verify_bound`。字段继续以“绑定”形态出现在产物，实际不构成证据。
- 最小反例：把 `upstream_receipts` 改为不存在的 `does-not-exist.json`、伪 SHA、伪 size，`validate_scan` 仍返回 `[]`。
- 最强替代解释：提交注释称它只是记录性字段，不参与分区计算。**不采纳**：若仅记录，schema 不应宣称绑定；若保留为收据引用，validator 至少必须拒绝不存在/哈希不符。当前是可伪造的证据外观。

### F-09 — P1 — 图 1 对未知阵营静默漏画

- 视角：④同族调用面、⑤双向一致性、⑥闸可绕性
- 归因：**历史漏检**（既有 R10 候选 RA-03，当前 main 未修）
- 证据：`scripts/report/figures_from_facts.py:93-125`；`scripts/report/standard_charts.py:141-175`
- 问题：wrapper 接受任意阵营并打印输入阵营数，绘图层只取 `CAMP_ORDER` 交集；未知阵营无 warning、无非零退出。A5 只绑定最终 PNG 哈希，不重验图例集合。
- 最小反例：输入 `大庄=60%` 与未知阵营 `40%`，真实 legend 只有 `大庄`。
- 最强替代解释：白名单用于防止非标准命名。**不采纳**：正确行为应拒绝，而不是静默删掉 40% 数据。

### F-10 — P1 — 对抗复核可由两个 2 字节 `ok` 产物满足

- 视角：①字段来源、②失败分支、⑥闸可绕性
- 归因：**历史漏检**（既有 R10 候选 RA-04，当前 main 未修）
- 证据：`scripts/report/adversarial_review_runner.py:44-113`；`scripts/report/audit_release_gate.py:706-724`
- 问题：runner 只要求 exit 0 和 staging 非空；发布闸只核角色名、blocker resolved 与 decision。没有 artifact schema、claim 覆盖、重算引用或 finding 明细。
- 最小反例：entrypoint 只写 `ok`；两角色 execution receipt 均有效，`check_adversarial()` 无错误。
- 最强替代解释：机器无法判断自然语言质量。**不采纳**：无需判断结论对错，也能强制结构化 claim IDs、覆盖集合和重算引用；当前连客观结构都没有。

### F-11 — P1 — 小样本 EVM replay gate 失败仍 exit 0 并继续产序列

- 视角：②失败分支、④同族调用面、⑥闸可绕性
- 归因：**历史漏检**（既有 R10 候选 RA-05，当前 main 未修）
- 证据：`scripts/evm/replay_pass1.py:136-163`；`scripts/evm/replay_pass2.py:21-38,94-123`；正确同族 `scripts/evm/replay_duck.py` 在 gate fail 非零退出
- 问题：pass1 已落 `gate_pass=false` 但 `main()` 没返回非零；pass2 只取 `mint_total_wei`，不要求 gate PASS，继续写正式命名 `camp_series.json/entity_series.json`。
- 最小反例：未 mint 的普通地址转出 100，实测 pass1 `rc=0, gate_pass=false, neg=1`，pass2 随后 `rc=0` 并产序列。
- 最强替代解释：后续 identity/release gate 可能再拒绝。**不采纳**：上游和直接下游都把坏账当成功，正式命名产物已生成；后闸不能修正错误退出语义。

### F-12 — P2 — formal E2E 来源守卫仍可被模块级重绑定绕过

- 视角：④同族调用面、⑥闸可绕性
- 归因：**老问题修复不全（半修残留）**；仓库已登记并由用户在 2026-08-09 接受降级边界
- 证据：`scripts/tests/invariant_scan.py:509-520,647-693` 及其 KNOWN-OPEN 注释；`maintenance/repair-20260806/b4_progress.md`
- 问题：scanner 记住顶层 import 名，却不检查后续模块级重绑定。样本可先 `import subprocess`，再 `subprocess = Dummy()`；函数内保留真实脚本字面调用即可被计为执行证据。
- 最小反例：既有武器化样本得到 `errors=[]`、测试 exit 0、Dummy 收到 6 次调用、0 个生产进程启动。
- 最强替代解释：这是已知且已接受的元守卫边界。**不采纳为“无问题”**：风险接受不改变技术事实；本轮不把它夸大为外部 P0/P1，但必须保留 P2 记账。

### F-13 — P2 — 现役 HyperSync v2 仍接受位置明文 token，同族回归漏入口

- 视角：④同族调用面、⑤双向一致性
- 归因：**老问题修复不全（半修残留）**（既有 R10 候选 RA-07）
- 证据：`scripts/evm/fetch_hypersync_v2.py:314-335`；`scripts/tests/test_token_no_positional.py:1-14`
- 问题：v2 采集器保留可选位置 `api_token`，且优先于环境变量/文件；F-07 回归只列三支 v1 脚本，没有现役首选 v2。
- 最小反例：v2 parser 接受首个位置明文 secret，并在 `resolve_token()` 返回它。
- 最强替代解释：这是旧兼容入口且会 warning。**不采纳**：`ps` 可见的密钥泄漏面不会因 warning 消失；同族修复明确漏入口。

## 5. 六视角逐条结果与实际文件面

### ① 字段来源审计

- 实际检查：138 个活跃生产 Python；33 个 JSON/schema/manifest；`SKILL.md`；`references/analyze-workflow.md`、`split-run.md`、`scan-schemas.md`、各链 pipeline、`report-template.md`；receipt kernel/validator；52 producer 与 55 consumer 登记面；45 CSV、2 gzip 与标签 manifest。
- 重点端到端链：采集 done/receipt → channels preflight → replay stats/balances → reconciliation/supply truth → handoff READY → entity freeze → A4/A5 → build/release。
- 结果：F-01、F-02、F-03、F-04、F-08、F-10。其余关键 receipt envelope 的 producer/input/hash 基础结构未发现新增缺口。
- 不适用：纯图片、纯历史文本没有运行时字段来源；仍做全字节读取与引用检查。

### ② 失败分支审计

- 实际检查：138 个活跃生产 Python 的宽泛 `except`、warning/continue、`return 0`、subprocess returncode、临时文件/原子替换、失败 receipt 与旧 PASS 保护；重点逐文件读 `fetch_*`、`replay_*`、`*_gate.py`、`*_receipt.py`、`handoff_manifest.py`、`build_html.py`、迁移器。
- 结果：F-03、F-07、F-10、F-11。
- 正向结论：receipt kernel、四查 runner、A4/A5 seal、正式 build/release 的点名失败路径在既有注入测试中 fail-closed；不据此推出未测变体也闭合。

### ③ 新格式的存量迁移

- 实际检查：全库 schema/version/legacy/migrate/refresh 搜索；39 个 v6.37→v6.39.5 改动文件逐个 diff；`migrate_legacy_case.py`、HyperSync v2 done v3、supply-truth v3、handoff v3、distribution v1；maintenance 工单、红绿证据和历史 fixture 全读。
- 结果：F-07。另确认 supply-truth v2 只作为明确 legacy 负例留在活跃测试；maintenance 的旧 v2 smoke JSON 是历史证据，不被当前发布入口接受。
- 没有跳过旧件；archive/maintenance 只用于谱系与归因，不当成当前 producer。

### ④ 修复点的同族调用面

- 实际检查：以 `camp_share_series/addr2camp/gate_pass/tolerance-bps/as_of_block/upstream_receipts/acknowledge_flip/api_token/receipt schema` 全库 `rg`，逐项对照 EVM/Solana、旧/新 replay、producer/consumer、正式/探索、文档/测试；83 个测试挂载逐一核对。
- 结果：F-05、F-07、F-09、F-11、F-12、F-13。
- 正向结论：正式链 registry、版本三处、commands staging/部署副本、标签发布表、supply-truth v3 主生产者/消费者同版在既有守卫下闭合。

### ⑤ 双向一致性

- 实际检查：111 个 Markdown 全文；58 个运行时文档 lint；CLI argparse ↔ docs、schema ↔ producer/consumer、manifest ↔ 文件实态、测试 ↔ 生产入口、版本 ↔ SKILL/pyproject/VERSION 双向核对。
- 结果：F-01、F-02、F-04、F-05、F-06、F-08、F-09、F-13。
- 正向结论：当前版本 6.39.5 三处一致；正式候选链 eth/bsc/base/sol 与 registry/labels/route tests 一致；Robinhood/Arbitrum 保持 exploration 边界。

### ⑥ 每道闸的可绕性

- 实际检查：accounting/supply truth/reconciliation/time/handoff/distribution/entity freeze/A4/A5/build/audit 的必经性；可选参数、legacy 模式、不同入口、空壳产物、阈值覆盖、收据替换与同名文件；对 8 条 finding 做了独立最小反例。
- 结果：F-01、F-02、F-03、F-04、F-06、F-08、F-09、F-10、F-11、F-12。
- 正向结论：正式 `build_html --mode analysis-new|analysis-audit` 的 mode、facts/state/A4/A5 seal 与 release profile 仍是必经路径；本轮未找到省略这些参数仍冒充正式报告的新增路径。

## 6. 归因统计与收敛判断

| 归因 | 数量 | Finding |
|---|---:|---|
| 修复中新引入 | 4 | F-01、F-06、F-07、F-08 |
| 老问题修复不全 | 2 | F-12、F-13 |
| 历史漏检 | 7 | F-02、F-03、F-04、F-05、F-09、F-10、F-11 |

按 `maintenance-review-repair.md` §7.1，新引入与半修残留不分严重度都要求修复后重审。本轮有 P0，且新增问题并非边角料，不满足连轴 review 收口条件。

## 7. 建议修复顺序（仅建议，本轮未改 skill）

1. 先封 F-01/F-02/F-03/F-04/F-05 五个 P0；每项按不变量工单补原反例、同族变体、失败分支三件套。
2. 再封 F-06/F-07/F-08；这些直接长在 v6.39.x repair diff 中，必须对新代码再跑六视角①②。
3. 处理既有 R10 的 F-09/F-10/F-11/F-13；F-12 若维持用户接受边界，应在正式发布风险台账继续显式保留，不能写成 CLOSED。
4. 修完后冻结新 tip，先复跑本报告所有最小反例，再做一轮增量六视角；不能只复跑当前 suite。

## 8. 仓库不变性与交付边界

- 审查期间没有修改 `/Users/uravvv/.claude/skills/token-chip-analysis`；起止均为 `main@2ebd885d` 且 source worktree clean。
- 动态反例只写系统临时目录；全量 suite 只在临时 clone 产生运行时临时件。
- 本 Markdown 是唯一持久交付物；没有 patch、bundle 或修复 commit。

## 附录 A：450 文件逐文件覆盖台账

标签解释：

- `CODE-6L`：活跃生产代码，六视角全适用。
- `TEST-6L`：测试/守卫，检查 fixture、挂载、反例深度与生产入口；不把测试自报当生产证据。
- `LIVE-DOC`：活跃文档/schema，重点视角③⑤⑥并反查代码。
- `HISTORY`：archive/maintenance/blind review，全文读取，用于迁移、同族和归因；非当前运行入口。
- `DATA`：数据/标签/图片/压缩源，全字节与格式/manifest/消费者检查；②⑥无可执行语义。
- `CONFIG`：JSON/TOML/lock/manifest，结构解析并参与①③⑤。

下表由冻结 clone 的 `git ls-files` 机械生成；SHA-256 是本轮实际读取字节的摘要。

| # | 路径 | bytes | SHA-256 | 标签 |
|---:|---|---:|---|---|
| 1 | `.gitignore` | 686 | `94911ceb418c504de34ad63a48beb4c4f4e28d8e7007e5c66b0fdc22c371505a` | CONFIG |
| 2 | `CHANGELOG.md` | 71752 | `1aedd14721bd6e72ccd39d1a24dc5c755ec43ed7f405db979edc4f995b4da63f` | LIVE-DOC |
| 3 | `SKILL.md` | 7737 | `d40d6c569d79005b06c27df10ef05609f35227ce92a7f3365ee35e2b26099395` | LIVE-DOC |
| 4 | `VERSION` | 6 | `8d72971a556ac19353062df611d07bb72f802643ee28fdf5ae903050efa4d5b4` | CONFIG |
| 5 | `archive/CHANGELOG-archive.md` | 492848 | `5cf763fcf0d5f7a42eb6d53746a8a6f083baec11420bce581b8f285ab2067b85` | HISTORY |
| 6 | `archive/README.md` | 274 | `edca1f6b81f539cbebcfee1787e52a4d8b2aa61cef7cd47786e2f5a1697e4876` | HISTORY |
| 7 | `archive/case-history-notes.md` | 36994 | `d57533ffddaa6228445ba3bdab08a3305e67cdbe67f3bcb052380e30456656c2` | HISTORY |
| 8 | `archive/casebook-pre-6.28-snapshots.md` | 39492 | `aeeebbdaf0fe85513b11bd8f1ca4292855a6d0bd61287dcb2ad6cb2cb02a959f` | HISTORY |
| 9 | `archive/evals/README.md` | 4070 | `c9eaac966a78d3c1f0ed2a77ab8a0cce38ef028c20db450ca4017dba2577e127` | HISTORY |
| 10 | `archive/evals/cases/01-pythia-alpha-inventory.md` | 2390 | `9c5670a5757fa9a344d73c2c78faf782c25b96fdf35eb264cc63b9067644c989` | HISTORY |
| 11 | `archive/evals/cases/02-troll-ata-constant.md` | 2569 | `0c811784ccbbc6caeeae58dd13ec032449b313e15a51671055422f91f79c53c1` | HISTORY |
| 12 | `archive/evals/cases/03-iq-upbit-custody.md` | 2526 | `e3af23106b06f85ef4cfb5c2b578f664b267a3cf467e217bacbf57dcec6be3d0` | HISTORY |
| 13 | `archive/evals/cases/04-iq-eip7702-clustering.md` | 2211 | `2c3c5878c4976db4322264e1cfac186d80f8d5df534833d2b553db36c9c8f4aa` | HISTORY |
| 14 | `archive/evals/cases/05-quq-infra-in-entity.md` | 2618 | `cc26395ba9341205092995267fe9c486874aab448d243ef6a29c473fda688028` | HISTORY |
| 15 | `archive/evals/cases/06-silent-migration.md` | 2363 | `440627cd6456ff4d2919ada2d9096fe80d7a293ac7e3e57cebc3ac0e494e4111` | HISTORY |
| 16 | `archive/evals/cases/07-gmx-mirror-supply.md` | 2308 | `0d7b149e3910a5b1fc5e93a4e0d6d0e5c7e208025435c723906306e5914fa70c` | HISTORY |
| 17 | `archive/evals/cases/08-iq-denominator.md` | 2117 | `989b47af40e32f9afe8912dcbe238268ed857960aab91296c8eb575f494e97d7` | HISTORY |
| 18 | `archive/evals/cases/09-pythia-cleared-wave.md` | 4500 | `cec9013f205ef98fc15b5e298fcf9c75af66069ca17884997eb3ea91f6952073` | HISTORY |
| 19 | `archive/evm-par-route/README.md` | 351 | `014d522fdc2b646f67de2e669b2222cfba115ef7f33fde91a06715d114878020` | HISTORY |
| 20 | `archive/evm-par-route/fetch_hypersync_par.py` | 10296 | `ecd5f9389f174373bbc3c48a73bb4533741bf4e63240d96caf473b6c5047403b` | HISTORY |
| 21 | `archive/evm-par-route/merge_parts.py` | 1895 | `61e4f7c51fcfcbc519096712f97c92c3b9602086d32af4f52dc3bbb15c9f639b` | HISTORY |
| 22 | `archive/evm-par-route/test_progress_guards.py` | 1583 | `559e8bc32cb68b70027f15c567dcb7c834d69f0476b0c12103e4bfa83e8221d3` | HISTORY |
| 23 | `archive/evm-par-route/watchdog_dual.py` | 5207 | `9f560b19cdacc973dfab2286ea6f5c2b2238d743d633b3e4bd7f0e80d9acdac8` | HISTORY |
| 24 | `archive/fix-worklogs/fix_sixlens_20260806.md` | 15063 | `58f5456203e8c0e14092e41715fb9fd74a0466c1fba2f7925d77467fed75d831` | HISTORY |
| 25 | `archive/fix-worklogs/fix_v635_stage1_20260806.md` | 10952 | `bae3bf5981cf591a3907b613c2b6b068fc20a640a1f69eb3813cbaa6a9c810b0` | HISTORY |
| 26 | `archive/fix-worklogs/fix_v635_stage2_20260806.md` | 12672 | `1f98ece9d1968c7870765fea466531fd7779effb090c9a2c105e53ff68382646` | HISTORY |
| 27 | `archive/fix-worklogs/fix_v635_stage3_20260806.md` | 12920 | `d830ea521cd6bfe6c0d69805579fb724d0417bb30c4ce20bfec48faab559d5f7` | HISTORY |
| 28 | `archive/fix-worklogs/fix_v636_stage4_20260806.md` | 8163 | `4f07824cf236dd6d7ff58481dbc29256150e074541f9729bba9ff34257347a92` | HISTORY |
| 29 | `archive/scripts/fetch_fundedby.py` | 4625 | `bb6a0eed9c70f212282e3ae37a9beeb73142fc8cb989f0c85d0bcb47c697f665` | HISTORY |
| 30 | `archive/scripts/gas_fast.py` | 2714 | `dae565353a4766387faca4b2c40cff6e0d646e06e1b7c5411ccfc5b47985799c` | HISTORY |
| 31 | `archive/scripts/trace_network.py` | 4720 | `baf1f479ba5cb8552cd2bf7d30f0a7f1ccfad45a849c764ece2894d92d904665` | HISTORY |
| 32 | `archive/serial-conflicts/serial_conflicts_2026-07-22.json` | 1274 | `752834cc2152966320a6d32cff373313d5a7519f0f3474b0d4ea15d58f374036` | HISTORY |
| 33 | `archive/serial-conflicts/serial_conflicts_2026-07-22.md` | 754 | `20916b45038924b4db036b8ca1d6e460e4456d017588ddd5be4faa3056df2e1f` | HISTORY |
| 34 | `archive/serial-conflicts/serial_conflicts_2026-07-25.json` | 3103 | `7f2a6386abfbfcd8e41eef5d3baace88276944ba3852763ec398c18ba31ff71d` | HISTORY |
| 35 | `archive/serial-conflicts/serial_conflicts_2026-07-25.md` | 1704 | `b489d403b4ccb322c7b54cb6bcf8879a9da22b9e4e41ecec0f3d72964d0f28d0` | HISTORY |
| 36 | `archive/serial-conflicts/serial_conflicts_2026-07-26.json` | 3103 | `3b046d728f4ecf4df523f2bb1c6ca5ee402907aaf63fca5984e34839fc99e584` | HISTORY |
| 37 | `archive/serial-conflicts/serial_conflicts_2026-07-26.md` | 1704 | `663a9b388357ba89d147cfda31b9c19bcc93cb85c33198543607d9d317f32f08` | HISTORY |
| 38 | `archive/serial-conflicts/serial_conflicts_2026-07-28.json` | 3103 | `bd7213b1afa4fe719d1a084ce1cced7af484d1a4cdc7a44ae7c38e9f0a94e369` | HISTORY |
| 39 | `archive/serial-conflicts/serial_conflicts_2026-07-28.md` | 1704 | `5d76decb2fcb7a4a22734dd1fb44d4a5a5915b3c693371cdf1fcb7624fb42fac` | HISTORY |
| 40 | `archive/serial-conflicts/serial_conflicts_2026-07-29.json` | 3103 | `1ea17538f232e9c10ec80e5cf900514de97ca5f2d177193205446606f99f7ee3` | HISTORY |
| 41 | `archive/serial-conflicts/serial_conflicts_2026-07-29.md` | 1704 | `ea0e5598dab16b5f0cec489d7033d62549a5c0f0d5f029c945feacbf239cc436` | HISTORY |
| 42 | `archive/solana-readme-history/README-2026-08-05.md` | 10034 | `727133a296440493fb21077476c0e67cf93b790a7ca49501e2fe47c55d3fb15b` | HISTORY |
| 43 | `archive/solana-sqd-v1/README.md` | 424 | `ef7ffe639aaf5c9554e994b057d684d90c5516b1b83f05ad512b7d9ec3bb74bb` | HISTORY |
| 44 | `archive/solana-sqd-v1/fetch_sqd_transfers.py` | 13006 | `5d8a56dd33744391a1faff90cea1dfee12f06f88176b0d000a9e0470a4790445` | HISTORY |
| 45 | `blind-reviews/r9/45bf8f3/round-a-sixlens.md` | 22000 | `c2652f3d82f3485430430f23f34f9be03ddebcfb138d71b1b66b8fac23ab26f8` | HISTORY |
| 46 | `blind-reviews/r9/45bf8f3/round-b-ledger-replay.md` | 15025 | `d429c6837e28877e2ddd99095400a7c7347c77d0499afd7afcd95bf0c157c027` | HISTORY |
| 47 | `commands-staging/token-analyze-1.md` | 2112 | `9832eace6960bb6626a2b6e55f4c88745c5ffa33c640bc7eb97c71544aa0f215` | LIVE-DOC |
| 48 | `commands-staging/token-analyze-2.md` | 2449 | `510152a8a40efcc3f9b9a166b17d612b5166365baca22a6554771014cadebce6` | LIVE-DOC |
| 49 | `commands-staging/token-analyze.md` | 828 | `f227da3bddcee26b6a5d89fd325026a46bd208dd4f18017b670bf97f1280296e` | LIVE-DOC |
| 50 | `maintenance/repair-20260806/b1_progress.md` | 38142 | `7d22ea2c5c0462ca4ac0686d3192cf2676c309e522d4b321cf21b757d6a99191` | HISTORY |
| 51 | `maintenance/repair-20260806/b2_progress.md` | 10336 | `2af40e3f4f66ad7bd5836160639915102a1b4e1fcbc73320046adffd00e5e0b3` | HISTORY |
| 52 | `maintenance/repair-20260806/b3_progress.md` | 48195 | `9f83020a457886033f1d9f5c1eab7d55d5727ebd665baab7bed28803b60c0264` | HISTORY |
| 53 | `maintenance/repair-20260806/b4_progress.md` | 32565 | `9168f4bfea50007f8bec1de41ddad25ba9e476d76e319bad39ea86ba8a4dfefd` | HISTORY |
| 54 | `maintenance/repair-20260806/batch1-report.md` | 14319 | `ff760f160609f61161486aa58c243fc454d54585e462efe7f8678fda8d5166cc` | HISTORY |
| 55 | `maintenance/repair-20260806/batch2-report.md` | 22926 | `01a547f744c20c0db119cfdd1a819a7fecf4e53d42d9b22d303f1f657bf01f04` | HISTORY |
| 56 | `maintenance/repair-20260806/batch3-report.md` | 17234 | `2607c8d9226450727869ae8abed24db024c61487b65dd77f2e243e844d69bb61` | HISTORY |
| 57 | `maintenance/repair-20260806/batch4-report.md` | 13271 | `870f9072cd0767bda01248308adba79012f8e5c9b9330acc975409b8651c68b9` | HISTORY |
| 58 | `maintenance/repair-20260806/diff-finding-map.md` | 48126 | `8f8a220cb65870137ef12cf73c7ce9f04d642a5df9314e164f7b6d95cdf80bb5` | HISTORY |
| 59 | `maintenance/repair-20260806/exemptions.md` | 2343 | `b4f8c4f83837adb33565ba4f1ba8f3689d07f8b4f2deb9c0447defc24e721131` | HISTORY |
| 60 | `maintenance/repair-20260806/final_acceptance.md` | 7132 | `26d7e229cda8f92cb17f48132a5aea20dd7ff21028019606c7c651ab9a313075` | HISTORY |
| 61 | `maintenance/repair-20260806/g3_preflight/g3_0a_usdc_activity.json` | 2415 | `c89ec1d635dcddc31749e83024f86470a9a24d5809b8d8e628a8bf843348a16b` | HISTORY |
| 62 | `maintenance/repair-20260806/g3_preflight/g3_0a_usdc_activity.py` | 4315 | `a8ea85ceea8e6f33083fceac2c8fbab239644eab69bfe85da1a016ec55be08e0` | HISTORY |
| 63 | `maintenance/repair-20260806/g3_preflight/g3_0b_pythia_gpa.json` | 5120 | `faf8d902ee1aa1d52f4a8e6c99084274b90f9d18f37ce9bc4b007d1e1d4023ea` | HISTORY |
| 64 | `maintenance/repair-20260806/g3_preflight/g3_0b_pythia_gpa.py` | 2713 | `5b14d52917a15f4470bf21e6eed68112b601f87950f5057a647a46a0d227e7f6` | HISTORY |
| 65 | `maintenance/repair-20260806/g3_preflight/smoke-20260808/accounting_mode.json` | 1216 | `5fa831ceac129b928c289fef9bada9564c291de4243f067e5926db379b081ff7` | HISTORY |
| 66 | `maintenance/repair-20260806/g3_preflight/smoke-20260808/solana_observation_bundle.json` | 4903 | `1d606ec406a8eb313976a452de7170473c57af780b0b45ba00240c981db205f9` | HISTORY |
| 67 | `maintenance/repair-20260806/g3_preflight/smoke-20260808/supply_truth.json` | 1770 | `67767aa1b3f4c2f0594692a4445d3494063a31cbd3a7a5e326384f9dcb131b37` | HISTORY |
| 68 | `maintenance/repair-20260806/invariant-merge.md` | 9007 | `dff02931fb4e900cb8fcb40af68850ea537cd93a8e0b13db6114fe60a79c23d9` | HISTORY |
| 69 | `maintenance/repair-20260806/ledger.md` | 90675 | `c2de86a3c4195c249bd747577d77366964d3cebf9015af7190230d5a85e07ef4` | HISTORY |
| 70 | `maintenance/repair-20260806/reviews/batch1-review.md` | 23495 | `f5edff2e2f9653d816b3356f86904299225aa147c79b861d97c4c1f4774ce6ea` | HISTORY |
| 71 | `maintenance/repair-20260806/reviews/batch2-rereview.md` | 27888 | `b94a58a77837d0412bfc3a9a93eca2544901a9d8f2cb75ef012eddb77135f805` | HISTORY |
| 72 | `maintenance/repair-20260806/reviews/batch2-review.md` | 33511 | `18f42de7db2dd9876adadfdfc21bdd20c1046f4e6aa653d3c48df197c061c238` | HISTORY |
| 73 | `maintenance/repair-20260806/reviews/batch2-review3.md` | 12002 | `ebfe42c5e9582fae2c9cc838b177c8cb0d42e79c273c5f8d93c25254c612be95` | HISTORY |
| 74 | `maintenance/repair-20260806/reviews/batch3-rereview.md` | 18609 | `9912422e4197e3f5324c7ab7fbbcc62c95d6963136df33f23abf1bb70a60a8da` | HISTORY |
| 75 | `maintenance/repair-20260806/reviews/batch3-review.md` | 31947 | `25cd22ffb712de5f43e3d19b82be5ae4414cf70f56881a56f51497d108413346` | HISTORY |
| 76 | `maintenance/repair-20260806/reviews/batch4-rereview.md` | 9199 | `1275f9d0e43a68e5883d4ce0db0ee042ce12eaa252c90a986311cabf5273df36` | HISTORY |
| 77 | `maintenance/repair-20260806/reviews/batch4-review.md` | 22632 | `3ce4eeeb3aeb04dc846e09695895749c1ccfc0f25c113a66f44b4a9374e08c16` | HISTORY |
| 78 | `maintenance/repair-20260806/reviews/r9-batch1-rereview.md` | 35048 | `03957f5f0295e34ae59b6ba416ba96561c04f163e4a996c8428e3662902d4c0b` | HISTORY |
| 79 | `maintenance/repair-20260806/reviews/r9-batch1-rereview2.md` | 24340 | `5d92a798a34feb8b6a08018f39115f18523877d04f10459c71bbbd9be7ae6cf8` | HISTORY |
| 80 | `maintenance/repair-20260806/reviews/r9-batch1-review.md` | 36607 | `da81e146e8c73cc8cbc81a0124b94ad715a5014b4b18db59b2943f999adfa9cb` | HISTORY |
| 81 | `maintenance/repair-20260806/reviews/r9-batch3-rereview-partial.md` | 4703 | `b2ea0db2a57ff7ff9269522c0348fe66447ae4c2fb218f8a916cffa75d647600` | HISTORY |
| 82 | `maintenance/repair-20260806/reviews/r9-batch3-rereview3-mutants.md` | 3478 | `fce4c1257e741e968f99953d9e5c5a8c0649cc46e8c07d6f0309193664405b33` | HISTORY |
| 83 | `maintenance/repair-20260806/reviews/r9-batch3-review.md` | 23524 | `933a55b19b382a6a6831e636e3e66a08ef1875b5e75045f353ed7b02e25575ff` | HISTORY |
| 84 | `maintenance/repair-20260806/reviews/r9-batch4-rereview.md` | 9678 | `c23039dc04e346c75f62f75c5ef0365e659e9ce5f56659f8f55a60f549b011a7` | HISTORY |
| 85 | `maintenance/repair-20260806/reviews/r9-batch4-rereview2.md` | 20360 | `9cc177025bdb7f1b056aed3aa8ebf990fd8cf5c081f2d0e7bfc4865d559b7003` | HISTORY |
| 86 | `maintenance/repair-20260806/reviews/r9-batch4-review.md` | 6322 | `c2225937680cff73512c4850e4610ea14b080c4e69a3bcd4e1db026087608429` | HISTORY |
| 87 | `maintenance/repair-20260806/robinhood-impact.md` | 8328 | `dbf462b93b2ee9ab9c4f02242ab06a1116c7e35e4c7392be07ceff30f6a2054f` | HISTORY |
| 88 | `maintenance/repair-20260806/sha_replay.py` | 5050 | `00faea5effe16aeb9931d65b8d26cc335be1baa7bdcd378544bb401fb188efe7` | HISTORY |
| 89 | `maintenance/repair-20260806/transport-injections.json` | 10423 | `b72500565d5e8505e71b718b9ebe9cd1b11be00261ce9b16b49dd2433b133824` | HISTORY |
| 90 | `maintenance/repair-20260809-apu-legacy/WORKORDER_apu_legacy_gaps.md` | 7519 | `80f8dd7254f3e79ca053eb4d117fef7b3931a0f4a1b50215434dc292cc8f2c5b` | HISTORY |
| 91 | `maintenance/repair-20260809-apu-legacy/run_all_final.txt` | 9734 | `885598887d3df09b1894a4059deb4e6cd9e170e7edae7bef61ba471aa17090a0` | HISTORY |
| 92 | `maintenance/repair-20260809-supplytruth/WORKLOG_codex.md` | 2341 | `f99c81146f39e3372ce7ccb2e411dfb23b2610cc2c611c34be1b36acc80eea59` | HISTORY |
| 93 | `maintenance/repair-20260809-supplytruth/WORKORDER_supplytruth.md` | 11918 | `5783105c0b40426ea0487bb860951f7e6bf6b5b7ef694e96303367df17c9e2db` | HISTORY |
| 94 | `maintenance/repair-20260809-supplytruth/acceptance_rerun_fable.txt` | 9650 | `8af4fbcc8d103b91c00b6bac8e940669e8ccba9b35d6df1b33cbbaf9d16a7c61` | HISTORY |
| 95 | `maintenance/repair-20260809-supplytruth/red_phase.txt` | 6671 | `932c6d1a57f98747ee06454647779e6c085ed584e489d1026ebf165b45be8907` | HISTORY |
| 96 | `maintenance/repair-20260809-supplytruth/run_all_final.txt` | 9650 | `8af4fbcc8d103b91c00b6bac8e940669e8ccba9b35d6df1b33cbbaf9d16a7c61` | HISTORY |
| 97 | `pyproject.toml` | 1784 | `69041f2f2de037a9edd2f42dad3bb0fc5f1e5b32f534b84990471af30f82c9e8` | CONFIG |
| 98 | `references/address-book.md` | 72734 | `2ceb66def647ce7cad5802a779a0a797c410ae90268b3cb10cd4f6774aaa6120` | LIVE-DOC |
| 99 | `references/analysis-playbook.md` | 6031 | `0ee07ee636347e65af27ac94a79ac875df81d6f51f173cc2b7e53f928e718821` | LIVE-DOC |
| 100 | `references/analyze-workflow.md` | 24674 | `088b355247e58bf4c25708c46b8da3cb9298ba81327fa9c1aa325e8182892f70` | LIVE-DOC |
| 101 | `references/attic.md` | 6335 | `db42c08871f690c7f3b01991085c71a3165545045e5d2bd4aee63c1ef757f214` | LIVE-DOC |
| 102 | `references/casebook/README.md` | 3175 | `43c1135db8671aa7d0e312e0665b6ef6b953a16433a6a1047529f56ed1032aca` | LIVE-DOC |
| 103 | `references/casebook/cex-custody-methods.md` | 5573 | `32b74409a6ac8bd901750de022a6b95359443e4c799640172c02b50ba5ef6160` | LIVE-DOC |
| 104 | `references/casebook/cex-custody.md` | 8612 | `8f02ace907df71acaa477591288b6833e4d215a63bf0b71c399483d4ce09fac5` | LIVE-DOC |
| 105 | `references/casebook/entity-clustering-methods.md` | 20728 | `d3cead0cb0c58e32242c700fe74e5f4e54eadad1b93fa5594b368abbbb8800e9` | LIVE-DOC |
| 106 | `references/casebook/entity-clustering.md` | 13935 | `2dff82ea4ea37e511c242480946f4b2b962f0617d35e393dba37fd9cea4c7892` | LIVE-DOC |
| 107 | `references/casebook/supply-accounting-methods.md` | 1891 | `8e0e8921b6175a9d9ba2350efb651a670aa5ec0e2c0e82a328db658d40d7be66` | LIVE-DOC |
| 108 | `references/casebook/supply-accounting.md` | 17356 | `78661b47ddd7cbdc0402a49b2fe2b03db0bd9491a97697b8a41d767825852e9e` | LIVE-DOC |
| 109 | `references/context-discipline.md` | 6661 | `753e254a51ccaac1e9b0097073ed399e9b0a61b1ff0997bef824c425f6981aa4` | LIVE-DOC |
| 110 | `references/data-pipeline-evm-channels.md` | 45445 | `b549440692bf1f4954b6a94fb98cb9412b34584923d9313b4edc9c9012662214` | LIVE-DOC |
| 111 | `references/data-pipeline-evm-recon.md` | 28012 | `5468a62805416f375a10e94f7eaa664c7fb120a7f6afbbefb7607169fa459cf4` | LIVE-DOC |
| 112 | `references/data-pipeline-evm-sources.md` | 29983 | `18594513328f2424e22927e633ad01f4eca5cac56ba2d8e19c7331f00fc3dbef` | LIVE-DOC |
| 113 | `references/data-pipeline-evm.md` | 2747 | `4f90e2b23622db2bb3e4b75f8e1d2f41aa3a535ad604f25688d0ddb213b96cdb` | LIVE-DOC |
| 114 | `references/data-pipeline-robinhood-channels.md` | 10465 | `03d2ea615c7764e419975fbff4e57c2ede874d8e383e6c67fd6bf81256b3225d` | LIVE-DOC |
| 115 | `references/data-pipeline-robinhood-methods.md` | 8420 | `2021dc72a2d9f116cc105d55851377b3bbd585b7c1fabced9c017d51530359c3` | LIVE-DOC |
| 116 | `references/data-pipeline-robinhood-traps.md` | 20580 | `53b13bf779a7af6466883b0b3199a1af1ee8b524d08ad4b0d14137d899ca55a8` | LIVE-DOC |
| 117 | `references/data-pipeline-robinhood.md` | 3023 | `2482fcbd2b02db6b9c8f501f304b5a390d8507721967c8d6c3f072360c0f9946` | LIVE-DOC |
| 118 | `references/data-pipeline-solana-capture.md` | 30160 | `f4e36791680093f42980e8723e76ac00f66a213fbea4550c51dcd3255629040c` | LIVE-DOC |
| 119 | `references/data-pipeline-solana-scan.md` | 34039 | `222a047a808f791f751b69df398579d569767f1303c08af2f2810e64ee47b9f0` | LIVE-DOC |
| 120 | `references/data-pipeline-solana.md` | 3136 | `c69e0c8e73662cee075ac8c1ea5a284aa939d4c422192e8045d8c1ca9e7c5d23` | LIVE-DOC |
| 121 | `references/economic-control-accounting.md` | 6715 | `46eda5de8bb39892febfde150b2ac592d18a17b13be3b6c545570f3c5078b6b3` | LIVE-DOC |
| 122 | `references/environment.md` | 6803 | `49e7b4c54a1c47ab72fa159909b0c15947903a106427d624a8b3daa27e41611d` | LIVE-DOC |
| 123 | `references/examples/lifecycle-flow-sample.png` | 234681 | `31c2d5e1f2c0177e7d726a5e5af917ff2215b86d0e19aee001ed806a52315745` | DATA |
| 124 | `references/independent-audit-protocol.md` | 13126 | `e568700d3389a762ca7e9ed5ff9a05dfd587806a4d8a352ae5337988ff4eaffd` | LIVE-DOC |
| 125 | `references/labels/MAINTENANCE.md` | 14676 | `8d21f35701f04a03f3e8440db1981332fa19f1a34c1fce3750f1af0b83ec8c3d` | LIVE-DOC |
| 126 | `references/labels/README.md` | 14040 | `168608aced12067ed09a91576f01d755a8203b9b22a4dca367c327eb457e308b` | LIVE-DOC |
| 127 | `references/labels/benchmark/goldset.csv` | 107783 | `9237a17b7cc793e0040ef0d95ab8d404597ffca2a62c54a977d29be167da5a9c` | DATA |
| 128 | `references/labels/benchmark/result-2026-07-16.json` | 1058 | `2b5be5b496a105639fe12d017e452f9ae1a48b266c1a7475f59c26e57b858a1c` | DATA |
| 129 | `references/labels/benchmark/result-2026-07-17.json` | 1496 | `afde6351eafe70c03d1a359ea622c5e711e9603302a8c35da327806f24b85bda` | DATA |
| 130 | `references/labels/benchmark/result-2026-07-18.json` | 1496 | `9c9b88457f893f6ee3f19ad53e22d471ee629efb01e329b6edfcbd83d96aa967` | DATA |
| 131 | `references/labels/codehash-robinhood.csv` | 1040 | `ff4f3c16974fed723f000bcc058f30a4bb2c7b0827f3cfe8d1e29338f05d5b92` | DATA |
| 132 | `references/labels/labels-base.csv` | 2691308 | `72e12e405cc257118e4eb8a0722cde13e84c314b600abd0e95c0d9091ad67365` | DATA |
| 133 | `references/labels/labels-bsc-privacy.csv` | 24659870 | `6900c32f6fadaf13aa48cb0c61a7938fa19488e34d735938452c5ac5912cbcc2` | DATA |
| 134 | `references/labels/labels-bsc.csv` | 3305851 | `2ac3f3e7e7cfd015b4e89da3c33244f458cd7529c7188dba9eaec4faa4b7e670` | DATA |
| 135 | `references/labels/labels-eth-privacy.csv` | 33176897 | `2fc7cc7074d95196301e42990807f138c19c9efb6cd64120ebf4fc4d831150e3` | DATA |
| 136 | `references/labels/labels-eth.csv` | 21563798 | `f3af6001bb02bb0b77fca5cf926ff77f5269061f363ea1a04d74442dda838702` | DATA |
| 137 | `references/labels/labels-robinhood.csv` | 104551 | `edd33770b8787642c84e2edf098a562b9e2e2a765af0bb4d05f72321751690f2` | DATA |
| 138 | `references/labels/labels-sol.csv` | 1541377 | `1d25d5ecfab3c8d48265853e85ee3eb1ae60f060cef35aa7f8dfda298b997ab9` | DATA |
| 139 | `references/labels/manifest.json` | 1251 | `6c05dd9146966a061ffe10e5543437ce3036284659952f0fd5c77fe7ce27df3e` | DATA |
| 140 | `references/labels/miss-queue/base.csv` | 16214 | `bc1777748e50b9532c6e667d685e48cd8337b1d3d64fc8f88a7e4cab90715df9` | DATA |
| 141 | `references/labels/miss-queue/bsc.csv` | 97931 | `e1aa09c9406c16aaf02544daa2a4582ecfebc053782d92ac224ef9f9f351452b` | DATA |
| 142 | `references/labels/miss-queue/eth.csv` | 72240 | `936afefc7c827c0f01caaf83b5d043146a5b1ed34fb02ed72ada5e406bf66322` | DATA |
| 143 | `references/labels/miss-queue/sol.csv` | 4645 | `63c34624eb446d907cd6a36a72297f00f304f40d50ed25e20980fd974a055189` | DATA |
| 144 | `references/lp-fee-accounting.md` | 8143 | `eba4288905a6842ccf38a7bd21aefab8201b6002a90a524d955812532bad4963` | LIVE-DOC |
| 145 | `references/maintenance-review-repair.md` | 16478 | `ca8ab56d40609ba85c555625d6c72f027b5ff4549c53f9172dc675a19d9b9805` | LIVE-DOC |
| 146 | `references/monitoring-package.md` | 15075 | `90891428b989bc0e8f92947c6a3620019f7556134c0af436558b4126828c180c` | LIVE-DOC |
| 147 | `references/playbook-entity-cluster-cost.md` | 6696 | `73b30d013b1cca36c8b70c041eb64a28c4f34fe878418835401be6dc2455ab97` | LIVE-DOC |
| 148 | `references/playbook-entity-cluster-methods.md` | 48026 | `1bf26a57a067ff00cc5dfd2274d68374065fc075b333b6191bbe65fe8ea40831` | LIVE-DOC |
| 149 | `references/playbook-entity-cluster-tiering.md` | 29028 | `b863e3eb039ae5d9bac3500b6c77e700b13981b959a1d5afdeeeb0554ef4f013` | LIVE-DOC |
| 150 | `references/playbook-evidence-wording.md` | 20158 | `ca8eeb75ed5012eab863fa68209318d6b2d96892723fe0aee4fe4626b731f4ca` | LIVE-DOC |
| 151 | `references/playbook-state-anomaly.md` | 44921 | `7993754db4fb127e6a200fbe30470b3cfaf217874511a60e7deb92f979b53ef4` | LIVE-DOC |
| 152 | `references/playbook-supply-recon.md` | 19691 | `d9ac11183a0b83daf1a576e67d048a9ae4a5e19ec3b7afe6a8cf772e83464ca2` | LIVE-DOC |
| 153 | `references/report-template.md` | 38921 | `a8d815dc5b5e670e5bb924daf1b7635a80ab9442b9a0a9351e3ea92f3cdffd95` | LIVE-DOC |
| 154 | `references/research-workflows.md` | 23276 | `236e2d7016d6c198f5b696125cd34e2c637064edb537df36c8f8f57e3117cbc0` | LIVE-DOC |
| 155 | `references/retrospective.md` | 18114 | `69ba3b7448f40b9b3461a1fe0573f3544fca0da4c1f1617f7ef20f2291fe3768` | LIVE-DOC |
| 156 | `references/scan-schemas.md` | 35327 | `9371c9c9c36d413a59c9a04d337127baaf2a924c56e64cf166de579d10004581` | LIVE-DOC |
| 157 | `references/split-run.md` | 18775 | `7334a0e7e8f9b9c38f75cfacf3f071d710f43fe83383411a4e62125216436648` | LIVE-DOC |
| 158 | `requirements.lock` | 1119 | `b098a367e4496226cb898d7232b16a5c4daae6562a4497e4a8723a628caab58a` | CONFIG |
| 159 | `scripts/bench/golden_baseline.py` | 5457 | `edb7e5ff29f1bf5b0948992dc07976215dd88b1cb2302dfbf7ab2f9ca2f5483e` | CODE-6L |
| 160 | `scripts/bench/scan_script_forks.py` | 7156 | `bde941b7965e268a9fbbf6a1f99a3a1236c9241d0a9da4cc01ce58d453e03928` | CODE-6L |
| 161 | `scripts/evm/accounting_gate.py` | 25483 | `38914a1ccc872f234f24bbf0c4bb77db7a4ae845c194c7789e83e809121cc6b4` | CODE-6L |
| 162 | `scripts/evm/analyze_holdings.py` | 13711 | `62d4c5fc1c12affd38aa5284d0b47fa25c526ec971397f15650aa0b28d7eaf05` | CODE-6L |
| 163 | `scripts/evm/cadence_fingerprint.py` | 13995 | `212b9036b563a739cc3951ab7f9c4262e87d61259dd7159142be2355dc9aa96d` | CODE-6L |
| 164 | `scripts/evm/cadence_rank.py` | 10102 | `1c59f83e1ef44d90752b75c26735d2a554941fdf66ea2564d7d1823703e7eaf2` | CODE-6L |
| 165 | `scripts/evm/channels_preflight.py` | 22922 | `992d9bc2201c672ea03927e177cd40b9eca026b6190d02e66a271c943da3a2e6` | CODE-6L |
| 166 | `scripts/evm/cluster.py` | 14586 | `56bad823a8181f37fd1f0e4a25988e0aca5ef00afc294123535c76e47db220a5` | CODE-6L |
| 167 | `scripts/evm/cluster_prep_duck.py` | 10979 | `20156d2a5b0d9a16cc3acfa866e0bc1306ca0a2989378949e614325f275ba70b` | CODE-6L |
| 168 | `scripts/evm/cluster_sensitivity.py` | 29309 | `e825b108bd959d1ef8db9d3c7d0f16fc84da3550a1bdbebc73856e110d0694be` | CODE-6L |
| 169 | `scripts/evm/config.example.json` | 4407 | `e92e65ac33c9f7b8557219f120d4f8a09d6bafeb4fd7920a1de91c8dd57f63b4` | CONFIG |
| 170 | `scripts/evm/csv_collector_receipt.py` | 2499 | `2cca90ee43a52394d3d993ffcd578ea66980e54177884f677fafd562046d589b` | CODE-6L |
| 171 | `scripts/evm/fetch_alchemy.py` | 7130 | `bf8fa1f2e47e3d54c0359e7c191f3217d7cd31a11a0aa55c85be1336d1051164` | CODE-6L |
| 172 | `scripts/evm/fetch_bigquery.py` | 5429 | `20bbc52479c5877ea5add7500759fd836dc49d654aaee5cc5dee309e33f00552` | CODE-6L |
| 173 | `scripts/evm/fetch_etherscan.py` | 3540 | `c9042e30cb14c1d3f5dc8c25f1a021afc91364a94f2037906c3404d27912d0c8` | CODE-6L |
| 174 | `scripts/evm/fetch_gmgn.sh` | 2641 | `7793c1cca67c9b41d2a57053d425adeb1ea5d4fba753742f0c5ff1555195821b` | CODE-6L |
| 175 | `scripts/evm/fetch_hypersync.py` | 12333 | `d8113c590fe78e497364b15089215e82d0b061c413f80bb4600913f334f36b6d` | CODE-6L |
| 176 | `scripts/evm/fetch_hypersync_logs.py` | 6394 | `629d183a7826c2acf0379a4f4be1de8911a37331a8a90317b84a6a479afe3dc4` | CODE-6L |
| 177 | `scripts/evm/fetch_hypersync_v2.py` | 20791 | `d229a1c200554708560f8eab4bed1ccaf378b65cd9fe852d57bcf75b7569fe16` | CODE-6L |
| 178 | `scripts/evm/fetch_pool_swaps.py` | 8074 | `ff98d0465dc2cf8b7bd9950e1be5d4524419021f86ea747230c0e2e059fd400e` | CODE-6L |
| 179 | `scripts/evm/fetch_sqd_evm.py` | 5732 | `042fe44eb1f8aea703f195707d91a9ad89e239ba94414b1dc03c0b837ff55a4b` | CODE-6L |
| 180 | `scripts/evm/lp_positions.py` | 10493 | `534afc66a074e75e11f4549e20b689bda2186cca466478ecaabf424f9e272d48` | CODE-6L |
| 181 | `scripts/evm/make_channel_receipt.py` | 4426 | `d7aa3301b4e8f32150c6460390d5911619d67423d532dbbe5645c80893c3585c` | CODE-6L |
| 182 | `scripts/evm/multicall_balances.py` | 5268 | `9a7a05785b347899891430f58c673a6addc29bd022a26b1ba4d7aad9b5c0921b` | CODE-6L |
| 183 | `scripts/evm/peaks_daily.py` | 11876 | `0a8ceb05548684a5eced403e69a67c4ef50b611a6135b2fdc4cbae55ef6dfae9` | CODE-6L |
| 184 | `scripts/evm/pierce_stake.py` | 7750 | `79aa51519c72e1f489ae071ae05524fc389a630a2b0638ed6a9206fbcb255b83` | CODE-6L |
| 185 | `scripts/evm/prep_cluster_inputs.py` | 1408 | `6aaeb53ce2c8dcce6a0ec44a1c0f8635af1fda9fc2d99d60fc761ec79c22ab3b` | CODE-6L |
| 186 | `scripts/evm/replay_duck.py` | 32271 | `50def969eac162c11808922e41606f3d5d42322db1bfc61272ff32feb4abf2f5` | CODE-6L |
| 187 | `scripts/evm/replay_pass1.py` | 8471 | `2d4e3f2b51c15a6e3af4e39dcccf6f852a00670083618d51407a0a81d979678d` | CODE-6L |
| 188 | `scripts/evm/replay_pass2.py` | 5578 | `6928aadb794c558ca0ffb2e25a3a83a764a10a330dcf5aa226a323ebc40650fb` | CODE-6L |
| 189 | `scripts/evm/replay_stream.py` | 13363 | `70f42cb9e01d12bf5cdda5c21e4c83c8ee13c36ceee07d068c81beb21132482a` | CODE-6L |
| 190 | `scripts/evm/scan_bloxroute_seg.py` | 5115 | `8f32b95a055dc2cb1d60a8974dbdc3b27c26cb62cde9faa2e33851cb57809c05` | CODE-6L |
| 191 | `scripts/evm/scan_transfers.py` | 8689 | `0b08dc4d130c6e990b5c7cdb3da0d6c8cd7447b050dfceb63362fe48a9feef6b` | CODE-6L |
| 192 | `scripts/evm/staged_capture.sh` | 2614 | `2723504d7b9008eb1195fdb9625ac7cbd5d11fa89d1f378e5b163080cd29bced` | CODE-6L |
| 193 | `scripts/evm/transfers_lib.py` | 18144 | `d130fe4be5f6eb2c672a219126c5bf195941dad249c4cadfc80a76499510ed1a` | CODE-6L |
| 194 | `scripts/evm/verify_recon.py` | 8510 | `ca99e0181af104e14a5f8cbf9385dea750d656f8abbefef89eef9a6de6b791df` | CODE-6L |
| 195 | `scripts/hooks/guard_file_ops.py` | 3068 | `830ee92d5ff1b5ea0e0a71e44fce50f0484de67c2821f4458feee6a8851abc7f` | CODE-6L |
| 196 | `scripts/labels/accumulate_offenders.py` | 19664 | `9001e8e36cf636cdc1de66dc068265777da198e6683605d75c3240bceb07cbd3` | CODE-6L |
| 197 | `scripts/labels/add_labels.py` | 10531 | `a6f230bb92265a64c6121e89919ba98b3ea113b849161e88e07fe9f8ea17486c` | CODE-6L |
| 198 | `scripts/labels/benchmark_labels.py` | 7052 | `8d0dc7d17acadf4a264dfdb800eede8a70e787a5ea7290abb9fcee0634a649b1` | CODE-6L |
| 199 | `scripts/labels/build_goldset.py` | 12905 | `17466b7fc52421e5c2c7140ce8621a0670829d4f5b071b9bcc2fc1f24802cc65` | CODE-6L |
| 200 | `scripts/labels/build_labels.py` | 39265 | `4980a49a3969e82163adc74f66c2c4aeae6f791a4b2ea3ced1be06e7a0291e28` | CODE-6L |
| 201 | `scripts/labels/check_manual_sync.py` | 1988 | `4d24ec59055bcc232b5c675eca7387d73ecd7fb0b1c70e4c4d802625a756d0f6` | CODE-6L |
| 202 | `scripts/labels/dune_fetch_results.py` | 1111 | `a4541963bae1aa12abf747f9960975cc136b1ccfe0ecd0aaf03530edd5b019e8` | CODE-6L |
| 203 | `scripts/labels/fingerprint_check.py` | 6063 | `0fe510de21d1ef7f72bf300e2a9fe3d5ccc66cbb1b065d458551dc422ba7ff77` | CODE-6L |
| 204 | `scripts/labels/gatekeeper.py` | 7630 | `5f7460e6550b6e36bc9e93e49e741f47fc448e0791eaab655af2392753774abd` | CODE-6L |
| 205 | `scripts/labels/gen_manual_from_addressbook.py` | 4882 | `bba7af2f679e008bd2cd7abb7bd9880a9c8c43126b635e1976bce70f9ab3b071` | CODE-6L |
| 206 | `scripts/labels/goplus_check.py` | 4777 | `50718264bfe61ef674fe9e3bbd2ce14a4cb7e564b30ba32a1dc331d9477231cf` | CODE-6L |
| 207 | `scripts/labels/label_lookup.py` | 11546 | `99cbe81ef0975c5359c1e42a2c3a13eeaa4bc57d7e0f59ef1e43c6af4c012a35` | CODE-6L |
| 208 | `scripts/labels/labels_resolver.py` | 22187 | `c15d2a15ad81e4b0f273ecbc72abccaba6f29b8af8630bea18c5665b95fe33aa` | CODE-6L |
| 209 | `scripts/labels/probe_codetype.py` | 3698 | `cd15c01f498bfa5e8b5adf64d85b760251607a31740398d84d18b7ddbb4aad7f` | CODE-6L |
| 210 | `scripts/labels/pull_verified_contracts.py` | 4341 | `20d13acbe59292445c47a3a73c614c28261ae8163c2afdbd41ee26a2e79810ef` | CODE-6L |
| 211 | `scripts/labels/risk_flags.py` | 1416 | `b5330dd275fb80cabcbdb471536538110304f0b2489a2aff08728dc635a2aafd` | CODE-6L |
| 212 | `scripts/labels/roundtrip_check.py` | 8743 | `671f5e1573644a19c1d40f073ab085b223ad4b5bfc59a96a8801e37e6fcba673` | CODE-6L |
| 213 | `scripts/labels/sources/additions/base_aa_bundlers.csv` | 10175 | `8f6af01ff840297061e4fa8d3b1af5f00aaa127abc24fea5b2bead0c23c3218e` | DATA |
| 214 | `scripts/labels/sources/additions/base_aa_paymasters.csv` | 4543 | `e4e4ad8f116e2148a766ed205a937c46cb5ac11045037625a1cc0ec88108b5f3` | DATA |
| 215 | `scripts/labels/sources/additions/bsc_bridges_p0.csv` | 6467 | `6240e68b6f8249528414a1d382350197a9f6b56a33d380e6d33195b6b6940526` | DATA |
| 216 | `scripts/labels/sources/additions/bsc_lockers_p0.csv` | 7682 | `147ff2b842c742ed0fa8c43827cad79051b498b508b46cd9579c9624a53b6825` | DATA |
| 217 | `scripts/labels/sources/additions/bsc_routers_p1.csv` | 3814 | `fcd37cd6651b6452fb0ab5c75b56134ca695040000bca6afb096ac83b590834d` | DATA |
| 218 | `scripts/labels/sources/additions/curation_overrides_20260717.csv` | 39176 | `d2b603b07ba4e37d7aa9c06bf464c0ee11600fb42d2fa9fc9bf8d5c23040a50a` | DATA |
| 219 | `scripts/labels/sources/additions/curation_overrides_20260718.csv` | 3824 | `2c8c1c499d2f5544ed83d84303628947ab7d0c42c421c526361d0097feaa806a` | DATA |
| 220 | `scripts/labels/sources/additions/curation_overrides_20260718_asteroid.csv` | 583 | `85eac8b79b06af3bbdbeff85dd8b47e1567ebbb0aace62f98aa1237761447d8e` | DATA |
| 221 | `scripts/labels/sources/additions/curation_overrides_20260722.csv` | 856 | `0d6884d1da7a62233191d871926540a8d5812efac9959791ccb0f107e82f3e52` | DATA |
| 222 | `scripts/labels/sources/additions/curation_overrides_20260724_goat.csv` | 3182 | `ce1331804d8271445a4ae64d500c62a8bbbc5377907f54292621a5999cc5e56c` | DATA |
| 223 | `scripts/labels/sources/additions/curation_overrides_20260724_quq.csv` | 1922 | `e4034d633c7ff4d910e6c89d6088076a9a9dc35e5da9257df8928878acf0d99b` | DATA |
| 224 | `scripts/labels/sources/additions/curation_overrides_20260724_siren.csv` | 1756 | `fb32ddda96afdf0b0e59c194fd3fcf009b2abba4b4eadfd23ba4c6addb2539ee` | DATA |
| 225 | `scripts/labels/sources/additions/recovered_increments_20260717.csv` | 6298 | `c31f60ef40e96db9c97dd6658e395f86679e0a7df0b8653ce7d0ecb5cf997cfc` | DATA |
| 226 | `scripts/labels/sources/additions/safe_family.csv` | 22145 | `0e4489427f89bb571afa10153d406e47d5b0c80cb419ba88a100ed79597ba422` | DATA |
| 227 | `scripts/labels/sources/additions/serial_actors.csv` | 471956 | `e7d7383fdb67f1112a38ea878bd53f5293d9b40638d03b369b07439f1a8c2a4e` | DATA |
| 228 | `scripts/labels/sources/additions/serial_actors_2026-07-22.csv` | 504530 | `5d6768223cb8658a55e961524a13781e6060cd67a242448af0c1666e1ddddd5b` | DATA |
| 229 | `scripts/labels/sources/additions/serial_actors_2026-07-23_from_codex.csv` | 430 | `618923b11dda1ede9b4e827023460e38dd40695b8fc9f04cb377dee9da6bb4e0` | DATA |
| 230 | `scripts/labels/sources/additions/serial_actors_2026-07-24.csv` | 441918 | `1630b42ebedcb5951e558580edaa4319b261fe3a9a53eb581ab8c4840fb0d7f5` | DATA |
| 231 | `scripts/labels/sources/additions/serial_actors_2026-07-25.csv` | 554785 | `03dbe74434e41125a62e606df90b0b9cc74bbeb3f32283607a367e05eb0292fb` | DATA |
| 232 | `scripts/labels/sources/additions/serial_actors_2026-07-26.csv` | 555090 | `4d683233a6052b810c3e9ee912897016ea0485aac6bdfb762cd345768eb2511f` | DATA |
| 233 | `scripts/labels/sources/additions/serial_actors_2026-07-28.csv` | 704194 | `09fd0f01148cdde2e7f839b4dc019044915ff6cfce2b7cb337d2f0deeac9cf7f` | DATA |
| 234 | `scripts/labels/sources/additions/serial_actors_2026-07-29.csv` | 704520 | `1b786796da6106e294fc86a40486053df625b4d1c00563098b459fe0b11bd9ed` | DATA |
| 235 | `scripts/labels/sources/additions/sol_cex_p0.csv` | 5006 | `05dcdc3d38dba18493ccc37781781617356a0d30f5984005dd00632c2250e248` | DATA |
| 236 | `scripts/labels/sources/additions/sol_kr_cex_p0.csv` | 1736 | `673e552f0695a9e37f4ec8f48b16e0f0621eb2e00f81d48b353a0fa624d26f80` | DATA |
| 237 | `scripts/labels/sources/additions/sol_lockers_launchpads_p1.csv` | 1772 | `fa61611782ad815a621ffc51ecff5f41ddcf61efe0f5af7d59eb95809b47fb8a` | DATA |
| 238 | `scripts/labels/sources/additions/solver_intent_p0.csv` | 29748 | `c79d885840e1c9005a438b46049b2a37e7caca132cd3c22627275120f7c59a74` | DATA |
| 239 | `scripts/labels/sources/dune_labels_v2.csv.gz` | 1808240 | `16b8918660680cfeb8cb1bb9e90d97905419b2fcffa9bfb199e8666730167fa2` | DATA |
| 240 | `scripts/labels/sources/dune_tornado.csv.gz` | 7801760 | `712f43ce14167017b6977220ed98398a14416b9efaed46865cfcac5f3d44d71f` | DATA |
| 241 | `scripts/labels/sources/gmgn_additions.csv` | 35996 | `5f556f00070c56f4f061020b48cfbe6fb0db6b3e82e1ed8c0831cba9026e4101` | DATA |
| 242 | `scripts/labels/sources/gmgn_wallets.jsonl` | 49925 | `3417ac87b209c4c4e223f47b9e88b3f2879af636bd1908cb02a63aab57e6ecb5` | DATA |
| 243 | `scripts/labels/sources/hypurrscan_aliases.json` | 29309 | `cd3464b00726411a7bbec714dc3e16ea5a3c209d531720fe8b1c2c32101f30c9` | DATA |
| 244 | `scripts/labels/sources/jup_labels.json` | 5661 | `d7a98379391ae7079ef813b25043deef1b7a16264521b6ebecd914846a0968e5` | DATA |
| 245 | `scripts/labels/sources/kolscan_wallets.json` | 71905 | `41d772e2cb8fbaff88e83fb4b4d7f7e01827bf9144f25c23f3836f04c96e9403` | DATA |
| 246 | `scripts/labels/sources/manual_labels.csv` | 34897 | `88da74759cb35824ca14afe54ca45cb29d98ce7057d26a82ab8783e7d16036cc` | DATA |
| 247 | `scripts/labels/sources/ofac_bsc.txt` | 43 | `b52296adc8fabdcf907f581c90e65848e087cf33bb2b8cd2864ab77cda67f630` | DATA |
| 248 | `scripts/labels/sources/ofac_eth.txt` | 4128 | `473bf23bedfc21b240c8830b0ccb50e7dc1e92bf9a159495b5e864d1710f5c54` | DATA |
| 249 | `scripts/labels/sources/ofac_eth_codetype.json` | 5120 | `28fbb3d979a34996d7dd8ac008d8f5b44bface76b31b18e9fa21d960aef75b2f` | DATA |
| 250 | `scripts/labels/sources/ofac_sol.txt` | 135 | `2813aec9b0c5ca638fb90a9d3620a290dab929ac8204403f367797cf3786bc32` | DATA |
| 251 | `scripts/labels/sources/official_registry.csv` | 14429 | `f11968fe6ee435a8427a081462718e869153931114a3bd6a27e33fcffa2a4f10` | DATA |
| 252 | `scripts/labels/sources/scamsniffer_address.json` | 121442 | `5f5e5fcb1c20015d4a00466dda2ca924b0341bf833fc095d683fe1e80150b012` | DATA |
| 253 | `scripts/labels/sources/scamsniffer_codetype.json` | 134797 | `7c000fb2e5101f0d5ef66d96c2b699136cea7d3ef78ad00cb2a743b3a7d77252` | DATA |
| 254 | `scripts/labels/sources/serial_actors.csv` | 704520 | `1b786796da6106e294fc86a40486053df625b4d1c00563098b459fe0b11bd9ed` | DATA |
| 255 | `scripts/labels/sources/sol_cex_cleanup_20260717.json` | 5023 | `b7922f1d5783d3478ddc6ac20ee4200d49fe0cd4a094b8a5509c8e1402470831` | DATA |
| 256 | `scripts/labels/sources/sol_programs_verified.json` | 4354 | `a200a045770e7a9719b8bb680549be770c986d84fcfa5af6bd420884c7ad589d` | DATA |
| 257 | `scripts/labels/sources/spellbook_cex_addrs.txt` | 213150 | `a9845c1512b6c2ff6706bbaa4c1da3d0cd1038925a57054f7480e610326780c7` | DATA |
| 258 | `scripts/labels/sources/spellbook_cex_codetype_base.json` | 262883 | `7b841a65d001760659e437d2647dc3d52e4f9bc3205a313fd8fc9a5a404c02ad` | DATA |
| 259 | `scripts/labels/sources/spellbook_cex_codetype_bsc.json` | 263213 | `dbbb7f3983d9f9ee40de25093ab4fbf4c2ec75ffc171239e57bb3f9c33b6fa87` | DATA |
| 260 | `scripts/labels/sources/spellbook_cex_codetype_eth.json` | 264708 | `aa0152854219ae93bbac26053d0b9a89836616c53097f75abb04b3ad448e50b2` | DATA |
| 261 | `scripts/labels/sources/spellbook_parsed.csv` | 1597404 | `87fce2339a30e3dce1145997263f355e1fd7a0592f222af1426a01185fa50d27` | DATA |
| 262 | `scripts/labels/sources/tornado_bsc_contracts.csv` | 1488 | `91a1bc48563381524b66a238d0c7a81ef01c3847df698ae1bd61d04d159887be` | DATA |
| 263 | `scripts/labels/sourcify_check.py` | 4951 | `75756faa0d7f1f6889670f44d789f0ad460b5920b810f120f5df84c9bbc85bc0` | CODE-6L |
| 264 | `scripts/labels/validate_labels.py` | 8035 | `f66558b7dfc9d30b8c9fefd590c1b921c69540dde25871fc900b0e92e6457394` | CODE-6L |
| 265 | `scripts/lib/anchor_plan.py` | 12186 | `e5168a455d53bb5163722ea7f2a67c42b20bd3dd8ef6c3ae5e588014842cc1d9` | CODE-6L |
| 266 | `scripts/lib/anchor_selection.py` | 15428 | `fdc7af62143a41748b8b3a0170469ffe5784276322dd2c4d92f6186d214fba85` | CODE-6L |
| 267 | `scripts/lib/artifact_quarantine.py` | 968 | `3d2ef1e4f03a49d6b4b07b699908a810033b04e53c15e4f9ce95f36571be170f` | CODE-6L |
| 268 | `scripts/lib/attestation_adapters.py` | 1723 | `4c5af4b9f5e03c5959b2dbe5244673c052428c5d4fa1134f1810806f0703117d` | CODE-6L |
| 269 | `scripts/lib/chain_registry.py` | 11691 | `8266ab2dbd75e1449ccbc111fe714e71e55426f04ba49738192bb885aec02a55` | CODE-6L |
| 270 | `scripts/lib/endpoint_identity.py` | 3142 | `732958d865a67822dc5a6c1631159bc9a8fcd4ffd5e9fb8be6a172c868a4f730` | CODE-6L |
| 271 | `scripts/lib/formal_capability_probes.py` | 10370 | `d22b1550ec999ec6a438b172385b6495340f3a0c383972d9b8c2e55f69db2fa4` | CODE-6L |
| 272 | `scripts/lib/net.py` | 18552 | `af9d7a94304282efdb29eec56b40ff3d7acbd021cd4a9acda6a665c6d79c3b6f` | CODE-6L |
| 273 | `scripts/lib/receipt_kernel.py` | 20783 | `2b4b039c3610463ce4caaeead552d7b1b0fd77146ac6fa02dd50f99e57df66d3` | CODE-6L |
| 274 | `scripts/lib/receipt_validate.py` | 4554 | `2fbe31e3facabc2420d2eca85d2da451a89c6b906df83fd017e553c684f5f251` | CODE-6L |
| 275 | `scripts/lib/rpc_batch.py` | 5434 | `f993c16ea846945e24c8d403d5962d3d2deae7c6358663b3ac84eb36f817a5a8` | CODE-6L |
| 276 | `scripts/lib/solana_attested_session.py` | 5574 | `59e24d67d90f2dbaf818575e8a78f0f58e3b0204db7de67d7698323801be63b3` | CODE-6L |
| 277 | `scripts/lib/solana_observation.py` | 28074 | `c0f38c0ef12c5c17200632277037f7336a5e29793f63b4136c5a3ba3a5630ead` | CODE-6L |
| 278 | `scripts/lib/solana_sqd_dataset.py` | 2766 | `51bca2c79e1b5dea5fc11b11c5e706402e7e6ae7a64009abef35f94f6720bd0c` | CODE-6L |
| 279 | `scripts/lib/supply_semantics.py` | 819 | `dfef0925ae7d8bc1b99666ef95846d0f7c2cb06b3d11d0c894d2e8bbeddd18d3` | CODE-6L |
| 280 | `scripts/lib/supply_truth_gate.py` | 17609 | `24713f19e13d33f6269272d09d93cfac6aec851231e20d05e176d016f0015fd9` | CODE-6L |
| 281 | `scripts/lib/time_spotcheck.py` | 21687 | `23cf87e23f8c18560fe0e542fe9687e85bf12e663c2db8b82f8b53828e793d55` | CODE-6L |
| 282 | `scripts/prices/llama_price.py` | 5918 | `a0f50dd5adb666f27bbd5c6fcc873722c0eb2ea5bd777ae5556576ccd5badb5e` | CODE-6L |
| 283 | `scripts/prices/price_check.py` | 9768 | `45f7fb2c53350d41108a260aac518992934723cb9220faf2916a27e91a16b089` | CODE-6L |
| 284 | `scripts/proclock.py` | 6788 | `c7b9b8e69215bc87713412cef9213deefe8fd9c360ef969c229f9d3139e76be3` | CODE-6L |
| 285 | `scripts/report/a4_gate.py` | 22796 | `af6cb83a3692785b9528e98f74a03278c470948bc11a5b2b41836dd75b499b7b` | CODE-6L |
| 286 | `scripts/report/a5_report_seal.py` | 9143 | `c6a2ff31d54b3e70cc240da3d850e9b8c66a0d225ab39c7d69d190f603dca118` | CODE-6L |
| 287 | `scripts/report/adjudication_validator.py` | 31244 | `6d340b50ec84d3bdf037e74c2688e7aacbc7ddeaba7e72b54d726e35356df5ce` | CODE-6L |
| 288 | `scripts/report/adversarial_review_runner.py` | 5311 | `c423e62a93922d4b4f8d26ac7e1ea070237be12112674c7227a43ef92dd5576b` | CODE-6L |
| 289 | `scripts/report/audit_release_gate.py` | 39936 | `34bec1945c27e08ed59fd0c11029659fdb03609eef630e4b83e80a39f1d29dab` | CODE-6L |
| 290 | `scripts/report/build_html.py` | 29237 | `87cd8e238592ca1453515ea3fc547c1861d39bf8e15859b6ee538a5524d27f17` | CODE-6L |
| 291 | `scripts/report/chart_style.py` | 2250 | `b2ed3effc720e7623e403bcd2b328995ee0042620d9bbea1d789f936f98d690b` | CODE-6L |
| 292 | `scripts/report/distribution_explanation_check.py` | 9318 | `9f28d91275cd1e889d419e6d7fba683dd5af0c813e2d5fb4efcfd021368042b8` | CODE-6L |
| 293 | `scripts/report/entity_identity_gate.py` | 19499 | `fa864d0d78aa0f2e40aba9d4d8e945d53cd505ad3807b8e3db6421d33d121384` | CODE-6L |
| 294 | `scripts/report/entity_source_trace.py` | 41000 | `ee4243eaf597dc67cf1a18e1aa1130787c9c8650dd734caaafd22c724431787e` | CODE-6L |
| 295 | `scripts/report/facts_gate.py` | 13963 | `f58093f042d0f8fe8c5b3f1744c8204a81a544168d351e77a1c4ee02a6ae3a2d` | CODE-6L |
| 296 | `scripts/report/figures_from_facts.py` | 10404 | `1e21d6b57dd929e360a2eeea295aad3f45c3c2769df2017f154f4e8da456a96d` | CODE-6L |
| 297 | `scripts/report/flow_anomaly_scan.py` | 23833 | `7f13c4fd4cb027ee742fef37e8547e913bac55a655e6950a651c20ed0967c637` | CODE-6L |
| 298 | `scripts/report/handoff_manifest.py` | 59109 | `e24d4123cef0b9554abdd3a01d20e8d12ebf272a4bcc487b64913e203adc986a` | CODE-6L |
| 299 | `scripts/report/holder_distribution_scan.py` | 45689 | `a4d810f0411154d51a220c311517ef8522e1caf73a097ccc370717030b8be926` | CODE-6L |
| 300 | `scripts/report/identity_snapshot_receipt.py` | 11482 | `4a636a88811ad90b465ec9352d6f3a71640d1f5d53e300d738a8d13dfeec79f8` | CODE-6L |
| 301 | `scripts/report/lifecycle_flow.py` | 12276 | `493ae70caa6bb8612d9cbc77f745cbc9bfb1067cdef9dd4d3421e333503982db` | CODE-6L |
| 302 | `scripts/report/md2pdf.py` | 9961 | `6f78e957383c23d5825e8b8d91db9c2f2e790b4e206ed7c929ff585b3176bdd4` | CODE-6L |
| 303 | `scripts/report/migrate_legacy_case.py` | 7848 | `01d73a0b1c06f8a4da04fd4c1d47ad3b24f678fc093dcd6ed51de7a7fb6fbd95` | CODE-6L |
| 304 | `scripts/report/reconciliation_report.py` | 12650 | `c8b0b429252624c20ec0cf123a652c89fb9c013c6f06a8155427ce89af5894d9` | CODE-6L |
| 305 | `scripts/report/reproduce_receipt.py` | 6057 | `753f3afac9324d9ef5c77788f2d9e32cfd93dd6ebc28cc84ac480cbab3cefdaf` | CODE-6L |
| 306 | `scripts/report/retro_draft.py` | 5895 | `ca1caa7b1b508b90788dd9ddfe2ec8feb31fde758f0c1990ca693f8276c1e213` | CODE-6L |
| 307 | `scripts/report/shared_release_receipt.py` | 18480 | `f7031d3d9f715fe31e54fd7616ff29216d5bb34cc2f5a7e1e5c40a1dd170524d` | CODE-6L |
| 308 | `scripts/report/standard_charts.py` | 19970 | `c8ffa96da8919d619d89dcac290dd8601a54a97c58db3f25a41396a9169d8d16` | CODE-6L |
| 309 | `scripts/report/state_from_facts.py` | 5893 | `e8a0667207ab4776391e65f9b61767b12680efb9dfdeb92e047af96632899b09` | CODE-6L |
| 310 | `scripts/report/wave_scan.py` | 40711 | `4d8f999406287c32258c9d834928b5b176ddb2c34b9461489d80550262f6638e` | CODE-6L |
| 311 | `scripts/robinhood/amounts.py` | 670 | `c9c6d10b39affa23873ba5898c6a6a9002232a75148255b65a3e3b0745890b67` | CODE-6L |
| 312 | `scripts/robinhood/build_price.py` | 3844 | `d93bf0f5a7f9e8fb10969c29e97a7d36249f6d9d228118501c288a421500e5c6` | CODE-6L |
| 313 | `scripts/robinhood/config.example.json` | 3074 | `1aa84661c4b7daa7a7380ef10be1b780ff9f78bdc7c7c8f935ed79980d9b7d12` | CONFIG |
| 314 | `scripts/robinhood/cost_engine.py` | 4794 | `7ad85a1baf9e38ddf4c5a1cc9da6a0fb0095116ec9737dd4e6a6dfa814a32c38` | CODE-6L |
| 315 | `scripts/robinhood/gas_trace.py` | 5250 | `60859545aa234b4f256e88756bc51ef12a7702153872e958a7d0fe1662cb17b0` | CODE-6L |
| 316 | `scripts/robinhood/gas_trace_bs.py` | 5792 | `49c6b2628e533e1a221c92eea7dfd2f848f12840cb5008970112132db2b1c509` | CODE-6L |
| 317 | `scripts/robinhood/merge_hs_rpc.py` | 3881 | `6a3950c44ae4fc2f1f48cc48417b0572dfe8a75df2a29f624a8845038333fd8b` | CODE-6L |
| 318 | `scripts/robinhood/pull_block_ts_anchors.py` | 1285 | `c13b15cb386c43684929689d423dfe2c85bd842cd4e0e9fd6765308d9df14d8f` | CODE-6L |
| 319 | `scripts/robinhood/pull_lp_events.py` | 5675 | `f82c4ffbcd0bf014e58d197e6125bba417c74ce6785ac675e5030d42a0a6787e` | CODE-6L |
| 320 | `scripts/robinhood/pull_ohlcv.py` | 2909 | `66fa6e950942eba6959598d525281e479cb76ce7f799c9a4c6b79f4fcdce4e6c` | CODE-6L |
| 321 | `scripts/robinhood/pull_swaps.py` | 4840 | `5ecc0fc16ba30f6b08ce5d43221118eca9a769922870bfef33196d93a89c1166` | CODE-6L |
| 322 | `scripts/robinhood/pull_swaps_v4.py` | 6161 | `407133bca3c598a452803b9125ab7c5852d82526d6345de48e61a27104148d13` | CODE-6L |
| 323 | `scripts/robinhood/pull_transfers.py` | 5368 | `95fb216c98293ba06ac7d41557f141c1c51388df96503ac5f2a81c73c05e29fe` | CODE-6L |
| 324 | `scripts/robinhood/pull_transfers_rpc.py` | 3103 | `51ca6fd4848bb9709dd43795b54fbe5b23c86a4d9b9d7fe3d83a522a29896b6e` | CODE-6L |
| 325 | `scripts/robinhood/pull_weth_pool.py` | 3122 | `8f9dddd926bdeff14968f12b0cf9b06dbba765218d9858fd2ae8645545f7d414` | CODE-6L |
| 326 | `scripts/robinhood/resume_guard.py` | 2238 | `2375138e386ebc33999c9986278dffafcda3695e8b8861af9a83b2c3b6c4fef7` | CODE-6L |
| 327 | `scripts/run_guarded.py` | 9080 | `a407b2344a6775173714ebbcdc623a5fdac3eeefc7c997b56efeb7a28469490a` | CODE-6L |
| 328 | `scripts/solana/README.md` | 2855 | `06d896fed39207e7ff971d745e9af5bcd4d662af050494099f7539c62071ebbf` | LIVE-DOC |
| 329 | `scripts/solana/accounting_gate_sol.py` | 13544 | `b84b6f7666823a584aabb7e6d1d00b2ae1d647bd69ef8d276a3e8baed4b0c28a` | CODE-6L |
| 330 | `scripts/solana/anchor_sampler.py` | 13606 | `bde20f22ca190f24cb74a34d5ffc8ce94e3e236f08d199b9161ce029ab63f3c6` | CODE-6L |
| 331 | `scripts/solana/audit_closed_accounts.py` | 17159 | `a438fc12213811c20009b38d015a6b640d48c65cecc69be8b8b3f3a4bf92ae7a` | CODE-6L |
| 332 | `scripts/solana/build_evolution.py` | 10248 | `700202fa87c239f028c2fc4f9253b1cada84c74b1666826fa97cfca80afad704` | CODE-6L |
| 333 | `scripts/solana/curve_cost.py` | 5965 | `3749ad8458b7cbbbd5dd7a4b8568b6f821e7d9163b926b527ad8cedd8b6faa9c` | CODE-6L |
| 334 | `scripts/solana/decode_txs.py` | 3462 | `d15227be85193b4334088a7eb4ae42a6dbd3fdb1a845f73abdb50e40735db357` | CODE-6L |
| 335 | `scripts/solana/decode_txs_v2.py` | 16962 | `fa5b3ef0e59a5769060c78c11f2cdcad060d98560c0407e7b7357509f18784ab` | CODE-6L |
| 336 | `scripts/solana/fast_probe_tops.py` | 6089 | `8f426097d87b1b625008e48899f32e96c6959415c2bddf590137df20159d783a` | CODE-6L |
| 337 | `scripts/solana/fetch_pool_sigs.py` | 3039 | `e79252dabd974aa3e0dc1fe8f8d451791b7f33dc9c2f22bdd4fcf64656628cb2` | CODE-6L |
| 338 | `scripts/solana/fetch_sqd_transfers_v2.py` | 59442 | `ee78b746a1c61048423a4d350c77f3e098e6665760e22b18d8955a8f37e60caa` | CODE-6L |
| 339 | `scripts/solana/gas_origin.py` | 5626 | `a862ec5b5139765fcb864b9d818998f7e3a08a64bc1942392a0703f8c8b49a8b` | CODE-6L |
| 340 | `scripts/solana/hypersync_recon.py` | 7928 | `c045bf8bcb31aeb1e92d924f9a41efbb3871c8b6d75f2cfbaa44523e3d115e32` | CODE-6L |
| 341 | `scripts/solana/probe_escrows.py` | 6700 | `d781ac10efa62f0ff51b4532ecabab21e84a319890643f330defd6baf35d4325` | CODE-6L |
| 342 | `scripts/solana/probe_window_moves.py` | 7615 | `9ffd167bde956e6259ea02268a746dc36ed5bbf381e7a6e0d3974aceddbf57c0` | CODE-6L |
| 343 | `scripts/solana/replay_edges.py` | 16491 | `244fb7d665c2d41a53b6fb1506f5fdf0544accfa8c49d494f58623ea7ca8cd25` | CODE-6L |
| 344 | `scripts/solana/scan_sharded.py` | 6074 | `37a2eb6fbc9295e6eee340eb513222bb46af22c2bac80769f2ef424a1f99923e` | CODE-6L |
| 345 | `scripts/solana/scan_token_accounts.py` | 15442 | `8405225cf71cb952ad922161932862434866e9076b638c5af933f6c3bbc3094d` | CODE-6L |
| 346 | `scripts/solana/snapshot_diff.py` | 3938 | `394801e25b2cab1a1081afd78f2d712858182d0333e2b0c176de084a1ede96d7` | CODE-6L |
| 347 | `scripts/solana/squads_members.py` | 6631 | `90128bde1e325bb16928de8e85d130ca8ebfda58d23a355badd2bdc3137de34b` | CODE-6L |
| 348 | `scripts/solana/stake_decode.py` | 7328 | `737721f55843d70f9c912f772c707f31758ac2ca45a7b1e8980df2b44c0a60f4` | CODE-6L |
| 349 | `scripts/solana/trace_wallet.py` | 5953 | `ed176d36c76598d663da94bb9c7a85e73bb962fd8354e7243ea3030222caede3` | CODE-6L |
| 350 | `scripts/solana/whale_deep.py` | 8301 | `d428addd0d17c569b18d148e4752c47121f0c50421888aebf1a0ca267af9b27d` | CODE-6L |
| 351 | `scripts/solana/window_fetch.py` | 10846 | `fe3d767545227833cfb469b832d03942198f92a4f97ef0a76cc19c0b1d1a1c2e` | CODE-6L |
| 352 | `scripts/tests/casebook_lint.py` | 3541 | `4d3fa8e54764bb0848b066a596e690acecd4ad9af0448d548466cbe9b8c58d78` | TEST-6L |
| 353 | `scripts/tests/changelog_lint.py` | 3485 | `ff426ca0beef2af935ba57b2fae309f2212619ac1757d955afcf6b5c7c1646bc` | TEST-6L |
| 354 | `scripts/tests/contract_ids_snapshot.json` | 2488 | `c02cc10bc97327ace5cf313897a82d311a93a97088e622c0d4d9036a8ccde006` | CONFIG |
| 355 | `scripts/tests/contract_manifest.json` | 20631 | `6645b0b1c84264565f3124998d9e3058bbc9053301dd86ac87e470480696724a` | CONFIG |
| 356 | `scripts/tests/docs_lint.py` | 22703 | `39be88edfd06771204848647fc401afb2faee17139d76d2660a908f74051b32e` | TEST-6L |
| 357 | `scripts/tests/env_check.py` | 2138 | `88ee0954433ed7c1da26f94d5eb47874a012681339e0b9cb7de8a2d0604751b9` | TEST-6L |
| 358 | `scripts/tests/evm_channel_fixture.py` | 1859 | `978119b5e4aaf86547007ae6c638c43bfa5da73ec49448fe36fff22ebbc02a11` | TEST-6L |
| 359 | `scripts/tests/fixtures/pythia_anchors.json` | 7291 | `55055a93269f5c7947b263fdd77786d112e94ff1440f971529569484941425d9` | CONFIG |
| 360 | `scripts/tests/fixtures_lint.py` | 4886 | `6ea338e9f029946526c787fc6e2603c2ba6fb325b7140f53993903c8a7a5bb34` | TEST-6L |
| 361 | `scripts/tests/formal_ready_test_harness.py` | 2749 | `27a1588937c07c732faaeb0a2f164c0bc74f7f59de74fea30da757e663fc1075` | TEST-6L |
| 362 | `scripts/tests/identity_gate_fixture.py` | 2996 | `6dd5cf4d1cd13379c30de752f0ee64ab5223b7958fffd08e854006b32fe98255` | TEST-6L |
| 363 | `scripts/tests/invariant_manifest.json` | 23116 | `e5edc66f8e214d5a23fa9dc87bbc9f06917c55149a25c4c3a5640d695f00a6ae` | CONFIG |
| 364 | `scripts/tests/invariant_scan.py` | 58006 | `48f075c29ad1b3063b990328975a8390d60795b3923d152e043219e91e2b139b` | TEST-6L |
| 365 | `scripts/tests/labels_manifest.py` | 3111 | `e476feb099a1cf7eb5f29c9005e0ca417aae8e4b30f1388c7f9ac1c04e16b0ee` | TEST-6L |
| 366 | `scripts/tests/run_all.py` | 5009 | `5870d69b41327a7dbf74431c10f13cfc3e6b8b477b122c8056eff877c570e8f7` | TEST-6L |
| 367 | `scripts/tests/runtime_docs_manifest.json` | 4113 | `4d2b22d49fe241419600b4ed9c4889a8602cb874e78ca598e949cd452dd215b5` | CONFIG |
| 368 | `scripts/tests/test_a4_gate.py` | 24065 | `335dca133bb52340ac9b9bad2792374f1f90c4b5970d63d6fb6d1afbf37a9904` | TEST-6L |
| 369 | `scripts/tests/test_add_labels_rollback.py` | 6580 | `9838064d41a601b7c5cb4c86ab349a3db5eb072821f8c3f0b59f81ac9292fb34` | TEST-6L |
| 370 | `scripts/tests/test_adjudication_validator.py` | 16840 | `a0e4cb13c14ca65e92cd3e5d00d586ec7ab01689c24d3dca7e37f30c6d73c5cc` | TEST-6L |
| 371 | `scripts/tests/test_apu_legacy_gaps.py` | 20263 | `9e092dae9db42d0894718dc50b769b5974d03fc4bfaab3ae02d6f20513bcbf02` | TEST-6L |
| 372 | `scripts/tests/test_audit_release_gate.py` | 31990 | `69c4b657e56bdc4254e957540df647bc902696542dff77680c6acbffb4a0959f` | TEST-6L |
| 373 | `scripts/tests/test_batch1_receipt_paths.py` | 5345 | `404e332a04e0a99eced8d70f4d08ae76fa77928836c67605bd3b932a7d8ba765` | TEST-6L |
| 374 | `scripts/tests/test_batch1_risk_flags.py` | 4298 | `3075ebc169009758f4cbb910e5f7c3e9778a855934e7b6ae08c034e51b88bcfa` | TEST-6L |
| 375 | `scripts/tests/test_batch1_rpc_attestation.py` | 13653 | `e93180407f80eeda5ad8e82389edc49875610cb2e7b82b213f5151f9ff1fcd31` | TEST-6L |
| 376 | `scripts/tests/test_batch2_capability_matrix.py` | 3904 | `ebcd3d6342ad849273e4033d3cdc0937fa942db0c4d05d7c1b8b3c1a9f619795` | TEST-6L |
| 377 | `scripts/tests/test_batch2_legacy_hardening.py` | 7752 | `cdb6ed90d63e92c1cdb4cfd81683f8cdcb476916d173e4bc959fa2b7b10314b5` | TEST-6L |
| 378 | `scripts/tests/test_batch2_p3_hardening.py` | 2346 | `8761459b77831a6116a5622d1996bd0e00672f98d2f31f18ec051e3136f3e9e5` | TEST-6L |
| 379 | `scripts/tests/test_batch2_ready_reconciliation.py` | 903 | `4f74abc8cae2dc5287d9c9b91e2605e070d8cc05114b68ec89da000536a2a904` | TEST-6L |
| 380 | `scripts/tests/test_batch2_registry_harness_hardening.py` | 4741 | `4960a10fc1dab392e46f4b36e18451f37a98924a510bcb28e80254dabdb49c4d` | TEST-6L |
| 381 | `scripts/tests/test_batch2_robinhood_exploration.py` | 5892 | `8ea28527a7efcb6dc18bbe26adbb70fb4accb3556fa5c87cdeec3f0d7b352ce0` | TEST-6L |
| 382 | `scripts/tests/test_batch3_evm_vertical_slice.py` | 15083 | `e8851480f8880a3abea40c8379aa6f729189bb66b8a432d0499438c3a55fe563` | TEST-6L |
| 383 | `scripts/tests/test_batch3_solana_producers.py` | 14473 | `4e2536455c809d925ea20d2382bcf4edfc8987d0d6da2e143b51af8139efd3d6` | TEST-6L |
| 384 | `scripts/tests/test_batch3_solana_vertical_slice.py` | 11888 | `fc4d3726390f342fad0ecbf6247e59b66aa64a8db58e546ec974b88baaa4c552` | TEST-6L |
| 385 | `scripts/tests/test_batch4_invariant_guards.py` | 23650 | `70b05c4329c0d7ef11b3ca80197203f8576de82666f4aedce195b984cb2c484d` | TEST-6L |
| 386 | `scripts/tests/test_benchmark_labels.py` | 3090 | `62a57ac93167cc011341f3abf7f8dabb39a09f4d401a123d3659a071ba5f0531` | TEST-6L |
| 387 | `scripts/tests/test_build_html.py` | 5577 | `e2a52366b6db56ece97ad47c7b4f7b11720d9da1618eaed52bdcdaf371054ad2` | TEST-6L |
| 388 | `scripts/tests/test_chain_registry.py` | 5831 | `eb8da61d2cc981a91a5a4109721938d316d8cd4f134ccc48108a3e1558460e53` | TEST-6L |
| 389 | `scripts/tests/test_chain_support_matrix.py` | 4456 | `4eb359d766468dde458937d3c09959f5e9d73760d628b519b13c16e8d7a31c9f` | TEST-6L |
| 390 | `scripts/tests/test_cluster_quality.py` | 11320 | `8fe4ba92e220fb1f8a3d7baf9be2ac0f0795f41f9f354b5537b0e20df73e42c7` | TEST-6L |
| 391 | `scripts/tests/test_commands_deploy_sync.py` | 3212 | `d6cb6e405d2ba975f24534df66a489c16d58a3ecc45e6486bfcfd943d504f3e5` | TEST-6L |
| 392 | `scripts/tests/test_contract_routes.py` | 8458 | `a0697ac1db0afcb43ce3873532c21b462a59adf9cde44867235a58ab3cc69020` | TEST-6L |
| 393 | `scripts/tests/test_distribution_gate.py` | 26863 | `9c74d226d5b62592652524121724eefa760b006fefb9989804d9dcf766843f3c` | TEST-6L |
| 394 | `scripts/tests/test_engine_equivalence.py` | 5812 | `a2bc29c22bf88ad68dbf59e862470c314b3e6d84fe06d979b2e13438042ea9cd` | TEST-6L |
| 395 | `scripts/tests/test_entity_identity_gate.py` | 2763 | `49502e8359dc3e3cb502cffd331afbb8305752d40b604ad656d0f079aff5f7f7` | TEST-6L |
| 396 | `scripts/tests/test_entity_source_trace.py` | 12763 | `e10901b052b856d20a8d63405fd77d33f29fc815516c8465eea3a2b1450f2042` | TEST-6L |
| 397 | `scripts/tests/test_exemption_guards.py` | 3974 | `2ad6c3a571f23835c080c2a723b075a1d1f8f8162fcd09f1540e77cc1b984860` | TEST-6L |
| 398 | `scripts/tests/test_fault_injection.py` | 11929 | `27427aeaecf7df90eb3889686b360c5599799b337227889e5c3d8f378d4786b8` | TEST-6L |
| 399 | `scripts/tests/test_fetch_failclosed.py` | 9320 | `bf96ed91ec989359f181e530aefca1696d7dbd3d75c0f2a7ff711b7e6a316b01` | TEST-6L |
| 400 | `scripts/tests/test_fetch_gmgn_sh.py` | 3104 | `2268e8a47abb63204888765162a0f536fdd5fecd4643af8d0bc4b7920ed93f76` | TEST-6L |
| 401 | `scripts/tests/test_figures_from_facts.py` | 5180 | `aa1a8c904328adb5bb0bf12c9506e65530e5894e8a84780284717d3f6fae5252` | TEST-6L |
| 402 | `scripts/tests/test_flow_anomaly.py` | 15334 | `b32c9648a1dc07fd738b999f74d1d31f084ab721f6a99d24f948d5850bd97c3b` | TEST-6L |
| 403 | `scripts/tests/test_formal_chain_support.py` | 4116 | `2538901ca35c9771984f3a15d29e93bd50502791a42adf5a35dc913b9dad4166` | TEST-6L |
| 404 | `scripts/tests/test_handoff_manifest.py` | 38649 | `ea0562c6bf6776fa3aa34160dd39356df023315736f76e005968ea1e43179785` | TEST-6L |
| 405 | `scripts/tests/test_labels_resolver_guards.py` | 1099 | `6db978c59ffefe88572c4c9ab25142080d46ef5a95734866252665d74f34a3c5` | TEST-6L |
| 406 | `scripts/tests/test_net_result.py` | 1862 | `1ab20226acbac2381a82d04916a33b430f010e2330a74d41c66663dbc561b0cd` | TEST-6L |
| 407 | `scripts/tests/test_param_scripts.py` | 3697 | `9a405c05020bff0266115ab42b28e2ca6a84e33219be6a97be972df2a2a490a5` | TEST-6L |
| 408 | `scripts/tests/test_peaks_daily.py` | 6172 | `d7a5cbe905f3a339b996aa7e23b1a05f1f4a3bdf7e09466616977d434a09b8d6` | TEST-6L |
| 409 | `scripts/tests/test_r7_findings.py` | 23378 | `1526aaf807a6c5296e4957644f010553bab3e470de3807071f3a199832e43fb9` | TEST-6L |
| 410 | `scripts/tests/test_r9_batch1_boundaries.py` | 15159 | `068de96919b873ee7d96e23815216b1e022484fd4a8a051f4922553d1ad4b2ca` | TEST-6L |
| 411 | `scripts/tests/test_r9_batch2_attestation_adapters.py` | 3573 | `38fc8c3648a9b8cfbd92bccef3e50ace86a1de1de1d45810fc1349726d6abe69` | TEST-6L |
| 412 | `scripts/tests/test_r9_batch2_executable_capabilities.py` | 5684 | `0021524a8133fbf01b2af175e52534982599317bc9316cdb02eec261056749d6` | TEST-6L |
| 413 | `scripts/tests/test_r9_batch2_solana_sqd_adapter.py` | 4122 | `cee06bcfff5d39d8e511c32a379b9311827b24bb42d77ab122b5896a38314f87` | TEST-6L |
| 414 | `scripts/tests/test_r9_batch3_dynamic_runner.py` | 3560 | `6e65f08260dace69861863bc3fdd91d24bf2ad02d7e594bddf52b10bafa7345a` | TEST-6L |
| 415 | `scripts/tests/test_r9_batch3_preflight.py` | 2945 | `f407c1d10713c67859e251e65b267eb9cadd1acfafdcc08462f46189e4587f56` | TEST-6L |
| 416 | `scripts/tests/test_r9_batch3_release_guards.py` | 7468 | `d02311021242878f80b877ad16e8f946b5f38718bee7d838ced92b5038883e09` | TEST-6L |
| 417 | `scripts/tests/test_r9_batch3_solana_observation.py` | 25036 | `b167e8df3e586530bfa3dbd70b84cb0b1217ed12489b0d8512aaf76ae1ae6fc2` | TEST-6L |
| 418 | `scripts/tests/test_r9_solana_attested_session.py` | 9508 | `fad8d94c0d028c34b410106a18b15859ece4cf328ae276fecefed95acea4b926` | TEST-6L |
| 419 | `scripts/tests/test_receipt_kernel.py` | 10177 | `9fb6a7296c73f02707cba9606089273ced7f700264d66e55f86c7150d70e2128` | TEST-6L |
| 420 | `scripts/tests/test_reconciliation_runner.py` | 6695 | `05ccbfe9a1c1499c7f2b6170cbeaebdbeb4f75751d2f9f4607fe0ce20e1e1771` | TEST-6L |
| 421 | `scripts/tests/test_report_facts.py` | 5555 | `e1bbced3f321b9ecf1ee5f3977ca27d8914bdb1126af5fd4a6a3fa55c649bffc` | TEST-6L |
| 422 | `scripts/tests/test_review_20260804_p0.py` | 8393 | `096c0f92927030967b62e9ec6520753b46ffa8073af58d7b9d13908d9b3c347a` | TEST-6L |
| 423 | `scripts/tests/test_review_20260804_p101.py` | 3171 | `de63967ff91fa05465c5fce628e7638328e637456729c63de38e3231e727bac4` | TEST-6L |
| 424 | `scripts/tests/test_review_20260804_p104.py` | 2649 | `21b8a6e1d0040467fb8ef4d2bb6c55bda75a1674c3ed3f0f2599e7e74647a320` | TEST-6L |
| 425 | `scripts/tests/test_review_20260804_p105.py` | 4688 | `66d65afddebabf2cbdbfcb2ee41cc5e35f085ee53fc91ac8f32324ddcfbda98d` | TEST-6L |
| 426 | `scripts/tests/test_review_20260804_p106.py` | 3079 | `72e11ce33b8f2501aa0207bc70699f3768246f585e153cebc4f7b5cbbda200bd` | TEST-6L |
| 427 | `scripts/tests/test_review_20260804_p201.py` | 2748 | `157c2af6aac46777b9972862a22d067645f86bbe304a6391e2f2b10fe9b463a4` | TEST-6L |
| 428 | `scripts/tests/test_review_20260804_p202.py` | 2194 | `adafcbae70abfe88127210ab83a42d093e63da32e0b99926a37e66fb4049c928` | TEST-6L |
| 429 | `scripts/tests/test_review_chain_collectors.py` | 1392 | `d7e32c337c2432d7281329c481765b21a6c6057ea9d2dd674e537022caac6361` | TEST-6L |
| 430 | `scripts/tests/test_review_evm_integrity.py` | 4273 | `63c85101f66250411bb3f226d71cdd4dd330cb2f6b9bd15e33ee5b9ffef3c317` | TEST-6L |
| 431 | `scripts/tests/test_review_labels.py` | 1475 | `34f7ea46e49e4bb92a9877091573921f67d01ac18d386b93982f27a6995f2932` | TEST-6L |
| 432 | `scripts/tests/test_review_resume_integrity.py` | 11035 | `12778d9395524f3cf3f6aac6289572e0a6a7d15fdd08a79152382c3a347c67ec` | TEST-6L |
| 433 | `scripts/tests/test_review_robinhood_integrity.py` | 1794 | `75674e1fdf39845e0f5ae3808bd5e41d80c0f62bf7c5e9e3a2c6b76e19b029b3` | TEST-6L |
| 434 | `scripts/tests/test_review_scale_guards.py` | 3438 | `6f107ee2e183d454250a43afadd91208f19304a266cbca23411a72032b556e20` | TEST-6L |
| 435 | `scripts/tests/test_review_solana_integrity.py` | 6580 | `4ea9ac3355195f42c1be0b1ea95b46cad1a14640eef0e57aea0e1e8b52d8cc05` | TEST-6L |
| 436 | `scripts/tests/test_round4_a5_seal.py` | 2424 | `ed936bf02f885c55e8e06abfc3b2bd5a67fa9edf95ae1d3eb8479d41a2e37bb3` | TEST-6L |
| 437 | `scripts/tests/test_round4_csv_adapters.py` | 1518 | `68a81d853137aa04a67ca51a042b816fdd8ab3c33310cbddbfb0461b9baed2b2` | TEST-6L |
| 438 | `scripts/tests/test_round4_identity_emitter.py` | 4000 | `88c1674787c23fb909269d287e12db4ab50ae848350a593b94edaad863f78c28` | TEST-6L |
| 439 | `scripts/tests/test_round4b_provenance.py` | 5848 | `d1e12282f8cf6cf982b067665a832e04af425679bba1b463db0eb3fafd7d079e` | TEST-6L |
| 440 | `scripts/tests/test_round4c_solana_provenance.py` | 6703 | `750d440545f1463b159d52636e2db9e86cd56805ce493e902e8cb82176731a36` | TEST-6L |
| 441 | `scripts/tests/test_roundtrip_check.py` | 5468 | `d954f2ab932294264fe440ccad009484fddea8821d047fb555e0596f400b58c0` | TEST-6L |
| 442 | `scripts/tests/test_sixlens_docs.py` | 5399 | `749bd1fd7311d07679c529fa332a03adc8d599db900fd6ec484199d5ed656647` | TEST-6L |
| 443 | `scripts/tests/test_sixlens_receipts.py` | 13337 | `1eb60ca8b7a14ee4208503004b3b0d3184288c17f952de192565884b1220e953` | TEST-6L |
| 444 | `scripts/tests/test_sqd_merge_equiv.py` | 10548 | `88c949006ccde7fcc2d15d59069b10761d767e4830dfe31e9807f9ae9e55bdd4` | TEST-6L |
| 445 | `scripts/tests/test_state_from_facts.py` | 1893 | `e762225438369ecb7b4e61c155a9189616a363412643e7d2c2e26fd509cac230` | TEST-6L |
| 446 | `scripts/tests/test_supply_truth_gate.py` | 11539 | `c0818b3a984237989f97ea74a309bdb53cf85da50e2092e786bfa0bccaf63cd9` | TEST-6L |
| 447 | `scripts/tests/test_time_spotcheck.py` | 16728 | `7986ca7bdbbc341a9876649fb5897f56e789a2735fdc839be4f9d247a53996e5` | TEST-6L |
| 448 | `scripts/tests/test_token_no_positional.py` | 2581 | `4e548d9d77a9e89d7e0aa594d364ade88b195fc82d66ff0fd11d5c062bae2515` | TEST-6L |
| 449 | `scripts/tests/test_version_consistency.py` | 1217 | `ab7c81c054a2c6a475692e2cd726d3c3cd916140ae6ce8d7c9f4cc17b756fc3b` | TEST-6L |
| 450 | `scripts/tests/test_wave_scan.py` | 10448 | `7b1ca665bf1cc67c869d2f7098bdcdffc4da8a45d8ead627ec844094f18aa203` | TEST-6L |
