# 惯犯库 × 主标签库 身份冲突报告（2026-07-25）

共 2 条（primary 2）。primary=主库设施身份 vs 庄家成员,误入库会被高置信覆盖抹掉设施标签→聚类拦截失效。**设施级已硬闸拦截不入库,逐条人工裁决**（三路径见脚本 docstring）。

## [primary] bsc `0x2aa5d15eb36e5960d056e8fea6e7bb3e2a06a351`
- 惯犯侧: 惯犯庄家（SIREN案·离场庄#1·核心链）
  - 证据: SIREN分析2026-07-19 appendix whale_group「离场庄#1·核心链」
- 主库侧: Hedgey TokenLockup/NFT 锁仓协议（公共设施） <locker|tier=exclude|merge=no_merge> 来源:serial-offenders+curation
  - 证据: Sourcify v2 exact_match 验证名 'Hedgeys'（chainId 56）；SIREN 案 2026-07-19 误判为'离场庄#1·归集主仓（庄家的单一大钱包）'收进核心成员表并随 serial 回灌标成'惯犯庄家'，GPT5.6 外部复核 REFUTED 后 Sourcify 复验裁决恢复设施身份（skill v3.27.0）——905 份 SIREN 锁仓计划的'归集

## [primary] bsc `0xb1c5b2ca2f0af1424897ab7377cbeda4ab9a6699`
- 惯犯侧: 惯犯庄家（SIREN案·离场庄#1·核心链）
  - 证据: SIREN分析2026-07-19 appendix whale_group「离场庄#1·核心链」
- 主库侧: Hedgey BatchNFTMinter（公共设施） <infra|tier=exclude|merge=no_merge> 来源:serial-offenders+curation
  - 证据: Sourcify v2 match 验证名 'BatchNFTMinter'（chainId 56）；SIREN 案 2026-07-19 误判为'离场庄#1·专用原子转发合约（私人通道反成归属铁证）'收进核心成员表并随 serial 回灌标成'惯犯庄家'，GPT5.6 外部复核 REFUTED 后 Sourcify 复验裁决恢复设施身份（skill v3.27.0）——'即收即转 905 笔/生

