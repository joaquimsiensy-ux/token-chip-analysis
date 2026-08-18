# 批 5 T2：ARC 真采实物破坏性注入三连

## 1. 执行边界

- 输入：T1 碰撞窗的真实 v4 edge/meta。
- 注入副本：`/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/token-chip-batch5-injection-q40odkxr/`。
- 三种注入各自复制完整 `data/` 到独立子目录；T1 原件不改。
- 原件执行前后 SHA-256 一致：
  - edge：`27d3a900e73832216b0e61fc622dbeb281feac2e9176585d79a0384ca7199917`；
  - meta：`831887be6f11ead8210f06943ef34f86bc6463cf0e10a3fce1cbcadb4f8b3824`。

复算命令：

```text
python3 maintenance/repair-20260817-sqd-v4/tools/destructive_injection_verify.py
```

总结果：`status=PASS`。

## 2. 注入 1：边内容单一逻辑字节

- 注入：解压后的逻辑边流 offset 139，ASCII `6→8`；总长度不变，逐字节 Hamming distance=1，
  随后重新封装 gzip。副本 edge SHA-256 变为
  `5161fbc6d8ae6cb8f997c57bf395c46dba2bdf5b6401b90e56cb3a08972740ba`，meta 保持原样。
- 调用：正式 `replay_edges.py reconcile --mint <ARC> --no-labels`。
- 返回：rc=2。
- 错误原文：

```text
BLOCK: SQD 缓存 meta.edge_logical_sha256 与实际边重放摘要不一致
```

- 到达自证：该错误只在 `cmd_reconcile` 对真实遍历边计算 `edge_digest` 后，与 meta
  `edge_logical_sha256` 比较的目标分支产生；不是 gzip 解码、7 元组格式或参数错误。

## 3. 注入 2：未登记 collector hash

- 注入：meta `collector_sha256` 从现役登记值
  `2589f6a396c262d0747343ef21dee2bc7ba814eaa59eebdfa782fe9253c32212` 改为 64 个 `f`；
  其他 meta 和 edge 保持原样。
- 调用：正式 `replay_edges.py top 1 --mint <ARC> --no-labels`。
- 返回：rc=1（`_validate_cache_meta` 用带文本的 `SystemExit` 前置拒绝）。
- 错误原文：

```text
SQD v4 meta.collector_sha256 未命中 fetch_sqd_transfers_v2.py producer 登记
```

- 到达自证：精确命中 `_validate_cache_meta` 的 `historical_producer_hashes` ACTIVE 对表分支；
  不是 schema、mint、窗口或边格式拒绝。

## 4. 注入 3：v3 meta

构造案内样式 v3 meta：`schema=sqd-solana-cache/v3`、`version=3`、原 mint/from slot，且把原
`finalized_upper_slot` 映射为 `collection_upper_slot`。

第一路，正式 replay：

- 调用：`replay_edges.py top 1 --mint <ARC> --no-labels`；
- 返回 rc=1；
- 错误原文：

```text
正式重放只接受绑定原始 mint、v4 边契约及 finalized_upper_slot 的 v4 meta
```

第二路，producer 前置升级闸：

- 调用 collector 时把 SQD 与 state RPC 都故意指向不可用哨兵 `127.0.0.1:9`；
- 返回 rc=2；
- 错误原文：

```text
[sqd2] [fail-closed] 检测到旧 SQD cache meta 'sqd-solana-cache/v3'；格式升级需全量重采，旧缓存请改名归档
```

- 到达自证：拿到旧 meta 的专用升级拒绝文案，而不是哨兵端点的连接错误，证明拒绝发生在首个
  SQD/RPC 请求和任何 v4 part 写入之前。
