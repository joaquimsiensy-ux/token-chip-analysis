# 登记不修台账 —— repair-20260918b-p0-fig2-decimals（调度方维护）

| 编号 | 段 | 内容 | 处置 |
|---|---|---|---|
| Q1 | 全局 | review F06：峰值 override 证据自写、metrics 无公式契约（900% 通过） | 用户 09-18 裁决：威胁模型＝自己人，维持现状，已知残余 |
| Q2 | 全局 | review F02/F03/F04（净室轨） | 缓修 P1（09-18 上午裁决） |
| Q3 | G1 | `references/report-template.md:222` 只写"终值对账"，未提必画下限 | 文档不增字；契约由 CHANGELOG 条目与代码 docstring 承载 |
| Q4 | G1 | 必画下限只按 label 前缀（项目方/大庄/小庄/离场庄），与 stage2_closeout 既有规则同源；不按 tier/category | 与现行契约一致 |
| Q5 | G2 | Solana 分支 `accounting.checks.decimals` 与 observation bundle `supply.decimals` 的相等性未在共享校验器加核（accounting_gate_sol 从 mint 真写出，F05 闸已消费） | 本轮只修 EVM 缺口；Solana 对称加固另单（需动 batch14/15 夹具） |
| Q6 | G2 | 非标准 ERC20（无 decimals() 或返回非 uint8）在观测阶段直接 FAIL，正式通路被拒 | 目标行为（review 修复方向原文）；特殊代币需另立有证据的适配 |
| Q7 | G2 | 存量 EVM 案 v1 bundle 在闸前 BLOCK，须重跑 observe_supply→accounting_gate→supply_truth 三件再重建下游 | 迁移代价明示；钉版机制承接旧案 |
| Q8 | 版本 | G2 升 bundle schema v1→v2、旧 v1 拒收＝不兼容契约变更；按 CHANGELOG 头部规则应为主版本；叠加 7.2.1 待决的 8.0.0 争议 | **已裁决 09-18：8.0.0（主版本）**，收官段 E 执行 |
