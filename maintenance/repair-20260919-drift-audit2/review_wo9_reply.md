# 工单R9复核：退回

**D1 的修法会遗漏既有 extras，不能按 v1 施工。D2、D3 可原样采纳。** 三处锚点、行号和字节声明均核对正确，但 D1 的 `+119 B` 并非准确性所必需。

**D1：原发现成立，替换文本须修改。**

- [a4_gate.py:276](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/a4_gate.py:276) 确实只对 `new-analysis` 执行分布检查；`terminal` 非 null 时加入失败项，finalize 最终返回 2。`independent-audit` 豁免这项检查，但仍须满足 registry 对账、报告图目录为空等 A4 前置。“可直接 finalize”不能理解为免除这些要求。
- `stage2_closeout.py:1378、1381` 的参数真实存在；终态案先在 `:1022` reopen-cycle，再经 `:1239–1240` finalize。**问题在 [reseal_extra_files:1216](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/stage2_closeout.py:1216)：显式参数直接返回，未传才继承旧 extras。** 内存运行现行函数得到：未传参数返回 `prior_extra.json`；传入 `appendix.json` 则仅返回 `appendix.json`。mandatory、claims、当前 source 仍会加入，但其他旧 extras 不会保留。仅删除参数也不会自动封入新 appendix。
- reseal 不生成 A5 report seal。[a5_report_seal.py:373](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/a5_report_seal.py:373) 重验 A4、Markdown 绑定，`build_html.py:310–314` 对失效 A5 拒收。原 A5 流程已规定出图、封报告、编译；“再按原工作流”只有解释为**完整重走 A5**才足以覆盖，不能仅重跑 build_html。这无需另改工作流文档。

建议将 `references/monitoring-package.md:117` 整行替换为以下文本，保留原编译后半句。实测 **657 B，净增 81 B，比 v1 少 38 B**：

```text
3. 默认重跑 `build_html.py --mode legacy-recompile --degrade-reason "买入后补嵌监控 JSON，未改分析结论" --md 报告.md --out 报告.html --json appendix.json`（含宏加 `--facts facts.json`）——这是合法重编译但带显式水印。若要维持正式身份，按原流程重封 A4（新分析用 `stage2_closeout.py reseal --from a4 ...`），`--seal-files` 含原 extras 及 `appendix.json`，重走 A5（含 report seal），再按原工作流用 `build_html.py --mode analysis-new|analysis-audit ... --a4-seal a4_seal.json --json appendix.json` 走完整门禁；未进入 seal 的 JSON 一律 BLOCK，不存在 skip 开关。
```

工单依据应明确：显式 `--seal-files` 必须提供既有 extras 与 appendix.json 的完整列表；删除“+119 B 已尽量压缩”的结论。

**D2：采纳。**

[fetch_etherscan.py:24](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/evm/fetch_etherscan.py:24) 确实写死 `chainid=1`；[evm-sources:112](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-evm-sources.md:112) 确实记载免费三链 ETH/Arb/Polygon，登记文件 §8 的非敏感链范围记载相同。删除服务层的 ETH-only 断言、保留脚本限制，足以消除项目内矛盾。离线材料不能证明服务商当前套餐，但本修复没有新增套餐断言。

`references/data-pipeline-evm-channels.md:214` 采纳的整行原文：

```text
- 跨链代币的 ETH 侧全量转账、金库地址 txlist/txlistinternal（vesting 释放追踪）都走它。（OPN，07）
```

**D3：采纳。**

`playbook-entity-cluster-methods.md` 全文旧条名命中 **0 次**，`:59` 已指向 C-07。[cex-custody-methods.md:14](/Users/uravvv/.claude/skills/token-chip-analysis/references/casebook/cex-custody-methods.md:14) 确为 C-07，`:23` 包含 gas supplier 等组合指纹。属于真实失效引用修复。

`references/address-book.md:225` 采纳的整行原文：

```text
0xa86309988947559b6e72ef716c5058f479386c0f,eth,Coinbase Prime Custody Gas Supplier 1,cex,exclude,addressbook,2026-07-25,标签库多源 + 创世资金来自 Coinbase 4；Prime 托管分仓 gas 滴灌锚,,,,,,,,E-CEX,Coinbase Prime Custody Gas Supplier 1 (ETH)；标签库多源＋创世资金来自 Coinbase 4；**机构托管分仓群识别锚**——分仓群 gas 全由它精确滴灌＝Prime 托管实锤（判例见 casebook C-07）；⚠托管≠自营，Prime 托管是客户/机构资产，风险语义与所自营仓不同（SPX6900 分析核验 2026-07-25）
```

**回归面、白名单及最小修改原则。**

- 在允许读取的现役 Markdown 中，未发现需要新增修复文件的同款残留。`analyze-workflow.md:174、180` 属首封或非终态回流；`:182` 已规定终态后 reopen-cycle，`split-run.md:136` 已规定 reseal。
- `evm-channels.md:23、151、212` 的 ETH 限制与脚本、通道绑定，不能当作另一处服务套餐漂移。`robinhood-channels.md:16` 的 Arbitrum 记载与 sources 一致。
- 失效条名仅命中 address-book:225。删除整个括注可减 93 B，但损失判例入口；缩为“（见 casebook C-07）”可比 v1 再减 6 B，仅属可选措辞，不作为退回理由。
- **现有三份正文白名单足够。** 无需修改 SKILL、代码、命令、manifest 或 CHANGELOG。建议文本仍只修原问题，没有扩大范围。

**汇总表**（UTF-8 字节不含行尾 LF；LF 不变）：

| 项目 | `grep -n -F`／`-F -x` | 现行字节 | v1 字节／净变 | 建议字节／净变 | 意见 |
|---|---|---:|---:|---:|---|
| D1 | 均仅第 117 行 1 处 | 576 | 695／+119 | 657／+81 | 修改后采纳 |
| D2 | 均仅第 214 行 1 处 | 160 | 126／−34 | 126／−34 | 原样采纳 |
| D3 | 均仅第 225 行 1 处 | 632 | 568／−64 | 568／−64 | 原样采纳 |
| 合计 | 三锚均通过 | 1368 | 1389／+21 | 1351／−17 | v1 退回 |

三文件行数分别保持 **130、333、237**，均一行替换一行，无删行。

实测 `SKILL.md=8021 B`、commands-staging 四份合计 `8789 B`；references 基线 `929154 B`，v1 模拟 `929175 B`，全部符合工单声明。采用建议稿后，§1.1 应改为 **929137 B，净变 −17 B：D1 +81、D2 −34、D3 −64**，无需增加运行文档总字节。

末检 HEAD=`9e38bba26470c37a1621cd9c0d862c7adf8d4bb1`；git status 为空，工单规定路径相对 `bf20266` 的内容差异统计为空。

执行披露：报告已打印到 stdout；离线，未修改、新建或提交文件。未读 `~/.codex/`、memories 或其他禁读区；`attic.md` 仅取大小，未读正文。未执行会遍历禁区或创建临时文件的守卫，不声称 §1.2 全绿。首次 Git 启动器和 heredoc 的临时写入尝试被只读沙箱拒绝，未落盘；随后改用直接 Git 二进制与 `python3 -B -c`。
