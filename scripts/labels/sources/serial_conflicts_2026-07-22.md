# 惯犯库 × 主标签库 身份冲突报告（2026-07-22）

共 1 条（primary 1）。primary=主库设施身份 vs 庄家成员,误入库会被高置信覆盖抹掉设施标签→聚类拦截失效。**不阻塞入库,逐条人工裁决。**

## [goldset-infra] bsc `0x238a358808379702088667322f80ac48bad5e6c4`
- 惯犯侧: 惯犯庄家（QUQ案·大庄#1(刷量bot合约+EOA接力库存体系)）
  - 证据: QUQ分析 appendix whale_group「大庄#1(刷量bot合约+EOA接力库存体系)」
- 主库侧: 惯犯庄家（QUQ案·大庄#1(刷量bot合约+EOA接力库存体系)） <serial-actor|tier=identity|merge=allow> 来源:manual-addressbook+serial-offenders
  - 证据: benchmark goldset expected=infrastructure（manual 层设施金标）

