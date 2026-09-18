# 登记不修台账 —— repair-20260918c-p1-f02-f04-f05（调度方维护）

| 编号 | 段 | 内容 | 处置 |
|---|---|---|---|
| Q1 | 全局 | review F01：price_check 对含 `-` 的时间只截前 10 位，同日多条时按价格排序取到最高价 | 用户 09-18 裁决：影响面有限，不修 |
| Q2 | 全局 | review F07：price_check 非有限价格（NaN）落入 PASS，收据含非法 JSON NaN | 本轮不在名单（三轮连报；与 Q1 同属 price_check 解析层，下次一并） |
| Q3 | 全局 | review F03：峰值 override 证据自报 | 维持 0918 晚裁决：威胁模型＝自己人，已知残余 |
| Q4 | 全局 | review F08 / F06 | 环境项 / 探索 helper 文档，不修 |
| Q5 | F04 | `RpcPool._one` 只校验 `result` 键在场，不校验 `id` 回显与 `jsonrpc` 版本 | 最小改动：id/jsonrpc 校验会改变部分提供商（id 类型不同）的行为面，不扩 |
| Q6 | F04 | 合法 `"result": null`（如 `eth_getTransactionReceipt` 未上链）继续 `ok=True, result=None`；各方法消费者自核类型（lp_positions/evm_observation 等既有处理不改） | 与 review"合法 null 与缺字段须区别对待"一致 |
| Q7 | F05 | closeout 只核收据内容与主源哈希绑定，不重跑第二源网络查询（离线） | 目标：拒纯申报，不是复算价格 |
| Q8 | F05 | 存量代价（明示）：`price_check.py` 收据新增 `price_file_sha256`，旧收据（无该字段）在 closeout 被拒；**APU 0914 案** `price_source_checks.json` 为自定义格式（primary/rows/comparisons）亦被拒——进 −3 前须 `price_check.py --out price_source_checks.json` 重跑并 `stage2_closeout amend` 工单；ARC 案内联 `dual_source_check.receipt` 形态符合新契约无需改 | 已汇报；**用户 09-18 裁决：APU 暂不重跑**，进 −3 时再补 |
| Q9 | F05 | 内联 `price_source.dual_source_check` 若为字符串（KAITO/LIT/AZTEC/SPORTFUN/COLLECT 存量）现行 HEAD 已拒（need isinstance dict），本轮不改变其命运 | 存量已 BLOCK，非本轮新增代价 |
| Q10 | F02 | 流通量只作选材分母，不进 G2 供给上界、不进宏渲染（无 `{{e.circ_share}}` 宏）；report-template:179 已写"总供应或流通"，文档零改动 | 能改不增 |
| Q11 | F02 | 流通量来源为人工声明（第三方口径：CG/CMC/项目方披露），带 asof/source；不做链上重算（流通量本无链上定义） | 与 playbook-supply-recon.md:13"第三方流通口径只作可比口径引用"一致 |
| Q12 | 版本 | 8.1.0 vs 9.0.0 | **用户 09-18 裁决：9.0.0**（契约收紧＝主版本先例） |
