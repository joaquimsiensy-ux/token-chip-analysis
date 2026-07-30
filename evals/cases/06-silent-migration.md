# 题 6：全部自检通过的重放，余额是真的吗

## A 节·执行输入（可投喂，零泄漏）

**场景**（纸面题，GNT 链上可实查）：一个 2016 年发行的 ETH 老币（后来项目方发过新版代币，老合约留有 `migrate()` 函数）。全量事件重放完成：mint_total=10 亿、`sum_balances_wei == mint_total` 闭合、无负余额、supply_check_ok=true、accounting_gate 判 PASS（standard 模式）。你按重放余额出 TOP 持仓榜，正要写进报告。

**任务**：交付前还需要做什么供给侧检验？如果发现异常，余额口径怎么处理？（合约 `0xa744…ac0d` 可实查验证。）

## B 节·考官侧（禁止进入执行会话上下文）

1. **当年确证错误**（GNT 2026-07-28 实测）：老合约 `migrate()` **直接改账本、不发任何 Transfer/Burn 事件**。重放余额**虚高 10 倍**（TOP12 重放 5.26 亿 vs 链上实时 0.52 亿），而 mint/burn 闭合、负余额、accounting_gate 的全部检测项**没有一项能覆盖**——全绿放行。唯一暴露手段：拿 `mint_total − burn_total` 比链上实查 `totalSupply()`（重放 10 亿 vs 链上 2.035 亿，差 7.96 亿=已迁移量）。旁证指纹：浏览器深榜加总远超 100%（GNT 1500 名加总=264%）。
2. **唯一失败原因**：重放终态没有对过链上 totalSupply 真值——内部自检全部自洽不等于对外部为真（模型错但自洽）。
3. **禁止输出**：把重放余额直接当真实持仓写进报告/持仓榜。
4. **必做证据动作**：重放收尾必跑供给真值闸——`mint_total − burn_total` vs 链上 `totalSupply()`（EVM `eth_call totalSupply` / Solana `getTokenSupply`），超阈值即 FAIL。FAIL 后处置：余额改走 Multicall3 链上实时直查；地址全集与转账历史仍可用重放（迁移不改历史事件）；重放余额仅可作"≥阈值超集筛选"（migrate 只减不增，数学严格）。
5. **缺证据时的结论上限**：totalSupply 查询临时不可用时**不允许交付持仓结论**——这是 fail-closed 闸，不是软提醒（本题没有"降级表述"出路，等通道恢复）。

**预期拦截点**：**供给真值闸（v6 新增代码，本题是它的验收题）**——analyze/easy/update 三条 workflow 的重放收尾必跑项 + casebook/supply-accounting.md 静默改账条。
