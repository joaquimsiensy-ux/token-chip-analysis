# 工单 R10：v9.0.1 口径漂移与文档-代码不符 1 条纯文本修复 v1

内容基线：`4353454`（R9 施工落地后的内容态；施工 HEAD 可含 maintenance/ 提交，但 §0.1 差异校验须为空）。来源：盲审 R10a 1 条 blocker（`blind_r10a_report.md`）；R10b 0 条（`blind_r10b_report.md`）。Fable 亲核两侧原文与代码属实。本单为纯文本修复，零代码改动；**锚为目标文件整行原文，按代码块内整行字面处理**。

## §0 施工纪律
0.1 开工先确认 `git status --short` 为空并记录施工 HEAD；`git diff --stat 4353454 HEAD -- SKILL.md references scripts commands-staging VERSION CHANGELOG.md` 须为空，不符即停工汇报。
0.2 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）、`archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`（§1.1 统计字节时 attic.md 只计大小不读内容；守卫脚本自身遍历文档属被测代码既有行为，允许并要求原样运行）；`maintenance/` 下只读本工程目录。
0.3 **白名单**：`references/data-pipeline-solana-scan.md`，以及新建 `maintenance/repair-20260919-drift-audit2/r10_done.md`。
0.4 删除 > 修改 > 新增；锚必须是目标文件整行原文，以 `grep -n -F -x` 核验恰 1 处且行号一致；不符停工；按整行替换，其他行不动。
0.5 不 commit、不 push、不部署；不改 `scripts/`、`commands-staging/`、`CHANGELOG.md`、两份 manifest。

## §1 硬约束
1.1 字节：`SKILL.md` = 8021、`commands-staging/*.md` 合计 = 8789 不变；references 三组 glob（`references/*.md references/casebook/*.md references/labels/*.md`）合计 = 929122（基线 929131；一处整行替换按 UTF-8 字面模拟净变动 -9 B；实测数写入报告，须等于该值）。
1.2 守卫全绿：`python3 scripts/tests/docs_lint.py`、`docs_lint.py --all`、`casebook_lint.py`、`changelog_lint.py`、`test_contract_routes.py`、`test_sixlens_docs.py`、`test_g3_docs_guards.py`、`test_version_consistency.py`、`test_commands_deploy_sync.py`，原始输出贴进 r10_done.md。
1.3 `git diff --stat` 只含 §0.3 白名单。

## §2 逐条施工（锚为整行，已由 Fable 逐行匹配验为恰 1 处；行号以 `4353454` 内容态为准）

### D1（R10a D1，blocker）旧 Solana 快照「raw/supply 完整可直接重新 emit」承诺过不了当前扫描器哈希校验
`references/data-pipeline-solana-scan.md:67`。锚（整行）：
```
- **G8 离线重放契约**：`holders_snapshot_meta.json` 绑定的每个 GPA `raw_artifact` 不是“有文件有哈希”即算通过；identity emitter/check 必须调用 `scan_token_accounts.py` 的同一套 `parse_gpa_response`＋`parse_token_accounts`，从原始 RPC JSON 重做 base64 解码、跨 dataSlice/pubkey 去重、账户明细和 owner 聚合，并要求逐条等于 `holders_accounts.json`/`holders_owners.json`；同时解析 supply receipt 的 `result.value.amount` 与 `supply_raw` 闭合。round4b 格式存量若 raw/supply 实物完整可直接重新 emit；缺失或重放不一致则必须重跑 `scan_token_accounts.py`，禁止手补 meta/hash。
```
→（只改末句，其余逐字不动）
```
- **G8 离线重放契约**：`holders_snapshot_meta.json` 绑定的每个 GPA `raw_artifact` 不是“有文件有哈希”即算通过；identity emitter/check 必须调用 `scan_token_accounts.py` 的同一套 `parse_gpa_response`＋`parse_token_accounts`，从原始 RPC JSON 重做 base64 解码、跨 dataSlice/pubkey 去重、账户明细和 owner 聚合，并要求逐条等于 `holders_accounts.json`/`holders_owners.json`；同时解析 supply receipt 的 `result.value.amount` 与 `supply_raw` 闭合。存量产物 producer 哈希须等于当前扫描器且 raw/supply 重放一致，否则必须重跑 `scan_token_accounts.py`，禁止手补 meta/hash。
```
依据 `scripts/report/identity_snapshot_receipt.py:83-84`（meta.producer 必须等于 `{path: scan_token_accounts.py, sha256: 当前文件 sha}`，否则 ValueError）、`:143`（emit_solana 先调用该校验）、`:188`（ValueError → exit 2 BLOCK）；`scripts/solana/scan_token_accounts.py:265`（producer.sha256 = 扫描器自身文件哈希）。旧扫描器产物的 producer 哈希必然不等于当前，故「实物完整即可直接 emit」不成立；改为「producer 哈希等于当前扫描器且 raw/supply 重放一致」两个条件，其余重跑与禁手补规则保留。全库 `round4b 格式存量` 仅此一处（maintenance-review-repair.md:116 的 round4b 为版本史，不动）。

## §3 完成报告 `r10_done.md` 必含
①改前→改后 diff；②§1.1 字节实测（三组数）；③§1.2 各守卫原始输出；④`git diff --stat`；⑤差异/停工点；⑥禁读披露。
