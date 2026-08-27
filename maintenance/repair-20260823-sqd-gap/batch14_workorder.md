# 批 14 工单：accounting 观测 bundle 绑定的冻结态内容寻址兜底（方案 A 同族第六消费点）

- 裁决依据：延续用户 2026-08-26 方案 A。批 10-13 关五层后，ARC handoff verify
  第 2 发暴露第六处：`solana accounting observation bundle size mismatch`。
- 背景（大白话）：A0 会计核定收据把它消费的观测 bundle 按 **path+size+sha256**
  三元组绑定，path=当时的正式路径 `data/solana_observation_bundle.json`、内容=
  封账观测（ARC 实测 sha=c4f7bc53…/4686B，与
  `data/solana_observation_bundle_frozen.json` 现物逐字节同一）。方案 A 后该正式
  路径被五查 supply 观测占用（活链 bundle 4725B/87e18219…，supply_truth 收据
  也按该路径绑定活内容）——**同一路径被两份合法收据绑定两份不同内容**，
  案级无解。`_bound_case_ref`（shared_release_receipt.py:345-358）按"路径上的
  现物"验哈希 → accounting 绑定必炸。
- 修正哲学：**哈希是身份，路径只是地址**。sha256+size 全等＝字节同一，收据
  attested 的就是这份内容；它现居冻结件正式命名处不损真实性。冻结态给
  accounting bundle 绑定加内容寻址兜底：路径现物不匹配时，若
  `SOLANA_FROZEN_OBSERVATION_BUNDLE`（data/solana_observation_bundle_frozen.json）
  的 size+sha256 与收据记录**逐字节全等**，则解析到冻结件继续全部后续深验；
  两处都不匹配维持原报错 fail-closed。

## 改动面

### 1. shared_release_receipt.py solana accounting bundle 绑定段（约 :1756-1767）

- 现行 `_bound_case_ref(root, bundle_ref, "solana accounting observation bundle")`
  改为：先按原路径试解析；`size mismatch`/`sha256 mismatch` 时（仅这两种失败，
  路径逃逸/符号链接等安全类失败**不兜底**照拒），改试
  `root/SOLANA_FROZEN_OBSERVATION_BUNDLE`：该文件必须存在、为普通文件、案根内、
  且 size+sha256 与 bundle_ref 记录全等——全等则用它作 bundle_path，否则抛
  原始错误（不吞安全类异常）。
- 兜底命中后走完全部既有后续检查（validate_observation_bundle 深验＋
  observed_context_slot==snapshot.slot），零跳过。
- `_bound_case_ref` 通用函数本体**不改**（它服务全库绑定；兜底逻辑只落在
  accounting solana 分支局部）。
- EVM accounting 分支零变化。

### 2. 波及面核查（关到同一深度）

- rg 全库找同型"A0/封账期收据按正式路径绑定、路径现物已被活观测替换"的其他
  绑定面（supply_truth 绑活 bundle=自洽不需改；重点查还有谁绑了封账内容的
  旧路径），逐处行号结论写 done 报告。
- handoff generate 路径（本轮 generate exit 0）是否也解析 accounting bundle
  绑定——给行号结论；若有同型比对同修。

### 3. 文档

- scan-schemas.md accounting 段（若有绑定表述）补一句冻结态内容寻址兜底的
  大白话；无则 done 说明。

### 4. 测试（先红后绿）

- R1 红：冻结态夹具（accounting 绑封账内容@正式路径、正式路径现物=活 bundle、
  冻结件=封账内容）→ 现行拒 size mismatch（留红证据）。
- G1 绿：同夹具改后通过（且后续深验真实走到）。
- N1：冻结件也不匹配（内容被改 1 字节）→ 拒（原始报错）。
- N2：冻结件缺失 → 拒。
- N3：路径逃逸/符号链接类失败 → 不进兜底直接拒（安全面回归）。
- N4：静态态（路径现物即匹配）与 EVM 全部现有夹具零变化。
- run_all 全套（真实失败清零）。

## 边界与禁改面

- validate_observation_bundle / _bound_case_ref 本体 / accounting 生产者 /
  批 10-13 已改面一律不动。
- 不触碰密钥；ARC 案根一个字不动。
- 纯改文件不 commit、不动版本登记面；完成写 batch14_done.md，Fable 验收后代 commit。
