# 工单 R2：v9.0.1 口径漂移与文档-代码不符 3 条纯文本修复 v2

内容基线：`07c97d6`（R1 施工落地后的内容态；施工 HEAD 可含 maintenance/ 提交，但 §0.1 差异校验须为空）。来源：盲审 R2a 2 条（`blind_r2a_report.md` D1/D2）＋ Fable 补报 1 条（R2a 首派因配额中断前抛出的线索，Fable 亲核属实；R2b 报 0 条）。本单全部为纯文本修复，零代码改动；v2 采纳 codex 复核 r1（`review_wo2_reply.md`）非阻断精简建议：D1b 改为仅保留指针 `见 §3.5`（§3.5 已含禁止改源码要求）；**所有锚与替换文本均为代码块内整行片段，不含首尾空白**。

## §0 施工纪律
0.1 开工先确认 `git status --short` 为空并记录施工 HEAD；`git diff --stat 07c97d6 HEAD -- SKILL.md references scripts commands-staging VERSION CHANGELOG.md` 须为空，不符即停工汇报。
0.2 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）、`archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`（§1.1 统计字节时 attic.md 只计大小不读内容；守卫脚本自身遍历文档属被测代码既有行为，允许并要求原样运行）；`maintenance/` 下只读本工程目录。
0.3 **白名单**：`references/data-pipeline-evm-channels.md`、`references/data-pipeline-evm-sources.md`、`references/playbook-evidence-wording.md`、`references/analyze-workflow.md`，以及新建 `maintenance/repair-20260919-drift-audit2/r2_done.md`。
0.4 删除 > 修改 > 新增；每处锚先 `grep -n -F` 核验恰 1 处且行号一致；不符停工；只动指定片段，锚外一字不动。
0.5 不 commit、不 push、不部署；不改 `scripts/`、`commands-staging/`、`CHANGELOG.md`、两份 manifest。

## §1 硬约束
1.1 字节：`SKILL.md` = 8021、`commands-staging/*.md` 合计 = 8789 不变；references 三组 glob（`references/*.md references/casebook/*.md references/labels/*.md`）合计 ≤ 930160（基线 930145；Fable 本机按四处替换逐字模拟净减 66 B → 930079（复核 r1 独立重算一致），实测数写入报告）。
1.2 守卫全绿：`python3 scripts/tests/docs_lint.py`、`docs_lint.py --all`、`casebook_lint.py`、`changelog_lint.py`、`test_contract_routes.py`、`test_sixlens_docs.py`、`test_g3_docs_guards.py`、`test_version_consistency.py`、`test_commands_deploy_sync.py`，原始输出贴进 r2_done.md。
1.3 `git diff --stat` 只含 §0.3 白名单。

## §2 逐条施工（锚均已由 Fable `grep -c -F` 验为恰 1 处）

### D1（R2a D1）Multicall3 跨链示例漏 `--chain`，两处
D1a `references/data-pipeline-evm-channels.md:219`。锚：
```
[--rpc URL ...]`。默认 4 个公共节点仅适用于 BSC；跨链必须显式传对应链的 `--rpc`，禁止改源码注入标的。
```
→
```
[--chain <链> --rpc URL ...]`。默认 4 个公共节点仅适用于 BSC；跨链必须显式传对应链的 `--chain` 与 `--rpc`，禁止改源码注入标的。
```
D1b `references/data-pipeline-evm-sources.md:28`（删除重复且不全的参数说明，保留 §3.5 指针）。锚：
```
见 §3.5；用 `--token/--input/--out` 注入本案参数，非 BSC 链另显式传 `--rpc`，禁止改源码注入标的
```
→
```
见 §3.5
```
依据 `scripts/evm/multicall_balances.py:90-92`（`--chain` 默认 `bsc`）、`:107-112`（按 `args.chain` 做 RPC chain id attest，不匹配退出 1）、`scripts/lib/net.py:339-342`（`eth_chainId` ≠ expected 即 `RpcChainMismatch`）。

### D2（R2a D2）措辞册产物名 `report_facts.json` 与主流程 `facts.json` 不一致
`references/playbook-evidence-wording.md:18`。锚：`` `report_facts.json`、措辞表、facts gate `` → `` `facts.json`、措辞表、facts gate ``。依据 `scripts/report/facts_gate.py:531`（`--out` 默认 `facts.json`）、`references/report-template.md:208-212`（事实源即 `facts.json`）；`report_facts.json` 在现行文档与 `scripts/` 中无其他定义（测试文件名 `test_report_facts.py` 是模块名不是产物名）。

### D3（Fable 补报）A0 Solana 记账预检命令缺 `--exploration` 且占用正式产物名
`references/analyze-workflow.md:50`。锚：
```
accounting_gate_sol.py --mint <mint> --out accounting_mode.json
```
→
```
accounting_gate_sol.py --mint <mint> --exploration --out accounting_mode.exploration.json
```
依据 `scripts/solana/accounting_gate_sol.py:132-133`（无 `--bundle` 且无 `--exploration` 时 `ap.error` 退出 2）、同文档同行后句"A0 是模型预检……文件名固定为 `accounting_mode.exploration.json`，不得占用正式名"、`SKILL.md:43`（A0 预检产物名不分链）、同行 EVM 命令已带 `--exploration --out accounting_mode.exploration.json`。

## §3 完成报告 `r2_done.md` 必含
①逐条改前→改后 diff；②§1.1 字节实测（三组数）；③§1.2 各守卫原始输出；④`git diff --stat`；⑤差异/停工点；⑥禁读披露。
