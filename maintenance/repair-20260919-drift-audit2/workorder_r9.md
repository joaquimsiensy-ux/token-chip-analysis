# 工单 R9：v9.0.1 口径漂移与文档-代码不符 3 条纯文本修复 v2（吸收 codex 复核：D1 改为显式 --seal-files 须含原 extras＋重走 A5 的整行稿、D3 压缩）

内容基线：`bf20266`（R8 施工落地后的内容态；施工 HEAD 可含 maintenance/ 提交，但 §0.1 差异校验须为空）。来源：盲审 R9a 1 条 blocker（`blind_r9a_report.md`）＋ R9b 1 minor＋1 nit（`blind_r9b_report.md`）；Fable 逐条亲核两侧原文与代码属实。本单全部为纯文本修复，零代码改动；**所有锚均为目标文件整行原文，按代码块内整行字面处理**。

## §0 施工纪律
0.1 开工先确认 `git status --short` 为空并记录施工 HEAD；`git diff --stat bf20266 HEAD -- SKILL.md references scripts commands-staging VERSION CHANGELOG.md` 须为空，不符即停工汇报。
0.2 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）、`archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`（§1.1 统计字节时 attic.md 只计大小不读内容；守卫脚本自身遍历文档属被测代码既有行为，允许并要求原样运行）；`maintenance/` 下只读本工程目录。
0.3 **白名单**：`references/monitoring-package.md`、`references/data-pipeline-evm-channels.md`、`references/address-book.md`，以及新建 `maintenance/repair-20260919-drift-audit2/r9_done.md`。
0.4 删除 > 修改 > 新增；每处锚必须是目标文件整行原文，以 `grep -n -F -x` 核验恰 1 处且行号一致；不符停工；按整行替换，其他行不动。
0.5 不 commit、不 push、不部署；不改 `scripts/`、`commands-staging/`、`CHANGELOG.md`、两份 manifest。

## §1 硬约束
1.1 字节：`SKILL.md` = 8021、`commands-staging/*.md` 合计 = 8789 不变；references 三组 glob（`references/*.md references/casebook/*.md references/labels/*.md`）合计 = 929131（基线 929154；三处整行替换按 UTF-8 字面模拟净变动 -23 B：D1 +81、D2 -34、D3 -70；实测数写入报告，须等于该值）。
1.2 守卫全绿：`python3 scripts/tests/docs_lint.py`、`docs_lint.py --all`、`casebook_lint.py`、`changelog_lint.py`、`test_contract_routes.py`、`test_sixlens_docs.py`、`test_g3_docs_guards.py`、`test_version_consistency.py`、`test_commands_deploy_sync.py`，原始输出贴进 r9_done.md。
1.3 `git diff --stat` 只含 §0.3 白名单。

## §2 逐条施工（锚均为整行，已由 Fable 逐行匹配验为恰 1 处；行号以 `bf20266` 内容态为准）

### D1（R9a D1，blocker）监控包「维持正式身份」指引让已交付案直接再跑 a4 finalize，会被分布终态检查拒绝
`references/monitoring-package.md:117`。锚（整行）：
```
3. 默认重跑 `build_html.py --mode legacy-recompile --degrade-reason "买入后补嵌监控 JSON，未改分析结论" --md 报告.md --out 报告.html --json appendix.json`（含宏加 `--facts facts.json`）——这是合法重编译但带显式水印。若要维持正式身份，必须把 `appendix.json` 加入 `a4_gate.py finalize --seal-files ...` 重新封口，再按原工作流用 `build_html.py --mode analysis-new|analysis-audit ... --a4-seal a4_seal.json --json appendix.json` 走完整门禁；未进入 seal 的 JSON 一律 BLOCK，不存在 skip 开关。
```
→
```
3. 默认重跑 `build_html.py --mode legacy-recompile --degrade-reason "买入后补嵌监控 JSON，未改分析结论" --md 报告.md --out 报告.html --json appendix.json`（含宏加 `--facts facts.json`）——这是合法重编译但带显式水印。若要维持正式身份，按原流程重封 A4（新分析用 `stage2_closeout.py reseal --from a4 ...`），`--seal-files` 含原 extras 及 `appendix.json`，重走 A5（含 report seal），再按原工作流用 `build_html.py --mode analysis-new|analysis-audit ... --a4-seal a4_seal.json --json appendix.json` 走完整门禁；未进入 seal 的 JSON 一律 BLOCK，不存在 skip 开关。
```
依据 `scripts/report/a4_gate.py:276-277`（仅 new-analysis 做此检查）、`:285-286`（`distribution_rounds.json` 有 terminal → fails「禁止再次 A4 finalize」）、`:434-438`（fails 非空返回 2）；`scripts/report/stage2_closeout.py:1378`（`reseal --from {freeze,a4,rounds}`）、`:1381`（`--seal-files`）、`:1022`（reseal 先 `holder_distribution_scan.py reopen-cycle`）、`:1216-1222`（显式 `--seal-files` 直接采用，否则自动合并既有 extras）、`:1237-1240`（再 `a4_gate.py finalize --seal-files <extras>`）；`references/split-run.md:136`（「重封一律 `stage2_closeout reseal`」）。只改该句，后半「再按原工作流用 build_html…」逐字不动。注意 `stage2_closeout.py:1216-1218` 显式 `--seal-files` 直接采用、不继承旧 extras，故须写明"含原 extras 及 appendix.json"；reseal 不产 A5 report seal（`a5_report_seal.py:373` 重验 A4 与 md 绑定，`build_html.py:310-314` 拒失效 A5），故须"重走 A5（含 report seal）"。

### D2（R9b D1）Etherscan V2 免费层链范围两处互斥
`references/data-pipeline-evm-channels.md:214`。锚（整行）：
```
- 免费 key 仅 chainid=1 可用；跨链代币的 ETH 侧全量转账、金库地址 txlist/txlistinternal（vesting 释放追踪）都走它。（OPN，07）
```
→
```
- 跨链代币的 ETH 侧全量转账、金库地址 txlist/txlistinternal（vesting 释放追踪）都走它。（OPN，07）
```
依据 `references/data-pipeline-evm-sources.md:112`（免费三链 ETH/Arb/Polygon，chainid=42161 全可用）、api-keys §8 同款；`scripts/evm/fetch_etherscan.py:24` 写死 chainid=1 属脚本限制，§3.4 标题与 `:23` 已注明「仅 ETH 主网 / 仅 chainid=1，fetch_etherscan.py」，故删去对免费 key 的错误断言即可。

### D3（R9b D2）地址簿指向 methods 分册中不存在的条名
`references/address-book.md:225`。锚（整行）：
```
0xa86309988947559b6e72ef716c5058f479386c0f,eth,Coinbase Prime Custody Gas Supplier 1,cex,exclude,addressbook,2026-07-25,标签库多源 + 创世资金来自 Coinbase 4；Prime 托管分仓 gas 滴灌锚,,,,,,,,E-CEX,Coinbase Prime Custody Gas Supplier 1 (ETH)；标签库多源＋创世资金来自 Coinbase 4；**机构托管分仓群识别锚**——分仓群 gas 全由它精确滴灌＝Prime 托管实锤（指纹三件套见 playbook-entity-cluster-methods「CEX 提币囤仓反转通道」条）；⚠托管≠自营，Prime 托管是客户/机构资产，风险语义与所自营仓不同（SPX6900 分析核验 2026-07-25）
```
→
```
0xa86309988947559b6e72ef716c5058f479386c0f,eth,Coinbase Prime Custody Gas Supplier 1,cex,exclude,addressbook,2026-07-25,标签库多源 + 创世资金来自 Coinbase 4；Prime 托管分仓 gas 滴灌锚,,,,,,,,E-CEX,Coinbase Prime Custody Gas Supplier 1 (ETH)；标签库多源＋创世资金来自 Coinbase 4；**机构托管分仓群识别锚**——分仓群 gas 全由它精确滴灌＝Prime 托管实锤（见 casebook C-07）；⚠托管≠自营，Prime 托管是客户/机构资产，风险语义与所自营仓不同（SPX6900 分析核验 2026-07-25）
```
依据 `references/playbook-entity-cluster-methods.md` 全文无「CEX 提币囤仓反转通道」；实际内容在 `references/casebook/cex-custody-methods.md:14`（C-07）`:23`（托管/储备层判定指纹组，含 gas supplier）；`methods.md:59` 自身也指 casebook C-07。缩为「（见 casebook C-07）」。

## §3 完成报告 `r9_done.md` 必含
①逐条改前→改后 diff；②§1.1 字节实测（三组数）；③§1.2 各守卫原始输出；④`git diff --stat`；⑤差异/停工点；⑥禁读披露。
