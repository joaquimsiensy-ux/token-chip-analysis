# SQD Portal 协议三场景实测记录（F-06 第一刀定案依据）

- 实测时间：2026-08-15；端点 `https://portal.sqd.dev/datasets/binance-mainnet/stream`（直连，gzip）
- 探针标的：CAKE `0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82`（BSC，部署于约块 693k）+ ERC20 Transfer topic0
- 原始响应与请求体存执行会话 scratchpad（sqd_s1/s2/s3_*），关键数据如下，全部为真实 HTTP 200 输出

## 场景 1：零匹配区间 [100000, 100010]（标的部署前，保证零事件）

- 响应 2 行，**均为 header-only 哨兵行**（无 logs 字段）：首块 100000 与末块 100010
- 末行 `header.number = 100010 = 请求上界` → **零匹配区间不产生空正文，provider 用哨兵行确认扫描前沿**
- 响应头含 `x-sqd-finalized-head-number: 116086855`、`x-sqd-head-number`、`x-sqd-finalized-head-hash`（数据源当前高度元数据，可作辅助证据，不强依赖）

## 场景 2：稀疏长区间 [1, 2000000]（前约 69 万块零事件）

- 响应仅 20 行即截断，末行 `number=419815`，**has_logs=False**（header-only 哨兵），远小于请求上界 2000000
- 中间行（如第 2 行 number=168306）同为 header-only → 响应按内部数据分片推进，每片留进度哨兵
- 证明：**单次响应不保证覆盖请求区间；截断点由末行哨兵标记扫描前沿**；续拉 `cur = 末行 number + 1` 无缝

## 场景 3：有事件区间 [690000, 800000]（活跃早期）

- 响应 25046 行（7.5MB）截断于 748026 < 800000；末行 **has_logs=True**（事件行）
- 含事件行 25037/25046，首行 690000 为 header-only 起点哨兵
- 证明：截断末行可以是事件行，其 `number` 同样是扫描前沿（该块已扫完）

## 定案结论

1. **SQD 正常响应永不为空正文**——至少含区间首块哨兵；零匹配也有首末哨兵。**空正文＝协议/网络异常**，绝不能当"已扫描"推进。
2. **每次响应末行的 `header.number` ＝ provider 侧扫描前沿**（无论哨兵行还是事件行）——v2 收据的块游标语义对 SQD 成立。
3. 现有代码病灶精确定位：`fetch_sqd_evm.py` 空正文时 `last_block` 保持 `cur` 再 `cur = last_block + 1`，等于**把异常响应当成"该块已扫完"悄悄跳块**——跳过块内的 Transfer 全部丢失且全绿。
4. **裁决：SQD 保留正式 receipt 资格**；receipt 游标必须改为 provider 派生值（全程响应末行块号的最大值 +1），完成条件＝provider 末行块号 ≥ 请求上界。
