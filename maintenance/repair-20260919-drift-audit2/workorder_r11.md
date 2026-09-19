# 工单 R11：v9.0.1 口径漂移与文档-代码不符 2 条纯文本修复 v2（吸收 codex 复核：D1 删"记得 / 同时"两词、依据补 Helius 默认分支）

内容基线：`8f73554`（R10 施工落地后的内容态；施工 HEAD 可含 maintenance/ 提交，但 §0.1 差异校验须为空）。来源：盲审 R11a 2 条 minor（`blind_r11a_report.md`）；R11b 0 条（`blind_r11b_report.md`）。Fable 逐条亲核两侧原文与代码属实。本单全部为纯文本修复，零代码改动；**所有锚均为目标文件整行原文，按代码块内整行字面处理**。

## §0 施工纪律
0.1 开工先确认 `git status --short` 为空并记录施工 HEAD；`git diff --stat 8f73554 HEAD -- SKILL.md references scripts commands-staging VERSION CHANGELOG.md` 须为空，不符即停工汇报。
0.2 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）、`archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`（§1.1 统计字节时 attic.md 只计大小不读内容；守卫脚本自身遍历文档属被测代码既有行为，允许并要求原样运行）；`maintenance/` 下只读本工程目录。
0.3 **白名单**：`references/data-pipeline-solana-capture.md`、`references/data-pipeline-robinhood-methods.md`，以及新建 `maintenance/repair-20260919-drift-audit2/r11_done.md`。
0.4 删除 > 修改 > 新增；每处锚必须是目标文件整行原文，以 `grep -n -F -x` 核验恰 1 处且行号一致；不符停工；按整行替换，其他行不动。
0.5 不 commit、不 push、不部署；不改 `scripts/`、`commands-staging/`、`CHANGELOG.md`、两份 manifest。

## §1 硬约束
1.1 字节：`SKILL.md` = 8021、`commands-staging/*.md` 合计 = 8789 不变；references 三组 glob（`references/*.md references/casebook/*.md references/labels/*.md`）合计 = 929105（基线 929110；两处整行替换按 UTF-8 字面模拟净变动 -5 B：D1 +5、D2 -10；实测数写入报告，须等于该值）。
1.2 守卫全绿：`python3 scripts/tests/docs_lint.py`、`docs_lint.py --all`、`casebook_lint.py`、`changelog_lint.py`、`test_contract_routes.py`、`test_sixlens_docs.py`、`test_g3_docs_guards.py`、`test_version_consistency.py`、`test_commands_deploy_sync.py`，原始输出贴进 r11_done.md。
1.3 `git diff --stat` 只含 §0.3 白名单。

## §2 逐条施工（锚均为整行，已由 Fable 逐行匹配验为恰 1 处；行号以 `8f73554` 内容态为准）

### D1（R11a D1）快照更新示例把 RPC 简称写成不可执行的参数值
`references/data-pipeline-solana-capture.md:61`。锚（整行）：
```
1. **新全量快照**：`scan_token_accounts.py`（Token-2022 记得 `--rpc api.mainnet-beta` + 先把旧 `_gpa_raw_*` 改名存档，见 §9.8）；同时 `getTokenSupply` 复验供给闭合（窗口内销毁体现在总量差）。
```
→（换完整 URL，并删"记得 "与"同时 "两词，其余逐字不动）
```
1. **新全量快照**：`scan_token_accounts.py`（Token-2022 `--rpc https://api.mainnet-beta.solana.com` + 先把旧 `_gpa_raw_*` 改名存档，见 §9.8）；`getTokenSupply` 复验供给闭合（窗口内销毁体现在总量差）。
```
依据 `scripts/solana/scan_token_accounts.py:147`（`--rpc` append 原样收集）、`:191`（`endpoints = args.rpcs or [_default_rpc()]`）、`:126-132`（存在非空 Helius key 时默认用 Helius，否则回退 `https://api.mainnet-beta.solana.com`，故 Token-2022 须显式传公共 URL 而不能省略 `--rpc`）；`scripts/lib/solana_attested_session.py:64`（仅 strip，不展开简称）、`:42-43`（直接 `urllib.request.Request(endpoint, …)`，非 URL 抛 `unknown url type`）。允许读取的现行文档与代码中 `--rpc api.mainnet-beta` 仅此一处；`solana-scan.md:24/:34` 的 api.mainnet-beta 为叙述简称非参数值，不动。

### D2（R11a D2）同一案例金额与「差 8 倍」不一致
`references/data-pipeline-robinhood-methods.md:20`。锚（整行）：
```
- **★gas_trace_bs 只抓普通 tx，会整体漏掉 internal 转账入金**（VIRTUAL 实测：Safe 部署者军资表面 464E 实际 1,699E 差 8 倍——73% 经 Across SpokePool 以 internal 交付）——大额资金溯源必须补 `/addresses/{a}/internal-transactions`（浏览器 UA）；"资金链断头"结论在补查 internal 前不得下（VIRTUAL 复核，07-16）
```
→
```
- **★gas_trace_bs 只抓普通 tx，会整体漏掉 internal 转账入金**（VIRTUAL 实测：Safe 部署者军资表面 464E 实际 1,699E——73% 经 Across SpokePool 以 internal 交付）——大额资金溯源必须补 `/addresses/{a}/internal-transactions`（浏览器 UA）；"资金链断头"结论在补查 internal 前不得下（VIRTUAL 复核，07-16）
```
依据同行数字：1,699/464≈3.66，(1699−464)/1699≈72.7% 与句中 73% 相符，「差 8 倍」无法由两金额得出；删去该短语，两金额与 73% 足以表达案例。

## §3 完成报告 `r11_done.md` 必含
①逐条改前→改后 diff；②§1.1 字节实测（三组数）；③§1.2 各守卫原始输出；④`git diff --stat`；⑤差异/停工点；⑥禁读披露。
