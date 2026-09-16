# 工单 R2：口径漂移与文档-代码不符修复（盲审 R2 消化）v2

v2 变更（消化 `review_wo2_reply.md` 退回 4 条）：D1/D2/D5 改用更短措辞（字节净减）；D3 整行替换并补 :30 路径；D7 补 :70–80 下载块 cwd；§0.2 明确守卫脚本可运行。

内容基线：`445d7acf996c287b78250bb7c8a64614ecf13c36`（VERSION 7.1.1；R1 施工已落地于 01296ab）。来源：`blind_r2_report.md` 8 条（Fable 逐条亲核属实）＋待确认转正 F2。
本工单**只改文本**。无新增需改代码项（`code_change_pending.md` 仍只有 D1）。

## §0 施工纪律（同工单 R1 §0，此处只列差异）
0.1 开工先确认 `git status --short` 为空并记录施工 HEAD；`git diff --stat 445d7ac HEAD -- SKILL.md references scripts commands-staging VERSION` 须为空，不符即停工汇报。
0.2 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`——这只约束**你的主动读取**（统计字节用 `stat -f %z` 逐文件，不用 `cat` 通配）；**运行 §1.2 守卫脚本属被测代码既有行为，允许并要求原样运行**（它们内部遍历 attic/archive 不算你读）。
0.3 **白名单**：`references/lp-fee-accounting.md`、`references/retrospective.md`、`references/data-pipeline-robinhood-channels.md`、`references/independent-audit-protocol.md`、`references/scan-schemas.md`、`references/labels/MAINTENANCE.md`、`references/playbook-state-anomaly.md`、`references/monitoring-package.md`，以及新建报告 `maintenance/repair-20260916-drift-audit/r2_done.md`。
0.4 删除 > 修改 > 新增；不新增章节/条目/文件；锚文本先 `grep -n -F` 核验恰 1 处且行号一致，同文件从后向前替换；不符即停工。只动指定片段。
0.5 不 commit；不改 `scripts/`、不改 `contract_manifest.json`；撞 needle 即停工汇报。

## §1 硬约束
1.1 字节：`SKILL.md` = 8021 不变；references 三组 glob（`references/*.md references/casebook/*.md references/labels/*.md`）合计 ≤ 929850（基线，须净减或持平；复核内存模拟为 929831；统计用 `stat -f %z` 逐文件求和）；`commands-staging/*.md` = 8798 不变。
1.2 守卫全绿（同 R1 §1.2 七条＋`--all`），输出贴进 r2_done.md。
1.3 `git diff --stat` 只含白名单。

## §2 逐条施工（锚＝改前原文片段）

### D1 V4 手续费公式把输出腿当输入腿
`references/lp-fee-accounting.md:62`。锚：`gross_input_j = 正数一侧的 amount0 或 amount1` → `gross_input_j = 经同 tx Transfer 校准的输入腿负值绝对值（data-pipeline-robinhood-traps 第 12 条）`

### D2 "本案回灌"命令实际跨案批扫
`references/retrospective.md:102`。锚：`——本案庄家实体回灌惯犯库（appendix.json / analysis-state.json 为扫描源，筛查不买入的案子复盘时同样回灌；含 manifest 自动落印）` → `——跨案回灌惯犯库（扫描 `DEFAULT_ROOT` 或所传案根父目录；每案优先 appendix.json，否则 analysis-state.json；跨案合并并自动落印）`

### D3 报价小时线格式与消费者归属
`references/data-pipeline-robinhood-channels.md`
- :34 整行替换（保留两个前导空格）。锚（行首）：`  ⚠️ 依赖 `data/ethusdt_1h.json` 为 **list 格式**` → `  cost_engine 的 `data/quote_usd_hour.json` 为 `[[ts,o,h,l,c],...]`；`data/ethusdt_1h.json` 属 build_price 输入，列为 `[[ts,close],...]`；pull_lp_events 不读小时线。`
- :30 锚：`+ transit_contracts.json；config 可选 fee_distributor。` → `+ data/transit_contracts.json；config 可选 fee_distributor。`（cost_engine.py:25 读 `data/transit_contracts.json`）

### D4 复现命令的控制器选项被转给子脚本
`references/independent-audit-protocol.md:105-106`。锚（105）：`python3 scripts/report/reproduce_receipt.py <案目录> \`；锚（106）：`  --output reproduce_output.json --receipt reproduce_receipt.json`。两行合并为一行：`python3 scripts/report/reproduce_receipt.py <案目录>`（两项与默认值相同；案目录之后的词会被 `script_args` 原样转给 reproduce_audit.py，故删除）

### D5 "公共字段各产物一律在场"不符分布扫描
`references/scan-schemas.md:17`。锚：`各产物一律在场，下文不再逐一重复` → `仅 wave-scan／flow-anomaly 保证齐全，其他产物见各自 schema`

### D6 LP 采集池配置读取行为相反
`references/data-pipeline-robinhood-channels.md:33`。锚：`**不读 config.json 的池子配置**，必须命令行传参 `--from-block N --pools 0x主池 --out data/lp_events.jsonl`（漏传 --from-block 直接 usage 报错、串行链会被短路）` → `**`--from-block N` 必传**（漏传直接 usage 报错、串行链会被短路）；`--pools` 可省略则取 config.pools（CLI 优先）；`--out` 默认 data/lp_events.json`

### D7 标签维护示例 cwd 连续性
`references/labels/MAINTENANCE.md`
- :86 锚：`cd sources && python3 ../add_labels.py my_additions.csv` → `(cd sources && python3 ../add_labels.py my_additions.csv)`（行尾注释不动）
- :87 锚：`python3 ../accumulate_offenders.py && cd sources && python3 ../add_labels.py serial_actors.csv` → `python3 accumulate_offenders.py && (cd sources && python3 ../add_labels.py serial_actors.csv)`
- :70–80 下载块（页首约定在 `scripts/labels/` 执行，但块内 `../probe_codetype.py` 与下载落点都按 sources/ 写）：在 :70 锚 `P="${CHIP_PROXY:?请先设置 CHIP_PROXY}"` 所在行之前插入一行 `(cd sources || exit`；在 :80 锚 `ETH_RPC="https://ethereum-rpc.publicnode.com" python3 ../probe_codetype.py scamsniffer_address.json scamsniffer_codetype.json` 所在行之后插入一行 `)`。:70–80 原内容不动。改后用 `zsh -n` 检查该代码块可解析。

### D8 CEX 封闭盘识别三角引用节号
`references/playbook-state-anomaly.md:36`。锚：`data-pipeline-evm-sources §6 表` → `data-pipeline-evm-sources §4 表`

### F2 监控包把探索档 robinhood 列为"正式枚举"（待确认转正；chain_registry robinhood release_tier=exploration）
`references/monitoring-package.md:43`。锚：`**chain** 小写正式枚举：bsc / eth / base / sol / robinhood。` → `**chain** 小写枚举：bsc / eth / base / sol / robinhood（robinhood 为探索档）。`

## §3 完成报告 `r2_done.md` 必含
①逐条改前→改后 diff；②§1.1 字节实测；③§1.2 原始输出；④`git diff --stat`；⑤差异/停工点；⑥禁读披露。
