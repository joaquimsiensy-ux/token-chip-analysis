# EVM V3/V4 LP 手续费核算

> 适用：回答“项目方/庄家做 LP 赚了多少”“V3 与 V4 哪个池手续费更多”“某 NFT/仓位最近 24h 收入多少”。本页只规定可复用账本与措辞；具体代币结论不得回写 skill。

## 1. 先锁定四个不同问题

任何 LP 收益结论都必须分列，禁止混成一个“收入”：

1. **池子产生费 `pool_generated_fee`**：窗口内所有 swap 产生的目标币/报价币手续费。
2. **仓位应得费 `position_attributed_fee`**：目标仓位在实际价格路径上按活跃流动性份额分到的 gross fee。
3. **当前未结算费 `uncollected_fee_snapshot`**：目标区块时仓位自上次 checkpoint 后尚未结算的账本值。
4. **历史已结算/已提现费 `settled_or_withdrawn_fee`**：过去每次仓位操作中真正结算给持有人的 fee 部分。

第 1–3 项可分别计算；第 4 项在 V4 普通事件层最难。**不得用“2−3”无条件冒充 4**：当前未结算费可能含窗口开始前的累计，窗口内也可能有仓位迁移、NFT 转移、复投或跨 manager 结算。

同时另列：gas、无常损失/逆向选择、库存币价变化、协议费、hook delta。`gross_fee` 不是净利润，自成交产生的 fee 也可能只是同一实体左手付右手收。

## 2. V3 的事件口径

V3 常见仓位可从 `Mint/Burn/Collect` 与 position state 还原；但“`Collect−Burn=纯手续费`”只有以下条件同时满足才可用：

- 同一 pool、同一 position/tick 区间、同一统计窗口；
- 处理窗口开始前已经累计的 `tokensOwed0/1`；
- 处理 burn 先记 principal、collect 后取走 principal+fee 的时序；
- 买入方向与卖出方向分别以输入币计费，不能只算稳定币一侧。

条件不齐时，逐 swap 计算池费，再按活跃流动性份额归因；不要拿钱包收款差额硬猜。

## 3. V4 为什么“混在一起”仍然能算

V4 `PoolManager.modifyLiquidity` 在核心层分别计算：

```text
principalDelta = 增减 liquidity 造成的本金变化
feesAccrued   = 自上次 checkpoint 以来该仓位累计的 fee
callerDelta   = principalDelta + feesAccrued + 可选 hook delta
```

普通 `ModifyLiquidity` 事件只记录 poolId、sender、tickLower、tickUpper、liquidityDelta、salt，没有公开两个返回值，所以仅看 receipt 转账无法拆本金与 fee。但：

- 内部调用 trace/return data 可读取 `feesAccrued`；
- `Swap` 事件 + 全历史 `ModifyLiquidity` 可重建窗口内产生费与仓位应得费；
- `StateView.getFeeGrowthInside` + position state 可计算目标区块的未结算费。

官方机制源：

- `v4-core/src/interfaces/IPoolManager.sol`：`modifyLiquidity` 返回 `callerDelta, feesAccrued`；
- `v4-core/src/libraries/Pool.sol`：`principalDelta` 与 `feeDelta` 分开计算；
- `v4-core/src/libraries/Position.sol`：按 fee growth 差额计算 `feesOwed`；
- `v4-periphery/src/PositionManager.sol`：增加/减少 0 liquidity 也可触发 fee checkpoint/领取。

## 4. 池子窗口内产生费

逐笔读取 V4 `Swap` 事件的 `amount0, amount1, sqrtPriceX96, liquidity, tick, fee`。对第 `j` 笔 swap：

```text
fee_rate_j = event.fee / 1_000_000
gross_input_j = 正数一侧的 amount0 或 amount1
swap_fee_j ≈ gross_input_j × fee_rate_j
```

静态费池也必须读取事件内真实 `fee`；动态费池禁止把初始化费率套满全窗。整数舍入需复刻 `SwapMath` 才是逐 wei 精确，不复刻时统一标 `protocol_math_estimate`，不得伪称事件直接给出的精确 fee。

协议费不为 0 时按该版本核心合约的编码与方向扣除，禁止把 packed denominator 当普通百分比。hook 非零时检查 before/afterSwap delta、自定义记账与额外收费；`Donate` 增长 feeGrowth 但不是 swap fee，二者分开列。

## 5. 仓位应得费：逐 Swap × 逐 tick 重放

先从池创建块重放全部 `ModifyLiquidity`，得到每一时点、每个 `(manager,tickLower,tickUpper,salt)` 的 liquidity。对一笔不跨 tick 的 swap：

```text
position_share = active_liquidity_position / active_liquidity_total
position_fee   = swap_fee × position_share
```

跨 tick 时，把起止 `sqrtPriceX96` 路径按所有经过的 tick 边界切段。每段输入量权重：

```text
价格上升、token1 输入：W = L × (sqrtP_b - sqrtP_a) / Q96
价格下降、token0 输入：W = L × Q96 × (1/sqrtP_b - 1/sqrtP_a)
```

目标仓位分到：

```text
position_fee_j = swap_fee_j × ΣW_position / ΣW_all
```

不同 fee、hook 或协议费在每笔 swap 层处理后再分摊，不要先按全天总量平均。

## 6. 当前未结算费

目标区块读取区间当前 `feeGrowthInside0/1X128`，再读取仓位的 `liquidity` 与 `feeGrowthInside0/1LastX128`：

```text
feeOwed0 = floor(liquidity × (inside0 - last0 mod 2^256) / 2^128)
feeOwed1 = floor(liquidity × (inside1 - last1 mod 2^256) / 2^128)
```

这是目标区块的账本快照，不自动限定为“最近 24h”。若仓位上次 checkpoint 早于窗口开始，快照包含窗前累计；若仓位在窗口内已 checkpoint，多数窗内 fee 已进入 `callerDelta`，快照只剩 checkpoint 后部分。

## 7. 历史已结算费的三档证据

按强到弱选择：

1. **内部 trace/返回值**：逐笔解码 `PoolManager.modifyLiquidity(...)->feesAccrued`；可按交易精确拆本金与 fee。
2. **严格双端 checkpoint**：窗口起止均读取同仓位 feeGrowth state，期间所有 modify/transfer/burn 完整重放；可还原窗口应计与已结算，但要处理 NFT 所有权变更。
3. **差额估算**：窗口归因 fee − 期末未结算 fee。只允许命名 `settled_or_crystallized_estimate`，并明确可能混入跨窗累计；禁止命名 `realized_income`、`withdrawn_fee` 或“净利润”。

## 8. 所有权与实体归因

- 官方 PositionManager：用 `ownerOf(tokenId)`、NFT `Transfer` 历史和 tokenId=salt 的 position key；不能只看当前 owner，也不能只看最初 `tx.from`。
- NFT 转移后，未结算 fee 的经济权益通常随头寸转移；此前已 checkpoint 的 fee 仍归此前领取方。实体归因必须以 fee 发生/结算时点为准。
- 自定义 manager、vault、自动复投器：PositionManager 是池内 owner，最终受益人还要穿透 vault shares/manager 账本；公共 manager 不得并入庄组。
- `receipt 净现金流` 只用于证明投入/提取与归属线索，不能代替 feeGrowth/trace。

## 9. 对账 gate

输出 LP 费结论前至少通过：

1. poolId 对应的 currency0/currency1/fee/tickSpacing/hooks 唯一确认，token decimals 实查；
2. 从 Initialize/创建块重放全史 `ModifyLiquidity`，不能只抓 24h 增减；
3. 每笔 swap 后，重建的 active liquidity 与 `Swap.liquidity` 对表；不匹配必须修数据，不能继续出数；
4. 起止块分别读取 protocol fee、LP fee 与 hook；动态变化逐事件处理；
5. NFT Transfer/manager/vault 归属历史覆盖统计窗；
6. 原币数量与 USD 折价分开：原币账本值不受折价影响，USD 必须注明价格时点；
7. 把 swap fee 与 donate/hook/custom accounting 分开；
8. 自成交/刷量只影响“收入由谁支付”的经济解释，不改变协议账本产生的 gross fee。

推荐输出：

```json
{
  "accounting_classification": {
    "pool_generated_fee": "protocol_math_estimate",
    "position_attributed_fee": "tick_path_replay_estimate",
    "uncollected_fee_snapshot": "fee_growth_state_formula",
    "settled_or_withdrawn_fee": "not_reported_without_trace_or_aligned_checkpoints"
  },
  "quality": {
    "liquidity_reconstruction_mismatch_count": 0,
    "protocol_fee_checked": true,
    "hook_checked": true,
    "ownership_history_checked": true,
    "usd_price_timestamp": "ISO-8601"
  }
}
```

报告正文先给原币数量，再给同一价格时点的折算值；小数位不要用计算器精度冒充结论精度。
